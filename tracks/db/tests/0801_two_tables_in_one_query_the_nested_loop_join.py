"""08.01 Two tables in one query: the nested loop join

FROM names several tables, joined by commas, JOIN, INNER JOIN or CROSS JOIN, with or
without ON, up to 64 of them. Names bind across the tables as sqlite3 binds them
(q.c, a bare c, rowid per table, * and x.*, ORDER BY a result column's name), and
the join's answers are sqlite3's: every multi-row query has an ORDER BY that fixes
the order (sqlite3 picks its own join order), or the rows are compared sorted.
Every query also runs with a two-page cache, so pages are evicted in the middle of
a join, and must give the same answer. Where sqlite3 also reads the tables in the
written order (CROSS JOIN, automatic indexes off, sent to sqlite3 only) the rows
come out in the same order and EXPLAIN QUERY PLAN prints the same lines. Errors are
sqlite3's; what 08.01 does not have is refused by name. Then the one-table core is
untouched: 05.03's test (its plans, and the sqllogictest slice), and the slice
again with joins no longer skipped.
"""

import os

from harness.core import load_test

SHOP = """CREATE TABLE customers(id INTEGER PRIMARY KEY, name TEXT, city TEXT);
CREATE TABLE orders(id INTEGER PRIMARY KEY, customer_id INTEGER, total INTEGER);
CREATE TABLE cities(name TEXT, country TEXT);
CREATE TABLE countries(code TEXT, name TEXT);
CREATE TABLE blank(x, y);
CREATE INDEX customers_city ON customers(city);
INSERT INTO customers VALUES (1,'Ada','London'),(2,'Brook','Paris'),(3,'Chen','London'),(4,'Dee','Oslo');
INSERT INTO orders VALUES (10,1,30),(11,3,15),(12,1,50),(13,2,20),(14,3,5),(15,NULL,40);
INSERT INTO cities VALUES ('London','UK'),('Paris','FR'),('Oslo','NO'),('Rome','IT');
INSERT INTO countries VALUES ('UK','United Kingdom'),('FR','France'),('NO','Norway');
CREATE TABLE r(rowid, v);
INSERT INTO r VALUES (100, 'r100'), (200, 'r200');
CREATE TABLE jw(left, inner, cross);
INSERT INTO jw VALUES (1, 2, 3), (4, 1, 6);
"""

# one column of no affinity holding 1 as an integer, text, real and blob, against
# INTEGER, REAL and no-affinity columns; NULL keys on both sides; an empty table
MIXED = """CREATE TABLE a(id INTEGER PRIMARY KEY, x, y TEXT);
CREATE TABLE b(id INTEGER PRIMARY KEY, x INTEGER, z TEXT);
CREATE TABLE c(k REAL, w);
CREATE TABLE m(v);
CREATE TABLE e(x, y);
INSERT INTO a VALUES (1, 1, 'one'), (2, '1', 'text one'), (3, 1.0, 'real one'), (4, x'31', 'blob'),
  (5, NULL, 'null'), (6, 2, 'two'), (7, 'a', 'b1'), (8, 1.5, 'b2');
INSERT INTO b VALUES (10, 1, 'b1'), (11, 2, 'b2'), (12, NULL, 'bnull'), (13, '1', 'one'), (14, 3, 'b3'),
  (15, 'a', 'text a'), (16, x'31', 'blob');
INSERT INTO c VALUES (1, 'c1'), (2.5, 'c2.5'), ('1', 'ctext'), (NULL, 'cnull'), (1.5, 'c1.5');
INSERT INTO m VALUES (1), ('1'), (1.0), (x'31'), (NULL), ('a'), (2), (NULL);
"""

JOIN = "customers c JOIN orders o ON o.customer_id = c.id"

