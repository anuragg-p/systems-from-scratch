"""Scaling: predicting a model you have not trained (Kaplan et al. 2020).

Kaplan et al. trained language models of 768 to 1.5 billion weights and
found that the loss on held-out text falls as a power law in the number
of weights, L(N) = (N_c / N)^alpha_N, with alpha_N about 0.076, for models
"trained to convergence on sufficiently large datasets", N counting every
weight but the embeddings of the tokens and of the positions. A straight
line on log-log axes can be drawn through small models and followed to a
large one before it is trained. Here, on TinyStories (09.04's tokens), 08's
GPT at one depth and several widths, each trained for the same number of
tokens, a few seeds each:

1. The sizes, and their weights counted as the paper counts them.
2. Each size trained and scored: bits per token on held-out stories.
3. The power law fitted to every size but the largest; the largest
   predicted from it, with an interval from the fit's own scatter; then the
   largest's runs beside the prediction. The same with every weight counted,
   embeddings too (the paper's figure 6 says the trend is then less clean).
4. The recorded run (experiments/recorded/scaling, about 40 minutes: larger
   sizes, more steps), read and fitted the same way.

    python3 -m experiments.scaling

The default trains sizes that take seconds. The recorded run is this
script with the settings its config.json files hold (NOTES.md has the
command). Needs TinyStories: python3 -m data.fetch tinystories.
"""

import json
import math
import os

import numpy as np
import torch

import lab
from data import tinystories
from experiments.language import train
from experiments.sequences import per_character, window_bits, windows
from models.gpt import GPT

CONFIG = dict(size=4096, layers=4, heads=4, widths=[16, 24, 32], largest=48, context=64, batch=32, steps=120,
              lr=0.003, warmup=20, weight_decay=0.1, clip=1.0, every=20, seeds=2, largest_seeds=2, held=32,
              held_stories=200, level=0.95, recorded="experiments/recorded", device="cpu")
# The paper's law in N alone (its equation 1.1, section 1.2): nats per token on WebText2's test text, averaged over
# a context of 1024, for models trained to near convergence on its 22 billion tokens.
PAPER = dict(alpha=0.076, n_c=8.8e13)


# @build 13.04 counted
# The weights of a GPT as Kaplan et al. count them (their N): every one but
# the embeddings, the vocabulary's table and the positions' (tokens.weight
# and positions.weight). They also leave out biases and layer norms ("sub-
# leading terms"), writing N as about 12 layers width^2; these are counted
# here, and are a few per cent of N at the smallest width.
def counted(model):
    return sum(p.numel() for name, p in model.named_parameters() if name not in ("tokens.weight", "positions.weight"))
# @end


# @build 13.04 predict
# The scaling law's test, on runs: rows (one dict per run: width, weights,
# all_weights, bits) of every size, `largest` the width held back. The
# power law (lab's power_law) through the runs of every other width, bits
# against `by` (weights as counted, or all_weights); what it predicts for the
# largest, with the interval for the mean of as many runs as the largest
# has, at `level`; and what those runs gave. A dict.
def predict(rows, largest, by="weights", level=0.95):
    fit_rows = [r for r in rows if r["width"] != largest]
    held = [r for r in rows if r["width"] == largest]
    law = lab.power_law([r[by] for r in fit_rows], [r["bits"] for r in fit_rows])
    n = held[0][by]
    guess, lo, hi = lab.power_interval(law, n, level, k=len(held))
    got = lab.mean([r["bits"] for r in held])
    return dict(law=law, n=n, predicted=guess, low=lo, high=hi, got=got, runs=[r["bits"] for r in held],
                inside=lo <= got <= hi)
# @end


