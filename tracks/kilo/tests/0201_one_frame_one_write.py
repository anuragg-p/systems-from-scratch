"""02.01 One frame, one write

Every key gets one new screen. Each one hides the cursor, starts at the top
left, draws every row erased to its end (a ~ for each row past the end of
the file, the welcome a third of the way down when the file is empty), and
ends by putting the cursor back and showing it. When the window changes
size, kilo draws the screen again at the new size, with the cursor inside it.
"""

import re


def test(t):
    tr = t.track
    ed = tr.edit(t, None, name="new.txt")          # no such file: an empty buffer
    frame = ed.raw
    t.check(frame.startswith(b"\x1b[?25l\x1b[H"), f"a screen should start by hiding the cursor and going home: {frame[:12]!r}")
    t.check(frame.endswith(b"\x1b[1;1H\x1b[?25h"), f"and end by moving the cursor to it and showing it: {frame[-16:]!r}")
    t.check(frame.count(b"\x1b[?25h") == 1, "one screen so far")
    t.check(frame.count(b"~\x1b[0K\r\n") == 21, f"21 empty rows, each a ~ erased to its end: {frame.count(b'~')}")
    lines = ed.lines
    # The welcome: on row 22 // 3 == 7, centred, after a ~.
    w = "Kilo editor -- version 0.0.1"
    t.check(lines[7].startswith("~ ") and lines[7].strip("~ ") == w, f"row 7 should hold the welcome: {lines[7]!r}")
    t.check(abs(lines[7].index(w) - (80 - len(w)) // 2) <= 4, f"the welcome should be centred: {lines[7]!r}")
    t.check(all(l == "~" for i, l in enumerate(lines[:22]) if i != 7), f"every other text row is ~: {lines[:22]}")
    # One screen per key, each the whole screen again; Ctrl-L just draws it again.
    for k, key in enumerate([tr.ctrl("l"), tr.ctrl("l"), tr.ctrl("l")], 2):
        ed.keys(key)
        t.check(ed.screen.frames == k, f"after {k - 1} keys there should be {k} screens, not {ed.screen.frames}")
    t.check(ed.lines == lines, "Ctrl-L should draw the same screen again")
    frames = ed.raw.split(b"\x1b[?25l")[1:]
    t.check(len(set(frames)) == 1, "every screen of the same state should be the same bytes")

    # Resize after resize while kilo waits for a key: each is drawn, and kilo goes on
    # waiting. This part fails only on Linux with glibc, with the original kilo's
    # signal(SIGWINCH, handleSigWinCh) put back: in a C99 build with _POSIX_C_SOURCE that
    # is the System V signal(), so the first resize makes the read() in editorReadKey()
    # fail with EINTR and kilo exits with status 1 (and with that read() retried, the
    # second is not drawn: the handler was reset after the first). On macOS and on musl
    # signal() keeps the handler and restarts the read(), and it passes there either way.
    ed = tr.edit(t, tr.lines_of(5), name="resize.txt")
    for n, (rows, cols) in enumerate([(30, 100), (20, 60), (24, 80)], 1):
        try:
            ed.resize(rows, cols)
        except tr.Fail as e:
            raise tr.Fail(f"resize {n} of 3, to {rows} x {cols}, with kilo waiting for a key: {e}")
        t.check(len(ed.status) == cols and ed.status.endswith("1/5") and ed.reverse(rows - 2),
                f"resize {n}: the status bar should fill row {rows - 2} of {cols} columns: {ed.status!r}")
    ed.keys(tr.DOWN, "x")
    t.check(ed.line(1) == "xline 2", f"after the resizes kilo still takes keys: {ed.line(1)!r}")

    # A window that grows, and one that shrinks under the cursor.
    ed = tr.edit(t, tr.lines_of(30))
    ed.resize(30, 100)
    t.check(ed.lines[27] == "line 28" and ed.reverse(28) and len(ed.status) == 100 and ed.status.endswith("1/30"),
            f"at 30x100 the text should fill 28 rows and the status bar row 28: {ed.lines[27]!r} {ed.status!r}")
    ed.keys(tr.DOWN * 10)
    t.check(ed.cursor == (10, 0), f"cursor should be on row 10: {ed.cursor}")
    ed.resize(12, 100)                              # 10 rows of text: row 10 is now the status bar
    t.check(ed.cursor[0] == 9, f"after shrinking, the cursor should be on the last text row, 9, not {ed.cursor[0]}")
    t.check(ed.reverse(10) and re.match(r"f\.txt - 30 lines", ed.status), f"status bar on row 10: {ed.status!r}")
    ed.keys("x")
    t.check(ed.line(9) == "xline 10", f"typing goes where the cursor is shown: {ed.line(9)!r}")

    # A screen narrower than the welcome: no padding, and the text cut to the width. With
    # the original kilo's padding (negative below 33 columns) kilo never draws at all, and
    # with its whole text the welcome wraps onto the row below.
    for cols in (32, 30, 20, 12):
        try:
            ed = tr.edit(t, None, name="narrow.txt", rows=10, cols=cols, timeout=5)
        except tr.Fail as e:
            raise tr.Fail(f"10 x {cols}, empty file: {e}")
        lines = ed.lines
        t.check(w.startswith(lines[2]) and len(lines[2]) >= min(len(w), cols - 1),
                f"10 x {cols}: row 2 should be the welcome, cut to the width: {lines}")
        t.check(all(l == "~" for i, l in enumerate(lines[:8]) if i != 2),
                f"10 x {cols}: every other text row is ~, nothing wrapped: {lines}")
        t.check(ed.reverse(8), f"10 x {cols}: the status bar should be on row 8: {lines}")
        t.check(ed.quit() == 0, f"10 x {cols}: Ctrl-Q should quit")
