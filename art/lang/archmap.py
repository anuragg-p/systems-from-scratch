"""The lang track's architecture map for chapter 1, one copy per lesson.

    python3 -B art/lang/archmap.py      writes tracks/lang/lessons/01-introduction/figures/01.LL-map.svg

The same map every time: the system as it stands at the end of chapter 1 (plans/lang-01-lessons.md,
"The map"). Lessons reference it as

    ![Where 01.LL fits](figures/01.LL-map.svg)

and the track's overview page shows 01.01's copy as the track's architecture.

At the top, the program's text (programs/), with the same program in C, gcd.c, to its left. Three
roads run down from the text, side by side:

    left     the first interpreter, with the prompt as a cell inside it; out of it, output
    middle   the translator to C, then the computer's own C compiler, assembler and linker (gcd.c
             entering the compiler from the left, rt feeding the linker from the side); out of
             them, a program for your computer, then output
    right    one frame, mote: scanner -> parser -> semantic analysis (the symbol table a cell
             inside it), then a fork: down-left the tree walk, to output; down-right the
             improver -> the code generator, whose assembly goes down out of the frame into the
             machine, which gcd.s, by hand, also feeds from the right; out of it, output

Across the bottom, one thin wide box takes the four outputs: agree, every way the same answer.

Who lights what (OWNER): 01.01 the machine, gcd.s and the machine's output; 01.02 the program's
text, gcd.c and rt, with their arrows into the C tools and what comes out of them (the program
for your computer and its output: lesson 01.02 already builds and runs ./gcd from gcd.c); 01.03
the first interpreter and its road; 01.04 the translator and its road; 01.05 the prompt cell and
the agree bar; 01.06 the scanner, the frame and every arrow between the phases inside it (the
driver), and the right road into it; 01.07 the parser; 01.08 semantic analysis and the symbol
table; 01.09 the tree walk and its output; 01.10 the code generator and the assembly it writes;
01.11 the improver. The computer's C compiler, assembler and linker are not ours: hollow, with a
dashed outline in every copy, muted until lesson 01.02 first uses them, in the accent colour in
01.04 (lit with the translator), plain otherwise. An output's line into the agree bar is lit by
the lesson agree gains that way: the first interpreter's and the C program's with agree (01.05),
the tree walk's in 01.09, the machine's in 01.10 (-S) and again in 01.11 (-O), and never before
the output and the bar themselves. Nothing on the map names a function.

In each lesson's copy the lesson's own pieces are in the accent colour, those of earlier lessons
solid, those still to come dashed and muted. The drawing primitives (Fig, and the sanitizer check
sane) are the cc track's, art/cc/figlib.py, loaded under its own module name so that a figlib.py
of this track's own can sit beside this file.
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.dont_write_bytecode = True
_spec = importlib.util.spec_from_file_location("cc_figlib", os.path.join(ROOT, "art", "cc", "figlib.py"))
_cc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cc)
Fig, sane = _cc.Fig, _cc.sane

OUT = os.path.join(ROOT, "tracks", "lang", "lessons", "01-introduction", "figures")

# (id, title): the design's lesson titles (plans/lang-01-lessons.md, "Lesson titles")
LESSONS = [
    ("01.01", "A machine, and a program written in its language"),
    ("01.02", "Your language, and the programs you want it to run"),
    ("01.03", "An interpreter: the program run from its text"),
    ("01.04", "A translator: to C, and from there to the machine"),
    ("01.05", "The tools around a language: a prompt and a test runner"),
    ("01.06", "The phases of a compiler, and the first: a scanner"),
    ("01.07", "The parser: tokens into a tree"),
    ("01.08", "Semantic analysis: the syntax tree and the symbol table"),
    ("01.09", "Walking the tree: an interpreter built on the front end"),
    ("01.10", "Target code: loads, stores, tests and branches"),
    ("01.11", "Code improvement: variables kept in registers"),
]

# Who builds each piece: key -> the lessons that light it.
OWNER = {
    "machine": {"01.01"}, "gcds": {"01.01"}, "out_machine": {"01.01"},
    "text": {"01.02"}, "gcdc": {"01.02"}, "rt": {"01.02"}, "program": {"01.02"}, "out_c": {"01.02"},
    "interp": {"01.03"}, "out_interp": {"01.03"},
    "translator": {"01.04"}, "ctools": {"01.04"},
    "prompt": {"01.05"}, "agree": {"01.05"},
    # each output's line into agree: the lesson agree gains that way (01.10 and 01.11 both add a
    # way through the machine: -S, then -O)
    "join_interp": {"01.05"}, "join_c": {"01.05"}, "join_tree": {"01.09"}, "join_machine": {"01.10", "01.11"},
    "frame": {"01.06"}, "scanner": {"01.06"},
    "parser": {"01.07"},
    "semantic": {"01.08"}, "symtab": {"01.08"},
    "treewalk": {"01.09"}, "out_tree": {"01.09"},
    "codegen": {"01.10"}, "assembly": {"01.10"},
    "improver": {"01.11"},
}
# Pieces that exist before the lesson that lights them: key -> the first lesson that uses them.
SINCE = {"ctools": "01.02"}

W, HEIGHT = 640, 518

# the program's text, at the top, centred; gcd.c to its left
TX, TY, TW, TH = 250, 8, 140, 42
TMID = TY + 21                                  # where the left and right roads leave it
GC_X, GC_Y, GC_W, GC_H = 136, 44, 48, 20        # gcd.c

ROW = 88                                        # the top of the first box of every road

# left road: the first interpreter, the prompt a cell inside it
IX, IW, IH = 16, 108, 62
# middle road: the translator, the C tools, the program it makes
MX, MW = 196, 132
MC = MX + MW / 2                                # 262: straight down from the text's bottom
TRH = 26
CT_Y, CT_H = 132, 80                            # the computer's C compiler, assembler and linker
CT_LINES = ["the computer's", "C compiler,", "assembler", "and linker"]
CT_LH, CT_B0 = 16, CT_Y + 19                    # line height, first baseline
RT_X, RT_W, RT_H = 146, 28, 20                  # rt, in the corridor left of the C tools
PG_Y, PG_W, PG_H = 230, 104, 36                 # a program for your computer

# right road: the frame mote
FX, FY, FW, FB = 344, 70, 282, 332
FC = 485                                        # the phases' column
PW, PH = 150, 26                                # scanner, parser
SC_Y, PA_Y = ROW, 130
SE_Y, SE_H = 172, 50                            # semantic analysis, with its cell
FORK = SE_Y + SE_H + 14
TW_X, TW_W = 356, 96                            # the tree walk, down-left
IM_X, IM_W = 504, 110                           # the improver and the code generator, down-right
BR_Y, CG_Y = 250, 292                           # their rows
DROP = 530                                      # where the assembly goes down to the machine

# the machine, bottom right, gcd.s by hand feeding it from the right
MA_X, MA_Y, MA_W, MA_H = 446, 360, 100, 36
GS_X, GS_W = 574, 54

OUT_Y, OUT_H, OUT_W = 412, 20, 56               # the four outputs
AG_X, AG_Y, AG_W, AG_H = 16, 448, 610, 22       # agree


def state(key, lid):
    if lid in OWNER[key]:
        return "here"
    if min(OWNER[key]) < lid or SINCE.get(key, "99") <= lid:
        return "built"
    return "later"


def worst(*states):
    """The state of an arrow between pieces: the latest of them."""
    for s in ("later", "here", "built"):
        if s in states:
            return s
    return "built"


STYLE = {  # state -> (box class, dashed, name text class, weight)
    "here": ("a af", False, "ta", 700),
    "built": ("s f", False, "t", 600),
    "later": ("m f", True, "tm", 500),
}
STROKE = {"here": "a", "built": "s", "later": "m"}


def draw(lid, title):
    f = Fig("map" + lid.replace(".", ""), f"Where {lid} fits: {title}", HEIGHT, W)
    st = {k: state(k, lid) for k in OWNER}

    def arrow(pts, s, head=True):
        f.poly(pts, STROKE[s], arrow=head, dash=s == "later")

    def piece(x, y, w, h, s, rx=8):
        cls, dash, _, _ = STYLE[s]
        f.rect(x, y, w, h, cls, rx, dash=dash)

    def name(x, y, s, key, size=13):
        _, _, tc, wt = STYLE[st[key]]
        f.text(x, y, s, tc, size, "middle", wt)

    def box(key, x, y, w, h, label, size=13, rx=8):
        piece(x, y, w, h, st[key], rx)
        name(x + w / 2, y + h / 2 + size * 0.36, label, key, size)

    def mono(x, y, s, key, size=11, anchor="middle"):
        s_ = st[key]
        f.text(x, y, s, STYLE[s_][2], size, anchor, 600 if s_ == "here" else None, mono=True)

    def cell(key, x, y, w, h, label):
        s_ = st[key]
        cls, dash, tc, _ = STYLE[s_]
        f.rect(x, y, w, h, cls, 4, dash=dash)
        f.text(x + w / 2, y + h / 2 + 3.8, label, tc, 10.5, "middle", 600 if s_ == "here" else None)

    def output(key, join, cx):
        s_ = st[key]
        cls, dash, tc, _ = STYLE[s_]
        f.rect(cx - OUT_W / 2, OUT_Y, OUT_W, OUT_H, cls, OUT_H / 2, dash=dash)
        f.text(cx, OUT_Y + OUT_H / 2 + 3.9, "output", tc, 11, "middle", 600 if s_ == "here" else None, mono=True)
        arrow([(cx, OUT_Y + OUT_H + 1), (cx, AG_Y - 2)], worst(s_, st["agree"], st[join]))

    ic = IX + IW / 2
    ct_line = [CT_B0 + k * CT_LH - 4 for k in range(len(CT_LINES))]   # the middle of each line of the C tools
    tw_c, im_c = TW_X + TW_W / 2, IM_X + IM_W / 2
    ma_c = MA_X + MA_W / 2
    rt_y = ct_line[3] - RT_H / 2

    # ---- the arrows first, so the boxes sit over their ends
    # left road: out of the text's left side, along, down into the first interpreter
    arrow([(TX - 1, TMID), (ic, TMID), (ic, ROW - 2)], st["interp"])
    arrow([(ic, ROW + IH + 1), (ic, OUT_Y - 2)], st["out_interp"])
    # middle road: straight down from the text into the translator, on into the C tools
    arrow([(MC, TY + TH + 1), (MC, ROW - 2)], st["translator"])
    arrow([(MC, ROW + TRH + 1), (MC, CT_Y - 2)], st["translator"])
    arrow([(MC, CT_Y + CT_H + 1), (MC, PG_Y - 2)], st["program"])
    arrow([(MC, PG_Y + PG_H + 1), (MC, OUT_Y - 2)], st["out_c"])
    # gcd.c down the corridor and into the compiler; rt into the linker
    gx = GC_X + GC_W / 2
    arrow([(gx, GC_Y + GC_H + 1), (gx, ct_line[1]), (MX - 2, ct_line[1])], st["gcdc"])
    arrow([(RT_X + RT_W + 1, ct_line[3]), (MX - 2, ct_line[3])], st["rt"])
    # right road: out of the text's right side, along, down through the frame's top into the scanner
    arrow([(TX + TW + 1, TMID), (FC, TMID), (FC, SC_Y - 2)], st["frame"])
    # the driver: scanner -> parser -> semantic analysis -> the fork -> improver -> code generator
    fr = st["frame"]
    arrow([(FC, SC_Y + PH + 1), (FC, PA_Y - 2)], fr)
    arrow([(FC, PA_Y + PH + 1), (FC, SE_Y - 2)], fr)
    arrow([(FC, SE_Y + SE_H + 1), (FC, FORK), (tw_c, FORK), (tw_c, BR_Y - 2)], fr)
    arrow([(FC, SE_Y + SE_H + 1), (FC, FORK), (im_c, FORK), (im_c, BR_Y - 2)], fr)
    arrow([(im_c, BR_Y + PH + 1), (im_c, CG_Y - 2)], fr)
    # out of the frame: the tree walk's output; the code generator's assembly, down into the machine
    arrow([(tw_c, BR_Y + PH + 1), (tw_c, OUT_Y - 2)], st["out_tree"])
    arrow([(DROP, CG_Y + PH + 1), (DROP, MA_Y - 2)], st["assembly"])
    # gcd.s, by hand, into the machine from the right; the machine's output
    arrow([(GS_X - 1, MA_Y + MA_H / 2), (MA_X + MA_W + 2, MA_Y + MA_H / 2)], st["gcds"])
    arrow([(ma_c, MA_Y + MA_H + 1), (ma_c, OUT_Y - 2)], st["out_machine"])

    # ---- the frame, labelled mote on its top edge
    cls, dash, tcls, wt = STYLE[fr]
    f.rect(FX, FY, FW, FB - FY, STROKE[fr], 12, dash=dash)
    lab_w = 56
    lx = FX + FW - lab_w - 16
    f.rect(lx, FY - 10, lab_w, 20, "f", 0, sw=False)
    f.text(lx + lab_w / 2, FY + 4.5, "mote", tcls, 13, "middle", 700, mono=True)

    # ---- the program's text, and gcd.c
    piece(TX, TY, TW, TH, st["text"], 10)
    name(TX + TW / 2, TY + 17, "the program's text", "text", 12.5)
    f.text(TX + TW / 2, TY + 33, "programs/", "ta" if st["text"] == "here" else "tm", 11, "middle",
           600 if st["text"] == "here" else None, mono=True)
    piece(GC_X, GC_Y, GC_W, GC_H, st["gcdc"], GC_H / 2)
    mono(gx, GC_Y + GC_H / 2 + 3.9, "gcd.c", "gcdc")

    # ---- left road
    s_ = st["interp"]
    piece(IX, ROW, IW, IH, s_)
    name(ic, ROW + 19, "first interpreter", "interp")
    cell("prompt", IX + 10, ROW + 30, IW - 20, 22, "prompt")

    # ---- middle road
    box("translator", MX, ROW, MW, TRH, "translator to C")
    s_ = st["ctools"]
    f.rect(MX, CT_Y, MW, CT_H, STROKE[s_], 8, dash=True)          # hollow: not ours
    tc = {"here": "ta", "built": "t", "later": "tm"}[s_]
    for k, ln in enumerate(CT_LINES):
        f.text(MC, CT_B0 + k * CT_LH, ln, tc, 12, "middle", 600 if s_ == "here" else 500)
    piece(RT_X, rt_y, RT_W, RT_H, st["rt"], 5)
    mono(RT_X + RT_W / 2, rt_y + RT_H / 2 + 3.9, "rt", "rt")
    s_ = st["program"]
    cls, dash, _, _ = STYLE[s_]
    f.page(MC - PG_W / 2, PG_Y, PG_W, PG_H, cls, dash=dash)
    for k, ln in enumerate(["a program for", "your computer"]):
        name(MC, PG_Y + 15 + k * 14, ln, "program", 11.5)

    # ---- right road: the phases
    box("scanner", FC - PW / 2, SC_Y, PW, PH, "scanner")
    box("parser", FC - PW / 2, PA_Y, PW, PH, "parser")
    piece(FC - PW / 2, SE_Y, PW, SE_H, st["semantic"])
    name(FC, SE_Y + 18, "semantic analysis", "semantic")
    cell("symtab", FC - PW / 2 + 22, SE_Y + 25, PW - 44, 19, "symbol table")
    box("treewalk", TW_X, BR_Y, TW_W, PH, "tree walk")
    box("improver", IM_X, BR_Y, IM_W, PH, "improver")
    box("codegen", IM_X, CG_Y, IM_W, PH, "code generator")
    mono(DROP + 8, (FB + MA_Y) / 2 + 4, "assembly", "assembly", anchor="start")

    # ---- the machine, and gcd.s by hand
    box("machine", MA_X, MA_Y, MA_W, MA_H, "the machine")
    s_ = st["gcds"]
    cls, dash, _, _ = STYLE[s_]
    f.page(GS_X, MA_Y, GS_W, MA_H, cls, dash=dash, fold=8)
    mono(GS_X + GS_W / 2, MA_Y + 15, "gcd.s", "gcds")
    name(GS_X + GS_W / 2, MA_Y + 29, "by hand", "gcds", 11)

    # ---- the four outputs, and agree under them
    for key, cx in (("out_interp", ic), ("out_c", MC), ("out_tree", tw_c), ("out_machine", ma_c)):
        output(key, "join_" + key[4:], cx)
    s_ = st["agree"]
    piece(AG_X, AG_Y, AG_W, AG_H, s_, 6)
    name(AG_X + AG_W / 2, AG_Y + 15, "agree: every way, the same answer", "agree", 12)

    # ---- legend
    ly = HEIGHT - 12
    x = 20
    for cls, dash, lab, tcls in (("a af", False, f"{lid}: this lesson", "ta"), ("s f", False, "built earlier", "t"),
                                 ("m f", True, "still to come", "tm")):
        f.rect(x, ly - 13, 22, 16, cls, 4, dash=dash)
        f.text(x + 30, ly, lab, tcls, 14, weight=600 if tcls == "ta" else None)
        x += 30 + len(lab) * 14 * 0.56 + 28
    return f


def write(lid, fig):
    """Write fig as figures/<lid>-map.svg after the checks (ASCII, kept whole by the site's
    sanitizer); return the path."""
    name = f"{lid}-map"
    text = fig.svg()
    try:
        text.encode("ascii")
    except UnicodeEncodeError as e:
        raise SystemExit(f"{name}: not ASCII: {e}")
    sane(text, name)
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, name + ".svg")
    with open(p, "w") as fh:
        fh.write(text)
    print(os.path.relpath(p, ROOT))
    return p


def main():
    ids = [lid for lid, _ in LESSONS]
    assert ids == sorted(ids) and len(set(ids)) == len(ids)
    every = set().union(*OWNER.values())
    assert every == set(ids), sorted(every ^ set(ids))     # every lesson lights something, and no other
    for lid, title in LESSONS:
        write(lid, draw(lid, title))


if __name__ == "__main__":
    main()
