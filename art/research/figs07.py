"""Figures for research module 07, Language models, from counting to attention (lessons 07.01-07.04).

    RESEARCH_FIGS_CACHE=DIR python3 -B art/research/figs07.py [07.02 ...]
                                    all of them, or those whose name starts so (DIR keeps the runs)

Every bar, curve, cell and number comes from the reference code (tracks/research), run as the page
runs it, or from the recorded long run the page shows:

  07.01  python3 -m experiments.bigram (the page's run): the twelve pairs of its part 1, its ladder;
         the pair table, bigram.pair_counts of the project at 07.01 on the training text, and the
         pairs of the test text it never saw
  07.02  python3 -m experiments.nplm (the page's run, 3 seeds): counting's table and the network's
         rows; the recorded long run, experiments/recorded/nplm/ (its logs and summaries, as
         committed), and seed 0 of context 8's embeddings there for the similarities
  07.03  python3 -m experiments.rnn (the page's run, 3 seeds): what it uses, the recall task and the
         gradient's table; the stepped figure trains seed 0 of the page's text network in the
         project at 07.03 (experiments.rnn.train, the page's settings) and reads ROMEO's first line
         into it, a character at a time
  07.04  python3 -m experiments.attention (the page's run, 3 seeds): the accuracy against length,
         and seed 0's two examples (lengths 10 and 30) from its summary.json, the weights of every
         output step: the stepped figure and the two maps

PyTorch must be installed (07.02 on); nothing needs a download. The runs take about three minutes in
all on the machine in NOTES.md.
"""
import json
import math
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)                          # art/research/: figlib, figart
sys.path.insert(0, os.path.dirname(HERE))         # art/: steps.py, for the stepped figures
import figart  # noqa: E402
import figlib  # noqa: E402
import steps  # noqa: E402
from figlib import Fig, sig, tw, write  # noqa: E402

MOD = "07"


def in_project(at, code):
    """Run python code in the project as it stands at lesson `at`; the JSON it prints last."""
    d = figart.project(at)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=d)
    r = subprocess.run([sys.executable, "-B", "-c", code], cwd=d, env=env, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"python in the project at {at} failed:\n{r.stdout[-1500:]}{r.stderr[-1500:]}")
    return json.loads(r.stdout.strip().splitlines()[-1])


def shown(c):
    """A character as a figure writes it: the space as _, the newline as \\n."""
    return {" ": "_", "\n": "\\n"}.get(c, c)


# ------------------------------------------------------------------ 07.01

def bigram_run():
    return figart.experiment("bigram", at="07.01")


def twelve(out):
    """Part 1 of bigram's output: [(pair, count, of, p, bits)] and the mean it printed."""
    rows = []
    for line in out.splitlines():
        m = re.match(r"^   ('.*?'|\".*?\") +(\d+) +(\d+) +(\S+) +(\S+)$", line)
        if m:
            pair = eval(m.group(1))                # the repr the run printed: '\n' is a newline
            rows.append((pair, int(m.group(2)), int(m.group(3)), float(m.group(4)), float(m.group(5))))
    mean = figart.value(out, r"mean -log2 p over these \d+: (\S+) bits")
    if len(rows) != 12:
        raise SystemExit(f"bigram: expected 12 pairs in part 1, read {len(rows)}:\n{out}")
    return rows, mean


def ladder_of(out):
    """Part 3: {name: (test, training)} for the three rungs."""
    got = {}
    for name in ("every character equally likely", "single characters, by their counts", "pairs: by the one before"):
        m = re.search(rf"^   {re.escape(name)} +(\S+) \( *\S+\) +(\S+) \(", out, re.M)
        got[name] = (float(m.group(1)), float(m.group(2)))
    return got


TABLE_CODE = """
import json
import numpy as np
from data import shakespeare
from experiments import bigram
train, test = shakespeare.split("train"), shakespeare.split("test")
table = bigram.pair_counts(train, 65)
unseen = sorted({(int(a), int(b)) for a, b in zip(test[:-1], test[1:]) if table[a, b] == 0})
print(json.dumps({"table": table.tolist(), "chars": shakespeare.chars(), "unseen": unseen}))
"""


