"""The question, the predictions, and a pilot that sizes the experiment (15.01).

Before the experiment runs, two things it needs are not known: how far
the gap between the two arms moves from seed to seed, which says how many
seeds the experiment needs, and how long a run takes, which says whether
it fits the hour. A pilot is a small run made to find them out. Here:

1. The question and the predictions, from experiments/question.py, each
   with the rule that will decide it: written down before any run.
2. The pilot: GPTs of a few depths, without positions and with learned
   positions, each pair from one seed (question.pair), at 08.03's rate,
   scored on the validation text only: the test text is kept for the
   experiment's final numbers.
3. The seeds: how many pairs show a gap of question.SMALLEST four times
   in five (13.02's seeds_needed), from the spread of the pilot's gaps;
   and how many it would be if the arms were not paired.
4. The budget: the minutes the experiment's plan takes at the times the
   pilot measured.
5. The recorded pilot (experiments/recorded/pilot, the depths that bound
   the plan), read: the same, and the number of seeds it fixed.

    python3 -m experiments.pilot
"""

import os

import torch

import lab
from data import shakespeare
from experiments import question as q

CONFIG = dict(width=64, context=32, heads=4, batch=32, steps=300, lr=0.003, warmup=50, weight_decay=0.1, clip=1.0,
              every=100, depths=[1, 2], seeds=3, plan_depths=[1, 2, 4, 6, 8], plan_rates=4,
              recorded="experiments/recorded", device="cpu")


def texts(dev):
    """The three parts of the text, each one tensor on the device."""
    return {s: torch.from_numpy(shakespeare.split(s)).to(dev) for s in ("train", "val", "test")}


def describe(runs, depths, seconds=None):
    """The pilot's table, from {(depth, arm): [validation bits by seed]}; the largest sd of a depth's gaps."""
    worst = 0.0
    for d in depths:
        none, learned = runs[d, "none"], runs[d, "learned"]
        gaps = [a - b for a, b in zip(none, learned, strict=True)]
        worst = max(worst, lab.sd(gaps))
        time = f"   {seconds[d]:.1f} s a run" if seconds else ""
        name = f"{d} block{'s' * (d > 1)}"
        print(f"   {name:10s}none      {lab.spread(none, 4)}\n"
              f"   {'':10s}learned   {lab.spread(learned, 4)}\n"
              f"   {'':10s}the gap   {lab.spread(gaps, 3)}{time}")
    return worst


def decide(worst, arm_sd):
    """The number of seeds, paired, at the pilot's spread (at least 3); and unpaired, for comparison."""
    paired = max(3, lab.seeds_needed(q.SMALLEST, worst, q.LEVEL, q.POWER, paired=True))
    return paired, lab.seeds_needed(q.SMALLEST, arm_sd, q.LEVEL, q.POWER)


def main():
    cfg = lab.config(CONFIG)
    dev = lab.device(torch, cfg.device)
    V = len(shakespeare.chars())
    data = texts(dev)
    start = lab.clock(torch, dev)

    print(f"1. The question: {q.QUESTION}\n   It comes from 08.03: at {q.BEFORE['blocks']} blocks, {q.BEFORE['none']} "
          f"bits per character without positions against {q.BEFORE['learned']} with them, a gap of "
          f"{q.BEFORE['gap']}.\n   The predictions, written down before any run, and the rule that decides each:")
    for p in q.PREDICTIONS:
        print(f"   {p.key:20s} {p.says}\n   {'':20s} ({q.rule_text(p.rule)})")

    runs, seconds = {}, {}
    for seed in range(cfg.seeds):
        for d in cfg.depths:
            for arm, model in q.pair(V, cfg, d, seed, dev).items():
                run = lab.Run(cfg, seed, label=f"blocks{d}-{arm}")
                t = lab.clock(torch, dev)
                got = q.trained(model, cfg, run, dev, data)
                seconds.setdefault(d, []).append(lab.clock(torch, dev) - t)
                runs.setdefault((d, arm), []).append(got["val_bits"])
    seconds = {d: lab.mean(s) for d, s in seconds.items()}
    print(f"\n2. The pilot: {cfg.seeds} pairs at each depth, {cfg.steps} steps at lr {cfg.lr:g} (08.03's), bits per "
          f"character on the validation text (each character with {cfg.context // 2} or more before it):")
    worst = describe(runs, cfg.depths, seconds)
    arm_sd = max(lab.sd(xs) for xs in runs.values())
    n, unpaired = decide(worst, arm_sd)
    print(f"\n3. The seeds: a gap of {q.SMALLEST} clear of 0 ({q.LEVEL:.0%} interval) {q.POWER:.0%} of the time, at the "
          f"largest sd of a depth's gaps, {worst:.4f}:\n   {n} pairs (13.02's seeds_needed, paired; at least 3). "
          f"Unpaired, at the largest sd of one arm, {arm_sd:.4f}: {unpaired} a side.")
    minutes, per = lab_budget(seconds, cfg, n)
    print(f"\n4. The budget: {cfg.plan_rates} rates on one seed and {n} fresh seeds, both arms, at depths "
          f"{', '.join(map(str, cfg.plan_depths))},\n   and {n} runs of the control at 4 blocks: about {minutes:.0f} "
          f"minutes at the times measured now (a run: " +
          ", ".join(f"{d} block{'s' * (d > 1)} {s:.0f} s" for d, s in per.items()) + ")")

    recorded = os.path.join(cfg.recorded, "pilot")
    if os.path.isdir(recorded) and os.path.abspath(recorded) != os.path.abspath(f"{cfg.out}/{cfg.name}"):
        rec = q.read_runs(recorded)
        rcfg = lab.Config(next(iter(rec.values()))[0][0])
        rruns = {(int(label[6:].split("-")[0]), label.split("-")[1]): [s["val_bits"] for _, s in seeds]
                 for label, seeds in rec.items()}
        print(f"\n5. The recorded pilot ({recorded}): {rcfg.seeds} pairs at depths "
              f"{', '.join(map(str, rcfg.depths))}, {rcfg.steps} steps at lr {rcfg.lr:g}:")
        rworst = describe(rruns, rcfg.depths)
        rn, runpaired = decide(rworst, max(lab.sd(xs) for xs in rruns.values()))
        print(f"   The largest sd of a depth's gaps, {rworst:.4f}: {rn} pairs, fixed before the experiment ran "
              f"(unpaired: {runpaired} a side).")
    print(f"\n{lab.clock(torch, dev) - start:.0f} s of training and scoring on {dev.type}")


def lab_budget(seconds, cfg, n):
    """question.budget for the plan, and the control's runs (one arm, 4 blocks) on top."""
    minutes, per = q.budget(seconds, cfg.plan_depths, cfg.plan_rates + n)
    control = q.budget(seconds, [4], n, arms=1)[0]
    return minutes + control, per


if __name__ == "__main__":
    main()
