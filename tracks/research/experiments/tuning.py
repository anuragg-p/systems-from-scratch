"""Fine-tuning a pretrained GPT: the loop and the measures module 12 shares.

08's language.train reads windows of one long text. A labelled set is
many short texts instead, each with its label (12.01) or its answer
(12.03), of different lengths: a batch is a few of them padded to the
longest (pad), and the loss is on what each text is for: its label, or
its answer's tokens. What is trained is whatever needs a gradient, so
the same loop trains a whole model, a new head alone, or LoRA's A and B
(12.02): AdamW over the parameters with requires_grad, a new head at a
rate of its own, the rate warmed up then along half a cosine (03.05).
"""

import numpy as np
import torch
import torch.nn.functional as F

import lab
from data import batches
from experiments.sequences import per_character, window_bits                    # @from 12.04


# @build 12.01 pad
# rows (lists of token ids, of different lengths) as one (len(rows), T)
# tensor on dev, T the longest, each row followed by `fill` up to T; and
# their lengths, a tensor of len(rows).
def pad(rows, fill, dev):
    T = max(len(r) for r in rows)
    ids = torch.tensor([list(r) + [fill] * (T - len(r)) for r in rows], device=dev)
    return ids, torch.tensor([len(r) for r in rows], device=dev)
# @end


# @build 12.01 vectors
# model.features (the body's vector at each text's last token) for every
# text of seqs, in eval mode, without a graph, `batch` texts at a time in
# order of length (so a batch pads little): a (len(seqs), width) tensor in
# the order of seqs. Then back in training mode.
def vectors(model, seqs, fill, dev, batch=100):
    model.eval()
    order = np.argsort([len(s) for s in seqs], kind="stable")
    out = [None] * len(seqs)
    with torch.no_grad():
        for i in range(0, len(seqs), batch):
            at = order[i:i + batch]
            for j, v in zip(at, model.features(*pad([seqs[j] for j in at], fill, dev))):
                out[j] = v
    model.train()
    return torch.stack(out)
# @end


# @build 12.01 accuracy
# The share of texts whose highest score is their label (labels, a numpy
# array): inputs are the texts (lists of token ids), scored by
# model(ids, lengths) as vectors() reads them, or the body's vectors
# already read (a tensor), scored by model.scores. In eval mode, without
# a graph; then back in training mode.
def accuracy(model, inputs, labels, fill, dev, batch=100):
    model.eval()
    with torch.no_grad():
        if torch.is_tensor(inputs):
            guess = model.scores(inputs).argmax(-1).cpu().numpy()
        else:
            order = np.argsort([len(s) for s in inputs], kind="stable")
            guess = np.zeros(len(inputs), dtype=np.int64)
            for i in range(0, len(inputs), batch):
                at = order[i:i + batch]
                guess[at] = model(*pad([inputs[j] for j in at], fill, dev)).argmax(-1).cpu().numpy()
    model.train()
    return float((guess == labels).mean())
# @end


# @build 12.01 fit
# Train model (a Classifier) for cfg.steps steps on inputs and labels (a
# numpy array). inputs are the texts (lists of token ids), each batch
# padded with fill and scored by model(ids, lengths); or the body's vectors
# already read once (a tensor: a frozen body need not run again), scored by
# model.scores. Each step cfg.batch of them, in an order drawn from run.rng
# anew for every pass (03.01's batches; a pass's last, smaller batch is
# skipped); the loss is F.cross_entropy for their labels. AdamW, weight
# decay cfg.weight_decay, over every parameter that needs a gradient: the
# head's (model.head) at cfg.head_lr, the others at cfg.lr; the rate
# warmed up over the first cfg.warmup steps, then half a cosine to 0
# (03.05's warmup_cosine). Every cfg.every steps and at the last, a row of
# the run's log: the step, the batch's loss, and what measure(model), when
# given, returns (a dict). Returns the model.
def fit(model, cfg, run, dev, inputs, labels, fill=None, measure=None):
    head = [p for p in model.head.parameters() if p.requires_grad]
    body = [p for n, p in model.named_parameters() if p.requires_grad and not n.startswith("head.")]
    groups = [{"params": body, "lr": cfg.lr}] if body else []
    opt = torch.optim.AdamW(groups + [{"params": head, "lr": cfg.head_lr}], weight_decay=cfg.weight_decay)
    scheduler = torch.optim.lr_scheduler.LambdaLR(opt, lab.warmup_cosine(cfg.warmup, cfg.steps))
    model.train()
    step, order = 0, iter(())
    while step < cfg.steps:
        at = next(order, None)
        if at is None or len(at) < min(cfg.batch, len(labels)):
            order = batches(len(labels), cfg.batch, run.rng)
            continue
        if torch.is_tensor(inputs):
            scores = model.scores(inputs[torch.from_numpy(at).to(inputs.device)])
        else:
            scores = model(*pad([inputs[j] for j in at], fill, dev))
        loss = F.cross_entropy(scores, torch.from_numpy(labels[at]).to(dev))
        opt.zero_grad()
        loss.backward()
        opt.step()
        scheduler.step()
        if step % cfg.every == 0 or step == cfg.steps - 1:
            run.log(step=step, loss=loss.item(), **(measure(model) if measure else {}))
        step += 1
    return model
