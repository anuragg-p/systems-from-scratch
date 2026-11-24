"""The drawing surface for the research track's lesson figures: Fig, write() and check().

Copied from art/dsa/figlib.py (itself the xv6 one) and kept the same, so a figure here reads
like a figure there: one 640-wide SVG per figure, styled only by the site's .art classes, so
it is right in light and dark with nothing else to do. The classes (harness/web/app.css):

    s m a        stroke: foreground, muted, accent
    f fs af fa   fill: page, code background, accent-soft, accent
    t tm ta      text fill: foreground, muted, accent          mono: monospace

The accent is for what the lesson is about; foreground for what the reader already has;
muted (and dashed) for what is not there yet or does not matter here. Text is ASCII only:
write +- for plus-minus, x for times, -> for an arrow, e-5 for a power of ten.

How a figure generator uses it. Each module has one, art/research/figsNN.py, written by the
agent who writes that module's lessons; it imports this file and figart.py (the plots, graphs,
tensors and networks this track draws again and again) and nothing else of another module:

    import os, sys
    HERE = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, HERE)                          # art/research/: figlib, figart
    sys.path.insert(0, os.path.dirname(HERE))         # art/: steps.py, for a stepped figure
    import figlib, figart
    from figlib import Fig, write

    def loss0003():
        r = figart.experiment("curve")                # a real run of the reference code
        f = Fig("loss0003", "Train loss of five seeds of the same fit", 300)
        ...                                           # draw on f: rect, text, line, path, ...
        return f

    print(write("00", "00.03-seeds", loss0003()))     # tracks/research/lessons/00-workbench/figures/

and the lesson shows it with a line of its own, ![Caption](figures/00.03-seeds.svg). Name
every file NN.LL-<name>.svg after the lesson it belongs to; NN.LL-map.svg is the
architecture map's (archmap.py), never a figsNN.py's. Give each Fig a key of its own
(letters and digits, e.g. the function name): it names the figure's arrowheads.

write() refuses a figure the site would not show as drawn (check() says why). For a preview
outside the repo, set figlib.LESSONS to a scratch directory first: the module folders and
their figures/ are made under it.

Fig's methods, all in the figure's own pixels (x right, y down, 640 wide, height as given):

    rect / box(x, y, w, h, cls, rx, dash)      a rectangle; dash=True for "not there yet"
    text(x, y, s, cls, size, anchor, weight, mono)   one line of text, y is the baseline
    line(x1, y1, x2, y2, cls, arrow, dash, start)    a straight line, an arrowhead at the end
                                               (arrow) or at both ends (start too)
    path(d, cls, arrow, dash, start)           any SVG path ("M10 20 C ...")
    polyline(points, cls, dash, width)         a line through [(x, y), ...]: a curve
    polygon(points, cls, opacity)              a filled shape: a band between two curves
    circle(cx, cy, r, cls)
    label_box(x, y, w, h, label, ..., sub)     a box with a centred label (and a second line)
    brace_h(x1, x2, y, cls, up)                a flat bracket under (or over) a span
    svg()                                      the file's text

tw(s, size, mono) is a rough width of a line of text in pixels: use it to place the next
thing and to keep text inside its box. fmt(v) prints a coordinate. sig(v) prints a measured
number the way the track's pages do (3 significant digits).
"""
import html
import math
import os
import re
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TRACK = os.path.join(ROOT, "tracks", "research")
LESSONS = os.path.join(TRACK, "lessons")
SW = 'stroke-width="1.5"'
WIDTH = 640

# The module folders, fixed so that nobody has to guess (lessons go in these, figures in their figures/).
MODULE_DIRS = {
    "00": "00-workbench",
    "01": "01-backprop",
    "02": "02-tensors",
    "03": "03-optimisers",
    "04": "04-deep-networks",
    "05": "05-generalisation",
    "06": "06-images",
    "07": "07-language-models",
    "08": "08-transformer",
    "09": "09-gpt-2",
    "10": "10-todays-architecture",
    "13": "13-experiments-that-hold-up",
    "14": "14-grokking",
}


def esc(s):
    return html.escape(s, quote=True)


