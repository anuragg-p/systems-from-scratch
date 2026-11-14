"""Figures, cover and icon for db module 01, Pages (lessons 01.01, 01.02, 01.03).

    python3 art/db/figs01.py

Offsets and bytes are from real files the reference engine wrote (demo.db
with one table t(a) holding 'hello'; a row (1, 'pear', 300, 0.75, NULL)),
dumped with xxd; cache numbers are from DB_STATS=1 runs. The LRU/FIFO trace and the run-on
record are from the probes of 01.02 (look.db, 380 pages, from sqlite3 3.54.1) and 01.03, run on
the project as it stands at those lessons.
"""
import os

import figart
import figlib
from figlib import Fig, write, tw

figlib.LESSONS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                              "tracks", "db", "lessons")
MOD = "01-pages"


def bytebox(f, x, y, b, cls="s f", tcls="t", w=24, h=24, size=11.5):
    f.rect(x, y, w, h, cls, 3)
    f.text(x + w / 2, y + h / 2 + 4, b, tcls, size, "middle", mono=True)


# ------------------------------------------------------------------ 01.01

def pages():
    f = Fig("f0101a", "demo.db: two pages of 4096 bytes", 322)
    X0 = 40
    f.text(24, 22, "demo.db after CREATE TABLE t(a); INSERT INTO t VALUES ('hello'): 8192 bytes (not to scale)", "tm", 11)
    layouts = [
        (80, "page 1", 0, [(120, "database header", "a fa", "f", 0), (70, "page header", "s fs", "t", 100), (40, "ptr", "s fs", "t", 108),
                           (230, "free space", "s f", "tm", 110), (100, "row: table t", "a af", "ta", 4063)], 4096, "0fdf = 4063"),
        (206, "page 2", 4096, [(70, "page header", "s fs", "t", 4096), (40, "ptr", "s fs", "t", 4104),
                               (350, "free space", "s f", "tm", 4106), (100, "row: 'hello'", "a af", "ta", 8183)], 8192, "0ff7 = 4087"),
    ]
    for y, name, base, zones, endoff, ptr in layouts:
        f.text(24, y - 38, name, "t", 12.5, weight=700)
        f.text(84, y - 38, f"starts at (n - 1) x 4096 = {base}", "tm", 11, mono=True)
        x = X0
        xs = {}
        for w, label, cls, tcls, off in zones:
            f.rect(x, y, w, 34, cls, 0)
            f.text(x + w / 2, y + 21, label, tcls, 11, "middle", 600 if cls.startswith("a") else None)
            f.line(x, y + 34, x, y + 40, "m")
            f.text(x, y + 52, str(off), "tm", 10.5, "middle", mono=True)
            xs[label] = (x, w)
            x += w
        f.line(x, y + 34, x, y + 40, "m")
        f.text(x, y + 52, str(endoff), "tm", 10.5, "middle", mono=True)
        px, pw = xs["ptr"]
        cx, cw = [v for k, v in xs.items() if k.startswith("row")][0]
        f.path(f"M{px + pw / 2:.1f} {y - 2} C {px + pw / 2:.1f} {y - 22}, {cx + cw / 2:.1f} {y - 22}, {cx + cw / 2:.1f} {y - 3}", "a", arrow=True)
        f.text((px + cx + cw) / 2, y - 21, "pointer " + ptr, "ta", 10.5, "middle", mono=True)
    f.text(24, 294, "A page is found by arithmetic alone. Inside it, rows fill from the end and the pointers to them", "tm", 11)
    f.text(24, 310, "from the front; page 1 is the same, but after the 100-byte database header.", "tm", 11)
    return f


HEADER = [
    "53 51 4c 69 74 65 20 66 6f 72 6d 61 74 20 33 00",
    "10 00 01 01 00 40 20 20 00 00 00 02 00 00 00 02",
    "00 00 00 00 00 00 00 00 00 00 00 01 00 00 00 04",
    "00 00 00 00 00 00 00 00 00 00 00 01 00 00 00 00",
    "00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00",
    "00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 02",
    "00 2e 7a 70 0d 00 00 00 01 0f df 00 0f df 00 00",
]
# byte offset -> class: set by header_init, set at every commit, set elsewhere, page 1's b-tree header
INIT = set(range(0, 24)) | set(range(44, 48)) | set(range(56, 60)) | set(range(96, 108))
COMMIT = set(range(24, 32)) | set(range(92, 96))
LATER = set(range(40, 44)) | set(range(108, 110))
BTREE = set()
NOTES = [
    ["0  \"SQLite format 3\" and a 0 byte"],
    ["16 page size 0x1000 = 4096", "18 versions 1, 1; 21 fractions 64, 32, 32", "24 change counter 2; 28 page count 2"],
    ["40 schema cookie 1; 44 schema format 4"],
    ["56 text encoding 1: UTF-8"],
    [],
    ["92 version-valid-for 2: page count trusted"],
    ["96 last written by version 3046000", "100 page 1's own header: 0d = table leaf"],
]


