from figlib import Fig, write, tw

MOD = "03-traps"


def frame():
    f = Fig("f0301a", "kernelvec's 256-byte frame on the kernel stack", 252)
    f.text(24, 22, "the frame kernelvec pushes: 32 slots of 8 bytes, lowest address first", "tm", 11)
    row1 = ["ra", "sp", "gp", "tp", "t0", "t1", "t2", "s0", "s1", "a0", "a1", "a2", "a3", "a4", "a5", "a6"]
    row2 = ["a7", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10", "s11", "t3", "t4", "t5", "t6", ""]
    empty = {"sp", "s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10", "s11", ""}
    x0, cw, ch = 60, 35, 34
    for r, (y, names) in enumerate(((52, row1), (136, row2))):
        for i, n in enumerate(names):
            x = x0 + i * cw
            off = (r * 16 + i) * 8
            if n == "tp":
                f.rect(x, y, cw, ch, "a af", 0)
                f.text(x + cw / 2, y + 21, n, "ta", 11.5, "middle", 600, True)
            elif n in empty:
                f.rect(x + 2, y + 2, cw - 4, ch - 4, "m", 0, dash=True)
                if n:
                    f.text(x + cw / 2, y + 21, n, "tm", 10, "middle", None, True)
            else:
                f.rect(x, y, cw, ch, "s f", 0)
                f.text(x + cw / 2, y + 21, n, "t", 11.5, "middle", None, True)
            f.text(x + cw / 2, y + ch + 13, str(off), "tm", 9.5, "middle", None, True)
    f.text(50, 73, "sp", "t", 12, "end", 600, True)
    f.text(50, 157, "+128", "tm", 10.5, "end", None, True)
    xend = x0 + 16 * cw
    f.line(xend, 124, xend, 134, "s")
    f.text(xend, 120, "sp + 256: the interrupted code's sp", "tm", 10.5, "end")
    tpx = x0 + 3 * cw + cw / 2
    f.text(tpx - 12, 114, "saved, never loaded back: tp is the hart id", "ta", 10.5)
    f.line(tpx, 100, tpx, 104, "a")
    f.brace_h(x0 + cw + 2, x0 + 11 * cw - 2, 198, "m")
    f.text(x0 + 6 * cw, 214, "left empty: s0-s11 are callee-saved, so kerneltrap() saves the ones it uses", "tm", 10.5, "middle")
    ly = 240
    f.rect(60, ly - 10, 12, 12, "s f", 0); f.text(80, ly, "saved and restored", "tm", 11)
    f.rect(206, ly - 10, 12, 12, "a af", 0); f.text(226, ly, "saved only", "tm", 11)
    f.rect(316, ly - 10, 12, 12, "m", 0, dash=True); f.text(336, ly, "not saved", "tm", 11)
    return f


def scause():
    f = Fig("f0301b", "How devintr reads scause", 282)
    f.text(24, 22, "scause, 64 bits", "tm", 11)
    f.text(75, 40, "63", "tm", 10, "middle", None, True)
    f.text(114, 40, "62", "tm", 10, "start", None, True)
    f.text(596, 40, "0", "tm", 10, "end", None, True)
    f.rect(40, 46, 70, 30, "a af", 0)
    f.text(75, 65, "interrupt", "ta", 11, "middle", 600)
    f.rect(110, 46, 490, 30, "s f", 0)
    f.text(355, 65, "cause code", "t", 12, "middle")
    f.path("M75 76 L75 90 M75 90 L360 90 M360 90 L360 100", "m")
    f.line(75, 90, 75, 100, "m")
    f.text(40, 116, "bit 63 = 1: an interrupt", "t", 12, weight=600)
    f.text(345, 116, "bit 63 = 0: an exception", "t", 12, weight=600)
    items = [(128, "0x8000000000000005", "timer: devintr() returns 2", "clockintr()"),
             (184, "0x8000000000000009", "device, via the PLIC: returns 1", "plic_claim(), then the driver")]
    for y, val, what, call in items:
        f.rect(40, y, 270, 46, "s f", 6)
        f.text(52, y + 18, val, "t", 11.5, mono=True)
        f.text(52, y + 36, what, "tm", 11)
    codes = [("0x8", "ecall from user mode"), ("0xc", "instruction page fault"), ("0xd", "load page fault"),
             ("0xf", "store page fault")]
    for i, (c, what) in enumerate(codes):
        y = 140 + i * 19
        f.text(345, y, c, "t", 11.5, mono=True)
        f.text(385, y, what, "tm", 11)
    f.rect(345, 214, 255, 16, "fs", 4, sw=False)
    f.text(352, 226, "devintr() returns 0: unexpected() panics", "t", 11)
    f.line(24, 248, 616, 248, "m")
    f.text(40, 268, "sepc", "t", 11.5, mono=True, weight=600)
    f.text(80, 268, "the instruction that trapped", "tm", 11)
    f.text(345, 268, "stval", "t", 11.5, mono=True, weight=600)
    f.text(390, 268, "the bad address, for a page fault", "tm", 11)
    return f


def sawtooth():
    f = Fig("f0302a", "time against stimecmp", 286)
    X0, PX, Y0, PY = 82, 112, 186, 32

    def X(t):
        return X0 + t * PX

    def Y(v):
        return Y0 - v * PY
    d = [0.05, 0.35, 0.05, 0.05]
    cross = [1.0]
    for k in range(3):
        cross.append(cross[-1] + d[k] + 1)
    tend = 4.58
    f.line(X0 - 8, 190, X(tend) + 6, 190, "m", arrow=True)
    f.text(X(tend) + 6, 205, "real time", "tm", 10.5, "end")
    f.text(X0 - 8, 30, "counts", "tm", 10.5)
    # time: a straight line
    f.line(X(0), Y(0), X(tend), Y(tend), "s")
    f.text(X(tend) - 4, Y(tend) - 8, "time", "t", 12, "end", 600, True)
    # stimecmp: steps
    pts = [(X(0), Y(1))]
    for k, c in enumerate(cross):
        w = c + d[k]
        pts.append((X(w), Y(c)))
        if k < 3:
            pts.append((X(w), Y(cross[k + 1])))
    pts[-1] = (X(tend), pts[-1][1])
    dd = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    f.path(dd, "a")
    f.text(X(0) + 4, Y(1) - 8, "stimecmp", "ta", 12, weight=600, mono=True)
    # one deadline's distance
    w0 = cross[0] + d[0]
    yy = Y(cross[1]) - 12
    f.line(X(w0), yy, X(cross[1]), yy, "m", arrow=True, start=True)
    f.text((X(w0) + X(cross[1])) / 2, yy - 6, "+1000000 = 0.1 s", "tm", 10.5, "middle", None, True)
    # pending waveform
    base, high = 238, 222
    f.text(X0 - 8, base - 3, "pending", "tm", 10.5, "end")
    wp = [f"M{X(0):.1f} {base}"]
    for k, c in enumerate(cross):
        wp.append(f"L{X(c):.1f} {base} L{X(c):.1f} {high} L{X(c + d[k]):.1f} {high} L{X(c + d[k]):.1f} {base}")
    wp.append(f"L{X(tend):.1f} {base}")
    f.path(" ".join(wp), "s")
    for k, c in enumerate(cross):
        f.line(X(c), Y(c), X(c), high - 4, "m", dash=True)
        f.text(X(c + d[k]), 256, f"ticks {k + 1}", "tm", 10, "middle", None, True)
    f.text(X0 - 8, 256, "on hart 0", "tm", 10.5, "end")
    f.text(X(cross[1] + d[1] / 2), 276, "taken late (interrupts were off): the next deadline counts from then", "tm", 10.5, "middle")
    return f


def storm():
    f = Fig("f0302b", "A timer interrupt that is never cleared", 180)
    f.text(24, 22, "without the write to stimecmp", "tm", 11)
    X0 = 96
    base, high = 70, 50
    f.text(X0 - 10, base - 3, "pending", "tm", 10.5, "end")
    f.path(f"M{X0} {base} L140 {base} L140 {high} L616 {high}", "a")
    f.text(146, high - 8, "time >= stimecmp, and stays true", "ta", 11)
    f.text(X0 - 10, 113, "the hart", "tm", 10.5, "end")
    x = 140
    seq = ["trap", "clockintr()", "sret"] * 3
    for i, s in enumerate(seq):
        w = tw(s, 11, True) + 16
        if x + w > 600:
            break
        f.rect(x, 96, w, 26, "s f" if s != "sret" else "s fs", 6)
        f.text(x + w / 2, 113, s, "t", 11, "middle", None, True)
        nx = x + w + 10
        x = nx
    f.text(x + 2, 113, "...", "tm", 12)
    f.text(140, 150, "sret turns interrupts back on, the interrupt is still pending,", "tm", 11)
    f.text(140, 166, "and the hart traps again before the interrupted code runs.", "tm", 11)
    return f


def plic():
    f = Fig("f0303a", "Claim and complete", 336)
    lanes = [(80, "UART", "irq 10"), (320, "PLIC", "0x0c000000"), (540, "hart 0", "devintr()")]
    H = 336
    for x, name, sub in lanes:
        f.rect(x - 62, 12, 124, 36, "s f", 8)
        f.text(x, 28, name, "t", 12, "middle", 600)
        f.text(x, 42, sub, "tm", 10, "middle", None, True)
        f.line(x, 48, x, H - 12, "m", dash=True)
    U, P, Hh = 80, 320, 540
    # 1. raise
    f.line(U, 76, P - 6, 76, "s", arrow=True)
    f.text((U + P) / 2, 70, "a byte arrives: line 10 raised", "t", 11, "middle")
    # 2. signal hart
    f.line(P, 116, Hh - 6, 116, "s", arrow=True)
    f.text((P + Hh) / 2, 110, "external interrupt", "t", 11, "middle")
    f.text((P + Hh) / 2, 131, "scause 0x8000000000000009", "tm", 10, "middle", None, True)
    # in-service bar
    f.rect(P - 6, 160, 12, 140, "a af", 3)
    f.text(P - 12, 236, "line 10", "ta", 11, "end", 600)
    f.text(P - 12, 251, "in service", "ta", 11, "end")
    # 3. claim
    f.line(Hh, 164, P + 8, 164, "s", arrow=True)
    f.text((P + Hh) / 2, 158, "plic_claim(): 32-bit load", "t", 11, "middle")
    f.text((P + Hh) / 2, 179, "PLIC_SCLAIM(0) = 0x0c201004", "tm", 10, "middle", None, True)
    # 4. returns 10
    f.line(P + 8, 210, Hh - 6, 210, "s", arrow=True, dash=True)
    f.text((P + Hh) / 2, 204, "returns 10", "t", 11, "middle", None)
    # self box
    f.rect(Hh - 70, 224, 140, 46, "s fs", 6)
    f.text(Hh, 243, "uartintr()", "t", 11, "middle", None, True)
    f.text(Hh, 260, "consoleintr(c)", "t", 11, "middle", None, True)
    # 5. complete
    f.line(Hh, 296, P + 8, 296, "s", arrow=True)
    f.text((P + Hh) / 2, 290, "plic_complete(10): store 10", "t", 11, "middle")
    f.text((P + Hh) / 2, 311, "to the same address", "tm", 10, "middle")
    f.text(P - 12, 322, "line 10 can be delivered again", "tm", 10.5, "end")
    return f


def consbuf():
    f = Fig("f0303b", "cons.buf and its three indexes", 280)
    x0, cw, ch = 176, 26, 26
    rows = [
        (44, "typed", "echo one", "echo one", 0, 0, 8, None),
        (134, "then", "Control-H x2", "echo one", 0, 0, 6, (6, 8)),
        (224, "then typed", "two, Enter", "echo otwo\n", 0, 10, 10, None),
    ]
    for y, l1, l2, chars, r, w, e, dead in rows:
        f.text(24, y + 10, l1, "tm", 11)
        f.text(24, y + 26, l2, "t", 12, mono=True)
        cells = []
        i = 0
        while i < len(chars):
            if chars[i] == "\n":
                cells.append("\\n")
            else:
                cells.append(chars[i])
            i += 1
        for k in range(12):
            x = x0 + k * cw
            isdead = dead and dead[0] <= k < dead[1]
            f.rect(x, y, cw, ch, "s f" if k < len(cells) and not isdead else "m f", 0)
            if k < len(cells):
                c = cells[k]
                cls = "tm" if isdead else "t"
                if c == " ":
                    f.line(x + 8, y + 19, x + cw - 8, y + 19, "m")
                else:
                    f.text(x + cw / 2, y + 18, c, cls, 12 if c != "\\n" else 10.5, "middle", None, True)
        xe = x0 + 12 * cw
        f.text(xe + 8, y + 18, "...", "tm", 12)
        f.text(xe + 30, y + 18, "128 bytes, a ring", "tm", 10.5)
        # markers
        marks = {}
        for name, v in (("r", r), ("w", w), ("e", e)):
            marks.setdefault(v, []).append(name)
        for v, names in marks.items():
            x = x0 + v * cw
            acc = "w" in names and y == 224
            f.line(x, y + ch + 2, x, y + ch + 10, "a" if acc else "s")
            f.text(x, y + ch + 22, " ".join(names), "ta" if acc else "t", 11.5, "middle", 600, True)
        # brackets
        if y == 44:
            f.brace_h(x0 + w * cw + 1, x0 + e * cw - 1, y - 6, "m", up=True)
            f.text(x0 + (w + e) / 2 * cw, y - 12, "w..e: the line being typed", "tm", 10.5, "middle")
        if dead:
            f.brace_h(x0 + dead[0] * cw + 1, x0 + dead[1] * cw - 1, y - 6, "m", up=True)
            f.text(x0 + dead[0] * cw, y - 12, "erased: e moved back, the bytes stay", "tm", 10.5)
        if y == 224:
            f.brace_h(x0 + r * cw + 1, x0 + w * cw - 1, y - 6, "m", up=True)
            f.text(x0 + (r + w) / 2 * cw, y - 12, "r..w: a whole line consoleread() may take", "tm", 10.5, "middle")
            f.text(x0 + w * cw + 16, y + ch + 22, "w = e, then wakeup(&cons.r)", "ta", 10.5)
    return f


FIGS = [
    ("03.01-kernelvec-frame", frame),
    ("03.01-scause", scause),
    ("03.02-stimecmp", sawtooth),
    ("03.02-never-cleared", storm),
    ("03.03-claim-complete", plic),
    ("03.03-cons-buf", consbuf),
]

if __name__ == "__main__":
    for name, fn in FIGS:
        print(write(MOD, name, fn()))
