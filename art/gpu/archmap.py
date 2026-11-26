"""The gpu track's map, one copy per lesson (plans/gpu-00-01-lessons.md, "The map").

    python3 -B art/gpu/archmap.py       writes figures/NN.LL-map.svg for 00.01 to 01.05 into
                                        tracks/gpu/lessons/00-the-workbench/ and
                                        tracks/gpu/lessons/01-matrix-multiply-on-the-cpu/

Lessons reference it as

    ![Where NN.LL fits](figures/NN.LL-map.svg)

and the track's overview page shows 00.01's copy as the track's architecture. figs01.py (and any
later module's generator) imports this file for svg(lid) or draw(lid) and LESSONS.

The same picture in every lesson: the whole track as a stack, read bottom to top.

    bottom, full width     the workbench (00): plain version, checker, timer
    above it, left         on the CPU: matrix multiply (01), five rungs in a row:
                           ijk, ikj, simd, blocked, threads
    above it, right        on the GPU: one row a module, 02 at the bottom to 08 at the top
    top, full width        a small model on your kernels, against PyTorch (09)

In lesson NN.LL its own piece is in the accent colour, the pieces of earlier lessons solid, later
ones dashed and muted. The pieces of modules 00 and 01 belong to one lesson each (OWNER); a GPU row
and the top bar belong to their whole module (a row in that module's lessons is lit whole). A box
that holds pieces (a module, a frame) is solid once any piece in it is built, and never takes the
accent itself. The key sits in the corner the CPU frame leaves free, top left.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from figlib import Art, sans, r1, write  # noqa: E402

# (id, the piece it lights): the lessons of modules 00 and 01, in order
LESSONS = [
    ("00.01", "plain version"),
    ("00.02", "checker"),
    ("00.03", "timer"),
    ("01.01", "ijk"),
    ("01.02", "ikj"),
    ("01.03", "simd"),
    ("01.04", "blocked"),
    ("01.05", "threads"),
]
OWNER = {piece: lid for lid, piece in LESSONS}
WORKBENCH = ["plain version", "checker", "timer"]
RUNGS = ["ijk", "ikj", "simd", "blocked", "threads"]
# the GPU column, bottom to top, and the top bar: (label, the modules it stands for)
GPU_ROWS = [
    ("element-wise kernels (02)", {"02"}),
    ("matrix multiply (03)", {"03"}),
    ("sums across a block: RMS norm, softmax (04)", {"04"}),
    ("rotary positions and the KV cache in blocks (05)", {"05"}),
    ("attention: one token (06), a whole prompt (07)", {"06", "07"}),
    ("half precision (08)", {"08"}),
]
TOP = ("a small model on your kernels, against PyTorch (09)", {"09"})

# what each state looks like: (box class, dashed, text class, weight)
STYLE = {
    "here": ("a af", False, "ta", 700),
    "built": ("s f", False, "t", 600),
    "later": ("m f", True, "tm", 500),
}

# the layout
L, R = 16, 624                                 # the page's margins
TOP_Y, TOP_H = 8, 26                           # the top bar
MID_Y = 44                                     # the CPU and GPU frames' tops (the GPU frame's; the CPU's is lower)
CPU_X, CPU_W = L, 220                          # the left third
GPU_X = CPU_X + CPU_W + 10                     # the right two thirds
GPU_W = R - GPU_X
ROW_H, ROW_P = 20, 25                          # a GPU row's height, its pitch
FRAME_T = 24                                   # a frame's title band
MID_B = MID_Y + FRAME_T + (len(GPU_ROWS) - 1) * ROW_P + ROW_H + 8     # both frames' bottoms
MM_H, RUNG_H = 50, 20                          # matrix multiply's box, a rung
CPU_Y = MID_B - (FRAME_T + MM_H + 8)           # the CPU frame: only as tall as its box
WB_Y = MID_B + 10                              # the workbench
PIECE_H = 22
WB_H = 24 + PIECE_H + 8
HEIGHT = WB_Y + WB_H + 8


def check():
    """The map's facts, against the design: the order, the owners, the module numbers."""
    ids = [lid for lid, _ in LESSONS]
    assert ids == ["00.01", "00.02", "00.03", "01.01", "01.02", "01.03", "01.04", "01.05"], ids
    assert [OWNER[p] for p in WORKBENCH] == ["00.01", "00.02", "00.03"]
    assert [OWNER[p] for p in RUNGS] == ["01.01", "01.02", "01.03", "01.04", "01.05"]
    for label, mods in GPU_ROWS + [TOP]:
        assert re.findall(r"\((\d\d)\)", label) == sorted(mods), label
    assert sorted(set().union(*(m for _, m in GPU_ROWS))) == [f"{k:02}" for k in range(2, 9)]
    assert HEIGHT <= 300, HEIGHT


def state(piece, lid):
    """here, built or later: piece is a lesson's (OWNER) or a set of modules (a GPU row, the top)."""
    if isinstance(piece, str):
        own = OWNER[piece]
        return "here" if own == lid else "built" if own < lid else "later"
    mod = lid[:2]
    return "here" if mod in piece else "built" if max(piece) < mod else "later"


