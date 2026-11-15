"""Figures for research module 05, Generalisation (lessons 05.01-05.04).

    python3 -B art/research/figs05.py [05.02 ...]      all of them, or those whose name starts so

Every curve, bar and number comes from a run of the reference code (tracks/research), with the
settings the lesson's page runs, so the figure and the page agree:

  05.01  python3 -m experiments.random_labels     (3 seeds, 60 epochs): the curves; the sizes of
         the three sets from the run's config.json and from MNIST itself
  05.02  python3 -m experiments.regularise        (3 seeds): validation and test error per seed;
         the dropout masks from F.dropout of the project at 05.02, after torch.manual_seed(0)
         (the page's own run checks the expected value over a million numbers)
  05.03  python3 -m experiments.augment           (3 seeds): training and test error per seed;
         the shifted digit from data.augment.shift of the project at 05.03, on MNIST's first
         training image, with np.random.default_rng(0)
  05.04  python3 -m experiments.double_descent    (3 seeds): test error, size of the weights and
         training error against p, from each seed's log

MNIST must be in the cache (python3 -m data.fetch mnist, in tracks/research). Set
RESEARCH_FIGS_CACHE=DIR while working on the drawing, so the runs (one to two minutes each) are
made once.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)                          # art/research/: figlib, figart
import figart  # noqa: E402
import figlib  # noqa: E402
from figlib import Fig, sig, tw, write  # noqa: E402

MOD = "05"


def in_project(at, code):
    """Run python code in the project as it stands at lesson `at`; what it prints, as JSON."""
    d = figart.project(at)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=d)
    r = subprocess.run([sys.executable, "-B", "-c", code], cwd=d, env=env, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"python in the project at {at} failed:\n{r.stdout[-1500:]}{r.stderr[-1500:]}")
    return json.loads(r.stdout)


def seeds_of(runs, label, key):
    """key of every seed's summary.json, under runs/<label>, in seed order."""
    return [figart.summary(d)[key] for d in figart.seed_dirs(os.path.join(runs, label))]


def comma(n):
    return f"{n:,}"


def chart(fig, box, groups, ylabel="", ylim=None, value=None):
    """figart.seeds_chart, with the mean printed as the experiment prints it (value) and room on the
    right of the last column for its number: one column per (label, values over seeds, style), a ring
    per seed, the mean a short bar, the whisker min to max. Returns the Axes."""
    value = value or (lambda v: f"{v:.2f}")
    bx, by, bw, bh = box
    vals = [v for _, vs, _ in groups for v in vs]
    auto = figart._limits(vals, False, 0.08)
    ylim = tuple(a if a is not None else b for a, b in zip(ylim or (None, None), auto))
    yt = figart.ticks(*sorted(ylim))
    left = max(tw(figart.tick_label(t), 10.5, mono=True) for t in yt) + 12
    lines = max(len(g[0].split("\n")) for g in groups)
    ax = figart.Axes(fig, bx + left, by + 22, bw - left - 4, bh - 22 - 8 - 14 * lines,
                     (-0.5, len(groups) - 0.5 + 0.35), ylim)
    ax.draw(xticks=[], ylabel=ylabel)
    for i, (label, vs, style) in enumerate(groups):
        X = ax.px(i)
        for k, line in enumerate(label.split("\n")):
            fig.text(X, ax.y + ax.h + 15 + 14 * k, line, figart.TEXT.get(style, "t") if k == 0 else "tm", 11,
                     "middle", 600 if style == "a" and k == 0 else None)
        ax.whisker(i, vs, style, cap=6, mean=False)
        for v in vs:
            fig.circle(X, ax.py(v), 2.5, f"{style} f")
        m = sum(vs) / len(vs)
        fig.line(X - 14, ax.py(m), X + 14, ax.py(m), style)
        fig.text(X + 18, ax.py(m) + 3.5, value(m), figart.TEXT.get(style, "t"), 10.5, mono=True)
    return ax


# ------------------------------------------------------------------ 05.01

