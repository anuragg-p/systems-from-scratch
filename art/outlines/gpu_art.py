"""Art for the GPU kernels outline (outlines/gpu-kernels.md, id gpu): modules 00 to 04, and the
track's own pair. Modules 05 to 09 are drawn by gpu_art_b.py.

Writes, under outlines/gpu-kernels/:
    art.svg         280x160, the track's picture on its home page card (one .draw path moves on hover)
    icon.svg        20x20 currentColor line icon for the top bar
    NN/cover.svg    640x300 teaching diagram for module NN (00 to 04)
    NN/icon.svg     20x20 currentColor line icon for module NN

Covers style themselves only through the .art classes in harness/web/app.css:
    s m a        stroke: foreground, muted, accent
    f fs af fa   fill: page, code background, accent-soft, accent
    t tm ta      text fill: foreground, muted, accent      mono: monospace
One accent idea a cover: the accent classes mark the single thing the cover is about. No cover
shows a timing, a speed-up or a bar drawn to a made-up height: the reader measures those.

Code is set on a monospace grid: a line of code is split into runs of text, and each run is
placed at its own column (x = left + column * 0.6em, Geist Mono's advance), so indentation and
double spaces survive SVG's whitespace collapsing.

Computed here, and asserted, so a typo stops the script instead of reaching a cover:
    art the thread's cells in its row: range(0, 8, 3) == [0, 3, 6]
    00  six timed runs (TIMED, shared with art/gpu/figs00.py), all different and all shorter than the
        warm-up, the fastest among them; no number is drawn from their lengths
    01  a 4x4 matrix stored row by row: row 1 is cells [4, 5, 6, 7], column 1 is [1, 5, 9, 13],
        each step down the column N = 4 cells on
    02  d = 12 values, blockDim.x = 4: thread t takes range(t, 12, 4), [0, 4, 8] to [3, 7, 11]
    03  C tile (1, 2) needs A tiles (1, k) and B tiles (k, 2) for k = 0..3; the pair drawn is k = 0
    04  the xor shuffle run on eight lanes: each row v[i] + v[i ^ mask], the last all 31 == sum(start)

The Art class is the one from nand_art.py, repeated so this file stands alone.

    python3 art/outlines/gpu_art.py [NN ...]
        write every file (or only modules NN), then check each one is ASCII and survives
        harness/web/art.py's sanitizer unchanged
"""
import html
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "outlines", "gpu-kernels")
SW = 'stroke-width="1.5"'
EM = 0.6            # the monospace advance, in em (Geist Mono, SF Mono, Menlo)
SANS = 0.56         # a generous average advance for Figtree, in em


def esc(s):
    return html.escape(s, quote=True)


class Art:
    def __init__(self, key, title, h=300):
        self.key, self.title, self.out, self.h = key, title, [], h

    def add(self, s):
        self.out.append(s)

    def box(self, x, y, w, h, cls="s f", rx=10, dash=False):
        d = ' stroke-dasharray="4 4"' if dash else ""
        self.add(f'<rect class="{cls}" x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" {SW}{d}/>')

    def text(self, x, y, s, cls="t", size=12, anchor="start", weight=None, mono=False):
        assert size >= 10, (self.key, s, size)
        c = cls + (" mono" if mono else "")
        wt = f' font-weight="{weight}"' if weight else ""
        a = f' text-anchor="{anchor}"' if anchor != "start" else ""
        self.add(f'<text class="{c}" x="{x}" y="{y}" font-size="{size}"{wt}{a}>{esc(s)}</text>')

    def marker(self, cls):
        return {"a": "aa", "m": "am"}.get(cls.split()[0], "ah")

    def line(self, x1, y1, x2, y2, cls="s", arrow=False, dash=False, width=None):
        m = f' marker-end="url(#{self.key}-{self.marker(cls)})"' if arrow else ""
        d = ' stroke-dasharray="4 4"' if dash else ""
        sw = f'stroke-width="{width}"' if width else SW
        self.add(f'<line class="{cls}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" {sw} stroke-linecap="round"{m}{d}/>')

    def path(self, d, cls="s", arrow=False, dash=False):
        m = f' marker-end="url(#{self.key}-{self.marker(cls)})"' if arrow else ""
        da = ' stroke-dasharray="4 4"' if dash else ""
        self.add(f'<path class="{cls}" d="{d}" {SW} stroke-linecap="round" stroke-linejoin="round"{m}{da}/>')

    def circle(self, cx, cy, r, cls="s f"):
        self.add(f'<circle class="{cls}" cx="{cx}" cy="{cy}" r="{r}" {SW}/>')

    def svg(self):
        def mk(name, cls):
            return (f'<marker id="{self.key}-{name}" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" '
                    f'markerHeight="7" orient="auto-start-reverse"><path class="{cls}" d="M1 1.5L8.5 5L1 8.5" {SW} '
                    f'stroke-linecap="round" stroke-linejoin="round"/></marker>')
        defs = f'<defs>{mk("ah", "s")}{mk("aa", "a")}{mk("am", "m")}</defs>'
        body = "\n".join(self.out)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 {self.h}" fill="none">\n'
                f'<title>{esc(self.title)}</title>\n{defs}\n{body}\n</svg>\n')


