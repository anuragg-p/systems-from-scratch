"""What the research track's lesson figures draw again and again, on a figlib.Fig.

Every number in a figure comes from a real run of the reference code (tracks/research), never
from a number typed into the generator: a curve is read from a run's log.jsonl, a bar from what
the experiment printed or returned. experiment() runs one; the rest draw.

A figure generator, art/research/figsNN.py (one per module, see figlib's docstring for the
imports and write()), goes like this:

    import figart
    from figlib import Fig, write

    def seeds0003():
        r = figart.experiment("curve")                        # python3 -m experiments.curve out=<tmp>
        f = Fig("seeds0003", "Train loss of the same fit with five seeds", 300)
        series = [figart.Series(f"seed {i}", *figart.column(figart.read_log(d), "train_loss"),
                                style="a" if i == 0 else "m")
                  for i, d in enumerate(figart.seed_dirs(r.runs))]
        ax = figart.plot(f, (14, 10, 612, 280), series, xlabel="step", ylabel="train loss", logy=True)
        ax.hline(0.04, "the noise: 0.04")                    # anything else, in the data's units
        return f

    write("00", "00.03-seeds", seeds0003())

Running the reference code

    experiment(name, *settings, at=None)    python3 -B -m experiments.<name> settings... out=<scratch>,
                                            run in tracks/research (at=None: the finished code) or in
                                            the project as it stands at lesson `at` ("00.01": curve.py
                                            before the lab). A Result: .out (what it printed), .runs
                                            (<scratch>/<name>, or None if it wrote no runs). Same
                                            arguments, same Result: each runs once per process. Stops
                                            the generator, with the reason, if the run fails (MNIST
                                            not fetched: python3 -m data.fetch mnist, in tracks/research)
    project(at)                             the project as it stands at lesson `at`, in a scratch folder
    RESEARCH_FIGS_CACHE=DIR                 keep runs in DIR between processes while you work on the
                                            drawing (a change to any .py of the project starts afresh)

Reading what a run left (lab/run.py writes it)

    seed_dirs(d)                            the seed<k> folders under d, in seed order
    read_log(run_dir)                       log.jsonl as a list of dicts: [{"step": 0, "loss": 2.3}, ...]
    summary(run_dir), config(run_dir)       summary.json, config.json
    column(rows, key, x="step")             (xs, ys) of the rows that have key
    over_seeds(run_dirs, key, x="step")     (xs, mean, lo, hi) at the x every seed logged; lo and hi
                                            the min and max over the seeds (spread="sd": mean -+ sd)
    value(text, regex)                      the float a regex's first group finds in printed output

Drawing

    plot(fig, box, series, ...)             a line plot in box = (x, y, w, h): axes, round ticks (the
                                            lab's own ticks()), light grid, the curves, a legend
                                            (legend="right", "top", "end" or None); returns its Axes
    Series(label, xs, ys, style, dash, lo, hi)
                                            one curve; style "a" accent, "s" foreground, "m" muted;
                                            lo/hi: a band round it (the spread over seeds)
    Axes                                    px(x), py(y) map data to figure pixels; curve, band,
                                            whisker, dot, hline, vline, note, legend draw in data units
    ticks(lo, hi, log=), tick_label(v)      the lab's own axis numbers (tracks/research/lab/plot.py);
    spaced(ts, pos, gap, log)               thinned so that labels do not touch
    seeds_chart(fig, box, groups, ...)      one column per setting: a dot per seed, the mean as a bar,
                                            the min-max whisker; for "which setting won, over seeds"
    graph(fig, nodes, edges, ...)           a computation graph: value boxes (name, value, gradient)
                                            and operation circles, joined by arrows
    tensor(fig, x, y, values, ...)          a small tensor as a grid of cells with its shape under it;
                                            cells can be lit (here) or dashed (ghost: broadcast copies);
                                            shape_text((2, 3)) is "(2, 3)"
    shape_box(fig, x, y, w, h, rows, cols)  a big tensor as one rectangle, its sizes along two sides
    network(fig, box, sizes, ...)           a layered network: a column of units per layer, every
                                            unit joined to the next layer's; returns the columns' x
    layer_bars(fig, box, series, ...)       a bar per layer (or a group of bars), on a log axis by
                                            default: activation and gradient sizes; xs= lines them up
                                            under network()'s columns
    legend(fig, x, y, items)                a legend anywhere: [(label, style, dash), ...]

Styles. The accent is the thing the figure is about (this lesson's setting, the curve that
fails); foreground what it is compared with; muted the rest (other seeds, a reference line).
Dashed tells two curves of the same colour apart. More than four curves in one plot is
usually a table instead. Text is ASCII (figlib's docstring).

Notes from the runs (tracks/research/NOTES.md has every lesson's numbers):
- Run a figure's experiment with the settings the lesson's page runs or quotes, so the
  figure and the page's numbers agree; say in the caption what was run ("3 seeds, the band
  is min to max").
- What a log holds differs by experiment: read one run's log.jsonl before drawing from it.
  Some numbers are only printed, not logged (deep_stats' per-layer table): take them from
  Result.out with value() or a regex, never by copying them into the generator.
- From 03.01 on the experiments read MNIST from the cache, and most default runs take 10
  to 30 seconds: set RESEARCH_FIGS_CACHE while drawing, never commit what it holds.
- A process (a backward pass node by node, an optimiser's steps) can be a stepped figure:
  art/steps.py's step(fig, caption) around what one frame draws, at most one per lesson.
"""
import atexit
import hashlib
import importlib.util
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile

