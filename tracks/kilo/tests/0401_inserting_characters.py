"""04.01 Inserting characters

A typed character goes into the text where the cursor is, and the cursor
moves past it; past the right edge the view scrolls. Typing below the end
of the file first adds empty rows down to the cursor. A tab is a character
like any other. The status bar says (modified).
"""


def test(t):
    tr = t.track
    ed = tr.edit(t, "hello world\nab\n")
    ed.keys(tr.RIGHT * 5, ",")
    t.check(ed.line(0) == "hello, world" and ed.cursor == (0, 6), f"{ed.line(0)!r} {ed.cursor}")
    t.check("(modified)" in ed.status, f"the status bar should say (modified): {ed.status!r}")
    ed.keys(tr.DOWN, "c", tr.TAB, "d")
    t.check(ed.line(1) == "abc     d" and ed.cursor == (1, 8 + 1), f"{ed.line(1)!r} {ed.cursor}")
    # One row past the end of the file: typing there adds the row.
    ed.keys(tr.DOWN, "new")
    t.check(ed.line(2) == "new" and "3 lines" in ed.status, f"{ed.line(2)!r} {ed.status!r}")
    # Further down (Page Down puts the cursor on the bottom row): empty rows fill the gap.
    ed.keys(tr.PAGE_DOWN, "z")
    t.check(ed.cursor == (21, 1) and ed.line(21) == "z" and "22 lines" in ed.status, f"{ed.cursor} {ed.status!r}")
    ed.keys(tr.ctrl("s"))
    t.check(ed.saved() == "hello, world\nabc\td\nnew\n" + "\n" * 18 + "z\n", f"saved {ed.saved()!r}")
    ed.quit()

    # Past the right edge the view scrolls, and the cursor stays in the last column.
    ed = tr.edit(t, "")
    text = "".join(chr(ord("a") + i % 26) for i in range(85))
    ed.keys(text)
    t.check(ed.cursor == (0, 79) and ed.line(0) == text[6:], f"{ed.cursor} {ed.line(0)!r}")
    ed.keys(tr.ctrl("s"))
    t.check(ed.saved() == text + "\n", f"saved {ed.saved()!r}")
