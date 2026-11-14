"""Insert figure lines after the paragraph (or list, or code block) that contains an anchor."""
import os, re, sys
L = os.path.expanduser("~/Documents/WORK/misc/systems-from-scratch/tracks/xv6/lessons")
PLACES = [
 ("00-workbench/00.01-how-a-kernel-works.md", "the trampoline page at 0x80007000), and `.rodata` starts at",
  "The kernel image as `kernel.ld` lays it out: `_entry` at the first byte, the trampoline on a page of its own, and `end` after `.bss`.",
  "00.01-kernel-image.svg"),
 ("00-workbench/00.01-how-a-kernel-works.md", "position-independent code, no stack canaries",
  "`medlow` reaches 2 GB either side of address 0, and the kernel starts just past that; `medany` reaches 2 GB either side of the pc.",
  "00.01-mcmodel-reach.svg"),
 ("00-workbench/00.02-running-and-debugging-the-kernel.md", "lesson: for 01.02 it is `01.02: start() not written yet`.",
  "`./learn start` cuts out the first lesson with code. Each `./learn next` keeps what you wrote and cuts out the next one.",
  "00.02-workspace.svg"),
 ("01-boot/01.01-the-first-instruction.md", "the region, `call start`, takes it from there.",
  "Each hart's `sp` starts at the top of its own slice of `stack0`, and its stack grows down from there.",
  "01.01-stack0-slices.svg"),
 ("01-boot/01.01-the-first-instruction.md", "now starts at the very bottom of the array",
  "Without the + 1, hart N starts at the bottom of slice N, and hart 0 grows down out of `stack0`.",
  "01.01-stack0-without-plus-one.svg"),
 ("01-boot/01.02-machine-mode-and-the-drop-to-supervisor-mode.md", "\"Pretend we came from supervisor mode.\"",
  "`start` puts S in `mstatus.MPP` and the address of `main` in `mepc`. `mret` takes the mode from one and the pc from the other.",
  "01.02-mret.svg"),
 ("01-boot/01.02-machine-mode-and-the-drop-to-supervisor-mode.md", "`pmpaddr0 << 2`, here the whole 56-bit physical space).",
  "`pmpcfg0 = 0xf` sets read, write and execute with top-of-range matching, and `pmpaddr0` puts the top past every physical address.",
  "01.02-pmp-entry-0.svg"),
 ("01-boot/01.03-the-uart-and-printf.md", "sends a character; reading `RHR` (also offset 0) receives one.",
  "The UART's eight registers, one byte each from `UART0`, and the two that `uartputc_sync` uses.",
  "01.03-uart-registers.svg"),
 ("01-boot/01.03-the-uart-and-printf.md", "`while` makes 0 print as `0`, not nothing.",
  "`printint(1024, 10, 0)`: division stores the digits lowest first, and the print loop reads `buf` from the top down.",
  "01.03-printint-reverse.svg"),
 ("02-memory/02.01-the-physical-memory-map.md", "header; `kernel.ld` defines them.",
  "Physical addresses on QEMU `virt` as this kernel uses them: device registers low, RAM from `KERNBASE` to `PHYSTOP`.",
  "02.01-physical-map.svg"),
 ("02-memory/02.01-the-physical-memory-map.md", "unmapped (`proc_mapstacks` in `kernel/proc.c` maps one page per slot).",
  "The top pages of virtual memory. One address can mean different pages in the kernel's table and in a process's.",
  "02.01-virtual-top.svg"),
 ("02-memory/02.02-the-page-allocator.md", "`kalloc` returns it.",
  "Each free page holds the address of the next free page in its first 8 bytes. `kalloc` takes the head and fills it with 5s.",
  "02.02-free-list.svg"),
 ("02-memory/02.02-the-page-allocator.md", "`mappages` reports failure and `kvmmap` panics.",
  "With `r->next = 0`, every `kfree` drops the list it was handed, and only the last page freed is left on it.",
  "02.02-lost-list.svg"),
 ("02-memory/02.03-spinlocks-and-multiple-harts.md", "to 1; if it was already 1, the hart tries again, in a loop, until it wins.",
  "Two harts adding 1 to `x`, which holds 5. Without a lock both load 5. With one, hart 1 spins until hart 0 has stored.",
  "02.03-race-and-lock.svg"),
 ("02-memory/02.03-spinlocks-and-multiple-harts.md", "(acquire) means no later load or store may be reordered before the swap.",
  "Both harts swap 1 into `lk->locked`. The memory does one swap at a time, so only the first gets back 0.",
  "02.03-amoswap.svg"),
 ("02-memory/02.03-spinlocks-and-multiple-harts.md", "`pop_off` takes `noff` to 0 and `intena` was set.",
  "Two locks held, two `push_off`s. Interrupts come back only when the last `pop_off` takes `noff` to 0.",
  "02.03-push-pop-nesting.svg"),
 ("02-memory/02.04-sv39-page-tables.md", "leaving the caller to read or write it.",
  "`PA2PTE` moves the physical page number of `pa` into bits 53..10 of a PTE; the flags take the low bits.",
  "02.04-pte-bits.svg"),
 ("02-memory/02.04-sv39-page-tables.md", "the instruction under it vanishing (06.01).",
  "What `kvmmake` maps: devices and RAM at their own addresses, and two things at the top that are not: the trampoline and the kernel stacks.",
  "02.04-kernel-address-space.svg"),
]
for rel, anchor, cap, fig in PLACES:
    path = os.path.join(L, rel)
    lines = open(path).read().split("\n")
    if any(f"(figures/{fig})" in l for l in lines):
        continue
    hits = [i for i, l in enumerate(lines) if anchor in l]
    assert len(hits) == 1, (rel, anchor, hits)
    i = hits[0]
    # end of this block: the next blank line (lists: the next blank line not followed by an item or indent)
    while i + 1 < len(lines) and lines[i + 1].strip():
        i += 1
    while i + 2 < len(lines) and not lines[i + 1].strip() and re.match(r"^(\s+\S|- |\d+\. )", lines[i + 2]):
        i += 2
        while i + 1 < len(lines) and lines[i + 1].strip():
            i += 1
    lines[i + 1:i + 1] = ["", f"![{cap}](figures/{fig})"]
    open(path, "w").write("\n".join(lines))
    print("placed", fig, "after line", i + 1)
