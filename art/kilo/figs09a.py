"""Figures for kilo module 09, An API, and Lua on top of it: lessons 09.01 to 09.05 (an extension).

    python3 -B art/kilo/figs09a.py [name-prefix ...]
                                       writes tracks/kilo/lessons/09-api-and-lua/figures/09.0N-*.svg

09.06 to 09.10 are figs09b.py's; the maps, the cover and the icon are archmap.py's and covers.py's
(the cover from capture_cover() here).

Every script, screen, message, byte and number here is from a real run, or from NOTES.md where it
says so, checked against its words. The project at each lesson is written with ./learn files kilo
--at 09.0N, given Lua's source as the track's own tools give it (track.py's supply_lua), and built
with make. ./kilo runs on a pseudo-terminal through the track's fixture (edit() in
tracks/kilo/track.py), with KILO_INIT naming the init.lua shown, or with no screen (kilo -l, the
fixture run_script()) where only what the API says is needed. A trace that the code does not print
(Lua's stack, the dispatcher's steps, a reference's life) comes from a scratch copy of the
project with a few lines put in (a patch, below), which append to the file $KILO_TRACE.

  09.01-stack            stepped: the project at 09.01 with STACK_PATCH: Lua's stack after each
                         step of scriptEvalIn() and print, for the line 1+1 typed at Ctrl-E; the
                         message line it left ("2")
  09.01-protected-call   the project at 09.01 with NOTES.md's init.lua that has an error: the screen
                         and its message; and a copy with lua_call() for lua_pcall() in
                         scriptProtected(): what it wrote, how it ended, the terminal's modes after
  09.02-table            kilo --api-info at 09.02, and the table's entry for get_lines in kilo.c
  09.02-dispatch         stepped: the project at 09.02 with DISPATCH_PATCH, kilo -l running
                         get_lines(0, 2) on NOTES.md's f.txt: the stack, the checks, the ApiValues
  09.02-generator        NOTES.md's "The notable editors" (Neovim's generator and its three ways
                         in), and kilo's own two from the code
  09.03-set-lines        stepped: kilo -l at 09.03, four calls each on the same five rows
  09.03-cursor-rule      kilo -l at 09.03: three of NOTES.md's cursor cases, run again
  09.04-reference        stepped: the project at 09.04 with REF_PATCH, an init.lua mapping Ctrl-D
                         twice: the references luaL_ref() gave and freed, and the key's slot
  09.04-layers           SCRIPT_LUA from script.c, the table, and Neovim's names from NOTES.md
  09.05-save-events      the project at 09.05, an init.lua that trims trailing spaces before a save
                         and logs each event; Ctrl-S; the file on disk
  09.05-tick             the same project: keys typed, the changed tick before each (KeyPress) and
                         where TextChanged fired
  09.05-nesting          stepped: the same project, a TextChanged function that adds a line
"""
import contextlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, ROOT)
import figlib  # noqa: E402
from figlib import Fig, write, fmt  # noqa: E402
import steps  # noqa: E402
from harness import core  # noqa: E402

figlib.LESSONS = os.path.join(ROOT, "tracks", "kilo", "lessons")
MOD = "09-api-and-lua"
NOTES = os.path.join(ROOT, "tracks", "kilo", "NOTES.md")
TRACK = core.Track("kilo")
TK = TRACK.module                       # tracks/kilo/track.py: edit(), run_script(), supply_lua()
UP, DOWN, RIGHT, LEFT = "\x1b[A", "\x1b[B", "\x1b[C", "\x1b[D"
ENTER, ESC, BACKSPACE = "\r", "\x1b", "\x7f"


def ctrl(ch):
    return chr(ord(ch.upper()) & 0x1f)


def notes_09():
    with open(NOTES) as f:
        text = f.read()
    at = text.index("## 09 An API, and Lua on top of it")
    end = text.index("\n## ", at + 4)
    return text[at:end]


def notes_section(title):
    """The text of the section "### title" of NOTES.md's module 09 (to the next heading)."""
    text = notes_09()
    at = text.index("### " + title + "\n")
    end = re.search(r"\n#{2,3} ", text[at + 4:])
    return text[at:at + 4 + end.start()] if end else text[at:]


