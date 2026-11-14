"""More training data for free: new images made from the ones there are.

A digit moved a pixel or two is still the same digit, so every epoch can
show the network each image shifted by a new random amount: what it sees
is never quite the same twice, and fitting the exact pixels of 2000 images
no longer pays.
"""

import numpy as np


# @build 05.03 shift
# Each image of x (rows of 784 pixels, 28 by 28) moved by its own random
# whole number of pixels, from -k to k, across and down, drawn from rng;
# what moves in from the edge is `fill` (the value of a blank pixel). Pad
# every image by k on all sides, then cut a 28 by 28 window out of each at
# its own offset, all at once by indexing.
def shift(x, k, rng, fill):
    n = len(x)
    padded = np.pad(x.reshape(n, 28, 28), ((0, 0), (k, k), (k, k)), constant_values=fill)
    down = rng.integers(0, 2 * k + 1, n)
    across = rng.integers(0, 2 * k + 1, n)
    rows = down[:, None] + np.arange(28)
    cols = across[:, None] + np.arange(28)
    out = padded[np.arange(n)[:, None, None], rows[:, :, None], cols[:, None, :]]
    return out.reshape(n, 784)
# @end
