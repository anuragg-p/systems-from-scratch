"""Generate the xv6 module art: icon.svg (20x20 line icon) and cover.svg
(640x300 teaching diagram) for each module directory.

Covers style themselves through classes the web UI defines under .art:
  s m a        stroke: foreground, muted, accent
  f fs af fa   fill: page, code background, accent-soft, accent
  t tm ta      text fill: foreground, muted, accent      mono: monospace
"""
import html
import os
import sys

LESSONS = os.path.expanduser("~/Documents/WORK/misc/systems-from-scratch/tracks/xv6/lessons")
SW = 'stroke-width="1.5"'


def esc(s):
    return html.escape(s, quote=True)


class Art:
    def __init__(self, key, title, h=300):
        self.key, self.title, self.out, self.h = key, title, [], h

    def add(self, s):
        self.out.append(s)

    def box(self, x, y, w, h, cls="s f", rx=10, dash=False):
        d = ' stroke-dasharray="4 4"' if dash else ""
        self.add(f'<rect class="{cls}" x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" {SW}{d}/>')

    def text(self, x, y, s, cls="t", size=12, anchor="start", weight=None, mono=False):
        c = cls + (" mono" if mono else "")
        wt = f' font-weight="{weight}"' if weight else ""
        a = f' text-anchor="{anchor}"' if anchor != "start" else ""
        self.add(f'<text class="{c}" x="{x}" y="{y}" font-size="{size}"{wt}{a}>{esc(s)}</text>')

    def line(self, x1, y1, x2, y2, cls="s", arrow=False, dash=False):
        m = f' marker-end="url(#{self.key}-{"aa" if "a" == cls else "ah"})"' if arrow else ""
        d = ' stroke-dasharray="4 4"' if dash else ""
        self.add(f'<line class="{cls}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" {SW} stroke-linecap="round"{m}{d}/>')

    def path(self, d, cls="s", arrow=False, dash=False):
        m = f' marker-end="url(#{self.key}-{"aa" if "a" == cls else "ah"})"' if arrow else ""
        da = ' stroke-dasharray="4 4"' if dash else ""
        self.add(f'<path class="{cls}" d="{d}" {SW} stroke-linecap="round" stroke-linejoin="round"{m}{da}/>')

    def circle(self, cx, cy, r, cls="s f"):
        self.add(f'<circle class="{cls}" cx="{cx}" cy="{cy}" r="{r}" {SW}/>')

    def svg(self):
        defs = (f'<defs>'
                f'<marker id="{self.key}-ah" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
                f'<path class="s" d="M1 1.5L8.5 5L1 8.5" {SW} stroke-linecap="round" stroke-linejoin="round"/></marker>'
                f'<marker id="{self.key}-aa" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
                f'<path class="a" d="M1 1.5L8.5 5L1 8.5" {SW} stroke-linecap="round" stroke-linejoin="round"/></marker>'
                f'</defs>')
        body = "\n".join(self.out)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 {self.h}" fill="none">\n'
                f'<title>{esc(self.title)}</title>\n{defs}\n{body}\n</svg>\n')


# ------------------------------------------------------------------ 00

def workbench():
    a = Art("m00", "From source code to a running virt machine")
    a.box(24, 60, 150, 50); a.text(40, 82, "kernel/*.c", mono=True, size=13); a.text(40, 100, "kernel/*.S", "tm", mono=True, size=11)
    a.line(174, 85, 294, 85, arrow=True); a.text(234, 76, "gcc + ld", "tm", 11, "middle", mono=True); a.text(234, 102, "kernel.ld", "tm", 11, "middle", mono=True)
    a.box(296, 60, 150, 50, "a af"); a.text(312, 82, "kernel (ELF)", mono=True, size=13); a.text(312, 100, "_entry 0x80000000", "ta", 11, mono=True)
    a.box(24, 190, 150, 50); a.text(40, 212, "user/*.c", mono=True, size=13); a.text(40, 230, "+ README", "tm", 11, mono=True)
    a.line(174, 215, 294, 215, arrow=True); a.text(234, 206, "gcc, mkfs", "tm", 11, "middle", mono=True)
    a.box(296, 190, 150, 50); a.text(312, 212, "fs.img", mono=True, size=13); a.text(312, 230, "2000 blocks x 1 KB", "tm", 11, mono=True)
    a.box(486, 32, 130, 236, "s fs", rx=14); a.text(500, 56, "qemu virt", size=13, weight=700); a.text(500, 73, "riscv64, 3 harts", "tm", 11)
    for y, name, addr, cls in ((90, "RAM", "0x80000000", "a af"), (150, "virtio disk", "0x10001000", "s f"), (210, "uart0", "0x10000000", "s f")):
        a.box(500, y, 102, 44, cls, rx=8)
        a.text(512, y + 19, name, size=12, weight=600)
        a.text(512, y + 35, addr, "ta" if cls.startswith("a") else "tm", 10.5, mono=True)
    a.path("M446 85 C 472 85, 474 112, 498 112", "a", arrow=True)
    a.path("M446 215 C 474 215, 472 172, 498 172", "s", arrow=True)
    a.text(24, 288, "loaded at the address the boot ROM jumps to", "tm", 11)
    return a


