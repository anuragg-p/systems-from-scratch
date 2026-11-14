"""02.03 Matrix multiply, sums and indexing

Matrix products (of matrices, vectors and stacks), sums and means along any dimension, indexing
of every kind, transposes and reshapes give PyTorch's values and gradients (1e-6, float64);
no_grad records no graph and in-place updates need it; and the two groups, trained as matrices,
are told apart on either engine with the same numbers.
"""


def test(t):
    T = t.track
    T.inside(t, __file__)
    ours = T.experiment(t, "groups_tensors", "steps=300", "seeds=2")
    theirs = T.on_torch(t, "groups_tensors", "steps=300", "seeds=2")
    for seed, (a, b) in enumerate(zip(T.summaries(ours), T.summaries(theirs))):
        t.check(a["accuracy"] >= 0.97 and a["test_accuracy"] >= 0.95, f"seed {seed}: {a}")
        t.check(abs(a["test_accuracy"] - b["test_accuracy"]) <= 0.01 and abs(a["loss"] - b["loss"]) < 0.01,
                f"seed {seed}: the same weights and steps, but ours {a} and PyTorch's {b}")


def inside(S):
    import numpy as np
    import engine

    ops = [
        ("matrix @ matrix", lambda m, a, b: a @ b, [(5, 3), (3, 4)]),
        ("matrix @ vector", lambda m, a, b: a @ b, [(5, 3), (3,)]),
        ("vector @ matrix", lambda m, a, b: a @ b, [(3,), (3, 4)]),
        ("stack @ matrix", lambda m, a, b: a @ b, [(2, 5, 3), (3, 4)]),
        ("matmul()", lambda m, a, b: m.matmul(a, b).tanh(), [(4, 3), (3, 2)]),
        ("sum", lambda m, a: a.sum() * a, [(4, 3)]),
        ("sum(0)", lambda m, a: a.sum(0), [(4, 3)]),
        ("sum(1, keepdim)", lambda m, a: a.sum(1, keepdim=True) * a, [(4, 3)]),
        ("sum((0, 2))", lambda m, a: a.sum((0, 2)), [(2, 3, 4)]),
        ("mean(-1, keepdim)", lambda m, a: a - a.mean(-1, keepdim=True), [(4, 3)]),
        ("mean", lambda m, a: a.mean() + a.mean(0).sum(), [(4, 3)]),
        ("x[1]", lambda m, a: a[1] * 2, [(4, 3)]),
        ("x[1:3, ::2]", lambda m, a: a[1:3, ::2] ** 2, [(4, 3)]),
        ("x[[0, 2, 2], [1, 0, 1]]", lambda m, a: a[np.array([0, 2, 2]), np.array([1, 0, 1])], [(4, 3)]),
        ("x[:, 0]", lambda m, a: a[:, 0].exp(), [(4, 3)]),
        ("x[tensor]", lambda m, a: a[m.tensor([3, 0, 3])], [(4, 3)]),
        ("transpose", lambda m, a: a.transpose(0, 1) * 2, [(4, 3)]),
        (".T", lambda m, a, b: a.T @ b, [(3, 5), (3, 4)]),
        ("reshape", lambda m, a: a.reshape(2, 6).tanh(), [(4, 3)]),
        ("view(-1)", lambda m, a: a.view(-1) * a.view(12), [(4, 3)]),
        ("float()", lambda m, a: a.float().double() * 2, [(4, 3)]),
    ]
    for name, fn, shapes in ops:
        S.same_op(fn, shapes, name)
    x = engine.tensor([1.0, 2.0], requires_grad=True)
    with engine.no_grad():
        y = x * 2
    assert not y.requires_grad and (x * 2).requires_grad, "no_grad records nothing, and only inside"
    try:
        with engine.no_grad():
            raise KeyError
    except KeyError:
        pass
    assert (x * 2).requires_grad, "no_grad turns recording back on after an exception"
    try:
        x -= 1.0
        raise AssertionError("an in-place change to a leaf that needs a gradient should fail outside no_grad")
    except RuntimeError:
        pass
    data = x.data
    with engine.no_grad():
        x -= engine.tensor([0.5, 0.5])
    assert x.data is data and x.data.tolist() == [0.5, 1.5], "in place, inside no_grad"
    a = engine.tensor([[1.0, 5.0, 2.0], [7.0, 0.0, 3.0]])
    assert a.argmax(1).tolist() == [1, 0] and a.argmax().item() == 3
    assert ((a > 1.5) == (a >= 2.0)).float().mean().item() == 1.0
    assert (a < 1).tolist() == [[False, False, False], [False, True, False]]
