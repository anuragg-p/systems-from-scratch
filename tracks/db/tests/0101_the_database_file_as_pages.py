"""01.01 The database file as pages

The file is whole pages; page 1 starts with the 100-byte header in
SQLite's format; and the engine reads files sqlite3 made with any page
size, and makes files sqlite3 accepts.
"""

import os


def test(t):
    tr = t.track
    f = tr.path(t)
    tr.db(t, f, "CREATE TABLE a(x INTEGER PRIMARY KEY, y TEXT);\nINSERT INTO a(y) VALUES ('one'), ('two');\n"
                "CREATE TABLE b(z);\n")
    size = os.path.getsize(f)
    h = tr.header(f)
    t.check(h["magic"] == b"SQLite format 3\0", f"the file must start with 'SQLite format 3\\0', not {h['magic']!r}")
    t.check(h["page_size"] == 4096 and size % 4096 == 0, f"page size {h['page_size']}, file size {size}")
    t.check((h["write_version"], h["read_version"], h["reserved"]) == (1, 1, 0),
            f"versions/reserved bytes 18-20: {h['raw'][18:21]!r}")
    t.check(h["fractions"] == (64, 32, 32), f"payload fractions (bytes 21-23) must be 64, 32, 32: {h['fractions']}")
    t.check(h["schema_format"] == 4 and h["encoding"] == 1, f"schema format {h['schema_format']}, encoding {h['encoding']}")
    t.check(h["page_count"] == size // 4096, f"header says {h['page_count']} pages, the file has {size // 4096}")
    t.check(h["valid_for"] == h["change_counter"] > 0,
            f"version-valid-for ({h['valid_for']}) must equal the change counter ({h['change_counter']})")
    t.check(tr.page_type(f, 1) == 13, "page 1 must hold the sqlite_schema table leaf after the header")
    for root in (2, 3):
        t.check(tr.page_type(f, root) == 13, f"page {root} should be a table's root (a table leaf, type 13)")
    tr.integrity(t, f)
    out = tr.sqlite(t, f, "SELECT y FROM a ORDER BY x;").out
    t.check(out == "one\ntwo\n", f"sqlite3 read {out!r}")

    # Files made by sqlite3, with page sizes other than ours.
    rows = "".join(f"INSERT INTO t VALUES({i}, '{'v' * (i % 300)}');\n" for i in range(1, 401))
    for ps in (512, 1024, 8192, 65536):
        g = tr.path(t)
        tr.sqlite(t, g, f"PRAGMA page_size={ps};\nCREATE TABLE t(id INTEGER PRIMARY KEY, v TEXT);\nBEGIN;\n{rows}COMMIT;\n")
        t.check(tr.header(g)["page_size"] == ps, f"sqlite3 did not make a {ps}-byte page file")
        want = tr.sqlite(t, g, "SELECT id, v FROM t;").out
        got = tr.db(t, g, "SELECT id, v FROM t;").out
        t.check(got == want, f"reading sqlite3's {ps}-byte pages gave different rows")
        tr.db(t, g, "INSERT INTO t VALUES(1000, 'written by db');")
        tr.integrity(t, g)
        t.check(tr.sqlite(t, g, "SELECT v FROM t WHERE id = 1000;").out == "written by db\n",
                f"sqlite3 cannot see a row ./db wrote into a {ps}-byte page file")

    # A page size of our own choosing, set before the first write.
    g = tr.path(t)
    tr.db(t, g, "PRAGMA page_size=8192;\nCREATE TABLE t(v);\nINSERT INTO t VALUES ('big pages');\n")
    t.check(tr.header(g)["page_size"] == 8192 and os.path.getsize(g) % 8192 == 0, "PRAGMA page_size=8192 ignored")
    tr.integrity(t, g)
