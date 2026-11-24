"""What fine-tuning forgot: measuring before and after.

A fine-tuned GPT-2 is still a model of the next token, and tuning moved
its weights for one task. What did that cost it on text it was not tuned
on? Measured as its bits per character on Tiny Shakespeare's test text
(GPT-2 as published: 1.851, 09.03) and on held-out TinyStories, before
and after, beside how far the weights moved.

1. The classifier of 12.01 and 12.02 (the head alone, LoRA at each rank,
   every weight trained), from the run recorded in
   experiments/recorded/lora/, which measured all this as it trained:
   test accuracy, the bits after, how far the weights moved.
2. Along the way: at each of that run's evaluations, the task's accuracy
   on validation beside the bits on Tiny Shakespeare; and so the bits
   each method had when it first reached the same accuracy.
3. The instruction model of 12.03, here, small: GPT-2 tuned on the
   instruction tasks with LoRA and with every weight trained, the same
   steps and seeds: exact match, the bits before and after, how far the
   weights moved.

    python3 -m experiments.forgetting

Needs GPT-2's files (python3 -m data.fetch gpt2); TinyStories is used
when it is there.
"""

import json
import os

import numpy as np
import torch

import lab
from data import fetch, shakespeare, tinystories
from data import instructions as I
from experiments.tuning import answers, moved, text_bits, tune, weights
from models import gpt2 as M
from models.lora import adapt
from tokens import gpt2

CONFIG = dict(recorded="experiments/recorded/lora", levels=[0.8, 0.85, 0.88], methods=["lora", "full"], rank=8, alpha=8,
              examples=1000, steps=30, batch=8, lr=0.003, full_lr=6.25e-5, weight_decay=0.0, warmup=0.06, every=10 ** 9,
              seeds=2, scored=4, longest=6, untuned_tokens=1024, stories=0, device="cpu")


# @build 12.04 at_accuracy
# From a run's log rows (each with "valid", its accuracy, and
# "untuned_bits"), the bits on the untuned text when the accuracy first
# reached level: read on the straight line between the two evaluations
# either side of it. None when the run never reached it.
def at_accuracy(rows, level):
    for a, b in zip(rows, rows[1:]):
        if a["valid"] < level <= b["valid"]:
            f = (level - a["valid"]) / (b["valid"] - a["valid"])
            return a["untuned_bits"] + f * (b["untuned_bits"] - a["untuned_bits"])
    return rows[0]["untuned_bits"] if rows and rows[0]["valid"] >= level else None
# @end


def read(path):
    """The recorded run: {method: [(summary, log rows) for each seed]}."""
    out = {}
    for method in sorted(os.listdir(path)):
        d = os.path.join(path, method)
        if os.path.isdir(d) and method != "demo":                    # 12.02's part 2, not a method
            out[method] = []
            for seed in sorted(n for n in os.listdir(d) if n.startswith("seed")):
                with open(os.path.join(d, seed, "summary.json")) as f:
                    out[method].append((json.load(f), lab.read_log(os.path.join(d, seed))))
    order = ["head", "lora1", "lora2", "lora4", "lora8", "lora16", "full"]
    return {m: out[m] for m in sorted(out, key=lambda m: order.index(m) if m in order else len(order))}


