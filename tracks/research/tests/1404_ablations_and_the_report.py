"""14.04 Ablations, and the report

settings lists every run the three sweeps need, each once; median_steps counts a run that never got
there as later than any; scaled_start multiplies every weight but the layer norms'; read_seeds and
read_runs give back what lab.Run wrote; sweep picks a sweep's runs out of them; norm_ratio and
outcomes compute each claim's number from a fixture of logs written here, whose answers are known;
changes lists the settings that differ from the paper's. The recorded ablations
(experiments/recorded/ablations) have every file, and their result: without weight decay no seed
generalises in the steps given, with weight decay 1 every seed does; with more of the equations the
median steps to 99% fall; ten times GPT's start generalises later at 50% than GPT's own. The default
reads them and prints their table; the report, read from the recorded runs, gives the same numbers as
their summaries and a verdict for every claim. A tiny sweep run twice gives the same bytes, and the
report reads it.
"""

import json
import os
import re

ABLATIONS = "experiments/recorded/ablations"
FIGURE = "experiments/recorded/grokking"


def read(path):
    with open(path, "rb") as f:
        return f.read()


def summaries(d):
    out = {}
    for label in sorted(os.listdir(d)):
        if os.path.isdir(os.path.join(d, label)):
            seeds = sorted(int(s[4:]) for s in os.listdir(os.path.join(d, label)) if s.startswith("seed"))
            for seed in seeds:
                with open(os.path.join(d, label, f"seed{seed}", "summary.json")) as f:
                    s = json.load(f)
                with open(os.path.join(d, label, f"seed{seed}", "config.json")) as f:
                    s["config"] = json.load(f)
                out.setdefault(label, []).append(s)
    return out