def splits0501():
    r = figart.experiment("random_labels")
    cfg = figart.config(figart.seed_dirs(os.path.join(r.runs, "real-labels"))[0])
    n_train, n_val = cfg["n_train"], cfg["n_val"]
    sizes = in_project("05.01", "import json\nfrom data import mnist\n"
                                "print(json.dumps([len(mnist.load('train')[1]), len(mnist.load('test')[1])]))")
    n_all, n_test = sizes
    f = Fig("splits0501", f"MNIST cut three ways: the first {comma(n_train)} training digits to learn from, "
                          f"the last {comma(n_val)} to validate on, the test set for the end", 246)
    x0, w = 20, 600
    px = w / n_all

    def bar(y, a, b, cls, dash=False):
        f.rect(x0 + a * px, y, (b - a) * px, 30, cls, 2, dash)

    # the training set of MNIST
    f.text(x0, 22, f"MNIST's training set: {comma(n_all)} digits, in the order the files give them", "t", 12, weight=600)
    y = 34
    bar(y, n_train, n_all - n_val, "m", dash=True)
    bar(y, 0, n_train, "s fs")
    bar(y, n_all - n_val, n_all, "s fs")
    f.text(x0 + (n_train + (n_all - n_val - n_train) / 2) * px, y + 19, f"{comma(n_all - n_train - n_val)} not used here",
           "tm", 11, "middle")
    # labels under the training and validation parts
    f.line(x0 + n_train * px / 2, y + 30, x0 + n_train * px / 2, y + 44, "s")
    f.text(x0, y + 58, f"training: the first {comma(n_train)}", "t", 12, weight=600)
    f.text(x0, y + 74, "learned from; labels real,", "tm", 11)
    f.text(x0, y + 88, "or replaced by digits drawn at random", "tm", 11)
    xv = x0 + (n_all - n_val / 2) * px
    f.line(xv, y + 30, xv, y + 44, "s")
    f.text(x0 + w, y + 58, f"validation: the last {comma(n_val)}", "t", 12, "end", 600)
    f.text(x0 + w, y + 74, "real labels; scored every 5 epochs;", "tm", 11, "end")
    f.text(x0 + w, y + 88, "anything chosen is chosen here", "tm", 11, "end")
    # the test set
    yt = 166
    f.text(x0, yt - 12, f"MNIST's test set: {comma(n_test)} digits", "t", 12, weight=600)
    f.rect(x0, yt, n_test * px, 30, "a af", 2)
    f.text(x0 + n_test * px + 14, yt + 13, "real labels; scored once, at the end of each run, after every choice is made;",
           "ta", 11)
    f.text(x0 + n_test * px + 14, yt + 28, "its number is reported, never used to choose anything", "ta", 11)
    f.text(x0, yt + 62, "The same width is the same number of digits in both bars.", "tm", 10.5)
    return f


def memorise0501():
    r = figart.experiment("random_labels")
    series = []
    for label, style in (("real-labels", "s"), ("random-labels", "a")):
        dirs = figart.seed_dirs(os.path.join(r.runs, label))
        name = label.replace("-", " ")
        for key, part, dash in (("train_accuracy", "training", False), ("val_accuracy", "validation", True)):
            xs, mean, lo, hi = figart.over_seeds(dirs, key, x="epoch")
            series.append(figart.Series(f"{name}, {part}", xs, mean, style, dash, lo, hi))
    f = Fig("memorise0501", "Accuracy on the 1000 training digits and on the 10,000 validation digits, epoch by "
                            "epoch, with real labels and with labels drawn at random", 300)
    ax = figart.plot(f, (10, 8, 620, 288), series, xlabel="epoch", ylabel="accuracy", xlim=(0, 60),
                     ylim=(0, 1.03), yticks=[0, 0.2, 0.4, 0.6, 0.8, 1])
    ax.hline(0.1, "chance: 0.1", side="right")
    return f


# ------------------------------------------------------------------ 05.02

DROP_CODE = """
import json
import engine as torch
F = torch.nn.functional
torch.manual_seed(0)
x = torch.ones(1, 10)
rows = [F.dropout(x, 0.5), F.dropout(x, 0.5), F.dropout(x, 0.2), F.dropout(x, 0.5, training=False)]
print(json.dumps({"rows": [r.data[0].tolist() for r in rows]}))
"""


