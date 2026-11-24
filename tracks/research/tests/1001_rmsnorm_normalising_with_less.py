"""10.01 RMSNorm: normalising with less

RMSNorm equals torch.nn.RMSNorm and the formula written out (float64), its gradients pass gradcheck, and
it is layer norm's answer whenever a vector's mean is 0; the written-out layer norm equals nn.LayerNorm;
GPT(norm="rms") has an RMSNorm wherever 08's GPT has a layer norm, (2 L + 1) W weights fewer (the norms'
biases), the same names, and equals the same model computed again in float64 numpy (tests/support.py); a
GPT built with the defaults is 08's (the same names, shapes and starting weights as one built with
norm="layer"). compare gives two variants with the same settings the same bits, whatever their turn;
centring reads what each norm reads; uncentred changes only the layer norms, and changes nothing where the
vectors are centred; norm_times times each norm. The short run: RMSNorm's bits within 0.05 of layer
norm's, the layer-norm model's vectors near centred at every norm and its bits unchanged within 0.01
without the mean step; and the same seed gives the same bytes again.
"""

import os


def read(path):
    with open(path, "rb") as f:
        return f.read()


def test(t):
    T = t.track
    T.inside(t, __file__)
    r = T.experiment(t, "rmsnorm")
    a, b = ([s["test_bits"] for s in T.summaries(r, k)] for k in ("layer norm", "RMSNorm"))
    t.check(len(a) == len(b) == 3 and abs(sum(a) / 3 - sum(b) / 3) < 0.05,
            f"RMSNorm should score about as layer norm does: {a} {b}")
    t.check("largest difference from torch.nn.RMSNorm: 0;" in r.out, f"RMSNorm against PyTorch's:\n{r.out[:600]}")
    line = [l for l in r.out.splitlines() if l.strip().startswith("layer norm   ") and "0." in l and "weights" not in l][0]
    shares = [float(v) for v in line.split()[2:]]
    t.check(len(shares) == 9 and max(shares) < 0.2, f"the layer-norm model's norms should read near-centred vectors: {line}")
    trained = T.value(r.out, r"on the test text: (\S+) as trained")
    without = T.value(r.out, r"as trained, (\S+)")
    t.check(abs(trained - without) < 0.01, f"without the mean step the trained model should score about the same: "
                                           f"{trained} {without}")
    tiny = ["seeds=2", "steps=10", "layers=1", "width=16", "context=16", "repeats=2", "big=[2,8,16]"]
    x, y = T.experiment(t, "rmsnorm", *tiny), T.experiment(t, "rmsnorm", *tiny)
    for run in ("layer norm/seed1", "RMSNorm/seed1"):
        for name in ("log.jsonl", "summary.json"):
            t.check(read(os.path.join(x.runs, run, name)) == read(os.path.join(y.runs, run, name)),
                    f"the same seed twice gave two different {run}/{name}")


