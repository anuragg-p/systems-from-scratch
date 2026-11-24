"""Error bars: is the difference real? 08.02's four heads against one, measured until it is decided.

08.02 found four heads of 16 a little better than one head of 64 at the
same weights (4 blocks, width 64, no positions): 3.407 against 3.433 bits
per character on the test text, t = -2.4 at 3 seeds, and inside the noise
at 2. Here, the same models, the same seeds:

1. The two arms, a few seeds each, and 08.02's comparison again.
2. Each mean with its standard error and an interval: Student's t at the
   seeds there are, beside the normal's 1.96; and by the bootstrap.
3. The difference, as two independent sets of runs and as pairs: one seed
   gives both arms the same starting weights (their shapes are the same)
   and the same batches, so the pairs' differences leave out what a seed
   does to both.
4. The other noise: the test text is a sample of Shakespeare too. Each
   model's score is a mean over the test positions; its standard error,
   counted with neighbours moving together, beside the spread over seeds.
5. How many seeds a difference needs at the spread measured.
6. The recorded run (experiments/recorded/errorbars: the same at 10 seeds a
   side), read: the verdict, and how often a few of its seeds would have
   given it.

    python3 -m experiments.errorbars
"""

import json
import math
import os
from statistics import NormalDist

import numpy as np
import torch
import torch.nn.functional as F

import lab
from data import shakespeare
from experiments.language import train
from experiments.sequences import window_bits, windows
from models.gpt import GPT

CONFIG = dict(width=64, context=32, batch=32, steps=300, lr=0.003, warmup=50, weight_decay=0.1, clip=1.0, every=100,
              seeds=3, layers=4, heads=4, level=0.95, resamples=10000, batches=[1, 4, 16, 64, 256], honest=64,
              sizes=[0.01, 0.026, 0.05], subsets=[2, 3, 5], recorded="experiments/recorded", device="cpu")


# @build 13.02 position_bits
# window_bits' score, position by position: the bits of every position it
# counts (the same windows: spans of `span` positions, each read with
# `warm` symbols before it), in the order of the text, as a numpy array of
# float64. Their mean is window_bits; their spread is what a standard error
# of that mean needs.
def position_bits(predict, ids, span, warm, batch=64):
    firsts = list(range(0, len(ids) - warm, span))
    length = warm - 1 + span
    full = [s for s in firsts if s + length < len(ids)]
    groups = [full[i:i + batch] for i in range(0, len(full), batch)] + [[s] for s in firsts if s not in full]
    out = []
    with torch.no_grad():
        for group in groups:
            x, y = windows(ids, torch.tensor(group, device=ids.device), min(length, len(ids) - 1 - group[0]))
            scores, y = predict(x)[:, warm - 1:], y[:, warm - 1:]
            nats = F.cross_entropy(scores.reshape(-1, scores.shape[-1]), y.reshape(-1), reduction="none")
            out.append((nats / math.log(2)).double().cpu().numpy())
    return np.concatenate(out)
# @end


def build(heads, cfg, V, dev):
    """08.02's GPT of cfg.layers blocks, no positions, with `heads` heads."""
    return GPT(V, cfg.context, cfg.layers, heads, cfg.width, positions=False).to(dev)


def read(directory):
    """A recorded run's test bits: {heads: [bits by seed]}, and its settings."""
    out, cfg = {}, None
    for label in sorted(os.listdir(directory)):
        if not label.startswith("heads"):
            continue
        seeds = sorted(int(s[4:]) for s in os.listdir(os.path.join(directory, label)) if s.startswith("seed"))
        for seed in seeds:
            with open(os.path.join(directory, label, f"seed{seed}", "summary.json")) as f:
                out.setdefault(int(label[5:]), []).append(json.load(f)["test_bits"])
        if cfg is None:
            with open(os.path.join(directory, label, "seed0", "config.json")) as f:
                cfg = lab.Config(json.load(f))
    return out, cfg


def clear_share(diffs, k, level, draws):
    """The share of `draws` sets of k of the paired differences (drawn without putting back, rng 1) whose interval
    is clear of 0."""
    rng = np.random.default_rng(1)
    clear = 0
    for _ in range(draws):
        lo, hi = lab.interval([diffs[i] for i in rng.choice(len(diffs), k, replace=False)], level)
        clear += hi < 0 or lo > 0
    return clear / draws