SHOP_QUERIES = [
    # the ways of writing a join of two tables, with and without ON
    "SELECT c.name, o.id, o.total FROM customers c, orders o WHERE o.customer_id = c.id ORDER BY o.id",
    f"SELECT c.name, o.id, o.total FROM {JOIN} ORDER BY o.id",
    "SELECT c.name, o.id FROM customers c INNER JOIN orders o ON o.customer_id = c.id ORDER BY o.id",
    "SELECT c.name, o.id FROM customers c CROSS JOIN orders o ON o.customer_id = c.id ORDER BY o.id",
    "SELECT c.name, o.id FROM customers c, orders o ON o.customer_id = c.id ORDER BY o.id",
    "SELECT c.name, o.id FROM customers c JOIN orders o ORDER BY c.id, o.id",
    "SELECT c.name, o.id FROM customers c CROSS JOIN orders o ORDER BY o.id, c.id",
    "SELECT c.name, o.id FROM customers c INNER JOIN orders o ORDER BY c.id DESC, o.id",
    "SELECT c.name, o.id FROM customers c, orders o ORDER BY c.id, o.id",
    "SELECT c.name, o.id FROM customers c join orders o on o.customer_id = c.id order by o.id",
    # ON and WHERE mean the same for an inner join, wherever the term is
    f"SELECT c.name, o.id FROM {JOIN} WHERE c.city = 'London' ORDER BY o.id",
    "SELECT c.name, o.id FROM customers c JOIN orders o ON o.customer_id = c.id AND c.city = 'London' ORDER BY o.id",
    "SELECT c.name, o.id FROM customers c JOIN orders o ON c.city = 'London' WHERE o.customer_id = c.id ORDER BY o.id",
    f"SELECT c.name, o.id FROM {JOIN} WHERE o.total > 10 AND c.id > 1 AND 1 = 1 ORDER BY o.id",
    f"SELECT c.name, o.id FROM {JOIN} WHERE c.city = 'London' OR o.total > 25 ORDER BY o.id",
    f"SELECT c.name, o.id FROM {JOIN} WHERE NOT (c.city = 'London') ORDER BY o.id",
    "SELECT c.name, o.id FROM customers c JOIN orders o ON 1 WHERE o.total = 20 ORDER BY c.id",
    "SELECT c.name, o.id FROM customers c JOIN orders o ON 0 ORDER BY c.id",
    "SELECT c.name, o.id FROM customers c JOIN orders o ON NULL ORDER BY c.id",
    "SELECT c.name, o.id FROM customers c JOIN orders o ON o.total > 1000 ORDER BY c.id",
    "SELECT c.name, o.id FROM customers c JOIN orders o WHERE c.id = o.customer_id + 0 ORDER BY o.id",
    # item 0 read by its own terms: a rowid lookup, a rowid range, an index lookup
    f"SELECT c.name, o.id FROM {JOIN} WHERE c.id = 3 ORDER BY o.id",
    f"SELECT c.name, o.id FROM {JOIN} WHERE c.id BETWEEN 2 AND 3 ORDER BY o.id",
    f"SELECT c.name, o.id FROM {JOIN} WHERE c.id > 1 AND c.id < 4 ORDER BY o.id",
    f"SELECT c.name, o.id FROM {JOIN} WHERE c.city = 'London' AND o.total > 10 ORDER BY o.id",
    f"SELECT c.name, o.id FROM {JOIN} WHERE c.city > 'M' ORDER BY o.id",
    # three and four tables; an ON naming a table to its right; terms at every level
    "SELECT c.name, o.id, ci.country FROM customers c JOIN orders o ON o.customer_id = c.id "
    "JOIN cities ci ON ci.name = c.city ORDER BY o.id",
    "SELECT c.name, o.id, ci.country, co.name FROM customers c JOIN orders o ON o.customer_id = c.id "
    "JOIN cities ci ON ci.name = c.city JOIN countries co ON co.code = ci.country ORDER BY o.id",
    "SELECT c.name, o.id, ci.country FROM customers c JOIN orders o ON ci.name = c.city "
    "JOIN cities ci ON o.customer_id = c.id ORDER BY o.id",
    "SELECT c.name, o.id, ci.country, co.name FROM customers c, orders o, cities ci, countries co "
    "WHERE o.customer_id = c.id AND ci.name = c.city AND co.code = ci.country AND c.id > 1 "
    "AND o.total > 5 AND co.name <> 'Norway' AND 2 > 1 ORDER BY o.id",
    "SELECT ci.name, c.name, o.id FROM cities ci JOIN customers c ON c.city = ci.name "
    "JOIN orders o ON o.customer_id = c.id AND o.total < ci.rowid * 20 ORDER BY o.id",
    "SELECT c.name, ci.name, co.code FROM customers c CROSS JOIN cities ci CROSS JOIN countries co "
    "WHERE ci.country = co.code AND c.city <> ci.name ORDER BY c.id, ci.rowid, co.rowid",
    "SELECT co.name, ci.name, c.name, o.total FROM countries co, cities ci, customers c, orders o "
    "WHERE co.code = ci.country AND (ci.name = c.city OR o.total = 40) AND o.customer_id IS NOT c.id "
    "ORDER BY co.rowid, ci.rowid, c.id, o.id",
    # self-joins with aliases, and one side unaliased
    "SELECT a.name, b.name FROM customers a JOIN customers b ON a.city = b.city AND a.id < b.id ORDER BY a.id, b.id",
    "SELECT a.name, b.name FROM customers a, customers b WHERE a.id <> b.id ORDER BY a.id, b.id",
    "SELECT customers.name, c2.name FROM customers, customers AS c2 WHERE customers.id = c2.id + 1 ORDER BY c2.id",
    "SELECT x.id, y.id, z.id FROM orders x, orders y, orders z WHERE x.total + y.total = z.total "
    "ORDER BY x.id, y.id, z.id",
    # *, x.* and both
    f"SELECT * FROM {JOIN} ORDER BY o.id",
    f"SELECT o.*, c.name FROM {JOIN} ORDER BY o.id",
    f"SELECT c.*, o.* FROM {JOIN} ORDER BY o.id",
    f"SELECT o.*, * FROM {JOIN} ORDER BY o.id",
    f"SELECT *, c.name, o.total * 2 FROM {JOIN} ORDER BY o.id",
    "SELECT C.*, O.* FROM customers c JOIN orders o ON o.customer_id = c.id ORDER BY o.id",
    "SELECT customers.*, orders.* FROM customers, orders WHERE customer_id = customers.id ORDER BY orders.id",
    "SELECT * FROM customers JOIN cities ON cities.name = customers.city JOIN countries ON code = country "
    "ORDER BY customers.id",
    "SELECT a.* FROM customers a JOIN customers b ON a.id = b.id ORDER BY 1",
    # names: qualified, bare where only one table has them, any case, quoted, join words
    "SELECT name, total, city FROM customers JOIN orders ON customer_id = customers.id ORDER BY orders.id",
    "SELECT C.NAME, O.Total FROM customers c JOIN orders o ON O.customer_id = C.id ORDER BY o.ID",
    "SELECT customers.name, orders.total FROM customers, orders WHERE orders.customer_id = customers.id "
    "ORDER BY orders.id",
    "SELECT \"my c\".name, o.id FROM customers AS \"my c\" JOIN orders o ON o.customer_id = \"my c\".id ORDER BY o.id",
    "SELECT right.id, left.name FROM customers AS left JOIN orders AS right ON right.customer_id = left.id ORDER BY 1",
    "SELECT jw.left, jw.cross, c.name FROM jw, customers c WHERE jw.inner = c.id ORDER BY 1",
    "SELECT left, cross FROM jw ORDER BY 1",
    # rowid, oid and _rowid_ of each table; a table whose column is called rowid
    f"SELECT c.rowid, o.oid, o._rowid_, c._rowid_ FROM {JOIN} ORDER BY 2",
    f"SELECT c.name, o.id FROM {JOIN} WHERE c.rowid = 2 ORDER BY o.id",
    f"SELECT c.name, o.id FROM {JOIN} WHERE c.rowid > 1 AND o.rowid < 14 ORDER BY o.id",
    "SELECT c.name, o.id FROM customers c JOIN orders o ON c.rowid = o.customer_id ORDER BY o.rowid",
    "SELECT cities.rowid, cities.name, c.name FROM cities, customers c WHERE c.city = cities.name "
    "ORDER BY cities.rowid, c.id",
    "SELECT ci.oid + c.rowid, ci.name FROM cities ci JOIN customers c ON c.city = ci.name ORDER BY 1, 2",
    "SELECT r.rowid, v, c.name FROM r, customers c WHERE c.id < 3 ORDER BY r.rowid, c.id",
    "SELECT rowid, c.name FROM r, customers c WHERE c.id = 1 ORDER BY 1",
    # ORDER BY over a join: a number, an alias, a column a * stands for, an expression
    f"SELECT c.name, o.total FROM {JOIN} ORDER BY 2 DESC, 1",
    f"SELECT c.name AS who, o.total AS t FROM {JOIN} ORDER BY t DESC, who",
    f"SELECT o.total AS name, c.name FROM {JOIN} ORDER BY name",
    f"SELECT c.name, o.total FROM {JOIN} ORDER BY total, name",
    f"SELECT * FROM {JOIN} ORDER BY id DESC, total",
    f"SELECT *, o.total AS id FROM {JOIN} ORDER BY id DESC, o.id",
    f"SELECT o.total AS id, * FROM {JOIN} ORDER BY id, o.id",
    f"SELECT c.name, o.total FROM {JOIN} ORDER BY o.total * 2 - c.id, o.id",
    f"SELECT c.name, o.total FROM {JOIN} ORDER BY c.city DESC, o.total",
    # LIMIT and OFFSET over a join
    f"SELECT c.name, o.id FROM {JOIN} ORDER BY o.total DESC, o.id LIMIT 3",
    f"SELECT c.name, o.id FROM {JOIN} ORDER BY o.id LIMIT 2 OFFSET 1",
    f"SELECT c.name, o.id FROM {JOIN} ORDER BY o.id LIMIT 1, 2",
    f"SELECT c.name, o.id FROM {JOIN} ORDER BY o.id LIMIT 0",
    f"SELECT c.name, o.id FROM {JOIN} ORDER BY o.id LIMIT -1 OFFSET 3",
    "SELECT c.name, o.id FROM customers c, orders o ORDER BY o.id, c.id LIMIT 5 OFFSET 7",
    # an empty table on either side or in the middle; a NULL key never joins
    "SELECT * FROM customers, blank",
    "SELECT * FROM blank, customers",
    "SELECT c.name FROM customers c JOIN blank n ON 1 JOIN orders o ON 1",
    "SELECT * FROM blank a JOIN blank b ON a.x = b.x",
    f"SELECT o.id FROM {JOIN} WHERE o.customer_id IS NULL",
    "SELECT o.id, c.name FROM orders o JOIN customers c ON o.customer_id IS c.id ORDER BY o.id",
    # 08.01 adds only the join: one table still runs the core's plan
    "SELECT * FROM customers c WHERE c.city = 'London' ORDER BY c.name",
    "SELECT c.* FROM customers c ORDER BY 2",
    "SELECT customers.name FROM customers WHERE customers.rowid > 2",
    "SELECT CUSTOMERS.* FROM customers ORDER BY 1",
    # sqlite_master answers to that name too (the catalog calls it sqlite_schema)
    "SELECT sqlite_master.type, sqlite_master.name FROM sqlite_master ORDER BY 2",
    "SELECT sqlite_master.* FROM sqlite_master WHERE name = 'jw'",
    "SELECT sqlite_schema.name FROM sqlite_master WHERE type = 'index'",
    "SELECT s.name, c.name FROM sqlite_master s, customers c WHERE s.type = 'index' AND c.id < 3 ORDER BY c.id",
    "SELECT sqlite_master.tbl_name, c.name FROM sqlite_master JOIN customers c ON c.id = sqlite_master.rowid "
    "ORDER BY c.id",
]

