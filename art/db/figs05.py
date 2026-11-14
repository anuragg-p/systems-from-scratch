"""Figures for db module 05, Indexes and the planner (lessons 05.01-05.03), plus its cover and icon.

    python3 art/db/figs05.py

Every number here comes from a real file written by the engine as it stands at each
lesson (05.01-05.03 make the same files) and dumped:
  demo.db   rows.py's 20000 rows, t(id INTEGER PRIMARY KEY, a INTEGER, b TEXT), a = id * 7919 % 20011,
            then CREATE INDEX t_a ON t(a): table root page 2 (493 signposts, 494 leaves),
            index root page 497 (63 entries, 64 leaves, 19937 entries); 561 pages in all.
            Row 2062 (a = 2) is cell 23 of table leaf 53 (rows 2039-2079); its index entry is
            cell 1 of index leaf 537 (a 1..322). a = 7919 is in index leaf 523 (a 7843..8152),
            its row (id 1) in table leaf 4 (rows 1-44, signpost 44).
            a = 100..105 are rows 3045, 4076, 5107, 6138, 7169, 8200 on table leaves 77, 102,
            127, 152, 178, 203; rows 19998-20000 are on leaf 3 (rows 19956-20000).
  dup.db    d(id INTEGER PRIMARY KEY, a): (1,7) (2,9) (3,5) (8,7) (9,7), index d_a.
  base.db   the benchmark's 100000-row file at 05.03: WHERE a >= 0 through t_a reads 100530
            pages (80 ms), the same rows by a scan 2293 pages (12 ms); the table is 2292 pages.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import figlib  # noqa: E402
from figlib import Fig  # noqa: E402
from figart import Art  # noqa: E402

figlib.LESSONS = os.path.expanduser("~/Documents/WORK/misc/systems-from-scratch/tracks/db/lessons")
MOD = "05-indexes"


def byte_row(f, x, y, items, h=30):
    """items: (width, text, sub, cls). Draws boxes left to right; returns the x of each box's centre."""
    mids = []
    for w, text, sub, cls in items:
        f.rect(x, y, w, h, cls, 0)
        tcls = "ta" if cls.startswith("a") else "t"
        f.text(x + w / 2, y + h / 2 + 4, text, tcls, 11.5, "middle", None, True)
        if sub:
            f.text(x + w / 2, y + h + 14, sub, "tm", 10.5, "middle")
        mids.append(x + w / 2)
        x += w
    return mids


# ------------------------------------------------------------------ 05.01

def entry0501():
    f = Fig("f0501a", "One row of the table and its entry in the index, byte by byte", 306)
    f.text(24, 22, "row 2062 of demo.db, as stored in the table: leaf page 53, 47 bytes", "tm", 11)
    top = byte_row(f, 24, 34, [
        (40, "2c", "size 44", "s f"),
        (58, "90 0e", "rowid", "a af"),
        (34, "04", "hdr", "s fs"),
        (34, "00", "id", "s fs"),
        (34, "01", "a", "s fs"),
        (34, "5b", "b", "s fs"),
        (40, "02", "a = 2", "a af"),
        (318, "72 6f 77 20 32 30 36 32 20 78 ...", "b: 'row 2062 xxx...', 39 bytes", "s f"),
    ])
    f.text(508, 162, "its entry in the index", "tm", 11)
    f.text(508, 178, "t_a: leaf 537, 7 bytes", "tm", 11)
    bot = byte_row(f, 250, 150, [
        (40, "06", "size 6", "s f"),
        (34, "03", "hdr", "s fs"),
        (34, "01", "a", "s fs"),
        (34, "02", "rowid", "s fs"),
        (40, "02", "a = 2", "a af"),
        (64, "08 0e", "rowid 2062", "a af"),
    ])
    f.path(f"M{top[6]} 86 C {top[6]} 110, {bot[4]} 110, {bot[4]} 148", "a", arrow=True)
    f.path(f"M{top[1]} 86 C {top[1]} 124, {bot[5]} 104, {bot[5]} 148", "a", arrow=True, dash=True)
    f.text(24, 166, "the key: the indexed", "t", 11.5)
    f.text(24, 182, "value, then the rowid,", "t", 11.5)
    f.text(24, 198, "as one record (2, 2062)", "t", 11.5)
    f.line(24, 222, 616, 222, "m")
    f.text(24, 244, "in the table the rowid is the cell's key, outside the record (id is stored as NULL there);", "tm", 10.5)
    f.text(24, 260, "in the index it is the last field of the record, so equal values of a still sort by rowid", "tm", 10.5)
    f.text(24, 284, "an entry carries no other column: to read b, a lookup goes back to the table with the rowid", "t", 11)
    return f


