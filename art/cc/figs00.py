"""Figures for cc module 00, The smallest compiler (lessons 00.01 to 00.03).

    python3 -B art/cc/figs00.py [name-prefix ...]
                writes tracks/cc/lessons/00-the-smallest-compiler/figures/00.0N-*.svg

Every file name, size, address, instruction and status here is from a real run of the project as
the site shows it at the lesson (./learn files cc --at 00.0N, then make -s: figlib.project), with
the RISC-V toolchain and QEMU on this machine. NOTES.md's values are asserted, so a change to the
track that moves one stops this script:

  00.01-journey       at 00.02, NOTES.md's by-hand commands: ./cc -o prog.s try.c, as for
                      rt/start.S and prog.s, ld -T rt/link.ld, QEMU: try.c is 42, prog.s is
                      ./cc's four lines, the status is 42; the sizes of the files as written
  00.01-four-lines    ./cc try.c at 00.01: exactly the four lines
  00.02-memory        nm and objdump -h of that prog.elf: _start 0x80000000, main 0x80000038,
                      stack_top 0x80010040, .text 0x40 bytes, so the stack is 0x80000040 up to
                      stack_top (64 KiB); the test device is where start.S's store goes
                      (0x100000), from the run below
  00.02-run           stepped: objdump -d of that prog.elf, run from 0x80000000 one instruction
                      at a time (run_start(): the jumps here, the rest figlib.simulate) until the
                      store to the test device: the word is 0x2a3333 and its code, 42, is QEMU's
                      real exit status. QEMU's -d in_asm log of the same run says what comes
                      before: 6 reset instructions of QEMU's own at 0x1000, then 0x80000000 (the
                      first step's note; they are not drawn)
  00.03-two-compilers ./same try.c at 00.03: "same: status 42"; the files it leaves in
                      build/same/ and gcc.c as written
  00.03-differ        the same with NOTES.md's wrongcc through CC_UNDER_TEST: ours.s holds
                      li a0, 7, and same prints "ours: status 7", "gcc: status 42", "differ", status 1
The maps, the cover and the icon are not made here (archmap.py; art/outlines/cc_art.py).
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import figlib as L  # noqa: E402
from figlib import Fig, write, steps  # noqa: E402

FOUR = ["  .globl main", "main:", "  li a0, 42", "  ret"]


# ------------------------------------------------------------------ the by-hand build at 00.02

def by_hand():
    """NOTES.md's commands at 00.02, in the project: {file: size}, the status, objdump and nm."""
    d = L.project("00.02")
    pre = L.tools()
    with open(os.path.join(d, "try.c")) as f:
        assert f.read() == "42\n"
    cmds = [["./cc", "-o", "prog.s", "try.c"],
            [pre + "as", "-march=rv64im", "-mabi=lp64", "-o", "start.o", "rt/start.S"],
            [pre + "as", "-march=rv64im", "-mabi=lp64", "-o", "prog.o", "prog.s"],
            [pre + "ld", "-T", "rt/link.ld", "-o", "prog.elf", "start.o", "prog.o"]]
    for c in cmds:
        out, err, st = L.sh(d, c)
        assert st == 0, (c, err)
    _, _, status = L.sh(d, ["qemu-system-riscv64", "-machine", "virt", "-bios", "none", "-display", "none",
                            "-monitor", "none", "-serial", "stdio", "-kernel", "prog.elf"])
    assert status == 42, status
    # what QEMU runs before the program: its own reset code, which jumps to 0x80000000
    _, _, st = L.sh(d, ["qemu-system-riscv64", "-machine", "virt", "-bios", "none", "-display", "none", "-monitor",
                        "none", "-serial", "stdio", "-kernel", "prog.elf", "-d", "in_asm", "-D", "qemu-in_asm.log"])
    with open(os.path.join(d, "qemu-in_asm.log")) as f:
        ran = [int(a, 16) for a in re.findall(r"^0x([0-9a-f]+):", f.read(), re.M)]
    reset = [a for a in ran if a < 0x80000000]
    assert st == 42 and ran[0] == 0x1000 and len(reset) == 6 and ran[len(reset)] == 0x80000000, ran[:8]
    with open(os.path.join(d, "prog.s")) as f:
        assert f.read().splitlines() == FOUR
    sizes = {n: os.path.getsize(os.path.join(d, n)) for n in ("try.c", "prog.s", "start.o", "prog.o", "prog.elf")}
    dump = L.sh(d, [pre + "objdump", "-d", "prog.elf"])[0]
    nm = {m[2]: int(m[1], 16) for m in re.finditer(r"^([0-9a-f]+) \w (\S+)$", L.sh(d, [pre + "nm", "prog.elf"])[0],
                                                     re.M) for m in [m]}
    heads = L.sh(d, [pre + "objdump", "-h", "prog.elf"])[0]
    text = re.search(r"\.text\s+([0-9a-f]+)\s+([0-9a-f]+)", heads)
    code = {n: int(L.sh(d, [pre + "size", n])[0].splitlines()[1].split()[0]) for n in ("start.o", "prog.o", "prog.elf")}
    return dict(sizes=sizes, status=status, dump=dump, nm=nm, text_size=int(text[1], 16),
                text_vma=int(text[2], 16), code=code, prefix=pre, reset=len(reset))


