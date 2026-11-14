"""Inline lesson figures for xv6 module 09 (the GUI).

Writes tracks/xv6/lessons/09-gui/figures/09.LL-name.svg. The values are real: the
fw_cfg file directory was printed by a kernel built for the purpose (QEMU 10.2,
-device ramfb; checked again on the 09.01 build); the addresses of fb, cfg and req are
from the 09.01 build's build/kernel/kernel.sym (fb, cfg.1, req.0; the same through 09.05,
since module 09 builds on the core without module 08);
the event bytes are what the events program printed while QMP pressed keys and
moved the tablet; the glyph is font['a'] from user/font.c; the line's pixels are
what user/gui.c's line() plots.
"""
import os
import re

from figlib import Fig, write

MOD = "09-gui"
REPO = os.path.expanduser("~/Documents/WORK/misc/systems-from-scratch/tracks/xv6")

FB, CFG, REQ = 0x80013000, 0x80012000, 0x80012020
DIRECTORY = [(0x20, 0, "bios-geometry"), (0x21, 0, "bootorder"), (0x22, 36, "etc/acpi/rsdp"),
             (0x23, 131072, "etc/acpi/tables"), (0x24, 4, "etc/boot-fail-wait"), (0x25, 28, "etc/ramfb"),
             (0x26, 24, "etc/smbios/smbios-anchor"), (0x27, 287, "etc/smbios/smbios-tables"),
             (0x28, 2304, "etc/table-loader")]


def font():
    src = open(os.path.join(REPO, "user", "font.c")).read().split("font[95][8]", 1)[1]
    vals = [int(v, 16) for v in re.findall(r"0x([0-9a-f]{2})", src)]
    return [vals[i * 8:i * 8 + 8] for i in range(95)]


def bresenham(x0, y0, x1, y1):
    """The same steps as line() in user/gui.c."""
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err, out = dx + dy, []
    while True:
        out.append((x0, y0, err))
        if (x0, y0) == (x1, y1):
            return out
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def cell(f, x, y, w, h, top, val, cls="s f", acc=False, vsize=10.5):
    f.rect(x, y, w, h, cls, 0)
    f.text(x + w / 2, y + 14, top, "ta" if acc else "tm", 9.5, "middle")
    f.text(x + w / 2, y + 31, val, "ta" if acc else "t", vsize, "middle", 600 if acc else None, True)


# ================================================================== 09.01

