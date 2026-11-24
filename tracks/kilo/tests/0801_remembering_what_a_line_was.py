"""08.01 Remembering what a line was

Before a row changes, kilo keeps what it was: a record of the row's text
before a change (U_CHG) or a deletion (U_DEL), or of a row inserted
(U_INS), made in the core's row functions themselves. Ctrl-Z puts the rows
back, the last record first. Reading the file is not an edit: there is
nothing to undo in a file just opened. Every kind of edit comes undone,
byte for byte, on the screen and in the file saved after.
"""


def undo_one(t, tr, text, keys, after, cursor, name="f.txt", rows=24, cols=80):
    """Open text, type keys, check the rows show `after`; Ctrl-Z: the text again, the cursor
    where it was before the edit (cursor, from 0), and the file saved is text to the byte."""
    ed = tr.edit(t, text, name=name, rows=rows, cols=cols, asan=True)
    ed.keys(*keys)
    n = len(after)
    t.check(ed.lines[:n] == after, f"{keys!r} on {text!r}: {ed.lines[:n]}, not {after}")
    ed.keys(tr.ctrl("z"))
    want = text.split("\n")[:-1] if text else []
    t.check(ed.lines[:len(want)] == [w.replace("\t", " " * 8) for w in want],
            f"undone {keys!r}: {ed.lines[:len(want) + 1]}")
    t.check(ed.cursor == cursor, f"undone {keys!r}: the cursor at {ed.cursor}, not {cursor}")
    t.check("(modified)" not in ed.status, f"undone, back to the file: {ed.status!r}")
    ed.keys(tr.ctrl("s"))
    t.check(ed.saved() == text, f"undone {keys!r}, saved: {ed.saved()!r}, not {text!r}")
    return ed


