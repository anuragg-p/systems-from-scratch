"""06.03 Recovery

Opening a database with a hot journal puts the old pages back: after
our crashes, after a crash during recovery itself, and after sqlite3
was killed in the middle of a transaction that had already written.
"""

import os

DUMP = "SELECT id, a, b FROM t;\n"


def test(t):
    tr = t.track
    rows = "".join(f"INSERT INTO t VALUES({i}, {i % 10}, 'row {i} {'r' * 60}');\n" for i in range(1, 3001))
    setup = "CREATE TABLE t(id INTEGER PRIMARY KEY, a INTEGER, b TEXT);\nBEGIN;\n" + rows + "COMMIT;\n"
    change = "UPDATE t SET b = 'changed', a = a + 1;\n"

    f = tr.path(t)
    tr.db(t, f, setup)
    old = tr.db(t, f, DUMP).out
    tr.crash(t, f, "db-partial", change)
    r = tr.db(t, f, DUMP)
    t.check(r.out == old, "reopening after a crash mid-commit must give the old rows back")
    t.check("rolled back an interrupted transaction" in r.err, f"recovery should say what it did: {r.err!r}")
    t.check(not os.path.exists(f + "-journal"), "the journal must be deleted once rolled back")
    tr.integrity(t, f)

    # A crash during recovery: the journal is still there, still hot; run it again.
    tr.crash(t, f, "db-torn", change)
    tr.crash(t, f, "recover-partial", DUMP)
    t.check(os.path.exists(f + "-journal"), "a crash during recovery must leave the journal for the next try")
    t.check(tr.db(t, f, DUMP).out == old, "recovery must be safe to run twice")
    tr.integrity(t, f)

    # A journal that never became hot: nothing to undo, and nothing said.
    tr.crash(t, f, "journal-partial", change)
    r = tr.db(t, f, DUMP)
    t.check(r.out == old and "rolled back" not in r.err, "a journal that never became hot must be ignored")
    t.check(not os.path.exists(f + "-journal"), "a journal that never became hot must be deleted")

    # sqlite3's own hot journal: a transaction big enough to spill pages into
    # the database file before COMMIT, then sqlite3 killed.
    g = tr.path(t)
    tr.sqlite(t, g, setup)
    with open(g, "rb") as fh:
        before = fh.read()
    tr.kill_sqlite(t, g, "PRAGMA cache_size=10;\nBEGIN;\nUPDATE t SET b = 'spilled ' || b;\n")
    t.check(os.path.exists(g + "-journal"), "killing sqlite3 mid-transaction should leave its journal")
    with open(g, "rb") as fh:
        t.check(fh.read() != before, "the test needs sqlite3 to have written pages before COMMIT (cache spill)")
    r = tr.db(t, g, DUMP)
    t.check(r.out == old, "./db must roll back sqlite3's hot journal")
    t.check("rolled back" in r.err, "./db should report the rollback")
    tr.integrity(t, g)
