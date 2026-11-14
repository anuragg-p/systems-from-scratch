"""00.01 How a kernel works

The cross compiler produces a RISC-V ELF linked to run at 0x80000000,
with _entry as its first byte - the one address QEMU's virt machine
jumps to. Everything else depends on that one fact.
"""

import re


def test(t):
    kernel = f"{t.root}/build-test/kernel/kernel"

    head = t.run([t.track.tool("objdump"), "-f", kernel]).stdout
    t.check("elf64-littleriscv" in head, f"not a 64-bit RISC-V ELF:\n{head}")
    m = re.search(r"start address 0x([0-9a-f]+)", head)
    t.check(m and int(m.group(1), 16) == 0x80000000,
            f"ELF entry point should be 0x80000000:\n{head}")

    syms = {}
    for line in t.run([t.track.tool("nm"), kernel]).stdout.splitlines():
        parts = line.split()
        if len(parts) == 3:
            syms[parts[2]] = int(parts[0], 16)
    t.check(syms.get("_entry") == 0x80000000, "_entry must be the first byte of the kernel")
    # The highest byte any section occupies must be inside the 128 MB of RAM.
    top = 0
    for line in t.run([t.track.tool("objdump"), "-h", kernel]).stdout.splitlines():
        f = line.split()
        if len(f) >= 4 and f[0].isdigit():
            top = max(top, int(f[3], 16) + int(f[2], 16))
    t.check(0x80000000 < top < 0x80000000 + 128 * 1024 * 1024,
            f"the kernel image must fit in the 128 MB of RAM QEMU gives us (ends at {top:#x})")
    t.check(syms.get("_trampoline", 1) % 4096 == 0, "the trampoline must start on a page boundary")
