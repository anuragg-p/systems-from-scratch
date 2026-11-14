"""Tests for credits: a track's UPSTREAM on its overview, home card and lessons, /credits with
the licence in full, and the static export of it (harness/web/views.py, export.py)."""

import http.client
import os
import re
import shutil
import tempfile
import threading
import unittest

from harness import outlines as outlines_mod

COPYRIGHT = "Copyright (c) 2001 Example Authors <&> Co"
LICENCE = f"""The thing software is:

{COPYRIGHT}

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software.
"""

BASED = '''
TITLE = "Based"
KIND = "demo"
SUMMARY = "A track whose code is derived from another project's."
SOURCES = ["src/*.c"]
STUBS = {".c": 'panic("{id}: {title} not written yet");'}
FILES_FROM = {"LICENSE": "01.01"}
UPSTREAM = {"name": "thing", "url": "https://github.com/example/thing", "licence": "MIT",
            "copyright": "Copyright (c) 2001 Example Authors <&> Co",
            "owes": "The code taught here is thing's, with this course's lessons.",
            "derived": True, "licence_file": "LICENSE", "chip": "based on thing"}
'''

PLAIN = '''
TITLE = "Plain"
KIND = "demo"
SUMMARY = "Our own code, written to someone else's format."
UPSTREAM = [{"name": "Format", "url": "https://example.com/format", "licence": "Public domain",
             "owes": "Our own engine, written to the format.", "derived": False,
             "also": [("The spec", "https://example.com/spec"), ("Bad", "javascript:alert(1)")],
             "licence_file": "../cbased/LICENSE"}]
'''

EVIL = '''
TITLE = "Evil"
KIND = "demo"
SUMMARY = "An upstream that must not be shown."
UPSTREAM = {"name": "evil", "url": "javascript:alert(1)", "licence": "MIT"}
'''

NONE = '''
TITLE = "Nothing"
KIND = "demo"
SUMMARY = "A track built on nothing in particular."
'''

A_C = """int add(int a, int b)
{
    // @build 01.01 adder
    // Return the sum.
    return a + b;
    // @end
}
"""

DOC = """---
id: 01.01
title: Adder
labels: with code
---

# 01.01 Adder

Intro.

## The idea

IDEA.
"""

