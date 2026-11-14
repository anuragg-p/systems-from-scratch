"""Figures and module art for db module 04 (Running queries): lessons 04.01-04.04.

    python3 art/db/figs04.py

writes tracks/db/lessons/04-queries/figures/*.svg, cover.svg and icon.svg. The bytes,
rowids, page counts and results below come from runs of the engine (xxd of the file,
DB_STATS=1, the query output); the operator names are the ones EXPLAIN prints.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from figlib import Fig, tw  # noqa: E402

MOD = os.path.join(HERE, "..", "..", "tracks", "db", "lessons", "04-queries")


def save(name, fig):
    d = os.path.join(MOD, "figures") if name not in ("cover", "icon") else MOD
    os.makedirs(d, exist_ok=True)
    s = fig if isinstance(fig, str) else fig.svg()
    s.encode("ascii")
    with open(os.path.join(d, name + ".svg"), "w") as f:
        f.write(s)


# ------------------------------------------------------------------ 04.01

OPS = [("Limit", "stops asking once it has n rows", "04.03"),
       ("Sort", "asks for every row, then hands them out in order", "04.03"),
       ("Filter", "passes on only the rows WHERE is true for", "04.02"),
       ("Scan", "one row per call, read from the table's B-tree", "this lesson")]


def operators():
    f = Fig("f0401a", "A query as a stack of operators, each asked for one row at a time", 330)
    f.label_box(150, 14, 180, 32, "the SELECT loop", "s fs", "t", 12, mono=False, weight=600)
    f.text(340, 34, "prints each row it gets, until it gets none", "tm", 10.5)
    ys = [74, 128, 182, 236]
    for (name, what, where), y in zip(OPS, ys):
        hot = name == "Scan"
        f.label_box(150, y, 180, 32, name, "a af" if hot else "s f", "ta" if hot else "t", 13, weight=600)
        f.text(352, y + 14, what, "t", 11)
        f.text(352, y + 28, where, "ta" if hot else "tm", 10.5)
    tops = [46] + [y + 32 for y in ys[:-1]]
    for top, y in zip(tops, ys):
        f.line(196, top + 3, 196, y - 3, "s", arrow=True)
        f.line(284, y - 3, 284, top + 3, "a", arrow=True)
    f.text(186, 64, "next()", "tm", 10.5, "end", None, True)
    f.text(294, 64, "a row", "ta", 10.5)
    # the leaf under Scan
    f.text(24, 311, "table p's leaf", "tm", 10.5)
    cells = ["1", "2", "10", "11"]
    for i, c in enumerate(cells):
        x = 150 + i * 45
        f.rect(x, 294, 45, 26, "s fs" if i else "a af", 0)
        f.text(x + 22.5, 311, c, "ta" if i == 0 else "t", 12, "middle", None, True)
    f.line(172, 274, 172, 291, "a", arrow=True)
    f.text(180, 286, "cursor", "ta", 10.5)
    f.text(340, 311, "the cursor moves one cell per call", "tm", 10.5)
    return f


def record():
    f = Fig("f0401b", "Row 1 of table p as stored, and as decode_row() hands it back", 264)
    f.text(24, 20, "INSERT INTO p(n, s) VALUES ('42', 7);   p is (id INTEGER PRIMARY KEY, n INTEGER, s TEXT)", "tm", 10.5, mono=True)
    f.text(24, 44, "its cell on the leaf page, from xxd", "tm", 11)
    cells = [("06", "size", "s fs"), ("01", "rowid", "a af"), ("04", "hdr", "s f"), ("00", "NULL", "s f"),
             ("01", "int8", "s f"), ("0f", "text 1", "s f"), ("2a", "42", "s fs"), ("37", "'7'", "s fs")]
    x0, cw = 70, 62
    for i, (b, what, cls) in enumerate(cells):
        x = x0 + i * cw
        f.rect(x, 54, cw, 32, cls, 0)
        f.text(x + cw / 2, 75, b, "ta" if cls.startswith("a") else "t", 14, "middle", 600, True)
        f.text(x + cw / 2, 102, what, "ta" if cls.startswith("a") else "tm", 10.5, "middle")
    f.brace_h(x0 + 2 * cw + 2, x0 + 6 * cw - 2, 118, "m")
    f.text(x0 + 4 * cw, 134, "record header: one serial type per column", "tm", 10.5, "middle")
    f.brace_h(x0 + 6 * cw + 2, x0 + 8 * cw - 2, 118, "m")
    f.text(x0 + 7 * cw, 134, "record body", "tm", 10.5, "middle")
    f.text(24, 168, "decoded into a row", "tm", 11)
    out = [("id", "1", "the rowid, put back", "a af"), ("n", "42", "'42' became an integer", "s f"),
           ("s", "'7'", "7 became text", "s f")]
    for i, (col, v, why, cls) in enumerate(out):
        x = 70 + i * 184
        f.rect(x, 178, 168, 34, cls, 6)
        f.text(x + 12, 200, col, "tm", 11, mono=True)
        f.text(x + 84, 201, v, "ta" if cls.startswith("a") else "t", 14, "middle", 600, True)
        f.text(x + 84, 230, why, "ta" if cls.startswith("a") else "tm", 10.5, "middle")
    f.path(f"M{x0 + cw * 1.5} 108 L{x0 + cw * 1.5} 176", "a", arrow=True, dash=True)
    f.text(24, 256, "The record keeps NULL where id is: the rowid already holds it. Affinity changed the other two on the way in.", "tm", 10.5)
    return f


def rowids():
    f = Fig("f0401c", "The rowid each of four INSERTs got", 150)
    X0, PX = 80, 42
    f.line(X0 - 10, 60, X0 + 12 * PX + 8, 60, "m")
    for i in range(0, 13):
        x = X0 + i * PX
        f.line(x, 56, x, 64, "m")
        f.text(x, 80, str(i), "tm", 10, "middle", None, True)
    pts = [(1, "('42', 7)", "largest 0, + 1", "end"), (2, "(NULL, 'x')", "largest 1, + 1", "start"),
           (10, "(10, 1, 'ten')", "asked for 10: free", "end"), (11, "('next')", "largest 10, + 1", "start")]
    for r, vals, why, anchor in pts:
        x = X0 + r * PX
        f.circle(x, 60, 6, "a fa")
        f.line(x, 66, x, 112, "m")
        tx = x - 7 if anchor == "end" else x + 7
        f.text(tx, 108, vals, "t", 11, anchor, None, True)
        f.text(tx, 124, why, "tm", 10.5, anchor)
    f.text(24, 64, "rowid", "tm", 11)
    f.text(24, 24, "INSERT INTO p VALUES (10, 2, 'again')  ->  Error: UNIQUE constraint failed: p.id", "ta", 10.5, "start", None, True)
    return f


# ------------------------------------------------------------------ 04.02

def filt():
    f = Fig("f0402a", "Filter keeps a row only when WHERE is true for it", 214)
    f.text(24, 22, "SELECT id FROM t WHERE n < 6;", "t", 12.5, mono=True, weight=600)
    f.text(24, 52, "rows from the scan", "tm", 10.5)
    f.text(250, 52, "n < 6 evaluated", "tm", 10.5)
    f.text(430, 52, "Filter", "tm", 10.5)
    rows = [("1", "5", "1", "true: kept", True), ("2", "NULL", "NULL", "unknown: dropped", False),
            ("3", "7", "0", "false: dropped", False)]
    for i, (rid, n, val, verdict, keep) in enumerate(rows):
        y = 62 + i * 44
        f.rect(24, y, 170, 32, "s fs", 6)
        f.text(36, y + 21, f"id {rid}", "t", 12, mono=True)
        f.text(110, y + 21, f"n {n}", "t", 12, mono=True)
        f.line(198, y + 16, 244, y + 16, "s", arrow=True)
        f.rect(250, y, 150, 32, "a af" if keep else "s f", 6)
        f.text(325, y + 21, val, "ta" if keep else "t", 13, "middle", 600, True)
        f.line(404, y + 16, 424, y + 16, "s" if keep else "m", arrow=True)
        f.text(430, y + 21, verdict, "ta" if keep else "tm", 12, weight=600 if keep else None)
    f.text(24, 202, "Only 1 passes. NULL is not false, but it is not true either, and WHERE wants true.", "tm", 11)
    return f


def truth():
    f = Fig("f0402b", "AND and OR with NULL as unknown", 214)
    vals = ["1", "0", "NULL"]
    AND = {("1", "1"): "1", ("1", "0"): "0", ("1", "NULL"): "NULL", ("0", "1"): "0", ("0", "0"): "0",
           ("0", "NULL"): "0", ("NULL", "1"): "NULL", ("NULL", "0"): "0", ("NULL", "NULL"): "NULL"}
    OR = {("1", "1"): "1", ("1", "0"): "1", ("1", "NULL"): "1", ("0", "1"): "1", ("0", "0"): "0",
          ("0", "NULL"): "NULL", ("NULL", "1"): "1", ("NULL", "0"): "NULL", ("NULL", "NULL"): "NULL"}
    for k, (name, tab, short) in enumerate((("AND", AND, "0"), ("OR", OR, "1"))):
        x0 = 70 + k * 300
        f.text(x0 - 46, 30, f"a {name} b", "t", 13, weight=700, mono=True)
        f.text(x0 + 120, 30, "b", "tm", 11, "middle", None, True)
        f.text(x0 - 30, 118, "a", "tm", 11, "middle", None, True)
        for j, b in enumerate(vals):
            f.text(x0 + 40 + j * 80, 52, b, "tm", 11, "middle", 600, True)
        for i, a in enumerate(vals):
            y = 62 + i * 40
            f.text(x0 - 6, y + 25, a, "tm", 11, "end", 600, True)
            for j, b in enumerate(vals):
                x = x0 + j * 80
                decided = a == short
                f.rect(x, y, 80, 40, "a af" if decided else "s f", 0)
                v = tab[(a, b)]
                f.text(x + 40, y + 25, v, "ta" if decided else ("tm" if v == "NULL" else "t"), 13, "middle",
                       600 if decided else None, True)
    f.rect(70, 192, 14, 14, "a af", 2)
    f.text(92, 203, "decided by a alone: b is not evaluated", "tm", 11)
    return f


def compare():
    f = Fig("f0402c", "The order of values, and affinity applied before a comparison", 238)
    f.text(24, 20, "every value has a place in one order", "tm", 11)
    groups = [("NULL", ["NULL"], 70), ("numbers, by value", ["-2", "2.5", "3"], 210), ("text, bytewise", ["'10'", "'9'", "'a'"], 210),
              ("blobs", ["x'00'"], 70)]
    x = 24
    for name, items, w in groups:
        f.rect(x, 30, w, 40, "s fs", 6)
        step = w / len(items)
        for i, it in enumerate(items):
            f.text(x + step * (i + 0.5), 56, it, "t", 12.5, "middle", None, True)
        f.text(x + w / 2, 88, name, "tm", 10.5, "middle")
        if x > 24:
            f.text(x - 7, 55, "<", "ta", 14, "middle", 700, True)
        x += w + 14
    f.text(24, 128, "before comparing, a column's affinity converts the other side", "tm", 11)
    ex = [("n = '5'", "n is an INTEGER column holding 5: '5' becomes 5", "1"),
          ("1 = '1'", "two literals, no affinity: a number is never text", "0"),
          ("'10' < '9'", "text compares byte by byte: '1' < '9'", "1")]
    for i, (e, why, r) in enumerate(ex):
        y = 140 + i * 30
        f.rect(24, y, 120, 24, "s f", 5)
        f.text(84, y + 16.5, e, "t", 12, "middle", None, True)
        f.text(156, y + 16.5, why, "t", 11)
        f.text(616, y + 16.5, r, "ta", 13, "end", 700, True)
    return f


# ------------------------------------------------------------------ 04.03

def breaker():
    f = Fig("f0403a", "LIMIT stops the scan early; a Sort in between reads everything first", 262)
    f.text(24, 20, "the same table: 3000 rows on 59 pages", "tm", 11)
    plans = [(24, "SELECT id FROM t LIMIT 3;", ["Limit 3 offset 0", "Scan t"], "3 rows pulled", "pages read 3"),
             (330, "SELECT id, n FROM t ORDER BY n LIMIT 3;", ["Limit 3 offset 0", "Sort by n", "Scan t"],
              "3000 rows pulled", "pages read 59")]
    for x0, sql, ops, pulled, pages in plans:
        f.text(x0, 48, sql, "t", 11, mono=True, weight=600)
        for i, op in enumerate(ops):
            y = 64 + i * 50
            hot = op.startswith("Sort")
            f.label_box(x0 + 20, y, 160, 30, op, "a af" if hot else "s f", "ta" if hot else "t", 12)
            if i:
                f.line(x0 + 100, y - 2, x0 + 100, y - 18, "s", arrow=True)
        ylast = 64 + (len(ops) - 1) * 50 + 30
        f.text(x0 + 100, ylast + 22, pulled, "t", 12, "middle", 600)
        f.text(x0 + 100, ylast + 40, pages, "ta", 12, "middle", 600, True)
    f.text(522, 125, "the first row out", "tm", 10.5)
    f.text(522, 139, "needs the last row in", "tm", 10.5)
    f.text(24, 252, "Measured with DB_STATS=1. Without ORDER BY the scan stops after the first leaf.", "tm", 11)
    return f


def sort_order():
    f = Fig("f0403b", "ORDER BY x over five different kinds of value", 176)
    asc = [("3", "NULL", "m f"), ("5", "2.5", "s f"), ("2", "3", "s f"), ("4", "'a'", "s fs"), ("1", "'b'", "s fs")]
    for k, (title, seq) in enumerate((("ORDER BY x", asc), ("ORDER BY x DESC", list(reversed(asc))))):
        y = 30 + k * 72
        f.text(24, y + 22, title, "t", 11.5, mono=True, weight=600)
        for i, (rid, v, cls) in enumerate(seq):
            x = 180 + i * 88
            f.rect(x, y, 80, 34, cls, 6, dash=v == "NULL")
            f.text(x + 40, y + 22, v, "tm" if v == "NULL" else "t", 13, "middle", None, True)
            f.text(x + 40, y + 50, f"id {rid}", "tm", 10, "middle", None, True)
            if i:
                f.text(x - 4, y + 22, "<" if k == 0 else ">", "ta", 12, "middle", 700, True)
    f.text(24, 168, "NULL first, then numbers by value, then text: the order comparisons already use.", "tm", 11)
    return f


def limit_lanes():
    f = Fig("f0403c", "LIMIT 3 OFFSET 2 over ids 1 to 6, with the test as written and the broken one", 214)
    lanes = [("seen - offset >= limit", ["skip", "skip", "out", "out", "out", "never"], "3 4 5"),
             ("seen >= limit", ["skip", "skip", "out", "never", "never", "never"], "3")]
    for k, (test, kinds, result) in enumerate(lanes):
        y = 40 + k * 80
        f.text(24, y - 10, "as written" if k == 0 else "broken", "t", 12, weight=600)
        f.text(110, y - 10, f"stop when {test}", "tm", 11, mono=True)
        for i, kind in enumerate(kinds):
            x = 24 + i * 72
            cls = {"skip": "m fs", "out": "a af", "never": "m f"}[kind]
            f.rect(x, y, 64, 34, cls, 6, dash=kind == "never")
            f.text(x + 32, y + 22, str(i + 1), "ta" if kind == "out" else "tm", 14, "middle", 600 if kind == "out" else None, True)
            if kind != "never":
                f.text(x + 32, y + 50, f"seen {i + 1}", "tm", 10, "middle", None, True)
        f.text(470, y + 22, "prints: " + result, "ta" if k == 0 else "t", 12.5, weight=600, mono=True)
    ly = 200
    for i, (cls, name, dash) in enumerate((("m fs", "skipped (OFFSET)", False), ("a af", "handed on", False), ("m f", "never asked for", True))):
        x = 24 + i * 170
        f.rect(x, ly - 11, 14, 14, cls, 3, dash=dash)
        f.text(x + 22, ly, name, "tm", 11)
    return f


# ------------------------------------------------------------------ 04.04

def two_phase():
    f = Fig("f0404a", "UPDATE t SET id = id + 100: collect the rowids, then change the rows", 300)
    f.text(24, 22, "UPDATE t SET id = id + 100;   rows 1, 2, 3", "t", 12, mono=True, weight=600)
    # as written
    f.text(24, 52, "as written", "t", 12, weight=600)
    f.text(24, 70, "1. find the rows, keep only their rowids", "tm", 11)
    for i, r in enumerate(["1", "2", "3"]):
        f.rect(270 + i * 40, 58, 36, 22, "a af", 4)
        f.text(288 + i * 40, 73, r, "ta", 12, "middle", 600, True)
    f.text(24, 96, "2. for each: read it, compute, delete the old row, insert the new", "tm", 11)
    leaf_y = 108
    f.text(24, leaf_y + 21, "leaf after", "tm", 10.5)
    for i, r in enumerate(["101", "102", "103"]):
        f.rect(110 + i * 54, leaf_y, 54, 32, "s fs", 0)
        f.text(137 + i * 54, leaf_y + 21, r, "t", 12.5, "middle", None, True)
    f.text(290, leaf_y + 21, "each row visited once: 101|10 102|20 103|30", "t", 11)
    f.line(24, 160, 616, 160, "m", dash=True)
    # the alternative
    f.text(24, 186, "if the scan changed rows as it went (not what the code does)", "t", 12, weight=600)
    seq = ["1", "2", "3", "101", "102", "103", "201", "..."]
    for i, r in enumerate(seq):
        x = 24 + i * 72
        moved = i >= 3
        f.rect(x, 202, 62, 30, "a af" if moved else "s f", 6, dash=r == "...")
        f.text(x + 31, 222, r, "ta" if moved else "t", 12.5, "middle", None, True)
        if i < len(seq) - 1:
            f.line(x + 64, 217, x + 70, 217, "m")
    f.text(24, 254, "Row 1 moves to 101, which lies ahead of the cursor in rowid order, so the scan meets it again", "tm", 11)
    f.text(24, 270, "and moves it to 201, then 301: the update never ends. Collecting the rowids first is what", "tm", 11)
    f.text(24, 286, "stops it, and it is what SQL means: SET is worked out from the rows as they were.", "tm", 11)
    return f


# ------------------------------------------------------------------ module art

def cover():
    f = Fig("m04", "A query runs as a stack of operators that pull rows up from a B-tree", 300)
    f.rect(24, 18, 592, 36, "fs", 10, sw=False)
    f.text(40, 41, "SELECT name FROM fruit WHERE price > 0.5 ORDER BY name LIMIT 2;", "t", 13, mono=True)
    ops = [("Limit 2 offset 0", 76), ("Sort by name", 126), ("Filter (price > 0.5)", 176), ("Scan fruit", 226)]
    for name, y in ops:
        f.label_box(150, y, 200, 30, name, "a af" if name.startswith("Scan") else "s f",
                    "ta" if name.startswith("Scan") else "t", 12.5)
    for y in (106, 156, 206):
        f.line(230, y + 2, 230, y + 18, "s", arrow=True, start=False)
        f.line(270, y + 18, 270, y + 2, "a", arrow=True)
    f.text(220, 120, "next()", "tm", 10.5, "end", None, True)
    f.text(280, 120, "row", "ta", 10.5)
    for i, v in enumerate(["apple 0.5", "fig 2.0", "kiwi 0.75", "pear 0.6"]):
        f.rect(392, 92 + i * 42, 200, 30, "s fs", 0)
        f.text(404, 112 + i * 42, f"{i + 1}  {v}", "t", 12, mono=True)
    f.text(392, 80, "fruit's B-tree leaf", "tm", 11)
    f.path("M390 240 C 370 240, 368 246, 352 246", "a", arrow=True)
    f.text(150, 280, "prints fig, kiwi. One row moves up at a time; only Sort holds them all.", "tm", 11)
    return f


ICON = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="none" stroke="currentColor" '
        'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="2.5" y="2.5" width="9" height="4" rx="1"/><rect x="2.5" y="8" width="9" height="4" rx="1"/>'
        '<rect x="2.5" y="13.5" width="9" height="4" rx="1"/><path d="M15.5 16.5v-12M13 7l2.5-2.5L18 7"/></svg>\n')


def main():
    for name, fn in (("04.01-operators", operators), ("04.01-record", record), ("04.01-rowids", rowids),
                     ("04.02-filter", filt), ("04.02-truth", truth), ("04.02-compare", compare),
                     ("04.03-breaker", breaker), ("04.03-order", sort_order), ("04.03-limit", limit_lanes),
                     ("04.04-two-phase", two_phase)):
        save(name, fn())
    save("cover", cover())
    save("icon", ICON)
    print("wrote module 04 figures, cover and icon to", os.path.normpath(MOD))


if __name__ == "__main__":
    main()
