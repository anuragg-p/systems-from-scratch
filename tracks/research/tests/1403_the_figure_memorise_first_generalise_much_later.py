"""14.03 The figure: memorise first, generalise much later

weight_norm is the square root of the sum of every weight's square; first_step finds the first
measured step at a level; milestones reads a log for the steps to 99% on each split, their ratio,
validation accuracy at the first, the validation loss's peak and the weights' norm. The recorded long
run (experiments/recorded/grokking) has every file, its settings and its log at every measured step,
and its result: every seed memorised in under 1000 steps with validation accuracy near chance, then
reached 99% on validation three or more times later; the validation loss rose above a guess's in
between; the weights were smaller when it generalised than at their largest. A short run that
generalises (50% of the equations): both 99% steps found, the norm smaller at the second; and the
same seed gives the same bytes again. With LEARN_RERUN_LONG=1 the long run is run again (about ten
minutes).
"""

import json
import math
import os

LONG = "experiments/recorded/grokking"


def read(path):
    with open(path, "rb") as f:
        return f.read()


def test(t):
    T = t.track
    T.inside(t, __file__)
    check_recorded(t, os.path.join(t.root, LONG))
    r = T.experiment(t, "grokking", "fraction=0.5", "steps=800", "seeds=2")
    for s in T.summaries(r):
        t.check(s["train99"] is not None and s["val99"] is not None and s["norm_at_val99"] < s["norm_start"],
                f"at 50% of the equations both accuracies should reach 99% within 800 steps, the weights smaller "
                f"then than at the start: {s}")
    t.check("Memorised, then generalised" in r.out and os.path.isfile(os.path.join(r.runs, "norm.svg")),
            f"the milestones and the norm's curve:\n{r.out[-1500:]}")
    tiny = ["seeds=2", "steps=12", "p=7", "fraction=0.5"]
    a, b = T.experiment(t, "grokking", *tiny), T.experiment(t, "grokking", *tiny)
    for name in ("log.jsonl", "summary.json"):
        t.check(read(os.path.join(a.runs, "seed1", name)) == read(os.path.join(b.runs, "seed1", name)),
                f"the same seed twice gave two different seed1/{name}")
    if os.environ.get("LEARN_RERUN_LONG"):
        with open(os.path.join(t.root, LONG, "seed0", "config.json")) as f:
            cfg = json.load(f)
        settings = [f"{k}={cfg[k]!r}".replace(" ", "") for k in ("p", "operation", "fraction", "layers", "heads", "width",
                                                                   "lr", "weight_decay", "betas", "warmup", "batch",
                                                                   "steps", "per_decade", "seeds")]
        again = T.experiment(t, "grokking", *settings, timeout=3 * 3600)
        check_recorded(t, again.runs, rerun=True)


def check_recorded(t, d, rerun=False):
    """The long run: every seed's config, log and summary, the curves, what it printed, and its result."""
    where = "the rerun" if rerun else f"the recorded run ({LONG})"
    t.check(os.path.isdir(d), f"no {where}")
    with open(os.path.join(d, "seed0", "config.json")) as f:
        cfg = json.load(f)
    t.check(cfg["seeds"] >= 3 and cfg["steps"] >= 3000 and cfg["p"] == 97 and cfg["operation"] == "/",
            f"{where}: x/y mod 97, 3 seeds or more, 3000 steps or more: {cfg}")
    for name in ("accuracy.svg", "loss.svg", "norm.svg") + (() if rerun else ("output.txt",)):
        t.check(os.path.isfile(os.path.join(d, name)), f"{where}: no {name}")
    for seed in range(cfg["seeds"]):
        run = os.path.join(d, f"seed{seed}")
        with open(os.path.join(run, "config.json")) as f:
            c = json.load(f)
        t.check({k: v for k, v in c.items() if k not in ("seed", "out")} == {k: v for k, v in cfg.items()
                                                                              if k not in ("seed", "out")}
                and c["seed"] == seed, f"{where}: {run} was run with other settings")
        with open(os.path.join(run, "log.jsonl")) as f:
            rows = [json.loads(line) for line in f if line.strip()]
        t.check(rows[0]["step"] == 0 and rows[-1]["step"] == cfg["steps"] and len(rows) > 50 and
                all({"train_acc", "val_acc", "train_loss", "val_loss", "norm"} <= set(row) for row in rows),
                f"{where}: {run}/log.jsonl should hold both splits and the norm from step 0 to the end")
        with open(os.path.join(run, "summary.json")) as f:
            s = json.load(f)
        t.check(s["train99"] is not None and s["train99"] < 1000 and s["val_acc_at_train99"] < 0.05,
                f"{where}: seed {seed} should memorise in under 1000 steps, validation near chance meanwhile: {s}")
        t.check(s["val99"] is not None and s["val99"] >= 3 * s["train99"],
                f"{where}: seed {seed} should reach 99% on validation three or more times later: {s}")
        t.check(s["peak_val_loss"] > math.log(cfg["p"]) and s["train99"] <= s["peak_step"] < s["val99"],
                f"{where}: seed {seed}'s validation loss should rise above a guess's between the two: {s}")
        t.check(s["norm_at_val99"] < s["norm_max"], f"{where}: seed {seed}'s weights should have shrunk: {s}")


def inside(S):
    import math
    import torch
    from experiments import arithmetic
    from models.gpt import GPT

    torch.manual_seed(0)
    model = GPT(11, 4, layers=1, heads=2, width=8)
    want = torch.cat([p.detach().flatten() for p in model.parameters()]).double().norm().item()
    assert abs(arithmetic.weight_norm(model) - want) < 1e-5 * want, (arithmetic.weight_norm(model), want)

    rows = [dict(step=s, train_acc=ta, val_acc=va, train_loss=tl, val_loss=vl, norm=n) for s, ta, va, tl, vl, n in [
        (0, 0.01, 0.01, 4.6, 4.6, 27.0), (10, 0.5, 0.01, 2.0, 5.0, 28.0), (100, 0.995, 0.02, 0.1, 6.0, 30.0),
        (1000, 1.0, 0.5, 0.05, 3.0, 25.0), (2000, 1.0, 0.999, 0.01, 0.02, 20.0), (3000, 1.0, 1.0, 0.01, 0.01, 19.0)]]
    assert arithmetic.first_step(rows, "train_acc", 0.99) == 100 and arithmetic.first_step(rows, "val_acc", 0.99) == 2000
    assert arithmetic.first_step(rows, "val_acc", 1.5) is None
    m = arithmetic.milestones(rows, 97)
    assert (m["train99"], m["val99"], m["ratio"], m["val_acc_at_train99"]) == (100, 2000, 20.0, 0.02), m
    assert m["peak_val_loss"] == 6.0 and m["peak_step"] == 100 and abs(m["peak_over_chance"] - 6 / math.log(97)) < 1e-12
    assert (m["norm_start"], m["norm_max"], m["norm_max_step"], m["norm_at_val99"], m["norm_end"]) == \
        (27.0, 30.0, 100, 20.0, 19.0), m
    assert m["best_val_acc"] == 1.0
    never = arithmetic.milestones(rows[:3], 97)
    assert never["val99"] is None and never["ratio"] is None and never["norm_at_val99"] is None
