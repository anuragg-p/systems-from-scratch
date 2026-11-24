"""Attention without the big matrix.

self_attend (08.01) writes attention out: a (T, T) table of scores for
every head of every window, the mask, the softmax into a second (T, T)
table of weights, the weighted sum; the backward pass keeps the weights.
Each table is a pass over memory, and their size grows with the square of
the window. Dao et al. (2022), FlashAttention, compute the same sums in
one kernel that works through the keys block by block in fast memory,
never writes the table out, and works the weights out again in the
backward pass: "an IO-aware exact attention algorithm", measured on
NVIDIA GPUs (an A100: "3x speedup on GPT-2 (seq. length 1K)"). PyTorch's
F.scaled_dot_product_attention is such a kernel; GPT(fused=True) uses it
(models/gpt.py's fused_attend).

1. The same numbers, in float64: fused_attend against self_attend, with
   and without the mask and the division; a whole GPT's scores and
   gradients.
2. Attention alone, forward and backward, against the window's length:
   time, and the memory kept for the backward pass, written out against
   fused.
3. A whole training step of 11.01's baseline at a few window lengths.
4. Trained, written out and fused alike, from the same seeds: the bits
   on the test text, and the time a step.

    python3 -m experiments.fused
"""

import textwrap

import torch

import lab
from data import shakespeare
from experiments.language import compare
from experiments.sequences import bits
from lab import bench
from models.gpt import GPT, fused_attend, self_attend

CONFIG = dict(layers=4, heads=4, width=64, context=64, kv_heads=2, batch=32, steps=150, lr=0.003, warmup=50,
              weight_decay=0.1, clip=1.0, every=50, seeds=2, lengths=[64, 128, 256, 512, 1024], windows_a_batch=8,
              windows=[64, 256], repeats=5, device="cpu")
ALL_FOUR = dict(norm="rms", positions="rotary", mlp="swiglu")
CLAIM = ("Dao et al. (2022): \"FlashAttention trains Transformers faster than existing baselines: 15% end-to-end "
         "wall-clock speedup on BERT-large (seq. length 512) compared to the MLPerf 1.1 training speed record, 3x "
         "speedup on GPT-2 (seq. length 1K)\"; attention alone \"up to 3x faster than the PyTorch implementation\" "
         "and \"up to 20x more memory efficient\"; memory \"linear in sequence length\". Every number on NVIDIA GPUs "
         "(an A100 for these); none on a CPU.")


# @build 11.03 kept_bytes
# The bytes autograd keeps for the backward pass while work() runs: every
# tensor it saves passes through pack (a saved_tensors_hooks pair, which
# keeps it as it is), and each piece of memory is counted once, however
# many operations save it (the weights are saved by the softmax and by
# the product with the values). Returns (bytes, what work returned).
def kept_bytes(work):
    seen = {}

    def pack(t):
        seen[t.untyped_storage().data_ptr()] = t.untyped_storage().nbytes()
        return t
    with torch.autograd.graph.saved_tensors_hooks(pack, lambda t: t):
        out = work()
    return sum(seen.values()), out
# @end


