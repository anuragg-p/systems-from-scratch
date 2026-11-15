"""06.01 A colour for every character

Each row keeps a highlight class for every character of render, and the
row is drawn a character at a time in its class's colour. Which language a
file is in, if any, comes from its name: .c, .h, .cpp, .hpp and .cc are C,
wherever else the name has a dot. In a C file a character isprint() says no
to is drawn in reverse video as a letter (Ctrl-A as A) or '?', one cell
for each byte, a byte above 127 too; in any other file kilo draws as
without highlighting, to the byte.
"""


def test(t):
    tr = t.track
    text = "a\x01b\x1ac\x7fd\ncaf\xc3\xa9 au lait\n\x1b[Hred\nplain text\n"
    ed = tr.edit(t, text, name="t.c", asan=True)
    want = [("aAbZc?d", ".#.#.#."), ("caf?? au lait", "...##........"), ("?[Hred", "#....."),
            ("plain text", "..........")]
    for n, (line, colors) in enumerate(want):
        t.check(ed.line(n) == line and ed.colors(n) == colors,
                f"row {n}: {ed.painted(n)!r}, not {tr.paint(line, colors)!r}")
    # One cell per byte: the cursor stays on the character it is on.
    ed.keys(tr.DOWN, tr.RIGHT * 5)
    t.check(ed.cursor == (1, 5), f"after the 3 bytes of 'caf' and the 2 of an e-acute: {ed.cursor}")
    t.check(ed.colors(22) == "#" * len(ed.line(22)), f"the status bar: {ed.painted(22)!r}")
    ed.quit()

    # A file kilo has no language for: the same bytes as the editor without highlighting.
    ed = tr.edit(t, "ab\n\x01x\n", name="t.txt", rows=6, cols=20)
    t.check(ed.raw.startswith(b"\x1b[?25l\x1b[Hab\x1b[0K\r\n\x01x\x1b[0K\r\n~\x1b[0K\r\n"),
            f"no colours and no reverse video in a .txt file: {ed.raw[:60]!r}")
    ed.quit()

    # Chosen by the name: a pattern that starts with a dot must end it.
    for name, c in [("t.h", True), ("t.cpp", True), ("t.hpp", True), ("t.cc", True),
                    ("my.cool.c", True), (".config/t.c", True), ("dir.c/t.c", True),
                    ("t.c.orig", False), ("t.cc.bak", False), ("t.txt", False), ("Makefile", False),
                    ("c", False), ("t.", False)]:
        ed = tr.edit(t, "x\x01y\n", name=name)
        got = ed.colors(0) == ".#."
        t.check(got == c, f"{name}: {'' if c else 'not '}C expected, the row is {ed.painted(0)!r}")
        ed.quit()