def disassembly(dump):
    """objdump -d's instructions: [(label, address, word, mnemonic, operands, comment)] in order;
    label is the symbol a row starts (or "")."""
    rows, label = [], ""
    for ln in dump.splitlines():
        m = re.match(r"^([0-9a-f]+) <(\w+)>:$", ln)
        if m:
            label = m[2]
            continue
        m = re.match(r"^\s+([0-9a-f]+):\s+([0-9a-f]+)\s+(\S+)\s*([^#]*?)\s*(#.*)?$", ln)
        if m:
            rows.append((label, int(m[1], 16), m[2], m[3], m[4].strip(), (m[5] or "").strip()))
            label = ""
    return rows


def run_start(rows):
    """Run the disassembled program from its first address, an instruction at a time, as the
    machine does, until the store to the test device. Returns [(index of the row, regs after,
    what happened)], regs holding pc (the next instruction), sp, ra, a0, t0, t1; the stored word
    is regs["word"] at the last step."""
    at = {a: k for k, (_, a, *_r) in enumerate(rows)}
    regs = {"pc": rows[0][1]}
    trace = []
    while True:
        k = at[regs["pc"]]
        _, addr, _, op, args, _ = rows[k]
        a = [x.strip() for x in args.split(",")] if args else []
        nxt = addr + 4
        r = dict(regs)
        if op == "auipc":
            r[a[0]] = addr + (int(a[1], 0) << 12)
        elif op == "jal":
            r["ra"] = nxt
            nxt = int(a[0].split()[0], 16)
        elif op == "ret":
            nxt = r["ra"]
        elif op == "beqz":
            if r.get(a[0], 0) == 0:
                nxt = int(a[1].split()[0], 16)
        elif op == "j":
            raise AssertionError("the program reached its loop: the store did not stop it")
        elif op == "sw":
            mo = re.match(r"^(-?\w+)\((\w+)\)$", a[1])
            r["store"] = (r[mo[2]] + int(mo[1], 0), r[a[0]] & 0xffffffff)
        else:
            line = f"{op} {', '.join(a)}"
            (_, after, _), = L.simulate([line], regs={x: v for x, v in r.items() if x not in ("pc", "store")})
            r.update({x: v for x, v in after.items() if x != "zero"})
        r["pc"] = nxt
        trace.append((k, r))
        regs = r
        if op == "sw":
            return trace


# ------------------------------------------------------------------ 00.01

