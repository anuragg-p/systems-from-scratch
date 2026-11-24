"""06.04 ResNet: the plain network against the residual one

The paper's CIFAR-10 networks have 6n + 2 layers and its numbers of weights (0.27M for 20 layers,
0.85M for 56), the plain and the residual one exactly the same weights; a block's shortcut is the
identity, or every second pixel padded with zero channels where the shape changes (option A); the
short run shows the deeper plain network ending with the higher training error and the residual
one of the same depth far below it; and the recorded long run (20 and 56 layers) has every file,
every pass and the paper's result: every seed of the deeper plain network ends above every seed of
the shallower, and the deeper residual one is not worse. With LEARN_RERUN_LONG=1 the long run is
run again (about 50 minutes on the CPU) and must show it too.
"""

import json
import os

LONG = "experiments/recorded/resnet"


def mean(xs):
    return sum(xs) / len(xs)


def test(t):
    T = t.track
    T.inside(t, __file__)
    check_recorded(t, T, os.path.join(t.root, LONG))
    T.need(t, "cifar10")
    r = T.experiment(t, "resnet")
    errors = {k: [s["train_error"] for s in T.summaries(r, k)] for k in ("plain8", "plain20", "residual8", "residual20")}
    t.check(mean(errors["plain20"]) > mean(errors["plain8"]) + 2,
            f"the short run: 20 plain layers should end with a higher training error than 8: {errors}")
    t.check(mean(errors["residual20"]) < mean(errors["plain20"]) - 4,
            f"the short run: 20 residual layers should train far better than 20 plain ones: {errors}")
    if os.environ.get("LEARN_RERUN_LONG"):
        with open(os.path.join(t.root, LONG, "plain20", "seed0", "config.json")) as f:
            cfg = json.load(f)
        settings = [f"{k}={cfg[k]!r}".replace(" ", "") for k in ("depths", "width", "n_train", "n_test", "epochs", "batch",
                                                                   "lr", "momentum", "weight_decay", "augment", "seeds")]
        again = T.experiment(t, "resnet", *settings, timeout=4 * 3600)
        check_recorded(t, T, again.runs, rerun=True)


def check_recorded(t, T, d, rerun=False):
    """The long run: every network and seed with its config, a log line for every pass and a summary,
    the two curves, and the paper's result in its summaries."""
    where = "the rerun" if rerun else f"the recorded run ({LONG})"
    t.check(os.path.isdir(d), f"no {where}")
    with open(os.path.join(d, "plain20", "seed0", "config.json")) as f:
        cfg = json.load(f)
    shallow, deep = cfg["depths"]
    got = {}
    for kind in ("plain", "residual"):
        t.check(os.path.isfile(os.path.join(d, f"{kind}.svg")), f"{where}: no {kind}.svg")
        for depth in (shallow, deep):
            for seed in range(cfg["seeds"]):
                run = os.path.join(d, f"{kind}{depth}", f"seed{seed}")
                with open(os.path.join(run, "config.json")) as f:
                    c = json.load(f)
                t.check({k: v for k, v in c.items() if k not in ("label", "seed", "out")} ==
                        {k: v for k, v in cfg.items() if k not in ("label", "seed", "out")} and c["seed"] == seed,
                        f"{where}: {run} was run with other settings")
                with open(os.path.join(run, "log.jsonl")) as f:
                    rows = [json.loads(line) for line in f if line.strip()]
                t.check([r["epoch"] for r in rows] == list(range(1, cfg["epochs"] + 1)) and
                        all({"train_loss", "train_error", "test_error"} <= set(r) for r in rows),
                        f"{where}: {run}/log.jsonl should have every pass")
                with open(os.path.join(run, "summary.json")) as f:
                    s = json.load(f)
                t.check(s["layers"] == depth and 0 <= s["train_error"] <= 100, f"{where}: {run}: {s}")
                got.setdefault((kind, depth), []).append(s["train_error"])
    t.check(cfg["seeds"] >= 3 and cfg["n_train"] >= 4000 and cfg["depths"] == [20, 56],
            f"{where}: the long run is the paper's 20 and 56 layers, 3 seeds or more: {cfg}")
    if not rerun:
        t.check(os.path.isfile(os.path.join(d, "output.txt")), f"{where}: no output.txt, what the run printed")
    t.check(min(got["plain", deep]) > max(got["plain", shallow]),
            f"{where}: every seed of the deeper plain network should end above every seed of the shallower: {got}")
    t.check(mean(got["residual", deep]) < mean(got["residual", shallow]) + 1,
            f"{where}: the deeper residual network should not be worse: {got}")
    t.check(max(got["residual", deep]) < min(got["plain", deep]),
            f"{where}: with shortcuts the deep network should train far better than without: {got}")


def inside(S):
    import torch
    from models import resnet as R

    for n, weights in ((1, 75290), (3, 269722), (9, 853018)):
        plain, res = R.resnet(n, residual=False), R.resnet(n)
        assert R.layers(plain) == R.layers(res) == 6 * n + 2
        assert [(k, tuple(p.shape)) for k, p in plain.named_parameters()] == \
            [(k, tuple(p.shape)) for k, p in res.named_parameters()], "the same weights, plain or residual"
        assert sum(p.numel() for p in res.parameters()) == weights, (n, sum(p.numel() for p in res.parameters()))
    torch.manual_seed(0)
    net = R.resnet(3, width=8)
    assert net(torch.zeros(2, 3, 32, 32)).shape == (2, 10)
    w = net.blocks[4].conv2.weight
    assert abs(w.std().item() - (2 / w[0].numel()) ** 0.5) < 0.1 * (2 / w[0].numel()) ** 0.5, "He's start"
    for (c_in, c_out, stride) in ((4, 4, 1), (4, 8, 2)):
        x = torch.randn(3, c_in, 8, 8)
        for residual in (True, False):
            block = R.Block(c_in, c_out, stride, residual).eval()
            for conv in (block.conv1, block.conv2):
                torch.nn.init.zeros_(conv.weight)
            with torch.no_grad():
                out = block(x)
            if not residual:
                assert (out == 0).all(), "a plain block with no weights gives nothing"
                continue
            want = torch.zeros(3, c_out, 8 // stride, 8 // stride)
            want[:, :c_in] = x[:, :, ::stride, ::stride]
            assert torch.equal(out, torch.relu(want)), f"the shortcut, {c_in} to {c_out} channels, stride {stride}"
    block = R.Block(4, 4, 1, True)
    x = torch.randn(2, 4, 6, 6, requires_grad=True)
    block(x).sum().backward()
    assert x.grad.abs().sum() > 0
