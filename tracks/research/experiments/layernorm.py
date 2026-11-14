"""Layer normalisation, and what the batch had to do with batch norm.

Batch norm normalises each feature over the batch, so in training an
example's output depends on which other examples share its batch. Ba,
Kiros and Hinton (2016) normalise each example over its own features
instead. The script shows the difference four ways:

1. one digit, two different batchmates: batch norm (training mode) gives
   it two different outputs, layer norm the same one;
2. a batch of one: batch norm refuses it, layer norm does not mind;
3. a batch of two: batch norm turns every feature into exactly -1 or +1;
4. training the sigmoid network of 04.03 on batches of 2, and of 60, with
   each, over a few seeds: test accuracy at the end.

    python3 -m experiments.layernorm         (needs MNIST: python3 -m data.fetch mnist)
"""

import numpy as np

import engine as torch                      # the engine; "import torch" runs this on PyTorch
import lab
from data import batches, mnist
from experiments.loop import evaluate

nn, F = torch.nn, torch.nn.functional
CONFIG = dict(sizes=[784, 100, 100, 100, 10], steps=3000, settings=[[2, 0.02], [60, 0.5]], seeds=3)
NORMS = {"batch": lambda n: nn.BatchNorm1d(n), "layer": lambda n: nn.LayerNorm(n)}


# @build 04.04 sigmoid_net
# The sigmoid network of 04.03 with the named normalisation ("batch" or
# "layer") between each hidden linear layer and its sigmoid.
def sigmoid_net(sizes, norm):
    layers = []
    for i, (n_in, n_out) in enumerate(zip(sizes[:-1], sizes[1:])):
        layers.append(nn.Linear(n_in, n_out))
        if i < len(sizes) - 2:
            layers += [NORMS[norm](n_out), nn.Sigmoid()]
    return nn.Sequential(*layers)
# @end


def train_steps(model, x, y, batch, lr, steps, rng):
    opt = torch.optim.SGD(model.parameters(), lr=lr)
    step = 0
    while step < steps:
        for idx in batches(len(x), batch, rng):
            loss = F.cross_entropy(model(torch.from_numpy(x[idx])), torch.from_numpy(y[idx]))
            opt.zero_grad()
            loss.backward()
            opt.step()
            step += 1
            if step == steps:
                return


def main():
    cfg = lab.config(CONFIG)
    x, y = mnist.load("train")
    xt, yt = mnist.load("test")
    torch.manual_seed(0)
    norms = {name: make(4) for name, make in NORMS.items()}
    one = x[:1, :4]
    for name, norm in norms.items():
        a = norm(torch.from_numpy(np.concatenate([one, x[1:4, :4] + 1.0]))).detach().numpy()[0]
        b = norm(torch.from_numpy(np.concatenate([one, x[4:7, :4] - 1.0]))).detach().numpy()[0]
        print(f"1. {name} norm, the same digit with two sets of batchmates: largest difference in its output "
              f"{np.abs(a - b).max():.3f}")
    for name, norm in norms.items():
        try:
            norm(torch.from_numpy(x[:1, :4]))
            print(f"2. {name} norm, a batch of one: fine")
        except ValueError as e:
            print(f"2. {name} norm, a batch of one: {e}")
    first = nn.Linear(784, 4)
    out = norms["batch"](first(torch.from_numpy(x[100:102]))).detach().numpy()
    rows = "; ".join(" ".join(f"{v:+.3f}" for v in row) for row in out)
    print(f"3. batch norm on a batch of two, the four outputs of a linear layer: {rows}")
    for batch, lr in cfg.settings:
        for name in NORMS:
            accuracies = []
            for seed in range(cfg.seeds):
                run = lab.Run(cfg, seed, label=f"{name}-batch{batch}")
                torch.manual_seed(seed)
                model = sigmoid_net(cfg.sizes, name)
                train_steps(model, x, y, batch, lr, cfg.steps, run.rng)
                accuracies.append(evaluate(torch, model, xt, yt)[1])
                run.finish(test_accuracy=accuracies[-1])
            print(f"4. batches of {batch:2d}, lr {lr:<4g}, {cfg.steps} steps, {name} norm: test accuracy "
                  f"{lab.spread(accuracies)}")


if __name__ == "__main__":
    main()
