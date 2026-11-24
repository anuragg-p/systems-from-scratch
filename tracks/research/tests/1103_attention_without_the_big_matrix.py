"""11.03 Attention without the big matrix

fused_attend gives self_attend's sums in float64 to 1e-12, with and without the mask and the division, and
its gradients; PyTorch runs it as its CPU flash-attention kernel (the profiler names it). GPT(fused=True)
gives the same scores and gradients as GPT() in float64 (learned and rotary positions, grouped heads) and
is built draw for draw like it; fused is off unless asked for, and attention_maps, which needs the weights,
still rebuilds a fused model's first block. kept_bytes counts what autograd keeps: written out, the (T, T)
weights among it; fused, under a fifth of that at 256 positions, and growing with T, not T squared. The
short run: the same numbers, the memory kept, and trained alike from the same seeds the same bits to 1e-3.
"""

import re


def test(t):
    T = t.track
    T.inside(t, __file__)
    r = T.experiment(t, "fused")
    worst = T.value(r.out, r"mask and division on and off +(\S+)")
    scores = T.value(r.out, r"written out against fused: scores (\S+),")
    grads = T.value(r.out, r"every gradient (\S+)")
    t.check(max(worst, scores, grads) < 1e-12, f"fused and written out should give the same numbers: {worst} {scores} {grads}")
    kept = {int(T): (float(w), float(f)) for T, w, f in
            re.findall(r"^ +(\d+) +\S+ ms +(\S+) +\S+ ms +(\S+) +x", r.out, re.M)}
    t.check(sorted(kept) == [64, 128, 256, 512, 1024] and all(f < w / 5 for T, (w, f) in kept.items() if T >= 512),
            f"fused should keep a small part of what written out keeps: {kept}")
    a, b = (T.summaries(r, k) for k in ("written out", "fused"))
    t.check(all(abs(x["test_bits"] - y["test_bits"]) < 1e-3 for x, y in zip(a, b)),
            f"trained alike, the same bits: {a} {b}")


def inside(S):
    import torch
    import torch.nn.functional as F
    from torch.profiler import ProfilerActivity, profile
    from experiments import fused
    from experiments.language import attention_maps
    from models.gpt import GPT, SelfAttention, fused_attend, self_attend

    torch.manual_seed(0)
    for shape in ((2, 3, 17, 8), (1, 1, 1, 4), (3, 2, 64, 16)):
        q, k, v = (torch.randn(*shape, dtype=torch.float64, requires_grad=True) for _ in range(3))
        for mask in (True, False):
            for scale in (True, False):
                a = fused_attend(q, k, v, mask, scale)
                b = self_attend(q, k, v, mask, scale)[0]
                S.same(a, b, f"fused_attend {shape} mask={mask} scale={scale}", tol=1e-12)
                g = torch.randn_like(a)
                ga = torch.autograd.grad(a, (q, k, v), g)
                gb = torch.autograd.grad(b, (q, k, v), g)
                for x, y in zip(ga, gb):
                    S.same(x, y, f"fused_attend's gradients {shape} mask={mask} scale={scale}", tol=1e-12)
    q, k, v = (torch.randn(4, 2, 32, 8) for _ in range(3))
    with profile(activities=[ProfilerActivity.CPU], acc_events=True) as prof:
        fused_attend(q, k, v)
    assert any("flash_attention" in e.key for e in prof.key_averages()), "the CPU's flash-attention kernel"

    assert not SelfAttention(8, heads=2).fused and SelfAttention(8, heads=2, fused=True).fused
    for kw in (dict(), dict(positions="rotary", norm="rms", mlp="swiglu", kv_heads=2), dict(positions=False)):
        torch.manual_seed(1)
        a = GPT(65, 24, layers=2, heads=4, width=16, **kw).double()
        torch.manual_seed(1)
        b = GPT(65, 24, layers=2, heads=4, width=16, fused=True, **kw).double()
        assert all(torch.equal(x, y) for x, y in zip(a.parameters(), b.parameters())), "built draw for draw alike"
        assert all(blk.attention.fused for blk in b.blocks) and not any(blk.attention.fused for blk in a.blocks)
        ids = torch.randint(0, 65, (3, 24))
        for m in (a, b):
            m.zero_grad()
            F.cross_entropy(m(ids[:, :-1]).reshape(-1, 65), ids[:, 1:].reshape(-1)).backward()
        S.same(b(ids), a(ids), f"GPT(fused=True) {kw}", tol=1e-12)
        for x, y in zip(b.parameters(), a.parameters()):
            S.same(x.grad, y.grad, f"GPT(fused=True)'s gradients {kw}", tol=1e-12)
        maps = attention_maps(b, ids)
        blk = b.blocks[0]
        with torch.no_grad():
            h = blk.norm1(b.embed(ids))
            _, _, vv = blk.attention.qkv(h)
            S.same(blk.attention.out((maps[0] @ vv).transpose(1, 2).reshape(3, 24, 16)), blk.attention(h),
                   f"attention_maps of a fused GPT {kw}", tol=1e-12)

    B, H, d = 2, 2, 8
    kept = {}
    for T in (64, 256):
        q, k, v = (torch.randn(B, H, T, d, requires_grad=True) for _ in range(3))
        w, _ = fused.kept_bytes(lambda: self_attend(q, k, v)[0])
        f, _ = fused.kept_bytes(lambda: fused_attend(q, k, v))
        assert w >= B * H * T * T * 4, (T, w)
        kept[T] = (w, f)
    assert kept[256][1] < kept[256][0] / 5, kept
    assert kept[256][1] <= 4.5 * kept[64][1], f"fused keeps what grows with T, not T squared: {kept}"
    n, out = fused.kept_bytes(lambda: torch.ones(3, requires_grad=True).exp().sum())
    assert n == 3 * 4 and out.item() > 0
