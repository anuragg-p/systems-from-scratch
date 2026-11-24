"""09.06 Drawing from a script: highlights and the status bar

create_namespace(name) gives a namespace's id (the same name, the same id;
"" a new one each time; at most 64). add_highlight(ns, row, start, end,
style) draws bytes [start, end) of a row in a style (red, green, yellow,
blue, magenta, cyan, bold, underline, reverse) over what the editor drew:
when it is added the row must be in the file and start not past end; when
it is drawn it is cut to the row as it then is, and to the screen. Later
ones are drawn over earlier ones; they do not move with the text;
clear_namespace(ns) removes one namespace's; at most 10000.
set_statusline(text) replaces the left part of the status bar ("" gives
the editor's own back), the row count staying on the right. get_view() and
get_size() say what the screen shows.
"""

import os

# The 09.10 proof, cut down: every number on the screen coloured, again whenever the file is
# read, the text changes or the cursor moves (the view may have scrolled).
NUMBERS = r"""
local nums = kilo.api.create_namespace('numbers')
local function paint()
  kilo.api.clear_namespace(nums)
  local top, rows = kilo.api.get_view()[1], kilo.api.get_size()[1]
  local last = math.min(top + rows, kilo.api.line_count())
  if last <= top then return end
  for i, line in ipairs(kilo.api.get_lines(top, last)) do
    for s, e in line:gmatch('()%d+()') do
      kilo.api.add_highlight(nums, top + i - 1, s - 1, e - 1, 'red')
    end
  end
end
for _, event in ipairs({'BufReadPost', 'TextChanged', 'CursorMoved'}) do
  kilo.api.create_autocmd(event, paint)
end
"""


