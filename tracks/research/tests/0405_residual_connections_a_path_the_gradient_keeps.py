"""04.05 Residual connections: a path the gradient keeps

Training steps of a residual network with batch norm are PyTorch's (1e-6, float64); a plain
network of 32 layers ends one pass far above one of 8, and with residual blocks the 32-layer one
trains about as well as the 8-layer one, on either engine.
"""


def test(t):
    T = t.track
    T.need(t, "mnist")
    T.inside(t, __file__)
    ours = T.experiment(t, "residual", "seeds=2")
    cost = {k: sum(s["train_cost"] for s in T.summaries(ours, k)) / 2
            for k in ("plain8", "plain32", "residual8", "residual32")}
    t.check(cost["plain32"] > 3 * cost["plain8"], f"the deeper plain network should train far worse: {cost}")
    t.check(cost["residual32"] < 1.5 * cost["residual8"] and cost["residual32"] < 0.25,
            f"with shortcuts, 32 layers should train about as well as 8: {cost}")
    theirs = T.on_torch(t, "residual", "seeds=1")
    cost = {k: T.summaries(theirs, k)[0]["train_cost"] for k in ("plain8", "plain32", "residual8", "residual32")}
    t.check(cost["plain32"] > 3 * cost["plain8"] and cost["residual32"] < 1.5 * cost["residual8"],
            f"on PyTorch: {cost}")


def inside(S):
    import numpy as np
    import engine
    import torch
    from experiments import residual

    class Block(torch.nn.Module):
        def __init__(self, width):
            super().__init__()
            self.a, self.bn_a = torch.nn.Linear(width, width), torch.nn.BatchNorm1d(width)
            self.b, self.bn_b = torch.nn.Linear(width, width), torch.nn.BatchNorm1d(width)

        def forward(self, x):
            return (x + self.bn_b(self.b(self.bn_a(self.a(x)).relu()))).relu()

    engine.manual_seed(0)
    ours = residual.residual(6, 8).double()
    theirs = torch.nn.Sequential(torch.nn.Linear(784, 8), torch.nn.ReLU(), Block(8), Block(8), torch.nn.Linear(8, 10))
    theirs = S.copy_weights(ours, theirs)
    rng = np.random.default_rng(0)
    x, y = rng.standard_normal((64, 784)), rng.integers(0, 10, 64)
    oo, ot = engine.optim.SGD(ours.parameters(), lr=0.05, momentum=0.9), torch.optim.SGD(theirs.parameters(), lr=0.05, momentum=0.9)
    for step in range(4):
        for model, opt, m in ((ours, oo, engine), (theirs, ot, torch)):
            loss = m.nn.functional.cross_entropy(model(m.tensor(x[step::4])), m.tensor(y[step::4]))
            opt.zero_grad()
            loss.backward()
            opt.step()
        for k, (p, q) in enumerate(zip(S.params(ours), S.params(theirs))):
            S.same(p, q, f"residual network: parameter {k} after step {step}")
    S.same(ours[2].bn_a.running_var, theirs[2].bn_a.running_var, "a block's running variance")
    assert len(residual.residual(32, 8)) == 18 and len(residual.plain(32, 8)) == 93, "15 blocks; 30 hidden layers"
