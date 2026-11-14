"""01.01 A growable array

freq --algo=list, its words in a growable array and found by looking at each in turn, gives the
counts of tr | sort | uniq -c | sort -rn, every word of the book in the same order; and the array
doubles when full: a word of 100000 letters is pushed one letter at a time with about log2(n)
grows, and every element is copied fewer than twice.
"""


def test(t):
    T = t.track
    fx = T.fixtures("freq")
    book = T.data(t, "book.txt")
    r = fx.check(t, book, ["--algo=list", "--top=select"], n=0)
    t.check(len(r.lines()) > 7000, f"the book has more than 7000 different words, freq found {len(r.lines())}")
    fx.check(t, book, ["--algo=list", "--top=select"])
    fx.check(t, book, ["--algo=list", "--top=select"], n=3)
    fx.check(t, T.write(t, "punct.txt", "...it's IT, it's -- it!\n\"Its\" its; i.t.\n"),
             ["--algo=list", "--top=select"], n=0)

    # standard input and several files count together; no letters, no words
    alone = {w: c for c, w in fx.counts(T.run(t, "freq", ["--algo=list", "-n", "0", book]).out)}
    r = T.run(t, "freq", ["--algo=list", "-n", "0", "-", book], input="Holmes holmes HOLMES\n")
    both = {w: c for c, w in fx.counts(r.out)}
    t.check(both["holmes"] == alone["holmes"] + 3 and len(both) == len(alone),
            f"freq - book.txt: holmes {alone['holmes']} times in the book, {both['holmes']} with the 3 more")
    r = T.run(t, "freq", ["--algo=list"], input="1234 -- !!\n")
    t.check(r.out == "", f"freq on no words printed {r.out!r}")

    # the array: a word of 100000 letters, pushed a letter at a time, into an array that doubles
    r = T.run(t, "freq", ["--algo=list"], input="x" * 100000 + "\n", env={"DS_STATS": "1"})
    t.check(fx.counts(r.out) == [(1, "x" * 100000)], "a word of 100000 letters is one word")
    a = T.stats(r.err)["array"]
    t.check(a["pushes"] >= 100000, f"a letter at a time: {a}")
    t.check(a["moves"] < 2 * a["pushes"], f"doubling copies each element fewer than twice on average: {a}")
    t.check(a["grows"] <= 20, f"100000 letters need about log2(100000/8) = 14 grows, not {a['grows']}: {a}")

    # every word is looked for in the list: the probes are the words read times the list so far
    r = T.run(t, "freq", ["--algo=list", book], env={"DS_STATS": "1"})
    f = T.stats(r.err)["freq"]
    t.check(f["words"] > 100000 and f["distinct"] > 7000, f"the book: {f}")
    t.check(f["list probes"] > 50 * f["words"], f"the list is searched from the start for every word: {f}")

    # options of later lessons and bad ones are ordinary errors
    r = T.run(t, "freq", ["-n", "x", book], check=False)
    t.check(r.rc == 2 and "-n wants a count" in r.err, f"freq -n x:\n{r}")
    r = T.run(t, "freq", ["--algo=tree", book], check=False)
    t.check(r.rc == 2 and "no --algo 'tree'" in r.err, f"freq --algo=tree:\n{r}")
