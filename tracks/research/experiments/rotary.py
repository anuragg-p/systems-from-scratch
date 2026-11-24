"""Rotary positions: turning instead of adding.

08.03's positions are a learned vector for each place, added to the
character's embedding: a table of rows for places 0 to context - 1 and
none after. Su et al. (2021) put the place into attention instead: each
query and each key is turned, pair of numbers by pair, through angles
that grow with its place (models/gpt.py's Rotary), so the dot product of
a query and a key depends on how far apart they are, not on where they
are (their equation 16). Nothing is added to the embeddings and nothing
is learned. Their abstract: "RoPE enables valuable properties, including
the flexibility of sequence length, decaying inter-token dependency with
increasing relative distances". Here, on Tiny Shakespeare:

1. The turning, exactly, in float64: the score of a query at place m and
   a key at place n is the same when both move along by s; every vector
   keeps its length; the paper's pairs (neighbours) and ours (i and
   i + d / 2) give the same scores when the rows of the projections are
   put in the other order.
2. Bits per character on the test text: 08.03's learned positions
   against rotary positions, at the length trained on; weights; ms a step.
3. Past the length trained on: windows two and four times as long. The
   learned table has no row for them; the rotary model reads them.

    python3 -m experiments.rotary
"""

import torch

import lab
from data import shakespeare
from experiments.language import compare
from experiments.sequences import bits, windows
from models.gpt import Rotary

CONFIG = dict(layers=4, heads=4, width=64, context=64, batch=32, steps=150, lr=0.003, warmup=50, weight_decay=0.1,
              clip=1.0, every=50, seeds=3, longer=[2, 4], device="cpu")


# @build 10.02 neighbours
# The paper's own form of the turning (its equation 34), for x of shape
# (..., T, d): numbers 2i and 2i + 1 are pair i, turned through m theta_i
# at place m; x times the cosines plus (-x_2, x_1, -x_4, x_3, ...) times
# the sines, each angle written twice, once for each number of its pair.
def neighbours(x, base=10000.0):
    d = x.shape[-1]
    theta = 1.0 / base ** (torch.arange(0, d, 2, dtype=x.dtype) / d)
    angles = (torch.arange(x.shape[-2], dtype=x.dtype)[:, None] * theta).repeat_interleave(2, dim=-1)
    swapped = torch.stack([-x[..., 1::2], x[..., 0::2]], dim=-1).flatten(-2)
    return x * angles.cos() + swapped * angles.sin()
# @end


def main():
    cfg = lab.config(CONFIG)
    dev = lab.device(torch, cfg.device)
    V = len(shakespeare.chars())
    train_t, test_t = (torch.from_numpy(shakespeare.split(s)).to(dev) for s in ("train", "test"))
    start = lab.clock(torch, dev)

    d = cfg.width // cfg.heads
    turn = Rotary(d)
    g = torch.Generator().manual_seed(0)
    q, k = (torch.randn(8, 40, d, dtype=torch.float64, generator=g) for _ in range(2))
    scores = turn(q) @ turn(k).transpose(-2, -1)
    moved = max((turn(q, start=s) @ turn(k, start=s).transpose(-2, -1) - scores).abs().max().item() for s in (1, 7, 1000))
    length = (turn(q).norm(dim=-1) - q.norm(dim=-1)).abs().max().item()
    order = torch.cat([torch.arange(0, d, 2), torch.arange(1, d, 2)])     # neighbours' numbers, put as ours pair them
    paper = neighbours(q) @ neighbours(k).transpose(-2, -1)
    ours = turn(q[..., order]) @ turn(k[..., order]).transpose(-2, -1)
    unturned = (q @ k.transpose(-2, -1) - scores).abs().max().item()
    print(f"1. Rotary positions on 8 x 40 queries and keys of {d} numbers (float64), the largest change:\n"
          f"   in a score when query and key both move along by 1, 7 or 1000 places  {moved:.3g}\n"
          f"   in a vector's length                                                    {length:.3g}\n"
          f"   between the paper's pairs (neighbours) and ours, the numbers reordered  "
          f"{(paper - ours).abs().max().item():.3g}\n"
          f"   (and between the scores turned and not turned                           {unturned:.3g})")

    variants = {"learned": {}, "rotary": {"positions": "rotary"}}
    common = dict(vocab=V, context=cfg.context, layers=cfg.layers, heads=cfg.heads, width=cfg.width)
    got = compare(variants, common, cfg, dev, train_t, test_t)
    a, b = got["learned"], got["rotary"]
    print(f"\n2. 08.04's GPT ({cfg.layers} blocks of {cfg.heads} heads, width {cfg.width}, windows of {cfg.context}), "
          f"{cfg.steps} steps of {cfg.batch}, {cfg.seeds} seeds; bits per character on the test text\n"
          f"   (each character with {cfg.context // 4} or more before it), and ms a training step:")
    for name, r in got.items():
        print(f"   {name:9s} {r['weights']:>9,} weights   bits {lab.spread(r['bits'], 4)}\n"
              f"   {'':30s}ms a step {lab.spread(r['ms'], 3)}")
    print(f"   rotary against learned: bits {lab.mean(b['bits']) - lab.mean(a['bits']):+.4f}, "
          f"t = {lab.welch_t(b['bits'], a['bits']):+.1f}; time a step x{lab.mean(b['ms']) / lab.mean(a['ms']):.3f}, "
          f"t = {lab.welch_t(b['ms'], a['ms']):+.1f}; {a['weights'] - b['weights']:,} weights fewer "
          f"(the table of {cfg.context} places)")

    print(f"\n3. Past the length trained on ({cfg.context}), seed 0's models:")
    long = cfg.context * max(cfg.longer)
    try:
        a["models"][0](test_t[None, :long])
    except ValueError as e:
        print(f"   learned positions, a window of {long}: ValueError: {e}")
    model = b["models"][0]
    print(f"   rotary positions, windows of n times {cfg.context}; bits per character at the positions of each part:")
    for n in [1] + cfg.longer:
        length = cfg.context * n
        starts = torch.arange(0, len(test_t) - length - 1, length, device=dev)
        xs, ys = windows(test_t, starts, length)
        with torch.no_grad():
            scores = model(xs)
        parts = [(0, cfg.context)] + [(cfg.context * 2 ** j, cfg.context * 2 ** (j + 1)) for j in range(8)
                                      if cfg.context * 2 ** (j + 1) <= length]
        print(f"   n = {n}: " + "   ".join(f"{lo:3d} to {hi - 1:3d}: {bits(scores[:, lo:hi], ys[:, lo:hi]).item():.3f}"
                                         for lo, hi in parts))
    print(f"\n{lab.clock(torch, dev) - start:.0f} s of training and scoring on {dev.type}")


if __name__ == "__main__":
    main()