def test(t):
    tr = t.track
    text = "abc\nxyz\n"

    # Nothing to undo in a file just opened: reading it is no edit.
    ed = tr.edit(t, text, asan=True)
    ed.keys(tr.ctrl("z"))
    t.check(ed.message == "Nothing to undo" and ed.lines[:2] == ["abc", "xyz"],
            f"Ctrl-Z on a file just opened: {ed.message!r} {ed.lines[:2]}")
    t.check(ed.lines[2] == "~" and "2 lines" in ed.status, f"{ed.lines[:3]} {ed.status!r}")
    ed.quit()

    # A character typed.
    undo_one(t, tr, text, [tr.RIGHT, "X"], ["aXbc", "xyz"], (0, 1))
    # Enter at the start, in the middle and at the end of a row.
    undo_one(t, tr, text, [tr.DOWN, tr.ENTER], ["abc", "", "xyz"], (1, 0))
    undo_one(t, tr, text, [tr.DOWN, tr.RIGHT, tr.ENTER], ["abc", "x", "yz"], (1, 1))
    undo_one(t, tr, text, [tr.DOWN, tr.RIGHT * 3, tr.ENTER], ["abc", "xyz", ""], (1, 3))
    # Backspace inside a row, and at its start: the join.
    undo_one(t, tr, text, [tr.DOWN, tr.RIGHT * 2, tr.BACKSPACE], ["abc", "xz"], (1, 2))
    undo_one(t, tr, text, [tr.DOWN, tr.BACKSPACE], ["abcxyz", "~"], (1, 0))
    # Below the last row: a row is added for the cursor, then the character.
    undo_one(t, tr, text, [tr.DOWN * 2, "X"], ["abc", "xyz", "X", "~"], (2, 0))
    # Page Down on a short file leaves the cursor on the bottom line, rows below the end:
    # typing there adds the rows between, and all of them go.
    ed = undo_one(t, tr, text, [tr.PAGE_DOWN, "X"], ["abc", "xyz"] + [""] * 19 + ["X"], (21, 0))
    t.check("2 lines" in ed.status and ed.lines[2] == "~", f"rows gone: {ed.status!r} {ed.lines[2]!r}")
    # A character typed past the end of a row: the spaces that pad it go too. (The cursor
    # gets there when the window shrinks under it: it keeps its column on a shorter row.)
    long = "".join(f"{'y' * 30}\n" if i == 15 else f"r{i}\n" for i in range(20))
    ed = tr.edit(t, long, name="g.txt", asan=True)
    ed.keys(tr.DOWN * 15, tr.RIGHT * 25)
    ed.resize(8, 80)
    t.check(ed.cursor == (5, 25) and ed.line(5) == "r5", f"past the end of 'r5': {ed.cursor}")
    ed.keys("X")
    t.check(ed.line(5) == "r5" + " " * 23 + "X", f"padded: {ed.line(5)!r}")
    ed.keys(tr.ctrl("z"))
    t.check(ed.line(5) == "r5" and ed.cursor == (5, 25), f"undone: {ed.line(5)!r} {ed.cursor}")
    ed.keys(tr.ctrl("s"))
    t.check(ed.saved() == long, f"saved {ed.saved()[:40]!r}")
    ed.quit()

    # A file that is not there yet: what was typed goes, and the text is empty again.
    ed = tr.edit(t, None, name="new.txt", asan=True)
    ed.keys("hi", tr.ENTER, "yo")
    ed.keys(tr.ctrl("z"), tr.ctrl("z"), tr.ctrl("z"))
    t.check(ed.lines[0] == "~" and "0 lines" in ed.status, f"empty again: {ed.lines[:2]} {ed.status!r}")
    ed.keys(tr.ctrl("z"))
    t.check(ed.message == "Nothing to undo", f"{ed.message!r}")
    ed.quit()

    # Many edits, undone one by one to the file as it was opened.
    ed = tr.edit(t, "one\n\ttwo\nthree\n", name="h.txt", asan=True)
    ed.keys(tr.DOWN, tr.RIGHT, "A", tr.ENTER, tr.UP, tr.BACKSPACE, tr.DOWN * 2, tr.BACKSPACE, "Z")
    t.check(ed.lines[:4] == ["one     A", "two", "thZee", "~"], f"edited: {ed.lines[:4]}")
    for _ in range(20):
        ed.keys(tr.ctrl("z"))
        if ed.message == "Nothing to undo":
            break
    t.check(ed.message == "Nothing to undo", f"{ed.message!r}")
    t.check(ed.lines[:4] == ["one", "        two", "three", "~"], f"all undone: {ed.lines[:4]}")
    ed.keys(tr.ctrl("s"))
    t.check(ed.saved() == "one\n\ttwo\nthree\n", f"saved {ed.saved()!r}")
    ed.quit()

    # With module 06: the rows below a comment's opening are coloured again when the row
    # that opens it comes back. The row is deleted with Backspaces (one step), then undone.
    ed = tr.edit(t, "x = 1;\n/* a\nb\nc */\nint y;\n", name="t.c", asan=True)
    t.check(ed.painted(2) == "[c:b]", f"in the comment: {ed.painted(2)!r}")
    ed.keys(tr.DOWN, tr.RIGHT * 4, tr.BACKSPACE * 5)
    t.check(ed.lines[:2] == ["x = 1;", "b"] and ed.painted(1) == "b" and ed.painted(2) == "c */",
            f"deleted: {[ed.painted(n) for n in range(4)]}")
    ed.keys(tr.ctrl("z"))
    t.check([ed.painted(n) for n in range(5)] == ["x = [r:1];", "[c:/* a]", "[c:b]", "[c:c */]", "[g:int] y;"],
            f"undone: {[ed.painted(n) for n in range(5)]}")
    ed.keys(tr.ctrl("s"))
    ed.quit()

    # With module 07: the language server is sent the text as the undo left it.
    ed = tr.edit(t, "int x;\n", name="s.c", lsp="")
    ed.wait_received("textDocument/didOpen")
    ed.keys("y")
    ed.wait_received("textDocument/didChange")
    ed.keys(tr.ctrl("z"))
    changes = ed.wait_received("textDocument/didChange", 2)
    got = [(c["params"]["textDocument"]["version"], c["params"]["contentChanges"][0]["text"]) for c in changes]
    t.check(got == [(2, "yint x;\n"), (3, "int x;\n")], f"the server got {got}")
    ed.keys(tr.ctrl("s"))
    ed.quit()
