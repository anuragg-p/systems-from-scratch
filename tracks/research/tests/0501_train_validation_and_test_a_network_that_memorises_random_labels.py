"""05.01 Train, validation and test: a network that memorises random labels

The three sets are kept apart and only the training labels are made random; the network gets
every training label right whether the labels are real or random (Zhang et al., figure 1a), the
random ones later; and only validation and test tell the two apart, on either engine.
"""


def test(t):
    T = t.track
    T.need(t, "mnist")
    T.inside(t, __file__)
    ours = T.experiment(t, "random_labels", "seeds=2")
    real, rand = T.summaries(ours, "real-labels"), T.summaries(ours, "random-labels")
    for s in real:
        t.check(s["train_accuracy"] == 1.0 and s["val_accuracy"] > 0.85, f"real labels: {s}")
    for s in rand:
        t.check(s["train_accuracy"] >= 0.97 and s["val_accuracy"] < 0.2 and s["test_accuracy"] < 0.2,
                f"random labels, memorised and nothing learned: {s}")
    when = reached(ours.out)
    t.check(None not in when["real labels"] + when["random labels"], f"a seed never got every label right:\n{ours.out}")
    t.check(min(when["random labels"]) > max(when["real labels"]), f"random labels should take longer: {when}")
    theirs = T.on_torch(t, "random_labels", "seeds=1")
    s = T.summaries(theirs, "random-labels")[0]
    t.check(None not in reached(theirs.out)["random labels"] and s["val_accuracy"] < 0.2,
            f"on PyTorch: {s}\n{theirs.out}")


def reached(out):
    """The epoch at which each seed first got every training label right (None: never), for real and
    random labels. Adam may lose a few of them again afterwards, so the epoch is the claim."""
    when = {}
    for k in ("real labels", "random labels"):
        found = re.search(rf"^{k}: 100% of the training set right at epoch (.*)$", out, re.M).group(1).split(", ")
        when[k] = [None if e == "never" else int(e) for e in found]
    return when


def inside(S):
    import numpy as np
    from experiments.random_labels import split

    (x, y), (xv, yv), (xt, yt) = split(1000, 10000, False, np.random.default_rng(0))
    assert x.shape == (1000, 784) and xv.shape == (10000, 784) and xt.shape == (10000, 784)
    full, labels = __import__("data.mnist", fromlist=["load"]).load("train")
    assert np.array_equal(x, full[:1000]) and np.array_equal(xv, full[-10000:]), "the first n, the last n_val"
    (_, yr), (_, yv2), (_, yt2) = split(1000, 10000, True, np.random.default_rng(0))
    assert np.array_equal(yv2, yv) and np.array_equal(yt2, yt), "validation and test keep their real labels"
    assert 0.8 < np.mean(yr != y) < 0.95 and set(yr.tolist()) == set(range(10)), np.mean(yr != y)


import re  # noqa: E402
