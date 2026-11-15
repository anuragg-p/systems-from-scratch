"""Progress and resume (harness/web/app.js, app.css): kept in the reader's browser only. The script
finds everything it needs in the pages the server already writes, so these tests hold the pages to
the hooks it reads, and the script and stylesheet to what they must contain."""

import os
import re
import unittest

from harness import core
from harness.web import views

WEB = os.path.join(core.ROOT, "harness", "web")


def read(name):
    with open(os.path.join(WEB, name), encoding="utf-8") as f:
        return f.read()


class ProgressTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.track = next(t for t in core.discover_tracks() if t.lessons)
        cls.lesson = cls.track.lessons[0]

    def test_the_script_keeps_progress_in_this_browser_only(self):
        js = read("app.js")
        self.assertIn('localStorage.setItem("progress"', js)
        self.assertIn('localStorage.getItem("progress"', js)
        block = js[js.index("// Progress, kept in this browser only"):]
        for word in ("fetch(", "XMLHttpRequest", "sendBeacon", "cookie"):
            self.assertNotIn(word, block, f"progress must not leave the browser: {word}")

    def test_the_marks_are_styled_quietly(self):
        css = read("app.css")
        self.assertIn(".side-lesson.is-read .sl-t::after", css)
        self.assertIn(".grid-card.unit.is-read .unit-code::after", css)
        self.assertIn(".read-sr", css)

    def test_a_lesson_page_has_what_the_script_reads(self):
        page = views.lesson_page(self.track, self.lesson)
        self.assertRegex(page, r'(?s)<header class="lesson-head">.*?<h1>', "the lesson's title")
        name = views.safe_track(self.track)[0]
        self.assertRegex(page, r'(?s)class="track-pill" href="/t/[^"]+"><span class="mod-ic[^"]*">.*?</span><span>'
                         + re.escape(views.esc(name)) + "</span>", "the track's name, in the pill's unclassed span")
        self.assertIn('<footer class="site-foot', page)
        self.assertIn(f'class="side-lesson active" href="/t/{self.track.id}/{self.lesson.id}"', page)

    def test_the_overview_and_home_have_a_place_for_the_way_back(self):
        overview = views.track_page(self.track)
        self.assertIn('<section class="strip-card"><span class="strip-text">', overview)
        self.assertIn(f'class="grid-card unit" href="/t/{self.track.id}/{self.lesson.id}"', overview)
        home = views.home_page()
        self.assertIn('<body class="home">', home)
        self.assertIn('<div class="hero-cta">', home)

    def test_the_lesson_pattern_matches_both_kinds_of_url(self):
        js = read("app.js")
        pattern = re.search(r"var LESSON = /(.*)/;", js).group(1).replace("\\/", "/")
        rx = re.compile(pattern)
        for url in ("/t/research/03.02", "/t/research/03.02/", "/t/research/03.02/index.html"):
            self.assertEqual(rx.search(url).groups(), ("research", "03.02"), url)
        self.assertIsNone(rx.search("/t/research"))


if __name__ == "__main__":
    unittest.main()
