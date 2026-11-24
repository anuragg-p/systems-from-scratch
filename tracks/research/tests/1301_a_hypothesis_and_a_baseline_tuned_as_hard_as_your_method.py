"""13.01 A hypothesis, and a baseline tuned as hard as your method

best_of gives the expected best of n trials drawn from N, and the expected reported number of the one chosen,
the same as every way of drawing n counted out by hand; draw_rates draws the same search for each optimiser,
seeded, every rate inside its range; run_one trains one optimiser at one rate and seed the same way twice and
scores validation and test. Then (with MNIST) the experiment, its search as the default's and 3 fresh seeds: the
hypothesis and its rule printed before anything else; the hurried comparison (Adam tuned against SGD at the docs'
rate) a far wider gap than the fair one, the docs' rate worse than SGD's own tuned one; the expected best of n
falling as n grows, for both; and the same seed gives the same bytes again.
"""

import os
import re


def read(path):
    with open(path, "rb") as f:
        return f.read()


def test(t):
    T = t.track
    T.inside(t, __file__)
    T.need(t, "mnist")
    r = T.experiment(t, "baseline", "seeds=3")
    t.check(r.out.startswith("1. The hypothesis: Adam reaches a lower test error"),
            f"the hypothesis should be printed first, before any run:\n{r.out[:500]}")
    gaps = [float(x) for x in re.findall(r"SGD's test error minus Adam's: ([+-][\d.]+) points", r.out)]
    t.check(len(gaps) == 2 and gaps[0] > 3 and gaps[0] > 2 * abs(gaps[1]),
            f"the hurried gap should be far wider than the fair one: {gaps}\n{r.out[-2500:]}")
    hurried_t = T.value(r.out, r"3\. The hurried comparison.*\n.*t = ([+-][\d.]+)")
    t.check(hurried_t >= 3, f"the hurried comparison should come out beyond the noise: t = {hurried_t}")
    docs, tuned = T.summaries(r, "nesterov-docs"), T.summaries(r, "nesterov-tuned")
    t.check(len(docs) == len(tuned) == 3 and all(s["lr"] == 0.01 for s in docs),
            f"three fresh seeds of each arm: {os.listdir(r.runs)}")
    t.check(sum(s["test_error"] for s in docs) > sum(s["test_error"] for s in tuned),
            "SGD at the docs' rate should be worse than SGD at its own tuned rate")
    table = re.findall(r"^\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)$", r.out, re.M)
    t.check(len(table) == 8, f"the best-of-n table should have a row for n = 1 to 8:\n{r.out[-1500:]}")
    for col in (1, 3):
        values = [float(row[col]) for row in table]
        t.check(all(a >= b - 1e-9 for a, b in zip(values, values[1:])),
                f"the expected best validation error should not rise with n: {values}")
    tiny = ["n_train=500", "n_val=500", "trials=2", "seeds=1", "epochs=1", "hidden=16"]
    a, b = T.experiment(t, "baseline", *tiny), T.experiment(t, "baseline", *tiny)
    for label in os.listdir(a.runs):
        if os.path.isdir(os.path.join(a.runs, label)):
            for name in ("log.jsonl", "summary.json"):
                t.check(read(os.path.join(a.runs, label, "seed" + ("0" if label.startswith("search") else "1"), name)) ==
                        read(os.path.join(b.runs, label, "seed" + ("0" if label.startswith("search") else "1"), name)),
                        f"the same seed twice gave two different {label}/{name}")


def inside(S):
    import itertools
    import math
    import tempfile
    import numpy as np
    import torch
    import lab
    from experiments import baseline

    rng = np.random.default_rng(0)
    for N in (1, 2, 5, 7):
        scores = rng.random(N).tolist()
        reported = rng.random(N).tolist()
        for n in range(1, N + 1):
            draws = list(itertools.combinations(range(N), n))
            best = sum(min(scores[i] for i in d) for d in draws) / len(draws)
            chosen = sum(reported[min(d, key=lambda i: scores[i])] for d in draws) / len(draws)
            assert abs(lab.best_of(scores, n) - best) < 1e-12, (N, n)
            assert abs(lab.best_of(scores, n, reported) - chosen) < 1e-12, (N, n)
        assert abs(lab.best_of(scores, 1) - sum(scores) / N) < 1e-12 and lab.best_of(scores, N) == min(scores)

    ranges = {"adam": [1e-4, 1e-2], "nesterov": [3e-3, 3e-1]}
    a = baseline.draw_rates(ranges, 50, np.random.default_rng(3))
    b = baseline.draw_rates(ranges, 50, np.random.default_rng(3))
    assert a == b and set(a) == set(ranges) and all(len(v) == 50 for v in a.values())
    for name, (low, high) in ranges.items():
        assert all(low <= r < high for r in a[name]), name
    place = {name: [math.log(r / low) / math.log(high / low) for r in a[name]] for name, (low, high) in ranges.items()}
    assert all(abs(x - y) < 1e-12 for x, y in zip(place["adam"], place["nesterov"])), "the same draws in each range"
    assert baseline.draw_rates(ranges, 50, np.random.default_rng(4)) != a

    with tempfile.TemporaryDirectory() as d:
        cfg = lab.Config(baseline.CONFIG, hidden=8, epochs=2, batch=16, out=d, name="baseline")
        g = torch.Generator().manual_seed(0)
        x, y = torch.rand(120, 784, generator=g), torch.randint(0, 10, (120,), generator=g)
        data = ((x[:80], y[:80]), (x[80:100], y[80:100]), (x[100:], y[100:]))
        one = baseline.run_one(cfg, "adam", 0.01, 2, "a", data, torch.device("cpu"))
        again = baseline.run_one(cfg, "adam", 0.01, 2, "b", data, torch.device("cpu"))
        other = baseline.run_one(cfg, "nesterov", 0.01, 2, "c", data, torch.device("cpu"))
        assert one == again and one != other, (one, other)
        assert one["optimiser"] == "adam" and one["lr"] == 0.01 and 0 <= one["val_error"] <= 1 and 0 <= one["test_error"] <= 1
        assert abs(one["val_error"] * 20 - round(one["val_error"] * 20)) < 1e-9, "a share of the 20 validation images"
        assert len(lab.read_log(os.path.join(d, "baseline", "a", "seed2"))) == 2, "a log row for each pass"
    assert baseline.verdict([1.0, 1.1, 0.9], [2.0, 2.1, 1.9])[1].startswith("held")
    assert baseline.verdict([2.0, 2.1, 1.9], [1.0, 1.1, 0.9])[1].startswith("the reverse")
    assert baseline.verdict([1.0, 1.2, 0.8], [1.1, 1.3, 0.9])[1] == "a tie"