def cell(a, x, y, w, h, s, cls="s f", tcls="t", size=12, rx=4, dash=False, weight=None, mono=True, under=False):
    """A box with one centred label: a value, an index, a chip's name. under puts a page-coloured box
    beneath it first, for a see-through fill (af) drawn over a line."""
    if under:
        a.add(f'<rect class="f" x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}"/>')
    a.box(x, y, w, h, cls, rx=rx, dash=dash)
    if s:
        a.text(round(x + w / 2, 1), round(y + h / 2 + size * 0.35, 1), s, tcls, size, "middle", weight, mono)


def code(a, x, y, s, size=11.5, cls="t", spans=(), weight=None):
    """One line of code on the monospace grid: column c sits at x + c * 0.6em. spans is a list of
    (start, end, class) that recolour columns start..end-1. Runs split at two or more spaces, at a
    leading indent and at a change of class, each run a tspan placed at its own column."""
    kinds = [cls] * len(s)
    for st, en, c in spans:
        for i in range(st, en):
            kinds[i] = c
    runs, i = [], 0
    while i < len(s):
        if s[i] == " ":
            i += 1
            continue
        j = i
        while j < len(s):
            if s[j] == " ":
                if j + 1 < len(s) and s[j + 1] != " " and kinds[j + 1] == kinds[i]:
                    j += 1
                    continue
                break
            if kinds[j] != kinds[i]:
                break
            j += 1
        runs.append((i, s[i:j], kinds[i]))
        i = j
    cw_ = EM * size
    wt = f' font-weight="{weight}"' if weight else ""
    assert size >= 10
    if len(runs) == 1 and runs[0][0] == 0:
        a.add(f'<text class="{runs[0][2]} mono" x="{x}" y="{y}" font-size="{size}"{wt}>{esc(runs[0][1])}</text>')
        return
    spans_out = "".join(
        f'<tspan x="{round(x + c * cw_, 2)}"{"" if k == cls else f" class={chr(34)}{k}{chr(34)}"}>{esc(t)}</tspan>'
        for c, t, k in runs)
    a.add(f'<text class="{cls} mono" x="{x}" y="{y}" font-size="{size}"{wt}>{spans_out}</text>')


def rich(a, x, y, parts, size=11, anchor="start", weight=None, cls="t"):
    """Text whose parts flow one after another: parts is a list of (text, class, mono)."""
    assert size >= 10
    wt = f' font-weight="{weight}"' if weight else ""
    an = f' text-anchor="{anchor}"' if anchor != "start" else ""
    inner = ""
    for t, c, mono in parts:
        k = (c or cls) + (" mono" if mono else "")
        inner += f'<tspan class="{k}">{esc(t)}</tspan>'
    a.add(f'<text class="{cls}" x="{x}" y="{y}" font-size="{size}"{wt}{an}>{inner}</text>')


def cw(size):
    return EM * size


def sans(s, size):
    """A generous width for sans text s at size: enough to keep it clear of its neighbours."""
    return len(s) * size * SANS


def r1(v):
    return round(v, 1)


# =================================================================== the track's own pair