def flat(s):
    """s with its runs of white space made one space: NOTES.md's prose is wrapped."""
    return " ".join(s.split())


def in_notes(phrase, section=None):
    """Stop unless NOTES.md's module 09 (or one section of it) says phrase, wrapping aside."""
    text = flat(notes_section(section) if section else notes_09())
    if flat(phrase) not in text:
        raise SystemExit(f"figs09a: NOTES.md does not say {phrase!r}" + (f" in {section}" if section else ""))


def notes_block(section, after):
    """The indented block in a NOTES.md section that follows the line ending in `after`, dedented."""
    text = notes_section(section)
    at = text.index(after)
    lines = text[at:].split("\n")[2:]
    out = []
    for line in lines:
        if not line.startswith("    "):
            break
        out.append(line[4:])
    return out


# ------------------------------------------------------------------ running the project

_built = {}


def tracer(fmt_, *args):
    """A C statement that appends one line to the file $KILO_TRACE, if it is set."""
    a = "".join("," + x for x in args)
    return (' { FILE *tf_ = getenv("KILO_TRACE") ? fopen(getenv("KILO_TRACE"),"a") : NULL;'
            f' if (tf_) {{ fprintf(tf_,"{fmt_}\\n"{a}); fclose(tf_); }} }}')


def project(at, patch=None, name="script.c"):
    """The project at lesson `at`, written by ./learn files, given lua/ and built; with patch, a
    list of (old, new) made to a scratch copy of its file `name` first (each old once)."""
    key = (at, name, tuple(patch or ()))
    if key not in _built:
        d = os.path.join(tempfile.mkdtemp(prefix="kilo-figs09a-"), at)
        subprocess.run([os.path.join(ROOT, "learn"), "files", "kilo", "--at", at, d], check=True,
                       stdout=subprocess.DEVNULL)
        if patch:
            path = os.path.join(d, name)
            with open(path) as f:
                src = f.read()
            for old, new in patch:
                assert src.count(old) == 1, (at, old)
                src = src.replace(old, new)
            with open(path, "w") as f:
                f.write(src)
        TK.supply_lua(d)
        subprocess.run(["make", "-s"], cwd=d, check=True)
        _built[key] = d
    return _built[key]


@contextlib.contextmanager
def context(at, patch=None, name="script.c"):
    """A test context t on the project at `at` (t.root), its scratch directory t.tmp."""
    root = project(at, patch, name)
    t = core.TestContext(TRACK, TRACK.lessons[0], root=root)
    try:
        yield t
    finally:
        t.cleanup()


def run_l(at, lua, text=None, patch=None, trace=False):
    """kilo -l script.lua f.txt at lesson `at` (with patch): (returncode, stdout, stderr, trace
    lines, the file f.txt after)."""
    with context(at, patch) as t:
        env = dict(os.environ)
        tpath = os.path.join(t.tmp, "trace.txt")
        if trace:
            env["KILO_TRACE"] = tpath
        r = TK.run_script(t, lua, text, env=env)
        after = None
        if text is not None and os.path.exists(os.path.join(t.tmp, "f.txt")):
            with open(os.path.join(t.tmp, "f.txt"), encoding="latin-1", newline="") as f:
                after = f.read()
        return r.returncode, r.stdout, r.stderr, trace_lines(tpath), after


def trace_lines(path):
    try:
        with open(path) as f:
            return f.read().split("\n")[:-1]
    except OSError:
        return []


class Shot:
    """What a screen showed: its lines, the cursor."""

    def __init__(self, ed):
        self.lines = list(ed.lines)
        self.cursor = ed.cursor


# ------------------------------------------------------------------ the cover's capture

CTRL_D_INIT = notes_block("09.04 Any key can run a Lua function", "The lesson's two, in init.lua:")


