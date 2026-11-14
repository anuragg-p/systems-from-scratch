"""Optional modules (extensions): the flag, how the site shows them, and the command-line workspace flow.

The sample track has one core module and two optional ones:

    01 Basics    01.01 adder, 01.02 doubler (regions), 01.03 a lab (no regions)
    02 Network   02.01 send, 02.02 recv          optional: true
    03 GUI       03.01 draw                      optional: true
"""

import contextlib
import io
import json
import os
import re
import shutil
import tempfile
import threading
import unittest

from harness import outlines as outlines_mod
from harness.tests.test_web import http_req, plain, restore_env, write

KERN = '''
TITLE = "Kern"
KIND = "demo"
SUMMARY = "A core and two extensions."
SOURCES = ["src/*.c"]
STUBS = {".c": 'panic("{id}: {title} not written yet");'}


def build(t):
    pass


def prepare(root):
    return None


def run_argv(root):
    return ["cat"]
'''

PLAIN = KERN.replace('"Kern"', '"Plain"')


def region(lid, title, code):
    return f"// @build {lid} {title}\n// Write {title}.\n{code}\n// @end\n"


def lesson_doc(lid, title):
    return f"---\nid: {lid}\ntitle: {title}\nlabels: with code\n---\n\n# {lid} {title}\n\nIntro for {title}.\n"


def lesson_test(lid, title, src):
    """Fails while the lesson's stub (which names the lesson) is in the file."""
    return (f'"""{lid} {title}\n"""\nimport os\nfrom harness.core import Fail\n\n\ndef test(t):\n'
            f'    with open(os.path.join(t.root, "src", "{src}")) as f:\n'
            f'        if "{lid}:" in f.read():\n            raise Fail("{title} is not written yet")\n')


LESSONS = [
    # module dir, readme front matter, lesson id, title, source file or None (a lab)
    ("01-basics", "id: 01\ntitle: Basics", "01.01", "Adder", "core.c"),
    ("01-basics", "id: 01\ntitle: Basics", "01.02", "Doubler", "core.c"),
    ("01-basics", "id: 01\ntitle: Basics", "01.03", "A lab", None),
    ("02-network", "id: 02\ntitle: Network\noptional: true", "02.01", "Send", "net.c"),
    ("02-network", "id: 02\ntitle: Network\noptional: true", "02.02", "Recv", "net.c"),
    ("03-gui", "id: 03\ntitle: GUI\noptional: true", "03.01", "Draw", "gui.c"),
]


def make_track(root, title_py, optional=True):
    write(os.path.join(root, "track.py"), title_py)
    sources = {}
    for mdir, head, lid, title, src in LESSONS:
        if not optional:
            head = head.replace("\noptional: true", "")
        write(os.path.join(root, "lessons", mdir, "README.md"), f"---\n{head}\n---\n\n# Module\n")
        write(os.path.join(root, "lessons", mdir, f"{lid}-{title.lower().replace(' ', '-')}.md"), lesson_doc(lid, title))
        test_name = f"{lid.replace('.', '')}_{title.lower().replace(' ', '_')}.py"
        if src:
            sources[src] = sources.get(src, "int top;\n") + region(lid, title.lower(), f"int ref_{lid.replace('.', '_')} = 1;")
            write(os.path.join(root, "tests", test_name), lesson_test(lid, title.lower(), src))
        else:
            write(os.path.join(root, "tests", test_name), f'"""{lid} {title}\n"""\n\n\ndef test(t):\n    pass\n')
    for src, text in sources.items():
        write(os.path.join(root, "src", src), text)


def run_cli(*args):
    """(exit code or message, stdout) of ./learn with these arguments."""
    from harness import cli
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        try:
            code = cli.main(list(args))
        except SystemExit as e:
            code = e.code
    return code, out.getvalue()


