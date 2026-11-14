"""Pairs of files for diff: data/gen.py's kinds versions, revised and unrelated.

Each makes two files of n lines from data/book.txt: a stretch of the book,
from a line the seed picks (going round to the start again when it runs
out), and a second file made from it. grow.py puts both paths after the
command, so

    python3 bench/grow.py --input versions bin/diff --algo=table

times diff on pairs that double in length.

  versions   the stretch, and a copy with 16 small edits: each deletes,
             inserts or changes one to three lines. The difference stays
             the same size however long the files are
  revised    the same with an edit every 32 lines: the difference grows
             with the files
  unrelated  the stretch, and another stretch from half the book away:
             in common only what any two pages share, blank lines and a
             few short ones
"""

import os

BOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "book.txt")
_lines = None


def book_lines():
    global _lines
    if _lines is None:
        with open(BOOK, "rb") as f:
            _lines = f.read().split(b"\n")[:-1]
    return _lines


def stretch(n, start):
    lines = book_lines()
    return [lines[(start + i) % len(lines)] for i in range(n)]


def edit(lines, edits, rng):
    """lines with edits made at places rng picks: each deletes, inserts or changes 1 to 3 lines."""
    out = list(lines)
    places = sorted((rng.below(len(out) + 1) for _ in range(edits)), reverse=True)
    for k, at in enumerate(places):
        what, count = rng.below(3), 1 + rng.below(3)
        new = [b"A line that was not here before (%d.%d)." % (k + 1, j + 1) for j in range(count)]
        if what == 0:
            del out[at:at + count]
        elif what == 1:
            out[at:at] = new
        else:
            out[at:at + count] = [l + b" (changed)" for l in out[at:at + count]] or new
    return out


def join(lines):
    return b"".join(l + b"\n" for l in lines)


def versions(n, rng):
    a = stretch(n, rng.below(len(book_lines())))
    return [join(a), join(edit(a, 16, rng))]


def revised(n, rng):
    a = stretch(n, rng.below(len(book_lines())))
    return [join(a), join(edit(a, max(1, n // 32), rng))]


def unrelated(n, rng):
    start = rng.below(len(book_lines()))
    return [join(stretch(n, start)), join(stretch(n, start + len(book_lines()) // 2))]


KINDS = {
    "versions": (versions, "lines", "two files: lines of the book, and a copy with 16 small edits"),
    "revised": (revised, "lines", "two files: lines of the book, and a copy with an edit every 32 lines"),
    "unrelated": (unrelated, "lines", "two files: lines of the book, and other lines of it"),
}
