"""12.02 LoRA: training under one percent of the weights

A LoRA layer is its frozen Linear layer plus (alpha / r) x A^T B^T, against that written out (1e-12 in
float64); A starts random with sd 1 / sqrt(inputs), B at 0, so the adapted model's scores are exactly
the model's; adapt makes the query and value layers of every block LoRA layers and freezes the rest:
after a backward only A and B have gradients, and their count is Hu et al.'s 2 x (layers adapted) x
d_model x r; after training, merge gives back GPT's own names and the adapter's scores (1e-10 in
float64). With GPT-2's files and Banking77 (python3 -m data.fetch gpt2 banking77; without them the test
fails there with "missing:" and that command): the counts for GPT-2 small at ranks 1, 4 and 8, its
scores unchanged when adapted. The recorded run (experiments/recorded/lora) has every file, no weights,
and its result: fine-tuning beats the head alone, and each rank of LoRA is far above the head alone and
close to every weight trained (as found: within 2 points). The default prints the counts, the merge,
the times and the recorded table; and a tiny train=True twice gives the same bytes.
"""

import json
import os

LONG = "experiments/recorded/lora"
METHODS = ["head", "lora1", "lora4", "lora8", "full"]


def read(path):
    with open(path, "rb") as f:
        return f.read()


def test(t):
    T = t.track
    T.inside(t, __file__)
    runs = check_recorded(t, os.path.join(t.root, LONG))
    T.need(t, "gpt2")
    T.need(t, "banking77")
    T.inside(t, __file__, "with_data")
    r = T.experiment(t, "lora")
    for n in ("36,864", "147,456", "294,912"):
        t.check(r.out.count(n) >= 2, f"rank counts and the formula should agree ({n}):\n{r.out[:1500]}")
    t.check("GPT-2's own scores, on 8 questions, 0." in r.out, f"adapted, not trained: the same scores:\n{r.out[:2500]}")
    t.check(T.value(r.out, r"the adapter's class scores (\S+),") < 1e-3, f"merged: the same class scores:\n{r.out[:2500]}")
    full, lora = T.value(r.out, r"full +(\d+) ms a step"), T.value(r.out, r"lora8 +(\d+) ms a step")
    t.check(lora < full, f"a LoRA step should be quicker than a full one on this CPU: {lora} {full}")
    for method in runs:
        mean = sum(s["test_accuracy"] for s in runs[method]) / len(runs[method])
        t.check(f"{100 * mean:.0f}" in r.out or f"{mean:.4g}" in r.out,
                f"the default should print the recorded {method}'s accuracy {mean}:\n{r.out[-2500:]}")
    tiny = ["train=True", "methods=['head','lora1','full']", "seeds=2", "steps=3", "batch=4", "every=2", "valid=8",
            "untuned_tokens=100", "stories=1", "ranks=[1]", "demo_steps=1", "timed=1", "standardise_from=10",
            "questions=40", "tested=20", "scored_tokens=200"]
    a, b = T.experiment(t, "lora", *tiny), T.experiment(t, "lora", *tiny)
    for run in ("head/seed1/log.jsonl", "lora1/seed1/log.jsonl", "lora1/seed0/summary.json", "full/seed1/summary.json"):
        t.check(read(os.path.join(a.runs, run)) == read(os.path.join(b.runs, run)),
                f"the same settings twice gave two different {run}")
    if os.environ.get("LEARN_RERUN_LONG"):
        with open(os.path.join(t.root, LONG, "full", "seed0", "config.json")) as f:
            cfg = json.load(f)
        keys = ("alpha", "methods", "seeds", "steps", "batch", "lr", "lora_lr", "head_lr", "weight_decay", "warmup",
                "every", "valid", "standardise_from", "untuned_tokens", "stories")
        again = T.experiment(t, "lora", "train=True", *[f"{k}={cfg[k]!r}".replace(" ", "") for k in keys],
                             timeout=3 * 3600)
        check_recorded(t, again.runs, rerun=True)


