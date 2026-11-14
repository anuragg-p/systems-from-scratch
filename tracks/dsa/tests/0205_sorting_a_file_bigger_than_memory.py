"""02.05 Sorting a file bigger than memory

With -S, sort holds no more than that many bytes of lines: it writes sorted runs to files in -T's
directory, merges them through a heap, sixteen at a time, and prints the system's bytes: 60000 lines
(1.5 MB) with -S 64K, with -r, -n, -u and keys. Every run is gone afterwards; and without -S, or with
room for everything, there are no runs at all.
"""

import os


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