def fwcfg():
    f = Fig("f0901a", "Finding etc/ramfb in fw_cfg, then writing it by DMA", 432)
    # the registers
    f.text(24, 20, "fw_cfg at 0x10100000", "t", 11.5, "start", 600, True)
    regs = [("+0", "data", "read the selected item, a byte at a time"),
            ("+8", "selector", "16 bits, big-endian: which item"),
            ("+16", "DMA", "64 bits, big-endian: where a request is")]
    for i, (off, name, what) in enumerate(regs):
        y = 32 + i * 28
        acc = name == "DMA"
        f.rect(24, y, 150, 22, "a af" if acc else "s f", 4)
        f.text(34, y + 15, off, "tm", 10, "start", None, True)
        f.text(70, y + 15, name, "ta" if acc else "t", 10.5, "start", 600, True)
        f.text(184, y + 15, what, "tm", 10)
    # step 1: the directory
    y0 = 136
    f.text(24, y0 - 10, "1. selector = 0x0019; read: the file directory", "t", 11, "start", 600)
    f.rect(24, y0, 290, 22, "s fs", 0)
    f.text(34, y0 + 15, "count", "tm", 10, "start")
    f.text(304, y0 + 15, "00 00 00 09 = 9 files", "t", 10.5, "end", None, True)
    for i, (sel, size, name) in enumerate(DIRECTORY):
        y = y0 + 22 + i * 21
        acc = name == "etc/ramfb"
        f.rect(24, y, 290, 21, "a af" if acc else "s f", 0)
        f.text(34, y + 14, f"{sel >> 8:02x} {sel & 0xff:02x}", "ta" if acc else "tm", 10, "start", 600 if acc else None, True)
        f.text(84, y + 14, name, "ta" if acc else "t", 10, "start", 600 if acc else None, True)
        f.text(304, y + 14, str(size), "ta" if acc else "tm", 10, "end", None, True)
    f.text(24, y0 + 22 + 9 * 21 + 16, "each entry: size, select, 2 bytes unused, a 56-byte name", "tm", 10)
    # step 2: the DMA
    x2 = 350
    f.text(x2, y0 - 10, "2. DMA = the address of req", "t", 11, "start", 600)
    f.text(x2, y0 + 8, f"req at {REQ:#x}", "tm", 10, "start", None, True)
    req = [("control", "00 25 00 18", "item 0x25: select, write"), ("length", "00 00 00 1c", "28 bytes"),
           ("address", f"{CFG:016x}"[8:], "cfg")]
    for i, (k, v, what) in enumerate(req):
        y = y0 + 16 + i * 26
        f.rect(x2, y, 266, 26, "s f", 0)
        f.text(x2 + 8, y + 17, k, "tm", 10, "start", None, True)
        f.text(x2 + 64, y + 17, v, "t", 10.5, "start", None, True)
        f.text(x2 + 258, y + 17, what, "tm", 9, "end")
    yc = y0 + 16 + 3 * 26 + 30
    f.path(f"M{x2 + 262} {y0 + 16 + 2 * 26 + 13} C {x2 + 290} {y0 + 16 + 2 * 26 + 30}, {x2 + 290} {yc - 20}, {x2 + 250} {yc - 2}", "s", arrow=True)
    f.text(x2, yc - 8, f"cfg at {CFG:#x}: what ramfb reads", "tm", 10, "start", None, True)
    cfg = [("addr", f"{FB:x}", "the first pixel: fb"), ("fourcc", "58 52 32 34", '"XR24"'), ("flags", "0", ""),
           ("width", "640", ""), ("height", "480", ""), ("stride", "2560", "bytes per row")]
    for i, (k, v, what) in enumerate(cfg):
        y = yc + i * 24
        acc = k == "addr"
        f.rect(x2, y, 266, 24, "a af" if acc else "s f", 0)
        f.text(x2 + 8, y + 16, k, "ta" if acc else "tm", 10, "start", None, True)
        f.text(x2 + 70, y + 16, v, "ta" if acc else "t", 10.5, "start", 600 if acc else None, True)
        f.text(x2 + 258, y + 16, what, "ta" if acc else "tm", 9.5, "end")
    f.text(x2, yc + 6 * 24 + 16, "all big-endian; fourcc is 0x34325258", "tm", 10)
    f.line(330, y0 - 22, 330, 424, "m", dash=True)
    return f


def pixel():
    f = Fig("f0901b", "The pixel format, and where pixel (x, y) is", 330)
    # a corner of the screen as a grid
    gx, gy, c = 40, 40, 26
    cols, rows = 9, 5
    f.text(24, 22, "the screen: 640 pixels a row, 480 rows", "t", 11, "start", 600)
    for r in range(rows):
        for k in range(cols):
            acc = (k, r) == (3, 2)
            f.rect(gx + k * c, gy + r * c, c, c, "a fa" if acc else "s f", 0)
    for k in range(cols):
        f.text(gx + k * c + c / 2, gy - 6, str(k) if k < cols - 1 else "...", "tm", 9, "middle", None, True)
    for r in range(rows):
        f.text(gx - 6, gy + r * c + c / 2 + 3, str(r) if r < rows - 1 else "...", "tm", 9, "end", None, True)
    f.text(gx + 3 * c + c / 2, gy + rows * c + 18, "(3, 2)", "ta", 10.5, "middle", 600, True)
    # the formula
    fx = 300
    f.text(fx, 50, "pixel (x, y) is the uint32 at", "t", 11)
    f.text(fx, 74, "fb + y * 2560 + x * 4", "ta", 13, "start", 600, True)
    f.text(fx, 96, "2560 = 640 pixels x 4 bytes: the stride", "tm", 10)
    f.text(fx, 124, "(3, 2): fb + 5120 + 12 = fb + 5132", "t", 10.5, "start", None, True)
    f.text(fx, 142, f"= {FB + 5132:#x}", "tm", 10.5, "start", None, True)
    # one pixel, four bytes
    y = 228
    f.text(24, y - 14, "one pixel in memory: red, 0x00ff0000 as a uint32", "t", 11, "start", 600)
    bytes_ = [("+0", "blue", "00"), ("+1", "green", "00"), ("+2", "red", "ff"), ("+3", "unused", "00")]
    for i, (off, name, val) in enumerate(bytes_):
        x = 24 + i * 76
        acc = name == "red"
        cell(f, x, y, 76, 44, name, val, "a af" if acc else ("m f" if name == "unused" else "s f"), acc)
        f.text(x + 3, y + 58, off, "tm", 9, "start", None, True)
    f.text(340, y + 16, "RISC-V is little-endian: the low byte", "tm", 10.5)
    f.text(340, y + 32, "comes first, so 0x00RRGGBB is stored", "tm", 10.5)
    f.text(340, y + 48, "as B, G, R, 0. DRM calls it XRGB8888.", "tm", 10.5)
    f.text(24, 318, "the whole screen: 640 * 480 * 4 = 1228800 bytes, exactly 300 pages", "tm", 10.5)
    return f


