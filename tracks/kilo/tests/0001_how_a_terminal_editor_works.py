"""00.01 How a terminal editor works

The whole loop, key to screen: kilo opens a file and draws it, each key
changes the text or the cursor and the screen is drawn again, Ctrl-S writes
the file, and Ctrl-Q puts the terminal back and exits.
"""


def test(t):
    tr = t.track
    ed = tr.edit(t, "Hello\nworld\n", name="hello.txt")
    t.check(ed.lines[:3] == ["Hello", "world", "~"], f"the file: {ed.lines[:3]}")
    t.check(ed.status.startswith("hello.txt - 2 lines") and ed.status.endswith("1/2"), f"{ed.status!r}")
    t.check(ed.message.startswith("HELP: Ctrl-S = save"), f"{ed.message!r}")
    frames = ed.screen.frames
    ed.keys(tr.RIGHT * 5, ",", tr.DOWN, "!", tr.ENTER, "from kilo")
    t.check(ed.lines[:3] == ["Hello,", "world!", "from kilo"], f"after typing: {ed.lines[:3]}")
    t.check(ed.screen.frames >= frames + 18, "every key draws the screen again")
    t.check(ed.cursor == (2, 9) and "(modified)" in ed.status, f"{ed.cursor} {ed.status!r}")
    ed.keys(tr.ctrl("s"))
    t.check(ed.saved() == "Hello,\nworld!\nfrom kilo\n", f"saved {ed.saved()!r}")
    t.check(ed.message == "24 bytes written on disk", f"{ed.message!r}")
    rc = ed.quit()
    t.check(rc == 0, f"Ctrl-Q exits with status 0: {rc}")
    import termios
    t.check(ed.termios()[3] & termios.ECHO, "the terminal echoes again after kilo exits")
