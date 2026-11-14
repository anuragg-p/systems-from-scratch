"""02.01 The physical memory map

The linker script and memlayout.h agree on where everything is: kernel
text from 0x80000000 up to a page boundary, then data and bss, then free
RAM up to PHYSTOP (128 MB after KERNBASE).
"""


def test(t):
    s = t.track.boot(t)
    m = s.expect(r"\[02\.01\] text 0x0*80000000-0x([0-9a-f]+), data\+bss 0x([0-9a-f]+)-0x([0-9a-f]+), "
                 r"free RAM 0x([0-9a-f]+)-0x([0-9a-f]+) \((\d+) pages\)")
    etext, data, end, free0, phystop = (int(g, 16) for g in m.groups()[:5])
    pages = int(m.group(6))
    t.check(etext % 4096 == 0, "text must end on a page boundary so data can be mapped without X")
    t.check(data == etext, "data starts right where text ends")
    t.check(free0 == (end + 4095) // 4096 * 4096, "free RAM starts at the first page after the kernel")
    t.check(phystop == 0x80000000 + 128 * 1024 * 1024, "PHYSTOP is 128 MB above KERNBASE")
    t.check(pages == (phystop - free0) // 4096, "page count matches the free range")
    t.track.selftest(s, "02.01")
