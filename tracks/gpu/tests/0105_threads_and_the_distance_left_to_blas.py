"""01.05 Threads, and the distance left to BLAS

matmul_threads (blocked_rows on each thread's share of the rows) is held to matmul_ref on every
shape of the plan on the default thread count and on 3 threads, and under ThreadSanitizer on 1,
2, 3, 7, 64 and 256 threads, including more threads than rows (no data race, every row computed
once); rows are independent, so its c equals blocked's bit for bit. thread_count() is mm -t's
number, or the cores. matmul_blas, when make found a BLAS, is within the tolerance of matmul_ref
on every shape (a side of 0 included: its leading dimensions are at least 1), and every variant
is within it of matmul_blas; without one, mm leaves blas out and says how to get one. mm list
names all six; mm time -t T prints "threads = T" and a row for each; -t outside 1 to 256 is
refused.
"""

import os


def test(t):
    tr = t.track
    tr.check_variant(t, "threads")
    tr.check_variant(t, "threads", threads=3, every=2, offsets=(1,))

    # Under ThreadSanitizer: a data race is a report, and the report fails the test.
    if os.environ.get("GPU_TSAN", "1") != "0":
        for count in (1, 2, 3, 7, 64):
            tr.check_variant(t, "threads", mode="thread", threads=count, every=3, offsets=(1,))
        lines = tr.driver(t, "matmul_driver", "threads 64\ncheck threads 5 100 70 3\ncheck threads 1 64 64 4\n"
                                              "threads 256\ncheck threads 63 17 9 5\n", mode="thread")
        t.check([l.split()[0] for l in lines] == ["threads", "ok", "ok", "threads", "ok"],
                f"more threads than rows, under ThreadSanitizer: {lines}")

    for m, k, n, seed in ((7, 9, 11, 1), (130, 70, 140, 2), (300, 20, 9, 3)):
        a = tr.driver(t, "matmul_driver", f"dump blocked {m} {k} {n} {seed}\n")[0]
        b = tr.driver(t, "matmul_driver", f"threads 3\ndump threads {m} {k} {n} {seed}\n")[1]
        t.check(a == b, f"{m}x{k}x{n}: threads' c differs from blocked's: a row is computed by two threads, "
                        f"or by none")

    blas = tr.driver(t, "matmul_driver", "blas\n")[0].split()[1]
    st, out, err = tr.prog(t, "mm", ["list"])
    names = out.split("\n")
    if blas != "none":
        tr.check_variant(t, "blas", offsets=(1,))
        text, asked = "", []
        for name in ("ijk", "ikj", "simd", "blocked", "threads"):
            for i, (m, k, n) in enumerate(tr.shapes(tr.block_size(t))[::5]):
                text += f"vsblas {name} {m} {k} {n} {50 + i}\n"
                asked.append(f"{name} {m}x{k}x{n}")
        lines = tr.driver(t, "matmul_driver", text)
        bad = [f"{a}: {l}" for a, l in zip(asked, lines) if not l.startswith("ok")]
        t.check(len(lines) == len(asked) and not bad, f"against matmul_blas:\n  " + "\n  ".join(bad[:8]))
        t.check(st == 0 and names == ["ijk", "ikj", "simd", "blocked", "threads", f"blas ({blas})", ""],
                f"mm list: {out!r}")
    else:
        t.check(st == 0 and names == ["ijk", "ikj", "simd", "blocked", "threads", ""] and
                err.startswith("mm: blas: make found no BLAS library."), f"mm list, no BLAS: {out!r} {err!r}")
        st, out, err = tr.prog(t, "mm", ["time", "-n", "16", "blas"])
        t.check(st == 0 and "mm: blas: make found no BLAS library." in err, f"mm time blas, no BLAS: {err!r}")

    st, out, err = tr.prog(t, "mm", ["check", "-t", "3", "threads"])
    t.check(st == 0 and tr.mm_check_line("threads").match(out.strip()), f"mm check -t 3 threads: {st} {out!r}")
    st, out, err = tr.prog(t, "mm", ["check"])
    lines = out.splitlines()
    t.check(st == 0 and [l.split()[0] for l in lines] ==
            ["ijk", "ikj", "simd", "blocked", "threads"] + (["blas"] if blas != "none" else []) and
            all(tr.mm_check_line(l.split()[0]).match(l) for l in lines), f"mm check: {st} {out!r}")

    n, threads, rows = tr.mm_time(t, ["-n", "64", "-t", "3"])
    t.check(n == 64 and threads == 3 and [r[0] for r in rows] ==
            ["ijk", "ikj", "simd", "blocked", "threads"] + (["blas"] if blas != "none" else []) and
            all(r[3] is not None for r in rows), f"mm time -n 64 -t 3: {n} {threads} {rows}")
    n, threads, rows = tr.mm_time(t, ["-n", "64", "simd"])
    t.check(threads is None, "mm time without the threads variant prints no threads line")
    n, threads, rows = tr.mm_time(t, ["-n", "64", "threads"])
    t.check(threads is not None and threads >= 1, f"mm time threads: the default thread count, {threads}")
    for argv, msg in ((["time", "-t", "0"], "mm: -t wants a whole number from 1 to 256, not '0'\n"),
                      (["check", "-t", "257"], "mm: -t wants a whole number from 1 to 256, not '257'\n")):
        st, out, err = tr.prog(t, "mm", argv)
        t.check((st, out, err) == (2, "", msg), f"mm {' '.join(argv)}: {st} {out!r} {err!r}")
    st, out, err = tr.prog(t, "mm", ["list", "-t", "2"])
    t.check(st == 2 and err.startswith("usage: mm list\n       mm check [-t T] [name...]\n"), f"mm list -t 2: {err!r}")
