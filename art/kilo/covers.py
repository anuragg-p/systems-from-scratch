"""The kilo track's module art and track art.

    python3 -B art/kilo/covers.py

writes, for each module NN under tracks/kilo/lessons/, cover.svg (640x300, a picture of
the idea the module teaches) and icon.svg (20x20 line icon), and the track's own
art.svg (the home page card, 280x160) and icon.svg.

Every value a cover shows was read off the editor itself, run on a pseudo-terminal of
the size the cover names (the reference kilo.c, or the project at 02.01 for 02):

  00  6 x 20, f.txt "ab\\n": the first frame is 108 bytes, exactly the ones drawn.
  01  the codes editorReadKey() returns: 'a' 97, Up 1002, Page Down 1008, Escape 27
      (enum KEY_ACTION; NOTES.md 01.02).
  02  at 02.01 on 10 x 44: 18 abAppend() calls build a 116-byte frame, one write().
  03  8 x 24, twelve rows "this is wider than the screen N"; Down x8, Up x3,
      Right x31, Left x8: rowoff 3, coloff 8, cursor (2, 15), status "6/12". The rows
      end one column short of the window's edge, and column 7 is a space: no glyph
      touches the window's frame, and the screen's last column (which kilo's ESC [ 0 K
      erases on a VT100) is empty.
  04  "hello world", Right x5, ',' then Enter: rows "hello," and " world"; Ctrl-S
      writes 14 bytes.
  05  NOTES.md's C file on 10 x 44, Ctrl-F then r, e, t: "r" puts row 3 on top (4/6),
      "re" and "ret" row 4 (5/6), cursor at screen column 8 after the tab.

Text in these SVGs is placed a run of non-spaces at a time, at its column: SVG
collapses runs of spaces, and a screen's columns must line up.
"""
import os

import figart

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TRACK = os.path.join(ROOT, "tracks", "kilo")
LESSONS = os.path.join(TRACK, "lessons")
MODULES = {"00": "00-workbench", "01": "01-terminal", "02": "02-screen", "03": "03-viewer",
           "04": "04-editor", "05": "05-search"}
SW = 'stroke-width="1.5"'


def n(v):
    """A coordinate, without float noise."""
    v = round(v, 2)
    return int(v) if v == int(v) else v


class Art(figart.Art):
    """figart.Art with rounded coordinates and monospaced text placed by column."""

    def box(self, x, y, w, h, cls="s f", rx=10, dash=False):
        super().box(n(x), n(y), n(w), n(h), cls, rx, dash)

    def fill(self, x, y, w, h, cls, rx=0):
        """A shape with no stroke: a highlight, a cursor, a reverse-video bar."""
        self.add(f'<rect class="{cls}" x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}" rx="{n(rx)}"/>')

    def text(self, x, y, s, cls="t", size=12, anchor="start", weight=None, mono=False):
        super().text(n(x), n(y), s, cls, n(size), anchor, weight, mono)

    def line(self, x1, y1, x2, y2, cls="s", arrow=False, dash=False):
        super().line(n(x1), n(y1), n(x2), n(y2), cls, arrow, dash)

    def mono(self, x, y, s, cls="t", size=12, weight=None):
        """s in a monospaced font from x, each run of non-spaces at its own column.
        Returns the x just past the last column."""
        cw = size * 0.6
        col = 0
        for word in s.split(" "):
            if word:
                self.text(x + col * cw, y, word, cls, size, weight=weight, mono=True)
            col += len(word) + 1
        return x + len(s) * cw


def cw(size):
    return size * 0.6


# ------------------------------------------------------------------ 00 the workbench

