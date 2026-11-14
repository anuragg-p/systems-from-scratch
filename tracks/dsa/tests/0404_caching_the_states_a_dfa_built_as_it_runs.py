"""04.04 Caching the states: a DFA built as it runs

grep -E --algo=dfa (the default), each set of NFA states made a state the first time the text leads to
it, prints the system's grep -E lines for the table, and agrees with Python's re on random
expressions, with the cache big enough and with room for one state. On the book a pattern needs a
handful of states, and after the first lines nearly every byte is one lookup. The cache is bounded: a
pattern that needs a state for every subset of its NFA's states fills it, the cache is emptied and
built again, and the lines are still right.
"""

import random


def test(t):
    T = t.track
    fx = T.fixtures("grep")
    fx.table(t, "-E", "dfa")
    fx.oracle(t, "dfa", 150, seed=5)
    fx.oracle(t, "dfa", 60, seed=6, args=["-i"])
    fx.oracle(t, "dfa", 60, seed=7, cache=1)

    # the default; and on the book, a few states and nearly all hits
    book = T.data(t, "book.txt")
    for pat in ("Holmes|Watson", "[A-Z][a-z]+ [A-Z][a-z]+", "^([A-Za-z]+ ?)*$"):
        r = fx.check(t, ["-E", "-c", pat], [book])
        d = T.stats(r.err)["dfa"]
        t.check(d["states built"] <= 60 and d["flushes"] == 0, f"{pat}: a handful of states on the book: {d}")
        t.check(d["hits"] + d["misses"] == d["examined"] and d["hits"] > 0.99 * d["examined"],
                f"{pat}: all but a few bytes of the book are a lookup: {d}")

    # a?^n a^n: one state for each byte, each built once
    pat, line = fx.expo(30)
    d = T.stats(T.run(t, "grep", ["-E", pat], input=line + "\n", env={"DS_STATS": "1"}).err)["dfa"]
    t.check(d["examined"] == 30 and d["states built"] == 31, f"a?^30a^30: 30 bytes, 31 states: {d}")

    # (a|b)*a(a|b)^k: a state for each of the last k+1 bytes there can be; the cache fills
    k = 10
    pat = "(a|b)*a" + "(a|b)" * k + "$"
    rng = random.Random(1)
    text = "".join("".join(rng.choice("ab") for _ in range(40)) + "\n" for _ in range(500))
    path = T.write(t, "ab.txt", text)
    big = T.stats(fx.check(t, ["-E", "-c", pat], [path]).err)["dfa"]
    t.check(big["states built"] > 1000 and big["flushes"] == 0,
            f"(a|b)*a(a|b)^{k}$ on 500 random lines: over a thousand states, all kept: {big}")
    small = T.stats(fx.check(t, ["-E", "-n", pat], [path], cache=64).err)["dfa"]
    t.check(small["flushes"] > 10 and small["states built"] > big["states built"],
            f"--cache=64: the cache fills, is emptied, and states are built again: {small}")

    # --cache wants a number
    for v in ("0", "x", ""):
        r = T.run(t, "grep", [f"--cache={v}", "a"], input="a\n", check=False)
        t.check(r.rc == 2 and "--cache wants" in r.err, f"grep --cache={v}:\n{r}")
