"""Module art for the dsa outline (outlines/data-structures-and-algorithms.md), in the same
visual language as outline_art.py and the xv6 covers.

Writes, under outlines/data-structures-and-algorithms/:
    art.svg         280x160 picture for the home page card
    icon.svg        20x20 currentColor line icon for the top bar
    NN/cover.svg    640x300 teaching diagram for module NN (00 to 10)
    NN/icon.svg     20x20 currentColor line icon for module NN

Covers style themselves only through the .art classes in harness/web/app.css:
    s m a        stroke: foreground, muted, accent
    f fs af fa   fill: page, code background, accent-soft, accent
    t tm ta      text fill: foreground, muted, accent      mono: monospace

Every value a cover shows is computed here rather than typed in: the hash slots, the heap,
the piece offsets, the NFA's state sets, the edit distance, the LCS table and its path, the
build order, the shortest paths, the Huffman tree and the git object ids.

The Art class is the one from art/xv6/covers.py. outline_art.py imports it from
art/tools/art.py, which is not in this repo, so it is repeated here.

    python3 art/outlines/dsa_art.py          write every file, then check each one survives
                                             harness/web/art.py's sanitizer unchanged
"""
import hashlib
import heapq
import html
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "outlines", "data-structures-and-algorithms")
SW = 'stroke-width="1.5"'


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
        c = cls + (" mono" if mono else "")
        wt = f' font-weight="{weight}"' if weight else ""
        a = f' text-anchor="{anchor}"' if anchor != "start" else ""
        self.add(f'<text class="{c}" x="{x}" y="{y}" font-size="{size}"{wt}{a}>{esc(s)}</text>')

    def line(self, x1, y1, x2, y2, cls="s", arrow=False, dash=False):
        m = f' marker-end="url(#{self.key}-{"aa" if "a" == cls else "ah"})"' if arrow else ""
        d = ' stroke-dasharray="4 4"' if dash else ""
        self.add(f'<line class="{cls}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" {SW} stroke-linecap="round"{m}{d}/>')

    def path(self, d, cls="s", arrow=False, dash=False):
        m = f' marker-end="url(#{self.key}-{"aa" if "a" == cls else "ah"})"' if arrow else ""
        da = ' stroke-dasharray="4 4"' if dash else ""
        self.add(f'<path class="{cls}" d="{d}" {SW} stroke-linecap="round" stroke-linejoin="round"{m}{da}/>')

    def circle(self, cx, cy, r, cls="s f"):
        self.add(f'<circle class="{cls}" cx="{cx}" cy="{cy}" r="{r}" {SW}/>')

    def svg(self):
        defs = (f'<defs>'
                f'<marker id="{self.key}-ah" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
                f'<path class="s" d="M1 1.5L8.5 5L1 8.5" {SW} stroke-linecap="round" stroke-linejoin="round"/></marker>'
                f'<marker id="{self.key}-aa" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
                f'<path class="a" d="M1 1.5L8.5 5L1 8.5" {SW} stroke-linecap="round" stroke-linejoin="round"/></marker>'
                f'</defs>')
        body = "\n".join(self.out)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 {self.h}" fill="none">\n'
                f'<title>{esc(self.title)}</title>\n{defs}\n{body}\n</svg>\n')


def cell(a, x, y, w, h, s, cls="s f", tcls="t", size=12, rx=4, dash=False, weight=None, mono=True):
    """A box with one centred label: an array slot, a heap node, a buffer byte."""
    a.box(x, y, w, h, cls, rx=rx, dash=dash)
    if s:
        a.text(round(x + w / 2, 1), round(y + h / 2 + size * 0.35, 1), s, tcls, size, "middle", weight, mono)


def node(a, x, y, s, r=14, cls="s f", tcls="t", size=12, weight=600, mono=True):
    a.circle(x, y, r, cls)
    a.text(x, round(y + size * 0.35, 1), s, tcls, size, "middle", weight, mono)


def toward(x1, y1, x2, y2, r1, r2):
    """The segment between two circles' edges (centre to centre, shortened by each radius)."""
    d = math.hypot(x2 - x1, y2 - y1)
    ux, uy = (x2 - x1) / d, (y2 - y1) / d
    return round(x1 + ux * r1, 1), round(y1 + uy * r1, 1), round(x2 - ux * r2, 1), round(y2 - uy * r2, 1)


# =================================================================== 00 workbench

def dsa_workbench():
    a = Art("d00", "The doubling test: run one job at n, 2n, 4n and 8n, and read how it grows from the ratio of the times")
    a.text(24, 30, "one job: does any value appear twice?", size=12, weight=700)
    a.text(24, 49, "slow: compare every pair", "tm", 10.5)
    a.text(24, 65, "fast: sort, then compare neighbours", "tm", 10.5)
    ns = [10_000, 20_000, 40_000, 80_000]
    slow = [0.05 * (n / ns[0]) ** 2 for n in ns]                                   # seconds, c * n^2
    fast = [0.001 * n * math.log2(n) / (ns[0] * math.log2(ns[0])) for n in ns]     # seconds, c * n log n
    a.text(24, 94, "n", "tm", 10.5)
    a.text(104, 94, "slow", "tm", 10.5)
    a.text(206, 94, "fast", "tm", 10.5)
    for i, n in enumerate(ns):
        y = 114 + i * 18
        a.text(24, y, f"{n:,}", size=11, mono=True)
        a.text(104, y, f"{slow[i]:.2f} s", size=11, mono=True)
        a.text(206, y, f"{fast[i] * 1000:.2f} ms", size=11, mono=True)
        if i:
            a.text(158, y, f"x{slow[i] / slow[i - 1]:.2f}", "ta", 10.5, weight=600, mono=True)
            a.text(266, y, f"x{fast[i] / fast[i - 1]:.2f}", "ta", 10.5, weight=600, mono=True)
    big = 1000 * ns[0]
    slow_big = 0.05 * (big / ns[0]) ** 2
    fast_big = 0.001 * big * math.log2(big) / (ns[0] * math.log2(ns[0]))
    a.text(24, 204, f"1,000x the input, n = {big:,}:", size=11.5, weight=700)
    a.text(24, 223, "slow", "tm", 11, mono=True)
    a.text(64, 223, f"{slow_big:,.0f} s = {slow_big / 3600:.0f} hours", "ta", 11, weight=600, mono=True)
    a.text(24, 240, "fast", "tm", 11, mono=True)
    a.text(64, 240, f"{fast_big:.2f} s", size=11, weight=600, mono=True)

    # the same numbers on log-log axes: the slope is the exponent
    px0, px1, py0, py1 = 376, 604, 44, 208
    lo, hi = -3.5, 1.0
    X = lambda k: round(px0 + 14 + k * (px1 - px0 - 28) / 3, 1)
    Y = lambda t: round(py1 - (math.log10(t) - lo) / (hi - lo) * (py1 - py0), 1)
    a.line(px0, py1, px1, py1, "m"); a.line(px0, py1, px0, py0 - 8, "m")
    for t, lab in ((0.001, "1 ms"), (0.01, "10 ms"), (0.1, "0.1 s"), (1, "1 s"), (10, "10 s")):
        a.line(px0 - 4, Y(t), px0, Y(t), "m")
        a.text(px0 - 8, Y(t) + 3.5, lab, "tm", 9.5, "end", mono=True)
    for k, lab in enumerate(("10k", "20k", "40k", "80k")):
        a.line(X(k), py1, X(k), py1 + 4, "m")
        a.text(X(k), py1 + 17, lab, "tm", 9.5, "middle", mono=True)
    a.text(px0, 30, "time, log scale", "tm", 10.5)
    a.text(px1, py1 + 34, "n, log scale", "tm", 10.5, "end")
    sp = [(X(k), Y(t)) for k, t in enumerate(slow)]
    fp = [(X(k), Y(t)) for k, t in enumerate(fast)]
    a.path("M" + " L".join(f"{x} {y}" for x, y in sp), "a")
    a.path("M" + " L".join(f"{x} {y}" for x, y in fp), "s")
    for x, y in sp:
        a.circle(x, y, 3.5, "a fa")
    for x, y in fp:
        a.circle(x, y, 3.5, "s f")
    a.text(sp[1][0] - 6, sp[1][1] - 24, "slope 2: n^2", "ta", 11, weight=600)
    a.text(fp[0][0] - 6, fp[0][1] - 40, "slope about 1: n log n", size=11, weight=600)
    a.text(24, 282, "Double n and divide the times: a steady x4 is n^2, a bit over x2 is n log n. Trust the ratio, not one run.",
           "tm", 11)
    return a


