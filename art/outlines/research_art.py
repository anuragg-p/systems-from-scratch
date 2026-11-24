"""Module art for the research track (its outline is plans/research-outline.md), in the same visual
language as dsa_art.py, outline_art.py and the xv6 covers.

Writes, under outlines/ai-research/:
    NN/cover.svg    640x300 teaching diagram for module NN (00 to 21; 16 to 21 are the extensions)
    NN/icon.svg     20x20 currentColor line icon for module NN
and the same two files into tracks/research/lessons/NN-*/ for every module that has a lessons
folder there, so a built module's art and the outline's never drift apart.
The track-level art.svg and icon.svg are not this script's.

Covers style themselves only through the .art classes in harness/web/app.css:
    s m a        stroke: foreground, muted, accent
    f fs af fa   fill: page, code background, accent-soft, accent
    t tm ta      text fill: foreground, muted, accent      mono: monospace
A shaded cell is a rect of class fa (or t) with a fill-opacity, so it follows the theme.

What a cover shows is either computed here or drawn as a labelled schematic with no numbers on
its axes. Every word and number on a built module's cover must be true of the built track.
Computed, for the built modules, from the formulas and settings of the track's own code:
    00  experiments/curve.py over seeds 0 to 4: the training-loss curves and test losses, with
        numpy's default_rng drawing in the script's order, so they are the script's numbers
    01  01.02's neuron, o = tanh(x1 w1 + x2 w2 + b), its backward() node by node and 01.01's
        central-difference nudge (h = 1e-6) for every input
    02  a broadcast's backward on small numbers, and the shapes of a matrix multiply's backward
    03  SGD, momentum 0.8 and Adam in 03.02's valley, and 03.05's warmup and cosine schedule
    04  the spread over a batch at every relu of 04.02's 30-layer network for its three starts
        (random inputs in place of MNIST), and each start's factor sqrt(n Var(w) / 2)
    06  a 3 by 3 kernel on a 6 by 6 image, and 06.04's recorded long run read from
        tracks/research/experiments/recorded/resnet/: the training error of each network at the
        end, the mean of its seeds' summaries
    07  the pair model's bits on the test text, counted here from the shipped text as 07.01 counts
        it (k = 0.1), and 07.02's recorded long run at a context of 5 (the network's mean over seeds,
        deleted interpolation) read from tracks/research/experiments/recorded/nplm/; the rows of
        what each model looks back at are a schematic (the attention row is 07.04's copying, the
        decoder's weight on the position it writes)
    08  the causal mask itself (0 and -inf, exact), the block drawn at the sizes of 08.04's recorded long run,
        and that run's results read from tracks/research/experiments/recorded/gpt/: its weight count (checked
        against what it printed), each dropout's mean test bits, the turn-up without dropout; and module 07's
        best, 07.02's recorded network mixed with interpolation at 8 characters
Where a cover prints a number the lessons print, the script asserts it is the same number, so a
change to the track that moves it stops this script instead of leaving the cover wrong.
Also computed: the double-descent curve in 05 (random ReLU features, least squares), the
convolution in 06, the BPE merges in 09, the LoRA counts in 12, the DDPM noising in 17 and the
PPO objective in 18. Schematic (the true shape, no measured numbers): 11's loss curves, 13's panels, 14's grokking curves (after Power et al. 2022, Figure 1), 15's
paper, 20's over-optimisation and 21's four phenomena.

Modules 14 and 15 keep the covers first drawn for the older outline in outline_art.py (its
modules 04 and 07): 14 with its step gap corrected to the paper's (train near 100% before 1e3
steps, validation only near 1e6), 15 with its repository shown as the track lays one out (a run
is `python3 -m experiments.<name>` with key=value settings, and leaves config.json, log.jsonl
and summary.json). The rest are new here.

The Art class is the one from art/xv6/covers.py and dsa_art.py, repeated so this file stands alone.
Module 00's cover needs numpy, as the track does.

    python3 art/outlines/research_art.py [NN ...]
        write every file (or only modules NN), then check each one is ASCII and survives
        harness/web/art.py's sanitizer unchanged
"""
import glob
import html
import json
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "outlines", "ai-research")
LESSONS = os.path.join(ROOT, "tracks", "research", "lessons")
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

CURVE = dict(n_train=20, n_test=500, noise=0.2, degree=3, lr=0.5, steps=2000, every=100)   # curve.py's CONFIG


def curve_run(seed, n_train, n_test, noise, degree, lr, steps, every):
    """One run of module 00's experiment, experiments/curve.py: a cubic fitted by gradient descent
    to n_train points of sin(pi x) plus noise, its gradient 2 X.T (X w - y) / n worked by hand,
    then scored on n_test points drawn after them from the same generator. numpy's
    default_rng(seed) makes the draws in the script's order, so these are the script's numbers.
    Returns the training loss every `every` steps and after the last, and the test loss."""
    import numpy as np
    rng = np.random.default_rng(seed)

    def make_data(n):
        x = rng.uniform(-1, 1, n)
        return x, np.sin(np.pi * x) + rng.normal(0, noise, n)
    x, y = make_data(n_train)
    xt, yt = make_data(n_test)
    X = np.stack([x ** k for k in range(degree + 1)], axis=1)
    Xt = np.stack([xt ** k for k in range(degree + 1)], axis=1)
    loss = lambda w, A, b: float(np.mean((A @ w - b) ** 2))
    w = np.zeros(degree + 1)
    log = []
    for step in range(steps):
        if step % every == 0:
            log.append(loss(w, X, y))
        w -= lr * 2 * X.T @ (X @ w - y) / len(y)
    log.append(loss(w, X, y))
    return log, loss(w, Xt, yt)


