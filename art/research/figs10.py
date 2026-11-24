"""Figures for research module 10, Today's architecture (lessons 10.01-10.05).

    RESEARCH_FIGS_CACHE=DIR python3 -B art/research/figs10.py [10.02 ...]
                                    all of them, or those whose name starts so (DIR keeps the runs)

Every bar, curve and number comes from the reference code (tracks/research), run as the page runs it,
from SmolLM2's and GPT-2's fetched files, or from the recorded long run 10.05 reads:

  10.01  python3 -m experiments.rmsnorm (the page's run): its four parts and each seed's summary; RMSNorm
         and nn.LayerNorm on the run's two vectors, in the project at 10.01 (they must be the run's)
  10.02  python3 -m experiments.rotary (the page's run); Rotary in the project at 10.02: one pair of a head
         of 16 turned for four places, the angles of every pair along a window of 64, the offset test move
         by move (its largest change must be the run's); python3 -m experiments.positions at 08.03 (08.03's
         page run) for the model without positions; experiments/recorded/ablation/ (base and rotary)
  10.03  python3 -m experiments.swiglu (the page's run), and the same with steps=600 and steps=1200, run
         for the figure; 10.05's page run (its 80-step rows); experiments/recorded/ablation/; the MLPs'
         weights and gelu and silu in the project at 10.03
  10.04  python3 -m experiments.smollm (the page's run); SmolLM2's file header and GPT(**CONFIG)'s shapes,
         SmolLM2's and GPT-2's tokenizers on two sentences, in the project at 10.04; python3 -m
         experiments.gpt2 at 09.03 with its sampling cut short, for its ladder (09.03's page's rows)
  10.05  python3 -m experiments.ablation (the page's run); experiments/recorded/ablation/ (every row's
         summaries and logs, beside its output.txt, whose table must be the same numbers)

Needs PyTorch, SmolLM2's and GPT-2's files (python3 -m data.fetch smollm2, python3 -m data.fetch gpt2,
in tracks/research). The runs take about fifteen minutes in all on the machine in NOTES.md, most of it
the two longer SwiGLU runs; RESEARCH_FIGS_CACHE keeps them between processes.
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

MOD = "10"
REC = os.path.join(figlib.TRACK, "experiments", "recorded", "ablation")
ROWS = ["base (08)", "RMSNorm", "rotary", "SwiGLU", "grouped-query", "all four"]
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
    """Welch's t of a against b (lab.welch_t's), and its denominator, the spread of the difference."""
    se = math.sqrt(sd(a) ** 2 / len(a) + sd(b) ** 2 / len(b))
    return (mean(a) - mean(b)) / se, se


def seeds_of(d, key="test_bits"):
    return [figart.summary(x)[key] for x in figart.seed_dirs(d)]


def shown(s, space="_"):
    """Text as a figure writes it, in ASCII: a space as _, a line break as \\n, anything else outside
    printable ASCII as its escape."""
    out = []
    for c in s:
        if c == " ":
            out.append(space)
        elif c == "\n":
            out.append("\\n")
        elif 32 < ord(c) < 127:
            out.append(c)
        else:
            out.append(ascii(c)[1:-1])
    return "".join(out)


def chip(f, x, y, s, cls="s f", tcls="t", size=11, h=22, pad=7, weight=None, dash=False):
    """A box round one piece of text in mono, its width from the text; the x after it."""
    w = max(tw(s, size, mono=True) + 2 * pad, 16)
    f.rect(x, y, w, h, cls, 3, dash=dash)
    f.text(x + w / 2, y + h / 2 + size * 0.36, s, tcls, size, "middle", weight, mono=True)
    return x + w


def shade(f, x, y, w, h, op, cls="fa"):
    op = round(max(0.0, min(1.0, op)), 2)
    if op >= 0.03:
        f.add(f'<rect class="{cls}" x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill-opacity="{op}"/>')


def spread_of(text):
    """lab.spread's line, '3.563 +- 0.004889 (min 3.559, max 3.568, 3 seeds)': (mean, sd, min, max, n)."""
    m = re.match(r"(\S+) \+- (\S+) \(min (\S+), max (\S+), (\d+) seeds\)", text)
    return tuple(float(v) for v in m.groups()[:4]) + (int(m.group(5)),)


# ------------------------------------------------------------------ the runs

def rms_run():
    return figart.experiment("rmsnorm", at="10.01")


def rot_run():
    return figart.experiment("rotary", at="10.02")


def pos_run():
    return figart.experiment("positions", at="08.03")


def glu_run(steps=None):
    return figart.experiment("swiglu", *([f"steps={steps}"] if steps else []), at="10.03")


def smol_run():
    return figart.experiment("smollm", at="10.04")


def ladder_run():
    return figart.experiment("gpt2", "prompts=1", "length=2", "seeds=1", "greedy=2", at="09.03")


def abl_run():
    return figart.experiment("ablation", at="10.05")


def compared(r, names):
    """Each variant's test bits by seed, from the summaries a compare() run wrote: {name: [...]}."""
    return {n: seeds_of(os.path.join(r.runs, n)) for n in names}


def printed_ms(out, name):
    """A variant's 'ms a step' spread as the run printed it, under its bits line."""
    m = re.search(rf"^   {re.escape(name)} .*\n +ms a step (.*)$", out, re.M)
    return spread_of(m.group(1))


# ------------------------------------------------------------------ 10.01

VECTOR_CODE = """
import json, torch
from torch import nn
from models.gpt import RMSNorm
one = torch.tensor([[3.0, 4.0, 0.0, 0.0], [5.0, 6.0, 7.0, 8.0]])
with torch.no_grad():
    print(json.dumps({"x": one.tolist(), "rms": RMSNorm(4)(one).tolist(), "layer": nn.LayerNorm(4)(one).tolist()}))
"""


def vector1001():
    d = in_project("10.01", VECTOR_CODE)
    out = rms_run().out
    for k, v in enumerate(d["x"]):
        line = re.search(rf"\[{', '.join(str(int(x)) for x in v)}\]: .*$", out, re.M).group(0)
        rms = [round(x, 4) for x in d["rms"][k]]
        layer = [round(x, 4) for x in d["layer"][k]]
        if f"RMSNorm {rms}" not in line or f"layer norm {layer}" not in line:
            raise SystemExit(f"the norms here are not the run's:\n{line}\n{rms} {layer}")
    f = Fig("vector1001", "What each norm does to one vector of four numbers: RMSNorm divides it by the root of the "
                          "mean of its squares and keeps its direction; layer norm first takes its mean away, so "
                          "[5, 6, 7, 8] comes out as low, lower, higher, highest around 0", 300)
    cols = [("the vector", "x", "s fs", "t", None),
            ("RMSNorm: x / rms(x)", "rms", "a af", "ta", None),
            ("layer norm: (x - mean) / spread", "layer", "s f", "t", None)]
    x0s = [122, 290, 458]
    for c, (title, key, cls, tcls, _) in enumerate(cols):
        f.text(x0s[c] + 70, 24, title, tcls, 11.5, "middle", 700 if key == "rms" else 600)
    for r, vec in enumerate(d["x"]):
        y0 = 92 + r * 118                        # the zero line
        n = len(vec)
        m = sum(vec) / n
        rms = math.sqrt(sum(v * v for v in vec) / n)
        f.text(20, y0 - 20, "[" + ", ".join(str(int(v)) for v in vec) + "]", "t", 12.5, weight=700, mono=True)
        f.text(20, y0 - 4, f"mean {m:g}", "tm", 10.5)
        f.text(20, y0 + 11, f"rms {rms:.4g}", "tm", 10.5)
        for c, (title, key, cls, tcls, _) in enumerate(cols):
            vals = d[key][r]
            scale = 44 / (8 if key == "x" else 1.4)
            x = x0s[c]
            f.line(x - 4, y0, x + 150, y0, "m")
            for i, v in enumerate(vals):
                bx = x + 4 + i * 37
                h = v * scale
                if abs(h) > 0.4:
                    f.rect(bx, y0 - max(h, 0), 26, abs(h), cls, 2)
                label = f"{v:g}" if key == "x" else f"{v:.2f}"
                f.text(bx + 13, y0 - h - 5 if v >= 0 else y0 - h + 13, label, tcls, 10, "middle", mono=True)
    f.text(20, 278, "Gains 1 and biases 0, as both start. RMSNorm keeps the signs and the ratios (3 : 4, "
                    "5 : 6 : 7 : 8);", "tm", 10.5)
    f.text(20, 293, "layer norm's four outputs always add up to 0.", "tm", 10.5)
    return f