def journey():
    b = by_hand()
    sz, code, pre = b["sizes"], b["code"], b["prefix"]
    f = Fig("f0001a", "One program from the file that holds 42 to the status 42 coming back", 318)
    fx = [70, 196, 322, 448, 574]           # the files' centres
    px = [133, 259, 385, 511]               # the programs', between them
    py, ph, pw = 46, 44, 104
    cy = 128                                # the cards' top
    # what this lesson builds, and what the next one does
    f.brace_h(fx[0] - 48, px[0] + pw / 2, 30, "a", up=True)
    f.text((fx[0] - 48 + px[0] + pw / 2) / 2, 20, "this lesson", "ta", 12, "middle", 700)
    f.brace_h(px[1] - pw / 2, px[3] + pw / 2, 30, "m", up=True)
    f.text((px[1] + px[3]) / 2, 20, "lesson 00.02", "tm", 12, "middle", 600)

    # the arrows: each file into the program on its right, each program out to the file on its right
    for k in range(4):
        hot = k == 0
        c = "a" if hot else "s"
        f.line(fx[k] + 14, cy - 2, px[k] - 18, py + ph + 3, c, arrow=True)
        f.line(px[k] + 18, py + ph + 3, fx[k + 1] - 14, cy - 3, "s", arrow=True)
    # start.o joins the linker, up between prog.o and prog.elf
    so_y = 246
    f.line(px[2], so_y - 2, px[2], py + ph + 3, "s", arrow=True)

    # the programs
    names = [("cc", "./cc"), ("assembler", pre + "as"), ("linker", pre + "ld"), ("the machine", "QEMU")]
    for k, (name, cmd) in enumerate(names):
        hot = k == 0
        f.rect(px[k] - pw / 2, py, pw, ph, "a af" if hot else "s f", 8)
        f.text(px[k], py + 19, name, "ta" if hot else "t", 13.5, "middle", 700, mono=hot)
        f.text(px[k], py + 35, cmd, "ta" if hot else "tm", 10.5, "middle", mono=True)

    def card(cx, w, name, size, lines, hot=False, mono_lines=True, y=cy, h=None):
        h = h or 44 + 15 * len(lines)
        f.page(cx - w / 2, y, w, h, "a af" if hot else "s fs")
        f.text(cx - w / 2 + 10, y + 18, name, "ta" if hot else "t", 12.5, weight=700, mono=True)
        f.text(cx - w / 2 + 10, y + 33, size, "ta" if hot else "tm", 10.5)
        for i, ln in enumerate(lines):
            if mono_lines:
                f.code(cx - w / 2 + 10, y + 52 + i * 15, ln, 11, "ta" if hot else "t")
            else:
                f.text(cx - w / 2 + 10, y + 52 + i * 15, ln, "ta" if hot else "t", 11)
        return h

    card(fx[0], 96, "try.c", f"{sz['try.c']} bytes", ["42"], hot=True)
    card(fx[1], 112, "prog.s", f"{sz['prog.s']} bytes", FOUR)
    card(fx[2], 112, "prog.o", f"{sz['prog.o']} bytes", ["main: 2 instructions,", f"{code['prog.o']} bytes of code"],
         mono_lines=False)
    card(fx[3], 112, "prog.elf", f"{sz['prog.elf']} bytes", [f"{code['prog.elf']} bytes of code,", "at 0x80000000"],
         mono_lines=False)
    # start.o, under the linker
    f.page(px[2] - 56, so_y, 112, 58, "s fs")
    f.text(px[2] - 46, so_y + 18, "start.o", "t", 12.5, weight=700, mono=True)
    f.text(px[2] - 46, so_y + 33, f"{sz['start.o']} bytes", "tm", 10.5)
    f.text(px[2] - 46, so_y + 49, "from rt/start.S", "t", 11)
    # the status
    f.rect(fx[4] - 46, cy, 92, 40, "s f", 20)
    f.text(fx[4], cy + 17, "status", "tm", 11, "middle")
    f.text(fx[4], cy + 33, str(b["status"]), "t", 15, "middle", 700, mono=True)
    f.text(fx[4], cy + 60, "what the shell", "tm", 10.5, "middle")
    f.text(fx[4], cy + 74, "sees: echo $?", "tm", 10.5, "middle")
    return f


NOTES4 = ["lets the linker see the name", "a label: the address of the next instruction",
          "a0 is the register a function leaves its result in", "go back to whoever called main"]


def four_lines():
    out, err, st = L.cc("00.01", L.source("00.01", "try.c"))
    assert st == 0 and out.splitlines() == FOUR, out
    f = Fig("f0001b", "The four lines the compiler writes, and what each one is for", 230)
    x0, y0, rh, size = 24, 30, 40, 15
    f.rect(x0, y0 - 6, 176, rh * 4 + 6, "s fs", 8)
    for k, (ln, note) in enumerate(zip(out.splitlines(), NOTES4)):
        y = y0 + 20 + k * rh
        spans = [(ln.index("42"), ln.index("42") + 2, "ta")] if "42" in ln else ()
        f.code(x0 + 14, y + 5, ln, size, "t", spans, weight=600 if "42" in ln else None)
        end = x0 + 14 + L.cw(size) * len(ln) + 10
        f.line(end, y, 222, y, "m", dash=True)
        f.line(222, y, 236, y, "m")
        f.text(244, y + 4.5, note, "t", 13)
    y = y0 + rh * 4 + 26
    f.text(x0, y, "Only the 42 comes from try.c: the other three lines are the same for every number.", "ta", 12.5,
           weight=600)
    return f


# ------------------------------------------------------------------ 00.02

