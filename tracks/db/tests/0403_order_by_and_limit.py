"""04.03 ORDER BY and LIMIT

Rows sort in SQLite's order (NULL, numbers, text, blobs), on several
keys in either direction, and LIMIT and OFFSET cut the result.
"""

import random


def test(t):
    tr = t.track
    setup = """CREATE TABLE t(id INTEGER PRIMARY KEY, x, n INTEGER, s TEXT);
INSERT INTO t VALUES (1, 3, 1, 'b'), (2, 'abc', 2, 'a'), (3, NULL, 1, 'c'), (4, 2.5, 2, 'b'), (5, x'41', 1, 'a'),
  (6, -1, 3, NULL), (7, 'ABC', 3, 'c'), (8, 3, 2, 'a'), (9, NULL, 1, 'b'), (10, '', 3, 'a');
"""
    q = """SELECT id, x FROM t ORDER BY x, id;
SELECT id, x FROM t ORDER BY x DESC, id;
SELECT id, n, s FROM t ORDER BY n DESC, s, id DESC;
SELECT id, s FROM t ORDER BY s IS NULL, s, id;
SELECT id AS k, n FROM t ORDER BY 2, k DESC;
SELECT id, n * 10 AS big FROM t ORDER BY big, id;
SELECT id, typeof(x) FROM t ORDER BY typeof(x), id;
SELECT id FROM t ORDER BY id LIMIT 3;
SELECT id FROM t ORDER BY id LIMIT 3 OFFSET 2;
SELECT id FROM t ORDER BY id LIMIT 2, 3;
SELECT id FROM t ORDER BY id LIMIT -1 OFFSET 7;
SELECT id FROM t ORDER BY id LIMIT 0;
SELECT id FROM t ORDER BY id DESC LIMIT 4;
SELECT id FROM t WHERE n = 1 ORDER BY s, id LIMIT 2;
SELECT id FROM t LIMIT 3;
"""
    tr.both(t, q, setup)
    rnd = random.Random(403)
    big = "CREATE TABLE b(id INTEGER PRIMARY KEY, v INTEGER, w TEXT);\nBEGIN;\n" + "".join(
        f"INSERT INTO b VALUES({i}, {rnd.randint(-1000, 1000)}, '{rnd.choice('abcdef') * rnd.randint(1, 4)}');\n"
        for i in range(1, 5001)) + "COMMIT;\n"
    tr.both(t, "SELECT v, w, id FROM b ORDER BY w DESC, v, id;\nSELECT id FROM b ORDER BY v, id LIMIT 10 OFFSET 2000;\n", big)
    tr.errors_alike(t, setup, "SELECT id FROM t LIMIT 'x';\n")
