"""02.05 Unary operators and comparisons

unary: "+x" is x, "-x" neg, "!x" seqz, "~x" not; they bind tighter than
any binary operator, and nest. equality ("==", "!=") and relational ("<",
"<=", ">", ">=") sit between "&" and "<<"; a > b is parsed as b < a, and
a >= b as b <= a. A comparison is 1 or 0: == is xor then seqz, != xor then
snez, < slt, <= slt the other way round then xori 1.
"""


def test(t):
    tr = t.track
    for src, want in (("-2*3", "(* (- 2) 3)"),
                      ("!1==0", "(== (! 1) 0)"),
                      ("1<2==1", "(== (< 1 2) 1)"),
                      ("1>2", "(< 2 1)"),
                      ("1>=2", "(<= 2 1)"),
                      ("1<=2", "(<= 1 2)"),
                      ("+3", "3"),
                      ("- -3", "(- (- 3))"),
                      ("-!~1", "(- (! (~ 1)))"),
                      ("1 - -1", "(- 1 (- 1))"),
                      ("1&2==2", "(& 1 (== 2 2))"),
                      ("1==2<3", "(== 1 (< 2 3))"),
                      ("1<2<<3", "(< 1 (<< 2 3))"),
                      ("1<2<3", "(< (< 1 2) 3)"),
                      ("3>2>1", "(< 1 (< 2 3))"),
                      ("1!=2!=3", "(!= (!= 1 2) 3)")):
        got = tr.sexp(tr.tree(t, src))
        t.check(got == want, f"{src}: {got}, not {want}")
    head, tail = "  .globl main\nmain:\n", "  mv a0, t0\n  ret\n"
    for src, body in (("1<=2", ["li t0, 1", "li t1, 2", "slt t0, t1, t0", "xori t0, t0, 1"]),
                      ("1>2", ["li t0, 2", "li t1, 1", "slt t0, t0, t1"]),
                      ("3==4", ["li t0, 3", "li t1, 4", "xor t0, t0, t1", "seqz t0, t0"]),
                      ("3!=4", ["li t0, 3", "li t1, 4", "xor t0, t0, t1", "snez t0, t0"]),
                      ("-!~5", ["li t0, 5", "not t0, t0", "seqz t0, t0", "neg t0, t0"])):
        want = head + "".join(f"  {l}\n" for l in body) + tail
        got = tr.asm(t, src)
        t.check(got == want, f"the code for {src}:\n{got}\nnot\n{want}")
    for src, want in (("1<2", 1), ("2<1", 0), ("1<1", 0), ("(0-1)<0", 1), ("0<(0-1)", 0), ("1<=1", 1),
                      ("2<=1", 0), ("(0-5)<=(0-5)", 1), ("1>0", 1), ("0>1", 0), ("1>=1", 1), ("0>=1", 0),
                      ("(0-3)>(0-4)", 1), ("1==1", 1), ("1==2", 0), ("1!=1", 0), ("3!=4", 1),
                      ("-3", -3), ("- -3", 3), ("-(2+3)", -5), ("+7", 7), ("!0", 1), ("!5", 0), ("!!5", 1),
                      ("!(0-1)", 0), ("~0", -1), ("~5", -6), ("~(0-1)", 0), ("-2*3", -6), ("1<2==1", 1),
                      ("!1==0", 1), ("1<2<3", 1), ("3>2>1", 0), ("-2147483647 - 1 < 0", 1),
                      ("2147483647 > -2147483647", 1), ("-3 < 2 == !0", 1), ("~-1 == 0", 1), ("-~5", 6)):
        tr.value(t, src, want)
    for src, msg, col in (("-", "expected an expression", 2), ("1 < ", "expected an expression", 5),
                          ("!", "expected an expression", 2), ("1 =< 2", "extra token", 3),
                          ("--1", "expected an expression", 1)):
        e = tr.error(t, src)
        t.check((e.msg, e.col) == (msg, col), f"{src!r}: {e!r}, not {msg!r} at column {col}")
