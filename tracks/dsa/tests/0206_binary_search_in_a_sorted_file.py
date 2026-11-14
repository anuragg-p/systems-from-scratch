"""02.06 Binary search in a sorted file

look prints the lines of a sorted file that start with a string, as the system's look does where
there is one, and exits 0 if there were any, 1 if not. Binary search looks at no more than
log2(lines) + 2 lines to find the first; a scan looks at every line before it.
"""

import math


def test(t):
    T = t.track
    fx = T.fixtures("look")
    n = 100000
    path = T.gen(t, "dict", n)
    with open(path) as f:
        lines = f.read().splitlines()
    keys = [lines[0], lines[n // 2][:3], lines[n // 3][:2], lines[-1], "a", "zzzzzz", "0", lines[777] + "x",
            lines[1234], "the"]
    for key in keys:
        before = sum(1 for l in lines if l < key and not l.startswith(key))
        b = T.stats(fx.check(t, key, path, "binary").err)["look"]
        s = T.stats(fx.check(t, key, path, "scan").err)["look"]
        t.check(b["probes"] <= math.log2(n) + 2, f"look {key!r}: binary search, {b['probes']} probes: {b}")
        t.check(s["probes"] == min(before + 1, n), f"look {key!r}: a scan looks at {before + 1} lines: {s}")
        fx.check(t, key, path)

    # small files: one line, none, no last newline, an empty key
    for text in ("solo\n", "", "a\nab\nb", "a\na\na\nb\n"):
        p = T.write(t, "small.txt", text)
        for key in ("a", "solo", "b", ""):
            for algo in ("binary", "scan"):
                r = T.run(t, "look", [f"--algo={algo}", key, p], check=False)
                want = fx.reference(p, key)
                t.check(r.out == want and r.rc == (0 if want else 1), f"look {key!r} in {text!r}:\n{r}")
    for args in ([], ["x"], ["--algo=bogo", "x", path], ["x", "/no/such/file"]):
        r = T.run(t, "look", args, check=False)
        t.check(r.rc == 2 and r.err.startswith("look: "), f"look {' '.join(args)}:\n{r}")