MIXED_QUERIES = [
    "SELECT a.id, b.id FROM a JOIN b ON a.x = b.x ORDER BY a.id, b.id",
    "SELECT a.id, b.id FROM a JOIN b ON b.x = a.x ORDER BY a.id, b.id",
    "SELECT a.id, b.id FROM a, b WHERE a.x IS b.x ORDER BY a.id, b.id",
    "SELECT a.id, b.id, typeof(a.x), typeof(b.x) FROM a JOIN b ON a.x < b.x ORDER BY a.id, b.id",
    "SELECT a.id, b.id FROM a JOIN b ON a.x >= b.x ORDER BY a.id, b.id",
    "SELECT a.id, b.id FROM a JOIN b ON a.x = b.x || '' ORDER BY a.id, b.id",
    "SELECT a.id, b.id FROM a JOIN b ON a.x + 0 = b.x ORDER BY a.id, b.id",
    "SELECT a.id, b.id FROM a JOIN b ON a.y = b.z ORDER BY a.id, b.id",
    "SELECT a.id, c.rowid, c.k FROM a JOIN c ON a.x = c.k ORDER BY a.id, c.rowid",
    "SELECT b.id, c.rowid FROM b JOIN c ON c.k = b.x ORDER BY b.id, c.rowid",
    "SELECT a.id, c.rowid FROM a JOIN c ON a.x > c.k ORDER BY a.id, c.rowid",
    "SELECT m1.rowid, m2.rowid FROM m m1 JOIN m m2 ON m1.v = m2.v ORDER BY 1, 2",
    "SELECT m1.rowid, m2.rowid FROM m m1, m m2 WHERE m1.v IS m2.v ORDER BY 1, 2",
    "SELECT m1.rowid, m2.rowid FROM m m1, m m2 WHERE m1.v < m2.v ORDER BY 1, 2",
    "SELECT m.rowid, a.id FROM m JOIN a ON a.x = m.v ORDER BY 1, 2",
    "SELECT m.rowid, b.id FROM m JOIN b ON b.x = m.v ORDER BY 1, 2",
    "SELECT m.rowid, c.rowid FROM m JOIN c ON c.k = m.v ORDER BY 1, 2",
    "SELECT a.id, b.id, c.rowid FROM a JOIN b ON a.x = b.x JOIN c ON c.k = b.x ORDER BY 1, 2, 3",
    "SELECT * FROM a, e",
    "SELECT * FROM e, a",
    "SELECT a.id FROM a JOIN e ON 1 JOIN b ON 1",
    "SELECT a.id FROM a JOIN e ON a.x = e.x",
    "SELECT * FROM a JOIN b ON a.id + 9 = b.id ORDER BY a.id",
    "SELECT a.*, b.* FROM a JOIN b ON a.x IS NULL AND b.x IS NULL",
]

