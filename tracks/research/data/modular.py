"""Equations a o b = c modulo a prime p: the data of the grokking paper (14.01).

    SYMBOLS                        the tokens after the p residues: "=", then one per operation
    divide(a, b, p)                a / b modulo p: a times the number that b times is 1
    OPERATIONS                     "+", "-" and "/", each a function of a, b and p
    equations(p, op)               every a, b and their c = a op b (mod p), one row each: (n, 3)
    tokens(rows, p, op)            the rows as the paper's sequences, a op b = c: (n, 5) token numbers
    split(p, op, fraction, seed)   a random fraction of the equations to train on, the rest to validate
    names(p)                       the text of every token, for printing

Power et al. (2022), appendix A.1.1: "For each binary operation we
constructed a dataset of equations of the form <x><op><y><=><x o y>, where
<a> stands for the token corresponding to element a. For each training
run, we chose a fraction of all available equations at random and declared
them to be the training set, with the rest of equations being the
validation set." Every residue is a symbol of its own: the model is never
told that 5 comes after 4, or that 0 is special. All it can learn is how
the symbols combine.
"""

import numpy as np

SYMBOLS = ["=", "+", "-", "/"]


# @build 14.01 divide
# a / b modulo a prime p: the c with c times b equal to a (mod p). It is a
# times the inverse of b, the number that b times is 1, and Fermat's little
# theorem gives it: b^(p-1) is 1 (mod p) for any b that is not a multiple
# of p, so b^(p-2) is the inverse (Python's pow(b, p - 2, p) computes it
# without the huge power). b = 0 has no inverse: a ZeroDivisionError.
def divide(a, b, p):
    if b % p == 0:
        raise ZeroDivisionError(f"{a} / {b}: {b} has no inverse modulo {p}")
    return a * pow(b, p - 2, p) % p
# @end


OPERATIONS = {"+": lambda a, b, p: (a + b) % p, "-": lambda a, b, p: (a - b) % p, "/": divide}


# @build 14.01 equations
# Every equation of the operation op ("+", "-" or "/") modulo the prime
# p, one row (a, b, c) each, in order of a and then b: a and b each from 0
# to p - 1, except that b starts at 1 for division (the paper's 0 <= x < p,
# 0 < y < p). p x p rows, p x (p - 1) for division. int64.
def equations(p, op):
    f = OPERATIONS[op]
    first = 1 if op == "/" else 0
    return np.array([(a, b, f(a, b, p)) for a in range(p) for b in range(first, p)], dtype=np.int64)
# @end


# @build 14.01 tokens
# The rows (a, b, c) as the paper writes them, five tokens each: a, the
# operation, b, "=", c. A residue r is token r; the tokens after the p
# residues are SYMBOLS in order, so "=" is token p and op is p + its place
# in SYMBOLS. (n, 5), int64.
def tokens(rows, p, op):
    n = len(rows)
    return np.stack([rows[:, 0], np.full(n, p + SYMBOLS.index(op)), rows[:, 1], np.full(n, p), rows[:, 2]],
                    axis=1).astype(np.int64)
# @end


# @build 14.01 split
# The paper's split: every equation of op modulo p, as tokens, put in a
# random order drawn from a numpy Generator seeded with seed; the first
# round(fraction x n) are the training set, the rest the validation set.
# Each equation is in exactly one of the two, and the same seed always
# gives the same split. Returns (train, val), each (rows, 5).
def split(p, op, fraction, seed):
    rows = tokens(equations(p, op), p, op)
    order = np.random.default_rng(seed).permutation(len(rows))
    k = round(fraction * len(rows))
    return rows[order[:k]], rows[order[k:]]
# @end


def names(p):
    """The text of each token number: the residues, then SYMBOLS."""
    return [str(r) for r in range(p)] + SYMBOLS