# ================================================================== 09.02

def mapping():
    f = Fig("f0902a", "Two processes, one screen", 346)
    W = 170
    colx = [(24, "colors (pid 3)", 194, 234), (446, "its child (pid 4)", 446, 406)]
    for x, title, edge, _ in colx:
        f.text(x, 20, title, "t", 11, "start", 600)
        boxes = [(30, 42, "TRAMPOLINE, TRAPFRAME", "s fs", "at the top: 0x3fffffe000"), (72, 24, "", "m f", ""),
                 (96, 64, "FBVA: the screen", "a af", "0x40000000, 300 pages"), (160, 46, "", "m f", ""),
                 (206, 84, "text, data, stack, heap", "s f", "0 to p->sz")]
        for y, h, label, cls, sub in boxes:
            f.rect(x, y, W, h, cls, 0, dash=cls == "m f")
            if label:
                acc = cls.startswith("a")
                f.text(x + 8, y + 18, label, "ta" if acc else "t", 10.5, "start", 600 if acc else None)
                f.text(x + 8, y + 33, sub, "ta" if acc else "tm", 9.5, "start", None, True)
        f.text(x + W / 2, 308, "uvmcopy, uvmfree: 0 to sz only", "tm", 9.5, "middle")
    px, pw = 236, 168
    f.text(px + pw / 2, 20, "physical memory", "t", 11, "middle", 600)
    f.rect(px, 30, pw, 40, "s fs", 0)
    f.text(px + 8, 54, "kernel text and data", "tm", 10)
    f.rect(px, 70, pw, 100, "a af", 0)
    f.text(px + 8, 90, "fb[], in the kernel's bss", "ta", 10.5, "start", 600)
    f.text(px + 8, 106, f"{FB:#x}", "ta", 10, "start", None, True)
    f.text(px + 8, 126, "below end: kalloc never", "ta", 10)
    f.text(px + 8, 140, "hands it out, and kfree", "ta", 10)
    f.text(px + 8, 154, "panics if given it", "ta", 10)
    f.rect(px, 170, pw, 90, "s f", 0)
    f.text(px + 8, 188, "end", "tm", 10, "start", None, True)
    f.text(px + 8, 206, "pages from kalloc: each", "tm", 10)
    f.text(px + 8, 220, "process's own memory, the", "tm", 10)
    f.text(px + 8, 234, "child's a copy of its parent's", "tm", 10)
    for x, title, edge, tip in colx:
        f.path(f"M{edge} 128 C {(edge + tip) / 2} 128, {(edge + tip) / 2} 118, {tip} 118", "a", arrow=True)
        f.path(f"M{edge} 248 C {(edge + tip) / 2} 248, {(edge + tip) / 2} 222, {tip} 222", "s", arrow=True)
    f.text(320, 290, "the same 300 pages,", "ta", 10.5, "middle", 600)
    f.text(320, 306, "mapped in both page tables", "ta", 10.5, "middle", 600)
    f.text(24, 336, "fork copies 0 to sz, so the child starts without the screen; its own fbmap() maps the same pages.", "tm", 10.5)
    return f


