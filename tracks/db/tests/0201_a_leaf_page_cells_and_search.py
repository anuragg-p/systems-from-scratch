"""02.01 A leaf page: cells and search

./db finds rows by rowid in pages sqlite3 wrote: a binary search over
the cells of a leaf, including cells whose payload spills onto overflow
pages.
"""

import random


def test(t):
    tr = t.track
    rnd = random.Random(201)
    keys = rnd.sample(range(1, 10000), 60)
    f = tr.path(t)
    sql = "CREATE TABLE t(id INTEGER PRIMARY KEY, v TEXT);\n" + "".join(
        f"INSERT INTO t VALUES({k}, 'value {k}');\n" for k in keys)
    tr.sqlite(t, f, sql)
    t.check(tr.page_type(f, 2) == 13, "the test wants a table small enough for one leaf page")
    probes = keys[:30] + [k + 1 for k in keys[:10] if k + 1 not in keys] + [0, -5, 10000, 99999]
    q = "".join(f"SELECT id, v FROM t WHERE id = {k};\n" for k in probes)
    want = tr.sqlite(t, f, q).out
    got = tr.db(t, f, q).out
    t.check(got == want, f"lookups by rowid in sqlite3's leaf page disagree:\n./db:\n{got[:600]}\nsqlite3:\n{want[:600]}")
    t.check(len(got.splitlines()) == 30, "every present key must be found, and no absent one")

    # Payloads bigger than a page: the cell keeps the start, overflow pages the rest.
    g = tr.path(t)
    sql = ("CREATE TABLE big(id INTEGER PRIMARY KEY, v TEXT);\n"
           + "".join(f"INSERT INTO big VALUES({i}, '{chr(97 + i) * (2000 * i)}');\n" for i in range(1, 8)))
    tr.sqlite(t, g, sql)
    q = "SELECT id, length(v), v FROM big WHERE id = 7;\nSELECT id, length(v) FROM big;\n"
    t.check(tr.db(t, g, q).out == tr.sqlite(t, g, q).out, "rows with overflow pages read back differently")