def alone1001():
    out = rms_run().out
    rows = []
    for m in re.finditer(r"^   ([\d x]+) \(([\d,]+) numbers\): nn\.LayerNorm (\S+), layer norm written out (\S+), "
                         r"RMSNorm \(ours\) (\S+), nn\.RMSNorm (\S+)$", out, re.M):
        rows.append((m.group(1), m.group(2), [float(m.group(k)) for k in range(3, 7)]))
    if len(rows) != 2:
        raise SystemExit(f"rmsnorm: expected two sizes in part 2, read {rows}")
    names = [("nn.LayerNorm", "one fused kernel", "s fs", "t"),
             ("layer norm written out", "the same operations as RMSNorm, and the mean", "s f", "t"),
             ("RMSNorm (ours)", "pow, mean, rsqrt, two multiplies", "a af", "ta"),
             ("nn.RMSNorm", "PyTorch's own, on this CPU", "m fs", "t")]
    f = Fig("alone1001", "The norm alone, forward and backward, at the GPT's size and at SmolLM2's width: PyTorch's "
                         "layer norm, layer norm written out as RMSNorm is, RMSNorm, and PyTorch's RMSNorm; the median "
                         "of 100 calls taking turns, in one run with other work on the machine", 316)
    x0, W = 186, 330
    for g, (shape, count, ms) in enumerate(rows):
        y = 28 + g * 140
        what = "the GPT's activations" if g == 0 else "a batch at SmolLM2's width"
        f.text(20, y, f"{shape}: {count} numbers, {what}", "t", 11.5, weight=700)
        top = max(ms)
        for i, ((name, note, cls, tcls), v) in enumerate(zip(names, ms)):
            yy = y + 12 + i * 26
            f.text(x0 - 8, yy + 13, name, tcls, 11, "end", 700 if tcls == "ta" else None, mono=True)
            f.rect(x0, yy + 2, W * v / top, 18, cls, 2)
            f.text(x0 + W * v / top + 6, yy + 15, f"{v:.3f} ms", tcls, 10.5, mono=True)
        ratio = ms[2] / ms[1]
        f.text(620, y, f"RMSNorm / written-out layer norm: {ratio:.2f}", "ta", 10.5, "end", 600)
    f.text(20, 302, "Written alike, RMSNorm does about two thirds of the work. PyTorch's layer norm, one kernel of its "
                    "own, is faster than either.", "tm", 10.5)
    return f


def trained1001():
    r = rms_run()
    bits = compared(r, ["layer norm", "RMSNorm"])
    page = {n: spread_of(re.search(rf"^   {re.escape(n)} .*bits (.*)$", r.out, re.M).group(1)) for n in bits}
    for n, vs in bits.items():
        if f"{mean(vs):.4g}" != f"{page[n][0]:.4g}":
            raise SystemExit(f"{n}: the summaries' mean {mean(vs)} is not the run's {page[n]}")
    ms = {n: printed_ms(r.out, n) for n in bits}
    t, _ = welch(bits["RMSNorm"], bits["layer norm"])
    f = Fig("trained1001", "08.04's GPT with layer norm and with RMSNorm in every norm, 150 steps, 3 seeds: bits per "
                           "character on the test text (a ring per seed, the bar their mean), and ms a training step "
                           "(the mean of the seeds, the whisker min to max; one run, other work on the machine)", 316)
    figart.seeds_chart(f, (8, 4, 330, 290), [("layer norm", bits["layer norm"], "s"), ("RMSNorm", bits["RMSNorm"], "a")],
                       ylabel="bits per character, test text", ylim=(3.54, 3.58), yticks=[3.54, 3.55, 3.56, 3.57, 3.58])
    f.text(190, 308, f"the same bits: t = {t:+.1f}", "ta", 10.5, "middle", 600)
    top = max(v[3] for v in ms.values()) * 1.15
    ax = figart.Axes(f, 410, 26, 200, 220, (-0.5, 1.5), (0, top))
    ax.draw(xticks=[], ylabel="ms a training step")
    for i, (n, style) in enumerate((("layer norm", "s"), ("RMSNorm", "a"))):
        m_, _, lo, hi, _ = ms[n]
        X = ax.px(i)
        ax.whisker(i, [lo, hi], style, cap=6, mean=False)
        f.line(X - 14, ax.py(m_), X + 14, ax.py(m_), style)
        f.text(X + 18, ax.py(m_) + 3.5, sig(m_), TEXT[style], 10.5, mono=True)
        f.text(X, ax.y + ax.h + 15, n, TEXT[style], 11, "middle", 600 if style == "a" else None)
    ratio = ms["RMSNorm"][0] / ms["layer norm"][0]
    f.text(510, 308, f"a slower step: x{ratio:.2f} in this run", "ta", 10.5, "middle", 600)
    return f


def centring1001():
    out = rms_run().out
    rows = {m.group(1): [float(v) for v in m.group(2).split()]
            for m in re.finditer(r"^   (layer norm|RMSNorm) +((?:\d\.\d{3} *){9})$", out, re.M)}
    m = re.search(r"test text: (\d\.\d{4}) as trained, (\d\.\d{4})", out)
    trained, without = float(m.group(1)), float(m.group(2))
    if len(rows) != 2:
        raise SystemExit(f"rmsnorm: expected two rows in part 4, read {rows}")
    names = [f"{b}.{k}" for b in range(1, 5) for k in (1, 2)] + ["last"]
    f = Fig("centring1001", "How far from centred the vectors are that each norm reads, in seed 0's trained models on "
                            "125 windows of the test text: the mean of a vector over its root mean square (0: centred), "
                            "for the nine norms of each model", 300)
    ax = figart.Axes(f, 64, 40, 390, 190, (-0.5, 8.5), (0, 0.14))
    ax.draw(xticks=[], yticks=[0, 0.02, 0.04, 0.06, 0.08, 0.1, 0.12, 0.14], ylabel="|mean| / rms")
    for i, name in enumerate(names):
        X = ax.px(i)
        for k, (who, cls) in enumerate((("layer norm", "s fs"), ("RMSNorm", "a af"))):
            v = rows[who][i]
            bx = X - 15 + k * 15
            f.rect(bx, ax.py(v), 14, ax.py(0) - ax.py(v), cls, 1)
        f.text(X, ax.y + ax.h + 14, name if name == "last" else name.split(".")[0], "tm", 10, "middle", mono=True)
    f.text(ax.x + ax.w / 2, ax.y + ax.h + 30, "block (its norm1, then norm2), and the last norm", "tm", 10.5, "middle")
    x = 476
    f.rect(x, 206, 12, 12, "s fs", 1)
    f.text(x + 18, 216, "the layer-norm model's", "t", 10.5)
    f.rect(x, 224, 12, 12, "a af", 1)
    f.text(x + 18, 234, "the RMSNorm model's", "ta", 10.5)
    f.text(x, 60, "the layer-norm model,", "t", 11.5, weight=700)
    f.text(x, 76, "bits on the test text:", "t", 11.5, weight=700)
    f.text(x, 102, "as trained", "tm", 10.5)
    f.text(x + 140, 102, f"{trained:.4f}", "t", 11.5, "end", mono=True)
    f.text(x, 124, "every norm without", "ta", 10.5)
    f.text(x, 138, "its mean step", "ta", 10.5)
    f.text(x + 140, 138, f"{without:.4f}", "ta", 11.5, "end", 700, mono=True)
    f.text(x, 166, "gains and biases kept;", "tm", 10.5)
    f.text(x, 180, f"{without - trained:+.4f} bits", "tm", 10.5)
    f.text(20, 290, "Its vectors are already within 2 to 5% of centred: taking the mean away was almost doing "
                    "nothing.", "tm", 10.5)
    return f


