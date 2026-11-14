"""./learn verify (harness/verify.py): the annotations, the static checks, and replays of lessons
on a tiny track whose system is a shell script, so nothing needs a compiler.

The sample track, vt: a calculator REPL that prints "calc> ". 01.01 teaches `add`, 01.02 `mul`.
Each test writes the lessons it needs.
"""

import contextlib
import io
import os
import shutil
import tempfile
import unittest

from harness.tests.test_web import write

TRACK = '''
TITLE = "Vt"
KIND = "demo"
SUMMARY = "A calculator."
SOURCES = ["src/*.sh"]
STUBS = {".sh": 'echo "{id}: {title} not written yet"'}
FILES_FROM = {}
VERIFY_PROMPTS = ["calc> "]
VERIFY_QUIT = ["\\x04"]
VERIFY_QUIET = 0.1
VERIFY_SETTLE = 0.5
TOOLS = {}


def prepare(root):
    # "builds" unless a source file says BROKEN
    return ["sh", "-c", "if grep -rq BROKEN src; then echo 'src/calc.sh: error: BROKEN'; exit 1; fi"]


def run_argv(root, args=()):
    return ["sh", "src/calc.sh"] + list(args)


def verify_tools():
    return dict(TOOLS)
'''

CALC = """# The calculator: a command and two numbers per line.
echo "calc: ready"
while printf 'calc> ' && read -r cmd a b; do
  case "$cmd" in
  # @build 01.01 add
  # Add two numbers.
  add) echo $((a + b)) ;;
  # @end
  # @build 01.02 mul
  # Multiply two numbers.
  mul) echo $((a * b)) ;;
  # @end
  hang) while :; do sleep 1; done ;;
  wait4) echo "waiting"; read -r x; echo "you typed $x" ;;
  *) echo "unknown: $cmd" ;;
  esac
done
"""


def lesson(lid, title, run, how="", brk=""):
    """A lesson with every section, its Run it and Break it as given."""
    return f"""---
id: {lid}
title: {title}
labels: with code
---

# {lid} {title}

The calculator learns {title.lower()}.

## Where this fits

It is the whole system.

## The idea

One case per command.

## Run it

{run}

## How it works

{how or "Nothing more."}

## Break it

{brk or "Nothing to break."}

## Go deeper

Nothing.
"""


RUN_0101 = """<!-- verify: session -->
```
$ ./learn run vt --at 01.01
Running vt as it stands at 01.01 (Add). Its files are in build/at/vt/01.01/
calc: ready
calc> add 2 3
5
calc> mul 2 3
unknown: mul
```"""

GOOD_0101 = lesson("01.01", "Add", RUN_0101, how="""The case:

```
  add) echo $((a + b)) ;;
```""", brk="""Make `add` subtract: in build/at/vt/01.01/src/calc.sh change the case to
`add) echo $((a - b)) ;;` and run it again.

<!-- verify: patch file=src/calc.sh
-  add) echo $((a + b)) ;;
+  add) echo $((a - b)) ;;
-->
<!-- verify: session run="./learn run vt --at 01.01" -->
```
calc> add 2 3
-1
```""")


class VerifyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="learn-verify-test-")
        self.root = os.path.join(self.tmp, "tracks", "vt")
        write(os.path.join(self.root, "track.py"), TRACK)
        write(os.path.join(self.root, "src", "calc.sh"), CALC)
        write(os.path.join(self.root, "lessons", "01-calc", "README.md"), "---\nid: 01\ntitle: Calc\n---\n")
        self.lesson("01.02", "Mul", lesson("01.02", "Mul", "Nothing to run."))
        from harness import core, verify
        self.core, self.verify = core, verify
        self.saved = (core.TRACKS_DIR, os.environ.get("LEARN_VERIFY_DIR"))
        core.TRACKS_DIR = os.path.join(self.tmp, "tracks")
        os.environ["LEARN_VERIFY_DIR"] = os.path.join(self.tmp, "build")

    def tearDown(self):
        self.core.TRACKS_DIR = self.saved[0]
        if self.saved[1] is None:
            os.environ.pop("LEARN_VERIFY_DIR", None)
        else:
            os.environ["LEARN_VERIFY_DIR"] = self.saved[1]
        shutil.rmtree(self.tmp, ignore_errors=True)

    def lesson(self, lid, title, text):
        write(os.path.join(self.root, "lessons", "01-calc", f"{lid}-{title.lower()}.md"), text)

    def run_verify(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            try:
                code = self.verify.main(["vt"] + list(args))
            except SystemExit as e:
                code = e.code
        return code, out.getvalue()

    # ---- whole lessons

    def test_a_true_lesson_passes_and_is_cached(self):
        self.lesson("01.01", "Add", GOOD_0101)
        code, out = self.run_verify("01.01")
        self.assertEqual(code, 0, out)
        self.assertIn("01.01  Add", out)
        self.assertIn(" ok ", out)
        self.assertIn("2 sessions, 1 quoted, 1 patches", out)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "build", "verify", "run", "vt", "01.01")))
        code, out = self.run_verify("01.01")
        self.assertEqual(code, 0, out)
        self.assertIn("cached", out)
        code, out = self.run_verify("01.01", "--fresh")
        self.assertNotIn("cached", out)
        self.assertFalse(os.path.exists(os.path.join(self.root, "build")))       # nothing written in tracks/

    def test_output_from_a_later_lesson_fails_where_the_lesson_says_it(self):
        text = GOOD_0101.replace("calc> mul 2 3\nunknown: mul", "calc> mul 2 3\n6")
        self.lesson("01.01", "Add", text)
        code, out = self.run_verify("01.01")
        self.assertEqual(code, 1, out)
        line = text.split("\n").index("6") + 1
        self.assertIn(f"01.01-add.md:{line}: session at 01.01: the lesson shows    '6'", out)
        self.assertIn("the project printed 'unknown: mul'", out)
        self.assertIn("problems in vt/01.01", out)
        kept = os.path.join(self.tmp, "build", "verify", "run", "vt", "01.01", "transcripts.txt")
        with open(kept) as f:
            self.assertIn("unknown: mul", f.read())

    def test_a_quote_that_only_exists_later(self):
        text = GOOD_0101.replace("  add) echo $((a + b)) ;;\n```", "  mul) echo $((a * b)) ;;\n```")
        self.lesson("01.01", "Add", text)
        code, out = self.run_verify("01.01", "--static")
        self.assertEqual(code, 1, out)
        self.assertIn("quoted code not in the project at 01.01; it comes with 01.02: 'mul) echo $((a * b)) ;;'", out)

    def test_a_patch_that_does_not_apply(self):
        text = GOOD_0101.replace("-  add) echo $((a + b)) ;;", "-  sub) echo $((a - b)) ;;")
        self.lesson("01.01", "Add", text)
        code, out = self.run_verify("01.01", "--static")
        self.assertEqual(code, 1, out)
        self.assertIn("patch src/calc.sh at 01.01: the lines to change are not in the file "
                      "(looking for 'sub) echo $((a - b)) ;;')", out)

    def test_a_patch_may_only_add_what_the_page_shows(self):
        text = GOOD_0101.replace("+  add) echo $((a - b)) ;;", "+  add) echo $((a - b - 1)) ;;")
        self.lesson("01.01", "Add", text)
        code, out = self.run_verify("01.01", "--static")
        self.assertIn("patch adds 'add) echo $((a - b - 1)) ;;', which the page never shows the reader", out)

    def test_hangs(self):
        hangs = lesson("01.01", "Add", """<!-- verify: session run="./learn run vt --at 01.01" hangs=1 -->
```
calc> hang
```""")
        self.lesson("01.01", "Add", hangs)
        code, out = self.run_verify("01.01")
        self.assertEqual(code, 0, out)
        self.lesson("01.01", "Add", hangs.replace("calc> hang", "calc> add 1 1\n2"))
        code, out = self.run_verify("01.01")
        self.assertEqual(code, 1, out)
        self.assertIn("the lesson says it hangs here, but a prompt came back", out)

    def test_panics(self):
        self.lesson("01.01", "Add", lesson("01.01", "Add", """<!-- verify: patch file=src/calc.sh
   echo "calc: ready"
+echo "panic: no numbers today"; exit 3
-->
<!-- verify: session panics="no numbers" exit=3 -->
```
$ ./learn run vt --at 01.01
Running vt as it stands at 01.01 (Add). Its files are in build/at/vt/01.01/
calc: ready
panic: no numbers today
```""", brk='Add `echo "panic: no numbers today"; exit 3` after the first echo.'))
        code, out = self.run_verify("01.01")
        self.assertEqual(code, 0, out)

    def test_build_fails_and_exit_status(self):
        self.lesson("01.01", "Add", lesson("01.01", "Add", """<!-- verify: patch file=src/calc.sh
   echo "calc: ready"
+BROKEN
-->
<!-- verify: session build-fails="error: BROKEN" exit=1 -->
```
$ ./learn run vt --at 01.01
Running vt as it stands at 01.01 (Add). Its files are in build/at/vt/01.01/
src/calc.sh: error: BROKEN
build failed
```""", brk="Type `BROKEN` into it."))
        code, out = self.run_verify("01.01")
        self.assertEqual(code, 0, out)

    def test_facts_and_the_sentence_they_check(self):
        good = lesson("01.01", "Add", """<!-- verify: fact cmd='sh src/calc.sh < /dev/null | head -1 | wc -c' expect=12 -->
The first line is 12 bytes long.""")
        self.lesson("01.01", "Add", good)
        code, out = self.run_verify("01.01")
        self.assertEqual(code, 0, out)
        self.lesson("01.01", "Add", good.replace("expect=12", "expect=13").replace("12 bytes", "13 bytes"))
        code, out = self.run_verify("01.01")
        self.assertIn("fact: the lesson says '13'; `sh src/calc.sh < /dev/null | head -1 | wc -c` in the project "
                      "at 01.01 printed '12'", out)
        self.lesson("01.01", "Add", good.replace("12 bytes", "twelve bytes"))
        code, out = self.run_verify("01.01", "--static")
        self.assertIn("fact: the text after it does not say '12'", out)

    def test_the_computer_s_own_shell(self):
        """The reader's terminal: ./learn files, cd into the copy, variables, pipes; cwd=project."""
        self.lesson("01.01", "Add", lesson("01.01", "Add", """<!-- verify: session -->
```
$ ./learn files vt --at 01.01
Wrote vt as it stands at 01.01 (Add) to build/at/vt/01.01/
$ cd build/at/vt/01.01
$ N=7
$ echo "add $N 1" | sh src/calc.sh
calc: ready
calc> 8
calc> $ ls
src
```

<!-- verify: session cwd=project exit=0 -->
```
$ printf 'mul 2 3\\n' | sh src/calc.sh | head -2 | tail -1
calc> unknown: mul
```"""))
        code, out = self.run_verify("01.01")
        self.assertEqual(code, 0, out)

    def test_keys_typed_lines_and_continuations(self):
        """Keys pressed as a line starts, a line typed where no prompt shows, a command over two
        lines, time in one line, a line typed that the block leaves out (type=), a second
        terminal, and the shell's prompt after the program it ran has gone."""
        self.lesson("01.01", "Add", lesson("01.01", "Add", r"""<!-- verify: session run="./learn run vt --at 01.01"
line 2 keys garbage ctrl-u
line 6 typed
-->
```
calc: ready
calc> add 2 3
5
calc> wait4
waiting
hello
you typed hello
```

<!-- verify: session terminal=2
line 6 ~   \d+\.\d\ds user \d+\.\d\ds system [\d.]+% cpu \d+\.\d+ total
-->
```
$ echo "one
two"
one
two
$ time (true)
  0.00s user 0.00s system 0% cpu 0.001 total
```

<!-- verify: session type="add 4 5" -->
```
9
```

<!-- verify: session -->
```
calc> add 1 1
2
```

<!-- verify: session -->
```
$ echo back at the prompt
back at the prompt
```
""", brk="Nothing."))
        code, out = self.run_verify("01.01")
        self.assertEqual(code, 0, out)

    def test_setup_file_and_a_change_inside_a_line(self):
        self.lesson("01.01", "Add", GOOD_0101)
        self.lesson("01.02", "Mul", lesson("01.02", "Mul", """Set up as 01.01's Break it did, and make a note:

<!-- verify: setup at=01.02 cwd=project
$ echo noted > note.txt
-->
<!-- verify: session cwd=project -->
```
$ cat note.txt
noted
```

The file holds the case:

<!-- verify: file path=src/calc.sh -->
```
  mul) echo $((a * b)) ;;
  hang) while :; do sleep 1; done ;;
```""", brk="""Change `$((a * b))` to `$((a * b + 1))`:

<!-- verify: patch file=src/calc.sh old="$((a * b))" new="$((a * b + 1))" -->
<!-- verify: setup
replay 01.01 "$ ./learn run vt --at 01.01"
-->
<!-- verify: session run="./learn run vt --at 01.02" -->
```
calc> mul 2 3
7
```"""))
        code, out = self.run_verify("01.02")
        self.assertEqual(code, 0, out)
        with open(os.path.join(self.root, "lessons", "01-calc", "01.02-mul.md")) as f:
            text = f.read()
        self.lesson("01.02", "Mul", text.replace("mul) echo $((a * b)) ;;\n  hang)", "mul) echo $((a * b)) ;;\n  wait4)"))
        code, out = self.run_verify("01.02")
        self.assertEqual(code, 1, out)
        self.assertIn("file src/calc.sh at 01.02: the lesson shows    '  wait4) while :; do sleep 1; done ;;'", out)
        self.lesson("01.02", "Mul", text.replace('new="$((a * b + 1))"', 'new="$((a * b + 2))"'))
        code, out = self.run_verify("01.02", "--static")
        self.assertIn("patch changes to '$((a * b + 2))', which the page never shows the reader", out)

    def test_missing_tools(self):
        write(os.path.join(self.root, "track.py"), TRACK.replace("TOOLS = {}", 'TOOLS = {"frobnicator": None}'))
        self.lesson("01.01", "Add", GOOD_0101)
        code, out = self.run_verify("01.01")
        self.assertEqual(code, 1, out)
        self.assertIn("cannot verify: missing frobnicator", out)
        code, out = self.run_verify("01.01", "--allow-missing")
        self.assertEqual(code, 0, out)

    def test_pending_lessons_are_skipped_unless_named(self):
        self.lesson("01.01", "Add", GOOD_0101.replace("calc> mul 2 3\nunknown: mul", "calc> mul 2 3\n6"))
        write(os.path.join(self.root, "lessons", "verify-pending.txt"), "# not yet\n01.01\n01.02\n")
        code, out = self.run_verify()
        self.assertEqual(code, 0, out)
        self.assertIn("no lessons to check (2 pending)", out)
        code, out = self.run_verify("01.01")
        self.assertEqual(code, 1, out)
        problems, notes = self.verify.static_problems()
        self.assertEqual(problems, [])
        self.assertIn("vt has 2 lessons not annotated yet", notes[0])

    # ---- the static checks one by one

    def problems(self, text, lid="01.01", title="Add"):
        self.lesson(lid, title, text)
        track = self.core.Track("vt")
        l = next(x for x in track.lessons if x.id == lid)
        return [str(p) for p in self.verify.Verifier().static(track, l) if not p.warning]

    def test_an_unannotated_transcript_or_prose_block_is_an_error(self):
        got = self.problems(lesson("01.01", "Add", "```\ncalc> add 1 2\n3\n```\n\n```\nsome notes\n```"))
        self.assertTrue(any("looks like a terminal transcript" in p for p in got), got)
        self.assertTrue(any("none of this block is code from the project" in p for p in got), got)
        got = self.problems(lesson("01.01", "Add", '<!-- verify: skip reason="a picture" -->\n```\nsome notes\n```'))
        self.assertEqual(got, [])
        got = self.problems(lesson("01.01", "Add", "<!-- verify: skip -->\n```\nsome notes\n```"))
        self.assertTrue(any("skip needs reason=" in p for p in got), got)

    def test_mentions(self):
        ok = "`calc.sh` and `src/calc.sh`, and `mul()`, which comes in 01.02."
        self.assertEqual(self.problems(lesson("01.01", "Add", ok)), [])
        got = self.problems(lesson("01.01", "Add", "Then `mul()` multiplies. And `nope.c` is a file."))
        self.assertTrue(any("`mul()` is not in the project at 01.01; it comes with 01.02" in p for p in got), got)
        self.assertTrue(any("`nope.c` is not in the project at 01.01; not in any lesson's project" in p for p in got), got)
        declared = ('<!-- verify: mention names="nope.c" outside reason="another program" -->\n'
                    '<!-- verify: mention names="mul()" at=01.02 -->\n'
                    "Then `mul()` multiplies. And `nope.c` is a file.")
        self.assertEqual(self.problems(lesson("01.01", "Add", declared)), [])
        got = self.problems(lesson("01.01", "Add", "Open `build/at/vt/01.01/src/gone.sh`."))
        self.assertTrue(any("there is no src/gone.sh in the project at 01.01" in p for p in got), got)

    def test_arrow_notes_on_quoted_code(self):
        quote = "```\n  add) echo $((a + b)) ;;     <- this line\n```"
        self.assertEqual(self.problems(lesson("01.01", "Add", quote)), [])
        got = self.problems(lesson("01.01", "Add", quote.replace("a + b", "a + c")))
        self.assertTrue(any("quoted code not in the project at 01.01" in p for p in got), got)

    def test_words_commands_and_sections(self):
        got = self.problems(lesson("01.01", "Add", "Run `./learn test vt` until the stub passes, "
                                                   "then `./learn run vt --at 09.09`."))
        self.assertTrue(any("`./learn test` is not a command learners use" in p for p in got), got)
        self.assertTrue(any("talks about stubs" in p for p in got), got)
        self.assertTrue(any("vt has no lesson 09.09" in p for p in got), got)
        got = self.problems(lesson("01.01", "Add", "x").replace("## Break it", "## Breaking"))
        self.assertTrue(any("sections should be Where this fits" in p for p in got), got)
        got = self.problems(lesson("01.01", "Add", "A DNS stub resolver is fine, as is a test card."))
        self.assertEqual(got, [])

    def test_annotation_errors(self):
        got = self.problems(lesson("01.01", "Add", "<!-- verify: sesion -->\n```\nx\n```"))
        self.assertTrue(any("unknown annotation `sesion`" in p for p in got), got)
        got = self.problems(lesson("01.01", "Add", "<!-- verify: session colour=red -->\n```\ncalc> x\n```"))
        self.assertTrue(any("`session` does not take colour" in p for p in got), got)
        got = self.problems(lesson("01.01", "Add", "<!-- verify: session -->\nsome text\n\n```\ncalc> x\n```"))
        self.assertTrue(any("must come directly before the fenced block" in p for p in got), got)
        got = self.problems(lesson("01.01", "Add", "<!-- verify: session\nlines 2-9 mixed\n-->\n```\ncalc> x\n```"))
        self.assertTrue(any("lines 2-9: the block has 1 lines" in p for p in got), got)
        got = self.problems(lesson("01.01", "Add", "<!-- an unclosed comment\n\nmore"))
        self.assertTrue(any("never closes" in p for p in got), got)


