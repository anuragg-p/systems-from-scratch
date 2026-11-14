"""09.02 Pixels from user space

colors maps the screen with fbmap() and stores the test card straight
into it: eight colour bars of 80 pixels over the top 360 rows, and below
them a grey ramp that a forked child drew through a mapping of its own.
Every bar and the ramp are exactly where they belong, and the parent sees
the child's pixels, so both mappings lead to the same pages. The picture
is still there after both exit: exit took the mapping down without
freeing or scribbling on the pages. Running it again, many times, works;
a program that never maps the screen is unaffected.
"""

BARS = [0xffffff, 0xffff00, 0x00ffff, 0x00ff00, 0xff00ff, 0xff0000, 0x0000ff, 0x000000]


def test(t):
    tr = t.track
    s = tr.shell(t)
    out = tr.run(s, "colors")
    t.check("colors: the screen is at 0x0000000040000000" in out, f"colors should map the screen at 1 GB: {out!r}")
    t.check("drew the ramp; this process sees it too" in out,
            f"the parent should see the child's pixels through its own mapping: {out!r}")

    # colors and its child have both exited by now.
    shot = tr.wait_screen(s, "the colour bars", lambda sh: sh[40, 100] == BARS[0] and sh[600, 100] == BARS[7])

    def want(x, y, color, what):
        got = shot[x, y]
        t.check(got == color, f"pixel ({x}, {y}), {what}, is {got:06x}, expected {color:06x}")

    for i, color in enumerate(BARS):
        for x in (80 * i, 80 * i + 40, 80 * i + 79):
            for y in (0, 180, 359):
                want(x, y, color, f"in bar {i}")
    for x in (0, 1, 100, 320, 500, 638, 639):
        g = x * 255 // 639
        for y in (360, 420, 479):
            want(x, y, g << 16 | g << 8 | g, "in the ramp")

    # Map, draw, fork, exit, again and again: no page is freed or copied.
    out = tr.run(s, "colors; colors; colors; colors; colors", timeout=60)
    t.check(out.count("this process sees it too") == 5, f"five runs of colors: {out!r}")
    out = tr.run(s, "echo still here")
    t.check("still here" in out, f"echo printed {out!r}")
    shot = s.qmp.screen()
    want(40, 100, BARS[0], "after five more runs")
    want(639, 479, 0xffffff, "after five more runs")
