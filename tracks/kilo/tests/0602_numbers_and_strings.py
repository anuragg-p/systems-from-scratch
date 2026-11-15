"""06.02 Numbers and strings

In a C file, a number is red: a digit after a separator starts one, and
digits and dots right after it go on with it, so 12.5 is one number and
the 3 of y3 is none. A string is magenta from its quote to the same quote
again, ' or ", a backslash taking the next character along; a string with
no end goes to the end of the row, and the row below starts outside it.
"""


def test(t):
    tr = t.track
    text = ("x = 12.5 + y3 - 7;\n"
            "s = \"say \\\"hi\\\"\" + 'q';\n"
            "t = \"no end\n"
            "after = 1;\n"
            "u = \"back\\\n"
            "v = \"a\"\x01\"b\";\n"
            "w = (8)+[9];\n")
    ed = tr.edit(t, text, name="t.c", asan=True)
    want = ["x = [r:12.5] + y3 - [r:7];",
            "s = [m:\"say \\\"hi\\\"\"] + [m:'q'];",
            "t = [m:\"no end]",
            "after = [r:1];",
            "u = [m:\"back\\]",
            # A non-printable character between two strings: both stay magenta.
            "v = [m:\"a\"][M:A][m:\"b\"];",
            "w = ([r:8])+[[r:9]];"]
    for n, w in enumerate(want):
        t.check(ed.painted(n) == w, f"row {n}: {ed.painted(n)!r}, not {w!r}")
    # A backslash last in a string, the end of the row: nothing written past hl (with
    # AddressSanitizer, where the compiler has it, the original stops kilo here).
    ed.keys(tr.DOWN * 4, tr.RIGHT * 10, "x")
    t.check(ed.painted(4) == "u = [m:\"back\\x]", f"typed after the backslash: {ed.painted(4)!r}")
    ed.keys(tr.BACKSPACE, tr.ctrl("s"))
    t.check(ed.saved() == text, f"saved {ed.saved()!r}")
