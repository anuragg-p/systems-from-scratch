"""12.03 Instructions: a chat template, and a model that answers

Every instance's answer is checked by a computation written apart from data/instructions.py; the
words and the number tasks' instances split into a part to train on and a part held out that share
nothing; the last wording of each task is the held-out one; the template puts each marker on a line of
its own and its parts can be read back. answer_loss against a direct sum of -ln p over the reply's
tokens only (1e-10 in float64); tune trains only what needs a gradient; answers against greedy steps
taken one prompt at a time, stopping at the end marker. With GPT-2's files (python3 -m data.fetch
gpt2; without them the test fails there with "missing:" and that command): each marker's token count,
the prompt's and the reply's tokens joined are the whole example's tokens, and decode gives the text
back. The default run: GPT-2 as it is answers almost nothing right; fine-tuned, over a quarter of the
held-out instances in trained wordings are right, and asked for the smaller of two numbers (never
trained) it mostly gives the larger; the same settings twice give the same bytes.
"""

import json
import os
import re


def read(path):
    with open(path, "rb") as f:
        return f.read()


def _task_rows(T, t):
    """instruct.py's scored rows of the task never trained, (task, prompt, answer), in order."""
    r = T.py(t, ["-c", "import json, sys\nsys.argv = ['instruct']\nimport lab\nfrom experiments import instruct as X\n"
                       "print(json.dumps(X.scored_sets(lab.config(X.CONFIG, []))['task']))"])
    return json.loads(r.out)


def test(t):
    T = t.track
    T.inside(t, __file__)
    T.need(t, "gpt2")
    T.inside(t, __file__, "with_data")
    r = T.experiment(t, "instruct")
    before = {k: T.value(r.out, rf"^2\.(?:.|\n)*?{k} +([\d.]+)") for k in ("trained wordings", "held-out wording",
                                                                          r"\(smaller\)")}
    t.check(max(before.values()) < 0.1, f"GPT-2 as it is should answer almost nothing right: {before}")
    s = T.summaries(r)
    t.check(len(s) == 2, f"two seeds: {s}")
    seen = sum(x["seen"] for x in s) / len(s)
    t.check(seen > 0.25, f"fine-tuned, held-out instances in trained wordings: over a quarter right, where GPT-2 got "
                         f"none: {[x['seen'] for x in s]}")
    larger = [a == str(max(map(int, re.findall(r"\d+", p)))) for (task, p, _), a in
              zip(_task_rows(T, t), s[0]["answers"]["task"])]
    t.check(sum(larger) > len(larger) / 2, "asked for the smaller number, the tuned model mostly gives the larger")
    t.check(all(len(x["answers"]["seen"]) == 60 for x in s), "60 answers scored in each set")
    tiny = ["steps=3", "seeds=2", "scored=1", "examples=20", "longest=3"]
    a, b = T.experiment(t, "instruct", *tiny), T.experiment(t, "instruct", *tiny)
    for run in ("seed1/log.jsonl", "seed1/summary.json"):
        t.check(read(os.path.join(a.runs, run)) == read(os.path.join(b.runs, run)),
                f"the same settings twice gave two different {run}")