def memory():
    b = by_hand()
    nm = b["nm"]
    assert nm["_start"] == 0x80000000 and nm["main"] == 0x80000038 and nm["stack_top"] == 0x80010040, nm
    assert b["text_vma"] == 0x80000000 and b["text_size"] == 0x40, (b["text_vma"], b["text_size"])
    stack_lo = nm["stack_top"] - 0x10000
    assert stack_lo == b["text_vma"] + b["text_size"]          # ALIGN(16) after the code: nothing between
    rows = disassembly(b["dump"])
    device, word = run_start(rows)[-1][1]["store"]
    assert device == 0x100000, hex(device)
    n_start = sum(1 for r in rows if r[1] < nm["main"])
    n_main = sum(1 for r in rows if r[1] >= nm["main"])

    f = Fig("f0002a", "The linked program in the machine's memory, and the test device", 402)
    bx, bw = 150, 168                       # the memory column
    ax = bx - 10                            # addresses, right-aligned to it
    nx = bx + bw + 16                       # notes

    def addr(y, a, cls="t", size=12):
        """An address at the left of the column, at the boundary y it names."""
        f.text(ax, y + 4, f"{a:#010x}", cls, size, "end", mono=True)

    f.text(bx + bw / 2, 18, "the machine's memory, low addresses at the bottom", "tm", 11.5, "middle")
    # the stack: 64 KiB, drawn short
    st_top, st_bot = 40, 176
    f.rect(bx, st_top, bw, st_bot - st_top, "s f", 0)
    f.text(bx + bw / 2, st_top + 28, "the stack", "t", 13.5, "middle", 700)
    f.text(bx + bw / 2, st_top + 46, f"{0x10000 // 1024} KiB, still empty", "tm", 11.5, "middle")
    f.line(bx + bw / 2, st_top + 58, bx + bw / 2, st_top + 92, "s", arrow=True)
    f.text(bx + bw / 2 + 8, st_top + 80, "it grows down", "tm", 11)
    f.text(bx + bw / 2, st_bot - 10, "(not to scale)", "tm", 10.5, "middle")
    addr(st_top, nm["stack_top"])
    f.rich(nx, st_top + 4, [("stack_top", "t", True), (": _start sets sp here", "t", False)], 12.5)
    # main and _start
    main_h, start_h = 30, 64
    my, sy = st_bot, st_bot + main_h
    f.rect(bx, my, bw, main_h, "s fs", 0)
    f.code(bx + 12, my + 20, "main", 13, "t", weight=700)
    f.text(bx + bw - 10, my + 20, f"{n_main} instructions", "tm", 11, "end")
    f.rect(bx, sy, bw, start_h, "a af", 0)
    f.code(bx + 12, sy + 24, "_start", 13, "ta", weight=700)
    f.text(bx + 12, sy + 42, f"{n_start} instructions,", "ta", 11)
    f.text(bx + 12, sy + 56, "from rt/start.S", "ta", 11)
    addr(my - 0.01, stack_lo, "tm", 11)
    f.text(ax, my + 22, f"{nm['main']:#010x}", "t", 12, "end", mono=True)
    f.line(ax + 3, my + 18, bx, my + 18, "m", dash=True)
    addr(sy + start_h, nm["_start"], "ta")
    f.text(nx, my + 20, "prog.s: li a0, 42 and ret", "t", 12)
    f.text(nx, sy + 24, "where QEMU's reset code jumps to,", "ta", 12.5, weight=700)
    f.text(nx, sy + 40, "the first address of RAM:", "ta", 12.5, weight=700)
    f.text(nx, sy + 56, "link.ld puts _start first", "ta", 12.5, weight=700)
    # the long gap down to the device
    gy0 = sy + start_h
    gy1 = gy0 + 76
    yb = (gy0 + gy1) / 2
    f.path(f"M{bx} {gy0} V{yb - 18} M{bx + bw} {gy0} V{yb - 18} M{bx} {yb + 18} V{gy1} M{bx + bw} {yb + 18} V{gy1}",
           "m", dash=True)
    f.path(f"M{bx - 7} {yb - 14} l7 -4 l7 4 M{bx + bw - 7} {yb - 14} l7 -4 l7 4 "
           f"M{bx - 7} {yb + 18} l7 -4 l7 4 M{bx + bw - 7} {yb + 18} l7 -4 l7 4", "m")
    f.text(bx + bw / 2, yb - 1, "2 GiB of addresses", "tm", 11, "middle")
    f.text(bx + bw / 2, yb + 13, "with nothing at them", "tm", 11, "middle")
    # the device
    dy = gy1
    f.rect(bx, dy, bw, 36, "s f", 0)
    f.text(bx + bw / 2, dy + 23, "the test device", "t", 13, "middle", 700)
    f.text(ax, dy + 22, f"{device:#010x}", "t", 12, "end", mono=True)
    f.line(ax + 3, dy + 18, bx, dy + 18, "m", dash=True)
    f.text(nx, dy + 15, "not memory: a store here stops QEMU,", "t", 12)
    f.text(nx, dy + 31, f"and {word:#x} makes it exit with {word >> 16}", "t", 12)
    return f


