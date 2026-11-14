"""00.01 One job, done slow and done fast

bin/paste -s joins each file's lines into one line, the system's paste -s bytes exactly, in two ways
that differ in one line: --algo=strcat looks for the end of what it has built before each piece, so
twice the lines scan four times the bytes; --algo=end remembers where the end is and scans none.
"""


def test(t):
    T = t.track
    book = T.data(t, "book.txt")
    small = T.write(t, "small.txt", "one two\n\nthree\n\n\nfour\n")
    for algo in ("strcat", "end"):
        for args in (["-s"], ["-s", "-d", " "], ["-sd", ",;"], ["-s", "-d", "\\t"], ["-s", "-d", "\\n"]):
            for path in (book, small):
                ours = T.run(t, "paste", args + [f"--algo={algo}", path])
                theirs = T.system(t, ["paste"] + args + [path])
                T.same(t, ours.out, theirs.out, f"paste {' '.join(args)} --algo={algo}")

    # standard input, and several files: one line each
    r = T.run(t, "paste", ["-s", "-", small], input="x\ny\n")
    t.check(r.out == "x\ty\none two\t\tthree\t\t\tfour\n", f"paste -s - small.txt printed {r.out!r}")
    # -d '\0' is no delimiter at all; an empty input is an empty line (GNU's paste; BSD's prints none)
    r = T.run(t, "paste", ["-s", "-d", "\\0", small])
    t.check(r.out == "one twothreefour\n", f"paste -s -d '\\0' printed {r.out!r}")
    r = T.run(t, "paste", ["-s"], input="")
    t.check(r.out == "\n", f"paste -s on nothing printed {r.out!r}")

    # the counts: strcat scans what it has built every time, end never does
    a, b = T.gen(t, "lines", 4000), T.gen(t, "lines", 8000)
    got = {}
    for algo in ("strcat", "end"):
        for n, path in ((4000, a), (8000, b)):
            r = T.run(t, "paste", ["-s", f"--algo={algo}", path], env={"DS_STATS": "1"})
            got[algo, n] = T.stats(r.err)["paste"]
    for n in (4000, 8000):
        t.check(got["strcat", n]["bytes copied"] == got["end", n]["bytes copied"],
                f"both ways copy every byte once: {got}")
        t.check(got["end", n]["bytes scanned"] == 0, f"--algo=end scans nothing: {got['end', n]}")
    ratio = got["strcat", 8000]["bytes scanned"] / got["strcat", 4000]["bytes scanned"]
    t.check(3.6 < ratio < 4.4, f"twice the lines should scan four times the bytes, not {ratio:.2f} times: {got}")

    # errors are ordinary
    r = T.run(t, "paste", [book], check=False)
    t.check(r.rc == 2 and "only paste -s is here" in r.err, f"paste without -s:\n{r}")
    r = T.run(t, "paste", ["-s", "--algo=fast", book], check=False)
    t.check(r.rc == 2 and "no --algo 'fast' (have: strcat, end)" in r.err, f"paste --algo=fast:\n{r}")
