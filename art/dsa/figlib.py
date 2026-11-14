"""Helpers for the xv6 lesson figures (modules 03-05).

Copied from the cover generator's Art class and extended: variable height, a muted
arrowhead, and a few layout helpers. Classes are the .art ones from app.css:
  s m a        stroke: foreground, muted, accent
  f fs af fa   fill: page, code background, accent-soft, accent
  t tm ta      text fill: foreground, muted, accent      mono: monospace
"""
import html
import os

LESSONS = os.path.expanduser("~/Documents/WORK/misc/systems-from-scratch/tracks/xv6/lessons")
SW = 'stroke-width="1.5"'


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
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 {self.h}" fill="none">\n'
                f'<title>{esc(self.title)}</title>\n{defs}\n{body}\n</svg>\n')


def write(module_dir, name, fig):
    d = os.path.join(LESSONS, module_dir, "figures")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, name + ".svg")
    s = fig.svg()
    s.encode("ascii")
    with open(p, "w") as f:
        f.write(s)
    return p
