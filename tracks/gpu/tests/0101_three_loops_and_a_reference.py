"""01.01 Three loops and a reference

matmul_ref is the exact sum rounded once: each element equals, bit for bit, the sum of its
products taken in order in a double (Python's float) and rounded to a float. matmul_ijk is held
to it at the module's tolerance (rtol 1e-4, atol 1e-3) on every shape of the plan: every square
size 1 to 67, forty random ones, the sides around 8 and MM_BLOCK, 1 x k x 1, m x 1 x n, a side of
0; with c full of NaN to start and canaries either side, a and b untouched, at aligned and
unaligned addresses; a times I and I times a are exactly a. The checker is checked: three wrong
multiplies (the last column skipped, b read transposed, a term dropped) all fail at that
tolerance. mm list names the variants, ijk first; mm check prints one ok line for ijk; mm time
prints n, then a row for ijk (min ms, GFLOP/s = 2 n^3 / min, 1.0x); bad options are usage errors.
"""


def ref_sums(tr, m, k, n, seed):
    a, b = tr.rng_fill(seed, m * k), tr.rng_fill(seed + 1, k * n)
    out = []
    for i in range(m):
        for j in range(n):
            s = 0.0
            for p in range(k):
                s += a[i * k + p] * b[p * n + j]
            out.append(tr.f32(s))
    return out


def test(t):
    tr = t.track

    # matmul_ref, against the same sums done in Python.
    for m, k, n, seed in ((1, 1, 1, 1), (2, 3, 4, 5), (5, 7, 3, 9), (16, 33, 9, 2), (3, 200, 2, 77), (4, 0, 3, 8)):
        line = tr.driver(t, "matmul_driver", f"dump ref {m} {k} {n} {seed}\n")[0].split()
        got, want = tr.floats(line[1:]), ref_sums(tr, m, k, n, seed)
        t.check(line[0] == "c" and got == want,
                f"matmul_ref {m}x{k}x{n} (seed {seed}) is not the double sum rounded once: "
                f"{[(i, g, w) for i, (g, w) in enumerate(zip(got, want)) if g != w][:3]}")

    tr.check_variant(t, "ijk")

    # The checker checked: each wrong multiply is caught at the tolerance, on every shape tried.
    for which in ("lastcol", "transposed", "dropterm"):
        for m, k, n in ((64, 64, 64), (33, 70, 20), (100, 200, 50), (7, 9, 11), (1, 50, 2)):
            got = tr.driver(t, "matmul_driver", f"wrong {which} {m} {k} {n} 3\n")[0]
            t.check(got.startswith("caught "), f"a matmul with {which} wrong at {m}x{k}x{n} passes the "
                                               f"checker: {got}")

    # mm list, check and time.
    st, out, err = tr.prog(t, "mm", ["list"])
    names = [l.split()[0] for l in out.splitlines()]
    t.check(st == 0 and names[:1] == ["ijk"] and set(names) <= {"ijk", "ikj", "blocked", "simd", "threads", "blas"},
            f"mm list: {st} {out!r}")
    st, out, err = tr.prog(t, "mm", ["check", "ijk"])
    t.check(st == 0 and len(out.splitlines()) == 1 and tr.mm_check_line("ijk").match(out.splitlines()[0]),
            f"mm check ijk: {st} {out!r} {err!r}")
    n, threads, rows = tr.mm_time(t, ["-n", "64", "ijk"])
    t.check(n == 64 and threads is None and len(rows) == 1 and rows[0][0] == "ijk" and rows[0][3] == 1.0,
            f"mm time -n 64 ijk: {n} {threads} {rows}")
    name, ms, gflops, x = rows[0]
    t.check(ms > 0 and abs(gflops - 2 * 64 ** 3 / (ms / 1e3) / 1e9) <= 0.01 * gflops + 0.01,
            f"mm time -n 64 ijk: {ms} ms is not {gflops} GFLOP/s at 2 n^3 operations")
    n, threads, rows = tr.mm_time(t, ["ijk", "-n", "100"])
    t.check(n == 100 and [r[0] for r in rows] == ["ijk"], f"mm time ijk -n 100: {n} {rows}")
    for argv, msg in ((["time", "-n", "0"], "mm: -n wants a whole number from 1 to 8192, not '0'\n"),
                      (["time", "-n", "8193"], "mm: -n wants a whole number from 1 to 8192, not '8193'\n"),
                      (["time", "-n", "x"], "mm: -n wants a whole number from 1 to 8192, not 'x'\n"),
                      (["time", "nosuch"], "mm: no variant called 'nosuch' (mm list names them)\n"),
                      (["check", "ref"], "mm: no variant called 'ref' (mm list names them)\n")):
        st, out, err = tr.prog(t, "mm", argv)
        t.check((st, out, err) == (2, "", msg), f"mm {' '.join(argv)}: {st} {out!r} {err!r}")
    for argv in ([], ["lst"], ["check", "-n", "64"], ["list", "ijk"], ["time", "-n"], ["time", "-q"]):
        st, out, err = tr.prog(t, "mm", argv)
        t.check(st == 2 and out == "" and err.startswith("usage: mm list\n"), f"mm {' '.join(argv)}: {st} {err!r}")
