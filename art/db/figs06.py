"""Figures for db module 06, Transactions (lessons 06.01-06.04), plus its cover and icon.

    python3 art/db/figs06.py

Every number here comes from a real run of the engine as it stands at each lesson
(06.01-06.04, all four make the same file) on rows06.py's file: 2000 rows,
t(id INTEGER PRIMARY KEY, b TEXT), b = 'old ' + 80 x 'o', 92 pages. Page 2 is the root;
the leaves are pages 4..92 (rows 1-22, 23-44, ...; 22 cells each) and page 3 (rows 1961-2000,
40 cells). Cells are 91 bytes (90 for rows below 128), packed down from the end of the page.
  UPDATE t SET b = 'new' changes page 1 and the 90 leaves: 91 dirty pages, written in page
  order. A crash after 46 of them (db-partial) leaves pages 1, 3, 4-47 new: rows 1-970 and
  1961-2000, 1010 rows.
  db-torn writes the first 2048 bytes of page 47 (rows 949-970): the new header says 22 cells
  from 3898, pointers 4087, 4078, ...; at 4087 the old page holds 'ooo...' (0x6f = 111).
  sqlite3: "Tree 2 page 47 cell 20: Rowid 111 out of order".
  With UPDATE t SET b = upper(b) WHERE id > 1960 (pages 1 and 3) the torn page 3 passes
  PRAGMA integrity_check: rows 1984-2000 new, 1961-1982 old, row 1983 (at 2003-2093) half.
  The journal of that UPDATE (06.02): 91 records, 373976 bytes; header d9d505f9 20a163d7,
  nRec 0x5b, nonce 3fb5444e (random each time), 0x5c pages, sector 0x200, page 0x1000.
  Every crash point, then sqlite3 opening the file: 0 rows changed.
  sqlite3 killed inside BEGIN with cache_size=10 (06.03) left 12 hot segments of 7 records at
  offsets 0, 29696, ..., 326656 (pages 4-87) and a thirteenth at 356352 not yet hot (6
  records, pages 88-92 and 3); 381488 bytes. Pages 4-86 of the database file were already
  overwritten (1828 rows). Recovery restored 84 pages.
  WAL (06.04): UPDATE ... WHERE id <= 100 with a crash in the checkpoint (checkpoint-partial):
  frames for pages 4 to 8, the commit mark (92 pages) on the fifth; header 377f0683 002de218
  00001000 00000000 00000001 228094d4 1604e6d8 df5e6365; 20632 bytes. The database file
  alone shows 22 changed rows (page 4 was copied back), with the log all 100.
  wal-partial on UPDATE t SET b = 'new': 45 of 90 frames (pages 3-92); with the mark moved
  to the first frame, frame 1 (page 3, rows 1961-2000) reads as a commit: 40 rows.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import figlib  # noqa: E402
from figlib import Fig  # noqa: E402
from figart import Art  # noqa: E402

figlib.LESSONS = os.path.expanduser("~/Documents/WORK/misc/systems-from-scratch/tracks/db/lessons")
MOD = "06-transactions"


def hexrow(f, x, y, items, h=30, size=11):
    """items: (width, text, sub, cls); returns the right edge."""
    for w, text, sub, cls in items:
        f.rect(x, y, w, h, cls, 0)
        f.text(x + w / 2, y + h / 2 + 4, text, "ta" if cls.startswith("a") else "t", size, "middle", None, True)
        if sub:
            f.text(x + w / 2, y + h + 14, sub, "tm", 10.5, "middle")
        x += w
    return x


# ------------------------------------------------------------------ 06.01

def half0601():
    f = Fig("f0601a", "A commit cut in half: the file holds whichever pages were written first", 254)
    f.text(24, 22, "UPDATE t SET b = 'new', no journal: 91 changed pages, written in page order", "tm", 11)
    pages = [1] + list(range(3, 93))
    x0, w = 36, 6.1
    for i, pg in enumerate(pages):
        x = x0 + i * w
        if i < 46:
            f.rect(x, 44, w - 1.8, 34, "a fa" if pg in (1, 3) else "a af", 1)
        else:
            f.rect(x, 44, w - 1.8, 34, "m", 1)
    xc = x0 + 46 * w - 0.9
    f.line(xc, 34, xc, 92, "a")
    f.text(xc + 6, 100, "SIGKILL here (DB_CRASH=db-partial)", "ta", 11, None, 600)
    f.text(x0, 100, "written: 1, 3, 4 ... 47", "t", 11)
    f.text(x0 + 91 * w - 1.8, 118, "48 ... 92: never written", "tm", 11, "end")
    f.text(x0, 38, "1, 3", "ta", 10, None, None, True)
    f.line(24, 130, 616, 130, "m")
    f.text(24, 150, "what the rows say afterwards", "t", 11.5, None, 600)
    rows = [("rows 1-970", "pages 4-47", "new", "a af"), ("rows 971-1960", "pages 48-92", "old", "m"),
            ("rows 1961-2000", "page 3", "new", "a af")]
    x = 24
    for (r, p, st, cls), w2 in zip(rows, (198, 206, 194)):
        f.rect(x, 162, w2 - 6, 40, cls, 6)
        f.text(x + 10, 179, f"{r}: {st}", "ta" if st == "new" else "t", 11.5, None, 600)
        f.text(x + 10, 195, p, "tm", 10.5)
        x += w2
    f.text(24, 226, "1010 of 2000 rows changed. Not a prefix of the rows either: page 3, the last leaf,", "t", 11)
    f.text(24, 242, "has a low page number, so the newest rows were among the first written", "t", 11)
    return f


def page_bar(f, y, x0=40, w=560):
    sc = w / 4096

    def X(off):
        return x0 + off * sc
    return X


def torn0601():
    f = Fig("f0601b", "A torn page: the new page's first half over the old page's second half", 286)
    f.text(24, 22, "page 47 after DB_CRASH=db-torn (UPDATE t SET b = 'new'): 4096 bytes, drawn to scale", "tm", 11)
    X = page_bar(f, 0)
    y = 60
    f.rect(X(0), y, X(2048) - X(0), 46, "a af", 0)
    f.rect(X(2048), y, X(4096) - X(2048), 46, "s fs", 0)
    f.rect(X(0), y, X(52) - X(0), 46, "a fa", 0)
    f.text(X(0), y - 8, "0", "tm", 10.5, None, None, True)
    f.text(X(2048), y - 8, "2048", "tm", 10.5, "middle", None, True)
    f.text(X(4096), y - 8, "4096", "tm", 10.5, "end", None, True)
    f.text(X(120), y + 20, "written: the new page's first half", "ta", 11, None, 600)
    f.text(X(120), y + 36, "header: 22 cells, content starts at 3898", "t", 10.5)
    f.text(X(2140), y + 20, "never written: the old page", "t", 11, None, 600)
    f.text(X(2140), y + 36, "old cells, 'old oooooooo...'", "tm", 10.5, None, None)
    # pointer from header to 4087
    f.path(f"M{X(30)} {y + 46} C {X(30)} {y + 100}, {X(4087)} {y + 100}, {X(4087)} {y + 50}", "a", arrow=True)
    f.text(X(1100), y + 96, "cell 0's pointer: 4087", "ta", 11, "middle", 600, True)
    f.rect(X(2560), y + 112, 560 + 40 - X(2560), 54, "s f", 6)
    f.text(X(2560) + 10, y + 130, "at 4087: 6f 6f 6f 6f 6f ...", "t", 11, None, None, True)
    f.text(X(2560) + 10, y + 146, "'ooo': size 111, rowid 111", "t", 11)
    f.text(X(2560) + 10, y + 160, "(0x6f = 111 = 'o')", "tm", 10.5)
    f.text(24, y + 130, "the new cells were meant for 3898-4096,", "t", 11)
    f.text(24, y + 146, "in the half that never reached the disk", "t", 11)
    f.line(24, y + 182, 616, y + 182, "m")
    f.text(24, y + 202, "sqlite3: Tree 2 page 47 cell 20: Rowid 111 out of order", "t", 10.5, None, None, True)
    f.text(24, y + 218, "./db:    database is corrupt: bad record in table t, rowid 111", "t", 10.5, None, None, True)
    return f


def silent0601():
    f = Fig("f0601c", "The same tear with a same-size update: every check passes, one row is half old", 250)
    f.text(24, 22, "UPDATE t SET b = upper(b) WHERE id > 1960 writes pages 1 and 3; page 3 torn at 2048", "tm", 11)
    X = page_bar(f, 0)
    y = 58
    f.rect(X(0), y, X(88) - X(0), 40, "m fs", 0)
    f.rect(X(88), y, X(456) - X(88), 40, "m", 0)
    f.text(X(0), y - 6, "hdr", "tm", 10, None, None)
    f.text((X(88) + X(456)) / 2, y + 25, "free", "tm", 10.5, "middle")
    for k in range(40):
        start = 4005 - 91 * k
        if start + 91 <= 2048:
            cls = "a af"
        elif start >= 2048:
            cls = "s fs"
        else:
            cls = None
        if cls:
            f.rect(X(start), y, X(start + 91) - X(start), 40, cls, 0)
        else:
            f.rect(X(start), y, X(2048) - X(start), 40, "a af", 0)
            f.rect(X(2048), y, X(start + 91) - X(2048), 40, "s fs", 0)
    f.line(X(2048), y - 10, X(2048), y + 50, "a")
    f.text(X(2048), y - 14, "2048", "ta", 10.5, "middle", None, True)
    f.text(X(1100), y + 66, "rows 2000 ... 1984: written, upper case", "ta", 11, "middle", 600)
    f.text(X(3080), y + 66, "rows 1982 ... 1961: still lower case", "t", 11, "middle", 600)
    f.line(X(2048), y + 40, X(2048), y + 84, "a", dash=True)
    f.text(24, y + 108, "row 1983 straddles the tear:", "t", 11.5, None, 600)
    f.text(24, y + 126, "1983|OLD OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOoooooooooooooooooooooooooooooooooooooooooooooo", "t", 10.5, None, None, True)
    f.text(24, y + 156, "PRAGMA integrity_check: ok. Nothing in the file says this page is half one commit, half another.", "t", 11)
    f.text(24, y + 174, "Only a copy of the page from before the commit can put it right: the next lesson's journal.", "tm", 10.5)
    return f


# ------------------------------------------------------------------ 06.02

def commit0602():
    f = Fig("f0602a", "The order of a commit with a rollback journal, and what a crash at each point leaves", 362)
    f.text(24, 22, "journal_commit, top to bottom; middle: the crash points; right: what the next open does", "tm", 11)
    steps = [
        ("copy each original page to the journal", "its magic is still zeroes", ["journal-partial"]),
        ("fsync the journal and its directory", "", []),
        ("write the magic and the count, fsync", "now the journal is hot", ["journal-hot"]),
        ("write the new pages into demo.db", "", ["db-partial", "db-torn"]),
        ("fsync demo.db", "", ["db-written"]),
        ("delete the journal", "the commit point", ["before-delete"]),
    ]
    x = 40
    y0, dy = 54, 40
    f.line(x, y0, x, y0 + 5 * dy, "m")
    for i, (a, b, pts) in enumerate(steps):
        y = y0 + i * dy
        last = i == 5
        f.circle(x, y, 9, "a fa" if last else "s f")
        f.text(x, y + 4, str(i + 1), "t", 10.5, "middle", 700)
        f.text(x + 18, y + 4, a, "ta" if last else "t", 11.5, None, 600 if last else None)
        if b:
            f.text(x + 18, y + 19, b, "ta" if i in (2, 5) else "tm", 10.5)
        for k, pt in enumerate(pts):
            f.text(326, y + 4 + k * 15, pt, "tm", 10.5, None, None, True)
    bands = [(y0 - 14, y0 + dy + 22, "s fs", ["not hot: the next open", "deletes it; demo.db", "was never touched"]),
             (y0 + 2 * dy - 14, y0 + 5 * dy + 24, "a af", ["hot: the next open", "copies the originals", "back (91 pages)"])]
    for y1, y2, cls, lines in bands:
        f.rect(452, y1, 164, y2 - y1, cls, 6)
        for k, l in enumerate(lines):
            f.text(462, y1 + 18 + k * 15, l, "ta" if cls.startswith("a") else "t", 10.5)
    f.rect(452, y0 + 5 * dy + 32, 164, 30, "s f", 6)
    f.text(462, y0 + 5 * dy + 51, "gone: committed", "t", 10.5, None, 600)
    f.text(40, y0 + 5 * dy + 51, "after step 6", "tm", 10.5)
    f.line(24, 312, 616, 312, "m")
    f.text(24, 332, "every crash point above, run on the 2000-row table and then opened by sqlite3: 0 rows changed", "t", 11)
    f.text(24, 348, "(this engine reads a journal from 06.03 on; until then sqlite3 is the next open)", "tm", 10.5)
    return f


def jfile0602():
    f = Fig("f0602b", "The journal file, as the crash left it", 240)
    f.text(24, 22, "demo.db-journal after a crash at db-partial: 373976 bytes = 512 + 91 x (4 + 4096 + 4)", "tm", 11)
    hexrow(f, 24, 34, [
        (168, "d9 d5 05 f9 20 a1 63 d7", "magic", "a af"),
        (84, "00 00 00 5b", "91 records", "s f"),
        (84, "3f b5 44 4e", "nonce", "s f"),
        (84, "00 00 00 5c", "92 pages", "s f"),
        (84, "00 00 02 00", "sector 512", "s fs"),
        (84, "00 00 10 00", "page 4096", "s fs"),
    ], size=10.5)
    f.text(24, 100, "header: offsets 0, 8, 12, 16, 20, 24, then zeroes to byte 512 (one sector)", "tm", 10.5)
    y = 124
    x = hexrow(f, 24, y, [
        (84, "00 00 00 01", "page 1", "a af"),
        (300, "53 51 4c 69 74 65 20 66 ... (4096 bytes)", "its content before the commit", "s f"),
        (78, "4 bytes", "checksum", "s fs"),
    ], size=10.5)
    f.text(x + 10, y + 20, "x 91", "t", 12, None, 600)
    f.text(24, 196, "the 92 is how big the database was before: recovery cuts the file back to it,", "t", 11)
    f.text(24, 212, "so pages a transaction added need no record at all", "t", 11)
    f.text(24, 232, "the checksum is the nonce plus every 200th byte of the page: enough to spot a record cut short", "tm", 10.5)
    return f


# ------------------------------------------------------------------ 06.03

def recover0603():
    f = Fig("f0603a", "What the next open does with a journal", 320)
    f.text(24, 22, "journal_recover, called before anything reads the database", "tm", 11)

    def box(x, y, w, t1, t2="", cls="s f"):
        f.rect(x, y, w, 40 if t2 else 30, cls, 6)
        tc = "ta" if cls.startswith("a") else "t"
        f.text(x + 10, y + 19 if not t2 else y + 17, t1, tc, 11)
        if t2:
            f.text(x + 10, y + 32, t2, "tm", 10.5)
    box(24, 40, 210, "demo.db-journal exists?")
    box(24, 100, 210, "starts with the magic?")
    box(24, 160, 260, "copy each record's page back", "stop at a record cut short", "a af")
    box(24, 222, 260, "cut demo.db to the old page count,", "fsync it", "a af")
    box(24, 284, 260, "delete the journal", "", "a af")
    f.line(129, 70, 129, 98, "s", arrow=True)
    f.line(129, 130, 129, 158, "s", arrow=True)
    f.line(129, 200, 129, 220, "a", arrow=True)
    f.line(129, 262, 129, 282, "a", arrow=True)
    f.text(136, 88, "yes", "tm", 10.5)
    f.text(136, 148, "yes: hot", "ta", 10.5)
    f.line(234, 55, 330, 55, "s", arrow=True)
    f.text(240, 50, "no", "tm", 10.5)
    f.rect(332, 40, 284, 30, "s fs", 6)
    f.text(342, 59, "the last commit finished: nothing to do", "t", 11)
    f.line(234, 115, 330, 115, "s", arrow=True)
    f.text(240, 110, "no", "tm", 10.5)
    f.rect(332, 100, 284, 40, "s fs", 6)
    f.text(342, 117, "it never became hot, so demo.db was", "t", 11)
    f.text(342, 132, "never touched: just delete it", "t", 11)
    f.text(310, 182, "a crash anywhere in the shaded steps leaves", "t", 11)
    f.text(310, 198, "the journal in place, and the next open does", "t", 11)
    f.text(310, 214, "it all again: copying the same originals over", "t", 11)
    f.text(310, 230, "the same pages twice changes nothing", "t", 11)
    return f


def segments0603():
    f = Fig("f0603b", "A journal sqlite3 left: hot segments, one per cache spill", 270)
    f.text(24, 22, "sqlite3 killed inside BEGIN; UPDATE ... with cache_size=10: demo.db-journal, 381488 bytes", "tm", 11)
    total = 381488
    x0, sc = 24, 560 / total
    for k in range(12):
        off = k * 29696
        x = x0 + off * sc
        w = 29696 * sc - 2.5
        f.rect(x, 40, w, 46, "a af", 3)
        f.rect(x, 40, 4, 46, "a fa", 0)
        f.text(x + 4 + (w - 4) / 2, 58, "7", "ta", 10.5, "middle", 600)
        f.text(x + 4 + (w - 4) / 2, 76, f"{4 + 7 * k}-{10 + 7 * k}", "t", 9.5, "middle", None, True)
    x = x0 + 356352 * sc
    f.rect(x, 40, (total - 356352) * sc, 46, "m", 3, dash=True)
    f.text(x + (total - 356352) * sc / 2, 58, "not", "tm", 10.5, "middle")
    f.text(x + (total - 356352) * sc / 2, 76, "hot", "tm", 10.5, "middle")
    for off in (0, 29696, 356352):
        f.text(x0 + off * sc, 102, str(off), "tm", 10, None, None, True)
    f.text(24, 128, "each segment: a header (the magic, its own record count: the 7 above), then 7 records of 4104 bytes,", "t", 11)
    f.text(24, 144, "starting on a 512-byte boundary; sqlite3 makes a segment hot before it writes those pages", "t", 11)
    f.line(24, 162, 616, 162, "m")
    f.text(24, 184, "demo.db at the moment of the kill: pages 4-86 already hold the new rows (1828 of them)", "t", 11.5, None, 600)
    for i in range(92):
        pg = i + 1
        cls = "a fa" if 4 <= pg <= 86 else "s fs"
        f.rect(24 + i * 6.4, 196, 4.8, 22, cls, 1)
    f.text(24, 238, "pages 1-92", "tm", 10.5)
    f.text(616, 238, "recovery: 84 pages restored (the twelve hot segments), 0 rows left changed", "ta", 11, "end", 600)
    return f


def order0603():
    f = Fig("f0603c", "Why the journal is deleted last: a crash during recovery", 236)
    cols = [(24, "as written: copy, then delete", "a af",
             ["copy page 1 back", "SIGKILL (recover-partial)", "next open: the journal is still there", "copies all 91 again: 0 rows changed"]),
            (330, "broken: delete, then copy", "s fs",
             ["delete the journal", "copy page 1 back", "SIGKILL (recover-partial)", "next open: no journal: 1010 rows stay changed"])]
    for x, title, cls, lines in cols:
        f.text(x, 24, title, "ta" if cls.startswith("a") else "t", 12, None, 600)
        for i, l in enumerate(lines):
            y = 40 + i * 44
            crash = "SIGKILL" in l
            last = i == 3
            f.rect(x, y, 286, 34, "a af" if crash else (cls if last else "s f"), 6, dash=crash)
            f.text(x + 10, y + 21, l, "ta" if crash else "t", 11, None, 600 if (last or crash) else None)
            if i < 3:
                f.line(x + 143, y + 34, x + 143, y + 42, "s", arrow=True)
    f.text(24, 228, "recovery has to survive being cut short too: the journal is the only copy of the originals", "tm", 10.5)
    return f


# ------------------------------------------------------------------ 06.04

def twoways0604():
    f = Fig("f0604a", "Two ways to commit: save the old pages, or append the new ones", 280)
    for x, title in ((24, "rollback journal (06.02)"), (336, "write-ahead log")):
        f.text(x, 22, title, "ta" if "log" in title else "t", 12, None, 600)
    # left: journal
    f.rect(24, 40, 130, 120, "s f", 8)
    f.text(34, 58, "demo.db", "t", 11.5, None, 600, True)
    for i, lab in enumerate(("page 4: new", "page 5: new", "page 6: new")):
        f.rect(34, 68 + i * 28, 110, 22, "a af", 4)
        f.text(42, 83 + i * 28, lab, "ta", 10.5)
    f.rect(184, 40, 120, 120, "s fs", 8)
    f.text(194, 58, "-journal", "t", 11.5, None, 600, True)
    for i, lab in enumerate(("page 4: old", "page 5: old", "page 6: old")):
        f.rect(194, 68 + i * 28, 100, 22, "s f", 4)
        f.text(202, 83 + i * 28, lab, "t", 10.5)
    f.text(24, 182, "1 copy the originals aside", "t", 10.5)
    f.text(24, 198, "2 overwrite the pages in place", "t", 10.5)
    f.text(24, 214, "3 delete the journal: committed", "t", 10.5)
    f.text(24, 238, "4 fsyncs per commit", "tm", 10.5)
    # right: wal
    f.rect(336, 40, 120, 120, "s f", 8)
    f.text(346, 58, "demo.db", "t", 11.5, None, 600, True)
    for i, lab in enumerate(("page 4: old", "page 5: old", "page 6: old")):
        f.rect(346, 68 + i * 28, 100, 22, "s f", 4)
        f.text(354, 83 + i * 28, lab, "t", 10.5)
    f.rect(476, 40, 140, 120, "a af", 8)
    f.text(486, 58, "-wal", "ta", 11.5, None, 600, True)
    for i, lab in enumerate(("page 4: new", "page 5: new", "page 6: new, commit")):
        f.rect(486, 68 + i * 28, 120, 22, "a f", 4)
        f.text(494, 83 + i * 28, lab, "ta", 10.5, None, 700 if i == 2 else None)
    f.text(336, 182, "1 append the new pages; the last one", "t", 10.5)
    f.text(336, 198, "  carries the commit mark", "t", 10.5)
    f.text(336, 214, "2 fsync the log: committed", "t", 10.5)
    f.text(336, 238, "readers look in the log first; a checkpoint", "tm", 10.5)
    f.text(336, 254, "copies the pages home later", "tm", 10.5)
    f.line(318, 34, 318, 264, "m")
    return f


def walfile0604():
    f = Fig("f0604b", "The log after a crash in the middle of a checkpoint", 290)
    f.text(24, 22, "demo.db-wal: 20632 bytes = 32 + 5 x (24 + 4096)", "tm", 11)
    hexrow(f, 24, 34, [
        (80, "37 7f 06 83", "magic", "a af"),
        (80, "00 2d e2 18", "3007000", "s f"),
        (80, "00 00 10 00", "page 4096", "s f"),
        (60, "00..00", "ckpt 0", "s fs"),
        (60, "00..01", "salt-1", "s fs"),
        (80, "22 80 94 d4", "salt-2", "s fs"),
        (152, "16 04 e6 d8 df 5e 63 65", "checksum", "s fs"),
    ], size=10)
    f.text(24, 98, "header, 32 bytes. Then each frame: 24 bytes of header, then the page", "tm", 10.5)
    for i in range(5):
        x = 24 + i * 119.2
        last = i == 4
        f.rect(x, 114, 111, 68, "a af" if last else "a f", 6)
        f.text(x + 10, 132, f"frame {i + 1}", "t", 11.5, None, 600)
        f.text(x + 10, 150, f"page: {4 + i}", "t", 10.5, None, None, True)
        f.text(x + 10, 166, f"mark: {92 if last else 0}", "t" if last else "tm", 10.5, None, 600 if last else None, True)
    f.text(24, 204, "a commit mark is the database's size in pages after the commit; only the last frame of a commit has one", "t", 11)
    f.text(24, 220, "salts and checksums chain every frame to the header: a torn or stale frame does not check out", "t", 11)
    f.line(24, 236, 616, 236, "m")
    f.text(24, 256, "demo.db alone: 22 rows changed (page 4 was copied home before the crash)", "t", 11)
    f.text(24, 274, "demo.db with its log: 100 rows changed, the whole commit", "ta", 11, None, 600)
    return f


def chain0604():
    f = Fig("f0604c", "A crash halfway through appending a commit, with the mark in the right place and the wrong one", 272)
    f.text(24, 22, "UPDATE t SET b = 'new' in WAL mode: 90 frames to append (pages 3-92); DB_CRASH=wal-partial after 45", "tm", 11)
    rows = [(48, "as written: the mark goes on the last frame", None, "nothing is marked: the next open uses no frame, 0 rows changed"),
            (156, "broken: the mark on the first frame", 0, "frame 1 (page 3, rows 1961-2000) looks like a whole commit: 40 rows changed")]
    step = 8
    for y, title, marked, outcome in rows:
        f.text(24, y, title, "t", 11.5, None, 600)
        for k in range(45):
            x = 24 + k * step
            cls = "a fa" if marked == k else "a af"
            f.rect(x, y + 10, step - 2, 30, cls, 1)
        xr = 24 + 45 * step + 6
        f.rect(xr, y + 10, 616 - xr, 30, "m", 4, dash=True)
        f.text((xr + 616) / 2, y + 30, "45 frames never written", "tm", 10.5, "middle")
        if marked is not None:
            f.text(24, y + 54, "mark 92", "ta", 10.5, None, 600, True)
        else:
            f.text(24, y + 54, "pages 3 ... 47, marks 0", "tm", 10.5, None, None, True)
        f.text(24, y + 72, outcome, "ta" if marked is not None else "t", 11)
    f.text(24, 262, "a commit mark is a promise that every frame before it is in the log; put first, it promises too soon", "tm", 10.5)
    return f


# ------------------------------------------------------------------ cover and icon

def cover():
    a = Art("m06db", "A commit that a crash cannot cut in half")
    a.text(24, 28, "UPDATE t SET b = 'new': 48 pages to write", "tm", 11)
    for i in range(24):
        a.box(24 + i * 12, 40, 10, 26, "a af", 2)
    for i in range(24, 48):
        a.box(24 + i * 12, 40, 10, 26, "s f", 2)
    a.line(24 + 24 * 12 - 1, 34, 24 + 24 * 12 - 1, 74, "a")
    a.text(24 + 24 * 12 + 4, 88, "crash", "ta", 11, weight=600)
    a.text(24, 88, "without a journal: half new, half old", "t", 11)
    a.box(24, 120, 280, 140, "s fs", 12)
    a.text(40, 144, "rollback journal", "t", 13, weight=600)
    a.text(40, 166, "1 save the old pages aside", "t", 11.5)
    a.text(40, 186, "2 overwrite in place", "t", 11.5)
    a.text(40, 206, "3 delete the journal", "ta", 11.5, weight=600)
    a.text(40, 236, "a crash: copy the old pages back", "tm", 11)
    a.box(336, 120, 280, 140, "a af", 12)
    a.text(352, 144, "write-ahead log", "ta", 13, weight=600)
    a.text(352, 166, "1 append the new pages", "t", 11.5)
    a.text(352, 186, "2 mark the last one: commit", "ta", 11.5, weight=600)
    a.text(352, 206, "3 later, copy them home", "t", 11.5)
    a.text(352, 236, "a crash: ignore an unmarked tail", "tm", 11)
    a.text(320, 288, "either way the file holds all of a commit or none of it", "ta", 12, "middle", 600)
    return a


ICON = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="none" stroke="currentColor" '
        'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="3" y="2.5" width="10" height="13" rx="1.5"/><path d="M5.5 6h5M5.5 9h5M5.5 12h3"/>'
        '<path d="M12.5 13.5l2 2 3.5-4"/></svg>\n')


FIGS = [
    ("06.01-half-commit", half0601), ("06.01-torn-page", torn0601), ("06.01-silent-tear", silent0601),
    ("06.02-commit-order", commit0602), ("06.02-journal-file", jfile0602),
    ("06.03-recovery", recover0603), ("06.03-sqlite-journal", segments0603), ("06.03-delete-last", order0603),
    ("06.04-two-ways", twoways0604), ("06.04-wal-file", walfile0604), ("06.04-mark-last", chain0604),
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
