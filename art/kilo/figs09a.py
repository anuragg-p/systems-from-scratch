"""Figures for kilo module 09, An API, and Lua on top of it: lessons 09.01 to 09.05 (an extension).

    python3 -B art/kilo/figs09a.py [name-prefix ...]
                                       writes tracks/kilo/lessons/09-api-and-lua/figures/09.0N-*.svg

09.06 to 09.10 are figs09b.py's; the maps, the cover and the icon are archmap.py's and covers.py's
(the cover from capture_cover() here).

Every script, screen, message, byte and number here is from a real run of the lesson's own example
(its file, its init.lua, read from the lesson's text, its keys and terminal size), checked against
the lesson's words and NOTES.md's; Neovim's names are NOTES.md's, checked against its words. The
project at each lesson is written with ./learn files kilo --at 09.0N, given Lua's source as the
track's own tools give it (track.py's supply_lua), and built with make; ./kilo runs on a
pseudo-terminal through the track's fixture (edit() in tracks/kilo/track.py), with KILO_INIT
naming the init.lua. What the code does not print (Lua's stack, the dispatcher's steps, a
reference's life, the events and the tick) comes from a scratch copy of the project with a few
lines put in (a patch, below) that append to the file $KILO_TRACE. The figures say nothing of how
they were made.

  09.01-stack            stepped: the project at 09.01 with STACK_PATCH, 1+1 typed at Ctrl-E on
                         notes.txt, 8 x 80: Lua's stack after each step of scriptEvalIn() and print
  09.01-protected-call   the lesson's init.lua with a typo at 09.01: the screen (ERROR_PATCH for the
                         status and the stack lua_pcall() left); then a copy with lua_call(), run
                         from sh on the terminal, which prints kilo's exit status and stty -a
  09.02-table            kilo --api-info at 09.02 and at 09.09, and the entry for get_lines in kilo.c
  09.02-dispatch         stepped: the project at 09.02 with DISPATCH_PATCH, the lesson's
                         table.concat(kilo.api.get_lines(0, 2), ' | ') at Ctrl-E on notes.txt
  09.02-generator        Neovim's generator and its three ways in (NOTES.md), kilo's two (the code)
  09.03-set-lines        stepped: the lesson's five rows a to e and its calls, through an init.lua
                         (kilo -l comes only at 09.09), get_lines after each
  09.03-cursor-rule      three of NOTES.md's cursor cases on ten rows, run again the same way
  09.04-reference        stepped: the project at 09.04 with REF_PATCH and REF_PATCH_KILO, the
                         lesson's init.lua on demo.lua, 8 x 72: Ctrl-D, then the lesson's
                         kilo.keymap.set('<C-d>', print) at the prompt
  09.04-layers           SCRIPT_LUA from script.c, --api-info at 09.04, Neovim's names (NOTES.md)
  09.05-save-events      the project at 09.05 with EVENT_PATCH, the lesson's init.lua on its
                         notes.txt, 8 x 72: a, space, Ctrl-S; the rows, the events, the file
  09.05-tick             the same: a, Right, Enter; the tick at each key, where TextChanged fired
  09.05-nesting          stepped: the same, the lesson's TextChanged function that adds a ! made
                         at the prompt, then x and y
"""
import contextlib
import functools
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


NOTES_TXT = "hello world\nsecond line\n"     # the lessons' notes.txt, 09.01 to 09.03


def lesson_text(lid):
    d = os.path.join(figlib.LESSONS, MOD)
    name = next(n for n in sorted(os.listdir(d)) if n.startswith(lid + "-") and n.endswith(".md"))
    with open(os.path.join(d, name)) as f:
        return f.read()


def in_lesson(lid, phrase):
    """Stop unless the lesson's text says phrase, wrapping aside: the figure shows the lesson's own example."""
    if flat(phrase) not in flat(lesson_text(lid)):
        raise SystemExit(f"figs09a: lesson {lid} does not say {phrase!r}")


def lesson_init(lid):
    """The init.lua a lesson's Run it has the reader write: the ```lua block after "init.lua`:"."""
    text = lesson_text(lid)
    at = text.index(f"Put this in `build/at/kilo/{lid}/init.lua`:")
    at = text.index("```lua\n", at) + len("```lua\n")
    return text[at:text.index("```", at)]


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


# ------------------------------------------------------------------ Lua's stack, as a trace line

# A C function put into a scratch copy of script.c: one line in $KILO_TRACE for the stack of the
# function running now, "what|top|type:value|...", bottom first. A function is C or Lua (C:print
# for kilo's print, scriptPrint), a table its length, a light userdata nothing more.
DUMP_C = r'''
static int scriptPrint(lua_State *L);
static void figsDump(lua_State *L, const char *what) {
    FILE *tf_ = getenv("KILO_TRACE") ? fopen(getenv("KILO_TRACE"),"a") : NULL;
    int i, top = lua_gettop(L);
    if (!tf_) return;
    fprintf(tf_,"%s|%d",what,top);
    for (i = 1; i <= top; i++) {
        int t = lua_type(L,i);
        if (t == LUA_TSTRING) fprintf(tf_,"|string:%s",lua_tostring(L,i));
        else if (t == LUA_TNUMBER && lua_isinteger(L,i)) fprintf(tf_,"|integer:%lld",(long long)lua_tointeger(L,i));
        else if (t == LUA_TNUMBER) fprintf(tf_,"|float:%g",lua_tonumber(L,i));
        else if (t == LUA_TFUNCTION && lua_tocfunction(L,i) == scriptPrint) fprintf(tf_,"|function:C:print");
        else if (t == LUA_TFUNCTION) fprintf(tf_,"|function:%s",lua_iscfunction(L,i) ? "C" : "Lua");
        else if (t == LUA_TTABLE) fprintf(tf_,"|table:%d",(int)lua_rawlen(L,i));
        else if (t == LUA_TLIGHTUSERDATA) fprintf(tf_,"|light userdata:");
        else fprintf(tf_,"|%s:",lua_typename(L,t));
    }
    fprintf(tf_,"\n");
    fclose(tf_);
}
'''


def stack_of(line):
    """A trace line of figsDump: (what, [(type, value)], bottom first)."""
    parts = line.split("|")
    slots = [tuple(p.split(":", 1)) for p in parts[2:]]
    assert len(slots) == int(parts[1]), line
    return parts[0], slots


# ------------------------------------------------------------------ 09.01: captures

STACK_PATCH = [
    ("static int scriptProtected(lua_CFunction fn, void *arg) {\n",
     DUMP_C + "static int scriptProtected(lua_CFunction fn, void *arg) {\n"),
    ("    lua_pushlightuserdata(L,arg);\n    status = lua_pcall(L,1,0,0);\n",
     '    lua_pushlightuserdata(L,arg);\n    figsDump(L,"protected before");\n    status = lua_pcall(L,1,0,0);\n'
     '    figsDump(L,"protected after");\n'),
    ("    lua_settop(L,0);\n    lua_pushfstring(L,\"return %s;\",line);\n",
     '    figsDump(L,"entry");\n    lua_settop(L,0);\n    figsDump(L,"settop");\n'
     '    lua_pushfstring(L,"return %s;",line);\n    figsDump(L,"pushfstring");\n'),
    ("    } else {\n        lua_remove(L,1);\n    }\n    lua_call(L,0,LUA_MULTRET);\n",
     '    } else {\n        figsDump(L,"loadbuffer");\n        lua_remove(L,1);\n    }\n    figsDump(L,"remove");\n'
     '    lua_call(L,0,LUA_MULTRET);\n    figsDump(L,"call chunk");\n'),
    ("        lua_getglobal(L,\"print\");\n        lua_insert(L,1);\n        lua_call(L,n,0);\n    }\n",
     '        lua_getglobal(L,"print");\n        figsDump(L,"getglobal");\n        lua_insert(L,1);\n'
     '        figsDump(L,"insert");\n        lua_call(L,n,0);\n        figsDump(L,"call print");\n    }\n'),
    ("        luaL_tolstring(L,i,NULL);\n        luaL_addvalue(&b);\n",
     '        luaL_tolstring(L,i,NULL);\n        figsDump(L,"print tolstring");\n        luaL_addvalue(&b);\n'),
]


@functools.lru_cache(None)
def capture0901stack():
    """The project at 09.01 with STACK_PATCH, on the lesson's notes.txt, 8 x 80: Ctrl-E, 1+1, Enter. The stacks the trace gives, in order from the protected call that ran the line, and
    the screens."""
    with context("09.01", STACK_PATCH) as t:
        env = dict(os.environ, KILO_TRACE=os.path.join(t.tmp, "trace.txt"))
        ed = TK.edit(t, NOTES_TXT, name="notes.txt", rows=8, cols=80, env=env)
        ed.keys(ctrl("e"))
        prompt = ed.message
        ed.keys("1+1")
        typed = ed.message
        ed.keys(ENTER)
        shot = Shot(ed)
        trace = trace_lines(os.path.join(t.tmp, "trace.txt"))
    assert prompt == "lua:" and typed == "lua: 1+1" and shot.lines[-1] == "2", (prompt, typed, shot.lines[-1])
    in_lesson("09.01", "Press Ctrl-E: the message line says `lua: `. Type `1+1` and Enter: it says `2`")
    stacks = [stack_of(line) for line in trace]
    start = max(i for i, (w, _) in enumerate(stacks) if w == "protected before" and i + 1 < len(stacks)
                and stacks[i + 1][0] == "entry")
    got = stacks[start:]
    assert [w for w, _ in got] == ["protected before", "entry", "settop", "pushfstring", "loadbuffer", "remove",
                                   "call chunk", "getglobal", "insert", "print tolstring", "call print",
                                   "protected after"], [w for w, _ in got]
    return {"stacks": dict(got), "shot": shot}


INIT_ERROR = ["local name = 'kilo'", "print('hello ' .. nme)"]
# What lua_pcall() gave back in scriptProtected(): its status, and the stack.
ERROR_PATCH = [STACK_PATCH[0],
               ("    status = lua_pcall(L,1,0,0);\n",
                "    status = lua_pcall(L,1,0,0);\n" + tracer("pcall status|%d", "status")
                + '\n    figsDump(L,"after pcall");\n')]


