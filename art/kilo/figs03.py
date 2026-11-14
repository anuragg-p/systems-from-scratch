"""Figures for kilo module 03, A text viewer (lessons 03.01 to 03.04).

    python3 -B art/kilo/figs03.py      writes tracks/kilo/lessons/03-viewer/figures/03.0N-*.svg

Every screen, byte and offset here is from a real run of the project as it stands at that
lesson (./learn files kilo --at NN.LL), on a pseudo-terminal, its output fed to the Screen
emulator in tracks/kilo/track.py:
  03.01 rows     notes.txt ("kilo", a 30-byte line, an empty line, "end": 41 bytes) on 6 x 24
  03.02 window   nato.txt (alpha .. juliett, line 5 is 52 bytes) on 6 x 20: Down x5 and
                 Right x24 leave rowoff 1, coloff 5, cy 4, cx 19; one more Down: rowoff 2,
                 coloff 4, cy 4, cx 0 (read off the screens and the cursor kilo drew)
  03.03 render   "ab\\tc" and "\\tone" on 6 x 24: the cursor on 'c' is drawn at column 9, at
                 the end of "\\tone" at column 12
  03.03 rawtabs  the project's own Makefile on 10 x 44 after Page Down, at 03.02 and at 03.03
  03.04 bars     hello.c (six lines, two of them tabbed) on 10 x 44: the frame's last two lines
The module's cover and icon are not made here.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import figlib  # noqa: E402
from figlib import Fig, write  # noqa: E402
from figs02 import mono_runs, screen  # noqa: E402

figlib.LESSONS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                              "tracks", "kilo", "lessons")
MOD = "03-viewer"


def bytebox(f, x, y, ch, cls="s f", tcls="t", w=13, h=22, size=10):
    f.rect(x, y, w, h, cls, 2)
    if ch:
        f.text(x + w / 2, y + h / 2 + size * 0.36, ch, tcls, size, "middle", mono=True)


# ------------------------------------------------------------------ 03.01

NOTES = "kilo\na line longer than this screen\n\nend\n"


def rows():
    assert len(NOTES) == 41
    f = Fig("f0301a", "notes.txt: 41 bytes, four rows, and the screen kilo draws from them", 432)
    f.text(24, 22, "notes.txt, read by kilo at 03.01 on a terminal 6 rows by 24 columns", "tm", 11)
    # the file's bytes
    f.text(24, 50, "the file: 41 bytes", "t", 11.5, weight=600)
    x0, y0, bw = 24, 60, 14
    for i, ch in enumerate(NOTES):
        x = x0 + i * bw
        if ch == "\n":
            bytebox(f, x, y0, "\\n", "a af", "ta", w=bw - 1, size=8.5)
        else:
            bytebox(f, x, y0, ch if ch != " " else "", "m f", "t", w=bw - 1)
    lines = NOTES.split("\n")[:-1]
    start = 0
    for r, line in enumerate(lines):
        a, b = start, start + len(line)
        if b > a:
            f.brace_h(x0 + a * bw + 1, x0 + b * bw - 2, y0 + 30, "m")
            f.text(x0 + a * bw + 1, y0 + 46, f"row {r}", "tm", 10.5)
        else:
            f.line(x0 + a * bw + 6, y0 + 25, x0 + a * bw + 6, y0 + 52, "m")
            f.text(x0 + a * bw + 6, y0 + 66, f"row {r}: no bytes", "tm", 10.5, "end")
        start = b + 1
    f.text(616, 50, "each \\n ends a line; getline() keeps it, kilo strips it", "ta", 10.5, "end")
    # E.row
    f.text(24, 150, "E.row: one erow a line, E.numrows = 4", "t", 11.5, weight=600)
    ry, rh = 160, 28
    cx0 = 176
    for r, line in enumerate(lines):
        y = ry + r * rh
        f.text(24, y + 15, f"E.row[{r}]", "t", 11, mono=True)
        f.text(96, y + 15, f"size {len(line)}", "tm", 11, mono=True)
        for i, ch in enumerate(line):
            bytebox(f, cx0 + i * bw, y, ch if ch != " " else "", "m f", "t", w=bw - 1, h=20)
        bytebox(f, cx0 + len(line) * bw, y, "\\0", "m fs", "tm", w=bw - 1, h=20, size=8.5)
    f.text(cx0, ry + 4 * rh + 12, "chars: the line without its \\n, and a \\0 that size does not count", "tm", 10.5)
    # the screen
    sy = 318
    f.text(24, sy - 18, "the screen", "t", 11.5, weight=600)
    scr = ["kilo", "a line longer than this", "", "end", "~", ""]
    screen(f, 46, sy, scr, 24, cw=7.0, rh=17)
    nx = 46 + 24 * 7 + 34
    notes = [(0, "rows 1 to 4: E.row[0] to E.row[3]"),
             (1, "cut at the screen's edge: 24 bytes of the 30"),
             (4, "past the end of the file: ~"),
             (5, "the bottom line stays empty")]
    for r, text in notes:
        yy = sy + r * 17 + 12
        f.line(nx - 22, yy - 4, nx - 6, yy - 4, "m")
        f.text(nx, yy, text, "t" if r < 2 else "tm", 11)
    return f


# ------------------------------------------------------------------ 03.02

NATO = ["alpha", "bravo", "charlie", "delta", "echo",
        "foxtrot: this line is longer than the screen is wide", "golf", "hotel", "india", "juliett"]


def window():
    f = Fig("f0302a", "nato.txt on a 6 x 20 terminal: the window over the file, its two offsets, and the cursor", 486)
    f.text(24, 22, "nato.txt, 10 rows, at 03.02 on a terminal 6 rows by 20 columns: 5 rows of text, 20 columns", "tm", 11)
    cw, rh = 6.6, 16
    x0 = 72
    panels = [
        (62, "after Down 5 times and Right 24 times", 1, 5, 4, 19,
         ["E.rowoff = 1", "E.coloff = 5", "E.cy = 4, E.cx = 19", "file row 1 + 4 = 5", "file column 5 + 19 = 24"]),
        (282, "then Down once more, onto golf", 2, 4, 4, 0,
         ["E.rowoff = 2", "E.coloff = 4", "E.cy = 4, E.cx = 0", "file row 2 + 4 = 6", "file column 4 + 0 = 4:", "the end of golf"]),
    ]
    for top, title, rowoff, coloff, cy, cx, notes in panels:
        f.text(24, top - 14, title, "t", 12, weight=600)
        # column ruler
        for c in range(0, 53, 10):
            f.text(x0 + c * cw, top - 2, str(c), "tm", 9, mono=True)
        y = top + 4
        wx, wy = x0 + coloff * cw, y + rowoff * rh
        f.rect(wx, wy, 20 * cw, 5 * rh, "a af", 2)
        crow, ccol = rowoff + cy, coloff + cx
        f.rect(x0 + ccol * cw, y + crow * rh + 2, cw, rh - 3, "a fa", 1)
        for r, line in enumerate(NATO):
            yy = y + r * rh + 12
            f.text(x0 - 10, yy, str(r), "tm", 9.5, "end", mono=True)
            inside = rowoff <= r < rowoff + 5
            for c, ch in enumerate(line):
                if ch == " ":
                    continue
                vis = inside and coloff <= c < coloff + 20
                cls = "f" if (r, c) == (crow, ccol) else ("t" if vis else "tm")
                f.text(x0 + c * cw, yy, ch, cls, 11, mono=True)
        f.text(wx + 20 * cw + 6, wy + 12, "the window: 5 x 20", "ta", 10.5)
        nx = 470
        for k, text in enumerate(notes):
            f.text(nx, y + 12 + 18 * k + 40, text, "t" if k < 3 else "tm", 11, mono=k < 3)
    f.text(24, 474, "golf is 4 characters, so the cursor is pulled back to its end; coloff drops just enough to keep it on the screen.", "tm", 10.5)
    return f


# ------------------------------------------------------------------ 03.03

def render():
    f = Fig("f0303a", "A row's bytes, the columns it takes on the screen, and where the cursor goes", 372)
    f.text(24, 22, "at 03.03: chars is what the file holds, render what the screen shows; a tab runs to the next multiple of 8", "tm", 11)
    bw = 26
    x0 = 118
    examples = [
        (52, "ab\tc", "ab      c", 3, 9, "E.cx = 3, on the c: screen column 9", "a tab at column 2: 6 spaces"),
        (210, "\tone", "        one", 4, 12, "E.cx = 4, the end of the row: column 12", "a tab at column 0: 8 spaces"),
    ]
    for y, chars, rend, cx, scol, cnote, tnote in examples:
        f.text(24, y + 16, "chars", "t", 11.5, weight=600, mono=True)
        f.text(24, y + 82, "render", "t", 11.5, weight=600, mono=True)
        for i, ch in enumerate(chars):
            tab = ch == "\t"
            bytebox(f, x0 + i * bw, y, "\\t" if tab else ch, "a af" if tab else "s f", "ta" if tab else "t", w=bw - 2, h=24, size=11)
            f.text(x0 + i * bw + (bw - 2) / 2, y - 4, str(i), "tm", 9, "middle", mono=True)
        ry = y + 66
        t = chars.index("\t")
        tab_end = len(rend) - (len(chars) - t - 1)
        for c, ch in enumerate(rend):
            pad = t <= c < tab_end
            bytebox(f, x0 + c * bw, ry, ch.strip(), "a af" if pad else "s f", "t", w=bw - 2, h=24, size=11)
            f.text(x0 + c * bw + (bw - 2) / 2, ry + 36, str(c), "tm", 9, "middle", mono=True)
        # chars -> render
        for i, ch in enumerate(chars):
            sx = x0 + i * bw + (bw - 2) / 2
            if ch == "\t":
                f.path(f"M{sx} {y + 25} L{x0 + t * bw + 2} {ry - 2}", "a")
                f.path(f"M{sx} {y + 25} L{x0 + tab_end * bw - 4} {ry - 2}", "a")
            else:
                c = i if i < t else i + (tab_end - t - 1)
                f.line(sx, y + 25, x0 + c * bw + (bw - 2) / 2, ry - 2, "m")
        f.text(x0 + len(chars) * bw + 16, y + 16, tnote, "ta", 11)
        # the cursor
        cxx = x0 + (scol - 1) * bw
        f.rect(cxx - 1, ry - 3, bw, 30, "a", 3)
        f.text(x0 + max(len(rend), scol) * bw + 10, ry + 16, cnote, "t", 11)
    f.text(24, 360, "Screen columns count from 1 in ESC [ row ; col H: render column 8 is screen column 9.", "tm", 10.5)
    return f


RAW_0302 = ["kilo: kilo.c", "#   make$(CC) -o kilo kilo.c -Wall -W -pedan", "tic -st", "", "clean:",
            "        rm -f kilo", "", ".PHONY: all clean", "~", ""]
RENDER_0303 = ["", "kilo: kilo.c", "        $(CC) -o kilo kilo.c -Wall -W -peda", "", "clean:",
               "        rm -f kilo", "", ".PHONY: all clean", "~", ""]


def rawtabs():
    f = Fig("f0303b", "The Makefile after Page Down, with tabs sent to the terminal as they are and with tabs rendered", 330)
    f.text(24, 22, "the project's Makefile on a terminal 10 rows by 44 columns, after Page Down", "tm", 11)
    cw, rh = 5.6, 17
    for x, title, lines, bad in ((44, "at 03.02: the tab byte goes to the terminal", RAW_0302, {1, 2}),
                                 (360, "at 03.03: the row is drawn from render", RENDER_0303, set())):
        f.text(x - 6, 54, title, "ta" if bad else "t", 11.5, weight=600)
        screen(f, x, 68, lines, 44, cw, rh, cls_of=lambda r, bad=bad: "ta" if r in bad else "t")
    f.text(24, 268, "Left: the tab moved the cursor 8 columns without erasing them, and what was there before stays;", "tm", 10.5)
    f.text(24, 284, "the row, cut at 44 bytes, is 51 columns wide on the screen and wraps onto the next line, and the frame,", "tm", 10.5)
    f.text(24, 300, "one line too long, scrolls the screen up: the Makefile's empty line 9 has gone off the top.", "tm", 10.5)
    return f


# ------------------------------------------------------------------ 03.04

HELLO = ["#include <stdio.h>", "", "int main(void) {", "        printf(\"hello\\n\");", "        return 0;", "}", "~", "~"]


def bars():
    f = Fig("f0304a", "The status bar and the message line: the screen, and the bytes of its last two lines", 414)
    f.text(24, 22, "hello.c at 03.04 on a terminal 10 rows by 44 columns: 8 rows of text, then the two bars", "tm", 11)
    cw, rh = 6.4, 18
    x, y = 44, 44
    lines = HELLO + ["", ""]
    screen(f, x, y, lines, 44, cw, rh, cursor=(0, 0))
    status = "hello.c - 6 lines" + " " * 24 + "1/6"
    assert len(status) == 44
    by = y + 8 * rh
    f.rect(x, by + 2, 44 * cw, rh - 3, "fa", 0, sw=False)
    mono_runs(f, x, by + rh * 0.68, status, cw, "f")
    mono_runs(f, x, by + rh + rh * 0.68, "HELP: Ctrl-Q = quit", cw, "t")
    nx = x + 44 * cw + 26
    for r, text, cls in ((0, "rows 1 to 8: the file", "t"), (7, "E.screenrows = 10 - 2 = 8", "tm"),
                         (8, "row 9: the status bar", "ta"), (9, "row 10: the message line", "t")):
        yy = y + r * rh + 13
        f.line(nx - 20, yy - 4, nx - 6, yy - 4, "m")
        f.text(nx, yy, text, cls, 11, weight=600 if cls == "ta" else None)
    # the bytes of the last two lines
    ty = 260
    f.text(24, ty, "the end of the frame, after row 8's \\r\\n", "t", 11.5, weight=600)
    bx = 24
    y1 = ty + 40
    f.text(bx, y1, "ESC[0K ESC[7m", "ta", 10.5, mono=True)
    sx = bx + 14 * 6.3
    f.rect(sx - 2, y1 - 12, 44 * 6.3 + 4, 17, "af", 2, sw=False)
    mono_runs(f, sx, y1, status, 6.3, "t", 10.5)
    f.text(sx + 44 * 6.3 + 6, y1, "ESC[0m \\r\\n", "ta", 10.5, mono=True)
    f.brace_h(sx, sx + 17 * 6.3, y1 + 8, "m")
    f.text(sx, y1 + 26, "\"%.20s - %d lines\"", "tm", 10, mono=True)
    f.brace_h(sx + 17 * 6.3 + 2, sx + 41 * 6.3 - 2, y1 + 8, "m")
    f.text(sx + 29 * 6.3, y1 + 26, "24 spaces", "tm", 10, "middle")
    f.brace_h(sx + 41 * 6.3, sx + 44 * 6.3, y1 + 8, "m")
    f.text(sx + 44 * 6.3 + 2, y1 - 18, "\"%d/%d\", ending at column 44", "tm", 10, "end")
    y2 = y1 + 52
    f.text(bx, y2, "ESC[0K", "ta", 10.5, mono=True)
    mono_runs(f, bx + 7 * 6.3, y2, "HELP: Ctrl-Q = quit", 6.3, "t", 10.5)
    f.text(bx + 27 * 6.3, y2, "no \\r\\n: the frame ends on the bottom line", "tm", 10.5)
    f.text(bx, y2 + 24, "ESC[1;1H ESC[?25h", "ta", 10.5, mono=True)
    f.text(bx + 18 * 6.3, y2 + 24, "the cursor back to the file, at row 1, column 1, and shown", "tm", 10.5)
    return f


FIGS = [
    ("03.01-rows", rows),
    ("03.02-window", window),
    ("03.03-render", render),
    ("03.03-rawtabs", rawtabs),
    ("03.04-bars", bars),
]


def main():
    for name, fn in FIGS:
        print(write(MOD, name, fn()))


if __name__ == "__main__":
    main()
