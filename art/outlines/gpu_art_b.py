"""Art for modules 05 to 09 of the GPU kernels outline (outlines/gpu-kernels.md, id gpu): the KV
cache, the two attention kernels, half precision and the capstone. The track's own pair and modules
00 to 04 are drawn by gpu_art.py, not here.

Writes, under outlines/gpu-kernels/:
    NN/cover.svg    640x300 teaching diagram for module NN (05 to 09)
    NN/icon.svg     20x20 currentColor line icon for module NN

Covers style themselves only through the .art classes in harness/web/app.css:
    s m a        stroke: foreground, muted, accent
    f fs af fa   fill: page, code background, accent-soft, accent
    t tm ta      text fill: foreground, muted, accent      mono: monospace
One accent idea a cover: the accent classes mark the single thing the cover is about. No cover
shows a speed, a timing or a speed-up: the course's rule is that the reader measures.

Code is set on a monospace grid: a line of code is split into runs of text, and each run is
placed at its own column (x = left + column * 0.6em, Geist Mono's advance), so indentation and
double spaces survive SVG's whitespace collapsing.

Computed here, and asserted, so a typo stops the script instead of reaching a cover:
    05  two sequences (7 and 3 tokens) placed through block tables [5, 2] and [6] into a pool of
        8 blocks of 4: what each block holds; token 6 of A is logical block 1, offset 2, physical
        block 2, slot 10, and 10 // 4 == 2, 10 % 4 == 2 takes it back
    06  context_len 7 with block_size 4: (7 + 4 - 1) // 4 == 2 blocks holding [0, 1, 2, 3] and
        [4, 5, 6], one slot unused
    07  T = 8 in tiles of 2: 4 tiles a side, 10 on or below the diagonal, 6 skipped; query-tile
        row 2 needs key tiles [0, 1, 2]
    08  sign + exponent + fraction: 1 + 8 + 23 == 32, 1 + 5 + 10 == 16, 1 + 8 + 7 == 16
    09  the block's kernels in order, the two groups of three, and the report's 5 x 2 empty cells

The Art class and helpers are the ones from nand_art_sw.py, repeated so this file stands alone.

    python3 art/outlines/gpu_art_b.py [NN ...]
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


def n(v):
    """A coordinate as short text: 12, 12.5, 12.35 (no float noise)."""
    v = round(float(v), 2)
    return int(v) if v == int(v) else v


class Art:
    def __init__(self, key, title, h=300):
        self.key, self.title, self.out, self.h = key, title, [], h

    def add(self, s):
        self.out.append(s)

    def box(self, x, y, w, h, cls="s f", rx=10, dash=False):
        d = ' stroke-dasharray="4 4"' if dash else ""
        self.add(f'<rect class="{cls}" x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}" rx="{n(rx)}" {SW}{d}/>')

    def text(self, x, y, s, cls="t", size=12, anchor="start", weight=None, mono=False, rot=None):
        assert size >= 10, (self.key, s, size)
        c = cls + (" mono" if mono else "")
        wt = f' font-weight="{weight}"' if weight else ""
        a = f' text-anchor="{anchor}"' if anchor != "start" else ""
        tr = f' transform="rotate({rot} {n(x)} {n(y)})"' if rot else ""
        self.add(f'<text class="{c}" x="{n(x)}" y="{n(y)}" font-size="{size}"{wt}{a}{tr}>{esc(s)}</text>')

    def marker(self, cls):
        return {"a": "aa", "m": "am"}.get(cls.split()[0], "ah")

    def line(self, x1, y1, x2, y2, cls="s", arrow=False, dash=False):
        m = f' marker-end="url(#{self.key}-{self.marker(cls)})"' if arrow else ""
        d = ' stroke-dasharray="4 4"' if dash else ""
        self.add(f'<line class="{cls}" x1="{n(x1)}" y1="{n(y1)}" x2="{n(x2)}" y2="{n(y2)}" {SW} '
                 f'stroke-linecap="round"{m}{d}/>')

    def path(self, d, cls="s", arrow=False, dash=False):
        m = f' marker-end="url(#{self.key}-{self.marker(cls)})"' if arrow else ""
        da = ' stroke-dasharray="4 4"' if dash else ""
        self.add(f'<path class="{cls}" d="{d}" {SW} stroke-linecap="round" stroke-linejoin="round"{m}{da}/>')

    def circle(self, cx, cy, r, cls="s f"):
        self.add(f'<circle class="{cls}" cx="{n(cx)}" cy="{n(cy)}" r="{n(r)}" {SW}/>')

    def svg(self):
        def mk(name, cls):
            return (f'<marker id="{self.key}-{name}" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" '
                    f'markerHeight="7" orient="auto-start-reverse"><path class="{cls}" d="M1 1.5L8.5 5L1 8.5" {SW} '
                    f'stroke-linecap="round" stroke-linejoin="round"/></marker>')
        defs = f'<defs>{mk("ah", "s")}{mk("aa", "a")}{mk("am", "m")}</defs>'
        body = "\n".join(self.out)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 {self.h}" fill="none">\n'
                f'<title>{esc(self.title)}</title>\n{defs}\n{body}\n</svg>\n')


def cell(a, x, y, w, h, s, cls="s f", tcls="t", size=12, rx=4, dash=False, weight=None, mono=True):
    """A box with one centred label: a token, a key, a score."""
    a.box(x, y, w, h, cls, rx=rx, dash=dash)
    if s:
        a.text(x + w / 2, y + h / 2 + size * 0.35, s, tcls, size, "middle", weight, mono)


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
    c_w = cw(size)
    wt = f' font-weight="{weight}"' if weight else ""
    assert size >= 10
    if len(runs) == 1 and runs[0][0] == 0:
        a.add(f'<text class="{runs[0][2]} mono" x="{n(x)}" y="{n(y)}" font-size="{size}"{wt}>{esc(runs[0][1])}</text>')
        return
    spans_out = "".join(
        f'<tspan x="{n(x + c * c_w)}"{"" if k == cls else f" class={chr(34)}{k}{chr(34)}"}>{esc(t)}</tspan>'
        for c, t, k in runs)
    a.add(f'<text class="{cls} mono" x="{n(x)}" y="{n(y)}" font-size="{size}"{wt}>{spans_out}</text>')


def rich(a, x, y, parts, size=11, anchor="start", weight=None, cls="t"):
    """Text whose parts flow one after another: parts is a list of (text, class, mono)."""
    assert size >= 10
    wt = f' font-weight="{weight}"' if weight else ""
    an = f' text-anchor="{anchor}"' if anchor != "start" else ""
    inner = ""
    for t, c, mono in parts:
        k = (c or cls) + (" mono" if mono else "")
        inner += f'<tspan class="{k}">{esc(t)}</tspan>'
    a.add(f'<text class="{cls}" x="{n(x)}" y="{n(y)}" font-size="{size}"{wt}{an}>{inner}</text>')


def cw(size):
    return EM * size


def sans_w(s, size):
    return len(s) * SANS * size


def chip(a, cx, y, s, cls="s f", tcls="t", size=11, mono=True, h=22, weight=None, w=None):
    """A pill centred on cx, its width from the text (monospace exact, sans estimated)."""
    w = w or round(len(s) * (EM if mono else SANS) * size + 18)
    a.box(cx - w / 2, y, w, h, cls, rx=h / 2)
    a.text(cx, y + h / 2 + size * 0.35, s, tcls, size, "middle", weight, mono)
    return w


def bracket_up(a, x1, x2, y, depth=5, cls="m"):
    """A bracket under a run of cells, open towards them: its ends at y, its bar at y + depth."""
    a.path(f"M{n(x1)} {n(y)} V{n(y + depth)} H{n(x2)} V{n(y)}", cls)


# =================================================================== 05 positions and the KV cache

def place(seqs, tables, bs, nblocks):
    """Where every token of every sequence lives: {physical block: [slot contents]}. Token t of a
    sequence goes to block tables[seq][t // bs], slot t % bs, as cache_kernels.cu computes it."""
    pool = {b: [None] * bs for b in range(nblocks)}
    for s, ntok in seqs.items():
        assert len(tables[s]) == (ntok + bs - 1) // bs
        for t in range(ntok):
            blk, off = tables[s][t // bs], t % bs
            assert pool[blk][off] is None
            pool[blk][off] = f"{s}{t}"
    return pool


def kv_cache():
    a = Art("g05", "Two sequences, their block tables and the pool of blocks: token 6 of A goes to "
                   "block table[1] = 2, slot 2 * 4 + 2 = 10")
    BS, NB = 4, 8
    seqs = {"A": 7, "B": 3}
    tables = {"A": [5, 2], "B": [6]}
    pool = place(seqs, tables, BS, NB)
    assert pool[5] == ["A0", "A1", "A2", "A3"] and pool[2] == ["A4", "A5", "A6", None], pool
    assert pool[6] == ["B0", "B1", "B2", None], pool
    assert all(pool[b] == [None] * BS for b in (0, 1, 3, 4, 7)), pool
    runs = {s: [list(range(i, min(i + BS, k))) for i in range(0, k, BS)] for s, k in seqs.items()}
    assert runs == {"A": [[0, 1, 2, 3], [4, 5, 6]], "B": [[0, 1, 2]]}, runs
    new = seqs["A"] - 1
    lb, off = new // BS, new % BS
    pb = tables["A"][lb]
    slot = pb * BS + off
    assert (new, lb, off, pb, slot) == (6, 1, 2, 2, 10), (new, lb, off, pb, slot)
    assert (slot // BS, slot % BS) == (2, 2)                  # the kernel's way back from the slot
    lines = [f"token {new} of A:  logical block {new} / {BS} = {lb},  offset {new} % {BS} = {off}",
             f"block table[{lb}] = {pb}", f"slot = {pb} * {BS} + {off} = {slot}"]
    assert lines == ["token 6 of A:  logical block 6 / 4 = 1,  offset 6 % 4 = 2", "block table[1] = 2",
                     "slot = 2 * 4 + 2 = 10"], lines

    # the sequences: a row of tokens each, a small gap between runs of BS
    tw, th, rgap, sx = 24, 22, 6, 24
    TX = lambda t: sx + t * tw + (t // BS) * rgap
    # the block tables, in the middle column
    ex, ew, eh = 244, 30, 22
    rows = {"A": 36, "B": 150}
    entry_y = {"A": 88, "B": 188}
    for s, y in rows.items():
        a.text(sx, y - 8, f"sequence {s}", "tm", 11, weight=600)
        for t in range(seqs[s]):
            hot = s == "A" and t == new
            cell(a, TX(t), y, tw, th, str(t), "a af" if hot else "s f", "ta" if hot else "t", 11, rx=0,
                 weight=700 if hot else None)
        if s == "A":
            a.text(TX(new) + tw / 2, y - 8, "new", "ta", 11, "middle", 700)
        # each run's bracket, and an arrow from it to its entry
        ey = entry_y[s]
        by = y + th + 4
        for k, run in enumerate(runs[s]):
            x1, x2 = TX(run[0]) + 3, TX(run[-1]) + tw - 3
            bracket_up(a, x1, x2, by)
            mid = (x1 + x2) / 2
            if k == 0:                                        # the first run: down, then right into its side
                a.path(f"M{n(mid)} {by + 5} V{ey + eh / 2} H{ex - 2}", "s", arrow=True)
            else:                                             # the second: over the first entry, into its top
                assert by + 11 < ey - 12
                a.path(f"M{n(mid)} {by + 5} V{by + 11} H{n(ex + k * ew + ew / 2)} V{ey - 2}", "s", arrow=True)
        for k, b in enumerate(tables[s]):
            cell(a, ex + k * ew, ey, ew, eh, str(b), "s fs", "t", 12, rx=0, weight=700)
            a.text(ex + k * ew + ew / 2, ey + eh + 13, f"[{k}]", "tm", 10.5, "middle", mono=True)
    a.text(ex, 28, "block tables", "tm", 11, weight=600)
    assert TX(seqs["A"] - 1) + tw < ex - 24

    # the pool: 8 blocks of BS slots, two columns of four, in block-number order
    px, pw_, pitch, sw_ = 372, 24, 40, 136
    rich(a, px - 14, 28, [("the pool: 8 blocks, ", "tm", False), (f"block_size = {BS}", "tm", True)], 11,
         weight=600)
    for b in range(NB):
        x = px + (b // 4) * sw_
        y = 36 + (b % 4) * pitch
        used = any(pool[b])
        a.text(x - 8, y + th / 2 + 4, str(b), "t" if used else "tm", 11.5, "end", 700 if used else None, mono=True)
        for j, v in enumerate(pool[b]):
            if b == pb and j == off:
                continue
            cell(a, x + j * pw_, y, pw_, th, v, "s fs" if v else ("s f" if used else "m f"), "t", 10.5, rx=0)
        if b == pb:                                           # the new token's slot, drawn last, on top
            cell(a, x + off * pw_, y, pw_, th, pool[b][off], "a af", "ta", 10.5, rx=0, weight=700)
        assert x + BS * pw_ <= 616
    assert px - 14 > ex + 2 * ew + 24

    # the arithmetic
    for k, ln in enumerate(lines):
        last = k == len(lines) - 1
        code(a, sx, 246 + k * 17, ln, 12, "ta" if last else "t", weight=700 if last else None)
    assert len(lines[0]) * cw(12) + sx <= 616
    return a


# =================================================================== 06 attention for one new token

def decode_attention():
    a = Art("g06", "Decode attention: the query reads every cached key through the block table, "
                   "then scores, a softmax, and the weighted values")
    BS, ctx, table = 4, 7, [5, 2]
    nblocks = (ctx + BS - 1) // BS
    assert nblocks == 2 == len(table)
    toks = [list(range(i * BS, min((i + 1) * BS, ctx))) for i in range(nblocks)]
    assert toks == [[0, 1, 2, 3], [4, 5, 6]], toks
    unused = nblocks * BS - ctx
    assert unused == 1

    kw, kh, kx, bgap = 50, 24, 196, 16
    KX = lambda i, j: kx + i * (BS * kw + bgap) + j * kw     # table entry i, slot j
    col = [KX(t // BS, t % BS) for t in range(ctx)]           # key t's column, used again by the rows below
    ky = 100
    # the launch, top right
    note = "blockIdx.x = head    blockIdx.y = sequence"
    code(a, 616 - len(note) * cw(11), 24, note, 11, "tm")
    # q, a vector of one head
    qx, qy, qc, qn = 24, 52, 16, 5
    a.text(qx, 40, "q: the new token's query, one head", "t", 11, weight=600)
    for j in range(qn):
        a.box(qx + j * qc, qy, qc, 20, "s fs", rx=0)
    # the block table, its first entry straight above the first key block
    ew, eh = 30, 24
    tx = KX(0, 0) + BS * kw / 2 - ew / 2
    tcy = qy + 10
    ty = tcy - eh / 2
    a.text(tx, ty - 8, "block table", "ta", 11, weight=700)
    a.line(qx + qn * qc + 4, tcy, tx - 2, tcy, "a", arrow=True)
    for i, b in enumerate(table):
        cell(a, tx + i * ew, ty, ew, eh, str(b), "a af", "ta", 12.5, rx=0, weight=700)
    code(a, tx + 2 * ew + 12, tcy + 4, f"context_len = {ctx}", 11)
    # through the table to each key block, in table order
    c0 = tx + ew / 2
    assert c0 == KX(0, 0) + BS * kw / 2
    a.line(c0, ty + eh, c0, ky - 2, "a", arrow=True)
    c1 = KX(1, 0) + BS * kw / 2
    a.path(f"M{n(tx + ew * 1.5)} {n(ty + eh)} V80 H{n(c1)} V{ky - 2}", "a", arrow=True)
    for i, b in enumerate(table):
        a.text(KX(i, 0), ky - 8, f"block {b}", "tm", 10.5, weight=600)
        for j in range(BS):
            t = i * BS + j
            if t < ctx:
                cell(a, KX(i, j), ky, kw, kh, f"k{t}", "s f", "t", 11, rx=0)
            else:                                             # the slot past context_len
                x = KX(i, j)
                a.box(x, ky, kw, kh, "m f", rx=0)
                a.path(f"M{n(x + 16)} {ky + 6} L{n(x + kw - 16)} {ky + kh - 6} M{n(x + kw - 16)} {ky + 6} "
                       f"L{n(x + 16)} {ky + kh - 6}", "m")
                a.text(x + kw, ky + kh + 14, "past context_len: ignored", "tm", 10.5, "end")
    assert KX(1, BS - 1) + kw <= 616
    # scores, a softmax, the weights, and the output
    sy, wy, rh = 150, 198, 24
    lx = kx - 10
    a.text(lx, sy + 16, "scores", "t", 11, "end", 600)
    a.text(lx, wy + 16, "weights", "t", 11, "end", 600)
    for t in range(ctx):
        cell(a, col[t], sy, kw, rh, f"q . k{t}", "s fs", "t", 10.5, rx=0)
        a.box(col[t], wy, kw, rh, "s f", rx=0)
    ax = KX(1, 0) - bgap / 2                                  # the arrows run down the gap between the blocks
    a.line(ax, sy + rh + 2, ax, wy - 2, "s", arrow=True)
    a.text(ax + 10, sy + rh + 16, "softmax across the block", "tm", 11)
    oy, oc, on = 250, 16, 5
    a.line(ax, wy + rh + 2, ax, oy - 2, "s", arrow=True)
    a.text(ax + 10, wy + rh + 17, "times values, summed", "tm", 11)
    ox = ax - on * oc / 2
    for j in range(on):
        a.box(ox + j * oc, oy, oc, 20, "s fs", rx=0)
    a.text(ox - 10, oy + 14.5, "out", "t", 11, "end", 600)
    return a


# =================================================================== 07 attention over a whole prompt

def prefill_attention():
    a = Art("g07", "Tiled attention: the score table is never stored; one tile at a time updates "
                   "a running max, sum and output")
    T, TILE = 8, 2
    N = T // TILE
    assert N == 4
    lower = [(r, c) for r in range(N) for c in range(N) if c <= r]
    skipped = [(r, c) for r in range(N) for c in range(N) if c > r]
    assert len(lower) == N * (N + 1) // 2 == 10 and len(skipped) == 6, (lower, skipped)
    ROW = 2
    need = [c for c in range(N) if (ROW, c) in lower]
    assert need == [0, 1, 2], need
    done, cur, todo = need
    ts, pitch = 36, 46                                        # a tile, and tile to tile
    gx, gy = 104, 62
    gw = N * pitch - (pitch - ts)
    TXY = lambda r, c: (gx + c * pitch, gy + r * pitch)
    tok = ts / TILE
    # the axes: token numbers, two to a tile
    a.text(gx + gw / 2, 30, "keys", "t", 11.5, "middle", 600)
    a.text(gx - 40, gy + gw / 2, "queries", "t", 11.5, "middle", 600, rot=-90)
    for t in range(T):
        c, k = divmod(t, TILE)
        a.text(gx + c * pitch + k * tok + tok / 2, gy - 12, str(t), "tm", 10, "middle", mono=True)
        a.text(gx - 12, gy + c * pitch + k * tok + tok / 2 + 3.5, str(t), "tm", 10, "end", mono=True)
    # the outline of the whole table: never stored
    pad = 5
    a.box(gx - pad, gy - pad, gw + 2 * pad, gw + 2 * pad, "m", rx=6, dash=True)
    a.text(gx + gw / 2, gy + gw + pad + 16, "never stored", "tm", 11, "middle", 600)
    for r, c in skipped:
        x, y = TXY(r, c)
        a.box(x, y, ts, ts, "m", rx=3, dash=True)
    x, y = TXY(0, N - 1)
    a.text(x + ts + pad + 12, y + ts / 2 + 4, "skipped: the future", "tm", 11)
    for r, c in lower:
        if r == ROW and c == cur:
            continue
        x, y = TXY(r, c)
        a.box(x, y, ts, ts, "s fs" if (r, c) == (ROW, done) else "s f", rx=3)
    for c, word in ((done, "done"), (todo, "next")):
        x, y = TXY(ROW, c)
        a.text(x + ts / 2, y + ts / 2 + 3.5, word, "tm", 10, "middle")
    # the current tile, and the arrow from it along the gap under its row into the three values
    x, y = TXY(ROW, cur)
    a.box(x, y, ts, ts, "a af", rx=3)
    a.text(x + ts / 2, y + ts / 2 + 4, "now", "ta", 11, "middle", 700)
    gap_y = y + ts + (pitch - ts) / 2
    bx, bw, bh, bp = 382, 196, 28, 36
    top = gap_y - bp - bh / 2                                 # the middle box sits on the arrow's line
    a.path(f"M{n(x + ts / 2)} {n(y + ts)} V{n(gap_y)} H{bx - 2}", "a", arrow=True)
    a.text(bx, top - 10, f"kept for query-tile row {ROW}", "tm", 11, weight=600)
    for k, (v, what) in enumerate((("m", "running max"), ("l", "running sum"), ("o", "running output"))):
        yy = top + k * bp
        a.box(bx, yy, bw, bh, "s f", rx=6)
        a.text(bx + 16, yy + bh / 2 + 5, v, "t", 14, weight=700, mono=True)
        a.text(bx + 40, yy + bh / 2 + 4.5, what, "t", 12)
    cy = top + 2 * bp + bh
    a.text(bx, cy + 20, "updated after each tile; rescaled", "tm", 11)
    a.text(bx, cy + 35, "when a larger score arrives", "tm", 11)
    assert cy + 35 <= 284 and top - 10 - 11 > gy + ts / 2 + 4, (cy, top)
    return a


# =================================================================== 08 half the bits

FORMATS = [("float32", 1, 8, 23), ("float16", 1, 5, 10), ("bfloat16", 1, 8, 7)]


def half_bits():
    a = Art("g08", "float32, float16 and bfloat16 bit by bit; read 16 bits, add in 32, write 16")
    widths = {name: s + e + f for name, s, e, f in FORMATS}
    assert 1 + 8 + 23 == widths["float32"] == 32
    assert 1 + 5 + 10 == widths["float16"] == 16
    assert 1 + 8 + 7 == widths["bfloat16"] == 16
    assert FORMATS[2][2] == FORMATS[0][2]                     # bfloat16 keeps float32's exponent
    bw, sh, x0 = 15, 20, 112
    assert x0 + 32 * bw <= 616
    for k, (name, s, e, f) in enumerate(FORMATS):
        y = 42 + k * 48
        code(a, 24, y + sh / 2 + 4.5, name, 12, weight=600)
        x = x0
        for g, (nbits, fill) in enumerate(((s, "s f"), (e, "s fs"), (f, "s f"))):
            a.box(x, y, nbits * bw, sh, fill, rx=0)
            for i in range(1, nbits):
                a.line(x + i * bw, y + 4, x + i * bw, y + sh - 4, "m")
            a.text(x + nbits * bw / 2, y + sh + 14, str(nbits), "tm", 10.5, "middle", mono=True)
            if k == 0:
                a.text(x + nbits * bw / 2, y - 8, ("sign", "exponent", "fraction")[g], "tm", 10.5, "middle")
            x += nbits * bw
        assert x - x0 == widths[name] * bw
        if name == "bfloat16":
            a.text(x + 16, y + sh / 2 + 4, "the same exponent as float32", "tm", 11)
    # what the RMS norm kernel does with them
    boxes = [("input: ", "float16"), ("sum of squares: ", "float32"), ("output: ", "float16")]
    size, h, gap, y = 12, 32, 40, 206
    ws = [round(sans_w(p, size) + cw(size) * len(t) + 28) for p, t in boxes]
    x = 320 - (sum(ws) + gap * (len(ws) - 1)) / 2
    for k, ((p, t), w) in enumerate(zip(boxes, ws)):
        hot = k == 1
        a.box(x, y, w, h, "a af" if hot else "s f", rx=8)
        tc = "ta" if hot else "t"
        rich(a, x + w / 2, y + h / 2 + 4.5, [(p, tc, False), (t, tc, True)], size, "middle", 700 if hot else 600)
        if k:
            a.line(x - gap + 4, y + h / 2, x - 4, y + h / 2, "s", arrow=True)
        x += w + gap
    rich(a, 320, y + h + 26, [("as vLLM's ", "tm", False), ("rms_norm_kernel", "tm", True), (" does", "tm", False)],
         11, "middle")
    return a


# =================================================================== 09 capstone

BLOCK = ["rms_norm", ("attention", ["rotary", "reshape_and_cache", "paged attention"]), "add",
         "rms_norm", ("MLP", ["matmul", "silu_and_mul", "matmul"]), "add"]
REPORT = ["matmul", "rms_norm", "rotary", "attention", "whole model"]


def capstone():
    a = Art("g09", "The capstone: Python over your extension over the GPU, one transformer block as your "
                   "kernels, and a report you fill in")
    kernels = [k for step in BLOCK for k in ([step] if isinstance(step, str) else step[1])]
    assert kernels == ["rms_norm", "rotary", "reshape_and_cache", "paged attention", "add",
                       "rms_norm", "matmul", "silu_and_mul", "matmul", "add"], kernels
    assert [len(s[1]) for s in BLOCK if not isinstance(s, str)] == [3, 3]
    halves = [BLOCK[:3], BLOCK[3:]]                           # attention and its add, then the MLP and its add
    assert all(len(hh) == 3 for hh in halves)

    # left: the three layers
    dy = 14                                                   # the whole cover, centred on the canvas
    lx, lw = 24, 116
    layers = [["Python:", "PyTorch tensors"], ["the extension:", "your kernels", "as functions"], ["the GPU"]]
    y = 58 + dy
    for k, words in enumerate(layers):
        h = 16 + 14 * len(words)
        a.box(lx, y, lw, h, "s fs" if k == 1 else "s f", rx=8)
        for j, w in enumerate(words):
            a.text(lx + lw / 2, y + 19 + j * 14, w, "t", 11, "middle", 600 if j == 0 else None)
            assert sans_w(w, 11) <= lw - 12, w
        y += h
        if k < len(layers) - 1:
            a.line(lx + lw / 2, y + 2, lx + lw / 2, y + 18, "s", arrow=True)
            y += 20
    # middle: one transformer block, two columns of kernels
    size, chh = 10, 20
    chw = round(len("reshape_and_cache") * cw(size) + 14)
    gw = chw + 12
    mx = [156, 156 + gw + 16]
    a.text((mx[0] + mx[1] + gw) / 2, 28 + dy, "one transformer block", "tm", 11, "middle", 600)
    ends = []
    for c, half in enumerate(halves):
        cx = mx[c] + gw / 2
        y = 44 + dy
        prev = None
        for step in half:
            if prev is not None:
                a.line(cx, prev + 2, cx, y - 2, "s", arrow=True)
            if isinstance(step, str):
                chip(a, cx, y, step, "a af", "ta", size, True, chh, 600, w=chw)
                if c == 0 and step == "add":
                    ends.append((cx + chw / 2, y + chh / 2))
                if c == 1 and step == "rms_norm" and prev is None:
                    ends.append((cx - chw / 2, y + chh / 2))
                prev = y + chh
                y += chh + 16
            else:
                name, ks = step
                gh = 26 + len(ks) * chh + (len(ks) - 1) * 14 + 8
                a.box(mx[c], y, gw, gh, "m", rx=8, dash=True)
                a.text(mx[c] + 8, y + 14, name, "tm", 10.5, weight=600)
                ky = y + 22
                for j, k in enumerate(ks):
                    if j:
                        a.line(cx, ky - 12, cx, ky - 2, "s", arrow=True)
                    chip(a, cx, ky, k, "a af", "ta", size, True, chh, 600, w=chw)
                    ky += chh + 14
                prev = y + gh
                y += gh + 16
        assert prev <= 284
    # from the first half's add to the second half's rms_norm, up the gap between the columns
    (x1, y1), (x2, y2) = ends
    gx = mx[0] + gw + 8
    a.path(f"M{n(x1 + 2)} {n(y1)} H{n(gx)} V{n(y2)} H{n(x2 - 2)}", "s", arrow=True)
    # right: the report, every cell yours to fill
    tx, lc, vc, rh = 440, 74, 51, 22
    tw = lc + 2 * vc
    assert tx > mx[1] + gw + 8 and tx + tw <= 616, (tx, mx, gw)
    ty = 62 + dy
    a.text(tx, ty - 10, "the report", "t", 12, weight=700)
    a.box(tx, ty, tw, rh * (len(REPORT) + 1), "s f", rx=6)
    a.line(tx, ty + rh, tx + tw, ty + rh, "s")
    for v in (tx + lc, tx + lc + vc):
        a.line(v, ty, v, ty + rh * (len(REPORT) + 1), "m")
    for j, head in enumerate(("yours", "PyTorch")):
        a.text(tx + lc + j * vc + vc / 2, ty + 15, head, "t", 10.5, "middle", 600)
    for i, row in enumerate(REPORT):
        y = ty + rh * (i + 1)
        if i:
            a.line(tx, y, tx + tw, y, "m")
        mono = row != "whole model"
        a.text(tx + 7, y + 15, row, "t", 10.5, mono=mono)
        assert tx + 7 + len(row) * (EM if mono else SANS) * 10.5 <= tx + lc - 2, row
        for j in range(2):
            a.text(tx + lc + j * vc + vc / 2, y + 15, "-", "tm", 11, "middle", mono=True)
    a.text(tx + tw / 2, ty + rh * (len(REPORT) + 1) + 22, "you measure", "t", 12, "middle", 600)
    return a


# =================================================================== icons and the table

ICON = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="none" stroke="currentColor" '
        'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">{}</svg>\n')

MODULES = {
    # a table bracket, an arrow from it, two stacked blocks
    "05": (kv_cache, '<path d="M4.5 4H2V16H4.5"/><path d="M5.75 13.25H11M9.25 11.5L11 13.25l-1.75 1.75"/>'
                     '<rect x="12.75" y="3" width="5.25" height="6" rx="1"/><rect x="12.75" y="10.25" width="5.25" height="6" rx="1"/>'),
    # an arrow into a row of three cells
    "06": (decode_attention, '<path d="M1.5 10H6M4.25 8.25L6 10l-1.75 1.75"/>'
                             '<rect x="7.5" y="6" width="11" height="8" rx="1"/><path d="M11.17 6v8M14.83 6v8"/>'),
    # the lower-left triangle of a grid, in three steps
    "07": (prefill_attention, '<path d="M3 3H7.67V7.67H12.33V12.33H17V17H3Z"/>'
                              '<path d="M3 7.67H7.67M3 12.33H12.33M7.67 7.67V17M12.33 12.33V17"/>'),
    # a bar, its left half filled with three strokes
    "08": (half_bits, '<rect x="2" y="6.5" width="16" height="7" rx="1.5"/><path d="M4.5 8.75v2.5M7 8.75v2.5M9.5 8.75v2.5"/>'),
    # a flag on a pole
    "09": (capstone, '<path d="M4.5 2.5V17.5"/><path d="M4.5 3.5H15.5L13 7L15.5 10.5H4.5"/>'),
}


def files(only=None):
    """{relative path: svg text} for every file this script owns (or only for the modules listed)."""
    out = {}
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
    only = set(argv) or None
    if only and not only <= set(MODULES):
        raise SystemExit(f"gpu_art_b: modules are {', '.join(MODULES)}, not {', '.join(sorted(only - set(MODULES)))}")
    out = files(only)
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
