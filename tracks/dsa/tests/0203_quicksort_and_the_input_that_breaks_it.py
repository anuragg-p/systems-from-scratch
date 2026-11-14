"""02.03 Quicksort, and the input that breaks it

Both quicksorts print the system's bytes. quick-first, the first line as the pivot, makes n(n-1)/2
comparisons on lines already in order and on lines that are all the same. quick, with a random pivot
and a three-way split, makes fewer than 2n*log2(n) on those and on lines in no order, and on lines
all the same exactly n-1: one pass puts every line equal to the pivot in its place.
"""

import math


def test(t):
    T = t.track
    fx = T.fixtures("sort")
    path = T.write(t, "random.txt", fx.random_lines(t, 4, 600))
    for algo in ("quick-first", "quick"):
        for args in fx.FLAGS:
            fx.check(t, args, path, algo=algo)
    words = T.gen(t, "words", 30000)                 # the book's words: a few of them very many times
    for args in ([], ["-r"], ["-u"]):
        fx.check(t, args, words, algo="quick")

    n = 2000
    got = {}
    for algo in ("quick-first", "quick"):
        for kind in ("sorted", "same", "lines"):
            r = fx.check(t, [], T.gen(t, kind, n), env={"DS_STATS": "1"}, algo=algo)
            got[algo, kind] = T.stats(r.err)["sort"]["comparisons"]
    worst = n * (n - 1) // 2
    t.check(got["quick-first", "sorted"] == worst and got["quick-first", "same"] == worst,
            f"the first line as the pivot: n(n-1)/2 = {worst} comparisons on sorted or equal lines: {got}")
    bound = 2 * n * math.log2(n)
    t.check(all(got["quick", k] < bound for k in ("sorted", "same", "lines")),
            f"a random pivot: under 2n*log2(n) = {bound:.0f} on any of them: {got}")
    t.check(got["quick", "same"] == n - 1, f"a three-way split: n-1 comparisons on equal lines: {got}")
