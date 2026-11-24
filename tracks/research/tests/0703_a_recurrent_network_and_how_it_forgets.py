"""07.03 A recurrent network, and how it forgets

RNNCell and RNN, with torch.nn.RNN's weights copied in, give its states and its gradients (every
weight's, the inputs' and the first state's) to 1e-10 in float64; windows and window_bits do what
they say against direct computations; the recall task is a symbol and blanks; gradient_back is the
gradient that reaches each input. The short run: the text network scores below 3 bits per
character; the recall network gives back the symbol after 2 blanks and is near chance after 40; the
gradient reaching 60 steps back is all but gone from the network as it starts and grows when its
recurrent weights are rescaled to a radius of 3; what the text network reads more than 16
characters back makes no difference to its guess; and the same seed gives the same bytes again.
"""

import os


def read(path):
    with open(path, "rb") as f:
        return f.read()


def test(t):
    T = t.track
    T.inside(t, __file__)
    r = T.experiment(t, "rnn", "seeds=2", "steps=300", "delays=[2,40]", "reads=[4,16,64]")
    for s in T.summaries(r, "text"):
        t.check(s["test_bits"] < 3.0, f"the text network should be below 3 bits per character after 300 steps: {s}")
    for s in T.summaries(r, "recall2"):
        t.check(s["accuracy"] > 0.98, f"after 2 blanks the symbol should come back: {s}")
    late = [s["accuracy"] for s in T.summaries(r, "recall40")]
    t.check(sum(late) / len(late) < 0.4, f"after 40 blanks the recall network should be near chance (0.125): {late}")
    start = row(t, r.out, "the recall network, as it starts")
    big = row(t, r.out, "rescaled to radius 3")
    t.check(start[-1] < start[1] * 1e-10,
            f"from the network as it starts, the gradient 60 steps back should vanish: {start}")
    t.check(big[-1] > big[1] * 10, f"rescaled to radius 3, the gradient should grow going back: {big}")
    w4, w16, w64 = (T.value(r.out, rf"w = +{w}: (\S+)") for w in (4, 16, 64))
    t.check(w4 > w16 + 0.2 and abs(w64 - w16) < 0.01,
            f"the text network should use the last 16 characters and nothing much before them: {w4} {w16} {w64}")
    tiny = ["seeds=2", "steps=20", "recall_steps=20", "delays=[3]", "reads=[0,8]", "radii=[1.0]", "back=[0,8]",
            "orders=2", "drawn=20"]
    a, b = T.experiment(t, "rnn", *tiny), T.experiment(t, "rnn", *tiny)
    for run in ("text/seed1", "recall3/seed1"):
        for name in ("log.jsonl", "summary.json"):
            t.check(read(os.path.join(a.runs, run, name)) == read(os.path.join(b.runs, run, name)),
                    f"the same seed twice gave two different {run}/{name}")


def row(t, out, name):
    """The six gradients printed on the line that starts with name (after its radius)."""
    for line in out.splitlines():
        if line.strip().startswith(name):
            return [float(v) for v in line.split()[-6:]]
    t.check(False, f"no line {name!r} in the output:\n{out[-2500:]}")


def inside(S):
    import numpy as np
    import torch
    import torch.nn.functional as F
    from experiments import rnn as experiment
    from experiments.sequences import bits, window_bits, windows
    from models.rnn import RNN, RNNCell

    torch.manual_seed(0)
    ours = RNN(3, 5).double()
    theirs = torch.nn.RNN(3, 5, batch_first=True).double()
    with torch.no_grad():
        theirs.weight_ih_l0.copy_(ours.cell.ih.weight)
        theirs.bias_ih_l0.copy_(ours.cell.ih.bias)
        theirs.weight_hh_l0.copy_(ours.cell.hh.weight)
        theirs.bias_hh_l0.copy_(ours.cell.hh.bias)
    x = torch.randn(4, 7, 3, dtype=torch.float64)
    h0 = torch.randn(4, 5, dtype=torch.float64)
    for start in (None, h0):
        xa, xb = x.clone().requires_grad_(), x.clone().requires_grad_()
        ha = None if start is None else start.clone().requires_grad_()
        hb = None if start is None else start.clone().requires_grad_()
        states, last = ours(xa, ha)
        want, want_last = theirs(xb, None if hb is None else hb[None])
        S.same(states, want, "every state")
        S.same(last, want_last[0], "the last state")
        g = torch.randn(4, 7, 5, dtype=torch.float64)
        ((states * g).sum() + last.sum()).backward()
        ((want * g).sum() + want_last.sum()).backward()
        S.same(xa.grad, xb.grad, "the inputs' gradient", 1e-10)
        if start is not None:
            S.same(ha.grad, hb.grad, "the first state's gradient", 1e-10)
        for mine, name in ((ours.cell.ih.weight, "weight_ih_l0"), (ours.cell.ih.bias, "bias_ih_l0"),
                           (ours.cell.hh.weight, "weight_hh_l0"), (ours.cell.hh.bias, "bias_hh_l0")):
            S.same(mine.grad, getattr(theirs, name).grad, f"{name}'s gradient", 1e-10)
        ours.zero_grad()
        theirs.zero_grad()
    cell = RNNCell(3, 5).double()
    assert torch.allclose(cell(x[:, 0], h0), torch.tanh(x[:, 0] @ cell.ih.weight.T + cell.ih.bias +
                                                        h0 @ cell.hh.weight.T + cell.hh.bias))

    text = torch.arange(50) * 2
    x, y = windows(text, torch.tensor([0, 10]), 4)
    assert x.tolist() == [[0, 2, 4, 6], [20, 22, 24, 26]] and y.tolist() == [[2, 4, 6, 8], [22, 24, 26, 28]]

    table = torch.randn(9, 9, dtype=torch.float64)
    ids = torch.from_numpy(np.random.default_rng(0).integers(0, 9, 203))
    direct = bits(table[ids[6:-1]], ids[7:]).item()          # scores at t from x[t] alone: positions 7 on
    for span, warm in ((10, 7), (64, 7), (500, 7)):
        got = window_bits(lambda x: table[x], ids, span, warm, batch=3)
        assert abs(got - direct) < 1e-12, (span, warm, got, direct)

    def lookback(x):                                         # scores at t from x[t - 1] (from x[t] at t = 0)
        return table[torch.cat([x[:, :1], x[:, :-1]], dim=1)]
    direct = bits(table[ids[4:-2]], ids[6:]).item()           # every position from 6 on, from the one two back
    assert abs(window_bits(lookback, ids, 17, 6) - direct) < 1e-12

    rng = np.random.default_rng(1)
    x, y = experiment.recall_task(5, 4, 8, rng, torch.device("cpu"))
    assert x.shape == (5, 5) and (x[:, 1:] == 8).all() and (x[:, 0] == y).all() and (y < 8).all()
    torch.manual_seed(0)
    net = experiment.Recall(8, 4, 6).double()
    e = net.embed(x).detach().requires_grad_()
    F.cross_entropy(net.out(net.rnn(e)[1]), y).backward()
    got = experiment.gradient_back(net, x, y)
    assert torch.allclose(got, e.grad.norm(dim=2).mean(dim=0).flip(0)) and got.shape == (5,)
    assert net.embed.weight.grad is None, "gradient_back should leave the weights' gradients alone"
    lm = experiment.CharRNN(65, 4, 6)
    scores, h = lm(torch.zeros(2, 3, dtype=torch.long))
    assert scores.shape == (2, 3, 65) and h.shape == (2, 6)