def main():
    cfg = lab.config(CONFIG)
    dev = lab.device(torch, cfg.device)
    start = lab.clock(torch, dev)
    tok = gpt2.load()
    text = shakespeare.load()
    untuned = torch.tensor(tok.encode(text[int(0.95 * len(text)):]), device=dev)[:cfg.untuned_tokens]
    have_stories = cfg.stories > 0 and not fetch.missing("tinystories")
    if have_stories:
        stories = torch.tensor(tok.encode("\n\n".join(tinystories.stories("valid")[:cfg.stories])), device=dev)

    print(f"1. The classifier on Banking77 (12.02's recorded run, {cfg.recorded}): after tuning, test accuracy; bits per "
          f"character\n   on Tiny Shakespeare's test text and on held-out TinyStories (GPT-2 itself: the head alone's "
          f"numbers);\n   how far the weights moved (the length of the change over the length of the weights).\n")
    if not os.path.isdir(cfg.recorded):
        print(f"   No recorded run in {cfg.recorded}: python3 -m experiments.lora train=True makes it.")
        runs = {}
    else:
        runs = read(cfg.recorded)
        print(f"   {'':6s} {'test accuracy':16s} {'Shakespeare':13s} {'TinyStories':13s} {'moved':10s}")
        for method, seeds in runs.items():
            s = [x for x, _ in seeds]
            print(f"   {method:6s} {lab.mean([x['test_accuracy'] for x in s]):<16.4f} "
                  f"{lab.mean([x['shakespeare_bits'] for x in s]):<13.4f} {lab.mean([x.get('stories_bits', float('nan')) for x in s]):<13.4f} "
                  f"{lab.mean([x['moved'] for x in s]):<10.3g} ({len(s)} seeds)")
        if "full" in runs and "head" in runs:
            for method in [m for m in runs if m.startswith("lora")]:
                a = [x["shakespeare_bits"] for x, _ in runs[method]]
                b = [x["shakespeare_bits"] for x, _ in runs["full"]]
                print(f"   Shakespeare's bits, {method} against full: Welch's t {lab.welch_t(a, b):+.1f}")

        print(f"\n2. Along the way, at each evaluation: accuracy on validation and the bits on the first "
              f"{cfg.untuned_tokens:,} tokens of\n   Shakespeare's test text. The bits when each method first reached an "
              f"accuracy (mean over the seeds that did):\n")
        print(f"   {'':6s} " + " ".join(f"{'at ' + str(level):>14s}" for level in cfg.levels) + "   the last evaluation")
        for method, seeds in runs.items():
            cells = []
            for level in cfg.levels:
                got = [b for b in (at_accuracy(rows, level) for _, rows in seeds) if b is not None]
                cells.append(f"{lab.mean(got):8.4f} ({len(got)}/{len(seeds)})" if got else f"{'never':>14s}")
            last = [rows[-1] for _, rows in seeds]
            print(f"   {method:6s} " + " ".join(f"{c:>14s}" for c in cells) +
                  f"   {lab.mean([r['valid'] for r in last]):.4f}, {lab.mean([r['untuned_bits'] for r in last]):.4f}")

    print(f"\n3. The instruction model (12.03), small: {cfg.steps} steps of {cfg.batch} examples, LoRA at rank {cfg.rank} "
          f"(AdamW {cfg.lr}) and\n   every weight trained (AdamW {cfg.full_lr}), {cfg.seeds} seeds; exact match on "
          f"{cfg.scored} held-out instances of each trained task.")
    rng = np.random.default_rng(1000)
    scored = []
    for task in I.TRAINED:
        ways = I.wordings(task, "train")
        for fields, answer in I.instances(task, "held", cfg.scored, rng):
            scored.append((tok.encode(I.chat(ways[int(rng.integers(0, len(ways)))].format(**fields))), answer))
    stop = tok.encode("\n")                       # the first line is what is scored, as in 12.03

    def exact(model):
        drawn = answers(model, [p for p, _ in scored], cfg.longest, stop, dev)
        return float(np.mean([tok.decode(d).split(I.END)[0].split("\n")[0].strip() == a for d, (_, a) in zip(drawn, scored)]))

    model = M.load(dev)
    before = {"exact": exact(model), "shakespeare": text_bits(model, untuned, tok.table)}
    if have_stories:
        before["stories"] = text_bits(model, stories, tok.table)
    print(f"   GPT-2 before: exact match {before['exact']:.3f}, Shakespeare {before['shakespeare']:.4f}"
          + (f", TinyStories {before['stories']:.4f}" if have_stories else "") + " bits per character")
    results = {}
    for method in cfg.methods:
        results[method] = []
        for seed in range(cfg.seeds):
            run = lab.Run(cfg, seed, label=method)
            examples = []
            for task in I.TRAINED:
                ways = I.wordings(task, "train")
                for fields, answer in I.instances(task, "train", cfg.examples // len(I.TRAINED), run.rng):
                    examples.append((tok.encode(I.chat(ways[int(run.rng.integers(0, len(ways)))].format(**fields))),
                                     tok.encode(I.reply(answer))))
            torch.manual_seed(seed)
            model = M.load(dev)
            begun = {n: w.detach().clone() for n, w in weights(model).items()}
            if method == "lora":
                adapt(model, cfg.rank, cfg.alpha)
            lr = cfg.lr if method == "lora" else cfg.full_lr
            tune(model, lab.Config({**cfg, "lr": lr, "warmup": int(cfg.warmup * cfg.steps)}), run, dev, examples, gpt2.END)
            got = {"exact": exact(model), "shakespeare": text_bits(model, untuned, tok.table), "moved": moved(model, begun)}
            if have_stories:
                got["stories"] = text_bits(model, stories, tok.table)
            run.finish(**got)
            results[method].append(got)
    print(f"   {'':6s} {'exact match':38s} {'Shakespeare':38s} {'moved'}")
    for method, got in results.items():
        print(f"   {method:6s} {lab.spread([g['exact'] for g in got], 3):38s} "
              f"{lab.spread([g['shakespeare'] for g in got], 4):38s} {lab.mean([g['moved'] for g in got]):.3g}")
        if have_stories:
            print(f"   {'':6s} {'':38s} TinyStories {lab.spread([g['stories'] for g in got], 4)}")
    if len(results) == 2 and cfg.seeds > 1:
        a, b = ([g["shakespeare"] for g in results[m]] for m in cfg.methods)
        print(f"   Shakespeare's bits, {cfg.methods[0]} against {cfg.methods[1]}: Welch's t {lab.welch_t(a, b):+.1f}")
    print(f"\n{lab.clock(torch, dev) - start:.0f} s of reading, training and scoring on {dev.type}")


if __name__ == "__main__":
    main()
