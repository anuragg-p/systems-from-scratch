"""Outlines: tracks that are planned but not built. Parsing (harness/outlines.py) and how the
site shows them: listed as coming soon, an overview with nothing to open, and no lesson pages."""

import os
import re
import shutil
import tempfile
import threading
import unittest

from harness import outlines
from harness.tests.test_web import SAMPLE_TRACK, SVG_COVER, SVG_ICON, SVG_TRACK_ART, http_req, restore_env, write

DEMO = """---
id: demo
title: A demo <b>engine</b>, from scratch
kind: inference
status: coming soon
audience: People who test things.
prerequisites: Python.
outcome: A working `demo` you can run.
---

# A demo engine, from scratch

First intro sentence, and a second
line of the same paragraph.

**Coming soon.** This is the outline: the direction, not the lessons yet.
Format: `templates/outline.md`.

## Module 00 - The start

- Goal: Know the
  whole thing.
- You build: A thing.
- Value: It helps.
- Lessons:
  - 00.01 First lesson
  - 00.02 Second lesson, with a title that
    wraps onto a second line
- Learn from: [B-ONE], [V-TWO]

## Module 01 - Next

- Goal: Go further.
- You build: More.
- Value: Even more.
- Lessons:
  - 01.01 Third lesson
- Learn from: [P-THREE], [NOPE]

## Library

| Key | Kind | Title | By | Where |
|---|---|---|---|---|
| B-ONE | book | The <i>Book</i> | An Author | Press, 2020; free at https://example.com/book/ |
| V-TWO | video | A Video | Someone | https://www.example.org/watch?v=1&t=2 |
| X-BAD | article | Not a link | Mallory | javascript:alert(1) |
| P-THREE | paper | A Paper | Et Al. | Journal, 2019 |
| Z-ODD | podcast | An Episode | Host | https://pod.example.net/ep |
"""

BARE = """---
id: bare
title: Bare outline
kind: research
outcome: Nothing drawn yet.
---

# Bare outline

## Module 00 - Only

- Goal: G.
- You build: B.
- Value: V.
- Lessons:
  - 00.01 Lone lesson
- Learn from: [K]

## Library

| Key | Kind | Title | By | Where |
|---|---|---|---|---|
| K | book | Kay | K. | 2000 |
"""

# an outline whose id a real track already has: the track wins
CLASH = "---\nid: sample\ntitle: CLASHING OUTLINE\n---\n\n# CLASHING OUTLINE\n\n## Module 00 - X\n\n- Lessons:\n  - 00.01 Y\n"


def section(page, mid):
    start = page.index(f'id="m-{mid}"')
    end = page.find('<section class="module"', start + 1)
    return page[start:end if end != -1 else page.index('id="library"', start)]


class ParseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="learn-outline-parse-")
        write(os.path.join(cls.tmp, "demo.md"), DEMO)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_front_matter_intro_and_modules(self):
        o = outlines.parse(os.path.join(self.tmp, "demo.md"))
        self.assertEqual((o.id, o.stem, o.kind, o.status_label), ("demo", "demo", "inference", "Coming soon"))
        self.assertEqual(o.title, "A demo <b>engine</b>, from scratch")     # raw here; the page escapes it
        self.assertEqual(o.audience, "People who test things.")
        self.assertEqual(o.prerequisites, "Python.")
        self.assertEqual(o.outcome, "A working `demo` you can run.")
        self.assertEqual(o.intro, "First intro sentence, and a second line of the same paragraph.")  # no status note
        self.assertEqual([m.id for m in o.modules], ["00", "01"])
        m = o.modules[0]
        self.assertEqual((m.title, m.goal, m.build, m.value), ("The start", "Know the whole thing.", "A thing.", "It helps."))
        self.assertEqual(m.lessons, [("00.01", "First lesson"),
                                     ("00.02", "Second lesson, with a title that wraps onto a second line")])
        self.assertEqual(m.learn_from, ["B-ONE", "V-TWO"])
        self.assertEqual(len(o.lessons), 3)

    def test_library(self):
        o = outlines.parse(os.path.join(self.tmp, "demo.md"))
        lib = {r.key: r for r in o.library}
        self.assertEqual(lib["B-ONE"].url, "https://example.com/book/")
        self.assertEqual(lib["V-TWO"].url, "https://www.example.org/watch?v=1&t=2")
        self.assertIsNone(lib["P-THREE"].url)
        self.assertIsNone(lib["X-BAD"].url)            # only http(s) becomes a link
        self.assertEqual([k for k, _ in o.library_by_kind()], ["book", "video", "article", "paper", "podcast"])

    def test_problems_name_what_breaks_the_format(self):
        o = outlines.parse(os.path.join(self.tmp, "demo.md"))
        found = outlines.problems(o)
        self.assertEqual(len(found), 1, found)
        self.assertTrue(found[0].endswith("demo.md: module 01 cites [NOPE], which is not in the Library"), found)

    def test_a_malformed_file_still_parses(self):
        path = os.path.join(self.tmp, "junk-file.md")
        write(path, "no front matter\n\n## Module 7 - not two digits\n| a | b |\n")
        o = outlines.parse(path)
        self.assertEqual((o.id, o.title, o.modules, o.library), ("junk-file", "junk-file", [], []))
        self.assertTrue(outlines.problems(o))

    def test_discover_skips_track_ids_duplicates_and_other_files(self):
        d = tempfile.mkdtemp(prefix="learn-outline-disc-")
        try:
            write(os.path.join(d, "a.md"), DEMO)
            write(os.path.join(d, "b.md"), DEMO)                 # same id as a.md: the first file wins
            write(os.path.join(d, "c.md"), CLASH)
            write(os.path.join(d, "notes.txt"), "not an outline")
            old = outlines.OUTLINES_DIR
            outlines.OUTLINES_DIR = d
            try:
                self.assertEqual([(o.id, o.stem) for o in outlines.discover(["sample"])], [("demo", "a")])
                self.assertEqual([o.id for o in outlines.discover()], ["demo", "sample"])
                outlines.OUTLINES_DIR = os.path.join(d, "missing")
                self.assertEqual(outlines.discover(), [])
            finally:
                outlines.OUTLINES_DIR = old
        finally:
            shutil.rmtree(d, ignore_errors=True)


class RealOutlinesTests(unittest.TestCase):
    """The outlines in this repo follow the template, and each module has its art."""

    def test_every_real_outline_is_well_formed(self):
        found = outlines.discover()
        self.assertTrue(found, "no outlines in outlines/")
        for o in found:
            self.assertEqual(outlines.problems(o), [], o.path)
            for m in o.modules:
                self.assertTrue(m.goal and m.build and m.value and m.lessons, f"{o.id} module {m.id}")

    def test_shipped_art_is_safe_and_complete(self):
        from harness.web import art
        for o in outlines.discover():
            if o.stem not in ("inference-engineering", "ai-research"):
                continue   # art is optional for any other outline
            self.assertEqual(len(o.modules), 8, o.id)
            for m in o.modules:
                cover = art.outline_art(o, m.id, "cover")
                icon = art.outline_art(o, m.id, "icon")
                self.assertTrue(cover.startswith("<svg ") and 'viewBox="0 0 640 300"' in cover, f"{o.id} {m.id} cover")
                self.assertTrue(icon.startswith("<svg ") and 'viewBox="0 0 20 20"' in icon, f"{o.id} {m.id} icon")

    def test_real_overview_pages_render_without_lesson_links(self):
        from harness.web import views
        for o in outlines.discover([t.id for t in views.tracks()]):
            page = views.outline_page(o)
            self.assertEqual(page.count('<section class="module"'), len(o.modules), o.id)
            self.assertEqual(page.count('class="grid-card unit is-planned"'), len(o.lessons), o.id)
            self.assertNotRegex(page, rf'href="/t/{re.escape(o.id)}/', o.id)


