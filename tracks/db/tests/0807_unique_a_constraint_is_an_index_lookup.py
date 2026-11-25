"""08.07 UNIQUE: a constraint is an index lookup

UNIQUE, CREATE UNIQUE INDEX and every PRIMARY KEY but INTEGER PRIMARY KEY
are unique indexes: CREATE TABLE writes the automatic indexes sqlite3
writes, named and numbered as sqlite3 numbers them, each engine opens and
writes what the other made, and INSERT, UPDATE and CREATE UNIQUE INDEX look
in the indexes before they write, failing as sqlite3 fails and leaving the
rows sqlite3 leaves, also when the process is killed in the commit after.
"""

import itertools
import os
import random
import re

ERROR = re.compile(r"^(?:Parse error|Runtime error|Error)(?: near line \d+(?: of .*)?)?: (.*)$", re.M)
SCHEMA = "SELECT type, name, tbl_name, rootpage, sql FROM sqlite_schema ORDER BY rowid;\n"
DUMP = "SELECT rowid, a, b, c FROM t ORDER BY rowid;\n"

# Every way to declare a constraint, on a table t with columns a, b and c (and an id
# where the INTEGER PRIMARY KEY is another column).
DECLS = [
    # a column's UNIQUE, a table's UNIQUE, CREATE UNIQUE INDEX
    "CREATE TABLE t(a UNIQUE, b, c);",
    "CREATE TABLE t(a, b, c, UNIQUE(a, b));",
    "CREATE TABLE t(a, b, c);\nCREATE UNIQUE INDEX t_ab ON t(a, b);",
    "CREATE TABLE t(a, b, c);\nCREATE UNIQUE INDEX t_c ON t(c);\nCREATE INDEX t_b ON t(b);",
    # a PRIMARY KEY that is not INTEGER PRIMARY KEY
    "CREATE TABLE t(a TEXT PRIMARY KEY, b, c);",
    "CREATE TABLE t(a INT PRIMARY KEY, b, c);",
    "CREATE TABLE t(a PRIMARY KEY, b, c);",
    "CREATE TABLE t(a INTEGER(10) PRIMARY KEY, b, c);",
    "CREATE TABLE t(a, b, c, PRIMARY KEY(a));",
    "CREATE TABLE t(a REAL, b, c, CONSTRAINT pk PRIMARY KEY(a ASC));",
    # a PRIMARY KEY of several columns
    "CREATE TABLE t(a, b, c, PRIMARY KEY(a, b));",
    "CREATE TABLE t(a, b, c, PRIMARY KEY(c, a));",
    # INTEGER PRIMARY KEY beside UNIQUE
    "CREATE TABLE t(id INTEGER PRIMARY KEY, a UNIQUE, b, c);",
    "CREATE TABLE t(id INTEGER, a, b UNIQUE, c, PRIMARY KEY(id));",
    "CREATE TABLE t(id INTEGER, a, b, c UNIQUE, PRIMARY KEY(id DESC));",
    "CREATE TABLE t(a INTEGER UNIQUE PRIMARY KEY, b, c);",
    "CREATE TABLE t(a INTEGER PRIMARY KEY UNIQUE, b, c);",
    "CREATE TABLE t(a INTEGER PRIMARY KEY, b, c, UNIQUE(a), UNIQUE(b, a));",
    # a constraint that repeats another (no index, no number) or does not quite
    "CREATE TABLE t(a UNIQUE, b, c, UNIQUE(a));",
    "CREATE TABLE t(a UNIQUE UNIQUE, b, c);",
    "CREATE TABLE t(a, b, c, PRIMARY KEY(a, b), UNIQUE(a, b), UNIQUE(b, a));",
    "CREATE TABLE t(a, b, c, UNIQUE(a, b), PRIMARY KEY(a, b));",
    "CREATE TABLE t(a PRIMARY KEY UNIQUE, b UNIQUE, c, UNIQUE(b));",
    "CREATE TABLE t(a, b, c, UNIQUE(a, a));",
    "CREATE TABLE t(a UNIQUE, b, c);\nCREATE UNIQUE INDEX t_a ON t(a);",
    # several on one table, columns and table constraints mixed
    "CREATE TABLE t(a UNIQUE, b TEXT PRIMARY KEY, c, UNIQUE(c, a));",
    "CREATE TABLE t(a, b TEXT PRIMARY KEY, c UNIQUE, UNIQUE(c, a), UNIQUE(a));",
    "CREATE TABLE t(a UNIQUE, b UNIQUE, c TEXT PRIMARY KEY);\nCREATE UNIQUE INDEX t_ab ON t(a, b);",
] + [  # three constraints in every order
    f"CREATE TABLE t(a, b TEXT, c, {', '.join(p)});"
    for p in itertools.permutations(["PRIMARY KEY(b)", "UNIQUE(a)", "UNIQUE(c, a)"])
]

