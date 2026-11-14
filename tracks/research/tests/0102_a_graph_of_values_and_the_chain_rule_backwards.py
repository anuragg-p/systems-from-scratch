"""01.02 A graph of values, and the chain rule backwards

backward() over a graph of scalar Values gives PyTorch's gradients (1e-6, float64) for every
operation, alone and combined, with a Value used more than once; a graph thousands of nodes deep
does not overflow the stack; and the neuron experiment agrees with the nudge.
"""


def test(t):
    T = t.track
    T.inside(t, __file__)
    r = T.experiment(t, "graph")
    t.check(T.value(r.out, r"largest difference from the nudge: (\S+)") < 1e-6, f"backward and nudge differ:\n{r.out}")
    t.check("o = tanh(n)      tanh      0.6640     1.0000" in r.out, f"the output node:\n{r.out}")


def inside(S):
    import torch
    from engine.value import Value

    cases = {
        "a * b + b ** 3": lambda a, b: a * b + b ** 3,
        "(a - b) / (a * a + 1)": lambda a, b: (a - b) / (a * a + 1),
        "log(exp(a) + b)": lambda a, b: (a.exp() + b).log(),
        "tanh(a b) + relu(a - b)": lambda a, b: (a * b).tanh() + (a - b).relu(),
        "a used four times": lambda a, b: a * a * a + a,
        "plain numbers on the left": lambda a, b: 2 - a / 3 + 1 / b,
        "relu that is off": lambda a, b: (b - a).relu() * a,
    }
    for a0, b0 in ((0.7, 1.3), (-0.4, 2.1)):
        for name, fn in cases.items():
            a, b = Value(a0), Value(b0)
            out = fn(a, b)
            out.backward()
            ta = torch.tensor(a0, dtype=torch.float64, requires_grad=True)
            tb = torch.tensor(b0, dtype=torch.float64, requires_grad=True)
            ref = fn(ta, tb)
            ref.backward()
            S.same(out.data, ref, f"{name} at {a0}, {b0}")
            S.same(a.grad, ta.grad, f"d({name})/da at {a0}, {b0}")
            S.same(b.grad, tb.grad, f"d({name})/db at {a0}, {b0}")
    x = Value(1.0)
    s = x
    for _ in range(5000):
        s = s + x * 0.001
    s.backward()
    assert abs(x.grad - 6.0) < 1e-9, x.grad
