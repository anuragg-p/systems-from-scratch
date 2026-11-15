"""Adam: one learning rate for weights whose gradients differ by orders of magnitude. Two parts.

1. The valley of 03.02, (w0^2 + s w1^2) / 2 from (-4, 1), in float64. Momentum moves each
   weight by lr times its gradient, so lr has to be small enough for the steepest direction,
   and then the shallow one crawls. Adam divides each weight's step by the size of that
   weight's own recent gradients, so its steps do not depend on how big the gradient is. The
   script counts the steps each needs to get the loss below 0.0001 at s = 50 (03.02's valley)
   and at s = 5000, at several rates for momentum and one for Adam; prints the first step each
   takes; and runs the valley again with its loss multiplied by 1000.
2. The Adam paper's comparison at laptop size. Kingma and Ba (2014), figures 1 and 2: on
   MNIST, logistic regression and a network of two hidden layers, the training cost of each
   optimiser against the passes over the data, each at the best learning rate from a grid. The
   paper's claim for the multilayer network is that Adam's cost falls fastest; for logistic
   regression, that Adam does about as well as SGD with Nesterov momentum. Here: the same two
   models (the network has 256 units a layer, not 1000, and no dropout), pixels on the paper's
   scale 0..1, batches of 128, three passes, each optimiser at the best rate of a small grid
   (chosen by the mean final cost over the seeds), several seeds. After every pass, the cost on
   the whole training set.

    python3 -m experiments.adam              (part 2 needs MNIST: python3 -m data.fetch mnist)
    python3 -m experiments.adam models=[]    part 1 alone
    python3 -m experiments.adam standardise=True       the inputs the rest of the track uses
"""

import math

import engine as torch                      # the engine; "import torch" runs this on PyTorch
import lab
from data import mnist
from experiments.loop import evaluate, mlp, train

CONFIG = dict(steeps=[50.0, 5000.0], momentum_lrs=[0.03, 0.01, 0.003, 0.001, 0.0003], valley_momentum=0.8,
              valley_lr=0.1, scale=1000.0, max_steps=5000,
              models=["logistic", "mlp"], hidden=256, epochs=3, batch=128, adam_lrs=[3e-4, 1e-3, 3e-3],
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


def valley(name, steep, lr, scale, max_steps, mu):
    """Descent on scale * (w0^2 + steep * w1^2) / 2 from (-4, 1), in float64, with Adam ("adam")
    or SGD with momentum mu ("momentum"), until the loss is below scale * 0.0001 or max_steps
    have been taken: the number of steps (None if the loss stopped being a finite number) and
    the path, [w0, w1] at the start and after each step."""
    w = torch.tensor([-4.0, 1.0], dtype=torch.float64, requires_grad=True)
    curve = torch.tensor([scale, scale * steep], dtype=torch.float64)
    opt = make_optimizer("adam", [w], lr, 0) if name == "adam" else torch.optim.SGD([w], lr=lr, momentum=mu)
    path = [w.tolist()]
    for step in range(max_steps):
        loss = (curve * w * w).sum() * 0.5
        if not math.isfinite(loss.item()):
            return None, path
        if loss.item() < scale * 1e-4:
            return step, path
        opt.zero_grad()
        loss.backward()
        opt.step()
        path.append(w.tolist())
    return max_steps, path


def one_rate(cfg):
    """Part 1: momentum and Adam on the valley at each steepness, their first steps, and the loss
    multiplied by cfg.scale."""
    mu, lr = cfg.valley_momentum, cfg.valley_lr
    say = lambda n: "diverged" if n is None else f"{n} steps"
    print(f"1. the valley (w0^2 + s w1^2) / 2 from (-4, 1): steps to a loss below 0.0001 (at most {cfg.max_steps})")
    print(f"   {'':26s}" + "".join(f"{'s = %g' % s:>10s}" for s in cfg.steeps))
    rows = [(f"momentum {mu:g}, lr {r:g}", "momentum", r) for r in cfg.momentum_lrs] + [(f"adam, lr {lr:g}", "adam", lr)]
    for label, name, rate in rows:
        steps = [valley(name, s, rate, 1.0, cfg.max_steps, mu)[0] for s in cfg.steeps]
        print(f"   {label:26s}" + "".join(f"{'diverged' if n is None else n:>10}" for n in steps))
    steep, small = max(cfg.steeps), min(cfg.momentum_lrs)
    print(f"   the first step at s = {steep:g}, how far each weight moves:")
    for label, name, rate in ((f"momentum {mu:g}, lr {small:g}", "momentum", small), (f"adam, lr {lr:g}", "adam", lr)):
        (u0, v0), (u1, v1) = valley(name, steep, rate, 1.0, 1, mu)[1]
        print(f"   {label:26s}w0 {abs(u1 - u0):<8.3g}  w1 {abs(v1 - v0):.3g}")
    steep, big = min(cfg.steeps), max(cfg.momentum_lrs)
    print(f"   the loss times {cfg.scale:g}, s = {steep:g}:")
    for rate in (big, big / cfg.scale):
        print(f"   {f'momentum {mu:g}, lr {rate:g}':26s}{say(valley('momentum', steep, rate, cfg.scale, cfg.max_steps, mu)[0])}")
    n, plain = valley("adam", steep, lr, 1.0, cfg.max_steps, mu)
    k, scaled = valley("adam", steep, lr, cfg.scale, cfg.max_steps, mu)
    gap = max(abs(u - v) for p, q in zip(plain, scaled) for u, v in zip(p, q))
    print(f"   {f'adam, lr {lr:g}':26s}{say(k)}, every weight within {gap:.1e} of its place on the loss itself")


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


def race(cfg):
    """Part 2: the paper's comparison, model by model."""
    data = mnist.load("train", None, cfg.standardise)
    scale = "standardised" if cfg.standardise else "0..1"
    print("2. the Adam paper's comparison on MNIST, at laptop size")
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


def main():
    cfg = lab.config(CONFIG)
    one_rate(cfg)
    if cfg.models:
        race(cfg)


if __name__ == "__main__":
    main()
