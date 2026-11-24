"""Figures for research module 13, Experiments that hold up (lessons 13.01-13.04).

    RESEARCH_FIGS_CACHE=DIR python3 -B art/research/figs13.py [13.02 ...]
                                    all of them, or those whose name starts so (DIR keeps the runs)

Every dot, bar, curve and number comes from the reference code (tracks/research), run as the page runs
it, from the fetched data, or from the recorded runs the pages read; where a figure computes a number the
page prints, it stops if the two differ:

  13.01  python3 -m experiments.baseline (the page's run): every trial's and every fresh seed's summary,
         checked against the gaps, t's and best-of table it printed; the same with trials=16 (the page's
         aside)
  13.02  python3 -m experiments.errorbars (the page's run): each seed's summary, and the tables it
         printed (the intervals, the test text's standard errors); experiments/recorded/errorbars/ (every
         seed's summary); Student's t, the intervals and seeds_needed from lab/stats.py at 13.02
  13.03  python3 -m experiments.fooled (the page's run): the 32 runs' summaries, the chosen table, what it
         printed; CIFAR-10's and MNIST's twins found again in the project at 13.03 with its shrink and
         two_nearest (the count must be the run's), the images from the fetched files; shared_grams on
         Tiny Shakespeare at more lengths (those the run printed must agree)
  13.04  experiments/recorded/scaling/ (every run's summary and log, fit/seed0/summary.json and
         output.txt); the fits made again with lab/stats.py at 13.04 (they must be the recorded ones)

Needs PyTorch, MNIST, CIFAR-10 and TinyStories (python3 -m data.fetch mnist, cifar10, tinystories, in
tracks/research). The runs take about three minutes in all on the machine in NOTES.md, most of it
errorbars' six models; RESEARCH_FIGS_CACHE keeps them between processes.
"""
import json
import math
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)                          # art/research/: figlib, figart
import figart  # noqa: E402
import figlib  # noqa: E402
from figlib import Fig, sig, tw, write  # noqa: E402

MOD = "13"
REC = os.path.join(figlib.TRACK, "experiments", "recorded")
TEXT = {"a": "ta", "s": "t", "m": "tm"}
_memo = {}


def in_project(at, code):
    """Run python code in the project as it stands at lesson `at`, in a fresh python; the JSON it prints
    last (once per process for the same code)."""
    if (at, code) in _memo:
        return _memo[at, code]
    d = figart.project(at)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=d)
    r = subprocess.run([sys.executable, "-B", "-c", code], cwd=d, env=env, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"python in the project at {at} failed:\n{r.stdout[-1500:]}{r.stderr[-1500:]}")
    _memo[at, code] = json.loads(r.stdout.strip().splitlines()[-1])
    return _memo[at, code]


def mean(xs):
    return sum(xs) / len(xs)


def sd(xs):
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def welch(a, b):
    return (mean(a) - mean(b)) / math.sqrt(sd(a) ** 2 / len(a) + sd(b) ** 2 / len(b))


def same(what, ours, printed):
    """Stop the generator when a number it computed is not the one the page's run printed."""
    if ours != printed:
        raise SystemExit(f"{what}: computed here {ours!r}, the run printed {printed!r}")


def seeds_of(d, key):
    return [figart.summary(x)[key] for x in figart.seed_dirs(d)]


def find(out, regex):
    m = re.search(regex, out, re.M)
    if not m:
        raise SystemExit(f"no {regex!r} in:\n{out[-1500:]}")
    return m


def bracket(f, x1, x2, y, text, cls="a", tcls="ta", up=True):
    """A bracket over (or under) x1..x2 at y with a label beside its middle."""
    d = 6 if up else -6
    f.path(f"M{x1:.1f} {y + d:.1f}L{x1:.1f} {y:.1f}L{x2:.1f} {y:.1f}L{x2:.1f} {y + d:.1f}", cls)
    f.text((x1 + x2) / 2, y - 6 if up else y + 14, text, tcls, 10.5, "middle", 600)


# ================================================================== 13.01

def base_run():
    return figart.experiment("baseline", at="13.01")


def wide_run():
    return figart.experiment("baseline", "trials=16", at="13.01")


def trials_of(r, name):
    """Each trial of one optimiser's search: [(lr, validation %, test %)] in trial order."""
    k, out = 0, []
    while os.path.isdir(os.path.join(r.runs, f"search-{name}-{k}")):
        s = figart.summary(os.path.join(r.runs, f"search-{name}-{k}", "seed0"))
        out.append((s["lr"], 100 * s["val_error"], 100 * s["test_error"]))
        k += 1
    return out


def fresh_of(r, label):
    return [100 * e for e in seeds_of(os.path.join(r.runs, label), "test_error")]


def best_of(scores, n, reported=None):
    """lab.best_of, again here (the table the run printed checks it)."""
    reported = scores if reported is None else reported
    order = sorted(range(len(scores)), key=lambda i: scores[i])
    N = len(scores)
    return sum(reported[j] * math.comb(N - 1 - i, n - 1) for i, j in enumerate(order)) / math.comb(N, n)


def checked_arms(r):
    """The three arms' fresh-seed test errors, %, checked against the gaps and t's the run printed."""
    adam, docs, tuned = (fresh_of(r, k) for k in ("adam-tuned", "nesterov-docs", "nesterov-tuned"))
    for words, other in (("3. The hurried", docs), ("4. The fair", tuned)):
        m = find(r.out, rf"^{words} .*:\n   SGD's test error minus Adam's: ([+-][\d.]+) points, t = ([+-][\d.]+): (.*)$")
        same(words, (f"{mean(other) - mean(adam):+.2f}", f"{welch(other, adam):+.1f}"), m.groups()[:2])
    return adam, docs, tuned


def hurried1301():
    r = base_run()
    adam, docs, tuned = checked_arms(r)
    lr = {k: figart.summary(figart.seed_dirs(os.path.join(r.runs, k))[0])["lr"]
          for k in ("adam-tuned", "nesterov-docs", "nesterov-tuned")}
    f = Fig("hurried1301", "Test error on 5 fresh seeds (a ring per seed, the bar their mean, the whisker min to max): "
                           "the hurried comparison, Adam's rate searched and SGD's taken from PyTorch's documentation, "
                           "beside the fair one, both rates from the same search", 318)
    ylim, yt = (4, 17), [4, 6, 8, 10, 12, 14, 16]
    panels = [("the hurried comparison", [(f"Adam\nlr {lr['adam-tuned']:.3g}, searched", adam, "a"),
                                          (f"SGD, Nesterov\nlr {lr['nesterov-docs']:g}, the docs'", docs, "s")], docs),
              ("the fair comparison", [(f"Adam\nlr {lr['adam-tuned']:.3g}, searched", adam, "a"),
                                       (f"SGD, Nesterov\nlr {lr['nesterov-tuned']:.3g}, searched", tuned, "s")], tuned)]
    for p, (title, groups, other) in enumerate(panels):
        x0 = 8 + p * 316
        f.text(x0 + 52, 20, title, "t", 12, weight=700)
        ax = figart.seeds_chart(f, (x0, 24, 300, 236), groups, ylabel="test error, %" if p == 0 else "",
                                ylim=ylim, yticks=yt)
        gap, t = mean(other) - mean(adam), welch(other, adam)
        verdict = "held: Adam lower" if t >= 3 else "a tie"
        f.text(ax.x + ax.w / 2, 300, f"SGD minus Adam: {gap:+.2f} points, t = {t:+.1f}", "ta" if p == 0 else "t", 11,
               "middle", 700)
        f.text(ax.x + ax.w / 2, 314, f"by the rule written first: {verdict}", "ta" if p == 0 else "t", 10.5, "middle")
    return f


