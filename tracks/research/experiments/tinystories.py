"""Pretraining on TinyStories: a model of a few million weights that tells a whole story.

Eldan and Li (2023) wrote millions of short stories with GPT-3.5 and
GPT-4, in the words a three or four year old knows, and found that on
them models "below 10 million total parameters" write "fluent and
consistent stories with several paragraphs". Here, on 64 MiB of their
stories, tokenised with 09.01's byte pair encoding learned on them:

1. The data: stories, tokens, bytes a token.
2. 08's GPT trained on it, a few seeds: its bits per byte on held-out
   stories (the validation file), and its curve.
3. Stories it writes, each from the symbol that starts a story, measured
   as code can measure them (the paper's grading by GPT-4 is not run):
   does the story end on its own (the model writes END), how long it is,
   does it end in a loop (08.05's repetition), and copying: the longest
   run of tokens it shares with the training text, beside the same for
   stories the model never saw.

The default run trains a small model briefly, which shows what a minute
gives; then, when there is one, the checkpoint of the long run (made with
the settings in experiments/recorded/tinystories/; NOTES.md has the
command), measured the same way. checkpoint=PATH takes another one,
checkpoint=none none.

    python3 -m experiments.tinystories

Needs TinyStories: python3 -m data.fetch tinystories (87 MB, once).
"""

import os

import numpy as np
import torch

import lab
from data import tinystories
from experiments.language import generate, load, loops, save, train
from experiments.sequences import per_character, window_bits, windows
from models.gpt import GPT
from tokens import bpe

CONFIG = dict(size=4096, layers=4, heads=4, width=128, context=128, batch=32, steps=120, lr=0.003, warmup=20,
              weight_decay=0.1, clip=1.0, every=20, seeds=2, held=32, held_stories=200, samples=8, length=300,
              temperature=1.0, shown=2, checkpoint="", device="cpu")
# Where the long run leaves its checkpoint (recorded with out=experiments/recorded), then the default run's.
CHECKPOINTS = ["experiments/recorded/tinystories/model.safetensors", "runs/tinystories/model.safetensors"]
MULTIPLIER = 0x9E3779B97F4A7C15                 # an odd 64-bit number: k-gram hashes as polynomials mod 2^64


# @build 09.04 tell
# Stories from model, one for each row of prompts (each row: END, the
# start of a story), at most `length` tokens each: 08.05's generate, a
# chunk of 32 tokens at a time, stopped once every row has written END.
# Each story is its tokens before the first END, and whether it wrote
# one: a list of (tokens, ended).
def tell(model, prompts, length, generator, temperature, end):
    drawn = prompts[:, :0]
    while drawn.shape[1] < length and not (drawn == end).any(1).all():
        more = generate(model, torch.cat([prompts, drawn], 1), min(32, length - drawn.shape[1]), generator, temperature)
        drawn = torch.cat([drawn, more], 1)
    out = []
    for row in drawn.tolist():
        out.append((row[:row.index(end)], True) if end in row else (row, False))
    return out
# @end


# @build 09.04 kgram_hashes
# A hash of every run of k tokens of ids (a numpy array), the i-th for
# the run that starts at i: its tokens as the digits of a number in base
# MULTIPLIER, kept to 64 bits (numpy's uint64 wraps around). Equal runs
# have equal hashes; different runs almost never do.
def kgram_hashes(ids, k):
    n = max(len(ids) - k + 1, 0)
    h = np.zeros(n, dtype=np.uint64)
    for j in range(k):
        h = h * np.uint64(MULTIPLIER) + ids[j:j + n].astype(np.uint64)
    return h
# @end


# @build 09.04 shared_run
# The longest run of tokens of story (a list) that ids (the training
# tokens) also has, as (where it starts in story, its length); runs
# shorter than k are not looked for (0). index is (the hashes of ids's
# runs of k, sorted; where each starts). For each start in story, every
# place ids has its k tokens (found by the hash, then checked token by
# token) is followed while it still agrees with the story; a start is
# skipped once the story has too few tokens left to beat the longest.
def shared_run(story, ids, index, k):
    hashes, order = index
    story = np.array(story, dtype=np.int64)
    best = (0, 0)
    for i, h in enumerate(kgram_hashes(story, k)):
        if len(story) - i <= best[1]:
            break
        lo, hi = np.searchsorted(hashes, h, "left"), np.searchsorted(hashes, h, "right")
        at = order[lo:hi]
        at = at[(ids[at[:, None] + np.arange(k)] == story[i:i + k]).all(1)] if len(at) else at
        n = k
        while len(at) and i + n < len(story):
            at = at[at + n < len(ids)]
            keep = at[ids[at + n] == story[i + n]]
            if not len(keep):
                break
            at, n = keep, n + 1
        if len(at) and n > best[1]:
            best = (i, n)
    return best
