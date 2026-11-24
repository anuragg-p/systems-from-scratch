"""06.03 A convolutional network on CIFAR-10

read_records reads CIFAR-10's records (a label byte, then the red, green and blue pixels, row by
row); load gives standardised images of shape (3, 32, 32); crop_flip crops within its padding and
mirrors about half; train_epoch and evaluate train and score a model on tensors; on CIFAR-10 the
convolutional network beats the fully connected one on test images, and crops and flips narrow
the gap between training and test accuracy; and the same seed on the same machine gives PyTorch's
digits again, run after run, byte for byte.
"""

import os


def read(path):
    with open(path, "rb") as f:
        return f.read()


def test(t):
    T = t.track
    T.inside(t, __file__)
    T.need(t, "cifar10")
    T.inside(t, __file__, "with_data")
    r = T.experiment(t, "cifar", "seeds=2", "epochs=10", "n_test=1000")
    fc, conv, aug = (T.summaries(r, k) for k in ("fc", "conv", "conv-augmented"))
    for f, c, g in zip(fc, conv, aug):
        t.check(c["test_accuracy"] > f["test_accuracy"] + 0.03,
                f"the convolutional network should beat the fully connected one on test images: {f} {c}")
        t.check(f["train_accuracy"] - f["test_accuracy"] > 0.4,
                f"the fully connected network should fit its training images far better than the test: {f}")
        t.check(g["train_accuracy"] - g["test_accuracy"] < (c["train_accuracy"] - c["test_accuracy"]) / 2,
                f"crops and flips should narrow the gap between training and test: {c} {g}")
    tiny = ["seeds=2", "n_train=300", "n_test=200", "epochs=2"]
    a, b = T.experiment(t, "cifar", *tiny), T.experiment(t, "cifar", *tiny)
    for label in ("fc", "conv", "conv-augmented"):
        for name in ("log.jsonl", "summary.json"):
            t.check(read(os.path.join(a.runs, label, "seed1", name)) == read(os.path.join(b.runs, label, "seed1", name)),
                    f"the same seed twice gave two different {label}/seed1/{name}")


def inside(S):
    import tempfile
    import numpy as np
    import torch
    from data import cifar
    from data.augment import crop_flip
    from experiments.images import evaluate, tensors, train_epoch

    rng = np.random.default_rng(0)
    labels = rng.integers(0, 10, 7).astype(np.uint8)
    pixels = rng.integers(0, 256, (7, 3, 32, 32)).astype(np.uint8)
    path = os.path.join(tempfile.mkdtemp(), "records.bin")
    with open(path, "wb") as f:
        for lab, img in zip(labels, pixels):
            f.write(bytes([lab]) + img[0].tobytes() + img[1].tobytes() + img[2].tobytes())
    x, y = cifar.read_records(path)
    assert x.shape == (7, 3, 32, 32) and np.array_equal(x, pixels) and np.array_equal(y, labels)
    with open(path, "ab") as f:
        f.write(b"\0")
    try:
        cifar.read_records(path)
        raise AssertionError("a file that is not whole records should be refused")
    except ValueError:
        pass

    dot = np.zeros((400, 2, 8, 8), dtype=np.float32)
    dot[:, 0, 3, 4], dot[:, 0, 3, 5] = 1.0, 3.0           # a 1 with a 3 to its right
    dot[:, 1, 3, 4] = 2.0
    out = crop_flip(dot, 2, np.random.default_rng(1))
    assert out.shape == dot.shape and out.dtype == np.float32
    flipped = 0
    offsets = set()
    for o in out:
        (r, c), = np.argwhere(o[0] == 1.0)
        assert o[1, r, c] == 2.0 and (o[0] != 0).sum() == 2 and (o[1] != 0).sum() == 1, "the same dots, every channel"
        mirrored = c > 0 and o[0, r, c - 1] == 3.0
        assert mirrored or o[0, r, c + 1] == 3.0
        flipped += mirrored
        dr, dc = r - 3, (7 - c if mirrored else c) - 4
        offsets.add((int(dr), int(dc)))
        assert -2 <= dr <= 2 and -2 <= dc <= 2, (r, c, mirrored)
    assert 150 < flipped < 250 and len(offsets) == 25, (flipped, len(offsets))
    same = crop_flip(np.arange(2 * 3 * 4 * 4, dtype=np.float32).reshape(2, 3, 4, 4), 0, np.random.default_rng(2))
    for o, i in zip(same, np.arange(96, dtype=np.float32).reshape(2, 3, 4, 4)):
        assert np.array_equal(o, i) or np.array_equal(o, i[:, :, ::-1]), "pad 0: the image, or its mirror"

    torch.manual_seed(0)
    model = torch.nn.Sequential(torch.nn.Flatten(), torch.nn.Linear(12, 3))
    xs = rng.standard_normal((90, 3, 2, 2)).astype(np.float32)
    ys = (xs.reshape(90, 12)[:, :3].argmax(1)).astype(np.int64)
    xt, yt = tensors(torch.device("cpu"), xs, ys)
    opt = torch.optim.SGD(model.parameters(), lr=0.5)
    first = evaluate(model, xt, yt, batch_size=7)
    for _ in range(30):
        loss, acc = train_epoch(model, opt, xt, yt, 16, rng)
    last = evaluate(model, xt, yt, batch_size=7)
    assert model.training and last[0] < first[0] / 2 and last[1] > 0.9 and 0 <= acc <= 1, (first, last, acc)
    with torch.no_grad():
        scores = model(xt)
    assert abs(last[0] - torch.nn.functional.cross_entropy(scores, yt).item()) < 1e-5
    assert abs(last[1] - (scores.argmax(1) == yt).sum().item() / 90) < 1e-12


def with_data(S):
    import numpy as np
    from data import cifar

    x, y = cifar.load("test")
    assert x.shape == (10000, 3, 32, 32) and x.dtype == np.float32 and y.dtype == np.int64
    assert np.bincount(y).tolist() == [1000] * 10, np.bincount(y)
    x, y = cifar.load("train", 12000)
    assert x.shape == (12000, 3, 32, 32) and np.bincount(y).min() > 1000
    channel_mean = x.mean(axis=(0, 2, 3))
    channel_sd = x.std(axis=(0, 2, 3))
    assert np.abs(channel_mean).max() < 0.02 and np.abs(channel_sd - 1).max() < 0.02, (channel_mean, channel_sd)
