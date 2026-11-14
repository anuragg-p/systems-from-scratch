"""03.01 Kernel traps

stvec points at kernelvec. Four instructions that cannot complete each
trap into kerneltrap() with the right cause: reading an M-mode register
(proving the kernel really runs in S-mode), ebreak, a load from an
unmapped address, and a store into read-only kernel text.
"""


def test(t):
    s = t.track.boot(t)
    s.expect(r"\[03\.01\] csrr mstatus from S-mode -> scause 2 ")
    s.expect(r"\[03\.01\] ebreak -> scause 3 ")
    s.expect(r"\[03\.01\] load from 0x0+ -> scause 13 .*stval 0x0+\r?\n")
    s.expect(r"\[03\.01\] store to 0x0*80000000 -> scause 15 .*stval 0x0*80000000")
    t.track.selftest(s, "03.01")
