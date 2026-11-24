"""A hypothesis, and a baseline tuned as hard as your method: 03.03's race again, run fairly.

03.03 put Adam against SGD with Nesterov momentum on MNIST and found a tie
at laptop size. A hurried paper gets a clear win out of the same two
optimisers: it searches for the learning rate of its own method and runs
the baseline at a rate it did not search for. Here, on the network of
03.03 (784-256-256-10, pixels 0..1), the first n_train training images,
a few passes:

1. The hypothesis, and the rule that will decide it, written down before
   any run.
2. The search: the same number of trials for each optimiser, the same
   draws mapped into each one's range of learning rates (two decades
   about where each is known to work), every trial on seed 0, chosen on
   validation (the last n_val training images, never trained on); the
   test images are only ever reported.
3. The hurried comparison: Adam at the rate its search chose, SGD at the
   rate PyTorch's documentation shows it with (lr=0.01, momentum=0.9),
   each on fresh seeds (the winner's own trial was chosen for being
   lucky on seed 0, so it is not reported).
4. The fair one: SGD at the rate its search chose, on the same fresh seeds.
5. What a larger search buys: the expected best of n trials, n = 1 to
   trials, worked out from the trials made (lab's best_of), for each.

    python3 -m experiments.baseline          (needs MNIST: python3 -m data.fetch mnist)
"""

import math

import numpy as np
import torch

import lab
from data import mnist
from experiments.images import evaluate, tensors, train_epoch
from experiments.loop import mlp

CONFIG = dict(n_train=10000, n_val=10000, hidden=256, epochs=2, batch=128, trials=8, seeds=5, search_seed=0,
              adam=[1e-4, 1e-2], nesterov=[3e-3, 3e-1], momentum=0.9, default_lr=0.01, standardise=False,
              device="cpu")

# Written before the search was run, and printed first by every run.
HYPOTHESIS = ("Adam reaches a lower test error than SGD with Nesterov momentum 0.9 on this network after the same "
              "passes, when each optimiser's learning rate is found by the same search.")
RULE = ("Held if Adam's test error over the fresh seeds is below SGD's with |t| of 3 or more (Welch's t, 00.03); "
        "the reverse if SGD's is below by as much; a tie otherwise.")


# @build 13.01 draw_rates
# The search's trials: `trials` learning rates for each optimiser, from
# its range (low, high), log-uniform: low (high / low)^u for u uniform in
# [0, 1). One draw of the u's (rng, a numpy Generator) serves every
# optimiser, so each search is the same search, put into its own range.
# A dict {name: [rates]}.
def draw_rates(ranges, trials, rng):
    u = rng.random(trials)
    return {name: [float(low * (high / low) ** x) for x in u] for name, (low, high) in ranges.items()}
# @end


# @build 13.01 run_one
# One optimiser at one rate and one seed: 03.03's network, started from
# torch.manual_seed(seed), trained for cfg.epochs passes over the training
# images in batches of cfg.batch (the order from run.rng); "adam" is Adam
# at lr with its default betas, "nesterov" SGD at lr with Nesterov
# momentum cfg.momentum. Each pass's loss goes to the log; the summary is
# the error, as a fraction, on the validation and the test images.
def run_one(cfg, name, lr, seed, label, data, dev):
    (x, y), val, test = data
    run = lab.Run(cfg, seed, label=label)
    torch.manual_seed(seed)
    model = mlp(torch, [784, cfg.hidden, cfg.hidden, 10]).to(dev)
    if name == "adam":
        opt = torch.optim.Adam(model.parameters(), lr=lr)
    else:
        opt = torch.optim.SGD(model.parameters(), lr=lr, momentum=cfg.momentum, nesterov=True)
    for epoch in range(cfg.epochs):
        loss, _ = train_epoch(model, opt, x, y, cfg.batch, run.rng)
        run.log(epoch=epoch + 1, loss=loss)
    return run.finish(optimiser=name, lr=lr, val_error=1 - evaluate(model, *val)[1], test_error=1 - evaluate(model, *test)[1])
# @end


def verdict(adam, sgd):
    """The rule, applied: Welch's t of SGD's test errors against Adam's (positive: Adam lower)."""
    t = lab.welch_t(sgd, adam)
    return t, ("held: Adam lower" if t >= 3 else "the reverse: SGD lower" if t <= -3 else "a tie")