def trees0501():
    f = Fig("f0501b", "The table and its index: two B-trees in one file", 300)
    # table
    f.text(160, 22, "table t (rowid order)", "t", 12, "middle", 600)
    f.rect(70, 38, 180, 40, "s f", 6)
    f.text(160, 54, "page 2: 493 signposts", "t", 11.5, "middle", None, True)
    f.text(160, 70, "rowids only, no rows", "tm", 10.5, "middle")
    for x, a, b in ((24, "leaf 4", "rows 1-44"), (110, "leaf 53", "2039-2079"), (196, "leaf 3", "19956-20000")):
        f.rect(x, 128, 82, 40, "s f", 6)
        f.line(160, 78, x + 41, 126, "s", arrow=True)
        f.text(x + 41, 146, a, "t", 11, "middle", None, True)
        f.text(x + 41, 160, b, "tm", 10.5, "middle")
    # index
    f.text(480, 22, "index t_a (a order, then rowid)", "ta", 12, "middle", 600)
    f.rect(370, 38, 220, 40, "a af", 6)
    f.text(480, 54, "page 497: 63 entries", "ta", 11.5, "middle", None, True)
    f.text(480, 70, "each one (a, rowid), like any other", "tm", 10.5, "middle")
    for x, a, b in ((352, "leaf 537", "a 1..322"), (438, "leaf 523", "a 7843..8152"), (524, "...", "64 leaves")):
        f.rect(x, 128, 82, 40, "a af", 6)
        f.line(480, 78, x + 41, 126, "a", arrow=True)
        f.text(x + 41, 146, a, "ta", 11, "middle", None, True)
        f.text(x + 41, 160, b, "tm", 10.5, "middle")
    f.path("M479 170 C 479 232, 65 232, 65 172", "a", arrow=True, dash=True)
    f.text(320, 248, "the entry (7919, 1) in leaf 523 leads back to row 1 in leaf 4", "ta", 11, "middle")
    f.text(160, 276, "494 leaves hold all 20000 rows", "tm", 10.5, "middle")
    f.text(480, 276, "63 entries in the root + 19937 in the leaves", "tm", 10.5, "middle")
    f.text(480, 292, "= 20000: one entry per row", "tm", 10.5, "middle")
    return f


# ------------------------------------------------------------------ 05.02

