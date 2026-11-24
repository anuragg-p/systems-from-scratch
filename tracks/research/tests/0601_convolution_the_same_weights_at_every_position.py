"""06.01 Convolution: the same weights at every position

conv2d (any stride and padding, with a bias or none) and max_pool2d give PyTorch's values and
gradients (1e-6, float64), and gradcheck passes on them; Conv2d starts as PyTorch's does and
Flatten flattens as its does; training steps of the convolutional network are PyTorch's. On test
digits moved 2 pixels the convolutional network keeps far more of its accuracy than the fully
connected one (neither holds at 4); a digit moved 4 pixels gives the same maps moved, exactly;
and shuffling every image's pixels costs the convolutional network accuracy and the fully
connected one none to speak of, on either engine.
"""


def test(t):
    T = t.track
    T.need(t, "mnist")
    T.inside(t, __file__)
    ours = T.experiment(t, "conv", "seeds=2")
    check_run(t, T, ours)
    t.check(ours.out.count("largest difference 0\n") == 2,
            f"the moved digit's maps should be the same numbers, moved:\n{ours.out}")
    theirs = T.on_torch(t, "conv", "seeds=1")
    check_run(t, T, theirs, "on PyTorch: ")


def check_run(t, T, r, where=""):
    fc, conv = T.summaries(r, "fc"), T.summaries(r, "conv")
    fcs, convs = T.summaries(r, "fc-shuffled"), T.summaries(r, "conv-shuffled")
    for a, b in zip(fc, conv):
        t.check(a["weights"] == 79510 and b["weights"] == 9098, f"{where}weights: {a} {b}")
        t.check(a["moved0"] > 0.87 and b["moved0"] > 0.92, f"{where}both should learn the digits: {a} {b}")
        t.check(b["moved2"] > a["moved2"] + 0.1, f"{where}moved 2 pixels, the convolutional network should "
                                                 f"keep far more: {a} {b}")
        t.check(a["moved4"] < 0.35 and b["moved4"] < 0.65, f"{where}neither should hold at 4 pixels: {a} {b}")
    mean = lambda rows, key: sum(s[key] for s in rows) / len(rows)
    t.check(abs(mean(fcs, "accuracy") - mean(fc, "moved0")) < 0.05,
            f"{where}shuffled pixels should not matter to the fully connected network: {fc} {fcs}")
    t.check(mean(convs, "accuracy") < mean(conv, "moved0") - 0.06,
            f"{where}shuffled pixels should cost the convolutional network: {conv} {convs}")


