"""07.03 One more optimisation, measured

Rows inserted in rowid order split pages at the end, leaving every old
page full: the file comes out about the size of sqlite3's, where an even
split would leave it nearly twice as big. Random order is not an append.
"""

import os


def test(t):
    tr = t.track
    rows = "".join(f"INSERT INTO t VALUES({i}, 'row {i:06d} {'p' * 30}');\n" for i in range(1, 20001))
    sql = "CREATE TABLE t(id INTEGER PRIMARY KEY, b TEXT);\nBEGIN;\n" + rows + "COMMIT;\n"
    ours, theirs = tr.path(t), tr.path(t)
    r = tr.db(t, ours, sql, env={"DB_STATS": "1"})
    tr.sqlite(t, theirs, sql)
    s = tr.stats(r.err)
    t.check(s["append splits"] > 0 and s["append splits"] >= s["splits"] * 0.9,
            f"inserting in rowid order, nearly every split should be an append split: {s}")
    a, b = os.path.getsize(ours), os.path.getsize(theirs)
    t.check(a <= b * 1.1, f"./db's file is {a} bytes, sqlite3's {b}: appends should fill pages as sqlite3 does")
    tr.integrity(t, ours)

    shuffled = rows.splitlines()
    shuffled = shuffled[1::2] + shuffled[0::2]           # two passes: not in order
    r = tr.db(t, tr.path(t), "CREATE TABLE t(id INTEGER PRIMARY KEY, b TEXT);\nBEGIN;\n" + "\n".join(shuffled)
              + "\nCOMMIT;\n", env={"DB_STATS": "1"})
    s = tr.stats(r.err)
    t.check(s["splits"] > 0 and s["append splits"] < s["splits"] / 2,
            f"inserting out of order, most splits are not appends: {s}")
