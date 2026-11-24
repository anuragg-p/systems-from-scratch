"""TinyStories (Eldan and Li 2023): short stories in the words a small child knows, and the tokens a model reads.

    stories(split)        the stories of "train" (the first 64 MiB of the paper's training file, whole stories
                          only) or "valid" (its validation file), as a list of strings
    tokenizer(size)       09.01's byte pair encoding learned on the first training stories: (merges, table)
    tokens(split, size)   every story of a split as tokens, each followed by END, one numpy array

The files are fetched once (python3 -m data.fetch tinystories). In them a
story ends with a line <|endoftext|>; here that line is one symbol of its
own, END, the last of the vocabulary: a model that writes it has ended
its story. A vocabulary of `size` is 256 bytes, size - 257 merges, END.

Tokenising 64 MiB takes about 15 s (learning the merges on the first
10,000 stories, then every story, each different piece merged once), so
tokens() keeps what it made in the data cache beside the files
(bpe<size>.json, train-bpe<size>.npy, valid-bpe<size>.npy) and reads it
from there the next time. Delete those files to make them again.
"""

import json
import os
from functools import lru_cache

import numpy as np

from data import fetch
from tokens import bpe

FILES = {"train": "train.txt", "valid": "valid.txt"}
SEPARATOR = b"<|endoftext|>"
LEARN_FROM = 10000                     # the training stories the merges are learned from


# @build 09.04 stories
# The stories of a split, in the file's order: its bytes cut at each
# <|endoftext|> (the training file is a range of a larger one, so the cut
# after its last one ends mid-story: dropped), each read as UTF-8 and
# stripped of the line breaks around it; empty ones left out.
@lru_cache(maxsize=2)
def stories(split):
    fetch.need("tinystories")
    with open(fetch.path("tinystories", FILES[split]), "rb") as f:
        parts = f.read().split(SEPARATOR)
    if split == "train":
        parts = parts[:-1]
    return [s for s in (p.decode("utf-8").strip() for p in parts) if s]
# @end


# @build 09.04 tokenizer
# The merges of a vocabulary of size symbols (the last, END, is not a
# merge), learned by 09.01's train from the first LEARN_FROM training
# stories, one to a line, and their table of bytes; kept in the data
# cache as bpe<size>.json, a list of the merged pairs in order, and read
# from there when it is there.
@lru_cache(maxsize=2)
def tokenizer(size):
    path = fetch.path("tinystories", f"bpe{size}.json")
    if os.path.isfile(path):
        with open(path) as f:
            merges = {tuple(pair): 256 + i for i, pair in enumerate(json.load(f))}
    else:
        merges = bpe.train("\n".join(stories("train")[:LEARN_FROM]), size - 1)
        with open(path + ".part", "w") as f:
            json.dump([list(pair) for pair in merges], f)
        os.replace(path + ".part", path)
    return merges, bpe.vocab(merges)
# @end


# @build 09.04 tokens
# Every story of split as tokens (bpe's pieces, each different piece
# merged once and remembered), END (size - 1) after each, as one array of
# uint16; kept in the data cache as <split>-bpe<size>.npy and read from
# there when it is there.
@lru_cache(maxsize=4)
def tokens(split, size):
    path = fetch.path("tinystories", f"{split}-bpe{size}.npy")
    if os.path.isfile(path):
        return np.load(path)
    merges, _ = tokenizer(size)
    seen, out = {}, []
    for story in stories(split):
        for piece in bpe.pieces(story):
            ids = seen.get(piece)
            if ids is None:
                ids = seen[piece] = bpe.encode(piece, merges)
            out.extend(ids)
        out.append(size - 1)
    ids = np.array(out, dtype=np.uint16)
    with open(path + ".part", "wb") as f:
        np.save(f, ids)
    os.replace(path + ".part", path)
    return ids
# @end
