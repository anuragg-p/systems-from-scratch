"""Stepped figures for lesson figure generators: the frames of a process, as step groups.

A stepped figure is one ordinary .svg file (the rules: harness/web/art.py). Each top-level
<g class="step"> is one frame the reader steps through, in document order, drawn over everything
else in the file (the base, the same in every frame). A step group's leading <title> is that
step's caption: what just happened, in one line. The site shows the frames one at a time with Back
and Next, and without scripts or in print all of them, one under another.

    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # art/
    import steps

    # with a figlib.Fig: what is drawn inside the block becomes one step, in its place
    draw_axes(fig)                                # the base
    for caption, state in trace:                  # from a real run of the reference code
        with steps.step(fig, caption):
            draw_state(fig, state)
    text = fig.svg()
    steps.check(text)                             # ValueError if the site would not step it

    # or from markup of your own
    body = base + "".join(steps.group(caption, markup) for caption, markup in frames)

Use one only where the idea is a process (a sort, a heap fixing itself, a table being filled), at
most one per lesson, with frames made from a real run of the reference code so they cannot
disagree with it. Each frame should draw the whole state at that step, not what changed since the
last one: a reader without scripts sees every frame on its own. Steps do not nest.
"""
import contextlib
import html
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from harness.web import art as site  # noqa: E402  the site's own rules, so the two cannot drift

MAX_STEPS = site.MAX_STEPS


def group(caption, body):
    """One step group: <g class="step"><title>caption</title>body</g>. caption is plain text
    (escaped here, folded to one line); body is the SVG markup this step draws over the base."""
    cap = " ".join(str(caption or "").split())
    title = f"<title>{html.escape(cap, quote=False)}</title>" if cap else ""
    return f'<g class="step">{title}\n{body}\n</g>'


@contextlib.contextmanager
def step(fig, caption):
    """Everything drawn on fig inside the with-block becomes one step group, in its place among
    what fig has drawn. fig is anything that keeps its markup in a list, fig.out (figlib.Fig)."""
    start = len(fig.out)
    yield fig
    body = "\n".join(fig.out[start:])
    del fig.out[start:]
    fig.out.append(group(caption, body))


def check(svg_text):
    """The number of steps in svg_text, when the site will step through it. ValueError when it
    will not: not ASCII, not a usable SVG, fewer than two step groups, or past the limits
    (MAX_STEPS frames, or site.MAX_STEPPED bytes of markup over all of them)."""
    svg_text.encode("ascii")    # UnicodeEncodeError is a ValueError
    frames = site.split_steps(svg_text)
    if frames is None:
        raise ValueError('not a stepped figure: fewer than two top-level <g class="step">, or not a usable SVG')
    over = site.steps_over(frames)
    if over:
        raise ValueError(f"the figure {over}: the site would show only its last step")
    return len(frames)
