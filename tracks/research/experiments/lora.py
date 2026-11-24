"""LoRA: training under one percent of the weights (Hu et al. 2021), on 12.01's task.

Fine-tuning GPT-2 small changes all 124 million of its weights, and
AdamW keeps two more numbers for each. Hu et al. freeze them all and
train, beside the query and value layers of every block, a change of low
rank, B A.

1. The count: what LoRA trains at each rank, against the paper's formula
   2 x (layers adapted) x d_model x r, beside the body's weights.
2. Exact: adapted and not yet trained, the model gives GPT-2's own
   scores (B starts at 0); trained a few steps, each B A merged into its
   weight gives the same scores as the adapter, up to rounding.
3. Time and memory on this CPU: a training step of the whole body
   against LoRA's, on the same batches; and the numbers each keeps to
   train (a gradient and AdamW's two averages for each trained weight).
4. The paper's claim, LoRA about as good as fine-tuning everything with
   a small fraction of the weights: GPT-2's body with a new head on
   Banking77, frozen (the head alone), LoRA at ranks 1, 4 and 8, and every
   weight trained, the same steps, batches and seeds. That takes most of
   an hour, so the default run reads the run recorded in
   experiments/recorded/lora/ and prints its table; train=True makes the
   runs (NOTES.md has the recorded command).

    python3 -m experiments.lora

Needs GPT-2's files and Banking77: python3 -m data.fetch gpt2 banking77.
"""

import copy
import json
import os

import numpy as np
import torch
import torch.nn.functional as F

import lab
from data import banking77
from data import fetch, shakespeare, tinystories                                   # @from 12.04
from experiments.tuning import accuracy, fit, pad, vectors
from experiments.tuning import moved, text_bits, weights                           # @from 12.04
from models import gpt2 as M
from models.classifier import Classifier
from models.lora import adapt, merge, trained
from tokens import gpt2

CONFIG = dict(ranks=[1, 4, 8], alpha=8, demo_steps=10, timed=5, train=False,
              methods=["head", "lora1", "lora4", "lora8", "full"], seeds=3, steps=600, batch=16, lr=6.25e-5, lora_lr=0.001,
              head_lr=0.003, weight_decay=0.0, warmup=0.06, every=150, valid=1000, standardise_from=1000, questions=0,
              tested=0, recorded="experiments/recorded/lora", device="cpu")
# questions and tested cut the training and the test questions to their first so many (0: all of them), for a quick run
# of train=True.
# @from 12.04
# What else the run measures as it trains (12.04): the bits on the first untuned_tokens tokens of Shakespeare's test
# text at every evaluation; at the end, on the first scored_tokens of it (0: all) and on the first `stories` held-out
# TinyStories.
CONFIG.update(untuned_tokens=2048, stories=50, scored_tokens=0)
# @end


def method_settings(cfg, method):
    """fit's settings for one method: LoRA's A and B at lora_lr, every weight at lr, the head at head_lr."""
    return lab.Config({**cfg, "lr": cfg.lora_lr if method.startswith("lora") else cfg.lr,
                       "warmup": int(cfg.warmup * cfg.steps)})


def build(method, dev, center, alpha):
    """GPT-2 small with a new head, standardised as 12.01's, made ready to train as method says."""
    model = Classifier(M.load(dev), len(banking77.classes())).to(dev)
    model.center.copy_(center[0])
    model.spread.copy_(center[1])
    if method == "head":
        for p in model.body.parameters():
            p.requires_grad_(False)
    elif method.startswith("lora"):
        adapt(model.body, int(method[4:]), alpha)
    return model


def table(rows):
    """The comparison, one line a method: trained weights, test accuracy, its Welch's t against full, and the time a
    step took when this run measured it (times are printed, never written to a summary)."""
    full = rows.get("full")
    print(f"   {'':6s} {'trained':>12s} {'of all':>9s}   {'test accuracy':48s} {'t':>6s}")
    for method, r in rows.items():
        t = f"{lab.welch_t(r['test'], full['test']):+6.1f}" if full and method != "full" else "      "
        print(f"   {method:6s} {r['trained']:>12,d} {100 * r['trained'] / r['total']:8.3f}%   "
              f"{lab.spread(r['test'], 4):48s} {t}" + (f"   {r['ms']:4.0f} ms a step" if "ms" in r else ""))


