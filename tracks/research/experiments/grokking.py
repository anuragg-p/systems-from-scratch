"""Grokking, the experiment from the paper's text: modular arithmetic.

Power et al. (2022) train a small transformer on part of a table of
equations a o b = c modulo 97 (data/modular.py) and score it on the rest.
Their figure 1: training accuracy passes 99% in under 10^3 steps, and
validation accuracy, near chance all that while, gets there only near
10^6. This script runs the set-up their text describes (appendix A.1.2)
with the learner's GPT from module 08 (models/gpt.py, unchanged) at the
paper's depth, width and heads, and experiments/arithmetic.py's loop.

1. The data and the model.
2. Training: AdamW with the paper's rate, betas and weight decay, its
   warmup and batch size, several seeds; accuracy and loss on the whole
   training set and the whole validation set at steps spaced evenly in the
   logarithm, as the paper's figure has a log axis; the curves.
3. When each seed memorised and when it generalised, what the validation   # @from 14.03
   loss did in between, and the size of the weights over the run.           # @from 14.03

    python3 -m experiments.grokking

The default is a short run. The long run recorded in experiments/recorded/grokking/ is this script with many more
steps; its config.json files hold every setting.
"""

import math

import torch

import lab
from data import modular
from experiments.arithmetic import log_steps, train
from experiments.arithmetic import milestones                                  # @from 14.03
from models.gpt import GPT

# The paper's set-up, appendix A.1.2: "we used a transformer with 2 layers, width 128, and 4 attention heads"; "AdamW
# optimizer with learning rate 10^-3, weight decay 1, beta1 = 0.9, beta2 = 0.98, linear learning rate warmup over the
# first 10 updates, minibatch size 512 or half of training dataset size (whichever was smaller) and optimization
# budget of 10^5 gradient updates". Its data, x/y mod 97, is figure 1's; the fraction is not (see NOTES.md).
CONFIG = dict(p=97, operation="/", fraction=0.35, layers=2, heads=4, width=128, lr=1e-3, weight_decay=1.0,
              betas=[0.9, 0.98], warmup=10, batch=512, steps=350, per_decade=5, seeds=3, device="cpu")


def steps_text(s):
    return "never" if s is None else f"{s}"


