"""Figures for kilo module 09, An API, and Lua on top of it (lessons 09.06 to 09.10), an extension.

    python3 -B art/kilo/figs09b.py [name-prefix ...]
                                       writes tracks/kilo/lessons/09-api-and-lua/figures/09.LL-*.svg

(09.01 to 09.05, the maps, the cover and the icon are figs09a.py's, archmap.py's and covers.py's.)

Every script, screen, byte and message here is from a real run, or from NOTES.md (module 09)
where a figure shows what another editor does or a number measured once; each is checked against
NOTES.md's words here. The project at each lesson is written with ./learn files kilo --at 09.LL,
given Lua (track.py's supply_lua) and built with make; ./kilo runs on a pseudo-terminal through the
track's own fixture (edit() in tracks/kilo/track.py). The init.lua files are the tests' own where
NOTES.md names them (NUMBERS of 0906, GOTO of 0907, INIT of 0908, UPPER of 0909), read from the
test files here.

  09.06-drawn-over      kilo at 09.06 with NUMBERS on NOTES.md's three rows: the bytes it wrote for
                        row 0 (ed.raw), and the row before and after the second pass
  09.06-namespaces      kilo at 09.06 with two scripts, each with its own namespace (numbers in
                        yellow, trailing spaces in reverse): the screen, then clear_namespace() of
                        one at the prompt
  09.06-moves-or-not    kilo at 09.06: a highlight on a word, Enter at the top; again with a
                        TextChanged function that puts it back. Neovim's side from NOTES.md
                        (extmarks: extmark.c, marktree.c), not run
  09.07-nested-loop     kilo at 09.07 with GOTO, a scratch copy whose editorPrompt() writes its
                        backtrace (execinfo) into $KILO_TRACE: the C stack while input() waits
  09.07-quit-mark       stepped: kilo at 09.07, a scratch copy that writes a line at the quit mark,
                        at each return to the editor, before exit() and at scriptStop(); a mapped
                        key that calls quit(true) and then writes a file
  09.08-hook            kilo at 09.08 with INIT: Ctrl-T, keys typed while it runs, Ctrl-C; the
                        count from script.h, the time per look from NOTES.md
  09.08-allocator       NOTES.md's numbers (09.08's table), with runs at 09.08 that give the same
                        messages, and the allocator's refusal from script.c at 09.08
  09.08-trust           Neovim, VS Code, Zed: NOTES.md's confirmed facts only, not run
  09.09-two-doors       kilo at 09.09: UPPER with kilo -l, and the same file through a key in the
                        editor; main() and editorRunScript() as the project has them
  09.09-ui-client       Neovim's client and server, from NOTES.md's quotes, not run
  09.10-could-have-been the three plugins of 09.10 and the API functions each calls: PLUGIN_CALLS
                        below, TO BE CHECKED AGAINST THE PLUGINS when they land
  09.10-frontier        NOTES.md's frontier and the Neovim name for each piece

The maps, the cover and the icon are not made here (archmap.py, covers.py).
"""
import contextlib
import functools
import importlib.util
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

# ---------------------------------------------------------------- 09.10: TO BE CHECKED
#
# The three plugins of 09.10 (tracks/kilo/plugins/vi.lua, colour.lua, find.lua) are being written;
# they were not on master when this was drawn. Each plugin's list is the API functions and events
# NOTES.md's "For 09.10: does the API reach the three proofs" says it needs. TO BE CHECKED AGAINST
# THE PLUGINS when they land: every name here must be one the plugin calls, and every kilo.api
# function the plugin calls must be here. check_plugins() does that once the files are there.
PLUGIN_CALLS = {
    "vi.lua": ["create_autocmd", "feed_key", "set_cursor", "get_cursor", "get_lines", "set_lines",
               "set_statusline"],
    "colour.lua": ["get_name", "create_namespace", "clear_namespace", "add_highlight", "get_view", "get_size",
                   "get_lines", "create_autocmd"],
    "find.lua": ["input", "set_cursor", "get_lines", "line_count", "create_namespace",
                 "add_highlight", "clear_namespace", "message"],
}
PLUGIN_EVENTS = {
    "vi.lua": ["KeyPress"],
    "colour.lua": ["BufReadPost", "TextChanged", "CursorMoved"],
    "find.lua": [],
}


def check_plugins():
    """When tracks/kilo/plugins/ is there: PLUGIN_CALLS against what each plugin calls."""
    d = os.path.join(KILO, "plugins")
    if not os.path.isdir(d):
        print("figs09b: tracks/kilo/plugins/ is not there yet: PLUGIN_CALLS is unchecked")
        return False
    for name, calls in PLUGIN_CALLS.items():
        with open(os.path.join(d, name)) as f:
            src = f.read()
        used = sorted(set(re.findall(r"kilo\.api\.(\w+)", src)))
        assert sorted(calls) == used, (name, sorted(calls), used)
        for ev in PLUGIN_EVENTS[name]:
            assert f"'{ev}'" in src or f'"{ev}"' in src, (name, ev)
    return True


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


def test_const(test, name):
    """A constant of one of the track's tests (an init.lua NOTES.md names by it)."""
    path = os.path.join(KILO, "tests", test)
    spec = importlib.util.spec_from_file_location("t_" + name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, name)


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

NUM_TEXT = "int width = 640;\nint height = 480;\nprint(width * height * 3);\n"


@functools.cache
def capture0906():
    """kilo at 09.06 with NUMBERS (0906) on NOTES.md's three rows, a terminal 8 x 60: the screen
    and every byte kilo wrote."""
    numbers = test_const("0906_drawing_from_a_script_highlights_and_the_status_bar.py", "NUMBERS")
    with scratch("09.06") as (t, tr):
        ed = tr.edit(t, NUM_TEXT, rows=8, cols=60, init=numbers)
        shot = Shot(ed)
        painted = [ed.painted(r) for r in range(3)]
        raw = bytes(ed.raw)
        ed.quit()
    return {"shot": shot, "painted": painted, "raw": raw, "init": numbers}