def lookup0502():
    f = Fig("f0502a", "WHERE a = 7919: five page reads, through the index and back to the table", 270)
    f.text(24, 22, "SELECT id, a FROM t WHERE a = 7919, on demo.db: the pages read, in order", "tm", 11)
    steps = [
        (24, 48, "1", "page 1", "the schema:", "t_a is at 497"),
        (210, 48, "2", "page 497", "index root: left", "of (8153, 1123)"),
        (210, 156, "3", "page 523", "index leaf:", "(7919, rowid 1)"),
        (436, 48, "4", "page 2", "table root:", "1 <= 44: child 4"),
        (436, 156, "5", "page 4", "table leaf:", "the row 1|7919"),
    ]
    for x, y, n, name, a, b in steps:
        hot = n in ("2", "3")
        f.rect(x, y, 170, 62, "a af" if hot else "s f", 8)
        f.circle(x + 18, y + 18, 11, "a fa" if hot else "s fs")
        f.text(x + 18, y + 22, n, "t", 11.5, "middle", 700)
        f.text(x + 38, y + 23, name, "ta" if hot else "t", 12, None, 600, True)
        f.text(x + 14, y + 42, a, "tm", 10.5)
        f.text(x + 14, y + 56, b, "t", 10.5, None, None, True)
    f.line(194, 79, 208, 79, "s", arrow=True)
    f.line(295, 110, 295, 154, "a", arrow=True)
    f.path("M380 187 C 410 187, 400 79, 434 79", "a", arrow=True)
    f.text(432, 140, "rowid 1", "ta", 10.5, None, 600, True)
    f.line(521, 110, 521, 154, "s", arrow=True)
    f.text(24, 248, "DB_STATS: pages read 5. A scan for the same row reads page 1 and every page of the table: 496.", "t", 11)
    return f


def bias0502():
    f = Fig("f0502b", "Where a seek lands among equal keys: bias -1 and bias +1", 244)
    f.text(24, 22, "index d_a of dup.db, in key order; probe: a = 7 (compare 1 field, ignore the rowid)", "tm", 11)
    ents = [("5", "3"), ("7", "1"), ("7", "8"), ("7", "9"), ("9", "2")]
    x0, w = 90, 92
    for i, (a, r) in enumerate(ents):
        x = x0 + i * w
        hot = a == "7"
        f.rect(x, 76, w - 10, 40, "a af" if hot else "s f", 6)
        f.text(x + (w - 10) / 2, 101, f"({a}, {r})", "ta" if hot else "t", 12, "middle", None, True)
    f.text(x0 - 12, 101, "a, rowid", "tm", 10.5, "end")
    # bias -1
    xa = x0 + w - 5
    f.line(xa, 54, xa, 72, "a", arrow=True)
    f.text(xa, 50, "bias -1: before every 7", "ta", 11, "middle", 600)
    xb = x0 + 4 * w - 5
    f.line(xb, 138, xb, 120, "s", arrow=True)
    f.text(xb, 154, "bias +1: after every 7", "t", 11, "middle", 600)
    f.text(24, 190, "-1 is the start of a range: WHERE a = 7 reads (7,1) (7,8) (7,9), stops at (9,2): ids 1, 8, 9", "t", 11)
    f.text(24, 210, "+1 skips them all: the first entry it sees is (9, 2), already past the bound: no rows", "t", 11)
    f.text(24, 230, "bias is only the answer to a tie: with no equal entries both land in the same place", "tm", 10.5)
    return f


def range0502():
    f = Fig("f0502c", "A range through the index jumps around the table; a rowid range does not", 250)
    f.text(24, 22, "WHERE a BETWEEN 100 AND 105: six neighbours in one index leaf", "tm", 11)
    f.rect(24, 34, 324, 36, "a af", 6)
    f.text(32, 56, "leaf 537", "ta", 10.5, None, 600, True)
    ents = ["100", "101", "102", "103", "104", "105"]
    rows = [("3045", "77"), ("4076", "102"), ("5107", "127"), ("6138", "152"), ("7169", "178"), ("8200", "203")]
    for i, a in enumerate(ents):
        x = 92 + i * 42
        f.rect(x, 40, 38, 24, "a f", 4)
        f.text(x + 19, 56, a, "ta", 10.5, "middle", None, True)
    for i, (rid, pg) in enumerate(rows):
        x = 24 + i * 102
        f.rect(x, 116, 92, 40, "s f", 6)
        f.text(x + 46, 132, f"leaf {pg}", "t", 11, "middle", None, True)
        f.text(x + 46, 148, f"row {rid}", "tm", 10.5, "middle", None, True)
        f.line(92 + i * 42 + 19, 66, x + 46, 114, "a", arrow=True)
    f.text(24, 178, "10 page reads: page 1, two index pages, the table root, and six different leaves", "t", 11)
    f.line(24, 194, 616, 194, "m")
    f.text(24, 216, "WHERE id > 19997: the rows sit side by side in table leaf 3, read in one go", "tm", 11)
    f.text(24, 236, "3 page reads: page 1, the table root, leaf 3", "t", 11)
    return f


