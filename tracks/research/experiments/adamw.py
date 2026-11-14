"""AdamW: weight decay is not L2, once the optimiser divides by the gradient's size.

Loshchilov and Hutter (2017). Three parts.

1. For SGD, adding (wd / 2) |w|^2 to the loss (L2) and shrinking every
   weight by a fraction lr * wd after the step (weight decay) are the same
   update. For Adam they are not: the L2 term's gradient goes through
   Adam's division by the square root of v like any other gradient.
2. Where the difference lands: logistic regression on MNIST with pixels
   0..1, where a pixel that is 0 in every training image gives its weights
   no gradient from the data at all. With L2 in Adam, wd * w is the whole
   of their gradient, Adam scales it to a step of about lr, and those
   weights are driven to 0 at a speed set by lr, whatever wd is; the
   weights that the data moves are hardly decayed. With AdamW every weight
   shrinks by the same factor.
3. The paper's figure 2 at laptop size: test error over a grid of learning
   rate and decay, for Adam with L2 and for AdamW, on 2000 training images
   for 40 passes. The paper's claim is that AdamW's region of good settings
   is wider. The script prints both grids and how many settings land within
   0.3 points of each one's best.

    python3 -m experiments.adamw             (needs MNIST: python3 -m data.fetch mnist)
"""

import numpy as np

import engine as torch                      # the engine; "import torch" runs this on PyTorch
import lab
from data import mnist
from experiments.loop import evaluate, mlp, train

F = torch.nn.functional
CONFIG = dict(seed=0, lr=1e-3, l2s=[1e-4, 1e-2], decays=[0.01, 1.0], n_grid=2000, epochs=40, hidden=256,
              grid_lrs=[3e-4, 1e-3, 3e-3], adam_wds=[0.0, 3e-4, 1e-3, 3e-3], adamw_wds=[0.0, 0.1, 0.3, 1.0],
              seeds=2, margin=0.3)


def same_start(seed, dtype):
    torch.manual_seed(seed)
    model = mlp(torch, [784, 32, 10])
    return model.double() if dtype == "float64" else model


def batch():
    x, y = mnist.load("train", 256)
    return torch.from_numpy(x.astype(np.float64)), torch.from_numpy(y)


# @build 03.04 l2_step
# One step on a batch from the same start, the L2 way: the loss plus
# (wd / 2) times the sum of every weight squared, then opt.step(). Returns
# the weights after the step as a list of numpy arrays.
def l2_step(model, opt, x, y, wd):
    loss = F.cross_entropy(model(x), y)
    loss = loss + wd / 2 * sum((p * p).sum() for p in model.parameters())
    opt.zero_grad()
    loss.backward()
    opt.step()
    return [p.detach().numpy().copy() for p in model.parameters()]
# @end


# @build 03.04 decay_step
# The same, the weight-decay way: the gradient of the plain loss, then every
# weight shrunk by a fraction lr * wd (in place, outside the graph, before
# the step, so the shrinking uses the weight the gradient was taken at),
# then opt.step(). With AdamW the optimiser shrinks the weights itself, so
# wd here is 0.
def decay_step(model, opt, x, y, lr, wd):
    loss = F.cross_entropy(model(x), y)
    opt.zero_grad()
    loss.backward()
    with torch.no_grad():
        for p in model.parameters():
            p -= lr * wd * p
    opt.step()
    return [p.detach().numpy().copy() for p in model.parameters()]
# @end


def biggest_gap(a, b):
    return max(float(np.abs(u - v).max()) for u, v in zip(a, b))


def part1(cfg):
    x, y = batch()
    lr, wd = 0.1, 0.01
    m1, m2 = same_start(cfg.seed, "float64"), same_start(cfg.seed, "float64")
    a = l2_step(m1, torch.optim.SGD(m1.parameters(), lr=lr), x, y, wd)
    b = decay_step(m2, torch.optim.SGD(m2.parameters(), lr=lr), x, y, lr, wd)
    print(f"1. SGD, lr {lr}, wd {wd}: after one step, L2 and weight decay differ by at most "
          f"{biggest_gap(a, b):.1e} (rounding)")
    lr = cfg.lr
    m1, m2, m3 = (same_start(cfg.seed, "float64") for _ in range(3))
    start = max(float(np.abs(p.detach().numpy()).max()) for p in m3.parameters())
    a = l2_step(m1, torch.optim.Adam(m1.parameters(), lr=lr), x, y, wd)
    b = decay_step(m2, torch.optim.AdamW(m2.parameters(), lr=lr, weight_decay=wd), x, y, lr, 0.0)
    print(f"   Adam, lr {lr}, wd {wd}: after one step, L2 and AdamW differ by up to {biggest_gap(a, b):.1e}; "
          f"the decay itself moves no weight by more than {lr * wd * start:.1e}")


def part2(cfg):
    x, y = mnist.load("train", None, False)
    idle = x.max(0) == 0
    print(f"2. {int(idle.sum())} of 784 pixels are 0 in every training image: their weights get no gradient "
          f"from the data")
    for name, cls, wds in (("Adam + L2", torch.optim.Adam, cfg.l2s), ("AdamW", torch.optim.AdamW, cfg.decays)):
        for wd in wds:
            torch.manual_seed(cfg.seed)
            model = torch.nn.Linear(784, 10)
            start = model.weight.detach().numpy().copy()
            opt = cls(model.parameters(), lr=cfg.lr, weight_decay=wd)
            train(torch, model, opt, x, y, 128, 1, np.random.default_rng(cfg.seed))
            w = model.weight.detach().numpy()
            size = lambda m: float(np.sqrt((m ** 2).mean()))
            print(f"   {name:9s} wd {wd:<6g}: after one pass, idle pixels' weights at "
                  f"{size(w[:, idle]) / size(start[:, idle]):6.1%} of their starting size, the others' at "
                  f"{size(w[:, ~idle]) / size(start[:, ~idle]):6.1%}")


def part3(cfg):
    x, y = mnist.load("train", cfg.n_grid)
    xt, yt = mnist.load("test")
    print(f"3. test error (%), {cfg.n_grid} training images, {cfg.epochs} passes, mean of {cfg.seeds} seeds")
    for name, cls, wds in (("Adam + L2", torch.optim.Adam, cfg.adam_wds),
                           ("AdamW", torch.optim.AdamW, cfg.adamw_wds)):
        grid = {}
        for wd in wds:
            for lr in cfg.grid_lrs:
                errors = []
                for seed in range(cfg.seeds):
                    run = lab.Run(cfg, seed, label=f"{name.split()[0].lower()}-lr{lr:g}-wd{wd:g}")
                    torch.manual_seed(seed)
                    model = mlp(torch, [784, cfg.hidden, 10])
                    train(torch, model, cls(model.parameters(), lr=lr, weight_decay=wd), x, y, 128, cfg.epochs,
                          run.rng)
                    errors.append(100 * (1 - evaluate(torch, model, xt, yt)[1]))
                    run.finish(test_error=errors[-1])
                grid[wd, lr] = lab.mean(errors)
        best = min(grid.values())
        good = sum(1 for v in grid.values() if v <= best + cfg.margin)
        print(f"   {name}: rows wd, columns lr {cfg.grid_lrs}")
        for wd in wds:
            print(f"     wd {wd:<7g}" + "".join(f"{grid[wd, lr]:8.2f}" for lr in cfg.grid_lrs))
        print(f"     best {best:.2f}; {good} of {len(grid)} settings within {cfg.margin} of it")


def main():
    cfg = lab.config(CONFIG)
    part1(cfg)
    part2(cfg)
    part3(cfg)


if __name__ == "__main__":
    main()
