"""A recurrent network, and how it forgets.

07.02's network reads a fixed number of characters; to read more it needs
more weights, and in 07.02's long run 8 characters did no better than 5.
A recurrent network reads one character at a time into a state, a vector
it keeps, with the same weights at every step (models/rnn.py), so in
principle it can use everything it has read. Here, on Tiny Shakespeare:

1. a recurrent network over embeddings of the characters, trained with
   truncated backpropagation through time: the text read in pieces, the
   state carried from piece to piece but the gradient cut at each piece's
   start; bits per character on the test text, a few seeds, beside the
   best count model of 07.02;
2. how much of what it reads it uses: the bits when only the last w of
   the characters it reads before each one are the real ones, the rest
   taken from another place in the text, for growing w;
3. the recall task: a symbol shown first must be given back after T
   steps of blanks; accuracy against T, a few seeds;
4. why: the size of the gradient that reaches an input k steps back
   (Bengio, Simard and Frasconi, 1994; Pascanu, Mikolov and Bengio,
   2013), in the recall network as it starts, with its recurrent weights
   rescaled to other spectral radii, and in the trained text network;
5. text drawn from it.

    python3 -m experiments.rnn
"""

import numpy as np
import torch
from torch import nn
import torch.nn.functional as F

import lab
from data import shakespeare
from experiments.sequences import bits, contexts, sample, window_bits, windows
from models.ngram import NGram, mixture_weights
from models.rnn import RNN

CONFIG = dict(embed=32, hidden=256, steps=600, batch=64, length=64, lr=0.005, clip=1.0, seeds=3, span=1024, warm=64,
              reads=[0, 1, 2, 4, 8, 16, 32, 64], symbols=8, recall_embed=16, recall_hidden=64, recall_steps=300,
              recall_batch=64, recall_opt="sgd", recall_lr=0.1, delays=[2, 5, 10, 20, 40], radii=[0.5, 1.0, 2.0, 3.0],
              back=[0, 5, 10, 20, 40, 60], orders=5, drawn=300, device="cpu")


# @build 07.03 CharRNN
# The recurrent network of the next character: each character's embedding
# (07.02), a recurrent network over them (models/rnn.py), and a Linear
# layer from its state at every step to scores for the character after
# that step. x is (batch, steps) of character numbers; the state starts at
# h (zeros when None). Returns the scores, (batch, steps, V), and the last
# state.
class CharRNN(nn.Module):
    def __init__(self, V, embed, hidden):
        super().__init__()
        self.embed = nn.Embedding(V, embed)
        self.rnn = RNN(embed, hidden)
        self.out = nn.Linear(hidden, V)

    def forward(self, x, h=None):
        states, h = self.rnn(self.embed(x), h)
        return self.out(states), h
# @end


# @build 07.03 train
# Truncated backpropagation through time, one seed: the training text cut
# into cfg.batch streams laid end to end, all read together cfg.length
# characters at a time (windows), the state carried from one piece to the
# next but detached from the graph, so backward goes back cfg.length steps
# at most; at the end of the streams, back to their starts with no state.
# Adam at cfg.lr, falling to 0 along half a cosine (03.05). Each gradient's
# length is measured, and scaled down to cfg.clip when it is longer and
# cfg.clip is not 0 (clip_grad_norm_). Every 50 steps the batch's bits and
# that length go to the run's log. Returns the model and every length.
def train(cfg, run, dev, ids, V):
    torch.manual_seed(run.seed)
    model = CharRNN(V, cfg.embed, cfg.hidden).to(dev)
    opt = torch.optim.Adam(model.parameters(), lr=cfg.lr)
    scheduler = torch.optim.lr_scheduler.LambdaLR(opt, lab.warmup_cosine(0, cfg.steps))
    stream = (len(ids) - 1) // cfg.batch
    starts = torch.arange(cfg.batch, device=dev) * stream
    h, at, norms = None, 0, []
    for step in range(cfg.steps):
        if at + cfg.length > stream:
            h, at = None, 0
        x, y = windows(ids, starts + at, cfg.length)
        at += cfg.length
        scores, h = model(x, h)
        h = h.detach()
        loss = bits(scores, y)
        opt.zero_grad()
        loss.backward()
        norms.append(torch.nn.utils.clip_grad_norm_(model.parameters(), cfg.clip or float("inf")).item())
        opt.step()
        scheduler.step()
        if step % 50 == 0 or step == cfg.steps - 1:
            run.log(step=step, bits=loss.item(), gradient=norms[-1])
    return model, norms
# @end


