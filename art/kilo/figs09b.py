"""Figures for kilo module 09, An API, and Lua on top of it (lessons 09.06 to 09.10), an extension.

    python3 -B art/kilo/figs09b.py [name-prefix ...]
                                       writes tracks/kilo/lessons/09-api-and-lua/figures/09.LL-*.svg

(09.01 to 09.05, the maps, the cover and the icon are figs09a.py's, archmap.py's and covers.py's.)

Every script, screen, byte and message here is from a real run, or from NOTES.md where a figure
shows what another editor does or a number measured once; each is checked against the words of
NOTES.md or of the lesson here. The project at each lesson is written with ./learn files kilo --at
09.LL, given Lua (track.py's supply_lua) and built with make; ./kilo runs on a pseudo-terminal
through the track's own fixture (edit() in tracks/kilo/track.py). Where a lesson has an example (its
files, init.lua, keys and terminal size, read from the lesson's Run it here), the figure runs that.
No figure's text names NOTES.md, a test, or how the figure was made.

  09.06-drawn-over      09.06 on the lesson's sizes.txt and init.lua, 8 x 72: the bytes written for
                        the third row (the tab, 307200 in yellow), bytes to cells
  09.06-namespaces      the same: the first three rows; clear_namespace of 'spaces' at the prompt;
                        then Down
  09.06-moves-or-not    the same, with the lesson's green highlight added at the prompt, then Enter
                        at the top; Neovim's side from NOTES.md (extmark.c, marktree.c), not run
  09.07-nested-loop     09.07 on the lesson's add.c and init.lua, 12 x 60, in a copy whose
                        editorPrompt() writes its backtrace (execinfo): Ctrl-O, 8
  09.07-quit-mark       stepped: the lesson's Ctrl-X (save, and leave), in a copy that writes a line
                        at the mark, at each return from Lua, before exit() and in scriptStop(), to
                        check the order the frames show; each frame shows the line of kilo's code
  09.08-hook            09.08 on the lesson's notes.txt and init.lua, 8 x 60: unsaved, Ctrl-T, abc,
                        Ctrl-C, then Ctrl-S
  09.08-allocator       the lesson's lines at the prompt at 09.08, and the 200 MB line at 09.07
  09.08-trust           Neovim, VS Code, Zed: NOTES.md's confirmed facts only, not run
  09.09-two-doors       09.09: the editor on the lesson's notes.txt, then its upper.lua with kilo -l;
                        main() and editorRunScript() as the project has them
  09.09-ui-client       Neovim's client and server, from NOTES.md's quotes, not run
  09.10-could-have-been the three plugins of 09.10 (tracks/kilo/plugins/) and the API functions each
                        calls: PLUGIN_CALLS below, checked against the plugins and NOTES.md
  09.10-frontier        NOTES.md's frontier and the Neovim name for each piece

The maps, the cover and the icon are not made here (archmap.py, covers.py).
"""
import contextlib
import functools
import os
import re
import shutil
import subprocess
import sys
import tempfile
import termios
import time

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
KILO = os.path.join(ROOT, "tracks", "kilo")
NOTES = os.path.join(KILO, "NOTES.md")
UP, DOWN, RIGHT, LEFT = "\x1b[A", "\x1b[B", "\x1b[C", "\x1b[D"
ENTER, ESC = "\r", "\x1b"

# ---------------------------------------------------------------- 09.10: the plugins
#
# The API functions and events each of 09.10's plugins (tracks/kilo/plugins/) calls, in the order
# NOTES.md's "09.10 Features as scripts" lists them. check_plugins() compares them with the plugins'
# own calls (each plugin names kilo.api "api") and stops the generator on any difference.
PLUGIN_CALLS = {
    "vi.lua": ["create_autocmd", "get_cursor", "set_cursor", "get_lines", "line_count", "set_lines",
               "set_statusline", "get_name"],
    "colour.lua": ["create_namespace", "clear_namespace", "add_highlight", "get_name", "get_view", "get_size",
                   "line_count", "get_lines", "create_autocmd"],
    "find.lua": ["set_keymap", "create_autocmd", "create_namespace", "clear_namespace", "add_highlight",
                 "get_cursor", "set_cursor", "get_view", "set_view", "line_count", "get_lines", "message", "input"],
}
PLUGIN_EVENTS = {
    "vi.lua": ["KeyPress", "BufReadPost"],
    "colour.lua": ["BufReadPost", "TextChanged", "CursorMoved"],
    "find.lua": ["KeyPress", "TextChanged", "CursorMoved"],
}
PLUGIN_LINES = {"vi.lua": 89, "colour.lua": 113, "find.lua": 105}


def check_plugins():
    """PLUGIN_CALLS, PLUGIN_EVENTS and PLUGIN_LINES against the plugins themselves, and against
    NOTES.md's list of what each calls."""
    d = os.path.join(KILO, "plugins")
    for name, calls in PLUGIN_CALLS.items():
        with open(os.path.join(d, name)) as f:
            src = f.read()
        assert re.search(r"^local api = kilo\.api$", src, re.M), name
        assert "kilo.api." not in src, name
        used = sorted(set(re.findall(r"\bapi\.(\w+)", src)))
        assert sorted(calls) == used, (name, sorted(calls), used)
        for ev in PLUGIN_EVENTS[name]:
            assert f"'{ev}'" in src, (name, ev)
        assert src.count("\n") == PLUGIN_LINES[name], (name, src.count("\n"))
        said(f"`plugins/{name}` ({PLUGIN_LINES[name]}" if name == "vi.lua" else f"`plugins/{name}` ({PLUGIN_LINES[name]})")
    said("- vi.lua: create_autocmd (KeyPress, BufReadPost), get_cursor, set_cursor, get_lines, line_count, set_lines, "
         "set_statusline, get_name.",
         "- colour.lua: create_namespace, clear_namespace, add_highlight, get_name, get_view, get_size, line_count, "
         "get_lines, create_autocmd (BufReadPost, TextChanged, CursorMoved).",
         "- find.lua: set_keymap (Ctrl-N, Ctrl-O), create_autocmd (KeyPress, TextChanged, CursorMoved), "
         "create_namespace, clear_namespace, add_highlight, get_cursor, set_cursor, get_view, set_view, line_count, "
         "get_lines, message, input.")


# ---------------------------------------------------------------- NOTES.md

@functools.cache
def notes09():
    """NOTES.md's module 09 section, its runs of spaces and line breaks made one space."""
    with open(NOTES) as f:
        text = f.read()
    at = text.index("## 09 An API, and Lua on top of it")
    end = text.find("\n## ", at + 4)
    return " ".join(text[at:end if end > 0 else None].split())


def said(*words):
    """Each of words is in NOTES.md's 09 section (spaces folded). Returns the first."""
    for w in words:
        assert " ".join(w.split()) in notes09(), f"not in NOTES.md 09: {w!r}"
    return words[0]


LESSONS = os.path.join(KILO, "lessons", MOD)


@functools.cache
def lesson(ll):
    """The text of lesson 09.ll."""
    name = next(n for n in os.listdir(LESSONS) if n.startswith(f"09.{ll}-") and n.endswith(".md"))
    with open(os.path.join(LESSONS, name)) as f:
        return f.read()


def lesson_said(ll, *words):
    """Each of words is in lesson 09.ll (spaces folded)."""
    text = " ".join(lesson(ll).split())
    for w in words:
        assert " ".join(w.split()) in text, f"not in 09.{ll}: {w!r}"


def printf_text(arg):
    """What printf makes of its format argument (the lessons use \\n and \\t only)."""
    assert "%" not in arg
    return arg.replace("\\n", "\n").replace("\\t", "\t")


def lesson_file(ll, name):
    """The text of a file a lesson makes with printf (or cat and a here-document) in its Run it."""
    text = lesson(ll)
    m = re.search(r"\$ printf '([^']*)' > build/at/kilo/09\.%s/%s\n" % (ll, re.escape(name)), text)
    if m:
        return printf_text(m.group(1))
    m = re.search(r'\$ printf "([^"]*)" > build/at/kilo/09\.%s/%s\n' % (ll, re.escape(name)), text)
    if m:
        return printf_text(m.group(1))
    m = re.search(r"\$ cat > build/at/kilo/09\.%s/%s <<'EOF'\n(.*?\n)EOF\n" % (ll, re.escape(name)), text, re.S)
    assert m, (ll, name)
    return m.group(1)


def lesson_lua(ll):
    """The init.lua a lesson writes as a block of its own (09.06)."""
    m = re.search(r"<!-- verify: patch file=init.lua create\n@block\n-->\n```lua\n(.*?\n)```\n", lesson(ll), re.S)
    assert m, ll
    return m.group(1)


def ctrl(ch):
    return chr(ord(ch.upper()) & 0x1f)


# ---------------------------------------------------------------- running the project

_built = {}