def search1301():
    r = base_run()
    cfg = figart.config(os.path.join(r.runs, "search-adam-0", "seed0"))
    f = Fig("search1301", "The search, trial by trial: each optimiser's 8 learning rates, drawn log-uniform over its "
                          "own two decades, every one on seed 0, and its error on the validation images; the one "
                          "chosen in the accent", 300)
    for p, (name, title, rng) in enumerate((("adam", "Adam", cfg["adam"]), ("nesterov", "SGD, Nesterov momentum 0.9",
                                                                           cfg["nesterov"]))):
        trials = sorted(trials_of(r, name))
        x0 = 56 + p * 316
        ax = figart.Axes(f, x0, 44, 250, 190, tuple(rng), (0, 33), True, False)
        ticks = [v for v in (1e-4, 3e-4, 1e-3, 3e-3, 1e-2, 3e-2, 1e-1, 3e-1) if rng[0] <= v <= rng[1]]
        ax.draw(xlabel="learning rate (log scale)", ylabel="validation error, %" if p == 0 else "", xticks=ticks,
                yticks=[0, 10, 20, 30], xfmt=lambda v: f"{v:g}")
        f.text(x0, 24, f"{title}: {rng[0]:g} to {rng[1]:g}", "t", 12, weight=700)
        ax.curve([t[0] for t in trials], [t[1] for t in trials], "m", width=1)
        chosen = min(trials, key=lambda t: t[1])
        for lr, v, _ in trials:
            ax.dot(lr, v, "a fa" if (lr, v) == chosen[:2] else "s f", 4.5 if (lr, v) == chosen[:2] else 3.5)
        ax.note(chosen[0], chosen[1], f"chosen: {chosen[0]:.3g}, {chosen[1]:.2f}%", "ta", 10.5, "end", 4, 20,
                weight=700)
        if name == "nesterov":
            ax.vline(cfg["default_lr"], None)
            ax.note(cfg["default_lr"], 31, f"the docs' {cfg['default_lr']:g}", "tm", 10.5, dx=5)
            near = min(trials, key=lambda t: abs(math.log(t[0] / cfg["default_lr"])))
            ax.note(near[0], near[1], f"{near[1]:.2f}%", "t", 10, dx=6, dy=-8)
    f.text(56, 290, "Neither choice is at the edge of its range: a better rate outside it is not likely.", "tm", 10.5)
    return f


def draws1301():
    r = base_run()
    cfg = figart.config(os.path.join(r.runs, "search-adam-0", "seed0"))
    rates = {name: [t[0] for t in trials_of(r, name)] for name in ("adam", "nesterov")}
    us = {name: [math.log(x / cfg[name][0]) / math.log(cfg[name][1] / cfg[name][0]) for x in xs]
          for name, xs in rates.items()}
    if any(abs(a - b) > 1e-9 for a, b in zip(us["adam"], us["nesterov"])):
        raise SystemExit(f"the two searches do not share their draws: {us}")
    f = Fig("draws1301", "draw_rates: 8 numbers u drawn once between 0 and 1, and each put into both ranges as low "
                         "(high / low)^u, so the k-th trial of each search sits at the same place in its own range",
            226)
    x0, x1 = 150, 610
    rows = [("u, drawn once", None, 44), ("Adam's rates", cfg["adam"], 120), ("SGD's rates", cfg["nesterov"], 196)]
    for label, rng, y in rows:
        f.line(x0, y, x1, y, "m")
        f.text(x0 - 14, y + 4, label, "t", 11.5, "end", 600)
        if rng is None:
            for v in (0, 0.25, 0.5, 0.75, 1):
                f.line(x0 + v * (x1 - x0), y, x0 + v * (x1 - x0), y + 4, "m")
                f.text(x0 + v * (x1 - x0), y + 17, f"{v:g}", "tm", 10, "middle", mono=True)
        else:
            for k in range(3):
                v = rng[0] * 10 ** k
                if v <= rng[1] * 1.0001:
                    X = x0 + math.log(v / rng[0]) / math.log(rng[1] / rng[0]) * (x1 - x0)
                    f.line(X, y, X, y + 4, "m")
                    f.text(X, y + 17, f"{v:g}", "tm", 10, "middle", mono=True)
    for k, u in enumerate(us["adam"]):
        X = x0 + u * (x1 - x0)
        f.line(X, rows[0][2], X, rows[2][2], "a" if k == 0 else "m", dash=k != 0)
        for _, rng, y in rows:
            f.circle(X, y, 4 if k == 0 else 3, "a fa" if k == 0 else "s f")
        f.text(X, rows[0][2] - 9, str(k), "ta" if k == 0 else "tm", 10, "middle", mono=True)
    X0 = x0 + us["adam"][0] * (x1 - x0)
    f.text(X0 + 8, 88, f"trial 0: u = {us['adam'][0]:.3f}", "ta", 10.5, weight=600)
    f.text(X0 + 8, 112, f"Adam {rates['adam'][0]:.3g}", "ta", 10.5, weight=600)
    f.text(X0 + 8, 188, f"SGD {rates['nesterov'][0]:.3g}", "ta", 10.5, weight=600)
    return f


def bestof1301():
    r = base_run()
    rows = [tuple(float(v) for v in m) for m in re.findall(r"^ +(\d+) +([\d.]+) +([\d.]+) +([\d.]+) +([\d.]+)$",
                                                             r.out, re.M)]
    curves = {}
    for name in ("adam", "nesterov"):
        t = trials_of(r, name)
        val, test = [x[1] for x in t], [x[2] for x in t]
        curves[name] = ([best_of(val, n) for n in range(1, len(t) + 1)],
                        [best_of(val, n, test) for n in range(1, len(t) + 1)])
    for i, row in enumerate(rows):
        same(f"best of {i + 1}", [f"{v:.2f}" for v in (curves["adam"][0][i], curves["adam"][1][i],
                                                       curves["nesterov"][0][i], curves["nesterov"][1][i])],
             [f"{v:.2f}" for v in row[1:]])
    n = list(range(1, len(rows) + 1))
    f = Fig("bestof1301", "What a search of n trials buys, worked out from the 8 each search made: the expected best "
                          "validation error of n trials drawn at random (solid), and the test error of the trial so "
                          "chosen (dashed)", 300)
    series = [figart.Series("SGD, validation", n, curves["nesterov"][0], "s"),
              figart.Series("SGD, test of the chosen", n, curves["nesterov"][1], "s", True),
              figart.Series("Adam, validation", n, curves["adam"][0], "a"),
              figart.Series("Adam, test of the chosen", n, curves["adam"][1], "a", True)]
    ax = figart.plot(f, (8, 6, 624, 260), series, xlabel="trials in the search (n)", ylabel="error, %",
                     ylim=(0, 17), yticks=[0, 4, 8, 12, 16], xticks=n, legend="right")
    for k in (1, len(n)):
        a, s = curves["adam"][0][k - 1], curves["nesterov"][0][k - 1]
        X = ax.px(k) + (10 if k == 1 else -10)
        f.line(X, ax.py(a), X, ax.py(s), "m", start=True, arrow=True)
        ax.note(k, 2.2, f"n = {k}: SGD {s - a:.2f} behind", "t", 10.5, "start" if k == 1 else "end",
                dx=6 if k == 1 else -6, weight=600)
    f.text(16, 292, "A search of 1 trial is a rate picked at random in the range; most of what 8 buy comes in the "
                    "first 3 or 4.", "tm", 10.5)
    return f