# @build 07.03 recall_task
# n sequences of the recall task, as tensors on dev: a symbol from 0 to
# symbols - 1 drawn by rng, then `delay` blanks (the symbol numbered
# `symbols`); the answer to each is its first symbol.
def recall_task(n, delay, symbols, rng, dev):
    first = rng.integers(0, symbols, n)
    x = np.full((n, delay + 1), symbols)
    x[:, 0] = first
    return torch.from_numpy(x).to(dev), torch.from_numpy(first).to(dev)
# @end


# @build 07.03 Recall
# The recall network: the symbols' embeddings, a recurrent network over
# them, and a Linear layer from its last state to a score for each
# symbol: its answer comes after the whole sequence.
class Recall(nn.Module):
    def __init__(self, symbols, embed, hidden):
        super().__init__()
        self.embed = nn.Embedding(symbols + 1, embed)
        self.rnn = RNN(embed, hidden)
        self.out = nn.Linear(hidden, symbols)

    def forward(self, x):
        return self.out(self.rnn(self.embed(x))[1])
# @end


# @build 07.03 train_recall
# One recall network, one seed, one delay: plain gradient descent with
# momentum 0.9 (03.02), as the papers have it, at cfg.recall_lr (or Adam,
# with cfg.recall_opt "adam"), for cfg.recall_steps steps, each on a new
# batch of the task, the gradient clipped as the text network's is.
# Returns the model and its accuracy on 1000 new sequences.
def train_recall(cfg, delay, run, dev):
    torch.manual_seed(run.seed)
    model = Recall(cfg.symbols, cfg.recall_embed, cfg.recall_hidden).to(dev)
    if cfg.recall_opt == "adam":
        opt = torch.optim.Adam(model.parameters(), lr=cfg.recall_lr)
    else:
        opt = torch.optim.SGD(model.parameters(), lr=cfg.recall_lr, momentum=0.9)
    for step in range(cfg.recall_steps):
        x, y = recall_task(cfg.recall_batch, delay, cfg.symbols, run.rng, dev)
        loss = F.cross_entropy(model(x), y)
        opt.zero_grad()
        loss.backward()
        norm = torch.nn.utils.clip_grad_norm_(model.parameters(), cfg.clip or float("inf"))
        opt.step()
        if step % 50 == 0 or step == cfg.recall_steps - 1:
            run.log(step=step, loss=loss.item(), gradient=norm.item())
    x, y = recall_task(1000, delay, cfg.symbols, run.rng, dev)
    with torch.no_grad():
        return model, (model(x).argmax(1) == y).float().mean().item()
# @end


# @build 07.03 gradient_back
# How much of the gradient reaches each earlier input: the network's
# inputs, the embeddings of x, made a tensor of their own that needs a
# gradient, run through model.rnn; the cross-entropy of model.out on the
# last state for the answers y; torch.autograd.grad of it with respect to
# the inputs (the weights' .grad is left alone); and the mean over the
# batch of the length of that gradient at each step, k steps back from the
# last (k = 0 the last input, the first input last).
def gradient_back(model, x, y):
    e = model.embed(x).detach().requires_grad_()
    loss = F.cross_entropy(model.out(model.rnn(e)[1]), y)
    (g,) = torch.autograd.grad(loss, e)
    return g.norm(dim=2).mean(dim=0).flip(0)
# @end


def radius(w):
    """The spectral radius of a square matrix: the largest size of its eigenvalues."""
    return torch.linalg.eigvals(w.detach().cpu().double()).abs().max().item()


def counted(V, train_ids, val, test, n):
    """07.02's best count model: deleted interpolation of the contexts up to n characters, test bits."""
    models = [NGram(train_ids, j, V) for j in range(n + 1)]

    def rows(ids):
        return np.stack([models[j].probabilities(ids)[n - j:] for j in range(n + 1)])
    return float(-np.log2(mixture_weights(rows(val)) @ rows(test)).mean())