# ------------------------------------------------------------------ 10.02

TURN_CODE = """
import json, torch
from models.gpt import Rotary
d, i = 16, 1
turn = Rotary(d)
q, k = torch.zeros(10, d, dtype=torch.float64), torch.zeros(10, d, dtype=torch.float64)
q[:, i], q[:, i + d // 2] = 1.0, 0.25
k[:, i], k[:, i + d // 2] = 0.3, -0.75
tq, tk = turn(q), turn(k)
pair = lambda t, m: [t[m, i].item(), t[m, i + d // 2].item()]
print(json.dumps({"q": pair(q, 0), "k": pair(k, 0), "tq": {m: pair(tq, m) for m in range(10)},
                  "tk": {m: pair(tk, m) for m in range(10)}, "theta": 10000.0 ** (-2 * i / d),
                  "dots": {f"{m},{n}": (tq[m] @ tk[n]).item() for m in range(10) for n in range(10)}}))
"""


def turn1002():
    d = in_project("10.02", TURN_CODE)
    th = d["theta"]
    cases = [(2, 5), (6, 9)]
    f = Fig("turn1002", f"One pair of a query's numbers and the same pair of a key's (pair 1 of a head of 16: "
                        f"{th:.3f} radians a place), turned for their places: m and n move together, the angle between "
                        f"them stays, and so does their dot product", 300)
    for c, (m, n) in enumerate(cases):
        cx, cy, R = 150 + c * 300, 140, 86
        f.circle(cx, cy, R, "m")
        f.line(cx - R - 8, cy, cx + R + 8, cy, "m")
        f.line(cx, cy - R - 8, cx, cy + R + 8, "m")
        sc = R / 1.05

        def tip(v):
            return cx + v[0] * sc, cy - v[1] * sc
        for v, cls in ((d["q"], "m"), (d["k"], "m")):
            x, y = tip(v)
            f.line(cx, cy, x, y, cls, arrow=True, dash=True)
        qx, qy = tip(d["tq"][str(m)])
        kx, ky = tip(d["tk"][str(n)])
        f.line(cx, cy, qx, qy, "a", arrow=True)
        f.line(cx, cy, kx, ky, "s", arrow=True)
        aq, ak = math.atan2(d["tq"][str(m)][1], d["tq"][str(m)][0]), math.atan2(d["tk"][str(n)][1], d["tk"][str(n)][0])
        r = 30
        f.path(f"M{cx + r * math.cos(aq):.1f} {cy - r * math.sin(aq):.1f} A {r} {r} 0 0 0 "
               f"{cx + r * math.cos(ak):.1f} {cy - r * math.sin(ak):.1f}", "a")
        for ang, label, tcls, other in ((aq, f"q at place {m}", "ta", ak), (ak, f"k at place {n}", "t", aq)):
            lx, ly = cx + (R + 12) * math.cos(ang), cy - (R + 12) * math.sin(ang) + 4
            anchor = "start" if math.cos(ang) > 0.25 else ("end" if math.cos(ang) < -0.25 else "middle")
            if abs(ang - other) < 0.6 and anchor == "middle":
                anchor = "end" if ang > other else "start"
            f.text(lx, ly, label, tcls, 10.5, anchor, 700)
        f.text(cx, 254, f"q turned by {m} x {th:.3f}, k by {n} x {th:.3f}", "tm", 10.5, "middle")
        f.text(cx, 272, f"q . k = {d['dots'][f'{m},{n}']:.6f}", "ta", 11.5, "middle", 700, mono=True)
    f.text(320, 292, "Dashed: the pair before it is turned (place 0). Both cases are 3 places apart.", "tm", 10.5,
           "middle")
    if abs(d["dots"]["2,5"] - d["dots"]["6,9"]) > 1e-12:
        raise SystemExit(f"the turned scores differ: {d['dots']['2,5']} {d['dots']['6,9']}")
    return f


ANGLES_CODE = """
import json, math, torch
from models.gpt import Rotary
d, T = 16, 64
x = torch.zeros(d // 2, T, d, dtype=torch.float64)
for i in range(d // 2):
    x[i, :, i] = 1.0
y = Rotary(d)(x)
cos = [[y[i, m, i].item() for m in range(T)] for i in range(d // 2)]
sin = [[y[i, m, i + d // 2].item() for m in range(T)] for i in range(d // 2)]
print(json.dumps({"cos": cos, "theta": [math.atan2(sin[i][1], cos[i][1]) for i in range(d // 2)]}))
"""


def angles1002():
    d = in_project("10.02", ANGLES_CODE)
    cos, theta = d["cos"], d["theta"]
    n, T = len(cos), len(cos[0])
    f = Fig("angles1002", "The angles across the width and along the window: for each of the 8 pairs of a head of 16 "
                          "numbers (base 10000), the cosine of its angle at each of 64 places; the first pair turns a "
                          "radian a place, the last a three-thousandth of one", 300)
    x0, y0, cw, ch = 152, 40, 6.0, 22
    f.text(20, 30, "pair i, radians a place", "tm", 10.5)
    f.text(x0 + T * cw + 10, 16, "turns in", "tm", 10.5)
    f.text(x0 + T * cw + 10, 30, "64 places", "tm", 10.5)
    for i in range(n):
        y = y0 + i * ch
        f.text(20, y + 15, f"pair {i}", "t", 11, mono=True)
        f.text(140, y + 15, sig(theta[i]), "ta", 10.5, "end", mono=True)
        for m in range(T):
            c = cos[i][m]
            shade(f, x0 + m * cw, y + 1, cw, ch - 2, abs(c), "fa" if c >= 0 else "fs")
            if c < 0:
                shade(f, x0 + m * cw, y + 1, cw, ch - 2, abs(c) * 0.55, "t")
        f.rect(x0, y + 1, T * cw, ch - 2, "m", 0)
        f.text(x0 + T * cw + 10, y + 15, f"{T * theta[i] / (2 * math.pi):.3g}", "t", 10.5, mono=True)
    yb = y0 + n * ch
    for m in (0, 16, 32, 48, 63):
        f.text(x0 + m * cw + cw / 2, yb + 14, str(m), "tm", 10, "middle", mono=True)
    f.text(x0 + T * cw / 2, yb + 30, "place m in the window", "tm", 10.5, "middle")
    f.rect(x0, yb + 42, 12, 12, "fa", 2, sw=False)
    f.text(x0 + 18, yb + 52, "cos near +1", "tm", 10.5)
    f.add(f'<rect class="t" x="{x0 + 110}" y="{yb + 42}" width="12" height="12" rx="2" fill-opacity="0.55"/>')
    f.text(x0 + 128, yb + 52, "cos near -1", "tm", 10.5)
    f.text(x0 + 230, yb + 52, "pair i turns m theta_i at place m,", "tm", 10.5)
    f.text(x0 + 230, yb + 67, "theta_i = 10000^(-2i / 16)", "tm", 10.5, mono=True)
    return f


OFFSET_CODE = """
import json, torch
from experiments.rotary import neighbours
from models.gpt import Rotary
d = 16
turn = Rotary(d)
g = torch.Generator().manual_seed(0)
q, k = (torch.randn(8, 40, d, dtype=torch.float64, generator=g) for _ in range(2))
scores = turn(q) @ turn(k).transpose(-2, -1)
moves = {s: (turn(q, start=s) @ turn(k, start=s).transpose(-2, -1) - scores).abs().max().item() for s in (1, 7, 1000)}
order = torch.cat([torch.arange(0, d, 2), torch.arange(1, d, 2)])
paper = neighbours(q) @ neighbours(k).transpose(-2, -1)
ours = turn(q[..., order]) @ turn(k[..., order]).transpose(-2, -1)
print(json.dumps({"moves": moves, "length": (turn(q).norm(dim=-1) - q.norm(dim=-1)).abs().max().item(),
                  "pairs": (paper - ours).abs().max().item(),
                  "unturned": (q @ k.transpose(-2, -1) - scores).abs().max().item()}))
"""


