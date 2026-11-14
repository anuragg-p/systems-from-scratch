"""06.01 The longest common subsequence, as a table

diff --algo=table fills a table of (n+1) x (m+1) cells, and its corner says how many lines the two
files have in common: as many as the system's diff -d keeps, on every pair; diff -q prints what the
system's prints, with its exit status. Equal lines are found through the hash table, one lookup a
line. The table's cells and bytes are the product of the lengths, so twice the lines is four times
the work; a table over 4 GB is an ordinary error, before it takes the memory.
"""


def test(t):
    T = t.track
    fx = T.fixtures("diff")
    for name, (a, b) in fx.cases(t).items():
        r = fx.check(t, a, b, ["-q"], algo="table")
        n, m = (len(fx.lines(fx.read(p))) for p in (a, b))
        s = T.stats(r.err)
        t.check(s["lcs"]["cells"] == (n + 1) * (m + 1) and s["lcs"]["bytes"] == 4 * (n + 1) * (m + 1),
                f"{name}: a table of {n + 1} x {m + 1} cells: {s['lcs']}")
        t.check(s["table"]["lookups"] == n + m, f"{name}: one lookup for each of {n + m} lines: {s['table']}")

    # twice the lines, four times the cells
    cells = []
    for n in (1000, 2000):
        a, b = T.gen(t, "versions", n)
        cells.append(T.stats(fx.check(t, a, b, ["-q"], algo="table").err)["lcs"]["cells"])
    t.check(3.9 < cells[1] / cells[0] < 4.1, f"twice the lines, four times the cells: {cells}")

    # the table, as DS_TRACE prints it, for a/b/c/d against a/c/d/e
    old, new = T.write(t, "old", "a\nb\nc\nd\n"), T.write(t, "new", "a\nc\nd\ne\n")
    r = T.run(t, "diff", ["--algo=table", "-q", old, new], env={"DS_TRACE": "1"}, check=False)
    rows = [l for l in r.err.splitlines() if l.startswith("trace: lcs: row") or l.startswith("trace: lcs: length")]
    t.check(rows == ["trace: lcs: row 4: 0 0 0 0 0", "trace: lcs: row 3: 1 1 1= 0 0",
                     "trace: lcs: row 2: 2 2= 1 0 0", "trace: lcs: row 1: 2 2 1 0 0",
                     "trace: lcs: row 0: 3= 2 1 0 0", "trace: lcs: length 3"],
            f"DS_TRACE=1, the table row by row from the bottom:\n{r.err}")

    # a table over 4 GB: refused, an ordinary error
    a, b = T.gen(t, "versions", 33000)
    r = T.run(t, "diff", ["--algo=table", "-q", a, b], check=False)
    t.check(r.rc == 2 and "the table would take" in r.err, f"two files of 33000 lines, the table:\n{r}")

    # trouble is exit status 2, as the system's diff
    for args in (["--algo=bogo", old, new], [old], [old, "/no/such/file"], ["--nonesuch", old, new]):
        r = T.run(t, "diff", args, check=False)
        t.check(r.rc == 2 and r.err.startswith("diff: "), f"diff {' '.join(args)}:\n{r}")