# @end


def copying(stories, train_ids, index, k, table):
    """For each story (a list of tokens): the longest run of tokens it shares with the training text, and that run's
    words; and the longest of them all, as text."""
    found = [(shared_run(s, train_ids, index, k), s) for s in stories]
    texts = [bpe.decode(s[i:i + n], table) for (i, n), s in found]
    longest = max(range(len(found)), key=lambda j: found[j][0][1])
    return [n for (_, n), _ in found], [len(t.split()) for t in texts], texts[longest]


def measure(model, cfg, dev, held, held_ids, table, end, train_ids, index, k, label):
    """A model's bits per byte on the held-out stories, and its stories, measured; prints and returns them."""
    warm = model.context // 4
    b = window_bits(model, held, model.context - warm + 1, warm)
    bpb = per_character(b, held_ids, table, warm)
    prompts = torch.full((cfg.samples, 1), end, device=dev)
    told = tell(model, prompts, cfg.length, torch.Generator().manual_seed(0), cfg.temperature, end)
    runs, words, longest = copying([s for s, _ in told], train_ids, index, k, table)
    out = dict(bits_per_byte=bpb, ended=sum(e for _, e in told), samples=len(told), tokens=[len(s) for s, _ in told],
               words=[len(bpe.decode(s, table).split()) for s, _ in told], looped=sum(loops(s) for s, _ in told),
               copied=runs, copied_words=words)
    print(f"\n   {label}\n   bits per byte on {cfg.held_stories:,} held-out stories: {bpb:.4f}\n"
          f"   {len(told)} stories at temperature {cfg.temperature}: {out['ended']} ended on their own (wrote END) within "
          f"{cfg.length} tokens; {out['looped']} ended in a loop.\n   Words each: {', '.join(map(str, out['words']))}\n"
          f"   The longest run of tokens each shares with the training text: {', '.join(map(str, runs))}\n"
          f"   (in words: {', '.join(map(str, words))}); the longest: {longest!r}")
    for s, ended in told[:cfg.shown]:
        text = bpe.decode(s, table).replace("\n", "\n      ")
        print(f"\n      {text}\n      [{'END' if ended else 'no END'}]")
    return out