def spread(xs):
    """lab.spread: mean +- sample sd, min, max, to 3 significant digits."""
    m = sum(xs) / len(xs)
    sd = math.sqrt(sum((v - m) ** 2 for v in xs) / (len(xs) - 1))
    return f"{m:.3g} +- {sd:.3g} (min {min(xs):.3g}, max {max(xs):.3g}, {len(xs)} seeds)"


def res_workbench():
    a = Art("r00", "One experiment in one file, run over five seeds: the same seed gives the same numbers, "
                   "other seeds show how far the test loss moves by chance")
    a.text(24, 28, "one file", size=12, weight=700)
    stages = [("data", "20 points of sin(pi x), plus noise"), ("model", "a cubic, w0 + w1 x + w2 x^2 + w3 x^3"),
              ("loss", "mean squared error"), ("update", "w -= lr * grad, worked by hand"),
              ("evaluate", "loss on 500 points it never saw")]
    for k, (name, sub) in enumerate(stages):
        y = 40 + k * 38
        cell(a, 32, y, 92, 26, name, "s fs" if k in (1, 3) else "s f", "t", 11.5, rx=6, weight=600, mono=False)
        a.text(134, y + 17, sub, "tm", 10.5)
        if k:
            a.line(78, y - 12, 78, y - 2, "s", arrow=True)
    a.path("M32 167 H 20 V 91 H 30", "m", arrow=True)
    a.text(24, 236, "each run's folder: config.json, log.jsonl and", "tm", 10.5)
    a.text(24, 251, "summary.json; curves are drawn from the logs", "tm", 10.5)

    runs = [curve_run(s, **CURVE) for s in range(5)]
    assert curve_run(0, **CURVE) == runs[0]           # same seed, same numbers, to the last digit
    tests = [t for _, t in runs]
    line = spread(tests)
    # the numbers lessons 00.01 to 00.03 print; if the experiment changes, so must this cover
    assert (round(runs[0][0][-1], 4), round(tests[0], 4)) == (0.0104, 0.0496)
    assert line == "0.0542 +- 0.00668 (min 0.0472, max 0.0645, 5 seeds)", line
    px0, px1, py0, py1 = 356, 540, 46, 204
    lo, hi = math.log10(0.008), math.log10(0.8)
    n = len(runs[0][0]) - 1
    X = lambda i: px0 + 4 + i / n * (px1 - px0 - 8)
    Y = lambda v: py1 - (math.log10(v) - lo) / (hi - lo) * (py1 - py0)
    axes(a, px0, py0 - 6, px1, py1)
    a.text(px0, 30, "training loss, log scale", "tm", 10.5)
    a.text(X(0), py1 + 15, "0", "tm", 9.5, "middle", mono=True)
    a.text(X(n), py1 + 15, str(CURVE["steps"]), "tm", 9.5, "middle", mono=True)
    a.text((px0 + px1) / 2, py1 + 15, "step", "tm", 10.5, "middle")
    for s in (1, 2, 3, 4, 0):
        poly(a, [(X(i), Y(v)) for i, v in enumerate(runs[s][0])], "a" if s == 0 else "m")
    a.text(px1 - 4, 72, "seed 0, run twice: the same", "ta", 10.5, "end", 600)
    a.text(px1 - 4, 87, "log, to the last digit", "ta", 10.5, "end")
    a.text(px1 - 4, 108, "seeds 1 to 4: same code,", "tm", 10.5, "end")
    a.text(px1 - 4, 123, "other numbers", "tm", 10.5, "end")
    # the test losses, one dot a seed, on a scale of their own
    tx, t0, t1 = 584, min(tests), max(tests)
    TY = lambda v: py1 - 16 - (v - t0) / (t1 - t0) * (py1 - py0 - 64)
    a.text(tx + 6, 30, "test loss", "tm", 10.5, "middle")
    a.line(tx - 12, py0 - 6, tx - 12, py1, "m")
    for s in (1, 2, 3, 4, 0):
        dot(a, tx, TY(tests[s]), 3, "a fa" if s == 0 else "s f")
    a.path(f"M{tx + 10} {TY(t1):.1f} H {tx + 14} V {TY(t0):.1f} H {tx + 10}", "s")
    a.text(tx + 6, TY(t1) - 12, f"{t1:.3g}", "tm", 9.5, "middle", mono=True)
    a.text(tx + 6, TY(t0) + 20, f"{t0:.3g}", "tm", 9.5, "middle", mono=True)
    a.text(24, 272, "One run is never a result. The five test losses, as the lab reports them:", "tm", 11)
    a.text(24, 289, f"test loss {line}", "ta", 11, weight=600, mono=True)
    a.text(616, 289, "(computed here)", "tm", 10.5, "end")
    return a


# =================================================================== 01 backprop

NEURON = dict(x1=1.5, x2=-0.5, w1=0.8, w2=-1.2, b=-1.0)         # experiments/graph.py's CONFIG


def neuron(x1, x2, w1, w2, b):
    """01.02's neuron, o = tanh(x1 w1 + x2 w2 + b), one step at a time in graph.py's order."""
    p1 = x1 * w1
    p2 = x2 * w2
    s = p1 + p2
    n = s + b
    return p1, p2, s, n, math.tanh(n)


def central(f, xs, h=1e-6):
    """01.01's gradient(): every partial derivative of f at xs by the central difference."""
    out = []
    for i in range(len(xs)):
        up, down = list(xs), list(xs)
        up[i] += h
        down[i] -= h
        out.append((f(up) - f(down)) / (2 * h))
    return out


