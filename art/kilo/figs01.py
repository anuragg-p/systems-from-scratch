"""Figures for kilo module 01, The terminal (lessons 01.01, 01.02, 01.03).

    python3 -B art/kilo/figs01.py

Every value is from a real run of the project at the lesson, on a pseudo-terminal
(macOS, Apple clang):
  01.01  the bytes a, Enter and Ctrl-C arrive as 97, 13 and 3 in raw mode; with ICRNL
         left on Enter arrives as 10, with ISIG left on Ctrl-C kills kilo (SIGINT).
         The flags are the ones enableRawMode() changes.
  01.02  the codes the project at 01.02 printed for each sequence; a lone Escape came
         back as 27 after 0.100 s, an arrow at once; Escape and then "[A" half a second
         later printed 27, 91, 65.
  01.03  on a pseudo-terminal whose size the kernel did not know (0 x 0), with a
         24 x 80 terminal answering ESC [ 6 n, kilo wrote
         ESC[6n ESC[999C ESC[999B ESC[6n ESC[1;1H and printed "This window has 24 rows
         and 80 columns."; the answers were ESC[1;1R and ESC[24;80R.
"""
import os

import figlib
from figlib import Fig, write

figlib.LESSONS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                              "tracks", "kilo", "lessons")
MOD = "01-terminal"


def bytebox(f, x, y, v, name, cls="s f", tcls="t", w=40, h=30):
    f.rect(x, y, w, h, cls, 4)
    f.text(x + w / 2, y + 13, str(v), tcls, 11.5, "middle", 600, True)
    f.text(x + w / 2, y + 25, name, "ta" if tcls == "ta" else "tm", 9, "middle", None, True)


# ------------------------------------------------------------------ 01.01

def cooked_raw():
    f = Fig("f0101a", "Three keys, a then Enter then Ctrl-C, through the terminal driver in each mode", 318)
    lanes = [
        (24, "cooked: how the shell leaves the terminal", "s fs", "t",
         ["97: echoed to the screen, kept", "13: made 10 (ICRNL): the line is done",
          "3: not passed on: SIGINT (ISIG)"],
         ["read() returns 97 10,", "both at once, after Enter;", "then the program is killed"]),
        (162, "raw: how kilo sets it", "a af", "ta",
         ["every byte passed on as it comes,", "unchanged and not echoed"],
         ["read() returns 97,", "then 13, then 3,", "each as it is typed"]),
    ]
    for y, title, cls, tcls, driver, out in lanes:
        f.text(24, y + 12, title, tcls, 12.5, weight=700)
        by = y + 34
        for k, (v, key) in enumerate(((97, "a"), (13, "Enter"), (3, "Ctrl-C"))):
            bytebox(f, 24 + k * 46, by + 20, v, key, w=42, h=32)
        f.text(24, by + 10, "the terminal sends", "tm", 10.5)
        f.line(164, by + 36, 190, by + 36, "s", arrow=True)
        f.rect(192, by, 236, 88, cls, 8)
        f.text(204, by + 18, "the terminal driver", tcls, 11.5, weight=600)
        for i, line in enumerate(driver):
            f.text(204, by + 38 + i * 17, line, "t", 11)
        f.line(432, by + 36, 458, by + 36, "s", arrow=True)
        f.text(462, by + 10, "the program gets", "tm", 10.5)
        for i, line in enumerate(out):
            f.text(462, by + 30 + i * 17, line, "t", 11.5, mono=i == 0)
    f.text(24, 308, "Raw mode is the same terminal with the driver's processing switched off, flag by flag.", "tm", 11)
    return f


FLAGS = [
    ("c_iflag &= ~", "BRKINT", "a break on the line no longer sends SIGINT"),
    ("", "ICRNL", "Enter's 13 is no longer turned into 10"),
    ("", "INPCK", "no parity check on input"),
    ("", "ISTRIP", "the 8th bit of each byte is kept"),
    ("", "IXON", "Ctrl-S and Ctrl-Q reach the program: no flow control"),
    ("c_oflag &= ~", "OPOST", "output goes out as written: \\n is not made \\r\\n"),
    ("c_cflag |=", "CS8", "8-bit characters"),
    ("c_lflag &= ~", "ECHO", "nothing typed is echoed"),
    ("", "ICANON", "each byte as it comes, not a line at a time"),
    ("", "IEXTEN", "no extra keys: Ctrl-V reaches the program"),
    ("", "ISIG", "Ctrl-C, Ctrl-Z, Ctrl-\\ are bytes, not signals"),
    ("c_cc[] =", "VMIN 0", "read() may return with no byte at all"),
    ("", "VTIME 1", "after waiting at most 0.1 s for one"),
]