def offset1002():
    d = in_project("10.02", OFFSET_CODE)
    out = rot_run().out
    want = {"move": max(d["moves"].values()), "length": d["length"], "pairs": d["pairs"], "unturned": d["unturned"]}
    for key, pat in (("move", r"move along by 1, 7 or 1000 places +(\S+)"), ("length", r"in a vector's length +(\S+)"),
                     ("pairs", r"the numbers reordered +(\S+)"), ("unturned", r"turned and not turned +([\d.]+)")):
        if f"{want[key]:.3g}" != re.search(pat, out).group(1):
            raise SystemExit(f"rotary: {key} here {want[key]:.3g}, the run printed {re.search(pat, out).group(1)}")
    rows = [(f"both moved {s} place{'s' * (int(s) > 1)}", v, "a") for s, v in d["moves"].items()] + \
        [("a vector's length, turned", d["length"], "a"), ("the paper's pairs against ours", d["pairs"], "a"),
         ("for scale: turned against not turned", d["unturned"], "s")]
    f = Fig("offset1002", "The offset test, in float64, on 8 x 40 random queries and keys of 16: the largest change in "
                          "any score when query and key both move along, the change in a vector's length, and the two "
                          "ways of pairing the numbers; beside them, how much turning changes a score", 270)
    ax = figart.Axes(f, 250, 30, 340, 6 * 30, (1e-16, 1e2), (6, 0), logx=True)
    for e in range(-16, 3, 2):
        X = ax.px(10.0 ** e)
        f.line(X, ax.y, X, ax.y + ax.h, "m", dash=True)
        f.text(X, ax.y + ax.h + 16, f"1e{e}" if e else "1", "tm", 10, "middle", mono=True)
    for i, (name, v, style) in enumerate(rows):
        y = ax.y + 8 + i * 30
        f.text(ax.x - 10, y + 13, name, TEXT[style], 11, "end", 600 if style == "a" else None)
        w = ax.px(v) - ax.x
        f.rect(ax.x, y + 2, w, 16, "a af" if style == "a" else "s fs", 2)
        f.text(ax.x + w + 6, y + 15, sig(v), TEXT[style], 10.5, mono=True)
    f.text(20, 256, "A float64 keeps about 16 digits: a change near 1e-15 is rounding. Moving by 1000 places, the "
                    "angles' own rounding shows.", "tm", 10.5)
    return f


def parts_of(out):
    """Part 3's rows of a windows run (rotary's or 08.03's positions'): {n: [(first, last, bits)]}."""
    rows = {}
    for m in re.finditer(r"^   n = (\d): (.*)$", out, re.M):
        rows[int(m.group(1))] = [(int(a), int(b), float(v)) for a, b, v in re.findall(r"(\d+) to +(\d+): (\S+)",
                                                                                      m.group(2))]
    return rows


def longer1002():
    rot, none = parts_of(rot_run().out), parts_of(pos_run().out)
    Tr, Tn = rot[1][0][1] + 1, none[1][0][1] + 1
    f = Fig("longer1002", f"Past the length trained on, as 08.03 measured it, with rotary positions added: bits per "
                          f"character at each part of a window four times as long as the training windows; 08.03's "
                          f"model without positions (windows of {Tn}, 300 steps) and 10.02's rotary model (windows of "
                          f"{Tr}, 150 steps), seed 0 of each", 300)
    ax = figart.Axes(f, 64, 40, 400, 200, (0, 4), (3.2, 3.75))
    ax.draw(xticks=[0, 1, 2, 3, 4], yticks=[3.2, 3.3, 3.4, 3.5, 3.6, 3.7], xfmt=lambda v: f"{v:g}x",
            xlabel="place in the window, in lengths trained on", ylabel="bits per character")
    ax.vline(1)
    ax.note(1, 3.665, "the longest trained on", "tm", 10.5, "start", dx=5)
    for rows, T, style, name in ((none, Tn, "s", "no positions (08.03)"), (rot, Tr, "a", "rotary (10.02)")):
        for a, b, v in rows[4]:
            f.line(ax.px(a / T), ax.py(v), ax.px((b + 1) / T), ax.py(v), style, dash=style == "s")
            ax.note((a + b + 1) / (2 * T), v, f"{v:.3f}", TEXT[style], 10, "middle", dy=-6 if style == "a" else 14)
    f.text(484, 62, "with learned positions:", "t", 11, weight=700)
    f.text(484, 78, "no row past the last place;", "tm", 10.5)
    f.text(484, 92, "a longer window is refused", "tm", 10.5)
    f.text(484, 106, "(ValueError)", "tm", 10.5, mono=True)
    figart.legend(f, 484, 140, [("rotary (10.02)", "a", False), ("no positions (08.03)", "s", True)])
    f.text(484, 196, "Trained differently:", "tm", 10.5)
    f.text(484, 210, "compare each line's rise,", "tm", 10.5)
    f.text(484, 224, "not their levels.", "tm", 10.5)
    f.text(20, 290, "The windows of 4x are read whole, each part scored at its own places; the line at 1x is where "
                    "training stopped.", "tm", 10.5)
    return f


def held_curves(label):
    """A recorded row's validation bits: (steps, the mean over seeds, min, max)."""
    return figart.over_seeds(figart.seed_dirs(os.path.join(REC, label)), "held_bits")


def lead1002():
    xs, base, blo, bhi = held_curves("base")
    _, rot, rlo, rhi = held_curves("rotary")
    test = {k: seeds_of(os.path.join(REC, k)) for k in ("base", "rotary")}
    f = Fig("lead1002", "Rotary positions against learned ones over the recorded long run of 10.05 (4 blocks, width 128, "
                        "windows of 128, 3 seeds): bits per character on 64 validation windows every 100 steps, the "
                        "band min to max over the seeds; the lead is widest early and narrows", 300)
    keep = [i for i, x in enumerate(xs) if x >= 100]
    pick = lambda a: [a[i] for i in keep]  # noqa: E731
    series = [figart.Series("learned positions (08)", pick(xs), pick(base), "s", lo=pick(blo), hi=pick(bhi)),
              figart.Series("rotary", pick(xs), pick(rot), "a", lo=pick(rlo), hi=pick(rhi))]
    ax = figart.plot(f, (10, 8, 620, 270), series, xlabel="step (32 windows of 128 characters)",
                     ylabel="bits per character, validation", ylim=(2.0, 3.7), xlim=(100, 2000),
                     yticks=[2.0, 2.4, 2.8, 3.2, 3.6], legend="right")
    for s in (200, xs[-1]):
        i = xs.index(s)
        gap = base[i] - rot[i]
        if s < 1000:
            ax.note(s, rot[i], f"step {s}: {gap:.3f} lower", "ta", 10.5, "start", dx=4, dy=90, weight=600)
        else:
            ax.note(s, base[i], f"step {s}: {gap:.3f} lower", "ta", 10.5, "end", dx=-4, dy=-40, weight=600)
        f.line(ax.px(s), ax.py(base[i]), ax.px(s), ax.py(rot[i]), "a")
    f.text(ax.x + ax.w + 14, ax.y + 70, "test text, the end:", "tm", 10.5)
    f.text(ax.x + ax.w + 14, ax.y + 86, f"learned {mean(test['base']):.3f}", "t", 10.5, mono=True)
    f.text(ax.x + ax.w + 14, ax.y + 102, f"rotary  {mean(test['rotary']):.3f}", "ta", 10.5, mono=True)
    return f


# ------------------------------------------------------------------ 10.03

