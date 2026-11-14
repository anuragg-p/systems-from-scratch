from figlib import Fig, write, tw

MOD = "04-processes"


def kstacks():
    f = Fig("f0401a", "Kernel stacks and guard pages under the trampoline", 316)
    f.text(150, 18, "page at", "tm", 10.5, "end")
    f.text(170, 18, "kernel page table, top of the address space", "tm", 10.5)
    rows = [("0x3ffffff000", "trampoline", "s fs"),
            ("0x3fffffe000", "not mapped", "gap"),
            ("0x3fffffd000", "proc[0] kernel stack", "s f"),
            ("0x3fffffc000", "guard page: not mapped", "gap"),
            ("0x3fffffb000", "proc[1] kernel stack", "s f"),
            ("0x3fffffa000", "guard page: not mapped", "gap"),
            (None, "...", "dots"),
            ("0x3ffff7f000", "proc[63] kernel stack", "s f"),
            ("0x3ffff7e000", "guard page: not mapped", "gap")]
    y0, rh, x, w = 28, 28, 166, 176
    ys = {}
    for i, (addr, name, cls) in enumerate(rows):
        y = y0 + i * rh
        ys[i] = y
        if cls == "dots":
            f.text(x + w / 2, y + 18, "...", "tm", 12, "middle")
            continue
        if cls == "gap":
            f.rect(x + 2, y + 2, w - 4, rh - 4, "m", 0, dash=True)
            f.text(x + w / 2, y + 18, name, "tm", 10.5, "middle")
        else:
            f.rect(x, y, w, rh, cls, 0)
            f.text(x + w / 2, y + 18, name, "t", 11.5, "middle", None, name == "trampoline")
        f.text(150, y + 18, addr, "tm", 10.5, "end", None, True)
    # proc[0] annotations
    top = ys[2]
    ax = x + w + 14
    f.line(ax + 8, top, x + w + 3, top, "s", arrow=True)
    f.text(ax + 14, top + 4, "context.sp = p->kstack + 4096", "t", 10.5, mono=True)
    f.text(ax + 14, top + 19, "one past the top: the first push goes below it", "tm", 10.5)
    f.line(x + w - 14, top + 6, x + w - 14, top + 22, "m", arrow=True)
    # overflow
    g = ys[3]
    f.path(f"M{x + 16} {top + 8} L{x + 16} {g + 16}", "a", arrow=True)
    f.text(ax + 14, g + 26, "an overflow lands here and page-faults,", "ta", 10.5)
    f.text(ax + 14, g + 41, "instead of writing into proc[1]'s stack", "ta", 10.5)
    f.line(ax + 8, g + 14, x + w + 3, g + 14, "a", arrow=True)
    f.text(x, 296, "KSTACK(p) = TRAMPOLINE - (p + 1) * 2 * PGSIZE", "t", 11, mono=True)
    f.text(x, 311, "64 slots, 8192 bytes apart: one stack page, one guard page", "tm", 10.5)
    return f


def states():
    f = Fig("f0401b", "Process states and who moves a slot between them", 266)
    nodes = {
        "UNUSED": (16, 70, 96), "USED": (176, 70, 84), "RUNNABLE": (322, 70, 104), "RUNNING": (520, 70, 104),
        "SLEEPING": (418, 168, 104), "ZOMBIE": (16, 200, 96),
    }
    H = 32
    for n, (x, y, w) in nodes.items():
        acc = n == "RUNNING"
        f.rect(x, y, w, H, "a af" if acc else "s f", 16)
        f.text(x + w / 2, y + 20, n, "ta" if acc else "t", 11.5, "middle", 600, True)

    def lab(x, y, s, anchor="middle"):
        f.text(x, y, s, "tm", 10.5, anchor, None, True)
    # UNUSED -> USED
    f.line(112, 86, 174, 86, "s", arrow=True); lab(143, 62, "allocproc")
    # USED -> RUNNABLE
    f.line(260, 86, 320, 86, "s", arrow=True); lab(290, 50, "kfork,"); lab(290, 62, "userinit")
    # RUNNABLE <-> RUNNING
    f.line(426, 80, 518, 80, "s", arrow=True); lab(472, 62, "scheduler")
    f.line(518, 94, 428, 94, "s", arrow=True); lab(472, 116, "yield")
    # RUNNING -> SLEEPING
    f.path("M548 102 C 548 140, 540 184, 524 184", "s", arrow=True); lab(554, 146, "sleep", "start")
    # SLEEPING -> RUNNABLE
    f.path("M418 184 C 380 184, 372 140, 372 104", "s", arrow=True); lab(366, 150, "wakeup, kkill", "end")
    # RUNNING -> ZOMBIE
    f.path("M600 102 L600 232 L114 232", "s", arrow=True); lab(358, 250, "kexit")
    lab(300, 226, "")
    # ZOMBIE -> UNUSED
    f.line(64, 198, 64, 104, "s", arrow=True); lab(72, 146, "kwait: freeproc", "start")
    f.text(132, 210, "every move is made", "tm", 10.5)
    f.text(132, 224, "holding p->lock", "tm", 10.5, mono=True)
    return f