def wider1301():
    r, w = base_run(), wide_run()
    eight, sixteen = trials_of(r, "nesterov"), trials_of(w, "nesterov")
    if sixteen[:8] != eight:
        raise SystemExit("the 16-trial search does not start with the 8 trials of the 8-trial one")
    tuned8, tuned16 = fresh_of(r, "nesterov-tuned"), fresh_of(w, "nesterov-tuned")
    m = find(w.out, r"^   nesterov, tuned +lr (\S+) +(\S+) \+- ")
    same("16 trials' SGD", (f"{max(sixteen, key=lambda t: -t[1])[0]:.3g}", f"{mean(tuned16):.3g}"), m.groups())
    f = Fig("wider1301", "A search twice as large, still on one seed: SGD's 8 more trials (accent) hold a rate a little "
                         "better on seed 0's validation images, and on 5 fresh seeds it is worse and far less steady",
            300)
    ax = figart.Axes(f, 56, 44, 250, 190, (0.03, 0.3), (7.2, 8.6), True, False)
    ax.draw(xlabel="learning rate (log scale)", ylabel="validation error, %, seed 0", xticks=[0.03, 0.1, 0.3],
            yticks=[7.4, 7.8, 8.2, 8.6], xfmt=lambda v: f"{v:g}")
    f.text(56, 24, "SGD's best trials, of 16", "t", 12, weight=700)
    for k, (lr, v, _) in enumerate(sixteen):
        if ax.inside(lr, v):
            ax.dot(lr, v, "a fa" if k >= 8 else "s f", 4)
    c8, c16 = min(eight, key=lambda t: t[1]), min(sixteen, key=lambda t: t[1])
    ax.note(c8[0], c8[1], f"best of 8: {c8[0]:.3g}", "t", 10.5, "end", -8, 4)
    ax.note(c16[0], c16[1], f"best of 16: {c16[0]:.3g}", "ta", 10.5, "end", -8, 14, weight=700)
    figart.seeds_chart(f, (330, 24, 300, 236), [(f"lr {c8[0]:.3g}\nbest of 8", tuned8, "s"),
                                                (f"lr {c16[0]:.3g}\nbest of 16", tuned16, "a")],
                       ylabel="test error, %, 5 fresh seeds", ylim=(6, 14), yticks=[6, 8, 10, 12, 14])
    f.text(56, 292, f"Validation, seed 0: {c16[1]:.2f}% against {c8[1]:.2f}%. Fresh seeds: {mean(tuned16):.3g} +- "
                    f"{sd(tuned16):.3g} against {mean(tuned8):.3g} +- {sd(tuned8):.3g}.", "tm", 10.5)
    return f


# ================================================================== 13.02

def eb_run():
    return figart.experiment("errorbars", at="13.02")


def arms_page():
    r = eb_run()
    one, four = (seeds_of(os.path.join(r.runs, f"heads{h}"), "test_bits") for h in (1, 4))
    for name, xs in (("1 head", one), ("4 heads", four)):
        m = find(r.out, rf"^   {name} +(\S+) \+- ")
        same(name, f"{mean(xs):.4g}", m.group(1))
    return one, four


def arms_recorded():
    d = os.path.join(REC, "errorbars")
    one, four = (seeds_of(os.path.join(d, f"heads{h}"), "test_bits") for h in (1, 4))
    with open(os.path.join(d, "output.txt")) as fh:
        printed = fh.read()
    for name, xs in (("1 head", one), ("4 heads", four)):
        same(f"recorded {name}", f"{mean(xs):.4g}", find(printed, rf"^   {name} +(\S+) \+- ").group(1))
    return one, four


T_CODE = """
import json, lab
from statistics import NormalDist
xs = [i / 20 for i in range(-140, 141)]
print(json.dumps({"x": xs, "normal": [NormalDist().pdf(x) for x in xs],
                  "t2": [lab.stats.t_density(x, 2) for x in xs], "t9": [lab.stats.t_density(x, 9) for x in xs],
                  "q2": lab.t_quantile(0.975, 2), "q9": lab.t_quantile(0.975, 9), "z": NormalDist().inv_cdf(0.975)}))
"""


def t1302():
    d = in_project("13.02", T_CODE)
    r = eb_run()
    same("t at 2 degrees of freedom", f"{d['q2']:.2f}", find(r.out, r"95% interval, t ([\d.]+)").group(1))
    f = Fig("t1302", "Student's t: how far a mean of n seeds falls from the truth, in its own standard errors, when "
                     "the standard error was measured from the same n; at 3 seeds (2 degrees of freedom) and at 10 (9), "
                     "beside the normal; 95% of each lies between its marks", 300)
    series = [figart.Series("the normal (sd known)", d["x"], d["normal"], "s"),
              figart.Series("t, 9 degrees of freedom", d["x"], d["t9"], "m", True),
              figart.Series("t, 2 degrees of freedom", d["x"], d["t2"], "a")]
    ax = figart.plot(f, (8, 6, 624, 260), series, xlabel="(mean - truth) / sem", ylabel="density", xlim=(-7, 7),
                     ylim=(0, 0.42), xticks=[-6, -4, -2, 0, 2, 4, 6], yticks=[0, 0.1, 0.2, 0.3, 0.4], legend="right")
    for q, cls, y, lab in ((d["z"], "s", 0.36, "1.96"), (d["q9"], "m", 0.30, f"{d['q9']:.2f}"),
                           (d["q2"], "a", 0.24, f"{d['q2']:.2f}")):
        for s in (-1, 1):
            f.line(ax.px(s * q), ax.py(0), ax.px(s * q), ax.py(y - 0.02), cls, dash=cls != "a")
        ax.note(q, y, lab, TEXT[cls], 11, dx=4, weight=700)
    f.text(16, 292, "With 3 seeds the interval that holds the truth 95 times in 100 is +- 4.30 standard errors, not "
                    "+- 1.96: 2.2 times as wide.", "tm", 10.5)
    return f


def interval_rows(out, part):
    """The printed table of part 2 or 6: {name: [(t lo, hi), (1.96 lo, hi), (bootstrap lo, hi)]}, and the t used."""
    start = out.index("2 and 3." if part == 2 else "6. The recorded")
    chunk = out[start:]
    t = float(find(chunk, r"95% interval, t ([\d.]+)").group(1))
    rows = {}
    for name in ("1 head", "4 heads"):
        m = find(chunk, rf"^   {name} +[\d.]+ +[\d.]+ +([\d.]+) to ([\d.]+) +([\d.]+) to ([\d.]+) +([\d.]+) to ([\d.]+)$")
        v = [float(x) for x in m.groups()]
        rows[name] = [(v[0], v[1]), (v[2], v[3]), (v[4], v[5])]
    return rows, t


INTERVAL_CODE = """
import json, lab
a = {a}
print(json.dumps([lab.interval(xs) for xs in a]))
"""


def intervals1302():
    r = eb_run()
    page, rec = arms_page(), arms_recorded()
    p_rows, p_t = interval_rows(r.out, 2)
    r_rows, r_t = interval_rows(r.out, 6)
    ours = in_project("13.02", INTERVAL_CODE.format(a=json.dumps([page[0], page[1], rec[0], rec[1]])))
    for (name, rows), got in zip([("1 head", p_rows), ("4 heads", p_rows), ("1 head", r_rows), ("4 heads", r_rows)],
                                 ours):
        same(f"{name}'s t interval", [f"{v:.4f}" for v in got], [f"{v:.4f}" for v in rows[name][0]])
    f = Fig("intervals1302", "Each arm's mean with a 95% interval three ways, at the page's 3 seeds and the recorded 10: "
                             "Student's t, the normal's 1.96 in its place, and the bootstrap; a tick for each seed, and "
                             "each interval's width at the right", 352)
    ax = figart.Axes(f, 130, 30, 380, 262, (3.38, 3.48), (0, 1), False, False)
    ax.draw(xlabel="bits per character on the test text", xticks=[3.38, 3.40, 3.42, 3.44, 3.46, 3.48], yticks=[],
            grid=False)
    f.text(ax.x + ax.w + 14, ax.y - 8, "width", "tm", 10.5)
    ways = [("Student's t", "a"), ("1.96", "m"), ("bootstrap", "s")]
    y = ax.y + 16
    for name, idx in (("1 head", 0), ("4 heads", 1)):
        for label, rows, tq, xs in (("3 seeds", p_rows, p_t, page[idx]), ("10 seeds", r_rows, r_t, rec[idx])):
            f.text(ax.x - 10, y + 16, f"{name},", "t", 11, "end", 600)
            f.text(ax.x - 10, y + 30, f"{label}: t {tq:.2f}", "tm", 10.5, "end")
            for xv in xs:
                f.line(ax.px(xv), y + 34, ax.px(xv), y + 41, "m")
            for k, ((lo, hi), (way, cls)) in enumerate(zip(rows[name], ways)):
                Y = y + k * 12
                f.line(ax.px(lo), Y, ax.px(hi), Y, cls)
                f.line(ax.px(lo), Y - 3, ax.px(lo), Y + 3, cls)
                f.line(ax.px(hi), Y - 3, ax.px(hi), Y + 3, cls)
                f.text(ax.x + ax.w + 14, Y + 4, f"{hi - lo:.4f}", TEXT[cls], 10, weight=700 if k == 0 else None,
                       mono=True)
            y += 64
    x = ax.x + 4
    for way, cls in ways:
        label = way if way != "1.96" else "1.96 in place of t"
        f.line(x, 342, x + 22, 342, cls)
        f.text(x + 28, 346, label, TEXT[cls], 10.5)
        x += 28 + tw(label, 10.5) + 24
    return f


