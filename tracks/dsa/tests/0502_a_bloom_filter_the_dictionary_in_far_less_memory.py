"""05.02 A Bloom filter: the dictionary in far less memory

spell --algo=bloom holds the dictionary in a Bloom filter sized from the false-positive rate asked
for: m = n ln(1/p) / (ln 2)^2 bits (then the next prime) and k = (m/n) ln 2 hashes. It never calls
a word of the dictionary unknown, so what it prints is part of the exact answer; the unknown words
it lets through are its false positives, and on words that are not in the dictionary their rate is
the formula's, (1 - e^(-kn/m))^k, within five standard deviations. It takes about a tenth of the
memory of the word list as text, and far less than the list, the table or the trie. It holds no
words, so -p is refused.
"""

import math


def is_prime(m):
    return m >= 2 and all(m % d for d in range(2, int(math.isqrt(m)) + 1))


def test(t):
    T = t.track
    fx = T.fixtures("spell")
    book = T.data(t, "book.txt")
    words = fx.dictionary(t)
    n = len(words)

    # the book: part of the exact answer, in order; the rest got through
    exact = fx.unknown(t, book)
    r = T.run(t, "spell", ["--algo=bloom", book], env={"DS_STATS": "1"})
    got = r.lines()
    t.check(got == sorted(set(got)) and set(got) <= set(exact),
            f"the filter calls no word of the dictionary unknown: {sorted(set(got) - set(exact))[:10]}")
    t.check(len(exact) - len(got) <= 0.03 * len(exact),
            f"about 1% of the {len(exact)} unknown words get through, not {len(exact) - len(got)}")
    s, b = T.stats(r.err)["spell"], T.stats(r.err)["bloom"]
    m, k = b["bits"], b["hashes"]
    t.check(b["keys"] == n and b["bits set"] == k * n and b["bits on"] <= b["bits set"],
            f"each word sets k bits: {b}")
    t.check(b["bits tested"] <= k * s["checked"] and b["bits tested"] >= s["checked"],
            f"a test looks at 1 to k bits, stopping at the first 0: {b}, {s['checked']} words checked")
    t.check(b["bytes"] == (m + 7) // 8 and s["dict bytes"] == b["bytes"], f"m bits in bytes: {b} {s}")
    t.check(abs(b["bits on"] / m - 0.5) < 0.02, f"with the best k, about half the bits are on: {b}")

    # sized from the rate: m the first prime from n ln(1/p) / (ln 2)^2, k = (m/n) ln 2
    for p in (0.1, 0.01, 0.001):
        b = T.stats(T.run(t, "spell", ["--algo=bloom", f"--fp={p}", "/dev/null"], env={"DS_STATS": "1"}).err)["bloom"]
        want_m = math.ceil(n * math.log(1 / p) / math.log(2) ** 2)
        t.check(is_prime(b["bits"]) and want_m <= b["bits"] < want_m + 200 and
                not any(is_prime(x) for x in range(want_m, b["bits"])),
                f"--fp={p}: m is the first prime from {want_m}: {b}")
        t.check(b["hashes"] == round(b["bits"] / n * math.log(2)), f"--fp={p}: k = (m/n) ln 2: {b}")
        f = fx.bloom_formula(n, b["bits"], b["hashes"])
        t.check(abs(f - p) < 0.06 * p, f"--fp={p}: the formula gives {f:.5f} for this m and k")

    # the false-positive rate, measured on words that are not in the dictionary, against the formula
    count = 40000
    path = T.write(t, "nonwords.txt", "".join(w + "\n" for w in fx.nonwords(count, words, 5)))
    for args in (["--fp=0.1"], ["--fp=0.01"], ["--fp=0.001"], ["--hashes=1"], ["--hashes=14"]):
        r = T.run(t, "spell", ["--algo=bloom"] + args + [path], env={"DS_STATS": "1"})
        b = T.stats(r.err)["bloom"]
        through = count - len(r.lines())
        f = fx.bloom_formula(n, b["bits"], b["hashes"])
        sd = math.sqrt(f * (1 - f) / count)
        t.check(abs(through / count - f) <= 5 * sd + 0.0002,
                f"{' '.join(args)}: {through} of {count} non-words got through ({through / count:.4f}); "
                f"the formula says {f:.4f} with m = {b['bits']}, k = {b['hashes']}")
    one = T.run(t, "spell", ["--algo=bloom", "--hashes=1", path])
    best = T.run(t, "spell", ["--algo=bloom", path])
    t.check(count - len(one.lines()) > 5 * (count - len(best.lines())),
            f"one hash lets far more through than the best k: {count - len(one.lines())} against "
            f"{count - len(best.lines())}")

    # memory, by each structure's own count: the filter is a small part of the text
    size = {}
    for algo in ("list", "table", "trie", "bloom"):
        sp = T.stats(T.run(t, "spell", [f"--algo={algo}", "/dev/null"], env={"DS_STATS": "1"}).err)["spell"]
        size[algo] = sp["dict bytes"]
        text = sp["dict text"]
    t.check(text == sum(len(w) + 1 for w in words), f"the list as text: {text} bytes")
    t.check(size["bloom"] * 7 < text < size["list"] < size["table"] < size["trie"],
            f"bytes: text {text}, {size}")
    t.check(size["bloom"] < 1.25 * n * 9.6 / 8, f"about 9.6 bits a word for 1%: {size['bloom']} bytes")

    # what it cannot do: list the words
    r = T.run(t, "spell", ["--algo=bloom", "-p", "ca"], check=False)
    t.check(r.rc == 2 and "holds no words" in r.err and r.out == "", f"spell --algo=bloom -p ca:\n{r}")
    for args in (["--fp=0"], ["--fp=1"], ["--fp=x"], ["--hashes=0"], ["--algo=bloom", "--hashes=2.5x"]):
        r = T.run(t, "spell", args + ["/dev/null"], check=False)
        t.check(r.rc == 2 and r.err.startswith("spell: "), f"spell {' '.join(args)}:\n{r}")

    # the trace: the bits a word sets, and those a test looks at
    small = T.write(t, "small.txt", "car\ncart\ncat\ndog\n")
    r = T.run(t, "spell", ["--algo=bloom", "-d", small], input="cat\n", env={"DS_TRACE": "1", "DS_STATS": "1"})
    b = T.stats(r.err)["bloom"]
    adds = [l for l in r.err.splitlines() if l.startswith("trace: bloom: add ")]
    test = [l for l in r.err.splitlines() if l.startswith("trace: bloom: test ")]
    t.check(len(adds) == 4 and all(len(set(l.split(": ")[-1].split())) == b["hashes"] for l in adds),
            f"one line an add, its k bits all different:\n{r.err}")
    t.check(len(test) == 1 and test[0].endswith(": yes") and test[0].count(" on") == b["hashes"],
            f"a test of a word that is in: all k bits on:\n{r.err}")
