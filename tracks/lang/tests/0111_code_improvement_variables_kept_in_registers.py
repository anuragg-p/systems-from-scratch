"""01.11 Code improvement: variables kept in registers

./mote -S -O runs improve() first: each variable's appearances in the tree are counted, and the
most used get s1 to s11 (a tie to the lower index); the rest keep slots in memory. A variable in
a register costs no instruction to use; x := a op b is computed straight into x's register,
x := y is a mv and x := 5 a li; a condition branches on the registers themselves; with no
variable left in memory there is no addi sp. gcd on 1071 462: 61 instructions, against 142
without -O and 53 for programs/gcd.s by hand. A program with 13 variables keeps 2 in memory.
What it writes runs as the reference says, and agree has its fifth way.
"""

import os

GCD_O = """main:
    call getint
    mv   s1, a0
    call getint
    mv   s2, a0
.L1:
    beq  s1, s2, .L2
    ble  s1, s2, .L3
    sub  s1, s1, s2
    j    .L4
.L3:
    sub  s2, s2, s1
.L4:
    j    .L1
.L2:
    mv   a0, s1
    call putint
    li   a0, 0
    call exit
"""


def test(t):
    tr = t.track
    gcd = os.path.join(t.root, "programs", "gcd.mote")
    st, out, err = tr.prog(t, "mote", ["-S", "-O", gcd])
    t.check((st, out, err) == (0, GCD_O, ""), f"mote -S -O programs/gcd.mote:\n{out}{err}")
    counts = {}
    for name, text in (("improved", GCD_O), ("naive", tr.asm(t, open(gcd).read())),
                       ("by hand", open(os.path.join(t.root, "programs", "gcd.s")).read())):
        st, out, err = tr.machine(t, text, "1071 462\n", "--count")
        t.check((st, out) == (0, "21\n"), f"gcd {name}: {st} {out!r}")
        counts[name] = int(err.split()[0])
    t.check(counts == {"improved": 61, "naive": 142, "by hand": 53}, f"the counts on 1071 462: {counts}")
    tr.assembles(t, GCD_O)

    # The most used first; a tie to the lower index; s0 is never used.
    code = tr.asm(t, "a := 1\nb := 2\nb := b + b\nc := b\nwrite c + a\n", opt=True)
    want = ("main:\n    li   s2, 1\n    li   s1, 2\n    add  s1, s1, s1\n    mv   s3, s1\n    add  t0, s3, s2\n"
            "    mv   a0, t0\n    call putint\n    li   a0, 0\n    call exit\n")
    t.check(code == want, f"b (5 uses) gets s1; a and c (2 each) tie, and a (index 1) gets s2:\n{code}")

    # 13 variables: the 11 most used in s1 to s11, the two least used in memory.
    names = [f"v{k}" for k in range(13)]
    src = "".join(f"read {v}\n" for v in names)
    src += "".join(f"{v} := {v} + {v}\n" * (13 - k) for k, v in enumerate(names))
    src += "".join(f"write {v}\n" for v in names)
    code = tr.asm(t, src, opt=True)
    regs = [f"s{k}" for k in range(1, 12)]
    t.check(code.startswith("main:\n    addi sp, sp, -16\n") and "s0" not in code and
            all(r in code for r in regs) and "# v11" in code and "# v12" in code and "# v10" not in code,
            f"13 variables: 11 in registers, v11 and v12 in memory:\n{code}")
    numbers = [3, -1, 7, 2 ** 40, 0, 5, -9, 11, 12, 13, 14, 15, 16]
    want = "".join(f"{tr.gen().wrap(n * 2 ** (13 - k))}\n" for k, n in enumerate(numbers))
    got = tr.machine(t, code, " ".join(map(str, numbers)))
    t.check(got == (0, want, ""), f"13 variables, run: {got}, not {want!r}")
    t.check(tr.compiled(t, src, " ".join(map(str, numbers)))[:2] == (0, want), "and the same without -O")
    tr.assembles(t, code)

    code = tr.asm(t, "x := 5\ny := x\nx := y * 2\nread y\nwrite x / y\n", opt=True)
    t.check("    li   s1, 5\n    mv   s2, s1\n    li   t1, 2\n    mul  s1, s2, t1\n    call getint\n    mv   s2, a0\n"
            in code and "addi" not in code and "    bnez s2, .L1\n" in code and "    div  t0, s1, s2\n" in code,
            f"li, mv, straight into the register, no frame:\n{code}")
    st, out, err = tr.mote(t, "write 1\n", "-O")
    t.check(st == 2 and err.startswith("usage: mote"), f"-O goes with -S: {st} {err!r}")

    g = tr.gen()
    for k, (text, text_in, want) in enumerate(g.sample(111, 150)):
        code = tr.asm(t, text, opt=True)
        got = tr.machine(t, code, text_in)
        t.check(got == (0, want, ""), f"the improved program and the reference differ on:\n{text}\ninput {text_in}\n"
                                      f"machine: {got}\nreference: {want!r}\n{code}")
        if k < 20:
            tr.assembles(t, code)