# =================================================================== 01 freq

def fnv1a(s):
    h = 2166136261
    for b in s.encode():
        h = ((h ^ b) * 16777619) & 0xFFFFFFFF
    return h


def dsa_freq():
    a = Art("d01", "A hash table: a word's hash picks its slot; when the slot is taken, try the next one")
    text = "the cat sat on the mat"
    size = 8
    slots = [None] * size                     # [word, count, home]
    for w in text.split():
        i = fnv1a(w) % size
        while slots[i] is not None and slots[i][0] != w:
            i = (i + 1) % size
        if slots[i] is None:
            slots[i] = [w, 0, fnv1a(w) % size]
        slots[i][1] += 1
    focus = "sat"
    fh = fnv1a(focus)
    home = fh % size
    owner = slots[home][0]
    land = next(i for i, s in enumerate(slots) if s and s[0] == focus)
    assert home == 7 and land == 0, (home, land)

    a.text(24, 30, "input", "tm", 10.5)
    a.text(24, 50, text, size=12.5, weight=600, mono=True)
    a.text(24, 90, f"insert '{focus}'", size=12, weight=700)
    a.text(24, 110, f'fnv1a("{focus}") = {fh:#010x}', size=11, mono=True)
    calc = f"{fh:#010x} % {size} = {home}"
    a.text(24, 128, calc, "ta", 11, weight=600, mono=True)
    a.text(24, 152, f"slot {home} already holds '{owner}': a collision,", "tm", 10.5)
    a.text(24, 168, f"so try the next slot; after {size - 1} it wraps to {land}", "tm", 10.5)
    the = fnv1a("the") % size
    a.text(24, 204, "look up 'the'", size=12, weight=700)
    tc = next(s[1] for s in slots if s and s[0] == "the")
    a.text(24, 224, f'fnv1a("the") % {size} = {the}: found, n = {tc}', size=11, mono=True)

    tx, tw, ty, rh = 424, 176, 40, 26
    a.text(tx + 30, 30, "word", "tm", 10)
    a.text(tx + 112, 30, "n", "tm", 10, "middle")
    a.text(tx + tw - 10, 30, "hash % 8", "tm", 10, "end")
    for i, s in enumerate(slots):
        y = ty + i * rh
        foc = s is not None and s[0] == focus
        a.box(tx, y, tw, rh, "a af" if foc else ("s f" if s else "m f"), rx=0)
        a.text(tx - 8, y + 17, str(i), "tm", 10.5, "end", mono=True)
        if s:
            a.text(tx + 30, y + 17, s[0], "ta" if foc else "t", 12, weight=600 if foc else None, mono=True)
            a.text(tx + 112, y + 17, str(s[1]), "ta" if foc else "t", 12, "middle", mono=True)
            a.text(tx + tw - 10, y + 17, str(s[2]), "ta" if foc else "tm", 11, "end", mono=True)
    yh, yl = ty + home * rh + rh / 2, ty + land * rh + rh / 2
    cx = 24 + len(calc) * 6.6 + 8
    a.path(f"M{cx:.1f} 124 H 384 C 404 124, 400 {yh}, {tx - 22} {yh}", "a", arrow=True)
    a.path(f"M{tx + tw} {yh} C {tx + tw + 30} {yh}, {tx + tw + 30} {yl}, {tx + tw + 2} {yl}", "a", arrow=True)
    used = sum(1 for s in slots if s)
    a.text(24, 282, f"{used} of {size} slots in use. Past 3/4 full, grow to {2 * size} slots and insert every word again.", "tm", 11)
    return a


# =================================================================== 02 sort