def describe(one, many, cfg, rng):
    """Parts 2, 3 and 5 for two arms of paired runs (lists by seed)."""
    n = len(one)
    level = cfg.level
    t, z = lab.t_quantile((1 + level) / 2, n - 1), NormalDist().inv_cdf((1 + level) / 2)
    print(f"   {'':16s}{'mean':>8s}{'sem':>9s}   {level:.0%} interval, t {t:.2f}   with {z:.2f} instead     bootstrap")
    for name, xs in (("1 head", one), (f"{cfg.heads} heads", many)):
        lo, hi = lab.interval(xs, level)
        blo, bhi = lab.bootstrap([xs], np.mean, rng, cfg.resamples, level)
        m, s = lab.mean(xs), lab.sem(xs)
        print(f"   {name:16s}{m:8.4f}{s:9.4f}   {lo:.4f} to {hi:.4f}     {m - z * s:.4f} to {m + z * s:.4f}"
              f"   {blo:.4f} to {bhi:.4f}")
    d, ulo, uhi = lab.difference(many, one, paired=False, level=level)
    _, plo, phi = lab.difference(many, one, paired=True, level=level)
    diffs = [a - b for a, b in zip(many, one)]
    blo, bhi = lab.bootstrap([diffs], np.mean, rng, cfg.resamples, level)
    r = float(np.corrcoef(one, many)[0, 1])
    print(f"\n   {cfg.heads} heads minus 1 head: {d:+.4f} bits per character")
    print(f"   as two independent sets (Welch):  {ulo:+.4f} to {uhi:+.4f}, width {uhi - ulo:.4f}")
    print(f"   as pairs, seed by seed:           {plo:+.4f} to {phi:+.4f}, width {phi - plo:.4f}   "
          f"(bootstrap of the pairs {blo:+.4f} to {bhi:+.4f})")
    print(f"   the two arms' runs move together over seeds: correlation {r:+.2f}; the pairs' differences "
          f"{lab.spread(diffs, 3)}")
    print(f"   {cfg.heads} heads lower on {sum(x < 0 for x in diffs)} of {n} seeds")
    return d, diffs


