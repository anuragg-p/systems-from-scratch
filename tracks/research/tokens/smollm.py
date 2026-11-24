"""SmolLM2's tokenizer: GPT-2's byte pair encoding with another vocabulary, from its tokenizer.json (10.04).

    split(text)        a text cut into the pieces SmolLM2 merges within: every digit alone, then GPT-2's pattern
    Tokenizer(path)    encode(text) and decode(ids) with SmolLM2's symbols and merges, read from tokenizer.json
    load()             the Tokenizer from the file `python3 -m data.fetch smollm2` puts in the cache

SmolLM2 keeps its tokenizer in one file, tokenizer.json (the format of
Hugging Face's tokenizers library): the symbols and their ids, the
merges in order, the special symbols, and the steps that cut a text
into pieces. Read there, it is GPT-2's kind of tokenizer (09.02):
bytes written as GPT-2's printable characters (tokens/gpt2.py's
byte_symbols), GPT-2's pattern, merges applied in the order learned.
What differs:

- Digits. Before GPT-2's pattern, every character Unicode counts as a
  number is cut out as a piece of its own (the pre-tokenizer "Digits"
  with individual_digits): " 2019" is " ", "2", "0", "1", "9", where
  GPT-2 has the one piece " 2019".
- The vocabulary: 49,152 symbols. The first 17 are special:
  <|endoftext|> is 0 (the end of a document, as GPT-2's 50256), then
  <|im_start|> and <|im_end|> (a chat's turns) and 14 for code
  (<repo_name>, <file_sep>, <jupyter_code>, ...). Then the bytes, but
  235 of them, not 256: 21 bytes that never occurred in the text it was
  learned on have no symbol, and a character that needs one of them
  loses that byte (the reference does the same). Then 48,900 merges,
  the k-th (from 0) making symbol 252 + k.

encode, like tokens/gpt2.py's, reads a special symbol's text in a text
as ordinary text; END is the id to put between documents by hand.
"""

import json
import re

from data import fetch
from tokens import bpe
from tokens import gpt2

END = 0                                     # <|endoftext|>


# @build 10.04 split
# The pieces of text, as SmolLM2 cuts it: every number character (a
# Unicode category N, as tokens/gpt2.py's classes() has them) a piece of
# its own, and each run of text between them cut by GPT-2's pattern
# (tokens/gpt2.py's split). Every character is in exactly one piece.
def split(text):
    out = []
    for part in re.split(f"([{gpt2.classes()['N']}])", text):
        if part:
            out.extend(gpt2.split(part))
    return out
# @end


# @build 10.04 Tokenizer
# SmolLM2's tokenizer, from its tokenizer.json. table: id -> bytes (each
# symbol's characters back to bytes by byte_symbols; a special symbol's
# are its text); first: byte -> the id of its one-byte symbol, or None
# for the 21 bytes that have none; merges: (id, id) -> new id, in the
# file's order, each new id one more than the last (checked), so 09.01's
# loop, smallest new id first, merges in the order learned. specials:
# text -> id of the special symbols. The file's own description of how
# it cuts a text is checked too: anything else would need other code.
# encode merges each piece of split() as tokens/gpt2.py's does, leaving
# out bytes with no symbol, with a cache of pieces seen; decode is 09.01's.
class Tokenizer:
    CUTS = {"type": "Sequence", "pretokenizers": [{"type": "Digits", "individual_digits": True},
                                                 {"type": "ByteLevel", "add_prefix_space": False, "trim_offsets": True,
                                                  "use_regex": True}]}

    def __init__(self, path):
        with open(path, encoding="utf-8") as f:
            spec = json.load(f)
        if spec["pre_tokenizer"] != self.CUTS or spec["normalizer"] is not None or spec["model"]["type"] != "BPE":
            raise ValueError(f"{path}: not cut as SmolLM2's tokenizer cuts a text")
        byte_of = {c: b for b, c in enumerate(gpt2.byte_symbols())}
        vocab = spec["model"]["vocab"]
        self.specials = {t["content"]: t["id"] for t in spec["added_tokens"]}
        self.table = {i: text.encode("utf-8") if text in self.specials else bytes(byte_of[c] for c in text)
                      for text, i in vocab.items()}
        self.first = [vocab.get(c) for c in gpt2.byte_symbols()]
        pairs = [m.split(" ") if isinstance(m, str) else m for m in spec["model"]["merges"]]
        self.merges = {(vocab[a], vocab[b]): vocab[a + b] for a, b in pairs}
        start = len(vocab) - len(pairs)
        if list(self.merges.values()) != list(range(start, len(vocab))):
            raise ValueError(f"{path}: the k-th merge should make the symbol {start} + k")
        self.cache = {}

    def encode(self, text, cache=True):
        out = []
        for piece in split(text):
            ids = self.cache.get(piece) if cache else None
            if ids is None:
                ids = [self.first[b] for b in piece.encode("utf-8") if self.first[b] is not None]
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


def load():
    """SmolLM2's tokenizer, from the file data/fetch.py keeps in the cache (the script stops with the fetch command
    when it is not there)."""
    fetch.need("smollm2")
    return Tokenizer(fetch.path("smollm2", "tokenizer.json"))
