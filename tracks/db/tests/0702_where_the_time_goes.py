"""07.02 Where the time goes

DB_STATS=1 counts what the engine did: a point lookup reads one page
per level of the tree, a rollback-journal commit costs four fsyncs and
a WAL commit one, and a commit journals only the pages it changes.
"""


def test(t):
    tr = t.track
    f = tr.path(t)
    rows = "".join(f"INSERT INTO t VALUES({i}, 'v{i} {'s' * 30}');\n" for i in range(1, 30001))
    tr.db(t, f, "CREATE TABLE t(id INTEGER PRIMARY KEY, b TEXT);\nBEGIN;\n" + rows + "COMMIT;\n")
    depth = tr.tree_depth(f, 2)
    s = tr.stats(tr.db(t, f, "SELECT b FROM t WHERE id = 23456;\n", env={"DB_STATS": "1"}).err)
    # page 1 (the schema) plus one page per level
    t.check(s["cache misses"] == depth + 1, f"a lookup in a {depth}-level tree should read {depth + 1} pages: {s}")

    n = 20
    s = tr.stats(tr.db(t, f, "".join(f"INSERT INTO t VALUES({40000 + i}, 'x');\n" for i in range(n)),
                       env={"DB_STATS": "1"}).err)
    t.check(s["fsyncs"] == 4 * n, f"{n} autocommit inserts with the journal should fsync 4 times each: {s}")
    t.check(2 * n <= s["journal pages"] <= 2 * n + 2,
            f"each such commit journals the leaf it changes and page 1 (and a split, a parent): {s}")

    tr.db(t, f, "PRAGMA journal_mode=wal;\n")
    s = tr.stats(tr.db(t, f, "".join(f"INSERT INTO t VALUES({50000 + i}, 'y');\n" for i in range(n)),
                       env={"DB_STATS": "1"}).err)
    t.check(n <= s["fsyncs"] <= n + 4, f"{n} WAL commits should cost about one fsync each: {s}")
    t.check(s["wal frames"] >= n and s["checkpoints"] == 1, f"the frames, and the checkpoint at close: {s}")
