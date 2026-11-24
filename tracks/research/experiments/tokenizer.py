"""GPT-2's tokenizer, read from OpenAI's own files: the same ids as theirs.

1. What the files hold: 256 byte symbols, 50,000 merges in the order
   learned (the k-th makes symbol 256 + k: 09.01's form), and
   <|endoftext|>; the printable characters bytes are written as.
2. The pieces: GPT-2's pattern, with Unicode's letters and numbers made
   from unicodedata, against what re's own \\w would do.
3. Encoding: a few texts, their ids, and the round trip.
4. Bytes per token on Tiny Shakespeare: GPT-2's vocabulary, learned on
   web pages, against 09.01's, learned on Shakespeare's training text.
5. The speed of encoding, with and without the cache of pieces seen.

    python3 -m experiments.tokenizer
"""

import re
import time
import unicodedata
from collections import Counter

import lab
from data import shakespeare
from tokens import bpe, gpt2

CONFIG = dict(shown=12, size=4096, repeats=2)
SENTENCE = "Hello world! It's 2019, isn't it?  Yes...\n\n   NAME:\tna\u00efve 3.14 caf\u00e9s"
# Texts to encode (non-ASCII written as escapes, so that this file stays plain ASCII): a famous single token, digits,
# a contraction in capitals, another script, an emoji, and a letter Unicode added in version 16.0 (U+1C89), which
# this Python's unicodedata may not know.
EXAMPLES = ["Hello world", " SolidGoldMagikarp", "1234567890", "IT'S", "\u4f60\u597d", "\U0001f44b\U0001f3fd",
            "\u1c89's"]


def main():
    cfg = lab.config(CONFIG)
    start = time.perf_counter()
    tok = gpt2.load()
    symbols = gpt2.byte_symbols()
    first = list(tok.merges.items())[:cfg.shown]
    print(f"1. GPT-2's files: {len(tok.table):,} symbols, {len(tok.merges):,} merges; the k-th merge makes symbol "
          f"256 + k (checked), and {gpt2.END} is {tok.table[gpt2.END].decode()}.\n"
          f"   A space is written {ascii(symbols[32])}, a newline {ascii(symbols[10])}, the byte 0xe9 "
          f"{ascii(symbols[0xE9])}.\n   The first {cfg.shown} merges: "
          + "  ".join(f"{tok.table[a]!r}+{tok.table[b]!r}" for (a, b), _ in first))
    longest = max(tok.table, key=lambda i: len(tok.table[i]))
    print(f"   The longest symbol, {longest}, is {len(tok.table[longest])} bytes: {tok.table[longest][:24]!r}...")

    c = gpt2.classes()
    print(f"\n2. The pieces. This Python's unicodedata is Unicode {unicodedata.unidata_version}: "
          f"{sum(1 for i in range(0x110000) if unicodedata.category(chr(i))[0] == 'L'):,} letters in "
          f"{c['L'].count(chr(92) + 'U') :,} runs,\n   "
          f"{sum(1 for i in range(0x110000) if unicodedata.category(chr(i))[0] == 'N'):,} numbers in "
          f"{c['N'].count(chr(92) + 'U'):,} runs.")
    print(f"   GPT-2's pattern:     {' '.join(ascii(p) for p in gpt2.split(SENTENCE))}")
    print(f"   09.01's, with re's \\w: {' '.join(ascii(p) for p in bpe.pieces(SENTENCE))}")

    print("\n3. Encoding:")
    for s in EXAMPLES:
        ids = tok.encode(s)
        print(f"   {ascii(s):22s} {str(ids):38s} {' '.join(repr(tok.table[i]) for i in ids)[:60]}")
    print(f"   U+1C89 is {unicodedata.category(chr(0x1C89))} here ({'unassigned' if unicodedata.category(chr(0x1C89)) == 'Cn' else 'assigned'}), "
          f"so {ascii(chr(0x1C89) + chr(39) + 's')} is cut {' '.join(ascii(p) for p in gpt2.split(chr(0x1C89) + chr(39) + 's'))}")
    text = shakespeare.load()
    ids = tok.encode(text)
    print(f"   All of Tiny Shakespeare, {len(text):,} bytes: {len(ids):,} tokens, decoded the same: "
          f"{tok.decode(ids) == text}")

    lo, mid = int(0.9 * len(text)), int(0.95 * len(text))
    parts = {"training text": text[:lo], "test text": text[mid:]}
    merges = bpe.train(parts["training text"], cfg.size)
    found = Counter(bpe.pieces(parts["training text"]))
    ours = {"training text": sum(n * len(bpe.encode(p, merges)) for p, n in found.items()),
            "test text": len(bpe.encode(parts["test text"], merges))}
    print(f"\n4. Bytes per token on Tiny Shakespeare:\n   {'':16s} {'GPT-2 (' + format(len(tok.table), ',') + ')':>14s}"
          f"   09.01's ({cfg.size:,}, learned on the training text)")
    for name, part in parts.items():
        print(f"   {name:16s} {len(part) / len(tok.encode(part)):14.3f}   {len(part) / ours[name]:8.3f}")

    print(f"\n5. Encoding all of Tiny Shakespeare ({len(text) / 1e6:.2f} MB), best of {cfg.repeats}:")
    for cache in (False, True):
        times = []
        for _ in range(cfg.repeats):
            tok.cache = {}
            t = time.perf_counter()
            again = tok.encode(text, cache=cache)
            times.append(time.perf_counter() - t)
        assert again == ids
        print(f"   {'with' if cache else 'without':7s} the cache: {min(times):.2f} s, {len(text) / min(times) / 1e6:.2f} MB a "
              f"second" + (f" ({len(tok.cache):,} different pieces kept)" if cache else ""))
    pieces = gpt2.split(text)
    print(f"   The text is {len(pieces):,} pieces, {len(set(pieces)):,} of them different: most of the work without the "
          f"cache is merging the same pieces again.")
    print(f"\n{time.perf_counter() - start:.0f} s of reading, training and encoding on cpu")


if __name__ == "__main__":
    main()
