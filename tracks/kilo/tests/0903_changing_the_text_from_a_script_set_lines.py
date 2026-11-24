"""09.03 Changing the text from a script: set_lines

set_lines(start, end, lines) replaces the rows [start, end) by the lines:
all or nothing (every argument is checked before the first row changes; a
line holding "\\n" is refused, any other byte taken as it is), made with
the core's own editorDelRow() and editorInsertRow(). The cursor afterwards:
below the range, on the same line; inside it, the same row or the range's
new last row, whichever is higher, or with no new rows the row that took
the range's place (the last row if none did); its column cut to the row;
the view scrolled to show it. set_cursor() refuses a place outside the
text; save() is Ctrl-S. After any script returns, the cursor is in the
text. In the finished project the change is coloured (module 06) and sent
to the language server (module 07) as a typed one is.
"""

import os

BASE = [f"line{i}" for i in range(10)]


def test(t):
    tr = t.track
    # Helpers, so that each case is one short line at the prompt: R puts the ten rows back and
    # the cursor at r, c; C says where the cursor is and what the rows are.
    init = ("BASE = {" + ",".join(f"'{l}'" for l in BASE) + "}\n"
            "function R(r, c)\n"
            "  kilo.api.set_lines(0, kilo.api.line_count(), BASE)\n"
            "  kilo.api.set_cursor({r, c})\n"
            "end\n"
            "function C()\n"
            "  return table.concat(kilo.api.get_cursor(), ',') .. ' ' ..\n"
            "         table.concat(kilo.api.get_lines(0, kilo.api.line_count()), '|')\n"
            "end\n")
    ed = tr.edit(t, "".join(l + "\n" for l in BASE), init=init, asan=True)

    def lua(line):
        ed.keys(tr.ctrl("e"), line, tr.ENTER)
        return ed.message

    def rows():
        said = lua("table.concat(kilo.api.get_lines(0, kilo.api.line_count()), '|')")
        return said.split("|") if said else []

    def case(cur, call, want_rows, want_cur):
        said = lua("R(%d, %d) kilo.api.set_lines(%s) return C()" % (cur + (call,)))
        want = ("%d,%d " % want_cur + "|".join(want_rows)).rstrip()
        t.check(said == want, f"set_lines({call}) with the cursor at {cur}: {said!r}, not {want!r}")

    L = BASE
    # Above the range: not moved. Below it: the same line.
    case((1, 3), "5, 7, {'x'}", L[:5] + ["x"] + L[7:], (1, 3))
    case((8, 2), "2, 5, {}", L[:2] + L[5:], (5, 2))
    case((8, 2), "2, 3, {'a', 'b', 'c'}", L[:2] + ["a", "b", "c"] + L[3:], (10, 2))
    # Inside it: the same row, or the new last row if that is higher; the column cut.
    case((6, 4), "3, 8, {'x', 'y'}", L[:3] + ["x", "y"] + L[8:], (4, 1))
    case((4, 3), "3, 5, {'p', 'q', 'r', 's'}", L[:3] + ["p", "q", "r", "s"] + L[5:], (4, 1))
    case((5, 4), "5, 6, {'Z'}", L[:5] + ["Z"] + L[6:], (5, 1))
    # Inside it, with no new rows: the row that took the range's place, or the last row.
    case((4, 2), "3, 6, {}", L[:3] + L[6:], (3, 2))
    case((8, 4), "7, 10, {}", L[:7], (6, 4))
    case((5, 1), "0, 10, {}", [], (0, 0))
    # At the start (a header line) and at the end; on the row past the last.
    case((2, 2), "0, 0, {'-- header'}", ["-- header"] + L, (3, 2))
    case((9, 1), "10, 10, {'end1', 'end2'}", L + ["end1", "end2"], (9, 1))
    case((10, 0), "9, 10, {'x', 'y'}", L[:9] + ["x", "y"], (11, 0))
    # An empty file: lines go in; the cursor, on the row past the last, stays past it.
    case((0, 0), "0, 10, {}", [], (0, 0))
    said = lua("kilo.api.set_lines(0, 0, {'a', 'b'})")
    t.check(rows() == ["a", "b"] and lua("table.concat(kilo.api.get_cursor(), ',')") == "2,0", f"{ed.message!r}")
    t.check("(modified)" in ed.status and ed.lines[:3] == ["a", "b", "~"], f"{ed.lines[:3]} {ed.status!r}")

    # All or nothing: an error, and not a row changed.
    lua("R(0, 0)")
    for call, said in (("0, 2, {'ok', 'bad\\nline', 'ok2'}", "a line cannot hold a newline (line 2)"),
                       ("-1, 0, {}", "[-1, 0) is not a range of the file's 10 rows"),
                       ("0, 11, {'x'}", "[0, 11) is not a range of the file's 10 rows"),
                       ("5, 3, {}", "[5, 3) is not a range of the file's 10 rows")):
        t.check(lua(f"kilo.api.set_lines({call})") == f"lua:1: set_lines: {said}", f"{call}: {ed.message!r}")
        t.check(rows() == BASE, f"set_lines({call}) changed the text")
    # Any byte but a newline is taken as it is: a NUL, a tab, a carriage return, high bytes.
    lua("kilo.api.set_lines(0, 1, {'a\\0b\\tc\\rd\\233'})")
    t.check(lua("kilo.api.get_lines(0, 1)[1] == 'a\\0b\\tc\\rd\\233'") == "true", f"{ed.message!r}")
    t.check(lua("kilo.api.save()") == "true", f"save(): {ed.message!r}")
    t.check(ed.saved() == "a\0b\tc\rd\xe9\n" + "".join(l + "\n" for l in BASE[1:]), f"{ed.saved()[:30]!r}")
    t.check("(modified)" not in ed.status, f"{ed.status!r}")

    # set_cursor: inside the text, the row past the last at column 0, nowhere else.
    for pos, said in (("-1, 0", "row -1 is outside the file (it has 10 rows)"),
                      ("11, 0", "row 11 is outside the file (it has 10 rows)"),
                      ("10, 1", "column 1 is outside row 10 (it has 0 bytes)"),
                      ("1, 6", "column 6 is outside row 1 (it has 5 bytes)"),
                      ("1, -1", "column -1 is outside row 1 (it has 5 bytes)")):
        t.check(lua(f"kilo.api.set_cursor({{{pos}}})") == f"lua:1: set_cursor: {said}", f"{pos}: {ed.message!r}")
    lua("kilo.api.set_cursor({10, 0})")
    t.check(ed.cursor == (10, 0), f"the row past the last: {ed.cursor}")
    lua("kilo.api.set_cursor({1, 5})")
    t.check(ed.cursor == (1, 5), f"{ed.cursor}")
    ed.quit()

    # The view follows: on a file of 40 rows, set_cursor far down scrolls; rows put in above
    # the cursor at the bottom of the screen push it down, and the view goes with it.
    ed = tr.edit(t, tr.lines_of(40), asan=True)
    lua("kilo.api.set_cursor({35, 2})")
    t.check(ed.cursor == (21, 2) and ed.line(21) == "line 36" and ed.status.endswith("36/40"),
            f"{ed.cursor} {ed.line(21)!r} {ed.status!r}")
    lua("kilo.api.set_cursor({0, 0})")
    ed.keys(*[tr.DOWN] * 21, tr.RIGHT)
    lua("kilo.api.set_lines(0, 0, {'a', 'b', 'c'})")
    t.check(ed.cursor == (21, 1) and ed.line(21) == "line 22" and ed.line(0) == "line 1",
            f"pushed down, the view with it: {ed.cursor} {ed.line(0)!r} {ed.line(21)!r}")
    lua("kilo.api.set_lines(0, 30, {})")
    t.check(ed.cursor == (0, 1) and ed.line(0) == "line 28", f"deleted from under it: {ed.cursor} {ed.line(0)!r}")
    ed.keys(tr.ctrl("s"))
    ed.quit()

    # After any script, the cursor is in the text: Page Down on a short file leaves it on the
    # bottom line, below the text; a script that does nothing brings it back to the row past
    # the last.
    ed = tr.edit(t, "one\ntwo\nthree\n", asan=True)
    ed.keys(tr.PAGE_DOWN)
    t.check(ed.cursor == (21, 0), f"Page Down: {ed.cursor}")
    lua("1")
    t.check(ed.cursor == (3, 0), f"after a script: {ed.cursor}")

    # save(): as Ctrl-S; false when it failed, the reason in the message line.
    lua("kilo.api.set_lines(0, 1, {'ONE'})")
    t.check(lua("print(kilo.api.save())") == "true" and ed.saved() == "ONE\ntwo\nthree\n", f"{ed.saved()!r}")
    ed.quit()
    ed = tr.edit(t, None, name="no/such/dir.txt", asan=True)
    t.check(lua("print(kilo.api.save())") == "false", f"save() of a file that cannot be written: {ed.message!r}")
    ed.quit()

    # The finished project: module 06 colours what set_lines put in.
    if "editorSelectSyntaxHighlight" in open(os.path.join(t.root, "kilo.c"), errors="replace").read():
        ed = tr.edit(t, "x\n", name="t.c", asan=True)
        lua("kilo.api.set_lines(0, 0, {'int n = 42; /* a'})")
        t.check(ed.painted(0) == "[g:int] n = [r:42]; [c:/* a]" and ed.painted(1) == "[c:x]",
                f"coloured: {ed.painted(0)!r} {ed.painted(1)!r}")
        lua("kilo.api.set_lines(0, 1, {'int n = 42;'})")
        t.check(ed.painted(1) == "x", f"the comment closed again: {ed.painted(1)!r}")
        ed.keys(tr.ctrl("s"))
        ed.quit()
    # And module 07 sends it to the language server as it sends what is typed: the scripted
    # server's tiny language makes "oops" an error, which comes back underlined.
    if os.path.exists(os.path.join(t.root, "lsp.c")):
        ed = tr.edit(t, "int a;\n", name="t.c", lsp="", asan=True)
        ed.wait_received("textDocument/didOpen")
        lua("kilo.api.set_lines(1, 1, {'\\tint oops;'})")
        changes = ed.wait_received("textDocument/didChange")
        t.check(changes[-1]["params"]["contentChanges"][0]["text"] == "int a;\n\tint oops;\n",
                f"the server got: {changes[-1]['params']}")
        ed.wait_for(lambda: "[_:" in ed.under(1), "the server's diagnostic underlined")
        t.check(ed.under(1) == "        int [_:oops];", f"{ed.under(1)!r}")
        ed.keys(tr.ctrl("s"))
        ed.quit()
