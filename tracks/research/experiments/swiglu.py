"""A gated MLP: SwiGLU.

08.02's MLP is a Linear layer up to 4 x width numbers, GELU, and a Linear
layer back. Shazeer (2020) replaces the first layer and its activation by
a gated linear unit (Dauphin et al. 2017): two layers up, one of them
through Swish (SiLU), multiplied number by number (models/gpt.py's
SwiGLU). That is three matrices where the MLP has two, so "To keep the
number of parameters and the amount of computation constant, we reduce
the number of hidden units d_ff ... by a factor of 2/3" (section 2). His
table 1 (a T5-sized model, C4, log-perplexity after 65,536 steps): FFN_GELU
1.983, FFN_SwiGLU 1.944. And section 4: "We offer no explanation as to why
these architectures seem to work; we attribute their success, as all else,
to divine benevolence." Here, on Tiny Shakespeare:

1. The weights counted: 08's MLP, and SwiGLU with the inner width cut to
   two thirds, at this GPT's width and at SmolLM2's.
2. Bits per character on the test text and ms a training step, 08.04's
   GPT with each, a few seeds.
3. What the gate does in the trained model: how many of the inner numbers
   it lets through, and how many it shuts.

    python3 -m experiments.swiglu
"""

import torch

import lab
from data import shakespeare
from experiments.language import compare
from experiments.sequences import windows
from models.gpt import MLP, SwiGLU

CONFIG = dict(layers=4, heads=4, width=64, context=64, batch=32, steps=150, lr=0.003, warmup=50, weight_decay=0.1,
              clip=1.0, every=50, seeds=3, device="cpu")


# @build 10.03 gates
# What the gates of a GPT with SwiGLU blocks do when it reads windows x:
# for each block, the share of the gate's numbers, silu(gate(x)), whose
# size is under 0.1 (shut: their product with up's numbers is near 0),
# and the share over 1 (open wider than the number up gives). Read with
# forward hooks on each block's gate layer, in eval mode, without a graph.
def gates(model, x):
    seen = []
    hooks = [b.mlp.gate.register_forward_hook(lambda m, inp, out: seen.append(torch.nn.functional.silu(out)))
             for b in model.blocks]
    model.eval()
    with torch.no_grad():
        model(x)
    for h in hooks:
        h.remove()
    return [((g.abs() < 0.1).float().mean().item(), (g.abs() > 1).float().mean().item()) for g in seen]
# @end


def main():
    cfg = lab.config(CONFIG)
    dev = lab.device(torch, cfg.device)
    V = len(shakespeare.chars())
    train_t, test_t = (torch.from_numpy(shakespeare.split(s)).to(dev) for s in ("train", "test"))
    start = lab.clock(torch, dev)

    print("1. The weights of one MLP: up and down to 4 x width (08.02), against SwiGLU's gate, up and down to "
          "8 x width / 3:")
    for W in (cfg.width, 576):
        h = 8 * W // 3
        for bias in (True, False):
            mlp, glu = sum(p.numel() for p in MLP(W, bias).parameters()), sum(p.numel() for p in SwiGLU(W, h, bias).parameters())
            print(f"   width {W:3d}, {'with biases   ' if bias else 'without biases'}: MLP (inner {4 * W:4d}) {mlp:9,}   "
                  f"SwiGLU (inner {h:4d}) {glu:9,}   difference {glu - mlp:+,}")

    variants = {"GELU MLP": {}, "SwiGLU": {"mlp": "swiglu"}}
    common = dict(vocab=V, context=cfg.context, layers=cfg.layers, heads=cfg.heads, width=cfg.width)
    got = compare(variants, common, cfg, dev, train_t, test_t)
    a, b = got["GELU MLP"], got["SwiGLU"]
    print(f"\n2. 08.04's GPT ({cfg.layers} blocks of {cfg.heads} heads, width {cfg.width}, windows of {cfg.context}), "
          f"{cfg.steps} steps of {cfg.batch}, {cfg.seeds} seeds; bits per character on the test text\n"
          f"   (each character with {cfg.context // 4} or more before it), and ms a training step:")
    for name, r in got.items():
        print(f"   {name:9s} {r['weights']:>9,} weights   bits {lab.spread(r['bits'], 4)}\n"
              f"   {'':30s}ms a step {lab.spread(r['ms'], 3)}")
    print(f"   SwiGLU against the GELU MLP: bits {lab.mean(b['bits']) - lab.mean(a['bits']):+.4f}, "
          f"t = {lab.welch_t(b['bits'], a['bits']):+.1f}; time a step x{lab.mean(b['ms']) / lab.mean(a['ms']):.3f}, "
          f"t = {lab.welch_t(b['ms'], a['ms']):+.1f}; weights {b['weights'] - a['weights']:+,}")

    starts = torch.arange(0, len(test_t) - cfg.context - 1, 7 * cfg.context, device=dev)
    xs, _ = windows(test_t, starts, cfg.context)
    print(f"\n3. The gates of seed 0's SwiGLU model on {len(starts)} windows of the test text, block by block: the share "
          f"of silu(gate) under 0.1\n   in size (shut) and over 1 (wide open):")
    for i, (shut, wide) in enumerate(gates(b["models"][0], xs)):
        print(f"   block {i + 1}: shut {shut:.3f}, wide open {wide:.3f}")
    print(f"\n{lab.clock(torch, dev) - start:.0f} s of training and scoring on {dev.type}")


if __name__ == "__main__":
    main()