import figlib
from figlib import Fig, fmt, sig, tw  # noqa: F401  (Fig, sig: for the generators that import them from here)

ROOT = figlib.ROOT
TRACK = figlib.TRACK
MAX_POINTS = 400                # a curve is thinned to this many points (the lab's plots do the same)


def _load_lab_plot():
    """tracks/research/lab/plot.py, the lab's own plotting code: its ticks() and tick labels, so
    a figure's axes number themselves exactly as the learner's plots do."""
    spec = importlib.util.spec_from_file_location("research_lab_plot", os.path.join(TRACK, "lab", "plot.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_lab_plot = _load_lab_plot()
ticks = _lab_plot.ticks           # ticks(lo, hi, n=5, log=False): round numbers for an axis
tick_label = _lab_plot._label     # a tick's text, as few digits as it needs


# ---------------------------------------------------------------- running the reference code

_tmp = tempfile.mkdtemp(prefix="research-figs-")
atexit.register(shutil.rmtree, _tmp, True)
_projects, _results = {}, {}


class Result:
    def __init__(self, argv, out, runs):
        self.argv, self.out, self.runs = argv, out, runs

    def __repr__(self):
        return f"Result({' '.join(self.argv)!r}, runs={self.runs!r})"


def project(at):
    """The project as it stands at lesson `at` ("03.02"), written once per process by
    ./learn files research --at; its directory. at=None is tracks/research itself."""
    if at is None:
        return TRACK
    if at not in _projects:
        d = os.path.join(_tmp, "at-" + at)
        r = subprocess.run([os.path.join(ROOT, "learn"), "files", "research", "--at", at, d],
                           capture_output=True, text=True, cwd=ROOT)
        if r.returncode != 0:
            raise SystemExit(f"./learn files research --at {at}: {r.stdout}{r.stderr}")
        _projects[at] = d
    return _projects[at]


def _sources_hash():
    h = hashlib.sha256()
    for pkg in ("engine", "lab", "data", "experiments"):
        for dirpath, dirs, files in sorted(os.walk(os.path.join(TRACK, pkg))):
            dirs.sort()
            for name in sorted(files):
                if name.endswith(".py"):
                    with open(os.path.join(dirpath, name), "rb") as f:
                        h.update(name.encode() + f.read())
    return h.hexdigest()[:16]


def experiment(name, *settings, at=None):
    """Run experiments/<name>.py of the reference code with settings ("seeds=3", "lrs=[0.1]")
    and out=<scratch>: a Result with .out (stdout) and .runs (the folder its runs went to, or None
    when it wrote none, as curve.py at 00.01). Raises SystemExit with its output if it fails."""
    key = (at, name, tuple(str(s) for s in settings))
    if key in _results:
        return _results[key]
    cache = os.environ.get("RESEARCH_FIGS_CACHE")
    if cache:
        tag = hashlib.sha256(repr((key, _sources_hash())).encode()).hexdigest()[:16]
        base = os.path.join(os.path.abspath(cache), f"{name}-{tag}")
    else:
        base = os.path.join(_tmp, f"{name}-{len(_results)}")
    argv = [sys.executable, "-B", "-m", f"experiments.{name}"] + [str(s) for s in settings] + [f"out={base}"]
    done = os.path.join(base, "stdout.txt")
    if cache and os.path.isfile(done):
        with open(done) as f:
            out = f.read()
    else:
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=project(at))
        r = subprocess.run(argv, cwd=project(at), env=env, capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f"experiments.{name} {' '.join(map(str, settings))} (at {at or 'the end'}) "
                             f"failed, exit {r.returncode}:\n{r.stdout[-1500:]}{r.stderr[-1500:]}")
        out = r.stdout
        os.makedirs(base, exist_ok=True)
        with open(done, "w") as f:
            f.write(out)
    runs = os.path.join(base, name)
    _results[key] = Result(argv, out, runs if os.path.isdir(runs) else None)
    return _results[key]


def value(text, regex):
    """The float that regex's first group matches in text (a run's printed output)."""
    m = re.search(regex, text, re.M)
    if not m:
        raise SystemExit(f"no {regex!r} in:\n{text[-1500:]}")
    return float(m.group(1))


# ---------------------------------------------------------------- reading runs

def seed_dirs(d):
    """The seed<k> folders under d (a Result's .runs, or .runs/<label>), in seed order."""
    found = [(int(m.group(1)), n) for n in os.listdir(d) for m in [re.match(r"seed(\d+)$", n)] if m]
    return [os.path.join(d, n) for _, n in sorted(found)]


def read_log(run_dir):
    """The rows of run_dir/log.jsonl: one dict per logged step."""
    with open(os.path.join(run_dir, "log.jsonl")) as f:
        return [json.loads(line) for line in f if line.strip()]


def summary(run_dir):
    with open(os.path.join(run_dir, "summary.json")) as f:
        return json.load(f)


def config(run_dir):
    with open(os.path.join(run_dir, "config.json")) as f:
        return json.load(f)


def column(rows, key, x="step"):
    """(xs, ys): x and key of every row that has key (a log may log some values less often)."""
    pts = [(r[x], r[key]) for r in rows if key in r and x in r]
    return [p[0] for p in pts], [p[1] for p in pts]


def over_seeds(run_dirs, key, x="step", spread="minmax"):
    """(xs, mean, lo, hi) of key over several seeds' logs, at each x that every seed logged.
    lo and hi are the min and max over the seeds, or with spread="sd" the mean -+ the sample sd.
    A value that is not finite in any seed makes that x's mean nan (the curve breaks there)."""
    cols = [dict(zip(*column(read_log(d), key, x))) for d in run_dirs]
    xs = sorted(set.intersection(*(set(c) for c in cols)))
    mean, lo, hi = [], [], []
    for v in xs:
        vals = [c[v] for c in cols]
        if not all(isinstance(t, (int, float)) and math.isfinite(t) for t in vals):
            mean.append(float("nan")); lo.append(float("nan")); hi.append(float("nan"))
            continue
        m = sum(vals) / len(vals)
        mean.append(m)
        if spread == "sd" and len(vals) > 1:
            s = math.sqrt(sum((t - m) ** 2 for t in vals) / (len(vals) - 1))
            lo.append(m - s); hi.append(m + s)
        else:
            lo.append(min(vals)); hi.append(max(vals))
    return xs, mean, lo, hi


# ---------------------------------------------------------------- line plots

FILL = {"a": "af", "s": "fs", "m": "fs"}       # a band's fill for a curve's style
TEXT = {"a": "ta", "s": "t", "m": "tm"}        # a label's text class for a curve's style


def _ok(v, log):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and (v > 0 or not log)


def _keep(n, *arrays):
    """Which of n points to draw: every one up to MAX_POINTS; past that, in each of about
    MAX_POINTS / 2 buckets the smallest and largest value of each array and the first and last
    value that is not a finite number, so a spike (a rate that blows up for three steps) and a
    break (a run that diverged) survive the thinning."""
    if n <= MAX_POINTS:
        return list(range(n))
    k = math.ceil(n / (MAX_POINTS // (2 * len(arrays))))
    keep = {0, n - 1}
    for s in range(0, n, k):
        idx = range(s, min(n, s + k))
        for a in arrays:
            fin = [i for i in idx if _ok(a[i], False)]
            bad = [i for i in idx if not _ok(a[i], False)]
            if fin:
                keep.update((min(fin, key=a.__getitem__), max(fin, key=a.__getitem__)))
            if bad:
                keep.update((bad[0], bad[-1]))
    return sorted(keep)


def spaced(ts, pos, gap, log=False):
    """The ticks ts, thinned so that no two are closer than gap pixels (pos: a tick's pixel); on a
    log axis, every k-th power of ten, so ten decades in a short axis still read."""
    if len(ts) < 2 or min(abs(pos(b) - pos(a)) for a, b in zip(ts, ts[1:])) >= gap:
        return ts
    if log:
        tens = [t for t in ts if abs(math.log10(t) - round(math.log10(t))) < 1e-9]
        if len(tens) >= 2:
            k = math.ceil(gap / abs(pos(tens[1]) - pos(tens[0])))
            kept = [t for t in tens if round(math.log10(t)) % k == 0]
            return kept if len(kept) >= 2 else tens[::k]
    out = [ts[0]]
    for t in ts[1:]:
        if abs(pos(t) - pos(out[-1])) >= gap:
            out.append(t)
    return out


class Series:
    """One curve of a plot: label (for the legend; "" for none), its xs and ys, a style ("a"
    accent, "s" foreground, "m" muted), dash (True, or a dasharray like "2 3"), and lo/hi, a
    band round it (the spread over seeds), drawn under every curve."""

    def __init__(self, label, xs, ys, style="a", dash=False, lo=None, hi=None, width=1.75):
        self.label, self.xs, self.ys = label, list(xs), list(ys)
        self.style, self.dash, self.lo, self.hi, self.width = style, dash, lo, hi, width


class Axes:
    """A plot's frame at (x, y, w, h) in figure pixels, mapping data (xlim, ylim, log or not) onto
    it. Everything it draws takes data units; px() and py() give the pixels for anything else."""

    def __init__(self, fig, x, y, w, h, xlim, ylim, logx=False, logy=False):
        self.fig, self.x, self.y, self.w, self.h = fig, x, y, w, h
        self.xlim, self.ylim, self.logx, self.logy = xlim, ylim, logx, logy

    def _f(self, v, log):
        return math.log10(v) if log else v

    def px(self, v):
        a, b = (self._f(t, self.logx) for t in self.xlim)
        return self.x + (self._f(v, self.logx) - a) / (b - a) * self.w

    def py(self, v):
        a, b = (self._f(t, self.logy) for t in self.ylim)
        return self.y + self.h - (self._f(v, self.logy) - a) / (b - a) * self.h

    def inside(self, x, y):
        return (_ok(x, self.logx) and _ok(y, self.logy) and
                min(self.xlim) <= x <= max(self.xlim) and min(self.ylim) <= y <= max(self.ylim))

    def draw(self, xlabel="", ylabel="", xticks=None, yticks=None, grid=True, frame=True, xfmt=None, yfmt=None):
        """The frame, the ticks with their labels and a light grid, xlabel under the axis and ylabel
        over the top-left corner (read horizontally). xticks/yticks: the tick values (default the
        lab's ticks()); xfmt/yfmt: a tick's text (default tick_label)."""
        f = self.fig
        xt = xticks
        if xt is None:
            xt = ticks(*sorted(self.xlim), log=self.logx)
            gap = max([tw((xfmt or tick_label)(t), 10.5, mono=True) for t in xt] or [0]) + 10
            xt = spaced(xt, self.px, gap, self.logx)
        yt = yticks if yticks is not None else spaced(ticks(*sorted(self.ylim), log=self.logy), self.py, 14, self.logy)
        for t in yt:
            y = self.py(t)
            if grid and abs(y - self.y) > 1 and abs(y - self.y - self.h) > 1:
                f.add(f'<line class="m" x1="{fmt(self.x)}" y1="{y:.1f}" x2="{fmt(self.x + self.w)}" y2="{y:.1f}" '
                      f'stroke-width="0.75" stroke-opacity="0.6"/>')
            f.text(self.x - 6, y + 3.5, (yfmt or tick_label)(t), "tm", 10.5, "end", mono=True)
        for t in xt:
            x = self.px(t)
            f.line(x, self.y + self.h, x, self.y + self.h + 4, "m")
            f.text(x, self.y + self.h + 16, (xfmt or tick_label)(t), "tm", 10.5, "middle", mono=True)
        if frame:
            f.rect(self.x, self.y, self.w, self.h, "m", 0)
        if xlabel:
            f.text(self.x + self.w / 2, self.y + self.h + 32, xlabel, "tm", 11.5, "middle")
        if ylabel:
            f.text(self.x - 6, self.y - 8, ylabel, "tm", 11.5)
        return self

    def curve(self, xs, ys, cls="a", dash=False, width=1.75):
        """A line through the points inside the axes, broken wherever a value is left out (not a
        finite number, not positive on a log axis, outside the limits): a diverged run stops."""
        keep = _keep(len(xs), ys)
        xs, ys = [xs[i] for i in keep], [ys[i] for i in keep]
        run = []
        for x, y in list(zip(xs, ys)) + [(None, None)]:
            if x is not None and self.inside(x, y):
                run.append((self.px(x), self.py(y)))
                continue
            if len(run) == 1:
                self.fig.circle(run[0][0], run[0][1], 1.5, f"{cls} fa" if cls == "a" else cls)
            elif run:
                self.fig.polyline(run, cls, dash, width)
            run = []

    def band(self, xs, lo, hi, cls="af", opacity=None):
        """The region between lo and hi (the spread over seeds), filled; broken where either is
        not finite."""
        pts = [(xs[i], lo[i], hi[i]) for i in _keep(len(xs), lo, hi)]
        seg = []
        for x, a, b in pts + [(None, None, None)]:
            if x is not None and _ok(a, self.logy) and _ok(b, self.logy) and _ok(x, self.logx):
                a, b = (min(max(v, min(self.ylim)), max(self.ylim)) for v in (a, b))
                seg.append((self.px(x), self.py(a), self.py(b)))
                continue
            if len(seg) > 1:
                self.fig.polygon([(p, q) for p, q, _ in seg] + [(p, r) for p, _, r in reversed(seg)], cls, opacity)
                if cls != "af":                     # a pale fill alone hardly shows: outline it
                    self.fig.polyline([(p, q) for p, q, _ in seg], "m", False, 0.75)
                    self.fig.polyline([(p, r) for p, _, r in seg], "m", False, 0.75)
            seg = []

    def whisker(self, x, values, cls="a", cap=4, mean=True):
        """The spread of one number over seeds at x: a line from the smallest to the largest
        value with caps, and the mean as a dot (mean=False: no dot)."""
        lo, hi = min(values), max(values)
        X, y1, y2 = self.px(x), self.py(lo), self.py(hi)
        self.fig.line(X, y1, X, y2, cls)
        self.fig.line(X - cap, y1, X + cap, y1, cls)
        self.fig.line(X - cap, y2, X + cap, y2, cls)
        if mean:
            self.dot(x, sum(values) / len(values), f"{cls} fa" if cls == "a" else f"{cls} f")

    def dot(self, x, y, cls="a fa", r=3):
        if self.inside(x, y):
            self.fig.circle(self.px(x), self.py(y), r, cls)

    def hline(self, v, label=None, cls="m", dash=True, side="right"):
        """A reference level across the plot (the noise floor, log(10), chance), labelled just
        above the line at the right (side="left": at the left)."""
        y = self.py(v)
        self.fig.line(self.x, y, self.x + self.w, y, cls, dash=dash)
        if label:
            if side == "right":
                self.fig.text(self.x + self.w - 4, y - 5, label, TEXT.get(cls, "tm"), 10.5, "end")
            else:
                self.fig.text(self.x + 4, y - 5, label, TEXT.get(cls, "tm"), 10.5)

    def vline(self, v, label=None, cls="m", dash=True):
        """A marked x (the step a run jumped, p = n), labelled at the top."""
        x = self.px(v)
        self.fig.line(x, self.y, x, self.y + self.h, cls, dash=dash)
        if label:
            self.fig.text(x + 4, self.y + 12, label, TEXT.get(cls, "tm"), 10.5)

    def note(self, x, y, s, cls="tm", size=10.5, anchor="start", dx=0, dy=0, weight=None):
        """Text at a data point, moved by dx, dy pixels."""
        self.fig.text(self.px(x) + dx, self.py(y) + dy, s, cls, size, anchor, weight)

    def legend(self, items, x=None, y=None, gap=17):
        """A legend, one row per item, at pixel (x, y) (default: inside the top-right corner)."""
        w = max(tw(label, 11) for label, *_ in items) + 30
        legend(self.fig, self.x + self.w - w - 6 if x is None else x, self.y + 14 if y is None else y, items, gap)


def legend(fig, x, y, items, gap=17, across=False):
    """[(label, style, dash), ...] as a short line in each style and its label, from pixel (x, y)
    down (across=True: in one row, left to right). Returns the x after the last item."""
    for label, style, *rest in items:
        dash = rest[0] if rest else False
        fig.polyline([(x, y - 4), (x + 22, y - 4)], style, dash, 2.25)
        fig.text(x + 28, y, label, TEXT.get(style, "t"), 11)
        if across:
            x += 28 + tw(label, 11) + 18
        else:
            y += gap
    return x


_legend = legend         # plot() takes a legend= setting of the same name


def _limits(vals, log, pad):
    vals = [v for v in vals if _ok(v, log)]
    if not vals:
        raise ValueError("nothing finite to plot")
    lo, hi = min(vals), max(vals)
    if log:
        a, b = math.log10(lo), math.log10(hi)
        p = (b - a) * pad if b > a else 0.5
        return 10 ** (a - p), 10 ** (b + p)
    if hi == lo:
        return lo - 1, hi + 1
    p = (hi - lo) * pad
    return lo - p, hi + p


def plot(fig, box, series, xlabel="", ylabel="", logx=False, logy=False, xlim=None, ylim=None,
         legend="right", xticks=None, yticks=None, xfmt=None, yfmt=None, pad=0.05):
    """A line plot of series (a list of Series) in box = (x, y, w, h), figure pixels, labels and
    legend included. The limits span every finite value (bands too) with pad of room, unless
    xlim/ylim fix them (ylim=(0, None): fix one end). legend: "right" (a column right of the
    frame), "top" (one row over it), "end" (each label at its curve's last point), or None.
    Bands are drawn first, then the muted curves, the foreground ones, and the accent ones on
    top (in the order given within each); the legend keeps the order given. Returns the Axes,
    to add lines, notes or dots in data units."""
    bx, by, bw, bh = box
    xs = [v for s in series for v in s.xs]
    ys = [v for s in series for v in s.ys + (s.lo or []) + (s.hi or [])]
    auto_x, auto_y = _limits(xs, logx, 0), _limits(ys, logy, pad)
    xlim = tuple(a if a is not None else b for a, b in zip(xlim or (None, None), auto_x))
    ylim = tuple(a if a is not None else b for a, b in zip(ylim or (None, None), auto_y))
    yt = yticks if yticks is not None else ticks(*sorted(ylim), log=logy)
    left = max(tw((yfmt or tick_label)(t), 10.5, mono=True) for t in yt) + 12
    top = 22 if ylabel or legend == "top" else 8
    labelled = [s for s in series if s.label]
    names = [s.label for s in labelled]
    right = {"right": max([tw(n, 11) for n in names] or [0]) + 44,
             "end": max([tw(n, 10.5) for n in names] or [0]) + 10}.get(legend, 10) if labelled else 10
    bottom = 38 if xlabel else 22
    ax = Axes(fig, bx + left, by + top, bw - left - right, bh - top - bottom, xlim, ylim, logx, logy)
    ax.draw(xlabel, "" if legend == "top" else ylabel, xticks, yticks, xfmt=xfmt, yfmt=yfmt)
    for s in series:
        if s.lo is not None and s.hi is not None:
            ax.band(s.xs, s.lo, s.hi, FILL.get(s.style, "fs"), 0.75 if s.style != "a" else None)
    for s in sorted(series, key=lambda s: {"m": 0, "s": 1}.get(s.style, 2)):
        ax.curve(s.xs, s.ys, s.style, s.dash, s.width)
    if not labelled:
        return ax
    items = [(s.label, s.style, s.dash) for s in labelled]
    seen = []
    items = [i for i in items if not (i in seen or seen.append(i))]
    if legend == "right":
        _legend(fig, ax.x + ax.w + 14, ax.y + 10, items)
    elif legend == "top":
        if ylabel:
            fig.text(ax.x - 6, by + 12, ylabel, "tm", 11.5)
        _legend(fig, ax.x + ax.w - sum(28 + tw(i[0], 11) + 18 for i in items) + 18, by + 12, items, across=True)
    elif legend == "end":
        ends = []
        for s in labelled:
            pts = [(x, y) for x, y in zip(s.xs, s.ys) if ax.inside(x, y)]
            if pts:
                ends.append([ax.py(pts[-1][1]) + 3.5, s])
        ends.sort(key=lambda e: e[0])
        for i in range(1, len(ends)):                 # keep end labels 12 px apart
            ends[i][0] = max(ends[i][0], ends[i - 1][0] + 12)
        for y, s in ends:
            fig.text(ax.x + ax.w + 6, y, s.label, TEXT.get(s.style, "t"), 10.5)
    return ax


def seeds_chart(fig, box, groups, ylabel="", ylim=None, logy=False, yticks=None, yfmt=None, pad=0.08):
    """Which setting won, over seeds: one column per group (label, values over seeds, style),
    each seed a small ring, the mean a short bar with its value printed beside it, and the
    min-max whisker. box = (x, y, w, h). A label may hold "\\n" for a second line. Returns the
    Axes (x runs 0 .. len(groups) - 1)."""
    bx, by, bw, bh = box
    vals = [v for _, vs, _ in groups for v in vs]
    auto = _limits(vals, logy, pad)
    ylim = tuple(a if a is not None else b for a, b in zip(ylim or (None, None), auto))
    yt = yticks if yticks is not None else ticks(*sorted(ylim), log=logy)
    left = max(tw((yfmt or tick_label)(t), 10.5, mono=True) for t in yt) + 12
    lines = max(len(g[0].split("\n")) for g in groups)
    ax = Axes(fig, bx + left, by + 22, bw - left - 4, bh - 22 - 8 - 14 * lines, (-0.5, len(groups) - 0.5), ylim, False, logy)
    ax.draw(xticks=[], yticks=yticks, ylabel=ylabel, yfmt=yfmt)
    for i, (label, vs, style) in enumerate(groups):
        X = ax.px(i)
        for k, line in enumerate(label.split("\n")):
            fig.text(X, ax.y + ax.h + 15 + 14 * k, line, TEXT.get(style, "t") if k == 0 else "tm", 11, "middle",
                     600 if style == "a" and k == 0 else None)
        ax.whisker(i, vs, style, cap=6, mean=False)
        for v in vs:
            if ax.inside(i, v):
                fig.circle(X, ax.py(v), 2.5, f"{style} f")
        m = sum(vs) / len(vs)
        fig.line(X - 14, ax.py(m), X + 14, ax.py(m), style)
        fig.text(X + 18, ax.py(m) + 3.5, sig(m), TEXT.get(style, "t"), 10.5, mono=True)
    return ax


# ---------------------------------------------------------------- computation graphs

VALUE_W, VALUE_H, OP_R = 96, 42, 14


def _op_r(label):
    return max(OP_R, tw(label, 10, mono=True) / 2 + 6)


def graph(fig, nodes, edges, here=(), grads=True, value_w=VALUE_W):
    """A computation graph. nodes: {key: (kind, x, y, label, value, grad)}, kind "value" (a box
    value_w wide: label and value on the first line, "grad g" under it) or "op" (a circle with
    the operation: "+", "*", "tanh"); x, y its centre in figure pixels; value/grad numbers (4
    significant digits) or text, or None. edges: [(from key, to key)], drawn as arrows in the
    forward direction. here: keys drawn in the accent (the node a step is at); an edge between
    two of them too. grads=False leaves the gradients out (before backward has run).
    Returns {key: (x, y)}."""
    def half(k):
        kind, label = nodes[k][0], nodes[k][3]
        return (_op_r(label),) * 2 if kind == "op" else (value_w / 2, VALUE_H / 2)

    def clip(k, dx, dy):
        """How far from k's centre, towards (dx, dy), its edge is: the arrow starts or ends there."""
        d = math.hypot(dx, dy) or 1
        ux, uy = dx / d, dy / d
        hw, hh = half(k)
        if nodes[k][0] == "op":
            return ux * (hw + 2), uy * (hw + 2)
        t = min(hw / abs(ux) if ux else 1e9, hh / abs(uy) if uy else 1e9)
        return ux * (t + 2), uy * (t + 2)

    def num(v):
        return sig(v, 4) if isinstance(v, float) else str(v)

    for a, b in edges:
        (_, xa, ya, *_), (_, xb, yb, *_) = nodes[a], nodes[b]
        dx, dy = xb - xa, yb - ya
        sa, sb = clip(a, dx, dy), clip(b, -dx, -dy)
        cls = "a" if a in here and b in here else "s"
        fig.line(xa + sa[0], ya + sa[1], xb + sb[0], yb + sb[1], cls, arrow=True)
    for k, (kind, x, y, label, val, grad) in nodes.items():
        lit = k in here
        if kind == "op":
            fig.circle(x, y, _op_r(label), "a af" if lit else "s f")
            fig.text(x, y + (4.5 if len(label) == 1 else 3.5), label, "ta" if lit else "t",
                     14 if len(label) == 1 else 10, "middle", 600, mono=True)
            continue
        fig.rect(x - value_w / 2, y - VALUE_H / 2, value_w, VALUE_H, "a af" if lit else "s f", 6)
        fig.text(x - value_w / 2 + 8, y - 4, label, "ta" if lit else "t", 12, weight=700, mono=True)
        if val is not None:
            fig.text(x + value_w / 2 - 8, y - 4, num(val), "ta" if lit else "t", 11.5, "end", mono=True)
        if grads and grad is not None:
            g = num(grad)
            word = "grad" if tw("grad", 10.5) + tw(g, 11, mono=True) + 22 <= value_w else "g"
            fig.text(x - value_w / 2 + 8, y + 13, word, "tm", 10.5)
            fig.text(x + value_w / 2 - 8, y + 13, g, "ta", 11, "end", 600, mono=True)
    return {k: (n[1], n[2]) for k, n in nodes.items()}


# ---------------------------------------------------------------- tensors

def shape_text(shape):
    """(2, 3) as a page writes it: "(2, 3)", "(4,)" for one dimension."""
    shape = tuple(shape)
    return "(" + ", ".join(str(d) for d in shape) + ("," if len(shape) == 1 else "") + ")"


def tensor(fig, x, y, values, cell=(36, 22), label=None, here=(), ghost=(), digits=3, shape=True, size=11):
    """A small tensor as a grid, its top-left corner at (x, y): values is a list (one row) or a
    list of rows, each a number, a string, or None for an empty cell. here: cells (i, j) lit in
    the accent; ghost: cells drawn dashed and muted (the copies broadcasting makes, never stored).
    label goes over the grid, the shape (shape=True) under it. Returns (width, height) of the grid."""
    rows = values if values and isinstance(values[0], (list, tuple)) else [values]
    one_d = not (values and isinstance(values[0], (list, tuple)))
    cw, ch = cell
    if label:
        fig.text(x, y - 7, label, "t", 12, weight=600, mono=True)
    for i, row in enumerate(rows):
        for j, v in enumerate(row):
            k = (j if one_d else (i, j))
            cx, cy = x + j * cw, y + i * ch
            lit, gh = k in here or (i, j) in here, k in ghost or (i, j) in ghost
            fig.rect(cx, cy, cw, ch, "a af" if lit else ("m f" if gh else "s f"), 0, dash=gh)
            if v is not None:
                s = v if isinstance(v, str) else (sig(v, digits) if isinstance(v, float) else str(v))
                fig.text(cx + cw / 2, cy + ch / 2 + size * 0.36, s, "ta" if lit else ("tm" if gh else "t"), size,
                         "middle", mono=True)
    w, h = cw * max(len(r) for r in rows), ch * len(rows)
    if shape:
        dims = (len(rows[0]),) if one_d else (len(rows), len(rows[0]))
        fig.text(x + w / 2, y + h + 15, shape_text(dims), "tm", 10.5, "middle", mono=True)
    return w, h


def shape_box(fig, x, y, w, h, rows, cols, label=None, cls="s f", dash=False, tcls="t"):
    """A tensor too big to draw cell by cell (784 x 100 weights) as one rectangle at (x, y), w by
    h pixels (the caller picks them, roughly in proportion), with rows written along its left
    side and cols along its top, and label inside it. rows/cols are numbers or names ("batch")."""
    fig.rect(x, y, w, h, cls, 3, dash)
    fig.text(x - 5, y + h / 2 + 3.5, str(rows), "tm", 10.5, "end", mono=True)
    fig.text(x + w / 2, y - 5, str(cols), "tm", 10.5, "middle", mono=True)
    if label:
        fig.text(x + w / 2, y + h / 2 + 4, label, tcls, 11.5, "middle", 600, mono=True)


# ---------------------------------------------------------------- layered networks

def network(fig, box, sizes, max_units=5, here=(), names=None, r=None):
    """A layered network in box = (x, y, w, h): one column per layer (sizes = [784, 64, ..., 10]),
    at most max_units units drawn per column (the middle ones replaced by a vertical "...") with
    the layer's size under it, every drawn unit joined to every unit of the next column. here:
    layer indices drawn in the accent. names: a label per column under its size (default none).
    Returns the columns' x centres, for layer_bars(xs=...)."""
    bx, by, bw, bh = box
    n = len(sizes)
    step = bw / n
    xs = [bx + step * (i + 0.5) for i in range(n)]
    foot = 16 + (14 if names else 0)
    r = r or max(3.0, min(9.0, step * 0.22, (bh - foot) / (max_units * 2.6)))
    cols = []
    for i, size in enumerate(sizes):
        k = min(size, max_units)
        gap = (bh - foot) / max_units
        y0 = by + (bh - foot) / 2 - gap * (k - 1) / 2
        ys = [y0 + gap * j for j in range(k)]
        cols.append(ys)
    for i in range(n - 1):
        d = " ".join(f"M{xs[i] + r:.1f} {ya:.1f}L{xs[i + 1] - r:.1f} {yb:.1f}" for ya in cols[i] for yb in cols[i + 1])
        lit = i in here and i + 1 in here
        fig.add(f'<path class="{"a" if lit else "m"}" d="{d}" stroke-width="0.6" stroke-opacity="0.8"/>')
    for i, (size, ys) in enumerate(zip(sizes, cols)):
        lit = i in here
        cut = size > max_units
        for j, y in enumerate(ys):
            if cut and j == len(ys) // 2:
                fig.text(xs[i], y + 4, "...", "ta" if lit else "tm", 11, "middle", mono=True)
                continue
            fig.circle(xs[i], y, r, "a af" if lit else "s f")
        fig.text(xs[i], by + bh - foot + 13, str(size), "ta" if lit else "tm", 10, "middle", mono=True)
        if names:
            fig.text(xs[i], by + bh - 2, names[i], "ta" if lit else "tm", 10.5, "middle")
    return xs


def layer_bars(fig, box, series, labels=None, log=True, floor=None, xs=None, ylabel="", values=False,
               yticks=None, here=()):
    """A bar per layer, in box = (x, y, w, h): series = [(label, values per layer, style)], each
    layer's bars side by side (two series: activation spread and gradient). log=True (default):
    heights on a log axis down to floor (default a tenth of the smallest value), as these sizes
    run from 1 to 1e-11. labels: one per layer under its bars (default 1, 2, ...; "" skips one).
    xs: the layers' x centres (network()'s return) to line the bars up under a drawing. values:
    print each bar's number over it (only when there are few). here: layer indices lit.
    Returns the Axes (y in data units; x is pixels)."""
    bx, by, bw, bh = box
    n = len(series[0][1])
    allv = [v for _, vs, _ in series for v in vs if _ok(v, log)]
    lo = floor if floor is not None else (min(allv) / 10 if log else 0)
    hi = max(allv) * (3 if log else 1.08)
    yt = yticks if yticks is not None else ticks(lo, hi, log=log)
    left = max(tw(tick_label(t), 10.5, mono=True) for t in yt) + 12
    top = (24 if ylabel or len(series) > 1 else 8) + (12 if values else 0)
    if xs is None:
        step = (bw - left - 6) / n
        xs = [bx + left + step * (i + 0.5) for i in range(n)]
        x0, x1 = bx + left, bx + bw - 6
    else:
        step = (xs[-1] - xs[0]) / max(1, n - 1) if n > 1 else bw
        x0, x1 = xs[0] - step / 2, xs[-1] + step / 2
    ax = Axes(fig, x0, by + top, x1 - x0, bh - top - 20, (x0, x1), (lo, hi), False, log)
    ax.draw(xticks=[], yticks=yticks, frame=False)
    if ylabel:
        fig.text(ax.x - 6, by + 13, ylabel, "tm", 11.5)
    fig.line(x0, ax.y + ax.h, x1, ax.y + ax.h, "m")
    k = len(series)
    bw_each = min(14, step * 0.7 / k)
    for i in range(n):
        for s, (_, vs, style) in enumerate(series):
            v = vs[i]
            X = xs[i] - bw_each * k / 2 + bw_each * s
            if not _ok(v, log):
                continue
            top_y = ax.py(min(max(v, lo), hi))
            cls = "a af" if (style == "a" or i in here) else ("s fs" if style == "s" else "m fs")
            fig.rect(X, top_y, bw_each - 1, ax.y + ax.h - top_y, cls, 1)
            if values:
                fig.text(X + bw_each / 2, top_y - 4, sig(v, 2), TEXT.get(style, "t"), 9.5, "middle", mono=True)
        lab = str(i + 1) if labels is None else labels[i]
        if lab:
            fig.text(xs[i], ax.y + ax.h + 14, lab, "ta" if i in here else "tm", 10, "middle", mono=True)
    if len(series) > 1:
        x = bx + bw - sum(15 + tw(label, 11) + 18 for label, _, _ in series) + 18
        for label, _, style in series:
            fig.rect(x, by + 4, 10, 10, "a af" if style == "a" else ("s fs" if style == "s" else "m fs"), 1)
            fig.text(x + 15, by + 13, label, TEXT.get(style, "t"), 11)
            x += 15 + tw(label, 11) + 18
    return ax
