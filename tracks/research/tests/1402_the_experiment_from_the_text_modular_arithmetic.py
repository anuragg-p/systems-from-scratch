"""14.02 The experiment from the text: modular arithmetic

log_steps gives 0, steps spaced evenly in the logarithm and the last step; score is the accuracy and
the cross-entropy of the guess at c, read at the last of the four tokens a op b =, in eval mode and
back in training mode; train uses AdamW with the paper's betas and weight decay on every weight, the
rate warmed up over the first updates and then constant, batches of half the training set when that
is under the batch size, and logs both splits at log_steps; on a tiny table it learns the training
equations. The short run: every seed has memorised most of the training equations (accuracy over
0.9) while validation accuracy stays near chance (under 0.05), the log holds both splits at every
measured step, the curves are written; and the same seed gives the same bytes again.
"""

import json
import os


def read(path):
    with open(path, "rb") as f:
        return f.read()


def test(t):
    T = t.track
    T.inside(t, __file__)
    r = T.experiment(t, "grokking")
    for s in T.summaries(r):
        t.check(s["train_acc"] > 0.9 and s["val_acc"] < 0.05,
                f"the short run should have memorised most training equations while validation stays at chance: {s}")
    with open(os.path.join(r.runs, "seed0", "log.jsonl")) as f:
        rows = [json.loads(line) for line in f]
    t.check(rows[0]["step"] == 0 and rows[-1]["step"] == 350 and len(rows) > 10 and
            all({"train_acc", "val_acc", "train_loss", "val_loss"} <= set(row) for row in rows),
            f"the log should hold both splits at steps from 0 to 350: {rows[:3]}")
    t.check(rows[-1]["val_loss"] > rows[-1]["train_loss"] + 2,
            f"the validation loss should stay far above the training loss: {rows[-1]}")
    t.check(all(os.path.isfile(os.path.join(r.runs, f)) for f in ("accuracy.svg", "loss.svg")),
            f"the curves should be in {r.runs}")
    tiny = ["seeds=2", "steps=12", "p=7", "fraction=0.5"]
    a, b = T.experiment(t, "grokking", *tiny), T.experiment(t, "grokking", *tiny)
    for name in ("log.jsonl", "summary.json"):
        t.check(read(os.path.join(a.runs, "seed1", name)) == read(os.path.join(b.runs, "seed1", name)),
                f"the same seed twice gave two different seed1/{name}")


def inside(S):
    import math
    import torch
    import torch.nn.functional as F
    import lab
    from data import modular
    from experiments import arithmetic
    from models.gpt import GPT

    at = arithmetic.log_steps(1000, 10)
    assert at[0] == 0 and at[-1] == 1000 and at == sorted(set(at)), at
    assert at[1:5] == [1, 2, 3, 5] and 100 in at and 501 in at and 794 in at, at
    assert all(sum(1 for s in at if 10 ** d <= s < 10 ** (d + 1)) <= 10 for d in range(3)), "per_decade a decade"
    assert arithmetic.log_steps(7, 10) == [0, 1, 2, 3, 5, 6, 7]

    torch.manual_seed(0)
    model = GPT(11, 4, layers=1, heads=2, width=8)
    rows = torch.from_numpy(modular.tokens(modular.equations(7, "+"), 7, "+"))
    right, loss = arithmetic.score(model, rows)
    with torch.no_grad():
        scores = model.eval()(rows[:, :4])[:, -1]
    model.train()
    want = sum(-math.log(F.softmax(scores[i], 0)[rows[i, 4]].item()) for i in range(len(rows))) / len(rows)
    assert abs(loss - want) < 1e-5 and model.training, (loss, want)
    assert right == (scores.argmax(-1) == rows[:, 4]).float().mean().item()

    seen = {}

    class Recorder(torch.optim.AdamW):
        def __init__(self, params, **kw):
            params = list(params)
            seen.update(kw, count=len(params))
            super().__init__(params, **kw)

        def step(self, closure=None):
            seen.setdefault("lrs", []).append(self.param_groups[0]["lr"])
            return super().step(closure)

    import data
    import tempfile
    batches = data.batches

    def counted(n, size, rng):
        seen.setdefault("sizes", set()).add(size)
        return batches(n, size, rng)

    real, torch.optim.AdamW, data.batches = torch.optim.AdamW, Recorder, counted
    with tempfile.TemporaryDirectory() as d:
        train, val = (torch.from_numpy(a) for a in modular.split(7, "+", 0.9, 0))
        cfg = lab.Config(lr=1e-2, betas=[0.9, 0.98], weight_decay=0.1, warmup=10, batch=512, steps=300, per_decade=5,
                         out=d, name="t")
        run = lab.Run(cfg, 0)
        torch.manual_seed(0)
        model = GPT(11, 4, layers=1, heads=2, width=16)
        arithmetic.train(model, cfg, run, torch.device("cpu"), train, val)
    torch.optim.AdamW, data.batches = real, batches
    assert seen["sizes"] == {22}, f"44 training equations, under 512: batches of half of them, {seen['sizes']}"
    assert seen["weight_decay"] == 0.1 and seen["betas"] == (0.9, 0.98) and seen["lr"] == 1e-2
    assert seen["count"] == len(list(model.parameters())), "weight decay on every weight, in one group"
    lrs = seen["lrs"]
    assert len(lrs) == 300 and abs(lrs[0] - 1e-3) < 1e-12 and abs(lrs[9] - 1e-2) < 1e-12 and \
        all(abs(x - 1e-2) < 1e-12 for x in lrs[9:]), "warmed up over 10 updates, then constant"
    assert [r["step"] for r in run.rows] == arithmetic.log_steps(300, 5)
    assert all({"train_acc", "val_acc", "train_loss", "val_loss"} <= set(r) for r in run.rows)
    assert run.rows[-1]["train_acc"] == 1.0, f"a tiny table should be learned: {run.rows[-1]}"
