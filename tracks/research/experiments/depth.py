"""The experiment: what learned positions are worth as blocks are added (15.02).

experiments/question.py holds the question and the predictions, written
before any run; pilot.py (15.01) fixed the number of seeds. Here, at each
depth, a GPT without positions against the same GPT with learned
positions (08.03's sizes and budget), done with module 13's tools:

1. The search: the same learning rates for both arms at every depth, one
   seed (0), each run scored on the validation text only; each arm's rate
   at each depth is the one with the lowest validation bits.
2. The runs: each arm at its chosen rate on fresh seeds (1 to `seeds`),
   paired: one seed gives both arms the same batches and the same start
   for every weight they share. Scored on the validation text and then,
   with nothing left to choose, on the test text.
3. The gap at each depth (without minus with, the same seed's pair), its
   paired interval beside Welch's, on the test text and on validation.
4. The control: the weights learned positions add, put into the MLPs of
   the GPT without positions instead (at depth `control`; 0: none).
5. Each prediction beside its outcome, by the rule written before.
6. The recorded run (experiments/recorded/depth: depths 1 to 8, the seeds
   the pilot fixed), read: its choices, its table and its verdicts.

    python3 -m experiments.depth

The default is a small honest version, two depths and two rates; the
recorded run is the experiment.
"""

import math
import os

import torch
from torch import nn

import lab
from data import shakespeare
from experiments import question as q
from models.gpt import gelu

CONFIG = dict(width=64, context=32, heads=4, batch=32, steps=150, warmup=50, weight_decay=0.1, clip=1.0, every=50,
              depths=[1, 2], rates=[0.003, 0.006], seeds=2, control=0, recorded="experiments/recorded", device="cpu")


# @build 15.02 search
# The same search for both arms at every depth: for each depth in
# cfg.depths and each rate in cfg.rates, the pair of seed 0 (question.pair),
# each arm trained at that rate (its run labelled search-blocks<d>-<arm>-
# lr<rate>, the rate in its config.json) and scored on the validation text
# only (question.trained without test). Returns {(depth, arm): {rate:
# validation bits}}.
def search(V, cfg, dev, texts):
    found = {}
    for d in cfg.depths:
        for rate in cfg.rates:
            at = lab.Config(cfg, lr=rate)
            for arm, model in q.pair(V, at, d, 0, dev).items():
                run = lab.Run(at, 0, label=f"search-blocks{d}-{arm}-lr{rate:g}")
                found.setdefault((d, arm), {})[rate] = q.trained(model, at, run, dev, texts)["val_bits"]
    return found
# @end


# @build 15.02 Wider
# The control: an MLP like models/gpt.py's, but `extra` hidden units
# wider, built from the MLP of a block of a GPT of `layers` blocks: its
# first 4 x width units are that MLP's own weights, copied; the extra ones
# start as GPT-2 starts (sd 0.02, the layer down by sqrt(2 x layers)
# smaller, biases 0). So a GPT without positions given Wider MLPs starts as
# it was, plus weights that cannot say where a character is.
class Wider(nn.Module):
    def __init__(self, mlp, extra, layers):
        super().__init__()
        width, hidden = mlp.up.in_features, mlp.up.out_features
        self.up = nn.Linear(width, hidden + extra)
        self.down = nn.Linear(hidden + extra, width)
        with torch.no_grad():
            nn.init.normal_(self.up.weight, 0.0, 0.02)
            nn.init.zeros_(self.up.bias)
            nn.init.normal_(self.down.weight, 0.0, 0.02 / math.sqrt(2 * layers))
            self.up.weight[:hidden] = mlp.up.weight
            self.up.bias[:hidden] = mlp.up.bias
            self.down.weight[:, :hidden] = mlp.down.weight
            self.down.bias.copy_(mlp.down.bias)

    def forward(self, x):
        return self.down(gelu(self.up(x)))
# @end


def widen(model, extra, layers):
    """model (a GPT without positions) with every block's MLP made Wider by extra units."""
    for block in model.blocks:
        block.mlp = Wider(block.mlp, extra, layers)
    return model


def extra_units(cfg, layers):
    """How many hidden units a block's MLP gains so that the GPT gains about the weights positions add, context x
    width: each unit is width + 1 weights in and width out."""
    return round(cfg.context * cfg.width / (layers * (2 * cfg.width + 1)))


def texts(dev):
    return {s: torch.from_numpy(shakespeare.split(s)).to(dev) for s in ("train", "val", "test")}


