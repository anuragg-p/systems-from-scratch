"""09.01 Bytes, UTF-8 and byte pair encoding

pieces cuts any text into pieces that join back to it; pairs counts neighbours (overlapping ones too)
and merge replaces a pair left to right; train_simple and train learn the same merges as a slow
reference written apart from them (tests/support.py), on Shakespeare and on text from every part of
Unicode, ties broken by the smaller pair; encode gives what applying every merge in the order learned
gives, and of the training text what training made of it; decode(encode(text)) is the text for any
text, in any script, with bytes the training text never had; a list of symbols that cuts a character
gives U+FFFD. unseen and per_character (experiments/sequences.py) against direct counts. The short run: a window of 256
characters holds about 48 words, 15.9% of the test text's different words never occur in training;
the fast trainer gives the obvious one's merges far sooner; bytes per token grow with the vocabulary,
and more on the training text than on the test text; every round trip holds; the GPT on BPE tokens
ends far below the one on characters, in bits per character; and the same seed gives the same bytes
again.
"""

import os


def read(path):
    with open(path, "rb") as f:
        return f.read()


def mean(xs):
    return sum(xs) / len(xs)


def test(t):
    T = t.track
    T.inside(t, __file__)
    r = T.experiment(t, "bpe", "sizes=[256,512,1024]", "vocab=1024", "steps=200")
    words = T.value(r.out, r"holds (\S+) words")
    t.check(40 < words < 55, f"a window of 256 characters should hold about 48 words: {words}")
    t.check("2,396 different words 15.9% never occur in training: 6.9% of its 10,264 running words" in r.out,
            f"the unseen words, counted:\n{r.out[:900]}")
    slow = T.value(r.out, r"every merge: (\S+) s a merge")
    fast = T.value(r.out, r"768 merges in (\S+) s")
    t.check(fast < 768 * slow / 50 and "Its first 3 merges are the obvious way's: True" in r.out,
            f"the fast trainer: the same merges, far sooner: {slow} s a merge, {fast} s for 768:\n{r.out[:1500]}")
    rows = [[float(x) for x in line.replace(",", "").split()]
            for line in r.out.split("3. Bytes per token")[1].split("\n")[2:5]]
    t.check([row[0] for row in rows] == [256, 512, 1024] and rows[0][1:] == [1.0, 1.0] and
            rows[1][1] < rows[2][1] and rows[1][2] < rows[2][2] and rows[2][1] > rows[2][2] + 0.1,
            f"bytes per token should grow with the vocabulary, more on the training text: {rows}")
    t.check("tokens: True" in r.out and r.out.count("back the same: True") == 8,
            f"every round trip should give the text back:\n{r.out}")
    chars, tokens = ([s["test_bits"] for s in T.summaries(r, k)] for k in ("characters", "bpe1024"))
    t.check(max(tokens) < min(chars) - 0.2,
            f"the GPT on BPE tokens should end far below the one on characters, in bits per character: {tokens} {chars}")
    tiny = ["seeds=2", "steps=6", "layers=1", "width=16", "context=16", "every=2", "sizes=[256,300]", "vocab=300",
            "windows=10", "simple_merges=1"]
    a, b = T.experiment(t, "bpe", *tiny), T.experiment(t, "bpe", *tiny)
    for run in ("characters/seed1", "bpe300/seed1"):
        for name in ("log.jsonl", "summary.json"):
            t.check(read(os.path.join(a.runs, run, name)) == read(os.path.join(b.runs, run, name)),
                    f"the same seed twice gave two different {run}/{name}")


def inside(S):
    import numpy as np
    from data import shakespeare
    from experiments import bpe as experiment
    from experiments.sequences import per_character
    from tokens import bpe

    rng = np.random.default_rng(0)
    pool, _ = S.unicode_pool()
    texts = S.unicode_strings(rng, 300, 40, pool)
    for s in texts:
        assert "".join(bpe.pieces(s)) == s, ascii(s)
    assert bpe.pieces("Hello, world!\n\n  hi you're") == ["Hello", ",", " world", "!", "\n\n  ", "hi", " you", "'",
                                                          "re"], bpe.pieces("Hello, world!\n\n  hi you're")

    assert bpe.pairs([1, 1, 1, 2]) == {(1, 1): 2, (1, 2): 1} and bpe.pairs([5]) == {} and bpe.pairs([]) == {}
    assert bpe.merge([1, 1, 1], (1, 1), 9) == [9, 1] and bpe.merge([1, 1, 1, 1], (1, 1), 9) == [9, 9]
    assert bpe.merge([3, 1, 2, 1, 2, 1], (1, 2), 7) == [3, 7, 7, 1] and bpe.merge([], (1, 2), 7) == []
    for _ in range(200):
        ids = rng.integers(0, 3, int(rng.integers(0, 12))).tolist()
        pair = tuple(rng.integers(0, 3, 2).tolist())
        assert tuple(bpe.merge(ids, pair, 5)) == S._merged(tuple(ids), pair, 5), (ids, pair)

    text = shakespeare.load()[:20000]
    want = S.bpe_reference(text, 500)
    assert list(bpe.train_simple(text, 500).items()) == list(want.items()), "train_simple against the reference"
    assert list(bpe.train(text, 500).items()) == list(want.items()), "train against the reference"
    odd = "".join(texts)
    want = S.bpe_reference(odd, 400)
    assert list(bpe.train(odd, 400).items()) == list(want.items()), "train against the reference, any Unicode"
    assert list(bpe.train_simple(odd, 400).items()) == list(want.items())
    assert list(bpe.train("ab cd", 300)) == [(32, 99), (97, 98), (256, 100)], "ties: the smaller pair first"
    assert list(bpe.train("aaaa", 300).items()) == [((97, 97), 256), ((256, 256), 257)]
    assert bpe.train("a", 300) == {} and bpe.train("", 300) == {}

    merges = bpe.train(shakespeare.load()[:200000], 800)
    assert len(merges) == 544 and list(merges.values()) == list(range(256, 800))
    table = bpe.vocab(merges)
    assert len(table) == 800 and all(table[new] == table[a] + table[b] for (a, b), new in merges.items())
    held = shakespeare.load()[200000:206000]
    for s in [held] + texts[:100]:
        ids = bpe.encode(s, merges)
        assert ids == S.bpe_replay(s, merges), ascii(s)
        assert bpe.decode(ids, table) == s, ascii(s)
    assert len(bpe.encode(held, merges)) < len(held) / 2
    for s in ["na\u00efve caf\u00e9", "\u4f60\u597d", "\U0001f44b\U0001f3fd", "e\u0301", "\x00\x7f\x80"]:
        assert bpe.encode(s, merges) == list(s.encode("utf-8")) or bpe.decode(bpe.encode(s, merges), table) == s
        assert bpe.decode(bpe.encode(s, merges), table) == s
    assert bpe.decode([0xE4, 0xBD], table) == "\ufffd" and bpe.decode([104, 0xFF, 105], table) == "h\ufffdi"

    assert experiment.unseen(["a", "b", "a"], ["a", "c", "c", "d"]) == (2 / 3, 3 / 4)
    small = {0: b"ab", 1: b"c", 2: b"def"}
    assert abs(per_character(2.0, [0, 1, 2, 2, 1], small, 2) - 2.0 * 3 / 7) < 1e-12