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


FIGS = [
    ("07.01-table", table0701),
    ("07.01-surprise", surprise0701),
    ("07.01-ladder", ladder0701),
    ("07.02-counts", counts0702),
    ("07.02-nplm", nplm0702),
    ("07.02-scores", scores0702),
    ("07.02-near", near0702),
]


def main():
    only = sys.argv[1:]
    for name, fn in FIGS:
        if only and not any(name.startswith(o) for o in only):
            continue
        print(write(MOD, name, fn()))


if __name__ == "__main__":
    main()
