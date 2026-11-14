"""A checklist for a training script: five things to measure before trusting a run.

None of these bugs crashes. Each leaves a script that runs to the end and
prints a number, and the number is wrong. Every check here judges a
measurement the script takes (a loss, gradients, an accuracy, predictions),
so it works with any engine, and returns (passed, what it saw).

1. starting_loss       before training, a classifier that knows nothing gives
                       every class the same chance, so its loss is log(classes)
2. learns_one_batch    a network can memorise a few examples: training on one
                       small batch alone must drive the loss to almost 0
3. gradients_fresh     two backward passes on the same batch, with the same
                       weights, must give the same gradient (not twice it)
4. beats_chance        after a short training, held-out examples must be
                       classified far better than by guessing
5. same_answers        scoring the same examples in another order (other
                       batchmates) must give the same predictions
"""

import math

import numpy as np


# @build 04.06 starting_loss
# Within `slack` (a fraction) of log(classes)?
def starting_loss(loss, classes, slack=0.25):
    expected = math.log(classes)
    ok = abs(loss - expected) <= slack * expected
    return ok, f"loss {loss:.3f} at the start, log({classes}) = {expected:.3f}"
# @end


# @build 04.06 learns_one_batch
# losses: the loss after each step of training on one batch alone. Did it
# end below `below`?
def learns_one_batch(losses, below=0.05):
    return losses[-1] < below, f"one batch, {len(losses)} steps: loss {losses[0]:.3f} -> {losses[-1]:.3f}"
# @end


# @build 04.06 gradients_fresh
# first, second: the gradients (lists of numpy arrays) after one and after
# two backward passes on the same batch. They must be equal, within
# rounding; the ratio of their sizes says what happened instead.
def gradients_fresh(first, second, rtol=1e-5):
    size = lambda gs: math.sqrt(sum(float(np.sum(np.asarray(g, dtype=np.float64) ** 2)) for g in gs))
    ok = all(np.allclose(a, b, rtol=rtol, atol=1e-8) for a, b in zip(first, second))
    return ok, f"the second backward's gradient is {size(second) / size(first):.2f} times the first's"
# @end


# @build 04.06 beats_chance
# accuracy on held-out examples after a short training: at least
# `at_least`, where guessing would give 1 / classes.
def beats_chance(accuracy, classes, at_least=0.5):
    return accuracy >= at_least, f"held-out accuracy {accuracy:.3f}, guessing gives {1 / classes:.3f}"
# @end


# @build 04.06 same_answers
# a, b: the predicted classes for the same examples, scored in two orders
# and put back in one order. Identical?
def same_answers(a, b):
    differ = int(np.sum(np.asarray(a) != np.asarray(b)))
    return differ == 0, f"{differ} of {len(a)} predictions change with the order"
# @end