def table(found, runs, control, cfg, out=None):
    """Parts 1 to 5 for a run, done or read back; the figures to out/ when given. Returns the verdicts."""
    chosen = q.choose(found)
    depths = sorted({d for d, _ in runs})
    print(f"   The search, validation bits by rate ({', '.join(f'{r:g}' for r in sorted(cfg.rates))}), seed 0; "
          f"the rate chosen:")
    for (d, arm), scores in sorted(found.items()):
        edge = " (at the edge of the range)" if chosen[d, arm] in (min(cfg.rates), max(cfg.rates)) else ""
        print(f"   {d} block{'s' * (d > 1)}, {arm:8s} " + "  ".join(f"{scores[r]:.4f}" for r in sorted(scores)) +
              f"   chosen {chosen[d, arm]:g}{edge}")
    seeds = len(runs[depths[0], "none"])
    test = {k: [s["test_bits"] for s in v] for k, v in runs.items()}
    val = {k: [s["val_bits"] for s in v] for k, v in runs.items()}
    print(f"\n   Test bits per character, {seeds} fresh seeds (1 to {seeds}), each arm at its chosen rate; the gap is "
          f"none minus learned,\n   seed by seed, with its {q.LEVEL:.0%} interval paired and as two independent sets "
          f"(Welch):")
    on_test, on_val = q.gaps(test, depths), q.gaps(val, depths)
    for d in depths:
        each, mean, (plo, phi), (wlo, whi), lower = on_test[d]
        print(f"   {d} block{'s' * (d > 1)}:  none {lab.spread(test[d, 'none'], 4)}\n"
              f"   {'':10s}learned {lab.spread(test[d, 'learned'], 4)}\n"
              f"   {'':10s}gap {mean:+.4f}   paired {plo:+.4f} to {phi:+.4f}   Welch {wlo:+.4f} to {whi:+.4f}   "
              f"learned lower on {lower} of {len(each)};  on validation {on_val[d][1]:+.4f}")
    if control:
        for d, rows in control.items():
            bits = [s["test_bits"] for s in rows]
            added = rows[0]["weights"] - runs[d, "none"][0]["weights"]
            print(f"\n   The control at {d} blocks: no positions, {added} more weights in the MLPs (learned positions "
                  f"add {runs[d, 'learned'][0]['weights'] - runs[d, 'none'][0]['weights']}):\n"
                  f"   {'':10s}{lab.spread(bits, 4)}; minus learned, paired: " +
                  "{:+.4f} ({:+.4f} to {:+.4f})".format(*lab.difference(bits, test[d, "learned"], paired=True)))
    results = ({d: on_test[d][0] for d in depths}, test, {d: [s["test_bits"] for s in rows] for d, rows in control.items()})
    print("\n   The predictions, each by the rule written before any run:")
    verdicts = {}
    for p in q.PREDICTIONS:
        try:
            verdicts[p.key] = q.judge(p.rule, *results)
        except (KeyError, ZeroDivisionError):
            verdicts[p.key] = ("not run here", None)
        print(f"   {p.key:20s} {verdicts[p.key][0]:13s} {shown(verdicts[p.key][1])}")
    if out:
        draw(out, depths, test, on_test)
    return verdicts


def shown(v):
    if v is None:
        return ""
    if isinstance(v, (list, tuple)):
        return "(" + ", ".join(f"{x:+.4f}" for x in v) + ")"
    return f"{v:+.4f}"


def draw(out, depths, test, on_test):
    """bits.svg, each arm's test bits against depth (the mean, and the seeds' range as a bar), and gap.svg, the gap
    against depth with its paired interval (solid) and Welch's (dashed, beside it)."""
    series = []
    for k, arm in enumerate(q.ARMS):
        series.append(lab.Line(f"{arm} positions" if arm == "none" else "learned positions", depths,
                               [lab.mean(test[d, arm]) for d in depths], k))
        series += [lab.Line("", [d, d], [min(test[d, arm]), max(test[d, arm])], k) for d in depths]
    lab.lines(os.path.join(out, "bits.svg"), series, xlabel="blocks", ylabel="bits per character, test text")
    series = [lab.Line("gap (none minus learned)", depths, [on_test[d][1] for d in depths], 0),
              lab.Line("zero", depths, [0.0] * len(depths), "#888888", dashed=True)]
    series += [lab.Line("", [d, d], list(on_test[d][2]), 0) for d in depths]
    series += [lab.Line("Welch's interval", [d * 1.04, d * 1.04], list(on_test[d][3]), 1, dashed=True) for d in depths]
    lab.lines(os.path.join(out, "gap.svg"), series, xlabel="blocks", ylabel="gap, bits per character")


def main():
    cfg = lab.config(CONFIG)
    dev = lab.device(torch, cfg.device)
    V = len(shakespeare.chars())
    data = texts(dev)
    start = lab.clock(torch, dev)

    found = search(V, cfg, dev, data)
    chosen = q.choose(found)
    runs, control = {}, {}
    for seed in range(1, cfg.seeds + 1):
        for d in cfg.depths:
            for arm, model in q.pair(V, cfg, d, seed, dev).items():
                at = lab.Config(cfg, lr=chosen[d, arm])
                run = lab.Run(at, seed, label=f"blocks{d}-{arm}")
                runs.setdefault((d, arm), []).append(q.trained(model, at, run, dev, data, test=True))
        if cfg.control:
            d = cfg.control
            at = lab.Config(cfg, lr=chosen[d, "none"])
            model = widen(q.pair(V, at, d, seed, dev)["none"], extra_units(cfg, d), d).to(dev)
            run = lab.Run(at, seed, label=f"control-blocks{d}-wider")
            control.setdefault(d, []).append(q.trained(model, at, run, dev, data, test=True))
    print(f"1 to 5. {cfg.steps} steps of {cfg.batch} windows of {cfg.context}, width {cfg.width}, {cfg.heads} heads, "
          f"depths {', '.join(map(str, cfg.depths))}:")
    table(found, runs, control, cfg, os.path.join(cfg.out, cfg.name))
    print(f"   figures in {os.path.join(cfg.out, cfg.name, 'bits.svg')} and gap.svg")

    recorded = os.path.join(cfg.recorded, "depth")
    if os.path.isdir(recorded) and os.path.abspath(recorded) != os.path.abspath(f"{cfg.out}/{cfg.name}"):
        rfound, rruns, rcontrol, rcfg = q.results(recorded)
        print(f"\n6. The recorded run ({recorded}): {rcfg.steps} steps, depths {', '.join(map(str, rcfg.depths))}, "
              f"rates {', '.join(f'{r:g}' for r in rcfg.rates)}:")
        table(rfound, rruns, rcontrol, rcfg)
    print(f"\n{lab.clock(torch, dev) - start:.0f} s of training and scoring on {dev.type}")


if __name__ == "__main__":
    main()
