"""Bigger batches: accumulation, clipping and the learning rate.

A step's cost is not in proportion to its batch: a small batch leaves
the processor waiting on PyTorch's work around each operation, a larger
one keeps it busy, so tokens a second grow with the batch until the
processor is full. A batch too large for memory can still be had by
gradient accumulation: the batch cut into parts, each part's gradient
added up before the step. But more tokens a second is not sooner to a
target loss: a larger batch is a better estimate of the same gradient,
not a longer step, unless the rate grows with it.

1. Tokens a second against the batch, and the batch of 128 accumulated
   from 4 parts of 32.
2. Accumulation gives the gradient of the whole batch: exactly, in
   float64; and what dropout does to that.
3. The time to 11.01's target against the batch, the rate held and the
   rate scaled with the batch.
4. Clipping: how long the gradient is at each batch, how many steps the
   clip of 1 cuts, and the time to the target with it and without.

    python3 -m experiments.batches
"""

import numpy as np
import torch

import lab
from data import shakespeare
from experiments.language import race, train
from experiments.sequences import bits, windows
from lab import bench
from models.gpt import GPT

CONFIG = dict(layers=4, heads=4, width=64, context=64, kv_heads=2, batch=32, steps=600, lr=0.003, warmup=50,
              weight_decay=0.1, clip=1.0, every=10, held=32, target=3.0, seeds=2, sizes=[8, 16, 32, 64, 128],
              parts=4, batches=[16, 32, 64], scaled=[64], norm_steps=40, clip_batches=[16], repeats=3, number=2,
              device="cpu")
ALL_FOUR = dict(norm="rms", positions="rotary", mlp="swiglu")


# @build 11.05 accumulated
# The gradient of model's mean bits over a batch (x, y) when the batch is
# cut into `parts` equal parts, as train does with cfg.accumulate: each
# part's bits divided by parts, its backward pass adding into the same
# .grad. Returns every weight's gradient (a list, in model.parameters()'s
# order).
def accumulated(model, x, y, parts):
    model.zero_grad()
    for xs, ys in zip(x.chunk(parts), y.chunk(parts)):
        (bits(model(xs), ys) / parts).backward()
    return [p.grad.clone() for p in model.parameters()]
# @end


def norms(common, cfg, dev, ids, batch, steps):
    """The gradient's length before clipping at each of the first steps of a run at this batch (train's steps,
    AdamW at cfg.lr with warmup, clipped to cfg.clip)."""
    torch.manual_seed(0)
    model = GPT(**common).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=cfg.lr)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lab.warmup_cosine(cfg.warmup, cfg.steps))
    rng, out = np.random.default_rng(0), []
    for _ in range(steps):
        x, y = windows(ids, torch.from_numpy(rng.integers(0, len(ids) - cfg.context, batch)).to(dev), cfg.context)
        loss = bits(model(x), y)
        opt.zero_grad()
        loss.backward()
        out.append(torch.nn.utils.clip_grad_norm_(model.parameters(), cfg.clip).item())
        opt.step()
        sched.step()
    return out


def line(name, r):
    seconds = [s for s in r["seconds"] if s is not None]
    steps = [s for s in r["steps"] if s is not None]
    if not seconds:
        return f"   {name:26s} not reached in {lab.mean(r['bits']) and len(r['bits'])} seeds"
    return (f"   {name:26s} {lab.spread(seconds, 3):44s} s   {lab.mean(steps):5.0f} steps "
            f"{lab.mean(steps) * r['tokens'] / 1000:7.0f}k tokens   {lab.mean(r['ms']):6.1f} ms a step"
            + ("" if len(seconds) == len(r["seconds"]) else f"   ({len(seconds)} of {len(r['seconds'])} seeds)"))


