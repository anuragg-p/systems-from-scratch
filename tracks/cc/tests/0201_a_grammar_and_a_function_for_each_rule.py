"""02.01 A grammar, and a function for each rule

The parser reads an expression of numbers, "+" and "-" by recursive
descent, a function for each rule, and builds a tree of nodes, left to
right: 1 - 2 - 3 is (1 - 2) - 3. --tree prints the tree, one node a line,
each child two spaces in from its parent, the left one first: the operator,
or "num" and the value. Anything after the expression is "extra token"; a
missing operand is "expected an expression".
"""


def test(t):
    tr = t.track
    st, out, err = tr.compile(t, "1-2-3", "--tree")
    t.check((st, out) == (0, "-\n  -\n    num 1\n    num 2\n  num 3\n"), f"--tree of 1-2-3:\n{out}{err}")
    t.check(tr.asm(t, "42", "--tree") == "num 42\n", "a number alone is one node")
    for src, want in (("1-2-3", "(- (- 1 2) 3)"),
                      ("1+2-3+4", "(+ (- (+ 1 2) 3) 4)"),
                      ("10 - 4 + 3", "(+ (- 10 4) 3)"),
                      ("7", "7")):
        got = tr.sexp(tr.tree(t, src))
        t.check(got == want, f"{src}: {got}, not {want}")
    # The tree is what runs: left to right.
    tr.value(t, "1-2-3", -4)
    tr.value(t, "10 - 4 + 3", 9)
    tr.value(t, "0 - 1 - 1 - 1 - 1 - 1 - 1 - 1 - 1 - 1", -9)
    for src, msg, col in (("1+", "expected an expression", 3), ("1 2", "extra token", 3),
                          ("+", "expected an expression", 2), ("1 - x", "expected an expression", 5),
                          ("", "expected an expression", 1)):
        e = tr.error(t, src)
        t.check((e.msg, e.col) == (msg, col), f"{src!r}: {e!r}, not {msg!r} at column {col}")
