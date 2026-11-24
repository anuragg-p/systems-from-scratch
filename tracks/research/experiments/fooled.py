"""An evaluation you tried to fool: two ways an honest-looking test score is wrong, measured on the track's data.

1. Choosing by the test set. Runs of 13.01's tuned Adam that differ only
   by their seed (a search over a setting that does nothing is the same
   thing), each scored on half of MNIST's test images (A); the best one
   picked by its score there, as a paper that tries many runs and
   reports its best does; then that one scored on the other half (B),
   held back from the start and never looked at to choose. How far the
   winner falls, against the number of runs it was chosen among, beside
   what the runs' own spread predicts (lab's normal_best).
2. Leakage: test examples the training set already holds. Exact copies
   (the same bytes), and twins: a training image far closer to the test
   image than any other training image is (the nearest at under half the
   distance of the second nearest, on the images shrunk, centred and
   scaled to length 1), in MNIST and CIFAR-10; how a classifier that
   remembers (the nearest training image's label) and the runs of part 1
   do on the test images with a twin and on the rest.
3. Leakage in text: of the test text's runs of k characters, how many the
   training text has (Tiny Shakespeare, split by position); what a split
   of overlapping windows at random would share; and TinyStories'
   held-out stories that are word for word in our training stories.

    python3 -m experiments.fooled     (needs MNIST; parts 2 and 3 use CIFAR-10 and TinyStories when fetched)
"""

import numpy as np
import torch

import lab
from data import cifar, fetch, mnist, shakespeare, tinystories
from data.mnist import read_idx
from experiments.images import evaluate, tensors, train_epoch
from experiments.loop import mlp

CONFIG = dict(n_train=10000, hidden=256, epochs=2, batch=128, lr=0.004, runs=32, ks=[1, 2, 4, 8, 16, 32],
              ratio=0.5, pools={"mnist": 1, "cifar10": 4}, n_test=10000, grams=[8, 16, 32], window=256, shown=16,
              device="cpu")


