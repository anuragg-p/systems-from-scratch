"""Tests for stepped figures: one .svg whose top-level <g class="step"> groups are frames the reader
steps through (harness/web/art.py, markdown.py, app.js, app.css; the author's helper art/steps.py)."""

import importlib.util
import os
import re
import shutil
import tempfile
import unittest

from harness import outlines as outlines_mod
from harness.tests.test_web import SAMPLE_TRACK, SVG_COVER, SVG_EVIL, http_req, restore_env, write

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# A figure with exactly one step group is an ordinary figure: it renders as it always has.
ONE_STEP = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100"><defs><marker id="m" viewBox="0 0 10 10" refX="5" refY="5">'
            '<path d="M0 0L10 5L0 10z" class="fa"/></marker></defs><rect class="s" x="1" y="1" width="20" height="20"/>'
            '<g class="step" id="g1"><title>Only &lt;step&gt;</title><path class="a" d="M0 50H90" marker-end="url(#m)"/>'
            '<text class="t" x="5" y="15">ONE</text></g></svg>')
ORDINARY_DOC = "Text.\n\n![Cover `x` caption](figures/plain.svg)\n\n- item\n\n  ![One step](figures/one.svg)\n"
# What the renderer at the first commit (before stepped figures) made of ORDINARY_DOC, with SVG_COVER
# as plain.svg and ONE_STEP as one.svg, numbering from art101: the same bytes must come out now.
ORDINARY_HTML = (
    '<p>Text.</p>\n<figure class="art fig"><svg viewBox="0 0 640 300" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" '
    'focusable="false"><defs><marker id="art101-arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">'
    '<path d="M0 0L6 3L0 6z" class="fa"></path></marker></defs><rect x="10" y="10" width="100" height="50" rx="6" class="s fs">'
    '</rect><path d="M110 35H300" class="a" marker-end="url(#art101-arrow)"></path><text x="20" y="40" class="t mono" '
    'font-size="14" text-anchor="start">COVER-LABEL</text></svg><figcaption>Cover <code>x</code> caption</figcaption></figure>\n'
    '<ul><li><p>item</p>\n<figure class="art fig"><svg viewBox="0 0 200 100" xmlns="http://www.w3.org/2000/svg" '
    'aria-hidden="true" focusable="false"><defs><marker id="art102-m" viewBox="0 0 10 10" refX="5" refY="5"><path '
    'd="M0 0L10 5L0 10z" class="fa"></path></marker></defs><rect class="s" x="1" y="1" width="20" height="20"></rect>'
    '<g class="step" id="art102-g1"><title>Only &lt;step&gt;</title><path class="a" d="M0 50H90" '
    'marker-end="url(#art102-m)"></path><text class="t" x="5" y="15">ONE</text></g></svg><figcaption>One step'
    '</figcaption></figure></li></ul>')


def load_helper():
    """art/steps.py, the figure generators' helper (art/ is not a package)."""
    spec = importlib.util.spec_from_file_location("figure_steps", os.path.join(ROOT, "art", "steps.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sort_svg(values=(5, 2, 4, 6, 1, 3), late=""):
    """Insertion sort as a stepped figure, from a real run: the unsorted row, then one frame per
    insertion. The base has an arrowhead marker in <defs> that every frame's arrow points to, and
    `late` is base markup placed after the steps. Returns (svg text, [the row after each frame])."""
    steps = load_helper()
    a, rows, frames = list(values), [list(values)], []
    for i in range(1, len(a)):
        key, j = a[i], i - 1
        while j >= 0 and a[j] > key:
            a[j + 1] = a[j]
            j -= 1
        a[j + 1] = key
        rows.append(list(a))
    for k, row in enumerate(rows):
        cells = "".join(f'<rect class="s f" x="{20 + 60 * c}" y="40" width="50" height="40" id="c{c}"/>'
                        f'<text class="t mono" x="{45 + 60 * c}" y="66" text-anchor="middle">{v}</text>' for c, v in enumerate(row))
        arrow = f'<path class="a" d="M{45 + 60 * k} 100V86" marker-end="url(#tip)"/>' if k else ""
        cap = "The row as given" if not k else f"Insert {values[k]} & keep the first {k + 1} <sorted>"
        frames.append(steps.group(cap, cells + arrow + f'<text class="tm" x="20" y="20">ROW-{",".join(map(str, row))}</text>'))
    base = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 120"><title>whole figure</title><defs>'
            '<marker id="tip" viewBox="0 0 10 10" refX="8" refY="5"><path d="M0 0L10 5L0 10z" class="fa"/></marker></defs>'
            '<text class="tm" x="300" y="20" id="lbl">BASE-LABEL</text>')
    return base + "".join(frames) + late + "</svg>", rows


def counting_svg(n):
    """n small frames: frame k shows ROW-k over the base's BASE-LABEL."""
    steps = load_helper()
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 40"><text class="tm" x="4" y="12">BASE-LABEL</text>'
            + "".join(steps.group(f"step {k}", f'<text class="t" x="4" y="30">ROW-{k}</text>') for k in range(1, n + 1))
            + "</svg>")


