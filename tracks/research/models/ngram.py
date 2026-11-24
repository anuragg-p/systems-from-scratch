"""Count models of language: the next character's chances from how often it followed the same few characters.

    NGram(ids, n, V)            the counts, in the training ids, of every context of n characters and
                                of every (context, next character) that occurs
    model.counts(ids)           for each position t >= n of ids: how often ids[t] came after its context
                                in training, and how often the context came at all
    model.probabilities(ids, k) the chance of ids[t] after its context, every count plus k (07.01's
                                smoothing), for each position t >= n of ids
    mixture_weights(p)          the weights of a mixture of models, fit to give a text its highest chance

07.01's pair table, for any length of context. A table of every context
has V ** n rows, 65 ** 5 = 1,160,290,625 of them for 5 characters, and
nearly all of them would be empty; so only what occurs is kept, as two
sorted arrays of numbers with their counts, and looked up by binary
search. A count model has nothing to train, so this file is numpy only.
"""

import numpy as np


# @build 07.02 context_codes
# The n characters before each position t >= n of ids (character numbers
# 0..V-1), each context as one number, its characters as digits in base V
# (for n = 2 and V = 65, the context "ab", numbers 39 and 40, is 39 * 65 +
# 40), and the character at each of those positions. A context of 0
# characters is the number 0 everywhere: the single counts. An int64 holds
# a context and its next character for n up to 9.
def context_codes(ids, n, V):
    if V ** (n + 1) >= 2 ** 63:
        raise ValueError(f"contexts of {n} characters of {V} do not fit in an int64")
    code = np.zeros(len(ids) - n, dtype=np.int64)
    for j in range(n):
        code = code * V + ids[j:len(ids) - n + j]
    return code, ids[n:]
# @end


# @build 07.02 lookup
# The count of each of queries in keys (sorted, distinct) with their
# counts, by binary search (np.searchsorted); 0 for a query not among them.
def lookup(keys, counts, queries):
    i = np.minimum(np.searchsorted(keys, queries), len(keys) - 1)
    return np.where(keys[i] == queries, counts[i], 0)
# @end


# @build 07.02 NGram
# A count model with contexts of n characters, counted in the training
# ids: the distinct contexts that occur with how often each does, and the
# distinct (context, next character) pairs, coded context * V + next, with
# theirs (np.unique sorts and counts). Its chance of a character after a
# context is (count of the pair + k) / (count of the context + V k), 07.01's
# smoothing; a context never seen in training gets every character equally,
# 1 / V, whatever k (which is what that formula gives for any k > 0).
class NGram:
    def __init__(self, ids, n, V):
        self.n, self.V = n, V
        context, after = context_codes(ids, n, V)
        self.pairs, self.pair_counts = np.unique(context * V + after, return_counts=True)
        self.contexts, self.context_counts = np.unique(context, return_counts=True)

    def counts(self, ids):
        context, after = context_codes(ids, self.n, self.V)
        return (lookup(self.pairs, self.pair_counts, context * self.V + after),
                lookup(self.contexts, self.context_counts, context))

    def probabilities(self, ids, k=0.0):
        pair, context = self.counts(ids)
        seen = context > 0
        p = np.full(len(pair), 1.0 / self.V)
        p[seen] = (pair[seen] + k) / (context[seen] + k * self.V)
        return p
# @end


# @build 07.02 mixture_weights
# The weights w (each >= 0, adding up to 1) of a mixture of models, sum
# over m of w[m] p[m], that gives a text its highest chance: p holds each
# model's chance of each character of the text, one row a model. Start
# with equal weights, then `steps` times: each model's share of each
# character's mixed chance, w[m] p[m] / (the mixture), averaged over the
# characters, is its new weight (expectation-maximisation: the text's
# chance under the mixture never falls from one step to the next).
def mixture_weights(p, steps=200):
    w = np.full(len(p), 1.0 / len(p))
    for _ in range(steps):
        share = w[:, None] * p
        w = (share / share.sum(axis=0)).mean(axis=1)
    return w
# @end
