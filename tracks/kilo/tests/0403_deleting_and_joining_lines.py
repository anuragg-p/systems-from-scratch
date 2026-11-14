"""04.03 Deleting, and joining lines

Backspace deletes the character left of the cursor. At the start of a row
it joins the row onto the end of the one above, and the cursor goes to
where they meet, scrolling to keep it on the screen. At the very start of
the file it does nothing. In kilo, Delete and Ctrl-H do what Backspace does.
"""


def test(t):
    tr = t.track
    ed = tr.edit(t, "abcdef\nghi\n")
    ed.keys(tr.RIGHT * 3, tr.BACKSPACE)
    t.check(ed.line(0) == "abdef" and ed.cursor == (0, 2), f"{ed.line(0)!r} {ed.cursor}")
    ed.keys(tr.DEL, tr.ctrl("h"))
    t.check(ed.line(0) == "def" and ed.cursor == (0, 0), f"Delete and Ctrl-H: {ed.line(0)!r} {ed.cursor}")
    ed.keys(tr.BACKSPACE)
    t.check(ed.line(0) == "def" and ed.cursor == (0, 0), "Backspace at the start of the file does nothing")
    ed.keys(tr.DOWN, tr.BACKSPACE)
    t.check(ed.lines[:2] == ["defghi", "~"] and ed.cursor == (0, 3), f"join: {ed.lines[:2]} {ed.cursor}")
    t.check("1 lines" in ed.status, f"one row fewer: {ed.status!r}")
    ed.keys(tr.ctrl("s"))
    t.check(ed.saved() == "defghi\n", f"saved {ed.saved()!r}")
    ed.quit()

    # Joining onto a row longer than the screen: the view scrolls right, the cursor on the join.
    ed = tr.edit(t, "x" * 100 + "\nabc\n", name="g.txt")
    ed.keys(tr.DOWN, tr.BACKSPACE)
    # (The screen's last column is left out of these checks: a row as wide as the screen
    # is followed by ESC [ 0 K with the cursor still in that column, which erases it.)
    t.check(ed.cursor == (0, 79) and ed.line(0)[:79] == "x" * 79, f"{ed.cursor} {ed.line(0)[70:]!r}")
    ed.keys("|")
    t.check(ed.cursor == (0, 79) and ed.line(0)[77:79] == "x|", f"typing goes in at the join: {ed.line(0)[70:]!r}")
    ed.keys(tr.ctrl("s"))
    t.check(ed.saved() == "x" * 100 + "|abc\n", f"saved {ed.saved()[-10:]!r}")
    ed.quit()

    # At the start of the top row of a scrolled view: the view scrolls up.
    ed = tr.edit(t, tr.lines_of(40), name="h.txt")
    ed.keys(tr.DOWN * 25, tr.UP * 21, tr.BACKSPACE)
    t.check(ed.line(0) == "line 4line 5" and ed.cursor == (0, 6), f"{ed.line(0)!r} {ed.cursor}")
    # Scrolled right, Backspace at the left edge scrolls back one column.
    ed = tr.edit(t, "y" * 90 + "\n", name="i.txt")
    ed.keys(tr.RIGHT * 85, tr.LEFT * 79, tr.BACKSPACE)
    t.check(ed.cursor == (0, 0) and ed.line(0)[:79] == "y" * 79, f"{ed.cursor} {len(ed.line(0))}")
    ed.keys(tr.ctrl("s"))
    t.check(ed.saved() == "y" * 89 + "\n", f"saved {len(ed.saved())} bytes")