def diff_parts(out, part):
    start = out.index("2 and 3." if part == 2 else "6. The recorded")
    chunk = out[start:]
    welch_lo, welch_hi = (float(v) for v in find(chunk, r"\(Welch\): +([+-][\d.]+) to ([+-][\d.]+)").groups())
    pair_lo, pair_hi = (float(v) for v in find(chunk, r"as pairs, seed by seed: +([+-][\d.]+) to ([+-][\d.]+)").groups())
    corr = float(find(chunk, r"correlation ([+-][\d.]+)").group(1))
    return (welch_lo, welch_hi), (pair_lo, pair_hi), corr


def pairs1302():
    r = eb_run()
    f = Fig("pairs1302", "The two arms as clouds of runs (left: a ring per seed, a line joining one seed's two runs), "
                         "and their difference (right): Welch's interval, which treats the clouds as independent, "
                         "against the interval of the seed-by-seed differences (dots)", 408)
    for row, (label, (one, four), part) in enumerate((("the page's 3 seeds", arms_page(), 2),
                                                      ("the recorded 10 seeds", arms_recorded(), 6))):
        (wl, wh), (pl, ph), corr = diff_parts(r.out, part)
        diffs = [b - a for a, b in zip(one, four)]
        same(f"{label}: correlation", f"{corr:+.2f}",
             f"{sum((a - mean(one)) * (b - mean(four)) for a, b in zip(one, four)) / (len(one) - 1) / sd(one) / sd(four):+.2f}")
        y0 = 52 + row * 192
        f.text(16, y0 - 30, label, "t", 12, weight=700)
        ax = figart.Axes(f, 60, y0, 170, 120, (-0.6, 1.6), (3.39, 3.45), False, False)
        ax.draw(yticks=[3.39, 3.41, 3.43, 3.45], xticks=[], ylabel="bits per character")
        for a, b in zip(one, four):
            f.line(ax.px(0), ax.py(a), ax.px(1), ax.py(b), "m")
        for k, xs in enumerate((one, four)):
            for v in xs:
                f.circle(ax.px(k), ax.py(v), 3, "s f" if k == 0 else "a f")
            f.text(ax.px(k), ax.y + ax.h + 15, "1 head" if k == 0 else "4 heads", "t" if k == 0 else "ta", 11,
                   "middle", 600)
        f.text(ax.x + ax.w + 8, ax.y + 12, f"correlation", "tm", 10)
        f.text(ax.x + ax.w + 8, ax.y + 26, f"{corr:+.2f}", "t", 11, weight=700, mono=True)
        bx = figart.Axes(f, 330, y0, 290, 120, (-0.07, 0.035), (0, 3), False, False)
        bx.draw(xticks=[-0.06, -0.04, -0.02, 0, 0.02], yticks=[], grid=False, xfmt=lambda v: f"{v:+.2f}" if v else "0",
                xlabel="4 heads minus 1 head, bits" if row == 1 else "")
        f.line(bx.px(0), bx.y, bx.px(0), bx.y + bx.h, "s")
        for k, (lo, hi, name, cls) in enumerate(((wl, wh, "Welch", "m"), (pl, ph, "pairs", "a"))):
            Y = bx.py(2.2 - k * 1.2)
            f.line(bx.px(lo), Y, bx.px(hi), Y, cls)
            f.line(bx.px(lo), Y - 4, bx.px(lo), Y + 4, cls)
            f.line(bx.px(hi), Y - 4, bx.px(hi), Y + 4, cls)
            f.text(bx.px(lo) - 6, Y + 4, name, TEXT[cls], 10.5, "end", 600)
            f.text(bx.px(hi) + 6, Y + 4, f"{hi - lo:.4f} wide", TEXT[cls], 10, weight=600)
            if cls == "a":
                for d in diffs:
                    f.circle(bx.px(d), Y + 14, 2.6, "a fa")
    return f


def noise1302():
    r = eb_run()
    one, four = arms_page()
    rone, rfour = arms_recorded()
    m = find(r.out, r"moves by sd ([\d.]+) \(1 head\) and ([\d.]+) \(4 heads\); the test text's own sampling error, "
                    r"([\d.]+) \(batches of 64")
    same("the seeds' sds", (f"{sd(one):.4f}", f"{sd(four):.4f}"), m.groups()[:2])
    text_one = float(m.group(3))
    rows = re.findall(r"^ +(1 head|4 heads|4 minus 1)((?: +[\d.]+){5})$", r.out, re.M)
    table = {name: [float(v) for v in vals.split()] for name, vals in rows[:3]}
    pair_text = float(find(r.out, r"For the difference on the same text it is ([\d.]+), against the spread of the "
                                  r"seeds' differences, ([\d.]+)").group(1))
    same("the difference's text error", f"{table['4 minus 1'][3]:.4f}", f"{pair_text:.4f}")
    rd = [b - a for a, b in zip(rone, rfour)]
    d3 = [b - a for a, b in zip(one, four)]
    f = Fig("noise1302", "Two kinds of noise: how far a score moves from seed to seed (the sd over the recorded 10 "
                         "seeds, a ring for the page's 3), and the test text's own sampling error (the standard error "
                         "over its positions, seed 0's models), for one model's score and for the difference", 300)
    groups = [("1 head", sd(rone), sd(one), table["1 head"][3]), ("4 heads", sd(rfour), sd(four), table["4 heads"][3]),
              ("4 heads minus 1", sd(rd), sd(d3), table["4 minus 1"][3])]
    ax = figart.Axes(f, 70, 40, 540, 200, (-0.5, 2.5), (0, 0.018), False, False)
    ax.draw(xticks=[], yticks=[0, 0.005, 0.01, 0.015], ylabel="bits per character")
    for i, (name, s10, s3, tx) in enumerate(groups):
        X = ax.px(i)
        for k, (v, cls) in enumerate(((s10, "s fs"), (tx, "a af"))):
            bx = X - 44 + k * 46
            f.rect(bx, ax.py(v), 40, ax.py(0) - ax.py(v), cls, 1)
            f.text(bx + 20, ax.py(v) - 6, f"{v:.4f}", "t" if k == 0 else "ta", 10, "middle", mono=True)
        f.circle(X - 24, ax.py(s3), 3.5, "s f")
        f.text(X, ax.y + ax.h + 16, name, "t", 11.5, "middle", 600)
        f.text(X, ax.y + ax.h + 30, "one model's score" if i < 2 else "the comparison", "tm", 10.5, "middle")
    f.rect(70, 280, 12, 10, "s fs", 1)
    f.text(88, 289, "over seeds", "t", 10.5)
    f.rect(170, 280, 12, 10, "a af", 1)
    f.text(188, 289, "over the test text", "ta", 10.5)
    f.circle(330, 285, 3.5, "s f")
    f.text(338, 289, "over seeds, the page's 3", "t", 10.5)
    return f