def flags():
    f = Fig("f0101b", "What enableRawMode() changes in the terminal's settings", 384)
    f.text(24, 22, "struct termios, a copy of orig_termios; each line is what the flag's change does", "tm", 11)
    y0, rh = 36, 24
    for i, (field, name, what) in enumerate(FLAGS):
        y = y0 + i * rh
        if field:
            if i:
                f.line(24, y - 2, 616, y - 2, "m")
            f.text(24, y + 15, field, "t", 11.5, weight=600, mono=True)
        f.rect(150, y + 2, 74, 18, "a af", 4)
        f.text(187, y + 15, name, "ta", 11, "middle", 600, True)
        f.text(236, y + 15, what, "t", 11.5)
    f.line(24, y0 + len(FLAGS) * rh - 2, 616, y0 + len(FLAGS) * rh - 2, "m")
    f.text(24, y0 + len(FLAGS) * rh + 18, "Then tcsetattr(fd, TCSAFLUSH, &raw): the change waits for pending output, and throws", "tm", 11)
    f.text(24, y0 + len(FLAGS) * rh + 34, "away input typed before it.", "tm", 11)
    return f


# ------------------------------------------------------------------ 01.02

SEQS = [
    ("ESC [ letter", [("A", 1002, "Up"), ("B", 1003, "Down"), ("C", 1001, "Right"), ("D", 1000, "Left"),
                      ("H", 1005, "Home"), ("F", 1006, "End")]),
    ("ESC [ digit ~", [("3", 1004, "Delete"), ("5", 1007, "Page Up"), ("6", 1008, "Page Down")]),
    ("ESC O letter", [("H", 1005, "Home"), ("F", 1006, "End")]),
]


def decode():
    f = Fig("f0102a", "editorReadKey(): one byte, or ESC and the bytes after it, become one key", 504)
    # the first questions
    f.rect(24, 20, 150, 34, "s f", 6)
    f.text(99, 42, "read one byte", "t", 12, "middle", 600)
    f.line(174, 37, 214, 37, "s", arrow=True)
    f.text(194, 30, "not 27", "tm", 10.5, "middle")
    f.rect(216, 20, 400, 34, "s fs", 6)
    f.text(228, 42, "that byte is the key: a is 97, Enter 13, Ctrl-Q 17", "t", 11.5)
    f.line(99, 54, 99, 76, "a", arrow=True)
    f.text(106, 70, "27, ESC", "ta", 10.5, weight=600)
    f.rect(24, 78, 150, 34, "a af", 6)
    f.text(99, 93, "two more bytes,", "ta", 11.5, "middle", 600)
    f.text(99, 107, "each within 0.1 s?", "ta", 11.5, "middle", 600)
    f.line(174, 95, 214, 95, "s", arrow=True)
    f.text(194, 88, "no", "tm", 10.5, "middle")
    f.rect(216, 78, 400, 34, "s fs", 6)
    f.text(228, 100, "the Escape key itself: 27", "t", 11.5)
    f.line(99, 112, 99, 134, "s", arrow=True)
    f.text(106, 128, "yes", "tm", 10.5)
    # the sequences
    y = 140
    for name, rows in SEQS:
        h = 14 + len(rows) * 20
        f.rect(24, y, 150, h, "s f", 6)
        f.text(36, y + 20, name, "t", 12, weight=600, mono=True)
        for k, (ch, code, key) in enumerate(rows):
            ry = y + 7 + k * 20
            f.text(216, ry + 13, f"{name.split()[0]} {name.split()[1]} {ch}" + (" ~" if "~" in name else ""), "t", 11.5, mono=True)
            f.text(340, ry + 13, str(code), "ta", 11.5, weight=600, mono=True)
            f.text(392, ry + 13, key, "t", 11.5)
        f.line(174, y + 14, 210, y + 14, "s", arrow=True)
        y += h + 8
    f.rect(24, y, 150, 34, "m f", 6, dash=True)
    f.text(36, y + 21, "anything else", "tm", 12, weight=600)
    f.line(174, y + 17, 210, y + 17, "m", arrow=True)
    f.text(216, y + 14, "not a key kilo knows (Insert is ESC [ 2 ~): go round and read on;", "tm", 11)
    f.text(216, y + 29, "with nothing more within 0.1 s, the key is 27", "tm", 11)
    f.text(24, y + 58, "The codes are kilo's own, from 1000 up: above 255, so no byte can be mistaken for one.", "tm", 11)
    return f