def median_of(xs):
    xs = sorted(xs, key=lambda x: float("inf") if x is None else x)
    return xs[len(xs) // 2]


def test(t):
    T = t.track
    T.inside(t, __file__)
    runs = check_recorded(t, os.path.join(t.root, ABLATIONS))
    r = T.experiment(t, "ablations")
    t.check(r.out.count("validation 99% at step") >= 7 and "1. Weight decay" in r.out and "3. The start" in r.out,
            f"the default should print the recorded runs' three tables:\n{r.out[-2000:]}")
    for label, seeds in runs.items():
        med = median_of([s["val99"] for s in seeds])
        if med is not None:
            t.check(f"median {med}\n" in r.out, f"the table should give {label}'s median, {med}:\n{r.out[-2000:]}")
    rep = T.experiment(t, "report")
    text = read(os.path.join(rep.runs, "report.txt")).decode()
    t.check(text.strip() in rep.out, "the report printed should be the report written")
    with open(os.path.join(t.root, FIGURE, "seed0", "config.json")) as f:
        seeds = json.load(f)["seeds"]
    fig = []
    for seed in range(seeds):
        with open(os.path.join(t.root, FIGURE, f"seed{seed}", "summary.json")) as f:
            fig.append(json.load(f))
    t99 = median_of([s["train99"] for s in fig])
    t.check(re.search(rf"memorise .*\n.*\n      ours: {t99} \(", text) is not None,
            f"the report's memorise should be the summaries' median, {t99}:\n{text[:3000]}")
    verdicts = re.findall(r"^      (held|did not hold|not settled) \(held if", text, re.M)
    t.check(len(verdicts) == 10, f"every claim should have a verdict: {verdicts}")
    t.check("fraction: ours 0.35, the paper's 0.5" in text, f"the report should say what was changed:\n{text[:1500]}")

    tiny = ["train=True", "seeds=2", "steps=8", "p=7", "per_decade=5"]
    a, b = T.experiment(t, "ablations", *tiny), T.experiment(t, "ablations", *tiny)
    for label in os.listdir(a.runs):
        if os.path.isdir(os.path.join(a.runs, label)):
            for name in ("log.jsonl", "summary.json"):
                t.check(read(os.path.join(a.runs, label, "seed1", name)) == read(os.path.join(b.runs, label, "seed1", name)),
                        f"the same seed twice gave two different {label}/seed1/{name}")
    g = T.experiment(t, "grokking", "seeds=2", "steps=8", "p=7")
    T.experiment(t, "report", f"figure={g.runs}", f"ablations={a.runs}")


def check_recorded(t, d):
    """The recorded ablations: every setting the sweeps need, every seed's files, and the result."""
    where = f"the recorded ablations ({ABLATIONS})"
    t.check(os.path.isdir(d) and os.path.isfile(os.path.join(d, "output.txt")), f"no {where}, or no output.txt")
    runs = summaries(d)
    c = next(iter(runs.values()))[0]["config"]
    t.check(c["seeds"] >= 3 and len(c["decays"]) >= 3 and 0.0 in c["decays"] and len(c["fractions"]) >= 3,
            f"{where}: no weight decay and two sizes, three fractions or more, 3 seeds or more: {c}")
    want = {f"fraction{f:g}-decay{wd:g}-start{s:g}" for f, wd, s in
            [(c["decay_fraction"], wd, 1.0) for wd in c["decays"]] + [(f, c["fraction_decay"], 1.0) for f in c["fractions"]]
            + [(c["start_fraction"], c["start_decay"], s) for s in c["starts"]]}
    t.check(set(runs) == want and all(len(s) == c["seeds"] for s in runs.values()),
            f"{where}: every setting the sweeps need, {c['seeds']} seeds each: {sorted(runs)}")
    for label, seeds in runs.items():
        for k, s in enumerate(seeds):
            log = os.path.join(d, label, f"seed{k}", "log.jsonl")
            with open(log) as f:
                rows = [json.loads(line) for line in f if line.strip()]
            t.check(rows[0]["step"] == 0 and rows[-1]["step"] == s["last_step"] and
                    (s["val99"] == s["last_step"] or s["last_step"] == c["steps"]),
                    f"{where}: {label} seed {k} should stop where validation reached 99%, or at the last step")

    def sweep(**fixed):
        return [s for seeds in runs.values() for s in seeds if all(s["config"][k] == v for k, v in fixed.items())]
    none = sweep(fraction=c["decay_fraction"], weight_decay=0.0, start=1.0)
    full = sweep(fraction=c["decay_fraction"], weight_decay=1.0, start=1.0)
    t.check(all(s["val99"] is None and s["best_val_acc"] < 0.5 for s in none),
            f"{where}: without weight decay no seed should generalise in {c['steps']} steps: {none}")
    t.check(all(s["val99"] is not None for s in full), f"{where}: with weight decay 1 every seed should: {full}")
    meds = [median_of([s["val99"] for s in sweep(fraction=f, weight_decay=c["fraction_decay"], start=1.0)])
            for f in sorted(c["fractions"])]
    t.check(None not in meds and all(a > b for a, b in zip(meds, meds[1:])),
            f"{where}: the more of the equations, the sooner validation reaches 99% (median): {meds}")
    own, big = (median_of([s["val99"] for s in sweep(fraction=c["start_fraction"], weight_decay=c["start_decay"],
                                                       start=x)]) for x in (1.0, max(c["starts"])))
    t.check(own is not None and big is not None and big > 2 * own,
            f"{where}: a larger start should generalise later, at 50%: {own} against {big}")
    return runs


def inside(S):
    import math
    import tempfile
    import torch
    import lab
    from experiments import ablations, arithmetic, report
    from experiments.predictions import CLAIMS, SETUP
    from models.gpt import GPT

    cfg = lab.Config(ablations.CONFIG)
    assert ablations.settings(cfg) == [(0.4, 0.0, 1.0), (0.4, 0.3, 1.0), (0.4, 1.0, 1.0), (0.35, 1.0, 1.0),
                                       (0.5, 1.0, 1.0), (0.5, 1.0, 10.0)], ablations.settings(cfg)
    assert arithmetic.median_steps([300, None, 100], 5000) == (300, False)
    assert arithmetic.median_steps([None, 100, None], 5000) == (5000, True)
    assert arithmetic.median_steps([200, 100], 5000) == (200, False)

    torch.manual_seed(0)
    model = GPT(11, 4, layers=1, heads=2, width=8)
    before = {k: v.clone() for k, v in model.state_dict().items()}
    arithmetic.scaled_start(model, 3.0)
    for k, v in model.state_dict().items():
        assert torch.equal(v, before[k] if "norm" in k else 3 * before[k]), k

    def rows(t99, v99, steps, peak=6.0, norms=(27.0, 30.0, 20.0)):
        out = []
        for s in sorted({0, 10, t99 or steps, v99 or steps, steps}):
            out.append(dict(step=s, train_acc=1.0 if t99 is not None and s >= t99 else 0.5,
                            val_acc=1.0 if v99 is not None and s >= v99 else (0.02 if s else 0.01),
                            train_loss=0.1, val_loss=peak if s == t99 else 4.0,
                            norm=norms[0] if s == 0 else (norms[1] if v99 is None or s < v99 else norms[2])))
        return out

    with tempfile.TemporaryDirectory() as d:
        base = {k: v for k, (v, _) in SETUP.items()}
        fig_cfg = lab.Config(base, fraction=0.35, steps=5000, seeds=3, per_decade=20, out=d, name="grokking")
        for seed, (t99, v99) in enumerate([(400, 2000), (500, 2500), (400, None)]):
            run = lab.Run(fig_cfg, seed)
            for row in rows(t99, v99, 5000):
                run.log(**row)
            run.finish()
        abl_cfg = lab.Config(cfg, out=d, name="ablations")
        answers = {(0.4, 0.0, 1.0): [None, None, None], (0.4, 0.3, 1.0): [4000, None, 5000],
                   (0.4, 1.0, 1.0): [1000, 1250, 1500], (0.35, 1.0, 1.0): [2000, 2500, 3000],
                   (0.5, 1.0, 1.0): [500, 600, 700], (0.5, 1.0, 10.0): [3000, 4000, 5000]}
        for (f, wd, s), v99s in answers.items():
            c = lab.Config(abl_cfg, fraction=f, weight_decay=wd, start=s)
            for seed, v99 in enumerate(v99s):
                run = lab.Run(c, seed, label=ablations.label(f, wd, s))
                for row in rows(300 if f < 0.5 else 200, v99, v99 or cfg.steps):
                    run.log(**row)
                run.finish()
        fig = arithmetic.read_seeds(os.path.join(d, "grokking"))
        abl = arithmetic.read_runs(os.path.join(d, "ablations"))
        assert len(fig) == 3 and fig[2][0]["seed"] == 2 and fig[0][1][0]["step"] == 0
        assert sorted(abl) == sorted(ablations.label(*k) for k in answers) and all(len(v) == 3 for v in abl.values())
        table = ablations.sweep(abl, "weight_decay", cfg.decays, dict(fraction=0.4, start=1.0))
        assert [row[2] for row in table] == [answers[(0.4, wd, 1.0)] for wd in cfg.decays], table
        assert table[0][3] == [0.02, 0.02, 0.02] and table[2][4] == cfg.steps

        assert report.norm_ratio(fig[0][1]) == 20.0 / 30.0 and report.norm_ratio(fig[2][1]) is None
        got = report.outcomes(fig, abl)
        assert set(got) == {c.key for c in CLAIMS}
        assert got["memorise"][:2] == (400, False) and got["near_chance"][0] == 0.02
        assert got["late"][:2] == (5.0, True), got["late"]
        assert got["generalise"][0] == 1.0 and abs(got["loss_rises"][0] - 6.0 / math.log(97)) < 1e-12
        k = math.log(2500 / 600) / math.log(0.5 / 0.35)
        assert abs(got["less_data"][0] - k) < 1e-12 and got["less_data"][1] is False
        assert got["train_sooner"][0] == 300 / 200 and abs(got["decay"][0] - 0.02) < 1e-12
        assert got["more_decay"][:2] == (5000 / 1250, False), got["more_decay"]
        assert got["norm_falls"][0] is None, "a seed that never generalised leaves it unsettled"
    assert report.changes(dict(base, fraction=0.35, steps=5000)) == [
        f"fraction: ours 0.35, the paper's 0.5 ({SETUP['fraction'][1]})",
        f"steps: ours 5000, the paper's 100000 ({SETUP['steps'][1]})"]