# What 08.01 does not build: refused by name (sqlite3 runs each of them).
REFUSED = [
    ("SELECT * FROM customers LEFT JOIN orders ON 1", "LEFT JOIN is not supported"),
    ("SELECT * FROM customers left outer join orders ON 1", "LEFT JOIN is not supported"),
    ("SELECT * FROM customers c JOIN orders o ON 1 LEFT JOIN cities ON 1", "LEFT JOIN is not supported"),
    ("SELECT * FROM customers NATURAL JOIN orders", "NATURAL JOIN is not supported"),
    ("SELECT * FROM customers NATURAL LEFT JOIN orders", "NATURAL JOIN is not supported"),
    ("SELECT * FROM customers RIGHT JOIN orders ON 1", "RIGHT JOIN is not supported"),
    ("SELECT * FROM customers RIGHT OUTER JOIN orders ON 1", "RIGHT JOIN is not supported"),
    ("SELECT * FROM customers FULL JOIN orders ON 1", "FULL JOIN is not supported"),
    ("SELECT * FROM customers FULL OUTER JOIN orders ON 1", "FULL JOIN is not supported"),
    ("SELECT * FROM customers JOIN orders USING (id)", "USING is not supported"),
    ("SELECT * FROM (SELECT 1)", "subqueries in FROM are not supported"),
    ("SELECT * FROM customers JOIN (SELECT 1)", "subqueries in FROM are not supported"),
    ("SELECT * FROM customers JOIN (orders JOIN cities)", "parenthesised joins are not supported"),
    ("SELECT count(*) FROM customers, orders", "aggregate functions are not supported: count"),
    ("SELECT DISTINCT c.city FROM customers c, orders o", "SELECT DISTINCT is not supported"),
    ("SELECT c.city FROM customers c, orders o GROUP BY c.city", "GROUP BY is not supported"),
    ("SELECT * FROM customers c, orders o WHERE c.id IN (SELECT 1)", "subqueries are not supported"),
    ("UPDATE customers SET name = name FROM orders WHERE orders.customer_id = customers.id",
     "UPDATE ... FROM is not supported"),
]

