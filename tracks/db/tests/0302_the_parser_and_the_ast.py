"""03.02 The parser and the AST

Operators group by SQLite's precedence, the SELECT statement's clauses
parse in all their forms, and malformed SQL is an error, not a crash.
"""


def test(t):
    tr = t.track
    exprs = """SELECT 1 + 2 * 3, (1 + 2) * 3, 2 * 3 - 4 / 2, 10 - 4 - 3, 100 / 10 / 5, 2 || 3 + 4;
SELECT 1 < 2 = 1, NOT 0 = 0, NOT 1 AND 0, 1 OR 0 AND 0, (1 OR 0) AND 0, -2 * -3, - - 4;
SELECT 5 BETWEEN 1 AND 10 AND 1, 3 IN (1, 2, 3) = 1, 4 NOT IN (1, 2), NULL IS NULL, 1 IS NOT NULL;
SELECT 7 % 3 * 2, 1 + 2 < 4, 'a' || 'b' = 'ab', 2 + 3 BETWEEN 4 AND 6, 1 = 1 OR 1 / 0;
SELECT NULL ISNULL, 3 NOTNULL, 3 NOT NULL, 'x' LIKE 'X', 'abc' NOT LIKE 'a%';
"""
    tr.both(t, exprs)
    setup = ("CREATE TABLE t(a INTEGER, b TEXT);\n"
             "INSERT INTO t VALUES (1, 'one'), (2, 'two'), (3, 'three'), (4, 'four'), (5, 'five');\n")
    selects = """SELECT a AS x, b y FROM t AS q WHERE q.a > 1 ORDER BY 1 DESC LIMIT 2 OFFSET 1;
SELECT *, a * 10 FROM t WHERE b <> 'two' ORDER BY a LIMIT 1, 2;
SELECT t.* FROM t ORDER BY b;
SELECT b FROM t WHERE (a = 1 OR a = 3) AND NOT b = 'one';
SELECT ALL a FROM t ORDER BY a DESC LIMIT 2;
"""
    tr.both(t, selects, setup)
    for bad in ["SELECT FROM t;", "SELECT 1 +;", "SELECT (1;", "SELECT 1 2;", "SELECT * FROM;",
                "INSERT INTO t VALUES (1,;", "SELECT a FROM t WHERE;", "SELECT a FROM t ORDER a;",
                "CREATE TABLE (a);", "SELECT 1 FROM t LIMIT;"]:
        tr.errors_alike(t, setup, bad + "\n")

    # EXPLAIN shows the tree the parser built, outermost operator first.
    f = tr.path(t)
    tr.db(t, f, setup)
    out = tr.db(t, f, "EXPLAIN SELECT a FROM t WHERE a > 1 ORDER BY b LIMIT 3;\n").out.splitlines()
    names = [line.strip().split(" ")[0] for line in out]
    t.check(names == ["Limit", "Sort", "Filter", "Scan"], f"EXPLAIN printed {out}")
    t.check(out[2].strip() == "Filter (a > 1)", f"the WHERE clause should print back as (a > 1): {out[2]!r}")
