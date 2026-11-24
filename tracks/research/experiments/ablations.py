"""Ablations: what the late generalising depends on, one setting changed at a time.

14.03's run (x/y mod 97, AdamW, weight decay 1, 35% of the equations)
memorised in a few hundred steps and generalised several times later. Here
each run changes one thing and records the step at which validation
accuracy first reached 99%: how long the model takes to generalise.

1. Weight decay: none, and two sizes (the paper's section 3.3 and figure
   2, left; Nanda et al.'s appendix D.1).
2. The fraction of the equations trained on (figure 1, center; section
   3.1.1).
3. The start: the GPT's own, as GPT-2's (every weight with sd 0.02),
   against one made larger, at the paper's own 50% of the equations. The
   paper's code keeps PyTorch's start, far larger than GPT-2's.

A run stops at the first measured step at which validation accuracy is
99% or more (that step is the measurement), or after `steps` steps. Every
run's config.json, log.jsonl and summary.json are written as lab.Run lays
them out, and the table is read back from them.

    python3 -m experiments.ablations

A minute of this machine's CPU is about 1500 steps of the paper's model,
too few for any run of the table to generalise. So the default does not
train: it reads the recorded runs (`runs`, experiments/recorded/ablations)
and prints their table. train=True runs them again, into `out`.
"""

import torch

import lab
from data import modular
from experiments.arithmetic import first_step, median_steps, read_runs, scaled_start, train
from models.gpt import GPT

CONFIG = dict(p=97, operation="/", layers=2, heads=4, width=128, lr=1e-3, betas=[0.9, 0.98], warmup=10, batch=512,
              per_decade=10, steps=6000, seeds=3, decays=[0.0, 0.3, 1.0], decay_fraction=0.4,
              fractions=[0.35, 0.4, 0.5], fraction_decay=1.0, starts=[1.0, 10.0], start_fraction=0.5, start_decay=1.0,
              train=False, runs="experiments/recorded/ablations", device="cpu")


# @build 14.04 settings
# Every run the three sweeps need, as (fraction, weight decay, start), in
# order and each once (a setting two sweeps share is run once): the
# weight decays at cfg.decay_fraction of the equations, the fractions at
# weight decay cfg.fraction_decay, and the starts at cfg.start_fraction
# and cfg.start_decay; every one with GPT's own start (1) but the starts'.
def settings(cfg):
    want = ([(cfg.decay_fraction, wd, 1.0) for wd in cfg.decays]
            + [(f, cfg.fraction_decay, 1.0) for f in cfg.fractions]
            + [(cfg.start_fraction, cfg.start_decay, s) for s in cfg.starts])
    return list(dict.fromkeys(want))
# @end


def label(fraction, weight_decay, start):
    return f"fraction{fraction:g}-decay{weight_decay:g}-start{start:g}"


def run_all(cfg, dev):
    """Every setting, every seed: trained until validation accuracy is 99% or for cfg.steps steps."""
    V = cfg.p + len(modular.SYMBOLS)
    for fraction, weight_decay, start in settings(cfg):
        c = lab.Config(cfg, fraction=fraction, weight_decay=weight_decay, start=start)
        for seed in range(cfg.seeds):
            run = lab.Run(c, seed, label=label(fraction, weight_decay, start))
            train_rows, val_rows = (torch.from_numpy(a).to(dev) for a in
                                    modular.split(cfg.p, cfg.operation, fraction, seed))
            torch.manual_seed(seed)
            model = scaled_start(GPT(V, 4, layers=cfg.layers, heads=cfg.heads, width=cfg.width).to(dev), start)
            train(model, c, run, dev, train_rows, val_rows, stop=True)
            rows = run.rows
            run.finish(train99=first_step(rows, "train_acc", 0.99), val99=first_step(rows, "val_acc", 0.99),
                       best_val_acc=max(r["val_acc"] for r in rows), last_step=rows[-1]["step"])


# @build 14.04 sweep
# One row of the table for each value of a sweep, from the runs read back
# (read_runs): for each run whose config matches `fixed` (a dict of
# settings) and has `key` equal to the value, the step at which training
# accuracy and validation accuracy first reached 99% (None: never, within
# the run's steps) and its best validation accuracy. Returns a list of
# (value, train99s, val99s, bests, steps), seeds in order.
def sweep(runs, key, values, fixed):
    out = []
    for value in values:
        got = [(c, rows) for seeds in runs.values() for c, rows in seeds
               if c[key] == value and all(c[k] == v for k, v in fixed.items())]
        got.sort(key=lambda cr: cr[0]["seed"])
        out.append((value, [first_step(rows, "train_acc", 0.99) for _, rows in got],
                    [first_step(rows, "val_acc", 0.99) for _, rows in got],
                    [max(r["val_acc"] for r in rows) for _, rows in got], max((c["steps"] for c, _ in got), default=0)))
    return out
# @end


def tables(c):
    """The three sweeps of a run's settings c: (title, the setting swept, its values, the settings held)."""
    return [(f"Weight decay, {c['decay_fraction']:.0%} of the equations to train on", "weight_decay", c["decays"],
             dict(fraction=c["decay_fraction"], start=1.0)),
            (f"The fraction of the equations to train on, weight decay {c['fraction_decay']:g}", "fraction",
             c["fractions"], dict(weight_decay=c["fraction_decay"], start=1.0)),
            (f"The start, as a multiple of GPT's own, {c['start_fraction']:.0%} of the equations, weight decay "
             f"{c['start_decay']:g}", "start", c["starts"], dict(fraction=c["start_fraction"],
                                                                 weight_decay=c["start_decay"]))]


def show(name, table, budget_text):
    print(name)
    for value, t99s, v99s, bests, steps in table:
        med, more = median_steps(v99s, steps)
        each = ", ".join("never" if s is None else str(s) for s in v99s)
        print(f"   {value:<6g} validation 99% at step {each:24s} median {'more than ' * more}{med}")
        print(f"   {'':6s} training 99% at step   {', '.join('never' if s is None else str(s) for s in t99s):24s} "
              f"best validation accuracy {', '.join(f'{b:.3f}' for b in bests)}")
    print(f"   (never: not within {budget_text})")


def main():
    cfg = lab.config(CONFIG)
    dev = lab.device(torch, cfg.device)
    start = lab.clock(torch, dev)
    if cfg.train:
        run_all(cfg, dev)
        where = f"{cfg.out}/{cfg.name}"
    else:
        where = cfg.runs
        print(f"A minute of CPU holds about 1500 steps of this model, too few for any run of the table to generalise;\n"
              f"so this reads the runs recorded in {where} (train=True runs them again).\n")
    runs = read_runs(where)
    first = next(iter(runs.values()))[0][0]
    budget = f"{first['steps']} steps; {first['seeds']} seeds each, x {first['operation']} y mod {first['p']}"
    for i, (name, key, values, fixed) in enumerate(tables(first), 1):
        show(f"{'' if i == 1 else chr(10)}{i}. {name}:", sweep(runs, key, values, fixed), budget)
    print(f"\n{lab.clock(torch, dev) - start:.0f} s of training and reading on {dev.type}")


if __name__ == "__main__":
    main()
