"""08.04 Training a GPT on Shakespeare

held_bits is the bits of the held-out windows in eval mode; train logs them every `every` steps when
given; save writes a safetensors file the safetensors library reads, every weight and the config in
its metadata, and load builds the same GPT from it, the same scores; ladder gives module 07's count
models again (6.022, 4.850 and 3.599 bits on the test text); lowest finds the lowest point of the
validation curve. The short run: the GPT ends below the pair model, its validation curve logged,
the checkpoint written and read back with the same scores; and the same seed gives the same bytes
again. The recorded long run (experiments/recorded/gpt) has every file and no weights, and its
result: without dropout every seed's validation curve turns up before the end; dropout gives the
lower validation bits; and every seed of the setting chosen on validation is below module 07's best
(its network and deleted interpolation mixed). With LEARN_RERUN_LONG=1 the long run is run again
(about an hour).
"""

import json
import os

LONG = "experiments/recorded/gpt"


def read(path):
    with open(path, "rb") as f:
        return f.read()


def test(t):
    T = t.track
    T.inside(t, __file__)
    check_recorded(t, os.path.join(t.root, LONG))
    r = T.experiment(t, "gpt")
    for s in T.summaries(r, "dropout0.0"):
        t.check(s["test_bits"] < 3.6, f"the short run's GPT should end below the pair model (3.599): {s}")
    t.check(os.path.isfile(os.path.join(r.runs, "model.safetensors")) and os.path.isfile(os.path.join(r.runs, "curves.svg")),
            f"the short run should leave its checkpoint and its curves in {r.runs}")
    t.check("loaded back, the same scores, number for number: True" in r.out, f"the checkpoint:\n{r.out[-1500:]}")
    with open(os.path.join(r.runs, "dropout0.2", "seed1", "log.jsonl")) as f:
        rows = [json.loads(line) for line in f]
    t.check(all("held_bits" in row for row in rows) and rows[-1]["held_bits"] < rows[0]["held_bits"] - 1,
            f"the validation curve should be logged at every row, and fall: {rows}")
    tiny = ["seeds=2", "steps=12", "layers=1", "width=16", "context=16", "every=4", "held=4", "orders=2", "length=20"]
    a, b = T.experiment(t, "gpt", *tiny), T.experiment(t, "gpt", *tiny)
    for run in ("dropout0.0/seed1", "dropout0.2/seed1"):
        for name in ("log.jsonl", "summary.json"):
            t.check(read(os.path.join(a.runs, run, name)) == read(os.path.join(b.runs, run, name)),
                    f"the same seed twice gave two different {run}/{name}")
    t.check(read(os.path.join(a.runs, "model.safetensors")) == read(os.path.join(b.runs, "model.safetensors")),
            "the same seed twice gave two different checkpoints")
    if os.environ.get("LEARN_RERUN_LONG"):
        with open(os.path.join(t.root, LONG, "dropout0.0", "seed0", "config.json")) as f:
            cfg = json.load(f)
        settings = [f"{k}={cfg[k]!r}".replace(" ", "") for k in ("layers", "heads", "width", "context", "batch", "steps",
                                                                   "lr", "warmup", "weight_decay", "clip", "dropouts",
                                                                   "seeds", "every", "held")]
        again = T.experiment(t, "gpt", *settings, timeout=3 * 3600)
        check_recorded(t, again.runs, rerun=True)