# What each engine writes into the other's tables: NULLs, several rows at once, updates
# of the constrained columns and of the rowid, deletes.
DML = """INSERT INTO t(a, b, c) VALUES (1, 'x', 10), (2, 'y', 20), (3, 'z', 30);
INSERT INTO t(a, b, c) VALUES (4, 'w', 40);
INSERT INTO t(a, b, c) VALUES (NULL, 'n', NULL);
INSERT INTO t(a, b, c) VALUES (NULL, NULL, NULL);
UPDATE t SET c = c + 1 WHERE a = 2;
UPDATE t SET a = a + 10, b = b || '!' WHERE a < 4;
DELETE FROM t WHERE a = 13;
INSERT INTO t(a, b, c) VALUES (5, 'x', 10);
UPDATE t SET rowid = rowid + 100 WHERE b = 'w';
"""
# ... and what some of the constraints refuse.
CLASHES = """INSERT INTO t(a, b, c) VALUES (11, 'x!', 10);
INSERT INTO t(a, b, c) VALUES (4, 'w', 40);
INSERT INTO t(a, b, c) VALUES (6, 'v', 60), (12, 'y!', 21);
UPDATE t SET a = 4 WHERE b = 'x';
UPDATE t SET b = 'w', c = 40 WHERE a = 11;
UPDATE t SET a = 5, b = 'x', c = 10;
"""


def errors(text):
    """The error messages in a run's stderr, without either engine's prefix."""
    return ERROR.findall(text)


def alike(t, tr, sql, setup="", ours=None, theirs=None):
    """setup, then sql, through ./db and sqlite3, each on its own file (fresh, or the
    ones given): the same output, the same errors in the same order. Returns the files."""
    a, b = ours or tr.path(t), theirs or tr.path(t)
    if setup:
        tr.db(t, a, setup)
        tr.sqlite(t, b, setup)
    x = tr.db(t, a, sql, check=False)
    y = tr.sqlite(t, b, sql, check=False)
    t.check(x.rc >= 0, f"./db died:\n{x}")
    t.check(tr.same_output(x.out, y.out),
            f"./db and sqlite3 print different rows\n--- ./db\n{x.out[-1500:]}\n--- sqlite3\n{y.out[-1500:]}"
            f"\n--- sql\n{(setup + sql)[-2500:]}")
    t.check(errors(x.err) == errors(y.err),
            f"./db and sqlite3 fail differently\n--- ./db\n{x.err[-1500:]}\n--- sqlite3\n{y.err[-1500:]}"
            f"\n--- sql\n{(setup + sql)[-2500:]}")
    return a, b


def test(t):
    tr = t.track
    declarations(t, tr)
    violations(t, tr)
    update_order(t, tr)
    nulls(t, tr)
    which_one(t, tr)
    unique_index(t, tr)
    mixed_types(t, tr)
    many_rows(t, tr)
    crashes(t, tr)
    plans(t, tr)
    refused(t, tr)
    damaged(t, tr)