def ids(markup):
    return re.findall(r'\sid="([^"]+)"', markup)


class SteppedFigureTests(unittest.TestCase):
    """The split, the markup and the limits, without a server."""

    def setUp(self):
        from harness.web import art
        self.art = art
        self.tmp = tempfile.mkdtemp(prefix="learn-steps-test-")
        self.doc = os.path.join(self.tmp, "01.01-x.md")
        self.saved_counter = art._counter[0]

    def tearDown(self):
        self.art._counter[0] = self.saved_counter
        shutil.rmtree(self.tmp, ignore_errors=True)

    def fig(self, name, text):
        write(os.path.join(self.tmp, "figures", name), text)
        return f"figures/{name}"

    def render(self, text):
        from harness.web.markdown import render
        return render(text, None, lambda src: self.art.doc_figure(self.doc, src))

    def test_ordinary_figures_render_byte_for_byte_as_before(self):
        self.fig("plain.svg", SVG_COVER)
        self.fig("one.svg", ONE_STEP)
        self.art._counter[0] = 100              # a fresh directory: both files are new to the cache
        self.assertEqual(self.render(ORDINARY_DOC), ORDINARY_HTML)
        self.assertIsInstance(self.art.doc_figure(self.doc, "figures/one.svg"), str)
        self.assertIsNone(self.art.split_steps(ONE_STEP))
        self.assertEqual(self.art.figure_problems(self.doc), [])

    def test_a_stepped_file_gives_one_whole_frame_per_step(self):
        text, rows = sort_svg(late='<rect class="m" id="late" x="0" y="0" width="4" height="4"/>')
        frames = self.art.split_steps(text, prefix="pf")
        self.assertEqual(len(frames), 6)
        for k, ((svg, _), row) in enumerate(zip(frames, rows), 1):
            self.assertTrue(svg.startswith('<svg viewBox="0 0 400 120" '), k)       # one viewBox: no jump between frames
            self.assertEqual(svg.count("BASE-LABEL"), 1, k)                          # the base, once in every frame
            self.assertEqual(re.findall(r"ROW-([\d,]+)", svg), [",".join(map(str, row))], k)   # its own step only
            self.assertLess(svg.index('id="pf-%d-late"' % k), svg.index('<g class="step"'))     # base under the step
            self.assertNotIn("<title>Insert", svg)                                  # the caption left the picture
            self.assertIn("<title>whole figure</title>", svg)                       # the base's own title stays
        self.assertEqual(rows[-1], [1, 2, 3, 4, 5, 6])
        self.assertEqual(rows[3], [2, 4, 5, 6, 1, 3])

    def test_ids_are_unique_and_every_reference_resolves_in_its_own_frame(self):
        self.fig("sort.svg", sort_svg()[0])
        self.fig("plain.svg", SVG_COVER)
        page = self.render("![Insertion sort](figures/sort.svg)\n\n![Cover](figures/plain.svg)")
        found = ids(page)
        self.assertEqual(len(found), 6 * 8 + 1)          # per frame: the marker, the label, six cells; the cover's marker
        self.assertEqual(len(found), len(set(found)))
        frames = re.findall(r'<li class="steps-frame">(.*?)</li>', page)
        self.assertEqual(len(frames), 6)
        refs = [re.findall(r"url\(#([^)]+)\)", frame) for frame in frames]
        self.assertEqual([len(r) for r in refs], [0, 1, 1, 1, 1, 1])     # the row as given has no arrow
        for frame, got in zip(frames, refs):
            for ref in got:
                self.assertIn(ref, ids(frame))               # its own frame's copy of the marker

    def test_the_markup_lists_every_frame_with_its_step_and_caption(self):
        self.fig("sort.svg", sort_svg()[0])
        out = self.render("![Insertion sort on *six* numbers](figures/sort.svg)")
        self.assertTrue(out.startswith('<figure class="art fig steps"><ol class="steps-list"><li class="steps-frame"><svg '))
        self.assertTrue(out.endswith("</ol><figcaption>Insertion sort on <em>six</em> numbers</figcaption></figure>"))
        for k in range(1, 7):
            self.assertIn(f'<span class="steps-k">Step {k} of 6</span>', out)
        self.assertIn('<span class="steps-k">Step 1 of 6</span> <span class="steps-t">The row as given</span></p></li>', out)
        self.assertNotIn("<button", out)                 # controls are the script's: a page without one has none
        self.assertEqual(self.art.figure_problems(self.doc), [])

    def test_step_captions_are_escaped(self):
        self.fig("sort.svg", sort_svg()[0])
        out = self.render("![Sort](figures/sort.svg)")
        self.assertIn('<span class="steps-t">Insert 2 &amp; keep the first 2 &lt;sorted&gt;</span>', out)
        evil = sort_svg()[0].replace("<title>The row as given</title>",
                                     '<title>A <tspan>"q"</tspan>\n  &lt;script&gt;alert(1)&lt;/script&gt;</title>')
        self.fig("evil.svg", evil)
        out = self.render("![Sort](figures/evil.svg)")
        self.assertIn('<span class="steps-t">A &quot;q&quot; &lt;script&gt;alert(1)&lt;/script&gt;</span>', out)
        self.assertNotIn("<script", out)
        self.assertNotIn("<tspan>&quot;q", out)

    def test_hostile_content_in_a_step_group_is_still_sanitized(self):
        inner = SVG_EVIL[SVG_EVIL.index(">") + 1:SVG_EVIL.rindex("</svg>")]
        text = ('<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 10 10">'
                '<rect class="s" x="1" y="1" width="2" height="2"/>'
                f'<g class="step" onclick="alert(4)" style="fill:red"><title>one</title>{inner}</g>'
                f'<g class="step"><script>alert(5)</script><title>two</title>{inner}</g></svg>')
        self.fig("evil.svg", text)
        out = self.render("![Hostile](figures/evil.svg)")
        self.assertEqual(out.count('<li class="steps-frame">'), 2)
        for bad in ("<script", "alert(", "<style", "foreignObject", "onload", "onclick", "style=", "href", "evil.example", "<image", "<a "):
            self.assertNotIn(bad, out, bad)
        self.assertIn('<span class="steps-t">one</span>', out)
        self.assertNotIn("steps-t\">two", out)               # a <title> not first in its group is no caption
        self.assertIn("T &amp; <tspan>U</tspan>", out)

    def test_the_frame_cap(self):
        from harness.web.markdown import render
        self.assertEqual(self.art.MAX_STEPS, 40)
        self.fig("many.svg", counting_svg(41))
        got = self.art.doc_figure(self.doc, "figures/many.svg")
        self.assertIsInstance(got, str)       # an ordinary figure: base and the last step
        self.assertEqual(re.findall(r"ROW-\d+", got), ["ROW-41"])
        self.assertIn("BASE-LABEL", got)
        out = render("![Many](figures/many.svg)", None, lambda s: got)
        self.assertTrue(out.startswith('<figure class="art fig"><svg '))
        write(self.doc, "# x\n\n![Many](figures/many.svg)\n")       # and ./learn check says so
        self.assertEqual(self.art.figure_problems(self.doc),
                         [(3, "figure figures/many.svg has 41 steps, more than 40: the page shows only its last step, "
                              "as a still figure")])
        self.fig("forty.svg", counting_svg(40))
        self.assertEqual(len(self.art.doc_figure(self.doc, "figures/forty.svg")), 40)

    def test_the_size_cap(self):
        text = sort_svg()[0]
        frames = self.art.split_steps(text)
        size = sum(len(m) for m, _ in frames)
        saved = self.art.MAX_STEPPED
        self.art.MAX_STEPPED = size - 1
        try:
            self.assertIn("KB over its 6 frames", self.art.steps_over(frames))
            self.fig("big.svg", text)
            self.assertIsInstance(self.art.doc_figure(self.doc, "figures/big.svg"), str)
        finally:
            self.art.MAX_STEPPED = saved
        self.assertEqual(self.art.steps_over(frames), "")


