"""02.01 The scalar engine is a thousand times too slow

Every elementwise operation of the tensor engine gives PyTorch's values and gradients (1e-6,
float64), alone and combined, with a tensor used twice and an explicit output gradient; tensors
are made with PyTorch's types; gradients of the tensors in between are dropped after backward();
and the speed experiment gets the scalar engine's gradients many times faster, on either engine.
"""


def test(t):
    T = t.track
    T.inside(t, __file__)
    r = T.experiment(t, "speed", "n=5000", "repeats=1")
    t.check(T.value(r.out, r"largest difference between their gradients: (\S+)") < 1e-9, r.out)
    t.check(T.value(r.out, r"the tensor is (\d+) times faster") > 20, f"tensors should be far faster:\n{r.out}")
    r = T.on_torch(t, "speed", "n=2000", "repeats=1")
    t.check(T.value(r.out, r"largest difference between their gradients: (\S+)") < 1e-9, f"on PyTorch:\n{r.out}")


def inside(S):
    import numpy as np
    import engine

    ops = {
        "a + b": (lambda m, a, b: a + b, False),
        "a * b": (lambda m, a, b: a * b, False),
        "a - b": (lambda m, a, b: a - b, False),
        "a / b": (lambda m, a, b: a / b, True),
        "-a + 2 - b": (lambda m, a, b: -a + 2 - b, False),
        "a ** 3, b ** 0.5": (lambda m, a, b: a ** 3 * b ** 0.5, True),
        "exp": (lambda m, a, b: a.exp() * b, False),
        "log": (lambda m, a, b: a.log() + b.log(), True),
        "tanh": (lambda m, a, b: (a * b + a).tanh(), False),
        "relu": (lambda m, a, b: (a - b).relu() * a, False),
        "functions": (lambda m, a, b: m.tanh(m.exp(a) * m.relu(b)) + m.log(m.exp(b)), False),
        "a used three times": (lambda m, a, b: a * a + a * b, False),
        "1 / b and 3 - a": (lambda m, a, b: 1 / b + (3 - a), True),
    }
    for name, (fn, positive) in ops.items():
        S.same_op(fn, [(3, 4), (3, 4)], name, positive=positive)
    S.same_op(lambda m, a, b: a * b, [(), ()], "single numbers")
    x = engine.tensor([1.0, 2.0], requires_grad=True)
    try:
        (x * 2).backward()
        raise AssertionError("backward() of two numbers with no gradient given should fail")
    except RuntimeError:
        pass
    y = x * 2
    z = (y * 3).tanh()
    z.backward(engine.ones_like(z))
    assert y.grad is None and x.grad is not None, "gradients in between are dropped, the leaves' kept"
    c = engine.tensor([1.0, 2.0])
    (x * c).backward(engine.ones_like(c))
    assert c.grad is None, "no gradient for a tensor that does not need one"
    assert engine.tensor([1.0]).dtype == engine.float32 and engine.tensor([1, 2]).dtype == engine.int64
    assert engine.tensor(np.array([1.0])).dtype == engine.float64, "a numpy array keeps its type"
    assert (engine.tensor([1.0]) * 2.0).dtype == engine.float32, "a plain number takes the tensor's type"
    a = np.arange(3.0)
    assert engine.from_numpy(a).data is a, "from_numpy shares the array"
    try:
        engine.tensor([1.0], requires_grad=True).numpy()
        raise AssertionError("numpy() of a tensor that requires grad should fail, as PyTorch's does")
    except RuntimeError:
        pass