def regfmt(v):
    if v is None:
        return "-"
    return str(v) if 0 <= v < 0x1000 else f"{v:#x}"


RUN_REGS = ["pc", "sp", "ra", "a0", "t0", "t1"]


def run():
    b = by_hand()
    rows = disassembly(b["dump"])
    trace = run_start(rows)
    addr, word = trace[-1][1]["store"]
    assert addr == 0x100000 and word == 0x2a3333 and (word >> 16) & 0xff == b["status"] == 42, (hex(addr), hex(word))
    f = Fig("f0002b", "From the first instruction to QEMU's exit, one step at a time", 404)
    x0, y0, rh = 24, 34, 17.5
    f.text(x0, 18, f"{b['prefix']}objdump -d prog.elf", "tm", 11.5, mono=True)
    # the listing: a row a line, labels on rows of their own
    ys, y = {}, y0
    for k, (lab, a, w, op, args, _) in enumerate(rows):
        if lab:
            y += 6 if k else 0
            f.code(x0, y + 12, f"{lab}:", 12, "t", weight=700)
            y += rh
        ys[k] = y
        y += rh
    list_bottom = y
    f.rect(x0 - 6, y0 - 4, 356, list_bottom - y0 + 10, "m", 6)

    def row_text(k, cls):
        _, a, w, op, args, _ = rows[k]
        f.code(x0 + 14, ys[k] + 12.5, f"{a:08x}", 11, "tm" if cls == "t" else cls)
        f.code(x0 + 90, ys[k] + 12.5, f"{op:<7} {args}", 12, cls)

    for k in range(len(rows)):
        row_text(k, "t")
    # the register panel and the device
    rx, ry = 410, 40
    f.text(rx, ry - 12, "registers", "tm", 11.5)
    for i, name in enumerate(RUN_REGS):
        f.rect(rx, ry + i * 28, 206, 24, "s f", 4)
        f.code(rx + 10, ry + i * 28 + 16.5, name, 12.5, "tm")
    dy = ry + len(RUN_REGS) * 28 + 22
    f.text(rx, dy - 8, "the test device, 0x100000", "tm", 11.5)
    f.rect(rx, dy, 206, 30, "s f", 4)
    sy = dy + 58
    f.text(rx, sy - 8, "the shell", "tm", 11.5)
    f.rect(rx, sy, 206, 46, "s fs", 4)
    f.code(rx + 10, sy + 18, "$ echo $?", 12, "tm")

    def state(regs, changed, k, cap, device=None, shell=None, note=None):
        with steps.step(f, cap):
            if note:
                f.text(x0, list_bottom + 22, note, "tm", 11)
            if k is not None:
                f.rect(x0, ys[k], 344, rh, "a af", 3)
                row_text(k, "ta")
            for i, name in enumerate(RUN_REGS):
                v = regs.get(name)
                hot = name in changed
                if hot:
                    f.rect(rx + 1, ry + i * 28 + 1, 204, 22, "a af", 3, sw=False)
                    f.code(rx + 10, ry + i * 28 + 16.5, name, 12.5, "ta")
                f.code(rx + 52, ry + i * 28 + 16.5, regfmt(v), 12.5, "ta" if hot else "t", weight=700 if hot else None)
            if device is not None:
                f.rect(rx + 1, dy + 1, 204, 28, "a af", 3, sw=False)
                f.code(rx + 10, dy + 19.5, f"{device:#x} written", 12.5, "ta", weight=700)
            if shell is not None:
                f.code(rx + 10, sy + 36, shell, 13, "ta", weight=700)

    blank = {"pc": rows[0][1]}
    state(blank, {"pc"}, None, f"QEMU's own reset code, {b['reset']} instructions at 0x1000, jumps to "
                               f"{rows[0][1]:#x}: _start's first instruction, the first of the program. No register "
                               "the program uses has been set yet.",
          note=f"before this: QEMU's reset code at 0x1000 ({b['reset']} instructions, not shown) jumped here")
    prev = blank
    for n, (k, regs) in enumerate(trace):
        _, a, w, op, args, _ = rows[k]
        changed = {x for x in RUN_REGS if regs.get(x) != prev.get(x)} - {"pc"}
        jumped = regs["pc"] != a + 4
        if jumped:
            changed |= {"pc"}
        caps = {
            "auipc": lambda: f"auipc: sp is this instruction's address plus 0x10 << 12, {regs['sp']:#x}.",
            "addi": lambda: f"addi: sp goes up by 64 to {regs['sp']:#x}, stack_top, the top of the stack. "
                            "The two make start.S's la sp, stack_top.",
            "jal": lambda: f"jal, which call main became: ra keeps the return address, {regs['ra']:#x}, and pc "
                           f"goes to main at {regs['pc']:#x}.",
            "li": lambda: "li a0, 42: the compiler's one line of work. main's result is in a0.",
            "ret": lambda: f"ret: pc goes back to ra, {regs['pc']:#x}, the instruction after the call.",
            "zext.b": lambda: "andi a0, a0, 0xff, shown as zext.b: only the low 8 bits of main's result count. "
                              "42 stays 42.",
            "beqz": lambda: "beqz: a0 is not 0, so no jump: the status is not 0, and start.S builds a word that "
                            "says so.",
            "slli": lambda: f"slli: a0 shifted 16 bits left, {regs['a0']:#x}: the status moves to the word's "
                            "upper half.",
            "or": lambda: f"or: t0 = a0 | t1 = {regs['t0']:#x}, the status over 0x3333.",
            "sw": lambda: f"sw: the word {word:#x} is stored at {addr:#x}, the test device.",
        }
        if op == "lui":
            cap = f"lui: {args.split(',')[0]} = {regs[args.split(',')[0]]:#x}, the upper bits of a constant."
            if regs.get("t1") == 0x100000 and "t1" in changed:
                cap = f"lui: t1 = {regs['t1']:#x}, the test device's address (li t1, 0x100000 is this one instruction)."
        elif op == "addiw":
            r = args.split(",")[0]
            cap = f"addiw: {r} = {regs[r]:#x}. With the lui before it, this is li {r}, {regs[r]:#x}."
        else:
            cap = caps[op]()
        if op == "sw":
            state(regs, changed, k, cap + " QEMU reads it: 0x3333 in the low half says stop, failing, and the upper "
                                          f"half, {word >> 16:#x}, is the code to exit with.", device=word)
        else:
            state(regs, changed, k, cap)
        prev = regs
    state(prev, set(), None, f"QEMU has exited with code {word >> 16}: the shell's $? is {b['status']}. The "
                             "loop at the end of _start never runs.", device=word, shell=str(b["status"]))
    return f