def workbench():
    a = Art("k00", "The bytes kilo writes for one screen, in one write(), and the screen a 6 x 20 terminal shows")
    a.text(24, 24, "what kilo writes: 108 bytes, in one write()", "tm", 11)
    a.text(430, 24, "what a 6 x 20 terminal shows", "tm", 11)
    size = 11.5
    rows = [70, 98, 126, 154, 182, 210]           # baselines of the screen's six rows

    def stream(y, tokens):
        x = 24
        for s, cls in tokens:
            x = a.mono(x, y, s, cls, size) + 4
        return x

    tilde = [("~", "t"), ("ESC[0K", "ta"), ("\\r\\n", "tm")]
    x = stream(46, [("ESC[?25l", "ta"), ("ESC[H", "ta")])
    a.text(x + 8, 46, "hide the cursor, go to the top left", "tm", 10.5)
    stream(rows[0], [("ab", "t"), ("ESC[0K", "ta"), ("\\r\\n", "tm")])
    for y in rows[1:4]:
        stream(y, tilde)
    stream(rows[4], [("ESC[0K", "ta"), ("ESC[7m", "ta"), ("f.txt - 1 lines  1/1", "t"), ("ESC[0m", "ta"), ("\\r\\n", "tm")])
    stream(rows[5], [("ESC[0K", "ta"), ("HELP: Ctrl-S = save ", "t")])
    x = stream(238, [("ESC[1;1H", "ta"), ("ESC[?25h", "ta")])
    a.text(x + 8, 238, "the cursor to row 1, column 1; show it", "tm", 10.5)

    # one write(): a bracket round the bytes, an arrow to the terminal
    a.path("M340 34 L346 34 L346 244 L340 244", "m")
    a.line(352, 140, 424, 140, "a", arrow=True)
    a.text(388, 131, "write()", "ta", 11.5, "middle", 600, mono=True)

    # the terminal: each row next to the bytes that drew it
    tx, tsize = 440, 14
    tcw = cw(tsize)
    a.box(428, 50, 192, 178, "s fs", rx=10)
    a.fill(tx, rows[0] - 13, tcw, 17, "fa", 1.5)                 # the cursor, on 'a'
    a.text(tx, rows[0], "a", "f", tsize, mono=True)
    a.text(tx + tcw, rows[0], "b", "t", tsize, mono=True)
    for y in rows[1:4]:
        a.text(tx, y, "~", "t", tsize, mono=True)
    a.fill(tx - 2, rows[4] - 14, 20 * tcw + 4, 19, "t", 2)        # reverse video
    a.mono(tx, rows[4], "f.txt - 1 lines  1/1", "f", tsize)
    a.mono(tx, rows[5], "HELP: Ctrl-S = save", "t", tsize)

    a.text(24, 284, "Then kilo reads one key (Up arrives as ESC [ A), acts on it, and writes the whole screen again.",
           "tm", 11.5)
    return a


# ------------------------------------------------------------------ 01 the terminal

def terminal():
    a = Art("k01", "Four keys, the bytes each sends, and the one key code editorReadKey() makes of them")
    a.text(24, 24, "key", "tm", 11)
    a.text(112, 24, "the bytes read() returns, in raw mode", "tm", 11)
    a.text(400, 24, "editorReadKey()", "t", 12, "middle", 600, mono=True)
    a.text(504, 24, "key code", "tm", 11)
    ys = [70, 124, 178, 232]
    keys = [
        ("a", [(97, "'a'")], "a byte", ("97", "'a'")),
        ("Up", [(27, "ESC"), (91, "["), (65, "A")], "ESC [ A", ("1002", "ARROW_UP")),
        ("Page Down", [(27, "ESC"), (91, "["), (54, "6"), (126, "~")], "ESC [ 6 ~", ("1008", "PAGE_DOWN")),
        ("Esc", [(27, "ESC")], "ESC alone", ("27", "ESC")),
    ]
    a.box(330, 38, 140, 230, "s fs", rx=10)
    for y, (key, bytes_, rule, (code, name)) in zip(ys, keys):
        a.box(24, y - 18, 72, 36, "s f", rx=7)
        a.text(60, y + 4.5, key, "t", 12.5, "middle", 600)
        x = 112
        for v, ch in bytes_:
            esc = ch == "ESC"
            a.box(x, y - 18, 40, 36, "a af" if esc else "s f", rx=5)
            a.text(x + 20, y + 1, str(v), "ta" if esc else "t", 12.5, "middle", 600, mono=True)
            a.text(x + 20, y + 13, ch, "ta" if esc else "tm", 9.5, "middle", mono=True)
            x += 46
        if key == "Esc":
            a.text(x + 2, y + 4, "then nothing for 0.1 s", "tm", 11)
            x += 138
        a.line(x - 2, y, 328, y, "s", arrow=True)
        a.text(400, y + 4, rule, "tm", 11, "middle", mono=True)
        big = int(code) >= 1000
        a.line(472, y, 500, y, "a" if big else "s", arrow=True)
        a.text(506, y + 5, code, "ta" if big else "t", 15, weight=700, mono=True)
        a.text(506 + len(code) * cw(15) + 8, y + 4, name, "ta" if big else "tm", 10, mono=True)
    a.text(24, 290, "A sequence editorReadKey() knows becomes one code above 1000; a lone Escape is 27, once 0.1 s has passed.",
           "tm", 11.5)
    return a


