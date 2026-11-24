"""Byte pair encoding: text as bytes, and the pairs that come up most often merged into new symbols (09.01).

    pieces(text)              the text cut into words (each with the space before it), runs of other marks, spaces
    pairs(ids)                how often each pair of neighbours occurs in ids: {(a, b): count}
    merge(ids, pair, new)     ids with every (a, b), left to right, replaced by the one symbol new
    train_simple(text, size)  the merges, the obvious way: every pair of the text counted again for every merge
    train(text, size)         the same merges, each distinct piece counted once, the counts kept up to date
    encode(text, merges)      the symbols of text: each piece's bytes, merged in the order the merges were learned
    vocab(merges)             the bytes each symbol stands for
    decode(ids, table)        the text a list of symbols stands for

Characters make a model's window short, and words leave out every word
the training text never had. Sennrich, Haddow and Birch (2016), "Neural
Machine Translation of Rare Words with Subword Units", took a middle
way from data compression: start from single symbols, count every pair
of neighbours in the training text, make the most frequent pair a new
symbol, and repeat. Frequent words end as one symbol, rare words as a
few pieces, and nothing is unknown. Here the single symbols are the 256
values of a byte, as GPT-2's are: any text is UTF-8 bytes, so any text,
in any script, can be written with them.

A merge is a pair (a, b) and the new symbol it makes, numbered from 256
in the order they were learned: merges is a dict {(a, b): new} in that
order. Pairs are never counted across pieces, so a symbol never holds the
end of one word and the start of the next.

The rule for ties: of pairs counted equally often, the merge is the one
with the smaller first symbol, then the smaller second, so the merges do
not depend on the order the text was read in.
"""

import re
from collections import Counter

# A word with the space before it, a run of other marks with the space before it, or a run of spaces and line
# breaks. Every character is one of the three (\w: a letter or digit of any script, or _; \s: any space), so the
# pieces of a text, put back together, are the text.
SPLIT = re.compile(r" ?\w+| ?[^\w\s]+|\s+")


# @build 09.01 pieces
# The text cut into its pieces: SPLIT's matches, in order. Every character
# is in exactly one, so "".join(pieces(text)) == text.
def pieces(text):
    return SPLIT.findall(text)
# @end


# @build 09.01 pairs
# How often each pair of neighbours (ids[i], ids[i + 1]) occurs in ids (a
# list of symbols): a Counter {(a, b): count}. Overlapping pairs count
# each time: (1, 1) occurs twice in [1, 1, 1].
def pairs(ids):
    return Counter(zip(ids, ids[1:]))
# @end


# @build 09.01 merge
# ids (a list) with every occurrence of pair (a, b) replaced by the one
# symbol new, read left to right: [1, 1, 1] with (1, 1) becomes [new, 1].
def merge(ids, pair, new):
    out, i = [], 0
    while i < len(ids):
        if i + 1 < len(ids) and (ids[i], ids[i + 1]) == pair:
            out.append(new)
            i += 2
        else:
            out.append(ids[i])
            i += 1
    return out
# @end


# @build 09.01 train_simple
# The merges of a vocabulary of `size` symbols (256 bytes and size - 256
# merges), learned from text the obvious way: every piece as its UTF-8
# bytes; then, for each merge, the pairs of every piece of the text
# counted again, the most frequent made the next symbol (ties: the smaller
# pair), and merged in every piece. Stops early when no pair is left.
def train_simple(text, size):
    words = [list(p.encode("utf-8")) for p in pieces(text)]
    merges = {}
    for new in range(256, size):
        counts = Counter()
        for w in words:
            counts.update(pairs(w))
        if not counts:
            break
        best = max(counts, key=lambda p: (counts[p], -p[0], -p[1]))
        merges[best] = new
        words = [merge(w, best, new) for w in words]
    return merges
# @end


# @build 09.01 train
# The same merges as train_simple, fast enough for a real vocabulary. Two
# changes. Each distinct piece is held once, with how often it occurs (a
# text of a million characters has about 25,000), and its pairs count that
# many times. And the counts are kept, not made again: `where` says which
# pieces hold each pair, and a merge changes only those, taking their old
# pairs out of the counts and putting their new ones in.
def train(text, size):
    found = Counter(pieces(text))
    words = [list(p.encode("utf-8")) for p in found]
    times = list(found.values())
    counts, where = Counter(), {}
    for i, w in enumerate(words):
        for p in zip(w, w[1:]):
            counts[p] += times[i]
            where.setdefault(p, set()).add(i)
    merges = {}
    for new in range(256, size):
        if not counts:
            break
        best = max(counts, key=lambda p: (counts[p], -p[0], -p[1]))
        merges[best] = new
        for i in where.pop(best):
            w = words[i]
            for p in zip(w, w[1:]):
                counts[p] -= times[i]
                if not counts[p]:
                    del counts[p]
            words[i] = w = merge(w, best, new)
            for p in zip(w, w[1:]):
                counts[p] += times[i]
                where.setdefault(p, set()).add(i)
    return merges
# @end


# @build 09.01 encode
# The symbols of text: each piece's UTF-8 bytes, then, again and again, of
# the pairs of neighbours that are merges the one learned first is merged
# (wherever it occurs), until no pair left is a merge. Learned first means
# the smallest new symbol. This makes of a training piece exactly what
# training made of it.
def encode(text, merges):
    out = []
    for piece in pieces(text):
        ids = list(piece.encode("utf-8"))
        while len(ids) > 1:
            pair = min(zip(ids, ids[1:]), key=lambda p: merges.get(p, float("inf")))
            if pair not in merges:
                break
            ids = merge(ids, pair, merges[pair])
        out.extend(ids)
    return out
# @end


# @build 09.01 vocab
# The bytes each symbol stands for, {symbol: bytes}: 0 to 255 one byte
# each, and each merge (a, b) the bytes of a and then of b, in the order
# the merges were learned (a dict keeps it), so a and b are always there.
def vocab(merges):
    table = {i: bytes([i]) for i in range(256)}
    for (a, b), new in merges.items():
        table[new] = table[a] + table[b]
    return table
# @end


# @build 09.01 decode
# The text symbols stand for: their bytes one after another, read as
# UTF-8. Symbols that encode made always give whole characters; any other
# list may cut one, and a byte that is no character's becomes U+FFFD.
def decode(ids, table):
    return b"".join(table[i] for i in ids).decode("utf-8", errors="replace")
# @end
