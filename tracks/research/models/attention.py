"""Attention: a weighted sum over positions, the weights a softmax of scores (07.04).

    attend(scores, values)               the softmax of scores over the positions (their last axis), and
                                         the sum of values those weights give: (summed, weights)
    Additive(query_size, key_size, size) Bahdanau, Cho and Bengio's scores, v . tanh(W q + U k), for every
                                         query q and every key k

Three steps, kept apart on purpose: a score for every pair of a query
and a position, a softmax over the positions, and the weighted sum of the
values there. Here (07.04) the query is the decoder's state, and the keys
and the values are the encoder's states. Module 08's self-attention keeps
attend as it is and changes only the scores: queries, keys and values all
from one sequence, a scaled dot product, and a mask.
"""

import torch
from torch import nn
import torch.nn.functional as F


# @build 07.04 attend
# scores, of shape (..., queries, positions), made weights by a softmax
# over the positions (each query's weights are positive and add up to 1),
# and values, (..., positions, size), summed with those weights: one
# vector of `size` for each query, (..., queries, size). Returns the sums
# and the weights.
def attend(scores, values):
    weights = F.softmax(scores, dim=-1)
    return weights @ values, weights
# @end


# @build 07.04 Additive
# The paper's scores (its appendix A.1.2): for a query q (the decoder's
# state) and a key k (an encoder state), v . tanh(W q + U k), W, U and v
# learned, without biases as the paper writes them. queries are (batch,
# Tq, query_size), keys (batch, S, key_size); every query is added to
# every key (broadcasting, 02.02), giving scores of shape (batch, Tq, S).
class Additive(nn.Module):
    def __init__(self, query_size, key_size, size):
        super().__init__()
        self.W = nn.Linear(query_size, size, bias=False)
        self.U = nn.Linear(key_size, size, bias=False)
        self.v = nn.Linear(size, 1, bias=False)

    def forward(self, queries, keys):
        return self.v(torch.tanh(self.W(queries)[:, :, None] + self.U(keys)[:, None]))[..., 0]
# @end
