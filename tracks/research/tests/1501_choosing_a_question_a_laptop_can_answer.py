"""15.01 Choosing a question a laptop can answer

The predictions are complete (each has words, a measure and a rule judge() knows) and judge() gives each rule's
three outcomes on made numbers; pair() starts the two arms from the same weights everywhere but the table of
positions, and the two runs of one seed draw the same batches; trained() scores the test text only when asked;
budget() is the arithmetic it says on made times; read_runs() gives back what lab.Run wrote. The recorded pilot
(experiments/recorded/pilot) has every file, read the validation text only, and the number of pairs its spread
gives is the number the recorded experiment ran. The default pilot prints the predictions first, finds positions
worth more than 0.05 bits at one block on every seed, and fixes a number of pairs; the same seed gives the same
bytes again.
"""

import json
import os

PILOT = "experiments/recorded/pilot"
DEPTH = "experiments/recorded/depth"


def read(path):
    with open(path, "rb") as f:
        return f.read()


def runs_in(d):
    """A recorded run, packed (runs.jsonl, one line a run, each file's text): {label: [(config, summary, log rows)]}
    in seed order."""
    out = {}
    with open(os.path.join(d, "runs.jsonl")) as f:
        packed = [json.loads(line) for line in f if line.strip()]
    for r in sorted(packed, key=lambda r: (r["label"], r["seed"])):
        files = r["files"]
        rows = [json.loads(line) for line in files["log.jsonl"].splitlines() if line.strip()]
        out.setdefault(r["label"], []).append((json.loads(files["config.json"]), json.loads(files["summary.json"]), rows))
    return out


def test(t):
    T = t.track
    T.inside(t, __file__)
    needed = check_pilot(t, os.path.join(t.root, PILOT))
    r = T.experiment(t, "pilot")
    t.check(r.out.index("1. The question") < r.out.index("2. The pilot") and r.out.count("(held if") == 7,
            f"the predictions, each with its rule, should come before the pilot:\n{r.out[:3000]}")
    for label in ("blocks1-none", "blocks1-learned"):
        t.check(len(T.summaries(r, label)) == 3, f"the default should run 3 seeds of {label}")
    gaps = [a["val_bits"] - b["val_bits"] for a, b in zip(T.summaries(r, "blocks1-none"),
                                                          T.summaries(r, "blocks1-learned"))]
    t.check(all(g > 0.05 for g in gaps), f"positions should be worth more than 0.05 bits at one block, every seed: {gaps}")
    for label in os.listdir(r.runs):
        for seed in os.listdir(os.path.join(r.runs, label)):
            t.check("test_bits" not in json.load(open(os.path.join(r.runs, label, seed, "summary.json"))),
                    f"the pilot should not read the test text: {label}/{seed}")
    n = int(T.value(r.out, r"^   (\d+) pairs \(13\.02's seeds_needed"))
    t.check(n >= 3, f"a number of pairs, at least 3: {n}")
    t.check(f"{needed} pairs, fixed before the experiment ran" in r.out,
            f"the default should read the recorded pilot and its {needed} pairs:\n{r.out[-1500:]}")
    t.check(T.value(r.out, r"about (\d+) minutes at the times measured now") > 0, "the budget should be printed")
    tiny = ["seeds=2", "steps=6", "every=2", "depths=[1,2]", "width=16", "context=16"]
    a, b = T.experiment(t, "pilot", *tiny), T.experiment(t, "pilot", *tiny)
    for run in ("blocks1-none/seed1", "blocks2-learned/seed1"):
        for name in ("log.jsonl", "summary.json"):
            t.check(read(os.path.join(a.runs, run, name)) == read(os.path.join(b.runs, run, name)),
                    f"the same seed twice gave two different {run}/{name}")