# Errors in both engines (errors_alike).
ERRORS = [
    "SELECT * FROM customers JOIN nosuch ON 1",
    "SELECT * FROM nosuch, customers",
    "SELECT id FROM customers JOIN orders ON 1",
    "SELECT c.name FROM customers c JOIN orders o ON id = 1",
    "SELECT x.id FROM customers c JOIN orders o",
    "SELECT customers.id FROM customers c JOIN orders o",
    "SELECT c.nope FROM customers c JOIN orders o",
    "SELECT nope FROM customers c, orders o",
    "SELECT * FROM customers JOIN customers",
    "SELECT customers.* FROM customers JOIN customers",
    "SELECT customers.id FROM customers, customers",
    "SELECT a.id FROM customers a JOIN orders a",
    "SELECT * FROM customers a JOIN orders a",
    "SELECT rowid FROM customers, orders",
    "SELECT oid FROM r, customers",
    "SELECT * FROM customers c, orders o WHERE _rowid_ = 1",
    "SELECT x.* FROM customers, orders",
    "SELECT customers.* FROM customers AS c2, orders",
    "SELECT * FROM customers c JOIN orders o ON nope = 1",
    "SELECT * FROM customers c JOIN orders o ON x.y = 1",
    "SELECT c.name FROM customers c JOIN orders o ORDER BY id",
    "SELECT c.name FROM customers c JOIN orders o ORDER BY 2",
    "SELECT c.name FROM customers c JOIN orders o ORDER BY 0",
    "SELECT c.name, o.id FROM customers c JOIN orders o ORDER BY 1, 3",
    "SELECT c.name FROM customers c JOIN orders o ORDER BY nope",
    "SELECT * FROM customers c JOIN orders o LIMIT c.id",
    "SELECT * FROM customers ON 1",
    "SELECT * FROM customers c ON c.id = 1, orders",
    "SELECT * FROM customers USING (id)",
    "SELECT * FROM customers OUTER JOIN orders",
    "SELECT * FROM customers INNER OUTER JOIN orders",
    "SELECT * FROM customers LEFT INNER JOIN orders",
    "SELECT * FROM customers CROSS LEFT JOIN orders",
    "SELECT * FROM customers LEFT nope JOIN orders",
    "SELECT * FROM customers CROSS orders",
    "SELECT * FROM customers JOIN",
    "SELECT * FROM customers,",
    "SELECT * FROM customers JOIN orders ON",
    "SELECT * FROM customers inner",
    "SELECT * FROM customers JOIN orders ON 1 ON 1",
]