def project(at, patch=None):
    """The project at lesson `at`, written by ./learn files, given lua/ and built; with patch, a
    list of (file, old, new) made to a scratch copy first (each old there exactly once)."""
    key = (at, tuple(patch or ()))
    if key not in _built:
        d = os.path.join(tempfile.mkdtemp(prefix="kilo-figs09b-"), at)
        subprocess.run([os.path.join(ROOT, "learn"), "files", "kilo", "--at", at, d], check=True,
                       stdout=subprocess.DEVNULL)
        for name, old, new in patch or ():
            path = os.path.join(d, name)
            with open(path) as f:
                src = f.read()
            assert src.count(old) == 1, (at, name, old)
            with open(path, "w") as f:
                f.write(src.replace(old, new))
        core.Track("kilo").module.supply_lua(d)
        subprocess.run(["make", "-s"], cwd=d, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        _built[key] = d
    return _built[key]


def source(at, name):
    with open(os.path.join(project(at), name)) as f:
        return f.read()


@contextlib.contextmanager
def scratch(at, patch=None):
    """(t, tr): a test context on the project at `at` (patched), its scratch directory t.tmp."""
    root = project(at, patch)
    track = core.Track("kilo")
    t = core.TestContext(track, track.lessons[0], root=root)
    try:
        yield t, t.track
    finally:
        t.cleanup()


class Shot:
    """What a screen showed: its lines (trailing spaces dropped), its rows whole (cells), the
    colour of every cell of them as Screen.colors() says it (a letter, "#" reverse, "." none, but
    for every cell, trailing spaces too), the cursor."""

    def __init__(self, ed):
        sc = ed.screen
        self.lines = ed.lines
        self.cells = ["".join(row) for row in sc.grid]
        cols = sc.colors()
        self.colors = []
        for r in range(sc.rows):
            out = []
            for c in range(sc.cols):
                code = ed.t.track.COLOURS.get(sc.fg[r][c], ".")
                if sc.rev[r][c]:
                    code = "#" if code == "." else code.upper()
                out.append(code)
            self.colors.append("".join(out))
            assert self.colors[r].startswith(cols[r])
        self.cursor = ed.cursor


def tracer(fmt_, *args):
    """A C statement that appends one line to the file $KILO_TRACE, if it is set."""
    a = "".join("," + x for x in args)
    return (' { FILE *tf_ = getenv("KILO_TRACE") ? fopen(getenv("KILO_TRACE"),"a") : NULL;'
            f' if (tf_) {{ fprintf(tf_,"{fmt_}\\n"{a}); fclose(tf_); }} }}')


def leave(ed):
    """Ctrl-Q until kilo has gone (with unsaved changes it asks for more); its status."""
    for _ in range(4):
        if ed.s.proc.poll() is not None:
            break
        ed.s.send(ctrl("q"))
        time.sleep(0.1)
    return ed.s.wait_exit(10)


def read_lines(path):
    try:
        with open(path) as f:
            return f.read().split("\n")[:-1]
    except OSError:
        return []


# ---------------------------------------------------------------- 09.06: captures

@functools.cache
def capture0906():
    """kilo at 09.06 on the lesson's sizes.txt with its init.lua, a terminal 8 x 72: the screen and
    every byte written; the namespaces' numbers; the line that clears the spaces at the prompt, and
    the screen; then Down, and the screen."""
    init, text = lesson_lua("06"), lesson_file("06", "sizes.txt")
    with scratch("09.06") as (t, tr):
        ed = tr.edit(t, text, name="sizes.txt", rows=8, cols=72, init=init)
        first = Shot(ed)
        raw = bytes(ed.raw)
        ed.keys(ctrl("e"), "print(kilo.api.create_namespace('numbers'), kilo.api.create_namespace('spaces'))", ENTER)
        ids = ed.message
        ed.keys(ctrl("e"), CLEAR_SPACES, ENTER)
        cleared = Shot(ed)
        ed.keys(DOWN)
        down = Shot(ed)
        ed.quit()
    return {"init": init, "text": text, "first": first, "raw": raw, "ids": ids, "cleared": cleared, "down": down}


CLEAR_SPACES = "kilo.api.clear_namespace(kilo.api.create_namespace('spaces'))"
GREEN = "ns = kilo.api.create_namespace('') kilo.api.add_highlight(ns, 1, 0, 6, 'green')"


@functools.cache
def capture0906moves():
    """The lesson's "Before the frame": the same editor, a green highlight added at the prompt on row
    1, then Enter with the cursor at the start of the first row."""
    with scratch("09.06") as (t, tr):
        ed = tr.edit(t, lesson_file("06", "sizes.txt"), name="sizes.txt", rows=8, cols=72, init=lesson_lua("06"))
        ed.keys(ctrl("e"), GREEN, ENTER)
        before = Shot(ed)
        ed.keys(ENTER)
        after = Shot(ed)
        leave(ed)
    return {"before": before, "after": after}


# ---------------------------------------------------------------- 09.07: captures

BT_PATCH = [
    ("kilo.c", "#include <stdio.h>\n", "#include <stdio.h>\n#include <execinfo.h>\n"),
    ("kilo.c", "    char line[SCRIPT_PROMPT_MAX+1] = {0};\n    int len = 0;\n",
     "    char line[SCRIPT_PROMPT_MAX+1] = {0};\n    int len = 0;\n"
     '    { void *bt_[64]; int n_ = backtrace(bt_,64); FILE *tf_ = getenv("KILO_TRACE") ? '
     'fopen(getenv("KILO_TRACE"),"a") : NULL; if (tf_) { fflush(tf_); '
     "backtrace_symbols_fd(bt_,n_,fileno(tf_)); fclose(tf_); } }\n"),
]


def bt_frames(lines):
    """backtrace_symbols lines ("3   kilo   0x... editorPrompt + 64") as [(image, function)],
    innermost first."""
    out = []
    for line in lines:
        m = re.match(r"\s*\d+\s+(\S+)\s+0x[0-9a-f]+\s+(\S+)\s+\+\s+\d+", line)
        if m:
            out.append((m.group(1), m.group(2)))
    return out


@functools.cache
def capture0907stack():
    """kilo at 09.07 on the lesson's add.c (add.h beside it) with its init.lua, a terminal 12 x 60, in a
    copy whose editorPrompt() writes its backtrace: Ctrl-O, "8"; the C stack, the screen at the prompt;
    Enter, and the screen."""
    init = lesson_file("07", "init.lua")
    with scratch("09.07", BT_PATCH) as (t, tr):
        with open(os.path.join(t.tmp, "add.h"), "w") as f:
            f.write(lesson_file("07", "add.h"))
        trace = os.path.join(t.tmp, "trace")
        ipath = os.path.join(t.tmp, "init.lua")
        with open(ipath, "w") as f:
            f.write(init)
        env = dict(os.environ, KILO_TRACE=trace, KILO_INIT=ipath, KILO_LSP="")
        ed = tr.edit(t, lesson_file("07", "add.c"), name="add.c", rows=12, cols=60, init="env", env=env)
        ed.keys(ctrl("o"), "8")
        prompt = Shot(ed)
        frames = bt_frames(read_lines(trace))
        ed.keys(ENTER)
        after = Shot(ed)
        ed.quit()
    return {"init": init, "frames": frames, "prompt": prompt, "after": after}


QUIT_PATCH = [
    ("kilo.c", "    editorQuit = 1;\n", "    editorQuit = 1;\n" + tracer("apiQuit: the mark") + "\n"),
    ("kilo.c", "    if (editorQuit) exit(0);\n",
     "    if (editorQuit) {" + tracer("editorAfterKey: exit") + " }\n    if (editorQuit) exit(0);\n"),
    ("script.c", "    S.depth--;\n", "    S.depth--;\n" + tracer("scriptProtected: returned, depth %d", "S.depth") + "\n"),
    ("script.c", "    if (S.L && S.depth == 0) lua_close(S.L);\n",
     tracer("scriptStop: closes %s", 'S.L && S.depth == 0 ? "yes" : "no"') + "\n"
     "    if (S.L && S.depth == 0) lua_close(S.L);\n"),
]


@functools.cache
def capture0907quit():
    """The lesson's Ctrl-X (save, and leave) on add.c, in a copy of 09.07 that writes a line at the
    mark, at each return from Lua, before exit() and in scriptStop(): x typed and taken back (a change
    unsaved), then Ctrl-X. The lines, the exit status, the file, the terminal's mode after."""
    init = lesson_file("07", "init.lua")
    text = lesson_file("07", "add.c")
    with scratch("09.07", QUIT_PATCH) as (t, tr):
        trace = os.path.join(t.tmp, "trace")
        ipath = os.path.join(t.tmp, "init.lua")
        with open(ipath, "w") as f:
            f.write(init)
        env = dict(os.environ, KILO_TRACE=trace, KILO_INIT=ipath, KILO_LSP="")
        ed = tr.edit(t, text, name="add.c", rows=12, cols=60, init="env", env=env)
        ed.keys("x", tr.BACKSPACE)
        dirty = "(modified)" in ed.status
        open(trace, "w").close()                # what came before the key: not this figure's
        ed.s.send(ctrl("x"))
        rc = ed.s.wait_exit(10)
        ed.pump(0)
        echo = bool(ed.termios()[3] & termios.ECHO)
        lines = read_lines(trace)
        saved = ed.saved()
    return {"init": init, "text": text, "trace": lines, "rc": rc, "saved": saved, "echo": echo, "dirty": dirty}


# ---------------------------------------------------------------- 09.08: captures

@functools.cache
def capture0908hook():
    """kilo at 09.08 on the lesson's notes.txt with its init.lua, a terminal 8 x 60: "unsaved " typed,
    Ctrl-T (while true do end), "abc" while it runs, then Ctrl-C: the screen; then Ctrl-S."""
    init = lesson_file("08", "init.lua")
    with scratch("09.08") as (t, tr):
        ed = tr.edit(t, lesson_file("08", "notes.txt"), name="notes.txt", rows=8, cols=60, init=init)
        ed.keys("unsaved ")
        ed.s.send(ctrl("t"))
        time.sleep(1.0)
        alive = ed.s.proc.poll() is None
        ed.s.send("abc")
        time.sleep(0.2)
        ed.keys(ctrl("c"))
        shot = Shot(ed)
        ed.keys(ctrl("s"))
        saved_msg = ed.message
        ed.quit()
    return {"init": init, "alive": alive, "shot": shot, "saved_msg": saved_msg}


GROW = "local t = {} while true do t[#t + 1] = {} end"
BIG = "s = string.rep('x', 100 * 2^20)"


@functools.cache
def capture0908mem():
    """The lesson's lines at the prompt, kilo at 09.08 on its notes.txt: BIG, collectgarbage('count'),
    GROW, collectgarbage('count'); and at 09.07, which has no limit, #string.rep('x', 200 * 2^20)."""
    out = {}
    for at in ("09.08", "09.07"):
        with scratch(at) as (t, tr):
            ed = tr.edit(t, lesson_file("08", "notes.txt"), name="notes.txt", rows=8, cols=60)

            def lua(line):
                ed.keys(ctrl("e"), line, ENTER)
                return ed.message
            r = {}
            if at == "09.08":
                r["big"] = lua(BIG)
                r["big_after"] = float(lua("collectgarbage('count')"))
                r["grow"] = lua(GROW)
                r["grow_after"] = float(lua("collectgarbage('count')"))
            else:
                r["big200"] = lua("#string.rep('x', 200 * 2^20)")
            ed.quit()
            out[at] = r
    return out


# ---------------------------------------------------------------- 09.09: captures

@functools.cache
def capture0909():
    """kilo at 09.09 on the lesson's notes.txt: the editor's screen (a terminal 8 x 40), Ctrl-Q; then
    the lesson's upper.lua with kilo -l: its output, status and the file."""
    upper, text = lesson_file("09", "upper.lua"), lesson_file("09", "notes.txt")
    out = {"upper": upper, "text": text}
    with scratch("09.09") as (t, tr):
        ed = tr.edit(t, text, name="notes.txt", rows=8, cols=40)
        out["shot"] = Shot(ed)
        ed.quit()
        r = tr.run_script(t, upper, text, name="notes.txt", script="upper.lua")
        with open(os.path.join(t.tmp, "notes.txt")) as f:
            out["cli"] = {"rc": r.returncode, "stdout": r.stdout, "stderr": r.stderr, "file": f.read()}
    return out


# ---------------------------------------------------------------- drawing

class F9(Fig):
    """figlib.Fig whose text stays ASCII (a character past it as a character reference), with a
    filled shape that has no stroke."""

    def text(self, x, y, s, cls="t", size=12, anchor="start", weight=None, mono=False):
        super().text(x, y, s, cls, size, anchor, weight, mono)
        self.out[-1] = self.out[-1].encode("ascii", "xmlcharrefreplace").decode()

    def bar(self, x, y, w, h, cls, rx=0):
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


def notes(f, x, y, s, width, cls="tm", size=10.5, lh=14, weight=None):
    lines = wrap(s, width)
    for k, line in enumerate(lines):
        f.text(x, y + k * lh, line, cls, size, weight=weight)
    return y + len(lines) * lh


def code(f, x, y, lines, size=9.5, lh=None, w=None, mark=(), cls="t"):
    """A code card: lines in monospace on the code background; the line numbers in mark (from 0)
    in accent. Returns (bottom, [baseline of each line])."""
    lh = lh or size * 1.45
    w = w or max(len(s) for s in lines) * cwid(size) + 16
    f.rect(x, y, w, len(lines) * lh + 10, "m fs", 5)
    bases = []
    for k, s in enumerate(lines):
        b = y + 5 + (k + 0.75) * lh
        bases.append(b)
        if k in mark:
            f.bar(x + 3, b - lh * 0.72, w - 6, lh, "af", 2)
        mono(f, x + 8, b, s, "ta" if k in mark else cls, size, weight=700 if k in mark else None)
    return y + len(lines) * lh + 10, bases


def screen(f, x, y, shot, cw, rh, cols, rows=None, status=True, cursor=False):
    """A terminal screen from a Shot, in a rounded frame: the rows given (all by default); the
    status bar (the last row but one) in reverse video; each cell drawn in reverse as a filled
    cell, a green cell in accent in an accent outline, each other coloured cell in accent on the
    accent's soft fill. Returns {row: baseline}."""
    n = len(shot.cells)
    rows = list(range(n)) if rows is None else list(rows)
    size = cw / 0.6
    f.rect(x - 6, y - 4, cols * cw + 12, len(rows) * rh + 8, "s fs", 5)
    base = {}
    for k, r in enumerate(rows):
        top = y + k * rh
        b = top + rh * 0.72
        base[r] = b
        cells, codes = shot.cells[r][:cols], shot.colors[r][:cols]
        if status and r == n - 2:
            f.bar(x - 1, top + 1, cols * cw + 2, rh - 2, "t", 1.5)
            mono(f, x, b, cells.rstrip(), "f", size)
            continue
        i = 0
        while i < cols:
            j = i
            while j < cols and codes[j] == codes[i]:
                j += 1
            run, c = cells[i:j], codes[i]
            if c == ".":
                mono(f, x + i * cw, b, run, "t", size)
            elif c == "#":
                f.bar(x + i * cw, top + 1.5, (j - i) * cw, rh - 3, "t", 1)
                mono(f, x + i * cw, b, run, "f", size)
            elif c == "g":                      # green: an outline, so it is told from yellow
                f.rect(x + i * cw, top + 1.5, (j - i) * cw, rh - 3, "a", 1)
                mono(f, x + i * cw, b, run, "ta", size, weight=700)
            else:
                f.bar(x + i * cw, top + 1.5, (j - i) * cw, rh - 3, "af", 1)
                mono(f, x + i * cw, b, run, "ta", size, weight=700)
            i = j
    if cursor and shot.cursor[0] in base:
        r, c = shot.cursor
        f.rect(x + c * cw - 0.5, base[r] - rh * 0.72 + 1.5, cw + 1, rh - 3, "a", 1)
    return base


def arrow_label(f, x1, y, x2, label, cls="a", tcls="ta", size=10, above=True):
    f.line(x1, y, x2, y, cls, arrow=True)
    f.text((x1 + x2) / 2, y - 6 if above else y + 13, label, tcls, size, "middle", 600)


# ---------------------------------------------------------------- 09.06

def drawn_over0906():
    cap = capture0906()
    shot, raw = cap["first"], cap["raw"]
    lines = cap["text"].split("\n")
    r = 2                                          # the third row: the one with the tab
    row, cells = lines[r], shot.lines[r]
    assert row.startswith("\t") and cells == " " * 8 + row[1:], (row, cells)
    i = raw.rfind(cells.encode() + b"\x1b[0K")
    assert i >= 0
    j = raw.index(b"\r\n", i + len(cells)) + 2
    data = raw[i:j].decode()
    m = re.fullmatch(r"(.*)\x1b\[0K\r\x1b\[(\d+)C\x1b\[(\d+)m(\d+)\x1b\[0m\r\n", data)
    assert m and m.group(1) == cells, data
    n, style, num = int(m.group(2)), m.group(3), m.group(4)
    b0 = row.index(num)
    assert style == "33" and '{"yellow","33"}' in source("09.06", "kilo.c") and n == cells.index(num)
    lesson_said("06", f"then `\\r`, `ESC [ {n} C`, `ESC [ {style} m`, `{num}`, `ESC [ 0 m`", "[y:307200]")
    said(f"the row, `ESC[0K`, then `\\r ESC[{n}C ESC[{style}m {num} ESC[0m`")
    assert "kilo.api.add_highlight(numbers, top + i - 1, s - 1, e - 1, 'yellow')" in cap["init"]
    f = F9("f09-06a", f"The bytes kilo at 09.06 writes for the row with a tab and {num}: the row as always, then "
           f"back to its start, {n} cells right, yellow on, {num} again, colours off", 330)
    f.text(24, 22, "kilo at 09.06 on sizes.txt with the lesson's init.lua: what it writes for the third row, "
           "a tab and pixels = 307200", "tm", 11)
    size = 11
    cw = cwid(size)
    x, y = 24, 58
    toks = [(cells, "t", 1), ("ESC[0K", "tm", 1), ("\\r", "a", 2), (f"ESC[{n}C", "a", 2), (f"ESC[{style}m", "a", 2),
            (num, "a", 2), ("ESC[0m", "a", 2), ("\\r\\n", "tm", 3)]
    spans = {}
    for s_, cls, part in toks:
        x0 = x
        if s_ == cells:                            # the tab's eight spaces, each a faint mark
            for k in range(8):
                cx = x + k * cw + cw * 0.18
                f.path(f"M{fmt(cx)} {fmt(y - 2.5)} L{fmt(cx)} {y} L{fmt(cx + cw * 0.64)} {y} "
                       f"L{fmt(cx + cw * 0.64)} {fmt(y - 2.5)}", "m")
            x = mono(f, x + 8 * cw, y, s_[8:], "t", size)
        else:
            x = mono(f, x, y, s_, "ta" if cls == "a" else cls, size, weight=700 if cls == "a" else None)
        spans.setdefault(part, [x0, x])[1] = x
        x += 6
    a, b = spans[1]
    f.brace_h(a, b, y + 10)
    f.text(a, y + 28, "first pass: the row, and erase to its end", "t", 10.5)
    a, b = spans[2]
    f.brace_h(a, b, y + 10, "a")
    f.text(a, y + 44, "second pass: the highlight, over the same cells", "ta", 10.5, weight=600)
    call = f"kilo.api.add_highlight(numbers, {r}, {b0}, {b0 + len(num)}, 'yellow')"
    f.text(24, 126, "the call paint_numbers() made for it:", "tm", 10.5)
    mono(f, 24 + figlib.tw("the call paint_numbers() made for it:", 10.5) + 8, 126, call, "t", 10)
    # bytes to cells
    U, X0, yb, yc = 11.0, 92, 158, 194
    f.text(X0 - 8, yb + 12, "bytes", "tm", 10, "end")
    f.text(X0 - 8, yc + 12, "cells", "tm", 10, "end")
    cx = 0
    for k, ch in enumerate(row):
        wd = 8 if ch == "\t" else 1
        hot = b0 <= k < b0 + len(num)
        f.rect(X0 + cx * U + 0.75, yb, wd * U - 1.5, 17, "a af" if hot else "s fs", 2)
        f.text(X0 + (cx + wd / 2) * U, yb + 12.5, "tab" if ch == "\t" else ch, "ta" if hot else "t", 9.5, "middle",
               700 if hot else None, mono=ch != "\t")
        if k in (0, 1, b0) or k == len(row) - 1:
            f.text(X0 + (cx + 0.5) * U, yb - 4, str(k), "ta" if hot else "tm", 8.5, "middle", mono=True)
        cx += wd
    for c in range(len(cells)):
        hot = n <= c < n + len(num)
        f.rect(X0 + c * U + 0.75, yc, U - 1.5, 17, "a af" if hot else "m f", 2)
        if c in (0, 7, 8, n) or c == len(cells) - 1:
            f.text(X0 + (c + 0.5) * U, yc + 29, str(c), "ta" if c == n else "tm", 8.5, "middle",
                   700 if c == n else None, mono=True)
    f.path(f"M{fmt(X0)} {yc - 7} L{fmt(X0 + n * U)} {yc - 7}", "a", arrow=True)
    gx = X0 + len(cells) * U + 14
    f.text(gx, yb + 12, f"bytes {b0} to {b0 + len(num)} of the row:", "t", 10)
    f.text(gx, yb + 26, "the tab is one byte", "tm", 10)
    f.text(gx, yc + 6, "and eight cells, so", "tm", 10)
    f.text(gx, yc + 20, f"{num} starts in cell {n}: ESC[{n}C", "ta", 10, weight=700)
    # the row on the terminal, after each pass
    cw2, rh = 9.0, 22
    tx, ty = 40, 250
    for k, (label, hot) in enumerate((("after the first pass", False), (f"after the second: {num} in yellow", True))):
        xx = tx + k * 300
        f.rect(xx - 6, ty, 24 * cw2 + 12, rh, "s fs", 4)
        if hot:
            f.bar(xx + n * cw2, ty + 3, len(num) * cw2, rh - 6, "af", 2)
            mono(f, xx, ty + 15.5, cells[:n], "t", 15)
            mono(f, xx + n * cw2, ty + 15.5, num, "ta", 15, weight=700)
        else:
            mono(f, xx, ty + 15.5, cells, "t", 15)
        f.text(xx - 6, ty + rh + 16, label, "ta" if hot else "tm", 10.5, weight=600 if hot else None)
    return f


def namespaces0906():
    cap = capture0906()
    first, cleared, down = cap["first"], cap["cleared"], cap["down"]
    assert cap["ids"] == "1 2", cap["ids"]
    rows = range(3)
    for r in rows:                                # the clear took the reverse, and only it
        assert "#" not in cleared.colors[r][:30]
        assert cleared.colors[r].replace("#", ".")[:30] == first.colors[r].replace("#", ".")[:30]
        assert cleared.cells[r] == first.cells[r] and down.colors[r][:30] == first.colors[r][:30]
    assert "y" in first.colors[0] and "###" in first.colors[1][:30], first.colors[:2]
    lesson_said("06", CLEAR_SPACES, "The reverse spaces go; every yellow stays. Press Down, and the spaces are back, "
                "put there again on CursorMoved.", "local numbers = kilo.api.create_namespace('numbers')",
                "local spaces = kilo.api.create_namespace('spaces')")
    f = F9("f09-06b", "Two scripts draw on the same rows, each in a namespace of its own: numbers in yellow in "
           "namespace 1, spaces at a row's end in reverse in namespace 2; clearing namespace 2 leaves every yellow",
           318)
    f.text(24, 22, "kilo at 09.06 on sizes.txt with the lesson's init.lua, a terminal 8 x 72 (its first three rows)",
           "tm", 11)
    cw, rh = 7.0, 17
    xs, y = (30, 238, 446), 76
    titles = [("both drawn", "on BufReadPost", "t"), ("clear_namespace(2)", "typed at the prompt", "ta"),
              ("Down", "CursorMoved: put again", "t")]
    for x, shot, (title, sub, cls) in zip(xs, (first, cleared, down), titles):
        f.text(x - 6, 48, title, cls, 11, weight=700, mono=title.startswith("clear"))
        f.text(x - 6, 62, sub, "tm", 10)
        screen(f, x, y, shot, cw, rh, 23, rows=rows, status=False)
    for x in xs[:2]:
        f.line(x + 23 * cw + 8, y + 1.5 * rh, x + 23 * cw + 22, y + 1.5 * rh, "m", arrow=True)
    ly = 170

    def swatch(x, yy, cls_bar, cls_text, label):
        f.bar(x, yy - 10, 3 * 7.8, 13, cls_bar, 2)
        f.text(x + 3, yy, label, cls_text, 10, weight=700, mono=True)
    swatch(24, ly, "af", "ta", "640")
    mono(f, 56, ly, "local numbers = kilo.api.create_namespace('numbers')", "t", 9.5)
    f.text(56, ly + 15, "namespace 1: every number on the screen, in yellow", "tm", 10)
    swatch(24, ly + 40, "t", "f", "   ")
    mono(f, 56, ly + 40, "local spaces = kilo.api.create_namespace('spaces')", "t", 9.5)
    f.text(56, ly + 55, "namespace 2: the spaces at the end of a row, in reverse", "tm", 10)
    mono(f, 24, ly + 86, "lua: " + CLEAR_SPACES, "ta", 9.5, weight=700)
    f.text(24, ly + 102, "The same name gives the same number, 2: clear_namespace() takes that namespace's "
           "highlights, and no other's.", "tm", 10.5)
    f.text(24, ly + 118, "Both scripts clear and draw again on every event, so the next one that fires brings the "
           "spaces back.", "tm", 10.5)
    return f


def moves0906():
    cap = capture0906moves()
    before, after = cap["before"], cap["after"]
    rows_b = cap_rows = 3                         # kilo's rows; Neovim's side draws the first two
    assert before.colors[1][:6] == "gggggg" and before.lines[1].startswith("height")
    assert after.lines[1] == "width = 640" and after.colors[1][:6] == "gggggg" and "g" not in after.colors[2]
    assert "y" in after.colors[2] and "#" in after.colors[2][:30]          # the scripts' follow their row
    lesson_said("06", GREEN, "`[g:width ]= [y:640]`", "the green stays on row 1")
    said("Extmarks move with the text (extmark.c:", "adjustment to text changes", "kilo's do not",
         "then marks (mark_adjust_buf, extmark_splice)", "Marks are moved by calls to extmark_splice.")
    f = F9("f09-06c", "A row put in above a highlighted word: kilo's highlight stays on its row number, over the "
           "row that moved there; Neovim's extmark moves down with the word", 322)
    f.text(24, 22, "kilo at 09.06 on sizes.txt, the lesson's init.lua and a green highlight added at the prompt; "
           "Neovim from its source", "tm", 11)
    cw, rh = 6.4, 16
    f.text(24, 52, "kilo: a highlight is a row and a range of bytes", "t", 11.5, weight=700)
    y = 96
    for x, shot, rows_, (title, sub, cls) in ((30, before, range(rows_b), ("before", "green: row 1, bytes 0 to 6", "t")),
                                              (210, after, range(cap_rows + 1),
                                               ("Enter at the top", "green: still row 1, bytes 0 to 6", "ta"))):
        f.text(x - 6, y - 26, title, cls, 11, weight=700)
        f.text(x - 6, y - 12, sub, "tm", 10)
        screen(f, x, y, shot, cw, rh, 23, rows=rows_, status=False)
    f.line(30 + 23 * cw + 8, y + 1.5 * rh, 30 + 23 * cw + 22, y + 1.5 * rh, "m", arrow=True)
    f.text(24, 186, "the line typed at the prompt, before Enter:", "tm", 10)
    a_, b_ = GREEN.split(" kilo.api.add_highlight")
    mono(f, 24, 202, a_, "t", 8.6)
    mono(f, 24, 215, "kilo.api.add_highlight" + b_, "t", 8.6)
    notes(f, 24, 240, "The yellow and the reverse are put again by the scripts on TextChanged, so they follow their "
          "rows. The green was put once: it stays on row 1, now over width.", 64, "t", 10, 13)
    # Neovim's side, from its source
    f.line(388, 44, 388, 270, "m", dash=True)
    nx = 410
    f.text(nx - 6, 52, "Neovim: an extmark", "t", 11.5, weight=700)
    words = cap["before"].lines[:2]
    w = "height"
    for k, (title, sub) in enumerate((("before", "row 1, col 0"), ("a row put in", "moved: row 2, col 0"))):
        xx = nx + k * 110
        f.text(xx - 6, y - 26, title, "ta" if k else "t", 11, weight=700)
        f.text(xx - 6, y - 12, sub, "tm", 10)
        lines = ([""] if k else []) + [l_[:13] for l_ in words]
        f.rect(xx - 6, y - 4, 13 * cw + 12, 4 * rh + 8, "s fs", 5)
        for r, line in enumerate(lines[:4]):
            b = y + r * rh + rh * 0.72
            if line.startswith(w):
                f.rect(xx, y + r * rh + 1.5, len(w) * cw, rh - 3, "a", 1)
                mono(f, xx, b, w, "ta", cw / 0.6, weight=700)
                mono(f, xx + len(w) * cw, b, line[len(w):], "t", cw / 0.6)
            else:
                mono(f, xx, b, line, "t", cw / 0.6)
    f.line(nx + 13 * cw + 8, y + 1.5 * rh, nx + 13 * cw + 18, y + 1.5 * rh, "m", arrow=True)
    yy = notes(f, nx - 6, 196, "nvim_buf_set_lines calls extmark_splice, and \"Marks are moved by calls to "
               "extmark_splice\" (extmark.c).", 38, "tm", 10, 13)
    notes(f, nx - 6, yy + 6, "They sit in a tree (marktree.c), with \"adjustment to text changes\".", 38, "tm", 10, 13)
    f.text(24, 304, "kilo: the script pays, again after every change. Neovim: the editor pays, once, in every edit; "
           "every plugin gains.", "t", 10.5)
    return f


# ---------------------------------------------------------------- 09.07

def lua_frame(name):
    """Is name one of Lua's own functions (lua/src), not kilo's?"""
    return name.startswith(("lua", "luaD_", "luaV_", "precall")) and name not in ("luaL_ref",)


def nested_loop0907():
    cap = capture0907stack()
    frames = [fn for img, fn in cap["frames"] if img == "kilo"]
    assert cap["frames"][-1][1] in ("start",) or cap["frames"][-1][0] != "kilo"
    want = ["editorPrompt", "apiInput", "scriptDispatch"]
    assert frames[:3] == want and frames[-2:] == ["editorProcessKeypress", "main"], frames
    for fn in ("editorScriptKey", "scriptCall", "scriptProtected", "lua_pcallk", "scriptCallIn", "luaV_execute"):
        assert fn in frames, fn
    ksrc = source("09.07", "kilo.c") + source("09.07", "script.c")
    for fn in frames:
        if not lua_frame(fn):
            assert re.search(r"^\w[\w *]*\b" + fn + r"\(", ksrc, re.M), fn
    assert cap["prompt"].lines[-1] == "Go to line: 8" and cap["prompt"].lines[-2].startswith("add.c - 9 lines")
    assert cap["after"].lines[-2].endswith("8/9") and cap["after"].cursor[1] == 0
    lesson_said("07", "add.c - 9 lines 1/9 Go to line: 8", "and the bar says `8/9`")
    init = cap["init"].split("\n")
    ln = next(k for k, s in enumerate(init) if "api.input(" in s) + 1      # init.lua's line number
    f = F9("f09-07a", "The C stack while input() waits in kilo at 09.07: main's loop, the key, the Lua function "
           "mapped to Ctrl-O, input(), and the prompt's own key loop on top", 352)
    f.text(24, 22, "kilo at 09.07 on add.c with the lesson's init.lua: Ctrl-O, then 8 typed; the C stack, "
           "innermost at the top", "tm", 11)
    size, lh = 9, 13
    x, w = 40, 150
    names = ["read()", "editorReadKey()"] + frames
    y0 = 44
    ys = {}
    for k, fn in enumerate(names):
        yy = y0 + k * lh
        ys[k] = yy
        dashed = k < 2
        lua_ = lua_frame(fn)
        loop = fn in ("editorPrompt", "main")
        cls = "a af" if loop else ("m f" if lua_ or dashed else "s f")
        f.rect(x, yy, w, lh - 2, cls, 2, dash=dashed)
        f.text(x + 6, yy + 8.6, fn, "ta" if loop else ("tm" if lua_ or dashed else "t"), size,
               weight=700 if loop else None, mono=True)
        if loop:
            f.text(x + w - 5, yy + 8.6, "while(1)", "ta", 8, "end", 700, mono=True)
    f.text(x + w / 2, y0 + len(names) * lh + 12, "the bottom of the stack", "tm", 9.5, "middle")
    f.text(16, y0 + 8, "top", "tm", 9.5)

    # the groups, by where their first and last frame are
    def idx(fn):
        return names.index(fn)
    groups = [
        (0, idx("editorPrompt"), "the prompt's own key loop",
         "draws, reads a key: it waits here", True),
        (idx("apiInput"), idx("scriptDispatch"), "input()", "the dispatcher, then the API's function", False),
        (idx("scriptDispatch") + 1, idx("luaV_execute"), "the mapped Lua function",
         f"init.lua, line {ln}: api.input(...)", False),
        (idx("luaV_execute") + 1, idx("scriptProtected"), "into Lua, protected",
         "scriptCallIn: the function by its reference", False),
        (idx("scriptCall"), idx("editorScriptKey"), "the key", "Ctrl-O is mapped: offered to Lua", False),
        (idx("editorProcessKeypress"), idx("main"), "main's loop", "it read Ctrl-O, and has not returned", True),
    ]
    bx = x + w + 8
    for a, b, title, sub, hot in groups:
        top, bot = ys[a] + 1, ys[b] + lh - 3
        f.path(f"M{fmt(bx)} {fmt(top)} L{fmt(bx + 5)} {fmt(top)} L{fmt(bx + 5)} {fmt(bot)} L{fmt(bx)} {fmt(bot)}",
               "a" if hot else "m")
        mid = (top + bot) / 2
        f.text(bx + 12, mid - 1, title, "ta" if hot else "t", 10.5, weight=700)
        f.text(bx + 12, mid + 11, sub, "tm", 9.5)
    f.text(x + w + 20, y0 + len(names) * lh + 12, "grey: Lua's own functions (lua/src)", "tm", 9.5)
    # the message line meanwhile
    sx = 444
    f.text(sx, 56, "the message line meanwhile", "tm", 10)
    f.rect(sx, 64, 172, 20, "s fs", 4)
    mono(f, sx + 8, 78, cap["prompt"].lines[-1], "t", 10)
    notes(f, sx, 112, "Two key loops on one stack. Enter gives the line back to the Lua function, which moves the "
          f"cursor (to line 8: the bar then says {cap['after'].lines[-2].split()[-1]}); only then does main's "
          "loop read a key again.", 32, "t", 10, 13.5)
    return f


def quit_mark0907():
    cap = capture0907quit()
    tr_ = cap["trace"]
    assert tr_ == ["apiQuit: the mark", "scriptProtected: returned, depth 0", "editorAfterKey: exit",
                   "scriptStop: closes yes"], tr_
    assert cap["rc"] == 0 and cap["echo"] and cap["dirty"] and cap["saved"] == cap["text"]
    lesson_said("07", "Ctrl-X saves and leaves", "`echo $?` says 0", "if (editorQuit) exit(0);",
                "if (S.L && S.depth == 0) lua_close(S.L);")
    init = cap["init"].rstrip("\n").split("\n")
    at = next(k for k, s in enumerate(init) if s.startswith("-- Ctrl-X"))
    qlines = init[at:at + 4]
    assert qlines[-1] == "end)" and "api.quit(false)" in qlines[2], qlines
    ksrc, ssrc = source("09.07", "kilo.c"), source("09.07", "script.c")
    run = [["editorQuit = 1;"], ["status = lua_pcall(L,1,0,0);", "S.depth--;"],
           ["if (editorQuit) exit(0);", "disableRawMode(STDIN_FILENO);", "if (S.L && S.depth == 0) lua_close(S.L);"]]
    for k, lines in enumerate(run):
        for line in lines:
            assert line in (ksrc if k != 1 else ssrc) or line in ssrc, line
    f = F9("f09-07b", "quit() inside a mapped function, in kilo at 09.07: the mark is set, the function returns to "
           "C, and only then does kilo leave and close Lua", 316)
    f.text(24, 22, "kilo at 09.07 on add.c with the lesson's init.lua: x typed and taken back, then Ctrl-X",
           "tm", 11)
    _, qb = code(f, 24, 32, qlines, size=9.5)
    qw = max(len(q) for q in qlines) * cwid(9.5) + 16

    def at_line(*ks):
        """An accent frame round lines ks of the code card: where Lua is."""
        lh = 9.5 * 1.45
        top, bot = qb[ks[0]] - lh * 0.75, qb[ks[-1]] + lh * 0.3
        f.rect(27, top, qw - 6, bot - top, "a", 2)
    f.text(24, 118, "the stack", "tm", 10.5)
    f.text(306, 118, "the state", "tm", 10.5)

    def stack(items):
        """items bottom first: (name, kind), kind "live", "hot" (accent) or "gone" (dashed)."""
        bx, bw, bh = 24, 270, 17
        for k, (name, kind) in enumerate(items):
            yy = 290 - (k + 1) * (bh + 2)
            cls = {"live": "s f", "hot": "a af", "gone": "m f"}[kind]
            f.rect(bx, yy, bw, bh, cls, 3, dash=kind == "gone")
            f.text(bx + 8, yy + 12, name, {"live": "t", "hot": "ta", "gone": "tm"}[kind], 9.5,
                   weight=700 if kind == "hot" else None, mono=True)

    def state(rows_, lines):
        for k, (key, val, hot) in enumerate(rows_):
            yy = 140 + k * 19
            f.text(306, yy, key, "tm", 10.5)
            f.text(400, yy, val, "ta" if hot else "t", 10.5, weight=700 if hot else None)
        f.text(306, 262, "the line of kilo's that does it:", "tm", 9.5)
        for k, s_ in enumerate(lines):
            mono(f, 306, 277 + k * 13, s_, "ta", 8.6, weight=700)
    base = [("main: while(1)", "live"), ("editorProcessKeypress", "live"), ("editorScriptKey", "live"),
            ("scriptCall", "live")]
    with steps.step(f, "Ctrl-X: the function mapped to it saves the file, then calls quit(false), which only sets "
                       "a mark, editorQuit = 1, and returns to the Lua function: it is still running."):
        at_line(2)
        stack(base + [("scriptProtected: lua_pcall", "live"), ("Lua: the function mapped to <C-x>", "live"),
                      ("api.quit(false): apiQuit", "hot")])
        state([("editorQuit", "1: the mark", True), ("calls into Lua", "1, still running", False),
               ("add.c", "saved by api.save()", False), ("the Lua state", "open", False),
               ("the terminal", "raw", False), ("kilo", "running", False)], run[0])
    with steps.step(f, "The function ends: the protected call returns, and the stack is C alone. No frame is "
                       "drawn: the main loop comes round first."):
        at_line(3)
        stack(base + [("scriptProtected: lua_pcall returned", "hot"), ("Lua: the function mapped to <C-x>", "gone"),
                      ("api.quit(false): apiQuit", "gone")])
        state([("editorQuit", "1", False), ("calls into Lua", "0", True), ("add.c", "saved", False),
               ("the Lua state", "open", False), ("the terminal", "raw", False), ("kilo", "running", False)], run[1])
    with steps.step(f, "At the top of main's loop, editorAfterKey() reads the mark and calls exit(0). The functions "
                       "registered with atexit() put the terminal back, and scriptStop() closes the Lua state: no Lua "
                       "function is on the stack."):
        stack([("main: while(1)", "live"), ("editorAfterKey: exit(0)", "live"), ("atexit: scriptStop", "hot")])
        state([("editorQuit", "1", False), ("calls into Lua", "0", False), ("add.c", "saved", False),
               ("the Lua state", "closed: lua_close", True), ("the terminal", "put back (ECHO on)", True),
               ("kilo", f"gone, status {cap['rc']}", True)], run[2])
    return f


# ---------------------------------------------------------------- 09.08

def hook0908():
    cap = capture0908hook()
    h = source("09.08", "script.h")
    c = source("09.08", "script.c")
    count = int(re.search(r"#define SCRIPT_HOOK_COUNT (\d+)", h).group(1))
    for needle in ("lua_sethook(L,scriptHook,LUA_MASKCOUNT,1);", "luaL_where(L,0);", 'lua_pushliteral(L,"interrupted");',
                   "if (S.depth == 0 && status != LUA_OK) lua_gc(L,LUA_GCCOLLECT);",
                   "lua_sethook(L,scriptHook,LUA_MASKCOUNT,SCRIPT_HOOK_COUNT);", "poll(&pfd,1,0) == 1",
                   "if (buf[i] == 3) S.interrupted = 1;"):
        assert needle in c, needle
    shot = cap["shot"]
    assert cap["alive"] and shot.lines[0] == "unsaved the first line" and shot.lines[-1] == "init.lua:1: interrupted"
    assert cap["saved_msg"] == "23 bytes written on disk", cap["saved_msg"]
    assert cap["init"] == "kilo.api.set_keymap('<C-t>', function() while true do end end)\n"
    lesson_said("08", f"kilo's runs every {count}, about every 0.2 ms here", "unsaved the first line",
                "init.lua:1: interrupted", "Ctrl-S says `23 bytes written on disk`",
                "lua_sethook(lua,luaMaskCountHook,LUA_MASKCOUNT,100000);")
    ms = 0.2
    f = F9("f09-08a", f"The count hook in kilo at 09.08: every {count} instructions it looks at the keyboard; a Ctrl-C "
           "there raises interrupted, which goes up to the protected call", 338)
    f.text(24, 22, "kilo at 09.08 on notes.txt with the lesson's init.lua: unsaved typed, Ctrl-T; a second later "
           "a b c, then Ctrl-C", "tm", 11)
    y, x0, x1 = 96, 40, 470
    f.line(x0, y, x1, y, "m")
    k = x0
    while k <= x1:
        f.line(k, y - 3, k, y + 3, "m")
        k += 4
    looks = [x0 + 30 + j * 62 for j in range(7)]
    for j, lx in enumerate(looks):
        f.circle(lx, y, 5, "a fa" if j == len(looks) - 1 else "a f")
    f.brace_h(looks[0], looks[1], y + 14)
    f.text((looks[0] + looks[1]) / 2, y + 30, f"{count} instructions", "t", 10, "middle", 600)
    f.text((looks[0] + looks[1]) / 2, y + 43, f"about {ms:g} ms", "tm", 10, "middle")
    f.text(looks[2], y + 30, "each look: poll() with no wait;", "tm", 10)
    f.text(looks[2], y + 43, "nothing there: the script goes on", "tm", 10)
    for label, look in (("a b c", 5), ("Ctrl-C", 6)):
        hot = label == "Ctrl-C"
        f.text(looks[look], y - 40, label, "ta" if hot else "t", 10.5, "middle", 700, mono=not hot)
        f.line(looks[look], y - 34, looks[look], y - 10, "a" if hot else "s", arrow=True)
    f.text(x1 + 8, y - 4, "a b c: read by a look,", "t", 10)
    f.text(x1 + 8, y + 9, "and dropped", "t", 10)
    f.text(x1 + 8, y + 26, "Ctrl-C: the last look", "ta", 10, weight=700)
    f.text(x1 + 8, y + 39, "finds a 3", "ta", 10, weight=700)
    f.text(24, 50, f"Lua's instructions (not to scale: a second is some {int(round(1000 / ms, -2))} looks)", "tm", 10)
    f.text(24, 172, "then the error goes up the stack, to the protected call", "tm", 10.5)
    boxes = [("scriptHook: the count set to 1; where + \"interrupted\"; lua_error", "hot"),
             ("init.lua:1, the function mapped to <C-t>: unwound", "gone"),
             ("scriptCallIn, and Lua's own frames: unwound", "gone"),
             ("scriptProtected: lua_pcall returns the error; scriptReport()", "live"),
             ("at depth 0: a full collection, the hook's count back", "live")]
    bx, bw, bh = 24, 330, 19
    for j, (label, kind) in enumerate(boxes):
        yy = 182 + j * (bh + 4)
        f.rect(bx, yy, bw, bh, {"hot": "a af", "gone": "m f", "live": "s f"}[kind], 3, dash=kind == "gone")
        f.text(bx + 8, yy + 13, label, {"hot": "ta", "gone": "tm", "live": "t"}[kind], 9.5,
               weight=700 if kind == "hot" else None)
    f.path(f"M{bx + bw + 4} {182 + bh / 2} C{bx + bw + 30} {182 + bh / 2}, {bx + bw + 30} {182 + 3 * (bh + 4) + bh / 2}, "
           f"{bx + bw + 6} {182 + 3 * (bh + 4) + bh / 2}", "a", arrow=True)
    f.text(bx + bw + 32, 182 + 1.5 * (bh + 4) + 14, "longjmp", "ta", 10, weight=700, mono=True)
    sx = 440
    f.text(sx, 176, "the screen after: row 0, and", "tm", 10)
    f.text(sx, 189, "the message line", "tm", 10)
    f.rect(sx, 196, 176, 40, "s fs", 4)
    mono(f, sx + 8, 210, shot.lines[0], "t", 10)
    mono(f, sx + 8, 228, shot.lines[-1], "ta", 10, weight=700)
    notes(f, sx, 254, f"The a b c never reached the text. Then Ctrl-S: \"{cap['saved_msg']}\".", 31, "t", 10, 13)
    f.text(24, 312, "Redis sets the same kind of hook: lua_sethook(lua,luaMaskCountHook,LUA_MASKCOUNT,100000) "
           "(src/script_lua.c).", "tm", 10)
    f.text(24, 326, "Neovim's Lua glue (src/nvim/lua/executor.c and the files beside it) calls no lua_sethook.",
           "tm", 10)
    return f


def allocator0908():
    cap = capture0908mem()
    h = source("09.08", "script.h")
    c = source("09.08", "script.c")
    line_h = "#define SCRIPT_MAX_MEMORY (64*1024*1024)"
    line_c = "if (nsize > osize && S.used-osize+nsize > SCRIPT_MAX_MEMORY) return NULL;"
    assert line_h in h and line_c in c and "S.L = lua_newstate(scriptAlloc,NULL);" in c
    assert "S.L = luaL_newstate();" in source("09.07", "script.c")
    r8, r7 = cap["09.08"], cap["09.07"]
    assert r8["big"] == r8["grow"] == "not enough memory", r8
    assert r8["big_after"] < 100 and r8["grow_after"] < 100, r8
    assert r7["big200"] == str(200 * 2 ** 20), r7
    lesson_said("08", f"| `{BIG}` | `not enough memory` |", f"| `{GROW}` | `not enough memory` |",
                "`#string.rep('x', 200 * 2^20)` answered `209715200`, and Lua went on holding 212642 KB",
                line_c)
    f = F9("f09-08b", "Lua's memory in kilo: every block through scriptAlloc(), refused past 64 MB, and given back "
           "by the collection after the error", 340)
    f.text(24, 22, "kilo at 09.08 on notes.txt, lines typed at the prompt; at 09.07, with no limit, one line",
           "tm", 11)
    code(f, 24, 32, [line_h + "        script.h", line_c + "  script.c, scriptAlloc()"], size=8.8)
    X0, W = 40, 400
    px = W / 64

    def axis(y):
        for mb in (0, 16, 32, 48, 64):
            f.line(X0 + mb * px, y + 22, X0 + mb * px, y + 26, "m")
            f.text(X0 + mb * px, y + 37, f"{mb} MB", "ta" if mb == 64 else "tm", 9, "middle",
                   700 if mb == 64 else None)
    y = 102
    f.text(24, y - 8, GROW, "t", 10.5, weight=700, mono=True)
    f.rect(X0, y, W, 20, "s f", 2)
    f.bar(X0 + 1, y + 1, W - 2, 18, "af", 1)
    f.text(X0 + 8, y + 14, "a table, and tables, block after block", "ta", 10, weight=600)
    f.line(X0 + W, y - 6, X0 + W, y + 26, "a")
    f.rect(X0 + W + 4, y, 26, 20, "a", 2, dash=True)
    f.text(X0 + W + 36, y + 9, "one more block:", "ta", 10, weight=700)
    f.text(X0 + W + 36, y + 22, "NULL, refused", "ta", 10, weight=700)
    axis(y)
    f.text(24, y + 58, "Lua raises \"not enough memory\"; the error reaches the protected call; at the outermost "
           "return, a full collection:", "t", 10.5)
    f.rect(X0, y + 68, W, 16, "m f", 2)
    f.bar(X0 + 1, y + 69, 2, 14, "fa", 0)
    f.text(X0 + 10, y + 80, f"{r8['grow_after']:.1f} KB held after: collectgarbage('count')", "ta", 10, weight=700)
    y = 240
    f.text(24, y - 8, BIG + ": one block of 100 MB", "t", 10.5, weight=700, mono=True)
    f.rect(X0, y, 560, 18, "s f", 2)
    f.bar(X0 + 1, y + 1, 558, 16, "fs", 1)
    f.path(f"M{X0 + 470} {y - 3} l6 12 l-6 12", "m")
    f.path(f"M{X0 + 478} {y - 3} l6 12 l-6 12", "m")
    f.line(X0 + W, y - 6, X0 + W, y + 24, "a")
    f.text(X0 + 8, y + 13, "09.07, no limit: #string.rep('x', 200 * 2^20) gave 209715200; Lua held 212642 KB after",
           "t", 9.5)
    y2 = y + 30
    f.rect(X0, y2, W, 18, "m f", 2)
    f.text(X0 + 10, y2 + 13, f"09.08: refused at once, \"not enough memory\"; {r8['big_after']:.1f} KB held after",
           "ta", 9.5, weight=700)
    f.text(24, 324, "At 09.08 Lua's state is made by lua_newstate(scriptAlloc, NULL); at 09.07 by luaL_newstate(), "
           "with no limit of kilo's.", "tm", 10)
    return f


def trust0908():
    said("`lua_State *lstate = luaL_newstate();` and `luaL_openlibs(lstate);` in nlua_init",
         "executor.c has no lua_sethook", "if you write an endless loop inside `:lua` then it can't be interrupted",
         "To ensure that extensions cannot interfere with the stability and performance of VS Code",
         "The Extension Host in VS Code prevents extensions from: Impacting startup performance / Slowing down UI "
         "operations / Modifying the UI",
         "we run extensions in an [Extension Host](/api/advanced-topics/extension-host) process and prevent direct "
         "access to the DOM.",
         "an extension can read and write files on your machine, make network requests, run external processes",
         "There can be several hosts (local, remote, web)", "another process (the extension host)",
         "the host runs the module with wasmtime in Zed's process",
         "`ctx.preopened_dir(&path, \".\", dir_perms, file_perms)?;`",
         "governed by a capability system",
         "Capabilities (`process:exec`, `download_file`, `npm:install`)",
         "Procedural parts of extensions are written in Rust and compiled to WebAssembly.",
         "Redis (not an editor) | Lua 5.1 | in the server's process",
         "a script has the user's whole trust")
    f = F9("f09-08c", "Where extension code runs in Neovim, VS Code and Zed, what stops a loop that never ends, and "
           "what it may reach, as their sources and docs say", 340)
    f.text(24, 22, "from each project's source and documentation, at the versions named; not run here", "tm", 11)
    cols = [24, 230, 436]
    W = 180
    heads = ["Neovim", "VS Code", "Zed"]
    subs = ["v0.12.6", "vscode-docs", "v0.233.10"]
    for x, h_, s_ in zip(cols, heads, subs):
        f.text(x, 52, h_, "t", 13, weight=700)
        f.text(x + figlib.tw(h_, 13) * 1.12 + 8, 52, s_, "tm", 9.5)
    # the diagrams
    dy = 62
    x = cols[0]
    f.rect(x, dy, W, 70, "s fs", 6)
    f.text(x + 8, dy + 15, "nvim: one process", "t", 10, weight=600)
    f.rect(x + 10, dy + 24, 72, 36, "s f", 4)
    f.text(x + 46, dy + 46, "the editor", "t", 9.5, "middle")
    f.rect(x + 92, dy + 24, 78, 36, "a af", 4)
    f.text(x + 131, dy + 40, "Lua: one", "ta", 9.5, "middle", 700)
    f.text(x + 131, dy + 52, "lua_State", "ta", 9.5, "middle", 700, mono=True)
    x = cols[1]
    f.rect(x, dy, 76, 70, "s fs", 6)
    f.text(x + 38, dy + 30, "VS Code:", "t", 9.5, "middle", 600)
    f.text(x + 38, dy + 43, "the window", "t", 9.5, "middle")
    f.rect(x + 100, dy, 80, 70, "a af", 6)
    f.text(x + 140, dy + 24, "Extension", "ta", 9.5, "middle", 700)
    f.text(x + 140, dy + 37, "Host: a", "ta", 9.5, "middle", 700)
    f.text(x + 140, dy + 50, "process", "ta", 9.5, "middle", 700)
    f.line(x + 78, dy + 35, x + 98, dy + 35, "m", dash=True)
    x = cols[2]
    f.rect(x, dy, 120, 70, "s fs", 6)
    f.text(x + 8, dy + 15, "Zed: one process", "t", 10, weight=600)
    f.rect(x + 10, dy + 22, 100, 40, "s f", 4)
    f.text(x + 16, dy + 34, "wasmtime", "tm", 9, mono=True)
    f.rect(x + 18, dy + 38, 84, 18, "a af", 3)
    f.text(x + 60, dy + 51, "extension.wasm", "ta", 8.5, "middle", 700, mono=True)
    f.path(f"M{x + 132} {dy + 22} l0 -6 l14 0 l4 5 l26 0 l0 30 l-44 0 z", "s")
    f.text(x + 154, dy + 62, "its work dir", "t", 9, "middle")
    f.line(x + 102, dy + 47, x + 130, dy + 40, "a", arrow=True)
    # the rows
    rows_ = [
        ("where it runs", [
            "In Nvim's process: nlua_init() makes one lua_State (executor.c).",
            "\"in an Extension Host process\", with no direct access to the DOM; local, remote, or web.",
            "Rust compiled to WebAssembly, run by wasmtime inside Zed's process (wasm_host.rs)."]),
        ("a loop that never ends", [
            "No count hook: its Lua glue calls no lua_sethook. Issue #6800, open: \"if you write an endless loop "
            "inside :lua then it can't be interrupted\".",
            "Run there \"To ensure that extensions cannot interfere with the stability and performance of VS "
            "Code\".",
            "Not in what was read."]),
        ("what it may reach", [
            "luaL_openlibs(): Lua's libraries, io and os among them.",
            "\"the same permissions as\" VS Code: \"read and write files ..., make network requests, run "
            "external processes\".",
            "Files: its own work dir only (preopened_dir). Operations go by capabilities: process:exec, "
            "download_file, npm:install."]),
    ]
    yy = 156
    for title, texts in rows_:
        bottoms = []
        for x, t_ in zip(cols, texts):
            f.text(x, yy, title, "tm", 9.5, weight=600)
            bottoms.append(notes(f, x, yy + 15, t_, 33, "t", 10, 13))
        yy = max(bottoms) + 12
    f.line(24, yy - 4, 616, yy - 4, "m")
    end = notes(f, 24, yy + 12, "kilo (this module): in the editor's process, as Neovim, with a script trusted as "
                "the user; two guards of its own: the count hook (Redis sets the same kind) and the 64 MB allocator.",
                112, "t", 10.5, 14)
    f.h = int(end + 6)
    return f


# ---------------------------------------------------------------- 09.09

MAIN_LINES = [  # (shown, what main() at 09.09 must hold, in this order)
    ("if (... --api-info ...) return apiInfo();", 'strcmp(argv[1],"--api-info") == 0) return apiInfo();'),
    ("if (... -l ...)", 'strcmp(argv[1],"-l") == 0)'),
    ("    return editorRunScript(...);", "return editorRunScript(argv[2],"),
    ("enableRawMode(STDIN_FILENO);", "enableRawMode(STDIN_FILENO);"),
    ("initEditor();", "initEditor();"),
    ("editorOpen(argv[1]);", "editorOpen(argv[1]);"),
    ("editorSetStatusMessage(\"HELP: ...\");", "editorSetStatusMessage("),
    ("scriptStart();", "scriptStart();"),
    ("editorEvent(\"BufReadPost\");", 'editorEvent("BufReadPost");'),
    ("while(1) {", "while(1) {"),
    ("    editorAfterKey();", "editorAfterKey();"),
    ("    editorRefreshScreen();", "editorRefreshScreen();"),
    ("    editorProcessKeypress(STDIN_FILENO);", "editorProcessKeypress(STDIN_FILENO);"),
    ("}", "}"),
]
RUN_LINES = ["editorScreen = 0;", "E.screenrows = 22;", "E.screencols = 80;", "if (filename) editorOpen(filename);",
             "return scriptRun(script) == 0 ? 0 : 1;"]


def body(src, head):
    """The body of the C function whose definition starts with head, comments and @ lines out."""
    at = src.index(head)
    depth, i = 0, src.index("{", at)
    start = i
    while True:
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                break
        i += 1
    text = re.sub(r"/\*.*?\*/", "", src[start:i + 1], flags=re.S)
    return "\n".join(line.split("//")[0].rstrip() for line in text.split("\n"))


def two_doors0909():
    cap = capture0909()
    cli, shot = cap["cli"], cap["shot"]
    assert (cli["rc"], cli["stdout"], cli["stderr"]) == (0, "2 lines upper-cased\n", ""), cli
    assert cli["file"] == "HELLO\nWORLD\n123\n" and shot.lines[:3] == ["hello", "World", "123"]
    lesson_said("09", "2 lines upper-cased $ cat build/at/kilo/09.09/notes.txt HELLO WORLD 123",
                "This comes before `enableRawMode()`")
    src = source("09.09", "kilo.c")
    m = body(src, "int main(int argc, char **argv) {")
    at = 0
    for shown, need in MAIN_LINES:
        k = m.find(need, at)
        assert k >= 0, need
        at = k + len(need)
    r = body(src, "int editorRunScript(char *script, char *filename) {")
    at = 0
    for need in RUN_LINES:
        k = r.find(need, at)
        assert k >= 0, need
        at = k + len(need)
    assert "if (scriptNew() == -1) return -1;" in body(source("09.09", "script.c"), "int scriptRun(const char *path) {")
    f = F9("f09-09a", "Two ways into the same API: the keyboard and the screen, or kilo -l with a script; main() "
           "takes the second before any of the screen's work", 358)
    f.text(24, 22, "kilo at 09.09 on notes.txt (hello / World / 123), each way; upper.lua as the lesson makes it",
           "tm", 11)
    lx = 24
    f.text(lx, 52, "the keyboard and the screen", "t", 11, weight=700)
    mono(f, lx, 70, "$ ./kilo notes.txt", "t", 9.5)
    f.text(lx, 92, "raw mode, the window, init.lua,", "tm", 10)
    f.text(lx, 105, "the loop: a frame, a key", "tm", 10)
    f.text(lx, 128, "the screen:", "tm", 10)
    screen(f, lx + 6, 136, shot, 5.6, 14, 21, rows=[0, 1, 2, 6], status=True)
    mx = 186
    f.text(mx, 52, "main() at 09.09", "tm", 10)
    shown = ["int main(int argc, char **argv) {"] + ["    " + s_ for s_, _ in MAIN_LINES]
    bottom, bases = code(f, mx, 58, shown, size=8.2, lh=12.2, mark=(2, 3), w=226)
    a, b = bases[4] - 9, bases[-1] + 3
    f.path(f"M{mx + 230} {fmt(a)} L{mx + 236} {fmt(a)} L{mx + 236} {fmt(b)} L{mx + 230} {fmt(b)}", "a")
    rx = 430
    f.text(rx, 52, "no screen", "t", 11, weight=700)
    mono(f, rx, 70, "$ ./kilo -l upper.lua notes.txt", "t", 8.6)
    f.text(rx, 90, "editorRunScript():", "tm", 10)
    code(f, rx, 96, RUN_LINES, size=7.6, w=186)
    notes(f, rx, 192, "kilo -l skips every line the bracket holds: raw mode, the window's size, the HELP line, "
          "init.lua and its count hook, BufReadPost, and the key loop with the screen.", 34, "ta", 10, 13,
          weight=600)
    api = subprocess.run([os.path.join(project("09.09"), "kilo"), "--api-info"], check=True,
                         capture_output=True, text=True).stdout.splitlines()
    lesson_said("09", f"And the API is {len(api)} functions")
    by = 290
    f.rect(150, by, 340, 24, "a af", 6)
    f.text(320, by + 16, f"kilo.api: the same {len(api)} functions, the same rows", "ta", 11, "middle", 700)
    f.line(172, 214, 172, by - 3, "s", arrow=True)
    f.line(468, 280, 468, by - 3, "s", arrow=True)
    f.line(mx + 228, bases[2] - 3, rx - 3, bases[2] - 3, "a", arrow=True)
    f.text(24, 334, "The editor showed notes.txt as it is. Under -l, upper.lua changed two rows and saved them, "
           "HELLO / WORLD / 123;", "t", 10.5)
    f.text(24, 348, f"\"{cli['stdout'].strip()}\" went to standard output, and kilo's status was {cli['rc']}.",
           "t", 10.5)
    return f


def ui_client0909():
    said("Nvim has a client-server architecture: by default when you run `nvim`, this starts the builtin UI client, "
         "which starts a `nvim --embed` server (child) process that the UI client connects to.",
         "The |TUI| is changed to run in a separate process (previously, a separate thread was used).",
         "all UIs, including the builtin |TUI| are just plugins that connect to a Nvim server (via |--server| or "
         "|--embed|).",
         "Use stdin/stdout as a msgpack-RPC channel, so applications can embed and control Nvim via the RPC |API|.",
         "Buffer, Window, Tabpage", "Nvim exposes a powerful API that can be used by plugins and external processes via |RPC|, |Lua| and "
         "Vimscript",
         "`--headless`: \"Start without UI\"",
         "kilo's screen is in its own process; only the API is shared by the editor and -l.",
         "Print msgpack-encoded |api-metadata| and exit")
    f = F9("f09-09b", "Neovim as a server: the terminal UI is one client of the API, in a process of its own, and "
           "other programs are clients the same way; kilo keeps its screen inside", 340)
    f.text(24, 22, "Neovim v0.12.6, from its documentation; not run here", "tm", 11)
    # the client you run
    f.rect(24, 44, 178, 60, "s f", 6)
    mono(f, 34, 62, "$ nvim", "t", 10.5, weight=700)
    f.text(34, 78, "the builtin UI client (the TUI)", "t", 10)
    f.text(34, 92, "draws the terminal", "tm", 10)
    f.rect(230, 44, 178, 60, "s f", 6)
    f.text(240, 62, "other programs", "t", 10.5, weight=700)
    f.text(240, 78, "embedders, other UIs", "t", 10)
    f.text(240, 92, "via --embed or --server", "tm", 10)
    # the server
    sy = 150
    f.rect(24, sy, 384, 128, "a af", 8)
    mono(f, 36, sy + 18, "nvim --embed", "ta", 10.5, weight=700)
    f.text(36 + 12 * 6.3 + 10, sy + 18, "the server: a child process", "ta", 10.5, weight=600)
    f.rect(36, sy + 30, 360, 34, "s f", 5)
    f.text(46, sy + 45, "the API: C functions in src/nvim/api/*.h, one generated table", "t", 10, weight=600)
    f.text(46, sy + 58, "Buffer and Window are among its types", "tm", 9.5)
    for k, (label, sub) in enumerate((("RPC", "msgpack"), ("Lua", "vim.api"), ("Vimscript", ""),
                                      ("--api-info", "its metadata"))):
        cx = 36 + k * 92
        f.rect(cx, sy + 76, 84, 38, "s f", 5)
        f.text(cx + 42, sy + 92, label, "t", 10, "middle", 700, mono=label.startswith("--"))
        if sub:
            f.text(cx + 42, sy + 106, sub, "tm", 9, "middle", mono=sub == "vim.api")
    # the channels
    for x in (113, 319):
        f.line(x, 106, x, sy - 2, "a", arrow=True, start=True)
    f.text(121, 124, "msgpack-RPC on", "ta", 9.5, weight=600)
    f.text(121, 136, "stdin/stdout", "ta", 9.5, weight=600)
    f.text(327, 130, "msgpack-RPC", "ta", 9.5, weight=600)
    f.text(24, 312, "\"all UIs, including the builtin TUI are just plugins that connect to a Nvim server\" "
           "(vim_diff.txt); the TUI", "tm", 10)
    f.text(24, 326, "became a process of its own in 0.9 (news-0.9.txt). --headless starts Nvim without a UI.",
           "tm", 10)
    # kilo, for contrast
    kx = 434
    f.line(kx - 10, 44, kx - 10, 280, "m", dash=True)
    f.text(kx, 58, "kilo", "t", 12, weight=700)
    f.rect(kx, 68, 182, 100, "s fs", 6)
    mono(f, kx + 10, 86, "$ ./kilo notes.txt", "t", 9.5)
    f.text(kx + 10, 100, "one process", "tm", 9.5)
    f.rect(kx + 10, 108, 162, 22, "s f", 4)
    f.text(kx + 18, 123, "the screen: editorRefreshScreen", "t", 9)
    f.rect(kx + 10, 136, 162, 22, "a af", 4)
    f.text(kx + 18, 151, "kilo.api", "ta", 9.5, weight=700, mono=True)
    f.rect(kx, 184, 182, 60, "s fs", 6)
    mono(f, kx + 10, 202, "$ ./kilo -l upper.lua notes.txt", "t", 8.6)
    f.rect(kx + 10, 212, 162, 22, "a af", 4)
    f.text(kx + 18, 227, "kilo.api, no screen", "ta", 9.5, weight=700)
    notes(f, kx, 262, "The screen is drawn inside kilo; only the API is shared by the editor and -l.", 34, "t", 10, 13)
    return f


# ---------------------------------------------------------------- 09.10

def could_have_been0910():
    check_plugins()
    said("module 06 adds 411 lines to kilo.c (261 of code, the rest notes); colour.lua has 106 that are not blank "
         "(94 of code). vi.lua 74 lines of code, find.lua 78.",
         "vi.lua against vi's modes: h j k l, 0 and $, i a o, x, dd, Escape back to normal",
         "the mode in the status bar",
         "colour.lua against module 06: the same classes and colours for C", "Lua besides",
         "find.lua against the core's Ctrl-F: as you type from the top", "On Ctrl-N, as Ctrl-F is the core's.",
         "Escape to put back the cursor and the view (with set_view)", "Go to a line: Ctrl-O, input(), set_cursor.")
    kc = open(os.path.join(KILO, "kilo.c")).read()
    for fn in ("void editorFind(int fd) {", "void editorUpdateSyntax(erow *row) {", "struct editorSyntax HLDB[] = {"):
        assert fn in kc, fn
    api = re.findall(r'^\s*\{"(\w+)", \{', kc, re.M)
    for name, calls in PLUGIN_CALLS.items():
        for c_ in calls:
            assert c_ in api, (name, c_)
    f = F9("f09-10a", "Three features as scripts: what each is or would be in C, the plugin that does it in Lua, and "
           "the API functions the plugin calls", 330)
    f.text(24, 22, "the three plugins of 09.10, each only Lua, each standing in for C", "tm", 11)
    cols = [24, 230, 436]
    W = 180
    heads = [("vi's keys", "vi.lua"), ("colour for C and Lua", "colour.lua"), ("find, and go to a line", "find.lua")]
    in_c = [("none in the track:", "kilo's keys have no modes"),
            ("module 06: editorUpdateSyntax(),", "HLDB: 411 lines of kilo.c, 261 code"),
            ("module 05: editorFind(), Ctrl-F,", "in kilo.c")]
    code_lines = {"vi.lua": 74, "colour.lua": 94, "find.lua": 78}
    how = ["A KeyPress function: h j k l, 0 and $, i a o, x, dd, Escape back to normal; the mode in the status bar.",
           "A namespace of its own: highlights over the rows on the screen, again on BufReadPost, TextChanged and "
           "CursorMoved; C, and Lua besides.",
           "Ctrl-N: find as you type, a KeyPress layer; next and previous; Escape puts back the cursor and the view "
           "(set_view). Ctrl-O: go to a line, with input()."]
    ends = []
    for k, x in enumerate(cols):
        name, plugin = heads[k]
        f.text(x, 50, name, "t", 12, weight=700)
        f.text(x, 68, "in C", "tm", 9.5, weight=600)
        f.rect(x, 74, W, 38, "s fs", 5)
        f.text(x + 8, 89, in_c[k][0], "t", 10)
        f.text(x + 8, 103, in_c[k][1], "tm", 10)
        f.line(x + W / 2, 114, x + W / 2, 128, "a", arrow=True)
        f.text(x, 142, "as a script", "tm", 9.5, weight=600)
        f.rect(x, 148, W, 22, "a af", 5)
        mono(f, x + 8, 163, "plugins/" + plugin, "ta", 9.5, weight=700)
        f.text(x, 186, f"{PLUGIN_LINES[plugin]} lines, {code_lines[plugin]} of code", "ta", 10, weight=600)
        ends.append(notes(f, x, 204, how[k], 33, "t", 10, 13))
    top = max(ends) + 10
    bottom = top
    for k, x in enumerate(cols):
        plugin = heads[k][1]
        f.text(x, top, "the API it calls", "tm", 9.5, weight=600)
        names = PLUGIN_CALLS[plugin] + [f"event {e}" for e in PLUGIN_EVENTS[plugin]]
        cx, cy = x, top + 8
        for nm in names:
            w_ = len(nm) * cwid(8.5) + 10
            if cx + w_ > x + W:
                cx, cy = x, cy + 17
            f.rect(cx, cy, w_, 14, "m f", 3)
            f.text(cx + 5, cy + 10.5, nm, "t", 8.5, mono=True)
            cx += w_ + 4
        bottom = max(bottom, cy + 14)
    f.h = int(bottom + 12)
    return f


def frontier0910():
    said("Wait for time to pass, or work in the background: no timers (the frontier: one loop would have to own all "
         "the waiting, 07's poll() included, as libuv does for Neovim).",
         "More than one file at a time, windows, floating windows, menus: E is one file and the screen is the core's.",
         "or highlights that move with the text (Neovim's extmarks, marktree.c).",
         "highlights that do not move when the text does (Neovim's extmarks do)",
         "(and Buffer, Window, Tabpage)", "nvim_win_set_cursor", "Platform and I/O facilities are built upon libuv.",
         "`vim.uv` exposes the \"luv\" Lua bindings for the libUV library",
         "Tree data structure for storing marks at (row, col) positions and updating them to arbitrary text changes.",
         "Marks are moved by calls to extmark_splice.")
    f = F9("f09-10b", "Four things a script cannot do in kilo, the piece of an editor each would need, and that piece "
           "in Neovim", 318)
    f.text(24, 22, "what kilo leaves out on purpose, and Neovim's name for each piece, from its source and "
           "documentation", "tm", 11)
    X = [24, 196, 406]
    WS = [164, 202, 210]
    heads = ["a script cannot", "it would need", "in Neovim"]
    for x, h_ in zip(X, heads):
        f.text(x, 50, h_, "tm", 10, weight=600)
    rows_ = [
        ("wait for time to pass, or work in the background",
         "one loop that owns all the waiting, 07's poll() included: kilo has no timers",
         "libuv: \"Platform and I/O facilities are built upon libuv\"; vim.uv gives Lua its bindings"),
        ("edit more than one file at a time",
         "many buffers: kilo's E is one file",
         "Buffer, a type of the API (kObjectTypeBuffer); the nvim_buf_* functions take one"),
        ("keep highlights that move with the text",
         "marks in a tree, moved by every edit: kilo keeps a list, put again on TextChanged",
         "extmarks, in a MarkTree (marktree.c), moved by extmark_splice"),
        ("show windows, floating windows, menus",
         "windows over the text: kilo's screen is the core's, one file",
         "Window, a type of the API (kObjectTypeWindow): nvim_win_set_cursor"),
    ]
    y = 60
    for k, cells in enumerate(rows_):
        h = 58
        for j, (x, w_, t_) in enumerate(zip(X, WS, cells)):
            cls = "a af" if j == 1 else ("s fs" if j == 0 else "s f")
            f.rect(x, y, w_, h - 6, cls, 5)
            notes(f, x + 8, y + 16, t_, int((w_ - 16) / 5.3), "ta" if j == 1 else "t", 10, 13,
                  weight=600 if j == 1 else None)
        y += h
    f.text(24, y + 14, "Each is a different editor, not a missing function: a loop, a list of buffers, a tree of "
           "marks, a list of windows.", "t", 10.5)
    return f


def cleanup():
    for d in {os.path.dirname(p) for p in _built.values()}:
        shutil.rmtree(d, ignore_errors=True)
    _built.clear()


FIGS = [
    ("09.06-drawn-over", drawn_over0906, False),
    ("09.06-namespaces", namespaces0906, False),
    ("09.06-moves-or-not", moves0906, False),
    ("09.07-nested-loop", nested_loop0907, False),
    ("09.07-quit-mark", quit_mark0907, True),
    ("09.08-hook", hook0908, False),
    ("09.08-allocator", allocator0908, False),
    ("09.08-trust", trust0908, False),
    ("09.09-two-doors", two_doors0909, False),
    ("09.09-ui-client", ui_client0909, False),
    ("09.10-could-have-been", could_have_been0910, False),
    ("09.10-frontier", frontier0910, False),
]


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
