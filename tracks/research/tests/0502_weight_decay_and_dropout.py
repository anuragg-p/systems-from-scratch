"""05.02 Weight decay and dropout

Dropout drops a fraction p of the numbers and scales the rest by 1 / (1 - p) in training, its
gradient goes only where it kept a number, it does nothing in eval mode, and a seed fixes its
mask; and on 2000 MNIST digits, dropout as the paper places it (Srivastava et al., table 2)
lowers the test error, and so does weight decay, a little.
"""


def test(t):
    T = t.track
    T.need(t, "mnist")
    T.inside(t, __file__)
    ours = T.experiment(t, "regularise", "seeds=2")
    mean = lambda k: sum(s["test_error"] for s in T.summaries(ours, k)) / 2
    neither, decay, drop = mean("neither"), mean("weight-decay"), mean("dropout")
    t.check(drop < neither - 0.5, f"dropout should lower the test error: {drop:.2f} against {neither:.2f}")
    t.check(decay < neither, f"weight decay should lower it, if less: {decay:.2f} against {neither:.2f}")
    theirs = T.on_torch(t, "regularise", "seeds=1", "epochs=20")
    for s in (T.summaries(theirs, k)[0] for k in ("neither", "dropout")):
        t.check(s["test_error"] < 15, f"on PyTorch: {s}")


def inside(S):
    import numpy as np
    import engine
    import torch

    F = engine.nn.functional
    x = engine.ones(400, 250, requires_grad=True)
    engine.manual_seed(0)
    out = F.dropout(x, 0.3)
    kept = out.data != 0
    assert abs(1 - kept.mean() - 0.3) < 0.01 and np.allclose(out.data[kept], 1 / 0.7), kept.mean()
    g = np.random.default_rng(0).standard_normal((400, 250)).astype(np.float32)
    out.backward(engine.tensor(g))
    assert np.allclose(x.grad.data, np.where(kept, g / 0.7, 0)), "the gradient goes only where a number was kept"
    engine.manual_seed(0)
    assert np.array_equal(F.dropout(engine.ones(400, 250), 0.3).data, out.data), "a seed fixes the mask"
    assert F.dropout(x, 0.3, training=False) is x and F.dropout(x, 0.0) is x
    ours = engine.nn.Sequential(engine.nn.Linear(5, 4), engine.nn.Dropout(0.5), engine.nn.Linear(4, 2)).double()
    theirs = S.copy_weights(ours, torch.nn.Sequential(torch.nn.Linear(5, 4), torch.nn.Dropout(0.5), torch.nn.Linear(4, 2)))
    assert list(ours.state_dict()) == list(theirs.state_dict()), "Dropout has no weights"
    ours.eval()
    theirs.eval()
    v = np.random.default_rng(1).standard_normal((3, 5))
    S.same(ours(engine.tensor(v)), theirs(torch.tensor(v)), "eval mode: dropout does nothing")
    ours.train()
    a, b = ours(engine.tensor(v)), ours(engine.tensor(v))
    assert not np.array_equal(a.data, b.data), "training mode: a new mask every call"