@functools.lru_cache(None)
def capture0901error():
    """The lesson's init.lua with a typo, at 09.01 on notes.txt, 8 x 80: the screen. Then the same
    with scriptProtected() calling lua_call() for lua_pcall(): run from sh on the terminal, which
    then prints kilo's exit status and stty -a, the modes kilo left."""
    in_lesson("09.01", 'printf "local name = \'kilo\'\\nprint(\'hello \' .. nme)\\n" > build/at/kilo/09.01/init.lua')
    init = "\n".join(INIT_ERROR) + "\n"
    text = NOTES_TXT
    with context("09.01") as t:
        ed = TK.edit(t, text, name="notes.txt", rows=8, cols=80, init=init)
        shot = Shot(ed)
    want = "init.lua:2: attempt to concatenate a nil value (global 'nme')"
    assert shot.lines[-1] == want and shot.lines[:2] == ["hello world", "second line"], shot.lines
    in_lesson("09.01", want)
    with context("09.01", ERROR_PATCH) as t:
        env = dict(os.environ, KILO_TRACE=os.path.join(t.tmp, "trace.txt"))
        TK.edit(t, text, name="notes.txt", rows=8, cols=80, init=init, env=env)
        trace = trace_lines(os.path.join(t.tmp, "trace.txt"))
    status_line = [x for x in trace if x.startswith("pcall status|")]
    after = [stack_of(x)[1] for x in trace if x.startswith("after pcall|")]
    patch = [("    status = lua_pcall(L,1,0,0);\n", "    lua_call(L,1,0); status = LUA_OK;\n")]
    with context("09.01", patch) as t:
        for name, body in (("notes.txt", text), ("init.lua", init)):
            with open(os.path.join(t.tmp, name), "w") as f:
                f.write(body)
        env = dict(os.environ, KILO_INIT=os.path.join(t.tmp, "init.lua"), KILO_LSP="")
        sh = "./kilo notes.txt; s=$?; echo; echo \"kilo's exit status: $s\"; stty -a"
        shutil.copy(os.path.join(t.root, "kilo"), os.path.join(t.tmp, "kilo"))
        s = t.spawn(["/bin/sh", "-c", sh], name="sh", cwd=t.tmp, pty=True, env=env, size=(24, 80))
        rc = s.wait_exit(20)
        while s._pump(0.1):
            pass
        out = s.buf.decode("utf-8", "replace")
    assert rc == 0, out
    m = re.search(r"kilo's exit status: (\d+)", out)
    before = out[:m.start()]
    panic = re.match(r"PANIC: unprotected error in call to Lua API \((.*)\)\n", before)
    assert panic and panic.group(1) == want, before
    in_lesson("09.01", panic.group(0).rstrip("\n"))
    abort = re.search(r"Abort trap: 6", before)
    modes = re.findall(r"(?<![\w-])(-?(?:icanon|isig|echo|icrnl|ixon|opost))(?![\w-])", out[m.end():])
    assert sorted(modes) == sorted(["-icanon", "-isig", "-echo", "-icrnl", "-ixon", "-opost"]), modes
    # two protected calls: the libraries (scriptOpen), then the init file
    assert status_line == ["pcall status|0", "pcall status|2"] and after == [[], [("string", want)]], \
        (status_line, after)
    return {"shot": shot, "status": int(m.group(1)), "panic": panic.group(0).rstrip("\n"),
            "abort": abort.group(0) if abort else None, "modes": modes, "message": want}


# ------------------------------------------------------------------ 09.02: captures



DISPATCH_PATCH = [
    STACK_PATCH[0],
    ("    int n = lua_gettop(L), i, status, nret;\n",
     "    int n = lua_gettop(L), i, status, nret;\n" + tracer("entry|%s|%d", "f->name", "f->nargs")
     + '\n    figsDump(L,"dispatch entry");\n'),
    ("apiTypeName(f->args[i]),why);\n",
     "apiTypeName(f->args[i]),why);\n    for (i = 0; i < n; i++)"
     + tracer("check|%d|%s|%s|%s", "i+1", "f->argnames[i]", "apiTypeName(f->args[i])", "luaL_typename(L,i+1)")
     + "\n"),
    ("    ret = f->fn(args,n,&err);\n",
     "    for (i = 0; i < n; i++)" + tracer("take|%d|%s|%lld", "i+1", "apiTypeName(args[i].type)",
                                          "args[i].u.integer")
     + "\n    ret = f->fn(args,n,&err);\n" + tracer("ret|%s|%d", "apiTypeName(ret.type)", "ret.u.lines.count")
     + "\n    for (i = 0; ret.type == API_LINES && i < ret.u.lines.count; i++)"
     + tracer("retline|%d|%s", "i", "ret.u.lines.line[i].s") + "\n"),
    ("    status = lua_pcall(L,1,nret,0);\n",
     "    status = lua_pcall(L,1,nret,0);\n" + '    figsDump(L,"pushed");\n'),
]
GET_LINES = "table.concat(kilo.api.get_lines(0, 2), ' | ')"


@functools.lru_cache(None)
def capture0902():
    """kilo --api-info at 09.02 and at 09.09; and the project at 09.02 with DISPATCH_PATCH running
    the lesson's line GET_LINES at the prompt (Ctrl-E) on its notes.txt, 8 x 80: the dispatcher's trace
    and the message line."""
    info = subprocess.run([os.path.join(project("09.02"), "kilo"), "--api-info"], capture_output=True,
                          text=True, check=True).stdout.split("\n")[:-1]
    full = subprocess.run([os.path.join(project("09.09"), "kilo"), "--api-info"], capture_output=True,
                          text=True, check=True).stdout.split("\n")[:-1]
    for line in info:
        in_notes(line, "The API as built")
    with context("09.02", DISPATCH_PATCH) as t:
        env = dict(os.environ, KILO_TRACE=os.path.join(t.tmp, "trace.txt"))
        ed = TK.edit(t, NOTES_TXT, name="notes.txt", rows=8, cols=80, env=env)
        ed.keys(ctrl("e"), GET_LINES, ENTER)
        shot = Shot(ed)
        trace = trace_lines(os.path.join(t.tmp, "trace.txt"))
    in_lesson("09.02", GET_LINES + "  hello world | second line")
    assert shot.lines[-1] == "hello world | second line", shot.lines
    get = trace[trace.index("entry|get_lines|2"):]
    return {"info": info, "full": full, "shot": shot, "trace": get}


# ------------------------------------------------------------------ 09.03: captures

FIVE = ["a", "b", "c", "d", "e"]                         # the lesson's five rows, and its calls
SET_CASES = [("a change", 1, 3, ["X", "Y"]), ("an insert", 2, 2, ["new"]), ("a delete", 1, 3, []),
             ("refused", 0, 1, ["a", "b", "c\nd"])]
TEN = [f"line{i}" for i in range(10)]
# NOTES.md's cursor cases (0903), as (cursor before, start, end, lines, cursor after): one below
# the range, one inside it, one above it.
CURSOR_CASES = [((8, 2), 2, 5, [], (5, 2)), ((6, 4), 3, 8, ["x", "y"], (4, 1)), ((1, 3), 5, 7, ["x"], (1, 3))]
LOGGER = ("local out = io.open(os.getenv('FIGS_LOG'), 'w')\n"
          "local function note(...) out:write(table.concat({...}, '\\31'), '\\n') out:flush() end\n"
          "local function rows() return table.concat(kilo.api.get_lines(0, kilo.api.line_count()), '|') end\n")


def lua_list(items):
    return "{" + ", ".join(TK.lua_quote(s) for s in items) + "}"


def run_init(at, init, text, rows=8, cols=60, keys=(), patch=None):
    """kilo at `at` (with patch) on f.txt holding text, its init.lua LOGGER + init, keys typed one by
    one: (the lines init.lua noted, a Shot after each key (the first: before any), the file after,
    the trace)."""
    with context(at, patch) as t:
        log = os.path.join(t.tmp, "figs.log")
        env = dict(os.environ, FIGS_LOG=log, KILO_TRACE=os.path.join(t.tmp, "trace.txt"))
        ed = TK.edit(t, text, rows=rows, cols=cols, init=LOGGER + init, env=env)
        shots = [Shot(ed)]
        for k in keys:
            ed.keys(k)
            shots.append(Shot(ed))
        with open(log) as f:
            noted = [line.split("\x1f") for line in f.read().split("\n")[:-1]]
        with open(ed.path, newline="") as f:
            saved = f.read()
        return noted, shots, saved, trace_lines(os.path.join(t.tmp, "trace.txt"))


@functools.lru_cache(None)
def capture0903():
    """The project at 09.03: each of SET_CASES on FIVE, and each of CURSOR_CASES on TEN, through
    an init.lua (kilo -l comes only at 09.09); what get_lines and get_cursor said after."""
    lua = [f"local FIVE, TEN = {lua_list(FIVE)}, {lua_list(TEN)}"]
    for _, s, e, lines in SET_CASES:
        lua.append("kilo.api.set_lines(0, kilo.api.line_count(), FIVE)")
        lua.append(f"do local ok, err = pcall(kilo.api.set_lines, {s}, {e}, {lua_list(lines)}) "
                   f"note('set', tostring(ok), err or '', rows()) end")
    for (r, c), s, e, lines, _ in CURSOR_CASES:
        lua.append("kilo.api.set_lines(0, kilo.api.line_count(), TEN)")
        lua.append(f"kilo.api.set_cursor({{{r}, {c}}})")
        lua.append(f"kilo.api.set_lines({s}, {e}, {lua_list(lines)})")
        lua.append("note('cursor', kilo.api.get_cursor()[1], kilo.api.get_cursor()[2], rows())")
    noted, _, _, _ = run_init("09.03", "\n".join(lua) + "\n", "\n".join(FIVE) + "\n")
    return noted


# ------------------------------------------------------------------ 09.04: captures

REF_PATCH = [
    STACK_PATCH[0],
    ("    int n = lua_gettop(L), i, status, nret;\n",
     "    int n = lua_gettop(L), i, status, nret;\n" + tracer("entry|%s", "f->name")
     + '\n    figsDump(L,"dispatch entry");\n'),
    ("        v.u.function = luaL_ref(L,LUA_REGISTRYINDEX);\n",
     "        v.u.function = luaL_ref(L,LUA_REGISTRYINDEX);\n" + tracer("ref|%d", "v.u.function") + "\n"),
    ("void scriptUnref(int ref) {\n", "void scriptUnref(int ref) {\n" + tracer("unref|%d", "ref") + "\n"),
    ("    lua_rawgeti(L,LUA_REGISTRYINDEX,c->ref);\n",
     "    lua_rawgeti(L,LUA_REGISTRYINDEX,c->ref);\n" + tracer("call|%d", "c->ref") + '\n    figsDump(L,"rawgeti");\n'),
]
REF_PATCH_KILO = [
    ("    if (*slot) scriptUnref(*slot);\n    *slot = args[1].u.function;\n",
     "    { int old_ = *slot;\n    if (*slot) scriptUnref(*slot);\n    *slot = args[1].u.function;\n"
     + tracer("slot|%d|%d|%d", "key", "old_", "*slot") + " }\n"),
]
DEMO_LUA = "local x = 1\nprint(x)\n"                    # 09.04's demo.lua
REF_AGAIN = "kilo.keymap.set('<C-d>', print)"           # Ctrl-D mapped again, as 09.04 does it