def main():
    cfg = lab.config(CONFIG)
    dev = lab.device(torch, cfg.device)
    V = len(shakespeare.chars())
    train_ids, val, test = (shakespeare.split(s) for s in ("train", "val", "test"))
    train_t, test_t = (torch.from_numpy(a).to(dev) for a in (train_ids, test))
    start = lab.clock(torch, dev)

    print(f"1. A recurrent network of the next character (embeddings of {cfg.embed}, a state of {cfg.hidden}), "
          f"{cfg.steps} steps of {cfg.batch} streams x {cfg.length} characters,\n   Adam {cfg.lr}, gradient clipped to "
          f"{cfg.clip or 'nothing'}; bits per character on the test text, every character with {cfg.warm} or more "
          f"before it")
    results, nets = [], []
    for seed in range(cfg.seeds):
        run = lab.Run(cfg, seed, label="text")
        model, norms = train(cfg, run, dev, train_t, V)
        results.append(window_bits(lambda x: model(x)[0], test_t, cfg.span, cfg.warm))
        clipped = sum(n > cfg.clip for n in norms) if cfg.clip else 0
        run.finish(test_bits=results[-1], largest_gradient=max(norms), clipped=clipped)
        nets.append(model)
        print(f"   seed {seed}: {results[-1]:.3f} bits; gradient length before clipping: median {np.median(norms):.2f}, "
              f"largest {max(norms):.2f}, {clipped} of {cfg.steps} steps clipped")
    best = counted(V, train_ids, val, test, cfg.orders)
    print(f"   the recurrent network: {lab.spread(results, 4)}")
    print(f"   07.02's best count model (deleted interpolation, contexts up to {cfg.orders}): {best:.3f}")

    model = nets[0].eval()
    longest = max(cfg.reads)
    print(f"\n2. What it uses: bits per character on the test text, each character read after {longest} others of "
          f"which only the last w are\n   the ones before it; the rest come from another place in the text (seed 0)")
    positions = torch.arange(longest, len(test_t), 4, device=dev)
    real, y = contexts(test_t, positions, longest)
    other, _ = contexts(test_t, positions[torch.from_numpy(np.random.default_rng(0).permutation(len(positions)))],
                        longest)
    for w in cfg.reads:
        x = torch.where(torch.arange(longest, device=dev) >= longest - w, real, other)
        with torch.no_grad():
            got = bits(model(x)[0][:, -1], y).item()
        print(f"   w = {w:3d}: {got:.3f}")

    print(f"\n3. The recall task: a symbol (one of {cfg.symbols}), then T blanks; the answer is the symbol "
          f"(chance {1 / cfg.symbols:.3f}).\n   A state of {cfg.recall_hidden}, {cfg.recall_steps} steps of "
          f"{cfg.recall_batch}, {'Adam' if cfg.recall_opt == 'adam' else 'SGD with momentum 0.9'} at {cfg.recall_lr}; "
          f"accuracy on 1000 new sequences")
    for delay in cfg.delays:
        accuracy = []
        for seed in range(cfg.seeds):
            run = lab.Run(cfg, seed, label=f"recall{delay}")
            accuracy.append(train_recall(cfg, delay, run, dev)[1])
            run.finish(accuracy=accuracy[-1])
        print(f"   T = {delay:3d}: {lab.spread(accuracy)}")

    deepest = max(cfg.back)
    rng = np.random.default_rng(0)
    print(f"\n4. The gradient that reaches the input k steps back, the answer {deepest} steps after the symbol "
          f"(mean over 256 sequences)")
    print(f"   {'recurrent weights':34s} {'radius':>6s}  " + " ".join(f"{f'k = {k}':>9s}" for k in cfg.back))
    x, y = recall_task(256, deepest, cfg.symbols, rng, dev)
    torch.manual_seed(0)
    fresh = Recall(cfg.symbols, cfg.recall_embed, cfg.recall_hidden).to(dev)
    rows = [("the recall network, as it starts", fresh)]
    for r in cfg.radii:
        scaled = Recall(cfg.symbols, cfg.recall_embed, cfg.recall_hidden).to(dev)
        scaled.load_state_dict(fresh.state_dict())
        with torch.no_grad():
            scaled.rnn.cell.hh.weight *= r / radius(scaled.rnn.cell.hh.weight)
        rows.append((f"  rescaled to radius {r:g}", scaled))
    for name, net in rows:
        g = gradient_back(net, x, y)
        print(f"   {name:34s} {radius(net.rnn.cell.hh.weight):6.2f}  " + " ".join(f"{g[k]:9.2e}" for k in cfg.back))
    windows_x, windows_y = windows(test_t, torch.arange(0, 256 * 97, 97, device=dev), deepest + 1)
    g = gradient_back(model, windows_x, windows_y[:, -1])
    print(f"   {'the text network, trained (seed 0)':34s} {radius(model.rnn.cell.hh.weight):6.2f}  "
          + " ".join(f"{g[k]:9.2e}" for k in cfg.back))

    prompt = shakespeare.encode("\n").tolist()

    class Reader:
        """next_scores for sample: reads only the numbers it has not read yet into its state."""
        h, read = None, 0

        def __call__(self, ids):
            scores, self.h = model(ids[None, self.read:].to(dev), self.h)
            self.read = len(ids)
            return scores[0, -1]
    drawn = sample(Reader(), prompt, cfg.drawn, torch.Generator().manual_seed(0))
    print(f"\n5. {cfg.drawn} characters drawn from the recurrent network (seed 0):\n")
    print("\n".join(("   " + line).rstrip() for line in shakespeare.decode(drawn).split("\n")))
    print(f"\n{lab.clock(torch, dev) - start:.0f} s of training and scoring on {dev.type}")


if __name__ == "__main__":
    main()
