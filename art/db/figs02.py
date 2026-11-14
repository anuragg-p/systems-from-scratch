"""Figures for db module 02, The B-tree (lessons 02.01-02.05), plus its cover and icon.

    python3 art/db/figs02.py

Every number in these figures comes from a real file the built engine (or sqlite3)
wrote and that was dumped byte by byte; the lessons' "Run it" sections make the
same files:
  demo.db   rows 7, 3, 9 inserted by sqlite3 (02.01); rowid 5 added by ./db (02.02);
            rowid 12 with 5000 bytes, which spills to overflow page 3 (02.01)
  s.db      100-byte rows: 37 rows 10..370, then 15, 1..21, then 22 (02.02, 02.03)
  inorder   2000 rows in rowid order, 30-byte text: leaf page 4 holds rowids 1..93 (02.01)
  deep.db   4000 rows of 400 bytes in scrambled order, three levels (02.03, 02.04), made by
            the 04.01 and 05.03 builds the lessons use: 1499 ends leaf 283, 1500 starts leaf 563
  ix.db     3000 rows, index t_a on a = i * 7919 % 3001, root page 3 (02.02, 02.04, 02.05)
  del.db    3000 rows in order, then DELETE id > 1000 (02.05)
  three.db  rows 1 and 3 of 2000 bytes, then rowid 2 of 4000 bytes: a split into three (02.02)
  small.db  512-byte pages, 600 rows of 100 bytes, then DELETE id > 100: two trunks (02.05)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import figlib  # noqa: E402
from figlib import Fig, tw  # noqa: E402
from figart import Art  # noqa: E402

figlib.LESSONS = os.path.expanduser("~/Documents/WORK/misc/systems-from-scratch/tracks/db/lessons")
MOD = "02-btree"


def cell(f, x, y, w, h, label, cls="s f", tcls="t", size=11.5, mono=True, rx=4, sub=None, weight=None):
    f.label_box(x, y, w, h, label, cls, tcls, size, mono, rx, weight, sub=sub)


# ------------------------------------------------------------------ 02.01

def tree0201():
    f = Fig("f0201a", "Module 02 in one picture: a table as a tree of pages", 270)
    f.text(24, 22, "the table t of s.db (built in 02.02): four pages of one file", "tm", 11)
    rx, ry = 92, 52
    f.rect(rx, ry, 196, 34, "a af", 6)
    cell(f, rx + 8, ry + 6, 54, 22, "5 | 19", "s f", size=11)
    cell(f, rx + 68, ry + 6, 62, 22, "4 | 180", "s f", size=11)
    cell(f, rx + 136, ry + 6, 52, 22, "-> 3", "m f", "tm", size=11)
    f.text(rx + 98, ry - 8, "root: page 2, interior", "ta", 10.5, "middle", 600)
    leaves = [(24, "page 5", "rowids 1-19"), (140, "page 4", "rowids 20-180"), (256, "page 3", "rowids 190-370")]
    for (x, name, keys), sx in zip(leaves, (rx + 35, rx + 99, rx + 162)):
        f.rect(x, 140, 100, 44, "s f", 6)
        f.text(x + 50, 158, name, "t", 11.5, "middle", 600, True)
        f.text(x + 50, 174, keys, "tm", 10.5, "middle")
        f.line(sx, ry + 28, x + 50, 138, "s", arrow=True)
    f.path("M74 196 C 110 216, 150 216, 186 196", "a", arrow=True, dash=True)
    f.path("M196 196 C 232 216, 272 216, 300 196", "a", arrow=True, dash=True)
    f.text(24, 238, "leaves hold the rows, in rowid order; the root holds", "tm", 10.5)
    f.text(24, 252, "signposts: (child page | the largest rowid in it)", "tm", 10.5)
    f.line(386, 40, 386, 256, "m")
    f.text(404, 48, "what each lesson adds", "t", 11.5, weight=600)
    tags = [("02.01", "a leaf page: its cells,", "and a search inside it"), ("02.02", "insert; a full page", "splits in two"),
            ("02.03", "interior pages; the root", "grows but stays page 2"), ("02.04", "a cursor that walks", "the leaves in order"),
            ("02.05", "delete, and pages", "handed back for reuse")]
    for i, (lid, a, b) in enumerate(tags):
        yy = 76 + i * 38
        f.text(404, yy, lid, "ta", 11, weight=600, mono=True)
        f.text(452, yy, a, "t", 11)
        f.text(452, yy + 14, b, "t", 11)
    return f


def leaf0201():
    f = Fig("f0201b", "Page 2 of demo.db: a table leaf with three cells", 290)
    f.text(24, 20, "page 2 of demo.db as sqlite3 wrote it, rows inserted in the order 7, 3, 9", "tm", 11)
    hz = [("0d", "type 13", "table leaf"), ("00 00", "freeblock", "none"), ("00 03", "cells", "3"),
          ("0f e3", "content at", "4067"), ("00", "fragments", "0")]
    x = 24
    for b, l1, l2 in hz:
        w = 44 if len(b) == 2 else 70
        cell(f, x, 34, w, 26, b, "s f", size=11.5)
        f.text(x + w / 2, 74, l1, "tm", 10, "middle")
        f.text(x + w / 2, 87, l2, "t", 10.5, "middle", 600)
        x += w + 6
    f.text(x + 6, 46, "the 8-byte header", "t", 11, weight=600)
    f.text(x + 6, 61, "offsets 0-7 of the page", "tm", 10.5)
    Y, H = 140, 38
    f.rect(24, Y, 80, H, "s fs", 0)
    f.text(64, Y + 24, "header", "t", 11, "middle")
    for i, v in enumerate(("4076", "4086", "4067")):
        cell(f, 104 + i * 40, Y, 40, H, v, "a af", "ta", 10.5, rx=0)
    f.rect(226, Y + 2, 102, H - 4, "m", 0, dash=True)
    f.text(277, Y + 17, "free", "tm", 11, "middle")
    f.text(277, Y + 31, "4053 bytes", "tm", 10, "middle", None, True)
    cells = [(330, 92, "rowid 9"), (422, 97, "rowid 3"), (519, 97, "rowid 7")]
    for x, w, name in cells:
        cell(f, x, Y, w, H, name, "s f", "t", 11, mono=False, rx=0)
    for x, v in ((24, "0"), (104, "8"), (224, "14"), (330, "4067"), (422, "4076"), (519, "4086"), (616, "4096")):
        f.line(x, Y - 5, x, Y - 1, "m")
        f.text(x, Y - 9, v, "tm", 10, "middle", None, True)
    f.text(164, 112, "cell pointers, in key order", "ta", 10.5, "middle", 600)
    f.text(474, 112, "cells, in the order they arrived", "t", 10.5, "middle", 600)
    b = Y + H
    for sx, tx, d in ((124, 470, 58), (164, 567, 84), (204, 376, 32)):
        f.path(f"M{sx} {b} C {sx} {b + d}, {tx} {b + d}, {tx} {b + 2}", "a", arrow=True)
    f.text(24, 262, "the cells' bytes:", "tm", 10.5)
    rows = [("4067", "07 09 03 00 15", "nine"), ("4076", "08 03 03 00 17", "three"), ("4086", "08 07 03 00 17", "seven")]
    for i, (off, hx, txt) in enumerate(rows):
        x = 130 + i * 166
        f.text(x, 262, off, "tm", 10.5, mono=True)
        f.text(x + 34, 262, hx, "t", 10.5, mono=True)
        f.text(x + 34, 278, txt, "tm", 10.5, mono=True)
    return f


def cells0201():
    f = Fig("f0201c", "The four kinds of cell, with a real example of each", 344)
    f.text(24, 20, "a cell field by field; the example bytes are from real pages", "tm", 11)
    rows = [
        ("table leaf", "type 13", [("08", "payload size", "s f"), ("07", "rowid", "a af"),
                                   ("03 00 17 73 65 76 65 6e", "the record: NULL, 'seven'", "s fs")],
         "demo.db page 2"),
        ("table leaf", "spilled", [("a7 0c", "size 5004", "s f"), ("0c", "rowid 12", "a af"),
                                   ("04 00 ce 1d 78 78 ...", "the first 912 bytes", "s fs"),
                                   ("00 00 00 03", "page 3: the other 4092", "s f")], None),
        ("table interior", "type 5", [("00 00 00 04", "left child", "s f"), ("81 34", "rowid 180", "a af")],
         "s.db page 2: page 4 holds rowids <= 180"),
        ("index leaf", "type 10", [("05", "payload size", "s f"), ("03 09 02 04 40", "the key: a = 1, rowid 1088", "a af")],
         "index t_a, ix.db page 16"),
        ("index interior", "type 2", [("00 00 00 10", "left child", "s f"), ("06", "size", "s f"),
                                      ("03 02 01 01 85 5b", "a = 389, rowid 91", "a af")],
         "ix.db page 3: an entry, not a copy"),
    ]
    y = 40
    for name, typ, fields, note in rows:
        f.text(24, y + 17, name, "t", 11.5, weight=600)
        f.text(24, y + 32, typ, "tm", 10.5)
        x = 130
        for b, lab, cls in fields:
            w = max(tw(b, 11, True) + 16, tw(lab, 10, False) + 8, 40)
            cell(f, x, y + 2, w, 26, b, cls, "ta" if cls.startswith("a") else "t", 11)
            f.text(x + w / 2, y + 42, lab, "tm", 10, "middle")
            x += w + 4
        if note:
            f.text(616, y + 19, note, "tm", 10, "end")
        y += 60
    return f


def search0201():
    f = Fig("f0201d", "Binary search for rowid 50 in a leaf of 93 cells", 300)
    f.text(24, 20, "inorder.db, leaf page 4: cells 0-92 hold rowids 1-93; looking for rowid 50", "tm", 11)
    X0, X1 = 48, 372
    cw = (X1 - X0) / 93

    def cx(i):
        return X0 + i * cw
    steps = [(0, 93, 46, 47, "lo"), (47, 93, 70, 71, "hi"), (47, 70, 58, 59, "hi"), (47, 58, 52, 53, "hi"),
             (47, 52, 49, 50, "hi"), (47, 49, 48, 49, "lo")]
    f.text(390, 44, "read the middle cell of the range:", "tm", 10.5)
    y = 60
    for n, (lo, hi, mid, key, which) in enumerate(steps):
        f.text(30, y + 10, str(n + 1), "tm", 11, "middle", 600, True)
        f.rect(X0, y, X1 - X0, 12, "m fs", 2)
        f.rect(cx(lo), y, cx(hi) - cx(lo), 12, "a af", 2)
        f.circle(cx(mid) + cw / 2, y + 6, 4, "a fa")
        if which == "lo":
            what = f"cell {mid}: rowid {key} < 50, lo = {mid + 1}"
        else:
            what = f"cell {mid}: rowid {key} >= 50, hi = {mid}"
        f.text(390, y + 10, what, "t", 11, mono=False)
        y += 30
    f.rect(X0, y, X1 - X0, 12, "m fs", 2)
    f.rect(cx(49) - 1, y - 3, cw + 2, 18, "a fa", 1)
    f.text(390, y + 10, "lo = hi = 49: rowid 50 is cell 49", "ta", 11, weight=600)
    f.text(X0, y + 32, "cell 0", "tm", 10, "start", None, True)
    f.text(X1, y + 32, "cell 92", "tm", 10, "end", None, True)
    f.text(24, y + 58, "6 cells read out of 93: each read follows a 2-byte pointer and decodes one cell's rowid", "tm", 10.5)
    return f


# ------------------------------------------------------------------ 02.02

def split0202():
    f = Fig("f0202a", "Splitting page 4 of s.db when rowid 22 does not fit", 340)
    f.text(24, 20, "before: page 4 is full (37 cells, 86 bytes free) and rowid 22 belongs in it", "tm", 11)

    def parent(y, cells):
        w = sum(c[1] + 6 for c in cells) + 64
        x = 320 - w / 2
        f.rect(x, y, w, 34, "s fs", 6)
        f.text(x - 8, y + 21, "page 2", "t", 11.5, "end", 600, True)
        cx = x + 10
        pos = []
        for label, cw, acc in cells:
            cell(f, cx, y + 6, cw, 22, label, "a af" if acc else "s f", "ta" if acc else "t", 11)
            pos.append(cx + cw / 2)
            cx += cw + 6
        cell(f, cx, y + 6, 44, 22, "-> 3", "m f", "tm", 11)
        pos.append(cx + 22)
        return pos

    def leaf(x, y, name, l1, acc=False):
        f.rect(x, y, 150, 46, "a af" if acc else "s f", 6)
        f.text(x + 75, y + 18, name, "ta" if acc else "t", 11.5, "middle", 600, True)
        f.text(x + 75, y + 35, l1, "ta" if acc else "tm", 10.5, "middle")

    p = parent(34, [("4 | 180", 62, False)])
    leaf(150, 104, "page 4", "37 cells: rowids 1-180")
    leaf(340, 104, "page 3", "19 cells: 190-370")
    f.line(p[0], 62, 225, 102, "s", arrow=True)
    f.line(p[1], 62, 415, 102, "s", arrow=True)
    f.label_box(36, 110, 76, 30, "22", "a af", "ta", 12, True, 15, 600)
    f.line(112, 125, 146, 125, "a", arrow=True)
    f.text(74, 156, "INSERT", "ta", 10.5, "middle")
    f.line(24, 172, 616, 172, "m", dash=True)
    f.text(24, 192, "after: a new page takes the left half; page 4 keeps the right half", "tm", 11)
    p = parent(206, [("5 | 19", 56, True), ("4 | 180", 62, False)])
    leaf(64, 280, "page 5", "19 cells: rowids 1-19", acc=True)
    leaf(245, 280, "page 4", "19 cells: 20-180")
    leaf(426, 280, "page 3", "19 cells: 190-370")
    f.line(p[0], 234, 139, 278, "a", arrow=True)
    f.line(p[1], 234, 320, 278, "s", arrow=True)
    f.line(p[2], 234, 501, 278, "s", arrow=True)
    f.text(616, 230, "new divider: page 5,", "ta", 10.5, "end")
    f.text(616, 244, "its last rowid 19", "ta", 10.5, "end")
    f.text(24, 230, "the pointer to page 4", "tm", 10.5)
    f.text(24, 244, "did not change", "tm", 10.5)
    return f


def insert0202():
    f = Fig("f0202b", "Putting rowid 5 into demo.db's leaf: pointers grow down, cells grow up", 262)
    f.text(24, 20, "page 2 of a fresh demo.db holding only 02.01's rows 7, 3, 9; then ./db inserts (5, 'five')", "tm", 11)

    def bar(y, n, content, ptrs, cells, newptr=None):
        f.text(24, y - 8, f"{n} cells, content starts at {content}", "t", 11, weight=600)
        f.rect(24, y, 60, 34, "s fs", 0)
        f.text(54, y + 21, "header", "t", 10.5, "middle")
        x = 84
        for i, v in enumerate(ptrs):
            acc = i == newptr
            cell(f, x, y, 44, 34, v, "a af" if not acc else "a fa", "ta" if not acc else "f", 10.5, rx=0,
                 weight=600 if acc else None)
            x += 44
        start = 616 - sum(c[1] for c in cells)
        f.rect(x + 2, y + 2, start - x - 4, 30, "m", 0, dash=True)
        f.text((x + start) / 2, y + 21, "free", "tm", 10.5, "middle")
        x = start
        for name, w, acc in cells:
            cell(f, x, y, w, 34, name, "a fa" if acc else "s f", "f" if acc else "t", 10.5, rx=0,
                 weight=600 if acc else None)
            x += w
    bar(56, 3, 4067, ["4076", "4086", "4067"], [("9", 56, False), ("3", 60, False), ("7", 60, False)])
    f.text(616, 48, "rowids, as stored", "tm", 10, "end")
    bar(176, 4, 4058, ["4076", "4058", "4086", "4067"],
        [("5", 52, True), ("9", 56, False), ("3", 60, False), ("7", 60, False)], newptr=1)
    f.path("M150 92 C 150 128, 194 136, 194 172", "s", arrow=True)
    f.path("M194 92 C 194 128, 238 136, 238 172", "s", arrow=True)
    f.text(24, 120, "the pointers after", "tm", 10.5)
    f.text(24, 134, "slot 1 move along", "tm", 10.5)
    f.text(24, 148, "2 bytes", "tm", 10.5)
    f.path("M392 124 C 360 124, 346 140, 346 172", "a", arrow=True)
    f.text(400, 120, "new cell: 9 bytes at 4058, just", "ta", 10.5)
    f.text(400, 134, "below where the content started", "ta", 10.5)
    f.text(24, 240, "free space: 4053 bytes before, 4042 after (9 for the cell, 2 for its pointer)", "tm", 10.5)
    return f


def dividers0202():
    f = Fig("f0202c", "What a split sends up to the parent, by kind of page", 252)
    panels = [
        (24, "table leaf: a copy", "5 | 19", ("page 5", "1 ... 19"), ("page 4", "20 ... 180"),
         ["19 stays in page 5: the parent", "holds a copy, a signpost", "(s.db)"]),
        (230, "index leaf: the entry", "16 | 389, 91", ("page 16", "a 1 ... 388"), ("page 10", "a 390 ... 761"),
         ["a = 389 is in no leaf: the", "entry itself moved up", "(index t_a of ix.db)"]),
        (436, "interior page: a cell", "518 | 2031", ("page 518", "right: 22"), ("page 517", "> 2031"),
         ["cell (22 | 2031) moved up;", "page 22 became page 518's", "right-most child (deep.db)"]),
    ]
    for x, title, pl, (ln, lk), (rn, rk), notes in panels:
        f.text(x, 22, title, "t", 11.5, weight=600)
        pw = tw(pl, 11, True) + 18
        mid = x + 90
        f.rect(mid - pw / 2 - 8, 38, pw + 16, 34, "s fs", 6)
        cell(f, mid - pw / 2, 44, pw, 22, pl, "a af", "ta", 11)
        for cx, name, keys in ((x, ln, lk), (x + 96, rn, rk)):
            f.rect(cx, 112, 88, 46, "s f", 6)
            f.text(cx + 44, 130, name, "t", 11, "middle", 600, True)
            f.text(cx + 44, 147, keys, "tm", 10, "middle", None, True)
        f.line(mid - 20, 72, x + 44, 110, "s", arrow=True)
        for i, n in enumerate(notes):
            f.text(x, 186 + i * 15, n, "tm" if i < 2 else "tm", 10.5)
    f.text(24, 240, "the arrow is the divider's left child: everything in it sorts before (or, in a table, up to) the divider", "tm", 10.5)
    return f


# ------------------------------------------------------------------ 02.03

def grow0203():
    f = Fig("f0203a", "The root of g.db (and of s.db in 02.02) grows a level and keeps its page number", 300)
    cols = [(24, "1. page 2 is full", "37 rows, rowids 10-370;", "rowid 15 does not fit"),
            (230, "2. the root moves down", "a new page takes all of it;", "page 2 just points there"),
            (436, "3. page 3 splits", "as in 02.02; the divider", "lands in the root")]
    for x, t, s1, s2 in cols:
        f.text(x, 22, t, "t", 12, weight=600)
        f.text(x, 38, s1, "tm", 10.5)
        f.text(x, 52, s2, "tm", 10.5)
    for x in (214, 420):
        f.line(x, 64, x, 262, "m", dash=True)
    f.rect(34, 120, 160, 50, "a af", 6)
    f.text(114, 140, "page 2: table leaf", "ta", 11.5, "middle", 600, True)
    f.text(114, 158, "37 cells, 67 bytes free", "ta", 10.5, "middle")
    f.label_box(84, 210, 60, 26, "15", "a af", "ta", 12, True, 13, 600)
    f.line(114, 208, 114, 174, "a", arrow=True)
    f.rect(246, 88, 156, 46, "a af", 6)
    f.text(324, 106, "page 2: interior", "ta", 11.5, "middle", 600, True)
    f.text(324, 124, "0 cells, -> 3", "ta", 10.5, "middle", None, True)
    f.rect(246, 186, 156, 50, "s f", 6)
    f.text(324, 206, "page 3: table leaf", "t", 11.5, "middle", 600, True)
    f.text(324, 224, "the same 37 cells", "tm", 10.5, "middle")
    f.line(324, 136, 324, 184, "s", arrow=True)
    f.text(334, 164, "a new page", "tm", 10)
    f.rect(452, 88, 150, 46, "a af", 6)
    f.text(527, 106, "page 2: interior", "ta", 11.5, "middle", 600, True)
    f.text(527, 124, "4 | 180, -> 3", "ta", 10.5, "middle", None, True)
    f.rect(446, 186, 80, 50, "s f", 6)
    f.text(486, 206, "page 4", "t", 11.5, "middle", 600, True)
    f.text(486, 224, "10-180", "tm", 10.5, "middle")
    f.rect(532, 186, 80, 50, "s f", 6)
    f.text(572, 206, "page 3", "t", 11.5, "middle", 600, True)
    f.text(572, 224, "190-370", "tm", 10.5, "middle")
    f.line(500, 136, 486, 184, "s", arrow=True)
    f.line(556, 136, 572, 184, "s", arrow=True)
    f.text(486, 252, "19 cells", "tm", 10, "middle")
    f.text(572, 252, "19 cells", "tm", 10, "middle")
    f.text(24, 288, "sqlite_schema still says rootpage 2 for t: nothing outside the tree had to change", "t", 11)
    return f


def interior0203():
    f = Fig("f0203b", "Page 2 of s.db after both splits: a table interior page", 286)
    f.text(24, 20, "page 2 of s.db at the end of 02.02's run, byte by byte", "tm", 11)
    hz = [("05", "type 5", "interior"), ("00 00", "freeblock", "none"), ("00 02", "cells", "2"),
          ("0f f5", "content at", "4085"), ("00", "fragments", "0"), ("00 00 00 03", "right-most", "child: 3")]
    x = 24
    for b, l1, l2 in hz:
        w = 40 if len(b) == 2 else (64 if len(b) == 5 else 96)
        acc = l1 == "right-most"
        cell(f, x, 34, w, 26, b, "a af" if acc else "s f", "ta" if acc else "t", 11)
        f.text(x + w / 2, 74, l1, "tm", 10, "middle")
        f.text(x + w / 2, 87, l2, "ta" if acc else "t", 10.5, "middle", 600)
        x += w + 6
    f.text(x + 4, 46, "12 bytes:", "t", 11, weight=600)
    f.text(x + 4, 61, "4 more than", "tm", 10.5)
    f.text(x + 4, 74, "a leaf's", "tm", 10.5)
    Y = 124
    f.rect(24, Y, 96, 34, "s fs", 0)
    f.text(72, Y + 21, "header", "t", 10.5, "middle")
    cell(f, 120, Y, 46, 34, "4085", "a af", "ta", 10.5, rx=0)
    cell(f, 166, Y, 46, 34, "4090", "a af", "ta", 10.5, rx=0)
    f.rect(214, Y + 2, 210, 30, "m", 0, dash=True)
    f.text(319, Y + 21, "free: 4069 bytes", "tm", 10.5, "middle")
    cell(f, 426, Y, 84, 34, "5 | 19", "s f", "t", 11, rx=0)
    cell(f, 510, Y, 106, 34, "4 | 180", "s f", "t", 11, rx=0)
    for xx, v in ((24, "0"), (120, "12"), (212, "16"), (426, "4085"), (510, "4090"), (616, "4096")):
        f.text(xx, Y - 6, v, "tm", 10, "middle", None, True)
    f.text(616, Y + 52, "5 | 19 is 00 00 00 05 13", "tm", 10, "end", None, True)
    f.text(616, Y + 66, "4 | 180 is 00 00 00 04 81 34", "tm", 10, "end", None, True)
    f.text(24, 222, "its three children, in key order:", "tm", 10.5)
    kids = [(24, "child 0: page 5", "rowids <= 19"), (222, "child 1: page 4", "19 < rowids <= 180"),
            (420, "child 2: page 3", "rowids > 180 (right-most)")]
    for xx, a, b in kids:
        f.rect(xx, 232, 192, 40, "s f", 6)
        f.text(xx + 96, 248, a, "t", 11, "middle", 600)
        f.text(xx + 96, 264, b, "tm", 10.5, "middle")
    return f


def seek0203():
    f = Fig("f0203c", "Going down deep.db to rowid 1500, and the path the descent leaves behind", 310)
    f.text(24, 20, "deep.db: 4000 rows of 400 bytes, three levels; looking for rowid 1500", "tm", 11)
    # level 0
    f.text(24, 52, "page 2", "t", 11, weight=600, mono=True)
    f.text(24, 66, "level 0", "tm", 10)
    f.rect(100, 36, 168, 34, "s fs", 6)
    cell(f, 108, 42, 92, 22, "518 | 2031", "a af", "ta", 11)
    cell(f, 206, 42, 54, 22, "-> 517", "s f", "t", 11)
    f.text(284, 52, "1500 <= 2031: go down the first", "t", 10.5)
    f.text(284, 66, "child, page 518 (idx 0)", "t", 10.5)
    # level 1
    f.text(24, 134, "page 518", "t", 11, weight=600, mono=True)
    f.text(24, 148, "level 1", "tm", 10)
    f.rect(100, 118, 456, 34, "s fs", 6)
    f.text(116, 139, "...", "tm", 11, "middle", None, True)
    x = 130
    for lab, acc in (("283 | 1499", False), ("563 | 1504", True), ("24 | 1509", False)):
        cell(f, x, 124, 92, 22, lab, "a af" if acc else "s f", "ta" if acc else "t", 11)
        x += 98
    f.text(x + 4, 139, "... 314 cells", "tm", 10.5, mono=True)
    f.path("M154 70 C 154 96, 274 92, 274 116", "a", arrow=True)
    f.text(330, 172, "the first rowid >= 1500 is 1504,", "t", 10.5)
    f.text(330, 186, "cell 231: go down to page 563", "t", 10.5)
    # level 2
    f.text(24, 222, "page 563", "t", 11, weight=600, mono=True)
    f.text(24, 236, "level 2", "tm", 10)
    f.rect(100, 206, 296, 34, "s f", 6)
    x = 106
    for i, k in enumerate((1500, 1501, 1502, 1503, 1504)):
        cell(f, x, 212, 52, 22, str(k), "a af" if i == 0 else "s f", "ta" if i == 0 else "t", 11)
        x += 57
    f.path("M274 146 C 274 176, 132 178, 132 204", "a", arrow=True)
    f.text(410, 222, "a leaf: rowid 1500 is", "t", 10.5)
    f.text(410, 236, "its cell 0 (idx 0)", "t", 10.5)
    # the path
    f.line(24, 258, 616, 258, "m")
    f.text(24, 278, "the path", "ta", 11, weight=600)
    f.text(24, 296, "left behind", "ta", 11, weight=600)
    for j, (lab, vals) in enumerate((("page", ("2", "518", "563")), ("idx", ("0", "231", "0")))):
        y = 278 + j * 18
        f.text(124, y, lab, "tm", 11, mono=True)
        for i, v in enumerate(vals):
            f.text(190 + i * 56, y, v, "t", 11, "end", None, True)
    f.text(330, 287, "one entry per level, root first", "tm", 10.5)
    return f


# ------------------------------------------------------------------ 02.04

def walk0204():
    f = Fig("f0204a", "A cursor crossing from one leaf to the next: WHERE id BETWEEN 1499 AND 1502 in deep.db", 352)
    f.text(24, 18, "deep.db again: the range starts at the end of one leaf and goes on in the next", "tm", 11)
    f.rect(140, 34, 360, 34, "s fs", 6)
    f.text(132, 56, "page 518", "t", 11, "end", 600, True)
    f.text(156, 55, "...", "tm", 11, "middle", None, True)
    c230, c231 = 172, 274
    cell(f, c230, 40, 96, 22, "283 | 1499", "s f", "t", 11)
    cell(f, c231, 40, 96, 22, "563 | 1504", "a af", "ta", 11)
    f.text(388, 55, "... 314", "tm", 10.5, None, None, True)
    f.text(c230 + 48, 82, "idx 230", "tm", 10, "middle", None, True)
    f.text(c231 + 48, 82, "idx 231", "ta", 10, "middle", 600, True)
    L1, L2, cw = 24, 362, 34
    f.rect(L1, 150, 9 * cw + 10, 34, "s f", 6)
    x = L1 + 6
    pos = {}
    for k in range(1491, 1500):
        acc = k == 1499
        cell(f, x, 156, cw - 2, 22, str(k), "a af" if acc else "s f", "ta" if acc else "t", 9.5)
        pos[k] = x + (cw - 2) / 2
        x += cw
    f.rect(L2, 150, 5 * cw + 10, 34, "s f", 6)
    x = L2 + 6
    for k in range(1500, 1505):
        acc = k <= 1502
        cell(f, x, 156, cw - 2, 22, str(k), "a af" if acc else "m f", "ta" if acc else "tm", 9.5)
        pos[k] = x + (cw - 2) / 2
        x += cw
    f.text(L1, 204, "leaf 283: rowids 1491-1499", "tm", 10.5)
    f.text(L2, 204, "leaf 563: 1500-1504", "tm", 10.5)
    f.line(c230 + 48, 62, L1 + 160, 148, "m")
    # the walk
    f.path(f"M{pos[1499]} 150 C {pos[1499]} 116, 300 108, 300 90", "a", arrow=True)
    f.path(f"M346 90 C 346 116, {pos[1500]} 116, {pos[1500]} 152", "a", arrow=True)
    f.text(pos[1499] - 12, 118, "2. leaf used up:", "ta", 10.5, "end")
    f.text(pos[1499] - 12, 132, "climb to page 518", "ta", 10.5, "end")
    f.text(pos[1500] + 16, 112, "3. idx 231: down to", "ta", 10.5)
    f.text(pos[1500] + 16, 126, "its leftmost leaf", "ta", 10.5)
    f.text(pos[1499], 198, "1.", "ta", 10.5, "middle", 600)
    f.text(L2 + 5 * cw + 16, 164, "1503 > 1502", "tm", 10)
    f.text(L2 + 5 * cw + 16, 178, "so stop", "tm", 10)
    # the path, step by step
    ty = 230
    f.line(24, ty - 8, 616, ty - 8, "m")
    f.text(24, ty + 8, "step", "tm", 10.5, weight=600)
    f.text(150, ty + 8, "page at each level", "tm", 10.5, weight=600)
    f.text(320, ty + 8, "idx at each level", "tm", 10.5, weight=600)
    f.text(470, ty + 8, "row", "tm", 10.5, weight=600)
    rows = [("1. seek 1499", ("2", "518", "283"), ("0", "230", "8"), "1499"),
            ("2-3. next", ("2", "518", "563"), ("0", "231", "0"), "1500"),
            ("next", ("2", "518", "563"), ("0", "231", "1"), "1501"),
            ("next", ("2", "518", "563"), ("0", "231", "2"), "1502"),
            ("next", ("2", "518", "563"), ("0", "231", "3"), "1503: past the range")]
    for i, (st, pg, ix, row) in enumerate(rows):
        y = ty + 28 + i * 18
        cls = "ta" if i == 1 else "t"
        f.text(24, y, st, cls, 10.5)
        for j, v in enumerate(pg):
            f.text(166 + j * 40, y, v, cls, 10.5, "end", None, True)
        for j, v in enumerate(ix):
            f.text(330 + j * 40, y, v, cls, 10.5, "end", None, True)
        f.text(470, y, row, cls, 10.5, mono=row.isdigit())
    return f


def index0204():
    f = Fig("f0204b", "In an index the interior cells are entries too: the order a cursor visits them", 262)
    f.text(24, 20, "index t_a of ix.db: root page 3 holds 7 entries, its 8 children hold the other 2993", "tm", 11)
    ents = [389, 762, 1135, 1509, 1884, 2254, 2627]
    kids = [(16, "1-388"), (10, "390-761"), (19, "763-1134"), (7, "1136-1508"), (18, "1510-1883"),
            (11, "1885-2253"), (17, "2255-2626"), (6, "2628-3000")]
    lw, gap = 68, 7.4
    lx = [24 + i * (lw + gap) for i in range(8)]
    ex = [lx[i] + lw + gap / 2 for i in range(7)]
    f.rect(52, 44, 536, 34, "s fs", 6)
    f.text(46, 66, "page 3", "t", 11, "end", 600, True)
    for i, e in enumerate(ents):
        cell(f, ex[i] - 25, 50, 50, 22, str(e), "a af", "ta", 11)
    for i, (pg, rng) in enumerate(kids):
        f.rect(lx[i], 140, lw, 44, "s f", 6)
        f.text(lx[i] + lw / 2, 158, f"page {pg}", "t", 10.5, "middle", 600, True)
        f.text(lx[i] + lw / 2, 174, rng, "tm", 10, "middle", None, True)
        top = ex[i] - 25 if i < 7 else ex[6] + 25
        f.line(top, 72, lx[i] + lw / 2, 138, "m")
    for i in range(8):
        f.circle(lx[i] + lw / 2, 204, 9, "a f")
        f.text(lx[i] + lw / 2, 208, str(2 * i + 1), "ta", 10, "middle", 600, True)
    for i in range(7):
        f.circle(ex[i], 100, 9, "a f")
        f.text(ex[i], 104, str(2 * i + 2), "ta", 10, "middle", 600, True)
    f.text(24, 236, "Visiting order: a leaf, then the root entry after it, then the next leaf. A table's cursor skips", "t", 10.5)
    f.text(24, 252, "interior cells (they only repeat a rowid); an index's cursor must stop on them, or lose 7 rows.", "t", 10.5)
    return f


# ------------------------------------------------------------------ 02.05

def freelist0205():
    f = Fig("f0205a", "The freelist of del.db after DELETE FROM t WHERE id > 1000", 286)
    f.text(24, 20, "del.db: 37 pages, 23 of them free; page 1's header points at the list", "tm", 11)
    f.text(24, 50, "page 1, offset 32", "t", 11, weight=600)
    cell(f, 24, 58, 110, 28, "00 00 00 10", "a af", "ta", 11)
    cell(f, 138, 58, 110, 28, "00 00 00 17", "a af", "ta", 11)
    f.text(79, 102, "first trunk: 16", "t", 10.5, "middle")
    f.text(193, 102, "free pages: 23", "t", 10.5, "middle")
    f.text(268, 70, "two numbers in the file header are the", "tm", 10.5)
    f.text(268, 84, "whole record of free space: no bitmap", "tm", 10.5)
    f.path("M50 108 C 50 124, 44 136, 44 152", "a", arrow=True)
    f.text(110, 140, "page 16, the trunk: 4-byte numbers", "t", 11, weight=600)
    Y = 156
    vals = [("0", "next trunk"), ("22", "how many"), ("17", None), ("18", None), ("19", None), ("...", None),
            ("36", None), ("37", None), ("3", None)]
    x = 24
    for v, lab in vals:
        w = 56 if lab else 40
        if v == "...":
            f.text(x + 16, Y + 19, "...", "tm", 11, "middle", None, True)
            x += 34
            continue
        acc = v == "3"
        cell(f, x, Y, w, 28, v, "a af" if acc else ("s fs" if lab else "s f"), "ta" if acc else "t", 11)
        if lab:
            f.text(x + w / 2, Y + 44, lab, "tm", 10, "middle")
        x += w + 2
    f.text(220, Y + 44, "the free pages: 17-37, then 3", "tm", 10, "middle")
    f.rect(x + 2, Y + 2, 616 - x - 4, 24, "m", 0, dash=True)
    f.text((x + 616) / 2, Y + 19, "unused: room for 1016 in all", "tm", 10.5, "middle")
    f.text(24, 228, "Freeing a page adds its number at the end; when a trunk is full, the freed page becomes", "t", 10.5)
    f.text(24, 244, "the new first trunk. Taking a page takes the last number: page 3 first, then 37, 36, ...", "t", 10.5)
    f.text(24, 268, "500 new rows later: still 37 pages, 17 free. The file did not grow; it never shrinks either.", "tm", 10.5)
    return f


def merge0205():
    f = Fig("f0205b", "Deleting the last row of a leaf: the empty page leaves the tree", 316)
    f.text(24, 20, "del.db during the DELETE: page 16 holds one row, 1147, and it is deleted", "tm", 11)

    def strip(y, cells):
        pos = {}
        widths = [tw(lab, 11, True) + 16 for lab, _ in cells]
        total = 40 + sum(w + 6 for w in widths) + 30
        x0 = 84
        f.rect(x0, y, total, 34, "s fs", 6)
        f.text(x0 - 8, y + 21, "page 2", "t", 11, "end", 600, True)
        f.text(x0 + 18, y + 20, "...", "tm", 11, "middle", None, True)
        x = x0 + 36
        for (lab, acc), w in zip(cells, widths):
            cell(f, x, y + 6, w, 22, lab, "a af" if acc else "s f", "ta" if acc else "t", 11)
            pos[lab] = x + w / 2
            x += w + 6
        f.text(x + 10, y + 20, "...", "tm", 11, "middle", None, True)
        return pos

    def leaf(x, y, name, keys, cls="s f"):
        f.rect(x, y, 130, 42, cls, 6)
        f.text(x + 65, y + 17, name, "ta" if cls.startswith("a") else "t", 11, "middle", 600, True)
        f.text(x + 65, y + 33, keys, "tm", 10, "middle")

    f.text(616, 48, "before", "t", 11.5, "end", 600)
    p = strip(36, [("14 | 974", False), ("15 | 1061", False), ("16 | 1147", True), ("17 | 1233", False)])
    leaf(120, 100, "page 15", "975-1000, 26 cells")
    leaf(270, 100, "page 16", "1147 only", "a af")
    leaf(420, 100, "page 17", "1148-1233")
    f.line(p["15 | 1061"], 64, 185, 98, "s", arrow=True)
    f.line(p["16 | 1147"], 64, 335, 98, "a", arrow=True)
    f.line(p["17 | 1233"], 64, 485, 98, "s", arrow=True)
    f.line(24, 160, 616, 160, "m", dash=True)
    f.text(616, 188, "after", "t", 11.5, "end", 600)
    p = strip(176, [("14 | 974", False), ("15 | 1147", True), ("17 | 1233", False)])
    leaf(120, 240, "page 15", "975-1000, 26 cells")
    leaf(420, 240, "page 17", "1148-1233")
    f.line(p["15 | 1147"], 204, 185, 238, "a", arrow=True)
    f.line(p["17 | 1233"], 204, 485, 238, "s", arrow=True)
    f.rect(270, 240, 130, 42, "m", 6, dash=True)
    f.text(335, 257, "page 16", "tm", 11, "middle", 600, True)
    f.text(335, 273, "on the freelist", "tm", 10, "middle")
    f.text(24, 304, "(15 | 1061) is gone and the next cell now points at page 15, which covers rowids up to 1147", "tm", 10.5)
    return f


def pred0205():
    f = Fig("f0205c", "Deleting an index entry that lives in an interior page", 262)
    f.text(24, 20, "ix.db: DELETE FROM t WHERE id = 91 must remove the index entry (389, 91) from root page 3", "tm", 11)
    for x, title, ent, leaf_cells in ((24, "before", "16 | 389, 91", [("387, 916", False), ("388, 2004", True)]),
                                      (334, "after", "16 | 388, 2004", [("387, 916", False)])):
        f.text(x, 50, title, "t", 11.5, weight=600)
        f.rect(x, 62, 270, 34, "s fs", 6)
        w = tw(ent, 11, True) + 16
        cell(f, x + 8, 68, w, 22, ent, "a af", "ta", 11)
        f.text(x + 16 + w, 83, "(762, 780) ...", "tm", 10.5, mono=True)
        f.text(x + 262, 112, "root page 3", "tm", 10, "end")
        f.rect(x, 146, 270, 34, "s f", 6)
        f.text(x + 10, 167, "(1, 1088) ...", "tm", 10.5, mono=True)
        cx = x + 104
        for lab, acc in leaf_cells:
            cw = tw(lab, 11, True) + 16
            cell(f, cx, 152, cw, 22, lab, "a af" if acc else "s f", "ta" if acc else "t", 11)
            cx += cw + 6
        f.text(x + 262, 196, "leaf page 16", "tm", 10, "end")
        f.line(x + 30, 90, x + 30, 144, "m", arrow=True)
    f.path("M248 150 C 248 120, 140 126, 112 92", "a", arrow=True)
    f.text(258, 134, "1. copy up", "ta", 10.5, weight=600)
    f.text(24, 222, "1. The entry just before it in key order, the last one in the leaf under its left child,", "t", 10.5)
    f.text(24, 238, "takes its place, so the root keeps a cell. 2. That leaf's copy is then deleted, an easy leaf delete.", "t", 10.5)
    return f


def three0202():
    f = Fig("f0202d", "A split into three pages: cells of 2007, 4007 and 2007 bytes", 268)
    f.text(24, 20, "three.db: rows 1 and 3 of 2000 bytes fill page 2; then rowid 2 arrives with 4000 bytes", "tm", 11)

    def page(x, y, name, cells, free, acc=False, w=150):
        f.rect(x, y, w, 52, "a af" if acc else "s f", 6)
        f.text(x + 8, y + 16, name, "ta" if acc else "t", 11, weight=600, mono=True)
        bx, bw = x + 8, w - 16
        f.rect(bx, y + 24, bw, 18, "m fs", 2)
        cx = bx + bw
        for rid, size in cells:
            cw = bw * size / 4096
            cx -= cw
            cell(f, cx, y + 24, cw, 18, f"rowid {rid}", "s f", "t", 9.5, mono=False, rx=0)
        f.text(x + w - 8, y + 16, f"{free} free", "tm", 10, "end")

    f.text(24, 52, "before", "t", 11.5, weight=600)
    page(24, 62, "page 2", [(1, 2007), (3, 2007)], 70, w=200)
    f.label_box(250, 74, 120, 28, "rowid 2: 4007", "a af", "ta", 10.5, False, 14, 600)
    f.line(250, 88, 228, 88, "a", arrow=True)
    f.text(390, 76, "cut after 1: 2009 | 6018 bytes", "t", 10.5)
    f.text(390, 92, "cut after 2: 6018 | 2009 bytes", "t", 10.5)
    f.text(390, 108, "a page holds 4088: no cut works", "ta", 10.5, weight=600)
    f.line(24, 132, 616, 132, "m", dash=True)
    f.text(24, 156, "after", "t", 11.5, weight=600)
    f.rect(214, 146, 176, 34, "s fs", 6)
    f.text(206, 167, "page 2", "t", 11, "end", 600, True)
    for x, lab, w in ((222, "4 | 1", 52), (280, "5 | 2", 52)):
        cell(f, x, 152, w, 22, lab, "a af", "ta", 11)
    cell(f, 338, 152, 44, 22, "-> 3", "m f", "tm", 11)
    page(24, 206, "page 4", [(1, 2007)], 2079, acc=True)
    page(245, 206, "page 5", [(2, 4007)], 79, acc=True)
    page(466, 206, "page 3", [(3, 2007)], 2079)
    f.line(248, 174, 99, 204, "a", arrow=True)
    f.line(306, 174, 320, 204, "a", arrow=True)
    f.line(360, 174, 541, 204, "s", arrow=True)
    return f


def path0203():
    f = Fig("f0203d", "The insert's path before and after grow_root, and without the shift", 236)
    f.text(24, 20, "inserting rowid 15 into g.db: the path the descent left, at three moments", "tm", 11)
    cols = [(24, "1. before: page 2 is the full leaf", [("0", "page 2", "idx 1", "full leaf", "a af")], "depth 1"),
            (232, "2. after grow_root", [("0", "page 2", "idx 0", "interior, 0 cells", "s f"),
                                         ("1", "page 3", "idx 1", "full leaf", "a af")], "depth 2"),
            (440, "without the shift", [("0", "page 2", "idx 1", "interior now", "s f"),
                                        ("1", "page 0", "", "never set", "m f")], "depth 1")]
    for x, title, rows, depth in cols:
        f.text(x, 50, title, "ta" if title.startswith("without") else "t", 11, weight=600)
        y = 64
        for lvl, pg, idx, note, cls in rows:
            f.text(x, y + 20, f"level {lvl}", "tm", 10.5)
            f.rect(x + 50, y, 126, 30, cls, 6, dash=cls.startswith("m"))
            tc = "ta" if cls.startswith("a") else ("tm" if cls.startswith("m") else "t")
            f.text(x + 60, y + 19, pg, tc, 11, weight=600, mono=True)
            if idx:
                f.text(x + 168, y + 19, idx, tc, 11, "end", None, True)
            f.text(x + 113, y + 44, note, "tm", 10, "middle")
            y += 58
        f.text(x, 196, depth, "tm", 10.5, mono=True)
    f.line(214, 60, 214, 200, "m", dash=True)
    f.line(422, 60, 422, 200, "m", dash=True)
    f.text(24, 224, "The split runs at level 1 and puts its divider in level 0. Without the shift, level 1 is page 0.", "t", 10.5)
    return f


def trunks0205():
    f = Fig("f0205d", "When a trunk is full, the next freed page becomes the first trunk", 214)
    f.text(24, 20, "small.db (512-byte pages, so a trunk holds 120 numbers), after a DELETE freed 129 pages", "tm", 11)
    f.text(24, 52, "page 1", "t", 11, weight=600, mono=True)
    cell(f, 24, 60, 92, 26, "first: 152", "a af", "ta", 10.5)
    cell(f, 120, 60, 92, 26, "free: 129", "s f", "t", 10.5)
    f.path("M70 86 C 70 104, 40 104, 40 120", "a", arrow=True)
    rows = [(122, "page 152", [("next 29", True), ("7", False), ("153", False), ("154", False), ("155", False), ("156", False),
                               ("71", False), ("72", False), ("3", False)], "newer trunk, 7 so far"),
            (170, "page 29", [("next 0", False), ("120", False), ("30", False), ("31", False), ("...", None), ("150", False),
                              ("151", False)], "full: 120 numbers")]
    for y, name, vals, note in rows:
        f.text(24, y + 18, name, "t", 11, weight=600, mono=True)
        x = 92
        for v, acc in vals:
            if acc is None:
                f.text(x + 14, y + 18, "...", "tm", 11, "middle", None, True)
                x += 30
                continue
            w = 58 if v.startswith("next") else 36
            cell(f, x, y, w, 26, v, "a af" if acc else ("s fs" if v.startswith("next") or v in ("7", "120") else "s f"),
                 "ta" if acc else "t", 10.5)
            x += w + 2
        f.text(616, y + 18, note, "tm", 10.5, "end")
    f.path("M121 148 C 121 158, 112 160, 104 168", "a", arrow=True)
    return f


# ------------------------------------------------------------------ cover and icon

def cover():
    a = Art("m02db", "A table as a B-tree of pages: a root, its leaves, and a cursor walking them")
    a.text(24, 28, "s.db: one table, four pages", "tm", 11)
    a.text(24, 62, "a full page splits", "tm", 11)
    a.text(24, 78, "and sends a divider up", "tm", 11)
    a.box(214, 44, 212, 48, "a af", 10)
    a.text(226, 62, "page 2", "ta", 11, weight=600, mono=True)
    for x, lab, w in ((226, "5 | 19", 58), (290, "4 | 180", 66)):
        a.box(x, 68, w, 18, "s f", 4)
        a.text(x + w / 2, 81, lab, "t", 11, "middle", mono=True)
    a.box(362, 68, 52, 18, "s f", 4)
    a.text(388, 81, "-> 3", "tm", 11, "middle", mono=True)
    leaves = [(40, "page 5", "1 .. 19"), (250, "page 4", "20 .. 180"), (460, "page 3", "190 .. 370")]
    for (x, name, keys), sx in zip(leaves, (255, 323, 388)):
        a.box(x, 150, 140, 70, "s f", 8)
        a.add(f'<rect class="s fs" x="{x + 8}" y="158" width="18" height="14" stroke-width="1.5"/>')
        for k in range(3):
            a.add(f'<rect class="a af" x="{x + 28 + k * 9}" y="158" width="8" height="14" stroke-width="1.5"/>')
        for k in range(4):
            a.add(f'<rect class="s f" x="{x + 76 + k * 14}" y="158" width="12" height="14" stroke-width="1.5"/>')
        a.text(x + 12, 194, name, "t", 12, weight=600, mono=True)
        a.text(x + 12, 210, keys, "tm", 11, mono=True)
        a.line(sx, 88, x + 70, 148, "s", arrow=True)
    a.path("M70 238 C 150 262, 230 262, 290 238", "a", arrow=True, dash=True)
    a.path("M320 238 C 380 262, 440 262, 500 238", "a", arrow=True, dash=True)
    a.text(320, 284, "a cursor reads the leaves left to right: every row, in rowid order", "ta", 11.5, "middle")
    return a


ICON = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="none" stroke="currentColor" '
        'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="6.5" y="2.5" width="7" height="4.5" rx="1"/>'
        '<rect x="1.75" y="13" width="5" height="4.5" rx="1"/><rect x="7.5" y="13" width="5" height="4.5" rx="1"/>'
        '<rect x="13.25" y="13" width="5" height="4.5" rx="1"/>'
        '<path d="M10 7v6M8 7l-3.75 6M12 7l3.75 6"/></svg>\n')


FIGS = [
    ("02.01-tree", tree0201), ("02.01-leaf-page", leaf0201), ("02.01-cells", cells0201), ("02.01-search", search0201),
    ("02.02-split", split0202), ("02.02-insert", insert0202), ("02.02-dividers", dividers0202), ("02.02-three-way", three0202),
    ("02.03-grow", grow0203), ("02.03-interior", interior0203), ("02.03-seek", seek0203), ("02.03-path", path0203),
    ("02.04-walk", walk0204), ("02.04-index-order", index0204),
    ("02.05-freelist", freelist0205), ("02.05-merge", merge0205), ("02.05-predecessor", pred0205), ("02.05-trunks", trunks0205),
]


def main():
    for name, fn in FIGS:
        print(figlib.write(MOD, name, fn()))
    d = os.path.join(figlib.LESSONS, MOD)
    s = cover().svg()
    s.encode("ascii")
    with open(os.path.join(d, "cover.svg"), "w") as fh:
        fh.write(s)
    with open(os.path.join(d, "icon.svg"), "w") as fh:
        fh.write(ICON)
    print("cover and icon in", d)


if __name__ == "__main__":
    main()
