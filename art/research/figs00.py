"""Figures for research module 00, The workbench (lessons 00.01-00.03).

    python3 -B art/research/figs00.py

Every number comes from the reference code. The 00.01 figures import experiments/curve.py of
the project as it stands at 00.01 and call its own make_data, features, loss and fit with the
settings of its CONFIG (seed 0), as its main() does; they stop with an error unless the final
losses agree with what the script itself prints. The 00.02 figure shows the files a run of the
project at 00.02 really wrote; the 00.03 figures read the summaries and logs of runs of the
project at 00.03 (five seeds, fifty seeds, and degrees 1, 3 and 5), the runs the page shows.
"""
import importlib.util
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)                          # art/research/: figlib, figart
sys.path.insert(0, os.path.dirname(HERE))         # art/: steps
import figart  # noqa: E402
import figlib  # noqa: E402
import steps  # noqa: E402
from figlib import Fig, sig, tw, write  # noqa: E402

MOD = "00"


# ---------------------------------------------------------------- the reference code

def curve_at(at):
    """experiments/curve.py of the project at lesson `at`, imported from there."""
    d = figart.project(at)
    if d not in sys.path:
        sys.path.insert(0, d)
    spec = importlib.util.spec_from_file_location(f"curve_{at.replace('.', '_')}",
                                                  os.path.join(d, "experiments", "curve.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def the_fit_0001():
    """The 00.01 experiment, as its main() runs it: (module, X, y, Xt, yt, x, y_points, cfg)."""
    import numpy as np
    c = curve_at("00.01")
    cfg = c.CONFIG
    rng = np.random.default_rng(cfg["seed"])
    x, y = c.make_data(cfg["n_train"], cfg["noise"], rng)
    xt, yt = c.make_data(cfg["n_test"], cfg["noise"], rng)
    X, Xt = c.features(x, cfg["degree"]), c.features(xt, cfg["degree"])
    w = c.fit(X, y, cfg["lr"], cfg["steps"])
    printed = figart.experiment("curve", at="00.01").out
    mine = f"train loss {c.loss(w, X, y):.4f}  test loss {c.loss(w, Xt, yt):.4f}"
    if mine not in printed:
        raise SystemExit(f"00.01: the figure's fit ({mine}) is not the script's:\n{printed}")
    return c, X, y, Xt, yt, x, xt, cfg


def poly(w, xs):
    return [sum(wk * v ** k for k, wk in enumerate(w)) for v in xs]


def num4(v):
    return f"{v:.4f}"


# ---------------------------------------------------------------- 00.01

FRAMES = [0, 1, 2, 5, 10, 20, 50, 100, 300, 2000]


def fit0001():
    """Stepped: the cubic over the 20 training points at steps 0 to 2000, and its training loss."""
    import numpy as np
    c, X, y, Xt, yt, x, xt, cfg = the_fit_0001()
    lr = cfg["lr"]
    true_train = float(np.mean((np.sin(np.pi * x) - y) ** 2))
    grid = [-1 + 2 * i / 120 for i in range(121)]
    curve_steps = sorted({int(round(10 ** (k / 20))) for k in range(0, 67)} | set(FRAMES[1:]))
    curve_steps = [s for s in curve_steps if 1 <= s <= cfg["steps"]]
    curve_loss = [c.loss(c.fit(X, y, lr, s), X, y) for s in curve_steps]

    f = Fig("fit0001", "The cubic over the 20 training points as gradient descent runs, and its training loss", 330)
    ax = figart.plot(f, (8, 30, 330, 290), [figart.Series("", grid, [math.sin(math.pi * v) for v in grid], "m",
                                                           dash=True)],
                     xlabel="x", ylabel="y", xlim=(-1, 1), ylim=(-1.75, 1.75), legend=None,
                     xticks=[-1, -0.5, 0, 0.5, 1], yticks=[-1.5, -1, -0.5, 0, 0.5, 1, 1.5])
    for a, b in zip(x, y):
        ax.dot(a, b, "s f", 3)
    after = figart.legend(f, ax.x, 16, [("the cubic", "a"), ("sin(pi x), which made the points", "m", True)],
                          across=True)
    f.circle(after + 4, 12, 3, "s f")
    f.text(after + 12, 16, "a training point (20 of them)", "t", 11)

    bx = ax.x + ax.w + 56
    lax = figart.plot(f, (bx - 50, 30, 640 - bx + 46, 290),
                      [figart.Series("", curve_steps, curve_loss, "s")],
                      xlabel="steps taken", ylabel="training loss", logx=True, logy=True,
                      xlim=(1, cfg["steps"]), ylim=(0.008, 0.5), legend=None,
                      xticks=[1, 10, 100, 1000], yticks=[0.01, 0.02, 0.05, 0.1, 0.2, 0.5],
                      yfmt=lambda v: f"{v:g}")
    lax.hline(true_train, f"sin(pi x): {num4(true_train)}", "m", side="right")

    for k in FRAMES:
        w = c.fit(X, y, lr, k)
        tr, te = c.loss(w, X, y), c.loss(w, Xt, yt)
        ws = ", ".join(f"{v:.3f}" for v in w)
        if k == 0:
            cap = (f"Step 0: every weight is 0, so the cubic is the flat line y = 0. Training loss {num4(tr)}, "
                   f"test loss {num4(te)}.")
        elif k == 1:
            cap = (f"One step against the gradient: the weights are ({ws}), and the training loss has halved, "
                   f"to {num4(tr)}.")
        elif k == cfg["steps"]:
            cap = (f"Step {k}: weights ({ws}). Training loss {num4(tr)}, lower than sin(pi x) itself scores on "
                   f"these points ({num4(true_train)}); test loss {num4(te)}.")
        else:
            cap = f"Step {k}: training loss {num4(tr)}, test loss {num4(te)}."
        with steps.step(f, cap):
            ax.curve(grid, poly(w, grid), "a", width=2.25)
            f.text(ax.x + 8, ax.y + 16, f"step {k}", "ta", 12, weight=700, mono=True)
            f.text(ax.x + 8, ax.y + 31, f"train {num4(tr)}", "t", 11, mono=True)
            f.text(ax.x + 8, ax.y + 45, f"test  {num4(te)}", "tm", 11, mono=True)
            if k >= 1:
                lax.dot(k, tr, "a fa", 4)
            else:
                f.text(lax.x + 6, lax.y + 14, f"at the start: {num4(tr)}", "ta", 10.5)
    return f


def scores0001():
    """The mean squared error of the cubic and of sin(pi x) on the training and the test points."""
    import numpy as np
    c, X, y, Xt, yt, x, xt, cfg = the_fit_0001()
    w = c.fit(X, y, cfg["lr"], cfg["steps"])
    zero = c.loss(np.zeros(X.shape[1]), X, y)
    rows = [("the 20 training points", c.loss(w, X, y), float(np.mean((np.sin(np.pi * x) - y) ** 2))),
            ("the 500 test points", c.loss(w, Xt, yt), float(np.mean((np.sin(np.pi * xt) - yt) ** 2)))]
    f = Fig("scores0001", "Mean squared error of the fitted cubic and of sin(pi x) on the training and test points",
            218)
    ax = figart.Axes(f, 150, 20, 460, 130, (0.008, 0.5), (0, 2), logx=True)
    ax.draw(xlabel="mean squared error (log scale)", xticks=[0.01, 0.02, 0.05, 0.1, 0.2, 0.5], yticks=[],
            grid=False, frame=False, xfmt=lambda v: f"{v:g}")
    f.line(ax.x, ax.y + ax.h, ax.x + ax.w, ax.y + ax.h, "m")
    for i, (name, cubic, true) in enumerate(rows):
        yy = ax.y + 30 + i * 60
        f.text(ax.x - 12, yy + 4, name, "t", 11.5, "end")
        f.line(ax.x, yy, ax.x + ax.w, yy, "m", dash=True)
        tx, cx = ax.px(true), ax.px(cubic)
        f.circle(tx, yy, 5, "s f")
        f.circle(cx, yy, 5, "a fa")
        left, right = (cx, tx) if cx < tx else (tx, cx)
        lab_c, lab_t = f"cubic {num4(cubic)}", f"sin(pi x) {num4(true)}"
        if cx < tx:
            f.text(cx - 9, yy - 9, lab_c, "ta", 11, "end", 600, mono=True)
            f.text(tx + 9, yy - 9, lab_t, "t", 11, mono=True)
        else:
            f.text(tx - 9, yy - 9, lab_t, "t", 11, "end", mono=True)
            f.text(cx + 9, yy - 9, lab_c, "ta", 11, weight=600, mono=True)
    yy = ax.y + 30
    zx = ax.px(zero)
    f.circle(zx, yy, 5, "m f")
    f.text(zx + 8, yy + 19, f"all weights 0: {num4(zero)}", "tm", 10.5, "end", mono=True)
    f.text(ax.x - 12, ax.y + 30 + 18, "the fit sees these", "tm", 10.5, "end")
    f.text(ax.x - 12, ax.y + 90 + 18, "it never sees these", "tm", 10.5, "end")
    f.text(16, 210, "Seed 0, after 2000 steps. The noise added to each y has sd 0.2: about 0.04 of error no rule "
                    "can avoid on new points.", "tm", 10.5)
    return f


# ---------------------------------------------------------------- 00.02

def reader_run(at, *settings):
    """python3 -m experiments.curve settings... run as the reader runs it, in a copy of the project
    at `at` with no out= (so config.json says "out": "runs", as the page's run does): the folder
    the run wrote, runs/curve/seed<k>."""
    import shutil
    import subprocess
    import tempfile
    d = tempfile.mkdtemp(prefix="figs00-", dir=figart._tmp)
    for pkg in ("experiments", "lab"):
        shutil.copytree(os.path.join(figart.project(at), pkg), os.path.join(d, pkg))
    r = subprocess.run([sys.executable, "-B", "-m", "experiments.curve"] + list(settings), cwd=d,
                       capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    if r.returncode != 0:
        raise SystemExit(f"curve {' '.join(settings)} at {at} failed:\n{r.stdout}{r.stderr}")
    return d, r.stdout


def run0002():
    """What one run is: the settings, the seed, and the three files a real run at 00.02 wrote."""
    top, out = reader_run("00.02", "lr=0.1", "steps=300")
    rel = out.strip().split("\n")[-1].split("run in ")[1]
    files = []
    for name in ("config.json", "log.jsonl", "summary.json"):
        with open(os.path.join(top, rel, name)) as fh:
            files.append((name, fh.read().rstrip("\n").split("\n")))
    c = curve_at("00.02")
    items = [f"{k}={v!r}" for k, v in c.CONFIG.items()]

    f = Fig("run0002", "One run: the settings from CONFIG and the command line, one seed, and the three files the run "
                       "writes", 456)
    L, W = 16, 262
    f.text(L, 16, "the command", "tm", 10.5)
    f.label_box(L, 22, W, 26, "curve lr=0.1 steps=300", "a af", "ta", 11.5)
    f.text(L, 68, "CONFIG, at the top of curve.py", "tm", 10.5)
    f.rect(L, 74, W - 28, 58, "s fs")
    for i, line in enumerate([items[:2], items[2:5], items[5:]]):
        f.text(L + 8, 92 + 15 * i, ", ".join(line) + ("," if i < 2 else ""), "t", 10.5, mono=True)
    f.line(L + (W - 28) / 2, 134, L + (W - 28) / 2, 152, "s", arrow=True)
    f.line(L + W - 12, 48, L + W - 12, 152, "a", arrow=True)
    f.label_box(L, 156, W, 40, "config()", "s f", "t", 12, sub="CONFIG, with lr and steps changed")
    f.line(L + W / 2, 196, L + W / 2, 214, "s", arrow=True)
    f.label_box(L, 218, W, 40, "Run(settings, seed 0)", "s f", "t", 12, sub="a folder, and rng = default_rng(0)")
    f.line(L + W / 2, 258, L + W / 2, 276, "s", arrow=True)
    f.rect(L, 280, W, 92, "s f")
    f.text(L + 10, 298, "rng draws, in this order:", "tm", 10.5)
    f.text(L + 10, 316, "20 training points", "t", 11.5, mono=True)
    f.text(L + 10, 332, "500 test points", "t", 11.5, mono=True)
    f.text(L + 10, 352, "fit: a log line every 100 steps", "tm", 10.5)
    f.text(L + 10, 366, "finish: the final losses", "tm", 10.5)
    f.text(L, 396, "Same settings and seed: the same draws,", "tm", 10.5)
    f.text(L, 410, "the same arithmetic, the same bytes", "tm", 10.5)
    f.text(L, 424, "in all three files.", "tm", 10.5)

    X = 306
    f.text(X, 16, rel.replace(os.sep, "/") + "/", "t", 12, weight=700, mono=True)
    y, mids = 26, []
    for name, lines in files:
        h = 22 + 14 * len(lines) + 6
        f.rect(X, y, 640 - X - 8, h, "s fs")
        f.text(X + 8, y + 16, name, "ta", 11.5, weight=700, mono=True)
        for i, line in enumerate(lines):
            if tw(line, 10, mono=True) > 640 - X - 24:
                raise SystemExit(f"00.02-run: {line!r} does not fit")
            f.text(X + 8, y + 32 + 14 * i, line, "t", 10, mono=True)
        mids.append(y + 16)
        y += h + 8
    f.line(L + W + 2, 238, X - 4, mids[0] - 4, "m", arrow=True)
    f.line(L + W + 2, 348, X - 4, mids[1] - 4, "m", arrow=True)
    f.line(L + W + 2, 362, X - 4, mids[2] - 4, "m", arrow=True)
    return f


# ---------------------------------------------------------------- 00.03

def five_seeds():
    r = figart.experiment("curve", at="00.03")
    dirs = figart.seed_dirs(r.runs)
    return r, dirs, [figart.summary(d)["test_loss"] for d in dirs]


def seeds0003():
    """Five seeds of the same fit: their training curves, and their test losses with mean and sd."""
    r, dirs, tests = five_seeds()
    stats = stats_at("00.03")
    printed = figart.value(r.out, r"^test loss (\S+) \+-")
    if f"{stats.mean(tests):.3g}" != f"{printed:.3g}":
        raise SystemExit(f"00.03: the summaries' mean {stats.mean(tests)} is not the printed {printed}")
    f = Fig("seeds0003", "The same fit with five seeds: five training curves, and five test losses", 300)
    series = []
    for i, d in enumerate(dirs):
        xs, ys = figart.column(figart.read_log(d), "train_loss")
        series.append(figart.Series(f"seed {i}", xs, ys, "s" if i else "a", width=1.5))
    figart.plot(f, (8, 10, 400, 280), series, xlabel="step", ylabel="training loss", logy=True,
                ylim=(0.008, 0.5), legend="end", yticks=[0.01, 0.02, 0.05, 0.1, 0.2, 0.5],
                yfmt=lambda v: f"{v:g}")
    ax = figart.Axes(f, 500, 32, 120, 218, (0, 1), (0.04, 0.07))
    ax.draw(xticks=[], yticks=[0.04, 0.05, 0.06, 0.07], frame=False, yfmt=lambda v: f"{v:g}")
    f.text(ax.x - 6, ax.y - 14, "test loss", "tm", 11.5)
    f.line(ax.x, ax.y, ax.x, ax.y + ax.h, "m")
    m, s = stats.mean(tests), stats.sd(tests)
    X = ax.px(0.3)
    f.rect(X - 10, ax.py(m + s), 20, ax.py(m - s) - ax.py(m + s), "a af", 2)
    f.line(X - 16, ax.py(m), X + 16, ax.py(m), "a")
    order = sorted(enumerate(tests), key=lambda t: -t[1])
    ys = []
    for i, v in order:                                # top to bottom, at least 13 px apart
        ys.append(max(ax.py(v) + 4, ys[-1] + 13) if ys else ax.py(v) + 4)
    for (i, v), ty in zip(order, ys):
        ax.dot(0.3, v, "a fa" if i == 0 else "s f", 3.5)
        f.text(X + 22, ty, f"seed {i}  {sig(v)}", "ta" if i == 0 else "t", 10.5, mono=True)
    f.text(ax.x + ax.w / 2 + 8, ax.y + ax.h + 22, f"mean {sig(m)}", "ta", 11, "middle", 600, mono=True)
    f.text(ax.x + ax.w / 2 + 8, ax.y + ax.h + 38, f"band: +- sd {sig(s)}", "tm", 10.5, "middle", mono=True)
    return f


def stats_at(at):
    d = figart.project(at)
    spec = importlib.util.spec_from_file_location(f"stats_{at.replace('.', '_')}", os.path.join(d, "lab", "stats.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def stack(ax, values, y0, r, cls, here=()):
    """values as dots on the row at pixel y0, piled upwards where they would touch."""
    placed = []
    for i, v in sorted(enumerate(values), key=lambda t: t[1]):
        X = ax.px(v)
        level = 0
        while any(abs(X - px) < 2 * r + 0.5 and lv == level for px, lv in placed):
            level += 1
        placed.append((X, level))
        ax.fig.circle(X, y0 - level * (2 * r + 1), r, "a fa" if i in here else cls)
    return max(lv for _, lv in placed)


def means0003():
    """Fifty seeds one by one, and the same fifty as ten means of five: the means spread less."""
    stats = stats_at("00.03")
    r = figart.experiment("curve", "seeds=50", at="00.03")
    tests = [figart.summary(d)["test_loss"] for d in figart.seed_dirs(r.runs)]
    if len(tests) != 50:
        raise SystemExit(f"00.03: {len(tests)} seeds, not 50")
    means = [stats.mean(tests[i:i + 5]) for i in range(0, 50, 5)]
    s1, s5 = stats.sd(tests), stats.sd(means)
    f = Fig("means0003", "The test loss of fifty seeds one by one, and as ten means of five seeds each", 282)
    ax = figart.Axes(f, 40, 20, 580, 218, (0.035, 0.13), (0, 1))
    ax.draw(xlabel="test loss", xticks=[0.04, 0.06, 0.08, 0.1, 0.12], yticks=[], grid=False, frame=False,
            xfmt=lambda v: f"{v:g}")
    f.line(ax.x, ax.y + ax.h, ax.x + ax.w, ax.y + ax.h, "m")
    r1, y1, y2 = 3.2, ax.y + 96, ax.y + 178

    def bracket(m, s, y, cls, text):
        a, b = ax.px(m - s), ax.px(m + s)
        f.path(f"M{a:.1f} {y - 5:.1f} L{a:.1f} {y:.1f} L{b:.1f} {y:.1f} L{b:.1f} {y - 5:.1f}", cls)
        f.line(ax.px(m), y - 3, ax.px(m), y + 3, cls)
        f.text(b + 8, y + 4, text, "ta" if cls == "a" else "t", 10.5, mono=True)

    stack(ax, tests, y1, r1, "s f")
    worst = max(range(50), key=tests.__getitem__)
    f.text(ax.px(tests[worst]), y1 - 12, f"seed {worst}: {sig(tests[worst])}", "t", 10.5, "middle", mono=True)
    bracket(stats.mean(tests), s1, y1 + 14, "s", f"mean +- sd: {sig(stats.mean(tests))} +- {sig(s1)}")
    f.text(ax.x, ax.y + 6, "50 seeds, one run each", "t", 11.5, weight=600)
    stack(ax, means, y2, r1, "a fa")
    bracket(stats.mean(means), s5, y2 + 14, "a", f"sd of the means {sig(s5)};  {sig(s1)} / sqrt(5) = "
                                                  f"{sig(s1 / math.sqrt(5))}")
    f.text(ax.x, y2 - 36, "the same runs as 10 means of 5 seeds", "ta", 11.5, weight=600)
    return f


def compare0003():
    """Degree 1, 3 and 5 over five seeds each, with Welch's t against degree 3."""
    stats = stats_at("00.03")
    groups, vals = [], {}
    for deg in (1, 3, 5):
        r = figart.experiment("curve", f"degree={deg}", at="00.03")
        vals[deg] = [figart.summary(d)["test_loss"] for d in figart.seed_dirs(r.runs)]
    for deg in (1, 3, 5):
        t = "" if deg == 3 else f"\nt = {stats.welch_t(vals[deg], vals[3]):.1f}"
        groups.append((f"degree {deg}" + (t or "\n(the page's fit)"), vals[deg], "a" if deg == 3 else "s"))
    f = Fig("compare0003", "Test loss of five seeds at degree 1, 3 and 5, and Welch's t of each against degree 3", 290)
    figart.seeds_chart(f, (16, 6, 608, 280), groups, ylabel="test loss, 5 seeds each (log scale)", logy=True,
                       ylim=(0.04, 0.4), yticks=[0.05, 0.1, 0.2, 0.4], yfmt=lambda v: f"{v:g}")
    return f


def main():
    out = [write(MOD, "00.01-fit", fit0001()),
           write(MOD, "00.01-scores", scores0001()),
           write(MOD, "00.02-run", run0002()),
           write(MOD, "00.03-seeds", seeds0003()),
           write(MOD, "00.03-means", means0003()),
           write(MOD, "00.03-compare", compare0003())]
    for p in out:
        print(os.path.relpath(p, figlib.ROOT))
    steps.check(open(out[0]).read())


if __name__ == "__main__":
    main()
