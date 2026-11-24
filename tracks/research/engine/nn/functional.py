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


# @from 06.01
def _pair(v):
    """A size given as one number or as (height, width): always the pair."""
    return (v, v) if isinstance(v, int) else tuple(v)
# @end


# @build 06.01 _windows
# Every kh by kw window of x, a numpy array of shape (n, c, h, w), that a
# kernel visits when it moves stride (a pair) pixels at a time, left to
# right and top to bottom: an array of shape (n, c, oh, ow, kh, kw) with
# oh = (h - kh) // stride + 1 windows down and ow = (w - kw) // stride + 1
# across. numpy's sliding_window_view gives every window as a view of x's
# own numbers, copying nothing (overlapping windows share them); keeping
# every stride-th window down and across is a view too.
def _windows(x, kh, kw, stride):
    win = np.lib.stride_tricks.sliding_window_view(x, (kh, kw), axis=(2, 3))
    return win[:, :, ::stride[0], ::stride[1]]
# @end


# @build 06.01 _scatter
# The way back from _windows: g holds one number for every place of every
# window (shape (n, c, oh, ow, kh, kw)), and each goes back to the pixel of
# x (shape `shape`) it was read from, added, since overlapping windows read
# a pixel more than once. One step for each of the kh * kw places in a
# window: place (i, j) of the window at (r, s) read pixel (r * stride + i,
# s * stride + j), so all the windows' place (i, j) together land on every
# stride-th pixel from (i, j).
def _scatter(g, shape, stride):
    out = np.zeros(shape, dtype=g.dtype)
    oh, ow, kh, kw = g.shape[2:]
    sh, sw = stride
    for i in range(kh):
        for j in range(kw):
            out[:, :, i:i + sh * (oh - 1) + 1:sh, j:j + sw * (ow - 1) + 1:sw] += g[:, :, :, :, i, j]
    return out
# @end


# @build 06.01 conv2d
# A convolution: weight holds out_channels filters, each of shape
# (in_channels, kh, kw), and every filter is laid on every window of the
# input (shape (n, in_channels, h, w)), padded first with `padding` zeros
# on every side: the sum of the products is one number of the output, of
# shape (n, out_channels, oh, ow). The same weights at every position.
# Written as one matrix product: every window flattened into a row (one
# row per window of every image, the copy numpy must make), every filter
# into a row of weight, and rows @ filters.T, then the bias of each
# filter added. Its gradient is the matrix product's (02.03): the filters'
# from the rows, and the rows' from the filters, which _scatter takes back
# to the pixels each window read, and the padding is cut off again.
def conv2d(input, weight, bias=None, stride=1, padding=0):
    stride, (ph, pw) = _pair(stride), _pair(padding)
    x = np.pad(input.data, ((0, 0), (0, 0), (ph, ph), (pw, pw)))
    o, c, kh, kw = weight.shape
    win = _windows(x, kh, kw, stride)
    n, _, oh, ow = win.shape[:4]
    rows = win.transpose(0, 2, 3, 1, 4, 5).reshape(n * oh * ow, c * kh * kw)
    out = rows @ weight.data.reshape(o, -1).T
    if bias is not None:
        out = out + bias.data
    parents = (input, weight) if bias is None else (input, weight, bias)
    out = _t._result(out.reshape(n, oh, ow, o).transpose(0, 3, 1, 2), parents, "ConvolutionBackward")
    if out.requires_grad:
        def _backward():
            g = out.grad.data.transpose(0, 2, 3, 1).reshape(n * oh * ow, o)
            weight._accumulate((g.T @ rows).reshape(weight.shape))
            if bias is not None:
                bias._accumulate(g.sum(0))
            if input.requires_grad:
                back = (g @ weight.data.reshape(o, -1)).reshape(n, oh, ow, c, kh, kw).transpose(0, 3, 1, 2, 4, 5)
                gx = _scatter(back, x.shape, stride)
                input._accumulate(gx[:, :, ph:ph + input.shape[2], pw:pw + input.shape[3]])
        out._backward = _backward
    return out
# @end


# @build 06.01 max_pool2d
# The largest number of every kernel_size window (stride: kernel_size
# unless given; padding counts as minus infinity, so it is never the
# largest). Only that one number moved the output, so the gradient goes
# back to it alone, and to the first of several equal ones, as PyTorch's
# does.
def max_pool2d(input, kernel_size, stride=None, padding=0):
    (kh, kw), (ph, pw) = _pair(kernel_size), _pair(padding)
    stride = _pair(kernel_size if stride is None else stride)
    x = np.pad(input.data, ((0, 0), (0, 0), (ph, ph), (pw, pw)), constant_values=-np.inf)
    win = _windows(x, kh, kw, stride)
    flat = win.reshape(win.shape[:4] + (kh * kw,))
    at = flat.argmax(-1)
    out = _t._result(np.take_along_axis(flat, at[..., None], -1)[..., 0], (input,), "MaxPool2DBackward")
    if out.requires_grad:
        def _backward():
            g = np.zeros(flat.shape, dtype=flat.dtype)
            np.put_along_axis(g, at[..., None], out.grad.data[..., None], -1)
            gx = _scatter(g.reshape(win.shape), x.shape, stride)
            input._accumulate(gx[:, :, ph:ph + input.shape[2], pw:pw + input.shape[3]])
        out._backward = _backward
    return out
# @end
