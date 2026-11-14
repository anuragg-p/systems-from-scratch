"""Figures for kilo module 00, The workbench (lessons 00.01, 00.02).

    python3 -B art/kilo/figs00.py

Every byte and screen drawn here is from a real run of the finished editor on a
pseudo-terminal (macOS, Apple clang), turned into a screen by the Screen class in
tracks/kilo/track.py:
  00.01  ./kilo hello.txt on 10 x 44, a new file: Hello, Enter, world, then "!";
         the frame that "!" made is 192 bytes.
  00.02  ./kilo ab.txt on 6 x 20, the file "ab\\n": the first screen is 108 bytes,
         recorded with script(1). The key bytes are what the project at 01.01
         printed for each key.
"""
import os
import re

import figlib
from figlib import Fig, write, tw

figlib.LESSONS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                              "tracks", "kilo", "lessons")
MOD = "00-workbench"


def segments(line):
    """(column, text) for each piece of a line between runs of two or more spaces: SVG
    collapses spaces, so a status bar's right part is placed by its column."""
    out = [(m.start(), m.group(0)) for m in re.finditer(r"\S+(?: \S+)*", line)]
    return out


def screen(f, x, y, lines, cols, rev=(), cursor=None, size=10.5, rh=14):
    """A terminal screen: one mono line per row, a frame around it, reversed rows on the
    accent fill, and the cursor as an accent outline around its cell."""
    cw = size * 0.6
    w = cols * cw + 16
    f.rect(x, y, w, len(lines) * rh + 12, "s fs", 6)
    for i, line in enumerate(lines):
        ty = y + 6 + i * rh
        if i in rev:
            f.rect(x + 8, ty, cols * cw, rh, "af", 0, sw=False)
        if cursor and cursor[0] == i:
            f.rect(x + 8 + cursor[1] * cw, ty + 1, cw, rh - 2, "a", 1)
        for col, text in segments(line):
            f.text(x + 8 + col * cw, ty + rh - 3.5, text, "ta" if i in rev else "t", size, mono=True)
    return w


# ------------------------------------------------------------------ 00.01

def one_key():
    f = Fig("f0001a", "One key through the finished kilo: ! typed at the end of world", 446)
    f.text(24, 22, "./kilo hello.txt on a 10 x 44 terminal; the file holds Hello and world, the cursor is after world", "tm", 11)
    rows = [
        ("the terminal", "turns the key ! into one byte, 0x21, and writes it", "module 00"),
        ("raw mode", "the kernel passes it on at once, unechoed", "module 01"),
        ("editorReadKey()", "reads one key: 33, the code of !", "module 01"),
        ("editorProcessKeypress()", "has no case of its own for 33, so it is text", "module 04"),
        ("editorInsertChar(33)", "E.row[1]: world -> world!", "module 04"),
        ("editorRefreshScreen()", "the whole screen, drawn from E: 192 bytes", "modules 02, 03"),
        ("write()", "one call; the terminal draws the screen below", "module 02"),
    ]
    y0, rh, gap = 38, 26, 6
    for i, (name, what, mod) in enumerate(rows):
        y = y0 + i * (rh + gap)
        f.rect(48, y, 464, rh, "s f", 6)
        f.text(60, y + 17, name, "t", 12, weight=600, mono=name != "the terminal" and name != "raw mode")
        f.text(232, y + 17, what, "tm", 11.5, mono=what.startswith("E.row"))
        if what.startswith("E.row"):
            f.text(412, y + 17, "E.cx: 5 -> 6", "tm", 11.5, mono=True)
        f.rect(520, y + 3, 96, rh - 6, "a af", 10)
        f.text(568, y + 17, mod, "ta", 10.5, "middle", 600)
    # the loop: after the write, back to the top for the next key
    ytop = y0 + rh / 2
    ybot = y0 + (len(rows) - 1) * (rh + gap) + rh / 2
    f.path(f"M47 {ybot} H30 V{ytop} H46", "a", arrow=True)
    yb = y0 + len(rows) * (rh + gap)
    # the loop: from the screen back up to the next key
    f.path(f"M32 {y0 + rh / 2} L32 {y0 + 6 * (rh + gap) + rh / 2}", "m")
    f.line(32, y0 + rh / 2, 46, y0 + rh / 2, "s", arrow=True, start=False)
    f.text(24, yb + 8, "then main()'s loop waits for the next key", "tm", 11)
    lines = ["Hello", "world!", "~", "~", "~", "~", "~", "~",
             "hello.txt - 2 lines (modified)           2/2",
             "HELP: Ctrl-S = save | Ctrl-Q = quit | Ctrl-F"]
    sy = yb + 22
    w = screen(f, 24, sy, lines, 44, rev={8}, cursor=(1, 6))
    tx = 24 + w + 20
    f.text(tx, sy + 18, "the screen after !", "t", 12, weight=600)
    f.text(tx, sy + 38, "10 rows of 44 columns:", "tm", 11)
    f.text(tx, sy + 54, "8 for the file (~ past its end),", "tm", 11)
    f.text(tx, sy + 70, "the status bar in reverse video,", "tm", 11)
    f.text(tx, sy + 86, "the message line, cut at 44.", "tm", 11)
    f.text(tx, sy + 110, "The cursor is drawn last: row 2,", "tm", 11)
    f.text(tx, sy + 126, "column 7, just after the !", "tm", 11)
    return f


# ------------------------------------------------------------------ 00.02

