"""Art for the language outline (outlines/lang.md, id lang), in the same visual language as
cc_art.py, research_art.py and outline_art.py.

Writes, under outlines/lang/:
    art.svg         280x160, the track's picture on its home page card (one .draw path moves on hover)
    icon.svg        20x20 currentColor line icon for the top bar
    NN/cover.svg    640x300 teaching diagram for module NN (01 to 17, one per chapter of the book)
    NN/icon.svg     20x20 currentColor line icon for module NN

The language on the covers is the track's own small language (working name Mote). The diagrams
are the course's own: nothing on them is taken from the book the track is read beside.

Covers style themselves only through the .art classes in harness/web/app.css:
    s m a        stroke: foreground, muted, accent
    f fs af fa   fill: page, code background, accent-soft, accent
    t tm ta      text fill: foreground, muted, accent      mono: monospace
One accent idea a cover: the accent classes mark the single thing the cover is about.

Code is set on a monospace grid: a line of code is split into runs of text, and each run is
placed at its own column (x = left + column * 0.6em, Geist Mono's advance), so indentation and
double spaces survive SVG's whitespace collapsing and an arrow can start at a given column.

Computed here, and asserted, so a typo stops the script instead of reaching a cover:
    01  6 * 7 evaluated, and the four stack instructions run on a stack machine: both 42
    05  the four instruction addresses from 0x1000 in steps of 4; the registers after the first
        two instructions (pc 0x1008, t0 6, t1 7); 42 after mul, and its eight bits 00101010
    07  the one constraint unified: 'a := int, so inc : int -> int
    08  the set the roots reach over the pointer edges: {A, B, C, D}
    12  the search: parent(X, B) tried against each fact, then parent(B, carol): one yes, X = alice
    13  both schedules run on a counter that starts at 5: interleaved ends at 6, locked at 7
    14  the pattern run with Python's re over the three log lines: {"disk": 2}
    15  lib.o placed after main.o's 0x40 bytes: 0x1040
    16  the bytecode run: the stack after each instruction, [42] after MUL, and 42 written
    17  value numbering over the three instructions: the table and the two lines it keeps

The Art class is the one from cc_art.py, repeated so this file stands alone.

    python3 art/outlines/lang_art.py [NN ...]
        write every file (or only modules NN), then check each one is ASCII and survives
        harness/web/art.py's sanitizer unchanged
"""
import html
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "outlines", "lang")
SW = 'stroke-width="1.5"'
EM = 0.6            # the monospace advance, in em (Geist Mono, SF Mono, Menlo)
SANS = 0.56         # a generous average advance for Figtree, in em, to size pills around sans text


def esc(s):
    return html.escape(s, quote=True)


class Art:
    def __init__(self, key, title, h=300):
        self.key, self.title, self.out, self.h = key, title, [], h

    def add(self, s):
        self.out.append(s)

    def box(self, x, y, w, h, cls="s f", rx=10, dash=False):
        d = ' stroke-dasharray="4 4"' if dash else ""
        self.add(f'<rect class="{cls}" x="{r1(x)}" y="{r1(y)}" width="{r1(w)}" height="{r1(h)}" rx="{r1(rx)}" {SW}{d}/>')

    def text(self, x, y, s, cls="t", size=12, anchor="start", weight=None, mono=False):
        assert size >= 10, (self.key, s, size)
        c = cls + (" mono" if mono else "")
        wt = f' font-weight="{weight}"' if weight else ""
        a = f' text-anchor="{anchor}"' if anchor != "start" else ""
        self.add(f'<text class="{c}" x="{r1(x)}" y="{r1(y)}" font-size="{size}"{wt}{a}>{esc(s)}</text>')

    def marker(self, cls):
        return {"a": "aa", "m": "am"}.get(cls.split()[0], "ah")

    def line(self, x1, y1, x2, y2, cls="s", arrow=False, dash=False):
        m = f' marker-end="url(#{self.key}-{self.marker(cls)})"' if arrow else ""
        d = ' stroke-dasharray="4 4"' if dash else ""
        self.add(f'<line class="{cls}" x1="{r1(x1)}" y1="{r1(y1)}" x2="{r1(x2)}" y2="{r1(y2)}" {SW} '
                 f'stroke-linecap="round"{m}{d}/>')

    def path(self, d, cls="s", arrow=False, dash=False):
        m = f' marker-end="url(#{self.key}-{self.marker(cls)})"' if arrow else ""
        da = ' stroke-dasharray="4 4"' if dash else ""
        self.add(f'<path class="{cls}" d="{d}" {SW} stroke-linecap="round" stroke-linejoin="round"{m}{da}/>')

    def circle(self, cx, cy, r, cls="s f"):
        self.add(f'<circle class="{cls}" cx="{r1(cx)}" cy="{r1(cy)}" r="{r1(r)}" {SW}/>')

    def svg(self):
        def mk(name, cls):
            return (f'<marker id="{self.key}-{name}" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" '
                    f'markerHeight="7" orient="auto-start-reverse"><path class="{cls}" d="M1 1.5L8.5 5L1 8.5" {SW} '
                    f'stroke-linecap="round" stroke-linejoin="round"/></marker>')
        defs = f'<defs>{mk("ah", "s")}{mk("aa", "a")}{mk("am", "m")}</defs>'
        body = "\n".join(self.out)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 {self.h}" fill="none">\n'
                f'<title>{esc(self.title)}</title>\n{defs}\n{body}\n</svg>\n')


def r1(v):
    """A coordinate as short text: 12, 12.5, 12.35 (no float noise)."""
    v = round(float(v), 2)
    return str(int(v)) if v == int(v) else f"{v:g}"


def cw(size):
    return EM * size


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
    w = cw(size)
    wt = f' font-weight="{weight}"' if weight else ""
    assert size >= 10
    if len(runs) == 1 and runs[0][0] == 0:
        a.add(f'<text class="{runs[0][2]} mono" x="{r1(x)}" y="{r1(y)}" font-size="{size}"{wt}>{esc(runs[0][1])}</text>')
        return
    spans_out = "".join(
        f'<tspan x="{r1(x + c * w)}"{"" if k == cls else f" class={chr(34)}{k}{chr(34)}"}>{esc(t)}</tspan>'
        for c, t, k in runs)
    a.add(f'<text class="{cls} mono" x="{r1(x)}" y="{r1(y)}" font-size="{size}"{wt}>{spans_out}</text>')


def col(x, k, size):
    """The x of column k (its left edge) of code set at x in `size`."""
    return x + k * cw(size)


def rich(a, x, y, parts, size=11, anchor="start", weight=None, cls="t"):
    """Text whose parts flow one after another: parts is a list of (text, class, mono)."""
    assert size >= 10
    wt = f' font-weight="{weight}"' if weight else ""
    an = f' text-anchor="{anchor}"' if anchor != "start" else ""
    inner = ""
    for t, c, mono in parts:
        k = (c or cls) + (" mono" if mono else "")
        inner += f'<tspan class="{k}">{esc(t)}</tspan>'
    a.add(f'<text class="{cls}" x="{r1(x)}" y="{r1(y)}" font-size="{size}"{wt}{an}>{inner}</text>')


