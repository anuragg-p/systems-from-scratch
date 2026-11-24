"""The grokking paper's claims as predictions, written down before anything is run (14.01).

    PAPER, NANDA          the two papers, as they are cited
    Claim                 key, where (in the paper), says (its words), setting, measure, paper (its number), rule
    CLAIMS                the claims module 14 tests
    verdict(rule, ours)   "held", "did not hold" or "not settled", by the claim's rule

Each claim says where in the paper it is (a figure, a section), quotes the
paper's own words, names the setting the paper ran it in, says what we will
measure, gives the paper's number and fixes the rule that will decide
whether it held. The rule is chosen now, before any run, so that a result
cannot move it. claims.py prints the table; report.py (14.04) fills in our
number and the verdict of each claim from the recorded runs' logs.

A number read off a figure with a log axis is good to about a factor of 3,
so "about" holds within a factor of 3 either way; "below" and "above" are
the direction the paper states or its figure shows.
"""

from collections import namedtuple

PAPER = ("Power, Burda, Edwards, Babuschkin and Misra (2022), Grokking: Generalization Beyond Overfitting on Small "
         "Algorithmic Datasets, arXiv 2201.02177v1")
NANDA = ("Nanda, Chan, Lieberum, Smith and Steinhardt (2023), Progress measures for grokking via mechanistic "
         "interpretability, arXiv 2301.05217v3")

Claim = namedtuple("Claim", "key where says setting measure paper rule")

FIGURE1 = "x/y mod 97, 50% of the equations to train on, Adam without weight decay, 10^6 steps"
CLAIMS = [
    Claim("memorise", "figure 1 (left), its caption",
          "Training accuracy becomes close to perfect at < 10^3 optimization steps",
          FIGURE1, "the first step at which training accuracy is 99% or more",
          "under 1000", ("below", 1000)),
    Claim("near_chance", "figure 1 (left), its caption",
          "we see very little evidence of any generalization until 10^5 steps",
          FIGURE1, "validation accuracy at that step",
          "about 0.01, chance (1/97), read off the figure", ("below", 0.05)),
    Claim("late", "figure 1 (left), its caption",
          "it takes close to 10^6 steps for validation accuracy to reach that level",
          FIGURE1, "steps until validation accuracy is 99%, divided by steps until training accuracy is",
          "about 1000 (close to 10^6 against under 10^3)", ("about", 1000)),
    Claim("generalise", "the abstract; figure 1 (left)",
          "improving generalization performance from random chance level to perfect generalization",
          FIGURE1, "the highest validation accuracy of the run",
          "about 0.99 at the end of figure 1", ("above", 0.99)),
    Claim("loss_rises", "figure 4, its caption",
          "the validation loss increases from 10^2 to about 10^5 optimization steps before it begins a second descent",
          FIGURE1, "the highest validation loss of the run, divided by the loss of a guess (ln 97)",
          "about 9 (a peak of about 20 against its chance line, about 2.3, read off)", ("above", 1.0)),
    Claim("less_data", "figure 1 (center); section 3.1.1",
          "Training time required to reach 99% validation accuracy increases rapidly as the training data "
          "fraction decreases",
          "the product in the group S5, AdamW with weight decay 1, 25% to 80% of the equations, 7 seeds",
          "k in: median steps until validation accuracy is 99% grow as 1 / fraction^k, between the smallest and the "
          "largest fraction run",
          "about 4 (about 1.1e5 steps at 30% and 1.4e4 at 50%, read off); 1 would be in proportion",
          ("above", 1.0)),
    Claim("train_sooner", "section 3.1.1",
          "the number of steps until the train accuracy first reaches 99% generally trends down as dataset size "
          "decreases",
          "the product in S5, AdamW with weight decay 1",
          "median steps until training accuracy is 99% at the smallest fraction run, divided by at the largest",
          "below 1", ("below", 1.0)),
    Claim("decay", "figure 2 (left), its caption; section 3.3",
          "Weight decay improves generalization the most",
          "S5, 10^5 steps: Adam without weight decay against AdamW with weight decay 1, 30% to 95% of the equations",
          "the highest validation accuracy without weight decay, mean over seeds, where weight decay 1 generalises",
          "about 0 at 50% (minibatch Adam), about 1 with weight decay 1, read off", ("below", 0.5)),
    Claim("more_decay", "Nanda et al. (2023), appendix D.1 and figure 27",
          "Smaller amounts of weight decay lead to slower grokking",
          "x + y mod 113, 30% of the pairs, one layer, full batch",
          "median steps until validation accuracy is 99% with weight decay 0.3, divided by with 1",
          "about 2 to 4 (about 20k epochs at 0.3 in figure 27; 5-10k at 1 in the text)", ("above", 1.0)),
    Claim("norm_falls", "Nanda et al. (2023), section 5.2 and figure 7",
          "The sums of squared weights decreases smoothly during circuit formation and more sharply during cleanup",
          "x + y mod 113, 30% of the pairs, one layer, full batch",
          "the weights' norm when validation accuracy reaches 99%, divided by its highest before then",
          "about 0.53 (the sum of squares from about 3600 down to about 1000, read off)", ("below", 1.0)),
]


# @build 14.01 verdict
# Whether a claim held, by its rule, for our number. more=True says our
# number is only a lower bound (a run that ended before it got there:
# "more than 10000 steps"). ("below", x): held when ours is under x;
# ("above", x): held when over x; ("about", x): held within a factor of 3
# either way. A lower bound settles "above" when it is already over x and
# rules out "below" and "about" once it is past them; otherwise it settles
# nothing. No number at all settles nothing. Returns "held", "did not
# hold" or "not settled".
def verdict(rule, ours, more=False):
    kind, x = rule
    if ours is None:
        return "not settled"
    if kind == "below":
        return "did not hold" if ours >= x else ("not settled" if more else "held")
    if kind == "above":
        return "held" if ours > x else ("not settled" if more else "did not hold")
    if more:
        return "did not hold" if ours > 3 * x else "not settled"
    return "held" if x / 3 <= ours <= 3 * x else "did not hold"
# @end