# EXPLAIN QUERY PLAN where sqlite3 must read the tables as written: CROSS JOIN, and no
# automatic index (PRAGMA automatic_index=OFF goes to sqlite3 only), and no term an
# inner table could be looked up by (08.03's), no ORDER BY sqlite3 can skip the sort for.
PLANS = [
    "SELECT * FROM customers CROSS JOIN orders",
    "SELECT * FROM customers AS c CROSS JOIN orders AS o ON o.customer_id = c.id",
    "SELECT * FROM customers AS c CROSS JOIN orders AS o WHERE c.id = 2",
    "SELECT * FROM customers AS c CROSS JOIN orders AS o WHERE c.id > 2",
    "SELECT * FROM customers AS c CROSS JOIN orders AS o WHERE c.id BETWEEN 2 AND 3",
    "SELECT * FROM customers AS c CROSS JOIN orders AS o WHERE c.city = 'London' AND o.total > 10",
    "SELECT * FROM customers AS c CROSS JOIN orders AS o WHERE c.city > 'M'",
    "SELECT * FROM customers AS c CROSS JOIN orders AS o ON o.customer_id = c.id ORDER BY o.total",
    "SELECT * FROM customers c CROSS JOIN orders o CROSS JOIN cities ci ON ci.name = c.city",
    "SELECT * FROM orders o CROSS JOIN cities CROSS JOIN countries co CROSS JOIN blank",
    "SELECT * FROM orders AS x CROSS JOIN orders AS y WHERE x.total = y.total",
    "SELECT * FROM cities CROSS JOIN orders ORDER BY orders.total, cities.name",
]

# The order a nested loop hands rows up in, with no ORDER BY: the outer table's rows in
# rowid order, each with every inner row in rowid order. sqlite3 does the same here
# (CROSS JOIN, no automatic index, no index on these tables).
NESTED_ORDER = [
    "SELECT o.id, ci.name FROM orders o CROSS JOIN cities ci",
    "SELECT ci.name, o.id, co.code FROM cities ci CROSS JOIN orders o CROSS JOIN countries co WHERE o.total > 20",
    "SELECT o.id, ci.name FROM orders o CROSS JOIN cities ci LIMIT 5 OFFSET 2",
    "SELECT x.id, y.id FROM orders x CROSS JOIN orders y ON y.total < x.total",
]