def teardown():
    f = Fig("f0902b", "What proc_freepagetable does with each kind of page", 252)
    steps = [("uvmunmap(TRAMPOLINE, 1, 0)", "the trampoline: shared by every process", "unmap"),
             ("uvmunmap(TRAPFRAME, 1, 0)", "the trapframe: freeproc frees it", "unmap"),
             ("fbunmap(pagetable)", "the screen, if mapped: fb[] is the kernel's", "unmap"),
             ("uvmfree(pagetable, sz)", "0 to sz: this process's own pages", "unmap and kfree"),
             ("then, inside uvmfree: freewalk", "the page-table pages; panics at any leaf left", "kfree")]
    for i, (call, what, act) in enumerate(steps):
        y = 24 + i * 40
        acc = call.startswith("fbunmap")
        f.rect(24, y, 592, 32, "a af" if acc else "s f", 6)
        f.text(36, y + 20, call.strip(), "ta" if acc else "t", 10.5, "start", 600, True)
        f.text(250, y + 20, what, "ta" if acc else "tm", 10.5)
        f.text(604, y + 20, act, "ta" if acc else "t", 10.5, "end", 600)
    f.text(24, 242, "on exit, and on exec for the old page table. Without fbunmap: panic: freewalk: leaf", "tm", 10.5)
    return f


# ================================================================== 09.03

def keypath():
    f = Fig("f0903a", "From a key press to a struct inputevent", 360)
    lx, w, h = 24, 270, 38
    steps = [("a key goes down in the window", "QEMU's virtio-keyboard-device", "s fs"),
             ("the device writes 8 bytes into ev[i]", "a buffer the driver gave it ahead", "s f"),
             ("used ring: i; interrupt 3", "the PLIC picks a hart", "s f"),
             ("virtio_input_intr(3)", "copies the event to input.q, gives", "a af"),
             ("", "ev[i] back, wakeup(&input.r)", None)]
    y = 24
    for i, (a, b, cls) in enumerate(steps[:4]):
        f.rect(lx, y, w, h + (14 if i == 3 else 0), cls, 6)
        acc = cls.startswith("a")
        f.text(lx + 10, y + 16, a, "ta" if acc else "t", 10.5, "start", 600, acc)
        f.text(lx + 10, y + 31, b, "ta" if acc else "tm", 9.5)
        if i == 3:
            f.text(lx + 10, y + 45, steps[4][1], "ta", 9.5)
        if i < 3:
            f.line(lx + w / 2, y + h, lx + w / 2, y + h + 14, "s", arrow=True)
        y += h + 16
    # the process side
    rx = 346
    f.text(rx, 20, "events, meanwhile", "t", 11, "start", 600)
    ps = [("read(fd, ev, 128)", "user space", "s fs"), ("fileread: FD_DEVICE", "devsw[INPUT].read", "s f"),
          ("inputread", "sleeps on &input.r", "a af")]
    y = 28
    for i, (a, b, cls) in enumerate(ps):
        f.rect(rx, y, w, h, cls, 6)
        acc = cls.startswith("a")
        f.text(rx + 10, y + 16, a, "ta" if acc else "t", 10.5, "start", 600, True)
        f.text(rx + 10, y + 31, b, "ta" if acc else "tm", 9.5)
        if i < 2:
            f.line(rx + w / 2, y + h, rx + w / 2, y + h + 14, "s", arrow=True)
        y += h + 16
    f.path(f"M{lx + w} {24 + 3 * 54 + 26} C {lx + w + 30} {24 + 3 * 54 + 26}, {rx - 30} {28 + 2 * 54 + 30}, {rx - 2} {28 + 2 * 54 + 30}",
           "a", arrow=True)
    f.text(322, 156, "wakeup", "ta", 10, "middle", 600)
    y = 28 + 3 * 54
    f.rect(rx, y, w, 52, "s f", 6)
    f.text(rx + 10, y + 16, "it wakes: copyout of every", "t", 10.5)
    f.text(rx + 10, y + 31, "whole event waiting, oldest first", "t", 10.5)
    f.text(rx + 10, y + 45, "a key going down: read returns 16", "tm", 9.5)
    f.line(rx + w / 2, y - 16, rx + w / 2, y - 2, "s", arrow=True)
    f.line(24, 286, 616, 286, "m", dash=True)
    f.text(24, 306, "The mouse takes the same path on interrupt 4: a tablet at slot 3 whose positions run 0 to", "tm", 10.5)
    f.text(24, 322, "32767; the driver turns them into pixels. Both devices feed the one queue, input.q, of 64", "tm", 10.5)
    f.text(24, 338, "events: when it is full, new events are dropped until someone reads.", "tm", 10.5)
    return f


