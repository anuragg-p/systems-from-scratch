"""03.03 Tabs

A tab shows as spaces up to the next column that is a multiple of 8, as a
terminal puts it, and the cursor counts it as that many columns. The file
keeps the tab.
"""


def test(t):
    tr = t.track
    text = "\tone\nab\tc\n1234567\tX\n12345678\tY\n\t\tdeep\n"
    ed = tr.edit(t, text)
    want = ["        one", "ab      c", "1234567 X", "12345678        Y", "                deep"]
    t.check(ed.lines[:5] == want, f"tabs to multiples of 8:\n{ed.lines[:5]}\nnot\n{want}")
    t.check(b"\t" not in ed.raw, "kilo should send spaces for a tab, never the tab itself")
    ed.keys(tr.RIGHT)
    t.check(ed.cursor == (0, 8), f"past the tab the cursor is at column 8: {ed.cursor}")
    ed.keys(tr.DOWN, tr.RIGHT, tr.RIGHT)
    t.check(ed.cursor == (1, 8), f"on 'ab<tab>c', after the tab: column 8: {ed.cursor}")
    ed.keys(tr.DOWN, tr.RIGHT * 5)
    t.check(ed.cursor == (2, 8), f"on '1234567<tab>X', after the tab: column 8: {ed.cursor}")
    ed.keys(tr.DOWN)
    t.check(ed.cursor == (3, 8), f"down to '12345678<tab>Y': on the tab, column 8: {ed.cursor}")
    ed.keys(tr.RIGHT)
    t.check(ed.cursor == (3, 16), f"past that tab: column 16: {ed.cursor}")
    ed.keys(tr.DOWN, tr.LEFT * 6, tr.RIGHT, tr.RIGHT)
    t.check(ed.cursor == (4, 16), f"after two tabs: column 16: {ed.cursor}")
    # Typing after a tab: the row is drawn again, the file keeps its tabs.
    ed.keys("Z", tr.ctrl("s"))
    t.check(ed.line(4) == "                Zdeep", f"{ed.line(4)!r}")
    t.check(ed.saved() == text.replace("\t\tdeep", "\t\tZdeep"), f"saved {ed.saved()!r}")
