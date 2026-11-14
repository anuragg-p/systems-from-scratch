"""05.01 An index is a B-tree

CREATE INDEX builds a B-tree of (columns..., rowid) entries over the
rows already there, and every INSERT, UPDATE and DELETE keeps it in
step: sqlite3's integrity check matches every entry against its row.
"""

import random


def test(t):
    tr = t.track
    rnd = random.Random(501)
    f = tr.path(t)
    rows = "".join(f"INSERT INTO t VALUES({i}, {rnd.randint(0, 300)}, '{rnd.choice(['x', 'y', 'z'])}{i % 17}', "
                   f"{rnd.choice(['NULL', '1.5', repr('t'), '7'])});\n" for i in range(1, 3001))
    setup = "CREATE TABLE t(id INTEGER PRIMARY KEY, a INTEGER, b TEXT, c);\nBEGIN;\n" + rows + "COMMIT;\n"
    tr.db(t, f, setup + "CREATE INDEX t_a ON t(a);\nCREATE INDEX t_bc ON t(b, c);\nCREATE INDEX t_c ON t(c);\n")
    tr.integrity(t, f)
    q = "SELECT type, name, tbl_name, sql FROM sqlite_schema WHERE type = 'index';\n"
    want = ("index|t_a|t|CREATE INDEX t_a ON t(a)\nindex|t_bc|t|CREATE INDEX t_bc ON t(b, c)\n"
            "index|t_c|t|CREATE INDEX t_c ON t(c)\n")
    t.check(tr.db(t, f, q).out == want, "sqlite_schema should list the three indexes as sqlite3 would")

    changes = ["BEGIN;"]
    for i in range(1, 600):
        k = rnd.randint(1, 3500)
        c = rnd.random()
        if c < 0.3:
            changes.append(f"INSERT INTO t VALUES({3000 + i}, {rnd.randint(0, 300)}, 'n{i}', {i});")
        elif c < 0.6:
            changes.append(f"UPDATE t SET a = {rnd.randint(0, 300)}, c = 'u' WHERE id = {k};")
        elif c < 0.7:
            changes.append(f"UPDATE t SET id = {10000 + i} WHERE id = {k};")
        else:
            changes.append(f"DELETE FROM t WHERE id = {k};")
    changes.append("COMMIT;")
    tr.db(t, f, "\n".join(changes) + "\n")
    tr.integrity(t, f)

    # The entries themselves: walking the index gives every row once, in key order.
    got = tr.db(t, f, "SELECT a, id FROM t WHERE a >= 0;\n").out
    want = tr.sqlite(t, f, "SELECT a, id FROM t ORDER BY a, id;\n").out
    t.check(got == want, "walking t_a must give (a, rowid) for every row, in order")

    # An index on a table that is empty, then filled.
    g = tr.path(t)
    tr.db(t, g, "CREATE TABLE e(x, y);\nCREATE INDEX e_y ON e(y);\nBEGIN;\n"
                + "".join(f"INSERT INTO e VALUES({i}, {i * 37 % 101});\n" for i in range(2000)) + "COMMIT;\n")
    tr.integrity(t, g)
    tr.errors_alike(t, "CREATE TABLE e(x);\nCREATE INDEX e_x ON e(x);\n", "CREATE INDEX e_x ON e(x);\n")
    tr.errors_alike(t, "CREATE TABLE e(x);\n", "CREATE INDEX e_q ON e(nope);\n")
