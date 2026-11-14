#!/usr/bin/env python3
"""Inputs of any size, the same bytes on every machine and every run.

    python3 data/gen.py KIND N [--seed S] [-o FILE]

N counts the unit in brackets. The words come from data/book.txt; the
random choices from a generator of our own (splitmix64), so a seed always
gives the same bytes, whatever Python or machine runs it.

  text      [words] words of the book, picked at random, ten or so to a
            line, with commas and full stops; one word in ten is made up
            ("tavomi"), from a stock that grows with N, so the number of
            different words keeps growing with the text, as it does in a
            real library: n/12 or so of them, besides the book's 8000
  words     [words] the same words, one to a line
  lines     [lines] lines of one to eight words; long ones are all
            different, short ones repeat
  sorted    [lines] those lines, sorted byte by byte (as LC_ALL=C sort)
  reversed  [lines] the same, in reverse
  same      [lines] one line, N times
  numbers   [lines] whole numbers from -1000000 to 1000000, one in five
            with two decimal places
  fields    [lines] a word, a number and a word, between runs of one to
            three spaces: for sort -k
  dict      [lines] N different words, sorted byte by byte: a dictionary,
            for look

A tool can bring kinds of its own: a file tools/<name>/gen.py with KINDS
= {"kind": (make, "unit", "what it is")}, where make(n, rng) returns the
bytes of one file, or a list of bytes for a command that takes several.
"""

import glob
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BOOK = os.path.join(HERE, "book.txt")
MASK = (1 << 64) - 1


class Rand:
    """splitmix64: small, fast enough, and the same everywhere."""

    def __init__(self, seed):
        self.state = seed & MASK

    def next(self):
        self.state = (self.state + 0x9E3779B97F4A7C15) & MASK
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK
        return z ^ (z >> 31)

    def below(self, n):
        return self.next() % n


_book = None


def book_words():
    """Every word of the book, in order, as it is written (case kept)."""
    global _book
    if _book is None:
        with open(BOOK, "rb") as f:
            _book = [w.decode("ascii") for w in re.findall(rb"[A-Za-z]+", f.read())]
    return _book


SYLLABLES = ["ba", "be", "da", "di", "fo", "ga", "ka", "ke", "la", "li", "lo", "ma", "me", "mi", "na", "ne",
             "no", "pa", "po", "ra", "re", "ri", "ru", "sa", "se", "so", "ta", "te", "ti", "to", "va", "vo"]


def made_up(i):
    """The i-th made-up word: i written in base 32, a syllable a digit, three at least."""
    out = []
    while True:
        out.append(SYLLABLES[i % 32])
        i //= 32
        if i == 0 and len(out) >= 3:
            break
    return "".join(out)