def batches1302():
    r = eb_run()
    rows = re.findall(r"^ +(1 head|4 heads|4 minus 1)((?: +[\d.]+){5})$", r.out, re.M)
    table = {name: [float(v) for v in vals.split()] for name, vals in rows[:3]}
    sizes = [int(v) for v in find(r.out, r"windows a batch((?: +\d+){5})").group(1).split()]
    f = Fig("batches1302", "The standard error of one model's score over the test text, its positions taken in "
                           "batches of consecutive windows: it grows while the batches are still shorter than a "
                           "stretch that moves together, then the batches run out", 270)
    series = [figart.Series("1 head", sizes, table["1 head"], "s"),
              figart.Series("4 heads", sizes, table["4 heads"], "s", True),
              figart.Series("4 heads minus 1", sizes, table["4 minus 1"], "a")]
    ax = figart.plot(f, (8, 6, 624, 236), series, xlabel="windows a batch (17 positions a window; log scale)",
                     ylabel="standard error, bits", logx=True, ylim=(0, 0.016), xticks=sizes,
                     yticks=[0, 0.004, 0.008, 0.012, 0.016], legend="right", xfmt=lambda v: f"{v:g}")
    ax.vline(64, None)
    ax.note(64, 0.0155, "taken: 64 windows", "tm", 10.5, dx=5)
    n_b = 55754 // (256 * 17)
    ax.note(256, table["1 head"][4], f"{n_b} batches", "tm", 10, "end", dx=-6, dy=16)
    f.text(16, 262, f"With 1 window a batch the error is the plain standard error, {table['1 head'][0]:.4f}; batches "
                    f"of 64 give {table['1 head'][3]:.4f}, {table['1 head'][3] / table['1 head'][0]:.1f} times it.",
           "tm", 10.5)
    return f


SEEDS_CODE = """
import json, lab
sizes = [round(0.005 + 0.001 * i, 3) for i in range(56)]
out = {{}}
for key, (arm, pair) in {spreads}.items():
    out[key] = {{"independent": [lab.seeds_needed(s, arm) for s in sizes],
                 "paired": [lab.seeds_needed(s, pair, paired=True) for s in sizes]}}
print(json.dumps({{"sizes": sizes, "n": out}}))
"""


def seeds1302():
    r = eb_run()
    one, four = arms_page()
    rone, rfour = arms_recorded()
    spreads = {"3": (math.sqrt((sd(one) ** 2 + sd(four) ** 2) / 2), sd([b - a for a, b in zip(one, four)])),
               "10": (math.sqrt((sd(rone) ** 2 + sd(rfour) ** 2) / 2), sd([b - a for a, b in zip(rone, rfour)]))}
    d = in_project("13.02", SEEDS_CODE.format(spreads=json.dumps(spreads)))
    sizes = d["sizes"]
    printed = re.findall(r"^ +(0\.\d{3}) +(\d+) +(\d+)$", r.out, re.M)
    for size, ind, par in printed:
        i = sizes.index(float(size))
        same(f"seeds for {size}", (d["n"]["3"]["independent"][i], d["n"]["3"]["paired"][i]), (int(ind), int(par)))
    rec_n = int(find(r.out, r"seeds_needed for ([\d.]+) at the pairs' sd [\d.]+, four times in five: (\d+)").group(2))
    i = sizes.index(0.025)
    same("seeds for 0.025 at the recorded spread", d["n"]["10"]["paired"][i], rec_n)
    f = Fig("seeds1302", "Seeds a side for a true difference to come out with its 95% interval clear of 0 four times in "
                         "five, against the size of the difference: two independent sets of runs, and pairs, at the "
                         "spreads the page's 3 seeds measured and the recorded 10", 310)
    series = [figart.Series("independent, 3 seeds' spread", sizes, d["n"]["3"]["independent"], "s", True),
              figart.Series("independent, 10 seeds' spread", sizes, d["n"]["10"]["independent"], "s"),
              figart.Series("paired, 3 seeds' spread", sizes, d["n"]["3"]["paired"], "a", True),
              figart.Series("paired, 10 seeds' spread", sizes, d["n"]["10"]["paired"], "a")]
    ax = figart.plot(f, (8, 6, 624, 270), series, xlabel="the difference to find, bits per character", ylabel="seeds a side",
                     logy=True, ylim=(2, 120), xlim=(0.005, 0.06), xticks=[0.01, 0.02, 0.03, 0.04, 0.05, 0.06],
                     yticks=[2, 3, 5, 10, 20, 50, 100], legend="right", xfmt=lambda v: f"{v:g}")
    ax.vline(0.025, None)
    ax.note(0.025, 90, "measured: 0.025", "tm", 10.5, dx=5)
    ax.dot(0.025, d["n"]["10"]["paired"][i], "a fa", 4.5)
    ax.note(0.025, d["n"]["10"]["paired"][i], f"{d['n']['10']['paired'][i]} paired", "ta", 10.5, dx=8, dy=-14,
            weight=700)
    f.text(16, 302, "The steps are whole seeds. Pairs need fewer wherever the two arms of one seed move together.",
           "tm", 10.5)
    return f


# ================================================================== 13.03

def fooled_run():
    return figart.experiment("fooled", at="13.03")


def halves1303():
    r = fooled_run()
    runs = [figart.summary(d) for d in figart.seed_dirs(os.path.join(r.runs, "runs"))]
    a, b = [100 * s["error_a"] for s in runs], [100 * s["error_b"] for s in runs]
    same("A's mean", f"{mean(a):.3g}", find(r.out, r"^   A: (\S+) \+- ").group(1))
    same("B's mean", f"{mean(b):.3g}", find(r.out, r"^   B: (\S+) \+- ").group(1))
    f = Fig("halves1303", "The 32 runs that differ only by seed, each scored on half A and half B of MNIST's test "
                          "images (drawn at random before any run): the one chosen by its score on A, and where it "
                          "lands on B", 330)
    ax = figart.Axes(f, 70, 30, 300, 250, (5.3, 8.1), (5.3, 8.1), False, False)
    ax.draw(xlabel="test error on half A, % (chosen on)", ylabel="on half B, % (held back)",
            xticks=[5.5, 6, 6.5, 7, 7.5, 8], yticks=[5.5, 6, 6.5, 7, 7.5, 8])
    f.line(ax.px(5.3), ax.py(5.3), ax.px(8.1), ax.py(8.1), "m", dash=True)
    ax.note(7.7, 7.75, "A = B", "tm", 10, dx=-30, dy=-2)
    best = min(range(len(a)), key=lambda i: a[i])
    for i, (x, y) in enumerate(zip(a, b)):
        if i != best:
            ax.dot(x, y, "s f", 3.2)
    ax.dot(a[best], b[best], "a fa", 5)
    f.line(ax.px(a[best]) + 6, ax.py(b[best]), ax.px(6.95) - 4, ax.py(5.68), "a")
    ax.note(6.95, 5.68, f"the best on A: seed {best}", "ta", 10.5, weight=700)
    ax.note(6.95, 5.68, f"{a[best]:.2f} on A, {b[best]:.2f} on B", "ta", 10.5, dy=14)
    f.line(ax.px(mean(a)), ax.y, ax.px(mean(a)), ax.y + ax.h, "s", dash=True)
    f.line(ax.x, ax.py(mean(b)), ax.x + ax.w, ax.py(mean(b)), "s", dash=True)
    x = 400
    f.text(x, 50, "the 32 runs", "t", 12, weight=700)
    f.text(x, 72, f"on A: {mean(a):.2f} +- {sd(a):.2f}", "t", 10.5, mono=True)
    f.text(x, 88, f"on B: {mean(b):.2f} +- {sd(b):.2f}", "t", 10.5, mono=True)
    f.text(x, 104, "(dashed: the means)", "tm", 10.5)
    f.text(x, 132, "B is easier for every run alike,", "t", 10.5)
    f.text(x, 146, "by chance; and a run good on A", "t", 10.5)
    f.text(x, 160, "tends to be good on B: the runs", "t", 10.5)
    f.text(x, 174, "really differ.", "t", 10.5)
    luck = float(find(r.out, r"The rest, ([\d.]+) \(sd").group(1))
    f.text(x, 202, f"Of A's variance, {sd(a) ** 2:.4f},", "tm", 10.5)
    f.text(x, 216, f"{luck:.4f} is the luck of A's", "tm", 10.5)
    f.text(x, 230, "own 5,000 images.", "tm", 10.5)
    return f


