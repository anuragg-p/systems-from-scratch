"""02.04 Cursors and range scans

A cursor walks a tree's leaves in key order: full scans come out in
rowid order, ranges cross leaf boundaries, and an index (whose interior
cells are entries too) is walked in key order.
"""

import random


def test(t):
    tr = t.track
    rnd = random.Random(204)
    keys = rnd.sample(range(1, 200_000), 5000)
    f = tr.path(t)
    sql = ["CREATE TABLE t(id INTEGER PRIMARY KEY, a INTEGER, v TEXT);", "BEGIN;"]
    sql += [f"INSERT INTO t VALUES({k}, {rnd.randint(-50, 50)}, 'v{k}');" for k in keys]
    sql.append("COMMIT;")
    tr.db(t, f, "\n".join(sql) + "\n")

    ids = [int(x) for x in tr.db(t, f, "SELECT id FROM t;").out.split()]
    t.check(ids == sorted(keys), "a full scan must return every row, in rowid order")
    ranges = [(1, 50), (1000, 9000), (150_000, 300_000), (-10, 0), (77_777, 77_777)]
    q = "".join(f"SELECT id, v FROM t WHERE id BETWEEN {a} AND {b};\n" for a, b in ranges)
    t.check(tr.db(t, f, q).out == tr.sqlite(t, f, q).out, "range scans disagree with sqlite3")

    # An index built by sqlite3, walked in key order by ./db.
    g = tr.path(t)
    tr.sqlite(t, g, "\n".join(sql) + "\nCREATE INDEX t_a ON t(a, v);\n")
    t.check(tr.tree_depth(g, int(tr.sqlite(t, g, "SELECT rootpage FROM sqlite_schema WHERE name='t_a';").out)) >= 2,
            "the index should be more than one page, so interior entries matter")
    got = tr.db(t, g, "SELECT a, id FROM t WHERE a >= -50;").out
    want = tr.sqlite(t, g, "SELECT a, id FROM t ORDER BY a, v;").out
    t.check(got == want, "walking sqlite3's index must give its entries in key order")