class FlagTests(unittest.TestCase):
    """core.py reads `optional` from a module README's front matter; lessons inherit it."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="learn-flag-test-")
        from harness import core
        self.core, self.old = core, core.TRACKS_DIR
        core.TRACKS_DIR = self.tmp

    def tearDown(self):
        self.core.TRACKS_DIR = self.old
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_values_that_mean_optional(self):
        root = os.path.join(self.tmp, "flags")
        write(os.path.join(root, "track.py"), KERN)
        values = {"01": None, "02": "true", "03": "True", "04": "yes", "05": "false", "06": "no", "07": "", "08": "maybe", "09": "1"}
        for mid, value in values.items():
            head = f"id: {mid}\ntitle: M{mid}" + (f"\noptional: {value}" if value is not None else "")
            write(os.path.join(root, "lessons", f"{mid}-m", "README.md"), f"---\n{head}\n---\n")
            write(os.path.join(root, "lessons", f"{mid}-m", f"{mid}.01-x.md"), lesson_doc(f"{mid}.01", "X"))
        write(os.path.join(root, "lessons", "10-empty", "README.md"), "---\nid: 10\ntitle: Empty\noptional: true\n---\n")
        write(os.path.join(root, "tests", "0402_only_a_test.py"), '"""04.02 Only a test\n"""\n')
        track = self.core.Track("flags")
        want = {"01": False, "02": True, "03": True, "04": True, "05": False, "06": False, "07": False, "08": False, "09": False}
        self.assertEqual({mid: track.modules[mid].optional for mid in want}, want)
        self.assertEqual({l.id: l.optional for l in track.lessons if l.id.endswith(".01")}, {f"{m}.01": v for m, v in want.items()})
        self.assertTrue(next(l for l in track.lessons if l.id == "04.02").optional)       # a test with no doc: its module's flag
        self.assertTrue(track.is_optional("02.01") and track.is_optional("02"))
        self.assertFalse(track.is_optional("01.01") or track.is_optional("99.01") or track.is_optional(""))
        self.assertEqual([m.id for m in track.optional_modules], ["02", "03", "04"])     # 10 has no lessons
        self.assertEqual([l.id for l in track.core_lessons], ["01.01", "05.01", "06.01", "07.01", "08.01", "09.01"])
        self.assertEqual(next(l for l in track.lessons if l.id == "02.01").module, ("02", "M02"))   # the tuple is unchanged


class ExtensionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="learn-ext-test-")
        cls.work = os.path.join(cls.tmp, "work")
        cls.saved = {k: os.environ.get(k) for k in ("LEARN_TRACKS_DIR", "LEARN_WORK_DIR")}
        os.environ["LEARN_TRACKS_DIR"] = os.path.join(cls.tmp, "tracks")
        os.environ["LEARN_WORK_DIR"] = cls.work
        cls.root = os.path.join(cls.tmp, "tracks", "kern")
        make_track(cls.root, KERN)
        make_track(os.path.join(cls.tmp, "tracks", "plain"), PLAIN, optional=False)
        from harness import core, workspace
        cls.core, cls.ws = core, workspace
        cls.old = (core.TRACKS_DIR, workspace.WORK_DIR)
        core.TRACKS_DIR = os.path.join(cls.tmp, "tracks")
        workspace.WORK_DIR = cls.work
        cls.old_outlines = outlines_mod.OUTLINES_DIR
        outlines_mod.OUTLINES_DIR = os.path.join(cls.tmp, "no-outlines")
        from harness.web.server import WebServer
        cls.srv = WebServer(0)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.core.TRACKS_DIR, cls.ws.WORK_DIR = cls.old
        outlines_mod.OUTLINES_DIR = cls.old_outlines
        restore_env(cls.saved)
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        shutil.rmtree(self.work, ignore_errors=True)
        for tid in ("kern", "plain"):
            shutil.rmtree(os.path.join(self.tmp, "tracks", tid, ".test-logs"), ignore_errors=True)

    # ---- helpers

    def page(self, path):
        status, body = http_req(self.port, "GET", path)
        self.assertEqual(status, 200, path)
        return body

    def track(self):
        return self.core.Track("kern")

    def state(self):
        with open(os.path.join(self.work, "kern", ".learn.json")) as f:
            return json.load(f)

    def src(self, name):
        with open(os.path.join(self.work, "kern", "src", name)) as f:
            return f.read()

    def start(self):
        self.assertEqual(self.ws.start(self.track())[0], "01.01")

    def finish_core(self):
        self.start()
        self.assertEqual(self.ws.advance(self.track(), use_solution=True)[0], "01.02")
        self.assertEqual(self.ws.advance(self.track(), use_solution=True), (None, []))

    def write_lesson(self, lid, title):
        """Play the learner: replace the stub of one lesson with code of their own."""
        path = {"01": "core.c", "02": "net.c", "03": "gui.c"}[lid[:2]]
        text = self.src(path)
        stub = f'panic("{lid}: {title} not written yet");'
        self.assertIn(stub, text)
        with open(os.path.join(self.work, "kern", "src", path), "w") as f:
            f.write(text.replace(stub, f"int mine_{lid.replace('.', '_')} = 1;"))

    @staticmethod
    def bar(page):
        i = page.index('<nav class="lesson-bar"')
        return page[i:page.index("</nav>", i)]

    @staticmethod
    def side(page):
        i = page.index('<aside class="side"')
        return page[i:page.index("</aside>", i)]

    # ---- the site: sidebar

    def test_sidebar_without_optional_modules_has_no_extensions_row(self):
        for path in ("/t/plain", "/t/plain/01.01"):
            page = self.page(path)
            for word in ("ext-toggle", "Extensions", "opt-tag", "optional", 'id="ext"'):
                self.assertNotIn(word, page, f"{word!r} on {path}")

    def test_sidebar_lists_extensions_behind_a_collapsed_button(self):
        side = self.side(self.page("/t/kern"))
        self.assertRegex(side, r'<button class="ext-toggle" type="button" id="ext-toggle" aria-expanded="false" aria-controls="ext-list">'
                               r'<span class="ext-ic"><svg class="ic plus"')
        self.assertIn('<div class="ext-list" id="ext-list" hidden>', side)
        self.assertIn('data-force="0"', side)
        self.assertLess(side.index('<span class="mn">01</span>'), side.index("ext-toggle"))       # after the core modules
        listed = side[side.index('id="ext-list"'):]
        self.assertNotIn('<span class="mn">01</span>', listed)                                    # core modules stay above
        for mid, title, n in (("02", "Network", 2), ("03", "GUI", 1)):                           # like core rows, plus the tag
            self.assertRegex(listed, rf'<summary><span class="mn">{mid}</span><svg[^>]*>.*?</svg><span class="mt">{title}</span>'
                                     rf'<span class="opt-tag">optional</span><span class="mc">{n}</span></summary>')
        self.assertEqual(listed.count("opt-tag"), 2)
        self.assertIn('<span class="mc">2</span></button>', side)                               # two optional modules
        self.assertIn('localStorage.getItem("ext:"+', side)                                      # the remembered choice
        js = http_req(self.port, "GET", "/static/app.js")[1]
        self.assertIn('localStorage.setItem("ext:"', js)
        self.assertIn('"aria-expanded"', js)
        for word in ("here", "built", "Workspace"):                                              # no workspace markers
            self.assertNotIn(f">{word}<", side)

    def test_sidebar_opens_on_an_optional_lesson_and_ignores_any_workspace(self):
        side = self.side(self.page("/t/kern/02.02"))
        self.assertIn('aria-expanded="true"', side)
        self.assertIn('<div class="ext-list" id="ext-list">', side)
        self.assertIn('data-force="1"', side)                                                     # always shown there
        self.assertRegex(side, r'<details class="mod" open><summary><span class="mn">02</span>')
        self.assertIn('class="side-lesson active" href="/t/kern/02.02"', side)
        self.start()
        self.ws.extend(self.track(), "02", fill_core=True)                                       # the CLI is in an extension
        side = self.side(self.page("/t/kern/01.01"))
        self.assertIn('aria-expanded="false"', side)                                             # the site does not care

    # ---- the site: overview, pager, home

    def test_overview_groups_core_then_extensions(self):
        self.start()                                                                              # a workspace changes nothing
        page = self.page("/t/kern")
        order = [page.index(x) for x in ('id="m-01"', 'id="extensions"', 'id="m-02"', 'id="m-03"')]
        self.assertEqual(order, sorted(order))
        self.assertIn('<h2 class="divider-label" id="extensions"><span>Extensions</span></h2>', page)
        lede = re.search(r'<p class="ext-lede">(.*?)</p>', page).group(1)
        self.assertIn("Optional", lede)
        self.assertIn("independent of the others", lede)
        self.assertEqual(lede.count(". "), 0)                                                     # one sentence
        for mid, title in (("02", "Network"), ("03", "GUI")):                                    # the same layout as core
            sec = page[page.index(f'id="m-{mid}"'):]
            sec = sec[:sec.index("</section>")]
            self.assertIn('<div class="module-strip">', sec)
            self.assertIn('class="unit-grid"', sec)
            self.assertIn(f"<h2>{title}</h2>", sec)
        self.assertIn("2 lessons &middot; optional", page)                                         # the structure panel
        self.assertIn("3 lessons &middot; 2 extensions", page)                                     # the strip counts the core
        for word in ("ext-count", "data-extend", "fill_core", " built", "Start this extension", "Continue"):
            self.assertNotIn(word, page)
        self.assertIn('href="/t/kern/01.01"><span>Start with 01.01 Adder</span>', page)

    def test_pager_stays_on_the_core_or_its_extension(self):
        last_core = self.bar(self.page("/t/kern/01.03"))
        self.assertIn("<em>3/3</em>", last_core)
        self.assertNotIn("Next", last_core)                                                       # the core ends here
        self.assertNotIn('href="/t/kern/02.01"', last_core)
        ext = self.bar(self.page("/t/kern/02.01"))
        self.assertIn("<span>Network</span><em>1/2</em>", ext)                                    # position in the module
        self.assertNotIn('href="/t/kern/01.03"', ext)
        self.assertRegex(ext, r'<a class="btn primary" href="/t/kern/02.02" rel="next"')
        self.assertNotIn('href="/t/kern/03.01"', self.bar(self.page("/t/kern/02.02")))
        page = self.page("/t/kern/02.01")
        self.assertIn('<span class="tag opt">optional</span>', page)
        self.assertIn("int ref_02_01 = 1;", plain(page))                                                 # the reference code, as anywhere

    def test_an_extension_s_files_stay_on_its_own_path(self):
        def drawer(lid):
            page = self.page(f"/t/kern/{lid}")
            return re.findall(r'data-path="([^"]+)"', page[page.index('<div class="drawer"'):])
        self.assertNotIn("src/net.c", drawer("01.03"))                                         # the core never has it
        self.assertNotIn("src/gui.c", drawer("01.03"))
        self.assertIn("src/net.c", drawer("02.01"))                                            # its extension does
        self.assertNotIn("src/gui.c", drawer("02.02"))                                         # and not the other one's
        self.assertIn("src/gui.c", drawer("03.01"))
        self.assertNotIn("src/net.c", drawer("03.01"))
        self.assertIn("src/core.c", drawer("03.01"))                                           # on top of the whole core

    def test_home_card_counts_lessons_and_extensions(self):
        home = self.page("/")
        card = home[home.index('<a class="grid-card track-card" href="/t/kern">'):]
        card = card[:card.index("</a>")]
        self.assertIn('<span class="pill">3 lessons</span><span class="pill">2 extensions</span>', card)
        card = home[home.index('<a class="grid-card track-card" href="/t/plain">'):]
        card = card[:card.index("</a>")]
        self.assertIn('<span class="pill">6 lessons</span></span>', card)                         # all core, nothing to mention

    def test_the_extend_endpoint_is_gone(self):
        self.start()
        for path in ("/api/extend/kern/02", "/api/extend/kern/02?fill_core=1", "/api/extend/nope/02"):
            self.assertEqual(http_req(self.port, "POST", path)[0], 404, path)
        self.assertEqual(self.state(), {"current": "01.01", "done": []})

    # ---- the command line: the workspace flow

    def test_advance_stops_at_the_end_of_the_core(self):
        self.start()
        self.ws.advance(self.track(), use_solution=True)
        code, out = run_cli("next", "kern", "--use-solution")
        self.assertEqual(code, 0)
        self.assertIn("last core lesson", out)
        self.assertIn("./learn extend kern 02", out)
        self.assertIn("./learn extend kern 03", out)
        self.assertEqual(self.state(), {"current": None, "done": ["01.01", "01.02"]})
        self.assertNotIn("not written yet", self.src("net.c"))                                    # nothing of 02 was cut
        self.assertEqual(self.ws.progress(self.track(), self.state())["stage"], "core-complete")
        with self.assertRaises(self.core.Fail) as e:                                              # nothing to continue
            self.ws.advance(self.track())
        self.assertIn("no lesson in progress", str(e.exception))
        self.assertIn("./learn extend kern 02", run_cli("status", "kern")[1])

    def test_advance_stops_at_the_end_of_an_extension(self):
        self.finish_core()
        self.assertEqual(self.ws.extend(self.track(), "02")[0], "02.01")
        self.assertIn("02.01: send not written yet", self.src("net.c"))
        self.assertEqual(self.ws.advance(self.track(), use_solution=True)[0], "02.02")
        code, out = run_cli("next", "kern", "--use-solution")
        self.assertIn("last lesson of extension 02 Network", out)
        self.assertIn("./learn extend kern 03", out)
        self.assertNotIn("./learn extend kern 02", out)
        prog = self.ws.progress(self.track(), self.state())
        self.assertEqual((self.state()["current"], prog["stage"]), (None, "extension-complete"))
        self.assertNotIn("not written yet", self.src("gui.c"))                                    # 03 was never walked into

    def test_extend_refuses_while_the_core_is_unfinished(self):
        self.start()
        code, _ = run_cli("extend", "kern", "02")
        self.assertIn("2 core lessons are not built yet (01.01 01.02)", code)
        self.assertIn("./learn extend kern 02 --fill-core", code)
        self.assertEqual(self.state(), {"current": "01.01", "done": []})                          # nothing changed
        self.assertIn("01.01: adder not written yet", self.src("core.c"))

    def test_extend_with_fill_core_fills_the_rest_and_keeps_your_code(self):
        self.start()
        self.write_lesson("01.01", "adder")
        self.ws.advance(self.track())
        code, out = run_cli("extend", "kern", "02", "--fill-core")
        self.assertEqual(code, 0, out)
        self.assertIn("Extension 02 Network", out)
        self.assertIn("src/net.c", out)
        self.assertEqual(self.state(), {"current": "02.01", "done": ["01.01", "01.02"]})
        core_c = self.src("core.c")
        self.assertIn("int mine_01_01 = 1;", core_c)                                               # built by the learner: kept
        self.assertIn("int ref_01_02 = 1;", core_c)                                                # unbuilt: the reference
        self.assertNotIn("not written yet", core_c)
        self.assertIn("02.01: send not written yet", self.src("net.c"))
        self.assertNotIn("02.02:", self.src("net.c"))

    def test_extend_after_the_core_and_its_refusals(self):
        self.finish_core()
        self.assertEqual(self.ws.extend(self.track(), "03")[0], "03.01")
        self.assertIn("03.01: draw not written yet", self.src("gui.c"))
        for mid, fill, want in (("02", False, "one at a time"), ("03", False, "already building"),
                                ("01", False, "part of the core"), ("09", False, "has no module")):
            with self.assertRaises(self.core.Fail) as e:
                self.ws.extend(self.track(), mid, fill_core=fill)
            self.assertIn(want, str(e.exception), mid)
        self.write_lesson("03.01", "draw")
        self.ws.advance(self.track())
        with self.assertRaises(self.core.Fail) as e:
            self.ws.extend(self.track(), "03")
        self.assertIn("already built", str(e.exception))                                          # never cut over your code
        self.assertIn("int mine_03_01 = 1;", self.src("gui.c"))
        self.assertEqual(self.ws.extend(self.track(), "02")[0], "02.01")                          # the other one, any order

    def test_extend_copies_files_the_workspace_lacks_and_refuses_stale_ones(self):
        self.finish_core()
        os.remove(os.path.join(self.work, "kern", "src", "net.c"))                                # made before 02 existed
        self.assertEqual(self.ws.extend(self.track(), "02")[0], "02.01")
        self.assertIn("02.01: send not written yet", self.src("net.c"))
        shutil.rmtree(self.work)
        self.finish_core()
        with open(os.path.join(self.work, "kern", "src", "gui.c"), "w") as f:                     # there, but older
            f.write("int old_gui;\n")
        with self.assertRaises(self.core.Fail) as e:
            self.ws.extend(self.track(), "03")
        self.assertIn("src/gui.c", str(e.exception))
        self.assertIn("lack its @build regions", str(e.exception))
        self.assertIsNone(self.state()["current"])                                                # nothing changed

    def test_cli_extend_rejects_bad_arguments(self):
        for args, want in ((("extend", "kern", "01"), "part of the core"), (("extend", "kern", "09"), "has no module"),
                           (("extend", "kern"), "usage"), (("extend", "kern", "x2"), "usage"),
                           (("extend", "kern", "02", "--bogus"), "usage"), (("extend", "kern", "02"), "no workspace")):
            code, _ = run_cli(*args)
            self.assertIn(want, str(code), args)

    def test_an_existing_state_file_keeps_working_unchanged(self):
        self.start()
        with open(os.path.join(self.work, "kern", ".learn.json"), "w") as f:
            f.write('{\n  "current": "01.01",\n  "done": []\n}')                                  # the owner's file, as is
        self.assertEqual(self.ws.progress(self.track(), self.state())["stage"], "core")
        out = run_cli("status", "kern")[1]
        self.assertIn("Lesson 01.01 Adder", out)
        self.assertNotIn("./learn run", out)               # it runs the track's own code, not the workspace
        for path in ("/", "/t/kern", "/t/kern/01.01", "/t/kern/02.01"):
            self.page(path)
        self.assertEqual(self.ws.advance(self.track(), use_solution=True)[0], "01.02")
        self.assertEqual(self.state(), {"current": "01.02", "done": ["01.01"]})                   # no new keys
        with open(os.path.join(self.work, "kern", ".learn.json"), "w") as f:                      # lessons left, none current
            json.dump({"current": None, "done": ["01.01"]}, f)
        self.assertEqual(self.ws.progress(self.track(), self.state())["stage"], "idle")

    # ---- the command line: map and the author tools

    def test_map_counts_the_core_and_mentions_extensions(self):
        code, out = run_cli("map", "kern")
        self.assertIn("kern - Kern  [demo]  3 lessons, +2 optional modules", out)
        self.assertLess(out.index("Module 01 - Basics"), out.index("Extensions - optional"))
        self.assertLess(out.index("Extensions - optional"), out.index("Module 02 - Network  (optional)"))
        self.assertIn("Module 03 - GUI  (optional)", out)
        code, out = run_cli("map", "plain")
        self.assertIn("plain - Plain  [demo]  6 lessons\n", out)
        self.assertNotIn("optional", out)
        from harness import cli
        md = cli.map_markdown([self.track()])
        self.assertIn("- 3 lessons, +2 optional modules -", md)
        self.assertIn("**Module 02 - Network** (optional)", md)
        self.assertIn("**Extensions** - optional modules", md)

    def test_check_skeleton_and_tests_cover_optional_lessons(self):
        code, out = run_cli("check-skeleton", "kern")
        self.assertEqual(code, 0, out)
        for lid in ("01.01", "02.01", "02.02", "03.01"):
            self.assertIn(f"{lid}  cut out: builds, test fails as it should", out)
        code, out = run_cli("test", "kern", "--ref")
        self.assertEqual(code, 0, out)
        self.assertIn("all 6 passed", out)
        # in a workspace, "everything up to your lesson" follows the lesson's own path
        self.start()
        self.ws.extend(self.track(), "03", fill_core=True)
        code, out = run_cli("test", "kern")
        ran = re.findall(r"^\s+(\d\d\.\d\d) ", out, re.M)
        self.assertEqual(ran, ["01.01", "01.02", "01.03", "03.01"])
        self.assertIn("1 of 4 failed: kern/03.01", out)                                           # your hole, nothing else


if __name__ == "__main__":
    unittest.main()