def declarations(t, tr):
    """Each declaration: ./db's file is sqlite3's, schema row for schema row, and sqlite3
    finds it sound; sqlite3's file is one ./db writes into soundly, as sqlite3 would."""
    for decl in DECLS:
        a, b = alike(t, tr, decl + "\n" + SCHEMA + DML + CLASHES + DUMP)
        tr.integrity(t, a)
        theirs = tr.sqlite(t, a, SCHEMA + DUMP).out
        t.check(theirs == tr.sqlite(t, b, SCHEMA + DUMP).out,
                f"sqlite3 reads ./db's file for {decl!r} differently from its own:\n{theirs}")
        # The other way: sqlite3 makes the table, ./db writes into it.
        g, h = tr.path(t), tr.path(t)
        tr.sqlite(t, g, decl + "\n")
        tr.sqlite(t, h, decl + "\n")
        alike(t, tr, DML + CLASHES + DUMP, ours=g, theirs=h)
        tr.integrity(t, g)
        t.check(tr.sqlite(t, g, SCHEMA + DUMP).out == tr.sqlite(t, h, SCHEMA + DUMP).out,
                f"after ./db wrote into sqlite3's {decl!r}, sqlite3 reads it differently")

    # Names: as written, quotes and case kept.
    for decl, name in [('CREATE TABLE "my t"(a UNIQUE, b);', '"my t"'), ("CREATE TABLE MiXed(A unique, b);", "mixed")]:
        a, _ = alike(t, tr, decl + "\n" + SCHEMA + f"INSERT INTO {name} VALUES (1, 2);\n"
                     f"INSERT INTO {name} VALUES (1, 3);\nSELECT * FROM {name};\n")
        tr.integrity(t, a)
    # DROP TABLE takes its automatic indexes with it; they cannot be dropped alone.
    a, _ = alike(t, tr, "DROP INDEX sqlite_autoindex_t_1;\nDROP INDEX IF EXISTS sqlite_autoindex_t_2;\n"
                        "DROP TABLE t;\n" + SCHEMA,
                 "CREATE TABLE t(a UNIQUE, b TEXT PRIMARY KEY);\nINSERT INTO t VALUES (1, 'x'), (2, 'y');\n")
    tr.integrity(t, a)
    # .schema shows the table, not its automatic indexes.
    f = tr.path(t)
    tr.db(t, f, "CREATE TABLE t(a UNIQUE, b);\nCREATE UNIQUE INDEX t_b ON t(b);\n")
    t.check(tr.db(t, f, ".schema\n").out == tr.sqlite(t, f, ".schema\n").out, ".schema should print what sqlite3 prints")


def violations(t, tr):
    """INSERT and UPDATE, one row and many, one column and two, outside BEGIN and inside:
    sqlite3's message, and the statement undone whole."""
    setup = ("CREATE TABLE t(id INTEGER PRIMARY KEY, a UNIQUE, b, c, UNIQUE(b, c));\n"
             "INSERT INTO t VALUES (1, 'a1', 'b1', 'c1'), (2, 'a2', 'b2', 'c2'), (3, 'a3', 'b3', 'c3');\n")
    clashes = """INSERT INTO t VALUES (4, 'a1', 'b4', 'c4');
INSERT INTO t VALUES (4, 'a4', 'b1', 'c1');
INSERT INTO t VALUES (1, 'a1', 'b1', 'c1');
INSERT INTO t VALUES (4, 'a4', 'b4', 'c4'), (5, 'a5', 'b5', 'c5'), (6, 'a1', 'b6', 'c6');
INSERT INTO t VALUES (4, 'a4', 'b4', 'c4'), (5, 'a4', 'b5', 'c5');
INSERT INTO t(a, b, c) VALUES ('a7', 'b7', 'c7'), ('a8', 'b7', 'c7');
UPDATE t SET a = 'a2' WHERE id = 1;
UPDATE t SET b = 'b2', c = 'c2' WHERE id = 3;
UPDATE t SET a = 'same';
UPDATE t SET b = 'b1', c = 'c1';
UPDATE t SET c = 'c1' WHERE id >= 2;
UPDATE t SET a = a || '!', b = 'b2' WHERE id <> 2;
UPDATE t SET id = id + 10, a = 'a1' WHERE id = 2;
"""
    alike(t, tr, clashes + "SELECT * FROM t ORDER BY id;\n", setup)
    a, _ = alike(t, tr, "BEGIN;\nINSERT INTO t VALUES (10, 'a10', 'b10', 'c10');\n" + clashes +
                 "INSERT INTO t VALUES (11, 'a11', 'b11', 'c11'), (12, 'a12', 'b12', 'c12');\n"
                 "UPDATE t SET a = a || 'x' WHERE id > 10;\n"
                 "SELECT * FROM t ORDER BY id;\nCOMMIT;\nSELECT * FROM t ORDER BY id;\n", setup)
    tr.integrity(t, a)
    # Outside BEGIN a failed multi-row INSERT or UPDATE leaves the file as it was, byte for byte.
    f = tr.path(t)
    tr.db(t, f, setup)
    with open(f, "rb") as fh:
        before = fh.read()
    for sql in ["INSERT INTO t VALUES (4, 'a4', 'b4', 'c4'), (5, 'a5', 'b5', 'c5'), (6, 'a1', 'b6', 'c6');",
                "UPDATE t SET a = 'same';", "UPDATE t SET b = 'b9', c = 'c9' WHERE id >= 2;"]:
        r = tr.db(t, f, sql + "\n", check=False)
        t.check(errors(r.err) and errors(r.err)[0].startswith("UNIQUE constraint failed"), f"{sql} should fail:\n{r}")
        with open(f, "rb") as fh:
            t.check(fh.read() == before, f"a failed {sql} must leave the file untouched")


