"""Reading the benchmark: time to a target loss.

Module 11 makes training and writing faster, and every change has to be
measured before and after. A time is a number that moves, like a loss
over seeds: the first step is slow, other programs take the processor
now and then, and a step that is faster is no use if it learns less.
This script times 10.05's "all four" GPT (RMSNorm, rotary positions,
SwiGLU, 2 key/value heads for 4) the way the rest of the module will:

1. One step, cold (the first of a process) and then warm, timed again
   and again: every timing with the load average beside it, the
   smallest, the median and the largest of each round. Tokens a second.
2. The measure from here on: the time to reach a target loss on
   held-out text, each run's validation windows scored every cfg.every
   steps (untimed) until their bits reach cfg.target; several seeds; a
   row for each of cfg.rows: the baseline, the row every later lesson
   compares with, and a step that is faster but learns less (half the
   batch). Each later lesson adds its row.
3. The recorded benchmark: every row on a larger GPT, three seeds.   # @from 11.06

    python3 -m experiments.benchmark

The recorded benchmark (experiments/recorded/benchmark/) is this
script with bigger settings and every row (NOTES.md has the command and
its time).
"""

import glob
import json
import os

import numpy as np
import torch

import lab
from data import shakespeare
from experiments.language import race
from experiments.sequences import bits, windows
from lab import bench
from models.gpt import GPT
from models.gpt import Rotary                                                       # @from 11.02

CONFIG = dict(layers=4, heads=4, width=64, context=64, kv_heads=2, batch=32, steps=400, lr=0.003, warmup=50,
              weight_decay=0.1, clip=1.0, every=10, held=32, target=3.0, seeds=2, rows=["baseline", "half the batch"],
              repeats=5, number=5, rounds=3,
              recorded="experiments/recorded/benchmark",                           # @from 11.06
              device="cpu")
ALL_FOUR = dict(norm="rms", positions="rotary", mlp="swiglu")
KEEP = {"angles kept"}                                                              # @from 11.02
KEEP.add("all together")                                                            # @from 11.05


# @build 11.01 rows
# The rows a benchmark can run: for each, what it changes in the model
# (GPT's arguments) and in the training settings. The baseline is the
# model as module 10 left it; each later lesson adds its row.
def rows(cfg):
    return {
        "baseline": ({}, {}),
        "half the batch": ({}, {"batch": cfg.batch // 2}),
        "angles kept": ({}, {}),                                                    # @from 11.02
        "fused attention": ({"fused": True}, {}),                                   # @from 11.03
        "bfloat16": ({}, {"precision": "bfloat16"}),                                # @from 11.04
        "twice the batch and rate": ({}, {"batch": 2 * cfg.batch, "lr": 2 * cfg.lr}),  # @from 11.05
        "all together": ({"fused": True}, {"batch": 2 * cfg.batch, "lr": 2 * cfg.lr}),  # @from 11.05
    }
# @end


def label(name):
    return name.replace(" ", "-")


# @build 11.01 board
# One line a row: the seconds to the target over seeds (lab.spread), the
# steps, the ratio of its mean seconds to the first row's with Welch's t,
# and ms a step and tokens a second. got: {name: race's result}.
def board(got):
    base = [s for s in next(iter(got.values()))["seconds"] if s is not None]
    lines = [f"   {'':26s} {'seconds to the target':48s} {'steps':>6s} {'against the first':>18s} {'ms a step':>10s} "
             f"{'tokens a second':>16s}"]
    for i, (name, r) in enumerate(got.items()):
        seconds = [s for s in r["seconds"] if s is not None]
        steps = [s for s in r["steps"] if s is not None]
        if not seconds:
            lines.append(f"   {name:26s} not reached in {len(r['seconds'])} seeds; ms a step {lab.mean(r['ms']):.1f}")
            continue
        ratio = lab.mean(seconds) / lab.mean(base) if base else float("nan")
        t = lab.welch_t(seconds, base) if i and len(seconds) > 1 and len(base) > 1 else 0.0
        against = f"x{ratio:.2f} (t {t:+5.1f})" if i and base else ""
        ms = lab.mean(r["ms"])
        lines.append(f"   {name:26s} {lab.spread(seconds, 3):48s} {lab.mean(steps):6.0f} "
                     f"{against:>18s} {ms:10.1f} {1000 * r['tokens'] / ms:16,.0f}"
                     + ("" if len(seconds) == len(r["seconds"]) else f"  ({len(seconds)} of {len(r['seconds'])} seeds)"))
    return "\n".join(lines)
# @end


def step_timer(model, cfg, dev, ids):
    """One training step of model as train takes it (a batch from random places, bits, AdamW, clipping), as a
    function of no arguments, for bench.timings."""
    opt = torch.optim.AdamW(model.parameters(), lr=cfg.lr)
    rng = np.random.default_rng(0)

    def step():
        starts = torch.from_numpy(rng.integers(0, len(ids) - cfg.context, cfg.batch)).to(dev)
        x, y = windows(ids, starts, cfg.context)
        loss = bits(model(x), y)
        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), cfg.clip)
        opt.step()
    return step


