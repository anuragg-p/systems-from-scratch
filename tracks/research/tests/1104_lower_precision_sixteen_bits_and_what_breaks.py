"""11.04 Lower precision: sixteen bits, and what breaks

The float16 facts by direct computation (65,504 and no more, nothing below 2^-24, 1e-8 is 0, 1 + 2^-11
is 1) and bfloat16's (257 is 256); lost against updates worked out by hand (a step under half of
float16's spacing at the weight is lost, one over it is not, weights of 0 are left out). Rotary under
autocast makes its angles in float32 and only then 16 bits (bit for bit the float32 angles, rounded), and
in float32 and float64 exactly as before; under bfloat16 autocast Kinds sees the Linear layers give 16 bits
and the cross-entropy float32. train's precision setting: "float32" gives the same log and weights, bit
for bit, as no setting at all; "bfloat16" and "float16" train, their bits finite and near float32's. The
short run: no update lost at the full rate and some at the late one, eps 0 in float16, the operations by
type, bfloat16 trained within 0.1 bits of float32, and loss scaling losing no more gradients than none.
"""


def test(t):
    T = t.track
    T.inside(t, __file__)
    r = T.experiment(t, "precision")
    full = T.value(r.out, r"rate 0\.003: .*\n +(\S+)% of the updates would change nothing in float16")
    late = T.value(r.out, r"rate 1\.8e-05: .*\n +(\S+)% of the updates would change nothing in float16")
    t.check(full < 1 and late > 5, f"updates lost in float16: at the full rate {full}%, late {late}%")
    t.check("Adam's eps, 1e-8, in float16: 0.0." in r.out, f"eps in float16:\n{r.out[:2500]}")
    t.check(re.search(r"float32 in, 16 bits out: .*linear", r.out) and re.search(r"16 bits in, float32 out: .*cross_entropy",
                                                                                r.out), f"the types:\n{r.out[-3000:]}")
    f32, b16 = ([s["held_bits"] for s in T.summaries(r, k)] for k in ("float32", "bfloat16"))
    t.check(abs(sum(f32) / len(f32) - sum(b16) / len(b16)) < 0.1, f"bfloat16 trained near float32: {f32} {b16}")
    zeros = [float(z) for z in re.findall(r"the loss times +\d+: (\S+)% made 0", r.out)]
    t.check(len(zeros) == 3 and zeros[1] <= zeros[0] and zeros[2] <= zeros[0], f"loss scaling: {zeros}")


import re   # noqa: E402


def inside(S):
    import os
    import numpy as np
    import torch
    import lab
    from data import shakespeare
    from experiments import precision
    from experiments.language import train
    from experiments.sequences import bits
    from models.gpt import GPT, Rotary

    f16 = np.float16
    assert float(f16(65504)) == 65504 and np.isinf(f16(65504) * f16(2)) and np.isinf(f16(65520))
    assert f16(2.0 ** -24) > 0 and f16(2.0 ** -26) == 0 and f16(1e-8) == 0
    assert f16(1) + f16(2.0 ** -11) == f16(1) and f16(1) + f16(2.0 ** -10) > f16(1)
    assert torch.tensor(257.0).bfloat16().item() == 256.0 and torch.tensor(1 + 2.0 ** -9).bfloat16().item() == 1.0

    w = np.array([1.0, 1.0, 0.0, 0.02, 0.02], dtype=np.float32)
    u = np.array([2.0 ** -12, 2.0 ** -9, 1.0, 1e-7, 1e-3], dtype=np.float32)
    assert precision.lost(w, u) == 0.5, precision.lost(w, u)        # 2^-12 at 1 and 1e-7 at 0.02 lost; 0 left out

    cpu = torch.device("cpu")
    rot = Rotary(16)
    for start, T in ((0, 64), (300, 300)):
        c16, s16 = rot.angles(start, T, torch.bfloat16, cpu)
        c32, s32 = rot.angles(start, T, torch.float32, cpu)
        assert c16.dtype == torch.bfloat16 and torch.equal(c16, c32.bfloat16()) and torch.equal(s16, s32.bfloat16())
        theta = 1.0 / 10000.0 ** (torch.arange(0, 16, 2).double() / 16)
        old = (torch.arange(start, start + T).double()[:, None] * theta).repeat(1, 2)
        assert torch.equal(rot.angles(start, T, torch.float64, cpu)[0], old.cos())
    x = torch.randn(2, 40, 16)
    with torch.autocast("cpu", dtype=torch.bfloat16):
        assert rot(x.bfloat16(), 0).dtype == torch.bfloat16

    torch.manual_seed(0)
    model = GPT(65, 16, layers=1, heads=2, width=16, positions="rotary", norm="rms", mlp="swiglu")
    ids = torch.randint(0, 65, (2, 17))
    kinds = precision.Kinds()
    with kinds, torch.autocast("cpu", dtype=torch.bfloat16):
        bits(model(ids[:, :-1]), ids[:, 1:])
    seen = {(f, out) for f, took, out in kinds.seen}
    assert ("linear", "bfloat16") in seen and ("cross_entropy", "float32") in seen and ("embedding", "float32") in seen, seen

    cfg = lab.Config(steps=6, batch=8, context=16, lr=0.003, warmup=2, weight_decay=0.1, clip=1.0, every=2,
                     out=os.environ.get("TMPDIR", "/tmp") + "/learn-1104", name="t1104")
    text = torch.from_numpy(shakespeare.split("train"))
    got = {}
    for kind in (None, "float32", "bfloat16", "float16"):
        c = lab.Config(cfg) if kind is None else lab.Config({**cfg, "precision": kind})
        torch.manual_seed(0)
        m = GPT(65, 16, layers=1, heads=2, width=16, positions="rotary", norm="rms", mlp="swiglu", kv_heads=1)
        run = lab.Run(c, 0, label=str(kind))
        train(m, c, run, cpu, text)
        got[kind] = (run.rows, [p.detach().clone() for p in m.parameters()])
    assert got[None][0] == got["float32"][0], "precision float32: the same log as no setting"
    assert all(torch.equal(a, b) for a, b in zip(got[None][1], got["float32"][1])), "and the same weights"
    for kind in ("bfloat16", "float16"):
        rows = got[kind][0]
        assert all(np.isfinite(r["bits"]) for r in rows) and abs(rows[-1]["bits"] - got[None][0][-1]["bits"]) < 0.2, rows
        assert got[kind][0] != got[None][0], f"{kind} computes other numbers"