def main():
    cfg = lab.config(CONFIG)
    dev = lab.device(torch, cfg.device)
    clock = lambda: lab.clock(torch, dev)                                            # noqa: E731
    V = len(shakespeare.chars())
    train_t, test_t = (torch.from_numpy(shakespeare.split(s)).to(dev) for s in ("train", "test"))
    start = clock()

    g = torch.Generator().manual_seed(0)
    q, k, v = (torch.randn(4, 3, 40, 16, dtype=torch.float64, generator=g) for _ in range(3))
    worst = max((fused_attend(q, k, v, m, s) - self_attend(q, k, v, m, s)[0]).abs().max().item()
                for m in (True, False) for s in (True, False))
    common = dict(vocab=V, context=cfg.context, layers=cfg.layers, heads=cfg.heads, width=cfg.width,
                  kv_heads=cfg.kv_heads, **ALL_FOUR)
    torch.manual_seed(0)
    written = GPT(**common).double()
    fused = GPT(**common, fused=True).double()
    fused.load_state_dict(written.state_dict())
    ids = test_t[:4 * (cfg.context + 1)].view(4, cfg.context + 1).cpu()
    grads = []
    for m in (written, fused):
        m.zero_grad()
        loss = bits(m(ids[:, :-1]), ids[:, 1:])
        loss.backward()
        grads.append([p.grad for p in m.parameters()])
    with torch.no_grad():
        scores = (written(ids[:, :-1]) - fused(ids[:, :-1])).abs().max().item()
    gap = max((a - b).abs().max().item() for a, b in zip(*grads))
    print(f"1. The same numbers, float64, the largest difference:\n"
          f"   fused_attend against self_attend, 4 x 3 heads x 40 positions of 16, mask and division on and off  {worst:.3g}\n"
          f"   the baseline GPT ({cfg.layers} blocks, width {cfg.width}), written out against fused: scores "
          f"{scores:.3g}, every gradient {gap:.3g}")

    B, H, d = cfg.windows_a_batch, cfg.heads, cfg.width // cfg.heads
    print(f"\n2. Attention alone, forward and backward, {B} windows x {H} heads of {d} on {dev.type} (load "
          f"{bench.load_average():.1f}); the smallest of {cfg.repeats}\n   timings, and the memory autograd keeps "
          f"for the backward pass (MiB):\n   {'length':>6s}   {'written out':>12s} {'kept':>9s}   {'fused':>10s} "
          f"{'kept':>8s}   {'faster':>7s}   {'the (T, T) weights':>18s}")
    for T in cfg.lengths:
        q, k, v = (torch.randn(B, H, T, d, device=dev, requires_grad=True) for _ in range(3))
        grad = torch.randn(B, H, T, d, device=dev)
        row = []
        for attend in (lambda: self_attend(q, k, v)[0], lambda: fused_attend(q, k, v)):
            kept, _ = kept_bytes(attend)
            t = bench.timings(lambda: attend().backward(grad), clock, repeats=cfg.repeats, number=max(1, 512 // T))
            row.append((min(t), kept))
        (a, ka), (b, kb) = row
        print(f"   {T:6d}   {1000 * a:9.2f} ms {ka / 2 ** 20:9.2f}   {1000 * b:7.2f} ms {kb / 2 ** 20:8.2f}   x{a / b:6.2f}"
              f"   {B * H * T * T * 4 / 2 ** 20:15.1f}")

    print(f"\n3. A whole training step of the baseline GPT (batches of {cfg.batch}), the smallest of {cfg.repeats} "
          f"timings (load {bench.load_average():.1f}):")
    for T in cfg.windows:
        ids = train_t[:cfg.batch * (T + 1)].view(cfg.batch, T + 1)
        row = []
        for f in (False, True):
            torch.manual_seed(0)
            m = GPT(**{**common, "context": T}, fused=f).to(dev)
            opt = torch.optim.AdamW(m.parameters(), lr=cfg.lr)

            def step():
                loss = bits(m(ids[:, :-1]), ids[:, 1:])
                opt.zero_grad()
                loss.backward()
                opt.step()
            row.append(min(bench.timings(step, clock, repeats=cfg.repeats, number=2)))
        print(f"   windows of {T:4d}: written out {1000 * row[0]:7.1f} ms, fused {1000 * row[1]:7.1f} ms, "
              f"x{row[0] / row[1]:.2f}; {cfg.batch * T / row[1]:,.0f} tokens a second fused")

    got = compare({"written out": {}, "fused": {"fused": True}}, common, cfg, dev, train_t, test_t)
    a, b = got["written out"], got["fused"]
    print(f"\n4. Trained alike ({cfg.steps} steps of {cfg.batch} windows of {cfg.context}, {cfg.seeds} seeds, the same "
          f"seeds and batches): bits per character on the test text")
    for name, r in got.items():
        print(f"   {name:12s} {lab.spread(r['bits'], 4):48s} ms a step {lab.spread(r['ms'], 3)}")
    print("   seed by seed, fused less written out: " + ", ".join(f"{y - x:+.2g}" for x, y in zip(a["bits"], b["bits"]))
          + f"; time a step x{lab.mean(b['ms']) / lab.mean(a['ms']):.3f}")
    print("\n   " + "\n   ".join(textwrap.wrap(CLAIM, 107)))
    print(f"\n{clock() - start:.0f} s of timing, training and scoring on {dev.type}")


if __name__ == "__main__":
    main()