# ------------------------------------------------------------------ 00.03

def same_run(wrong=False):
    d = L.project("00.03")
    env = {}
    if wrong:
        L.put(d, "wrongcc", '#!/bin/sh\nprintf "  .globl main\\nmain:\\n  li a0, 7\\n  ret\\n" > "$2"\n')
        os.chmod(os.path.join(d, "wrongcc"), 0o755)
        env["CC_UNDER_TEST"] = "./wrongcc"
    out, err, st = L.sh(d, ["./same", "try.c"], env=env)
    files = sorted(os.listdir(os.path.join(d, "build", "same")))
    with open(os.path.join(d, "build", "same", "gcc.c")) as fh:
        gcc_c = fh.read()
    with open(os.path.join(d, "build", "same", "ours.s")) as fh:
        ours_s = fh.read()
    with open(os.path.join(d, "try.c")) as fh:
        assert gcc_c == "int main(void) { return " + fh.read() + "\n; }\n", gcc_c
    return out, err, st, files, gcc_c, ours_s


def lanes(f, x0, ys, stages, status, hot_status=False, small=False):
    """Two lanes of stage boxes: stages[lane] = [(action, file)]; returns the x after the last box."""
    bw, gap, bh = (78, 14, 40) if not small else (70, 12, 36)
    for lane, y in enumerate(ys):
        x = x0
        for k, (act, fn) in enumerate(stages[lane]):
            f.rect(x, y, bw, bh, "s f", 7)
            f.text(x + bw / 2, y + 16, act, "t", 12, "middle", 700, mono=act.startswith("./"))
            f.text(x + bw / 2, y + 31, fn, "tm", 10.5, "middle", mono=True)
            if k:
                f.line(x - gap + 1, y + bh / 2, x - 2, y + bh / 2, "s", arrow=True)
            x += bw + gap
    return x - gap, bw, bh


