"""12.01 A new head on a pretrained body

last_states reads each text's vector at its last token, and the padding after it changes nothing (a
text alone gives the same vector, to 1e-12 in float64); a Classifier's scores are its head on that
vector standardised, and change when the last token does, not when padding does; pad, vectors and
accuracy against direct computations; fit trains only what needs a gradient (a frozen body is left
exactly as it was) and logs every `every` steps; words and bag against direct counts;
data/banking77.py on small files written here: the validation part cut by its seed, test.csv whole,
a training question the same as a scored one left out. With GPT-2's files and Banking77 (python3 -m
data.fetch gpt2 banking77; without them the test fails there with "missing:" and that command): the
real parts' sizes and the questions left out; then the default run: the bag of words beats always
guessing the largest class by far, the head on standardised vectors beats the head on the vectors as
they come, the frozen body is below the bag of words at this size (as found), and fewer questions
give lower accuracy; and the same settings twice give the same bytes.
"""

import os


def read(path):
    with open(path, "rb") as f:
        return f.read()


def test(t):
    T = t.track
    T.inside(t, __file__)
    T.need(t, "gpt2")
    T.need(t, "banking77")
    T.inside(t, __file__, "with_data")
    r = T.experiment(t, "classify")
    acc = {label: [s["test_accuracy"] for s in T.summaries(r, label)] for label in ("bag", "small", "frozen-raw", "frozen",
                                                                                     "frozen-100", "frozen-1000")}
    mean = {k: sum(v) / len(v) for k, v in acc.items()}
    t.check(all(len(v) == 3 for v in acc.values()), f"3 seeds of each: {acc}")
    largest = T.value(r.out, r"always guessing it scores ([\d.]+)%") / 100
    t.check(largest < 0.03 and mean["bag"] > 0.7, f"the bag of words far above the largest class: {mean} {largest}")
    t.check(mean["frozen"] > mean["frozen-raw"] + 0.3, f"standardised vectors should be far better than raw: {mean}")
    t.check(mean["frozen"] > 0.65 and mean["small"] > 0.6, f"the frozen body and the small GPT learn the task: {mean}")
    t.check(mean["frozen"] < mean["bag"], f"at 3,000 questions the bag of words is ahead of the frozen body: {mean}")
    t.check(mean["frozen-100"] < mean["frozen-1000"] < mean["frozen"], f"fewer questions, lower accuracy: {mean}")
    t.check("number 496" in r.out and "most numbers vary by about 0.0" in r.out,
            f"the lopsided vectors should be named:\n{r.out[-3000:]}")
    tiny = ["train=300", "test_per_class=1", "seeds=2", "head_steps=20", "small_steps=4", "small_width=16",
            "sizes=[100]"]
    a, b = T.experiment(t, "classify", *tiny), T.experiment(t, "classify", *tiny)
    for run in ("bag/seed1/summary.json", "small/seed1/log.jsonl", "frozen/seed1/log.jsonl",
                "frozen-100/seed0/summary.json"):
        t.check(read(os.path.join(a.runs, run)) == read(os.path.join(b.runs, run)),
                f"the same settings twice gave two different {run}")