def dropout0502():
    d = in_project("05.02", DROP_CODE)
    rows = d["rows"]
    f = Fig("dropout0502", "F.dropout on a row of ten ones: in training each number is dropped with probability p "
                           "and the rest are scaled by 1 / (1 - p); in eval mode it changes nothing", 290)
    cell = (34, 24)
    x0 = 20
    specs = [("x", [1.0] * 10, None, "the input: ten ones"),
             ("dropout(x, 0.5)", rows[0], 0.5, "training"),
             ("dropout(x, 0.5)", rows[1], 0.5, "training, the next call: a new mask"),
             ("dropout(x, 0.2)", rows[2], 0.2, "training, the rate used on the pixels"),
             ("dropout(x, 0.5, training=False)", rows[3], None, "eval mode: the identity")]
    y = 30
    for label, vals, p, note in specs:
        kept = [i for i, v in enumerate(vals) if v != 0]
        dropped = [i for i, v in enumerate(vals) if v == 0]
        lit = kept if p else []
        shown = [sig(v, 3) for v in vals]
        f.text(x0, y - 8, label, "t", 12, weight=600, mono=True)
        f.text(x0 + tw(label, 12, mono=True) + 12, y - 8, note, "tm", 11)
        figart.tensor(f, x0, y, shown, cell=cell, here=lit, ghost=dropped, shape=False)
        tx = x0 + cell[0] * 10 + 18
        mean = sum(vals) / len(vals)
        if p:
            f.text(tx, y + 10, f"kept {len(kept)} of 10, each x {sig(1 / (1 - p), 3)}", "ta", 11)
            f.text(tx, y + 23, f"mean of the row: {sig(mean, 3)}", "tm", 11)
        else:
            f.text(tx, y + 16, f"mean of the row: {sig(mean, 3)}", "tm", 11)
        y += 58
    return f


def errors0502():
    r = figart.experiment("regularise")
    ways = [("neither", "neither", "s"), ("weight-decay", "weight\ndecay", "s"), ("dropout", "dropout", "a"),
            ("both", "both", "s")]
    f = Fig("errors0502", "Validation and test error of the same network trained four ways on 2000 digits, "
                          "three seeds each: a ring per seed, the bar their mean, the whisker min to max", 270)
    for i, (key, title) in enumerate((("val_error", "validation error (%): to choose with"),
                                      ("test_error", "test error (%): scored once"))):
        groups = [(name, seeds_of(r.runs, label, key), style) for label, name, style in ways]
        chart(f, (10 + 315 * i, 8, 305, 256), groups, ylabel=title, value=sig if key == "val_error" else None)
    return f


# ------------------------------------------------------------------ 05.03

SHIFT_CODE = """
import json
import numpy as np
from data import mnist
from data.augment import shift
from experiments.augment import BLANK
x, y = mnist.load("train")
rng = np.random.default_rng(0)
img = x[:1]
outs = [shift(img, 2, rng, BLANK) for _ in range(4)]
ink = lambda a: np.clip(a * mnist.STD + mnist.MEAN, 0, 1).reshape(28, 28)
def offset(a):
    base = ink(img)
    for dr in range(-2, 3):
        for dc in range(-2, 3):
            moved = np.zeros((32, 32))
            moved[2 + dr:30 + dr, 2 + dc:30 + dc] = base
            if np.allclose(moved[2:30, 2:30], ink(a), atol=1e-6):
                return [dr, dc]
    raise SystemExit("no offset found")
print(json.dumps({"label": int(y[0]), "images": [ink(a).round(2).tolist() for a in [img] + outs],
                  "offsets": [offset(a) for a in outs]}))
"""


def digit(f, x, y, img, cell, title, sub, accent=False):
    """A 28 x 28 image, each inked pixel a square of the foreground (accent) at its ink's opacity."""
    for r, row in enumerate(img):
        for c, v in enumerate(row):
            if v >= 0.05:
                f.add(f'<rect class="{"fa" if accent else "t"}" x="{x + c * cell:.1f}" y="{y + r * cell:.1f}" '
                      f'width="{cell:.1f}" height="{cell:.1f}" fill-opacity="{round(v, 1)}"/>')
    f.rect(x, y, 28 * cell, 28 * cell, "m", 0)
    f.text(x + 14 * cell, y + 28 * cell + 16, title, "ta" if accent else "t", 11.5, "middle", 600)
    f.text(x + 14 * cell, y + 28 * cell + 30, sub, "tm", 10.5, "middle")


def moves(dr, dc):
    def one(n, pos, neg):
        return f"{abs(n)} {pos if n > 0 else neg}" if n else ""
    parts = [p for p in (one(dr, "down", "up"), one(dc, "right", "left")) if p]
    return ", ".join(parts) or "not moved"


def shifts0503():
    d = in_project("05.03", SHIFT_CODE)
    imgs, offs = d["images"], d["offsets"]
    f = Fig("shifts0503", f"MNIST's first training digit, a {d['label']}, and the copies shift(x, 2, ...) made of it "
                          f"in four passes: each moved by its own whole number of pixels, at most 2 each way", 190)
    cell = 3.9
    size = 28 * cell
    gap = (600 - 5 * size) / 4
    for i, img in enumerate(imgs):
        x = 20 + i * (size + gap)
        if i == 0:
            digit(f, x, 22, img, cell, "as it is", "the image on file")
        else:
            digit(f, x, 22, img, cell, f"pass {i}", moves(*offs[i - 1]), accent=True)
    f.text(20, 14, "what the network sees of this image:", "tm", 11)
    return f


