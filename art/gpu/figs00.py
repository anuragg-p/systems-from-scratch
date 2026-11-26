"""Figures for gpu module 00, the workbench (plans/gpu-00-01-lessons.md, the "Figures:" entries).

    python3 -B art/gpu/figs00.py [name-prefix ...]
        writes tracks/gpu/lessons/00-the-workbench/figures/00.0N-*.svg (the maps are archmap.py's)

Each figure's <title> is its caption from the design; the lesson carries the caption itself. What
each one draws is checked against the design's values and against the track's code
(tracks/gpu/*.c), so a change to either stops this script instead of reaching a figure:

  00.01-two-versions   add's loop run on n = 11, as add.c writes it (i + 4 <= n, i += 4): passes at
                       0 and 4, the tail 8, 9, 10; add_ref takes the 11 one at a time
  00.01-seed           rng.c: three shifts XORed back (12, 25, 27), the product's top 32 bits, the
                       top 24 of those over 2^24 = 16777216, then 2x - 1; the seed is the first state
  00.02-allowance      check.c's rule, allowed = atol + rtol * |want|, with rtol 1e-4 and atol 1e-3
                       in exact fractions: want 20 allows 0.003 and got 20.002 is good; want 0
                       allows 0.001 and got 0.002 is bad
  00.03-runs           the warm-up and six timed runs of the module's cover (gpu_art.TIMED, lengths
                       only, never a number); the median is bench.c's (the mean of the two middle
                       runs for an even count)
"""
import os
import re
import sys
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from figlib import G, Art, cell, sans, cw, r1, source, write  # noqa: E402

L, R = 16, 624


def both_ends(a, x1, y1, x2, y2, cls="m"):
    """A dimension line: an arrowhead at each end (the markers are orient="auto-start-reverse")."""
    mk = f"url(#{a.key}-{a.marker(cls)})"
    a.add(f'<line class="{cls}" x1="{r1(x1)}" y1="{r1(y1)}" x2="{r1(x2)}" y2="{r1(y2)}" stroke-width="1.5" '
          f'stroke-linecap="round" marker-start="{mk}" marker-end="{mk}"/>')


def bracket(a, x1, x2, y, cls="m", h=6):
    """A bracket over x1..x2, its feet down at y."""
    a.path(f"M{r1(x1)} {y}V{y - h}H{r1(x2)}V{y}", cls)


# ====================================================================== 00.01

def two_versions():
    n = 11
    src = source("add.c")
    assert "for (; i + 4 <= n; i += 4)" in src and "for (; i < n; i++)" in src
    passes, i = [], 0
    while i + 4 <= n:                                   # add's first loop
        passes.append(i)
        i += 4
    tail = list(range(i, n))                            # its second
    assert passes == [0, 4] and tail == [8, 9, 10], (passes, tail)

    a = Art("twov", "The same eleven sums, one at a time and four at a time", 156)
    w, h, x0 = 44, 30, 104
    assert x0 + n * w <= R - 20

    def row(y, name, hot):
        a.text(x0 - 14, y + h / 2 + 4.5, name, "t", 13, "end", 700, mono=True)
        assert x0 - 14 - len(name) * cw(13) >= L
        for k in range(n):
            on = k in hot
            cell(a, x0 + k * w, y, w, h, str(k), "a af" if on else "s f", "ta" if on else "t", 12, rx=0,
                 weight=700 if on else None)

    # add_ref: eleven single steps
    y1 = 24
    for k in range(n):
        bracket(a, x0 + k * w + 5, x0 + (k + 1) * w - 5, y1 - 6, "s")
    row(y1, "add_ref", [])
    # add: two passes of four, then the tail one at a time
    y2 = 110
    for p in passes:
        lo, hi = x0 + p * w + 5, x0 + (p + 4) * w - 5
        bracket(a, lo, hi, y2 - 6, "s")
        a.text(r1((lo + hi) / 2), y2 - 18, "one pass", "t", 12, "middle", 600)
    for k in tail:
        bracket(a, x0 + k * w + 5, x0 + (k + 1) * w - 5, y2 - 6, "a")
    tx = x0 + (tail[0] + tail[-1] + 1) * w / 2
    s = "the tail, one at a time"
    a.text(r1(tx), y2 - 18, s, "ta", 12, "middle", 700)
    last_pass = x0 + (passes[-1] + 2) * w + sans("one pass", 12) / 2    # the right end of the last "one pass"
    assert tx + sans(s, 12) / 2 <= R and tx - sans(s, 12) / 2 >= last_pass + 8
    row(y2, "add", tail)
    assert y2 + h + 16 <= a.h
    return a


