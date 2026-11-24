"""12.04 What fine-tuning forgot: measuring before and after

at_accuracy reads the bits where a run's accuracy first reaches a level, on the straight line between
two evaluations, on rows written here whose answers are known; weights gives a LoRA-adapted GPT's
weights as GPT's own names, each the frozen weight plus B A, equal to merge's; moved is 0 for an
untouched model and 0.1 for one whose every weight was made 1.1 times larger; text_bits against
window_bits and per_character on a tiny model. The recorded run (12.02's) measured all this as it
trained: the head alone left GPT-2's bits as they were (1.851 on Shakespeare's test text, 09.03) and
its weights unmoved, every other method moved them. With GPT-2's files (python3 -m data.fetch gpt2;
without them the test fails there with "missing:" and that command): the default run prints the
recorded table and runs the instruction model, LoRA and every weight, whose bits on Shakespeare move
from GPT-2's; and the same settings twice give the same bytes.
"""

import json
import os

LONG = "experiments/recorded/lora"


def read(path):
    with open(path, "rb") as f:
        return f.read()


def test(t):
    T = t.track
    T.inside(t, __file__)
    d = os.path.join(t.root, LONG)
    summaries = {}
    for method in sorted(os.listdir(d)):
        if os.path.isdir(os.path.join(d, method)):
            summaries[method] = []
            for seed in sorted(os.listdir(os.path.join(d, method))):
                with open(os.path.join(d, method, seed, "summary.json")) as f:
                    summaries[method].append(json.load(f))
    for s in summaries["head"]:
        t.check(abs(s["shakespeare_bits"] - 1.851) < 0.002 and s["moved"] == 0,
                f"the head alone leaves GPT-2 as it was: {s}")
    for method in ("lora1", "lora8", "full"):
        for s in summaries[method]:
            t.check(s["moved"] > 0 and s["shakespeare_bits"] != summaries["head"][0]["shakespeare_bits"],
                    f"{method}: tuning moved the weights and the bits: {s}")
    T.need(t, "gpt2")
    r = T.experiment(t, "forgetting")
    t.check("head" in r.out and "full" in r.out and "at 0.85" in r.out, f"the recorded table:\n{r.out[:3000]}")
    for method in ("lora", "full"):
        s = T.summaries(r, method)
        t.check(len(s) == 2 and all(x["moved"] > 0 for x in s), f"{method}: two seeds, the weights moved: {s}")
    before = T.value(r.out, r"GPT-2 before: exact match [\d.]+, Shakespeare ([\d.]+)")
    t.check(abs(before - 2.0) < 0.3, f"GPT-2's bits on the first tokens of the test text: {before}")
    tiny = ["steps=2", "seeds=2", "scored=1", "examples=10", "untuned_tokens=200", "stories=1"]
    a, b = T.experiment(t, "forgetting", *tiny), T.experiment(t, "forgetting", *tiny)
    for run in ("lora/seed1/summary.json", "full/seed1/summary.json"):
        t.check(read(os.path.join(a.runs, run)) == read(os.path.join(b.runs, run)),
                f"the same settings twice gave two different {run}")


def inside(S):
    import torch
    from experiments.forgetting import at_accuracy
    from experiments.sequences import per_character, window_bits
    from experiments.tuning import moved, text_bits, weights
    from models.gpt import GPT
    from models.lora import adapt, merge

    rows = [{"valid": 0.1, "untuned_bits": 2.0}, {"valid": 0.5, "untuned_bits": 2.2}, {"valid": 0.9, "untuned_bits": 3.0}]
    assert abs(at_accuracy(rows, 0.7) - 2.6) < 1e-12 and abs(at_accuracy(rows, 0.3) - 2.1) < 1e-12
    assert at_accuracy(rows, 0.95) is None and at_accuracy(rows, 0.05) == 2.0 and at_accuracy(rows, 0.5) == 2.2

    torch.manual_seed(0)
    model = GPT(30, 32, layers=2, heads=2, width=8).double()
    start = {n: w.clone() for n, w in weights(model).items()}
    assert set(start) == set(model.state_dict()) and moved(model, start) == 0
    with torch.no_grad():
        for p in model.parameters():
            p.mul_(1.1)
    assert abs(moved(model, start) - 0.1) < 1e-12

    adapt(model, 2, 4)
    with torch.no_grad():
        for name, p in model.named_parameters():
            if name.endswith(".B"):
                p.normal_()
    got = weights(model)
    assert set(got) == set(start)
    merge(model)
    for name, w in model.state_dict().items():
        S.same(got[name], w, f"weights: {name} as merge makes it", tol=1e-12)

    ids = torch.randint(0, 30, (200,))
    table = {i: b"x" * (1 + i % 3) for i in range(30)}
    want = per_character(window_bits(model, ids, model.context - 8 + 1, 8, batch=4), ids.tolist(), table, 8)
    assert abs(text_bits(model, ids, table, warm=8) - want) < 1e-12 and model.training
