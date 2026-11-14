"""Weight decay and dropout: the same network, made to memorise less.

Srivastava et al. (2014), table 2: on MNIST, a network trained with
dropout (each input pixel dropped with probability 0.2, each hidden unit
with 0.5) has a lower test error than the same network without. Here, at
laptop size: two hidden layers of 512 trained with AdamW for 50 passes
over 2000 digits, four ways: neither, weight decay alone, dropout alone,
both; a few seeds each. The model is chosen on the validation set; the
test error is printed beside it.

    python3 -m experiments.regularise        (needs MNIST: python3 -m data.fetch mnist)
"""

import engine as torch                      # the engine; "import torch" runs this on PyTorch
import lab
from data import mnist
from experiments.loop import evaluate, train

nn = torch.nn
CONFIG = dict(n_train=2000, n_val=10000, hidden=512, lr=1e-3, batch=128, epochs=50, decay=0.5,
              drop_in=0.2, drop_hidden=0.5, seeds=3)
WAYS = [("neither", False, False), ("weight decay", True, False), ("dropout", False, True), ("both", True, True)]


# @build 05.02 network
# Two hidden layers of `hidden` relu units; with dropout, an nn.Dropout of
# p_in on the input pixels and of p_hidden after each hidden layer, as the
# paper places them (p of 0 adds nothing).
def network(hidden, p_in=0.0, p_hidden=0.0):
    layers = [nn.Dropout(p_in)] if p_in else []
    for n_in in (784, hidden):
        layers += [nn.Linear(n_in, hidden), nn.ReLU()]
        if p_hidden:
            layers.append(nn.Dropout(p_hidden))
    return nn.Sequential(*layers, nn.Linear(hidden, 10))
# @end


def main():
    cfg = lab.config(CONFIG)
    x, y = mnist.load("train")
    x, y, xv, yv = x[:cfg.n_train], y[:cfg.n_train], x[-cfg.n_val:], y[-cfg.n_val:]
    xt, yt = mnist.load("test")
    errors = {}
    print(f"{cfg.n_train} training digits, {cfg.epochs} passes; error in %")
    print(f"{'':14s}{'training':>10s}  {'validation':32s}  test")
    for name, decay, drop in WAYS:
        rows = []
        for seed in range(cfg.seeds):
            run = lab.Run(cfg, seed, label=name.replace(" ", "-"))
            torch.manual_seed(seed)
            model = network(cfg.hidden, cfg.drop_in if drop else 0.0, cfg.drop_hidden if drop else 0.0)
            opt = torch.optim.AdamW(model.parameters(), lr=cfg.lr, weight_decay=cfg.decay if decay else 0.0)
            train(torch, model, opt, x, y, cfg.batch, cfg.epochs, run.rng, run)
            rows.append([100 * (1 - evaluate(torch, model, a, b)[1]) for a, b in ((x, y), (xv, yv), (xt, yt))])
            run.finish(train_error=rows[-1][0], val_error=rows[-1][1], test_error=rows[-1][2])
        errors[name] = [r[2] for r in rows]
        print(f"{name:14s}{lab.mean([r[0] for r in rows]):10.2f}  {lab.spread([r[1] for r in rows]):32s}  "
              f"{lab.mean([r[2] for r in rows]):.2f}")
    for name in ("weight decay", "dropout", "both"):
        print(f"test error, {name} against neither: t = {lab.welch_t(errors[name], errors['neither']):+.1f} "
              f"(negative: lower)")


if __name__ == "__main__":
    main()
