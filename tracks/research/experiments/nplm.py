"""Embeddings and a network: a neural language model, against counting with longer contexts.

The obvious way past 07.01's pairs is a longer context: count what
follows every 3, 4, 5 characters. Part 1 shows where that goes: the
number of possible contexts is 65 to the power of their length, almost
all of them never occur, more and more of the held-out text's contexts
were never seen in training, and while the training text's bits keep
falling the held-out bits turn up, however the counts are smoothed
(add-k, k chosen on the validation text). Part 2 gives counting its best
honest chance, the paper's own baseline: deleted interpolation, every
length of context up to n mixed with weights fit on the validation text.

Bengio et al. (2003), "A Neural Probabilistic Language Model": give
every symbol a vector of m learned numbers, an embedding, and let a
network read the context's embeddings side by side and score the next
symbol, trained by cross-entropy. Similar symbols get similar vectors, so
what is learned about one context carries to contexts never seen. Their
table 1 (words, the Brown corpus): test perplexity 268 for their best
network alone and 252 mixed with a trigram model, against 312 for the
best n-gram model and 336 for deleted interpolation of trigrams. Part 3
runs it on characters at several lengths of context, a few seeds each,
against the best count models of the same length, and the paper's mix of
the two (each half the chance). Part 4 looks at which characters the
network put near each other, and part 5 at what it writes.

    python3 -m experiments.nplm

The default is a short run. The long run recorded in experiments/recorded/
(its config.json files hold every setting) is this script with a bigger
network trained eight times as long.
"""

import numpy as np
import torch
from torch import nn
import torch.nn.functional as F

import lab
from data import shakespeare
from experiments.sequences import bits, context_bits, contexts, sample
from models.ngram import NGram, mixture_weights

CONFIG = dict(orders=[0, 1, 2, 3, 4, 5, 6, 7], ks=[1.0, 0.3, 0.1, 0.03, 0.01, 0.003, 0.001], contexts=[1, 3, 5],
              embed=24, hidden=512, dropout=0.0, steps=2500, batch=1024, lr=0.01, seeds=3, length=300,
              near="ae.A!s", common=1000, device="cpu")


# @build 07.02 NPLM
# Bengio et al.'s network for contexts of n symbols: each symbol of the
# context looked up in one table of embeddings (nn.Embedding, a row of m
# numbers for each of the V symbols, learned like any weight), the n rows
# side by side as one vector of n * m, a hidden layer of tanh units, and a
# Linear layer to V scores, one for each symbol that could come next. With
# dropout, the hidden units are dropped in training (05.02). (The paper's
# direct connections, from the embeddings straight to the scores, are left
# out.)
class NPLM(nn.Module):
    def __init__(self, V, n, m, hidden, dropout=0.0):
        super().__init__()
        self.embed = nn.Embedding(V, m)
        self.hidden = nn.Linear(n * m, hidden)
        self.out = nn.Linear(hidden, V)
        self.dropout = dropout

    def forward(self, x):
        h = torch.tanh(self.hidden(self.embed(x).flatten(1)))
        return self.out(F.dropout(h, self.dropout, self.training))
# @end


# @build 07.02 train
# One network, one seed, contexts of n characters: NPLM on the device,
# Adam at cfg.lr falling to 0 along half a cosine over cfg.steps steps
# (03.05); each step a batch of cfg.batch positions of the training text
# drawn from run.rng, the n characters before each the input, the
# character at it the target, cross-entropy. The batch's bits every 100
# steps go to the run's log. Returns the model.
def train(cfg, n, run, dev, ids, V):
    torch.manual_seed(run.seed)
    model = NPLM(V, n, cfg.embed, cfg.hidden, cfg.dropout).to(dev)
    opt = torch.optim.Adam(model.parameters(), lr=cfg.lr)
    scheduler = torch.optim.lr_scheduler.LambdaLR(opt, lab.warmup_cosine(0, cfg.steps))
    for step in range(cfg.steps):
        positions = torch.from_numpy(run.rng.integers(n, len(ids), cfg.batch)).to(dev)
        x, y = contexts(ids, positions, n)
        loss = bits(model(x), y)
        opt.zero_grad()
        loss.backward()
        opt.step()
        scheduler.step()
        if step % 100 == 0 or step == cfg.steps - 1:
            run.log(step=step, bits=loss.item())
    return model
