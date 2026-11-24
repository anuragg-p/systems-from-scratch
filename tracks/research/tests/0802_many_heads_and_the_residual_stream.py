"""08.02 Many heads, and the residual stream

gelu is GPT-2's tanh form (F.gelu(approximate="tanh")); SelfAttention with heads equals each head's
attention written out on its slice of the width, and PyTorch's F.scaled_dot_product_attention on
the same queries, keys and values; a Block and a whole GPT (no positions) equal the same model
computed again in float64 numpy from their weights (tests/support.py) to 1e-10, and in float32 to
1e-5; a later character changes nothing before it; a GPT has V W + L (12 W^2 + 13 W) + 2 W weights
and starts as GPT-2 does; attention_maps gives each block's weights and looks what they reach. The
short run: 08.01's attention stacked four deep is far worse than one layer, four blocks far better
than one, four heads better than one head at the same weights; the logged weights are the deepest
model's, each row adding up to 1; and the same seed gives the same bytes again.
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
    r = T.experiment(t, "heads", "seeds=2")
    bits = {label: [s["test_bits"] for s in T.summaries(r, label)]
            for label in ("stack1-heads1", "stack4-heads1", "blocks1-heads4", "blocks4-heads4", "blocks4-heads1")}
    t.check(mean(bits["stack4-heads1"]) > mean(bits["stack1-heads1"]) + 0.3,
            f"08.01's attention stacked four deep should be far worse than one layer: {bits}")
    t.check(mean(bits["blocks4-heads4"]) < mean(bits["blocks1-heads4"]) - 0.05,
            f"four blocks should be better than one: {bits}")
    t.check(mean(bits["blocks4-heads4"]) < mean(bits["blocks4-heads1"]),
            f"four heads should be (a little) better than one head of the same weights: {bits}")
    s = T.summaries(r, "blocks4-heads4")[0]
    w = s["weights"]
    t.check(len(w) == 4 and all(len(block) == 4 for block in w) and len(s["window"]) == 32 and
            all(abs(sum(row) - 1) < 1e-3 and all(x == 0 for x in row[i + 1:])
                for block in w for head in block for i, row in enumerate(head)),
            "the logged weights: 4 blocks of 4 heads, each row over the positions up to it, adding up to 1")
    tiny = ["seeds=2", "steps=20", "layers=2"]
    a, b = T.experiment(t, "heads", *tiny), T.experiment(t, "heads", *tiny)
    for run in ("stack2-heads1/seed1", "blocks2-heads4/seed1"):
        for name in ("log.jsonl", "summary.json"):
            t.check(read(os.path.join(a.runs, run, name)) == read(os.path.join(b.runs, run, name)),
                    f"the same seed twice gave two different {run}/{name}")


def inside(S):
    import math
    import torch
    import torch.nn.functional as F
    from experiments import heads
    from experiments.language import attention_maps, looks
    from models.gpt import GPT, MLP, Block, SelfAttention, gelu

    x = torch.linspace(-6, 6, 241, dtype=torch.float64)
    S.same(gelu(x), F.gelu(x, approximate="tanh"), "gelu against F.gelu(approximate='tanh')", tol=1e-14)
    assert abs(gelu(torch.tensor(1.0, dtype=torch.float64)).item() -
               0.5 * (1 + math.tanh(math.sqrt(2 / math.pi) * 1.044715))) < 1e-15

    torch.manual_seed(0)
    layer = SelfAttention(12, heads=3).double()
    x = torch.randn(2, 6, 12, dtype=torch.float64)
    p = {k: v.numpy() for k, v in layer.state_dict().items()}
    S.same(layer(x), S.attention_numpy(x.numpy(), p, "", 3), "SelfAttention, 3 heads, against the loops", tol=1e-12)
    q, k, v = (f(x).view(2, 6, 3, 4).transpose(1, 2) for f in (layer.query, layer.key, layer.value))
    fused = F.scaled_dot_product_attention(q, k, v, is_causal=True).transpose(1, 2).reshape(2, 6, 12)
    S.same(layer(x), layer.out(fused), "SelfAttention against F.scaled_dot_product_attention", tol=1e-12)
    try:
        SelfAttention(10, heads=3)
        raise AssertionError("a width of 10 does not cut into 3 heads: that should be refused")
    except ValueError:
        pass

    mlp = MLP(12).double()
    S.same(mlp(x), mlp.down(F.gelu(mlp.up(x), approximate="tanh")), "MLP", tol=1e-12)
    assert mlp.up.weight.shape == (48, 12) and mlp.down.weight.shape == (12, 48)

    block = Block(12, 3).double()
    for param in block.parameters():
        torch.nn.init.normal_(param, 0.0, 0.5)
    p = {k: v.numpy() for k, v in block.state_dict().items()}
    S.same(block(x), S.block_numpy(x.numpy(), p, "", 3), "Block against numpy", tol=1e-10)

    torch.manual_seed(1)
    gpt = GPT(65, 16, layers=3, heads=4, width=16, positions=False).double()
    with torch.no_grad():
        for param in gpt.parameters():
            param.add_(0.3 * torch.randn_like(param))
    ids = torch.randint(0, 65, (2, 11))
    S.same(gpt(ids), S.gpt_numpy(gpt, ids.numpy(), 4), "GPT against numpy, float64", tol=1e-10)
    S.same(gpt.float()(ids), S.gpt_numpy(gpt, ids.numpy(), 4), "GPT against numpy, float32", tol=1e-5)
    gpt.double()
    later = ids.clone()
    later[:, 8:] = (later[:, 8:] + 1) % 65
    with torch.no_grad():
        assert torch.equal(gpt(ids)[:, :8], gpt(later)[:, :8]), "a later character should change nothing before it"
    assert gpt(torch.randint(0, 65, (1, 40))).shape == (1, 40, 65), "without positions any length can be read"

    V, W, L = 65, 32, 3
    fresh = GPT(V, 16, layers=L, heads=4, width=W, positions=False)
    assert sum(p.numel() for p in fresh.parameters()) == V * W + L * (12 * W * W + 13 * W) + 2 * W
    named = dict(fresh.named_parameters())
    assert abs(named["tokens.weight"].std().item() - 0.02) < 0.002
    assert abs(named["blocks.0.attention.query.weight"].std().item() - 0.02) < 0.003
    assert abs(named["blocks.0.mlp.down.weight"].std().item() - 0.02 / math.sqrt(2 * L)) < 0.002
    assert abs(named["blocks.0.attention.out.weight"].std().item() - 0.02 / math.sqrt(2 * L)) < 0.002
    assert (named["blocks.0.mlp.up.bias"] == 0).all() and (named["norm.weight"] == 1).all()

    maps = attention_maps(gpt, ids)
    assert len(maps) == 3 and maps[0].shape == (2, 4, 11, 11) and gpt.training
    for w in maps:
        assert torch.allclose(w.sum(-1), torch.ones(2, 4, 11, dtype=torch.float64))
        assert (w.triu(1) == 0).all()
    with torch.no_grad():
        h = gpt.blocks[0].norm1(gpt.embed(ids))
        a = gpt.blocks[0].attention
        v = a.value(h).view(2, 11, 4, 4).transpose(1, 2)
        S.same(a.out((maps[0] @ v).transpose(1, 2).reshape(2, 11, 16)), a(h), "the first block's weights", tol=1e-12)
    flat = [torch.tril(torch.ones(6, 6, dtype=torch.float64))[None, None]]
    flat[0] = flat[0] / flat[0].sum(-1, keepdim=True)
    ((back, own, before),) = looks(flat, skip=2)[0]
    assert abs(back - sum(i / 2 for i in range(2, 6)) / 4) < 1e-12
    assert abs(own - sum(1 / (i + 1) for i in range(2, 6)) / 4) < 1e-12 and abs(before - own) < 1e-12

    stack = heads.Stack(65, 12, 2, 3)
    assert stack(ids).shape == (2, 11, 65) and len(stack.layers) == 2
