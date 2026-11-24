"""07.04 Attention: looking back at every position

attend is the formula written out (a softmax over the positions, weights that add up to 1, a weighted
sum of the values); Additive's scores are v . tanh(W q + U k) for every query and key; the decoder
without attention never looks at the encoder's states, the one with attention takes its context
from attend over them; teacher forcing with the symbols a model wrote gives the scores it wrote
them by. The short run: without attention the copy is right at length 2 and falls far with length;
with attention it holds at the lengths trained on and stays far above without on a longer one; the
logged weights are each output step's, over the input, adding up to 1; and the same seed gives the
same bytes again.
"""

import math
import os


def read(path):
    with open(path, "rb") as f:
        return f.read()


def test(t):
    T = t.track
    T.inside(t, __file__)
    r = T.experiment(t, "attention", "seeds=2", "steps=800", "lengths=[2,10,30]", "tested=300")
    plain, attending = T.summaries(r, "no-attention"), T.summaries(r, "attention")
    for p, a in zip(plain, attending):
        right, wrong = a["symbols_right"], p["symbols_right"]
        t.check(wrong["2"] > 0.9 and wrong["10"] < 0.5, f"without attention: right at 2, far worse at 10: {wrong}")
        t.check(right["10"] > 0.95, f"with attention the copy should hold at length 10: {right}")
        t.check(right["30"] > wrong["30"] + 0.3, f"at 30, longer than trained on, attention should stay far ahead: "
                                                  f"{right} {wrong}")
        for example in a["examples"]:
            n = len(example["input"])
            t.check(len(example["weights"]) == n and all(len(w) == n and abs(sum(w) - 1) < 1e-5
                                                         for w in example["weights"]),
                    f"each output step's weights over the {n} inputs, adding up to 1: {example}")
    tiny = ["seeds=2", "steps=20", "lengths=[3]", "tested=20", "examples=[4]", "shown=4"]
    a, b = T.experiment(t, "attention", *tiny), T.experiment(t, "attention", *tiny)
    for run in ("no-attention/seed1", "attention/seed1"):
        for name in ("log.jsonl", "summary.json"):
            t.check(read(os.path.join(a.runs, run, name)) == read(os.path.join(b.runs, run, name)),
                    f"the same seed twice gave two different {run}/{name}")


def inside(S):
    import torch
    from models.attention import Additive, attend
    from models.seq2seq import AttentionDecoder, Decoder, Encoder, Seq2Seq

    torch.manual_seed(0)
    scores = torch.randn(2, 3, 5, dtype=torch.float64)
    values = torch.randn(2, 5, 4, dtype=torch.float64)
    summed, weights = attend(scores, values)
    for b in range(2):
        for q in range(3):
            e = [math.exp(s) for s in scores[b, q].tolist()]
            w = [x / sum(e) for x in e]
            assert all(abs(a - c) < 1e-12 for a, c in zip(weights[b, q].tolist(), w))
            want = [sum(w[j] * values[b, j, d].item() for j in range(5)) for d in range(4)]
            assert all(abs(a - c) < 1e-12 for a, c in zip(summed[b, q].tolist(), want)), (b, q)
    assert torch.allclose(weights.sum(-1), torch.ones(2, 3, dtype=torch.float64))

    score = Additive(4, 6, 3).double()
    q, k = torch.randn(2, 3, 4, dtype=torch.float64), torch.randn(2, 5, 6, dtype=torch.float64)
    got = score(q, k)
    assert got.shape == (2, 3, 5)
    for b in range(2):
        for i in range(3):
            for j in range(5):
                want = score.v.weight[0] @ torch.tanh(score.W.weight @ q[b, i] + score.U.weight @ k[b, j])
                assert abs(got[b, i, j].item() - want.item()) < 1e-12, (b, i, j)

    torch.manual_seed(1)
    states = torch.randn(2, 6, 8, dtype=torch.float64)
    h = torch.randn(2, 8, dtype=torch.float64)
    previous = torch.tensor([3, 10])
    plain = Decoder(10, 5, 8).double()
    s1, h1, w1 = plain.step(previous, h, states)
    s2, h2, _ = plain.step(previous, h, torch.randn(2, 6, 8, dtype=torch.float64))
    assert w1 is None and torch.equal(s1, s2) and torch.equal(h1, h2), "without attention the states go unused"
    looking = AttentionDecoder(10, 5, 8, 7).double()
    s, h_new, w = looking.step(previous, h, states)
    context, want_w = attend(looking.score(h[:, None], states), states)
    assert torch.allclose(w, want_w[:, 0])
    want_h = looking.cell(torch.cat([looking.embed(previous), context[:, 0]], dim=1), h)
    assert torch.allclose(h_new, want_h) and torch.allclose(s, looking.out(torch.cat([want_h, context[:, 0]], dim=1)))

    for decoder in (Decoder(10, 5, 8), AttentionDecoder(10, 5, 8, 7)):
        net = Seq2Seq(Encoder(10, 5, 8), decoder).double()
        x = torch.randint(0, 10, (3, 6))
        written, weights = net.generate(x, 6)
        start = torch.full((3, 1), 10)
        scores, forced = net(x, torch.cat([start, written[:, :-1]], dim=1))
        assert torch.equal(scores.argmax(-1), written), "teacher forcing with its own symbols writes them again"
        assert (weights is None) == (forced is None) and (weights is None or torch.allclose(weights, forced))
        assert scores.shape == (3, 6, 10)
