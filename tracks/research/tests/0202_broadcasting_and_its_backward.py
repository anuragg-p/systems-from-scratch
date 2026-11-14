"""02.02 Broadcasting, and its backward

Operations on tensors of different shapes give PyTorch's values and gradients (1e-6, float64),
each gradient in its own input's shape; unbroadcast sums over exactly the repeated dimensions;
gradcheck passes a right gradient and catches a wrong one; and the experiment prints the same on
both engines.
"""


def test(t):
    T = t.track
    T.inside(t, __file__)
    ours = T.experiment(t, "broadcast")
    t.check(ours.out.count(" ok\n") == 5 and "FAILED" not in ours.out, f"gradcheck on every pair:\n{ours.out}")
    t.check("the bias's gradient is [5.0, 5.0, 5.0, 5.0]" in ours.out, ours.out)
    theirs = T.on_torch(t, "broadcast")
    t.check(ours.out == theirs.out, f"PyTorch prints otherwise:\n{theirs.out}\nours:\n{ours.out}")


def inside(S):
    import numpy as np
    import engine
    from engine.tensors import _result, unbroadcast

    pairs = [((3, 1), (1, 4)), ((2, 3, 4), (4,)), ((5, 4), ()), ((1, 4), (3, 1)), ((2, 1, 4), (3, 1)), ((4,), (2, 3, 4))]
    for sa, sb in pairs:
        S.same_op(lambda m, a, b: a + b, [sa, sb], f"{sa} + {sb}")
        S.same_op(lambda m, a, b: (a * b - b) * a, [sa, sb], f"{sa} * {sb}")
        S.same_op(lambda m, a, b: a / b, [sa, sb], f"{sa} / {sb}", positive=True)
    g = unbroadcast(np.ones((2, 3, 4)), (3, 1))
    assert g.shape == (3, 1) and np.all(g == 8), g
    assert unbroadcast(np.ones((5, 4)), ()).shape == () and unbroadcast(np.ones((5, 4)), ()) == 20
    x = engine.tensor(np.random.default_rng(0).standard_normal((3, 1)), requires_grad=True)
    w = engine.tensor(np.random.default_rng(1).standard_normal((1, 4)), requires_grad=True)
    assert engine.autograd.gradcheck(lambda a, b: (a * b).tanh() + a, (x, w)) is True
    assert x.grad is None and w.grad is None, "gradcheck leaves the gradients as they were"

    def wrong_square(a):
        out = _result(a.data ** 2, (a,), "WrongSquare")
        def _backward():
            a._accumulate(out.grad.data * a.data)          # the 2 left out
        out._backward = _backward
        return out
    try:
        engine.autograd.gradcheck(wrong_square, (x,))
        raise AssertionError("gradcheck passed a gradient that is half what it should be")
    except RuntimeError as e:
        assert "Jacobian mismatch" in str(e), e