EXPLAIN_TREE = """Sort by o.id
  Filter (ci.name = c.city)
    Join
      Filter ((o.total > 10) AND (o.customer_id = c.id))
        Join
          Filter (c.id > 1)
            Rowid range customers rowid > ?
          Scan orders AS o
      Scan cities AS ci
"""

EXPLAIN_INDEX = """Filter (o.customer_id = c.id)
  Join
    Filter (c.city = 'London')
      Index lookup customers using customers_city (city = ?)
    Scan orders AS o
"""


def files(t, setup):
    """A file for each engine, both holding setup."""
    tr = t.track
    a, b = tr.path(t), tr.path(t)
    tr.db(t, a, setup)
    tr.sqlite(t, b, setup)
    return a, b


def lines(out):
    return "".join(sorted(out.splitlines(keepends=True)))


def compare(t, a, b, sql, theirs_first="", sort=False):
    """sql through ./db on file a, with the default cache and with a two-page cache (pages
    are then evicted in the middle of a join), and through sqlite3 on b, with theirs_first
    before it: the three answers must agree (sorted line by line, with sort)."""
    tr = t.track
    ours = tr.db(t, a, sql).out
    tiny = tr.db(t, a, sql, env={"DB_CACHE_PAGES": "2"}).out
    theirs = tr.sqlite(t, b, theirs_first + sql).out
    if sort:
        ours, tiny, theirs = lines(ours), lines(tiny), lines(theirs)
    if not tr.same_output(ours, theirs):
        la, lb = ours.splitlines(), theirs.splitlines()
        i = next((i for i in range(max(len(la), len(lb)))
                  if i >= len(la) or i >= len(lb) or not tr.same_output(la[i], lb[i])), 0)
        got = la[i] if i < len(la) else "<nothing>"
        want = lb[i] if i < len(lb) else "<nothing>"
        t.check(False, f"./db and sqlite3 disagree at output line {i + 1}:\n  ./db:    {got!r}\n"
                       f"  sqlite3: {want!r}\n--- sql\n{sql[:3000]}")
    t.check(tiny == ours, f"with DB_CACHE_PAGES=2 ./db answers differently:\n{tiny[:1500]}\n--- sql\n{sql[:2000]}")
    return ours


def listing(queries, sep=True):
    return "".join(f"{q};\n" + ("SELECT '--';\n" if sep else "") for q in queries)


