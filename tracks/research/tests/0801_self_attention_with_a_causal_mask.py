"""08.01 Self-attention with a causal mask

causal_mask is the lower triangle; self_attend equals the formula written out by loops (scores q . k
/ sqrt(d), the later positions left out, a softmax, a weighted sum of the values), with and without
the mask and the division, and PyTorch's F.scaled_dot_product_attention, in float64 to 1e-12;
SelfAttention is its four Linear layers around self_attend; with the mask, changing a later
character leaves every score before it exactly the same, without it changes them; last_bits scores
each character from the window before it; at_the_start's spreads are sqrt(d) and 1. The short run:
without the mask the loss as trained is lower than with it and the bits from the past only are far
higher; without the division the trained model is worse; the masked model's text is not one
character over and over and the unmasked one's is; and the same seed gives the same bytes again.
"""

import os
import re


def mean(rows, key):
    return sum(s[key] for s in rows) / len(rows)


def read(path):
    with open(path, "rb") as f:
        return f.read()


def test(t):
    T = t.track
    T.inside(t, __file__)
    r = T.experiment(t, "self_attention", "seeds=2", "sizes=[16,1024]")
    masked, plain, unmasked = (T.summaries(r, label) for label in ("masked", "not_divided", "no_mask"))
    t.check(mean(unmasked, "test_bits") < mean(masked, "test_bits") - 0.15,
            f"without the mask, scored as trained, the loss should look better: {masked} {unmasked}")
    t.check(mean(unmasked, "past_bits") > mean(masked, "past_bits") + 0.3,
            f"without the mask, each character from the past only, it should be far worse: {masked} {unmasked}")
    t.check(mean(plain, "past_bits") > mean(masked, "past_bits") + 0.08,
            f"without the division by sqrt(d) the trained model should be worse: {masked} {plain}")
    runs = [int(m) for m in re.findall(r"longest run of one character (\d+)", r.out)]
    t.check(len(runs) == 3 and runs[1] < 10 and runs[2] > 20,
            f"the masked model's text should not be one character over and over, the unmasked one's should: {runs}")
    t.check(T.value(r.out, r"masked +the largest change in the scores at the \d+ positions before it: (\S+);") == 0,
            f"with the mask, a later character should change nothing before it:\n{r.out[-600:]}")
    t.check(T.value(r.out, r"no mask +the largest change in the scores at the \d+ positions before it: (\S+);") > 0,
            f"without the mask, a later character should change the scores before it:\n{r.out[-600:]}")
    tiny = ["seeds=2", "steps=20", "sizes=[16]", "length=20", "orders=2"]
    a, b = T.experiment(t, "self_attention", *tiny), T.experiment(t, "self_attention", *tiny)
    for run in ("masked/seed1", "no_mask/seed1"):
        for name in ("log.jsonl", "summary.json"):
            t.check(read(os.path.join(a.runs, run, name)) == read(os.path.join(b.runs, run, name)),
                    f"the same seed twice gave two different {run}/{name}")


def inside(S):
    import math
    import numpy as np
    import torch
    import torch.nn.functional as F
    from experiments import self_attention
    from models.gpt import SelfAttention, causal_mask, self_attend

    assert causal_mask(4).tolist() == [[i >= j for j in range(4)] for i in range(4)]

    torch.manual_seed(0)
    q, k, v = (torch.randn(2, 3, 5, 4, dtype=torch.float64) for _ in range(3))
    for mask in (True, False):
        for scale in (True, False):
            got, weights = self_attend(q, k, v, mask, scale)
            for b in range(2):
                for h in range(3):
                    for i in range(5):
                        seen = range(i + 1) if mask else range(5)
                        s = [sum(q[b, h, i, c].item() * k[b, h, j, c].item() for c in range(4)) / (2.0 if scale else 1.0)
                             for j in seen]
                        e = [math.exp(x - max(s)) for x in s]
                        w = [x / sum(e) for x in e]
                        for j in range(5):
                            want = w[j] if j in seen else 0.0
                            assert abs(weights[b, h, i, j].item() - want) < 1e-12, (mask, scale, b, h, i, j)
                        for c in range(4):
                            want = sum(w[n] * v[b, h, j, c].item() for n, j in enumerate(seen))
                            assert abs(got[b, h, i, c].item() - want) < 1e-12, (mask, scale, b, h, i, c)
    for mask in (True, False):
        S.same(self_attend(q, k, v, mask)[0], F.scaled_dot_product_attention(q, k, v, is_causal=mask),
               f"self_attend, mask={mask}, against F.scaled_dot_product_attention", tol=1e-12)

    layer = SelfAttention(6).double()
    x = torch.randn(2, 7, 6, dtype=torch.float64)
    q, k, v = layer.query(x), layer.key(x), layer.value(x)
    scores = (q @ k.transpose(1, 2) / math.sqrt(6)).masked_fill(torch.ones(7, 7).triu(1).bool(), float("-inf"))
    S.same(layer(x), layer.out(F.softmax(scores, dim=-1) @ v), "SelfAttention against its definition", tol=1e-12)
    assert len(list(layer.parameters())) == 8, "four Linear layers, each with its bias"

    later = x.clone()
    later[:, -1] = torch.randn(2, 6, dtype=torch.float64)
    assert torch.equal(layer(x)[:, :-1], layer(later)[:, :-1]), "with the mask a later position changes nothing before it"
    loose = SelfAttention(6, mask=False).double()
    assert not torch.equal(loose(x)[:, :-1], loose(later)[:, :-1]), "without the mask it should"
    net = self_attention.OneHead(65, 16).double()
    ids = torch.randint(0, 65, (3, 12))
    changed = ids.clone()
    changed[:, 7] = (changed[:, 7] + 1) % 65
    assert torch.equal(net(ids)[:, :7], net(changed)[:, :7]) and not torch.equal(net(ids)[:, 7:], net(changed)[:, 7:])
    assert net(ids).shape == (3, 12, 65)

    text = torch.randint(0, 65, (200,))
    with torch.no_grad():
        want = [-math.log2(F.softmax(net(text[p - 10:p][None])[0, -1], 0)[text[p]].item()) for p in range(10, 200, 3)]
    assert abs(self_attention.last_bits(net, text, 10, every=3, batch=7) - sum(want) / len(want)) < 1e-9
    assert net.training

    rng = np.random.default_rng(0)
    sd, largest, gradient = self_attention.at_the_start(400, 30, False, rng)
    assert abs(sd / math.sqrt(400) - 1) < 0.1 and largest > 0.8, (sd, largest)
    sd, largest, _ = self_attention.at_the_start(400, 30, True, rng)
    assert abs(sd - 1) < 0.1 and largest < 0.3, (sd, largest)