def inside(S):
    import tempfile
    import numpy as np
    import torch
    import lab
    from data import banking77, fetch
    from experiments.classify import bag, words
    from experiments.tuning import accuracy, fit, pad, vectors
    from models.classifier import Classifier, last_states
    from models.gpt import GPT

    ids, lengths = pad([[1, 2, 3], [4], [5, 6]], 9, torch.device("cpu"))
    assert ids.tolist() == [[1, 2, 3], [4, 9, 9], [5, 6, 9]] and lengths.tolist() == [3, 1, 2]

    torch.manual_seed(0)
    body = GPT(30, 12, layers=2, heads=2, width=8).double().eval()
    texts = [[3, 4, 5, 6], [7], [8, 9, 10], [11, 12, 13, 14, 15, 16]]
    ids, lengths = pad(texts, 0, torch.device("cpu"))
    with torch.no_grad():
        got = last_states(body, ids, lengths)
        for i, text in enumerate(texts):
            x = body.embed(torch.tensor([text]))
            for block in body.blocks:
                x = block(x)
            S.same(got[i], body.norm(x)[0, -1], f"last_states, text {i}: its vector alone", tol=1e-12)
        other = ids.clone()
        other[1, 1:] = 29                                   # only padding changed
        S.same(last_states(body, other, lengths), got, "last_states: padding changes nothing", tol=0)

    model = Classifier(body, 5).double().eval()
    assert model.head.weight.shape == (5, 8) and model.head.bias.abs().max() == 0
    assert abs(model.head.weight.std().item() - 0.02) < 0.01
    v = torch.randn(20, 8, dtype=torch.float64) * torch.tensor([1, 2, 3, 0.1, 5, 6, 7, 100.0], dtype=torch.float64) + 40
    model.standardise(v)
    S.same(model.center, v.mean(0), "standardise: center")
    S.same(model.spread, v.std(0), "standardise: spread")
    with torch.no_grad():
        S.same(model.scores(v), ((v - v.mean(0)) / v.std(0)) @ model.head.weight.T + model.head.bias,
               "scores: the head on the standardised vector", tol=1e-12)
        S.same(model(ids, lengths), model.scores(got), "forward: scores of last_states", tol=1e-12)
        changed = ids.clone()
        changed[0, 3] = 2                                   # the first text's last token
        diff = (model(changed, lengths) - model(ids, lengths)).abs().sum(-1)
        assert diff[0] > 0 and diff[1:].max() == 0, diff

    with torch.no_grad():
        vs = vectors(model, texts, 0, torch.device("cpu"), batch=3)
        S.same(vs, got, "vectors: in the texts' order", tol=1e-12)
        labels = np.array([0, 1, 2, 3])
        want = float(np.mean(model.scores(got).argmax(-1).numpy() == labels))
    assert accuracy(model, texts, labels, 0, torch.device("cpu")) == want
    assert accuracy(model, got, labels, 0, torch.device("cpu")) == want
    assert model.training, "accuracy puts the model back in training mode"

    frozen_before = {k: p.detach().clone() for k, p in body.named_parameters()}
    for p in body.parameters():
        p.requires_grad_(False)
    head_before = model.head.weight.detach().clone()
    with tempfile.TemporaryDirectory() as d:
        cfg = lab.Config(dict(out=d, name="t", steps=7, batch=2, lr=0.1, head_lr=0.01, weight_decay=0.0, warmup=2,
                              every=3))
        run = lab.Run(cfg, 0)
        fit(model, cfg, run, torch.device("cpu"), texts, labels, 0, measure=lambda m: {"x": 1})
        assert [r["step"] for r in run.rows] == [0, 3, 6] and all(r["x"] == 1 for r in run.rows)
        for k, p in body.named_parameters():
            assert torch.equal(p, frozen_before[k]), f"fit changed the frozen {k}"
        assert not torch.equal(model.head.weight, head_before), "fit should train the head"
        for p in body.parameters():
            p.requires_grad_(True)
        run = lab.Run(cfg, 1)
        fit(model, cfg, run, torch.device("cpu"), got, labels)               # vectors read once: the body is not run
        moved = [k for k, p in body.named_parameters() if not torch.equal(p, frozen_before[k])]
        assert not moved, f"with vectors given, fit should not touch the body: {moved}"
        run = lab.Run(cfg, 2)
        fit(model, cfg, run, torch.device("cpu"), texts, labels, 0)
        assert any(not torch.equal(p, frozen_before[k]) for k, p in body.named_parameters()), "fit trains the body too"

    assert words("Can I top-up 20 GBP? It's late.") == ["can", "i", "top", "up", "20", "gbp", "it's", "late"]
    vocab = {"card": 0, "my": 1, "late": 2}
    assert bag(["My card, my CARD!", "nothing here", "late late late"], vocab).tolist() == [[2, 2, 0], [0, 0, 0], [0, 0, 3]]

    with tempfile.TemporaryDirectory() as d:
        old, spec = os.environ.get("LEARN_CACHE"), fetch.DATASETS["banking77"]["files"]
        saved = dict(spec)
        os.environ["LEARN_CACHE"] = d
        os.makedirs(os.path.join(d, "banking77"))
        rows = [f"Question number {i}?,{['a', 'b', 'c'][i % 3]}" for i in range(30)]
        rows[29] = "the  SAME question,b"
        files = {"categories.json": '["a", "b", "c"]', "train.csv": "text,category\n" + "\n".join(rows) + "\n",
                 "test.csv": 'text,category\n"The same question",b\n"Commas, quoted",c\n'}
        try:
            for name, text in files.items():
                with open(os.path.join(d, "banking77", name), "w") as f:
                    f.write(text)
                spec[name] = (len(text.encode()), saved[name][1])
            for f in (banking77.classes, banking77.split):
                f.cache_clear()
            old_valid, banking77.VALID = banking77.VALID, 5
            assert banking77.classes() == ["a", "b", "c"]
            test_texts, test_labels = banking77.split("test")
            assert test_texts == ["The same question", "Commas, quoted"] and test_labels.tolist() == [1, 2]
            vt, vl = banking77.split("valid")
            tt, tl = banking77.split("train")
            order = np.random.default_rng(banking77.SEED).permutation(30)
            all_texts = [r.split(",")[0] for r in rows]
            label = {r.split(",")[0]: "abc".index(r[-1]) for r in rows}
            assert vt == [all_texts[i] for i in order[:5]] and vl.tolist() == [label[x] for x in vt]
            assert tt == [all_texts[i] for i in order[5:] if i != 29], tt       # the same as a test question: left out
            assert tl.tolist() == [label[x] for x in tt]
            assert banking77.same("  The   same QUESTION ") == "the same question"
        finally:
            banking77.VALID = old_valid
            spec.update(saved)
            for f in (banking77.classes, banking77.split):
                f.cache_clear()
            if old is None:
                os.environ.pop("LEARN_CACHE", None)
            else:
                os.environ["LEARN_CACHE"] = old


def with_data(S):
    import numpy as np
    from data import banking77

    assert len(banking77.classes()) == 77 and banking77.classes()[0] == "card_arrival"
    parts = {name: banking77.split(name) for name in ("train", "valid", "test")}
    assert [len(parts[n][0]) for n in ("train", "valid", "test")] == [8997, 1000, 3080]
    assert np.bincount(parts["test"][1]).tolist() == [40] * 77
    seen = {banking77.same(x) for x in parts["valid"][0] + parts["test"][0]}
    assert not any(banking77.same(x) in seen for x in parts["train"][0])
    assert parts["train"][0][0] and all(0 <= y < 77 for y in parts["train"][1])