# ------------------------------------------------------------------ 01

def boot():
    a = Art("m01", "Every hart, from reset to main")
    a.add('<rect class="fs" x="112" y="46" width="368" height="200" rx="12"/>')
    a.add('<rect class="af" x="480" y="46" width="136" height="200" rx="12"/>')
    a.text(126, 64, "machine mode", "tm", 11); a.text(494, 64, "supervisor mode", "ta", 11)
    cols = [(162, "boot ROM", "0x1000"), (262, "_entry", "0x80000000"), (382, "start()", "start.c"), (480, "mret", ""), (552, "main()", "main.c")]
    for x, top, sub in cols:
        a.text(x, 92, top, "ta" if top == "mret" else "t", 12, "middle", 600, mono=top != "boot ROM")
        if sub:
            a.text(x, 108, sub, "tm", 10.5, "middle", mono=True)
    a.line(480, 116, 480, 236, "a")
    for i, y in enumerate((146, 182, 218)):
        a.text(24, y + 4, f"hart {i}", mono=True, size=12)
        a.line(100, y, 606, y, "m")
        for x, top, _ in cols:
            a.circle(x, y, 5, "a f" if top == "mret" else "s f")
    a.text(262, 272, "sp = stack0 + (hartid + 1) * 4096", "ta", 11.5, "middle", mono=True)
    a.text(552, 272, "hart 0 sets up; the rest wait", "tm", 11, "middle")
    return a


# ------------------------------------------------------------------ 02

def memory():
    a = Art("m02", "Sv39: one virtual address, three page-table lookups")
    a.text(60, 24, "virtual address", "tm", 11)
    segs = [(60, 120, "L2"), (180, 120, "L1"), (300, 120, "L0"), (420, 160, "offset")]
    for x, w, name in segs:
        a.add(f'<rect class="s f" x="{x}" y="32" width="{w}" height="34" {SW}/>')
        a.text(x + w / 2, 54, name, size=12, anchor="middle", weight=600, mono=True)
    for x, w, bits in ((60, 120, "9 bits"), (180, 120, "9 bits"), (300, 120, "9 bits"), (420, 160, "12 bits")):
        a.text(x + w / 2, 82, bits, "tm", 10.5, "middle", mono=True)
    tables = [(70, 2, "level 2"), (230, 5, "level 1"), (390, 3, "level 0")]
    rowh = 16.5
    for x, hi, name in tables:
        a.add(f'<rect class="af" x="{x}" y="{128 + hi * rowh}" width="96" height="{rowh}"/>')
        a.box(x, 128, 96, 132, "s", rx=6)
        for r in range(1, 8):
            a.line(x, 128 + r * rowh, x + 96, 128 + r * rowh, "m")
        a.text(x + 48, 278, name, "t", 11.5, "middle", 600)
        a.text(x + 48, 293, "512 PTEs", "tm", 10.5, "middle", mono=True)
    for sx, tx in ((120, 118), (240, 278), (360, 438)):
        a.line(sx, 92, tx, 126, "m", dash=True)
    a.line(500, 92, 575, 148, "m", dash=True)
    a.text(22, 175, "satp", "ta", 12, mono=True, weight=600)
    a.line(54, 171, 68, 171, "a", arrow=True)

    def mid(hi):
        return 128 + hi * rowh + rowh / 2
    a.path(f"M166 {mid(2)} C 198 {mid(2)}, 198 {mid(5)}, 228 {mid(5)}", "a", arrow=True)
    a.path(f"M326 {mid(5)} C 358 {mid(5)}, 358 {mid(3)}, 388 {mid(3)}", "a", arrow=True)
    a.path(f"M486 {mid(3)} C 508 {mid(3)}, 508 195, 528 195", "a", arrow=True)
    a.box(530, 150, 90, 90, "a af", rx=8)
    a.circle(575, 210, 3.5, "a fa")
    a.text(575, 278, "physical page", "t", 11.5, "middle", 600)
    a.text(575, 293, "4096 bytes", "tm", 10.5, "middle", mono=True)
    return a


