"""00.02 What the terminal sends and understands

Keys reach kilo as bytes: letters as themselves, Ctrl keys as 1 to 26,
Enter as 13, Backspace as 127, and the arrows and other special keys as
escape sequences (ESC [ A ...). kilo answers with bytes too: text, and
escape sequences the terminal obeys: hide and show the cursor, move it,
erase to the end of the line, reverse video, and ask where the cursor is.
"""


def test(t):
    tr = t.track
    ed = tr.edit(t, "ab\n", rows=6, cols=20)
    raw = ed.raw
    # The whole first screen, byte for byte: 4 rows of text, the status bar, the message.
    want = (b"\x1b[?25l\x1b[H"                         # hide the cursor, go to row 1, column 1
            b"ab\x1b[0K\r\n"                           # a row of the file, the rest of the line erased
            b"~\x1b[0K\r\n~\x1b[0K\r\n~\x1b[0K\r\n"    # rows past the end of the file
            b"\x1b[0K\x1b[7mf.txt - 1 lines  1/1\x1b[0m\r\n"   # the status bar, in reverse video
            b"\x1b[0KHELP: Ctrl-S = save "             # the message, cut to 20 columns
            b"\x1b[1;1H\x1b[?25h")                     # the cursor to row 1, column 1, shown
    t.check(raw == want, f"the first screen is\n{raw!r}\nnot\n{want!r}")
    # The same keys as kilo sees them, one escape sequence per special key.
    ed.keys("\x1b[C", "\x1b[C")                       # Right, Right
    t.check(ed.raw.endswith(b"\x1b[1;3H\x1b[?25h"), f"the cursor moved to column 3: {ed.raw[-14:]!r}")
    ed.keys("\x0d")                                   # Enter is 13: a carriage return
    ed.keys("x", "\x7f", "\x7f")                      # Backspace is 127, twice: x, then the row break
    t.check(ed.lines[:2] == ["ab", "~"], f"{ed.lines[:2]}")
    ed.keys("\x1b[D", "\x1bOF", "\x1b[3~")            # Left, End (one form of it), Delete
    t.check(ed.lines[0] == "b" and ed.cursor == (0, 0), f"{ed.lines[0]!r} {ed.cursor}")
    ed.keys("\x13")                                   # Ctrl-S is 19
    t.check(ed.saved() == "b\n", f"saved {ed.saved()!r}")
