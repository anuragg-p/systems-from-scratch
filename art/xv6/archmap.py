"""The xv6 architecture map, one copy per lesson: tracks/xv6/lessons/<module>/figures/NN.LL-map.svg.

The same map every time: user programs, system calls, the kernel's middle (processes,
memory, file system, traps, locks), the drivers, boot, and the QEMU machine underneath.
The lesson's own piece is drawn in the accent, pieces built by earlier lessons are solid,
pieces still to come are dashed and muted. The optional extensions (08 network, 09 screen)
are marked "optional" and count as built only inside their own extension.

usage: python3 archmap.py            # every lesson
       python3 archmap.py 04 05.02    # only ids starting with these
"""
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from figlib import Fig, LESSONS, SW, esc, fmt  # noqa: E402

W = 480          # narrower than the usual 640, so the labels stay readable on a phone
X0, X1 = 12, 468
ROW_H, GAP, TOP = 40, 6, 10

# piece: (row, x, width, label, sub)
PIECES = {
    "user":    (0, X0, X1 - X0, "shell and programs", "user space"),
    "sys":     (1, X0, X1 - X0, "system calls", "how a program asks the kernel for something"),
    "proc":    (2, 12, 146, "processes", "and the scheduler"),
    "mem":     (2, 166, 147, "memory", "pages and page tables"),
    "fs":      (2, 321, 147, "file system", "files on the disk"),
    "trap":    (3, 12, 300, "traps and interrupts", "timer, devices, faults"),
    "locks":   (3, 320, 148, "locks", "harts take turns"),
    "console": (4, 12, 108, "console", "serial port"),
    "disk":    (4, 128, 108, "disk", "virtio"),
    "net":     (4, 244, 108, "network", "optional"),
    "screen":  (4, 360, 108, "screen", "optional"),
    "boot":    (5, X0, X1 - X0, "boot", "from power-on to C on every hart"),
    "hw":      (6, X0, X1 - X0, "QEMU virt machine", "RISC-V harts, RAM, UART, disk, interrupt controller"),
}
OPTIONAL = {"net": "08", "screen": "09"}

# which piece(s) each lesson builds
LESSON_PIECES = {
    "00.01": ["hw"], "00.02": ["hw"],
    "01.01": ["boot"], "01.02": ["boot"], "01.03": ["console"],
    "02.01": ["mem"], "02.02": ["mem"], "02.03": ["locks"], "02.04": ["mem"],
    "03.01": ["trap"], "03.02": ["trap"], "03.03": ["trap", "console"],
    "04.01": ["proc"], "04.02": ["proc"], "04.03": ["proc"], "04.04": ["proc"],
    "05.01": ["disk"], "05.02": ["fs"], "05.03": ["fs"], "05.04": ["fs"], "05.05": ["fs"],
    "05.06": ["fs"], "05.07": ["fs"],
    "06.01": ["sys"], "06.02": ["sys"], "06.03": ["proc"], "06.04": ["proc"], "06.05": ["mem"],
    "06.06": ["fs"], "06.07": ["sys"],
    "07.01": ["user"], "07.02": ["user"], "07.03": ["user"],
    "08.01": ["net"], "08.02": ["net"], "08.03": ["net"], "08.04": ["net"], "08.05": ["net", "user"],
    "09.01": ["screen"], "09.02": ["screen"], "09.03": ["screen"], "09.04": ["screen", "user"],
    "09.05": ["screen", "user"],
}


# Lessons whose map carries their own title (the track's opening lesson, as in the db track).
TITLES = {"00.01": "How a kernel works"}


def lessons():
    """[(id, module dir)] for every lesson doc on disk, in order."""
    out = []
    for p in sorted(glob.glob(os.path.join(LESSONS, "*", "[0-9][0-9].[0-9][0-9]-*.md"))):
        lid = os.path.basename(p)[:5]
        out.append((lid, os.path.basename(os.path.dirname(p))))
    return out


def before(a, b):
    """Is lesson a built before lesson b? The core comes first; each extension stands alone."""
    ma, mb = a[:2], b[:2]
    if ma in ("08", "09"):
        return ma == mb and a < b
    return mb in ("08", "09") or a < b


