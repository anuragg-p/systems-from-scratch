"""03.03 Adam: a step size for each parameter

Adam's steps are PyTorch's (1e-6, float64), with its defaults, other betas and eps, and its L2
weight_decay; on logistic regression on MNIST, each at its best rate, Adam ends about where SGD
with Nesterov momentum does (the Adam paper's figure 1 says the same); and the comparison runs
on PyTorch to the same costs.
"""


def test(t):
    T = t.track
    T.need(t, "mnist")
    T.inside(t, __file__)
    short = ["models=['logistic']", "epochs=2", "seeds=2"]
    ours = T.experiment(t, "adam", *short)
    best = {}
    for opt in ("adam", "nesterov"):
        costs = [T.value(l, r"final cost (\S+)") for l in ours.out.splitlines() if l.strip().startswith(opt)]
        t.check(len(costs) == 3 and all(c < 0.6 for c in costs), f"{opt}: three rates, all training:\n{ours.out}")
        best[opt] = min(costs)
    t.check(abs(best["adam"] - best["nesterov"]) < 0.05 * best["nesterov"],
            f"logistic regression: Adam and Nesterov at their best rates should end within 5%: {best}")
    one = ["models=['logistic']", "epochs=1", "seeds=1", "adam_lrs=[0.003]", "sgd_lrs=[0.1]"]
    a, b = T.experiment(t, "adam", *one), T.on_torch(t, "adam", *one)
    for opt, lr in (("adam", "0.003"), ("nesterov", "0.1")):
        ca = T.value(a.out, rf"{opt} +lr {lr} +final cost (\S+)")
        cb = T.value(b.out, rf"{opt} +lr {lr} +final cost (\S+)")
        t.check(abs(ca - cb) < 0.02, f"{opt}: ours {ca}, PyTorch's {cb}, from different starting weights")


def inside(S):
    import numpy as np
    import engine
    import torch
    from experiments.loop import mlp

    rng = np.random.default_rng(0)
    x, y = rng.standard_normal((80, 20)), rng.integers(0, 10, 80)
    for settings in (dict(), dict(lr=0.01, betas=(0.8, 0.99), eps=1e-6), dict(lr=0.003, weight_decay=0.01)):
        engine.manual_seed(1)
        ours = mlp(engine, [20, 16, 10]).double()
        theirs = S.copy_weights(ours, mlp(torch, [20, 16, 10]))
        opts = [engine.optim.Adam(ours.parameters(), **settings), torch.optim.Adam(theirs.parameters(), **settings)]
        for step in range(10):
            for model, opt, m in ((ours, opts[0], engine), (theirs, opts[1], torch)):
                loss = m.nn.functional.cross_entropy(model(m.tensor(x[step::10])), m.tensor(y[step::10]))
                opt.zero_grad()
                loss.backward()
                opt.step()
            for k, (p, q) in enumerate(zip(S.params(ours), S.params(theirs))):
                S.same(p, q, f"Adam({settings}): parameter {k} after step {step}")
