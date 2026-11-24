"""ResNet: the plain network against the residual one, on CIFAR-10.

He et al. (2015), section 4.2, figure 6 and table 6: on CIFAR-10 the
deeper plain network ends with the higher training error (not
overfitting: the error on its own training images), while with shortcuts
the deeper network is not worse, and in the paper better. Here: the
paper's networks (models/resnet.py) at two depths, plain and residual,
trained the paper's way at laptop size (SGD with momentum 0.9 and weight
decay 1e-4, the rate divided by 10 halfway and at three quarters, every
pass a new crop and mirror of every image), on the first n_train
training images, a few seeds each, but at a tenth of the paper's rate:
in a few hundred steps at 0.1 a deep residual network has not started
to learn, as the paper says of its 110 layers, which it starts at 0.01.
The training error at the end is the claim; the test error is beside it.

    python3 -m experiments.resnet          (needs CIFAR-10: python3 -m data.fetch cifar10)

The default is a short run. The long run recorded in experiments/recorded/
(its config.json files hold every setting) is this script with more
images, passes, depth and seeds.
"""

import torch

import lab
from data import cifar
from data.augment import crop_flip
from experiments.images import evaluate, tensors, train_epoch
from models.resnet import layers, resnet

CONFIG = dict(depths=[8, 20], width=16, n_train=800, n_test=400, epochs=3, batch=64, lr=0.01, momentum=0.9,
              weight_decay=1e-4, augment=True, seeds=2, device="cpu")
KINDS = ("plain", "residual")


# @build 06.04 train
# One network, one seed: resnet((depth - 2) // 6, residual, width) on the
# device, SGD with momentum and weight decay, its rate divided by 10 after
# half of all the steps and again after three quarters (MultiStepLR,
# stepped every batch); each pass, every image cropped and mirrored anew
# when cfg.augment, as one tensor on the device. After each pass, the
# pass's training loss and error (counted as it went) and the error on the
# test images go to the run's log. Returns the model.
def train(cfg, residual, depth, run, dev, x, y, test_set):
    torch.manual_seed(run.seed)
    model = resnet((depth - 2) // 6, residual, cfg.width).to(dev)
    opt = torch.optim.SGD(model.parameters(), lr=cfg.lr, momentum=cfg.momentum, weight_decay=cfg.weight_decay)
    steps = cfg.epochs * -(-len(x) // cfg.batch)
    scheduler = torch.optim.lr_scheduler.MultiStepLR(opt, [steps // 2, steps * 3 // 4], 0.1)
    (labels,) = tensors(dev, y)
    for epoch in range(cfg.epochs):
        (images,) = tensors(dev, crop_flip(x, 4, run.rng) if cfg.augment else x)
        loss, acc = train_epoch(model, opt, images, labels, cfg.batch, run.rng, scheduler)
        run.log(epoch=epoch + 1, train_loss=loss, train_error=100 * (1 - acc),
                test_error=100 * (1 - evaluate(model, *test_set)[1]))
    return model
# @end


def main():
    cfg = lab.config(CONFIG)
    dev = lab.device(torch, cfg.device)
    x, y = cifar.load("train", cfg.n_train)
    xt, yt = cifar.load("test", cfg.n_test)
    train_set, test_set = tensors(dev, x, y), tensors(dev, xt, yt)
    print(f"{cfg.n_train} training images, {cfg.epochs} passes, width {cfg.width}, {cfg.seeds} seeds, on {dev.type}: "
          f"error in % at the end")
    print(f"{'network':10s} {'layers':>6s}  {'training error':38s}  test error")
    errors, curves = {}, {kind: [] for kind in KINDS}
    start = lab.clock(torch, dev)
    for kind in KINDS:
        for i, depth in enumerate(cfg.depths):
            rows = []
            for seed in range(cfg.seeds):
                run = lab.Run(cfg, seed, label=f"{kind}{depth}")
                model = train(cfg, kind == "residual", depth, run, dev, x, y, test_set)
                rows.append((100 * (1 - evaluate(model, *train_set)[1]), 100 * (1 - evaluate(model, *test_set)[1])))
                run.finish(layers=layers(model), train_error=rows[-1][0], test_error=rows[-1][1],
                           train_loss=run.rows[-1]["train_loss"])
                epochs = [r["epoch"] for r in run.rows]
                curves[kind] += [lab.Line(f"{depth} layers", epochs, [r["train_error"] for r in run.rows], i, 0.8,
                                          dashed=True),
                                 lab.Line(f"{depth} layers", epochs, [r["test_error"] for r in run.rows], i, 0.8)]
            errors[kind, depth] = [r[0] for r in rows]
            print(f"{kind:10s} {layers(model):6d}  {lab.spread(errors[kind, depth]):38s}  "
                  f"{lab.mean([r[1] for r in rows]):.1f}")
    seconds = lab.clock(torch, dev) - start
    shallow, deep = cfg.depths
    for kind in KINDS:
        a, b = errors[kind, deep], errors[kind, shallow]
        print(f"{kind}: {deep} layers against {shallow}, training error {lab.mean(a):.1f} against {lab.mean(b):.1f}, "
              f"t = {lab.welch_t(a, b):+.1f} (positive: the deeper is worse)")
    for kind in KINDS:
        path = lab.lines(f"{cfg.out}/{cfg.name}/{kind}.svg", curves[kind], title=f"{kind}: training (dashed) and test",
                         xlabel="pass over the training images", ylabel="error %")
        print(f"{kind} curves in {path}")
    print(f"{seconds / 60:.1f} minutes of training on {dev.type}")


if __name__ == "__main__":
    main()