def check_pilot(t, d):
    """The recorded pilot: two depths that bound the plan, both arms, 4 seeds or more, validation only; and the
    number of pairs it gives, which the recorded experiment must have run."""
    import math
    where = f"the recorded pilot ({PILOT})"
    t.check(os.path.isdir(d) and os.path.isfile(os.path.join(d, "output.txt")), f"no {where}, or no output.txt")
    runs = runs_in(d)
    c = runs[next(iter(runs))][0][0]
    t.check(c["seeds"] >= 4 and min(c["depths"]) == 1 and max(c["depths"]) == max(c["plan_depths"]),
            f"{where}: 4 seeds or more, at depths bounding the plan: {c['depths']}, {c['seeds']}")
    t.check(set(runs) == {f"blocks{dd}-{arm}" for dd in c["depths"] for arm in ("none", "learned")},
            f"{where}: both arms at every depth: {sorted(runs)}")
    sds = []
    for dd in c["depths"]:
        none, learned = runs[f"blocks{dd}-none"], runs[f"blocks{dd}-learned"]
        for (cn, sn, rn), (cl, sl, rl) in zip(none, learned):
            t.check({k: v for k, v in cn.items() if k != "label"} == {k: v for k, v in cl.items() if k != "label"},
                    f"{where}: the two arms of seed {cn['seed']} at {dd} blocks were run with other settings")
            t.check("test_bits" not in sn and "test_bits" not in sl, f"{where}: the pilot read the test text")
            t.check(rn[0]["step"] == 0 and rn[-1]["step"] == c["steps"] - 1, f"{where}: a log from 0 to the last step")
            t.check(sl["weights"] - sn["weights"] == c["context"] * c["width"],
                    f"{where}: learned positions should add context x width weights")
        gaps = [sn["val_bits"] - sl["val_bits"] for (_, sn, _), (_, sl, _) in zip(none, learned)]
        m = sum(gaps) / len(gaps)
        sds.append(math.sqrt(sum((g - m) ** 2 for g in gaps) / (len(gaps) - 1)))
    import subprocess
    import sys
    code = (f"import lab; from experiments import question as q; "
            f"print(max(3, lab.seeds_needed(q.SMALLEST, {max(sds)!r}, q.LEVEL, q.POWER, paired=True)))")
    out = subprocess.run([sys.executable, "-B", "-c", code], cwd=t.root, capture_output=True, text=True,
                         env=dict(os.environ, PYTHONPATH=t.root))
    t.check(out.returncode == 0, f"seeds_needed failed: {out.stderr[-800:]}")
    needed = int(out.stdout.strip())
    depth = runs_in(os.path.join(t.root, DEPTH)) if os.path.isdir(os.path.join(t.root, DEPTH)) else {}
    if depth:
        main = [x for label, x in depth.items() if not label.startswith(("search", "control"))]
        t.check(all(len(x) == needed for x in main),
                f"the recorded experiment should run the {needed} pairs the pilot fixed: "
                f"{sorted({len(x) for x in main})}")
    return needed


