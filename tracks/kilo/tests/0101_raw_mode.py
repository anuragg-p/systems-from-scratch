"""01.01 Raw mode

While kilo runs, the terminal is in raw mode: no echo, no line editing, no
signals, no flow control, no output processing, and reads that return after
a tenth of a second. Ctrl-C and Ctrl-Z do not stop it. When it exits, the
terminal is exactly as it was before.
"""

import os
import pty
import termios


def test(t):
    tr = t.track
    # How a new pseudo-terminal starts out: what kilo's terminal was before it ran.
    m, s = pty.openpty()
    fresh = termios.tcgetattr(m)
    os.close(m)
    os.close(s)

    ed = tr.edit(t, "one\ntwo\n")
    iflag, oflag, cflag, lflag, _, _, cc = ed.termios()
    for name in ("ECHO", "ICANON", "ISIG", "IEXTEN"):
        t.check(not lflag & getattr(termios, name), f"{name} should be off in raw mode")
    for name in ("BRKINT", "ICRNL", "INPCK", "ISTRIP", "IXON"):
        t.check(not iflag & getattr(termios, name), f"{name} should be off in raw mode")
    t.check(not oflag & termios.OPOST, "OPOST should be off in raw mode")
    t.check(cflag & termios.CSIZE == termios.CS8, "characters should be 8 bits (CS8)")
    t.check(cc[termios.VMIN] in (0, b"\x00") and cc[termios.VTIME] in (1, b"\x01"),
            f"read() should return after 0.1 s, with a byte or without: VMIN {cc[termios.VMIN]!r}, "
            f"VTIME {cc[termios.VTIME]!r}")

    # Ctrl-C, Ctrl-Z and Ctrl-\ are bytes now, not signals (the terminal is kilo's own
    # controlling terminal here, as in a real one, so with ISIG on they would stop it).
    ed.keys(tr.ctrl("c"), tr.ctrl("z"), tr.ctrl("\\"))
    t.check(ed.s.proc.poll() is None, "Ctrl-C, Ctrl-Z or Ctrl-\\ stopped kilo: ISIG is still on")
    # The terminal does not echo: what is typed shows once, where kilo draws it.
    ed.keys("xy")
    t.check(sum(l.count("xy") for l in ed.lines) == 1, f"typed text should show once: {ed.lines[:3]}")
    # Enter arrives as 13, not turned into 10: kilo splits the line.
    ed.keys(tr.ENTER)
    t.check(ed.lines[:3] == ["xy", "one", "two"], f"Enter should split the line: rows {ed.lines[:3]}")
    # Ctrl-S reaches kilo (no flow control): it saves.
    ed.keys(tr.ctrl("s"))
    t.check("bytes written on disk" in ed.message, f"Ctrl-S should save; the message line: {ed.message!r}")
    # Ctrl-Z and Ctrl-\ reached kilo as the bytes 26 and 28, and went into the text as
    # any byte without a key of its own does (kilo ignores only Ctrl-C). With module 08 in
    # the tree Ctrl-Z has a key of its own, undo, and with nothing done yet it said so.
    ctrl_z = "" if ed.said("Nothing to undo") else "\x1a"
    t.check(ed.saved() == ctrl_z + "\x1cxy\none\ntwo\n", f"saved {ed.saved()!r}")
    # So does Ctrl-Q: kilo exits with status 0, and the terminal is as it was.
    rc = ed.quit()
    t.check(rc == 0, f"Ctrl-Q should exit with status 0, not {rc}")
    after = ed.termios()
    for k, what in enumerate(("input", "output", "control", "local")):
        t.check(after[k] == fresh[k], f"after exit the terminal's {what} flags are {after[k]:#x}, "
                                      f"not {fresh[k]:#x} as before")
    t.check(after[6] == fresh[6], "after exit the terminal's control characters differ from before")
