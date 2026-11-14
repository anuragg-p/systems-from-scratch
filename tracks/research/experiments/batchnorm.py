"""Batch normalisation: the same network, each layer's inputs normalised over the batch.

Ioffe and Szegedy (2015). Two claims, two parts.

1. Their figure 1(a), at laptop size: MNIST, three hidden layers of 100
   sigmoid units, batches of 60, plain SGD; test accuracy as training goes
   on, with and without batch norm before each sigmoid. The claim: with it,
   the network gets to a given accuracy in fewer steps.
2. A rate that diverges without it: the 20-layer relu network of 04.02,
   started with He's weights, one pass of SGD with momentum at 0.01 and at
   0.1, with and without batch norm after each hidden layer.

    python3 -m experiments.batchnorm         (needs MNIST: python3 -m data.fetch mnist)
"""

import math

import numpy as np

import engine as torch                      # the engine; "import torch" runs this on PyTorch
import lab
from data import batches, mnist
from experiments.loop import evaluate, train

nn, F = torch.nn, torch.nn.functional
CONFIG = dict(sizes=[784, 100, 100, 100, 10], batch=60, lr=0.5, steps=3000, every=250, target=0.9,
              depth=20, width=64, deep_lrs=[0.01, 0.1], momentum=0.9, seeds=3)


# @build 04.03 with_norm
# The network of the given sizes: a linear layer, then, between the hidden
# layers, nn.BatchNorm1d (when norm is "batch") and then the activation
# (made by act()). He's starting weights and zero biases when he is True,
# else nn.Linear's own.
def with_norm(sizes, act, norm=None, he=False):
    layers = []
    for i, (n_in, n_out) in enumerate(zip(sizes[:-1], sizes[1:])):
        lin = nn.Linear(n_in, n_out)
        if he:
            nn.init.kaiming_normal_(lin.weight, nonlinearity="relu")
            nn.init.zeros_(lin.bias)
        layers.append(lin)
        if i < len(sizes) - 2:
            if norm == "batch":
                layers.append(nn.BatchNorm1d(n_out))
            layers.append(act())
    return nn.Sequential(*layers)
# @end


def accuracy_curve(cfg, norm, seed, data):
    """Test accuracy every cfg.every steps of plain SGD on the sigmoid network."""
    x, y, xt, yt = data
    run = lab.Run(cfg, seed, label=f"sigmoid-{norm or 'none'}")
    torch.manual_seed(seed)
    model = with_norm(cfg.sizes, nn.Sigmoid, norm)
    opt = torch.optim.SGD(model.parameters(), lr=cfg.lr)
    step, curve = 0, []
    while step < cfg.steps:
        for idx in batches(len(x), cfg.batch, run.rng):
            loss = F.cross_entropy(model(torch.from_numpy(x[idx])), torch.from_numpy(y[idx]))
            opt.zero_grad()
            loss.backward()
            opt.step()
            step += 1
            if step % cfg.every == 0:
                curve.append(evaluate(torch, model, xt, yt)[1])
                run.log(step=step, test_accuracy=curve[-1])
            if step == cfg.steps:
                break
    run.finish(test_accuracy=curve[-1])
    return curve


def main():
    cfg = lab.config(CONFIG)
    x, y = mnist.load("train")
    xt, yt = mnist.load("test")
    steps = list(range(cfg.every, cfg.steps + 1, cfg.every))
    print(f"1. sigmoid network {cfg.sizes}, SGD lr {cfg.lr}, batches of {cfg.batch}: test accuracy")
    lines = []
    for i, norm in enumerate([None, "batch"]):
        curves = [accuracy_curve(cfg, norm, seed, (x, y, xt, yt)) for seed in range(cfg.seeds)]
        mean = np.mean(curves, axis=0)
        first = next((s for s, a in zip(steps, mean) if a >= cfg.target), None)
        name = "batch norm" if norm else "no norm"
        print(f"   {name:10s}: " + "  ".join(f"{s}: {a:.3f}" for s, a in zip(steps, mean) if s in (250, 500, 1000, 2000, cfg.steps))
              + f"; first at {cfg.target:.0%}: " + (f"step {first}" if first else "not reached"))
        lines += [lab.Line(name, steps, c, i, 0.6) for c in curves]
    print(f"   curves in {lab.lines(f'{cfg.out}/{cfg.name}/sigmoid.svg', lines, xlabel='step', ylabel='test accuracy')}")
    print(f"2. {cfg.depth} relu layers of {cfg.width}, He's start, one pass of SGD with momentum {cfg.momentum}: "
          f"loss of the last 50 steps")
    sizes = [784] + [cfg.width] * (cfg.depth - 1) + [10]
    for lr in cfg.deep_lrs:
        for norm in (None, "batch"):
            finals = []
            for seed in range(cfg.seeds):
                run = lab.Run(cfg, seed, label=f"deep-lr{lr:g}-{norm or 'none'}")
                torch.manual_seed(seed)
                model = with_norm(sizes, nn.ReLU, norm, he=True)
                opt = torch.optim.SGD(model.parameters(), lr=lr, momentum=cfg.momentum)
                losses = train(torch, model, opt, x, y, 128, 1, run.rng, run)
                end = losses[-50:]
                finals.append(sum(end) / len(end) if math.isfinite(losses[-1]) else float("nan"))
                run.finish(train_loss=finals[-1])
            bad = sum(1 for v in finals if not math.isfinite(v))
            each = ", ".join(f"{v:.3f}" for v in finals)
            text = lab.spread(finals) if not bad else f"diverged in {bad} of {len(finals)} runs"
            print(f"   lr {lr:<5g} {'batch norm' if norm else 'no norm':10s}: {each}  ({text})")


if __name__ == "__main__":
    main()