def states(lid, all_ids):
    cur = set(LESSON_PIECES[lid])
    built = {"hw"}
    for other in all_ids:
        if before(other, lid):
            built.update(LESSON_PIECES[other])
    return {k: "now" if k in cur else ("built" if k in built else "later") for k in PIECES}


class Map(Fig):
    def svg(self):
        def mk(name, cls):
            return (f'<marker id="{self.key}-{name}" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
                    f'<path class="{cls}" d="M1 1.5L8.5 5L1 8.5" {SW} stroke-linecap="round" stroke-linejoin="round"/></marker>')
        defs = "<defs>" + mk("ah", "s") + mk("aa", "a") + mk("am", "m") + "</defs>"
        body = "\n".join(self.out)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {fmt(self.h)}" fill="none">\n'
                f'<title>{esc(self.title)}</title>\n{defs}\n{body}\n</svg>\n')


def draw(lid, all_ids):
    st = states(lid, all_ids)
    legend_y = TOP + 7 * (ROW_H + GAP) + 16
    title = f"Where {lid} fits: {TITLES[lid]}" if lid in TITLES else f"Where {lid} fits in xv6"
    f = Map("map" + lid.replace(".", ""), title, legend_y + 10)
    for k, (row, x, w, label, sub) in PIECES.items():
        y = TOP + row * (ROW_H + GAP)
        s = st[k]
        if s == "now":
            f.rect(x, y, w, ROW_H, "a af", 6)
            tc, sc, wt = "ta", "ta", 700
        elif s == "built":
            f.rect(x, y, w, ROW_H, "s fs" if k == "hw" else "s f", 6)
            tc, sc, wt = "t", "tm", 600
        elif k in OPTIONAL:
            # an extension nobody has started: grey fill and a dotted edge, apart from "later"
            f.add(f'<rect class="m fs" x="{fmt(x + 0.75)}" y="{fmt(y + 0.75)}" width="{fmt(w - 1.5)}" '
                  f'height="{fmt(ROW_H - 1.5)}" rx="6" {SW} stroke-dasharray="1.5 3" stroke-linecap="round"/>')
            tc, sc, wt = "tm", "tm", 600
        else:
            f.rect(x + 0.75, y + 0.75, w - 1.5, ROW_H - 1.5, "m", 6, dash=True)
            tc, sc, wt = "tm", "tm", 600
        if k in OPTIONAL and s == "built":
            sub = "optional, built"
        f.text(x + w / 2, y + 18, label, tc, 16, "middle", wt)
        f.text(x + w / 2, y + 33, sub, sc, 12, "middle")
    # legend
    ly = legend_y
    f.rect(X0, ly - 10, 12, 12, "a af", 3)
    f.text(X0 + 18, ly, "this lesson", "ta", 13, weight=600)
    f.rect(118, ly - 10, 12, 12, "s f", 3)
    f.text(136, ly, "built", "t", 13)
    f.rect(190, ly - 10, 12, 12, "m", 3, dash=True)
    f.text(208, ly, "still to come", "tm", 13)
    f.add(f'<rect class="m fs" x="306" y="{fmt(ly - 10)}" width="12" height="12" rx="3" {SW} stroke-dasharray="1.5 3" stroke-linecap="round"/>')
    f.text(324, ly, "optional extension", "tm", 13)
    return f


def main():
    only = sys.argv[1:]
    all_ids = [lid for lid, _ in lessons()]
    missing = [lid for lid in all_ids if lid not in LESSON_PIECES]
    if missing:
        sys.exit(f"no piece for lessons: {missing}")
    n = 0
    for lid, mod in lessons():
        if only and not any(lid.startswith(o) for o in only):
            continue
        svg = draw(lid, all_ids).svg()
        svg.encode("ascii")
        d = os.path.join(LESSONS, mod, "figures")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, f"{lid}-map.svg"), "w") as fh:
            fh.write(svg)
        n += 1
    print(f"{n} maps written")


if __name__ == "__main__":
    main()
