"""Learning-rate schedules as plain functions of the step: what LambdaLR multiplies the rate by.

warmup_cosine(warmup, total) rises in a straight line from almost 0 to 1
over the first `warmup` steps, then falls along half a cosine wave to
`floor` at step `total`. The rise keeps the first steps small, while the
running averages of an optimiser like Adam are still made of a handful of
gradients; the fall lets the last steps settle into the minimum the big
steps were jumping around (Loshchilov and Hutter, 2016, decay the rate
this way).
"""

import math


# @build 03.05 warmup_cosine
# A function of the step number: (step + 1) / warmup while step < warmup;
# after that, with p the fraction of the remaining steps done (capped at 1),
# floor + (1 - floor) * (1 + cos(pi * p)) / 2. warmup may be 0.
def warmup_cosine(warmup, total, floor=0.0):
    def multiplier(step):
        if step < warmup:
            return (step + 1) / warmup
        p = min(1.0, (step - warmup) / max(1, total - warmup))
        return floor + (1 - floor) * 0.5 * (1 + math.cos(math.pi * p))
    return multiplier
# @end
