"""01.01 The first instruction

Watches the very first instructions QEMU runs: the boot ROM at 0x1000
reads the hart id and jumps to 0x80000000, where entry.S gives each hart
a stack before calling C.
"""

import os
import re


def blocks(log):
    """QEMU's -d in_asm log -> list of (first address, instruction text)."""
    out = []
    for chunk in log.split("IN:")[1:]:
        lines = [l for l in chunk.splitlines() if re.match(r"0x[0-9a-f]+:", l)]
        if lines:
            out.append((int(lines[0].split(":")[0], 16), "\n".join(lines)))
    return out


def test(t):
    log = os.path.join(t.tmp, "in_asm.log")
    s = t.track.boot(t, disk=False, qemu_args=["-d", "in_asm", "-D", log])
    s.expect(r"xv6 kernel is booting")
    s.close()

    bs = blocks(open(log).read())
    t.check(bs, "QEMU logged no instructions")
    t.check(bs[0][0] == 0x1000, f"first instruction should be the boot ROM at 0x1000, was {bs[0][0]:#x}")
    rom = [text for addr, text in bs if addr < 0x2000]
    t.check(any("mhartid" in r for r in rom), "the boot ROM should read mhartid (and pass it in a0)")
    entry = [text for addr, text in bs if addr == 0x80000000]
    t.check(entry, "no hart ever reached 0x80000000")
    t.check("mhartid" in entry[0], "entry.S should read mhartid to pick this hart's stack")
    first_kernel = next(i for i, (a, _) in enumerate(bs) if a == 0x80000000)
    t.check(all(a < 0x2000 for a, _ in bs[:first_kernel]),
            "nothing but the boot ROM should run before _entry")
