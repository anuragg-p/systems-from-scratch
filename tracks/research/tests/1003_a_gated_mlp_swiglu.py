"""10.03 A gated MLP: SwiGLU

SwiGLU is down(silu(gate(x)) * up(x)), silu being x times its sigmoid, against the formula written out
(float64) and transformers' LlamaMLP on the same weights; it has 3 W h weights (and 2 h + W biases), the
same count as 08's MLP when h = 8 W / 3 is whole and there are no biases (SmolLM2's 576 and 1536);
GPT(mlp="swiglu") has a SwiGLU in every block, inner width 8 W / 3 by default, its down layer started
small as 08's MLP's is, and equals the same model computed again in float64 numpy; gates reads what each
block's gate lets through. The short run: SwiGLU's bits within 0.1 of the GELU MLP's at 150 steps (behind
it there, as measured; ahead by 600: NOTES.md), the weights counted, the gates' shares between 0 and 1;
and the same seed gives the same bytes again.
"""

import os


def read(path):
    with open(path, "rb") as f:
        return f.read()


def mean(xs):
    return sum(xs) / len(xs)


def test(t):
    T = t.track
    T.inside(t, __file__)
    r = T.experiment(t, "swiglu")
    gelu, glu = ([s["test_bits"] for s in T.summaries(r, k)] for k in ("GELU MLP", "SwiGLU"))
    weights = [T.summaries(r, k)[0]["weights"] for k in ("GELU MLP", "SwiGLU")]
    t.check(abs(mean(glu) - mean(gelu)) < 0.1 and mean(glu) < 3.8, f"SwiGLU should score near the GELU MLP: {glu} {gelu}")
    t.check(weights[1] - weights[0] == -176, f"4 blocks of SwiGLU (inner 170) against MLP (inner 256): {weights}")
    t.check("width 576, without biases: MLP (inner 2304) 2,654,208   SwiGLU (inner 1536) 2,654,208   difference +0"
            in r.out, f"the weights at SmolLM2's width:\n{r.out[:900]}")
    shares = [float(v) for line in r.out.splitlines() if line.strip().startswith("block ")
              for v in (line.split("shut ")[1].split(",")[0], line.split("wide open ")[1])]
    t.check(len(shares) == 8 and all(0 <= s <= 1 for s in shares) and shares[0] > 0.05,
            f"the gates' shares, block by block: {shares}")
    tiny = ["seeds=2", "steps=10", "layers=1", "width=16", "context=16"]
    a, b = T.experiment(t, "swiglu", *tiny), T.experiment(t, "swiglu", *tiny)
    for run in ("GELU MLP/seed1", "SwiGLU/seed1"):
        for name in ("log.jsonl", "summary.json"):
            t.check(read(os.path.join(a.runs, run, name)) == read(os.path.join(b.runs, run, name)),
                    f"the same seed twice gave two different {run}/{name}")


def inside(S):
    import math
    import torch
    import torch.nn.functional as F
    from experiments import swiglu
    from models.gpt import GPT, MLP, SwiGLU

    torch.manual_seed(0)
    x = torch.randn(2, 5, 12, dtype=torch.float64)
    glu = SwiGLU(12, 32).double()
    p = {k: v.numpy() for k, v in glu.state_dict().items()}
    g, u = x.numpy() @ p["gate.weight"].T + p["gate.bias"], x.numpy() @ p["up.weight"].T + p["up.bias"]
    S.same(glu(x), (S.silu_numpy(g) * u) @ p["down.weight"].T + p["down.bias"], "SwiGLU against the formula", tol=1e-12)
    S.same(F.silu(x), x * torch.sigmoid(x), "silu is x times its sigmoid", tol=1e-15)
    assert glu.gate.weight.shape == glu.up.weight.shape == (32, 12) and glu.down.weight.shape == (12, 32)
    for W, h, bias in ((12, 32, True), (64, 170, True), (576, 1536, False)):
        n = sum(q.numel() for q in SwiGLU(W, h, bias).parameters())
        assert n == 3 * W * h + (2 * h + W) * bias, (W, h, bias, n)
    assert sum(q.numel() for q in SwiGLU(576, 1536, False).parameters()) == sum(q.numel() for q in MLP(576, False).parameters())

    try:
        import transformers
        from transformers.models.llama import modeling_llama as llama
    except ImportError:
        print("10.03 transformers is not installed: SwiGLU is not compared with its LlamaMLP")
    else:
        theirs = llama.LlamaMLP(transformers.LlamaConfig(hidden_size=12, intermediate_size=32, mlp_bias=False,
                                                         hidden_act="silu")).double()
        ours = SwiGLU(12, 32, bias=False).double()
        ours.load_state_dict({"gate.weight": theirs.gate_proj.weight, "up.weight": theirs.up_proj.weight,
                              "down.weight": theirs.down_proj.weight})
        S.same(ours(x), theirs(x), "SwiGLU against transformers' LlamaMLP", tol=1e-12)

    V, ctx, L, W = 65, 16, 2, 24
    torch.manual_seed(1)
    model = GPT(V, ctx, layers=L, heads=4, width=W, mlp="swiglu")
    assert all(isinstance(b.mlp, SwiGLU) and b.mlp.gate.weight.shape == (64, W) for b in model.blocks)
    assert sum(q.numel() for q in model.parameters()) - sum(q.numel() for q in GPT(V, ctx, L, 4, W).parameters()) == \
        L * ((2 * 64 + W) - (4 * W + W)), "the same matrices (3 x 24 x 64 = 2 x 24 x 96); the biases differ"
    named = dict(model.named_parameters())
    assert abs(named["blocks.0.mlp.gate.weight"].std().item() - 0.02) < 0.004
    assert abs(named["blocks.0.mlp.down.weight"].std().item() - 0.02 / math.sqrt(2 * L)) < 0.003
    assert (named["blocks.0.mlp.up.bias"] == 0).all()
    assert GPT(V, ctx, L, 4, W, mlp="swiglu", hidden=40).blocks[0].mlp.up.weight.shape == (40, W)
    model = model.double()
    with torch.no_grad():
        for q in model.parameters():
            q.add_(0.3 * torch.randn_like(q))
    ids = torch.randint(0, V, (2, ctx))
    S.same(model(ids), S.gpt10_numpy(model, ids.numpy(), 4, mlp="swiglu"), "GPT(mlp='swiglu') against numpy", tol=1e-10)

    shares = swiglu.gates(model, ids)
    with torch.no_grad():
        b0, e = model.blocks[0], model.embed(ids)
        s = F.silu(b0.mlp.gate(b0.norm2(e + b0.attention(b0.norm1(e)))))
    assert len(shares) == L and abs(shares[0][0] - (s.abs() < 0.1).double().mean().item()) < 1e-12, (shares, s.shape)
    assert abs(shares[0][1] - (s.abs() > 1).double().mean().item()) < 1e-12
