"""07.01 Counting pairs: a bigram model, and the loss to beat

The shipped text is the one pinned in NOTES.md (its size and SHA-256), with 65 characters; encode
and decode undo each other and the three parts, cut by position, are the whole text in order; the
pair table equals a direct count of the pairs; probabilities are the counts' proportions, or with k
added (count + k) / (total + V k), and add up to 1; bits is the mean of -log2 p and infinite at a
zero; a sample follows the table; and the experiment's ladder: every character equally likely is
log2 65 bits, single counts lower, pairs lower still, the unsmoothed pair model infinite on the test
text, Shannon's F2 met by the folded text, and the same seed gives the same bytes again.
"""

import hashlib
import os

SIZE, SHA256 = 1115394, "86c4e6aa9db7c042ec79f339dcb96d42b0075e16b8fc2e86bf0ca57e2dc565ed"


def read(path):
    with open(path, "rb") as f:
        return f.read()


def test(t):
    T = t.track
    data = read(os.path.join(t.root, "data", "tinyshakespeare.txt"))
    t.check(len(data) == SIZE and hashlib.sha256(data).hexdigest() == SHA256,
            f"data/tinyshakespeare.txt is not the pinned file: {len(data)} bytes, {hashlib.sha256(data).hexdigest()}")
    T.inside(t, __file__)
    a = T.experiment(t, "bigram")
    ladder = {name: T.value(a.out, rf"^   {name} +(\S+) \(") for name in
              ("every character equally likely", "single characters, by their counts", "pairs: by the one before")}
    uniform, singles, pairs = ladder.values()
    t.check(abs(uniform - 6.022) < 1e-3, f"equal chances over 65 characters is log2 65 = 6.022 bits:\n{a.out}")
    t.check(4.7 < singles < 5.0 and 3.5 < pairs < 3.7, f"the ladder: singles near 4.85, pairs near 3.6:\n{a.out}")
    t.check("over all 55,769 pairs of the test text: inf bits" in a.out,
            f"the unsmoothed pair model should be infinite on the test text:\n{a.out}")
    t.check(T.value(a.out, r"chosen: k = (\S+)") > 0, a.out)
    folded = T.value(a.out, r"training text folded to 27 symbols +\S+ +\S+ +(\S+)")
    t.check(abs(folded - 3.32) < 0.1,
            f"the text folded to Shannon's 27 symbols should give an F2 near his 3.32:\n{a.out}")
    b = T.experiment(t, "bigram")
    for name in ("log.jsonl", "summary.json"):
        t.check(read(os.path.join(a.runs, "seed0", name)) == read(os.path.join(b.runs, "seed0", name)),
                f"the same seed twice gave two different {name}")


def inside(S):
    import collections
    import math
    import numpy as np
    from data import shakespeare
    from experiments import bigram

    text = shakespeare.load()
    vocab = shakespeare.chars()
    assert len(text) == 1115394 and len(vocab) == 65 and list(vocab) == sorted(set(text)), (len(text), vocab)
    ids = shakespeare.encode(text[:5000])
    assert ids.dtype == np.int64 and shakespeare.decode(ids) == text[:5000]
    assert [vocab[i] for i in ids[:20]] == list(text[:20])
    parts = [shakespeare.split(s) for s in ("train", "val", "test")]
    assert [len(p) for p in parts] == [1003854, 55770, 55770], [len(p) for p in parts]
    assert shakespeare.decode(np.concatenate(parts)) == text, "the three parts are the whole text, in order"

    rng = np.random.default_rng(0)
    small = rng.integers(0, 5, 300)
    table = bigram.pair_counts(small, 5)
    want = collections.Counter(zip(small[:-1].tolist(), small[1:].tolist()))
    assert table.shape == (5, 5) and all(table[a, b] == want[a, b] for a in range(5) for b in range(5))
    train = shakespeare.split("train")
    table = bigram.pair_counts(train, 65)
    pairs = collections.Counter(zip(train[:-1].tolist(), train[1:].tolist()))
    assert table.sum() == len(train) - 1 and all(table[a, b] == n for (a, b), n in pairs.items())

    counts = np.array([[3, 0, 1], [0, 0, 0], [2, 2, 0]])
    p = bigram.probabilities(counts)
    assert np.allclose(p[0], [0.75, 0, 0.25]) and (p[1] == 0).all() and np.allclose(p[2], [0.5, 0.5, 0])
    p = bigram.probabilities(counts, 0.5)
    assert np.allclose(p[0], [3.5 / 5.5, 0.5 / 5.5, 1.5 / 5.5]) and np.allclose(p.sum(axis=1), 1)
    assert np.allclose(bigram.probabilities(np.array([1, 3])), [0.25, 0.75]), "one row of single counts"

    chances = np.array([0.5, 0.25, 0.125])
    assert abs(bigram.bits(chances) - 2.0) < 1e-12 and abs(bigram.bits(np.array([0.3])) + math.log2(0.3)) < 1e-12
    assert bigram.bits(np.array([0.5, 0.0])) == float("inf")

    chain = np.array([[0, 1.0, 0], [0, 0, 1.0], [1.0, 0, 0]])
    assert bigram.sample(chain, 0, 7, np.random.default_rng(1)) == [1, 2, 0, 1, 2, 0, 1]
    probs = bigram.probabilities(table, 0.1)
    one = bigram.sample(probs, 0, 50, np.random.default_rng(3))
    assert one == bigram.sample(probs, 0, 50, np.random.default_rng(3)) and all(0 <= c < 65 for c in one)
