"""03.03 The schema: CREATE TABLE and the catalog

CREATE TABLE writes the same sqlite_schema rows sqlite3 writes; the
catalog is rebuilt from them, from our files and from sqlite3's; tables
using features we lack are read-only rather than damaged, and CREATE
TABLE refuses them (a PRIMARY KEY other than INTEGER PRIMARY KEY needs an
index sqlite3 makes by itself, which this engine does not keep).
"""

# Primary keys sqlite3 backs with an automatic index (sqlite_autoindex_k_1).
NOT_ROWID_PKS = ["CREATE TABLE k(id INT PRIMARY KEY, v);",
                 "CREATE TABLE k(id TEXT PRIMARY KEY, v);",
                 "CREATE TABLE k(id PRIMARY KEY, v);",
                 "CREATE TABLE k(id, v, PRIMARY KEY(id));",
                 "CREATE TABLE k(a, b, PRIMARY KEY(a, b));"]


def test(t):
    tr = t.track
    ddl = """CREATE TABLE plain(a, b, c);
CREATE TABLE IF NOT EXISTS typed (id INTEGER PRIMARY KEY, name VARCHAR(40) NOT NULL, score DOUBLE PRECISION,
  joined DATE DEFAULT '2026-01-01', flag BOOLEAN);
create table   Lower(x integer, y text);
CREATE TABLE IF NOT EXISTS plain(z);
CREATE TABLE "quoted name"("col one" TEXT, [col two] INT);
"""
    q = "SELECT type, name, tbl_name, rootpage, sql FROM sqlite_schema;\n"
    out = tr.both(t, ddl + q)
    t.check(out.count("\ntable|") + out.startswith("table|") == 4, f"four tables, one row each in sqlite_schema:\n{out}")

    f = tr.path(t)
    tr.db(t, f, ddl)
    t.check(tr.header(f)["schema_cookie"] == 4, f"each CREATE bumps the schema cookie: {tr.header(f)['schema_cookie']}")
    tr.integrity(t, f)
    t.check(tr.db(t, f, ".tables\n").out.splitlines() == ["plain", "typed", "Lower", "quoted name"], ".tables after reopening")
    tr.db(t, f, "INSERT INTO typed(name, score) VALUES ('ann', '9.5');\nINSERT INTO \"quoted name\" VALUES ('v', '12');\n")
    want = "1|ann|9.5|2026-01-01|\n"
    t.check(tr.sqlite(t, f, "SELECT * FROM typed;").out == want, "sqlite3 reads a row ./db wrote")
    t.check(tr.sqlite(t, f, "SELECT typeof(\"col two\") FROM \"quoted name\";").out == "integer\n",
            "INT affinity turns '12' into an integer")
    tr.errors_alike(t, ddl, "CREATE TABLE plain(z);\n")
    tr.errors_alike(t, "", "CREATE TABLE d(a, b, A);\n")
    tr.errors_alike(t, "", "CREATE TABLE sqlite_mine(a);\n")

    # sqlite3's schemas, including what we cannot write to.
    g = tr.path(t)
    tr.sqlite(t, g, ddl + "CREATE TABLE u(a TEXT UNIQUE, b);\nINSERT INTO u VALUES ('k', 1);\n"
                         "CREATE TABLE ai(id INTEGER PRIMARY KEY AUTOINCREMENT, v);\nCREATE INDEX plain_b ON plain(b);\n")
    t.check(tr.db(t, g, ".tables\n").out.splitlines() == ["plain", "typed", "Lower", "quoted name", "u", "ai"],
            "./db should list every table sqlite3 made (sqlite_sequence is internal)")
    t.check(tr.db(t, g, "SELECT a, b FROM u;\n").out == "k|1\n", "a table with UNIQUE is still readable")
    r = tr.db(t, g, "INSERT INTO u VALUES ('k2', 2);\n", check=False)
    t.check(r.rc != 0 and "read-only" in r.err, f"a table with UNIQUE must refuse writes, got:\n{r}")
    tr.db(t, g, "INSERT INTO plain VALUES (1, 2, 3);\n")
    tr.integrity(t, g)

    primary_keys(t, tr, ddl)
    unparsable(t, tr)


def primary_keys(t, tr, ddl):
    """Only INTEGER PRIMARY KEY is the rowid; any other primary key is refused
    by CREATE TABLE, and read-only in a file sqlite3 made."""
    for sql in NOT_ROWID_PKS:
        g = tr.path(t)
        made = tr.sqlite(t, g, sql + "\nSELECT name FROM sqlite_schema WHERE type = 'index';\n").out
        t.check(made.startswith("sqlite_autoindex_k_"), f"sqlite3 should back {sql} with an index, made {made!r}")
        f = tr.path(t)
        tr.db(t, f, ddl)
        r = tr.db(t, f, sql + "\n", check=False)
        t.check(r.rc != 0 and "Error:" in r.err and "PRIMARY KEY" in r.err and "not supported" in r.err,
                f"./db should refuse {sql} (sqlite3 needs an index for it that ./db would not keep), got:\n{r}")
        t.check("k" not in tr.db(t, f, ".tables\n").out.split(), f"a refused {sql} must not leave a table behind")
        tr.integrity(t, f)
    # Two primary keys: an error in both.
    tr.errors_alike(t, "", "CREATE TABLE k(a INTEGER PRIMARY KEY, b INTEGER PRIMARY KEY);\n")
    # PRIMARY KEY(id) on a column declared INTEGER is the rowid, as a column constraint is.
    tr.both(t, "INSERT INTO k(v) VALUES ('a');\nINSERT INTO k VALUES (10, 'b');\nINSERT INTO k(v) VALUES ('c');\n"
               "SELECT rowid, id, v FROM k;\nSELECT type, name FROM sqlite_schema;\n",
            "CREATE TABLE k(id INTEGER, v, PRIMARY KEY(id));\n")
    # The same table made by sqlite3: readable, read-only, and left intact.
    g = tr.path(t)
    tr.sqlite(t, g, "CREATE TABLE k(id INT PRIMARY KEY, v);\nINSERT INTO k VALUES (2, 'two'), (1, 'one');\n")
    q = "SELECT id, v FROM k ORDER BY id;\nSELECT v FROM k WHERE id = 2;\n"
    t.check(tr.same_output(tr.db(t, g, q).out, tr.sqlite(t, g, q).out), "./db reads sqlite3's INT PRIMARY KEY table")
    r = tr.db(t, g, "INSERT INTO k VALUES (3, 'three');\n", check=False)
    t.check(r.rc != 0 and "read-only" in r.err, f"an INT PRIMARY KEY table from sqlite3 must refuse writes, got:\n{r}")
    tr.integrity(t, g)


def unparsable(t, tr):
    """A table whose CREATE text this engine cannot parse is listed, and
    refused with a message that says so once."""
    g = tr.path(t)
    tr.sqlite(t, g, "CREATE TABLE gen(a INTEGER, b INTEGER GENERATED ALWAYS AS (a * 2) VIRTUAL);\n"
                    "INSERT INTO gen(a) VALUES (1);\n")
    t.check(tr.db(t, g, ".tables\n").out.split() == ["gen"], "a table ./db cannot parse is still listed")
    for sql in ["SELECT * FROM gen;", "INSERT INTO gen(a) VALUES (2);", "CREATE INDEX gen_a ON gen(a);"]:
        r = tr.db(t, g, sql + "\n", check=False)
        t.check(r.rc != 0 and r.err.strip() == "Error: table gen uses SQL this engine cannot parse",
                f"{sql} on a table ./db cannot parse should say why once, got:\n{r}")
    tr.integrity(t, g)