def recorded(path):
    """The recorded run's summaries, by method: what table() prints."""
    rows = {}
    for method in sorted(os.listdir(path)):
        d = os.path.join(path, method)
        if not os.path.isdir(d) or method == "demo":                 # part 2's run, not a method
            continue
        s = []
        for seed in sorted(n for n in os.listdir(d) if n.startswith("seed")):
            with open(os.path.join(d, seed, "summary.json")) as f:
                s.append(json.load(f))
        rows[method] = {"trained": s[0]["trained"], "total": s[0]["total"], "test": [x["test_accuracy"] for x in s]}
    order = ["head", "lora1", "lora2", "lora4", "lora8", "lora16", "full"]
    return {m: rows[m] for m in sorted(rows, key=lambda m: order.index(m) if m in order else len(order))}


def main():
    cfg = lab.config(CONFIG)
    dev = lab.device(torch, cfg.device)
    start = lab.clock(torch, dev)
    tok = gpt2.load()
    texts, labels = banking77.split("train")
    if cfg.questions:
        texts, labels = texts[:cfg.questions], labels[:cfg.questions]
    seqs = [tok.encode(t) + [gpt2.END] for t in texts]
    classes = len(banking77.classes())

    body = M.load(dev)
    total = sum(p.numel() for p in body.parameters())
    layers, width = len(body.blocks), body.tokens.weight.shape[1]
    print(f"1. GPT-2 small: {total:,} weights. LoRA on W_q and W_v (query, value) of its {layers} blocks, alpha "
          f"{cfg.alpha}:")
    print(f"   {'rank':>4s} {'A and B':>10s} {'2 x 24 x 768 x r':>17s} {'of the body':>12s}   with the head's "
          f"{width * classes + classes:,}")
    for r in cfg.ranks:
        n = trained(adapt(copy.deepcopy(body), r, cfg.alpha))
        print(f"   {r:4d} {n:10,d} {2 * 2 * layers * width * r:17,d} {100 * n / total:11.3f}%   "
              f"{100 * (n + width * classes + classes) / total:.3f}%")

    rng = np.random.default_rng(0)
    ids, lengths = pad([seqs[i] for i in rng.choice(len(seqs), 8, replace=False)], gpt2.END, dev)
    adapted = adapt(copy.deepcopy(body), max(cfg.ranks), cfg.alpha)
    with torch.no_grad():
        before = (adapted(ids) - body(ids)).abs().max().item()
    some = rng.choice(len(seqs), cfg.standardise_from, replace=False)
    center = vectors(Classifier(body, classes), [seqs[i] for i in some], gpt2.END, dev)
    center = (center.mean(0), center.std(0))
    torch.manual_seed(0)
    model = build(f"lora{max(cfg.ranks)}", dev, center, cfg.alpha)
    run = lab.Run(cfg, 0, label="demo")
    fit(model, lab.Config({**method_settings(cfg, "lora"), "steps": cfg.demo_steps, "every": 1, "warmup": 0}), run, dev,
        seqs, labels, gpt2.END)
    model.eval()
    with torch.no_grad():
        scores, logits = model(ids, lengths), model.body(ids)
        merge(model.body)
        merged = (model(ids, lengths) - scores).abs().max().item(), (model.body(ids) - logits).abs().max().item()
    losses = [r["loss"] for r in run.rows]
    run.finish(start_difference=before, merged_scores_difference=merged[0], merged_logits_difference=merged[1])
    print(f"\n2. Adapted at rank {max(cfg.ranks)}, not yet trained: the largest difference from GPT-2's own scores, on 8 "
          f"questions, {before:.3g}.\n   Trained {cfg.demo_steps} steps with a new head (the loss {losses[0]:.2f} to "
          f"{losses[-1]:.2f}), then merged:\n   the largest difference from the adapter's class scores {merged[0]:.3g}, "
          f"from its scores for the next token {merged[1]:.3g}.")

    print(f"\n3. A training step on this CPU ({cfg.timed} steps of {cfg.batch} questions each, the same for both, after one "
          f"not timed):")
    for method in ("full", f"lora{max(cfg.ranks)}"):
        torch.manual_seed(0)
        model = build(method, dev, center, cfg.alpha)
        params = [p for p in model.parameters() if p.requires_grad]
        opt = torch.optim.AdamW(params, lr=1e-5)
        order = np.random.default_rng(1).choice(len(seqs), (cfg.timed + 1, cfg.batch))
        for i, at in enumerate(order):
            if i == 1:
                tick = lab.clock(torch, dev)
            loss = F.cross_entropy(model(*pad([seqs[j] for j in at], gpt2.END, dev)), torch.from_numpy(labels[at]).to(dev))
            opt.zero_grad()
            loss.backward()
            opt.step()
        ms = 1000 * (lab.clock(torch, dev) - tick) / cfg.timed
        kept = sum(p.numel() for p in params)
        weights_mb = 4 * sum(p.numel() for p in model.parameters()) / 1e6
        print(f"   {method:6s} {ms:6.0f} ms a step; trains {kept:,} weights: their gradients and AdamW's two averages "
              f"are {12 * kept / 1e6:,.1f} MB\n          beside the {weights_mb:,.0f} MB of the weights themselves")

    print(f"\n4. Banking77, GPT-2's body with a new head: the head alone (frozen body), LoRA, and every weight trained;"
          f"\n   test accuracy over seeds and Welch's t against every weight trained (with train=True, the time a step "
          f"took too).")
    if not cfg.train:
        if not os.path.isdir(cfg.recorded):
            print(f"   No recorded run in {cfg.recorded}: train=True makes the runs.")
        else:
            with open(os.path.join(cfg.recorded, "full", "seed0", "config.json")) as f:
                c = json.load(f)
            print(f"   The run recorded in {cfg.recorded}: {c['steps']} steps of {c['batch']} questions, AdamW (every "
                  f"weight {c['lr']}, LoRA {c['lora_lr']},\n   the head {c['head_lr']}), alpha {c['alpha']}, {c['seeds']} "
                  f"seeds:\n")
            table(recorded(cfg.recorded))
    else:
        valid_texts, valid_labels = banking77.split("valid")
        valid = [tok.encode(t) + [gpt2.END] for t in valid_texts[:cfg.valid]]
        valid_labels = valid_labels[:cfg.valid]
        test_texts, test_labels = banking77.split("test")
        if cfg.tested:
            keep = np.linspace(0, len(test_texts) - 1, cfg.tested).astype(int)
            test_texts, test_labels = [test_texts[i] for i in keep], test_labels[keep]
        test = [tok.encode(t) + [gpt2.END] for t in test_texts]
        # @from 12.04
        text = shakespeare.load()
        untuned = torch.tensor(tok.encode(text[int(0.95 * len(text)):]), device=dev)
        scored = untuned[:cfg.scored_tokens] if cfg.scored_tokens else untuned
        stories = None if fetch.missing("tinystories") else torch.tensor(
            tok.encode("\n\n".join(tinystories.stories("valid")[:cfg.stories])), device=dev)
        # @end
        rows, inputs = {}, None
        for method in cfg.methods:
            got, ms = [], []
            for seed in range(cfg.seeds):
                run = lab.Run(lab.Config({**cfg, "method": method}), seed, label=method)
                torch.manual_seed(seed)
                model = build(method, dev, center, cfg.alpha)
                # @from 12.04
                begun = {n: w.detach().clone() for n, w in weights(model.body).items()}
                # @end

                measuring = [0.0]

                def measure(model):
                    tick = lab.clock(torch, dev)
                    row = {"valid": accuracy(model, valid, valid_labels, gpt2.END, dev)}
                    # @from 12.04
                    row["untuned_bits"] = text_bits(model.body, untuned[:cfg.untuned_tokens], tok.table)
                    row["moved"] = moved(model.body, begun)
                    # @end
                    measuring[0] += lab.clock(torch, dev) - tick
                    return row

                if method == "head" and inputs is None:
                    inputs = vectors(model, seqs, gpt2.END, dev)          # the frozen body read once, for every seed
                tick = lab.clock(torch, dev)
                if method == "head":
                    fit(model, method_settings(cfg, method), run, dev, inputs, labels, measure=measure)
                else:
                    fit(model, method_settings(cfg, method), run, dev, seqs, labels, gpt2.END, measure)
                spent = lab.clock(torch, dev) - tick - measuring[0]
                result = dict(test_accuracy=accuracy(model, test, test_labels, gpt2.END, dev), trained=trained(model),
                              total=sum(p.numel() for p in model.parameters()))
                # @from 12.04
                result.update(shakespeare_bits=text_bits(model.body, scored, tok.table), moved=moved(model.body, begun))
                if stories is not None:
                    result["stories_bits"] = text_bits(model.body, stories, tok.table)
                # @end
                run.finish(**result)
                got.append(result["test_accuracy"])
                ms.append(1000 * spent / cfg.steps)
                print(f"   {method} seed {seed}: test accuracy {got[-1]:.4f}; {spent:.0f} s of training, {ms[-1]:.0f} ms a "
                      f"step; {measuring[0]:.0f} s of measuring", flush=True)
            rows[method] = {"trained": result["trained"], "total": result["total"], "test": got, "ms": lab.mean(ms)}
        print()
        table(rows)
    print(f"\n{lab.clock(torch, dev) - start:.0f} s of loading, training and scoring on {dev.type}")


if __name__ == "__main__":
    main()