def res_backprop():
    a = Art("r01", "Backpropagation through one neuron, o = tanh(x1 w1 + x2 w2 + b): values flow forward, "
                   "gradients flow back, and the nudge checks them")
    v = NEURON
    p1, p2, s, n, o = neuron(**v)
    # backward(), node by node: o.grad = 1; tanh passes 1 - o^2; a sum passes its grad on unchanged;
    # a product gives each input the other input times its grad
    g = {"o": 1.0}
    g["n"] = (1 - o * o) * g["o"]
    g["s"] = g["b"] = g["n"]
    g["x1*w1"] = g["x2*w2"] = g["s"]
    g["x1"], g["w1"] = v["w1"] * g["x1*w1"], v["x1"] * g["x1*w1"]
    g["x2"], g["w2"] = v["w2"] * g["x2*w2"], v["x2"] * g["x2*w2"]
    names = ("x1", "x2", "w1", "w2", "b")
    nudged = central(lambda xs: neuron(*xs)[-1], [v[k] for k in names])
    worst = max(abs(g[k] - e) for k, e in zip(names, nudged))
    # what 01.02's run prints: o = 0.6640, the nudge for w1 +0.83858275, the largest gap 1.2e-10
    assert (f"{o:.4f}", f"{nudged[2]:+.8f}", f"{worst:.1e}") == ("0.6640", "+0.83858275", "1.2e-10")
    W, H = 96, 38
    val = {"x1": v["x1"], "w1": v["w1"], "x2": v["x2"], "w2": v["w2"], "b": v["b"], "x1*w1": p1, "x2*w2": p2,
           "s": s, "n": n, "o": o}
    at = {"x1": (24, 34), "w1": (24, 80), "x2": (24, 136), "w2": (24, 182), "x1*w1": (182, 57),
          "x2*w2": (182, 159), "s": (340, 108), "b": (340, 176), "n": (498, 142), "o": (498, 40)}
    for name, (x, y) in at.items():
        a.box(x, y, W, H, "s f", rx=8)
        a.text(x + 10, y + 16, f"{name} = {val[name]:.4g}", size=11.5, mono=True, weight=600)
        a.text(x + 10, y + 31, f"grad {g[name]:.4g}", "ta", 10.5, mono=True)
    for x, y, op in ((152, 76, "*"), (152, 178, "*"), (310, 127, "+"), (468, 161, "+")):
        a.circle(x, y, 12, "s fs")
        a.text(x, y + 4.5, op, size=13, anchor="middle", mono=True, weight=600)
    a.circle(546, 110, 14, "s fs")
    a.text(546, 113.5, "tanh", size=9.5, anchor="middle", mono=True, weight=600)

    def edge(x1, y1, x2, y2):
        a.path(f"M{x1} {y1} C {x1 + 14} {y1}, {x2 - 16} {y2}, {x2} {y2}", "s")
    edge(120, 53, 140, 72); edge(120, 99, 140, 80)
    a.line(164, 76, 180, 76, arrow=True)
    edge(120, 155, 140, 174); edge(120, 201, 140, 182)
    a.line(164, 178, 180, 178, arrow=True)
    edge(278, 76, 298, 123); edge(278, 178, 298, 131)
    a.line(322, 127, 338, 127, arrow=True)
    edge(436, 127, 456, 157); edge(436, 195, 456, 165)
    a.line(480, 161, 496, 161, arrow=True)
    a.line(546, 142, 546, 124)
    a.line(546, 96, 546, 80, arrow=True)
    a.line(24, 16, 300, 16, "s", arrow=True)
    a.text(308, 20, "forward: values", "tm", 10.5)
    a.text(24, 240, "chain rule, one step:", "tm", 10.5)
    a.text(24, 256, "w1.grad = x1 x (x1*w1).grad", "ta", 11, mono=True, weight=600)
    a.text(77, 272, f"= {v['x1']:g} x {g['x1*w1']:.4f} = {g['w1']:.4f}", "ta", 11, mono=True)
    a.text(290, 240, "check, the nudge both ways, h = 1e-6:", "tm", 10.5)
    a.text(290, 256, f"(o(w1+h) - o(w1-h)) / 2h = {nudged[2]:.8f}", size=11, mono=True)
    a.text(290, 272, f"backward: {g['w1']:.8f}; largest gap of the five {worst:.1e}", "tm", 10.5)
    a.line(616, 290, 250, 290, "a", arrow=True)
    a.text(240, 294, "backward(): gradients, from o", "ta", 10.5, "end", 600)
    return a


# =================================================================== 02 tensors