# @build 13.03 hold_back
# Two disjoint halves of n test examples, drawn once from rng (a numpy
# Generator) before anything is run: A, the one choices are made on, and
# B, held back, the one the choice never sees. (MNIST's test images are
# in an order, the first half written by one group of people and the
# second by another, so the halves are drawn at random, not cut.)
def hold_back(n, rng):
    order = rng.permutation(n)
    return np.sort(order[:n // 2]), np.sort(order[n // 2:])
# @end


# @build 13.03 shrink
# Images (n, channels, height, width), as features for finding twins: each
# channel averaged over squares of pool by pool pixels (a small shift or
# crop moves little), then each image's numbers centred on 0 and scaled to
# length 1 (brighter or paler copies come out the same). float32, (n,
# features).
def shrink(x, pool):
    n, c, h, w = x.shape
    x = x.reshape(n, c, h // pool, pool, w // pool, pool).astype(np.float32).mean((3, 5)).reshape(n, -1)
    x = x - x.mean(1, keepdims=True)
    return x / np.maximum(np.linalg.norm(x, axis=1, keepdims=True), 1e-6)
# @end


# @build 13.03 two_nearest
# For each test row (features of length 1, from shrink), its nearest
# training row and the distances to the nearest and the second nearest,
# 1 - their dot product (the cosine distance). The training rows are read
# against `chunk` test rows at a time: a (chunk, n_train) table of dot
# products, its two largest in each row (argpartition). Returns (nearest,
# d1, d2).
def two_nearest(train, test, chunk=500):
    nearest, d1, d2 = (np.empty(len(test), dtype) for dtype in (np.int64, np.float64, np.float64))
    for s in range(0, len(test), chunk):
        sim = test[s:s + chunk] @ train.T
        top = np.argpartition(-sim, 1, axis=1)[:, :2]
        two = np.take_along_axis(sim, top, 1)
        first = two.argmax(1)
        rows = np.arange(len(top))
        nearest[s:s + chunk] = top[rows, first]
        d1[s:s + chunk] = 1 - two[rows, first]
        d2[s:s + chunk] = 1 - two[rows, 1 - first]
    return nearest, d1, d2
# @end


# @build 13.03 exact_copies
# For each test row, whether some training row has exactly its bytes: a
# set of the training rows' bytes, and each test row looked up in it.
def exact_copies(train, test):
    seen = {row.tobytes() for row in train}
    return np.array([row.tobytes() in seen for row in test])
# @end


# @build 13.03 shared_grams
# Of the runs of k symbols of test (a numpy array of integers), the share
# that occur somewhere in train: every run of k of each made one number (a
# polynomial in an odd 64-bit multiplier, wrapping, as 09.04's
# kgram_hashes does: equal runs give equal numbers, different ones almost
# never do), and np.isin.
def shared_grams(train, test, k):
    def hashes(ids):
        ids = ids.astype(np.uint64)
        n = len(ids) - k + 1
        h = np.zeros(n, dtype=np.uint64)
        for j in range(k):
            h = h * np.uint64(0x9E3779B97F4A7C15) + ids[j:j + n]
        return h
    return float(np.isin(hashes(test), hashes(train)).mean())
# @end


def raw(name):
    """A dataset's training and test images as they are stored (uint8, (n, channels, height, width)) and their
    labels."""
    if name == "mnist":
        files = [(read_idx(fetch.path("mnist", i)), read_idx(fetch.path("mnist", l))) for i, l in
                 (mnist.FILES["train"], mnist.FILES["test"])]
        return [(x[:, None], y.astype(np.int64)) for x, y in files]
    out = []
    for split in ("train", "test"):
        parts = [cifar.read_records(fetch.path("cifar10", f)) for f in cifar.FILES[split]]
        out.append((np.concatenate([x for x, _ in parts]), np.concatenate([y for _, y in parts]).astype(np.int64)))
    return out


def choose_by_test(cfg, dev):
    """Part 1: cfg.runs runs, each scored on the halves A and B of the test images; the table of choosing among k."""
    x, y = mnist.load("train", cfg.n_train, False)
    tx, ty = mnist.load("test", None, False)
    a, b = hold_back(len(tx), np.random.default_rng(0))
    train_set = tensors(dev, x, y)
    half_a, half_b = tensors(dev, tx[a], ty[a]), tensors(dev, tx[b], ty[b])
    errors_a, errors_b, wrong = [], [], np.zeros(len(tx))
    whole = tensors(dev, tx, ty)
    for seed in range(cfg.runs):
        run = lab.Run(cfg, seed, label="runs")
        torch.manual_seed(seed)
        model = mlp(torch, [784, cfg.hidden, cfg.hidden, 10]).to(dev)
        opt = torch.optim.Adam(model.parameters(), lr=cfg.lr)
        for epoch in range(cfg.epochs):
            loss, _ = train_epoch(model, opt, *train_set, cfg.batch, run.rng)
            run.log(epoch=epoch + 1, loss=loss)
        model.eval()
        with torch.no_grad():
            wrong += (model(whole[0]).argmax(1) != whole[1]).cpu().numpy()
        ea, eb = 1 - evaluate(model, *half_a)[1], 1 - evaluate(model, *half_b)[1]
        run.finish(error_a=ea, error_b=eb)
        errors_a.append(100 * ea)
        errors_b.append(100 * eb)
    sd_a, shared = lab.sd(errors_a), float(np.cov(errors_a, errors_b)[0, 1])
    luck = max(sd_a ** 2 - shared, 0.0)
    p = lab.mean(errors_a) / 100
    print(f"1. Choosing by the test set: {cfg.runs} runs of 13.01's network and Adam (lr {cfg.lr}, {cfg.epochs} passes "
          f"over {cfg.n_train:,} images),\n   only the seed differs. Test error, %, on half A ({len(a):,} images) and "
          f"half B ({len(b):,}), drawn at random before any run:")
    print(f"   A: {lab.spread(errors_a)}\n   B: {lab.spread(errors_b)}")
    print(f"   Of A's spread over the runs (variance {sd_a ** 2:.4f}), B shares {shared:.4f} (their covariance): the "
          f"runs really differing.\n   The rest, {luck:.4f} (sd {luck ** 0.5:.3f}), is the luck of A's images. (A coin "
          f"for each of {len(a):,} images at {p:.1%} wrong would give sd {100 * (p * (1 - p) / len(a)) ** 0.5:.3f}.)")
    print(f"   The best of k runs by A (expected over every way of picking k of the {cfg.runs}), and that run on B, %; "
          f"the gains\n   are below the average run, and what the spread predicts for them: the normal's best of k "
          f"(normal_best) times\n   A's sd, and of that the luck's share:")
    print(f"   {'k':>4s}{'best on A':>11s}{'it on B':>9s}{'gain on A':>11s}{'predicted':>11s}{'on B':>7s}{'lost':>7s}"
          f"{'predicted':>11s}")
    rows = []
    for k in cfg.ks:
        best_a, its_b = lab.best_of(errors_a, k), lab.best_of(errors_a, k, errors_b)
        seen, real = lab.mean(errors_a) - best_a, lab.mean(errors_b) - its_b
        gain = lab.normal_best(k) * sd_a
        lost = gain * luck / sd_a ** 2 if sd_a > 0 else 0.0
        rows.append(dict(k=k, best_a=best_a, its_b=its_b, seen=seen, real=real, predicted_gain=gain, predicted_lost=lost))
        print(f"   {k:4d}{best_a:11.3f}{its_b:9.3f}{seen:11.3f}{gain:11.3f}{real:7.3f}{seen - real:7.3f}{lost:11.3f}")
    lab.Run(cfg, 0, label="chosen").finish(rows=rows, spread_a=sd_a, shared=shared, luck=luck)
    path = lab.lines(f"{cfg.out}/{cfg.name}/chosen.svg", [
        lab.Line("gain on A, where it was chosen", [r["k"] for r in rows], [r["seen"] for r in rows], 0),
        lab.Line("gain on B, held back", [r["k"] for r in rows], [r["real"] for r in rows], 1),
        lab.Line("A, as the spread predicts", [r["k"] for r in rows], [r["predicted_gain"] for r in rows], 0, 0.6,
                 dashed=True),
        lab.Line("B, as the spread predicts", [r["k"] for r in rows],
                 [r["predicted_gain"] - r["predicted_lost"] for r in rows], 1, 0.6, dashed=True)],
        xlabel="runs chosen among (k)", ylabel="points of error below the average run", logx=True)
    print(f"   curves in {path}")
    return 1 - wrong / cfg.runs


def twins(cfg, name, right_by_runs):
    """Part 2 for one dataset: exact copies, twins, and accuracy on the test images with a twin and without."""
    (x, y), (tx, ty) = raw(name)
    tx, ty = tx[:cfg.n_test], ty[:cfg.n_test]
    right_by_runs = None if right_by_runs is None else right_by_runs[:cfg.n_test]
    copies = exact_copies(x.reshape(len(x), -1), tx.reshape(len(tx), -1))
    nearest, d1, d2 = two_nearest(shrink(x, cfg.pools[name]), shrink(tx, cfg.pools[name]))
    twin = d1 < cfg.ratio * d2
    knn = y[nearest] == ty
    f = twin.mean()
    print(f"\n   {name}: {len(tx):,} test images against {len(x):,} training images: {copies.sum()} exact copies; "
          f"{twin.sum()} with a twin ({f:.2%}; shrunk to squares of {cfg.pools[name]}, the nearest under "
          f"{cfg.ratio} of the second)")
    if twin.any():
        print(f"   the nearest training image's label (a classifier that remembers): right on {knn[twin].mean():.1%} of "
              f"those with a twin, {knn[~twin].mean():.1%} of the rest; overall {knn.mean():.1%}, of which "
              f"{100 * f * (knn[twin].mean() - knn[~twin].mean()):.2f} points are the twins'")
        if right_by_runs is not None:
            print(f"   part 1's runs (they trained on the first {cfg.n_train:,} training images): right on "
                  f"{right_by_runs[twin].mean():.1%} of those with a twin, {right_by_runs[~twin].mean():.1%} of the rest")
    order = np.argsort(d1 / d2)[:cfg.shown]
    lab.Run(cfg, 0, label=f"twins-{name}").finish(
        exact=int(copies.sum()), twins=int(twin.sum()), test=len(tx), nearest_right_twins=float(knn[twin].mean()) if
        twin.any() else None, nearest_right_rest=float(knn[~twin].mean()),
        closest=[[int(t), int(nearest[t]), round(float(d1[t] / d2[t]), 4)] for t in order])


def text(cfg):
    """Part 3: shared runs of characters in Tiny Shakespeare's split, a split of overlapping windows, and
    TinyStories' held-out stories found in training."""
    tr, te = shakespeare.split("train"), shakespeare.split("test")
    print(f"\n3. Leakage in text. Tiny Shakespeare, split by position: of the test text's runs of k characters, the "
          f"share the training text has:\n   " + "   ".join(f"k = {k}: {shared_grams(tr, te, k):.2%}" for k in cfg.grams))
    text_all = np.concatenate([tr, shakespeare.split("val"), te])
    n = len(text_all)
    starts = np.arange(0, n - cfg.window, cfg.window // 2)
    rng = np.random.default_rng(0)
    test_w = rng.random(len(starts)) < 0.1
    covered = np.zeros(n, bool)
    for s in starts[~test_w]:
        covered[s:s + cfg.window] = True
    inside = np.mean([covered[s:s + cfg.window].mean() for s in starts[test_w]])
    print(f"   The same text cut into windows of {cfg.window} every {cfg.window // 2} characters, a tenth of them "
          f"drawn for testing: {inside:.1%} of a test\n   window's characters are in some training window.")
    if fetch.missing("tinystories"):
        print("   TinyStories: not fetched (python3 -m data.fetch tinystories); skipped.")
        return
    train_stories, held = tinystories.stories("train"), tinystories.stories("valid")
    seen = set(train_stories)
    found = [i for i, s in enumerate(held) if s in seen]
    print(f"   TinyStories: of the {len(held):,} held-out stories, {len(found)} are word for word in our "
          f"{len(train_stories):,} training stories\n   ({sum(i < 2000 for i in found)} of the first 2,000, which "
          f"09.04 and 13.04 score on); the training stories themselves hold {len(train_stories) - len(seen)} "
          f"repeats.")
    lab.Run(cfg, 0, label="text").finish(held_in_train=found, train_repeats=len(train_stories) - len(seen),
                                        window_shared=float(inside))


def main():
    cfg = lab.config(CONFIG)
    dev = lab.device(torch, cfg.device)
    start = lab.clock(torch, dev)
    fetch.need("mnist")
    right = choose_by_test(cfg, dev)
    print("\n2. Leakage: test images the training set already holds.")
    for name in ("mnist", "cifar10"):
        if fetch.missing(name):
            print(f"\n   {name}: not fetched (python3 -m data.fetch {name}); skipped.")
            continue
        twins(cfg, name, right if name == "mnist" else None)
    text(cfg)
    print(f"\n{lab.clock(torch, dev) - start:.0f} s of training, searching and counting on {dev.type}")


if __name__ == "__main__":
    main()
