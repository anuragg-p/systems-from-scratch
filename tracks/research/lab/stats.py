"""How far a number moves by chance: the spread of a result over seeds.

One run gives one number, and a second run with another seed gives another.
Both are draws from the spread of numbers the method gives by chance: which
points were sampled, where the weights started, the order of the batches.
A result is the middle of that spread with its width, never one draw from
it, and two methods differ only when the gap between them is wide next to
how much each moves by chance.
What a search of n trials buys: best_of.                                  # @from 13.01
How far a mean of a few seeds can be from the truth, and whether two      # @from 13.02
arms differ: sem, t_density, t_cdf, t_quantile, interval, difference,     # @from 13.02
bootstrap, seeds_needed; and batch_sem, for neighbours that move together. # @from 13.02
How much the best of k runs is ahead by luck alone: normal_best.          # @from 13.03
A power law through points, and what it predicts: power_law,              # @from 13.04
power_interval.                                                           # @from 13.04
"""

import functools                                                          # @from 13.02
import math
from statistics import NormalDist                                         # @from 13.02
import numpy as np                                                        # @from 13.02


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
# the last digits of a float differ from machine to machine. One seed has
# no spread to show, only its number: "0.0496 (1 seed)".
def spread(xs, digits=3):
    g = f".{digits}g"
    if len(xs) == 1:
        return f"{xs[0]:{g}} (1 seed)"
    return f"{mean(xs):{g}} +- {sd(xs):{g}} (min {min(xs):{g}}, max {max(xs):{g}}, {len(xs)} seeds)"
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


# @build 13.01 best_of
# What a search of n trials buys, worked out from the N trials one search
# made: the expected score of the best (the lowest) of n of them drawn at
# random, none twice. In order from best to worst, the i-th (from 0) is the
# best of a draw exactly when it is drawn and the other n - 1 come from the
# N - 1 - i after it: comb(N - 1 - i, n - 1) of the comb(N, n) draws. With
# reported, the trials are ranked by scores (validation) but the expected
# number given is reported's (test) for the one chosen.
def best_of(scores, n, reported=None):
    reported = scores if reported is None else reported
    order = sorted(range(len(scores)), key=lambda i: scores[i])
    N = len(scores)
    return sum(reported[j] * math.comb(N - 1 - i, n - 1) for i, j in enumerate(order)) / math.comb(N, n)
# @end


# @build 13.02 sem
# The standard error of the mean of xs: how far the mean of n numbers moves
# from one set of n to another drawn the same way, sd / sqrt(n).
def sem(xs):
    return sd(xs) / math.sqrt(len(xs))
# @end


# @build 13.02 t_density
# Student's t with df degrees of freedom (Gosset, 1908): the spread of
# (mean - truth) / sem over sets of df + 1 numbers drawn from a normal
# distribution. Gamma((df + 1) / 2) / (sqrt(df pi) Gamma(df / 2)) (1 + x^2 /
# df)^(-(df + 1) / 2): a bell like the normal's with fatter tails, the
# fatter the fewer the numbers, since the sd in the sem was estimated from
# them too (lgamma: the gammas of a large df overflow).
def t_density(x, df):
    c = math.exp(math.lgamma((df + 1) / 2) - math.lgamma(df / 2)) / math.sqrt(df * math.pi)
    return c * (1 + x * x / df) ** (-(df + 1) / 2)
# @end


# @build 13.02 t_cdf
# The chance that t with df degrees of freedom is below t: half (the area
# left of 0) plus the area under t_density from 0 to t, by Simpson's rule on
# `steps` slices (weights 1, 4, 2, 4, ..., 2, 4, 1, times the slice / 3).
# For t below 0 the slices are negative and so is the area.
def t_cdf(t, df, steps=2000):
    h = t / steps
    ends = t_density(0.0, df) + t_density(t, df)
    inside = sum((4 if k % 2 else 2) * t_density(k * h, df) for k in range(1, steps))
    return 0.5 + (ends + inside) * h / 3
