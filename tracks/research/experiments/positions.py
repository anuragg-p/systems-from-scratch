"""Where am I: position embeddings.

Attention weighs positions by their keys, and a key is made from the
vector at a position, which says what character is there and nothing
about where it is. So a GPT without positions reads a window more like a
bag of characters than a line of text (Vaswani et al. 2017, section 3.5:
"Since our model contains no recurrence and no convolution, in order for
the model to make use of the order of the sequence, we must inject some
information about the relative or absolute position of the tokens in the
sequence."). GPT-2 adds a learned vector for each place, 0 to context -
1, to each character's embedding (models/gpt.py, GPT's positions). Here,
on Tiny Shakespeare:

1. Order: the scores at the last position of a window, and of the same
   window with the characters before the last shuffled, in float64. One
   block without positions gives the same scores for any order; with more
   blocks the mask itself lets order in (each position's first block saw a
   different set of characters); with positions every order differs.
2. Bits per character on the test text with and without learned
   positions, a few seeds each.
3. Past the context length: the model with positions has no vector for
   place `context` and stops; the model without them reads windows two
   and four times as long as any it was trained on.
4. Where each head looks with positions, beside 08.02's without.

    python3 -m experiments.positions
"""

import copy

import numpy as np
import torch

import lab
from data import shakespeare
from experiments.language import attention_maps, looks, train
from experiments.sequences import bits, window_bits, windows
from models.gpt import GPT

CONFIG = dict(width=64, context=32, batch=32, steps=300, lr=0.003, warmup=50, weight_decay=0.1, clip=1.0, every=100,
              seeds=3, layers=4, heads=4, orders=5, longer=[2, 4], device="cpu")


# @build 08.03 shuffled
# How much the scores at the last position of window x (a 1-d tensor)
# move when the characters before the last are put in other orders: the
# largest difference from the window's own scores over `orders` orders
# drawn from rng, computed in float64 on a copy of model.
def shuffled(model, x, orders, rng):
    exact = copy.deepcopy(model).double().eval()
    worst = 0.0
    with torch.no_grad():
        first = exact(x[None])[0, -1]
        for _ in range(orders):
            order = torch.from_numpy(rng.permutation(len(x) - 1)).to(x.device)
            y = torch.cat([x[:-1][order], x[-1:]])
            worst = max(worst, (exact(y[None])[0, -1] - first).abs().max().item())
    return worst
# @end


def main():
    cfg = lab.config(CONFIG)
    dev = lab.device(torch, cfg.device)
    V = len(shakespeare.chars())
    train_t, test_t = (torch.from_numpy(shakespeare.split(s)).to(dev) for s in ("train", "test"))
    start = lab.clock(torch, dev)
    warm = cfg.context // 2

    results, nets = {}, {}
    for layers, positions in ((1, False), (cfg.layers, False), (cfg.layers, True)):
        seeds = 1 if layers == 1 else cfg.seeds
        for seed in range(seeds):
            label = f"blocks{layers}-{'positions' if positions else 'none'}"
            run = lab.Run(cfg, seed, label=label)
            torch.manual_seed(seed)
            model = GPT(V, cfg.context, layers, cfg.heads, cfg.width, positions=positions).to(dev)
            train(model, cfg, run, dev, train_t)
            model.eval()
            got = window_bits(model, test_t, cfg.context - warm + 1, warm)
            run.finish(test_bits=got)
            results.setdefault((layers, positions), []).append(got)
            nets.setdefault((layers, positions), model)

    rng = np.random.default_rng(0)
    x = test_t[:cfg.context]
    print(f"1. The scores at the last of {cfg.context} test characters, the {cfg.context - 1} before it shuffled into "
          f"{cfg.orders} other orders (float64):")
    for (layers, positions), model in nets.items():
        name = f"{layers} block{'s' * (layers > 1)}, {'learned positions' if positions else 'no positions'}"
        print(f"   {name:32s} the largest change in a score: {shuffled(model, x, cfg.orders, rng):.3g}")

    print(f"\n2. Bits per character on the test text (each character with {warm} or more before it), {cfg.layers} "
          f"blocks of {cfg.heads} heads, width {cfg.width},\n   windows of {cfg.context}, {cfg.steps} steps of "
          f"{cfg.batch}, {cfg.seeds} seeds:")
    a, b = results[cfg.layers, False], results[cfg.layers, True]
    print(f"   no positions       {lab.spread(a, 4)}")
    print(f"   learned positions  {lab.spread(b, 4)}")
    print(f"   t = {lab.welch_t(b, a):+.1f}")

    print(f"\n3. Past the context length ({cfg.context}), seed 0's models:")
    long = cfg.context * max(cfg.longer)
    try:
        nets[cfg.layers, True](test_t[None, :long])
    except ValueError as e:
        print(f"   learned positions, a window of {long}: ValueError: {e}")
    print(f"   learned positions, reading only the last {cfg.context} characters before each (as trained): "
          f"{window_bits(nets[cfg.layers, True], test_t, cfg.context - warm + 1, warm):.3f} bits per character")
    model = nets[cfg.layers, False]
    print(f"   no positions, windows of n times {cfg.context}; bits per character at the positions of each part:")
    for n in [1] + cfg.longer:
        length = cfg.context * n
        starts = torch.arange(0, len(test_t) - length - 1, length, device=dev)
        xs, ys = windows(test_t, starts, length)
        with torch.no_grad():
            scores = model(xs)
        parts = [(0, cfg.context)] + [(cfg.context * 2 ** k, cfg.context * 2 ** (k + 1)) for k in range(8)
                                      if cfg.context * 2 ** (k + 1) <= length]
        print(f"   n = {n}: " + "   ".join(f"{lo:3d} to {hi - 1:3d}: {bits(scores[:, lo:hi], ys[:, lo:hi]).item():.3f}"
                                         for lo, hi in parts))

    print(f"\n4. Where each head looks with learned positions ({cfg.layers} blocks of {cfg.heads} heads, seed 0; "
          f"positions {warm} to {cfg.context - 1}):\n   how far back on average, weight on its own position, weight on "
          f"the one before")
    starts = torch.arange(0, len(test_t) - cfg.context - 1, 97, device=dev)
    xs, _ = windows(test_t, starts, cfg.context)
    for b, block in enumerate(looks(attention_maps(nets[cfg.layers, True], xs), warm)):
        print(f"   block {b + 1}: " + "   ".join(f"{back:5.1f} {own:.2f} {before:.2f}" for back, own, before in block))
    print(f"\n{lab.clock(torch, dev) - start:.0f} s of training and scoring on {dev.type}")


if __name__ == "__main__":
    main()