def main():
    cfg = lab.config(CONFIG)
    dev = lab.device(torch, cfg.device)
    V = len(shakespeare.chars())
    train_t, test_t = (torch.from_numpy(shakespeare.split(s)).to(dev) for s in ("train", "test"))
    start = lab.clock(torch, dev)
    warm = cfg.context // 2
    span = cfg.context - warm + 1
    rng = np.random.default_rng(0)

    scores, positions, starts = {}, {}, []
    for heads in (1, cfg.heads):
        for seed in range(cfg.seeds):
            run = lab.Run(cfg, seed, label=f"heads{heads}")
            torch.manual_seed(seed)
            model = build(heads, cfg, V, dev)
            if seed == 0:
                starts.append({k: v.clone() for k, v in model.state_dict().items()})
            train(model, cfg, run, dev, train_t)
            model.eval()
            bits = position_bits(model, test_t, span, warm)
            run.finish(test_bits=float(bits.mean()), test_sem=lab.batch_sem(bits, cfg.honest * span))
            scores.setdefault(heads, []).append(float(bits.mean()))
            if seed == 0:
                positions[heads] = bits
    one, many = scores[1], scores[cfg.heads]
    same = all(torch.equal(starts[0][k], starts[1][k]) for k in starts[0])
    print(f"1. 08.02's models: {cfg.layers} blocks, width {cfg.width}, no positions, 1 head of {cfg.width} against "
          f"{cfg.heads} heads of {cfg.width // cfg.heads};\n   {cfg.steps} steps of {cfg.batch} windows of {cfg.context}, "
          f"seeds 0 to {cfg.seeds - 1}. Bits per character on the test text ({len(positions[1]):,} positions):")
    print(f"   1 head    {lab.spread(one, 4)}\n   {cfg.heads} heads   {lab.spread(many, 4)}\n   t = "
          f"{lab.welch_t(many, one):+.1f}   (one seed starts both arms from the same weights: {same}; and the same "
          f"batches)")

    print("\n2 and 3. The means, and the difference:")
    describe(one, many, cfg, rng)
    path = lab.lines(f"{cfg.out}/{cfg.name}/pairs.svg", [lab.Line(f"seed {s}", [1, cfg.heads], [one[s], many[s]], s)
                                                         for s in range(cfg.seeds)],
                     xlabel="heads", ylabel="bits per character, test text")
    print(f"   each seed's two runs, joined, in {path}")

    print(f"\n4. The test text as a sample (seed 0's models): the standard error of the mean over the test positions, "
          f"the positions\n   taken in consecutive batches of so many windows ({span} positions a window):")
    print(f"   {'windows a batch':>16s}" + "".join(f"{b:>9d}" for b in cfg.batches))
    pair = positions[cfg.heads] - positions[1]
    for name, xs in (("1 head", positions[1]), (f"{cfg.heads} heads", positions[cfg.heads]),
                     (f"{cfg.heads} minus 1", pair)):
        print(f"   {name:>16s}" + "".join(f"{lab.batch_sem(xs, b * span):9.4f}" for b in cfg.batches))
    honest = lab.batch_sem(positions[1], cfg.honest * span)
    print(f"   Over seeds, one model's score moves by sd {lab.sd(one):.4f} (1 head) and {lab.sd(many):.4f} ({cfg.heads} "
          f"heads); the test text's own sampling error, {honest:.4f} (batches of {cfg.honest} windows).\n   For the "
          f"difference on the same text it is {lab.batch_sem(pair, cfg.honest * span):.4f}, against the spread of the "
          f"seeds' differences, {lab.sd([x - y for x, y in zip(many, one)]):.4f}.")

    sd_one = math.sqrt((lab.sd(one) ** 2 + lab.sd(many) ** 2) / 2)
    sd_pair = lab.sd([x - y for x, y in zip(many, one)])
    print(f"\n5. Seeds a side for a difference to show (its {cfg.level:.0%} interval clear of 0 four times in five), at "
          f"this run's spread\n   (each arm's sd {sd_one:.4f}; the pairs' differences' {sd_pair:.4f}):")
    print(f"   {'difference':>12s}{'independent':>13s}{'paired':>8s}")
    for size in cfg.sizes:
        print(f"   {size:12.3f}{lab.seeds_needed(size, sd_one, cfg.level):13d}"
              f"{lab.seeds_needed(size, sd_pair, cfg.level, paired=True):8d}")

    recorded = os.path.join(cfg.recorded, "errorbars")
    if os.path.isdir(recorded) and os.path.abspath(recorded) != os.path.abspath(f"{cfg.out}/{cfg.name}"):
        rec, rcfg = read(recorded)
        r_one, r_many = rec[1], rec[rcfg.heads]
        print(f"\n6. The recorded run ({recorded}): the same, seeds 0 to {len(r_one) - 1}.")
        print(f"   1 head    {lab.spread(r_one, 4)}\n   {rcfg.heads} heads   {lab.spread(r_many, 4)}\n   t = "
              f"{lab.welch_t(r_many, r_one):+.1f}")
        d, diffs = describe(r_one, r_many, cfg, rng)
        _, lo, hi = lab.difference(r_many, r_one, paired=True, level=cfg.level)
        said = (f"{rcfg.heads} heads lower" if hi < 0 else "1 head lower" if lo > 0 else "not decided")
        print(f"   The verdict at {len(r_one)} seeds, paired: {said}.")
        half = len(r_one) // 2
        print(f"   One arm against itself, its first {half} seeds against the next {half} (Henderson et al.'s test): "
              + ", ".join(f"{name} t = {lab.welch_t(xs[:half], xs[half:2 * half]):+.1f}"
                          for name, xs in (("1 head", r_one), (f"{rcfg.heads} heads", r_many))))
        sd_rec = lab.sd(diffs)
        print(f"   seeds_needed for {abs(d):.4f} at the pairs' sd {sd_rec:.4f}, four times in five: "
              f"{lab.seeds_needed(abs(d), sd_rec, cfg.level, paired=True)}. How often n of these {len(diffs)} seeds, "
              f"drawn at\n   random (2000 draws), give a paired {cfg.level:.0%} interval clear of 0: " + ", ".join(
                  f"n = {k}: {share:.2f}" for k, share in ((k, clear_share(diffs, k, cfg.level, 2000)) for k in
                                                         cfg.subsets if k < len(diffs))))
    print(f"\n{lab.clock(torch, dev) - start:.0f} s of training and scoring on {dev.type}")


if __name__ == "__main__":
    main()