def check_recorded(t, d, rerun=False):
    """Every method and seed of the long run, with its config, its log and its summary; no weights; its result."""
    where = "the rerun" if rerun else f"the recorded run ({LONG})"
    t.check(os.path.isdir(d), f"no {where}")
    if not rerun:
        t.check(os.path.isfile(os.path.join(d, "output.txt")), f"{where}: no output.txt, what the run printed")
    runs, first = {}, None
    for method in METHODS:
        seeds = sorted(n for n in os.listdir(os.path.join(d, method)) if n.startswith("seed"))
        t.check(len(seeds) >= 3, f"{where}: {method} should have 3 seeds or more: {seeds}")
        runs[method] = []
        for seed in seeds:
            run = os.path.join(d, method, seed)
            t.check(not os.path.exists(os.path.join(run, "model.safetensors")), f"{where}: no weights are shipped")
            with open(os.path.join(run, "config.json")) as f:
                c = json.load(f)
            same = {k: v for k, v in c.items() if k not in ("label", "seed", "out", "method")}
            first = first or same
            t.check(same == first and c["method"] == method and c["train"] is True,
                    f"{where}: {run} was run with other settings")
            with open(os.path.join(run, "log.jsonl")) as f:
                rows = [json.loads(line) for line in f if line.strip()]
            t.check(rows[0]["step"] == 0 and rows[-1]["step"] == c["steps"] - 1 and
                    all({"valid", "untuned_bits", "moved"} <= set(r) for r in rows), f"{where}: {run}/log.jsonl")
            with open(os.path.join(run, "summary.json")) as f:
                runs[method].append(json.load(f))
    mean = {m: sum(s["test_accuracy"] for s in v) / len(v) for m, v in runs.items()}
    t.check(first["steps"] >= 500, f"{where}: 500 steps or more: {first['steps']}")
    t.check(mean["full"] > mean["head"] + 0.03, f"{where}: fine-tuning the body should beat the head alone: {mean}")
    for m in ("lora1", "lora4", "lora8"):
        t.check(mean[m] > mean["head"] + 0.02 and abs(mean[m] - mean["full"]) < 0.02,
                f"{where}: {m} far above the head alone and within 2 points of every weight: {mean}")
        t.check(runs[m][0]["trained"] < 0.01 * runs[m][0]["total"], f"{where}: {m} trains under 1% of the weights")
    return runs


def inside(S):
    import math
    import torch
    from models.gpt import GPT
    from models.lora import LoRA, adapt, merge, trained

    torch.manual_seed(0)
    linear = torch.nn.Linear(64, 48).double()
    layer = LoRA(linear, 4, 8).double()
    assert layer.A.shape == (4, 64) and layer.B.shape == (48, 4) and layer.scale == 2.0
    assert torch.equal(layer.B, torch.zeros(48, 4)) and abs(layer.A.std().item() - 1 / math.sqrt(64)) < 0.03
    assert not linear.weight.requires_grad and not linear.bias.requires_grad
    x = torch.randn(3, 5, 64, dtype=torch.float64)
    S.same(layer(x), linear(x), "LoRA at the start: the frozen layer exactly", tol=0)
    with torch.no_grad():
        layer.B.normal_()
    S.same(layer(x), x @ linear.weight.T + linear.bias + 2.0 * (x @ layer.A.T) @ layer.B.T, "LoRA: the formula", tol=1e-12)
    S.same(layer.delta(), 2.0 * layer.B @ layer.A, "delta: (alpha / r) B A", tol=1e-12)

    L, W, r = 3, 16, 2
    model = GPT(50, 12, layers=L, heads=2, width=W).double()
    ids = torch.randint(0, 50, (2, 12))
    with torch.no_grad():
        want = model(ids)
    names = set(model.state_dict())
    adapt(model, r, 4)
    with torch.no_grad():
        S.same(model(ids), want, "adapted, not trained: the model's own scores", tol=0)
    assert trained(model) == 2 * (2 * L) * W * r, (trained(model), "Hu et al.'s 2 x L x d_model x r")
    assert {n for n, p in model.named_parameters() if p.requires_grad} == {
        f"blocks.{i}.attention.{k}.{m}" for i in range(L) for k in ("query", "value") for m in ("A", "B")}
    loss = model(ids).square().mean()
    loss.backward()
    have = {n for n, p in model.named_parameters() if p.grad is not None}
    assert have == {n for n, p in model.named_parameters() if p.requires_grad}, have
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=0.05)
    for _ in range(5):
        opt.zero_grad()
        model(ids).square().mean().backward()
        opt.step()
    with torch.no_grad():
        adapted = model(ids)
        assert (adapted - want).abs().max() > 1e-3, "training should change the scores"
        merge(model)
        S.same(model(ids), adapted, "merged: the adapter's scores", tol=1e-10)
    assert set(model.state_dict()) == names, "merged: GPT's own names again"
    assert not any(isinstance(m, LoRA) for m in model.modules())


def with_data(S):
    import torch
    from models import gpt2 as M
    from models.lora import adapt, trained

    body = M.load(torch.device("cpu"))
    ids = torch.randint(0, 50257, (2, 16), generator=torch.Generator().manual_seed(0))
    with torch.no_grad():
        want = body(ids)
    adapt(body, 1, 8)
    assert trained(body) == 36864, trained(body)                # 2 x 24 x 768 x 1
    with torch.no_grad():
        assert torch.equal(body(ids), want), "GPT-2 adapted, not trained: its own scores exactly"
