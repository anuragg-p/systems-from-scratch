"""LoRA (Hu et al. 2021): train a small change to a weight instead of the weight (12.02).

    LoRA(linear, r, alpha)       a frozen nn.Linear, plus (alpha / r) B A x: B (out, r) from 0, A (r, in) random
    adapt(model, r, alpha, ...)  every GPT block's attention query and value made LoRA layers; the rest frozen
    merge(model)                 each LoRA layer back into one nn.Linear holding W + (alpha / r) B A
    trained(model)               how many numbers the optimiser changes: those with requires_grad

Fine-tuning changes every weight W of the body. Hu et al.'s idea is that
the change a task needs, W' - W, is close to a matrix of low rank, so it
can be written as a product B A of two thin matrices: for a layer of
in_features inputs and out_features outputs, B is out x r and A is r x
in, r numbers wide in the middle, and only A and B are trained. B starts
at 0, so the adapted model starts as exactly the model it adapts; A
starts random, so B's gradient is not 0. The change is scaled by
alpha / r, so that a rank chosen later needs no new learning rate ("we
simply set alpha to the first r we try and do not tune it", section 4.1).

Once trained, B A can be added into W: one Linear layer again, as fast
as the original, giving the same outputs (merge).
"""

import math

import torch
from torch import nn


# @build 12.02 LoRA
# A Linear layer (linear: an nn.Linear, frozen here: its weight and bias
# no longer need gradients) with a trained change of rank r beside it:
# forward(x) is linear(x) + (alpha / r) (x A^T) B^T, A of shape (r,
# in_features) drawn from a normal distribution of sd 1 / sqrt(in_features)
# (Hu et al.: "a random Gaussian initialization for A"), B of shape
# (out_features, r) all 0 ("zero for B, so Delta W = BA is zero at the
# beginning of training"). delta() is that change as a matrix, (alpha / r)
# B A, the shape of linear's weight.
class LoRA(nn.Module):
    def __init__(self, linear, r, alpha):
        super().__init__()
        self.linear = linear
        for p in linear.parameters():
            p.requires_grad_(False)
        out_features, in_features = linear.weight.shape
        like = dict(dtype=linear.weight.dtype, device=linear.weight.device)
        self.A = nn.Parameter(torch.randn(r, in_features, **like) / math.sqrt(in_features))
        self.B = nn.Parameter(torch.zeros(out_features, r, **like))
        self.r, self.alpha, self.scale = r, alpha, alpha / r

    def forward(self, x):
        return self.linear(x) + (x @ self.A.T @ self.B.T) * self.scale

    def delta(self):
        return (self.B @ self.A) * self.scale
# @end


# @build 12.02 adapt
# Adapt a GPT (models/gpt.py's) for training with LoRA: every weight of
# model frozen, then in each block the attention layers named in `names`
# (Hu et al.'s W_q and W_v: query and value) replaced by LoRA layers of
# rank r around them. Everything else stays frozen; a classifier's head,
# when model is one, is made trainable again by the caller. Returns model.
def adapt(model, r, alpha, names=("query", "value")):
    for p in model.parameters():
        p.requires_grad_(False)
    for block in model.blocks:
        for name in names:
            setattr(block.attention, name, LoRA(getattr(block.attention, name), r, alpha))
    return model
# @end


# @build 12.02 merge
# Each LoRA layer of model (a GPT that adapt changed) replaced by one
# nn.Linear whose weight is the frozen weight plus delta(): the same
# outputs, up to rounding, with no extra work at each step. Returns model.
def merge(model):
    for block in model.blocks:
        for name, layer in list(block.attention.named_children()):
            if isinstance(layer, LoRA):
                with torch.no_grad():
                    layer.linear.weight += layer.delta()
                setattr(block.attention, name, layer.linear)
    return model
# @end


# @build 12.02 trained
# The numbers training changes: every parameter that needs a gradient.
def trained(model):
    return sum(p.numel() for p in model.parameters() if p.requires_grad)
# @end
