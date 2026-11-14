"""05.03 More data for free: augmentation

shift moves each image by its own whole number of pixels, at most k each way, and fills what
comes in from the edge; and training on images shifted anew every pass lowers the test error of
the 2000-digit network by more than a point and a half on every seed, on either engine.
"""


def test(t):
    T = t.track
    T.need(t, "mnist")
    T.inside(t, __file__)
    ours = T.experiment(t, "augment", "seeds=2", "shifts=[0, 2]")
    for a, b in zip(T.summaries(ours, "shift0"), T.summaries(ours, "shift2")):
        t.check(b["test_error"] < a["test_error"] - 1.5, f"shifting should lower the test error: {a} {b}")
    theirs = T.on_torch(t, "augment", "seeds=1", "shifts=[0, 2]", "epochs=20")
    a, b = T.summaries(theirs, "shift0")[0], T.summaries(theirs, "shift2")[0]
    t.check(b["test_error"] < a["test_error"], f"on PyTorch: {a} {b}")


def inside(S):
    import numpy as np
    from data.augment import shift

    rng = np.random.default_rng(0)
    x = rng.random((50, 784)).astype(np.float32)
    assert np.array_equal(shift(x, 0, rng, -1.0), x), "k = 0 changes nothing"
    dots = np.full((200, 28, 28), -1.0, dtype=np.float32)
    dots[:, 14, 14] = 5.0
    moved = shift(dots.reshape(200, 784), 2, np.random.default_rng(1), -1.0).reshape(200, 28, 28)
    where = [tuple(np.argwhere(m == 5.0)[0]) for m in moved]
    assert all((m == 5.0).sum() == 1 and (m == -1.0).sum() == 783 for m in moved), "one bright pixel each, moved"
    offsets = {(r - 14, c - 14) for r, c in where}
    assert offsets <= {(dr, dc) for dr in range(-2, 3) for dc in range(-2, 3)} and len(offsets) > 15, offsets
    edge = np.zeros((10, 28, 28), dtype=np.float32)
    out = shift(edge.reshape(10, 784) + 3.0, 2, np.random.default_rng(2), -9.0).reshape(10, 28, 28)
    assert (out == -9.0).any() and set(np.unique(out).tolist()) <= {3.0, -9.0}, "the fill comes in from the edge"
