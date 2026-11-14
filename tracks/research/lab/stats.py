"""How far a number moves by chance: the spread of a result over seeds.

One run gives one number, and a second run with another seed gives another.
Both are draws from the spread of numbers the method gives by chance: which
points were sampled, where the weights started, the order of the batches.
A result is the middle of that spread with its width, never one draw from
it, and two methods differ only when the gap between them is wide next to
how much each moves by chance.
"""

import math


# @build 00.03 mean
# The mean of a list of numbers.
def mean(xs):
    return sum(xs) / len(xs)
# @end


# @build 00.03 sd
# Their sample standard deviation: the root of the mean squared distance
# from the mean, dividing by n - 1 rather than n, since the mean was itself
# taken from the same numbers (with n of 1 there is no spread to measure:
# nan).
def sd(xs):
    if len(xs) < 2:
        return float("nan")
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))
# @end


# @build 00.03 spread
# One line for a result over seeds: "0.0432 +- 0.0051 (min 0.0371, max
# 0.0502, 5 seeds)", the mean and standard deviation, then the smallest and
# largest, to `digits` significant digits. The page prints three or four:
# the last digits of a float differ from machine to machine.
def spread(xs, digits=3):
    g = f".{digits}g"
    return (f"{mean(xs):{g}} +- {sd(xs):{g}} (min {min(xs):{g}}, max {max(xs):{g}}, "
            f"{len(xs)} seed{'s' if len(xs) != 1 else ''})")
# @end


# @build 00.03 welch_t
# How many times wider the gap between two sets of runs' means is than the
# noise in that gap: (mean(a) - mean(b)) / sqrt(sd(a)^2 / len(a) + sd(b)^2 /
# len(b)), Welch's t. Near 0 the two cannot be told apart; past about 3
# (for five seeds a side) chance alone rarely makes a gap that wide.
def welch_t(a, b):
    noise = math.sqrt(sd(a) ** 2 / len(a) + sd(b) ** 2 / len(b))
    return (mean(a) - mean(b)) / noise if noise > 0 else float("inf") * (mean(a) - mean(b))
# @end