def update_order(t, tr):
    """UPDATE checks row by row, in sqlite3's order: SET a = a + 1 fails on 1, 2, 3 and
    passes on 3, 2, 1, and through an index it changes, it goes in rowid order."""
    setup = ("CREATE TABLE asc_t(a UNIQUE);\nINSERT INTO asc_t VALUES (1), (2), (3);\n"
             "CREATE TABLE desc_t(a UNIQUE);\nINSERT INTO desc_t VALUES (3), (2), (1);\n"
             "CREATE TABLE e(a UNIQUE, b);\nCREATE INDEX e_b ON e(b);\nINSERT INTO e VALUES (1, 3), (2, 2), (3, 1);\n"
             "CREATE TABLE f(id INTEGER PRIMARY KEY, b);\nCREATE INDEX f_b ON f(b);\n"
             "INSERT INTO f VALUES (1, 3), (2, 2), (3, 1);\n")
    sql = """UPDATE asc_t SET a = a + 1;
UPDATE desc_t SET a = a + 1;
SELECT rowid, a FROM asc_t ORDER BY rowid;
SELECT rowid, a FROM desc_t ORDER BY rowid;
UPDATE desc_t SET a = a + 1 WHERE a > 0;
UPDATE asc_t SET a = a + 1 WHERE a > 0;
UPDATE asc_t SET a = a - 1 WHERE a >= 1;
UPDATE desc_t SET a = a - 1 WHERE a BETWEEN 0 AND 100;
SELECT rowid, a FROM asc_t ORDER BY rowid;
SELECT rowid, a FROM desc_t ORDER BY rowid;
UPDATE e SET a = a + 1 WHERE b > 0;
UPDATE e SET a = a + 1;
UPDATE e SET a = a + 1, b = b + 1 WHERE b > 0;
UPDATE e SET a = a + 1 WHERE b = 2;
SELECT rowid, a, b FROM e ORDER BY rowid;
UPDATE f SET id = id + 1 WHERE b > 0;
UPDATE f SET id = id - 1 WHERE b > 0;
UPDATE f SET id = id + 1;
SELECT id, b FROM f ORDER BY id;
"""
    alike(t, tr, sql, setup)
    a, _ = alike(t, tr, "BEGIN;\n" + sql + "COMMIT;\n" + sql, setup)
    tr.integrity(t, a)


def nulls(t, tr):
    """NULL never equals anything, so it never conflicts: not in a UNIQUE column, not in
    one column of several, not in a PRIMARY KEY that is not INTEGER PRIMARY KEY."""
    setup = ("CREATE TABLE t(a UNIQUE, b, c, UNIQUE(b, c));\nCREATE TABLE p(k TEXT PRIMARY KEY, v);\n"
             "CREATE TABLE q(x, y, PRIMARY KEY(x, y));\n")
    sql = """INSERT INTO t VALUES (NULL, 1, NULL), (NULL, 1, NULL), (NULL, NULL, NULL);
INSERT INTO t VALUES (1, 1, 1);
INSERT INTO t VALUES (NULL, 1, 1);
UPDATE t SET a = NULL;
UPDATE t SET c = NULL WHERE b = 1;
UPDATE t SET b = 1, c = NULL;
INSERT INTO p VALUES (NULL, 1), (NULL, 2);
INSERT INTO p VALUES ('x', 3);
INSERT INTO p VALUES ('x', 4);
UPDATE p SET k = NULL WHERE v = 3;
UPDATE p SET k = NULL;
INSERT INTO q VALUES (1, NULL), (1, NULL), (NULL, NULL), (NULL, 1), (1, 1);
INSERT INTO q VALUES (1, 1);
CREATE UNIQUE INDEX t_c ON t(c);
CREATE UNIQUE INDEX t_b ON t(b);
SELECT rowid, a, b, c FROM t ORDER BY rowid;
SELECT rowid, k, v FROM p ORDER BY rowid;
SELECT rowid, x, y FROM q ORDER BY rowid;
"""
    a, _ = alike(t, tr, sql, setup)
    tr.integrity(t, a)


