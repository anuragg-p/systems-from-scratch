"""Modules and a checkpoint: train a network built from nn layers, save it, load it into another.

The network is nn.Sequential(Linear, ReLU, Linear, ReLU, Linear): two
scores per point, one for each group, trained with cross-entropy on the
two groups of 01.04. Its state_dict names every weight the way PyTorch
does. The script saves it as safetensors, prints what the file says it
holds, loads it into a second network that started from other weights,
and checks that the two now give the same scores.

    python3 -m experiments.checkpoint
"""

import os

import numpy as np

import engine as torch                      # the engine; "import torch" runs this on PyTorch
import lab
from data.points import two_groups
from lab.safetensors import load_file, read_header, save_file

nn, F = torch.nn, torch.nn.functional
CONFIG = dict(n_train=200, noise=0.1, hidden=16, steps=500, lr=0.5, seed=0)


def network(hidden):
    return nn.Sequential(nn.Linear(2, hidden), nn.ReLU(), nn.Linear(hidden, hidden), nn.ReLU(),
                         nn.Linear(hidden, 2))


# @build 02.05 train
# Full-batch gradient descent on cross_entropy for `steps` steps, by hand
# (optimisers come in module 03): forward, loss, zero_grad, backward, then
# every parameter moved by -lr times its gradient inside no_grad. Returns
# the last loss as a float.
def train(model, x, y, steps, lr):
    for _ in range(steps):
        loss = F.cross_entropy(model(x), y)
        model.zero_grad()
        loss.backward()
        with torch.no_grad():
            for p in model.parameters():
                p -= lr * p.grad
    return loss.item()
# @end


def main():
    cfg = lab.config(CONFIG)
    run = lab.Run(cfg, cfg.seed)
    torch.manual_seed(cfg.seed)
    x, y = two_groups(cfg.n_train, cfg.noise, run.rng)
    x, y = torch.from_numpy(x), torch.from_numpy(y)
    model = network(cfg.hidden)
    print(model)
    loss = train(model, x, y, cfg.steps, cfg.lr)
    accuracy = (model(x).argmax(1) == y).float().mean().item()
    print(f"after {cfg.steps} steps: loss {loss:.4f}, accuracy {accuracy:.3f}")
    path = os.path.join(run.dir, "model.safetensors")
    save_file({k: v.numpy() for k, v in model.state_dict().items()}, path, metadata={"steps": cfg.steps})
    header, n = read_header(path)
    print(f"{path}: {os.path.getsize(path)} bytes, a header of {n}:")
    for name, spec in header.items():
        print(f"  {name:10s} {spec}")
    other = network(cfg.hidden)
    scores = model(x).detach().numpy()
    print(f"a new network before loading: scores differ by up to "
          f"{np.abs(other(x).detach().numpy() - scores).max():.3f}")
    other.load_state_dict({k: torch.from_numpy(v) for k, v in load_file(path).items()})
    same = np.array_equal(other(x).detach().numpy(), scores)
    print(f"after loading: the same scores, number for number: {same}")
    run.finish(loss=loss, accuracy=accuracy, same=same)


if __name__ == "__main__":
    main()
