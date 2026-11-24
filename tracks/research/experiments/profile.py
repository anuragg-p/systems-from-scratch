"""Where a step goes: profiling.

A training step is many small pieces of work: picking the batch, the
forward pass through the embedding, the norms, attention, the MLP and
the scores, the loss, the backward pass, clipping, the optimiser. Before
making any of it faster, find out which pieces the time goes to. Two
ways, on 10.05's "all four" GPT (11.01's baseline):

1. Plain timers: the clock read before and after each piece of the
   forward pass (hooks on the model's layers), and around the backward
   pass, the clipping and the optimiser step; the mean over steps.
2. PyTorch's profiler on the same steps: every operation PyTorch runs,
   how many times and for how long, each put under the piece it ran in.
   Where the two disagree, and why.
3. What 10.02 left: rotary positions make their angles again on every
   call. Their share of a step, and the step with them kept (models/
   gpt.py's Rotary.angles): the same numbers bit for bit, and the time.

    python3 -m experiments.profile
"""

import collections

import numpy as np
import torch
from torch.profiler import ProfilerActivity, profile, record_function

import lab
from data import shakespeare
from experiments.sequences import bits, windows
from lab import bench
from models.gpt import GPT, Rotary

CONFIG = dict(layers=4, heads=4, width=64, context=64, kv_heads=2, batch=32, lr=0.003, clip=1.0, steps=10,
              repeats=5, number=4, rounds=3, shown=12, device="cpu")
ALL_FOUR = dict(norm="rms", positions="rotary", mlp="swiglu")
PARTS = ["data", "forward", "backward", "clipping", "optimiser"]
FORWARD = ["embedding", "norms", "attention: q, k, v and out", "attention: rotary", "attention: the rest", "MLP",
           "adds and dropout", "the last norm", "scores and loss"]


# @build 11.02 piece_of
# The piece of a forward pass a layer of a GPT belongs to, from its name
# in the model (named_modules), or None for one not timed on its own: the
# embeddings, the norms in the blocks and the last one, attention's four
# Linear layers, its rotary turning, attention whole (its rest is the
# whole less its parts), the MLP, and each block whole (less its parts:
# the adds into the stream and the dropout).
def piece_of(name):
    last = name.split(".")[-1]
    if name in ("tokens", "positions"):
        return "embedding"
    if name == "norm":
        return "the last norm"
    if last in ("norm1", "norm2"):
        return "norms"
    if ".attention." in name and last in ("query", "key", "value", "out"):
        return "attention: q, k, v and out"
    if name.endswith("attention.rotary"):
        return "attention: rotary"
    if last in ("attention", "mlp"):
        return "attention" if last == "attention" else "MLP"
    if name.startswith("blocks.") and last.isdigit():
        return "block"
    return None
# @end


# @build 11.02 timers
# Plain timers on a model's pieces: a forward pre-hook reads the clock as
# each named layer starts and a forward hook as it ends, and the seconds
# go to spent[its piece]. With labels, each layer also runs inside a
# record_function of its piece's name, so the profiler puts the
# operations it runs under that name. Returns the hooks' handles, to take
# them off again (handle.remove()).
def timers(model, clock, spent, labels=False):
    handles = []
    for name, layer in model.named_modules():
        piece = piece_of(name)
        if piece is None:
            continue
        started = []

        def before(layer, args, piece=piece, started=started):
            if labels:
                started.append(record_function(piece).__enter__())
            started.append(clock())

        def after(layer, args, out, piece=piece, started=started):
            spent[piece] += clock() - started.pop()
            if labels:
                started.pop().__exit__(None, None, None)
        handles += [layer.register_forward_pre_hook(before), layer.register_forward_hook(after)]
    return handles
# @end


# @build 11.02 where
# The profiler's operations put under the piece each ran in: for every
# PyTorch operation (aten::...), its own time (not its children's) goes
# to the nearest piece (a record_function of one of `names`) it ran
# inside. In the backward pass, the operations are under autograd's
# functions, named after the forward operation whose gradient they make
# (MulBackward0 is a multiply's): those names are kept too. Returns
# {piece: {operation: [calls, microseconds]}}.
def where(events, names):
    out = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0.0]))
    for e in events:
        if not e.name.startswith("aten::"):
            continue
        piece, up, grad = None, e.cpu_parent, None
        while up is not None and piece is None:
            if up.name in names:
                piece = up.name
            elif up.name.endswith(("Backward0", "Backward1")) and ":" not in up.name:
                grad = grad or up.name
            up = up.cpu_parent
        if piece is None:
            continue
        row = out[piece][grad or e.name]
        row[0] += 1
        row[1] += e.self_cpu_time_total
    return out
