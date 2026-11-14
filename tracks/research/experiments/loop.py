"""The training loop the MNIST experiments share, and how they measure a model.

The script that calls these passes its engine in as the first argument
(torch), so the loop runs on whichever engine that script named in its one
import line. Nothing here imports an engine itself.
"""

import math

from data import batches


# @build 03.01 train
# Minibatch training for `epochs` passes over (x, y), numpy arrays: each
# pass in a new order from rng, cut into batches of batch_size; for each
# batch, cross_entropy of the model's scores, zero_grad, backward, step.
# Every `every` steps (and the first), the batch's loss goes to run.log with
# the step number. A loss that is not a finite number means the run has
# diverged: log it and stop. Returns the losses of every step.
# @from 03.05
def train(torch, model, opt, x, y, batch_size, epochs, rng, run=None, every=10, scheduler=None):
# @else
# def train(torch, model, opt, x, y, batch_size, epochs, rng, run=None, every=10):
# @end
    F = torch.nn.functional
    losses = []
    for _ in range(epochs):
        for idx in batches(len(x), batch_size, rng):
            loss = F.cross_entropy(model(torch.from_numpy(x[idx])), torch.from_numpy(y[idx]))
            opt.zero_grad()
            loss.backward()
            opt.step()
            # @from 03.05
            if scheduler is not None:
                scheduler.step()
            # @end
            value = loss.item()
            losses.append(value)
            step = len(losses) - 1
            if run is not None and (step % every == 0 or not math.isfinite(value)):
                run.log(step=step, loss=value)
            if not math.isfinite(value):
                return losses
    return losses
# @end


# @build 03.01 evaluate
# The mean cross-entropy and the accuracy of model on (x, y), numpy arrays,
# in eval mode and without a graph, in chunks of 10000 rows. The model is
# put back in training mode afterwards.
def evaluate(torch, model, x, y):
    F = torch.nn.functional
    model.eval()
    total, right = 0.0, 0
    with torch.no_grad():
        for start in range(0, len(x), 10000):
            xb, yb = torch.from_numpy(x[start:start + 10000]), torch.from_numpy(y[start:start + 10000])
            scores = model(xb)
            total += F.cross_entropy(scores, yb, reduction="sum").item()
            right += (scores.argmax(1) == yb).float().sum().item()
    model.train()
    return total / len(x), right / len(x)
# @end


def mlp(torch, sizes):
    """Linear layers of the given sizes with a relu between each pair: mlp(torch, [784, 100, 10])."""
    nn = torch.nn
    layers = []
    for i, (n_in, n_out) in enumerate(zip(sizes[:-1], sizes[1:])):
        layers.append(nn.Linear(n_in, n_out))
        if i < len(sizes) - 2:
            layers.append(nn.ReLU())
    return nn.Sequential(*layers)