def which_one(t, tr):
    """A row that breaks several constraints fails on the one declared last; an index
    CREATE UNIQUE INDEX made later comes before them all; the same after reopening."""
    setup = "CREATE TABLE m(a UNIQUE, b UNIQUE, c TEXT PRIMARY KEY);\nINSERT INTO m VALUES (1, 1, 'x');\n"
    probe = ("INSERT INTO m VALUES (1, 1, 'x');\nINSERT INTO m VALUES (2, 1, 'x');\nINSERT INTO m VALUES (2, 2, 'x');\n"
             "INSERT INTO m VALUES (1, 1, 'y');\nINSERT INTO m VALUES (1, 2, 'y');\n"
             "UPDATE m SET a = 1, b = 1, c = 'x' WHERE c = 'z';\nINSERT INTO m VALUES (5, 5, 'z');\n"
             "UPDATE m SET a = 1, b = 1, c = 'x' WHERE c = 'z';\nUPDATE m SET a = 1, b = 1 WHERE c = 'z';\n")
    a, b = alike(t, tr, probe, setup)
    alike(t, tr, "CREATE UNIQUE INDEX m_ab ON m(a, b);\n" + probe, ours=a, theirs=b)
    alike(t, tr, probe + "SELECT * FROM m ORDER BY rowid;\n", ours=a, theirs=b)    # reopened
    tr.integrity(t, a)
    # Every order of three constraints, broken all at once and two at a time.
    for p in itertools.permutations(["PRIMARY KEY(b)", "UNIQUE(a)", "UNIQUE(c, a)", "UNIQUE(c)"]):
        alike(t, tr, "INSERT INTO t VALUES (1, 'x', 1);\nINSERT INTO t VALUES (1, 'y', 2);\n"
                     "INSERT INTO t VALUES (2, 'x', 1);\nINSERT INTO t VALUES (3, 'z', 1);\n",
              f"CREATE TABLE t(a, b TEXT, c, {', '.join(p)});\nINSERT INTO t VALUES (1, 'x', 1);\n")


def unique_index(t, tr):
    """CREATE UNIQUE INDEX over rows that already hold a duplicate fails as an INSERT
    would and leaves no trace of itself: not a row, not a page."""
    setup = "CREATE TABLE t(a, b);\nINSERT INTO t VALUES (1, 'x'), (2, 'y'), (1, 'z'), (NULL, 'n1'), (NULL, 'n2');\n"
    sql = ("CREATE UNIQUE INDEX t_a ON t(a);\nCREATE UNIQUE INDEX t_ab ON t(a, b);\nCREATE UNIQUE INDEX t_b ON t(b);\n"
           "INSERT INTO t VALUES (3, 'x');\nDELETE FROM t WHERE b = 'z';\nCREATE UNIQUE INDEX t_a ON t(a);\n"
           "INSERT INTO t VALUES (2, 'q');\nINSERT INTO t VALUES (NULL, 'q');\n"
           "SELECT name, sql FROM sqlite_schema WHERE type = 'index' ORDER BY rowid;\n")
    a, _ = alike(t, tr, sql, setup)
    tr.integrity(t, a)
    a, _ = alike(t, tr, "BEGIN;\nINSERT INTO t VALUES (5, 'five');\n" + sql + "COMMIT;\n" + SCHEMA, setup)
    tr.integrity(t, a)
    f = tr.path(t)
    tr.db(t, f, setup + "BEGIN;\n" + "".join(f"INSERT INTO t VALUES ({i}, '{'p' * 300}');\n" for i in range(3, 400)) +
          "COMMIT;\n")
    with open(f, "rb") as fh:
        before = fh.read()
    r = tr.db(t, f, "CREATE UNIQUE INDEX t_a ON t(a);\n", check=False)
    t.check(errors(r.err) == ["UNIQUE constraint failed: t.a"], f"CREATE UNIQUE INDEX over a duplicate:\n{r}")
    with open(f, "rb") as fh:
        t.check(fh.read() == before, "a failed CREATE UNIQUE INDEX must leave the file as it was")
    tr.db(t, f, "BEGIN;\nCREATE UNIQUE INDEX t_ab ON t(a, b);\nCREATE UNIQUE INDEX t_a ON t(a);\nCOMMIT;\n", check=False)
    t.check(tr.db(t, f, "SELECT name FROM sqlite_schema WHERE type = 'index';\n").out == "t_ab\n",
            "inside BEGIN only the failed CREATE UNIQUE INDEX is undone")
    tr.integrity(t, f)


