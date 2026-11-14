"""01.04 Training it: a loss that goes down

The two groups of points are made the same way from a seed, half in each group; the hinge loss is
what its formula says; and training the scalar network brings the loss down by more than four
times and gets at least 95% of the training points right, on every seed.
"""

import json


def test(t):
    T = t.track
    T.inside(t, __file__)
    r = T.experiment(t, "two_groups", "seeds=2")
    for seed, s in enumerate(T.summaries(r)):
        first = json.loads(open(f"{r.runs}/seed{seed}/log.jsonl").readline())
        t.check(s["accuracy"] >= 0.95, f"seed {seed}: training accuracy {s['accuracy']}")
        t.check(s["loss"] < first["loss"] / 4, f"seed {seed}: loss {first['loss']} -> {s['loss']}")
        t.check(s["test_accuracy"] >= 0.85, f"seed {seed}: accuracy on fresh points {s['test_accuracy']}")


def inside(S):
    import numpy as np
    from data.points import two_groups
    from engine.value import MLP
    from experiments.two_groups import hinge_loss

    x, y = two_groups(101, 0.1, np.random.default_rng(5))
    assert x.shape == (101, 2) and x.dtype == np.float32 and y.dtype == np.int64, (x.shape, x.dtype, y.dtype)
    assert sorted(set(y.tolist())) == [0, 1] and int((y == 0).sum()) == 50, "half in each group"
    x2, y2 = two_groups(101, 0.1, np.random.default_rng(5))
    assert np.array_equal(x, x2) and np.array_equal(y, y2), "the same seed, the same points"
    upper = x[y == 0]
    assert upper[:, 1].mean() > 0.4 and x[y == 1][:, 1].mean() < 0.1, "group 0 above, group 1 below"
    model = MLP(2, [4, 1], seed=0)
    loss, accuracy = hinge_loss(model, x[:10], y[:10])
    scores = [model([float(a), float(b)]).data for a, b in x[:10]]
    t = [1.0 if v == 1 else -1.0 for v in y[:10]]
    want = np.mean([max(0.0, 1 - ti * si) for ti, si in zip(t, scores)])
    assert abs(loss.data - want) < 1e-12, (loss.data, want)
    assert accuracy == np.mean([(si > 0) == (ti > 0) for ti, si in zip(t, scores)])
