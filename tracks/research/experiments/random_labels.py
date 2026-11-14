"""Train, validation and test: a network that memorises labels given at random.

Zhang et al. (2016), figure 1(a): the same network that learns real labels
also fits labels drawn at random, to zero training error, only more
slowly. Here: a network of two hidden layers of 512 trained with Adam on
1000 MNIST digits, once with their own labels and once with labels drawn
at random, a few seeds each. The data are cut three ways: the 1000 to
train on; 10,000 more of MNIST's training set to validate on, watched
while training; and MNIST's test set, scored once, at the end. Training
accuracy reaches 100% either way; only the held-out sets tell learning
from memorising.

    python3 -m experiments.random_labels     (needs MNIST: python3 -m data.fetch mnist)
"""

import numpy as np

import engine as torch                      # the engine; "import torch" runs this on PyTorch
import lab
from data import mnist
from experiments.loop import evaluate, mlp, train

CONFIG = dict(n_train=1000, n_val=10000, hidden=512, lr=1e-3, batch=100, epochs=60, every=5, seeds=3)


# @build 05.01 split
# Three sets from MNIST, kept apart: the first n_train training images to
# train on; the last n_val of the training set to validate on (never
# trained on, looked at as often as wanted); the test set, for the end.
# With random=True the training labels are replaced by classes drawn
# uniformly from rng; the other two sets keep their real labels.
def split(n_train, n_val, random, rng):
    x, y = mnist.load("train")
    train_x, train_y = x[:n_train], y[:n_train]
    if random:
        train_y = rng.integers(0, 10, n_train)
    return (train_x, train_y), (x[-n_val:], y[-n_val:]), mnist.load("test")
# @end


def main():
    cfg = lab.config(CONFIG)
    lines = []
    for i, random in enumerate([False, True]):
        name = "random labels" if random else "real labels"
        done_at, finals = [], []
        for seed in range(cfg.seeds):
            run = lab.Run(cfg, seed, label=name.replace(" ", "-"))
            (x, y), (xv, yv), (xt, yt) = split(cfg.n_train, cfg.n_val, random, run.rng)
            torch.manual_seed(seed)
            model = mlp(torch, [784, cfg.hidden, cfg.hidden, 10])
            opt = torch.optim.Adam(model.parameters(), lr=cfg.lr)
            first = None
            for epoch in range(cfg.every, cfg.epochs + 1, cfg.every):
                train(torch, model, opt, x, y, cfg.batch, cfg.every, run.rng)
                train_acc, val_acc = evaluate(torch, model, x, y)[1], evaluate(torch, model, xv, yv)[1]
                run.log(epoch=epoch, train_accuracy=train_acc, val_accuracy=val_acc)
                if first is None and train_acc == 1.0:
                    first = epoch
            done_at.append(first)
            test_acc = evaluate(torch, model, xt, yt)[1]
            finals.append(run.finish(train_accuracy=train_acc, val_accuracy=val_acc, test_accuracy=test_acc))
            lines.append(lab.Line(f"{name}, training", [r["epoch"] for r in run.rows],
                                  [r["train_accuracy"] for r in run.rows], 2 * i, 0.7))
            lines.append(lab.Line(f"{name}, validation", [r["epoch"] for r in run.rows],
                                  [r["val_accuracy"] for r in run.rows], 2 * i + 1, 0.7, dashed=True))
        reached = ", ".join(str(e) if e else "never" for e in done_at)
        print(f"{name}: 100% of the training set right at epoch {reached}")
        for key in ("train_accuracy", "val_accuracy", "test_accuracy"):
            print(f"   {key.replace('_', ' '):18s} {lab.spread([s[key] for s in finals])}")
    path = lab.lines(f"{cfg.out}/{cfg.name}/accuracy.svg", lines, xlabel="epoch", ylabel="accuracy")
    print(f"curves in {path}")


if __name__ == "__main__":
    main()
