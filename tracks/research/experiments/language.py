"""Training a model of the next character on windows of the text: the loop module 08 shares.

07's scripts each trained their own way (positions, streams, tasks). From
08.01 on every model reads a window of `context` characters and scores
the next character at every position of it at once, so they share one
loop: a batch is cfg.batch windows from random places of the training
text (07.03's windows), the loss is the mean of their bits per character
(07.02's bits), and the optimiser is AdamW (03.04) with a warmup and a
cosine decay (03.05), the gradient clipped to cfg.clip (07.03).
"""

import json                                                           # @from 08.04

import torch
import torch.nn.functional as F                                       # @from 08.05

import lab
from experiments.sequences import bits, windows
from experiments.sequences import window_bits                         # @from 10.01
from lab import safetensors                                           # @from 08.04
from models.gpt import self_attend                                    # @from 08.02
from models.gpt import GPT                                            # @from 08.04


# @build 08.01 train
# Train model, one seed, for cfg.steps steps, on ids (the training text, a
# 1-d tensor on the device dev): each step cfg.batch windows of
# cfg.context characters, starting at places drawn from run.rng, and the
# character after every position of each as its target. AdamW at cfg.lr,
# its weight decay cfg.weight_decay on the weight matrices and embeddings
# only (not on biases or layer norms, as nanoGPT does), the rate rising over
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


# @build 08.04 save
# A GPT's checkpoint, in the safetensors format (02.05's lab/safetensors.py):
# every weight of its state_dict as a numpy array of float32, and in the
# metadata the settings that build it again (config, a dict of GPT's
# arguments) and anything else worth keeping with it (notes), each as JSON.
def save(model, config, path, **notes):
    tensors = {name: t.detach().float().cpu().numpy() for name, t in model.state_dict().items()}
    metadata = {"config": json.dumps(config, sort_keys=True), **{k: json.dumps(v) for k, v in notes.items()}}
    safetensors.save_file(tensors, path, metadata)
# @end


# @build 08.04 load
# The GPT a checkpoint written by save holds, on the device dev, in eval
# mode, and the metadata's notes (a dict, the config among them).
def load(path, dev):
    header, _ = safetensors.read_header(path)
    notes = {k: json.loads(v) for k, v in header.get("__metadata__", {}).items()}
    model = GPT(**notes["config"])
    model.load_state_dict({name: torch.from_numpy(a) for name, a in safetensors.load_file(path).items()})
    return model.to(dev).eval(), notes
# @end


# @build 08.05 top_k
# scores (..., V) with every score below the k-th highest set to -inf, so
# that the softmax gives only the k highest a chance (more than k when
# several tie with the k-th), in the same proportions as before.
def top_k(scores, k):
    kth = scores.topk(k, dim=-1).values[..., -1:]
    return scores.masked_fill(scores < kth, float("-inf"))
# @end


# @build 08.05 top_p
# Holtzman et al.'s nucleus: of the symbols in order of their chances
# (the softmax of scores, (..., V)), the fewest whose chances add up to p
# or more keep their scores, every other one gets -inf. A symbol is kept
# when the chances of those before it add up to less than p, so the first
# is always kept. (Equal chances stay in the order of their symbols:
# stable=True.)
def top_p(scores, p):
    chances, order = F.softmax(scores, dim=-1).sort(dim=-1, descending=True, stable=True)
    out = (chances.cumsum(-1) - chances) >= p
    return scores.masked_fill(out.scatter(-1, order, out), float("-inf"))
# @end


# @build 08.05 generate
# n symbols after each row of prompts, (batch, P), from model (a GPT): at
# every step the scores at the last position of the window (its last
# model.context symbols), divided by temperature, then cut to top_k and
# top_p when k and p are given, and one symbol drawn from their softmax
# with generator (a seeded torch.Generator, on the CPU); temperature 0 is
# greedy, the highest score every time. Returns the symbols drawn, (batch,
# n). In eval mode, without a graph.
def generate(model, prompts, n, generator, temperature=1.0, k=None, p=None):
    model.eval()
    ids = prompts
    with torch.no_grad():
        for _ in range(n):
            scores = model(ids[:, -model.context:])[:, -1].float()
            if temperature == 0:
                chosen = scores.argmax(-1, keepdim=True)
            else:
                scores = scores / temperature
                if k:
                    scores = top_k(scores, k)
                if p is not None:
                    scores = top_p(scores, p)
                chosen = torch.multinomial(F.softmax(scores, dim=-1).cpu(), 1, generator=generator).to(ids.device)
            ids = torch.cat([ids, chosen], dim=1)
    return ids[:, prompts.shape[1]:]
# @end


# @build 09.03 loops
# Holtzman et al.'s repetition, 08.05's measure, here for any symbols
# (09.03's word pieces, 09.04's): True when ids (a list) end with a
# phrase of 2 or more symbols repeated at least 3 times in a row.
def loops(ids):
    return any(ids[-L:] == ids[-2 * L:-L] == ids[-3 * L:-2 * L] for L in range(2, len(ids) // 3 + 1))
# @end


# @build 10.01 compare
# GPTs that differ in one piece, trained and scored alike: for each of
# cfg.seeds seeds, each of `variants` (a dict, name -> GPT's arguments
# beyond `common`) built from that seed, trained by train on the training
# text ids for cfg.steps steps (with held, its held-out windows logged),
# its training timed with lab.clock, and scored on test by window_bits,
# each character with cfg.context // 4 or more before it. The variants
# take turns seed by seed, so a change in the machine's load falls on all
# of them alike, and each first takes one step of AdamW untimed (a
# process's first step is slow, about half a second here, while memory
# and the optimiser are set up; the seed is set again after it). Each
# run's summary.json has its test bits and weights. Returns {name:
# {"bits": [...], "ms": [...] (a step), "weights": n, "models": [...]}},
# the lists by seed.
def compare(variants, common, cfg, dev, ids, test, held=None):
    out = {name: {"bits": [], "ms": [], "models": []} for name in variants}
    for changes in variants.values():
        model, x = GPT(**common, **changes).to(dev), ids[:cfg.batch * cfg.context].view(cfg.batch, cfg.context)
        bits(model(x), x).backward()
        torch.optim.AdamW(model.parameters()).step()
    for seed in range(cfg.seeds):
        for name, changes in variants.items():
            run = lab.Run(cfg, seed, label=name)
            torch.manual_seed(seed)
            model = GPT(**common, **changes).to(dev)
            start = lab.clock(torch, dev)
            train(model, cfg, run, dev, ids, held)
            ms = 1000 * (lab.clock(torch, dev) - start) / cfg.steps
            model.eval()
            got = window_bits(model, test, cfg.context - cfg.context // 4 + 1, cfg.context // 4)
            weights = sum(p.numel() for p in model.parameters())
            run.finish(test_bits=got, weights=weights)
            r = out[name]
            r["bits"].append(got)
            r["ms"].append(ms)
            r["models"].append(model)
            r["weights"] = weights
    return out
# @end