def check_recorded(t, d, rerun=False):
    """The long run: every dropout and seed with its config, a log with the validation curve and a summary;
    the curves; what it printed; no weights; and the result in the summaries."""
    where = "the rerun" if rerun else f"the recorded run ({LONG})"
    t.check(os.path.isdir(d), f"no {where}")
    with open(os.path.join(d, "dropout0.0", "seed0", "config.json")) as f:
        cfg = json.load(f)
    t.check(cfg["seeds"] >= 2 and len(cfg["dropouts"]) >= 2 and cfg["steps"] >= 1500,
            f"{where}: the long run is two settings of dropout or more, 2 seeds or more, 1500 steps or more: {cfg}")
    t.check(os.path.isfile(os.path.join(d, "curves.svg")), f"{where}: no curves.svg")
    if not rerun:
        t.check(os.path.isfile(os.path.join(d, "output.txt")), f"{where}: no output.txt, what the run printed")
        t.check(not os.path.exists(os.path.join(d, "model.safetensors")), f"{where}: no weights are shipped")
    got = {}
    for dropout in cfg["dropouts"]:
        for seed in range(cfg["seeds"]):
            run = os.path.join(d, f"dropout{dropout}", f"seed{seed}")
            with open(os.path.join(run, "config.json")) as f:
                c = json.load(f)
            t.check({k: v for k, v in c.items() if k not in ("label", "seed", "out")} ==
                    {k: v for k, v in cfg.items() if k not in ("label", "seed", "out")} and c["seed"] == seed,
                    f"{where}: {run} was run with other settings")
            with open(os.path.join(run, "log.jsonl")) as f:
                rows = [json.loads(line) for line in f if line.strip()]
            t.check(rows[0]["step"] == 0 and rows[-1]["step"] == cfg["steps"] - 1 and
                    all("held_bits" in row for row in rows), f"{where}: {run}/log.jsonl should have the validation curve")
            with open(os.path.join(run, "summary.json")) as f:
                got.setdefault(dropout, []).append(json.load(f))
    for s in got[0.0]:
        t.check(s["lowest_step"] < cfg["steps"] - 1 and s["end_held_bits"] > s["lowest_held_bits"] + 0.02,
                f"{where}: without dropout the validation curve should turn up before the end: {s}")
    best = min(cfg["dropouts"], key=lambda dr: sum(s["val_bits"] for s in got[dr]))
    t.check(best != 0.0, f"{where}: with dropout the validation bits should be lower than without: {got}")
    bits = [s["test_bits"] for s in got[best]]
    t.check(max(bits) < 2.283, f"{where}: every seed of the GPT (dropout {best}, chosen on validation) should be "
                               f"below module 07's best (2.283, its network and interpolation mixed): {bits}")


def inside(S):
    import math
    import numpy as np
    import torch
    import torch.nn.functional as F
    import lab
    from data import shakespeare
    from experiments import gpt
    from experiments.language import held_bits, load, save, train
    from models.gpt import GPT

    torch.manual_seed(0)
    config = dict(vocab=65, context=12, layers=2, heads=2, width=8, dropout=0.3, bias=True, positions=True)
    model = GPT(**config)
    x, y = torch.randint(0, 65, (5, 12)), torch.randint(0, 65, (5, 12))
    with torch.no_grad():
        want = sum(-math.log2(F.softmax(model.eval()(x)[b, i], 0)[y[b, i]].item()) for b in range(5) for i in range(12))
    model.train()
    assert abs(held_bits(model, x, y) - want / 60) < 1e-5 and model.training, "held_bits: in eval mode, back to training"

    import tempfile
    with tempfile.TemporaryDirectory() as d:
        cfg = lab.Config(steps=7, batch=3, context=12, lr=1e-3, warmup=2, weight_decay=0.1, clip=1.0, every=3,
                         out=d, name="t")
        run = lab.Run(cfg, 0)
        train(model, cfg, run, torch.device("cpu"), torch.randint(0, 65, (500,)), (x, y))
        assert [r["step"] for r in run.rows] == [0, 3, 6] and all("held_bits" in r for r in run.rows)
        path = os.path.join(d, "model.safetensors")
        save(model, config, path, steps=7, val_bits=3.25)
        again, notes = load(path, torch.device("cpu"))
        assert notes["config"] == config and notes["steps"] == 7 and notes["val_bits"] == 3.25 and not again.training
        model.eval()
        with torch.no_grad():
            assert torch.equal(model(x), again(x)), "loaded, the same scores"
        from safetensors import safe_open
        with safe_open(path, "np") as f:
            assert json.loads(f.metadata()["config"]) == config
            assert sorted(f.keys()) == sorted(model.state_dict())
            assert np.array_equal(f.get_tensor("positions.weight"), model.positions.weight.detach().numpy())

    train_ids, val, test = (shakespeare.split(s) for s in ("train", "val", "test"))
    rows = dict(gpt.ladder(train_ids, val, test, 65, 2, [0.1, 0.01]))
    assert abs(rows["every character equally likely"] - math.log2(65)) < 1e-12
    assert round(rows["single characters"], 3) == 4.850 and round(rows["pairs (add-k 0.1)"], 3) == 3.599, rows
    assert gpt.lowest([{"step": 0, "bits": 5}, {"step": 1, "bits": 4, "held_bits": 3.0}, {"step": 2, "bits": 3,
                       "held_bits": 2.5}, {"step": 3, "bits": 2, "held_bits": 2.7}]) == (2, 2.5, 2.7)