def errors0503():
    r = figart.experiment("augment")
    ways = [("shift0", "as they\nare", "s"), ("shift1", "up to\n1 pixel", "s"), ("shift2", "up to\n2 pixels", "a")]
    f = Fig("errors0503", "Test error and training error of the same network trained on 2000 digits as they are "
                          "and shifted anew every pass, three seeds each", 270)
    for i, (key, title) in enumerate((("test_error", "test error (%)"), ("train_error", "training error (%)"))):
        groups = [(name, seeds_of(r.runs, label, key), style) for label, name, style in ways]
        chart(f, (10 + 315 * i, 8, 305, 256), groups, ylabel=title, ylim=(-0.1, None) if i else None)
    return f


# ------------------------------------------------------------------ 05.04

def curve0504():
    r = figart.experiment("double_descent")
    dirs = figart.seed_dirs(r.runs)
    cfg = figart.config(dirs[0])
    n = cfg["n_train"]
    f = Fig("curve0504", f"Test error, size of the weights and training error against the number of random "
                         f"features p, {n} training digits, mean of {len(dirs)} seeds (band: min to max)", 520)
    xs, err, lo, hi = figart.over_seeds(dirs, "test_error", x="width")
    pct = lambda vs: [100 * v for v in vs]
    ax = figart.plot(f, (8, 6, 624, 230), [figart.Series("", xs, pct(err), "a", lo=pct(lo), hi=pct(hi))],
                     ylabel="test error (%)", logx=True, ylim=(0, 100), legend=None,
                     xticks=[50, 100, 200, 500, 1000, 2000, 5000, 10000])
    ax.vline(n, f"p = n = {n}: the peak")
    k_first = min(range(len(xs)), key=lambda i: err[i] if xs[i] < n else 9)
    ax.dot(xs[k_first], 100 * err[k_first], "s f")
    ax.note(xs[k_first], 100 * err[k_first], f"{100 * err[k_first]:.1f}% at p = {xs[k_first]}", "t", dy=20,
            anchor="middle")
    ax.dot(xs[-1], 100 * err[-1], "a fa")
    ax.note(xs[-1], 100 * err[-1], f"{100 * err[-1]:.1f}%", "ta", dx=-4, dy=-10, anchor="end")
    k_peak = max(range(len(xs)), key=lambda i: err[i])
    ax.note(xs[k_peak], 100 * err[k_peak], f"{100 * err[k_peak]:.1f}%", "ta", dx=8, dy=4)

    xs2, wts, lo2, hi2 = figart.over_seeds(dirs, "weights", x="width")
    ax2 = figart.plot(f, (8, 246, 624, 150), [figart.Series("", xs2, wts, "s", lo=lo2, hi=hi2)],
                      ylabel="size of the weights (log scale)", logx=True, logy=True, legend=None,
                      xticks=[50, 100, 200, 500, 1000, 2000, 5000, 10000], yticks=[1, 10, 100])
    ax2.vline(n)
    k = max(range(len(xs2)), key=lambda i: wts[i])
    ax2.note(xs2[k], wts[k], f"{wts[k]:.1f}", "t", dx=8, dy=10)
    ax2.note(xs2[0], wts[0], f"{wts[0]:.1f}", "t", dx=4, dy=-8)
    ax2.note(xs2[-1], wts[-1], f"{wts[-1]:.1f}", "t", dx=-4, dy=-8, anchor="end")
    xs3, tr, lo3, hi3 = figart.over_seeds(dirs, "train_mse", x="width")
    ax3 = figart.plot(f, (8, 406, 624, 112), [figart.Series("", xs3, tr, "s", lo=lo3, hi=hi3)],
                      xlabel="random features p (log scale)", ylabel="training error (mse)", logx=True,
                      ylim=(0, None), legend=None, xticks=[50, 100, 200, 500, 1000, 2000, 5000, 10000],
                      yticks=[0, 0.2, 0.4, 0.6])
    ax3.vline(n)
    return f


FIGS = [
    ("05.01-splits", splits0501),
    ("05.01-memorise", memorise0501),
    ("05.02-dropout", dropout0502),
    ("05.02-errors", errors0502),
    ("05.03-shifts", shifts0503),
    ("05.03-errors", errors0503),
    ("05.04-curve", curve0504),
]


def main():
    only = sys.argv[1:]
    for name, fn in FIGS:
        if only and not any(name.startswith(o) for o in only):
            continue
        print(write(MOD, name, fn()))


if __name__ == "__main__":
    main()
