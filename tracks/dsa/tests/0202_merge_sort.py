"""02.02 Merge sort

sort --algo=merge (the default) prints the system's bytes for every option set on random lines, and
on 50000 generated lines; it makes at most n*ceil(log2 n) comparisons on any input, a little over
half that on input in order; and it is stable: with -u and a key, the line printed for each run of
equal keys is the first of them in the input, as the system's sort prints.
"""

import math


def test(t):
    T = t.track
    fx = T.fixtures("sort")
    path = T.write(t, "random.txt", fx.random_lines(t, 3, 1000))
    for args in fx.FLAGS:
        fx.check(t, args, path)
        fx.check(t, args, path, algo="merge")
    big = T.gen(t, "lines", 50000)
    for args in ([], ["-r"], ["-u"], ["-k2"]):
        fx.check(t, args, big)
    fields = T.gen(t, "fields", 20000)
    for args in (["-k2,2n"], ["-k3,3", "-k2,2nr"], ["-u", "-k1,1"], ["-u", "-k2,2n"]):
        fx.check(t, args, fields)

    n = 20000
    bound = n * math.ceil(math.log2(n))
    got = {}
    for kind in ("lines", "sorted", "reversed", "same"):
        r = fx.check(t, [], T.gen(t, kind, n), env={"DS_STATS": "1"}, algo="merge")
        got[kind] = T.stats(r.err)["sort"]["comparisons"]
    t.check(all(c <= bound for c in got.values()), f"merge sort: at most n*ceil(log2 n) = {bound}: {got}")
    t.check(got["sorted"] < 0.6 * bound, f"in order, each merge stops early: {got}")

    r = T.run(t, "sort", ["--algo=merge", "-u", "-k1,1"], input="b 1\na 2\nb 3\na 4\nc 5\n")
    t.check(r.out == "a 2\nb 1\nc 5\n", f"sort -u -k1,1 keeps the first of each key: {r.out!r}")