def inside(S):
    import torch
    from torch import nn
    import lab
    from experiments import rmsnorm
    from experiments.language import compare
    from models.gpt import GPT, RMSNorm

    torch.manual_seed(0)
    x = 3 * torch.randn(4, 7, 12, dtype=torch.float64) + 1
    ours = RMSNorm(12).double()
    assert (ours.weight == 1).all() and ours.eps == 1e-5 and len(list(ours.parameters())) == 1
    with torch.no_grad():
        ours.weight.normal_()
    w = ours.weight.detach().numpy()
    S.same(ours(x), S.rms_norm(x.numpy(), w), "RMSNorm against the formula", tol=1e-12)
    if hasattr(nn, "RMSNorm"):
        theirs = nn.RMSNorm(12, eps=1e-5).double()
        theirs.weight.data.copy_(ours.weight.data)
        S.same(ours(x), theirs(x), "RMSNorm against torch.nn.RMSNorm", tol=1e-12)
    else:
        print("10.01 this torch has no nn.RMSNorm: compared with the formula only")
    assert torch.autograd.gradcheck(ours, (x[:1, :3].clone().requires_grad_(),))
    centred = x - x.mean(-1, keepdim=True)
    layer = nn.LayerNorm(12, elementwise_affine=False).double()
    S.same(RMSNorm(12).double()(centred), layer(centred), "RMSNorm is layer norm on centred vectors", tol=1e-9)
    ln = nn.LayerNorm(12).double()
    with torch.no_grad():
        ln.weight.normal_(), ln.bias.normal_()
    S.same(rmsnorm.written_layer_norm(x, ln.weight, ln.bias), ln(x), "layer norm written out", tol=1e-12)

    V, ctx, L, W = 65, 16, 2, 16
    torch.manual_seed(3)
    base = GPT(V, ctx, layers=L, heads=4, width=W)
    torch.manual_seed(3)
    named = GPT(V, ctx, layers=L, heads=4, width=W, norm="layer")
    assert list(base.state_dict()) == list(named.state_dict()) and all(
        torch.equal(a, b) for a, b in zip(base.state_dict().values(), named.state_dict().values())), \
        "the defaults should build 08's GPT, draw for draw"
    rms = GPT(V, ctx, layers=L, heads=4, width=W, norm="rms").double()
    norms = [rms.norm] + [n for b in rms.blocks for n in (b.norm1, b.norm2)]
    assert all(isinstance(n, RMSNorm) for n in norms) and not any(isinstance(m, nn.LayerNorm) for m in rms.modules())
    assert sum(p.numel() for p in base.parameters()) - sum(p.numel() for p in rms.parameters()) == (2 * L + 1) * W
    assert list(rms.state_dict()) == [k for k in base.state_dict() if not ("norm" in k and k.endswith(".bias"))]
    with torch.no_grad():
        for p in rms.parameters():
            p.add_(0.3 * torch.randn_like(p))
    ids = torch.randint(0, V, (2, ctx))
    S.same(rms(ids), S.gpt10_numpy(rms, ids.numpy(), 4, norm="rms"), "GPT(norm='rms') against numpy", tol=1e-10)
    later = ids.clone()
    later[:, 9:] = (later[:, 9:] + 1) % V
    with torch.no_grad():
        assert torch.equal(rms(ids)[:, :9], rms(later)[:, :9]), "a later character should change nothing before it"

    import tempfile
    from data import shakespeare
    train_t, test_t = (torch.from_numpy(shakespeare.split(s)) for s in ("train", "test"))
    with tempfile.TemporaryDirectory() as d:
        cfg = lab.Config(steps=4, batch=4, context=16, lr=1e-3, warmup=2, weight_decay=0.1, clip=1.0, every=2, seeds=2,
                         out=d, name="t")
        common = dict(vocab=V, context=16, layers=1, heads=2, width=8)
        got = compare({"a": {}, "b": {"norm": "rms"}, "c": {}}, common, cfg, torch.device("cpu"), train_t, test_t[:500])
        assert got["a"]["bits"] == got["c"]["bits"] and got["a"]["bits"] != got["b"]["bits"], got
        assert all(len(r["bits"]) == len(r["ms"]) == len(r["models"]) == 2 for r in got.values())
        assert got["a"]["weights"] - got["b"]["weights"] == 3 * 8 and all(m > 0 for m in got["b"]["ms"])
        assert os.path.isfile(os.path.join(d, "t", "b", "seed1", "summary.json"))

    model = GPT(V, ctx, layers=2, heads=4, width=W).double()
    with torch.no_grad():
        for p in model.parameters():
            p.add_(0.3 * torch.randn_like(p))
    shares = rmsnorm.centring(model, ids)
    e = model.embed(ids)
    want = (e.mean(-1).abs() / e.pow(2).mean(-1).sqrt()).mean().item()
    assert len(shares) == 5 and abs(shares[0] - want) < 1e-12, (shares, want)
    off = rmsnorm.uncentred(model)
    assert not any("forward" in vars(m) for m in model.modules()), "uncentred should leave the model it is given alone"
    with torch.no_grad():
        c = torch.randn(3, W, dtype=torch.float64)
        c = c - c.mean(-1, keepdim=True)
        S.same(off.blocks[0].norm1(c), model.blocks[0].norm1(c), "uncentred on centred vectors", tol=1e-9)
        assert (off(ids) - model(ids)).abs().max() > 1e-6, "uncentred should change the model's scores"
    times = rmsnorm.norm_times({"layer": nn.LayerNorm(8), "rms": RMSNorm(8)}, torch.randn(4, 8), 3, torch.device("cpu"))
    assert set(times) == {"layer", "rms"} and all(v > 0 for v in times.values())
