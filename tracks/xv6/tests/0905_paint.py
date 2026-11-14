"""09.05 A program worth showing

paint, started in the background, leaves the shell on the serial console
working. Its first frame has a white canvas and no pointer. Then, with
QMP's keyboard and mouse: the pointer appears where the mouse is, with
the pixel it points at left showing; a click on the red swatch moves the
white frame to it; a drag draws a red stroke three pixels wide; the
pointer leaves no trace where it was; 3 makes the pen five pixels wide
and says so; c clears the canvas. Esc ends paint, leaving a black screen,
and the shell still answers.
"""

import os
import re

BAR = 0x2b2b2b
WHITE = 0xffffff
BLACK = 0x000000
RED = 0xff0000
DIM = 0xb0b0b0


def font_glyph(root, ch):
    """Character ch's 8 rows, from the font in user/font.c."""
    with open(os.path.join(root, "user", "font.c")) as f:
        vals = [int(v, 16) for v in re.findall(r"0x([0-9a-fA-F]{2})", f.read().split("font[95][8]", 1)[1])]
    i = (ord(ch) - 32) * 8
    return vals[i:i + 8]


def test(t):
    tr = t.track
    s = tr.shell(t)
    q = s.qmp
    s.sendline("paint &")
    # the shell's next prompt may come before or after paint's banner
    s.expect(r"paint: draw in the window; Esc there quits\r?\n", timeout=10)
    s.wait_quiet(0.3)
    out = tr.run(s, "echo the shell still works")
    t.check("the shell still works" in out, f"echo printed {out!r}")

    shot = tr.wait_screen(s, "paint's first frame", lambda sh: sh[2, 2] == BAR and sh[320, 240] == WHITE)
    t.check(shot.count(BLACK, 0, 20, 640, 448) == 0, "before the mouse moves, there should be no pointer")

    def want(shot, x, y, color, what):
        got = shot[x, y]
        t.check(got == color, f"pixel ({x}, {y}), {what}, is {got:06x}, expected {color:06x}")

    # The pointer.
    q.move(320, 240)
    shot = tr.wait_screen(s, "the pointer at (320, 240)", lambda sh: sh[325, 240] == BLACK)
    for dx, dy in ((3, 0), (8, 0), (-3, 0), (-8, 0), (0, 3), (0, 8), (0, -3), (0, -8)):
        want(shot, 320 + dx, 240 + dy, BLACK, "on an arm of the pointer")
    for dx, dy in ((9, 0), (-9, 0), (0, 9), (0, -9), (5, 1), (5, -1)):
        want(shot, 320 + dx, 240 + dy, WHITE, "on the pointer's outline")
    for dx, dy in ((0, 0), (1, 0), (2, 0), (0, 2), (2, 2)):
        want(shot, 320 + dx, 240 + dy, WHITE, "in the gap in the middle of the pointer")

    # Choose red: the frame moves from black to red.
    q.click(8 + 3 * 40 + 16, 464)
    shot = tr.wait_screen(s, "the frame round the red swatch", lambda sh: sh[126, 460] == WHITE)
    want(shot, 6, 460, BAR, "where the frame round black was")
    want(shot, 128, 452, RED, "the red swatch")

    # A red stroke with the default pen, three pixels wide.
    q.drag([(100, 100), (300, 200)])
    q.move(100, 300)
    shot = tr.wait_screen(s, "a red stroke", lambda sh: sh[200, 150] == RED and sh[100, 305] == BLACK)
    for x, y in ((100, 100), (200, 150), (300, 200)):
        for d in (-1, 0, 1):
            want(shot, x, y + d, RED, "in the stroke")
        want(shot, x, y - 3, WHITE, "above the stroke")
        want(shot, x, y + 3, WHITE, "below the stroke")
    # The pointer was drawn at (300, 200) when the drag ended; now it is
    # elsewhere, and the canvas under it shows again.
    for x, y in ((306, 200), (300, 206), (294, 200), (300, 194)):
        want(shot, x, y, WHITE, "where the pointer used to be")
    t.check(shot.count(BLACK, 280, 180, 320, 220) == 0, "the old pointer left black pixels behind")

    # A wider pen, then clear.
    q.key("3")
    three = font_glyph(t.root, "3")
    tr.wait_screen(s, '"pen 3"', lambda sh: all(sh[624 + c, 460 + r] == (DIM if three[r] & (0x80 >> c) else BAR)
                                                 for r in range(8) for c in range(8)))
    q.drag([(100, 400), (400, 400)])
    q.move(500, 300)
    shot = tr.wait_screen(s, "a stroke five pixels wide", lambda sh: sh[250, 402] == RED)
    for d in (-2, -1, 0, 1, 2):
        want(shot, 250, 400 + d, RED, "in the wide stroke")
    want(shot, 250, 403, WHITE, "below the wide stroke")
    want(shot, 250, 397, WHITE, "above the wide stroke")

    q.key("c")
    shot = tr.wait_screen(s, "a clear canvas", lambda sh: sh[200, 150] == WHITE and sh[250, 400] == WHITE)
    t.check(shot.count(RED, 0, 20, 640, 448) == 0, "c should clear every red pixel")

    # Esc: paint ends with a black screen; the shell carries on.
    q.key("esc")
    tr.wait_screen(s, "the black screen paint leaves", lambda sh: sh[2, 2] == BLACK and sh[320, 240] == BLACK)
    out = tr.run(s, "echo still here")
    t.check("still here" in out, f"echo printed {out!r}")