def timeline():
    f = Fig("f0402a", "Two swtch calls, and the lock that crosses them", 286)
    lanes = [(70, "process A", "A's kernel stack"), (150, "scheduler()", "the hart's boot stack"),
             (230, "process B", "B's kernel stack")]
    x0 = 150
    for y, name, sub in lanes:
        f.text(24, y - 2, name, "t", 12, weight=600, mono=name.endswith(")"))
        f.text(24, y + 13, sub, "tm", 10.5)
        f.line(x0, y, 620, y, "m", dash=True)
    # lock bands (behind)
    xa, xs1, xra, xlb, xs2, xrb = 200, 236, 330, 370, 420, 520
    f.rect(xa, 102, xra - xa, 18, "a af", 4)
    f.text((xs1 + xra) / 2 + 2, 115, "A->lock held", "ta", 10.5, "middle", 600, True)
    f.rect(xlb, 182, xrb - xlb, 18, "a af", 4)
    f.text((xs2 + xrb) / 2, 195, "B->lock held", "ta", 10.5, "middle", 600, True)
    # running segments
    f.add(f'<line class="s" x1="{x0}" y1="70" x2="{xs1}" y2="70" stroke-width="3" stroke-linecap="round"/>')
    f.add(f'<line class="s" x1="{xs1}" y1="150" x2="{xs2}" y2="150" stroke-width="3" stroke-linecap="round"/>')
    f.add(f'<line class="s" x1="{xs2}" y1="230" x2="620" y2="230" stroke-width="3" stroke-linecap="round"/>')
    # events
    f.line(xa, 62, xa, 78, "s")
    f.text(xa, 52, "yield(): lock A, RUNNABLE", "t", 10.5, "middle", None, True)
    f.line(xs1, 74, xs1, 146, "s", arrow=True)
    f.text(xs1 + 6, 92, "swtch", "t", 10.5, "start", 600, True)
    f.text(xs1 - 6, 92, "sched()", "tm", 10.5, "end", None, True)
    f.line(xra, 142, xra, 158, "s")
    f.text(xra, 174, "release A", "t", 10.5, "middle", None, True)
    f.line(xlb, 142, xlb, 158, "s")
    f.text(xlb, 136, "lock B, RUNNING", "t", 10.5, "middle", None, True)
    f.line(xs2, 154, xs2, 226, "s", arrow=True)
    f.text(xs2 + 6, 172, "swtch", "t", 10.5, "start", 600, True)
    f.line(xrb, 222, xrb, 238, "s")
    f.text(xrb, 254, "yield() returns: release B", "t", 10.5, "middle", None, True)
    f.text(620, 220, "B runs", "tm", 10.5, "end")
    f.text(x0, 278, "time ->", "tm", 10.5)
    return f


