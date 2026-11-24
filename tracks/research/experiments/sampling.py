"""Sampling: greedy, temperature, top-k and top-p, measured as Holtzman et al. measure them.

A model gives a chance to every next character; how the next one is
picked is a separate choice. Holtzman et al. (2020), "The Curious Case of
Neural Text Degeneration", generated 5,000 passages of up to 200 word
pieces with GPT-2 Large from the start of held-out web pages, and found
(their table 1, figures 6 and 9) that taking the most likely word at
every step (greedy) gives text the model finds far more likely than
people's own, which "gets stuck in repetitive loops"; that sampling from
the whole distribution gives text it finds less likely than people's
("the model is confusing itself"); and that sampling from the nucleus,
the fewest words whose chances add up to p, "obtains closest perplexity
to human text".

Here the same measurements at laptop size, on characters: a GPT (the
learner's checkpoint from 08.04 when there is one, else a small one
trained here), prompts of `prompt` characters from the starts of speeches
in the test text, `length` characters generated after each by every
method, every seed of the sampling its own draw; for each method the
model's perplexity of what it wrote (2 to its bits per character, the
model's own chances, before any cut), beside its perplexity of what
follows those prompts in the text itself; and how often a passage ends
in a loop (the paper's repetition: a phrase of 2 or more characters
repeated at least 3 times at the end).

    python3 -m experiments.sampling
"""

import os

import numpy as np
import torch

import lab
from data import shakespeare
from experiments.language import generate, load, train
from experiments.sequences import bits
from models.gpt import GPT

CONFIG = dict(checkpoint="", layers=4, heads=4, width=64, context=64, batch=32, steps=600, lr=0.003, warmup=50,
              weight_decay=0.1, clip=1.0, every=100, prompts=16, prompt=32, length=200, seeds=3,
              methods=[["greedy", 0.0, 0, None], ["pure sampling", 1.0, 0, None], ["sampling, t=0.9", 0.9, 0, None],
                       ["sampling, t=0.7", 0.7, 0, None], ["top-k=5", 1.0, 5, None], ["nucleus, p=0.95", 1.0, 0, 0.95]],
              shown=2, device="cpu")
# Where 08.04 leaves its checkpoint: its long run (recorded with out=experiments/recorded), else its default run.
# checkpoint=PATH takes that one; checkpoint=none trains a small model even when there is one.
CHECKPOINTS = ["experiments/recorded/gpt/model.safetensors", "runs/gpt/model.safetensors"]


