"""Instructions: a chat template, and a model that answers.

GPT-2 was trained to go on with web pages, not to answer. Asked "Which
is larger, 12 or 57?" it goes on with something a page might say next.
A model that answers is the same model fine-tuned on examples of asking
and answering, written in a template that marks who speaks and where an
answer ends.

1. The tasks (made by code, data/instructions.py), the template, and what
   each marker costs in GPT-2's tokens: they are ordinary text to it.
2. GPT-2 as it is, asked in the template: exact match, its first line
   against the right answer, on instances it was never trained on, in
   the wordings training uses; on the same instances in a wording kept
   out of training; and on a task kept out of training (smaller).
3. GPT-2 fine-tuned on the trained tasks in the trained wordings (LoRA at
   rank 8 on W_q and W_v by default; method=full trains every weight),
   the loss on the answer's tokens only: the same three numbers, after.
   Then a few answers decoded on to the end marker, as the template has
   it.

Every answer is greedy. What is scored is the first line, so scoring
stops each answer at its first line break (or after `longest` tokens);
the answers shown go on to the end marker.

    python3 -m experiments.instruct

Needs GPT-2's files: python3 -m data.fetch gpt2.
"""

import numpy as np
import torch

import lab
from data import instructions as I
from experiments.tuning import answers, holds, tune
from models import gpt2 as M
from models.lora import adapt, trained
from tokens import gpt2

CONFIG = dict(method="lora", rank=8, alpha=8, examples=2000, steps=80, batch=8, lr=0.003, weight_decay=0.0, warmup=0.06,
              every=20, seeds=2, scored=12, longest=6, shown=6, device="cpu")
WHAT = {"seen": "held-out instances, trained wordings", "wording": "held-out instances, the held-out wording",
        "task": "a task never trained (smaller)"}


def encode(tok, prompt, answer):
    """(the prompt in the template, the reply) as GPT-2's tokens."""
    return tok.encode(I.chat(prompt)), tok.encode(I.reply(answer))


def scored_sets(cfg):
    """The three sets every model is scored on, the same for every seed: {name: [(task, prompt, answer), ...]}."""
    rng = np.random.default_rng(1000)
    out = {"seen": [], "wording": [], "task": []}
    for task in I.TRAINED:
        ways = I.wordings(task, "train")
        for fields, answer in I.instances(task, "held", cfg.scored, rng):
            out["seen"].append((task, ways[int(rng.integers(0, len(ways)))].format(**fields), answer))
        for fields, answer in I.instances(task, "held", cfg.scored, rng):
            out["wording"].append((task, I.wordings(task, "held")[0].format(**fields), answer))
    ways = I.TASKS["smaller"][2]
    for fields, answer in I.instances("smaller", "held", cfg.scored * len(I.TRAINED), rng):
        out["task"].append(("smaller", ways[int(rng.integers(0, len(ways)))].format(**fields), answer))
    return out


def first_line(tok, tokens):
    """What a model answered: its tokens decoded, cut at the end marker, then at the first line break, stripped."""
    return tok.decode(tokens).split(I.END)[0].split("\n")[0].strip()


def score(model, tok, sets, cfg, dev):
    """Exact match on each scored set, and the answers given, {name: (share right, [(task, answer given, right)])}."""
    out = {}
    for name, rows in sets.items():
        drawn = answers(model, [tok.encode(I.chat(p)) for _, p, _ in rows], cfg.longest, tok.encode("\n"), dev)
        given = [(task, first_line(tok, d), a) for (task, _, a), d in zip(rows, drawn)]
        out[name] = (float(np.mean([g == a for _, g, a in given])), given)
    return out