def gain1303():
    r = fooled_run()
    rows = figart.summary(os.path.join(r.runs, "chosen", "seed0"))["rows"]
    printed = re.findall(r"^ +(\d+)" + r" +([\d.-]+)" * 7 + "$", r.out, re.M)
    for row, p in zip(rows, printed):
        same(f"k = {row['k']}", [f"{row[k]:.3f}" for k in ("seen", "predicted_gain", "real")], [p[3], p[4], p[5]])
    ks = [row["k"] for row in rows]
    f = Fig("gain1303", "The gain from choosing: how far the best of k runs, chosen by half A, is below the average run, "
                        "on A where it was chosen and on B where it was not (dots); dashed, what the runs' spread "
                        "predicts for each", 300)
    series = [figart.Series("gain on A, where chosen", ks, [row["seen"] for row in rows], "a"),
              figart.Series("A, predicted", ks, [row["predicted_gain"] for row in rows], "a", True),
              figart.Series("gain on B, held back", ks, [row["real"] for row in rows], "s"),
              figart.Series("B, predicted", ks, [row["predicted_gain"] - row["predicted_lost"] for row in rows], "s",
                            True)]
    ax = figart.plot(f, (8, 6, 624, 262), series, xlabel="runs chosen among (k; log scale)",
                     ylabel="points of error below the average run", logx=True, xticks=ks, ylim=(0, 1.2),
                     yticks=[0, 0.25, 0.5, 0.75, 1.0], legend="right", xfmt=lambda v: f"{v:g}")
    for row in rows:
        if row["k"] > 1:
            ax.dot(row["k"], row["seen"], "a fa", 3.2)
            ax.dot(row["k"], row["real"], "s f", 3.2)
    last = rows[-1]
    X = ax.px(last["k"]) - 8
    f.line(X, ax.py(last["seen"]), X, ax.py(last["real"]), "m", start=True, arrow=True)
    ax.note(last["k"], 0.85, f"{last['seen'] - last['real']:.2f}: luck", "t", 10.5, "end", dx=-14, weight=600)
    f.text(16, 292, f"The best of {last['k']} looks {last['seen']:.2f} points better than the average run where it was "
                    f"chosen, and is {last['real']:.2f} better where it was not.", "tm", 10.5)
    return f


TWINS_CODE = """
import json
import numpy as np
from data import cifar, fetch, mnist
from experiments.fooled import raw, shrink, two_nearest
out = {}
for name, pool in (("cifar10", 4), ("mnist", 1)):
    (x, y), (tx, ty) = raw(name)
    nearest, d1, d2 = two_nearest(shrink(x, pool), shrink(tx, pool))
    ratio = d1 / d2
    out[name] = {"ratio": [round(float(v), 5) for v in ratio], "twins": int((d1 < 0.5 * d2).sum())}
    if name == "cifar10":
        picks = []
        for want in (0.0, 0.1, 0.25, 0.4, 0.49, 0.6):
            t = int(np.argmin(np.abs(ratio - want)))
            gray = lambda im: (im.astype(np.float64).mean(0) / 255).round(3).tolist()
            picks.append({"test": t, "train": int(nearest[t]), "ratio": float(ratio[t]), "label": cifar.CLASSES[int(ty[t])],
                          "its": cifar.CLASSES[int(y[nearest[t]])], "a": gray(tx[t]), "b": gray(x[nearest[t]])})
        out["picks"] = picks
print(json.dumps(out))
"""


def twins_data():
    d = in_project("13.03", TWINS_CODE)
    r = fooled_run()
    for name in ("mnist", "cifar10"):
        same(f"{name}'s twins", d[name]["twins"], int(find(r.out, rf"^   {name}: .* (\d+) with a twin").group(1)))
    return d


def picture(f, x, y, values, cell):
    """A grey photograph as a grid: the foreground at the opacity of its darkness, so it reads as a photograph on
    a light page and as its negative on a dark one (a figure has only the theme's colours); squares of equal
    opacity in a row are one path."""
    paths = {}
    for i, row in enumerate(values):
        j = 0
        while j < len(row):
            op = round(1 - row[j], 1)
            k = j + 1
            while k < len(row) and round(1 - row[k], 1) == op:
                k += 1
            if op >= 0.05:
                paths.setdefault(op, []).append(f"M{x + j * cell:.1f} {y + i * cell:.1f}h{(k - j) * cell:g}v{cell:g}"
                                                f"h{-(k - j) * cell:g}z")
            j = k
    for op, parts in sorted(paths.items()):
        f.add(f'<path class="t" d="{"".join(parts)}" fill-opacity="{op}"/>')
    f.rect(x, y, len(values[0]) * cell, len(values) * cell, "m", 0)


def twins1303():
    d = twins_data()
    picks = d["picks"]
    f = Fig("twins1303", "CIFAR-10 test images (left of each pair) and their nearest training image (right), in grey, "
                         "by the ratio of the nearest's distance to the second nearest's: under 0.5 the rule calls it "
                         "a twin. In the dark theme the photographs show as negatives", 356)
    cell, gap = 2.6, 6
    w = 32 * cell
    for n, p in enumerate(picks):
        col, row = n % 3, n // 3
        x = 16 + col * 210
        y = 34 + row * 160
        picture(f, x, y, p["a"], cell)
        picture(f, x + w + gap, y, p["b"], cell)
        twin = p["ratio"] < 0.5
        cls = "ta" if twin else "tm"
        f.text(x, y - 8, f"ratio {p['ratio']:.3f}: {'a twin' if twin else 'not a twin'}", cls, 11, weight=700)
        f.text(x, y + w + 15, f"test {p['test']}, {p['label']}", "t", 10)
        f.text(x, y + w + 29, f"training {p['train']}, {p['its']}", "tm", 10)
    f.text(16, 348, "The ratio, not the distance: a twin is a training image far nearer than every other one.", "tm",
           10.5)
    return f


def ratio1303():
    d = twins_data()
    f = Fig("ratio1303", "Every test image's ratio, the distance to its nearest training image over the distance to the "
                         "second nearest, in bins of 0.025, on a log scale of images: the rule's line at 0.5", 312)
    bins = 40
    for p, (name, title) in enumerate((("cifar10", "CIFAR-10, shrunk to 8 x 8"), ("mnist", "MNIST, at full size"))):
        counts = [0] * bins
        for v in d[name]["ratio"]:
            counts[min(bins - 1, int(v * bins))] += 1
        x0 = 60 + p * 300
        ax = figart.Axes(f, x0, 52, 250, 200, (0, 1), (0.8, 3000), False, True)
        ax.draw(xlabel="nearest / second nearest", ylabel="test images" if p == 0 else "", xticks=[0, 0.25, 0.5, 0.75, 1],
                yticks=[1, 10, 100, 1000], xfmt=lambda v: f"{v:g}")
        f.text(x0, 20, f"{title}: {d[name]['twins']} twins", "t", 12, weight=700)
        for i, c in enumerate(counts):
            if c:
                lo, hi = i / bins, (i + 1) / bins
                cls = "a af" if hi <= 0.5 else "s fs"
                f.rect(ax.px(lo), ax.py(c), ax.px(hi) - ax.px(lo) - 0.5, ax.py(0.8) - ax.py(c), cls, 0)
        ax.vline(0.5, None, "a")
        ax.note(0.5, 2000, "the rule: 0.5", "ta", 10.5, "end", dx=-5)
    f.text(16, 304, "Most images' nearest is hardly nearer than the next: ratios near 1. A copy, shifted or re-coloured, "
                    "stands far apart.", "tm", 10.5)
    return f


