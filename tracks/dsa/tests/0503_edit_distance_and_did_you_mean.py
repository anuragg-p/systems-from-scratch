"""05.03 Edit distance, and "did you mean"

spell --distance A B is Levenshtein's distance, the same as the whole table filled in Python, and
DS_TRACE=1 prints that table a row at a time. spell -s prints each unknown word with the
dictionary's nearest words (those at the smallest distance up to -e, in byte order, the first -n),
the same whether it computes the distance to every word (--near=scan) or walks the trie carrying
one row of the table, leaving out each subtree no near word can be in (--near=trie); the walk fills
a small part of the cells the scan fills. With a Bloom filter, the trie for the suggestions is built
only once a word needs them.
"""

import random


def table_rows(a, b):
    """The rows of the whole table, as DS_TRACE=1 prints them."""
    prev = list(range(len(a) + 1))
    out = [f"trace: edit: \"{a}\" \"{b}\"", "trace: edit: row 0 -: " + " ".join(map(str, prev))]
    for i, c in enumerate(b, 1):
        row = [i]
        for j in range(1, len(a) + 1):
            row.append(min(prev[j] + 1, row[j - 1] + 1, prev[j - 1] + (a[j - 1] != c)))
        out.append(f"trace: edit: row {i} {c}: " + " ".join(map(str, row)))
        prev = row
    return out + [f"trace: edit: distance {prev[-1]}"]


def test(t):
    T = t.track
    fx = T.fixtures("spell")
    words = fx.dictionary(t)

    # the distance, against the whole table; every cell filled once
    pairs = [("kitten", "sitting"), ("", ""), ("abc", ""), ("", "abc"), ("flaw", "lawn"),
             ("intention", "execution"), ("same", "same"), ("ab", "ba"), ("teh", "the"),
             ("recieve", "receive"), ("a", "b"), ("Holmes", "holmes")]
    rng = random.Random(3)
    for _ in range(50):
        pairs.append(tuple("".join(rng.choice("abc") for _ in range(rng.randint(0, 7))) for _ in range(2)))
    for a, b in pairs:
        r = T.run(t, "spell", ["--distance", a, b], env={"DS_STATS": "1"})
        want = fx.distance(a, b)
        e = T.stats(r.err)["edit"]
        t.check(r.out == f"{want}\n", f"--distance {a!r} {b!r}: {want}, not {r.out!r}")
        t.check(e["distances"] == 1 and e["rows"] == len(b) + 1 and e["cells filled"] == (len(a) + 1) * (len(b) + 1),
                f"--distance {a!r} {b!r}: a row for each letter of b and one more, a cell for each of a: {e}")
    r = T.run(t, "spell", ["--distance", "kitten", "sitting"], env={"DS_TRACE": "1"})
    t.check(r.err.splitlines() == table_rows("kitten", "sitting"), f"DS_TRACE=1, the table row by row:\n{r.err}")

    # suggestions on a text with typos, against a dictionary of every fourth word: scan and walk
    # print the same, and what the model says (checked on every third unknown word: the model is slow)
    small = words[::4]
    dpath = T.write(t, "quarter.txt", "".join(w + "\n" for w in small))
    text = T.gen(t, "typos", 400)
    unknown = fx.unknown(t, text, small)
    got = {}
    for near in ("scan", "trie"):
        r = T.run(t, "spell", ["-s", f"--near={near}", "-d", dpath, text], env={"DS_STATS": "1"})
        got[near] = r
        t.check([l.split(":")[0] for l in r.lines()] == unknown, f"-s --near={near}: a line for each unknown word")
    T.same(t, got["trie"].out, got["scan"].out, "-s: the walk and the scan")
    lines = got["trie"].lines()
    for u, line in list(zip(unknown, lines))[::3]:
        want = u + ":" + "".join(" " + w for w in fx.nearest(u, small))
        t.check(line == want, f"-s {u}: {want!r}, not {line!r}")
    scan, walk = T.stats(got["scan"].err)["edit"], T.stats(got["trie"].err)["edit"]
    t.check(scan["distances"] == len(unknown) * len(set(small)),
            f"the scan computes the distance to every word, for each of {len(unknown)} words: {scan}")
    t.check(walk["distances"] == 0 and walk["cells filled"] * 10 < scan["cells filled"],
            f"the walk fills a small part of the scan's cells: walk {walk}, scan {scan}")

    # the real dictionary, a few words, every way there is
    for word, args in (("speling", []), ("teh", []), ("recieve", ["-e", "1"]), ("holmes", ["-n", "0"]),
                       ("qzxj", ["-e", "1"]), ("quik", ["-n", "2"]), ("lazzy", ["-e", "2", "-n", "1"])):
        e = int(args[args.index("-e") + 1]) if "-e" in args else 2
        n = int(args[args.index("-n") + 1]) if "-n" in args else 5
        want = word + ":" + "".join(" " + w for w in fx.nearest(word, words, e, n)) + "\n"
        for way in (["--near=trie"], ["--near=scan"], ["--algo=list"], ["--algo=table"], ["--algo=bloom"]):
            r = T.run(t, "spell", ["-s"] + way + args, input=word + "\n")
            t.check(r.out == want, f"spell -s {' '.join(way + args)} on {word}: {want!r}, not {r.out!r}")

    # with the filter, the trie is built once a word needs suggestions, and only then
    r = T.run(t, "spell", ["--algo=bloom", "-s"], input="The cat sat.\n", env={"DS_STATS": "1"})
    t.check(r.out == "" and "trie" not in T.stats(r.err), f"no unknown word, no trie:\n{r}")
    r = T.run(t, "spell", ["--algo=bloom", "-s"], input="The cat sat on teh mat.\n", env={"DS_STATS": "1"})
    st = T.stats(r.err)
    t.check(r.out.startswith("teh: ") and st["trie"]["words"] == len(words) and st["spell"]["dict bytes"] < 100000,
            f"an unknown word: a trie for its suggestions; the filter's bytes are still the dictionary's:\n{r}")

    # the trace of the walk: a line a node, with its row
    d = T.write(t, "cats.txt", "car\ncart\ncat\ndog\n")
    r = T.run(t, "spell", ["-s", "-e", "1", "-d", d], input="cst\n", env={"DS_TRACE": "1"})
    walk = [l for l in r.err.splitlines() if l.startswith("trace: trie: near ")]
    t.check(r.out == "cst: cat\n" and 'trace: trie: near "ca" -> 2: 2 1 1 2, min 1' in walk
            and 'trace: trie: near "cat" -> 5: 3 2 2 1, min 1, a word at 1' in walk
            and 'trace: trie: near "d" -> 6: 1 1 2 3, min 1' in walk
            and 'trace: trie: near "do" -> 7: 2 2 2 3, min 2, pruned' in walk
            and not any('"dog"' in l for l in walk), f"DS_TRACE=1 -s:\n{r}")

    # ordinary errors
    for args in (["-s", "-e", "0"], ["-s", "-e", "4"], ["-s", "-n", "-1"], ["--near=bogo"],
                 ["-s", "--near=trie", "--algo=list"], ["--distance", "a"], ["--distance", "a", "b", "c"]):
        r = T.run(t, "spell", args, input="", check=False)
        t.check(r.rc == 2 and r.err.startswith("spell: ") and r.out == "", f"spell {' '.join(args)}:\n{r}")
