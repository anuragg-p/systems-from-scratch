"""The same arithmetic on n numbers, as n scalar Values and as one tensor: how much faster?

For n pairs of numbers x and y, out = tanh(x * y + x), and the gradient of
the sum of out with respect to every x and y. The scalar engine builds a
Python object for every number of every step; the tensor engine builds one
per operation and leaves the n numbers to numpy. The script times both
(the best of a few repeats), checks that they give the same gradients, and
prints how many times slower the scalar engine is.

    python3 -m experiments.speed
"""

import time

import numpy as np

import engine as torch                      # the engine; "import torch" runs this on PyTorch
import lab
from engine.value import Value

CONFIG = dict(n=20000, repeats=3, seed=0)


def with_values(xs, ys):
    """Forward and backward on scalar Values: the gradients as two lists of floats."""
    vx, vy = [Value(a) for a in xs], [Value(b) for b in ys]
    total = sum(((a * b + a).tanh() for a, b in zip(vx, vy)), Value(0.0))
    total.backward()
    return [v.grad for v in vx], [v.grad for v in vy]


# @build 02.01 with_tensors
# The same on two tensors of n numbers: out = (x * y + x).tanh(), and
# out.backward(ones) gives the gradient of out's sum (the gradient of a sum
# is 1 for every term). Returns the two gradients as numpy arrays.
def with_tensors(xs, ys):
    x = torch.tensor(xs, dtype=torch.float64, requires_grad=True)
    y = torch.tensor(ys, dtype=torch.float64, requires_grad=True)
    out = (x * y + x).tanh()
    out.backward(torch.ones_like(out))
    return x.grad.numpy(), y.grad.numpy()
# @end


def best_time(fn, *args, repeats=3):
    best, result = float("inf"), None
    for _ in range(repeats):
        start = time.perf_counter()
        result = fn(*args)
        best = min(best, time.perf_counter() - start)
    return best, result


def main():
    cfg = lab.config(CONFIG)
    rng = np.random.default_rng(cfg.seed)
    xs, ys = rng.standard_normal(cfg.n), rng.standard_normal(cfg.n)
    t_values, (gx, gy) = best_time(with_values, xs.tolist(), ys.tolist(), repeats=cfg.repeats)
    t_tensors, (tx, ty) = best_time(with_tensors, xs, ys, repeats=cfg.repeats)
    diff = max(np.abs(np.array(gx) - tx).max(), np.abs(np.array(gy) - ty).max())
    print(f"{cfg.n} numbers, forward and backward:")
    print(f"  scalar Values  {t_values * 1e3:9.2f} ms  ({t_values / cfg.n * 1e9:7.0f} ns a number)")
    print(f"  one tensor     {t_tensors * 1e3:9.2f} ms  ({t_tensors / cfg.n * 1e9:7.0f} ns a number)")
    print(f"  the tensor is {t_values / t_tensors:.0f} times faster")
    print(f"  largest difference between their gradients: {diff:.1e}")


if __name__ == "__main__":
    main()
