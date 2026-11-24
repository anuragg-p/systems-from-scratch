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


FIGS = [
    ("07.01-table", table0701),
    ("07.01-surprise", surprise0701),
    ("07.01-ladder", ladder0701),
]


def main():
    only = sys.argv[1:]
    for name, fn in FIGS:
        if only and not any(name.startswith(o) for o in only):
            continue
        print(write(MOD, name, fn()))


if __name__ == "__main__":
    main()
