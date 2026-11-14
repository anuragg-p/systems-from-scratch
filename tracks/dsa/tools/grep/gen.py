"""grep's inputs for data/gen.py and bench/grow.py (module 04).

  runs   [lines] lines of 1000 a's: on it, a search that tries every
         position for aa...ab compares the whole string at each one
  ab     [lines] lines of 40 a's and b's, each picked at random
"""


def runs(n, rng):
    return (b"a" * 1000 + b"\n") * n


def ab(n, rng):
    return b"".join(bytes(rng.below(2) + ord("a") for _ in range(40)) + b"\n" for _ in range(n))


KINDS = {
    "runs": (runs, "lines", "lines of 1000 a's"),
    "ab": (ab, "lines", "lines of 40 random a's and b's"),
}
