"""06.02 From the table to hunks: unified output

The walk through the table gives a script the system's patch applies: on every pair, diff
--algo=table prints the two header lines and hunks that are right about both files, with 3 lines of
context or -U's number, the same numbers of lines deleted and inserted as the system's diff -d, and
the system's patch makes the second file of the first with them. Where only one script is shortest,
the hunks are the system's own bytes, at -U 0, 1, 3 and 5.
"""


def test(t):
    T = t.track
    fx = T.fixtures("diff")
    for name, (a, b) in fx.cases(t).items():
        for args in ([], ["-U", "0"], ["-U1"], ["-u", "-U", "7"]):
            fx.check(t, a, b, args, algo="table")

    for name, (a, b) in fx.unique_cases(t).items():
        for c in ("0", "1", "3", "5"):
            ours = T.run(t, "diff", ["--algo=table", "-U", c, a, b], check=False)
            theirs = fx.system_diff(t, a, b, ["-U", c])
            t.check(ours.rc == theirs.rc == 1, f"{name}: exit status {ours.rc}, the system's {theirs.rc}")
            fx.same_text(t, ours.raw, theirs.raw, f"{name}, diff -U {c}")

    # the walk, as DS_TRACE prints it: keep, delete on a tie, insert once a is done
    old, new = T.write(t, "old", "a\nb\nc\nd\n"), T.write(t, "new", "a\nc\nd\ne\n")
    r = T.run(t, "diff", ["--algo=table", old, new], env={"DS_TRACE": "1"}, check=False)
    walk = [l for l in r.err.splitlines() if l.startswith("trace: walk:")]
    t.check(walk == ['trace: walk: at 0 0, L 3: keep "a"', 'trace: walk: at 1 1, L 2: delete "b": below 2 >= right 1',
                     'trace: walk: at 2 1, L 2: keep "c"', 'trace: walk: at 3 2, L 1: keep "d"',
                     'trace: walk: at 4 3, L 0: insert "e": a is done'], f"DS_TRACE=1, the walk:\n{r.err}")

    # standard input as a file; a bad -U
    r = T.run(t, "diff", ["--algo=table", "-", new], input="a\nb\nc\nd\n", check=False)
    t.check(r.rc == 1 and r.lines()[0].startswith("--- -\t") and r.lines()[2] == "@@ -1,4 +1,4 @@",
            f"diff - new, with old on standard input:\n{r}")
    for bad in ("-1", "x", ""):
        r = T.run(t, "diff", ["-U", bad, old, new], check=False)
        t.check(r.rc == 2 and "-U wants a number" in r.err, f"diff -U '{bad}':\n{r}")
