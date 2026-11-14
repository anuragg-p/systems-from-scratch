"""Points in the plane in two groups, made here from a seed: the first data a network learns.

Two interleaved half circles (two "moons"): one group arches up, the other,
shifted right and down, arches below it and into its gap. No straight line
separates them, so a model needs a bend, which is what the hidden layers of
a network give it.
"""

import numpy as np


# @build 01.04 two_groups
# n points (n // 2 in group 0, the rest in group 1), drawn from rng (a numpy
# Generator). Group 0 lies on the upper half of the unit circle centred at
# (0, 0); group 1 on the lower half of the one centred at (1, 0.5), each
# point at a uniformly random angle, then moved by normal noise of standard
# deviation `noise` in each direction. Returns the points, float32 of shape
# (n, 2), and their groups, int64 0 or 1, shuffled together.
def two_groups(n, noise, rng):
    n0 = n // 2
    a0 = rng.uniform(0, np.pi, n0)
    a1 = rng.uniform(0, np.pi, n - n0)
    upper = np.stack([np.cos(a0), np.sin(a0)], axis=1)
    lower = np.stack([1 - np.cos(a1), 0.5 - np.sin(a1)], axis=1)
    x = np.concatenate([upper, lower]) + rng.normal(0, noise, (n, 2))
    y = np.concatenate([np.zeros(n0), np.ones(n - n0)]).astype(np.int64)
    order = rng.permutation(n)
    return x[order].astype(np.float32), y[order]
# @end