def dsa_sort():
    a = Art("d02", "Sorting a file bigger than memory: sorted runs on disk, merged through a heap of their heads")
    runs = [[3, 8, 15, 21], [1, 9, 12, 30], [5, 6, 17, 25]]
    assert all(r == sorted(r) for r in runs)
    pos = [0] * len(runs)
    heap = [(r[0], i) for i, r in enumerate(runs)]
    heapq.heapify(heap)
    out = []
    for _ in range(5):
        v, i = heapq.heappop(heap)
        out.append(v)
        pos[i] += 1
        if pos[i] < len(runs[i]):
            heapq.heappush(heap, (runs[i][pos[i]], i))
    assert out == sorted(out) and out == sorted(sum(runs, []))[:5]
    top, top_run = heap[0]

    a.text(24, 30, "sorted runs on disk", "tm", 10.5)
    cw, ch = 36, 28
    for i, r in enumerate(runs):
        y = 44 + i * 46
        a.text(24, y + 19, f"run {i + 1}", size=11, mono=True, weight=600 if i == top_run else None)
        for k, v in enumerate(r):
            x = 80 + k * (cw + 4)
            done = k < pos[i]
            head = k == pos[i]
            foc = head and i == top_run
            cls = "a af" if foc else ("m" if done else ("s fs" if head else "s f"))
            cell(a, x, y, cw, ch, str(v), cls, "ta" if foc else ("tm" if done else "t"), 12, rx=5, dash=done,
                 weight=700 if head else None)
    a.text(80, 196, "dashed: already written out", "tm", 10.5)

    # the heap: one entry per run, smallest on top
    hx, hy = 330, 30
    a.text(hx, hy, "heap of run heads", "tm", 10.5, "middle")
    pts = [(hx, 68), (hx - 44, 136), (hx + 44, 136)]
    for k in (1, 2):
        if k < len(heap):
            x1, y1, x2, y2 = toward(*pts[0], *pts[k], 18, 18)
            a.line(x1, y1, x2, y2, "s")
    for k, (v, i) in enumerate(heap):
        x, y = pts[k]
        foc = k == 0
        node(a, x, y, str(v), 18, "a af" if foc else "s fs", "ta" if foc else "t", 13, 700)
        a.text(x, y + 32, f"run {i + 1}", "ta" if foc else "tm", 10, "middle")
    a.text(hx, 196, "as an array: [" + ", ".join(str(v) for v, _ in heap) + "]", "tm", 10.5, "middle", mono=True)

    # output so far, and the value about to be written
    ox, ow = 436, 26
    a.text(ox, 30, "output", "tm", 10.5)
    for k, v in enumerate(out):
        cell(a, ox + k * (ow + 3), 54, ow, ch, str(v), "s f", "t", 12, rx=5)
    nx = ox + len(out) * (ow + 3)
    cell(a, nx, 54, ow, ch, str(top), "a af", "ta", 12, rx=5, weight=700)
    a.path(f"M{hx + 18} 68 C {hx + 60} 104, {nx - 20} 104, {nx + ow / 2} 86", "a", arrow=True)
    a.text(ox, 124, f"pop {top}, the smallest head;", "ta", 11, weight=600)
    nxt = runs[top_run][pos[top_run] + 1]
    a.text(ox, 141, f"push {nxt}, the next value", "tm", 11)
    a.text(ox, 156, f"from run {top_run + 1}", "tm", 11)
    a.text(24, 252, "Sort what fits in memory into runs, write them to disk, then merge: one heap entry per run.", "tm", 11)
    a.text(24, 270, "Each step costs log(runs), and memory holds one block per run however big the file is.", "tm", 11)
    return a


# =================================================================== 03 edit

def dsa_edit():
    a = Art("d03", "Two ways to hold the text: a gap buffer at the cursor, and a piece table that never moves a byte")
    before, after, gap = "the quick ", "fox", 6
    # gap buffer
    a.text(24, 28, "gap buffer", size=12, weight=700)
    a.text(104, 28, "the free space sits at the cursor", "tm", 10.5)
    cw, y0 = 21, 40
    x = 24
    for ch in before:
        cell(a, x, y0, cw, 26, ch.strip(), "s f", "t", 12, rx=0)
        x += cw
    gx = x
    for _ in range(gap):
        cell(a, x, y0, cw, 26, "", "m fs", rx=0, dash=True)
        x += cw
    for ch in after:
        cell(a, x, y0, cw, 26, ch, "s f", "t", 12, rx=0)
        x += cw
    a.line(gx, y0 - 5, gx, y0 + 31, "a")
    a.path(f"M{gx + 2} {y0 + 34} V {y0 + 40} H {gx + gap * cw - 2} V {y0 + 34}", "m")
    a.text(gx + gap * cw / 2, y0 + 54, "gap", "tm", 10.5, "middle")
    a.text(gx, y0 + 54, "cursor", "ta", 10.5, "end")
    a.text(452, 48, "a key fills one gap slot: O(1);", "tm", 10.5)
    a.text(452, 63, "moving the cursor copies text", "tm", 10.5)
    a.text(452, 78, "across the gap", "tm", 10.5)

    # piece table, after typing "brown " at the cursor
    orig, add = before + after, "brown "
    at = len(before)
    pieces = [("orig", 0, at), ("add", 0, len(add)), ("orig", at, len(orig) - at)]
    text = "".join((orig if b == "orig" else add)[s:s + n] for b, s, n in pieces)
    assert text == "the quick brown fox"
    a.text(24, 126, "piece table", size=12, weight=700)
    a.text(106, 126, "after typing 'brown ' at the cursor", "tm", 10.5)
    bw, ox, oy = 19, 108, 138
    a.text(24, oy + 16, "original", "tm", 10.5)
    for k, ch in enumerate(orig):
        cell(a, ox + k * bw, oy, bw, 24, ch.strip(), "s f", "t", 11.5, rx=0)
    a.text(24, 270, "add", "tm", 10.5)
    ax, ay = 108, 254
    for k, ch in enumerate(add):
        cell(a, ax + k * bw, ay, bw, 24, ch.strip(), "a af", "ta", 11.5, rx=0)
    a.text(ax + len(add) * bw + 8, ay + 16, "append-only", "tm", 10.5)
    # the pieces, a list in text order
    py, pw, ph = 196, 92, 30
    pxs = [108, 230, 352]
    for k, ((buf, s, n), px) in enumerate(zip(pieces, pxs)):
        foc = buf == "add"
        cell(a, px, py, pw, ph, f"{buf} {s}, {n}", "a af" if foc else "s fs", "ta" if foc else "t", 11, rx=6,
             weight=600)
        if k:
            a.line(pxs[k - 1] + pw, py + ph / 2, px - 2, py + ph / 2, "s", arrow=True)
        if buf == "orig":
            sx0, sx1 = ox + s * bw, ox + (s + n) * bw
            a.path(f"M{sx0 + 1} {oy + 28} V {oy + 33} H {sx1 - 1} V {oy + 28}", "s")
            a.line(round((sx0 + sx1) / 2, 1), oy + 33, px + pw / 2, py - 2, "s", arrow=True)
        else:
            a.line(px + pw / 2, py + ph, ax + len(add) * bw / 2, ay - 2, "a", arrow=True)
    a.text(24, py + 20, "pieces", "tm", 10.5)
    tx = 470
    a.text(tx, 158, "read the pieces in order:", "tm", 10.5)
    a.add(f'<text class="t mono" x="{tx}" y="180" font-size="12">{esc(before)}'
          f'<tspan class="ta" font-weight="700">{esc(add)}</tspan>{esc(after)}</text>')
    a.text(tx, 212, "undo puts back the old list;", "tm", 10.5)
    a.text(tx, 227, "the buffers never change", "tm", 10.5)
    return a


# =================================================================== 04 grep