class AuthorHelperTests(unittest.TestCase):
    def test_group_step_and_check(self):
        steps = load_helper()
        self.assertEqual(steps.group("a < b\n  then c", "<rect/>"), '<g class="step"><title>a &lt; b then c</title>\n<rect/>\n</g>')
        self.assertEqual(steps.group("", "<rect/>"), '<g class="step">\n<rect/>\n</g>')

        class Fig:
            def __init__(self):
                self.out = []
        fig = Fig()
        fig.out.append("<base/>")
        with steps.step(fig, "first"):
            fig.out.append("<one/>")
            fig.out.append("<two/>")
        with steps.step(fig, "second"):
            fig.out.append("<three/>")
        self.assertEqual(fig.out, ["<base/>", '<g class="step"><title>first</title>\n<one/>\n<two/>\n</g>',
                                   '<g class="step"><title>second</title>\n<three/>\n</g>'])
        self.assertEqual(steps.check(sort_svg()[0]), 6)
        self.assertEqual(steps.check(counting_svg(40)), 40)
        for bad in (ONE_STEP, counting_svg(41), sort_svg()[0].replace("BASE-LABEL", "BASE" + chr(0x2014) + "LABEL"), "<svg>"):
            with self.assertRaises(ValueError):
                steps.check(bad)