def res_tensors():
    a = Art("r02", "Every backward returns a gradient the shape of its input: a broadcast forward is a sum backward, "
                   "and a matrix multiply's backward is two more")
    cw, ch = 20, 18
    # broadcasting, forward
    a.text(24, 28, "broadcasting", size=12, weight=700)
    a.text(24, 48, "out = x + b", size=11.5, mono=True, weight=600)
    gy = 58
    for r in range(3):
        for c in range(4):
            a.box(24 + c * cw, gy + r * ch, cw, ch, "s f", rx=0)
            a.box(224 + c * cw, gy + r * ch, cw, ch, "s f", rx=0)
            a.box(124 + c * cw, gy + r * ch, cw, ch, "a af" if r == 0 else "m", rx=0, dash=r > 0)
    a.text(114, gy + 31, "+", size=14, anchor="middle", mono=True)
    a.text(214, gy + 31, "=", size=14, anchor="middle", mono=True)
    a.text(64, gy + 70, "x  (3, 4)", "tm", 10.5, "middle", mono=True)
    a.text(164, gy + 70, "b  (4,)", "ta", 10.5, "middle", mono=True)
    a.text(264, gy + 70, "out  (3, 4)", "tm", 10.5, "middle", mono=True)
    a.text(164, gy + 85, "repeated down the rows", "tm", 10, "middle")
    # broadcasting, backward
    dy = [[1, 0, 2, 1], [0, 1, 1, 0], [2, 1, 0, 1]]
    db = [sum(dy[r][c] for r in range(3)) for c in range(4)]
    a.text(24, 160, "backward", size=11.5, weight=700)
    by = 170
    for r in range(3):
        for c in range(4):
            cell(a, 24 + c * cw, by + r * ch, cw, ch, str(dy[r][c]), "s f", "t", 10.5, rx=0)
    a.text(64, by + 68, "out.grad  (3, 4)", "tm", 10.5, "middle", mono=True)
    a.path(f"M108 {by + 27} H 172", "a", arrow=True)
    a.text(140, by + 20, "sum(axis=0)", "ta", 10, "middle", mono=True)
    for c in range(4):
        cell(a, 176 + c * cw, by + 18, cw, ch, str(db[c]), "a af", "ta", 10.5, rx=0, weight=700)
    a.text(216, by + 52, "b.grad  (4,)", "ta", 10.5, "middle", mono=True)
    a.text(24, 254, "b was used in 3 rows, so its gradient adds up all 3", "tm", 10.5)

    # matrix multiply: rectangles drawn to scale, n = 3, k = 4, m = 2
    u = 9
    a.text(340, 28, "matrix multiply", size=12, weight=700)
    a.text(616, 28, "drawn with n = 3, k = 4, m = 2", "tm", 10, "end")
    rows = [("out = x @ w", 50, [("(n, k)", 4, 3, "s f"), ("(k, m)", 2, 4, "s f"), ("(n, m)", 2, 3, "s f")], ""),
            ("w.grad = x.T @ out.grad", 124, [("(k, n)", 3, 4, "s f"), ("(n, m)", 2, 3, "s f"), ("(k, m)", 2, 4, "a af")],
             "w"),
            ("x.grad = out.grad @ w.T", 194, [("(n, m)", 2, 3, "s f"), ("(m, k)", 4, 2, "s f"), ("(n, k)", 4, 3, "a af")],
             "x")]
    centres = [374, 448, 522]
    for title, ty, mats, of in rows:
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
        if of:
            a.text(566, top + 1.5 * u + 4, "<- shape of " + of, "ta", 10, weight=600)
    a.text(24, 272, "Each gradient has the shape of the tensor it belongs to: the first check on any backward.", "tm", 11)
    a.text(24, 288, "Every backward here is checked against the nudge, and against PyTorch's gradients to within 1e-6.",
           "tm", 11)
    return a


# =================================================================== 03 optimisers

VALLEY = dict(steep=50.0, start=(-4.0, 1.0), threshold=1e-4)    # 03.02's valley: (w0^2 + 50 w1^2) / 2


def valley_path(steep, start, threshold, lr, mu=0.0, adam=False, max_steps=5000):
    """Descent on (w0^2 + steep w1^2) / 2 from start until the loss is below threshold, as
    experiments/momentum.py (SGD, momentum mu, the velocity starting as the first gradient) and
    adam.py (Adam, betas 0.9 and 0.999, eps 1e-8) run it. Returns the steps taken and the path."""
    w = list(start)
    buf, m, s = None, [0.0, 0.0], [0.0, 0.0]
    path = [tuple(w)]
    for step in range(max_steps):
        if 0.5 * (w[0] ** 2 + steep * w[1] ** 2) < threshold:
            return step, path
        g = [w[0], steep * w[1]]
        if adam:
            t = step + 1
            for i in range(2):
                m[i] = 0.9 * m[i] + 0.1 * g[i]
                s[i] = 0.999 * s[i] + 0.001 * g[i] * g[i]
                w[i] -= lr * (m[i] / (1 - 0.9 ** t)) / (math.sqrt(s[i] / (1 - 0.999 ** t)) + 1e-8)
        else:
            if mu:
                buf = list(g) if buf is None else [mu * b + gi for b, gi in zip(buf, g)]
                g = buf
            w = [wi - lr * gi for wi, gi in zip(w, g)]
        path.append(tuple(w))
    return max_steps, path


def warmup_cosine(warmup, total):
    """lab/schedule.py's multiplier of the rate at each step: up in a line, then half a cosine to 0."""
    def multiplier(step):
        if step < warmup:
            return (step + 1) / warmup
        p = min(1.0, (step - warmup) / max(1, total - warmup))
        return 0.5 * (1 + math.cos(math.pi * p))
    return multiplier