# ------------------------------------------------------------------ 02 the screen

def screen():
    a = Art("k02", "One frame built in memory by 18 abAppend() calls, then sent to the terminal in one write()")
    a.text(24, 20, "struct abuf ab, at 02.01 on a 10 x 44 terminal: one abAppend() per cell", "tm", 11)
    segs = [6, 3, 7, 7, 7, 1, 1, 1, 1, 1, 34, 7, 7, 7, 7, 7, 6, 6]
    total = sum(segs)                                    # 116
    x0, y0, h = 24, 44, 30
    s = 592 / total
    acc = {0, 1, 16, 17}                                 # hide, home; cursor, show
    at = 0
    for i, b in enumerate(segs):
        x = x0 + at * s
        a.add(f'<rect class="{"a af" if i in acc else "s f"}" x="{n(x)}" y="{y0}" width="{n(b * s)}" height="{h}" {SW}/>')
        if b == 7:
            a.text(x + b * s / 2, y0 + 20, "~", "t", 11, "middle", mono=True)
        at += b
    a.text(x0 + (69 - 34 + 17) * s, y0 + 19, "Kilo editor -- version 0.0.1", "t", 9.5, "middle", mono=True)
    # ab.len where each part ends, and what each part is
    for v in (0, 9, 30, 69, 104, 116):
        a.text(x0 + v * s, y0 - 6, str(v), "tm", 9.5, "middle", mono=True)
    parts = [(0, 9, "hide, home"), (9, 30, "3 rows of ~"), (30, 69, "~, 4 spaces, the welcome"),
             (69, 104, "5 rows of ~"), (104, 116, "cursor, show")]
    for lo, hi, label in parts:
        xa, xb = x0 + lo * s + 2, x0 + hi * s - 2
        a.path(f"M{n(xa)} {y0 + h + 6} L{n(xa)} {y0 + h + 10} L{n(xb)} {y0 + h + 10} L{n(xb)} {y0 + h + 6}", "m")
        a.text((xa + xb) / 2, y0 + h + 26, label, "tm", 10.5, "middle")

    # the terminal, after the write
    tx, tsize, pitch = 392, 8.5, 13
    tcw = cw(tsize)
    a.box(384, 138, 232, 146, "s fs", rx=10)
    ys = [156 + j * pitch for j in range(10)]
    a.fill(tx, ys[0] - 8.5, tcw, 11, "fa", 1)
    a.text(tx, ys[0], "~", "f", tsize, mono=True)
    for j in range(1, 9):
        a.text(tx, ys[j], "~", "t", tsize, mono=True)
    a.mono(tx + 5 * tcw, ys[3], "Kilo editor -- version 0.0.1", "t", tsize)
    a.line(500, 110, 500, 134, "a", arrow=True)
    a.text(492, 128, "write(): 116 bytes", "ta", 11, "end", 600, mono=True)

    # building it, and sending it
    a.mono(24, 168, "abAppend() x 18", "t", 12.5, 600)
    a.text(24, 186, "into memory: nothing on the screen yet", "tm", 11.5)
    a.mono(24, 222, "write() x 1", "ta", 12.5, 600)
    a.text(24, 240, "the whole frame at once", "tm", 11.5)
    a.text(24, 274, "A write() per piece would be 18 calls,", "tm", 11.5)
    a.text(24, 290, "and the terminal could show any of them half drawn.", "tm", 11.5)
    return a


# ------------------------------------------------------------------ 03 a text viewer

