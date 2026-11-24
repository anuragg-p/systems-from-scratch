"""15.03 The paper, and a repository anyone can rerun

defaults() reads an experiment's CONFIG from its source without importing it; command() gives back the command
that made a run, from its config.json alone, every list quoted. The paper built from a small fixture of runs
written here has the fixture's numbers in it: the gap and its interval, the pairs the pilot asked for, every
verdict. On the recorded runs the paper is printed as written, its abstract four sentences, its commands the
recorded runs' own; and the experiment's command is true: given as the paper prints it, cut to one depth, one rate and
one pair, in a clean copy of the project with no runs and no records, it makes the recorded runs of that pair again.
"""

import hashlib
import json
import os
import re
import shlex
import shutil

DEPTH = "experiments/recorded/depth"
PILOT = "experiments/recorded/pilot"
PAPER = "experiments/recorded/paper"


def read(path):
    with open(path, "rb") as f:
        return f.read()


def test(t):
    T = t.track
    T.inside(t, __file__)
    r = T.experiment(t, "paper")
    text = read(os.path.join(r.runs, "paper.txt")).decode()
    t.check(text.strip() in r.out, "the paper printed should be the paper written")
    t.check(read(os.path.join(t.root, PAPER, "paper.txt")).decode() == text,
            f"{PAPER}/paper.txt should be what paper.py writes from the recorded runs today")
    abstract = text.split("Abstract\n\n", 1)[1].split("\n\n", 1)[0].replace("\n", " ")
    t.check(len(re.findall(r"[a-z0-9)]\. (?=[A-Z])", abstract)) == 3 and abstract.endswith("."),
            f"the abstract should be four sentences:\n{abstract}")
    for section in ("1. The problem", "2. What this paper shows", "3. Method", "4. Results",
                    "5. The predictions, written before any run", "6. What was not expected", "7. What others found",
                    "8. Limits", "9. To make every number again"):
        t.check(f"\n{section}\n" in text, f"the paper should have a section {section!r}")
    t.check(len(re.findall(r"^   (held|did not hold|not settled)$", text, re.M)) == 7, "a verdict for each prediction")
    with open(os.path.join(t.root, DEPTH, "blocks1-none", "seed1", "config.json")) as f:
        cfg = json.load(f)
    lines = [line.strip() for line in text.splitlines() if line.startswith("   python3 -m experiments.depth")]
    main = [line for line in lines if f"seeds={cfg['seeds']}" in line]
    t.check(len(main) == 1, f"the paper should give the experiment's command once: {lines}")
    words = shlex.split(main[0])
    given = dict(w.split("=", 1) for w in words[3:])
    for key in ("depths", "rates", "seeds", "steps", "every", "control", "out"):
        t.check(given.get(key) == (cfg[key] if isinstance(cfg[key], str) else json.dumps(cfg[key]).replace(" ", "")),
                f"the paper's command should give {key}={cfg[key]!r}: {main[0]}")
    t.check(set(given) == {"depths", "rates", "seeds", "steps", "every", "control", "out"},
            f"the command should give the settings that differ from depth.py's defaults, no others: {main[0]}")
    with open(os.path.join(t.root, "data", "tinyshakespeare.txt"), "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    t.check(digest in text, "the paper should give the text's SHA-256")

    # The command is true: run in a clean copy of the project (no runs, no records), cut to one depth, one rate and
    # two pairs (an interval needs two), it makes the recorded runs of those pairs again, byte for byte.
    clean = os.path.join(t.tmp, "clean")
    shutil.copytree(t.root, clean, ignore=shutil.ignore_patterns("__pycache__", "runs", "recorded"))
    one = {"depths": "[1]", "rates": f"[{cfg_rate(t)}]", "seeds": "2", "control": "0"}
    args = [f"{k}={one.get(k, v)}" for k, v in given.items() if k != "out"]
    r = T.experiment(t, "depth", *args, root=clean)
    for arm in ("none", "learned"):
        for seed in (1, 2):
            for name in ("log.jsonl", "summary.json"):
                got = read(os.path.join(r.runs, f"blocks1-{arm}", f"seed{seed}", name))
                want = read(os.path.join(t.root, DEPTH, f"blocks1-{arm}", f"seed{seed}", name))
                t.check(got == want, f"a clean copy, from the paper's command, gave another "
                                     f"blocks1-{arm}/seed{seed}/{name}")


def cfg_rate(t):
    """The rate the recorded search chose for both models at one block (they chose the same)."""
    rates = set()
    for arm in ("none", "learned"):
        with open(os.path.join(t.root, DEPTH, f"blocks1-{arm}", "seed1", "config.json")) as f:
            rates.add(json.load(f)["lr"])
    t.check(len(rates) == 1, f"both models at one block should run at one rate: {rates}")
    return rates.pop()


def inside(S):
    import tempfile
    import lab
    from experiments import paper, question as q

    # defaults: a CONFIG read from source, never imported (this file would raise if it were)
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "experiments"))
    with open(os.path.join(d, "experiments", "made.py"), "w") as f:
        f.write('raise SystemExit("imported")\nCONFIG = dict(steps=300, lrs=[0.1, 0.01], name_it="x", flag=True)\n')
    assert paper.defaults("made", d) == {"steps": 300, "lrs": [0.1, 0.01], "name_it": "x", "flag": True}
    # command: only what differs from the defaults, lists quoted, the runner's own keys left out
    settings = {"name": "made", "label": "a", "seed": 3, "out": "runs", "steps": 300, "lrs": [0.3, 0.1],
                "name_it": "y", "flag": True, "lr": 0.003}
    assert paper.command(settings, d) == 'python3 -m experiments.made "lrs=[0.3,0.1]" name_it=\'y\' out=runs', \
        paper.command(settings, d)
    assert paper.command(dict(settings, lrs=[0.1, 0.01], name_it="x"), d) == "python3 -m experiments.made out=runs"
    assert paper.command(json.load(open("experiments/recorded/pilot/blocks1-none/seed0/config.json"))) == \
        'python3 -m experiments.pilot "depths=[1,8]" seeds=4 out=experiments/recorded'

    # the paper from a fixture of runs whose numbers are known
    out = tempfile.mkdtemp()
    base = lab.Config(width=64, context=32, heads=4, batch=32, steps=300, warmup=50, weight_decay=0.1, clip=1.0,
                      every=100, recorded="experiments/recorded", device="cpu", out=out)
    pc = lab.Config(base, lr=0.003, depths=[1, 8], seeds=4, plan_depths=[1, 2, 4, 6, 8], plan_rates=4, name="pilot")
    for dd, g in ((1, [0.10, 0.14, 0.12, 0.16]), (8, [0.03, 0.03, 0.04, 0.02])):
        for seed, gap in enumerate(g):
            for arm, v in (("none", 3.5 + gap), ("learned", 3.5)):
                run = lab.Run(pc, seed, label=f"blocks{dd}-{arm}")
                run.log(step=0, bits=6.0)
                run.finish(val_bits=v, weights=1000 + (2048 if arm == "learned" else 0))
    dc = lab.Config(base, depths=[1, 4, 8], rates=[0.003, 0.006], seeds=3, control=4, name="depth")
    gaps = {1: [0.30, 0.32, 0.28], 4: [0.06, 0.07, 0.05], 8: [0.03, 0.035, 0.025]}
    for dd in dc.depths:
        for arm in q.ARMS:
            for rate in dc.rates:
                run = lab.Run(lab.Config(dc, lr=rate), 0, label=f"search-blocks{dd}-{arm}-lr{rate:g}")
                run.finish(val_bits=3.4 + (0.01 if rate == 0.006 else 0), weights=5)
            for seed, gap in enumerate(gaps[dd], start=1):
                run = lab.Run(lab.Config(dc, lr=0.003), seed, label=f"blocks{dd}-{arm}")
                v = 3.4 - 0.01 * dd + (gap if arm == "none" else 0)
                run.finish(val_bits=v, test_bits=v + 0.2, weights=100 * dd + (2048 if arm == "learned" else 0))
    for seed in (1, 2, 3):
        run = lab.Run(lab.Config(dc, lr=0.003), seed, label="control-blocks4-wider")
        run.finish(val_bits=3.4, test_bits=3.4 - 0.04 + 0.2 + 0.055, weights=400 + 2064)
    with open(os.path.join(out, "pilot", "output.txt"), "w") as f:
        f.write("157 s of training and scoring on cpu\n")
    r = paper.gather(os.path.join(out, "pilot"), os.path.join(out, "depth"))
    assert r["depths"] == [1, 4, 8] and r["seeds"] == [1, 2, 3] and r["chosen"][1, "none"] == 0.003
    assert abs(r["gaps"][1][1] - 0.30) < 1e-9 and r["gaps"][1][4] == 3
    assert r["needed"] == max(3, lab.seeds_needed(q.SMALLEST, lab.sd([0.10, 0.14, 0.12, 0.16]), paired=True))
    assert r["verdicts"]["one_block"][0] == "held" and r["verdicts"]["shrinks"][0] == "held"
    assert r["verdicts"]["again"][0] == "held" and r["verdicts"]["not_closed"][0] == "held"
    assert r["seconds"] == {"pilot": 157, "depth": None}
    lines = paper.paper(r, lab.Config(paper.CONFIG, pilot=os.path.join(out, "pilot"), depth=os.path.join(out, "depth")))
    text = "\n".join(lines)
    _, lo, hi = lab.difference([3.80, 3.82, 3.78], [3.5, 3.5, 3.5], paired=True)
    assert f"0.300 bits ({lo:.3f} to {hi:.3f})" in text, text[:2000]
    assert f"ask for {r['needed']} pairs" in text and "3/3" in text
    assert len(paper.abstract(r)) == 4 and all(s.endswith(".") for s in paper.abstract(r))
    assert sum(line.strip() in ("held", "did not hold", "not settled") for line in lines) == 7
    for p in q.PREDICTIONS:
        assert f"{p.key}: {p.says}" in " ".join(text.split())