def capture_cover():
    """For covers.py: the project at 09.04 with NOTES.md's init.lua (its Ctrl-D and Ctrl-T), on
    "local x = 1 / print(x)" on a terminal 8 x 30; Ctrl-D. The init.lua's lines, the screen
    before and after, and the API's names (kilo --api-info at 09.09)."""
    init = "\n".join(CTRL_D_INIT) + "\n"
    assert CTRL_D_INIT[0] == "kilo.keymap.set('<C-d>', function()" and CTRL_D_INIT[4] == "end)", CTRL_D_INIT
    in_notes('On "local x = 1 / print(x)": Ctrl-D gives `local x = 1` twice (the cursor stays on row 1)',
             "09.04 Any key can run a Lua function")
    with context("09.04") as t:
        ed = TK.edit(t, "local x = 1\nprint(x)\n", rows=8, cols=30, init=init)
        before = Shot(ed)
        ed.keys(ctrl("d"))
        after = Shot(ed)
    assert after.lines[:3] == ["local x = 1", "local x = 1", "print(x)"], after.lines
    assert before.cursor == after.cursor == (0, 0), (before.cursor, after.cursor)
    info = subprocess.run([os.path.join(project("09.09"), "kilo"), "--api-info"], capture_output=True,
                          text=True, check=True).stdout.split("\n")[:-1]
    in_notes(f"{len(info)} C functions in a table")
    names = [line[:line.index("(")] for line in info]
    return {"init": CTRL_D_INIT[:5], "before": before, "after": after, "names": names}


# ------------------------------------------------------------------ drawing

class F9(Fig):
    def bar(self, x, y, w, h, cls, rx=0):
        """A filled shape with no stroke."""
        self.add(f'<rect class="{cls}" x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}" rx="{fmt(rx)}"/>')


def cwid(size):
    return size * 0.6


def mono(f, x, y, s, cls="t", size=11, weight=None):
    """s in monospace from x, each run of non-spaces at its own column (SVG collapses runs of
    spaces). Returns the x just past it."""
    cw = cwid(size)
    col = 0
    for word in s.split(" "):
        if word:
            f.text(x + col * cw, y, word, cls, size, weight=weight, mono=True)
        col += len(word) + 1
    return x + len(s) * cw


def wrap(s, width):
    out, line = [], ""
    for w in s.split():
        if line and len(line) + 1 + len(w) > width:
            out.append(line)
            line = w
        else:
            line = (line + " " + w).strip()
    if line:
        out.append(line)
    return out


def notes(f, x, y, s, width, cls="tm", size=10.5, lh=14):
    lines = wrap(s, width)
    for k, line in enumerate(lines):
        f.text(x, y + k * lh, line, cls, size)
    return y + len(lines) * lh


def screen(f, x, y, shot, cw, rh, cols, rows=None, cursor=True, status=True):
    """A terminal screen from a Shot, in a rounded frame: the rows given (all by default); the
    status bar (the last row but one) in reverse video; the cursor as an outlined cell.
    Returns {row: baseline}."""
    rows = list(range(len(shot.lines))) if rows is None else list(rows)
    n = len(shot.lines)
    size = cw / 0.6
    f.rect(x - 7, y - 4, cols * cw + 14, len(rows) * rh + 8, "s fs", 6)
    base = {}
    for k, r in enumerate(rows):
        b = y + k * rh + rh * 0.72
        base[r] = b
        line = shot.lines[r]
        if status and r == n - 2:
            f.bar(x - 1, y + k * rh + 1, cols * cw + 2, rh - 2, "t", 1.5)
            mono(f, x, b, line, "f", size)
        else:
            mono(f, x, b, line, "t", size)
    if cursor and shot.cursor[0] in base:
        r, c = shot.cursor
        f.rect(x + c * cw - 0.5, base[r] - rh * 0.72 + 1.5, cw + 1, rh - 3, "a", 1)
    return base


FIGS = []


def cleanup():
    """Remove the projects built for the captures."""
    for d in {os.path.dirname(p) for p in _built.values()}:
        shutil.rmtree(d, ignore_errors=True)
    _built.clear()


def main():
    only = sys.argv[1:]
    try:
        for name, fn, stepped in FIGS:
            if only and not any(name.startswith(o) for o in only):
                continue
            fig = fn()
            text = fig.svg()
            if stepped:
                print(name, "steps:", steps.check(text))
            print(write(MOD, name, fig))
    finally:
        cleanup()


if __name__ == "__main__":
    main()
