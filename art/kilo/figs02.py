"""Figures for kilo module 02, The screen (lesson 02.01).

    python3 -B art/kilo/figs02.py      writes tracks/kilo/lessons/02-screen/figures/02.01-*.svg

Every byte and count here is from a real run of the project as it stands at 02.01
(./learn files kilo --at 02.01), on a pseudo-terminal, its output fed to the Screen
emulator in tracks/kilo/track.py:
  frame    the first frame on a 10 x 44 terminal: 116 bytes, one write()
  writes   four screens on 24 x 80 (start, then Ctrl-L three times), counted with a write()
           interposer: 4 calls and 928 bytes; with abAppend() writing each piece at once,
           the same 928 bytes take 204 calls (51 a frame: the pieces listed in PIECES_24x80)
The module's cover and icon are not made here.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import figlib  # noqa: E402
from figlib import Fig, write  # noqa: E402

figlib.LESSONS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                              "tracks", "kilo", "lessons")
MOD = "02-screen"


# ------------------------------------------------------------------ helpers (figs03.py uses them too)

def mono_runs(f, x, y, s, cw, cls="t", size=None):
    """Text s in a monospace grid of cw px a column, each run of non-spaces placed at its own
    column (SVG would collapse the spaces between them)."""
    size = size or cw / 0.6
    col = 0
    for part in s.split(" "):
        if part:
            f.text(x + col * cw, y, part, cls, size, mono=True)
        col += len(part) + 1


def screen(f, x, y, lines, cols, cw=6.0, rh=18, cursor=None, label_rows=True, cls_of=None, frame_cls="s fs"):
    """A terminal screen: a box of len(lines) rows x cols columns, each line's text drawn at its
    columns, an optional cursor cell (row, col from 0), row numbers from 1 on the left."""
    w = cols * cw
    h = len(lines) * rh
    f.rect(x - 6, y - 4, w + 12, h + 8, frame_cls, 6)
    if cursor:
        r, c = cursor
        f.rect(x + c * cw - 0.5, y + r * rh + 2, cw + 1, rh - 4, "a af", 1)
    for r, line in enumerate(lines):
        cls = cls_of(r) if cls_of else "t"
        mono_runs(f, x, y + r * rh + rh * 0.68, line, cw, cls)
        if label_rows:
            f.text(x - 12, y + r * rh + rh * 0.68, str(r + 1), "tm", 9.5, "end", mono=True)
    return w, h


# ------------------------------------------------------------------ 02.01

# The first frame at 02.01 on 10 x 44, as kilo wrote it: (screen row from 1 or None, pieces).
# A piece is (text, kind): "c" what the screen shows, "e" an escape sequence or \r\n.
WELCOME = "~    Kilo editor -- version 0.0.1"


def frame():
    f = Fig("f0201a", "One frame on a 10 x 44 terminal: the bytes kilo writes, and the screen they draw", 358)
    f.text(24, 22, "kilo at 02.01 on a terminal 10 rows by 44 columns: its first frame, 116 bytes, one write()", "tm", 11)
    cw = 6.0
    lx = 24                      # the bytes
    sx = 346                     # the screen
    top = 80
    rh = 20
    f.text(lx, 52, "the bytes, in the order they are written", "t", 11.5, weight=600)
    f.text(sx - 6, 52, "the screen they draw", "t", 11.5, weight=600)

    def pieces(y, items):
        x = lx
        for text, kind in items:
            if kind == "c":
                mono_runs(f, x, y, text, cw, "t")
            else:
                f.text(x, y, text, "ta", 10, mono=True)
            x += (len(text) + 1) * cw
        return x

    # before the rows
    y = top - 6
    pieces(y, [("ESC[?25l", "e"), ("ESC[H", "e")])
    f.text(lx + 15 * cw, y, "hide the cursor; go to row 1, column 1", "tm", 10.5)
    rows = []
    for r in range(9):
        if r == 3:
            rows.append([(WELCOME, "c"), ("ESC[0K", "e"), ("\\r\\n", "e")])
        else:
            rows.append([("~", "c"), ("ESC[0K", "e"), ("\\r\\n", "e")])
    for r, items in enumerate(rows):
        yy = top + 10 + r * rh + 13
        end = pieces(yy, items)
        if r in (0, 4):
            f.text(end + 4, yy, "erase to the end of the line, next line" if r == 0 else "every line the same way", "tm", 10.5)
    yy = top + 10 + 9 * rh + 13
    f.text(lx, yy, "row 10: nothing. A \\r\\n here would scroll the screen up", "tm", 10.5)
    y2 = top + 10 + 10 * rh + 18
    pieces(y2, [("ESC[1;1H", "e"), ("ESC[?25h", "e")])
    f.text(lx + 18 * cw, y2, "cursor to row 1, column 1; show it", "tm", 10.5)
    f.text(lx, y2 + 22, "ESC is the one byte 27; \\r\\n are the two bytes 13 and 10.", "tm", 10.5)
    f.text(lx, y2 + 38, "9 + 8 x 7 + 39 + 6 + 6 = 116 bytes, handed to write() once.", "tm", 10.5)

    lines = ["~"] * 9 + [""]
    lines[3] = WELCOME
    screen(f, sx, top + 10, lines, 44, cw, rh, cursor=(0, 0))
    f.text(sx + 44 * cw, top + 10 + 10 * rh + 18, "the cursor: row 1, column 1", "ta", 10.5, "end")
    return f


# The pieces abAppend() is handed for one frame on 24 x 80 at 02.01, in order, in bytes:
# hide 6, home 3, 7 rows of "~ ESC[0K \r\n" (7 each), the welcome row as "~", 22 single
# spaces and the 34-byte welcome, 15 more rows, the cursor move 6, show 6. Written at once,
# each is a write() of its own, and the final write() of the empty buffer is one more.
PIECES_24x80 = [6, 3] + [7] * 7 + [1] + [1] * 22 + [34] + [7] * 15 + [6, 6, 0]


def writes():
    assert len(PIECES_24x80) == 51 and sum(PIECES_24x80) == 232
    f = Fig("f0201b", "Four screens, the same 928 bytes: 4 write() calls with the frame buffer, 204 without", 236)
    f.text(24, 22, "kilo at 02.01 on 24 x 80: the first screen and three Ctrl-L, 928 bytes in all; each mark is one write()", "tm", 11)
    x0, w = 24, 592
    sc = w / 928.0
    rows = [(54, "a frame built in memory, then one write(): 4 calls", "a af", "ta"),
            (136, "every piece written at once: 204 calls", "s fs", "t")]
    for y, label, cls, tcls in rows:
        f.text(x0, y - 10, label, tcls, 12, weight=600)
    # top: one block a frame
    for k in range(4):
        f.rect(x0 + k * 232 * sc, 54, 232 * sc, 34, "a af", 2)
        f.text(x0 + k * 232 * sc + 116 * sc, 76, f"frame {k + 1}: 232 bytes", "ta", 11, "middle")
    # bottom: one mark a call, at the byte where it starts
    y = 136
    f.rect(x0, y, w, 34, "m f", 2)
    pos = 0
    for k in range(4):
        for n in PIECES_24x80:
            xx = x0 + pos * sc
            f.add(f'<line class="s" x1="{xx:.2f}" y1="{y}" x2="{xx:.2f}" y2="{y + 34}" stroke-width="0.6"/>')
            pos += n
    for k in range(4):
        f.line(x0 + k * 232 * sc, y - 2, x0 + k * 232 * sc, y + 36, "a")
    f.line(x0 + w, y - 2, x0 + w, y + 36, "a")
    wx = x0 + (9 + 49 + 1) * sc
    f.brace_h(wx, wx + 22 * sc, y + 42, "m")
    f.text(wx - 4, y + 60, "the welcome's padding: 22 writes of one space each", "tm", 10.5)
    f.text(x0, 222, "Between any two writes the terminal may show the screen: written in pieces, a frame can be seen half drawn.", "tm", 11)
    return f


FIGS = [
    ("02.01-frame", frame),
    ("02.01-writes", writes),
]


def main():
    for name, fn in FIGS:
        print(write(MOD, name, fn()))


if __name__ == "__main__":
    main()
