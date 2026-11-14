"""Training a network of Values to tell two groups of points apart: a loss that goes down.

The points are the two moons of data/points.py; the network is
MLP(2, [8, 8, 1]) from the scalar engine, whose one output is a score: above
0 means group 1, below means group 0. The loss is the hinge loss: nothing
for a point scored on the right side by a margin of 1, more the further it
falls short. Each step computes the loss on every training point, runs
backward(), and moves every weight against its gradient. Over a few seeds
it reports the loss as it falls, the accuracy on the training points and
on fresh points, and draws the loss curves.

    python3 -m experiments.two_groups
"""

import lab
from data.points import two_groups
from engine.value import MLP

CONFIG = dict(n_train=50, n_test=200, noise=0.1, sizes=[8, 8, 1], steps=80, lr=0.5, seeds=3)


# @build 01.04 hinge_loss
# The mean over points of relu(1 - t * score), with t = +1 for group 1 and
# -1 for group 0 (a Value), and the fraction of points on the right side
# (a float): score > 0 for group 1, score <= 0 for group 0.
def hinge_loss(model, x, y):
    scores = [model([float(a), float(b)]) for a, b in x]
    signs = [1.0 if label == 1 else -1.0 for label in y]
    losses = [(1 - t * s).relu() for t, s in zip(signs, scores)]
    accuracy = sum((s.data > 0) == (t > 0) for t, s in zip(signs, scores)) / len(scores)
    return sum(losses) * (1.0 / len(losses)), accuracy
# @end


# @build 01.04 train
# Gradient descent on the hinge loss over all the training points at once,
# for `steps` steps: every weight's gradient set to 0, the loss computed,
# backward(), every weight moved by -lr times its gradient. Each step's
# loss and accuracy go to run.log (before that step's update).
def train(model, x, y, steps, lr, run):
    params = model.parameters()
    for step in range(steps):
        for p in params:
            p.grad = 0.0
        loss, accuracy = hinge_loss(model, x, y)
        run.log(step=step, loss=loss.data, accuracy=accuracy)
        loss.backward()
        for p in params:
            p.data -= lr * p.grad
# @end


def main():
    cfg = lab.config(CONFIG)
    curves, finals = [], []
    for seed in range(cfg.seeds):
        run = lab.Run(cfg, seed)
        x, y = two_groups(cfg.n_train, cfg.noise, run.rng)
        xt, yt = two_groups(cfg.n_test, cfg.noise, run.rng)
        model = MLP(2, cfg.sizes, seed=seed)
        train(model, x, y, cfg.steps, cfg.lr, run)
        loss, accuracy = hinge_loss(model, x, y)
        _, test_accuracy = hinge_loss(model, xt, yt)
        first = run.rows[0]
        s = run.finish(loss=loss.data, accuracy=accuracy, test_accuracy=test_accuracy)
        print(f"seed {seed}: loss {first['loss']:.3f} -> {s['loss']:.3f}, accuracy {first['accuracy']:.2f} -> "
              f"{s['accuracy']:.2f}, on fresh points {s['test_accuracy']:.2f}")
        finals.append(s)
        curves.append(lab.Line("hinge loss, one line per seed", [r["step"] for r in run.rows],
                               [r["loss"] for r in run.rows], 0, 0.7))
    print("training accuracy  ", lab.spread([s["accuracy"] for s in finals]))
    print("accuracy on fresh points", lab.spread([s["test_accuracy"] for s in finals]))
    path = lab.lines(f"{cfg.out}/{cfg.name}/loss.svg", curves, xlabel="step", ylabel="hinge loss")
    print(f"curves in {path}")


if __name__ == "__main__":
    main()