def dsa_grep():
    a = Art("d04", "A regular expression as a machine: grep follows every possible state at once and reads each character once")
    pattern, data = "abab|abbb", "abbb"
    # states: 0 start; 1-4 spell abab, 5-8 spell abbb
    edges = [(0, "a", 1), (1, "b", 2), (2, "a", 3), (3, "b", 4), (0, "a", 5), (5, "b", 6), (6, "b", 7), (7, "b", 8)]
    accept = {4, 8}
    sets = [{0}]
    for ch in data:
        sets.append({t for s, c, t in edges if s in sets[-1] and c == ch})
    assert sets[-1] & accept
    alive = set().union(*sets)
    path = {0, 5, 6, 7, 8}

    a.text(24, 30, f"grep -E '{pattern}'", size=12.5, weight=700, mono=True)
    pos = {0: (60, 140)}
    for k in range(4):
        pos[1 + k] = (148 + k * 82, 82)
        pos[5 + k] = (148 + k * 82, 198)
    r = 16
    a.line(24, 140, 60 - r - 2, 140, "s", arrow=True)
    a.text(24, 130, "start", "tm", 10)
    for s, ch, t in edges:
        x1, y1, x2, y2 = toward(*pos[s], *pos[t], r, r + 2)
        on = s in path and t in path
        a.line(x1, y1, x2, y2, "a" if on else ("s" if t in alive else "m"), arrow=True)
        mx, my = (pos[s][0] + pos[t][0]) / 2, (pos[s][1] + pos[t][1]) / 2
        dy = -8 if pos[s][1] == pos[t][1] else 0
        dx = 0 if pos[s][1] == pos[t][1] else 14
        if s == 0:
            dx, dy = (-10, -6) if t == 1 else (-10, 14)
        a.text(round(mx + dx, 1), round(my + dy, 1), ch, "ta" if on else "tm", 12, "middle", 600, mono=True)
    for s, (x, y) in pos.items():
        on = s in path
        dead = s not in alive
        a.circle(x, y, r, "a af" if on else ("m f" if dead else "s f"))
        if s in accept:
            a.circle(x, y, r - 4, "a" if on else "m")
        a.text(x, y + 4.5, str(s), "ta" if on else ("tm" if dead else "t"), 12, "middle", 600, mono=True)
    a.text(pos[2][0], pos[2][1] - 26, "wants 'a', reads 'b': dropped", "tm", 10.5, "middle")
    a.text(pos[8][0], pos[8][1] + 34, "match", "ta", 11, "middle", 700)

    # the sets it passed through: the DFA, built one state at a time
    sx = 456
    a.text(sx, 30, f"reading '{data}'", size=12, weight=700)
    a.text(sx, 46, "the live states, as a set", "tm", 10.5)
    for k, st in enumerate(sets):
        y = 58 + k * 42
        last = k == len(sets) - 1
        label = "{" + ", ".join(str(s) for s in sorted(st)) + "}"
        cell(a, sx, y, 76, 26, label, "a af" if last else "s fs", "ta" if last else "t", 12, rx=6, weight=600)
        if k < len(data):
            a.line(sx + 38, y + 26, sx + 38, y + 40, "s", arrow=True)
            a.text(sx + 48, y + 38, data[k], "tm", 11.5, weight=600, mono=True)
    a.text(sx + 86, 58 + 2 * 42 + 17, "each set is", "tm", 10.5)
    a.text(sx + 86, 58 + 2 * 42 + 32, "one DFA state,", "tm", 10.5)
    a.text(sx + 86, 58 + 2 * 42 + 47, "cached", "tm", 10.5)
    a.text(24, 270, "No backtracking: one pass over the input, so no pattern can make it hang.", "tm", 11)
    a.text(24, 287, "Double ring: an accepting state.", "tm", 11)
    return a


# =================================================================== 05 spell

def lev(s, t):
    prev = list(range(len(t) + 1))
    for i, cs in enumerate(s, 1):
        cur = [i]
        for j, ct in enumerate(t, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (cs != ct)))
        prev = cur
    return prev[-1]


def dsa_spell():
    a = Art("d05", "A trie: a prefix is one walk from the root, and every word below it is a completion")
    words = ["car", "card", "care", "cat", "do", "dog"]
    prefix, typo = "ca", "cst"
    trie = {}
    for w in words:
        n = trie
        for ch in w:
            n = n.setdefault(ch, {})
        n["$"] = True
    completions = sorted(w for w in words if w.startswith(prefix))
    best = min(lev(typo, w) for w in words)
    near = [w for w in words if lev(typo, w) == best]
    assert completions == ["car", "card", "care", "cat"] and near == ["cat"] and best == 1

    # laid out left to right: one column per letter of the word
    pos = {"": (40, 150), "c": (112, 106), "d": (112, 226), "ca": (184, 106), "do": (184, 226),
           "car": (256, 70), "cat": (256, 166), "dog": (256, 226), "card": (328, 44), "care": (328, 100)}
    r = 15

    def walk(n, key):
        for ch, sub in n.items():
            if ch == "$":
                continue
            k = key + ch
            x1, y1, x2, y2 = toward(*pos[key], *pos[k], r, r)
            on = prefix.startswith(k) or k.startswith(prefix)
            a.line(x1, y1, x2, y2, "a" if on else "s")
            walk(sub, k)

    def get(key):
        n = trie
        for ch in key:
            n = n[ch]
        return n
    walk(trie, "")
    for key, (x, y) in pos.items():
        on = key and (prefix.startswith(key) or key.startswith(prefix))
        a.circle(x, y, r, "a af" if on else ("s fs" if not key else "s f"))
        if get(key).get("$"):
            a.circle(x, y, r - 4, "a" if on else "s")
        if key:
            a.text(x, y + 4.5, key[-1], "ta" if on else "t", 13, "middle", 700, mono=True)
    a.text(40, 182, "root", "tm", 10.5, "middle")
    for w in completions:
        x, y = pos[w]
        a.text(x + r + 6, y + 4, w, "ta", 10.5, mono=True)
    for w in ("do", "dog"):
        x, y = pos[w]
        a.text(x, y + r + 15, w, "tm", 10.5, "middle", mono=True)

    rx = 432
    a.text(rx, 34, f"complete '{prefix}'", size=12, weight=700)
    a.text(rx, 52, f"walk {', '.join(prefix)}, then list the", "tm", 10.5)
    a.text(rx, 67, "words below it:", "tm", 10.5)
    a.text(rx, 86, "  ".join(completions), "ta", 11.5, weight=600, mono=True)
    a.text(rx, 124, f"check '{typo}'", size=12, weight=700)
    a.text(rx, 142, f"after '{typo[0]}' there is no '{typo[1]}' branch:", "tm", 10.5)
    a.text(rx, 157, "not in the dictionary", "tm", 10.5)
    a.text(rx, 176, f"did you mean: {near[0]}?", "ta", 11.5, weight=600, mono=True)
    a.text(rx, 192, f"edit distance {best}: {typo[1]} -> {near[0][1]}", "tm", 10.5)
    a.text(rx, 230, "Bloom filter", size=12, weight=700)
    a.text(rx, 248, "the same check in 9.6 bits a word:", "tm", 10.5)
    a.text(rx, 263, "its 'no' is always right, its", "tm", 10.5)
    a.text(rx, 278, "'maybe' wrong 1% of the time", "tm", 10.5)
    a.text(24, 284, "Double ring: a word ends here.", "tm", 10.5)
    return a


# =================================================================== 06 diff

