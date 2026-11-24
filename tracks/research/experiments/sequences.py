"""Training, scoring and sampling models of the next symbol on PyTorch: what 07.02 on share.

From 07.02 on the text is a 1-d tensor of character numbers, made from
data/shakespeare.py's numpy array once and put on the run's device; a
batch is picked out of it by positions (data/ stays numpy, as images.py
has it for pictures). Every score is in bits per character on text the
model never saw: F.cross_entropy's mean, which is in nats (natural
logarithms), divided by ln 2.
"""

import math

import torch
import torch.nn.functional as F


# @build 07.02 bits
# The mean cross-entropy of scores, of shape (..., V), for targets, the
# same shape without V, in bits: F.cross_entropy's mean is -ln p, in nats,
# and log2 p = ln p / ln 2.
def bits(scores, targets):
    return F.cross_entropy(scores.reshape(-1, scores.shape[-1]), targets.reshape(-1)) / math.log(2)
# @end


# @build 07.02 contexts
# For each of positions (a 1-d int64 tensor, each at least n): the n
# character numbers of ids (a 1-d tensor) just before it, as one row of a
# (len(positions), n) batch, and the character at it.
def contexts(ids, positions, n):
    return ids[positions[:, None] - n + torch.arange(n, device=ids.device)], ids[positions]
# @end


# @build 07.02 context_bits
# A model of the next character from the n before it, scored on ids (a
# 1-d tensor): its bits per character over every position from n on, in
# batches, in eval mode and without a graph; then back in training mode.
def context_bits(model, ids, n, batch=8192):
    model.eval()
    positions = torch.arange(n, len(ids), device=ids.device)
    total = 0.0
    with torch.no_grad():
        for start in range(0, len(positions), batch):
            x, y = contexts(ids, positions[start:start + batch], n)
            total += bits(model(x), y).item() * len(y)
    model.train()
    return total / len(positions)
# @end


# @build 07.02 sample
# n symbols drawn one at a time after prompt (a list of numbers):
# next_scores(ids), given a 1-d tensor of every number so far, returns the
# next one's scores; their softmax, at a temperature (scores divided by it:
# below 1 sharper, above 1 flatter), are its chances, and torch.multinomial
# draws from them with generator (a seeded torch.Generator, so a seed
# always gives the same text). Returns the n numbers drawn.
def sample(next_scores, prompt, n, generator, temperature=1.0):
    ids = list(prompt)
    with torch.no_grad():
        for _ in range(n):
            p = F.softmax(next_scores(torch.tensor(ids)).float().cpu() / temperature, dim=-1)
            ids.append(int(torch.multinomial(p, 1, generator=generator)))
    return ids[len(prompt):]
# @end


# @build 07.03 windows
# For each of starts (a 1-d int64 tensor): the `length` numbers of ids
# from it on, a row of a (len(starts), length) batch, and the `length`
# after them, each one place later: the next symbol at every position.
def windows(ids, starts, length):
    at = starts[:, None] + torch.arange(length, device=ids.device)
    return ids[at], ids[at + 1]
# @end


# @build 07.03 window_bits
# A model that scores the next symbol at every position of a window,
# predict(x) giving scores of shape (B, T, V) for x of shape (B, T), the
# scores at t from x[:, :t + 1] alone, scored on ids: bits per symbol
# over every position from warm on, without a graph. The positions are cut
# into spans of `span`, each read in a window that starts `warm` symbols
# before it, and only the span's own positions count: each has at least
# `warm` symbols before it in its window. Windows go in batches of batch;
# the last, shorter one alone.
def window_bits(predict, ids, span, warm, batch=64):
    firsts = list(range(0, len(ids) - warm, span))
    length = warm - 1 + span
    full = [s for s in firsts if s + length < len(ids)]
    groups = [full[i:i + batch] for i in range(0, len(full), batch)] + [[s] for s in firsts if s not in full]
    total, count = 0.0, 0
    with torch.no_grad():
        for group in groups:
            n = min(length, len(ids) - 1 - group[0])
            x, y = windows(ids, torch.tensor(group, device=ids.device), n)
            scores, y = predict(x)[:, warm - 1:], y[:, warm - 1:]
            total += bits(scores, y).item() * y.numel()
            count += y.numel()
    return total / count
# @end
