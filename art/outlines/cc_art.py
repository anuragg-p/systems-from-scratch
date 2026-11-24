"""Art for the C compiler outline (outlines/cc.md, id cc), in the same visual language as
research_art.py and outline_art.py.

Writes, under outlines/cc/:
    art.svg         280x160, the track's picture on its home page card (one .draw path moves on hover)
    icon.svg        20x20 currentColor line icon for the top bar
    NN/cover.svg    640x300 teaching diagram for module NN (00 to 13; 10 to 13 are the extensions)
    NN/icon.svg     20x20 currentColor line icon for module NN

Covers style themselves only through the .art classes in harness/web/app.css:
    s m a        stroke: foreground, muted, accent
    f fs af fa   fill: page, code background, accent-soft, accent
    t tm ta      text fill: foreground, muted, accent      mono: monospace
One accent idea a cover: the accent classes mark the single thing the cover is about.

Code is set on a monospace grid: a line of code is split into runs of text, and each run is
placed at its own column (x = left + column * 0.6em, Geist Mono's advance), so indentation and
double spaces survive SVG's whitespace collapsing and a caret can sit under a given column.

Computed here, and asserted, so a typo stops the script instead of reaching a cover:
    01  the caret's column under the @ of the error line
    06  the three addresses p, p + 1 and p + 2 from base 0x1000 and sizeof(int) = 4
    07  struct S's offsets, size and alignment by "align each field to its size, pad the end"
    10  linear scan over five live ranges with three registers
    11  the 32-bit word of add a0, a0, a1 from its six fields
    11  ... and the distance the call's relocation holds, f's address minus the call's
    12  the addresses of the line table, from 0x80000000 in steps of 4: a 4-instruction prologue
        for line 1, then 2, 3 and 2 instructions for lines 2 to 4

The Art class is the one from research_art.py, repeated so this file stands alone.

    python3 art/outlines/cc_art.py [NN ...]
        write every file (or only modules NN), then check each one is ASCII and survives
        harness/web/art.py's sanitizer unchanged
"""
import html
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "outlines", "cc")
SW = 'stroke-width="1.5"'
EM = 0.6            # the monospace advance, in em (Geist Mono, SF Mono, Menlo)


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

    def line(self, x1, y1, x2, y2, cls="s", arrow=False, dash=False):
        m = f' marker-end="url(#{self.key}-{self.marker(cls)})"' if arrow else ""
        d = ' stroke-dasharray="4 4"' if dash else ""
        self.add(f'<line class="{cls}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" {SW} stroke-linecap="round"{m}{d}/>')

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


