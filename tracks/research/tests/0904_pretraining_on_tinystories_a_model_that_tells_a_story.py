"""09.04 Pretraining on TinyStories: a model that tells a story

data/tinystories.py, on small files made by the test: stories cut at <|endoftext|> (the training
file's last, cut piece dropped, empty ones left out), merges learned and kept, tokens with END after
each story, kept and read back the same. kgram_hashes against the polynomial written out; shared_run
against a direct search for the longest common run, runs shorter than k not counted; tell gives
generate's tokens up to END, says which ended, and stops once all have. With TinyStories (python3 -m
data.fetch tinystories; without it the rest is skipped, with a line that says so): the real files'
stories and tokens, which decode back to the stories. The recorded long run
(experiments/recorded/tinystories) has every file and no weights, and its result: bits per byte
below the short run's, most stories ending on their own, and its stories sharing runs with the
training text no longer than held-out stories do. The short run: bits per byte, the checkpoint
written, stories told; and the same seed gives the same bytes again. With LEARN_RERUN_LONG=1 the
long run is run again (about an hour).
"""

import json
import os

LONG = "experiments/recorded/tinystories"


def read(path):
    with open(path, "rb") as f:
        return f.read()


def test(t):
    T = t.track
    T.inside(t, __file__)
    check_recorded(t, os.path.join(t.root, LONG))
    if not T.need(t, "tinystories", skip=True):
        return
    T.inside(t, __file__, "with_data")
    r = T.experiment(t, "tinystories", "checkpoint=none")
    for s in T.summaries(r):
        t.check(s["bits_per_byte"] < 2.2, f"the short run's model should learn something: {s}")
    t.check(os.path.isfile(os.path.join(r.runs, "model.safetensors")) and os.path.isfile(os.path.join(r.runs, "curves.svg")),
            f"the short run should leave its checkpoint and curves in {r.runs}")
    told = T.summaries(r, "stories-trained-here")[0]
    t.check(told["samples"] == 8 and len(told["tokens"]) == 8 and len(told["copied"]) == 8, f"stories told: {told}")
    tiny = ["seeds=2", "steps=6", "layers=1", "width=16", "heads=2", "context=16", "every=2", "held=4", "held_stories=20",
            "samples=2", "length=20", "checkpoint=none"]
    a, b = T.experiment(t, "tinystories", *tiny), T.experiment(t, "tinystories", *tiny)
    for run in ("seed1/log.jsonl", "seed1/summary.json", "stories-trained-here/seed0/summary.json"):
        t.check(read(os.path.join(a.runs, run)) == read(os.path.join(b.runs, run)),
                f"the same seed twice gave two different {run}")
    if os.environ.get("LEARN_RERUN_LONG"):
        with open(os.path.join(t.root, LONG, "seed0", "config.json")) as f:
            cfg = json.load(f)
        settings = [f"{k}={cfg[k]!r}".replace(" ", "") for k in ("size", "layers", "heads", "width", "context", "batch",
                                                                   "steps", "lr", "warmup", "weight_decay", "clip",
                                                                   "every", "seeds", "held", "held_stories", "samples",
                                                                   "length", "temperature")]
        again = T.experiment(t, "tinystories", *settings, "checkpoint=none", timeout=3 * 3600)
        check_recorded(t, again.runs, rerun=True)