# Two scripts, each with a namespace of its own: numbers in yellow (09.06's Run it), and spaces at
# the end of a row in reverse.
NS_NUMBERS = """local nums = kilo.api.create_namespace('numbers')
local function paint()
  kilo.api.clear_namespace(nums)
  for row, line in kilo.lines() do
    for s, e in line:gmatch('()%d+()') do
      kilo.api.add_highlight(nums, row, s - 1, e - 1, 'yellow')
    end
  end
end
kilo.api.create_autocmd('BufReadPost', paint)
kilo.api.create_autocmd('TextChanged', paint)
"""
NS_TRAILING = """local trail = kilo.api.create_namespace('trailing')
local function paint()
  kilo.api.clear_namespace(trail)
  for row, line in kilo.lines() do
    local s = line:find('%s+$')
    if s then kilo.api.add_highlight(trail, row, s - 1, #line, 'reverse') end
  end
end
kilo.api.create_autocmd('BufReadPost', paint)
kilo.api.create_autocmd('TextChanged', paint)
"""
NS_TEXT = "width = 640   \nheight = 480\narea = width * height  \nlimit = 64 \n"
NS_CLEAR = "kilo.api.clear_namespace(kilo.api.create_namespace('numbers'))"


@functools.cache
def capture0906ns():
    """kilo at 09.06 with NS_NUMBERS and NS_TRAILING as its init.lua, a terminal 8 x 40: the screen
    (BufReadPost drew both); the two namespaces' ids; then NS_CLEAR at the prompt, the screen."""
    with scratch("09.06") as (t, tr):
        ed = tr.edit(t, NS_TEXT, rows=8, cols=40, init=NS_NUMBERS + NS_TRAILING)
        both = Shot(ed)
        ed.keys(ctrl("e"), "print(kilo.api.create_namespace('numbers'), kilo.api.create_namespace('trailing'))",
                ENTER)
        ids = ed.message
        ed.keys(ctrl("e"), NS_CLEAR, ENTER)
        cleared = Shot(ed)
        leave(ed)
    return {"both": both, "ids": ids, "cleared": cleared}


MV_TEXT = "first line\nthe word here\nlast line\n"
MV_PUT = "kilo.api.add_highlight(ns, 1, 4, 8, 'reverse')"
MV_AGAIN = """kilo.api.create_autocmd('TextChanged', function()
  kilo.api.clear_namespace(ns)
  for row, line in kilo.lines() do
    local s, e = line:find('word', 1, true)
    if s then kilo.api.add_highlight(ns, row, s - 1, e, 'reverse') end
  end
end)
"""


@functools.cache
def capture0906moves():
    """kilo at 09.06 on MV_TEXT, a terminal 7 x 30: the highlight put on "word" (row 1, bytes 4 to
    8), then Enter at the top of the file; once with nothing else, once with MV_AGAIN."""
    out = {}
    with scratch("09.06") as (t, tr):
        for name, extra in (("once", ""), ("again", MV_AGAIN)):
            init = "ns = kilo.api.create_namespace('word')\n" + MV_PUT + "\n" + extra
            ed = tr.edit(t, MV_TEXT, rows=7, cols=30, init=init)
            before = Shot(ed)
            ed.keys(ENTER)
            out[name] = {"before": before, "after": Shot(ed), "init": init}
            leave(ed)
    return out


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
    """kilo at 09.07 with GOTO (0907) on 40 numbered lines, a terminal 8 x 60, editorPrompt() writing
    its backtrace: Ctrl-O, "30"; the C stack, the screen at the prompt; Enter and where it went."""
    goto = test_const("0907_asking_opening_leaving_input_open_quit.py", "GOTO")
    with scratch("09.07", BT_PATCH) as (t, tr):
        trace = os.path.join(t.tmp, "trace")
        env = dict(os.environ, KILO_TRACE=trace, KILO_LSP="")
        ipath = os.path.join(t.tmp, "init.lua")
        with open(ipath, "w") as f:
            f.write(goto)
        env["KILO_INIT"] = ipath
        ed = tr.edit(t, tr.lines_of(40), rows=8, cols=60, init="env", env=env)
        ed.keys(ctrl("o"), "30")
        prompt = Shot(ed)
        frames = bt_frames(read_lines(trace))
        ed.keys(ENTER)
        after = Shot(ed)
        ed.quit()
    return {"goto": goto, "frames": frames, "prompt": prompt, "after": after}


QUIT_PATCH = [
    ("kilo.c", "    editorQuit = 1;\n", "    editorQuit = 1;\n" + tracer("quit(true): editorQuit = 1") + "\n"),
    ("kilo.c", "    if (editorQuit) exit(0);\n",
     "    if (editorQuit) {" + tracer("editorAfterKey: editorQuit is set: exit(0)") + " }\n"
     "    if (editorQuit) exit(0);\n"),
    ("script.c", "    S.depth--;\n",
     "    S.depth--;\n" + tracer("scriptProtected: lua_pcall returned, depth %d, after.txt %s", "S.depth",
                                 'access("after.txt",F_OK) == 0 ? "there" : "not there"') + "\n"),
    ("script.c", "    if (S.L && S.depth == 0) lua_close(S.L);\n",
     tracer("scriptStop: raw mode off; lua_close: %s", 'S.L && S.depth == 0 ? "yes" : "no"') + "\n"
     "    if (S.L && S.depth == 0) lua_close(S.L);\n"),
]
QUIT_INIT = """kilo.api.set_keymap('<C-x>', function()
  kilo.api.quit(true)
  io.open('after.txt', 'w'):write('ran'):close()
end)
"""


@functools.cache
def capture0907quit():
    """kilo at 09.07 patched with QUIT_PATCH, QUIT_INIT as init.lua, a change typed and not saved,
    then Ctrl-X: the trace, the exit status, after.txt, the file, the terminal's mode after."""
    with scratch("09.07", QUIT_PATCH) as (t, tr):
        trace = os.path.join(t.tmp, "trace")
        ipath = os.path.join(t.tmp, "init.lua")
        with open(ipath, "w") as f:
            f.write(QUIT_INIT)
        env = dict(os.environ, KILO_TRACE=trace, KILO_INIT=ipath, KILO_LSP="")
        ed = tr.edit(t, "kept text\n", rows=8, cols=40, init="env", env=env)
        ed.keys("new ")
        open(trace, "w").close()                # what came before the key: not this figure's
        typed = Shot(ed)
        ed.s.send(ctrl("x"))
        rc = ed.s.wait_exit(10)
        ed.pump(0)
        echo = bool(ed.termios()[3] & termios.ECHO)
        lines = read_lines(trace)
        with open(os.path.join(t.tmp, "after.txt")) as f:
            after = f.read()
        saved = ed.saved()
    return {"trace": lines, "rc": rc, "after": after, "saved": saved, "echo": echo, "typed": typed}


# ---------------------------------------------------------------- 09.08: captures

