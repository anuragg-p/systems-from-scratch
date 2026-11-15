"""Figures for research module 04, Deep networks that train (lessons 04.01-04.06).

    RESEARCH_FIGS_CACHE=DIR python3 -B art/research/figs04.py      (DIR keeps the runs between tries)

Every number drawn comes from a run of the code as it stands at the lesson (figart.experiment, at=
the lesson), never from a number typed in here. Two kinds of run:

- the lesson's experiment with its default settings, the run the page's "Run it" shows: the curves,
  the dots over seeds and the table of checks are read from its logs, summaries and printed lines;
- for the per-layer pictures, the same measurement the experiment prints for a few layers, taken
  for every layer: experiments.deep.layer_stats on the same network, seed and batch (every_layer()
  below). The generator stops unless those numbers agree with the lines the experiment printed.

The diagrams with no numbers (where batch norm sits, the residual block) draw the code's structure.
"""
import json
import math
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)                          # art/research/: figlib, figart
sys.path.insert(0, os.path.dirname(HERE))         # art/: steps.py, for the stepped figure
import figart  # noqa: E402
import figlib  # noqa: E402
import steps  # noqa: E402
from figlib import Fig, sig, tw, write  # noqa: E402

MOD = "04"


# ------------------------------------------------------------------ runs

STATS = '''
import json
import engine as torch
from data import mnist
from experiments.deep import layer_stats, network
{imports}
x, y = mnist.load("train")
xb, yb = torch.from_numpy(x[:128]), torch.from_numpy(y[:128])
out = {{}}
for name in {names!r}:
    torch.manual_seed(0)
    out[name] = layer_stats(torch, {make}, xb, yb)
print(json.dumps(out))
'''


