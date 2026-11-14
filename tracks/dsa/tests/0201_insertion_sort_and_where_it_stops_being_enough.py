"""02.01 Insertion sort, and where it stops being enough

sort --algo=insertion prints the system sort's bytes with LC_ALL=C: for thirty sets of -r -n -u -k
-t on short random lines full of ties, blanks, signs and points, and on the book. It is stable, so
with -u the first line of each run of equal keys is the one printed. It makes n-1 comparisons on
lines already in order, n(n-1)/2 on different lines in reverse order, and about n*n/4 on lines in
no order.
"""


def test(t):
    T = t.track
    fx = T.fixtures("sort")
    for seed in (1, 2):
        path = T.write(t, f"random{seed}.txt", fx.random_lines(t, seed, 300))
        for args in fx.FLAGS:
            fx.check(t, args, path, algo="insertion")
    book = T.data(t, "book.txt")
    for args in ([], ["-r"], ["-u"], ["-k2,2", "-k1,1r"]):
        fx.check(t, args, book, algo="insertion")

    # stable: equal keys stay in input order, so -u keeps the first of each
    r = T.run(t, "sort", ["--algo=insertion", "-u", "-k1,1"], input="b 1\na 2\nb 3\na 4\n")
    t.check(r.out == "a 2\nb 1\n", f"sort -u -k1,1 keeps the first of each key: {r.out!r}")

    # standard input, several files, a last line with no newline, nothing at all
    r = T.run(t, "sort", ["--algo=insertion", "-", book], input="zzz\nAAA")
    T.same(t, r.out, T.system(t, ["sort", "-", book], input="zzz\nAAA").out, "sort - book.txt")
    t.check(T.run(t, "sort", ["--algo=insertion"], input="").out == "", "sorting nothing prints nothing")

    # the comparisons: n-1 in order, n(n-1)/2 in reverse, about n*n/4 in no order
    n = 2000
    words = T.gen(t, "dict", n)
    with open(words) as f:
        lines = f.read().splitlines()
    rev = T.write(t, "reversed.txt", "".join(w + "\n" for w in reversed(lines)))
    mixed = T.gen(t, "lines", n)
    got = {}
    for name, path in (("sorted", words), ("reversed", rev), ("mixed", mixed)):
        r = T.run(t, "sort", ["--algo=insertion", path], env={"DS_STATS": "1"})
        got[name] = T.stats(r.err)["sort"]["comparisons"]
    t.check(got["sorted"] == n - 1, f"lines in order: n-1 = {n - 1} comparisons, not {got['sorted']}")
    t.check(got["reversed"] == n * (n - 1) // 2, f"lines in reverse: n(n-1)/2 = {n * (n - 1) // 2}, not {got['reversed']}")
    t.check(n * n / 5 < got["mixed"] < n * n / 3, f"lines in no order: about n*n/4 = {n * n // 4}, not {got['mixed']}")

    # bad keys and options are ordinary errors, as the system's are
    for args, words in ((["-k0"], "numbered from 1"), (["-k1.0"], "numbered from 1"), (["-k1b"], "'b' is not"),
                        (["-t", "ab"], "one character"), (["-x"], "unknown option -x"),
                        (["--algo=bogo"], "no --algo 'bogo'")):
        r = T.run(t, "sort", args, input="a\n", check=False)
        t.check(r.rc == 2 and words in r.err, f"sort {' '.join(args)}:\n{r}")