def main():
    cfg = lab.config(CONFIG)
    dev = lab.device(torch, cfg.device)
    clock = lambda: lab.clock(torch, dev)                                            # noqa: E731
    V = len(shakespeare.chars())
    train_t, val_t = (torch.from_numpy(shakespeare.split(s)).to(dev) for s in ("train", "val"))
    start = clock()
    common = dict(vocab=V, context=cfg.context, layers=cfg.layers, heads=cfg.heads, width=cfg.width,
                  kv_heads=cfg.kv_heads, norm="rms", positions="rotary", mlp="swiglu")

    print(f"1. A training step of the baseline GPT against its batch, windows of {cfg.context}, the smallest of "
          f"{cfg.repeats} timings (load {bench.load_average():.1f}):")
    rates = {}
    for b in cfg.sizes + [cfg.sizes[-1]]:
        parts = cfg.parts if b == cfg.sizes[-1] and b in rates else 1
        torch.manual_seed(0)
        model = GPT(**common).to(dev)
        opt = torch.optim.AdamW(model.parameters(), lr=cfg.lr)
        x, y = windows(train_t, torch.arange(0, b * cfg.context, cfg.context, device=dev), cfg.context)

        def step():
            accumulated(model, x, y, parts)
            opt.step()
        t = min(bench.timings(step, clock, repeats=cfg.repeats, number=cfg.number))
        rates[b] = b * cfg.context / t
        print(f"   batch {b:4d}{f' in {parts} parts of {b // parts}' if parts > 1 else '':16s} {1000 * t:8.1f} ms a step  "
              f"{b * cfg.context / t:9,.0f} tokens a second")

    torch.manual_seed(0)
    model = GPT(**common).double()
    x, y = windows(train_t.cpu(), torch.arange(0, 32 * cfg.context, cfg.context), cfg.context)
    whole = accumulated(model, x, y, 1)
    gaps = {p: max((a - b).abs().max().item() for a, b in zip(accumulated(model, x, y, p), whole)) for p in (2, 4, 8, 32)}
    size = max(g.abs().max().item() for g in whole)
    torch.manual_seed(0)
    dropped = GPT(**common, dropout=0.1).double()
    torch.manual_seed(1)
    one = accumulated(dropped, x, y, 1)
    torch.manual_seed(1)
    four = accumulated(dropped, x, y, 4)
    torch.manual_seed(2)
    other = accumulated(dropped, x, y, 1)
    flat = lambda gs: torch.cat([g.flatten() for g in gs])                                 # noqa: E731
    trained = []
    for parts in (1, cfg.parts):
        torch.manual_seed(0)
        m = GPT(**common).double()
        c = lab.Config({**cfg, "steps": 5, "every": 1, "batch": 32, "accumulate": parts})
        run = lab.Run(c, 0, label=f"accumulate{parts}")
        train(m, c, run, torch.device("cpu"), train_t.cpu())
        trained.append((run.rows, list(m.parameters())))
    (rows1, w1), (rows4, w4) = trained
    print(f"\n2. The gradient of a batch of 32, float64, against the same batch in parts, the largest difference in "
          f"any weight's\n   (the largest gradient is {size:.3g}): "
          + ", ".join(f"{p} parts {g:.2g}" for p, g in gaps.items())
          + f"\n   train, 5 steps of 32 windows in one part and in {cfg.parts} (cfg.accumulate), float64: the largest "
          f"difference in a\n   logged loss {max(abs(a['bits'] - b['bits']) for a, b in zip(rows1, rows4)):.2g} bits, "
          f"in a weight {max((a - b).abs().max().item() for a, b in zip(w1, w4)):.2g}"
          + f"\n   With dropout 0.1, the same seed before each: 4 parts against 1, {(flat(four) - flat(one)).norm() / flat(one).norm():.3f} "
          f"of the gradient's length;\n   1 part with another seed against 1, {(flat(other) - flat(one)).norm() / flat(one).norm():.3f}: "
          f"other masks, as another seed's")

    held = windows(val_t, torch.from_numpy(np.random.default_rng(0).integers(0, len(val_t) - cfg.context, cfg.held))
                   .to(dev), cfg.context)
    print(f"\n3. Time to {cfg.target} bits on {cfg.held} validation windows against the batch, {cfg.seeds} seeds; "
          f"AdamW {cfg.lr} at batch {cfg.batch},\n   held, and for the batches in cfg.scaled scaled with the batch "
          f"(load {bench.load_average():.1f}):")
    results = {}
    for b in cfg.batches:
        for rule in ("held",) + (("scaled",) if b in cfg.scaled else ()):
            lr = cfg.lr if rule == "held" else cfg.lr * b / cfg.batch
            c = lab.Config({**cfg, "batch": b, "lr": lr})
            results[b, rule] = race({}, common, c, dev, train_t, held, label=f"batch{b}-{rule}")
            print(line(f"batch {b}, rate {lr:g}", results[b, rule]))

    print(f"\n4. Clipping at {cfg.clip}: the gradient's length over the first {cfg.norm_steps} steps, and how many of "
          f"them the clip cut:")
    for b in cfg.batches:
        n = norms(common, cfg, dev, train_t, b, cfg.norm_steps)
        print(f"   batch {b:4d}: median {np.median(n):.3f}, last 10 {np.median(n[-10:]):.3f}; clipped "
              f"{sum(v > cfg.clip for v in n)} of {len(n)}")
    for b in cfg.clip_batches:
        c = lab.Config({**cfg, "batch": b, "clip": 0.0})
        free = race({}, common, c, dev, train_t, held, label=f"batch{b}-noclip")
        print(line(f"batch {b}, rate {cfg.lr:g}, no clip", free))
        print(line(f"batch {b}, rate {cfg.lr:g}, clip {cfg.clip}", results[b, "held"]))
    print(f"\n{clock() - start:.0f} s of timing and training on {dev.type}")


if __name__ == "__main__":
    main()