def inside(S):
    import numpy as np
    import engine
    import torch
    from engine.autograd import gradcheck
    from experiments import conv

    F = lambda m: m.nn.functional
    for name, fn, shapes in (
            ("conv2d", lambda m, x, w, b: F(m).conv2d(x, w, b), [(2, 3, 7, 6), (4, 3, 3, 2), (4,)]),
            ("conv2d, stride 2, padding 1", lambda m, x, w, b: F(m).conv2d(x, w, b, stride=2, padding=1),
             [(2, 3, 9, 8), (5, 3, 3, 3), (5,)]),
            ("conv2d, stride (2, 1), padding (2, 0)",
             lambda m, x, w, b: F(m).conv2d(x, w, b, stride=(2, 1), padding=(2, 0)), [(3, 2, 8, 7), (4, 2, 5, 3), (4,)]),
            ("conv2d, no bias, 1 by 1, stride 2", lambda m, x, w: F(m).conv2d(x, w, None, stride=2),
             [(2, 4, 6, 6), (3, 4, 1, 1)]),
            ("conv2d, stride 3, pixels left over", lambda m, x, w, b: F(m).conv2d(x, w, b, stride=3, padding=1),
             [(2, 2, 10, 9), (3, 2, 4, 4), (3,)]),
            ("max_pool2d 2", lambda m, x: F(m).max_pool2d(x, 2), [(2, 3, 8, 6)]),
            ("max_pool2d 2, a row and a column left over", lambda m, x: F(m).max_pool2d(x, 2), [(2, 2, 7, 5)]),
            ("max_pool2d 3, stride 2, padding 1", lambda m, x: F(m).max_pool2d(x, 3, 2, 1), [(2, 3, 9, 7)]),
            ("max_pool2d (2, 3), stride 1", lambda m, x: F(m).max_pool2d(x, (2, 3), 1), [(1, 2, 5, 6)]),
            ("convolution, relu, pooling, Flatten",
             lambda m, x, w, b: m.nn.Flatten()(F(m).max_pool2d(F(m).conv2d(x, w, b, padding=1).relu(), 2)),
             [(2, 3, 8, 8), (4, 3, 3, 3), (4,)])):
        S.same_op(fn, shapes, name)
    rng = np.random.default_rng(1)
    x = engine.tensor(rng.standard_normal((2, 2, 6, 5)), requires_grad=True)
    w = engine.tensor(rng.standard_normal((3, 2, 3, 3)), requires_grad=True)
    b = engine.tensor(rng.standard_normal(3), requires_grad=True)
    assert gradcheck(lambda x, w, b: engine.nn.functional.conv2d(x, w, b, stride=2, padding=1), (x, w, b))
    assert gradcheck(lambda x: engine.nn.functional.max_pool2d(x, 2, 1, 1), (x,))

    engine.manual_seed(0)
    layer = engine.nn.Conv2d(3, 64, (3, 5), stride=2, padding=1)
    bound = 1 / np.sqrt(3 * 3 * 5)
    assert layer.weight.shape == (64, 3, 3, 5) and layer.bias.shape == (64,), layer.weight.shape
    for p in (layer.weight, layer.bias):
        assert p.dtype == engine.float32 and np.abs(p.data).max() <= bound and np.abs(p.data).max() > 0.9 * bound
    assert engine.nn.Conv2d(3, 4, 3, bias=False).bias is None
    assert layer(engine.zeros(2, 3, 11, 12)).shape == (2, 64, 6, 5) == tuple(
        torch.nn.Conv2d(3, 64, (3, 5), stride=2, padding=1)(torch.zeros(2, 3, 11, 12)).shape)
    assert engine.nn.MaxPool2d(2)(engine.zeros(2, 3, 7, 6)).shape == (2, 3, 3, 3)
    assert engine.nn.Flatten()(engine.zeros(2, 3, 4, 5)).shape == (2, 60)
    assert engine.nn.Flatten(0, 1)(engine.zeros(2, 3, 4)).shape == (6, 4)

    engine.manual_seed(0)
    ours = conv.convnet().double()
    tn = torch.nn
    theirs = S.copy_weights(ours, tn.Sequential(
        tn.Conv2d(1, 8, 3, padding=1), tn.ReLU(), tn.MaxPool2d(2), tn.Conv2d(8, 16, 3, padding=1), tn.ReLU(),
        tn.MaxPool2d(2), tn.Flatten(), tn.Linear(784, 10)))
    x, y = rng.standard_normal((32, 1, 28, 28)), rng.integers(0, 10, 32)
    oo = engine.optim.SGD(ours.parameters(), lr=0.05, momentum=0.9)
    ot = torch.optim.SGD(theirs.parameters(), lr=0.05, momentum=0.9)
    for step in range(3):
        for model, opt, m in ((ours, oo, engine), (theirs, ot, torch)):
            loss = m.nn.functional.cross_entropy(model(m.tensor(x[step::3])), m.tensor(y[step::3]))
            opt.zero_grad()
            loss.backward()
            opt.step()
        for k, (p, q) in enumerate(zip(S.params(ours), S.params(theirs))):
            S.same(p, q, f"convolutional network: parameter {k} after step {step}")

    dot = np.full((4, 28, 28), -1.0, dtype=np.float32)
    dot[:, 10, 12] = 5.0
    for k in (0, 3):
        out = conv.moved(dot.reshape(4, 784), k, -1.0).reshape(4, 28, 28)
        where = [tuple(int(v) for v in np.argwhere(o == 5.0)[0]) for o in out]
        assert where == [(10 - k, 12), (10 + k, 12), (10, 12 - k), (10, 12 + k)], (k, where)
        assert all((o == -1.0).sum() == 783 for o in out), "one bright pixel each, the rest blank"
    edge = conv.moved(np.zeros((4, 784), dtype=np.float32), 2, 7.0).reshape(4, 28, 28)
    assert (edge[0, 26:] == 7).all() and (edge[1, :2] == 7).all() and (edge[2, :, 26:] == 7).all() \
        and (edge[3, :, :2] == 7).all() and (edge == 7).sum() == 4 * 56, "the fill comes in at the far edge"