def table(rows, cfg, title):
    """Prints each size's weights and bits, then the fit and the prediction, both ways of counting."""
    print(title)
    print(f"   {'width':>5s}  {'weights (N)':>12s}  {'12 L W^2':>10s}  {'all weights':>11s}  bits per token on held-out "
          f"stories")
    for w in sorted({r["width"] for r in rows}):
        runs = [r for r in rows if r["width"] == w]
        mark = "  (held back, predicted)" if w == cfg.largest else ""
        print(f"   {w:5d}  {runs[0]['weights']:12,d}  {12 * cfg.layers * w * w:10,d}  {runs[0]['all_weights']:11,d}  "
              f"{lab.spread([r['bits'] for r in runs], 4)}{mark}")
    out = {}
    if sum(r["width"] != cfg.largest for r in rows) < 3:
        print("   (a line with its scatter needs 3 runs or more besides the largest: no fit)")
        return out
    for by, name in (("weights", "weights counted as the paper counts them"), ("all_weights", "every weight counted")):
        p = predict(rows, cfg.largest, by, cfg.level)
        law = p["law"]
        print(f"   With {name}: bits = (N_c / N)^alpha through {law['n']} runs, alpha = {law['alpha']:.4f} (standard "
              f"error {law['alpha_se']:.4f}),\n      N_c = 10^{math.log10(law['a']) / law['alpha']:.1f}, scatter about "
              f"the line {law['s']:.4f} in ln bits."
              f"\n      Width {cfg.largest} (N = {p['n']:,}) predicted {p['predicted']:.4f}, {cfg.level:.0%} interval "
              f"for the mean of {len(p['runs'])} run{'s' * (len(p['runs']) > 1)} {p['low']:.4f} to {p['high']:.4f};"
              f"\n      trained: "
              f"{lab.spread(p['runs'], 4)}: {'inside' if p['inside'] else 'outside'} the interval, "
              f"{100 * (p['got'] - p['predicted']) / p['predicted']:+.1f}% from the prediction.")
        out[by] = p
    return out


def plot(rows, fits, path, cfg):
    """bits against N on log-log axes: each run a point, the line fitted (drawn on a little past the largest), the
    prediction's interval at the largest, and the largest's runs."""
    p = fits["weights"]
    law = p["law"]
    xs = [min(r["weights"] for r in rows), 1.5 * p["n"]]
    series = [lab.Line("fitted", [r["weights"]], [r["bits"]], 0) for r in rows if r["width"] != cfg.largest]
    series.append(lab.Line("power law", xs, [law["a"] * x ** -law["alpha"] for x in xs], 2, 0.8, dashed=True))
    series.append(lab.Line(f"{cfg.level:.0%} interval", [p["n"], p["n"]], [p["low"], p["high"]], 3))
    series += [lab.Line("held back", [r["weights"]], [r["bits"]], 1) for r in rows if r["width"] == cfg.largest]
    return lab.lines(path, series, xlabel="weights, embeddings not counted (N)", ylabel="bits per token, held out",
                     logx=True, logy=True)


def read(directory):
    """The runs of a scaling run on disk (directory: its <out>/scaling): one row per finished run (a run still going
    has no summary.json yet), as main makes them, and the settings of the first."""
    rows, cfg = [], None
    for label in sorted(os.listdir(directory)):
        if not label.startswith("width"):
            continue
        for seed in sorted(os.listdir(os.path.join(directory, label))):
            if not os.path.isfile(os.path.join(directory, label, seed, "summary.json")):
                continue
            with open(os.path.join(directory, label, seed, "summary.json")) as f:
                s = json.load(f)
            if cfg is None:
                with open(os.path.join(directory, label, seed, "config.json")) as f:
                    cfg = lab.Config(json.load(f))
            rows.append(dict(width=s["width"], weights=s["weights"], all_weights=s["all_weights"],
                             bits=s["bits_per_token"], seed=s["seed"]))
    return rows, cfg


