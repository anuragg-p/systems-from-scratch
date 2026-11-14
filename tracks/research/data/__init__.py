"""The data the experiments train on: points made here (points.py), MNIST read from the cache
(mnist.py, fetched by fetch.py), and how a training set is cut into batches."""

import numpy as np


# @build 03.01 batches
# The positions 0 .. n-1 in a random order drawn from rng (a numpy
# Generator), cut into consecutive batches of batch_size; the last one may
# be smaller. A new order every time it is called: one call is one pass over
# the data, an epoch.
def batches(n, batch_size, rng):
    order = rng.permutation(n)
    for start in range(0, n, batch_size):
        yield order[start:start + batch_size]
# @end