def swtch_regs():
    f = Fig("f0402b", "swtch: fourteen stores, fourteen loads, ret", 304)
    regs = ["ra", "sp"] + [f"s{i}" for i in range(12)]
    y0, rh = 46, 14.5
    cols = [(70, "*a0: the old context", "where this thread parks"), (262, "the hart's registers", ""),
            (454, "*a1: the new context", "where the next one parked")]
    for cx, title, sub in cols:
        f.text(cx + 58, 18, title, "t", 11.5, "middle", 600, title.startswith("*"))
        if sub:
            f.text(cx + 58, 33, sub, "tm", 10.5, "middle")
    for i, r in enumerate(regs):
        y = y0 + i * rh
        for cx, _, _ in cols:
            acc = cx == 454 and r == "ra"
            f.rect(cx, y, 116, rh, "a af" if acc else ("s fs" if cx == 262 else "s f"), 0)
            f.text(cx + 58, y + 11, r, "ta" if acc else "t", 10.5, "middle", 600 if acc else None, True)
        f.text(cx_off := 64, y + 11, str(i * 8), "tm", 9.5, "end", None, True)
        f.text(576, y + 11, str(i * 8), "tm", 9.5, "start", None, True)
    mid = y0 + 7 * rh
    f.line(258, mid, 190, mid, "s", arrow=True)
    f.text(224, mid - 8, "sd", "t", 11, "middle", 600, True)
    f.line(450, mid, 382, mid, "s", arrow=True)
    f.text(416, mid - 8, "ld", "t", 11, "middle", 600, True)
    yb = y0 + 14 * rh + 26
    f.text(320, yb, "then ret: pc = the ra just loaded,", "ta", 11, "middle")
    f.text(320, yb + 16, "just after the new thread's own call to swtch", "ta", 11, "middle")
    return f


def interleave(broken):
    title = "The lost wakeup" if broken else "The order sleep uses"
    f = Fig("f0403a" if broken else "f0403b", title, 312 if broken else 362)
    cx = (40, 340)
    f.text(cx[0], 20, "hart 0: virtio_disk_rw() sleeping on b", "t", 11.5, weight=600)
    f.text(cx[1], 20, "hart 1: virtio_disk_intr()", "t", 11.5, weight=600)
    if broken:
        f.text(cx[0], 35, "if sleep let go of lk before taking p->lock", "tm", 10.5)
        steps = [
            (0, "acquire(&disk.vdisk_lock)", None),
            (0, "b->disk == 1, so sleep(b, lk)", None),
            (0, "release(lk)", "win"),
            (1, "acquire(&disk.vdisk_lock)", None),
            (1, "b->disk = 0", None),
            (1, "wakeup(b): nobody is SLEEPING", "acc"),
            (1, "release(&disk.vdisk_lock)", None),
            (0, "acquire(&p->lock)", "winend"),
            (0, "p->state = SLEEPING; sched()", None),
            (0, "asleep on b; nothing will wake it", "tm"),
        ]
    else:
        f.text(cx[0], 35, "as sleep is written: p->lock first, then release(lk)", "tm", 10.5)
        steps = [
            (0, "acquire(&disk.vdisk_lock)", None),
            (0, "b->disk == 1, so sleep(b, lk)", None),
            (0, "acquire(&p->lock)", None),
            (0, "release(lk)", None),
            (1, "acquire(&disk.vdisk_lock)", None),
            (1, "b->disk = 0", None),
            (1, "wakeup(b): acquire(&p->lock)", "spin"),
            (0, "p->state = SLEEPING; sched()", None),
            (0, "scheduler: release(&p->lock)", "spinend"),
            (1, "SLEEPING, chan == b: RUNNABLE", None),
            (1, "release both locks", None),
            (0, "later: sleep returns, b->disk is 0", "tm"),
        ]
    y0, rh = 62, 25
    ylast = y0 + (len(steps) - 1) * rh
    win = [i for i, s in enumerate(steps) if s[2] in ("win", "winend")]
    if win:
        ya, yb = y0 + win[0] * rh, y0 + win[1] * rh
        f.rect(16, ya + 8, 608, yb - ya - 16, "fs", 6, sw=False)
        f.text(620, ya + 26, "the window", "tm", 10.5, "end")
    for c in cx:
        f.line(c + 4, y0 - 10, c + 4, ylast + 10, "m")
    spin = [i for i, s in enumerate(steps) if s[2] in ("spin", "spinend")]
    if spin:
        ya, yb = y0 + spin[0] * rh, y0 + spin[1] * rh
        f.rect(cx[1] - 1, ya + 6, 10, yb - ya - 12, "a af", 3)
        f.text(cx[1] + 20, ya + 20, "spins: hart 0 holds p->lock", "ta", 10.5)
        f.text(cx[1] + 20, ya + 35, "until it is off this stack", "ta", 10.5)
    for i, (col, s, kind) in enumerate(steps):
        y = y0 + i * rh
        c = cx[col]
        acc = kind in ("acc",)
        f.circle(c + 4, y - 4, 3.5, "a fa" if acc else ("s f" if kind != "tm" else "m f"))
        cls = "ta" if acc else ("tm" if kind == "tm" else "t")
        f.text(c + 18, y, s, cls, 11, mono=kind != "tm", weight=600 if acc else None)
    return f


