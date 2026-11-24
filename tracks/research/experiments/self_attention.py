"""Self-attention with a causal mask: one head, on Tiny Shakespeare.

07.04's decoder attended from its own state to another sequence, the
encoder's. Here a sequence attends to itself: the model reads a window of
`context` characters and scores the next character at every position of
it at once (models/gpt.py: SelfAttention, self_attend). The model is the
smallest that does only that: each character's embedding (07.02), one
head of self-attention, and a Linear layer to the scores.

1. Why the scores are divided by sqrt(d) (Vaswani et al. 2017, section
   3.2.1 and its footnote): for queries and keys of d random numbers of
   variance 1, the spread of their dot products, the largest softmax
   weight, and the gradient that passes back through the softmax, with
   and without the division; then the model trained with and without it,
   a few seeds each.
2. The obvious self-attention lets every position look at every other,
   the later ones too. Trained so, the loss it reports is better than the
   masked model's, on held-out text as well; asked for each character from
   the characters before it only, it is worse, and what it writes falls
   into one character over and over. The mask: a later position's score
   is -inf before the softmax. What each writes is scored by 07.02's best
   count model (deleted interpolation of contexts up to 5 characters).
3. With the mask, changing the last character of a window changes no
   score before it, exactly; without it, every one.

    python3 -m experiments.self_attention
"""

import numpy as np
import torch
from torch import nn
import torch.nn.functional as F

import lab
from data import shakespeare
from experiments.language import train
from experiments.sequences import bits, sample, window_bits, windows
from models.gpt import SelfAttention
from models.ngram import NGram, mixture_weights

CONFIG = dict(width=128, context=32, batch=32, steps=600, lr=0.003, warmup=50, weight_decay=0.1, clip=1.0, every=100,
              seeds=3, sizes=[16, 64, 256, 1024], length=300, orders=5, device="cpu")
KINDS = {"masked": dict(mask=True, scale=True), "not divided": dict(mask=True, scale=False),
         "no mask": dict(mask=False, scale=True)}


# @build 08.01 OneHead
# The smallest model of the next character that uses self-attention: each
# character's embedding (07.02), one head of self-attention over the
# window (with its mask and its division by sqrt(d), unless turned off),
# and a Linear layer from each position's result to a score for every
# character. x is (batch, T); returns (batch, T, V).
class OneHead(nn.Module):
    def __init__(self, V, width, mask=True, scale=True):
        super().__init__()
        self.tokens = nn.Embedding(V, width)
        self.attention = SelfAttention(width, mask=mask, scale=scale)
        self.out = nn.Linear(width, V)

    def forward(self, x):
        return self.out(self.attention(self.tokens(x)))
# @end


# @build 08.01 last_bits
# Bits per character of model on ids, each scored character predicted from
# the `context` characters before it only: the window that ends just before
# it, and the model's scores at that window's last position. Every
# `every`-th character from position `context` on, in batches, in eval mode
# and without a graph; the model is put back in training mode.
def last_bits(model, ids, context, every=8, batch=512):
    model.eval()
    positions = torch.arange(context, len(ids), every, device=ids.device)
    total = 0.0
    with torch.no_grad():
        for start in range(0, len(positions), batch):
            p = positions[start:start + batch]
            x, _ = windows(ids, p - context, context)
            total += bits(model(x)[:, -1], ids[p]).item() * len(p)
    model.train()
    return total / len(positions)
# @end


# @build 08.01 at_the_start
# Vaswani et al.'s footnote, in numbers: 1000 queries, each against the
# keys of T positions, every query and key d numbers drawn with variance 1
# (from rng); the scores q . k, divided by sqrt(d) when scale is set.
# Returns their sd, the mean over the queries of the largest softmax
# weight, and the mean length of the gradient the softmax passes back to
# the scores (for a random weighting of its output).
def at_the_start(d, T, scale, rng):
    q = torch.from_numpy(rng.standard_normal((1000, 1, d)))
    k = torch.from_numpy(rng.standard_normal((1000, T, d)))
    scores = (q @ k.transpose(-2, -1))[:, 0]
    if scale:
        scores = scores / d ** 0.5
    scores.requires_grad_()
    w = F.softmax(scores, dim=-1)
    (g,) = torch.autograd.grad((w * torch.from_numpy(rng.standard_normal(w.shape))).sum(), scores)
    return scores.detach().std().item(), w.max(dim=-1).values.mean().item(), g.norm(dim=-1).mean().item()
# @end


def judge(train_ids, val, n):
    """07.02's best count model: deleted interpolation of the contexts up to n characters, fit on val.
    Returns a function giving its bits per character of a text (a numpy array of numbers), from
    position n on."""
    V = len(shakespeare.chars())
    models = [NGram(train_ids, j, V) for j in range(n + 1)]

    def rows(ids):
        return np.stack([models[j].probabilities(ids)[n - j:] for j in range(n + 1)])
    w = mixture_weights(rows(val))
    return lambda ids: float(-np.log2(w @ rows(np.asarray(ids))).mean())


