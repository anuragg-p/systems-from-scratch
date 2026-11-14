"""00.01 One experiment, end to end

The curve fit's pieces each do their job (points of a noisy sine, the polynomial's columns, the
loss, a gradient that agrees with a nudge, descent that gets as low as least squares does), and
the whole experiment fits the curve on every seed.
"""


def test(t):
    T = t.track
    T.inside(t, __file__)
    r = T.experiment(t, "curve", "seeds=3")
    for seed, s in enumerate(T.summaries(r)):
        t.check(s["train_loss"] < 0.08 and s["test_loss"] < 0.1,
                f"seed {seed}: the cubic should fit sin(pi x) to the noise (0.04): {s}")
    rows = [l for l in open(f"{r.runs}/seed0/log.jsonl")]
    t.check(len(rows) == 21, f"a line every 100 steps of 2000, and one at the end: {len(rows)} lines")


def inside(S):
    import numpy as np
    from experiments import curve

    rng = np.random.default_rng(0)
    x, y = curve.make_data(200, 0.2, rng)
    assert x.shape == (200,) and y.shape == (200,), (x.shape, y.shape)
    assert np.abs(x).max() <= 1, "x in [-1, 1]"
    noise = y - np.sin(np.pi * x)
    assert 0.15 < noise.std() < 0.25, f"noise of 0.2: {noise.std()}"
    X = curve.features(x, 3)
    assert X.shape == (200, 4) and np.allclose(X[:, 0], 1) and np.allclose(X[:, 3], x ** 3), X[:2]
    w = rng.standard_normal(4)
    assert abs(curve.loss(w, X, y) - np.mean((X @ w - y) ** 2)) < 1e-12
    g = curve.gradient(w, X, y)
    h = 1e-6
    for k in range(4):
        e = np.zeros(4)
        e[k] = h
        nudged = (curve.loss(w + e, X, y) - curve.loss(w - e, X, y)) / (2 * h)
        assert abs(g[k] - nudged) < 1e-6 * (1 + abs(nudged)), f"d loss / d w{k}: {g[k]} by hand, {nudged} nudged"
    seen = []
    fitted = curve.fit(X, y, 0.5, 2000, lambda step, l: seen.append((step, l)))
    best = np.linalg.lstsq(X, y, rcond=None)[0]
    assert curve.loss(fitted, X, y) < 1.05 * curve.loss(best, X, y), (fitted, best)
    assert [s for s, _ in seen] == list(range(0, 2001, 100)), "report every 100 steps and after the last"
    assert seen[-1][1] < seen[0][1] / 5, f"the loss goes down: {seen[0]} -> {seen[-1]}"
