"""Figures for kilo module 04, A text editor (lessons 04.01-04.04).

    python3 art/kilo/figs04.py

Every value is from a real run of the project at the lesson (./learn files kilo --at NN.LL),
on a 10 x 44 pseudo-terminal, on the file the lesson's Run it makes:

  f.txt     "hello world\\nsecond\\nthird\\n", 25 bytes
  04.01     Right x5, then ','   -> row 0 "hello, world", size 12, cursor column 6
  04.02     Right x5, then Enter -> rows "hello", " world", "second", "third"; cursor (1, 0)
            sizeof(erow) is 24 on a 64-bit build: E.row grows from 72 bytes to 96, and under
            -fsanitize=address the stale row pointer reads "8 bytes inside of 72-byte region"
  04.03     Right x5, Backspace -> "hell world"; Down, Backspace at column 0 -> "hello worldsecond",
            cursor (0, 11), 2 rows
  04.04     Right x11, Backspace x6, Ctrl-S -> "19 bytes written on disk"; the file is 19 bytes;
            without the ftruncate() it is 25: "hello\\nsecond\\nthird\\nthird\\n"
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import figlib  # noqa: E402
from figlib import Fig  # noqa: E402

figlib.LESSONS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                              "tracks", "kilo", "lessons")
MOD = "04-editor"

# A byte box: (text, kind). Kinds: n plain, z a '\0' or a byte past the end (muted),
# u not set yet (dashed), a accent-soft (changed), A accent (the byte this step writes),
# o old bytes left behind (muted, dashed).
STYLE = {
    "n": ("s f", "t", False),
    "z": ("m f", "tm", False),
    "u": ("m f", "tm", True),
    "a": ("a af", "ta", False),
    "A": ("a fa", "f", False),
    "o": ("m fs", "tm", True),
    "s": ("s fs", "t", False),
}


def cells(text, kind="n"):
    """Byte boxes for a C string: "\\0" and "\\n" as one box each."""
    out, i = [], 0
    while i < len(text):
        if text[i] == "\\" and i + 1 < len(text) and text[i + 1] in "0n":
            out.append(("\\" + text[i + 1], "z" if text[i + 1] == "0" else kind))
            i += 2
        else:
            out.append((text[i], kind))
            i += 1
    return out


def strip(f, x, y, boxes, w=26, h=26, size=12):
    """Draw byte boxes left to right from (x, y). A space shows as a small 'sp'."""
    for i, (ch, kind) in enumerate(boxes):
        cls, tcls, dash = STYLE[kind]
        bx = x + i * w
        f.rect(bx, y, w - 2, h, cls, 3, dash=dash)
        if ch == " ":
            f.text(bx + (w - 2) / 2, y + h / 2 + 3.5, "sp", "tm" if tcls == "t" else tcls, 9, "middle", mono=True)
        elif ch:
            small = len(ch) > 1
            f.text(bx + (w - 2) / 2, y + h / 2 + (4 if not small else 3.5), ch, tcls, size if not small else 10.5,
                   "middle", mono=True)
    return x + len(boxes) * w


def indexes(f, x, y, n, w=26, start=0, every=1):
    for i in range(0, n, every):
        f.text(x + i * w + (w - 2) / 2, y, str(start + i), "tm", 9.5, "middle", mono=True)


def cursor_bar(f, x, y, h, label=None, below=True):
    """The cursor: an accent bar at the left edge of the byte it is on."""
    f.line(x - 1, y - 3, x - 1, y + h + 3, "a")
    if label:
        f.text(x - 1, y + h + 15 if below else y - 8, label, "ta", 10, "middle")


# ------------------------------------------------------------------ 04.01

def insert0401():
    f = Fig("f0401a", "Typing a comma with the cursor at column 5 of hello world: the row grows by one byte", 318)
    f.text(24, 20, "row 0 of f.txt, its chars, while ',' is typed with the cursor at column 5", "tm", 11)
    X, W = 228, 30
    indexes(f, X, 46, 13, W)
    steps = [
        (56, "before", "size 11; 12 bytes with the '\\0'",
         cells("hello world\\0")),
        (122, "realloc(chars, size+2)", "13 bytes; the new one not set yet",
         cells("hello world\\0") + [("?", "u")]),
        # positions 6-12 now hold " world\0", copied from 5-11; position 5 keeps its old space
        (188, "memmove(chars+6, chars+5, 7)", "bytes 5-11 and the '\\0', one right",
         cells("hello") + [(" ", "o")] + [(" ", "a")] + [(c, "a") for c in "world"] + [("\\0", "a")]),
        (254, "chars[5] = ','", "size 12; render made again",
         cells("hello") + [(",", "A")] + cells(" world\\0")),
    ]
    for y, label, sub, boxes in steps:
        f.text(24, y + 12, label, "t", 11, weight=600, mono=True)
        f.text(24, y + 27, sub, "tm", 10.5)
        strip(f, X, y, boxes, W, 28)
    # arrows for the move: from each byte of step 2 down-right to step 3
    for i in range(5, 12):
        x1 = X + i * W + (W - 2) / 2
        f.line(x1, 152, x1 + W - 4, 184, "m", arrow=True)
    cursor_bar(f, X + 5 * W, 56, 28)
    f.text(X + 5 * W - 1, 98, "cursor", "ta", 10, "middle")
    cursor_bar(f, X + 6 * W, 254, 28)
    f.text(X + 6 * W - 1, 296, "cursor: cx 5 -> 6", "ta", 10, "middle")
    return f


# ------------------------------------------------------------------ 04.02

def split0402():
    f = Fig("f0402a", "Enter at column 5 of hello world: the row is cut in two", 346)
    X, W = 104, 22

    def row(y, name, text, note, kind="n", note_cls="tm", extra=None):
        f.text(24, y + 15, name, "t", 11, mono=True)
        boxes = cells(text, kind)
        if extra:
            boxes = extra
        end = strip(f, X, y, boxes, W, 22, 11)
        f.text(end + 10, y + 15, note, note_cls, 10.5)

    f.text(24, 20, "E.row before Enter, the cursor at row 0, column 5", "tm", 11)
    row(52, "E.row[0]", "hello world\\0", "size 11",
        extra=cells("hello") + [(c, "a") for c, _ in cells(" world")] + [("\\0", "a")])
    row(80, "E.row[1]", "second\\0", "size 6")
    row(108, "E.row[2]", "third\\0", "size 5")
    f.brace_h(X + 5 * W, X + 12 * W - 2, 47, "a", up=True)
    f.text(X + 8.5 * W, 39, "copied into a new row, '\\0' too", "ta", 10, "middle")
    cursor_bar(f, X + 5 * W, 52, 22)

    f.line(24, 150, 616, 150, "m", dash=True)
    f.text(24, 172, "after: editorInsertRow(1, chars+5, 6), then the old row cut at 5", "tm", 11)
    row(188, "E.row[0]", "", "size 5; bytes 6-11 still there, unused",
        extra=cells("hello") + [("\\0", "A")] + [(c, "z") for c in "world"] + [("\\0", "z")])
    row(216, "E.row[1]", "", "new row, size 6: 7 bytes copied",
        extra=[(c, "a") for c, _ in cells(" world")] + [("\\0", "a")])
    row(244, "E.row[2]", "second\\0", "moved down one place")
    row(272, "E.row[3]", "third\\0", "moved down one place")
    cursor_bar(f, X, 216, 22)
    f.text(24, 318, "The cursor goes to row 1, column 0: cy + 1 (or the view scrolls on the bottom line), cx 0, coloff 0.",
           "tm", 10.5)
    f.text(24, 334, "E.row grew by one erow, so it may have moved: the row pointer is taken again before the cut.",
           "tm", 10.5)
    return f


def realloc0402():
    f = Fig("f0402b", "editorInsertRow reallocs E.row: a pointer taken before the call points into freed memory", 304)
    f.text(24, 20, "E.row is one array of struct erow, 24 bytes each: size, rsize, chars, render", "tm", 11)
    FIELDS = ((36, "size"), (42, "rsize"), (52, "chars"), (54, "render"))
    CHARS_MID = 6 + 36 + 42 + 24          # the chars field's centre, from the block's left edge

    def block(x, y, names, label, dead=False, fresh=()):
        for i, name in enumerate(names):
            yy = y + i * 34
            acc = i in fresh
            f.rect(x, yy, 196, 30, "m fs" if dead else ("a af" if acc else "s f"), 4, dash=dead)
            fx = x + 6
            for fw, fname in FIELDS:
                hit = dead and fname == "chars" and i == 0
                f.rect(fx, yy + 5, fw - 4, 20, "a af" if hit else "m f", 2, dash=dead and not hit)
                f.text(fx + (fw - 4) / 2, yy + 18.5, fname, "ta" if hit else "tm", 9, "middle", mono=True)
                fx += fw
            f.text(x + 204, yy + 19, name, "tm" if dead else ("ta" if acc else "t"), 10.5, mono=True)
            f.text(x - 6, yy + 4, str(i * 24), "tm", 9, "end", mono=True)
        f.text(x - 6, y + len(names) * 34, str(len(names) * 24), "tm", 9, "end", mono=True)
        f.text(x, y + len(names) * 34 + 18, label, "tm" if dead else "t", 11, weight=600)

    # the two pointers, above the blocks
    f.rect(48, 38, 196, 24, "m f", 4, dash=True)
    f.text(56, 54, "row, taken before the call", "tm", 10.5, mono=True)
    f.line(48 + CHARS_MID, 62, 48 + CHARS_MID, 92, "m", arrow=True, dash=True)
    f.rect(352, 38, 196, 24, "a af", 4)
    f.text(360, 54, "row = &E.row[filerow]", "ta", 10.5, mono=True)
    f.line(352 + CHARS_MID, 62, 352 + CHARS_MID, 92, "a", arrow=True)
    block(48, 96, ["hello world", "second", "third"], "old block, 72 bytes: freed", dead=True)
    block(352, 96, ["hello world", "\" world\"", "second", "third"], "new block, 96 bytes", fresh=(1,))
    f.text(352, 270, "the new row is [1]; [2] and [3] moved down", "tm", 10.5)
    f.text(24, 296, "Through the old pointer, row->chars is read 8 bytes into freed memory: a use-after-free.",
           "tm", 10.5)
    return f


# ------------------------------------------------------------------ 04.03

def delete0403():
    f = Fig("f0403a", "Backspace with the cursor at column 5 of hello world: the byte before the cursor goes", 196)
    f.text(24, 20, "editorRowDelChar(row, 4): row 0's chars, before and after", "tm", 11)
    X, W = 228, 30
    indexes(f, X, 46, 12, W)
    f.text(24, 68, "before", "t", 11, weight=600, mono=True)
    f.text(24, 83, "size 11", "tm", 10.5)
    strip(f, X, 56, cells("hell") + [("o", "A")] + cells(" world\\0"), W, 28)
    cursor_bar(f, X + 5 * W, 56, 28)
    for i in range(5, 12):
        x1 = X + i * W + (W - 2) / 2
        f.line(x1, 88, x1 - W + 4, 116, "m", arrow=True)
    f.text(24, 134, "memmove(chars+4, chars+5, 7)", "t", 11, weight=600, mono=True)
    f.text(24, 149, "size 10; the buffer keeps 12 bytes", "tm", 10.5)
    strip(f, X, 122, cells("hell") + [(c, "a") for c, _ in cells(" world")] + [("\\0", "a")] + [("\\0", "o")], W, 28)
    cursor_bar(f, X + 4 * W, 122, 28)
    f.text(X + 4 * W - 1, 168, "cursor: cx 5 -> 4", "ta", 10, "middle")
    f.text(24, 188, "The bytes after the deleted one, the '\\0' included, move one place left; the last byte is left over.",
           "tm", 10.5)
    return f


def join0403():
    f = Fig("f0403b", "Backspace at the start of second: the row joins the end of the row above, and is deleted", 324)
    X, W = 104, 20

    def row(y, name, boxes, note, note_cls="tm"):
        f.text(24, y + 14, name, "t", 11, mono=True)
        end = strip(f, X, y, boxes, W, 20, 10.5)
        f.text(end + 10, y + 14, note, note_cls, 10.5)
        return end

    f.text(24, 20, "before: the cursor at row 1, column 0", "tm", 11)
    row(34, "E.row[0]", cells("hello world\\0"), "size 11")
    row(60, "E.row[1]", [(c, "a") for c in "second"] + [("\\0", "z")], "size 6")
    row(86, "E.row[2]", cells("third\\0"), "size 5")
    cursor_bar(f, X, 60, 20)

    f.line(24, 124, 616, 124, "m", dash=True)
    f.text(24, 146, "editorRowAppendString(&E.row[0], \"second\", 6): row 0 grows to 18 bytes", "tm", 11)
    row(158, "E.row[0]", cells("hello world") + [(c, "a") for c in "second"] + [("\\0", "z")], "size 17")
    f.text(24, 218, "editorDelRow(1): free row 1's chars and render, move the rows after it up one place", "tm", 11)
    row(230, "E.row[1]", cells("third\\0"), "was E.row[2]; 2 rows now")
    cursor_bar(f, X + 11 * W, 158, 20)
    f.text(X + 11 * W - 1, 192, "cursor: (0, 11)", "ta", 10, "middle")
    f.text(24, 282, "The cursor goes where the rows meet: column 11, the size row 0 had before the append,", "tm", 10.5)
    f.text(24, 298, "read first. If 11 is past the screen's edge, the view scrolls right to keep it in sight.", "tm", 10.5)
    return f


# ------------------------------------------------------------------ 04.04

def string0404():
    f = Fig("f0404a", "editorRowsToString: three rows become one string of 19 bytes, a newline after each", 212)
    f.text(24, 20, "the rows of f.txt after ' world' is deleted, and the one string the save writes", "tm", 11)
    X, W = 70, 26
    rows = [("E.row[0]", "hello"), ("E.row[1]", "second"), ("E.row[2]", "third")]
    starts = [0, 6, 13]
    # the rows, laid out above the part of the string they become
    for (name, text), st in zip(rows, starts):
        x = X + st * W
        f.text(x, 46, name + ", size " + str(len(text)), "t", 10.5, mono=True)
        strip(f, x, 54, cells(text), W, 24, 11.5)
        f.line(x + len(text) * W / 2, 82, x + len(text) * W / 2, 104, "m", arrow=True)
    buf = cells("hello") + [("\\n", "a")] + cells("second") + [("\\n", "a")] + cells("third") + [("\\n", "a")] + [("\\0", "z")]
    strip(f, X, 108, buf, W, 28, 11.5)
    indexes(f, X, 150, 20, W, every=2)
    f.text(24, 126, "buf", "t", 11.5, weight=600, mono=True)
    f.brace_h(X, X + 19 * W - 2, 160, "a")
    f.text(X + 9.5 * W, 178, "*buflen = 19: the '\\0' is not counted, and is not written", "ta", 10.5, "middle")
    f.text(24, 202, "Then one write(fd, buf, 19). Every row ends in '\\n', the last one too.", "tm", 10.5)
    return f


def truncate0404():
    f = Fig("f0404b", "What f.txt holds at each step of the save, with ftruncate and without it", 300)
    f.text(24, 20, "f.txt on disk, byte by byte, while 19 bytes are saved over its 25", "tm", 11)
    X, W = 180, 17.6

    def frow(y, label, sub, boxes, lcls="t"):
        f.text(24, y + 13, label, lcls, 11, weight=600, mono=True)
        f.text(24, y + 27, sub, "tm", 10)
        for i, (ch, kind) in enumerate(boxes):
            cls, tcls, dash = STYLE[kind]
            bx = X + i * W
            f.rect(bx, y, W - 2, 24, cls, 2, dash=dash)
            if ch == " ":
                f.text(bx + (W - 2) / 2, y + 15, "sp", "tm" if tcls == "t" else tcls, 7.5, "middle", mono=True)
            else:
                f.text(bx + (W - 2) / 2, y + 16, ch, tcls, 10 if len(ch) > 1 else 11, "middle", mono=True)
        f.text(X + len(boxes) * W + 4, y + 16, str(len(boxes)), "tm", 10, mono=True)

    old = cells("hello world\\nsecond\\nthird\\n")
    new = cells("hello\\nsecond\\nthird\\n", "a")
    indexes(f, X, 46, 25, W, every=4)
    frow(54, "before", "the file kilo opened", old)
    frow(100, "ftruncate(fd, 19)", "cut to the new length", cells("hello world\\nsecond\\n"))
    frow(146, "write(fd, buf, 19)", "the new text over it", new)
    f.line(24, 190, 616, 190, "m", dash=True)
    frow(206, "no ftruncate", "write() alone", new + [(c, "o") for c, _ in cells("third\\n")], lcls="ta")
    f.brace_h(X + 19 * W, X + 25 * W - 2, 238, "a")
    f.text(X + 22 * W, 256, "old bytes 19-24 stay", "ta", 10.5, "middle")
    f.text(24, 284, "A crash between the two calls leaves the middle line: the right length, the old bytes.", "tm", 10.5)
    return f


FIGS = [
    ("04.01-insert", insert0401),
    ("04.02-split", split0402), ("04.02-realloc", realloc0402),
    ("04.03-delete", delete0403), ("04.03-join", join0403),
    ("04.04-rows-to-string", string0404), ("04.04-truncate", truncate0404),
]


def main():
    for name, fn in FIGS:
        print(figlib.write(MOD, name, fn()))


if __name__ == "__main__":
    main()
