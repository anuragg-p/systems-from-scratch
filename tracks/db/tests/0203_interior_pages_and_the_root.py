"""02.03 Interior pages and the root

The tree grows from the root down: the root page keeps its number while
the table becomes three levels deep, and even page 1 (sqlite_schema,
behind the file header) grows into an interior page.
"""

import random


def test(t):
    tr = t.track
    rnd = random.Random(203)
    keys = rnd.sample(range(1, 10_000_000), 4000)
    f = tr.path(t)
    sql = ["CREATE TABLE t(id INTEGER PRIMARY KEY, v TEXT);", "BEGIN;"]
    sql += [f"INSERT INTO t VALUES({k}, '{'z' * 400}{k}');" for k in keys]
    sql.append("COMMIT;")
    tr.db(t, f, "\n".join(sql) + "\n")
    root = int(tr.sqlite(t, f, "SELECT rootpage FROM sqlite_schema WHERE name = 't';").out)
    t.check(root == 2, f"the table's root page moved: sqlite_schema says {root}")
    depth = tr.tree_depth(f, root)
    t.check(depth >= 3, f"4000 rows of 400 bytes should make a tree 3 levels deep, not {depth}")
    tr.integrity(t, f)
    probe = rnd.sample(keys, 200) + [1, 2, 3]
    q = "".join(f"SELECT id, length(v) FROM t WHERE id = {k};\n" for k in probe)
    got = tr.db(t, f, q).out
    t.check(got == tr.sqlite(t, f, q).out, "lookups through interior pages disagree with sqlite3")
    t.check(len(got.splitlines()) == 200, "every inserted key must be found through the interior pages")

    # Page 1 holds sqlite_schema; enough tables make it split like any root.
    g = tr.path(t)
    names = [f"table_with_a_rather_long_name_number_{i:03d}" for i in range(150)]
    tr.db(t, g, "".join(f"CREATE TABLE {n}(id INTEGER PRIMARY KEY, some_column TEXT, another_column REAL);\n"
                        for n in names))
    t.check(tr.page_type(g, 1) == 5, "150 schema rows should turn page 1 into an interior page (type 5)")
    tr.integrity(t, g)
    tables = tr.db(t, g, ".tables\n").out.split()
    t.check(tables == names, f".tables lists {len(tables)} of the 150 tables")
    tr.db(t, g, f"INSERT INTO {names[149]} VALUES (1, 'last', 1.5);\n")
    t.check(tr.sqlite(t, g, f"SELECT * FROM {names[149]};").out == "1|last|1.5\n", "sqlite3 cannot read the last table")