def every_layer(at, names, make, imports=""):
    """{name: [layer_stats' dict per activation layer]} for each name, the network made by the
    expression make (name in scope) in the project at lesson `at`, seed 0, the first batch of 128."""
    d = figart.project(at)
    code = STATS.format(imports=imports, names=list(names), make=make)
    env = dict(os.environ, PYTHONPATH=d, PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run([sys.executable, "-B", "-c", code], cwd=d, env=env, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"every_layer at {at} failed:\n{r.stdout[-1500:]}{r.stderr[-1500:]}")
    return json.loads(r.stdout)


def same(what, mine, printed):
    if mine != printed:
        raise SystemExit(f"{what}: the figure has {mine!r}, the experiment printed {printed!r}")


def runs_of(r, label):
    return figart.seed_dirs(os.path.join(r.runs, label))


# ------------------------------------------------------------------ drawing helpers

def bar_axes(f, x0, x1, y, h, lo, hi, label=None):
    """A log axis for per-layer bars, from x0 to x1 in pixels, y the top, h the height; its ticks
    every second power of ten. Returns the Axes (y in data units)."""
    ax = figart.Axes(f, x0, y, x1 - x0, h, (x0, x1), (lo, hi), False, True)
    tens = [10.0 ** k for k in range(round(math.log10(lo)), round(math.log10(hi)) + 1) if k % 2 == 0]
    ax.draw(xticks=[], yticks=tens, frame=False)
    f.line(x0, y + h, x1, y + h, "m")
    if label:
        f.text(x0 - 6, y - 8, label, "tm", 11.5)
    return ax


def bar(f, ax, x, w, v, cls):
    top = ax.py(min(max(v, ax.ylim[0]), ax.ylim[1]))
    f.rect(x, top, w, ax.y + ax.h - top, cls, 1)
    return top


def key(f, x, y, items):
    """A legend of filled squares: [(label, box class, text class)], in one row from x."""
    for label, cls, tcls in items:
        f.rect(x, y - 10, 10, 10, cls, 1)
        f.text(x + 15, y - 1, label, tcls, 11)
        x += 15 + tw(label, 11) + 18
    return x


def node(f, x, y, w, h, label, cls="s f", tcls="t", size=11.5, mono=True, dash=False, sub=None):
    f.label_box(x, y, w, h, label, cls, tcls, size, mono, 6, None, dash, sub)
    return x + w


# ------------------------------------------------------------------ 04.01

def layers0401():
    """The signal's size layer by layer, then the gradient's on the way back: 20 relu layers as
    nn.Linear starts them, one batch. Stepped."""
    at = "04.01"
    r = figart.experiment("deep_stats", at=at)
    stats = every_layer(at, ["relu"], "network(torch, 20, 64, name)")["relu"]
    printed = re.search(r"relu, 20 layers.*?\n(.*?)  one pass", r.out, re.S).group(1)
    for m in re.finditer(r"^\s+(\d+)\s+(\S+)\s+(\S+)\s+\d+%$", printed, re.M):
        k = int(m.group(1))
        same(f"layer {k}", (f"{stats[k - 1]['spread']:.2e}", f"{stats[k - 1]['grad']:.2e}"), (m.group(2), m.group(3)))
    spread = [s["spread"] for s in stats]
    grad = [s["grad"] for s in stats]
    n = len(stats)                                       # 19 activation layers

    f = Fig("layers0401", "The spread of each layer's output over the batch, and the gradient arriving at it: "
                          "20 relu layers as nn.Linear starts them", 330)
    sizes = [784] + [64] * n + [10]
    box = (40, 6, 586, 86)
    xs = figart.network(f, box, sizes, max_units=3)
    step = xs[1] - xs[0]
    foot = 16
    gap = (box[3] - foot) / 3
    y0 = box[1] + (box[3] - foot) / 2 - gap
    rr = max(3.0, min(9.0, step * 0.22, (box[3] - foot) / (3 * 2.6)))
    f.text(xs[0], box[1] + box[3] + 10, "pixels", "tm", 10, "middle")
    f.text(xs[-1], box[1] + box[3] + 10, "scores", "tm", 10, "middle")

    lo, hi = 1e-12, 3.0
    ax = bar_axes(f, xs[1] - step / 2, xs[n] + step / 2, 132, 160, lo, hi)
    f.text(ax.x - 6, 120, "size, log scale", "tm", 11)
    key(f, 352, 122, [("spread over the batch", "a af", "ta"), ("gradient arriving", "s fs", "t")])
    for k in range(1, n + 1):
        f.text(xs[k], ax.y + ax.h + 14, str(k), "tm", 10, "middle", mono=True)
    f.text((ax.x + ax.x + ax.w) / 2, ax.y + ax.h + 30, "relu layer", "tm", 11, "middle")
    bw = 9

    def lit(k):
        for j, y in enumerate([y0, y0 + gap, y0 + 2 * gap]):
            if j != 1:
                f.circle(xs[k], y, rr, "a af")
        f.text(xs[k], y0 + gap + 4, "...", "ta", 11, "middle", mono=True)
        f.text(xs[k], box[1] + box[3] - foot + 13, "64", "ta", 10, "middle", mono=True)
        f.text(xs[k], ax.y + ax.h + 14, str(k), "ta", 10, "middle", 700, mono=True)

    def bars(upto_spread, from_grad, here, show):
        for k in range(1, n + 1):
            if k <= upto_spread:
                bar(f, ax, xs[k] - bw, bw - 1, spread[k - 1], "a af")
            if from_grad is not None and k >= from_grad:
                bar(f, ax, xs[k], bw - 1, grad[k - 1], "s fs")
        what, v, cls = (("spread", spread[here - 1], "ta") if show == "spread"
                        else ("gradient arriving", grad[here - 1], "t"))
        f.text(ax.x + ax.w, ax.y + 16, f"layer {here}, {what}: {sig(v)}", cls, 12, "end", 700, mono=True)

    def factor(a, b):
        return (spread[b - 1] / spread[a - 1]) ** (1 / (b - a))

    forward = [1, 2, 3, 4, 5, 10, 15, n]
    for i, k in enumerate(forward):
        if k == 1:
            cap = (f"Forward, layer 1: its outputs differ from one digit to the next by {sig(spread[0])} "
                   f"(the spread over the batch)")
        elif k == n:
            cap = (f"Layer {k}: {sig(spread[k - 1])}. Every digit gives the last layers almost the same output: "
                   f"x{factor(1, k):.2f} a layer, {k - 1} times")
        else:
            prev = forward[i - 1]
            each = f"x{factor(prev, k):.2f}" + (" a layer" if k - prev > 1 else "")
            cap = f"Layer {k}: {sig(spread[k - 1])}, {each} from layer {prev}"
        with steps.step(f, cap):
            lit(k)
            bars(k, None, k, "spread")
    for k in [n, 15, 10, 5, 1]:
        if k == n:
            cap = f"Backward, from the loss: the gradient arriving at layer {k} is {sig(grad[k - 1])}"
        elif k == 1:
            cap = (f"Layer 1: {sig(grad[0])}. The first layers' weights get almost no gradient, "
                   f"so training cannot move them")
        else:
            cap = f"Layer {k}: {sig(grad[k - 1])}; the gradient shrinks on the way back, as the signal did on the way in"
        with steps.step(f, cap):
            lit(k)
            bars(n, k, k, "grad")
    steps.check(f.svg())
    return f


# ------------------------------------------------------------------ 04.02

def variance0402():
    """One layer's output variance from its input's: the derivation as a picture."""
    f = Fig("variance0402", "One unit of a layer: 64 inputs, each times its weight, summed, then the relu", 250)
    xs_in, xs_w, xs_sum, xs_relu = 40, 150, 330, 470
    ys = [40, 78, 116, 182]
    labels = ["x1", "x2", "x3", "x64"]
    for y, lab in zip(ys, labels):
        f.circle(xs_in, y, 13, "s f")
        f.text(xs_in, y + 4, lab, "t", 11, "middle", mono=True)
        f.line(xs_in + 15, y, xs_sum - 26, 116, "m", arrow=True)
        f.text((xs_in + xs_sum) / 2 - 40, y + (116 - y) * 0.35 - 6, lab.replace("x", "w"), "tm", 10.5, mono=True)
    f.text(xs_in, 154, "...", "tm", 12, "middle", mono=True)
    f.circle(xs_sum, 116, 24, "s f")
    f.text(xs_sum, 121, "sum", "t", 12, "middle", 600)
    f.line(xs_sum + 26, 116, xs_relu - 32, 116, "s", arrow=True)
    f.label_box(xs_relu - 30, 100, 60, 32, "relu", "s f", "t", 12)
    f.line(xs_relu + 32, 116, 590, 116, "a", arrow=True)
    f.text(560, 106, "out", "ta", 11.5, "middle", 600, mono=True)

    f.text(xs_in - 26, 216, "each input:", "tm", 11)
    f.text(xs_in - 26, 231, "E[x^2] = q", "t", 11.5, mono=True)
    f.text((xs_in + xs_sum) / 2 - 8, 216, "each weight: mean 0,", "tm", 11, "middle")
    f.text((xs_in + xs_sum) / 2 - 8, 231, "Var(w), apart from x", "t", 11.5, "middle", mono=True)
    f.text(xs_sum + 10, 166, "z = w1 x1 + ... + w64 x64", "t", 11.5, "middle", mono=True)
    f.text(xs_sum + 10, 184, "Var(z) = 64 Var(w) q", "ta", 12, "middle", 600, mono=True)
    f.text(xs_relu + 50, 158, "z is even about 0; relu", "tm", 11, "middle")
    f.text(xs_relu + 50, 173, "keeps the half above 0:", "tm", 11, "middle")
    f.text(xs_relu + 50, 191, "E[out^2] = Var(z) / 2", "ta", 12, "middle", 600, mono=True)
    f.text(xs_relu + 50, 231, "same size: Var(w) = 2 / 64", "ta", 12, "middle", 700, mono=True)
    return f


def starts0402():
    """The spread over the batch at every layer of the 30-layer network, for each start, against
    what the derivation predicts from layer 1."""
    at = "04.02"
    r = figart.experiment("init", at=at)
    stats = every_layer(at, ["default", "glorot", "he"], "initialise(network(torch, 30, 64), name)",
                        "from experiments.init import initialise")
    for how in ("default", "glorot", "he"):
        m = re.search(rf"^{how}\s*: spread at layer 1 (\S+), at layer 29 (\S+);", r.out, re.M)
        same(how, (f"{stats[how][0]['spread']:.2e}", f"{stats[how][-1]['spread']:.2e}"), (m.group(1), m.group(2)))
    f = Fig("starts0402", "Spread over the batch at each of the 29 relu layers, three starts: measured (solid) "
                          "and predicted from layer 1 (dashed)", 330)
    series = []
    names = {"default": ("nn.Linear's start", "m", 1 / 6), "glorot": ("Glorot", "s", 1 / 2), "he": ("He", "a", 1.0)}
    for how, (label, style, var) in names.items():
        s = [d["spread"] for d in stats[how]]
        ks = list(range(1, len(s) + 1))
        pred = [s[0] * math.sqrt(var) ** (k - 1) for k in ks]
        series.append(figart.Series("", ks, pred, style, dash="5 4", width=1.25))
        series.append(figart.Series(label, ks, s, style, width=2))
    ax = figart.plot(f, (8, 4, 624, 322), series, xlabel="relu layer", ylabel="spread over the batch (log scale)",
                     logy=True, ylim=(1e-9, 3), xlim=(1, 29), legend="right",
                     xticks=[1, 5, 10, 15, 20, 25, 29])
    for how, (label, style, var) in names.items():
        s = [d["spread"] for d in stats[how]]
        ax.note(29, s[-1], f"predicted x{math.sqrt(var):.2f} a layer", figart.TEXT[style], 10.5, "end", dx=-4,
                dy={"default": -8, "glorot": 16, "he": 16}[how])
    figart.legend(f, ax.x + ax.w + 14, ax.y + 10 + 3 * 17 + 6, [("predicted", "m", "5 4")])
    return f


# ------------------------------------------------------------------ 04.03

def where0403():
    """Where batch norm sits, and what it averages over: one feature, down the batch."""
    f = Fig("where0403", "Batch norm between a linear layer and its activation: each feature normalised over "
                         "the examples of the batch", 270)
    y, h = 22, 34
    x = 14
    x = node(f, x, y, 92, h, "Linear") + 14
    f.line(x - 14, y + h / 2, x - 2, y + h / 2, "s", arrow=True)
    x = node(f, x, y, 118, h, "BatchNorm1d", "a af", "ta") + 14
    f.line(x - 14, y + h / 2, x - 2, y + h / 2, "s", arrow=True)
    x = node(f, x, y, 92, h, "Sigmoid") + 14
    f.line(x - 14, y + h / 2, x - 2, y + h / 2, "s", arrow=True)
    x = node(f, x, y, 92, h, "Linear") + 14
    f.line(x - 14, y + h / 2, x - 2, y + h / 2, "s", arrow=True)
    f.text(x + 4, y + h / 2 + 4, "...", "tm", 13, mono=True)

    gx, gy, cw, ch = 74, 104, 34, 20
    rows, cols, col = 5, 7, 2
    grid = [[None] * cols for _ in range(rows)]
    figart.tensor(f, gx, gy, grid, (cw, ch), shape=False, here=[(i, col) for i in range(rows)])
    f.text(gx - 8, gy + rows * ch / 2 + 4, "60 examples", "tm", 11, "end")
    f.text(gx + (col + 1) * cw + 4, gy - 8, "100 features, one column each", "tm", 11)
    f.line(gx + col * cw + cw / 2, gy + rows * ch + 4, gx + col * cw + cw / 2, gy + rows * ch + 22, "a", arrow=True)
    f.text(gx + col * cw + cw / 2, gy + rows * ch + 38, "mean and sd of this column", "ta", 11.5, "middle", 600)
    f.text(gx + col * cw + cw / 2, gy + rows * ch + 53, "over the 60 examples", "ta", 11.5, "middle")
    f.path(f"M{gx + col * cw + cw / 2:.1f} {y + h + 4} L{gx + col * cw + cw / 2:.1f} {gy - 22}", "m", dash=True)
    tx = 380
    f.text(tx, 124, "for every number h in the column:", "tm", 11.5)
    f.text(tx, 148, "(h - mean) / sd", "ta", 13, weight=600, mono=True)
    f.text(tx, 168, "   * weight + bias", "t", 13, mono=True)
    f.text(tx, 194, "weight and bias are learned,", "tm", 11.5)
    f.text(tx, 210, "one pair per feature", "tm", 11.5)
    return f


def sigmoid0403():
    """Test accuracy as the sigmoid network trains, with and without batch norm (their figure 1(a),
    at laptop size)."""
    at = "04.03"
    r = figart.experiment("batchnorm", at=at)
    series = []
    for label, name, style in (("sigmoid-none", "no norm", "s"), ("sigmoid-batch", "batch norm", "a")):
        xs, mean, lo, hi = figart.over_seeds(runs_of(r, label), "test_accuracy")
        series.append(figart.Series(name, xs, mean, style, lo=lo, hi=hi))
    f = Fig("sigmoid0403", "Test accuracy of the 3-hidden-layer sigmoid network every 250 steps, with and without "
                           "batch norm: mean of 3 seeds, the band min to max", 290)
    ax = figart.plot(f, (8, 4, 624, 282), series, xlabel="step", ylabel="test accuracy", ylim=(0.2, 1.0),
                     xlim=(0, 3000), legend="right")
    ax.hline(0.9, "90%", side="left")
    for s in series:
        first = next(x for x, v in zip(s.xs, s.ys) if v >= 0.9)
        ax.dot(first, s.ys[s.xs.index(first)], "a fa" if s.style == "a" else "s f", 3.5)
        ax.note(first, s.ys[s.xs.index(first)], f"90% at step {first}", figart.TEXT[s.style], 10.5,
                dx=6, dy=-8 if s.style == "a" else 16)
    return f


# ------------------------------------------------------------------ 04.04

def axes0404():
    """What each normalisation averages over, and a batch of two under batch norm."""
    at = "04.04"
    r = figart.experiment("layernorm", at=at)
    f = Fig("axes0404", "Batch norm averages each feature down the batch; layer norm averages each example "
                        "across its features", 270)
    cw, ch, rows, cols = 32, 20, 4, 6
    empty = [[None] * cols for _ in range(rows)]
    for gx, title, here, note1, note2, cls in (
            (40, "batch norm", [(i, 1) for i in range(rows)], "one feature,", "over the batch", "t"),
            (360, "layer norm", [(2, j) for j in range(cols)], "one example,", "over its own features", "ta")):
        f.text(gx, 22, title, cls, 13, weight=700)
        figart.tensor(f, gx, 36, empty, (cw, ch), shape=False, here=here)
        f.text(gx, 36 + rows * ch + 17, f"{note1} {note2}", "tm" if cls == "t" else "ta", 11.5)
    f.text(296, 36 + rows * ch / 2 - 2, "rows: examples", "tm", 10.5, "middle")
    f.text(296, 36 + rows * ch / 2 + 12, "columns: features", "tm", 10.5, "middle")
    m = re.search(r"^3\. batch norm on a batch of two, the four outputs of a linear layer: (.*)$", r.out, re.M)
    rows2 = [[v.strip() for v in row.split()] for row in m.group(1).split(";")]
    y = 176
    f.text(40, y, "batch norm on a batch of two (the run): every number is about -1 or +1", "t", 12, weight=600)
    figart.tensor(f, 40, y + 14, rows2, (64, 24), shape=False, size=11.5)
    f.text(40 + 4 * 64 + 14, y + 30, "a column of two numbers has its mean halfway", "tm", 11)
    f.text(40 + 4 * 64 + 14, y + 45, "between them, and each is one sd from it:", "tm", 11)
    f.text(40 + 4 * 64 + 14, y + 60, "whatever the digit, -1 and +1", "tm", 11)
    return f


def batch0404():
    """Test accuracy after 3000 steps, batch norm against layer norm, at batches of 2 and of 60."""
    at = "04.04"
    r = figart.experiment("layernorm", at=at)
    groups = []
    for size in (2, 60):
        for norm, name, style in (("batch", "batch norm", "s"), ("layer", "layer norm", "a")):
            acc = [figart.summary(d)["test_accuracy"] for d in runs_of(r, f"{norm}-batch{size}")]
            groups.append((f"{name}\nbatches of {size}", acc, style))
    f = Fig("batch0404", "Test accuracy after 3000 steps of the sigmoid network: each seed a ring, the mean a bar",
            270)
    figart.seeds_chart(f, (8, 4, 624, 262), groups, ylabel="test accuracy", ylim=(0.4, 1.0))
    return f


# ------------------------------------------------------------------ 04.05

def block0405():
    """A residual block of two layers beside a plain pair, the shortcut in the accent."""
    f = Fig("block0405", "A plain pair of layers, and the same pair as a residual block: the input is added back "
                         "before the last relu", 262)
    y1, y2, h = 30, 178, 32
    for y, title, short in ((y1, "plain", False), (y2, "residual block", True)):
        f.text(14, y - (58 if short else 12), title, "ta" if short else "t", 12.5, weight=700)
        x = 14
        f.text(x + 8, y + h / 2 + 4, "x", "t", 13, "middle", 600, mono=True)
        x += 22
        parts = ["Linear", "BN", "relu", "Linear", "BN"] + (["+"] if short else []) + ["relu"]
        start = x
        plus_x = None
        for p in parts:
            w = 34 if p == "+" else (40 if p in ("BN",) else (48 if p == "relu" else 62))
            f.line(x, y + h / 2, x + 14, y + h / 2, "s", arrow=True)
            x += 16
            if p == "+":
                f.circle(x + w / 2, y + h / 2, 14, "a af")
                f.text(x + w / 2, y + h / 2 + 5, "+", "ta", 15, "middle", 700, mono=True)
                plus_x = x + w / 2
            else:
                node(f, x, y, w, h, p, size=11.5)
            x += w + 2
        f.line(x, y + h / 2, x + 14, y + h / 2, "s", arrow=True)
        f.text(x + 22, y + h / 2 + 4, "out", "t", 12, weight=600, mono=True)
        if short:
            sx = start - 4
            f.path(f"M{sx:.1f} {y + h / 2:.1f} L{sx:.1f} {y - 24:.1f} L{plus_x:.1f} {y - 24:.1f} "
                   f"L{plus_x:.1f} {y + h / 2 - 16:.1f}", "a", arrow=True)
            f.text((sx + plus_x) / 2, y - 30, "the shortcut: x itself", "ta", 11.5, "middle", 600)
            f.text(14, y + h + 26, "backward: the gradient of out reaches x along the shortcut whatever the "
                   "layers in between do to theirs", "tm", 11)
        else:
            f.text(14, y + h + 26, "backward: the gradient reaches x only through both layers", "tm", 11)
    return f


def depth0405():
    """Training cost after one pass, plain against residual, 8 and 32 layers, over seeds."""
    at = "04.05"
    r = figart.experiment("residual", at=at)
    groups = []
    for kind, style in (("plain", "s"), ("residual", "a")):
        for depth in (8, 32):
            dirs = runs_of(r, f"{kind}{depth}")
            cost = [figart.summary(d)["train_cost"] for d in dirs]
            g = sum(figart.summary(d)["first_layer_grad"] for d in dirs) / len(dirs)
            groups.append((f"{kind} {depth}\ngradient at layer 1: {sig(g, 2)}", cost, style))
    f = Fig("depth0405", "Training cost after one pass over seeds: plain and residual, 8 and 32 layers", 290)
    figart.seeds_chart(f, (8, 4, 624, 282), groups, ylabel="training cost after one pass", ylim=(0, 1.2))
    return f


# ------------------------------------------------------------------ 04.06

CHECK_NAMES = ["starting loss", "one batch", "fresh gradients", "beats chance", "same answers"]


def checks0406():
    """The table the bugs experiment prints: each bug against each check."""
    at = "04.06"
    r = figart.experiment("bugs", at=at)
    rows = []
    for line in r.out.splitlines():
        m = re.match(r"^(\S.{0,19})(\s+(?:ok|FAILS \d/\d)){5}\s*$", line)
        if m:
            name = line[:20].strip()
            cells = re.findall(r"ok|FAILS \d/\d", line[20:])
            rows.append((name, cells))
    if len(rows) != 6:
        raise SystemExit(f"bugs: expected 6 rows, read {len(rows)}:\n{r.out}")
    fired = [[j for j, c in enumerate(cells) if c != "ok"] for _, cells in rows]
    if fired[0] or any(len(fj) != 1 for fj in fired[1:]) or len({fj[0] for fj in fired[1:]}) != 5:
        raise SystemExit(f"bugs: not one check per bug: {fired}")
    f = Fig("checks0406", "Each script against each check, 3 seeds: a check that fires is lit", 260)
    x0, y0, cw, rh = 168, 54, 92, 30
    for j, c in enumerate(CHECK_NAMES):
        a, b = c.split(" ", 1)
        f.text(x0 + j * cw + cw / 2, y0 - 26, f"{j + 1}. {a}", "t", 11.5, "middle", 600)
        f.text(x0 + j * cw + cw / 2, y0 - 11, b, "t", 11.5, "middle", 600)
    for i, (name, cells) in enumerate(rows):
        y = y0 + i * rh
        label = "the correct script" if name == "none" else name
        f.text(x0 - 12, y + rh / 2 + 4, label, "t", 12, "end",
               700 if name == "none" else None, mono=name != "none")
        for j, c in enumerate(cells):
            x = x0 + j * cw
            fired = c != "ok"
            f.rect(x + 3, y + 3, cw - 6, rh - 6, "a af" if fired else "m f", 4)
            f.text(x + cw / 2, y + rh / 2 + 4, c.lower() if fired else "ok", "ta" if fired else "tm", 11.5,
                   "middle", 700 if fired else None, mono=True)
    f.text(x0, y0 + 6 * rh + 22, "Each bug fires exactly one check, and each check catches exactly one bug.",
           "tm", 11.5)
    return f


FIGURES = [
    ("04.01-layers", layers0401),
    ("04.02-variance", variance0402),
    ("04.02-starts", starts0402),
    ("04.03-where", where0403),
    ("04.03-sigmoid", sigmoid0403),
    ("04.04-axes", axes0404),
    ("04.04-batch", batch0404),
    ("04.05-block", block0405),
    ("04.05-depth", depth0405),
    ("04.06-checks", checks0406),
]


def main(argv):
    names = [n for n, _ in FIGURES]
    want = argv or names
    for name in want:
        if name not in names:
            raise SystemExit(f"no figure {name} (have: {', '.join(names)})")
    for name, make in FIGURES:
        if name in want:
            print(write(MOD, name, make()))


if __name__ == "__main__":
    main(sys.argv[1:])