class PageTests(unittest.TestCase):
    """The site, against a temp folder of tracks and one of outlines."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="learn-outline-web-")
        cls.saved = {k: os.environ.get(k) for k in ("LEARN_TRACKS_DIR", "LEARN_WORK_DIR", "LEARN_OUTLINES_DIR")}
        tracks, odir, cls.work = (os.path.join(cls.tmp, x) for x in ("tracks", "outlines", "work"))
        os.environ.update(LEARN_TRACKS_DIR=tracks, LEARN_WORK_DIR=cls.work, LEARN_OUTLINES_DIR=odir)
        root = os.path.join(tracks, "sample")
        write(os.path.join(root, "track.py"), SAMPLE_TRACK)
        write(os.path.join(root, "lessons", "01-basics", "README.md"), "---\nid: 01\ntitle: Basics\n---\n")
        write(os.path.join(root, "lessons", "01-basics", "01.01-one.md"), "---\nid: 01.01\ntitle: One\n---\n\n# 01.01 One\n\nProse.\n")
        write(os.path.join(odir, "demo-outline.md"), DEMO)
        write(os.path.join(odir, "demo-outline", "00", "cover.svg"), SVG_COVER)
        write(os.path.join(odir, "demo-outline", "00", "icon.svg"), SVG_ICON)
        write(os.path.join(odir, "demo-outline", "art.svg"), SVG_TRACK_ART)
        write(os.path.join(odir, "demo-outline", "icon.svg"), SVG_ICON)
        write(os.path.join(odir, "bare.md"), BARE)
        write(os.path.join(odir, "clash.md"), CLASH)
        from harness import core, workspace
        cls.core, cls.ws = core, workspace
        cls.old = (core.TRACKS_DIR, workspace.WORK_DIR, outlines.OUTLINES_DIR)
        core.TRACKS_DIR, workspace.WORK_DIR, outlines.OUTLINES_DIR = tracks, cls.work, odir
        from harness.web.server import WebServer
        cls.srv = WebServer(0)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.core.TRACKS_DIR, cls.ws.WORK_DIR, outlines.OUTLINES_DIR = cls.old
        restore_env(cls.saved)
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def get(self, path):
        return http_req(self.port, "GET", path)

    def page(self, path):
        status, body = self.get(path)
        self.assertEqual(status, 200, path)
        return body

    def test_outline_icon_in_the_top_bar_switcher(self):
        page = self.page("/t/demo")
        pill = page[page.index('<a class="track-pill"'):page.index("</a>", page.index('<a class="track-pill"'))]
        self.assertIn('<span class="mod-ic tp-ic"><svg', pill)
        self.assertNotIn("tp-ic", self.page("/t/bare").split('<a class="track-pill"')[1].split("</a>")[0])

    def test_home_lists_outlines_as_coming_soon(self):
        home = self.page("/")
        card = re.search(r'<a class="grid-card track-card is-soon" href="/t/demo">.*?</a>', home, re.S)
        self.assertIsNotNone(card)
        card = card.group(0)
        self.assertIn("Coming soon", card)
        self.assertIn("A demo &lt;b&gt;engine&lt;/b&gt;, from scratch", card)
        self.assertIn('<span class="card-meta"><span class="pill">2 modules</span><span class="pill">3 lessons planned</span></span>', card)
        for absent in ('class="bar"', "data-start", "built", "Start", "Continue", " of ", "%", "progress", "workspace"):
            self.assertNotIn(absent, card)                     # no progress, no start button
        self.assertIn('<span class="pill soon">Coming soon</span>', card.split('<span class="card-body">')[1])   # inside the body
        self.assertIn("TRACK-ART-LABEL", card)                 # its own picture, sanitized
        self.assertNotIn("<script", card)
        bare = re.search(r'<a class="grid-card track-card is-soon" href="/t/bare">.*?</a>', home, re.S).group(0)
        self.assertIn("M150 128l-10 8 10 8", bare)              # no art.svg: the default picture
        self.assertIn('href="/t/bare"', home)
        grid = home[home.index('class="track-grid"'):]
        self.assertEqual(grid.count('href="/t/sample"'), 1)    # the clashing outline is not listed
        self.assertNotIn("CLASHING OUTLINE", home)
        self.assertIn("<b>1 track</b>", home)                   # outlines are not counted as open tracks
        self.assertIn("2 coming soon", home)

    def test_overview_shows_modules_covers_lessons_and_library(self):
        page = self.page("/t/demo")
        self.assertIn('<h1 class="ov-title">A demo &lt;b&gt;engine&lt;/b&gt;, from scratch</h1>', page)
        self.assertIn("A working <code>demo</code> you can run.", page)
        strip = page[page.index('class="strip-card soon-strip"'):page.index("</section>", page.index("soon-strip"))]
        self.assertIn("Coming soon", strip)
        self.assertIn("no lesson is written yet", strip)
        self.assertIn("First intro sentence, and a second line of the same paragraph.", page)
        self.assertNotIn("templates/outline.md", page)          # the status note is for authors
        m0 = section(page, "00")
        self.assertIn("<h2>The start</h2>", m0)
        self.assertIn('<div class="art cover"><svg', m0)
        self.assertIn("COVER-LABEL", m0)
        self.assertLess(m0.index("art cover"), m0.index("mod-facts"))
        self.assertLess(m0.index("mod-facts"), m0.index("plan-grid"))
        for text in ("<dt>Goal</dt><dd>Know the whole thing.</dd>", "<dt>What it builds</dt><dd>A thing.</dd>",
                     "<dt>Value</dt><dd>It helps.</dd>", "00.01", "First lesson",
                     "Second lesson, with a title that wraps onto a second line", "2 lessons planned"):
            self.assertIn(text, m0)
        self.assertIn('href="https://example.com/book/"', m0)   # Learn from links to the resource
        self.assertIn("Third lesson", section(page, "01"))
        self.assertIn('id="m-01"', page)

        lib = page[page.index('id="library"'):]
        heads = re.findall(r'<section class="lib-group"><h3>([^<]+)</h3>', lib)
        self.assertEqual(heads, ["Books", "Videos", "Articles", "Papers", "Podcast"])
        self.assertIn('<a class="lib-title" href="https://example.com/book/" target="_blank" rel="noopener noreferrer">', lib)
        self.assertIn('href="https://www.example.org/watch?v=1&amp;t=2"', lib)
        self.assertIn("The &lt;i&gt;Book&lt;/i&gt;", lib)
        self.assertIn("Press, 2020; free at example.com", lib)  # the URL reads as its host
        self.assertIn('<span class="lib-title">A Paper</span>', lib)
        self.assertNotIn('href="javascript', page)
        self.assertIn('id="lib-b-one"', lib)

    def test_lesson_cards_have_no_link_and_no_tabindex(self):
        page = self.page("/t/demo")
        cards = re.findall(r'<li class="grid-card unit is-planned">.*?</li>', page, re.S)
        self.assertEqual(len(cards), 3)
        for card in cards:
            for absent in ("<a", "href", "tabindex", "<button", 'class="ic"'):
                self.assertNotIn(absent, card)
        self.assertNotIn('href="/t/demo/', page)                # no lesson link anywhere, sidebar included
        self.assertNotIn("tabindex", page)

    def test_sidebar_lists_modules_without_lesson_links(self):
        page = self.page("/t/demo")
        side = page[page.index('<aside class="side"'):page.index("</aside>")]
        self.assertIn("Coming soon", side)
        self.assertIn('href="#m-00"', side)
        self.assertIn('href="#m-01"', side)
        self.assertEqual(side.count('class="mod-ic"'), 1)       # only module 00 has an icon
        self.assertNotIn("<details", side)
        self.assertNotIn("First lesson", side)

    def test_lesson_urls_and_workspace_calls_404(self):
        for path in ("/t/demo/00.01", "/t/demo/01.01", "/t/demo/99.99", "/t/demo/x", "/api/state/demo", "/api/file/demo?path=a"):
            self.assertEqual(self.get(path)[0], 404, path)
        self.assertEqual(http_req(self.port, "POST", "/api/start/demo")[0], 404)
        self.assertFalse(os.path.exists(os.path.join(self.work, "demo")))

    def test_missing_cover_renders_nothing(self):
        self.assertNotIn('class="art', section(self.page("/t/demo"), "01"))
        bare = self.page("/t/bare")
        for marker in ('class="art', 'class="mod-ic"', "<svg xmlns"):
            self.assertNotIn(marker, bare)
        self.assertIn("Lone lesson", bare)

    def test_a_track_keeps_its_id_over_an_outline(self):
        page = self.page("/t/sample")
        self.assertIn("Sample &lt;b&gt;track&lt;/b&gt;", page)
        self.assertNotIn("CLASHING OUTLINE", page)
        self.assertEqual(self.get("/t/sample/01.01")[0], 200)

    def test_nothing_about_tests_or_building(self):
        page = self.page("/t/demo")
        for word in ("Run test", "PASS", "FAIL", "learn test", "Start building", "data-start", "Continue"):
            self.assertNotIn(word, page)


if __name__ == "__main__":
    unittest.main()
