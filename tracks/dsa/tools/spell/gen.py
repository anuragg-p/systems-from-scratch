"""spell's own input for data/gen.py and bench/grow.py.

  typos   [words] words of the book, picked at random, ten to a line, one in
          ten of those of three letters or more with a typo: a letter left
          out, one put in, one changed, or two side by side swapped. The
          different unknown words grow with the text, as a writer's typos
          do: spell finds 756 in 10000 words, 2529 in 40000, 5521 in 100000.

    python3 data/gen.py typos 10000 > typos.txt
    python3 bench/grow.py --input typos bin/spell -s --near=scan
"""

import os
import re

BOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "book.txt")
LETTERS = "abcdefghijklmnopqrstuvwxyz"

_words = None


def book_words():
    global _words
    if _words is None:
        with open(BOOK, "rb") as f:
            _words = [w.decode("ascii").lower() for w in re.findall(rb"[A-Za-z]+", f.read())]
    return _words


def typo(w, rng):
    """w with one random edit."""
    i = rng.below(len(w))
    kind = rng.below(4)
    if kind == 0:                                   # a letter left out
        return w[:i] + w[i + 1:]
    if kind == 1:                                   # a letter put in
        return w[:i] + LETTERS[rng.below(26)] + w[i:]
    if kind == 2:                                   # a letter changed
        return w[:i] + LETTERS[rng.below(26)] + w[i + 1:]
    i = min(i, len(w) - 2)                          # two side by side swapped
    return w[:i] + w[i + 1] + w[i] + w[i + 2:]


def typos(n, rng):
    words = book_words()
    lines, line = [], []
    for _ in range(n):
        w = words[rng.below(len(words))]
        if len(w) >= 3 and rng.below(10) == 0:
            w = typo(w, rng)
        line.append(w)
        if len(line) == 10:
            lines.append(" ".join(line))
            line = []
    if line:
        lines.append(" ".join(line))
    return "".join(l + "\n" for l in lines).encode("ascii")


KINDS = {"typos": (typos, "words", "words of the book, one in ten (of three letters or more) with a typo")}
