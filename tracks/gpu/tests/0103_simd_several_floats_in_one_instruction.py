"""01.03 SIMD: several floats in one instruction

mul_add_tile adds to c, over rows [i0, i1) and columns [j0, j1), the sums over p in [p0, p1):
on a tile in the middle of a larger c (filled with a pattern) every element outside the tile is
untouched, bit for bit, and every one inside is the pattern plus its partial sum, at the
module's tolerance; an empty range of i, of p or of j changes nothing; ranges that start and
end anywhere relative to a vector or a group of four values of p are met. matmul_simd (c set to
0, then one mul_add_tile over everything) is held to matmul_ref on every shape of the plan,
which covers sides around 4 and 8 (a vector of either width), k % 4 of 1 to 3 with n % 8 of 1 to
7, and a, b and c starting 1, 2, 3, 5 and 7 floats past an aligned address; a times I is a. Held
to matmul_ref, not to ikj bit for bit: it fuses each multiply and add into one rounding. mm check
simd prints its ok line.
"""

import random


def test(t):
    tr = t.track

    # mul_add_tile on its own: tiles in the middle, at the edges, of every width; empty ranges.
    cases = [
        (20, 30, 40, 5, 9, 7, 19, 11, 29),       # in the middle of everything
        (20, 30, 40, 0, 20, 0, 30, 0, 40),       # all of it
        (20, 30, 40, 19, 20, 29, 30, 39, 40),    # the last row, p and column
        (16, 16, 16, 3, 13, 1, 14, 1, 15),       # p and j starting off a group and a vector
        (9, 13, 70, 2, 7, 3, 12, 9, 66),         # several vectors and a tail
        (9, 13, 70, 2, 7, 3, 12, 9, 17),         # exactly one vector of eight
        (9, 13, 70, 2, 7, 3, 12, 9, 13),         # exactly one vector of four
        (9, 13, 70, 2, 7, 3, 12, 9, 12),         # three columns: a tail only
        (9, 13, 70, 2, 7, 3, 7, 0, 70),          # four values of p: one group, none left over
        (9, 13, 70, 2, 7, 3, 6, 0, 70),          # three values of p: all left over
        (9, 13, 70, 2, 7, 5, 6, 0, 70),          # one value of p
        (9, 13, 70, 4, 4, 0, 13, 0, 70),         # no rows
        (9, 13, 70, 0, 9, 6, 6, 0, 70),          # no values of p
        (9, 13, 70, 0, 9, 0, 13, 33, 33),        # no columns
        (9, 13, 70, 7, 3, 0, 13, 0, 70),         # rows the wrong way round: nothing
        (9, 13, 70, 0, 9, 0, 13, 40, 30),        # columns the wrong way round: nothing
    ]
    rng = random.Random(103)
    for _ in range(60):
        m, k, n = rng.randint(1, 40), rng.randint(1, 40), rng.randint(1, 80)
        i0 = rng.randint(0, m)
        p0 = rng.randint(0, k)
        j0 = rng.randint(0, n)
        cases.append((m, k, n, i0, rng.randint(i0, m), p0, rng.randint(p0, k), j0, rng.randint(j0, n)))
    lines = tr.driver(t, "matmul_driver", "".join(
        f"tile {' '.join(map(str, c))} {7 + i}\n" for i, c in enumerate(cases)))
    bad = [f"{c}: {l}" for c, l in zip(cases, lines) if l != "ok"]
    t.check(len(lines) == len(cases) and not bad, "mul_add_tile (m, k, n, i0, i1, p0, p1, j0, j1):\n  " +
            "\n  ".join(bad[:8]))

    tr.check_variant(t, "simd", offsets=(1, 2, 3, 5, 7))

    st, out, err = tr.prog(t, "mm", ["check", "simd"])
    t.check(st == 0 and len(out.splitlines()) == 1 and tr.mm_check_line("simd").match(out.splitlines()[0]),
            f"mm check simd: {st} {out!r} {err!r}")
    n, threads, rows = tr.mm_time(t, ["-n", "72", "simd", "ijk"])
    t.check([r[0] for r in rows] == ["ijk", "simd"], f"mm time -n 72 simd ijk: {rows}")