KEYS = [
    ("a", [(97, "a")], "itself, in ASCII"),
    ("Enter", [(13, "CR")], "a carriage return"),
    ("Tab", [(9, "HT")], ""),
    ("Backspace", [(127, "DEL")], ""),
    ("Ctrl-Q", [(17, "DC1")], "'q' is 113; 113 & 0x1f = 17"),
    ("Escape", [(27, "ESC")], ""),
    ("Up", [(27, "ESC"), (91, "["), (65, "A")], "ESC [ A"),
    ("Home", [(27, "ESC"), (91, "["), (72, "H")], "ESC [ H; some send ESC O H"),
    ("Delete", [(27, "ESC"), (91, "["), (51, "3"), (126, "~")], "ESC [ 3 ~"),
    ("Page Down", [(27, "ESC"), (91, "["), (54, "6"), (126, "~")], "ESC [ 6 ~"),
]


def keys():
    f = Fig("f0002a", "What ten keys send: one byte, or an escape sequence of three or four", 418)
    f.text(24, 22, "decimal byte values, as the project at 01.01 prints them; under each, its name or character", "tm", 11)
    y0, rh = 40, 34
    bx, bw, bg = 132, 44, 6
    for i, (key, bytes_, note) in enumerate(KEYS):
        y = y0 + i * rh
        seq = len(bytes_) > 1
        f.text(24, y + 17, key, "t", 12.5, weight=600)
        for k, (v, name) in enumerate(bytes_):
            x = bx + k * (bw + bg)
            esc = name == "ESC"
            f.rect(x, y, bw, 26, "a af" if esc else "s f", 4)
            f.text(x + bw / 2, y + 12, str(v), "ta" if esc else "t", 11.5, "middle", 600, True)
            f.text(x + bw / 2, y + 23, name, "ta" if esc else "tm", 9, "middle", None, True)
        if note:
            f.text(bx + 4 * (bw + bg) + 14, y + 17, note, "t" if seq else "tm", 11.5, mono=seq and "some" not in note)
    yb = y0 + len(KEYS) * rh + 14
    f.text(24, yb, "A key that has a character sends that character's byte. A key that has none sends ESC (27)", "tm", 11)
    f.text(24, yb + 16, "and a few more bytes: the same 27 the Escape key sends on its own.", "tm", 11)
    return f


# The first screen of ./kilo ab.txt on a 6 x 20 terminal: 108 bytes, in order.
FRAME = [
    ("ESC[?25l ESC[H", "hide the cursor; go to row 1, column 1"),
    ("ab ESC[0K \\r\\n", "a row of the file, erased to its end"),
    ("~ ESC[0K \\r\\n", "a row past the end of the file"),
    ("~ ESC[0K \\r\\n", ""),
    ("~ ESC[0K \\r\\n", ""),
    ("ESC[0K ESC[7m ab.txt - 1 lines 1/1 ESC[0m \\r\\n", "the status bar, in reverse video"),
    ("ESC[0K HELP: Ctrl-S = save ", "the message, cut at 20 columns"),
    ("ESC[1;1H ESC[?25h", "the cursor to row 1, column 1; show it"),
]
SCREEN = ["ab", "~", "~", "~", "ab.txt - 1 lines 1/1", "HELP: Ctrl-S = save"]


def first_screen():
    f = Fig("f0002b", "kilo's first screen, as bytes and as the terminal draws it", 344)
    f.text(24, 22, "./kilo ab.txt on a 6 x 20 terminal, the file holding ab: 108 bytes in one write()", "tm", 11)
    y0, rh = 40, 30
    sx = 392
    cw = 6.9
    f.rect(sx - 10, y0 + rh - 5, 20 * cw + 20, 6 * rh + 2, "s fs", 6)
    for i, (bytes_, what) in enumerate(FRAME):
        y = y0 + i * rh
        f.rect(24, y, 306, 22, "s f", 4)
        f.text(32, y + 15, bytes_, "t", 10.5, mono=True)
        if 1 <= i <= 6:
            r = i - 1
            f.line(334, y + 11, sx - 16, y + 11, "m", arrow=True)
            if r == 4:
                f.rect(sx, y + 2, 20 * cw, 18, "af", 0, sw=False)
            if r == 0:
                f.rect(sx, y + 3, cw, 16, "a", 1)
            f.text(sx, y + 15, SCREEN[r], "ta" if r == 4 else "t", 11.5, mono=True)
        else:
            f.text(sx - 10, y + 15, what, "tm", 10.5)
    yb = y0 + len(FRAME) * rh + 14
    f.text(24, yb, "ESC is the one byte 27, so ESC[0K is four bytes: 27 [ 0 K. Everything that is not part of an escape", "tm", 11)
    f.text(24, yb + 16, "sequence is printed where the cursor is. ESC[?25l and ESC[?25h hide and show the cursor; ESC[H and", "tm", 11)
    f.text(24, yb + 32, "ESC[1;1H move it to row 1, column 1; ESC[0K erases from it to the end of the line; ESC[7m and ESC[0m", "tm", 11)
    f.text(24, yb + 48, "turn reverse video on and off; \\r\\n, carriage return and line feed, start the next row at column 1.", "tm", 11)
    return f


FIGS = [
    ("00.01-one-key", one_key),
    ("00.02-keys", keys),
    ("00.02-first-screen", first_screen),
]


def main():
    for name, fn in FIGS:
        print(write(MOD, name, fn()))


if __name__ == "__main__":
    main()