def project2(at, patches):
    """project() with patches to more than one file: {name: patch}."""
    key = (at, "+", tuple((n, tuple(p)) for n, p in sorted(patches.items())))
    if key not in _built:
        d = os.path.join(tempfile.mkdtemp(prefix="kilo-figs09a-"), at)
        subprocess.run([os.path.join(ROOT, "learn"), "files", "kilo", "--at", at, d], check=True,
                       stdout=subprocess.DEVNULL)
        for name, patch in patches.items():
            path = os.path.join(d, name)
            with open(path) as f:
                src = f.read()
            for old, new in patch:
                assert src.count(old) == 1, (at, name, old)
                src = src.replace(old, new)
            with open(path, "w") as f:
                f.write(src)
        TK.supply_lua(d)
        subprocess.run(["make", "-s"], cwd=d, check=True)
        _built[key] = d
    return _built[key]


@functools.lru_cache(None)
def capture0904():
    """The project at 09.04 with REF_PATCH and REF_PATCH_KILO, the lesson's init.lua (Ctrl-D, Ctrl-T,
    Ctrl-S) on its demo.lua, 8 x 72: Ctrl-D; then at the prompt Ctrl-D mapped again (REF_AGAIN). The
    trace, the screen after Ctrl-D, SCRIPT_LUA's lines, and --api-info at 09.04."""
    init = lesson_init("09.04")
    in_lesson("09.04", "printf 'local x = 1\\nprint(x)\\n' > build/at/kilo/09.04/demo.lua")
    in_lesson("09.04", f"Map Ctrl-D again, `{REF_AGAIN}`, and the same line says `5 6 7`: the new reference was "
                       "made, 7, before the old, 4, was given back")
    root = project2("09.04", {"script.c": REF_PATCH, "kilo.c": REF_PATCH_KILO})
    t = core.TestContext(TRACK, TRACK.lessons[0], root=root)
    try:
        tpath = os.path.join(t.tmp, "trace.txt")
        env = dict(os.environ, KILO_TRACE=tpath)
        ed = TK.edit(t, DEMO_LUA, name="demo.lua", rows=8, cols=72, init=init, env=env)
        at_start = trace_lines(tpath)
        ed.keys(ctrl("d"))
        doubled = Shot(ed)
        after_key = trace_lines(tpath)
        ed.keys(ctrl("e"), REF_AGAIN, ENTER)
        again = trace_lines(tpath)
    finally:
        t.cleanup()
    assert doubled.lines[:3] == ["local x = 1", "local x = 1", "print(x)"] and doubled.cursor == (0, 0), doubled.lines
    in_lesson("09.04", doubled.lines[6])
    with open(os.path.join(project("09.04"), "script.c")) as f:
        src = f.read()
    lua_on_top = src[src.index("static const char SCRIPT_LUA[] ="):]
    lua_on_top = lua_on_top[:lua_on_top.index(";\n")]
    lua_lines = [eval(s) for s in re.findall(r'^\s*("(?:[^"\\]|\\.)*")', lua_on_top, re.M)]
    info = subprocess.run([os.path.join(project("09.04"), "kilo"), "--api-info"], capture_output=True,
                          text=True, check=True).stdout.split("\n")[:-1]
    return {"start": at_start, "key": after_key[len(at_start):], "again": again[len(after_key):],
            "doubled": doubled, "lua": "".join(lua_lines).split("\n"), "info": info}


# ------------------------------------------------------------------ 09.05: captures

# A scratch copy of kilo.c at 09.05 that notes, in $KILO_TRACE, each key read (its code, and the tick
# then), each event fired or skipped (and the tick), editorAfterKey()'s look at the tick and what it
# noted, and in a save the rows before and after BufWritePre, the string's length and the write.
EVENT_PATCH = [
    ('    editorEvent("BufWritePre");\n    char *buf = editorRowsToString(&len);\n',
     "    { int j_; for (j_ = 0; j_ < E.numrows; j_++)" + tracer("row|%d|%s", "j_", "E.row[j_].chars") + " }\n"
     '    editorEvent("BufWritePre");\n'
     "    { int j_; for (j_ = 0; j_ < E.numrows; j_++)" + tracer("trimmed|%d|%s", "j_", "E.row[j_].chars") + " }\n"
     "    char *buf = editorRowsToString(&len);\n" + tracer("string|%d|%lld", "len", "E.changedtick") + "\n"),
    ("    if (write(fd,buf,len) != len) goto writeerr;\n",
     "    if (write(fd,buf,len) != len) goto writeerr;\n" + tracer("write|%d", "len") + "\n"),
    ("    int c = editorFed != -1 ? editorFed : editorReadKey(fd);\n",
     "    int c = editorFed != -1 ? editorFed : editorReadKey(fd);\n"
     + tracer("key|%d|%d|%lld", "c", "editorFed", "E.changedtick") + "\n"),
    ("    if (editorRunning) return 0;\n    editorRunning = event;\n",
     "    if (editorRunning) {" + tracer("skip|%s|%lld", "event", "E.changedtick") + " return 0; }\n"
     + tracer("fire|%s|%lld", "event", "E.changedtick") + "\n    editorRunning = event;\n"),
    ('    if (tick != -1 && tick != E.changedtick) editorEvent("TextChanged");\n',
     tracer("look|%lld|%lld", "tick", "E.changedtick")
     + '\n    if (tick != -1 && tick != E.changedtick) editorEvent("TextChanged");\n'),
    ("    tick = E.changedtick;\n", "    tick = E.changedtick;\n" + tracer("noted|%lld", "tick") + "\n"),
]
NOTES05 = "hello world  \nsecond line\t\n"              # 09.05's notes.txt
BANG = ("kilo.api.create_autocmd('TextChanged', function() local l = kilo.api.get_lines(0, 1)[1] "
        "kilo.api.set_lines(0, 1, {l .. '!'}) end)")    # 09.05's TextChanged function that changes the text


def run0905(keys):
    """The project at 09.05 with EVENT_PATCH, the lesson's init.lua, on its notes.txt, 8 x 72; keys
    typed one by one (a str: one key; a tuple: several, waited for once). A Shot before and after
    each, the trace from the first key on, the file after."""
    in_lesson("09.05", "printf 'hello world  \\nsecond line\\t\\n' > build/at/kilo/09.05/notes.txt")
    init = lesson_init("09.05")
    with context("09.05", EVENT_PATCH, "kilo.c") as t:
        tpath = os.path.join(t.tmp, "trace.txt")
        env = dict(os.environ, KILO_TRACE=tpath)
        ed = TK.edit(t, NOTES05, name="notes.txt", rows=8, cols=72, init=init, env=env)
        shots = [Shot(ed)]
        start = len(trace_lines(tpath))
        for k in keys:
            ed.keys(*k) if isinstance(k, tuple) else ed.keys(k)
            shots.append(Shot(ed))
        trace = trace_lines(tpath)[start:]
        with open(ed.path, newline="") as f:
            saved = f.read()
    return shots, [line.split("|") for line in trace], saved


def per_key(trace):
    """The trace cut at each key the main loop read: [{"key", "tick", "fired": [(event, tick)], "look",
    "noted", "lines"}], what each key's work and the look after it did."""
    out = []
    for p in trace:
        if p[0] == "key":
            out.append({"key": int(p[1]), "tick": int(p[3]), "fired": [], "look": None, "noted": None, "lines": []})
        elif out:
            cur = out[-1]
            cur["lines"].append(p)
            if p[0] == "fire":
                cur["fired"].append((p[1], int(p[2])))
            elif p[0] == "look":
                cur["look"] = (int(p[1]), int(p[2]))
            elif p[0] == "noted":
                cur["noted"] = int(p[1])
    return out


@functools.lru_cache(None)
def capture0905save():
    """The lesson's a, space, then Ctrl-S."""
    shots, trace, saved = run0905(["a", " ", ctrl("s")])
    keys = per_key(trace)
    assert [k["key"] for k in keys] == [ord("a"), ord(" "), 19], keys
    in_lesson("09.05", "The file on disk is `a hello world` and `second line`, 26 bytes")
    assert saved == "a hello world\nsecond line\n" and shots[-1].lines[-1] == "5 words", (saved, shots[-1].lines)
    s = keys[2]
    rows = [p[2] for p in s["lines"] if p[0] == "row"]
    trimmed = [p[2] for p in s["lines"] if p[0] == "trimmed"]
    string = [p for p in s["lines"] if p[0] == "string"][0]
    write_ = [p for p in s["lines"] if p[0] == "write"][0]
    return {"key": s, "rows": rows, "trimmed": trimmed, "string": (int(string[1]), int(string[2])),
            "write": int(write_[1]), "shot": shots[-1], "before": shots[-2], "saved": saved,
            "noted_before": keys[1]["noted"]}


@functools.lru_cache(None)
def capture0905tick():
    """The lesson's file and init.lua: a, Right, Enter (in the middle of the row)."""
    shots, trace, _ = run0905(["a", RIGHT, ENTER])
    keys = per_key(trace)
    assert len(keys) == 3, keys
    return {"keys": keys, "shots": shots}


@functools.lru_cache(None)
def capture0905nest():
    """The lesson's file and init.lua, BANG made at the prompt, then x and y."""
    in_lesson("09.05", "`" + BANG + "`")
    shots, trace, _ = run0905([(ctrl("e"), BANG, ENTER), "x", "y"])
    keys = per_key(trace)
    assert shots[1].lines[-1] == "3", shots[1].lines
    return {"keys": keys, "shots": shots}


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


def code_lines(at, name, *wanted):
    """Each wanted piece of C, checked to be in the file `name` of the project at `at` (so a figure
    cannot show code the project does not have)."""
    with open(os.path.join(project(at), name)) as f:
        src = f.read()
    for w in wanted:
        assert w in src, (at, name, w)
    return list(wanted)


def stack(f, x, ybot, slots, w=180, h=28, gap=4, changed=(), size=11, sub=10, empty="empty"):
    """Lua's stack as C sees it: slots [(type, what)] bottom first, a box each from ybot upwards,
    the index from the bottom on the left (1, 2, ...) and from the top on the right (-1, ...).
    changed: indexes (from 1) drawn in the accent. Returns the y of the top."""
    n = len(slots)
    if not n:
        f.rect(x, ybot - h, w, h, "m f", 4, dash=True)
        f.text(x + w / 2, ybot - h / 2 + 4, empty, "tm", sub, "middle")
        return ybot - h
    for k, (typ, what) in enumerate(slots, 1):
        y = ybot - k * (h + gap) + gap
        acc = k in changed
        f.rect(x, y, w, h, "a af" if acc else "s f", 4)
        f.text(x + 8, y + h / 2 + 3.5, typ, "ta" if acc else "tm", sub)
        f.text(x + w - 8, y + h / 2 + 4, what, "ta" if acc else "t", size, "end", 700 if acc else 600, mono=True)
        f.text(x - 8, y + h / 2 + 4, str(k), "t", size, "end", 600, mono=True)
        f.text(x + w + 8, y + h / 2 + 4, str(k - n - 1), "tm", size, weight=None, mono=True)
    return ybot - n * (h + gap) + gap