OUTLINE = """---
id: soon
title: A planned track
status: coming soon
upstream: Proposed, not decided: [bigrepo](https://github.com/example/bigrepo) (MIT)
---

# A planned track

What it is.

## Module 00 - Start

- Goal: Start.
- You build: A thing.
- Value: It helps.
- Lessons:
  - 00.01 First
- Learn from: [K]

## Library

| Key | Kind | Title | By | Where |
|---|---|---|---|---|
| K | book | A book | Someone | 2020 |
"""


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class CreditsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="learn-credits-test-")
        tracks = os.path.join(cls.tmp, "tracks")
        based = os.path.join(tracks, "cbased")
        write(os.path.join(based, "track.py"), BASED)
        write(os.path.join(based, "LICENSE"), LICENCE)
        write(os.path.join(based, "src", "a.c"), A_C)
        write(os.path.join(based, "lessons", "01-basics", "README.md"), "---\nid: 01\ntitle: Basics\n---\n")
        write(os.path.join(based, "lessons", "01-basics", "01.01-adder.md"), DOC)
        for tid, src in (("cplain", PLAIN), ("cevil", EVIL), ("cnone", NONE)):
            write(os.path.join(tracks, tid, "track.py"), src)
            write(os.path.join(tracks, tid, "lessons", "01-basics", "README.md"), "---\nid: 01\ntitle: Basics\n---\n")
            write(os.path.join(tracks, tid, "lessons", "01-basics", "01.01-adder.md"), DOC)
        write(os.path.join(cls.tmp, "outlines", "soon.md"), OUTLINE)
        from harness import core, workspace
        cls.core, cls.ws = core, workspace
        cls.saved = (core.ROOT, core.TRACKS_DIR, workspace.WORK_DIR, outlines_mod.OUTLINES_DIR)
        core.ROOT = cls.tmp
        core.TRACKS_DIR = tracks
        workspace.WORK_DIR = os.path.join(cls.tmp, "work-none")
        outlines_mod.OUTLINES_DIR = os.path.join(cls.tmp, "outlines")
        from harness.web import views
        cls.views = views
        cls.track = {t.id: t for t in views.tracks()}

    @classmethod
    def tearDownClass(cls):
        core, ws = cls.core, cls.ws
        core.ROOT, core.TRACKS_DIR, ws.WORK_DIR, outlines_mod.OUTLINES_DIR = cls.saved
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_upstreams_are_read_and_unsafe_ones_dropped(self):
        v = self.views
        self.assertEqual([u["name"] for u in v.upstreams(self.track["cbased"])], ["thing"])
        self.assertEqual([u["name"] for u in v.upstreams(self.track["cplain"])], ["Format"])   # a list works too
        self.assertEqual(v.upstreams(self.track["cevil"]), [])                                  # not an http(s) URL
        self.assertEqual(v.upstreams(self.track["cnone"]), [])
        self.assertEqual(v.licence_label({"licence": "MIT"}), "MIT licence")
        self.assertEqual(v.licence_label({"licence": "Public domain"}), "Public domain")
        self.assertEqual(v.licence_text(self.track["cplain"], {"licence_file": "../cbased/LICENSE"}), "")
        self.assertIn(COPYRIGHT, v.licence_text(self.track["cbased"], {"licence_file": "LICENSE"}))

    def test_the_overview_says_what_the_track_is_built_on(self):
        page = self.views.track_page(self.track["cbased"])
        hero = page[page.index('class="ov-hero"'):page.index("</section>", page.index('class="ov-hero"'))]
        self.assertIn("Built on", hero)
        self.assertIn('href="https://github.com/example/thing" target="_blank" rel="noopener noreferrer"', hero)
        self.assertIn("MIT licence", hero)
        self.assertIn("The code taught here is thing&#x27;s, with this course&#x27;s lessons.", hero)
        self.assertIn('href="/credits#cbased"', hero)
        self.assertNotIn('class="upstream"', self.views.track_page(self.track["cnone"]))
        self.assertNotIn("javascript:", self.views.track_page(self.track["cevil"]))

    def test_the_home_card_carries_a_quiet_chip(self):
        home = self.views.home_page()
        self.assertIn('<span class="pill up-chip">based on thing</span>', home)
        self.assertIn('<span class="pill up-chip">based on Format</span>', home)   # no chip given: "based on <name>"
        self.assertEqual(home.count("up-chip"), 2)

    def test_every_page_links_to_credits_and_a_derived_tracks_lessons_name_it(self):
        v = self.views
        based, plain = self.track["cbased"], self.track["cplain"]
        lesson = v.lesson_page(based, based.lessons[0])
        foot = lesson[lesson.index('<footer class="site-foot'):]
        self.assertIn('<a class="sf-link" href="/credits#cbased">Code derived from thing, MIT licence</a>', foot)
        self.assertIn('href="/credits">Credits</a>', foot)
        other = v.lesson_page(plain, plain.lessons[0])
        self.assertNotIn("Code derived from", other)                 # written to a format, not derived from code
        for page in (v.home_page(), v.track_page(based), other, v.credits_page(), v.outline_page(v.outlines()[0])):
            self.assertIn('href="/credits">Credits</a></footer>', page)

    def test_the_licence_file_is_in_the_drawer_not_under_the_code(self):
        v = self.views
        based = self.track["cbased"]
        page = v.lesson_page(based, based.lessons[0])
        self.assertIn('data-path="LICENSE"', page)                   # it comes with the project's files
        self.assertNotIn('data-open="LICENSE"', page)                # the drawer opens on code
        self.assertNotIn("tracks/cbased/LICENSE", page)              # and The code shows code only
        self.assertIn("tracks/cbased/src/a.c", page)

    def test_credits_page_prints_each_upstream_and_the_licence_whole(self):
        page = self.views.credits_page()
        based = page[page.index('id="cbased"'):page.index("</section>", page.index('id="cbased"'))]
        self.assertIn('href="https://github.com/example/thing"', based)
        self.assertIn("Copyright (c) 2001 Example Authors &lt;&amp;&gt; Co", based)
        self.assertIn('<div class="licence-text"><p>The thing software is:</p><p>Copyright (c) 2001 Example Authors '
                      '&lt;&amp;&gt; Co</p><p>Permission is hereby granted, free of charge, to any person obtaining '
                      'a copy of this software.</p></div>', based)       # word for word, paragraphs reflowed
        plain = page[page.index('id="cplain"'):page.index("</section>", page.index('id="cplain"'))]
        self.assertIn("Public domain", plain)
        self.assertIn('href="https://example.com/spec"', plain)
        self.assertNotIn("javascript:", page)
        self.assertNotIn("Permission is hereby granted", plain)      # its licence_file points outside its track
        self.assertNotIn('id="cnone"', page)
        self.assertNotIn('id="cevil"', page)
        self.assertIn("/static/fonts/LICENSE-OFL.txt", page)         # and what the site itself ships

    def test_an_outline_names_what_it_is_planned_to_follow(self):
        page = self.views.outline_page(self.views.outlines()[0])
        self.assertIn("<dt>Planned to follow</dt>", page)
        self.assertIn("Proposed, not decided:", page)
        self.assertIn('href="https://github.com/example/bigrepo"', page)

    def test_the_server_serves_credits(self):
        from harness.web.server import WebServer
        srv = WebServer(0)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            for path in ("/credits", "/credits/"):
                c = http.client.HTTPConnection("127.0.0.1", srv.server_address[1], timeout=30)
                c.request("GET", path)
                r = c.getresponse()
                body = r.read().decode("utf-8")
                c.close()
                self.assertEqual(r.status, 200, path)
                self.assertIn("Copyright (c) 2001 Example Authors &lt;&amp;&gt; Co", body)
        finally:
            srv.shutdown()
            srv.server_close()

    def test_the_export_includes_credits(self):
        from harness.web import export
        out = os.path.join(self.tmp, "site")
        stats = export.export(out)
        self.assertEqual(stats["leaks"], [])
        credits = read(os.path.join(out, "credits", "index.html"))
        self.assertIn("Copyright (c) 2001 Example Authors &lt;&amp;&gt; Co", credits)
        lesson = read(os.path.join(out, "t", "cbased", "01.01", "index.html"))
        self.assertIn('href="/credits/#cbased"', lesson)            # the directory form a static host serves
        self.assertIn('href="/credits/">Credits</a>', lesson)
        self.assertEqual(re.findall(r'href="/credits[#"]', lesson), [])
        index = read(os.path.join(out, "api", "file", "cbased", "01.01.json"))
        self.assertIn('"LICENSE"', index)                            # the drawer has the licence in the export too
        export.export(out)                                           # an earlier export, credits/ and all, is replaced


if __name__ == "__main__":
    unittest.main()