def res_optim():
    a = Art("r03", "Optimisers in a narrow valley: plain SGD zigzags across it, momentum adds up the push along it, "
                   "and Adam sizes each parameter's step on its own")
    runs = {"sgd": valley_path(lr=0.03, **VALLEY), "momentum": valley_path(lr=0.03, mu=0.8, **VALLEY),
            "adam": valley_path(lr=0.1, adam=True, **VALLEY)}
    steps = {k: n for k, (n, _) in runs.items()}
    # what 03.02 and 03.03 print: 186 and 52 steps for SGD at lr 0.03 without and with momentum 0.8,
    # 109 for Adam at lr 0.1
    assert steps == {"sgd": 186, "momentum": 52, "adam": 109}, steps
    paths = {k: p for k, (_, p) in runs.items()}
    sc, steep = 44, VALLEY["steep"]
    a.text(24, 28, "03.02's valley, (w0^2 + 50 w1^2) / 2, from (-4, 1), to a loss below 1e-4", "tm", 10.5)
    panels = [(40, ["sgd"], f"plain SGD, lr 0.03: {steps['sgd']} steps"),
              (150, ["momentum", "adam"], "momentum, and Adam")]
    for top, names, title in panels:
        box = (24, top, 360, top + 96)
        ox, oy = 24 + 4.75 * sc, top + 48
        X = lambda u: ox + u * sc
        Y = lambda v: oy - v * sc
        for c in (0.2, 1.0, 2.8, 6, 11, 18, 28):
            rx, ry = math.sqrt(c), math.sqrt(c / steep)
            pts = [(X(rx * math.cos(2 * math.pi * k / 240)), Y(ry * math.sin(2 * math.pi * k / 240))) for k in range(241)]
            clipped(a, pts, box, "m")
        dot(a, X(0), Y(0), 2.5, "s fs")
        for name in names:
            pts = [(X(u), Y(v)) for u, v in paths[name]]
            cls = "a" if name == "adam" else "s"
            poly(a, pts, cls)
            last = pts[0]
            for x, y in pts[1:]:                 # a dot a step, where the steps are not too close to see
                if math.hypot(x - last[0], y - last[1]) >= 3:
                    dot(a, x, y, 1.8, "a fa" if name == "adam" else "s fs")
                    last = (x, y)
            dot(a, pts[0][0], pts[0][1], 3.2, "s f")
        a.text(360, top + 12, title, size=10.5, anchor="end", weight=700)
    a.text(130, 150 + 48 + 40, f"momentum 0.8, lr 0.03: {steps['momentum']} steps", size=10, weight=600)
    a.text(130, 150 + 48 - 30, f"Adam, lr 0.1: {steps['adam']} steps", "ta", 10, weight=600)

    rx0 = 392
    T, M, S = "t", "tm", "sans"
    rules = [("SGD", "s", [("w -= lr * g", T)]),
             ("momentum", "s", [("v = mu * v + g;  w -= lr * v", T)]),
             ("Adam", "a", [("m, v: running means of g and g^2,", S), ("each corrected for starting at 0", S),
                            ("w -= lr * m / (sqrt(v) + eps)", T)]),
             ("AdamW", "s", [("w -= lr * wd * w", T), ("first, then Adam's step on g alone", S)])]
    y = 40
    for name, cls, lines in rules:
        a.text(rx0, y, name, "ta" if cls == "a" else "t", 11.5, weight=700)
        for k, (ln, kind) in enumerate(lines):
            sans = kind == S
            a.text(rx0, y + 15 + k * 14, ln, M if sans else ("ta" if cls == "a" else "t"), 10.5, mono=not sans)
        y += 18 + 14 * len(lines)
    # 03.05's schedule: 200 warmup steps, then cosine decay, over 2 passes of 469 batches
    gx0, gx1, gy0, gy1 = rx0 + 4, 604, 224, 254
    total = 2 * math.ceil(60000 / 128)
    lr = warmup_cosine(200, total)
    axes(a, gx0, gy0 - 4, gx1, gy1)
    poly(a, [(gx0 + s / (total - 1) * (gx1 - gx0), gy1 - lr(s) * (gy1 - gy0)) for s in [*range(0, total, 6), total - 1]],
         "s")
    a.text(rx0, 213, "03.05's rate: 200 steps of warmup, cosine decay", "tm", 10.5)
    a.text(24, 272, "Steep across, shallow along: a step small enough for the steep way crawls along the shallow way.",
           "tm", 11)
    a.text(24, 288, "Each optimiser is the fix for what you watched the one before it do.  (Paths computed here.)", "tm", 11)
    return a


# =================================================================== 04 deep networks

def layer_spreads(how, depth=30, width=64, n_in=784, batch=16, seed=0):
    """04.02's network at the start: depth linear layers, n_in -> width -> ... -> width -> 10, a relu
    after each but the last, on a batch of random inputs. Each layer started as experiments/init.py
    starts it: "default" as nn.Linear does (weights and biases uniform in +-1/sqrt(fan_in)),
    "glorot" xavier_normal_ (sd sqrt(2 / (fan_in + fan_out))), "he" kaiming_normal_ for relu
    (sd sqrt(2 / fan_in)), both with biases 0. Returns layer_stats' spread at every relu: for each
    unit the standard deviation of its output over the batch, averaged over the units."""
    r = random.Random(seed)
    h = [[r.gauss(0, 1) for _ in range(n_in)] for _ in range(batch)]
    out, fan = [], n_in
    for _ in range(depth - 1):
        if how == "default":
            bound = 1 / math.sqrt(fan)
            W = [[r.uniform(-bound, bound) for _ in range(fan)] for _ in range(width)]
            bias = [r.uniform(-bound, bound) for _ in range(width)]
        else:
            sd = math.sqrt(2 / (fan + width)) if how == "glorot" else math.sqrt(2 / fan)
            W = [[r.gauss(0, sd) for _ in range(fan)] for _ in range(width)]
            bias = [0.0] * width
        h = [[max(0.0, sum(wk * xk for wk, xk in zip(wi, hb)) + bi) for wi, bi in zip(W, bias)] for hb in h]
        fan = width
        total = 0.0
        for j in range(width):
            col = [hb[j] for hb in h]
            m = sum(col) / batch
            total += math.sqrt(sum((c - m) ** 2 for c in col) / (batch - 1))
        out.append(total / width)
    return out