def main():
    cfg = lab.config(CONFIG)
    dev = lab.device(torch, cfg.device)
    start = lab.clock(torch, dev)
    end = cfg.size - 1
    train_np = tinystories.tokens("train", cfg.size).astype(np.int64)
    valid_np = tinystories.tokens("valid", cfg.size).astype(np.int64)
    _, table = tinystories.tokenizer(cfg.size)
    table = {**table, end: b"\n"}                 # END stands for the line <|endoftext|>: one byte, as a line break
    stories = tinystories.stories("train")
    made = lab.clock(torch, dev) - start
    print(f"1. TinyStories: {len(stories):,} training stories, {len(train_np):,} tokens (a vocabulary of {cfg.size}: 256 "
          f"bytes, {cfg.size - 257} merges, END),\n   {sum(len(s.encode()) + 1 for s in stories) / len(train_np):.2f} bytes "
          f"a token; {len(tinystories.stories('valid')):,} held-out stories, {len(valid_np):,} tokens. ({made:.0f} s to "
          f"read and tokenise, or to read what was kept.)")

    cut = int(np.flatnonzero(valid_np == end)[cfg.held_stories - 1]) + 1
    held_ids = valid_np[:cut]
    held = torch.from_numpy(held_ids).to(dev)
    train_t = torch.from_numpy(train_np).to(dev)
    valid_t = torch.from_numpy(valid_np).to(dev)
    curve = windows(valid_t, torch.from_numpy(np.random.default_rng(0).integers(0, len(valid_np) - cfg.context - 1,
                                                                            cfg.held)).to(dev), cfg.context)
    config = dict(vocab=cfg.size, context=cfg.context, layers=cfg.layers, heads=cfg.heads, width=cfg.width,
                  dropout=0.0, bias=True, positions=True)
    results, lines, best = [], [], None
    warm = cfg.context // 4
    for seed in range(cfg.seeds):
        run = lab.Run(cfg, seed)
        torch.manual_seed(seed)
        model = GPT(**config).to(dev)
        train(model, cfg, run, dev, train_t, curve)
        model.eval()
        bpb = per_character(window_bits(model, held, cfg.context - warm + 1, warm), held_ids, table, warm)
        run.finish(bits_per_byte=bpb, end_held_bits=run.rows[-1]["held_bits"])
        results.append(bpb)
        if best is None or bpb < best[0]:
            best = (bpb, model, seed)
        lines.append(lab.Line(f"seed {seed}, held-out windows", [r["step"] for r in run.rows],
                              [r["held_bits"] for r in run.rows], seed, 0.8))
    size = sum(p.numel() for p in best[1].parameters())
    tokens_seen = cfg.steps * cfg.batch * cfg.context
    print(f"\n2. 08's GPT, {cfg.layers} blocks of {cfg.heads} heads, width {cfg.width}, windows of {cfg.context} tokens: "
          f"{size:,} weights.\n   {cfg.steps} steps of {cfg.batch} windows ({tokens_seen:,} tokens, "
          f"{tokens_seen / len(train_np):.2f} passes over the training stories), AdamW {cfg.lr}.\n"
          f"   Bits per byte on the first {cfg.held_stories:,} held-out stories: {lab.spread(results, 4)}")
    path = lab.lines(f"{cfg.out}/{cfg.name}/curves.svg", lines, title="bits per token on held-out windows",
                     xlabel="step", ylabel="bits per token")
    where = f"{cfg.out}/{cfg.name}/model.safetensors"
    save(best[1], config, where, steps=cfg.steps, seed=best[2], bits_per_byte=best[0])
    print(f"   curves in {path}; the best seed ({best[2]}) saved to {where}")

    found = ([] if cfg.checkpoint == "none" else [cfg.checkpoint] if cfg.checkpoint else
             [p for p in CHECKPOINTS if os.path.exists(p) and os.path.abspath(p) != os.path.abspath(where)])
    k = 8
    hashes = kgram_hashes(train_np, k)
    order = np.argsort(hashes)
    index = (hashes[order], order)
    print(f"\n3. Stories, each started from END, the symbol after which a new story begins (runs of fewer than {k} "
          f"tokens shared with the training text count as 0):")
    measured = {"trained here": measure(best[1], cfg, dev, held, held_ids, table, end, train_np, index, k,
                                        f"The model trained here (seed {best[2]}):")}
    if found:
        model, notes = load(found[0], dev)
        c = notes["config"]
        measured["checkpoint"] = measure(model, cfg, dev, held, held_ids, table, end, train_np, index, k,
                                         f"The checkpoint {found[0]}: {c['layers']} blocks of {c['heads']} heads, width "
                                         f"{c['width']}, windows of {c['context']}, {notes.get('steps', '?')} steps:")
    ends = np.flatnonzero(held_ids == end)[:cfg.samples]
    people, words, longest = copying([held_ids[a + 1:b].tolist() for a, b in zip([-1, *ends[:-1]], ends)], train_np,
                                     index, k, table)
    print(f"\n   The first {cfg.samples} held-out stories, which no model saw: the longest run of tokens each shares with "
          f"the training text:\n   {', '.join(map(str, people))} (in words: {', '.join(map(str, words))}); the longest: "
          f"{longest!r}")
    for label, out in measured.items():
        lab.Run(cfg, 0, label=f"stories-{label.replace(' ', '-')}").finish(**out)
    lab.Run(cfg, 0, label="stories-held-out").finish(copied=people, copied_words=words)
    print(f"\n{lab.clock(torch, dev) - start:.0f} s of tokenising, training, scoring and telling on {dev.type}")


if __name__ == "__main__":
    main()
