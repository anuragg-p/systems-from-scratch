"""Inline lesson figures for xv6 modules 00-02.

Writes tracks/xv6/lessons/NN-slug/figures/NN.LL-name.svg. Numbers come from the
reference build (riscv64-elf-objdump -h, kernel.sym) and kernel/*.h; see the
comments next to each one.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from figart import Art, SW, esc  # noqa: E402
from figlib import Fig  # noqa: E402

LESSONS = os.path.expanduser("~/Documents/WORK/misc/systems-from-scratch/tracks/xv6/lessons")
MODDIR = {"00": "00-workbench", "01": "01-boot", "02": "02-memory"}


def raw(a, s):
    a.add(s)


def rect(a, x, y, w, h, cls="s f", dash=False, rx=0):
    a.box(x, y, w, h, cls, rx=rx, dash=dash)


def tsp(text, cls, size=None, mono=False):
    c = cls + (" mono" if mono else "")
    fs = f' font-size="{size}"' if size else ""
    return f'<tspan class="{c}"{fs}>{esc(text)}</tspan>'


def rich(a, x, y, parts, size=12, anchor="start", cls="t", mono=False):
    """A text line made of (text, cls, mono) parts."""
    c = cls + (" mono" if mono else "")
    an = f' text-anchor="{anchor}"' if anchor != "start" else ""
    inner = "".join(tsp(t, k, None, m) if k else esc(t) for t, k, m in parts)
    a.add(f'<text class="{c}" x="{x}" y="{y}" font-size="{size}"{an}>{inner}</text>')


# ================================================================== 00.01

def f0001_image():
    # The finished kernel, which is what 00.01 shows (there is no kernel at 00.01).
    # objdump -h build/at/xv6/finished/build/kernel/kernel: .text 0x80000000 size 0xa000,
    # .rodata 0x8000a000, .data 0x8000aa20, .bss 0x8000b000 size 0x147400 -> end 0x80152400;
    # _trampoline 0x80009000; fb 0x80015000 (module 09's framebuffer, 0x12c000 bytes) and
    # stack0 0x80149f70 (kernel.sym).
    a = Art("f0001a", "The kernel image as kernel.ld lays it out", 184)
    y, h = 64, 56
    segs = [(24, 180, ".text", "code, 9 pages", "s f"), (204, 84, "trampoline", "1 page", "s fs"),
            (288, 54, ".rodata", "", "s f"), (342, 42, ".data", "", "s f"), (384, 152, ".bss", "", "s f")]
    for x, w, name, sub, cls in segs:
        rect(a, x, y, w, h, cls)
        mono = name.startswith(".") or name == "trampoline"
        size = 13 if w > 100 else (11.5 if w > 60 else 10.5)
        cx = x + w / 2 if name != ".bss" else 436
        a.text(cx, y + (26 if sub else (20 if name == ".bss" else 32)), name, "t", size, "middle", 600, mono=mono)
        if sub:
            a.text(cx, y + 44, sub, "tm", 11, "middle")
    # inside .bss, not to scale: fb, 300 pages, then stack0 0x80149f70 .. 0x80151f70
    rect(a, 392, y + 28, 90, 20, "s fs")
    a.text(437, y + 42, "fb, 300 pages", "tm", 9.5, "middle")
    rect(a, 488, y, 48, h, "s fs")
    a.text(512, y + 32, "stack0", "tm", 10, "middle", mono=True)
    # free memory after end
    rect(a, 536, y, 80, h, "m", dash=True)
    a.text(576, y + 26, "free", "tm", 11.5, "middle")
    a.text(576, y + 42, "pages", "tm", 11.5, "middle")
    # symbols above, addresses below
    for x, sym, addr in ((24, "_entry", "0x80000000"), (204, "_trampoline", "0x80009000"),
                         (288, "etext", "0x8000a000"), (536, "end", "0x80152400")):
        cls = "ta" if sym == "_entry" else "t"
        a.line(x, y - 12, x, y, "a" if sym == "_entry" else "s")
        a.line(x, y + h, x, y + h + 8, "m")
        anchor = "start" if x == 24 else "middle"
        a.text(x, y - 18, sym, cls, 12, anchor, 600, mono=True)
        a.text(x, y + h + 22, addr, "tm", 10.5, anchor, mono=True)
    a.text(24, 34, "the boot ROM jumps here", "ta", 11)
    a.text(24, 172, "low addresses", "tm", 11)
    a.text(616, 172, "high addresses", "tm", 11, "end")
    a.line(108, 168, 520, 168, "m", arrow=True)
    return a


def f0001_medany():
    # -mcmodel=medlow: absolute addresses from lui+addi, a signed 32-bit range [-2 GB, +2 GB).
    # -mcmodel=medany: auipc+addi, pc-relative, pc +- 2 GB. The kernel starts at 0x80000000.
    a = Art("f0001b", "What -mcmodel=medlow and medany can reach", 214)

    def X(gb):
        return 40 + (gb + 2) * 92
    axis = 168
    kx = X(2)
    a.add(f'<rect class="af" x="{kx}" y="24" width="12" height="{axis - 24}"/>')
    a.line(kx, 24, kx, axis, "a")
    # medlow
    a.text(40, 46, "-mcmodel=medlow", "t", 12, mono=True, weight=600)
    a.text(170, 46, "absolute: lui + addi", "tm", 11)
    rect(a, X(-2), 56, X(2) - X(-2), 22, "m fs", rx=4)
    a.text((X(-2) + X(2)) / 2, 71, "reachable: -2 GB to +2 GB", "tm", 11, "middle")
    a.text(kx + 20, 64, "the kernel starts here,", "ta", 11.5, weight=600)
    a.text(kx + 20, 80, "just out of medlow's reach", "ta", 11.5)
    # medany
    a.text(40, 108, "-mcmodel=medany", "t", 12, mono=True, weight=600)
    a.text(170, 108, "pc-relative: auipc + addi", "tm", 11)
    rect(a, X(0), 118, X(4) - X(0), 22, "s f", rx=4)
    a.text((X(0) + kx) / 2, 133, "pc - 2 GB", "t", 11, "middle")
    a.text((kx + 12 + X(4)) / 2, 133, "pc + 2 GB", "t", 11, "middle")
    # axis
    a.line(28, axis, 616, axis, "m")
    for gb, lab in ((-2, "-2 GB"), (0, "0"), (2, "+2 GB"), (4, "+4 GB")):
        a.line(X(gb), axis - 5, X(gb), axis + 5, "s")
        a.text(X(gb), axis + 20, lab, "ta" if gb == 2 else "tm", 11, "middle", mono=True)
    a.text(kx, axis + 36, "0x80000000", "ta", 11, "middle", mono=True)
    return a


def f0001_trip():
    # One `ls` through the finished kernel: down to the disk and back, then out to the console.
    f = Fig("f0001c", "One ls, from the shell down to the disk and back", 432)
    layers = [("ls", "a user program, started by the shell", "s f"),
              ("system calls", "the door into the kernel", "s f"),
              ("file system", "names, files and disk blocks", "s f"),
              ("disk driver", "asks the disk, sleeps until it answers", "s f"),
              ("the disk", "fs.img, inside QEMU", "s fs")]
    bx, bw, bh, step, top = 196, 248, 42, 74, 44
    for i, (name, sub, cls) in enumerate(layers):
        y = top + i * step
        f.rect(bx, y, bw, bh, cls, 6)
        f.text(bx + bw / 2, y + 18, name, "t", 14, "middle", 600, mono=(name == "ls"))
        f.text(bx + bw / 2, y + 34, sub, "tm", 11, "middle")
    down = ["read the directory", "a trap into the kernel", "which blocks hold it?", "read these blocks"]
    up = ["back in ls, with the names", "the entries, copied out", "the blocks, now in memory", "an interrupt: done"]
    dx, ux = bx + 70, bx + bw - 70
    for i in range(4):
        y1 = top + i * step + bh + 4
        y2 = top + (i + 1) * step - 4
        f.line(dx, y1, dx, y2, "s", arrow=True)
        f.line(ux, y2, ux, y1, "a", arrow=True)
        ym = (y1 + y2) / 2 + 4.5
        f.text(bx - 14, ym, down[i], "t", 12.5, "end")
        f.text(bx + bw + 14, ym, up[i], "ta", 12.5)
    f.text(bx - 14, 24, "the request goes down", "t", 12.5, "end", 600)
    f.text(bx + bw + 14, 24, "the answer comes back up", "ta", 12.5, None, 600)
    f.line(24, 400, 616, 400, "m")
    f.text(320, 422, "Then ls prints the names: write() goes down the same door, out the serial port to your terminal.", "tm", 12, "middle")
    return f


# ================================================================== 00.02

def f0002_loop():
    # The run/debug loop of lesson 00.02. The panic and the kernel.asm lines are from a real
    # run of the 07.03 build with pid = *(volatile int *)0x10; added to sys_kill after argint
    # (kernel/sysproc.c:82) and `kill 5` typed at the shell.
    f = Fig("f0002b", "The loop: edit, make qemu, read the console, quit, look up the address", 252)
    y1, h1, ym = 46, 46, 69
    boxes = [(24, 120, "edit", "kernel/*.c"), (176, 140, "make qemu", "build, then boot"),
             (348, 140, "console", "the kernel's UART"), (520, 96, "Control-a x", "QEMU quits")]
    for x, w, lab, sub in boxes:
        f.rect(x, y1, w, h1, "s f", 6)
        f.text(x + w / 2, y1 + h1 / 2 - 2, lab, "t", 12, "middle", 600, mono=lab == "make qemu")
        f.text(x + w / 2, y1 + h1 / 2 + 11.5, sub, "tm", 10.5, "middle", None, mono=sub.startswith("kernel/"))
    for (x, w, _, _), (nx, _, _, _) in zip(boxes, boxes[1:]):
        f.line(x + w + 2, ym, nx - 4, ym, "s", arrow=True)
    # round again
    f.path("M568 44 L568 26 L84 26 L84 42", "m", arrow=True)
    f.text(326, 20, "fix it, and go round again", "tm", 11, "middle")
    # when it dies: the panic
    y2, h2 = 140, 72
    f.line(418, y1 + h1 + 2, 418, y2 - 4, "a", arrow=True)
    f.text(428, 122, "when it dies", "ta", 11, weight=600)
    f.rect(348, y2, 268, h2, "a af", 6)
    cw = 10.5 * 0.6
    x0 = 360
    f.text(x0, y2 + 28, "scause=0xd ", "t", 10.5, mono=True)
    f.text(x0 + 11 * cw, y2 + 28, "sepc=0x80005020", "ta", 10.5, mono=True, weight=600)
    f.text(x0 + 27 * cw, y2 + 28, "stval=0x10", "t", 10.5, mono=True)
    f.text(x0, y2 + 50, "panic: kerneltrap", "t", 10.5, mono=True)
    # look it up
    f.rect(24, y2, 270, h2, "s fs", 6)
    f.text(36, y2 + 20, "build/kernel/kernel.asm", "tm", 10.5, mono=True)
    f.text(36, y2 + 41, "pid = *(volatile int *)0x10;", "t", 11, mono=True, weight=600)
    f.text(36, y2 + 60, "80005020:", "ta", 11, mono=True, weight=600)
    f.text(36 + 11 * 0.6 * 10, y2 + 60, "lw  a0,16(zero)", "t", 11, mono=True)
    f.line(346, y2 + 40, 298, y2 + 40, "a", arrow=True)
    f.text(321, y2 + 32, "look up", "ta", 10.5, "middle")
    f.line(84, y2 - 2, 84, y1 + h1 + 4, "s", arrow=True)
    f.text(94, 122, "the line to fix", "t", 11)
    f.text(24, 240, "Also on the console: Control-P lists the processes, Control-a c opens QEMU's monitor.", "tm", 11)
    return f


# ================================================================== 01.01

def stack_strip(a, x0, sw, y, h, labels):
    for i in range(8):
        x = x0 + i * sw
        lab = labels[i]
        rect(a, x, y, sw, h, "s f" if lab else "m fs")
        if lab:
            a.text(x + sw / 2, y + 20, lab, "t", 11.5, "middle", 600)
            a.line(x + sw - 8, y + 34, x + 10, y + 34, "s", arrow=True)
        else:
            a.text(x + sw / 2, y + 27, "unused", "tm", 10.5, "middle")


def f0101_slices():
    # stack0 = 0x80001000 in the 01.01 build (kernel.sym), right after the one page of .text;
    # char stack0[4096 * NCPU], NCPU = 8; -smp 3. So sp = 0x80002000, 0x80003000, 0x80004000.
    a = Art("f0101a", "stack0, one 4096-byte slice per hart", 222)
    x0, sw, y, h = 64, 64, 92, 48
    stack_strip(a, x0, sw, y, h, ["hart 0", "hart 1", "hart 2", "", "", "", "", ""])
    a.text(24, 42, "sp", "ta", 12, mono=True, weight=600)
    for k in (1, 2, 3):
        x = x0 + k * sw
        a.text(x, 42, f"hart {k - 1}", "ta", 11.5, "middle", 600)
        a.line(x, 50, x, y - 3, "a", arrow=True)
    for k, row in ((0, 0), (1, 1), (2, 0), (3, 1), (8, 0)):
        x = x0 + k * sw
        a.line(x, y + h, x, y + h + 8 + row * 16, "m")
        anchor = "start" if k == 0 else ("end" if k == 8 else "middle")
        a.text(x, y + h + 20 + row * 16, f"0x{0x80001000 + k * 0x1000:08x}", "tm", 10.5, anchor, mono=True)
    a.text(x0 - 6, y + 30, "low", "tm", 11, "end")
    a.text(x0 + 8 * sw + 6, y + 30, "high", "tm", 11)
    a.text(24, 210, "stack0 = 8 slices of 4096 bytes (NCPU = 8); this machine has 3 harts", "tm", 11.5)
    return a


def f0101_break():
    # Without "addi a1, a1, 1": sp = stack0 + N * 4096. In the 01.01 build stack0 is
    # 0x80001000 and the page below it, from 0x80000000, is .text: _entry and spin.
    a = Art("f0101b", "Without the + 1, every hart's stack moves down one slice", 214)
    x0, sw, y, h = 176, 55, 92, 48
    stack_strip(a, x0, sw, y, h, ["hart 1", "hart 2", "", "", "", "", "", ""])
    # what the linker put below stack0: the page of code
    rect(a, 24, y, x0 - 24, h, "s fs")
    a.text(64, y + 21, "kernel code", "t", 11.5, "middle")
    a.text(64, y + 37, ".text", "tm", 10.5, "middle", mono=True)
    a.add(f'<rect class="af" x="{x0 - 64}" y="{y + 1}" width="63" height="{h - 2}"/>')
    a.line(x0 - 6, y + 40, x0 - 56, y + 40, "a", arrow=True)
    a.text(x0 - 32, y + 22, "hart 0", "ta", 10.5, "middle", 600)
    a.text(24, 42, "sp", "t", 12, mono=True, weight=600)
    for k in (0, 1, 2):
        x = x0 + k * sw
        cls = "a" if k == 0 else "s"
        a.text(x, 42, f"hart {k}", "ta" if k == 0 else "t", 11.5, "middle", 600)
        a.line(x, 50, x, y - 3, cls, arrow=True)
    a.line(x0, y + h, x0, y + h + 8, "m")
    a.text(x0, y + h + 20, "stack0 = 0x80001000", "tm", 10.5, "middle", mono=True)
    a.line(24, y + h, 24, y + h + 8, "m")
    a.text(24, y + h + 20, "0x80000000", "tm", 10.5, mono=True)
    a.text(24, 196, "hart 0 starts at the bottom of stack0, and its calls write down", "ta", 11.5)
    a.text(24, 212, "into the page of kernel code below it", "ta", 11.5)
    return a


# ================================================================== 01.02

def f0102_mret():
    # MSTATUS_MPP_MASK (3L << 11), MSTATUS_MPP_S (1L << 11); main = 0x80000020 in the 01.02
    # build (kernel.sym), the mepc that info registers shows.
    a = Art("f0102a", "mret takes the mode from mstatus.MPP and the pc from mepc", 226)
    a.add('<rect class="fs" x="12" y="12" width="436" height="202" rx="12"/>')
    a.add('<rect class="af" x="456" y="12" width="172" height="202" rx="12"/>')
    a.text(28, 34, "machine mode, in start()", "tm", 11)
    a.text(472, 34, "supervisor mode", "ta", 11, weight=600)
    # mstatus bits
    a.text(28, 86, "mstatus", "t", 12.5, mono=True, weight=600)
    cells = [(104, 70, "63 .. 13", "...", "s f"), (174, 36, "12", "0", "s f"), (210, 36, "11", "1", "s f"),
             (246, 70, "10 .. 0", "...", "s f")]
    for x, w, bits, val, cls in cells:
        rect(a, x, 66, w, 30, cls)
        a.text(x + w / 2, 60, bits, "tm", 10, "middle", mono=True)
        a.text(x + w / 2, 86, val, "t" if val != "..." else "tm", 13, "middle", 600 if val != "..." else None, mono=True)
    a.path("M174 104 V110 H246 V104", "s")
    a.text(210, 126, "MPP = 01: S", "t", 11.5, "middle", 600, mono=True)
    a.text(210, 142, "11 = M, 01 = S, 00 = U", "tm", 10.5, "middle", mono=True)
    # mepc
    a.text(28, 186, "mepc", "t", 12.5, mono=True, weight=600)
    rect(a, 104, 166, 212, 30, "s f")
    a.text(116, 186, "main = 0x80000020", "t", 12, mono=True)
    # mret
    rect(a, 360, 110, 68, 30, "a f", rx=15)
    a.text(394, 130, "mret", "ta", 13, "middle", 700, mono=True)
    a.path("M316 81 C 340 81, 340 118, 358 120", "a", arrow=True)
    a.path("M316 181 C 340 181, 340 134, 358 132", "a", arrow=True)
    a.line(428, 125, 470, 125, "a", arrow=True)
    a.text(478, 112, "mode = S", "t", 12.5, mono=True, weight=600)
    a.text(478, 134, "pc = main", "t", 12.5, mono=True, weight=600)
    a.text(478, 166, "main() runs here,", "tm", 11)
    a.text(478, 182, "on stack0, paging off", "tm", 11)
    return a


def f0102_pmp():
    # pmpcfg0 = 0xf: pmp0cfg = R W X + A=01 (TOR); pmpaddr0 = 0x3fffffffffffff, << 2 = 0xfffffffffffffc.
    a = Art("f0102b", "PMP entry 0: top of range, from 0 up to pmpaddr0 << 2", 222)
    a.text(24, 64, "pmpcfg0", "t", 12.5, mono=True, weight=600)
    a.text(24, 80, "bits 7..0", "tm", 10.5)
    x0, cw = 136, 40
    names = ["L", "", "", "A", "A", "X", "W", "R"]
    vals = ["0", "0", "0", "0", "1", "1", "1", "1"]
    for i in range(8):
        x = x0 + i * cw
        rect(a, x, 46, cw, 30, "s f")
        a.text(x + cw / 2, 40, str(7 - i), "tm", 10, "middle", mono=True)
        a.text(x + cw / 2, 66, vals[i], "t", 13, "middle", 600, mono=True)
        if names[i] and names[i] != "A":
            a.text(x + cw / 2, 94, names[i], "t", 11.5, "middle", 600, mono=True)
    a.path(f"M{x0 + 3 * cw + 4} 84 V88 H{x0 + 5 * cw - 4} V84", "s")
    a.text(x0 + 4 * cw, 104, "A = 01: TOR", "t", 11, "middle", 600, mono=True)
    a.text(x0 + 6.5 * cw, 112, "X W R = 0x7", "tm", 10.5, "middle", mono=True)
    a.text(x0 + 8 * cw + 14, 66, "= 0xf", "t", 13, mono=True, weight=600)
    # pmpaddr0
    a.text(24, 150, "pmpaddr0", "t", 12.5, mono=True, weight=600)
    rect(a, 136, 131, 160, 28, "s f")
    a.text(216, 150, "0x3fffffffffffff", "t", 12, "middle", mono=True)
    a.text(308, 150, "<< 2  =  0xfffffffffffffc", "tm", 11.5, mono=True)
    # range
    a.text(24, 196, "entry 0", "t", 12, weight=600)
    rect(a, 136, 180, 480, 24, "a af", rx=4)
    a.text(376, 197, "S-mode may read, write and execute every address", "ta", 11.5, "middle", 600)
    a.text(136, 218, "0", "tm", 10.5, mono=True)
    a.text(616, 218, "0xfffffffffffffc", "tm", 10.5, "end", mono=True)
    return a


# ================================================================== 01.03

def f0103_uart():
    # kernel/uart.c: RHR/THR 0, IER 1, ISR/FCR 2, LCR 3, LSR 5; LSR_TX_IDLE (1<<5), LSR_RX_READY (1<<0);
    # IER_TX_ENABLE (1<<1), IER_RX_ENABLE (1<<0); LCR_BAUD_LATCH (1<<7). 4, 6, 7 are not used.
    a = Art("f0103a", "The 16550 UART: eight one-byte registers at UART0", 300)
    rows = [("RHR / THR", "read: the next byte in. write: the next byte out", True),
            ("IER", "interrupt enable: bit 1 TX, bit 0 RX", True),
            ("ISR / FCR", "read: interrupt status. write: FIFO control", True),
            ("LCR", "line control: 8 data bits; bit 7 = baud latch", True),
            ("MCR", "not used by this kernel", False),
            ("LSR", "line status: bit 5 TX_IDLE, bit 0 RX_READY", True),
            ("MSR", "not used by this kernel", False),
            ("SPR", "not used by this kernel", False)]
    y0, rh = 22, 30
    for i, (name, what, used) in enumerate(rows):
        y = y0 + i * rh
        a.text(24, y + 19, f"0x1000000{i}", "tm" if not used else "t", 11.5, mono=True)
        rect(a, 150, y + 2, 130, rh - 4, "s f" if used else "m fs", rx=4)
        a.text(215, y + 19, name, "t" if used else "tm", 12, "middle", 600 if used else None, mono=True)
        a.text(296, y + 19, what, "t" if used else "tm", 11.5)
    # the polling loop: LSR -> THR
    ly, ty = y0 + 5 * rh + rh / 2, y0 + rh / 2
    a.path(f"M148 {ly} H126 Q118 {ly} 118 {ly - 8} V{ty + 8} Q118 {ty} 126 {ty} H146", "a", arrow=True)
    a.text(24, 278, "uartputc_sync: wait until LSR says TX_IDLE, then store the byte to THR", "ta", 11.5, weight=600)
    a.text(24, 294, "UART0 = 0x10000000; register r is the byte at UART0 + r", "tm", 11)
    return a


def f0103_printint():
    # printint(1024, 10, 0): buf = '4' '2' '0' '1', i = 4; while(--i >= 0) prints buf[3] .. buf[0].
    a = Art("f0103b", "printint collects digits lowest first and prints them backwards", 252)
    xs = [100 + i * 84 for i in range(4)]
    steps = [(1024, 4), (102, 2), (10, 0), (1, 1)]
    a.text(24, 40, "x", "tm", 11.5, mono=True)
    a.text(24, 58, "x % 10", "tm", 11.5, mono=True)
    a.text(24, 112, "buf", "t", 12.5, mono=True, weight=600)
    a.text(24, 222, "printed", "t", 12, weight=600)
    for i, (x, (v, d)) in enumerate(zip(xs, steps)):
        cx = x + 42
        a.text(cx, 40, str(v), "tm", 11.5, "middle", mono=True)
        a.text(cx, 58, str(d), "t", 12, "middle", 600, mono=True)
        a.line(cx, 66, cx, 86, "s", arrow=True)
        rect(a, x, 88, 84, 36, "s f")
        a.text(cx, 112, f"'{d}'", "t", 15, "middle", 600, mono=True)
        a.text(cx, 140, f"buf[{i}]", "tm", 10.5, "middle", mono=True)
    rect(a, 436, 88, 104, 36, "m fs")
    a.text(488, 104, "buf[4..23]", "tm", 10.5, "middle", mono=True)
    a.text(488, 118, "unused", "tm", 10.5, "middle")
    a.text(552, 40, "x /= 10", "tm", 11, mono=True)
    a.text(552, 58, "until 0", "tm", 11)
    # crossing lines: buf[3-i] -> output position i
    for i in range(4):
        src = xs[3 - i] + 42
        dst = xs[i] + 42
        a.line(src, 146, dst, 196, "a", arrow=True)
    for i, ch in enumerate("1024"):
        rect(a, xs[i], 200, 84, 34, "s f")
        a.text(xs[i] + 42, 223, ch, "t", 15, "middle", 600, mono=True)
    a.text(452, 214, "i = 3, 2, 1, 0", "ta", 11, mono=True)
    a.text(452, 230, "while(--i >= 0)", "tm", 11, mono=True)
    return a


# ================================================================== 02.01

def f0201_phys():
    # memlayout.h + info mtree; etext and end from kernel.ld: in the 02.01 build .text is one
    # page, so etext is 0x80001000; PHYSTOP 0x88000000.
    a = Art("f0201a", "The physical address space of QEMU virt, as this kernel uses it", 346)
    bx, bw = 250, 150
    # dashed outline of the whole space, 0 to PHYSTOP
    rect(a, bx, 26, bw, 298, "m", dash=True)

    def seg(y, h, cls, name, note, addr, addr_y=None, dash=False):
        rect(a, bx, y, bw, h, cls, dash=dash)
        if name:
            rich(a, 414, y + h / 2 + 4, [(name, None, False), ("  " + note, "tm", True)] if note else [(name, None, False)],
                 size=12, cls="t" if "a" not in cls.split()[0] else "ta")
        if addr:
            a.text(238, (addr_y if addr_y is not None else y + h) - 1, addr, "tm", 11, "end", mono=True)

    seg(26, 72, "a af", "free pages", "", "PHYSTOP 0x88000000", 37)
    a.text(325, 58, "kalloc hands", "ta", 11.5, "middle")
    a.text(325, 74, "these out", "ta", 11.5, "middle")
    seg(98, 24, "s f", "kernel data, bss", "R W", "end", 102)
    seg(122, 24, "s fs", "kernel text", "R X", "etext 0x80001000", 126)
    a.text(238, 150, "KERNBASE 0x80000000", "tm", 11, "end", mono=True)
    a.text(325, 186, "unused", "tm", 11, "middle")
    seg(204, 14, "s f", "virtio disk", "VIRTIO0, IRQ 1", "0x10001000")
    seg(218, 14, "s f", "UART", "UART0, IRQ 10", "0x10000000")
    seg(244, 22, "s f", "PLIC", "PLIC, 6 MB", "0x0c000000")
    seg(280, 12, "m fs", "CLINT", "not used", "0x02000000", dash=True)
    seg(304, 10, "s fs", "boot ROM", "QEMU's", "0x00001000")
    a.text(238, 334, "0", "tm", 11, "end", mono=True)
    # brackets
    for y1, y2, l1, l2 in ((26, 146, "RAM", "128 MB"), (204, 314, "devices", "")):
        a.path(f"M70 {y1 + 2} H64 V{y2 - 2} H70", "m")
        a.text(56, (y1 + y2) / 2 + (0 if l2 else 4), l1, "t", 12, "end", 600)
        if l2:
            a.text(56, (y1 + y2) / 2 + 16, l2, "tm", 11, "end", mono=True)
    a.text(616, 340, "not to scale", "tm", 10.5, "end")
    return a


def f0201_vtop():
    # MAXVA 0x4000000000; TRAMPOLINE 0x3ffffff000; TRAPFRAME 0x3fffffe000;
    # KSTACK(p) = TRAMPOLINE - (p+1)*2*PGSIZE: 0x3fffffd000, 0x3fffffb000, ..., KSTACK(63) 0x3ffff7f000.
    a = Art("f0201b", "The top of the virtual address space, page by page", 318)
    kx, ux, cw = 236, 440, 176
    a.text(kx + cw / 2, 22, "the kernel's page table", "t", 12, "middle", 600)
    a.text(ux + cw / 2, 22, "a process's page table", "t", 12, "middle", 600)
    a.text(224, 36, "MAXVA 0x4000000000", "tm", 10.5, "end", mono=True)
    a.line(kx, 32, ux + cw, 32, "m")
    rows = [("TRAMPOLINE", "0x3ffffff000", ("trampoline", "s fs"), ("trampoline", "s fs")),
            ("TRAPFRAME", "0x3fffffe000", ("unmapped", "m"), ("trapframe", "s f")),
            ("KSTACK(0)", "0x3fffffd000", ("kernel stack, proc[0]", "s f"), None),
            ("", "0x3fffffc000", ("guard page, unmapped", "a af"), None),
            ("KSTACK(1)", "0x3fffffb000", ("kernel stack, proc[1]", "s f"), None),
            ("", "0x3fffffa000", ("guard page, unmapped", "m"), None)]
    y, rh = 32, 28
    for name, addr, kern, user in rows:
        rich(a, 224, y + 18, [(name + "  ", None, True), (addr, "tm", True)] if name else [(addr, "tm", True)],
             size=10.5, anchor="end", cls="t", mono=True)
        lab, cls = kern
        rect(a, kx, y, cw, rh, cls, dash=cls == "m")
        a.text(kx + cw / 2, y + 18, lab, "ta" if cls.startswith("a") else ("tm" if cls == "m" else "t"), 11.5, "middle",
               600 if cls.startswith("a") else None, mono=lab in ("trampoline", "trapframe"))
        if user:
            lab, cls = user
            rect(a, ux, y, cw, rh, cls)
            a.text(ux + cw / 2, y + 18, lab, "t", 11.5, "middle", mono=True)
        y += rh
    # gap, then the last stack
    a.text(kx + cw / 2, y + 24, "...", "tm", 14, "middle")
    a.text(224, y + 24, "62 more stacks", "tm", 10.5, "end")
    y += 40
    for name, addr, lab, cls in (("KSTACK(63)", "0x3ffff7f000", "kernel stack, proc[63]", "s f"),
                                 ("", "0x3ffff7e000", "guard page, unmapped", "m")):
        rich(a, 224, y + 18, [(name + "  ", None, True), (addr, "tm", True)] if name else [(addr, "tm", True)],
             size=10.5, anchor="end", cls="t", mono=True)
        rect(a, kx, y, cw, rh, cls, dash=cls == "m")
        a.text(kx + cw / 2, y + 18, lab, "tm" if cls == "m" else "t", 11.5, "middle")
        y += rh
    # user side below the trapframe
    rect(a, ux, 32 + 2 * rh, cw, y - (32 + 2 * rh), "m", dash=True)
    a.text(ux + cw / 2, 32 + 2 * rh + 30, "unused, down to", "tm", 11.5, "middle")
    a.text(ux + cw / 2, 32 + 2 * rh + 46, "the top of the heap", "tm", 11.5, "middle")
    a.text(224, 306, "one page per row: 4096 bytes", "tm", 10.5, "end")
    return a


# ================================================================== 02.02

def page(a, x, y, addr, nxt, fill="01", cls="s f", label_cls="t", dash=False, whole=False):
    w = 92
    a.text(x + w / 2, y - 8, addr, label_cls, 10.5 if len(addr) > 10 else 11.5, "middle", 600, mono=True)
    if whole:
        rect(a, x, y, w, 64, cls, dash=dash)
        a.text(x + w / 2, y + 28, f"{fill} {fill} {fill} {fill}", "ta" if cls.startswith("a") else "tm", 10.5, "middle", mono=True)
        a.text(x + w / 2, y + 44, f"{fill} {fill} {fill} {fill}", "ta" if cls.startswith("a") else "tm", 10.5, "middle", mono=True)
        return
    rect(a, x, y, w, 64, "s fs" if not dash else "m", dash=dash)
    rect(a, x, y, w, 22, cls, dash=dash)
    a.text(x + w / 2, y + 15, nxt, "t" if not dash else "tm", 10.5, "middle", mono=True)
    a.text(x + w / 2, y + 47, f"{fill} {fill} {fill} {fill}", "tm", 10.5, "middle", mono=True)


def freelist_box(a, y):
    rect(a, 24, y, 100, 22, "s fs", rx=4)
    a.text(74, y + 15, "kmem.freelist", "t", 10.5, "middle", 600, mono=True)


def f0202_list():
    # freerange frees ascending and kfree pushes at the head, so the head is 0x87fff000 and the
    # tail PGROUNDUP(end) (0x80153000 in the reference build).
    a = Art("f0202a", "The free list lives inside the free pages", 312)
    cols = [146, 264, 382, 520]
    a.text(24, 30, "after kinit()", "t", 12, weight=600)
    y = 68
    freelist_box(a, y)
    a.line(124, y + 11, 144, y + 11, "s", arrow=True)
    for x, addr, nxt in ((146, "0x87fff000", "0x87ffe000"), (264, "0x87ffe000", "0x87ffd000"),
                         (382, "0x87ffd000", "0x87ffc000"), (520, "PGROUNDUP(end)", "0")):
        page(a, x, y, addr, nxt)
    a.line(238, y + 11, 262, y + 11, "s", arrow=True)
    a.line(356, y + 11, 380, y + 11, "s", arrow=True)
    a.line(474, y + 11, 486, y + 11, "s")
    a.text(497, y + 15, "...", "tm", 12, "middle")
    a.line(508, y + 11, 518, y + 11, "s", arrow=True)
    a.text(74, y + 42, "next pointer", "tm", 10.5, "middle")
    a.text(74, y + 56, "in the first 8 bytes", "tm", 10.5, "middle")
    # after kalloc
    a.text(24, 168, "after one kalloc()", "t", 12, weight=600)
    y = 206
    freelist_box(a, y)
    page(a, 146, y, "0x87fff000", "", fill="05", cls="a af", label_cls="ta", whole=True)
    a.path(f"M74 {y + 22} V294 Q74 302 82 302 H302 Q310 302 310 294 V{y + 66}", "s", arrow=True)
    for x, addr, nxt in ((264, "0x87ffe000", "0x87ffd000"), (382, "0x87ffd000", "0x87ffc000"), (520, "PGROUNDUP(end)", "0")):
        page(a, x, y, addr, nxt)
    a.line(356, y + 11, 380, y + 11, "s", arrow=True)
    a.line(474, y + 11, 486, y + 11, "s")
    a.text(497, y + 15, "...", "tm", 12, "middle")
    a.line(508, y + 11, 518, y + 11, "s", arrow=True)
    a.text(192, y + 82, "returned, filled with 5s", "ta", 11, "middle")
    return a


def f0202_break():
    a = Art("f0202b", "With r->next = 0, the list keeps only the last page freed", 188)
    a.text(24, 30, "after kinit(), with r->next = 0", "t", 12, weight=600)
    y = 68
    freelist_box(a, y)
    a.line(124, y + 11, 144, y + 11, "s", arrow=True)
    page(a, 146, y, "0x87fff000", "0")
    for x, addr in ((264, "0x87ffe000"), (382, "0x87ffd000"), (520, "PGROUNDUP(end)")):
        page(a, x, y, addr, "0", dash=True, label_cls="tm")
    a.text(497, y + 36, "...", "tm", 12, "middle")
    a.path(f"M264 {y + 76} V{y + 82} H612 V{y + 76}", "a")
    a.text(438, y + 100, "still free, but nothing points to them", "ta", 11.5, "middle", 600)
    return a


# ================================================================== 02.03

def pill(a, x, y, w, s, cls="s f", tcls="t", h=20):
    rect(a, x, y, w, h, cls, rx=6)
    a.text(x + w / 2, y + h / 2 + 4, s, tcls, 11, "middle", mono=True)


def f0203_race():
    a = Art("f0203a", "x = x + 1 on two harts, without and with a lock", 336)
    a.add('<rect class="fs" x="12" y="12" width="300" height="312" rx="12"/>')
    a.add('<rect class="fs" x="328" y="12" width="300" height="312" rx="12"/>')
    a.text(28, 36, "no lock", "t", 12.5, weight=600)
    a.text(344, 36, "with a spinlock", "t", 12.5, weight=600)
    # left
    h0, h1, w = 48, 182, 120
    a.text(h0 + w / 2, 60, "hart 0", "tm", 11, "middle")
    a.text(h1 + w / 2, 60, "hart 1", "tm", 11, "middle")
    left = [(0, "load x  -> 5", True), (1, "load x  -> 5", True), (0, "add     -> 6", False), (1, "add     -> 6", False),
            (0, "store 6", False), (1, "store 6", False)]
    for i, (hart, s, hot) in enumerate(left):
        y = 72 + i * 30
        pill(a, h0 if hart == 0 else h1, y, w, s, "a af" if hot else "s f", "ta" if hot else "t")
    a.line(30, 72, 30, 248, "m", arrow=True)
    a.text(30, 266, "time", "tm", 10.5, "middle")
    a.text(162, 296, "x = 6: one increment lost", "ta", 12, "middle", 600)
    a.text(162, 312, "both harts loaded 5", "tm", 11, "middle")
    # right
    g0, g1 = 344, 486
    a.text(g0 + w / 2, 60, "hart 0", "tm", 11, "middle")
    a.text(g1 + w / 2, 60, "hart 1", "tm", 11, "middle")
    rh = 21
    right0 = ["acquire", "load x  -> 5", "add     -> 6", "store 6", "release"]
    for i, s in enumerate(right0):
        pill(a, g0, 70 + i * rh, w, s, h=18)
    a.line(g1 + w / 2, 74, g1 + w / 2, 72 + 5 * rh - 4, "m", dash=True)
    rect(a, g1 + 30, 72 + 2 * rh - 2, 60, 20, "f", rx=4)
    a.text(g1 + w / 2, 72 + 2 * rh + 12, "spins", "tm", 11, "middle")
    right1 = ["acquire", "load x  -> 6", "add     -> 7", "store 7", "release"]
    for i, s in enumerate(right1):
        pill(a, g1, 70 + (5 + i) * rh, w, s, h=18)
    a.text(478, 296, "x = 7", "t", 12, "middle", 600, mono=True)
    a.text(478, 312, "the second load waits for the first store", "tm", 11, "middle")
    return a


def f0203_amoswap():
    # amoswap.w.aq a5,a5,(s1) with a5 = 1: writes 1, returns the old value.
    a = Art("f0203b", "amoswap: the memory does one swap at a time", 236)
    a.text(24, 54, "hart 0", "t", 12, weight=600)
    a.text(24, 190, "hart 1", "t", 12, weight=600)
    a.text(24, 125, "lk->locked", "t", 12, mono=True, weight=600)
    # memory value over time
    t1, t2 = 230, 430
    rect(a, 120, 106, t1 - 120, 30, "s f")
    rect(a, t1, 106, 616 - t1, 30, "s f")
    a.text((120 + t1) / 2, 126, "0", "t", 14, "middle", 600, mono=True)
    a.text((t1 + t2) / 2, 126, "1", "t", 14, "middle", 600, mono=True)
    a.text((t2 + 616) / 2, 126, "1", "t", 14, "middle", 600, mono=True)
    # hart 0 swap
    rect(a, t1 - 70, 38, 140, 26, "s f", rx=6)
    a.text(t1, 56, "amoswap  a5 = 1", "t", 11, "middle", mono=True)
    a.line(t1 - 8, 64, t1 - 8, 104, "s", arrow=True)
    a.line(t1 + 8, 106, t1 + 8, 70, "a", arrow=True)
    a.text(t1 + 16, 90, "old 0", "ta", 11, mono=True, weight=600)
    a.text(t1 + 76, 56, "-> lock taken", "ta", 11.5, weight=600)
    # hart 1 swap
    rect(a, t2 - 70, 174, 140, 26, "s f", rx=6)
    a.text(t2, 192, "amoswap  a5 = 1", "t", 11, "middle", mono=True)
    a.line(t2 - 8, 172, t2 - 8, 138, "s", arrow=True)
    a.line(t2 + 8, 138, t2 + 8, 172, "s", arrow=True)
    a.text(t2 + 16, 160, "old 1", "t", 11, mono=True, weight=600)
    a.text(t2 + 76, 192, "-> bnez: again", "t", 11.5)
    a.line(120, 222, 616, 222, "m", arrow=True)
    a.text(120, 216, "time", "tm", 10.5)
    return a


def f0203_nesting():
    # push_off: if noff == 0, intena = old; noff += 1.  pop_off: noff -= 1; if noff == 0 && intena, intr_on().
    a = Art("f0203c", "push_off and pop_off count: interrupts return at the last release", 236)
    xs = [176, 290, 404, 518]
    calls = [("acquire(&a)", "push_off"), ("acquire(&b)", "push_off"), ("release(&b)", "pop_off"), ("release(&a)", "pop_off")]
    for x, (c, p) in zip(xs, calls):
        a.text(x, 32, c, "t", 11.5, "middle", 600, mono=True)
        a.text(x, 48, p, "tm", 10.5, "middle", mono=True)
        a.line(x, 58, x, 204, "m", dash=True)
    lv = {0: 154, 1: 120, 2: 86}
    a.text(24, 90, "mycpu()->noff", "t", 11, mono=True, weight=600)
    for n, y in lv.items():
        a.text(130, y + 4, str(n), "tm", 11, "end", mono=True)
    a.path(f"M140 {lv[0]} H{xs[0]} V{lv[1]} H{xs[1]} V{lv[2]} H{xs[2]} V{lv[1]} H{xs[3]} V{lv[0]} H616", "s")
    a.text(xs[0] + 6, lv[1] - 8, "intena = 1", "tm", 10.5, mono=True)
    a.text(24, 197, "interrupts", "t", 11.5, weight=600)
    rect(a, 140, 184, xs[0] - 140, 20, "s f", rx=4)
    a.text((140 + xs[0]) / 2, 198, "on", "t", 11, "middle")
    rect(a, xs[0], 184, xs[3] - xs[0], 20, "s fs", rx=4)
    a.text((xs[0] + xs[3]) / 2, 198, "off", "tm", 11, "middle")
    rect(a, xs[3], 184, 616 - xs[3], 20, "a af", rx=4)
    a.text((xs[3] + 616) / 2, 198, "on", "ta", 11, "middle", 600)
    a.text((xs[3] + 616) / 2, 226, "intr_on()", "ta", 11, "middle", 600, mono=True)
    a.text(xs[1] + 57, 226, "still off: b was not the last", "tm", 11, "middle")
    return a


# ================================================================== 02.04

def f0204_pte():
    # riscv.h: PTE_V 0, R 1, W 2, X 3, U 4, A 6, D 7; PA2PTE(pa) = (pa >> 12) << 10; PTE_FLAGS & 0x3FF.
    a = Art("f0204a", "A PTE holds the page number from a physical address, and the flags", 252)
    lx, rsv0, ppn0, ppn1 = 24, 88, 142, 342
    fl0 = 390
    fw = (616 - fl0) / 8
    # physical address
    a.text(lx, 70, "pa", "t", 13, mono=True, weight=600)
    rect(a, rsv0, 50, ppn0 - rsv0, 30, "m", dash=True)
    a.text((rsv0 + ppn0) / 2, 70, "0", "tm", 11, "middle", mono=True)
    rect(a, ppn0, 50, ppn1 - ppn0, 30, "s f")
    a.text((ppn0 + ppn1) / 2, 70, "page number, 44 bits", "t", 12, "middle", 600)
    rect(a, ppn1, 50, 616 - ppn1, 30, "s fs")
    a.text((ppn1 + 616) / 2, 70, "offset: 0 for a page", "tm", 11.5, "middle")
    for x, s, anc in ((ppn0 + 3, "55", "start"), (ppn1 - 3, "12", "end"), (ppn1 + 3, "11", "start"), (613, "0", "end")):
        a.text(x, 44, s, "tm", 10, anc, mono=True)
    # the shift
    mid = (ppn0 + ppn1) / 2
    a.line(mid, 82, mid, 146, "a", arrow=True)
    a.text(mid + 10, 108, "PA2PTE(pa) = (pa >> 12) << 10", "ta", 11.5, mono=True, weight=600)
    a.text(mid + 10, 126, "PTE2PA undoes it", "tm", 11)
    # PTE
    a.text(lx, 170, "pte", "t", 13, mono=True, weight=600)
    rect(a, rsv0, 150, ppn0 - rsv0, 30, "m fs")
    a.text((rsv0 + ppn0) / 2, 170, "0", "tm", 11, "middle", mono=True)
    rect(a, ppn0, 150, ppn1 - ppn0, 30, "a af")
    a.text((ppn0 + ppn1) / 2, 170, "page number, 44 bits", "ta", 12, "middle", 600)
    rect(a, ppn1, 150, fl0 - ppn1, 30, "m fs")
    a.text((ppn1 + fl0) / 2, 170, "RSW", "tm", 10.5, "middle", mono=True)
    for x, s, anc in ((rsv0 + 3, "63", "start"), (ppn0 - 3, "54", "end"), (ppn0 + 3, "53", "start"), (ppn1 - 3, "10", "end"),
                      (ppn1 + 3, "9", "start"), (fl0 - 3, "8", "end")):
        a.text(x, 144, s, "tm", 10, anc, mono=True)
    flags = ["D", "A", "G", "U", "X", "W", "R", "V"]
    for i, f in enumerate(flags):
        x = fl0 + i * fw
        used = f != "G"
        rect(a, x, 150, fw, 30, "s f" if used else "m fs")
        a.text(x + fw / 2, 144, str(7 - i), "tm", 10, "middle", mono=True)
        a.text(x + fw / 2, 170, f, "t" if used else "tm", 12.5, "middle", 600 if used else None, mono=True)
    a.text(lx, 210, "V valid, R read, W write, X execute, U user, A accessed, D dirty", "t", 11.5)
    a.text(lx, 228, "V set with R, W and X all clear: the entry points at the next table, not at a page", "tm", 11.5)
    a.text(lx, 244, "G and RSW are not used by this kernel", "tm", 11)
    return a


def f0204_kvm():
    # kvmmake at 02.04: UART0, VIRTIO0 one page RW; PLIC 0x4000000 bytes RW; KERNBASE..etext RX;
    # etext..PHYSTOP RW. In the 02.04 build .text is one page, so etext = 0x80001000 (kernel.sym,
    # and info mem shows 0x80000000 r-x for 0x1000). The two mappings at the top come later:
    # proc_mapstacks (04.01) maps KSTACK(p) to kalloc'd pages, and 06.01 maps TRAMPOLINE to the
    # trampoline code inside the kernel's text.
    a = Art("f0204b", "The kernel's address space at 02.04: a direct map, with the top still empty", 344)
    vx, px, cw = 176, 432, 150
    a.text(vx + cw / 2, 20, "virtual", "t", 12, "middle", 600)
    a.text(px + cw / 2, 130, "physical", "t", 12, "middle", 600)

    def vbox(y, h, name, perm, cls="s f", dash=False):
        rect(a, vx, y, cw, h, cls, dash=dash)
        a.text(vx + 8, y + h / 2 + 4, name, "t" if cls != "m" else "tm", 11, mono=name in ("trampoline",))
        if perm:
            a.text(vx + cw - 8, y + h / 2 + 4, perm, "tm", 10.5, "end", mono=True)

    def addr(y, s):
        a.text(vx - 10, y, s, "tm", 10.5, "end", mono=True)

    # high part: nothing mapped yet; two places reserved for later lessons
    vbox(30, 24, "trampoline", "06.01", "m", dash=True)
    addr(46, "TRAMPOLINE 0x3ffffff000")
    vbox(62, 30, "kernel stacks", "04.01", "m", dash=True)
    addr(80, "KSTACK(0) .. KSTACK(63)")
    vbox(100, 20, "unmapped", "", "m", dash=True)
    a.text(vx + cw + 16, 46, "not mapped yet: both come later,", "tm", 11)
    a.text(vx + cw + 16, 62, "and neither will be at its own address", "tm", 11)
    # RAM
    for x in (vx, px):
        rect(a, x, 140, cw, 52, "s f")
        rect(a, x, 192, cw, 40, "s fs")
    a.text(vx + 8, 170, "data, free RAM", "t", 11)
    a.text(vx + cw - 8, 170, "R W", "tm", 10.5, "end", mono=True)
    a.text(vx + 8, 216, "kernel text", "t", 11)
    a.text(vx + cw - 8, 216, "R X", "tm", 10.5, "end", mono=True)
    a.text(px + 8, 170, "data, free RAM", "t", 11)
    a.text(px + 8, 216, "kernel text", "t", 11)
    addr(150, "PHYSTOP 0x88000000")
    addr(196, "etext 0x80001000")
    addr(236, "KERNBASE 0x80000000")
    # devices
    for x in (vx, px):
        for y, h in ((252, 16), (268, 16), (284, 30)):
            rect(a, x, y, cw, h, "s f")
    for y, h, name in ((252, 16, "VIRTIO0"), (268, 16, "UART0"), (284, 30, "PLIC, 64 MB")):
        a.text(vx + 8, y + h / 2 + 4, name, "t", 11, mono=name != "PLIC, 64 MB")
        a.text(vx + cw - 8, y + h / 2 + 4, "R W", "tm", 10.5, "end", mono=True)
        a.text(px + 8, y + h / 2 + 4, name, "t", 11, mono=name != "PLIC, 64 MB")
    addr(266, "0x10001000")
    addr(282, "0x10000000")
    addr(312, "0x0c000000")
    # identity arrows
    for y in (166, 212, 260, 276, 299):
        a.line(vx + cw + 2, y, px - 4, y, "m", arrow=True)
    a.text((vx + cw + px) / 2, 330, "same address on both sides", "tm", 11, "middle")
    return a


FIGS = {
    "00.01-kernel-image": f0001_image, "00.01-mcmodel-reach": f0001_medany, "00.01-ls-trip": f0001_trip,
    "00.02-run-loop": f0002_loop,
    "01.01-stack0-slices": f0101_slices, "01.01-stack0-without-plus-one": f0101_break,
    "01.02-mret": f0102_mret, "01.02-pmp-entry-0": f0102_pmp,
    "01.03-uart-registers": f0103_uart, "01.03-printint-reverse": f0103_printint,
    "02.01-physical-map": f0201_phys, "02.01-virtual-top": f0201_vtop,
    "02.02-free-list": f0202_list, "02.02-lost-list": f0202_break,
    "02.03-race-and-lock": f0203_race, "02.03-amoswap": f0203_amoswap, "02.03-push-pop-nesting": f0203_nesting,
    "02.04-pte-bits": f0204_pte, "02.04-kernel-address-space": f0204_kvm,
}


def main():
    only = sys.argv[1:]
    for name, fn in FIGS.items():
        if only and not any(name.startswith(o) for o in only):
            continue
        d = os.path.join(LESSONS, MODDIR[name[:2]], "figures")
        os.makedirs(d, exist_ok=True)
        svg = fn().svg()
        svg.encode("ascii")
        with open(os.path.join(d, name + ".svg"), "w") as f:
            f.write(svg)
    print("ok")


if __name__ == "__main__":
    main()
