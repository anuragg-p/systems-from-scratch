"""02.04 A heap, and the top ten without sorting everything

Heapsort prints the system's bytes in at most 2n*log2(n) comparisons. freq --top=heap prints the
pipeline's top ten, top thousand and every word; for the top thousand of a text of 14000 different
words it makes under a tenth of the comparisons --top=select makes; and the heap never holds more
than the thousand.
"""

import math


def test(t):
    T = t.track
    fx = T.fixtures("sort")
    path = T.write(t, "random.txt", fx.random_lines(t, 5, 600))
    for args in fx.FLAGS:
        fx.check(t, args, path, algo="heap")
    n = 20000
    for kind in ("lines", "sorted", "same"):
        r = fx.check(t, [], T.gen(t, kind, n), env={"DS_STATS": "1"}, algo="heap")
        h = T.stats(r.err)["heap"]
        t.check(h["comparisons"] <= 2 * n * math.log2(n), f"heapsort on {kind}: at most 2n*log2(n): {h}")

    freq = T.fixtures("freq")
    book = T.data(t, "book.txt")
    for k in (10, 1000, 0):
        freq.check(t, book, ["--top=heap"], n=k)
    text = T.gen(t, "text", 100000)
    got = {}
    for top in ("select", "heap"):
        r = freq.check(t, text, [f"--top={top}"], n=1000)
        got[top] = T.stats(T.run(t, "freq", [f"--top={top}", "-n", "1000", text], env={"DS_STATS": "1"}).err)
    sel, hp = got["select"]["freq"]["rank comparisons"], got["heap"]["freq"]["rank comparisons"]
    t.check(hp * 10 < sel, f"the top 1000 with a heap: under a tenth of select's comparisons: {hp} against {sel}")
    h = got["heap"]["heap"]
    t.check(h["pushes"] - h["pops"] == 0 and h["pushes"] >= 1000, f"every word pushed is popped: {h}")
