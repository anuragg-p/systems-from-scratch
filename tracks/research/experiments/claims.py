"""Reading a paper for what it claims: the grokking paper's claims, as predictions with numbers.

Power, Burda, Edwards, Babuschkin and Misra (2022), "Grokking:
Generalization Beyond Overfitting on Small Algorithmic Datasets", arXiv
2201.02177v1. Before anything is run, each claim the module will test is
written down (experiments/predictions.py): where in the paper it is, its
words, the setting the paper ran it in, what we will measure, the paper's
number, and the rule that will say whether it held. 14.03 and 14.04 run
the experiments; report.py (14.04) fills in the outcome of each claim.

1. The claims, as predictions.
2. The baselines any run must beat, on the paper's own data (data/modular.py):
   a guess (chance), and a model that only memorises.

    python3 -m experiments.claims
"""

import math
from collections import Counter

import lab
from data import modular
from experiments.predictions import CLAIMS, NANDA, PAPER

CONFIG = dict(p=97, operation="/", fraction=0.5, seeds=3)


# @build 14.01 memoriser
# What a model that only memorises scores: every training equation looked
# up in a table (so it is always right on them), and for an equation not in
# the table, the answer that is commonest in the training set. Returns its
# accuracy on the training rows and on the validation rows (each (n, 5),
# the answer in the last column).
def memoriser(train, val):
    table = {tuple(row[:4]): row[4] for row in train.tolist()}
    guess = Counter(train[:, 4].tolist()).most_common(1)[0][0]

    def accuracy(rows):
        return sum(table.get(tuple(row[:4]), guess) == row[4] for row in rows.tolist()) / len(rows)
    return accuracy(train), accuracy(val)
# @end


def main():
    cfg = lab.config(CONFIG)
    print(f"1. What the paper claims, as predictions (before running anything).\n   The paper: {PAPER}.\n"
          f"   And one that explains it: {NANDA}.")
    for i, c in enumerate(CLAIMS, 1):
        kind, x = c.rule
        rule = f"within a factor of 3 of {x:g}" if kind == "about" else f"{kind} {x:.4g}"
        print(f"\n   {i:2d}. {c.key} ({c.where})\n       \"{c.says}\"\n       the paper's setting: {c.setting}\n"
              f"       we measure: {c.measure}\n       the paper: {c.paper}\n       held if ours is {rule}")

    p, op = cfg.p, cfg.operation
    rows = modular.equations(p, op)
    print(f"\n2. The baselines, x {op} y mod {p}: {len(rows)} equations, {cfg.fraction:.0%} of them to train on.")
    example = rows[(rows[:, 0] == 20 % p) & (rows[:, 1] == 15 % p)]
    a, b, c = example[0]
    names = modular.names(p)
    print(f"   An equation, its five tokens: {' '.join(names[t] for t in modular.tokens(example, p, op)[0])}"
          + (f" (as {c} x {b} = {c * b} = {a} mod {p})" if op == "/" else ""))
    print(f"   A guess: accuracy 1/{p} = {1 / p:.4f}; loss ln {p} = {math.log(p):.3f} nats (the cross-entropy of "
          f"equal chances)")
    got = [memoriser(*modular.split(p, op, cfg.fraction, seed)) for seed in range(cfg.seeds)]
    print(f"   A memoriser (the table of training equations, else the commonest training answer), {cfg.seeds} splits:\n"
          f"      training accuracy   {lab.spread([a for a, _ in got], 4)}\n"
          f"      validation accuracy {lab.spread([b for _, b in got], 4)}")
    print("   A run has learned the operation only if its validation accuracy is far above these.")


if __name__ == "__main__":
    main()