# ------------------------------------------------------------------ 03

def traps():
    a = Art("m03", "Every trap enters the kernel through stvec")
    a.add('<rect class="fs" x="24" y="20" width="592" height="98" rx="12"/>')
    a.text(40, 40, "user mode", "tm", 11)
    a.box(24, 158, 592, 122, "m f", rx=12)
    a.text(40, 178, "supervisor mode: the kernel", "tm", 11)
    a.line(24, 138, 616, 138, "m", dash=True)
    pills = [(56, 92, "ecall"), (168, 112, "page fault"), (300, 84, "timer"), (404, 150, "device (PLIC)")]
    for x, w, name in pills:
        a.box(x, 58, w, 30, "s f", rx=15)
        a.text(x + w / 2, 78, name, size=12, anchor="middle", mono=name in ("ecall",))
        a.line(x + w / 2, 88, 320, 132, "s")
    a.circle(320, 138, 7, "a af")
    a.text(336, 152, "stvec", "ta", 12, weight=600, mono=True)
    a.line(320, 146, 320, 186, "s", arrow=True)
    a.box(214, 188, 212, 30, "s f", rx=8); a.text(320, 208, "uservec / kernelvec", size=12, anchor="middle", mono=True)
    a.line(320, 218, 320, 230, "s", arrow=True)
    a.box(214, 232, 212, 30, "s f", rx=8); a.text(320, 252, "usertrap() / kerneltrap()", size=12, anchor="middle", mono=True)
    a.path("M426 247 C 448 247, 448 206, 470 206", "s", arrow=True)
    a.path("M426 247 C 448 247, 448 252, 470 252", "s", arrow=True)
    a.box(472, 192, 108, 28, "s f", rx=8); a.text(526, 211, "syscall()", size=12, anchor="middle", mono=True)
    a.box(472, 238, 108, 28, "s f", rx=8); a.text(526, 257, "devintr()", size=12, anchor="middle", mono=True)
    a.path("M596 192 C 596 140, 596 100, 572 90", "a", arrow=True)
    a.text(588, 128, "sret", "ta", 12, "end", 600, mono=True)
    a.text(40, 262, "scause says why", "tm", 11)
    a.text(40, 247, "sepc, stval: where", "tm", 11)
    return a


# ------------------------------------------------------------------ 04

