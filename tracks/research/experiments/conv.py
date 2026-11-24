"""Convolution: the same weights at every position.

A fully connected layer has a weight for every pixel: what it learns about
a stroke in one place it knows nothing of two pixels away. A convolution
lays the same small filter on every window of the image. Three parts:

1. The fully connected network of 03.01 (784-100-10) and a small
   convolutional one with a ninth of its weights, each trained on 10,000
   digits as they are, then scored on test digits moved k pixels (a
   quarter of them up, a quarter down, left, right).
2. Why the convolutional network holds up, and why only so far: one test
   digit moved 4 pixels, through the trained network, layer by layer.
3. The same two networks trained and tested on digits whose pixels are
   all shuffled by one fixed permutation, the same for every image.

    python3 -m experiments.conv          (needs MNIST: python3 -m data.fetch mnist)
"""

import numpy as np

import engine as torch                      # the engine; "import torch" runs this on PyTorch
import lab
from data import mnist
from experiments.loop import evaluate, mlp, train

nn = torch.nn
CONFIG = dict(n_train=10000, n_test=5000, epochs=2, batch=64, lr=0.05, momentum=0.9, shifts=[0, 1, 2, 3, 4],
              seeds=3)
BLANK = (0 - mnist.MEAN) / mnist.STD         # a white pixel, standardised


# @build 06.01 convnet
# Two 3 by 3 convolutions, 8 filters and then 16, each padded by one
# pixel so that the image keeps its size and followed by a relu and a 2
# by 2 max pooling (28 by 28, then 14 by 14, then 7 by 7); then the 16
# maps of 7 by 7 in one row each, and a Linear layer to the 10 scores.
def convnet():
    return nn.Sequential(nn.Conv2d(1, 8, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
                         nn.Conv2d(8, 16, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
                         nn.Flatten(), nn.Linear(16 * 7 * 7, 10))
# @end


# @build 06.01 moved
# Each image of x (rows of 784 pixels) moved k pixels: image i up when i %
# 4 is 0, down when it is 1, left when 2 and right when 3. What moves out
# at one edge is lost, and what comes in at the other is `fill`, a blank
# pixel. Pad every image by k pixels of fill on all sides, then cut out
# its 28 by 28 window, 2k, 0 or k pixels from the top and from the left.
def moved(x, k, fill):
    n = len(x)
    padded = np.pad(x.reshape(n, 28, 28), ((0, 0), (k, k), (k, k)), constant_values=fill)
    out = np.empty((n, 28, 28), dtype=x.dtype)
    for i, (top, left) in enumerate(((2 * k, k), (0, k), (k, 2 * k), (k, 0))):
        out[i::4] = padded[i::4, top:top + 28, left:left + 28]
    return out.reshape(n, 784)
# @end


def network(kind):
    """The network and the shape its input takes: rows of 784 pixels, or images of 1 by 28 by 28."""
    if kind == "fully connected":
        return mlp(torch, [784, 100, 10]), (-1, 784)
    return convnet(), (-1, 1, 28, 28)


def trained(cfg, kind, seed, x, y, label, shuffled=False):
    """A network trained on (x, y), after shuffling every image's pixels by one permutation drawn from
    the run's generator when shuffled; the run, the model, its input's shape and the order of pixels."""
    run = lab.Run(cfg, seed, label=label)
    order = run.rng.permutation(784) if shuffled else np.arange(784)
    torch.manual_seed(seed)
    model, shape = network(kind)
    opt = torch.optim.SGD(model.parameters(), lr=cfg.lr, momentum=cfg.momentum)
    train(torch, model, opt, x[:, order].reshape(shape), y, cfg.batch, cfg.epochs, run.rng, run)
    return run, model, shape, order


def through(model, x, upto):
    """The output of the model's first `upto` layers, as a numpy array."""
    h = torch.from_numpy(x.reshape(-1, 1, 28, 28))
    with torch.no_grad():
        for m in list(model)[:upto]:
            h = m(h)
    return h.numpy()


def main():
    cfg = lab.config(CONFIG)
    x, y = mnist.load("train", cfg.n_train)
    xt, yt = mnist.load("test", cfg.n_test)
    kinds = ("fully connected", "convolutional")
    print(f"1. Trained on {cfg.n_train} digits as they are ({cfg.epochs} pass{'es' if cfg.epochs != 1 else ''}, "
          f"SGD lr {cfg.lr}); accuracy on {cfg.n_test} test digits moved k pixels")
    acc, models = {}, {}
    for kind in kinds:
        label = "fc" if kind == "fully connected" else "conv"
        weights = sum(p.numel() for p in network(kind)[0].parameters())
        print(f"   {kind}, {weights} weights")
        rows = []
        for seed in range(cfg.seeds):
            run, model, shape, _ = trained(cfg, kind, seed, x, y, label)
            rows.append([evaluate(torch, model, moved(xt, k, BLANK).reshape(shape), yt)[1] for k in cfg.shifts])
            run.finish(weights=weights, **{f"moved{k}": a for k, a in zip(cfg.shifts, rows[-1])})
            models[kind, seed] = model
        for i, k in enumerate(cfg.shifts):
            acc[kind, k] = [r[i] for r in rows]
            print(f"     k = {k}: {lab.spread(acc[kind, k])}")
    for k in cfg.shifts:
        t = lab.welch_t(acc["convolutional", k], acc["fully connected", k])
        print(f"   moved {k}: convolutional against fully connected, t = {t:+.1f}")
    lines = [lab.Line(kind, cfg.shifts, [lab.mean(acc[kind, k]) for k in cfg.shifts], i) for i, kind in enumerate(kinds)]
    print(f"   plot in {lab.lines(f'{cfg.out}/{cfg.name}/moved.svg', lines, xlabel='pixels moved', ylabel='test accuracy', ylim=(0, 1))}")

    print("2. One test digit and the same digit moved 4 pixels up, through the convolutional network (seed 0):")
    net = models["convolutional", 0]
    digit, up = xt[:1], moved(xt[:1], 4, BLANK)
    a, b = through(net, digit, 1), through(net, up, 1)
    print(f"   after the first convolution, rows 1 to 22 of the moved digit's maps are rows 5 to 26 of the "
          f"other's: largest difference {np.abs(b[:, :, 1:23] - a[:, :, 5:27]).max():.3g}")
    a, b = through(net, digit, 6), through(net, up, 6)
    print(f"   after the second pooling (16 maps of 7 by 7), rows 1 to 4 are rows 2 to 5: largest difference "
          f"{np.abs(b[:, :, 1:5] - a[:, :, 2:6]).max():.3g}")
    a, b = through(net, digit, 8), through(net, up, 8)
    print(f"   the Linear layer has a weight for every place on those maps: its 10 scores move by up to "
          f"{np.abs(b - a).max():.3g} (they range over {a.max() - a.min():.3g}); predicted {a.argmax()} and {b.argmax()}, "
          f"the label is {yt[0]}")

    print("3. Every image's pixels shuffled by one fixed permutation (training and test alike), not moved:")
    for kind in kinds:
        label = "fc" if kind == "fully connected" else "conv"
        got = []
        for seed in range(cfg.seeds):
            run, model, shape, order = trained(cfg, kind, seed, x, y, label + "-shuffled", shuffled=True)
            got.append(evaluate(torch, model, xt[:, order].reshape(shape), yt)[1])
            run.finish(accuracy=got[-1])
        print(f"   {kind:16s} {lab.spread(got)}; against the same pixels unshuffled, t = "
              f"{lab.welch_t(got, acc[kind, 0]):+.1f}")


if __name__ == "__main__":
    main()