def header():
    f = Fig("f0101b", "The first 112 bytes of demo.db, from xxd", 352)
    x0, y0, cw, rh = 52, 44, 19, 40
    f.text(24, 22, "xxd -l 112 demo.db, one box per byte", "tm", 11)
    for r, row in enumerate(HEADER):
        y = y0 + r * rh
        f.text(x0 - 8, y + 16, f"{r * 16:3d}", "tm", 10.5, "end", mono=True)
        for c, b in enumerate(row.split()):
            off = r * 16 + c
            cls, tcls = "m f", "tm"
            if off in INIT:
                cls, tcls = "a af", "ta"
            elif off in COMMIT:
                cls, tcls = "s fs", "t"
            elif off in LATER:
                cls, tcls = "s f", "t"
            if off in LATER:
                f.rect(x0 + c * cw, y, cw - 2, 22, "s f", 3, dash=True)
                f.text(x0 + c * cw + (cw - 2) / 2, y + 15, b, "t", 10, "middle", mono=True)
            else:
                bytebox(f, x0 + c * cw, y, b, cls, tcls, w=cw - 2, h=22, size=10)
        for i, note in enumerate(NOTES[r]):
            f.text(x0 + 16 * cw + 12, y + 10 + i * 13 - (len(NOTES[r]) - 1) * 4, note, "t" if i == 0 else "t", 10.5, mono=False)
    ly = y0 + 7 * rh + 14
    items = [("a af", "header_init()"), ("s fs", "rewritten at every commit"), ("s f", "other code"), ("m f", "zero")]
    x = 24
    for cls, label in items:
        f.rect(x, ly - 11, 14, 14, cls, 3, dash=label == "other code")
        f.text(x + 20, ly, label, "tm", 11)
        x += 20 + tw(label, 11) + 22
    return f


def off_by_one():
    f = Fig("f0101c", "Where page 1 is read from, right and wrong", 236)
    X0, W = 168, 440
    sc = W / 8192.0
    f.text(24, 22, "a file sqlite3 made: two pages", "tm", 11)
    f.rect(X0, 36, W / 2, 30, "s f", 2)
    f.rect(X0 + W / 2, 36, W / 2, 30, "s f", 2)
    f.text(X0 + W / 4, 56, "page 1", "t", 12, "middle", 600)
    f.text(X0 + 3 * W / 4, 56, "page 2", "t", 12, "middle", 600)
    for v in (0, 4096, 8192):
        f.text(X0 + v * sc, 82, str(v), "tm", 10.5, "middle", mono=True)
    rows = [(112, "(pgno - 1) x 4096", 0, "a af", "ta", "byte 100 = 0d: a table leaf. The catalog is read."),
            (176, "pgno x 4096", 4096, "s fs", "t", "byte 100 of page 2 = 00: \"page 1 is not a b-tree page (type 0)\"")]
    for y, formula, off, cls, tcls, what in rows:
        f.text(X0 - 10, y + 19, formula, tcls, 11.5, "end", mono=True)
        f.rect(X0 + off * sc, y, W / 2, 28, cls, 2)
        f.text(X0 + off * sc + W / 4, y + 18, "read_page(p, 1, buf)", tcls, 11, "middle", mono=True)
        f.line(X0 + off * sc + W / 4, y - 2, X0 + off * sc + W / 4, 70, "m", arrow=False, dash=True)
        f.text(X0, y + 46, what, tcls, 11)
    return f


# ------------------------------------------------------------------ 01.02

