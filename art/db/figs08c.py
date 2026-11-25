"""Figures for db module 08, More SQL: lessons 08.06-08.07 (08.06's are still to come).

    python3 art/db/figs08c.py                 writes tracks/db/lessons/08-more-sql/figures/08.0[67]-*.svg
    python3 art/db/figs08c.py --dump FILE N   prints the cells of page N of a database file

Every byte and number below comes from files written by the engine as it stands at 08.07
(`./learn run db --at 08.07 -- <file> "<sql>"`, i.e. build/at/db/08.07/db) and dumped with
--dump (the page header, the cell pointer array, each cell's bytes), checked against sqlite3
3.54.1 (/opt/homebrew/opt/sqlite/bin/sqlite3):

  users.db  CREATE TABLE users(id INTEGER PRIMARY KEY, email TEXT UNIQUE, name TEXT);
            INSERT INTO users VALUES (1, 'ada@x.io', 'Ada'), (2, 'brook@x.io', 'Brook'),
                                     (3, 'chen@x.io', 'Chen');
            SELECT type, name, tbl_name, rootpage, typeof(sql), sql FROM sqlite_schema:
              table|users|users|2|text|CREATE TABLE users(id INTEGER PRIMARY KEY, email TEXT UNIQUE, name TEXT)
              index|sqlite_autoindex_users_1|users|3|null|
            page 1, cell 1 (the index's row, 43 bytes):
              29 02 06 17 3d 17 01 00 'index' 'sqlite_autoindex_users_1' 'users' 03
            page 3 (index leaf, 3 cells): 0b 03 1d 09 'ada@x.io' (rowid 1 is serial type 9,
              no byte); 0e 03 21 01 'brook@x.io' 02; 0d 03 1f 01 'chen@x.io' 03
            page 2 (table leaf): rows 1-3, id stored as NULL (serial type 00).
            Then, one statement per run:
              INSERT INTO users VALUES (4, 'dee@x.io', 'Dee');   no error; DB_STATS=1: pages
                written 3 (pages 1, 2 and 3 differ from the file before: cmp -l); page 3 gains
                0c 03 1d 01 'dee@x.io' 04 after chen's entry
              INSERT INTO users VALUES (5, 'ada@x.io', 'Eve');   Error: UNIQUE constraint
                failed: users.email; DB_STATS=1: pages written 0; the file is byte for byte
                what it was (cmp)
            sqlite3 gives the same error for the same two statements and integrity_check is ok.
  plain.db  the same table with email TEXT (no UNIQUE), CREATE INDEX users_email ON users(email),
            the same three rows: users_email is at page 3, and its page 3 is byte for byte
            users.db's page 3 (before Dee). Pages 2 and 3 of both files are byte for byte the
            pages sqlite3 3.54.1 writes for the same statements; page 1 holds the same cells
            (sqlite3 places them in another order on the page).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import figlib  # noqa: E402
from figlib import Fig, tw  # noqa: E402

figlib.LESSONS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                              "tracks", "db", "lessons")
MOD = "08-more-sql"

# The index leaf (page 3 of users.db) after the first INSERT: (email, rowid), in key order.
ENTRIES = [("ada@x.io", 1), ("brook@x.io", 2), ("chen@x.io", 3), ("dee@x.io", 4)]


def cells(f, x, y, items, h=22, size=11):
    """items: (width, text, cls). Cells left to right with no gap; cls "null" is a NULL:
    an empty dashed cell with the word in muted text. Returns the x after the last cell."""
    for w, text, cls in items:
        if cls == "null":
            f.rect(x, y, w, h, "m f", 0, dash=True)
            f.text(x + w / 2, y + h / 2 + size * 0.36, "NULL", "tm", size - 1, "middle", None, True)
        else:
            f.rect(x, y, w, h, cls, 0)
            tcls = "ta" if cls.startswith("a") else ("tm" if cls.startswith("m") else "t")
            f.text(x + w / 2, y + h / 2 + size * 0.36, text, tcls, size, "middle", None, True)
        x += w
    return x


def byte_row(f, x, y, items, h=30, subs=True):
    """items: (width, text, sub, cls), as in figs05: boxes left to right, a label under each
    (above each when subs is "above", none when False). Returns the x of each box's left edge,
    and the x after the last."""
    xs = []
    for w, text, sub, cls in items:
        f.rect(x, y, w, h, cls, 0)
        tcls = "ta" if cls.startswith("a") else "t"
        f.text(x + w / 2, y + h / 2 + 4, text, tcls, 11.5, "middle", None, True)
        if sub and subs:
            f.text(x + w / 2, y - 8 if subs == "above" else y + h + 14, sub, "tm", 10.5, "middle")
        xs.append(x)
        x += w
    xs.append(x)
    return xs


def step(f, x, y, n, label, cls="t"):
    """A numbered step heading: a small circle with n, then the label."""
    f.circle(x + 9, y - 4, 9, "a af" if cls == "ta" else "s fs")
    f.text(x + 9, y, str(n), "t", 10.5, "middle", 700)
    f.text(x + 24, y, label, cls, 11.5, None, 600)


# ------------------------------------------------------------------ 08.06
# (08.06's figures go here: one function each, and a line each in FIGS below.)


# ------------------------------------------------------------------ 08.07

def index_leaf(f, x, y, entries, hot=None, h=None):
    """users.db's index leaf, page 3, as a box of (email, rowid) entries. hot: the index of an
    entry to ring. Returns (the y of each entry's top, the box's bottom)."""
    h = h or 40 + 24 * len(entries)
    f.rect(x, y, 240, h, "a af", 6)
    f.text(x + 12, y + 18, "page 3: sqlite_autoindex_users_1", "ta", 10.5, None, 600, True)
    tops = []
    for i, (email, rid) in enumerate(entries):
        ey = y + 28 + 24 * i
        cells(f, x + 12, ey, [(104, email, "a f"), (28, str(rid), "a f")], h=20, size=11)
        if i == hot:
            f.rect(x + 8, ey - 4, 140, 28, "a", 4)
        tops.append(ey)
    return tops, y + h


def check0807():
    f = Fig("f0807a", "Two INSERTs into users: a lookup in the unique index comes before any write", 478)

    # a new email
    f.text(24, 22, "INSERT INTO users VALUES (4, 'dee@x.io', 'Dee');", "t", 11.5, None, 600, True)
    f.text(616, 22, "a new email", "tm", 11, "end")
    step(f, 24, 50, 1, "look up 'dee@x.io'", "ta")
    step(f, 300, 50, 2, "nothing equal: write both B-trees")
    tops, bot = index_leaf(f, 24, 62, ENTRIES[:3])
    gap = tops[-1] + 26
    f.line(36, gap, 168, gap, "a", dash=True)
    f.rect(196, gap - 10, 60, 20, "a f", 4)
    f.text(226, gap + 4, "dee@x.io", "ta", 10.5, "middle", None, True)
    f.line(194, gap, 172, gap, "a", arrow=True)
    f.text(24, bot + 18, "the seek lands past chen@x.io: no entry equals it", "tm", 10.5)
    # the two writes
    f.rect(300, 62, 316, 52, "s f", 6)
    f.text(312, 80, "page 2: table users", "t", 10.5, None, 600, True)
    f.text(312, 102, "+ row", "t", 11)
    cells(f, 360, 88, [(28, "4", "s f"), (104, "dee@x.io", "s f"), (40, "Dee", "s f")], h=20)
    f.rect(300, 124, 316, 52, "a af", 6)
    f.text(312, 142, "page 3: sqlite_autoindex_users_1", "ta", 10.5, None, 600, True)
    f.text(312, 164, "+ entry", "ta", 11)
    cells(f, 360, 150, [(104, "dee@x.io", "a f"), (28, "4", "a f")], h=20)
    f.path("M266 118 C 282 118, 280 88, 296 88", "s", arrow=True)
    f.path("M266 118 C 282 118, 280 150, 296 150", "a", arrow=True)
    f.text(312, 196, "the row, then its entry; pages written: 3 (and page 1's header)", "tm", 10.5)

    f.line(24, 222, 616, 222, "m")

    # an email already there
    y0 = 222
    f.text(24, y0 + 26, "INSERT INTO users VALUES (5, 'ada@x.io', 'Eve');", "t", 11.5, None, 600, True)
    f.text(616, y0 + 26, "an email already there", "tm", 11, "end")
    step(f, 24, y0 + 54, 1, "look up 'ada@x.io'", "ta")
    step(f, 300, y0 + 54, 2, "an equal entry: write nothing")
    tops, bot = index_leaf(f, 24, y0 + 66, ENTRIES, hot=0)
    hit = tops[0] + 10
    f.rect(196, hit - 10, 60, 20, "a f", 4)
    f.text(226, hit + 4, "ada@x.io", "ta", 10.5, "middle", None, True)
    f.line(194, hit, 174, hit, "a", arrow=True)
    f.text(24, bot + 18, "it lands on ('ada@x.io', 1): rowid 1, not this row's 5", "tm", 10.5)
    f.rect(300, y0 + 66, 316, 36, "m f", 6, dash=True)
    f.text(312, y0 + 88, "page 2: table users", "tm", 10.5, None, 600, True)
    f.text(604, y0 + 88, "unchanged", "tm", 10.5, "end")
    f.rect(300, y0 + 112, 316, 36, "m f", 6, dash=True)
    f.text(312, y0 + 134, "page 3: the index", "tm", 10.5, None, 600, True)
    f.text(604, y0 + 134, "unchanged", "tm", 10.5, "end")
    f.rect(300, y0 + 162, 316, 32, "s fs", 6)
    f.text(458, y0 + 182, "Error: UNIQUE constraint failed: users.email", "t", 10.5, "middle", None, True)
    f.text(312, y0 + 214, "pages written: 0; the file is byte for byte as it was", "tm", 10.5)

    f.line(24, 452, 616, 452, "m")
    f.text(24, 470, "Before either lookup the table is asked whether the rowid is free (04.01's check): 4 and 5 are.", "tm", 10.5)
    return f


def schema0807():
    f = Fig("f0807b", "sqlite_schema for users: the table's row, and its automatic index's row with no sql", 378)
    f.text(24, 22, "page 1 of users.db: the two rows of sqlite_schema, as ./db wrote them (sqlite3 reads the same)", "tm", 11)
    sql = ["CREATE TABLE users(id INTEGER", "PRIMARY KEY, email TEXT", "UNIQUE, name TEXT)"]
    cards = [(24, "row 1", "table", "users", "2", "page 2: the table's B-tree", sql, "s"),
             (328, "row 2", "index", "sqlite_autoindex_users_1", "3", "page 3: the index's B-tree", None, "a")]
    for x, rid, typ, name, root, page, sqltext, tone in cards:
        f.rect(x, 36, 288, 204, "s f", 8)
        f.text(x + 12, 56, rid, "t", 11.5, None, 700)
        fields = [("type", typ), ("name", name), ("tbl_name", "users"), ("rootpage", root)]
        for i, (k, v) in enumerate(fields):
            y = 68 + 26 * i
            f.text(x + 12, y + 15, k, "tm", 10.5, None, None, True)
            if k == "rootpage":
                cells(f, x + 76, y, [(28, v, "a af")], h=20)
                f.line(x + 108, y + 10, x + 130, y + 10, "a", arrow=True)
                f.text(x + 136, y + 14, page, "ta" if tone == "a" else "t", 10.5)
            else:
                cells(f, x + 76, y, [(max(36, tw(v, 11, True) + 16), v, "s f")], h=20)
        y = 68 + 26 * 4
        f.text(x + 12, y + 15, "sql", "tm", 10.5, None, None, True)
        if sqltext:
            f.rect(x + 76, y, 200, 16 * len(sqltext) + 8, "s f", 0)
            for k, line in enumerate(sqltext):
                f.text(x + 84, y + 15 + 16 * k, line, "t", 10.5, None, None, True)
        else:
            cells(f, x + 76, y, [(60, "", "null")], h=20)
            f.text(x + 148, y + 15, "no CREATE text", "tm", 10.5)

    # the index row's record, from the dump of page 1
    f.text(24, 266, "row 2 as stored: its record header ends in serial type 00, a NULL, which takes no bytes", "tm", 11)
    xs = byte_row(f, 24, 276, [
        (34, "29", "size", "s f"), (34, "02", "rowid", "s f"), (34, "06", "hdr", "s fs"),
        (34, "17", "type", "s fs"), (34, "3d", "name", "s fs"), (34, "17", "tbl", "s fs"),
        (34, "01", "root", "s fs"), (34, "00", "sql", "a af"),
        (50, "index", "", "s f"), (184, "sqlite_autoindex_users_1", "", "s f"), (50, "users", "", "s f"),
        (32, "03", "", "a af"),
    ])
    f.text((xs[8] + xs[12]) / 2, 320, "the values: type, name, tbl_name, rootpage; nothing for sql", "tm", 10.5, "middle")
    f.line(24, 334, 616, 334, "m")
    f.text(24, 354, "id INTEGER PRIMARY KEY makes no index (it is the rowid), so email's UNIQUE is the table's index _1.", "t", 11)
    f.text(24, 371, "At every open the CREATE text is parsed again, its UNIQUE named _1 again, and that name finds this row.",
           "tm", 10.5)
    return f


def entry0807():
    f = Fig("f0807c", "An entry of the unique index and of an ordinary index on the same column: the same bytes", 262)
    f.text(24, 22, "row 3 of users, (3, 'chen@x.io', 'Chen'): its entry in each index, leaf page 3, cell 2, 14 bytes", "tm", 11)
    chars = "chen@x.io"
    items = [(40, "0d", "size 13", "s f"), (34, "03", "hdr", "s fs"), (34, "1f", "email", "s fs"),
             (34, "01", "rowid", "s fs")]
    items += [(24, f"{ord(c):02x}", "", "a af") for c in chars]
    items += [(40, "03", "rowid 3", "a af")]
    x0 = 616 - sum(w for w, _, _, _ in items)
    rows = [(58, "UNIQUE", "ta", "sqlite_autoindex_users_1", "users.db"),
            (120, "ordinary", "t", "users_email", "plain.db")]
    for k, (y, role, rcls, name, where) in enumerate(rows):
        f.text(24, y + 12, role, rcls, 12, None, 700)
        f.text(24, y + 28, name, "tm", 10.5, None, None, True)
        f.text(24, y + 43, where, "tm", 10.5)
        xs = byte_row(f, x0, y, items, subs="above" if k == 0 else False)
    f.text((xs[4] + xs[13]) / 2, 50, "'chen@x.io', 9 bytes", "tm", 10.5, "middle")
    # the same bytes: an = under each box of the first row
    for i in range(len(items)):
        f.text((xs[i] + xs[i + 1]) / 2, 109, "=", "tm", 12, "middle", 600)
    f.brace_h(xs[4], xs[13], 166, "a")
    f.brace_h(xs[13], xs[14], 166, "a")
    f.text((xs[4] + xs[13]) / 2, 184, "the key: the email", "ta", 11, "middle", 600)
    f.text(xs[14], 184, "then the rowid", "ta", 11, "end", 600)
    f.line(24, 202, 616, 202, "m")
    f.text(24, 222, "Nothing in an entry, or in its page, says unique: page 3 is the same in both files, as sqlite3 writes it.", "t", 11)
    f.text(24, 240, "Unique is a check made before each write. The files differ only on page 1, in sqlite_schema: the CREATE", "tm", 10.5)
    f.text(24, 255, "TABLE text, and the index's row (its name, and NULL here where users_email's row has its CREATE INDEX).", "tm", 10.5)
    return f


FIGS = [
    ("08.07-check", check0807), ("08.07-schema", schema0807), ("08.07-entry", entry0807),
]


# ------------------------------------------------------------------ the dump the numbers came from

def varint(b, i):
    """The varint at b[i]: (value, index after it)."""
    v = 0
    for k in range(9):
        c = b[i + k]
        if k == 8:
            return (v << 8) | c, i + 9
        v = (v << 7) | (c & 0x7f)
        if c < 0x80:
            return v, i + k + 1


def dump(path, n):
    """Prints page n of the database file at path: its type, cell count, and each leaf cell's bytes."""
    with open(path, "rb") as fh:
        data = fh.read()
    p = data[(n - 1) * 4096:n * 4096]
    h = 100 if n == 1 else 0
    kind, ncell = p[h], int.from_bytes(p[h + 3:h + 5], "big")
    hl = 8 if kind in (0x0a, 0x0d) else 12
    print(f"page {n}: type 0x{kind:02x}, {ncell} cells, content at {int.from_bytes(p[h + 5:h + 7], 'big')}")
    for c in range(ncell):
        off = int.from_bytes(p[h + hl + 2 * c:h + hl + 2 * c + 2], "big")
        size, i = varint(p, off)
        if kind == 0x0d:
            _, i = varint(p, i)
        print(f"  cell {c} at {off}: " + " ".join(f"{b:02x}" for b in p[off:i + size]))


def main():
    if sys.argv[1:2] == ["--dump"]:
        return dump(sys.argv[2], int(sys.argv[3]))
    for name, fn in FIGS:
        print(figlib.write(MOD, name, fn()))


if __name__ == "__main__":
    main()
