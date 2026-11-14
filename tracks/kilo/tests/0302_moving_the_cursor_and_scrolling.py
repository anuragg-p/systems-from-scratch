"""03.02 Moving the cursor, and scrolling

The arrows move the cursor over the text: right at the end of a row goes to
the start of the next, left at the start to the end of the one above, up
and down keep the column unless the row is too short. The cursor can go one
row past the end of the file and no further. Moving past an edge of the
screen scrolls the view; Page Down and Page Up move a screenful.
"""


def test(t):
    tr = t.track
    text = "short\na much longer line\n\nend"
    ed = tr.edit(t, text)
    ed.keys(tr.RIGHT * 5)
    t.check(ed.cursor == (0, 5), f"five rights: {ed.cursor}")
    ed.keys(tr.RIGHT)
    t.check(ed.cursor == (1, 0), f"right at the end of a row goes to the next: {ed.cursor}")
    ed.keys(tr.LEFT)
    t.check(ed.cursor == (0, 5), f"left at the start goes to the end of the row above: {ed.cursor}")
    ed.keys(tr.DOWN, tr.RIGHT * 10)
    t.check(ed.cursor == (1, 15), f"down keeps the column, then ten rights: {ed.cursor}")
    ed.keys(tr.UP)
    t.check(ed.cursor == (0, 5), f"up to a shorter row: the end of it: {ed.cursor}")
    ed.keys(tr.DOWN, tr.RIGHT * 10, tr.DOWN)
    t.check(ed.cursor == (2, 0), f"down to an empty row: column 0: {ed.cursor}")
    ed.keys(tr.DOWN, tr.DOWN, tr.DOWN, tr.DOWN)
    t.check(ed.cursor == (4, 0), f"down stops one row past the end of the file: {ed.cursor}")
    t.check(ed.status.endswith("5/4"), f"the status bar counts that row too: {ed.status!r}")
    ed.keys(tr.LEFT)
    t.check(ed.cursor == (3, 3), f"left from there: the end of the last row: {ed.cursor}")
    ed.quit()

    # Scrolling: down past the bottom, right past the edge, and back.
    ed = tr.edit(t, tr.lines_of(50, "{} " + "y" * 90))
    ed.keys(tr.DOWN * 25)
    t.check(ed.cursor == (21, 0) and ed.line(0).startswith("5 "), f"25 downs: the view from file row 4, the "
                                                                  f"cursor on the last text row: {ed.line(0)[:6]!r} {ed.cursor}")
    ed.keys(tr.UP * 22)
    t.check(ed.cursor == (0, 0) and ed.line(0).startswith("4 "), f"22 ups: the top of the view: {ed.cursor}")
    ed.keys(tr.UP)
    t.check(ed.line(0).startswith("3 ") and ed.cursor == (0, 0), f"one more up scrolls: {ed.line(0)[:6]!r}")
    ed.keys(tr.RIGHT * 85)
    t.check(ed.cursor == (0, 79) and ed.line(0).startswith("yyy"), f"85 rights: scrolled right by 6: "
                                                                    f"{ed.cursor} {ed.line(0)[:6]!r}")
    ed.keys(tr.DOWN)
    t.check(ed.cursor == (1, 79), f"down keeps the column and the scroll: {ed.cursor}")
    ed.keys(tr.LEFT * 85)
    t.check(ed.cursor == (1, 0) and ed.line(1).startswith("4 "), f"back left: {ed.cursor} {ed.line(1)[:6]!r}")
    # Left at the start of the top row of a scrolled view: up a row, to its end, still on screen.
    ed.keys(tr.UP)
    ed.keys(tr.LEFT)
    t.check(ed.line(0).startswith("y") and ed.cursor == (0, 79),
            f"left at the top: the end of the row above, the view scrolled: {ed.cursor} {ed.line(0)[:6]!r}")
    t.check(ed.status.endswith("2/50"), f"cursor on file row 2: {ed.status!r}")
    # Page Down and Page Up.
    ed = tr.edit(t, tr.lines_of(100))
    ed.keys(tr.PAGE_DOWN)
    t.check(ed.cursor == (21, 0) and ed.line(0) == "line 23", f"Page Down: {ed.line(0)!r} {ed.cursor}")
    ed.keys(tr.PAGE_DOWN)
    t.check(ed.line(0) == "line 45", f"again: {ed.line(0)!r}")
    ed.keys(tr.PAGE_UP)
    t.check(ed.cursor == (0, 0) and ed.line(0) == "line 23", f"Page Up: {ed.line(0)!r} {ed.cursor}")
