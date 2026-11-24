"""Many heads, and the residual stream: blocks of a GPT, stacked.

08.01's model had one layer of attention. Here, on Tiny Shakespeare, a few
seeds each, bits per character on the test text:

1. The obvious way deeper: 08.01's attention, layer after layer (each
   layer's result is the next one's input), 1 layer against `layers`.
2. Blocks (models/gpt.py: Block, GPT): the residual stream. Each block
   reads a layer-normalised copy of the stream (04.04) and adds what its
   attention found back into it (04.05); then an MLP, the same way, which
   works on each position on its own. 1 block against `layers`.
3. Heads (Vaswani et al. 2017, section 3.2.2 and table 3, rows A): the
   width cut into `heads` pieces, each attending on its own, against one
   head over the whole width. The weights are the same in number: only
   how the queries, keys and values are cut changes.
4. Where each head of the deepest model looks, on windows of the test
   text: how far back on average, and how much weight it puts on its own
   position and on the one before. Seed 0's weights on one window go to
   its summary.json, for a figure.

These models have no positions yet (08.03): a head can choose what to
look at only by what is there, not by where it is.

    python3 -m experiments.heads
"""

import torch
from torch import nn

import lab
from data import shakespeare
from experiments.language import attention_maps, looks, train
from experiments.sequences import window_bits, windows
from models.gpt import GPT, SelfAttention

CONFIG = dict(width=64, context=32, batch=32, steps=300, lr=0.003, warmup=50, weight_decay=0.1, clip=1.0, every=100,
              seeds=2, layers=4, heads=4, shown=32, device="cpu")


# @build 08.02 Stack
# 08.01's attention made deeper the obvious way: the characters'
# embeddings, `layers` layers of self-attention (with `heads` heads), each
# reading the last one's result, and a Linear layer to the scores.
class Stack(nn.Module):
    def __init__(self, V, width, layers, heads):
        super().__init__()
        self.tokens = nn.Embedding(V, width)
        self.layers = nn.ModuleList(SelfAttention(width, heads) for _ in range(layers))
        self.out = nn.Linear(width, V)

    def forward(self, x):
        x = self.tokens(x)
        for layer in self.layers:
            x = layer(x)
        return self.out(x)
# @end


# @build 08.02 build
# The model of each row of the experiment: ("stack", layers, heads) is a
# Stack, ("blocks", layers, heads) a GPT of that many blocks and heads at
# cfg.width, no dropout, no positions (08.03).
def build(kind, layers, heads, cfg, V):
    if kind == "stack":
        return Stack(V, cfg.width, layers, heads)
    # @from 08.03
    return GPT(V, cfg.context, layers, heads, cfg.width, positions=False)
    # @else
    # return GPT(V, cfg.context, layers, heads, cfg.width)
    # @end
# @end


def main():
    cfg = lab.config(CONFIG)
    dev = lab.device(torch, cfg.device)
    V = len(shakespeare.chars())
    train_t, test_t = (torch.from_numpy(shakespeare.split(s)).to(dev) for s in ("train", "test"))
    start = lab.clock(torch, dev)
    rows = {"stack": [("stack", 1, 1), ("stack", cfg.layers, 1)],
            "blocks": [("blocks", 1, cfg.heads), ("blocks", cfg.layers, cfg.heads)],
            "heads": [("blocks", cfg.layers, 1), ("blocks", cfg.layers, cfg.heads)]}
    results, sizes, nets = {}, {}, {}
    warm = cfg.context // 2
    for row in dict.fromkeys(r for rs in rows.values() for r in rs):
        kind, layers, heads = row
        for seed in range(cfg.seeds):
            run = lab.Run(cfg, seed, label=f"{kind}{layers}-heads{heads}")
            torch.manual_seed(seed)
            model = build(kind, layers, heads, cfg, V).to(dev)
            train(model, cfg, run, dev, train_t)
            model.eval()
            got = window_bits(model, test_t, cfg.context - warm + 1, warm)
            extra = {}
            if row == ("blocks", cfg.layers, cfg.heads) and seed == 0:
                maps = attention_maps(model, test_t[None, :cfg.shown])
                extra["window"] = test_t[:cfg.shown].tolist()
                extra["weights"] = [[[[round(w, 4) for w in r] for r in head] for head in m[0].tolist()] for m in maps]
                nets[row] = model
            run.finish(test_bits=got, weights_count=sum(p.numel() for p in model.parameters()), **extra)
            results.setdefault(row, []).append(got)
            sizes[row] = sum(p.numel() for p in model.parameters())

    def line(row):
        kind, layers, heads = row
        name = (f"{layers} attention layer{'s' * (layers > 1)}" if kind == "stack" else
                f"{layers} block{'s' * (layers > 1)}, {heads} head{'s' * (heads > 1)}")
        return f"   {name:22s} {sizes[row]:8,d} weights   {lab.spread(results[row], 4)}"

    print(f"Bits per character on the test text (each character with {warm} or more before it), width {cfg.width}, "
          f"windows of {cfg.context},\n{cfg.steps} steps of {cfg.batch}, {cfg.seeds} seeds")
    titles = {"stack": "1. 08.01's attention, one layer after another:",
              "blocks": "2. Blocks: the residual stream, layer norm, attention and an MLP:",
              "heads": f"3. {cfg.layers} blocks: one head of {cfg.width} against {cfg.heads} heads of "
                       f"{cfg.width // cfg.heads}:"}
    for part, (a, b) in rows.items():
        print(f"\n{titles[part]}")
        print(line(a))
        print(line(b))
        print(f"   t = {lab.welch_t(results[b], results[a]):+.1f}")

    deepest = nets[("blocks", cfg.layers, cfg.heads)]
    starts = torch.arange(0, len(test_t) - cfg.context - 1, 97, device=dev)
    x, _ = windows(test_t, starts, cfg.context)
    print(f"\n4. Where each head looks ({cfg.layers} blocks of {cfg.heads} heads, seed 0; {len(starts)} windows of the "
          f"test text, positions {warm} to {cfg.context - 1}):\n   how far back on average, weight on its own "
          f"position, weight on the one before")
    for b, block in enumerate(looks(attention_maps(deepest, x), warm)):
        print(f"   block {b + 1}: " + "   ".join(f"{back:5.1f} {own:.2f} {before:.2f}" for back, own, before in block))
    every = range(warm, cfg.context)
    print(f"   (equal weights on every position from 0 to i: {sum(i / 2 for i in every) / len(every):.1f} back on "
          f"average, {sum(1 / (i + 1) for i in every) / len(every):.2f} on each)")
    print(f"\n{lab.clock(torch, dev) - start:.0f} s of training and scoring on {dev.type}")


if __name__ == "__main__":
    main()
