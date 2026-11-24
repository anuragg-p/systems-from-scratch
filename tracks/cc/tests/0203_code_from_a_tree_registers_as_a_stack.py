"""02.03 Code from a tree: registers as a stack

The code generator walks the tree: gen_expr(node, d) leaves the node's
value in reg[d], t0 to t5. A number is li; a binary operator computes its
left operand at d, its right one at d + 1, then one instruction into reg[d]
(add, sub, mul, div). main moves t0 into a0 and returns. The values are the
ones C gives, division rounding toward zero.
"""


def test(t):
    tr = t.track
    head, tail = "  .globl main\nmain:\n", "  mv a0, t0\n  ret\n"
    for src, body in (("1+2", ["li t0, 1", "li t1, 2", "add t0, t0, t1"]),
                      ("2*3+4", ["li t0, 2", "li t1, 3", "mul t0, t0, t1", "li t1, 4", "add t0, t0, t1"]),
                      ("2+3*4", ["li t0, 2", "li t1, 3", "li t2, 4", "mul t1, t1, t2", "add t0, t0, t1"]),
                      ("9/3-1", ["li t0, 9", "li t1, 3", "div t0, t0, t1", "li t1, 1", "sub t0, t0, t1"])):
        want = head + "".join(f"  {l}\n" for l in body) + tail
        got = tr.asm(t, src)
        t.check(got == want, f"the code for {src}:\n{got}\nnot\n{want}")
    # Five deep on the right: t0 to t5, and no more.
    got = tr.asm(t, "1-(2-(3-(4-(5-6))))")
    t.check("li t5, 6" in got and "t6" not in got and "sp" not in got, f"t0 to t5 for five levels:\n{got}")
    for src, want in (("1+2", 3), ("2*3+4", 10), ("2+3*4", 14), ("9/3-1", 2), ("10-20", -10),
                      ("7/2", 3), ("(0-7)/2", -3), ("7/(0-2)", -3), ("(0-7)/(0-2)", 3), ("0/5", 0),
                      ("46340*46340", 2147395600), ("(0-46340)*46340", -2147395600), ("2147483647-2147483647", 0),
                      ("1-(2-(3-(4-(5-6))))", -3)):
        tr.value(t, src, want)
