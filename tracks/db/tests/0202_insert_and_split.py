"""02.02 Insert and split

Rows inserted in random order fill a tree of many pages that sqlite3
checks and reads back; full pages split, large payloads overflow.
"""

import random


def test(t):
    tr = t.track
    rnd = random.Random(202)
    keys = rnd.sample(range(1, 1_000_000), 3000)
    model = {}
    lines = ["CREATE TABLE t(id INTEGER PRIMARY KEY, a INTEGER, v TEXT);", "CREATE INDEX t_a ON t(a);", "BEGIN;"]
    for k in keys:
        a = rnd.randint(0, 200)
        v = "v" * rnd.randint(0, 120) + str(k)
        model[k] = (a, v)
        lines.append(f"INSERT INTO t VALUES({k}, {a}, '{v}');")
    lines.append("COMMIT;")
    f = tr.path(t)
    r = tr.db(t, f, "\n".join(lines) + "\n", env={"DB_STATS": "1"})
    t.check(tr.stats(r.err)["splits"] > 20, f"3000 rows must split many pages: {tr.stats(r.err)}")
    tr.integrity(t, f)
    out = tr.sqlite(t, f, "SELECT id, a, v FROM t;").out
    got = {int(i): (int(a), v) for i, a, v in tr.rows(out)}
    t.check(got == model, f"sqlite3 reads {len(got)} rows from ./db's file, not the {len(model)} inserted")

    # Overflow pages: payloads of up to 5 pages each.
    g = tr.path(t)
    sql = "CREATE TABLE big(id INTEGER PRIMARY KEY, v BLOB);\nBEGIN;\n" + "".join(
        f"INSERT INTO big VALUES({i}, x'{format(i % 256, '02x') * (i * 97 % 20000)}');\n" for i in range(1, 120)) + "COMMIT;\n"
    tr.db(t, g, sql)
    tr.integrity(t, g)
    q = "SELECT id, length(v), typeof(v) FROM big;\n"
    t.check(tr.db(t, g, q).out == tr.sqlite(t, g, q).out, "big payloads read back differently")