def viewer():
    a = Art("k03", "The screen is a window onto the rows: rowoff and coloff place it, cx and cy are on the screen")
    size, pitch = 11, 17
    c = cw(size)
    fx, fy = 64, 62                                      # the file's column 0, row 0 baseline
    rowoff, coloff, rows, cols = 3, 8, 6, 24
    cy, cx = 2, 15
    a.text(24, 22, "E.row: the file's 12 rows", "tm", 11)
    # the window over the rows
    wx, wy = fx + coloff * c - 2, fy + rowoff * pitch - 13
    ww, wh = cols * c + 4, rows * pitch + 2
    a.box(wx, wy, ww, wh, "a af", rx=4)
    for i in range(12):
        y = fy + i * pitch
        line = f"this is wider than the screen {i + 1}"
        a.text(fx - 10, y, str(i), "ta" if rowoff <= i < rowoff + rows else "tm", 10, "end", mono=True)
        inside = rowoff <= i < rowoff + rows
        a.mono(fx, y, line[:coloff], "tm", size)
        a.mono(fx + coloff * c, y, line[coloff:], "t" if inside else "tm", size)
    # the cursor, in the file
    fr, fc = rowoff + cy, coloff + cx
    a.fill(fx + fc * c, fy + fr * pitch - 9.5, c, 13, "fa", 1)
    a.text(fx + fc * c, fy + fr * pitch, "s", "f", size, mono=True)
    # coloff across the top, rowoff down the right
    a.path(f"M{fx} 44 L{fx} 39 L{n(wx + 2)} 39 L{n(wx + 2)} 44", "a")
    a.text((fx + wx + 2) / 2, 33, "coloff 8", "ta", 10.5, "middle", 600, mono=True)
    rx = fx + 33 * c + 6
    a.path(f"M{n(rx)} {fy - 12} L{n(rx + 6)} {fy - 12} L{n(rx + 6)} {n(wy - 2)} L{n(rx)} {n(wy - 2)}", "a")
    a.text(rx + 12, (fy - 12 + wy) / 2 + 4, "rowoff 3", "ta", 10.5, weight=600, mono=True)

    # the screen: the window's rows, then the status bar and the message line
    sx = 384
    a.text(sx - 8, wy - 12, "what an 8 x 24 terminal shows", "tm", 11)
    a.box(sx - 8, wy, cols * c + 16, 8 * pitch + 6, "s fs", rx=8)
    for j in range(rows):
        y = fy + (rowoff + j) * pitch
        a.mono(sx, y, f"this is wider than the screen {rowoff + j + 1}"[coloff:coloff + cols], "t", size)
    ycur = fy + (rowoff + cy) * pitch
    a.fill(sx + cx * c, ycur - 9.5, c, 13, "fa", 1)
    a.text(sx + cx * c, ycur, "s", "f", size, mono=True)
    ys = fy + (rowoff + rows) * pitch
    a.fill(sx - 2, ys - 11, cols * c + 4, 15, "t", 2)
    a.mono(sx, ys, "f.txt - 12 lines    6/12", "f", size)
    # the window's edges carried across to the screen
    a.line(wx + ww + 2, wy, sx - 10, wy, "m", dash=True)
    a.line(wx + ww + 2, wy + wh, sx - 10, wy + wh, "m", dash=True)
    a.text(sx + cols * c + 18, ycur - 4, "cy 2", "ta", 10.5, weight=600, mono=True)
    a.text(sx + cols * c + 18, ycur + 10, "cx 15", "ta", 10.5, weight=600, mono=True)

    a.mono(24, 282, "file row 5 = rowoff 3 + cy 2      file column 23 = coloff 8 + cx 15", "t", 11.5)
    return a


# ------------------------------------------------------------------ 04 a text editor

def editor():
    a = Art("k04", "A row's bytes as a character goes in, and as Enter splits the row in two")
    cell, pitch, x0 = 28, 30, 116

    def cells(y, s, accent=(), label=None, sub=None, cursor=None):
        for i, ch in enumerate(s):
            cls = "a af" if i in accent else ("a f" if i == cursor else "s f")
            a.box(x0 + i * pitch, y, cell, 30, cls, rx=4)
            if ch == "\0":
                a.text(x0 + i * pitch + cell / 2, y + 19.5, "\\0", "tm", 11, "middle", mono=True)
            elif ch != " ":
                a.text(x0 + i * pitch + cell / 2, y + 20, ch, "ta" if i in accent else "t", 13.5, "middle", 600, mono=True)
        if label:
            a.text(24, y + 19.5, label, "t", 11.5, mono=True)
        if sub:
            a.text(x0 + len(s) * pitch + 8, y + 19.5, sub, "tm", 11.5, mono=True)

    for i in range(12):
        a.text(x0 + i * pitch + cell / 2, 32, str(i), "tm", 9, "middle", mono=True)
    cells(38, "hello world\0", label="E.row[0]", sub="size 11", cursor=5)
    a.text(x0 + 5 * pitch + cell / 2, 82, "cursor", "ta", 10, "middle", 600)

    a.text(24, 104, "type", "t", 12.5, weight=700)
    a.text(56, 104, "','", "t", 12.5, weight=700, mono=True)
    a.mono(x0, 104, "editorRowInsertChar(row, 5, ','): the 7 bytes from column 5 move right", "tm", 10.5)
    cells(114, "hello, world\0", accent={5}, label="E.row[0]", sub="size 12")

    a.text(24, 180, "Enter", "t", 12.5, weight=700)
    a.mono(x0, 180, "editorInsertNewline(): the bytes from column 6 become a new row", "tm", 10.5)
    cells(190, "hello,\0", accent={6}, label="E.row[0]", sub="size 6")
    cells(228, " world\0", accent=set(range(7)), label="E.row[1]", sub="size 6")
    a.text(400, 210, "a '\\0' cuts row 0 at column 6", "tm", 11)
    a.text(400, 248, "a new row, inserted below", "tm", 11)

    a.mono(24, 288, 'Ctrl-S: "hello,\\n world\\n", 14 bytes written on disk', "tm", 11)
    return a


