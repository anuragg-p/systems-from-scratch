"""03.01 MNIST in batches, and a learning rate that is too big

MNIST is read from its IDX files with the right shapes, labels and scale; batches cover the data
once each pass, in a new order; SGD's steps on a real network and real batches are PyTorch's
(1e-6, float64); and one pass at a good rate gets more than 93% of the test set right on either
engine, while a rate of 2 leaves the network guessing, most of its hidden units dead.
"""


def test(t):
    T = t.track
    T.need(t, "mnist")
    T.inside(t, __file__)
    ours = T.experiment(t, "mnist_lr", "lrs=[0.1, 2.0]", "seeds=2")
    for s in T.summaries(ours, "lr0.1"):
        t.check(s["test_accuracy"] > 0.93 and s["dead_units"] < 10, f"lr 0.1, one pass: {s}")
    for s in T.summaries(ours, "lr2"):
        t.check(s["train_loss"] > 1.5 and s["test_accuracy"] < 0.5, f"lr 2 should leave the network guessing: {s}")
        t.check(s["dead_units"] > 50, f"lr 2 should leave most of the 100 hidden units dead: {s}")
    theirs = T.on_torch(t, "mnist_lr", "lrs=[0.1]", "seeds=1")
    a, b = T.summaries(ours, "lr0.1")[0], T.summaries(theirs, "lr0.1")[0]
    t.check(b["test_accuracy"] > 0.93 and abs(a["test_accuracy"] - b["test_accuracy"]) < 0.015,
            f"PyTorch, from its own starting weights, should land as close: ours {a}, PyTorch's {b}")


def inside(S):
    import numpy as np
    import engine
    import torch
    from data import batches, fetch, mnist
    from experiments.loop import evaluate, mlp

    x, y = mnist.load("train")
    xt, yt = mnist.load("test")
    assert x.shape == (60000, 784) and x.dtype == np.float32 and y.dtype == np.int64, (x.shape, x.dtype, y.dtype)
    assert xt.shape == (10000, 784) and y[:5].tolist() == [5, 0, 4, 1, 9], y[:5]
    assert abs(x.mean()) < 0.01 and abs(x.std() - 1) < 0.02, (x.mean(), x.std())
    raw, _ = mnist.load("train", 100, False)
    assert raw.min() == 0 and raw.max() == 1, (raw.min(), raw.max())
    assert np.bincount(y).min() > 5000, np.bincount(y)
    labels = mnist.read_idx(fetch.path("mnist", "t10k-labels-idx1-ubyte.gz"))
    assert labels.shape == (10000,) and labels.dtype == np.uint8 and np.array_equal(labels, yt)
    rng = np.random.default_rng(0)
    first = list(batches(10, 3, rng))
    assert [len(b) for b in first] == [3, 3, 3, 1] and sorted(np.concatenate(first).tolist()) == list(range(10))
    assert not np.array_equal(np.concatenate(first), np.concatenate(list(batches(10, 3, rng)))), "a new order"

    engine.manual_seed(0)
    ours = mlp(engine, [784, 32, 10]).double()
    theirs = S.copy_weights(ours, mlp(torch, [784, 32, 10]))
    oo, ot = engine.optim.SGD(ours.parameters(), lr=0.1), torch.optim.SGD(theirs.parameters(), lr=0.1)
    for step, idx in enumerate(batches(640, 64, np.random.default_rng(1))):
        xb, yb = x[idx].astype(np.float64), y[idx]
        for model, opt, m in ((ours, oo, engine), (theirs, ot, torch)):
            loss = m.nn.functional.cross_entropy(model(m.from_numpy(xb)), m.from_numpy(yb))
            opt.zero_grad()
            loss.backward()
            opt.step()
        for k, (p, q) in enumerate(zip(S.params(ours), S.params(theirs))):
            S.same(p, q, f"SGD: parameter {k} after step {step}")
    loss, accuracy = evaluate(engine, ours, xt[:500].astype(np.float64), yt[:500])
    scores = theirs(torch.from_numpy(xt[:500].astype(np.float64)))
    S.same(loss, torch.nn.functional.cross_entropy(scores, torch.from_numpy(yt[:500])).item(), "evaluate's loss")
    assert abs(accuracy - (scores.argmax(1).numpy() == yt[:500]).mean()) < 1e-12, "evaluate's accuracy"