# ------------------------------------------------------------------ 09.01

def stack0901():
    cap = capture0901stack()
    st, shot = cap["stacks"], cap["shot"]
    line = "1+1"
    load = 'luaL_loadbuffer(L,lua_tostring(L,1),lua_rawlen(L,1),"=lua")'
    code = code_lines("09.01", "script.c", "lua_settop(L,0);", 'lua_pushfstring(L,"return %s;",line);', load,
                      "lua_remove(L,1);", "lua_call(L,0,LUA_MULTRET);", 'lua_getglobal(L,"print");',
                      "lua_insert(L,1);", "lua_call(L,n,0);", "return 0;", "status = lua_pcall(L,1,0,0);")
    assert st["protected before"] == [("function", "C"), ("light userdata", "")], st["protected before"]
    assert st["entry"] == [("light userdata", "")] and st["settop"] == []
    assert st["pushfstring"] == [("string", "return 1+1;")]
    assert st["loadbuffer"] == [("string", "return 1+1;"), ("function", "Lua")]
    assert st["remove"] == [("function", "Lua")] and st["call chunk"] == [("integer", "2")]
    assert st["insert"] == [("function", "C:print"), ("integer", "2")]
    assert st["print tolstring"] == [("integer", "2"), ("light userdata", ""), ("string", "2")]
    assert st["call print"] == [] and st["protected after"] == []
    assert shot.lines[-1] == "2"

    def slot(typ, val):
        what = {("light userdata", ""): f'the line "{line}"', ("function", "Lua"): "the chunk",
                ("function", "C:print"): "print"}.get((typ, val))
        if what is None:
            what = f'"{val}"' if typ == "string" else val
        typ = {"function": "function (Lua)" if val == "Lua" else "function (C)"}.get(typ, typ)
        return typ, what

    def slots(name):
        return [slot(t, v) for t, v in st[name]]

    f = F9("f0901a", "Lua's stack in scriptEvalIn() as kilo at 09.01 runs the line 1+1 typed at Ctrl-E: empty; the "
           "compiled chunk; its result, 2; print under the 2, which reads it as the text \"2\"; empty again", 316)
    notes(f, 24, 22, "kilo at 09.01: Ctrl-E, then 1+1 and Enter. scriptProtected() pushed scriptEvalIn and the line "
          "and called lua_pcall(L,1,0,0); this is the stack inside it, after each call.", 104, "tm", 11, 15)
    SX, BOT, SW = 52, 256, 170
    f.text(SX + SW / 2, 166, "scriptEvalIn's stack", "t", 12, "middle", 700)
    f.text(SX - 8, BOT + 16, "from the bottom", "tm", 9.5, "middle")
    f.text(SX + SW + 14, BOT + 16, "from the top", "tm", 9.5, "middle")
    CX, CS = 280, 9.2
    frames = [
        ("Inside lua_pcall(), scriptEvalIn finds the typed line at index 1, a light userdata, and empties its "
         "stack: lua_settop(L, 0).",
         slots("settop"), (), code[:1], f'it began with one value: the line "{line}" (a light userdata)'),
        ('lua_pushfstring() pushes "return 1+1;", luaL_loadbuffer() compiles it and pushes the chunk, a Lua '
         "function, on top of it; lua_remove(L, 1) takes the string out from under the chunk.",
         slots("remove"), (1,), code[1:4], 'the string "return 1+1;" was under it until lua_remove(L,1)'),
        ("lua_call(L, 0, LUA_MULTRET) pops the chunk and runs it: its one result, the integer 2, is left at "
         "index 1, which is also -1, the top.",
         slots("call chunk"), (1,), code[4:5], "the chunk is gone; what it returned is in its place"),
        ("lua_getglobal() pushes print, and lua_insert(L, 1) moves it under the 2; lua_call(L, 1, 0) calls it. "
         'Inside print, luaL_tolstring() reads the 2 as the text "2", which goes to the message line.',
         slots("insert"), (1,), code[5:8], None),
        ("lua_call() popped print and its argument: the stack is empty, as scriptProtected() left it, and "
         "lua_pcall() gives back 0, LUA_OK. The message line shows 2.",
         slots("call print"), (), code[7:10], "lua_pcall() returns LUA_OK: no error on the stack"),
    ]
    for k, (cap_, sl, changed, lines, note) in enumerate(frames):
        with steps.step(f, cap_):
            stack(f, SX, BOT, sl, w=SW, changed=changed, empty="empty: lua_gettop(L) is 0")
            f.text(CX, 66, "what ran", "tm", 10.5)
            y = 86
            for c in lines:
                f.bar(CX - 4, y - 12, len(c) * cwid(CS) + 8, 16, "af", 3)
                mono(f, CX, y, c, "ta", CS, 600)
                y += 20
            if note:
                notes(f, CX, 166, note, 52, "tm", 10.5, 14)
            if k == 3:
                # print's own frame: its argument, luaL_Buffer's placeholder, the text
                ps = [slot(t, v) for t, v in st["print tolstring"]]
                ps[1] = ("light userdata", "the buffer")
                f.text(CX + 160, 166, "inside print", "t", 12, "middle", 700)
                stack(f, CX + 70, BOT, ps, w=180, h=24, changed=(3,), size=10.5, sub=9.5)
            if k >= 3:
                f.text(24, 302, "the message line:", "tm", 10.5)
                f.rect(118, 288, 60, 20, "s fs", 4)
                mono(f, 126, 302, shot.lines[-1], "t", 11, 600)
    return f


def protected_call0901():
    cap = capture0901error()
    shot = cap["shot"]
    f = F9("f0901b", "The same init.lua with an error, run two ways: through lua_pcall(), as kilo is built, the error "
           "comes back as a message and the file opens; through lua_call(), Lua panics, kilo aborts, and the "
           "terminal is left raw", 416)
    f.text(24, 22, "kilo at 09.01 on notes.txt, a terminal 8 x 80, and an init.lua with a typo in its second line",
           "tm", 11)
    f.rect(24, 34, 240, 44, "s fs", 6)
    for k, text in enumerate(INIT_ERROR):
        mono(f, 34, 52 + k * 17, text, "t", 10.5)
    f.text(272, 60, "init.lua", "tm", 10.5)
    # above: lua_pcall, as kilo is built
    f.text(24, 104, "lua_pcall(L,1,0,0)", "t", 12, weight=700, mono=True)
    f.text(24, 120, "as kilo is built", "tm", 10.5)
    notes(f, 180, 104, "It gives back 2, LUA_ERRRUN, with the message on the stack; scriptReport() puts its first "
          "line in the message line and pops it. The file is open and kilo goes on.", 76, "t", 10.5, 14)
    cw, rh = 5.6, 13
    screen(f, 31, 152, shot, cw, rh, 80, cursor=True)
    # below: lua_call
    Y = 284
    f.line(24, Y - 12, 616, Y - 12, "m", dash=True)
    f.text(24, Y + 8, "lua_call(L,1,0)", "ta", 12, weight=700, mono=True)
    f.text(24, Y + 24, "the same error, unprotected", "tm", 10.5)
    words = wrap(cap["panic"], 72)
    f.rect(180, Y - 6, 436, 12 + 15 * len(words), "s fs", 6)
    for k, text in enumerate(words):
        mono(f, 188, Y + 10 + k * 15, text, "ta" if k == 0 else "t", 9.6)
    y = Y + 12 + 15 * len(words) + 14
    notes(f, 180, y, "Lua's panic function wrote this line, then abort() ended kilo before its first screen: "
          f"exit status {cap['status']}, signal 6, SIGABRT. No file was shown.", 76, "t", 10.5, 14)
    f.text(180, y + 40, "stty -a after it:", "tm", 10.5)
    mono(f, 272, y + 40, " ".join(cap["modes"]), "ta", 9.6, 600)
    f.text(180, y + 58, "raw mode is still on: nothing ran disableRawMode().", "t", 10.5)
    return f


def spaced(f, x, y, s, cls="t", size=10, weight=None):
    """s in monospace with each trailing space drawn as a small open box, and a tab as \\t: bytes a
    reader must see at the end of a row. Returns the x past it."""
    cw = cwid(size)
    trail = len(s.rstrip(' \t"'))           # a closing quote after them leaves them trailing
    for i, ch in enumerate(s):
        if ch == " " and i >= trail:
            x0 = x + i * cw + cw * 0.18
            f.path(f"M{fmt(x0)} {fmt(y - 2.5)} L{fmt(x0)} {fmt(y)} L{fmt(x0 + cw * 0.64)} {fmt(y)} "
                   f"L{fmt(x0 + cw * 0.64)} {fmt(y - 2.5)}", "m")
        elif ch == "\t":
            f.text(x + i * cw, y, "\\t", "tm", size * 0.8, mono=True)
    k = 0
    for word in re.findall(r"[^ \t]+|[ \t]+", s):
        if word[0] not in " \t":
            f.text(x + k * cw, y, word, cls, size, weight=weight, mono=True)
        k += len(word)
    return x + len(s) * cw


# ------------------------------------------------------------------ 09.02

API_INFO = re.compile(r"^(\w+)\((.*)\)(?: -> (\w+))?  -- (.*)$")


