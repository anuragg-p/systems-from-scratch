"""One more optimisation, measured: a cache of keys and values for writing text.

08.05's generate reads the whole window again for every symbol it
writes: a forward pass over every position, of which only the last
position's scores are used. Every earlier position's keys and values
are the same as at the step before (each depends only on the symbols up
to it), so they can be kept: then each step runs the model on the one
new symbol, turned by rotary positions for its own place, and its query
reads the kept keys and values (models/gpt.py's Cache, experiments/
language.py's cached_scores; generate(..., cache=True)). Grouped heads
(10.04) keep fewer of them: SmolLM2's 3 key/value heads for 9 keep a
third.

1. How it was chosen: the profile of writing text. The time of a step
   of generate against the length of the window it reads.
2. The same tokens: generate with the cache against without, greedy and
   sampled, on a small GPT trained here (rotary positions, grouped
   heads) and on SmolLM2-135M; and the scores in float64.
3. Tokens a second against the length written, with and without.
4. What the cache holds: numbers a token, and bytes for a full window.

    python3 -m experiments.cache

Parts 1, 3 and 4 and SmolLM2's half of part 2 need SmolLM2's files:
python3 -m data.fetch smollm2 (271 MB, once).
"""

import torch

import lab
from data import fetch, shakespeare
from experiments.language import cached_scores, generate, train
from lab import bench
from models import smollm
from models.gpt import GPT
from tokens import smollm as tokens

CONFIG = dict(layers=4, heads=4, width=64, context=64, kv_heads=2, batch=32, steps=60, lr=0.003, warmup=20,
              weight_decay=0.1, clip=1.0, every=60, small_length=100, prompt="To be, or not to be,", length=32,
              windows=[16, 64, 256, 1024], lengths=[32, 64, 128, 256], repeats=3, prompt_tokens=16,
              methods=[["greedy", 0.0, 0, None], ["sampled", 1.0, 0, None], ["top-k=40", 1.0, 40, None],
                       ["nucleus, p=0.95", 1.0, 0, 0.95]], device="cpu")
ALL_FOUR = dict(norm="rms", positions="rotary", mlp="swiglu")


# @build 11.06 written
# Greedy writing, n symbols after prompt (1, P), each step timed: the
# scores at the last position from the whole window (cache False) or
# from cached_scores, the highest chosen. Returns the symbols and the
# seconds after each step, from the start (clock() before and after).
def written(model, prompt, n, clock, cache):
    ids, state, times = prompt, None, []
    start = clock()
    with torch.no_grad():
        for _ in range(n):
            if cache:
                scores, state = cached_scores(model, ids, state)
            else:
                scores = model(ids[:, -model.context:])[:, -1]
            ids = torch.cat([ids, scores.argmax(-1, keepdim=True)], dim=1)
            times.append(clock() - start)
    return ids[:, prompt.shape[1]:], times
# @end


def same_tokens(model, prompt, n, methods):
    """For each sampling method: generate's symbols with the cache against without, the same seed: equal?"""
    out = []
    for name, temperature, k, p in methods:
        a, b = (generate(model, prompt, n, torch.Generator().manual_seed(0), temperature, k or None, p, cache=c)
                for c in (False, True))
        out.append((name, torch.equal(a, b)))
    return out