def cache():
    f = Fig("f0102a", "The page cache: a hash table to find a page, a list to know which is coldest", 366)
    # buckets
    f.text(24, 22, "p->hash: 1024 buckets, bucket = (pgno x 2654435761) & 1023", "tm", 11, mono=False)
    bx, by, bw, bh = 24, 34, 100, 22
    buckets = [("51", []), ("105", ["57"]), ("275", ["3"]), ("433", ["1"]), ("801", ["113"]), ("866", ["2", "1026"]), ("...", None)]
    dirty = {"3", "113"}
    for i, (b, chain) in enumerate(buckets):
        y = by + i * bh
        f.rect(bx, y, bw, bh, "s fs" if chain is not None else "m f", 0)
        f.text(bx + 8, y + 15, f"[{b}]" if b != "..." else "...", "t", 10.5, mono=True)
        if chain:
            f.line(bx + bw - 10, y + bh / 2, 152, y + bh / 2, "s", arrow=True)
            x = 154
            for k, pg in enumerate(chain):
                d = pg in dirty
                f.rect(x, y + 2, 72, bh - 4, "a f" if d else "s f", 4)
                f.text(x + 36, y + 15, f"page {pg}", "ta" if d else "t", 10.5, "middle", mono=True)
                if k + 1 < len(chain):
                    f.line(x + 72, y + bh / 2, x + 86, y + bh / 2, "s", arrow=True)
                x += 88
    f.text(330, by + 5 * bh + 15, "1024 apart: same bucket", "tm", 10.5)
    # LRU list
    ly = 258
    f.text(24, ly - 32, "p->lru: clean pages only, most recently used first", "tm", 11)
    nodes = [("lru", "s fs"), ("page 2", "s f"), ("page 1", "s f"), ("page 57", "s f"), ("...", None), ("page 1026", "s f")]
    x = 24
    xs = []
    for name, cls in nodes:
        w = 72 if name != "..." else 30
        if cls:
            f.rect(x, ly - 18, w, 30, cls, 6)
            f.text(x + w / 2, ly + 2, name, "ta" if cls.startswith("a") else "t", 11, "middle", mono=True)
        else:
            f.text(x + w / 2, ly + 2, name, "tm", 12, "middle")
        xs.append((x, w))
        x += w + 26
    for (x1, w1), (x2, _) in zip(xs, xs[1:]):
        f.line(x1 + w1 + 2, ly - 7, x2 - 3, ly - 7, "s", arrow=True)
        f.line(x2 - 3, ly + 1, x1 + w1 + 2, ly + 1, "m", arrow=True)
    f.text(xs[1][0] + 36, ly + 30, "hot end: lru.next", "t", 10.5, "middle")
    f.text(xs[-1][0] + 36, ly + 30, "cold end: lru.prev", "tm", 10.5, "middle")
    f.text(xs[-1][0] + 36, ly + 44, "evicted first", "tm", 10.5, "middle")
    # dirty
    dx = 470
    f.rect(dx, 40, 146, 116, "s fs", 10)
    f.text(dx + 12, 60, "p->dirty", "t", 12, weight=700, mono=True)
    f.text(dx + 12, 76, "changed, not committed", "tm", 10.5)
    for i, pg in enumerate(("page 113", "page 3")):
        f.rect(dx + 12, 88 + i * 30, 90, 24, "a f", 4)
        f.text(dx + 57, 104 + i * 30, pg, "ta", 10.5, "middle", mono=True)
    f.text(24, 336, "Every cached page is in exactly one bucket. A clean page is also on the list; a dirty one", "tm", 11)
    f.text(24, 352, "is on the dirty list instead, out of eviction's reach until COMMIT writes it.", "tm", 11)
    return f


def life():
    f = Fig("f0102b", "The life of a page in the cache", 196)
    y, h, w = 92, 44, 120
    boxes = [(24, "in the file only", "s fs", "t"), (260, "clean, cached", "s f", "t"), (496, "dirty", "a af", "ta")]
    for x, name, cls, tcls in boxes:
        f.rect(x, y, w, h, cls, 8)
        f.text(x + w / 2, y + 27, name, tcls, 12.5, "middle", 600)
    top, bot = y + 12, y + 32
    # file <-> clean
    f.line(144 + 2, top, 260 - 2, top, "s", arrow=True)
    f.text(202, top - 8, "page_get(): miss", "t", 10.5, "middle", mono=True)
    f.line(260 - 2, bot, 144 + 2, bot, "m", arrow=True)
    f.text(202, bot + 22, "pager_shrink():", "tm", 10.5, "middle", mono=True)
    f.text(202, bot + 36, "the cold end goes", "tm", 10.5, "middle")
    # clean <-> dirty
    f.line(380 + 2, top, 496 - 2, top, "a", arrow=True)
    f.text(438, top - 8, "pager_write()", "ta", 10.5, "middle", mono=True)
    f.line(496 - 2, bot, 380 + 2, bot, "s", arrow=True)
    f.text(438, bot + 22, "COMMIT writes it", "t", 10.5, "middle")
    f.text(438, bot + 36, "to the file", "tm", 10.5, "middle")
    # hit: back to the front
    cx = 320
    f.path(f"M{cx - 22} {y - 2} C {cx - 22} {y - 44}, {cx + 22} {y - 44}, {cx + 22} {y - 4}", "s", arrow=True)
    f.text(cx, y - 50, "page_get(): hit, to the front of the list", "t", 10.5, "middle")
    f.text(24, 186, "Clean pages can be thrown away: the file has the same bytes. A dirty page is the only copy of a change.", "tm", 11)
    return f