def table0902():
    cap = capture0902()
    info, full = cap["info"], cap["full"]
    entry = code_lines("09.02", "kilo.c", '{"get_lines", {API_INTEGER,API_INTEGER}, {"start","end"}, 2, API_LINES, '
                       'apiGetLines,', '"the rows [start, end), counted from 0"},')
    rows = [API_INFO.match(line).groups() for line in info]
    assert all(rows) and rows[1][0] == "get_lines"
    in_notes("(no Lua is started for it: the table is C)", "The API as built")
    f = F9("f0902a", "The API's table in kilo.c at 09.02: the entry for get_lines, its fields, and what kilo "
           "--api-info prints for each of the six entries", 316)
    f.text(24, 20, "kilo.c at 09.02: an entry of the table const ApiFunc API[], the one for get_lines", "tm", 11)
    size = 9.6
    cw = cwid(size)
    x0, y1 = 34, 80
    f.rect(24, y1 - 16, 556, 42, "s fs", 6)
    line1 = "    " + entry[0]
    mono(f, x0, y1, line1, "t", size)
    mono(f, x0, y1 + 17, "     " + entry[1], "t", size)
    fields = [('"get_lines"', "the name a script calls"), ("{API_INTEGER,API_INTEGER}", "the arguments' types"),
              ('{"start","end"}', "their names"), ("2,", "count"), ("API_LINES", "the result"),
              ("apiGetLines", "the C function")]
    for k, (tok, label) in enumerate(fields):
        at = line1.index(tok)
        n = len(tok.rstrip(","))
        a, b = x0 + at * cw, x0 + (at + n) * cw
        f.brace_h(a, b, y1 - 20, "a", up=True)
        f.text((a + b) / 2, y1 - 30 - (12 if k == 3 else 0), label, "ta", 9.5, "middle", 600)
    f.brace_h(x0 + 5 * cw, x0 + (5 + len(entry[1]) - 2) * cw, y1 + 23, "a")
    f.text(x0 + 5 * cw, y1 + 40, "what it does, for --api-info", "ta", 9.5, weight=600)
    # what --api-info prints
    f.text(24, 152, "kilo --api-info at 09.02: the table printed, a line per entry, no Lua started", "tm", 11)
    cols = [(24, "name"), (124, "arguments"), (304, "returns"), (372, "what it does")]
    for x, h in cols:
        f.text(x, 172, h, "tm", 9.5)
    for k, (name, args, ret, what) in enumerate(rows):
        y = 191 + k * 18
        if name == "get_lines":
            f.bar(18, y - 13, 604, 18, "af", 3)
        cls = "ta" if name == "get_lines" else "t"
        mono(f, 24, y, name, cls, 9.6, 700 if name == "get_lines" else 600)
        mono(f, 124, y, args or "", cls, 9.6)
        mono(f, 304, y, ret or "(none)", cls if ret else "tm", 9.6)
        f.text(372, y, what, "t" if name == "get_lines" else "tm", 9.5)
    in_notes(f"{len(full)} C functions in a table")
    f.text(24, 306, f"By 09.09 the same table has {len(full)} entries, and --api-info prints {len(full)} lines.",
           "tm", 10.5)
    return f


def dispatch0902():
    cap = capture0902()
    tr, shot = cap["trace"], cap["shot"]
    rec = {}
    for line in tr:
        p = line.split("|")
        rec.setdefault(p[0], []).append(p[1:])
    assert stack_of("dispatch entry|" + "|".join(rec["dispatch entry"][0]))[1] == [("integer", "0"), ("integer", "2")]
    checks = rec["check"]
    assert checks == [["1", "start", "integer", "number"], ["2", "end", "integer", "number"]], checks
    takes = rec["take"]
    assert takes == [["1", "integer", "0"], ["2", "integer", "2"]], takes
    assert rec["ret"] == [["lines", "2"]]
    lines = [r[1] for r in rec["retline"]]
    assert lines == NOTES_TXT.split("\n")[:2], lines
    pushed = stack_of("pushed|" + "|".join(rec["pushed"][0]))[1]
    assert pushed == [("integer", "0"), ("integer", "2"), ("table", "2")], pushed
    code_lines("09.02", "script.c", "lua_pushcclosure(L,scriptDispatch,1);", "ret = f->fn(args,n,&err);",
               "status = lua_pcall(L,1,nret,0);", "apiFree(&ret);")
    f = F9("f0902b", "kilo.api.get_lines(0, 2) through the one dispatcher: two Lua numbers, checked against the "
           "entry's types, made into ApiValues for apiGetLines, the lines it returns, and a Lua table of them on "
           "the stack", 318)
    f.text(24, 20, "kilo at 09.02 on notes.txt, this line typed at Ctrl-E; the steps of scriptDispatch() for get_lines",
           "tm", 11)
    mono(f, 24, 38, GET_LINES, "t", 10, 600)
    # the entry, the dispatcher's upvalue: the same in every frame
    EX, EY, EW = 236, 52, 168
    f.rect(EX, EY, EW, 58, "s fs", 6)
    f.text(EX + EW / 2, EY + 15, "upvalue 1: the entry", "tm", 9.5, "middle")
    mono(f, EX + 10, EY + 32, "get_lines", "t", 10.5, 700)
    mono(f, EX + 10, EY + 48, "integer, integer -> lines", "t", 9)
    SX, BOT, SW = 52, 282, 150
    f.text(SX + SW / 2, 136, "the dispatcher's stack", "t", 11.5, "middle", 700)
    RX = 272

    def apivalue(x, y, typ, what, acc=True, w=150):
        f.rect(x, y, w, 26, "a af" if acc else "s f", 4)
        f.text(x + 8, y + 17, typ, "ta" if acc else "tm", 9.5, mono=True)
        f.text(x + w - 8, y + 17, what, "ta" if acc else "t", 10.5, "end", 700, mono=True)

    two = [("integer", "0"), ("integer", "2")]
    frames = [
        ("kilo.api.get_lines is scriptDispatch, with the entry for get_lines as its upvalue. Called with 0 and 2, "
         "its stack holds the two Lua values; the entry says it takes two integers.", two, (1, 2), "values"),
        ("The checks, before anything else: 2 arguments, as the entry says; each a Lua number with no fraction, "
         "so an integer. A wrong count or type would be a Lua error here, and get_lines would never run.",
         two, (), "checks"),
        ("scriptTake() makes each argument an ApiValue of the entry's type, and the dispatcher calls the C "
         "function: apiGetLines(args, 2, &err). It knows nothing of Lua.", two, (), "apivalues"),
        ("apiGetLines returns an ApiValue of type lines: two strings it allocated, copies of rows 0 and 1, which "
         "the dispatcher will free.", two, (), "ret"),
        ("scriptPushIn(), in a protected call of its own, makes them a Lua table of two strings on the stack; "
         "apiFree() frees the C copy; the dispatcher returns 1, and the script gets the table.",
         two + [("table", "2")], (3,), "table"),
    ]
    for cap_, sl, changed, what in frames:
        with steps.step(f, cap_):
            disp = [(t, v if t != "table" else "{2 strings}") for t, v in sl]
            stack(f, SX, BOT, disp, w=SW, changed=changed, size=10.5, sub=9.5)
            if what == "values":
                f.path(f"M{SX + SW + 30} {BOT - 40} C {SX + SW + 50} {BOT - 80}, {EX - 30} {EY + 40}, {EX - 2} {EY + 36}",
                       "m", arrow=True)
                notes(f, RX, 160, "n = lua_gettop(L): 2. The entry is the light userdata in the closure's upvalue: "
                      "the same C function serves every name in kilo.api.", 48, "t", 10.5, 15)
            if what == "checks":
                f.text(RX, 152, "scriptCheck(), argument by argument", "tm", 10.5)
                rows = [("count", "2 arguments", "expected 2", "yes")]
                rows += [(f"{c[0]} ({c[1]})", f"a Lua {c[3]}, 0" if c[0] == "1" else f"a Lua {c[3]}, 2",
                          f"expected {c[2]}", "yes") for c in checks]
                for k, (a, b, c, d) in enumerate(rows):
                    y = 176 + k * 26
                    f.rect(RX, y - 15, 330, 22, "a af", 4)
                    f.text(RX + 8, y, a, "ta", 10, weight=700)
                    f.text(RX + 92, y, b, "t", 10)
                    f.text(RX + 200, y, c, "t", 10, mono=True)
                    f.text(RX + 322, y, d, "ta", 10, "end", 700)
            if what == "apivalues":
                f.text(RX, 152, "ApiValue args[2], from scriptTake()", "tm", 10.5)
                for k, (_, typ, val) in enumerate(takes):
                    apivalue(RX, 162 + k * 32, "API_" + typ.upper(), val)
                f.line(RX + 158, 190, RX + 186, 190, "a", arrow=True)
                mono(f, RX + 192, 194, "apiGetLines(args,2,&err)", "ta", 9.6, 700)
                f.text(RX, 244, "kilo.c's function: rows and bytes, no Lua", "tm", 10.5)
            if what == "ret":
                f.text(RX, 152, "ApiValue ret: API_LINES, count 2", "tm", 10.5)
                for k, s in enumerate(lines):
                    f.rect(RX, 162 + k * 30, 200, 24, "a af", 4)
                    f.text(RX + 8, 178 + k * 30, f"[{k}]", "ta", 9.5, mono=True)
                    spaced(f, RX + 34, 178 + k * 30, s, "ta", 10.5, 700)
                f.text(RX, 236, "copies, allocated by apiGetLines: the dispatcher frees them", "tm", 10.5)
            if what == "table":
                f.text(RX, 152, "returned to the script", "tm", 10.5)
                f.rect(RX, 162, 236, 56, "a af", 6)
                mono(f, RX + 10, 182, "t[1]", "ta", 10, 700)
                spaced(f, RX + 50, 182, '"' + lines[0] + '"', "ta", 10)
                mono(f, RX + 10, 204, "t[2]", "ta", 10, 700)
                mono(f, RX + 50, 204, '"' + lines[1] + '"', "ta", 10)
                f.text(RX, 244, "table.concat of it, in the message line", "tm", 10.5)
                f.rect(RX, 252, 236, 22, "s fs", 4)
                mono(f, RX + 8, 267, shot.lines[-1], "t", 10)
    return f


