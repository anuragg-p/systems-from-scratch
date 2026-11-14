"""The two groups of points again, with the network as matrices: the same training, much faster.

The network of 01.04 is three layers; written with tensors, each layer is
one matrix multiply and one bias for the whole batch: h = relu(x @ W + b).
The loss is the same hinge loss, now one line of tensor arithmetic, and the
update moves every weight inside no_grad(). With the time this saves, the
script trains a wider network on four times the points for many more
steps, over a few seeds, and reports the time per step.

    python3 -m experiments.groups_tensors
"""

import time

import numpy as np

import engine as torch                      # the engine; "import torch" runs this on PyTorch
import lab
from data.points import two_groups

CONFIG = dict(n_train=200, n_test=1000, noise=0.1, hidden=16, steps=1000, lr=0.5, seeds=3)


def init(rng, sizes):
    """Weights uniform in [-1, 1] / sqrt(inputs), biases 0: a list of (W, b) tensors that need gradients."""
    layers = []
    for n_in, n_out in zip(sizes[:-1], sizes[1:]):
        w = rng.uniform(-1, 1, (n_in, n_out)) / np.sqrt(n_in)
        layers.append((torch.tensor(w.astype(np.float32), requires_grad=True),
                       torch.zeros(n_out, requires_grad=True)))
    return layers


# @build 02.03 forward
# The scores of a batch x of shape (n, 2): through each layer x @ W + b, a
# relu after every layer but the last. Returns shape (n,): the last layer
# has one output, so its column is taken out with [:, 0].
def forward(layers, x):
    for i, (w, b) in enumerate(layers):
        x = x @ w + b
        if i < len(layers) - 1:
            x = x.relu()
    return x[:, 0]
# @end


# @build 02.03 hinge
# The mean hinge loss of the scores against labels 0 and 1: t = 2y - 1 is
# -1 or +1, and the loss is relu(1 - t * score), averaged. Also the fraction
# of scores on the right side of 0.
def hinge(scores, y):
    t = torch.from_numpy(2 * y.astype(np.float32) - 1)
    loss = (1 - t * scores).relu().mean()
    accuracy = ((scores > 0) == (t > 0)).float().mean().item()
    return loss, accuracy
# @end


# @build 02.03 sgd_step
# Move every weight by -lr times its gradient, in place and inside no_grad()
# (an update is not part of the graph), then forget the gradient.
def sgd_step(layers, lr):
    with torch.no_grad():
        for w, b in layers:
            for p in (w, b):
                p -= lr * p.grad
                p.grad = None
# @end


def main():
    cfg = lab.config(CONFIG)
    finals, curves = [], []
    for seed in range(cfg.seeds):
        run = lab.Run(cfg, seed)
        x, y = two_groups(cfg.n_train, cfg.noise, run.rng)
        xt, yt = two_groups(cfg.n_test, cfg.noise, run.rng)
        layers = init(run.rng, [2, cfg.hidden, cfg.hidden, 1])
        xb = torch.from_numpy(x)
        start = time.perf_counter()
        for step in range(cfg.steps):
            loss, accuracy = hinge(forward(layers, xb), y)
            if step % 10 == 0:
                run.log(step=step, loss=loss.item(), accuracy=accuracy)
            loss.backward()
            sgd_step(layers, cfg.lr)
        seconds = time.perf_counter() - start
        with torch.no_grad():
            loss, accuracy = hinge(forward(layers, xb), y)
            _, test_accuracy = hinge(forward(layers, torch.from_numpy(xt)), yt)
        s = run.finish(loss=loss.item(), accuracy=accuracy, test_accuracy=test_accuracy)
        finals.append(s)
        print(f"seed {seed}: loss {s['loss']:.4f}, accuracy {s['accuracy']:.3f}, on fresh points "
              f"{s['test_accuracy']:.3f}, {seconds / cfg.steps * 1e3:.2f} ms a step")
        curves.append(lab.Line("hinge loss, one line per seed", [r["step"] for r in run.rows],
                               [r["loss"] for r in run.rows], 0, 0.7))
    print("training accuracy       ", lab.spread([s["accuracy"] for s in finals]))
    print("accuracy on fresh points", lab.spread([s["test_accuracy"] for s in finals]))
    print(f"curves in {lab.lines(f'{cfg.out}/{cfg.name}/loss.svg', curves, xlabel='step', ylabel='hinge loss')}")


if __name__ == "__main__":
    main()