def holder(states):
    """A box that holds pieces: solid once any of them is built (or being built), dashed before."""
    return "later" if all(s == "later" for s in states) else "built"


def draw(lid):
    assert lid in OWNER.values(), lid
    a = Art("map" + lid.replace(".", ""), f"Where {lid} fits", HEIGHT)

    def box(x, y, w, h, st, rx=8):
        cls, dash, _, _ = STYLE[st]
        a.box(r1(x), r1(y), r1(w), h, cls, rx=rx, dash=dash)

    def label(x, y, s, st, size=11.5, anchor="middle", weight=None, mono=False):
        _, _, tcls, wt = STYLE[st]
        a.text(r1(x), r1(y), s, tcls, size, anchor, weight or wt, mono)

    def frame(x, y, w, h, title, st):
        """A frame round a group of modules: an outline, its title top left."""
        cls = "m" if st == "later" else "s"
        a.box(r1(x), r1(y), r1(w), r1(h), cls, rx=12, dash=st == "later")
        label(x + 12, y + 16, title, st, 12, "start", 700)

    # ---- the top bar: module 09
    s, mods = TOP
    st = state(mods, lid)
    box(L, TOP_Y, R - L, TOP_H, st)
    label((L + R) / 2, TOP_Y + TOP_H / 2 + 4.2, s, st, 12)
    assert sans(s, 12) + 24 <= R - L

    # ---- on the GPU: one row a module, bottom to top
    sts = [state(m, lid) for _, m in GPU_ROWS]
    frame(GPU_X, MID_Y, GPU_W, MID_B - MID_Y, "on the GPU", holder(sts))
    rx, rw = GPU_X + 10, GPU_W - 20
    for k, ((s, mods), st) in enumerate(zip(GPU_ROWS, sts)):
        y = MID_B - 8 - ROW_H - k * ROW_P                  # k = 0 is the bottom row
        box(rx, y, rw, ROW_H, st, rx=6)
        label(rx + rw / 2, y + ROW_H / 2 + 4, s, st, 11.5)
        assert sans(s, 11.5) + 16 <= rw, s
    assert MID_B - 8 - ROW_H - (len(GPU_ROWS) - 1) * ROW_P == MID_Y + FRAME_T

    # ---- on the CPU: matrix multiply (01) and its five rungs
    sts = [state(p, lid) for p in RUNGS]
    hst = holder(sts)
    frame(CPU_X, CPU_Y, CPU_W, MID_B - CPU_Y, "on the CPU", hst)
    mx, my, mw = CPU_X + 8, CPU_Y + FRAME_T, CPU_W - 16
    box(mx, my, mw, MM_H, hst)
    label(mx + mw / 2, my + 16, "matrix multiply (01)", hst, 11.5)
    size, gap = 10.5, 4
    ws = [sans(p, size) + 6 for p in RUNGS]
    pad = (mw - 12 - sum(ws) - gap * (len(RUNGS) - 1)) / len(RUNGS)   # share what is left evenly
    assert pad >= 0, pad
    x, ry = mx + 6, my + MM_H - 6 - RUNG_H
    for p, w, st in zip(RUNGS, ws, sts):
        box(x, ry, w + pad, RUNG_H, st, rx=5)
        label(x + (w + pad) / 2, ry + RUNG_H / 2 + 3.7, p, st, size, mono=False)
        x += w + pad + gap
    assert abs(x - gap - (mx + mw - 6)) < 0.01

    # ---- the workbench (00): its three pieces
    sts = [state(p, lid) for p in WORKBENCH]
    hst = holder(sts)
    box(L, WB_Y, R - L, WB_H, hst, rx=10)
    label((L + R) / 2, WB_Y + 16, "the workbench (00)", hst, 12, weight=700)
    pg = 16
    pw = (R - L - 2 * 12 - 2 * pg) / 3
    for k, (p, st) in enumerate(zip(WORKBENCH, sts)):
        x = L + 12 + k * (pw + pg)
        box(x, WB_Y + 24, pw, PIECE_H, st, rx=6)
        label(x + pw / 2, WB_Y + 24 + PIECE_H / 2 + 4.2, p, st, 12)

    # ---- the key, in the corner the CPU frame leaves free
    ky = MID_Y + 6
    assert ky + 3 * 22 <= CPU_Y - 6
    for k, (st, s) in enumerate((("here", f"{lid}: this lesson"), ("built", "built earlier"),
                                 ("later", "still to come"))):
        y = ky + k * 22
        box(CPU_X + 4, y, 24, 14, st, rx=4)
        label(CPU_X + 36, y + 11, s, st, 11.5, "start", 600 if st == "here" else 400)
    return a


def svg(lid):
    """The map as lesson lid's copy: its piece in the accent colour."""
    return draw(lid).svg()


def main():
    check()
    for lid, _ in LESSONS:
        write(f"{lid}-map", draw(lid))


if __name__ == "__main__":
    main()