def mixed_types(t, tr):
    """1, 1.0, '1' and x'31' under one constraint, with each column affinity: equal as
    sqlite3 compares them, after the column's affinity has made what it makes of them."""
    tables = ["n(x UNIQUE)", "s(x TEXT UNIQUE)", "i(x INTEGER UNIQUE)", "r(x REAL UNIQUE)", "u(x NUMERIC UNIQUE)",
              "k(x TEXT PRIMARY KEY)", "p(x, y, PRIMARY KEY(y, x))"]
    values = ["1", "1.0", "'1'", "x'31'", "'1.0'", "' 1'", "1.5", "'1.5'", "-0.0", "0", "9223372036854775807",
              "9.223372036854775807e18", "'abc'", "x'616263'", "'ABC'"]
    setup = "".join(f"CREATE TABLE {d};\n" for d in tables)
    sql = ""
    for d in tables:
        name = d.split("(")[0]
        cols = "(x, y)" if name == "p" else "(x)"
        for v in values:
            sql += f"INSERT INTO {name}{cols} VALUES ({v}{', 1' if name == 'p' else ''});\n"
        sql += f"SELECT rowid, x, typeof(x) FROM {name} ORDER BY rowid;\n"
        sql += f"UPDATE {name} SET x = 1 WHERE rowid > 1;\nUPDATE {name} SET x = '1' WHERE rowid = 3;\n"
        sql += f"SELECT rowid, x, typeof(x) FROM {name} ORDER BY rowid;\n"
    a, _ = alike(t, tr, sql, setup)
    tr.integrity(t, a)


def many_rows(t, tr):
    """Thousands of rows: the automatic indexes have several levels, and the lookup
    still finds every key, whichever page it is on."""
    rnd = random.Random(807)
    keys = rnd.sample(range(1, 10 ** 6), 5000)
    rows = "".join(f"INSERT INTO t VALUES ({k}, 'name {k:07d} {'n' * 60}', {i});\n" for i, k in enumerate(keys))
    setup = "CREATE TABLE t(a INTEGER UNIQUE, b TEXT PRIMARY KEY, c);\nBEGIN;\n" + rows + "COMMIT;\n"
    f = tr.path(t)
    tr.db(t, f, setup)
    tr.integrity(t, f)
    roots = tr.rows(tr.db(t, f, "SELECT name, rootpage FROM sqlite_schema WHERE type = 'index';\n").out)
    t.check([r[0] for r in roots] == ["sqlite_autoindex_t_1", "sqlite_autoindex_t_2"], f"the indexes: {roots}")
    depth = tr.tree_depth(f, int(roots[1][1]))
    t.check(depth >= 3, f"the index on b should have at least three levels, has {depth}")
    clash = []
    for _ in range(300):
        k = rnd.choice(keys)
        c = rnd.random()
        if c < 0.3:
            clash.append(f"INSERT INTO t VALUES ({k}, 'new {rnd.randint(0, 10 ** 9)}', 0);")
        elif c < 0.5:
            clash.append(f"INSERT INTO t VALUES ({rnd.randint(10 ** 6, 2 * 10 ** 6)}, 'name {k:07d} {'n' * 60}', 0);")
        elif c < 0.7:
            clash.append(f"UPDATE t SET a = {rnd.choice(keys)} WHERE a = {k};")
        elif c < 0.8:
            clash.append(f"DELETE FROM t WHERE a = {k};")
        else:
            clash.append(f"INSERT INTO t VALUES ({rnd.randint(2 * 10 ** 6, 3 * 10 ** 6)}, 'fresh {rnd.randint(0, 10 ** 9)}', 1);")
    sql = "\n".join(clash) + "\nSELECT a, b, c FROM t ORDER BY a;\n"
    a, _ = alike(t, tr, sql, setup)
    tr.integrity(t, a)
    # sqlite3's big table, written by ./db.
    g, h = tr.path(t), tr.path(t)
    tr.sqlite(t, g, setup)
    tr.sqlite(t, h, setup)
    alike(t, tr, sql, ours=g, theirs=h)
    tr.integrity(t, g)


