"""Module art for the research outline (outlines/ai-research.md), in the same visual language as
dsa_art.py, outline_art.py and the xv6 covers.

Writes, under outlines/ai-research/:
    NN/cover.svg    640x300 teaching diagram for module NN (00 to 21; 16 to 21 are the extensions)
    NN/icon.svg     20x20 currentColor line icon for module NN
The track-level art.svg and icon.svg there are not this script's.

Covers style themselves only through the .art classes in harness/web/app.css:
    s m a        stroke: foreground, muted, accent
    f fs af fa   fill: page, code background, accent-soft, accent
    t tm ta      text fill: foreground, muted, accent      mono: monospace
A shaded cell is a rect of class fa (or t) with a fill-opacity, so it follows the theme.

What a cover shows is either computed here or drawn as a labelled schematic with no numbers on
its axes. Computed: the backprop graph and its nudge check, the seed runs of module 00 (a small
curve fit with hand-written gradients), the optimiser paths of 03, the activation sizes through
50 layers in 04, the double-descent curve in 05 (random ReLU features, least squares), the
convolution in 06, the BPE merges in 09, the LoRA counts in 12, the DDPM noising in 17 and the
PPO objective in 18. Schematic (the true shape, no measured numbers): 08's attention shading,
11's loss curves, 13's panels, 14's grokking curves (after Power et al. 2022, Figure 1), 20's
over-optimisation and 21's four phenomena.

Modules 01, 14 and 15 keep the covers first drawn for the older outline in outline_art.py (its
modules 01, 04 and 07): 01 with a nudge check added, 14 with its step gap corrected to the
paper's (train near 100% before 1e3 steps, validation only near 1e6). The rest are new here.

The Art class is the one from art/xv6/covers.py and dsa_art.py, repeated so this file stands alone.

    python3 art/outlines/research_art.py     write every file, then check each one is ASCII and
                                             survives harness/web/art.py's sanitizer unchanged
"""
import html
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "outlines", "ai-research")
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
    """A box with one centred label: an array slot, a tensor element, a token."""
    a.box(x, y, w, h, cls, rx=rx, dash=dash)
    if s:
        a.text(round(x + w / 2, 1), round(y + h / 2 + size * 0.35, 1), s, tcls, size, "middle", weight, mono)


def shade(a, x, y, w, h, op, cls="fa"):
    """A filled cell with no outline, its strength given as an opacity: an attention weight, a pixel."""
    op = max(0.0, min(1.0, op))
    a.add(f'<rect class="{cls}" x="{round(x, 1)}" y="{round(y, 1)}" width="{round(w, 1)}" height="{round(h, 1)}" '
          f'fill-opacity="{op:.2f}"/>')


