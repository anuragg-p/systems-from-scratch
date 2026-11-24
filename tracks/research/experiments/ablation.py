"""Which change paid: an ablation table.

Module 10 changed 08's GPT one paper at a time: RMSNorm (10.01), rotary
positions (10.02), SwiGLU (10.03), grouped-query attention (10.04). Each
lesson set one change against the piece it replaced. An ablation asks it
of all of them at once, on one footing: the base model, each change
alone, and all four together, with the same data, the same steps and the
same seeds for every row. A row's difference from the base counts only
when it is wide next to the spread over seeds (Welch's t).

1. The table of the short run (the default, under a minute): rows of a
   small GPT trained briefly. It can tell a change that pays a lot early
   from the rest; most differences here are inside the noise.
2. The table of the recorded long run (experiments/recorded/ablation/, its
   config.json files hold every setting): a larger GPT trained far longer,
   3 seeds a row; and beside each change, what its paper claimed and at
   what size.

    python3 -m experiments.ablation

The long run is this script with bigger settings (NOTES.md has the command
and its time, about an hour on a laptop's CPU).
"""

import glob
import json
import os

import numpy as np
import torch

import lab
from data import shakespeare
from experiments.language import compare
from experiments.sequences import windows

CONFIG = dict(layers=4, heads=4, width=64, context=64, batch=32, steps=100, lr=0.003, warmup=50, weight_decay=0.1,
              clip=1.0, every=25, held=32, seeds=2, kv_heads=2, recorded="experiments/recorded/ablation", device="cpu")

# What each paper claimed, and at what size (read at the sources; NOTES.md has the quotes).
CLAIMS = {
    "RMSNorm": "Zhang and Sennrich (2019): \"comparable performance\" to layer norm, \"7%~64%\" less time; a "
               "Transformer base on WMT14 English-German, 26.8 BLEU against 26.6, 6.9% faster (TensorFlow, a V100)",
    "rotary": "Su et al. (2021): \"faster convergence\" than BERT's learned positions in pre-training (a figure, no "
              "numbers); 27.5 BLEU against 27.3 on WMT14 English-German",
    "SwiGLU": "Shazeer (2020): log-perplexity 1.944 against GELU's 1.983 after 65,536 steps (a T5 base of 12 + 12 "
              "layers, d_model 768, on C4), parameters and computation matched",
    "grouped-query": "Ainslie et al. (2023): \"quality close to multi-head attention\" with less to read when "
                     "writing; T5-XXL uptrained, average 47.1 (8 groups) against 47.2 (every head)",
}


def variants(cfg):
    return {"base (08)": {}, "RMSNorm": {"norm": "rms"}, "rotary": {"positions": "rotary"}, "SwiGLU": {"mlp": "swiglu"},
            "grouped-query": {"kv_heads": cfg.kv_heads},
            "all four": {"norm": "rms", "positions": "rotary", "mlp": "swiglu", "kv_heads": cfg.kv_heads}}


def label(name):
    return name.replace(" (08)", "").replace(" ", "-")


# @build 10.05 table
# One row a variant: its weights, its bits per character over seeds
# (lab.spread), the difference of its mean from the first row's with
# Welch's t, whether that is beyond the noise (|t| of 3 or more), and its
# ms a training step over seeds (when times are given). rows: {name:
# {"bits": [...], "weights": n}}, the first the base; times: {name: [...]}.
def table(rows, times=None):
    base = next(iter(rows.values()))["bits"]
    lines = [f"   {'':14s} {'weights':>9s}   {'bits per character':50s} {'against the base':>17s}   "
             f"{'beyond noise':13s} {'ms a step' if times else ''}"]
    for name, r in rows.items():
        diff = lab.mean(r["bits"]) - lab.mean(base)
        t = lab.welch_t(r["bits"], base) if r["bits"] is not base else 0.0
        against = f"{diff:+.4f} (t {t:+5.1f})" if r["bits"] is not base else ""
        beyond = ("yes" if abs(t) >= 3 else "no") if r["bits"] is not base else ""
        ms = f"{lab.mean(times[name]):.1f}" if times and name in times else ""
        lines.append(f"   {name:14s} {r['weights']:9,d}   {lab.spread(r['bits'], 4):50s} {against:>17s}   {beyond:13s} {ms}")
    return "\n".join(lines)
# @end


