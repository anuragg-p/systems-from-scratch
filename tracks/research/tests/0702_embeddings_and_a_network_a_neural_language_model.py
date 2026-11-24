"""07.02 Embeddings and a network: a neural language model

context_codes and NGram's counts equal a direct count of every context and what follows it, at
every length; NGram with a context of one character is 07.01's pair table; its chances add up to 1
after any context, and are 1 / V after one never seen; mixture_weights gives a text a chance at
least as high as the best mixture of a fine grid; bits, contexts, context_bits and sample do what
they say against direct computations; nearest is the cosine similarity. The short run: counting
with longer contexts makes the training text's bits fall while the test text's turn up; the network
beats add-k at five characters by far and matches the pair model at one; the network and deleted
interpolation mixed beat interpolation; the same seed gives the same bytes again. The recorded long
run has every file, and the paper's result: at five and eight characters every seed of the network
below deleted interpolation. With LEARN_RERUN_LONG=1 the long run is run again (about 30 minutes).
"""

import json
import os

LONG = "experiments/recorded/nplm"


def read(path):
    with open(path, "rb") as f:
        return f.read()


def test(t):
    T = t.track
    T.inside(t, __file__)
    check_recorded(t, os.path.join(t.root, LONG))
    r = T.experiment(t, "nplm", "contexts=[1,5]", "seeds=2", "steps=1500")
    (counts,) = T.summaries(r, "counts")
    add_k, interpolated = counts["add_k"], counts["interpolated"]
    with open(os.path.join(r.runs, "counts", "seed0", "log.jsonl")) as f:
        rows = [json.loads(line) for line in f]
    seen = [row["train_bits"] for row in rows]
    t.check(all(a > b for a, b in zip(seen, seen[1:])), f"the training text's bits should fall with the context: {seen}")
    t.check(add_k["7"] > add_k["4"] + 1 and add_k["4"] < add_k["2"],
            f"held-out bits should fall, then turn up, as the context grows: {add_k}")
    one, five = (T.summaries(r, f"context{n}") for n in (1, 5))
    for s in five:
        t.check(s["test_bits"] < add_k["5"] - 0.3, f"the network should beat add-k by far at 5 characters: {s} {add_k}")
        t.check(s["mixed_bits"] < interpolated["5"] - 0.03,
                f"the network and interpolation mixed should beat interpolation: {s} {interpolated}")
    for s in one:
        t.check(abs(s["test_bits"] - add_k["1"]) < 0.05, f"at one character the network is a pair model: {s} {add_k}")
    tiny = ["contexts=[2]", "seeds=2", "steps=30", "orders=[0,1,2]", "length=20"]
    a, b = T.experiment(t, "nplm", *tiny), T.experiment(t, "nplm", *tiny)
    for run in ("counts/seed0", "context2/seed1"):
        for name in ("log.jsonl", "summary.json"):
            t.check(read(os.path.join(a.runs, run, name)) == read(os.path.join(b.runs, run, name)),
                    f"the same seed twice gave two different {run}/{name}")
    if os.environ.get("LEARN_RERUN_LONG"):
        with open(os.path.join(t.root, LONG, "context5", "seed0", "config.json")) as f:
            cfg = json.load(f)
        settings = [f"{k}={cfg[k]!r}".replace(" ", "") for k in ("contexts", "embed", "hidden", "dropout", "steps",
                                                                   "batch", "lr", "seeds")]
        again = T.experiment(t, "nplm", *settings, timeout=3 * 3600)
        check_recorded(t, again.runs, rerun=True)


def check_recorded(t, d, rerun=False):
    """The long run: the count models' summary, every context and seed with its config, a log and a
    summary, the curves; and the paper's result in the summaries."""
    where = "the rerun" if rerun else f"the recorded run ({LONG})"
    t.check(os.path.isdir(d), f"no {where}")
    with open(os.path.join(d, "counts", "seed0", "summary.json")) as f:
        counts = json.load(f)
    with open(os.path.join(d, "context5", "seed0", "config.json")) as f:
        cfg = json.load(f)
    t.check(cfg["contexts"] == [1, 3, 5, 8] and cfg["seeds"] >= 3 and cfg["steps"] >= 20000,
            f"{where}: the long run is contexts 1, 3, 5 and 8, 3 seeds or more, 20000 steps: {cfg}")
    t.check(os.path.isfile(os.path.join(d, "training.svg")), f"{where}: no training.svg")
    if not rerun:
        t.check(os.path.isfile(os.path.join(d, "output.txt")), f"{where}: no output.txt, what the run printed")
    got = {}
    for n in cfg["contexts"]:
        for seed in range(cfg["seeds"]):
            run = os.path.join(d, f"context{n}", f"seed{seed}")
            with open(os.path.join(run, "config.json")) as f:
                c = json.load(f)
            t.check({k: v for k, v in c.items() if k not in ("label", "seed", "out")} ==
                    {k: v for k, v in cfg.items() if k not in ("label", "seed", "out")} and c["seed"] == seed,
                    f"{where}: {run} was run with other settings")
            with open(os.path.join(run, "log.jsonl")) as f:
                rows = [json.loads(line) for line in f if line.strip()]
            t.check(rows[0]["step"] == 0 and rows[-1]["step"] == cfg["steps"] - 1, f"{where}: {run}/log.jsonl")
            with open(os.path.join(run, "summary.json")) as f:
                got.setdefault(n, []).append(json.load(f))
    for n in (5, 8):
        bits = [s["test_bits"] for s in got[n]]
        t.check(max(bits) < counts["interpolated"][str(n)],
                f"{where}: at {n} characters every seed of the network should be below deleted interpolation "
                f"({counts['interpolated'][str(n)]:.3f}): {bits}")
    t.check(all(abs(s["test_bits"] - counts["add_k"]["1"]) < 0.05 for s in got[1]),
            f"{where}: at one character the network is a pair model: {[s['test_bits'] for s in got[1]]}")


