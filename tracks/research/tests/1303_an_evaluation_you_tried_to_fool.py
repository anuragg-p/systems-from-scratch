"""13.03 An evaluation you tried to fool

normal_best against its known values and a count over random draws; hold_back two disjoint halves, the same for
the same seed; shrink the same features for an image and a brighter copy, rows of length 1; two_nearest against a
direct search; exact_copies and the twin rule on a set made here with planted copies and shifted copies, and
none found among strangers; shared_grams against a direct count. Then (with MNIST, CIFAR-10 and TinyStories) the
experiment on short settings: the run chosen by half A of the test images looks better there than on half B,
held back; no exact copies; CIFAR-10's twins between 1% and 8% of its test images, every one the nearest
image's class far more often than the rest; Tiny Shakespeare's split sharing no run of 32 characters, a split of
overlapping windows nearly all; TinyStories' held-out stories found in training; and the same seed gives the
same bytes again.
"""

import os
import re


def read(path):
    with open(path, "rb") as f:
        return f.read()


def test(t):
    T = t.track
    T.inside(t, __file__)
    for name in ("mnist", "cifar10", "tinystories"):
        T.need(t, name)
    r = T.experiment(t, "fooled", "runs=8", "ks=[1,2,4,8]")
    rows = re.findall(r"^ +(\d+)" + r" +([\d.-]+)" * 7 + "$", r.out, re.M)
    t.check([int(row[0]) for row in rows] == [1, 2, 4, 8], f"the table of k:\n{r.out[:2500]}")
    seen, real = float(rows[-1][3]), float(rows[-1][5])
    t.check(seen > 0 and seen > real, f"the best of 8 by A should look better on A than on B: {rows[-1]}")
    t.check(r.out.count(" 0 exact copies") == 2, f"no exact copies in MNIST or CIFAR-10:\n{r.out[-2500:]}")
    twins = T.value(r.out, r"cifar10: .* (\d+) with a twin")
    t.check(100 <= twins <= 800, f"CIFAR-10's twins: {twins}")
    right = re.findall(r"right on ([\d.]+)% of those with a twin, ([\d.]+)% of the rest", r.out)
    t.check(len(right) >= 2 and all(float(a) > float(b) for a, b in right), f"twins are easier: {right}")
    t.check("k = 32: 0.00%" in r.out, f"Tiny Shakespeare's test text shares no run of 32 with training:\n{r.out[-1500:]}")
    t.check(T.value(r.out, r"a tenth of them drawn for testing: ([\d.]+)%") > 80, "overlapping windows share")
    found = T.value(r.out, r"of the [\d,]+ held-out stories, (\d+) are word for word")
    t.check(found >= 10, f"TinyStories' held-out stories found in training: {found}")
    tiny = ["runs=3", "ks=[1,3]", "n_train=300", "hidden=8", "epochs=1"]
    a, b = T.experiment(t, "fooled", *tiny), T.experiment(t, "fooled", *tiny)
    for run in ("runs/seed2/log.jsonl", "runs/seed2/summary.json", "chosen/seed0/summary.json",
                "twins-cifar10/seed0/summary.json"):
        t.check(read(os.path.join(a.runs, run)) == read(os.path.join(b.runs, run)),
                f"the same seed twice gave two different {run}")


def inside(S):
    import math
    import numpy as np
    import lab
    from experiments.fooled import exact_copies, hold_back, shared_grams, shrink, two_nearest

    assert lab.normal_best(1) == 0.0 or abs(lab.normal_best(1)) < 1e-12
    assert abs(lab.normal_best(2) - 1 / math.sqrt(math.pi)) < 1e-9
    assert abs(lab.normal_best(3) - 3 / (2 * math.sqrt(math.pi))) < 1e-9
    draws = np.random.default_rng(0).standard_normal((200000, 10)).max(1)
    assert abs(lab.normal_best(10) - draws.mean()) < 0.01, (lab.normal_best(10), draws.mean())

    a, b = hold_back(101, np.random.default_rng(3))
    assert len(a) == 50 and len(b) == 51 and not set(a) & set(b) and sorted([*a, *b]) == list(range(101))
    a2, _ = hold_back(101, np.random.default_rng(3))
    assert np.array_equal(a, a2) and not np.array_equal(a, hold_back(101, np.random.default_rng(4))[0])

    rng = np.random.default_rng(1)
    x = rng.integers(0, 200, (6, 3, 8, 8)).astype(np.uint8)
    f = shrink(x, 2)
    assert f.shape == (6, 48) and np.allclose(np.linalg.norm(f, axis=1), 1) and np.allclose(f.mean(1), 0, atol=1e-6)
    assert np.allclose(shrink(x.astype(np.float32) * 1.2 + 10, 2), f, atol=1e-6), "a brighter copy, the same features"
    pooled = x.astype(np.float64).reshape(6, 3, 4, 2, 4, 2).mean((3, 5)).reshape(6, -1)
    pooled -= pooled.mean(1, keepdims=True)
    assert np.allclose(f, pooled / np.linalg.norm(pooled, axis=1, keepdims=True), atol=1e-6)

    train = shrink(rng.integers(0, 256, (300, 1, 6, 6)), 1)
    test = shrink(rng.integers(0, 256, (40, 1, 6, 6)), 1)
    nearest, d1, d2 = two_nearest(train, test, chunk=7)
    dist = 1 - test.astype(np.float64) @ train.T.astype(np.float64)
    order = np.argsort(dist, 1)
    assert np.array_equal(nearest, order[:, 0])
    assert np.allclose(d1, dist[np.arange(40), order[:, 0]], atol=1e-6)
    assert np.allclose(d2, dist[np.arange(40), order[:, 1]], atol=1e-6) and (d1 <= d2).all()

    images = rng.integers(0, 256, (500, 1, 16, 16)).astype(np.uint8)
    images = np.repeat(np.repeat(images[:, :, ::4, ::4], 4, 2), 4, 3)              # blocky images, so a shift is small
    planted = images[[5, 17, 300]]
    shifted = np.roll(images[[40, 41, 42, 43]], 1, axis=3)
    strangers = np.repeat(np.repeat(rng.integers(0, 256, (20, 1, 4, 4)).astype(np.uint8), 4, 2), 4, 3)
    tests = np.concatenate([planted, shifted, strangers])
    flat = lambda z: z.reshape(len(z), -1)
    assert exact_copies(flat(images), flat(tests)).tolist() == [True] * 3 + [False] * 24
    nearest, d1, d2 = two_nearest(shrink(images, 4), shrink(tests, 4))
    twin = d1 < 0.5 * d2
    assert twin[:7].all() and not twin[7:].any(), (d1 / d2).round(3)
    assert nearest[:7].tolist() == [5, 17, 300, 40, 41, 42, 43]

    for k in (1, 3, 5):
        tr, te = rng.integers(0, 3, 400), rng.integers(0, 3, 60)
        have = {tuple(tr[i:i + k]) for i in range(len(tr) - k + 1)}
        want = np.mean([tuple(te[i:i + k]) in have for i in range(len(te) - k + 1)])
        assert abs(shared_grams(tr, te, k) - want) < 1e-12, k