def generator0902():
    in_lesson("09.02", "its build reads the declarations in src/nvim/api/*.h")
    for phrase in ("src/gen/gen_api_dispatch.lua reads the api headers", "nlua_api_<name>(lua_State *lstate)",
                   'put into `vim.api` by `lua_setfield(lstate, -2, "api");`', "src/gen/gen_api_metadata.lua packs",
                   '"Wrong number of arguments"', "kilo writes its table by hand, and --api-info prints text",
                   "a generated table serving Lua, msgpack-RPC and --api-info", "**nvim_buf_set_lines** (src/nvim/api/buffer.c)",
                   "Print msgpack-encoded |api-metadata| and exit"):
        in_notes(phrase)
    code_lines("09.02", "kilo.c", "const ApiFunc API[] = {", "int apiInfo(void) {", "static ApiValue apiGetLines(")
    code_lines("09.02", "script.c", "static int scriptDispatch(lua_State *L) {")
    f = F9("f0902c", "Neovim generates its API's table from the C declarations and serves it three ways, Lua, RPC "
           "and --api-info; kilo writes its table by hand and serves it two ways, Lua and --api-info", 330)
    f.text(24, 20, "Neovim v0.12.6, from its sources; kilo at 09.02", "tm", 11)

    def box(x, y, w, h, title, sub, cls="s f", tcls="t"):
        f.rect(x, y, w, h, cls, 6)
        f.text(x + w / 2, y + 18, title, tcls, 11.5, "middle", 700)
        for k, s in enumerate(sub):
            f.text(x + w / 2, y + 34 + k * 13, s, "tm", 9.5, "middle", mono=s.startswith(("src/", "nlua", "const", "api",
                                                                                        "script", "kilo.c", "msgpack")))

    def down(x, y0, y1, label=None):
        f.line(x, y0 + 1, x, y1 - 2, "s", arrow=True)
        if label:
            f.text(x + 8, (y0 + y1) / 2 + 4, label, "tm", 9.5)

    # Neovim
    NX = 24
    f.text(NX, 46, "Neovim", "t", 13, weight=700)
    box(NX + 36, 56, 280, 48, "the C declarations", ["src/nvim/api/*.h: functions on typed Objects"])
    down(NX + 176, 104, 126, "read at build time")
    box(NX + 36, 126, 280, 48, "the generator", ["src/gen/gen_api_dispatch.lua"], "a af", "ta")
    for x in (NX + 60, NX + 176, NX + 292):
        f.line(NX + 176, 175, x, 204, "a", arrow=True)
    f.text(NX + 186, 192, "writes", "ta", 9.5)
    ways = [("Lua: vim.api", ["nlua_api_<name>"]), ("RPC", ["the msgpack-RPC", "handlers"]),
            ("--api-info", ["the metadata,", "msgpack"])]
    for k, (t_, sub) in enumerate(ways):
        box(NX + k * 118, 206, 110, 60, t_, sub)
    # kilo
    KX = 412
    f.text(KX, 46, "kilo", "t", 13, weight=700)
    box(KX, 56, 204, 48, "the C functions", ["kilo.c: apiGetLines, ..."])
    down(KX + 102, 104, 126, "listed by hand")
    box(KX, 126, 204, 48, "the table, in kilo.c", ["const ApiFunc API[]"], "a af", "ta")
    for x in (KX + 50, KX + 154):
        f.line(KX + 102, 175, x, 204, "a", arrow=True)
    box(KX, 206, 98, 60, "Lua: kilo.api", ["made when Lua", "starts"])
    box(KX + 106, 206, 98, 60, "--api-info", ["text: apiInfo()"])
    f.line(394, 40, 394, 276, "m", dash=True)
    notes(f, 24, 296, "Neovim's one table serves Lua, other programs over RPC, and --api-info. A function added to "
          "src/nvim/api/ is in all three; one added to kilo.c is in neither until its line is in the table.",
          110, "tm", 10.5, 15)
    return f


# ------------------------------------------------------------------ 09.03

def set_lines0903():
    noted = capture0903()
    sets = [n for n in noted if n[0] == "set"]
    assert len(sets) == len(SET_CASES)
    in_lesson("09.03", "kilo.api.set_lines(0, 1, {'a', 'b', 'c\\nd'})")
    in_lesson("09.03", "lua:1: set_lines: a line cannot hold a newline (line 3)")
    in_lesson("09.03", "`set_lines(1, 3, {'X', 'Y'})` replaces b and c: a change.")
    code_lines("09.03", "kilo.c", "for (j = end-1; j >= start; j--) editorDelRow(j);",
               "for (j = 0; j < n; j++) editorInsertRow(start+j,line[j].s,line[j].len);")
    f = F9("f0903a", "set_lines(start, end, lines) on the same five rows, four times: a change, an insert, a delete, "
           "and a call refused before anything changed", 292)
    f.text(24, 20, "kilo at 09.03: each call on the same five rows, and the rows after it", "tm", 11)
    BX, AX, RW, RH, Y0 = 60, 420, 150, 24, 84
    f.text(BX, 72, "before", "tm", 10.5)
    f.text(AX, 72, "after", "tm", 10.5)

    def rowbox(x, y, k, s, cls):
        f.rect(x, y, RW, RH - 4, cls, 4)
        f.text(x - 8, y + 14, str(k), "tm", 9.5, "end", mono=True)
        mono(f, x + 8, y + 14, s, "ta" if cls.startswith("a") else "t", 10.5, 600 if cls.startswith("a") else None)

    for k, s in enumerate(FIVE):
        rowbox(BX, Y0 + k * RH, k, s, "s f")
    for (title, s, e, lines), (_, ok, err, after) in zip(SET_CASES, sets):
        after = after.split("|")
        shown = "{" + ", ".join("'" + x.replace("\n", "\\n") + "'" for x in lines) + "}"
        call = f"set_lines({s}, {e}, {shown})"
        if title == "refused":
            bad = next(i for i, x in enumerate(lines, 1) if "\n" in x)
            cap_ = (f"{call}: line {bad} holds a newline. Everything is checked before anything changes, so the call "
                    f"fails with \"{err}\" and the five rows are as they were.")
        elif not lines:
            cap_ = f"{call}: no lines, so rows {s} and {e - 1} are deleted and what was below them moves up."
        elif s == e:
            cap_ = f"{call}: an empty range, so nothing is deleted; the line goes in before row {s}."
        else:
            cap_ = f"{call}: rows {s} and {e - 1} are deleted, then the two lines put in where they were."
        with steps.step(f, cap_):
            if s < e:
                f.path(f"M{BX + RW + 8} {Y0 + s * RH} L{BX + RW + 14} {Y0 + s * RH} L{BX + RW + 14} "
                       f"{Y0 + e * RH - 4} L{BX + RW + 8} {Y0 + e * RH - 4}", "a")
            else:
                f.line(BX - 4, Y0 + s * RH - 2, BX + RW + 14, Y0 + s * RH - 2, "a")
            f.text(BX + RW + 20, Y0 + (s + e) * RH / 2 + 2, f"[{s}, {e})", "ta", 10, weight=700, mono=True)
            f.text(315, 46, title, "ta" if title != "refused" else "t", 12, "middle", 700)
            mono(f, 315 - len(call) * cwid(9.4) / 2, 64, call, "t", 9.4, 600)
            if title == "refused":
                f.line(262, 150, 372, 150, "s", arrow=True)
                notes(f, 262, 176, err, 24, "ta", 10, 14)
                assert ok == "false" and after == FIVE
                for k, x in enumerate(after):
                    rowbox(AX, Y0 + k * RH, k, x, "s f")
            else:
                f.line(262, 150, 372, 150, "a", arrow=True)
                assert ok == "true"
                new = set(range(s, s + len(lines)))
                for k, x in enumerate(after):
                    rowbox(AX, Y0 + k * RH, k, x, "a af" if k in new else "s f")
                f.text(AX, Y0 + len(after) * RH + 14, f"{len(after)} rows", "tm", 10)
    f.text(24, 276, "Rows count from 0 and a range [start, end) holds start but not end. Built from editorDelRow() and "
           "editorInsertRow().", "tm", 10.5)
    return f


def cursor_rule0903():
    noted = capture0903()
    curs = [n for n in noted if n[0] == "cursor"]
    block = flat(notes_section("09.03 Changing the text from a script: set_lines"))
    for ((r, c), s, e, lines, (r2, c2)), got in zip(CURSOR_CASES, curs):
        assert (int(got[1]), int(got[2])) == (r2, c2), got
        shown = "{" + ",".join(f"'{x}'" for x in lines) + "}"
        assert f"({r},{c}) {s},{e},{shown} -> ({r2},{c2})" in block, (r, c, s, e)
    in_notes("Neovim's fix_cursor keeps a cursor inside the replaced range on the same line number")
    f = F9("f0903b", "Where set_lines leaves the cursor: below the range it keeps its line, which moves by the change "
           "in the count; inside it, it goes to the range's new last row if it was below it; above, it stays", 312)
    f.text(24, 20, "kilo at 09.03 on ten rows, line0 to line9: the cursor put with set_cursor, then set_lines, then "
           "get_cursor", "tm", 11)
    titles = ["below the range", "inside the range", "above the range"]
    rh = 15
    for p, (((r, c), s, e, lines, (r2, c2)), got, title) in enumerate(zip(CURSOR_CASES, curs, titles)):
        x0 = 24 + p * 206
        after = got[3].split("|")
        shown = "{" + ", ".join(f"'{x}'" for x in lines) + "}"
        f.text(x0, 48, title, "ta", 12, weight=700)
        mono(f, x0, 66, f"set_lines({s}, {e}, {shown})", "t", 9.2, 600)
        size = 9.5
        cw = cwid(size)
        for col, rows_, cur, hi in ((0, TEN, (r, c), set(range(s, e))), (1, after, (r2, c2), set(range(s, s + len(lines))))):
            x = x0 + 4 + col * 100
            f.text(x, 88, "before" if col == 0 else "after", "tm", 9.5)
            for k, line in enumerate(rows_):
                y = 104 + k * rh
                if k in hi:
                    f.bar(x - 3, y - 11, 6 * cw + 6, rh - 1, "af", 2)
                mono(f, x, y, line, "ta" if k in hi else "t", size)
                if col == 0:
                    f.text(x - 6, y, str(k), "tm", 8.5, "end", mono=True)
            cy = 104 + cur[0] * rh
            f.rect(x + cur[1] * cw - 0.5, cy - 10, cw + 1, rh - 3, "a", 1)
            f.text(x, 270, f"({cur[0]}, {cur[1]})", "ta" if col else "t", 10.5, weight=700, mono=True)
        f.line(x0 + 66, 266, x0 + 98, 266, "a", arrow=True)
    notes(f, 24, 290, "Inside the range, column 4 was past the end of 'y', so it is cut to 1. Neovim's "
          "nvim_buf_set_lines leaves a cursor inside the range on its own line number (fix_cursor).", 112, "tm", 10.5,
          14)
    return f


# ------------------------------------------------------------------ 09.04

