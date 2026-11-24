"""RMSNorm: normalising with less.

Layer norm (04.04) does two things to each vector before a layer reads it:
it takes the vector's mean away (re-centring) and divides by its spread
(re-scaling). Zhang and Sennrich (2019) "hypothesize that the re-scaling
invariance is the reason for success of LayerNorm, rather than
re-centering invariance", and drop the first: RMSNorm divides each vector
by the root of the mean of its squares (models/gpt.py). Their claim, in
the abstract: "RMSNorm achieves comparable performance against LayerNorm
but reduces the running time by 7%~64% on different models." Here, on
08.04's GPT and Tiny Shakespeare:

1. RMSNorm against PyTorch's own (torch.nn.RMSNorm) and the formula.
2. The norm alone, forward and backward, at the GPT's size and at
   SmolLM2's (10.04): PyTorch's layer norm (one kernel), layer norm
   written out as RMSNorm is, RMSNorm, and PyTorch's RMSNorm.
3. The GPT with layer norm and with RMSNorm, every norm of it: bits per
   character on the test text, ms a training step, weights; a few seeds.
4. What the mean did: how far from centred the vectors are that each
   norm reads, in both trained models; and the layer-norm model scored
   again with its norms no longer taking the mean away.

    python3 -m experiments.rmsnorm
"""

import copy
import math

import torch
from torch import nn

import lab
from data import shakespeare
from experiments.language import compare
from experiments.sequences import window_bits, windows
from models.gpt import RMSNorm

CONFIG = dict(layers=4, heads=4, width=64, context=64, batch=32, steps=150, lr=0.003, warmup=50, weight_decay=0.1,
              clip=1.0, every=50, seeds=3, repeats=100, big=[8, 512, 576], device="cpu")


# @build 10.01 written_layer_norm
# Layer norm written out with the same operations as RMSNorm, for timing
# the two alike: each vector minus its mean, over the root of its
# variance plus eps, times the gain plus the bias. nn.LayerNorm computes
# the same numbers in one kernel of its own.
def written_layer_norm(x, weight, bias, eps=1e-5):
    x = x - x.mean(-1, keepdim=True)
    return x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + eps) * weight + bias
# @end