def recorded(where, names):
    """The recorded long run's rows (from each seed's summary.json), its config and its times, or None."""
    if not os.path.isdir(where):
        return None
    rows, config = {}, None
    for name in names:
        runs = sorted(glob.glob(os.path.join(where, label(name), "seed*", "summary.json")))
        if not runs:
            return None
        got = []
        for path in runs:
            with open(path) as f:
                got.append(json.load(f))
        rows[name] = {"bits": [s["test_bits"] for s in got], "weights": got[0]["weights"]}
        with open(os.path.join(os.path.dirname(runs[0]), "config.json")) as f:
            config = json.load(f)
    times = None
    if os.path.isfile(os.path.join(where, "times.json")):
        with open(os.path.join(where, "times.json")) as f:
            times = json.load(f)
    return rows, config, times


def main():
    cfg = lab.config(CONFIG)
    dev = lab.device(torch, cfg.device)
    V = len(shakespeare.chars())
    train_t, val_t, test_t = (torch.from_numpy(shakespeare.split(s)).to(dev) for s in ("train", "val", "test"))
    start = lab.clock(torch, dev)

    held = windows(val_t, torch.from_numpy(np.random.default_rng(0).integers(0, len(val_t) - cfg.context, cfg.held))
                   .to(dev), cfg.context)
    common = dict(vocab=V, context=cfg.context, layers=cfg.layers, heads=cfg.heads, width=cfg.width)
    runs = {label(n): v for n, v in variants(cfg).items()}
    got = compare(runs, common, cfg, dev, train_t, test_t, held)
    rows = {n: got[label(n)] for n in variants(cfg)}
    times = {n: r["ms"] for n, r in rows.items()}
    os.makedirs(os.path.join(cfg.out, cfg.name), exist_ok=True)
    with open(os.path.join(cfg.out, cfg.name, "times.json"), "w") as f:
        json.dump({n: [round(t, 2) for t in ms] for n, ms in times.items()}, f, indent=1)
        f.write("\n")
    curves = []
    for i, (name, r) in enumerate(rows.items()):
        logs = [lab.read_log(os.path.join(cfg.out, cfg.name, label(name), f"seed{s}")) for s in range(cfg.seeds)]
        steps = [row["step"] for row in logs[0]]
        mean = [lab.mean([log[j]["held_bits"] for log in logs]) for j in range(len(steps))]
        curves.append(lab.Line(name, steps, mean, i, 0.8))
    path = lab.lines(f"{cfg.out}/{cfg.name}/curves.svg", curves, title="bits per character on validation windows, "
                     "mean over seeds", xlabel="step", ylabel="bits per character")
    passes = cfg.steps * cfg.batch * cfg.context / len(train_t)
    print(f"1. This run: {cfg.layers} blocks of {cfg.heads} heads, width {cfg.width}, windows of {cfg.context}; "
          f"{cfg.steps} steps of {cfg.batch} ({passes:.2f} passes over the\n   training text), AdamW {cfg.lr}; "
          f"{cfg.seeds} seeds a row; grouped-query: {cfg.kv_heads} key/value heads for {cfg.heads}. Bits per "
          f"character on the test\n   text (each character with {cfg.context // 4} or more before it):\n")
    print(table(rows, times))
    print(f"\n   curves in {path}")

    have = recorded(cfg.recorded, list(rows))
    if have is None:
        print(f"\n2. No recorded long run in {cfg.recorded}.")
    else:
        rec, c, rec_times = have
        passes = c["steps"] * c["batch"] * c["context"] / len(train_t)
        print(f"\n2. The recorded long run ({cfg.recorded}): {c['layers']} blocks of {c['heads']} heads, width "
              f"{c['width']}, windows of {c['context']}; {c['steps']} steps of\n   {c['batch']} ({passes:.1f} passes), "
              f"AdamW {c['lr']}, warmup {c['warmup']}; {c['seeds']} seeds a row; grouped-query: {c['kv_heads']} "
              f"key/value heads for {c['heads']}.\n   Bits per character on the test text (each character with "
              f"{c['context'] // 4} or more before it), ms a step on the CPU it was run on:\n")
        print(table(rec, rec_times))
        print("\n   What each paper claimed, and at what size:")
        for name, claim in CLAIMS.items():
            print(f"   {name}: {claim}")
    print(f"\n{lab.clock(torch, dev) - start:.0f} s of training and scoring on {dev.type}")


if __name__ == "__main__":
    main()
