"""The project at each lesson: @from and @internal markers, materialize(), and `./learn check-timeline`.

The sample track has a core module and two optional ones, like test_extensions:

    01 Core      01.01 base, 01.02 more (regions in src/main.c), 01.03 a lab
    02 Net       02.01 send                optional: true
    03 GUI       03.01 draw                optional: true
"""

import os
import shutil
import stat
import tempfile
import unittest

from harness.tests.test_extensions import lesson_doc, run_cli
from harness.tests.test_web import write

TRACK = '''
import os

TITLE = "Tl"
KIND = "demo"
SUMMARY = "Markers."
SOURCES = ["src/*.c"]
STUBS = {".c": 'panic("{id}: {title} not written yet");'}
FILES_FROM = {"Makefile": "01.01", "src/late.h": "01.02", "src/net.c": "02.01", "src/gui.c": "03.01",
              "tools/run.sh": "01.01"}
TIMELINE_FAIL = [r"panic: "]


def prepare(root):
    # "builds" when no source file holds the word BROKEN
    return ["sh", "-c", "! grep -rq BROKEN src"]


def timeline_run(root):
    return ["sh", "tools/run.sh"]


def timeline_boot(lesson_id):
    return [(None, r"booted")] + ([("ping", r"pong")] if lesson_id >= "01.02" else [])


def timeline_after(root, lesson_id):
    # what the run left behind; tools/after-fails stands for a file another program rejects
    from harness.core import Fail
    if os.path.exists(os.path.join(root, "tools", "after-fails")):
        raise Fail("left a mess")
    return "after: clean"
'''

MAIN_C = """#include "late.h"  // @from 01.02

int top;

// @build 01.01 base
// Write base.
int base(void)
{
  start();
  // @from 01.02
  more();
  // @end
  return net();  // @from 02.01
}
// @end

// @from 01.02
// Helps more.
void
helper(void)
{
  stuff();  // comment stays @from 01.02
}
// @end

void
tail(void)
{
  // @from 01.02
  scheduler();
  // @else
  // for(;;)
  //   wait();
  // @end
  // @internal
#ifdef TEST
  selftest();
#endif
  // @end
}

void
more(void)
{
  // @build 01.02 more
  // Write more.
  x = 2;
  // @end
}
"""

MAKEFILE = """# Build it.
# @from 01.02
all: a b
# @else
# all: a
# @end
\techo built
"""

RUN_SH = """echo booted
# @from 01.02
read line
echo pong
# @end
sleep 30
"""


def make(root):
    write(os.path.join(root, "track.py"), TRACK)
    for mdir, head, lid, title in [
            ("01-core", "id: 01\ntitle: Core", "01.01", "Base"),
            ("01-core", "id: 01\ntitle: Core", "01.02", "More"),
            ("01-core", "id: 01\ntitle: Core", "01.03", "A lab"),
            ("02-net", "id: 02\ntitle: Net\noptional: true", "02.01", "Send"),
            ("03-gui", "id: 03\ntitle: GUI\noptional: true", "03.01", "Draw")]:
        write(os.path.join(root, "lessons", mdir, "README.md"), f"---\n{head}\n---\n")
        write(os.path.join(root, "lessons", mdir, f"{lid}-x.md"), lesson_doc(lid, title))
    write(os.path.join(root, "src", "main.c"), MAIN_C)
    write(os.path.join(root, "src", "late.h"), "int late;\n")
    write(os.path.join(root, "src", "net.c"), "// @build 02.01 send\n// Send.\nint send;\n// @end\n")
    write(os.path.join(root, "src", "gui.c"), "// @build 03.01 draw\n// Draw.\nint draw;\n// @end\n")
    write(os.path.join(root, "Makefile"), MAKEFILE)
    write(os.path.join(root, "tools", "run.sh"), RUN_SH)
    os.chmod(os.path.join(root, "tools", "run.sh"), 0o755)


class MarkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="learn-timeline-markers-")
        from harness import core
        cls.core, cls.old = core, core.TRACKS_DIR
        core.TRACKS_DIR = cls.tmp
        make(os.path.join(cls.tmp, "tl"))
        cls.track = core.Track("tl")

    @classmethod
    def tearDownClass(cls):
        cls.core.TRACKS_DIR = cls.old
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def project(self):
        from harness import timeline
        return timeline.Project(self.track)

    def at(self, rel, lid):
        lines, shown, band = self.project().lines_at(rel, lid)
        return [lines[i] for i in shown], {lines[i] for i in band if i in shown}

    def test_a_region_ends_at_its_own_end_not_a_nested_one(self):
        from harness import workspace as ws
        regions = ws.scan_text("src/main.c", MAIN_C)
        base = next(r for r in regions if r.lesson == "01.01")
        lines = MAIN_C.split("\n")
        self.assertEqual(lines[base.end], "// @end")
        self.assertEqual(lines[base.end - 2], "  return net();  // @from 02.01")
        self.assertEqual(base.instr_end, base.start + 2)                   # the instructions are one line

    def test_a_cut_region_takes_its_markers_with_it(self):
        from harness import workspace as ws
        root = os.path.join(self.tmp, "cut")
        shutil.copytree(self.track.root, root)
        ws.cut(self.track.module, root, "01.01")
        text = open(os.path.join(root, "src", "main.c")).read()
        self.assertIn('panic("01.01: base not written yet");', text)
        self.assertNotIn("more();", text.split("// @from 01.02\n// Helps")[0])
        self.assertEqual([r.lesson for r in ws.scan_text("src/main.c", text)], ["01.01", "01.02"])

    def test_before_its_lesson_a_block_is_gone_and_its_else_part_stands(self):
        text, _ = self.at("src/main.c", "01.01")
        joined = "\n".join(text)
        for gone in ("more();", "helper", "stuff();", "scheduler();", "late.h", "net();", "selftest", "#ifdef"):
            self.assertNotIn(gone, joined, gone)
        self.assertIn("  for(;;)\n    wait();", joined)                   # uncommented, indentation kept
        self.assertFalse(any("@" in t for t in text), text)               # no marker ever shows

    def test_from_its_lesson_on_a_block_is_there_and_banded(self):
        text, band = self.at("src/main.c", "01.02")
        joined = "\n".join(text)
        for there in ('#include "late.h"', "  more();", "helper(void)", "  stuff();  // comment stays", "  scheduler();"):
            self.assertIn(there, joined, there)
        self.assertNotIn("wait();", joined)
        self.assertNotIn("net();", joined)                                 # an extension's line, not on the core path
        self.assertIn("  scheduler();", band)
        self.assertIn('#include "late.h"', band)
        self.assertFalse(any("@" in t for t in text), text)

    def test_extensions_see_the_core_and_only_their_own_markers(self):
        net, _ = self.at("src/main.c", "02.01")
        self.assertIn("  return net();", net)
        self.assertIn("  scheduler();", net)                               # the whole core
        gui, _ = self.at("src/main.c", "03.01")
        self.assertNotIn("  return net();", gui)
        self.assertIn("  scheduler();", gui)

    def test_internal_code_is_never_shown(self):
        text, _ = self.at("src/main.c", None)
        self.assertNotIn("selftest();", "\n".join(text))
        self.assertIn("  return net();", text)                            # the end of the track has everything else

    def test_markers_in_a_makefile(self):
        early, _ = self.at("Makefile", "01.01")
        self.assertEqual(early, ["# Build it.", "all: a", "\techo built"])
        late, _ = self.at("Makefile", "01.02")
        self.assertEqual(late, ["# Build it.", "all: a b", "\techo built"])

    def test_status_whole_and_lesson_ids(self):
        proj = self.project()
        self.assertEqual(proj.status("src/main.c", "01.02"), "changed")
        self.assertEqual(proj.status("Makefile", "01.02"), "changed")       # no regions, but markers of 01.02
        self.assertIsNone(proj.status("Makefile", "01.03"))
        self.assertFalse(proj.whole("Makefile"))
        self.assertTrue(proj.whole("src/late.h"))
        self.assertIn("02.01", proj.lesson_ids())

    def test_unmarked_is_the_end_of_the_track(self):
        from harness import timeline
        out = timeline.unmarked(MAIN_C.split("\n"))
        joined = "\n".join(out)
        for gone in ("@from", "@else", "@internal"):
            self.assertNotIn(gone, joined)
        self.assertIn("// @build 01.01 base", out)                        # regions are not its business
        self.assertNotIn("wait();", joined)
        self.assertNotIn("selftest", joined)
        self.assertIn("  return net();", out)
        self.assertIn("  stuff();  // comment stays", out)

    def test_materialize_writes_what_the_site_shows(self):
        proj = self.project()
        dest = os.path.join(self.tmp, "at-0101")
        files = proj.materialize("01.01", dest)
        self.assertEqual(sorted(files), ["Makefile", "src/main.c", "tools/run.sh"])
        self.assertFalse(os.path.exists(os.path.join(dest, "src", "late.h")))
        lines, shown, _ = proj.lines_at("src/main.c", "01.01")
        self.assertEqual(open(os.path.join(dest, "src", "main.c")).read(), "\n".join(lines[i] for i in shown) + "\n")
        self.assertTrue(os.stat(os.path.join(dest, "tools", "run.sh")).st_mode & stat.S_IXUSR)
        whole = os.path.join(self.tmp, "at-0102")
        proj.materialize("01.02", whole)
        self.assertEqual(open(os.path.join(whole, "src", "late.h"), "rb").read(), b"int late;\n")

    def test_problems(self):
        from harness import timeline
        root = os.path.join(self.tmp, "bad")
        make(root)
        write(os.path.join(root, "src", "late.h"), "int late;\n// @from 01.01\nint early;\n// @end\nint x; // @from 09.09\n")
        write(os.path.join(root, "src", "net.c"), "// @from 02.01\nint open;\n")
        try:
            got = timeline.Project(self.core.Track("bad")).problems()
        finally:
            shutil.rmtree(root, ignore_errors=True)
        self.assertIn("src/late.h:2: @from 01.01, but the file only comes with 01.02", got)
        self.assertIn("src/late.h:5: @from 09.09: not a lesson of this track", got)
        self.assertIn("src/net.c:1: @from has no @end", got)
        self.assertEqual(len(got), 3, got)

    def test_scan_errors(self):
        from harness import core, timeline
        with self.assertRaises(core.Fail):
            timeline.scan_blocks("x.c", "// @else\n")
        with self.assertRaises(core.Fail):
            timeline.scan_blocks("x.c", "// @end\n")
        with self.assertRaises(core.Fail):
            timeline.scan_blocks("x.c", "// @internal\nint x;\n// @else\n// @end\n")
        blocks, marks = timeline.scan_blocks("x.ld", "/* @from 01.02 */\nA = .;\n/* @end */\nB = .; // x @from 01.01\n")
        self.assertEqual([(b.kind, b.lesson, b.start, b.end) for b in blocks], [("from", "01.02", 0, 2)])
        self.assertEqual(marks, {3: "01.01"})


