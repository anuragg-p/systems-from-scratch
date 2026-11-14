"""Softmax and cross-entropy: the obvious formula overflows, the shifted one does not.

Three rows of scores, the last two far too big for e**x in float32: the
softmax written as e**x / sum(e**x) gives nan for them; the library's,
which subtracts each row's largest score first, gives the right
probabilities. Then the loss: cross-entropy on scores that put almost all
the probability on a wrong class is large but finite, its gradient passes
gradcheck, and a classifier that knows nothing (every score equal) loses
log(classes), the number every training run should start near.

    python3 -m experiments.softmax
"""

import math

import numpy as np

import engine as torch                      # the engine; "import torch" runs this on PyTorch
import lab

F = torch.nn.functional
CONFIG = dict(seed=0, classes=10)


# @build 02.04 naive_softmax
# The softmax straight from its definition, to watch it fail: e to the
# power of each score, divided by the sum of those along the row.
def naive_softmax(x):
    e = x.exp()
    return e / e.sum(1, keepdim=True)
# @end


def main():
    cfg = lab.config(CONFIG)
    rng = np.random.default_rng(cfg.seed)
    scores = torch.tensor([[2.0, 1.0, 0.1], [100.0, 99.0, 0.0], [1000.0, 999.0, 0.0]])
    print("scores                   naive softmax                  F.softmax")
    for row, naive, safe in zip(scores.tolist(), naive_softmax(scores).tolist(), F.softmax(scores, 1).tolist()):
        print(f"{'[' + ', '.join(f'{v:g}' for v in row) + ']':24s} {'[' + ', '.join(f'{p:.4f}' for p in naive) + ']':30s} "
              f"[{', '.join(f'{p:.4f}' for p in safe)}]")
    wrong = torch.tensor([[0.0, 50.0, -50.0], [-80.0, 0.0, 80.0]], dtype=torch.float64, requires_grad=True)
    target = torch.tensor([0, 1])
    loss = F.cross_entropy(wrong, target)
    print(f"cross-entropy of confidently wrong scores: {loss.item():.4f} (finite)")
    some = torch.tensor(rng.integers(0, 3, 4))
    ok = torch.autograd.gradcheck(lambda s: F.cross_entropy(s, some),
                                  (torch.tensor(rng.standard_normal((4, 3)) * 5, requires_grad=True),))
    print(f"gradcheck of cross_entropy: {'ok' if ok else 'FAILED'}")
    flat = torch.zeros(8, cfg.classes)
    labels = torch.tensor(rng.integers(0, cfg.classes, 8))
    print(f"cross-entropy of equal scores over {cfg.classes} classes: "
          f"{F.cross_entropy(flat, labels).item():.4f}; log({cfg.classes}) = {math.log(cfg.classes):.4f}")


if __name__ == "__main__":
    main()
