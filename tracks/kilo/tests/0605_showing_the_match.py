"""06.05 Showing the match

While a search is on, its match is blue, over whatever colour it had, in
any file (one kilo has no language for too). When the search moves to
another match, the row it leaves gets its own colours back; when it ends,
by Escape or Enter, nothing is blue any more. A match after a tab is
coloured where the screen shows it.
"""


def test(t):
    tr = t.track
    text = ("int beta = 42;\n"
            "\tchar *s = \"beta\";\n"
            "/* beta */ return beta;\n")
    plain = ["[g:int] beta = [r:42];",
             "        [g:char] *s = [m:\"beta\"];",
             "[c:/* beta */] [y:return] beta;"]
    ed = tr.edit(t, text, name="t.c", asan=True)
    ed.keys(tr.ctrl("f"), "beta")
    t.check(ed.painted(0) == "[g:int] [b:beta] = [r:42];", f"first match: {ed.painted(0)!r}")
    ed.keys(tr.DOWN)
    # The match after a tab: blue on the screen's "beta", inside the string's magenta.
    t.check(ed.painted(0) == "        [g:char] *s = [m:\"][b:beta][m:\"];", f"after a tab: {ed.painted(0)!r}")
    ed.keys(tr.DOWN)
    t.check(ed.painted(0) == "[c:/* ][b:beta][c: */] [y:return] beta;", f"in a comment: {ed.painted(0)!r}")
    ed.keys(tr.DOWN)
    t.check(ed.painted(0) == "[g:int] [b:beta] = [r:42];", f"around again: {ed.painted(0)!r}")
    ed.keys(tr.ESC)
    t.check([ed.painted(n) for n in range(3)] == plain, f"Escape: {[ed.painted(n) for n in range(3)]}")

    # A number that is the match, then Enter: red again, and typing there colours as usual.
    ed.keys(tr.ctrl("f"), "42")
    t.check(ed.painted(0) == "[g:int] beta = [b:42];", f"{ed.painted(0)!r}")
    ed.keys(tr.ENTER)
    t.check(ed.painted(0) == plain[0], f"Enter: {ed.painted(0)!r}")
    ed.keys("1")
    t.check(ed.painted(0) == "[g:int] beta = [r:142];", f"typed into the number: {ed.painted(0)!r}")
    # A query that stops matching: the last match is not left blue.
    ed.keys(tr.ctrl("f"), "bet", "x")
    t.check(not any("b" in ed.colors(n) for n in range(3)), f"no match: {[ed.painted(n) for n in range(3)]}")
    ed.keys(tr.ESC)

    # A file with no syntax: only the match has a colour.
    ed = tr.edit(t, "one\n\tdelta two\n", name="t.txt")
    ed.keys(tr.ctrl("f"), "two")
    t.check(ed.painted(0) == "        delta [b:two]", f"in a .txt file: {ed.painted(0)!r}")
    ed.keys(tr.ESC)
    t.check(ed.painted(0) == "one" and ed.painted(1) == "        delta two", f"and none after: {ed.painted(1)!r}")
