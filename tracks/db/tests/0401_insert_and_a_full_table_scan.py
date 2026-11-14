"""04.01 INSERT and a full table scan

INSERT stores rows with SQLite's affinity rules and rowid choices, and
a scan reads them back exactly as sqlite3 does, including rows sqlite3
stored in its own ways: a whole-number float in a REAL column kept as an
integer, and a row stored before ALTER TABLE ADD COLUMN, which has no value
for the new column and reads as its DEFAULT.
"""


def test(t):
    tr = t.track
    setup = ("CREATE TABLE t(id INTEGER PRIMARY KEY, i INTEGER, r REAL, s TEXT, b BLOB, n NUMERIC, x);\n"
             "CREATE TABLE d(k INT, v TEXT DEFAULT 'none', w DEFAULT 7, z);\n")
    vals = ["'12'", "'12.5'", "12.0", "'abc'", "x'41'", "NULL", "1e3", "' 7 '", "'0x10'", "-0", "'-3e2'", "5"]
    sql = []
    for i, v in enumerate(vals):
        sql.append(f"INSERT INTO t(i, r, s, b, n, x) VALUES ({v}, {v}, {v}, {v}, {v}, {v});")
    sql += ["INSERT INTO t VALUES (100, 1, 2, 3, 4, 5, 6);",
            "INSERT INTO t(s) VALUES ('after 100');",
            "INSERT INTO t VALUES ('50', 1, 2, 3, 4, 5, 6);",
            "INSERT INTO t(id, s) VALUES (-5, 'negative'), (NULL, 'auto');",
            "INSERT INTO d(k) VALUES (1);",
            "INSERT INTO d VALUES (2, 'two', NULL, 'zz');",
            "INSERT INTO d(z, k) VALUES ('first', 3);",
            "INSERT INTO d(rowid, k) VALUES (40, 4);",
            "INSERT INTO d(k) VALUES (5);"]
    q = ["SELECT id, typeof(i), i, typeof(r), r, typeof(s), s, typeof(b), b, typeof(n), n, typeof(x), x FROM t;",
         "SELECT rowid, * FROM d;", "SELECT * FROM t;", "SELECT s, id FROM t;"]
    tr.both(t, "\n".join(sql + q) + "\n", setup)

    errs = ["INSERT INTO t(id) VALUES (100);", "INSERT INTO t VALUES (1, 2);", "INSERT INTO t(nope) VALUES (1);",
            "INSERT INTO nosuch VALUES (1);", "INSERT INTO t(id) VALUES ('text');", "INSERT INTO d(rowid) VALUES (40);"]
    base = setup + "INSERT INTO t(id) VALUES (100);\nINSERT INTO d(rowid, k) VALUES (40, 4);\n"
    for e in errs:
        tr.errors_alike(t, base, e + "\n")
    tr.errors_alike(t, "CREATE TABLE nn(a NOT NULL);\n", "INSERT INTO nn VALUES (NULL);\n")

    f = tr.path(t)
    tr.db(t, f, setup + "\n".join(sql) + "\n")
    tr.integrity(t, f)

    real_columns(t, tr)
    added_columns(t, tr)


def same_as_sqlite3(t, tr, g, q, what):
    """./db and sqlite3 read the same answers from the file sqlite3 wrote."""
    ours, theirs = tr.db(t, g, q).out, tr.sqlite(t, g, q).out
    if not tr.same_output(ours, theirs):
        raise tr.Fail(f"{what}: ./db and sqlite3 disagree. {tr._diff(ours, theirs)}\n--- sql\n{q}")


def real_columns(t, tr):
    """sqlite3 stores 2.0 in a REAL column as the integer 2; it reads as 2.0."""
    g = tr.path(t)
    tr.sqlite(t, g, "CREATE TABLE p(id INTEGER PRIMARY KEY, price REAL, f FLOAT, d DOUBLE, n NUMERIC, x);\n"
                    "INSERT INTO p(price, f, d, n, x) VALUES (2.0, 2.0, 2.0, 2.0, 2.0), (2, 3, -4, 2, 2), "
                    "(2.5, 0.0, 1e15, 2.5, 2.5), ('7', '7.0', '-0', '7.0', '7.0'), (NULL, x'41', 'abc', NULL, NULL);\n"
                    "CREATE INDEX p_price ON p(price);\n")
    q = ("SELECT id, price, typeof(price), price / 4, f, typeof(f), f / 4, d, typeof(d), d / 4, "
         "n, typeof(n), n / 4, x, typeof(x), x / 4 FROM p;\n"
         "SELECT id FROM p WHERE price = 2 ORDER BY id;\nSELECT id, price FROM p WHERE price > 1 ORDER BY price, id;\n"
         "SELECT id, price * 3, typeof(price * 3), price || '' FROM p ORDER BY id;\n")
    same_as_sqlite3(t, tr, g, q, "a REAL column sqlite3 wrote")
    # Rows rewritten by ./db (and their index entries) still agree.
    w = "UPDATE p SET x = price * 2;\nDELETE FROM p WHERE price = 2.5;\nUPDATE p SET price = price + 1 WHERE id = 2;\n"
    tr.db(t, g, w)
    tr.integrity(t, g)
    same_as_sqlite3(t, tr, g, q, "a REAL column after ./db changed it")


def added_columns(t, tr):
    """A row sqlite3 stored before ALTER TABLE ADD COLUMN reads as the DEFAULT."""
    g = tr.path(t)
    tr.sqlite(t, g, "CREATE TABLE t(a);\nINSERT INTO t VALUES (1), ('two');\n"
                    "ALTER TABLE t ADD COLUMN b DEFAULT 5;\nALTER TABLE t ADD COLUMN c REAL DEFAULT 3;\n"
                    "ALTER TABLE t ADD COLUMN d TEXT DEFAULT (-1);\nALTER TABLE t ADD COLUMN e NUMERIC DEFAULT '6.0';\n"
                    "ALTER TABLE t ADD COLUMN f DEFAULT 'x';\nALTER TABLE t ADD COLUMN g;\n"
                    "ALTER TABLE t ADD COLUMN h INTEGER DEFAULT NULL;\nALTER TABLE t ADD COLUMN i BLOB DEFAULT x'4142';\n"
                    "INSERT INTO t(a) VALUES (3);\nINSERT INTO t VALUES (4, 50, 30, 'dd', 60, 'ff', 'gg', 80, x'43');\n")
    q = ("SELECT rowid, a, b, typeof(b), c, typeof(c), d, typeof(d), e, typeof(e), f, g, typeof(g), h, typeof(h), "
         "i, typeof(i) FROM t;\n"
         "SELECT a FROM t WHERE b = 5 AND c = 3.0 AND d = '-1' ORDER BY a;\nSELECT a FROM t WHERE g IS NULL ORDER BY a;\n")
    same_as_sqlite3(t, tr, g, q, "rows stored before ALTER TABLE ADD COLUMN")
    # An index ./db builds over the short rows holds the defaults (sqlite3's
    # check looks every row up in it), and rows ./db rewrites keep them.
    tr.db(t, g, "CREATE INDEX t_b ON t(b);\nUPDATE t SET a = a || '!' WHERE rowid = 1;\nDELETE FROM t WHERE b = 50;\n")
    tr.integrity(t, g)
    same_as_sqlite3(t, tr, g, q + "SELECT a FROM t WHERE b = 5 ORDER BY a;\n", "the same rows after ./db changed them")