# ------------------------------------------------------------------ 05 search

def search():
    a = Art("k05", "Typing r, e, t: each key searches the rows from the top, and the match's row goes to the top of the screen")
    size, pitch = 12, 22
    c = cw(size)
    fx, fy = 48, 60
    a.text(24, 22, "E.row[].chars, searched with strstr() from row 0", "tm", 11)
    rows = ["#include <stdio.h>", "", "int main(void) {", "\tprintf(\"hello\\n\");", "\treturn 0;", "}"]
    hits = {3: (2, 1, "\"r\": offset 2"), 4: (1, 3, "\"re\", \"ret\": offset 1")}
    for i, r in enumerate(rows):
        y = fy + i * pitch
        a.text(fx - 10, y, str(i), "ta" if i in hits else "tm", 10, "end", mono=True)
        if i in hits:
            off, ln, label = hits[i]
            a.fill(fx + off * c, y - 11.5, ln * c, 15.5, "af", 2)
        for j, ch in enumerate(r):
            if ch == "\t":                           # one byte, drawn as an arrow to a tab stop
                a.path(f"M{n(fx + j * c + 0.5)} {y - 4} L{n(fx + j * c + c - 1)} {y - 4} "
                       f"M{n(fx + j * c + c - 3.5)} {y - 6.5} L{n(fx + j * c + c - 1)} {y - 4} L{n(fx + j * c + c - 3.5)} {y - 1.5}", "m")
            elif ch != " ":
                hit = i in hits and hits[i][0] <= j < hits[i][0] + hits[i][1]
                a.text(fx + j * c, y, ch, "ta" if hit else "t", size, weight=700 if hit else None, mono=True)
        if i in hits:
            a.text(fx + 21 * c, y, hits[i][2], "ta", 10.5, weight=600, mono=True)

    # the screen after "ret"
    tx, tsize, tp = 394, 8.4, 14
    tc = cw(tsize)
    a.text(386, 22, "what a 10 x 44 terminal shows after r, e, t", "tm", 11)
    a.box(386, 34, 230, 150, "s fs", rx=10)
    ys = [52 + j * tp for j in range(10)]
    a.fill(tx + 8 * tc, ys[0] - 8.5, tc, 11, "fa", 1)
    a.text(tx + 8 * tc, ys[0], "r", "f", tsize, mono=True)
    a.mono(tx + 9 * tc, ys[0], "eturn 0;", "t", tsize)
    a.text(tx, ys[1], "}", "t", tsize, mono=True)
    for j in range(2, 8):
        a.text(tx, ys[j], "~", "t", tsize, mono=True)
    a.fill(tx - 2, ys[8] - 8.5, 44 * tc + 4, 11.5, "t", 1.5)
    a.mono(tx, ys[8], "f.txt - 6 lines", "f", tsize)
    a.mono(tx + 41 * tc, ys[8], "5/6", "f", tsize)
    a.mono(tx, ys[9], "Search: ret (Use ESC/Arrows/Enter)", "t", tsize)
    a.path(f"M{n(fx + 21 * c + 150)} {fy + 4 * pitch - 4} C 360 {fy + 4 * pitch - 4}, 352 {ys[0] - 3}, 384 {ys[0] - 3}", "a", arrow=True)

    # each key typed, the row it finds
    a.text(24, 218, "as each key is typed", "tm", 11)
    steps = [("r", "row 3 to the top: 4/6"), ("re", "row 4 to the top: 5/6"), ("ret", "row 4 stays: 5/6")]
    for k, (q, what) in enumerate(steps):
        x = 24 + k * 200
        w = 34 + len(q) * cw(12.5)
        a.box(x, 230, w, 26, "a af", rx=13)
        a.text(x + w / 2, 247.5, q, "ta", 12.5, "middle", 700, mono=True)
        a.text(x + w + 10, 247.5, what, "t", 11.5)
    a.text(24, 288, "Every change to the query searches again from row 0; Escape would put the view back.", "tm", 11.5)
    return a


