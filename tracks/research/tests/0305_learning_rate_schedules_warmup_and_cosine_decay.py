"""03.05 Learning-rate schedules: warmup and cosine decay

warmup_cosine rises and falls as its formula says; LambdaLR sets the same rates as PyTorch's,
step by step, and Adam under it takes PyTorch's steps (1e-6, float64); on MNIST a warmup keeps a
high peak rate from throwing the first steps, and cosine decay ends lower than the best constant
rate, on either engine.
"""


def test(t):
    T = t.track
    T.need(t, "mnist")
    T.inside(t, __file__)
    ours = T.experiment(t, "schedule", "seeds=2",
                        "runs=[['constant', 0.001, 0], ['cosine', 0.003, 0], ['cosine', 0.01, 0], ['cosine', 0.01, 200]]")
    const, cosine = T.summaries(ours, "constant-lr0.001-w0"), T.summaries(ours, "cosine-lr0.003-w0")
    cold, warm = T.summaries(ours, "cosine-lr0.01-w0"), T.summaries(ours, "cosine-lr0.01-w200")
    for a, b in zip(const, cosine):
        t.check(b["train_cost"] < 0.8 * a["train_cost"], f"cosine from 3e-3 should end lower than constant 1e-3: {a} {b}")
    for a, b in zip(cold, warm):
        t.check(b["worst_early_loss"] < 2.4 < a["worst_early_loss"], f"a warmup should take the early spike away: {a} {b}")
    theirs = T.on_torch(t, "schedule", "seeds=1", "epochs=1", "runs=[['cosine', 0.01, 0], ['cosine', 0.01, 200]]")
    cold, warm = T.summaries(theirs, "cosine-lr0.01-w0")[0], T.summaries(theirs, "cosine-lr0.01-w200")[0]
    t.check(warm["worst_early_loss"] < 2.4 and cold["worst_early_loss"] > warm["worst_early_loss"],
            f"on PyTorch too: {cold} {warm}")


def inside(S):
    import numpy as np
    import engine
    import torch
    import lab
    from experiments.loop import mlp

    f = lab.warmup_cosine(10, 110)
    assert abs(f(0) - 0.1) < 1e-15 and f(9) == 1.0 and f(10) == 1.0, (f(0), f(9), f(10))
    assert abs(f(60) - 0.5) < 1e-12 and abs(f(110)) < 1e-15 and abs(f(500)) < 1e-15, (f(60), f(110))
    assert all(f(k) >= f(k + 1) for k in range(10, 120)), "falls after the warmup"
    assert abs(lab.warmup_cosine(0, 100, 0.1)(100) - 0.1) < 1e-15 and lab.warmup_cosine(0, 100)(0) == 1.0
    engine.manual_seed(3)
    ours = mlp(engine, [20, 16, 10]).double()
    theirs = S.copy_weights(ours, mlp(torch, [20, 16, 10]))
    oo, ot = engine.optim.Adam(ours.parameters(), lr=0.01), torch.optim.Adam(theirs.parameters(), lr=0.01)
    so = engine.optim.lr_scheduler.LambdaLR(oo, lab.warmup_cosine(4, 20))
    st = torch.optim.lr_scheduler.LambdaLR(ot, lab.warmup_cosine(4, 20))
    rng = np.random.default_rng(0)
    x, y = rng.standard_normal((100, 20)), rng.integers(0, 10, 100)
    for step in range(20):
        S.same(so.get_last_lr()[0], st.get_last_lr()[0], f"the rate at step {step}", tol=1e-12)
        for model, opt, sch, m in ((ours, oo, so, engine), (theirs, ot, st, torch)):
            loss = m.nn.functional.cross_entropy(model(m.tensor(x[step::20])), m.tensor(y[step::20]))
            opt.zero_grad()
            loss.backward()
            opt.step()
            sch.step()
        for k, (p, q) in enumerate(zip(S.params(ours), S.params(theirs))):
            S.same(p, q, f"Adam under LambdaLR: parameter {k} after step {step}")
