"""A network of Values: how many weights it has, and whether backward() gets all their gradients.

MLP(2, [4, 4, 1]) is two inputs through two layers of four relu neurons to
one output. The script counts its weights, runs it on one point, takes the
output's gradient with respect to every weight by backward(), and checks
each against a nudge of that weight, for several seeds (several starting
weights).

    python3 -m experiments.network
"""

import lab
from engine.value import MLP

CONFIG = dict(sizes=[4, 4, 1], point=[0.5, -1.5], seeds=3)


# @build 01.03 nudge_weights
# The output's derivative with respect to each weight by the nudge: move one
# weight's .data by h each way, run the network again, put it back.
# Returns one float per weight, in model.parameters() order.
def nudge_weights(model, x, h=1e-6):
    out = []
    for p in model.parameters():
        keep = p.data
        p.data = keep + h
        up = model(x).data
        p.data = keep - h
        down = model(x).data
        p.data = keep
        out.append((up - down) / (2 * h))
    return out
# @end


def main():
    cfg = lab.config(CONFIG)
    for seed in range(cfg.seeds):
        model = MLP(2, cfg.sizes, seed=seed)
        params = model.parameters()
        out = model(cfg.point)
        for p in params:
            p.grad = 0.0
        out.backward()
        nudged = nudge_weights(model, cfg.point)
        worst = max(abs(p.grad - n) for p, n in zip(params, nudged))
        zero = sum(1 for p in params if p.grad == 0)
        print(f"seed {seed}: {len(params)} weights, output {out.data:+.5f}, "
              f"{zero} with no gradient (behind a relu at 0), largest difference from the nudge {worst:.1e}")


if __name__ == "__main__":
    main()
