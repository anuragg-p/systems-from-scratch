"""01.01 A stream of tokens: numbers, plus and minus

The scanner turns the file into tokens: numbers (with their values), "+"
and "-", the end of the file; spaces and newlines only keep them apart. Each
token knows its line and column, and --tokens prints them one a line:
LINE:COL KIND TEXT, and a number's value. Sums and differences compile and
run, left to right. A character the scanner does not know is an error, and
so are letters run on to a number.
"""


def test(t):
    tr = t.track
    got = [repr(x) for x in tr.tokens(t, "5 + 20 - 4")]
    want = ["1:1 num 5 5", "1:3 punct +", "1:5 num 20 20", "1:8 punct -", "1:10 num 4 4", "1:11 eof"]
    t.check(got == want, f"--tokens of '5 + 20 - 4':\n{got}\nnot\n{want}")
    # Lines and columns; the end of the file is on its last line, after the last character.
    got = [repr(x) for x in tr.tokens(t, "1\n  + 22\n-3\n")]
    want = ["1:1 num 1 1", "2:3 punct +", "2:5 num 22 22", "3:1 punct -", "3:2 num 3 3", "3:3 eof"]
    t.check(got == want, f"positions over three lines:\n{got}\nnot\n{want}")
    got = [repr(x) for x in tr.tokens(t, "")]
    t.check(got == ["1:1 eof"], f"an empty file is the end of the file alone: {got}")
    got = [repr(x) for x in tr.tokens(t, "\t7\r\n")]
    t.check(got == ["1:2 num 7 7", "1:4 eof"], f"a tab is one column, and \\r is a space: {got}")
    got = [repr(x) for x in tr.tokens(t, "12345678901234567890")]
    t.check(got[0] == "1:1 num 12345678901234567890 -6101065172474983726",
            f"a number past 63 bits keeps its 64 (strtoul), printed signed: {got[0]}")

    # Sums and differences, left to right.
    tr.value(t, "5+20-4", 21)
    tr.value(t, "100 - 1 - 2 - 3", 94)
    tr.value(t, " 12 + 34 - 5 ", 41)
    tr.value(t, "0 - 7", -7)
    tr.value(t, "4294967296 - 4294967295", 1)

    for src, msg, col in (("1 $ 2", "invalid token", 3), ("12a", "invalid numeric constant", 1),
                          ("1 + 2_", "invalid numeric constant", 5)):
        e = tr.error(t, src)
        t.check((e.msg, e.line, e.col) == (msg, 1, col), f"{src!r}: {e!r}, not {msg!r} at 1:{col}")
