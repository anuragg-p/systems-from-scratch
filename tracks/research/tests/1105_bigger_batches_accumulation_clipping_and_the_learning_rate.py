"""11.05 Bigger batches: accumulation, clipping and the learning rate

accumulated gives the whole batch's gradient from 2, 4, 8 or 32 equal parts, in float64 to 1e-12 of the
largest; train's accumulate setting does the same inside training (the logged bits and the weights of 1
part and of 4 the same to 1e-12 in float64, and bit for bit the same log and weights as no setting at all
with 1 part); a batch that does not cut into equal parts is refused. With dropout the parts draw other
masks: the gradient moves as much as another seed's would. The short run: the gradients equal to 1e-12,
the larger batch fewer steps to the target and the smaller one more tokens' worth fewer (steps and tokens
are not timings: they are the same on any machine), the clip cutting most early steps.
"""

import re


def test(t):
    T = t.track
    T.inside(t, __file__)
    r = T.experiment(t, "batches")
    gaps = [float(g) for g in re.findall(r"\d+ parts (\S+?)[,\n]", r.out)]
    t.check(len(gaps) == 4 and max(gaps) < 1e-12, f"accumulation should give the same gradient: {gaps}\n{r.out[:2500]}")
    steps = {}
    for b in (16, 32, 64):
        s = T.summaries(r, f"batch{b}-held")
        t.check(all(x["steps_to_target"] is not None for x in s), f"batch {b} should reach the target: {s}")
        steps[b] = sum(x["steps_to_target"] for x in s) / len(s)
    t.check(steps[64] < steps[32] < steps[16], f"a larger batch, fewer steps to the target: {steps}")
    t.check(steps[16] * 16 < steps[64] * 64, f"a smaller batch, fewer tokens to the target: {steps}")
    clipped = [int(n) for n in re.findall(r"clipped (\d+) of", r.out)]
    t.check(len(clipped) == 3 and all(n > 0 for n in clipped), f"the clip should cut early steps: {clipped}")


def inside(S):
    import os
    import torch
    import lab
    from data import shakespeare
    from experiments import batches
    from experiments.language import train
    from models.gpt import GPT

    torch.manual_seed(0)
    model = GPT(65, 16, layers=2, heads=4, width=16, positions="rotary", norm="rms", mlp="swiglu", kv_heads=2).double()
    ids = torch.randint(0, 65, (32, 17))
    x, y = ids[:, :-1], ids[:, 1:]
    whole = batches.accumulated(model, x, y, 1)
    size = max(g.abs().max().item() for g in whole)
    for parts in (2, 4, 8, 32):
        for a, b in zip(batches.accumulated(model, x, y, parts), whole):
            assert (a - b).abs().max().item() < 1e-12 * size, parts
    torch.manual_seed(0)
    dropped = GPT(65, 16, layers=2, heads=4, width=16, dropout=0.1).double()
    torch.manual_seed(1)
    one = torch.cat([g.flatten() for g in batches.accumulated(dropped, x, y, 1)])
    torch.manual_seed(1)
    four = torch.cat([g.flatten() for g in batches.accumulated(dropped, x, y, 4)])
    assert (four - one).norm() > 0.01 * one.norm(), "dropout's masks differ in parts"

    cfg = lab.Config(steps=5, batch=16, context=16, lr=0.003, warmup=2, weight_decay=0.1, clip=1.0, every=1,
                     out=os.environ.get("TMPDIR", "/tmp") + "/learn-1105", name="t1105")
    text = torch.from_numpy(shakespeare.split("train"))
    got = {}
    for parts in (None, 1, 4):
        c = lab.Config(cfg) if parts is None else lab.Config({**cfg, "accumulate": parts})
        for kind in ("float32", "float64"):
            torch.manual_seed(0)
            m = GPT(65, 16, layers=1, heads=2, width=16, positions="rotary", norm="rms")
            m = m.double() if kind == "float64" else m
            run = lab.Run(c, 0, label=f"{parts}-{kind}")
            train(m, c, run, torch.device("cpu"), text)
            got[parts, kind] = (run.rows, [p.detach().clone() for p in m.parameters()])
    assert got[None, "float32"][0] == got[1, "float32"][0], "accumulate=1: the same log as no setting"
    assert all(torch.equal(a, b) for a, b in zip(got[None, "float32"][1], got[1, "float32"][1])), "and the same weights"
    (r1, w1), (r4, w4) = got[1, "float64"], got[4, "float64"]
    assert all(abs(a["bits"] - b["bits"]) < 1e-12 for a, b in zip(r1, r4)), (r1, r4)
    assert all((a - b).abs().max().item() < 1e-12 for a, b in zip(w1, w4))
    try:
        train(GPT(65, 16, layers=1, heads=2, width=16), lab.Config({**cfg, "accumulate": 3}), lab.Run(cfg, 0, "bad"),
              torch.device("cpu"), text)
    except ValueError as e:
        assert "does not split into 3 equal parts" in str(e)
    else:
        raise AssertionError("a batch of 16 in 3 parts should be refused")
