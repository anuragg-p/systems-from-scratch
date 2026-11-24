"""09.02 The API is a table

The editor's operations are a table of C functions with typed arguments
(api.h, API in kilo.c); one dispatcher (script.c) gives each to Lua as
kilo.api.NAME, checks the count and the type of every argument against the
table before the function runs, turns Lua's values into the API's and back,
and makes a function's failure a Lua error with its name in front.
`kilo --api-info` prints the table, with no Lua involved. The first six:
line_count, get_lines, get_cursor, get_name, is_modified, message. Rows
count from 0 and a range [start, end) holds start, not end; out of range is
an error, never cut to fit.
"""

import os
import subprocess

# Every function of the finished API: (name, [(argument, type)], what it returns or None).
FUNCS = [
    ("line_count", [], "integer"), ("get_lines", [("start", "integer"), ("end", "integer")], "lines"),
    ("get_cursor", [], "position"), ("get_name", [], "string"), ("is_modified", [], "boolean"),
    ("message", [("text", "string")], None),
    ("set_lines", [("start", "integer"), ("end", "integer"), ("lines", "lines")], None),
    ("set_cursor", [("pos", "position")], None), ("save", [], "boolean"),
    ("set_keymap", [("key", "string"), ("fn", "function")], None), ("del_keymap", [("key", "string")], None),
    ("feed_key", [("key", "string")], None),
    ("create_autocmd", [("event", "string"), ("fn", "function")], "integer"),
    ("del_autocmd", [("id", "integer")], None), ("get_changedtick", [], "integer"),
    ("create_namespace", [("name", "string")], "integer"),
    ("add_highlight", [("ns", "integer"), ("row", "integer"), ("start", "integer"), ("end", "integer"),
                       ("style", "string")], None),
    ("clear_namespace", [("ns", "integer")], None), ("set_statusline", [("text", "string")], None),
    ("get_view", [], "position"), ("get_size", [], "position"), ("set_view", [("pos", "position")], None),
    ("input", [("prompt", "string")], "string"), ("open", [("path", "string")], None),
    ("quit", [("force", "boolean")], None),
]

# A good value of each type, and wrong ones with what the error says they are.
GOOD = {"integer": "0", "string": '"x"', "lines": "{}", "position": "{0, 0}",
        "function": "function() end", "boolean": "false"}
BAD = {
    "integer": [('"1"', "string"), ("1.5", "float"), ("nil", "nil"), ("{}", "table"), ("true", "boolean")],
    "string": [("5", "number"), ("nil", "nil"), ("{}", "table"), ("function() end", "function")],
    "lines": [('"x"', "string"), ("{1}", "a table with a number at 1"), ('{"a", true}', "a table with a boolean at 2"),
              ('{"a", x = "b"}', "a table that is not a list"), ('{"a", nil, "c"}', "a table that is not a list"),
              ("nil", "nil")],
    "position": [("{1}", "a table that is not {row, col}"), ("{1, 2, 3}", "a table that is not {row, col}"),
                 ("{1.5, 0}", "a table with a float at 1"), ('{0, "a"}', "a table with a string at 2"),
                 ("5", "number")],
    "function": [('"f"', "string"), ("nil", "nil"), ("{}", "table")],
    "boolean": [("nil", "nil"), ("0", "number"), ('"true"', "string")],
}


def checks():
    """[(Lua expression of the call's arguments, function, the error it must give)]."""
    out = []
    for name, args, _ in FUNCS:
        n = len(args)
        good = [GOOD[ty] for _, ty in args]
        for m, vals in ((n + 1, good + ["1"]),) + (((n - 1, good[:-1]),) if n else ()):
            out.append((name, vals, f"{name}: expected {n} argument{'' if n == 1 else 's'}, got {m}"))
        for i, (arg, ty) in enumerate(args):
            for bad, got in BAD[ty]:
                vals = good[:i] + [bad] + good[i + 1:]
                out.append((name, vals, f"{name}: argument {i + 1} ({arg}): expected {ty}, got {got}"))
    return out


