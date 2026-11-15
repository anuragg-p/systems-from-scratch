"""02.05 Sorting a file bigger than memory

With -S, sort holds no more than that many bytes of lines: it writes sorted runs to files in -T's
directory, merges them through a heap, sixteen at a time, in passes, and prints the system's bytes:
60000 lines (1.5 MB) with -S 64K, with -r, -n, -u and keys. Every line goes through one merge a
pass, log16 of the runs rounded up, counted by the heap's pushes: over 256 runs, three each. Every
run is gone afterwards; and without -S, or with room for everything, there are no runs at all.
"""

import os


def passes(runs):
    """The merges a line goes through: log16 of the runs, rounded up (one, for 16 or fewer)."""
    p = 1
    while 16 ** p < runs:
        p += 1
    return p


def merges(runs):
    """All the merges: each pass makes a sixteenth as many runs, rounded up; then the last one."""
    m = 1
    while runs > 16:
        runs = -(-runs // 16)
        m += runs
    return m


def test(t):
    T = t.track
    fx = T.fixtures("sort")
    runs = os.path.join(t.tmp, "runs")
    os.mkdir(runs)
    lines = T.gen(t, "lines", 60000)
    nums = T.gen(t, "numbers", 60000)
    for args, path, algo in (([], lines, None), (["-r"], lines, None), (["-u"], lines, None),
                             (["-k2", "-u"], lines, None), (["-rn"], nums, None), (["-nu"], nums, None),
                             ([], lines, "quick"), (["-r"], lines, "heap")):
        r = fx.check(t, ["-S", "64K", "-T", runs] + args, path, env={"DS_STATS": "1"}, algo=algo)
        s = T.stats(r.err)
        t.check(s["lines"]["peak bytes"] <= 64 * 1024, f"-S 64K holds at most 64K: {s['lines']}")
        t.check(s["runs"]["written"] >= 17 and s["runs"]["merges"] >= 2,
                f"over 16 runs take more than one merge: {s['runs']}")
        t.check(os.listdir(runs) == [], f"run files left in -T's directory: {os.listdir(runs)}")
        # a line is pushed into the heap once for each merge it goes through; with -u a line
        # equal to one already written is dropped, and goes through no more merges
        w, read, pushes = s["runs"]["written"], s["lines"]["read"], s["heap"]["pushes"]
        bound = passes(w) * read
        unique = "-u" in args or "-nu" in args
        t.check(pushes == bound or (unique and pushes <= bound),
                f"{w} runs: each of {read} lines should go through {passes(w)} merges, "
                f"{bound} pushes, not {pushes} ({pushes / read:.2f} a line)")
        t.check(s["runs"]["merges"] == merges(w),
                f"{w} runs merged in passes of 16 take {merges(w)} merges, not {s['runs']['merges']}")

    # more runs, one more pass: over 256 runs, each line goes through three merges, not one more
    # for every sixteen runs (compared with the system's sort without -S: macOS's takes half a
    # minute with -S 8K)
    r = T.run(t, "sort", ["-S", "8K", "-T", runs, lines], env={"DS_STATS": "1"})
    T.same(t, r.out, T.system(t, ["sort", lines]).out, "sort -S 8K")
    s = T.stats(r.err)
    w, read, pushes = s["runs"]["written"], s["lines"]["read"], s["heap"]["pushes"]
    t.check(256 < w <= 4096 and pushes == 3 * read and s["runs"]["merges"] == merges(w),
            f"-S 8K on {read} lines: {w} runs, {s['runs']['merges']} merges, {pushes} pushes "
            f"({pushes / read:.2f} a line, not 3)")
    t.check(os.listdir(runs) == [], f"run files left in -T's directory: {os.listdir(runs)}")

    # the units of -S: K unless it says b, K, M or G; one line a run still sorts
    for size in ("1b", "300b", "1", "2K", "1M"):
        r = fx.check(t, ["-S", size, "-T", runs], T.gen(t, "lines", 500), env={"DS_STATS": "1"})
        written = T.stats(r.err)["runs"]["written"]
        t.check((written > 0) == (size not in ("1M",)), f"-S {size}: {written} runs")
    r = fx.check(t, [], lines, env={"DS_STATS": "1"})
    t.check(T.stats(r.err)["runs"]["written"] == 0, "without -S, no runs")
    for bad in ("0", "x", "12Q", "-5"):
        r = T.run(t, "sort", ["-S", bad], input="a\n", check=False)
        t.check(r.rc == 2 and "-S wants a size" in r.err, f"sort -S {bad}:\n{r}")