def dsa_diff():
    a = Art("d06", "diff as dynamic programming: a table of longest common subsequences, and the path through it that becomes the edits")
    old, new = "ABCABBA", "CBABAC"     # the example in Myers' paper
    n, m = len(old), len(new)
    L = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            L[i][j] = L[i - 1][j - 1] + 1 if old[i - 1] == new[j - 1] else max(L[i - 1][j], L[i][j - 1])
    # The shortest edit script Myers' paper (and the Coglan article) gives for this pair. Several
    # paths are equally short; check this one is a real path through the table: a diagonal only
    # where the lines match, every cell on it equal to the matches so far, LCS-many matches in all.
    ops = "--=+==-=+"
    i, j, kept, steps = 0, 0, 0, []
    for op in ops:
        if op == "=":
            assert old[i] == new[j]
            steps.append((" ", old[i])); i += 1; j += 1; kept += 1
        elif op == "-":
            steps.append(("-", old[i])); i += 1
        else:
            steps.append(("+", new[j])); j += 1
        assert L[i][j] == kept
        steps[-1] += (i, j)
    assert (i, j) == (n, m) and kept == L[n][m] == 4
    script = [(op, ch) for op, ch, _, _ in steps]
    cells = {(0, 0)} | {(i, j) for _, _, i, j in steps}

    a.text(24, 26, f"old: {old}", size=12, weight=600, mono=True)
    a.text(148, 26, f"new: {new}", size=12, weight=600, mono=True)
    x0, y0, cw, ch = 64, 58, 28, 24
    for j in range(1, m + 1):
        a.text(x0 + j * cw + cw / 2, y0 - 8, new[j - 1], "t", 11.5, "middle", 700, mono=True)
    for i in range(n + 1):
        if i:
            a.text(x0 - 10, y0 + i * ch + 16, old[i - 1], "t", 11.5, "end", 700, mono=True)
        for j in range(m + 1):
            on = (i, j) in cells
            a.add(f'<rect class="{"af" if on else "f"}" x="{x0 + j * cw}" y="{y0 + i * ch}" width="{cw}" height="{ch}"/>')
            a.text(x0 + j * cw + cw / 2, y0 + i * ch + 16, str(L[i][j]), "ta" if on else "tm", 11, "middle",
                   700 if on else None, mono=True)
    for j in range(m + 2):
        a.line(x0 + j * cw, y0, x0 + j * cw, y0 + (n + 1) * ch, "m")
    for i in range(n + 2):
        a.line(x0, y0 + i * ch, x0 + (m + 1) * cw, y0 + i * ch, "m")
    a.box(x0, y0, (m + 1) * cw, (n + 1) * ch, "s", rx=0)

    # the diff, read off the path
    dx = 300
    a.text(dx, 52, "the path, read forwards", size=12, weight=700)
    for k, (op, c) in enumerate(script):
        y = 74 + k * 17
        a.text(dx + 4, y, f"{op} {c}", "ta" if op == "+" else ("t" if op == "-" else "tm"), 12,
               weight=700 if op != " " else None, mono=True)
    rx = 384
    rules = [("diagonal", "same line: keep it, +1"), ("down", "delete a line of old"), ("across", "insert a line of new")]
    for k, (h, t) in enumerate(rules):
        y = 82 + k * 40
        a.text(rx, y, h, size=11.5, weight=700)
        a.text(rx, y + 16, t, "tm", 10.5)
    a.text(rx, 222, f"{L[n][m]} lines in common,", "ta", 11, weight=600)
    nd = sum(op == "-" for op, _ in script)
    ni = sum(op == "+" for op, _ in script)
    a.text(rx, 238, f"{nd} deletes, {ni} inserts", "ta", 11, weight=600)
    a.text(24, 282, "Cell (i, j): the LCS length of the first i old and first j new lines, from the cells above and to the left.",
           "tm", 11)
    return a


# =================================================================== 07 make

def dsa_make():
    a = Art("d07", "make: the makefile is a graph; after an edit, rebuild only what depends on it, in topological order")
    rules = {"freq": ["freq.o", "hash.o", "vec.o"], "freq.o": ["freq.c", "hash.h", "vec.h"],
             "hash.o": ["hash.c", "hash.h"], "vec.o": ["vec.c", "vec.h"]}
    edited = "hash.h"
    users = {}
    for t, deps in rules.items():
        for d in deps:
            users.setdefault(d, []).append(t)
    stale, todo = set(), [edited]
    while todo:
        for u in users.get(todo.pop(), []):
            if u not in stale:
                stale.add(u); todo.append(u)
    # build in waves: a target is ready once none of its stale prerequisites is left
    waves, left = [], set(stale)
    while left:
        ready = sorted(t for t in left if not (set(rules[t]) & left))
        waves.append(ready)
        left -= set(ready)
    assert waves == [["freq.o", "hash.o"], ["freq"]]

    a.text(24, 28, "Makefile", size=12, weight=700, mono=True)
    a.box(24, 38, 212, 82, "s fs", rx=8)
    for k, (t, deps) in enumerate(rules.items()):
        a.text(36, 60 + k * 17, f"{t}: {' '.join(deps)}", size=10.5, mono=True)
    a.text(24, 146, f"you edit {edited}:", "ta", 12, weight=700)
    a.text(24, 165, "step 1, at the same time", "tm", 10.5)
    a.text(36, 181, "cc -c " + waves[0][1].replace(".o", ".c"), size=10.5, mono=True)
    a.text(36, 196, "cc -c " + waves[0][0].replace(".o", ".c"), size=10.5, mono=True)
    a.text(24, 216, "step 2, after both", "tm", 10.5)
    a.text(36, 232, "cc -o freq " + " ".join(rules["freq"]), size=10.5, mono=True)

    srcs = ["hash.c", "hash.h", "freq.c", "vec.h", "vec.c"]
    objs = ["hash.o", "freq.o", "vec.o"]
    nw, nh = 62, 26
    pos = {s: (304 + k * 72, 214) for k, s in enumerate(srcs)}
    pos.update({o: (340 + k * 108, 140) for k, o in enumerate(objs)})
    pos["freq"] = (448, 66)
    for t, deps in rules.items():
        for d in deps:
            (x1, y1), (x2, y2) = pos[d], pos[t]
            hot = d == edited or d in stale
            a.line(x1, y1 - nh / 2, round(x2 + (x1 - x2) * 0.18, 1), y2 + nh / 2 + 2, "a" if hot else "m", arrow=True)
    for name, (x, y) in pos.items():
        hot = name == edited or name in stale
        cls = "a af" if hot else ("s f" if name in srcs else "s fs")
        cell(a, x - nw / 2, y - nh / 2, nw, nh, name, cls, "ta" if hot else "t", 11, rx=6, weight=700 if hot else None)
    a.text(24, 256, "vec.o is newer than vec.c and vec.h: skipped", "tm", 10.5)
    a.text(pos["freq"][0] + nw / 2 + 12, pos["freq"][1] + 4, "step 2", "ta", 11, weight=600)
    a.text(pos["hash.o"][0] - nw / 2 - 10, pos["hash.o"][1] + 4, "step 1", "ta", 11, "end", 600)
    a.text(616, 28, "arrow: is needed to build", "tm", 10.5, "end")
    a.text(24, 284, "A depth-first walk orders the graph so each file is built after all it needs, once. A cycle is an error.", "tm", 11)
    return a


