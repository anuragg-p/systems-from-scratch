"""02.06 Out of registers: spilling to memory

When the left operand is in t5, the last register, there is none for the
right one: spill() pushes t5 (addi sp, sp, -16; sd), computes the right
operand in t5 (spilling again if it must), pops the left one into t6 (ld;
addi sp, sp, 16), and does the operation into t5 with t6 on the left. So an
expression of any depth compiles, with the operands in the right order, and
the stack pointer is back where it was when main returns (the program gets
back to _start, which is the proof). Left-nested expressions never spill.
"""

import importlib.util
import os


def exprgen():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exprgen.py")
    spec = importlib.util.spec_from_file_location("cc_exprgen", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test(t):
    tr = t.track
    g = exprgen()

    def check(tree):
        tr.value(t, g.show(tree), g.value(tree))

    # Right-nested: five operators fit in t0 to t5; six spill once, seven twice, twenty 15 times.
    for n, spills in ((5, 0), (6, 1), (7, 2), (20, 15)):
        tree = g.right_nested(n, "-")
        src = g.show(tree)
        code = tr.asm(t, src)
        pushes, pops = code.count("addi sp, sp, -16"), code.count("addi sp, sp, 16")
        t.check(pushes == pops == spills and code.count("  sd t5, 0(sp)") == spills
                and code.count("  ld t6, 0(sp)") == spills,
                f"{src}: {spills} spills, as many pops as pushes:\n{code}")
        check(tree)
    # The code of one spill, in 1 - (2 - (3 - (4 - (5 - (6 - 7))))).
    code = tr.asm(t, g.show(g.right_nested(6, "-")))
    want = ("  li t5, 6\n  addi sp, sp, -16\n  sd t5, 0(sp)\n  li t5, 7\n  ld t6, 0(sp)\n"
            "  addi sp, sp, 16\n  sub t5, t6, t5\n  sub t4, t4, t5\n")
    t.check(want in code, f"one spill, the left operand back in t6, on the left of sub:\n{code}")

    # Each operator that cares which side is which, as the one that spills: five additions put
    # 1s in t0 to t4, then A op (B + C) has A in t5 and no register for the right side.
    def at_t5(op, a, b, c):
        tree = g.bin(op, a, g.bin("+", b, c))
        for _ in range(5):
            tree = g.bin("+", 1, tree)
        return tree
    for op, a, b, c in (("-", 100, 3, 4), ("/", 100, 3, 4), ("%", 100, 3, 4), ("<<", 1, 2, 3), (">>", 100, 1, 2),
                        ("<", 1, 2, 3), ("<=", 6, 2, 3), (">", 1, 2, 3), (">=", 5, 2, 3), ("==", 5, 2, 3),
                        ("!=", 5, 2, 3), ("*", 7, 2, 3), ("&", 12, 4, 6), ("|", 8, 1, 2), ("^", 15, 3, 2)):
        tree = at_t5(op, a, b, c)
        t.check("ld t6, 0(sp)" in tr.asm(t, g.show(tree)), f"{g.show(tree)} should spill")
        check(tree)

    # Left-nested: any depth in two registers, and no stack.
    for n in (6, 7, 20):
        tree = g.left_nested(n, "-")
        code = tr.asm(t, g.show(tree))
        t.check("sp" not in code and "t2" not in code, f"{g.show(tree)}: two registers and no stack:\n{code}")
        check(tree)
    # Mixed: deep on the left and the right, and deep on both sides at once.
    left, right = g.left_nested(8, "+"), g.right_nested(8, "-")
    for tree in (g.bin("-", left, right), g.bin("-", right, left), g.bin("-", g.bin("*", right, 2), right),
                 g.bin("-", g.bin("-", right, right), g.bin("-", right, g.bin("-", 1, right))),
                 g.right_nested(12, "^", first=3), g.bin("<", right, g.right_nested(10, "+"))):
        check(tree)
    # The sample a reader runs at this lesson.
    tr.value(t, "9 - (8 - (7 - (6 - (5 - (4 - (3 - 2))))))", 4)

    # 200 random expressions, the same every run, through value(): ours, gcc's and Python's.
    tr.parallel(t, lambda ctx, item: tr.value(ctx, item[0], item[1]), g.sample(2026, 200, depth=9))