def accuracy1303():
    r = fooled_run()
    found = re.findall(r"right on ([\d.]+)% of those with a twin, ([\d.]+)% of the rest", r.out)
    names = [m.group(1) for m in re.finditer(r"^   (mnist|cifar10): ", r.out, re.M)]
    mnist_knn, mnist_runs, cifar_knn = (tuple(float(v) for v in x) for x in found)
    same("order", names, ["mnist", "cifar10"])
    counts = {n: int(find(r.out, rf"^   {n}: .* (\d+) with a twin").group(1)) for n in names}
    groups = [("CIFAR-10", "the nearest image's label", cifar_knn, counts["cifar10"]),
              ("MNIST", "the nearest image's label", mnist_knn, counts["mnist"]),
              ("MNIST", "part 1's 32 networks", mnist_runs, counts["mnist"])]
    f = Fig("accuracy1303", "Accuracy on the test images that have a twin in training and on the rest: a classifier "
                            "that only remembers (the nearest training image's label), and on MNIST also part 1's "
                            "networks", 276)
    ax = figart.Axes(f, 200, 30, 300, 180, (0, 100), (-0.5, 2.5), False, False)
    ax.draw(xlabel="right, %", xticks=[0, 20, 40, 60, 80, 100], yticks=[], grid=True)
    for i, (data, who, (twin, rest), n) in enumerate(groups):
        Y = ax.y + 30 + i * 60
        f.text(ax.x - 10, Y, data, "t", 11.5, "end", 700)
        f.text(ax.x - 10, Y + 14, who, "tm", 10.5, "end")
        for k, (v, cls, lab) in enumerate(((twin, "a af", f"with a twin ({n})"), (rest, "s fs", "the rest"))):
            y = Y - 10 + k * 17
            f.rect(ax.x, y, ax.px(v) - ax.x, 13, cls, 1)
            f.text(ax.px(v) + 5, y + 10.5, f"{v:.1f}  {lab}", "ta" if k == 0 else "t", 10, mono=False)
    cifar_pts = float(find(r.out, r"cifar10: .*\n.* overall [\d.]+%, of which ([\d.]+) points are the twins'").group(1))
    f.text(16, 266, f"CIFAR-10's twins lift the remembering classifier's score by {cifar_pts:.2f} points; MNIST's by "
                    f"0.01.", "tm", 10.5)
    return f


GRAMS_CODE = """
import json
from data import shakespeare
from experiments.fooled import shared_grams
tr, te = shakespeare.split("train"), shakespeare.split("test")
ks = [1, 2, 3, 4, 5, 6, 8, 10, 12, 14, 16, 20, 24, 28, 32]
print(json.dumps({"k": ks, "shared": [shared_grams(tr, te, k) for k in ks]}))
"""


def grams1303():
    r = fooled_run()
    d = in_project("13.03", GRAMS_CODE)
    for k, v in re.findall(r"k = (\d+): ([\d.]+)%", r.out):
        same(f"shared runs of {k}", f"{100 * d['shared'][d['k'].index(int(k))]:.2f}", v)
    window = float(find(r.out, r"drawn for testing: ([\d.]+)% of a test").group(1))
    f = Fig("grams1303", "Of the test text's runs of k characters, the share found somewhere in the training text, "
                         "Tiny Shakespeare split by position; beside it, the same text cut into overlapping windows and "
                         "a tenth drawn at random for testing", 290)
    series = [figart.Series("split by position (the track's)", d["k"], [100 * v for v in d["shared"]], "a")]
    ax = figart.plot(f, (8, 6, 624, 250), series, xlabel="k, characters in a run", ylabel="share in training, %",
                     ylim=(0, 100), xlim=(1, 32), xticks=[1, 4, 8, 12, 16, 20, 24, 28, 32],
                     yticks=[0, 25, 50, 75, 100], legend=None)
    for k, v in zip(d["k"], d["shared"]):
        ax.dot(k, 100 * v, "a fa", 3)
    ax.hline(window, f"overlapping windows drawn at random: {window:.1f}% of a test window's characters seen", "s",
             side="right")
    ax.note(16, 100 * d["shared"][d["k"].index(16)], f"{100 * d['shared'][d['k'].index(16)]:.2f}% at 16", "ta", 10.5,
            dx=8, dy=-6)
    ax.note(32, 0, "0.00% at 32", "ta", 10.5, "end", dx=-4, dy=-8)
    f.text(16, 282, "By position, the test text is The Tempest; no 32 characters of it are anywhere in the training "
                    "plays.", "tm", 10.5)
    return f


# ================================================================== 13.04

def scaling_rows():
    d = os.path.join(REC, "scaling")
    rows = []
    for w in sorted(int(n[5:]) for n in os.listdir(d) if n.startswith("width")):
        for s in figart.seed_dirs(os.path.join(d, f"width{w}")):
            x = figart.summary(s)
            rows.append(dict(width=w, weights=x["weights"], all_weights=x["all_weights"], bits=x["bits_per_token"],
                             seed=x["seed"], run=s))
    return rows


FIT_CODE = """
import json, lab
from experiments.scaling import predict
rows = {rows}
out = {{}}
for by in ("weights", "all_weights"):
    p = predict(rows, 256, by)
    out[by] = {{"alpha": p["law"]["alpha"], "a": p["law"]["a"], "se": p["law"]["alpha_se"], "predicted": p["predicted"],
               "low": p["low"], "high": p["high"], "got": p["got"], "inside": p["inside"], "n": p["n"]}}
print(json.dumps(out))
"""


def fits():
    rows = scaling_rows()
    clean = [{k: v for k, v in r.items() if k != "run"} for r in rows]
    got = in_project("13.04", FIT_CODE.format(rows=json.dumps(clean)))
    rec = figart.summary(os.path.join(REC, "scaling", "fit", "seed0"))
    for by in ("weights", "all_weights"):
        same(f"the fit, {by}", [f"{got[by][k]:.6g}" for k in ("alpha", "predicted", "low", "high")],
             [f"{v:.6g}" for v in (rec[by]["law"]["alpha"], rec[by]["predicted"], rec[by]["low"], rec[by]["high"])])
    return rows, got


def fit1304():
    rows, got = fits()
    f = Fig("fit1304", "The recorded run on log-log axes: bits per token on held-out stories against the weights, each "
                       "run a dot; the power law through widths 32 to 128, its 95% interval for width 256 (made before "
                       "256 was trained) and width 256's two runs; counting the weights two ways", 330)
    for p, (by, title) in enumerate((("weights", "embeddings left out, as the paper counts"),
                                     ("all_weights", "every weight counted"))):
        g = got[by]
        x0 = 58 + p * 316
        ax = figart.Axes(f, x0, 44, 250, 210, (3e4, 7e6), (3.6, 6.2), True, True)
        ax.draw(xlabel="weights counted (N; log scale)", ylabel="bits per token" if p == 0 else "",
                xticks=[1e5, 1e6], yticks=[3.75, 4, 4.5, 5, 5.5, 6],
                xfmt=lambda v: {1e5: "100,000", 1e6: "1,000,000"}[v], yfmt=lambda v: f"{v:g}")
        f.text(x0, 24, title, "t", 12, weight=700)
        lo, hi = math.log(min(r[by] for r in rows) * 0.8), math.log(g["n"] * 1.6)
        xs = [math.exp(lo + (hi - lo) * k / 60) for k in range(61)]
        ax.curve(xs, [g["a"] * x ** -g["alpha"] for x in xs], "s", dash=True, width=1.3)
        for r in rows:
            ax.dot(r[by], r["bits"], "a fa" if r["width"] == 256 else "s f", 4 if r["width"] == 256 else 3)
        X = ax.px(g["n"]) - 12
        f.line(X, ax.py(g["low"]), X, ax.py(g["high"]), "m")
        f.line(X - 4, ax.py(g["low"]), X + 4, ax.py(g["low"]), "m")
        f.line(X - 4, ax.py(g["high"]), X + 4, ax.py(g["high"]), "m")
        f.circle(X, ax.py(g["predicted"]), 4, "s f")
        inside = "inside" if g["inside"] else "outside"
        ax.note(3.2e4, 4.05, f"alpha = {g['alpha']:.4f}", "t", 10.5, weight=600)
        ax.note(3.2e4, 3.88, f"predicted {g['predicted']:.3f}", "t", 10.5)
        ax.note(3.2e4, 3.88, f"({g['low']:.3f} to {g['high']:.3f})", "tm", 10.5, dy=14)
        ax.note(3.2e4, 3.88, f"trained {g['got']:.3f}: {inside}, {100 * (g['got'] / g['predicted'] - 1):+.1f}%",
                "ta", 10.5, dy=28, weight=700)
    f.text(16, 312, "Ring and bar: the prediction for the mean of 2 runs, and its interval, just left of width 256; "
                    "accent dots: 256 as trained.", "tm", 10.5)
    return f


