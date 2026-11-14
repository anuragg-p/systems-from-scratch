"""04.02 Initialisation: keeping the signal the same size

The gains are PyTorch's, and Glorot's and He's weights have the spread their formulas give; and a
30-layer relu network learns nothing in one pass started as nn.Linear starts it, barely moves
started with Glorot's weights, and trains started with He's (He et al., figure 3), on either
engine.
"""


def test(t):
    T = t.track
    T.need(t, "mnist")
    T.inside(t, __file__)
    ours = T.experiment(t, "init", "seeds=2")
    default, glorot, he = (T.summaries(ours, k) for k in ("default", "glorot", "he"))
    t.check(all(s["train_loss"] > 2.29 for s in default), f"nn.Linear's start: {default}")
    t.check(sum(s["train_loss"] for s in glorot) / 2 > 2.0, f"Glorot's start should stall at 30 layers: {glorot}")
    t.check(all(s["train_loss"] < 1.2 for s in he), f"He's start should train: {he}")
    theirs = T.on_torch(t, "init", "seeds=1", "inits=['default', 'he']")
    d, h = T.summaries(theirs, "default")[0], T.summaries(theirs, "he")[0]
    t.check(d["train_loss"] > 2.29 and h["train_loss"] < 1.2, f"on PyTorch: {d} {h}")


def inside(S):
    import math
    import numpy as np
    import engine
    import torch

    init = engine.nn.init
    for name, param in (("linear", None), ("sigmoid", None), ("tanh", None), ("relu", None), ("leaky_relu", 0.2)):
        assert abs(init.calculate_gain(name, param) - torch.nn.init.calculate_gain(name, param)) < 1e-12, name
    engine.manual_seed(0)
    w = engine.zeros(512, 256)
    checks = [
        (init.kaiming_normal_, dict(nonlinearity="relu"), math.sqrt(2 / 256)),
        (init.kaiming_normal_, dict(nonlinearity="relu", mode="fan_out"), math.sqrt(2 / 512)),
        (init.kaiming_uniform_, dict(nonlinearity="relu"), math.sqrt(2 / 256)),
        (init.xavier_normal_, dict(), math.sqrt(2 / (256 + 512))),
        (init.xavier_uniform_, dict(gain=2.0), 2 * math.sqrt(2 / (256 + 512))),
        (init.normal_, dict(std=0.05), 0.05),
    ]
    for fn, kw, sd in checks:
        out = fn(w, **kw)
        assert out is w and abs(w.data.std() / sd - 1) < 0.02 and abs(w.data.mean()) < 0.02 * sd, (fn.__name__, kw)
    init.kaiming_uniform_(w, nonlinearity="relu")
    assert np.abs(w.data).max() <= math.sqrt(6 / 256), "the uniform bound"
    init.zeros_(w)
    assert not w.data.any()
    try:
        init.xavier_normal_(engine.zeros(5))
        raise AssertionError("a vector has no fan_in and fan_out")
    except ValueError:
        pass
