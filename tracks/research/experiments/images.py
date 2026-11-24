"""Training and scoring image classifiers on PyTorch: the loop 06.03 and 06.04 share.

From 06.02 on a script imports torch itself, and so does this file. The
images stay numpy arrays until they are used: data/ reads them, and the
script turns a whole set into one tensor on the run's device at once
(tensors()), each pass for a training set that is augmented anew, so a GPU
is sent one big copy rather than one per batch. A batch is then picked out
of that tensor by the positions data.batches gives.
"""

import torch
import torch.nn.functional as F

from data import batches


def tensors(dev, *arrays):
    """numpy arrays as tensors on the device dev, each copied there once."""
    return [torch.from_numpy(a).to(dev) for a in arrays]


# @build 06.03 train_epoch
# One pass over the images x and labels y, tensors on one device: in a new
# order from rng (a numpy Generator), in batches of batch_size, each the
# cross-entropy of the model's scores, zero_grad, backward, the optimiser's
# step, and the scheduler's when there is one. Returns the mean loss and
# the fraction right over the pass, counted as it went (so on weights that
# changed during it). The two sums stay tensors on the device until the
# end: .item() makes the CPU wait for the device, once per pass, not once
# per batch.
def train_epoch(model, opt, x, y, batch_size, rng, scheduler=None):
    model.train()
    total = torch.zeros((), device=x.device)
    right = torch.zeros((), device=x.device)
    for idx in batches(len(x), batch_size, rng):
        idx = torch.from_numpy(idx).to(x.device)
        scores = model(x[idx])
        loss = F.cross_entropy(scores, y[idx])
        opt.zero_grad()
        loss.backward()
        opt.step()
        if scheduler is not None:
            scheduler.step()
        total += loss.detach() * len(idx)
        right += (scores.argmax(1) == y[idx]).sum()
    return total.item() / len(x), right.item() / len(x)
# @end


# @build 06.03 evaluate
# The mean cross-entropy and the accuracy of model on (x, y), tensors on
# one device, in eval mode (batch norm uses its running statistics) and
# without a graph, in batches of batch_size. The model is put back in
# training mode afterwards.
def evaluate(model, x, y, batch_size=1000):
    model.eval()
    total = right = 0.0
    with torch.no_grad():
        for start in range(0, len(x), batch_size):
            scores, yb = model(x[start:start + batch_size]), y[start:start + batch_size]
            total += F.cross_entropy(scores, yb, reduction="sum").item()
            right += (scores.argmax(1) == yb).sum().item()
    model.train()
    return total / len(x), right / len(x)
# @end
