"""Inputs for edit's --replay, made by data/gen.py: each kind is two files, a script of edits and
the text it edits, and bench/grow.py puts both paths after the command, in that order:

    python3 bench/grow.py --input typing bin/edit --algo=array --replay

  typing     [lines] a text of n lines (data/gen.py's lines), and a script that goes to its
             second line and types n/8 keys there: words, spaces, a newline now and then, and
             now and then Backspace twice. Typing in one place.
  scattered  [lines] the same text, and a script that types n/64 words, each at a place of its
             own, picked at random: editing all over the text.
  opening    [lines] the same text, and a script that types one key at its end: what it costs
             to open a file.

The scripts print nothing: the run is the edits alone.
"""

import importlib.util
import os

HERE = os.path.dirname(os.path.abspath(__file__))
WORDS = ["the", "piece", "gap", "tree", "a", "cursor", "Holmes", "x", "editor", "undo"]


def _gen():
    spec = importlib.util.spec_from_file_location("dsa_gen_for_edit", os.path.join(HERE, "..", "..", "data", "gen.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _text(n, rng):
    return _gen().lines(n, rng)


def typing(n, rng):
    text = _text(n, rng)
    second = text.index(b"\n") + 1
    out, typed = [f"goto {second}"], 0
    while typed < n // 8:
        word = WORDS[rng.below(len(WORDS))]
        if rng.below(8):
            out.append(f"type {word} ")
            typed += len(word) + 1
        else:
            out.append(f"type {word}\\n")
            typed += len(word) + 1
        if rng.below(10) == 0:
            out.append("back 2")
            typed += 2
    return ["".join(line + "\n" for line in out).encode("ascii"), text]


def scattered(n, rng):
    text = _text(n, rng)
    length, out = len(text), []
    for _ in range(max(1, n // 64)):
        word = WORDS[rng.below(len(WORDS))] + " "
        out.append(f"goto {rng.below(length + 1)}")
        out.append(f"type {word}")
        length += len(word)
    return ["".join(line + "\n" for line in out).encode("ascii"), text]


def opening(n, rng):
    return [b"goto end\ntype x\n", _text(n, rng)]


KINDS = {
    "typing": (typing, "lines", "for bin/edit --replay: a text, and n/8 keys typed at its second line"),
    "scattered": (scattered, "lines", "for bin/edit --replay: a text, and n/64 words typed at random places"),
    "opening": (opening, "lines", "for bin/edit --replay: a text, and one key typed at its end"),
}
