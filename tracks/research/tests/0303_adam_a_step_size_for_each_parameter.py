"""03.03 Adam: a step size for each parameter

Adam's steps are PyTorch's (1e-6, float64), with its defaults, other betas and eps, and its L2
weight_decay; in the valley one rate serves Adam at both steepnesses, where momentum's working
rate diverges at the steeper one and the rate that survives it crawls; Adam's first step moves
every weight by lr, and on the loss times 1000 Adam takes the same steps to within 1e-6, on either
engine digit for digit; on logistic regression on MNIST, each at its best rate, Adam ends about
where SGD with Nesterov momentum does (the Adam paper's figure 1 says the same); and the
comparison runs on PyTorch to the same costs.
"""


def test(t):
    T = t.track
    T.need(t, "mnist")
    T.inside(t, __file__)
    short = ["models=['logistic']", "epochs=2", "seeds=2"]
    ours = T.experiment(t, "adam", *short)
    one_rate(t, ours.out)
    best = {}
    for opt in ("adam", "nesterov"):
        costs = [T.value(l, r"final cost (\S+)") for l in ours.out.splitlines()
                 if l.strip().startswith(opt) and "final cost" in l]
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
    t.check(part1(a.out) == part1(b.out), f"the valley has no randomness: PyTorch should print the same part 1:\n"
                                          f"{a.out}\n{b.out}")


def part1(out):
    """The lines of part 1, the valley: from "1." up to "2." (or the end)."""
    lines = out.split("\n")
    start = next(i for i, l in enumerate(lines) if l.startswith("1. "))
    end = next((i for i, l in enumerate(lines) if l.startswith("2. ")), len(lines))
    return lines[start:end]


def one_rate(t, out):
    """Part 1: momentum needs a rate for each steepness and crawls at the one that survives the
    steep valley; Adam takes about the same steps at one rate; its first step is lr for every
    weight; times 1000 the loss, Adam's path is the same to within 1e-6."""
    T = t.track
    rows = {}
    for line in part1(out):
        m = re.match(r"^   (momentum \S+, lr \S+|adam, lr \S+) +(\d+|diverged) +(\d+|diverged)$", line)
        if m:
            rows[m.group(1)] = [None if c == "diverged" else int(c) for c in m.group(2, 3)]
    t.check(len(rows) == 6, f"five momentum rates and Adam's at s = 50 and s = 5000:\n{out}")
    fast, crawl = rows.get("momentum 0.8, lr 0.03"), rows.get("momentum 0.8, lr 0.0003")
    adam = rows.get("adam, lr 0.1")
    t.check(fast[0] is not None and fast[1] is None, f"momentum's rate for s = 50 should diverge at s = 5000: {rows}")
    t.check(adam[0] is not None and adam[1] is not None and abs(adam[1] - adam[0]) < 0.25 * adam[0],
            f"Adam at one rate should take about the same steps at both: {rows}")
    survivors = [r[1] for r in rows.values() if r is not adam and r[1] is not None]
    t.check(survivors and min(survivors) > 10 * adam[1],
            f"every momentum rate that survives s = 5000 should take over 10 times Adam's steps: {rows}")
    t.check(crawl[1] is not None, f"momentum at 0.0003 should survive s = 5000: {rows}")
    w = re.findall(r"^   adam, lr 0\.1 +w0 (\S+) +w1 (\S+)$", out, re.M)
    t.check(w and all(abs(float(v) - 0.1) < 1e-6 for v in w[0]), f"Adam's first step should be lr for each weight:\n{out}")
    t.check(re.search(r"^   momentum 0\.8, lr 0\.03 +diverged$", out, re.M) is not None,
            f"momentum at 0.03 should diverge on the loss times 1000:\n{out}")
    t.check(T.value(out, r"^   momentum 0\.8, lr 3e-05 +(\d+) steps$") == fast[0],
            f"momentum at the rate divided by 1000 should take the same steps on the loss times 1000:\n{out}")
    t.check(T.value(out, r"^   adam, lr 0\.1 +(\d+) steps, every weight") == adam[0] and
            T.value(out, r"every weight within (\S+) of its place") < 1e-6,
            f"Adam should take the same steps on the loss times 1000, to within 1e-6:\n{out}")


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


import re  # noqa: E402