MLP_CODE = """
import json, math, torch
import torch.nn.functional as F
from models.gpt import MLP, SwiGLU, gelu
count = lambda m: sum(p.numel() for p in m.parameters())
xs = [x / 10 for x in range(-50, 31)]
t = torch.tensor(xs)
print(json.dumps({"mlp": count(MLP(64)), "glu": count(SwiGLU(64, 8 * 64 // 3)), "hidden": 8 * 64 // 3,
                  "mlp576": count(MLP(576, False)), "glu576": count(SwiGLU(576, 1536, False)),
                  "xs": xs, "gelu": gelu(t).tolist(), "silu": F.silu(t).tolist()}))
"""


def mlp1003():
    d = in_project("10.03", MLP_CODE)
    out = glu_run().out
    if f"MLP (inner  256)    {d['mlp']:,}   SwiGLU (inner  {d['hidden']})    {d['glu']:,}" not in out:
        raise SystemExit("swiglu: the weights counted here are not the run's")
    f = Fig("mlp1003", f"08.02's MLP beside the gated MLP, at the page's width of 64 with biases: two matrices "
                       f"against three, the inner width cut to two thirds so the weights match ({d['mlp']:,} against "
                       f"{d['glu']:,}); SiLU, the gate's bend, beside GELU", 330)
    def box(x, y, w, h, label, sub, cls="s f", tcls="t"):
        f.label_box(x, y, w, h, label, cls, tcls, 11.5, True, 6, 600, sub=sub)

    # 08's MLP
    y = 44
    f.text(20, 26, "08.02's MLP", "t", 12, weight=700)
    f.text(20, 40, f"{d['mlp']:,} weights a block", "tm", 10.5)
    box(20, y + 16, 52, 40, "x", "64")
    box(104, y + 16, 92, 40, "up", "64 -> 256")
    box(222, y + 16, 64, 40, "GELU", "256")
    box(312, y + 16, 92, 40, "down", "256 -> 64")
    for a, b in ((72, 104), (196, 222), (286, 312)):
        f.line(a, y + 36, b - 2, y + 36, "s", arrow=True)
    # SwiGLU
    y = 144
    f.text(20, y - 8, "SwiGLU (Shazeer 2020)", "ta", 12, weight=700)
    f.text(20, y + 6, f"{d['glu']:,} weights a block", "tm", 10.5)
    box(20, y + 50, 52, 40, "x", "64")
    box(104, y + 18, 92, 40, "gate", f"64 -> {d['hidden']}", "a af", "ta")
    box(104, y + 82, 92, 40, "up", f"64 -> {d['hidden']}")
    box(222, y + 18, 64, 40, "SiLU", str(d["hidden"]), "a af", "ta")
    f.circle(254, y + 102, 13, "a af")
    f.text(254, y + 107, "x", "ta", 14, "middle", 700, mono=True)
    box(312, y + 82, 92, 40, "down", f"{d['hidden']} -> 64")
    f.path(f"M72 {y + 70} H 86 V {y + 38} H 102", "s", arrow=True)
    f.path(f"M86 {y + 70} V {y + 102} H 102", "s", arrow=True)
    f.line(196, y + 38, 220, y + 38, "a", arrow=True)
    f.line(254, y + 58, 254, y + 87, "a", arrow=True)
    f.line(196, y + 102, 239, y + 102, "s", arrow=True)
    f.line(267, y + 102, 310, y + 102, "s", arrow=True)
    f.text(20, y + 150, "At SmolLM2's width, 576 without biases, the inner width 1536 is exactly two thirds of 2304:",
           "tm", 10.5)
    f.text(20, y + 165, f"{d['glu576']:,} weights, as many as the MLP's {d['mlp576']:,}.", "tm", 10.5)
    # the bends
    ax = figart.Axes(f, 452, 60, 160, 150, (-5, 3), (-0.6, 3))
    ax.draw(xticks=[-4, -2, 0, 2], yticks=[0, 1, 2, 3])
    f.text(452, 44, "the bends", "t", 11.5, weight=700)
    ax.curve(d["xs"], d["gelu"], "s", dash=True, width=1.5)
    ax.curve(d["xs"], d["silu"], "a", width=2)
    ax.note(-1.3, -0.28, "SiLU", "ta", 10.5, "middle", dy=16, weight=600)
    ax.note(-4.6, 0.55, "GELU, dashed", "t", 10.5, "start", weight=600)
    f.text(452, 246, "SiLU(x) = x sigmoid(x)", "ta", 10.5, mono=True)
    f.text(452, 262, "near x for large x, near 0", "tm", 10.5)
    f.text(452, 276, "far below 0, a dip between", "tm", 10.5)
    return f


def gates1003():
    out = glu_run().out
    rows = [(int(m.group(1)), float(m.group(2)), float(m.group(3)))
            for m in re.finditer(r"^   block (\d): shut (\S+), wide open (\S+)$", out, re.M)]
    if len(rows) != 4:
        raise SystemExit(f"swiglu: expected four blocks of gates, read {rows}")
    f = Fig("gates1003", "The gates of seed 0's trained SwiGLU model on 125 windows of the test text, block by block: "
                         "the share of silu(gate) under 0.1 in size (shut: that inner number is multiplied by almost "
                         "nothing), between, and over 1 (open wider than up's number)", 230)
    x0, W = 110, 420
    f.text(x0, 24, "every inner number of every position, each block", "tm", 10.5)
    for i, (b, shut, wide) in enumerate(rows):
        y = 36 + i * 36
        f.text(x0 - 10, y + 17, f"block {b}", "t", 11.5, "end", 600)
        mid = 1 - shut - wide
        f.rect(x0, y + 2, W * shut, 22, "a af", 0)
        f.rect(x0 + W * shut, y + 2, W * mid, 22, "s f", 0)
        if wide * W >= 1:
            f.rect(x0 + W * (shut + mid), y + 2, W * wide, 22, "s fs", 0)
        f.text(x0 + 6, y + 17, f"shut {shut:.3f}", "ta", 10.5, weight=700)
        f.text(x0 + W + 8, y + 17, f"over 1: {wide:.3f}", "t", 10.5)
    f.text(20, 196, "About two fifths of a deeper block's inner numbers are shut for any one character; which ones "
                    "depends on the character", "tm", 10.5)
    f.text(20, 211, "and what came before it.", "tm", 10.5)
    return f