def seed():
    src = source("rng.c")
    shifts = re.findall(r"x \^= x (>>|<<) (\d+);", src)
    assert shifts == [(">>", "12"), ("<<", "25"), (">>", "27")], shifts
    state_bits = int(re.search(r"uint(\d+)_t x = \*state;", src).group(1))
    top = int(re.search(r"0x2545F4914F6CDD1DULL\) >> (\d+)\)", src).group(1))
    m = re.search(r"\(float\)\(rng_u32\(state\) >> (\d+)\) / (\d+)\.0f", src)
    keep, over = 32 - int(m.group(1)), int(m.group(2))
    assert "x[i] = 2 * rng_f32(&state) - 1;" in src and "uint64_t state = seed;" in src
    assert (state_bits, len(shifts), top, keep, over) == (64, 3, 32, 24, 2 ** 24)
    assert 32 == 64 - top                                # the top half of the 64-bit product
    steps = [
        ["state:", f"{state_bits} bits"],
        ["three shifts,", "each XORed back"],
        ["times a constant,", f"top {64 - top} bits"],
        [f"top {keep} bits / 2^{keep}:", "a float in [0, 1)"],
        ["2x - 1:", "in [-1, 1)"],
    ]
    hot = 3

    a = Art("seed", "From a seed to a float", 124)
    size, pad, by, bh = 11.5, 16, 22, 48
    ws = [max(sans(t, size) for t in lines) + pad for lines in steps]
    gap = (R - L - sum(ws)) / (len(steps) - 1)
    assert gap >= 20, gap
    x, xs = L, []
    for k, (lines, w) in enumerate(zip(steps, ws)):
        on = k == hot
        a.box(r1(x), by, r1(w), bh, "a af" if on else "s f", rx=8)
        for j, t in enumerate(lines):
            a.text(r1(x + w / 2), by + 20 + j * 16, t, "ta" if on else "t", size, "middle", 700 if on else 500)
        if k:
            a.line(r1(x - gap + 3), by + bh / 2, r1(x - 3), by + bh / 2, arrow=True)
        xs.append(x)
        x += w + gap
    assert abs(x - gap - R) < 0.01
    # the seed comes in from below
    c0 = xs[0] + ws[0] / 2
    a.line(r1(c0), by + bh + 26, r1(c0), by + bh + 3, arrow=True)
    a.text(L, by + bh + 44, "the seed is the first state", "t", 12, weight=600)
    assert by + bh + 44 + 8 <= a.h
    return a


# ====================================================================== 00.02

def fmt(v):
    """A Fraction as the design writes it: 20, 19.997, -0.001."""
    s = f"{float(v):.3f}".rstrip("0").rstrip(".")
    assert Fraction(s) == v, (v, s)
    return "0" if s == "-0" else s


def allowance():
    src = source("check.c")
    assert "atol + rtol * fabs(w)" in src and "!(err <= allowed)" in src
    rtol, atol = Fraction("1e-4"), Fraction("1e-3")
    cases = []                                          # (want, got, allowed, good)
    for want, got in ((Fraction(20), Fraction("20.002")), (Fraction(0), Fraction("0.002"))):
        allowed = atol + rtol * abs(want)
        cases.append((want, got, allowed, abs(got - want) <= allowed))
    assert [(c[2], c[3]) for c in cases] == [(Fraction(3, 1000), True), (Fraction(1, 1000), False)], cases

    a = Art("allow", "What counts as close: the allowance around want", 252)
    unit = Fraction(1, 1000)
    k, span = 40, 5                                     # px per 0.001; the axis runs want +- 5 of them
    cx = 352
    assert cx - span * k >= 140 and cx + span * k <= R - 40

    def px(v, want):
        return cx + float((v - want) / unit) * k

    for row, (want, got, allowed, good) in enumerate(cases):
        y0 = 8 + row * 108
        ay = y0 + 46                                    # the axis
        lo, hi = want - allowed, want + allowed
        # the band, then the axis and its ticks over it
        a.box(r1(px(lo, want)), ay - 12, r1(px(hi, want) - px(lo, want)), 24, "s fs", rx=3)
        a.line(cx - span * k, ay, cx + span * k, ay, "m")
        for t in range(-span, span + 1):
            v = want + t * unit
            major = v in (lo, want, hi)
            a.line(r1(px(v, want)), ay - (6 if major else 3), r1(px(v, want)), ay + (6 if major else 3),
                   "s" if major else "m", width=1.5 if major else 1)
        for v in (lo, want, hi):
            a.text(r1(px(v, want)), ay + 26, fmt(v), "t", 11.5 if v == want else 11, "middle",
                   700 if v == want else None, mono=True)
        a.text(L, ay + 4, f"want = {fmt(want)}", "t", 12.5, weight=700, mono=True)
        assert L + len(f"want = {fmt(want)}") * cw(12.5) + 12 <= cx - span * k
        # the allowance: from want to the band's edge, labelled
        both_ends(a, px(want, want) + 1, ay - 20, px(hi, want) - 1, ay - 20, "s")
        label = f"atol + rtol x {fmt(want)} = {fmt(allowed)}" if want else f"atol alone = {fmt(allowed)}"
        assert want or rtol * abs(want) == 0
        lx = (px(want, want) + px(hi, want)) / 2
        a.text(r1(lx), ay - 28, label, "t", 12, "middle", 600)
        assert lx - sans(label, 12) / 2 >= 140
        # got: on the axis, its label under the tick labels on a leader
        gx = px(got, want)
        for v in (lo, want, hi):                        # the leader clears the tick labels
            assert abs(gx - px(v, want)) > len(fmt(v)) * cw(11) / 2 + 6, v
        cls, tcls, verdict = ("s f", "t", "good") if good else ("a fa", "ta", "bad")
        a.line(r1(gx), ay + 7, r1(gx), ay + 34, "a" if not good else "s", width=1)
        a.circle(r1(gx), ay, 5.5, cls)
        a.text(r1(gx), ay + 50, f"got {fmt(got)}: {verdict}", tcls, 12, "middle", 700)
        inside = lo <= got <= hi
        assert inside == good
    assert (rtol, atol) == (Fraction(1, 10 ** 4), Fraction(1, 10 ** 3))
    foot = "rtol = 1e-4, atol = 1e-3"
    a.text(320, 240, foot, "tm", 12, "middle", mono=True)
    return a


