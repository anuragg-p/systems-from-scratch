"""Adam against SGD with Nesterov momentum on MNIST: the Adam paper's comparison, at laptop size.

Kingma and Ba (2014), figures 1 and 2: on MNIST, logistic regression and a
network of two hidden layers, the training cost of each optimiser against
the passes over the data, each at the best learning rate from a grid. The
paper's claim for the multilayer network is that Adam's cost falls fastest;
for logistic regression, that Adam does about as well as SGD with Nesterov
momentum. Here: the same two models (the network has 256 units a layer,
not 1000, and no dropout), pixels on the paper's scale 0..1, batches of
128, three passes, each optimiser at the best rate of a small grid
(chosen by the mean final cost over the seeds), several seeds. After every
pass, the cost on the whole training set.

    python3 -m experiments.adam              (needs MNIST: python3 -m data.fetch mnist)
    python3 -m experiments.adam standardise=True       the inputs the rest of the track uses
"""

import engine as torch                      # the engine; "import torch" runs this on PyTorch
import lab
from data import mnist
from experiments.loop import evaluate, mlp, train

CONFIG = dict(models=["logistic", "mlp"], hidden=256, epochs=3, batch=128, adam_lrs=[3e-4, 1e-3, 3e-3],
              sgd_lrs=[0.01, 0.03, 0.1], momentum=0.9, seeds=3, standardise=False)
SIZES = {"logistic": lambda h: [784, 10], "mlp": lambda h: [784, h, h, 10]}


# @build 03.03 make_optimizer
# The optimiser under test, by name: "adam" is Adam at lr with its default
# betas and eps; "nesterov" is SGD at lr with Nesterov momentum.
def make_optimizer(name, params, lr, momentum):
    if name == "adam":
        return torch.optim.Adam(params, lr=lr)
    return torch.optim.SGD(params, lr=lr, momentum=momentum, nesterov=True)
# @end


def costs(cfg, model_name, opt_name, lr, seed, data):
    """The training cost on the whole training set after each pass, for one rate and seed."""
    x, y = data
    run = lab.Run(cfg, seed, label=f"{model_name}-{opt_name}-lr{lr:g}")
    torch.manual_seed(seed)
    model = mlp(torch, SIZES[model_name](cfg.hidden))
    opt = make_optimizer(opt_name, model.parameters(), lr, cfg.momentum)
    out = []
    for epoch in range(1, cfg.epochs + 1):
        losses = train(torch, model, opt, x, y, cfg.batch, 1, run.rng)
        cost = evaluate(torch, model, x, y)[0] if losses[-1] == losses[-1] else float("nan")
        run.log(epoch=epoch, cost=cost)
        out.append(cost)
    run.finish(cost=out[-1])
    return out


def main():
    cfg = lab.config(CONFIG)
    data = mnist.load("train", None, cfg.standardise)
    scale = "standardised" if cfg.standardise else "0..1"
    for model_name in cfg.models:
        print(f"{model_name} {SIZES[model_name](cfg.hidden)}, pixels {scale}: training cost after each pass, "
              f"{cfg.seeds} seeds")
        best, lines = {}, []
        for i, (opt_name, lrs) in enumerate((("adam", cfg.adam_lrs), ("nesterov", cfg.sgd_lrs))):
            grid = {lr: [costs(cfg, model_name, opt_name, lr, seed, data) for seed in range(cfg.seeds)]
                    for lr in lrs}
            for lr, runs in grid.items():
                finals = [r[-1] for r in runs]
                print(f"  {opt_name:8s} lr {lr:<6g} final cost {lab.spread(finals)}")
            lr = min(grid, key=lambda k: lab.mean([r[-1] for r in grid[k]]) if all(
                r[-1] == r[-1] for r in grid[k]) else float("inf"))
            best[opt_name] = (lr, grid[lr])
            lines += [lab.Line(f"{opt_name} lr {lr:g}", range(1, cfg.epochs + 1), r, i, 0.7) for r in grid[lr]]
        (a_lr, a), (s_lr, s) = best["adam"], best["nesterov"]
        for e in range(cfg.epochs):
            ae, se = [r[e] for r in a], [r[e] for r in s]
            print(f"  pass {e + 1}: adam (lr {a_lr:g}) {lab.mean(ae):.4f}  nesterov (lr {s_lr:g}) "
                  f"{lab.mean(se):.4f}  lower: {'adam' if lab.mean(ae) < lab.mean(se) else 'nesterov'}, "
                  f"t = {lab.welch_t(se, ae):+.1f}")
        path = lab.lines(f"{cfg.out}/{cfg.name}/{model_name}.svg", lines, xlabel="passes over the data",
                         ylabel="training cost", logy=True)
        print(f"  curves in {path}")


if __name__ == "__main__":
    main()
