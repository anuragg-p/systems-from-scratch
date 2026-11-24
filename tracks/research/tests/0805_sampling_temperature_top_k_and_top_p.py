"""08.05 Sampling: temperature, top-k and top-p

top_k keeps the k highest scores (ties with the k-th too) and top_p the fewest symbols whose chances
add up to p, both against a direct computation on small scores, the kept chances in the same
proportions; generate is greedy at temperature 0 (the same as a loop of argmax), draws from the cut
distribution otherwise (counted over many draws), the same digits for the same generator, and reads
only the last model.context symbols; repeats is the paper's repetition; continuation_bits is each
character's bits from the characters before it. The short run: greedy writes text the model finds
far more likely than the test text and ends in loops; pure sampling is about as unlikely to it as
the text itself, a lower temperature, top-k and the nucleus all more likely; a checkpoint from
08.04 is used when given; and the same seed gives the same bytes again.
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
    r = T.experiment(t, "sampling", "seeds=2", "checkpoint=none")
    text = T.value(r.out, r"the text itself +(\S+)")
    got = {name: T.summaries(r, name)[0] for name in ("greedy", "pure_sampling", "sampling-t0.7", "top-k5",
                                                      "nucleus-p0.95")}
    ppl = {name: mean(s["perplexity"]) for name, s in got.items()}
    t.check(ppl["greedy"] < text / 2 and mean(got["greedy"]["repetition"]) >= 50,
            f"greedy: text the model finds far more likely than the test text, ending in loops: {text} {got['greedy']}")
    t.check(abs(ppl["pure_sampling"] / text - 1) < 0.15,
            f"pure sampling: about as unlikely to the model as the test text: {text} {ppl}")
    for name in ("sampling-t0.7", "top-k5", "nucleus-p0.95"):
        t.check(ppl[name] < ppl["pure_sampling"] * 0.95, f"{name}: more likely to the model than pure sampling: {ppl}")
    t.check("a small one trained here" in r.out, f"with no checkpoint, a small model is trained:\n{r.out[:600]}")
    tiny = ["seeds=2", "steps=20", "prompts=3", "length=12", "context=16", "prompt=8", "checkpoint=none"]
    a, b = T.experiment(t, "sampling", *tiny), T.experiment(t, "sampling", *tiny)
    for run in ("model/seed0", "pure_sampling/seed0", "nucleus-p0.95/seed0"):
        t.check(read(os.path.join(a.runs, run, "summary.json")) == read(os.path.join(b.runs, run, "summary.json")),
                f"the same seed twice gave two different {run}/summary.json")
    T.py(t, ["-c", CHECKPOINT.format(path=os.path.join(t.tmp, "tiny.safetensors"))])
    c = T.experiment(t, "sampling", *tiny[:2], "prompts=3", "length=12", "prompt=8",
                     f"checkpoint={os.path.join(t.tmp, 'tiny.safetensors')}")
    t.check("The model: the checkpoint" in c.out and "2 blocks of 2 heads, width 16, windows of 24" in c.out,
            f"given a checkpoint, the model should be the checkpoint's:\n{c.out[:600]}")


CHECKPOINT = """
import torch
from experiments.language import save
from models.gpt import GPT
torch.manual_seed(0)
config = dict(vocab=65, context=24, layers=2, heads=2, width=16, dropout=0.0, bias=True, positions=True)
save(GPT(**config), config, {path!r}, steps=7, val_bits=4.5)
"""


def inside(S):
    import collections
    import math
    import torch
    import torch.nn.functional as F
    from experiments import sampling
    from experiments.language import generate, top_k, top_p
    from models.gpt import GPT

    scores = torch.tensor([[1.0, 3.0, 2.0, 3.0, -1.0, 0.5], [0.0, 0.0, 0.0, 0.0, 0.0, 5.0]], dtype=torch.float64)
    p = F.softmax(scores, dim=-1)
    for k in range(1, 7):
        cut = F.softmax(top_k(scores, k), dim=-1)
        for row in range(2):
            kth = sorted(scores[row].tolist(), reverse=True)[k - 1]
            kept = [i for i in range(6) if scores[row, i] >= kth]
            total = sum(p[row, i].item() for i in kept)
            for i in range(6):
                want = p[row, i].item() / total if i in kept else 0.0
                assert abs(cut[row, i].item() - want) < 1e-12, (k, row, i)
    for q in (0.01, 0.3, 0.5, 0.75, 0.9, 0.95, 0.999, 1.0):
        cut = F.softmax(top_p(scores, q), dim=-1)
        for row in range(2):
            ranked = sorted(range(6), key=lambda i: -p[row, i].item())
            kept, mass = [], 0.0
            for i in ranked:
                if mass >= q and kept:
                    break
                kept.append(i)
                mass += p[row, i].item()
            for i in range(6):
                want = p[row, i].item() / mass if i in kept else 0.0
                assert abs(cut[row, i].item() - want) < 1e-12, (q, row, i, kept)
    assert torch.isfinite(top_p(scores, 1e-9)).sum(-1).tolist() == [1, 1], "the most likely symbol is always kept"

    class Fixed(torch.nn.Module):
        """A stand-in for a GPT whose scores are the same after anything: what generate draws from."""
        context = 4

        def __init__(self, row):
            super().__init__()
            self.row = row

        def forward(self, ids):
            assert ids.shape[1] <= self.context, "generate should read only the last model.context symbols"
            return self.row.expand(ids.shape[0], ids.shape[1], -1)

    fixed = Fixed(torch.log(torch.tensor([0.5, 0.3, 0.15, 0.05])))
    prompts = torch.zeros(4000, 6, dtype=torch.long)
    for kw, want in ((dict(), [0.5, 0.3, 0.15, 0.05]), (dict(k=2), [0.625, 0.375, 0, 0]),
                     (dict(p=0.7), [0.625, 0.375, 0, 0]), (dict(p=0.9), [0.5 / 0.95, 0.3 / 0.95, 0.15 / 0.95, 0]),
                     (dict(temperature=0.5), [x * x / 0.365 for x in (0.5, 0.3, 0.15, 0.05)])):
        drawn = generate(fixed, prompts, 1, torch.Generator().manual_seed(0), **kw)[:, 0].tolist()
        counts = collections.Counter(drawn)
        for symbol, w in enumerate(want):
            assert abs(counts[symbol] / 4000 - w) < 0.03, (kw, symbol, counts)
    assert (generate(fixed, prompts[:3], 5, torch.Generator(), temperature=0) == 0).all()

    torch.manual_seed(0)
    gpt = GPT(65, 10, layers=2, heads=2, width=16)
    ids = torch.randint(0, 65, (3, 14))
    greedy = generate(gpt, ids, 6, torch.Generator(), temperature=0)
    loop = ids.clone()
    with torch.no_grad():
        for _ in range(6):
            loop = torch.cat([loop, gpt(loop[:, -10:])[:, -1].argmax(-1, keepdim=True)], dim=1)
    assert torch.equal(greedy, loop[:, 14:]), "temperature 0 is argmax at every step"
    assert torch.equal(generate(gpt, ids, 6, torch.Generator().manual_seed(3), k=1), greedy)
    once, twice = (generate(gpt, ids, 8, torch.Generator().manual_seed(3), 0.8, 10, 0.9) for _ in range(2))
    assert torch.equal(once, twice), "the same generator, the same symbols"

    assert sampling.repeats(list("and the end ee ee ee")) and sampling.repeats([1, 2, 3, 1, 2, 3, 1, 2, 3])
    assert not sampling.repeats(list("and the end ee ee")) and not sampling.repeats([5, 5]) and \
        sampling.repeats([5, 5, 5, 5, 5, 5])
    continuation = torch.randint(0, 65, (3, 9))
    with torch.no_grad():
        rows = torch.cat([ids[:, :5], continuation], dim=1)
        span = 10 - 5 + 1
        want = [-math.log2(F.softmax(gpt(rows[b:b + 1, (t - 5) // span * span:t])[0, -1], 0)[rows[b, t]].item())
                for b in range(3) for t in range(5, 14)]
    assert abs(sampling.continuation_bits(gpt, ids[:, :5], continuation) - sum(want) / len(want)) < 1e-5