def track_art():
    """280x160: three thread blocks of eight; in the middle one, one thread strides its row, landing
    on cells 0, 3 and 6. The stride is the one moving path."""
    stride = list(range(0, 8, 3))
    assert stride == [0, 3, 6], stride
    n, cwid, ch, pitch = 8, 20, 16, 26
    bw = (n - 1) * pitch + cwid + 2 * 11            # the block: its eight cells and a margin
    bh, gap = 42, 8
    bx = (280 - bw) / 2
    y0 = (160 - 3 * bh - 2 * gap) / 2
    assert bx >= 8 and y0 >= 8, (bx, y0)
    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 280 160" fill="none">']
    top_mid = None
    for b in range(3):
        by = y0 + b * (bh + gap)
        out.append(f'<rect class="s" x="{r1(bx)}" y="{r1(by)}" width="{bw}" height="{bh}" rx="8" stroke-width="1.5" '
                   f'stroke-dasharray="4 4"/>')
        cy = by + bh - 8 - ch                       # the cells sit low, leaving room above for the hops
        for c in range(n):
            hot = b == 1 and c in stride
            cls = "a fa" if hot else "s f"
            out.append(f'<rect class="{cls}" x="{r1(bx + 11 + c * pitch)}" y="{r1(cy)}" width="{cwid}" height="{ch}" '
                       f'rx="3" stroke-width="1.5"/>')
        if b == 1:
            top_mid = cy
    # one thread's stride: arcs over the middle row, from cell 0 to 3 to 6
    xs = [bx + 11 + c * pitch + cwid / 2 for c in stride]
    yt, up = top_mid - 2, top_mid - 18
    apex = yt - 0.75 * (yt - up)                    # a cubic with both controls at up peaks 3/4 of the way
    assert apex > y0 + bh + gap + 3, apex           # the hops stay inside the middle block
    d = f"M{r1(xs[0])} {r1(yt)}"
    for x1, x2 in zip(xs, xs[1:]):
        d += f"C{r1(x1 + 6)} {r1(up)} {r1(x2 - 6)} {r1(up)} {r1(x2)} {r1(yt)}"
    out.append(f'<path class="a draw" d="{d}" pathLength="1" stroke-width="2.5" stroke-linecap="round" '
               f'stroke-linejoin="round"/>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


# a graphics card: a wide board, two fans, three pins under its left half
TRACK_ICON = ('<rect x="1.5" y="4" width="17" height="10" rx="1.5"/><circle cx="6.25" cy="9" r="2.4"/>'
              '<circle cx="13.75" cy="9" r="2.4"/><path d="M3.5 14v2.5M6 14v2.5M8.5 14v2.5"/>')


# =================================================================== 00 The workbench

# One measurement as module 00 draws it, in this cover and in lesson 00.03's figure 00.03-runs
# (art/gpu/figs00.py imports these): the warm-up run, then six timed runs in the order they ran.
# Lengths only, relative to the warm-up's: no number is ever drawn from them, and they are not a
# measurement; what matters is which is longest (the warm-up), which is shortest (the fastest) and
# where the middle falls.
WARMUP = 1.0
TIMED = [0.71, 0.66, 0.74, 0.62, 0.69, 0.72]


def runs_median(times):
    """bench.c's median: the middle run, or the mean of the two middle ones."""
    s = sorted(times)
    k = len(s) // 2
    return s[k] if len(s) % 2 else (s[k - 1] + s[k]) / 2


def runs_check():
    """The picture's facts: six timed runs, all different, all shorter than the warm-up; one fastest."""
    assert len(TIMED) == 6 and len(set(TIMED)) == 6, TIMED
    assert max(TIMED) < WARMUP, TIMED
    fastest = TIMED.index(min(TIMED))
    assert fastest not in (0, len(TIMED) - 1)            # among the runs, not at either end
    med = runs_median(TIMED)
    assert min(TIMED) < med < max(TIMED) and med not in TIMED, med
    return fastest, med


def workbench():
    a = Art("g00", "Trust the answer, then trust the time")
    # top: one input into the plain version and the version under test, a compare under both
    n, w, sy, sh = 8, 16, 18, 18
    sx = 320 - n * w / 2
    a.text(sx - 10, sy + 13, "input", "t", 12, "end", 600)
    for i in range(n):
        a.box(sx + i * w, sy, w, sh, "s f", rx=0)
    bw, by, bh = 224, 58, 32
    lc, rc = 196, 444                               # the two boxes' centres
    assert rc - lc > bw                             # side by side, not touching
    boxes = [(lc, "the plain version"), (rc, "the version under test")]
    for cx, label in boxes:
        assert sans(label, 12) + 20 <= bw, label
        cell(a, cx - bw / 2, by, bw, bh, label, "s f", "t", 12, rx=8, mono=False)
    a.path(f"M320 {sy + sh}V{sy + sh + 10}H{lc}V{by - 2}", arrow=True)
    a.path(f"M320 {sy + sh + 10}H{rc}V{by - 2}", arrow=True)
    cmp_ = "compare: every element within its allowance?"
    cwid_, cy, chh = 336, 110, 32
    assert sans(cmp_, 12) + 20 <= cwid_ and 320 - cwid_ / 2 < lc and 320 + cwid_ / 2 > rc
    for cx, _ in boxes:
        a.line(cx, by + bh, cx, cy - 2, arrow=True)
    cell(a, 320 - cwid_ / 2, cy, cwid_, chh, cmp_, "s f", "t", 12, rx=8, mono=False)
    # bottom: one measurement. The warm-up run, thrown away; six timed runs, each drawn from the same
    # start; the fastest in accent. Labels at the left, "timed runs" bracketed at the right.
    fastest, _ = runs_check()
    x0, L = 184, 344                                # where every run starts; the warm-up's length
    wy, ty, bh2, pitch, ay = 164, 184, 10, 14, 276  # the warm-up bar, the first timed bar, bar height, pitch, axis
    ends = [x0 + t * L for t in TIMED]
    assert wy + bh2 + 8 <= ty and ty + 5 * pitch + bh2 + 8 <= ay <= 284 and cy + chh + 16 <= wy
    a.box(x0, wy, L * WARMUP, bh2, "m f", rx=3, dash=True)
    for k, end in enumerate(ends):
        if k != fastest:
            a.box(x0, ty + k * pitch, r1(end - x0), bh2, "s fs", rx=3)
    a.box(x0, ty + fastest * pitch, r1(ends[fastest] - x0), bh2, "a af", rx=3)
    lab = [("warm-up: not counted", wy, "tm", 11.5, None), ("the fastest: reported", ty + fastest * pitch, "ta", 12, 600)]
    for s, y, cls, size, wt in lab:
        a.text(x0 - 12, y + bh2 / 2 + size * 0.35, s, cls, size, "end", wt)
        assert x0 - 12 - sans(s, size) >= 16, s
    bx = r1(max(ends) + 14)                         # the bracket round the six timed runs
    yt, yb = ty - 2, ty + 5 * pitch + bh2 + 2
    a.path(f"M{bx - 5} {yt}H{bx}V{yb}H{bx - 5}", "m")
    a.text(bx + 10, r1((yt + yb) / 2 + 4), "timed runs", "t", 11.5)
    assert bx + 10 + sans("timed runs", 11.5) <= 624 - 8
    # the time axis: every run measured from its own start
    xe = x0 + L * WARMUP + 40
    a.path(f"M{x0} {wy - 6}V{ay}H{xe}", arrow=True)
    a.text(xe + 8, ay + 4, "time", "tm", 11)
    assert xe + 8 + sans("time", 11) <= 632
    return a


# =================================================================== 01 Matrix multiply on the CPU

def cpu_matmul():
    a = Art("g01", "A row is neighbours, a column is strides")
    N, row, col = 4, 1, 1
    row_cells = [row * N + j for j in range(N)]       # stored row by row: element (i, j) is cell i * N + j
    col_cells = [i * N + col for i in range(N)]
    assert row_cells == [4, 5, 6, 7] and col_cells == [1, 5, 9, 13], (row_cells, col_cells)
    hops = [q - p for p, q in zip(col_cells, col_cells[1:])]
    assert hops == [N, N, N], hops
    gx, gc = 24, 13                                   # the small grid: its left, its cell
    sx, cwid, ch = 112, 30, 26                        # the strip: its left, cell width, height
    assert sx + N * N * cwid <= 624 and gx + N * gc + 24 <= sx

    def grid(y, marked):
        for r in range(N):
            for c in range(N):
                k = r * N + c
                a.box(gx + c * gc, y + r * gc, gc, gc, "s fs" if k in marked else "s f", rx=0)
        # the marked row or column again, with a heavier edge: fs alone is too faint in dark mode
        rs, cs = sorted({k // N for k in marked}), sorted({k % N for k in marked})
        assert len(rs) == 1 or len(cs) == 1
        x, yy = gx + cs[0] * gc, y + rs[0] * gc
        a.add(f'<rect class="s" x="{x}" y="{yy}" width="{len(cs) * gc}" height="{len(rs) * gc}" stroke-width="2.5"/>')

    def strip(y, marked, cls, tcls):
        cells = [k for k in range(N * N) if k not in marked] + list(marked)   # marked last: their edges on top
        for k in cells:
            hot = k in marked
            cell(a, sx + k * cwid, y, cwid, ch, str(k), cls if hot else "s f", tcls if hot else "tm", 11, rx=0,
                 weight=700 if hot else None)

    def cx(k):
        return sx + k * cwid + cwid / 2

    # strip one: A, row 1, four neighbours
    g1 = 42
    a.text(gx, g1 - 8, "A, row 1", "t", 12, weight=600)
    grid(g1, row_cells)
    s1 = g1 + N * gc / 2 - ch / 2
    strip(s1, row_cells, "s fs", "t")
    bry = s1 + ch + 6
    lo, hi = sx + row_cells[0] * cwid, sx + (row_cells[-1] + 1) * cwid
    a.path(f"M{lo + 3} {bry}V{bry + 5}H{hi - 3}V{bry}", "m")
    a.text(r1((lo + hi) / 2), bry + 20, "next to each other: one cache line", "t", 11.5, "middle")
    # strip two: B, column 1, a stride of N between each
    g2 = 146
    a.text(gx, g2 - 8, "B, column 1", "t", 12, weight=600)
    grid(g2, col_cells)
    s2 = g2 + N * gc / 2 - ch / 2
    up = s2 - 20
    assert up - 14 > bry + 20 + 4                      # the hop labels clear caption one
    for p, q in zip(col_cells, col_cells[1:]):
        a.path(f"M{cx(p)} {s2 - 2}C{cx(p) + 10} {up} {cx(q) - 10} {up} {cx(q) - 1} {s2 - 3}", "a", arrow=True)
        rich(a, (cx(p) + cx(q)) / 2, up - 2, [("+N", "ta", True)], 12, "middle", 700)
    strip(s2, col_cells, "a af", "ta")
    rich(a, r1((cx(col_cells[0]) + cx(col_cells[-1])) / 2), s2 + ch + 20,
         [("N", "t", True), (" apart: a new cache line each step", "t", False)], 11.5, "middle")
    # the five versions, then the library
    chips = ["3 loops", "reordered", "SIMD", "blocked", "threads", "BLAS"]   # the lessons' order, then the library
    ws = [max(56, round(sans(c, 12) + 24)) for c in chips]
    arr = 30
    total = sum(ws) + arr * (len(chips) - 1)
    x, y, h = (640 - total) / 2, 238, 28
    assert x >= 16 and y + h <= 284
    for k, (name, w) in enumerate(zip(chips, ws)):
        last = k == len(chips) - 1
        cell(a, r1(x), y, w, h, name, "m f" if last else "s f", "tm" if last else "t", 12, rx=8, dash=last,
             weight=600, mono=False)
        if not last:
            a.line(r1(x + w + 3), y + h / 2, r1(x + w + arr - 3), y + h / 2,
                   "m" if k == len(chips) - 2 else "s", arrow=True, dash=k == len(chips) - 2)
        x += w + arr
    return a


# =================================================================== 02 Threads, blocks and a grid

def threads():
    a = Art("g02", "One block per token, each thread strides the row")
    tokens, d, bdim, hot = 4, 12, 4, 1
    lanes = [list(range(t, d, bdim)) for t in range(bdim)]
    assert lanes == [[0, 4, 8], [1, 5, 9], [2, 6, 10], [3, 7, 11]], lanes
    assert sorted(sum(lanes, [])) == list(range(d))            # every cell taken once
    # left: the tensor, one row a block
    tsize = 11
    rich(a, 24, 40, [("input ", "t", False), ("[num_tokens, d]", "t", True)], 12, weight=600)
    rx0, rw, rh, rp, ry0 = 126, 90, 20, 28, 52
    assert 24 + len("blockIdx.x = 0") * cw(tsize) + 8 <= rx0
    for r in range(tokens):
        y = ry0 + r * rp
        on = r == hot
        a.box(rx0, y, rw, rh, "s fs" if on else "m f", rx=3)
        for k in range(1, d):
            xk = r1(rx0 + k * rw / d)
            a.line(xk, y + 3, xk, y + rh - 3, "m", width=1)
        a.text(24, y + rh / 2 + 4, f"blockIdx.x = {r}", "t" if on else "tm", tsize, weight=600 if on else None,
               mono=True)
    # right: row 1 opened out, d cells, blockDim.x threads striding it
    cx0, cwid, ch, cy = 300, 26, 28, 60
    assert cx0 + d * cwid <= 616
    rich(a, cx0, 44, [("blockDim.x = 4", "t", True), (" threads", "t", False)], 12, weight=600)
    a.text(cx0 + d * cwid, 44, f"d = {d}", "tm", 11.5, "end", mono=True)
    hy = ry0 + hot * rp
    a.line(rx0 + rw + 4, hy, cx0 - 4, cy, "m", dash=True)
    a.line(rx0 + rw + 4, hy + rh, cx0 - 4, cy + ch, "m", dash=True)
    mine = lanes[hot]
    for k in [k for k in range(d) if k not in mine] + mine:
        on = k in mine
        cell(a, cx0 + k * cwid, cy, cwid, ch, str(k), "a af" if on else "s f", "ta" if on else "t", 11.5, rx=0,
             weight=700 if on else None)
    # one lane a thread: the cells it takes, under their columns
    ly0, lp = 116, 24
    for t, cells in enumerate(lanes):
        on = t == hot
        y = ly0 + t * lp
        a.text(cx0 - 10, y + 4, f"thread {t}", "ta" if on else "t", tsize, "end", 700 if on else None, mono=True)
        a.line(cx0, y, cx0 + d * cwid, y, "a" if on else "m")
        for k in cells:
            cell(a, r1(cx0 + k * cwid + 2), y - 9, cwid - 4, 18, str(k), "a af" if on else "s f",
                 "ta" if on else "t", 11, rx=4, weight=700 if on else None, under=on)
    assert cx0 - 10 - len("thread 0") * cw(tsize) > rx0 + rw         # the labels clear the tensor
    # the loop every thread runs
    src = "for (idx = threadIdx.x; idx < d; idx += blockDim.x)"
    size = 13
    x = r1((640 - len(src) * cw(size)) / 2)
    code(a, x, 246, src, size, weight=500)
    return a


# =================================================================== 03 Matrix multiply on the GPU

def gpu_matmul():
    a = Art("g03", "Load a tile once, use it many times")
    T, ci, cj, k0 = 4, 1, 2, 0                        # tiles a side; the C tile; the pair drawn
    a_tiles = [(ci, k) for k in range(T)]
    b_tiles = [(k, cj) for k in range(T)]
    assert a_tiles == [(1, 0), (1, 1), (1, 2), (1, 3)] and b_tiles == [(0, 2), (1, 2), (2, 2), (3, 2)]
    pa, pb = a_tiles[k0], b_tiles[k0]
    assert (pa, pb) == ((1, 0), (0, 2))
    t, gy = 22, 46                                    # a tile's side, the grids' top
    G = T * t
    ox = 80
    ax, bx, cx = ox, ox + G + 52, ox + 2 * (G + 52)
    for name, x0, marked, sel in (("A", ax, a_tiles, None), ("B", bx, b_tiles, None), ("C", cx, [], (ci, cj))):
        a.text(x0 + G / 2, gy - 10, name, "t", 13, "middle", 700, mono=True)
        for r in range(T):
            for c in range(T):
                on = (r, c) in marked or (r, c) == sel
                a.box(x0 + c * t, gy + r * t, t, t, "s fs" if on else "s f", rx=0)
    a.text(ax + G + 26, gy + G / 2 + 5, "x", "t", 14, "middle", 600)
    a.text(bx + G + 26, gy + G / 2 + 5, "=", "t", 14, "middle", 600)
    # A's row of tiles, B's column and the C tile again, with a heavier edge: fs alone is too faint in dark mode
    for x0, (r, c), (nr, nc) in ((ax, a_tiles[0], (1, T)), (bx, b_tiles[0], (T, 1)), (cx, (ci, cj), (1, 1))):
        a.add(f'<rect class="s" x="{x0 + c * t}" y="{gy + r * t}" width="{nc * t}" height="{nr * t}" '
              f'stroke-width="2.5"/>')

    def centre(x0, rc):
        r, c = rc
        return x0 + c * t + t / 2, gy + r * t + t / 2

    # shared memory: one box a block, two tile-sized squares straight under the tiles they hold
    (pax, pay), (pbx, pby) = centre(ax, pa), centre(bx, pb)
    sy, sh = 178, 72
    sx0, sx1 = pax - t / 2 - 18, pbx + t / 2 + 18
    a.box(sx0, sy, sx1 - sx0, sh, "a af", rx=10)
    qy = sy + sh / 2 - t / 2
    for px, py in ((pax, pay), (pbx, pby)):
        a.circle(px, py, 1.25, "s")                   # a dot where the tile leaves from
        a.line(px, py + 3, px, qy - 2, arrow=True)
        a.box(px - t / 2, qy, t, t, "a f", rx=0)
    mid = (pax + pbx) / 2
    for k, s in enumerate(("shared memory,", "one per thread block")):
        a.text(mid, sy + sh / 2 - 3 + k * 15, s, "ta", 11.5, "middle", 600)
    assert mid - sans("one per thread block", 11.5) / 2 > pax + t / 2 + 4
    # global memory: the arrows in, read once per tile
    gl = (gy + G + sy) / 2
    a.text(mid, gl - 2, "global memory:", "tm", 11, "middle")
    a.text(mid, gl + 12, "read once per tile", "tm", 11, "middle")
    assert mid - sans("read once per tile", 11) / 2 > pax + 6
    # out to the C tile
    tcx, tcy = centre(cx, (ci, cj))
    ey = sy + sh / 2
    a.path(f"M{sx1} {ey}H{tcx}V{tcy + t / 2 + 3}", "s", arrow=True)
    for k, s in enumerate(("every thread in the block", "multiplies from here")):
        a.text(tcx + 12, gy + G + 34 + k * 15, s, "t", 11.5)
    assert tcx + 12 + sans("every thread in the block", 11.5) <= 624
    rich(a, (sx0 + sx1) / 2, sy + sh + 20, [("shared memory: read ", "tm", False), ("TILE", "tm", True),
                                            (" times", "tm", False)], 11, "middle")
    return a


# =================================================================== 04 Many threads, one number

def shuffle(v, mask):
    return [v[i] + v[i ^ mask] for i in range(len(v))]


def reduction():
    a = Art("g04", "Each shuffle adds a partner lane; when the mask reaches 1 every lane has the sum")
    start = [3, 1, 4, 1, 5, 9, 2, 6]
    lanes, warp = len(start), 32
    assert lanes == 8 and warp % lanes == 0
    rows, v = [("start", None, start)], start
    for mask in (4, 2, 1):
        v = shuffle(v, mask)
        rows.append((f"mask {mask}", mask, v))
    assert [r[2] for r in rows] == [[3, 1, 4, 1, 5, 9, 2, 6], [8, 10, 6, 7, 8, 10, 6, 7],
                                    [14, 17, 14, 17, 14, 17, 14, 17], [31] * 8], rows
    assert rows[-1][2] == [sum(start)] * lanes and sum(start) == 31
    # the lanes whose pairing is drawn at each step: half of them, so no two lines cross
    drawn = {4: [0, 1, 2, 3], 2: [0, 1, 4, 5], 1: [0, 2, 4, 6]}
    for mask, ls in drawn.items():
        assert all(i ^ mask not in ls for i in ls) and len(ls) == lanes // 2
    a.text(24, 28, f"one warp, drawn with {lanes} of its {warp} lanes", "tm", 11.5)
    lx, x0, w, p, h, y0, rp = 24, 104, 38, 46, 26, 58, 50
    assert x0 + (lanes - 1) * p + w <= 470
    for i in range(lanes):
        a.text(x0 + i * p + w / 2, y0 - 8, str(i), "tm", 10.5, "middle", mono=True)
    a.text(x0 - 12, y0 - 8, "lane", "tm", 10.5, "end")

    def cx(i):
        return x0 + i * p + w / 2

    for r, (name, mask, vals) in enumerate(rows):
        y = y0 + r * rp
        last = r == len(rows) - 1
        if mask:
            for i in drawn[mask]:                     # lane i takes its partner's value: from i ^ mask, above
                a.line(r1(cx(i ^ mask)), y - rp + h + 3, r1(cx(i)), y - 3, "m", width=1)
        a.text(lx, y + h / 2 + 4, name, "t", 12, weight=600, mono=True)
        for i, val in enumerate(vals):
            cell(a, x0 + i * p, y, w, h, str(val), "a af" if last else "s f", "ta" if last else "t", 12.5, rx=5,
                 weight=700 if last else None)
    yl = y0 + 3 * rp
    nx = x0 + (lanes - 1) * p + w + 18
    a.text(nx, yl + h / 2 - 3, "lane 0 writes it", "t", 11.5)
    a.text(nx, yl + h / 2 + 12, "to shared memory", "t", 11.5)
    assert nx + sans("lane 0 writes it", 11.5) <= 624
    src = "val += __shfl_xor_sync(0xffffffff, val, mask);"
    code(a, x0, yl + h + 34, src, 12.5, weight=500)
    assert x0 + len(src) * cw(12.5) <= 624 and yl + h + 34 <= 284
    return a


# =================================================================== icons and the table

ICON = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="none" stroke="currentColor" '
        'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">{}</svg>\n')

MODULES = {
    # a stopwatch
    "00": (workbench, '<circle cx="10" cy="11.5" r="6.25"/><path d="M8 2.5h4M10 2.5v2.75M10 11.5l2.5-2.5"/>'
                      '<path d="M15 5.5l1.25-1.25"/>'),
    # a square bracket pair holding a 2x2 grid of dots
    "01": (cpu_matmul, '<path d="M5.5 3.5H3.5v13h2M14.5 3.5h2v13h-2"/>'
                       '<circle cx="8" cy="8" r=".75" fill="currentColor"/><circle cx="12" cy="8" r=".75" fill="currentColor"/>'
                       '<circle cx="8" cy="12" r=".75" fill="currentColor"/><circle cx="12" cy="12" r=".75" fill="currentColor"/>'),
    # a 3x3 grid of dots
    "02": (threads, "".join(f'<circle cx="{x}" cy="{y}" r=".75" fill="currentColor"/>'
                            for y in (4.5, 10, 15.5) for x in (4.5, 10, 15.5))),
    # a square cut into four tiles, one hatched
    "03": (gpu_matmul, '<rect x="3" y="3" width="14" height="14" rx="1.5"/><path d="M10 3v14M3 10h14"/>'
                       '<path d="M4.5 6.25L6.25 4.5M5.5 8.5L8.5 5.5"/>'),
    # three short lines converging down into one dot
    "04": (reduction, '<path d="M4 3.5l4.5 8.75M10 3.5v8.5M16 3.5l-4.5 8.75"/>'
                      '<circle cx="10" cy="15.75" r="1.25" fill="currentColor"/>'),
}


def files(only=None):
    """{relative path: svg text} for every file this script owns (or only for the modules listed)."""
    out = {}
    if not only:
        out["art.svg"] = track_art()
        out["icon.svg"] = ICON.format(TRACK_ICON)
    for mid, (fn, icon) in MODULES.items():
        if only and mid not in only:
            continue
        out[f"{mid}/cover.svg"] = fn().svg()
        out[f"{mid}/icon.svg"] = ICON.format(icon)
    return out


def check(out):
    """Each file must be ASCII and come through the site's sanitizer with every element kept."""
    sys.path.insert(0, ROOT)
    sys.dont_write_bytecode = True        # read harness/, never write into it
    from harness.web.art import sanitize
    bad = []
    for rel, text in out.items():
        if not text.isascii():
            bad.append(f"{rel}: not ASCII")
        clean = sanitize(text, "x")
        if not clean:
            bad.append(f"{rel}: rejected by sanitize")
        else:
            kept = clean.count("<") - clean.count("</")
            had = text.count("<") - text.count("</")
            if kept != had:
                bad.append(f"{rel}: sanitize dropped {had - kept} element(s)")
    return bad


def main(argv):
    out = files(set(argv) or None)
    for rel, text in out.items():
        path = os.path.join(OUT, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(text)
    bad = check(out)
    for b in bad:
        print("problem:", b)
    print("wrote", len(out), "files under", os.path.relpath(OUT, ROOT))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
