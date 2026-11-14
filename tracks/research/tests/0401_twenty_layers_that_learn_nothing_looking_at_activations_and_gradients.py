"""04.01 Twenty layers that learn nothing: looking at activations and gradients

abs, var and std give PyTorch's values and gradients (1e-6, float64), and retain_grad keeps a
layer's gradient as PyTorch's does; twenty layers started as nn.Linear starts them pass almost
nothing from the input to the output or back, and one pass of training leaves the loss at
log(10), on either engine.
"""

import math


def test(t):
    T = t.track
    T.need(t, "mnist")
    T.inside(t, __file__)
    ours = T.experiment(t, "deep_stats", "seeds=2", "acts=['relu']")
    for s in T.summaries(ours, "relu"):
        t.check(abs(s["train_loss"] - math.log(10)) < 0.01, f"twenty relu layers should learn nothing: {s}")
    first = T.value(ours.out, r"^ +1 +(\S+) +\S+ +\S+$")
    last = T.value(ours.out, r"^ +19 +(\S+) +\S+ +\S+$")
    grad = T.value(ours.out, r"^ +1 +\S+ +(\S+) +\S+$")
    t.check(last < 1e-6 * first and grad < 1e-8, f"the spread should vanish with depth, and the gradient at layer 1:\n{ours.out}")
    theirs = T.on_torch(t, "deep_stats", "seeds=1", "acts=['relu']")
    loss = T.summaries(theirs, "relu")[0]["train_loss"]
    t.check(abs(loss - math.log(10)) < 0.01, f"on PyTorch, with its own nn.Linear start, too: {loss}")


def inside(S):
    import numpy as np
    import engine
    import torch
    from experiments.deep import layer_stats, network

    S.same_op(lambda m, a: a.abs() * a, [(4, 3)], "abs")
    for unbiased in (True, False):
        S.same_op(lambda m, a: a.var(0, unbiased=unbiased) * a.var(unbiased=unbiased), [(5, 3)], f"var({unbiased})")
        S.same_op(lambda m, a: a.std(1, unbiased=unbiased, keepdim=True) * a, [(5, 3)], f"std({unbiased})")
    ours, theirs = S.pair([np.random.default_rng(0).standard_normal((4, 3)),
                           np.random.default_rng(1).standard_normal((3, 2))])
    hidden = []
    for m, a, b in ((engine, *ours), (torch, *theirs)):
        h = (a @ b).tanh()
        h.retain_grad()
        (h * h).sum().backward()
        hidden.append(h.grad)
    S.same(hidden[0], hidden[1], "a kept gradient of a layer's output")
    engine.manual_seed(0)
    model = network(engine, 6, 16)
    rng = np.random.default_rng(2)
    stats = layer_stats(engine, model, engine.tensor(rng.standard_normal((32, 784)).astype(np.float32)),
                        engine.tensor(rng.integers(0, 10, 32)))
    assert len(stats) == 5 and all(set(s) == {"spread", "grad", "stuck"} for s in stats), stats
    assert all(p.grad is None for p in model.parameters()), "layer_stats leaves no gradients behind"
