"""11.01 Reading the benchmark: time to a target loss

lab/bench.py: timings calls the work warm-up times untimed and times each repeat of `number` calls with the
clock given (checked with a clock that moves by known amounts); spread_ms puts the smallest first, then the
median, the largest, the count and the load; time_to finds where held-out bits first reach a target, on the
straight line between the logged rows on either side (checked against numbers worked out by hand), and
says None when no row reaches it; load_average is the system's. experiments/language.py's train gives the
same log and the same weights, bit for bit, with times and without, adds one time a row, rising, and with
until stops at the first row that reaches it; race's summaries have the steps to the target and no times,
the same seed gives the same summary, and its steps agree with time_to on its own log. The short run: the
step timed in rounds with the load beside each, the baseline reaching the target on every seed, half the
batch taking more steps to it (steps are not timings: they are the same on any machine); and the same seed
gives the same bytes again.
"""

import json
import os


def read(path):
    with open(path, "rb") as f:
        return f.read()


def test(t):
    T = t.track
    T.inside(t, __file__)
    r = T.experiment(t, "benchmark")
    t.check("The first step of the process" in r.out and r.out.count("round ") == 3 and "load " in r.out,
            f"the step should be timed in rounds, the load beside each:\n{r.out[:2500]}")
    base, half = (T.summaries(r, k) for k in ("baseline", "half-the-batch"))
    t.check(all(s["steps_to_target"] is not None for s in base), f"the baseline should reach the target: {base}")
    t.check(all(s["steps_to_target"] is not None for s in half) and
            sum(s["steps_to_target"] for s in half) > sum(s["steps_to_target"] for s in base),
            f"half the batch should take more steps to the target: {base} {half}")
    t.check(all("seconds" not in s for s in base), f"no times in summary.json: {base}")
    with open(os.path.join(r.runs, "times.json")) as f:
        times = json.load(f)
    t.check(set(times) == {"baseline", "half the batch"} and all(len(v["seconds"]) == 2 for v in times.values()) and
            os.path.isfile(os.path.join(r.runs, "curves.svg")), f"times.json and the curves: {times}")
    tiny = ["seeds=2", "steps=12", "layers=1", "width=16", "context=16", "every=3", "held=4", "target=5.8", "rounds=1",
            "repeats=2", "number=1"]
    a, b = T.experiment(t, "benchmark", *tiny), T.experiment(t, "benchmark", *tiny)
    for run in ("baseline/seed1", "half-the-batch/seed0"):
        for name in ("log.jsonl", "summary.json"):
            t.check(read(os.path.join(a.runs, run, name)) == read(os.path.join(b.runs, run, name)),
                    f"the same seed twice gave two different {run}/{name}")


