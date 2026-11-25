"""01.10 Target code: loads, stores, tests and branches

The machine gains memory (1 MiB; sp starts at its top; an address outside it is a fault),
addi, ld and sd, and the routine divzero ("line N: division by zero", status 1). ./mote -S
writes assembly for it: main:, the frame (8 bytes a variable, rounded up to 16), a load for
every use and a store for every assignment with the variable's name in a comment, t0 to t6 as a
stack, each condition one branch on the opposite comparison to .Ln, a check before each div,
li a0, 0 and call exit at the end. More than seven values waiting is "expression too deep". gcd
on 1071 462 runs 142 instructions. What it writes runs on the machine as the reference says,
and the RISC-V assembler takes it.
"""

import os

GCD_S = """main:
    addi sp, sp, -16
    call getint
    sd   a0, 0(sp)        # i
    call getint
    sd   a0, 8(sp)        # j
.L1:
    ld   t0, 0(sp)        # i
    ld   t1, 8(sp)        # j
    beq  t0, t1, .L2
    ld   t0, 0(sp)        # i
    ld   t1, 8(sp)        # j
    ble  t0, t1, .L3
    ld   t0, 0(sp)        # i
    ld   t1, 8(sp)        # j
    sub  t0, t0, t1
    sd   t0, 0(sp)        # i
    j    .L4
.L3:
    ld   t0, 8(sp)        # j
    ld   t1, 0(sp)        # i
    sub  t0, t0, t1
    sd   t0, 8(sp)        # j
.L4:
    j    .L1
.L2:
    ld   t0, 0(sp)        # i
    mv   a0, t0
    call putint
    li   a0, 0
    call exit
"""

MEMORY = """main:
    addi sp, sp, -16
    mv   a0, sp
    call putint          # 1048560
    li   t0, -5
    sd   t0, 8(sp)
    li   t0, 9223372036854775807
    sd   t0, 0(sp)
    ld   a0, 8(sp)
    call putint          # -5
    ld   a0, 0(sp)
    call putint
    addi a0, zero, -2048
    call putint
    li   t1, 1048568
    sd   t1, 0(t1)       # the last 8 bytes there are
    ld   a0, 0(t1)
    call putint
    li   a0, 0
    call exit
"""


def test(t):
    tr = t.track
    gcd = os.path.join(t.root, "programs", "gcd.mote")
    st, out, err = tr.prog(t, "mote", ["-S", gcd])
    t.check((st, out, err) == (0, GCD_S, ""), f"mote -S programs/gcd.mote:\n{out}{err}")
    st, out, err = tr.machine(t, GCD_S, "1071 462\n", "--count")
    t.check((st, out, err) == (0, "21\n", "142 instructions\n"), f"the naive gcd on the machine: {st} {out!r} {err!r}")
    tr.assembles(t, GCD_S)

    # The machine's memory.
    st, out, err = tr.machine(t, MEMORY)
    t.check((st, out.split()) == (0, ["1048560", "-5", str(2 ** 63 - 1), "-2048", "1048568"]), f"memory: {out.split()} {err}")
    st, out, err = tr.machine(t, "main:\n    li   t0, -5\n    sd   t0, -8(sp)\n    ret\n", "", "--trace")
    t.check("sd   t0, -8(sp)" in err and "mem[1048568] = -5" in err, f"--trace shows the store:\n{err}")
    for asm, msg in (("main:\n    ld   a0, 0(sp)\n", "2: address 1048576 is outside the memory"),
                     ("main:\n    sd   a0, -8(zero)\n", "2: address -8 is outside the memory"),
                     ("main:\n    li   t0, 1048569\n    ld   a0, 0(t0)\n", "3: address 1048569 is outside the memory"),
                     ("main:\n    ld   a0, 8 sp\n", "2: expected '('"),
                     ("main:\n    sd   a0, 8(sp\n", "2: expected ')'")):
        st, out, err = tr.machine(t, asm)
        t.check((st, err) == (1, f"machine: t{t._lang_files}.s:{msg}\n"), f"{asm!r}: {st} {err!r}")
    t.check(tr.machine(t, "main:\n    li   a0, 7\n    call divzero\n") == (1, "", "line 7: division by zero\n"),
            "call divzero")
    tr.assembles(t, MEMORY)

    # The parts of the code.
    code = tr.asm(t, "read a\nb := 0\nwrite a / b\n")
    t.check("    bnez t1, .L1\n    li   a0, 3\n    call divzero\n.L1:\n    div  t0, t0, t1\n" in code,
            f"a check before each division:\n{code}")
    t.check(tr.compiled(t, "read a\nb := 0\nwrite 1\nwrite a / b\n", "5") == (1, "1\n", "line 4: division by zero\n"),
            "a compiled division by zero stops at its line")
    for src, frame in (("write 1\n", None), ("a := 1\n", 16), ("a := 1\nb := a\n", 16), ("a := 1\nb := a\nc := b\n", 32)):
        code = tr.asm(t, src)
        line = code.split("\n")[1]
        t.check(code.startswith("main:\n") and (line == f"    addi sp, sp, -{frame}" if frame else "addi" not in code),
                f"{src!r}: the frame should be {frame}:\n{code}")
    code = tr.asm(t, "a := 1\nb := 2\nc := a - (b - (a * b))\nwrite c\n")
    t.check("    ld   t1, 8(sp)        # b\n    ld   t2, 0(sp)        # a\n    ld   t3, 8(sp)        # b\n"
            "    mul  t2, t2, t3\n    sub  t1, t1, t2\n    sub  t0, t0, t1\n    sd   t0, 16(sp)       # c\n" in code,
            f"t0 to t6 as a stack:\n{code}")
    t.check(all("# " in l for l in code.split("\n") if l.startswith(("    ld", "    sd"))),
            "every load and store names its variable")
    for op, branch in (("==", "bne"), ("!=", "beq"), ("<", "bge"), (">=", "blt"), (">", "ble"), ("<=", "bgt")):
        code = tr.asm(t, f"read a\nwhile a {op} 3 do\n  a := a + 1\nend\n")
        t.check(f"    {branch:<4} t0, t1, .L2\n" in code, f"while a {op} 3 leaves the loop on {branch}:\n{code}")
        for a in (2, 3, 4):
            src = f"read a\nif a {op} 3 then\n  write 1\nelse\n  write 0\nend\n"
            want = tr.gen().evaluate(src, f"{a}")[1]
            got = tr.compiled(t, src, f"{a}")
            t.check(got == (0, want, ""), f"if {a} {op} 3: {got}, not {want!r}")

    # Seven values waiting fit in t0 to t6; the eighth does not.
    t.check(tr.compiled(t, "write 1 - (2 - (3 - (4 - (5 - (6 - 7)))))\n")[:2] == (0, "4\n"), "seven values fit")
    st, out, err = tr.mote(t, "x := 1 - (2 - (3 - (4 - (5 - (6 - (7 - 8))))))\n", "-S")
    t.check((st, err) == (1, f"t{t._lang_files}.mote:1:40: expression too deep\n"), f"the eighth: {st} {err!r}")

    # Random programs, compiled and run on the machine, held to the reference; the assembler
    # takes what is written.
    g = tr.gen()
    for k, (text, text_in, want) in enumerate(g.sample(110, 150)):
        code = tr.asm(t, text)
        got = tr.machine(t, code, text_in)
        t.check(got == (0, want, ""), f"the compiled program and the reference differ on:\n{text}\ninput {text_in}\n"
                                      f"machine: {got}\nreference: {want!r}\n{code}")
        if k < 20:
            tr.assembles(t, code)
