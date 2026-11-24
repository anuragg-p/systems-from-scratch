"""Bytes, UTF-8 and byte pair encoding: what a model reads, between characters and words.

1. The two obvious vocabularies, counted on Tiny Shakespeare: characters
   make a window short (how many words 08.04's 256 characters hold), and
   words leave out every word the training text never had (how many of
   the test text's words, and of its running words, are such).
2. Byte pair encoding (Sennrich et al. 2016) trained on the training
   text's bytes: the obvious trainer, timed, and the one that fits in a
   minute, with the same merges.
3. Bytes per token against the size of the vocabulary, on the training
   text and on the test text.
4. Any text round-trips, the test text and text in scripts the training
   text never had.
5. 08.04's GPT trained for the same steps on characters and on BPE
   tokens, both scored in bits per character on the test text.

    python3 -m experiments.bpe
"""

import re
import time
from collections import Counter

import numpy as np
import torch

import lab
from data import shakespeare
from experiments.language import train
from experiments.sequences import window_bits
from models.gpt import GPT
from tokens import bpe

CONFIG = dict(window=256, windows=2000, simple_merges=3, sizes=[256, 512, 1024, 2048, 4096], shown=24,
              vocab=2048, layers=4, heads=4, width=64, context=64, batch=32, steps=300, lr=0.003, warmup=50,
              weight_decay=0.1, clip=1.0, every=50, seeds=2, device="cpu")
WORD = re.compile(r"[A-Za-z]+")
# Text the training text never had: accents, Greek, Russian, Chinese, Hindi, an emoji with a skin tone, a flag, and
# a letter with a combining accent. Written as escapes, so that this file stays plain ASCII.
STRANGERS = ["naïve café, señor", "καλημέρα",
             "привет", "你好，世界",
             "नमस्ते", "\U0001f44b\U0001f3fd \U0001f1ec\U0001f1e7",
             "é and é", "tab\tnul\x00 and \x7f"]


# @build 09.01 unseen
# Of the words of `held` (a list), the share of different words that never
# occur in `seen` (another list), and the share of the running words, each
# occurrence counted, that are such: what a model with one symbol for each
# word of its training text could not write.
def unseen(seen, held):
    known = set(seen)
    different = set(held)
    return (sum(w not in known for w in different) / len(different),
            sum(w not in known for w in held) / len(held))
# @end


# @build 09.01 per_character
# A model's bits per token on text of tokens ids, made into bits per
# character: window_bits (07.03) scores every token from the warm-th on,
# so the bits of all of them over the characters they stand for (table
# gives each token's bytes; Tiny Shakespeare is ASCII, a byte a character).
def per_character(bits_per_token, ids, table, warm):
    scored = ids[warm:]
    return bits_per_token * len(scored) / sum(len(table[int(i)]) for i in scored)
# @end


def gpt_bits(cfg, dev, run, V, train_ids, test_ids, table):
    """08.04's GPT trained on train_ids for cfg.steps steps (the run's seed), then its bits per character on
    test_ids, each token scored with cfg.context / 4 or more before it."""
    torch.manual_seed(run.seed)
    model = GPT(V, cfg.context, cfg.layers, cfg.heads, cfg.width).to(dev)
    train(model, cfg, run, dev, torch.from_numpy(train_ids).to(dev))
    model.eval()
    warm = cfg.context // 4
    b = window_bits(model, torch.from_numpy(test_ids).to(dev), cfg.context - warm + 1, warm)
    return per_character(b, test_ids, table, warm)