# @end


# @build 13.02 t_quantile
# The t that Student's t with df degrees of freedom is below with chance p:
# t_cdf turned around, by Newton's method from 0. Each step goes the chance
# still missing divided by the slope there, which is the density; t_cdf
# bends down past 0, so every step falls short and the next goes on. Below
# p = 0.5 the same, mirrored. With 3 seeds (df 2) the 95% interval's is
# 4.30, against the normal's 1.96. The same few are asked for again and
# again, so each answer is kept (lru_cache).
@functools.lru_cache(maxsize=1024)
def t_quantile(p, df):
    if p < 0.5:
        return -t_quantile(1 - p, df)
    t = 0.0
    for _ in range(200):
        step = (p - t_cdf(t, df)) / t_density(t, df)
        t += step
        if abs(step) < 1e-10 * (1 + t):
            break
    return t
# @end


# @build 13.02 interval
# The range that holds the mean of what xs were drawn from (the mean of
# infinitely many seeds), with chance `level`: mean +- t sem, the t that
# Student's t with n - 1 degrees of freedom is below with chance (1 +
# level) / 2. A pair (low, high).
def interval(xs, level=0.95):
    half = t_quantile((1 + level) / 2, len(xs) - 1) * sem(xs)
    return mean(xs) - half, mean(xs) + half
# @end


# @build 13.02 difference
# mean(a) - mean(b), and the range that holds it with chance `level`: a
# triple (difference, low, high). paired: a[i] and b[i] are one seed's runs
# of the two arms, with what can be shared between them shared (data order,
# starting weights): the interval of the differences a[i] - b[i], whose
# spread leaves out what a seed does to both. Not paired: the two standard
# errors added in squares, va + vb (va = sem(a)^2), and t with Welch and
# Satterthwaite's degrees of freedom, (va + vb)^2 / (va^2 / (len(a) - 1) +
# vb^2 / (len(b) - 1)).
def difference(a, b, paired=False, level=0.95):
    d = mean(a) - mean(b)
    if paired:
        lo, hi = interval([x - y for x, y in zip(a, b, strict=True)], level)
        return d, lo, hi
    va, vb = sem(a) ** 2, sem(b) ** 2
    df = (va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1))
    half = t_quantile((1 + level) / 2, df) * math.sqrt(va + vb)
    return d, d - half, d + half
# @end


# @build 13.02 bootstrap
# An interval by resampling (Efron, 1979), for any statistic: each of the
# groups drawn again, as many numbers as it has, with replacement, from
# itself (rng, a numpy Generator), `resamples` times; the statistic of each
# new set of groups (statistic takes them as numpy arrays, in order); the
# middle `level` of those values: the percentile interval, a pair (low,
# high). It needs no formula for the statistic's error, and it knows only
# the spread the groups show: with 3 numbers there are 10 different
# resamples, and the interval is too narrow.
def bootstrap(groups, statistic, rng, resamples=10000, level=0.95):
    groups = [np.asarray(g, dtype=np.float64) for g in groups]
    drawn = [g[rng.integers(0, len(g), (resamples, len(g)))] for g in groups]
    values = np.array([statistic(*(d[r] for d in drawn)) for r in range(resamples)])
    lo, hi = np.quantile(values, [(1 - level) / 2, (1 + level) / 2])
    return float(lo), float(hi)
# @end


# @build 13.02 seeds_needed
# How many seeds each arm needs for a true difference of `size` to come out
# beyond the noise (its `level` interval clear of 0) with chance `power`:
# the smallest n at which size is (t at (1 + level) / 2 plus t at power)
# standard errors of the difference. That standard error is sd sqrt(2 / n)
# for two arms of n independent runs, each with spread sd; paired, sd is
# the spread of the seeds' differences and it is sd / sqrt(n). The normal's
# quantiles give an n too small (t's are larger); from there n goes up one
# at a time until the t's at its degrees of freedom agree.
def seeds_needed(size, sd, level=0.95, power=0.8, paired=False):
    k = 1 if paired else 2
    z = NormalDist().inv_cdf((1 + level) / 2) + NormalDist().inv_cdf(power)
    n = max(2, math.ceil(k * (z * sd / size) ** 2))
    while True:
        df = n - 1 if paired else 2 * (n - 1)
        t = t_quantile((1 + level) / 2, df) + t_quantile(power, df)
        if n >= k * (t * sd / size) ** 2:
            return n
        n += 1