@functools.cache
def capture0908hook():
    """kilo at 09.08 with INIT (0908): Ctrl-T (while true do end), "abc" typed while it runs, then
    Ctrl-C: the message, row 0, the time from Ctrl-C to the frame."""
    init = test_const("0908_scripts_that_go_wrong.py", "INIT")
    with scratch("09.08") as (t, tr):
        ed = tr.edit(t, "safe text\n", rows=8, cols=60, init=init)
        ed.s.send(ctrl("t"))
        time.sleep(1.0)
        alive = ed.s.proc.poll() is None
        ed.s.send("abc")
        time.sleep(0.2)
        t0 = time.monotonic()
        ed.keys(ctrl("c"))
        took = time.monotonic() - t0
        shot = Shot(ed)
        ed.keys("ok ", ctrl("s"))
        saved = ed.saved()
        ed.quit()
    return {"init": init, "alive": alive, "took": took, "shot": shot, "saved": saved}


GROW = "local t = {} for i = 1, 1e9 do t[i] = string.rep('x', 1000) .. i end"


@functools.cache
def capture0908mem():
    """kilo at 09.08 and at 09.07 (no limit yet): GROW at 09.08, then collectgarbage('count');
    #string.rep('x', 200 * 2^20) at both. (What Lua holds after the big string, and how many
    strings the table had, change with what ran before in the session: the figure takes those
    numbers from NOTES.md, and these runs show the messages are the same.)"""
    out = {}
    for at in ("09.08", "09.07"):
        with scratch(at) as (t, tr):
            ed = tr.edit(t, "x\n", rows=8, cols=60)

            def lua(line):
                ed.keys(ctrl("e"), line, ENTER)
                return ed.message
            r = {}
            if at == "09.08":
                r["grow"] = lua(GROW)
                r["grow_after"] = float(lua("collectgarbage('count')"))
            r["big"] = lua("#string.rep('x', 200 * 2^20)")
            ed.quit()
            out[at] = r
    return out


# ---------------------------------------------------------------- 09.09: captures

@functools.cache
def capture0909():
    """kilo at 09.09: UPPER (0909) as upper.lua with kilo -l on NOTES.md's notes.txt; and the same
    file through the editor, upper.lua run by a key (dofile) mapped in init.lua, then Ctrl-Q."""
    upper = test_const("0909_the_editor_without_its_screen.py", "UPPER")
    text = "hello\nWorld\n123\n"
    out = {"upper": upper, "text": text}
    with scratch("09.09") as (t, tr):
        r = tr.run_script(t, upper, text, name="notes.txt", script="upper.lua")
        with open(os.path.join(t.tmp, "notes.txt")) as f:
            out["cli"] = {"rc": r.returncode, "stdout": r.stdout, "stderr": r.stderr, "file": f.read()}
        with open(os.path.join(t.tmp, "notes.txt"), "w") as f:
            f.write(text)
        ed = tr.edit(t, None, name="notes.txt", rows=8, cols=40,
                     init="kilo.api.set_keymap('<C-u>', function() dofile('upper.lua') end)\n")
        ed.keys(ctrl("u"))
        shot = Shot(ed)
        rc = ed.quit()
        with open(os.path.join(t.tmp, "notes.txt")) as f:
            out["key"] = {"rc": rc, "shot": shot, "file": f.read()}
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
    cell, each coloured cell in accent on the accent's soft fill. Returns {row: baseline}."""
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
    shot, raw = cap["shot"], cap["raw"]
    for k, p in enumerate(cap["painted"]):
        said("|" + p)                                     # NOTES.md's screen, row by row
    row = shot.lines[0]
    i = raw.rfind(row.encode() + b"\x1b[0K")
    assert i >= 0
    j = raw.index(b"\r\n", i + len(row)) + 2
    data = raw[i:j].decode()
    m = re.fullmatch(r"(.*)\x1b\[0K\r\x1b\[(\d+)C\x1b\[(\d+)m(\d+)\x1b\[0m\r\n", data)
    assert m and m.group(1) == row, data
    n, style, num = int(m.group(2)), m.group(3), m.group(4)
    s0 = row.index(num)
    assert n == s0 and style == "31" and '{"red","31"}' in source("09.06", "kilo.c")
    said(f"Row 0 as kilo sends it: `{row}ESC[0K \\r ESC[{n}C ESC[{style}m {num} ESC[0m`")
    assert "add_highlight(nums, top + i - 1, s - 1, e - 1, 'red')" in cap["init"]
    f = F9("f0906a", f"The bytes kilo at 09.06 writes for row 0 with a highlight on {num}: the row as always, then "
           f"back to its start, {n} cells right, red on, {num} again, colours off", 304)
    f.text(24, 22, "row 0 of the frame, from what kilo at 09.06 wrote to the terminal; NUMBERS of 0906 as init.lua",
           "tm", 11)
    size = 11.5
    x, y = 24, 58
    toks = [(row, "t", 1), ("ESC[0K", "tm", 1), ("\\r", "a", 2), (f"ESC[{n}C", "a", 2), (f"ESC[{style}m", "a", 2),
            (num, "a", 2), ("ESC[0m", "a", 2), ("\\r\\n", "tm", 3)]
    spans = {}
    for s_, cls, part in toks:
        x0 = x
        x = mono(f, x, y, s_, "ta" if cls == "a" else cls, size, weight=700 if cls == "a" else None)
        spans.setdefault(part, [x0, x])[1] = x
        x += 6
    a, b = spans[1]
    f.brace_h(a, b, y + 10)
    f.text(a, y + 28, "first pass: the row, and erase to its end", "t", 10.5)
    a, b = spans[2]
    f.brace_h(a, b, y + 10, "a")
    f.text(a, y + 44, "second pass: the highlight, over the same cells", "ta", 10.5, weight=600)
    # the call that made it
    call = f"kilo.api.add_highlight(nums, 0, {s0}, {s0 + len(num)}, 'red')"
    f.text(24, 124, "the call NUMBERS made for this row:", "tm", 10.5)
    mono(f, 24 + figlib.tw("the call NUMBERS made for this row:", 10.5) + 8, 124, call, "t", 10.5)
    # the terminal's row, before and after the second pass
    cw2, rh = 10.0, 24
    tx, ty = 40, 160
    for k in (0, 8, n, n + len(num)):
        f.text(tx + k * cw2 + cw2 / 2, ty - 8, str(k), "ta" if k in (n, n + len(num)) else "tm", 9, "middle",
               700 if k == n else None, mono=True)
    for k, (label, hot) in enumerate((("after the first pass", False), (f"after the second: {num} in red", True))):
        yy = ty + k * 60
        f.rect(tx - 6, yy, 22 * cw2 + 12, rh, "s fs", 4)
        if hot:
            f.bar(tx + n * cw2, yy + 3, len(num) * cw2, rh - 6, "af", 2)
            mono(f, tx, yy + 16.5, row[:n], "t", 16.5)
            mono(f, tx + n * cw2, yy + 16.5, num, "ta", 16.5, weight=700)
            mono(f, tx + (n + len(num)) * cw2, yy + 16.5, row[n + len(num):], "t", 16.5)
        else:
            mono(f, tx, yy + 16.5, row, "t", 16.5)
        f.text(tx + 22 * cw2 + 16, yy + 16, label, "ta" if hot else "tm", 10.5, weight=600 if hot else None)
    ay = ty + 38
    f.path(f"M{fmt(tx + 19 * cw2)} {ay} L{fmt(tx)} {ay}", "a", arrow=True)
    f.text(tx + 19 * cw2 + 6, ay + 4, "\\r", "ta", 10.5, weight=700, mono=True)
    f.path(f"M{fmt(tx)} {ay + 9} L{fmt(tx + n * cw2)} {ay + 9}", "a", arrow=True)
    f.text(tx + n * cw2 + 6, ay + 13, f"ESC[{n}C", "ta", 10.5, weight=700, mono=True)
    f.text(24, 274, f"Bytes [{s0}, {s0 + len(num)}) of the row are cells {n} to {n + len(num) - 1} here: no tab before "
           "them, and the view starts at column 0. With a tab,", "tm", 10.5)
    f.text(24, 289, "the cells are counted again: a tab goes to the next multiple of 8, and the view's left column "
           "is taken off.", "tm", 10.5)
    return f