def poly(a, pts, cls="s", dash=False, arrow=False):
    a.path("M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts), cls, arrow=arrow, dash=dash)


def dot(a, x, y, r=3.5, cls="s f"):
    a.circle(round(x, 1), round(y, 1), r, cls)


def plus(a, x, y, r=9):
    a.circle(x, y, r, "s f")
    a.path(f"M{x - r / 2} {y} H {x + r / 2} M{x} {y - r / 2} V {y + r / 2}", "s")


def axes(a, x0, y0, x1, y1):
    """An L of two muted lines: the y axis at x0 from y0 down to y1, the x axis along y1."""
    a.line(x0, y1, x1, y1, "m")
    a.line(x0, y1, x0, y0, "m")


def clipped(a, pts, box, cls="m", dash=False):
    """Draw only the parts of a polyline that lie inside box = (x0, y0, x1, y1)."""
    x0, y0, x1, y1 = box
    seg = []
    for x, y in pts:
        if x0 <= x <= x1 and y0 <= y <= y1:
            seg.append((x, y))
        else:
            if len(seg) > 1:
                poly(a, seg, cls, dash)
            seg = []
    if len(seg) > 1:
        poly(a, seg, cls, dash)


# =================================================================== 00 workbench

def seed_run(seed, steps=300, every=5, lr=0.1, hidden=8, batch=8):
    """The kind of experiment module 00 starts with, small: fit a curve with a 1-8-1 tanh network,
    its gradients worked out by hand, plain SGD on mini-batches. The data is the same for every
    seed; the seed sets the starting weights and the batch order. Returns the validation losses."""
    rd = random.Random(1000)
    xs = [rd.uniform(-1, 1) for _ in range(64)]
    data = [(x, math.sin(2.5 * x) + rd.gauss(0, 0.1)) for x in xs]
    train, val = data[:32], data[32:]
    r = random.Random(seed)
    w1 = [r.gauss(0, 1) for _ in range(hidden)]
    b1 = [0.0] * hidden
    w2 = [r.gauss(0, 1 / math.sqrt(hidden)) for _ in range(hidden)]
    b2 = 0.0

    def fwd(x):
        h = [math.tanh(w1[j] * x + b1[j]) for j in range(hidden)]
        return h, sum(w2[j] * h[j] for j in range(hidden)) + b2

    def loss(d):
        return sum((fwd(x)[1] - y) ** 2 for x, y in d) / len(d)
    log, order = [], []
    for step in range(steps + 1):
        if step % every == 0:
            log.append(loss(val))
        if step == steps:
            break
        if not order:
            order = list(range(len(train)))
            r.shuffle(order)
        gw1, gb1, gw2, gb2 = [0.0] * hidden, [0.0] * hidden, [0.0] * hidden, 0.0
        for x, y in (train[order.pop()] for _ in range(batch)):
            h, p = fwd(x)
            d = 2 * (p - y) / batch
            gb2 += d
            for j in range(hidden):
                gw2[j] += d * h[j]
                dh = d * w2[j] * (1 - h[j] ** 2)
                gw1[j] += dh * x
                gb1[j] += dh
        for j in range(hidden):
            w1[j] -= lr * gw1[j]
            b1[j] -= lr * gb1[j]
            w2[j] -= lr * gw2[j]
        b2 -= lr * gb2
    return log


def res_workbench():
    a = Art("r00", "One experiment in one file, run over five seeds: the same seed gives the same curve, "
                   "other seeds show how far the number moves by chance")
    a.text(24, 28, "one file", size=12, weight=700)
    stages = [("data", "points on a curve, with noise"), ("model", "y = f(x; w)"), ("loss", "mean squared error"),
              ("update", "w -= lr * grad, worked by hand"), ("evaluate", "loss on held-out points")]
    for k, (name, sub) in enumerate(stages):
        y = 40 + k * 38
        cell(a, 32, y, 92, 26, name, "s fs" if k in (1, 3) else "s f", "t", 11.5, rx=6, weight=600, mono=False)
        a.text(134, y + 17, sub, "tm", 10.5)
        if k:
            a.line(78, y - 12, 78, y - 2, "s", arrow=True)
    a.path("M32 167 H 20 V 91 H 30", "m", arrow=True)
    a.text(24, 248, "the runner keeps every run's config,", "tm", 10.5)
    a.text(24, 263, "seed and log, and draws runs over each other", "tm", 10.5)

    logs = [seed_run(s) for s in range(5)]
    assert seed_run(0) == logs[0]                     # same seed, same numbers, to the last digit
    px0, px1, py0, py1 = 356, 604, 44, 214
    lo = math.log10(min(min(l) for l in logs)) - 0.08
    hi = math.log10(max(max(l) for l in logs)) + 0.05
    n = len(logs[0]) - 1
    X = lambda i: px0 + 4 + i / n * (px1 - px0 - 8)
    Y = lambda v: py1 - (math.log10(v) - lo) / (hi - lo) * (py1 - py0)
    axes(a, px0, py0 - 6, px1, py1)
    a.text(px0, 32, "validation loss, log scale", "tm", 10.5)
    a.text(px1, py1 + 18, "steps", "tm", 10.5, "end")
    for s in (1, 2, 3, 4, 0):
        poly(a, [(X(i), Y(v)) for i, v in enumerate(logs[s])], "a" if s == 0 else "m")
    ends = sorted(Y(l[-1]) for l in logs)
    for s in range(5):
        dot(a, X(n), Y(logs[s][-1]), 2.6, "a fa" if s == 0 else "s f")
    bx = px1 + 6
    a.path(f"M{bx - 2} {ends[0]:.1f} H {bx + 2} V {ends[-1]:.1f} H {bx - 2}", "s")
    a.text(px1 - 4, ends[0] - 10, "the spread over 5 seeds", size=10.5, anchor="end", weight=600)
    a.text(px1 - 4, 70, "seed 0, run twice: one curve,", "ta", 10.5, "end", 600)
    a.text(px1 - 4, 85, "the same to the last digit", "ta", 10.5, "end")
    a.text(px1 - 4, 106, "seeds 1 to 4: same code,", "tm", 10.5, "end")
    a.text(px1 - 4, 121, "other numbers", "tm", 10.5, "end")
    a.text(24, 288, "One run is never a result: report the number with its spread over seeds.  (Curves computed here.)",
           "tm", 11)
    return a


# =================================================================== 01 backprop

def res_backprop():
    a = Art("r01", "Backpropagation on a small graph: values flow forward, gradients flow back")
    va, vb, vc, vf = 2.0, -3.0, 10.0, -2.0

    def forward(xa):
        e = xa * vb
        d = e + vc
        return e, d, d * vf
    ve, vd, vL = forward(va)
    gL = 1.0
    gd, gf = vf * gL, vd * gL           # L = d * f
    ge, gc = gd, gd                     # d = e + c
    ga, gb = vb * ge, va * ge           # e = a * b
    h = 0.001
    nudge = (forward(va + h)[2] - vL) / h
    assert abs(nudge - ga) < 1e-6
    W, H = 96, 46
    f1 = lambda v: f"{v:.1f}"
    nodes = {"a": (24, 36, va, ga), "b": (24, 112, vb, gb), "e": (182, 72, ve, ge),
             "c": (182, 158, vc, gc), "d": (342, 116, vd, gd), "f": (342, 200, vf, gf),
             "L": (504, 158, vL, gL)}
    for name, (x, y, v, g) in nodes.items():
        a.box(x, y, W, H, "s f", rx=8)
        a.text(x + 12, y + 19, f"{name} = {f1(v)}", size=12, mono=True, weight=600)
        a.text(x + 12, y + 36, f"grad {f1(g)}", "ta", 11, mono=True)
    for x, y, s in ((152, 97, "*"), (312, 139, "+"), (474, 181, "*")):
        a.circle(x, y, 12, "s fs")
        a.text(x, y + 4.5, s, size=13, anchor="middle", mono=True, weight=600)

    def edge(x1, y1, x2, y2):
        a.path(f"M{x1} {y1} C {x1 + 14} {y1}, {x2 - 16} {y2}, {x2} {y2}", "s")
    edge(120, 59, 140, 93); edge(120, 135, 140, 101)
    a.line(164, 97, 180, 95, arrow=True)
    edge(278, 95, 300, 135); edge(278, 181, 300, 143)
    a.line(324, 139, 340, 139, arrow=True)
    edge(438, 139, 462, 177); edge(438, 223, 462, 185)
    a.line(486, 181, 502, 181, arrow=True)
    a.line(24, 16, 300, 16, "s", arrow=True)
    a.text(308, 20, "forward: values", "tm", 10.5)
    a.text(24, 186, "chain rule, one step:", "tm", 10.5)
    a.text(24, 204, "a.grad = b x e.grad", "ta", 11, mono=True, weight=600)
    a.text(65, 220, f"= {f1(vb)} x {f1(ge)} = {f1(ga)}", "ta", 11, mono=True)
    a.text(24, 246, f"check: nudge a by h = {h}", "tm", 10.5)
    a.text(24, 262, f"(L(a+h) - L(a)) / h = {nudge:.3f}", size=11, mono=True)
    a.line(616, 280, 250, 280, "a", arrow=True)
    a.text(240, 284, "backward(): gradients, from L", "ta", 10.5, "end", 600)
    return a


# =================================================================== 02 tensors

def res_tensors():
    a = Art("r02", "Every backward returns a gradient the shape of its input: a broadcast forward is a sum backward, "
                   "and a matrix multiply's backward is two more")
    cw, ch = 20, 18
    # broadcasting, forward
    a.text(24, 28, "broadcasting", size=12, weight=700)
    a.text(24, 48, "y = x + b", size=11.5, mono=True, weight=600)
    gy = 58
    for r in range(3):
        for c in range(4):
            a.box(24 + c * cw, gy + r * ch, cw, ch, "s f", rx=0)
            a.box(224 + c * cw, gy + r * ch, cw, ch, "s f", rx=0)
            a.box(124 + c * cw, gy + r * ch, cw, ch, "a af" if r == 0 else "m", rx=0, dash=r > 0)
    a.text(114, gy + 31, "+", size=14, anchor="middle", mono=True)
    a.text(214, gy + 31, "=", size=14, anchor="middle", mono=True)
    a.text(64, gy + 70, "x  [3, 4]", "tm", 10.5, "middle", mono=True)
    a.text(164, gy + 70, "b  [4]", "ta", 10.5, "middle", mono=True)
    a.text(264, gy + 70, "y  [3, 4]", "tm", 10.5, "middle", mono=True)
    a.text(164, gy + 85, "copied down the rows", "tm", 10, "middle")
    # broadcasting, backward
    dy = [[1, 0, 2, 1], [0, 1, 1, 0], [2, 1, 0, 1]]
    db = [sum(dy[r][c] for r in range(3)) for c in range(4)]
    a.text(24, 160, "backward", size=11.5, weight=700)
    by = 170
    for r in range(3):
        for c in range(4):
            cell(a, 24 + c * cw, by + r * ch, cw, ch, str(dy[r][c]), "s f", "t", 10.5, rx=0)
    a.text(64, by + 68, "y.grad  [3, 4]", "tm", 10.5, "middle", mono=True)
    a.path(f"M108 {by + 27} H 150", "a", arrow=True)
    a.text(130, by + 20, "sum(0)", "ta", 10, "middle", mono=True)
    for c in range(4):
        cell(a, 154 + c * cw, by + 18, cw, ch, str(db[c]), "a af", "ta", 10.5, rx=0, weight=700)
    a.text(194, by + 52, "b.grad  [4]", "ta", 10.5, "middle", mono=True)
    a.text(24, 254, "b was used in 3 rows, so its gradient adds up all 3", "tm", 10.5)

    # matrix multiply: rectangles drawn to scale, B = 3, in = 4, out = 2
    u = 9
    a.text(340, 28, "matrix multiply", size=12, weight=700)
    a.text(616, 28, "B: batch; in, out: layer sizes", "tm", 10, "end")
    rows = [("y = x @ W", 50, [("[B, in]", 4, 3, "s f"), ("[in, out]", 2, 4, "s f"), ("[B, out]", 2, 3, "s f")]),
            ("x.grad = y.grad @ W.T", 124, [("[B, out]", 2, 3, "s f"), ("[out, in]", 4, 2, "s f"), ("[B, in]", 4, 3, "a af")]),
            ("W.grad = x.T @ y.grad", 194, [("[in, B]", 3, 4, "s f"), ("[B, out]", 2, 3, "s f"), ("[in, out]", 2, 4, "a af")])]
    centres = [374, 448, 522]
    for title, ty, mats in rows:
        a.text(340, ty, title, "ta" if "grad" in title else "t", 11, mono=True, weight=600)
        top = ty + 8
        for k, (lab, w, hh, cls) in enumerate(mats):
            cx = centres[k]
            a.box(round(cx - w * u / 2, 1), top, w * u, hh * u, cls, rx=2)
            hot = cls.startswith("a")
            a.text(cx, top + 4 * u + 12, lab, "ta" if hot else "tm", 9.5, "middle", mono=True)
            if k < 2:
                a.text((cx + centres[k + 1]) / 2, top + 1.5 * u + 4, "@" if k == 0 else "=", size=12, anchor="middle",
                       mono=True)
        if ty > 100:
            a.text(566, top + 1.5 * u + 4, "<- shape of " + ("x" if ty < 150 else "W"), "ta", 10, weight=600)
    a.text(24, 272, "Each gradient has the shape of the tensor it belongs to: the first check on any backward.", "tm", 11)
    a.text(24, 288, "Every backward here is checked against PyTorch's gradients, to six decimal places.", "tm", 11)
    return a


# =================================================================== 03 optimisers

K03 = 25.0                                  # the valley: f(u, v) = (u^2 + K v^2) / 2


def opt_paths(start=(-4.4, 1.05), n=20):
    grad = lambda u, v: (u, K03 * v)
    out = {}
    u, v = start
    p = [(u, v)]
    for _ in range(n):
        gu, gv = grad(u, v)
        u, v = u - 0.07 * gu, v - 0.07 * gv
        p.append((u, v))
    out["sgd"] = p
    u, v = start
    bu = bv = 0.0
    p = [(u, v)]
    for _ in range(n):
        gu, gv = grad(u, v)
        bu, bv = 0.6 * bu + gu, 0.6 * bv + gv
        u, v = u - 0.06 * bu, v - 0.06 * bv
        p.append((u, v))
    out["momentum"] = p
    u, v = start
    m, s = [0.0, 0.0], [0.0, 0.0]
    p = [(u, v)]
    for t in range(1, n + 1):
        g = grad(u, v)
        for i in range(2):
            m[i] = 0.9 * m[i] + 0.1 * g[i]
            s[i] = 0.999 * s[i] + 0.001 * g[i] ** 2
        step = [0.25 * (m[i] / (1 - 0.9 ** t)) / (math.sqrt(s[i] / (1 - 0.999 ** t)) + 1e-8) for i in range(2)]
        u, v = u - step[0], v - step[1]
        p.append((u, v))
    out["adam"] = p
    return out


def res_optim():
    a = Art("r03", "Optimisers in a narrow valley: plain SGD zigzags across it, momentum adds up the push along it, "
                   "and Adam sizes each parameter's step on its own")
    paths = opt_paths()
    sc = 44
    a.text(24, 28, "a narrow valley, the same start, 20 steps each", "tm", 10.5)
    panels = [(40, ["sgd"], "SGD: zigzags across, crawls along"),
              (150, ["momentum", "adam"], "momentum, and Adam")]
    for top, names, title in panels:
        box = (24, top, 360, top + 96)
        ox, oy = 24 + 4.75 * sc, top + 48
        X = lambda u: ox + u * sc
        Y = lambda v: oy - v * sc
        for c in (0.2, 1.0, 2.8, 6, 11, 18, 28):
            rx, ry = math.sqrt(c), math.sqrt(c / K03)
            pts = [(X(rx * math.cos(2 * math.pi * k / 240)), Y(ry * math.sin(2 * math.pi * k / 240))) for k in range(241)]
            clipped(a, pts, box, "m")
        dot(a, X(0), Y(0), 2.5, "s fs")
        for name in names:
            pts = [(X(u), Y(v)) for u, v in paths[name]]
            cls = "a" if name == "adam" else "s"
            poly(a, pts, cls)
            for x, y in pts[1:]:
                dot(a, x, y, 1.8, "a fa" if name == "adam" else "s fs")
            dot(a, pts[0][0], pts[0][1], 3.2, "s f")
        a.text(360, top + 12, title, size=10.5, anchor="end", weight=700)
    u, v = paths["momentum"][-1]
    a.text(24 + 4.75 * sc + u * sc + 4, 150 + 48 + 22, "momentum", size=10, weight=600)
    u, v = paths["adam"][-1]
    a.text(24 + 4.75 * sc + u * sc + 8, 150 + 48 - v * sc - 10, "Adam", "ta", 10, weight=600)

    rx0 = 392
    rules = [("SGD", "s", ["w -= lr * g"]),
             ("momentum", "s", ["v = mu * v + g;  w -= lr * v"]),
             ("Adam", "a", ["m, v: running means of g and g^2,", "each corrected for starting at 0",
                            "w -= lr * m / (sqrt(v) + eps)"]),
             ("AdamW", "s", ["Adam, then  w -= lr * wd * w"])]
    y = 40
    for name, cls, lines in rules:
        a.text(rx0, y, name, "ta" if cls == "a" else "t", 11.5, weight=700)
        for k, ln in enumerate(lines):
            sans = ln.startswith("m, v") or ln.startswith("each")
            a.text(rx0, y + 16 + k * 15, ln, "tm" if sans else ("ta" if cls == "a" else "t"), 10.5, mono=not sans)
        y += 20 + 15 * len(lines)
    # warmup, then cosine decay
    gx0, gx1, gy0, gy1 = rx0 + 4, 604, 222, 254
    warm, T = 0.12, 1.0
    lr = lambda t: t / warm if t < warm else 0.5 * (1 + math.cos(math.pi * (t - warm) / (T - warm)))
    axes(a, gx0, gy0 - 4, gx1, gy1)
    poly(a, [(gx0 + t / 100 * (gx1 - gx0), gy1 - lr(t / 100) * (gy1 - gy0)) for t in range(101)], "s")
    a.text(rx0, 212, "the learning rate: warmup, then cosine decay", "tm", 10.5)
    a.text(24, 272, "Steep across, shallow along: a step small enough for the steep way crawls along the shallow way.",
           "tm", 11)
    a.text(24, 288, "Each optimiser is the fix for what you watched the one before it do.  (Paths computed here.)", "tm", 11)
    return a


# =================================================================== 04 deep networks

def layer_sizes(var, layers=50, width=64, batch=16, seed=0):
    """The RMS of each layer's output in a ReLU network at initialisation, weights ~ N(0, var / width)."""
    r = random.Random(seed)
    h = [[r.gauss(0, 1) for _ in range(width)] for _ in range(batch)]
    out = []
    for _ in range(layers):
        W = [[r.gauss(0, math.sqrt(var / width)) for _ in range(width)] for _ in range(width)]
        h = [[max(0.0, sum(wi[k] * hb[k] for k in range(width))) for wi in W] for hb in h]
        out.append(math.sqrt(sum(v * v for hb in h for v in hb) / (width * batch)))
    return out


def res_deep():
    a = Art("r04", "Fifty layers deep, a signal shrinks or blows up a little at every layer; the right initial size, "
                   "normalisation and shortcuts keep it the same")
    px0, px1, py0, py1 = 64, 352, 44, 214
    lo, hi = -8.5, 5.0
    L = 50
    X = lambda l: px0 + (l - 1) / (L - 1) * (px1 - px0)
    Y = lambda v: py1 - (math.log10(v) - lo) / (hi - lo) * (py1 - py0)
    axes(a, px0, py0 - 6, px1, py1)
    for e, lab in ((-8, "1e-8"), (-4, "1e-4"), (0, "1"), (4, "1e4")):
        a.line(px0 - 4, Y(10 ** e), px0, Y(10 ** e), "m")
        a.text(px0 - 8, Y(10 ** e) + 3.5, lab, "tm", 9.5, "end", mono=True)
    for l in (1, 10, 20, 30, 40, 50):
        a.line(X(l), py1, X(l), py1 + 4, "m")
        a.text(X(l), py1 + 16, str(l), "tm", 9.5, "middle", mono=True)
    a.text(px0, 30, "size of each layer's output (RMS), log scale", "tm", 10.5)
    a.text((px0 + px1) / 2, py1 + 32, "layer", "tm", 10.5, "middle")
    a.line(px0, Y(1), px1, Y(1), "m", dash=True)
    lines = [(3.0, "s", "N(0, 3/n)"), (2.0, "a", "N(0, 2/n)"), (1.0, "s", "N(0, 1/n)")]
    for var, cls, lab in lines:
        sizes = layer_sizes(var)
        poly(a, [(X(l + 1), Y(v)) for l, v in enumerate(sizes)], cls)
        factor = math.sqrt(var / 2)          # expected change of the RMS per layer
        y = Y(sizes[-1])
        a.text(px1 + 8, y - 2, lab, "ta" if cls == "a" else "t", 10.5, weight=600, mono=True)
        note = "holds (He)" if var == 2 else f"x{factor:.2f} a layer"
        a.text(px1 + 8, y + 12, note, "ta" if cls == "a" else "tm", 10)
    rx0 = 470
    a.text(rx0, 36, "three fixes", size=12, weight=700)
    fixes = [("1. the right starting size", ["w ~ N(0, 2 / fan_in)", "for ReLU: He et al."], [True, False]),
             ("2. normalise each layer", ["(h - mean) / std", "batch norm: over the batch", "layer norm: over features"],
              [True, False, False]),
             ("3. a shortcut", ["x + F(x)", "the gradient has a path", "that skips F"], [True, False, False])]
    y = 60
    for head, ls, mono in fixes:
        a.text(rx0, y, head, size=11, weight=700)
        for k, (ln, mo) in enumerate(zip(ls, mono)):
            a.text(rx0, y + 16 + k * 14, ln, "ta" if mo else "tm", 10.5 if mo else 10, mono=mo)
        y += 26 + 14 * len(ls) + 8
    a.text(24, 270, "Weights in a ReLU network, n inputs a layer: the variance 2/n keeps the size; a little less fades,",
           "tm", 11)
    a.text(24, 286, "a little more explodes. Gradients do the same going back.  (Lines computed here: 64 wide, at init.)",
           "tm", 11)
    return a


# =================================================================== 05 generalisation

def solve(A, b):
    """x with A x = b, by Gaussian elimination with partial pivoting."""
    n = len(A)
    M = [row[:] + [bb] for row, bb in zip(A, b)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        M[c], M[p] = M[p], M[c]
        for r in range(c + 1, n):
            f = M[r][c] / M[c][c]
            if f:
                Mr, Mc = M[r], M[c]
                for k in range(c, n + 1):
                    Mr[k] -= f * Mc[k]
    x = [0.0] * n
    for c in range(n - 1, -1, -1):
        x[c] = (M[c][n] - sum(M[c][k] * x[k] for k in range(c + 1, n))) / M[c][c]
    return x


def double_descent(n=40, d=10, ps=None, seeds=11, noise=0.3, ntest=120):
    """Test and train error of least squares on p random ReLU features (the minimum-norm fit once
    p >= n), the target a noisy linear function of d inputs, tested on fresh noisy points.
    The median over seeds, for each p."""
    test = {p: [] for p in ps}
    train = {p: [] for p in ps}
    P = max(ps)
    for s in range(seeds):
        r = random.Random(s)
        beta = [r.gauss(0, 1) / math.sqrt(d) for _ in range(d)]
        f = lambda x: sum(b * xi for b, xi in zip(beta, x))
        X = [[r.gauss(0, 1) for _ in range(d)] for _ in range(n)]
        Yv = [f(x) + r.gauss(0, noise) for x in X]
        T = [[r.gauss(0, 1) for _ in range(d)] for _ in range(ntest)]
        YT = [f(t) + r.gauss(0, noise) for t in T]
        W = [[r.gauss(0, 1) / math.sqrt(d) for _ in range(d)] for _ in range(P)]
        feats = lambda x: [max(0.0, sum(wi * xi for wi, xi in zip(w, x))) for w in W]
        FX, FT = [feats(x) for x in X], [feats(t) for t in T]
        for p in ps:
            Phi = [row[:p] for row in FX]
            if p < n:
                G = [[sum(Phi[i][j] * Phi[i][k] for i in range(n)) for k in range(p)] for j in range(p)]
                w = solve(G, [sum(Phi[i][j] * Yv[i] for i in range(n)) for j in range(p)])
            else:
                G = [[sum(Phi[i][k] * Phi[j][k] for k in range(p)) for j in range(n)] for i in range(n)]
                al = solve(G, Yv)
                w = [sum(Phi[i][k] * al[i] for i in range(n)) for k in range(p)]
            pred = lambda row: sum(wk * fk for wk, fk in zip(w, row))
            test[p].append(sum((pred(FT[i]) - YT[i]) ** 2 for i in range(ntest)) / ntest)
            train[p].append(sum((pred(FX[i]) - Yv[i]) ** 2 for i in range(n)) / n)
    med = lambda v: sorted(v)[len(v) // 2]
    return {p: (med(test[p]), med(train[p])) for p in ps}


def res_general():
    a = Art("r05", "Double descent: test error falls, peaks where the model has just enough parameters to fit every "
                   "training point, then falls again")
    n = 40
    ps = sorted(set([int(round(10 ** (k / 14))) for k in range(0, 37)] + list(range(30, 52, 2))))
    ps = [p for p in ps if p <= 400]
    dd = double_descent(n=n, ps=ps)
    test = lambda p: dd[p][0]
    assert all(dd[p][1] < 1e-9 for p in ps if p >= n)                  # past p = n it fits every point
    assert max(ps, key=test) in range(n - 2, n + 3)                     # the peak sits at p = n
    first = min(test(p) for p in ps if p < n)
    assert first < test(1) and test(max(ps)) < first                    # falls, peaks, falls lower
    px0, px1, py0, py1 = 40, 372, 52, 222
    ymax = 1.0
    X = lambda p: px0 + math.log10(p) / math.log10(max(ps)) * (px1 - px0)
    Y = lambda e: py1 - e / ymax * (py1 - py0)
    axes(a, px0, py0 - 10, px1, py1)
    a.text(px0, 34, "error", "tm", 10.5)
    a.text(px1, py1 + 18, "model size: features p, log scale", "tm", 10.5, "end")
    xn = X(n)
    a.line(xn, py0 - 10, xn, py1, "m", dash=True)
    a.text(xn + 6, py1 - 24, "p = n: just enough", "tm", 10)
    a.text(xn + 6, py1 - 11, "to fit every point", "tm", 10)
    # test error: drawn inside the frame; where it runs off the top, the gap is marked
    seg, out = [], []
    for p in ps:
        e = dd[p][0]
        if e <= ymax:
            seg.append((X(p), Y(e)))
        else:
            if seg:
                out.append(seg)
            seg = []
    out.append(seg)
    for s in out:
        if len(s) > 1:
            poly(a, s, "a")
    for s in out[:-1]:
        a.line(s[-1][0], s[-1][1], s[-1][0] + 4, py0 - 4, "a", arrow=True)
    a.line(out[-1][0][0] - 4, py0 - 4, out[-1][0][0], out[-1][0][1], "a")
    a.text(xn - 16, py0 - 2, "the peak runs", "ta", 10, "end")
    a.text(xn - 16, py0 + 11, "off the top", "ta", 10, "end")
    poly(a, [(X(p), Y(dd[p][1])) for p in ps], "s")
    a.text(X(2), Y(test(2)) - 9, "test", "ta", 11, weight=700)
    a.text(X(3), Y(dd[3][1]) + 18, "train", size=11, weight=700)
    a.text(X(max(ps)) - 2, Y(test(max(ps))) - 8, "test", "ta", 11, "end", 700)

    rx0 = 404
    blocks = [("random labels", ["the same network learns labels", "drawn at random: perfect on train,",
                                 "chance on test (Zhang et al. 2016)"]),
              ("what narrows the gap", ["weight decay, dropout, and more", "data, some of it made by", "augmenting what you have"]),
              ("so", ["train error says nothing about", "test error: only held-out data", "can tell them apart"])]
    y = 40
    for head, ls in blocks:
        a.text(rx0, y, head, size=11.5, weight=700)
        for k, ln in enumerate(ls):
            a.text(rx0, y + 16 + k * 14, ln, "tm", 10.5)
        y += 16 + 14 * len(ls) + 18
    a.text(24, 270, "Computed here: least squares on p random ReLU features of 10 inputs, n = 40 noisy training points,",
           "tm", 11)
    a.text(24, 286, "median of 11 seeds. Past p = n it takes the smallest-norm fit that passes through every point.",
           "tm", 11)
    return a


# =================================================================== 06 images

def res_conv():
    a = Art("r06", "A convolution uses the same few weights at every position; a residual block adds its input back, "
                   "so a deeper network is no longer worse")
    img = [[1 if c >= 3 else 0 for c in range(6)] for _ in range(6)]
    k = [[-1, 0, 1]] * 3
    out = [[sum(img[i + di][j + dj] * k[di][dj] for di in range(3) for dj in range(3)) for j in range(4)]
           for i in range(4)]
    assert [row for row in out] == [[0, 3, 3, 0]] * 4
    s = 20
    ix, iy = 24, 52
    a.text(24, 30, "image, 6 x 6", "tm", 10.5)
    for i in range(6):
        for j in range(6):
            cell(a, ix + j * s, iy + i * s, s, s, str(img[i][j]), "s fs" if img[i][j] else "s f", "t", 10, rx=0)
    wi, wj = 1, 1                      # the window drawn: rows 1-3, columns 1-3
    a.add(f'<rect class="a" x="{ix + wj * s}" y="{iy + wi * s}" width="{3 * s}" height="{3 * s}" stroke-width="2.5"/>')
    kx, ky = 186, 52
    a.text(kx, 30, "kernel: 9 weights", "ta", 10.5, weight=600)
    for i in range(3):
        for j in range(3):
            cell(a, kx + j * s, ky + i * s, s, s, str(k[i][j]), "a af", "ta", 10, rx=0, weight=600)
    ox, oy = 186, 140
    a.text(ox, 132, "output, 4 x 4", "tm", 10.5)
    for i in range(4):
        for j in range(4):
            hot = (i, j) == (wi, wj)
            cell(a, ox + j * s, oy + i * s, s, s, str(out[i][j]), "a af" if hot else "s f", "ta" if hot else "t", 10,
                 rx=0, weight=700 if hot else None)
    a.text(24, 196, "the outlined window times the", "tm", 10.5)
    a.text(24, 211, "kernel, added up: the outlined", "tm", 10.5)
    a.text(24, 226, f"output, {out[wi][wj]}; then slide one step", "tm", 10.5)
    a.text(24, 248, f"a dense layer, 36 in, 16 out: {36 * 16} weights;", size=10.5)
    a.text(24, 263, "this convolution: 9, shared by all 16", "ta", 10.5, weight=600)

    def blk(cx, y, w, label):
        a.box(cx - w / 2, y, w, 22, "s f", rx=5)
        a.text(cx, y + 15, label, "t", 10.5, "middle")
    for cx, res, name in ((392, False, "plain block"), (528, True, "residual block")):
        a.text(cx, 30, name, size=12, anchor="middle", weight=700)
        a.text(cx, 238, "x", size=12, anchor="middle", mono=True)
        a.line(cx, 226, cx, 208, arrow=True)
        blk(cx, 184, 116, "3x3 conv, BN, ReLU")
        a.line(cx, 184, cx, 164, arrow=True)
        blk(cx, 140, 116, "3x3 conv, BN")
        if res:
            a.line(cx, 140, cx, 124, arrow=True)
            plus(a, cx, 114)
            a.line(cx, 105, cx, 94, arrow=True)
            a.path(f"M{cx} 218 H {cx + 74} V 114 H {cx + 11}", "a", arrow=True)
            a.text(cx + 80, 170, "x", "ta", 11, mono=True, weight=600)
        else:
            a.line(cx, 140, cx, 94, arrow=True)
        blk(cx, 70, 60, "ReLU")
        a.line(cx, 70, cx, 52, arrow=True)
        a.text(cx, 46, "y", size=12, anchor="middle", mono=True)
    a.text(392, 262, "y = relu(F(x))", "tm", 10.5, "middle", mono=True)
    a.text(528, 262, "y = relu(F(x) + x)", "ta", 10.5, "middle", mono=True)
    a.text(24, 288, "He et al. 2015, CIFAR-10: a plain 56-layer network trains worse than a plain 20-layer one; "
                    "with shortcuts, 56 layers beat 20.", "tm", 10.5)
    return a


# =================================================================== 07 language models

def res_lm():
    a = Art("r07", "Language models from counting to attention: each guesses the next character from more of the past, "
                   "scored in bits of surprise")
    txt = "to be or not to b"
    nxt = "e"
    cw, ch, sx = 15, 20, 150
    a.text(sx, 30, "what each model can use to guess the next character", "tm", 10.5)
    rows = [("counts", "a bigram table", "how often each character", "follows 'b'"),
            ("embeddings", "and a network", "a fixed window: the last", "few characters"),
            ("recurrent", "network", "one state carried along:", "the far past fades"),
            ("attention", "", "looks back at every", "position, near or far")]
    n = len(txt)
    for r, (name, sub, d1, d2) in enumerate(rows):
        y = 44 + r * 50
        a.text(24, y + 14, name, size=11.5, weight=700)
        if sub:
            a.text(24, y + 29, sub, "tm", 10)
        for i, c in enumerate(txt):
            x = sx + i * cw
            back = n - 1 - i
            if r == 0:
                use = 1.0 if back == 0 else 0
            elif r == 1:
                use = 1.0 if back < 3 else 0
            elif r == 2:
                use = 0.85 ** back
            else:
                use = 0.35
            if use:
                shade(a, x, y, cw, ch, 0.5 * use)          # at most half strength, so the letter stays readable
            a.box(x, y, cw, ch, "a" if use == 1.0 else "m", rx=0)
            if not (r == 3 and i == txt.index("be") + 1):       # that cell is drawn below, in bold
                a.text(x + cw / 2, y + 14, "_" if c == " " else c, "t", 11, "middle", mono=True)
        cell(a, sx + n * cw + 6, y, cw + 2, ch, nxt, "a af", "ta", 11, rx=3, weight=700)
        a.text(452, y + 9, d1, "tm", 10.5)
        a.text(452, y + 23, d2, "tm", 10.5)
        if r == 3:
            i0 = txt.index("be") + 1                   # the 'e' that followed the first 'b'
            x0, x1 = sx + i0 * cw + cw / 2, sx + (n - 1) * cw + cw / 2
            a.path(f"M{x1} {y + ch + 2} C {x1} {y + ch + 18}, {x0} {y + ch + 18}, {x0} {y + ch + 4}", "a", arrow=True)
            a.text((x0 + x1) / 2, y + ch + 26, "last time 'b' came, 'e' followed", "ta", 10, "middle")
            shade(a, sx + i0 * cw, y, cw, ch, 0.5)
            a.add(f'<rect class="a" x="{sx + i0 * cw}" y="{y}" width="{cw}" height="{ch}" stroke-width="2"/>')
            a.text(sx + i0 * cw + cw / 2, y + 14, "e", "t", 11, "middle", 700, mono=True)
    a.text(sx + n * cw + 14, 30, "next", "ta", 10.5, "middle")
    a.text(24, 270, "score: -log2 p(the true next character), in bits, averaged; lower is better. '_' is a space.", "tm", 11)
    a.text(24, 286, f"Guessing evenly among Tiny Shakespeare's 65 characters scores log2 65 = {math.log2(65):.2f} bits.",
           "tm", 11)
    return a


# =================================================================== 08 transformer

def res_gpt():
    a = Art("r08", "A transformer block: causal attention moves information between positions, the MLP changes each "
                   "position in place, both added to the residual stream")
    toks = ["to", "be", "or", "not", "to", "be"]
    n = len(toks)
    r = random.Random(8)
    scores = [[r.gauss(0, 1.3) for _ in range(n)] for _ in range(n)]
    gx, gy, cw, ch = 84, 52, 32, 26
    a.text(gx, 30, "attention weights, row by row", "tm", 10.5)
    for j, t in enumerate(toks):
        a.text(gx + j * cw + cw / 2, gy - 6, t, "tm", 10.5, "middle", mono=True)
    for i in range(n):
        a.text(gx - 8, gy + i * ch + 17, toks[i], size=11, anchor="end", mono=True, weight=600)
        ex = [math.exp(scores[i][j]) for j in range(i + 1)]
        tot = sum(ex)
        w = [e / tot for e in ex]
        assert abs(sum(w) - 1) < 1e-12
        for j in range(n):
            x, y = gx + j * cw, gy + i * ch
            if j <= i:
                shade(a, x + 1, y + 1, cw - 2, ch - 2, 0.1 + 0.9 * w[j] ** 0.8)
            else:
                a.add(f'<rect class="fs" x="{x}" y="{y}" width="{cw}" height="{ch}"/>')
    for k in range(n + 1):
        a.line(gx + k * cw, gy, gx + k * cw, gy + n * ch, "m")
        a.line(gx, gy + k * ch, gx + n * cw, gy + k * ch, "m")
    a.text(gx + n * cw - 4, gy + 20, "masked:", "tm", 10, "end")
    a.text(gx + n * cw - 4, gy + 34, "the future", "tm", 10, "end")
    a.text(24, gy + n * ch + 22, "row i: how much position i takes from each", "tm", 10.5)
    a.text(24, gy + n * ch + 37, "earlier one; each row sums to 1", "tm", 10.5)
    a.text(24, gy + n * ch + 52, "(the shading here is illustrative)", "tm", 10)

    ys = 160
    a.text(316, 30, "one block, on the residual stream", "tm", 10.5)
    a.text(306, ys + 4, "x", size=12, anchor="end", mono=True)
    a.line(312, ys, 610, ys, "a", arrow=True)
    for bx, name, sub, note in ((318, "attention", "causal, n heads", "between positions"),
                                (466, "MLP", "4x wider", "each position alone")):
        a.path(f"M{bx} {ys} V 92 H {bx + 8}", "s")
        cell(a, bx + 8, 80, 30, 24, "ln", "s f", "t", 11, rx=6)
        a.line(bx + 38, 92, bx + 46, 92, "s")
        a.box(bx + 46, 72, 84, 40, "s fs", rx=8)
        a.text(bx + 88, 89, name, size=12, anchor="middle", weight=700)
        a.text(bx + 88, 104, sub, "tm", 10, "middle")
        px = bx + 140
        a.path(f"M{bx + 130} 92 H {px} V {ys - 10}", "s", arrow=True)
        plus(a, px, ys)
        a.text(bx + 88, 130, note, "ta", 10.5, "middle", 600)
    a.text(460, ys + 22, "residual stream: one vector per position", "ta", 10.5, "middle")
    a.text(300, 214, "attn(x) = softmax(q k.T / sqrt(d_head) + mask) v", size=10.5, mono=True)
    a.text(300, 230, "mask: -inf above the diagonal, 0 elsewhere", "tm", 10.5)
    a.text(24, 288, "x = x + attn(ln(x)), then x = x + mlp(ln(x)), once per block; the GPT is a stack of these.",
           "tm", 11)
    return a


# =================================================================== 09 GPT-2

def bpe(text, merges):
    """minbpe's training loop on the bytes of text: merge the most frequent pair, merges times."""
    ids = list(text.encode())
    vocab = {i: bytes([i]) for i in range(256)}
    steps = [list(ids)]
    rules = []
    for k in range(merges):
        counts = {}
        for p in zip(ids, ids[1:]):
            counts[p] = counts.get(p, 0) + 1
        pair = max(counts, key=counts.get)
        new = 256 + k
        out, i = [], 0
        while i < len(ids):
            if i < len(ids) - 1 and (ids[i], ids[i + 1]) == pair:
                out.append(new)
                i += 2
            else:
                out.append(ids[i])
                i += 1
        ids = out
        vocab[new] = vocab[pair[0]] + vocab[pair[1]]
        steps.append(list(ids))
        rules.append((pair, new, counts[pair]))
    return steps, rules, vocab


def res_gpt2():
    a = Art("r09", "The same tokens in, the same numbers out: byte pair encoding merges frequent pairs into new ids, "
                   "and the published GPT-2 weights run in your model")
    text = "the theme then"
    steps, rules, vocab = bpe(text, 3)
    show = lambda i: vocab[i].decode().replace(" ", "_")
    assert [show(i) for i in steps[-1]] == ["the", "_the", "m", "e", "_the", "n"]
    a.text(24, 30, "byte pair encoding, trained on one line", "tm", 10.5)
    cw, ch = 17, 22
    for r, ids in enumerate(steps):
        y = 44 + r * 46
        x = 24
        new = rules[r - 1][1] if r else None
        for i in ids:
            w = len(vocab[i]) * cw
            hot = i == new
            cell(a, x, y, w, ch, show(i), "a af" if hot else ("s f" if i < 256 else "s fs"), "ta" if hot else "t", 11,
                 rx=3, weight=700 if hot else None)
            x += w + 3
        if r:
            (p0, p1), new, cnt = rules[r - 1]
            a.text(x + 8, y + 15, f"{show(p0)} + {show(p1)} -> {new}", "ta", 10.5, weight=600, mono=True)
        else:
            a.text(x + 8, y + 15, f"{len(ids)} bytes", "tm", 10.5)
        if r < len(steps) - 1:
            a.text(24, y + ch + 15, f"merge {r + 1}: the most frequent pair becomes id {256 + r}", "tm", 10)
    a.text(24, 44 + 3 * 46 + ch + 16, f"{len(steps[0])} bytes -> {len(steps[-1])} tokens.  '_' is a space.", "tm", 10.5)

    px, pw = 440, 160
    stages = [("text", "s f", None, None), ("your GPT-2 tokenizer", "s fs", "ids", "= tiktoken's ids"),
              ("your GPT + GPT-2's weights", "s fs", "logits", "= the reference's"), ("logits  [T, 50257]", "s f", None, None)]
    a.text(px, 30, "held to the real thing", size=11.5, weight=700)
    for k, (name, cls, what, check) in enumerate(stages):
        y = 44 + k * 56
        cell(a, px, y, pw, 26, name, cls, "t", 10.5, rx=6, weight=600, mono=False)
        if k < len(stages) - 1:
            a.line(px + 40, y + 26, px + 40, y + 54, "s", arrow=True)
        if check:
            a.text(px + 48, y + 44, what, "tm", 10, mono=True)
            a.text(px + 48 + 7 * len(what), y + 44, check, "ta", 10.5, weight=600)
    a.text(24, 270, "GPT-2's vocabulary: 256 bytes + 50,000 merges + 1 end-of-text token = 50,257 ids.", "tm", 11)
    a.text(24, 286, "Its weights load from the published model.safetensors, GPT-2 small, 124M parameters.", "tm", 11)
    assert 256 + 50000 + 1 == 50257
    return a


# =================================================================== 10 today's architecture

def res_modern():
    a = Art("r10", "Today's architecture: four pieces of GPT-2 replaced one paper at a time, each tested against "
                   "the piece it replaced")
    x0, x1, x2 = 24, 112, 300
    a.text(x1, 30, "GPT-2, 2019", size=11.5, weight=700)
    a.text(x2, 30, "open models now", "ta", 11.5, weight=700)
    rows = [("norm", "LayerNorm", "(x - mean) / std * g + b", "RMSNorm", "x / rms(x) * g"),
            ("position", "learned, added once", "x = tok_emb + pos_emb", "rotary (RoPE)", "turn q, k by m * theta"),
            ("MLP", "GELU", "W2 gelu(W1 x)", "SwiGLU", "W2 (silu(W1 x) * W3 x)"),
            ("attention", "each head its own k, v", "12 q heads, 12 k, v", "grouped-query", "q heads share k, v")]
    for k, (piece, old, oldf, new, newf) in enumerate(rows):
        y = 58 + k * 48
        if k:
            a.line(x0, y - 18, 450, y - 18, "m")
        a.text(x0, y, piece, size=11.5, weight=700)
        a.text(x1, y, old, size=10.5)
        a.text(x1, y + 16, oldf, "tm", 10.5, mono=True)
        a.line(x2 - 26, y + 4, x2 - 8, y + 4, "a", arrow=True)
        a.text(x2, y, new, "ta", 10.5, weight=600)
        a.text(x2, y + 16, newf, "ta", 10.5, mono=True)
    a.text(x2, 58 + 3 * 48 + 31, "SmolLM2-135M: 9 q heads on 3", "tm", 10)

    cx, cy, R = 534, 118, 52
    a.text(470, 30, "rotary, one pair of dims", size=11.5, weight=700)
    a.circle(cx, cy, R, "m")
    a.line(cx - R - 6, cy, cx + R + 6, cy, "m")
    a.line(cx, cy - R - 6, cx, cy + R + 6, "m")
    th = math.radians(28)
    for m in range(4):
        ang = m * th
        ex, ey = cx + (R - 4) * math.cos(ang), cy - (R - 4) * math.sin(ang)
        a.line(cx, cy, round(ex, 1), round(ey, 1), "a" if m in (0, 3) else "s", arrow=True)
        lx, ly = cx + (R + 11) * math.cos(ang), cy - (R + 11) * math.sin(ang)
        a.text(round(lx, 1), round(ly + 4, 1), str(m), "ta" if m in (0, 3) else "tm", 10.5, "middle", 600, mono=True)
    a.path(f"M{cx + 22} {cy} A 22 22 0 0 0 {cx + 22 * math.cos(th):.1f} {cy - 22 * math.sin(th):.1f}", "s")
    a.text(cx + 14, cy + 16, "theta", "tm", 9.5, mono=True)
    a.text(470, 196, "the same q at positions 0 to 3:", "tm", 10)
    a.text(470, 210, "position m turns it by m * theta,", "tm", 10)
    a.text(470, 224, "so q . k depends only on how far", "tm", 10)
    a.text(470, 238, "apart q's and k's positions are", "tm", 10)
    a.text(24, 270, "Each change goes in alone, same parameter count, several seeds; then a current open model's",
           "tm", 11)
    a.text(24, 286, "weights load into the result and give the reference's logits.", "tm", 11)
    return a


# =================================================================== 11 fast

def res_fast():
    a = Art("r11", "Fast: the yardstick is the time to reach a target loss; four changes each make the same loss "
                   "arrive sooner")
    px0, px1, py0, py1 = 48, 352, 48, 214
    loss = lambda s: 1.0 + 3.0 / (1 + s / 200) ** 0.8         # an illustrative loss-per-step curve
    steps, slow, fast = 2000, 1.0, 0.4
    tmax = steps * slow
    X = lambda t: px0 + t / tmax * (px1 - px0)
    Y = lambda L: py1 - (L - 0.8) / 3.4 * (py1 - py0)
    axes(a, px0, py0 - 8, px1, py1)
    a.text(px0, 36, "validation loss", "tm", 10.5)
    a.text(px1, py1 + 18, "wall-clock time", "tm", 10.5, "end")
    poly(a, [(X(s * slow), Y(loss(s))) for s in range(0, steps + 1, 20)], "s")
    poly(a, [(X(s * fast), Y(loss(s))) for s in range(0, int(steps * slow / fast) + 1, 20) if s * fast <= tmax], "a")
    target = 1.6
    s_hit = 200 * ((3.0 / (target - 1.0)) ** (1 / 0.8) - 1)
    assert abs(loss(s_hit) - target) < 1e-9
    a.line(px0, Y(target), px1, Y(target), "m", dash=True)
    a.text(px1, Y(target) - 6, "target loss", "tm", 10, "end")
    for sp, cls, lab in ((fast, "a", "after"), (slow, "s", "before")):
        t = X(s_hit * sp)
        a.line(t, Y(target), t, py1, cls, dash=True)
        dot(a, t, Y(target), 3.5, "a fa" if cls == "a" else "s f")
        a.text(t, py1 + 18, lab, "ta" if cls == "a" else "t", 10.5, "middle", 600)
    a.text(X(s_hit * fast) - 30, Y(2.9), "after: the same loss per step,", "ta", 10.5)
    a.text(X(s_hit * fast) - 30, Y(2.9) + 14, "in less time per step", "ta", 10.5)
    a.text(24, 256, "speedup = time before / time after, each the median of several runs", "tm", 10.5)

    rx0 = 384
    a.text(rx0, 30, "four changes, each measured", size=11.5, weight=700)
    items = [("fused attention", "softmax in tiles: no T x T matrix"),
             ("16-bit numbers", "bf16 keeps fp32's range; fp16 needs loss scaling"),
             ("bigger batches", "sum the gradients of k batches, one step"),
             ("one of your own", "kept only if the time to target falls")]
    for k, (head, sub) in enumerate(items):
        y = 52 + k * 34
        a.text(rx0, y, head, size=11, weight=600)
        a.text(rx0, y + 15, sub, "tm", 10)
    fmts = [("fp32", 1, 8, 23), ("bf16", 1, 8, 7), ("fp16", 1, 5, 10)]
    bw = 6
    for k, (name, sgn, ex, man) in enumerate(fmts):
        y = 196 + k * 18
        a.text(rx0, y + 10, name, size=10, mono=True, weight=600)
        x = rx0 + 34
        for n, cls in ((sgn, "s f"), (ex, "a af"), (man, "s fs")):
            a.box(x, y, n * bw * 0.85, 13, cls, rx=1)
            x += n * bw * 0.85
        a.text(x + 5, y + 10, f"{sgn}+{ex}+{man}", "tm", 9.5, mono=True)
    a.text(rx0, 188, "bits: sign, exponent (range), mantissa", "tm", 9.5)
    a.text(24, 288, "Profile one step first, then change one thing at a time and measure it the same way.", "tm", 11)
    return a


# =================================================================== 12 fine-tuning

def res_finetune():
    a = Art("r12", "Fine-tuning: keep the pretrained weights frozen and train a little beside them, a new head or a "
                   "LoRA update W + B A of low rank")
    a.text(24, 30, "GPT-2, pretrained", size=11.5, weight=700)
    x, w = 40, 150
    cell(a, x, 44, w, 24, "new head: classes", "a af", "ta", 10.5, rx=5, weight=700, mono=False)
    a.line(x + w / 2, 84, x + w / 2, 70, "s", arrow=True)
    for k in range(12):
        y = 86 + k * 12
        a.box(x, y, w, 9, "s fs", rx=2)
        a.box(x + w + 4, y, 14, 9, "a af", rx=2)
    a.text(x + w / 2, 248, "12 blocks, frozen", "tm", 10.5, "middle")
    a.text(x + w + 26, 140, "LoRA", "ta", 10.5, weight=600)
    a.text(x + w + 26, 154, "adapters", "ta", 10.5)
    a.text(x + w / 2, 264, "only the accent trains", "ta", 10.5, "middle", 600)

    d, rk = 768, 8
    frozen, trained = d * d, 2 * rk * d
    cx = 330
    a.text(cx, 30, "LoRA, one weight matrix", size=11.5, weight=700)
    a.text(cx + 76, 248, "x", size=12, anchor="middle", mono=True)
    a.path(f"M{cx + 76} 236 V 226 H {cx + 40} V 212", "s", arrow=True)
    a.path(f"M{cx + 76} 226 H {cx + 126} V 212", "s", arrow=True)
    a.box(cx, 104, 80, 106, "s fs", rx=6)
    a.text(cx + 40, 146, "W", size=14, anchor="middle", mono=True, weight=700)
    a.text(cx + 40, 164, "frozen", "tm", 10.5, "middle")
    a.text(cx + 40, 180, f"{d} x {d}", "tm", 9.5, "middle", mono=True)
    cell(a, cx + 100, 182, 52, 28, "", "a af")
    a.text(cx + 126, 195, "A", "ta", 12, "middle", 700, mono=True)
    a.text(cx + 126, 206, f"{rk} x {d}", "ta", 8, "middle", mono=True)
    a.line(cx + 126, 182, cx + 126, 154, "a", arrow=True)
    cell(a, cx + 100, 124, 52, 28, "", "a af")
    a.text(cx + 126, 137, "B", "ta", 12, "middle", 700, mono=True)
    a.text(cx + 126, 148, f"{d} x {rk}", "ta", 8, "middle", mono=True)
    a.path(f"M{cx + 40} 104 V 76 H {cx + 65}", "s", arrow=True)
    a.path(f"M{cx + 126} 124 V 76 H {cx + 87}", "a", arrow=True)
    plus(a, cx + 76, 76)
    a.line(cx + 76, 67, cx + 76, 46, arrow=True)
    a.text(cx + 86, 54, "h", size=12, mono=True)
    rx0 = 498
    a.text(rx0, 64, "h = W x + B A x", size=11, mono=True, weight=600)
    a.text(rx0, 84, "B starts at zero, so at", "tm", 10.5)
    a.text(rx0, 98, "step 0 it is the model", "tm", 10.5)
    a.text(rx0, 112, "you started from", "tm", 10.5)
    a.text(rx0, 140, f"W: {frozen:,} frozen", size=10.5, mono=True)
    a.text(rx0, 156, f"A, B: {trained:,}", "ta", 10.5, mono=True, weight=600)
    a.text(rx0, 172, f"trained, {100 * trained / frozen:.1f}% of W", "ta", 10.5)
    a.text(rx0, 196, f"rank r = {rk} here", "tm", 10.5)
    a.text(24, 288, "Evaluate before and after: on the new task, and on what the model could already do.", "tm", 11)
    return a


# =================================================================== 13 experiments

def res_rigour():
    a = Art("r13", "A result that holds up survives four attacks: a baseline tuned as hard, the spread over seeds, "
                   "a cheat the evaluation must catch, and a prediction made before the run")
    pw, py0, py1 = 132, 46, 166
    xs = [24, 178, 332, 486]
    heads = ["a fair baseline", "error bars", "an evaluation", "predict, then run"]
    descs = [["tune the baseline's", "learning rate as hard", "as your own method's"],
             ["is the gap bigger", "than the spread", "between seeds?"],
             ["a cheat that should", "fail, such as the most", "common answer, must"],
             ["fit loss against size", "on small models, then", "train a bigger one"]]
    for x0, head, ds in zip(xs, heads, descs):
        a.text(x0, py1 + 30, head, size=12, weight=700)
        for k, ln in enumerate(ds):
            a.text(x0, py1 + 47 + k * 14, ln, "tm", 10.5)
    a.text(xs[2], py1 + 47 + 3 * 14, "score near chance", "tm", 10.5)

    # 1: two learning-rate sweeps, U shapes; at your method's best lr the baseline looks bad
    x0 = xs[0]
    axes(a, x0, py0 - 6, x0 + pw, py1)
    X = lambda t: x0 + 6 + t * (pw - 12)
    Y = lambda L: py1 - 8 - L * (py1 - py0 - 16)                     # loss: lower is better, drawn lower
    base = lambda t: min(1.0, 0.20 + 2.6 * (t - 0.36) ** 2)
    mine = lambda t: min(1.0, 0.14 + 2.6 * (t - 0.66) ** 2)
    poly(a, [(X(k / 60), Y(base(k / 60))) for k in range(61)], "s")
    poly(a, [(X(k / 60), Y(mine(k / 60))) for k in range(61)], "a")
    a.line(X(0.66), py0 - 4, X(0.66), py1, "m", dash=True)
    dot(a, X(0.66), Y(base(0.66)), 3, "s f")
    dot(a, X(0.36), Y(base(0.36)), 3, "s fs")
    dot(a, X(0.66), Y(mine(0.66)), 3, "a fa")
    a.text(x0 + 4, py0 - 10, "loss", "tm", 10)
    a.text(x0 + pw, py1 + 12, "learning rate", "tm", 9.5, "end")
    a.text(X(0.36), Y(base(0.36)) + 16, "baseline", size=9.5, anchor="middle")
    a.text(X(0.66) + 7, Y(mine(0.66)) + 14, "yours", "ta", 9.5)

    # 2: five seeds each, mean and spread
    x0 = xs[1]
    axes(a, x0, py0 - 6, x0 + pw, py1)
    Yv = lambda v: py1 - 10 - v * (py1 - py0 - 20)
    groups = [("baseline", [0.32, 0.45, 0.52, 0.40, 0.58], "s"), ("yours", [0.44, 0.60, 0.50, 0.72, 0.55], "a")]
    for g, (lab, vals, cls) in enumerate(groups):
        cx = x0 + 36 + g * 60
        m = sum(vals) / len(vals)
        sd = math.sqrt(sum((v - m) ** 2 for v in vals) / (len(vals) - 1))
        for j, v in enumerate(vals):
            dot(a, cx - 14 + j * 5, Yv(v), 2.6, "a af" if cls == "a" else "s f")
        bx = cx + 16
        a.line(bx, Yv(m - sd), bx, Yv(m + sd), cls)
        a.line(bx - 4, Yv(m - sd), bx + 4, Yv(m - sd), cls)
        a.line(bx - 4, Yv(m + sd), bx + 4, Yv(m + sd), cls)
        dot(a, bx, Yv(m), 3.2, "a fa" if cls == "a" else "s fs")
        a.text(cx, py1 + 12, lab, "ta" if cls == "a" else "t", 9.5, "middle")
    a.text(x0 + 4, py0 - 10, "score, 5 seeds", "tm", 10)

    # 3: the cheat scores near chance, or the evaluation is broken
    x0 = xs[2]
    axes(a, x0, py0 - 6, x0 + pw, py1)
    bars = [("yours", 0.78, "a af"), ("cheat", 0.16, "m fs")]
    for k, (lab, v, cls) in enumerate(bars):
        bx = x0 + 22 + k * 56
        h = v * (py1 - py0 - 10)
        a.box(bx, py1 - h, 34, h, cls, rx=2, dash=lab == "cheat")
        a.text(bx + 17, py1 + 12, lab, "ta" if k == 0 else "tm", 9.5, "middle")
    chance = py1 - 0.16 * (py1 - py0 - 10)
    a.line(x0, chance, x0 + pw, chance, "m", dash=True)
    a.text(x0 + pw, chance - 5, "chance", "tm", 9.5, "end")
    a.text(x0 + 4, py0 - 10, "score", "tm", 10)

    # 4: a power law is a straight line on log-log axes; fit the small ones, predict the next
    x0 = xs[3]
    axes(a, x0, py0 - 6, x0 + pw, py1)
    LX = lambda t: x0 + 8 + t * (pw - 16)
    LY = lambda t: py0 + 8 + t * (py1 - py0 - 16)
    fit = [0.06, 0.22, 0.38, 0.54]
    for t in fit:
        dot(a, LX(t), LY(t * 0.9), 3, "s fs")
    a.line(LX(0.0), LY(0.0), LX(0.95), LY(0.95 * 0.9), "s", dash=True)
    dot(a, LX(0.9), LY(0.9 * 0.9), 4.5, "s f")
    dot(a, LX(0.9), LY(0.9 * 0.9) + 3, 3, "a fa")
    a.text(LX(0.9) - 10, LY(0.81) + 6, "predicted, then run", "ta", 9.5, "end")
    a.text(x0 + 4, py0 - 10, "loss, log", "tm", 10)
    a.text(x0 + pw, py1 + 12, "parameters, log", "tm", 9.5, "end")
    a.text(24, 288, "Schematics, no measured numbers. A power law L = (N_c / N)^alpha is a straight line on log-log axes.",
           "tm", 10.5)
    return a


# =================================================================== 14 grokking

def res_grok():
    a = Art("r14", "Grokking, the figure to reproduce: train accuracy saturates early, validation jumps much later")
    px0, px1, py0, py1 = 72, 440, 52, 212
    X = lambda lg: px0 + (lg - 1) / 5 * (px1 - px0)
    Y = lambda acc: py1 - acc * (py1 - py0)
    a.line(px0, py1, px1, py1, "m"); a.line(px0, py1, px0, py0 - 4, "m")
    for e in range(1, 7):
        a.line(X(e), py1, X(e), py1 + 4, "m")
        a.text(X(e), py1 + 18, f"1e{e}", "tm", 10, "middle", mono=True)
    for acc, lab in ((0, "0%"), (0.5, "50%"), (1, "100%")):
        a.text(px0 - 8, Y(acc) + 4, lab, "tm", 10, "end", mono=True)
    a.line(px0, Y(1), px1, Y(1), "m", dash=True)
    a.text(px0 + (px1 - px0) / 2, py1 + 36, "optimization steps, log scale", "tm", 10.5, "middle")
    a.text(24, 30, "accuracy", "tm", 10.5)

    def logistic(c, k, lo):
        return [(X(lg), Y(lo + (1 - lo) / (1 + math.exp(-k * (lg - c))))) for lg in [1 + i * 0.05 for i in range(101)]]
    poly(a, logistic(2.5, 9, 0.01), "s")
    poly(a, logistic(5.35, 10, 0.01), "a")
    a.text(X(2.5) + 10, Y(0.42), "train", size=11, weight=600)
    a.text(X(5.35) + 10, Y(0.42), "validation", "ta", 11, weight=600)
    # the paper: train accuracy near perfect before 1e3 steps, validation near perfect only close to 1e6
    a.path(f"M{X(3):.1f} 38 H {X(6) - 2:.1f}", "m", arrow=True)
    a.text((X(3) + X(6)) / 2, 32, "about 1000x more steps", "tm", 10.5, "middle")
    rx = 470
    a.text(rx, 64, "reproduce it", size=12, weight=700)
    for i, t in enumerate(["division mod 97", "train on 50% of the pairs", "the same optimizer and", "weight decay as the paper"]):
        a.text(rx, 86 + i * 17, t, "tm", 10.5)
    a.text(rx, 172, "Does the jump appear,", size=11, weight=600)
    a.text(rx, 188, "and at which step?", size=11, weight=600)
    a.text(24, 284, "After Power et al. 2022, Figure 1. A schematic: your own run produces the real curve.", "tm", 10.5)
    return a


# =================================================================== 15 your own result

def res_result():
    a = Art("r15", "Your own result: a loop of question, prediction, experiment and doubt, and a way out to a public write-up")
    nodes = {"Q": (40, 46, "a small question"), "P": (230, 46, "a prediction"), "E": (230, 146, "the experiment"),
             "D": (40, 146, "try to break it")}
    for _, (x, y, t) in nodes.items():
        a.box(x, y, 130, 36, "s f", rx=18)
        a.text(x + 65, y + 23, t, size=12, anchor="middle", weight=600)
    a.line(170, 64, 228, 64, arrow=True)
    a.line(295, 82, 295, 144, arrow=True)
    a.line(230, 164, 172, 164, arrow=True)
    a.line(105, 146, 105, 84, "m", arrow=True)
    a.text(114, 120, "it breaks: refine", "tm", 10.5)
    a.path("M105 182 V 236 H 396 V 104 H 416", "a", arrow=True)
    a.text(250, 228, "it survives: write it up", "ta", 11, "middle", 600)
    a.box(420, 30, 100, 140, "s f", rx=6)
    a.add(f'<rect class="s fs" x="432" y="42" width="76" height="9" rx="2" {SW}/>')
    for y in (62, 71, 80):
        a.line(432, y, 508, y, "m")
    a.line(436, 128, 436, 92, "m"); a.line(436, 128, 504, 128, "m")
    poly(a, [(440, 122), (452, 116), (464, 117), (476, 106), (488, 101), (500, 96)], "s")
    for y in (142, 151, 160):
        a.line(432, y, 508 if y < 160 else 480, y, "m")
    a.text(470, 188, "paper", size=12, anchor="middle", weight=700)
    a.box(540, 30, 76, 140, "s fs", rx=6)
    for i, t in enumerate(["repo/", "README", "data/", "train.py", "plots.py", "Makefile"]):
        a.text(550, 52 + i * 19, t, "t" if i == 0 else "tm", 10.5, weight=600 if i == 0 else None, mono=True)
    a.text(578, 188, "code", size=12, anchor="middle", weight=700)
    a.text(420, 222, "$ make reproduce", size=11, mono=True, weight=600)
    a.text(420, 238, "rebuilds every number and figure", "tm", 10.5)
    a.text(24, 284, "Small, finished and public beats big and half done.", "tm", 11)
    return a


# =================================================================== 16 looking inside

def res_inside():
    a = Art("r16", "Looking inside a trained network: read a fact from its activations with a probe, find which part "
                   "did the work by patching, split activations into features with a sparse autoencoder")
    xs = [24, 230, 436]
    heads = ["probe: is it there?", "patch: which part did it?", "sparse autoencoder"]
    for x0, h in zip(xs, heads):
        a.text(x0, 30, h, size=12, weight=700)
    # probe
    x0 = xs[0]
    hv = [0.7, 0.2, 0.9, 0.4, 0.1, 0.6, 0.3, 0.8]
    for k, v in enumerate(hv):
        shade(a, x0 + 8, 48 + k * 16, 22, 16, v, "t")
        a.box(x0 + 8, 48 + k * 16, 22, 16, "s", rx=0)
    a.text(x0 + 19, 192, "h", size=12, anchor="middle", mono=True, weight=600)
    a.text(x0 + 19, 206, "layer k", "tm", 10, "middle")
    for k in range(8):
        a.line(x0 + 32, 56 + k * 16, x0 + 96, 112, "m")
    cell(a, x0 + 98, 98, 64, 28, "w . h", "a af", "ta", 11, rx=6, weight=700)
    a.line(x0 + 162, 112, x0 + 178, 112, "a", arrow=True)
    a.text(x0 + 100, 146, "yes / no", "ta", 10.5, weight=600)
    a.text(x0, 228, "a linear classifier on the", "tm", 10.5)
    a.text(x0, 242, "activations; if it is right on", "tm", 10.5)
    a.text(x0, 256, "new inputs, the fact is there", "tm", 10.5)
    # patching
    x0 = xs[1]
    for r, lab in enumerate(("clean input", "corrupted input")):
        y = 58 + r * 74
        a.text(x0, y - 8 if r == 0 else y + 42, lab, "tm", 10)
        for k in range(4):
            bx = x0 + k * 34
            a.box(bx, y, 24, 26, "a af" if k == 1 else "s fs", rx=4)
            if k < 3:
                a.line(bx + 24, y + 13, bx + 33, y + 13, "s")
        a.line(x0 + 3 * 34 + 24, y + 13, x0 + 3 * 34 + 36, y + 13, "s", arrow=True)
        if r == 0:
            cell(a, x0 + 140, y + 1, 24, 24, "A", "s f", "t", 12, rx=4, weight=700)
        else:
            cell(a, x0 + 140, y + 1, 24, 24, "A", "a af", "ta", 12, rx=4, weight=700)
            a.text(x0 + 152, y + 42, "was B", "tm", 10, "middle")
    a.path(f"M{x0 + 46} 84 V 130", "a", arrow=True)
    a.text(x0 + 52, 110, "copy this one", "ta", 10.5, weight=600)
    a.text(x0, 228, "copy one activation from the clean", "tm", 10.5)
    a.text(x0, 242, "run into the corrupted one; if the", "tm", 10.5)
    a.text(x0, 256, "answer comes back, it carried it", "tm", 10.5)
    # sparse autoencoder
    x0 = xs[2]
    d, m = 4, 12
    on = {2, 7, 10}
    for k in range(d):
        a.box(x0 + 4, 64 + k * 22, 18, 18, "s fs", rx=2)
        a.box(x0 + 162, 64 + k * 22, 18, 18, "s fs", rx=2)
    for k in range(m):
        y = 44 + k * 12
        a.box(x0 + 82, y, 22, 9, "a af" if k in on else "m", rx=1, dash=k not in on)
    a.path(f"M{x0 + 24} 64 L {x0 + 78} 44 M{x0 + 24} 148 L {x0 + 78} 184", "m")
    a.path(f"M{x0 + 108} 44 L {x0 + 158} 64 M{x0 + 108} 184 L {x0 + 158} 148", "m")
    a.text(x0 + 13, 162, "h", size=12, anchor="middle", mono=True, weight=600)
    a.text(x0 + 93, 202, "f", "ta", 12, "middle", 700, mono=True)
    a.text(x0 + 171, 162, "h'", size=12, anchor="middle", mono=True, weight=600)
    a.text(x0 + 93, 216, "many features, few on", "ta", 10, "middle")
    a.text(x0, 232, "loss: rebuild h, with few f on", "tm", 10.5)
    a.text(x0, 248, "|h - h'|^2 + lambda |f|_1", size=10.5, mono=True)
    a.text(x0, 263, "more features than dimensions", "tm", 10.5)
    a.text(24, 288, "Then the network that grokked in module 14: find its algorithm, and confirm it by breaking it.", "tm", 11)
    return a


# =================================================================== 17 diffusion

def res_diffusion():
    a = Art("r17", "Diffusion: noise is added to an image step by step by a fixed rule, and a network learns to "
                   "predict that noise so it can be removed step by step")
    T = 1000
    betas = [1e-4 + (0.02 - 1e-4) * k / (T - 1) for k in range(T)]   # Ho et al. 2020, linear
    abar, p = [1.0], 1.0
    for b in betas:
        p *= 1 - b
        abar.append(p)
    ring = [[1 if 2.0 <= math.hypot(i - 3.5, j - 3.5) <= 3.4 else -1 for j in range(8)] for i in range(8)]
    r = random.Random(17)
    eps = [[r.gauss(0, 1) for _ in range(8)] for _ in range(8)]
    ts = [0, 100, 250, 500, 1000]
    px, s, gap = 30, 8, 52
    a.text(24, 30, "forward: a fixed rule adds a little Gaussian noise at every step; nothing is learned", "tm", 10.5)
    for k, t in enumerate(ts):
        x0 = px + k * (8 * s + gap)
        sa, sb = math.sqrt(abar[t]), math.sqrt(1 - abar[t])
        for i in range(8):
            for j in range(8):
                v = sa * ring[i][j] + sb * eps[i][j]
                shade(a, x0 + j * s, 46 + i * s, s, s, (v + 1) / 2, "t")
        a.box(x0, 46, 8 * s, 8 * s, "s", rx=0)
        a.text(x0 + 4 * s, 128, f"t = {t}", size=10.5, anchor="middle", mono=True, weight=600)
        if k < len(ts) - 1:
            a.line(x0 + 8 * s + 6, 66, x0 + 8 * s + gap - 6, 66, "s", arrow=True)
            a.line(x0 + 8 * s + gap - 6, 92, x0 + 8 * s + 6, 92, "a", arrow=True)
    a.text(px + 4 * s, 142, "x_0, the image", "tm", 10, "middle")
    a.text(px + 4 * (8 * s + gap) + 4 * s, 142, "x_T: pure noise", "tm", 10, "middle")
    a.text(24, 164, "reverse: a network predicts the noise in x_t; each step removes some of it", "ta", 10.5, weight=600)
    rows = [("noise to step t", "x_t = sqrt(abar_t) x_0 + sqrt(1 - abar_t) eps,  eps ~ N(0, I)"),
            ("train", "loss = | eps - eps_theta(x_t, t) |^2"),
            ("sample", "from pure noise, T steps back; DDIM: deterministic, far fewer"),
            ("guidance", "eps = eps_uncond + w (eps_class - eps_uncond)")]
    for k, (lab, f) in enumerate(rows):
        y = 190 + k * 18
        a.text(24, y, lab, "tm", 10.5)
        a.text(124, y, f, size=10.5, mono=not lab == "sample")
    a.text(24, 288, "Noise schedule of Ho et al. 2020: beta from 1e-4 to 0.02 over T = 1000 steps; the images are computed with it.",
           "tm", 10.5)
    return a


# =================================================================== 18 reward

def res_reward():
    a = Art("r18", "Learning from reward: an agent acts, the environment answers with a reward, and PPO clips how far "
                   "one update may move the policy")
    # the loop
    bx, bw = 98, 170
    cell(a, bx, 36, bw, 34, "agent: a policy network", "s fs", "t", 11, rx=8, weight=700, mono=False)
    a.box(bx, 132, bw, 96, "s f", rx=8)
    a.text(bx + 12, 150, "environment", size=11, weight=700)
    mid = bx + bw / 2
    a.line(bx + 20, 210, bx + bw - 20, 210, "m")
    a.box(mid - 18, 194, 36, 16, "s fs", rx=3)
    a.circle(mid - 10, 214, 3.5, "s f"); a.circle(mid + 10, 214, 3.5, "s f")
    ang = math.radians(14)
    tx, ty = mid + 58 * math.sin(ang), 194 - 58 * math.cos(ang)
    a.add(f'<line class="a" x1="{mid}" y1="194" x2="{tx:.1f}" y2="{ty:.1f}" stroke-width="4" stroke-linecap="round"/>')
    a.path(f"M{bx + bw + 6} 53 H {bx + bw + 24} V 172 H {bx + bw + 4}", "s", arrow=True)
    a.text(bx + bw + 30, 104, "action:", "tm", 10.5)
    a.text(bx + bw + 30, 119, "push left", size=10.5, mono=True)
    a.text(bx + bw + 30, 133, "or right", size=10.5, mono=True)
    a.path(f"M{bx - 6} 172 H {bx - 24} V 53 H {bx - 6}", "s", arrow=True)
    a.text(bx - 30, 108, "state,", "tm", 10.5, "end")
    a.text(bx - 30, 123, "reward", "tm", 10.5, "end")
    a.text(24, 248, "state: cart position and speed, pole angle and spin", "tm", 10.5)
    a.text(24, 263, "reward: +1 for every step the pole stays up", "ta", 10.5, weight=600)

    # PPO's clipped objective, as a function of the probability ratio r, for A > 0 and A < 0
    e = 0.2
    rx0 = 384
    a.text(rx0, 30, "PPO's objective, one action", size=11.5, weight=700)
    a.text(rx0, 50, "L = min(r A, clip(r, 1-e, 1+e) A)", size=10.5, mono=True)
    a.text(rx0, 65, "r = pi_new(a|s) / pi_old(a|s)", "tm", 10.5, mono=True)
    for k, sgn in enumerate((1, -1)):
        x0, y0, w, h = rx0 + 6 + k * 120, 84, 100, 110
        X = lambda rr: x0 + (rr - 0.4) / 1.2 * w                     # r from 0.4 to 1.6
        Y = lambda Lv: y0 + h / 2 - Lv * (h / 2 - 8) / 1.6
        a.line(x0, y0 + h / 2, x0 + w + 4, y0 + h / 2, "m")
        L = lambda rr: min(rr * sgn, max(1 - e, min(1 + e, rr)) * sgn)
        poly(a, [(X(0.4 + q / 50), Y(L(0.4 + q / 50))) for q in range(0, 61)], "a")
        for rr in (1 - e, 1 + e):
            a.line(X(rr), y0 + 4, X(rr), y0 + h - 4, "m", dash=True)
            a.text(X(rr), y0 + h + 14, f"{rr:.1f}", "tm", 9.5, "middle", mono=True)
        dot(a, X(1), Y(L(1)), 3, "a fa")
        a.text(x0 + w + 4, y0 + h / 2 + 14, "r", "tm", 10, "end", mono=True)
        a.text(x0 + w / 2, y0 - 6, "A > 0" if sgn > 0 else "A < 0", size=10.5, anchor="middle", weight=600, mono=True)
    a.text(rx0, 228, "e = 0.2; the dot: r = 1, the old policy", "tm", 10.5)
    a.text(rx0, 243, "A > 0: flat past 1+e; A < 0: flat below 1-e.", "tm", 10.5)
    a.text(rx0, 258, "No gain from moving the policy further.", "tm", 10.5)
    a.text(24, 288, "Three agents on one environment: Q-learning, a policy gradient, then PPO. A: the advantage of the action.",
           "tm", 10.5)
    return a


# =================================================================== 19 seeing

def res_vision():
    a = Art("r19", "Seeing with transformers: an image becomes a sequence of patches for the same block, and CLIP "
                   "learns to match images with their captions")
    a.text(24, 30, "an image as a sequence of patches", size=11.5, weight=700)
    ix, iy, s = 24, 46, 22
    house = ["............",
             ".....##.....",
             "....####....",
             "...######...",
             "..########..",
             ".##########.",
             "..########..",
             "..##....##..",
             "..##.##.##..",
             "..##.##.##..",
             "..##.##.##..",
             "############"]
    q = s * 4 / 12
    for i, row in enumerate(house):
        for j, c in enumerate(row):
            shade(a, ix + j * q, iy + i * q, q, q, 0.85 if c == "#" else 0.08, "t")
    for k in range(5):
        a.line(ix + k * 22, iy, ix + k * 22, iy + 88, "a")
        a.line(ix, iy + k * 22, ix + 88, iy + k * 22, "a")
    a.text(ix + 44, iy + 104, "4 x 4 = 16 patches", "ta", 10, "middle")
    tx, ty, tw = 136, 140, 12
    cell(a, tx, ty, tw + 6, 20, "c", "a af", "ta", 10, rx=2, weight=700)
    for k in range(16):
        a.box(tx + tw + 9 + k * (tw + 1), ty, tw, 20, "s fs", rx=2)
    a.text(tx, ty + 34, "[class] token + 16 patch vectors", "tm", 10)
    a.text(tx, ty + 48, "each patch: flatten, linear, + position", "tm", 10)
    a.path(f"M{ix + 92} {iy + 60} C 124 {iy + 60}, 126 {ty + 10}, {tx - 2} {ty + 10}", "s", arrow=True)
    a.line(tx + 120, ty - 2, tx + 120, 104, "s", arrow=True)
    cell(a, 160, 72, 200, 30, "transformer block x L, no mask", "s fs", "t", 10.5, rx=6, weight=600, mono=False)
    a.line(166, 72, 166, 52, "a", arrow=True)
    a.text(174, 52, "class, read from c", "ta", 10.5, weight=600)
    a.text(24, 236, "no built-in locality, unlike a convolution:", "tm", 10.5)
    a.text(24, 251, "on little data it trails a ResNet of its size", "tm", 10.5)

    rx0 = 400
    a.text(rx0, 30, "CLIP: match images and captions", size=11.5, weight=700)
    n, cw = 4, 26
    gx, gy = 424, 60
    for j in range(n):
        a.text(gx + j * cw + cw / 2, gy - 7, f"T{j + 1}", "tm", 10, "middle", mono=True)
        a.text(gx - 7, gy + j * cw + 17, f"I{j + 1}", "tm", 10, "end", mono=True)
    for i in range(n):
        for j in range(n):
            a.box(gx + j * cw, gy + i * cw, cw, cw, "a af" if i == j else "s f", rx=0)
    tx0 = gx + n * cw + 12
    a.text(tx0, gy + 14, "cell: image i", "tm", 10)
    a.text(tx0, gy + 28, "dot caption j", "tm", 10)
    a.text(tx0, gy + 54, "the diagonal:", "ta", 10, weight=600)
    a.text(tx0, gy + 68, "the true pairs,", "ta", 10)
    a.text(tx0, gy + 82, "pushed highest", "ta", 10)
    a.text(rx0, 190, "loss: cross-entropy along each row", "tm", 10.5)
    a.text(rx0, 205, "and down each column", "tm", 10.5)
    a.text(rx0, 228, "to classify, compare the image with", "tm", 10.5)
    a.text(rx0, 243, "'a photo of a {label}.'", size=10.5, mono=True)
    a.text(rx0, 258, "for every label; the best match wins", "tm", 10.5)
    a.text(24, 288, "The block is your GPT's; CLIP's published weights then label images it was never trained to label.",
           "tm", 10.5)
    return a


# =================================================================== 20 preferences

def res_prefs():
    a = Art("r20", "Preferences: a choice between two answers is the data; fit a reward model to the choices, or tune "
                   "the model on them directly with DPO")
    a.text(24, 30, "the data: one prompt, two stories, a choice", size=11.5, weight=700)
    cell(a, 24, 42, 230, 24, "prompt: a story about a lost cat", "s fs", "t", 10.5, rx=5, mono=False)
    cell(a, 24, 76, 110, 30, "story A", "a af", "ta", 11, rx=6, weight=700, mono=False)
    cell(a, 144, 76, 110, 30, "story B", "s f", "t", 11, rx=6, mono=False)
    a.text(139, 125, "A is preferred", "ta", 10.5, "middle", 600)
    a.text(24, 160, "reward model", size=11.5, weight=700)
    a.text(24, 178, "P(A over B) = sigmoid(r(A) - r(B))", size=10.5, mono=True)
    a.text(24, 194, "fit r to the choices, then tune the", "tm", 10.5)
    a.text(24, 208, "model to score high under r", "tm", 10.5)

    rx0 = 300
    a.text(rx0, 30, "DPO: no reward model", size=11.5, weight=700)
    a.text(rx0, 50, "loss = -log sigmoid(beta (dA - dB))", size=10.5, mono=True)
    a.text(rx0, 66, "dY = log pi(Y|x) - log pi_ref(Y|x)", size=10.5, mono=True)
    a.text(rx0, 84, "raise A's probability relative to the start,", "tm", 10.5)
    a.text(rx0, 98, "lower B's; beta keeps it near the start", "tm", 10.5)

    px0, px1, py0, py1 = rx0 + 8, 600, 136, 222
    axes(a, px0, py0 - 6, px1, py1)
    X = lambda t: px0 + t * (px1 - px0)
    Y = lambda v: py1 - v * (py1 - py0)
    proxy = lambda t: 0.08 + 0.85 * (1 - math.exp(-2.6 * t))
    gold = lambda t: 0.08 + 2.2 * t * math.exp(-2.6 * t)
    poly(a, [(X(k / 50), Y(proxy(k / 50))) for k in range(51)], "s")
    poly(a, [(X(k / 50), Y(gold(k / 50))) for k in range(51)], "a")
    a.text(X(1) - 4, Y(proxy(1)) - 8, "the reward model's score", size=10, anchor="end")
    a.text(X(0.62), Y(gold(0.62)) + 16, "what you wanted", "ta", 10, "middle", 600)
    a.text(px0 + 4, py0 - 12, "score", "tm", 10)
    a.text(px1, py1 + 14, "how far the model has moved from where it started", "tm", 10, "end")
    a.text(24, 266, "Push too far and the score keeps rising while the stories get worse: over-optimisation.", "tm", 11)
    a.text(24, 288, "A schematic, no measured numbers. What the tuning cost elsewhere is measured too.", "tm", 10.5)
    return a


# =================================================================== 21 phenomena

def res_phenomena():
    a = Art("r21", "Four phenomena to reproduce: a lottery ticket, distillation, the edge of stability, and a low path "
                   "between two trained networks")
    pw, py0, py1 = 132, 46, 166
    xs = [24, 178, 332, 486]
    heads = ["a lottery ticket", "distillation", "edge of stability", "a path between"]
    descs = [["keep the largest 10%,", "reset them to their first", "values: it trains as well"],
             ["the student learns the", "teacher's whole answer,", "softened by a temperature"],
             ["full-batch descent:", "sharpness rises to", "2 / lr, then stays there"],
             ["two trained networks:", "the straight line climbs", "a hill, a curve stays low"]]
    for x0, head, ds in zip(xs, heads, descs):
        a.text(x0, py1 + 30, head, size=12, weight=700)
        for k, ln in enumerate(ds):
            a.text(x0, py1 + 47 + k * 14, ln, "tm", 10.5)
    # 1: a weight matrix, the largest 10% kept (computed from random magnitudes)
    x0 = xs[0]
    r = random.Random(21)
    rows, cols, s = 7, 10, 12
    w = [[abs(r.gauss(0, 1)) for _ in range(cols)] for _ in range(rows)]
    cut = sorted(v for row in w for v in row)[-(rows * cols) // 10]
    kept = sum(v >= cut for row in w for v in row)
    assert kept == rows * cols // 10
    for i in range(rows):
        for j in range(cols):
            on = w[i][j] >= cut
            a.box(x0 + 4 + j * s, py0 + 10 + i * s, s - 2, s - 2, "a fa" if on else "m", rx=1)
    a.text(x0 + 4, py0 + 10 + rows * s + 16, f"{kept} of {rows * cols} weights", "ta", 10)
    # 2: a hard label against a teacher's softened answer
    x0 = xs[1]
    logits = [6.0, 3.2, 2.4, 1.0, 0.4, 0.0]
    Tm = 3.0
    ex = [math.exp(z / Tm) for z in logits]
    soft = [e / sum(ex) for e in ex]
    bw = 14
    for k in range(6):
        bx = x0 + 8 + k * (bw + 4)
        h1 = 46 if k == 0 else 0
        h2 = soft[k] * 46 / soft[0]
        if h1:
            a.box(bx, py0 + 52 - h1, bw, h1, "s fs", rx=1)
        a.add(f'<line class="m" x1="{bx}" y1="{py0 + 52}" x2="{bx + bw}" y2="{py0 + 52}" {SW}/>')
        a.box(bx, py1 - 4 - h2, bw, h2, "a af", rx=1)
    a.text(x0 + 122, py0 + 20, "label", "tm", 10, "end")
    a.text(x0 + 122, py1 - 40, "teacher", "ta", 10, "end")
    a.line(x0 + 4, py1 - 4, x0 + pw, py1 - 4, "m")
    # 3: sharpness rises until 2 / lr, then hovers there
    x0 = xs[2]
    axes(a, x0, py0 - 6, x0 + pw, py1)
    X = lambda t: x0 + 4 + t * (pw - 8)
    Yh = lambda v: py1 - 8 - v * (py1 - py0 - 30)
    sharp = lambda t: 0.15 + 0.85 * (t / 0.45) ** 1.4 if t < 0.45 else 1 + 0.035 * math.sin(60 * t) + 0.02 * math.sin(143 * t)
    a.line(x0, Yh(1), x0 + pw, Yh(1), "m", dash=True)
    a.text(x0 + 6, Yh(1) - 6, "2 / lr", "tm", 10, mono=True)
    poly(a, [(X(k / 120), Yh(sharp(k / 120))) for k in range(121)], "a")
    a.text(x0 + 4, py0 - 10, "sharpness", "tm", 10)
    a.text(x0 + pw, py1 + 12, "step", "tm", 9.5, "end")
    # 4: loss along the straight line between two minima, and along a curved path
    x0 = xs[3]
    axes(a, x0, py0 - 6, x0 + pw, py1)
    X = lambda t: x0 + 10 + t * (pw - 20)
    Yl = lambda v: py1 - 12 - v * (py1 - py0 - 30)
    poly(a, [(X(k / 60), Yl(math.sin(math.pi * k / 60) ** 2)) for k in range(61)], "s")
    poly(a, [(X(k / 60), Yl(0.06 * math.sin(math.pi * k / 60) ** 2)) for k in range(61)], "a")
    dot(a, X(0), Yl(0), 3.5, "s fs"); dot(a, X(1), Yl(0), 3.5, "s fs")
    a.text(X(0.5), Yl(1) - 6, "straight line", size=10, anchor="middle")
    a.text(X(0.5), Yl(0) - 8, "curved path", "ta", 10, "middle")
    a.text(x0 + 4, py0 - 10, "loss", "tm", 10)
    a.text(X(0), py1 + 12, "A", "t", 10, "middle", 700, mono=True)
    a.text(X(1), py1 + 12, "B", "t", 10, "middle", 700, mono=True)
    a.text(24, 288, "Schematics of each paper's finding, no measured numbers: your own runs draw the real ones.", "tm", 10.5)
    return a


# =================================================================== icons and the table

ICON = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="none" stroke="currentColor" '
        'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">{}</svg>\n')

MODULES = {
    "00": (res_workbench, '<rect x="3" y="3" width="14" height="14" rx="3"/>'
                          '<path d="M7 7h.01M13 13h.01M10 10h.01M13 7h.01M7 13h.01" stroke-width="2.2"/>'),
    "01": (res_backprop, '<circle cx="5" cy="5.5" r="2"/><circle cx="5" cy="14.5" r="2"/><circle cx="15" cy="10" r="2"/>'
                         '<path d="M7 6.4l6 2.7M7 13.6l6-2.7"/>'),
    "02": (res_tensors, '<path d="M10 2.5l7 4v7l-7 4-7-4v-7z"/><path d="M3 6.5l7 4 7-4M10 10.5v7"/>'),
    "03": (res_optim, '<path d="M2.5 3L9 5.5 3.5 8.5 11 10.5 6 13.5 13.5 15"/><circle cx="16" cy="15.75" r="1.5"/>'),
    "04": (res_deep, '<rect x="3" y="2.75" width="9" height="3.5" rx="1"/><rect x="3" y="8.25" width="9" height="3.5" rx="1"/>'
                     '<rect x="3" y="13.75" width="9" height="3.5" rx="1"/><path d="M12 15.5h4.5v-11H12"/>'),
    "05": (res_general, '<path d="M3 3v14h14"/><path d="M5.5 8c1.25 3.5 2.5 3.5 3.5 0 .75-3 1.5-3 2.25.5.9 4 2.5 5.5 5 5.5"/>'),
    "06": (res_conv, '<rect x="2.5" y="2.5" width="15" height="15" rx="2"/><rect x="5" y="5" width="7" height="7" rx=".5"/>'
                     '<path d="M7.33 5v7M9.67 5v7M5 7.33h7M5 9.67h7" stroke-width="1"/>'),
    "07": (res_lm, '<path d="M3 5h14M3 10h14M3 15h8"/><path d="M14 13v4" stroke-width="2"/>'),
    "08": (res_gpt, '<path d="M3 3h3.5v3.5H10V10h3.5v3.5H17V17H3z"/>'),
    "09": (res_gpt2, '<rect x="2.5" y="3" width="6.5" height="5" rx="1.5"/><rect x="11" y="3" width="6.5" height="5" rx="1.5"/>'
                     '<rect x="4" y="12" width="12" height="5" rx="1.5"/><path d="M5.75 8v2.25M14.25 8v2.25"/>'),
    "10": (res_modern, '<path d="M3 16.5h14"/><path d="M3 16.5l10-9.5"/><path d="M9.5 16.5a6.5 6.5 0 0 0-1.9-4.6"/>'
                       '<path d="M13 7l.6 3M13 7l-3 .4"/>'),
    "11": (res_fast, '<path d="M11.5 2.5L4.5 11h5l-1 6.5 7-8.5h-5z"/>'),
    "12": (res_finetune, '<path d="M4 3v14M10 3v14M16 3v14"/><circle cx="4" cy="12.5" r="1.75"/>'
                         '<circle cx="10" cy="7" r="1.75"/><circle cx="16" cy="13.5" r="1.75"/>'),
    "13": (res_rigour, '<path d="M6 4v8M4.5 4h3M4.5 12h3M14 7v9M12.5 7h3M12.5 16h3"/>'
                       '<path d="M6 8h.01M14 11.5h.01" stroke-width="2.6"/>'),
    "14": (res_grok, '<path d="M5 2.5h6.5L15 6v11.5H5z"/><path d="M11.5 2.5V6H15M7.5 10h5M7.5 13h5"/>'),
    "15": (res_result, '<path d="M7.5 14.5h5M8.5 17.5h3"/>'
                       '<path d="M10 2.5a5 5 0 0 0-3 9c.6.5 1 1.2 1 2v1h4v-1c0-.8.4-1.5 1-2a5 5 0 0 0-3-9z"/>'),
    "16": (res_inside, '<circle cx="8.5" cy="8.5" r="5"/><path d="M12.25 12.25L17 17"/>'),
    "17": (res_diffusion, '<path d="M10 2.5a7.5 7.5 0 0 1 0 15"/>'
                          '<path d="M7 3.1h.01M4.3 5h.01M2.8 8.1h.01M2.8 11.9h.01M4.3 15h.01M7 16.9h.01" stroke-width="2"/>'),
    "18": (res_reward, '<circle cx="10" cy="10" r="7.5"/><circle cx="10" cy="10" r="4"/><circle cx="10" cy="10" r=".75"/>'),
    "19": (res_vision, '<path d="M2 10s3-5.5 8-5.5 8 5.5 8 5.5-3 5.5-8 5.5S2 10 2 10z"/><circle cx="10" cy="10" r="2.5"/>'),
    "20": (res_prefs, '<path d="M10 3v14M6.5 17h7M4.5 5.5h11"/><path d="M4.5 5.5L2.5 11h4zM15.5 5.5l-2 5.5h4z"/>'),
    "21": (res_phenomena, '<path d="M10 2.5c.6 4.2 3.3 6.9 7.5 7.5-4.2.6-6.9 3.3-7.5 7.5-.6-4.2-3.3-6.9-7.5-7.5 '
                          '4.2-.6 6.9-3.3 7.5-7.5z"/>'),
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