def crashes(t, tr):
    """A multi-row INSERT that fails on its last row, inside a transaction killed during
    its COMMIT, leaves a file sqlite3 accepts with none of that INSERT's rows in it."""
    dump = "SELECT rowid, a, b, c, d FROM t ORDER BY rowid;\n"
    rows = "".join(f"INSERT INTO t VALUES ({i}, 'key {i} {'k' * 50}', {i * 7 % 2003}, 'row {i}');\n" for i in range(1, 2001))
    table = "CREATE TABLE t(a UNIQUE, b TEXT PRIMARY KEY, c, d, UNIQUE(c, a));\n"
    failing = ("INSERT INTO t VALUES " + ", ".join(f"({i}, 'new {i} {'n' * 50}', {i}, NULL)" for i in range(5000, 5600))
               + ", (1, 'dup', 0, NULL);\n")
    change = ("BEGIN;\nUPDATE t SET c = c + 100000 WHERE a % 5 = 0;\n" + failing +
              "INSERT INTO t VALUES (9000, 'after', 9000, 'after');\nCOMMIT;\n")
    for mode, points in [("", {p: "old" for p in ["journal-partial", "journal-hot", "db-partial", "db-torn",
                                                     "db-written", "before-delete"]}),
                         ("PRAGMA journal_mode=wal;\n", {"wal-partial": "old", "wal-torn": "old", "wal-written": "new",
                                                         "checkpoint-partial": "new", "checkpoint-done": "new"})]:
        setup = mode + table + "BEGIN;\n" + rows + "COMMIT;\n"
        f = tr.path(t)
        tr.db(t, f, setup)
        old = tr.db(t, f, dump).out
        a, _ = alike(t, tr, change + dump, ours=f, theirs=_made(t, tr, setup))
        new = tr.db(t, a, dump).out
        t.check(new != old and "new 5000" not in new, "the change commits without the failed INSERT's rows")
        for point, which in points.items():
            f = tr.path(t)
            tr.db(t, f, setup)
            r = tr.crash(t, f, point, change)
            t.check(errors(r.err) == ["UNIQUE constraint failed: t.a"], f"the INSERT should fail first:\n{r}")
            t.check(tr.db(t, f, dump).out == (old if which == "old" else new),
                    f"after a crash at {point} the database should hold the {which} rows")
            tr.integrity(t, f)
    # sqlite3 rolls back the journal ./db left, and finds the old rows and sound indexes.
    setup = table + "BEGIN;\n" + rows + "COMMIT;\n"
    f = tr.path(t)
    tr.db(t, f, setup)
    old = tr.db(t, f, dump).out
    tr.crash(t, f, "db-partial", change)
    t.check(tr.sqlite(t, f, dump).out == old, "sqlite3 should roll back ./db's journal to the old rows")
    tr.integrity(t, f)


def _made(t, tr, setup):
    g = tr.path(t)
    tr.sqlite(t, g, setup)
    return g


def plans(t, tr):
    """A lookup through an automatic index reads as sqlite3's EXPLAIN QUERY PLAN says."""
    setup = ("CREATE TABLE t(a UNIQUE, b);\nCREATE TABLE p(k TEXT PRIMARY KEY, v);\n"
             "CREATE TABLE m(x, y, z, UNIQUE(x, y));\nCREATE TABLE r(id INTEGER PRIMARY KEY, code TEXT UNIQUE, n);\n"
             "INSERT INTO t VALUES (5, 'five'), (6, 'six');\nINSERT INTO p VALUES ('x', 1);\n")
    sql = ("EXPLAIN QUERY PLAN SELECT * FROM t WHERE a = 5;\nEXPLAIN QUERY PLAN SELECT b FROM t WHERE a > 5;\n"
           "EXPLAIN QUERY PLAN SELECT v FROM p WHERE k = 'x';\nEXPLAIN QUERY PLAN SELECT z FROM m WHERE x = 1;\n"
           "EXPLAIN QUERY PLAN SELECT n FROM r WHERE code = 'q';\nEXPLAIN QUERY PLAN SELECT n FROM r WHERE id = 3;\n"
           "EXPLAIN QUERY PLAN UPDATE t SET b = 1 WHERE a = 5;\nEXPLAIN QUERY PLAN DELETE FROM p WHERE k = 'x';\n"
           "SELECT b FROM t WHERE a = 5;\nSELECT v FROM p WHERE k = 'x';\n")
    tr.both(t, sql, setup)
    out = tr.db(t, tr.path(t), setup + "EXPLAIN SELECT b FROM t WHERE a = 5;\n").out
    t.check("Index lookup t using sqlite_autoindex_t_1 (a = ?)" in out, f"EXPLAIN should show the lookup:\n{out}")


