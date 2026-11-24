"""A GPT: attention inside one sequence, each position looking only at those before it (08.01 to 08.03).

    causal_mask(T)                       True where position i may look at position j: j <= i
    self_attend(q, k, v, mask, scale)    scaled dot-product scores, the future masked, 07.04's attend
    SelfAttention(width, ...)            queries, keys and values from one sequence, and a Linear layer out
    gelu(x)                              GPT-2's GELU: 0.5 x (1 + tanh(sqrt(2 / pi) (x + 0.044715 x^3)))  # @from 08.02
    MLP(width, bias)                     Linear to 4 x width, gelu, Linear back                          # @from 08.02
    Block(width, heads, dropout, bias)   layer norm, attention, add; layer norm, MLP, add               # @from 08.02
    Positions(context, width)            a learned vector for each place, added to each embedding       # @from 08.03
    GPT(vocab, context, ...)             embeddings, blocks, a last layer norm, scores tied to the embeddings  # @from 08.02
    RMSNorm(width, eps)                  each vector over the root of its mean square, times a learned gain  # @from 10.01
    Rotary(d, base)                      queries and keys turned by angles that grow with their place       # @from 10.02
    SwiGLU(width, hidden, bias)          a gated MLP: down(silu(gate(x)) * up(x))                          # @from 10.03

07.04's attention looked from one sequence (the decoder's) at another
(the encoder's states). Self-attention looks from a sequence at itself:
every position makes a query, a key and a value from its own vector, and
its new vector is the weighted sum of the values of the positions it may
look at, the weights a softmax of its query's dot products with their
keys. A model of the next character may only look back, so the scores of
later positions are set to -inf before the softmax (the mask).

Every piece is written out, and each is its own function or class, so
that a later module can swap one: module 11 swaps self_attend for
PyTorch's fused F.scaled_dot_product_attention, which computes the same
numbers.
Module 10 swaps the layer norm, the MLP and the positions.                # @from 08.03
Each piece module 10 brings is chosen by an argument of GPT whose         # @from 10.01
default is module 08's piece, so a model of 08 or 09 is built as it was:  # @from 10.01
    norm="rms"           RMSNorm for every layer norm (10.01)             # @from 10.01
    positions="rotary"   Rotary inside attention, no Positions (10.02)    # @from 10.02
    mlp="swiglu"         SwiGLU for the MLP (10.03)                       # @from 10.03
    kv_heads=k           k heads of keys and values for all heads (10.04) # @from 10.04
The shapes are chosen so that GPT-2 small's published weights load into   # @from 08.02
GPT without changing it (09.03).                                          # @from 08.02
"""

import math

import torch
from torch import nn
import torch.nn.functional as F

from models.attention import attend


# @build 08.01 causal_mask
# A (T, T) table of booleans, True where position i (the row) may look at
# position j (the column): at itself and every position before it, j <= i,
# the lower triangle with its diagonal (torch.tril).
def causal_mask(T, device=None):
    return torch.ones(T, T, dtype=torch.bool, device=device).tril()
# @end


# @build 08.01 self_attend
# Attention of a sequence on itself. q, k and v are (..., T, d): a query,
# a key and a value for each of T positions. The score of position i for
# position j is q_i . k_j, all at once as q @ k transposed, (..., T, T),
# divided by sqrt(d) when scale is set (Vaswani et al. 2017, section
# 3.2.1). With mask, every score above the diagonal (a later position) is
# -inf, which the softmax makes a weight of exactly 0. Then 07.04's attend:
# the softmax over j and the weighted sum of the values. Returns the sums,
# (..., T, d), and the weights, (..., T, T).
def self_attend(q, k, v, mask=True, scale=True):
    scores = q @ k.transpose(-2, -1)
    if scale:
        scores = scores / math.sqrt(q.shape[-1])
    if mask:
        scores = scores.masked_fill(~causal_mask(q.shape[-2], q.device), float("-inf"))
    return attend(scores, v)
# @end


