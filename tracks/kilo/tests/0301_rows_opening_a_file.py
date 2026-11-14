"""03.01 Rows: opening a file

kilo reads the file into rows and shows them from the top, one per screen
row, cut at the screen's width. A missing file is an empty buffer (the
welcome shows, and nothing is created). Line endings are not part of a
row, whether "\\n" or "\\r\\n", and the last line needs none.
"""

import os


def test(t):
    tr = t.track
    long = "x" * 100
    ed = tr.edit(t, "first line\n\nthird, after an empty one\n" + long + "\nno newline at the end")
    lines = ed.lines
    t.check(lines[:3] == ["first line", "", "third, after an empty one"], f"rows 0-2: {lines[:3]}")
    t.check(lines[3].startswith("x" * 79) and len(lines[3]) <= 80, f"a long line is cut at the edge: {len(lines[3])}")
    t.check(lines[4] == "no newline at the end", f"the last line, without a newline: {lines[4]!r}")
    t.check(all(l == "~" for l in lines[5:22]), f"after the file, ~: {lines[5:22]}")
    t.check("Kilo editor" not in "".join(lines), "no welcome when the file has rows")
    t.check("5 lines" in ed.status, f"5 rows: {ed.status!r}")
    ed.quit()

    # More rows than the screen: the first 22.
    ed = tr.edit(t, tr.lines_of(100))
    t.check(ed.lines[:22] == [f"line {i}" for i in range(1, 23)], f"rows: {ed.lines[:3]} ... {ed.lines[21]}")
    ed.quit()

    # "\r\n" line endings.
    ed = tr.edit(t, "dos one\r\ndos two\r\n", name="dos.txt")
    t.check(ed.lines[:3] == ["dos one", "dos two", "~"], f"a \\r\\n file: {ed.lines[:3]}")
    t.check("2 lines" in ed.status, f"2 rows: {ed.status!r}")
    ed.quit()

    # A file that does not exist: an empty buffer, and no file until it is saved.
    ed = tr.edit(t, None, name="missing.txt")
    t.check(any("Kilo editor -- version" in l for l in ed.lines), "an empty buffer shows the welcome")
    t.check("missing.txt - 0 lines" in ed.status, f"status: {ed.status!r}")
    ed.quit()
    t.check(not os.path.exists(ed.path), "opening a missing file should not create it")
