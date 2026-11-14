"""Learning-rate schedules: a constant rate against warmup and cosine decay, with Adam on MNIST.

The network of two hidden layers, two passes over the training set, Adam,
a few seeds, five ways of setting the rate: constant at 1e-3 (Adam's
default) and at 3e-3; cosine decay from 3e-3 to 0; and at a peak of 1e-2,
cosine decay with and without a warmup of 200 steps. For each: the worst
batch loss of the first 300 steps (a spike there is the start going
wrong), the cost on the whole training set at the end, and the test error.

    python3 -m experiments.schedule          (needs MNIST: python3 -m data.fetch mnist)
"""

import math

import engine as torch                      # the engine; "import torch" runs this on PyTorch
import lab
from data import mnist
from experiments.loop import evaluate, mlp, train

CONFIG = dict(hidden=256, epochs=2, batch=128, seeds=3,
              runs=[["constant", 1e-3, 0], ["constant", 3e-3, 0], ["cosine", 3e-3, 0], ["cosine", 1e-2, 0],
                    ["cosine", 1e-2, 200]])


# @build 03.05 make_scheduler
# The scheduler for one way of setting the rate: none for "constant"; for
# "cosine", LambdaLR over warmup_cosine(warmup, total steps), so the rate
# the optimiser was made with is the peak.
def make_scheduler(kind, opt, warmup, total):
    if kind == "constant":
        return None
    return torch.optim.lr_scheduler.LambdaLR(opt, lab.warmup_cosine(warmup, total))
# @end


def main():
    cfg = lab.config(CONFIG)
    x, y = mnist.load("train")
    xt, yt = mnist.load("test")
    total = cfg.epochs * math.ceil(len(x) / cfg.batch)
    curves = []
    print(f"{'schedule':26s} {'worst loss, first 300':24s} {'training cost at the end':34s} test error (%)")
    for i, (kind, lr, warmup) in enumerate(cfg.runs):
        label = f"{kind} {lr:g}" + (f", warmup {warmup}" if warmup else "")
        spikes, costs, errors = [], [], []
        for seed in range(cfg.seeds):
            run = lab.Run(cfg, seed, label=f"{kind}-lr{lr:g}-w{warmup}")
            torch.manual_seed(seed)
            model = mlp(torch, [784, cfg.hidden, cfg.hidden, 10])
            opt = torch.optim.Adam(model.parameters(), lr=lr)
            losses = train(torch, model, opt, x, y, cfg.batch, cfg.epochs, run.rng, run,
                           scheduler=make_scheduler(kind, opt, warmup, total))
            spikes.append(max(losses[:300]))
            costs.append(evaluate(torch, model, x, y)[0])
            errors.append(100 * (1 - evaluate(torch, model, xt, yt)[1]))
            run.finish(worst_early_loss=spikes[-1], train_cost=costs[-1], test_error=errors[-1])
            curves.append(lab.Line(label, [r["step"] for r in run.rows], [r["loss"] for r in run.rows], i, 0.5))
        print(f"{label:26s} {lab.mean(spikes):<24.3f} {lab.spread(costs):34s} {lab.spread(errors, 3)}")
    path = lab.lines(f"{cfg.out}/{cfg.name}/loss.svg", curves, xlabel="step", ylabel="training loss (batch)",
                     logy=True)
    print(f"curves in {path}")


if __name__ == "__main__":
    main()