def pill(a, cx, cy, s, cls="s f", tcls="t", size=12, mono=True, h=24, weight=None, w=None, dash=False, rx=None):
    """A box centred on (cx, cy) around one label, its width from the text (monospace exact, sans
    estimated). Returns its bounds (x0, y0, x1, y1)."""
    w = w or max(h, round(len(s) * (EM if mono else SANS) * size + 18))
    a.box(cx - w / 2, cy - h / 2, w, h, cls, rx=h / 2 if rx is None else rx, dash=dash)
    a.text(cx, cy + size * 0.35, s, tcls, size, "middle", weight, mono)
    return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


def centre(b):
    return (b[0] + b[2]) / 2, (b[1] + b[3]) / 2


def towards(b, px, py, gap=2):
    """Where the segment from the centre of box b toward (px, py) leaves b, `gap` beyond its edge."""
    cx, cy = centre(b)
    dx, dy = px - cx, py - cy
    hw, hh = (b[2] - b[0]) / 2 + gap, (b[3] - b[1]) / 2 + gap
    t = min(hw / abs(dx) if dx else 1e9, hh / abs(dy) if dy else 1e9)
    return cx + dx * t, cy + dy * t


def join(a, b1, b2, cls="s", arrow=False, gap=2):
    """A straight line between two boxes, from edge to edge."""
    (x1, y1), (x2, y2) = towards(b1, *centre(b2), gap), towards(b2, *centre(b1), gap + (1 if arrow else 0))
    a.line(x1, y1, x2, y2, cls, arrow)


def page(a, x, y, w, h, cls="s f", dash=False, fold=9):
    """A file: a rectangle with its top right corner folded."""
    a.path(f"M{r1(x)} {r1(y)} H{r1(x + w - fold)} L{r1(x + w)} {r1(y + fold)} V{r1(y + h)} H{r1(x)} Z", cls, dash=dash)
    a.path(f"M{r1(x + w - fold)} {r1(y)} V{r1(y + fold)} H{r1(x + w)}", cls.split()[0], dash=dash)


def cycle(a, cx, cy, R, labels, size=11.5):
    """Three steps on a circle, clockwise from the top, each arc an arrow to the next."""
    angles = (-90, 30, 150)

    def at(d):
        return cx + R * math.cos(math.radians(d)), cy + R * math.sin(math.radians(d))
    boxes = [pill(a, *at(d), lab, "s f", "t", size, mono=False, h=24, weight=600) for lab, d in zip(labels, angles)]

    def inside(p, b, pad=5):
        return b[0] - pad <= p[0] <= b[2] + pad and b[1] - pad <= p[1] <= b[3] + pad
    for i in range(3):
        s, e = angles[i], angles[(i + 1) % 3] + (360 if i == 2 else 0)
        while inside(at(s), boxes[i]):
            s += 0.5
        while inside(at(e), boxes[(i + 1) % 3]):
            e -= 0.5
        (x1, y1), (x2, y2) = at(s), at(e)
        a.path(f"M{r1(x1)} {r1(y1)} A{R} {R} 0 0 1 {r1(x2)} {r1(y2)}", "s", arrow=True)
    return boxes


def stack_machine(prog):
    """Run stack code (push N, mul, write): the stack after each instruction, and what it wrote."""
    st, states, out = [], [], []
    for ins in prog:
        op, *arg = ins.lower().split()
        if op == "push":
            st.append(int(arg[0]))
        elif op == "mul":
            y, x = st.pop(), st.pop()
            st.append(x * y)
        elif op == "write":
            out.append(st.pop())
        else:
            raise ValueError(ins)
        states.append(list(st))
    return states, out


# =================================================================== the track's own pair

