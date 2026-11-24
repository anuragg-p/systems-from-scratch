"""Attention: looking back at every position.

An encoder reads a sequence of random symbols and a decoder writes it out
again (task "copy", or "reverse" to write it backwards), both 07.03's
recurrent cell. Without attention the decoder starts from the encoder's
last state and has nothing else: the whole input has to pass through one
vector. With attention (models/attention.py, models/seq2seq.py) it also
takes, at every step, a weighted sum of all the encoder's states, the
weights chosen by itself at that step.

Bahdanau, Cho and Bengio (2015), figure 2: translating English to French,
the encoder-decoder's quality falls as the sentences get longer, while
with attention it holds up. Here, at laptop size, the same pair of
models on the copying task: each trained on lengths from `shortest` to
`longest`, a few seeds each, then the fraction of symbols written right,
greedily (each symbol written from those it wrote before), at each length
of `lengths`, including lengths longer than any trained on. The weights
of one example of each length in `examples` go to the attention runs'
summary.json (the paper's figure 3 draws such weights).

    python3 -m experiments.attention
"""

import numpy as np
import torch
import torch.nn.functional as F

import lab
from models.seq2seq import AttentionDecoder, Decoder, Encoder, Seq2Seq

CONFIG = dict(task="copy", symbols=10, embed=32, hidden=64, size=64, shortest=1, longest=20, steps=1200, batch=64,
              lr=0.003, clip=1.0, lengths=[2, 5, 10, 15, 20, 25, 30, 40], tested=500, seeds=3, examples=[10, 30],
              shown=10, device="cpu")
KINDS = ("no attention", "attention")


def task(n, length, cfg, rng, dev):
    """n random inputs of the length, the outputs the task asks for, and what precedes each output
    symbol (START, then the output shifted one place), as tensors on dev."""
    x = rng.integers(0, cfg.symbols, (n, length))
    y = x[:, ::-1].copy() if cfg.task == "reverse" else x.copy()
    previous = np.concatenate([np.full((n, 1), cfg.symbols), y[:, :-1]], axis=1)
    return [torch.from_numpy(a).to(dev) for a in (x, y, previous)]


def model(kind, cfg):
    decoder = (AttentionDecoder(cfg.symbols, cfg.embed, cfg.hidden, cfg.size) if kind == "attention"
               else Decoder(cfg.symbols, cfg.embed, cfg.hidden))
    return Seq2Seq(Encoder(cfg.symbols, cfg.embed, cfg.hidden), decoder)


# @build 07.04 train
# One model, one seed: Adam at cfg.lr for cfg.steps steps, each a batch of
# new random inputs of one length drawn from shortest to longest (all of a
# batch the same length), the cross-entropy of every output position given
# the right symbols before it (teacher forcing), the gradient clipped to
# cfg.clip. The loss every 100 steps goes to the run's log.
def train(cfg, kind, run, dev):
    torch.manual_seed(run.seed)
    net = model(kind, cfg).to(dev)
    opt = torch.optim.Adam(net.parameters(), lr=cfg.lr)
    for step in range(cfg.steps):
        length = int(run.rng.integers(cfg.shortest, cfg.longest + 1))
        x, y, previous = task(cfg.batch, length, cfg, run.rng, dev)
        scores, _ = net(x, previous)
        loss = F.cross_entropy(scores.reshape(-1, cfg.symbols), y.reshape(-1))
        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(net.parameters(), cfg.clip)
        opt.step()
        if step % 100 == 0 or step == cfg.steps - 1:
            run.log(step=step, length=length, loss=loss.item())
    return net
# @end


# @build 07.04 accuracy
# The fraction of output symbols the model writes right, greedily, for n
# new random inputs of the length (drawn from rng), and the fraction of
# whole outputs right.
def accuracy(net, length, n, cfg, rng, dev):
    x, y, _ = task(n, length, cfg, rng, dev)
    with torch.no_grad():
        written, _ = net.generate(x, length)
    right = written == y
    return right.float().mean().item(), right.all(dim=1).float().mean().item()
# @end


def main():
    cfg = lab.config(CONFIG)
    dev = lab.device(torch, cfg.device)
    start = lab.clock(torch, dev)
    print(f"Task: {cfg.task} {cfg.symbols} random symbols; trained on lengths {cfg.shortest} to {cfg.longest}, "
          f"{cfg.steps} steps of {cfg.batch}, a state of {cfg.hidden}, {cfg.seeds} seeds;\nthe fraction of symbols "
          f"written right, greedily, on {cfg.tested} new inputs of each length (chance {1 / cfg.symbols:.2f})")
    results, nets = {}, {}
    for kind in KINDS:
        for seed in range(cfg.seeds):
            run = lab.Run(cfg, seed, label=kind.replace(" ", "-"))
            net = train(cfg, kind, run, dev)
            nets.setdefault(kind, net)
            rng = np.random.default_rng(1000 + seed)
            got = {length: accuracy(net, length, cfg.tested, cfg, rng, dev) for length in cfg.lengths}
            for length, (symbols, whole) in got.items():
                results.setdefault((kind, length), []).append((symbols, whole))
            examples = {}
            if kind == "attention":
                examples["examples"] = []
                for length in cfg.examples:
                    x, y, _ = task(1, length, cfg, np.random.default_rng(seed), dev)
                    with torch.no_grad():
                        written, weights = net.generate(x, length)
                    examples["examples"].append({"input": x[0].tolist(), "written": written[0].tolist(),
                                                 "weights": weights[0].tolist()})
            run.finish(symbols_right={str(k): v[0] for k, v in got.items()},
                       wholes_right={str(k): v[1] for k, v in got.items()}, **examples)
    print(f"\n{'length':>6s}  {'no attention':38s}  {'attention':38s}  t")
    for length in cfg.lengths:
        a, b = ([r[0] for r in results[kind, length]] for kind in KINDS)
        longer = "  (longer than any trained on)" if length > cfg.longest else ""
        print(f"{length:6d}  {lab.spread(a):38s}  {lab.spread(b):38s}  {lab.welch_t(b, a):+.1f}{longer}")
    print(f"\nWhole outputs right (mean over seeds):")
    print(f"{'length':>6s}  " + "  ".join(f"{kind:>12s}" for kind in KINDS))
    for length in cfg.lengths:
        print(f"{length:6d}  " + "  ".join(f"{lab.mean([r[1] for r in results[kind, length]]):12.3f}" for kind in KINDS))

    x, y, _ = task(1, cfg.shown, cfg, np.random.default_rng(0), dev)
    with torch.no_grad():
        written, weights = nets["attention"].generate(x, cfg.shown)
    print(f"\nWhere the attention decoder looked (seed 0), input {x[0].tolist()}:")
    for i in range(cfg.shown):
        w = weights[0, i]
        print(f"   step {i:2d} wrote {int(written[0, i])}: most weight on input position {int(w.argmax()):2d} "
              f"({float(w.max()):.2f}), symbol {int(x[0, w.argmax()])}")
    print(f"\n{lab.clock(torch, dev) - start:.0f} s of training and scoring on {dev.type}")


if __name__ == "__main__":
    main()