def check_recorded(t, d, rerun=False):
    """The long run: every seed with its config, its log with the held-out curve, and its summary; the curves; what
    it printed; the stories measured; no weights; and its result."""
    where = "the rerun" if rerun else f"the recorded run ({LONG})"
    t.check(os.path.isdir(d), f"no {where}")
    with open(os.path.join(d, "seed0", "config.json")) as f:
        cfg = json.load(f)
    t.check(cfg["seeds"] >= 2 and cfg["steps"] >= 1000, f"{where}: 2 seeds or more, 1000 steps or more: {cfg}")
    t.check(os.path.isfile(os.path.join(d, "curves.svg")), f"{where}: no curves.svg")
    if not rerun:
        t.check(os.path.isfile(os.path.join(d, "output.txt")), f"{where}: no output.txt, what the run printed")
        t.check(not os.path.exists(os.path.join(d, "model.safetensors")), f"{where}: no weights are shipped")
    bits = []
    for seed in range(cfg["seeds"]):
        run = os.path.join(d, f"seed{seed}")
        with open(os.path.join(run, "config.json")) as f:
            c = json.load(f)
        t.check({k: v for k, v in c.items() if k not in ("label", "seed", "out")} ==
                {k: v for k, v in cfg.items() if k not in ("label", "seed", "out")} and c["seed"] == seed,
                f"{where}: {run} was run with other settings")
        with open(os.path.join(run, "log.jsonl")) as f:
            rows = [json.loads(line) for line in f if line.strip()]
        t.check(rows[0]["step"] == 0 and rows[-1]["step"] == cfg["steps"] - 1 and all("held_bits" in r for r in rows),
                f"{where}: {run}/log.jsonl should have the held-out curve")
        with open(os.path.join(run, "summary.json")) as f:
            bits.append(json.load(f)["bits_per_byte"])
    with open(os.path.join(d, "stories-trained-here", "seed0", "summary.json")) as f:
        told = json.load(f)
    with open(os.path.join(d, "stories-held-out", "seed0", "summary.json")) as f:
        people = json.load(f)["copied"]
    t.check(max(bits) < 1.2, f"{where}: every seed's bits per byte on held-out stories should be below 1.2: {bits}")
    t.check(told["ended"] >= 0.75 * told["samples"], f"{where}: most stories should end on their own: {told}")
    median = sorted(told["copied"])[len(told["copied"]) // 2]
    t.check(median <= 2 * sorted(people)[len(people) // 2],
            f"{where}: the stories should share no longer runs with the training text than held-out ones, much: "
            f"{told['copied']} {people}")


def inside(S):
    import tempfile
    import numpy as np
    import torch
    from data import fetch, tinystories
    from experiments.tinystories import MULTIPLIER, kgram_hashes, shared_run, tell
    from models.gpt import GPT
    from tokens import bpe

    rng = np.random.default_rng(0)
    ids = rng.integers(0, 50, 300)
    h = kgram_hashes(ids, 5)
    for i in (0, 17, 295):
        want = 0
        for x in ids[i:i + 5]:
            want = (want * MULTIPLIER + int(x)) % 2 ** 64
        assert int(h[i]) == want
    assert len(kgram_hashes(ids[:3], 5)) == 0

    def direct(story, ids):
        best = 0
        for i in range(len(story)):
            for j in range(len(ids)):
                n = 0
                while i + n < len(story) and j + n < len(ids) and story[i + n] == ids[j + n]:
                    n += 1
                best = max(best, n)
        return best

    for trial in range(30):
        ids = rng.integers(0, 6, 400)
        story = rng.integers(0, 6, int(rng.integers(5, 40))).tolist()
        if trial % 2:
            a, n = int(rng.integers(0, len(story))), int(rng.integers(3, 15))
            b = int(rng.integers(0, 380))
            story[a:a + n] = ids[b:b + n].tolist()
        hashes = kgram_hashes(ids, 4)
        order = np.argsort(hashes)
        start, n = shared_run(story, ids, (hashes[order], order), 4)
        want = direct(story, ids)
        assert n == (want if want >= 4 else 0), (trial, n, want)
        if n:
            assert any(list(ids[j:j + n]) == story[start:start + n] for j in range(len(ids))), trial

    torch.manual_seed(0)
    model = GPT(12, 16, layers=1, heads=2, width=8).eval()
    with torch.no_grad():
        model.tokens.weight[11] += 0.3                          # 11 is END here: likely enough to be drawn
    prompts = torch.full((5, 1), 11)
    told = tell(model, prompts, 70, torch.Generator().manual_seed(3), 1.0, 11)
    from experiments.language import generate
    drawn = generate(model, prompts, 70, torch.Generator().manual_seed(3)).tolist()
    for (story, ended), row in zip(told, drawn):
        assert ended == (11 in row) and story == (row[:row.index(11)] if ended else row)
    assert sum(e for _, e in told) >= 3

    with tempfile.TemporaryDirectory() as d:
        old, spec = os.environ.get("LEARN_CACHE"), fetch.DATASETS["tinystories"]["files"]
        os.environ["LEARN_CACHE"] = d
        os.makedirs(os.path.join(d, "tinystories"))
        texts = {"train.txt": b"One day, a cat sat.\n<|endoftext|>\n\n<|endoftext|>\nThe dog ran. The dog ran far.\n"
                              b"<|endoftext|>\nA bird sang \xe2\x80\x9chi\xe2\x80\x9d.\n<|endoftext|>\nThe last one is cu",
                 "valid.txt": b"A fish swam.\n<|endoftext|>\nThe cat ran.\n"}
        saved = dict(spec)
        try:
            for name, raw in texts.items():
                with open(os.path.join(d, "tinystories", name), "wb") as f:
                    f.write(raw)
                spec[name] = (len(raw), saved[name][1])
            for f in (tinystories.stories, tinystories.tokenizer, tinystories.tokens):
                f.cache_clear()
            assert tinystories.stories("train") == ["One day, a cat sat.", "The dog ran. The dog ran far.",
                                                    "A bird sang \u201chi\u201d."]
            assert tinystories.stories("valid") == ["A fish swam.", "The cat ran."]
            merges, table = tinystories.tokenizer(270)
            assert len(merges) == 13 and merges == bpe.train("\n".join(tinystories.stories("train")), 269)
            got = tinystories.tokens("train", 270)
            assert got.dtype == np.uint16 and list(got).count(269) == 3 and got[-1] == 269
            back = bpe.decode([int(i) for i in got if i != 269], table)
            assert back == "".join(tinystories.stories("train")), back
            assert os.path.isfile(os.path.join(d, "tinystories", "train-bpe270.npy"))
            assert os.path.isfile(os.path.join(d, "tinystories", "bpe270.json"))
            tinystories.tokens.cache_clear()
            tinystories.tokenizer.cache_clear()
            assert np.array_equal(tinystories.tokens("train", 270), got) and tinystories.tokenizer(270)[0] == merges
        finally:
            spec.update(saved)
            for f in (tinystories.stories, tinystories.tokenizer, tinystories.tokens):
                f.cache_clear()
            if old is None:
                os.environ.pop("LEARN_CACHE", None)
            else:
                os.environ["LEARN_CACHE"] = old


def with_data(S):
    import numpy as np
    from data import tinystories
    from tokens import bpe

    train, valid = tinystories.stories("train"), tinystories.stories("valid")
    assert len(train) == 74394 and len(valid) == 21990, (len(train), len(valid))
    assert train[0].startswith("One day, a little girl named Lily found a needle")
    ids = tinystories.tokens("train", 4096)
    ends = np.flatnonzero(ids == 4095)
    assert len(ends) == len(train) and ids[-1] == 4095
    _, table = tinystories.tokenizer(4096)
    for i in (0, 1, 500, len(train) - 1):
        a = ends[i - 1] + 1 if i else 0
        assert bpe.decode(ids[a:ends[i]].tolist(), table) == train[i], i
    held = tinystories.tokens("valid", 4096)
    assert (held == 4095).sum() == len(valid)