def reference0904():
    cap = capture0904()
    st, key, again, shot = cap["start"], cap["key"], cap["again"], cap["doubled"]
    slots_ = [("<C-d>", 4), ("<C-t>", 20), ("<C-s>", 19)]
    for k, (name, code) in enumerate(slots_):
        assert st[4 * k:4 * k + 4] == ["entry|set_keymap", f"dispatch entry|2|string:{name}|function:Lua",
                                       f"ref|{4 + k}", f"slot|{code}|0|{4 + k}"], st
    assert key[0] == "call|4" and stack_of(key[1])[1] == [("light userdata", ""), ("function", "Lua")], key
    assert again[:5] == ["entry|set_keymap", "dispatch entry|2|string:<C-d>|function:C:print", "ref|7", "unref|4",
                         "slot|4|4|7"], again
    in_lesson("09.04", "With this init file it says `4 5 6`: the three mappings")
    code_lines("09.04", "script.c", "v.u.function = luaL_ref(L,LUA_REGISTRYINDEX);",
               "lua_rawgeti(L,LUA_REGISTRYINDEX,c->ref);", "if (S.L) luaL_unref(S.L,LUA_REGISTRYINDEX,ref);")
    code_lines("09.04", "kilo.c", "if (*slot) scriptUnref(*slot);", "*slot = args[1].u.function;")
    with open(os.path.join(ROOT, "tracks", "kilo", "lua", "src", "lua.h")) as fh:
        lh = fh.read()
    assert "#define LUA_RIDX_MAINTHREAD\t1" in lh and "#define LUA_RIDX_GLOBALS\t2" in lh
    in_lesson("09.04", "`typedef int LuaRef;` in src/nvim/types_defs.h")
    f = F9("f0904a", "A Lua function kept by C: luaL_ref puts it in Lua's registry under an integer, kilo keeps the "
           "integer in its table of keys, the key fetches the function by it, and mapping the key again gives it "
           "back", 318)
    notes(f, 24, 20, "kilo at 09.04 with this lesson's init.lua (Ctrl-D, Ctrl-T, Ctrl-S) on demo.lua; Ctrl-D, then "
          f"{REF_AGAIN} at the prompt", 108, "tm", 11, 15)
    SX, SW = 40, 150
    GX, GW = 236, 176
    KX, KW = 456, 160
    PITCH, RY = 26, 90
    f.text(SX + SW / 2, 66, "a stack", "t", 11.5, "middle", 700)
    f.text(GX + GW / 2, 66, "Lua's registry", "t", 11.5, "middle", 700)
    f.text(GX + GW / 2, 80, "a Lua table: integer -> value", "tm", 9.5, "middle")
    f.text(KX + KW / 2, 66, "kilo's table of keys", "t", 11.5, "middle", 700)
    f.text(KX + KW / 2, 80, "editorKeymap[], in kilo.c", "tm", 9.5, "middle")

    def registry(entries, acc=(), gone=()):
        """[(integer, what)] after Lua's own 1 and 2 (lua.h: LUA_RIDX_MAINTHREAD, LUA_RIDX_GLOBALS)."""
        ys = {}
        for k, (i, what) in enumerate([(1, "the main thread"), (2, "the globals")] + entries):
            y = RY + k * PITCH
            ys[i] = y + 11
            a, g = i in acc, i in gone
            f.rect(GX, y, GW, 22, "a af" if a else ("m f" if g else "s f"), 4, dash=g)
            f.text(GX + 10, y + 15, str(i), "ta" if a else ("tm" if g or i <= 2 else "t"), 10.5, weight=700, mono=True)
            f.text(GX + 28, y + 15, what, "ta" if a else ("tm" if g or i <= 2 else "t"), 10)
        return ys

    def keytable(refs, acc=None):
        for k, (name, code) in enumerate(slots_):
            y = RY + k * PITCH
            a = name == acc
            ref = refs.get(name)
            f.rect(KX, y, KW, 22, "a af" if a else "s f", 4)
            f.text(KX + 10, y + 15, f"[{code}] {name}", "ta" if a else "t", 10, mono=True)
            f.text(KX + KW - 10, y + 15, f"ref {ref}" if ref else "0, none", "ta" if a else ("t" if ref else "tm"),
                   10.5 if ref else 9.5, "end", 700 if ref else None, mono=bool(ref))

    d_fn, t_fn, s_fn = (4, "Ctrl-D's function"), (5, "Ctrl-T's function"), (6, "Ctrl-S's function")
    fn_slots = [("string", '"<C-d>"'), ("function", "fn")]
    frames = [
        ("kilo.keymap.set('<C-d>', fn) calls set_keymap: on the dispatcher's stack, the key's name and the "
         "function, a Lua value that C has no type for.",
         "the dispatcher's", fn_slots, (2,), ([], ()), ({}, None)),
        ("scriptTake() pushes the function again, and luaL_ref(L, LUA_REGISTRYINDEX) pops it into the registry "
         "under a free integer and returns it: 4, an int that C can keep.",
         "the dispatcher's", fn_slots, (), ([d_fn], (4,)), ({}, None)),
        ("apiSetKeymap() stores 4 in Ctrl-D's slot, 4, since Ctrl-D is byte 4. The init file's next two mappings do "
         "the same: Ctrl-T's function is 5, in slot 20, and Ctrl-S's is 6, in slot 19.",
         None, [], (), ([d_fn, t_fn, s_fn], ()), ({"<C-d>": 4, "<C-t>": 5, "<C-s>": 6}, "<C-d>")),
        ("Ctrl-D pressed: scriptCall(4) runs scriptCallIn, whose lua_rawgeti(L, LUA_REGISTRYINDEX, 4) pushes the "
         "function back onto its stack; lua_call() runs it, and the line is doubled.",
         "scriptCallIn's", [("light userdata", "the call"), ("function", "fn")], (2,), ([d_fn, t_fn, s_fn], (4,)),
         ({"<C-d>": 4, "<C-t>": 5, "<C-s>": 6}, "<C-d>")),
        (f"{REF_AGAIN} at the prompt: print is kept first, as 7, then apiSetKeymap() gives 4 back with luaL_unref. "
         "Nothing holds Ctrl-D's old function now, and 4 is free for the next luaL_ref.",
         None, [], (), ([(4, "free: given back"), t_fn, s_fn, (7, "print")], (7,)),
         ({"<C-d>": 7, "<C-t>": 5, "<C-s>": 6}, "<C-d>")),
    ]
    for k, (cap_, whose, sl, changed, (entries, acc), (refs, kacc)) in enumerate(frames):
        with steps.step(f, cap_):
            if sl:
                f.text(SX + SW / 2, 82, whose + " stack", "tm", 9.5, "middle")
                stack(f, SX, 164, sl, w=SW, h=24, changed=changed, size=10.5, sub=9.5)
            ys = registry(entries, acc, (4,) if k == 4 else ())
            keytable(refs, kacc)
            if k == 1:
                f.path(f"M{SX + SW + 28} 124 C {SX + SW + 50} 124, {GX - 30} {ys[4]}, {GX - 3} {ys[4]}", "a", arrow=True)
                f.text(GX - 4, ys[4] + 30, "luaL_ref: 4", "ta", 10.5, "end", 700, mono=True)
            if k == 2:
                f.path(f"M{GX + GW + 3} {ys[4]} C {GX + GW + 24} {ys[4]}, {KX - 24} {RY + 11}, {KX - 3} {RY + 11}",
                       "a", arrow=True)
            if k == 3:
                f.path(f"M{GX - 3} {ys[4]} C {GX - 30} {ys[4]}, {SX + SW + 50} 124, {SX + SW + 28} 124", "a", arrow=True)
                f.text(GX - 4, ys[4] + 30, "lua_rawgeti", "ta", 10.5, "end", 700, mono=True)
                f.text(24, 236, "the screen after Ctrl-D", "tm", 10.5)
                f.rect(24, 244, 200, 44, "s fs", 4)
                for j in range(3):
                    mono(f, 32, 257 + j * 13, shot.lines[j], "t", 9.6)
            if k == 4:
                mono(f, 24, 140, "luaL_unref(L,", "ta", 10, 700)
                mono(f, 24, 156, "LUA_REGISTRYINDEX,4)", "ta", 10, 700)
    f.text(24, 306, "Neovim keeps the same integer, a LuaRef (typedef int LuaRef;), made by luaL_ref in nlua_ref().",
           "tm", 10.5)
    return f


def layers0904():
    cap = capture0904()
    lua = cap["lua"]
    info = cap["info"]
    keymap = lua[lua.index("function kilo.keymap.set(keys, fn)"):lua.index("function kilo.keymap.set(keys, fn)") + 4]
    for phrase in ("`vim.api.nvim_set_keymap(m, lhs, rhs, opts)`", "**vim.keymap.set is Lua** (runtime/lua/vim/keymap.lua)",
                   "nlua_api_<name>(lua_State *lstate)", 'put into `vim.api` by `lua_setfield(lstate, -2, "api");`',
                   "**nvim_buf_set_lines** (src/nvim/api/buffer.c)"):
        in_notes(phrase)
    code_lines("09.04", "kilo.c", "static ApiValue apiSetKeymap(", "static ApiValue apiGetLines(")
    f = F9("f0904b", "Three layers: kilo.c's C functions; kilo.api, made from the table, one dispatcher for all; and "
           "kilo.keymap.set and kilo.lines, written in Lua on top. Beside each, Neovim's name for the same layer", 334)
    f.text(24, 20, "kilo at 09.04, and Neovim v0.12.6", "tm", 11)
    f.text(24, 44, "kilo", "t", 12.5, weight=700)
    f.text(420, 44, "Neovim", "t", 12.5, weight=700)
    bands = [
        ("written in Lua", "in script.c, run when the state is made", keymap,
         ["vim.keymap.set: Lua,", "runtime/lua/vim/keymap.lua;", "it calls vim.api.nvim_set_keymap"]),
        ("kilo.api, made from the table", f"{len(info)} names, each scriptDispatch() and its entry",
         ["kilo.api.set_keymap(key, fn)", "kilo.api.get_lines(start, end)", "..."],
         ["vim.api: a C binding for each,", "nlua_api_<name>, generated", "from the declarations"]),
        ("the editor's C functions", "kilo.c: rows, keys, the cursor; no Lua",
         ["apiSetKeymap(args, nargs, &err)", "apiGetLines(args, nargs, &err)", "..."],
         ["src/nvim/api/*.c:", "nvim_buf_set_lines in buffer.c,", "on typed Objects"]),
    ]
    for k, (title, sub, code, nv) in enumerate(bands):
        y = 54 + k * 88
        top = k == 0
        f.rect(24, y, 380, 78, "a af" if top else "s f", 8)
        f.text(36, y + 18, title, "ta" if top else "t", 12, weight=700)
        f.text(36, y + 32, sub, "tm", 9.5)
        for j, c in enumerate(code[:3]):
            mono(f, 36, y + 46 + j * 11, c, "ta" if top else "t", 8.6)
        f.rect(420, y, 196, 78, "s fs", 8)
        for j, s_ in enumerate(nv):
            f.text(430, y + 20 + j * 16, s_, "t" if j == 0 else "tm", 10.5 if j == 0 else 10,
                   weight=600 if j == 0 else None)
        if k < 2:
            f.line(214, y + 79, 214, y + 86, "s", arrow=True)
    notes(f, 24, 326, "Each layer calls only the one under it. A function added in Lua needs no C and no compile.",
          110, "tm", 10.5, 14)
    return f


# ------------------------------------------------------------------ 09.05