def budget1003():
    pts = []
    base = abl_run()
    a, b = seeds_of(os.path.join(base.runs, "base")), seeds_of(os.path.join(base.runs, "SwiGLU"))
    t, se = welch(b, a)
    pts.append((80, mean(b) - mean(a), se, t, "10.05's run (2 seeds)"))
    for steps in (None, 600, 1200):
        r = glu_run(steps)
        got = compared(r, ["GELU MLP", "SwiGLU"])
        t, se = welch(got["SwiGLU"], got["GELU MLP"])
        pts.append((steps or 150, mean(got["SwiGLU"]) - mean(got["GELU MLP"]), se, t,
                    "the page's run" if steps is None else f"steps={steps}"))
    page = re.search(r"SwiGLU against the GELU MLP: bits (\S+), t = (\S+);", glu_run().out)
    if f"{pts[1][1]:+.4f}" != page.group(1):
        raise SystemExit(f"swiglu: the difference here {pts[1][1]:+.4f} is not the run's {page.group(1)}")
    xs, bm, _, _ = held_curves("base")
    _, gm, _, _ = held_curves("SwiGLU")
    test = {k: seeds_of(os.path.join(REC, k)) for k in ("base", "SwiGLU")}
    f = Fig("budget1003", "SwiGLU behind early and ahead later: its bits per character on the test text less the GELU "
                          "MLP's, at width 64 for 80 to 1200 steps (3 seeds; 2 at 80; the whisker one spread of the "
                          "difference either side); and in 10.05's recorded run, width 128, on validation every 100 "
                          "steps", 320)
    ax = figart.Axes(f, 66, 40, 260, 210, (50, 3000), (-0.08, 0.13), logx=True)
    ax.draw(xticks=[80, 150, 600, 1200], yticks=[-0.08, -0.04, 0, 0.04, 0.08, 0.12], xfmt=lambda v: f"{int(v)}",
            xlabel="steps of training, width 64", ylabel="SwiGLU less the GELU MLP")
    ax.hline(0, None, "s", dash=False)
    for steps, diff, se, t, who in pts:
        style = "a" if diff < 0 and abs(t) >= 2 else "s"
        ax.whisker(steps, [diff - se, diff + se], style, cap=5, mean=False)
        ax.dot(steps, diff, "a fa" if style == "a" else "s fs", 4)
        side, dx = ("end", -8) if steps == 600 else ("start", 8)
        ax.note(steps, diff, f"{diff:+.3f}", TEXT[style], 10, side, dx=dx, dy=4, weight=600)
        ax.note(steps, diff, f"t {t:+.1f}", "tm", 9.5, side, dx=dx, dy=17)
    f.text(ax.x + ax.w - 4, ax.y + 14, "behind (worse)", "tm", 10.5, "end")
    f.text(ax.x + 4, ax.y + ax.h - 6, "ahead (better)", "tm", 10.5)
    ax2 = figart.Axes(f, 396, 40, 220, 210, (0, 2000), (-0.18, 0.08))
    ax2.draw(xticks=[0, 500, 1000, 1500, 2000], yticks=[-0.16, -0.12, -0.08, -0.04, 0, 0.04, 0.08],
             xlabel="step, the recorded run (width 128)")
    ax2.hline(0, None, "s", dash=False)
    diff = [g - bb for g, bb in zip(gm, bm)]
    ax2.curve(xs, diff, "a", width=2)
    for x, v in zip(xs, diff):
        ax2.dot(x, v, "a fa", 2)
    end = mean(test["SwiGLU"]) - mean(test["base"])
    ax2.dot(2000, end, "s fs", 4)
    ax2.note(2000, end, f"test {end:+.3f}", "t", 10, "end", dx=-6, dy=-8, weight=600)
    ax2.note(0, diff[0], f"step 0: {diff[0]:+.3f}", "tm", 10, "start", dx=6, dy=-6)
    f.text(20, 310, "Below the line SwiGLU is ahead. Every point at width 64 is a run of experiments/swiglu.py or "
                    "experiments/ablation.py.", "tm", 10.5)
    return f


# ------------------------------------------------------------------ 10.04

def groups1004():
    out = smol_run().out
    kept = {int(m.group(1)): int(m.group(2)) for m in re.finditer(r"^   (\d) key/value heads .*kept a token +(\d+) ",
                                                                       out, re.M)}
    m = re.search(r"Its keys and values: (\d) heads of (\d+) for (\d) query heads, ([\d,]+) numbers kept a token where "
                  r"\d would keep ([\d,]+)", out)
    kv, dh, qh, few, full = int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4), m.group(5)
    f = Fig("groups1004", f"Query heads sharing key and value heads: 08.02's attention, every head its own; the page's "
                          f"run, 2 key and value heads for 4 query heads; SmolLM2-135M, {kv} for {qh}; and the numbers "
                          f"a cache of keys and values would keep for each token", 330)

    def row(y, title, nq, nk, cls, tcls, w=34, gap=8):
        f.text(20, y, title, tcls, 11.5, weight=700)
        per = nq // nk
        xs = [20 + i * (w + gap) for i in range(nq)]
        for i, x in enumerate(xs):
            f.label_box(x, y + 10, w, 24, f"q{i + 1}", "s f", "t", 10.5, True, 4)
        for j in range(nk):
            group = xs[j * per:(j + 1) * per]
            gx0, gx1 = group[0], group[-1] + w
            f.label_box(gx0, y + 62, gx1 - gx0, 24, f"k, v {j + 1}" if gx1 - gx0 > 50 else f"kv{j + 1}", cls, tcls,
                        10.5, True, 4)
            for x in group:
                f.line(x + w / 2, y + 34, x + w / 2, y + 60, tcls.replace("t", "") or "s", arrow=True)
    row(28, "08.02: 4 query heads, each its own keys and values", 4, 4, "s fs", "t")
    row(138, "kv_heads=2: query heads 1, 2 share one; 3, 4 the other", 4, 2, "a af", "ta")
    x0 = 230
    f.text(x0 + 60, 248, "numbers kept for each token, every block (a cache)", "tm", 10.5)
    bars = [("our GPT, 4 kv heads", kept[4], "s fs", "t"), ("our GPT, 2 kv heads", kept[2], "a af", "ta"),
            (f"SmolLM2 if {qh} kv heads", int(full.replace(",", "")), "s fs", "t"),
            (f"SmolLM2, {kv} kv heads", int(few.replace(",", "")), "a af", "ta")]
    for i, (name, v, cls, tcls) in enumerate(bars):
        y = 256 + i * 17
        top = kept[4] if i < 2 else int(full.replace(",", ""))
        f.text(x0 + 140, y + 11, name, tcls, 10.5, "end")
        f.rect(x0 + 148, y + 2, 190 * v / top, 12, cls, 1)
        f.text(x0 + 154 + 190 * v / top, y + 12, f"{v:,}", tcls, 10.5, mono=True)
    f.text(20, 262, f"2 x kv heads x {dh}", "tm", 10.5, mono=True)
    f.text(20, 278, "x blocks: keys and values", "tm", 10.5, mono=True)
    f.text(20, 300, "(SmolLM2: 30 blocks, heads of 64)", "tm", 10.5)
    x1 = 360
    f.text(x1, 28, f"SmolLM2-135M: {qh} query heads on {kv}", "ta", 11.5, weight=700)
    w, gap = 22, 4
    for i in range(qh):
        f.label_box(x1 + i * (w + gap), 38, w, 20, str(i + 1), "s f", "t", 9.5, True, 3)
    per = qh // kv
    for j in range(kv):
        gx0, gx1 = x1 + j * per * (w + gap), x1 + (j + 1) * per * (w + gap) - gap
        f.label_box(gx0, 84, gx1 - gx0, 20, f"k, v {j + 1}", "a af", "ta", 9.5, True, 3)
        for i in range(per):
            x = x1 + (j * per + i) * (w + gap) + w / 2
            f.line(x, 58, x, 82, "a", arrow=True)
    f.text(x1, 124, "query head h reads key and value", "tm", 10.5)
    f.text(x1, 138, f"head h // {per} (from 0): repeat_interleave", "tm", 10.5)
    return f


NAMES_CODE = """
import json, torch
from data import fetch
from lab import safetensors
from models.gpt import GPT
from models.smollm import CONFIG
header, n = safetensors.read_header(fetch.path("smollm2", "model.safetensors"))
header.pop("__metadata__", None)
with torch.device("meta"):
    model = GPT(**CONFIG)
print(json.dumps({"theirs": {k: v["shape"] for k, v in header.items()}, "dtypes": sorted({v["dtype"] for v in header.values()}),
                  "ours": {k: list(v.shape) for k, v in model.state_dict().items()},
                  "count": sum(p.numel() for p in model.parameters()), "header": n}))
"""