# ====================================================================== 00.03

def runs():
    src = source("bench.c")
    assert "(times[r.runs / 2 - 1] + times[r.runs / 2]) / 2" in src
    assert src.index("    fn(arg);\n    bench_result") < src.index("while (r.runs < o.max_runs")   # the warm-up call
    fastest, med = G.runs_check()
    timed = G.TIMED
    assert med == G.runs_median(timed) and abs(med - (sorted(timed)[2] + sorted(timed)[3]) / 2) < 1e-12

    a = Art("runs", "One measurement: a run thrown away, then the fastest of the rest", 236)
    x0, Lw = 176, 340                                   # where every run starts; the warm-up's length
    wy, ty, bh, pitch, ay = 16, 48, 16, 24, 200
    ends = [x0 + t * Lw for t in timed]
    assert ty + 5 * pitch + bh + 12 <= ay
    a.box(x0, wy, Lw * G.WARMUP, bh, "m f", rx=3, dash=True)
    for k, end in enumerate(ends):
        if k != fastest:
            a.box(x0, ty + k * pitch, r1(end - x0), bh, "s fs", rx=3)
    a.box(x0, ty + fastest * pitch, r1(ends[fastest] - x0), bh, "a af", rx=3)
    for s, y, cls, wt in (("warm-up: not counted", wy, "tm", 500), ("the fastest: reported", ty + fastest * pitch, "ta", 700)):
        a.text(x0 - 12, y + bh / 2 + 4.2, s, cls, 12, "end", wt)
        assert x0 - 12 - sans(s, 12) >= L, s
    bx = r1(max(ends) + 14)                             # "timed runs": a bracket round the six
    yt, yb = ty - 3, ty + 5 * pitch + bh + 3
    a.path(f"M{bx - 6} {yt}H{bx}V{yb}H{bx - 6}", "m")
    a.text(bx + 10, r1((yt + yb) / 2 + 4), "timed runs", "t", 12, weight=600)
    assert bx + 10 + sans("timed runs", 12) <= R
    # the time axis: every run drawn from its own start
    xe = x0 + Lw * G.WARMUP + 40
    a.path(f"M{x0} {wy - 6}V{ay}H{xe}", arrow=True)
    a.text(xe + 8, ay + 4, "time", "tm", 11.5)
    assert xe + 8 + sans("time", 11.5) <= R
    # the median: a tick on the axis, and a guide up through the timed runs
    xm = r1(x0 + med * Lw)
    a.line(xm, ty - 6, xm, ay - 2, "m", dash=True, width=1.75)
    a.line(xm, ay - 6, xm, ay + 6, "s")
    s = "the median: printed beside it"
    a.text(xm, ay + 24, s, "t", 12, "middle", 600)
    assert xm - sans(s, 12) / 2 >= L and xm + sans(s, 12) / 2 <= R and ay + 24 + 8 <= a.h
    # the guide meets the fastest run's row only past its end, clear of its label
    assert ends[fastest] < xm
    return a


FIGURES = [
    ("00.01-two-versions", two_versions),
    ("00.01-seed", seed),
    ("00.02-allowance", allowance),
    ("00.03-runs", runs),
]


def main(argv):
    for name, fn in FIGURES:
        if argv and not any(name.startswith(p) for p in argv):
            continue
        write(name, fn())


if __name__ == "__main__":
    main(sys.argv[1:])
