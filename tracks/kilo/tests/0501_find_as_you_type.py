"""05.01 Find as you type

Ctrl-F turns the message line into a search prompt. Each key that changes
the query searches again from the top of the file: the first row holding it
goes to the top of the screen with the cursor on the match, scrolled right
if the match is past the screen's edge. Backspace edits the query; a query
with no match leaves everything where it is. Enter ends the search there.
"""


def test(t):
    tr = t.track
    text = ("alpha\nbeta\ngamma beta\n\tdelta\n" + tr.lines_of(40) + "far down: needle\n"
            + "z" * 120 + "zebra\n")
    ed = tr.edit(t, text)
    ed.keys(tr.ctrl("f"))
    t.check(ed.message == "Search:  (Use ESC/Arrows/Enter)", f"the prompt: {ed.message!r}")
    ed.keys("bet")
    t.check(ed.line(0) == "beta" and ed.cursor == (0, 0), f"'bet': {ed.line(0)!r} {ed.cursor}")
    t.check(ed.message == "Search: bet (Use ESC/Arrows/Enter)", f"{ed.message!r}")
    ed.keys("a")
    t.check(ed.line(0) == "beta" and ed.status.endswith(" 2/46"), f"'beta': {ed.line(0)!r} {ed.status!r}")
    ed.keys(tr.BACKSPACE * 4, "needle")
    t.check(ed.line(0) == "far down: needle" and ed.cursor == (0, 10), f"'needle': {ed.line(0)!r} {ed.cursor}")
    ed.keys("s")                                    # "needles": nowhere
    t.check(ed.line(0) == "far down: needle" and ed.cursor == (0, 10), "no match: nothing moves")
    ed.keys(tr.BACKSPACE, tr.ENTER)
    t.check(ed.message == "" and ed.line(0) == "far down: needle" and ed.cursor == (0, 10),
            f"Enter ends the search where it is: {ed.message!r} {ed.cursor}")
    ed.keys("X")
    t.check(ed.line(0) == "far down: Xneedle", f"typing goes in at the match: {ed.line(0)!r}")

    # A match after a tab: the cursor on the match, where the screen shows it.
    ed.keys(tr.ctrl("f"), "delta", tr.ENTER)
    t.check(ed.line(0) == "        delta" and ed.cursor == (0, 8), f"{ed.line(0)!r} {ed.cursor}")
    ed.keys("[")
    t.check(ed.line(0) == "        [delta", f"typing goes in at the match: {ed.line(0)!r}")
    # A match past the right edge: the view scrolls right to it.
    ed.keys(tr.ctrl("f"), "zebra", tr.ENTER)
    t.check(ed.cursor == (0, 79) and ed.line(0).startswith("zzzz") and ed.line(0)[79:] in ("", "z"),
            f"{ed.cursor} {ed.line(0)[-10:]!r}")
    ed.keys("_", tr.ctrl("s"))
    t.check("z" * 120 + "_zebra\n" in ed.saved(), f"typed at the match: {ed.saved()[-12:]!r}")
