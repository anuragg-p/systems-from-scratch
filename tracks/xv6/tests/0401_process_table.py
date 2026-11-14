"""04.01 The process table and kernel stacks

Processes live in a fixed table of NPROC slots. Each slot owns a kernel
stack page mapped high in the kernel page table, with an unmapped guard
page below it, and a user page table that maps the trampoline and the
process's trapframe at the top.
"""


def test(t):
    s = t.track.boot(t)
    m = s.expect_line(r'\[04\.01\] pid (\d+) "selftest" in slot (\d+) of (\d+), kernel stack 0x([0-9a-f]+), sp 0x([0-9a-f]+)')
    pid, slot, nproc = int(m.group(1)), int(m.group(2)), int(m.group(3))
    kstack, sp = int(m.group(4), 16), int(m.group(5), 16)
    t.check(pid == 1 and slot == 0, "the self-test thread is the first process: pid 1 in slot 0")
    trampoline = (1 << 38) - 4096
    t.check(kstack == trampoline - (slot + 1) * 2 * 4096, f"kernel stack {kstack:#x} is not KSTACK({slot})")
    t.check(kstack < sp <= kstack + 4096, "sp must be inside this process's kernel stack page")
    t.track.selftest(s, "04.01")
