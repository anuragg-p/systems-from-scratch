"""One import: the same network on the engine and on PyTorch, side by side.

The convolutional network of models/convnet.py, built with the engine and
again with PyTorch by the same function, the engine's starting weights
copied into PyTorch's, both fed the same random images and labels (what
the pictures show does not matter to a check of the arithmetic). Two
parts:

1. In float64, one training step on each (forward, cross-entropy,
   backward, SGD with momentum), for a few seeds: the loss, every
   parameter's gradient, and every parameter after the step, compared.
2. In float32, as training runs, `steps` steps on each from the same start
   on the same batches: every step's loss on each, how long a step takes,
   and what one pass over CIFAR-10's 50,000 training images would take.

    python3 -m experiments.switch                 (nothing to download)
    python3 -m experiments.switch device=auto     PyTorch on the GPU too, when there is one
"""

import numpy as np

import engine
import torch

import lab
from models.convnet import convnet

CONFIG = dict(width=32, batch=128, steps=10, lr=0.01, momentum=0.9, seeds=3, device="cpu")


# @build 06.02 copy_weights
# Make PyTorch's network compute what the engine's computes: state_dict
# gives every weight of the engine's network by name, as an engine tensor;
# turn each one's numbers into a PyTorch tensor (torch.from_numpy of a copy)
# and load_state_dict puts them in place. The names match because one
# function built both networks. Returns PyTorch's network.
def copy_weights(ours, theirs):
    theirs.load_state_dict({name: torch.from_numpy(t.numpy().copy()) for name, t in ours.state_dict().items()})
    return theirs
# @end


# @build 06.02 step
# One training step of model on the images x and labels y, with lib (the
# engine or PyTorch: the same lines run on either): the cross-entropy of
# the model's scores, zero_grad, backward and the optimiser's step. Returns
# the loss as a number; the gradients stay in each parameter's .grad.
def step(lib, model, opt, x, y):
    loss = lib.nn.functional.cross_entropy(model(x), y)
    opt.zero_grad()
    loss.backward()
    opt.step()
    return loss.item()
# @end


def largest(ours, theirs):
    """The largest difference between our arrays and PyTorch's, relative to PyTorch's: |a - b| / (1 + |b|)."""
    return max(float(np.max(np.abs(a - b) / (1 + np.abs(b)))) for a, b in zip(ours, theirs))


def arrays(tensors):
    return [t.detach().cpu().numpy() if isinstance(t, torch.Tensor) else t.detach().numpy() for t in tensors]


def main():
    cfg = lab.config(CONFIG)
    dev = lab.device(torch, cfg.device)
    cpu = torch.device("cpu")
    print(f"1. float64, one training step on {cfg.batch} random images, {cfg.seeds} seeds: the largest difference, "
          f"engine against PyTorch (relative)")
    names, grads, after, losses = None, {}, {}, []
    for seed in range(cfg.seeds):
        run = lab.Run(cfg, seed, label="float64")
        engine.manual_seed(seed)
        ours = convnet(engine, cfg.width).double()
        torch.manual_seed(seed)                 # PyTorch's own generator draws other weights: copy_weights replaces them
        theirs = copy_weights(ours, convnet(torch, cfg.width).double())
        x, y = run.rng.standard_normal((cfg.batch, 3, 32, 32)), run.rng.integers(0, 10, cfg.batch)
        loss = []
        for lib, model in ((engine, ours), (torch, theirs)):
            opt = lib.optim.SGD(model.parameters(), lr=cfg.lr, momentum=cfg.momentum)
            loss.append(step(lib, model, opt, lib.from_numpy(x), lib.from_numpy(y)))
        names = [name for name, _ in ours.named_parameters()]
        for name, p, q in zip(names, ours.parameters(), theirs.parameters()):
            grads.setdefault(name, []).append(largest(arrays([p.grad]), arrays([q.grad])))
            after.setdefault(name, []).append(largest(arrays([p]), arrays([q])))
        losses.append(abs(loss[0] - loss[1]) / (1 + abs(loss[1])))
        run.finish(loss_engine=loss[0], loss_pytorch=loss[1], gradient=max(g[-1] for g in grads.values()),
                   weights=max(a[-1] for a in after.values()))
    print(f"   the loss: {max(losses):.1e}")
    print(f"   {'parameter':10s} {'shape':16s} {'gradient':>10s} {'after the step':>15s}")
    shapes = {name: tuple(p.shape) for name, p in ours.named_parameters()}
    for name in names:
        print(f"   {name:10s} {str(shapes[name]):16s} {max(grads[name]):10.1e} {max(after[name]):15.1e}")

    print(f"2. float32, {cfg.steps} training steps from the same start on the same batches of {cfg.batch}:")
    run = lab.Run(cfg, 0, label="float32")
    engine.manual_seed(0)
    ours = convnet(engine, cfg.width)
    torch.manual_seed(0)
    sides =[("engine", engine, ours, cpu), ("PyTorch", torch, copy_weights(ours, convnet(torch, cfg.width)), cpu)]
    if dev.type != "cpu":
        sides.append((f"PyTorch on {dev.type}", torch, copy_weights(ours, convnet(torch, cfg.width)).to(dev), dev))
    data = [(run.rng.standard_normal((cfg.batch, 3, 32, 32)).astype(np.float32), run.rng.integers(0, 10, cfg.batch))
            for _ in range(cfg.steps + 1)]
    curves, seconds = {}, {}
    for name, lib, model, where in sides:
        opt = lib.optim.SGD(model.parameters(), lr=cfg.lr, momentum=cfg.momentum)
        curves[name] = []
        for i, (x, y) in enumerate(data):
            if i == 1:                          # the first step sets things up: time the rest
                start = lab.clock(torch, where)
            if lib is engine:
                x, y = engine.from_numpy(x), engine.from_numpy(y)
            else:
                x, y = torch.from_numpy(x).to(where), torch.from_numpy(y).to(where)
            curves[name].append(step(lib, model, opt, x, y))
        seconds[name] = (lab.clock(torch, where) - start) / cfg.steps
    for i in range(cfg.steps + 1):
        run.log(step=i, **{name.replace(" ", "_"): curves[name][i] for name in curves})
    print(f"   {'step':>4s}  " + "  ".join(f"{name:>14s}" for name in curves))
    for i in range(cfg.steps + 1):
        print(f"   {i:4d}  " + "  ".join(f"{curves[name][i]:14.7f}" for name in curves))
    gap = max(abs(a - b) for a, b in zip(curves["engine"], curves["PyTorch"]))
    run.finish(largest_loss_difference=gap)
    print(f"   largest difference between the engine's losses and PyTorch's: {gap:.1e}")
    print(f"   a step takes: " + ", ".join(f"{name} {1000 * s:.1f} ms" for name, s in seconds.items()))
    for name, s in seconds.items():
        if name != "engine":
            print(f"   {name} is {seconds['engine'] / s:.1f} times as fast as the engine")
    print(f"   one pass over 50,000 images would take: "
          + ", ".join(f"{name} {50000 / cfg.batch * s:.0f} s" for name, s in seconds.items()))


if __name__ == "__main__":
    main()
