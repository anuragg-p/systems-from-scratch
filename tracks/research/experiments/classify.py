"""A new head on a pretrained body: GPT-2 sorts a bank's customer questions into 77 intents.

Radford et al. (2018) pretrained a GPT on books, then for each task put
"an added linear output layer" on the last token's vector and trained
on that task's labelled examples. Here the task is Banking77: "Is there a
way to know when my card will arrive?" is card_arrival, one of 77.

1. The baselines a model must beat: always the largest class; and a bag
   of words, each question its counts of the training words, with a
   Linear layer.
2. 08's GPT, small, trained from nothing on the labelled questions alone.
3. GPT-2's body, frozen, with a new Linear head on its vector at each
   question's last token: the body is read once, and only the head is
   trained. First on the vectors as they come, then standardised.
4. How many labelled questions each needs: the frozen body and the bag
   of words trained on fewer.
5. With tune_steps: GPT-2's body fine-tuned with the head, every weight
   trained. Not in the default run (a step of GPT-2 small is about half
   a second on a laptop's CPU); its numbers are 12.02's recorded run.

The default run uses part of the data (train= questions, test_per_class=
of each intent) so that it takes a minute; train=0 test_per_class=0 is
all of it.

    python3 -m experiments.classify

Needs GPT-2's files and Banking77: python3 -m data.fetch gpt2 banking77.
"""

import re

import numpy as np
import torch
from torch import nn

import lab
from data import banking77
from experiments.tuning import accuracy, fit, vectors
from models import gpt2 as M
from models.classifier import Classifier
from models.gpt import GPT
from tokens import gpt2

CONFIG = dict(train=3000, test_per_class=10, seeds=3, batch=64, head_steps=500, bag_lr=0.03, head_lr=0.003,
              weight_decay=0.0, small_layers=2, small_heads=4, small_width=64, small_dropout=0.0, small_steps=600,
              small_batch=32, small_lr=0.003, sizes=[100, 300, 1000], tune_steps=0, tune_batch=16, tune_lr=5e-5,
              tune_head_lr=0.003, warmup=0.06, every=100, device="cpu")


# @build 12.01 words
# The words of a text, as the bag of words counts them: runs of letters,
# digits and apostrophes, in lower case.
def words(text):
    return re.findall(r"[a-z0-9']+", text.lower())
# @end


# @build 12.01 bag
# Texts as a bag of words: a (len(texts), len(vocab)) float32 tensor, row
# i counting how often each word of vocab (a dict, word: column) occurs in
# text i. Words not in vocab are not counted.
def bag(texts, vocab):
    x = torch.zeros(len(texts), len(vocab))
    for i, text in enumerate(texts):
        for w in words(text):
            if w in vocab:
                x[i, vocab[w]] += 1
    return x
# @end


class Bag(nn.Module):
    """A Linear layer on a bag of words, shaped as a Classifier is for fit and accuracy (head, scores)."""

    def __init__(self, n, classes):
        super().__init__()
        self.head = nn.Linear(n, classes)
        nn.init.normal_(self.head.weight, 0.0, 0.02)
        nn.init.zeros_(self.head.bias)

    def scores(self, x):
        return self.head(x)


def settings(cfg, steps, batch, lr, head_lr):
    """fit's settings for one kind of model, from the script's."""
    return lab.Config({**cfg, "steps": steps, "batch": batch, "lr": lr, "head_lr": head_lr,
                       "warmup": int(cfg.warmup * steps)})


def subset(n, labels, rng):
    """n positions of labels drawn without replacement by rng, in order."""
    return np.sort(rng.choice(len(labels), n, replace=False)) if n and n < len(labels) else np.arange(len(labels))


def heads(cfg, dev, make, lr, x_train, y_train, x_test, y_test, label, at=None):
    """A head (make() gives the model) trained at rate lr on fixed inputs for every seed; test accuracy of each."""
    got = []
    for seed in range(cfg.seeds):
        run = lab.Run(cfg, seed, label=label)
        torch.manual_seed(seed)
        model = make().to(dev)
        rows = at(run.rng) if at else np.arange(len(y_train))
        fit(model, settings(cfg, cfg.head_steps, cfg.batch, lr, lr), run, dev, x_train[rows], y_train[rows])
        got.append(accuracy(model, x_test, y_test, None, dev))
        run.finish(test_accuracy=got[-1], examples=len(rows))
    return got


