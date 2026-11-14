"""09.04 A drawing library

paint draws its whole frame with the library, so its screen is checked
against what the library promises. Text: every pixel of "paint", of the
help text and of "pen 2" is the text colour exactly where the font in
user/font.c has a 1 bit, and the bar colour where it has a 0.
Rectangles: the swatches and the frame round the chosen one have exact
edges. Lines: one pixel wide, from end to end inclusive, one pixel per
step along the longer axis and never more than half a pixel off the true
line, in every direction (shallow, steep, leftward, upward, diagonal,
flat, vertical, and a single point).
"""

import os
import re

BAR = 0x2b2b2b
WHITE = 0xffffff
DIM = 0xb0b0b0
TOP = 20
SWATCHES = [0x000000, 0x808080, 0xffffff, 0xff0000, 0xff8000, 0xffff00, 0x00c000, 0x00c0ff, 0x0000ff, 0x8000ff]

# (from, to), each in a box of its own; the pointer parks at (500, 220).
LINES = [((40, 60), (240, 110)), ((300, 60), (330, 260)), ((560, 300), (400, 380)),
         ((100, 400), (200, 300)), ((450, 100), (600, 100)), ((620, 150), (620, 250)),
         ((380, 200), (380, 200))]


def load_font(root):
    with open(os.path.join(root, "user", "font.c")) as f:
        src = f.read()
    body = src.split("font[95][8]", 1)[1]
    vals = [int(v, 16) for v in re.findall(r"0x([0-9a-fA-F]{2})", body)]
    if len(vals) != 95 * 8:
        raise AssertionError(f"user/font.c should hold 95 x 8 bytes, found {len(vals)}")
    return [vals[i * 8:i * 8 + 8] for i in range(95)]


def test(t):
    tr = t.track
    font = load_font(t.root)
    s = tr.shell(t)
    q = s.qmp
    s.sendline("paint")
    s.expect(r"paint: draw in the window", timeout=10)
    shot = tr.wait_screen(s, "paint's title bar", lambda sh: sh[2, 2] == BAR and sh[320, 240] == WHITE)

    def text(x, y, string, color, bg, what):
        for i, ch in enumerate(string):
            glyph = font[ord(ch) - 32]
            for row in range(8):
                for col in range(8):
                    on = glyph[row] & (0x80 >> col)
                    got = shot[x + 8 * i + col, y + row]
                    t.check(got == (color if on else bg),
                            f"{what}: pixel ({x + 8 * i + col}, {y + row}), row {row} column {col} of {ch!r}, "
                            f"is {got:06x}, expected {(color if on else bg):06x} (the font has a {1 if on else 0} there)")

    text(8, 6, "paint", WHITE, BAR, "the title")
    help = "c clear  1 2 3 pen  esc quit"
    text(640 - 8 - 8 * len(help), 6, help, DIM, BAR, "the help text")
    text(640 - 8 - 8 * 5, 460, "pen 2", DIM, BAR, "the pen size")

    def want(x, y, color, what):
        got = shot[x, y]
        t.check(got == color, f"pixel ({x}, {y}), {what}, is {got:06x}, expected {color:06x}")

    for i, color in enumerate(SWATCHES):
        x0 = 8 + 40 * i
        for x, y in [(x0, 452), (x0 + 31, 452), (x0, 475), (x0 + 31, 475)]:
            want(x, y, color, f"a corner of swatch {i}")
        edge = WHITE if i == 0 else BAR
        for x, y in [(x0 - 1, 460), (x0 + 32, 460), (x0 + 10, 451), (x0 + 10, 476)]:
            want(x, y, edge, f"just outside swatch {i}")
    for x, y in [(6, 450), (41, 450), (6, 477), (41, 477)]:
        want(x, y, WHITE, "a corner of the frame round the chosen swatch")
    for x, y in [(5, 460), (42, 460), (20, 449), (20, 478)]:
        want(x, y, BAR, "just outside the frame")

    # One-pixel lines in black, the chosen colour.
    q.key("1")
    for a, b in LINES:
        q.drag([a, b])
    q.move(500, 220)
    shot = tr.wait_screen(s, "the lines", lambda sh: sh[380, 200] == 0 and sh[499, 220] == WHITE and
                          sh[2, 2] == BAR, timeout=15)
    for (x0, y0), (x1, y1) in LINES:
        xa, xb, ya, yb = min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1)
        got = {(x, y) for y in range(ya - 2, yb + 3) for x in range(xa - 2, xb + 3) if shot[x, y] == 0}
        what = f"the line from ({x0}, {y0}) to ({x1}, {y1})"
        n = max(xb - xa, yb - ya) + 1
        t.check((x0, y0) in got and (x1, y1) in got, f"{what} should include both ends")
        t.check(len(got) == n, f"{what} has {len(got)} pixels, expected {n}: one per step")
        major_x = xb - xa >= yb - ya
        for x, y in got:
            if major_x:
                ideal = y0 + (y1 - y0) * (x - x0) / (x1 - x0) if x1 != x0 else y0
                off = abs(y - ideal)
            else:
                ideal = x0 + (x1 - x0) * (y - y0) / (y1 - y0)
                off = abs(x - ideal)
            t.check(off <= 0.5 + 1e-9, f"{what}: pixel ({x}, {y}) is {off:.2f} pixels off the true line")
        steps = {x for x, _ in got} if major_x else {y for _, y in got}
        t.check(len(steps) == n, f"{what} should have exactly one pixel in each {'column' if major_x else 'row'}")
    q.key("esc")
    s.expect(r"\$ ", timeout=10)
