"""GPT-2's tokenizer: OpenAI's vocabulary and merges, read from their own files, giving their ids (09.02).

    byte_symbols()           the printable character each of the 256 bytes is written as in GPT-2's files
    classes()                Unicode's letters and numbers as character classes for re, made from unicodedata
    pattern()                GPT-2's splitting pattern, written for re with those classes
    split(text)              a text cut into the pieces GPT-2 merges within
    Tokenizer(vocab, merges) encode(text) and decode(ids) with GPT-2's merges, a cache of pieces already seen
    load()                   the Tokenizer from the files `python3 -m data.fetch gpt2` puts in the cache

GPT-2 (Radford et al. 2019, section 2.2) is byte pair encoding on bytes,
as 09.01's: 256 symbols for the bytes, then 50,000 merges learned on
OpenAI's WebText, in order, the k-th making symbol 256 + k (the files
say so: Tokenizer checks it), and one more symbol, 50256, <|endoftext|>,
which marks where a document ends. Two things differ from 09.01:

- The files are text, so a byte that is not a printable character
  (a space, a newline, the bytes of other scripts) is written as one
  that is: byte_symbols() is the table. vocab.json maps each symbol, so
  written, to its id; merges.txt lists the merges, one pair a line.
- The pieces. Radford et al. stopped merges across kinds of character
  ("dog." "dog!" "dog?" each wasting a symbol), so GPT-2 cuts text with a
  pattern written for the regex module: contractions, letters, numbers,
  other marks, each with the space before it, and runs of spaces. It
  names Unicode's classes, \\p{L} (every letter of every script) and
  \\p{N} (every number), which Python's re does not have. classes()
  builds them from unicodedata, the same tables, so the pattern works in
  re unchanged. Its \\s is Unicode's White_Space, which is SPACE below:
  re's own \\s has four characters more (the separators 0x1c to 0x1f).

The ids are tiktoken's and transformers' (the internal test checks a
large and awkward text). A character that Unicode assigned after the
version this Python's unicodedata has is not a letter here; see
NOTES.md for what that changes.
"""

import json
import os
import re
import unicodedata
from functools import lru_cache

from data import fetch
from tokens import bpe

# Unicode's White_Space property (PropList.txt), all 25 characters: what \s means in the pattern GPT-2 was written
# for. Python's unicodedata does not have the property; re's \s is str.isspace(), which also counts 0x1c to 0x1f.
SPACE = r"\t\n\x0b\x0c\r \x85\xa0  -     　"
END = 50256                                   # <|endoftext|>: the id GPT-2 put between documents


# @build 09.02 byte_symbols
# The character each byte is written as in GPT-2's files, a list of 256:
# the bytes of printable characters ("!" to "~", and "\xa1" to "\xac" and
# "\xae" to "\xff" read as Latin-1) as themselves, and the other 68 (the
# space, controls, and the rest) as the characters 256, 257, ... in order
# of their byte: a space is "Ġ", a newline "Ċ".
def byte_symbols():
    printable = [*range(ord("!"), ord("~") + 1), *range(0xA1, 0xAD), *range(0xAE, 0x100)]
    others = [b for b in range(256) if b not in printable]
    symbols = [""] * 256
    for b in printable:
        symbols[b] = chr(b)
    for n, b in enumerate(others):
        symbols[b] = chr(256 + n)
    return symbols
# @end


# @build 09.02 classes
# Unicode's letters and numbers as the inside of an re character class,
# {"L": ..., "N": ...}: every code point whose general category in
# unicodedata starts with L (Lu Ll Lt Lm Lo) or N (Nd Nl No), in runs of
# neighbours written as ranges, "\U00000041-\U0000005a...". Made once.
@lru_cache(maxsize=1)
def classes():
    runs = {"L": [], "N": []}
    for c in range(0x110000):
        kind = unicodedata.category(chr(c))[0]
        if kind in runs:
            r = runs[kind]
            if r and r[-1][1] == c - 1:
                r[-1][1] = c
            else:
                r.append([c, c])
    return {k: "".join(f"\\U{a:08x}" + (f"-\\U{b:08x}" if b > a else "") for a, b in r) for k, r in runs.items()}
# @end


# @build 09.02 pattern
# GPT-2's pattern (OpenAI's encoder.py) for re: \p{L} and \p{N} are the
# classes above, \s is [SPACE] and \S its opposite. Tried in order: a
# contraction ('s 't 're 've 'm 'll 'd); letters, numbers, or other marks,
# each with one space before them or none; a run of spaces that leaves the
# last one for the word after it; any run of spaces.
@lru_cache(maxsize=1)
def pattern():
    L, N, S = classes()["L"], classes()["N"], SPACE
    return re.compile(rf"'s|'t|'re|'ve|'m|'ll|'d| ?[{L}]+| ?[{N}]+| ?[^{S}{L}{N}]+|[{S}]+(?![^{S}])|[{S}]+")
# @end


# @build 09.02 split
# The pieces of text, as GPT-2 cuts it: pattern()'s matches, in order.
# Every character is in exactly one.
def split(text):
    return pattern().findall(text)
# @end


# @build 09.02 Tokenizer
# GPT-2's tokenizer, from vocab.json and merges.txt. table: id -> bytes
# (each symbol's characters back to bytes by byte_symbols); first: byte
# -> the id of its one-byte symbol; merges: (id, id) -> new id, in the
# file's order, which is 09.01's form (the k-th line makes 256 + k:
# checked). encode cuts the text with split and merges each piece's
# symbols as 09.01's encode does, smallest new id first; a piece seen
# before is looked up in the cache (when cache is set) instead of merged
# again. decode is 09.01's.
class Tokenizer:
    def __init__(self, vocab_file, merges_file):
        symbols = byte_symbols()
        byte_of = {c: b for b, c in enumerate(symbols)}
        with open(vocab_file, encoding="utf-8") as f:
            vocab = json.load(f)
        self.table = {i: bytes(byte_of[c] for c in text) for text, i in vocab.items()}
        self.first = [vocab[c] for c in symbols]
        with open(merges_file, encoding="utf-8") as f:
            lines = [line.split(" ") for line in f.read().split("\n")[1:] if line]
        self.merges = {(vocab[a], vocab[b]): vocab[a + b] for a, b in lines}
        if list(self.merges.values()) != list(range(256, 256 + len(lines))):
            raise ValueError(f"{merges_file}: the k-th merge should make the symbol 256 + k")
        self.cache = {}

    def encode(self, text, cache=True):
        out = []
        for piece in split(text):
            ids = self.cache.get(piece) if cache else None
            if ids is None:
                ids = [self.first[b] for b in piece.encode("utf-8")]
                while len(ids) > 1:
                    pair = min(zip(ids, ids[1:]), key=lambda p: self.merges.get(p, float("inf")))
                    if pair not in self.merges:
                        break
                    ids = bpe.merge(ids, pair, self.merges[pair])
                if cache:
                    self.cache[piece] = ids
            out.extend(ids)
        return out

    def decode(self, ids):
        return bpe.decode(ids, self.table)
# @end


# @build 09.02 load
# GPT-2's tokenizer, from the files data/fetch.py keeps in the cache (the
# script stops with the fetch command when they are not there).
def load():
    fetch.need("gpt2")
    return Tokenizer(fetch.path("gpt2", "vocab.json"), fetch.path("gpt2", "merges.txt"))
# @end
