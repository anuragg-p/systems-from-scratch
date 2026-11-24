"""Training a GPT on Shakespeare, beside module 07's ladder.

models/gpt.py's GPT, with learned positions, trained on the training text
with experiments/language.py's loop: AdamW (03.04) with weight decay on
the weight matrices, a warmup and a cosine decay (03.05), the gradient
clipped. Each setting of dropout (05.02) a few seeds; the bits per
character on a fixed batch of validation windows every cfg.every steps,
so the curve shows where the validation loss stops falling or turns up.

1. Module 07's ladder on the test text: the count models computed again
   (models/ngram.py), its networks' results quoted from their runs.
2. The GPT: bits per character on the test text and on the validation
   text, each dropout, and where its validation curve was lowest.
3. The checkpoint: the model with the lowest validation bits, saved to
   the run's folder (lab/safetensors.py), loaded back, the same scores.
4. What it writes.

    python3 -m experiments.gpt

The default is a short run. The long run recorded in experiments/recorded/
(its config.json files hold every setting) is this script with a bigger
GPT trained far longer.
"""

import numpy as np
import torch

import lab
from data import shakespeare
from experiments.language import load, save, train
from experiments.sequences import sample, window_bits, windows
from models.gpt import GPT
from models.ngram import NGram, mixture_weights

CONFIG = dict(layers=4, heads=4, width=64, context=64, batch=32, steps=300, lr=0.003, warmup=50, weight_decay=0.1,
              clip=1.0, dropouts=[0.0, 0.2], seeds=2, every=50, held=64, ks=[1.0, 0.3, 0.1, 0.03, 0.01, 0.003, 0.001],
              orders=7, length=500, device="cpu")

# Module 07's networks, test bits per character, as their own runs printed them (NOTES.md has the runs).
NETWORKS = [("07.02's network, 5 characters (its short run)", 2.474),
            ("07.02's network, 5 characters (its long run, 20 minutes)", 2.346),
            ("07.02's network and interpolation, half each (long run, 5)", 2.294),
            ("07.02's network and interpolation, half each (long run, 8)", 2.283),
            ("07.03's recurrent network (its short run)", 2.540),
            ("07.03's recurrent network, 5000 steps (1 seed)", 2.369)]


# @build 08.04 ladder
# Module 07's count models scored on the test text again, from the
# training text's counts (models/ngram.py): every character equally
# likely (log2 V), single characters and pairs with k = 0.1 added (07.01),
# the best add-k over contexts of up to `orders` characters, k chosen on
# the validation text, and deleted interpolation of contexts up to
# `orders`, the weights fit on validation (07.02). Returns (name, bits).
def ladder(train_ids, val, test, V, orders, ks):
    models = [NGram(train_ids, n, V) for n in range(orders + 1)]

    def add_k(n, ids, k):
        return -np.log2(models[n].probabilities(ids, k)).mean()
    best = min(((n, min(ks, key=lambda k: add_k(n, val, k))) for n in range(orders + 1)),
               key=lambda nk: add_k(nk[0], val, nk[1]))

    def rows(ids):
        return np.stack([models[j].probabilities(ids)[orders - j:] for j in range(orders + 1)])
    mixed = -np.log2(mixture_weights(rows(val)) @ rows(test)).mean()
    return [("every character equally likely", np.log2(V)), ("single characters", add_k(0, test, 0.1)),
            ("pairs (add-k 0.1)", add_k(1, test, 0.1)),
            (f"add-k, context {best[0]}, k {best[1]:g} (the best on validation)", add_k(best[0], test, best[1])),
            (f"deleted interpolation, contexts up to {orders}", mixed)]
# @end


# @build 08.04 lowest
# Where a run's validation curve was lowest: the step and its bits, from
# the run's log (the rows that have held_bits), and the bits at the end.
def lowest(rows):
    held = [r for r in rows if "held_bits" in r]
    best = min(held, key=lambda r: r["held_bits"])
    return best["step"], best["held_bits"], held[-1]["held_bits"]
# @end