def tw(s, size=12, mono=False):
    """Rough text width in px (Figtree ~0.54em, Geist Mono 0.6em)."""
    return len(s) * size * (0.6 if mono else 0.54)


def fmt(v):
    if isinstance(v, float):
        v = round(v, 2)
        if v == int(v):
            v = int(v)
    return str(v)


def sig(v, digits=3):
    """A measured number as the pages print it (lab.spread's format): 3 significant digits,
    trailing zeros dropped (0.0542, 2.3), 5.3e-11 rather than 5.3e-011, a whole number below a
    million in full (1285), "nan" and "inf" as words."""
    if isinstance(v, float) and not math.isfinite(v):
        return "nan" if v != v else ("inf" if v > 0 else "-inf")
    if 10 ** digits <= abs(v) < 1e6:
        return str(int(round(v)))
    s = f"{v:.{digits}g}"
    return re.sub(r"e([+-])0*(\d)", lambda m: "e" + ("-" if m.group(1) == "-" else "") + m.group(2), s)


class Fig:
    def __init__(self, key, title, height):
        self.key, self.title, self.h, self.out = key, title, height, []

    def add(self, s):
        self.out.append(s)

    def rect(self, x, y, w, h, cls="s f", rx=6, dash=False, sw=True):
        d = ' stroke-dasharray="4 4"' if dash else ""
        s = f" {SW}" if sw else ""
        self.add(f'<rect class="{cls}" x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}" rx="{fmt(rx)}"{s}{d}/>')

    box = rect

    def text(self, x, y, s, cls="t", size=12, anchor="start", weight=None, mono=False):
        c = cls + (" mono" if mono else "")
        wt = f' font-weight="{weight}"' if weight else ""
        a = f' text-anchor="{anchor}"' if anchor != "start" else ""
        self.add(f'<text class="{c}" x="{fmt(x)}" y="{fmt(y)}" font-size="{fmt(size)}"{wt}{a}>{esc(s)}</text>')

    def _marker(self, cls):
        return {"a": "aa", "m": "am"}.get(cls, "ah")

    def line(self, x1, y1, x2, y2, cls="s", arrow=False, dash=False, start=False):
        m = f' marker-end="url(#{self.key}-{self._marker(cls)})"' if arrow else ""
        if start:
            m += f' marker-start="url(#{self.key}-{self._marker(cls)})"'
        d = ' stroke-dasharray="4 4"' if dash else ""
        self.add(f'<line class="{cls}" x1="{fmt(x1)}" y1="{fmt(y1)}" x2="{fmt(x2)}" y2="{fmt(y2)}" {SW} stroke-linecap="round"{m}{d}/>')

    def path(self, d, cls="s", arrow=False, dash=False, start=False):
        m = f' marker-end="url(#{self.key}-{self._marker(cls)})"' if arrow else ""
        if start:
            m += f' marker-start="url(#{self.key}-{self._marker(cls)})"'
        da = ' stroke-dasharray="4 4"' if dash else ""
        self.add(f'<path class="{cls}" d="{d}" {SW} stroke-linecap="round" stroke-linejoin="round"{m}{da}/>')

    def polyline(self, points, cls="s", dash=False, width=1.75):
        """A line through the points [(x, y), ...], in figure pixels: a curve of a plot."""
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        da = ' stroke-dasharray="5 3"' if dash is True else (f' stroke-dasharray="{dash}"' if dash else "")
        self.add(f'<polyline class="{cls}" points="{pts}" stroke-width="{fmt(width)}" stroke-linecap="round" '
                 f'stroke-linejoin="round"{da}/>')

    def polygon(self, points, cls="af", opacity=None):
        """A filled shape through the points, with no outline: a band between two curves.
        cls is a fill class (af for the accent's band, fs for any other); opacity lets bands that
        overlap show through each other."""
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        op = f' fill-opacity="{fmt(opacity)}"' if opacity is not None else ""
        self.add(f'<polygon class="{cls}" points="{pts}"{op}/>')

    def circle(self, cx, cy, r, cls="s f"):
        self.add(f'<circle class="{cls}" cx="{fmt(cx)}" cy="{fmt(cy)}" r="{fmt(r)}" {SW}/>')

    def label_box(self, x, y, w, h, label, cls="s f", tcls="t", size=12, mono=True, rx=6, weight=None, dash=False, sub=None, subcls="tm", subsize=10.5):
        self.rect(x, y, w, h, cls, rx, dash)
        if sub is None:
            self.text(x + w / 2, y + h / 2 + size * 0.36, label, tcls, size, "middle", weight, mono)
        else:
            self.text(x + w / 2, y + h / 2 - 2, label, tcls, size, "middle", weight, mono)
            self.text(x + w / 2, y + h / 2 + subsize + 1, sub, subcls, subsize, "middle", None, mono)

    def brace_h(self, x1, x2, y, cls="m", up=False):
        """A flat bracket under (or over) a span: |____| """
        d = -6 if up else 6
        self.path(f"M{fmt(x1)} {fmt(y - d)} L{fmt(x1)} {fmt(y)} L{fmt(x2)} {fmt(y)} L{fmt(x2)} {fmt(y - d)}", cls)

    def svg(self):
        def mk(name, cls):
            return (f'<marker id="{self.key}-{name}" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
                    f'<path class="{cls}" d="M1 1.5L8.5 5L1 8.5" {SW} stroke-linecap="round" stroke-linejoin="round"/></marker>')
        defs = "<defs>" + mk("ah", "s") + mk("aa", "a") + mk("am", "m") + "</defs>"
        body = "\n".join(self.out)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {self.h}" fill="none">\n'
                f'<title>{esc(self.title)}</title>\n{defs}\n{body}\n</svg>\n')