def inside(S):
    import tempfile
    import numpy as np
    import torch
    import lab
    from data import instructions as I
    from experiments.tuning import answer_loss, answers, tune
    from models.gpt import GPT

    words = I.words()
    assert len(words) > 5000 and all(3 <= len(w) <= 6 and w.isalpha() and w.islower() for w in words)
    assert words == sorted(set(words))
    rng = np.random.default_rng(0)
    for task in I.TASKS:
        for part in ("train", "held"):
            for fields, answer in I.instances(task, part, 200, rng):
                if task == "larger":
                    want = str(fields["a"] if fields["a"] > fields["b"] else fields["b"])
                elif task == "smaller":
                    want = str(fields["b"] if fields["a"] > fields["b"] else fields["a"])
                elif task == "sort":
                    d = [fields["x"], fields["y"], fields["z"]]
                    want = " ".join(str(v) for v in [min(d), sum(d) - min(d) - max(d), max(d)])
                elif task == "upper":
                    want = "".join(chr(ord(c) - 32) for c in fields["w"])
                elif task == "reverse":
                    want = "".join(fields["w"][i] for i in range(len(fields["w"]) - 1, -1, -1))
                else:
                    want = str(len([c for c in fields["w"] if c == fields["c"]]))
                assert answer == want, (task, fields, answer, want)
    counts = [a for _, a in I.instances("count", "train", 400, rng)]
    assert 0.2 < counts.count("0") / len(counts) < 0.8, "count: 0 should not be almost always right"
    parts = I._parts()
    for kind, (train, held) in parts.items():
        assert not set(map(str, train)) & set(map(str, held)), f"{kind}: a held-out instance in training"
        assert abs(len(held) / (len(train) + len(held)) - I.HELD) < 0.01
    held_words = set(parts["word"][1])
    for task in ("upper", "reverse", "count"):
        assert all(f["w"] in held_words for f, _ in I.instances(task, "held", 50, rng))
        assert not any(f["w"] in held_words for f, _ in I.instances(task, "train", 50, rng))
    for task, (_, _, ways) in I.TASKS.items():
        assert I.wordings(task, "train") == ways[:-1] and I.wordings(task, "held") == [ways[-1]]
    assert "smaller" not in I.TRAINED and set(I.TRAINED) | {"smaller"} == set(I.TASKS)
    text = I.chat("Which is larger, 12 or 57?") + I.reply("57")
    assert text == "<|user|>\nWhich is larger, 12 or 57?\n<|assistant|>\n57\n<|end|>"
    lines = text.split("\n")
    assert lines[0] == I.USER and lines[2] == I.ASSISTANT and lines[4] == I.END
    assert lines[1] == "Which is larger, 12 or 57?" and lines[3] == "57"
    assert all(ord(c) < 128 for c in I.USER + I.ASSISTANT + I.END)

    torch.manual_seed(0)
    model = GPT(20, 16, layers=2, heads=2, width=8).double()
    ids = torch.tensor([[1, 2, 3, 4, 5, 6, 0, 0], [7, 8, 9, 10, 11, 12, 13, 14]])
    starts, lengths = torch.tensor([3, 5]), torch.tensor([6, 8])
    got = answer_loss(model, ids, starts, lengths)
    with torch.no_grad():
        logp = torch.log_softmax(model(ids), -1)
    terms = [-logp[b, t - 1, ids[b, t]].item() for b in range(2) for t in range(int(starts[b]), int(lengths[b]))]
    assert abs(got.item() - sum(terms) / len(terms)) < 1e-10, (got.item(), sum(terms) / len(terms))

    frozen = {n: p.detach().clone() for n, p in model.named_parameters()}
    for n, p in model.named_parameters():
        p.requires_grad_(n.startswith("blocks.1."))
    examples = [([1, 2, 3], [4, 5]), ([6, 7], [8, 9, 10]), ([11, 12, 13, 14], [15]), ([2, 4], [6, 8])]
    with tempfile.TemporaryDirectory() as d:
        cfg = lab.Config(dict(out=d, name="t", steps=4, batch=2, lr=0.05, weight_decay=0.0, warmup=1, every=2))
        run = lab.Run(cfg, 0)
        tune(model, cfg, run, torch.device("cpu"), examples, 0)
        assert [r["step"] for r in run.rows] == [0, 2, 3]
    for n, p in model.named_parameters():
        assert torch.equal(p, frozen[n]) != n.startswith("blocks.1."), f"tune: {n}"

    model.eval()
    prompts = [[1, 2, 3], [4, 5, 6], [7, 8], [9, 10, 11, 12]]
    with torch.no_grad():
        first = [model(torch.tensor([p]))[0, -1].argmax().item() for p in prompts]
    stop = [first[2]]                                       # the third prompt, alone of its length, stops at once
    drawn = answers(model, prompts, 5, stop, torch.device("cpu"))
    for p, d in zip(prompts, drawn):
        row = list(p)
        want = []
        with torch.no_grad():
            for _ in range(len(d)):
                want.append(model(torch.tensor([row]))[0, -1].argmax().item())
                row.append(want[-1])
        assert d == want, (p, d, want)
    assert drawn[2] == stop and len(drawn[0]) == len(drawn[1]) and all(1 <= len(d) <= 5 for d in drawn)
    for p, d in zip(prompts, drawn):
        assert len(d) == 5 or all(stop[0] in e for q, e in zip(prompts, drawn) if len(q) == len(p)), (p, d)


def with_data(S):
    import numpy as np
    from data import instructions as I
    from tokens import gpt2

    tok = gpt2.load()
    assert [len(tok.encode(m)) for m in (I.USER, I.ASSISTANT, I.END)] == [5, 6, 5]
    rng = np.random.default_rng(3)
    for task in I.TASKS:
        for fields, answer in I.instances(task, "held", 40, rng):
            for way in I.TASKS[task][2]:
                prompt = way.format(**fields)
                whole = I.chat(prompt) + I.reply(answer)
                parts = tok.encode(I.chat(prompt)) + tok.encode(I.reply(answer))
                assert tok.encode(whole) == parts, (task, prompt)
                assert tok.decode(parts) == whole
