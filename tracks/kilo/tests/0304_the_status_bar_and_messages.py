"""03.04 The status bar and messages

The second-last row is the status bar, in reverse video: the file's name (at
most 20 characters), how many lines it has, "(modified)" once it differs
from the file, and at the right edge the cursor's row out of all of them.
The last row shows the latest message for 5 seconds, cut to the screen.
"""

import time


def test(t):
    tr = t.track
    name = "a_rather_long_file_name.txt"
    ed = tr.edit(t, "one\ntwo\nthree\n", name=name)
    t.check(ed.reverse(22), "the status bar should be in reverse video, edge to edge")
    t.check(not ed.reverse(21) and not any(ed.screen.rev[23]), "only the status bar is in reverse video")
    t.check(ed.status.startswith("a_rather_long_file_n - 3 lines"), f"name cut to 20 characters: {ed.status!r}")
    t.check(ed.status.endswith(" 1/3") and len(ed.status) == 80, f"row 1 of 3, at the right edge: {ed.status!r}")
    t.check(ed.message == "HELP: Ctrl-S = save | Ctrl-Q = quit | Ctrl-F = find", f"the help: {ed.message!r}")
    ed.keys(tr.DOWN, tr.DOWN)
    t.check(ed.status.endswith(" 3/3"), f"the right edge follows the cursor: {ed.status!r}")
    ed.keys("x")
    t.check("3 lines (modified)" in ed.status, f"(modified) once the text changes: {ed.status!r}")
    # The message goes once it is 5 seconds old, at the next screen drawn.
    time.sleep(5.2)
    ed.keys(tr.ctrl("l"))
    t.check(ed.message == "", f"after 5 seconds the message should be gone: {ed.message!r}")
    t.check("(modified)" in ed.status, "the status bar stays")

    # A narrow screen: both rows cut to its width.
    ed = tr.edit(t, "one\n", name="narrow.txt", rows=8, cols=30)
    t.check(ed.status == "narrow.txt - 1 lines" + " " * 7 + "1/1", f"30 columns: {ed.status!r}")
    t.check(ed.message == "HELP: Ctrl-S = save | Ctrl-Q =", f"message cut to 30 columns: {ed.message!r}")
    ed = tr.edit(t, "one\n", name=name, rows=8, cols=16)
    t.check(ed.status == "a_rather_long_fi", f"a status bar wider than the screen is cut: {ed.status!r}")