def inside(S):
    import collections
    import math
    import numpy as np
    import torch
    import torch.nn.functional as F
    from data import shakespeare
    from experiments import bigram, nplm
    from experiments.sequences import bits, context_bits, contexts, sample
    from models.ngram import NGram, context_codes, lookup, mixture_weights

    rng = np.random.default_rng(0)
    V = 4
    ids = rng.integers(0, V, 400)
    for n in (0, 1, 2, 3):
        codes, after = context_codes(ids, n, V)
        for t in (n, n + 7, 399):
            want = sum(int(c) * V ** (n - 1 - j) for j, c in enumerate(ids[t - n:t]))
            assert codes[t - n] == want and after[t - n] == ids[t], (n, t)
        model = NGram(ids, n, V)
        seen = collections.Counter(tuple(ids[t - n:t + 1].tolist()) for t in range(n, len(ids)))
        before = collections.Counter(tuple(ids[t - n:t].tolist()) for t in range(n, len(ids)))
        held = rng.integers(0, V, 60)
        pair, context = model.counts(held)
        for t in range(n, len(held)):
            assert pair[t - n] == seen[tuple(held[t - n:t + 1].tolist())], (n, t)
            assert context[t - n] == before[tuple(held[t - n:t].tolist())], (n, t)
        p = model.probabilities(held, 0.5)
        want = [(seen[tuple(held[t - n:t + 1].tolist())] + 0.5) / (before[tuple(held[t - n:t].tolist())] + 0.5 * V)
                for t in range(n, len(held))]
        assert np.allclose(p, want)
    assert (lookup(np.array([2, 5, 9]), np.array([7, 8, 9]), np.array([1, 2, 6, 9, 10])) == [0, 7, 0, 9, 0]).all()
    try:
        context_codes(ids, 10, 65)
        raise AssertionError("contexts of 10 of 65 characters do not fit in an int64: that should be refused")
    except ValueError:
        pass

    train = shakespeare.split("train")
    pairs = NGram(train, 1, 65)
    table = bigram.pair_counts(train, 65)
    assert sum(pairs.pair_counts) == table.sum() and len(pairs.pairs) == (table > 0).sum()
    for code, n in zip(pairs.pairs[:200], pairs.pair_counts[:200]):
        assert table[code // 65, code % 65] == n
    model = NGram(train[:5000], 3, 65)
    for k in (0.0, 0.3):
        for context in (shakespeare.encode(" th").tolist(), [0, 0, 0]):
            every =np.array([model.probabilities(np.array(context + [c]), k)[0] for c in range(65)])
            assert abs(every.sum() - 1) < 1e-9, (context, k, every.sum())
    unseen = np.array([0, 0, 0, 5])
    assert model.counts(unseen)[1][0] == 0 and model.probabilities(unseen)[0] == 1 / 65

    p = np.stack([rng.uniform(0.01, 1, 500), rng.uniform(0.01, 1, 500)])
    w = mixture_weights(p)
    assert abs(w.sum() - 1) < 1e-12 and (w >= 0).all()
    best = max(np.log(a * p[0] + (1 - a) * p[1]).sum() for a in np.linspace(0, 1, 1001))
    assert np.log(w @ p).sum() >= best - 1e-6, "EM's weights should be as good as the best of a fine grid"

    torch.manual_seed(0)
    scores, targets = torch.randn(3, 5, 7, dtype=torch.float64), torch.randint(0, 7, (3, 5))
    direct = -sum(math.log2(F.softmax(scores[i, j], 0)[targets[i, j]].item()) for i in range(3) for j in range(5)) / 15
    assert abs(bits(scores, targets).item() - direct) < 1e-12
    text = torch.arange(100) * 3
    x, y = contexts(text, torch.tensor([4, 10, 99]), 4)
    assert x.tolist() == [[0, 3, 6, 9], [18, 21, 24, 27], [285, 288, 291, 294]] and y.tolist() == [12, 30, 297]
    net = nplm.NPLM(65, 3, 5, 16).double()
    held = torch.from_numpy(shakespeare.split("val")[:300])
    with torch.no_grad():
        direct = sum(-math.log2(F.softmax(net(held[t - 3:t][None])[0], 0)[held[t]].item()) for t in range(3, 300)) / 297
    assert abs(context_bits(net, held, 3, batch=50) - direct) < 1e-9 and net.training
    assert net(held[None, :3]).shape == (1, 65)

    def scores_of(ids):
        return torch.log(torch.tensor([0.1, 0.2, 0.7], dtype=torch.float64)) + 0 * len(ids)
    one = sample(scores_of, [0], 200, torch.Generator().manual_seed(5))
    assert one == sample(scores_of, [0], 200, torch.Generator().manual_seed(5)) and 100 < one.count(2) < 180
    assert sample(scores_of, [0], 20, torch.Generator().manual_seed(5), temperature=0.01) == [2] * 20

    e = net.embed.weight.detach()
    got = nplm.nearest(net, 7, list(range(65)), k=3)
    cosine = [(i, (e[7] @ e[i] / (e[7].norm() * e[i].norm())).item()) for i in range(65) if i != 7]
    cosine.sort(key=lambda c: -c[1])
    assert [i for i, _ in got] == [i for i, _ in cosine[:3]] and abs(got[0][1] - cosine[0][1]) < 1e-9