def test(t):
    tr = t.track
    results = os.path.join(t.tmp, "results.txt")

    # kilo --api-info: the table, a line a function, with no editor and no Lua.
    r = subprocess.run([os.path.join(t.root, "kilo"), "--api-info"], capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, timeout=20)
    lines = r.stdout.splitlines()
    t.check(r.returncode == 0 and len(lines) == len(FUNCS), f"--api-info: {r.returncode}, {len(lines)} lines")
    for line, (name, args, ret) in zip(lines, FUNCS):
        sig = f"{name}({', '.join(f'{a}: {ty}' for a, ty in args)})" + (f" -> {ret}" if ret else "")
        t.check(line.startswith(sig + "  -- ") and len(line) > len(sig) + 6, f"--api-info: {line!r}, not {sig!r}")
    t.check(lines[1] == "get_lines(start: integer, end: integer) -> lines  -- the rows [start, end), counted from 0",
            f"{lines[1]!r}")

    # Every function, each wrong count and each wrong type: refused by the dispatcher before
    # the function runs (save, open, quit and input never run here).
    cases = checks()
    init = [f"local out = io.open({tr.lua_quote(results)}, 'w')",
            "local names = {}",
            "for name in pairs(kilo.api) do names[#names + 1] = name end",
            "table.sort(names)",
            "out:write(table.concat(names, ' '), '\\n')"]
    for name, vals, _ in cases:
        init.append(f"out:write(select(2, pcall({', '.join([f'kilo.api.{name}'] + vals)})), '\\n')")
    init += ["local ok, e = pcall(function()",
             "  return kilo.api.get_lines(0)",       # an error from a script's own call: its place in front
             "end)",
             "out:write(e, '\\n')",
             "out:close()"]
    ed = tr.edit(t, "one\n\ttwo\n\nfour\n", init="\n".join(init) + "\n", asan=True)
    with open(results) as f:
        got = f.read().split("\n")
    t.check(got[0] == " ".join(sorted(n for n, _, _ in FUNCS)), f"kilo.api holds: {got[0]}")
    for (name, vals, want), line in zip(cases, got[1:]):
        t.check(line == want, f"{name}({', '.join(vals)}): {line!r}, not {want!r}")
    t.check(got[len(cases) + 1] == f"init.lua:{len(init) - 3}: get_lines: expected 2 arguments, got 1",
            f"a script's own call: {got[len(cases) + 1]!r}")
    t.check(ed.lines[0] == "one" and ed.message.startswith("HELP:"), "and nothing ran: the file and message are as they were")

    # The six of this lesson, as a user types them at the prompt.
    def lua(line):
        ed.keys(tr.ctrl("e"), line, tr.ENTER)
        return ed.message
    t.check(lua("kilo.api.line_count()") == "4", f"{ed.message!r}")
    t.check(lua("table.concat(kilo.api.get_lines(0, 4), '|')") == "one| two||four", f"{ed.message!r}")
    t.check(lua("#kilo.api.get_lines(1, 1), #kilo.api.get_lines(4, 4)") == "0 0", f"empty ranges: {ed.message!r}")
    t.check(lua("kilo.api.get_lines(1.0, 2.0)[1] == '\\ttwo'") == "true", f"2.0 is an integer: {ed.message!r}")
    for call, said in (("get_lines(-1, 1)", "[-1, 1) is not a range of the file's 4 rows"),
                       ("get_lines(0, 5)", "[0, 5) is not a range of the file's 4 rows"),
                       ("get_lines(3, 1)", "[3, 1) is not a range of the file's 4 rows"),
                       ("get_lines(0, 1 << 62)", "[0, 4611686018427387904) is not a range of the file's 4 rows")):
        t.check(lua(f"kilo.api.{call}") == f"lua:1: get_lines: {said}", f"{call}: {ed.message!r}")
    # What get_lines gives is a copy: changing it changes nothing.
    lua("l = kilo.api.get_lines(0, 1); l[1] = 'zzz'")
    t.check(ed.lines[0] == "one" and lua("kilo.api.get_lines(0, 1)[1]") == "one", f"{ed.lines[0]!r}")
    # The cursor: a row and a byte of it, from 0 (past the tab: byte 1, screen column 8).
    t.check(lua("table.concat(kilo.api.get_cursor(), ',')") == "0,0", f"{ed.message!r}")
    ed.keys(tr.DOWN, tr.RIGHT)
    t.check(ed.cursor == (1, 8) and lua("table.concat(kilo.api.get_cursor(), ',')") == "1,1", f"{ed.message!r}")
    t.check(lua("kilo.api.get_name()") == "f.txt", f"{ed.message!r}")
    t.check(lua("kilo.api.is_modified()") == "false", f"{ed.message!r}")
    ed.keys("z")
    t.check(lua("kilo.api.is_modified()") == "true", f"{ed.message!r}")
    t.check(lua("kilo.api.message('hi\\tthere\\27[2J')") == "hi there?[2J", f"message(): {ed.message!r}")
    t.check(b"\x1b[2J" not in ed.raw, "an escape sequence from message() reached the terminal")
    ed.keys(tr.ctrl("s"))
    t.check(ed.quit() == 0, "Ctrl-Q quits")