def curves1304():
    d = os.path.join(REC, "scaling")
    cfg = figart.config(figart.seed_dirs(os.path.join(d, "width32"))[0])
    per = cfg["batch"] * cfg["context"]
    widths = sorted(int(n[5:]) for n in os.listdir(d) if n.startswith("width"))
    series = []
    for w in widths:
        xs, m, _, _ = figart.over_seeds(figart.seed_dirs(os.path.join(d, f"width{w}")), "held_bits")
        keep = [(x * per, v) for x, v in zip(xs, m) if x > 0]
        series.append(figart.Series(f"width {w}", [k[0] for k in keep], [k[1] for k in keep],
                                    "a" if w == max(widths) else ("s" if w == min(widths) else "m")))
    f = Fig("curves1304", "Every width's held-out bits over the recorded run (the mean of its seeds, 64 held-out "
                          "windows every 50 steps), against the tokens seen, both on log scales: every curve is still "
                          "falling when the run stops", 300)
    ax = figart.plot(f, (8, 6, 624, 268), series, xlabel="tokens seen (log scale)", ylabel="bits per token, held out",
                     logx=True, logy=True, ylim=(3.8, 8.5), yticks=[4, 5, 6, 7, 8], legend="end",
                     xfmt=lambda v: f"{v:,.0f}")
    del ax
    f.text(16, 292, f"No size was trained to convergence: each stopped at the same {cfg['steps'] * per:,} tokens, as "
                    "the design asked.", "tm", 10.5)
    return f


def weights1304():
    rows = scaling_rows()
    widths = sorted({r["width"] for r in rows})
    one = {w: next(r for r in rows if r["width"] == w) for w in widths}
    share = {w: 1 - one[w]["weights"] / one[w]["all_weights"] for w in widths}
    same("the embeddings' share", (f"{share[32]:.0%}", f"{share[256]:.0%}"), ("73%", "26%"))
    f = Fig("weights1304", "Each width's weights, the embeddings apart: the table of the vocabulary's 4096 tokens and "
                           "the positions', W numbers each, are most of a small model and a quarter of the largest",
            270)
    top = max(one[w]["all_weights"] for w in widths)
    x0, x1 = 100, 380
    f.text(x1 + 16, 24, "N + the embeddings: their share", "tm", 10.5)
    for i, w in enumerate(widths):
        y = 34 + i * 34
        n, a = one[w]["weights"], one[w]["all_weights"]
        f.text(x0 - 12, y + 15, f"width {w}", "t", 11.5, "end", 600)
        X = lambda v: x0 + v / top * (x1 - x0)  # noqa: E731
        f.rect(x0, y, X(n) - x0, 20, "a af", 1)
        f.rect(X(n), y, X(a) - X(n), 20, "m fs", 1)
        f.text(x1 + 16, y + 14, f"{n:,} + {a - n:,}: {share[w]:.0%}", "ta" if share[w] > 0.5 else "t", 10.5,
               weight=600 if share[w] > 0.5 else None, mono=True)
    f.rect(x0, 250, 12, 10, "a af", 1)
    f.text(x0 + 18, 259, "N, as the paper counts", "ta", 10.5)
    f.rect(x0 + 190, 250, 12, 10, "m fs", 1)
    f.text(x0 + 208, 259, "the embeddings: tokens and positions", "t", 10.5)
    return f


def local1304():
    rows, got = fits()
    widths = sorted({r["width"] for r in rows})
    m = {w: mean([r["bits"] for r in rows if r["width"] == w]) for w in widths}
    n = {w: next(r["weights"] for r in rows if r["width"] == w) for w in widths}
    pairs = list(zip(widths, widths[1:]))
    local = [-math.log(m[b] / m[a]) / math.log(n[b] / n[a]) for a, b in pairs]
    same("local exponents", [f"{v:.3f}" for v in local], ["0.092", "0.082", "0.106", "0.109", "0.089"])
    g = got["weights"]
    f = Fig("local1304", "The exponent between each pair of neighbouring widths (the slope of the line through their "
                         "means), beside the fit's, through widths 32 to 128, and the paper's for models trained to "
                         "convergence", 280)
    ax = figart.Axes(f, 70, 30, 400, 200, (-0.5, len(pairs) - 0.5), (0.06, 0.12), False, False)
    ax.draw(xticks=[], yticks=[0.06, 0.08, 0.10, 0.12], ylabel="alpha, between two widths")
    ax.band([-0.5, len(pairs) - 0.5], [g["alpha"] - g["se"]] * 2, [g["alpha"] + g["se"]] * 2, "fs")
    ax.hline(g["alpha"], None, "s", dash=False)
    ax.hline(0.076, None, "m")
    for i, ((a, b), v) in enumerate(zip(pairs, local)):
        ax.dot(i, v, "a fa" if b == max(widths) else "s f", 4.5)
        f.text(ax.px(i), ax.y + ax.h + 16, f"{a} to {b}", "ta" if b == max(widths) else "t", 10.5, "middle", 600)
        ax.note(i, v, f"{v:.3f}", "ta" if b == max(widths) else "t", 10, dx=8, dy=4)
    x = ax.x + ax.w + 14
    f.text(x, ax.py(g["alpha"]) + 4, f"the fit: {g['alpha']:.4f}", "t", 10.5, weight=600)
    f.text(x, ax.py(g["alpha"]) + 18, f"+- {g['se']:.4f}", "tm", 10.5)
    f.text(x, ax.py(0.076) + 4, "the paper: 0.076", "tm", 10.5)
    f.text(x, ax.py(0.076) + 18, "(to convergence)", "tm", 10.5)
    f.text(16, 272, "The last pair, 128 to 256, is the one the prediction crossed: a little flatter than the fit, "
                    "which is its 0.5%.", "tm", 10.5)
    return f


FIGS = [
    ("13.01-hurried", hurried1301),
    ("13.01-draws", draws1301),
    ("13.01-search", search1301),
    ("13.01-bestof", bestof1301),
    ("13.01-wider", wider1301),
    ("13.02-t", t1302),
    ("13.02-intervals", intervals1302),
    ("13.02-pairs", pairs1302),
    ("13.02-noise", noise1302),
    ("13.02-batches", batches1302),
    ("13.02-seeds", seeds1302),
    ("13.03-halves", halves1303),
    ("13.03-gain", gain1303),
    ("13.03-twins", twins1303),
    ("13.03-ratio", ratio1303),
    ("13.03-accuracy", accuracy1303),
    ("13.03-grams", grams1303),
    ("13.04-fit", fit1304),
    ("13.04-local", local1304),
    ("13.04-weights", weights1304),
    ("13.04-curves", curves1304),
]


def main():
    only = sys.argv[1:]
    for name, fn in FIGS:
        if only and not any(name.startswith(o) for o in only):
            continue
        print(write(MOD, name, fn()))


if __name__ == "__main__":
    main()
