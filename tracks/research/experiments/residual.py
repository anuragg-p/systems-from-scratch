"""Residual connections: a path the gradient keeps.

He et al. (2015), figures 1 and 4: a deeper plain network ends with a
higher training error than a shallower one (not overfitting: the training
error itself), and with shortcut connections the deeper one trains at
least as well. Here, on MNIST: networks of 8 and of 32 linear layers, 64
wide, He's start, batch norm after each hidden layer, one pass of SGD with
momentum, a few seeds. "Plain" stacks the layers; "residual" groups them
in pairs, each pair a block whose output is added to its input:
relu(x + bn(linear(relu(bn(linear(x)))))). For each, the training cost
at the end, and at the start how big the gradient is that reaches the
first layer.

    python3 -m experiments.residual          (needs MNIST: python3 -m data.fetch mnist)
"""

import engine as torch                      # the engine; "import torch" runs this on PyTorch
import lab
from data import mnist
from experiments.loop import evaluate, train

nn, F = torch.nn, torch.nn.functional
CONFIG = dict(depths=[8, 32], width=64, lr=0.01, momentum=0.9, batch=128, seeds=3)


def he(layer):
    nn.init.kaiming_normal_(layer.weight, nonlinearity="relu")
    nn.init.zeros_(layer.bias)
    return layer


def plain(depth, width):
    """depth linear layers, batch norm and relu after each hidden one."""
    layers = [he(nn.Linear(784, width)), nn.ReLU()]
    for _ in range(depth - 2):
        layers += [he(nn.Linear(width, width)), nn.BatchNorm1d(width), nn.ReLU()]
    return nn.Sequential(*layers, nn.Linear(width, 10))


# @build 04.05 Block
# Two linear layers with batch norm, as a branch beside a shortcut: the
# input goes through linear, batch norm, relu, linear, batch norm, and is
# then added back to what went in, and the sum goes through a relu. The
# gradient of the output reaches the input along the shortcut unchanged,
# whatever the branch does to it.
class Block(nn.Module):
    def __init__(self, width):
        super().__init__()
        self.a, self.bn_a = he(nn.Linear(width, width)), nn.BatchNorm1d(width)
        self.b, self.bn_b = he(nn.Linear(width, width)), nn.BatchNorm1d(width)

    def forward(self, x):
        return (x + self.bn_b(self.b(self.bn_a(self.a(x)).relu()))).relu()
# @end


def residual(depth, width):
    """The same number of linear layers, the hidden ones in residual blocks of two."""
    blocks = [Block(width) for _ in range((depth - 2) // 2)]
    return nn.Sequential(he(nn.Linear(784, width)), nn.ReLU(), *blocks, nn.Linear(width, 10))


def first_layer_grad(model, x, y):
    """The size (standard deviation) of the gradient of the first layer's weights, at the start."""
    F.cross_entropy(model(x), y).backward()
    g = model[0].weight.grad.std().item()
    model.zero_grad()
    return g


def main():
    cfg = lab.config(CONFIG)
    x, y = mnist.load("train")
    xb, yb = torch.from_numpy(x[:cfg.batch]), torch.from_numpy(y[:cfg.batch])
    print(f"{'network':16s} {'gradient at layer 1':20s} training cost after one pass")
    results = {}
    for kind, make in (("plain", plain), ("residual", residual)):
        for depth in cfg.depths:
            costs, grads = [], []
            for seed in range(cfg.seeds):
                run = lab.Run(cfg, seed, label=f"{kind}{depth}")
                torch.manual_seed(seed)
                model = make(depth, cfg.width)
                grads.append(first_layer_grad(model, xb, yb))
                opt = torch.optim.SGD(model.parameters(), lr=cfg.lr, momentum=cfg.momentum)
                train(torch, model, opt, x, y, cfg.batch, 1, run.rng, run)
                costs.append(evaluate(torch, model, x, y)[0])
                run.finish(train_cost=costs[-1], first_layer_grad=grads[-1])
            results[kind, depth] = costs
            print(f"{kind + ' ' + str(depth):16s} {lab.mean(grads):<20.2e} {lab.spread(costs)}")
    for kind in ("plain", "residual"):
        shallow, deep = (results[kind, d] for d in cfg.depths)
        print(f"{kind}: {cfg.depths[1]} layers against {cfg.depths[0]}: cost {lab.mean(deep):.4f} against "
              f"{lab.mean(shallow):.4f}, t = {lab.welch_t(deep, shallow):+.1f} (negative: the deeper is lower)")


if __name__ == "__main__":
    main()