# ------------------------------------------------------------------ icons and the track's own art

ICONS = {
    "00": '<path d="M15.75 8.5A6 6 0 0 0 4.6 6.25"/><path d="M4.25 2.75v3.75H8"/>'
          '<path d="M4.25 11.5a6 6 0 0 0 11.15 2.25"/><path d="M15.75 17.25V13.5H12"/>',
    "01": '<rect x="3" y="3" width="14" height="14" rx="3"/><path d="M10 13.75v-7.5M7 9.25l3-3 3 3"/>',
    "02": '<rect x="2.5" y="3" width="15" height="11" rx="2"/><path d="M7 17h6M10 14v3"/><path d="M5.5 6.5h5.5M5.5 9.5h8"/>',
    "03": '<path d="M2 10s3-5.5 8-5.5 8 5.5 8 5.5-3 5.5-8 5.5S2 10 2 10z"/><circle cx="10" cy="10" r="2.5"/>',
    "04": '<path d="M12.5 4.5l3 3L7 16H4v-3z"/><path d="M10.5 6.5l3 3"/>',
    "05": '<circle cx="8.5" cy="8.5" r="5"/><path d="M12.25 12.25L17 17"/>',
}
TRACK_ICON = '<rect x="2.5" y="3.5" width="15" height="13" rx="2.5"/><path d="M5.5 7h9M5.5 12h3.5"/><path d="M11.5 10.5v3"/>'


def icon_svg(body):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="none" stroke="currentColor" '
            'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">' + body + "</svg>\n")


def card():
    """The home page card: kilo's own screen, a word being typed into it (the one moving part)."""
    size = 9.5
    c = cw(size)
    x0, pitch = 46, 14
    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 280 160">']

    def t(x, y, s, cls="t"):
        col = 0
        for word in s.split(" "):
            if word:
                out.append(f'<text class="{cls} mono" x="{n(x + col * c)}" y="{n(y)}" font-size="{size}">'
                           + figart.esc(word) + "</text>")
            col += len(word) + 1

    out.append('<rect class="s f" x="34" y="10" width="212" height="140" rx="9" stroke-width="1.75"/>')
    out.append('<path class="m" d="M34 25h212" stroke-width="1.25"/>')
    for i in range(3):
        out.append(f'<circle class="m fs" cx="{45 + i * 9}" cy="17.5" r="2.5" stroke-width="1.25"/>')
    ys = [40 + j * pitch for j in range(8)]
    t(x0, ys[0], "#include <stdio.h>")
    t(x0, ys[1], "int main(void) {")
    t(x0, ys[2], "    puts(\"hello,")
    out.append('<g class="stream">')
    t(x0 + 17 * c, ys[2], "world")
    out.append("</g>")
    out.append(f'<rect class="fa" x="{n(x0 + 22 * c)}" y="{n(ys[2] - 9)}" width="{n(c)}" height="12" rx="1"/>')
    t(x0 + 22 * c, ys[2], "\"", "f")
    t(x0 + 23 * c, ys[2], ");")
    t(x0, ys[3], "}")
    for j in (4, 5):
        t(x0, ys[j], "~", "tm")
    out.append(f'<rect class="t" x="{x0 - 3}" y="{n(ys[6] - 9.5)}" width="{n(33 * c + 6)}" height="13" rx="2"/>')
    t(x0, ys[6], "f.txt - 4 lines (modified)", "f")
    t(x0 + 30 * c, ys[6], "3/4", "f")
    out.append("</svg>\n")
    return "\n".join(out)


COVERS = {"00": workbench, "01": terminal, "02": screen, "03": viewer, "04": editor, "05": search}


def main():
    for mid, fn in COVERS.items():
        d = os.path.join(LESSONS, MODULES[mid])
        for name, s in (("cover.svg", fn().svg()), ("icon.svg", icon_svg(ICONS[mid]))):
            s.encode("ascii")
            with open(os.path.join(d, name), "w") as f:
                f.write(s)
            print(os.path.join(d, name))
    for name, s in (("art.svg", card()), ("icon.svg", icon_svg(TRACK_ICON))):
        s.encode("ascii")
        with open(os.path.join(TRACK, name), "w") as f:
            f.write(s)
        print(os.path.join(TRACK, name))


if __name__ == "__main__":
    main()
