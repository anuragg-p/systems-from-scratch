"""Functions of tensors that layers and losses are made of: torch.nn.functional, as F.

A softmax turns a row of scores (logits) into probabilities: e to the power
of each, divided by their sum. Written that way it overflows: e**89 is
already past the largest float32, and inf / inf is nan. Subtracting the
row's largest score first changes nothing in exact arithmetic (it cancels
between top and bottom) and keeps every power at most 1. Its logarithm,
log_softmax, is computed directly, never as the log of a softmax, so a
probability too small to store still has a finite log.

Cross-entropy is the loss of a classifier: minus the log of the probability
it gave the right class, averaged over the batch.
"""

import numpy as np

from engine import tensors as _t
from engine.tensors import Tensor


def relu(input):
    return input.relu()


def tanh(input):
    return input.tanh()


# @build 02.04 log_softmax
# The log of the softmax along dim, without overflow: x - max - log(sum(e**(x
# - max))). Its gradient, worked out once on paper: for an output gradient
# g, the input gradient is g - softmax * (the sum of g along dim).
def log_softmax(input, dim):
    x = input.data
    shifted = x - x.max(axis=dim, keepdims=True)
    out = _t._result(shifted - np.log(np.exp(shifted).sum(axis=dim, keepdims=True)), (input,),
                     "LogSoftmaxBackward")
    if out.requires_grad:
        def _backward():
            g = out.grad.data
            input._accumulate(g - np.exp(out.data) * g.sum(axis=dim, keepdims=True))
        out._backward = _backward
    return out
# @end


# @build 02.04 softmax
# Probabilities along dim that add up to 1: e to the power of log_softmax,
# so its gradient comes from the two operations it is made of.
def softmax(input, dim):
    return log_softmax(input, dim).exp()
# @end


# @build 02.04 cross_entropy
# input: scores of shape (batch, classes); target: the right class of each
# row, as whole numbers; a different number of rows and classes is an
# error. The loss of each row is minus the log_softmax of its score for the
# right class (picked out by indexing); reduction says what to return:
# their mean ("mean", the default), their sum ("sum"), or all of them
# ("none").
def cross_entropy(input, target, reduction="mean"):
    target = target.data if isinstance(target, Tensor) else np.asarray(target)
    if len(target) != input.shape[0]:
        raise ValueError(f"Expected input batch_size ({input.shape[0]}) to match target batch_size "
                         f"({len(target)}).")
    losses = -log_softmax(input, 1)[np.arange(len(target)), target]
    if reduction == "mean":
        return losses.mean()
    if reduction == "sum":
        return losses.sum()
    if reduction == "none":
        return losses
    raise ValueError(f"{reduction} is not a valid value for reduction")
# @end


# @build 05.02 dropout
# In training, each number is set to 0 with probability p and the rest are
# multiplied by 1 / (1 - p), so the expected value of every number is what
# it was. When not training it is the identity: the whole network is used,
# at the size it learned. The mask comes from the engine's generator, so
# manual_seed decides it.
def dropout(input, p=0.5, training=True):
    if not training or p == 0:
        return input
    keep = _t.generator().random(input.data.shape) >= p
    return input * Tensor((keep / (1 - p)).astype(input.data.dtype))
# @end
