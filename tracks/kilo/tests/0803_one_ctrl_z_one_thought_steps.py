"""08.03 One Ctrl-Z, one thought: steps

A step is a run of keys of one kind: typing (any key that types a
character), deleting (Backspace, Ctrl-H, Delete), and any other key, which
always ends the step, and whose own edits (Enter's) are a step of their
own. A word typed is one Ctrl-Z, and a run of typing on one row is one
record: a change to a row the step's last record already brings back is
not kept again. Undo puts the cursor where the step began, redo where it
ended, and the view scrolls to show it.
"""


def test(t):
    tr = t.track

    def steps(text, keys, undos, name="f.txt"):
        """Type keys on text, then Ctrl-Z once per entry of undos: the first row after each."""
        ed = tr.edit(t, text, name=name, asan=True)
        ed.keys(*keys)
        for want in undos:
            ed.keys(tr.ctrl("z"))
            t.check(ed.line(0) == want, f"{keys!r}, undone to {ed.line(0)!r}, not {want!r}")
        ed.keys(tr.ctrl("z"))
        t.check(ed.message == "Nothing to undo", f"{keys!r}: {len(undos)} steps, not more: {ed.message!r}")
        return ed

    # A word typed is one step; a word, then Backspaces, two.
    steps("\n", ["hello"], [""]).quit()
    ed = steps("\n", ["hello", tr.BACKSPACE, tr.BACKSPACE], ["hello", ""])
    ed.quit()
    # Backspace, Ctrl-H and Delete are one kind.
    steps("abcdef\n", [tr.RIGHT * 6, tr.BACKSPACE, tr.ctrl("h"), tr.DEL], ["abcdef"]).quit()
    # An arrow between two letters makes two steps; so does Ctrl-L, a key that does nothing.
    steps("\n", ["a", tr.LEFT, "b"], ["a", ""]).quit()
    steps("\n", ["ab", tr.ctrl("l"), "cd"], ["ab", ""]).quit()
    # Enter is a step of its own, between two of typing.
    ed = steps("\n", ["ab", tr.ENTER, "cd"], ["ab", "ab", ""])
    t.check(ed.lines[:2] == ["", "~"], f"{ed.lines[:2]}")
    ed.quit()
    # Tab types; so do the two bytes of a character above 127 (UTF-8): one step.
    ed = steps("\n", ["a", tr.TAB, "caf\u00e9"], [""])
    ed.keys(tr.ctrl("r"), tr.ctrl("s"))
    t.check(ed.saved() == "a\tcaf\xc3\xa9\n", f"redone and saved: {ed.saved()!r}")
    ed.quit()
    # A search ends a step.
    steps("needle\n", ["ab", tr.ctrl("f"), "ne", tr.ESC, "cd"], ["abneedle", "needle"]).quit()

    # The cursor: undo puts it where the step began, redo where it ended. Off the screen, the
    # row goes to the top line, as a search puts its match.
    text = tr.lines_of(40)
    ed = tr.edit(t, text, name="g.txt", asan=True)
    ed.keys(tr.DOWN * 29, tr.RIGHT * 2, "XY")                 # file row 30, column 2
    t.check(ed.status.endswith("30/40") and ed.line(ed.cursor[0]) == "liXYne 30", f"{ed.status!r}")
    ed.keys(tr.PAGE_UP, tr.PAGE_UP)
    t.check(ed.line(0) == "line 1", f"back at the top: {ed.line(0)!r}")
    ed.keys(tr.ctrl("z"))
    t.check(ed.line(0) == "line 30" and ed.cursor == (0, 2) and ed.status.endswith("30/40"),
            f"undone: row 30 on the top line, the cursor on it: {ed.line(0)!r} {ed.cursor} {ed.status!r}")
    ed.keys(tr.PAGE_UP, tr.PAGE_UP, tr.ctrl("r"))
    t.check(ed.line(0) == "liXYne 30" and ed.cursor == (0, 4), f"redone: {ed.line(0)!r} {ed.cursor}")
    # On the screen already, the view stays.
    ed.keys(tr.UP, tr.ctrl("z"))
    t.check(ed.line(0) == "line 29" and ed.cursor == (1, 2), f"{ed.line(0)!r} {ed.cursor}")
    ed.keys(tr.ctrl("s"))
    t.check(ed.saved() == text, "saved as it was")
    ed.quit()
    # Past the screen's width, the view scrolls right to the cursor.
    ed = tr.edit(t, "x" * 120 + "\nshort\n", name="h.txt", asan=True)
    ed.keys(tr.RIGHT * 100, "Q", tr.LEFT * 101)
    t.check(ed.cursor == (0, 0) and ed.line(0)[:79] == "x" * 79, f"{ed.cursor} {ed.line(0)[:10]!r}")
    ed.keys(tr.ctrl("z"))
    t.check(ed.cursor == (0, 79) and ed.line(0)[:79] == "x" * 79, f"undone: {ed.cursor} {ed.line(0)!r}")
    ed.keys(tr.LEFT * 79, tr.ctrl("r"))
    t.check(ed.cursor == (0, 79) and ed.line(0)[78] == "Q", f"redone: {ed.cursor} {ed.line(0)[70:]!r}")
    ed.keys(tr.ctrl("s"))
    ed.quit()

    # A run of typing on one row is one record; and typing below the last row is one too:
    # the row inserted for it brings back all that is typed on it.
    env, log = tr.undo_env(t)
    ed = tr.edit(t, "abc\nxyz\n", name="i.txt", asan=True, env=env)
    ed.keys("0123456789")
    last = tr.undo_counts(log)[-1]
    t.check((last["undo"], last["records"]) == (1, 1), f"ten characters, one step: {last}")
    ed.keys(tr.DOWN * 2, "hey there")
    last = tr.undo_counts(log)[-1]
    t.check((last["undo"], last["records"]) == (2, 2), f"below the last row, one record: {last}")
    ed.keys(tr.ctrl("z"))
    t.check(ed.lines[:3] == ["0123456789abc", "xyz", "~"], f"undone: {ed.lines[:3]}")
    ed.keys(tr.ctrl("r"))
    t.check(ed.lines[:3] == ["0123456789abc", "xyz", "hey there"], f"redone: {ed.lines[:3]}")
    # Only the step's last record is looked at: in one run of Backspaces, a row changed, joined
    # onto the row above, and that row changed again is four records, and all come undone.
    ed.keys(tr.UP, tr.LEFT * 2, tr.BACKSPACE, tr.BACKSPACE, tr.BACKSPACE)
    t.check(ed.lines[:2] == ["0123456789abyz", "hey there"], f"deleted: {ed.lines[:2]}")
    last = tr.undo_counts(log)[-1]
    t.check((last["undo"], last["records"]) == (3, 2 + 4),
            f"U_CHG of row 1, U_CHG of row 0 and U_DEL of row 1 (the join), U_CHG of row 0: {last}")
    ed.keys(tr.ctrl("z"))
    t.check(ed.lines[:3] == ["0123456789abc", "xyz", "hey there"] and ed.cursor == (1, 1),
            f"undone: {ed.lines[:3]} {ed.cursor}")
    ed.keys(tr.ctrl("z"), tr.ctrl("z"))
    t.check(ed.lines[:3] == ["abc", "xyz", "~"], f"{ed.lines[:3]}")
    ed.keys(tr.ctrl("s"))
    t.check(ed.saved() == "abc\nxyz\n", f"saved {ed.saved()!r}")
    ed.quit()
