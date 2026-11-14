"""06.01 What a crash does to a half-written page

With no journal (journal_mode=OFF), a crash in the middle of writing a
commit leaves half of it in the file: some rows changed, others not.
DB_CRASH=<point> is how every later test crashes the engine on purpose.
"""


def test(t):
    tr = t.track
    f = tr.path(t)
    rows = "".join(f"INSERT INTO t VALUES({i}, 'old {'o' * 80}');\n" for i in range(1, 2001))
    tr.db(t, f, "CREATE TABLE t(id INTEGER PRIMARY KEY, b TEXT);\nBEGIN;\n" + rows + "COMMIT;\n")
    leaves = int(tr.db(t, f, "PRAGMA page_count;").out)
    t.check(leaves > 20, "the table should span many pages")

    r = tr.crash(t, f, "db-partial", "PRAGMA journal_mode=off;\nUPDATE t SET b = 'new';\n")
    t.check(not r.out.strip() or r.out.strip() == "off", f"output before the crash: {r.out!r}")
    new = int(tr.db(t, f, "SELECT id FROM t WHERE b = 'new';\n").out.count("\n"))
    t.check(0 < new < 2000,
            f"with no journal, a crash halfway through writing must leave some rows new and some old; "
            f"found {new} of 2000 new")

    # The same crash with the rollback journal (the default): all or nothing.
    g = tr.path(t)
    tr.db(t, g, "CREATE TABLE t(id INTEGER PRIMARY KEY, b TEXT);\nBEGIN;\n" + rows + "COMMIT;\n")
    tr.crash(t, g, "db-partial", "UPDATE t SET b = 'new';\n")
    new = tr.db(t, g, "SELECT id FROM t WHERE b = 'new';\n").out.count("\n")
    t.check(new == 0, f"with the journal, the half-done UPDATE must be rolled back; {new} rows are new")
    tr.integrity(t, g)