# =================================================================== 08 route

def dsa_route():
    a = Art("d08", "Shortest paths on a road map: Dijkstra pops the nearest junction from a heap until it pops the goal")
    pos = {"A": (52, 142), "B": (164, 68), "C": (164, 210), "D": (290, 142), "E": (300, 56), "F": (300, 220), "G": (420, 142)}
    roads = [("A", "B", 5), ("A", "C", 2), ("A", "D", 12), ("B", "E", 4), ("B", "D", 4), ("C", "D", 6), ("C", "F", 3),
             ("D", "G", 6), ("E", "G", 7), ("F", "G", 5)]
    adj = {k: [] for k in pos}
    for u, v, w in roads:
        adj[u].append((v, w)); adj[v].append((u, w))
    dist, prev, order, heap = {"A": 0}, {}, [], [(0, "A")]
    done = set()
    while heap:
        d, u = heapq.heappop(heap)
        if u in done:
            continue
        done.add(u); order.append((u, d))
        if u == "G":
            break
        for v, w in adj[u]:
            if d + w < dist.get(v, 1e9):
                dist[v] = d + w; prev[v] = u
                heapq.heappush(heap, (d + w, v))
    best = ["G"]
    while best[-1] != "A":
        best.append(prev[best[-1]])
    best.reverse()
    # breadth-first: fewest roads, whatever their length
    bprev, q = {"A": None}, ["A"]
    while q:
        u = q.pop(0)
        for v, _ in sorted(adj[u]):
            if v not in bprev:
                bprev[v] = u; q.append(v)
    few = ["G"]
    while bprev[few[-1]]:
        few.append(bprev[few[-1]])
    few.reverse()
    length = lambda p: sum(next(w for v, w in adj[x] if v == y) for x, y in zip(p, p[1:]))
    assert best == ["A", "C", "F", "G"] and length(best) == 10 and few == ["A", "D", "G"] and length(few) == 18
    on = set(zip(best, best[1:])) | set(zip(best[1:], best))

    r = 15
    lab_off = {("A", "B"): (-10, -6), ("A", "C"): (-10, 12), ("A", "D"): (0, -7), ("B", "E"): (0, -8),
               ("B", "D"): (10, -6), ("C", "D"): (10, 12), ("C", "F"): (0, 16), ("D", "G"): (0, -7),
               ("E", "G"): (10, -6), ("F", "G"): (10, 12)}
    for u, v, w in roads:
        x1, y1, x2, y2 = toward(*pos[u], *pos[v], r, r)
        hot = (u, v) in on
        a.line(x1, y1, x2, y2, "a" if hot else "m")
        dx, dy = lab_off[(u, v)]
        mx, my = (pos[u][0] + pos[v][0]) / 2 + dx, (pos[u][1] + pos[v][1]) / 2 + dy
        a.text(round(mx, 1), round(my + 4, 1), str(w), "ta" if hot else "tm", 11, "middle", 700 if hot else None, mono=True)
    dpos = {"A": (0, -22), "B": (0, -22), "C": (0, 32), "D": (0, -22), "E": (0, -22), "F": (0, 32), "G": (0, -22)}
    for k, (x, y) in pos.items():
        hot = k in best
        node(a, x, y, k, r, "a af" if hot else "s f", "ta" if hot else "t", 12.5, 700, mono=False)
        ox, oy = dpos[k]
        a.text(x + ox, y + oy, str(dist[k]), "ta" if hot else "tm", 10.5, "middle", 600, mono=True)
    a.text(pos["A"][0], pos["A"][1] + r + 16, "start", "tm", 10.5, "middle")
    a.text(446, pos["G"][1] + 4, "goal", "tm", 10.5)

    px = 492
    a.text(px, 28, "pops, nearest first", size=12, weight=700)
    for k, (u, d) in enumerate(order):
        y = 50 + k * 17
        hot = u in best
        a.text(px, y, u, "ta" if hot else "t", 11.5, weight=700, mono=True)
        a.text(px + 18, y, str(d), "ta" if hot else "tm", 11.5, mono=True)
        if u == "G":
            a.text(px + 44, y, "goal: stop", "ta", 10.5)
    a.text(px, 192, "fewest roads (BFS)", "tm", 10.5)
    a.text(px, 208, f"{'-'.join(few)} = {length(few)}", size=11.5, mono=True)
    a.text(px, 232, "shortest (Dijkstra)", "ta", 10.5)
    a.text(px, 248, f"{'-'.join(best)} = {length(best)}", "ta", 11.5, weight=700, mono=True)
    a.text(24, 286, "Numbers on nodes: distance from A. A* also adds a guess of the distance left, so it pops fewer.", "tm", 11)
    return a


# =================================================================== 09 gzip

