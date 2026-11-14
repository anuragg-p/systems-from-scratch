"""Figures for db module 07, Fast (lessons 07.01-07.03), plus its cover and icon.

    python3 art/db/figs07.py

The numbers are from real runs on an Apple M4 Pro (macOS 26.6.2) against sqlite3 3.54.1, of the
engine as it stands at each lesson:
  ./learn bench db --at 07.01, first run: autocommit 1.23x, one transaction 0.91x, point lookup
    4.29x, range scan 1.36x, secondary index 3.09x, update 0.82x, delete 0.76x; file 11505664
    against 5914624 bytes (1.95x).
  dbstat over the two benchmark files at 07.01: table t 2292 pages (50.3% full) against 1155
    (99.3%); index t_a 516 pages (55.4%) against 288 (99.0%); 311 (91.7%) when sqlite3 keeps the
    index while the rows go in.
  100000 point lookups, median of 5: ./db 611393/s (602220/s inside one BEGIN), sqlite3 174005/s
    (426707/s inside one BEGIN).
  sample(1) at 07.02 of six rounds of 100000 deletes (1714 samples), each sample counted in the
    first of these on its stack: node_rebuild 783, seeks (walk down) 417, pager_write and the
    statement savepoint 148, plan_query 66, parse_statement 65, the rest 235; of 100000 updates
    (1005): node_rebuild 303, seeks 224, savepoint 52, plan 68, parse 79, the rest 279.
  5 autocommit INSERTs: 20 fsyncs with the journal, 8 in WAL mode (5 + 1 + 2 at the checkpoint).
  20000 rows in rowid order: 249 splits, 250 leaves 99.0% full, 1032192 bytes (sqlite3's file:
    1032192); with append_split turned off 493 splits, 494 leaves 50.2% full, 2031616 bytes.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import figlib  # noqa: E402
from figlib import Fig  # noqa: E402
from figart import Art  # noqa: E402

figlib.LESSONS = os.path.expanduser("~/Documents/WORK/misc/systems-from-scratch/tracks/db/lessons")
MOD = "07-fast"

RATIOS = [("insert, autocommit", 1.23), ("insert, one transaction", 0.91), ("point lookup by primary key", 4.29),
          ("range scan, 100 rows each", 1.36), ("lookup by secondary index", 3.09),
          ("update by key", 0.82), ("delete by key", 0.76)]


# ------------------------------------------------------------------ 07.01

def ratios0701():
    f = Fig("f0701a", "The benchmark as ratios: ./db's speed over sqlite3's, one run", 300)
    f.text(24, 22, "./learn bench db --at 07.01: ops/s of ./db divided by ops/s of sqlite3 (above 1: ./db is faster)", "tm", 11)
    x0, sc = 214, 82
    y0 = 40
    for i, (name, r) in enumerate(RATIOS):
        y = y0 + i * 30
        slow = name in ("update by key", "delete by key")
        f.text(x0 - 10, y + 15, name, "ta" if slow else "t", 11, "end", 600 if slow else None)
        f.rect(x0, y + 3, r * sc, 18, "a fa" if slow else "s fs", 3)
        lx = max(x0 + r * sc, x0 + sc) + 8
        f.text(lx, y + 16, f"{r:.2f}x", "ta" if slow else "t", 11, None, 600, True)
        if name == "insert, one transaction":
            f.text(lx + 46, y + 16, "(another run: 1.05x)", "tm", 10.5)
    f.line(x0 + sc, y0 - 6, x0 + sc, y0 + 7 * 30, "s", dash=True)
    f.text(x0 + sc, y0 + 7 * 30 + 14, "1.0: as fast as sqlite3", "tm", 10.5, "middle")
    f.line(24, 270, 616, 270, "m")
    f.text(24, 290, "file size: 11,505,664 bytes against 5,914,624, 1.95x bigger", "ta", 11, None, 600)
    return f


def pages0701():
    f = Fig("f0701b", "Where the file's extra 1365 pages are: both trees, about half full", 268)
    f.text(24, 22, "pages per B-tree in the benchmark's file (sqlite3's dbstat on both files), and how full they are", "tm", 11)
    bars = [("table t, ./db", 2292, "50.3% full", "a fa"), ("table t, sqlite3", 1155, "99.3% full", "s fs"),
            ("index t_a, ./db", 516, "55.4% full", "a fa"), ("index t_a, sqlite3", 288, "99.0% full", "s fs"),
            ("t_a, sqlite3, kept during inserts", 311, "91.7% full", "s f")]
    x0, sc = 214, 260 / 2292
    for i, (name, pages, full, cls) in enumerate(bars):
        y = 40 + i * 30
        if i == 2:
            y += 8
        if i >= 3:
            y += 8
        f.text(x0 - 10, y + 15, name, "ta" if cls == "a fa" else "t", 11, "end", 600 if cls == "a fa" else None)
        f.rect(x0, y + 3, pages * sc, 18, cls, 3)
        f.text(x0 + pages * sc + 8, y + 16, f"{pages} pages, {full}", "ta" if cls == "a fa" else "t", 10.5)
    f.text(24, 222, "table: the rows arrive in rowid order and ./db splits every full leaf in the middle (07.03)", "t", 11)
    f.text(24, 240, "index: sqlite3 sorts the entries before it builds an index, and rebalances pages when it inserts;", "t", 11)
    f.text(24, 256, "./db inserts entries one by one in table order and splits pages in half", "t", 11)
    return f


def locks0701():
    f = Fig("f0701c", "Point lookups per second, one statement each, and inside one BEGIN", 230)
    f.text(24, 22, "100000 lookups by primary key on the benchmark file, median of 5 runs", "tm", 11)
    bars = [("./db, each its own statement", 611393, "s fs"), ("./db, all inside BEGIN ... COMMIT", 602220, "s fs"),
            ("sqlite3, each its own statement", 174005, "a fa"), ("sqlite3, all inside BEGIN ... COMMIT", 426707, "a af")]
    x0, sc = 244, 300 / 611393
    for i, (name, v, cls) in enumerate(bars):
        y = 40 + i * 30 + (8 if i >= 2 else 0)
        f.text(x0 - 10, y + 15, name, "t", 11, "end")
        f.rect(x0, y + 3, v * sc, 18, cls, 3)
        f.text(x0 + v * sc + 8, y + 16, f"{v:,}/s", "t", 10.5, None, None, True)
    f.text(24, 194, "outside a transaction sqlite3 takes a file lock and checks for a hot journal before every", "t", 11)
    f.text(24, 210, "statement, so that other processes can share the file; ./db assumes it is alone", "t", 11)
    return f


# ------------------------------------------------------------------ 07.02

def profile0702():
    f = Fig("f0702a", "Where the time of a delete and an update goes, from a sampling profiler", 262)
    f.text(24, 22, "sample(1) on six rounds of 100000 deletes, and of 100000 updates; share of samples", "tm", 11)
    parts = {
        "deletes (1714 samples)": [("rebuild the page", 783), ("walk down", 417), ("plan", 66), ("savepoint", 148),
                                   ("parse", 65), ("other", 235)],
        "updates (1005 samples)": [("rebuild the page", 303), ("walk down", 224), ("plan", 68), ("savepoint", 52),
                                   ("parse", 79), ("other", 279)],
    }
    cls = {"rebuild the page": "a fa", "walk down": "a af", "plan": "s fs", "savepoint": "s f", "parse": "s fs", "other": "m"}
    x0, W = 24, 592
    for i, (name, ps) in enumerate(parts.items()):
        y = 40 + i * 80
        tot = sum(v for _, v in ps)
        f.text(x0, y + 10, name, "t", 11.5, None, 600)
        x = x0
        for lab, v in ps:
            w = W * v / tot
            f.rect(x, y + 18, w, 24, cls[lab], 0)
            x += w
        line = " | ".join(f"{lab} {100 * v / tot:.0f}%" for lab, v in ps)
        f.text(x0, y + 60, line, "t", 11)
    f.text(24, 210, "rebuild the page: removing one cell copies every cell out and lays the page out again", "t", 11)
    f.text(24, 228, "walk down: seeks from the root, three or four per row; savepoint: a copy of each page a statement changes", "tm", 10.5)
    f.text(24, 246, "(an update removes the old cell and inserts the new one, so it rebuilds the page too)", "tm", 10.5)
    return f


def fsyncs0702():
    f = Fig("f0702b", "One autocommit INSERT: four fsyncs with the journal, one with the log", 214)
    rows = [("rollback journal", ["journal", "its directory", "journal header", "database"], "a fa"),
            ("write-ahead log", ["the log"], "a fa")]
    for i, (name, syncs, cls) in enumerate(rows):
        y = 34 + i * 70
        f.text(24, y + 4, name, "t", 11.5, None, 600)
        f.line(24, y + 30, 616, y + 30, "m")
        for k, s in enumerate(syncs):
            x = 60 + k * 140
            f.rect(x, y + 16, 26, 28, cls, 4)
            f.text(x + 34, y + 35, s, "t", 11)
    f.text(24, 186, "DB_STATS for five INSERTs: fsyncs 20 with the journal; 8 in WAL mode", "t", 11)
    f.text(24, 204, "(5 commits, 1 for the new log's directory, 2 for the checkpoint when the file is closed)", "tm", 10.5)
    return f


def remove0702():
    f = Fig("f0702c", "Removing one cell: rebuild the page, or drop its pointer and leave a hole", 270)
    f.text(24, 22, "a leaf with cells A..E; C is deleted", "tm", 11)

    def page(x, y, cells, title, tcls="t", hole=None, note=None, mark=""):
        f.text(x, y - 8, title, tcls, 11.5, None, 600)
        f.rect(x, y, 280, 44, "s f", 0)
        f.rect(x, y, 30, 44, "s fs", 0)
        f.text(x + 15, y + 27, "hdr", "tm", 10, "middle")
        xx = x + 280
        for c in cells:
            if c == "_":
                f.rect(xx - 36, y + 4, 34, 36, "m", 2, dash=True)
                f.text(xx - 19, y + 27, mark, "tm", 10, "middle")
                xx -= 36
                continue
            f.rect(xx - 36, y + 4, 34, 36, "a af" if c in ("D", "E") and hole is None else "s fs", 2)
            f.text(xx - 19, y + 27, c, "t", 11.5, "middle", 600, True)
            xx -= 36
        if note:
            f.text(x, y + 62, note[0], "tm", 10.5)
            f.text(x, y + 76, note[1], "tm", 10.5)
    page(24, 54, ["A", "B", "C", "D", "E"], "before", "t", hole=True)
    page(336, 54, ["A", "B", "D", "E"], "./db: copy every cell out, lay them out again", "ta",
         note=("all of D and E move; the whole page", "is rewritten (node_rebuild)"))
    page(24, 176, ["A", "B", "_", "D", "E"], "sqlite3: remove the pointer, free the bytes", "t", hole=True,
         note=("the hole goes on the page's freeblock list", "(header offset 1): nothing else moves"), mark="free")
    page(336, 176, ["A", "B", "_", "D", "E"], "the experiment: remove the pointer only", "t", hole=True,
         note=("the hole is in no list: sqlite3's check", "reports it as fragmentation nobody counted"), mark="?")
    return f


# ------------------------------------------------------------------ 07.03

def splits0703():
    f = Fig("f0703a", "Rows arriving in rowid order: a split in the middle against a split at the end", 300)
    f.text(24, 22, "a full leaf, and the next row (larger than every rowid in it) arrives", "tm", 11)
    cols = [(24, "split in the middle", "s fs", False), (336, "split for an append (07.03)", "a af", True)]
    for x, title, cls, app in cols:
        f.text(x, 48, title, "ta" if app else "t", 12, None, 600)
        # full leaf
        f.rect(x, 60, 120, 30, "s f", 4)
        f.rect(x + 2, 62, 116, 26, "s fs", 3)
        f.text(x + 60, 80, "full", "t", 11, "middle")
        f.text(x + 132, 80, "+ the new row", "tm", 10.5)
        f.line(x + 60, 92, x + 60, 112, "s", arrow=True)
        if not app:
            f.rect(x, 116, 120, 30, "s f", 4)
            f.rect(x + 2, 118, 58, 26, "s fs", 3)
            f.rect(x + 140, 116, 120, 30, "s f", 4)
            f.rect(x + 142, 118, 62, 26, "a af", 3)
            f.text(x + 60, 162, "half full, forever", "t", 10.5, "middle", 600)
            f.text(x + 200, 162, "half, then fills, then splits", "tm", 10.5, "middle")
            f.text(x, 196, "every leaf but the last stays half", "t", 11)
            f.text(x, 212, "empty: no later row can land there", "t", 11)
        else:
            f.rect(x, 116, 120, 30, "s f", 4)
            f.rect(x + 2, 118, 116, 26, "s fs", 3)
            f.rect(x + 140, 116, 120, 30, "s f", 4)
            f.rect(x + 142, 118, 8, 26, "a af", 3)
            f.text(x + 60, 162, "stays full", "t", 10.5, "middle", 600)
            f.text(x + 200, 162, "the new row alone", "tm", 10.5, "middle")
            f.text(x, 196, "every old cell stays together on the", "t", 11)
            f.text(x, 212, "left; the next rows fill the right page", "t", 11)
    f.line(316, 40, 316, 222, "m")
    f.line(24, 236, 616, 236, "m")
    f.text(24, 258, "20000 rows: 493 splits, 494 leaves 50.2% full", "t", 11)
    f.text(336, 258, "249 splits, 250 leaves 99.0% full", "ta", 11, None, 600)
    f.text(24, 282, "it applies only to a table leaf, and only when the row goes after every row on the right-most leaf", "tm", 10.5)
    return f


def size0703():
    f = Fig("f0703b", "File sizes with and without the append split", 224)
    f.text(24, 22, "the same rows, written by each engine", "tm", 11)
    groups = [("20000 rows (rows.py)", [("./db", 1032192, "a fa"), ("./db, no append split", 2031616, "s fs"), ("sqlite3", 1032192, "s f")]),
              ("benchmark file", [("./db", 6852608, "a fa"), ("./db, no append split", 11505664, "s fs"), ("sqlite3", 5914624, "s f")])]
    x0 = 214
    y = 40
    for gname, bars in groups:
        mx = max(v for _, v, _ in bars)
        f.text(24, y + 12, gname, "t", 11.5, None, 600)
        y += 18
        for name, v, cls in bars:
            w = 300 * v / mx
            f.text(x0 - 10, y + 14, name, "t", 11, "end")
            f.rect(x0, y + 2, w, 18, cls, 3)
            f.text(x0 + w + 8, y + 15, f"{v:,}", "t", 10.5, None, None, True)
            y += 24
        y += 8
    return f


# ------------------------------------------------------------------ cover and icon

def cover():
    a = Art("m07db", "Measure, find where the time goes, change one thing, measure again")
    a.text(24, 28, "./db against sqlite3, one run of the benchmark", "tm", 11)
    x0, sc = 230, 70
    for i, (name, r) in enumerate(RATIOS):
        y = 42 + i * 26
        slow = name in ("update by key", "delete by key")
        a.text(x0 - 10, y + 14, name, "ta" if slow else "t", 11, "end")
        a.add(f'<rect class="{"a fa" if slow else "s fs"}" x="{x0}" y="{y + 3}" width="{round(r * sc, 1)}" height="16" rx="3" stroke-width="1.5"/>')
        a.text(round(max(x0 + r * sc, x0 + sc) + 8, 1), y + 15, f"{r:.2f}x", "ta" if slow else "t", 10.5, mono=True)
    a.line(x0 + sc, 36, x0 + sc, 230, "s", dash=True)
    a.text(x0 + sc, 248, "1.0", "tm", 10.5, "middle", mono=True)
    a.text(24, 282, "faster where it skips work sqlite3 does; slower where it rewrites whole pages", "tm", 11.5)
    return a


ICON = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="none" stroke="currentColor" '
        'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M2.75 16.5h14.5"/><rect x="4" y="9" width="3" height="7.5" rx="0.5"/>'
        '<rect x="8.5" y="4" width="3" height="12.5" rx="0.5"/><rect x="13" y="11" width="3" height="5.5" rx="0.5"/></svg>\n')


FIGS = [
    ("07.01-ratios", ratios0701), ("07.01-pages", pages0701), ("07.01-lookups", locks0701),
    ("07.02-profile", profile0702), ("07.02-fsyncs", fsyncs0702), ("07.02-remove-cell", remove0702),
    ("07.03-splits", splits0703), ("07.03-file-size", size0703),
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
