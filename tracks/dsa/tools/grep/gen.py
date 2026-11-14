"""grep's inputs for data/gen.py and bench/grow.py (module 04).

  ab     [lines] lines of 40 a's and b's at random: a DFA for (a|b)*a(a|b)(a|b)...
         needs a new state for most bytes of them
  runs   [lines] lines of 1000 a's: the worst case of a search that tries every
         position, for a string such as aa...ab
"""


def ab(n, rng):
    return b"".join(bytes(rng.below(2) + ord("a") for _ in range(40)) + b"\n" for _ in range(n))


def runs(n, rng):
    return (b"a" * 1000 + b"\n") * n


KINDS = {
    "ab": (ab, "lines", "lines of 40 random a's and b's"),
    "runs": (runs, "lines", "lines of 1000 a's"),
}