class Words:
    """The stream of words text, words and lines are made of."""

    def __init__(self, n, rng):
        self.rng = rng
        self.book = book_words()
        self.stock = max(64, n // 4)       # made-up words to draw from

    def next(self):
        if self.rng.below(10) == 0:
            return made_up(self.rng.below(self.stock))
        return self.book[self.rng.below(len(self.book))]


def text(n, rng):
    ws, out, line, width, cap = Words(n, rng), [], [], 0, True
    for _ in range(n):
        w = ws.next()
        if cap:
            w = w[0].upper() + w[1:]
            cap = False
        r = rng.below(24)
        if r == 0:
            w, cap = w + ".", True
        elif r == 1:
            w += ","
        line.append(w)
        width += len(w) + 1
        if width > 66:
            out.append(" ".join(line))
            line, width = [], 0
    if line:
        out.append(" ".join(line))
    return lines_bytes(out)


def words(n, rng):
    ws = Words(n, rng)
    return lines_bytes(ws.next() for _ in range(n))


def _lines(n, rng):
    ws = Words(n * 4, rng)
    return [" ".join(ws.next() for _ in range(1 + rng.below(8))) for _ in range(n)]


def lines(n, rng):
    return lines_bytes(_lines(n, rng))


def sorted_lines(n, rng):
    return lines_bytes(sorted(_lines(n, rng)))


def reversed_lines(n, rng):
    return lines_bytes(sorted(_lines(n, rng), reverse=True))


def same(n, rng):
    return b"the same line, again and again\n" * n


def numbers(n, rng):
    out = []
    for _ in range(n):
        v = rng.below(2000001) - 1000000
        out.append(f"{v}.{rng.below(100):02d}" if rng.below(5) == 0 else str(v))
    return lines_bytes(out)


def fields(n, rng):
    book = book_words()
    out = []
    for _ in range(n):
        sp = [" " * (1 + rng.below(3)) for _ in range(2)]
        a, b = book[rng.below(len(book))].lower(), book[rng.below(len(book))].lower()
        out.append(f"{a}{sp[0]}{rng.below(1000)}{sp[1]}{b}")
    return lines_bytes(out)


def dict_words(n, rng):
    pool = sorted({w.lower() for w in book_words()})
    seen, i = set(pool), 0
    while len(pool) < n:                   # more than the book has: made-up words as well
        w = made_up(i)
        i += 1
        if w not in seen:
            seen.add(w)
            pool.append(w)
    for j in range(len(pool) - 1, 0, -1):  # shuffle (Fisher-Yates), keep n, sort them
        k = rng.below(j + 1)
        pool[j], pool[k] = pool[k], pool[j]
    return lines_bytes(sorted(pool[:n]))


def lines_bytes(it):
    return "".join(x + "\n" for x in it).encode("ascii")


KINDS = {
    "text": (text, "words", "words of the book, a line of ten or so at a time, with made-up words mixed in"),
    "words": (words, "words", "the same words, one to a line"),
    "lines": (lines, "lines", "lines of one to eight words"),
    "sorted": (sorted_lines, "lines", "lines, already sorted"),
    "reversed": (reversed_lines, "lines", "lines, sorted the other way"),
    "same": (same, "lines", "one line, again and again"),
    "numbers": (numbers, "lines", "whole numbers, some with decimals"),
    "fields": (fields, "lines", "a word, a number and a word"),
    "dict": (dict_words, "lines", "different words, sorted: a dictionary"),
}


def kinds():
    """Every kind: these, and those of tools/*/gen.py."""
    out = dict(KINDS)
    root = os.path.dirname(HERE)
    for path in sorted(glob.glob(os.path.join(root, "tools", "*", "gen.py"))):
        name = "gen_" + os.path.basename(os.path.dirname(path))
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for k, v in getattr(mod, "KINDS", {}).items():
            if k in out:
                raise SystemExit(f"gen.py: {path} defines kind {k!r} again")
            out[k] = v
    return out


def make(kind, n, seed=1):
    """The input: bytes, or a list of bytes for a kind that makes several files."""
    have = kinds()
    if kind not in have:
        raise SystemExit(f"gen.py: no kind {kind!r} (have: {', '.join(sorted(have))})")
    return have[kind][0](n, Rand(seed))


def main(argv):
    args, seed, out = [], 1, None
    i = 0
    while i < len(argv):
        if argv[i] in ("--seed", "-o") and i + 1 < len(argv):
            if argv[i] == "--seed":
                seed = int(argv[i + 1])
            else:
                out = argv[i + 1]
            i += 2
            continue
        args.append(argv[i])
        i += 1
    if len(args) != 2 or not args[1].isdigit():
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        print("kinds: " + ", ".join(sorted(kinds())), file=sys.stderr)
        return 2
    data = make(args[0], int(args[1]), seed)
    if isinstance(data, (list, tuple)):
        if out is None:
            print("gen.py: this kind makes several files: give -o PREFIX", file=sys.stderr)
            return 2
        for j, d in enumerate(data):
            with open(f"{out}.{j + 1}", "wb") as f:
                f.write(d)
        return 0
    if out:
        with open(out, "wb") as f:
            f.write(data)
    else:
        sys.stdout.buffer.write(data)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
