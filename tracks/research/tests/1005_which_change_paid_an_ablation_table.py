"""10.05 Which change paid: an ablation table

table gives each row its weights, its bits over seeds, the difference from the first row with Welch's t
and whether that is beyond the noise (|t| of 3 or more), against the same numbers computed directly.
The recorded long run (experiments/recorded/ablation) has every row and seed with the same settings, a
log with the validation curve, a summary, the curves, the times and what it printed, and no weights; and
its result, as measured: rotary positions, SwiGLU and all four changes together below the base by
more than 0.03 bits and beyond the noise, all four the lowest row, RMSNorm and grouped-query attention
within 0.02 bits of the base and inside the noise. The short run: six rows, the
recorded table read back with the papers' claims, rotary below the base; and the same seed gives the same
bytes again. With LEARN_RERUN_LONG=1 the long run is run again (about an hour).
"""

import json
import os

LONG = "experiments/recorded/ablation"
ROWS = ["base", "RMSNorm", "rotary", "SwiGLU", "grouped-query", "all-four"]


def read(path):
    with open(path, "rb") as f:
        return f.read()


def mean(xs):
    return sum(xs) / len(xs)


def test(t):
    T = t.track
    T.inside(t, __file__)
    check_recorded(t, os.path.join(t.root, LONG))
    r = T.experiment(t, "ablation")
    bits = {row: [s["test_bits"] for s in T.summaries(r, row)] for row in ROWS}
    t.check(all(len(b) == 2 for b in bits.values()), f"every row, 2 seeds: {bits}")
    t.check(mean(bits["rotary"]) < mean(bits["base"]) - 0.05, f"rotary should be below the base early on: {bits}")
    t.check("2. The recorded long run" in r.out and "Shazeer (2020)" in r.out and
            os.path.isfile(os.path.join(r.runs, "curves.svg")) and os.path.isfile(os.path.join(r.runs, "times.json")),
            f"the recorded table, the claims, the curves and the times:\n{r.out[-3000:]}")
    tiny = ["seeds=2", "steps=6", "layers=1", "width=16", "context=16", "every=2", "held=4"]
    a, b = T.experiment(t, "ablation", *tiny), T.experiment(t, "ablation", *tiny)
    for run in ("base/seed1", "all-four/seed1"):
        for name in ("log.jsonl", "summary.json"):
            t.check(read(os.path.join(a.runs, run, name)) == read(os.path.join(b.runs, run, name)),
                    f"the same seed twice gave two different {run}/{name}")
    if os.environ.get("LEARN_RERUN_LONG"):
        with open(os.path.join(t.root, LONG, "base", "seed0", "config.json")) as f:
            cfg = json.load(f)
        settings = [f"{k}={cfg[k]!r}".replace(" ", "") for k in ("layers", "heads", "width", "context", "batch", "steps",
                                                                   "lr", "warmup", "weight_decay", "clip", "every",
                                                                   "held", "seeds", "kv_heads")]
        again = T.experiment(t, "ablation", *settings, timeout=3 * 3600)
        check_recorded(t, again.runs, rerun=True)


def check_recorded(t, d, rerun=False):
    """The long run: every row and seed with its config, a log with the validation curve and a summary; the curves,
    the times, what it printed; no weights; and the result in the summaries."""
    where = "the rerun" if rerun else f"the recorded run ({LONG})"
    t.check(os.path.isdir(d), f"no {where}")
    with open(os.path.join(d, "base", "seed0", "config.json")) as f:
        cfg = json.load(f)
    t.check(cfg["seeds"] >= 3 and cfg["steps"] >= 1000, f"{where}: 3 seeds a row or more, 1000 steps or more: {cfg}")
    for name in ("curves.svg", "times.json") + (() if rerun else ("output.txt",)):
        t.check(os.path.isfile(os.path.join(d, name)), f"{where}: no {name}")
    if not rerun:
        t.check(not any(f.endswith(".safetensors") for _, _, fs in os.walk(d) for f in fs), f"{where}: no weights are shipped")
    got = {}
    for row in ROWS:
        for seed in range(cfg["seeds"]):
            run = os.path.join(d, row, f"seed{seed}")
            with open(os.path.join(run, "config.json")) as f:
                c = json.load(f)
            t.check({k: v for k, v in c.items() if k not in ("label", "seed", "out")} ==
                    {k: v for k, v in cfg.items() if k not in ("label", "seed", "out")} and c["seed"] == seed and
                    c["label"] == row, f"{where}: {run} was run with other settings")
            with open(os.path.join(run, "log.jsonl")) as f:
                rows = [json.loads(line) for line in f if line.strip()]
            t.check(rows[0]["step"] == 0 and rows[-1]["step"] == cfg["steps"] - 1 and
                    all("held_bits" in r for r in rows), f"{where}: {run}/log.jsonl should have the validation curve")
            with open(os.path.join(run, "summary.json")) as f:
                got.setdefault(row, []).append(json.load(f)["test_bits"])
    import math

    def welch(a, b):
        va, vb = (sum((x - mean(xs)) ** 2 for x in xs) / (len(xs) - 1) for xs in (a, b))
        return (mean(a) - mean(b)) / math.sqrt(va / len(a) + vb / len(b))
    for row in ("rotary", "SwiGLU", "all-four"):
        t.check(mean(got[row]) < mean(got["base"]) - 0.03 and welch(got[row], got["base"]) < -3,
                f"{where}: {row} should be below the base beyond the noise: {got}")
    t.check(min(got, key=lambda r: mean(got[r])) == "all-four", f"{where}: all four together should be the lowest: {got}")
    for row in ("RMSNorm", "grouped-query"):
        t.check(abs(mean(got[row]) - mean(got["base"])) < 0.02 and abs(welch(got[row], got["base"])) < 3,
                f"{where}: {row} should score as the base does, within the noise: {got}")


def inside(S):
    import math
    import lab
    from experiments import ablation

    rows = {"a": {"bits": [3.0, 3.2, 3.1], "weights": 100}, "b": {"bits": [2.5, 2.6, 2.55], "weights": 90},
            "c": {"bits": [3.05, 3.15, 3.0], "weights": 110}}
    out = ablation.table(rows, {"a": [10.0, 12.0], "b": [20.0, 22.0], "c": [1.0, 1.0]}).splitlines()
    assert len(out) == 4 and "ms a step" in out[0]
    t = (2.55 - 3.1) / math.sqrt(0.01 / 3 + 0.0025 / 3)
    assert f"{2.55 - 3.1:+.4f} (t {t:+5.1f})" in out[2] and out[2].split()[-2:] == ["yes", "21.0"], out[2]
    assert out[3].split()[-2:] == ["no", "1.0"] and lab.spread([3.0, 3.2, 3.1], 4) in out[1] and "    90" in out[2]
    assert "yes" not in out[1] and "no" not in out[1].split(), out[1]
    assert "ms a step" not in ablation.table(rows).splitlines()[0]
    assert list(ablation.variants(lab.Config(kv_heads=2))) == ["base (08)", "RMSNorm", "rotary", "SwiGLU",
                                                               "grouped-query", "all four"]
    assert [ablation.label(n) for n in ablation.variants(lab.Config(kv_heads=2))] == ROWS
