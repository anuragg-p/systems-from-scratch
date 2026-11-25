"""Lower precision: sixteen bits, and what breaks.

A float32 has 8 bits of exponent and 24 of precision. float16 keeps 5
and 11: numbers up to 65,504, steps of a thousandth near 1, nothing
below 2^-24. bfloat16 keeps float32's 8 bits of exponent and only 8 of
precision: the range of float32, steps of a hundredth near 1. Half the
bytes to move, and on hardware made for them, faster arithmetic:
Micikevicius et al. (2018) train in float16 "without losing model
accuracy", with three changes: a float32 master copy of the weights,
loss scaling, and float16 products summed in float32. PyTorch's autocast
runs the operations that gain from it in 16 bits and leaves the rest in
32 (cfg.precision in experiments/language.py's train).

1. What 16 bits cannot hold, shown exactly with numpy's float16 on this
   model's own numbers: the smallest step that still changes a weight
   against AdamW's steps, Adam's eps and its squared gradients, the
   gradients themselves, a softmax over large scores, and rotary's
   angles in bfloat16.
2. Autocast on this machine: which operations ran in 16 bits and which
   stayed in 32; the time of a step and of one matrix product in each
   type; the bits reached against float32's, trained alike.
3. Loss scaling: how many of the gradients float16 loses, without it
   and with it.

    python3 -m experiments.precision
"""

import collections
import math
import textwrap

import numpy as np
import torch
from torch.overrides import TorchFunctionMode

import lab
from data import shakespeare
from experiments.language import race, train
from experiments.sequences import bits, windows
from lab import bench
from models.gpt import GPT

CONFIG = dict(layers=4, heads=4, width=64, context=64, kv_heads=2, batch=32, steps=60, lr=0.003, warmup=10,
              weight_decay=0.1, clip=1.0, every=10, held=32, seeds=2, warm_steps=60, precisions=["float32", "bfloat16"],
              scales=[1, 1024, 65536], repeats=3, number=2, device="cpu")
ALL_FOUR = dict(norm="rms", positions="rotary", mlp="swiglu")
TYPES = {"float32": torch.float32, "bfloat16": torch.bfloat16, "float16": torch.float16}
CLAIM = ("Micikevicius et al. (2018): \"any value whose magnitude is smaller than 2^-24 becomes zero in FP16\"; a "
         "weight update is lost when \"the magnitude of a normalized weight value is at least 2048 times larger that "
         "of the weight update\"; loss scaling by 8 was enough for Multibox SSD, \"scaling factors ranging from 8 to "
         "32K (many networks did not require a scaling factor)\"; speed \"on recent GPUs\" (Volta).")


# @build 11.04 lost
# The share of updates that would change nothing if the weights were
# kept in 16 bits: weights w and the steps an optimiser made to them, u
# (numpy float32 arrays), both rounded to float16 (np.float16) and added
# in float16: lost where w + u is w again. Weights of 0 are left out.
def lost(w, u):
    w16 = w.astype(np.float16)
    keep = w16 != 0
    return float(((w16 + u.astype(np.float16)) == w16)[keep].mean())
# @end


# @build 11.04 Kinds
# Which operations ran in which type: a TorchFunctionMode (PyTorch's hook
# on every torch function called inside it) that counts each function by
# the types it took and the type it gave back, as autocast left them.
class Kinds(TorchFunctionMode):
    def __init__(self):
        super().__init__()
        self.seen = collections.Counter()

    def __torch_function__(self, func, types, args=(), kwargs=None):
        out = func(*args, **(kwargs or {}))
        if isinstance(out, torch.Tensor) and out.is_floating_point():
            took = sorted({str(a.dtype)[6:] for a in args if isinstance(a, torch.Tensor) and a.is_floating_point()})
            self.seen[getattr(func, "__name__", str(func)), "/".join(took), str(out.dtype)[6:]] += 1
        return out
