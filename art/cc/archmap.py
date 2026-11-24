"""The cc track's architecture map, one copy per lesson.

    python3 -B art/cc/archmap.py       writes tracks/cc/lessons/<module>/figures/NN.LL-map.svg

The same map every time: the pieces a program passes through, from its source text to a status
coming back. Lessons reference it as

    ![Where NN.LL fits](figures/NN.LL-map.svg)

Two bands. Band 1 is the compiler, one frame labelled cc: source text in, then the scanner, the
preprocessor, the parser, types and the code generator, left to right, and assembly out. The
scanner, the parser and the code generator are boxes of cells, one cell a piece a lesson adds;
under the scanner and the parser, one wide thin box for the errors that point at the source, and
under types and the code generator one for arrays, strings and structs. Band 2, under the frame,
reads left to right again from the assembly coming down: the assembler, the linker (the runtime,
rt/start.S and rt/link.ld, feeding it from below), the bare machine in QEMU, the exit status. A
parallel lane under it is gcc, for the same machine: the same source text, linked with the same
runtime, run on the same machine, and a small "=" joining the two statuses.

Who builds what follows the design of the track's lessons (and tracks/cc/NOTES.md, "Where the
code is, lesson by lesson"): the frame with its two arrows is 00.01's (the driver: read a file,
write assembly); the assembler, the linker, the runtime, the machine and the status are 00.02's;
gcc's lane and the "=" 00.03's; then a cell a lesson. 02.04 and 02.05 both light "every operator"
in the parser and in the code generator. The preprocessor (module 08), types (06), arrays,
strings and structs (07), statements (03), declarations and scopes (05), branches (03) and calls
and frames (04) are still to come in every map of step 1. Nothing names a function or a file but
the runtime's two.

In each lesson's copy the lesson's own pieces are in the accent colour, those of earlier lessons
solid, those still to come dashed and muted. An arrow takes the state of the piece it belongs to;
an arrow between two boxes takes the later of the two, and the preprocessor and types, which do
not exist in this step, let the flow pass through them (scanner to parser, parser to code
generator).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from figlib import Fig, write  # noqa: E402

# (id, title): the design's lesson titles
LESSONS = [
    ("00.01", "From a number to assembly"),
    ("00.02", "What the assembler, the linker and the machine do with it"),
    ("00.03", "The same answer as gcc"),
    ("01.01", "A stream of tokens"),
    ("01.02", "Longest match"),
    ("01.03", "Identifiers and keywords"),
    ("01.04", "Comments, character constants and strings"),
    ("01.05", "Errors that point at the source"),
    ("02.01", "A grammar, and a function for each rule"),
    ("02.02", "The syntax tree"),
    ("02.03", "Code from a tree: registers as a stack"),
    ("02.04", "Precedence and associativity: the whole table"),
    ("02.05", "Unary operators and comparisons"),
    ("02.06", "Out of registers: spilling to memory"),
]
LATER = "99"          # a lesson past this step: drawn dashed in every map here

# Who builds each piece: key -> the lessons that light it.
OWNER = {
    "frame": {"00.01"},
    "scanner": {"01.01"}, "s1": {"01.01"}, "s2": {"01.02"}, "s3": {"01.03"}, "s4": {"01.04"},
    "errors": {"01.05"},
    "prep": {"08"}, "types": {"06"}, "arrays": {"07"},
    "parser": {"02.01"}, "p1": {"02.01"}, "p2": {"02.02"}, "p3": {"02.04", "02.05"}, "p4": {"03"}, "p5": {"05"},
    "codegen": {"02.03"}, "g1": {"02.03"}, "g2": {"02.04", "02.05"}, "g3": {"02.06"}, "g4": {"03"}, "g5": {"04"},
    "assembler": {"00.02"}, "linker": {"00.02"}, "runtime": {"00.02"}, "machine": {"00.02"}, "status": {"00.02"},
    "gcc": {"00.03"}, "status2": {"00.03"}, "same": {"00.03"},
}

# Band 1
FX, FY, FW = 20, 46, 600                     # the frame
BY, BH = 68, 154                              # the boxes of band 1
CELL_Y, CELL_H, CELL_GAP = 30, 20, 4.5
BOXES = {  # key -> (name lines, x, w, cells [(key, label)])
    "scanner": (["scanner"], 32, 128, [("s1", "numbers and operators"), ("s2", "longest match"),
                                       ("s3", "names and keywords"), ("s4", "comments and literals")]),
    "prep": (["pre-", "processor"], 178, 54, []),
    "parser": (["parser"], 250, 150, [("p1", "a function for each rule"), ("p2", "the tree"),
                                      ("p3", "every operator"), ("p4", "statements"),
                                      ("p5", "declarations and scopes")]),
    "types": (["types"], 418, 46, []),
    "codegen": (["code generator"], 482, 126, [("g1", "registers as a stack"), ("g2", "every operator"),
                                               ("g3", "spilling"), ("g4", "branches"), ("g5", "calls and frames")]),
}
THIN_Y, THIN_H = 232, 22
THIN = {"errors": ("errors that point at the source", 32, 400 - 32),
        "arrays": ("arrays, strings and structs", 418, 548 - 418)}
FB = THIN_Y + THIN_H + 10                     # the frame's bottom

# Band 2
L1, LH = 304, 44                              # lane 1 (ours) top and height
RT_Y, RT_H = 360, 54                          # the runtime
L2, L2H = 428, 40                             # lane 2 (gcc)
ASM_X, LNK_X, BW2 = 40, 170, 104
MCH_X, MCH_W = 300, 148
ST_X, ST_W = 474, 96
GUTTER = FB + 18                              # where the assembly runs left
SRC = (24, 10, 104, 24)                       # the source text chip: x, y, w, h
MARGIN = 10                                   # the corridor down the left, to gcc
HEIGHT = 506


def state(key, lid):
    owners = OWNER[key]
    if lid in owners:
        return "here"
    if min(owners) < lid:
        return "built"
    return "later"


def worst(*states):
    """The state of an arrow between pieces: the latest of them."""
    for s in ("later", "here", "built"):
        if s in states:
            return s
    return "built"


STYLE = {  # state -> (box class, dashed, name text class, weight, cell class, cell text class)
    "here": ("a af", False, "ta", 700),
    "built": ("s f", False, "t", 600),
    "later": ("m f", True, "tm", 500),
}


def draw(lid, title):
    f = Fig("map" + lid.replace(".", ""), f"Where {lid} fits: {title}", HEIGHT)

    def arrow(pts, st, head=True):
        cls = {"here": "a", "built": "s", "later": "m"}[st]
        f.poly(pts, cls, arrow=head, dash=st == "later")

    def piece(x, y, w, h, st, rx=8):
        cls, dash, _, _ = STYLE[st]
        f.rect(x, y, w, h, cls, rx, dash=dash)

    fr = state("frame", lid)
    mid = BY + 18 - 4                         # the flow's height through band 1: the boxes' names
    # ---- the arrows first, so the boxes sit over their ends
    sx, sy, sw, sh = SRC
    scan_x = BOXES["scanner"][1]
    # source text in: down from the chip, into the scanner's top
    arrow([(sx + 40, sy + sh + 1), (sx + 40, BY - 2)], fr)
    # through the compiler: scanner -> preprocessor -> parser -> types -> code generator
    order = ["scanner", "prep", "parser", "types", "codegen"]
    ends = {"scanner": "scanner", "prep": None, "parser": "parser", "types": None, "codegen": "codegen"}
    for a, b in zip(order, order[1:]):
        # the preprocessor and types let the flow through: the arrow is the real pieces' on each side
        left = a if ends[a] else order[order.index(a) - 1]
        right = b if ends[b] else order[order.index(b) + 1]
        st = worst(state(left, lid), state(right, lid))
        ax = BOXES[a][1] + BOXES[a][2]
        arrow([(ax + 1, mid), (BOXES[b][1] - 2, mid)], st)
    # assembly out: down from the code generator, out of the frame, left along the gutter, into the assembler
    cgx, _, cgw = BOXES["codegen"][1], 0, BOXES["codegen"][2]
    drop = cgx + cgw - 20
    arrow([(drop, BY + BH + 1), (drop, GUTTER), (ASM_X + BW2 / 2, GUTTER), (ASM_X + BW2 / 2, L1 - 2)], fr)
    # band 2, lane 1
    l1m = L1 + LH / 2
    arrow([(ASM_X + BW2 + 1, l1m), (LNK_X - 2, l1m)], state("assembler", lid))
    arrow([(LNK_X + BW2 + 1, l1m), (MCH_X - 2, l1m)], state("linker", lid))
    arrow([(MCH_X + MCH_W + 1, l1m), (ST_X - 2, l1m)], state("status", lid))
    rcx = LNK_X + BW2 / 2
    arrow([(rcx, RT_Y - 1), (rcx, L1 + LH + 2)], state("runtime", lid))
    # lane 2: the same source text down the left margin to gcc; the runtime into gcc; gcc to the machine
    l2m = L2 + L2H / 2
    g = state("gcc", lid)
    arrow([(sx - 1, sy + sh / 2), (MARGIN, sy + sh / 2), (MARGIN, l2m), (ASM_X - 2, l2m)], g)
    arrow([(rcx, RT_Y + RT_H + 1), (rcx, L2 - 2)], g)
    arrow([(LNK_X + BW2 + 1, l2m), (MCH_X - 2, l2m)], g)
    arrow([(MCH_X + MCH_W + 1, l2m), (ST_X - 2, l2m)], state("status2", lid))

    # ---- the frame
    cls, dash, tcls, wt = STYLE[fr]
    f.rect(FX, FY, FW, FB - FY, cls.split()[0], 12, dash=dash)
    lab_w = 128
    lx = FX + FW - lab_w - 16
    f.rect(lx, FY - 10, lab_w, 20, "f", 0, sw=False)
    f.rich(lx + lab_w / 2, FY + 5, [("cc", tcls, True), ("  the compiler", "ta" if fr == "here" else "tm", False)],
           size=13, anchor="middle", weight=700)
    # the source text chip, and the assembly's label
    f.rect(sx, sy, sw, sh, "a af" if fr == "here" else "s fs", sh / 2)
    f.text(sx + sw / 2, sy + sh / 2 + 4.3, "source text", "ta" if fr == "here" else "t", 12, "middle", mono=True)
    f.text(drop - 8, GUTTER - 5, "assembly", "ta" if fr == "here" else "t", 12, "end", mono=True)

    # ---- band 1's boxes
    for key, (names, x, w, cells) in BOXES.items():
        st = state(key, lid)
        piece(x, BY, w, BH, st)
        _, _, tc, wt = STYLE[st]
        if cells:
            f.text(x + w / 2, BY + 19, names[0], tc, 13, "middle", wt)
            for k, (ck, lab) in enumerate(cells):
                cs = state(ck, lid)
                ccls, cdash, ctc, _ = STYLE[cs]
                cy = BY + CELL_Y + k * (CELL_H + CELL_GAP)
                f.rect(x + 6, cy, w - 12, CELL_H, ccls, 4, dash=cdash)
                f.text(x + w / 2, cy + 14, lab, ctc, 10.5, "middle", 600 if cs == "here" else None)
        else:
            y0 = BY + BH / 2 - (len(names) - 1) * 7
            for k, nm in enumerate(names):
                f.text(x + w / 2, y0 + k * 14 + 4, nm, tc, 11.5, "middle", wt)
    for key, (lab, x, w) in THIN.items():
        st = state(key, lid)
        piece(x, THIN_Y, w, THIN_H, st, 6)
        f.text(x + w / 2, THIN_Y + 15, lab, STYLE[st][2], 11, "middle", 600 if st == "here" else None)

    # ---- band 2
    def box2(key, x, y, w, h, lines, mono_line=None):
        st = state(key, lid)
        piece(x, y, w, h, st)
        _, _, tc, wt = STYLE[st]
        n = len(lines)
        lh = 14.5
        y0 = y + h / 2 - (n - 1) * lh / 2 + 4.5
        for k, ln in enumerate(lines):
            if mono_line is not None and k >= mono_line:
                f.text(x + w / 2, y0 + k * lh, ln, tc if st == "here" else "tm", 11, "middle", mono=True)
            else:
                f.text(x + w / 2, y0 + k * lh, ln, tc, 12.5, "middle", wt)
        return st

    box2("assembler", ASM_X, L1, BW2, LH, ["assembler"])
    box2("linker", LNK_X, L1, BW2, LH, ["linker"])
    box2("runtime", LNK_X, RT_Y, BW2, RT_H, ["the runtime", "rt/start.S", "rt/link.ld"], mono_line=1)
    box2("machine", MCH_X, L1, MCH_W, L2 + L2H - L1, ["the bare machine", "in QEMU"])
    box2("gcc", ASM_X, L2, LNK_X + BW2 - ASM_X, L2H, ["gcc, for the same machine"])
    for key, y in (("status", L1 + LH / 2 - 12), ("status2", L2 + L2H / 2 - 12)):
        st = state(key, lid)
        cls, dash, tc, wt = STYLE[st]
        f.rect(ST_X, y, ST_W, 24, cls, 12, dash=dash)
        f.text(ST_X + ST_W / 2, y + 16.5, "exit status", tc, 12, "middle", mono=True)
    # "=" between the two statuses: same
    st = state("same", lid)
    cx, top, bot = ST_X + ST_W / 2, L1 + LH / 2 + 12, L2 + L2H / 2 - 12
    cy = (top + bot) / 2
    sc = {"here": "a", "built": "s", "later": "m"}[st]
    f.line(cx, top + 1, cx, cy - 12, sc, dash=st == "later")
    f.line(cx, cy + 12, cx, bot - 1, sc, dash=st == "later")
    f.circle(cx, cy, 11, f"{sc} f", dash=st == "later")
    f.path(f"M{cx - 5} {cy - 3} H{cx + 5} M{cx - 5} {cy + 3} H{cx + 5}", sc)
    f.text(cx + 18, cy + 4.5, "same", STYLE[st][2], 12.5, weight=STYLE[st][3])

    # ---- legend
    ly = HEIGHT - 12
    x = 20
    for cls, dash, lab, tcls in (("a af", False, f"{lid}: this lesson", "ta"), ("s f", False, "built earlier", "t"),
                                 ("m f", True, "still to come", "tm")):
        f.rect(x, ly - 13, 22, 16, cls, 4, dash=dash)
        f.text(x + 30, ly, lab, tcls, 14, weight=600 if tcls == "ta" else None)
        x += 30 + len(lab) * 14 * 0.56 + 28
    return f


def main():
    ids = [lid for lid, _ in LESSONS]
    assert ids == sorted(ids) and len(set(ids)) == len(ids)
    every = set().union(*OWNER.values())
    for lid in ids:                       # every lesson of the step lights something
        assert lid in every, lid
    for lid, title in LESSONS:
        write(f"{lid}-map", draw(lid, title))


if __name__ == "__main__":
    main()
