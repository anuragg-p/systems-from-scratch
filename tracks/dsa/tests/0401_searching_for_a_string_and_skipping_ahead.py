"""04.01 Searching for a string, and skipping ahead

grep -F prints the system's grep -F lines, with both searches: scan (try every position) and horspool
(compare from the end and skip ahead), for a table of strings on the book and on the project's own
source, with -n -c -v -i, several files, standard input, a missing file. On a string absent from the
text, scan tries every position and horspool tries or skips each one exactly once, trying under a
tenth of them for a 15-byte string. Each has its own n*m input: "aa...ab" in a run of a's costs scan
m bytes a position and horspool one; "baa...a" the other way round.
"""

import os


def test(t):
    T = t.track
    fx = T.fixtures("grep")
    for algo in ("scan", "horspool"):
        fx.table(t, "-F", algo)

    # standard input among files, a missing file (status 2, and the rest still searched), no last newline
    book = T.data(t, "book.txt")
    for algo in ("scan", "horspool"):
        fx.check(t, ["-F", "-n", "Holmes", "-", book], input="Holmes\nwatson", algo=algo)
        fx.check(t, ["-F", "-c", "Holmes", book, "no-such-file"], algo=algo)
        fx.check(t, ["-F", "-v", "x"], input="a\nx\nb", algo=algo)
        fx.check(t, ["-F", "-n", "b"], input="a\n\nb\n\n", algo=algo)
        fx.check(t, ["-F", "-c", "x"], input="", algo=algo)

    # a string that is not there: every position is tried by scan; tried or skipped once by horspool
    n = os.path.getsize(book)
    for pat in ("Sherlock Holmez", "zzzzzzzzzzzzzzz"):
        m = len(pat)
        s = T.stats(T.run(t, "grep", ["-F", "--algo=scan", pat, book], env={"DS_STATS": "1"}, check=False).err)["search"]
        h = T.stats(T.run(t, "grep", ["-F", "--algo=horspool", pat, book], env={"DS_STATS": "1"}, check=False).err)["search"]
        t.check(s["positions"] == n - m + 1 and s["skipped"] == 0 and s["examined"] >= s["positions"],
                f"scan tries each of the {n - m + 1} positions for {pat!r}: {s}")
        t.check(h["positions"] + h["skipped"] == n - m + 1,
                f"horspool tries or skips each of the {n - m + 1} positions once for {pat!r}: {h}")
        t.check(h["positions"] * 10 < n and h["examined"] * 5 < s["examined"],
                f"a {m}-byte string: horspool tries under a tenth of the positions, and examines under a fifth "
                f"of what scan does: horspool {h}, scan {s}")

    # each one's worst case: a run of 10000 a's, and a 100-byte string that differs at one end
    run = T.write(t, "run.txt", "a" * 10000 + "\n")
    want = {("scan", "a" * 99 + "b"): (9902, 990200), ("horspool", "a" * 99 + "b"): (9902, 9902),
            ("scan", "b" + "a" * 99): (9902, 9902), ("horspool", "b" + "a" * 99): (9902, 990101)}
    for (algo, pat), (positions, examined) in want.items():
        r = T.run(t, "grep", ["-F", f"--algo={algo}", pat, run], env={"DS_STATS": "1"}, check=False)
        s = T.stats(r.err)["search"]
        t.check(r.rc == 1 and (s["positions"], s["examined"]) == (positions, examined),
                f"{algo} on {pat[:3]}...{pat[-3:]} in a run of a's: {positions} positions, {examined} bytes "
                f"examined, not {s}")

    # what is not grep: ordinary errors, status 2
    for args, words in ((["-F"], "usage"), (["-x", "a"], "unknown option -x"), (["--long", "a"], "unknown option"),
                        (["-F", "--algo=bogo", "a"], "no --algo 'bogo' for a fixed string (have: scan, horspool)"),
                        (["-F", "a\nb"], "newline")):
        r = T.run(t, "grep", args, input="a\n", check=False)
        t.check(r.rc == 2 and words in r.err and r.out == "", f"grep {' '.join(args)}:\n{r}")
