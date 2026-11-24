"""Momentum: the zigzag in a narrow valley, and the same fix on MNIST.

First a valley: the loss (w0^2 + 50 w1^2) / 2, fifty times steeper across
(w1) than along (w0). Plain gradient descent at a rate the steep side
allows bounces from wall to wall and creeps along the floor; with momentum
the bounces cancel and the steps along the floor add up. The script counts
the steps each needs to get the loss below a threshold, and draws both
paths.

Then MNIST, one pass, a few seeds: plain SGD at 0.05, momentum 0.9 at the
same rate, and plain SGD at 0.5, the best rate of 03.01.

    python3 -m experiments.momentum          (needs MNIST: python3 -m data.fetch mnist)
    python3 -m experiments.momentum "runs=[]"  the valley alone
"""

import math

import engine as torch                      # the engine; "import torch" runs this on PyTorch
import lab
from data import mnist
from experiments.loop import mlp, train

CONFIG = dict(steep=50.0, lr=0.03, mus=[0.0, 0.8], start=[-4.0, 1.0], threshold=1e-4, max_steps=500,
              runs=[[0.05, 0.0], [0.05, 0.9], [0.5, 0.0]], hidden=100, batch=128, seeds=3)


# @build 03.02 valley
# Gradient descent with SGD(lr, momentum) on the valley loss, from start,
# until the loss is below threshold or max_steps have been taken. Returns
# the number of steps and the path: the list of (w0, w1) after each step.
def valley(steep, lr, mu, start, threshold, max_steps):
    w = torch.tensor(start, requires_grad=True)
    curve = torch.tensor([1.0, steep])
    opt = torch.optim.SGD([w], lr=lr, momentum=mu)
    path = [tuple(w.tolist())]
    for step in range(max_steps):
        loss = (curve * w * w).sum() * 0.5
        if loss.item() < threshold:
            return step, path
        opt.zero_grad()
        loss.backward()
        opt.step()
        path.append(tuple(w.tolist()))
    return max_steps, path
# @end


def main():
    cfg = lab.config(CONFIG)
    paths = []
    for i, mu in enumerate(cfg.mus):
        steps, path = valley(cfg.steep, cfg.lr, mu, cfg.start, cfg.threshold, cfg.max_steps)
        print(f"valley, lr {cfg.lr}, momentum {mu}: {steps} steps to a loss below {cfg.threshold:g}")
        paths.append(lab.Line(f"momentum {mu}", [p[0] for p in path], [p[1] for p in path], i))
    print(f"paths in {lab.lines(f'{cfg.out}/{cfg.name}/valley.svg', paths, xlabel='w0', ylabel='w1')}")
    if not cfg.runs:
        return
    x, y = mnist.load("train")
    curves = []
    for i, (lr, mu) in enumerate(cfg.runs):
        finals = []
        for seed in range(cfg.seeds):
            run = lab.Run(cfg, seed, label=f"lr{lr:g}-m{mu:g}")
            torch.manual_seed(seed)
            model = mlp(torch, [784, cfg.hidden, 10])
            opt = torch.optim.SGD(model.parameters(), lr=lr, momentum=mu)
            losses = train(torch, model, opt, x, y, cfg.batch, 1, run.rng, run)
            finals.append(run.finish(train_loss=sum(losses[-50:]) / 50)["train_loss"])
            curves.append(lab.Line(f"lr {lr:g}, momentum {mu:g}", [r["step"] for r in run.rows],
                                   [r["loss"] for r in run.rows], i, 0.6))
        text = lab.spread(finals) if all(math.isfinite(v) for v in finals) else "diverged"
        print(f"MNIST, lr {lr:g}, momentum {mu:g}: training loss, last 50 steps {text}")
    path = lab.lines(f"{cfg.out}/{cfg.name}/mnist.svg", curves, xlabel="step", ylabel="training loss (batch)",
                     logy=True)
    print(f"curves in {path}")


if __name__ == "__main__":
    main()