def namespaces0906():
    cap = capture0906ns()
    both, cleared = cap["both"], cap["cleared"]
    assert cap["ids"] == "1 2", cap["ids"]
    nums = {r for r in range(4) for c in both.colors[r] if c == "y"}
    rev = [r for r in range(4) if "#" in both.colors[r]]
    assert nums == {0, 1, 3} and rev == [0, 2, 3], (nums, rev)
    for r in range(4):                                    # the clear took the yellow and only it
        assert "y" not in cleared.colors[r] and cleared.colors[r].count("#") == both.colors[r].count("#")
        assert cleared.cells[r] == both.cells[r]
    f = F9("f0906b", "Two scripts draw on the same rows, each in a namespace of its own: numbers in yellow, spaces "
           "at a row's end in reverse; clearing the first namespace leaves the second's highlights", 314)
    f.text(24, 22, "kilo at 09.06, a terminal 8 x 40; init.lua holds two scripts (the rows 0 to 3 and the bar)",
           "tm", 11)
    cw, rh = 5.4, 15
    lx, rx_, y = 30, 392, 64
    f.text(lx - 6, 50, "both drawn (BufReadPost)", "t", 11, weight=700)
    f.text(rx_ - 6, 50, "after the line at the prompt", "t", 11, weight=700)
    screen(f, lx, y, both, cw, rh, 40, rows=range(7))
    screen(f, rx_, y, cleared, cw, rh, 40, rows=range(7))
    # the line typed at the prompt, between them
    ax0, ax1, ay = lx + 40 * cw + 12, rx_ - 12, y + 2 * rh
    f.line(ax0, ay, ax1, ay, "a", arrow=True)
    f.text((ax0 + ax1) / 2, ay - 8, "clear_namespace", "ta", 10, "middle", 700, mono=True)
    f.text((ax0 + ax1) / 2, ay + 14, "of numbers (1)", "ta", 10, "middle")
    # who drew what
    ly = 200

    def swatch(x, yy, cls_bar, cls_text, label):
        f.bar(x, yy - 10, 3 * cw * 1.3, 13, cls_bar, 2)
        f.text(x + 3, yy, label, cls_text, 10, weight=700, mono=True)
    swatch(24, ly, "af", "ta", "640")
    mono(f, 56, ly, "local nums = kilo.api.create_namespace('numbers')", "t", 9.5)
    f.text(56, ly + 15, "namespace 1: every number, in yellow, on BufReadPost and TextChanged", "tm", 10)
    swatch(24, ly + 38, "t", "f", "   ")
    mono(f, 56, ly + 38, "local trail = kilo.api.create_namespace('trailing')", "t", 9.5)
    f.text(56, ly + 53, "namespace 2: the spaces at a row's end, in reverse, on the same events", "tm", 10)
    mono(f, 24, ly + 82, "lua: " + NS_CLEAR, "ta", 9.5, weight=700)
    f.text(24, ly + 98, "The same name gives the same id, 1: clear_namespace() takes that namespace's highlights, "
           "and no other.", "tm", 10.5)
    return f


