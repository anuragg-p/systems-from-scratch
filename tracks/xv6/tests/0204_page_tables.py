"""02.04 Sv39 page tables

The kernel page table maps text read+execute, data read+write, devices at
their physical addresses and the trampoline at the top. A mapping built
by hand with mappages() costs exactly four pages, and the MMU really uses
it: a write through one virtual address shows up at another.
"""


def test(t):
    s = t.track.boot(t)
    m = s.expect_line(r"\[02\.04\] va 0x0*12345000 -> L2\[(\d+)\] L1\[(\d+)\] L0\[(\d+)\] -> pa 0x([0-9a-f]+)")
    l2, l1, l0 = (int(x) for x in m.groups()[:3])
    va = 0x12345000
    t.check((l2, l1, l0) == ((va >> 30) & 511, (va >> 21) & 511, (va >> 12) & 511),
            f"page-table indices for {va:#x} are wrong: {(l2, l1, l0)}")
    t.check(int(m.group(4), 16) % 4096 == 0, "a mapped physical page must be page aligned")
    t.track.selftest(s, "02.04")
