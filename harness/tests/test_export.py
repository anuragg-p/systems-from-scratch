"""Tests for ./learn export: the site as plain files for a static host (harness/web/export.py)."""

import contextlib
import io
import json
import os
import re
import shutil
import tempfile
import unittest

from harness import outlines as outlines_mod

TRACK = '''
TITLE = "Exported"
KIND = "demo"
SUMMARY = "A track for the export tests."
SOURCES = ["src/*.c"]
STUBS = {".c": 'panic("{id}: {title} not written yet");'}
FILES_FROM = {"notes.txt": "01.01"}


def prepare(root):
    return ["true"]


def run_argv(root):
    return ["cat"]
'''

A_C = """int base(void) { return 1; }

int add(int a, int b)
{
    // @build 01.01 adder
    // Return the sum.
    return a + b;
    // @end
}
"""

B_C = """// @build 01.02 doubler
// Return twice the argument.
int twice(int a) { return 2 * a; }
// @end
"""

DOC = """---
id: {id}
title: {title}
labels: with code
---

# {id} {title}

Intro for {id}, see [the other one]({other}).

## The idea

IDEA-{id}.

## Run it

RUN-{id}.
<!-- verify: fact cmd='echo 1' expect=1 -->
1 line, and an inline <!-- verify: secret --> note.

<!-- verify: session run="./learn run exp --at {id}"
lines 1-2 unordered
-->
```
OUT-{id}-A
OUT-{id}-B
```
"""


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class ExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="learn-export-test-")
        root = os.path.join(cls.tmp, "tracks", "exp")
        write(os.path.join(root, "track.py"), TRACK)
        write(os.path.join(root, "src", "a.c"), A_C)
        write(os.path.join(root, "src", "b.c"), B_C)
        write(os.path.join(root, "notes.txt"), "plain notes\n")
        write(os.path.join(root, "lessons", "01-basics", "README.md"), "---\nid: 01\ntitle: Basics\n---\n")
        write(os.path.join(root, "lessons", "01-basics", "01.01-adder.md"),
              DOC.format(id="01.01", title="Adder", other="01.02-doubler.md"))
        write(os.path.join(root, "lessons", "01-basics", "01.02-doubler.md"),
              DOC.format(id="01.02", title="Doubler", other="01.01-adder.md"))
        from harness import core, workspace
        cls.core, cls.ws = core, workspace
        cls.saved = (core.ROOT, core.TRACKS_DIR, workspace.WORK_DIR, outlines_mod.OUTLINES_DIR)
        core.ROOT = cls.tmp           # the checkout: code locations are shown relative to it
        core.TRACKS_DIR = os.path.join(cls.tmp, "tracks")
        workspace.WORK_DIR = os.path.join(cls.tmp, "work-none")
        outlines_mod.OUTLINES_DIR = os.path.join(cls.tmp, "no-outlines")
        from harness.web import export
        cls.export = export
        cls.out = os.path.join(cls.tmp, "site")
        cls.stats = export.export(cls.out)

    @classmethod
    def tearDownClass(cls):
        core, ws = cls.core, cls.ws
        core.ROOT, core.TRACKS_DIR, ws.WORK_DIR, outlines_mod.OUTLINES_DIR = cls.saved
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def path(self, *parts):
        return os.path.join(self.out, *parts)

    def pages(self):
        for dirpath, _, names in os.walk(self.out):
            for n in names:
                if n.endswith(".html"):
                    yield os.path.join(dirpath, n)

    def resolves(self, url):
        """Does a static host find a file for url (a directory's index.html for "/...")?"""
        full = os.path.join(self.out, *[p for p in url.split("/") if p])
        return os.path.isfile(os.path.join(full, "index.html") if url.endswith("/") else full)

    def test_every_page_and_asset_is_written(self):
        for parts in (("index.html",), ("404.html",), ("t", "exp", "index.html"), ("t", "exp", "01.01", "index.html"),
                      ("t", "exp", "01.02", "index.html"), ("credits", "index.html"), ("static", "app.css"),
                      ("static", "app.js"), ("static", "fonts", "LICENSE-OFL.txt")):
            self.assertTrue(os.path.isfile(self.path(*parts)), parts)
        with open(self.path("static", "fonts", "Figtree.woff2"), "rb") as f:
            self.assertEqual(f.read(4), b"wOF2")
        self.assertIn("Page not found.", read(self.path("404.html")))
        self.assertEqual(self.stats["pages"], 6)
        self.assertEqual(self.stats["leaks"], [])

    def test_authors_annotations_never_reach_a_page(self):
        for page in self.pages():
            text = read(page)
            self.assertNotIn("verify", text, page)
            self.assertNotIn("&lt;!--", text, page)
            self.assertNotIn("<!--", text, page)
        lesson = read(self.path("t", "exp", "01.01", "index.html"))
        self.assertIn("RUN-01.01.", lesson)
        self.assertIn("OUT-01.01-A", lesson)

    def test_every_link_and_script_resolves_in_its_directory_form(self):
        for page in self.pages():
            text = read(page)
            for attr, url in re.findall(r'\s(href|src)="(/[^"#]*)', text):
                self.assertTrue(self.resolves(url), f"{page}: {attr}={url}")
            self.assertEqual(re.findall(r'href="/t/[^"#]*[^/"#](?=["#])', text), [], page)
        lesson = read(self.path("t", "exp", "01.01", "index.html"))
        self.assertIn('href="/t/exp/01.02/"', lesson)          # the doc's relative link and the pager
        self.assertIn('href="/t/exp/#m-01"', lesson)

    def test_lessons_need_no_server_and_no_checkout(self):
        from harness import core
        from harness.web import views
        page = read(self.path("t", "exp", "01.01", "index.html"))
        self.assertIn('data-index="/api/file/exp/01.01.json"', page)
        self.assertIn('data-files="/api/file/exp"', page)
        for word in ("vscode:", "data-editor", "Open in editor", self.tmp, "Run test", "learn test", "passing"):
            self.assertNotIn(word, page)
        self.assertIn('data-copy="tracks/exp/src/a.c:1"', page)   # the location stays, as text with Copy
        self.assertNotIn("learn run", page)                    # the doc's Run it is the only command shown
        self.assertIn("RUN-01.01", page)
        track = core.discover_tracks()[0]
        served = views.lesson_page(track, track.lessons[0])
        self.assertIn("data-editor", served)                   # ./learn serve is unchanged
        self.assertNotIn("data-index", served)

    def test_files_drawer_index_points_at_each_view_stored_once(self):
        from harness import core
        from harness.web import views
        at1 = json.loads(read(self.path("api", "file", "exp", "01.01.json")))
        at2 = json.loads(read(self.path("api", "file", "exp", "01.02.json")))
        page = read(self.path("t", "exp", "01.01", "index.html"))
        self.assertEqual(set(re.findall(r'class="ft-file[^"]*" data-path="([^"]+)"', page)), set(at1))
        self.assertEqual(sorted(at1), ["notes.txt", "src/a.c"])          # b.c comes with 01.02
        self.assertEqual(sorted(at2), ["notes.txt", "src/a.c", "src/b.c"])
        self.assertEqual(at1["notes.txt"], at2["notes.txt"])              # the same view, stored once
        self.assertNotEqual(at1["src/a.c"], at2["src/a.c"])               # 01.01 bands its own code
        self.assertEqual(self.stats["views"], 5)
        self.assertEqual(self.stats["stored"], 4)
        track = core.discover_tracks()[0]
        for lid, index in (("01.01", at1), ("01.02", at2)):
            for rel, url in index.items():
                self.assertTrue(re.match(r"^/api/file/exp/v/[0-9a-f]{20}\.json$", url), url)
                got = json.loads(read(self.path(*url.split("/"))))
                want = views.render_file_view(track, lid, rel)
                for j in (got, want):
                    j["html"] = re.sub(r"fv-fold-\d+", "fv-fold-N", j["html"])
                self.assertEqual(got, want, (lid, rel))
        self.assertIn("row band", read(self.path(*at1["src/a.c"].split("/"))))

    def test_a_path_of_this_machine_is_reported(self):
        from harness import core
        self.assertEqual(self.export.leaks(self.out), [])
        out = os.path.join(self.tmp, "leaky")
        write(os.path.join(out, "t", "x", "index.html"), f"<p>{core.TRACKS_DIR}/exp/src/a.c</p>")
        write(os.path.join(out, "static", "font.woff2"), core.ROOT)          # only text files are read
        self.assertEqual(self.export.leaks(out), [(os.path.join("t", "x", "index.html"), core.TRACKS_DIR)])

    def test_only_an_earlier_export_is_replaced(self):
        from harness import core
        foreign = os.path.join(self.tmp, "foreign")
        write(os.path.join(foreign, "notes.md"), "mine\n")
        with self.assertRaises(self.export.ExportError):
            self.export.export(foreign)
        self.assertEqual(os.listdir(foreign), ["notes.md"])
        with self.assertRaises(self.export.ExportError):
            self.export.export(os.path.join(core.TRACKS_DIR, "exp", "site"))
        again = os.path.join(self.tmp, "again")
        self.export.export(again)
        write(os.path.join(again, "api", "file", "exp", "v", "stale.json"), "{}")
        write(os.path.join(again, ".vercel", "project.json"), "{}")
        write(os.path.join(again, "vercel.json"), "{}")
        self.export.export(again)
        self.assertFalse(os.path.exists(os.path.join(again, "api", "file", "exp", "v", "stale.json")))
        self.assertTrue(os.path.isfile(os.path.join(again, ".vercel", "project.json")))
        self.assertTrue(os.path.isfile(os.path.join(again, "vercel.json")))
        self.assertTrue(os.path.isfile(os.path.join(again, "t", "exp", "01.02", "index.html")))

    def test_learn_export_command(self):
        from harness import cli
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = cli.main(["export", os.path.join(self.tmp, "by-cli")])
        self.assertEqual(code, 0)
        self.assertIn("exported 6 pages", buf.getvalue())
        with self.assertRaises(SystemExit):
            cli.main(["export"])


if __name__ == "__main__":
    unittest.main()
