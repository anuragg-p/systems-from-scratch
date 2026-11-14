"""00.02 The same run twice: seeds, configs and logs

The same settings and seed give the same log and summary, byte for byte; another seed or setting
gives others; config.json records what a run used; settings come from key=value on the command
line, and a setting the experiment does not have is an ordinary error.
"""

import json
import os


def read(path):
    with open(path, "rb") as f:
        return f.read()


def test(t):
    T = t.track
    T.inside(t, __file__)
    a = T.experiment(t, "curve", "seeds=1", "steps=300")
    b = T.experiment(t, "curve", "seeds=1", "steps=300")
    for name in ("log.jsonl", "summary.json"):
        t.check(read(f"{a.runs}/seed0/{name}") == read(f"{b.runs}/seed0/{name}"),
                f"two runs with the same seed differ in {name}")
    c = T.experiment(t, "curve", "seeds=2", "steps=300", "lr=0.3")
    t.check(read(f"{c.runs}/seed1/log.jsonl") != read(f"{c.runs}/seed0/log.jsonl"), "seeds 0 and 1 gave one log")
    t.check(read(f"{c.runs}/seed0/log.jsonl") != read(f"{a.runs}/seed0/log.jsonl"), "lr=0.3 changed nothing")
    with open(f"{c.runs}/seed1/config.json") as f:
        cfg = json.load(f)
    t.check(cfg["lr"] == 0.3 and cfg["seed"] == 1 and cfg["steps"] == 300 and cfg["n_train"] == 20,
            f"config.json should hold every setting and the seed: {cfg}")
    rows = [json.loads(l) for l in open(f"{a.runs}/seed0/log.jsonl")]
    t.check([r["step"] for r in rows] == [0, 100, 200, 300] and all("train_loss" in r for r in rows), rows)
    for args, word in ((["lrr=1"], "no setting 'lrr'"), (["steps"], "no setting 'steps'")):
        r = T.py(t, ["-m", "experiments.curve"] + args, check=False)
        t.check(r.rc == 2 and word in r.err and "Traceback" not in r.err, f"curve {args[0]}:\n{r}")


def inside(S):
    import sys
    import tempfile
    import lab

    sys.argv = ["experiments/demo.py"]
    cfg = lab.config(dict(a=1.0, b=[1], c="x", n=3), ["a=2", "b=[1, 2]", "c=yes", "n=7"])
    assert cfg.a == 2.0 and isinstance(cfg.a, float), cfg
    assert cfg.b == [1, 2] and cfg.c == "yes" and cfg.n == 7 and cfg["out"] == "runs" and cfg.name == "demo", cfg
    out = tempfile.mkdtemp()
    cfg = lab.config(dict(lr=0.1), [f"out={out}"])
    run = lab.Run(cfg, 3, label="first")
    assert run.dir == os.path.join(out, "demo", "first", "seed3"), run.dir
    assert run.rng.integers(0, 1 << 30) == __import__("numpy").random.default_rng(3).integers(0, 1 << 30)
    run.log(step=0, loss=1.5)
    assert read(os.path.join(run.dir, "log.jsonl")) == b'{"step": 0, "loss": 1.5}\n', "written at once"
    s = run.finish(loss=0.25)
    assert s == {"loss": 0.25} and json.load(open(os.path.join(run.dir, "summary.json"))) == s
    assert json.load(open(os.path.join(run.dir, "config.json"))) == {
        "label": "first", "lr": 0.1, "name": "demo", "out": out, "seed": 3}
    assert lab.read_log(run.dir) == [{"step": 0, "loss": 1.5}]