def res_deep():
    a = Art("r04", "Thirty relu layers deep, a signal shrinks at every layer unless the weights start at the right "
                   "size; normalisation and shortcuts also keep it the same")
    px0, px1, py0, py1 = 64, 352, 44, 214
    lo, hi = -8.0, 0.5
    n, L = 64, 29                             # 64 inputs a unit; 30 linear layers, so 29 relus
    X = lambda l: px0 + (l - 1) / (L - 1) * (px1 - px0)
    Y = lambda v: py1 - (math.log10(v) - lo) / (hi - lo) * (py1 - py0)
    axes(a, px0, py0 - 6, px1, py1)
    for e, lab in ((-8, "1e-8"), (-6, "1e-6"), (-4, "1e-4"), (-2, "1e-2"), (0, "1")):
        a.line(px0 - 4, Y(10 ** e), px0, Y(10 ** e), "m")
        a.text(px0 - 8, Y(10 ** e) + 3.5, lab, "tm", 9.5, "end", mono=True)
    for l in (1, 10, 20, 29):
        a.line(X(l), py1, X(l), py1 + 4, "m")
        a.text(X(l), py1 + 16, str(l), "tm", 9.5, "middle", mono=True)
    a.text(px0, 30, "spread of each layer's output over a batch, log scale", "tm", 10.5)
    a.text((px0 + px1) / 2, py1 + 32, "relu layer", "tm", 10.5, "middle")
    # each layer multiplies the size by sqrt(n Var(w) / 2): 04.02's derivation
    starts = [("default", 1 / (3 * n), "s", "nn.Linear's start"), ("glorot", 2 / (n + n), "s", "Glorot's"),
              ("he", 2 / n, "a", "He's")]
    factor = {how: f"{math.sqrt(n * var / 2):.2f}".rstrip("0").rstrip(".") for how, var, _, _ in starts}
    assert factor == {"default": "0.41", "glorot": "0.71", "he": "1"}          # 04.02's three numbers
    for how, var, cls, lab in starts:
        spreads = layer_spreads(how)
        assert len(spreads) == L
        clipped(a, [(X(l + 1), Y(v)) for l, v in enumerate(spreads)], (px0, py0 - 6, px1, py1), cls)
        note = f"x{factor[how]} a layer"
        tcls = "ta" if cls == "a" else "t"
        if spreads[-1] >= 10 ** lo:
            y = Y(spreads[-1])
            a.text(px1 + 8, y - 2, lab, tcls, 10.5, weight=600)
            a.text(px1 + 8, y + 12, note, "ta" if cls == "a" else "tm", 10)
        else:                                  # it leaves the frame at the bottom: say so where it does
            out = next(l for l, v in enumerate(spreads) if v < 10 ** lo)
            x = X(out + 0.5) + 8
            a.text(x, py1 - 26, lab, tcls, 10.5, weight=600)
            a.text(x, py1 - 12, f"{note}, on below 1e-8", "tm", 10)
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
    a.text(24, 270, "Each relu layer, its units summing n inputs, multiplies the size of the signal by sqrt(n Var(w) / 2):",
           "tm", 10.5)
    a.text(24, 286, f"{factor['default']} for nn.Linear's start, {factor['glorot']} for Glorot's, {factor['he']} for "
                    "He's.  (Computed here: 30 layers, 64 wide, random inputs.)", "tm", 10.5)
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
    a.text(392, 258, "y = relu(F(x))", "tm", 10.5, "middle", mono=True)
    a.text(528, 258, "y = relu(F(x) + x)", "ta", 10.5, "middle", mono=True)
    # 06.04's recorded long run: its training error at the end, mean over seeds, as the lesson prints it
    rec = os.path.join(ROOT, "tracks", "research", "experiments", "recorded", "resnet")
    err = {}
    for name in ("plain20", "plain56", "residual20", "residual56"):
        runs = sorted(glob.glob(os.path.join(rec, name, "seed*", "summary.json")))
        vals = [json.load(open(p))["train_error"] for p in runs]
        err[name] = f"{sum(vals) / len(vals):.1f}"
    assert err == {"plain20": "71.9", "plain56": "81.8", "residual20": "59.2", "residual56": "55.0"}, err  # 06.04
    a.text(24, 280, "He et al. 2015 on CIFAR-10, run here at laptop size (4000 images, 8 passes, 3 seeds), "
                    "training error at the end:", "tm", 10.5)
    a.text(24, 294, f"plain {err['plain20']}% at 20 layers, {err['plain56']}% at 56; residual {err['residual20']}% "
                    f"at 20, {err['residual56']}% at 56: the deeper plain worse, the deeper residual better.",
           "tm", 10.5)
    return a


# =================================================================== 07 language models

def lm_numbers():
    """07's numbers as its lessons print them: the pair model's bits on the test text, counted here from
    tracks/research/data/tinyshakespeare.txt with 07.01's split and smoothing (k = 0.1), and 07.02's
    recorded long run at a context of 5, the network's mean over seeds and deleted interpolation, read
    from its summaries."""
    import numpy as np
    with open(os.path.join(ROOT, "tracks", "research", "data", "tinyshakespeare.txt"), encoding="ascii") as f:
        text = f.read()
    vocab = sorted(set(text))
    number = {c: i for i, c in enumerate(vocab)}
    V, n = len(vocab), len(text)
    train = np.array([number[c] for c in text[:int(0.9 * n)]])
    test = np.array([number[c] for c in text[int(0.95 * n):]])
    table = np.zeros((V, V))
    np.add.at(table, (train[:-1], train[1:]), 1)
    table += 0.1
    pairs = float(-np.log2((table / table.sum(axis=1, keepdims=True))[test[:-1], test[1:]]).mean())
    rec = os.path.join(ROOT, "tracks", "research", "experiments", "recorded", "nplm")
    nets = [json.load(open(p))["test_bits"] for p in sorted(glob.glob(os.path.join(rec, "context5", "seed*", "summary.json")))]
    inter = json.load(open(os.path.join(rec, "counts", "seed0", "summary.json")))["interpolated"]["5"]
    got = {"blind": f"{math.log2(V):.3f}", "pairs": f"{pairs:.3f}", "network": f"{sum(nets) / len(nets):.3f}",
           "interpolation": f"{inter:.3f}"}
    assert got == {"blind": "6.022", "pairs": "3.599", "network": "2.346", "interpolation": "2.416"}, got  # 07.01, 07.02
    return got