# @build 08.05 repeats
# Holtzman et al.'s repetition, on characters: True when ids (a list) end
# with a phrase of 2 or more symbols repeated at least 3 times in a row
# ("ee ee ee", "thee, thee, thee, ").
def repeats(ids):
    return any(ids[-L:] == ids[-2 * L:-L] == ids[-3 * L:-2 * L] for L in range(2, len(ids) // 3 + 1))
# @end


# @build 08.05 continuation_bits
# The model's bits per character of the continuations after their prompts
# (rows of prompts and of continuations, (batch, P) and (batch, n)), as
# window_bits (07.03) scores a text: the continuations read in pieces of
# model.context - P + 1 characters, each piece in a window that starts P
# characters before its first, so every character is scored from at least
# P before it (for the first piece, its prompt). The mean over every
# character of every row.
def continuation_bits(model, prompts, continuations):
    P, n = prompts.shape[1], continuations.shape[1]
    rows = torch.cat([prompts, continuations], dim=1)
    span = model.context - P + 1
    total = 0.0
    with torch.no_grad():
        for c in range(0, n, span):
            m = min(span, n - c)
            scores = model(rows[:, c:c + P - 1 + m])[:, P - 1:]
            total += bits(scores, rows[:, c + P:c + P + m]).item() * m
    return total / n
# @end


def speeches(test, prompt, n, length):
    """The starts of n speeches of the test text (a character after a blank line), evenly spread, each with
    prompt + length characters after it."""
    text = shakespeare.decode(test)
    starts = [i + 2 for i in range(len(text) - 2) if text[i:i + 2] == "\n\n" and i + 2 + prompt + length < len(text)]
    picked = [starts[int(j)] for j in np.linspace(0, len(starts) - 1, n)]
    return np.stack([test[s:s + prompt + length] for s in picked])


def main():
    cfg = lab.config(CONFIG)
    dev = lab.device(torch, cfg.device)
    V = len(shakespeare.chars())
    train_t = torch.from_numpy(shakespeare.split("train")).to(dev)
    test = shakespeare.split("test")
    start = lab.clock(torch, dev)

    found = ([] if cfg.checkpoint == "none" else [cfg.checkpoint] if cfg.checkpoint else
             [p for p in CHECKPOINTS if os.path.exists(p)])
    if found:
        model, notes = load(found[0], dev)
        c = notes["config"]
        print(f"The model: the checkpoint {found[0]}: {c['layers']} blocks of {c['heads']} heads, width {c['width']}, "
              f"windows of {c['context']}, trained {notes.get('steps', '?')} steps (validation "
              f"{notes.get('val_bits', float('nan')):.3f} bits)")
    else:
        run = lab.Run(cfg, 0, label="model")
        torch.manual_seed(0)
        model = GPT(V, cfg.context, cfg.layers, cfg.heads, cfg.width).to(dev)
        train(model, cfg, run, dev, train_t)
        run.finish(bits=run.rows[-1]["bits"])
        print(f"The model: no checkpoint from 08.04 ({cfg.checkpoint or ' or '.join(CHECKPOINTS)}), so a small one "
              f"trained here: {cfg.layers} blocks of {cfg.heads} heads, width {cfg.width}, windows of {cfg.context}, "
              f"{cfg.steps} steps (seed 0)")
    model.eval()

    text = torch.from_numpy(speeches(test, cfg.prompt, cfg.prompts, cfg.length)).to(dev)
    prompts, human = text[:, :cfg.prompt], text[:, cfg.prompt:]
    people = continuation_bits(model, prompts, human)
    print(f"{cfg.prompts} prompts of {cfg.prompt} characters (starts of speeches in the test text), {cfg.length} "
          f"characters after each, {cfg.seeds} seeds of the sampling.\nPerplexity: 2 to the model's bits per "
          f"character of the text; repetition: the passages that end in a phrase repeated 3 times or more.\n")
    print(f"   {'':18s} {'perplexity':45s} repetition")
    print(f"   {'the text itself':18s} {2 ** people:<45.4g} "
          f"{100 * lab.mean([repeats(r.tolist()) for r in human]):5.1f}%")
    shown = {}
    for name, temperature, k, p in cfg.methods:
        perplexity, repetition = [], []
        for seed in range(cfg.seeds if temperature else 1):
            drawn = generate(model, prompts, cfg.length, torch.Generator().manual_seed(seed), temperature, k, p)
            perplexity.append(2 ** continuation_bits(model, prompts, drawn))
            repetition.append(100 * lab.mean([repeats(r.tolist()) for r in drawn]))
            if seed == 0:
                shown[name] = drawn[:cfg.shown]
        run = lab.Run(cfg, 0, label=name.replace(", ", "-").replace("=", "").replace(" ", "_"))
        run.finish(perplexity=perplexity, repetition=repetition)
        spread = lab.spread(perplexity, 4) if temperature else f"{perplexity[0]:.4g} (no chance in it)"
        print(f"   {name:18s} {spread:45s} {lab.mean(repetition):5.1f}% ({', '.join(f'{r:.0f}' for r in repetition)})")

    for i in range(cfg.shown):
        print(f"\nPrompt {i + 1}: {shakespeare.decode(prompts[i].tolist())!r}")
        print(f"   the text:  {shakespeare.decode(human[i].tolist())[:100]!r}")
        for name, drawn in shown.items():
            print(f"   {name + ':':18s} {shakespeare.decode(drawn[i].tolist())[:100]!r}")
    print(f"\n{lab.clock(torch, dev) - start:.0f} s of training, sampling and scoring on {dev.type}")


if __name__ == "__main__":
    main()
