"""Random calls of module 09's API, as Lua, for the tests of 09.08 and 09.09 (not a lesson's test).

calls(seed, n, screen) gives n lines of Lua, each one call `pcall(kilo.api.NAME, ...)` with
arguments of random count and type: mostly the right count and types, often not, and values
chosen to reach the edges (0, -1, the last row, 2^62, NaN, a newline in a line, a NUL, a key
name that is no key's, a function that fails or feeds a key...). With screen=True (in the
editor) it leaves out what would wait for the keyboard or end the run: input(), quit(),
feeding Ctrl-E or Ctrl-F, and deleting autocommand 1 (the test's own, which runs each block
on a key, as a KeyPress function that comes before any the calls make). The generator is Python's random with the seed given, so a failing
run can be repeated.
"""

import os
import random

# One report UndefinedBehaviorSanitizer makes that is not module 09's: module 06's
# editorUpdateSyntax() (upstream kilo's) does memset(row->hl, ..., 0) right after
# realloc(row->hl, 0), which on glibc frees and returns NULL, and memset() with a NULL pointer
# is undefined even for 0 bytes. The fuzz reaches it by feeding Backspace until a row is empty;
# typing does too. Changing it would change module 06's lessons, so it is named here instead
# (NOTES.md, 09, "Found on the way").
UBSAN_SUPPRESSIONS = "nonnull-attribute:editorUpdateSyntax\n"


def ubsan_options(directory):
    """UBSAN_OPTIONS for the fuzz: stop at the first report, with its stack, and the one
    suppression above (written to a file in directory)."""
    path = os.path.join(directory, "ubsan.supp")
    with open(path, "w") as f:
        f.write(UBSAN_SUPPRESSIONS)
    return f"halt_on_error=1:print_stacktrace=1:suppressions={path}"

SIGS = {
    "line_count": [], "get_lines": ["integer", "integer"], "get_cursor": [], "get_name": [],
    "is_modified": [], "message": ["string"], "set_lines": ["integer", "integer", "lines"],
    "set_cursor": ["position"], "save": [], "set_keymap": ["key", "function"], "del_keymap": ["key"],
    "feed_key": ["key"], "create_autocmd": ["event", "function"], "del_autocmd": ["integer"],
    "get_changedtick": [], "create_namespace": ["string"],
    "add_highlight": ["integer", "integer", "integer", "integer", "style"], "clear_namespace": ["integer"],
    "set_statusline": ["string"], "get_view": [], "get_size": [], "input": ["string"], "open": ["path"],
    "quit": ["boolean"],
}

INTEGERS = ["0", "1", "2", "3", "-1", "5", "7", "40", "100", "1 << 31", "1 << 62", "math.mininteger",
            "math.maxinteger", "kilo.api.line_count()", "kilo.api.line_count() - 1", "2.0"]
FLOATS = ["1.5", "0/0", "1/0", "-0.0"]
STRINGS = ['""', '"x"', '"a\\nb"', '"a\\0b"', 'string.rep("w", 300)', '"\\27[2J"', '"\\233\\200"', '"hello world"']
KEYS = ['"<C-t>"', '"<c-y>"', '"<Enter>"', '"<Up>"', '"<Down>"', '"<PageDown>"', '"<BS>"', '"<Del>"', '"x"',
        '"<"', '"<xe9>"', '"<C-s>"', '"<C-q>"', '"<F1>"', '"<C-a>"', '"<Tab>"', '"<Esc>"', '"<C-z>"', '"<C-g>"']
WAITING_KEYS = ['"<C-e>"', '"<C-f>"']
EVENTS = ['"BufReadPost"', '"BufWritePre"', '"BufWritePost"', '"TextChanged"', '"CursorMoved"', '"KeyPress"',
          '"Nope"', '"keypress"']
STYLES = ['"red"', '"bold"', '"underline"', '"reverse"', '"cyan"', '"purple"']
PATHS = ['"b.txt"', '"nope.txt"', '""', '"x.txt/y"', '"f.txt"']
LINES = ["{}", '{"a"}', '{"a", "b", "c"}', '{"x = 42", "\\t\\tint y;"}', '{"bad\\nline"}', '{"a\\0b"}',
         "{1, 2}", '{"a", nil, "c"}', '{x = "a"}', '{string.rep("long ", 50)}']
POSITIONS = ["{0, 0}", "{1, 2}", "{-1, 0}", "{0, -1}", "{kilo.api.line_count(), 0}", "{3, 100}", "{1.5, 0}",
             "{0}", "{0, 0, 0}", '{"a", 0}']
FUNCTIONS = ["function() end", "function() return true end", 'function() error("in a function") end',
             'function(k) kilo.api.set_lines(0, 0, {"from a function"}) return k == "x" end',
             'function() kilo.api.feed_key("<Down>") end', "function() kilo.api.message(kilo.api.get_name()) end",
             "function() kilo.api.add_highlight(kilo.api.create_namespace('f'), 0, 0, 3, 'red') end"]
OTHERS = ["nil", "true", "false", "{}", "coroutine.create(function() end)", "io.stdout", "print",
          "setmetatable({}, {__index = function() error('meta') end})"]

POOLS = {"integer": INTEGERS, "string": STRINGS, "key": KEYS, "event": EVENTS, "style": STYLES, "path": PATHS,
         "lines": LINES, "position": POSITIONS, "function": FUNCTIONS, "boolean": ["true", "false"]}
ANY = INTEGERS + FLOATS + STRINGS + LINES[:3] + POSITIONS[:2] + FUNCTIONS[:2] + OTHERS


def calls(seed, n, screen):
    rnd = random.Random(seed)
    names = [f for f in SIGS if not (screen and f in ("input", "quit"))]
    keys = KEYS + ([] if screen else WAITING_KEYS)
    out = []
    for _ in range(n):
        name = rnd.choice(names)
        sig = SIGS[name]
        count = len(sig) if rnd.random() < 0.75 else rnd.randint(0, 5)
        args = []
        for i in range(count):
            if i < len(sig) and rnd.random() < 0.8:
                pool = keys if sig[i] == "key" else POOLS[sig[i]]
            else:
                pool = ANY
            if screen and name == "del_autocmd":
                pool = [v for v in pool if v != "1"]    # autocommand 1 is the test's driver
            args.append(rnd.choice(pool))
        out.append(f"pcall({', '.join(['kilo.api.' + name] + args)})")
    return out
