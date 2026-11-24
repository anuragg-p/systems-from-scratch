"""Figures for research module 15, Your own result (lessons 15.01-15.03).

    RESEARCH_FIGS_CACHE=DIR python3 -B art/research/figs15.py [15.02 ...]
                                    all of them, or those whose name starts so

Every number comes from the recorded runs the pages read, or from the reference code (tracks/research):

  15.01  experiments/question.py (the predictions, their rules, what others published, 08.03's numbers);
         experiments/recorded/pilot/ (the recorded pilot: its gaps, and its output.txt for the budget);
         the other modules' recorded runs' output.txt (the minutes each took); lab's seeds_needed
  15.02  experiments/recorded/depth/ (the search, the pairs, the control); question.py's judge and rules
  15.03  experiments/recorded/paper/paper.txt (the paper as paper.py wrote it), the project's files on disk
         (their sizes), data/fetch.py's pinned downloads, and a rerun of a recorded config on short settings

PyTorch must be installed; nothing needs a download; nothing trains but 15.03's short rerun (seconds).
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

MOD = "15"
REC = os.path.join(figlib.TRACK, "experiments", "recorded")
sys.path.insert(0, figlib.TRACK)
import lab  # noqa: E402
from experiments import question as q  # noqa: E402


def recorded_seconds(name):
    """The seconds a recorded run took, from the last line its output.txt printed (minutes for 06.04's)."""
    with open(os.path.join(REC, name, "output.txt")) as f:
        text = f.read()
    m = re.findall(r"^([\d.]+) (s|minutes) of ", text, re.M)
    value, unit = m[-1]
    return float(value) * (60 if unit == "minutes" else 1)


def pilot():
    """The recorded pilot: {(depth, arm): [validation bits by seed]}, its settings, its budget line."""
    runs = q.read_runs(os.path.join(REC, "pilot"))
    cfg = lab.Config(next(iter(runs.values()))[0][0])
    bits = {(int(label[6:].split("-")[0]), label.split("-")[1]): [s["val_bits"] for _, s in seeds]
            for label, seeds in runs.items()}
    with open(os.path.join(REC, "pilot", "output.txt")) as f:
        text = f.read()
    minutes = float(re.search(r"about (\d+) minutes", text).group(1))
    pairs = int(re.search(r"^   (\d+) pairs \(13\.02", text, re.M).group(1))
    return bits, cfg, minutes, pairs


# ------------------------------------------------------------------ 15.01

def questions1501():
    """The track's results and the questions they leave, each with the minutes of the recorded run it extends."""
    _, _, minutes, _ = pilot()
    rows = [("08.03", "what positions are worth at other depths", "this module's pilot: its plan", minutes, "a"),
            ("14.04", "how the grokking delay grows with the start", "14.04's ablations, 18 runs",
             recorded_seconds("ablations") / 60, "s"),
            ("10.05", "SwiGLU's lead: the width or the steps?", "10.05's long run, which saw it",
             recorded_seconds("ablation") / 60, "s"),
            ("13.04", "does the exponent move with the steps?", "13.04's run, one budget of three",
             3 * recorded_seconds("scaling") / 60, "s"),
            ("09.04", "TinyStories' grammar, measured", "needs the paper's grader, GPT-4", None, "m")]
    f = Fig("questions1501", "The track's results and the questions they leave, each beside the minutes of the "
                             "recorded run it would extend, read from that run's output; the hour a recorded run "
                             "may take is the line", 300)
    x0, x1, top, rh = 300, 610, 46, 42
    scale = lambda m: x0 + (x1 - x0) * min(m, 180) / 180
    f.text(16, 22, "a question from the track's own results", "t", 11.5, weight=700)
    f.text(x0, 22, "minutes of CPU, from the recorded run it extends", "t", 11.5, weight=700)
    for t in (0, 60, 120, 180):
        X = scale(t)
        f.line(X, top - 8, X, top + len(rows) * rh - 6, "m", dash=t == 60)
        f.text(X, top + len(rows) * rh + 8, str(t), "tm", 10.5, "middle", mono=True)
    f.text(scale(60) + 4, top - 12, "the hour", "tm", 10.5)
    for k, (lid, question, run, m, style) in enumerate(rows):
        y = top + k * rh
        tcls = {"a": "ta", "s": "t", "m": "tm"}[style]
        f.text(16, y + 12, lid, "tm", 10.5, mono=True)
        f.text(58, y + 12, question, tcls, 11.5, weight=600 if style == "a" else None)
        f.text(58, y + 27, run, "tm", 10.5)
        if m is None:
            f.text(x0 + 4, y + 18, "not on a laptop, by the track's rules", "tm", 10.5)
            continue
        f.rect(x0, y + 4, scale(m) - x0, 18, "a af" if style == "a" else "s fs", 3)
        f.text(scale(m) + 6, y + 17, f"{m:.0f}", tcls, 10.5, mono=True, weight=600 if style == "a" else None)
    f.text(16, 292, "Read from experiments/recorded/*/output.txt; 13.04's is three budgets of its one recorded run.",
           "tm", 10.5)
    return f


def known1501():
    """Where each published comparison sits on the depth axis, and where this module's runs sit."""
    irie = [int(x) for x in re.search(r"(\d+), (\d+) and (\d+) layers", q.RELATED[0].found).groups()]
    haviv = [int(x) for x in re.search(r"(\d+) to (\d+) layers", q.RELATED[1].found).groups()]
    ours = [1, 2, 4, 6, 8]
    f = Fig("known1501", "Where each published comparison sits on the depth axis, and where this module's runs sit: "
                         "1 to 8 blocks, below every one of them", 250)
    ax = figart.Axes(f, 150, 40, 460, 150, (0.8, 60), (0, 4), True, False)
    ax.draw(xlabel="blocks (layers), log scale", xticks=[1, 2, 4, 8, 12, 24, 42], yticks=[], grid=False, frame=False)
    f.line(ax.x, ax.y + ax.h, ax.x + ax.w, ax.y + ax.h, "m")
    rows = [(3.3, "Irie et al. 2019", "word-level, LibriSpeech", irie, "s"),
            (2.3, "Haviv et al. 2022", "125M to 1.3B weights, the Pile", haviv, "s"),
            (1.3, "Kazemnejad et al. 2023", "a proof: layer 1 finds a position", [1, 2], "m"),
            (0.4, "this module", "64 wide, Tiny Shakespeare", ours, "a")]
    for y, who, what, xs, style in rows:
        tcls = {"a": "ta", "s": "t", "m": "tm"}[style]
        f.text(16, ax.py(y) - 1, who, tcls, 11, weight=700 if style == "a" else 600)
        f.text(16, ax.py(y) + 12, what, "tm", 10)
        if style == "m":
            f.line(ax.px(1), ax.py(y), ax.px(2), ax.py(y), "m", arrow=True)
            ax.note(1, y, "computes", "tm", 10, dy=-7)
            ax.note(2, y, "uses", "tm", 10, dx=6, dy=4)
            continue
        if len(xs) == 2 and style == "s" and xs == haviv:
            f.line(ax.px(xs[0]), ax.py(y), ax.px(xs[1]), ax.py(y), "s")
        for x in xs:
            ax.dot(x, y, "a fa" if style == "a" else "s f", 4)
    f.text(16, 238, "The published comparisons start at 12 layers; the proof needs a token that marks each input's start, "
                    "which our windows lack.", "tm", 10.5)
    return f


def predictions1501():
    def wrapped(s, width=455):
        lines, line = [], ""
        for word in s.split():
            if tw(line + " " + word, 11) > width and line:
                lines.append(line)
                line = word
            else:
                line = (line + " " + word).strip()
        return lines + [line]

    heights = [22 + 14 * len(wrapped(p.says)) for p in q.PREDICTIONS]
    f = Fig("predictions1501", "The seven predictions as experiments/question.py holds them, written before any run, "
                               "each with the rule that will decide it", 64 + sum(h + 6 for h in heights))
    f.text(16, 22, "PREDICTIONS, committed before the pilot ran", "t", 11.5, weight=700)
    f.text(624, 22, f"SMALLEST = {q.SMALLEST}: the smallest gap worth finding", "tm", 10.5, "end", mono=True)
    y = 34
    for k, (p, h) in enumerate(zip(q.PREDICTIONS, heights)):
        f.rect(12, y, 616, h, "s fs" if k % 2 else "s f", 5)
        f.text(22, y + 16, p.key, "ta", 10.5, mono=True, weight=700)
        lines = wrapped(p.says)
        for i, text in enumerate(lines):
            f.text(162, y + 16 + 14 * i, text, "t", 11)
        f.text(162, y + 16 + 14 * len(lines), q.rule_text(p.rule), "tm", 10.5)
        y += h + 6
    f.text(16, y + 16, "The gap: no positions minus learned, test bits per character, one seed's pair; positive when "
                       "positions help.", "tm", 10.5)
    return f


def pilot1501():
    bits, cfg, _, pairs = pilot()
    depths = cfg.depths
    gaps = {d: [a - b for a, b in zip(bits[d, "none"], bits[d, "learned"])] for d in depths}
    sds = {d: lab.sd(g) for d, g in gaps.items()}
    need = {d: max(3, lab.seeds_needed(q.SMALLEST, sds[d], q.LEVEL, q.POWER, paired=True)) for d in depths}
    assert need[min(depths)] == pairs or max(need.values()) == pairs, (need, pairs)
    f = Fig("pilot1501", "The recorded pilot: each pair's gap on the validation text at one block and at eight (dots), "
                         "and the pairs seeds_needed asks for against the spread of the gaps, with the two depths' "
                         "spreads marked", 290)
    groups = [(f"{d} block{'s' * (d > 1)}\nsd {sig(sds[d])}", gaps[d], "a" if d == min(depths) else "s")
              for d in depths]
    f.text(16, 18, f"the gap of each pair, {cfg.seeds} pairs, lr {cfg.lr:g}", "t", 11.5, weight=700)
    figart.seeds_chart(f, (10, 24, 220, 250), groups, ylabel="bits per character", ylim=(0, None))
    ax = figart.Axes(f, 320, 46, 290, 190, (0.0, 0.04), (0, 30), False, False)
    ax.draw(xlabel="sd of the pairs' gaps", ylabel="pairs needed", xticks=[0, 0.01, 0.02, 0.03, 0.04],
            yticks=[0, 10, 20, 30])
    f.text(320, 18, f"pairs for a gap of {q.SMALLEST}, four times in five", "t", 11.5, weight=700)
    xs = [0.001 * k for k in range(1, 41)]
    ax.curve(xs, [lab.seeds_needed(q.SMALLEST, x, q.LEVEL, q.POWER, paired=True) for x in xs], "s")
    for d in depths:
        style = "a" if need[d] == pairs else "m"
        ax.dot(sds[d], need[d], "a fa" if style == "a" else "s f", 4)
        ax.note(sds[d], need[d], f"{d} block{'s' * (d > 1)}: {need[d]}", "ta" if style == "a" else "tm",
                dx=-8, dy=-8, anchor="end")
    f.text(320, 282, f"The largest spread decides: {pairs} pairs at every depth.", "ta", 11, weight=600)
    return f


# ------------------------------------------------------------------ 15.02

def experiment():
    """The recorded experiment read back (question.results), with its test bits, gaps and verdicts."""
    found, runs, control, cfg = q.results(os.path.join(REC, "depth"))
    depths = sorted({d for d, _ in runs})
    test = {k: [s["test_bits"] for s in v] for k, v in runs.items()}
    gaps = q.gaps(test, depths)
    ctrl = {d: [s["test_bits"] for s in rows] for d, rows in control.items()}
    verdicts = {p.key: q.judge(p.rule, {d: g[0] for d, g in gaps.items()}, test, ctrl) for p in q.PREDICTIONS}
    return dict(found=found, runs=runs, control=ctrl, cfg=cfg, depths=depths, test=test, gaps=gaps,
                chosen=q.choose(found), verdicts=verdicts)


def followup():
    """The follow-up at 4 blocks with higher rates (experiments/recorded/followup/depth), read back; None if absent."""
    d = os.path.join(REC, "followup", "depth")
    if not os.path.isdir(d):
        return None
    found, runs, _, cfg = q.results(d)
    test = {k: [s["test_bits"] for s in v] for k, v in runs.items()}
    return dict(found=found, cfg=cfg, test=test, gaps=q.gaps(test, sorted({k for k, _ in runs})),
                chosen=q.choose(found))


def search1502():
    """Validation bits against the rate at every depth, both models, seed 0: the search, and each choice."""
    e = experiment()
    rates = sorted(e["cfg"].rates)
    f = Fig("search1502", "The search, seed 0: validation bits per character against the learning rate at every depth, "
                          "without positions (dashed) and with learned positions (solid), a dot at the rate each kept",
            250)
    lo = min(v for s in e["found"].values() for v in s.values())
    hi = max(v for s in e["found"].values() for v in s.values())
    n, x0, gap = len(e["depths"]), 58, 8
    w = (630 - x0 - gap * (n - 1)) / n
    for k, d in enumerate(e["depths"]):
        ax = figart.Axes(f, x0 + k * (w + gap), 40, w, 160, (rates[0] / 1.3, rates[-1] * 1.3), (lo - 0.02, hi + 0.02),
                         True, False)
        ax.draw(xticks=[], yticks=[3.2, 3.3, 3.4, 3.5] if k == 0 else [])
        for r, anchor in ((rates[0], "start"), (rates[-1], "end")):
            f.line(ax.px(r), ax.y + ax.h, ax.px(r), ax.y + ax.h + 4, "m")
            f.text(ax.px(r) + (-3 if anchor == "start" else 3), ax.y + ax.h + 16, f"{r:g}", "tm", 9.5, anchor, mono=True)
        f.text(ax.x + ax.w / 2, 32, f"{d} block{'s' * (d > 1)}", "t", 11.5, "middle", 700)
        for arm, style, dash in (("none", "s", True), ("learned", "a", False)):
            ys = [e["found"][d, arm][r] for r in rates]
            ax.curve(rates, ys, style, dash)
            r = e["chosen"][d, arm]
            ax.dot(r, e["found"][d, arm][r], "a fa" if style == "a" else "s f", 3.5)
    f.text(16, 32, "bits", "tm", 10.5)
    f.text(16, 232, f"Rates {', '.join(f'{r:g}' for r in rates)}; " +
           f"{sum(r == rates[-1] for r in e['chosen'].values())} of {len(e['chosen'])} choices are the largest rate tried.",
           "tm", 10.5)
    figart.legend(f, 430, 232, [("no positions", "s", True), ("learned", "a", False)], across=True)
    return f


def bits1502():
    e = experiment()
    f = Fig("bits1502", f"Test bits per character against blocks, {len(e['test'][1, 'none'])} pairs of seeds, each "
                        f"model at its chosen rate: the mean and the seeds' range; rings: 08.03's two runs at 4 blocks",
            300)
    series = []
    for arm, style, dash in (("none", "s", True), ("learned", "a", False)):
        means = [lab.mean(e["test"][d, arm]) for d in e["depths"]]
        series.append(figart.Series("no positions" if arm == "none" else "learned positions", e["depths"], means,
                                    style, dash, lo=[min(e["test"][d, arm]) for d in e["depths"]],
                                    hi=[max(e["test"][d, arm]) for d in e["depths"]]))
    ax = figart.plot(f, (10, 10, 620, 280), series, xlabel="blocks", ylabel="bits per character, test text",
                     xticks=e["depths"])
    ax.dot(4, q.BEFORE["none"], "s f", 4)
    ax.dot(4, q.BEFORE["learned"], "a f", 4)
    ax.note(4, q.BEFORE["none"], f"08.03: {q.BEFORE['none']}, {q.BEFORE['learned']} (lr {q.BEFORE['lr']:g})", "tm",
            dx=8, dy=-6)
    return f


def gap1502():
    e = experiment()
    f = Fig("gap1502", "The gap, no positions minus learned, against blocks: each pair (small dots), the mean, its "
                       "paired 95% interval (solid bar) and Welch's on the same runs (dashed, to its right); the ring: "
                       "08.03's 0.065", 300)
    ds = e["depths"]
    hi = max(max(g[0]) for g in e["gaps"].values())
    ax = figart.Axes(f, 70, 30, 540, 220, (0, ds[-1] + 1), (0, hi * 1.08), False, False)
    ax.draw(xlabel="blocks", ylabel="gap, bits per character", xticks=ds)
    ax.hline(q.SMALLEST, f"the smallest gap worth finding, {q.SMALLEST}")
    for d in ds:
        each, mean, paired, welch, _ = e["gaps"][d]
        for g in each:
            f.circle(ax.px(d) - 10, ax.py(g), 1.6, "m")
        f.line(ax.px(d), ax.py(paired[0]), ax.px(d), ax.py(paired[1]), "a")
        f.line(ax.px(d) + 9, ax.py(welch[0]), ax.px(d) + 9, ax.py(welch[1]), "s", dash=True)
        ax.dot(d, mean, "a fa", 4)
        ax.note(d, mean, f"{mean:.3f}", "ta", 10.5, dx=14, dy=4)
    ax.curve(ds, [e["gaps"][d][1] for d in ds], "a", width=1.25)
    ax.dot(4, q.BEFORE["gap"], "s f", 4.5)
    ax.note(4, q.BEFORE["gap"], f"08.03: {q.BEFORE['gap']}", "tm", 10.5, dx=10, dy=12)
    return f


def rate1502():
    """The gap on validation against the rate, seed 0, from the search: how much the rate decides it."""
    e = experiment()
    rates = sorted(e["cfg"].rates)
    f = Fig("rate1502", "From the search, seed 0: the gap on the validation text against the learning rate, one line "
                        "per depth; 08.03 ran at 0.003", 290)
    series = []
    for k, d in enumerate(e["depths"]):
        ys = [e["found"][d, "none"][r] - e["found"][d, "learned"][r] for r in rates]
        series.append(figart.Series(f"{d} block{'s' * (d > 1)}", rates, ys, "a" if d == 4 else ("s" if d == 1 else "m"),
                                    dash=False if d in (1, 4) else ("2 3" if d == 8 else True)))
    fu = followup()
    if fu:
        more = sorted(r for r in fu["cfg"].rates if r > rates[-1])
        xs = [rates[-1]] + more
        series.append(figart.Series("4 blocks, the follow-up", xs,
                                    [fu["found"][4, "none"][r] - fu["found"][4, "learned"][r] for r in xs], "a",
                                    dash=True))
    top = max(x for s in series for x in s.xs)
    ax = figart.plot(f, (10, 10, 620, 270), series, xlabel="learning rate (log scale)", ylabel="gap on validation",
                     logx=True, xlim=(rates[0] / 1.2, top * 1.2), xticks=sorted({x for s in series for x in s.xs}),
                     xfmt=lambda v: f"{v:g}", legend="right")
    ax.vline(0.003, "08.03's rate")
    ax.hline(0.0, None)
    return f


def verdicts1502():
    e = experiment()
    f = Fig("verdicts1502", "Each prediction, written before any run, beside its outcome by its own rule", 64 + 40 *
            len(q.PREDICTIONS))
    f.text(16, 22, "prediction, and its rule", "t", 11.5, weight=700)
    f.text(210, 22, "ours", "t", 11.5, weight=700)
    f.text(624, 22, "verdict", "t", 11.5, "end", 700)
    for k, p in enumerate(q.PREDICTIONS):
        y = 34 + k * 40
        v, ours = e["verdicts"][p.key]
        held = v == "held"
        f.rect(12, y, 616, 34, "s f" if held else "a af", 5)
        f.text(22, y + 14, p.key, "ta" if not held else "t", 10.5, mono=True, weight=700)
        f.text(22, y + 28, q.rule_text(p.rule), "tm", 10)
        if isinstance(ours, (list, tuple)):
            ours = ", ".join(f"{x:.3f}" for x in ours)
        else:
            ours = f"{ours:.3f}"
        f.text(210, y + 14, ours, "t", 10.5, mono=True)
        f.text(618, y + 14, v, "ta" if not held else "t", 11, "end", 700)
    held = sum(v[0] == "held" for v in e["verdicts"].values())
    f.text(16, 56 + 40 * len(q.PREDICTIONS), f"{held} of {len(q.PREDICTIONS)} held; the others are shaded.", "tm", 10.5)
    return f


# ------------------------------------------------------------------ 15.03

def paper_sections():
    """The paper as paper.py wrote it from the recorded runs: its numbered section headings, in order."""
    with open(os.path.join(REC, "paper", "paper.txt")) as f:
        text = f.read()
    return text, re.findall(r"^(\d)\. (.+)$", text, re.M)


def sources1503():
    _, sections = paper_sections()
    f = Fig("sources1503", "The paper, section by section, beside where each section's numbers come from: the recorded "
                           "runs' config.json, summary.json and output.txt, question.py, and the text's own bytes", 330)
    sources = [("config.json", "every setting of every run, its seed", "s"),
               ("summary.json", "every run's bits, its weights", "s"),
               ("output.txt", "what each run printed: its time", "s"),
               ("question.py", "predictions, rules, others' numbers", "a"),
               ("tinyshakespeare.txt", "its bytes: the size, the SHA-256", "m")]
    uses = {"The problem": [3], "What this paper shows": [1, 3], "Method": [0, 1, 2, 4], "Results": [0, 1],
            "The predictions, written before any run": [1, 3], "What was not expected": [0, 1, 3],
            "What others found": [3], "Limits": [0], "To make every number again": [0, 4]}
    f.text(16, 22, "paper.txt, as paper.py wrote it", "t", 11.5, weight=700)
    f.text(400, 22, "read from", "t", 11.5, weight=700)
    ys = {}
    f.label_box(16, 34, 250, 22, "Abstract (four sentences)", "s fs", "t", 10.5, False)
    for k, (num, title) in enumerate(sections):
        y = 62 + k * 26
        ys[title] = y + 11
        f.label_box(16, y, 250, 22, f"{num}. {title}", "s f", "t", 10.5, False)
    for k, (name, what, style) in enumerate(sources):
        y = 52 + k * 50
        f.label_box(400, y, 224, 38, name, "a af" if style == "a" else "s fs", "ta" if style == "a" else "t", 11, True,
                    weight=600, sub=what, subsize=9.5)
        for title, idx in uses.items():
            if k in idx and title in ys:
                f.line(268, ys[title], 398, y + 19, "m")
    f.text(16, 322, "Nothing is typed in: a number in the paper is read from one of these, or computed from them.", "tm",
           10.5)
    return f


def structure1503():
    _, sections = paper_sections()
    theirs = [("Title", "1000 readers"), ("Abstract", "4 sentences, 100 readers"), ("Introduction", "1 page, 100 readers"),
              ("The problem", "1 page, 10 readers"), ("My idea", "2 pages, 10 readers"),
              ("The details", "5 pages, 3 readers"), ("Related work", "1-2 pages, 10 readers"),
              ("Conclusions and further work", "0.5 pages")]
    ours = [("title", None), ("Abstract", None)] + [(f"{n}. {t}", None) for n, t in sections]
    match = {0: 0, 1: 1, 2: 3, 3: 2, 4: 4, 5: 5, 8: 6, 9: 7, 10: 7}
    f = Fig("structure1503", "Peyton Jones's structure, and the paper's sections against it: the same order, related "
                             "work late, and two sections of the track's own", 400)
    f.text(16, 22, "Peyton Jones's slides", "t", 11.5, weight=700)
    f.text(360, 22, "this module's paper", "t", 11.5, weight=700)
    ly = {}
    for k, (name, who) in enumerate(theirs):
        y = 34 + k * 40
        f.label_box(16, y, 230, 32, name, "s f", "t", 11, False, weight=600, sub=who, subsize=9.5)
        ly[k] = y + 16
    own = {"5. The predictions, written before any run", "6. What was not expected"}
    for k, (name, _) in enumerate(ours):
        y = 34 + k * 30
        mine = name in own
        f.label_box(360, y, 264, 24, name, "a af" if mine else "s fs", "ta" if mine else "t", 10.5, False,
                    weight=600 if mine else None)
        if k in match and not mine:
            f.line(248, ly[match[k]], 358, y + 12, "m")
    f.text(16, 390, "Shaded: the predictions beside their outcomes, and what was not expected, as modules 13 and 14 "
                    "taught; not on the slides.", "tm", 10.5)
    return f


def disk(path):
    total = 0
    for dirpath, _, files in os.walk(path):
        total += sum(os.path.getsize(os.path.join(dirpath, n)) for n in files)
    return total


def repo1503():
    """What the project ships, what it fetches by a pinned command, and what it never ships: sizes from disk and
    from data/fetch.py's pins."""
    sys.path.insert(0, figlib.TRACK)
    from data import fetch
    track = figlib.TRACK
    shipped = [("the code: every .py of the project",
                sum(disk(os.path.join(track, d)) for d in ("engine", "lab", "models", "tokens")) +
                sum(os.path.getsize(os.path.join(track, "data", n)) for n in os.listdir(os.path.join(track, "data"))
                    if n.endswith(".py")) +
                sum(os.path.getsize(os.path.join(track, "experiments", n))
                    for n in os.listdir(os.path.join(track, "experiments")) if n.endswith(".py"))),
               ("data/tinyshakespeare.txt, public domain", os.path.getsize(os.path.join(track, "data",
                                                                                         "tinyshakespeare.txt"))),
               ("experiments/recorded/: every recorded run", disk(os.path.join(track, "experiments", "recorded")))]
    fetched = [(name, sum(s for s, _ in d["files"].values()))
               for name, d in fetch.DATASETS.items()]
    f = Fig("repo1503", "What the track's project ships, what it fetches by a pinned command, and what it never ships, "
                        "with their sizes: from the files on disk and from data/fetch.py's pins", 300)
    f.text(16, 22, "in the repository", "t", 11.5, weight=700)
    for k, (name, size) in enumerate(shipped):
        f.label_box(16, 34 + k * 40, 300, 32, name, "s f", "t", 10, False, sub=mb(size), subsize=10)
    f.text(16, 170, "never in it: weights", "ta", 11.5, weight=700)
    f.label_box(16, 182, 300, 44, "a checkpoint is made again by its run's command", "a af", "ta", 10.5, False,
                sub="from its config.json and its seed", subsize=9.5)
    f.text(340, 22, "fetched once: python3 -m data.fetch <name>", "t", 11.5, weight=700)
    for k, (name, size) in enumerate(fetched):
        y = 34 + k * 34
        f.label_box(340, y, 284, 28, f"{name}: {mb(size)}", "s fs", "t", 10.5, True)
    f.text(340, 34 + len(fetched) * 34 + 14, "each file's size and SHA-256 pinned; its licence in NOTICE", "tm", 10.5)
    f.text(16, 290, "Sizes in MB (a million bytes); the downloads are the files kept, not the archives.", "tm", 10.5)
    return f


def mb(size):
    return f"{size / 1e6:.3g} MB" if size >= 1e5 else f"{size / 1e3:.3g} KB"


FIGURES = {"15.01-questions": questions1501, "15.01-known": known1501, "15.01-predictions": predictions1501,
           "15.01-pilot": pilot1501, "15.02-search": search1502, "15.02-bits": bits1502, "15.02-gap": gap1502,
           "15.02-rate": rate1502, "15.02-verdicts": verdicts1502, "15.03-sources": sources1503,
           "15.03-structure": structure1503, "15.03-repo": repo1503}


def main():
    wanted = sys.argv[1:]
    for name, fn in FIGURES.items():
        if wanted and not any(name.startswith(w) for w in wanted):
            continue
        print(write(MOD, name, fn()))


if __name__ == "__main__":
    main()