# @end


# @build 13.02 batch_sem
# The standard error of the mean of xs when neighbours move together (the
# scores of consecutive windows of one text, which share a scene and its
# names): xs cut into consecutive batches of `size` (a last, shorter one left
# out), and the sem of the batches' means. With size 1 it is sem(xs); as size
# grows past the stretch over which neighbours move together it stops
# growing, and that is the honest one. (Miller's clustered standard errors
# are the same idea with the groups given.)
def batch_sem(xs, size):
    k = len(xs) // size
    return sem([mean(xs[i * size:(i + 1) * size]) for i in range(k)])
# @end


# @build 13.03 normal_best
# The expected largest of k numbers drawn from a normal distribution of
# mean 0 and sd 1: the integral of x times the density of the largest, k
# phi(x) Phi(x)^(k - 1) (one of the k at x, the other k - 1 below it), by
# Simpson's rule from -10 to 10. 0 for k = 1, 0.564 for 2 (1 / sqrt(pi)),
# 1.54 for 10: how far the best of k runs is above their middle by chance,
# in standard deviations.
def normal_best(k, steps=4000):
    phi = NormalDist()
    h = 20 / steps
    f = lambda x: x * k * phi.pdf(x) * phi.cdf(x) ** (k - 1)
    total = f(-10) + f(10) + sum((4 if i % 2 else 2) * f(-10 + i * h) for i in range(1, steps))
    return total * h / 3
# @end


# @build 13.04 power_law
# The power law y = a x^-alpha through points (xs, ys), all positive: a
# straight line through (ln x, ln y) by least squares, slope -alpha and
# intercept ln a. Returned as a dict: alpha, a, and what an interval needs:
# the number of points n, the mean of ln x (mean_log_x), the sum of the
# squares of ln x about it (sxx), the residuals' standard deviation s (with
# n - 2 degrees of freedom: two numbers were fitted), and alpha's standard
# error, s / sqrt(sxx).
def power_law(xs, ys):
    u, v = [math.log(x) for x in xs], [math.log(y) for y in ys]
    mu, mv = mean(u), mean(v)
    sxx = sum((x - mu) ** 2 for x in u)
    slope = sum((x - mu) * (y - mv) for x, y in zip(u, v)) / sxx
    cut = mv - slope * mu
    s = math.sqrt(sum((y - cut - slope * x) ** 2 for x, y in zip(u, v)) / (len(u) - 2))
    return dict(alpha=-slope, a=math.exp(cut), n=len(u), mean_log_x=mu, sxx=sxx, s=s, alpha_se=s / math.sqrt(sxx))
# @end


# @build 13.04 power_interval
# What the power law fit predicts at x, and the range that holds, with
# chance `level`, the mean of k new runs there (k None: the law's own value,
# as if infinitely many): on the log scale the line's value +- t s sqrt(1 / k
# + 1 / n + (ln x - mean_log_x)^2 / sxx), t at n - 2 degrees of freedom; the
# further x is from the points, the wider. A triple (predicted, low, high).
def power_interval(fit, x, level=0.95, k=None):
    at = math.log(fit["a"]) - fit["alpha"] * math.log(x)
    spread = (1 / k if k else 0.0) + 1 / fit["n"] + (math.log(x) - fit["mean_log_x"]) ** 2 / fit["sxx"]
    half = t_quantile((1 + level) / 2, fit["n"] - 2) * fit["s"] * math.sqrt(spread)
    return math.exp(at), math.exp(at - half), math.exp(at + half)
# @end
