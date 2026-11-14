"""03.02 Momentum: the zigzag in a narrow valley

SGD with momentum, with dampening, and Nesterov's take the same steps as PyTorch's (1e-6,
float64); in the valley momentum gets to the bottom in under half the steps plain descent needs,
the same number of steps on either engine; and on MNIST momentum at the same rate ends lower.
"""


def test(t):
    T = t.track
    T.need(t, "mnist")
    T.inside(t, __file__)
    ours = T.experiment(t, "momentum", "seeds=2")
    plain = T.value(ours.out, r"momentum 0\.0: (\d+) steps")
    fast = T.value(ours.out, r"momentum 0\.8: (\d+) steps")
    t.check(fast < plain / 2, f"momentum should reach the valley floor in under half the steps: {fast} against {plain}")
    for a, b in zip(T.summaries(ours, "lr0.05-m0"), T.summaries(ours, "lr0.05-m0.9")):
        t.check(b["train_loss"] < a["train_loss"] - 0.05, f"momentum at the same rate should end lower: {a} {b}")
    theirs = T.on_torch(t, "momentum", "seeds=1", "runs=[[0.05, 0.9]]")
    valley = [l for l in ours.out.splitlines() if l.startswith("valley")]
    t.check(valley == [l for l in theirs.out.splitlines() if l.startswith("valley")],
            f"the valley has no randomness: PyTorch should take the same steps:\n{theirs.out}")


def inside(S):
    import numpy as np
    import engine
    import torch
    from experiments.loop import mlp

    rng = np.random.default_rng(0)
    x, y = rng.standard_normal((64, 20)), rng.integers(0, 10, 64)
    for settings in (dict(momentum=0.9), dict(momentum=0.9, dampening=0.3), dict(momentum=0.8, nesterov=True)):
        engine.manual_seed(0)
        ours = mlp(engine, [20, 16, 10]).double()
        theirs = S.copy_weights(ours, mlp(torch, [20, 16, 10]))
        opts = [engine.optim.SGD(ours.parameters(), lr=0.05, **settings),
                torch.optim.SGD(theirs.parameters(), lr=0.05, **settings)]
        for step in range(6):
            for model, opt, m in ((ours, opts[0], engine), (theirs, opts[1], torch)):
                loss = m.nn.functional.cross_entropy(model(m.tensor(x[step::6])), m.tensor(y[step::6]))
                opt.zero_grad()
                loss.backward()
                opt.step()
            for k, (p, q) in enumerate(zip(S.params(ours), S.params(theirs))):
                S.same(p, q, f"SGD({settings}): parameter {k} after step {step}")
    try:
        engine.optim.SGD([engine.tensor([1.0], requires_grad=True)], lr=0.1, nesterov=True)
        raise AssertionError("Nesterov without momentum should be refused, as PyTorch refuses it")
    except ValueError:
        pass