def main():
    cfg = lab.config(CONFIG)
    dev = lab.device(torch, cfg.device)
    clock = lambda: lab.clock(torch, dev)                                            # noqa: E731
    V = len(shakespeare.chars())
    train_t, test_t = (torch.from_numpy(shakespeare.split(s)).to(dev) for s in ("train", "test"))
    start = clock()

    fetch.need("smollm2")
    model = smollm.load(dev)
    tok = tokens.load()
    C = smollm.CONFIG
    text = shakespeare.load()
    test_text = text[int(0.95 * len(text)):]
    ids = torch.tensor([tok.encode(test_text)[:max(cfg.windows)]], device=dev)
    print(f"1. Writing text without a cache: SmolLM2-135M ({C['layers']} blocks, {C['heads']} query heads on "
          f"{C['kv_heads']} key/value heads), one row, greedy.\n   A step reads the whole window and keeps the last "
          f"position's scores; the smallest of {cfg.repeats} timings (load {bench.load_average():.1f}):")
    for T in cfg.windows:
        x = ids[:, :T]
        with torch.no_grad():
            t = min(bench.timings(lambda: model(x)[:, -1], clock, repeats=cfg.repeats))
        print(f"   a window of {T:5d}: {1000 * t:8.1f} ms a step, {1000 * t / T:6.3f} ms a position, of which "
              f"{100 * (T - 1) / T:4.1f}% are positions whose scores are thrown away")

    torch.manual_seed(0)
    small = GPT(vocab=V, context=cfg.context, layers=cfg.layers, heads=cfg.heads, width=cfg.width,
                kv_heads=cfg.kv_heads, **ALL_FOUR).to(dev)
    train(small, cfg, lab.Run(cfg, 0, label="small"), dev, train_t)
    small.eval()
    p = test_t[None, :8]
    print(f"\n2. With the cache against without, the same seed: the same symbols?\n   A small GPT trained here "
          f"({cfg.steps} steps; rotary, {cfg.kv_heads} key/value heads for {cfg.heads}), {cfg.small_length} characters "
          f"after 8, past its window of {cfg.context}:")
    for name, same in same_tokens(small, p, cfg.small_length, cfg.methods):
        print(f"   {name:16s} {same}")
    double = GPT(vocab=V, context=cfg.context, layers=cfg.layers, heads=cfg.heads, width=cfg.width,
                 kv_heads=cfg.kv_heads, **ALL_FOUR).double().eval()
    double.load_state_dict(small.state_dict())
    whole, state, worst = test_t[None, :cfg.context].cpu(), None, 0.0
    with torch.no_grad():
        for n in range(8, cfg.context + 1):
            scores, state = cached_scores(double, whole[:, :n], state)
            worst = max(worst, (scores - double(whole[:, :n])[:, -1]).abs().max().item())
    print(f"   its scores in float64, cached against the whole window, at every length up to {cfg.context}: the largest "
          f"difference {worst:.2g}")
    prompt = torch.tensor([tok.encode(cfg.prompt)], device=dev)
    print(f"   SmolLM2-135M, {cfg.length} tokens after {cfg.prompt!r}:")
    for name, same in same_tokens(model, prompt, cfg.length, cfg.methods):
        print(f"   {name:16s} {same}")
    drawn = generate(model, prompt, cfg.length, None, 0, cache=True)
    print(f"   greedy, cached: {cfg.prompt + tok.decode(drawn[0].tolist())!r}")

    prompt = ids[:, :cfg.prompt_tokens]
    n = max(cfg.lengths)
    plain, t0 = written(model, prompt, n, clock, False)
    kept, t1 = written(model, prompt, n, clock, True)
    print(f"\n3. Greedy writing with SmolLM2-135M, one row, after {cfg.prompt_tokens} tokens of the test text, "
          f"without and with the cache (load {bench.load_average():.1f}):\n   the same tokens: {torch.equal(plain, kept)}")
    print(f"   {'written':>8s}   {'without: s':>10s} {'tokens/s':>9s} {'last step':>10s}   {'with: s':>8s} "
          f"{'tokens/s':>9s} {'last step':>10s}   {'faster':>7s}")
    for L in cfg.lengths:
        a, b = t0[L - 1], t1[L - 1]
        la, lb = t0[L - 1] - t0[L - 2], t1[L - 1] - t1[L - 2]
        print(f"   {L:8d}   {a:10.2f} {L / a:9.1f} {1000 * la:7.1f} ms   {b:8.2f} {L / b:9.1f} {1000 * lb:7.1f} ms   "
              f"x{a / b:6.2f}")

    kv, d, layers = C["kv_heads"], C["width"] // C["heads"], C["layers"]
    per = 2 * kv * d * layers
    print(f"\n4. What the cache holds: SmolLM2 keeps {per:,} numbers a token (keys and values, {kv} heads of {d}, "
          f"{layers} blocks),\n   {4 * per / 1024:.0f} KiB in float32; a full window of {C['context']} tokens "
          f"{4 * per * C['context'] / 2 ** 20:,.0f} MiB, where 9 key/value heads would keep "
          f"{4 * per * 3 * C['context'] / 2 ** 20:,.0f} MiB. GPT-2 small keeps {2 * 12 * 64 * 12:,} a token.")
    print(f"\n{clock() - start:.0f} s of loading, training, writing and timing on {dev.type}")


if __name__ == "__main__":
    main()
