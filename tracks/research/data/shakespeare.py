"""Tiny Shakespeare: 1,115,394 characters of Shakespeare's plays, the text module 07 on models.

The file, data/tinyshakespeare.txt, ships with the project: the one from
Andrej Karpathy's char-rnn (a selection of the plays, the speaker's name
on a line of its own before each speech), byte for byte. It is plain
ASCII, so one byte is one character, and 65 different characters occur
in it: the newline, the space, ten punctuation marks (! $ & ' , - . : ;
?), the digit 3, and the 26 letters in both cases.

load() gives the text as one string; chars() its 65 characters, sorted,
a character's number being its place there; encode() and decode() turn
text into those numbers (a numpy array) and back. split() gives one part
of the text as numbers, by position: the first 90% to train on, the next
5% to choose settings by (validation), the last 5% to score on (test).
Nothing is shuffled, so held-out text is whole passages no model saw.
"""

import os
from functools import lru_cache

import numpy as np

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tinyshakespeare.txt")
SPLITS = {"train": (0.0, 0.9), "val": (0.9, 0.95), "test": (0.95, 1.0)}


# @build 07.01 load
# The whole text, as one string.
@lru_cache(maxsize=1)
def load():
    with open(FILE, encoding="ascii") as f:
        return f.read()
# @end


# @build 07.01 chars
# The different characters of the text, sorted, as one string: a model's
# vocabulary. A character's number is its place in it.
@lru_cache(maxsize=1)
def chars():
    return "".join(sorted(set(load())))
# @end


# @build 07.01 encode
# The numbers of the characters of text, as a numpy array of int64.
def encode(text):
    number = {c: i for i, c in enumerate(chars())}
    return np.array([number[c] for c in text], dtype=np.int64)
# @end


# @build 07.01 decode
# The text whose character numbers are ids (any sequence of ints).
def decode(ids):
    vocab = chars()
    return "".join(vocab[int(i)] for i in ids)
# @end


# @build 07.01 split
# One part of the text as character numbers, cut by position: "train" is
# the first 90% of the characters, "val" the next 5%, "test" the last 5%
# (SPLITS). The array is shared between calls: copy it before changing it.
@lru_cache(maxsize=3)
def split(name):
    lo, hi = SPLITS[name]
    text = load()
    return encode(text[int(lo * len(text)):int(hi * len(text))])
# @end