# @end


# @build 07.02 nearest
# Of the characters numbered in among, the k whose embeddings point the
# most nearly the same way as that of character c, most similar first,
# with their similarities: the cosine similarity of two vectors, their
# dot product over the product of their lengths (1 the same direction, 0
# at right angles).
def nearest(model, c, among, k=4):
    e = model.embed.weight.detach()
    e = e / e.norm(dim=1, keepdim=True)
    similarity = e[among] @ e[c]
    order = similarity.argsort(descending=True).tolist()
    return [(among[i], float(similarity[i])) for i in order if among[i] != c][:k]
# @end


def chances(model, ids, n):
    """The network's chance of each character of ids from position n on (numpy, float64)."""
    model.eval()
    out = []
    with torch.no_grad():
        positions = torch.arange(n, len(ids), device=ids.device)
        for start in range(0, len(positions), 8192):
            x, y = contexts(ids, positions[start:start + 8192], n)
            out.append(F.softmax(model(x), dim=1).gather(1, y[:, None])[:, 0].double().cpu())
    model.train()
    return torch.cat(out).numpy()


def mixed_counts(models, val, test, n):
    """Deleted interpolation: the count models of every context up to n characters, mixed with
    weights fit on the validation text; its chance of each test character from position n on."""
    def rows(ids):
        return np.stack([models[j].probabilities(ids)[n - j:] for j in range(n + 1)])
    w = mixture_weights(rows(val))
    return w @ rows(test), w


