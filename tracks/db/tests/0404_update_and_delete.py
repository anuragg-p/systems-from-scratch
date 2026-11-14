"""04.04 UPDATE and DELETE

UPDATE and DELETE change exactly the rows WHERE picks, even when the
change moves rows in the B-tree being searched; a failing statement
inside BEGIN undoes only itself.
"""

import random


def test(t):
    tr = t.track
    setup = ("CREATE TABLE t(id INTEGER PRIMARY KEY, a INTEGER, b TEXT NOT NULL DEFAULT 'b');\n"
             "BEGIN;\n" + "".join(f"INSERT INTO t VALUES({i}, {i % 7}, 'row {i}');\n" for i in range(1, 501)) + "COMMIT;\n")
    sql = """UPDATE t SET a = a + 100 WHERE a = 3;
UPDATE t SET b = b || '!' WHERE id BETWEEN 10 AND 20;
UPDATE t SET a = NULL, b = 'nulled' WHERE id % 50 = 0;
DELETE FROM t WHERE a = 5;
DELETE FROM t WHERE id > 480;
UPDATE t SET id = id + 1000 WHERE id < 30;
UPDATE t SET id = id + 5000;
UPDATE t SET a = '42' WHERE id = 6012;
SELECT id, a, b FROM t;
DELETE FROM t WHERE b LIKE '%!';
SELECT id, a, typeof(a), b FROM t;
"""
    tr.both(t, sql, setup)
    base = setup + "UPDATE t SET a = 0;\n"
    for bad in ["UPDATE t SET id = 2 WHERE id = 1;", "UPDATE t SET b = NULL WHERE id = 3;",
                "UPDATE t SET nope = 1;", "UPDATE nosuch SET a = 1;", "DELETE FROM nosuch;",
                "UPDATE t SET id = 'x' WHERE id = 4;"]:
        tr.errors_alike(t, base, bad + "\n")

    # Inside BEGIN, a failing statement is undone alone; the rest commits.
    script = ("BEGIN;\nUPDATE t SET a = 1 WHERE id <= 10;\nUPDATE t SET id = id + 1 WHERE id >= 499;\n"
              "UPDATE t SET b = 'kept' WHERE id = 5;\nCOMMIT;\nSELECT id, a, b FROM t WHERE id <= 10 OR id >= 498;\n")
    ours, theirs = tr.path(t), tr.path(t)
    tr.db(t, ours, setup)
    tr.sqlite(t, theirs, setup)
    a = tr.db(t, ours, script, check=False)
    b = tr.sqlite(t, theirs, script, check=False)
    t.check("UNIQUE constraint failed" in a.err, f"the second UPDATE must fail on a duplicate id:\n{a}")
    t.check(a.out == b.out, f"after a failed statement in BEGIN, ./db kept:\n{a.out}\nsqlite3 kept:\n{b.out}")
    tr.integrity(t, ours)

    # A random mix, against sqlite3 running the same statements.
    rnd = random.Random(404)
    mix = []
    for _ in range(300):
        k = rnd.randint(1, 600)
        c = rnd.random()
        if c < 0.4:
            mix.append(f"UPDATE t SET a = {rnd.randint(0, 9)}, b = 'm{k}' WHERE id = {k};")
        elif c < 0.7:
            mix.append(f"DELETE FROM t WHERE id = {k};")
        elif c < 0.9:
            mix.append(f"DELETE FROM t WHERE a = {rnd.randint(0, 9)} AND id > {k};")
        else:
            mix.append(f"UPDATE t SET b = b || 'x' WHERE a = {rnd.randint(0, 9)};")
    tr.both(t, "BEGIN;\n" + "\n".join(mix) + "\nCOMMIT;\nSELECT id, a, b FROM t;\n", setup)