# ------------------------------------------------------------------ 05.03

def ladder0503():
    f = Fig("f0503a", "The planner's five rules, tried in order; the first that matches wins", 306)
    f.text(24, 22, "on demo.db: t(id INTEGER PRIMARY KEY, a, b) with an index t_a on a", "tm", 11)
    rules = [
        ("1", "the rowid equals a constant", "WHERE id = 42", "SEARCH t USING INTEGER PRIMARY KEY (rowid=?)"),
        ("2", "an index's first column equals one", "WHERE a = 7919", "SEARCH t USING INDEX t_a (a=?)"),
        ("3", "the rowid has a bound", "WHERE id BETWEEN 10 AND 20", "... INTEGER PRIMARY KEY (rowid>? AND rowid<?)"),
        ("4", "an index's first column has a bound", "WHERE a > 5", "SEARCH t USING INDEX t_a (a>?)"),
        ("5", "anything else", "WHERE b = 'x'", "SCAN t"),
    ]
    for i, (n, cond, ex, out) in enumerate(rules):
        y = 38 + i * 46
        cls = "s fs" if n == "5" else "a af"
        f.rect(24, y, 592, 38, cls, 6)
        f.circle(44, y + 19, 10, "a fa" if n != "5" else "s f")
        f.text(44, y + 23, n, "t", 11.5, "middle", 700)
        f.text(62, y + 16, cond, "t", 11.5, None, 600)
        f.text(62, y + 31, ex, "tm", 10.5, None, None, True)
        f.text(606, y + 24, out, "ta" if n != "5" else "t", 10.5, "end", None, True)
    f.text(24, 284, "WHERE id = 2 AND a = 6 matches rules 1 and 2: rule 1 is tried first, so the rowid wins", "t", 11)
    f.text(24, 300, "a + 0 > 5 and a > 5 OR id = 3 fit no rule: they scan", "tm", 10.5)
    return f


def trees0503():
    f = Fig("f0503b", "Two plans for the same WHERE: the index's order makes the sort unnecessary", 254)
    cols = [(24, "... WHERE a > 5 ORDER BY a LIMIT 3",
             [("Limit 3 offset 0", "s f"), ("Filter (a > 5)", "s f"), ("Index range t using t_a (a > ?)", "a af")]),
            (330, "... WHERE a > 5 ORDER BY b LIMIT 3",
             [("Limit 3 offset 0", "s f"), ("Sort by b", "s fs"), ("Filter (a > 5)", "s f"), ("Index range t using t_a (a > ?)", "a af")])]
    for x, q, ops in cols:
        f.text(x, 24, q, "tm", 10.5, None, None, True)
        for i, (name, cls) in enumerate(ops):
            y = 38 + i * 44
            xx = x + i * 14
            f.rect(xx, y, 272 - i * 14, 30, cls, 6)
            f.text(xx + 10, y + 19, name, "ta" if cls.startswith("a") else "t", 11, None, None, True)
            if i:
                f.line(xx - 4, y - 14, xx - 4, y + 14, "m")
                f.line(xx - 4, y + 14, xx + 2, y + 14, "m")
    f.text(24, 186, "rows flow up one at a time; Limit", "t", 11)
    f.text(24, 202, "stops asking after 3, so only a few", "t", 11)
    f.text(24, 218, "index entries are ever read", "t", 11)
    f.text(330, 226, "Sort must pull every row before it", "t", 11)
    f.text(330, 242, "can hand out the first", "t", 11)
    f.text(24, 242, "(our EXPLAIN, outermost first)", "tm", 10.5)
    return f


