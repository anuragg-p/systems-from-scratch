"""05.02 Next match, previous match, and going back

In the search prompt, Down or Right goes on to the next row holding the
query and Up or Left back to the previous one, around the end of the file
in either direction. Escape ends the search with the cursor and the view
exactly where they were before Ctrl-F; Enter leaves them at the match.
"""


def test(t):
    tr = t.track
    text = "beta one\nnothing\ngamma beta\n" + tr.lines_of(30) + "beta last\n"
    ed = tr.edit(t, text)
    ed.keys(tr.DOWN * 25, tr.RIGHT * 4)
    before_lines, before_cursor = ed.lines[:22], ed.cursor
    t.check(before_cursor == (21, 4) and ed.line(0) == "line 2", f"start: {ed.line(0)!r} {before_cursor}")
    ed.keys(tr.ctrl("f"), "beta")
    t.check(ed.line(0) == "beta one" and ed.cursor == (0, 0), f"first match: {ed.line(0)!r} {ed.cursor}")
    ed.keys(tr.DOWN)
    t.check(ed.line(0) == "gamma beta" and ed.cursor == (0, 6), f"Down: the next: {ed.line(0)!r} {ed.cursor}")
    ed.keys(tr.RIGHT)
    t.check(ed.line(0) == "beta last", f"Right: the next: {ed.line(0)!r}")
    ed.keys(tr.DOWN)
    t.check(ed.line(0) == "beta one", f"Down at the last match: around to the first: {ed.line(0)!r}")
    ed.keys(tr.UP)
    t.check(ed.line(0) == "beta last", f"Up at the first match: around to the last: {ed.line(0)!r}")
    ed.keys(tr.LEFT)
    t.check(ed.line(0) == "gamma beta", f"Left: the previous: {ed.line(0)!r}")
    ed.keys(tr.ESC)
    t.check(ed.lines[:22] == before_lines and ed.cursor == before_cursor,
            f"Escape goes back: {ed.line(0)!r} {ed.cursor}, not {before_lines[0]!r} {before_cursor}")
    t.check(ed.message == "", f"and clears the prompt: {ed.message!r}")
    # Enter after moving between matches stays at the match.
    ed.keys(tr.ctrl("f"), "beta", tr.DOWN, tr.ENTER)
    t.check(ed.line(0) == "gamma beta" and ed.cursor == (0, 6), f"{ed.line(0)!r} {ed.cursor}")
    ed.keys("*", tr.ctrl("s"))
    t.check("gamma *beta\n" in ed.saved(), f"saved {ed.saved()[:40]!r}")