def groups():
    f = Fig("f0903b", "Events come in groups, each ended by EV_SYN", 300)
    f.text(24, 20, "one event: 8 bytes", "t", 11, "start", 600)
    cell(f, 24, 30, 120, 44, "type, 2 bytes", "u16", "s f")
    cell(f, 144, 30, 120, 44, "code, 2 bytes", "u16", "s f")
    cell(f, 264, 30, 240, 44, "value, 4 bytes", "s32", "s f")
    f.text(514, 50, "little-endian,", "tm", 10)
    f.text(514, 64, "as the device wrote it", "tm", 10)
    rows = [("the a key goes down", [("EV_KEY", "30", "1"), ("EV_SYN", "0", "0")]),
            ("and comes up", [("EV_KEY", "30", "0"), ("EV_SYN", "0", "0")]),
            ("the pointer moves to (100, 200)", [("EV_ABS", "ABS_X", "100"), ("EV_ABS", "ABS_Y", "200"), ("EV_SYN", "0", "0")]),
            ("the left button goes down", [("EV_KEY", "272", "1"), ("EV_SYN", "0", "0")])]
    y = 100
    for title, evs in rows:
        f.text(24, y + 20, title, "t", 10.5)
        x = 230
        for t, c, v in evs:
            syn = t == "EV_SYN"
            f.rect(x, y + 4, 124, 26, "m f" if syn else "s f", 4)
            f.text(x + 8, y + 21, f"{t} {c} {v}", "tm" if syn else "t", 10, "start", None, True)
            x += 128
        y += 40
    f.text(24, 274, "The tablet sent x = 5145 of 0 to 32767; the driver made it 5145 * 640 / 32768 = 100.", "tm", 10.5)
    f.text(24, 290, "A program acts at EV_SYN, when x and y are both there.", "tm", 10.5)
    return f


# ================================================================== 09.04

def glyph():
    f = Fig("f0904a", "The letter a as 8 bytes of bits", 288)
    g = font()[ord("a") - 32]
    gx, gy, c = 120, 46, 26
    for col in range(8):
        f.text(gx + col * c + c / 2, gy - 8, f"{0x80 >> col:x}".rjust(2, "0"), "tm", 9, "middle", None, True)
    f.text(gx - 12, gy - 8, "bit", "tm", 9, "end")
    for row in range(8):
        for col in range(8):
            on = g[row] & (0x80 >> col)
            f.rect(gx + col * c, gy + row * c, c, c, "a fa" if on else "s f", 0)
        f.text(gx - 12, gy + row * c + c / 2 + 4, f"row {row}", "tm", 9.5, "end", None, True)
        bits = format(g[row], "08b")
        f.text(gx + 8 * c + 16, gy + row * c + c / 2 + 4, f"0x{g[row]:02x}", "t", 11, "start", 600, True)
        f.text(gx + 8 * c + 66, gy + row * c + c / 2 + 4, bits, "tm", 10.5, "start", None, True)
    f.text(gx + 8 * c + 16, gy - 8, "byte", "tm", 9.5)
    f.text(gx + 8 * c + 66, gy - 8, "bits, 7 to 0", "tm", 9.5)
    f.text(24, 276, "font['a' - 32]: bit 7 is the leftmost pixel; drawchar plots each 1 at (x + column, y + row)", "tm", 10.5)
    return f


