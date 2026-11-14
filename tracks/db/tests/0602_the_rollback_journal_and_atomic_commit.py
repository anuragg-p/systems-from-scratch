"""06.02 The rollback journal and atomic commit

A crash at any point of a commit leaves the old database: the journal
holds every page the commit overwrote, until deleting it commits. The
journal is SQLite's, so sqlite3 itself can roll back ours.
"""

import os
import struct

POINTS = ["journal-partial", "journal-hot", "db-partial", "db-torn", "db-written", "before-delete"]
DUMP = "SELECT id, a, b FROM t;\n"


def fresh(t, tr):
    f = tr.path(t)
    rows = "".join(f"INSERT INTO t VALUES({i}, {i % 10}, 'row {i} {'r' * 50}');\n" for i in range(1, 2001))
    tr.db(t, f, "CREATE TABLE t(id INTEGER PRIMARY KEY, a INTEGER, b TEXT);\nCREATE INDEX t_a ON t(a);\n"
                "BEGIN;\n" + rows + "COMMIT;\n")
    return f


CHANGE = ("BEGIN;\nUPDATE t SET b = 'changed' WHERE id % 3 = 0;\nDELETE FROM t WHERE id % 7 = 0;\n"
          + "".join(f"INSERT INTO t VALUES({i}, 99, 'added {i}');\n" for i in range(5000, 5500)) + "COMMIT;\n")


def test(t):
    tr = t.track
    f = fresh(t, tr)
    old = tr.db(t, f, DUMP).out
    tr.db(t, f, CHANGE)
    new = tr.db(t, f, DUMP).out
    t.check(new != old, "the change should change something")
    t.check(not os.path.exists(f + "-journal"), "a committed transaction must leave no journal")
    tr.integrity(t, f)

    for point in POINTS:
        f = fresh(t, tr)
        tr.crash(t, f, point, CHANGE)
        j = f + "-journal"
        t.check(os.path.exists(j), f"a crash at {point} should leave the journal behind")
        with open(j, "rb") as fh:
            head = fh.read(28)
        hot = head[:8] == bytes.fromhex("d9d505f920a163d7")
        if point == "journal-partial":
            t.check(head[:12] == bytes(12), "until the journal is complete its magic and record count stay zero")
        else:
            t.check(hot and struct.unpack(">I", head[8:12])[0] > 0 and struct.unpack(">I", head[24:28])[0] == 4096,
                    f"after {point} the journal must be hot: magic, a record count, the page size: {head.hex()}")
        got = tr.db(t, f, DUMP).out
        t.check(got == old, f"after a crash at {point}, reopening must give the old database back")
        t.check(not os.path.exists(j), f"after recovering from {point} the journal must be gone")
        tr.integrity(t, f)

    # sqlite3 rolls back a journal ./db left.
    f = fresh(t, tr)
    tr.crash(t, f, "db-partial", CHANGE)
    t.check(tr.sqlite(t, f, DUMP).out == old, "sqlite3 should roll back ./db's hot journal and see the old rows")
    tr.integrity(t, f)
    t.check(not os.path.exists(f + "-journal"), "sqlite3 should delete the journal it rolled back")
