"""08.02 Redo: a record that undoes itself

Applying a record puts its text back and, in the same act, takes what was
there: a U_CHG keeps the row's text from before the undo, a U_INS becomes a
U_DEL holding the row it deleted, a U_DEL a U_INS. So the step undone is
the step to redo, applied first to last, and Ctrl-R does it. Undone steps
wait on a redo stack; a new edit empties it. Undo and redo, over and over,
leave the text and the file exactly as they were.
"""


def test(t):
    tr = t.track
    text = "abc\nxyz\n"
    cases = [  # (keys, the rows after them, the cursor after them)
        ([tr.RIGHT, "X"], ["aXbc", "xyz"], (0, 2)),
        ([tr.DOWN, tr.ENTER], ["abc", "", "xyz"], (2, 0)),
        ([tr.DOWN, tr.RIGHT, tr.ENTER], ["abc", "x", "yz"], (2, 0)),
        ([tr.DOWN, tr.RIGHT * 3, tr.ENTER], ["abc", "xyz", ""], (2, 0)),
        ([tr.DOWN, tr.RIGHT * 2, tr.BACKSPACE], ["abc", "xz"], (1, 1)),
        ([tr.DOWN, tr.BACKSPACE], ["abcxyz", "~"], (0, 3)),
        ([tr.DOWN * 2, "X"], ["abc", "xyz", "X", "~"], (2, 1)),
        ([tr.PAGE_DOWN, "X"], ["abc", "xyz"] + [""] * 19 + ["X"], (21, 1)),
    ]
    for keys, after, cursor in cases:
        ed = tr.edit(t, text, asan=True)
        ed.keys(*keys)
        n = len(after)
        t.check(ed.lines[:n] == after, f"{keys!r}: {ed.lines[:n]}")
        # Undone and redone three times over: the same screen, the cursor where the edit left it.
        for _ in range(3):
            ed.keys(tr.ctrl("z"))
            t.check(ed.lines[:2] == ["abc", "xyz"], f"{keys!r} undone: {ed.lines[:3]}")
            ed.keys(tr.ctrl("r"))
            t.check(ed.lines[:n] == after and ed.cursor == cursor,
                    f"{keys!r} redone: {ed.lines[:n]} {ed.cursor}, not {after} {cursor}")
        ed.keys(tr.ctrl("r"))
        t.check(ed.message == "Nothing to redo", f"{keys!r}: a second Ctrl-R: {ed.message!r}")
        ed.keys(tr.ctrl("s"))
        want = "\n".join(l for l in after if l != "~") + "\n"
        t.check(ed.saved() == want, f"{keys!r} redone, saved {ed.saved()!r}, not {want!r}")
        ed.quit()

    # Nothing to redo before any undo; and an edit after an undo: what was undone is gone.
    ed = tr.edit(t, "one\n", name="g.txt", asan=True)
    ed.keys(tr.ctrl("r"))
    t.check(ed.message == "Nothing to redo", f"{ed.message!r}")
    ed.keys("a", tr.ENTER, "b")
    t.check(ed.lines[:2] == ["a", "bone"], f"{ed.lines[:2]}")
    ed.keys(tr.ctrl("z"), tr.ctrl("z"))
    t.check(ed.lines[:2] == ["aone", "~"], f"two undone: {ed.lines[:2]}")
    ed.keys("Q")
    ed.keys(tr.ctrl("r"))
    t.check(ed.message == "Nothing to redo" and ed.lines[:2] == ["aQone", "~"],
            f"an edit after an undo empties redo: {ed.message!r} {ed.lines[:2]}")
    ed.keys(tr.ctrl("z"))
    t.check(ed.lines[0] == "aone", f"{ed.lines[0]!r}")
    ed.keys(tr.ctrl("z"))
    t.check(ed.lines[0] == "one", f"{ed.lines[0]!r}")
    ed.keys(tr.ctrl("r"), tr.ctrl("r"))
    t.check(ed.lines[:2] == ["aQone", "~"], f"redone both: {ed.lines[:2]}")
    ed.keys(tr.ctrl("s"))
    t.check(ed.saved() == "aQone\n", f"saved {ed.saved()!r}")
    ed.quit()

    # A step that inserts and deletes rows, back and forth: the records keep their opposites.
    rows = "".join(f"row {i}\n" for i in range(6))
    ed = tr.edit(t, rows, name="h.txt", asan=True)
    ed.keys(tr.DOWN * 3, tr.BACKSPACE)      # row 3 joined onto row 2
    ed.keys(tr.DOWN, tr.ENTER)              # an empty row after "row 4"
    ed.keys(tr.UP, tr.RIGHT * 2, tr.ENTER)  # "row 4" split in two
    edited = list(ed.lines[:8])
    for _ in range(4):
        for _ in range(3):
            ed.keys(tr.ctrl("z"))
        t.check(ed.lines[:7] == [f"row {i}" for i in range(6)] + ["~"], f"all undone: {ed.lines[:7]}")
        for _ in range(3):
            ed.keys(tr.ctrl("r"))
        t.check(ed.lines[:8] == edited, f"all redone: {ed.lines[:8]}, not {edited}")
    ed.keys(tr.ctrl("s"))
    t.check(ed.saved() == "".join(l + "\n" for l in edited if l != "~"), f"saved {ed.saved()!r}")
    ed.quit()