def module_dir(module):
    """The folder of a module: "03" or "03-optimisers" -> "03-optimisers"."""
    mid = module[:2]
    if mid not in MODULE_DIRS:
        raise ValueError(f"no module {module!r} in figlib.MODULE_DIRS")
    return MODULE_DIRS[mid]


def check(text):
    """What the site would do wrong with this SVG text, as a list of problems ([] when none): not
    ASCII, too big, rejected by the sanitizer, an element the sanitizer drops, or a stepped
    figure past its limits."""
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    sys.dont_write_bytecode = True          # read harness/, never write into it
    from harness.web import art as site
    bad = []
    if not text.isascii():
        at = next(i for i, c in enumerate(text) if ord(c) > 127)
        bad.append(f"not ASCII: {text[max(0, at - 30):at + 10]!r}")
    if len(text) > site.MAX_SVG:
        bad.append(f"{len(text)} bytes, more than the site's {site.MAX_SVG}")
    clean = site.sanitize(text, "x")
    if not clean:
        bad.append("rejected by the site's sanitizer")
    else:
        def count(svg, skip):
            root = ET.fromstring(svg)
            elements = list(root.iter())
            attrs = sum(len(el.attrib) for el in elements) - sum(1 for k in root.attrib if k in skip)
            return len(elements), attrs
        (ne, na), (ce, ca) = count(text, ("width", "height")), count(clean, ("aria-hidden", "focusable"))
        if ce != ne:
            bad.append(f"the sanitizer dropped {ne - ce} element(s): only {sorted(site.TAGS)} are kept")
        elif ca != na:
            bad.append(f"the sanitizer dropped {na - ca} attribute(s) or value(s) it does not allow "
                       f"(harness/web/art.py ATTRS)")
    frames = site.split_steps(text)
    if frames is not None and site.steps_over(frames):
        bad.append(f"a stepped figure that {site.steps_over(frames)}")
    return bad


def write(module, name, fig):
    """Write fig to LESSONS/<module folder>/figures/<name>.svg, after check(); the path.
    module is "03" or "03-optimisers"; name is "03.02-valley" (no .svg)."""
    d = os.path.join(LESSONS, module_dir(module), "figures")
    s = fig.svg()
    bad = check(s)
    if bad:
        raise ValueError(f"{name}.svg: " + "; ".join(bad))
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, name + ".svg")
    with open(p, "w") as f:
        f.write(s)
    return p