def wrong0503():
    f = Fig("f0503c", "A rule that is usually right: an index range that matches every row", 230)
    f.text(24, 22, "SELECT b FROM t WHERE a >= 0 on the benchmark's file: 100000 rows, all of them match", "tm", 11)
    bars = [("through t_a (rule 4)", 100530, 80, "a fa"), ("scan (a + 0 >= 0)", 2293, 12, "s fs")]
    x0, wmax = 190, 300
    for i, (name, pages, ms, cls) in enumerate(bars):
        y = 50 + i * 54
        f.text(x0 - 10, y + 18, name, "t", 11.5, "end")
        w = max(3, wmax * pages / 100530)
        f.rect(x0, y + 2, w, 24, cls, 3)
        f.text(x0 + w + 8, y + 18, f"{pages:,} page reads", "t", 11, None, 600)
        f.text(x0 - 10, y + 34, f"{ms} ms (median of 7)", "tm", 10.5, "end")
    f.text(24, 172, "the index hands out rows in a order, which is no order at all for the table: almost every row is a", "t", 11)
    f.text(24, 188, "fresh table leaf, and the 500-page cache cannot hold the 2292-page table, so leaves are read again and again", "t", 11)
    f.text(24, 214, "sqlite3 picks the index too, until ANALYZE gives it statistics: then it plans SCAN t", "tm", 10.5)
    return f


# ------------------------------------------------------------------ cover and icon

def cover():
    a = Art("m05db", "A query, a plan, and an index that leads back to the table")
    a.box(24, 30, 250, 40, "s fs", 10)
    a.text(40, 55, "SELECT b FROM t WHERE a = 7", "t", 12.5, mono=True)
    a.line(274, 50, 330, 50, "s", arrow=True)
    a.box(332, 30, 120, 40, "a af", 10)
    a.text(392, 55, "planner", "ta", 12.5, "middle", 600)
    a.text(470, 46, "index on a?", "tm", 11)
    a.text(470, 62, "use it", "tm", 11)
    # index tree
    a.box(120, 104, 120, 30, "a af", 8)
    a.text(180, 124, "t_a", "ta", 12, "middle", 600, True)
    for x in (64, 152, 240):
        a.box(x, 176, 76, 30, "a af", 6)
        a.line(180, 134, x + 38, 174, "a")
    a.text(190, 196, "(7, 7217)", "ta", 11, "middle", None, True)
    # table tree
    a.box(400, 104, 120, 30, "s f", 8)
    a.text(460, 124, "t", "t", 12, "middle", 600, True)
    for x in (344, 432, 520):
        a.box(x, 176, 76, 30, "s f", 6)
        a.line(460, 134, x + 38, 174, "s")
    a.text(470, 196, "row 7217", "t", 11, "middle", None, True)
    a.path("M228 206 C 260 260, 440 260, 470 208", "a", arrow=True, dash=True)
    a.text(350, 270, "the entry's rowid leads back to the row", "ta", 11.5, "middle")
    a.line(392, 70, 192, 102, "a", arrow=True, dash=True)
    return a


ICON = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="none" stroke="currentColor" '
        'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="2" y="3" width="7" height="14" rx="1.5"/><path d="M4 6.5h3M4 10h3M4 13.5h3"/>'
        '<circle cx="14" cy="8.5" r="3.25"/><path d="M16.4 10.9l2.1 2.1"/></svg>\n')


FIGS = [
    ("05.01-entry", entry0501), ("05.01-trees", trees0501),
    ("05.02-lookup", lookup0502), ("05.02-bias", bias0502), ("05.02-range", range0502),
    ("05.03-ladder", ladder0503), ("05.03-trees", trees0503), ("05.03-wrong-index", wrong0503),
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
