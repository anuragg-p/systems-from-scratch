"""05.04 Double descent: when a bigger model overfits less

The fit is the least-squares solution with the smallest weights, the one gradient descent from
zero reaches; past p = n it fits the training set exactly; and the test error rises to a peak at
p = n, then falls below the best it reached before the peak (Nakkiran et al.'s model-wise double
descent, here on random features).
"""


def test(t):
    T = t.track
    T.need(t, "mnist")
    T.inside(t, __file__)
    r = T.experiment(t, "double_descent", "seeds=2")
    peak = T.value(r.out, r"^peak at p = (\d+) ")
    top = T.value(r.out, r"^peak at p = \d+ \((\S+)%\)")
    before = T.value(r.out, r"best below it (\S+)%")
    end = T.value(r.out, r"at p = 10000 (\S+)%")
    t.check(950 <= peak <= 1050, f"the peak should sit at p = n = 1000:\n{r.out}")
    t.check(top > before + 30 and end < before, f"a peak far above, then lower than ever:\n{r.out}")
    for line in r.out.splitlines():
        m = re.match(r"^ +(\d+) +(\S+) ", line)
        if m and int(m.group(1)) >= 1050:
            t.check(float(m.group(2)) < 1e-3, f"past n, the training set should be fitted exactly: {line}")


def inside(S):
    import numpy as np
    from experiments.double_descent import features, fit_min_norm

    rng = np.random.default_rng(0)
    for n, p in ((40, 15), (20, 50)):
        a = features(rng.standard_normal((n, 30)), rng.standard_normal((30, p)) / np.sqrt(30))
        assert a.dtype == np.float64 and (a >= 0).all() and a.shape == (n, p)
        y = rng.standard_normal((n, 3))
        b = fit_min_norm(a, y)
        assert np.allclose(b, np.linalg.pinv(a) @ y, atol=1e-8), f"n={n}, p={p}: not the smallest least-squares fit"
    assert np.abs(a @ b - y).max() < 1e-8, "with more features than points, it fits them exactly"
    w = np.zeros_like(b)
    lr = 1 / np.linalg.norm(a, 2) ** 2
    for _ in range(20000):
        w -= lr * a.T @ (a @ w - y)
    assert np.abs(w - b).max() < 1e-6, "gradient descent from zero reaches the same weights"


import re  # noqa: E402