def inside(S):
    import tempfile
    import torch
    import lab
    from experiments import question as q

    # every prediction has words, a measure, and a rule judge() knows
    kinds = {"largest", "falls", "above", "clear", "about", "worse", "closes_under"}
    assert len(q.PREDICTIONS) == 7 and len({p.key for p in q.PREDICTIONS}) == 7
    assert all(p.says and p.measure and p.rule[0] in kinds for p in q.PREDICTIONS), q.PREDICTIONS
    assert q.SMALLEST == 0.02 and q.LEVEL == 0.95 and q.POWER == 0.8 and q.ARMS == ("none", "learned")
    assert all(r.key and r.cite and r.where and r.found for r in q.RELATED)

    # judge, each rule's outcomes on made numbers
    gaps = {1: [0.30, 0.32, 0.28], 2: [0.10, 0.12, 0.08], 4: [0.06, 0.07, 0.05], 8: [0.01, 0.03, -0.01]}
    bits = {(8, "none"): [3.38, 3.39, 3.37], (4, "learned"): [3.34, 3.35, 3.33], (4, "none"): [3.40, 3.41, 3.39]}
    control = {4: [3.40, 3.40, 3.39]}
    J = lambda rule, g=gaps, b=bits: q.judge(rule, g, b, control)[0]
    assert J(("largest", 1)) == "held" and J(("largest", 4)) == "did not hold"
    assert J(("falls",)) == "held" and J(("falls",), {**gaps, 8: [0.07, 0.08, 0.09]}) == "did not hold"
    assert J(("above", 1, 0.1)) == "held" and J(("above", 4, 0.1)) == "did not hold"
    assert J(("above", "deepest", 0.0)) == "not settled"
    assert J(("clear", "deepest")) == "did not hold" and J(("clear", 4)) == "held"
    assert J(("about", 4, 0.065, 2.0)) == "held" and J(("about", 8, 0.065, 2.0)) == "did not hold"
    assert J(("worse", "deepest", 4)) == "held"
    assert J(("worse", "deepest", 4), b={**bits, (8, "none"): [3.30, 3.31, 3.29]}) == "did not hold"
    assert J(("worse", "deepest", 4), b={**bits, (8, "none"): [3.30, 3.40, 3.35]}) == "not settled"
    verdict, share = q.judge(("closes_under", 4, 0.25), gaps, bits, control)
    assert verdict == "held" and abs(share - (3.40 - 3.3966666666666665) / 0.06) < 1e-9, share
    assert q.judge(("closes_under", 4, 0.25), gaps, bits, {4: [3.36, 3.36, 3.36]})[0] == "did not hold"
    assert all(q.rule_text(p.rule) for p in q.PREDICTIONS)

    # pair: the same start for every weight both have, positions only in one
    cfg = lab.Config(context=16, heads=2, width=16, batch=4, steps=3, lr=0.003, warmup=1, weight_decay=0.1, clip=1.0,
                     every=1, out=tempfile.mkdtemp(), name="pilot")
    dev = torch.device("cpu")
    for layers in (1, 3):
        arms = q.pair(65, cfg, layers, 0, dev)
        none, learned = arms["none"].state_dict(), arms["learned"].state_dict()
        assert set(learned) - set(none) == {"positions.weight"} and not set(none) - set(learned)
        assert all(torch.equal(v, learned[k]) for k, v in none.items())
        other = q.pair(65, cfg, layers, 1, dev)["none"].state_dict()
        assert not torch.equal(other["tokens.weight"], none["tokens.weight"])
    # ... and the same batches: both runs of a seed draw their windows from a Run's rng seeded alike
    texts = {s: torch.arange(200) % 65 for s in ("train", "val", "test")}
    class Spy:
        """A Run's rng that keeps every batch of window starts it draws."""
        def __init__(self, rng):
            self.rng, self.drawn = rng, []

        def integers(self, *a, **k):
            self.drawn.append(self.rng.integers(*a, **k))
            return self.drawn[-1]

    drawn = {}
    for arm, model in q.pair(65, cfg, 2, 7, dev).items():
        run = lab.Run(cfg, 7, label=f"x-{arm}")
        run.rng = Spy(run.rng)
        summary = q.trained(model, cfg, run, dev, texts)
        drawn[arm] = run.rng.drawn
        assert set(summary) == {"val_bits", "weights"}, summary        # no test text unless asked
    assert len(drawn["none"]) == 3 and all((a == b).all() for a, b in zip(drawn["none"], drawn["learned"]))
    with_test = q.trained(q.pair(65, cfg, 1, 0, dev)["none"], cfg, lab.Run(cfg, 0, label="y"), dev, texts, test=True)
    assert set(with_test) == {"val_bits", "test_bits", "weights"} and with_test["weights"] == 65 * 16 + 12 * 256 + 13 * 16 + 32

    # budget: measured depths as measured, the rest on the line through them
    minutes, per = q.budget({1: 3.0, 8: 17.0}, [1, 2, 4, 8], 10)
    assert per == {1: 3.0, 2: 5.0, 4: 9.0, 8: 17.0} and abs(minutes - (3 + 5 + 9 + 17) * 2 * 10 / 60) < 1e-12
    assert abs(q.budget({1: 3.0, 2: 5.0, 4: 9.0}, [6], 1, arms=1)[0] - 13.0 / 60) < 1e-12

    # read_runs gives back what lab.Run wrote
    for seed in (1, 0):
        run = lab.Run(cfg, seed, label="blocks1-none")
        run.log(step=0, bits=1.0)
        run.finish(val_bits=3.0 + seed, weights=10)
    back = q.read_runs(os.path.join(cfg.out, "pilot"))
    assert [s["val_bits"] for _, s in back["blocks1-none"]] == [3.0, 4.0]
    assert [c["seed"] for c, _ in back["blocks1-none"]] == [0, 1] and back["blocks1-none"][0][0]["lr"] == 0.003

    # pack: the folders made into runs.jsonl and removed; read_runs the same; unpack gives the bytes back
    d = os.path.join(cfg.out, "pilot")
    before = {}
    for label in os.listdir(d):
        for seed in os.listdir(os.path.join(d, label)):
            for name in q.RUN_FILES:
                with open(os.path.join(d, label, seed, name), "rb") as f:
                    before[label, seed, name] = f.read()
    assert q.pack(d) == len(before) // 3 and os.listdir(d) == ["runs.jsonl"]
    assert q.read_runs(d) == back
    q.unpack(d, os.path.join(cfg.out, "again"))
    for (label, seed, name), data in before.items():
        with open(os.path.join(cfg.out, "again", label, seed, name), "rb") as f:
            assert f.read() == data, (label, seed, name)