def lru_fifo():
    # A real trace of 01.02's probe (a copy of the engine at 01.02 printing the list after each
    # lookup): look.db of 380 pages from sqlite3, DB_CACHE_PAGES=10, the first lookups of the
    # 2,000; lookup i reads page 2, then leaf 3 + i * 7919 % 378.
    f = Fig("f0102c", "The cache after lookup 10, kept in LRU order and in FIFO order", 300)
    f.text(24, 22, "ten slots; each lookup reads the root, page 2, then one leaf; the newest page is on the left", "tm", 11)
    cw = 50
    rows = [
        ("LRU", 70, ["210", "2", "229", "248", "267", "286", "305", "324", "343", "362", "3"],
         "every lookup touches the root, so it stays near the front; leaf 3 goes", "2,001 pages read in 2,000 lookups"),
        ("FIFO", 178, ["210", "229", "248", "267", "286", "305", "324", "343", "362", "3", "2"],
         "the root sits where it was first read and reaches the end; lookup 11 reads it again", "2,200 pages read"),
    ]
    for name, y, slots, note, num in rows:
        f.text(24, y - 14, name, "t", 13, weight=700)
        f.text(616, y - 14, num, "ta" if name == "LRU" else "t", 12, "end", 700)
        for i, s_ in enumerate(slots):
            x = 24 + i * (cw + 4)
            root = s_ == "2"
            out = i == len(slots) - 1
            if out:
                f.rect(x, y, cw, 32, "m f", 4, dash=True)
                f.text(x + cw / 2, y + 21, s_, "tm", 12, "middle", 600 if root else None, True)
            else:
                f.rect(x, y, cw, 32, "a af" if root else "s f", 4)
                f.text(x + cw / 2, y + 21, s_, "ta" if root else "t", 12, "middle", 600 if root else None, True)
        f.text(24 + 10 * (cw + 4) + cw / 2, y + 48, "evicted", "tm", 10.5, "middle")
        f.text(24, y + 48, note, "t", 11)
    f.text(24, 284, "Pages by number; 2 is the root. Eleven are cached after lookup 10; the shrink after it trims to ten.", "tm", 11)
    return f


# ------------------------------------------------------------------ 01.03

def record():
    f = Fig("f0103a", "The row (1, 'pear', 300, 0.75, NULL) as bytes on page 2", 304)
    f.text(24, 22, "CREATE TABLE p(id INTEGER PRIMARY KEY, name TEXT, qty INTEGER, price REAL, note)", "tm", 11, mono=True)
    cells = ["14", "01", "06", "00", "15", "02", "07", "00", "70", "65", "61", "72", "01", "2c",
             "3f", "e8", "00", "00", "00", "00", "00", "00"]
    x0, y, w = 24, 66, 26
    groups = {0: "m", 1: "m", 2: "hl", 3: "st", 4: "st", 5: "st", 6: "st", 7: "st"}
    for i, b in enumerate(cells):
        x = x0 + i * (w + 1)
        if i < 2:
            cls, tcls = "m fs", "tm"
        elif i < 8:
            cls, tcls = "a af", "ta"
        else:
            cls, tcls = "s f", "t"
        bytebox(f, x, y, b, cls, tcls, w=w, h=28, size=12)
    X = lambda i: x0 + i * (w + 1)
    f.brace_h(X(0) + 1, X(2) - 3, 52, "m", up=True)
    f.text(X(0), 46, "the B-tree's", "tm", 10.5)
    f.brace_h(X(2) + 1, X(8) - 3, 52, "a", up=True)
    f.text(X(2) + 4, 46, "record header", "ta", 10.5, weight=600)
    f.brace_h(X(8) + 1, X(22) - 3, 52, "s", up=True)
    f.text(X(8) + 4, 46, "record body: the values, back to back", "t", 10.5, weight=600)
    f.text(X(0), 112, "payload 20,", "tm", 10.5)
    f.text(X(0), 125, "rowid 1", "tm", 10.5)
    # serial types explained
    types = [(2, "06", "header is 6 bytes"), (3, "00", "id: NULL (the rowid holds it)"), (4, "15", "21: text, (21 - 13) / 2 = 4 bytes"),
             (5, "02", "2: integer, 2 bytes"), (6, "07", "7: float, 8 bytes"), (7, "00", "note: NULL, no bytes")]
    for k, (i, b, what) in enumerate(types):
        ty = 152 + k * 22
        f.line(X(i) + w / 2, 96, X(i) + w / 2, ty - 4, "a" if k else "m")
        f.line(X(i) + w / 2, ty - 4, 250, ty - 4, "a" if k else "m")
        f.text(256, ty, what, "t", 11)
    vals = [(8, 12, "'pear'"), (12, 14, "300"), (14, 22, "0.75")]
    for a, b, v in vals:
        f.text((X(a) + X(b) - 1) / 2, 112, v, "t", 12, "middle", 600, True)
        f.brace_h(X(a) + 1, X(b) - 3, 100, "m")
    f.text(24, 292, "22 bytes for five columns: the record is 20, and sqlite3 writes the same bytes for the same row.", "tm", 11)
    return f