def recorded(where):
    """The recorded benchmark: each row's races as race returns them (from every seed's summary.json and
    times.json), and its config; or None."""
    if not os.path.isfile(os.path.join(where, "times.json")):
        return None
    with open(os.path.join(where, "times.json")) as f:
        times = json.load(f)
    got, config = {}, None
    for name, t in times.items():
        runs = sorted(glob.glob(os.path.join(where, label(name), "seed*", "summary.json")))
        summaries = []
        for path in runs:
            with open(path) as f:
                summaries.append(json.load(f))
        with open(os.path.join(os.path.dirname(runs[0]), "config.json")) as f:
            c = json.load(f)
        config = config or c
        got[name] = {"seconds": t["seconds"], "ms": t["ms"], "steps": [s["steps_to_target"] for s in summaries],
                     "bits": [s["held_bits"] for s in summaries], "tokens": c["batch"] * c["context"]}
    return got, config


def main():
    cfg = lab.config(CONFIG)
    dev = lab.device(torch, cfg.device)
    clock = lambda: lab.clock(torch, dev)                                            # noqa: E731
    V = len(shakespeare.chars())
    train_t, val_t = (torch.from_numpy(shakespeare.split(s)).to(dev) for s in ("train", "val"))
    start = clock()
    common = dict(vocab=V, context=cfg.context, layers=cfg.layers, heads=cfg.heads, width=cfg.width,
                  kv_heads=cfg.kv_heads, **ALL_FOUR)

    torch.manual_seed(0)
    model = GPT(**common).to(dev)
    step = step_timer(model, cfg, dev, train_t)
    cold = bench.timings(step, clock, repeats=1, warmup=0)[0]
    print(f"1. One training step of 10.05's \"all four\" GPT ({cfg.layers} blocks of {cfg.heads} heads, width "
          f"{cfg.width}, {cfg.kv_heads} key/value heads),\n   {cfg.batch} windows of {cfg.context} characters "
          f"({cfg.batch * cfg.context:,} tokens), on {dev.type} with {torch.get_num_threads()} threads.\n"
          f"   The first step of the process: {1000 * cold:.1f} ms (load {bench.load_average():.1f})")
    every = []
    for r in range(cfg.rounds):
        got = bench.timings(step, clock, repeats=cfg.repeats, warmup=1, number=cfg.number)
        every += got
        print(f"   round {r + 1}, {cfg.repeats} timings of {cfg.number} steps, ms a step: "
              + " ".join(f"{1000 * s:.1f}" for s in got) + f"\n   {'':9s}{bench.spread_ms(got, bench.load_average())}")
    best = min(every)
    print(f"   all {len(every)}: {bench.spread_ms(every)}; the largest is {max(every) / best:.2f} times the "
          f"smallest\n   tokens a second at the smallest: {cfg.batch * cfg.context / best:,.0f}")

    held = windows(val_t, torch.from_numpy(np.random.default_rng(0).integers(0, len(val_t) - cfg.context, cfg.held))
                   .to(dev), cfg.context)
    print(f"\n2. Time to {cfg.target} bits per character on {cfg.held} validation windows (scored every {cfg.every} "
          f"steps, untimed), at most\n   {cfg.steps} steps, AdamW {cfg.lr}, warmup {cfg.warmup} then a cosine over "
          f"{cfg.steps} steps; {cfg.seeds} seeds a row (load {bench.load_average():.1f}):\n")
    table, got = rows(cfg), {}
    for name in cfg.rows:
        changes, settings = table[name]
        Rotary.keep = name in KEEP                                                  # @from 11.02
        got[name] = race(changes, common, lab.Config({**cfg, **settings}), dev, train_t, held, label=label(name))
    Rotary.keep = True                                                              # @from 11.02
    print(board(got))
    print("\n   seed by seed, steps and seconds to the target:")
    for name, r in got.items():
        print(f"   {name:26s} " + "   ".join(f"{n:.0f}, {t:.1f} s" if t is not None else "not reached"
                                              for n, t in zip(r["steps"], r["seconds"])))
    folder = os.path.join(cfg.out, cfg.name)
    with open(os.path.join(folder, "times.json"), "w") as f:
        json.dump({n: {"seconds": [round(s, 3) if s is not None else None for s in r["seconds"]],
                       "ms": [round(m, 2) for m in r["ms"]]} for n, r in got.items()}, f, indent=1)
        f.write("\n")
    curves = []
    for i, (name, r) in enumerate(got.items()):
        log = lab.read_log(os.path.join(folder, label(name), "seed0"))
        ms = r["ms"][0]
        curves.append(lab.Line(name, [(row["step"] + 1) * ms / 1000 for row in log], [row["held_bits"] for row in log],
                               i, 0.8))
    path = lab.lines(os.path.join(folder, "curves.svg"), curves, title="bits per character on validation windows, "
                     "seed 0", xlabel="seconds of training (steps times ms a step)", ylabel="bits per character")
    print(f"   curves in {path}")

    # @from 11.06
    have = recorded(cfg.recorded) if cfg.recorded != "none" else None
    if have is None and cfg.recorded != "none":
        print(f"\n3. No recorded benchmark in {cfg.recorded}.")
    elif have is not None:
        rec, c = have
        print(f"\n3. The recorded benchmark ({cfg.recorded}): {c['layers']} blocks of {c['heads']} heads, width "
              f"{c['width']}, windows of {c['context']}, batches of {c['batch']};\n   time to {c['target']} bits on "
              f"{c['held']} validation windows, at most {c['steps']} steps, {c['seeds']} seeds a row, on the CPU it was "
              f"run on:\n")
        print(board(rec))
    # @end
    print(f"\n{clock() - start:.0f} s of timing and training on {dev.type}")


if __name__ == "__main__":
    main()