def main():
    cfg = lab.config(CONFIG)
    dev = lab.device(torch, cfg.device)
    start = lab.clock(torch, dev)
    end = cfg.size - 1
    train_np = tinystories.tokens("train", cfg.size).astype(np.int64)
    valid_np = tinystories.tokens("valid", cfg.size).astype(np.int64)
    _, table_bytes = tinystories.tokenizer(cfg.size)
    table_bytes = {**table_bytes, end: b"\n"}
    cut = int(np.flatnonzero(valid_np == end)[cfg.held_stories - 1]) + 1
    held_ids = valid_np[:cut]
    held = torch.from_numpy(held_ids).to(dev)
    train_t = torch.from_numpy(train_np).to(dev)
    valid_t = torch.from_numpy(valid_np).to(dev)
    curve = windows(valid_t, torch.from_numpy(np.random.default_rng(0).integers(0, len(valid_np) - cfg.context - 1,
                                                                            cfg.held)).to(dev), cfg.context)
    tokens = cfg.steps * cfg.batch * cfg.context
    print(f"1. 08's GPT, {cfg.layers} blocks of {cfg.heads} heads, windows of {cfg.context} tokens, the width varied; "
          f"each trained for\n   {cfg.steps} steps of {cfg.batch} windows ({tokens:,} tokens, {tokens / len(train_np):.2f} "
          f"passes over TinyStories' {len(train_np):,}),\n   AdamW {cfg.lr}, warmup {cfg.warmup} then cosine to 0. Scored "
          f"on the first {cfg.held_stories:,} held-out stories ({len(held_ids):,} tokens).")

    rows, lines = [], []
    warm = cfg.context // 4
    for w in cfg.widths + [cfg.largest]:
        for seed in range(cfg.largest_seeds if w == cfg.largest else cfg.seeds):
            began = lab.clock(torch, dev)
            run = lab.Run(cfg, seed, label=f"width{w}")
            torch.manual_seed(seed)
            model = GPT(cfg.size, cfg.context, cfg.layers, cfg.heads, w).to(dev)
            train(model, cfg, run, dev, train_t, curve)
            model.eval()
            b = window_bits(model, held, cfg.context - warm + 1, warm)
            s = run.finish(width=w, seed=seed, weights=counted(model), all_weights=sum(p.numel() for p in
                           model.parameters()), bits_per_token=b, bits_per_byte=per_character(b, held_ids, table_bytes,
                           warm), end_held_bits=run.rows[-1]["held_bits"], tokens=tokens)
            rows.append(dict(width=w, weights=s["weights"], all_weights=s["all_weights"], bits=b, seed=seed))
            print(f"   width {w:3d}, seed {seed}: {b:.4f} bits per token ({s['bits_per_byte']:.4f} per byte), "
                  f"{lab.clock(torch, dev) - began:.0f} s", flush=True)
            lines.append(lab.Line(f"width {w}", [r["step"] * cfg.batch * cfg.context for r in run.rows],
                                  [r["held_bits"] for r in run.rows], len({r["width"] for r in rows}) - 1, 0.7))
    print()
    fits = table(rows, cfg, f"2. Each size, {cfg.seeds} seed{'s' * (cfg.seeds > 1)} ({cfg.largest_seeds} of the "
                            f"largest):")
    lab.Run(cfg, 0, label="fit").finish(**fits)
    curves = lab.lines(f"{cfg.out}/{cfg.name}/curves.svg", lines, xlabel="tokens seen", ylabel="bits per token, "
                       "held-out windows", logx=True, logy=True)
    print(f"\n   curves in {curves}" + (f", the fit in {plot(rows, fits, f'{cfg.out}/{cfg.name}/fit.svg', cfg)}"
                                         if fits else ""))
    print(f"   The paper: alpha_N {PAPER['alpha']}, N_c {PAPER['n_c']:.2g} (nats per token on WebText2; the exponent is "
          f"the same in bits).")

    recorded = os.path.join(cfg.recorded, "scaling")
    if os.path.isdir(recorded) and os.path.abspath(recorded) != os.path.abspath(f"{cfg.out}/{cfg.name}"):
        rec_rows, rec = read(recorded)
        rec_tokens = rec.steps * rec.batch * rec.context
        print()
        table(rec_rows, rec, f"3. The recorded run ({recorded}): widths {rec.widths} and {rec.largest}, {rec.steps} "
                             f"steps of {rec.batch} windows of {rec.context}\n   ({rec_tokens:,} tokens each), "
                             f"{rec.seeds} seeds ({rec.largest_seeds} of the largest), AdamW {rec.lr}:")
    print(f"\n{lab.clock(torch, dev) - start:.0f} s of training, scoring and fitting on {dev.type}")


if __name__ == "__main__":
    main()