def main():
    cfg = lab.config(CONFIG)
    dev = lab.device(torch, cfg.device)
    start = lab.clock(torch, dev)
    images, labels = mnist.load("train", None, cfg.standardise)
    n = len(images)
    data = (tensors(dev, images[:cfg.n_train], labels[:cfg.n_train]),
            tensors(dev, images[n - cfg.n_val:], labels[n - cfg.n_val:]),
            tensors(dev, *mnist.load("test", None, cfg.standardise)))
    print(f"1. The hypothesis: {HYPOTHESIS}\n   The rule: {RULE}")

    ranges = {"adam": cfg.adam, "nesterov": cfg.nesterov}
    rates = draw_rates(ranges, cfg.trials, np.random.default_rng(cfg.search_seed))
    trials = {name: [run_one(cfg, name, lr, 0, f"search-{name}-{i}", data, dev) for i, lr in enumerate(rs)]
              for name, rs in rates.items()}
    print(f"\n2. The search: {cfg.trials} learning rates each, log-uniform over its range (the same draws), seed 0, "
          f"{cfg.epochs} passes over {cfg.n_train:,} images;\n   validation error / test error, in %:")
    best = {}
    for name, ts in trials.items():
        low, high = ranges[name]
        print(f"   {name:8s} ({low:g} to {high:g}): " + "  ".join(
            f"{t['lr']:.2g}: {100 * t['val_error']:.2f}/{100 * t['test_error']:.2f}" for t in sorted(ts, key=lambda t: t["lr"])))
        best[name] = min(ts, key=lambda t: t["val_error"])
        print(f"   {'':8s} chosen on validation: lr {best[name]['lr']:.3g} ({100 * best[name]['val_error']:.2f}% on "
              f"validation)")

    fresh = range(1, cfg.seeds + 1)
    arms = {"adam, tuned": ("adam", best["adam"]["lr"]),
            f"nesterov, lr {cfg.default_lr:g} (the docs' example)": ("nesterov", cfg.default_lr),
            "nesterov, tuned": ("nesterov", best["nesterov"]["lr"])}
    errors = {arm: [run_one(cfg, name, lr, s, f"{arm.split(',')[0]}-lr{lr:.3g}", data, dev)["test_error"] for s in fresh]
              for arm, (name, lr) in arms.items()}
    adam, hurried, fair = (errors[a] for a in arms)
    print(f"\n   Test error, %, on {cfg.seeds} fresh seeds (1 to {cfg.seeds}):")
    for arm, (name, lr) in arms.items():
        print(f"   {arm:34s} lr {lr:<8.3g} {lab.spread([100 * e for e in errors[arm]])}")
    print("   The chosen trials' own test error, seed 0 (chosen for being best there, so not reported): " +
          ", ".join(f"{name} {100 * t['test_error']:.2f}" for name, t in best.items()))
    for k, (other, words) in enumerate(((hurried, "3. The hurried comparison: Adam tuned, SGD at the docs' rate"),
                                        (fair, "4. The fair comparison: both tuned by the same search"))):
        t, said = verdict(adam, other)
        print(f"\n{words}:\n   SGD's test error minus Adam's: {100 * (lab.mean(other) - lab.mean(adam)):+.2f} points, "
              f"t = {t:+.1f}: {said}")

    print(f"\n5. What a search of n trials buys (expected over every way of drawing n of the {cfg.trials}): the best "
          f"validation error, and the test error of the one chosen, %")
    print("   " + f"{'n':>3s}" + "".join(f"{name + ' val':>15s}{name + ' test':>15s}" for name in trials))
    series = []
    for k, (name, ts) in enumerate(trials.items()):
        val, test = [t["val_error"] for t in ts], [t["test_error"] for t in ts]
        curve = [lab.best_of(val, m) for m in range(1, cfg.trials + 1)]
        series.append(lab.Line(f"{name}, validation", range(1, cfg.trials + 1), [100 * c for c in curve], k))
        series.append(lab.Line(f"{name}, test of the chosen", range(1, cfg.trials + 1),
                               [100 * lab.best_of(val, m, test) for m in range(1, cfg.trials + 1)], k, dashed=True))
    for m in range(1, cfg.trials + 1):
        cells = []
        for ts in trials.values():
            val, test = [t["val_error"] for t in ts], [t["test_error"] for t in ts]
            cells.append(f"{100 * lab.best_of(val, m):15.2f}{100 * lab.best_of(val, m, test):15.2f}")
        print(f"   {m:3d}" + "".join(cells))
    path = lab.lines(f"{cfg.out}/{cfg.name}/best_of.svg", series, xlabel="trials in the search (n)",
                     ylabel="error, %, expected best of n")
    print(f"   curves in {path}")
    print(f"\n{lab.clock(torch, dev) - start:.0f} s of training and scoring on {dev.type}")


if __name__ == "__main__":
    main()
