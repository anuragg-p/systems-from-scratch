"""The home page's top bar: a link to every track, built ones first, then the outlines (quieter),
however many there are. It used to stop at four, so the fixture has more than four."""

import os
import re
import shutil
import tempfile
import unittest

from harness import outlines
from harness.tests.test_web import SAMPLE_TRACK, restore_env, write

OUTLINE = "---\nid: {id}\ntitle: Planned {id}\n---\n\n# Planned {id}\n\n## Module 00 - X\n\n- Lessons:\n  - 00.01 Y\n"


class TopBarTests(unittest.TestCase):
    BUILT = ["alpha", "beta", "gamma"]                 # tracks: by folder name
    PLANNED = ["zeta", "eta", "delta", "epsilon"]      # outlines: by file name (01-zeta.md, ...), not by id

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="learn-topbar-")
        cls.saved = {k: os.environ.get(k) for k in ("LEARN_TRACKS_DIR", "LEARN_WORK_DIR", "LEARN_OUTLINES_DIR")}
        tracks, odir, work = (os.path.join(cls.tmp, x) for x in ("tracks", "outlines", "work"))
        os.environ.update(LEARN_TRACKS_DIR=tracks, LEARN_WORK_DIR=work, LEARN_OUTLINES_DIR=odir)
        for tid in cls.BUILT:
            root = os.path.join(tracks, tid)
            write(os.path.join(root, "track.py"), SAMPLE_TRACK)
            write(os.path.join(root, "lessons", "01-basics", "README.md"), "---\nid: 01\ntitle: Basics\n---\n")
            write(os.path.join(root, "lessons", "01-basics", "01.01-one.md"), "---\nid: 01.01\ntitle: One\n---\n\n# 01.01 One\n\nProse.\n")
        for n, oid in enumerate(cls.PLANNED, 1):
            write(os.path.join(odir, f"{n:02d}-{oid}.md"), OUTLINE.format(id=oid))
        write(os.path.join(odir, "99-clash.md"), OUTLINE.format(id="alpha"))   # a built track's id: not listed twice
        from harness import core, workspace
        cls.core, cls.ws = core, workspace
        cls.old = (core.TRACKS_DIR, workspace.WORK_DIR, outlines.OUTLINES_DIR)
        core.TRACKS_DIR, workspace.WORK_DIR, outlines.OUTLINES_DIR = tracks, work, odir

    @classmethod
    def tearDownClass(cls):
        cls.core.TRACKS_DIR, cls.ws.WORK_DIR, outlines.OUTLINES_DIR = cls.old
        restore_env(cls.saved)
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_home_top_bar_links_every_track_then_every_outline(self):
        from harness.web import views
        self.assertEqual([t.id for t in views.tracks()] + [o.id for o in views.outlines()], self.BUILT + self.PLANNED)
        home = views.home_page()
        nav = re.search(r'<nav class="nav-links" aria-label="Tracks">(.*?)</nav>', home, re.S).group(1)
        links = re.findall(r'<a class="nav-link( is-soon)?" href="/t/([^"]+)">([^<]+)</a>', nav)
        self.assertEqual(len(links), nav.count("<a "))                      # nothing else in the bar
        self.assertGreater(len(links), 4)
        self.assertEqual([href for _, href, _ in links], self.BUILT + self.PLANNED)
        self.assertEqual([text for _, _, text in links], self.BUILT + self.PLANNED)
        self.assertEqual([bool(soon) for soon, _, _ in links], [False] * len(self.BUILT) + [True] * len(self.PLANNED))

    def test_css_scrolls_the_bar_instead_of_overflowing(self):
        with open(os.path.join(self.core.ROOT, "harness", "web", "app.css"), encoding="utf-8") as f:
            css = f.read()
        rule = re.search(r"\n\.nav-links \{([^}]*)\}", css).group(1)
        for decl in ("min-width: 0", "overflow-x: auto", "scrollbar-width: none"):
            self.assertIn(decl, rule)
        self.assertIn(".nav-link.is-soon { color: var(--fg3); }", css)
        self.assertIn("body.home .topbar-in > .btn { flex: none; }", css)


if __name__ == "__main__":
    unittest.main()
