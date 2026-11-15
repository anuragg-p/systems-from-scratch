"""06.03 Comments, on one line and across many

In a C file, // after a separator makes the rest of the row a comment, and
/* opens one that goes on, over as many rows as it takes, blank rows too,
to the */ that closes it: all cyan. Whether a row ends inside a comment is
kept with the row, and the row below starts from it; an edit that changes
it changes the rows below, as far as the change reaches, however many.
"""


def test(t):
    tr = t.track
    text = ("x = 1; // note\n"           # 0
            "\t// x\n"                    # 1: a tab, then a short comment
            "a\t// comment text\n"        # 2
            "/* start\n"                  # 3
            "\n"                          # 4: a blank row inside the comment
            "   end */ y = 2;\n"          # 5
            "/*\n"                        # 6
            "// old */ z = 3;\n"          # 7: // inside a comment is part of it
            "w = 5;\n"                    # 8
            "s = \"/*\";\n"               # 9: a comment's opening in a string
            "a = 1; /*/\n"                # 10: opened, and a slash
            "still */ b = 2;\n"           # 11
            "c = 4;\n")                   # 12
    ed = tr.edit(t, text, name="t.c", asan=True)
    want = ["x = [r:1]; [c:// note]",
            "        [c:// x]",
            "a       [c:// comment text]",
            "[c:/* start]",
            "",
            "   [c:end */] y = [r:2];",
            "[c:/*]",
            "[c:// old */] z = [r:3];",
            "w = [r:5];",
            "s = [m:\"/*\"];",
            "a = [r:1]; [c:/*/]",
            "[c:still */] b = [r:2];",
            "c = [r:4];"]
    for n, w in enumerate(want):
        t.check(ed.painted(n) == w, f"row {n}: {ed.painted(n)!r}, not {w!r}")

    # // typed in front of the opening of row 3: the comment ends there for the rows below.
    ed.keys(tr.DOWN * 3, "//")
    t.check(ed.painted(3) == "[c:///* start]" and ed.painted(5) == "   end */ y = [r:2];",
            f"// in front: {ed.painted(3)!r} {ed.painted(5)!r}")
    ed.keys(tr.BACKSPACE * 2)
    t.check(ed.painted(5) == "   [c:end */] y = [r:2];", f"and back: {ed.painted(5)!r}")

    # Joining rows: each row still knows the row above it.
    ed = tr.edit(t, "x\n/* a\nb */\nc = 1;\n", name="j.c", asan=True)
    ed.keys(tr.DOWN, tr.BACKSPACE, tr.DOWN, "x")
    t.check(ed.painted(0) == "x[c:/* a]" and ed.painted(1) == "[c:bx */]" and ed.painted(2) == "c = [r:1];",
            f"joined: {[ed.painted(n) for n in range(3)]}")
    ed = tr.edit(t, "a\nb\nc\nd\n", name="k.c", asan=True)
    ed.keys(tr.DOWN, tr.BACKSPACE, tr.DOWN, tr.LEFT, tr.BACKSPACE, tr.DOWN, "/*")
    t.check(ed.lines[:3] == ["abc", "d/*", "~"] and ed.painted(1) == "d[c:/*]",
            f"two joins, then a row typed in: {[ed.painted(n) for n in range(3)]}")
    # Joined onto a // comment, a comment's opening is part of it: the rows below are not
    # inside a comment any more.
    ed = tr.edit(t, "a = 1; // note\n/* b\nc = 2;\n*/\n", name="l.c")
    ed.keys(tr.DOWN, tr.BACKSPACE)
    t.check(ed.painted(0) == "a = [r:1]; [c:// note/* b]" and ed.painted(1) == "c = [r:2];"
            and ed.painted(2) == "*/", f"joined onto //: {[ed.painted(n) for n in range(3)]}")

    # Enter opens a comment in the middle of the file: every row below is in it, to the last.
    ed = tr.edit(t, "x = 1; // a /* b\nc;\nd;\n", name="m.c")
    ed.keys(tr.RIGHT * 12, tr.ENTER)
    t.check([ed.painted(n) for n in range(4)] == ["x = [r:1]; [c:// a]", "[c:/* b]", "[c:c;]", "[c:d;]"],
            f"split before the opening: {[ed.painted(n) for n in range(4)]}")

    # A comment opened at the top of a long file reaches its last row.
    n = 100000
    ed = tr.edit(t, "x;\n" * (n - 1) + "end;\n", name="big.c", timeout=60)
    ed.keys("/*")
    t.check(ed.painted(0) == "[c:/*x;]" and ed.painted(21) == "[c:x;]", f"{ed.painted(0)!r} {ed.painted(21)!r}")
    ed.keys(tr.ctrl("f"), "end", tr.ENTER)
    t.check(ed.painted(0) == "[c:end;]" and ed.status.endswith(f"{n}/{n}"),
            f"the last row: {ed.painted(0)!r} {ed.status!r}")