def two_compilers():
    out, err, st, files, gcc_c, _ = same_run()
    assert (out, st) == ("same: status 42\n", 0), (out, err, st)
    want = ["gcc.c", "gcc.elf", "gcc.o", "gcc.out", "ours.elf", "ours.o", "ours.out", "ours.s", "start.o"]
    assert files == want, files
    f = Fig("f0003a", "The same source through two compilers to the same machine", 352)
    f.text(24, 20, "./same try.c: every file below is in build/same/", "tm", 11.5)
    y1, y2 = 44, 182
    x0 = 104
    stages = [[("./cc", "ours.s"), ("assemble", "ours.o"), ("link", "ours.elf"), ("run", "QEMU")],
              [("wrap", "gcc.c"), ("gcc -c", "gcc.o"), ("link", "gcc.elf"), ("run", "QEMU")]]
    xe, bw, bh = lanes(f, x0, (y1, y2), stages, 42)
    f.text(x0, y1 - 8, "ours", "t", 12, weight=700)
    f.text(x0, y2 - 8, "gcc, for the same machine", "t", 12, weight=700)
    # try.c, into both lanes
    tx, ty = 22, (y1 + y2 + bh) / 2 - 30
    f.page(tx, ty, 58, 60, "s fs")
    f.text(tx + 8, ty + 17, "try.c", "t", 12, weight=700, mono=True)
    f.text(tx + 29, ty + 44, "42", "t", 16, "middle", 700, mono=True)
    f.poly([(tx + 58 + 1, ty + 22), (88, ty + 22), (88, y1 + bh / 2), (x0 - 2, y1 + bh / 2)], "s", arrow=True)
    f.poly([(tx + 58 + 1, ty + 38), (88, ty + 38), (88, y2 + bh / 2), (x0 - 2, y2 + bh / 2)], "s", arrow=True)
    # start.o, between the lanes, into both links
    lx = x0 + 2 * (bw + 14)
    sx, sy = lx - 6, (y1 + bh + y2) / 2 - 17
    f.rect(sx, sy, bw + 12, 34, "s fs", 6)
    f.text(sx + (bw + 12) / 2, sy + 15, "start.o", "t", 12, "middle", 700, mono=True)
    f.text(sx + (bw + 12) / 2, sy + 28, "rt/start.S", "tm", 10.5, "middle", mono=True)
    f.line(lx + bw / 2, sy - 1, lx + bw / 2, y1 + bh + 2, "s", arrow=True)
    f.line(lx + bw / 2, sy + 35, lx + bw / 2, y2 - 2, "s", arrow=True)
    f.text(sx - 8, sy + 15, "the same", "tm", 11, "end")
    f.text(sx - 8, sy + 29, "start-up code", "tm", 11, "end")
    # the statuses, and the comparison to their right
    cx = xe + 46
    qx = cx + 62                            # the comparison, under both
    ow = 190
    ox, oy = 640 - 16 - ow, y2 + bh + 66    # what same prints
    my = oy - 28
    for y in (y1, y2):
        yy = y + bh / 2
        f.line(xe + 1, yy, cx - 30, yy, "s", arrow=True)
        f.rect(cx - 28, yy - 13, 56, 26, "s f", 13)
        f.text(cx, yy + 5, "42", "t", 14, "middle", 700, mono=True)
        f.text(cx, yy - 17, "status", "tm", 10.5, "middle")
        f.poly([(cx + 29, yy), (qx, yy), (qx, my - 13)], "a")
    f.circle(qx, my, 12, "a af")
    f.path(f"M{qx - 5.5} {my - 3} H{qx + 5.5} M{qx - 5.5} {my + 3} H{qx + 5.5}", "a")
    f.text(qx - 18, my + 4.5, "compare", "ta", 12.5, "end", 700)
    f.rect(ox, oy, ow, 34, "a af", 6)
    f.code(ox + 14, oy + 22, out.strip(), 14, "ta", weight=700)
    f.line(qx, my + 13, qx, oy - 2, "a", arrow=True)
    # gcc.c as written
    gx, gy = 24, y2 + bh + 30
    lines = gcc_c.splitlines()
    f.page(gx, gy, 236, 26 + 16 * len(lines), "s fs")
    f.code(gx + 10, gy + 17, "gcc.c", 11.5, "t", weight=700)
    f.text(gx + 56, gy + 17, "the number, wrapped in a main", "tm", 11)
    for i, ln in enumerate(lines):
        f.code(gx + 10, gy + 36 + i * 16, ln, 12, "t")
    f.line(x0 + bw / 2, y2 + bh + 1, x0 + bw / 2, gy - 2, "m", arrow=True)
    return f


