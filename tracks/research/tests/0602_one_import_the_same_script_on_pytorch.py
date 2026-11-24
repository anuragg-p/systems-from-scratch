"""06.02 One import: the same script on PyTorch

lab.device picks the device a setting names (auto: cuda, then mps, then the CPU) and lab.clock waits
for it before reading the time; convnet builds the same network, with the same names and shapes, on
either library; from the engine's weights, PyTorch's network takes the same training step to 1e-12
in float64 (the loss, every gradient, every weight after it), and in float32 their losses stay
within 1e-3 over the steps; and the same seed on the same machine gives PyTorch's digits again, run
after run, byte for byte.
"""

import os
import re


def read(path):
    with open(path, "rb") as f:
        return f.read()


def test(t):
    T = t.track
    T.inside(t, __file__)
    a = T.experiment(t, "switch", "steps=3")
    t.check(T.value(a.out, r"the loss: (\S+)") < 1e-12, a.out)
    rows = re.findall(r"^   (\d+\.\w+) +\(.*?\) +(\S+) +(\S+)$", a.out, re.M)
    t.check(len(rows) == 8 and all(float(g) < 1e-12 and float(w) < 1e-12 for _, g, w in rows),
            f"every gradient and weight should be PyTorch's to 1e-12:\n{a.out}")
    t.check(T.value(a.out, r"between the engine's losses and PyTorch's: (\S+)") < 1e-3, a.out)
    # A time, so no claim about which is faster: with other work on the machine three steps of
    # PyTorch have measured slower than the engine's (0.9 times). Only that both were timed.
    t.check(T.value(a.out, r"PyTorch is (\S+) times as fast") > 0.2, f"both should have been timed:\n{a.out}")
    b = T.experiment(t, "switch", "steps=3")
    for run in ("float64/seed0", "float64/seed2", "float32/seed0"):
        for name in ("log.jsonl", "summary.json"):
            t.check(read(os.path.join(a.runs, run, name)) == read(os.path.join(b.runs, run, name)),
                    f"the same seed twice gave two different {run}/{name}")


def inside(S):
    import types
    import numpy as np
    import engine
    import torch
    import lab
    from experiments import switch
    from models.convnet import convnet

    assert lab.device(torch, "cpu") == torch.device("cpu") and lab.device(torch) == torch.device("cpu")
    auto = lab.device(torch, "auto").type
    assert auto == ("cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")
    calls = []

    def fake(cuda, mps):
        return types.SimpleNamespace(
            device=lambda name: types.SimpleNamespace(type=name),
            cuda=types.SimpleNamespace(is_available=lambda: cuda, synchronize=lambda: calls.append("cuda")),
            mps=types.SimpleNamespace(synchronize=lambda: calls.append("mps")),
            backends=types.SimpleNamespace(mps=types.SimpleNamespace(is_available=lambda: mps)))
    for cuda, mps, want in ((True, True, "cuda"), (False, True, "mps"), (False, False, "cpu")):
        got = lab.device(fake(cuda, mps), "auto").type
        assert got == want, f"auto with cuda {cuda} and mps {mps}: {got}, not {want}"
    assert lab.device(fake(True, True), "cpu").type == "cpu", "a device named is the one used"
    for kind in ("cpu", "mps", "cuda"):
        t0 = lab.clock(fake(True, True), types.SimpleNamespace(type=kind))
        assert isinstance(t0, float)
    assert calls == ["mps", "cuda"], f"clock should wait for a GPU, and only for one: {calls}"
    t0 = lab.clock(torch, torch.device("cpu"))
    assert lab.clock(torch, torch.device("cpu")) >= t0

    engine.manual_seed(0)
    ours, theirs = convnet(engine), convnet(torch)
    shapes = [(n, tuple(p.shape)) for n, p in ours.named_parameters()]
    assert shapes == [(n, tuple(p.shape)) for n, p in theirs.named_parameters()], shapes
    assert sum(p.numel() for p in ours.parameters()) == 113738
    assert convnet(engine, 8)(engine.zeros(2, 3, 32, 32)).shape == (2, 10)

    rng = np.random.default_rng(3)
    engine.manual_seed(3)
    ours = convnet(engine, 8).double()
    theirs = switch.copy_weights(ours, convnet(torch, 8).double())
    for k, (p, q) in enumerate(zip(S.params(ours), S.params(theirs))):
        S.same(p, q, f"copied weight {k}", 0)
    oo = engine.optim.SGD(ours.parameters(), lr=0.05, momentum=0.9)
    ot = torch.optim.SGD(theirs.parameters(), lr=0.05, momentum=0.9)
    for i in range(3):
        x, y = rng.standard_normal((16, 3, 32, 32)), rng.integers(0, 10, 16)
        a = switch.step(engine, ours, oo, engine.from_numpy(x), engine.from_numpy(y))
        b = switch.step(torch, theirs, ot, torch.from_numpy(x), torch.from_numpy(y))
        assert isinstance(a, float) and abs(a - b) < 1e-12, (a, b)
        for k, (p, q) in enumerate(zip(ours.parameters(), theirs.parameters())):
            S.same(p.grad, q.grad, f"gradient {k} at step {i}", 1e-10)
            S.same(p, q, f"weight {k} after step {i}", 1e-10)
