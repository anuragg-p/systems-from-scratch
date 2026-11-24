"""Instructions made by code, so that every answer can be checked exactly (12.03).

    TASKS                       each task's wordings and how its instances are made and answered
    words()                     the words the word tasks draw from: Tiny Shakespeare's, 3 to 6 small letters
    instances(task, part, n, rng)   n of a task's instances, each (its fields, its answer), from one part
    wordings(task, part)        the ways a task is asked: "train" (all but the last) or "held" (the last)
    chat(prompt)                the prompt in the chat template, up to where the answer starts
    reply(answer)               the answer as the model is to write it: then a line with the end marker

A model told "Which is larger, 12 or 57?" can be scored exactly: 57 is
right and anything else is wrong. So every task here is made by code,
with its answer computed, short, and checkable character for character:
the larger of two numbers, three digits sorted, a word in capitals, a
word backwards, how many times a letter is in a word. Each task is asked
in several wordings; the last wording of each is never trained on, nor is
one whole task (smaller), so a fine-tuned model can be scored on
instances it never saw, in words it never saw, and on a task it was never
taught.

Instances are split too: the words are cut once (WORD_SEED) into words
to train on and words held out, and the number tasks' instances once
into the same two parts, so a "held" instance never occurs in training.

The chat template is plain ASCII, cut by the tokenizer as any text is:

    <|user|>
    Which is larger, 12 or 57?
    <|assistant|>
    57
    <|end|>

The model's part is the answer and the line <|end|> after it; a model
that has learned the template writes <|end|> and stops.
"""

import re
from functools import lru_cache

import numpy as np

from data import shakespeare

USER, ASSISTANT, END = "<|user|>", "<|assistant|>", "<|end|>"
WORD_SEED = 0                          # the one cut of the words, and of the number tasks' instances
HELD = 0.2                             # the share held out


def _upper(w):
    return w.upper()


def _reverse(w):
    return w[::-1]


def _count(w, c):
    return str(w.count(c))


def _larger(a, b):
    return str(max(a, b))


def _smaller(a, b):
    return str(min(a, b))


def _sort(x, y, z):
    return " ".join(str(d) for d in sorted((x, y, z)))


# name: (what it is made from, its answer from its fields, its wordings; the last wording is held out)
TASKS = {
    "larger": ("pair", _larger, ["Which is larger, {a} or {b}?", "Give the larger number: {a} or {b}.",
                                 "What is the bigger of {a} and {b}?", "Of {a} and {b}, which is greater?"]),
    "sort": ("digits", _sort, ["Sort the digits {x} {y} {z} from smallest to largest.",
                               "Put {x}, {y}, {z} in increasing order.", "Order these digits: {x} {y} {z}",
                               "Arrange {x} {y} {z} in ascending order."]),
    "upper": ("word", _upper, ["Write {w} in capital letters.", "Upper-case this word: {w}", "Make {w} all capitals.",
                               "Convert the word {w} to upper case."]),
    "reverse": ("word", _reverse, ["Reverse the word {w}.", "Write {w} backwards.", "Spell {w} in reverse order.",
                                   "What is {w} with its letters in the opposite order?"]),
    "count": ("letter", _count, ["How many times does the letter {c} occur in {w}?", "Count the letter {c} in the word {w}.",
                                 "In {w}, how many times is there a {c}?", "Tell me the number of {c}s in {w}."]),
    "smaller": ("pair", _smaller, ["Which is smaller, {a} or {b}?", "Give the smaller number: {a} or {b}.",
                                   "What is the lesser of {a} and {b}?", "Of {a} and {b}, which is less?"]),
}
TRAINED = ["larger", "sort", "upper", "reverse", "count"]       # smaller is never trained on


# @build 12.03 words
# The different words of Tiny Shakespeare of 3 to 6 small letters (a run
# of a to z, so "I'll" and capitals are not words here), sorted.
@lru_cache(maxsize=1)
def words():
    return sorted({w for w in re.findall(r"[a-z]+", shakespeare.load()) if 3 <= len(w) <= 6})
# @end


@lru_cache(maxsize=1)
def _parts():
    """Each kind's instances, cut once by WORD_SEED into (train, held)."""
    rng = np.random.default_rng(WORD_SEED)
    out = {}
    pairs = [(a, b) for a in range(100) for b in range(100) if a != b]
    digits = [(x, y, z) for x in range(10) for y in range(10) for z in range(10) if len({x, y, z}) == 3]
    for kind, items in (("word", words()), ("pair", pairs), ("digits", digits)):
        order = rng.permutation(len(items))
        cut = int(round(HELD * len(items)))
        out[kind] = ([items[i] for i in order[cut:]], [items[i] for i in order[:cut]])
    return out


# @build 12.03 instances
# n instances of task drawn with rng (a numpy Generator) from one part
# ("train" or "held"), each (fields, answer): fields the dict its
# wordings are filled from, answer the right answer as text, computed by
# the task's own function. A word task takes a word of that part; count
# also a letter, half the time one of the word's own and half the time
# any of a to z, so that 0 is not almost always right.
def instances(task, part, n, rng):
    kind, answer, _ = TASKS[task]
    pool = _parts()["word" if kind in ("word", "letter") else kind][part == "held"]
    out = []
    for i in rng.integers(0, len(pool), n):
        item = pool[int(i)]
        if kind == "pair":
            fields = {"a": item[0], "b": item[1]}
        elif kind == "digits":
            fields = {"x": item[0], "y": item[1], "z": item[2]}
        elif kind == "word":
            fields = {"w": item}
        else:
            letters = item if rng.random() < 0.5 else "abcdefghijklmnopqrstuvwxyz"
            fields = {"w": item, "c": letters[int(rng.integers(0, len(letters)))]}
        out.append((fields, answer(*fields.values())))
    return out
# @end


# @build 12.03 wordings
# The wordings of task: "train", every one but the last; "held", the last.
def wordings(task, part):
    ways = TASKS[task][2]
    return ways[:-1] if part == "train" else ways[-1:]
# @end


# @build 12.03 chat
# The chat template up to where the model starts to answer: the user's
# marker, the prompt, the assistant's marker, each on a line of its own.
def chat(prompt):
    return f"{USER}\n{prompt}\n{ASSISTANT}\n"
# @end


# @build 12.03 reply
# What the model is to write after chat(prompt): the answer, then the end
# marker on a line of its own.
def reply(answer):
    return f"{answer}\n{END}"
# @end