def lineplot():
    f = Fig("f0904b", "Bresenham's line from (0, 0) to (8, 3)", 264)
    pts = bresenham(0, 0, 8, 3)
    gx, gy, c = 44, 36, 34
    for r in range(4):
        for k in range(9):
            on = any(px == k and py == r for px, py, _ in pts)
            f.rect(gx + k * c, gy + r * c, c, c, "a fa" if on else "s f", 0)
    for k in range(9):
        f.text(gx + k * c + c / 2, gy - 8, str(k), "tm", 9.5, "middle", None, True)
    for r in range(4):
        f.text(gx - 8, gy + r * c + c / 2 + 4, str(r), "tm", 9.5, "end", None, True)
    f.path(f"M{gx + c / 2} {gy + c / 2} L{gx + 8 * c + c / 2} {gy + 3 * c + c / 2}", "s", dash=True)
    f.text(gx, gy + 4 * c + 22, "dx = 8, dy = -3, err starts at dx + dy = 5", "t", 10.5, "start", None, True)
    f.text(gx, gy + 4 * c + 40, "each step: e2 = 2 * err;", "tm", 10.5, "start", None, True)
    f.text(gx, gy + 4 * c + 56, "  e2 >= dy: step x, err += dy", "tm", 10.5, "start", None, True)
    f.text(gx, gy + 4 * c + 72, "  e2 <= dx: step y, err += dx", "tm", 10.5, "start", None, True)
    tx = 396
    f.text(tx, 26, "pixel   err there", "tm", 10, "start", None, True)
    for i, (x, y, err) in enumerate(pts):
        f.text(tx, 46 + i * 18, f"({x}, {y})", "t", 10.5, "start", None, True)
        f.text(tx + 90, 46 + i * 18, str(err), "tm", 10.5, "start", None, True)
    f.text(tx, 46 + len(pts) * 18 + 6, "9 pixels: max(8, 3) + 1", "ta", 10.5)
    return f


def buffers():
    f = Fig("f0904c", "Draw in the back buffer, then present it all at once", 214)
    boxes = [(24, "your drawing calls", "fillrect, line, drawtext", "s fs"),
             (244, "back: malloc(1228800)", "ordinary memory, not shown", "s f"),
             (464, "the screen: fbmap()", "at 0x40000000: shown", "a af")]
    for x, a, b, cls in boxes:
        f.rect(x, 40, 152, 64, cls, 8)
        acc = cls.startswith("a")
        f.text(x + 10, 66, a, "ta" if acc else "t", 10, "start", 600, True)
        f.text(x + 10, 84, b, "ta" if acc else "tm", 9.5)
    f.line(178, 72, 242, 72, "s", arrow=True)
    f.line(398, 72, 462, 72, "a", arrow=True)
    f.text(430, 62, "present()", "ta", 10, "middle", 600, True)
    f.text(24, 140, "QEMU reads the screen whenever it refreshes the window, never knowing a frame is half done.", "tm", 10.5)
    f.text(24, 158, "Drawn straight onto the screen, a frame would show while it is being built: a clear, then", "tm", 10.5)
    f.text(24, 176, "the shapes one by one, then the pointer. present() copies a finished frame in one pass,", "tm", 10.5)
    f.text(24, 194, "8 bytes at a time, so the window only ever moves from one whole frame to the next.", "tm", 10.5)
    return f


# ================================================================== 09.05

