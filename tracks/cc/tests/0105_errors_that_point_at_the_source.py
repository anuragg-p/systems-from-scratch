"""01.05 Errors that point at the source

An error at a place in the source is two lines: "FILE:LINE: " and the text
of that line, then a caret under the place with the message after it. The
caret's line repeats every tab of the source line before the place, so the
caret lines up whatever width the terminal gives a tab. It works on any
line, and for an error at the end of the file, which is on its last line.
An error with no place (a file that cannot be opened) is one line.
"""

import re


def test(t):
    tr = t.track
    # On line 1: the exact two lines. The file is t<N>.c in the test's scratch directory.
    st, out, err = tr.compile(t, "1 + $\n")
    name = err.split(":", 1)[0]
    pad = " " * len(f"{name}:1: ")
    t.check(err == f"{name}:1: 1 + $\n{pad}    ^ invalid token\n", f"on line 1:\n{err}")
    # On a later line, from the parser: the token knows its line.
    st, out, err = tr.compile(t, "1 +\n2 +\n  3 4\n")
    name = err.split(":", 1)[0]
    pad = " " * len(f"{name}:3: ")
    t.check(err == f"{name}:3:   3 4\n{pad}    ^ extra token\n", f"on line 3:\n{err}")
    # After tabs: the tabs are repeated in the caret's line.
    st, out, err = tr.compile(t, "\t1 +\t$\n")
    name = err.split(":", 1)[0]
    pad = " " * len(f"{name}:1: ")
    t.check(err == f"{name}:1: \t1 +\t$\n{pad}\t   \t^ invalid token\n", f"after tabs:\n{err!r}")
    e = tr.error(t, "\t\t1 2")
    t.check((e.line, e.col, e.msg, e.text) == (1, 5, "extra token", "\t\t1 2"), f"{e!r}")

    # At the end of the file: on the last line, just after its last character.
    for src, line, col, msg in (("1+", 1, 3, "expected an expression"),
                                ("1 +\n", 1, 4, "expected an expression"),
                                ("(1", 1, 3, "expected ')'"),
                                ("1\n+\n", 2, 2, "expected an expression"),
                                ("1 -\n\n", 2, 1, "expected an expression")):
        e = tr.error(t, src)
        t.check((e.line, e.col, e.msg) == (line, col, msg), f"{src!r}: {e!r}, not {msg!r} at {line}:{col}")
    # From the scanner, which has a place but no token yet.
    e = tr.error(t, "1 +\n\n   'ab'\n")
    t.check((e.line, e.col, e.text) == (3, 4, "   'ab'"), f"{e!r}")
    e = tr.error(t, "1 +\n/* never\nclosed\n")
    t.check((e.line, e.col, e.msg) == (2, 1, "unclosed block comment"), f"{e!r}")

    # No place: one line.
    st, out, err = tr.compile(t, "1", "nosuch.c")
    t.check(st == 1 and re.match(r"one file at a time: nosuch\.c and t\d+\.c\n$", err),
            f"an error with no place is one line: {err!r}")