def main():
    cfg = lab.config(CONFIG)
    dev = lab.device(torch, cfg.device)
    V = len(shakespeare.chars())
    train_ids, val, test = (shakespeare.split(s) for s in ("train", "val", "test"))
    train_t, val_t, test_t = (torch.from_numpy(a).to(dev) for a in (train_ids, val, test))
    start = lab.clock(torch, dev)

    print("1. Module 07's ladder, bits per character on the test text:")
    for name, b in ladder(train_ids, val, test, V, cfg.orders, cfg.ks):
        print(f"   {name:58s} {b:.3f}")
    for name, b in NETWORKS:
        print(f"   {name:58s} {b:.3f}")

    held = windows(val_t, torch.from_numpy(np.random.default_rng(0).integers(0, len(val) - cfg.context, cfg.held)).to(dev),
                   cfg.context)
    warm = cfg.context // 4
    passes = cfg.steps * cfg.batch * cfg.context / len(train_ids)
    results, curves, best = {}, [], None
    for i, dropout in enumerate(cfg.dropouts):
        config = dict(vocab=V, context=cfg.context, layers=cfg.layers, heads=cfg.heads, width=cfg.width,
                      dropout=dropout, bias=True, positions=True)
        for seed in range(cfg.seeds):
            run = lab.Run(cfg, seed, label=f"dropout{dropout}")
            torch.manual_seed(seed)
            model = GPT(**config).to(dev)
            train(model, cfg, run, dev, train_t, held)
            model.eval()
            got = dict(test_bits=window_bits(model, test_t, cfg.context - warm + 1, warm),
                       val_bits=window_bits(model, val_t, cfg.context - warm + 1, warm))
            step, low, end = lowest(run.rows)
            run.finish(**got, lowest_step=step, lowest_held_bits=low, end_held_bits=end)
            for k, v in dict(got, lowest_step=step, lowest=low, end=end).items():
                results.setdefault((dropout, k), []).append(v)
            if best is None or got["val_bits"] < best[0]:
                best = (got["val_bits"], model, config, dropout, seed)
            held_rows = [r for r in run.rows if "held_bits" in r]
            curves.append(lab.Line(f"training, dropout {dropout}", [r["step"] for r in run.rows],
                                   [r["bits"] for r in run.rows], 2 * i, 0.5, dashed=True))
            curves.append(lab.Line(f"validation, dropout {dropout}", [r["step"] for r in held_rows],
                                   [r["held_bits"] for r in held_rows], 2 * i + 1, 0.8))

    size = sum(p.numel() for p in best[1].parameters())
    print(f"\n2. The GPT: {cfg.layers} blocks of {cfg.heads} heads, width {cfg.width}, windows of {cfg.context}: "
          f"{size:,} weights.\n   {cfg.steps} steps of {cfg.batch} windows ({passes:.1f} passes over the training "
          f"text), AdamW {cfg.lr} (weight decay {cfg.weight_decay}),\n   {cfg.warmup} steps of warmup then a cosine to "
          f"0; {cfg.seeds} seed{'s' * (cfg.seeds > 1)} each. Bits per character (each character with {warm} or more "
          f"before it):")
    for dropout in cfg.dropouts:
        print(f"   dropout {dropout}: test {lab.spread(results[dropout, 'test_bits'], 4)}")
        print(f"   {'':12s} validation {lab.spread(results[dropout, 'val_bits'], 4)}")
        print(f"   {'':12s} validation curve ({cfg.held} windows) lowest at step "
              + ", ".join(f"{s:.0f} ({lo:.3f}, end {e:.3f})" for s, lo, e in zip(results[dropout, "lowest_step"],
                                                                                 results[dropout, "lowest"],
                                                                                 results[dropout, "end"])))
    if len(cfg.dropouts) == 2:
        a, b = (results[d, "test_bits"] for d in cfg.dropouts)
        print(f"   dropout {cfg.dropouts[1]} against {cfg.dropouts[0]}, test: t = {lab.welch_t(b, a):+.1f}")
    path = lab.lines(f"{cfg.out}/{cfg.name}/curves.svg", curves, title="bits per character: training batch and "
                     "validation windows", xlabel="step", ylabel="bits per character")
    print(f"   curves in {path}")

    _, model, config, dropout, seed = best
    where = f"{cfg.out}/{cfg.name}/model.safetensors"
    save(model, config, where, steps=cfg.steps, seed=seed, val_bits=best[0])
    again, notes = load(where, dev)
    x = test_t[None, :cfg.context]
    with torch.no_grad():
        same = torch.equal(model(x), again(x))
    print(f"\n3. The checkpoint: dropout {dropout}, seed {seed} (the lowest validation bits), saved to {where};\n"
          f"   loaded back, the same scores, number for number: {same}")

    prompt = shakespeare.encode("\n").tolist()
    drawn = sample(lambda ids: again(ids[None, -cfg.context:].to(dev))[0, -1], prompt, cfg.length,
                   torch.Generator().manual_seed(0))
    print(f"\n4. {cfg.length} characters from it, after a newline:\n")
    print("\n".join(("   " + line).rstrip() for line in shakespeare.decode(drawn).split("\n")))
    print(f"\n{lab.clock(torch, dev) - start:.0f} s of counting, training and scoring on {dev.type}")


if __name__ == "__main__":
    main()
