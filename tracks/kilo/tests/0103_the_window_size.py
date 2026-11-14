"""01.03 The window size

kilo fills the window it is given, whatever its size: the text rows, then
the status bar and the message line on the last two. When the kernel does
not know the size, kilo asks the terminal (ESC [ 6 n, after moving the
cursor as far right and down as it goes) and uses the answer.
"""


def layout(t, ed, rows, cols, what):
    lines = ed.lines
    t.check(len(lines) == rows, f"{what}: the screen has {len(lines)} rows")
    t.check(lines[0] == "first", f"{what}: first row is {lines[0]!r}")
    t.check(all(l == "~" for l in lines[2:rows - 2]), f"{what}: rows 2 to {rows - 3} should be ~: {lines}")
    t.check(ed.reverse(rows - 2) and ed.status.endswith("1/2"),
            f"{what}: the status bar should be row {rows - 2}, ending at column {cols}: {ed.status!r}")
    t.check(len(ed.status) == cols, f"{what}: the status bar is {len(ed.status)} columns wide, not {cols}")
    t.check(ed.message.startswith("HELP"), f"{what}: the last row should be the help: {ed.message!r}")


def test(t):
    tr = t.track
    for rows, cols in ((24, 80), (10, 40), (40, 132)):
        ed = tr.edit(t, "first\nsecond\n", rows=rows, cols=cols)
        layout(t, ed, rows, cols, f"{rows}x{cols}")
        t.check(b"\x1b[6n" not in ed.raw, "the kernel knew the size: kilo should not ask the terminal")
        ed.quit()
    # A terminal whose size the kernel does not know: kilo asks the terminal itself.
    ed = tr.edit(t, "first\nsecond\n", rows=20, cols=60, winsize=(0, 0))
    asked = ed.raw.count(b"\x1b[6n")
    t.check(asked == 2, f"kilo should ask twice where the cursor is, asked {asked} times")
    t.check(b"\x1b[999C\x1b[999B" in ed.raw, "kilo should move the cursor right and down as far as it goes")
    t.check(b"\x1b[999C\x1b[999B\x1b[6n\x1b[1;1H" in ed.raw, "and put it back where it was after asking")
    layout(t, ed, 20, 60, "asked")
