"""A convolutional network on CIFAR-10.

Photographs, not digits: 32 by 32 pixels in three colours, ten classes
(airplane, automobile, bird, cat, deer, dog, frog, horse, ship, truck).
On the first n_train training images, a few seeds each, three ways:

1. the obvious thing, the fully connected network: every number of every
   pixel an input, one hidden layer, ten scores;
2. the convolutional network of models/convnet.py;
3. the same convolutional network, trained each pass on a new random crop
   and mirror image of every picture (data/augment.py's crop_flip).

Accuracy on the training images and on the test images at the end, and
the gap between them.

    python3 -m experiments.cifar          (needs CIFAR-10: python3 -m data.fetch cifar10)
"""

import torch
from torch import nn

import lab
from data import cifar
from data.augment import crop_flip
from experiments.images import evaluate, tensors, train_epoch
from models.convnet import convnet

CONFIG = dict(n_train=2000, n_test=2000, epochs=12, batch=64, lr=0.02, fc_lr=0.01, momentum=0.9, hidden=256, width=16,
              seeds=3, device="cpu")
WAYS = ("fully connected", "convolutional", "convolutional, crops and flips")


def network(way, cfg):
    if way == "fully connected":
        return nn.Sequential(nn.Flatten(), nn.Linear(3 * 32 * 32, cfg.hidden), nn.ReLU(), nn.Linear(cfg.hidden, 10))
    return convnet(torch, cfg.width)


# @build 06.03 train
# One way, one seed: the network, trained for cfg.epochs passes with SGD
# and momentum, at cfg.fc_lr for the fully connected network and cfg.lr
# for the convolutional one; each pass on the training images as they
# are or, with augment, on crop_flip of them (padded by 4 pixels), turned
# into one tensor on the device. Every pass's loss and accuracy go to the
# run's log. Returns the model.
def train(cfg, way, run, dev, x, y, augment):
    torch.manual_seed(run.seed)
    model = network(way, cfg).to(dev)
    lr = cfg.fc_lr if way == "fully connected" else cfg.lr
    opt = torch.optim.SGD(model.parameters(), lr=lr, momentum=cfg.momentum)
    (labels,) = tensors(dev, y)
    for epoch in range(cfg.epochs):
        (images,) = tensors(dev, crop_flip(x, 4, run.rng) if augment else x)
        loss, acc = train_epoch(model, opt, images, labels, cfg.batch, run.rng)
        run.log(epoch=epoch + 1, loss=loss, accuracy=acc)
    return model
# @end


def main():
    cfg = lab.config(CONFIG)
    dev = lab.device(torch, cfg.device)
    x, y = cifar.load("train", cfg.n_train)
    xt, yt = cifar.load("test", cfg.n_test)
    train_set, test_set = tensors(dev, x, y), tensors(dev, xt, yt)
    print(f"{cfg.n_train} training images, {cfg.epochs} passes, SGD lr {cfg.fc_lr} (fully connected) and {cfg.lr}, on "
          f"{dev.type}; accuracy on them and on {cfg.n_test} test images")
    print(f"{'':32s} {'weights':>8s}  {'training':>8s}  {'test':40s}  gap")
    tests = {}
    start = lab.clock(torch, dev)
    for i, way in enumerate(WAYS):
        rows = []
        for seed in range(cfg.seeds):
            run = lab.Run(cfg, seed, label=("fc", "conv", "conv-augmented")[i])
            model = train(cfg, way, run, dev, x, y, augment=i == 2)
            rows.append((evaluate(model, *train_set)[1], evaluate(model, *test_set)[1]))
            run.finish(train_accuracy=rows[-1][0], test_accuracy=rows[-1][1])
        weights = sum(p.numel() for p in model.parameters())
        tests[way] = [r[1] for r in rows]
        train_acc = lab.mean([r[0] for r in rows])
        print(f"{way:32s} {weights:8d}  {train_acc:8.3f}  {lab.spread(tests[way]):40s}  "
              f"{train_acc - lab.mean(tests[way]):.3f}")
    print(f"test accuracy, convolutional against fully connected: t = "
          f"{lab.welch_t(tests[WAYS[1]], tests[WAYS[0]]):+.1f}")
    print(f"test accuracy, with crops and flips against without: t = {lab.welch_t(tests[WAYS[2]], tests[WAYS[1]]):+.1f}")
    print(f"{lab.clock(torch, dev) - start:.0f} s of training and scoring on {dev.type}")


if __name__ == "__main__":
    main()