class MatchTests(unittest.TestCase):
    """The transcript comparison: exact by default, with the allowances an annotation names."""

    def items(self, block, rules=""):
        from harness import verify
        b = verify.Block(10, 10 + len(block) + 1, block, 0)
        note = verify.Note(9, "session", {}, set(), [(5, r) for r in rules.split("\n") if r])
        return verify.session_items(note, b)

    def ok(self, block, actual, rules="", more=False, before=False):
        from harness import verify
        return verify.match(self.items(block, rules), actual, more=more, before=before).ok

    def test_exact_elide_and_more(self):
        self.assertTrue(self.ok(["a", "b"], ["a", "b"]))
        self.assertFalse(self.ok(["a", "b"], ["a", "c"]))
        self.assertFalse(self.ok(["a"], ["a", "b"]))
        self.assertTrue(self.ok(["a"], ["a", "b"], more=True))
        self.assertTrue(self.ok(["a", "...", "z"], ["a", "b", "c", "z"]))
        self.assertTrue(self.ok(["a", "...", "z"], ["a", "z"]))
        self.assertTrue(self.ok(["a  "], ["a"]))                  # trailing spaces do not count

    def test_allowances(self):
        self.assertTrue(self.ok(["x", "hart 1", "hart 2"], ["x", "hart 2", "hart 1"], "lines 2-3 unordered"))
        self.assertFalse(self.ok(["x", "hart 1", "hart 2"], ["x", "hart 2", "hart 1"]))
        self.assertTrue(self.ok(["hart hart 12 starting", " starting"], ["hart 1 starting", "hart 2 starting"],
                                "lines 1-2 mixed"))
        self.assertFalse(self.ok(["hart 1 starting", "hart 2 starting"], ["hart 1 starting", "hart 3 starting"],
                                 "lines 1-2 mixed"))
        self.assertTrue(self.ok(["main at 0x8000007a"], ["main at 0x80000100"], "vary 0x8000007a addr"))
        self.assertFalse(self.ok(["main at 0x8000007a"], ["main at 80000100"], "vary 0x8000007a addr"))
        self.assertTrue(self.ok(["took 1.5 ms"], ["took 12 ms"], "line 1 ~ took \\d+(\\.\\d+)? ms"))
        self.assertTrue(self.ok(["3 runs in 41 ms"], ["3 runs in 39 ms"], 'vary "41 ms" /\\d+ ms/'))

    def test_optional_anywhere_ignore_and_before(self):
        self.assertTrue(self.ok(["a", "b", "c"], ["a", "c"], "line 2 optional"))
        self.assertTrue(self.ok(["a", "b", "c"], ["a", "b", "c"], "line 2 optional"))
        self.assertFalse(self.ok(["a", "c"], ["a", "x", "c"], "line 2 optional"))
        self.assertTrue(self.ok(["a", "[1] 123", "c"], ["[1] 999", "a", "c"], "line 2 anywhere\nvary 123 int"))
        self.assertTrue(self.ok(["a", "c"], ["a", "Killed: 9", "c"], "ignore job-reports"))
        self.assertTrue(self.ok(["a", "c"], ["a", "zsh: killed     ./db t.db", "c"], "ignore job-reports"))
        self.assertTrue(self.ok(["a", "c"], ["reading from file x", "a", "c"], "ignore /reading from file .*/"))
        self.assertFalse(self.ok(["a", "c"], ["Killed", "a", "c"], "ignore /reading .*/"))
        self.assertTrue(self.ok(["y", "z"], ["w", "x", "y", "z"], before=True))
        self.assertFalse(self.ok(["y", "z"], ["w", "x", "y", "z"]))
        self.assertTrue(self.ok(["AAA"], ["AA", "A"], "line 1 mixed"))          # any number of lines
        self.assertTrue(self.ok(["AAA"], ["A", "A", "A"], "line 1 mixed"))
        self.assertTrue(self.ok([" pc  0000", "x"], [" pc  0000", "x"], "line 1 ~  pc  \\d+"))  # a regex may start with a space

    def test_trimmed_picks_lines_in_order(self):
        from harness import verify
        b = verify.Block(10, 14, ["CPU#1", " pc 80", " sp ff"], 0)
        exp = verify.session_items(verify.Note(9, "session", {}, {"trimmed"}, []), b)
        self.assertTrue(verify.match(exp, ["x", "CPU#1", "y", " pc 80", "z", " sp ff", "w"]).ok)
        self.assertFalse(verify.match(exp, ["CPU#1", " sp ff", " pc 80"]).ok)

    def test_screen_lines(self):
        from harness.verify import screen_lines
        self.assertEqual(screen_lines("a\r\nb\r\n$ "), ["a", "b", "$ "])
        self.assertEqual(screen_lines("(qemu) i\x1b[K\x1b[Din\x1b[K\r\r\nx"), ["(qemu) in", "x"])
        self.assertEqual(screen_lines("abc\b\bX\n"), ["aXc", ""])
        self.assertEqual(screen_lines("\x1b]7779;rc=0\x07$ ls\r\n"), ["$ ls", ""])

    def test_patches(self):
        from harness.verify import AnnotationError, apply_patch
        text = "a\n  b\nc\n  b\n"
        self.assertEqual(apply_patch(text, [(" ", "a"), ("-", "b"), ("+", "  B")]), "a\n  B\nc\n  b\n")
        with self.assertRaises(AnnotationError) as e:
            apply_patch(text, [("-", "b")])
        self.assertIn("2 times", str(e.exception))
        self.assertEqual(apply_patch(text, [("@", ["x();"])], append=True), "a\n  b\nc\n  b\nx();\n")
        self.assertEqual(apply_patch(text, [(" ", "c"), ("@", ["y"])]), "a\n  b\nc\ny\n  b\n")
        self.assertEqual(apply_patch(None, [("+", "new")]), "new\n")
        from harness.verify import apply_edit, added_lines
        self.assertEqual(apply_edit("if (c < 0)\n", "< 0", "<= 0"), "if (c <= 0)\n")
        with self.assertRaises(AnnotationError):
            apply_edit("a - 1, b - 1", "- 1", "")
        self.assertEqual(added_lines([("-", "  w_pmpcfg0(0xf);"), ("+", "  // w_pmpcfg0(0xf);")]),
                         [("  // w_pmpcfg0(0xf);", "  w_pmpcfg0(0xf);")])

    def test_options_and_keys(self):
        from harness.verify import parse_keys, parse_options
        self.assertEqual(parse_options('cmd="grep \\d+ \\"x\\"" f'), ({"cmd": 'grep \\d+ "x"'}, {"f"}))
        self.assertEqual(parse_keys("ctrl-a c"), "\x01c")
        self.assertEqual(parse_keys("echo one ctrl-h ctrl-h two enter"), "echo one\x08\x08two\r")
        self.assertEqual(parse_keys('"info mem" enter'), "info mem\r")


if __name__ == "__main__":
    unittest.main()
