"""04.02 Enter: splitting a line

Enter splits the row at the cursor: what is left of the cursor stays, the
rest becomes a new row below, and the cursor goes to the start of it. At
column 0 that inserts an empty row above; at the end of a row, an empty row
below; one row past the end of the file, it adds an empty row. On the
bottom row the view scrolls down; a view scrolled right goes back left.
"""


def test(t):
    tr = t.track
    ed = tr.edit(t, "hello world\nsecond\n")
    ed.keys(tr.RIGHT * 5, tr.ENTER)
    t.check(ed.lines[:3] == ["hello", " world", "second"] and ed.cursor == (1, 0), f"{ed.lines[:3]} {ed.cursor}")
    ed.keys(tr.ENTER)
    t.check(ed.lines[:4] == ["hello", "", " world", "second"] and ed.cursor == (2, 0), f"at column 0: {ed.lines[:4]}")
    ed.keys(tr.DOWN, tr.RIGHT * 6, tr.ENTER)
    t.check(ed.lines[:5] == ["hello", "", " world", "second", ""] and ed.cursor == (4, 0),
            f"at the end of a row: {ed.lines[:5]} {ed.cursor}")
    ed.keys(tr.DOWN, tr.ENTER)
    t.check("6 lines" in ed.status and ed.cursor == (6, 0), f"past the end: {ed.status!r} {ed.cursor}")
    ed.keys(tr.ctrl("s"))
    t.check(ed.saved() == "hello\n\n world\nsecond\n\n\n", f"saved {ed.saved()!r}")
    ed.quit()

    # On the bottom row of the screen, Enter scrolls the view.
    ed = tr.edit(t, tr.lines_of(30))
    ed.keys(tr.DOWN * 21, tr.RIGHT * 4, tr.ENTER)
    t.check(ed.cursor == (21, 0) and ed.line(21) == " 22" and ed.line(20) == "line", f"{ed.lines[19:22]} {ed.cursor}")
    t.check(ed.line(0) == "line 2", f"the view moved down one row: {ed.line(0)!r}")
    # Scrolled right, Enter brings the view back to column 0.
    ed = tr.edit(t, "x" * 100 + "tail\n", name="g.txt")
    ed.keys(tr.RIGHT * 100, tr.ENTER)
    t.check(ed.line(0)[:79] == "x" * 79 and ed.line(1) == "tail" and ed.cursor == (1, 0), f"{ed.lines[:2]} {ed.cursor}")
