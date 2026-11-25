"""01.01 A machine, and a program written in its language

./machine [--count] [--trace] FILE.s reads RISC-V assembly text in two passes (the labels, then
the instructions), runs it from main and ends with the status the program gives. 32 registers
by their RISC-V names, zero always 0; li, mv, neg, add, sub, mul, div (by zero -1, the most
negative number by -1 itself), the branches, j, call and ret, instructions 4 bytes apart. The
routines getint, putint and exit are the machine's own. --count prints "N instructions" and
--trace each instruction with its line and what it changed, on stderr. Every error is "machine:
FILE:LINE: message", status 1. programs/gcd.s gives math.gcd on every pair. Every program's
sources compile with -std=c11 -Wall -Wextra -pedantic -Werror.
"""

import math
import os
import random

MIN, MAX = -2 ** 63, 2 ** 63 - 1

ARITH = """main:
    li   t0, 7
    li   t1, -3
    add  a0, t0, t1
    call putint
    sub  a0, t0, t1
    call putint
    mul  a0, t0, t1
    call putint
    div  a0, t0, t1
    call putint
    neg  a0, t1
    call putint
    mv   a0, t0
    call putint
    div  a0, t0, zero
    call putint
    li   t3, -9223372036854775808
    li   t4, -1
    div  a0, t3, t4
    call putint
    li   t5, 9223372036854775807
    li   t6, 1
    add  a0, t5, t6
    call putint
    mul  a0, t5, t5
    call putint
    neg  a0, t3
    call putint
    sub  a0, t3, t6
    call putint
    li   zero, 5
    mv   a0, zero
    call putint
    li   s11, 12
    add  a0, s11, s11      # every register is one
    call putint
    li   a0, 0
    call exit
"""
ARITH_OUT = [4, 10, -21, -2, 3, 7, -1, MIN, MIN, 1, MIN, MAX, 0, 24]


def branch_program(op, a, b):
    operands = "t0, yes" if op in ("beqz", "bnez") else "yes" if op == "j" else "t0, t1, yes"
    return (f"main:\n    li   t0, {a}\n    li   t1, {b}\n    {op} {operands}\n    li   a0, 0\n"
            f"    call putint\n    call exit\nyes:\n    li   a0, 1\n    call putint\n    li   a0, 0\n    call exit\n")


TAKEN = {"beq": lambda a, b: a == b, "bne": lambda a, b: a != b, "blt": lambda a, b: a < b,
         "bge": lambda a, b: a >= b, "bgt": lambda a, b: a > b, "ble": lambda a, b: a <= b,
         "beqz": lambda a, b: a == 0, "bnez": lambda a, b: a != 0, "j": lambda a, b: True}


