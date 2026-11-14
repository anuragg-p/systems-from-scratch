"""Lesson figures for xv6 modules 06 and 07.

Copied from the shared cover generator (tools/art.py) and extended: variable height,
a muted arrow marker, square cells. Writes tracks/xv6/lessons/NN-*/figures/NN.LL-name.svg.

Classes (defined under .art in harness/web/app.css):
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


def fmt(v):
    return ("%.2f" % v).rstrip("0").rstrip(".") if isinstance(v, float) else str(v)


class Art:
    def __init__(self, key, title, h):
        self.key, self.title, self.h, self.out = key, title, h, []

    def add(self, s):
        self.out.append(s)

    def _marker(self, cls):
        return {"a": "aa", "m": "am"}.get(cls, "ah")

    def box(self, x, y, w, h, cls="s f", rx=8, dash=False):
        d = ' stroke-dasharray="4 4"' if dash else ""
        self.add(f'<rect class="{cls}" x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}" rx="{rx}" {SW}{d}/>')

    def cell(self, x, y, w, h, cls="s f", dash=False):
        self.box(x, y, w, h, cls, rx=0, dash=dash)

    def fill(self, x, y, w, h, cls="af", rx=0):
        self.add(f'<rect class="{cls}" x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}" rx="{rx}"/>')

    def text(self, x, y, s, cls="t", size=12, anchor="start", weight=None, mono=False):
        c = cls + (" mono" if mono else "")
        wt = f' font-weight="{weight}"' if weight else ""
        a = f' text-anchor="{anchor}"' if anchor != "start" else ""
        self.add(f'<text class="{c}" x="{fmt(x)}" y="{fmt(y)}" font-size="{size}"{wt}{a}>{esc(s)}</text>')

    def mono(self, x, y, s, cls="t", size=11, anchor="start", weight=None):
        self.text(x, y, s, cls, size, anchor, weight, mono=True)

    def line(self, x1, y1, x2, y2, cls="s", arrow=False, dash=False):
        m = f' marker-end="url(#{self.key}-{self._marker(cls)})"' if arrow else ""
        d = ' stroke-dasharray="4 4"' if dash else ""
        self.add(f'<line class="{cls}" x1="{fmt(x1)}" y1="{fmt(y1)}" x2="{fmt(x2)}" y2="{fmt(y2)}" {SW} stroke-linecap="round"{m}{d}/>')

    def path(self, d, cls="s", arrow=False, dash=False):
        m = f' marker-end="url(#{self.key}-{self._marker(cls)})"' if arrow else ""
        da = ' stroke-dasharray="4 4"' if dash else ""
        self.add(f'<path class="{cls}" d="{d}" {SW} stroke-linecap="round" stroke-linejoin="round"{m}{da}/>')

    def circle(self, cx, cy, r, cls="s f"):
        self.add(f'<circle class="{cls}" cx="{fmt(cx)}" cy="{fmt(cy)}" r="{fmt(r)}" {SW}/>')

    def svg(self):
        def mk(name, cls):
            return (f'<marker id="{self.key}-{name}" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
                    f'<path class="{cls}" d="M1 1.5L8.5 5L1 8.5" {SW} stroke-linecap="round" stroke-linejoin="round"/></marker>')
        defs = f'<defs>{mk("ah", "s")}{mk("aa", "a")}{mk("am", "m")}</defs>'
        body = "\n".join(self.out)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 {self.h}" fill="none">\n'
                f'<title>{esc(self.title)}</title>\n{defs}\n{body}\n</svg>\n')


# ================================================================== 06.01

TF = ["kernel_satp", "kernel_sp", "kernel_trap", "epc", "kernel_hartid",
      "ra", "sp", "gp", "tp", "t0", "t1", "t2", "s0", "s1", "a0", "a1", "a2", "a3", "a4", "a5", "a6", "a7",
      "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10", "s11", "t3", "t4", "t5", "t6"]


def trapframe():
    a = Art("f0601a", "struct trapframe: 36 eight-byte slots at fixed offsets", 262)
    rh = 22
    a.text(24, 24, "for the kernel", "tm", 10.5)
    a.text(176, 24, "the 31 user registers", "tm", 10.5)
    for i, name in enumerate(TF):
        if i < 5:
            x, y, cw = 24, 34 + i * rh, 136
        else:
            col, row = divmod(i - 5, 8)
            x, y, cw = 176 + col * 112, 34 + row * rh, 100
        hot = name == "a0"
        a.cell(x, y, cw, rh, "a af" if hot else ("s fs" if i < 5 else "s f"))
        a.mono(x + 30, y + 15, str(i * 8), "ta" if hot else "tm", 10.5, "end")
        a.mono(x + 40, y + 15, name, "ta" if hot else "t", 11, weight=600 if hot else None)
    for i, s in enumerate(("prepare_return() fills", "these in before each", "return; uservec reads", "them on the next trap")):
        a.text(24, 164 + i * 14, s, "tm", 10.5)
    a.text(24, 234, "uservec saves the user registers here and userret loads them back, at offsets hard-coded in the assembly", "tm", 10.5)
    a.text(24, 252, "a0 at 112 is parked in sscratch on the way in, so it is saved last and loaded last", "ta", 10.5)
    return a


def round_trip():
    a = Art("f0601b", "A system call's round trip, with the page table and stvec in force at each moment", 300)
    lanes = [(12, "user mode"), (72, "trampoline"), (132, "kernel")]
    for y, name in lanes:
        a.fill(24, y, 592, 52, "fs", rx=10)
        a.text(36, y + 15, name, "tm", 10.5)
    boxes = [(40, 34, 56, "ecall"), (112, 94, 100, "uservec"), (228, 154, 90, "usertrap()"),
             (330, 154, 122, "prepare_return()"), (466, 94, 80, "userret"), (560, 34, 56, "ecall+4")]
    for x, y, w, s in boxes:
        a.box(x, y, w, 24, "s f", rx=6)
        a.mono(x + w / 2, y + 16, s, size=11, anchor="middle")
    a.path("M68 58 C 68 80, 150 70, 150 92", arrow=True)
    a.path("M190 118 C 190 140, 260 132, 260 152", arrow=True)
    a.line(318, 166, 328, 166, arrow=True)
    a.path("M420 154 C 420 132, 496 140, 496 120", arrow=True)
    a.path("M530 94 C 530 72, 588 76, 588 60", arrow=True)
    a.mono(462, 150, "a0 = user satp", "tm", 10)
    # bands
    def band(y, label, segs, ticks):
        a.mono(24, y + 14, label, "t", 11, weight=600)
        for x1, x2, s, accent in segs:
            a.cell(x1, y, x2 - x1, 20, "a af" if accent else "s f")
            a.text((x1 + x2) / 2, y + 14, s, "ta" if accent else "tm", 10.5, "middle")
        for x, s in ticks:
            a.line(x, y + 20, x, y + 26, "s")
            a.mono(x, y + 37, s, "tm", 10, "middle")
    band(198, "satp", [(76, 200, "user page table", False), (200, 486, "kernel page table", True), (486, 616, "user page table", False)],
         [(200, "uservec: csrw satp"), (486, "userret: csrw satp")])
    band(252, "stvec", [(76, 236, "uservec", False), (236, 440, "kernelvec", False), (440, 616, "uservec", False)],
         [(236, "usertrap()"), (440, "prepare_return()")])
    return a


# ================================================================== 06.02

def syscall_path():
    a = Art("f0602", "write(1, buf, 3) as a system call: a7 picks the function, a0 carries the result back", 240)
    a.text(24, 22, "user program", "tm", 10.5)
    a.box(24, 34, 172, 30, "s f", rx=6)
    a.mono(36, 54, "n = write(1, buf, 3)", size=11.5)
    a.line(110, 64, 110, 90, arrow=True)
    a.box(24, 92, 172, 84, "s fs", rx=6)
    a.text(186, 108, "usys.S", "tm", 10, "end")
    for i, s in enumerate(("li  a7, 16", "ecall", "ret")):
        a.mono(40, 116 + i * 22, s, size=12)
    # trapframe
    a.mono(252, 22, "p->trapframe", "tm", 10.5)
    rows = [("112", "a0", "1"), ("120", "a1", "buf"), ("128", "a2", "3"), ("", "a3 .. a6", ""), ("168", "a7", "16")]
    for i, (off, name, val) in enumerate(rows):
        y = 34 + i * 24
        if off:
            a.cell(252, y, 140, 24, "s f")
            a.mono(274, y + 16, off, "tm", 10, "end")
            a.mono(284, y + 16, name, size=12)
            a.mono(382, y + 16, val, size=12, anchor="end")
        else:
            a.cell(252, y, 140, 24, "m fs")
            a.mono(284, y + 16, name, "tm", 11)
    a.line(196, 142, 250, 142, arrow=True)
    a.mono(223, 134, "ecall", "tm", 10, "middle")
    a.mono(223, 160, "uservec", "tm", 10, "middle")
    a.mono(223, 174, "saves", "tm", 10, "middle")
    # kernel
    a.box(452, 34, 164, 84, "s f", rx=6)
    a.mono(464, 54, "sys_write()", size=12, weight=600)
    for i, (call, val) in enumerate((("argaddr(1)", "buf"), ("argint(2)", "3"), ("argfd(0)", "ofile[1]"))):
        a.mono(464, 74 + i * 15, call, "tm", 10.5)
        a.mono(606, 74 + i * 15, val, "t", 10.5, "end")
    # kernel/syscall.c at 06.02: syscalls[] has read (5), fstat (8), write (16) and close (21);
    # the other calls arrive with 06.04 to 06.07.
    a.mono(452, 160, "syscalls[]", "tm", 10.5)
    for i, (n, fn) in enumerate((("8", "sys_fstat"), ("16", "sys_write"), ("21", "sys_close"))):
        y = 168 + i * 22
        hot = n == "16"
        a.cell(452, y, 164, 22, "a af" if hot else "s f")
        a.mono(482, y + 15, f"[{n}]", "ta" if hot else "tm", 11, "end")
        a.mono(492, y + 15, fn, "ta" if hot else "t", 11.5, weight=600 if hot else None)
    a.path("M392 142 C 420 142, 424 201, 450 201", "a", arrow=True)
    a.mono(414, 136, "a7", "ta", 10, "middle")
    a.path("M616 201 C 636 201, 636 76, 618 76", arrow=True)
    a.line(394, 88, 450, 88, "m", arrow=True, dash=True)
    a.mono(422, 82, "argraw", "tm", 10, "middle")
    a.line(450, 46, 394, 46, arrow=True)
    a.mono(422, 40, "a0 = 3", "t", 10, "middle")
    a.line(250, 49, 198, 49, arrow=True)
    a.mono(224, 43, "sret", "t", 10, "middle")
    a.text(24, 200, "userret restores a0 = 3,", "tm", 10.5)
    a.text(24, 214, "so write() returns 3", "tm", 10.5)
    return a


# ================================================================== 06.03

def elf_load():
    # _echo as 07.01 builds it, the first build that has it (readelf -lW): LOAD off 0x1000 vaddr 0
    # filesz 0x909 R E; LOAD off 0x2000 vaddr 0x1000 filesz 0 memsz 0x20 RW; entry 0x90. The file
    # is 0x87c8 bytes when built in build/at/xv6/07.01 (the debug info records that directory).
    a = Art("f0603a", "The two LOAD program headers of _echo become the first two pages of the new address space", 270)
    a.text(24, 18, "build/user/_echo at 07.01, the file (not to scale)", "tm", 10.5)
    y0, h = 26, 36
    a.cell(24, y0, 72, h); a.text(60, y0 + 22, "ELF header", size=11, anchor="middle")
    a.cell(96, y0, 84, h, "a af"); a.text(138, y0 + 22, "phdrs: 2 LOAD", "ta", 11, "middle", 600)
    a.cell(180, y0, 36, h, "m fs")
    a.cell(216, y0, 132, h); a.text(282, y0 + 15, ".text .rodata", size=11, anchor="middle"); a.mono(282, y0 + 29, "0x909 bytes", "tm", 10, "middle")
    a.cell(348, y0, 36, h, "m fs")
    a.cell(384, y0, 232, h, "m fs"); a.text(500, y0 + 22, "symbols, section headers", "tm", 11, "middle")
    a.line(384, y0 - 4, 384, y0 + h + 4, "a")
    for x, s, anc in ((24, "0x0", "start"), (96, "0x40", "middle"), (216, "0x1000", "middle"), (348, "0x1909", "middle"),
                      (384, "0x2000", "start"), (616, "0x87c8", "end")):
        a.mono(x if anc != "start" or x == 24 else x + 4, y0 + h + 14, s, "tm", 10, anc)
    # memory
    a.text(616, 146, "the new user address space", "tm", 10.5, "end")
    m0, mh = 154, 60
    pages = [(24, "text, rodata", "R X U", "s f"), (134, "data, bss", "R W U", "s f"), (244, "guard page", "R W, no U", "s fs"),
             (354, "stack", "R W U", "s f")]
    for x, name, perm, cls in pages:
        a.cell(x, m0, 110, mh, cls)
        a.text(x + 55, m0 + 22, name, "tm" if "guard" in name else "t", 11.5, "middle", 600)
        a.mono(x + 55, m0 + 40, perm, "tm", 10.5, "middle")
    a.text(189, m0 + 54, "0x20 bytes, zeroed", "tm", 10, "middle")
    a.text(409, m0 + 54, "argv, then sp", "tm", 10, "middle")
    a.cell(464, m0, 152, mh, "m", dash=True)
    a.text(540, m0 + 34, "unmapped", "tm", 11, "middle")
    for x, s in ((24, "0x0"), (134, "0x1000"), (244, "0x2000"), (354, "0x3000"), (464, "0x4000")):
        a.mono(x, m0 + mh + 14, s, "tm", 10, "start" if x == 24 else "middle")
    a.text(464, m0 + mh + 28, "p->sz; sp starts here", "tm", 10, "middle")
    a.line(282, y0 + h + 20, 79, m0 - 4, "a", arrow=True)
    a.line(384, y0 + h + 20, 189, m0 - 4, "a", arrow=True)
    a.mono(180, 106, "LOAD: 0x909 bytes, R E", "ta", 10, "end")
    a.mono(302, 130, "LOAD: filesz 0, memsz 0x20, RW", "ta", 10)
    return a


def argv_stack():
    a = Art("f0603b", "The top of the stack page after exec(\"echo\", [\"echo\", \"a\", \"bb\", \"ccc\"])", 272)
    x0, w = 244, 160
    a.line(x0 - 8, 30, x0 + w, 30, "s")
    a.mono(x0 + w + 8, 34, "0x4000", "tm", 10.5)
    a.text(x0 + w + 54, 34, "the top of the stack page", "tm", 10.5)
    rows = [("0x3FF0", 22, "\"echo\\0\"", "str"), ("0x3FE0", 22, "\"a\\0\"", "str"), ("0x3FD0", 22, "\"bb\\0\"", "str"),
            ("0x3FC0", 22, "\"ccc\\0\"", "str"), ("0x3FB8", 12, "", "pad"),
            ("0x3FB0", 20, "0", "argv[4]"), ("0x3FA8", 20, "0x3FC0", "argv[3]"), ("0x3FA0", 20, "0x3FD0", "argv[2]"),
            ("0x3F98", 20, "0x3FE0", "argv[1]"), ("0x3F90", 20, "0x3FF0", "argv[0]")]
    y = 30
    ys = {}
    for addr, h, s, kind in rows:
        if kind == "pad":
            a.cell(x0, y, w, h, "m fs", dash=True)
        else:
            hot = kind == "argv[0]"
            a.cell(x0, y, w, h, "a af" if hot else "s f")
            a.mono(x0 + 10, y + h / 2 + 4, s, "ta" if hot else "t", 11.5)
            if kind.startswith("argv"):
                a.mono(x0 + w - 8, y + h / 2 + 4, kind, "ta" if hot else "tm", 10, "end")
            a.mono(x0 - 12, y + h / 2 + 4, addr, "ta" if hot else "tm", 10.5, "end")
        ys[kind if kind != "str" else s] = y + h / 2
        y += h
    strs = ["\"echo\\0\"", "\"a\\0\"", "\"bb\\0\"", "\"ccc\\0\""]
    for i, s in enumerate(strs):
        yp, yt = ys[f"argv[{i}]"], ys[s]
        o = 22 + (3 - i) * 16
        a.path(f"M{x0 + w} {yp} C {x0 + w + o} {yp}, {x0 + w + o} {yt}, {x0 + w + 2} {yt}", "m", arrow=True)
    a.text(484, 72, "the strings, each start", "tm", 10.5)
    a.text(484, 86, "rounded down to 16 bytes", "tm", 10.5)
    a.text(484, 186, "argv[]: argc + 1", "tm", 10.5)
    a.text(484, 200, "pointers, ending in 0", "tm", 10.5)
    # registers
    a.box(24, 140, 132, 102, "s fs", rx=6)
    a.mono(36, 158, "p->trapframe", "tm", 10.5)
    for i, (r, v) in enumerate((("epc", "0x90"), ("a0", "4"), ("a1", "0x3F90"), ("sp", "0x3F90"))):
        yy = 180 + i * 18
        a.mono(36, yy, r, "ta" if r == "sp" else "t", 11.5)
        a.mono(146, yy, v, "ta" if r == "sp" else "t", 11.5, "end")
    a.line(156, 234, 186, 234, "a", arrow=True)
    a.text(24, 262, "a0 = argc, a1 = argv; main(argc, argv) runs on this stack", "tm", 10.5)
    return a


# ================================================================== 06.04

def fork_copy():
    a = Art("f0604a", "init forks: the child gets a copy of every page and the same open files", 292)
    rows = [(16, "parent: init, pid 1", "a0 = 2", "the child's pid", False),
            (166, "child: pid 2", "a0 = 0", "fork returns 0", True)]
    for y, name, a0, note, child in rows:
        a.box(24, y, 416, 110, "m f", rx=10)
        a.text(36, y + 20, name, size=12, weight=600)
        a.text(40, y + 44, "user memory", "tm", 10.5)
        for i, pg in enumerate(("text", "data", "guard", "stack")):
            a.cell(40 + i * 46, y + 52, 42, 36, "s fs" if pg == "guard" else "s f")
            a.text(61 + i * 46, y + 74, pg, "tm" if pg == "guard" else "t", 10.5, "middle")
        a.text(238, y + 44, "trapframe", "tm", 10.5)
        a.box(238, y + 52, 108, 36, "a af" if child else "s f", rx=6)
        a.mono(250, y + 68, a0, "ta" if child else "t", 12, weight=600 if child else None)
        a.text(250, y + 82, note, "ta" if child else "tm", 10)
        a.mono(366, y + 30, "ofile[]", "tm", 10.5)
        for i in range(3):
            a.cell(366, y + 38 + i * 20, 60, 20, "s f")
            a.mono(376, y + 52 + i * 20, str(i), "tm", 10.5)
            a.line(426, y + 48 + i * 20, 478, 128 + (i + (3 if child else 0)) * 6, "m")
    a.line(129, 106, 129, 216, arrow=True)
    a.text(138, 146, "uvmcopy: a fresh copy", "tm", 10.5)
    a.text(138, 160, "of every page", "tm", 10.5)
    a.line(292, 106, 292, 216, arrow=True)
    a.text(300, 146, "copied whole,", "tm", 10.5)
    a.text(300, 160, "then a0 = 0", "tm", 10.5)
    a.text(480, 98, "shared, not copied", "tm", 10.5)
    a.box(480, 106, 136, 72, "s f", rx=6)
    a.mono(492, 124, "struct file", "tm", 10.5)
    a.text(492, 142, "console", size=12, weight=600)
    a.mono(492, 162, "ref 3 -> 6", size=11)
    a.text(480, 200, "filedup on each open fd;", "tm", 10.5)
    a.text(480, 214, "idup on the cwd inode", "tm", 10.5)
    return a


def exit_wait():
    a = Art("f0604b", "B exits: it stays a zombie until its parent waits, and its own child goes to init", 300)
    a.text(24, 18, "B's slot in proc[]", "tm", 10.5)
    pills = [(24, 86, "RUNNING", "s f", "t"), (262, 116, "ZOMBIE", "a af", "ta"), (530, 86, "UNUSED", "m f", "tm")]
    for x, w, s, cls, tc in pills:
        a.box(x, 34, w, 28, cls, rx=14)
        a.mono(x + w / 2, 52, s, tc, 11.5, "middle", 600)
    a.line(110, 48, 260, 48, arrow=True)
    a.mono(185, 40, "exit(3)", "t", 11, "middle")
    a.line(378, 48, 528, 48, arrow=True)
    a.text(453, 40, "A calls wait()", "t", 11, "middle")
    notes = [(185, ["closes every open file", "iput(cwd)", "C's parent = init", "wakeup(A)", "xstate = 3, sched()"], "tm"),
             (320, ["still holds its pid,", "xstate = 3, memory,", "trapframe, page table"], "ta"),
             (453, ["finds B in ZOMBIE", "copies 3 out to A", "freeproc(B)", "returns B's pid"], "tm")]
    for x, lines, cls in notes:
        for i, s in enumerate(lines):
            a.text(x, 82 + i * 14, s, cls, 10.5, "middle")
    # the tree
    a.text(24, 176, "parent pointers when B exits", "tm", 10.5)
    nodes = [(24, "init", "pid 1", "s f", "t"), (172, "A", "will wait for B", "s f", "t"), (320, "B", "ZOMBIE", "a af", "ta"),
             (468, "C", "still running", "s f", "t")]
    for x, n, sub, cls, tc in nodes:
        a.box(x, 188, 112, 40, cls, rx=8)
        a.text(x + 12, 205, n, tc, 12, weight=600, mono=n == "init")
        a.text(x + 12, 220, sub, "ta" if tc == "ta" else "tm", 10.5)
    a.line(172, 208, 138, 208, arrow=True)
    a.line(320, 208, 286, 208, arrow=True)
    a.line(468, 208, 434, 208, "m", dash=True)
    a.text(451, 202, "was", "tm", 10, "middle")
    a.path("M524 228 C 524 286, 80 286, 80 230", arrow=True)
    a.mono(302, 258, "reparent: C->parent = initproc", "t", 10.5, "middle")
    a.text(616, 176, "each arrow points at the parent", "tm", 10.5, "end")
    return a


# ================================================================== 06.05

def sbrk_heap():
    a = Art("f0605", "sbrk(8192) after exec of echo: two new pages, and the call returns the old end", 250)
    pw = 52
    def strip(y, heap):
        cells = ["text", "data", "guard", "stack"]
        for i, s in enumerate(cells):
            x = 24 + i * pw
            a.cell(x, y, pw, 36, "s fs" if s == "guard" else "s f")
            a.text(x + pw / 2, y + 22, s, "tm" if s == "guard" else "t", 11, "middle")
        end = 24 + 4 * pw
        if heap:
            for k in range(2):
                x = end + k * pw
                a.cell(x, y, pw, 36, "a af")
                a.text(x + pw / 2, y + 22, "heap", "ta", 11, "middle", 600)
            end += 2 * pw
        a.cell(end, y, 440 - end, 36, "m", dash=True)
        a.text((end + 440) / 2, y + 22, "unmapped", "tm", 11, "middle")
        a.cell(440, y, 88, 36, "s fs"); a.mono(484, y + 22, "TRAPFRAME", "t", 10.5, "middle")
        a.cell(528, y, 88, 36, "s fs"); a.mono(572, y + 22, "TRAMPOLINE", "t", 10.5, "middle")
        n = 7 if heap else 5
        labels = [(24 + k * pw, "0x%x000" % k if k else "0x0") for k in range(n)]
        for x, s in labels:
            a.mono(x, y + 50, s, "tm", 10, "start" if x == 24 else "middle")
        a.mono(440, y + 50, "0x3FFFFFE000", "tm", 10)
        a.mono(528, y + 50, "0x3FFFFFF000", "tm", 10)
        return end
    a.text(24, 22, "after exec", "tm", 10.5)
    e1 = strip(36, False)
    a.line(e1, 8, e1, 32, arrow=True)
    a.mono(e1 + 6, 18, "p->sz", "t", 10.5)
    a.mono(24, 108, "sbrk(8192)", "t", 11.5, weight=600)
    a.text(24, 124, "growproc: uvmalloc", "tm", 10.5)
    a.text(24, 138, "two zeroed pages, PTE_W", "tm", 10.5)
    e2 = strip(150, True)
    a.line(e2, 122, e2, 146, arrow=True)
    a.mono(e2 + 6, 132, "p->sz", "t", 10.5)
    a.line(232, 104, 232, 146, "a", arrow=True)
    a.mono(238, 112, "returns 0x4000, the old end", "ta", 10.5)
    a.text(440, 220, "growproc refuses to let", "tm", 10.5)
    a.text(440, 234, "sz + n pass TRAPFRAME", "tm", 10.5)
    return a


# ================================================================== 06.06

def ring():
    a = Art("f0606a", "A pipe's 512-byte ring: nread and nwrite only count up, and % 512 gives the position", 232)
    x0, x1 = 40, 600
    def bx(b):
        return x0 + b * (x1 - x0) / 512
    y, h = 70, 40
    a.fill(bx(0), y, bx(164) - bx(0), h, "af")
    a.fill(bx(376), y, bx(512) - bx(376), h, "af")
    for b in range(32, 512, 32):
        a.line(bx(b), y, bx(b), y + h, "m")
    a.cell(x0, y, x1 - x0, h, "s")
    a.line(bx(164), y, bx(164), y + h, "a")
    a.line(bx(376), y, bx(376), y + h, "a")
    a.text((bx(376) + bx(512)) / 2, y + 25, "oldest bytes", "ta", 11, "middle", 600)
    a.text((bx(0) + bx(164)) / 2, y + 25, "newest bytes", "ta", 11, "middle", 600)
    a.text((bx(164) + bx(376)) / 2, y + 25, "free", "tm", 11, "middle")
    a.mono(x0, y + h + 14, "data[0]", "tm", 10)
    a.mono(x1, y + h + 14, "data[511]", "tm", 10, "end")
    a.line(bx(376), 44, bx(376), 66, arrow=True)
    a.mono(bx(376), 22, "nread = 1400", "t", 11.5, "middle", 600)
    a.text(bx(376), 37, "1400 % 512 = 376: next byte to read", "tm", 10.5, "middle")
    a.line(bx(164), 140, bx(164), 114, arrow=True)
    a.mono(bx(164), 156, "nwrite = 1700", "t", 11.5, "middle", 600)
    a.text(bx(164), 171, "1700 % 512 = 164: next free slot", "tm", 10.5, "middle")
    a.text(40, 22, "nwrite - nread = 300 bytes waiting", "t", 11)
    a.mono(40, 37, "empty: nread == nwrite", "tm", 10)
    a.mono(40, 51, "full:  nwrite == nread + 512", "tm", 10)
    a.path(f"M{x1} {y + h + 22} C {x1} 226, {x0} 226, {x0} {y + h + 22}", "m", arrow=True)
    a.text(320, 222, "the byte after data[511] goes to data[0]", "tm", 10.5, "middle")
    return a


def pipe_sequence():
    a = Art("f0606b", "A reader that arrives first and a writer with 600 bytes: each side wakes the other's channel", 346)
    W, R = 196, 444
    a.text(W, 20, "writer", size=12, anchor="middle", weight=600)
    a.text(R, 20, "reader", size=12, anchor="middle", weight=600)
    a.line(W, 30, W, 338, "m")
    a.line(R, 30, R, 338, "m")
    def asleep(x, y1, y2, label):
        a.box(x - 6, y1, 12, y2 - y1, "m fs", rx=6)
        a.mono(x + (16 if x == R else -16), (y1 + y2) / 2 + 4, label, "tm", 10, "start" if x == R else "end")
    def ev(x, y, lines):
        a.circle(x, y - 4, 3.5, "s f")
        for i, (s, mono) in enumerate(lines):
            if x == R:
                a.text(x + 14, y + i * 14, s, "t" if i == 0 else "tm", 10.5, mono=mono)
            else:
                a.text(x - 14, y + i * 14, s, "t" if i == 0 else "tm", 10.5, "end", mono=mono)
    def wake(x1, x2, y, label, cls):
        a.line(x1, y, x2 + (-8 if x2 > x1 else 8), y, cls, arrow=True)
        a.mono((x1 + x2) / 2, y - 6, label, "ta" if cls == "a" else "tm", 10, "middle")
    ev(R, 48, [("read(p[0], buf, 512)", True), ("empty: sleep(&pi->nread)", True)])
    asleep(R, 70, 156, "asleep")
    ev(W, 92, [("write(p[1], buf, 600)", True), ("512 bytes in: full", False)])
    wake(W, R, 124, "wakeup(&pi->nread)", "a")
    ev(W, 142, [("sleep(&pi->nwrite)", True)])
    asleep(W, 150, 222, "asleep")
    ev(R, 170, [("wakes, copies 512 bytes out", False)])
    wake(R, W, 190, "wakeup(&pi->nwrite)", "a")
    ev(R, 208, [("read returns 512", True)])
    ev(W, 236, [("wakes, copies the last 88 in", False), ("write returns 600", True)])
    ev(R, 266, [("read returns 88", True), ("empty: sleep(&pi->nread)", True)])
    asleep(R, 286, 306, "")
    ev(W, 300, [("close(p[1]): writeopen = 0", True)])
    wake(W, R, 300, "wakeup(&pi->nread)", "s")
    ev(R, 322, [("empty, no writer left:", False), ("read returns 0, end of file", True)])
    return a


# ================================================================== 06.07

def lowest_fd():
    a = Art("f0607a", "close(1) then open(): fdalloc takes the lowest free slot, which is 1", 226)
    a.mono(24, 26, "p->ofile[]", "tm", 10.5)
    x0, cw = 160, 62
    for i in range(6):
        a.mono(x0 + i * cw + cw / 2, 26, str(i), "tm", 10.5, "middle")
    a.mono(x0 + 6 * cw + 42, 26, "6 .. 15", "tm", 10.5, "middle")
    rows = [(36, "the shell's child", ["console", "console", "console", "", "", ""], False),
            (100, "close(1)", ["console", "", "console", "", "", ""], True),
            (164, "open(\"f\", ...)", ["console", "f", "console", "", "", ""], True)]
    for y, label, cells, mono in rows:
        a.text(24, y + 20, label, "t", 11.5, mono=mono)
        for i, s in enumerate(cells):
            hot = y == 164 and i == 1
            a.cell(x0 + i * cw, y, cw, 30, "a af" if hot else ("s f" if s else "m f"))
            if s:
                a.text(x0 + i * cw + cw / 2, y + 19, s, "ta" if hot else "t", 12 if hot else 11, "middle",
                       600 if hot else None, mono=hot)
        a.cell(x0 + 6 * cw, y, 84, 30, "m f", dash=True)
    a.path("M191 160 C 200 140, 244 140, 253 160", arrow=True)
    a.text(262, 150, "fdalloc scans up from 0 and takes the first empty slot", "tm", 10.5)
    a.text(160, 214, "the program the child execs next writes to fd 1, and the bytes land in f", "tm", 10.5)
    return a


def nlink():
    a = Art("f0607b", "Two names for one inode: link and unlink move nlink, and the inode goes when it reaches 0", 252)
    # echo, ln and rm come with 07.03; on that disk a new file gets inode 16 (console is 15).
    cols = [("echo hello > a", [("a", "16"), None], "1", ["create(): nlink = 1"]),
            ("ln a b", [("a", "16"), ("b", "16")], "2", ["sys_link(): nlink++"]),
            ("rm a", [None, ("b", "16")], "1", ["sys_unlink(): zero the", "entry, nlink--"]),
            ("rm b", [None, None], "0", ["nlink 0 and not open:", "iput frees inode, blocks"])]
    for c, (cmd, ents, nl, notes) in enumerate(cols):
        x = 24 + c * 150
        a.mono(x, 22, cmd, "t", 11.5, weight=600)
        a.text(x, 44, "entries in /", "tm", 10)
        for i, e in enumerate(ents):
            ex = x + i * 70
            a.cell(ex, 52, 70, 26, "s f" if e else "m f")
            if e:
                a.mono(ex + 10, 69, e[0], "t", 11.5)
                a.mono(ex + 60, 69, e[1], "tm", 11, "end")
                a.line(ex + 35, 78, x + 52 + i * 36, 126, arrow=True)
            else:
                a.mono(ex + 35, 69, "inum 0", "tm", 10, "middle")
        gone = nl == "0"
        a.box(x, 128, 140, 70, "m fs" if gone else "s f", rx=6, dash=gone)
        a.mono(x + 12, 148, "inode 16", "tm" if gone else "t", 11.5, weight=600)
        a.mono(x + 12, 168, f"nlink {nl}", "ta", 12, weight=600)
        a.text(x + 12, 186, "freed" if gone else "data: hello", "tm", 10.5)
        for i, s in enumerate(notes):
            a.text(x, 220 + i * 14, s, "tm", 10.5)
    return a


# ================================================================== 07.01

def free_list():
    a = Art("f0701a", "malloc(100) on a fresh heap: the 4096-unit block from morecore is split, and the caller gets the tail", 252)
    a.text(616, 18, "1 unit = sizeof(Header) = 16 bytes; not to scale", "tm", 10, "end")
    def row(y, label, split):
        a.text(24, y - 10, label, "tm", 10.5)
        a.box(24, y, 76, 40, "s fs", rx=6)
        a.mono(36, y + 17, "base", "t", 11.5, weight=600)
        a.mono(36, y + 32, "size 0", "tm", 10)
        a.cell(150, y, 56, 40, "s fs")
        a.mono(178, y + 17, "size", "tm", 10, "middle")
        a.mono(178, y + 32, "4088" if split else "4096", "t", 11, "middle")
        if split:
            a.cell(206, y, 224, 40, "s f"); a.text(318, y + 25, "free", "tm", 11, "middle")
            a.cell(430, y, 56, 40, "a af"); a.mono(458, y + 17, "size", "ta", 10, "middle"); a.mono(458, y + 32, "8", "ta", 11, "middle", 600)
            a.cell(486, y, 130, 40, "a af"); a.text(551, y + 25, "112 bytes for you", "ta", 11, "middle", 600)
        else:
            a.cell(206, y, 410, 40, "s f"); a.text(411, y + 25, "4095 free units: 65520 bytes", "tm", 11, "middle")
        a.line(100, y + 14, 148, y + 14, arrow=True)
        a.path(f"M178 {y + 40} C 178 {y + 64}, 62 {y + 64}, 62 {y + 42}", arrow=True)
        a.mono(124, y + 8, "ptr", "tm", 10, "middle")
        a.mono(120, y + 66, "ptr", "tm", 10, "middle")
    row(44, "after morecore: sbrk(65536) gave one free block, and the list is base -> block -> base", False)
    row(156, "after malloc(100): (100 + 15) / 16 + 1 = 8 units, cut off the tail", True)
    a.text(206, 212, "bytes from the start of the block:", "tm", 10)
    a.mono(430, 212, "0xff80", "tm", 10, "middle")
    a.mono(616, 212, "0x10000", "tm", 10, "end")
    a.line(486, 240, 486, 200, "a", arrow=True)
    a.text(478, 240, "malloc returns the byte after the header", "ta", 10.5, "end")
    return a


def to_disk():
    # The 07.01 disk: echo is the only program, so the root directory is ., .., README 2, echo 3.
    a = Art("f0701b", "From user/echo.c to /echo on the disk, and back out through exec", 172)
    a.text(24, 22, "every user/*.c outside the library", "tm", 10.5)
    a.box(24, 30, 100, 28, "s f", rx=6); a.mono(74, 48, "user/echo.c", size=11, anchor="middle")
    a.line(124, 44, 168, 44, arrow=True); a.mono(146, 38, "gcc", "tm", 10, "middle")
    a.box(170, 30, 66, 28, "s f", rx=6); a.mono(203, 48, "echo.o", size=11, anchor="middle")
    a.text(24, 116, "the user library, linked into each program", "tm", 10.5)
    a.box(24, 124, 228, 28, "s fs", rx=6); a.mono(138, 142, "ulib.o usys.o printf.o umalloc.o", size=10.5, anchor="middle")
    a.box(266, 79, 120, 28, "s f", rx=6); a.mono(326, 97, "build/user/_echo", size=10.5, anchor="middle")
    a.path("M236 44 C 256 44, 248 86, 264 86", arrow=True)
    a.path("M252 138 C 262 138, 254 100, 264 100", arrow=True)
    a.mono(326, 124, "ld -T user.ld", "tm", 10, "middle")
    a.text(326, 138, "_main entry, text at 0", "tm", 10, "middle")
    a.line(386, 93, 418, 93, arrow=True); a.mono(402, 86, "mkfs", "tm", 10, "middle")
    a.text(420, 22, "fs.img, the root dir", "tm", 10.5)
    rows = [(".", "1"), ("..", "1"), ("README", "2"), ("echo", "3")]
    for i, (n, ino) in enumerate(rows):
        y = 30 + i * 18
        hot = n == "echo"
        a.cell(420, y, 96, 18, "a af" if hot else "s f")
        a.mono(428, y + 13, n, "ta" if hot else "t", 11, weight=600 if hot else None)
        a.mono(508, y + 13, ino, "ta" if hot else "tm", 10.5, "end")
    a.text(420, 124, "mkfs drops the _", "tm", 10)
    a.text(420, 138, "and adds README", "tm", 10)
    a.box(536, 79, 80, 28, "s f", rx=6); a.mono(576, 97, "exec(\"echo\")", size=10, anchor="middle")
    a.line(536, 93, 520, 93, arrow=True)
    a.text(576, 124, "namei finds", "tm", 10, "middle")
    a.text(576, 138, "inode 3", "tm", 10, "middle")
    return a


# ================================================================== 07.02

def shell_cycle():
    a = Art("f0702a", "One command, echo hi: the shell forks, the child becomes echo, and the shell waits", 230)
    a.text(24, 30, "the shell", "tm", 10.5)
    y1 = 40
    a.cell(24, y1, 112, 24, "s f"); a.mono(80, y1 + 16, "getcmd(buf)", "t", 10.5, "middle")
    a.cell(136, y1, 404, 24, "m fs", dash=True); a.mono(338, y1 + 16, "wait(0): asleep", "tm", 10.5, "middle")
    a.cell(540, y1, 76, 24, "s f"); a.text(578, y1 + 16, "next prompt", "t", 10.5, "middle")
    a.circle(136, y1 + 12, 4, "s f")
    y2 = 150
    a.text(160, y2 - 10, "its child, one pid throughout", "tm", 10.5)
    a.cell(160, y2, 220, 24, "s fs"); a.text(270, y2 + 16, "a copy of the shell", "t", 10.5, "middle")
    a.cell(380, y2, 160, 24, "a af"); a.mono(460, y2 + 16, "echo", "ta", 11.5, "middle", 600)
    a.path(f"M136 {y1 + 24} C 136 110, 140 {y2 + 12}, 158 {y2 + 12}", arrow=True)
    a.mono(128, 112, "fork1()", "t", 10.5, "end")
    a.line(540, y2, 540, y1 + 26, arrow=True)
    a.mono(532, 108, "exit(0)", "t", 10.5, "end")
    a.text(532, 122, "wait returns its pid", "tm", 10.5, "end")
    ticks = [(212, "parsecmd(buf)", 194, "t"), (300, "runcmd(): EXEC", 210, "t"), (380, "exec(\"echo\", argv)", 194, "ta"),
             (470, "write(1, \"hi\", 2)", 210, "t")]
    for x, s, ty, cls in ticks:
        a.line(x, y2 + 24, x, ty - 12 if ty == 194 else ty - 12, "a" if cls == "ta" else "m")
        a.mono(x, ty, s, cls, 10.5, "middle", 600 if cls == "ta" else None)
    return a


def pipe_fds():
    a = Art("f0702b", "echo hi | wc: the descriptor tables just before each child execs", 282)
    cols = [(24, "left child: echo hi", ["close(1); dup(p[1])", "close(p[0]); close(p[1])", "exec(\"echo\", ...)"],
             ["console", "pipe write end", "console", "", ""], 1),
            (230, "right child: wc", ["close(0); dup(p[0])", "close(p[0]); close(p[1])", "exec(\"wc\", ...)"],
             ["pipe read end", "console", "console", "", ""], 0),
            (436, "runcmd, the parent", ["pipe(p): p[0] = 3, p[1] = 4", "fork twice, then", "close(p[0]); close(p[1])"],
             ["console", "console", "console", "", ""], None)]
    for x, head, ops, slots, hot in cols:
        a.text(x, 20, head, "t", 11.5, weight=600)
        for i, s in enumerate(ops):
            a.mono(x, 38 + i * 14, s, "tm", 10)
        for i, s in enumerate(slots):
            y = 80 + i * 22
            h = i == hot
            a.cell(x, y, 180, 22, "a af" if h else ("s f" if s else "m f"))
            a.mono(x + 10, y + 15, str(i), "ta" if h else "tm", 10.5)
            a.text(x + 30, y + 15, s if s else "closed", "ta" if h else ("t" if s else "tm"), 11, weight=600 if h else None)
    a.box(60, 214, 320, 36, "s f", rx=8)
    a.text(130, 236, "write end", "t", 11.5, "middle", 600)
    a.text(310, 236, "read end", "t", 11.5, "middle", 600)
    a.line(178, 232, 262, 232, arrow=True)
    a.mono(220, 226, "512 bytes", "tm", 10, "middle")
    a.path("M24 113 C 8 113, 8 232, 58 232", "a", arrow=True)
    a.path("M410 91 C 424 91, 424 232, 382 232", "a", arrow=True)
    a.text(436, 210, "then wait(0) twice; it", "tm", 10.5)
    a.text(436, 224, "holds no pipe end, so wc", "tm", 10.5)
    a.text(436, 238, "sees end of file when", "tm", 10.5)
    a.text(436, 252, "echo exits", "tm", 10.5)
    a.text(60, 272, "each pipe end is now open in exactly one process", "tm", 10.5)
    return a


# ================================================================== 07.03

def ls_loop():
    a = Art("f0703", "ls reads the directory 16 bytes at a time, then stats each name it finds", 262)
    a.text(24, 20, "the file \".\" (the root directory)", "tm", 10.5)
    a.mono(58, 40, "off", "tm", 10, "end"); a.mono(98, 40, "inum", "tm", 10, "end"); a.mono(110, 40, "name", "tm", 10)
    # The 07.03 disk as ls shows it: wc is inode 14 at offset 224, console 15 at 240.
    rows = [("0", "1", "."), ("16", "1", ".."), ("32", "2", "README"), ("48", "3", "cat"), ("", "", "..."),
            ("224", "14", "wc"), ("240", "15", "console"), ("256", "0", "skipped"), ("", "", "..."), ("1008", "0", "skipped")]
    for i, (off, ino, name) in enumerate(rows):
        y = 46 + i * 18
        hot = name == "README"
        empty = ino == "0"
        a.cell(24, y, 182, 18, "a af" if hot else ("m fs" if not off or empty else "s f"))
        if off:
            a.mono(58, y + 13, off, "ta" if hot else "tm", 10, "end")
            a.mono(98, y + 13, ino, "ta" if hot else ("tm" if empty else "t"), 10.5, "end")
            a.text(110, y + 13, name, "ta" if hot else ("tm" if empty else "t"), 10.5 if empty else 11, weight=600 if hot else None,
                   mono=not empty)
        else:
            a.mono(110, y + 13, name, "tm", 10.5)
    a.text(24, 242, "each entry is a struct dirent: a 2-byte inum and a 14-byte name; inum 0 means no file", "tm", 10.5)
    # the steps
    steps = [(34, 40, ["read(fd, &de, 16)", "de = {2, \"README\"}"]), (90, 24, ["buf = \"./README\""]),
             (130, 40, ["stat(buf, &st)", "open, fstat, close"]), (186, 24, ["type 2, ino 2, size 480"])]
    for y, h, lines in steps:
        a.box(246, y, 164, h, "s f", rx=6)
        for i, s in enumerate(lines):
            a.text(256, y + 16 + i * 15, s, "t" if i == 0 else "tm", 10.5 if i == 0 else 10, mono=i == 0 or "\"" in s)
    for y1, y2 in ((74, 88), (114, 128), (170, 184)):
        a.line(328, y1, 328, y2, arrow=True)
    a.path("M206 91 C 226 91, 226 50, 244 50", "a", arrow=True)
    a.text(328, 226, "repeat until read() is short", "tm", 10, "middle")
    # output
    a.text(440, 20, "what ls prints", "tm", 10.5)
    a.box(440, 30, 176, 106, "s fs", rx=6)
    out = [(".", "1 1 1024", False), ("..", "1 1 1024", False), ("README", "2 2 480", True), ("...", "", False),
           ("console", "3 15 0", False)]
    for i, (n, rest, hot) in enumerate(out):
        y = 50 + i * 18
        a.mono(450, y, n, "ta" if hot else ("tm" if n == "..." else "t"), 10, weight=600 if hot else None)
        if rest:
            a.mono(450 + 15 * 6, y, rest, "ta" if hot else "t", 10, weight=600 if hot else None)
    a.path("M410 198 C 430 198, 432 86, 438 86", "a", arrow=True)
    a.text(450, 156, "fmtname pads each name", "tm", 10.5)
    a.text(450, 170, "to 14 characters", "tm", 10.5)
    return a


FIGS = [
    ("06", "06.01-trapframe", trapframe), ("06", "06.01-round-trip", round_trip),
    ("06", "06.02-syscall-path", syscall_path),
    ("06", "06.03-elf-load", elf_load), ("06", "06.03-argv-stack", argv_stack),
    ("06", "06.04-fork-copy", fork_copy), ("06", "06.04-exit-wait", exit_wait),
    ("06", "06.05-sbrk-heap", sbrk_heap),
    ("06", "06.06-ring", ring), ("06", "06.06-sleep-wake", pipe_sequence),
    ("06", "06.07-lowest-fd", lowest_fd), ("06", "06.07-nlink", nlink),
    ("07", "07.01-free-list", free_list), ("07", "07.01-to-disk", to_disk),
    ("07", "07.02-fork-exec-wait", shell_cycle), ("07", "07.02-pipe-fds", pipe_fds),
    ("07", "07.03-ls-loop", ls_loop),
]


def main():
    dirs = {d[:2]: os.path.join(LESSONS, d) for d in os.listdir(LESSONS) if d[:2].isdigit()}
    only = sys.argv[1:]
    out = []
    for mid, name, fn in FIGS:
        if only and not any(name.startswith(o) for o in only):
            continue
        target = os.path.join(dirs[mid], "figures")
        os.makedirs(target, exist_ok=True)
        path = os.path.join(target, name + ".svg")
        svg = fn().svg()
        svg.encode("ascii")
        with open(path, "w") as f:
            f.write(svg)
        out.append(path)
    print("\n".join(out))


if __name__ == "__main__":
    main()
