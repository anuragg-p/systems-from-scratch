"""01.08 Semantic analysis: the syntax tree and the symbol table

analyze() walks the parse tree once into the syntax tree. ./mote --tree prints it a statement
a line, indented by nesting, expressions in prefix form with each variable's index in the
symbol table: while (!= i#1 j#2). Chains are left-nested (a - b - c is (- (- a b) c)),
parentheses leave nothing behind. ./mote --symbols prints INDEX NAME LINE:COL, names numbered
from 1 in the order the text first gives them a value. The static rule: a name used before the
text gives it a value is "FILE:LINE:COL: x is used before anything gives it a value", status 1;
in x := x + 1 the right side is checked before x is entered.
"""

import os


def tree(tr, t, src):
    st, out, err = tr.mote(t, src, "--tree")
    if st != 0:
        raise tr.Fail(f"--tree failed on {src!r}: {err}")
    return out.split("\n")[:-1]


def test(t):
    tr = t.track
    gcd = os.path.join(t.root, "programs", "gcd.mote")
    st, out, err = tr.prog(t, "mote", ["--tree", gcd])
    t.check((st, out.split("\n")[:-1]) == (0, tr.GCD_TREE), f"--tree programs/gcd.mote:\n{out}{err}")
    st, out, err = tr.prog(t, "mote", ["--symbols", gcd])
    t.check((st, out) == (0, "1 i 2:6\n2 j 3:6\n"), f"--symbols programs/gcd.mote:\n{out}{err}")

    got = tree(tr, t, "a := 1\nb := 2\nc := 3\nwrite a - b - c\nwrite a - (b - c)\nwrite a + b * c\n"
                      "write (a + b) * c\nwrite -a * -(b / 7)\nwrite ((((a))))\nwrite 9223372036854775807\n")
    want = [":= a#1 1", ":= b#2 2", ":= c#3 3", "write (- (- a#1 b#2) c#3)", "write (- a#1 (- b#2 c#3))",
            "write (+ a#1 (* b#2 c#3))", "write (* (+ a#1 b#2) c#3)", "write (* (- a#1) (- (/ b#2 7)))",
            "write a#1", "write 9223372036854775807"]
    t.check(got == want, f"expressions in prefix form:\n" + "\n".join(got))
    got = tree(tr, t, "read n\nif n < 0 then\n  while n < 0 do\n    n := n + 1\n  end\nelse\n  if n == 0 then\n"
                      "  end\nend\nwrite n\n")
    want = ["read n#1", "if (< n#1 0)", "  while (< n#1 0)", "    := n#1 (+ n#1 1)", "else", "  if (== n#1 0)",
            "write n#1"]
    t.check(got == want, f"nested blocks:\n" + "\n".join(got))

    st, out, err = tr.mote(t, "read b\nx := b\nif b > 0 then\n  a := 1\nelse\n  c := a\nend\nb := 3\nread c\n",
                           "--symbols")
    t.check((st, out) == (0, "1 b 1:6\n2 x 2:1\n3 a 4:3\n4 c 6:3\n"),
            f"numbered in the order the text gives them values, at the first place: {out}{err}")

    for src, line, col, name in (("write y\n", 1, 7, "y"), ("x := x + 1\n", 1, 6, "x"),
                                 ("read a\nb := a + (c * 2)\n", 2, 11, "c"),
                                 ("while 1 < 2 do\n  n := n + 1\nend\n", 2, 8, "n"),
                                 ("if q > 0 then\nend\n", 1, 4, "q")):
        st, out, err = tr.mote(t, src, "--tree")
        t.check(st == 1 and out == "" and
                err == f"t{t._lang_files}.mote:{line}:{col}: {name} is used before anything gives it a value\n",
                f"{src!r}: {st} {err!r}")
    # The rule is about the text, not about what will happen: this passes, and only running it
    # can tell that x has no value (01.09).
    st, out, err = tr.mote(t, "if 1 > 2 then\n  x := 1\nend\nwrite x\n", "--tree")
    t.check(st == 0, f"x is given a value earlier in the text: {err}")
