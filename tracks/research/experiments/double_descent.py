"""Double descent: test error against model size, past the point where the model fits the training set.

Nakkiran et al. (2019) find test error rising as a model grows to the size
where it can just fit its training set exactly (the interpolation
threshold), then falling again, below where it started, as the model
grows past it, and see it most strongly with label noise. Their figure
trains ResNets on CIFAR-10 for hours. At laptop size this runs the model the
effect was first described on (Belkin et al., 2019, cited by the paper):
a network of two layers whose first layer is fixed at random (p random
relu features of the image) and whose second is fitted exactly, by least
squares to the one-hot labels, with the smallest weights that do it (what
gradient descent started from zero converges to). n = 1000 training
digits, 10% of them with a random label; p from 50 to 10,000; a few seeds.
The threshold is p = n. Here the peak does not need the noise: with no
label random (noise=0) the test error at p = n is 86.8%, against 88.3%
with 10%; the noise raises the error on either side of the peak instead.

    python3 -m experiments.double_descent    (needs MNIST: python3 -m data.fetch mnist)
"""

import numpy as np

import lab
from data import mnist

CONFIG = dict(n_train=1000, n_test=5000, noise=0.1,
              widths=[50, 100, 200, 400, 600, 800, 900, 950, 1000, 1050, 1100, 1250, 1500, 2000, 3000, 5000,
                      10000], seeds=3)


# @build 05.04 features
# p random relu features of each image: relu(x @ W) for a W of shape
# (784, p) drawn from the normal distribution with variance 1 / 784, as
# float64.
def features(x, w):
    return np.maximum(x @ w, 0).astype(np.float64)
# @end


# @build 05.04 fit_min_norm
# The second layer: the weights B with features @ B as close as can be to
# the targets, and of those, the smallest. np.linalg.lstsq gives exactly
# that (through the singular value decomposition), on either side of the
# threshold.
def fit_min_norm(a, targets):
    return np.linalg.lstsq(a, targets, rcond=None)[0]
# @end


def one_seed(cfg, seed, x, y, xt, yt):
    rng = np.random.default_rng(seed)
    noisy = y.copy()
    flip = rng.random(len(y)) < cfg.noise
    noisy[flip] = rng.integers(0, 10, int(flip.sum()))
    targets, test_targets = np.eye(10)[noisy], np.eye(10)[yt]
    w = rng.standard_normal((784, max(cfg.widths))) / np.sqrt(784)
    out = []
    for p in cfg.widths:
        a, at = features(x, w[:, :p]), features(xt, w[:, :p])
        b = fit_min_norm(a, targets)
        pred = at @ b
        out.append(dict(width=p, train_mse=float(((a @ b - targets) ** 2).sum(1).mean()),
                        test_mse=float(((pred - test_targets) ** 2).sum(1).mean()),
                        test_error=float(np.mean(pred.argmax(1) != yt)), weights=float(np.sqrt((b ** 2).sum()))))
    return out


def main():
    cfg = lab.config(CONFIG)
    x, y = mnist.load("train", cfg.n_train)
    xt, yt = mnist.load("test", cfg.n_test)
    results = []
    for seed in range(cfg.seeds):
        run = lab.Run(cfg, seed)
        rows = one_seed(cfg, seed, x, y, xt, yt)
        for r in rows:
            run.log(**r)
        run.finish(peak_width=max(rows, key=lambda r: r["test_error"])["width"])
        results.append(rows)
    print(f"{cfg.n_train} training digits, {cfg.noise:.0%} of labels random; mean of {cfg.seeds} seeds")
    print(f"{'features p':>10s} {'training error (mse)':>21s} {'test error (mse)':>17s} {'test error':>11s} "
          f"{'size of weights':>16s}")
    for k, p in enumerate(cfg.widths):
        mean = lambda key: lab.mean([rows[k][key] for rows in results])
        print(f"{p:10d} {mean('train_mse'):21.3f} {mean('test_mse'):17.3f} {100 * mean('test_error'):10.1f}% "
              f"{mean('weights'):16.1f}")
    errors = [lab.mean([rows[k]["test_error"] for rows in results]) for k in range(len(cfg.widths))]
    peak = int(np.argmax(errors))
    before = min(errors[:peak]) if peak else float("nan")
    print(f"peak at p = {cfg.widths[peak]} ({100 * errors[peak]:.1f}%); best below it {100 * before:.1f}%; "
          f"at p = {cfg.widths[-1]} {100 * errors[-1]:.1f}%")
    lines = [lab.Line("test error", cfg.widths, errors, 1)] + [
        lab.Line("test error, one seed", cfg.widths, [r["test_error"] for r in rows], 1, 0.3) for rows in results]
    path = lab.lines(f"{cfg.out}/{cfg.name}/test_error.svg", lines, xlabel="random features p (log scale)",
                     ylabel="test error", logx=True)
    print(f"curve in {path}")


if __name__ == "__main__":
    main()