# @end


def step(model, opt, cfg, dev, ids, rng, clock, spent, label=False):
    """One training step, each of PARTS' seconds added to spent; with label, each inside a record_function."""
    def part(name, work):
        start = clock()
        if label:
            with record_function(name):
                out = work()
        else:
            out = work()
        spent[name] += clock() - start
        return out
    x, y = part("data", lambda: windows(ids, torch.from_numpy(rng.integers(0, len(ids) - cfg.context, cfg.batch))
                                         .to(dev), cfg.context))
    loss = part("forward", lambda: bits(model(x), y))
    opt.zero_grad()
    part("backward", loss.backward)
    part("clipping", lambda: torch.nn.utils.clip_grad_norm_(model.parameters(), cfg.clip))
    part("optimiser", opt.step)


def pieces(spent, steps):
    """The plain timers' sums as ms a step: PARTS, and the forward pass's FORWARD pieces (attention's rest is
    attention less its timed parts, the adds a block less its four parts, the scores and loss the forward pass
    less everything else)."""
    s = collections.defaultdict(float, {k: 1000 * v / steps for k, v in spent.items()})
    out = {k: s[k] for k in PARTS + FORWARD}
    out["attention: the rest"] = s["attention"] - s["attention: q, k, v and out"] - s["attention: rotary"]
    out["adds and dropout"] = s["block"] - s["norms"] - s["attention"] - s["MLP"]
    out["scores and loss"] = s["forward"] - s["embedding"] - s["block"] - s["the last norm"]
    return out