# @build 10.01 norm_times
# The time of each of norms (name -> a function of x) on x, forward and
# backward (the gradient of the sum of its output), in ms: `repeats`
# times each, the norms taking turns so the machine's load falls on all
# alike, and the median of each.
def norm_times(norms, x, repeats, dev):
    times = {name: [] for name in norms}
    x = x.detach().requires_grad_()
    for _ in range(repeats):
        for name, norm in norms.items():
            start = lab.clock(torch, dev)
            norm(x).sum().backward()
            times[name].append(1000 * (lab.clock(torch, dev) - start))
            x.grad = None
    return {name: sorted(t)[len(t) // 2] for name, t in times.items()}
# @end


# @build 10.01 centring
# How far from centred the vectors are that each norm of model (a GPT)
# reads when it reads windows x: for each norm in order (each block's
# norm1 and norm2, then the last), the mean over every vector it reads of
# |mean| / rms, the vector's mean over its numbers beside the root of the
# mean of their squares (0: centred; 1: all its numbers the same). Read
# with forward hooks, in eval mode, without a graph.
def centring(model, x):
    norms = [m for b in model.blocks for m in (b.norm1, b.norm2)] + [model.norm]
    seen = [[] for _ in norms]
    hooks = [n.register_forward_hook(lambda m, inp, out, k=k: seen[k].append(
        (inp[0].mean(-1).abs() / inp[0].pow(2).mean(-1).sqrt()).mean().item())) for k, n in enumerate(norms)]
    model.eval()
    with torch.no_grad():
        model(x)
    for h in hooks:
        h.remove()
    return [s[0] for s in seen]
# @end


# @build 10.01 uncentred
# A copy of a GPT whose layer norms (nn.LayerNorm) no longer take the
# mean away: each divides by the root mean square instead of the spread
# about the mean, and keeps its trained gain and bias. Nothing else
# changes, so the copy scores what the mean step was doing.
def uncentred(model):
    model = copy.deepcopy(model)
    for n in [m for m in model.modules() if isinstance(m, nn.LayerNorm)]:
        n.forward = lambda x, n=n: x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + n.eps) * n.weight + n.bias
    return model
# @end


def main():
    cfg = lab.config(CONFIG)
    dev = lab.device(torch, cfg.device)
    V = len(shakespeare.chars())
    train_t, test_t = (torch.from_numpy(shakespeare.split(s)).to(dev) for s in ("train", "test"))
    start = lab.clock(torch, dev)

    torch.manual_seed(0)
    x = 3 * torch.randn(4, 16, cfg.width, dtype=torch.float64, device=dev) + 1
    ours = RMSNorm(cfg.width).double().to(dev)
    with torch.no_grad():
        ours.weight.normal_()
    theirs = nn.RMSNorm(cfg.width, eps=1e-5).double().to(dev)
    theirs.weight.data.copy_(ours.weight.data)
    formula = x / torch.sqrt((x ** 2).sum(-1, keepdim=True) / cfg.width + 1e-5) * ours.weight
    print(f"1. RMSNorm on 64 vectors of {cfg.width} (float64), the largest difference from torch.nn.RMSNorm: "
          f"{(ours(x) - theirs(x)).abs().max().item():.3g}; from the formula: {(ours(x) - formula).abs().max().item():.3g}")
    one = torch.tensor([[3.0, 4.0, 0.0, 0.0], [5.0, 6.0, 7.0, 8.0]])
    print(f"   [3, 4, 0, 0]: root mean square {math.sqrt(25 / 4):g}, RMSNorm "
          f"{[round(v, 4) for v in RMSNorm(4)(one)[0].tolist()]}, layer norm "
          f"{[round(v, 4) for v in nn.LayerNorm(4)(one)[0].tolist()]}")
    print(f"   [5, 6, 7, 8]: RMSNorm {[round(v, 4) for v in RMSNorm(4)(one)[1].tolist()]}, "
          f"layer norm {[round(v, 4) for v in nn.LayerNorm(4)(one)[1].tolist()]}")

    print(f"\n2. The norm alone, forward and backward, ms (the median of {cfg.repeats}, the four taking turns):")
    for shape in ([cfg.batch, cfg.context, cfg.width], cfg.big):
        W = shape[-1]
        layer, rms, torch_rms = nn.LayerNorm(W).to(dev), RMSNorm(W).to(dev), nn.RMSNorm(W, eps=1e-5).to(dev)
        norms = {"nn.LayerNorm": layer, "layer norm written out": lambda x: written_layer_norm(x, layer.weight, layer.bias),
                 "RMSNorm (ours)": rms, "nn.RMSNorm": torch_rms}
        got = norm_times(norms, torch.randn(*shape, device=dev), cfg.repeats, dev)
        print(f"   {' x '.join(map(str, shape))} ({math.prod(shape):,} numbers): " +
              ", ".join(f"{name} {ms:.3f}" for name, ms in got.items()))
        print(f"      RMSNorm takes {got['RMSNorm (ours)'] / got['layer norm written out']:.2f} of the written-out "
              f"layer norm's time, {got['RMSNorm (ours)'] / got['nn.LayerNorm']:.2f} of nn.LayerNorm's")

    variants = {"layer norm": {}, "RMSNorm": {"norm": "rms"}}
    common = dict(vocab=V, context=cfg.context, layers=cfg.layers, heads=cfg.heads, width=cfg.width)
    got = compare(variants, common, cfg, dev, train_t, test_t)
    a, b = got["layer norm"], got["RMSNorm"]
    print(f"\n3. 08.04's GPT ({cfg.layers} blocks of {cfg.heads} heads, width {cfg.width}, windows of {cfg.context}), "
          f"{cfg.steps} steps of {cfg.batch}, {cfg.seeds} seeds; bits per character on the test text\n"
          f"   (each character with {cfg.context // 4} or more before it), and ms a training step:")
    for name, r in got.items():
        print(f"   {name:11s} {r['weights']:>9,} weights   bits {lab.spread(r['bits'], 4)}\n"
              f"   {'':32s}ms a step {lab.spread(r['ms'], 3)}")
    print(f"   RMSNorm against layer norm: bits {lab.mean(b['bits']) - lab.mean(a['bits']):+.4f}, "
          f"t = {lab.welch_t(b['bits'], a['bits']):+.1f}; time a step x{lab.mean(b['ms']) / lab.mean(a['ms']):.3f}, "
          f"t = {lab.welch_t(b['ms'], a['ms']):+.1f}; {a['weights'] - b['weights']:,} weights fewer "
          f"(the {2 * cfg.layers + 1} biases of the norms)")

    starts = torch.arange(0, len(test_t) - cfg.context - 1, 7 * cfg.context, device=dev)
    xs, _ = windows(test_t, starts, cfg.context)
    names = [f"block {i + 1} {n}" for i in range(cfg.layers) for n in ("norm1", "norm2")] + ["last norm"]
    print(f"\n4. What each norm reads, seed 0's models, {len(starts)} windows of the test text: |mean| / rms of a "
          f"vector, averaged\n   (0: centred; 1: every number the same):")
    print(f"   {'':12s} " + "  ".join(f"{n:>13s}" for n in names))
    for name in variants:
        print(f"   {name:12s} " + "  ".join(f"{v:13.3f}" for v in centring(got[name]["models"][0], xs)))
    warm = cfg.context // 4
    model = got["layer norm"]["models"][0]
    as_trained = window_bits(model, test_t, cfg.context - warm + 1, warm)
    without = window_bits(uncentred(model).eval(), test_t, cfg.context - warm + 1, warm)
    print(f"   The layer-norm model (seed 0), bits per character on the test text: {as_trained:.4f} as trained, "
          f"{without:.4f}\n   with every norm dividing by the root mean square without taking the mean away "
          f"(its gains and biases kept)")
    print(f"\n{lab.clock(torch, dev) - start:.0f} s of timing, training and scoring on {dev.type}")


if __name__ == "__main__":
    main()