def main():
    cfg = lab.config(CONFIG)
    dev = lab.device(torch, cfg.device)
    start = lab.clock(torch, dev)
    tok = gpt2.load()
    sets = scored_sets(cfg)
    print("1. The tasks, each in the first of its wordings (the last of each is held out):")
    rng = np.random.default_rng(0)
    for task in I.TASKS:
        fields, answer = I.instances(task, "train", 1, rng)[0]
        trained_on = "never trained" if task not in I.TRAINED else f"{len(I.TASKS[task][2]) - 1} wordings trained"
        print(f"   {task:8s} {I.TASKS[task][2][0].format(**fields)!r} -> {answer!r}   ({trained_on})")
    fields, answer = I.instances("larger", "train", 1, rng)[0]
    prompt, reply = encode(tok, I.TASKS["larger"][2][0].format(**fields), answer)
    print(f"   Words: {len(I.words()):,} of Tiny Shakespeare's, 3 to 6 small letters; a fifth of them, and of the number "
          f"tasks' instances, held out.\n   An example in the template, {len(prompt)} + {len(reply)} tokens (the loss is on "
          f"the last {len(reply)}):\n")
    print("      " + (I.chat(I.TASKS["larger"][2][0].format(**fields)) + I.reply(answer)).replace("\n", "\n      "))
    print("\n   What each marker costs: " + ", ".join(f"{m!r} {len(tok.encode(m))} tokens "
                                                   f"{[tok.decode([i]) for i in tok.encode(m)]}"
                                                   for m in (I.USER, I.ASSISTANT, I.END)))

    model = M.load(dev)
    before = score(model, tok, sets, cfg, dev)
    print(f"\n2. GPT-2 as it is, greedy, its first line against the answer ({cfg.scored} held-out instances of each task, "
          f"{cfg.scored * len(I.TRAINED)} in each row):")
    for name, (share, given) in before.items():
        print(f"   {WHAT[name]:42s} {share:.3f}")
    print("   What it wrote: " + "; ".join(f"{t} {g!r} (right: {a!r})" for t, g, a in before["seen"][1][::cfg.scored][:3]))

    total = sum(p.numel() for p in model.parameters())
    after = {name: [] for name in sets}
    per_task = {task: [] for task in I.TRAINED}
    for seed in range(cfg.seeds):
        run = lab.Run(cfg, seed)
        examples = []
        for task in I.TRAINED:
            ways = I.wordings(task, "train")
            for fields, answer in I.instances(task, "train", cfg.examples // len(I.TRAINED), run.rng):
                examples.append(encode(tok, ways[int(run.rng.integers(0, len(ways)))].format(**fields), answer))
        torch.manual_seed(seed)
        model = M.load(dev)
        if cfg.method == "lora":
            adapt(model, cfg.rank, cfg.alpha)
        tune(model, lab.Config({**cfg, "warmup": int(cfg.warmup * cfg.steps)}), run, dev, examples, gpt2.END)
        got = score(model, tok, sets, cfg, dev)
        for name in sets:
            after[name].append(got[name][0])
        for task in I.TRAINED:
            per_task[task].append(float(np.mean([g == a for t, g, a in got["seen"][1] if t == task])))
        run.finish(**{name: got[name][0] for name in sets}, trained=trained(model),
                   answers={name: [g for _, g, _ in got[name][1]] for name in sets})
    method = (f"LoRA at rank {cfg.rank} on W_q and W_v ({trained(model):,} weights trained of {total:,})"
              if cfg.method == "lora" else f"every weight trained ({total:,})")
    print(f"\n3. Fine-tuned: {method};\n   {len(examples):,} examples of the {len(I.TRAINED)} trained tasks, {cfg.steps} steps "
          f"of {cfg.batch}, AdamW {cfg.lr}, the loss on the reply's tokens only. Exact match after:")
    for name in sets:
        print(f"   {WHAT[name]:42s} {lab.spread(after[name], 3)}")
    print("   By task, held-out instances, trained wordings: " + ", ".join(f"{t} {lab.mean(v):.2f}"
                                                                         for t, v in per_task.items()))
    rows = [sets[name][i] for name in sets for i in range(0, len(sets[name]), max(1, len(sets[name]) // 2))]
    rows = rows[:cfg.shown]
    end = tok.encode("\n" + I.END)
    drawn = answers(model, [tok.encode(I.chat(p)) for _, p, _ in rows], cfg.longest + len(end), end, dev)
    print(f"   Decoded on to the end marker (seed {cfg.seeds - 1}); {sum(holds(d, end) for d in drawn)} of {len(rows)} "
          f"wrote it:")
    for (task, p, a), d in zip(rows, drawn):
        print(f"      {p!r} -> {tok.decode(d)!r}" + ("" if first_line(tok, d) == a else f"   (right: {a!r})"))
    print(f"\n{lab.clock(torch, dev) - start:.0f} s of loading, training and answering on {dev.type}")


if __name__ == "__main__":
    main()