def save_events0905():
    cap = capture0905save()
    s, rows, trimmed, (slen, stick), wlen = cap["key"], cap["rows"], cap["trimmed"], cap["string"], cap["write"]
    saved, shot = cap["saved"], cap["shot"]
    fired = [(e, t) for e, t in s["fired"] if e != "KeyPress"]
    assert fired == [("BufWritePre", 4), ("BufWritePost", 8), ("TextChanged", 8)], fired
    assert rows == ["a hello world  ", "second line\t"] and trimmed == ["a hello world", "second line"]
    assert slen == wlen == len(saved) == 26 and stick == 8 and s["look"] == (4, 8) and cap["noted_before"] == 4
    code_lines("09.05", "kilo.c", 'editorEvent("BufWritePre");', 'editorEvent("BufWritePost");',
               "char *buf = editorRowsToString(&len);", 'editorSetStatusMessage("%d bytes written on disk", len);')
    init = lesson_init("09.05").split("\n")
    trim = init[init.index("kilo.api.create_autocmd('BufWritePre', function()"):][:6]
    assert trim[-1] == "end)"
    f = F9("f0905a", "One Ctrl-S, in order: BufWritePre, whose function trims two rows; the rows made into one "
           "string; the write; BufWritePost; then, after the key's work, TextChanged, since the tick moved", 316)
    f.text(24, 20, "kilo at 09.05 with this lesson's init.lua, on notes.txt after a and a space are typed; then Ctrl-S",
           "tm", 11)
    f.rect(24, 32, 400, 16 + 12.5 * len(trim), "s fs", 6)
    for k, line in enumerate(trim):
        mono(f, 32, 47 + k * 12.5, line, "t", 8.6)
    notes(f, 438, 46, "and on TextChanged, the words of the file, in the message line", 30, "tm", 10, 14)
    Y = 150
    f.line(24, Y, 616, Y, "m")
    marks = [(48, "Ctrl-S", "t", f"tick {s['tick']}"), (150, "BufWritePre", "ta", f"tick {fired[0][1]}"),
             (262, "the string", "t", f"{slen} bytes"), (360, "write()", "t", f"{wlen} bytes"),
             (464, "BufWritePost", "ta", f"tick {fired[1][1]}"), (574, "TextChanged", "ta", f"tick {s['look'][0]} -> 8")]
    for x, name, cls, sub in marks:
        f.circle(x, Y, 4.5, "a fa" if cls == "ta" else "s f")
        f.text(x, Y - 12, name, cls, 11, "middle", 700)
        f.text(x, Y + 18, sub, "tm", 9.5, "middle")
    f.text(574, Y + 32, "after the key's work", "tm", 9, "middle")

    def rowset(x, y, title, rs, acc):
        f.text(x, y, title, "tm", 9.5)
        for k, r in enumerate(rs):
            f.rect(x, y + 6 + k * 22, 166, 18, "a af" if acc else "s f", 3)
            spaced(f, x + 6, y + 19 + k * 22, r, "ta" if acc else "t", 9.6)
    rowset(24, 210, "the rows when BufWritePre fires", rows, False)
    rowset(224, 210, f"after the trim: tick {stick}", trimmed, True)
    f.line(194, 235, 220, 235, "a", arrow=True)
    f.text(424, 210, f"notes.txt on disk, {len(saved)} bytes", "tm", 9.5)
    f.rect(424, 216, 166, 40, "s fs", 3)
    for k, r in enumerate(saved.split("\n")[:-1]):
        mono(f, 430, 229 + k * 16, r + "\\n", "t", 9.6)
    f.text(24, 286, "the message line after the key:", "tm", 10.5)
    f.rect(190, 273, 80, 20, "s fs", 4)
    mono(f, 198, 287, shot.lines[-1], "t", 10.5, 600)
    f.text(280, 287, f"TextChanged's count, over the save's \"{wlen} bytes written on disk\"", "tm", 10.5)
    return f


def tick0905():
    cap = capture0905tick()
    keys, shots = cap["keys"], cap["shots"]
    assert [k["key"] for k in keys] == [ord("a"), 1001, 13], keys
    ticks = [keys[0]["tick"]] + [k["noted"] for k in keys]
    assert ticks == [2, 3, 3, 5], ticks
    fired = [any(e == "TextChanged" for e, _ in k["fired"]) for k in keys]
    assert fired == [True, False, True] and shots[3].lines[:2] == ["ah", "ello world"], (fired, shots[3].lines)
    in_notes("`E.changedtick++;` after `E.dirty++` in editorInsertRow, editorDelRow, editorRowInsertChar, "
             "editorRowAppendString, editorRowDelChar, and after the cut in editorInsertNewline", "Hooks in core code")
    f = F9("f0905b", "Keys on a time line and the changed tick under them: a letter +1, an arrow +0, Enter in the "
           "middle of a row +2; TextChanged fires after each key that moved it, and only there", 318)
    f.text(24, 20, "kilo at 09.05 with this lesson's init.lua, on notes.txt: a, Right, then Enter", "tm", 11)
    names = ["a", "Right", "Enter"]
    why = ["editorRowInsertChar", "nothing changes", "editorInsertRow, and the cut"]
    X0, DX, Y = 150, 180, 112
    f.line(24, Y, 616, Y, "m")
    f.text(24, Y - 36, "keys", "tm", 9.5)
    f.text(24, Y + 34, "tick", "tm", 9.5)
    f.text(70, Y + 34, str(ticks[0]), "t", 13, "middle", 700, mono=True)
    f.text(70, Y + 50, "the file read:", "tm", 8.5, "middle")
    f.text(70, Y + 62, "two rows put in", "tm", 8.5, "middle")
    for i in range(3):
        x = X0 + i * DX
        tick = ticks[i + 1]
        moved = fired[i]
        f.rect(x - 34, Y - 52, 68, 24, "s f", 5)
        f.text(x, Y - 36, names[i], "t", 11, "middle", 700)
        f.circle(x, Y, 4.5, "s f")
        f.text(x, Y + 34, str(tick), "ta" if moved else "t", 13, "middle", 700, mono=True)
        delta = tick - ticks[i]
        f.text(x, Y + 50, f"+{delta}", "ta" if moved else "tm", 10, "middle", 700 if moved else None)
        f.text(x, Y + 64, why[i], "tm", 8.5, "middle")
        if moved:
            f.line(x, Y + 72, x, Y + 79, "a")
            f.rect(x - 44, Y + 80, 88, 22, "a af", 11)
            f.text(x, Y + 95, "TextChanged", "ta", 10, "middle", 700)
        sh = shots[i + 1]
        for j in range(2):
            mono(f, x - 50, Y + 124 + j * 13, sh.lines[j], "t", 9)
        mono(f, x - 50, Y + 154, sh.lines[-1], "tm", 9)
    f.text(24, Y + 124, "rows 0, 1", "tm", 9)
    f.text(24, Y + 154, "message", "tm", 9)
    notes(f, 24, 294, "TextChanged is fired by editorAfterKey(), at the top of main()'s loop after the key's work: once "
          "per key, whatever the tick went up by.", 110, "tm", 10.5, 14)
    return f


def nesting0905():
    cap = capture0905nest()
    keys, shots = cap["keys"], cap["shots"]
    x, y = keys[1], keys[2]
    assert (x["key"], y["key"]) == (ord("x"), ord("y")), keys
    tc = [[t for e, t in k["fired"] if e == "TextChanged"] for k in (x, y)]
    assert x["tick"] == 2 and x["look"] == (2, 3) and tc[0] == [3] and x["noted"] == 5, x
    assert y["tick"] == 5 and y["look"] == (5, 6) and tc[1] == [6] and y["noted"] == 8, y
    assert shots[2].lines[0] == "xhello world  !" and shots[3].lines[0] == "xyhello world  !!", shots[3].lines
    in_notes("the tick is noted after the autocommands, so a callback's own change does not fire it again")
    in_lesson("09.05", "Without the change, the same function adds one `!` for each key that changes the text.")
    f = F9("f0905c", "A TextChanged function that changes the text: the key fires it; its own change raises the tick "
           "and fires nothing; the next key fires it once more", 300)
    f.text(24, 20, "kilo at 09.05 with this lesson's init.lua, on notes.txt; at the prompt, this function; then x, y",
           "tm", 11)
    cut = BANG.index(" kilo.api.set_lines")
    f.rect(24, 30, 592, 40, "s fs", 6)
    mono(f, 32, 46, BANG[:cut], "t", 9.2)
    mono(f, 32, 61, "  " + BANG[cut + 1:], "t", 9.2)
    Y = 140
    f.line(24, Y, 616, Y, "m")
    f.text(24, Y + 26, "tick", "tm", 9.5)
    pts = [(70, 2, None), (170, 3, "x"), (290, 5, "set_lines"), (410, 6, "y"), (530, 8, "set_lines")]

    def timeline(upto, fired_at):
        for i, (px, tick, what) in enumerate(pts[:upto]):
            f.circle(px, Y, 4, "s f")
            f.text(px, Y + 26, str(tick), "t", 12, "middle", 700, mono=True)
            if what:
                f.text(px, Y - 12, what, "t", 10.5, "middle", 700, mono=what == "set_lines")
            if i in fired_at:
                f.rect(px - 44, Y + 36, 88, 20, "a af", 10)
                f.text(px, Y + 50, "TextChanged", "ta", 10, "middle", 700)

    def scr(sh):
        f.text(24, 222, "the screen's first row and its message line, after the key", "tm", 9.5)
        f.rect(24, 230, 300, 38, "s fs", 6)
        spaced(f, 32, 245, sh.lines[0], "t", 9.6)
        mono(f, 32, 260, sh.lines[-1], "t", 9.6)

    with steps.step(f, "x is typed: the tick goes from 2 to 3, and at the top of the loop TextChanged fires, once: "
                       "the word count, then this function."):
        timeline(2, {1})
        scr(shots[2])
    with steps.step(f, "The function puts row 0 back with a ! at its end: the row deleted and put in, so the tick "
                       "goes to 5. Nothing fires: the tick is noted, 5, after the functions return."):
        timeline(3, {1})
        scr(shots[2])
        notes(f, 340, 236, "its own change is not heard: editorAfterKey() notes the tick after the functions run",
              46, "ta", 10.5, 14)
    with steps.step(f, "y is typed: the tick goes to 6, TextChanged fires once more, and another ! goes in: tick 8, "
                       "and again nothing fires for that."):
        timeline(5, {1, 3})
        scr(shots[3])
        notes(f, 340, 236, "one ! for each key that changes the text", 46, "t", 10.5, 14)
    return f


FIGS = [
    ("09.01-stack", stack0901, True),
    ("09.01-protected-call", protected_call0901, False),
    ("09.02-table", table0902, False),
    ("09.02-dispatch", dispatch0902, True),
    ("09.02-generator", generator0902, False),
    ("09.03-set-lines", set_lines0903, True),
    ("09.03-cursor-rule", cursor_rule0903, False),
    ("09.04-reference", reference0904, True),
    ("09.04-layers", layers0904, False),
    ("09.05-save-events", save_events0905, False),
    ("09.05-tick", tick0905, False),
    ("09.05-nesting", nesting0905, True),
]


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
