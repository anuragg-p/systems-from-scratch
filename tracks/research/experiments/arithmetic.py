"""Training a model on a table of equations, and reading its log: the loop module 14 shares.

    log_steps(steps, per_decade)        the steps at which a run is measured, evenly spaced in the logarithm
    score(model, rows)                  accuracy and loss of the guess at c, on rows of equations
    train(model, cfg, run, dev, train_rows, val_rows)
                                        the paper's training: AdamW, warmup, batches of 512, measured at log_steps
    weight_norm(model)                  the size of all the weights together                            # @from 14.03
    first_step(rows, key, level)        when a curve of the log first reached a level                   # @from 14.03
    milestones(rows, p)                 what 14.03 measures in a run's log                              # @from 14.03
    scaled_start(model, factor)         the model's start made factor times larger                      # @from 14.04
    read_seeds(folder)                  every seed's config and log of one setting, read back           # @from 14.04
    read_runs(directory)                the same for every setting a script ran, by its label           # @from 14.04
    median_steps(steps, budget)         the median of steps some of which never came                    # @from 14.04

The model reads a o b = (four tokens of data/modular.py's five) and is
scored on its guess at c, at the last of them: models/gpt.py's GPT, or any
model that takes (batch, 4) token numbers and gives (batch, 4, vocab)
scores.
"""

import json                                                                    # @from 14.04
import math
import os                                                                      # @from 14.04

import torch
import torch.nn.functional as F

import data
import lab


# @build 14.02 log_steps
# The steps at which a run is measured, spaced evenly in the logarithm as
# the paper's figure's axis is: 0 (before any update), per_decade steps in
# every factor of ten, 10^(k / per_decade) rounded down (without repeats,
# so the first few are 1, 2, 3, ...), and the last step. A sorted list.
def log_steps(steps, per_decade):
    at = {0, steps}
    k = 0
    while 10 ** (k / per_decade) < steps:
        at.add(int(10 ** (k / per_decade)))
        k += 1
    return sorted(at)
# @end


# @build 14.02 score
# How model does on rows of equations (an int64 tensor (n, 5) on its
# device): it reads the first four tokens, a op b =, and its scores at the
# last of them are its guess at c. Returns the fraction it gets right (its
# highest score is c's) and its loss there, F.cross_entropy, in nats. In
# eval mode, without a graph; the model is put back in training mode.
def score(model, rows):
    model.eval()
    with torch.no_grad():
        scores = model(rows[:, :4])[:, -1]
        right = (scores.argmax(-1) == rows[:, 4]).float().mean().item()
        loss = F.cross_entropy(scores, rows[:, 4]).item()
    model.train()
    return right, loss
# @end


# @build 14.03 weight_norm
# The size of all of model's weights together: the square root of the sum
# of the squares of every number in every parameter. Weight decay pulls it
# down a little at every step; fitting the training set can push it up.
def weight_norm(model):
    return math.sqrt(sum((p.detach() ** 2).sum().item() for p in model.parameters()))
# @end


# @build 14.02 train
# Train model, one seed, for cfg.steps updates on the training rows (an
# int64 tensor on the device dev): batches of cfg.batch rows, or half the
# training set when that is smaller, in a new random order every pass
# (03.01's data.batches, from run.rng); the loss is the cross-entropy of
# the guess at c only (the paper: "calculated loss and accuracy only on the
# answer part of the equation"). AdamW (03.04) at cfg.lr with cfg.betas and
# cfg.weight_decay on every weight, the rate rising over the first
# cfg.warmup updates and then constant (03.05's warmup_cosine with its
# floor at 1: no decay). At each of log_steps, accuracy and loss on the
# whole training set and the whole validation set go to the run's log.
# @from 14.04
# With stop (14.04), the run ends at the first measured step at which
# validation accuracy is 99% or more.
def train(model, cfg, run, dev, train_rows, val_rows, stop=False):
# @else
# def train(model, cfg, run, dev, train_rows, val_rows):
# @end
    opt = torch.optim.AdamW(model.parameters(), lr=cfg.lr, betas=tuple(cfg.betas), weight_decay=cfg.weight_decay)
    scheduler = torch.optim.lr_scheduler.LambdaLR(opt, lab.warmup_cosine(cfg.warmup, cfg.steps, floor=1.0))
    size = min(cfg.batch, math.ceil(len(train_rows) / 2))
    at = set(log_steps(cfg.steps, cfg.per_decade))

    def measure(step):
        (train_acc, train_loss), (val_acc, val_loss) = score(model, train_rows), score(model, val_rows)
        # @from 14.03
        run.log(step=step, train_acc=train_acc, val_acc=val_acc, train_loss=train_loss, val_loss=val_loss,
                norm=weight_norm(model))
        # @else
        # run.log(step=step, train_acc=train_acc, val_acc=val_acc, train_loss=train_loss, val_loss=val_loss)
        # @end
        return val_acc                                                         # @from 14.04

    measure(0)
    step = 0
    while step < cfg.steps:
        for idx in data.batches(len(train_rows), size, run.rng):
            rows = train_rows[torch.from_numpy(idx).to(dev)]
            loss = F.cross_entropy(model(rows[:, :4])[:, -1], rows[:, 4])
            opt.zero_grad()
            loss.backward()
            opt.step()
            scheduler.step()
            step += 1
            # @from 14.04
            if step in at and measure(step) >= 0.99 and stop:
                return model
            # @else
            # if step in at:
            #     measure(step)
            # @end
            if step == cfg.steps:
                break
    return model
