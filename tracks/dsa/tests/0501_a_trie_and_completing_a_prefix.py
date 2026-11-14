"""05.01 A trie, and completing a prefix

spell prints the words of a text that are not in the dictionary, once each in byte order, as the
pipeline tr | grep .. | sort -u | comm -23 prints them, with the dictionary in a list, a hash table
or a trie; and -p completes a prefix as look does. A lookup in the list looks at every word before
the one it finds (all of them for a word that is not there); the trie steps down one node a letter,
and a prefix's words are the subtree below its node.
"""


def test(t):
    T = t.track
    fx = T.fixtures("spell")
    book = T.data(t, "book.txt")
    words = fx.dictionary(t)
    t.check(len(words) == 60388 and words == sorted(set(words)), f"the dictionary: {len(words)} words")

    # the book, with the trie and with the table, as the model and the pipeline say
    for algo in ("trie", "table"):
        r = fx.check(t, book, [f"--algo={algo}"])
        s = T.stats(r.err)["spell"]
        t.check(s["words"] == len(fx.text_words(book)) and s["unknown"] == len(r.lines()), f"the book: {s}")

    # the list on the first 1500 lines of the book (the whole book takes it seconds)
    with open(book) as f:
        part = T.write(t, "part.txt", "".join(f.readlines()[:1500]))
    r = fx.check(t, part, ["--algo=list"])
    checked = [w for w in fx.text_words(part) if len(w) > 1]
    first = {}
    for i, w in enumerate(words):
        first.setdefault(w, i)
    want = sum(first[w] + 1 if w in first else len(words) for w in checked)
    s = T.stats(r.err)["spell"]
    t.check(s["checked"] == len(checked), f"every word of two letters or more is checked: {s}")
    t.check(s["scanned"] == want, f"the list looks at each word up to the one it finds, every word when it "
                                  f"is not there: {want} in all, not {s['scanned']}")
    t.check("trie" not in T.stats(r.err) and "table" not in T.stats(r.err), f"the list is all it uses: {r.err}")

    # the trie: a node for each different prefix (and the root), one step down per letter
    r = fx.check(t, part, ["--algo=trie"])
    s, tr = T.stats(r.err)["spell"], T.stats(r.err)["trie"]
    prefixes = {w[:i] for w in words for i in range(1, len(w) + 1)}
    t.check(tr["nodes"] == len(prefixes) + 1 and tr["words"] == len(set(words)),
            f"{len(prefixes)} different prefixes and the root: {tr}")
    walked = 0
    for w in checked:
        i = 0
        while i < len(w) and w[:i + 1] in prefixes:
            i += 1
        walked += i
    t.check(tr["nodes visited"] == walked,
            f"a lookup steps down a node a letter, until a letter has no child: {walked}, not {tr}")
    t.check(s["scanned"] == 0 and tr["bytes"] >= tr["nodes"] * 105 and s["dict bytes"] == tr["bytes"],
            f"the trie's own bytes, 26 children a node: {s} {tr}")

    # completing a prefix: the same words three ways, and look's
    for prefix in ("zygot", "qu", "holm", "x", "", "xyzzy", "Cat", "abed", "z", "oxen"):
        rs = [fx.complete(t, prefix, [f"--algo={a}"]) for a in ("trie", "list", "table")]
        p = prefix.lower()
        under = [w for w in set(words) if w.startswith(p)]
        below = {w[:i] for w in under for i in range(len(p) + 1, len(w) + 1)}
        if under:
            want = len(p) + len(below)
        else:
            want = 0
            while want < len(p) and p[:want + 1] in prefixes:
                want += 1
        tr = T.stats(rs[0].err)["trie"]
        t.check(tr["nodes visited"] == want,
                f"-p {prefix!r}: a walk down the prefix, then the {len(below)} nodes below it: {want}, not {tr}")
        for r in rs[1:]:
            t.check(T.stats(r.err)["spell"]["scanned"] == len(words), f"-p {prefix!r} without a trie looks at "
                                                                       f"every word: {T.stats(r.err)}")

    # dictionaries of one's own: -d twice, capitals, a line that is not a word, a CRLF, a word twice
    d1 = T.write(t, "d1.txt", "Cat\ncart\r\ncar\nit's\n\ndog\nzebra\n")
    d2 = T.write(t, "d2.txt", "cat\nant\n42\nAnt\n")
    mine = fx.dictionary(t, d1) + fx.dictionary(t, d2)
    text = T.write(t, "text.txt", "The cat and the ant: a CAR, cars, carts, Zebra-dog; it's it.\n")
    for algo in ("list", "table", "trie"):
        args = [f"--algo={algo}", "-d", d1, f"-d{d2}"]
        r = fx.check(t, text, args, mine)
        t.check(T.stats(r.err)["spell"]["dict words"] == len(mine), f"{mine}: {T.stats(r.err)['spell']}")
        for prefix in ("ca", "an", "", "q"):
            fx.complete(t, prefix, args, mine)

    # standard input, and several files
    r = T.run(t, "spell", ["-", part], input="Holmes zzyzx\n")
    t.check(r.lines() == sorted(set(fx.unknown(t, part) + ["zzyzx"])), f"spell - part.txt:\n{r}")

    # the trace: a line a step
    small = T.write(t, "small.txt", "car\ncart\ncat\n")
    r = T.run(t, "spell", ["-d", small], input="cab\n", env={"DS_TRACE": "1"})
    want = ['trace: trie: add "car": c -> 1 new', 'trace: trie: add "car": a -> 2 new',
            'trace: trie: add "car": r -> 3 new, a word', 'trace: trie: add "cart": c -> 1',
            'trace: trie: add "cart": a -> 2', 'trace: trie: add "cart": r -> 3',
            'trace: trie: add "cart": t -> 4 new, a word', 'trace: trie: add "cat": c -> 1',
            'trace: trie: add "cat": a -> 2', 'trace: trie: add "cat": t -> 5 new, a word',
            'trace: trie: has "cab": c -> 1', 'trace: trie: has "cab": a -> 2',
            'trace: trie: has "cab": b -> none', 'trace: trie: has "cab": no']
    t.check(r.err.splitlines() == want and r.out == "cab\n", f"DS_TRACE=1:\n{r}")

    # errors are ordinary: status 2, a message
    for args in (["--algo=bogo"], ["-p"], ["-d", "/no/such/file"], ["--frobnicate"], ["-x"],
                 ["-p", "a", book], ["/no/such/file"]):
        r = T.run(t, "spell", args, check=False)
        t.check(r.rc == 2 and r.err.startswith("spell: ") and r.out == "", f"spell {' '.join(args)}:\n{r}")