# @build 08.01 SelfAttention
# Self-attention as a layer, for x of shape (batch, T, width): a query, a
# key and a value made from each position's vector by three Linear layers
# of their own, self_attend, and a fourth Linear layer, out, on the result.
# With heads (08.02), the width is cut into `heads` pieces of width / heads
# numbers and each piece attends on its own, with its own weights; their
# results are put side by side again before out. mask and scale are
# self_attend's, there to be turned off (08.01). qkv(x) gives the queries,
# keys and values, (batch, heads, T, width / heads) from 08.02 on.
class SelfAttention(nn.Module):
    # @from 08.02
    # @from 10.02
    def __init__(self, width, heads=1, bias=True, mask=True, scale=True,
                 rotary=None,
                 kv_heads=None,                                               # @from 10.04
                 ):
    # @else
    # def __init__(self, width, heads=1, bias=True, mask=True, scale=True):
    # @end
    # @else
    # def __init__(self, width, bias=True, mask=True, scale=True):
    # @end
        super().__init__()
        self.query = nn.Linear(width, width, bias=bias)
        # @from 10.04
        kv_heads = kv_heads or heads
        self.key = nn.Linear(width, width // heads * kv_heads, bias=bias)
        self.value = nn.Linear(width, width // heads * kv_heads, bias=bias)
        # @else
        # self.key = nn.Linear(width, width, bias=bias)
        # self.value = nn.Linear(width, width, bias=bias)
        # @end
        self.out = nn.Linear(width, width, bias=bias)
        self.mask, self.scale = mask, scale
        # @from 08.02
        if width % heads:
            raise ValueError(f"a width of {width} does not cut into {heads} heads")
        self.heads = heads
        # @end
        # @from 10.02
        self.rotary = Rotary(width // heads, rotary) if rotary else None
        # @end
        # @from 10.04
        if heads % kv_heads:
            raise ValueError(f"{heads} query heads do not share {kv_heads} key and value heads evenly")
        self.kv_heads = kv_heads
        # @end

    def qkv(self, x):
        q, k, v = self.query(x), self.key(x), self.value(x)
        # @from 08.02
        B, T, width = x.shape
        # @from 10.04
        q, k, v = (t.view(B, T, -1, width // self.heads).transpose(1, 2) for t in (q, k, v))
        # @else
        # q, k, v = (t.view(B, T, self.heads, width // self.heads).transpose(1, 2) for t in (q, k, v))
        # @end
        # @end
        # @from 10.02
        if self.rotary is not None:
            q, k = self.rotary(q), self.rotary(k)
        # @end
        # @from 10.04
        if self.kv_heads < self.heads:
            k, v = (t.repeat_interleave(self.heads // self.kv_heads, dim=1) for t in (k, v))
        # @end
        return q, k, v

    def forward(self, x):
        y, _ = self_attend(*self.qkv(x), self.mask, self.scale)
        # @from 08.02
        y = y.transpose(1, 2).reshape(x.shape)
        # @end
        return self.out(y)
# @end


# @build 08.02 gelu
# GPT-2's GELU (Hendrycks and Gimpel 2016, in its tanh form, as GPT-2's
# code writes it): about x for large x, about 0 for very negative x, and a
# smooth bend between, a little below 0 just left of it. F.gelu(x,
# approximate="tanh") gives the same numbers.
def gelu(x):
    return 0.5 * x * (1 + torch.tanh(math.sqrt(2 / math.pi) * (x + 0.044715 * x ** 3)))
# @end


# @build 08.02 MLP
# What a block does to each position on its own, after attention has
# moved information between them: a Linear layer to 4 x width numbers,
# gelu, and a Linear layer back to width (up and down).
class MLP(nn.Module):
    def __init__(self, width, bias=True):
        super().__init__()
        self.up = nn.Linear(width, 4 * width, bias=bias)
        self.down = nn.Linear(4 * width, width, bias=bias)

    def forward(self, x):
        return self.down(gelu(self.up(x)))
# @end


# @build 08.02 Block
# One block of the residual stream x, (batch, T, width): attention reads a
# layer-normalised copy of x (04.04) and its result is added to x (04.05);
# then the MLP does the same. Nothing else changes x, so every block, and
# the output, can read what the embeddings put there. With dropout (05.02)
# each result is dropped before it is added, in training only.
class Block(nn.Module):
    # @from 10.01
    def __init__(self, width, heads, dropout=0.0, bias=True,
                 norm="layer",
                 rotary=None,                                                 # @from 10.02
                 mlp="gelu", hidden=None,                                     # @from 10.03
                 kv_heads=None,                                               # @from 10.04
                 ):
    # @else
    # def __init__(self, width, heads, dropout=0.0, bias=True):
    # @end
        super().__init__()
        # @from 10.01
        self.norm1 = RMSNorm(width) if norm == "rms" else nn.LayerNorm(width, bias=bias)
        # @else
        # self.norm1 = nn.LayerNorm(width, bias=bias)
        # @end
        # @from 10.02
        self.attention = SelfAttention(width, heads, bias,
                                       rotary=rotary,
                                       kv_heads=kv_heads,                     # @from 10.04
                                       )
        # @else
        # self.attention = SelfAttention(width, heads, bias)
        # @end
        # @from 10.01
        self.norm2 = RMSNorm(width) if norm == "rms" else nn.LayerNorm(width, bias=bias)
        # @else
        # self.norm2 = nn.LayerNorm(width, bias=bias)
        # @end
        # @from 10.03
        self.mlp = SwiGLU(width, hidden or 8 * width // 3, bias) if mlp == "swiglu" else MLP(width, bias)
        # @else
        # self.mlp = MLP(width, bias)
        # @end
        self.dropout = dropout

    def forward(self, x):
        x = x + F.dropout(self.attention(self.norm1(x)), self.dropout, self.training)
        x = x + F.dropout(self.mlp(self.norm2(x)), self.dropout, self.training)
        return x
# @end


# @build 08.03 Positions
# Where each position is: a learned vector of width numbers for each place
# 0 to context - 1 (one row of weight for each, drawn like the embeddings
# and trained with them), the row of each position added to the vector at
# that position of x, (batch, T, width). There is no row for a place past
# context - 1: a longer x is a ValueError that says so.
class Positions(nn.Module):
    def __init__(self, context, width):
        super().__init__()
        self.weight = nn.Parameter(0.02 * torch.randn(context, width))

    def forward(self, x):
        T = x.shape[1]
        if T > len(self.weight):
            raise ValueError(f"{T} positions, but there are learned vectors for {len(self.weight)}")
        return x + self.weight[:T]
# @end


# @build 10.01 RMSNorm
# Zhang and Sennrich's (2019) root mean square layer normalisation: each
# vector of x (..., width) divided by the root of the mean of its squares
# (eps added under the root, as layer norm adds it to the variance), then
# times a learned gain for each of its numbers, which starts at 1. Layer
# norm (04.04) without its first step, taking the mean away, and without
# its bias. torch.nn.RMSNorm computes the same.
class RMSNorm(nn.Module):
    def __init__(self, width, eps=1e-5):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(width))
        self.eps = eps

    def forward(self, x):
        return x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps) * self.weight
# @end


# @build 10.02 Rotary
# Su et al.'s (2021) rotary positions, for queries or keys x of shape
# (..., T, d), d even: the d numbers of each vector are d / 2 pairs, and
# pair i of the vector at place m is turned through the angle m theta_i,
# theta_i = base^(-2i / d): the first pair by a radian a place, the last
# by about a ten-thousandth of one (base 10000). A query turned for place
# m and a key turned for place n then have a dot product that depends on
# their places only through n - m, and each keeps its length. A pair is
# numbers i and i + d / 2, as transformers' Llama has it, so SmolLM2's
# weights load as they are (10.04); the paper pairs neighbours, 2i and
# 2i + 1, the same turning with a projection's rows in another order.
# start is the place of x's first vector.
class Rotary(nn.Module):
    def __init__(self, d, base=10000.0):
        super().__init__()
        self.d, self.base = d, base

    def forward(self, x, start=0):
        half = self.d // 2
        theta = 1.0 / self.base ** (torch.arange(0, self.d, 2, device=x.device).to(x.dtype) / self.d)
        angles = (torch.arange(start, start + x.shape[-2], device=x.device).to(x.dtype)[:, None] * theta).repeat(1, 2)
        return x * angles.cos() + torch.cat([-x[..., half:], x[..., :half]], dim=-1) * angles.sin()
# @end


# @build 10.03 SwiGLU
# Shazeer's (2020) gated MLP, as Llama and SmolLM2 have it: two Linear
# layers from width up to `hidden` numbers, gate and up; the gate's
# numbers through SiLU (x times the sigmoid of x: Swish with beta 1,
# F.silu) multiply up's, number by number, a gated linear unit (Dauphin
# et al. 2017); a Linear layer down back to width. Three matrices where
# MLP has two, so with hidden = 2/3 x 4 x width the weights are as many.
class SwiGLU(nn.Module):
    def __init__(self, width, hidden, bias=True):
        super().__init__()
        self.gate = nn.Linear(width, hidden, bias=bias)
        self.up = nn.Linear(width, hidden, bias=bias)
        self.down = nn.Linear(hidden, width, bias=bias)

    def forward(self, x):
        return self.down(F.silu(self.gate(x)) * self.up(x))
# @end


# @build 08.02 GPT
# The whole model of the next symbol, for ids of shape (batch, T). embed:
# each symbol's embedding, a learned vector of width numbers (with
# positions, 08.03, plus Positions' vector for its place), dropped with
# dropout in training: the start of the residual stream.
# forward: `layers` blocks on it, a last layer norm, and a score for every
# symbol of the vocabulary: the dot product with that symbol's own
# embedding (the output layer is the embedding table, tied, as GPT-2's is).
# Returns the scores, (batch, T, vocab). Starts as GPT-2 does: every weight
# from a normal distribution of sd 0.02, biases 0, layer norms 1 and 0,
# and the two layers that add into the stream (attention's out, the MLP's
# down) by sqrt(2 x layers) smaller, so the stream does not grow with depth.
class GPT(nn.Module):
    # @from 08.03
    # @from 10.01
    def __init__(self, vocab, context, layers=4, heads=4, width=128, dropout=0.0, bias=True, positions=True,
                 norm="layer",
                 base=10000.0,                                                # @from 10.02
                 mlp="gelu", hidden=None,                                     # @from 10.03
                 kv_heads=None,                                               # @from 10.04
                 ):
    # @else
    # def __init__(self, vocab, context, layers=4, heads=4, width=128, dropout=0.0, bias=True, positions=True):
    # @end
    # @else
    # def __init__(self, vocab, context, layers=4, heads=4, width=128, dropout=0.0, bias=True):
    # @end
        super().__init__()
        self.context, self.dropout = context, dropout
        self.tokens = nn.Embedding(vocab, width)
        # @from 08.03
        # @from 10.02
        self.positions = Positions(context, width) if positions is True else None
        # @else
        # self.positions = Positions(context, width) if positions else None
        # @end
        # @end
        # @from 10.01
        self.blocks = nn.ModuleList(Block(width, heads, dropout, bias,
                                          norm=norm,
                                          rotary=base if positions == "rotary" else None,  # @from 10.02
                                          mlp=mlp, hidden=hidden,                          # @from 10.03
                                          kv_heads=kv_heads,                               # @from 10.04
                                          ) for _ in range(layers))
        self.norm = RMSNorm(width) if norm == "rms" else nn.LayerNorm(width, bias=bias)
        # @else
        # self.blocks = nn.ModuleList(Block(width, heads, dropout, bias) for _ in range(layers))
        # self.norm = nn.LayerNorm(width, bias=bias)
        # @end
        for name, p in self.named_parameters():
            if name.endswith("bias"):
                nn.init.zeros_(p)
            elif "norm" not in name:
                into_stream = name.endswith("attention.out.weight") or name.endswith("mlp.down.weight")
                nn.init.normal_(p, 0.0, 0.02 / math.sqrt(2 * layers) if into_stream else 0.02)

    def embed(self, ids):
        x = self.tokens(ids)
        # @from 08.03
        if self.positions is not None:
            x = self.positions(x)
        # @end
        return F.dropout(x, self.dropout, self.training)

    def forward(self, ids):
        x = self.embed(ids)
        for block in self.blocks:
            x = block(x)
        return self.norm(x) @ self.tokens.weight.T
# @end