def table0701():
    d = in_project("07.01", TABLE_CODE)
    table, chars, unseen = d["table"], d["chars"], d["unseen"]
    out = bigram_run().out
    occur = sum(1 for row in table for v in row if v)
    printed = figart.value(out, r"possible pairs, (\d+) occur")
    if occur != printed or len(unseen) != figart.value(out, r"(\d+) different pairs, never occur"):
        raise SystemExit(f"the table has {occur} pairs and {len(unseen)} unseen; the run printed:\n{out}")
    V = len(chars)
    f = Fig("table0701", "The pair table of the training text: a row for the character before, a column for the "
                         "one after, darker for more; blank where the pair never occurs", 452)
    cell = 5.6
    x0, y0 = 70, 56
    top = math.log(max(v for row in table for v in row) + 1)
    paths = {}
    for i, row in enumerate(table):
        for j, v in enumerate(row):
            if v:
                op = round(0.15 + 0.85 * math.log(v + 1) / top, 1)
                paths.setdefault(op, []).append(f"M{x0 + j * cell:.1f} {y0 + i * cell:.1f}h{cell}v{cell}h{-cell}z")
    for op, parts in sorted(paths.items()):
        f.add(f'<path class="t" d="{"".join(parts)}" fill-opacity="{op}"/>')
    f.rect(x0, y0, V * cell, V * cell, "m", 0)
    for a, b in unseen:
        f.add(f'<rect class="a" x="{x0 + b * cell - 1:.1f}" y="{y0 + a * cell - 1:.1f}" width="{cell + 2:.1f}" '
              f'height="{cell + 2:.1f}" stroke-width="1.5"/>')
    groups = [("punct.", 0, chars.index("A") - 1), ("A to Z", chars.index("A"), chars.index("Z")),
              ("a to z", chars.index("a"), chars.index("z"))]
    for label, lo, hi in groups:
        f.brace_h(x0 + lo * cell, x0 + (hi + 1) * cell, y0 - 6, "m", up=False)
        f.text(x0 + (lo + hi + 1) * cell / 2, y0 - 12, label, "tm", 10, "middle")
        ya, yb = y0 + lo * cell, y0 + (hi + 1) * cell
        f.path(f"M{x0 - 2} {ya} L{x0 - 8} {ya} L{x0 - 8} {yb} L{x0 - 2} {yb}", "m")
        f.text(x0 - 12, (ya + yb) / 2 + 3.5, label, "tm", 10, "end")
    f.text(x0, 20, "columns: the character after", "t", 11, weight=600)
    f.text(x0 + 190, 20, "rows: the character before", "t", 11, weight=600)
    f.text(x0 + V * cell / 2, y0 + V * cell + 18, "65 characters each way, in their order: \\n, space, punctuation, "
                                                  "3, capitals, small letters", "tm", 10, "middle")
    nx = x0 + V * cell + 26
    lines = [("t", f"{V} x {V} = {V * V} possible pairs", 600), ("t", f"{occur} of them occur in the", None),
             ("t", "training text; the other", None), ("t", f"{V * V - occur} cells are 0", None), ("", "", None),
             ("ta", f"outlined: the {len(unseen)} pairs the test", 600), ("ta", "text has and the training text", None),
             ("ta", "does not; with counts alone", None), ("ta", "each has the chance 0", None)]
    for k, (cls, s, w) in enumerate(lines):
        if s:
            f.text(nx, y0 + 12 + 15 * k, s, cls, 11, weight=w)
    for k, (a, b) in enumerate(unseen):
        f.text(nx + (k % 4) * 46, y0 + 168 + 15 * (k // 4), shown(chars[a]) + shown(chars[b]), "ta", 11, mono=True)
    f.text(nx, y0 + 230, "the row of r, scaled to 1:", "t", 11, weight=600)
    f.text(nx, y0 + 245, "after r, a came 2375 times", "tm", 10.5)
    f.text(nx, y0 + 259, "of 44,271: p = 0.0536", "tm", 10.5)
    r = chars.index("r")
    f.add(f'<rect class="a" x="{x0 - 1}" y="{y0 + r * cell:.1f}" width="{V * cell + 2:.1f}" height="{cell:.1f}" '
          f'stroke-width="1" stroke-dasharray="3 2"/>')
    if table[r][chars.index("a")] != 2375 or sum(table[r]) != 44271:
        raise SystemExit("the row of r is not the one the page quotes")
    return f


def surprise0701():
    rows, mean = twelve(bigram_run().out)
    f = Fig("surprise0701", "Surprise, -log2 p, against the chance p a model gave the character that came; and the "
                            "pair model's surprise at each of the first 12 characters of the test text", 300)
    ps = [i / 400 for i in range(1, 401)]
    ax = figart.Axes(f, 52, 30, 230, 220, (0, 1), (0, 10))
    ax.draw(xlabel="p, the chance of the character that came", xticks=[0, 0.25, 0.5, 0.75, 1],
            yticks=[0, 2, 4, 6, 8, 10])
    f.text(ax.x - 6, 22, "bits: -log2 p", "tm", 11)
    ax.curve(ps, [-math.log2(p) for p in ps], "a", width=2)
    for p, label, tx, ty in ((1.0, "sure and right: 0 bits", 0.97, 2.2), (0.5, "a fair coin: 1 bit", 0.52, 3.6),
                             (1 / 65, "1 of 65 equally likely: 6.022", 0.08, 6.6)):
        y = -math.log2(p)
        ax.dot(p, y, "s f", 3.5)
        anchor = "end" if tx > 0.9 else "start"
        f.text(ax.px(tx), ax.py(ty), label, "t", 10.5, anchor)
        if ty - y > 1:
            f.line(ax.px(p) - (4 if anchor == "end" else 0), ax.py(y) - 5,
                   ax.px(tx) + (-12 if anchor == "end" else 4), ax.py(ty) + 4, "m")
    f.text(ax.px(0) + 8, ax.y + 12, "p -> 0: no limit; at p = 0, infinite", "ta", 10.5)
    # the twelve characters
    bx, bw = 322, 250
    ax2 = figart.Axes(f, bx + 20, 30, bw - 20, 220, (-0.5, 11.5), (0, 10))
    ax2.draw(xticks=[], yticks=[0, 2, 4, 6, 8, 10])
    f.text(ax2.x - 6, 22, "the pair model on the test text, character by character", "tm", 11)
    w = ax2.w / 12 * 0.62
    for i, (pair, count, of, p, b) in enumerate(rows):
        top = ax2.py(b)
        f.rect(ax2.px(i) - w / 2, top, w, ax2.y + ax2.h - top, "s fs", 1)
        f.text(ax2.px(i), top - 4, f"{b:.1f}", "t", 9.5, "middle", mono=True)
        f.text(ax2.px(i), ax2.y + ax2.h + 14, shown(pair[0]), "tm", 10, "middle", mono=True)
        f.text(ax2.px(i), ax2.y + ax2.h + 27, shown(pair[1]), "t", 11, "middle", 700, mono=True)
    f.line(ax2.x, ax2.py(mean), ax2.x + ax2.w, ax2.py(mean), "a", dash=True)
    f.text(ax2.x + ax2.w + 6, ax2.py(mean) - 2, "mean", "ta", 10.5)
    f.text(ax2.x + ax2.w + 6, ax2.py(mean) + 11, f"{mean:.3f}", "ta", 10.5, mono=True)
    f.text(ax2.x + ax2.w + 6, ax2.y + ax2.h + 14, "before", "tm", 10)
    f.text(ax2.x + ax2.w + 6, ax2.y + ax2.h + 27, "came", "t", 10)
    return f


def ladder0701():
    got = ladder_of(bigram_run().out)
    f = Fig("ladder0701", "The ladder: bits per character of three count models on the test text (counted on the "
                          "training text, plus k = 0.1), beside their bits on the training text itself", 236)
    names = [("every character equally likely", "equal chances", "a context of nothing, no counts"),
             ("single characters, by their counts", "single characters", "a context of nothing"),
             ("pairs: by the one before", "pairs", "a context of one character")]
    x0, x1 = 190, 470
    ax = figart.Axes(f, x0, 34, x1 - x0, 150, (0, 7), (-0.5, 2.5))
    for t in range(8):
        X = ax.px(t)
        f.line(X, ax.y, X, ax.y + ax.h, "m", dash=True) if t else f.line(X, ax.y, X, ax.y + ax.h, "m")
        f.text(X, ax.y + ax.h + 16, str(t), "tm", 10.5, "middle", mono=True)
    f.text((x0 + x1) / 2, ax.y + ax.h + 32, "bits per character (lower is better)", "tm", 11, "middle")
    for i, (key, name, sub) in enumerate(names):
        held, seen = got[key]
        y = ax.y + 14 + i * 50
        f.text(x0 - 10, y + 9, name, "t", 12, "end", 600)
        f.text(x0 - 10, y + 23, sub, "tm", 10, "end")
        f.rect(x0, y, ax.px(held) - x0, 16, "a af", 2)
        f.text(ax.px(held) + 6, y + 12.5, f"{held:.3f}  (perplexity {2 ** held:.1f})", "ta", 11, mono=True)
        f.rect(x0, y + 19, ax.px(seen) - x0, 7, "s fs", 1)
    f.rect(x0, 16, 14, 9, "a af", 1)
    f.text(x0 + 20, 24, "test text", "ta", 10.5)
    f.rect(x0 + 100, 18, 14, 6, "s fs", 1)
    f.text(x0 + 120, 24, "training text, k = 0 (the counts' own text)", "t", 10.5)
    return f


# ------------------------------------------------------------------ 07.02

def nplm_run():
    return figart.experiment("nplm", at="07.02")


def recorded_nplm():
    """The recorded long run: its folder and its config (context 5, seed 0's)."""
    d = os.path.join(figlib.TRACK, "experiments", "recorded", "nplm")
    return d, figart.config(os.path.join(d, "context5", "seed0"))


def counts0702():
    r = nplm_run()
    rows = figart.read_log(os.path.join(r.runs, "counts", "seed0"))
    inter = figart.summary(os.path.join(r.runs, "counts", "seed0"))["interpolated"]
    ns = [row["context"] for row in rows]
    f = Fig("counts0702", "Counting with longer contexts: bits per character on the training text (k = 0) and on "
                          "the test text, add-k and deleted interpolation; and how much of the test text has a "
                          "context the training text never had", 300)
    series = [figart.Series("", ns, [row["train_bits"] for row in rows], "s", True),
              figart.Series("", ns, [row["test_bits"] for row in rows], "a"),
              figart.Series("", [int(k) for k in inter], list(inter.values()), "s")]
    ax = figart.plot(f, (8, 6, 420, 288), series, xlabel="characters of context", ylabel="bits per character",
                     ylim=(0, 6.5), xticks=ns, yticks=[0, 1, 2, 3, 4, 5, 6], legend=None)
    ax.hline(math.log2(65), "equal chances: 6.022", side="right")
    best = min(rows, key=lambda row: row["test_bits"])
    ax.dot(best["context"], best["test_bits"], "a fa", 3.5)
    ax.note(best["context"], best["test_bits"], f"{best['test_bits']:.3f}", "ta", 10.5, "middle", dy=-9)
    last = rows[-1]
    end = list(inter.values())[-1]
    ax.note(last["context"], last["test_bits"], f"test, add-k: {last['test_bits']:.3f}", "ta", 10.5, "end", dx=-8, dy=-6)
    ax.note(last["context"], end, f"test, interpolation: {end:.3f}", "t", 10.5, "end", dx=-4, dy=-7)
    ax.note(last["context"], last["train_bits"], f"training text, k = 0: {last['train_bits']:.3f}", "t", 10.5, "end",
            dx=-4, dy=16)
    ax2 = figart.Axes(f, 470, 40, 156, 210, (-0.5, len(rows) - 0.5), (0, 40))
    ax2.draw(xticks=ns, yticks=[0, 10, 20, 30, 40], xlabel="characters of context")
    f.text(ax2.x - 6, 24, "test text: % of contexts unseen", "tm", 11)
    for row in rows:
        v = 100 * row["unseen"]
        if v > 0:
            top = ax2.py(v)
            f.rect(ax2.px(row["context"]) - 7, top, 14, ax2.y + ax2.h - top, "a af", 1)
        if v >= 2:
            f.text(ax2.px(row["context"]), ax2.py(v) - 4, f"{v:.1f}", "ta", 9.5, "middle", mono=True)
    return f


NPLM_CODE = """
import json
from experiments.nplm import NPLM
m = NPLM(65, 5, 24, 512)
shapes = {n: list(p.shape) for n, p in m.named_parameters()}
shapes["total"] = sum(p.numel() for p in m.parameters())
print(json.dumps(shapes))
"""


def nplm0702():
    d = in_project("07.02", NPLM_CODE)
    cfg = figart.config(os.path.join(nplm_run().runs, "context5", "seed0"))
    m, h, n = cfg["embed"], cfg["hidden"], 5
    if d["embed.weight"] != [65, m] or d["hidden.weight"] != [h, n * m]:
        raise SystemExit(f"the network's shapes are not the page's: {d}")
    f = Fig("nplm0702", f"Bengio et al.'s network for a context of {n} characters, at the page's sizes: each "
                        f"character's embedding looked up in one table, the {n} side by side, {h} tanh units, "
                        f"65 scores", 324)
    word = "First"
    cx, cy, cw = 24, 58, 26
    f.text(cx, 30, f"the context: {n} characters", "t", 11.5, weight=600)
    for i, c in enumerate(word):
        f.rect(cx + i * (cw + 4), cy, cw, 24, "s f", 3)
        f.text(cx + i * (cw + 4) + cw / 2, cy + 16.5, c, "t", 12, "middle", 700, mono=True)
    f.text(cx + 5 * (cw + 4) + 4, cy + 16.5, "-> ?", "tm", 12, mono=True)
    tx, ty, tw_, th = 24, 132, 150, 150
    f.rect(tx, ty, tw_, th, "a af", 4)
    for k in range(5):                                  # five rows, picked out by the characters' numbers
        y = ty + 12 + k * 15
        f.rect(tx + 12, y, tw_ - 24, 10, "a", 1)
    f.text(tx + tw_ / 2, ty + 102, "the embedding table", "ta", 11.5, "middle", 700)
    f.text(tx + tw_ / 2, ty + 117, f"65 rows of {m} numbers,", "ta", 10.5, "middle")
    f.text(tx + tw_ / 2, ty + 131, "learned like any weight", "ta", 10.5, "middle")
    f.text(tx + tw_ / 2, ty + th + 14, f"{65 * m:,} weights", "tm", 10, "middle")
    for i in range(n):
        f.line(cx + i * (cw + 4) + cw / 2, cy + 26, tx + 16 + i * 3, ty + 12 + i * 15 + 5, "m")
    vx, vy = 214, 132
    f.text(vx, vy - 10, "side by side", "t", 11, weight=600)
    for i in range(n):
        f.rect(vx, vy + i * 30, 26, 26, "a af", 2)
        f.text(vx + 34, vy + i * 30 + 17, f"{m} from {word[i]}", "ta", 10.5, mono=True)
        f.line(tx + tw_ - 12, ty + 17 + i * 15, vx - 4, vy + i * 30 + 13, "a")
    f.text(vx, vy + n * 30 + 6, f"{n * m} numbers in all", "tm", 10.5)
    hx = 360
    f.label_box(hx, 150, 92, 96, f"{h} tanh", "s f", "t", 12, False, weight=700, sub="units")
    f.text(hx + 46, 264, f"{n * m} x {h} + {h}", "tm", 10, "middle", mono=True)
    f.line(vx + 110, 198, hx - 4, 198, "s", arrow=True)
    ox = 480
    f.label_box(ox, 172, 58, 52, "65", "s f", "t", 13, False, weight=700, sub="scores")
    f.text(ox + 29, 242, f"{h} x 65 + 65", "tm", 10, "middle", mono=True)
    f.line(hx + 94, 198, ox - 4, 198, "s", arrow=True)
    f.line(ox + 60, 198, 566, 198, "s", arrow=True)
    f.text(570, 194, "softmax:", "t", 10.5)
    f.text(570, 208, "the chances", "t", 10.5)
    f.text(570, 222, "of the next", "t", 10.5)
    f.text(24, 318, f"{d['total']:,} weights in all. A character's embedding is the same row wherever it stands "
                    f"in the context.", "tm", 10.5)
    return f


def scores0702():
    r = nplm_run()
    d, cfg = recorded_nplm()
    short = {n: [figart.summary(x)["test_bits"] for x in figart.seed_dirs(os.path.join(r.runs, f"context{n}"))]
             for n in (1, 3, 5)}
    counts = figart.summary(os.path.join(d, "counts", "seed0"))
    long_, mixed = {}, {}
    for n in cfg["contexts"]:
        dirs = figart.seed_dirs(os.path.join(d, f"context{n}"))
        long_[n] = [figart.summary(x)["test_bits"] for x in dirs]
        mixed[n] = [figart.summary(x)["mixed_bits"] for x in dirs]
    page = figart.summary(os.path.join(r.runs, "counts", "seed0"))
    for n in (1, 3, 5):                                  # the page's run and the recorded one counted alike
        if abs(page["interpolated"][str(n)] - counts["interpolated"][str(n)]) > 1e-12:
            raise SystemExit(f"the two runs' interpolation differs at {n}")
    ns = cfg["contexts"]
    f = Fig("scores0702", "Bits per character on the test text: the network in the page's one-minute run and in the "
                          "recorded 20-minute run (a ring per seed), against add-k and deleted interpolation of "
                          "the same context", 342)
    styles = ["m", "s", "s", "a", "a"]
    one = figart.Axes(f, 56, 64, 118, 222, (-0.5, 0.5), (3.585, 3.62))
    one.draw(xticks=[], yticks=[3.59, 3.60, 3.61, 3.62])
    rest = figart.Axes(f, 234, 64, 392, 222, (0.5, len(ns) - 0.5), (2.25, 3.05))
    rest.draw(xticks=[], yticks=[2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 3.0])
    f.text(one.x - 6, one.y - 8, "bits per character", "tm", 11.5)
    f.text(rest.x - 6, rest.y - 8, "(a scale of its own: from 2.25 to 3.05)", "tm", 10.5)
    step = 22
    for i, n in enumerate(ns):
        ax = one if i == 0 else rest
        lo, hi = ax.ylim
        X0 = ax.px(i) - step * (len(styles) - 1) / 2
        xs = [X0 + k * step for k in range(len(styles))]
        f.text(ax.px(i), ax.y + ax.h + 18, f"context {n}", "t", 11.5, "middle", 700)
        ak, it = counts["add_k"][str(n)], counts["interpolated"][str(n)]
        f.line(xs[0] - 10, ax.py(it), xs[-1] + 10, ax.py(it), "s", dash=True)
        if ak <= hi:
            f.rect(xs[0] - 3.5, ax.py(ak) - 3.5, 7, 7, "m fs", 0)
        else:
            f.line(xs[0], ax.py(hi) + 20, xs[0], ax.py(hi) + 3, "m", arrow=True)
            f.text(xs[0] + 3, ax.py(hi) + 32, f"{ak:.2f}", "tm", 9.5, "middle", mono=True)
        f.rect(xs[1] - 3.5, ax.py(it) - 3.5, 7, 7, "s fs", 0)
        for k, vals in ((2, short.get(n)), (3, long_[n]), (4, mixed[n])):
            for v in vals or []:
                f.circle(xs[k], ax.py(v), 3, f"{styles[k]} {'fa' if k == 4 else 'f'}")
        if i:
            mean = sum(long_[n]) / len(long_[n])
            f.text(xs[3], ax.py(min(long_[n])) + 14, f"{mean:.3f}", "ta", 9.5, "middle", mono=True)
            f.text(xs[0] - 10, ax.py(it) + 13, f"{it:.3f}", "t", 9.5, mono=True)
    items = [("add-k", "m", "sq"), ("deleted interpolation", "s", "sq"), ("network, 1 minute", "s", "ring"),
             ("network, 20 minutes", "a", "ring"), ("the 20-minute network mixed with interpolation", "a", "dot")]
    for k, (label, style, shape) in enumerate(items):
        x = 56 + (k % 3) * 196 if k < 3 else 56 + (k - 3) * 196
        y = 14 if k < 3 else 30
        if shape == "sq":
            f.rect(x, y - 7.5, 7, 7, f"{style} fs", 0)
        else:
            f.circle(x + 3.5, y - 4, 3, f"{style} {'fa' if shape == 'dot' else 'f'}")
        f.text(x + 12, y, label, figart.TEXT[style], 10.5)
    f.text(56, 334, "Left to right in each context: add-k, interpolation (and its dashed level), the network in 1 minute "
                    "and in 20, mixed.", "tm", 10.5)
    return f


def near0702():
    d, cfg = recorded_nplm()
    n = max(cfg["contexts"])
    emb = figart.summary(os.path.join(d, f"context{n}", "seed0"))["embedding"]
    chars = in_project("07.02", "import json; from data import shakespeare; print(json.dumps(shakespeare.chars()))")
    pick = list(".!?,;:") + list("aeiou") + list("AEIOU") + list("stST")
    vec = [emb[chars.index(c)] for c in pick]
    norm = [math.sqrt(sum(x * x for x in v)) for v in vec]
    sim = [[sum(a * b for a, b in zip(vec[i], vec[j])) / (norm[i] * norm[j]) for j in range(len(pick))]
           for i in range(len(pick))]
    if abs(sim[pick.index(".")][pick.index("!")] - 0.81) > 0.005 or abs(sim[pick.index("s")][pick.index("S")] - 0.57) > 0.005:
        raise SystemExit("the long run's similarities are not the ones its output printed")
    m = cfg["embed"]
    f = Fig("near0702", f"Cosine similarity of the embeddings of 20 characters after the recorded long run (context "
                        f"{n}, seed 0, {m} numbers each): accent above 0, the other colour below 0", 402)
    cell = 16
    x0, y0 = 40, 40
    for i, a in enumerate(pick):
        f.text(x0 - 6, y0 + i * cell + 11.5, shown(a), "t", 11, "end", mono=True)
        f.text(x0 + i * cell + cell / 2, y0 - 6, shown(a), "t", 11, "middle", mono=True)
        for j in range(len(pick)):
            v = sim[i][j]
            if i == j:
                continue
            op = round(min(1.0, abs(v)), 1)
            if op >= 0.1:
                f.add(f'<rect class="{"fa" if v > 0 else "t"}" x="{x0 + j * cell}" y="{y0 + i * cell}" '
                      f'width="{cell}" height="{cell}" fill-opacity="{op}"/>')
    f.rect(x0, y0, len(pick) * cell, len(pick) * cell, "m", 0)
    lo = min(sim[i][j] for i in range(3) for j in range(3) if i != j)
    hi = max(sim[i][j] for i in range(3) for j in range(3) if i != j)
    nx = x0 + len(pick) * cell + 24
    notes = [("ta", f". ! ? together: {lo:.2f} to {hi:.2f}", 600), ("ta", "the marks that end a sentence", None),
             ("", "", None),
             ("t", f"s and S {sim[pick.index('s')][pick.index('S')]:.2f}, a and A "
                   f"{sim[pick.index('a')][pick.index('A')]:.2f}:", 600),
             ("t", "a few capitals near their", None), ("t", "small letters", None), ("", "", None),
             ("tm", f"two random vectors of {m} numbers:", None), ("tm", "similarities spread with a standard", None),
             ("tm", f"deviation of 1/sqrt({m}) = {1 / math.sqrt(m):.2f}; most", None),
             ("tm", "cells here are within that", None)]
    for k, (cls, s, w) in enumerate(notes):
        if s:
            f.text(nx, y0 + 12 + 15 * k, s, cls, 11, weight=w)
    f.text(x0, y0 + len(pick) * cell + 22, "the diagonal, each character with itself (1), is left blank", "tm", 10.5)
    return f


# ------------------------------------------------------------------ 07.03

def rnn_run():
    return figart.experiment("rnn", at="07.03")


UNROLL_TEXT = "First Citizen"
UNROLL_CODE = """
import json, tempfile
import torch
import torch.nn.functional as F
import lab
from data import shakespeare
from experiments import rnn
from experiments.sequences import window_bits
cfg = lab.config(rnn.CONFIG, ["out=" + tempfile.mkdtemp()])
V = len(shakespeare.chars())
dev = torch.device("cpu")
train, test = (torch.from_numpy(shakespeare.split(s)) for s in ("train", "test"))
model, norms = rnn.train(cfg, lab.Run(cfg, 0, label="text"), dev, train, V)
score = window_bits(lambda x: model(x)[0], test, cfg.span, cfg.warm)
ids = torch.from_numpy(shakespeare.encode(%r))[None]
with torch.no_grad():
    states, h = model.rnn(model.embed(ids))
    p = F.softmax(model.out(states), dim=-1)[0]
vocab = shakespeare.chars()
steps = []
for t in range(ids.shape[1]):
    top = p[t].topk(3)
    steps.append({"state": states[0, t, :32].tolist(), "flat": int((states[0, t].abs() > 0.9).sum()),
                  "guesses": [[vocab[int(i)], float(v)] for v, i in zip(top.values, top.indices)]})
print(json.dumps({"bits": score, "hidden": cfg.hidden, "steps": steps}))
""" % UNROLL_TEXT


def unroll0703():
    """The stepped figure: the seed-0 text network of the page's run reads a line a character at a time."""
    d = in_project("07.03", UNROLL_CODE)
    printed = figart.value(rnn_run().out, r"seed 0: (\S+) bits")
    if f"{d['bits']:.3f}" != f"{printed:.3f}":
        raise SystemExit(f"the network trained here scores {d['bits']}, the page's seed 0 {printed}")
    text, hidden = UNROLL_TEXT, d["hidden"]
    f = Fig("unroll0703", f"The recurrent network of the page's run (seed 0) reading the first line of the training "
                          f"text a character at a time: the same cell at every step, its state carried to the next",
            316)
    x0, cw, gap = 22, 30, 16
    xs = [x0 + i * (cw + gap) for i in range(len(text))]
    f.text(x0, 20, "the characters, read one at a time", "tm", 11)
    f.text(x0, 136, f"the state after each: the first 32 of its {hidden} numbers (accent above 0, the other colour "
                    f"below)", "tm", 11)
    f.text(x0, 238, "its chances for the next character, the three highest", "tm", 11)
    for i, c in enumerate(text):
        f.rect(xs[i], 30, cw, 26, "m f", 3, dash=True)
        f.text(xs[i] + cw / 2, 48, shown(c), "tm", 12, "middle", mono=True)
    for t, st in enumerate(d["steps"]):
        said = lambda c: "a space" if c == " " else repr(c)
        cap = f"Reads {said(text[t])}" + (", from a state of zeros" if t == 0 else "") + ": "
        g = st["guesses"]
        nxt = text[t + 1] if t + 1 < len(text) else None
        cap += f"the most likely next is {said(g[0][0])} ({g[0][1]:.2f})"
        if nxt is not None:
            right = [x for x in g if x[0] == nxt]
            cap += (f"; what came, {said(nxt)}, is among its three best ({right[0][1]:.2f})" if right
                    else f"; what came, {said(nxt)}, is not among its three best")
        cap += f". {st['flat']} of the {hidden} numbers of its state are beyond 0.9 in size."
        with steps.step(f, cap):
            for i in range(t + 1):
                lit = i == t
                f.rect(xs[i], 30, cw, 26, "a af" if lit else "s f", 3)
                f.text(xs[i] + cw / 2, 48, shown(text[i]), "ta" if lit else "t", 12, "middle", 700 if lit else None,
                       mono=True)
                f.circle(xs[i] + cw / 2, 88, 11, "a af" if lit else "s f")
                f.text(xs[i] + cw / 2, 92, "h", "ta" if lit else "t", 11, "middle", 600, mono=True)
                f.line(xs[i] + cw / 2, 58, xs[i] + cw / 2, 75, "a" if lit else "s", arrow=True)
                if i:
                    f.line(xs[i - 1] + cw / 2 + 12, 88, xs[i] + cw / 2 - 13, 88, "a" if lit else "s", arrow=True)
            f.text(xs[t] + cw / 2, 116, "the same cell", "ta", 10, "middle")
            cell = 17
            for k, v in enumerate(st["state"]):
                X, Y = x0 + (k % 16) * (cell + 2), 146 + (k // 16) * (cell + 2)
                op = round(min(1.0, abs(v)), 1)
                if op >= 0.1:
                    f.add(f'<rect class="{"fa" if v > 0 else "t"}" x="{X}" y="{Y}" width="{cell}" height="{cell}" '
                          f'fill-opacity="{op}"/>')
                f.rect(X, Y, cell, cell, "m", 0)
            sx = x0 + 16 * (cell + 2) + 20
            f.text(sx, 160, f"{st['flat']} of {hidden}", "ta", 13, weight=700)
            f.text(sx, 176, "beyond 0.9 in size:", "tm", 10.5)
            f.text(sx, 190, "tanh's flat ends", "tm", 10.5)
            for k, (c, v) in enumerate(g):
                X = x0 + k * 150
                ok = nxt is not None and c == nxt
                f.rect(X, 248, max(2, 110 * v), 16, "a af" if ok else "s fs", 2)
                f.text(X, 280, f"{shown(c)!r} {v:.2f}", "ta" if ok else "t", 11.5, weight=700 if ok else None,
                       mono=True)
            if nxt is not None:
                f.text(x0 + 450, 260, f"what came: {shown(nxt)!r}", "t", 11.5, weight=600, mono=True)
            f.text(x0, 304, "accent: the character that came next; _ is a space", "tm", 10.5)
    steps.check(f.svg())
    return f


def uses0703():
    out = rnn_run().out
    ws = [int(m.group(1)) for m in re.finditer(r"^   w = +(\d+): ", out, re.M)]
    bits = [figart.value(out, rf"^   w = +{w}: (\S+)$") for w in ws]
    pairs = 3.599
    if f"{pairs:.3f}" not in bigram_run().out:
        raise SystemExit("07.01's pair model is not at 3.599")
    f = Fig("uses0703", "What the trained network uses (seed 0): bits per character on the test text when only the "
                        "last w characters it read are the real ones before each character, the rest from another "
                        "place", 290)
    ax = figart.Axes(f, 60, 30, 560, 200, (-0.5, len(ws) - 0.5), (2, 10.5))
    ax.draw(xticks=[], yticks=[2, 4, 6, 8, 10], xlabel="w, the real characters at the end of the 64 it read")
    f.text(ax.x - 6, 22, "bits per character", "tm", 11.5)
    for i, w in enumerate(ws):
        f.text(ax.px(i), ax.y + ax.h + 16, str(w), "tm", 10.5, "middle", mono=True)
    ax.hline(math.log2(65), "equal chances 6.022", side="right")
    ax.hline(pairs, "07.01's pairs 3.599", side="right")
    pts = [(ax.px(i), ax.py(b)) for i, b in enumerate(bits)]
    f.polyline(pts, "a", False, 2)
    for i, b in enumerate(bits):
        f.circle(ax.px(i), ax.py(b), 3.5, "a fa")
        f.text(ax.px(i) + (8 if i < 4 else 0), ax.py(b) - 8, f"{b:.3f}", "ta", 10, "start" if i < 4 else "middle",
               mono=True)
    k16 = ws.index(16)
    f.add(f'<rect class="af" x="{ax.px(k16) - 12:.1f}" y="{ax.y + 1}" width="{ax.px(len(ws) - 1) - ax.px(k16) + 24:.1f}" '
          f'height="{ax.h - 2}" fill-opacity="0.6"/>')
    f.text(ax.px(k16) - 4, ax.py(9.4), "past 16 characters, nothing it", "ta", 11, weight=600)
    f.text(ax.px(k16) - 4, ax.py(9.4) + 14, "reads changes the score", "ta", 11)
    return f


def recall0703():
    r = rnn_run()
    delays = figart.config(figart.seed_dirs(os.path.join(r.runs, "text"))[0])["delays"]
    groups = [(f"T = {T}", [figart.summary(x)["accuracy"] for x in figart.seed_dirs(os.path.join(r.runs, f"recall{T}"))],
               "a") for T in delays]
    f = Fig("recall0703", "The recall task: accuracy on 1000 new sequences after T blanks, 3 seeds each: a ring per "
                          "seed, the bar their mean", 260)
    ax = figart.seeds_chart(f, (8, 4, 624, 252), groups, ylabel="accuracy", ylim=(0, 1.05),
                            yticks=[0, 0.25, 0.5, 0.75, 1])
    ax.hline(0.125, "chance: 0.125", side="left")
    return f


def gradient_rows(out):
    """Part 4's table: [(name, radius, [six gradients])] and the k it was printed for."""
    ks = [int(k) for k in re.findall(r"k = (\d+)", out.split("4. The gradient")[1].splitlines()[1])]
    rows = []
    for line in out.split("4. The gradient")[1].splitlines()[2:]:
        m = re.match(r"^ +(\S.*?) +(\d+\.\d\d)  ((?: +\S+)+)$", line)
        if not m:
            break
        rows.append((m.group(1).strip(), float(m.group(2)), [float(v) for v in m.group(3).split()]))
    return ks, rows


def gradient0703():
    ks, rows = gradient_rows(rnn_run().out)
    f = Fig("gradient0703", "The gradient that reaches the input k steps back from the answer: the recall network as "
                            "it starts, its recurrent weights rescaled to other spectral radii, and the trained text "
                            "network", 344)
    ax = figart.Axes(f, 66, 30, 400, 250, (0, max(ks)), (1e-24, 1e4), False, True)
    ax.draw(xticks=ks, yticks=[1e-24, 1e-20, 1e-16, 1e-12, 1e-8, 1e-4, 1, 1e4],
            xlabel="k, steps back from the answer")
    f.text(ax.x - 6, 22, "size of the gradient (log scale)", "tm", 11.5)
    ends = []
    for name, rad, g in rows:
        trained = name.startswith("the text network")
        start = name.startswith("the recall network")
        style = "a" if trained else ("s" if start else "m")
        pts = [(k, v) for k, v in zip(ks, g) if v > 0]
        ax.curve([k for k, _ in pts], [v for _, v in pts], style, dash=not (trained or start), width=2 if trained else 1.75)
        for k, v in pts:
            ax.dot(k, v, f"{style} {'fa' if trained else 'f'}", 2.5)
        if len(pts) < len(ks):
            k, v = pts[-1]
            ax.note(k, v, "then 0", "tm", 10, "start", dx=6, dy=4)
        label = ("trained text network, radius" if trained else "as it starts, radius" if start else "radius")
        ends.append([ax.py(pts[-1][1]) + 3.5, f"{label} {rad:.2f}", style, ax.px(pts[-1][0])])
    ends.sort()
    for i in range(1, len(ends)):
        ends[i][0] = max(ends[i][0], ends[i - 1][0] + 13)
    for y, label, style, x in ends:
        f.text(ax.x + ax.w + 8, y, label, figart.TEXT[style], 10.5)
    f.text(66, 338, "Dashed: the same starting weights with the recurrent matrix scaled to the radius shown.", "tm", 10.5)
    return f


# ------------------------------------------------------------------ 07.04

def attention_run():
    return figart.experiment("attention", at="07.04")


def examples_of(seed=0):
    """The weights of the attention runs' examples (seed's summary.json): [{input, written, weights}]."""
    return figart.summary(os.path.join(attention_run().runs, "attention", f"seed{seed}"))["examples"]


def seq2seq0704():
    cfg = figart.config(os.path.join(attention_run().runs, "attention", "seed0"))
    h = cfg["hidden"]
    f = Fig("seq2seq0704", f"An encoder and a decoder, both 07.03's recurrent cell with a state of {h}. Without "
                           f"attention the decoder starts from the encoder's last state and has nothing else; with "
                           f"attention, every step also takes a weighted sum of all the encoder's states", 380)
    inp, n = [8, 6, 5, 2], 4
    step = 54

    def chain(x0, y, names, cls, tcls):
        xs = [x0 + i * step for i in range(len(names))]
        for i, lab in enumerate(names):
            f.circle(xs[i], y, 13, cls)
            f.text(xs[i], y + 4, lab, tcls, 10.5, "middle", 600, mono=True)
            if i:
                f.line(xs[i - 1] + 14, y, xs[i] - 15, y, "s", arrow=True)
        return xs

    for panel, (y0, title) in enumerate(((20, "without attention"), (190, "with attention"))):
        lit = "a af" if panel else "s f"
        f.text(20, y0, title, "ta" if panel else "t", 12.5, weight=700)
        by, cy = y0 + 22, y0 + 82
        ex = chain(120, cy, ["h1", "h2", "h3", "h4"], "s f", "t")
        dx = chain(410, cy, ["s1", "s2", "s3", "s4"], lit, "ta" if panel else "t")
        f.text(ex[0] - 22, cy + 4, "encoder", "t", 11, "end", 600)
        f.text(dx[-1] + 22, cy + 4, "decoder", "ta" if panel else "t", 11, "start", 600)
        for i, v in enumerate(inp):
            f.rect(ex[i] - 12, by, 24, 20, "s fs", 3)
            f.text(ex[i], by + 14, str(v), "t", 11, "middle", mono=True)
            f.line(ex[i], by + 21, ex[i], cy - 15, "s", arrow=True)
            f.rect(dx[i] - 12, by, 24, 20, lit, 3)
            f.text(dx[i], by + 14, str(v), "ta" if panel else "t", 11, "middle", mono=True)
            f.line(dx[i], cy - 14, dx[i], by + 22, "s", arrow=True)
        f.text(ex[0] - 22, by + 14, "reads", "tm", 10.5, "end")
        f.text(dx[-1] + 22, by + 14, "writes", "tm", 10.5)
        f.line(ex[-1] + 14, cy, dx[0] - 15, cy, "s", arrow=True)
        f.text((ex[-1] + dx[0]) / 2, cy - 8, f"one vector of {h}", "tm", 10.5, "middle")
        if panel:
            k = 2                                     # the decoder's third step looks back at every encoder state
            for i in range(n):
                on = i == k
                f.path(f"M{ex[i]} {cy + 14} C {ex[i]} {cy + 62}, {dx[k]} {cy + 62}, {dx[k]} {cy + 16}",
                       "a" if on else "m", arrow=on, dash=not on)
            f.text(ex[0] - 12, cy + 70, "step 3: a score for every encoder state, a softmax over the scores, and the "
                                        "states' weighted sum", "ta", 10.5)
    f.text(20, 372, "Training gives the decoder the right symbol before each step; writing, it is given the symbol it "
                    "wrote last.", "tm", 10.5)
    return f


def step0704():
    """The stepped figure: seed 0's length-10 example, a decoder step at a time."""
    ex = examples_of(0)[0]
    out = attention_run().out
    printed = re.search(r"input (\[[\d, ]+\]):", out).group(1)
    if json.loads(printed) != ex["input"]:
        raise SystemExit(f"the summary's example {ex['input']} is not the one the run printed, {printed}")
    x, wr, ws = ex["input"], ex["written"], ex["weights"]
    n = len(x)
    f = Fig("step0704", "The attention decoder of the page's run (seed 0) copying its first example: at each step, "
                        "its weights over the 10 input positions, and the symbol it wrote", 270)
    x0, cw, gap = 110, 40, 8
    xs = [x0 + i * (cw + gap) for i in range(n)]
    f.text(20, 40, "input", "t", 11.5, weight=600)
    f.text(20, 206, "written", "t", 11.5, weight=600)
    f.text(20, 130, "weights", "ta", 11.5, weight=600)
    for i, v in enumerate(x):
        f.rect(xs[i], 22, cw, 26, "s fs", 3)
        f.text(xs[i] + cw / 2, 40, str(v), "t", 12.5, "middle", 600, mono=True)
        f.text(xs[i] + cw / 2, 62, f"position {i}" if i == 0 else str(i), "tm", 9.5, "middle")
        f.rect(xs[i], 188, cw, 26, "m f", 3, dash=True)
    base, top = 170, 76
    f.line(xs[0] - 4, base, xs[-1] + cw + 4, base, "m")
    for t in range(n):
        w = ws[t]
        best = max(range(n), key=lambda j: w[j])
        cap = (f"Step {t}: most weight, {w[best]:.2f}, on input position {best}, the symbol {x[best]}; it writes "
               f"{wr[t]}" + (", right." if wr[t] == x[t] else f", where {x[t]} was right."))
        with steps.step(f, cap):
            for j in range(n):
                hgt = (base - top) * w[j]
                if hgt > 0.5:
                    f.rect(xs[j] + 6, base - hgt, cw - 12, hgt, "a af" if j == best else "s fs", 1)
                if w[j] >= 0.05:
                    f.text(xs[j] + cw / 2, base - hgt - 4, f"{w[j]:.2f}", "ta" if j == best else "tm", 9.5, "middle",
                           mono=True)
            f.add(f'<rect class="a" x="{xs[best] - 2}" y="20" width="{cw + 4}" height="30" rx="4" stroke-width="2"/>')
            for i in range(t + 1):
                lit = i == t
                f.rect(xs[i], 188, cw, 26, "a af" if lit else "s f", 3)
                f.text(xs[i] + cw / 2, 206, str(wr[i]), "ta" if lit else "t", 12.5, "middle", 700 if lit else None,
                       mono=True)
            f.text(20, 250, f"step {t}: the weights add up to {sum(w):.2f}", "tm", 10.5)
    steps.check(f.svg())
    return f


def length0704():
    r = attention_run()
    cfg = figart.config(os.path.join(r.runs, "attention", "seed0"))
    lengths = cfg["lengths"]
    series = []
    for label, name, style in (("no-attention", "no attention", "s"), ("attention", "attention", "a")):
        per = [[figart.summary(d)["symbols_right"][str(n)] for d in figart.seed_dirs(os.path.join(r.runs, label))]
               for n in lengths]
        series.append(figart.Series(name, lengths, [sum(p) / len(p) for p in per], style,
                                    lo=[min(p) for p in per], hi=[max(p) for p in per]))
    f = Fig("length0704", f"Copying random symbols: the fraction written right, greedily, on {cfg['tested']} new "
                          f"inputs of each length; trained on lengths {cfg['shortest']} to {cfg['longest']}; mean "
                          f"of {cfg['seeds']} seeds, the band from the lowest seed to the highest", 300)
    ax = figart.plot(f, (8, 6, 624, 288), series, xlabel="length of the input", ylabel="symbols written right",
                     ylim=(0, 1.05), xticks=lengths, yticks=[0, 0.2, 0.4, 0.6, 0.8, 1], legend="top")
    ax.hline(1 / cfg["symbols"], f"chance: {1 / cfg['symbols']:.2f}", side="left")
    ax.vline(cfg["longest"])
    ax.note(cfg["longest"], 0.55, "the longest", "tm", 10.5, "start", dx=5)
    ax.note(cfg["longest"], 0.55, f"trained on: {cfg['longest']}", "tm", 10.5, "start", dx=5, dy=14)
    for s in series:
        for n, v in zip(s.xs, s.ys):
            ax.dot(n, v, "a fa" if s.style == "a" else "s f", 3)
            if s.style == "s" and v > 0.99:
                continue
            ax.note(n, v, f"{v:.2f}" if v < 0.995 else "1", "ta" if s.style == "a" else "t", 10, "middle",
                    dy=-9 if s.style == "a" else 15)
    return f


def weights0704():
    exs = examples_of(0)
    f = Fig("weights0704", "The attention weights of seed 0's two examples: a row for each output step, a column for "
                           "each input position, darker for more weight; the outputs it wrote wrong are marked", 400)
    for k, (ex, x0, cell) in enumerate(((exs[0], 34, 16), (exs[1], 300, 9.4))):
        x, wr, ws = ex["input"], ex["written"], ex["weights"]
        n = len(x)
        y0 = 58
        wrong = [i for i in range(n) if wr[i] != x[i]]
        f.text(x0, 20, f"length {n}" + (", trained on" if n <= 20 else ", longer than any trained on"),
               "t", 11.5, weight=600)
        f.text(x0, 36, f"{n - len(wrong)} of {n} written right", "tm", 10.5)
        for i in range(n):
            for j in range(n):
                v = ws[i][j]
                op = round(min(1.0, v), 1)
                if op >= 0.1:
                    f.add(f'<rect class="fa" x="{x0 + j * cell:.1f}" y="{y0 + i * cell:.1f}" width="{cell}" '
                          f'height="{cell}" fill-opacity="{op}"/>')
            if i in wrong:
                f.text(x0 + n * cell + 6, y0 + i * cell + cell - 1.5, "x", "ta", 9 if cell < 12 else 11, weight=700,
                       mono=True)
        f.rect(x0, y0, n * cell, n * cell, "m", 0)
        f.text(x0 + n * cell / 2, y0 + n * cell + 16, "input position", "tm", 10.5, "middle")
        f.text(x0 - 4, y0 + 10, "step", "tm", 9.5, "end")
    lost = next((i for i, w in enumerate(exs[1]["weights"]) if max(range(len(w)), key=lambda j: w[j]) != i), None)
    f.text(34, 270, "The diagonal: at step i the most weight is on", "tm", 10.5)
    f.text(34, 284, "input i, the symbol to copy there.", "tm", 10.5)
    if lost is not None:
        f.text(300, 392, f"At step {lost} its largest weight leaves the diagonal for the first time.", "tm", 10.5)
    return f


FIGS = [
    ("07.01-table", table0701),
    ("07.01-surprise", surprise0701),
    ("07.01-ladder", ladder0701),
    ("07.02-counts", counts0702),
    ("07.02-nplm", nplm0702),
    ("07.02-scores", scores0702),
    ("07.02-near", near0702),
    ("07.03-unroll", unroll0703),
    ("07.03-uses", uses0703),
    ("07.03-recall", recall0703),
    ("07.03-gradient", gradient0703),
    ("07.04-seq2seq", seq2seq0704),
    ("07.04-step", step0704),
    ("07.04-length", length0704),
    ("07.04-weights", weights0704),
]


def main():
    only = sys.argv[1:]
    for name, fn in FIGS:
        if only and not any(name.startswith(o) for o in only):
            continue
        print(write(MOD, name, fn()))


if __name__ == "__main__":
    main()
