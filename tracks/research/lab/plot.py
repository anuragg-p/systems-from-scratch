"""Line plots as SVG files, drawn from the numbers of real runs.

    lines("runs/curve/loss.svg", [Line("seed 0", steps, losses), ...], xlabel="step", ylabel="loss", logy=True)

writes one SVG: axes with round-numbered ticks, one line per series, and a
legend. Several runs of the same setting share a colour (Line's color is a
number into PALETTE), so five seeds read as one band. A value that is not a
finite number (a run that diverged) breaks its line rather than stretching
the axes to infinity.

It writes plain SVG elements only (lines, polylines, text) with the text in
currentColor, so the same file is a lesson figure on the site, in light and
dark.
"""

import math
import os

PALETTE = ["#1f77b4", "#d62728", "#2ca02c", "#ff7f0e", "#9467bd", "#8c564b", "#e377c2", "#17becf"]
MAX_POINTS = 400        # per line: a longer line is thinned to this many points


class Line:
    """One series: a label (shown once per colour in the legend), its x and y values, a colour
    (an index into PALETTE, or "#rrggbb"), and how strongly it is drawn."""

    def __init__(self, label, x, y, color=0, opacity=1.0, dashed=False):
        self.label, self.x, self.y = label, list(x), list(y)
        self.color = PALETTE[color % len(PALETTE)] if isinstance(color, int) else color
        self.opacity, self.dashed = opacity, dashed


# @build 00.03 ticks
# About n round numbers from lo to hi for an axis: a step of 1, 2 or 5 times
# a power of ten, the smallest such step that gives at most n + 1 ticks, and
# every multiple of it inside [lo, hi]. On a log axis, the powers of ten
# inside the range (and 2 and 5 times them when there are fewer than three).
def ticks(lo, hi, n=5, log=False):
    if log:
        out = [10.0 ** k for k in range(math.floor(math.log10(lo)), math.ceil(math.log10(hi)) + 1)]
        if len([t for t in out if lo <= t <= hi]) < 3:
            out = [m * t for t in out for m in (1, 2, 5)]
        return [t for t in out if lo * (1 - 1e-9) <= t <= hi * (1 + 1e-9)]
    if hi <= lo:
        return [lo]
    raw = (hi - lo) / n
    power = 10.0 ** math.floor(math.log10(raw))
    step = next(m * power for m in (1, 2, 5, 10) if m * power >= raw)
    first = math.ceil(lo / step - 1e-9)
    return [k * step for k in range(first, math.floor(hi / step + 1e-9) + 1)]
# @end


def _label(v):
    """A tick's text: as few digits as it needs."""
    if v == 0:
        return "0"
    if abs(v) >= 1e5 or abs(v) < 1e-3:
        return f"{v:.0e}".replace("e-0", "e-").replace("e+0", "e")
    return f"{v:.6g}"


def _thin(xs, ys):
    if len(xs) <= MAX_POINTS:
        return xs, ys
    k = math.ceil(len(xs) / MAX_POINTS)
    keep = list(range(0, len(xs), k))
    if keep[-1] != len(xs) - 1:
        keep.append(len(xs) - 1)
    return [xs[i] for i in keep], [ys[i] for i in keep]


def _esc(text):
    return str(text).replace("&", "and").replace("<", "(").replace(">", ")")


