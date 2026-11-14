"""04.03 Batch normalisation

BatchNorm1d gives PyTorch's outputs and gradients in training, the same running statistics after
several batches, the same outputs in eval mode and the same checkpoint names (1e-6, float64), and
refuses a batch of one as PyTorch does; sigmoid is PyTorch's; with batch norm the paper's sigmoid
network gets to 90% in fewer steps, and the 20-layer network trains at a rate that breaks it
without, on either engine.
"""


def test(t):
    T = t.track
    T.need(t, "mnist")
    T.inside(t, __file__)
    ours = T.experiment(t, "batchnorm", "steps=1000", "seeds=2", "deep_lrs=[0.1]")
    plain = re.search(r"no norm +:.*first at 90%: (step (\d+)|not reached)", ours.out)
    norm = re.search(r"batch norm:.*first at 90%: step (\d+)", ours.out)
    t.check(norm and plain and (plain.group(2) is None or int(norm.group(1)) < int(plain.group(2))),
            f"batch norm should reach 90% in fewer steps:\n{ours.out}")
    for s in T.summaries(ours, "deep-lr0.1-batch"):
        t.check(s["train_loss"] < 1.0, f"lr 0.1 with batch norm should train: {s}")
    plain = T.summaries(ours, "deep-lr0.1-none")
    t.check(all(not s["train_loss"] < 1.0 for s in plain), f"lr 0.1 without batch norm should not: {plain}")
    theirs = T.on_torch(t, "batchnorm", "steps=500", "every=250", "seeds=1", "deep_lrs=[0.1]")
    t.check(T.value(theirs.out, r"batch norm: 250: (\S+)") > 0.85, f"on PyTorch:\n{theirs.out}")
    t.check(T.summaries(theirs, "deep-lr0.1-batch")[0]["train_loss"] < 1.0, f"on PyTorch:\n{theirs.out}")


def inside(S):
    import numpy as np
    import engine
    import torch

    S.same_op(lambda m, a: a.sigmoid() * m.sigmoid(a * 3), [(4, 3)], "sigmoid")
    ours = engine.nn.BatchNorm1d(5).double()
    theirs = torch.nn.BatchNorm1d(5).double()
    rng = np.random.default_rng(0)
    for step in range(3):
        x = rng.standard_normal((16, 5)) * 3 + 1
        a, b = S.pair([x])
        out, ref = ours(a[0]), theirs(b[0])
        S.same(out, ref, f"training-mode output, batch {step}")
        g = rng.standard_normal((16, 5))
        out.backward(engine.tensor(g))
        ref.backward(torch.tensor(g))
        S.same(a[0].grad, b[0].grad, f"input gradient, batch {step}")
        S.same(ours.weight.grad, theirs.weight.grad, f"weight gradient, batch {step}")
        S.same(ours.bias.grad, theirs.bias.grad, f"bias gradient, batch {step}")
        ours.zero_grad()
        theirs.zero_grad()
    S.same(ours.running_mean, theirs.running_mean, "running mean after 3 batches")
    S.same(ours.running_var, theirs.running_var, "running variance after 3 batches")
    assert ours.num_batches_tracked.item() == 3
    assert list(ours.state_dict()) == list(theirs.state_dict()), list(ours.state_dict())
    ours.eval()
    theirs.eval()
    x = rng.standard_normal((4, 5))
    S.same(ours(engine.tensor(x)), theirs(torch.tensor(x)), "eval-mode output")
    ours.train()
    try:
        ours(engine.zeros(1, 5, dtype=engine.float64))
        raise AssertionError("a batch of one in training should be refused")
    except ValueError as e:
        assert "Expected more than 1 value per channel when training" in str(e), e


import re  # noqa: E402
