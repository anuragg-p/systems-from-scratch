"""Counting pairs: a bigram model, and the loss to beat.

A language model guesses the next character: for every character that
could come, a chance, the chances adding up to 1. It is scored by how
surprised it was by the character that came, -log2 p bits (a sure
guess costs 0 bits, a fair coin's 1, one chance in 65 log2 65 = 6.02),
averaged over every character of text it never saw: bits per character,
the cross-entropy. 2 to that power is the perplexity, the number of
equally likely characters the model was as unsure as.

Here, on Tiny Shakespeare, the first rungs of the ladder every later
model has to beat, all by counting in the training text:

1. how one score is made, character by character, from the counts of
   pairs, and why one pair never seen makes it infinite;
2. smoothing: every count plus k, k chosen on the validation text;
3. the ladder on the test text: every character equally likely, single
   characters by their counts, each character by the one before it;
4. Shannon (1951)'s N-gram entropies of English beside ours: other
   text, another alphabet (his 26 letters and the space), so the text is
   also folded to his 27 symbols;
5. text drawn from the pair model.

Counting draws nothing at random: the numbers are exact, the same on
every run. Only the sample of part 5 depends on the seed.

    python3 -m experiments.bigram
"""

import math

import numpy as np

import lab
from data import shakespeare

CONFIG = dict(ks=[0.0, 1.0, 0.1, 0.01, 0.001], show=12, length=300, seed=0)

# Shannon (1951), "Prediction and Entropy of Printed English", the table on
# page 54: F0, F1, F2 of English with 26 letters and the space, in bits per
# letter, from published tables of letter and pair frequencies. (F3 is 3.1;
# from his guessing experiments, about one bit per letter with 100 letters
# known.)
SHANNON = (4.76, 4.03, 3.32)


# @build 07.01 pair_counts
# How often each character follows each other one in ids (character
# numbers, a numpy array): a table of V rows, the character before, by V
# columns, the character after; table[a, b] is the number of places in
# ids where b comes right after a.
def pair_counts(ids, V):
    table = np.zeros((V, V), dtype=np.int64)
    np.add.at(table, (ids[:-1], ids[1:]), 1)
    return table
# @end


# @build 07.01 probabilities
# Counts made into chances that add up to 1 along the last axis (a table's
# rows, or one row of single counts): (count + k) / (total + V k), V the
# number of columns. With k = 0 they are the counts' own proportions and a
# character never counted gets 0; with k > 0 every character gets a little,
# as if each had been seen k more times. A row with no counts at all and
# k = 0 stays all 0.
def probabilities(counts, k=0.0):
    counts = counts + k
    total = counts.sum(axis=-1, keepdims=True)
    return np.divide(counts, total, out=np.zeros(counts.shape), where=total > 0)
# @end


# @build 07.01 bits
# A model's score on a text, from p, the chance it gave each character
# that came: the mean of -log2 p, in bits per character. A character
# given p = 0 makes it infinite (numpy's log2(0) is -inf, without a
# warning here).
def bits(p):
    with np.errstate(divide="ignore"):
        return float(-np.log2(p).mean())
# @end


# @build 07.01 sample
# n characters drawn from the pair model probs (rows of chances): each
# next one from the row of the one before it, starting after `first`,
# with rng (a numpy Generator).
def sample(probs, first, n, rng):
    out = [first]
    for _ in range(n):
        out.append(int(rng.choice(len(probs), p=probs[out[-1]])))
    return out[1:]
# @end


def fold(text):
    """The text in Shannon's 27 symbols: letters made small, anything else a space, runs of spaces one."""
    small = "".join(c.lower() if c.isalpha() else " " for c in text)
    return " ".join(small.split())


def ladder(train, held, V, k):
    """Bits per character on held (character numbers) of the three models, counted on train."""
    singles = probabilities(np.bincount(train, minlength=V), k)
    pairs = probabilities(pair_counts(train, V), k)
    return math.log2(V), bits(singles[held]), bits(pairs[held[:-1], held[1:]])


