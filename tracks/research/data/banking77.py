"""Banking77 (Casanueva et al. 2020): 13,083 questions to an online bank, each labelled with one of 77 intents.

    classes()       the 77 intents, in the dataset's own order: a class's number is its place there
    same(text)      the form two texts must share to count as the same question
    split(name)     (texts, labels) of "train", "valid" or "test": a list of strings, a numpy array of int64

The files are fetched once (python3 -m data.fetch banking77): train.csv
(10,003 questions), test.csv (3,080, 40 of each intent) and the list of
intents. "I am still waiting on my card?" is card_arrival, "I think my
card is broken" card_not_working: 77 classes, some close to each other
(card_payment_fee_charged, transfer_fee_charged, cash_withdrawal_charge).

The dataset has no validation part, so one is cut out of train.csv, by a
seed, once: VALID questions to choose settings by, the rest to train on.
test.csv is kept whole, as the dataset gives it, so its numbers can sit
beside other people's. A question asked twice is not two examples: a
training question that is the same as a validation or test question
(same() of each: lower case, spaces made single) is left out of
training, so nothing scored was trained on: 6 of them, which leaves
split("train") 8,997 questions.
"""

import csv
import json
from functools import lru_cache

import numpy as np

from data import fetch

VALID = 1000                         # training questions held out to choose settings by
SEED = 0                             # the seed of that cut: the same for every run


# @build 12.01 classes
# The 77 intents, as categories.json lists them.
@lru_cache(maxsize=1)
def classes():
    fetch.need("banking77")
    with open(fetch.path("banking77", "categories.json"), encoding="utf-8") as f:
        return json.load(f)
# @end


# @build 12.01 same
# The form of a question that two copies share: lower case, every run of
# spaces one space, none at the ends.
def same(text):
    return " ".join(text.lower().split())
# @end


def _read(name):
    fetch.need("banking77")
    with open(fetch.path("banking77", name), newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    if rows[0] != ["text", "category"]:
        raise ValueError(f"{name}: expected the columns text, category, not {rows[0]}")
    number = {c: i for i, c in enumerate(classes())}
    return [text for text, _ in rows[1:]], np.array([number[c] for _, c in rows[1:]], dtype=np.int64)


# @build 12.01 split
# (texts, labels) of one part. "test" is test.csv whole. train.csv is
# put in an order drawn from numpy's default_rng(SEED); its first VALID
# questions are "valid", the rest "train", less every question whose
# same() form is also in valid or test. The arrays are shared between
# calls: copy one before changing it.
@lru_cache(maxsize=3)
def split(name):
    if name == "test":
        return _read("test.csv")
    texts, labels = _read("train.csv")
    order = np.random.default_rng(SEED).permutation(len(texts))
    held, rest = order[:VALID], order[VALID:]
    if name == "valid":
        return [texts[i] for i in held], labels[held]
    scored = {same(t) for t in _read("test.csv")[0]} | {same(texts[i]) for i in held}
    keep = [i for i in rest if same(texts[i]) not in scored]
    return [texts[i] for i in keep], labels[keep]
# @end