def refused(t, tr):
    """Errors in both engines, with sqlite3's words; what stays unsupported says so."""
    for sql in ["CREATE TABLE t(a, UNIQUE(b));", "CREATE TABLE t(a, PRIMARY KEY(b));",
                "CREATE TABLE t(a PRIMARY KEY, b PRIMARY KEY);", "CREATE TABLE t(a, b, PRIMARY KEY(a), PRIMARY KEY(b));",
                "CREATE TABLE t(a INTEGER PRIMARY KEY, b, PRIMARY KEY(b));", "CREATE TABLE t(a, b, UNIQUE());"]:
        r = tr.errors_alike(t, "", sql + "\n")
        theirs = tr.sqlite(t, tr.path(t), sql + "\n", check=False)
        t.check(errors(r.err) == errors(theirs.err), f"{sql}: ./db says {r.err!r}, sqlite3 {theirs.err!r}")
    alike(t, tr, "DROP INDEX sqlite_autoindex_t_1;\n", "CREATE TABLE t(a UNIQUE);\n")
    for sql, what in [("CREATE TABLE t(a UNIQUE COLLATE NOCASE);", "COLLATE"),
                      ("CREATE TABLE t(a, UNIQUE(a COLLATE NOCASE));", "COLLATE"),
                      ("CREATE TABLE t(a, b, UNIQUE(a DESC));", "DESC"),
                      ("CREATE TABLE t(a TEXT PRIMARY KEY DESC);", "DESC"),
                      ("CREATE TABLE t(a UNIQUE, b CHECK (b > 0));", "CHECK")]:
        r = tr.db(t, tr.path(t), sql + "\n", check=False)
        t.check(r.rc != 0 and what in r.err and "not supported" in r.err, f"{sql} should be refused, got:\n{r}")
        # sqlite3's table with it: readable, read-only, untouched.
        g = tr.path(t)
        tr.sqlite(t, g, sql + "\nINSERT INTO t(a) VALUES ('k');\n")
        t.check(tr.db(t, g, "SELECT a FROM t;\n").out == "k\n", f"{sql} from sqlite3 should still be readable")
        r = tr.db(t, g, "INSERT INTO t(a) VALUES ('j');\n", check=False)
        t.check(r.rc != 0 and "read-only" in r.err, f"{sql} from sqlite3 should be read-only, got:\n{r}")
        tr.integrity(t, g)
    for sql in ["INSERT OR REPLACE INTO t VALUES (1);", "INSERT OR IGNORE INTO t VALUES (1);",
                "INSERT INTO t VALUES (1) ON CONFLICT DO NOTHING;", "REPLACE INTO t VALUES (1);"]:
        r = tr.db(t, tr.path(t), "CREATE TABLE t(a UNIQUE);\n" + sql + "\n", check=False)
        t.check(r.rc != 0 and "Error:" in r.err, f"{sql} must stay refused, got:\n{r}")
    # INTEGER PRIMARY KEY DESC on the column is no rowid: an ordinary column, read as one.
    g = tr.path(t)
    tr.sqlite(t, g, "CREATE TABLE v(id INTEGER PRIMARY KEY DESC, z);\nINSERT INTO v VALUES (5, 'a');\n")
    t.check(tr.db(t, g, "SELECT rowid, id, z FROM v;\nSELECT z FROM v WHERE id = 5;\n").out == "1|5|a\na\n",
            "INTEGER PRIMARY KEY DESC keeps its value in the row, not in the rowid")


def damaged(t, tr):
    """A schema sqlite3 would call malformed (an automatic index missing, or one no
    constraint has) leaves the table readable and read-only, never written wrong."""
    for change in ["DELETE FROM sqlite_schema WHERE name = 'sqlite_autoindex_t_2';",
                   "UPDATE sqlite_schema SET name = 'sqlite_autoindex_t_9' WHERE name = 'sqlite_autoindex_t_2';"]:
        g = tr.path(t)
        tr.sqlite(t, g, "CREATE TABLE t(a UNIQUE, b UNIQUE);\nINSERT INTO t VALUES (1, 2);\n"
                        ".dbconfig defensive off\nPRAGMA writable_schema = ON;\n" + change + "\n")
        t.check(tr.db(t, g, "SELECT a, b FROM t WHERE b = 2;\n").out == "1|2\n", f"after {change} t is still readable")
        r = tr.db(t, g, "INSERT INTO t VALUES (3, 4);\n", check=False)
        t.check(r.rc != 0 and "read-only" in r.err, f"after {change} t must be read-only, got:\n{r}")