def dsa_gzip():
    a = Art("d09", "Huffman's greedy tree gives common symbols short codes; LZ77 replaces a repeat with a pointer back")
    text = "abracadabra"
    counts = {}
    for c in text:
        counts[c] = counts.get(c, 0) + 1
    heap, order, merges = [], 0, []
    for c, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        heap.append((n, order, c)); order += 1
    heapq.heapify(heap)
    while len(heap) > 1:
        n1, _, t1 = heapq.heappop(heap)
        n2, _, t2 = heapq.heappop(heap)
        merges.append((t1, n1, t2, n2))
        heapq.heappush(heap, (n1 + n2, order, (t1, t2))); order += 1
    root = heap[0][2]
    codes = {}

    def assign(t, code):
        if isinstance(t, str):
            codes[t] = code
        else:
            assign(t[0], code + "0"); assign(t[1], code + "1")
    assign(root, "")
    bits = sum(len(codes[c]) for c in text)
    assert bits == 23 and codes["a"] == "0"

    def letters(t):
        return t if isinstance(t, str) else letters(t[0]) + letters(t[1])

    def weight(t):
        return sum(counts[c] for c in letters(t))

    a.text(24, 30, "input", "tm", 10.5)
    a.text(24, 52, text, size=14, weight=700, mono=True)
    a.text(24, 84, "symbol", "tm", 10)
    a.text(104, 84, "count", "tm", 10, "end")
    a.text(120, 84, "code", "tm", 10)
    for k, c in enumerate(sorted(counts, key=lambda c: (-counts[c], codes[c]))):
        y = 104 + k * 18
        a.text(30, y, c, size=12, weight=700, mono=True)
        a.text(98, y, str(counts[c]), "tm", 12, "end", mono=True)
        a.text(120, y, codes[c], "ta", 12, weight=600, mono=True)

    # the tree: leaves spread left to right, parents centred over their children
    xs, ys = {}, {}
    leaves = []

    def place(t, depth):
        ys[id(t)] = 44 + depth * 54
        if isinstance(t, str):
            leaves.append(t)
            xs[id(t)] = 214 + (len(leaves) - 1) * 56
        else:
            place(t[0], depth + 1); place(t[1], depth + 1)
            xs[id(t)] = (xs[id(t[0])] + xs[id(t[1])]) / 2
    place(root, 0)

    def draw(t):
        x, y = xs[id(t)], ys[id(t)]
        if isinstance(t, str):
            cell(a, x - 19, y - 14, 38, 28, f"{t} {counts[t]}", "s fs", "t", 12, rx=6, weight=700)
            return
        for bit, ch in zip("01", t):
            cx, cy = xs[id(ch)], ys[id(ch)]
            x1, y1, x2, y2 = toward(x, y, cx, cy, 14, 16 if isinstance(ch, str) else 14)
            a.line(x1, y1, x2, y2, "s")
            a.text(round((x + cx) / 2 + (-9 if bit == "0" else 9), 1), round((y + cy) / 2 + 2, 1), bit, "ta", 11,
                   "middle", 700, mono=True)
            draw(ch)
        node(a, x, y, str(weight(t)), 14, "s f", "tm", 11, 600)
    draw(root)

    mx = 488
    a.text(mx, 30, "join the two smallest,", size=11.5, weight=700)
    a.text(mx, 45, "until one tree is left", size=11.5, weight=700)
    for k, (t1, n1, t2, n2) in enumerate(merges):
        a.text(mx, 70 + k * 18, f"{n1} + {n2} = {n1 + n2}", size=11, mono=True)
        a.text(mx + 80, 70 + k * 18, f"{letters(t1)}, {letters(t2)}", "tm", 10.5, mono=True)
    a.text(mx, 168, f"{bits} bits instead of", "ta", 11.5, weight=700)
    a.text(mx, 184, f"{8 * len(text)} as bytes", "ta", 11.5, weight=700)

    # LZ77: the second "abra" is a copy
    lz = 7
    best = max(((lz - s, k) for s in range(lz) for k in range(1, len(text) - lz + 1)
                if text[s:s + k] == text[lz:lz + k]), key=lambda dk: dk[1])
    back, length = best
    assert (back, length) == (7, 4)
    a.text(24, 262, "LZ77", size=12, weight=700)
    a.add(f'<text class="t mono" x="72" y="262" font-size="12">{esc(text[:lz])}'
          f'<tspan class="ta" font-weight="700">[back {back}, copy {length}]</tspan></text>')
    a.text(330, 262, f"the second '{text[lz:lz + length]}' points at the first", "tm", 10.5)
    a.text(24, 284, "DEFLATE does both: LZ77 finds the repeats, then Huffman codes what is left.", "tm", 11)
    return a


# =================================================================== 10 git

def git_id(kind, body):
    return hashlib.sha1(f"{kind} {len(body)}\0".encode() + body).hexdigest()


def dsa_git():
    a = Art("d10", "git's object graph: commits point at trees, trees at blobs and trees, each named by the SHA-1 of its content")
    who = "Ada <ada@example.com>"
    main_c = git_id("blob", b"int main(void) { return 0; }\n")
    r1 = git_id("blob", b"hello\n")
    r2 = git_id("blob", b"hello, world\n")
    entry = lambda mode, name, h: f"{mode} {name}\0".encode() + bytes.fromhex(h)
    src = git_id("tree", entry("100644", "main.c", main_c))
    t1 = git_id("tree", entry("100644", "README", r1) + entry("40000", "src", src))
    t2 = git_id("tree", entry("100644", "README", r2) + entry("40000", "src", src))
    c1 = git_id("commit", f"tree {t1}\nauthor {who} 1700000000 +0000\ncommitter {who} 1700000000 +0000\n\nfirst\n".encode())
    c2 = git_id("commit", f"tree {t2}\nparent {c1}\nauthor {who} 1700000600 +0000\n"
                          f"committer {who} 1700000600 +0000\n\nsay hello, world\n".encode())
    # the same files committed by the real git give these ids (checked when this was written)
    assert r1.startswith("ce01362") and c2.startswith("2402ac3") and src.startswith("ed46dd1")

    bw, bh = 120, 42
    objs = {
        "c2": (24, 48, "commit", c2, '"say hello, world"'), "c1": (24, 180, "commit", c1, '"first"'),
        "t2": (184, 48, "tree", t2, "README, src/"), "t1": (184, 180, "tree", t1, "README, src/"),
        "r2": (344, 22, "blob", r2, '"hello, world\\n"'), "src": (344, 114, "tree", src, "main.c"),
        "r1": (344, 206, "blob", r1, '"hello\\n"'), "mc": (496, 114, "blob", main_c, "int main(void)..."),
    }
    shared = {"src", "mc"}
    for key, (x, y, kind, h, sub) in objs.items():
        foc = key in shared
        a.box(x, y, bw, bh, "a af" if foc else ("s fs" if kind == "commit" else "s f"), rx=8)
        a.add(f'<text class="{"ta" if foc else "t"} mono" x="{x + 10}" y="{y + 17}" font-size="11.5">'
              f'<tspan font-weight="700">{kind}</tspan> {h[:7]}</text>')
        a.text(x + 10, y + 33, sub, "ta" if foc else "tm", 10, mono=kind == "blob")

    def arrow(f, t, cls="s", fy=None, ty=None):
        (fx0, fy0), (tx0, ty0) = objs[f][:2], objs[t][:2]
        x1, y1 = fx0 + bw, fy if fy is not None else fy0 + bh / 2
        x2, y2 = tx0 - 2, ty if ty is not None else ty0 + bh / 2
        a.path(f"M{x1} {y1} C {x1 + 20} {y1}, {x2 - 20} {y2}, {x2} {y2}", cls, arrow=True)
    arrow("c2", "t2"); arrow("c1", "t1")
    arrow("t2", "r2", fy=60); arrow("t2", "src", "a", fy=80, ty=130)
    arrow("t1", "src", "a", fy=188, ty=144); arrow("t1", "r1", fy=212)
    arrow("src", "mc", "a")
    # the parent link: the walk git log takes
    a.line(84, 90, 84, 178, "s", arrow=True)
    a.text(94, 128, "parent", "tm", 10.5)
    a.text(94, 143, "git log", "tm", 10.5)
    a.text(94, 158, "walks these", "tm", 10.5)
    a.box(24, 12, 46, 22, "s", rx=11)
    a.text(47, 27, "main", size=11, anchor="middle", weight=700, mono=True)
    a.line(47, 34, 47, 46, "s", arrow=True)
    a.text(556, 196, "src/ did not change:", "ta", 10.5, "middle", 600)
    a.text(556, 211, "both trees name it", "ta", 10.5, "middle")
    a.text(556, 226, "by the same hash", "ta", 10.5, "middle")
    a.text(24, 270, "An object is named by the SHA-1 of its content: what did not change keeps its name and is stored once,", "tm", 11)
    a.text(24, 286, "and a change renames every object above it, up to the commit. These ids are the ones git computes.", "tm", 11)
    return a