# @build 00.03 lines
# Write the plot to path (making its directory) and return path. The axes
# span the finite values of every series (on logy, the positive ones), with
# a little room; ylim=(lo, hi) fixes the y range instead, and a point
# outside it is left out. Each series is a polyline in data coordinates
# mapped to the plot area, broken where a value is left out. Ticks and their
# labels come from ticks(); the legend lists each label once, in its colour.
def lines(path, series, title="", xlabel="", ylabel="", logx=False, logy=False, ylim=None,
          width=640, height=360):
    left, right, top, bottom = 64, 150, 34, 46
    pw, ph = width - left - right, height - top - bottom

    def ok(v, log):
        return isinstance(v, (int, float)) and math.isfinite(v) and (v > 0 or not log)

    xs = [x for s in series for x in s.x if ok(x, logx)]
    ys = [y for s in series for x, y in zip(s.x, s.y) if ok(y, logy) and ok(x, logx)]
    if ylim:
        ys = [y for y in ys if ylim[0] <= y <= ylim[1]]
    if not xs or not ys:
        raise ValueError(f"{path}: nothing finite to plot")
    x0, x1 = min(xs), max(xs)
    y0, y1 = ylim if ylim else (min(ys), max(ys))
    fx = (lambda v: math.log10(v)) if logx else (lambda v: v)
    fy = (lambda v: math.log10(v)) if logy else (lambda v: v)
    if not ylim:
        pad = (fy(y1) - fy(y0)) * 0.05 or 0.5
        y0 = 10 ** (fy(y0) - pad) if logy else y0 - pad
        y1 = 10 ** (fy(y1) + pad) if logy else y1 + pad
    if x1 == x0:
        x0, x1 = (x0 / 2, x0 * 2) if logx else (x0 - 1, x1 + 1)

    def px(v):
        return left + (fx(v) - fx(x0)) / (fx(x1) - fx(x0)) * pw

    def py(v):
        return top + ph - (fy(v) - fy(y0)) / (fy(y1) - fy(y0)) * ph

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
           f'width="{width}" height="{height}">']
    if title:
        out.append(f'<text x="{left}" y="20" font-size="14" font-weight="bold" fill="currentColor">{_esc(title)}</text>')
    for t in ticks(y0, y1, log=logy):
        y = py(t)
        out.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + pw}" y2="{y:.1f}" stroke="currentColor" '
                   f'stroke-opacity="0.15"/>')
        out.append(f'<text x="{left - 6}" y="{y + 4:.1f}" font-size="11" text-anchor="end" '
                   f'fill="currentColor">{_label(t)}</text>')
    for t in ticks(x0, x1, log=logx):
        x = px(t)
        out.append(f'<line x1="{x:.1f}" y1="{top + ph}" x2="{x:.1f}" y2="{top + ph + 4}" stroke="currentColor"/>')
        out.append(f'<text x="{x:.1f}" y="{top + ph + 17}" font-size="11" text-anchor="middle" '
                   f'fill="currentColor">{_label(t)}</text>')
    out.append(f'<rect x="{left}" y="{top}" width="{pw}" height="{ph}" fill="none" stroke="currentColor"/>')
    if xlabel:
        out.append(f'<text x="{left + pw / 2:.1f}" y="{height - 8}" font-size="12" text-anchor="middle" '
                   f'fill="currentColor">{_esc(xlabel)}</text>')
    if ylabel:
        out.append(f'<text x="14" y="{top + ph / 2:.1f}" font-size="12" text-anchor="middle" fill="currentColor" '
                   f'transform="rotate(-90 14 {top + ph / 2:.1f})">{_esc(ylabel)}</text>')
    for s in series:
        sx, sy = _thin(s.x, s.y)
        runs, cur = [], []
        for x, y in zip(sx, sy):
            if ok(x, logx) and ok(y, logy) and y0 <= y <= y1:
                cur.append(f"{px(x):.1f},{py(y):.1f}")
            elif cur:
                runs.append(cur)
                cur = []
        if cur:
            runs.append(cur)
        dash = ' stroke-dasharray="5 3"' if s.dashed else ""
        for pts in runs:
            if len(pts) == 1:
                cx, cy = pts[0].split(",")
                out.append(f'<circle cx="{cx}" cy="{cy}" r="2.5" fill="{s.color}" opacity="{s.opacity}"/>')
            else:
                out.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{s.color}" '
                           f'stroke-width="1.6" stroke-opacity="{s.opacity}"{dash}/>')
    seen = []
    for s in series:
        if s.label and (s.label, s.color) not in seen:
            seen.append((s.label, s.color))
    for i, (label, color) in enumerate(seen):
        y = top + 8 + 18 * i
        out.append(f'<line x1="{left + pw + 12}" y1="{y}" x2="{left + pw + 32}" y2="{y}" stroke="{color}" '
                   f'stroke-width="2.5"/>')
        out.append(f'<text x="{left + pw + 38}" y="{y + 4}" font-size="11" fill="currentColor">{_esc(label)}</text>')
    out.append("</svg>")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        f.write("\n".join(out) + "\n")
    return path
# @end
