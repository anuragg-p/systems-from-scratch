"""Figures for gpu module 01, matrix multiply on the CPU (plans/gpu-00-01-lessons.md, the "Figures:" entries).

    python3 -B art/gpu/figs01.py [name-prefix ...]
        writes tracks/gpu/lessons/01-matrix-multiply-on-the-cpu/figures/01.0N-*.svg (the maps are
        archmap.py's)

Each figure's <title> is its caption from the design; the lesson carries the caption itself. What
each one draws is checked against the design's values and against the track's code
(tracks/gpu/matmul*.c), so a change to either stops this script instead of reaching a figure:

  01.01-row-times-column  a = [[1, 2, 3], [4, 5, 6]] times b = [[7, 8], [9, 10], [11, 12]] is
                          c = [[58, 64], [139, 154]]; c[1][0] = 4*7 + 5*9 + 6*11 = 28 + 45 + 66 = 139,
                          the sum matmul.c's loops make (a[i * k + p] * b[p * n + j])
  01.02-row-and-column    a 4 x 4 matrix stored row by row (b[p][j] is cell p * n + j): row 1 is
                          cells 4 5 6 7, one apart; column 1 is cells 1 5 9 13, n = 4 apart; ikj's
                          inner loop runs along j, ijk's along p (matmul.c)
  01.03-lanes             matmul_simd.c's vector loop: LANES is 8 with AVX2 and 4 without, so on the
                          lesson's machine (arm64) eight columns are two vectors; p goes four values
                          a step; each vector of c is loaded once, has four products added, and is
                          stored once
  01.04-tiles             matmul_simd is one mul_add_tile over the whole product, so every row of c
                          runs through all of b; matmul_blocked's call gives b's tile (p0..p1,
                          j0..j1) to c's (r0..r1, j0..j1): the same columns, a band of rows. A tile
                          of MM_BLOCK = 128 floats a side is 64 KiB. The 4 x 4 tiles are a drawing,
                          not a size.
  01.05-rows-to-threads   thread t of T gets rows m * t / T up to m * (t + 1) / T (matmul_threads.c):
                          with m = 1000 and T = 4, rows 0, 250, 500, 750 and 1000
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from figlib import Art, cell, code, rich, sans, cw, r1, source, write  # noqa: E402

L, R = 16, 624


def heavy(a, x, y, w, h, cls="s", width=2.5):
    """An outline drawn again over marked cells: a fill of fs alone is too faint in dark mode."""
    a.add(f'<rect class="{cls}" x="{r1(x)}" y="{r1(y)}" width="{r1(w)}" height="{r1(h)}" '
          f'stroke-width="{width}"/>')


def bracket(a, x1, x2, y, cls="m", h=6, down=True):
    """A bracket over x1..x2 with its feet at y, pointing down (over cells) or up (under them)."""
    t = y - h if down else y + h
    a.path(f"M{r1(x1)} {r1(y)}V{r1(t)}H{r1(x2)}V{r1(y)}", cls)


def body(src, name):
    """The text of C function `name` in src, from its signature to the next top-level brace."""
    i = src.index(f"void {name}(")
    return src[i:src.index("\n}\n", i) + 3]


# ====================================================================== 01.01

def row_times_column():
    A = [[1, 2, 3], [4, 5, 6]]
    B = [[7, 8], [9, 10], [11, 12]]
    m, k, n = len(A), len(B), len(B[0])
    assert (m, k, n) == (2, 3, 2) and all(len(r) == k for r in A) and all(len(r) == n for r in B)
    C = [[sum(A[i][p] * B[p][j] for p in range(k)) for j in range(n)] for i in range(m)]
    assert C == [[58, 64], [139, 154]], C
    i, j = 1, 0
    pairs = [(A[i][p], B[p][j]) for p in range(k)]
    prods = [x * y for x, y in pairs]
    assert pairs == [(4, 7), (5, 9), (6, 11)] and prods == [28, 45, 66] and sum(prods) == C[i][j] == 139
    assert "sum += a[i * k + p] * b[p * n + j];" in body(source("matmul.c"), "matmul_ijk")
    line = (f"c[{i}][{j}] = " + " + ".join(f"{x}*{y}" for x, y in pairs) + " = "
            + " + ".join(map(str, prods)) + f" = {C[i][j]}")
    assert line == "c[1][0] = 4*7 + 5*9 + 6*11 = 28 + 45 + 66 = 139", line

    a = Art("rxc", "One element of c: a row of a times a column of b", 204)
    w, h, op = 44, 32, 48                               # a cell; the space an operator takes
    grids = [("a", A, m, k), ("b", B, k, n), ("c", C, m, n)]
    total = sum(c * w for _, _, _, c in grids) + 2 * op
    x = (640 - total) / 2
    top = 34                                            # b, the tallest, starts here
    mid = top + k * h / 2
    where = {}
    for g, (name, M, rows, cols) in enumerate(grids):
        y0 = mid - rows * h / 2
        where[name] = (x, y0)
        for r in range(rows):
            for c in range(cols):
                hot = (name == "a" and r == i) or (name == "b" and c == j)
                me = name == "c" and (r, c) == (i, j)
                cls = "a af" if me else "s fs" if hot else "s f"
                cell(a, r1(x + c * w), r1(y0 + r * h), w, h, str(M[r][c]), cls, "ta" if me else "t", 13, rx=0,
                     weight=700 if me or hot else None)
        a.text(r1(x), r1(y0 - 10), name, "t", 14, weight=700, mono=True)
        a.text(r1(x + cw(14) + 8), r1(y0 - 10), f"{rows} x {cols}", "tm", 11.5)
        if g < 2:
            a.text(r1(x + cols * w + op / 2), r1(mid + 5), ("x", "=")[g], "t", 16, "middle", 600, mono=True)
        x += cols * w + op
    assert abs(x - op - (640 + total) / 2) < 0.01
    # the row and the column, outlined again; the labels that name them
    ax, ay = where["a"]
    bx, by = where["b"]
    heavy(a, ax, ay + i * h, k * w, h)
    heavy(a, bx + j * w, by, w, k * h)
    s = f"row {i}"
    a.text(r1(ax - 10), r1(ay + i * h + h / 2 + 4.2), s, "t", 12, "end", 600)
    assert ax - 10 - sans(s, 12) >= L
    s = f"column {j}"
    a.text(r1(bx + j * w + w / 2), r1(by + k * h + 18), s, "t", 12, "middle", 600)
    assert by + k * h + 18 < 176 - 13
    # the sum, written out
    size = 13
    lx = r1((640 - len(line) * cw(size)) / 2)
    head, tail = line.index(" ="), len(line) - len(str(C[i][j]))
    code(a, lx, 182, line, size, "t", spans=[(0, head, "ta"), (tail, len(line), "ta")], weight=500)
    assert lx >= L and 182 + 10 <= a.h
    return a


# ====================================================================== 01.02

def row_and_column():
    src = source("matmul.c")
    # ijk's inner loop steps p (down a column of b); ikj's steps j (along a row of b)
    assert "for (int p = 0; p < k; p++)\n                sum += a[i * k + p] * b[p * n + j];" in \
        body(src, "matmul_ijk")
    assert "for (int j = 0; j < n; j++)\n                c[i * n + j] += aip * b[p * n + j];" in \
        body(src, "matmul_ikj")
    N, row, col = 4, 1, 1

    def at(p, j):                                       # b[p][j] is b[p * n + j]
        return p * N + j

    row_cells = [at(row, j) for j in range(N)]
    col_cells = [at(p, col) for p in range(N)]
    assert row_cells == [4, 5, 6, 7] and col_cells == [1, 5, 9, 13], (row_cells, col_cells)
    assert [q - p for p, q in zip(row_cells, row_cells[1:])] == [1] * (N - 1)
    assert [q - p for p, q in zip(col_cells, col_cells[1:])] == [N] * (N - 1)

    a = Art("rowcol", "A row is neighbours in memory; a column is a stride", 250)
    gx, gc = L, 22                                      # the small grid: its left, its cell
    sx, sw, sh = 124, 30, 28                            # the strip: its left, a cell's width and height
    assert sx + N * N * sw <= R - 8 and gx + N * gc + 20 <= sx

    def grid(y, marked, cls, tcls):
        for r in range(N):
            for c in range(N):
                kk = at(r, c)
                hot = kk in marked
                cell(a, gx + c * gc, y + r * gc, gc, gc, str(kk), cls if hot else "s f", tcls if hot else "tm", 10,
                     rx=0, weight=700 if hot else None)
        rs, cs = sorted({kk // N for kk in marked}), sorted({kk % N for kk in marked})
        heavy(a, gx + cs[0] * gc, y + rs[0] * gc, len(cs) * gc, len(rs) * gc, cls.split()[0])

    def strip(y, marked, cls, tcls):
        for kk in [kk for kk in range(N * N) if kk not in marked] + marked:      # marked last: edges on top
            hot = kk in marked
            cell(a, sx + kk * sw, y, sw, sh, str(kk), cls if hot else "s f", tcls if hot else "tm", 11.5, rx=0,
                 weight=700 if hot else None)

    def mid(kk):
        return sx + kk * sw + sw / 2

    def rows_named(y):                                  # "row 0" .. "row 3" over or under each run of N
        for r in range(N):
            a.text(r1(sx + (r * N + N / 2) * sw), y, f"row {r}", "tm", 10.5, "middle")
        assert sans("row 0", 10.5) + 8 <= N * sw

    def title(y, loop, what):
        rich(a, gx, y, [(loop, "t", True), (what, "t", False)], 12.5, weight=600)
        return gx + len(loop) * cw(12.5) + sans(what, 12.5)

    # ikj: along row 1, one cell after another
    g1 = 26
    title(16, "ikj", " reads b by rows")
    grid(g1, row_cells, "s fs", "t")
    s1 = g1 + N * gc / 2 - sh / 2
    rows_named(s1 - 7)
    assert s1 - 7 - 11 > 16
    strip(s1, row_cells, "s fs", "t")
    heavy(a, sx + row_cells[0] * sw, s1, N * sw, sh)
    lo, hi = sx + row_cells[0] * sw + 3, sx + (row_cells[-1] + 1) * sw - 3
    bracket(a, lo, hi, s1 + sh + 5, "s", down=False)
    a.text(r1((lo + hi) / 2), r1(s1 + sh + 26), "one after another", "t", 12, "middle", 600)
    # ijk: down column 1, n cells a hop
    g2 = 154
    t2 = 142
    assert t2 - 13 > s1 + sh + 26 and t2 - 13 > g1 + N * gc
    end = title(t2, "ijk", " reads b by columns")
    grid(g2, col_cells, "a af", "ta")
    s2 = g2 + N * gc / 2 - sh / 2
    up = s2 - 20
    for p, q in zip(col_cells, col_cells[1:]):
        a.path(f"M{r1(mid(p))} {r1(s2 - 2)}C{r1(mid(p) + 12)} {r1(up)} {r1(mid(q) - 12)} {r1(up)} "
               f"{r1(mid(q) - 1)} {r1(s2 - 3)}", "a", arrow=True)
        hx = (mid(p) + mid(q)) / 2
        rich(a, r1(hx), r1(up - 2), [("+n", "ta", True)], 12, "middle", 700)
        assert hx - cw(12) > end + 8 and up - 2 - 12 > t2
    s = "n = 4"
    a.text(R - 8, r1(up - 2), s, "tm", 11.5, "end", mono=True)
    assert R - 8 - len(s) * cw(11.5) > (mid(col_cells[-2]) + mid(col_cells[-1])) / 2 + cw(12) + 8
    strip(s2, col_cells, "a af", "ta")
    rows_named(r1(s2 + sh + 15))
    assert s2 + sh + 15 + 6 <= a.h and g2 + N * gc + 6 <= a.h
    return a


# ====================================================================== 01.03

def lanes():
    src = source("matmul_simd.c")
    m = re.search(r"#if defined\(__AVX2__\)\n#define LANES (\d+)\n#else\n#define LANES (\d+)\n#endif", src)
    avx2, here = int(m.group(1)), int(m.group(2))
    assert (avx2, here) == (8, 4), (avx2, here)         # the lesson's machine is arm64: no AVX2, NEON's 4
    k = body(src, "mul_add_tile")
    assert "for (; p + 4 <= p1; p += 4) {" in k
    assert "vec a0 = splat(s0), a1 = splat(s1), a2 = splat(s2), a3 = splat(s3);" in k
    loop = k[k.index("for (; j + LANES <= j1; j += LANES) {"):]
    loop = loop[:loop.index("\n            }\n")]
    assert loop.count("load(ci + j)") == 1 and loop.count("store(ci + j, cv)") == 1, loop
    adds = re.findall(r"cv \+= a(\d) \* load\(b(\d) \+ j\);", loop)
    assert adds == [(str(q), str(q)) for q in range(4)], adds
    cols, ps = 8, len(adds)
    vecs = cols // here
    assert (cols, ps, vecs) == (8, 4, 2) and cols == avx2

    a = Art("lanes", "Eight columns of c and four values of p: two steps of the inner loop with 4-float vectors, one with AVX2", 266)
    tx, ms = 92, 11                                     # the text column; its mono size
    cx, lw, lh, vgap = 388, 26, 22, 18                  # the cells: left, a lane, a row's height, the gap
    vw = here * lw
    assert cx + vecs * vw + (vecs - 1) * vgap <= R

    def product(pq):
        """'a[i][p+1]  in every lane  x b[p+1][j .. j+7]' on the mono grid, "in every lane" muted."""
        s = f"{f'a[i][{pq}]':<10}in every lane  x b[{pq}][j .. j+7]"
        assert tx + len(s) * cw(ms) + 10 <= cx, s
        return s, [(10, 10 + len("in every lane"), "tm")]

    def lane_row(y, cls, tcls=None):
        for v in range(vecs):
            for ln in range(here):
                a.box(r1(cx + v * (vw + vgap) + ln * lw), y, lw, lh, cls, rx=0)

    def mid(y):
        return r1(y + lh / 2 + 4)

    # the vector: four floats here
    cy = 52
    bl, br = cx + 2, cx + vw - 2
    bracket(a, bl, br, cy - 7, "s")
    for n_, s in enumerate((f"a vector: {here} floats here,", f"{avx2} with AVX2")):
        yy = 16 + n_ * 14
        a.text(r1((bl + br) / 2), yy, s, "t", 11.5, "middle", 600)
        half = sans(s, 11.5) / 2
        assert (bl + br) / 2 - half > tx + len("c[i][j .. j+7]") * cw(ms) and (bl + br) / 2 + half < R
    # load once: c's eight columns
    a.text(L, mid(cy), "load once", "t", 12, weight=700)
    a.text(tx, mid(cy), "c[i][j .. j+7]", "t", ms, mono=True)
    assert L + sans("load once", 12) <= tx - 4
    lane_row(cy, "s f")
    # four values of p: a[i][p + q] in every lane, times row p + q of b
    py0, pitch = cy + 38, 28
    for q in range(ps):
        y = py0 + q * pitch
        pq = "p" if q == 0 else f"p+{q}"
        a.text(tx - 10, mid(y), "+", "t", 13, "end", 700, mono=True)
        s, spans = product(pq)
        code(a, tx, mid(y), s, ms, "t", spans)
        lane_row(y, "s fs")
    # the sum stays in the register, then goes back: store once
    rule = py0 + (ps - 1) * pitch + lh + 10
    a.line(cx - 6, rule, cx + vecs * vw + (vecs - 1) * vgap + 6, rule, "s")
    ay = rule + 8
    a.text(L, mid(ay), "store once", "t", 12, weight=700)
    a.text(tx, mid(ay), "c[i][j .. j+7]", "t", ms, mono=True)
    assert L + sans("store once", 12) <= tx - 4
    lane_row(ay, "a af")
    # which columns each vector holds
    for v in range(vecs):
        lo = v * here
        s = f"j .. j+{lo + here - 1}" if lo == 0 else f"j+{lo} .. j+{lo + here - 1}"
        a.text(r1(cx + v * (vw + vgap) + vw / 2), r1(ay + lh + 16), s, "tm", 10.5, "middle", mono=True)
        assert len(s) * cw(10.5) + 6 <= vw + vgap
    assert ay + lh + 16 + 6 <= a.h
    return a


# ====================================================================== 01.04

def tiles():
    simd = source("matmul_simd.c")
    blocked = source("matmul_blocked.c")
    # simd: one call over every row, every p, every column
    assert "mul_add_tile(a, b, c, k, n, 0, m, 0, k, 0, n);" in body(simd, "matmul_simd")
    # mul_add_tile's ranges: rows i of c, values p, columns j; c[i][j] += a[i][p] * b[p][j]
    sig = re.search(r"void mul_add_tile\(([^)]*)\)", simd).group(1)
    names = [s.split()[-1] for s in sig.split(",")]
    assert names[-6:] == ["i0", "i1", "p0", "p1", "j0", "j1"], names
    assert "Add to c[i][j], for i in [i0, i1) and j in [j0, j1), the sum over p in\n * [p0, p1) of a[i][p] * b[p][j]." \
        in simd
    # blocked: rows r0..r1, then p0..p1, then columns j0..j1: b's tile (p, j) goes to c's tile (r, j)
    rows = body(blocked, "blocked_rows")
    call = re.search(r"mul_add_tile\(a, b, c, k, n, (\w+), (\w+), (\w+), (\w+), (\w+), (\w+)\);", rows).groups()
    assert call == ("r0", "r1", "p0", "p1", "j0", "j1"), call
    assert rows.index("r0 = i0") < rows.index("p0 = 0") < rows.index("j0 = 0")
    block = int(re.search(r"#define MM_BLOCK (\d+)", blocked).group(1))
    assert block == 128 and block * block * 4 == 64 * 1024

    T = 4                                               # tiles a side, as drawn
    bt, ct = (3, 1), (0, 1)                             # b's tile (p, j); c's tile (r, j): the same j
    assert bt[1] == ct[1]

    a = Art("tiles", "Without tiles every row of c reads all of b; with them a tile of b serves a whole band of rows",
            282)
    S, gap = 100, 40                                    # a square's side; the gap between b and c
    by, cy = 32, 32 + S + gap
    tw = S / T
    a.line(320, 10, 320, a.h - 10, "m", width=1)

    def square(px, name, y, cls="s f"):
        x = px + 20
        a.box(x, y, S, S, cls, rx=0)
        a.text(x - 8, r1(y + S / 2 + 5), name, "t", 14, "end", 700, mono=True)
        return x

    def tiled(x, y):
        for t in range(1, T):
            a.line(r1(x + t * tw), y, r1(x + t * tw), y + S, "m", width=1)
            a.line(x, r1(y + t * tw), x + S, r1(y + t * tw), "m", width=1)

    def label(x, y0, y1, s):
        a.text(r1(x + 10), r1((y0 + y1) / 2 + 4), s, "t", 12, weight=600)
        return x + 10 + sans(s, 12)

    # simd: every row of c, all of b
    px = L
    a.text(px, 16, "simd", "t", 13, weight=700, mono=True)
    x = square(px, "b", by, "s fs")
    heavy(a, x, by, S, S)
    square(px, "c", cy)
    ry, rh = cy + 16, 9
    a.box(x, ry, S, rh, "s fs", rx=0)
    heavy(a, x, ry, S, rh, width=2)
    ax = x + S / 2
    a.line(ax, by + S + 3, ax, ry - 4, "s", arrow=True)
    assert label(ax, by + S, cy, "all of b, for this one row") <= 320 - 8
    # blocked: one tile of b, a band of rows of c
    px = 336
    a.text(px, 16, "blocked", "t", 13, weight=700, mono=True)
    x = square(px, "b", by)
    tiled(x, by)
    tx, ty = x + bt[1] * tw, by + bt[0] * tw
    a.box(r1(tx), r1(ty), r1(tw), r1(tw), "a af", rx=0)
    square(px, "c", cy)
    tiled(x, cy)
    ux, uy = x + ct[1] * tw, cy + ct[0] * tw
    a.box(r1(ux), r1(uy), r1(tw), r1(tw), "s fs", rx=0)
    for r in range(1, 4):                               # a band: several rows
        a.line(r1(ux + 3), r1(uy + r * tw / 4), r1(ux + tw - 3), r1(uy + r * tw / 4), "m", width=1)
    heavy(a, ux, uy, tw, tw, width=2)
    ax = tx + tw / 2
    assert abs(ax - (ux + tw / 2)) < 0.01                 # straight down: the same columns
    a.line(r1(ax), r1(ty + tw + 3), r1(ax), r1(uy - 4), "s", arrow=True)
    assert label(ax, by + S, cy, "this tile, for all these rows") <= R
    # the cache: a swatch of each tile beside its name
    kx, kw = x + S + 16, R - (x + S + 16)
    kh, sq = 78, 12
    ky = r1(cy + (S - kh) / 2)
    a.box(r1(kx), ky, r1(kw), kh, "s f", rx=8)
    a.text(r1(kx + 12), r1(ky + 20), "in the cache:", "t", 12, weight=700)
    for n_, (s, cls) in enumerate((("one tile of b,", "a af"), ("one of c", "s fs"))):
        yy = ky + 40 + n_ * 20
        a.box(r1(kx + 12), r1(yy - 10), sq, sq, cls, rx=0)
        if cls == "s fs":
            heavy(a, kx + 12, yy - 10, sq, sq, width=2)
        a.text(r1(kx + 12 + sq + 8), r1(yy), s, "t", 12, weight=500)
        assert 12 + sq + 8 + sans(s, 12) + 8 <= kw, s
    assert sans("in the cache:", 12) + 24 <= kw and ky + 40 + 20 + 10 <= ky + kh
    assert cy + S + 6 <= a.h
    return a


# ====================================================================== 01.05

def rows_to_threads():
    src = source("matmul_threads.c")
    mt = body(src, "matmul_threads")
    assert "shares[t] = (struct share){a, b, c, k, n, m * t / count, m * (t + 1) / count};" in mt
    assert "blocked_rows(s->a, s->b, s->c, s->k, s->n, s->i0, s->i1);" in src
    m, T, hot = 1000, 4, 1
    bands = [(m * t // T, m * (t + 1) // T) for t in range(T)]
    assert bands == [(0, 250), (250, 500), (500, 750), (750, 1000)], bands
    assert all(hi == lo2 for (_, hi), (lo2, _) in zip(bands, bands[1:])) and bands[0][0] == 0 and bands[-1][1] == m

    a = Art("rows", "Each thread owns a band of c's rows; all of them read a and b", 268)
    S = 90                                              # a and b
    sx, ay, by = 50, 30, 140
    cx, cy, cwid, chh = 300, 30, 180, 200               # c
    bh = chh / T
    foot = cy + chh + 24                                # the baseline of the two labels at the bottom
    # a and b in one frame, its label inside: the label is about both
    fx, fy, fw = L, 14, sx + S + 20 - L
    a.box(fx, fy, fw, foot + 10 - fy, "m", rx=10)
    for name, y in (("a", ay), ("b", by)):
        a.box(sx, y, S, S, "s f", rx=0)
        a.text(sx - 10, r1(y + S / 2 + 5), name, "t", 14, "end", 700, mono=True)
        assert sx - 10 - cw(14) >= fx + 8
    s = "read by every thread"
    a.text(r1(fx + fw / 2), foot, s, "t", 12, "middle", 600)
    assert sans(s, 12) + 8 <= fw and by + S + 12 <= foot - 12
    # c, a band a thread
    a.text(r1(cx + cwid / 2), cy - 10, "c", "t", 14, "middle", 700, mono=True)
    for t in range(T):
        y = cy + t * bh
        on = t == hot
        a.box(cx, r1(y), cwid, r1(bh), "a af" if on else "s f", rx=0)
    for t in range(T):                                  # the accent band's edges on top
        y = cy + t * bh
        on = t == hot
        if on:
            a.box(cx, r1(y), cwid, r1(bh), "a", rx=0)
        a.text(r1(cx + cwid / 2), r1(y + bh / 2 + 4.5), f"thread {t}", "ta" if on else "t", 12.5, "middle",
               700 if on else 500)
        lo, hi = bands[t]
        rs = f"rows {lo} to {hi - 1}"
        a.text(cx + cwid + 12, r1(y + bh / 2 + 4), rs, "ta" if on else "tm", 11, weight=600 if on else None,
               mono=True)
        assert cx + cwid + 12 + len(rs) * cw(11) <= R
    a.text(cx + cwid + 12, cy - 10, f"m = {m}", "tm", 11, mono=True)
    # a and b both feed all of c: a bracket the height of c, the arrows into its middle
    kx, kmid = cx - 16, cy + chh / 2
    a.path(f"M{kx + 8} {cy}H{kx}V{cy + chh}H{kx + 8}", "s")
    a.path(f"M{kx} {r1(kmid)}H{kx - 8}", "s")
    for y in (ay + S / 2, by + S / 2):
        a.path(f"M{sx + S + 4} {r1(y)}C{sx + S + 70} {r1(y)} {kx - 70} {r1(kmid)} {kx - 12} {r1(kmid)}", "s",
               arrow=True)
    assert sx + S + 70 < kx - 70
    s = "no two threads write the same row, so no lock"
    a.text(r1(cx + cwid / 2), foot, s, "t", 12, "middle", 600)
    half = sans(s, 12) / 2
    assert cx + cwid / 2 - half > fx + fw + 8
    assert cx + cwid / 2 + half <= R and foot + 10 + 4 <= a.h
    return a


FIGURES = [
    ("01.01-row-times-column", row_times_column),
    ("01.02-row-and-column", row_and_column),
    ("01.03-lanes", lanes),
    ("01.04-tiles", tiles),
    ("01.05-rows-to-threads", rows_to_threads),
]


def main(argv):
    for name, fn in FIGURES:
        if argv and not any(name.startswith(p) for p in argv):
            continue
        write(name, fn())


if __name__ == "__main__":
    main(sys.argv[1:])