def main():
    cfg = lab.config(CONFIG)
    dev = lab.device(torch, cfg.device)
    clock = lambda: lab.clock(torch, dev)                                            # noqa: E731
    V = len(shakespeare.chars())
    train_t = torch.from_numpy(shakespeare.split("train")).to(dev)
    start = clock()
    common = dict(vocab=V, context=cfg.context, layers=cfg.layers, heads=cfg.heads, width=cfg.width,
                  kv_heads=cfg.kv_heads, **ALL_FOUR)

    Rotary.keep = False                     # parts 1 and 2: the model as 10.02 left it, angles made every call
    torch.manual_seed(0)
    model = GPT(**common).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=cfg.lr)
    rng = np.random.default_rng(0)

    def untimed():
        step(model, opt, cfg, dev, train_t, rng, clock, collections.defaultdict(float))
    untimed()
    spent = collections.defaultdict(float)
    handles = timers(model, clock, spent)
    load = bench.load_average()
    for _ in range(cfg.steps):
        step(model, opt, cfg, dev, train_t, rng, clock, spent)
    for h in handles:
        h.remove()
    timed = pieces(spent, cfg.steps)
    whole = sum(timed[k] for k in PARTS)
    plain = bench.timings(untimed, clock, repeats=cfg.repeats, number=cfg.number)
    print(f"1. One training step of 10.05's \"all four\" GPT ({cfg.layers} blocks of {cfg.heads} heads, width "
          f"{cfg.width}, {cfg.batch} windows of {cfg.context}),\n   plain timers, the mean of {cfg.steps} steps on "
          f"{dev.type} (load {load:.1f}), ms a step and the share of the step:")
    for k in PARTS:
        print(f"   {k:30s} {timed[k]:7.2f}  {100 * timed[k] / whole:5.1f}%")
        if k == "forward":
            for f in FORWARD:
                print(f"     {f:28s} {timed[f]:7.2f}  {100 * timed[f] / whole:5.1f}%")
    print(f"   {'the step':30s} {whole:7.2f}\n   the step without the timers: {bench.spread_ms(plain, bench.load_average())}"
          f"\n   the backward pass takes {timed['backward'] / timed['forward']:.2f} times the forward's time")

    labelled = collections.defaultdict(float)
    handles = timers(model, clock, labelled, labels=True)
    with profile(activities=[ProfilerActivity.CPU]) as prof:
        for _ in range(cfg.steps):
            step(model, opt, cfg, dev, train_t, rng, clock, labelled, label=True)
    for h in handles:
        h.remove()
    under = 1000 * sum(labelled[k] for k in PARTS) / cfg.steps
    events = prof.key_averages()
    own = {e.key: e.cpu_time_total / 1000 / cfg.steps for e in events}
    ops = sorted((e for e in events if e.key.startswith("aten::")), key=lambda e: -e.self_cpu_time_total)
    total = sum(e.self_cpu_time_total for e in ops) / 1000 / cfg.steps
    calls = sum(e.count for e in ops) / cfg.steps
    print(f"\n2. PyTorch's profiler on {cfg.steps} more steps. Under it a step takes {under:.2f} ms by the plain "
          f"timers ({whole:.2f} without it):\n   it records {calls:,.0f} operations a step, "
          f"{1000 * (under - whole) / calls:+.1f} microseconds each. Its times for the pieces, ms a step:")
    for k in ("data", "forward", "embedding", "norms", "attention", "attention: rotary", "MLP", "backward", "clipping",
              "optimiser"):
        print(f"   {k:30s} profiler {own.get(k, 0.0):7.2f}   plain timers, under it {1000 * labelled[k] / cfg.steps:7.2f}"
              f"   not under it {1000 * spent[k] / cfg.steps:7.2f}")
    print(f"   The {cfg.shown} operations with the most time of their own, a step: calls, ms, share of all "
          f"{total:.1f} ms of operations")
    for e in ops[:cfg.shown]:
        print(f"   {e.key:34s} {e.count / cfg.steps:6.0f} {e.self_cpu_time_total / 1000 / cfg.steps:7.2f}  "
              f"{100 * e.self_cpu_time_total / 1000 / cfg.steps / total:5.1f}%")
    places = where(prof.events(), set(PARTS) | set(FORWARD) | {"attention"})
    print("   Where they ran, ms a step (and how many operations): each piece's operations; in the backward pass,\n"
          "   autograd's functions, each named after the forward operation whose gradient it makes")
    for piece in ["attention", "attention: rotary", "MLP", "norms", "backward", "optimiser"]:
        rows = sorted(places[piece].items(), key=lambda kv: -kv[1][1])
        size = sum(v[1] for v in places[piece].values()) / 1000 / cfg.steps
        print(f"   {piece} {size:.2f}: " + ", ".join(f"{name.replace('aten::', '')} {us / 1000 / cfg.steps:.2f} "
                                                       f"({n / cfg.steps:,.0f})" for name, (n, us) in rows[:5]))

    rot = model.blocks[0].attention.rotary
    made = bench.timings(lambda: rot.angles(0, cfg.context, torch.float32, dev), clock, repeats=cfg.repeats, number=50)
    x = torch.randn(cfg.batch, cfg.heads, cfg.context, rot.d, device=dev, requires_grad=True)
    grad = torch.randn_like(x)
    turned = bench.timings(lambda: rot(x).backward(grad), clock, repeats=cfg.repeats, number=10)
    turns = 2 * cfg.layers
    print(f"\n3. Rotary positions: {turns} calls a step (each block's queries, then its keys), each making the "
          f"angles of {cfg.context} places again.\n   The angles alone: {1e6 * min(made):.1f} microseconds a call, "
          f"{1000 * turns * min(made):.2f} ms a step, {100 * turns * min(made) * 1000 / whole:.1f}% of it; the "
          f"turning, forward and backward,\n   {1000 * min(turned):.2f} ms a call, {1000 * turns * min(turned):.1f} ms "
          f"a step, {100 * turns * min(turned) * 1000 / whole:.1f}% of it")
    kept = {}
    for keep in (False, True):
        Rotary.keep = keep
        torch.manual_seed(0)
        m = GPT(**common).to(dev)
        o = torch.optim.AdamW(m.parameters(), lr=cfg.lr)
        r = np.random.default_rng(1)
        for _ in range(3):
            step(m, o, cfg, dev, train_t, r, clock, collections.defaultdict(float))
        kept[keep] = (m, o)
    same = all(torch.equal(a, b) for a, b in zip(kept[False][0].parameters(), kept[True][0].parameters()))
    print(f"   Kept (Rotary.keep = True), every weight after 3 steps as without, bit for bit: {same}")
    times = {False: [], True: []}
    for _ in range(cfg.rounds):
        for keep in (False, True):
            Rotary.keep = keep
            m, o = kept[keep]
            times[keep] += bench.timings(lambda: step(m, o, cfg, dev, train_t, rng, clock, collections.defaultdict(float)),
                                         clock, repeats=cfg.repeats, number=cfg.number)
    load = bench.load_average()
    for keep in (False, True):
        print(f"   {'kept' if keep else 'made every call':16s} a step {bench.spread_ms(times[keep], load)}")
    a, b = min(times[False]), min(times[True])
    print(f"   kept against made every call, the smallest of each: {1000 * (b - a):+.2f} ms a step, x{b / a:.3f}")
    Rotary.keep = True
    print(f"\n{clock() - start:.0f} s of timing and profiling on {dev.type}")


if __name__ == "__main__":
    main()
