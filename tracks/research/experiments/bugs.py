"""Five bugs that do not crash, and the checklist that catches each.

One training script for MNIST (two hidden layers with batch norm, Adam),
and five copies of it, each with one bug of the kind that costs a week:
the script runs, prints a loss and an accuracy, and is wrong. For the
correct script and each bug, over a few seeds, the script runs the five
checks of lab/checks.py and prints which fired. The correct script must
pass all five; each bug must be caught.

    python3 -m experiments.bugs              (needs MNIST: python3 -m data.fetch mnist)
"""

import numpy as np

import engine as torch                      # the engine; "import torch" runs this on PyTorch
import lab
from data import batches, mnist
from lab import checks

nn, F = torch.nn, torch.nn.functional
CONFIG = dict(hidden=128, lr=1e-3, batch=128, held_out=5000, steps=300, one_batch=64, one_batch_steps=300,
              seeds=3)
BUGS = {
    "none": "the script as it should be",
    "no zero_grad": "the gradients are never set back to zero, so each step adds to the last",
    "softmax twice": "the scores go through softmax before cross_entropy, which takes a softmax of its own",
    "labels shuffled": "the images were put in a new order and their labels were not",
    "pixels 0-255": "the pixels are not scaled: 0 to 255 instead of standardised",
    "eval in train mode": "held-out digits are scored without model.eval(): batch norm uses each batch's own mean",
}
CHECKS = ["starting loss", "one batch", "fresh gradients", "beats chance", "same answers"]


def network(hidden):
    return nn.Sequential(nn.Linear(784, hidden), nn.BatchNorm1d(hidden), nn.ReLU(),
                         nn.Linear(hidden, hidden), nn.BatchNorm1d(hidden), nn.ReLU(), nn.Linear(hidden, 10))


# @build 04.06 gradients
# The training step's gradient, with the bug or without: zero_grad (unless
# the bug is "no zero_grad"), the loss of the batch (cross_entropy of the
# scores, or of their softmax under "softmax twice"), backward. Returns
# the loss as a float.
def gradients(bug, model, opt, xb, yb):
    if bug != "no zero_grad":
        opt.zero_grad()
    scores = model(xb)
    if bug == "softmax twice":
        scores = F.softmax(scores, 1)
    loss = F.cross_entropy(scores, yb)
    loss.backward()
    return loss.item()
# @end


# @build 04.06 predict
# The predicted class of every row of x, scored in chunks of 1000 rows in
# the order given, in eval mode (unless the bug is "eval in train mode")
# and without a graph.
def predict(bug, model, x):
    if bug != "eval in train mode":
        model.eval()
    out = []
    with torch.no_grad():
        for start in range(0, len(x), 1000):
            out.append(model(torch.from_numpy(x[start:start + 1000])).argmax(1).numpy())
    model.train()
    return np.concatenate(out)
# @end


def data(bug, seed, held_out):
    """Training images and labels, and the last held_out of MNIST's training set kept apart, as the
    buggy script would load them: under "pixels 0-255" both unscaled; under "labels shuffled" the
    training images in a new order, their labels not."""
    x, y = mnist.load("train", None, bug != "pixels 0-255")
    if bug == "pixels 0-255":
        x = x * 255
    x, y, xh, yh = x[:-held_out], y[:-held_out], x[-held_out:], y[-held_out:]
    if bug == "labels shuffled":
        x = x[np.random.default_rng(1000 + seed).permutation(len(x))]
    return x, y, xh, yh


def in_order(bug, model, x, order):
    """Predictions for x scored in the given order of its rows, put back in x's own order."""
    out = np.empty(len(x), dtype=np.int64)
    out[order] = predict(bug, model, x[order])
    return out


def run_checks(cfg, bug, seed):
    """The five checks, as (passed, what it saw), for one bug and seed."""
    x, y, xh, yh = data(bug, seed, cfg.held_out)
    results = []
    torch.manual_seed(seed)
    model = network(cfg.hidden)
    with torch.no_grad():
        model.eval()
        start = F.cross_entropy(model(torch.from_numpy(x[:1000])), torch.from_numpy(y[:1000])).item()
        model.train()
    results.append(checks.starting_loss(start, 10))
    torch.manual_seed(seed)
    model = network(cfg.hidden)
    opt = torch.optim.Adam(model.parameters(), lr=cfg.lr)
    xb, yb = torch.from_numpy(x[:cfg.one_batch]), torch.from_numpy(y[:cfg.one_batch])
    losses = []
    for _ in range(cfg.one_batch_steps):
        losses.append(gradients(bug, model, opt, xb, yb))
        opt.step()
    results.append(checks.learns_one_batch(losses))
    torch.manual_seed(seed)
    model = network(cfg.hidden)
    opt = torch.optim.Adam(model.parameters(), lr=cfg.lr)
    gradients(bug, model, opt, xb, yb)
    first = [p.grad.numpy().copy() for p in model.parameters()]
    gradients(bug, model, opt, xb, yb)
    second = [p.grad.numpy().copy() for p in model.parameters()]
    results.append(checks.gradients_fresh(first, second))
    torch.manual_seed(seed)
    model = network(cfg.hidden)
    opt = torch.optim.Adam(model.parameters(), lr=cfg.lr)
    rng, step = np.random.default_rng(seed), 0
    while step < cfg.steps:
        for idx in batches(len(x), cfg.batch, rng):
            gradients(bug, model, opt, torch.from_numpy(x[idx]), torch.from_numpy(y[idx]))
            opt.step()
            step += 1
            if step == cfg.steps:
                break
    results.append(checks.beats_chance(float(np.mean(predict(bug, model, xh) == yh)), 10))
    shuffled = in_order(bug, model, xh, np.random.default_rng(seed).permutation(len(xh)))
    by_digit = in_order(bug, model, xh, np.argsort(yh, kind="stable"))
    results.append(checks.same_answers(shuffled, by_digit))
    return results


def main():
    cfg = lab.config(CONFIG)
    print(f"{'':20s}" + "".join(f"{c:>17s}" for c in CHECKS))
    for bug, what in BUGS.items():
        fired = [0] * len(CHECKS)
        seen = None
        for seed in range(cfg.seeds):
            results = run_checks(cfg, bug, seed)
            for k, (ok, _) in enumerate(results):
                fired[k] += not ok
            seen = seen or [text for ok, text in results if not ok]
        print(f"{bug:20s}" + "".join(f"{('FAILS ' + str(n) + '/' + str(cfg.seeds)) if n else 'ok':>17s}"
                                     for n in fired))
        print(f"{'':20s}  {what}" + (f"; {seen[0]}" if seen else ""))


if __name__ == "__main__":
    main()