def main():
    cfg = lab.config(CONFIG)
    run = lab.Run(cfg, cfg.seed)
    vocab = shakespeare.chars()
    V = len(vocab)
    train, val, test = (shakespeare.split(s) for s in ("train", "val", "test"))
    print(f"Tiny Shakespeare: {len(shakespeare.load()):,} characters, {V} different ones; by position, "
          f"train {len(train):,}, validation {len(val):,}, test {len(test):,}")
    table = pair_counts(train, V)
    first = table.sum(axis=1)
    print(f"pairs in the training text: {int(table.sum()):,}; of the {V} x {V} = {V * V} possible pairs, "
          f"{int((table > 0).sum())} occur")

    print(f"\n1. The pair model on the first {cfg.show} characters of the test text: p = count of the pair / "
          f"count of the first")
    print(f"   {'pair':8s} {'count':>6s} {'of':>7s} {'p':>8s} {'-log2 p':>8s}")
    ps = []
    for a, b in zip(test[:cfg.show], test[1:cfg.show + 1]):
        p = table[a, b] / first[a]
        ps.append(p)
        print(f"   {shakespeare.decode([a, b])!r:8s} {int(table[a, b]):6d} {int(first[a]):7d} {p:8.4f} "
              f"{-math.log2(p):8.3f}")
    print(f"   mean -log2 p over these {cfg.show}: {bits(np.array(ps)):.3f} bits a character; "
          f"2 ** {bits(np.array(ps)):.3f} = {2 ** bits(np.array(ps)):.2f}, the perplexity")
    raw = probabilities(table)[test[:-1], test[1:]]
    unseen = sorted({shakespeare.decode([a, b]) for a, b in zip(test[:-1], test[1:]) if table[a, b] == 0})
    print(f"   over all {len(test) - 1:,} pairs of the test text: {bits(raw)} bits. {int((raw == 0).sum())} of them, "
          f"{len(unseen)} different pairs, never occur in the training text: p = 0, and -log2 0 = inf")
    print(f"   never seen in training: {' '.join(repr(u) for u in unseen[:12])}{' ...' if len(unseen) > 12 else ''}")

    print("\n2. Every count plus k: p = (count of the pair + k) / (count of the first + 65 k), "
          "bits per character on the validation text")
    tried = {}
    for k in cfg.ks:
        tried[k] = bits(probabilities(table, k)[val[:-1], val[1:]])
        print(f"   k = {k:<6g} {tried[k]:.4f}")
        run.log(k=k, val_bits=tried[k])
    k = min(tried, key=tried.get)
    print(f"   chosen: k = {k:g}")

    print(f"\n3. The ladder: bits per character (perplexity), counts from the training text plus k = {k:g}")
    held, seen = ladder(train, test, V, k), ladder(train, train, V, 0.0)
    names = ("every character equally likely", "single characters, by their counts", "pairs: by the one before")
    print(f"   {'':36s} {'test':>15s}   {'training text, k = 0':>20s}")
    for name, h, s in zip(names, held, seen):
        print(f"   {name:36s} {h:6.3f} ({2 ** h:5.1f})   {s:6.3f} ({2 ** s:5.1f})")

    print("\n4. Shannon (1951): F0, F1, F2 of English, 26 letters and the space, in bits per letter, from tables of\n"
          "   letter and pair frequencies (each model scored on the text it was counted from, like our training column)")
    folded = fold(shakespeare.load()[:int(0.9 * len(shakespeare.load()))])
    alphabet = sorted(set(folded))
    number = {c: i for i, c in enumerate(alphabet)}
    ids27 = np.array([number[c] for c in folded], dtype=np.int64)
    ours27 = ladder(ids27, ids27, len(alphabet), 0.0)
    print(f"   {'':44s} {'F0':>6s} {'F1':>6s} {'F2':>6s}")
    print(f"   {'Shannon, English':44s} {SHANNON[0]:6.2f} {SHANNON[1]:6.2f} {SHANNON[2]:6.2f}")
    print(f"   {f'training text folded to {len(alphabet)} symbols':44s} " + " ".join(f"{b:6.2f}" for b in ours27))
    print(f"   {f'training text, its {V} characters':44s} " + " ".join(f"{b:6.2f}" for b in seen))

    pairs = probabilities(table, k)
    start = int(shakespeare.encode("\n")[0])
    text = shakespeare.decode(sample(pairs, start, cfg.length, run.rng))
    print(f"\n5. {cfg.length} characters drawn from the pair model (k = {k:g}, seed {cfg.seed}):\n")
    print("\n".join(("   " + line).rstrip() for line in text.split("\n")))
    run.finish(k=k, test_bits=dict(zip(("uniform", "singles", "pairs"), held)),
               train_bits=dict(zip(("uniform", "singles", "pairs"), seen)), folded=ours27, sample=text)


if __name__ == "__main__":
    main()
