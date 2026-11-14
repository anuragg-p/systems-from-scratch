"""01.02 Reading a key

Escape sequences arrive as one key each: the arrows (ESC [ A..D), Page Up and
Down (ESC [ 5 ~, ESC [ 6 ~), Delete (ESC [ 3 ~), and Home and End in both
forms (ESC [ H/F, ESC O H/F, bound to nothing). A lone Escape is a key of its
own once nothing follows it for a tenth of a second, and a sequence kilo does
not know (Insert, ESC [ 2 ~) is not typed into the text.
"""


def test(t):
    tr = t.track
    ed = tr.edit(t, "abcdef\nghijkl\n" + tr.lines_of(60))
    ed.keys(tr.RIGHT, tr.RIGHT, tr.DOWN)
    t.check(ed.cursor == (1, 2), f"right, right, down should put the cursor at row 1, column 2: {ed.cursor}")
    ed.keys(tr.UP, tr.LEFT)
    t.check(ed.cursor == (0, 1), f"up, left should put it at row 0, column 1: {ed.cursor}")
    # Several keys in one read: each sequence is still one key.
    ed.keys(tr.RIGHT * 3 + tr.LEFT)
    t.check(ed.cursor == (0, 3), f"three rights and a left sent at once: {ed.cursor}")
    # Page Down and Page Up.
    ed.keys(tr.PAGE_DOWN)
    t.check(ed.line(0) != "abcdef", "Page Down should scroll the view")
    ed.keys(tr.PAGE_UP)
    t.check(ed.line(0) == "abcdef" and ed.cursor[0] == 0, f"Page Up should come back: {ed.line(0)!r} {ed.cursor}")
    # Home and End in both forms, Insert, and a lone Escape: nothing changes.
    before = ed.lines
    for key in (tr.HOME, tr.END, "\x1bOH", "\x1bOF", "\x1b[2~", tr.ESC):
        ed.keys(key)
        t.check(ed.lines == before, f"{key!r} changed the text: {ed.lines[:2]}")
    # Delete is one key, and deletes (as Backspace does in kilo: the character before
    # the cursor).
    ed.keys(tr.DEL)
    t.check(ed.line(0) == "abdef" and ed.cursor == (0, 2), f"Delete: {ed.line(0)!r} {ed.cursor}")
    # ESC on its own, and "[A" more than 0.1 s later, are three keys: Escape, then text.
    ed.keys(tr.ESC, "[A")
    t.check(ed.line(0) == "ab[Adef", f"a late '[A' after Escape is text: {ed.line(0)!r}")
    ed.keys(tr.ctrl("s"))
    t.check(ed.saved().startswith("ab[Adef\nghijkl\n"), f"saved {ed.saved()[:20]!r}")