def layout():
    f = Fig("f0905a", "paint's screen, drawn to scale", 330)
    s = 0.5
    x0, y0 = 120, 24

    def R(x, y, w, h, cls, rx=0):
        f.rect(x0 + x * s, y0 + y * s, w * s, h * s, cls, rx)

    R(0, 0, 640, 480, "s f")
    R(0, 0, 640, 20, "s fs")
    f.text(x0 + 4, y0 + 8, "paint", "t", 7, "start", 600, True)
    f.text(x0 + 316, y0 + 8, "c clear  1 2 3 pen  esc quit", "tm", 6, "end", None, True)
    R(0, 448, 640, 32, "s fs")
    clss = ["fa", "af", "f", "fa", "af", "f", "fa", "af", "f", "fa"]
    for i in range(10):
        x = 8 + 40 * i
        if i == 3:
            R(x - 2, 450, 36, 28, "a f")
        R(x, 452, 32, 24, "s " + clss[i])
    f.text(x0 + 316, y0 + 233, "pen 2", "tm", 6, "end", None, True)
    f.path(f"M{x0 + 40} {y0 + 90} C {x0 + 80} {y0 + 50}, {x0 + 120} {y0 + 120}, {x0 + 170} {y0 + 80} S {x0 + 230} {y0 + 60}, {x0 + 260} {y0 + 100}", "a")
    cx, cy = x0 + 210, y0 + 150
    f.path(f"M{cx - 4} {cy}L{cx - 1.5} {cy}M{cx + 1.5} {cy}L{cx + 4} {cy}M{cx} {cy - 4}L{cx} {cy - 1.5}M{cx} {cy + 1.5}L{cx} {cy + 4}", "s")
    # labels left
    for y, t in ((0, "0"), (20, "20"), (448, "448"), (480, "480")):
        f.line(x0 - 8, y0 + y * s, x0 - 2, y0 + y * s, "m")
        f.text(x0 - 12, y0 + y * s + 4, t, "tm", 9.5, "end", None, True)
    f.text(24, y0 + 6, "title bar", "t", 10)
    f.text(24, y0 + 120, "canvas", "t", 10, "start", 600)
    f.text(24, y0 + 134, "640 x 428,", "tm", 9.5, "start", None, True)
    f.text(24, y0 + 147, "a surface", "tm", 9.5)
    f.text(24, y0 + 147 + 13, "of its own", "tm", 9.5)
    f.text(24, y0 + 236, "colour bar", "t", 10)
    # labels right
    rx = 460
    f.text(rx, 46, "swatch i: (8 + 40i, 452),", "t", 10, "start", None, True)
    f.text(rx, 60, "32 x 24; the chosen one", "t", 10)
    f.text(rx, 74, "in a white frame 2 wide", "t", 10)
    f.text(rx, 112, "the stroke: line() at", "t", 10)
    f.text(rx, 126, "every offset up to pen", "t", 10)
    f.text(rx, 164, "the pointer: arms 3 to 8", "t", 10)
    f.text(rx, 178, "pixels out, black on white,", "t", 10)
    f.text(rx, 192, "the middle left clear", "t", 10)
    f.text(24, 306, "Text is the 8x8 font at 1:1, so on the real screen \"paint\" is 40 pixels wide; here everything is half size.", "tm", 10.5)
    f.text(24, 322, "Swatches: black, grey, white, red, orange, yellow, green, cyan, blue, purple; red is chosen here.", "tm", 10.5)
    return f


def loop():
    f = Fig("f0905b", "One turn of paint's loop", 250)
    boxes = [(24, 40, "read(fd, ev, 256)", "sleep until there are events;", "get up to 32 at once", "s fs"),
             (234, 40, "handle(e), for each", "EV_ABS: nx, ny; EV_SYN: move,", "stroke into the canvas; keys", "s f"),
             (444, 40, "redraw()", "compose the frame in back,", "then present()", "a af")]
    for x, y, a, b, c, cls in boxes:
        f.rect(x, y, 172, 70, cls, 8)
        acc = cls.startswith("a")
        f.text(x + 12, y + 22, a, "ta" if acc else "t", 10.5, "start", 600, True)
        f.text(x + 12, y + 40, b, "ta" if acc else "tm", 9.5)
        f.text(x + 12, y + 54, c, "ta" if acc else "tm", 9.5)
    f.line(196, 75, 232, 75, "s", arrow=True)
    f.line(406, 75, 442, 75, "s", arrow=True)
    f.path("M530 110 C 530 150, 110 150, 110 112", "s", arrow=True)
    layers = ["1  blit the canvas", "2  the title bar and its text", "3  the colour bar, the frame, the swatches",
              "4  the pointer, if it has moved", "5  present: the whole frame to the screen"]
    for i, t in enumerate(layers):
        f.text(234, 176 + i * 15, t, "ta" if i == 4 else "t", 10, "start", 600 if i == 4 else None)
    f.text(24, 176, "redraw, back to front:", "tm", 10.5)
    f.text(24, 194, "later layers cover earlier", "tm", 10.5)
    f.text(24, 212, "ones; nothing from the last", "tm", 10.5)
    f.text(24, 230, "frame survives but the canvas", "tm", 10.5)
    return f


FIGS = [
    ("09.01-fwcfg", fwcfg),
    ("09.01-pixel", pixel),
    ("09.02-mapping", mapping),
    ("09.02-teardown", teardown),
    ("09.03-keypath", keypath),
    ("09.03-groups", groups),
    ("09.04-glyph", glyph),
    ("09.04-line", lineplot),
    ("09.04-buffers", buffers),
    ("09.05-layout", layout),
    ("09.05-loop", loop),
]

if __name__ == "__main__":
    for name, fn in FIGS:
        print(write(MOD, name, fn()))