def inside(S):
    import os
    import lab
    import numpy as np
    import torch
    from data import shakespeare
    from experiments.language import race, train
    from experiments.sequences import windows
    from lab import bench
    from models.gpt import GPT

    now = [0.0]
    calls = []

    def clock():
        return now[0]

    def work():
        calls.append(1)
        now[0] += 0.5 * len(calls)                 # each call takes longer: 0.5, 1.0, 1.5, ...
    got = bench.timings(work, clock, repeats=3, warmup=2, number=2)
    assert len(calls) == 2 + 3 * 2, calls
    assert got == [(1.5 + 2.0) / 2, (2.5 + 3.0) / 2, (3.5 + 4.0) / 2], got
    line = bench.spread_ms([0.003, 0.001, 0.002, 0.010], 7.25)
    assert line == "1 ms (median 2.5, largest 10, 4 repeats, load 7.2)", line
    assert bench.spread_ms([0.0012345]) == "1.23 ms (median 1.23, largest 1.23, 1 repeat)"
    assert abs(bench.load_average() - os.getloadavg()[0]) < 5

    rows = [{"step": 0, "held_bits": 5.0}, {"step": 9, "held_bits": 4.0}, {"step": 19, "held_bits": 3.0},
            {"step": 29, "held_bits": 2.5}]
    times = [0.1, 1.0, 2.0, 3.0]
    steps, seconds = bench.time_to(rows, times, 3.5)
    assert abs(steps - 15.0) < 1e-12 and abs(seconds - 1.5) < 1e-12, (steps, seconds)  # halfway from step 9 to 19
    assert bench.time_to(rows, times, 3.0) == (20, 2.0)
    assert bench.time_to(rows, times, 6.0) == (1, 0.1)
    assert bench.time_to(rows, times, 2.0) == (None, None)

    cfg = lab.Config(steps=12, batch=8, context=16, lr=0.003, warmup=3, weight_decay=0.1, clip=1.0, every=3, seeds=2,
                     target=5.0, out=os.environ.get("TMPDIR", "/tmp") + "/learn-1101", name="t1101")
    ids = torch.from_numpy(shakespeare.split("train"))
    held = windows(torch.from_numpy(shakespeare.split("val")), torch.arange(0, 64, 16), 16)
    models, logs = [], []
    for kind in ("plain", "times"):
        torch.manual_seed(0)
        m = GPT(65, 16, layers=1, heads=2, width=16, positions="rotary", norm="rms")
        run = lab.Run(cfg, 0, label=kind)
        spent = [] if kind == "times" else None
        train(m, cfg, run, torch.device("cpu"), ids, held, spent)
        models.append(m)
        logs.append(run.rows)
        if spent is not None:
            assert len(spent) == len(run.rows) and all(b >= a for a, b in zip(spent, spent[1:])), spent
    assert logs[0] == logs[1], "times change nothing in the log"
    assert all(torch.equal(a, b) for a, b in zip(models[0].parameters(), models[1].parameters())), "nor the weights"
    torch.manual_seed(0)
    m = GPT(65, 16, layers=1, heads=2, width=16, positions="rotary", norm="rms")
    run = lab.Run(cfg, 0, label="until")
    stop = logs[0][2]["held_bits"] + 1e-9
    train(m, cfg, run, torch.device("cpu"), ids, held, [], stop)
    assert run.rows[-1]["step"] == logs[0][2]["step"] and len(run.rows) == 3, (run.rows, logs[0])

    common = dict(vocab=65, context=16, layers=1, heads=2, width=16)
    cfg["target"] = logs[0][3]["held_bits"] + 0.05
    out = race({}, common, cfg, torch.device("cpu"), ids, held, label="race")
    assert len(out["steps"]) == len(out["seconds"]) == len(out["ms"]) == 2 and out["tokens"] == 8 * 16
    for seed in range(2):
        d = os.path.join(cfg.out, cfg.name, "race", f"seed{seed}")
        with open(os.path.join(d, "summary.json")) as f:
            s = json.load(f)
        assert set(s) == {"steps_to_target", "held_bits", "steps"}, s
        log = lab.read_log(d)
        if s["steps_to_target"] is not None:
            assert log[-1]["held_bits"] <= cfg.target and s["steps"] == log[-1]["step"] + 1, (s, log)
            assert abs(bench.time_to(log, list(range(len(log))), cfg.target)[0] - s["steps_to_target"]) < 1e-9
    again = race({}, common, cfg, torch.device("cpu"), ids, held, label="race")
    assert again["steps"] == out["steps"] and again["bits"] == out["bits"]
    import experiments.benchmark as B
    table = B.rows(cfg)
    assert list(table)[:2] == ["baseline", "half the batch"] and table["half the batch"][1] == {"batch": 4}
    lines = B.board({"a": {"seconds": [2.0, 4.0], "steps": [10, 20], "ms": [100.0, 200.0], "tokens": 100},
                     "b": {"seconds": [1.0, 1.0], "steps": [5, 5], "ms": [50.0, 50.0], "tokens": 100},
                     "c": {"seconds": [None, None], "steps": [None, None], "ms": [10.0, 10.0], "tokens": 100}}).splitlines()
    assert "x0.33" in lines[2] and lines[2].split()[-1] == "2,000" and "not reached in 2 seeds" in lines[3], lines
    assert np.isfinite(float(lines[1].split()[-2]))