# =================================================================== track art

def track_art():
    """The home page card, 280x160: a heap drawn as a tree and as the array that stores it."""
    sw = 'stroke-width="1.5"'
    vals = [2, 5, 3, 9, 7, 8, 4]
    assert all(vals[i] <= vals[c] for i in range(7) for c in (2 * i + 1, 2 * i + 2) if c < 7)
    hot = [0, 2, 6]
    pts = [(140, 22), (92, 56), (188, 56), (68, 90), (116, 90), (164, 90), (212, 90)]
    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 280 160">']
    for c in range(1, 7):
        p = (c - 1) // 2
        x1, y1, x2, y2 = toward(*pts[p], *pts[c], 10, 10)
        if not (p in hot and c in hot):
            out.append(f'<path class="m" d="M{x1} {y1}L{x2} {y2}" {sw} stroke-linecap="round"/>')
    for i, (x, y) in enumerate(pts):
        cls = "a af" if i in hot else "s f"
        out.append(f'<circle class="{cls}" cx="{x}" cy="{y}" r="10" stroke-width="1.75"/>')
        out.append(f'<text class="{"ta" if i in hot else "t"} mono" x="{x}" y="{y + 3.5}" font-size="10" '
                   f'text-anchor="middle" font-weight="600">{vals[i]}</text>')
    seg = []
    for p, c in zip(hot, hot[1:]):
        x1, y1, x2, y2 = toward(*pts[p], *pts[c], 10, 10)
        seg.append(f"M{x1} {y1}L{x2} {y2}")
    out.append(f'<path class="a draw" d="{"".join(seg)}" pathLength="1" stroke-width="2.25" stroke-linecap="round"/>')
    cw, x0, y0 = 24, 56, 118
    for i, v in enumerate(vals):
        x = x0 + i * cw
        cls = "a af" if i in hot else "s f"
        out.append(f'<rect class="{cls}" x="{x}" y="{y0}" width="{cw}" height="20" rx="2" stroke-width="1.5"/>')
        out.append(f'<text class="{"ta" if i in hot else "t"} mono" x="{x + cw / 2}" y="{y0 + 14}" font-size="10" '
                   f'text-anchor="middle" font-weight="600">{v}</text>')
        out.append(f'<text class="tm mono" x="{x + cw / 2}" y="{y0 + 33}" font-size="7.5" text-anchor="middle">{i}</text>')
    out.append(f'<text class="tm mono" x="{x0 - 6}" y="{y0 + 14}" font-size="8" text-anchor="end">a[]</text>')
    out.append(f'<text class="tm mono" x="{x0 + 7 * cw + 6}" y="{y0 + 14}" font-size="8">children of i:</text>')
    out.append(f'<text class="tm mono" x="{x0 + 7 * cw + 6}" y="{y0 + 25}" font-size="8">2i+1, 2i+2</text>')
    out.append("</svg>\n")
    return "\n".join(out)


ICON = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="none" stroke="currentColor" '
        'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">{}</svg>\n')

TRACK_ICON = ('<rect x="7.5" y="2.5" width="5" height="5" rx="1"/><rect x="2.5" y="12.5" width="5" height="5" rx="1"/>'
              '<rect x="12.5" y="12.5" width="5" height="5" rx="1"/><path d="M8.75 7.5L6.25 12.5M11.25 7.5l2.5 5"/>')

MODULES = {
    "00": (dsa_workbench, '<path d="M3 3v14h14"/><path d="M6 14.5c4.5 0 7.5-3.5 9.5-10"/>'
                          '<path d="M6 14.5h.01M11.7 11.9h.01M15.5 4.5h.01" stroke-width="2.6"/>'),
    "01": (dsa_freq, '<rect x="9.5" y="2.5" width="8" height="15" rx="1.5"/><path d="M9.5 6.25h8M9.5 10h8M9.5 13.75h8"/>'
                     '<path d="M2.5 11.9h4.5M5.25 10.15l1.75 1.75-1.75 1.75"/>'),
    "02": (dsa_sort, '<path d="M4 16.5v-2M8 16.5v-5M12 16.5v-8M16 16.5V3.5" stroke-width="2.25"/>'),
    "03": (dsa_edit, '<path d="M2.5 5h7M2.5 10h4.5M2.5 15h7"/><path d="M13.5 3.5v13M11.75 3.5h3.5M11.75 16.5h3.5"/>'),
    "04": (dsa_grep, '<circle cx="5" cy="11" r="2.75"/><circle cx="15" cy="11" r="2.75"/><circle cx="15" cy="11" r="1"/>'
                     '<path d="M7.75 11h4.25M10.5 9.5l1.5 1.5-1.5 1.5"/><path d="M3.4 8.75C2.6 4.75 7.4 4.75 6.6 8.75"/>'),
    "05": (dsa_spell, '<circle cx="10" cy="3.75" r="1.75"/><circle cx="5.5" cy="10" r="1.75"/><circle cx="14.5" cy="10" r="1.75"/>'
                      '<circle cx="3" cy="16.25" r="1.75"/><circle cx="8" cy="16.25" r="1.75"/>'
                      '<path d="M9 5.2l-2.5 3.4M11 5.2l2.5 3.4M4.8 11.6l-1.1 3M6.2 11.6l1.1 3"/>'),
    "06": (dsa_diff, '<path d="M10 3.5v7M6.5 7h7M6.5 15.5h7"/>'),
    "07": (dsa_make, '<circle cx="10" cy="3.75" r="1.75"/><circle cx="4.5" cy="10" r="1.75"/><circle cx="15.5" cy="10" r="1.75"/>'
                     '<circle cx="10" cy="16.25" r="1.75"/><path d="M8.8 5.1l-3.1 3.5M11.2 5.1l3.1 3.5M5.7 11.4l3.1 3.5M14.3 11.4l-3.1 3.5"/>'),
    "08": (dsa_route, '<circle cx="4.5" cy="15.5" r="2"/><circle cx="15.5" cy="4.5" r="2"/>'
                      '<path d="M6.5 15.5H11a2.5 2.5 0 000-5H9a2.5 2.5 0 010-5h4.5"/>'),
    "09": (dsa_gzip, '<path d="M10 2.5v5M7.5 5l2.5 2.5L12.5 5M10 17.5v-5M7.5 15l2.5-2.5 2.5 2.5M3 10h14"/>'),
    "10": (dsa_git, '<circle cx="6" cy="4.5" r="2"/><circle cx="6" cy="15.5" r="2"/><circle cx="14" cy="6.5" r="2"/>'
                    '<path d="M6 6.5v7M14 8.5c0 3.5-8 2.5-8 5"/>'),
}


def files():
    """{relative path: svg text} for every file this script owns."""
    out = {"art.svg": track_art(), "icon.svg": ICON.format(TRACK_ICON)}
    for mid, (fn, icon) in MODULES.items():
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


def main():
    out = files()
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
    sys.exit(main())
