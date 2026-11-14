"""Figures for kilo module 05, Search (lessons 05.01, 05.02).

    python3 art/kilo/figs05.py

Every value is from a real run of the project at the lesson, on a 10 x 44 pseudo-terminal
(8 rows of text):

  05.01  hello.c, the six-line C program with a tab before printf and return. Ctrl-F, then
         r: row 4 to the top, cursor on chars 2 (screen column 10); re, ret: row 5, chars 1
         (screen column 9); retx: no row has it, nothing moves. Searching render instead of
         chars puts the cursor on chars 8 of "\\treturn 0;" (screen column 16).
  05.02  f.txt, "line 1" to "line 30". Page Down twice: rowoff 16, cy 7 (24/30). Ctrl-F
         "line 2": rows 2, 20-29 hold it. Down: 20; Up: 2; Up again: around to 29. Escape:
         back to 24/30. Putting back only cx and cy: rowoff stays 28, and the status bar
         says 36/30.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import figlib  # noqa: E402
from figlib import Fig  # noqa: E402
from figs04 import strip, indexes  # noqa: E402

figlib.LESSONS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                              "tracks", "kilo", "lessons")
MOD = "05-search"

HELLO = ["#include <stdio.h>", "", "int main(void) {", "\tprintf(\"hello\\n\");", "\treturn 0;", "}"]


# ------------------------------------------------------------------ 05.01

def typing0501():
    f = Fig("f0501a", "Each key typed at the search prompt searches hello.c again from the first row", 296)
    f.text(24, 20, "hello.c, and the rows strstr() tries for each query, top down, until one holds it", "tm", 11)
    X0, RH = 24, 30
    Y0 = 70
    # the file, one row per line
    f.text(X0, Y0 - 16, "row", "tm", 10)
    for i, line in enumerate(HELLO):
        y = Y0 + i * RH
        f.text(X0 + 10, y + 15, str(i + 1), "tm", 10.5, "middle", mono=True)
        shown = line.replace("\t", "\\t")
        f.rect(X0 + 24, y, 186, 22, "s fs", 3)
        f.text(X0 + 30, y + 15, shown, "t", 10.5, mono=True)
    queries = [("r", 3, 2, "row 4"), ("re", 4, 1, "row 5"), ("ret", 4, 1, "row 5"), ("retx", None, None, "none")]
    CX = [276, 360, 444, 528]
    for (q, hit, col, what), cx in zip(queries, CX):
        f.text(cx + 30, Y0 - 16, "\"" + q + "\"", "t", 11.5, "middle", 600, mono=True)
        last = hit if hit is not None else len(HELLO) - 1
        for i in range(len(HELLO)):
            y = Y0 + i * RH + 11
            if i < last or (hit is None and i == last):
                f.circle(cx + 30, y, 4.5, "m f")
            elif i == hit:
                f.rect(cx + 6, y - 10, 48, 20, "a fa", 10)
                f.text(cx + 30, y + 4, "chars " + str(col), "f", 9.5, "middle", 600, mono=True)
        # the scan line
        f.line(cx + 30, Y0 + 2, cx + 30, Y0 + last * RH + (6.5 if hit is None else 1), "m")
        f.text(cx + 30, Y0 + 6 * RH + 14, what, "ta" if hit is not None else "tm", 10.5, "middle", 600)
    for i in range(len(HELLO)):
        f.line(X0 + 214, Y0 + i * RH + 11, 270, Y0 + i * RH + 11, "m", dash=True)
    f.circle(30, 278, 4.5, "m f")
    f.text(42, 282, "tried: not in this row", "tm", 10.5)
    f.rect(186, 270, 40, 16, "a fa", 8)
    f.text(234, 282, "the first row that has it: to the top of the screen, cursor on the match", "tm", 10.5)
    return f


def chars0501():
    f = Fig("f0501b", "The same row as chars and as render: a match's place in one is not its place in the other", 232)
    f.text(24, 20, "row 5 of hello.c, and where \"ret\" is found in each copy of it", "tm", 11)
    X, W = 110, 28
    indexes(f, X, 46, 17, W)
    f.text(24, 70, "chars", "t", 11.5, weight=600, mono=True)
    f.text(24, 85, "size 10", "tm", 10.5)
    strip(f, X, 56, [("\\t", "s")] + [(c, "a" if i < 3 else "n") for i, c in enumerate("return 0;")] + [("\\0", "z")], W, 28)
    f.text(24, 136, "render", "t", 11.5, weight=600, mono=True)
    f.text(24, 151, "rsize 17", "tm", 10.5)
    strip(f, X, 122, [(" ", "s")] * 8 + [(c, "a" if i < 3 else "n") for i, c in enumerate("return 0;")], W, 28)
    f.brace_h(X, X + 8 * W - 2, 158, "m")
    f.text(X + 4 * W, 174, "the tab, as 8 spaces", "tm", 10, "middle")
    f.line(X + 1.5 * W, 86, X + 8.5 * W, 120, "m", arrow=True, dash=True)
    f.text(24, 202, "strstr(chars) gives 1: the cursor goes to chars 1, drawn at screen column 9, on the r.", "ta", 10.5)
    f.text(24, 218, "strstr(render) gives 8: used as a column of chars, that is the 0, drawn at column 16.", "tm", 10.5)
    return f


# ------------------------------------------------------------------ 05.02

def nextprev0502():
    f = Fig("f0502a", "The rows of f.txt that hold line 2, and where each arrow key goes from a match", 236)
    f.text(24, 20, "f.txt, rows 1 to 30; the query \"line 2\" is in rows 2 and 20 to 29", "tm", 11)
    X, W, Y = 40, 18.5, 98
    hits = {2} | set(range(20, 30))
    for r in range(1, 31):
        x = X + (r - 1) * W
        hit = r in hits
        f.rect(x, Y, W - 3, 30, "a af" if hit else "m f", 3)
        f.text(x + (W - 3) / 2, Y + 19, str(r), "ta" if hit else "tm", 8 if r > 9 else 9, "middle", mono=True)

    def mid(r):
        return X + (r - 1) * W + (W - 3) / 2

    # typing: from the top
    f.text(mid(1) - 8, 52, "typing: from row 1", "tm", 10)
    f.line(mid(1), 58, mid(2), Y - 4, "a", arrow=True)
    # Down: 2 -> 20, 20 -> 21
    f.path(f"M{mid(2):.1f} {Y - 4} C {mid(2):.1f} {Y - 46}, {mid(20):.1f} {Y - 46}, {mid(20):.1f} {Y - 4}", "a", arrow=True)
    f.text((mid(2) + mid(20)) / 2, Y - 42, "Down or Right: the next row with it", "ta", 10.5, "middle")
    f.path(f"M{mid(20):.1f} {Y - 4} C {mid(20):.1f} {Y - 20}, {mid(21):.1f} {Y - 20}, {mid(21):.1f} {Y - 4}", "a", arrow=True)
    # Up from 2, around the start to 29
    yb = Y + 70
    f.path(f"M{mid(2):.1f} {Y + 34} L{mid(2):.1f} {yb} L{X - 14} {yb} L{X - 14} {yb + 22} "
           f"L{mid(30) + 22:.1f} {yb + 22} L{mid(30) + 22:.1f} {yb} L{mid(29):.1f} {yb} L{mid(29):.1f} {Y + 34}",
           "s", arrow=True)
    f.text(320, yb + 40, "Up or Left at row 2: back past row 1, around the end, to row 29", "t", 10.5, "middle")
    f.text(320, yb + 56, "(Down at row 29 goes around the other way, to row 2)", "tm", 10.5, "middle")
    return f


def back0502():
    f = Fig("f0502b", "Escape puts four numbers back: the view and the cursor on the screen", 300)
    f.text(24, 20, "f.txt (30 rows) and the 8 rows of the screen, as rowoff and cy place them", "tm", 11)
    RH = 5.2
    TOP = 56
    panels = [
        (24, "before Ctrl-F", 16, 7, "rowoff 16, cy 7", "row 24: 24/30", "t"),
        (176, "at a match", 28, 0, "rowoff 28, cy 0", "row 29: 29/30", "t"),
        (328, "Escape", 16, 7, "all four put back", "row 24: 24/30", "ta"),
        (480, "only cx, cy back", 28, 7, "rowoff stays 28", "row 36: 36/30", "tm"),
    ]
    for x, title, rowoff, cy, l1, l2, tcls in panels:
        f.text(x, TOP - 14, title, "ta" if tcls == "ta" else "t", 11.5, weight=600)
        # the file: 30 rows
        f.rect(x + 30, TOP, 40, 30 * RH, "s fs", 2)
        f.text(x + 14, TOP + 8, "1", "tm", 9, "end", mono=True)
        f.text(x + 14, TOP + 30 * RH, "30", "tm", 9, "end", mono=True)
        # rows past the end, when the view reaches there
        end = rowoff + 8
        if end > 30:
            f.rect(x + 30, TOP + 30 * RH + 2, 40, (end - 30) * RH - 2, "m", 2, dash=True)
            f.text(x + 94, TOP + 30 * RH + (end - 30) * RH / 2 + 3, "past the end", "tm", 9)
        # the window: 8 rows from rowoff
        cls = "a af" if tcls == "ta" else ("m" if tcls == "tm" else "s")
        f.rect(x + 22, TOP + rowoff * RH, 56, 8 * RH, cls, 3, dash=tcls == "tm")
        # the cursor row
        cyy = TOP + (rowoff + cy) * RH + RH / 2
        f.line(x + 26, cyy, x + 84, cyy, "a" if tcls != "tm" else "s")
        f.circle(x + 86, cyy, 3, "a fa" if tcls != "tm" else "s f")
        f.text(x, 254, l1, "tm", 10.5)
        f.text(x, 270, l2, tcls, 10.5, weight=600 if tcls != "t" else None)
    f.text(24, 294, "The cursor is on file row rowoff + cy: the view and the cursor move together, or not at all.",
           "tm", 10.5)
    return f


FIGS = [
    ("05.01-as-you-type", typing0501), ("05.01-chars-render", chars0501),
    ("05.02-next-prev", nextprev0502), ("05.02-going-back", back0502),
]


def main():
    for name, fn in FIGS:
        print(figlib.write(MOD, name, fn()))


if __name__ == "__main__":
    main()