SORT_DOC = """---
id: 01.01
title: Sorting
---

# 01.01 Sorting

The intro.

## The idea

Insertion sort takes each number in turn and slides it left past every bigger one.

![Insertion sort on six numbers](figures/01.01-sort.svg)

## Run it

Run prose.
"""


class SteppedPageTests(unittest.TestCase):
    """A stepped figure in a real lesson page, served and exported."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="learn-steps-page-")
        cls.saved = {k: os.environ.get(k) for k in ("LEARN_TRACKS_DIR", "LEARN_WORK_DIR")}
        tracks = os.path.join(cls.tmp, "tracks")
        os.environ["LEARN_TRACKS_DIR"] = tracks
        os.environ["LEARN_WORK_DIR"] = os.path.join(cls.tmp, "work-none")
        mod = os.path.join(tracks, "sorty", "lessons", "01-basics")
        write(os.path.join(tracks, "sorty", "track.py"), SAMPLE_TRACK)
        write(os.path.join(mod, "README.md"), "---\nid: 01\ntitle: Basics\n---\n")
        write(os.path.join(mod, "01.01-sorting.md"), SORT_DOC)
        write(os.path.join(mod, "figures", "01.01-sort.svg"), sort_svg()[0])
        from harness import core, workspace
        cls.core, cls.ws = core, workspace
        cls.old = (core.ROOT, core.TRACKS_DIR, workspace.WORK_DIR, outlines_mod.OUTLINES_DIR)
        core.ROOT = cls.tmp
        core.TRACKS_DIR = tracks
        workspace.WORK_DIR = os.path.join(cls.tmp, "work-none")
        outlines_mod.OUTLINES_DIR = os.path.join(cls.tmp, "no-outlines")
        from harness.web.server import WebServer
        import threading
        cls.srv = WebServer(0)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.page = http_req(cls.port, "GET", "/t/sorty/01.01")[1]

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.core.ROOT, cls.core.TRACKS_DIR, cls.ws.WORK_DIR, outlines_mod.OUTLINES_DIR = cls.old
        restore_env(cls.saved)
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def check_page(self, page):
        fig = page[page.index('<figure class="art fig steps">'):]
        fig = fig[:fig.index("</figure>") + len("</figure>")]
        self.assertEqual(fig.count('<li class="steps-frame">'), 6)
        self.assertIn("<figcaption>Insertion sort on six numbers</figcaption>", fig)
        self.assertEqual(len(ids(page)), len(set(ids(page))))
        self.assertLess(page.index("slides it left"), page.index(fig))
        self.assertLess(page.index(fig), page.index('<script src="/static/app.js"></script>'))

    def test_served_page_has_every_frame_and_the_script(self):
        self.check_page(self.page)
        js = http_req(self.port, "GET", "/static/app.js")[1]
        css = http_req(self.port, "GET", "/static/app.css")[1]
        self.assertIn('querySelectorAll("figure.steps")', js)
        self.assertIn('aria-live="polite"', js)
        self.assertIn(".steps.is-live .steps-frame.on { visibility: visible; }", css)
        self.assertIn("@media print { .steps-bar { display: none; }", css)

    def test_export_has_the_frames_and_the_script(self):
        from harness.web import export
        out = os.path.join(self.tmp, "site")
        stats = export.export(out)
        self.assertEqual(stats["leaks"], [])
        with open(os.path.join(out, "t", "sorty", "01.01", "index.html"), encoding="utf-8") as f:
            page = f.read()
        self.check_page(page)
        with open(os.path.join(out, "static", "app.js"), encoding="utf-8") as f:
            self.assertIn('querySelectorAll("figure.steps")', f.read())
        with open(os.path.join(out, "static", "app.css"), encoding="utf-8") as f:
            self.assertIn(".steps.is-live", f.read())


if __name__ == "__main__":
    unittest.main()