FOLD_C = """#include "x.h"
#define TWICE(x) ((x) * 2)

struct pair {
  int a;
};

static int table[] = {
  1, 2,
};

int proto(int a,
          int b);

// The job of first.
int
first(int a,
      int b)
{
  if(a)
    goto out;
  return b;
out:
  return a;
}

int one_line(void) {
  return 1;
}

void empty(void)
{
}
"""


class FoldTests(unittest.TestCase):
    """"Functions only": every function body folds away, nothing else does."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="learn-timeline-fold-")
        from harness import core
        cls.core, cls.old = core, core.TRACKS_DIR
        core.TRACKS_DIR = cls.tmp
        make(os.path.join(cls.tmp, "tl"))
        cls.track = core.Track("tl")

    @classmethod
    def tearDownClass(cls):
        cls.core.TRACKS_DIR = cls.old
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_function_bodies(self):
        from harness import timeline
        lines = FOLD_C.split("\n")
        got = [(lines[h], lines[a], lines[b]) for h, a, b in timeline.functions(lines)]
        self.assertEqual(got[:2], [("first(int a,", "  if(a)", "  return a;"), ("int one_line(void) {", "  return 1;", "  return 1;")])
        self.assertEqual(lines[timeline.functions(lines)[2][0]], "void empty(void)")       # an empty body: nothing to fold
        self.assertEqual(len(timeline.function_bodies(lines)), 2)

    def code_step(self, lid):
        from harness.web.views import lesson_page
        lesson = next(l for l in self.track.lessons if l.id == lid)
        page = lesson_page(self.track, lesson)
        code = page[page.index('id="step-code"'):]
        return code[:code.index("</section>")]

    def test_every_function_folds_on_its_own(self):
        import re
        code = self.code_step("01.01")
        self.assertIn('data-fold-toggle aria-controls="code-fold" aria-pressed="false"', code)  # Functions only
        self.assertLess(code.index("data-fold-toggle"), code.index('class="region"'))     # at the top
        head = code[code.index('<div class="step-head">'):code.index('id="code-fold"')]
        self.assertIn('<span>The code</span></h2><button class="btn fold-toggle"', head)  # on the heading's line, outside the h2
        self.assertNotIn("fold-bar", code)                                              # no row of its own
        self.assertIn('id="code-fold"', code)
        folds = re.findall(r'<div class="fbody" id="([\w-]+)">', code)
        self.assertEqual(len(folds), 2)                                                 # base and tail; the Makefile has none
        for fid in folds:
            self.assertIn(f'<button class="fold-btn" type="button" aria-expanded="true" aria-controls="{fid}"', code)
            self.assertIn(f'<button class="fold-more" type="button" aria-controls="{fid}"', code)
        self.assertIn('aria-label="Fold base"', code)
        body = code[code.index(f'id="{folds[0]}"'):]
        body = body[:body.index("</div></div>", body.index("start"))]
        self.assertIn("start", body)                                                    # the body is inside its fold
        head = code[:code.index(f'id="{folds[0]}"')]
        self.assertIn('<span class="tk-f">base</span>', head)                             # the signature is outside it

    def test_the_file_viewer_folds_too(self):
        from harness.web.views import render_file_view
        got = render_file_view(self.track, "01.02", "src/main.c")
        self.assertTrue(got["foldable"])
        self.assertEqual(got["html"].count('class="fbody"'), 4)                         # base, helper, tail, more
        self.assertEqual(got["html"].count('class="fold-btn"'), 4)
        plain = render_file_view(self.track, "01.02", "Makefile")
        self.assertFalse(plain["foldable"])
        self.assertNotIn("fbody", plain["html"])


class CheckTimelineTests(unittest.TestCase):
    """./learn check-timeline: each lesson's project written out, built and booted."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="learn-timeline-check-")
        from harness import core
        self.core, self.old = core, core.TRACKS_DIR
        core.TRACKS_DIR = self.tmp
        make(os.path.join(self.tmp, "tl"))

    def tearDown(self):
        self.core.TRACKS_DIR = self.old
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_every_lesson_builds_and_boots(self):
        code, out = run_cli("check-timeline", "tl", "--seconds", "5", "-j", "2")
        self.assertEqual(code, 0, out)
        rows = [l.split() for l in out.splitlines() if l.startswith("   0")]
        self.assertEqual([r[0] for r in rows], ["01.01", "01.02", "01.03", "02.01", "03.01"])   # core, then each extension
        for r in rows:
            self.assertEqual((r[4], r[6]), ("ok", "ok"), r)
        self.assertIn("1 check ok", out)
        self.assertIn("2 checks ok (typed: ping)", out)
        self.assertIn("after: clean", out)
        self.assertIn("check-timeline: ok", out)

    def test_a_lesson_that_does_not_build_or_boot_fails(self):
        write(os.path.join(self.tmp, "tl", "src", "gui.c"), "// @build 03.01 draw\n// Draw.\nint draw; // BROKEN\n// @end\n")
        run = os.path.join(self.tmp, "tl", "tools", "run.sh")
        write(run, RUN_SH.replace("echo pong", "echo panic: no pong"))
        code, out = run_cli("check-timeline", "tl", "--seconds", "5")
        self.assertEqual(code, 1, out)
        rows = {l.split()[0]: l for l in out.splitlines() if l.startswith("   0")}
        self.assertIn("build FAIL", rows["03.01"])
        self.assertIn("boot FAIL", rows["01.02"])
        self.assertIn("boot ok", rows["01.01"])                              # 01.01 types nothing
        self.assertIn("problems in 01.02 01.03 02.01 03.01", out)

    def test_what_a_run_leaves_behind_is_checked_after_it(self):
        write(os.path.join(self.tmp, "tl", "tools", "after-fails"), "x\n")
        code, out = run_cli("check-timeline", "tl", "01.01", "--seconds", "5")
        self.assertEqual(code, 1, out)
        row = next(l for l in out.splitlines() if l.startswith("   01.01"))
        self.assertIn("boot FAIL", row)
        self.assertIn("after the run: left a mess", row)
        code, out = run_cli("check-timeline", "tl", "01.01", "--no-boot")    # nothing runs, nothing to check
        self.assertEqual(code, 0, out)

    def test_only_the_lessons_asked_for_and_no_boot(self):
        code, out = run_cli("check-timeline", "tl", "02", "--no-boot")
        self.assertEqual(code, 0, out)
        rows = [l.split() for l in out.splitlines() if l.startswith("   0")]
        self.assertEqual([(r[0], r[4], r[6]) for r in rows], [("02.01", "ok", "-")])

    def test_not_in_the_help(self):
        from harness import cli
        self.assertNotIn("check-timeline", cli.__doc__)
        code, out = run_cli("check-timeline")
        self.assertIn("usage", str(code))


