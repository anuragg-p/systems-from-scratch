"""10.02 Rotary positions: turning instead of adding

Rotary turns each pair (i, i + d / 2) of a vector through m theta_i, as a 2 x 2 rotation written out
(tests/support.py) does; in float64 the score of a query at place m and a key at place n is the same when
both move along (shifted by 1 to 500 places, at 1e-12 of the score's size) and every vector keeps its
length; transformers' Llama turning (LlamaRotaryEmbedding and apply_rotary_pos_emb) gives the same
numbers, bit for bit in float32; the paper's neighbours form gives the same scores once the numbers are
reordered. A GPT with positions="rotary" has no table of positions (context x width weights fewer), equals
the same model computed again in float64 numpy, is causal, reads windows longer than its context, and
attention_maps still rebuilds its first block. The short run: rotary well below learned positions in
bits, the learned model refusing a longer window, the rotary model reading it and worse past the length
it was trained on; and the same seed gives the same bytes again.
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
    r = T.experiment(t, "rotary")
    learned, rotary = ([s["test_bits"] for s in T.summaries(r, k)] for k in ("learned", "rotary"))
    t.check(mean(rotary) < mean(learned) - 0.1, f"rotary positions should be well below learned ones: {rotary} {learned}")
    t.check("ValueError: 256 positions, but there are learned vectors for 64" in r.out,
            f"the learned positions should refuse a longer window:\n{r.out[-1500:]}")
    first = T.value(r.out, r"n = 4:\s+0 to  63: (\S+)")
    last = T.value(r.out, r"n = 4:.*128 to 255: (\S+)")
    t.check(last > first + 0.05, f"rotary positions, past the length trained on, should get worse: {first} {last}")
    moved = T.value(r.out, r"move along by 1, 7 or 1000 places +(\S+)")
    t.check(moved < 1e-9, f"the scores should not move when query and key move together: {moved}")
    tiny = ["seeds=2", "steps=10", "layers=1", "width=16", "context=16", "longer=[2]"]
    a, b = T.experiment(t, "rotary", *tiny), T.experiment(t, "rotary", *tiny)
    for run in ("learned/seed1", "rotary/seed1"):
        for name in ("log.jsonl", "summary.json"):
            t.check(read(os.path.join(a.runs, run, name)) == read(os.path.join(b.runs, run, name)),
                    f"the same seed twice gave two different {run}/{name}")


def inside(S):
    import torch
    from experiments import rotary
    from experiments.language import attention_maps
    from models.gpt import GPT, Rotary, SelfAttention

    torch.manual_seed(0)
    x = torch.randn(3, 2, 11, 8, dtype=torch.float64)
    for base in (10000.0, 100000.0):
        turn = Rotary(8, base)
        for b in range(3):
            for h in range(2):
                S.same(turn(x)[b, h], S.rotate_numpy(x[b, h].numpy(), base), f"Rotary (base {base}) against the "
                                                                              f"rotation written out", tol=1e-12)
    turn = Rotary(8)
    assert torch.equal(turn(x[..., :1, :]), x[..., :1, :]), "place 0 is not turned"
    q, k = torch.randn(2, 30, 8, dtype=torch.float64), torch.randn(2, 30, 8, dtype=torch.float64)
    scores = turn(q) @ turn(k).transpose(-2, -1)
    for s in (1, 5, 77, 500):
        S.same(turn(q, start=s) @ turn(k, start=s).transpose(-2, -1), scores, f"scores moved along by {s}", tol=1e-12)
    S.same(turn(q).norm(dim=-1), q.norm(dim=-1), "a turned vector's length", tol=1e-14)
    assert (turn(q) @ turn(k).transpose(-2, -1) - q @ k.transpose(-2, -1)).abs().max() > 0.1, "the turning does something"
    order = torch.cat([torch.arange(0, 8, 2), torch.arange(1, 8, 2)])
    S.same(rotary.neighbours(q) @ rotary.neighbours(k).transpose(-2, -1),
           turn(q[..., order]) @ turn(k[..., order]).transpose(-2, -1), "the paper's pairs, reordered", tol=1e-12)

    try:
        import transformers
        from transformers.models.llama import modeling_llama as llama
    except ImportError:
        print("10.02 transformers is not installed: the turning is not compared with its Llama's")
    else:
        import warnings
        warnings.filterwarnings("ignore")
        config = transformers.LlamaConfig(hidden_size=576, num_attention_heads=9, rope_theta=100000.0,
                                          max_position_embeddings=8192)
        theirs = llama.LlamaRotaryEmbedding(config)
        for T in (16, 600):
            qq = torch.randn(2, 9, T, 64)
            cos, sin = theirs(qq, torch.arange(T)[None])
            want, _ = llama.apply_rotary_pos_emb(qq, qq, cos, sin)
            assert torch.equal(Rotary(64, 100000.0)(qq), want), f"Rotary against transformers' Llama at {T} places"

    V, ctx, L, W = 65, 16, 2, 16
    learned = GPT(V, ctx, layers=L, heads=4, width=W)
    model = GPT(V, ctx, layers=L, heads=4, width=W, positions="rotary").double()
    assert model.positions is None and all(b.attention.rotary is not None for b in model.blocks)
    assert all(b.attention.rotary.d == 4 and b.attention.rotary.base == 10000.0 for b in model.blocks)
    assert sum(p.numel() for p in learned.parameters()) - sum(p.numel() for p in model.parameters()) == ctx * W
    assert all(b.attention.rotary is None for b in learned.blocks)
    with torch.no_grad():
        for p in model.parameters():
            p.add_(0.3 * torch.randn_like(p))
    ids = torch.randint(0, V, (2, ctx))
    S.same(model(ids), S.gpt10_numpy(model, ids.numpy(), 4, rotary=10000.0), "GPT(positions='rotary') against numpy",
           tol=1e-10)
    later = ids.clone()
    later[:, 9:] = (later[:, 9:] + 1) % V
    with torch.no_grad():
        assert torch.equal(model(ids)[:, :9], model(later)[:, :9]), "a later character should change nothing before it"
        assert model(torch.randint(0, V, (1, 4 * ctx))).shape == (1, 4 * ctx, V), "rotary reads past its context"
    maps = attention_maps(model, ids)
    a = model.blocks[0].attention
    with torch.no_grad():
        h = model.blocks[0].norm1(model.embed(ids))
        v = a.value(h).view(2, ctx, 4, 4).transpose(1, 2)
        S.same(a.out((maps[0] @ v).transpose(1, 2).reshape(2, ctx, W)), a(h), "attention_maps, rotary", tol=1e-12)
    one = SelfAttention(8, heads=2, rotary=500.0)
    assert one.rotary.base == 500.0 and one.rotary.d == 4