def moves0906():
    cap = capture0906moves()
    once, again = cap["once"], cap["again"]
    w = "word"
    r1 = MV_TEXT.split("\n")[1]
    s0 = r1.index(w)
    assert MV_PUT == f"kilo.api.add_highlight(ns, 1, {s0}, {s0 + len(w)}, 'reverse')"
    for c in (once, again):
        assert c["before"].colors[1][s0:s0 + len(w)] == "####" and c["before"].colors[1].count("#") == 4
    assert once["after"].colors[1][s0:s0 + len(w)] == "####" and once["after"].lines[1] == "first line"
    assert "#" not in once["after"].colors[2]
    assert again["after"].colors[2][s0:s0 + len(w)] == "####" and "#" not in again["after"].colors[1]
    said("Extmarks move with the text (extmark.c:", "adjustment to text changes", "kilo's do not",
         "then marks (mark_adjust_buf, extmark_splice)", "A highlight is a row and bytes, drawn after the row; it does "
         "not move with the text. A script puts its highlights again on TextChanged")
    f = F9("f0906c", "A row put in above a highlighted word: kilo's highlight stays on its row number until a script "
           "puts it again; Neovim's extmark moves with the text", 320)
    f.text(24, 22, "kilo at 09.06, Enter at the top of the file; Neovim from its source, not run", "tm", 11)
    cw, rh = 6.0, 16
    rows = range(4)

    def mini(x, y, shot, title, sub, tcls="t"):
        f.text(x - 6, y - 26, title, tcls, 11, weight=700)
        f.text(x - 6, y - 12, sub, "tm", 10)
        screen(f, x, y, shot, cw, rh, 14, rows=rows, status=False)
    f.text(24, 52, "kilo: a highlight is a row and a range of bytes", "t", 11.5, weight=700)
    y = 96
    xs = (30, 140, 250)
    mini(xs[0], y, once["before"], "before", f"row 1, bytes {s0} to {s0 + len(w)}")
    mini(xs[1], y, once["after"], "Enter at the top", f"still row 1, {s0} to {s0 + len(w)}", "ta")
    mini(xs[2], y, again["after"], "with TextChanged", "put again: row 2")
    for x0 in xs[:2]:
        f.line(x0 + 14 * cw + 8, y + 2 * rh, x0 + 14 * cw + 18, y + 2 * rh, "m", arrow=True)
    code(f, 24, 184, MV_AGAIN.rstrip("\n").split("\n"), size=7.8, mark=(1, 4))
    # Neovim's side, drawn from what NOTES.md read
    f.line(376, 44, 376, 276, "m", dash=True)
    nx = 410
    f.text(nx - 6, 52, "Neovim: an extmark", "t", 11.5, weight=700)
    for k, (title, sub, mark_row) in enumerate((("before", "row 1, col 4", 1), ("a row put in", "moved: row 2, col 4", 2))):
        xx = nx + k * 110
        f.text(xx - 6, y - 26, title, "ta" if k else "t", 11, weight=700)
        f.text(xx - 6, y - 12, sub, "tm", 10)
        lines = MV_TEXT.split("\n")[:3]
        if k:
            lines = [""] + lines
        f.rect(xx - 6, y - 4, 14 * cw + 12, 4 * rh + 8, "s fs", 5)
        for r, line in enumerate(lines[:4]):
            b = y + r * rh + rh * 0.72
            if r == mark_row:
                f.bar(xx + s0 * cw, y + r * rh + 1.5, len(w) * cw, rh - 3, "t", 1)
                mono(f, xx, b, line[:s0], "t", cw / 0.6)
                mono(f, xx + s0 * cw, b, w, "f", cw / 0.6)
                mono(f, xx + (s0 + len(w)) * cw, b, line[s0 + len(w):], "t", cw / 0.6)
            else:
                mono(f, xx, b, line, "t", cw / 0.6)
    f.line(nx + 14 * cw + 8, y + 2 * rh, nx + 14 * cw + 18, y + 2 * rh, "m", arrow=True)
    yy = notes(f, nx - 6, 196, "nvim_buf_set_lines calls extmark_splice: the marks are adjusted in the same "
               "edit (buffer.c).", 40, "tm", 10, 13)
    notes(f, nx - 6, yy + 6, "They sit in a tree (marktree.c), with \"adjustment to text changes\" (extmark.c).",
          40, "tm", 10, 13)
    f.text(24, 300, "kilo: the script pays, again after every change. Neovim: the editor pays, once, in every edit; "
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
    assert cap["prompt"].lines[-1] == "Go to line: 30" and cap["after"].lines[-2].endswith("30/40")
    said("Ctrl-O, \"30\" shows `Go to line: 30` in the message line")
    goto = cap["goto"].split("\n")
    ln = next(k for k, s in enumerate(goto) if "kilo.api.input(" in s) + 1      # init.lua's line number
    f = F9("f0907a", "The C stack while input() waits in kilo at 09.07: main's loop, the key, the Lua function "
           "mapped to Ctrl-O, input(), and the prompt's own key loop on top", 352)
    f.text(24, 22, "kilo at 09.07 with GOTO of 0907: Ctrl-O, then 30 typed; the backtrace of editorPrompt() "
           "(a scratch build)", "tm", 11)
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
         f"init.lua, line {ln}: kilo.api.input(...)", False),
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
          f"cursor (to row 30: the bar then says {cap['after'].lines[-2].split()[-1]}); only then does main's "
          "loop read a key again.", 32, "t", 10, 13.5)
    return f


def quit_mark0907():
    cap = capture0907quit()
    tr_ = cap["trace"]
    assert tr_ == ["quit(true): editorQuit = 1", "scriptProtected: lua_pcall returned, depth 0, after.txt there",
                   "editorAfterKey: editorQuit is set: exit(0)", "scriptStop: raw mode off; lua_close: yes"], tr_
    assert cap["rc"] == 0 and cap["after"] == "ran" and cap["echo"] and cap["saved"] == "kept text\n"
    assert cap["typed"].lines[0] == "new kept text"
    said("quit(true) in a line at the prompt: the rest of the line still runs (it wrote a file), then kilo exits 0 "
         "and the terminal is put back.")
    f = F9("f0907b", "quit(true) inside a mapped function, in kilo at 09.07: the mark is set, the function returns to "
           "C, and only then does kilo close Lua and leave", 312)
    f.text(24, 22, "kilo at 09.07, \"new \" typed and not saved, then Ctrl-X; a scratch build writes a line at each "
           "point", "tm", 11)
    qlines = QUIT_INIT.rstrip("\n").split("\n")
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

    def state(rows_, line):
        for k, (key, val, hot) in enumerate(rows_):
            yy = 140 + k * 19
            f.text(306, yy, key, "tm", 10.5)
            f.text(400, yy, val, "ta" if hot else "t", 10.5, weight=700 if hot else None)
        f.text(306, 262, "the scratch build wrote:", "tm", 9.5)
        for k, s_ in enumerate(line):
            mono(f, 306, 277 + k * 13, s_, "ta", 8.4, weight=700)
    base = [("main: while(1)", "live"), ("editorProcessKeypress", "live"), ("editorScriptKey", "live"),
            ("scriptCall", "live")]
    with steps.step(f, "Ctrl-X: the function mapped to it calls quit(true). quit() only sets a mark, editorQuit = 1, "
                       "and returns: the Lua function goes on to its next line."):
        at_line(1)
        stack(base + [("scriptProtected: lua_pcall", "live"), ("Lua: the function mapped to <C-x>", "live"),
                      ("kilo.api.quit(true): apiQuit", "hot")])
        state([("editorQuit", "1: the mark", True), ("Lua running", "yes, one call deep", False),
               ("after.txt", "not yet: the next line", False), ("the Lua state", "open", False),
               ("the terminal", "raw", False), ("kilo", "running", False)], [tr_[0]])
    with steps.step(f, "The function's last line has run (after.txt was written) and it returns: lua_pcall in "
                       "scriptProtected returns, and no Lua is running. The key's work ends there."):
        at_line(2, 3)
        stack(base + [("scriptProtected: lua_pcall returned", "hot"), ("Lua: the function mapped to <C-x>", "gone"),
                      ("kilo.api.quit(true): apiQuit", "gone")])
        state([("editorQuit", "1", False), ("Lua running", "no: depth 0", True), ("after.txt", "ran", True),
               ("the Lua state", "open", False), ("the terminal", "raw", False), ("kilo", "running", False)],
              [tr_[1]])
    with steps.step(f, "At the top of main's loop, editorAfterKey() sees the mark and calls exit(0). At exit, "
                       "scriptStop() puts the terminal back, then closes the Lua state: nothing of Lua is on the "
                       "stack. The change was not saved."):
        stack([("main: while(1)", "live"), ("editorAfterKey: exit(0)", "live"), ("atexit: scriptStop", "hot")])
        state([("editorQuit", "1", False), ("Lua running", "no", False), ("after.txt", "ran", False),
               ("the Lua state", "closed: lua_close", True), ("the terminal", "put back (ECHO on)", True),
               ("kilo", f"exited, status {cap['rc']}", True)], tr_[2:])
    return f


