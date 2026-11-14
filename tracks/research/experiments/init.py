"""Initialisation: keeping the signal the same size, layer after layer.

He et al. (2015), figure 3: a 30-layer relu network started with Glorot
and Bengio's weights (variance 2 / (fan_in + fan_out)) does not learn at
all; started with He's (variance 2 / fan_in), it does. Here: 30 linear
layers, 64 wide, relu, on MNIST, started three ways (as nn.Linear starts
them, Glorot's, He's), biases at 0 for the last two. For each: the spread
of every layer's output over one batch, and the loss after one pass of SGD
with momentum, over a few seeds.

    python3 -m experiments.init              (needs MNIST: python3 -m data.fetch mnist)
"""

import math

import engine as torch                      # the engine; "import torch" runs this on PyTorch
import lab
from data import mnist
from experiments.deep import layer_stats, network
from experiments.loop import train

nn = torch.nn
CONFIG = dict(depth=30, width=64, inits=["default", "glorot", "he"], lr=0.01, momentum=0.9, batch=128,
              seeds=3)


# @build 04.02 initialise
# Start every linear layer of model the named way: "default" leaves
# nn.Linear's own start; "glorot" is xavier_normal_, "he" is
# kaiming_normal_ with the relu gain; both set the biases to 0.
def initialise(model, how):
    for m in model:
        if not isinstance(m, nn.Linear) or how == "default":
            continue
        if how == "glorot":
            nn.init.xavier_normal_(m.weight)
        elif how == "he":
            nn.init.kaiming_normal_(m.weight, nonlinearity="relu")
        else:
            raise ValueError(f"no initialisation {how!r} (have: default, glorot, he)")
        nn.init.zeros_(m.bias)
    return model
# @end


def main():
    cfg = lab.config(CONFIG)
    x, y = mnist.load("train")
    xb, yb = torch.from_numpy(x[:cfg.batch]), torch.from_numpy(y[:cfg.batch])
    lines = []
    for i, how in enumerate(cfg.inits):
        torch.manual_seed(0)
        stats = layer_stats(torch, initialise(network(torch, cfg.depth, cfg.width), how), xb, yb)
        finals = []
        for seed in range(cfg.seeds):
            run = lab.Run(cfg, seed, label=how)
            torch.manual_seed(seed)
            model = initialise(network(torch, cfg.depth, cfg.width), how)
            opt = torch.optim.SGD(model.parameters(), lr=cfg.lr, momentum=cfg.momentum)
            losses = train(torch, model, opt, x, y, cfg.batch, 1, run.rng, run)
            finals.append(run.finish(train_loss=sum(losses[-50:]) / 50)["train_loss"])
        print(f"{how:8s}: spread at layer 1 {stats[0]['spread']:.2e}, at layer {len(stats)} "
              f"{stats[-1]['spread']:.2e}; after one pass, loss {lab.spread(finals)}")
        lines.append(lab.Line(how, range(1, len(stats) + 1), [s["spread"] for s in stats], i))
    print(f"log(10) = {math.log(10):.4f}, the loss of a network that has learned nothing")
    path = lab.lines(f"{cfg.out}/{cfg.name}/spread.svg", lines, xlabel="layer", ylabel="spread over the batch",
                     logy=True)
    print(f"picture in {path}")


if __name__ == "__main__":
    main()
