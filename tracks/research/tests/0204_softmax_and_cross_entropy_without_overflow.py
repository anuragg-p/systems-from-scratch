"""02.04 Softmax and cross-entropy without overflow

log_softmax, softmax and cross_entropy (every reduction) give PyTorch's values and gradients
(1e-6, float64), for scores of any size, finite where the obvious formula is not; a class list of
the wrong length is an error; a classifier that knows nothing loses log(classes); and the
experiment prints the same on both engines.
"""


def test(t):
    T = t.track
    T.inside(t, __file__)
    ours = T.experiment(t, "softmax")
    t.check("[1000, 999, 0]           [nan, nan, 0.0000]             [0.7311, 0.2689, 0.0000]" in ours.out,
            f"the naive softmax should overflow where F.softmax does not:\n{ours.out}")
    t.check("gradcheck of cross_entropy: ok" in ours.out and "2.3026; log(10) = 2.3026" in ours.out, ours.out)
    theirs = T.on_torch(t, "softmax")
    t.check(ours.out == theirs.out, f"PyTorch prints otherwise:\n{theirs.out}\nours:\n{ours.out}")


def inside(S):
    import math
    import numpy as np
    import engine
    import torch
    from experiments.softmax import naive_softmax

    target = np.array([0, 2, 1, 2, 0])
    for scale in (1, 50, 1e4):
        S.same_op(lambda m, a: m.nn.functional.log_softmax(a * scale, 1), [(5, 3)], f"log_softmax, scores x{scale}")
        S.same_op(lambda m, a: m.nn.functional.softmax(a * scale, 0), [(5, 3)], f"softmax(dim 0), scores x{scale}")
        for reduction in ("mean", "sum", "none"):
            S.same_op(lambda m, a: m.nn.functional.cross_entropy(a * scale, m.tensor(target), reduction=reduction),
                      [(5, 3)], f"cross_entropy({reduction}), scores x{scale}")
    big = engine.tensor([[1e4, 0.0, -1e4]], dtype=engine.float64, requires_grad=True)
    loss = engine.nn.functional.cross_entropy(big, engine.tensor([2]))
    loss.backward()
    assert math.isfinite(loss.item()) and np.isfinite(big.grad.data).all(), (loss, big.grad)
    for bad in (lambda: engine.nn.functional.cross_entropy(engine.zeros(4, 3), engine.tensor([0, 1])),
                lambda: engine.nn.functional.cross_entropy(engine.zeros(2, 3), engine.tensor([0, 1]), reduction="x")):
        try:
            bad()
            raise AssertionError("should be a ValueError, as in PyTorch")
        except ValueError:
            pass
    flat = engine.nn.functional.cross_entropy(engine.zeros(6, 10), engine.tensor([3, 1, 4, 1, 5, 9]))
    assert abs(flat.item() - math.log(10)) < 1e-6, flat
    s = np.random.default_rng(0).standard_normal((4, 3))
    S.same(naive_softmax(engine.tensor(s)), torch.softmax(torch.tensor(s), 1), "the naive softmax, small scores")
