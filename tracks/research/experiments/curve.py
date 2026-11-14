"""A whole experiment in one file: fit a curve to noisy points by gradient descent.

The data are points of a sine wave, y = sin(pi x) for x in [-1, 1], with
noise added. The model is a polynomial, y = w0 + w1 x + w2 x^2 + w3 x^3.
The loss is the mean squared error. The update moves each weight against
the loss's derivative with respect to it, worked out by hand. The
evaluation is the same loss on points the fit never saw.

    python3 -m experiments.curve
"""

import numpy as np

import lab                                                            # @from 00.02

# @from 00.03
CONFIG = dict(n_train=20, n_test=500, noise=0.2, degree=3, lr=0.5, steps=2000, seeds=5)
# @else
# CONFIG = dict(n_train=20, n_test=500, noise=0.2, degree=3, lr=0.5, steps=2000, seed=0)
# @end


# @build 00.01 make_data
# n points: x uniform in [-1, 1], y = sin(pi x) plus normal noise of
# standard deviation `noise`, all drawn from rng (a numpy Generator).
def make_data(n, noise, rng):
    x = rng.uniform(-1, 1, n)
    y = np.sin(np.pi * x) + rng.normal(0, noise, n)
    return x, y
# @end


# @build 00.01 features
# The polynomial's inputs for every point at once: a matrix with one row
# per point and the columns x**0, x**1, ..., x**degree. The prediction for
# all points is then this matrix times the weights.
def features(x, degree):
    return np.stack([x ** k for k in range(degree + 1)], axis=1)
# @end


# @build 00.01 loss
# The mean squared error of the predictions X @ w against y.
def loss(w, X, y):
    return float(np.mean((X @ w - y) ** 2))
# @end


# @build 00.01 gradient
# The derivative of the loss with respect to each weight, by hand. The loss
# is the mean over points of (p - y)^2 with p = sum over k of w_k x^k, so
# its derivative with respect to w_k is the mean of 2 (p - y) x^k: for all k
# at once, 2 X.T @ (X @ w - y) / n.
def gradient(w, X, y):
    return 2 * X.T @ (X @ w - y) / len(y)
# @end


# @build 00.01 fit
# Gradient descent: every weight starts at 0; each of `steps` steps moves
# the weights by -lr times the gradient. Every 100 steps (and after the
# last), report(step, training loss) when report is given. Returns the
# weights.
def fit(X, y, lr, steps, report=None):
    w = np.zeros(X.shape[1])
    for step in range(steps):
        if report and step % 100 == 0:
            report(step, loss(w, X, y))
        w -= lr * gradient(w, X, y)
    if report:
        report(steps, loss(w, X, y))
    return w
# @end


# @build 00.02 one_run
# One run with one seed: its data drawn from the run's rng (training points
# first, then test points), the fit logged every 100 steps to the run's
# log, and the final losses as its summary. Returns the run and summary.
def one_run(cfg, seed):
    run = lab.Run(cfg, seed)
    x, y = make_data(cfg.n_train, cfg.noise, run.rng)
    xt, yt = make_data(cfg.n_test, cfg.noise, run.rng)
    X, Xt = features(x, cfg.degree), features(xt, cfg.degree)
    w = fit(X, y, cfg.lr, cfg.steps, lambda step, l: run.log(step=step, train_loss=l))
    return run, run.finish(train_loss=loss(w, X, y), test_loss=loss(w, Xt, yt))
# @end


def main():
    # @from 00.02
    cfg = lab.config(CONFIG)
    # @from 00.03
    runs = [one_run(cfg, seed) for seed in range(cfg.seeds)]
    for run, s in runs:
        print(f"seed {run.seed}  train loss {s['train_loss']:.4f}  test loss {s['test_loss']:.4f}")
    print("test loss", lab.spread([s["test_loss"] for _, s in runs]))
    curves = [lab.Line("train loss, one line per seed", [r["step"] for r in run.rows],
                       [r["train_loss"] for r in run.rows], 0, 0.6) for run, _ in runs]
    path = lab.lines(f"{cfg.out}/{cfg.name}/train_loss.svg", curves, xlabel="step", ylabel="training loss",
                     logy=True)
    print(f"runs in {cfg.out}/{cfg.name}/; curves in {path}")
    # @else
    # run, s = one_run(cfg, cfg.seed)
    # for row in run.rows:
    #     print(f"step {row['step']:5d}  train loss {row['train_loss']:.4f}")
    # print(f"train loss {s['train_loss']:.4f}  test loss {s['test_loss']:.4f}")
    # print(f"run in {run.dir}")
    # @end
    # @else
    # cfg = CONFIG
    # rng = np.random.default_rng(cfg["seed"])
    # x, y = make_data(cfg["n_train"], cfg["noise"], rng)
    # xt, yt = make_data(cfg["n_test"], cfg["noise"], rng)
    # X, Xt = features(x, cfg["degree"]), features(xt, cfg["degree"])
    # w = fit(X, y, cfg["lr"], cfg["steps"], lambda step, l: print(f"step {step:5d}  train loss {l:.4f}"))
    # print(f"weights {np.round(w, 3)}")
    # print(f"train loss {loss(w, X, y):.4f}  test loss {loss(w, Xt, yt):.4f}")
    # @end


if __name__ == "__main__":
    main()
