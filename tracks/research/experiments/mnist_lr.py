"""MNIST in batches with plain SGD, at learning rates from too small to too big.

A network of one hidden layer (784 pixels, 100 relu units, 10 scores) is
trained for one pass over the 60,000 training digits in batches of 128,
with stochastic gradient descent at each learning rate, over a few seeds.
Too small, and one pass gets nowhere. Too big, and within a few steps the
loss jumps far above where it started; the jump leaves most hidden units
at 0 for every digit (their relu never opens again), and the network is
left guessing, its loss near log(10) = 2.30 for the rest of the run. The
script prints, for each rate, the training loss at the end and the test
accuracy, and draws the loss of every step of every run.

    python3 -m experiments.mnist_lr          (needs MNIST: python3 -m data.fetch mnist)
"""

import math

import engine as torch                      # the engine; "import torch" runs this on PyTorch
import lab
from data import mnist
from experiments.loop import evaluate, mlp, train

CONFIG = dict(lrs=[0.01, 0.1, 0.5, 2.0], hidden=100, batch=128, epochs=1, n_train=60000, seeds=3)


# @build 03.01 one_run
# One rate, one seed: the engine seeded with the seed (the starting
# weights), the network, SGD at lr, one call to train with the run's rng
# (the batch order), then the test set. Returns the run's summary: the mean
# loss of the last 50 steps (nan if it diverged), test loss and accuracy.
def one_run(cfg, lr, seed, data):
    x, y, xt, yt = data
    run = lab.Run(cfg, seed, label=f"lr{lr:g}")
    torch.manual_seed(seed)
    model = mlp(torch, [784, cfg.hidden, 10])
    opt = torch.optim.SGD(model.parameters(), lr=lr)
    losses = train(torch, model, opt, x, y, cfg.batch, cfg.epochs, run.rng, run, every=1)
    end = losses[-50:]
    final = sum(end) / len(end) if all(math.isfinite(v) for v in end) else float("nan")
    test_loss, test_accuracy = evaluate(torch, model, xt, yt)
    return run, run.finish(train_loss=final, test_loss=test_loss, test_accuracy=test_accuracy)
# @end


def main():
    cfg = lab.config(CONFIG)
    x, y = mnist.load("train", cfg.n_train)
    xt, yt = mnist.load("test")
    curves = []
    print(f"{'lr':>6s}  {'training loss, last 50 steps':40s}  test accuracy")
    for i, lr in enumerate(cfg.lrs):
        runs = [one_run(cfg, lr, seed, (x, y, xt, yt)) for seed in range(cfg.seeds)]
        losses = [s["train_loss"] for _, s in runs]
        diverged = sum(1 for v in losses if not math.isfinite(v))
        loss_text = lab.spread(losses) if not diverged else f"diverged in {diverged} of {len(runs)} runs"
        acc_text = lab.spread([s["test_accuracy"] for _, s in runs]) if not diverged else "-"
        print(f"{lr:6g}  {loss_text:40s}  {acc_text}")
        curves += [lab.Line(f"lr {lr:g}", [r["step"] for r in run.rows], [r["loss"] for r in run.rows], i, 0.6)
                   for run, _ in runs]
    path = lab.lines(f"{cfg.out}/{cfg.name}/loss.svg", curves, xlabel="step", ylabel="training loss (batch)",
                     logy=True, ylim=(0.01, 100))
    print(f"curves in {path}")


if __name__ == "__main__":
    main()