def main():
    cfg = lab.config(CONFIG)
    dev = lab.device(torch, cfg.device)
    p, op = cfg.p, cfg.operation
    V = p + len(modular.SYMBOLS)
    start = lab.clock(torch, dev)
    n = len(modular.equations(p, op))
    k = round(cfg.fraction * n)
    print(f"1. The data: x {op} y mod {p}, {n} equations; {k} of them ({cfg.fraction:.0%}) to train on and {n - k} to "
          f"validate on,\n   a split of their own for each seed (data/modular.py). A guess is right 1 time in {p} "
          f"({1 / p:.4f}); its loss is ln {p} = {math.log(p):.3f} nats.")

    results, curves, losses = {}, [], []
    norms = []                                                                 # @from 14.03
    for seed in range(cfg.seeds):
        run = lab.Run(cfg, seed)
        train_rows, val_rows = (torch.from_numpy(a).to(dev) for a in modular.split(p, op, cfg.fraction, seed))
        torch.manual_seed(seed)
        model = GPT(V, 4, layers=cfg.layers, heads=cfg.heads, width=cfg.width).to(dev)
        if seed == 0:
            weights = sum(t.numel() for t in model.parameters())
            inside = weights - model.tokens.weight.numel() - model.positions.weight.numel()
            print(f"   The model: models/gpt.py's GPT, {cfg.layers} blocks of {cfg.heads} heads, width {cfg.width}, "
                  f"reading a {op} b =: {weights:,} weights,\n   {inside:,} of them outside the embeddings (the "
                  f"paper: \"about 4 x 10^5 non-embedding parameters\").")
            print(f"\n2. Training: AdamW, rate {cfg.lr:g}, betas {cfg.betas[0]:g} and {cfg.betas[1]:g}, weight decay "
                  f"{cfg.weight_decay:g}, the rate warmed up over {cfg.warmup} steps;\n   batches of "
                  f"{min(cfg.batch, math.ceil(k / 2))}; {cfg.steps} steps; {cfg.seeds} seed{'s' * (cfg.seeds > 1)}. "
                  f"Measured at {len(log_steps(cfg.steps, cfg.per_decade))} steps spaced evenly in the logarithm.")
        train(model, cfg, run, dev, train_rows, val_rows)
        rows = run.rows
        got = {key: rows[-1][key] for key in ("train_acc", "val_acc", "train_loss", "val_loss")}
        # @from 14.03
        got.update(milestones(rows, p))
        norms.append(lab.Line(f"seed {seed}", [r["step"] for r in rows], [r["norm"] for r in rows], seed))
        # @end
        run.finish(**got)
        for key, v in got.items():
            results.setdefault(key, []).append(v)
        x = [r["step"] for r in rows]
        curves += [lab.Line("training", x, [r["train_acc"] for r in rows], 1, 0.7, dashed=True),
                   lab.Line("validation", x, [r["val_acc"] for r in rows], 2, 0.8)]
        losses += [lab.Line("training", x, [r["train_loss"] for r in rows], 1, 0.7, dashed=True),
                   lab.Line("validation", x, [r["val_loss"] for r in rows], 2, 0.8)]

    print(f"   After {cfg.steps} steps (accuracy, then loss in nats):")
    for key, name in (("train_acc", "training accuracy  "), ("val_acc", "validation accuracy"),
                      ("train_loss", "training loss      "), ("val_loss", "validation loss    ")):
        print(f"   {name} {lab.spread(results[key], 4)}")
    where = f"{cfg.out}/{cfg.name}"
    lab.lines(f"{where}/accuracy.svg", curves, title=f"x {op} y mod {p}, {cfg.fraction:.0%} of the equations: accuracy",
              xlabel="step (log scale)", ylabel="accuracy", logx=True, ylim=(0, 1))
    chance = lab.Line(f"a guess, ln {p}", [1, cfg.steps], [math.log(p)] * 2, "#888888", 0.8, dashed=True)
    lab.lines(f"{where}/loss.svg", losses + [chance], title="loss (nats)", xlabel="step (log scale)", ylabel="loss",
              logx=True)
    print(f"   curves in {where}/accuracy.svg and {where}/loss.svg")

    # @from 14.03
    print("\n3. Memorised, then generalised: the first measured step at which each accuracy was 99% or more.")
    for seed in range(cfg.seeds):
        t99, v99, ratio = (results[key][seed] for key in ("train99", "val99", "ratio"))
        print(f"   seed {seed}: training at step {steps_text(t99)}, validation at step {steps_text(v99)}"
              + (f", {ratio:.1f} times later" if ratio else "")
              + (f"; validation accuracy at the first: {results['val_acc_at_train99'][seed]:.4f}" if t99 else ""))
    for key, name in (("train99", "training 99% at step  "), ("val99", "validation 99% at step"),
                      ("ratio", "times later           ")):
        got = [v for v in results[key] if v is not None]
        print(f"   {name} " + (lab.spread(got, 3) if got else "never")
              + (f" ({len(got)} of {cfg.seeds} seeds got there)" if 0 < len(got) < cfg.seeds else ""))
    print(f"   The validation loss at its highest, as times the loss of a guess (ln {p}): "
          f"{lab.spread(results['peak_over_chance'], 3)},\n   at step " + ", ".join(str(s) for s in results["peak_step"])
          + f"; at the end {lab.spread(results['val_loss'], 3)} nats.")
    print("   The weights' norm: at the start " + ", ".join(f"{v:.1f}" for v in results["norm_start"])
          + "; at its highest " + ", ".join(f"{v:.1f} (step {s})" for v, s in zip(results["norm_max"],
                                                                                  results["norm_max_step"]))
          + ";\n   when validation accuracy reached 99% "
          + ", ".join("never" if v is None else f"{v:.1f}" for v in results["norm_at_val99"])
          + "; at the end " + ", ".join(f"{v:.1f}" for v in results["norm_end"]))
    lab.lines(f"{where}/norm.svg", norms, title="the weights' norm", xlabel="step (log scale)", ylabel="norm", logx=True)
    print(f"   its curve in {where}/norm.svg")
    # @end
    print(f"\n{lab.clock(torch, dev) - start:.0f} s of training and scoring on {dev.type}")


if __name__ == "__main__":
    main()