def test(t):
    tr = t.track
    with open(os.path.join(t.root, "programs", "gcd.s")) as f:
        gcd_s = f.read()
    with open(os.path.join(t.root, "programs", "gcd.in")) as f:
        t.check(f.read() == "1071 462\n", "programs/gcd.in is 1071 462")

    # gcd.s, held to math.gcd.
    rng = random.Random(101)
    pairs = [(1071, 462), (1, 1), (7, 13), (100, 75), (2 ** 40, 2 ** 20), (1, 999)] + \
        [(rng.randint(1, 3000), rng.randint(1, 3000)) for _ in range(40)]
    for a, b in pairs:
        got = tr.machine(t, gcd_s, f"{a}\n  {b} ")
        t.check(got == (0, f"{math.gcd(a, b)}\n", ""), f"gcd.s on {a} {b}: {got}, not {math.gcd(a, b)}")
    st, out, err = tr.machine(t, gcd_s, "1071 462\n", "--count")
    t.check((st, out, err) == (0, "21\n", "53 instructions\n"), f"--count on 1071 462: {st} {out!r} {err!r}")

    # --trace: the line, the instruction's text, and each register it changed.
    st, out, err = tr.machine(t, gcd_s, "1071 462\n", "--trace")
    want = ["   4  call getint               ra = 4  a0 = 1071",
            "   5  mv   s1, a0               s1 = 1071",
            "   6  call getint               ra = 12  a0 = 462",
            "   7  mv   s2, a0               s2 = 462",
            "   9  beq  s1, s2, done",
            "  10  ble  s1, s2, smaller",
            "  11  sub  s1, s1, s2           s1 = 609",
            "  12  j    loop"]
    lines = err.split("\n")
    t.check(lines[:8] == want and out == "21\n", f"--trace's first lines:\n" + "\n".join(lines[:8]))
    t.check(len(lines) == 54 and lines[-2] == "  20  call exit                 ra = 56",
            f"--trace has a line for each of the 53 instructions, call exit last: {lines[-3:]}")

    # Each instruction, and wrap-around arithmetic.
    st, out, err = tr.machine(t, ARITH)
    t.check(st == 0 and out.split() == [str(n) for n in ARITH_OUT], f"the arithmetic: {out.split()}, not {ARITH_OUT}")
    for op, fn in TAKEN.items():
        for a, b in ((-1, 1), (1, -1), (3, 3), (0, 5), (MIN, MAX), (MAX, MIN), (0, 0)):
            st, out, err = tr.machine(t, branch_program(op, a, b))
            want = "1\n" if fn(a, b) else "0\n"
            t.check((st, out) == (0, want), f"{op} with {a}, {b}: {out!r}, not {want!r}")

    # call puts the next instruction's address in ra; ret goes there. A main that calls nothing
    # may end with ret, and its status is a0.
    sub = "main:\n    li   a0, 21\n    call double\n    call putint\n    li   a0, 3\n    call exit\n" \
          "double:\n    add  a0, a0, a0\n    ret\n"
    st, out, err = tr.machine(t, sub, "", "--trace")
    t.check((st, out) == (3, "42\n") and "call double               ra = 8" in err,
            f"call and ret: status {st}, {out!r}\n{err}")
    t.check(tr.machine(t, "main:  li a0, 7   # a label and an instruction on one line\n    ret\n") == (7, "", ""),
            "a ret from main with ra untouched ends the program with status a0")
    t.check(tr.machine(t, "main:\n    li   a0, 300\n    call exit\n")[0] == 44, "exit's status is a0's low 8 bits")
    st, out, err = tr.machine(t, "main:\n    li   a0, 2\n    ret\n", "", "--count")
    t.check((st, err) == (2, "2 instructions\n"), f"--count of a two-instruction program: {st} {err!r}")

    # getint: white space, a sign, digits; the end of the input.
    echo = "main:\nloop:\n    call getint\n    call putint\n    j    loop\n"
    st, out, err = tr.machine(t, echo, " -17\n+4\t9223372036854775807 9223372036854775808 0")
    t.check((st, out.split(), err) == (1, ["-17", "4", str(MAX), str(MIN), "0"], "machine: getint: no more input\n"),
            f"getint: {st} {out.split()} {err!r}")
    st, out, err = tr.machine(t, echo, "5 x")
    t.check((st, out, err) == (1, "5\n", "machine: getint: not a number\n"), f"getint at 'x': {st} {out!r} {err!r}")

    # Errors: machine: FILE:LINE: message, status 1.
    for asm, msg in (("main:\n    xyz a0, a1\n", "2: unknown instruction 'xyz'"),
                     ("main:\n    li   q1, 5\n", "2: unknown register 'q1'"),
                     ("main:\n    li   , 5\n", "2: expected a register"),
                     ("main:\n    li   a0\n", "2: expected ','"),
                     ("main:\n    li   a0, x\n", "2: expected a number"),
                     ("main:\n    li   a0, 99999999999999999999\n", "2: number too large: 99999999999999999999"),
                     ("main:\n    j    nowhere\n", "2: no label 'nowhere'"),
                     ("main:\n    beqz a0,\n", "2: expected a label"),
                     ("main:\n    ret  a0\n", "2: unexpected text after the instruction: 'a0'"),
                     ("main:\n\n    li   a0, 1\n", "3: ran off the end of the program"),
                     ("main:\n    li   ra, 6\n    ret\n", "3: no instruction at address 6"),
                     ("main:\n    ret\nmain:\n", "3: label 'main' defined twice")):
        st, out, err = tr.machine(t, asm)
        name = f"t{t._lang_files}.s"
        t.check((st, out, err) == (1, "", f"machine: {name}:{msg}\n"), f"{asm!r}: {st} {err!r}, not {msg!r}")
    st, out, err = tr.machine(t, "start:\n    ret\n")
    t.check((st, err) == (1, f"machine: t{t._lang_files}.s: no label main to start at\n"), f"no main: {err!r}")
    for argv in ([], ["a.s", "b.s"], ["--fast", "a.s"]):
        st, out, err = tr.prog(t, "machine", argv)
        t.check(st == 2 and err.startswith("usage: machine"), f"machine {' '.join(argv)}: {st} {err!r}")
    st, out, err = tr.prog(t, "machine", ["nosuch.s"])
    t.check((st, err) == (1, "machine: cannot open nosuch.s\n"), f"a missing file: {st} {err!r}")

    # The text is the real thing: the RISC-V assembler takes it, when there is one.
    for text in (gcd_s, ARITH, sub, branch_program("bgt", 1, 2), echo):
        tr.assembles(t, text)

    said = tr.warnings(t)
    t.check(not said, f"the sources are not warning-free under -Werror:\n{said}")