# @end


# @build 14.03 first_step
# The first measured step of a run's log (rows, in order of step) at which
# rows[key] is level or more: when training accuracy, or validation
# accuracy, first reached 99%. None if it never did.
def first_step(rows, key, level):
    return next((r["step"] for r in rows if r[key] >= level), None)
# @end


# @build 14.03 milestones
# What 14.03 measures in a run's log: the first step at which training
# accuracy and validation accuracy each reached 99%, and how many times
# later the second came (None where a run never got there); validation
# accuracy at the first of them; the highest validation loss, where it was,
# and how many times the loss of a guess (ln p) it is; the weights' norm at
# the start, at its highest (and where), when validation accuracy reached
# 99%, and at the end; and the best validation accuracy of the run.
def milestones(rows, p):
    train99, val99 = first_step(rows, "train_acc", 0.99), first_step(rows, "val_acc", 0.99)
    at = {r["step"]: r for r in rows}
    peak = max(rows, key=lambda r: r["val_loss"])
    top = max(rows, key=lambda r: r["norm"])
    return dict(train99=train99, val99=val99, ratio=val99 / train99 if train99 and val99 else None,
                val_acc_at_train99=at[train99]["val_acc"] if train99 is not None else None,
                peak_val_loss=peak["val_loss"], peak_step=peak["step"], peak_over_chance=peak["val_loss"] / math.log(p),
                norm_start=rows[0]["norm"], norm_max=top["norm"], norm_max_step=top["step"],
                norm_at_val99=at[val99]["norm"] if val99 is not None else None, norm_end=rows[-1]["norm"],
                best_val_acc=max(r["val_acc"] for r in rows))
# @end


# @build 14.04 scaled_start
# model's start made factor times larger: every weight but the layer
# norms' multiplied by factor (the biases start at 0 and stay so). GPT
# starts as GPT-2 does, every weight drawn with sd 0.02; the paper's code
# keeps PyTorch's own start, whose embedding has sd 1. factor 1 changes
# nothing. Returns the model.
def scaled_start(model, factor):
    with torch.no_grad():
        for name, p in model.named_parameters():
            if "norm" not in name:
                p.mul_(factor)
    return model
# @end


# @build 14.04 read_seeds
# The runs of one setting, read back from its folder (folder/seed<k>/, as
# lab.Run lays them out): a list, in seed order, of (config, rows), the
# settings from config.json and the rows of log.jsonl.
def read_seeds(folder):
    out = []
    for seed in sorted(int(s[4:]) for s in os.listdir(folder) if s.startswith("seed")):
        with open(os.path.join(folder, f"seed{seed}", "config.json")) as f:
            out.append((json.load(f), lab.read_log(os.path.join(folder, f"seed{seed}"))))
    return out
# @end


# @build 14.04 read_runs
# Every setting a script ran with a label (directory/<label>/seed<k>/): a
# dict from each label to read_seeds of its folder.
def read_runs(directory):
    return {label: read_seeds(os.path.join(directory, label)) for label in sorted(os.listdir(directory))
            if os.path.isdir(os.path.join(directory, label))}
# @end


# @build 14.04 median_steps
# The median of a list of steps at which something happened, where None
# says it never did within budget steps (so it counts as later than any
# step). Returns (median, more): more is True when the median is one of the
# runs that never got there, and the median is then only "more than
# budget". With an even count, the later of the two middle ones.
def median_steps(steps, budget):
    order = sorted(steps, key=lambda s: math.inf if s is None else s)
    middle = order[len(order) // 2]
    return (budget, True) if middle is None else (middle, False)
# @end