def main():
    cfg = lab.config(CONFIG)
    dev = lab.device(torch, cfg.device)
    text = shakespeare.load()
    lo, mid, hi = (int(f * len(text)) for f in (0.9, 0.95, 1.0))
    train_text, test_text = text[:lo], text[mid:hi]
    start = lab.clock(torch, dev)

    words, held = WORD.findall(train_text), WORD.findall(test_text)
    rng = np.random.default_rng(0)
    counts = [len(WORD.findall(test_text[s:s + cfg.window]))
              for s in rng.integers(0, len(test_text) - cfg.window, cfg.windows)]
    share, running = unseen(words, held)
    print(f"1. Characters and words, on Tiny Shakespeare (a word: a run of letters).\n"
          f"   characters: {len(shakespeare.chars())} symbols; a window of {cfg.window} characters (08.04's) holds "
          f"{lab.mean(counts):.1f} words\n   on average ({min(counts)} to {max(counts)}, {cfg.windows} windows of the "
          f"test text).\n   words: the training text has {len(words):,} words, {len(set(words)):,} different ones. Of "
          f"the test text's\n   {len(set(held)):,} different words {100 * share:.1f}% never occur in training: "
          f"{100 * running:.1f}% of its {len(held):,} running words.")

    found = bpe.pieces(train_text)
    t = time.perf_counter()
    simple = bpe.train_simple(train_text, 256 + cfg.simple_merges)
    each = (time.perf_counter() - t) / cfg.simple_merges
    size = max(cfg.sizes)
    t = time.perf_counter()
    merges = bpe.train(train_text, size)
    fast = time.perf_counter() - t
    table = bpe.vocab(merges)
    same = list(merges.items())[:len(simple)] == list(simple.items())
    print(f"\n2. Byte pair encoding, trained on the training text ({len(train_text.encode()):,} bytes, {len(found):,} "
          f"pieces, {len(set(found)):,} different).\n   The obvious way, every pair counted again for every merge: "
          f"{each:.2f} s a merge,\n   so {size - 256:,} merges would take about {each * (size - 256) / 60:.0f} minutes.\n"
          f"   Each different piece counted once, the counts kept up to date: {len(merges):,} merges in {fast:.1f} s.\n"
          f"   Its first {len(simple)} merges are the obvious way's: {same}")
    learned = [table[i].decode() for i in merges.values()]
    print(f"   The first {cfg.shown} symbols it made: {' '.join(repr(s) for s in learned[:cfg.shown])}")
    print(f"   The last {cfg.shown // 2}: {' '.join(repr(s) for s in learned[-(cfg.shown // 2):])}")

    print("\n3. Bytes per token (a text's bytes over its tokens), by the size of the vocabulary:\n"
          "   vocabulary   training text   test text")
    pieces = Counter(found)
    for v in cfg.sizes:
        some = dict(list(merges.items())[:v - 256])
        tokens = sum(n * len(bpe.encode(p, some)) for p, n in pieces.items())
        print(f"   {v:10,}   {len(train_text) / tokens:13.3f}   {len(test_text) / len(bpe.encode(test_text, some)):9.3f}")

    ids = bpe.encode(test_text, merges)
    print(f"\n4. Round trips, with the vocabulary of {size}: the test text, {len(ids):,} tokens: "
          f"{bpe.decode(ids, table) == test_text}")
    for s in STRANGERS:
        got = bpe.encode(s, merges)
        print(f"   {ascii(s):58s} {len(s.encode()):3d} bytes, {len(got):3d} tokens, back the same: "
              f"{bpe.decode(got, table) == s}")

    some = dict(list(merges.items())[:cfg.vocab - 256])
    sub = bpe.vocab(some)
    chars = {i: c.encode() for i, c in enumerate(shakespeare.chars())}
    data = {"characters": (len(chars), shakespeare.encode(train_text), shakespeare.encode(test_text), chars),
            f"bpe{cfg.vocab}": (cfg.vocab, np.array(bpe.encode(train_text, some)),
                                np.array(bpe.encode(test_text, some)), sub)}
    results = {}
    for label, (V, train_ids, test_ids, symbols) in data.items():
        for seed in range(cfg.seeds):
            run = lab.Run(cfg, seed, label=label)
            got = gpt_bits(cfg, dev, run, V, train_ids, test_ids, symbols)
            run.finish(test_bits=got, vocab=V)
            results.setdefault(label, []).append(got)
    print(f"\n5. 08.04's GPT ({cfg.layers} blocks of {cfg.heads} heads, width {cfg.width}, windows of {cfg.context} "
          f"symbols), {cfg.steps} steps of {cfg.batch} windows,\n   on characters and on BPE tokens (a vocabulary of "
          f"{cfg.vocab}); bits per character on the test text:")
    for label, bits in results.items():
        per_step = cfg.batch * cfg.context * len(train_text) / len(data[label][1])
        print(f"   {label:12s} {lab.spread(bits, 4):52s} a step reads {per_step:,.0f} characters")
    a, b = results.values()
    print(f"   BPE against characters: t = {lab.welch_t(b, a):+.1f}")
    print(f"\n{lab.clock(torch, dev) - start:.0f} s of counting, training and scoring on {dev.type}")


if __name__ == "__main__":
    main()