def names1004():
    d = in_project("10.04", NAMES_CODE)
    T, O = d["theirs"], d["ours"]
    if f"{len(T)} tensors, all {', '.join(d['dtypes'])}, read and widened to float32; {d['count']:,} weights" \
            not in smol_run().out:
        raise SystemExit("smollm: the file's tensors or the weight count are not the run's")
    rows = [("model.embed_tokens.weight", "tokens.weight", "s"),
            ("model.layers.0.input_layernorm.weight", "blocks.0.norm1.weight", "s"),
            ("model.layers.0.self_attn.q_proj.weight", "blocks.0.attention.query.weight", "s"),
            ("model.layers.0.self_attn.k_proj.weight", "blocks.0.attention.key.weight", "a"),
            ("model.layers.0.self_attn.v_proj.weight", "blocks.0.attention.value.weight", "a"),
            ("model.layers.0.self_attn.o_proj.weight", "blocks.0.attention.out.weight", "s"),
            ("model.layers.0.post_attention_layernorm.weight", "blocks.0.norm2.weight", "s"),
            ("model.layers.0.mlp.gate_proj.weight", "blocks.0.mlp.gate.weight", "a"),
            ("model.layers.0.mlp.up_proj.weight", "blocks.0.mlp.up.weight", "s"),
            ("model.layers.0.mlp.down_proj.weight", "blocks.0.mlp.down.weight", "s"),
            ("model.norm.weight", "norm.weight", "s")]
    for theirs, ours, _ in rows:
        assert theirs in T and ours in O, (theirs, ours)
        assert T[theirs] == O[ours], (theirs, T[theirs], O[ours])
    f = Fig("names1004", f"SmolLM2-135M's file beside the GPT that holds it, for block i of 30: every tensor goes in "
                         f"as it is, only renamed; in the accent the shapes 08's GPT never had (keys and values of 3 "
                         f"heads, the gate)", 404)
    xl, xm, xr = 20, 342, 392
    f.text(xl, 20, f"model.safetensors: {len(T)} tensors, all {', '.join(d['dtypes'])}", "t", 11.5, weight=700)
    f.text(xm, 20, "shape", "tm", 10.5, "middle")
    f.text(xr, 20, "models/gpt.py's GPT(**CONFIG)", "t", 11.5, weight=700)
    y = 34
    for theirs, ours, style in rows:
        tcls = TEXT[style]
        f.text(xl, y + 12, theirs.replace("layers.0.", "layers.i."), tcls, 10, weight=600 if style == "a" else None,
               mono=True)
        f.text(xr, y + 12, ours.replace("blocks.0.", "blocks.i."), tcls, 10, weight=600 if style == "a" else None,
               mono=True)
        f.text(xm, y + 12, str(T[theirs]), tcls, 10, "middle", mono=True)
        y += 26
    f.text(xl, y + 12, "(no lm_head: the output is the embedding, tied)", "tm", 10.5)
    f.text(xr, y + 12, "(GPT's scores: x @ tokens.weight.T)", "tm", 10.5)
    y += 34
    f.text(xl, y, "Every weight is kept as nn.Linear keeps it, (outputs, inputs): nothing is transposed, where GPT-2's "
                  "file", "tm", 10.5)
    f.text(xl, y + 15, f"needed every matrix turned. No biases. Each BF16 number is widened to float32: "
                       f"{d['count']:,} weights.", "tm", 10.5)
    return f


TOKENS_CODE = """
import json
from tokens import gpt2, smollm
S, G = smollm.load(), gpt2.load()
out = []
for s in SENTENCES:
    out.append({"s": s, "smol": [[p, S.encode(p)] for p in smollm.split(s)], "gpt2": [[p, G.encode(p)] for p in gpt2.split(s)],
                "ids": S.encode(s)})
print(json.dumps(out))
"""


def tokens1004():
    out = smol_run().out
    prompt = re.search(r'^5\. After "(.*)" \(a speech', out, re.M).group(1).encode().decode("unicode_escape")
    sentences = [" in 2019, 1234567890", prompt]
    d = in_project("10.04", TOKENS_CODE.replace("SENTENCES", repr(sentences)))
    printed = re.search(r"^   ' in 2019, 1234567890': pieces (\[.*?\]), tokens (\[.*?\])", out, re.M)
    if [p for p, _ in d[0]["smol"]] != eval(printed.group(1)) or d[0]["ids"] != json.loads(printed.group(2)):
        raise SystemExit("smollm: the pieces and tokens here are not the run's")
    f = Fig("tokens1004", "SmolLM2's tokenizer beside GPT-2's on two pieces of text: the same pattern cuts both, but "
                          "SmolLM2 cuts every digit out first; each piece in a box, its ids under it", 356)
    y = 22
    for k, s in enumerate(d):
        f.text(20, y, "'" + shown(s['s'], ' ') + "'", "t", 11.5, weight=700, mono=True)
        y += 12
        for who, key, cls, tcls in (("GPT-2", "gpt2", "s f", "t"), ("SmolLM2", "smol", "a af", "ta")):
            f.text(20, y + 15, who, tcls, 11, weight=700)
            x = 86
            n = 0
            for p, ids in s[key]:
                idt = " ".join(map(str, ids))
                w = max(tw(shown(p), 10.5, True) + 10, tw(idt, 9, True) + 4, 16)
                if x + w > 626:
                    x, y = 86, y + 42
                f.rect(x, y + 2, w, 20, cls, 3)
                f.text(x + w / 2, y + 16, shown(p), tcls, 10.5, "middle", mono=True)
                f.text(x + w / 2, y + 34, idt, "tm", 9, "middle", mono=True)
                x += w + 3
                n += len(ids)
            f.text(20, y + 30, f"{n} ids", "tm", 10)
            y += 46
        y += 12
    bpt = re.search(r"(\d\.\d{3}) bytes a token \(GPT-2's (\d\.\d{3})\)", out)
    f.h = y + 22
    f.text(20, y + 8, f"_ is a space. On the whole test text: SmolLM2 {bpt.group(1)} characters a token, GPT-2 "
                    f"{bpt.group(2)}.", "tm", 10.5)
    return f


def ladder1004():
    out = ladder_run().out
    part = out.split("Beside the track's own models")[1].split("\n\n")[0]
    rows = [(m.group(1).strip(), float(m.group(2))) for m in re.finditer(r"^   (.+?) +(\d\.\d{3})$", part, re.M)]
    if len(rows) != 7:
        raise SystemExit(f"gpt2: expected 7 rows on the ladder, read {rows}")
    smol = re.search(r"^   SmolLM2-135M +(\d\.\d{3}) +([\d,]+) weights$", smol_run().out, re.M)
    weights = {m.group(1).strip(): m.group(3) for m in re.finditer(r"^   (.+?) +(\d\.\d{3}) +([\d,]+) weights$",
                                                                    smol_run().out, re.M)}
    g2 = re.search(r"^   GPT-2 small \(09\.03\) +(\d\.\d{3})", smol_run().out, re.M).group(1)
    if f"{rows[-1][1]:.3f}" != g2:
        raise SystemExit(f"GPT-2's bits on the ladder ({rows[-1][1]}) are not smollm's ({g2})")
    rows.append(("SmolLM2-135M, trained by Hugging Face on 2 trillion tokens", float(smol.group(1))))
    wt = {"08.04's GPT, its long run (dropout 0.2)": weights["08.04's GPT, its long run (dropout 0.2)"],
          "GPT-2 small, never trained on this text by us": weights["GPT-2 small (09.03)"],
          rows[-1][0]: smol.group(2)}
    f = Fig("ladder1004", "Bits per character on Tiny Shakespeare's test text: the ladder of modules 07 and 08, each "
                          "trained here on the training plays, GPT-2 small (09.03), and SmolLM2-135M, with the weights "
                          "of each model", 18 * 8 + 96)
    x0, x1 = 300, 520
    lo, hi = 1.2, 3.8
    ax = figart.Axes(f, x0, 30, x1 - x0, 18 * 8 + 12, (lo, hi), (8, 0))
    ax.draw(xticks=[1.4, 1.8, 2.2, 2.6, 3.0, 3.4, 3.8], yticks=[], xlabel="bits per character on the test text")
    f.text(x1 + 12, 26, "weights", "tm", 10.5)
    for i, (name, b) in enumerate(rows):
        y = ax.y + 14 + i * 18
        smol_row = name.startswith("SmolLM2")
        cls = "ta" if smol_row else "t"
        f.text(x0 - 8, y + 4, name.replace(", trained by Hugging Face on 2 trillion tokens", ""), cls, 10.5, "end",
               700 if smol_row else None)
        if name in wt:
            f.text(x1 + 12, y + 4, wt[name], cls, 10, mono=True)
        if b > hi:
            f.line(x1 - 30, y, x1 - 4, y, "m", arrow=True)
            f.text(x1 - 34, y + 4, f"{b:.3f}", "tm", 9.5, "end", mono=True)
            continue
        f.circle(ax.px(b), y, 4 if smol_row else 3.5, "a fa" if smol_row else "s fs")
        f.text(ax.px(b) + 9, y + 4, f"{b:.3f}", cls, 10, weight=700 if smol_row else None, mono=True)
    return f


