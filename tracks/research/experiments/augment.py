"""More data for free: every image moved by a pixel or two, a new way every pass.

The network and the 2000 digits of 05.02, trained with AdamW for 50
passes, three ways: the images as they are; each pass, every image shifted
by up to 1 pixel each way; by up to 2. A few seeds each; training,
validation and test error at the end.

    python3 -m experiments.augment           (needs MNIST: python3 -m data.fetch mnist)
"""

import engine as torch                      # the engine; "import torch" runs this on PyTorch
import lab
from data import mnist
from data.augment import shift
from experiments.loop import evaluate, mlp, train

CONFIG = dict(n_train=2000, n_val=10000, hidden=512, lr=1e-3, batch=128, epochs=50, shifts=[0, 1, 2], seeds=3)
BLANK = (0 - mnist.MEAN) / mnist.STD         # a white pixel, standardised


# @build 05.03 train_shifted
# Train for `epochs` passes, each over a freshly shifted copy of the images
# (up to k pixels; k of 0 is the images as they are). Returns nothing: the
# model has learned.
def train_shifted(model, opt, x, y, k, batch, epochs, rng):
    for _ in range(epochs):
        seen = shift(x, k, rng, BLANK) if k else x
        train(torch, model, opt, seen, y, batch, 1, rng)
# @end


def main():
    cfg = lab.config(CONFIG)
    x, y = mnist.load("train")
    x, y, xv, yv = x[:cfg.n_train], y[:cfg.n_train], x[-cfg.n_val:], y[-cfg.n_val:]
    xt, yt = mnist.load("test")
    errors = {}
    print(f"{cfg.n_train} training digits, {cfg.epochs} passes; error in %")
    print(f"{'':16s}{'training':>10s}  {'validation':32s}  test")
    for k in cfg.shifts:
        rows = []
        for seed in range(cfg.seeds):
            run = lab.Run(cfg, seed, label=f"shift{k}")
            torch.manual_seed(seed)
            model = mlp(torch, [784, cfg.hidden, cfg.hidden, 10])
            opt = torch.optim.AdamW(model.parameters(), lr=cfg.lr)
            train_shifted(model, opt, x, y, k, cfg.batch, cfg.epochs, run.rng)
            rows.append([100 * (1 - evaluate(torch, model, a, b)[1]) for a, b in ((x, y), (xv, yv), (xt, yt))])
            run.finish(train_error=rows[-1][0], val_error=rows[-1][1], test_error=rows[-1][2])
        errors[k] = [r[2] for r in rows]
        name = f"shifts up to {k}" if k else "as they are"
        print(f"{name:16s}{lab.mean([r[0] for r in rows]):10.2f}  {lab.spread([r[1] for r in rows]):32s}  "
              f"{lab.mean([r[2] for r in rows]):.2f}")
    for k in cfg.shifts[1:]:
        print(f"test error, shifts up to {k} against none: t = {lab.welch_t(errors[k], errors[cfg.shifts[0]]):+.1f}")


if __name__ == "__main__":
    main()
