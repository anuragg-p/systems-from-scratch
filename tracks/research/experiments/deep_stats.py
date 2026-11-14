"""Twenty layers that learn nothing: looking at the activations and gradients of every layer.

A network of 20 linear layers, 64 units wide, relu between them, every
layer started the way nn.Linear starts it. On one batch of MNIST the
script measures, layer by layer, how much each layer's output differs from
one digit to the next (the spread of the activations over the batch) and
how big the gradient arriving at each layer is; then it trains the network
for one pass, over a few seeds, and the loss does not move from log(10).
The same for tanh. Both pictures are drawn, one line per activation.

    python3 -m experiments.deep_stats        (needs MNIST: python3 -m data.fetch mnist)
"""

import math

import engine as torch                      # the engine; "import torch" runs this on PyTorch
import lab
from data import mnist
from experiments.deep import layer_stats, network
from experiments.loop import train

CONFIG = dict(depth=20, width=64, acts=["relu", "tanh"], lr=0.01, momentum=0.9, batch=128, seeds=3)
SHOWN = (1, 2, 3, 5, 10, 15)


def main():
    cfg = lab.config(CONFIG)
    x, y = mnist.load("train")
    xb, yb = torch.from_numpy(x[:cfg.batch]), torch.from_numpy(y[:cfg.batch])
    spread, grads = [], []
    for i, act in enumerate(cfg.acts):
        torch.manual_seed(0)
        stats = layer_stats(torch, network(torch, cfg.depth, cfg.width, act), xb, yb)
        print(f"{act}, {cfg.depth} layers as nn.Linear starts them, one batch:")
        print(f"  layer  spread over the batch   gradient arriving   {'dead' if act == 'relu' else 'saturated'}")
        for k, s in enumerate(stats, 1):
            if k in SHOWN or k == len(stats):
                print(f"  {k:5d}  {s['spread']:21.2e}   {s['grad']:17.2e}   {s['stuck']:8.0%}")
        layers = list(range(1, len(stats) + 1))
        spread.append(lab.Line(act, layers, [s["spread"] for s in stats], i))
        grads.append(lab.Line(act, layers, [s["grad"] for s in stats], i))
        finals = []
        for seed in range(cfg.seeds):
            run = lab.Run(cfg, seed, label=act)
            torch.manual_seed(seed)
            model = network(torch, cfg.depth, cfg.width, act)
            opt = torch.optim.SGD(model.parameters(), lr=cfg.lr, momentum=cfg.momentum)
            losses = train(torch, model, opt, x, y, cfg.batch, 1, run.rng, run)
            finals.append(run.finish(train_loss=sum(losses[-50:]) / 50)["train_loss"])
        print(f"  one pass of SGD (lr {cfg.lr}, momentum {cfg.momentum}): loss of the last 50 steps "
              f"{lab.spread(finals, 4)}; log(10) = {math.log(10):.4f}")
    out = f"{cfg.out}/{cfg.name}"
    a = lab.lines(f"{out}/spread.svg", spread, xlabel="layer", ylabel="spread over the batch", logy=True)
    b = lab.lines(f"{out}/grad.svg", grads, xlabel="layer", ylabel="gradient arriving (sd)", logy=True)
    print(f"pictures in {a} and {b}")


if __name__ == "__main__":
    main()
