"""11.02 Where a step goes: profiling

piece_of names the piece of every layer of a GPT (08's and module 10's: learned and rotary positions, layer
norm and RMSNorm, the GELU MLP and SwiGLU); timers' hooks add each layer's time to its piece (checked
with a clock that moves by one at every reading) and come off again; where puts a real profile's
operations under the pieces they ran in (the scores' bmm in attention, rotary's mul and cat in rotary).
Rotary.angles gives the angles 10.02's forward made, bit for bit (bases 10,000 and 100,000, from 1 to 600
places, from place 0 and later ones, float32 and float64); kept, a second call for the same places gives
back the very same tensors, and a call for others makes them again; with Rotary.keep False nothing is
kept; a GPT trained 3 steps with its angles kept has every weight bit for bit as one without. The short
run: the step taken apart (its parts adding up to the step), the profiler's table, the angles' share,
and the weights the same bit for bit.
"""


def test(t):
    T = t.track
    T.inside(t, __file__)
    r = T.experiment(t, "profile")
    t.check("every weight after 3 steps as without, bit for bit: True" in r.out,
            f"keeping the angles should change no weight:\n{r.out[-2000:]}")
    parts = [T.value(r.out, rf"^   {k} +(\S+) ") for k in ("data", "forward", "backward", "clipping", "optimiser")]
    whole = T.value(r.out, r"^   the step +(\S+)")
    t.check(abs(sum(parts) - whole) < 0.02 * whole + 0.05, f"the parts should add up to the step: {parts} {whole}")
    t.check("aten::" in r.out and "Where they ran" in r.out and "BmmBackward0" in r.out,
            f"the profiler's table and where its operations ran:\n{r.out[-3000:]}")
    share = T.value(r.out, r"ms a step, (\S+)% of it; the turning")
    t.check(0 <= share < 50, f"the angles' share of the step: {share}")


def inside(S):
    import collections
    import numpy as np
    import torch
    from torch.profiler import ProfilerActivity, profile
    from experiments import profile as P
    from experiments.sequences import bits
    from models.gpt import GPT, Rotary

    names = {n: P.piece_of(n) for n, _ in GPT(65, 16, layers=2, heads=2, width=8).named_modules()}
    assert names["tokens"] == names["positions"] == "embedding" and names["norm"] == "the last norm"
    assert names["blocks.1.norm1"] == names["blocks.0.norm2"] == "norms" and names["blocks.0"] == "block"
    assert {names[f"blocks.1.attention.{k}"] for k in ("query", "key", "value", "out")} == {"attention: q, k, v and out"}
    assert names["blocks.0.attention"] == "attention" and names["blocks.0.mlp"] == "MLP"
    assert names[""] is None and names["blocks"] is None and names["blocks.0.mlp.up"] is None
    model = GPT(65, 16, layers=2, heads=2, width=8, positions="rotary", norm="rms", mlp="swiglu", kv_heads=1)
    names = {n: P.piece_of(n) for n, _ in model.named_modules()}
    assert names["blocks.0.attention.rotary"] == "attention: rotary" and names["blocks.1.mlp.gate"] is None
    assert names["blocks.0.norm1"] == "norms" and "positions" not in names

    now = [0.0]

    def clock():
        now[0] += 1.0
        return now[0]
    spent = collections.defaultdict(float)
    handles = P.timers(model, clock, spent)
    ids = torch.randint(0, 65, (2, 16))
    model(ids)
    # every timed layer: two readings, one apart, plus one for each reading inside it (its timed children)
    assert spent["MLP"] == 2 and spent["norms"] == 4 and spent["the last norm"] == 1 and spent["embedding"] == 1, spent
    assert spent["attention: rotary"] == 4 and spent["attention: q, k, v and out"] == 8, spent
    assert spent["attention"] == 2 * (1 + 2 * 4 + 2 * 2) and spent["block"] == 2 * (1 + 2 + 14 + 2 + 2), spent
    for h in handles:
        h.remove()
    assert all(not m._forward_hooks and not m._forward_pre_hooks for m in model.modules()), "the hooks come off"

    with profile(activities=[ProfilerActivity.CPU], acc_events=True) as prof:
        handles = P.timers(model, lambda: 0.0, collections.defaultdict(float), labels=True)
        loss = bits(model(ids), ids)
        loss.backward()
    for h in handles:
        h.remove()
    places = P.where(prof.events(), {"attention", "attention: rotary", "MLP"})
    assert "aten::bmm" in places["attention"] and any(k in places["attention"] for k in ("aten::softmax", "aten::_softmax"))
    assert "aten::mul" in places["attention: rotary"] and "aten::cat" in places["attention: rotary"]
    assert "aten::silu" in places["MLP"] and "aten::bmm" not in places["MLP"]

    def old(rot, start, T, dtype):        # 10.02's forward, its angles written as it made them
        theta = 1.0 / rot.base ** (torch.arange(0, rot.d, 2).to(dtype) / rot.d)
        angles = (torch.arange(start, start + T).to(dtype)[:, None] * theta).repeat(1, 2)
        return angles.cos(), angles.sin()
    for base in (10000.0, 100000.0):
        for d in (4, 16, 64):
            rot = Rotary(d, base)
            for dtype in (torch.float32, torch.float64):
                for start, T in ((0, 1), (0, 64), (0, 600), (5, 7), (511, 1), (1000, 300)):
                    got, want = rot.angles(start, T, dtype, torch.device("cpu")), old(rot, start, T, dtype)
                    assert torch.equal(got[0], want[0]) and torch.equal(got[1], want[1]), (base, d, dtype, start, T)
                    x = torch.randn(2, T, d, dtype=dtype)
                    c, s = want
                    h = d // 2
                    assert torch.equal(rot(x, start), x * c + torch.cat([-x[..., h:], x[..., :h]], dim=-1) * s)
    rot = Rotary(16)
    a = rot.angles(0, 64, torch.float32, torch.device("cpu"))
    b = rot.angles(0, 64, torch.float32, torch.device("cpu"))
    assert a[0] is b[0] and a[1] is b[1], "kept: the same tensors back"
    c = rot.angles(1, 64, torch.float32, torch.device("cpu"))
    assert c[0] is not a[0] and not torch.equal(c[0], a[0]), "other places: made again"
    assert rot.angles(1, 64, torch.float64, torch.device("cpu"))[0].dtype == torch.float64
    Rotary.keep = False
    try:
        rot = Rotary(16)
        a, b = (rot.angles(0, 64, torch.float32, torch.device("cpu")) for _ in range(2))
        assert a[0] is not b[0] and torch.equal(a[0], b[0]) and rot.kept is None, "keep False: made every call"
    finally:
        Rotary.keep = True

    weights = {}
    for keep in (False, True):
        Rotary.keep = keep
        torch.manual_seed(0)
        m = GPT(65, 32, layers=2, heads=4, width=16, positions="rotary", norm="rms", mlp="swiglu", kv_heads=2)
        opt = torch.optim.AdamW(m.parameters(), lr=0.01)
        rng = np.random.default_rng(0)
        for _ in range(3):
            x = torch.from_numpy(rng.integers(0, 65, (4, 33)))
            loss = bits(m(x[:, :-1]), x[:, 1:])
            opt.zero_grad()
            loss.backward()
            opt.step()
        weights[keep] = [p.detach().clone() for p in m.parameters()]
    Rotary.keep = True
    assert all(torch.equal(a, b) for a, b in zip(weights[False], weights[True])), "the same weights, bit for bit"
