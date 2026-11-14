"""04.04 Saving

Ctrl-S writes the rows to the file, each followed by "\\n", replacing what
was there (a file that did not exist is created, mode 0644 less the umask),
says how many bytes it wrote, and clears (modified). With unsaved changes,
Ctrl-Q warns and quits only when pressed 3 more times in a row; with none,
it quits at once. A save that fails says why.
"""

import os
import stat


def test(t):
    tr = t.track
    ed = tr.edit(t, "a long first line\nsecond\n")
    ed.keys(tr.DOWN, tr.RIGHT * 6, "!", tr.UP, tr.RIGHT * 10)
    ed.keys(tr.BACKSPACE * 11)
    t.check(ed.line(0) == "a long" and "(modified)" in ed.status, f"{ed.line(0)!r} {ed.status!r}")
    t.check(ed.saved() == "a long first line\nsecond\n", "nothing is written before Ctrl-S")
    ed.keys(tr.ctrl("s"))
    t.check(ed.saved() == "a long\nsecond!\n", f"saved {ed.saved()!r}: the file should be cut to the new text")
    t.check(ed.message == "15 bytes written on disk", f"message {ed.message!r}")
    t.check("(modified)" not in ed.status, f"(modified) should be gone: {ed.status!r}")
    rc = ed.quit()
    t.check(rc == 0, f"with nothing unsaved one Ctrl-Q quits, with status 0: {rc}")

    # Unsaved changes: Ctrl-Q three more times, in a row.
    ed = tr.edit(t, "x\n", name="g.txt")
    ed.keys("y", tr.ctrl("q"))
    t.check(ed.message == "WARNING!!! File has unsaved changes. Press Ctrl-Q 3 more times to quit.",
            f"the first Ctrl-Q warns: {ed.message!r}")
    ed.keys(tr.ctrl("q"))
    t.check("Press Ctrl-Q 2 more times" in ed.message, f"{ed.message!r}")
    ed.keys(tr.RIGHT, tr.ctrl("q"))
    t.check("Press Ctrl-Q 3 more times" in ed.message, f"another key starts the count again: {ed.message!r}")
    ed.keys(tr.ctrl("q"), tr.ctrl("q"))
    t.check(ed.s.proc.poll() is None and "Press Ctrl-Q 1 more times" in ed.message, f"{ed.message!r}")
    rc = ed.quit()
    t.check(rc == 0, f"the fourth Ctrl-Q quits: {rc}")
    t.check(ed.saved() == "x\n", "quitting does not save")

    # A new file, created by the first save.
    ed = tr.edit(t, None, name="new.txt")
    ed.keys("fresh", tr.ctrl("s"))
    mode = stat.S_IMODE(os.stat(ed.path).st_mode)
    umask = os.umask(0)
    os.umask(umask)
    t.check(mode == 0o644 & ~umask, f"a new file has mode {oct(mode)}, not {oct(0o644 & ~umask)}")
    t.check(ed.saved() == "fresh\n" and ed.message == "6 bytes written on disk", f"{ed.saved()!r} {ed.message!r}")

    # A save that cannot work.
    ed = tr.edit(t, None, name="no/such/dir.txt")
    ed.keys("z", tr.ctrl("s"))
    t.check(ed.message == "Can't save! I/O error: No such file or directory", f"{ed.message!r}")
    t.check("(modified)" in ed.status, "a failed save leaves the text modified")