def varint():
    f = Fig("f0103b", "Three varints, as the engine wrote them", 300)
    f.text(24, 22, "7 bits of the number per byte, most significant first; a set top bit means another byte follows", "tm", 11)
    # 5
    y = 50
    f.text(24, y + 18, "length 5", "t", 12, weight=600)
    bytebox(f, 140, y, "05", "s f", "t", w=30, h=28, size=12)
    f.text(186, y + 18, "0 0000101: top bit clear, the varint ends here", "tm", 11, mono=False)
    # 300
    y = 104
    f.text(24, y + 18, "rowid 300", "t", 12, weight=600)
    bytebox(f, 140, y, "82", "a af", "ta", w=30, h=28, size=12)
    bytebox(f, 174, y, "2c", "s f", "t", w=30, h=28, size=12)
    f.text(220, y + 12, "300 = 100101100 in binary, cut into 7-bit groups 0000010 0101100", "tm", 11)
    f.text(220, y + 28, "1 0000010 = 82: more follows", "t", 11, mono=True)
    f.text(430, y + 28, "0 0101100 = 2c: the last", "t", 11, mono=True)
    # -1
    y = 170
    f.text(24, y + 18, "rowid -1", "t", 12, weight=600)
    for i in range(9):
        bytebox(f, 140 + i * 34, y, "ff", "a af" if i < 8 else "s f", "ta" if i < 8 else "t", w=30, h=28, size=12)
    f.text(140, y + 48, "-1 is 64 one-bits. Eight bytes carry 7 bits each (56), and the ninth carries all 8 of its bits:", "tm", 11)
    f.text(140, y + 64, "8 x 7 + 8 = 64, so every 64-bit value fits in at most 9 bytes.", "tm", 11)
    f.text(24, 286, "From xxd of two real cells: 05 is a cell's payload length; 82 2c and the nine ff are rowids.", "tm", 11)
    return f


