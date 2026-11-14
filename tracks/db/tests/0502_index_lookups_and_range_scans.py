"""05.02 Index lookups and range scans

Lookups and ranges on an indexed column, and on the rowid, return what
a full scan would - checked against sqlite3 - while reading only a few
pages.
"""


def test(t):
    tr = t.track
    rows = "".join(f"INSERT INTO t VALUES({i}, {i * 7919 % 20011}, 'v{i}', '{i % 13}');\n" for i in range(1, 20001))
    setup = ("CREATE TABLE t(id INTEGER PRIMARY KEY, a INTEGER, b TEXT, s TEXT);\nBEGIN;\n" + rows +
             "INSERT INTO t VALUES(20001, NULL, 'null a', NULL), (20002, 'text', 'text a', 'x'), (20003, 7.5, 'real a', 5);\n"
             "COMMIT;\nCREATE INDEX t_a ON t(a);\nCREATE INDEX t_s ON t(s);\n")
    wheres = ["a = 7919", "a = '7919'", "a = 7.5", "a = 99999", "a > 20000", "a >= 20005", "a < 3",
              "a <= 2", "a BETWEEN 100 AND 140", "a > 30 AND a < 40", "40 > a AND a > 30", "a > 'a'",
              "a < NULL", "a = NULL", "a IS NULL", "a = 7919 AND b = 'v1'", "s = 5", "s = '5'", "s > '9'",
              "id = 77", "id = '77'", "id = 77.5", "id = 77.0", "id > 19990", "id >= 19995 AND id < 19998",
              "id < 3", "id <= 2.5", "id BETWEEN 500 AND 505", "id > 'a'", "id < 'a' AND id < 3",
              "id = 5 AND a = 1", "id > 9e18", "id < -9e18"]
    sql = "".join(f"SELECT id, a, b FROM t WHERE {w} ORDER BY id;\nSELECT '--';\n" for w in wheres)
    tr.both(t, sql, setup)

    f = tr.path(t)
    tr.db(t, f, setup)
    point = tr.stats(tr.db(t, f, "SELECT b FROM t WHERE a = 7919;\n", env={"DB_STATS": "1"}).err)
    rowid = tr.stats(tr.db(t, f, "SELECT b FROM t WHERE id = 12345;\n", env={"DB_STATS": "1"}).err)
    scan = tr.stats(tr.db(t, f, "SELECT b FROM t WHERE b = 'v1';\n", env={"DB_STATS": "1"}).err)
    t.check(point["cache misses"] < 12, f"an index lookup should read a handful of pages, read {point['cache misses']}")
    t.check(rowid["cache misses"] < 8, f"a rowid lookup should read a handful of pages, read {rowid['cache misses']}")
    t.check(scan["cache misses"] > 50, f"a column with no index needs a full scan: {scan['cache misses']} pages")