def res_lm():
    a = Art("r07", "Language models from counting to attention: what each model can look back at, and the bits per "
                   "character the lessons measure")
    got = lm_numbers()
    txt = "to be or not to b"
    nxt = "e"
    cw, ch, sx = 15, 20, 150
    a.text(sx, 30, "what each model looks back at", "tm", 10.5)
    rows = [("counts", "of pairs", "what followed 'b', counted;", f"test text: {got['pairs']} bits"),
            ("embeddings", "and a network", "a window of the last 5;", f"test text: {got['network']} bits"),
            ("recurrent", "network", "one state carried along;", "it uses about the last 16"),
            ("attention", "", "copying the row, it weighs", "every position at every step")]
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
                use = 1.0 if back < 5 else 0
            elif r == 2:
                use = 0.85 ** back
            else:
                use = 0.9 if i == 7 else 0.12         # writing its 8th symbol, the weight is on input 8
            if use:
                shade(a, x, y, cw, ch, 0.5 * use)          # at most half strength, so the letter stays readable
            a.box(x, y, cw, ch, "a" if use >= 0.9 else "m", rx=0)
            a.text(x + cw / 2, y + 14, "_" if c == " " else c, "t", 11, "middle", 700 if r == 3 and i == 7 else None,
                   mono=True)
        out = txt[7] if r == 3 else nxt
        cell(a, sx + n * cw + 6, y, cw + 2, ch, "_" if out == " " else out, "a af", "ta", 11, rx=3, weight=700)
        a.text(452, y + 9, d1, "tm", 10.5)
        a.text(452, y + 23, d2, "tm", 10.5)
        if r == 3:
            x0 = sx + 7 * cw + cw / 2
            a.path(f"M{sx + n * cw + 15} {y + ch + 2} C {sx + n * cw + 15} {y + ch + 18}, {x0} {y + ch + 18}, "
                   f"{x0} {y + ch + 4}", "a", arrow=True)
            a.text((x0 + sx + n * cw + 15) / 2, y + ch + 27, "the 8th symbol it writes: most weight on input 8",
                   "ta", 10, "middle")
    a.text(sx + n * cw + 14, 30, "next", "ta", 10.5, "middle")
    a.text(24, 270, "Scored in bits per character on the test text, -log2 p of the character that came, averaged; "
                    "'_' is a space.", "tm", 10.5)
    a.text(24, 286, f"Blind guess {got['blind']}; pairs {got['pairs']}; deleted interpolation of 5 characters "
                    f"{got['interpolation']}; the network of 5, in a 20-minute run, {got['network']}.", "tm", 10.5)
    return a


# =================================================================== 08 transformer

def gpt_numbers():
    """08's numbers as 08.04 prints them, from its recorded long run (tracks/research/experiments/recorded/gpt/):
    the GPT's settings and weight count (V W + context W + L (12 W^2 + 13 W) + 2 W, as models/gpt.py's GPT has),
    each dropout's mean test bits over its seeds, whether every seed without dropout turned up before the end,
    and module 07's best, 07.02's recorded network mixed with interpolation at 8 characters."""
    rec = os.path.join(ROOT, "tracks", "research", "experiments", "recorded")
    cfg = json.load(open(os.path.join(rec, "gpt", "dropout0.2", "seed0", "config.json")))
    V, W, L, ctx = 65, cfg["width"], cfg["layers"], cfg["context"]
    weights = V * W + ctx * W + L * (12 * W * W + 13 * W) + 2 * W
    with open(os.path.join(rec, "gpt", "output.txt")) as f:
        printed = f.read()
    assert f"{weights:,} weights" in printed, weights

    def runs(dropout):
        found = sorted(glob.glob(os.path.join(rec, "gpt", f"dropout{dropout}", "seed*", "summary.json")))
        return [json.load(open(p)) for p in found]
    none, some = runs("0.0"), runs("0.2")
    mixed = [json.load(open(p))["mixed_bits"] for p in sorted(glob.glob(os.path.join(rec, "nplm", "context8", "seed*",
                                                                                       "summary.json")))]
    got = {"layers": L, "heads": cfg["heads"], "width": W, "steps": cfg["steps"], "weights": f"{weights:,}",
           "seeds": len(some), "with": f"{sum(s['test_bits'] for s in some) / len(some):.3f}",
           "without": f"{sum(s['test_bits'] for s in none) / len(none):.3f}",
           "turned": all(s["lowest_step"] < cfg["steps"] - 1 and s["end_held_bits"] > s["lowest_held_bits"] + 0.02
                         for s in none),
           "best07": f"{sum(mixed) / len(mixed):.3f}"}
    assert got == {"layers": 6, "heads": 6, "width": 192, "steps": 2800, "weights": "2,731,200", "seeds": 2,
                   "with": "2.226", "without": "2.361", "turned": True, "best07": "2.283"}, got  # 08.04
    return got