def main():
    cfg = lab.config(CONFIG)
    dev = lab.device(torch, cfg.device)
    V = len(shakespeare.chars())
    train_ids, val, test = (shakespeare.split(s) for s in ("train", "val", "test"))
    start = lab.clock(torch, dev)
    longest = max(cfg.orders + cfg.contexts)
    models = {n: NGram(train_ids, n, V) for n in range(longest + 1)}

    print(f"1. Counting with longer contexts: bits per character on the training text itself (k = 0) and on "
          f"the test text\n   (k, added to every count, chosen on the validation text from {cfg.ks})")
    print(f"   {'context':>7s} {'contexts seen':>13s} {'of':>9s} {'pairs seen':>10s} {'of them':>9s} "
          f"{'unseen in test':>14s} {'training':>8s} {'test':>7s} {'k':>6s}")
    run = lab.Run(cfg, 0, label="counts")
    add_k = {}
    for n, model in models.items():
        k = min(cfg.ks, key=lambda k: -np.log2(model.probabilities(val, k)).mean())
        add_k[n] = -np.log2(model.probabilities(test, k)).mean()
        if n not in cfg.orders:
            continue
        seen = -np.log2(model.probabilities(train_ids)).mean()
        unseen = (model.counts(test)[1] == 0).mean()
        print(f"   {n:7d} {len(model.contexts):13,d} {float(V) ** n:9.3g} {len(model.pairs):10,d} "
              f"{len(model.pairs) / float(V) ** (n + 1):9.2e} {100 * unseen:13.1f}% {seen:8.3f} {add_k[n]:7.3f} {k:6g}")
        run.log(context=n, contexts=len(model.contexts), pairs=len(model.pairs), unseen=unseen, train_bits=seen,
                test_bits=add_k[n], k=k)

    print("\n2. Deleted interpolation: the count models of every context up to n mixed, weights fit on the "
          "validation text")
    interpolated = {}
    for n in range(1, longest + 1):
        interpolated[n], weights = mixed_counts(models, val, test, n)
        if n in cfg.orders or n in cfg.contexts:
            print(f"   up to {n}: test {-np.log2(interpolated[n]).mean():.3f}   weights, context 0 to {n}: "
                  + " ".join(f"{w:.3f}" for w in weights))
    run.finish(add_k={str(n): b for n, b in add_k.items()},
               interpolated={str(n): float(-np.log2(p).mean()) for n, p in interpolated.items()})

    train_t, test_t = (torch.from_numpy(a).to(dev) for a in (train_ids, test))
    print(f"\n3. The network (embeddings of {cfg.embed}, {cfg.hidden} tanh units, {cfg.steps} steps of "
          f"{cfg.batch}, {cfg.seeds} seed{'s' * (cfg.seeds > 1)}) against counting, bits per character on the test text")
    print(f"   {'context':>7s}  {'network':49s} {'add-k':>6s} {'interp.':>7s}  network and interp., half each")
    nets, results, curves = {}, {}, []
    for i, n in enumerate(cfg.contexts):
        rows, mixes = [], []
        for seed in range(cfg.seeds):
            run = lab.Run(cfg, seed, label=f"context{n}")
            model = train(cfg, n, run, dev, train_t, V)
            rows.append(context_bits(model, test_t, n))
            mixes.append(float(-np.log2((chances(model, test_t, n) + interpolated[n]) / 2).mean()))
            embedding = {"embedding": model.embed.weight.tolist()} if seed == 0 and n == max(cfg.contexts) else {}
            run.finish(test_bits=rows[-1], mixed_bits=mixes[-1], **embedding)
            nets.setdefault(n, model)
            curves.append(lab.Line(f"context {n}", [r["step"] for r in run.rows], [r["bits"] for r in run.rows], i, 0.7))
        results[n] = rows
        print(f"   {n:7d}  {lab.spread(rows, 4):49s} {add_k[n]:6.3f} {-np.log2(interpolated[n]).mean():7.3f}  "
              f"{lab.spread(mixes, 4)}")
    for n in cfg.contexts:
        counted = -np.log2(interpolated[n]).mean()
        print(f"   context {n}: the network {lab.mean(results[n]) - counted:+.3f} bits from interpolation, lower in "
              f"{sum(r < counted for r in results[n])} of {cfg.seeds} seeds; {lab.mean(results[n]) - add_k[n]:+.3f} "
              f"from add-k")
    path = lab.lines(f"{cfg.out}/{cfg.name}/training.svg", curves, title="the network: bits per character of each batch",
                     xlabel="step", ylabel="bits per character")
    print(f"   curves in {path}")

    n = max(cfg.contexts)
    vocab = shakespeare.chars()
    among = [int(i) for i in np.flatnonzero(np.bincount(train_ids, minlength=V) >= cfg.common)]
    print(f"\n4. Nearest characters by embedding (context {n}, seed 0), cosine similarity, among the {len(among)} "
          f"characters seen at least {cfg.common} times in training\n   (two random vectors of {cfg.embed} numbers: "
          f"similarities spread with a standard deviation of 1/sqrt({cfg.embed}) = {cfg.embed ** -0.5:.2f})")
    for c in cfg.near:
        print(f"   {c!r:5s} " + "  ".join(f"{vocab[i]!r} {s:.2f}" for i, s in nearest(nets[n], vocab.index(c), among)))

    model = nets[n].eval()
    prompt = shakespeare.encode("\n" * n).tolist()
    drawn = sample(lambda ids: model(ids[None, -n:].to(dev))[0], prompt, cfg.length, torch.Generator().manual_seed(0))
    print(f"\n5. {cfg.length} characters drawn from the network (context {n}, seed 0):\n")
    print("\n".join(("   " + line).rstrip() for line in shakespeare.decode(drawn).split("\n")))
    print(f"\n{lab.clock(torch, dev) - start:.0f} s of counting, training and scoring on {dev.type}")


if __name__ == "__main__":
    main()