def track_art():
    """280x160: an open book, a terminal; the one accent path runs from a line of the book into the prompt."""
    size = 11.5
    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 280 160" fill="none">']
    # the book: two pages meeting at the spine, a few lines on each
    out.append('<path class="s f" d="M66 44C52 36 30 34 10 38V122C30 118 52 120 66 128Z" stroke-width="1.5" '
               'stroke-linejoin="round"/>')
    out.append('<path class="s f" d="M66 44C80 36 102 34 122 38V122C102 118 80 120 66 128Z" stroke-width="1.5" '
               'stroke-linejoin="round"/>')
    left = [(20, 56, 58), (20, 50, 70), (20, 56, 82), (20, 44, 94), (20, 54, 106)]
    right = [(76, 112, 58), (76, 104, 70), (76, 96, 82), (76, 110, 94), (76, 100, 106)]
    lines = "".join(f"M{x1} {y}H{x2}" for x1, x2, y in left + right)
    out.append(f'<path class="m" d="{lines}" stroke-width="2" stroke-linecap="round"/>')
    # the path: on from the end of the right page's third line, into the terminal's prompt line
    out.append('<path class="a draw" d="M96 82C118 82 128 76 156 76" pathLength="1" stroke-width="2.5" '
               'stroke-linecap="round" stroke-linejoin="round"/>')
    # the terminal, drawn over the path's end
    tx, ty, tw, th = 150, 38, 122, 84
    prompt = "> write 6 * 7"
    assert 160 + len(prompt) * cw(size) <= tx + tw - 8
    out.append(f'<rect class="s f" x="{tx}" y="{ty}" width="{tw}" height="{th}" rx="8" stroke-width="1.5"/>')
    out.append(f'<path class="s" d="M{tx} {ty + 17}H{tx + tw}" stroke-width="1.5"/>')
    for k in range(3):
        out.append(f'<circle class="m" cx="{tx + 11 + k * 9}" cy="{ty + 8.5}" r="2.25" stroke-width="1.5"/>')
    out.append(f'<text class="t mono" x="160" y="80" font-size="{size}">{esc(prompt)}</text>')
    out.append('<text class="ta mono" x="160" y="104" font-size="14" font-weight="700">42</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


TRACK_ICON = ('<path d="M10 5.5C8.3 4.3 5.6 3.8 2.5 4.25v11C5.6 14.8 8.3 15.3 10 16.5"/>'
              '<path d="M10 5.5c1.7-1.2 4.4-1.7 7.5-1.25v11c-3.1-.45-5.8.05-7.5 1.25"/>'
              '<path d="M10 5.5v11"/><path d="M12.25 8.25l2.5 2-2.5 2"/>')


# =================================================================== 01 introduction

def lang_intro():
    a = Art("l01", "One program, two ways to run it")
    src = "write 6 * 7"
    prog = ["push 6", "push 7", "mul", "write"]
    assert eval(src.split(" ", 1)[1]) == 42                       # the interpreter: it does the sum
    assert stack_machine(prog)[1] == [42]                         # the compiled code, run on a machine
    ty, by = 82, 212
    # the source
    a.box(24, 128, 112, 44, "s fs", rx=8)
    code(a, 36, 155, src, 13, weight=600)
    a.path(f"M138 150 H152 V{ty} H170", "s", arrow=True)
    a.path(f"M152 150 V{by} H170", "s", arrow=True)
    # top lane: the interpreter runs it
    pill(a, 226, ty, "interpreter", "s f", "t", 12.5, False, h=36, weight=600, w=108, rx=8)
    a.line(282, ty, 553, ty, arrow=True)
    # bottom lane: the compiler writes instructions, a machine runs them
    pill(a, 217, by, "compiler", "s f", "t", 12.5, False, h=36, weight=600, w=90, rx=8)
    a.line(264, by, 285, by, arrow=True)
    a.box(288, by - 42, 78, 84, "s fs", rx=6)
    for k, ins in enumerate(prog):
        code(a, 300, by - 20 + k * 16, ins, 11.5)
    a.line(368, by, 391, by, arrow=True)
    pill(a, 436, by, "machine", "s f", "t", 12.5, False, h=36, weight=600, w=84, rx=8)
    a.line(480, by, 553, by, arrow=True)
    # the two results, and what joins them
    rx = 580
    for y in (ty, by):
        pill(a, rx, y, "42", "a af", "ta", 14, True, h=26, weight=700, w=48)
    a.line(rx, ty + 15, rx, by - 15, "a")
    a.text(rx - 12, (ty + by) / 2 + 4, "the same answer", "ta", 12.5, "end", 700)
    return a


# =================================================================== 02 syntax

def lang_syntax():
    a = Art("l02", "Characters, tokens, tree")
    src = "sum := sum + 3 * n"
    toks = [("sum", "id"), (":=", "assign"), ("sum", "id"), ("+", "op"), ("3", "num"), ("*", "op"), ("n", "id")]
    # where each token starts: scan the line, skipping spaces, and check every token is there
    at, spans = 0, []
    for t, _ in toks:
        while src[at] == " ":
            at += 1
        assert src[at:at + len(t)] == t, (t, at)
        spans.append((at, at + len(t)))
        at += len(t)
    assert at == len(src)
    x0, w = 104, 26
    X = lambda i: x0 + i * w
    for i, ch in enumerate(src):
        a.box(X(i), 24, w, 26, "s f", rx=0)
        if ch != " ":
            a.text(X(i) + w / 2, 42, ch, size=14, anchor="middle", mono=True)
    mid = {}
    for (t, kind), (i, j) in zip(toks, spans):
        cx = (X(i) + X(j)) / 2
        mid[len(mid)] = cx
        pill(a, cx, 72, t, "s fs", "t", 13, True, h=24, w=X(j) - X(i) - 4, rx=6)
        a.text(cx, 100, kind, "tm", 10.5, "middle")
    a.text(24, 76, "scanner", size=12, weight=600)
    a.text(24, 203, "parser", size=12, weight=600)
    # the tree: each node under its own token, one level down per step from the root
    lv = [136, 178, 220, 262]
    nodes = {0: (mid[1], lv[0], ":="), 1: (mid[0], lv[1], "sum"), 2: (mid[3], lv[1], "+"),
             3: (mid[2], lv[2], "sum"), 4: (mid[5], lv[2], "*"), 5: (mid[4], lv[3], "3"), 6: (mid[6], lv[3], "n")}
    edges = [(0, 1), (0, 2), (2, 3), (2, 4), (4, 5), (4, 6)]
    hot = {4, 5, 6}
    boxes = {}
    for k, (x, y, t) in nodes.items():
        on = k in hot
        boxes[k] = pill(a, x, y, t, "a af" if on else "s f", "ta" if on else "t", 13, True, h=24, weight=700 if on else 600)
    for p, c in edges:
        join(a, boxes[p], boxes[c], "a" if c in hot and p in hot else "s")
    return a


# =================================================================== 03 names, scopes and bindings

def lang_scopes():
    a = Art("l03", "One name, two answers: static scope and dynamic scope")
    src = ["var x = 1", "fn show() { write x }", "fn test() { var x = 2; show() }", "test()"]
    size = 11.5
    a.box(24, 102, 238, 98, "s fs", rx=8)
    for k, l in enumerate(src):
        code(a, 36, 124 + k * 22, l, size)
    # each panel: its own copy of the three declarations, and the x in show bound to one of them
    use = (1, src[1].index("write x") + 6)                  # (line, column) of the x in show
    first = (0, src[0].index("x"))
    in_test = (2, src[2].index("var x") + 4)
    assert src[use[0]][use[1]] == src[first[0]][first[1]] == src[in_test[0]][in_test[1]] == "x"
    ps, X = 12, 298
    for top, name, target, answer in ((22, "static scope", first, "writes 1"),
                                      (158, "dynamic scope", in_test, "writes 2")):
        a.box(284, top, 332, 120, "s f", rx=10)
        a.text(X, top + 21, name, size=12.5, weight=700)
        base = [top + 46, top + 76, top + 106]
        for (ln, c) in (use, target):
            a.box(col(X, c, ps) - 1.5, base[ln] - 11, cw(ps) + 3, 15, "af", rx=3)
        for k, l in enumerate(src[:3]):
            sp = [(c, c + 1, "ta") for (ln, c) in (use, target) if ln == k]
            code(a, X, base[k], l, ps, spans=sp, weight=None)
        sx = col(X, use[1] + 0.5, ps)
        tx = col(X, target[1] + 0.5, ps)
        if target is first:
            # up from the x in show, left through the gap between the lines, up into the first x
            ch = base[0] + 13
            a.path(f"M{r1(sx)} {base[1] - 13} V{ch + 4} Q{r1(sx)} {ch} {r1(sx - 4)} {ch} H{r1(tx + 4)} "
                   f"Q{r1(tx)} {ch} {r1(tx)} {ch - 4} V{base[0] + 6}", "a", arrow=True)
        else:
            # down from the x in show, across the gap, into the x that test declared
            a.path(f"M{r1(sx)} {base[1] + 5} C{r1(sx)} {base[1] + 15} {r1(tx)} {base[1] + 11} "
                   f"{r1(tx)} {base[2] - 14}", "a", arrow=True)
        a.text(600, base[1] + 4, answer, "ta", 13, "end", 700)
    return a


# =================================================================== 04 semantic analysis

def lang_semantic():
    a = Art("l04", "After the semantic pass: every node has a type, and one conversion was added")
    # as parsed
    code(a, 120 - 5 * cw(13) / 2, 58, "a + 2", 13, weight=600)
    t = {"+": pill(a, 120, 106, "+", "s f", "t", 14, True, h=30, w=30, weight=600),
         "a": pill(a, 78, 176, "a", "s f", "t", 14, True, h=30, w=30, weight=600),
         "2": pill(a, 162, 176, "2", "s f", "t", 14, True, h=30, w=30, weight=600)}
    join(a, t["+"], t["a"])
    join(a, t["+"], t["2"])
    a.text(120, 232, "a is declared real", "tm", 11.5, "middle")
    # the pass
    a.line(204, 150, 326, 150, arrow=True)
    a.text(264, 139, "semantic analysis", size=12, anchor="middle", weight=600)
    # decorated: a type on every node, and a conversion between + and 2
    def typed(cx, cy, name, ty, new=False):
        s = f"{name} : {ty}"
        w = round(len(s) * cw(12.5) + 20)
        a.box(cx - w / 2, cy - 13, w, 26, "a af" if new else "s f", rx=13)
        x = cx - len(s) * cw(12.5) / 2
        if new:
            code(a, x, cy + 4.4, s, 12.5, "ta", weight=700)
        else:
            code(a, x, cy + 4.4, s, 12.5, "t", spans=[(len(name), len(s), "ta")], weight=600)
        return (cx - w / 2, cy - 13, cx + w / 2, cy + 13)
    d = {"+": typed(468, 76, "+", "real"), "a": typed(398, 160, "a", "real"),
         "float": typed(542, 160, "float", "real", True), "2": typed(542, 236, "2", "int")}
    join(a, d["+"], d["a"])
    join(a, d["+"], d["float"], "a")
    join(a, d["float"], d["2"], "a")
    return a


# =================================================================== 05 target machine architecture

def lang_machine():
    a = Art("l05", "A small machine: registers, memory, and one instruction at a time")
    prog = ["li t0, 6", "li t1, 7", "mul a0, t0, t1", "ret"]
    addrs = [0x1000 + 4 * k for k in range(len(prog))]
    assert [f"0x{v:04x}" for v in addrs] == ["0x1000", "0x1004", "0x1008", "0x100c"]
    # run the first two instructions: the registers as the picture shows them, about to run mul
    regs = {"pc": 0x1000, "sp": 0x8000, "a0": 0, "t0": 0, "t1": 0}

    def step():
        op, *args = prog[(regs["pc"] - 0x1000) // 4].replace(",", "").split()
        if op == "li":
            regs[args[0]] = int(args[1])
        elif op == "mul":
            regs[args[0]] = regs[args[1]] * regs[args[2]]
        regs["pc"] += 4
    step()
    step()
    shown = [("pc", "0x1008"), ("sp", "0x8000"), ("a0", "0"), ("t0", "6"), ("t1", "7")]
    for name, v in shown:
        assert (f"0x{regs[name]:04x}" if v.startswith("0x") else str(regs[name])) == v, (name, regs)
    pc_at = addrs.index(regs["pc"])
    assert pc_at == 2
    step()
    assert regs["a0"] == 42
    bits = format(regs["a0"], "08b")
    assert bits == "00101010"
    # registers
    a.text(24, 50, "registers", "tm", 11)
    for k, (name, v) in enumerate(shown):
        y = 62 + k * 30
        a.text(24, y + 19, name, size=12, weight=600, mono=True)
        pill(a, 98, y + 14, v, "s fs", "t", 12, True, h=28, w=76, rx=0)
    # memory
    a.text(176, 64, "memory", "tm", 11)
    for k, (ins, ad) in enumerate(zip(prog, addrs)):
        y = 76 + k * 30
        hot = k == pc_at
        a.box(176, y, 146, 30, "a af" if hot else "s f", rx=0)
        code(a, 188, y + 19, ins, 12, "ta" if hot else "t", weight=700 if hot else None)
        a.text(332, y + 19, f"0x{ad:04x}", "tm", 11, mono=True)
    py = 76 + pc_at * 30 + 15
    a.path(f"M138 76 H155 V{py} H173", "a", arrow=True)
    # the loop the machine runs
    cycle(a, 518, 134, 58, ["fetch", "decode", "execute"])
    # the answer, as the bits a register holds
    code(a, 320 - len(f"42 = {bits}") * cw(14) / 2, 256, f"42 = {bits}", 14, weight=600)
    return a


# =================================================================== 06 control flow

def lang_control():
    a = Art("l06", "A case statement as a jump table: one index, not three tests")
    src = ["case n of", "  1: a()", "  2: b()", "  3: c()"]
    for k, l in enumerate(src):
        code(a, 24, 116 + k * 22, l, 12)
    # three tests, one after another: the way not taken
    cx = 205
    a.text(cx, 66, "three tests", "tm", 11.5, "middle")
    tests = []
    for k in range(3):
        tests.append(pill(a, cx, 94 + k * 56, f"n = {k + 1} ?", "m f", "tm", 12, True, h=28, w=90, rx=6))
    for b1, b2 in zip(tests, tests[1:]):
        join(a, b1, b2, "m", arrow=True)
    # the table: n picks a cell, the cell holds where to go
    tx, tw, ch = 446, 50, 30
    mids = [119, 149, 179]
    labels = ["L1: a()", "L2: b()", "L3: c()"]
    for k, (y, lab) in enumerate(zip(mids, labels)):
        hot = k == 1
        pill(a, tx + tw / 2, y, str(k + 1), "a af" if hot else "s f", "ta" if hot else "tm", 12, True, h=ch, w=tw, rx=0)
        a.line(tx + tw + 2, y, 532, y, "a" if hot else "s", arrow=True)
        pill(a, 571, y, lab, "a af" if hot else "s fs", "ta" if hot else "t", 12, True, h=24, w=74, rx=6,
             weight=700 if hot else None)
    a.line(296, mids[1], tx - 3, mids[1], "a", arrow=True)
    a.text(370, mids[1] - 10, "n = 2", "ta", 12.5, "middle", 700, mono=True)
    a.text(370, mids[1] + 22, "one index", "ta", 12, "middle", 600)
    return a


# =================================================================== 07 type systems

def unify(t1, t2, sub):
    """Unify two types (strings; a name starting with ' is a variable) under substitution sub."""
    t1, t2 = sub.get(t1, t1), sub.get(t2, t2)
    if t1 == t2:
        return sub
    if t1.startswith("'"):
        return {**sub, t1: t2}
    if t2.startswith("'"):
        return {**sub, t2: t1}
    raise TypeError(f"{t1} is not {t2}")


def lang_types():
    a = Art("l07", "Type inference: constraints, then one substitution that satisfies them")
    # + takes (int, int) to int; x is its left operand, so 'a = int; the body's type is +'s result
    sub = unify("'a", "int", {})
    result = "int"
    assert sub == {"'a": "int"}
    inc = f"{sub.get(chr(39) + 'a')} -> {result}"
    assert inc == "int -> int"
    top = "fn inc(x) = x + 1"
    a.box(320 - len(top) * cw(14) / 2 - 14, 30, len(top) * cw(14) + 28, 36, "s fs", rx=8)
    code(a, 320 - len(top) * cw(14) / 2, 53, top, 14, weight=600)
    cols = [(24, 168, "what the checker knows"), (226, 202, "constraints"), (460, 156, "solved")]
    for x, w, head in cols:
        a.text(x + w / 2, 104, head, size=12, anchor="middle", weight=700)
        a.box(x, 118, w, 120, "s f", rx=10)
    rows = [150, 182, 214]
    for y, s in zip(rows, ["x : 'a", "1 : int", "+ : int, int -> int"]):
        code(a, 38, y, s, 12)
    w = len("'a = int") * cw(12.5) + 20
    a.box(240, rows[0] - 17, w, 24, "a af", rx=12)
    code(a, 250, rows[0], "'a = int", 12.5, "ta", weight=700)
    a.text(240, rows[0] + 22, "from x being an operand of +", "tm", 10.5)
    code(a, 240, rows[2], "result = int", 12)
    code(a, 474, rows[0], "'a := int", 12)
    final = f"inc : {inc}"
    w = len(final) * cw(12.5) + 20
    a.box(468, rows[2] - 17, w, 24, "a af", rx=12)
    code(a, 478, rows[2], final, 12.5, "ta", weight=700)
    a.line(194, 178, 222, 178, arrow=True)
    a.line(430, 178, 456, 178, arrow=True)
    return a


# =================================================================== 08 composite types

def lang_gc():
    a = Art("l08", "Mark and sweep: what the roots can reach stays, the rest is freed")
    edges = [("root1", "A"), ("A", "B"), ("A", "C"), ("root2", "D"), ("E", "F"), ("F", "E")]
    reach, todo = set(), ["root1", "root2"]
    while todo:
        n = todo.pop()
        for p, c in edges:
            if p == n and c not in reach:
                reach.add(c)
                todo.append(c)
    assert reach == {"A", "B", "C", "D"}, reach
    # the stack, two of its slots roots
    a.text(68, 64, "stack", size=12, anchor="middle", weight=700)
    rows = {"root1": 94, "root2": 202}
    for k in range(4):
        y = 76 + k * 36
        name = {0: "root1", 3: "root2"}.get(k)
        a.box(28, y, 80, 36, "s f" if name else "m f", rx=0)
        if name:
            a.text(68, y + 22, name, size=12, anchor="middle", weight=600, mono=True)
    # the heap
    a.box(140, 28, 476, 244, "m", rx=14)
    a.text(156, 50, "heap", size=12, weight=700)
    at = {"A": (244, 94), "B": (356, 58), "C": (356, 130), "D": (244, 202),
          "E": (466, 108), "F": (570, 108), "G": (518, 226)}
    b = {}
    for n, (x, y) in at.items():
        live = n in reach
        b[n] = pill(a, x, y, n, "s af" if live else "m f", "t" if live else "tm", 13, True, h=30, w=40, rx=6,
                    weight=700 if live else 600, dash=not live)
    a.line(110, rows["root1"], 221, at["A"][1], "a", arrow=True)
    a.line(110, rows["root2"], 221, at["D"][1], "a", arrow=True)
    join(a, b["A"], b["B"], "a", arrow=True)
    join(a, b["A"], b["C"], "a", arrow=True)
    # E and F point at each other, and nothing points at them
    (ex, ey), (fx, fy) = at["E"], at["F"]
    a.path(f"M{ex + 8} {ey - 17} Q{(ex + fx) / 2} {ey - 40} {fx - 9} {fy - 18}", "m", arrow=True)
    a.path(f"M{fx - 8} {fy + 17} Q{(ex + fx) / 2} {fy + 40} {ex + 9} {ey + 18}", "m", arrow=True)
    a.text(518, 56, "unreachable: freed", "tm", 12, "middle", 600)
    a.text(518, 160, "a cycle that counting", "tm", 10.5, "middle")
    a.text(518, 175, "references never frees", "tm", 10.5, "middle")
    return a


# =================================================================== 09 subroutines and control abstraction

def lang_coroutines():
    a = Art("l09", "A coroutine keeps its own stack: transfer switches between them")
    # two stacks, two frames each
    for name, x, frames in (("producer", 160, ["produce()", "main"]), ("consumer", 360, ["consume()", "main"])):
        a.text(x + 60, 40, name, size=12.5, anchor="middle", weight=700)
        for k, fr in enumerate(frames):                       # the newest frame on top
            pill(a, x + 60, 71 + k * 38, fr, "s f", "t", 12, True, h=38, w=120, rx=0)
    # the time strip: who runs, and the transfers between them with what each hands over
    lanes = {"producer": 178, "consumer": 236}
    for name, y in lanes.items():
        a.text(24, y + 4, name, size=12, weight=600)
        a.line(104, y, 600, y, "m")
    runs = [("producer", 110, 220), ("consumer", 280, 390), ("producer", 450, 560)]
    for name, x1, x2 in runs:
        a.box(x1, lanes[name] - 10, x2 - x1, 20, "s fs", rx=4)
        a.text((x1 + x2) / 2, lanes[name] + 4, "runs", "tm", 10.5, "middle")
    # only the producer hands a value over; the way back carries none
    hands = [(runs[0], runs[1], "1", "transfer", "end", -16), (runs[1], runs[2], None, "transfer back", "start", 10)]
    for (n1, _, e1), (n2, s2, _), v, label, side, off in hands:
        y1 = lanes[n1] + (10 if lanes[n2] > lanes[n1] else -10)
        y2 = lanes[n2] + (-10 if lanes[n2] > lanes[n1] else 10)
        a.line(e1 + 2, y1, s2 - 3, y2, "a", arrow=True)
        mx, my = (e1 + s2) / 2, (lanes[n1] + lanes[n2]) / 2
        if v:
            a.circle(mx, my, 10, "a f")
            a.text(mx, my + 4.5, v, "ta", 12.5, "middle", 700, mono=True)
        a.text(mx + off, my + 8, label, "ta", 11.5, side, 600)
    return a


# =================================================================== 10 data abstraction and object orientation

def lang_objects():
    a = Art("l10", "An object, its class's table of methods, and a call that goes through it")
    # the object
    a.text(66, 70, "s", size=13, anchor="middle", weight=700, mono=True)
    for k, f in enumerate(["vptr", "w = 3", "h = 4"]):
        pill(a, 66, 95 + k * 30, f, "s f", "t", 12, True, h=30, w=84, rx=0, weight=600 if k == 0 else None)
    # Rect's table
    a.text(204, 70, "Rect", size=12.5, anchor="middle", weight=700, mono=True)
    for k, m in enumerate(["area", "draw"]):
        pill(a, 204, 95 + k * 30, m, "s f", "t", 12, True, h=30, w=80, rx=0)
    a.line(110, 95, 162, 95, arrow=True)
    # the code, in the middle
    code_at = {"Rect.area": 70, "Square.area": 146, "Shape.draw": 222}
    for name, y in code_at.items():
        pill(a, 358, y, name, "s fs", "t", 12, True, h=28, w=108, rx=6)
    a.path(f"M246 95 H274 V{code_at['Rect.area']} H302", "s", arrow=True)
    a.path(f"M246 125 H274 V{code_at['Shape.draw']} H302", "s", arrow=True)
    # Square's table: area overridden, draw inherited
    a.text(520, 121, "Square", size=12.5, anchor="middle", weight=700, mono=True)
    pill(a, 520, 146, "area", "a af", "ta", 12, True, h=30, w=80, rx=0, weight=700)
    pill(a, 520, 176, "draw", "s f", "t", 12, True, h=30, w=80, rx=0)
    a.text(520, 210, "a subclass of Rect", "tm", 10.5, "middle")
    a.line(478, code_at["Square.area"], 414, code_at["Square.area"], "a", arrow=True)
    a.path(f"M478 176 H446 V{code_at['Shape.draw']} H414", "s", arrow=True)
    call = "s.area()  ->  s.vptr[0](s)"
    code(a, 320 - len(call) * cw(13) / 2, 270, call, 13, weight=600)
    return a


# =================================================================== 11 functional languages

def lang_lazy():
    a = Art("l11", "A lazy list: only what is asked for is ever computed")
    y, h = 130, 40
    xs = [32, 144, 256]
    for k, x in enumerate(xs):
        a.box(x, y, 80, h, "s f", rx=6)
        a.line(x + 40, y + 1, x + 40, y + h - 1, "s")
        a.text(x + 20, y + 25, str(k), size=15, anchor="middle", weight=700, mono=True)
        a.circle(x + 60, y + 20, 3, "s fs")
        nxt = xs[k + 1] if k + 1 < len(xs) else 376
        a.line(x + 64, y + 20, nxt - 3, y + 20, arrow=True)
    code(a, (32 + 336) / 2 - len("take(3, naturals)") * cw(13) / 2, 92, "take(3, naturals)", 13, weight=600)
    a.path("M32 110 V104 H336 V110", "m")
    # the rest: a promise, not a list yet
    a.box(376, 116, 224, 68, "a af", rx=10, dash=True)
    a.text(488, 146, "a promise: the rest,", "ta", 13, "middle", 700)
    a.text(488, 164, "not computed yet", "ta", 13, "middle", 700)
    a.text(488, 212, "forced only if someone", "tm", 11.5, "middle")
    a.text(488, 228, "asks for the fourth", "tm", 11.5, "middle")
    return a


# =================================================================== 12 logic languages

def lang_logic():
    a = Art("l12", "A query answered by search: unify, try a rule, back up when it fails")
    facts = [("alice", "bob"), ("bob", "carol")]
    # grandparent(X, carol) :- parent(X, B), parent(B, carol): try each fact for the first goal
    tries = [(x, b, (b, "carol") in facts) for x, b in facts]
    assert tries == [("alice", "bob", True), ("bob", "carol", False)], tries
    answers = [x for x, _, ok in tries if ok]
    assert answers == ["alice"]
    prog = ["parent(alice, bob).", "parent(bob, carol).", "grandparent(A, C) :- parent(A, B), parent(B, C)."]
    q = "?- grandparent(X, carol)."
    ps = 11
    a.box(148, 22, 344, 84, "s fs", rx=8)
    for k, l in enumerate(prog):
        code(a, 160, 40 + k * 16, l, ps)
    a.line(160, 82, 480, 82, "m")
    code(a, 160, 98, q, ps, weight=700)
    goals = pill(a, 320, 133, "parent(X, B), parent(B, carol)", "s f", "t", ps, True, h=22, rx=11)
    a.line(320, 108, 320, 120, arrow=True)
    left = pill(a, 196, 214, "parent(bob, carol)", "a af", "ta", ps, True, h=22, rx=11, weight=700)
    right = pill(a, 444, 214, "parent(carol, carol)", "m f", "tm", ps, True, h=22, rx=11, dash=True)
    join(a, goals, left, "a", arrow=True)
    join(a, goals, right, "m", arrow=True)
    pill(a, 234, 174, "X = alice, B = bob", "a f", "ta", ps, True, h=20, rx=10, weight=700)
    pill(a, 406, 174, "X = bob, B = carol", "m f", "tm", ps, True, h=20, rx=10)
    a.text(196, 246, "yes", "ta", 12.5, "middle", 700)
    a.text(444, 246, "fails: back up", "tm", 11.5, "middle")
    pill(a, 196, 268, f"X = {answers[0]}", "a af", "ta", 12, True, h=22, rx=11, weight=700)
    return a


# =================================================================== 13 concurrency

def schedule(order, start=5):
    """Run (thread, step) pairs on a shared counter, each thread with a register of its own:
    the label of each step as it runs, and the counter at the end."""
    counter, reg, out = start, {}, []
    for t, op in order:
        if op == "load":
            reg[t] = counter
            out.append((t, f"load {counter}"))
        elif op == "add":
            reg[t] += 1
            out.append((t, "add 1"))
        else:
            counter = reg[t]
            out.append((t, f"store {counter}"))
    return out, counter


def lang_race():
    a = Art("l13", "A race: two threads, one counter, one update lost")
    ops = ["load", "add", "store"]
    race, end = schedule([(t, op) for op in ops for t in (1, 2)])
    assert [s for _, s in race] == ["load 5", "load 5", "add 1", "add 1", "store 6", "store 6"] and end == 6
    locked, end2 = schedule([(t, op) for t in (1, 2) for op in ops])
    assert [s for _, s in locked] == ["load 5", "add 1", "store 6", "load 6", "add 1", "store 7"] and end2 == 7
    X = lambda i: 136 + i * 64
    # interleaved
    lanes = {1: 60, 2: 104}
    for t, y in lanes.items():
        a.text(24, y + 4, f"thread {t}", size=12, weight=600)
        a.line(100, y, 488, y, "m")
    for i, (t, s) in enumerate(race):
        hot = i == 5
        pill(a, X(i), lanes[t], s, "a af" if hot else "s f", "ta" if hot else "t", 11, True, h=24, w=60, rx=6,
             weight=700 if hot else None)
    a.line(100, 134, 486, 134, "m", arrow=True)
    a.text(494, 138, "time", "tm", 10.5)
    code(a, 516, 78, f"counter = {end},", 12)
    a.text(516, 98, "not 7", "ta", 13.5, weight=700)
    # with a lock
    a.text(24, 176, "with a lock", size=12, weight=700)
    lanes2 = {1: 206, 2: 242}
    for t, y in lanes2.items():
        a.text(24, y + 4, f"thread {t}", "tm", 11)
        a.line(100, y, 488, y, "m")
    for i, (t, s) in enumerate(locked):
        pill(a, X(i), lanes2[t], s, "s f", "t", 10.5, True, h=20, w=58, rx=5)
    for t, i0 in ((1, 0), (2, 3)):
        a.box(X(i0) - 36, lanes2[t] - 14, X(i0 + 2) - X(i0) + 72, 28, "m", rx=8, dash=True)
    code(a, 516, lanes2[2] + 4, f"counter = {end2}", 12)
    return a


# =================================================================== 14 scripting languages

def lang_scripting():
    a = Art("l14", "A pattern, a table and two lines: what a scripting language is for")
    script = ['for line in lines("log.txt")', "  if line ~ /error: (\\w+)/ then count[$1] += 1"]
    log = ["error: disk full", "ok: saved", "error: disk slow"]
    pat = script[1][script[1].index("/") + 1:script[1].rindex("/")]
    assert pat == r"error: (\w+)"
    count = {}
    for l in log:
        m = re.search(pat, l)
        if m:
            count[m.group(1)] = count.get(m.group(1), 0) + 1
    assert count == {"disk": 2}, count
    s, o = 11.5, -14          # o: everything up a little, so the picture sits in the middle
    g0 = script[1].index("(\\w+)")
    g1 = g0 + len("(\\w+)")
    a.box(24, o + 114, 341, 60, "s fs", rx=8)
    a.box(col(36, g0, s) - 2, o + 150, (g1 - g0) * cw(s) + 4, 17, "af", rx=3)
    code(a, 36, o + 138, script[0], s)
    code(a, 36, o + 162, script[1], s, spans=[(g0, g1, "ta")])
    # the log
    code(a, 381, o + 100, "log.txt", 11, "tm")
    a.box(381, o + 108, 134, 70, "s f", rx=8)
    for k, l in enumerate(log):
        code(a, 393, o + 130 + k * 19, l, s)
    # the table the script fills
    (key, n), = count.items()
    a.box(535, o + 108, 76, 26, "s fs", rx=0)
    a.text(573, o + 126, "count", size=12, anchor="middle", weight=700, mono=True)
    pill(a, 557, o + 149, key, "s f", "t", 12, True, h=30, w=44, rx=0, weight=600)
    pill(a, 595, o + 149, str(n), "s f", "t", 12, True, h=30, w=32, rx=0)
    gx = col(36, (g0 + g1) / 2, s)
    a.path(f"M{r1(gx)} {o + 169} V{o + 210} H557 V{o + 167}", "a", arrow=True)
    return a


# =================================================================== 15 building a runnable program

def lang_backend():
    a = Art("l15", "From the tree to a program a machine can load")
    main_size = 0x40
    lib_at = 0x1000 + main_size
    assert lib_at == 0x1040
    o = -12                   # everything up a little, so the picture sits in the middle
    head = o + 100
    # the tree of a + b * c: + over a and *, * over b and c
    t = {k: pill(a, x, o + y, k, "s f", "t", 12, True, h=22, w=22, weight=600)
         for k, x, y in (("+", 62, 122), ("a", 36, 158), ("*", 88, 158), ("b", 70, 194), ("c", 106, 194))}
    for p, c in (("+", "a"), ("+", "*"), ("*", "b"), ("*", "c")):
        join(a, t[p], t[c])
    a.text(62, head, "tree", size=11.5, anchor="middle", weight=700)
    a.line(122, o + 156, 141, o + 156, arrow=True)
    # three-address code
    a.box(144, o + 130, 106, 52, "s fs", rx=6)
    code(a, 154, o + 151, "t1 := b * c", 11)
    code(a, 154, o + 169, "t2 := a + t1", 11)
    a.text(197, head, "three-address code", size=11.5, anchor="middle", weight=700)
    a.line(252, o + 156, 271, o + 156, arrow=True)
    # assembly
    a.box(274, o + 130, 118, 52, "s fs", rx=6)
    code(a, 284, o + 151, "mul t1, a1, a2", 11)
    code(a, 284, o + 169, "add t0, a0, t1", 11)
    a.text(333, head, "assembly", size=11.5, anchor="middle", weight=700)
    a.line(394, o + 156, 413, o + 156, arrow=True)
    # object files
    for y, name in ((o + 118, "main.o"), (o + 160, "lib.o")):
        page(a, 416, y, 60, 34, "s f", fold=8)
        a.text(446, y + 21, name, size=11, anchor="middle", mono=True)
    a.text(446, head, "object files", size=11.5, anchor="middle", weight=700)
    # the linker, and the program it writes: every piece at an address
    a.line(478, o + 156, 499, o + 156, "a", arrow=True)
    a.box(502, o + 116, 114, 80, "a af", rx=8)
    for k, (ad, name) in enumerate(((0x1000, "main.o"), (lib_at, "lib.o"))):
        y = o + 124 + k * 34
        a.box(510, y, 98, 30, "a f", rx=4)
        code(a, 517, y + 19.5, f"0x{ad:04x}", 11, "ta", weight=700)
        code(a, 517 + 7 * cw(11), y + 19.5, name, 11, "t")
    a.text(559, head, "program", "ta", 11.5, "middle", 700)
    a.text(489, o + 224, "the linker gives every", "ta", 11.5, "middle", 600)
    a.text(489, o + 240, "name an address", "ta", 11.5, "middle", 600)
    return a


# =================================================================== 16 run-time program management

def lang_vm():
    a = Art("l16", "A virtual machine: bytecode, a stack, and a loop")
    prog = ["PUSH 6", "PUSH 7", "MUL", "WRITE"]
    states, out = stack_machine(prog)
    assert states == [[6], [6, 7], [42], []] and out == [42], (states, out)
    pc = 2
    # the bytecode, and pc at the third instruction
    a.box(64, 82, 92, 110, "s fs", rx=8)
    for k, ins in enumerate(prog):
        hot = k == pc
        code(a, 78, 106 + k * 24, ins, 13, "ta" if hot else "t", weight=700 if hot else None)
    py = 106 + pc * 24 - 4.5
    a.text(24, py + 4.5, "pc", "ta", 13, weight=700, mono=True)
    a.line(46, py, 70, py, "a", arrow=True)
    # the operand stack after each instruction
    a.text(306, 88, "the stack after each", "tm", 11, "middle")
    cx0, step, ch, floor = 222, 56, 26, 192
    for k, (ins, st) in enumerate(zip(prog, states)):
        x = cx0 + k * step
        a.path(f"M{x - 23} {floor - 74} V{floor} H{x + 23} V{floor - 74}", "m")
        for j, v in enumerate(st):
            hot = k == pc
            pill(a, x, floor - 2 - ch / 2 - j * ch, str(v), "a af" if hot else "s f", "ta" if hot else "t", 12.5,
                 True, h=ch - 2, w=40, rx=3, weight=700 if hot else 600)
        a.text(x, floor + 18, ins, "tm", 10.5, "middle", mono=True)
    # the loop
    cycle(a, 520, 138, 56, ["fetch", "decode", "do"])
    s = f"writes {out[0]}"
    code(a, 320 - len(s) * cw(14) / 2, 262, s, 14, spans=[(7, len(s), "ta")], weight=700)
    return a


# =================================================================== 17 code improvement

def value_numbers(block):
    """Local value numbering over 'd := x op y' lines: (the lines kept, rewritten; the table)."""
    vn, table, alias, out, fresh = {}, {}, {}, [], iter(range(1, 1000))
    num = lambda v: vn[v] if v in vn else vn.setdefault(v, next(fresh))
    for line in block:
        d, x, op, y = re.match(r"(\w+) := (\w+) (\S) (\w+)$", line).groups()
        x, y = alias.get(x, x), alias.get(y, y)                  # a removed name reads as its holder
        key = (num(x), op, num(y))
        if key in table:                                         # done before: d is that value
            vn[d], alias[d] = table[key]
            continue
        vn[d] = next(fresh)
        table[key] = (vn[d], d)
        out.append(f"{d} := {x} {op} {y}")
    return out, vn, {k: n for k, (n, _) in table.items()}


def lang_vn():
    a = Art("l17", "Value numbering: the same work, done once")
    before = ["t1 := a + b", "t2 := a + b", "c := t1 * t2"]
    after, vn, table = value_numbers(before)
    assert after == ["t1 := a + b", "c := t1 * t1"], after
    assert (vn["a"], vn["b"], table[(1, "+", 2)], vn["t1"], vn["t2"]) == (1, 2, 3, 3, 3), (vn, table)
    s = 12
    x0 = 52
    # before
    a.text(x0, 96, "before", size=12.5, weight=700)
    a.box(x0, 108, 112, 82, "s fs", rx=8)
    for k, l in enumerate(before):
        code(a, x0 + 12, 132 + k * 24, l, s)
    a.line(x0 + 116, 149, x0 + 146, 149, "m", arrow=True)
    # the table
    tx = x0 + 150
    a.text(tx, 96, "value numbers", size=12.5, weight=700)
    a.box(tx, 108, 196, 124, "s f", rx=8)
    for k, l in enumerate(["a -> 1", "b -> 2", "1 + 2 -> 3"]):
        code(a, tx + 14, 132 + k * 24, l, s)
    a.line(tx + 10, 190, tx + 186, 190, "m")
    a.text(tx + 14, 208, "t1 is value 3", "tm", 11)
    a.text(tx + 14, 224, "t2 is value 3 too", "tm", 11)
    a.line(tx + 200, 149, tx + 230, 149, "m", arrow=True)
    # after: the second line gone, its use now the first one's
    ax = tx + 234
    a.text(ax, 96, "after", size=12.5, weight=700)
    a.box(ax, 108, 112, 82, "s fs", rx=8)
    code(a, ax + 12, 132, after[0], s)
    a.box(ax + 6, 140, 100, 20, "m", rx=4, dash=True)
    code(a, ax + 12, 156, before[1], s, "tm")
    last = after[1]
    reuse = last.rindex("t1")
    a.box(col(ax + 12, reuse, s) - 2, 168, 2 * cw(s) + 4, 17, "af", rx=3)
    code(a, ax + 12, 180, last, s, spans=[(reuse, reuse + 2, "ta")])
    return a


# =================================================================== icons and the table

ICON = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="none" stroke="currentColor" '
        'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">{}</svg>\n')

MODULES = {
    "01": (lang_intro, '<circle cx="10" cy="10" r="7.5"/><path d="M8.25 6.9v6.2l4.9-3.1z"/>'),
    "02": (lang_syntax, '<circle cx="10" cy="4.5" r="2"/><circle cx="4.5" cy="15.5" r="2"/>'
                        '<circle cx="15.5" cy="15.5" r="2"/><path d="M8.9 6.2l-3.3 7.6M11.1 6.2l3.3 7.6"/>'),
    "03": (lang_scopes, '<rect x="2.5" y="2.5" width="15" height="15" rx="3"/><rect x="5.5" y="5.5" width="9" height="9" rx="2"/>'
                        '<rect x="8.5" y="8.5" width="3" height="3" rx="1"/>'),
    "04": (lang_semantic, '<circle cx="6.5" cy="10" r="4"/><path d="M12.25 10.25l2 2 3.75-4.5"/>'),
    "05": (lang_machine, '<rect x="5" y="5" width="10" height="10" rx="1.5"/>'
                         '<path d="M7.5 2.25V5M10 2.25V5M12.5 2.25V5M7.5 15v2.75M10 15v2.75M12.5 15v2.75"/>'),
    "06": (lang_control, '<path d="M2.5 10H7M7 10L11.5 4H17M7 10H17M7 10l4.5 6H17"/>'
                         '<path d="M15.25 2.25L17 4l-1.75 1.75M15.25 8.25L17 10l-1.75 1.75M15.25 14.25L17 16l-1.75 1.75"/>'),
    "07": (lang_types, '<path d="M3 4.25C3 3.56 3.56 3 4.25 3H10l7.5 7.5-7 7L3 10Z"/><circle cx="6.75" cy="6.75" r="1.25"/>'),
    "08": (lang_gc, '<rect x="3" y="3" width="6" height="6" rx="1"/><rect x="11" y="3" width="6" height="6" rx="1"/>'
                    '<rect x="3" y="11" width="6" height="6" rx="1"/>'
                    '<rect x="11" y="11" width="6" height="6" rx="1" stroke-dasharray="1.5 2.5"/>'),
    "09": (lang_coroutines, '<rect x="2.5" y="3" width="8" height="4" rx="1"/><rect x="2.5" y="8.5" width="8" height="4" rx="1"/>'
                            '<rect x="2.5" y="14" width="8" height="4" rx="1"/>'
                            '<path d="M11.5 5c3.25 0 5 1.75 5 5v4.5"/><path d="M14.5 12.5l2 2 2-2"/>'),
    "10": (lang_objects, '<rect x="2" y="4.5" width="9" height="11" rx="1.5"/><path d="M11 10h2.5"/>'
                         '<rect x="13.5" y="7" width="4.5" height="6" rx="1"/>'),
    "11": (lang_lazy, '<path d="M4.5 3.5c1.75 0 2.6.75 3.4 2.6L14 16.5h1.5"/><path d="M9.5 9.25L4.5 16.5"/>'),
    "12": (lang_logic, '<path d="M3.5 6.25a3 3 0 1 1 4.6 2.5c-1 .65-1.6 1.3-1.6 2.5v.5"/><path d="M6.5 15.75v.01"/>'
                       '<path d="M12 11h5.5"/>'),
    "13": (lang_race, '<path d="M6 3v1.25M6 7.75v4.5M6 15.75V17M14 3v5.25M14 11.75V17"/>'
                      '<circle cx="6" cy="6" r="1.75"/><circle cx="14" cy="10" r="1.75"/><circle cx="6" cy="14" r="1.75"/>'),
    "14": (lang_scripting, '<path d="M5.5 4L4.5 16M9.5 4L8.5 16M2.75 8H11M2.25 12h8.25"/><path d="M15.5 4v7.5M15.5 15.75v.01"/>'),
    "15": (lang_backend, '<rect x="2" y="6" width="7" height="8" rx="1.5"/><rect x="11" y="6" width="7" height="8" rx="1.5"/>'
                         '<path d="M9 10h2"/>'),
    "16": (lang_vm, '<circle cx="10" cy="10" r="1.5"/><path d="M16.5 10a6.5 6.5 0 1 1-1.9-4.6"/><path d="M15.1 2.6v3.2h-3.2"/>'),
    "17": (lang_vn, '<path d="M3 14.5a7 7 0 0 1 14 0"/><path d="M10 14.5l3.5-4.5"/>'),
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