def processes():
    a = Art("m04", "The process table, and swtch moving the CPU between kernel stacks")
    a.text(32, 54, "proc[64]", mono=True, size=12, weight=600)
    states = ["run", "sleep", "ready", "sleep", "run", "ready", "sleep", "sleep", "ready", "run", "sleep", "sleep"]
    cls = {"run": "a fa", "ready": "a af", "sleep": "s fs", "unused": "m f"}
    for i in range(64):
        x, y = 32 + (i % 8) * 22, 66 + (i // 8) * 22
        st = states[i] if i < len(states) else "unused"
        a.add(f'<rect class="{cls[st]}" x="{x}" y="{y}" width="16" height="16" rx="4" {SW}/>')
    for i, (st, label) in enumerate((("run", "running"), ("ready", "runnable"), ("sleep", "sleeping"), ("unused", "unused"))):
        x = 32 + (i % 2) * 92
        y = 256 + (i // 2) * 22
        a.add(f'<rect class="{cls[st]}" x="{x}" y="{y - 11}" width="12" height="12" rx="3" {SW}/>')
        a.text(x + 20, y - 1, label, "tm", 11)
    cols = [(268, "process A", "kernel stack"), (398, "scheduler", "cpu->context"), (528, "process B", "kernel stack")]
    for x, t1, t2 in cols:
        a.text(x + 44, 70, t1, size=12, anchor="middle", weight=600)
        a.text(x + 44, 86, t2, "tm", 10.5, "middle", mono=True)
        a.box(x, 96, 88, 150, "s f", rx=8)
        for y in (122, 148, 174):
            a.line(x + 10, y, x + 78, y, "m")
        a.box(x + 6, 204, 76, 36, "a af", rx=6)
        a.text(x + 44, 219, "context", "ta", 10.5, "middle", 600, mono=True)
        a.text(x + 44, 233, "ra sp s0-s11", "tm", 9.5, "middle", mono=True)
    a.line(358, 222, 396, 222, "a", arrow=True); a.text(377, 266, "swtch", "ta", 11, "middle", 600, mono=True)
    a.line(488, 222, 526, 222, "a", arrow=True); a.text(507, 266, "swtch", "ta", 11, "middle", 600, mono=True)
    a.path("M572 54 C 572 22, 312 22, 312 52", "m", arrow=True, dash=True)
    a.text(442, 18, "later, B switches back the same way", "tm", 10.5, "middle")
    return a


# ------------------------------------------------------------------ 05

def storage():
    a = Art("m05", "The disk layout, the layers above it, and one logged transaction")
    a.text(24, 22, "fs.img, block by block (1024 bytes each)", "tm", 11)
    segs = [(24, 40, "boot", "0"), (64, 40, "super", "1"), (104, 120, "log", "2-32"), (224, 90, "inodes", "33-45"),
            (314, 40, "bitmap", "46"), (354, 262, "data", "47-1999")]
    for x, w, name, blocks in segs:
        cls = "a af" if name == "log" else "s f"
        a.add(f'<rect class="{cls}" x="{x}" y="32" width="{w}" height="44" {SW}/>')
        a.text(x + w / 2, 58, name, "ta" if name == "log" else "t", 10.5 if w <= 40 else 12, "middle", 600)
        a.text(x + w / 2, 92, blocks, "tm", 10.5, "middle", mono=True)
    a.text(24, 122, "the layers", "tm", 11)
    layers = ["file descriptors", "path names", "directories", "inodes", "log", "buffer cache", "virtio disk"]
    for i, name in enumerate(layers):
        y = 130 + i * 23
        a.box(24, y, 250, 18, "a af" if name == "log" else "s f", rx=5)
        a.text(36, y + 13, name, "ta" if name == "log" else "t", 11.5, weight=600 if name == "log" else None)
    a.text(330, 122, "one transaction", "tm", 11)
    steps = ["begin_op()", "log_write(b) for each changed block", "end_op(): copy the blocks into the log",
             "write the header: the commit point", "install the blocks at home", "clear the header"]
    a.line(338, 140, 338, 270, "m")
    for i, s in enumerate(steps):
        y = 140 + i * 26
        commit = "commit" in s
        a.circle(338, y, 4.5, "a fa" if commit else "s f")
        a.text(352, y + 4, s, "ta" if commit else "t", 11.5, weight=600 if commit else None, mono=s.endswith("()"))
    return a


# ------------------------------------------------------------------ 06

def user_space():
    a = Art("m06", "A process's address space next to the kernel's, sharing the trampoline")
    a.text(210, 16, "a process (user page table)", size=12, anchor="middle", weight=600)
    a.text(510, 16, "the kernel (kernel page table)", size=12, anchor="middle", weight=600)
    user = [(26, 24, "trampoline", "a af"), (50, 24, "trapframe", "s fs"), (74, 84, "", "gap"), (158, 30, "heap (sbrk grows it)", "s f"),
            (188, 26, "stack", "s f"), (214, 14, "guard page", "m fs"), (228, 24, "data, bss", "s f"), (252, 24, "text (code)", "s f")]
    for y, h, name, cls in user:
        if cls == "gap":
            a.box(120, y, 180, h, "m", rx=0, dash=True)
            a.text(210, y + h / 2 + 4, "unused", "tm", 11, "middle")
            continue
        a.add(f'<rect class="{cls}" x="120" y="{y}" width="180" height="{h}" {SW}/>')
        a.text(210, y + h / 2 + 4, name, "ta" if cls.startswith("a") else ("tm" if name == "guard page" else "t"),
               10 if name == "guard page" else 11.5, "middle", mono=name in ("trampoline", "trapframe"))
    a.path("M286 182 L286 166 M281 171 L286 166 L291 171", "s")
    a.text(112, 40, "MAXVA", "tm", 10.5, "end", mono=True)
    a.text(112, 280, "0", "tm", 10.5, "end", mono=True)
    a.text(112, 244, "PTE_U", "tm", 10, "end", mono=True)
    kern = [(26, 24, "trampoline", "a af"), (50, 44, "kernel stacks, guard pages", "s fs"), (94, 46, "", "gap"),
            (140, 84, "RAM, direct mapped", "s f"), (224, 52, "devices: PLIC, uart, virtio", "s f")]
    for y, h, name, cls in kern:
        if cls == "gap":
            a.box(420, y, 180, h, "m", rx=0, dash=True)
            a.text(510, y + h / 2 + 4, "unused", "tm", 11, "middle")
            continue
        a.add(f'<rect class="{cls}" x="420" y="{y}" width="180" height="{h}" {SW}/>')
        a.text(510, y + h / 2 + 4, name, "ta" if cls.startswith("a") else "t", 11.5, "middle", mono=name == "trampoline")
    a.text(510, 200, "KERNBASE .. PHYSTOP", "tm", 10, "middle", mono=True)
    a.line(300, 38, 418, 38, "a", dash=True)
    a.text(359, 58, "same address", "ta", 10.5, "middle", 600)
    a.text(359, 72, "in both", "ta", 10.5, "middle")
    return a


# ------------------------------------------------------------------ 07

def userland():
    a = Art("m07", "The shell parses a pipeline into a tree, then runs it as processes joined by pipes")
    a.add('<rect class="fs" x="24" y="14" width="592" height="40" rx="10"/>')
    a.text(44, 39, "$ cat README | grep cat | wc", mono=True, size=15)
    nodes = [(280, 72, 80, "PIPE"), (126, 116, 128, "EXEC cat README"), (410, 116, 80, "PIPE"),
             (346, 160, 118, "EXEC grep cat"), (480, 160, 84, "EXEC wc")]
    for x, y, w, label in nodes:
        a.box(x, y, w, 24, "s f", rx=12)
        a.text(x + w / 2, y + 16, label, size=11, anchor="middle", mono=True)
    for x1, y1, x2, y2 in ((320, 96, 190, 116), (320, 96, 450, 116), (450, 140, 405, 160), (450, 140, 522, 160)):
        a.line(x1, y1, x2, y2, "m")
    a.text(24, 132, "parsecmd()", "tm", 11, mono=True)
    a.text(24, 246, "runcmd()", "tm", 11, mono=True)
    procs = [(110, 76, "cat"), (266, 80, "grep"), (426, 60, "wc")]
    for x, w, name in procs:
        a.box(x, 226, w, 32, "s f", rx=8)
        a.text(x + w / 2, 247, name, size=12.5, anchor="middle", weight=600, mono=True)
    for x1, x2 in ((186, 266), (346, 426)):
        a.add(f'<rect class="a af" x="{x1}" y="236" width="{x2 - x1}" height="12" rx="6" {SW}/>')
        a.text((x1 + x2) / 2, 228, "pipe", "ta", 10.5, "middle", 600)
    a.line(486, 242, 528, 242, "s", arrow=True)
    a.text(534, 246, "console", size=12)
    a.text(226, 276, "fd 1 -> pipe -> fd 0", "tm", 10.5, "middle", mono=True)
    return a


ICONS = {
    "00": '<rect x="2.5" y="3.5" width="15" height="13" rx="2.5"/><path d="M6 8l2.5 2L6 12M10.5 12.5h3.5"/>',
    "01": '<path d="M10 2.75v6"/><path d="M6.1 5.4a6.25 6.25 0 1 0 7.8 0"/>',
    "02": '<rect x="3" y="3" width="14" height="14" rx="2.5"/><path d="M3 7.67h14M3 12.33h14M7.67 3v14M12.33 3v14"/>',
    "03": '<path d="M11 2.5L5 11h4.5l-1 6.5 6-8.5H10z"/>',
    "04": '<path d="M4 7h11M12 4l3 3-3 3M16 13H5M8 10l-3 3 3 3"/>',
    "05": '<ellipse cx="10" cy="5" rx="6" ry="2.5"/><path d="M4 5v10c0 1.38 2.69 2.5 6 2.5s6-1.12 6-2.5V5M4 10c0 1.38 2.69 2.5 6 2.5s6-1.12 6-2.5"/>',
    "06": '<path d="M2.5 10h15" stroke-dasharray="2 2.5"/><path d="M7 3v4.5M5 5.5l2 2 2-2M13 17v-4.5M11 14.5l2-2 2 2"/>',
    "07": '<rect x="1.75" y="7" width="4.5" height="6" rx="1"/><rect x="7.75" y="7" width="4.5" height="6" rx="1"/><rect x="13.75" y="7" width="4.5" height="6" rx="1"/><path d="M6.25 10h1.5M12.25 10h1.5"/>',
}

COVERS = {"00": workbench, "01": boot, "02": memory, "03": traps, "04": processes, "05": storage, "06": user_space, "07": userland}


def main():
    dirs = {d[:2]: os.path.join(LESSONS, d) for d in os.listdir(LESSONS) if d[:2].isdigit()}
    out = sys.argv[1] if len(sys.argv) > 1 else None
    for mid, fn in COVERS.items():
        target = os.path.join(out, mid) if out else dirs[mid]
        os.makedirs(target, exist_ok=True)
        with open(os.path.join(target, "cover.svg"), "w") as f:
            f.write(fn().svg())
        with open(os.path.join(target, "icon.svg"), "w") as f:
            f.write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="none" stroke="currentColor" '
                    'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">' + ICONS[mid] + "</svg>\n")
    print("wrote", len(COVERS), "covers and icons to", out or LESSONS)


if __name__ == "__main__":
    main()
