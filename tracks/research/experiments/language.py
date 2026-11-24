"""Training a model of the next character on windows of the text: the loop module 08 shares.

07's scripts each trained their own way (positions, streams, tasks). From
08.01 on every model reads a window of `context` characters and scores
the next character at every position of it at once, so they share one
loop: a batch is cfg.batch windows from random places of the training
text (07.03's windows), the loss is the mean of their bits per character
(07.02's bits), and the optimiser is AdamW (03.04) with a warmup and a
cosine decay (03.05), the gradient clipped to cfg.clip (07.03).
"""

import torch

import lab
from experiments.sequences import bits, windows
from models.gpt import self_attend                                    # @from 08.02


# @build 08.01 train
# Train model, one seed, for cfg.steps steps, on ids (the training text, a
# 1-d tensor on the device dev): each step cfg.batch windows of
# cfg.context characters, starting at places drawn from run.rng, and the
# character after every position of each as its target. AdamW at cfg.lr,
# its weight decay cfg.weight_decay on the weight matrices and embeddings
# only (not on biases or layer norms, as GPT-2 does), the rate rising over
# cfg.warmup steps and then falling to 0 along half a cosine; the gradient
# clipped to a length of cfg.clip (0: not clipped). Every cfg.every steps,
# and at the last, the batch's bits go to the run's log. Returns the model.
# @from 08.04
def train(model, cfg, run, dev, ids, held=None):
# @else
# def train(model, cfg, run, dev, ids):
# @end
    matrices = [p for p in model.parameters() if p.dim() >= 2]
    others = [p for p in model.parameters() if p.dim() < 2]
    opt = torch.optim.AdamW([{"params": matrices, "weight_decay": cfg.weight_decay},
                             {"params": others, "weight_decay": 0.0}], lr=cfg.lr)
    scheduler = torch.optim.lr_scheduler.LambdaLR(opt, lab.warmup_cosine(cfg.warmup, cfg.steps))
    for step in range(cfg.steps):
        starts = torch.from_numpy(run.rng.integers(0, len(ids) - cfg.context, cfg.batch)).to(dev)
        x, y = windows(ids, starts, cfg.context)
        loss = bits(model(x), y)
        opt.zero_grad()
        loss.backward()
        if cfg.clip:
            torch.nn.utils.clip_grad_norm_(model.parameters(), cfg.clip)
        opt.step()
        scheduler.step()
        if step % cfg.every == 0 or step == cfg.steps - 1:
            # @from 08.04
            # with held, a fixed batch (x, y) of held-out windows: their bits too
            row = {"step": step, "bits": loss.item()}
            if held is not None:
                row["held_bits"] = held_bits(model, *held)
            run.log(**row)
            # @else
            # run.log(step=step, bits=loss.item())
            # @end
    return model
# @end


# @build 08.02 attention_maps
# Every block's attention weights when model, a GPT, reads ids (batch,
# T): a list with one (batch, heads, T, T) tensor for each block, row i of
# a head's table being its weights over the positions j <= i. The model is
# run block by block as its forward does (its embed, then each block, the
# weights taken from the block's own queries and keys), in eval mode,
# without a graph; then put back in training mode.
def attention_maps(model, ids):
    model.eval()
    maps = []
    with torch.no_grad():
        x = model.embed(ids)
        for block in model.blocks:
            a = block.attention
            maps.append(self_attend(*a.qkv(block.norm1(x)), a.mask, a.scale)[1])
            x = block(x)
    model.train()
    return maps
# @end


# @build 08.02 looks
# Where each head of each block looks, from attention_maps of a batch of
# windows, averaged over the windows and over the positions i from skip
# on: how far back its weights reach (the sum over j of w_ij (i - j)), its
# weight on its own position (j = i), and on the one just before it (j =
# i - 1). A list for each block of (back, own, before), one for each head.
def looks(maps, skip=0):
    out = []
    for w in maps:
        T = w.shape[-1]
        i = torch.arange(T, device=w.device)
        back = (w * (i[:, None] - i[None, :]).clamp(min=0)).sum(-1)[..., skip:]
        own = w.diagonal(dim1=-2, dim2=-1)[..., skip:]
        before = w.diagonal(offset=-1, dim1=-2, dim2=-1)[..., max(skip - 1, 0):]
        out.append([(back[:, h].mean().item(), own[:, h].mean().item(), before[:, h].mean().item())
                    for h in range(w.shape[1])])
    return out
# @end


# @build 08.04 held_bits
# The bits per character of model on a fixed batch of windows x and the
# characters after them, y, in eval mode (no dropout) and without a graph;
# the model is put back in training mode.
def held_bits(model, x, y):
    model.eval()
    with torch.no_grad():
        got = bits(model(x), y).item()
    model.train()
    return got
# @end
