"""02.05 Modules, parameters, and a checkpoint file

Modules register their weights under PyTorch's names, in PyTorch's order; whole training steps of
a network give PyTorch's losses and weights (1e-6, float64); a seed gives the same starting
weights; state_dict and load_state_dict refuse what does not fit; the safetensors file this
writes is what the safetensors library reads and the other way round; and a network trained on
PyTorch, saved there and loaded here gives the same scores.
"""


def test(t):
    T = t.track
    T.inside(t, __file__)
    ours = T.experiment(t, "checkpoint")
    t.check("after loading: the same scores, number for number: True" in ours.out, ours.out)
    t.check(T.summaries(ours)[0]["accuracy"] >= 0.97, f"the network should learn the two groups:\n{ours.out}")
    theirs = T.on_torch(t, "checkpoint")
    t.check("after loading: the same scores, number for number: True" in theirs.out, f"on PyTorch:\n{theirs.out}")
    check = ("import numpy as np, torch, engine\n"
             "from lab.safetensors import load_file\n"
             "from data.points import two_groups\n"
             "def net(m):\n"
             "    return m.nn.Sequential(m.nn.Linear(2, 16), m.nn.ReLU(), m.nn.Linear(16, 16), m.nn.ReLU(),"
             " m.nn.Linear(16, 2))\n"
             f"state = load_file({theirs.runs + '/seed0/model.safetensors'!r})\n"
             "ours, theirs = net(engine), net(torch)\n"
             "ours.load_state_dict({k: engine.from_numpy(v) for k, v in state.items()})\n"
             "theirs.load_state_dict({k: torch.from_numpy(v) for k, v in state.items()})\n"
             "x, _ = two_groups(100, 0.1, np.random.default_rng(1))\n"
             "a = ours(engine.from_numpy(x)).detach().numpy()\n"
             "b = theirs(torch.from_numpy(x)).detach().numpy()\n"
             "print(float(np.abs(a - b).max()))\n")
    gap = float(T.py(t, ["-c", check]).out)
    t.check(gap < 1e-4, f"PyTorch's checkpoint, loaded here, gives scores {gap} away from PyTorch's")


def inside(S):
    import json
    import os
    import struct
    import tempfile
    import numpy as np
    import engine
    import torch
    import safetensors.numpy as st
    from lab.safetensors import load_file, save_file

    nn = engine.nn
    engine.manual_seed(3)
    a = nn.Linear(3, 2)
    engine.manual_seed(3)
    b = nn.Linear(3, 2)
    assert np.array_equal(a.weight.data, b.weight.data) and np.abs(a.weight.data).max() <= 1 / np.sqrt(3)
    assert a.weight.dtype == engine.float32 and a.weight.requires_grad and isinstance(a.weight, nn.Parameter)
    assert engine.randn(2, 3).shape == (2, 3) and engine.rand(4).dtype == engine.float32

    def build(m):
        return m.nn.Sequential(m.nn.Linear(4, 8), m.nn.ReLU(), m.nn.Linear(8, 8), m.nn.Tanh(), m.nn.Linear(8, 3))
    ours = build(engine).double()
    theirs = S.copy_weights(ours, build(torch))
    assert list(ours.state_dict()) == list(theirs.state_dict()), (list(ours.state_dict()), list(theirs.state_dict()))
    assert [tuple(p.shape) for p in ours.parameters()] == [tuple(p.shape) for p in theirs.parameters()]
    rng = np.random.default_rng(0)
    x, y = rng.standard_normal((16, 4)), rng.integers(0, 3, 16)
    for step in range(5):
        lo = engine.nn.functional.cross_entropy(ours(engine.tensor(x)), engine.tensor(y))
        lt = torch.nn.functional.cross_entropy(theirs(torch.tensor(x)), torch.tensor(y))
        S.same(lo.item(), lt.item(), f"loss at step {step}")
        ours.zero_grad()
        theirs.zero_grad()
        lo.backward()
        lt.backward()
        with engine.no_grad():
            for p in ours.parameters():
                p -= 0.3 * p.grad
        with torch.no_grad():
            for p in theirs.parameters():
                p -= 0.3 * p.grad
        for k, (p, q) in enumerate(zip(S.params(ours), S.params(theirs))):
            S.same(p, q, f"parameter {k} after step {step}")
    assert all(p.grad is not None for p in ours.parameters())
    ours.zero_grad()
    assert all(p.grad is None for p in ours.parameters())
    ours.eval()
    assert not ours.training and not ours[0].training
    ours.train()
    sd = ours.state_dict()
    for broken in ({k: v for k, v in sd.items() if k != "0.bias"}, {**sd, "extra": sd["0.bias"]},
                   {**sd, "0.bias": engine.zeros(5)}):
        try:
            build(engine).load_state_dict(broken)
            raise AssertionError("load_state_dict should refuse a missing, extra or misshapen weight")
        except RuntimeError:
            pass

    d = tempfile.mkdtemp()
    arrays = {"w": np.arange(6, dtype=np.float32).reshape(2, 3), "b": np.array([1.5, -2.0]),
              "steps": np.array(7, dtype=np.int64), "mask": np.array([True, False, True]),
              "empty": np.zeros((0, 4), dtype=np.float32)}
    save_file(arrays, f"{d}/ours.safetensors", metadata={"by": "us"})
    raw = open(f"{d}/ours.safetensors", "rb").read()
    (n,) = struct.unpack("<Q", raw[:8])
    header = json.loads(raw[8:8 + n])
    assert (8 + n) % 8 == 0 and header["__metadata__"] == {"by": "us"} and header["w"]["dtype"] == "F32"
    got = st.load_file(f"{d}/ours.safetensors")
    assert set(got) == set(arrays) and all(np.array_equal(got[k], v) and got[k].dtype == v.dtype
                                           for k, v in arrays.items()), "the safetensors library reads ours"
    st.save_file({k: v for k, v in arrays.items() if k != "mask"}, f"{d}/theirs.safetensors")
    back = load_file(f"{d}/theirs.safetensors")
    assert all(np.array_equal(back[k], arrays[k]) for k in back) and len(back) == 4, "we read theirs"
    back["w"][0, 0] = 99.0
    for name, bad in (("cut short", raw[:-4]), ("header longer than the file", struct.pack("<Q", 10 ** 6) + raw[8:])):
        open(f"{d}/bad.safetensors", "wb").write(bad)
        try:
            load_file(f"{d}/bad.safetensors")
            raise AssertionError(f"load_file should refuse a file {name}")
        except ValueError:
            pass
    sd = {k: v.numpy() for k, v in ours.state_dict().items()}
    save_file(sd, f"{d}/model.safetensors")
    fresh = build(engine).double()
    fresh.load_state_dict({k: engine.from_numpy(v) for k, v in load_file(f"{d}/model.safetensors").items()})
    S.same(fresh(engine.tensor(x)), ours(engine.tensor(x)), "a network loaded from its checkpoint")
    os.remove(f"{d}/bad.safetensors")