def timing():
    f = Fig("f0102b", "Three ways the byte 27 can arrive, on a time line", 256)
    X0, X1 = 150, 610
    T = 0.6
    px = lambda t: X0 + (X1 - X0) * t / T
    f.text(24, 22, "what the project at 01.02 printed, and when; read() waits at most 0.1 s for a byte", "tm", 11)
    ax = 214
    f.line(X0, ax, X1, ax, "m")
    for t in (0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6):
        f.line(px(t), ax - 4, px(t), ax + 4, "m")
        f.text(px(t), ax + 18, f"{t:.1f} s", "tm", 10.5, "middle", mono=True)
    lanes = [
        (48, "Up", [(0, ["27", "91", "65"])], [(0, "1002, at once")]),
        (104, "Escape", [(0, ["27"])], [(0.1, "27, after 0.1 s")]),
        (160, "Escape, then [ A", [(0, ["27"]), (0.5, ["91", "65"])], [(0.1, "27"), (0.5, "91, 65")]),
    ]
    for y, name, ins, outs in lanes:
        f.text(24, y + 14, name, "t", 12, weight=600)
        f.line(X0, y + 10, X1, y + 10, "m")
        for t, group in ins:
            for k, b in enumerate(group):
                x = px(t) + k * 28
                f.rect(x - 1, y - 2, 26, 22, "a af" if b == "27" else "s f", 3)
                f.text(x + 12, y + 13, b, "ta" if b == "27" else "t", 10.5, "middle", 600, True)
        for t, label in outs:
            f.text(px(t) + 4 if t > 0.05 else px(t) + 92, y + (36 if t > 0.05 else 13), label, "ta", 11, "start", 600)
            if t >= 0.1:
                f.line(px(t), y + 22, px(t), y + 26, "a")
        if name == "Escape":
            f.brace_h(px(0) + 26, px(0.1), y + 26, "a")
    f.text(24, 246, "The bytes of a sequence come in one write from the terminal; typed by hand, they come far apart.", "tm", 11)
    return f


# ------------------------------------------------------------------ 01.03

def ask():
    f = Fig("f0103a", "Two ways to learn the window's size: ask the kernel, or ask the terminal", 348)
    # the kernel
    f.text(24, 22, "the usual way: the kernel knows", "t", 12.5, weight=700)
    f.rect(24, 34, 250, 34, "s f", 6)
    f.text(36, 56, "ioctl(1, TIOCGWINSZ, &ws)", "t", 11.5, mono=True)
    f.line(274, 51, 300, 51, "s", arrow=True)
    f.rect(302, 34, 314, 34, "a af", 6)
    f.text(314, 56, "ws.ws_row = 24", "ta", 11.5, weight=600, mono=True)
    f.text(450, 56, "ws.ws_col = 80", "ta", 11.5, weight=600, mono=True)
    f.text(24, 88, "The terminal tells the kernel its size when it opens and on every resize.", "tm", 11)
    # the terminal
    f.text(24, 124, "when the kernel says 0 columns: ask the terminal", "t", 12.5, weight=700)
    kx, tx = 120, 520
    f.rect(kx - 54, 136, 108, 28, "s f", 6)
    f.text(kx, 155, "kilo", "t", 12, "middle", 600)
    f.rect(tx - 64, 136, 128, 28, "s f", 6)
    f.text(tx, 155, "the terminal", "t", 12, "middle", 600)
    f.line(kx, 164, kx, 334, "m", dash=True)
    f.line(tx, 164, tx, 334, "m", dash=True)
    steps = [
        (186, "ESC[6n", True, "where is the cursor?"),
        (214, "ESC[1;1R", False, "row 1, column 1"),
        (242, "ESC[999C ESC[999B", True, "right and down: it stops at the edges"),
        (270, "ESC[6n", True, ""),
        (298, "ESC[24;80R", False, "row 24, column 80: the size"),
        (326, "ESC[1;1H", True, "back to where it was"),
    ]
    for y, seq, out, note in steps:
        if out:
            f.line(kx + 2, y, tx - 4, y, "s", arrow=True)
            f.text(kx + 10, y - 5, seq, "t", 11, mono=True, weight=600)
        else:
            f.line(tx - 2, y, kx + 4, y, "a", arrow=True)
            f.text(tx - 10, y - 5, seq, "ta", 11, "end", 600, True)
        if note and out:
            f.text(tx - 10, y - 5, note, "tm", 10.5, "end")
        elif note:
            f.text(kx + 10, y - 5, note, "tm", 10.5)
    return f


FIGS = [
    ("01.01-cooked-raw", cooked_raw),
    ("01.01-flags", flags),
    ("01.02-decode", decode),
    ("01.02-timing", timing),
    ("01.03-ask", ask),
]


def main():
    for name, fn in FIGS:
        print(write(MOD, name, fn()))


if __name__ == "__main__":
    main()
