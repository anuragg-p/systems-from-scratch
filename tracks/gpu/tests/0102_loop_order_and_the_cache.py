"""01.02 Loop order and the cache

matmul_ikj is held to matmul_ref on every shape of the plan (c full of NaN to start, so a
variant that adds into c instead of setting it fails; canaries; aligned and unaligned), and a
times I is a. Its sums are the same as ijk's, in the same order: on these inputs every element
of ikj's c equals ijk's bit for bit. mm check ikj prints its ok line; mm time ijk ikj prints both
rows in the table's order (names in any order), ikj's "vs ijk" being ijk's time over its own.
"""


def test(t):
    tr = t.track
    tr.check_variant(t, "ikj")

    # Swapping the loops changes the order memory is read in, not the order of the additions.
    for m, k, n, seed in ((7, 9, 11, 1), (64, 64, 64, 2), (33, 130, 17, 3)):
        ijk = tr.driver(t, "matmul_driver", f"dump ijk {m} {k} {n} {seed}\n")[0]
        ikj = tr.driver(t, "matmul_driver", f"dump ikj {m} {k} {n} {seed}\n")[0]
        t.check(ijk == ikj, f"{m}x{k}x{n}: ikj's sums differ from ijk's, so they are not added in the same order")

    st, out, err = tr.prog(t, "mm", ["check", "ikj"])
    t.check(st == 0 and len(out.splitlines()) == 1 and tr.mm_check_line("ikj").match(out.splitlines()[0]),
            f"mm check ikj: {st} {out!r} {err!r}")
    n, threads, rows = tr.mm_time(t, ["-n", "96", "ikj", "ijk"])
    t.check(n == 96 and [r[0] for r in rows] == ["ijk", "ikj"], f"mm time -n 96 ikj ijk: {rows}")
    (_, ijk_ms, _, ijk_x), (_, ikj_ms, _, ikj_x) = rows
    t.check(ijk_x == 1.0 and abs(ikj_x - ijk_ms / ikj_ms) <= 0.06 + 0.01 * ikj_x,
            f"mm time: ikj's vs ijk is {ikj_x}, but {ijk_ms} / {ikj_ms} ms is {ijk_ms / ikj_ms:.2f}")
    n, threads, rows = tr.mm_time(t, ["-n", "40", "ikj"])
    t.check([r[0] for r in rows] == ["ikj"] and rows[0][3] is None, f"mm time ikj alone: no ijk to compare: {rows}")