def preempt():
    f = Fig("f0404a", "A's kernel stack while a tick has it switched out", 318)
    x, w = 40, 214
    f.text(x, 18, "A's kernel stack", "t", 11.5, weight=600)
    f.text(x + w, 18, "p->kstack + 4096", "tm", 10, "end", None, True)
    frames = [(30, 42, "the interrupted kernel code", "a long system call, say", "s f"),
              (72, 52, "kernelvec's frame", "256 bytes: ra, gp, tp, t0-t6, a0-a7", "s f"),
              (124, 46, "kerneltrap()", "locals: sepc, sstatus", "a af"),
              (170, 30, "yield()", None, "s f"),
              (200, 40, "sched()", "local: intena", "s f")]
    for y, h, name, sub, cls in frames:
        f.rect(x, y, w, h, cls, 0)
        acc = cls.startswith("a")
        if sub:
            f.text(x + 12, y + h / 2 - 2, name, "ta" if acc else "t", 11.5, None, 600 if acc else None, name.endswith(")"))
            f.text(x + 12, y + h / 2 + 13, sub, "ta" if acc else "tm", 10.5, None, None, sub.startswith("locals") or sub.startswith("local"))
        else:
            f.text(x + 12, y + h / 2 + 4, name, "t", 11.5, None, None, True)
    f.rect(x, 240, w, 30, "m", 0, dash=True)
    f.text(x + w / 2, 259, "free", "tm", 10.5, "middle")
    f.line(x - 8, 34, x - 8, 230, "m", arrow=True)
    # context pointer
    f.rect(x, 282, 120, 26, "s fs", 6)
    f.text(x + 60, 299, "A->context.sp", "t", 10.5, "middle", None, True)
    f.path(f"M{x + 120} 295 C {x + 170} 295, {x + w + 20} 282, {x + w + 20} 250 L{x + w + 20} 240 L{x + w + 4} 240", "s", arrow=True)
    # steps
    sx = 300
    steps = ["the tick: trap into kernelvec on A's stack",
             "kernelvec saves registers, calls kerneltrap()",
             "kerneltrap saves sepc, sstatus; devintr() is 2",
             "yield(), sched(), swtch to the scheduler",
             "other threads run; their traps overwrite sepc",
             "the scheduler picks A: swtch back, yield returns",
             "kerneltrap writes sepc and sstatus back",
             "kernelvec restores; sret resumes A where it was"]
    for i, s in enumerate(steps):
        y = 40 + i * 33
        acc = i in (2, 6)
        f.circle(sx + 10, y - 4, 10, "a af" if acc else "s f")
        f.text(sx + 10, y, str(i + 1), "ta" if acc else "t", 10.5, "middle", 600, True)
        f.text(sx + 28, y, s, "ta" if acc else "t", 11)
    return f


FIGS = [
    ("04.01-kernel-stacks", kstacks),
    ("04.01-states", states),
    ("04.02-two-swtches", timeline),
    ("04.02-swtch-registers", swtch_regs),
    ("04.03-lost-wakeup", lambda: interleave(True)),
    ("04.03-sleep-order", lambda: interleave(False)),
    ("04.04-preempted-stack", preempt),
]

if __name__ == "__main__":
    for name, fn in FIGS:
        print(write(MOD, name, fn()))
