"""02.05 Delete and free pages

Random inserts and deletes, checked against an in-memory model with a
fixed seed; emptied pages go to the freelist and are used again; DROP
TABLE frees every page of the table.
"""

import random


def test(t):
    tr = t.track
    rnd = random.Random(205)
    f = tr.path(t)
    tr.db(t, f, "CREATE TABLE t(id INTEGER PRIMARY KEY, a INTEGER, v TEXT);\nCREATE INDEX t_a ON t(a);\n")
    model = {}
    for rnd_round in range(6):
        lines = ["BEGIN;"]
        for _ in range(1500):
            if model and rnd.random() < 0.45:
                k = rnd.choice(list(model))
                del model[k]
                lines.append(f"DELETE FROM t WHERE id = {k};")
            else:
                k = rnd.randint(1, 50_000)
                if k in model:
                    continue
                size = rnd.choice([5, 50, 300, 6000])           # some rows overflow
                model[k] = (rnd.randint(0, 99), "d" * size)
                lines.append(f"INSERT INTO t VALUES({k}, {model[k][0]}, '{model[k][1]}');")
        lines.append("COMMIT;")
        tr.db(t, f, "\n".join(lines) + "\n")
        got = {int(i): (int(a), v) for i, a, v in tr.rows(tr.db(t, f, "SELECT id, a, v FROM t;").out)}
        t.check(got == model, f"round {rnd_round}: the table has {len(got)} rows, the model {len(model)}")
        tr.integrity(t, f)
    for a in (0, 42, 99):
        ids = [int(x) for x in tr.db(t, f, f"SELECT id FROM t WHERE a = {a};").out.split()]
        t.check(sorted(ids) == sorted(k for k, v in model.items() if v[0] == a), f"index lookup a = {a} is wrong")

    # Delete everything: the pages go to the freelist, and come back.
    tr.db(t, f, "DELETE FROM t;\n")
    tr.integrity(t, f)
    pages = int(tr.db(t, f, "PRAGMA page_count;").out)
    free = int(tr.db(t, f, "PRAGMA freelist_count;").out)
    t.check(free > pages // 2, f"after deleting every row, {free} of {pages} pages are free")
    tr.db(t, f, "BEGIN;\n" + "".join(f"INSERT INTO t VALUES({i}, 1, '{'r' * 300}');\n" for i in range(1, 1001)) + "COMMIT;\n")
    t.check(int(tr.db(t, f, "PRAGMA page_count;").out) == pages, "new rows must reuse free pages before the file grows")
    t.check(int(tr.db(t, f, "PRAGMA freelist_count;").out) < free, "inserting should take pages off the freelist")
    tr.integrity(t, f)

    # DROP TABLE hands back the table's pages and its index's.
    before = int(tr.db(t, f, "PRAGMA freelist_count;").out)
    tr.db(t, f, "DROP TABLE t;\n")
    after = int(tr.db(t, f, "PRAGMA freelist_count;").out)
    t.check(after > before and int(tr.db(t, f, "PRAGMA page_count;").out) == pages,
            f"DROP TABLE should free its pages: free {before} -> {after}")
    tr.integrity(t, f)
    t.check(tr.db(t, f, ".tables\n").out.strip() == "", "the table is still listed after DROP TABLE")