def main():
    cfg = lab.config(CONFIG)
    dev = lab.device(torch, cfg.device)
    start = lab.clock(torch, dev)
    tok = gpt2.load()
    names = banking77.classes()
    texts, labels = banking77.split("train")
    at = subset(cfg.train, labels, np.random.default_rng(0))
    texts, labels = [texts[i] for i in at], labels[at]
    test_texts, test_labels = banking77.split("test")
    if cfg.test_per_class:
        at = np.concatenate([np.flatnonzero(test_labels == c)[:cfg.test_per_class] for c in range(len(names))])
        test_texts, test_labels = [test_texts[i] for i in at], test_labels[at]
    seqs = [tok.encode(t) + [gpt2.END] for t in texts]
    test_seqs = [tok.encode(t) + [gpt2.END] for t in test_texts]
    counts = np.bincount(labels, minlength=len(names))
    largest = int(counts.argmax())
    print(f"1. Banking77: {len(texts):,} training questions, {len(test_texts):,} test questions, {len(names)} intents; "
          f"{np.mean([len(s) for s in seqs]):.1f} GPT-2 tokens a question\n   with END (longest {max(len(s) for s in seqs)}). "
          f"{texts[0]!r} is {names[labels[0]]}.")
    print(f"   The largest class in training, {names[largest]}, is {counts[largest] / len(labels):.2%} of it; always "
          f"guessing it scores {np.mean(test_labels == largest):.2%} on test.")
    vocab = {}
    for t in texts:
        for w in words(t):
            vocab.setdefault(w, len(vocab))
    x_bag, x_bag_test = bag(texts, vocab).to(dev), bag(test_texts, vocab).to(dev)
    bags = heads(cfg, dev, lambda: Bag(len(vocab), len(names)), cfg.bag_lr, x_bag, labels, x_bag_test, test_labels, "bag")
    print(f"   A bag of words ({len(vocab):,} training words) and a Linear layer, {cfg.head_steps} steps of {cfg.batch}, "
          f"AdamW {cfg.bag_lr}:\n   test accuracy {lab.spread(bags, 4)}")

    small = []
    for seed in range(cfg.seeds):
        run = lab.Run(cfg, seed, label="small")
        torch.manual_seed(seed)
        body = GPT(50257, 128, layers=cfg.small_layers, heads=cfg.small_heads, width=cfg.small_width,
                   dropout=cfg.small_dropout)
        model = Classifier(body, len(names), dropout=cfg.small_dropout).to(dev)
        fit(model, settings(cfg, cfg.small_steps, cfg.small_batch, cfg.small_lr, cfg.small_lr), run, dev, seqs, labels,
            gpt2.END)
        small.append(accuracy(model, test_seqs, test_labels, gpt2.END, dev))
        run.finish(test_accuracy=small[-1])
    size = sum(p.numel() for p in model.parameters())
    print(f"\n2. 08's GPT trained from nothing on these questions alone: {cfg.small_layers} blocks of {cfg.small_heads} heads, "
          f"width {cfg.small_width}\n   ({size:,} weights, {cfg.small_width * 50257:,} of them the embedding of GPT-2's "
          f"tokens), dropout {cfg.small_dropout}, {cfg.small_steps} steps of {cfg.small_batch}, AdamW {cfg.small_lr}:\n"
          f"   test accuracy {lab.spread(small, 4)}")

    body = M.load(dev)
    for p in body.parameters():
        p.requires_grad_(False)
    reading = lab.clock(torch, dev)
    frozen = Classifier(body, len(names)).to(dev)
    v_train, v_test = vectors(frozen, seqs, gpt2.END, dev), vectors(frozen, test_seqs, gpt2.END, dev)
    reading = lab.clock(torch, dev) - reading
    spread = v_train.std(0)
    big = spread.argsort(descending=True)[:3].tolist()
    print(f"\n3. GPT-2's body, frozen, read once at each question's END ({reading:.1f} s for {len(seqs) + len(test_seqs):,} "
          f"questions):\n   a vector of 768 numbers each. Over the training questions most numbers vary by about "
          f"{spread.median():.3f};\n   a few by far more: " + ", ".join(f"number {i} by {spread[i]:.2f} around "
                                                               f"{v_train[:, i].mean():.1f}" for i in big) + ".")

    def make(standardised):
        def build():
            model = Classifier(body, len(names))
            if standardised:
                model.standardise(v_train)
            return model
        return build

    raw = heads(cfg, dev, make(False), cfg.head_lr, v_train, labels, v_test, test_labels, "frozen-raw")
    print(f"   A new Linear head on those vectors as they come, {cfg.head_steps} steps of {cfg.batch}, AdamW {cfg.head_lr}: "
          f"test accuracy\n   {lab.spread(raw, 4)}")
    tuned = heads(cfg, dev, make(True), cfg.head_lr, v_train, labels, v_test, test_labels, "frozen")
    print(f"   The same head on the vectors standardised (each number less its mean over the training questions, over "
          f"its spread there):\n   test accuracy {lab.spread(tuned, 4)}")
    print(f"   Welch's t: standardised against as they come {lab.welch_t(tuned, raw):+.1f}; against the bag of words "
          f"{lab.welch_t(tuned, bags):+.1f};\n   against the small GPT {lab.welch_t(tuned, small):+.1f}")
    trained = sum(p.numel() for p in frozen.head.parameters())
    print(f"   Trained: the head's {trained:,} weights of {trained + sum(p.numel() for p in body.parameters()):,}.")

    print(f"\n4. Fewer labelled questions (each a random part of the {len(labels):,}, drawn for each seed), test accuracy:")
    print(f"   {'questions':>9s}   {'bag of words':50s}   GPT-2's body, frozen, and a head")
    for n in [s for s in cfg.sizes if s < len(labels)]:
        pick = lambda rng: subset(n, labels, rng)
        a = heads(cfg, dev, lambda: Bag(len(vocab), len(names)), cfg.bag_lr, x_bag, labels, x_bag_test, test_labels,
                  f"bag-{n}", pick)
        b = heads(cfg, dev, make(True), cfg.head_lr, v_train, labels, v_test, test_labels, f"frozen-{n}", pick)
        print(f"   {n:9,d}   {lab.spread(a, 3):50s}   {lab.spread(b, 3)}")
    print(f"   {len(labels):9,d}   {lab.spread(bags, 3):50s}   {lab.spread(tuned, 3)}   (parts 1 and 3)")

    if cfg.tune_steps:
        print(f"\n5. GPT-2's body fine-tuned with the head: every weight trained, {cfg.tune_steps} steps of {cfg.tune_batch} "
              f"questions, AdamW {cfg.tune_lr} (the head {cfg.tune_head_lr}):")
        whole = []
        for seed in range(cfg.seeds):
            run = lab.Run(cfg, seed, label="fine-tuned")
            torch.manual_seed(seed)
            model = Classifier(M.load(dev), len(names)).to(dev)
            model.standardise(v_train)
            fit(model, settings(cfg, cfg.tune_steps, cfg.tune_batch, cfg.tune_lr, cfg.tune_head_lr), run, dev, seqs,
                labels, gpt2.END)
            whole.append(accuracy(model, test_seqs, test_labels, gpt2.END, dev))
            run.finish(test_accuracy=whole[-1])
        print(f"   test accuracy {lab.spread(whole, 4)}; against the frozen body, Welch's t {lab.welch_t(whole, tuned):+.1f}")
    else:
        print("\n5. GPT-2's body fine-tuned with the head is not in this run (tune_steps=0): see 12.02's recorded run.")
    print(f"\n{lab.clock(torch, dev) - start:.0f} s of reading, training and scoring on {dev.type}")


if __name__ == "__main__":
    main()