def cell(a, x, y, w, h, s, cls="s f", tcls="t", size=12, rx=4, dash=False, weight=None, mono=True):
    """A box with one centred label: a character, a token, a register."""
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
    cw = EM * size
    wt = f' font-weight="{weight}"' if weight else ""
    assert size >= 10
    if len(runs) == 1 and runs[0][0] == 0:
        a.add(f'<text class="{runs[0][2]} mono" x="{x}" y="{y}" font-size="{size}"{wt}>{esc(runs[0][1])}</text>')
        return
    spans_out = "".join(
        f'<tspan x="{round(x + c * cw, 2)}"{"" if k == cls else f" class={chr(34)}{k}{chr(34)}"}>{esc(t)}</tspan>'
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


def chip(a, cx, y, s, cls="s f", tcls="t", size=11, mono=True, h=22, weight=None, w=None):
    """A pill centred on cx, its width from the text (monospace exact, sans estimated)."""
    w = w or round(len(s) * (EM if mono else 0.56) * size + 18)
    a.box(round(cx - w / 2, 1), y, w, h, cls, rx=h / 2)
    a.text(cx, round(y + h / 2 + size * 0.35, 1), s, tcls, size, "middle", weight, mono)
    return w


def page(a, x, y, w, h, cls="s f", dash=False, fold=10):
    """A file: a rectangle with its top right corner folded."""
    a.path(f"M{x} {y} H{x + w - fold} L{x + w} {y + fold} V{y + h} H{x} Z", cls, dash=dash)
    a.path(f"M{x + w - fold} {y} V{y + fold} H{x + w}", cls.split()[0], dash=dash)


# =================================================================== the track's own pair

def track_art():
    """280x160: source, the cc box, assembly; the one accent path runs through cc."""
    size, lh, pad = 11.5, 20, 8
    c = cw(size)
    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 280 160" fill="none">']
    cards = [(8, 100, ["int main() {", "  return 42;", "}"]), (178, 94, ["main:", "  li a0, 42", "  ret"])]
    h, y0 = 86, 37
    for x, w, lines in cards:
        assert max(len(l) for l in lines) * c + 2 * pad <= w
    # the path first, so the cc box sits over it and it seems to pass through
    out.append(f'<path class="a draw" d="M108 80 H178" pathLength="1" stroke-width="2.5" '
               f'stroke-linecap="round" stroke-linejoin="round"/>')
    for x, w, lines in cards:
        out.append(f'<rect class="s f" x="{x}" y="{y0}" width="{w}" height="{h}" rx="8" stroke-width="1.5"/>')
        for k, l in enumerate(lines):
            ind = len(l) - len(l.lstrip(" "))
            out.append(f'<text class="t mono" x="{round(x + pad + ind * c, 1)}" y="{y0 + 26.5 + k * lh}" '
                       f'font-size="{size}">{esc(l.strip())}</text>')
    out.append('<rect class="s f" x="126" y="62" width="34" height="36" rx="8" stroke-width="1.5"/>')
    out.append('<text class="ta mono" x="143" y="84.5" font-size="14" font-weight="700" text-anchor="middle">cc</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


TRACK_ICON = ('<path d="M6.5 3C5 3 4.5 3.75 4.5 5.25V8c0 1.25-.75 2-2 2 1.25 0 2 .75 2 2v2.75C4.5 16.25 5 17 6.5 17"/>'
              '<path d="M13.5 3c1.5 0 2 .75 2 2.25V8c0 1.25.75 2 2 2-1.25 0-2 .75-2 2v2.75c0 1.5-.5 2.25-2 2.25"/>'
              '<path d="M7.5 10h4.75M10.5 8l2 2-2 2"/>')


# =================================================================== 00 the smallest compiler

def cc_smallest():
    a = Art("c00", "One number becomes a running program, and gcc must agree")
    ty, by = 96, 204
    # top lane: your compiler, and every step after it
    page(a, 24, ty - 24, 44, 48, "s f")
    a.text(46, ty + 5, "42", size=15, anchor="middle", weight=700, mono=True)
    a.line(70, ty, 98, ty, arrow=True)
    a.box(100, ty - 20, 72, 40, "s f", rx=8)
    a.text(136, ty - 3, "your", size=11.5, anchor="middle", weight=600)
    a.text(136, ty + 11, "compiler", size=11.5, anchor="middle", weight=600)
    a.line(174, ty, 202, ty, arrow=True)
    a.box(204, ty - 26, 88, 52, "s fs", rx=6)
    for k, l in enumerate(["main:", "  li a0, 42", "  ret"]):
        code(a, 214, ty - 9 + k * 14, l, 10.5)
    a.line(294, ty, 322, ty, arrow=True)
    a.box(324, ty - 16, 58, 32, "s f", rx=8)
    a.text(353, ty + 4, "as + ld", size=11.5, anchor="middle", mono=True)
    a.line(384, ty, 412, ty, arrow=True)
    a.box(414, ty - 26, 80, 52, "s f", rx=8)
    for k, l in enumerate(["bare RISC-V", "machine", "in QEMU"]):
        a.text(454, ty - 8 + k * 13, l, size=11, anchor="middle", weight=600 if k == 0 else None)
    a.line(496, ty, 522, ty, arrow=True)
    a.box(524, ty - 12, 92, 24, "a af", rx=12)
    a.text(570, ty + 4, "exit status 42", "ta", 11, "middle", 600)
    # bottom lane: the same source, built by gcc for the same machine
    page(a, 24, by - 24, 44, 48, "m f", dash=True)
    a.text(46, by + 5, "42", "tm", 15, "middle", 700, mono=True)
    a.line(70, by, 164, by, "m", arrow=True, dash=True)
    a.box(166, by - 16, 152, 32, "m f", rx=8, dash=True)
    a.text(242, by + 4, "gcc, for the same machine", "tm", 11, "middle")
    a.line(320, by, 412, by, "m", arrow=True, dash=True)
    a.box(414, by - 16, 80, 32, "m f", rx=8, dash=True)
    a.text(454, by + 4, "same machine", "tm", 11, "middle")
    a.line(496, by, 522, by, "m", arrow=True, dash=True)
    a.box(524, by - 12, 92, 24, "a af", rx=12)
    a.text(570, by + 4, "exit status 42", "ta", 11, "middle", 600)
    # the test
    my = (ty + by) / 2
    a.line(570, ty + 12, 570, by - 12, "a")
    a.circle(570, my, 11, "a f")
    a.path(f"M564.5 {my - 3} H575.5 M564.5 {my + 3} H575.5", "a")
    a.text(550, my + 4, "the test: both agree", "ta", 11.5, "end", 600)
    return a


# =================================================================== 01 tokens

def cc_tokens():
    a = Art("c01", "Characters grouped into tokens, and an error that points at its column")
    src = "x = y1 >= 42; // n"
    n, w = len(src), 30
    x0 = (640 - n * w) / 2
    cy, ch = 50, 30
    X = lambda i: x0 + i * w
    for i, chr_ in enumerate(src):
        a.box(X(i), cy, w, ch, "s f", rx=0)
        if chr_ != " ":
            a.text(X(i) + w / 2, cy + 20, chr_, size=14, anchor="middle", mono=True)
    tokens = [("x", 0, "ident"), ("=", 2, "punct"), ("y1", 4, "ident"), (">=", 7, "punct"), ("42", 10, "num"),
              (";", 12, "punct")]
    for t, i, kind in tokens:
        assert src[i:i + len(t)] == t
        j = i + len(t)
        hot = t == ">="
        sc = "a" if hot else "s"
        bx0, bx1 = X(i) + 3, X(j) - 3
        mid = (X(i) + X(j)) / 2
        a.path(f"M{bx0} {cy + ch + 6} V{cy + ch + 12} H{bx1} V{cy + ch + 6}", sc)
        a.line(mid, cy + ch + 12, mid, cy + ch + 20, sc)
        bw = max(X(j) - X(i) - 6, 24)
        a.box(round(mid - bw / 2, 1), cy + ch + 20, bw, 24, "a af" if hot else "s fs", rx=8)
        a.text(mid, cy + ch + 37, t, "ta" if hot else "t", 13, "middle", 700 if hot else None, mono=True)
        a.text(mid, cy + ch + 60, kind, "tm", 10.5, "middle")
    # what the scanner skips: every space, and the comment, bracketed above the cells
    skipped = [(i, i + 1) for i, c in enumerate(src) if c == " " and i < src.index("//") - 1]
    skipped.append((src.index("//") - 1, n))
    for i, j in skipped:
        a.path(f"M{X(i) + 3} {cy - 6} V{cy - 12} H{X(j) - 3} V{cy - 6}", "m", dash=True)
    a.text((X(skipped[-1][0]) + X(n)) / 2, cy - 18, "skipped", "tm", 10.5, "middle")
    gx = (X(7) + X(9)) / 2
    a.text(gx, cy + ch + 82, "longest match: one token, not > then =", "ta", 11, "middle", 600)
    # the error, as the compiler prints it: the caret under the column of the @
    err = "t.c:1: x = 1 @ 2;"
    col = err.index("@")
    assert col == 13, col
    size = 12
    caret = " " * col + "^ invalid token"
    wcard = max(len(err), len(caret)) * cw(size) + 28
    ex = round(320 - wcard / 2, 1)
    a.box(ex, 200, round(wcard, 1), 58, "s fs", rx=8)
    code(a, ex + 14, 223, err, size)
    code(a, ex + 14, 244, caret, size)
    return a


# =================================================================== 02 expressions

def cc_expr():
    a = Art("c02", "1 + 2 * 3: tokens, the tree, and code that uses registers as a stack")
    # tokens
    for k, t in enumerate("1+2*3"):
        cell(a, 24 + k * 27, 127, 22, 26, t, "s fs", "t", 13, rx=5)
    a.line(166, 140, 196, 140, "m", arrow=True)
    # the tree; the * subtree sits deeper
    nodes = {"+": (276, 62), "1": (226, 134), "*": (326, 134), "2": (291, 206), "3": (361, 206)}
    a.box(262, 112, 128, 120, "a af", rx=18, dash=True)
    r = 15
    for p, c in (("+", "1"), ("+", "*"), ("*", "2"), ("*", "3")):
        (x1, y1), (x2, y2) = nodes[p], nodes[c]
        d = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        ux, uy = (x2 - x1) / d, (y2 - y1) / d
        a.line(round(x1 + ux * r, 1), round(y1 + uy * r, 1), round(x2 - ux * r, 1), round(y2 - uy * r, 1))
    for t, (x, y) in nodes.items():
        a.circle(x, y, r, "s f")
        a.text(x, y + 5, t, size=14, anchor="middle", weight=600, mono=True)
    a.text(326, 252, "binds tighter,", "ta", 11, "middle", 600)
    a.text(326, 267, "so it sits deeper", "ta", 11, "middle", 600)
    a.line(400, 140, 426, 140, "m", arrow=True)
    # the code, and the registers at its deepest point
    lines = ["li t0, 1", "li t1, 2", "li t2, 3", "mul t1, t1, t2", "add t0, t0, t1"]
    a.box(430, 82, 116, 116, "s fs", rx=8)
    for k, l in enumerate(lines):
        code(a, 442, 104 + k * 20, l, 11.5)
    for k, (reg, v) in enumerate((("t0", "1"), ("t1", "2"), ("t2", "3"))):
        cell(a, 576, 101 + k * 26, 40, 26, v, "s f", "t", 12, rx=0)
        a.text(568, 118 + k * 26, reg, "tm", 11, "end", mono=True)
    a.text(616, 202, "deepest point:", "tm", 10.5, "end")
    a.text(616, 216, "three values waiting", "tm", 10.5, "end")
    return a


# =================================================================== 03 statements and control flow

def cc_control():
    a = Art("c03", "A while loop is a label, a test, a branch out and a jump back")
    code(a, 24, 142, "while (i < n)", 12)
    code(a, 24, 162, "  i = i + 1;", 12)
    bx, bw = 214, 150
    blocks = [(50, ".L1", [("test: ", None, False), ("i < n", None, True)]),
              (126, None, [("body: ", None, False), ("i = i + 1", None, True)]),
              (214, ".L2", [("after the loop", None, False)])]
    for y, lab, parts in blocks:
        a.box(bx, y, bw, 36, "s f", rx=8)
        if lab:
            a.text(bx + 12, y + 23, lab, size=11.5, weight=700, mono=True)
        rich(a, bx + 50, y + 23, parts, 11.5)
    # true: fall through into the body
    a.line(244, 86, 244, 124, arrow=True)
    a.text(252, 110, "true: falls through", "tm", 10.5)
    # false: leave, down the right side
    a.path(f"M{bx + bw} 68 H392 V232 H{bx + bw + 2}", "s", arrow=True)
    a.text(400, 146, "bge", size=11.5, mono=True, weight=600)
    a.text(400, 162, "false: leave", "tm", 10.5)
    # the jump back, up the left side
    a.path(f"M{bx} 144 H186 V68 H{bx - 2}", "a", arrow=True)
    a.text(178, 110, "j .L1", "ta", 11.5, "end", 600, mono=True)
    # the assembly it becomes
    lines = [".L1:", "  bge t0, t1, .L2", "  ...body...", "  j .L1", ".L2:"]
    a.box(470, 96, 146, 110, "s fs", rx=8)
    for k, l in enumerate(lines):
        code(a, 482, 118 + k * 20, l, 11.5)
    return a


# =================================================================== 04 functions

def cc_functions():
    a = Art("c04", "The RISC-V stack frame, and the registers a call uses")
    regs = [("a0 - a7", "arguments 1 to 8"), ("a0", "the return value"), ("ra", "return address"),
            ("sp", "stack pointer"), ("s0", "frame pointer"), ("s0 - s11", "the callee saves"),
            ("t0 - t6", "the caller saves")]
    for k, (r, what) in enumerate(regs):
        y = 76 + k * 26
        a.text(24, y, r, size=11.5, weight=600, mono=True)
        a.text(96, y, what, "tm", 11)
    sx, sw = 300, 184
    cells = [(40, 44, "caller's frame", None, True), (84, 40, "arguments 9, 10, ...", "(on the stack)", True),
             (124, 28, "saved ra", "-8(s0)", False), (152, 28, "saved s0", "-16(s0)", False),
             (180, 42, "local variables", None, False), (222, 34, "temporaries", None, False)]
    for y, h, name, sub, muted in cells:
        a.box(sx, y, sw, h, "m f" if muted else "s f", rx=0)
        tc = "tm" if muted else "t"
        if sub and muted:
            a.text(sx + sw / 2, y + h / 2 - 2, name, tc, 11, "middle")
            a.text(sx + sw / 2, y + h / 2 + 12, sub, tc, 10.5, "middle")
        elif sub:
            a.text(sx + 12, y + h / 2 + 4, name, tc, 11)
            a.text(sx + sw - 12, y + h / 2 + 4, sub, tc, 11, "end", mono=True)
        else:
            a.text(sx + sw / 2, y + h / 2 + 4, name, tc, 11, "middle")
    # the two pointers
    fp, sp = 124, 256
    a.line(256, fp, sx - 2, fp, "a", arrow=True)
    a.text(250, fp + 4, "s0 (fp)", "ta", 11.5, "end", 600, mono=True)
    a.line(256, sp, sx - 2, sp, "a", arrow=True)
    a.text(250, sp + 4, "sp", "ta", 11.5, "end", 600, mono=True)
    # this call's frame
    bx = sx + sw + 10
    a.path(f"M{bx - 4} {fp + 2} H{bx + 4} V{sp - 2} H{bx - 4}", "a")
    a.text(bx + 14, 186, "this call's", "ta", 12, weight=700)
    a.text(bx + 14, 201, "frame", "ta", 12, weight=700)
    # which way it grows
    a.line(bx, 46, bx, 104, "m", arrow=True)
    a.text(bx + 10, 70, "grows toward", "tm", 10.5)
    a.text(bx + 10, 84, "lower addresses", "tm", 10.5)
    return a


# =================================================================== 05 names, scopes and storage

def cc_scopes():
    a = Art("c05", "Three variables called x, and where each one lives")
    src = ["int x = 1;", "int f() {", "  int x = 2;", "  { int x = 3; }", "  static int n;", "}"]
    for k, l in enumerate(src):
        code(a, 24, 96 + k * 20, l, 11.5)
    # three scopes, one inside another
    sc = [(156, 36, 264, 230, "file scope: ", ["x", "f"]), (172, 72, 232, 178, "function scope: ", ["x", "n"]),
          (188, 108, 200, 64, "block scope: ", ["x"])]
    for x, y, w, h, *_ in sc:
        a.box(x, y, w, h, "s f", rx=12)
    for x, y, w, h, lab, names in sc:
        parts = [(lab, "t", False)]
        for k, nm in enumerate(names):
            parts.append((nm, "t", True))
            if k < len(names) - 1:
                parts.append((", ", "t", False))
        rich(a, x + 12, y + 20, parts, 11.5, weight=600)
    # where each name sits in its label, measured in the page (Figtree 600 and Geist Mono at 11.5px):
    # the centre of the file scope's x and the function scope's x, the right end of n and the block's x
    name_x = {"file x": 228.0, "fn x": 271.9, "fn n": 287.8, "block x": 275.6}
    # storage
    stx, stw = 466, 150
    regions = [(".data", 40, 44, ["x = 1"]), (".bss", 96, 44, ["n"]), ("stack", 152, 86, ["x = 2", "x = 3"])]
    centre = {}
    for name, y, h, items in regions:
        a.box(stx, y, stw, h, "s f", rx=8)
        a.text(stx + stw - 12, y + 26, name, size=12, anchor="end", weight=700, mono=True)
        for k, it in enumerate(items):
            cy = y + 10 + k * 36
            cell(a, stx + 10, cy, 64, 24, it, "a af" if it == "n" else "s fs", "ta" if it == "n" else "t", 11.5)
            centre[it] = cy + 12
    # thin lines from each name to its storage; n's is the accent
    fy, fny, by = 56, 92, 128
    a.path(f"M{name_x['file x']} {fy + 4} V{fy + 10} H430 L{stx + 8} {centre['x = 1']}", "m", arrow=True)
    a.path(f"M{name_x['fn x']} {fny + 4} V{fny + 10} H436 L{stx + 8} {centre['x = 2']}", "m", arrow=True)
    a.path(f"M{name_x['fn n'] + 5} {fny - 4} H426 L{stx + 8} {centre['n']}", "a", arrow=True)
    a.path(f"M{name_x['block x'] + 5} {by - 4} H420 L{stx + 8} {centre['x = 3']}", "m", arrow=True)
    # lookup walks outward: from inside the block, out through the function, to the file
    a.line(206, 146, 206, 256, "a", arrow=True)
    a.text(216, 214, "lookup walks outward", "ta", 11, weight=600)
    a.text(stx + stw, 258, "n: function scope, but it lives", "tm", 10.5, "end")
    a.text(stx + stw, 273, "as long as the program", "tm", 10.5, "end")
    return a


# =================================================================== 06 types and pointers

def cc_types():
    a = Art("c06", "p + 1 moves four bytes: the type on each node decides the code")
    rich(a, 24, 34, [("given ", "tm", False), ("int *p", "t", True)], 12)
    nodes = {"+": (130, 76), "p": (70, 146), "1": (190, 146)}
    r = 15
    for c in ("p", "1"):
        (x1, y1), (x2, y2) = nodes["+"], nodes[c]
        d = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        ux, uy = (x2 - x1) / d, (y2 - y1) / d
        a.line(round(x1 + ux * r, 1), round(y1 + uy * r, 1), round(x2 - ux * r, 1), round(y2 - uy * r, 1))
    for t, (x, y) in nodes.items():
        a.circle(x, y, r, "s f")
        a.text(x, y + 5, t, size=14, anchor="middle", weight=600, mono=True)
    # the type on each node
    def tchip(x, y, s):
        w = len(s) * cw(10.5) + 16
        a.box(round(x, 1), y, round(w, 1), 20, "a af", rx=10)
        a.text(round(x + w / 2, 1), y + 14, s, "ta", 10.5, "middle", 600, mono=True)
        return w
    tchip(152, 66, "+ : int *")
    w = len("p : int *") * cw(10.5) + 16
    tchip(70 - w / 2, 170, "p : int *")
    tchip(212, 136, "1 : int")
    # the 1 is scaled
    a.line(190, 163, 190, 202, arrow=True)
    cell(a, 160, 204, 60, 26, "1 * 4", "s fs", "t", 12, rx=6)
    rich(a, 200, 188, [("scaled by ", "tm", False), ("sizeof(int)", "tm", True)], 10.5)
    # memory
    base, size = 0x1000, 4
    addrs = [base + k * size for k in range(3)]
    assert [f"0x{v:04x}" for v in addrs] == ["0x1000", "0x1004", "0x1008"]
    mx, mw, my = 378, 76, 104
    for k, v in enumerate(addrs):
        cell(a, mx + k * mw, my, mw, 36, "int", "s f", "t", 12, rx=0, mono=False)
        a.text(mx + k * mw + mw / 2, my - 10, f"0x{v:04x}", "tm", 10.5, "middle", mono=True)
    for k, lab, cls in ((0, "p", "s"), (1, "p + 1", "a")):
        x = mx + k * mw + mw / 2
        a.line(x, my + 72, x, my + 40, cls, arrow=True)
        a.text(x, my + 88, lab, "ta" if cls == "a" else "t", 12, "middle", 600, mono=True)
    # sizes
    x = 24
    for s in ("char 1", "short 2", "int 4", "long 8", "pointer 8"):
        w = len(s) * cw(11) + 18
        cell(a, x, 246, round(w, 1), 24, s, "s f", "t", 11, rx=12)
        x += w + 10
    a.text(round(x + 4, 1), 262, "bytes, on 64-bit RISC-V", "tm", 10.5)
    return a


# =================================================================== 07 arrays, strings and structs

def layout(fields):
    """Offsets by the rule: align each field to its size, pad the end to the largest alignment."""
    off, out = 0, []
    for name, size in fields:
        off = (off + size - 1) // size * size
        out.append((name, off, size))
        off += size
    align = max(s for _, s in fields)
    return out, (off + align - 1) // align * align, align


def cc_structs():
    a = Art("c07", "A struct is offsets, an array is a multiply: where every byte goes")
    code(a, 24, 34, "struct S { char c; int i; char d; long l; };", 11.5)
    placed, size, align = layout([("c", 1), ("i", 4), ("d", 1), ("l", 8)])
    assert [(n, o) for n, o, _ in placed] == [("c", 0), ("i", 4), ("d", 8), ("l", 16)] and (size, align) == (24, 8)
    pads, at = [], 0
    for _, o, s in placed:
        if o > at:
            pads.append((at, o - at))
        at = o + s
    if size > at:
        pads.append((at, size - at))
    assert pads == [(1, 3), (9, 7)]
    gx, cwid, rh, ry = 64, 32, 30, [56, 90, 124]

    def run(off, n, cls, label, tcls, dash):
        row, col = divmod(off, 8)
        assert col + n <= 8
        x, y = gx + col * cwid, ry[row]
        a.box(x, y, n * cwid, rh, cls, rx=3, dash=dash)
        for k in range(1, n):
            bx = x + k * cwid
            a.line(bx, y + 1, bx, y + 6, "m")
            a.line(bx, y + rh - 6, bx, y + rh - 1, "m")
        a.text(x + n * cwid / 2, y + 20, label, tcls, 12 if tcls == "t" else 11, "middle",
               700 if tcls == "t" else 600, mono=tcls == "t")
    for name, o, s in placed:
        run(o, s, "s fs", name, "t", False)
    for o, n in pads:
        run(o, n, "m", "pad", "ta", True)
    for k, y in enumerate(ry):
        a.text(gx - 10, y + 19, str(8 * k), "tm", 10.5, "end", mono=True)
    code(a, 352, 96, f"sizeof(struct S) = {size}", 11.5)
    i_off = dict((n, o) for n, o, _ in placed)["i"]
    code(a, 352, 124, f"s.i  is  {i_off} bytes past &s", 11.5, "ta", weight=600)
    # an array: a[2] is two ints past a
    a.text(24, 219, "int a[4]", size=11.5, mono=True, weight=600)
    ax, aw = 104, 40
    for k in range(4):
        a.box(ax + k * aw, 200, aw, 30, "s fs" if k == 2 else "s f", rx=0)
        a.text(ax + k * aw + aw / 2, 247, f"a[{k}]", "t" if k == 2 else "tm", 10.5, "middle",
               700 if k == 2 else None, mono=True)
    code(a, 290, 219, "a[2]  is  at  a + 2 * 4", 11.5)
    return a


# =================================================================== 08 the preprocessor

def cc_preproc():
    a = Art("c08", "Tokens in, tokens out: the parser never sees a #")
    sz = 11
    c = cw(sz)
    src = ['#define SQ(x) ((x) * (x))', '#include "defs.h"', 'int n = SQ(a + 1);']
    sx, sy = 36, 92
    a.box(24, 70, 192, 74, "s fs", rx=8)
    use = src[2].index("SQ(a + 1)")
    a.box(round(sx + use * c - 3, 1), sy + 40 - 12, round(9 * c + 6, 1), 17, "af", rx=3)
    for k, l in enumerate(src):
        sp = [(use, use + 9, "ta")] if k == 2 else []
        code(a, sx, sy + k * 20, l, sz, spans=sp, weight=600 if k == 2 else None)
    # defs.h, read in at the include line
    a.box(120, 182, 96, 52, "s f", rx=8)
    a.text(132, 200, "defs.h", size=11, weight=700, mono=True)
    code(a, 132, 220, "int a;", sz)
    inc_end = sx + len(src[1]) * c
    a.path(f"M190 180 V{sy + 16} H{round(inc_end + 8, 1)}", "s", arrow=True)
    # the preprocessor
    a.line(218, 107, 244, 107, arrow=True)
    a.box(246, 87, 100, 40, "s f", rx=8)
    a.text(296, 111, "preprocessor", size=12, anchor="middle", weight=700)
    a.line(348, 107, 374, 107, arrow=True)
    out = ["int a;", "int n = ((a + 1) * (a + 1));"]
    ox, oy = 390, 102
    a.box(376, 80, 240, 54, "s fs", rx=8)
    exp = out[1].index("((a + 1) * (a + 1))")
    a.box(round(ox + exp * c - 3, 1), oy + 20 - 12, round(19 * c + 6, 1), 17, "af", rx=3)
    for k, l in enumerate(out):
        sp = [(exp, exp + 19, "ta")] if k == 1 else []
        code(a, ox, oy + k * 20, l, sz, spans=sp, weight=600 if k == 1 else None)
    a.text(296, 252, "a second, smaller language", "tm", 11, "middle")
    a.text(296, 267, "that runs before the parser", "tm", 11, "middle")
    return a


# =================================================================== 09 real programs

def cc_real():
    a = Art("c09", "The compiler compiles itself: three stages, and the last two must match")
    # what it is held to
    chips = [("a published test suite", False), ("xv6's user programs", False), ("itself", True)]
    ws = [round(len(s) * 0.56 * 11 + 20) for s, _ in chips]
    x = (640 - sum(ws) - 12 * (len(ws) - 1)) / 2
    for (s, hot), w in zip(chips, ws):
        chip(a, x + w / 2, 30, s, "a af" if hot else "s f", "ta" if hot else "t", 11, False,
             weight=600 if hot else None, w=w)
        x += w + 12
    ry, rh = 112, 56
    mid = ry + rh / 2
    # cc.c, shown once, feeding every compile
    page(a, 24, mid - 24, 38, 48, "s f", fold=9)
    a.text(43, mid + 4, "cc.c", size=10.5, anchor="middle", weight=700, mono=True)
    a.line(64, mid, 80, mid, arrow=True)
    cell(a, 82, mid - 16, 40, 32, "gcc", "s f", "t", 12, rx=8)
    a.line(124, mid, 140, mid, arrow=True)
    s1 = (142, 76)
    a.box(s1[0], ry, s1[1], rh, "s f", rx=8)
    s1c = s1[0] + s1[1] / 2
    a.text(s1c, ry + 19, "stage 1:", size=11.5, anchor="middle", weight=700)
    a.text(s1c, ry + 34, "runs on your", "tm", 10.5, "middle")
    a.text(s1c, ry + 48, "machine", "tm", 10.5, "middle")
    for x1, x2 in ((220, 298), (464, 546)):
        a.line(x1, mid, x2, mid, arrow=True)
        rich(a, (x1 + x2) / 2 - 3, mid - 8, [("compiles ", "tm", False), ("cc.c", "tm", True)], 10, "middle")
    cw_ = 64
    cards = (300, 548)
    for x, k in zip(cards, (2, 3)):
        a.box(x, mid - 24, cw_, 48, "s fs", rx=6)
        a.text(x + cw_ / 2, mid - 4, f"stage {k}", size=11.5, anchor="middle", weight=700)
        a.text(x + cw_ / 2, mid + 11, "assembly", "tm", 10.5, "middle")
    a.line(366, mid, 378, mid, arrow=True)
    xv = (380, 82)                       # stage 2, run on the bare machine in QEMU
    xvc = xv[0] + xv[1] / 2
    a.box(xv[0], ry + 4, xv[1], rh - 8, "s f", rx=8)
    a.text(xvc, mid - 3, "runs on the", size=11, anchor="middle", weight=700)
    a.text(xvc, mid + 12, "bare machine", size=11, anchor="middle", weight=700)
    # the bus: cc.c into the two compiles after gcc's
    bus = 84
    a.path(f"M43 {mid - 26} V{bus} H{xvc} V{ry + 2}", "m", arrow=True)
    a.line(s1c, bus, s1c, ry - 2, "m", arrow=True)
    # the same bytes
    ey = 214
    c2, c3 = cards[0] + cw_ / 2, cards[1] + cw_ / 2
    em = (c2 + c3) / 2
    a.path(f"M{c2} {mid + 26} V{ey} H{c3} V{mid + 26}", "a")
    a.circle(em, ey, 11, "a f")
    a.path(f"M{em - 5.5} {ey - 3} H{em + 5.5} M{em - 5.5} {ey + 3} H{em + 5.5}", "a")
    a.text(em, ey + 32, "the same bytes", "ta", 12, "middle", 700)
    return a


# =================================================================== 10 an optimising back end

def linear_scan(ranges, regs):
    """Poletto and Sarkar's linear scan: walk the ranges by start; a register is free again when
    its range's end is <= the new start; take the lowest free one."""
    active, free, got = [], list(regs), {}
    for name, (s, e) in sorted(ranges.items(), key=lambda kv: kv[1][0]):
        for other in [o for o in active if ranges[o][1] <= s]:
            active.remove(other)
            free.append(got[other])
        free.sort(key=regs.index)
        assert free, f"{name} would spill"
        got[name] = free.pop(0)
        active.append(name)
    return got


def cc_backend():
    a = Art("c10", "A control flow graph, and live ranges packed into registers")
    bx, bw = 60, 170
    cell(a, 100, 26, 80, 24, "entry", "s f", "t", 11.5, rx=8, weight=700, mono=False)
    for y, name, lines in ((72, "test", ["v1 = i < n", "br v1, body, exit"]), (154, "body", ["v2 = i + 1", "i = v2"])):
        a.box(bx, y, bw, 60, "s f", rx=8)
        a.text(bx + 12, y + 18, name, size=11.5, weight=700)
        for k, l in enumerate(lines):
            code(a, bx + 12, y + 35 + k * 16, l, 11)
    cell(a, 100, 242, 80, 24, "exit", "s f", "t", 11.5, rx=8, weight=700, mono=False)
    a.line(140, 50, 140, 70, arrow=True)
    a.line(140, 132, 140, 152, arrow=True)
    a.path(f"M{bx} 184 H38 V102 H{bx - 2}", "s", arrow=True)
    a.path(f"M{bx + bw} 102 H256 V254 H182", "s", arrow=True)
    # live ranges, and the registers linear scan gives them
    ranges = {"v1": (0, 3), "v2": (1, 4), "v3": (2, 6), "v4": (4, 8), "v5": (6, 9)}
    got = linear_scan(ranges, ["t0", "t1", "t2"])
    assert got == {"v1": "t0", "v2": "t1", "v3": "t2", "v4": "t0", "v5": "t1"}, got
    X = lambda t: 384 + t * 20
    a.text(354, 34, "live ranges: five values, three registers", "tm", 11)
    for k, (v, (s, e)) in enumerate(ranges.items()):
        y = 64 + k * 28
        hot = v == "v4"
        a.text(354, y + 4, v, size=11.5, weight=600, mono=True)
        a.box(X(s), y - 7, X(e) - X(s), 14, "a af" if hot else "s fs", rx=3)
        a.text(X(e) + 8, y + 4, got[v], "ta" if hot else "t", 11.5, weight=700 if hot else 600, mono=True)
    ay = 200
    a.line(X(0), ay, X(9), ay, "m")
    for t in range(10):
        a.line(X(t), ay, X(t), ay + 4, "m")
        a.text(X(t), ay + 16, str(t), "tm", 10, "middle", mono=True)
    a.text(X(4.5), ay + 34, "instructions", "tm", 10.5, "middle")
    a.text(X(4.5), ay + 62, "v1 is dead: t0 is free again", "ta", 11.5, "middle", 600)
    return a


# =================================================================== 11 an assembler and a linker

def cc_asm():
    a = Art("c11", "One instruction as 32 bits, and a call whose address the linker fills in")
    code(a, 24, 34, "add a0, a0, a1", 13, weight=700)
    fields = [("funct7", 31, 25, 0b0000000, None), ("rs2", 24, 20, 11, "a1 = x11"), ("rs1", 19, 15, 10, "a0 = x10"),
              ("funct3", 14, 12, 0b000, None), ("rd", 11, 7, 10, None), ("opcode", 6, 0, 0b0110011, None)]
    word = 0
    for _, hi, lo, v, _ in fields:
        assert v < 1 << (hi - lo + 1)
        word |= v << lo
    assert word == 0x00b50533, hex(word)
    bit, x = 12, 24
    for name, hi, lo, v, note in fields:
        n = hi - lo + 1
        w = n * bit
        cx = x + w / 2
        a.box(x, 60, w, 28, "s fs", rx=0)
        a.text(cx, 79, format(v, f"0{n}b"), size=11.5, anchor="middle", mono=True)
        a.text(cx, 52, f"[{hi}:{lo}]", "tm", 10, "middle", mono=True)
        a.text(cx, 104, name, size=10.5, anchor="middle", mono=True)
        if note:
            a.text(cx, 119, note, "tm", 10, "middle", mono=True)
        x += w
    assert x == 24 + 32 * bit
    a.text(x + 16, 79, f"= 0x{word:08x}", size=13, weight=700, mono=True)
    # two object files, one program
    def ofile(y, name, content, hole):
        a.box(24, y, 150, 56, "s f", rx=8)
        a.text(36, y + 17, name, size=11, weight=700, mono=True)
        a.box(34, y + 24, 130, 24, "s fs", rx=4)
        a.text(42, y + 40, ".text", "tm", 10, mono=True)
        code(a, 80, y + 40, content, 11)
        if hole:
            cell(a, 127, y + 28, 32, 16, "????", "a af", "ta", 10, rx=3, dash=True, weight=700)
    ofile(146, "main.o", "call f", True)
    ofile(214, "f.o", "f:", False)
    call_at, fx = 0x80000000, 0x80000010     # the call is main's first instruction; f follows main
    dist = fx - call_at
    assert dist == 0x10, hex(dist)
    px = 234
    a.box(px, 146, 244, 112, "s f", rx=8)
    a.text(px + 12, 163, "prog", size=11, weight=700, mono=True)
    a.text(px + 48, 163, ".text", "tm", 10, mono=True)
    for k, (addr, content) in enumerate(((call_at, "call f"), (fx, "f:"))):
        y = 176 + k * 36
        a.text(px + 12, y + 18, f"0x{addr:08x}", "tm", 10, mono=True)
        a.box(px + 84, y, 150, 28, "s fs", rx=4)
        code(a, px + 92, y + 18, content, 11)
    cell(a, px + 140, 180, 48, 20, f"+0x{dist:x}", "a af", "ta", 10.5, rx=3, weight=700)
    a.line(176, 174, 232, 190, arrow=True)
    a.line(176, 242, 232, 226, arrow=True)
    a.text(494, 181, "relocation:", "ta", 11, weight=600)
    a.text(494, 196, "the linker writes", "ta", 11, weight=600)
    a.text(494, 211, "the distance to f", "ta", 11, weight=600)
    return a


# =================================================================== 12 a debugger's view

def cc_debug():
    a = Art("c12", "The line table: from an address back to a line of your source")
    src = ["1  int main() {", "2    int i = 6;", "3    i = i * 7;", "4    return i; }"]
    sy, sz = [92, 122, 152, 182], 12
    a.box(20, sy[2] - 16, 4 + len(src[2]) * cw(sz) + 10, 22, "af", rx=4)
    for k, l in enumerate(src):
        hot = k == 2
        code(a, 24, sy[k], l, sz, "ta" if hot else "t", spans=[] if hot else [(0, 1, "tm")],
             weight=700 if hot else None)
    # line 1 is the prologue, 4 instructions shown as one muted row; then 2, 3 and 2 for lines 2 to 4
    groups = [(1, 4, None), (2, 2, ["li t0, 6", "sw t0, -20(s0)"]),
              (3, 3, ["li t1, 7", "mulw t0, t0, t1", "sw t0, -20(s0)"]), (4, 2, ["lw a0, -20(s0)", "j .L.return"])]
    n = sum(c for _, c, _ in groups)
    addrs = [0x80000000 + 4 * k for k in range(n)]
    firsts = [addrs[sum(c for _, c, _ in groups[:g])] for g in range(len(groups))]
    assert firsts == [0x80000000, 0x80000010, 0x80000018, 0x80000024] and addrs[-1] == 0x80000028, \
        [hex(v) for v in firsts + addrs[-1:]]
    ax, ix, y, k = 300, 386, 50, 0
    for line, count, ins in groups:
        hot = line == 3
        top = y - 14
        if ins is None:
            a.text(ax, y, f"0x{addrs[k]:08x}", "tm", 11, mono=True)
            a.text(ix, y, f"prologue: {count} instructions", "tm", 11)
            rows = 1
        else:
            assert len(ins) == count
            rows = count
            if hot:
                a.box(ax - 6, top + 2, 186, len(ins) * 20 - 2, "af", rx=4)
            for j, i_ in enumerate(ins):
                yy = y + j * 20
                a.text(ax, yy, f"0x{addrs[k + j]:08x}", "ta" if hot else "tm", 11, mono=True)
                code(a, ix, yy, i_, 11, "ta" if hot else "t", weight=700 if hot else None)
                if hot and j == 0:
                    a.line(526, yy - 4, 492, yy - 4, "a", arrow=True)
                    a.text(534, yy, "break t.c:3", "ta", 11, weight=700, mono=True)
                    a.text(534, yy + 15, "stops here", "ta", 11, weight=600)
        k += count
        y += rows * 20
        bot = y - 20 + 6
        cls = "a" if hot else ("m" if ins is None else "s")
        a.path(f"M{ax - 10} {top + 4} H{ax - 16} V{bot} H{ax - 10}", cls)
        mid = (top + 4 + bot) / 2
        srow = sy[line - 1] - 4
        a.line(round(24 + len(src[line - 1]) * cw(sz) + 12, 1), srow, ax - 18, mid, cls)
        y += 14
    return a


# =================================================================== 13 beyond call and return

def cc_beyond():
    a = Art("c13", "longjmp drops frames; a coroutine switch swaps stacks")
    a.line(318, 30, 318, 270, "m")
    a.text(24, 36, "longjmp", size=12.5, weight=700, mono=True)
    sx, sw = 120, 100
    frames = [("f", 70, False), ("g", 112, True), ("h", 154, True)]
    for name, y, dropped in frames:
        a.box(sx, y, sw, 42, "m f" if dropped else "s f", rx=0, dash=dropped)
        a.text(sx + sw / 2, y + 26, name, "tm" if dropped else "t", 13, "middle", 700, mono=True)
    a.text(sx + sw / 2, 216, "h: the newest", "tm", 10.5, "middle")
    a.text(sx - 30, 95, "setjmp", size=11.5, anchor="end", weight=600, mono=True)
    a.line(sx - 26, 91, sx - 4, 91, "s", arrow=True)
    a.path(f"M{sx - 8} 116 H{sx - 14} V192 H{sx - 8}", "m")
    a.text(sx - 22, 158, "dropped", "tm", 11, "end")
    a.path(f"M{sx + sw} 175 H{sx + sw + 34} V91 H{sx + sw + 2}", "a", arrow=True)
    # coroutines: a stack each, and the switch between them
    a.text(342, 36, "coroutines", size=12.5, weight=700)
    for name, x in (("A", 342), ("B", 562)):
        a.text(x + 27, 72, name, size=13, anchor="middle", weight=700, mono=True)
        for k in range(2):
            a.box(x, 82 + k * 32, 54, 32, "s f", rx=0)
        a.line(x + 27, 176, x + 27, 150, arrow=True)
        a.text(x + 27, 191, "sp", size=11.5, anchor="middle", weight=600, mono=True)
    a.box(418, 90, 124, 52, "a af", rx=8)
    a.text(480, 111, "switch", "ta", 12, "middle", 700)
    code(a, round(480 - 16 * cw(10.5) / 2, 1), 130, "ra  sp  s0 - s11", 10.5, "ta", weight=600)
    a.line(398, 116, 416, 116, arrow=True)
    a.line(544, 116, 560, 116, arrow=True)
    a.text(480, 226, "the registers the callee must save,", "tm", 10.5, "middle")
    a.text(480, 241, "as xv6's swtch saves them", "tm", 10.5, "middle")
    return a


# =================================================================== icons and the table

ICON = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="none" stroke="currentColor" '
        'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">{}</svg>\n')

MODULES = {
    "00": (cc_smallest, '<circle cx="4.5" cy="10" r="2.25"/><path d="M8.5 10h5.5M12 8l2 2-2 2"/><path d="M17 5v10"/>'),
    "01": (cc_tokens, '<rect x="1.75" y="7" width="4" height="6" rx="1.5"/><rect x="8" y="7" width="5.5" height="6" rx="1.5"/>'
                      '<rect x="15.75" y="7" width="2.5" height="6" rx="1.25"/>'),
    "02": (cc_expr, '<circle cx="10" cy="4.5" r="2"/><circle cx="4.5" cy="15.5" r="2"/><circle cx="15.5" cy="15.5" r="2"/>'
                    '<path d="M8.9 6.2l-3.3 7.6M11.1 6.2l3.3 7.6"/>'),
    "03": (cc_control, '<path d="M10 4.5h5.5v11h-11v-11H7.5"/><path d="M5.5 2.5l2 2-2 2"/>'),
    "04": (cc_functions, '<rect x="2.5" y="2.75" width="9" height="3.5" rx="1"/><rect x="2.5" y="8.25" width="9" height="3.5" rx="1"/>'
                         '<rect x="2.5" y="13.75" width="9" height="3.5" rx="1"/><path d="M16 3v13.5M13.75 14.25L16 16.5l2.25-2.25"/>'),
    "05": (cc_scopes, '<rect x="2.5" y="2.5" width="15" height="15" rx="3"/><rect x="5.5" y="5.5" width="9" height="9" rx="2"/>'
                      '<rect x="8.5" y="8.5" width="3" height="3" rx="1"/>'),
    "06": (cc_types, '<path d="M5.5 2.5v6M2.9 4l5.2 3M2.9 7l5.2-3"/><path d="M5.5 11v4h5"/><path d="M9 13l2 2-2 2"/>'
                     '<rect x="12.5" y="12" width="5.5" height="6" rx="1"/>'),
    "07": (cc_structs, '<rect x="2" y="6" width="16" height="8" rx="1.5"/><path d="M5.5 6v8M13 6v8"/>'),
    "08": (cc_preproc, '<path d="M8 3L6.5 17M14 3l-1.5 14M3.5 7.5h13.5M3 12.5h13.5"/>'),
    "09": (cc_real, '<rect x="7.5" y="7.5" width="5" height="5" rx="1"/>'
                    '<path d="M13.25 15.63A6.5 6.5 0 1 1 16.5 10"/><path d="M14.5 8l2 2 2-2"/>'),
    "10": (cc_backend, '<circle cx="10" cy="3.5" r="1.75"/><circle cx="3.5" cy="10" r="1.75"/><circle cx="16.5" cy="10" r="1.75"/>'
                       '<circle cx="10" cy="16.5" r="1.75"/><path d="M8.75 4.75l-4 4M11.25 4.75l4 4M4.75 11.25l4 4M15.25 11.25l-4 4"/>'),
    "11": (cc_asm, '<rect x="1.75" y="6.5" width="10" height="7" rx="3.5"/><rect x="8.25" y="6.5" width="10" height="7" rx="3.5"/>'),
    "12": (cc_debug, '<circle cx="4" cy="10" r="2"/><path d="M9 5.5h8M9 10h8M9 14.5h8"/>'),
    "13": (cc_beyond, '<path d="M3 3v14M17 3v14"/><path d="M6.5 6.5l7 7M13.5 6.5l-7 7"/>'
                      '<path d="M13.5 10.5v3h-3M6.5 10.5v3h3"/>'),
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