def test(t):
    tr = t.track

    a, b = files(t, SHOP)
    compare(t, a, b, listing(SHOP_QUERIES))
    for q in NESTED_ORDER:
        compare(t, a, b, f"{q};\n", theirs_first="PRAGMA automatic_index=OFF;\n")
    compare(t, a, b, "".join(f"EXPLAIN QUERY PLAN {q};\n" for q in PLANS), theirs_first="PRAGMA automatic_index=OFF;\n")
    for q, msg in REFUSED:
        r = tr.db(t, a, f"{q};\n", check=False)
        t.check(r.rc != 0 and f"Error: {msg}" in r.err, f"{q} should be refused with {msg!r}, but:\n{r}")
        tr.sqlite(t, b, f"{q};\n")     # sqlite3 runs it: a feature, not an error
    for q in ERRORS:
        tr.errors_alike(t, SHOP, f"{q};\n")

    # EXPLAIN: a join's two inputs under it, outer side first; each filter as low as it goes
    out = tr.db(t, a, "EXPLAIN SELECT c.name, o.id, ci.country FROM customers c JOIN orders o ON o.customer_id = c.id "
                      "JOIN cities ci ON ci.name = c.city WHERE c.id > 1 AND o.total > 10 ORDER BY o.id;\n").out
    t.check(out == EXPLAIN_TREE, f"EXPLAIN of a three-table join:\n{out}\nexpected:\n{EXPLAIN_TREE}")
    out = tr.db(t, a, f"EXPLAIN SELECT * FROM {JOIN} WHERE c.city = 'London';\n").out
    t.check(out == EXPLAIN_INDEX, f"EXPLAIN of a join whose outer table is read by an index:\n{out}\nexpected:\n{EXPLAIN_INDEX}")

    # mixed types in the join columns, NULL keys, an empty table
    a2, b2 = files(t, MIXED)
    compare(t, a2, b2, listing(MIXED_QUERIES))

    # 64 tables (SQLite's limit), and a 65th
    one = "CREATE TABLE one(v);\nINSERT INTO one VALUES (7);\n"
    a3, b3 = files(t, one)
    compare(t, a3, b3, "SELECT 1 FROM " + ", ".join(["one"] * 64) + ";\n" +
            "SELECT t1.v + t64.v FROM one t1" + "".join(f" JOIN one t{i} ON t{i}.v = t{i - 1}.v" for i in range(2, 65)) +
            ";\n")
    tr.errors_alike(t, one, "SELECT 1 FROM " + ", ".join(["one"] * 65) + ";\n")

    # a table this engine cannot read is refused in a join too; one it cannot write joins
    f = tr.path(t)
    tr.sqlite(t, f, SHOP + "CREATE TABLE w(k PRIMARY KEY, v) WITHOUT ROWID;\nINSERT INTO w VALUES (1, 'w1');\n"
                           "CREATE TABLE u(k UNIQUE, v);\nINSERT INTO u VALUES (1, 'u1'), (3, 'u3');\n")
    r = tr.db(t, f, "SELECT * FROM customers c JOIN w ON w.k = c.id;\n", check=False)
    t.check(r.rc != 0 and "Error: table w uses WITHOUT ROWID" in r.err, f"a WITHOUT ROWID table in a join:\n{r}")
    got = tr.db(t, f, "SELECT c.name, u.v FROM customers c JOIN u ON u.k = c.id ORDER BY c.id;\n").out
    t.check(got == "Ada|u1\nChen|u3\n", f"a join with a read-only table: {got!r}")

    # tables of many pages, with pages evicted mid-join (a two-page cache), and rows whose
    # text spills to overflow pages: the outer row must be kept, not pointed at
    big = ("CREATE TABLE p(id INTEGER PRIMARY KEY, k INTEGER, pad TEXT);\n"
           "CREATE TABLE q(id INTEGER PRIMARY KEY, name TEXT, pad TEXT);\nBEGIN;\n" +
           "".join(f"INSERT INTO p VALUES ({i}, {i * 7 % 300 + 1}, '{'p' * (5000 if i % 500 == 0 else 120)}{i}');\n"
                   for i in range(1, 3001)) +
           "".join(f"INSERT INTO q VALUES ({j}, 'name {j}', '{chr(97 + j % 26) * 200}');\n" for j in range(1, 301)) +
           "COMMIT;\n")
    a4, b4 = files(t, big)
    compare(t, a4, b4, "SELECT p.id, q.name, p.pad FROM p JOIN q ON q.id = p.k;\n", sort=True)
    compare(t, a4, b4, "SELECT p.id, p.pad, q.id, q.pad FROM p, q WHERE p.id % 1000 IN (0, 1);\n", sort=True)
    compare(t, a4, b4, "SELECT p.id, q.name, r.id, r.pad FROM p JOIN q ON q.id = p.k JOIN q AS r ON r.id <= 300 "
                       "WHERE p.id <= 3 OR p.id = 1500;\n", sort=True)
    compare(t, a4, b4, "SELECT q.name, p.id, length(p.pad) FROM q JOIN p ON p.k = q.id WHERE q.id < 4 "
                       "ORDER BY q.name, p.id;\n")
    compare(t, a4, b4, "SELECT p.id, q.id FROM p CROSS JOIN q ON q.id = p.k ORDER BY q.pad, p.pad LIMIT 20;\n")
    r = tr.db(t, a4, "SELECT p.id, p.pad, q.id FROM p, q WHERE p.id % 1000 = 0;\n", env={"DB_CACHE_PAGES": "2", "DB_STATS": "1"})
    st = tr.stats(r.err)
    t.check(st["evictions"] > 100 and len(r.lines()) == 900,
            f"the two-page cache should evict pages mid-join: {st}, {len(r.lines())} rows")

    # the one-table core is untouched: 05.03's test (plans, EXPLAIN, the sqllogictest slice)
    load_test(os.path.join(os.path.dirname(os.path.abspath(__file__)), "0503_choosing_a_plan_and_explain.py")).test(t)
    # and the slice again, with SQL that joins no longer skipped
    tr.sqllogictest(t, have=("join",))
