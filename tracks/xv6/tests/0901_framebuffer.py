"""09.01 A framebuffer

The kernel finds etc/ramfb in fw_cfg's file directory and hands QEMU a
640x480 XRGB8888 framebuffer in its own memory. A screenshot of the
display then shows the boot screen pixel for pixel: a white border
exactly one pixel wide round the very edge, and red, green and blue
squares of 80 by 80 pixels in their places on the dark background, in
those colours (so the bytes of a pixel are in the right order and the
rows the right distance apart). Without -device ramfb the kernel boots to
the shell as before.
"""

BG = 0x202830
WHITE = 0xffffff


def test(t):
    tr = t.track
    s = tr.shell(t)
    shot = tr.wait_screen(s, "the boot screen", lambda sh: sh[320, 100] == BG and sh[0, 0] == WHITE)
    t.check((shot.w, shot.h) == (640, 480), f"the display is {shot.w}x{shot.h}, expected 640x480")

    def want(x, y, color, what):
        got = shot[x, y]
        t.check(got == color, f"pixel ({x}, {y}), {what}, is {got:06x}, expected {color:06x}")

    for x, y in [(0, 0), (639, 0), (0, 479), (639, 479), (320, 0), (320, 479), (0, 240), (639, 240)]:
        want(x, y, WHITE, "on the border")
    for x, y in [(1, 1), (638, 1), (1, 478), (638, 478), (320, 1), (320, 478), (1, 240), (638, 240)]:
        want(x, y, BG, "just inside the border")

    for x0, color, name in ((160, 0xff0000, "red"), (280, 0x00ff00, "green"), (400, 0x0000ff, "blue")):
        for x, y in [(x0, 200), (x0 + 79, 200), (x0, 279), (x0 + 79, 279), (x0 + 40, 240)]:
            want(x, y, color, f"in the {name} square")
        for x, y in [(x0 - 1, 240), (x0 + 80, 240), (x0 + 40, 199), (x0 + 40, 280)]:
            want(x, y, BG, f"just outside the {name} square")
        n = shot.count(color, x0 - 10, 190, x0 + 90, 290)
        t.check(n == 80 * 80, f"the {name} square has {n} pixels, expected 6400")

    # The shell works with the screen there.
    out = tr.run(s, "echo screen")
    t.check("screen" in out, f"echo printed {out!r}")
    s.close()

    # No screen at all: no etc/ramfb, and the kernel carries on without one.
    s = tr.shell(t, gui=False, name="qemu-no-screen")
    out = tr.run(s, "echo no screen")
    t.check("no screen" in out, f"echo printed {out!r}")