def differ():
    out, err, st, files, gcc_c, ours_s = same_run(wrong=True)
    assert out.splitlines() == ["ours: status 7", "gcc: status 42", "differ"] and st == 1, (out, st)
    assert "  li a0, 7" in ours_s.splitlines(), ours_s
    d = L.project("00.03")              # NOTES.md: on a file holding 7 the same fake agrees
    L.put(d, "seven.c", "7\n")
    assert L.sh(d, ["./same", "seven.c"], env={"CC_UNDER_TEST": "./wrongcc"})[:2] == ("same: status 7\n", "")
    f = Fig("f0003b", "A compiler that is wrong on purpose: the two statuses differ, and same says so", 236)
    y1, y2 = 40, 140
    x0 = 24
    stages = [[("wrongcc", "ours.s"), ("build", "ours.elf"), ("run", "QEMU")],
              [("wrap, gcc", "gcc.o"), ("build", "gcc.elf"), ("run", "QEMU")]]
    xe, bw, bh = lanes(f, x0, (y1, y2), stages, None, small=True)
    f.text(x0, y1 - 9, "ours: the compiler CC_UNDER_TEST names", "t", 12, weight=700)
    f.text(x0, y2 - 9, "gcc, for the same machine", "t", 12, weight=700)
    # ours.s as the fake wrote it
    lines = ours_s.splitlines()
    ox, oy = x0 - 2, y1 + bh + 8
    f.rect(ox, oy, 112, 18 + 14 * 0, "s fs", 4)
    li = next(l for l in lines if "li a0" in l).strip()
    f.code(ox + 10, oy + 13, li, 11, "ta", spans=[(len(li) - 1, len(li), "ta")], weight=700)
    f.text(ox + 120, oy + 13, "a fake: always 7", "tm", 10.5)
    cx = xe + 44
    for y, v in ((y1, 7), (y2, 42)):
        f.line(xe + 1, y + bh / 2, cx - 30, y + bh / 2, "s", arrow=True)
        f.rect(cx - 28, y + bh / 2 - 12, 56, 24, "s f", 12)
        f.text(cx, y + bh / 2 + 5, str(v), "t", 13.5, "middle", 700, mono=True)
    my = (y1 + y2 + bh) / 2
    f.line(cx, y1 + bh / 2 + 13, cx, my - 12, "a")
    f.line(cx, my + 12, cx, y2 + bh / 2 - 13, "a")
    f.circle(cx, my, 11, "a af")
    f.path(f"M{cx - 5} {my - 3} H{cx + 5} M{cx - 5} {my + 3} H{cx + 5} M{cx + 3.5} {my - 7} L{cx - 3.5} {my + 7}", "a")
    # what same printed
    tx, ty = cx + 40, y1 + 4
    tw_ = 640 - 16 - tx
    out_lines = out.splitlines()
    f.rect(tx, ty, tw_, 30 + 18 * (len(out_lines) + 2), "s fs", 8)
    f.code(tx + 12, ty + 20, "$ CC_UNDER_TEST=./wrongcc", 11, "tm")
    f.code(tx + 12, ty + 35, "    ./same try.c; echo $?", 11, "tm")
    for i, ln in enumerate(out_lines + [str(st)]):
        f.code(tx + 12, ty + 58 + i * 18, ln, 13, "ta" if ln == "differ" else "t", weight=700 if ln == "differ" else None)
    f.line(cx + 12, my, tx - 2, my, "a", arrow=True)
    f.text(24, 226, "On a file holding 7 the same fake would say same: status 7. One sample can agree by luck.", "tm", 11)
    return f


FIGS = [
    ("00.01-journey", journey, False),
    ("00.01-four-lines", four_lines, False),
    ("00.02-memory", memory, False),
    ("00.02-run", run, True),
    ("00.03-two-compilers", two_compilers, False),
    ("00.03-differ", differ, False),
]


def main(argv):
    for name, fn, stepped in FIGS:
        if argv and not any(name.startswith(a) for a in argv):
            continue
        write(name, fn(), stepped)


if __name__ == "__main__":
    main(sys.argv[1:])
