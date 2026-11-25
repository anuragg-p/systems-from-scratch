"""The reproduction report: each claim of 14.01, the paper's number, ours, and whether it held.

Every number in the report is read from the logs of the recorded runs,
14.03's (experiments/recorded/grokking) and 14.04's
(experiments/recorded/ablations), or from their config.json files; the
claims, the paper's numbers and the rules come from 14.01's
experiments/predictions.py. Nothing in it is typed in by hand.

1. What we ran, against the paper's set-up: every setting that differs,
   and how our model differs from theirs.
2. Each claim: where in the paper, the paper's number, ours (the median of
   the seeds, and each seed), and its verdict by the rule fixed in 14.01.
3. What the change of start did (14.04's third ablation).

The report is printed and written to <out>/report/report.txt.

    python3 -m experiments.report
"""

import math
import os

import lab
from experiments.arithmetic import first_step, median_steps, read_runs, read_seeds
from experiments.predictions import CLAIMS, PAPER, SETUP, verdict

CONFIG = dict(figure="experiments/recorded/grokking", ablations="experiments/recorded/ablations")

# How models/gpt.py's GPT differs from the paper's transformer (the authors' code, openai/grok, read at commit
# 3d64b1d8: grok/transformer.py): words only, no numbers.
MODEL = ["each block's layer norms come before its attention and its MLP (the paper's code: after each addition), "
         "and there is a last layer norm",
         "GELU in the MLP (the paper's code: ReLU)",
         "learned positions (the paper's code: fixed sines and cosines)",
         "the output scores are the embedding, tied (the paper's code: a Linear layer of its own)",
         "every Linear layer has a bias (the paper's code: none)",
         "it starts as GPT-2 does, every weight small (the paper's code keeps PyTorch's own start, far larger: "
         "the third part below is what that does)",
         "weight decay on every weight, as the paper's code has it; the paper's text does not say which"]