def test(t):
    tr = t.track
    init = "ns = kilo.api.create_namespace('test')\nfunction H(...) kilo.api.add_highlight(ns, ...) end\n"
    ed = tr.edit(t, "abcdefgh\n\tx = 42;\nhello\n", init=init, asan=True)

    def lua(line):
        ed.keys(tr.ctrl("e"), line, tr.ENTER)
        return ed.message

    # Namespaces.
    t.check(lua("kilo.api.create_namespace('a') == kilo.api.create_namespace('a'), "
                "kilo.api.create_namespace('a') ~= kilo.api.create_namespace('b'), "
                "kilo.api.create_namespace('') ~= kilo.api.create_namespace('')") == "true true true", f"{ed.message!r}")
    # Errors when it is added.
    for call, said in (("H(-1, 0, 1, 'red')", "row -1 is outside the file (it has 3 rows)"),
                       ("H(3, 0, 1, 'red')", "row 3 is outside the file (it has 3 rows)"),
                       ("H(0, 5, 2, 'red')", "[5, 2) is not a range of bytes"),
                       ("H(0, -1, 2, 'red')", "[-1, 2) is not a range of bytes"),
                       ("H(0, 0, 1, 'purple')", 'unknown style "purple": red, green, yellow, blue, magenta, cyan, '
                                                'bold, underline or reverse'),
                       ("H(0, 0, 1, 'red\\0')", 'unknown style "red": red, green, yellow, blue, magenta, cyan, '
                                                'bold, underline or reverse'),
                       ("kilo.api.add_highlight(999, 0, 0, 1, 'red')", "no namespace 999"),
                       ("kilo.api.clear_namespace(0)", "no namespace 0")):
        name = "clear_namespace" if "clear_namespace" in call else "add_highlight"
        # H() is init.lua's: the error is placed in it, where it called the API.
        want = f"{'init.lua:2' if call.startswith('H(') else 'lua:1'}: {name}: {said}"
        t.check(lua(f"select(2, pcall(function() {call} end)) == {tr.lua_quote(want)}") == "true",
                f"{call}: not {want!r} (the message line holds 79 bytes of it: "
                f"{lua(f'select(2, pcall(function() {call} end))')!r})")

    # Drawn over the row: bytes [2, 5) of row 0; past a tab, bytes 5 to 7 of row 1; one cut at
    # the row's end; one that starts past it, and an empty one, draw nothing.
    lua("H(0, 2, 5, 'red') H(1, 5, 7, 'blue') H(2, 3, 100, 'green') H(2, 9, 20, 'red') H(2, 1, 1, 'red')")
    t.check([ed.painted(r) for r in range(3)] == ["ab[r:cde]fgh", "        x = [b:42];", "hel[g:lo]"],
            f"{[ed.painted(r) for r in range(3)]}")
    # Later over earlier; the styles that are not colours.
    lua("kilo.api.clear_namespace(ns) H(0, 0, 4, 'red') H(0, 2, 6, 'blue') H(2, 0, 2, 'reverse') H(2, 2, 3, 'underline')")
    t.check(ed.painted(0) == "[r:ab][b:cdef]gh" and ed.painted(2) == "[#:he]llo" and ed.under(2) == "he[_:l]lo",
            f"{ed.painted(0)!r} {ed.painted(2)!r} {ed.under(2)!r}")
    lua("H(1, 1, 2, 'bold')")
    t.check(b"\r\x1b[8C\x1b[1mx\x1b[0m" in ed.raw, "bold: ESC [ 1 m over the x, 8 cells in")
    # clear_namespace takes only its own.
    lua("other = kilo.api.create_namespace('other') kilo.api.add_highlight(other, 2, 4, 5, 'cyan') kilo.api.clear_namespace(ns)")
    t.check([ed.painted(r) for r in range(3)] == ["abcdefgh", "        x = 42;", "hell[c:o]"],
            f"{[ed.painted(r) for r in range(3)]}")
    # They do not move with the text: a row put in above, and row 2's highlight is on row 2.
    ed.keys(tr.ENTER)
    t.check([ed.painted(r) for r in range(4)] == ["", "abcdefgh", "        x =[c: ]42;", "hello"],
            f"{[ed.painted(r) for r in range(4)]}")
    ed.keys(tr.BACKSPACE)
    # At most HIGHLIGHT_MAX.
    t.check(lua("kilo.api.clear_namespace(other) for i = 1, 10001 do H(0, 0, 1, 'red') end") ==
            "init.lua:2: add_highlight: too many highlights (10000)", f"{ed.message!r}")
    t.check(lua("for i = 1, 70 do kilo.api.create_namespace('n' .. i) end") ==
            "lua:1: create_namespace: too many namespaces (64)", f"{ed.message!r}")
    lua("kilo.api.clear_namespace(ns)")
    t.check(ed.painted(0) == "abcdefgh", f"{ed.painted(0)!r}")

    # The status bar: the text on the left, the row count still on the right.
    lua("kilo.api.set_statusline('my status')")
    t.check(ed.status.startswith("my status ") and ed.status.endswith(" 1/3") and ed.reverse(22),
            f"{ed.status!r}")
    lua("kilo.api.set_statusline('a\\tb\\27[2Jc')")
    t.check(ed.status.startswith("a b?[2Jc "), f"control bytes: {ed.status!r}")
    lua("kilo.api.set_statusline(string.rep('s', 200))")
    t.check(ed.status == "s" * 76 + " 1/3", f"cut, the count kept: {ed.status!r}")
    lua("kilo.api.set_statusline('')")
    t.check(ed.status.startswith("f.txt - 3 lines"), f"the editor's own again: {ed.status!r}")
    ed.keys(tr.ctrl("s"))
    ed.quit()

    # What the screen shows: the view and its size, as the cursor and the window move.
    ed = tr.edit(t, tr.lines_of(40), asan=True)
    t.check(lua("table.concat(kilo.api.get_view(), ','), table.concat(kilo.api.get_size(), ',')") == "0,0 22,80",
            f"{ed.message!r}")
    lua("kilo.api.set_cursor({30, 3})")
    t.check(lua("table.concat(kilo.api.get_view(), ',')") == "9,0", f"{ed.message!r}")
    ed.resize(30, 100)
    t.check(lua("table.concat(kilo.api.get_size(), ',')") == "28,100", f"{ed.message!r}")
    ed.quit()
    # A long row scrolled right, and text that is not ASCII: the highlight lands on its bytes.
    ed = tr.edit(t, "x" * 100 + " tail\n\u00e9t\u00e9 x\n".encode("utf-8").decode("latin-1"), utf8=True,
                 init="ns = kilo.api.create_namespace('') kilo.api.add_highlight(ns, 0, 101, 105, 'red') "
                      "kilo.api.add_highlight(ns, 1, 6, 7, 'green')", asan=True)
    t.check(ed.painted(1) == "\u00e9t\u00e9 [g:x]", f"after two-byte characters: {ed.painted(1)!r}")
    lua("kilo.api.set_cursor({0, 104})")
    t.check(ed.painted(0) == "x" * 75 + " [r:tail]", f"scrolled: {ed.painted(0)!r}")
    ed.quit()

    # Every number on the screen coloured, as the text changes and the view moves.
    ed = tr.edit(t, tr.lines_of(40, "row {} of 40"), init=NUMBERS, asan=True)
    t.check(ed.painted(0) == "row [r:1] of [r:40]" and ed.painted(21) == "row [r:22] of [r:40]",
            f"on BufReadPost: {ed.painted(0)!r} {ed.painted(21)!r}")
    ed.keys("7 ")
    t.check(ed.painted(0) == "[r:7] row [r:1] of [r:40]", f"on TextChanged: {ed.painted(0)!r}")
    lua("kilo.api.set_cursor({30, 0})")
    t.check(ed.painted(21) == "row [r:31] of [r:40]", f"on CursorMoved, the view scrolled: {ed.painted(21)!r}")
    ed.keys(tr.ctrl("s"))
    ed.quit()

    # The finished project: drawn over module 06's colours.
    if "editorSelectSyntaxHighlight" in open(os.path.join(t.root, "kilo.c"), errors="replace").read():
        ed = tr.edit(t, "int x = 42;\n", name="t.c",
                     init="ns = kilo.api.create_namespace('') kilo.api.add_highlight(ns, 0, 0, 3, 'blue')", asan=True)
        t.check(ed.painted(0) == "[b:int] x = [r:42];", f"over module 06's colours: {ed.painted(0)!r}")
        ed.quit()
