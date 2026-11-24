"""02.02 The syntax tree

"*" and "/" bind tighter than "+" and "-" because add() calls mul() for its
operands: precedence is the shape of the tree, not a table looked up. Both
levels go left to right. Parentheses make a primary of a whole expression,
and change the shape; a missing ")" is an error.
"""


def test(t):
    tr = t.track
    for src, want in (("2*3+4", "(+ (* 2 3) 4)"),
                      ("2+3*4", "(+ 2 (* 3 4))"),
                      ("(2+3)*4", "(* (+ 2 3) 4)"),
                      ("2*(3+4)", "(* 2 (+ 3 4))"),
                      ("2*3/4", "(/ (* 2 3) 4)"),
                      ("8/4/2", "(/ (/ 8 4) 2)"),
                      ("1+2*3-4/2", "(- (+ 1 (* 2 3)) (/ 4 2))"),
                      ("((5))", "5"),
                      ("(1-(2-3))", "(- 1 (- 2 3))")):
        got = tr.sexp(tr.tree(t, src))
        t.check(got == want, f"{src}: {got}, not {want}")
    st, out, err = tr.compile(t, "2+3*4", "--tree")
    t.check(out == "+\n  num 2\n  *\n    num 3\n    num 4\n", f"--tree of 2+3*4:\n{out}")
    for src, want in (("2*3+4", 10), ("2+3*4", 14), ("(2+3)*4", 20), ("100/7", 14), ("100/7*7", 98),
                      ("8/4/2", 1), ("1+(2*(3+4))", 15), ("1+2*3-4/2", 5), ("7/2", 3), ("(0-7)/2", -3),
                      ("1000000*1000", 1000000000), ("2147483647/10", 214748364)):
        tr.value(t, src, want)
    for src, msg, col in (("(1", "expected ')'", 3), ("(1+2", "expected ')'", 5), ("()", "expected an expression", 2),
                          ("1)", "extra token", 2), ("2*", "expected an expression", 3),
                          ("(1 2)", "expected ')'", 4)):
        e = tr.error(t, src)
        t.check((e.msg, e.col) == (msg, col), f"{src!r}: {e!r}, not {msg!r} at column {col}")