def median(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2] if len(xs) % 2 else (xs[len(xs) // 2 - 1] + xs[len(xs) // 2]) / 2


# @build 14.04 norm_ratio
# The weights' norm (from a run's log, rows) at the step validation
# accuracy first reached 99%, divided by its highest at or before that
# step: below 1 if the weights shrank on the way to generalising. None if
# validation accuracy never got there.
def norm_ratio(rows):
    at = first_step(rows, "val_acc", 0.99)
    if at is None:
        return None
    before = [r["norm"] for r in rows if r["step"] <= at]
    return before[-1] / max(before)
# @end


# @build 14.04 outcomes
# Our number for every claim, from the recorded runs: the figure's runs
# (fig, a list of (config, rows), one for each seed) and the ablations'
# (abl: read_runs of their folder). Each is (value, more, each): the median
# over seeds, more=True when that median is only a lower bound (runs that
# never got there in their steps), and the seeds' own values as text. A
# fraction's sweep gives k, the power in steps ~ 1 / fraction^k between its
# smallest and largest fraction.
def outcomes(fig, abl):
    p, steps = fig[0][0]["p"], fig[0][0]["steps"]
    t99 = [first_step(rows, "train_acc", 0.99) for _, rows in fig]
    v99 = [first_step(rows, "val_acc", 0.99) for _, rows in fig]
    at_t99 = [next(r["val_acc"] for r in rows if r["step"] == t) for (_, rows), t in zip(fig, t99) if t is not None]
    ratios = [(v or steps) / t for t, v in zip(t99, v99) if t is not None]
    peaks = [max(r["val_loss"] for r in rows) / math.log(p) for _, rows in fig]
    best = [max(r["val_acc"] for r in rows) for _, rows in fig]
    norms = [norm_ratio(rows) for _, rows in fig]

    def text(xs, f="{:.3g}"):
        return ", ".join("never" if x is None else f.format(x) for x in xs)

    def runs(**want):
        got = [(c, rows) for seeds in abl.values() for c, rows in seeds if all(c[k] == v for k, v in want.items())]
        return sorted(got, key=lambda cr: cr[0]["seed"])

    c = next(iter(abl.values()))[0][0]
    small, large = min(c["fractions"]), max(c["fractions"])
    by = {f: runs(fraction=f, weight_decay=c["fraction_decay"], start=1.0) for f in (small, large)}
    v_small, more_s = median_steps([first_step(r, "val_acc", 0.99) for _, r in by[small]], c["steps"])
    v_large, more_l = median_steps([first_step(r, "val_acc", 0.99) for _, r in by[large]], c["steps"])
    t_small = median([first_step(r, "train_acc", 0.99) or c["steps"] for _, r in by[small]])
    t_large = median([first_step(r, "train_acc", 0.99) or c["steps"] for _, r in by[large]])
    k = None if more_l else math.log(v_small / v_large) / math.log(large / small)
    none = runs(fraction=c["decay_fraction"], weight_decay=0.0, start=1.0)
    best_none = [max(r["val_acc"] for r in rows) for _, rows in none]
    by_wd = {wd: median_steps([first_step(r, "val_acc", 0.99) for _, r in runs(fraction=c["decay_fraction"],
                                                                             weight_decay=wd, start=1.0)], c["steps"])
             for wd in (0.3, 1.0)}
    return {
        "memorise": (median([t for t in t99 if t is not None]) if None not in t99 else steps, None in t99, text(t99)),
        "near_chance": (median(at_t99) if at_t99 else None, False, text(at_t99)),
        "late": (median(ratios) if ratios else None, None in v99,
                 text([v / t if v and t else None for t, v in zip(t99, v99)])),
        "generalise": (median(best), False, text(best, "{:.4f}")),
        "loss_rises": (median(peaks), False, text(peaks)),
        "less_data": (k, more_s and not more_l,
                      f"{small:g}: {'more than ' * more_s}{v_small} steps, {large:g}: {v_large} steps"),
        "train_sooner": (t_small / t_large, False, f"{small:g}: {t_small} steps, {large:g}: {t_large} steps"),
        "decay": (sum(best_none) / len(best_none), False, text(best_none, "{:.4f}")),
        "more_decay": (None if by_wd[1.0][1] else by_wd[0.3][0] / by_wd[1.0][0], by_wd[0.3][1],
                       f"0.3: {'more than ' * by_wd[0.3][1]}{by_wd[0.3][0]} steps, 1: {by_wd[1.0][0]} steps"),
        "norm_falls": (median([n for n in norms if n is not None]) if None not in norms else None, False, text(norms)),
    }
# @end


# @build 14.04 changes
# Every setting of a run's config that differs from the paper's set-up
# (predictions.SETUP): one line each, ours against the paper's and where
# the paper gives it.
def changes(config):
    return [f"{key}: ours {config[key]}, the paper's {value} ({where})"
            for key, (value, where) in SETUP.items() if config[key] != value]
# @end


def number(x, more=False):
    return "none" if x is None else ("more than " if more else "") + (f"{x:.3g}" if isinstance(x, float) else str(x))


def steps(s):
    return "never" if s is None else str(s)


def main():
    cfg = lab.config(CONFIG)
    fig, abl = read_seeds(cfg.figure), read_runs(cfg.ablations)
    c, a = fig[0][0], next(iter(abl.values()))[0][0]
    lines = [f"A reproduction of {PAPER},", f"with the learner's GPT. Read from the logs of {cfg.figure} ({len(fig)} "
             f"seeds) and {cfg.ablations} ({sum(len(s) for s in abl.values())} runs).", "",
             f"1. What we ran (x {c['operation']} y mod {c['p']}, {c['seeds']} seeds of {c['steps']} steps), against "
             f"the paper's set-up:"]
    lines += [f"   - {line}" for line in changes(c)]
    lines += [f"   - weight_decay: ours {c['weight_decay']:g}, as the text; {SETUP['weight_decay'][1]}"]
    lines += ["   The model, models/gpt.py's GPT at the paper's depth, width and heads, against the paper's code:"]
    lines += [f"   - {line}" for line in MODEL]
    lines += ["", f"2. The claims. Ours is the median over the seeds, decay's their mean (each seed's after it); the ablations ran each "
                  f"setting {a['seeds']} seeds, at most {a['steps']} steps."]
    got, tally = outcomes(fig, abl), {}
    for claim in CLAIMS:
        value, more, each = got[claim.key]
        v = verdict(claim.rule, value, more)
        tally[v] = tally.get(v, 0) + 1
        kind, x = claim.rule
        lines += [f"   {claim.key} ({claim.where}): \"{claim.says}\"",
                  f"      the paper: {claim.paper}", f"      ours: {number(value, more)} ({each})",
                  f"      {v} (held if {'within a factor of 3 of' if kind == 'about' else kind} {x:.4g})"]
    lines += ["   " + ", ".join(f"{v}: {n}" for v, n in sorted(tally.items())) + f", of {len(CLAIMS)} claims."]
    lines += ["", f"3. What the start did, at the paper's {a['start_fraction']:.0%} of the equations and weight decay "
                  f"{a['start_decay']:g} (the step at which each accuracy first reached 99%):"]
    for start in a["starts"]:
        seeds = [(cc, rows) for runs in abl.values() for cc, rows in runs
                 if cc["start"] == start and cc["fraction"] == a["start_fraction"] and cc["weight_decay"] == a["start_decay"]]
        t99 = [first_step(rows, "train_acc", 0.99) for _, rows in seeds]
        v99 = [first_step(rows, "val_acc", 0.99) for _, rows in seeds]
        name = "GPT's own start" if start == 1 else f"{start:g} times larger"
        later = ", ".join(f"{v / t:.1f}" if v and t else "never" for t, v in zip(t99, v99))
        lines += [f"   {name:22s} training {', '.join(steps(s) for s in t99)}; validation {', '.join(steps(s) for s in v99)}"
                  f"; times later {later}"]
    text = "\n".join(lines)
    print(text)
    path = os.path.join(cfg.out, cfg.name, "report.txt")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text + "\n")
    print(f"\nthe report in {path}")


if __name__ == "__main__":
    main()
