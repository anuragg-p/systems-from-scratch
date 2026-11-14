"""Broadcasting: tensors of different shapes in one operation, and where their gradients go.

For each pair of shapes the script adds and multiplies two tensors, prints
the shape of the result and of each input's gradient, and checks every
gradient against the nudge with gradcheck (in float64). The last pair is
the one every layer has: a batch of rows plus one bias row, whose gradient
is the sum of the batch's.

    python3 -m experiments.broadcast
"""

import numpy as np

import engine as torch                      # the engine; "import torch" runs this on PyTorch
import lab

CONFIG = dict(seed=0)
PAIRS = [((3, 4), (3, 4)), ((3, 1), (1, 4)), ((2, 3, 4), (4,)), ((5, 4), (4,)), ((3, 4), ())]


# @build 02.02 combine
# The function each pair goes through: (a + b) * b * a, so that each input
# meets the other's shape twice, once added and once multiplied.
def combine(a, b):
    return (a + b) * b * a
# @end


def main():
    cfg = lab.config(CONFIG)
    rng = np.random.default_rng(cfg.seed)
    print(f"{'a':>10s} {'b':>10s}  {'a op b':>10s}  {'a.grad':>10s} {'b.grad':>10s}  gradcheck")
    for sa, sb in PAIRS:
        a = torch.tensor(rng.standard_normal(sa), requires_grad=True)
        b = torch.tensor(rng.standard_normal(sb), requires_grad=True)
        out = combine(a, b)
        out.backward(torch.ones_like(out))
        ok = torch.autograd.gradcheck(combine, (a, b))
        print(f"{str(sa):>10s} {str(sb):>10s}  {str(tuple(out.shape)):>10s}  "
              f"{str(tuple(a.grad.shape)):>10s} {str(tuple(b.grad.shape)):>10s}  {'ok' if ok else 'FAILED'}")
    x = torch.tensor(rng.standard_normal((5, 4)))
    bias = torch.tensor(np.zeros(4), requires_grad=True)
    (x + bias).backward(torch.ones_like(x))
    print(f"a batch of 5 rows plus a bias of 4: the bias's gradient is {bias.grad.numpy().tolist()}, "
          f"one 1.0 from each row, summed")


if __name__ == "__main__":
    main()