# ---------------------------------------------------------------- 09.08

def hook0908():
    cap = capture0908hook()
    h = source("09.08", "script.h")
    c = source("09.08", "script.c")
    m = re.search(r"#define SCRIPT_HOOK_COUNT (\d+)", h)
    count = int(m.group(1))
    for needle in ("lua_sethook(L,scriptHook,LUA_MASKCOUNT,1);", "luaL_where(L,0);", 'lua_pushliteral(L,"interrupted");',
                   "if (S.depth == 0 && status != LUA_OK) lua_gc(L,LUA_GCCOLLECT);",
                   "lua_sethook(L,scriptHook,LUA_MASKCOUNT,SCRIPT_HOOK_COUNT);", "poll(&pfd,1,0) == 1",
                   "if (buf[i] == 3) S.interrupted = 1;"):
        assert needle in c, needle
    assert cap["alive"] and cap["shot"].lines[-1] == "init.lua:2: interrupted", cap["shot"].lines[-1]
    assert cap["shot"].lines[0] == "safe text" and cap["saved"] == "ok safe text\n"
    assert "kilo.api.set_keymap('<C-t>', function() while true do end end)" == cap["init"].split("\n")[1]
    every = said(f"the hook runs every {count} instructions, about 0.2 ms here")
    said("`init.lua:2: interrupted`", "`lua_sethook(lua,luaMaskCountHook,LUA_MASKCOUNT,100000);`",
         "executor.c has no lua_sethook")
    ms = float(re.search(r"about ([\d.]+) ms", every).group(1))
    f = F9("f0908a", f"The count hook in kilo at 09.08: every {count} instructions it looks at the keyboard; a Ctrl-C "
           "there raises interrupted, which goes up to the protected call", 338)
    f.text(24, 22, "kilo at 09.08 with INIT of 0908: Ctrl-T runs while true do end; a second later a b c, then "
           "Ctrl-C", "tm", 11)
    # the instructions, and the looks
    y, x0, x1 = 96, 40, 470
    f.line(x0, y, x1, y, "m")
    k = x0
    while k <= x1:
        f.line(k, y - 3, k, y + 3, "m")
        k += 4
    looks = [x0 + 30 + j * 62 for j in range(7)]
    for j, lx in enumerate(looks):
        last = j == len(looks) - 1
        f.circle(lx, y, 5, "a fa" if last else "a f")
    f.brace_h(looks[0], looks[1], y + 14)
    f.text((looks[0] + looks[1]) / 2, y + 30, f"{count} instructions", "t", 10, "middle", 600)
    f.text((looks[0] + looks[1]) / 2, y + 43, f"about {ms:g} ms", "tm", 10, "middle")
    f.text(looks[2], y + 30, "each look: poll() with no wait;", "tm", 10)
    f.text(looks[2], y + 43, "nothing there: the script goes on", "tm", 10)
    # the keys arriving, each above the look that reads it
    for label, look in (("a b c", 5), ("Ctrl-C", 6)):
        hot = label == "Ctrl-C"
        f.text(looks[look], y - 40, label, "ta" if hot else "t", 10.5, "middle", 700, mono=not hot)
        f.line(looks[look], y - 34, looks[look], y - 10, "a" if hot else "s", arrow=True)
    f.text(x1 + 8, y - 4, "a b c: read by a look,", "t", 10)
    f.text(x1 + 8, y + 9, "and dropped", "t", 10)
    f.text(x1 + 8, y + 26, "Ctrl-C: the last look", "ta", 10, weight=700)
    f.text(x1 + 8, y + 39, "finds a 3", "ta", 10, weight=700)
    f.text(24, 50, "Lua's instructions (not to scale: a second is some "
           f"{int(round(1000 / ms, -2))} looks)", "tm", 10)
    # the error going up
    f.text(24, 172, "then the error goes up the stack, to the protected call", "tm", 10.5)
    boxes = [("scriptHook: the count set to 1; where + \"interrupted\"; lua_error", "hot"),
             ("init.lua:2, the function mapped to <C-t>: unwound", "gone"),
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
    # the screen afterwards
    sx = 440
    f.text(sx, 176, "the screen after: row 0, and", "tm", 10)
    f.text(sx, 189, "the message line", "tm", 10)
    f.rect(sx, 196, 176, 40, "s fs", 4)
    mono(f, sx + 8, 210, cap["shot"].lines[0], "t", 10)
    mono(f, sx + 8, 228, cap["shot"].lines[-1], "ta", 10, weight=700)
    notes(f, sx, 254, f"Row 0 as it was: the a b c never reached it. Then ok and Ctrl-S saved \"{cap['saved'][:-1]}\".",
          32, "t", 10, 13)
    f.text(24, 312, "Redis sets the same kind of hook: lua_sethook(lua,luaMaskCountHook,LUA_MASKCOUNT,100000) "
           "(src/script_lua.c).", "tm", 10)
    f.text(24, 326, "Neovim's executor.c has no lua_sethook.", "tm", 10)
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
    assert r8["grow"] == "not enough memory" and r8["grow_after"] < 1024 and r8["big"] == "not enough memory"
    assert r7["big"] == str(200 * 2 ** 20), r7
    said("`not enough memory` after 51468 strings of 1 KB; 87 KB after the collection",
         "`#string.rep('x', 200 * 2^20)` | `209715200`; collectgarbage('count') after: 212642 KB | `not enough "
         "memory`; 1584 KB after", "| SCRIPT_MAX_MEMORY | 64 MB | what Lua may hold (0908) |")
    f = F9("f0908b", "Lua's memory in kilo: every block through scriptAlloc(), refused past 64 MB, and given back "
           "by the collection after the error", 340)
    f.text(24, 22, "kilo at 09.08 and at 09.07; the numbers are NOTES.md's (09.08), the messages from runs here",
           "tm", 11)
    code(f, 24, 32, [line_h + "        script.h", line_c + "  script.c, scriptAlloc()"], size=8.8)
    X0, W = 40, 400
    px = W / 64                                   # pixels per MB

    def axis(y):
        for mb in (0, 16, 32, 48, 64):
            f.line(X0 + mb * px, y + 22, X0 + mb * px, y + 26, "m")
            f.text(X0 + mb * px, y + 37, f"{mb} MB", "ta" if mb == 64 else "tm", 9, "middle",
                   700 if mb == 64 else None)
    # the table grown for ever
    y = 102
    f.text(24, y - 8, "a table grown for ever, at 09.08", "t", 11, weight=700)
    f.rect(X0, y, W, 20, "s f", 2)
    f.bar(X0 + 1, y + 1, W - 2, 18, "af", 1)
    f.text(X0 + 8, y + 14, "51468 strings of 1 KB, and the table", "ta", 10, weight=600)
    f.line(X0 + W, y - 6, X0 + W, y + 26, "a")
    f.rect(X0 + W + 4, y, 26, 20, "a", 2, dash=True)
    f.text(X0 + W + 36, y + 9, "the next block:", "ta", 10, weight=700)
    f.text(X0 + W + 36, y + 22, "NULL, refused", "ta", 10, weight=700)
    axis(y)
    f.text(24, y + 58, "Lua raises \"not enough memory\"; the protected call catches it; at the outermost "
           "return, a full collection:", "t", 10.5)
    f.rect(X0, y + 68, W, 16, "m f", 2)
    f.bar(X0 + 1, y + 69, max(87 / 1024 * px, 2), 14, "fa", 0)
    f.text(X0 + 10, y + 80, "87 KB held after", "ta", 10, weight=700)
    # one block of 200 MB
    y = 240
    f.text(24, y - 8, "#string.rep('x', 200 * 2^20): one block of 200 MB", "t", 11, weight=700)
    # 09.07: the bar runs off the scale
    f.rect(X0, y, 560, 18, "s f", 2)
    f.bar(X0 + 1, y + 1, 558, 16, "fs", 1)
    f.path(f"M{X0 + 470} {y - 3} l6 12 l-6 12", "m")
    f.path(f"M{X0 + 478} {y - 3} l6 12 l-6 12", "m")
    f.line(X0 + W, y - 6, X0 + W, y + 24, "a")
    f.text(X0 + 8, y + 13, "09.07, no allocator of kilo's: 209715200 bytes made; 212642 KB held after", "t", 9.5)
    y2 = y + 30
    f.rect(X0, y2, W, 18, "m f", 2)
    f.text(X0 + 10, y2 + 13, "09.08: refused at once, \"not enough memory\"; 1584 KB held after", "ta", 9.5, weight=700)
    f.text(24, 324, "At 09.08 Lua's state is made by lua_newstate(scriptAlloc, NULL); at 09.07 by luaL_newstate(), "
           "with no limit of kilo's.", "tm", 10)
    return f


def trust0908():
    said("`lua_State *lstate = luaL_newstate();` and `luaL_openlibs(lstate);` in nlua_init",
         "executor.c has no lua_sethook",
         "The Extension Host in VS Code prevents extensions from: Impacting startup performance / Slowing down UI "
         "operations / Modifying the UI",
         "we run extensions in an [Extension Host](/api/advanced-topics/extension-host) process and prevent direct "
         "access to the DOM.",
         "an extension can read and write files on your machine, make network requests, run external processes",
         "There can be several hosts (local, remote, web)", "another process (the extension host)",
         "runs an extension with wasmtime (`wasmtime::Engine`, `wasmtime::Store::new(`) inside Zed's process",
         "`ctx.preopened_dir(&path, \".\", dir_perms, file_perms)?;`",
         "governed by a capability system",
         "Capabilities (`process:exec`, `download_file`, `npm:install`)",
         "Procedural parts of extensions are written in Rust and compiled to WebAssembly.",
         "Redis (not an editor) | Lua 5.1 | in the server's process",
         "a script has the user's whole trust")
    f = F9("f0908c", "Where extension code runs in Neovim, VS Code and Zed, what stops a loop that never ends, and "
           "what it may reach, as their sources and docs say", 340)
    f.text(24, 22, "from each project's source and docs, as NOTES.md (09) quotes them; not run", "tm", 11)
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
            "No count hook: executor.c has no lua_sethook.",
            "The host \"prevents extensions from ... Slowing down UI operations\".",
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
    cli, key = cap["cli"], cap["key"]
    assert (cli["rc"], cli["stdout"], cli["stderr"]) == (0, "2 lines upper-cased\n", ""), cli
    assert cli["file"] == key["file"] == "HELLO\nWORLD\n123\n" and key["rc"] == 0
    assert key["shot"].lines[:3] == ["HELLO", "WORLD", "123"] and key["shot"].lines[-1] == "2 lines upper-cased"
    said("$ ./kilo -l upper.lua notes.txt (hello / World / 123) 2 lines upper-cased (status 0; notes.txt: HELLO / "
         "WORLD / 123)")
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
    f = F9("f0909a", "Two ways into the same API: the keyboard and the screen, or kilo -l with a script; main() "
           "takes the second before any of the screen's work", 358)
    f.text(24, 22, "kilo at 09.09, UPPER of 0909 as upper.lua, on notes.txt (hello / World / 123), each way", "tm", 11)
    # the left door
    lx = 24
    f.text(lx, 52, "the keyboard and the screen", "t", 11, weight=700)
    mono(f, lx, 70, "$ ./kilo notes.txt", "t", 9.5)
    f.text(lx, 90, "Ctrl-U, mapped in init.lua:", "tm", 10)
    mono(f, lx, 104, "dofile('upper.lua')", "t", 9.5)
    f.text(lx, 128, "the screen after:", "tm", 10)
    screen(f, lx + 6, 136, key["shot"], 5.6, 14, 21, rows=[0, 1, 2, 7], status=False)
    # main()
    mx = 186
    f.text(mx, 52, "main() at 09.09", "tm", 10)
    shown = ["int main(int argc, char **argv) {"] + ["    " + s_ for s_, _ in MAIN_LINES]
    bottom, bases = code(f, mx, 58, shown, size=8.2, lh=12.2, mark=(2, 3), w=226)
    # what -l skips
    a, b = bases[4] - 9, bases[-1] + 3
    f.path(f"M{mx + 230} {fmt(a)} L{mx + 236} {fmt(a)} L{mx + 236} {fmt(b)} L{mx + 230} {fmt(b)}", "a")
    # the right door
    rx = 430
    f.text(rx, 52, "no screen", "t", 11, weight=700)
    mono(f, rx, 70, "$ ./kilo -l upper.lua notes.txt", "t", 8.6)
    f.text(rx, 90, "editorRunScript():", "tm", 10)
    code(f, rx, 96, RUN_LINES, size=7.6, w=186)
    notes(f, rx, 192, "kilo -l skips every line the bracket holds: raw mode, the window's size, the HELP line, "
          "init.lua and its count hook, BufReadPost, and the key loop with the screen.", 34, "ta", 10, 13,
          weight=600)
    # where both arrive
    by = 290
    f.rect(150, by, 340, 24, "a af", 6)
    f.text(320, by + 16, "kilo.api: the same 24 functions, the same rows", "ta", 11, "middle", 700)
    f.line(172, 98, 172, by - 3, "s", arrow=True)
    f.line(468, 280, 468, by - 3, "s", arrow=True)
    f.line(mx + 228, bases[2] - 3, rx - 3, bases[2] - 3, "a", arrow=True)
    f.text(24, 334, "Both leave notes.txt as HELLO / WORLD / 123 and say \"2 lines upper-cased\": in the message line;",
           "t", 10.5)
    f.text(24, 348, f"with -l, on standard output, and kilo's status is {cli['rc']}.", "t", 10.5)
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
    f = F9("f0909b", "Neovim as a server: the terminal UI is one client of the API, in a process of its own, and "
           "other programs are clients the same way; kilo keeps its screen inside", 340)
    f.text(24, 22, "Neovim v0.12.6, from its documentation as NOTES.md (09) quotes it; not run", "tm", 11)
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
    mono(f, kx + 10, 202, "$ ./kilo -l s.lua notes.txt", "t", 9)
    f.rect(kx + 10, 212, 162, 22, "a af", 4)
    f.text(kx + 18, 227, "kilo.api, no screen", "ta", 9.5, weight=700)
    notes(f, kx, 262, "The screen is drawn inside kilo; only the API is shared by the editor and -l.", 34, "t", 10, 13)
    return f


# ---------------------------------------------------------------- 09.10

def could_have_been0910():
    said("A KeyPress function (created first, so it runs first) takes the keys of \"normal\" mode, moves with feed_key "
         "or set_cursor, edits with set_lines, gives keys back by returning false; Escape and i switch modes",
         "A mode in the status bar with set_statusline.",
         "by highlights over the visible rows, again on BufReadPost, TextChanged and CursorMoved",
         "a one-shot find (input(), then set_cursor and a highlight) yes", "go to a line, yes (0907)")
    kc = open(os.path.join(KILO, "kilo.c")).read()
    for fn in ("void editorFind(int fd) {", "void editorUpdateSyntax(erow *row) {", "struct editorSyntax HLDB[] = {"):
        assert fn in kc, fn
    api = re.findall(r'^\s*\{"(\w+)", \{', kc, re.M)
    for name, calls in PLUGIN_CALLS.items():
        for c_ in calls:
            assert c_ in api, (name, c_)
    f = F9("f0910a", "Three features as scripts: what each is or would be in C, the plugin that does it in Lua, and "
           "the API functions the plugin calls", 330)
    f.text(24, 22, "09.10's three plugins, each only Lua, each standing in for C", "tm", 11)
    cols = [24, 230, 436]
    W = 180
    heads = [("vi's keys", "vi.lua"), ("colour for C and Lua", "colour.lua"), ("go to a line, and find", "find.lua")]
    in_c = [("none in the track:", "kilo's keys have no modes"),
            ("module 06: editorUpdateSyntax()", "and the HLDB table, in kilo.c"),
            ("module 05: editorFind(),", "in kilo.c")]
    how = ["A KeyPress function takes normal mode's keys: moves with feed_key or set_cursor, edits with set_lines; "
           "Escape and i switch modes, shown in the status bar.",
           "Highlights over the rows on the screen, put again on BufReadPost, TextChanged and CursorMoved.",
           "input() asks; set_cursor goes there; a highlight shows the match."]
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
        ends.append(notes(f, x, 186, how[k], 33, "t", 10, 13))
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
    said("one loop would have to own all the waiting, as libuv does in Neovim; 07's poll() and a timer here could not "
         "know of each other", "one file at a time (E is one file: no buffers, no windows)",
         "highlights that do not move when the text does (Neovim's extmarks do)", "no floating windows or menus",
         "(and Buffer, Window, Tabpage)", "nvim_win_set_cursor", "Platform and I/O facilities are built upon libuv.",
         "`vim.uv` exposes the \"luv\" Lua bindings for the libUV library",
         "Tree data structure for storing marks at (row, col) positions and updating them to arbitrary text changes.",
         "Marks are moved by calls to extmark_splice.")
    f = F9("f0910b", "Four things a script cannot do in kilo, the piece of an editor each would need, and that piece "
           "in Neovim", 318)
    f.text(24, 22, "what NOTES.md (09) leaves out of kilo on purpose, and Neovim's name for each piece, from its "
           "source and docs", "tm", 11)
    X = [24, 196, 406]
    WS = [164, 202, 210]
    heads = ["a script cannot", "it would need", "in Neovim"]
    for x, h_ in zip(X, heads):
        f.text(x, 50, h_, "tm", 10, weight=600)
    rows_ = [
        ("wait for a time, or work in the background",
         "one loop that owns all the waiting: 07's poll() and a timer here could not know of each other",
         "libuv: \"Platform and I/O facilities are built upon libuv\"; vim.uv gives Lua its bindings"),
        ("edit more than one file",
         "many buffers: kilo's E is one file",
         "Buffer, a type of the API (kObjectTypeBuffer); the nvim_buf_* functions take one"),
        ("keep marks that move with the text",
         "marks in a tree, moved by every edit: kilo keeps a list, put again on TextChanged",
         "extmarks, in a MarkTree (marktree.c), moved by extmark_splice"),
        ("show windows over the text",
         "windows: kilo draws one screen of one file",
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
    check_plugins()
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
