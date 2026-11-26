"""01.04 Blocking

blocked_rows sets rows [i0, i1) of c to a * b, a tile at a time: on a band of rows in the middle
of a c filled with a pattern, every other row is untouched, bit for bit, and the band is
matmul_ref's at the tolerance; an empty band changes nothing. matmul_blocked (blocked_rows over
every row) is held to matmul_ref on every shape of the plan, which includes sides one less,
equal and one more than MM_BLOCK and twice a multiple of MM_BLOCK and 8, alone and together, so
every way a tile can be cut short is met; c starts full of NaN, canaries either side, aligned and
unaligned; a times I is a. With MM_BLOCK a multiple of 8 its tiles change only the order memory
is visited in, not the order of any element's additions: its c equals simd's bit for bit. With
MM_BLOCK changed to 1, 7, 30, 200 and 100000 (a patched copy, as a reader does in Break it) it is
still right. mm check blocked prints its ok line.
"""

import os
import re


def test(t):
    tr = t.track
    block = tr.block_size(t)

    # blocked_rows on its own: a band in the middle, at either end, one row, none, all.
    for m, k, n, i0, i1 in ((50, 40, 30, 10, 35), (block + 9, 37, block + 3, 3, block + 5), (20, 9, 17, 0, 1),
                            (20, 9, 17, 19, 20), (20, 9, 17, 7, 7), (20, 9, 17, 0, 20),
                            (2 * block + 1, 5, 11, block - 1, 2 * block)):
        got = tr.driver(t, "matmul_driver", f"rows {m} {k} {n} {i0} {i1} 5\n")[0]
        t.check(got == "ok", f"blocked_rows on rows [{i0}, {i1}) of {m}x{k}x{n}: {got}")

    tr.check_variant(t, "blocked")

    if block % 8 == 0:
        for m, k, n, seed in ((7, 9, 11, 1), (block + 1, block - 1, 2 * block + 1, 2), (33, 2 * block + 6, 17, 3)):
            a = tr.driver(t, "matmul_driver", f"dump simd {m} {k} {n} {seed}\n")[0]
            b = tr.driver(t, "matmul_driver", f"dump blocked {m} {k} {n} {seed}\n")[0]
            t.check(a == b, f"{m}x{k}x{n}: blocked's sums differ from simd's: the tiles change the order of the "
                            f"additions, or a product is added twice or not at all")

    st, out, err = tr.prog(t, "mm", ["check", "blocked"])
    t.check(st == 0 and len(out.splitlines()) == 1 and tr.mm_check_line("blocked").match(out.splitlines()[0]),
            f"mm check blocked: {st} {out!r} {err!r}")
    n, threads, rows = tr.mm_time(t, ["-n", "70", "blocked"])
    t.check([r[0] for r in rows] == ["blocked"], f"mm time -n 70 blocked: {rows}")

    # Break it: another MM_BLOCK, in a copy. Still right, tiles of any size or none.
    with open(os.path.join(t.root, "matmul_blocked.c")) as f:
        source = f.read()
    for size in (1, 7, 30, 200, 100000):
        mm = tr.build_with(t, "mm", {"matmul_blocked.c": tr.BLOCK_LINE.sub(f"#define MM_BLOCK {size}", source)})
        st, out, err = tr.prog(t, mm, ["check", "blocked"])
        lines = out.splitlines()
        t.check(st == 0 and len(lines) == 1 and tr.mm_check_line("blocked").match(lines[0]),
                f"with MM_BLOCK {size}: {st} {out!r} {err!r}")