# ------------------------------------------------------------------ 10.05

def recorded_rows():
    """The recorded table, from every seed's summary: {name: (bits by seed, weights)}; checked against output.txt."""
    with open(os.path.join(REC, "output.txt")) as fh:
        printed = fh.read()
    rows = {}
    for n in ROWS:
        d = os.path.join(REC, n.replace(" (08)", "").replace(" ", "-"))
        vals = seeds_of(d)
        w = figart.summary(figart.seed_dirs(d)[0])["weights"]
        line = re.search(rf"^   {re.escape(n)} +([\d,]+)   (\S+) \+-", printed, re.M)
        if line.group(1) != f"{w:,}" or line.group(2) != f"{mean(vals):.4g}":
            raise SystemExit(f"recorded {n}: the summaries ({w:,}, {mean(vals):.4g}) are not output.txt's {line.groups()}")
        rows[n] = (vals, w)
    return rows


def short_rows():
    r = abl_run()
    out = {}
    for n in ROWS:
        d = os.path.join(r.runs, n.replace(" (08)", "").replace(" ", "-"))
        out[n] = (seeds_of(d), figart.summary(figart.seed_dirs(d)[0])["weights"])
        line = re.search(rf"^   {re.escape(n)} +([\d,]+)   (\S+) \+-", r.out, re.M)
        if line.group(2) != f"{mean(out[n][0]):.4g}":
            raise SystemExit(f"ablation {n}: {mean(out[n][0]):.4g} is not the run's {line.group(2)}")
    return out


STYLE = {"base (08)": "s", "RMSNorm": "m", "rotary": "a", "SwiGLU": "a", "grouped-query": "m", "all four": "a"}


def table1005():
    rows = recorded_rows()
    base = rows["base (08)"][0]
    f = Fig("table1005", "The recorded ablation (4 blocks, width 128, windows of 128, 2000 steps, 3 seeds a row): bits "
                         "per character on the test text, a ring per seed, the bar their mean, the whisker min to max; "
                         "under each row its weights, and its difference from the base with Welch's t", 330)
    groups = []
    for n in ROWS:
        vals, w = rows[n]
        if n == "base (08)":
            style = "s"
        else:
            t, _ = welch(vals, base)
            style = "a" if abs(t) >= 3 else "m"
        groups.append((n, vals, style))
    ax = figart.seeds_chart(f, (8, 4, 624, 268), [(n.replace("grouped-query", "grouped"), v, s) for n, v, s in groups],
                            ylabel="bits per character, test text", ylim=(2.22, 2.37),
                            yticks=[2.22, 2.25, 2.28, 2.31, 2.34, 2.37])
    ax.hline(mean(base), "the base's mean", "s", dash=True, side="right")
    for i, (n, vals, style) in enumerate(groups):
        X = ax.px(i)
        y = ax.y + ax.h + 30
        f.text(X, y, f"{rows[n][1]:,}", "tm", 10, "middle", mono=True)
        if n != "base (08)":
            t, _ = welch(vals, base)
            f.text(X, y + 15, f"{mean(vals) - mean(base):+.3f}, t {t:+.1f}", TEXT[style], 10, "middle",
                   700 if style == "a" else None, mono=True)
            f.text(X, y + 29, "beyond noise" if abs(t) >= 3 else "not beyond", TEXT[style], 10, "middle")
    return f


def flip1005():
    short, long_ = short_rows(), recorded_rows()
    f = Fig("flip1005", "Each change's difference from the base, in the page's short run (width 64, 80 steps, 2 seeds) "
                        "and in the recorded long run (width 128, 2000 steps, 3 seeds): a dot the difference of the "
                        "means, the whisker one spread of it either side; in the accent where |t| is 3 or more", 300)
    changes = ROWS[1:]
    for p, (title, rows, lim, ticks) in enumerate((("the page's run: 80 steps", short, (-0.3, 0.15),
                                                    [-0.3, -0.2, -0.1, 0, 0.1]),
                                                   ("the recorded run: 2000 steps", long_, (-0.12, 0.06),
                                                    [-0.12, -0.08, -0.04, 0, 0.04]))):
        x0 = 120 + p * 262
        ax = figart.Axes(f, x0, 40, 220, 5 * 38, lim, (5, 0))
        ax.draw(xticks=ticks, yticks=[], xfmt=lambda v: f"{v:+.2g}" if v else "0", xlabel="less the base, bits")
        f.text(x0, 30, title, "t", 11.5, weight=700)
        f.line(ax.px(0), ax.y, ax.px(0), ax.y + ax.h, "s")
        base = rows["base (08)"][0]
        for i, n in enumerate(changes):
            y = ax.y + 19 + i * 38
            if p == 0:
                f.text(x0 - 10, y + 4, n, "t", 11, "end", 600)
            vals = rows[n][0]
            t, se = welch(vals, base)
            diff = mean(vals) - mean(base)
            style = "a" if abs(t) >= 3 else "m"
            lo, hi = max(diff - se, lim[0]), min(diff + se, lim[1])
            f.line(ax.px(lo), y, ax.px(hi), y, style)
            f.circle(ax.px(diff), y, 4, "a fa" if style == "a" else "m fs")
            if (diff < 0 or ax.px(hi) + 48 > ax.x + ax.w) and ax.px(lo) - 52 > ax.x:
                lx, anchor = ax.px(lo) - 7, "end"
            else:
                lx, anchor = ax.px(hi) + 7, "start"
            f.text(lx, y + 4, f"{diff:+.3f}", TEXT[style], 10, anchor, 700 if style == "a" else None, mono=True)
    f.text(20, 290, "Left of the line is better than the base. The same five changes, ranked otherwise by the budget: "
                    "SwiGLU from worst to best.", "tm", 10.5)
    return f


def curves1005():
    xs, base, _, _ = held_curves("base")
    f = Fig("curves1005", "Each change's validation bits less the base's, over the recorded long run (the mean of 3 "
                          "seeds, 64 validation windows every 100 steps): rotary's lead shrinks, SwiGLU's holds, "
                          "RMSNorm and grouped heads stay near 0", 320)
    series = []
    for n, style, dash in (("RMSNorm", "m", False), ("grouped-query", "m", True), ("rotary", "a", False),
                           ("SwiGLU", "s", False), ("all four", "a", True)):
        _, m, _, _ = held_curves(n.replace(" ", "-"))
        diff = [a - b for a, b in zip(m, base)]
        series.append(figart.Series(n, xs[1:], diff[1:], style, dash))
    ax = figart.plot(f, (10, 8, 620, 300), series, xlabel="step (the recorded run, width 128)",
                     ylabel="validation bits less the base's", ylim=(-0.62, 0.08), xlim=(100, 2000),
                     yticks=[-0.6, -0.5, -0.4, -0.3, -0.2, -0.1, 0], legend="end")
    ax.hline(0, None, "s", dash=False)
    return f


FIGS = [
    ("10.01-vector", vector1001),
    ("10.01-alone", alone1001),
    ("10.01-trained", trained1001),
    ("10.01-centring", centring1001),
    ("10.02-turn", turn1002),
    ("10.02-angles", angles1002),
    ("10.02-offset", offset1002),
    ("10.02-longer", longer1002),
    ("10.02-lead", lead1002),
    ("10.03-mlp", mlp1003),
    ("10.03-gates", gates1003),
    ("10.03-budget", budget1003),
    ("10.04-groups", groups1004),
    ("10.04-names", names1004),
    ("10.04-tokens", tokens1004),
    ("10.04-ladder", ladder1004),
    ("10.05-table", table1005),
    ("10.05-flip", flip1005),
    ("10.05-curves", curves1005),
]


def main():
    only = sys.argv[1:]
    for name, fn in FIGS:
        if only and not any(name.startswith(o) for o in only):
            continue
        print(write(MOD, name, fn()))


if __name__ == "__main__":
    main()
