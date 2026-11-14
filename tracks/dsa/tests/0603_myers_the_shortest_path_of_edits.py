"""06.03 Myers: the shortest path of edits

Myers' search, the default, finds scripts exactly as short as the table's, which the system's patch
applies, and where only one is shortest, the system's own hunks. Its work is the size of the
difference, not of the files: on 2000 lines with 16 edits it reaches a few thousand points of the
edit graph where the table fills four million; twice the lines with the same edits costs it less
than twice; twice the edits, about four times. Its d is the script's length, it keeps one point
for each diagonal of each round, and files the table refuses are quick for it. Two files with
nothing in common cost it as much as the table.
"""


def test(t):
    T = t.track
    fx = T.fixtures("diff")
    for name, (a, b) in fx.cases(t).items():
        r = fx.check(t, a, b)
        fx.check(t, a, b, ["-U", "0"], algo="myers")
        s = T.stats(r.err)
        table = T.stats(fx.check(t, a, b, ["-q"], algo="table").err)
        t.check(s["diff"]["common"] == table["diff"]["common"],
                f"{name}: myers keeps {s['diff']['common']} lines, the table {table['diff']['common']}")
        d = s["myers"]["d"]
        t.check(d == s["diff"]["deleted"] + s["diff"]["inserted"], f"{name}: d is the script's length: {s}")
        kept = s["myers"]["bytes"] // 4
        t.check(s["myers"]["diagonals"] == kept and d * (d + 1) // 2 < kept <= (d + 1) * (d + 2) // 2,
                f"{name}: one point kept for each diagonal of rounds 0 to {d}: {s['myers']}")

    for name, (a, b) in fx.unique_cases(t).items():
        for c in ("0", "3"):
            ours = T.run(t, "diff", ["-U", c, a, b], check=False)
            fx.same_text(t, ours.raw, fx.system_diff(t, a, b, ["-U", c]).raw, f"{name}, diff -U {c}")

    def cells(kind, n, algo, seed=1):
        a, b = T.gen(t, kind, n, seed=seed)
        s = T.stats(T.run(t, "diff", ["-q", f"--algo={algo}", a, b], env={"DS_STATS": "1"}, check=False).err)
        return s["myers" if algo == "myers" else "lcs"]["cells"]

    # the same 16 edits: a few thousand points against the table's millions, and linear in the lines
    m2, t2 = cells("versions", 2000, "myers"), cells("versions", 2000, "table")
    t.check(m2 * 500 < t2, f"2000 lines, 16 edits: myers reaches {m2} points, the table fills {t2}")
    m4, m8 = cells("versions", 4000, "myers", 2), cells("versions", 8000, "myers", 2)
    t.check(m8 < 2.5 * m4, f"twice the lines, the same 16 edits: myers reaches {m4}, then {m8} points")
    # an edit every 32 lines: twice the lines is twice the edits, and about four times the work
    r4, r8 = cells("revised", 4000, "myers"), cells("revised", 8000, "myers")
    t.check(3 < r8 / r4 < 5.5, f"twice the edits: myers reaches {r4}, then {r8} points")
    # nothing in common but blank lines: no better than the table
    u, ut = cells("unrelated", 1000, "myers"), cells("unrelated", 1000, "table")
    t.check(u > ut / 2, f"1000 unrelated lines: myers reaches {u} points, the table fills {ut}")

    # files too big for the table: refused by it, quick for myers, and the system's patch takes them
    a, b = T.gen(t, "versions", 40000)
    r = T.run(t, "diff", ["--algo=table", a, b], check=False)
    t.check(r.rc == 2 and "the table would take" in r.err, f"40000 lines, the table:\n{r}")
    s = T.stats(fx.check(t, a, b).err)
    t.check(s["myers"]["cells"] < 200000, f"40000 lines, 16 edits: {s['myers']}")

    # the search, as DS_TRACE prints it
    old, new = T.write(t, "old", "a\nb\nc\nd\n"), T.write(t, "new", "a\nc\nd\ne\n")
    r = T.run(t, "diff", [old, new], env={"DS_TRACE": "1"}, check=False)
    trace = [l for l in r.err.splitlines() if l.startswith("trace: myers: d ") or "reached" in l]
    t.check(trace == ["trace: myers: d 0 k 0: start (0,0), snake 1, reaches (1,1)",
                      "trace: myers: d 1 k -1: down from (1,1) to (1,2), snake 0, reaches (1,2)",
                      "trace: myers: d 1 k 1: right from (1,1) to (2,1), snake 2, reaches (4,3)",
                      "trace: myers: d 2 k -2: down from (1,2) to (1,3), snake 0, reaches (1,3)",
                      "trace: myers: d 2 k 0: down from (4,3) to (4,4), snake 0, reaches (4,4)",
                      "trace: myers: (4,4) reached with d 2"], f"DS_TRACE=1, the search:\n{r.err}")