# @end


# @build 12.03 answer_loss
# A GPT's loss on the answers alone. ids (batch, T) is each example's
# prompt and reply (12.03's chat and reply, as tokens), then padding;
# starts says where each reply begins, lengths where each example ends.
# The model scores the next token at every position, as in training on
# text; only the positions whose next token is part of the reply count
# (from starts - 1 to lengths - 2): the mean of -ln p of those tokens.
def answer_loss(model, ids, starts, lengths):
    scores = model(ids[:, :-1])
    at = torch.arange(ids.shape[1] - 1, device=ids.device)
    keep = (at[None, :] >= starts[:, None] - 1) & (at[None, :] < lengths[:, None] - 1)
    return F.cross_entropy(scores[keep], ids[:, 1:][keep])
# @end


# @build 12.03 tune
# Train a GPT (model) on examples, a list of (prompt, reply), each a list
# of token ids, for cfg.steps steps: each step cfg.batch examples in an
# order drawn from run.rng anew for every pass, joined and padded with
# fill, the loss answer_loss. AdamW over every parameter that needs a
# gradient at cfg.lr, weight decay cfg.weight_decay, warmed up over
# cfg.warmup steps then half a cosine. Every cfg.every steps and at the
# last, a row of the run's log, with what measure(model) returns. Returns
# the model.
def tune(model, cfg, run, dev, examples, fill, measure=None):
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=cfg.lr,
                            weight_decay=cfg.weight_decay)
    scheduler = torch.optim.lr_scheduler.LambdaLR(opt, lab.warmup_cosine(cfg.warmup, cfg.steps))
    model.train()
    step, order = 0, iter(())
    while step < cfg.steps:
        at = next(order, None)
        if at is None or len(at) < cfg.batch:
            order = batches(len(examples), cfg.batch, run.rng)
            continue
        ids, lengths = pad([examples[j][0] + examples[j][1] for j in at], fill, dev)
        starts = torch.tensor([len(examples[j][0]) for j in at], device=dev)
        loss = answer_loss(model, ids, starts, lengths)
        opt.zero_grad()
        loss.backward()
        opt.step()
        scheduler.step()
        if step % cfg.every == 0 or step == cfg.steps - 1:
            run.log(step=step, loss=loss.item(), **(measure(model) if measure else {}))
        step += 1
    return model
# @end


# @build 12.03 answers
# A GPT's greedy answers: after each prompt (a list of token ids), the
# token of highest score again and again, at most n, until the row holds
# stop (the end marker's tokens) or n is reached. Prompts of the same
# length go together (the model has no mask for padding, so a batch must
# not need any); each group stops once all its rows hold stop. In eval
# mode, without a graph; the token lists, in the prompts' order.
def answers(model, prompts, n, stop, dev):
    model.eval()
    out = [None] * len(prompts)
    groups = {}
    for i, p in enumerate(prompts):
        groups.setdefault(len(p), []).append(i)
    with torch.no_grad():
        for rows in groups.values():
            ids = torch.tensor([prompts[i] for i in rows], device=dev)
            drawn = ids[:, :0]
            while drawn.shape[1] < n and not all(holds(row, stop) for row in drawn.tolist()):
                more = model(torch.cat([ids, drawn], 1)[:, -model.context:])[:, -1].argmax(-1, keepdim=True)
                drawn = torch.cat([drawn, more], 1)
            for i, row in zip(rows, drawn.tolist()):
                out[i] = row
    model.train()
    return out
# @end


def holds(row, part):
    """Does the list row hold the list part, in a run?"""
    return any(row[i:i + len(part)] == part for i in range(len(row) - len(part) + 1))


# @build 12.04 text_bits
# What a GPT (body) now makes of a text it was not tuned on: its bits per
# character on ids (that text's GPT-2 tokens, a 1-d tensor), each token
# read with `warm` or more before it in windows of the body's context
# (09.03's window_bits), made bits per character with table (09.01's
# per_character). In eval mode; then back in training mode.
def text_bits(body, ids, table, warm=64):
    body.eval()
    got = per_character(window_bits(body, ids, body.context - warm + 1, warm, batch=4), ids.tolist(), table, warm)
    body.train()
    return got
# @end


# @build 12.04 weights
# The weights a GPT (body) computes with, under GPT's own names, whether
# or not LoRA adapted it: its state_dict, but each LoRA layer (a layer
# with 12.02's delta()) as the one weight it amounts to, W + (alpha / r)
# B A, and its bias. Without a graph.
def weights(body):
    out = {name.replace(".linear.", "."): t for name, t in body.state_dict().items() if not name.endswith((".A", ".B"))}
    with torch.no_grad():
        for name, layer in body.named_modules():
            if hasattr(layer, "delta"):
                out[name + ".weight"] = layer.linear.weight + layer.delta()
    return out
# @end


# @build 12.04 moved
# How far tuning moved a GPT's weights from where they started (start:
# weights() before tuning, copied): the length of the change of all of
# them laid end to end, over the length of the starting weights.
def moved(body, start):
    now = weights(body)
    change = sum(float(((now[n] - w) ** 2).sum()) for n, w in start.items())
    return (change / sum(float((w ** 2).sum()) for w in start.values())) ** 0.5
# @end
