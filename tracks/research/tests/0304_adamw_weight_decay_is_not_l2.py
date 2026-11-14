"""03.04 AdamW: weight decay is not L2

AdamW's steps are PyTorch's (1e-6, float64); for SGD an L2 term and weight decay are the same
step, for Adam they are not; with L2 in Adam, weights that get no gradient from the data are
driven to 0 whatever the decay, while AdamW shrinks them by exactly (1 - lr * wd) a step, on
either engine.
"""


def test(t):
    T = t.track
    T.need(t, "mnist")
    T.inside(t, __file__)
    small = ["epochs=2", "n_grid=500", "grid_lrs=[0.001]", "adam_wds=[0.0]", "adamw_wds=[0.1]", "seeds=1"]
    ours = T.experiment(t, "adamw", *small)
    t.check(T.value(ours.out, r"L2 and weight decay differ by at most (\S+)") < 1e-12, ours.out)
    t.check(T.value(ours.out, r"L2 and AdamW differ by up to (\S+);") > 1e-4, ours.out)
    got = idle(ours.out)
    steps = math.ceil(60000 / 128)
    want = {("AdamW", 0.01): 100 * (1 - 1e-5) ** steps, ("AdamW", 1.0): 100 * (1 - 1e-3) ** steps}
    t.check(len(got) == 4 and all(v < 1 for (name, _), v in got.items() if name == "Adam + L2"),
            f"with L2 in Adam the idle weights should go to 0 whatever the decay: {got}")
    for key, v in want.items():
        t.check(abs(got.get(key, -1) - v) < 0.1, f"{key}: idle weights at {got.get(key)}%, (1 - lr wd)^{steps} is {v:.2f}%")
    theirs = T.on_torch(t, "adamw", *small)
    t.check(idle(theirs.out) == got, f"PyTorch should shrink the idle weights the same:\n{theirs.out}")


def idle(out):
    """{(optimiser, wd): the idle pixels' weights as a % of their starting size} from part 2."""
    found = re.findall(r"^ +(Adam \+ L2|AdamW) +wd (\S+) *: after one pass, idle pixels' weights at +(\S+)%", out, re.M)
    return {(name, float(wd)): float(p) for name, wd, p in found}


def inside(S):
    import numpy as np
    import engine
    import torch
    from experiments.loop import mlp

    rng = np.random.default_rng(0)
    x, y = rng.standard_normal((80, 20)), rng.integers(0, 10, 80)
    for settings in (dict(), dict(lr=0.01, weight_decay=0.5)):
        engine.manual_seed(2)
        ours = mlp(engine, [20, 16, 10]).double()
        theirs = S.copy_weights(ours, mlp(torch, [20, 16, 10]))
        opts = [engine.optim.AdamW(ours.parameters(), **settings), torch.optim.AdamW(theirs.parameters(), **settings)]
        for step in range(10):
            for model, opt, m in ((ours, opts[0], engine), (theirs, opts[1], torch)):
                loss = m.nn.functional.cross_entropy(model(m.tensor(x[step::10])), m.tensor(y[step::10]))
                opt.zero_grad()
                loss.backward()
                opt.step()
            for k, (p, q) in enumerate(zip(S.params(ours), S.params(theirs))):
                S.same(p, q, f"AdamW({settings}): parameter {k} after step {step}")
    p = engine.tensor([1.0, -2.0], requires_grad=True)
    q = engine.tensor([1.0, -2.0], requires_grad=True)
    a, b = engine.optim.Adam([p], lr=0.1, weight_decay=0.1), engine.optim.AdamW([q], lr=0.1, weight_decay=0.1)
    for t_, opt in ((p, a), (q, b)):
        (t_ * engine.tensor([0.0, 1.0])).sum().backward()
        opt.step()
    assert np.abs(p.data - q.data).max() > 1e-3, (p, q)
    assert abs(q.data[0] - 0.99) < 1e-7, "AdamW: a weight with no gradient shrinks by lr * wd and no more"


import math  # noqa: E402
import re  # noqa: E402
