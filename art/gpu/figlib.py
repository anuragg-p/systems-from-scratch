"""Helpers for the gpu track's lesson figures (art/gpu/archmap.py, figs00.py, figs01.py).

Drawing: the Art class and helpers of the track's outline art, art/outlines/gpu_art.py (Art, cell,
code, rich, sans, cw, r1), loaded under its own module name so a figure looks like the covers. Art
draws a 640-wide viewBox of any height, asserts no text under 10px, and gives each figure its own
arrowhead markers (s, m and a). Classes are the .art ones from harness/web/app.css, nothing else, so
dark mode works:
    s m a        stroke: foreground, muted, accent
    f fs af fa   fill: page, code background, accent-soft, accent
    t tm ta      text fill: foreground, muted, accent      mono: monospace

write(name, art) checks a figure before it lands, with gpu_art.check: ASCII, and kept whole by the
site's sanitizer (every element survives). The file goes to the figures/ folder of the module the
name's lesson id belongs to: "00.02-allowance" -> tracks/gpu/lessons/00-the-workbench/figures/.

source(name) reads a file of the track's code (tracks/gpu/<name>), for a figure that checks what it
draws against the code.
"""
import importlib.util
import os
import sys

sys.dont_write_bytecode = True          # no __pycache__ under art/ or harness/
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

_spec = importlib.util.spec_from_file_location("gpu_outline_art", os.path.join(ROOT, "art", "outlines", "gpu_art.py"))
G = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(G)
Art, cell, code, rich, sans, cw, r1 = G.Art, G.cell, G.code, G.rich, G.sans, G.cw, G.r1

TRACK = os.path.join(ROOT, "tracks", "gpu")
LESSONS = os.path.join(TRACK, "lessons")
MODULES = {"00": "00-the-workbench", "01": "01-matrix-multiply-on-the-cpu"}
W = 640
MAX_H = 300


def figures_dir(lid):
    """The figures/ folder of the module lesson `lid` (NN.LL) is in."""
    return os.path.join(LESSONS, MODULES[lid[:2]], "figures")


def source(name):
    with open(os.path.join(TRACK, name)) as fh:
        return fh.read()


def write(name, art):
    """Check art and write it as <its module>/figures/<name>.svg; name is NN.LL-what. Returns the path."""
    assert art.h <= MAX_H, (name, art.h)
    text = art.svg()
    bad = G.check({name: text})
    if bad:
        raise SystemExit("\n".join(bad))
    d = figures_dir(name[:5])
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, name + ".svg")
    with open(path, "w") as fh:
        fh.write(text)
    print(os.path.relpath(path, ROOT))
    return path