def longest_run(ids):
    """The most times one character comes in a row in ids."""
    best = run = 1
    for a, b in zip(ids, ids[1:]):
        run = run + 1 if a == b else 1
        best = max(best, run)
    return best


def main():
    cfg = lab.config(CONFIG)
    dev = lab.device(torch, cfg.device)
    V = len(shakespeare.chars())
    train_ids, val, test = (shakespeare.split(s) for s in ("train", "val", "test"))
    train_t, test_t = (torch.from_numpy(a).to(dev) for a in (train_ids, test))
    start = lab.clock(torch, dev)

    rng = np.random.default_rng(0)
    print(f"1. Scores q . k for queries and keys of d random numbers of variance 1, over {cfg.context} positions:\n"
          f"   their sd, the largest softmax weight (mean), the gradient back through the softmax (mean length)")
    print(f"   {'d':>5s}   {'sd':>6s} {'largest':>8s} {'gradient':>9s}    divided by sqrt(d): "
          f"{'sd':>5s} {'largest':>8s} {'gradient':>9s}")
    for d in cfg.sizes:
        raw, scaled = (at_the_start(d, cfg.context, scale, rng) for scale in (False, True))
        print(f"   {d:5d}   {raw[0]:6.2f} {raw[1]:8.3f} {raw[2]:9.2e}    {'':20s}{scaled[0]:5.2f} {scaled[1]:8.3f} "
              f"{scaled[2]:9.2e}")

    results, nets = {}, {}
    for kind, how in KINDS.items():
        for seed in range(cfg.seeds):
            run = lab.Run(cfg, seed, label=kind.replace(" ", "_"))
            torch.manual_seed(seed)
            model = OneHead(V, cfg.width, **how).to(dev)
            train(model, cfg, run, dev, train_t)
            model.eval()
            got = dict(train_bits=run.rows[-1]["bits"], test_bits=window_bits(model, test_t, cfg.context, 1),
                       past_bits=last_bits(model, test_t, cfg.context))
            run.finish(**got)
            for key, v in got.items():
                results.setdefault((kind, key), []).append(v)
            nets.setdefault(kind, model)

    def row(kind, key):
        return results[kind, key]
    print(f"   Trained, one head of width {cfg.width} ({cfg.steps} steps), bits per character on the test text:")
    print(f"   divided      {lab.spread(row('masked', 'past_bits'), 4)}")
    print(f"   not divided  {lab.spread(row('not divided', 'past_bits'), 4)}   "
          f"t = {lab.welch_t(row('not divided', 'past_bits'), row('masked', 'past_bits')):+.1f}")

    print(f"\n2. One head (width {cfg.width}), with the mask and without: {cfg.steps} steps of {cfg.batch} windows of "
          f"{cfg.context} characters, {cfg.seeds} seeds; bits per character")
    for key, what in (("train_bits", "the last training batch"),
                      ("test_bits", f"the test text, every position of windows of {cfg.context}, as in training"),
                      ("past_bits", f"the test text, each character from the {cfg.context} before it only")):
        print(f"   {what}:")
        for kind in ("masked", "no mask"):
            print(f"      {kind:8s} {lab.spread(row(kind, key), 4)}")
        print(f"      no mask against masked: t = {lab.welch_t(row('no mask', key), row('masked', key)):+.1f}")

    score = judge(train_ids, val, cfg.orders)
    print(f"\n   What each writes ({cfg.length} characters after a newline, seed 0's model), scored by 07.02's count "
          f"model\n   (deleted interpolation up to {cfg.orders} characters; the test text itself: {score(test):.3f} bits "
          f"per character, longest run of one character {longest_run(test.tolist())})")
    for kind in ("masked", "no mask"):
        model = nets[kind]
        prompt = shakespeare.encode("\n").tolist()
        drawn = sample(lambda ids: model(ids[None, -cfg.context:].to(dev))[0, -1], prompt, cfg.length,
                       torch.Generator().manual_seed(0))
        print(f"\n   {kind}: {score(np.array(prompt + drawn)):.3f} bits per character, longest run of one character "
              f"{longest_run(drawn)}\n")
        print("\n".join(("      " + line).rstrip() for line in shakespeare.decode(drawn).split("\n")))

    print(f"\n3. A window of {cfg.context} test characters, then the same window with its last character changed:")
    x = test_t[None, :cfg.context]
    changed = x.clone()
    changed[0, -1] = (changed[0, -1] + 1) % V
    for kind in ("masked", "no mask"):
        with torch.no_grad():
            moved = (nets[kind](changed) - nets[kind](x))[0, :-1].abs().amax(dim=-1)
        print(f"   {kind:8s} the largest change in the scores at the {cfg.context - 1} positions before it: "
              f"{moved.max().item():.3g}; positions whose scores changed: {int((moved > 0).sum())}")
    print(f"\n{lab.clock(torch, dev) - start:.0f} s of training and scoring on {dev.type}")


if __name__ == "__main__":
    main()