# @end


def numbers(model, opt, x, y, lr):
    """One AdamW step of model on (x, y) at rate lr, in float32: the weights before it, the updates it made, the
    gradients, Adam's squared-gradient averages and the gradient of the stream at each block's output."""
    for group in opt.param_groups:
        group["lr"] = lr
    stream = []

    def keep(block, args, out):
        out.retain_grad()
        stream.append(out)
    hooks = [b.register_forward_hook(keep) for b in model.blocks]
    loss = bits(model(x), y)
    opt.zero_grad()
    loss.backward()
    for h in hooks:
        h.remove()
    before = [p.detach().clone() for p in model.parameters()]
    opt.step()
    flat = lambda ts: np.concatenate([t.detach().cpu().numpy().ravel() for t in ts])          # noqa: E731
    return dict(w=flat(before), u=flat(p.detach() - b for p, b in zip(model.parameters(), before)),
                g=flat(p.grad for p in model.parameters()), v=flat(opt.state[p]["exp_avg_sq"] for p in model.parameters()),
                stream=flat(s.grad for s in stream))


def main():
    cfg = lab.config(CONFIG)
    dev = lab.device(torch, cfg.device)
    clock = lambda: lab.clock(torch, dev)                                            # noqa: E731
    V = len(shakespeare.chars())
    train_t, val_t = (torch.from_numpy(shakespeare.split(s)).to(dev) for s in ("train", "val"))
    start = clock()
    common = dict(vocab=V, context=cfg.context, layers=cfg.layers, heads=cfg.heads, width=cfg.width,
                  kv_heads=cfg.kv_heads, **ALL_FOUR)
    held = windows(val_t, torch.from_numpy(np.random.default_rng(0).integers(0, len(val_t) - cfg.context, cfg.held))
                   .to(dev), cfg.context)

    f16, b16 = np.finfo(np.float16), torch.finfo(torch.bfloat16)
    print(f"1. What 16 bits hold. float16: largest {float(f16.max):,.0f}, smallest normal 2^{int(math.log2(f16.tiny))} "
          f"= {float(f16.tiny):.3g}, smallest at all 2^-24 = {2.0 ** -24:.3g},\n   steps of 2^{int(math.log2(f16.eps))} "
          f"near 1 (1 + 2^-11 is {float(np.float16(1) + np.float16(2.0 ** -11))!r}). bfloat16: largest {b16.max:.3g}, "
          f"smallest normal {b16.tiny:.3g},\n   steps of 2^{int(math.log2(b16.eps))} near 1 (1 + 2^-9 is "
          f"{(torch.tensor(1.0, dtype=torch.bfloat16) + 2.0 ** -9).item()!r}).")
    torch.manual_seed(0)
    model = GPT(**common).to(dev)
    warm = lab.Config({**cfg, "steps": cfg.warm_steps, "every": cfg.warm_steps})
    train(model, warm, lab.Run(warm, 0, label="warm"), dev, train_t)
    opt = torch.optim.AdamW(model.parameters(), lr=cfg.lr, weight_decay=0.0)
    x, y = windows(train_t, torch.from_numpy(np.random.default_rng(1).integers(0, len(train_t) - cfg.context,
                                                                               cfg.batch)).to(dev), cfg.context)
    late = cfg.lr * 0.5 * (1 + math.cos(math.pi * 0.95))
    print(f"   The baseline GPT after {cfg.warm_steps} steps, then one AdamW step at each rate (weights {sum(p.numel() for p in model.parameters()):,}):")
    for lr in (cfg.lr, late):
        n = numbers(model, opt, x, y, lr)
        w16 = np.abs(n["w"]).astype(np.float16)
        spacing = float(np.median(np.spacing(w16[w16 > 0])))
        w, u = torch.from_numpy(n["w"]).bfloat16(), torch.from_numpy(n["u"]).bfloat16()
        print(f"   rate {lr:.2g}: the median step {np.median(np.abs(n['u'])):.2g}, the median weight "
              f"{np.median(np.abs(n['w'])):.2g} (float16's steps there {spacing:.2g});\n"
              f"   {100 * lost(n['w'], n['u']):.1f}% of the updates would change nothing in float16, "
              f"{100 * ((w + u) == w)[w != 0].float().mean().item():.1f}% in bfloat16")
    v, g, s = n["v"], np.abs(n["g"]), np.abs(n["stream"])
    with np.errstate(divide="ignore"):
        inf = float(np.float16(1e-3) / (np.sqrt(np.float16(0)) + np.float16(1e-8)))
    print(f"   Adam's eps, 1e-8, in float16: {float(np.float16(1e-8))!r}. Its squared-gradient averages: "
          f"{100 * float((v.astype(np.float16) == 0).mean()):.1f}% are 0 in float16 ({100 * float((v == 0).mean()):.1f}% "
          f"in float32),\n   and where one is, its root plus eps is 0: an update of {inf!r}.")
    print(f"   The gradients: of the weights, {100 * float((g[g > 0] < 2.0 ** -24).mean()):.2f}% under 2^-24 (0 in float16), "
          f"{100 * float((g[g > 0] < 2.0 ** -14).mean()):.1f}% under 2^-14 (fewer bits);\n   of the stream at each block's "
          f"output, {100 * float((s[s > 0] < 2.0 ** -24).mean()):.2f}% and {100 * float((s[s > 0] < 2.0 ** -14).mean()):.1f}%"
          f" (largest {s.max():.2g}).")
    with torch.no_grad():
        a = model.blocks[-1].attention
        h = model.embed(x)
        for b in model.blocks[:-1]:
            h = b(h)
        q, k, _ = a.qkv(model.blocks[-1].norm1(h))
        scores = (q @ k.transpose(-2, -1) / math.sqrt(q.shape[-1])).cpu().numpy()
    big = np.float16(12.0)
    row = np.array([big, np.float16(0.0), np.float16(-3.0)], dtype=np.float16)
    with np.errstate(over="ignore", invalid="ignore"):
        naive, e12 = np.exp(row) / np.exp(row).sum(), float(np.exp(big))
    shifted = np.exp(row - row.max()) / np.exp(row - row.max()).sum()
    print(f"   A softmax: e^12 in float16 is {e12!r} (e^11.09 is about 65,504); scores [12, 0, -3] "
          f"give {[float(t) for t in naive]} written as e^s / sum,\n   {[round(float(t), 4) for t in shifted]} with the "
          f"largest taken away first (F.softmax does). This model's largest score in its last block: {np.abs(scores).max():.2f}.")
    angle = torch.arange(60.0, 61.0, 0.125)
    places = torch.tensor([255.0, 256.0, 257.0, 1000.0, 1001.0])
    print(f"   Rotary's angles in bfloat16: places {places.tolist()} become {places.bfloat16().float().tolist()}; "
          f"angles 60 to 60.875 radians\n   become {angle.bfloat16().float().tolist()} (models/gpt.py's Rotary makes "
          f"them in float32 under autocast).")

    print(f"\n2. Autocast on {dev.type} ({torch.get_num_threads()} threads):")
    for name in cfg.precisions[1:]:
        kinds = Kinds()
        with kinds, torch.autocast(dev.type, dtype=TYPES[name]):
            bits(model(x), y)
        sorts = collections.defaultdict(set)
        for (f, took, out) in kinds.seen:
            ins = "float32" if took == "float32" else ("mixed" if "float32" in took else ("16" if took else "none"))
            sorts["down" if ins == "float32" and out == name else "up" if ins != "float32" and out == "float32"
                  else "low" if out == name else "high"].add(f.strip("_"))
        print(f"   {name}, the functions of this model's forward pass and loss under autocast, by the types in and out:\n"
              f"     float32 in, 16 bits out: {', '.join(sorted(sorts['down']))}\n"
              f"     16 bits in, float32 out: {', '.join(sorted(sorts['up']))}\n"
              f"     16 bits in and out:      {', '.join(sorted(sorts['low'] - sorts['down']))}\n"
              f"     float32 in and out:      {', '.join(sorted(sorts['high'] - sorts['up']))}")
    a, b = torch.randn(2048, 256, device=dev), torch.randn(256, 256, device=dev)
    sizes = []
    for name in cfg.precisions:
        t = bench.timings(lambda: a.to(TYPES[name]) @ b.to(TYPES[name]), clock, repeats=cfg.repeats, number=5)
        sizes.append(f"{name} {1000 * min(t):.2f} ms")
    print("   One product, 2048 x 256 times 256 x 256: " + ", ".join(sizes) + f" (load {bench.load_average():.1f})")
    steps = {}
    for name in cfg.precisions:
        torch.manual_seed(0)
        m = GPT(**common).to(dev)
        o = torch.optim.AdamW(m.parameters(), lr=cfg.lr)

        def step(m=m, o=o, kind=TYPES[name]):
            with torch.autocast(dev.type, dtype=kind, enabled=kind != torch.float32):
                loss = bits(m(x), y)
            o.zero_grad()
            loss.backward()
            o.step()
        steps[name] = bench.timings(step, clock, repeats=cfg.repeats, number=cfg.number)
    print("   A training step: " + ", ".join(f"{k} {bench.spread_ms(v)}" for k, v in steps.items())
          + f" (load {bench.load_average():.1f})")
    print(f"   Trained alike, {cfg.steps} steps of {cfg.batch} windows, {cfg.seeds} seeds; bits on {cfg.held} validation "
          f"windows at the end:")
    trained = {}
    for name in cfg.precisions:
        c = lab.Config({**cfg, "precision": name, "target": 0.0})
        trained[name] = race({}, common, c, dev, train_t, held, label=name)
        print(f"   {name:9s} {lab.spread(trained[name]['bits'], 4):48s} ms a step {lab.spread(trained[name]['ms'], 3)}")
    first = cfg.precisions[0]
    for name in cfg.precisions[1:]:
        print(f"   {name} against {first}: {lab.mean(trained[name]['bits']) - lab.mean(trained[first]['bits']):+.4f}, "
              f"t = {lab.welch_t(trained[name]['bits'], trained[first]['bits']):+.1f}; time a step "
              f"x{lab.mean(trained[name]['ms']) / lab.mean(trained[first]['ms']):.2f}")

    print("\n3. Loss scaling. One backward pass under float16 autocast, against float32's: the share of the weights' "
          "gradients\n   float16 makes 0 where float32's are not, and the largest error of the rest, relative to "
          "float32's largest:")
    torch.manual_seed(0)
    model.zero_grad()
    bits(model(x), y).backward()
    want = [p.grad.clone() for p in model.parameters()]
    for scale in cfg.scales:
        model.zero_grad()
        with torch.autocast(dev.type, dtype=torch.float16):
            loss = bits(model(x), y)
        (loss * scale).backward()
        got = [p.grad / scale for p in model.parameters()]
        zero = sum(((a == 0) & (b != 0)).sum().item() for a, b in zip(got, want)) / sum(b.numel() for b in want)
        worst = max(((a - b).abs().max() / b.abs().max()).item() for a, b in zip(got, want))
        finite = all(torch.isfinite(a).all().item() for a in got)
        print(f"   the loss times {scale:6d}: {100 * zero:.3f}% made 0, largest error {worst:.2g}, every gradient "
              f"finite: {finite}")
    print("\n   " + "\n   ".join(textwrap.wrap(CLAIM, 107)))
    print(f"\n{clock() - start:.0f} s of training, timing and counting on {dev.type}")


if __name__ == "__main__":
    main()