# run_argv and bench for RunAtTests: each leaves what it was given in a file next to it, since
# the program writes to the terminal and not to the test's captured output.
RUN_HOOKS = '''

def run_argv(root, args=()):
    return ["sh", "-c", 'echo "$*" > ran.txt', "run"] + list(args)


def bench(root):
    return ["sh", "-c", 'echo "$*" > bench.txt', "bench"]
'''


class RunAtTests(unittest.TestCase):
    """./learn run / bench / files --at NN.LL: the project at a lesson, written to build/at/, built and run there."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="learn-run-at-")
        from harness import core
        from harness import workspace as ws
        self.core, self.ws = core, ws
        self.old = (core.TRACKS_DIR, ws.WORK_DIR, os.environ.get("LEARN_BUILD_DIR"))
        core.TRACKS_DIR = os.path.join(self.tmp, "tracks")
        ws.WORK_DIR = os.path.join(self.tmp, "work")
        self.build = os.path.join(self.tmp, "build")
        os.environ["LEARN_BUILD_DIR"] = self.build
        self.track = os.path.join(core.TRACKS_DIR, "tl")
        make(self.track)
        with open(os.path.join(self.track, "track.py"), "a") as f:
            f.write(RUN_HOOKS)

    def tearDown(self):
        self.core.TRACKS_DIR, self.ws.WORK_DIR, old_build = self.old
        if old_build is None:
            os.environ.pop("LEARN_BUILD_DIR", None)
        else:
            os.environ["LEARN_BUILD_DIR"] = old_build
        shutil.rmtree(self.tmp, ignore_errors=True)

    def at(self, *parts):
        return os.path.join(self.build, "at", "tl", *parts)

    def read(self, *parts):
        with open(self.at(*parts)) as f:
            return f.read()

    def test_runs_the_project_as_it_stands_at_the_lesson(self):
        code, out = run_cli("run", "tl", "--at", "01.02")
        self.assertEqual(code, 0, out)
        self.assertEqual(out.splitlines()[0], f"Running tl as it stands at 01.02 (More). Its files are in {self.at('01.02')}/")
        self.assertEqual(self.read("01.02", "ran.txt"), "\n")                      # ran there, with no args
        main = self.read("01.02", "src", "main.c")
        self.assertIn("more();", main)                                               # 01.02's code is in
        self.assertNotIn("net()", main)                                              # an extension's is not
        self.assertNotIn("@from", main)
        self.assertFalse(os.path.exists(self.at("01.02", "src", "net.c")))
        self.assertFalse(os.path.exists(os.path.join(self.track, "ran.txt")))       # nothing ran in tracks/
        code, out = run_cli("run", "tl", "--at=01.01")
        self.assertEqual(code, 0, out)
        self.assertNotIn("more();", self.read("01.01", "src", "main.c"))

    def test_an_extension_lesson_has_the_core_and_its_own_module_only(self):
        code, out = run_cli("run", "tl", "--at", "02.01")
        self.assertEqual(code, 0, out)
        self.assertTrue(os.path.exists(self.at("02.01", "src", "net.c")))
        self.assertFalse(os.path.exists(self.at("02.01", "src", "gui.c")))
        self.assertIn("return net();", self.read("02.01", "src", "main.c"))
        code, out = run_cli("run", "tl", "--at", "03.01")
        self.assertTrue(os.path.exists(self.at("03.01", "src", "gui.c")))
        self.assertFalse(os.path.exists(self.at("03.01", "src", "net.c")))

    def test_edits_stay_until_the_track_changes_or_fresh(self):
        run_cli("run", "tl", "--at", "01.02")
        mine = self.at("01.02", "src", "late.h")
        with open(mine, "w") as f:
            f.write("int mine;\n")
        code, out = run_cli("run", "tl", "--at", "01.02")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.read("01.02", "src", "late.h"), "int mine;\n")       # kept
        code, out = run_cli("run", "tl", "--at", "01.02", "--fresh")
        self.assertEqual(self.read("01.02", "src", "late.h"), "int late;\n")       # written again
        with open(mine, "w") as f:
            f.write("int mine;\n")
        write(os.path.join(self.track, "src", "late.h"), "int later_on;\n")         # the track's own code changes
        code, out = run_cli("run", "tl", "--at", "01.02")
        self.assertEqual(self.read("01.02", "src", "late.h"), "int later_on;\n")

    def test_args_after_the_double_dash_go_to_the_program(self):
        code, out = run_cli("run", "tl", "--at", "01.02", "--", "demo.db", "SELECT 1;", "--at")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.read("01.02", "ran.txt"), "demo.db SELECT 1; --at\n")
        code, out = run_cli("run", "tl", "--at", "01.02", "demo.db")              # a plain word needs no --
        self.assertEqual(self.read("01.02", "ran.txt"), "demo.db\n")
        code, out = run_cli("run", "tl", "--at", "01.02", "--bogus")
        self.assertIn("usage: learn run", str(code))
        with open(os.path.join(self.track, "track.py")) as f:
            hooks = f.read()
        write(os.path.join(self.track, "track.py"), hooks.replace("def run_argv(root, args=()):", "def run_argv(root):"))
        code, out = run_cli("run", "tl", "--at", "01.02", "--", "x")
        self.assertEqual(code, "./learn run tl takes no arguments for the program")

    def test_without_at_the_finished_track_runs_never_the_work_dir(self):
        os.makedirs(os.path.join(self.ws.WORK_DIR, "tl"))
        write(os.path.join(self.ws.WORK_DIR, "tl", ".learn.json"), '{"current": "01.02", "built": ["01.01"]}')
        for args in (("run", "tl"), ("run", "tl", "--ref")):                        # --ref: still accepted, and the same
            code, out = run_cli(*args)
            self.assertEqual(code, 0, out)
            self.assertEqual(out.splitlines()[0], f"Running the finished tl. Its files are in {self.at('finished')}/")
            self.assertTrue(os.path.exists(self.at("finished", "src", "net.c")))
            self.assertTrue(os.path.exists(self.at("finished", "src", "gui.c")))
            self.assertTrue(os.path.exists(self.at("finished", "ran.txt")))
        self.assertEqual(os.listdir(os.path.join(self.ws.WORK_DIR, "tl")), [".learn.json"])

    def test_a_lesson_with_no_code_or_a_wrong_one_says_so_in_a_line(self):
        write(os.path.join(self.track, "lessons", "00-intro", "README.md"), "---\nid: 00\ntitle: Intro\n---\n")
        write(os.path.join(self.track, "lessons", "00-intro", "00.01-x.md"), lesson_doc("00.01", "Hello"))
        code, out = run_cli("run", "tl", "--at", "00.01")
        self.assertEqual(code, "tl has no code yet at 00.01, so there is nothing to build or run; the code starts at 01.01")
        self.assertEqual(out, "")
        self.assertFalse(os.path.exists(self.at("00.01")))
        self.assertEqual(run_cli("run", "tl", "--at", "09.09")[0], "track tl has no lesson 09.09")
        self.assertEqual(run_cli("run", "tl", "--at", "1.2")[0], "--at takes a lesson number such as 02.03, not '1.2'")
        self.assertIn("usage: learn run", str(run_cli("run", "tl", "--at")[0]))
        code, out = run_cli("files", "tl", "--at", "00.01")                         # files writes it all the same
        self.assertEqual(code, 0, out)
        self.assertTrue(os.path.isdir(self.at("00.01")))

    def test_a_failed_build_stops_before_running(self):
        write(os.path.join(self.track, "src", "late.h"), "int late; // BROKEN\n")
        code, out = run_cli("run", "tl", "--at", "01.02")
        self.assertEqual(code, "build failed")
        self.assertFalse(os.path.exists(self.at("01.02", "ran.txt")))

    def test_bench_at_a_lesson_passes_its_args_on(self):
        code, out = run_cli("bench", "tl", "--at", "01.01", "--quick", "--rows", "10")
        self.assertEqual(code, 0, out)
        self.assertEqual(out.splitlines()[0], f"Benchmarking tl as it stands at 01.01 (Base). Its files are in {self.at('01.01')}/")
        self.assertEqual(self.read("01.01", "bench.txt"), "--quick --rows 10\n")
        code, out = run_cli("bench", "tl", "--ref", "--", "--json", "x")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.read("finished", "bench.txt"), "--json x\n")

    def test_files_writes_the_project_and_builds_nothing(self):
        dest = os.path.join(self.tmp, "mine")
        code, out = run_cli("files", "tl", "--at", "01.02", dest)
        self.assertEqual(code, 0, out)
        self.assertEqual(out.strip(), f"Wrote tl as it stands at 01.02 (More) to {dest}/")
        self.assertEqual(sorted(os.listdir(os.path.join(dest, "src"))), ["late.h", "main.c"])
        self.assertFalse(os.path.exists(os.path.join(dest, ".learn-at")))
        self.assertIn("is not empty", str(run_cli("files", "tl", "--at", "01.02", dest)[0]))
        for inside in (os.path.join(self.ws.WORK_DIR, "x"), os.path.join(self.track, "x")):
            self.assertIn("will not write into", str(run_cli("files", "tl", "--at", "01.02", inside)[0]))
            self.assertFalse(os.path.exists(inside))
        code, out = run_cli("files", "tl", "--at", "01.02")
        self.assertEqual(out.strip(), f"Wrote tl as it stands at 01.02 (More) to {self.at('01.02')}/")
        code, out = run_cli("files", "tl", "--at", "01.02")
        self.assertEqual(out.strip(), f"tl as it stands at 01.02 (More) is already in {self.at('01.02')}/")

    def test_the_help_says_at_and_no_longer_ref(self):
        from harness import cli
        lines = cli.__doc__.split("For authors")[0]
        part = lines[lines.index("./learn run"):]
        self.assertIn("./learn run <track> [--at NN.LL] [--fresh] [-- args...]", part)
        self.assertIn("./learn bench <track> [--at NN.LL] [--fresh] [args...]", part)
        self.assertIn("./learn files <track> [--at NN.LL] [dir]", part)
        self.assertIn("--fresh", part)
        for word in ("--ref", "workspace", "reference", "test", "stub", "exercise"):
            self.assertNotIn(word, part, word)


if __name__ == "__main__":
    unittest.main()