def res_gpt():
    a = Art("r08", "A GPT: the causal mask lets each position look only back; each block's attention moves information "
                   "between positions and its MLP changes each position in place, both added to the residual stream")
    got = gpt_numbers()
    toks = list("Not_in")
    n = len(toks)
    gx, gy, cw, ch = 60, 52, 30, 24
    a.text(24, 30, "the causal mask, added to the scores", "ta", 10.5, weight=600)
    for j, t in enumerate(toks):
        a.text(gx + j * cw + cw / 2, gy - 6, t, "tm", 10.5, "middle", mono=True)
    for i in range(n):
        a.text(gx - 8, gy + i * ch + 16, toks[i], size=11, anchor="end", mono=True, weight=600)
        for j in range(n):
            x, y = gx + j * cw, gy + i * ch
            if j <= i:
                shade(a, x + 1, y + 1, cw - 2, ch - 2, 0.35)
                a.text(x + cw / 2, y + 16, "0", "ta", 10, "middle", mono=True)
            else:
                a.add(f'<rect class="fs" x="{x}" y="{y}" width="{cw}" height="{ch}"/>')
                a.text(x + cw / 2, y + 15.5, "-inf", "tm", 8.5, "middle", mono=True)
    for k in range(n + 1):
        a.line(gx + k * cw, gy, gx + k * cw, gy + n * ch, "m")
        a.line(gx, gy + k * ch, gx + n * cw, gy + k * ch, "m")
    a.text(24, gy + n * ch + 20, "row i looks at columns 0 to i: each", "tm", 10.5)
    a.text(24, gy + n * ch + 35, "position's guess sees only the past", "tm", 10.5)

    ys = 160
    a.text(286, 30, f"one block of {got['layers']}, on the residual stream", "tm", 10.5)
    a.text(282, ys + 4, "x", size=12, anchor="end", mono=True)
    a.line(288, ys, 612, ys, "a", arrow=True)
    for bx, name, sub, note in ((294, "attention", f"{got['heads']} heads of {got['width'] // got['heads']}",
                                 "between positions"),
                                (452, "MLP", f"{got['width']} -> {4 * got['width']} -> {got['width']}",
                                 "each position alone")):
        a.path(f"M{bx} {ys} V 92 H {bx + 8}", "s")
        cell(a, bx + 8, 80, 30, 24, "ln", "s f", "t", 11, rx=6)
        a.line(bx + 38, 92, bx + 46, 92, "s")
        a.box(bx + 46, 72, 92, 40, "s fs", rx=8)
        a.text(bx + 92, 89, name, size=12, anchor="middle", weight=700)
        a.text(bx + 92, 104, sub, "tm", 10, "middle")
        px = bx + 148
        a.path(f"M{bx + 138} 92 H {px} V {ys - 10}", "s", arrow=True)
        plus(a, px, ys)
        a.text(bx + 92, 130, note, "ta", 10.5, "middle", 600)
    a.text(452, ys + 22, f"the residual stream: {got['width']} numbers per position", "ta", 10.5, "middle")
    a.text(286, 214, "x = x + attention(ln(x)); x = x + mlp(ln(x))", size=10.5, mono=True)
    a.text(286, 230, "scores: softmax(q k.T / sqrt(d_head) + mask) v", "tm", 10.5, mono=True)
    a.text(24, 270, f"The recorded run, {got['layers']} blocks, width {got['width']}, {got['weights']} weights, "
                    f"{got['steps']} steps, {got['seeds']} seeds each, bits per character on the test text:", "tm", 10.5)
    a.text(24, 286, f"with dropout 0.2, {got['with']}; without, {got['without']}, its held-out curve turned up; "
                    f"module 07's best, {got['best07']}.", "tm", 10.5)
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
    a = Art("r15", "Your own result: a loop of question, prediction, experiment and doubt, and a way out to a short "
                   "paper and a public repository anyone can rerun")
    nodes = {"Q": (24, 46, "a small question"), "P": (196, 46, "a prediction"), "E": (196, 146, "the experiment"),
             "D": (24, 146, "try to break it")}
    for _, (x, y, t) in nodes.items():
        a.box(x, y, 124, 36, "s f", rx=18)
        a.text(x + 62, y + 23, t, size=12, anchor="middle", weight=600)
    a.line(148, 64, 194, 64, arrow=True)
    a.line(258, 82, 258, 144, arrow=True)
    a.line(196, 164, 150, 164, arrow=True)
    a.line(86, 146, 86, 84, "m", arrow=True)
    a.text(95, 120, "it breaks: refine", "tm", 10.5)
    a.path("M86 182 V 236 H 330 V 100 H 342", "a", arrow=True)
    a.text(208, 228, "it survives: write it up", "ta", 11, "middle", 600)
    # the paper, a schematic page
    px, pw = 346, 76
    a.box(px, 30, pw, 140, "s f", rx=6)
    a.add(f'<rect class="s fs" x="{px + 10}" y="42" width="{pw - 20}" height="9" rx="2" {SW}/>')
    for y in (62, 71, 80):
        a.line(px + 10, y, px + pw - 10, y, "m")
    a.line(px + 14, 128, px + 14, 92, "m"); a.line(px + 14, 128, px + pw - 12, 128, "m")
    poly(a, [(px + 18, 122), (px + 27, 116), (px + 36, 117), (px + 45, 106), (px + 54, 101), (px + 62, 96)], "s")
    for y in (142, 151, 160):
        a.line(px + 10, y, px + pw - 10 if y < 160 else px + pw - 30, y, "m")
    a.text(px + pw / 2, 188, "paper", size=12, anchor="middle", weight=700)
    # the repository: the track's own layout, and the files every run leaves
    rx, rw = 436, 180
    a.box(rx, 30, rw, 140, "s fs", rx=6)
    tree = [("repo/", 0, "t"), ("engine/  lab/  data/", 1, "tm"), ("experiments/<name>.py", 1, "tm"),
            ("runs/<name>/seed0/", 1, "tm"), ("config.json", 2, "ta"), ("log.jsonl", 2, "ta"), ("summary.json", 2, "ta")]
    for i, (t, depth, cls) in enumerate(tree):
        a.text(rx + 10 + 14 * depth, 50 + i * 17, t, cls, 10, weight=600 if i == 0 else None, mono=True)
    a.text(rx + rw / 2, 188, "code, and every run", size=12, anchor="middle", weight=700)
    a.text(px, 216, "$ python3 -m experiments.<name> key=value", size=10.5, mono=True, weight=600)
    a.text(px, 232, "reruns it; each run's config.json records every", "tm", 10.5)
    a.text(px, 247, "setting it used and its seed", "tm", 10.5)
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


def built(mid):
    """The lessons folder of module mid in tracks/research, or None while the module is not built."""
    found = sorted(glob.glob(os.path.join(LESSONS, f"{mid}-*")))
    return found[0] if found else None


def main(argv):
    out = files(set(argv) or None)
    paths = {}
    for rel, text in out.items():
        paths[os.path.join(OUT, rel)] = text
        mid, name = rel.split("/")
        if built(mid):                           # a built module's copy, so the two never drift
            paths[os.path.join(built(mid), name)] = text
    for path, text in paths.items():
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(text)
    bad = check(out)
    for b in bad:
        print("problem:", b)
    copies = len(paths) - len(out)
    print("wrote", len(out), "files under", os.path.relpath(OUT, ROOT), "and", copies, "under",
          os.path.relpath(LESSONS, ROOT))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