def run_on():
    f = Fig("f0103c", "The pear row's record, right and with the last-byte bit left set", 250)
    f.text(24, 22, "record_build for (NULL, 'pear', 300, 0.75, NULL), the 01.03 probe", "tm", 11)
    hdr_good = ["06", "00", "15", "02", "07", "00"]
    hdr_bad = ["86", "80", "95", "82", "87", "80"]
    names = ["len 6", "NULL", "text 4", "int 2", "real", "NULL"]
    body = ["70", "65", "61", "72", "01", "2c", "3f", "e8"]
    x0, hw, bw = 96, 36, 28
    hx = [x0 + k * (hw + 3) for k in range(6)]
    bx = [x0 + 6 * (hw + 3) + 8 + k * (bw + 3) for k in range(8)]
    for k, n in enumerate(names):
        f.text(hx[k] + hw / 2, 70, n, "tm", 10, "middle")
    for a, b, v in ((0, 4, "'pear'"), (4, 6, "300"), (6, 8, "0.75")):
        f.text((bx[a] + bx[b - 1] + bw) / 2, 70, v, "tm", 10, "middle", None, True)
    f.brace_h(hx[0] + 1, hx[5] + hw - 1, 54, "a", up=True)
    f.text(hx[0], 47, "record header", "ta", 10.5, None, 600)
    f.brace_h(bx[0] + 1, bx[7] + bw - 1, 54, "s", up=True)
    f.text(bx[0], 47, "body: the values, written whole", "t", 10.5, None, 600)
    for r, (label, hdr, cls, tcls) in enumerate((("correct", hdr_good, "s f", "t"), ("broken", hdr_bad, "a af", "ta"))):
        y = 80 + r * 46
        f.text(x0 - 12, y + 20, label, tcls, 12, "end", 600)
        for k, b in enumerate(hdr):
            bytebox(f, hx[k], y, b, cls, tcls, w=hw, h=30, size=12.5)
        for k, b in enumerate(body):
            bytebox(f, bx[k], y, b, "s fs" if (r and k == 0) else "s f", "t", w=bw, h=30, size=12)
        f.text(bx[7] + bw + 6, y + 20, "...", "tm", 12, None, None, True)
    f.brace_h(hx[0] + 1, bx[0] + bw - 1, 166, "a")
    f.text(hx[0], 186, "read back as one varint: 7 bytes, 26,393,920,520,304", "ta", 11, None, 600)
    f.text(24, 216, "Each header byte gains 0x80, \"more follows\", so the header's length runs on until 70, the", "tm", 11)
    f.text(24, 232, "first byte with its top bit clear: far past the 20-byte record, and record_decode returns -1.", "tm", 11)
    return f


# ------------------------------------------------------------------ cover and icon

def cover():
    a = figart.Art("m01db", "The file as numbered pages, a cache of them in memory, and a row packed into bytes")
    a.text(24, 28, "memory: the page cache", "tm", 11)
    a.box(24, 38, 300, 74, "s fs", rx=12)
    for i, (pg, cls) in enumerate((("2", "a af"), ("1", "s f"), ("57", "s f"), ("113", "s f"))):
        a.box(40 + i * 70, 56, 56, 40, cls, rx=6)
        a.text(68 + i * 70, 81, pg, "ta" if cls.startswith("a") else "t", 13, "middle", 600, True)
    a.text(24, 232, "the file: page n at byte (n - 1) x 4096", "tm", 11)
    for i in range(8):
        x = 24 + i * 74
        a.box(x, 166, 66, 46, "a af" if i == 1 else "s f", rx=4)
        a.text(x + 33, 194, str(i + 1) if i < 7 else "...", "ta" if i == 1 else "t", 13, "middle", 600, True)
    a.line(131, 164, 76, 98, "a", arrow=True)
    a.text(122, 140, "read once, then kept in memory", "ta", 11)
    # record zoom
    a.text(372, 28, "a row as bytes", "tm", 11)
    a.box(372, 38, 244, 74, "s f", rx=12)
    for i, b in enumerate(("06", "00", "15", "02", "07", "00")):
        a.box(386 + i * 36, 52, 32, 24, "a af", rx=4)
        a.text(402 + i * 36, 69, b, "ta", 11.5, "middle", None, True)
    a.text(386, 98, "then 'pear', 300, 0.75", "t", 11.5, mono=True)
    a.text(24, 276, "01.01 the file as pages; 01.02 the page cache; 01.03 records: varints and serial types", "tm", 11)
    return a


ICON = ('<rect x="5.5" y="2.75" width="11" height="12.5" rx="1.5"/>'
        '<path d="M3.5 5.75v10a1.5 1.5 0 0 0 1.5 1.5h8.5"/><path d="M8.25 6.5h5.5M8.25 9.25h5.5M8.25 12h3.5"/>')


FIGS = [
    ("01.01-pages", pages),
    ("01.01-header", header),
    ("01.01-off-by-one", off_by_one),
    ("01.02-cache", cache),
    ("01.02-life", life),
    ("01.02-lru-fifo", lru_fifo),
    ("01.03-record", record),
    ("01.03-varint", varint),
    ("01.03-run-on", run_on),
]


def main():
    for name, fn in FIGS:
        print(write(MOD, name, fn()))
    d = os.path.join(figlib.LESSONS, MOD)
    s = cover().svg()
    s.encode("ascii")
    with open(os.path.join(d, "cover.svg"), "w") as fh:
        fh.write(s)
    with open(os.path.join(d, "icon.svg"), "w") as fh:
        fh.write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="none" stroke="currentColor" '
                 'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">' + ICON + "</svg>\n")
    print(os.path.join(d, "cover.svg"), os.path.join(d, "icon.svg"))


if __name__ == "__main__":
    main()
