"""06.04 A write-ahead log

In WAL mode a commit appends pages to file.db-wal and leaves the
database file alone until a checkpoint; a torn or unsynced tail is
ignored, a checkpoint can be interrupted, and sqlite3 reads our log as
we read its.
"""

import os

DUMP = "SELECT id, b FROM t;\n"


def make(t, tr, setup):
    f = tr.path(t)
    tr.db(t, f, setup)
    return f


def test(t):
    tr = t.track
    rows = "".join(f"INSERT INTO t VALUES({i}, 'row {i} {'w' * 40}');\n" for i in range(1, 1501))
    setup = "PRAGMA journal_mode=wal;\nCREATE TABLE t(id INTEGER PRIMARY KEY, b TEXT);\nBEGIN;\n" + rows + "COMMIT;\n"
    change = "BEGIN;\nUPDATE t SET b = 'new' WHERE id % 2 = 0;\nINSERT INTO t VALUES (9999, 'added');\nCOMMIT;\n"

    f = make(t, tr, setup)
    h = tr.header(f)
    t.check((h["write_version"], h["read_version"]) == (2, 2), f"WAL mode is bytes 18 and 19 = 2: {h['raw'][18:20]!r}")
    t.check(not os.path.exists(f + "-wal"), "closing the database checkpoints and deletes the log")
    old = tr.db(t, f, DUMP).out
    tr.integrity(t, f)

    # While the engine is open, commits go to the log, not the database file.
    s = tr.repl(t, f)
    with open(f, "rb") as fh:
        before = fh.read()
    tr.ask(s, "UPDATE t SET b = 'live' WHERE id = 1;")
    t.check(os.path.getsize(f + "-wal") > 4096, "a commit should append frames to the WAL")
    with open(f, "rb") as fh:
        t.check(fh.read() == before, "a WAL commit must not touch the database file")
    t.check(tr.ask(s, "SELECT b FROM t WHERE id = 1;").strip() == "live", "the change is visible at once")
    s.sendline(".exit")
    s.wait_exit()
    t.check(tr.sqlite(t, f, "SELECT b FROM t WHERE id = 1;").out == "live\n", "the checkpoint at close moved it in")

    expect = {"wal-partial": "old", "wal-torn": "old", "wal-written": "new", "checkpoint-partial": "new",
              "checkpoint-done": "new"}
    new = None
    for point, which in expect.items():
        f = make(t, tr, setup)
        tr.crash(t, f, point, change)
        got = tr.db(t, f, DUMP).out
        if new is None and which == "new":
            g = make(t, tr, setup)
            tr.db(t, g, change)
            new = tr.db(t, g, DUMP).out
        t.check(got == (old if which == "old" else new),
                f"after a crash at {point} the database should hold the {which} rows")
        tr.integrity(t, f)

    # sqlite3 reads a log ./db left (the checkpoint never ran).
    f = make(t, tr, setup)
    tr.crash(t, f, "checkpoint-partial", change)
    t.check(os.path.getsize(f + "-wal") > 0, "the log should still be there")
    t.check(tr.sqlite(t, f, DUMP).out == new, "sqlite3 should read the committed frames from ./db's WAL")
    tr.integrity(t, f)

    # ./db reads a log sqlite3 left: sqlite3 killed with frames not checkpointed.
    g = tr.path(t)
    tr.sqlite(t, g, setup)
    tr.kill_sqlite(t, g, "PRAGMA wal_autocheckpoint=0;\n" + change)
    t.check(os.path.getsize(g + "-wal") > 0, "sqlite3 should have left its WAL")
    t.check(tr.db(t, g, DUMP).out == new, "./db should read sqlite3's WAL")
    tr.integrity(t, g)

    # And back to the rollback journal.
    tr.db(t, g, "PRAGMA journal_mode=delete;\n")
    h = tr.header(g)
    t.check((h["write_version"], h["read_version"]) == (1, 1) and not os.path.exists(g + "-wal"),
            "journal_mode=delete must checkpoint, drop the log and set bytes 18 and 19 back to 1")
    t.check(tr.sqlite(t, g, DUMP).out == new, "nothing may be lost switching back")
