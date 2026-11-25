"""08.06 Subqueries: a query inside a query

A SELECT in parentheses is a value (the first row's, NULL with none), EXISTS (SELECT ...)
is whether it has a row, and x IN (SELECT ...) whether x is one of its values, with
sqlite3's NULL table and affinities, in a result column, WHERE, ON, ORDER BY, LIMIT, and
UPDATE's SET and WHERE, DELETE's WHERE and INSERT's VALUES. A name the subquery's tables
lack is looked for in the queries around it, one and two levels out; the nearest wins and
two in one scope are ambiguous. Every answer is sqlite3's: each query runs in ./db with the
default cache and a two-page one, and in sqlite3, with an ORDER BY that fixes the order
(sqlite3 turns EXISTS into a join and picks its own order). Writes whose subqueries read the
table being written leave what sqlite3 leaves. A subquery that names nothing outside it
runs once (cache hits counted); a correlated one runs per row, and uses an index on its
inner column. Tables of thousands of rows with text on overflow pages, under a two-page
cache, check that nothing a subquery hands back points into an evicted page. Errors are
sqlite3's; what 08.06 leaves out is refused by name. Then the sqllogictest slice with
subqueries no longer skipped, and 300 cases of the fuzzer with subqueries, joins and LEFT
JOINs. Joins and subqueries together: a lookup keyed by a subquery waits for the tables it
reads, and a LEFT JOIN's ON may hold subqueries that read the tables on its left.
"""

import os

SHOP = """CREATE TABLE customers(id INTEGER PRIMARY KEY, name TEXT, city TEXT);
CREATE TABLE orders(id INTEGER PRIMARY KEY, customer_id INTEGER, total INTEGER);
INSERT INTO customers VALUES (1,'Ada','London'),(2,'Brook','Paris'),(3,'Chen','London'),(4,'Dee','Oslo');
INSERT INTO orders VALUES (10,1,30),(11,3,15),(12,1,50),(13,2,20),(14,3,5),(15,NULL,40);
CREATE TABLE cities(name TEXT, country TEXT);
INSERT INTO cities VALUES ('London','UK'),('Paris','FR'),('Oslo','NO'),('Rome','IT');
CREATE TABLE blank(x, y);
CREATE TABLE ids(v);
INSERT INTO ids VALUES (1), (3);
CREATE TABLE ix(id INTEGER PRIMARY KEY, customer_id INTEGER, total INTEGER);
INSERT INTO ix SELECT * FROM orders;
CREATE INDEX ix_customer ON ix(customer_id);
"""
# ./db has no INSERT ... SELECT: the rows of ix written out
SHOP = SHOP.replace("INSERT INTO ix SELECT * FROM orders;",
                    "INSERT INTO ix VALUES (10,1,30),(11,3,15),(12,1,50),(13,2,20),(14,3,5),(15,NULL,40);")

C = "customers c"
SHOP_QUERIES = [
    # the three kinds, as the lesson shows them
    "SELECT name FROM customers WHERE id IN (SELECT customer_id FROM orders) ORDER BY id",
    "SELECT name FROM customers WHERE id NOT IN (SELECT customer_id FROM orders) ORDER BY id",
    "SELECT name FROM customers WHERE id NOT IN (SELECT customer_id FROM orders WHERE customer_id IS NOT NULL) ORDER BY id",
    f"SELECT name FROM {C} WHERE EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.id) ORDER BY id",
    f"SELECT name FROM {C} WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.id) ORDER BY id",
    f"SELECT name, (SELECT total FROM orders o WHERE o.customer_id = c.id ORDER BY total DESC LIMIT 1) FROM {C} ORDER BY id",
    "SELECT id, total, (SELECT name FROM customers WHERE id = customer_id) FROM orders ORDER BY id",
    "SELECT id, id IN (SELECT customer_id FROM orders), id NOT IN (SELECT customer_id FROM orders) FROM customers ORDER BY id",
    # scalar: no row is NULL; several rows give the first, where the first is fixed
    "SELECT (SELECT name FROM customers WHERE id = 3), (SELECT name FROM customers WHERE id = 9)",
    "SELECT (SELECT total FROM orders ORDER BY total LIMIT 1), (SELECT total FROM orders ORDER BY total DESC)",
    "SELECT (SELECT id FROM orders ORDER BY id), (SELECT id FROM orders ORDER BY id DESC), (SELECT id FROM orders WHERE 0)",
    "SELECT (SELECT total FROM orders ORDER BY total LIMIT 1 OFFSET 2), (SELECT total FROM orders ORDER BY total LIMIT 5 OFFSET 1), "
    "(SELECT total FROM orders LIMIT 0), (SELECT total FROM orders ORDER BY total LIMIT -1 OFFSET 5)",
    "SELECT (SELECT NULL) IS NULL, typeof((SELECT 1.5)), typeof((SELECT 'x')), typeof((SELECT x'31')), (SELECT x'31')",
    "SELECT -(SELECT 5), NOT (SELECT 0), (SELECT 2) * (SELECT 3), (SELECT 'a') || (SELECT 'b'), (SELECT 5) BETWEEN 1 AND (SELECT 9)",
    "SELECT (SELECT (SELECT (SELECT 7)))",
    "SELECT id FROM customers WHERE id = (SELECT customer_id FROM orders WHERE id = 13)",
    "SELECT id FROM customers WHERE id = (SELECT customer_id FROM orders WHERE id = 15)",
    "SELECT id FROM customers WHERE id = (SELECT customer_id FROM orders WHERE id = 99)",
    "SELECT id FROM customers WHERE city = (SELECT city FROM customers WHERE id = 3) ORDER BY id",
    "SELECT id FROM customers WHERE (SELECT city FROM customers WHERE id = 3) = city ORDER BY id",
    "SELECT id FROM customers WHERE id > (SELECT customer_id FROM orders WHERE id = 13) ORDER BY id",
    "SELECT id FROM customers WHERE id BETWEEN (SELECT 2) AND (SELECT customer_id FROM orders WHERE id = 11) ORDER BY id",
    "SELECT id FROM orders WHERE customer_id = (SELECT id FROM customers WHERE name = 'Chen') ORDER BY id",
    "SELECT id FROM ix WHERE customer_id = (SELECT id FROM customers WHERE name = 'Chen') ORDER BY id",
    "SELECT id FROM ix WHERE customer_id > (SELECT id FROM customers WHERE name = 'Ada') ORDER BY id",
    # EXISTS and NOT EXISTS, correlated and not, on empty and non-empty tables
    "SELECT EXISTS (SELECT 1 FROM orders), EXISTS (SELECT 1 FROM blank), NOT EXISTS (SELECT 1 FROM blank), "
    "EXISTS (SELECT NULL), EXISTS (SELECT 1 FROM orders LIMIT 0), EXISTS (SELECT 1, 2, 3)",
    "SELECT name FROM customers WHERE EXISTS (SELECT 1 FROM blank) ORDER BY id",
    "SELECT name FROM customers WHERE NOT EXISTS (SELECT 1 FROM blank) ORDER BY id",
    "SELECT name FROM customers WHERE EXISTS (SELECT 1 FROM orders) ORDER BY id",
    f"SELECT name FROM {C} WHERE EXISTS (SELECT 1 FROM blank WHERE blank.x = c.id) ORDER BY id",
    f"SELECT name FROM {C} WHERE NOT EXISTS (SELECT 1 FROM blank WHERE blank.x = c.id) ORDER BY id",
    f"SELECT c.id, EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.id AND o.total > 25), "
    f"NOT EXISTS (SELECT * FROM orders o WHERE o.customer_id = c.id) FROM {C} ORDER BY 1",
    f"SELECT c.id FROM {C} WHERE c.id > 1 AND EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.id) OR c.id = 4 ORDER BY 1",
    f"SELECT c.id FROM {C} WHERE c.id = 4 OR EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.id AND o.total < 10) ORDER BY 1",
    # IN: the subquery's rows as a set; an ORDER BY and LIMIT inside choose which rows
    "SELECT name FROM customers WHERE id IN (SELECT customer_id FROM orders ORDER BY total DESC LIMIT 2) ORDER BY id",
    "SELECT name FROM customers WHERE id IN (SELECT customer_id FROM orders WHERE total > 1000) ORDER BY id",
    "SELECT name FROM customers WHERE id NOT IN (SELECT customer_id FROM orders WHERE total > 1000) ORDER BY id",
    "SELECT name FROM customers WHERE id IN (1, (SELECT 2), (SELECT id FROM customers WHERE name = 'Dee')) ORDER BY id",
    "SELECT name FROM customers WHERE city IN (SELECT name FROM cities WHERE country <> 'UK') ORDER BY id",
    "SELECT name FROM cities WHERE name NOT IN (SELECT city FROM customers) ORDER BY name",
    "SELECT 1 WHERE (SELECT 1) IN (SELECT 1) AND (SELECT 2) NOT IN (SELECT 1)",
    "SELECT (SELECT id FROM customers ORDER BY id) IN (SELECT customer_id FROM orders)",
    f"SELECT c.id FROM {C} WHERE c.id IN (SELECT o.customer_id FROM orders o WHERE o.total > c.id * 10) ORDER BY 1",
    f"SELECT c.id, c.city IN (SELECT ci.name FROM cities ci WHERE ci.country = 'UK' OR c.id = 4) FROM {C} ORDER BY 1",
    # correlation: one level out, two levels out
    f"SELECT c.name, (SELECT (SELECT c.name || '/' || o.id || '/' || c3.city FROM customers c3 WHERE c3.id = o.customer_id) "
    f"FROM orders o WHERE o.customer_id = c.id ORDER BY o.id LIMIT 1) FROM {C} ORDER BY c.id",
    f"SELECT c.name FROM {C} WHERE EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.id AND EXISTS "
    f"(SELECT 1 FROM customers c2 WHERE c2.city = c.city AND c2.id <> c.id)) ORDER BY c.id",
    "SELECT a.id, (SELECT b.id FROM customers b WHERE b.id = (SELECT c.id FROM customers c WHERE c.id = a.id + 1)) "
    "FROM customers a ORDER BY 1",
    "SELECT a.id FROM customers a WHERE a.id = (SELECT b.id FROM customers b WHERE b.id = a.id AND b.id IN "
    "(SELECT c.id FROM customers c WHERE c.id = a.id AND c.id = b.id)) ORDER BY 1",
    "SELECT o.id, (SELECT (SELECT ci.country FROM cities ci WHERE ci.name = c.city AND o.total > 10) "
    "FROM customers c WHERE c.id = o.customer_id) FROM orders o ORDER BY o.id",
    # the same table inside and outside, under aliases; and with no alias outside
    "SELECT x.name, (SELECT y.name FROM customers y WHERE y.id = x.id + 1) FROM customers x ORDER BY x.id",
    "SELECT name FROM customers WHERE EXISTS (SELECT 1 FROM customers c WHERE c.id = customers.id + 2) ORDER BY id",
    "SELECT name FROM customers WHERE id IN (SELECT customers.id FROM customers WHERE city = 'London') ORDER BY id",
    # an inner name shadows an outer one; a name only the outer table has binds there
    "SELECT name, (SELECT name FROM customers WHERE id = 1) FROM customers ORDER BY id",
    "SELECT id, (SELECT id FROM orders WHERE total = 50) FROM customers ORDER BY id",
    "SELECT id, (SELECT name FROM orders WHERE total = 50) FROM customers ORDER BY id",
    "SELECT id, (SELECT total FROM orders WHERE customer_id = id) FROM customers ORDER BY id",
    "SELECT o.id, (SELECT rowid FROM customers WHERE id = o.customer_id) FROM orders o ORDER BY o.id",
    f"SELECT c.id, (SELECT name) FROM {C} ORDER BY c.id",
    f"SELECT c.id, (SELECT rowid), (SELECT c.rowid FROM orders LIMIT 1) FROM {C} ORDER BY c.id",
    "SELECT o.id, (SELECT oid + o.oid FROM customers WHERE id = 1) FROM orders o ORDER BY o.id",
    # an outer name used only in the inner select list, or only in its ORDER BY
    f"SELECT c.id, (SELECT c.name FROM orders LIMIT 1) FROM {C} ORDER BY c.id",
    f"SELECT c.id, (SELECT c.city FROM orders o WHERE o.customer_id = c.id ORDER BY c.name LIMIT 1) FROM {C} ORDER BY 1",
    f"SELECT c.id, (SELECT total FROM orders ORDER BY abs(total - c.id * 10), id LIMIT 1) FROM {C} ORDER BY c.id",
    f"SELECT c.id, (SELECT o.id FROM orders o ORDER BY o.total * c.id DESC, o.id LIMIT 1) FROM {C} ORDER BY 1",
    # in a join: in the result, in ON, in WHERE; a correlated ON
    "SELECT c.id, o.id, (SELECT total FROM orders WHERE id = o.id) FROM customers c JOIN orders o ON o.customer_id = c.id ORDER BY 2",
    "SELECT c.id, o.id FROM customers c JOIN orders o ON o.customer_id = c.id AND o.total = "
    "(SELECT total FROM orders o3 WHERE o3.customer_id = c.id ORDER BY total DESC LIMIT 1) ORDER BY 2",
    "SELECT c.id, o.id FROM customers c JOIN orders o ON o.customer_id IN (SELECT id FROM customers WHERE city = c.city) ORDER BY 1, 2",
    "SELECT c.id, o.id, ci.country FROM customers c, orders o, cities ci WHERE o.customer_id = c.id AND ci.name = c.city "
    "AND o.total > (SELECT total FROM orders WHERE id = 14) AND EXISTS (SELECT 1 FROM cities WHERE cities.country = ci.country) "
    "ORDER BY 2",
    "SELECT c.id, (SELECT id FROM orders WHERE total = 50) FROM customers c JOIN orders o ON o.customer_id = c.id ORDER BY 1, 2",
    # a name two tables outside share, but one inside has: the inside one, no ambiguity
    "SELECT c.id, o.id, (SELECT id FROM customers WHERE id = 2) FROM customers c JOIN orders o ON o.customer_id = c.id ORDER BY 2",
    "SELECT c.id, o.id FROM customers c, orders o WHERE (SELECT c.id + o.id) = 11 ORDER BY 1, 2",
    "SELECT c.rowid, o.id FROM customers c JOIN orders o ON o.customer_id = c.id WHERE (SELECT c.rowid) > 1 ORDER BY 2",
    # ORDER BY a subquery
    f"SELECT c.id FROM {C} ORDER BY (SELECT total FROM orders WHERE customer_id = c.id ORDER BY total LIMIT 1), c.id",
    f"SELECT c.id FROM {C} ORDER BY EXISTS (SELECT 1 FROM orders WHERE customer_id = c.id), c.id DESC",
    f"SELECT c.id, c.name FROM {C} ORDER BY c.id IN (SELECT customer_id FROM orders WHERE total > 25), c.name",
    "SELECT c.id, o.id FROM customers c JOIN orders o ON o.customer_id = c.id ORDER BY (SELECT o.total + c.id), o.id",
    # LIMIT and OFFSET from a subquery
    "SELECT name FROM customers ORDER BY id LIMIT (SELECT 2)",
    "SELECT name FROM customers ORDER BY id LIMIT (SELECT 2) OFFSET (SELECT customer_id FROM orders WHERE id = 10)",
    # an index lookup inside a correlated subquery, keyed by the outer row
    f"SELECT c.id, (SELECT ix.id FROM ix WHERE ix.customer_id = c.id ORDER BY ix.id DESC LIMIT 1) FROM {C} ORDER BY 1",
    f"SELECT c.id FROM {C} WHERE EXISTS (SELECT 1 FROM ix WHERE ix.customer_id = c.id AND ix.total > 25) ORDER BY 1",
    f"SELECT c.id, (SELECT ix.id FROM ix WHERE ix.customer_id > c.id ORDER BY ix.id LIMIT 1) FROM {C} ORDER BY 1",
    "SELECT o.id, (SELECT name FROM customers WHERE rowid = o.customer_id) FROM orders o ORDER BY 1",
]

# Joins (08.01-08.03) and subqueries together: a lookup for an inner table keyed by a subquery
# (only once the tables the subquery reads are in the row), a subquery's own join whose ON
# compares a column of the query outside (a constant there, never the inner table's column),
# a LEFT JOIN's ON holding subqueries that read only the tables on its left.
JOIN_QUERIES = [
    'SELECT o0.id, c.id FROM orders o0, customers c WHERE EXISTS (SELECT 1 FROM orders o JOIN customers x ON c.id = 2 WHERE x.id = 3) ORDER BY 1, 2',
    'SELECT o0.id, c.id, (SELECT x.name FROM orders o JOIN customers x ON c.id = x.id - 1 WHERE o.id = 10) FROM orders o0, customers c WHERE o0.id < 12 ORDER BY 1, 2',
    'SELECT o0.id, c.id, (SELECT x.name FROM orders o JOIN customers x ON c.id = 2 ORDER BY x.id DESC LIMIT 1) FROM orders o0, customers c WHERE o0.id = 10 ORDER BY 1, 2',
    'SELECT c.name, o.id FROM customers c JOIN orders o ON o.customer_id = (SELECT x.id FROM customers x WHERE x.id = c.id) ORDER BY o.id',
    'SELECT c.name, o.id FROM customers c JOIN ix o ON o.customer_id = (SELECT x.id FROM customers x WHERE x.id = c.id) ORDER BY o.id',
    'SELECT c.name, x.name FROM customers c JOIN customers x ON x.id = (SELECT customer_id FROM orders WHERE id = c.id + 9) ORDER BY c.id',
    'SELECT c.name, x.name, o.id FROM customers c JOIN customers x JOIN ix o ON (SELECT x.id) = o.customer_id WHERE x.id = c.id ORDER BY c.id, o.id',
    'SELECT c.name, o.id, x.name FROM customers c JOIN ix o ON o.customer_id = (SELECT x.id) JOIN customers x ON x.id = c.id ORDER BY c.id, o.id',
    'SELECT c.name, x.name FROM customers c JOIN customers x ON x.id = (SELECT 2) ORDER BY c.id',
    "SELECT c.name, o.id FROM customers c LEFT JOIN ix o ON o.customer_id = (SELECT x.id FROM customers x WHERE x.id = c.id AND x.city = 'London') ORDER BY c.id, o.id",
    "SELECT c.name, o.id FROM customers c LEFT JOIN orders o ON o.customer_id = c.id AND EXISTS (SELECT 1 FROM cities WHERE cities.name = c.city AND cities.country = 'UK') ORDER BY c.id, o.id",
    'SELECT c.name, o.id FROM customers c LEFT JOIN orders o ON o.customer_id = c.id AND o.total > (SELECT total FROM orders o2 WHERE o2.customer_id = c.id ORDER BY total LIMIT 1) ORDER BY c.id, o.id',
    'SELECT c.name, o.id FROM customers c LEFT JOIN orders o ON NOT EXISTS (SELECT 1 FROM orders o3 WHERE o3.total > o.total AND o3.customer_id = c.id) AND o.customer_id = c.id ORDER BY c.id, o.id',
    'SELECT c.name, o.id FROM customers c LEFT JOIN orders o ON o.customer_id IN (SELECT id FROM customers c2 WHERE c2.city = c.city) ORDER BY c.id, o.id',
    'SELECT c.name, o.id, ci.country FROM customers c LEFT JOIN orders o ON o.customer_id = c.id JOIN cities ci ON ci.name = c.city AND (SELECT o.total) > 10 ORDER BY c.id, o.id',
    'SELECT c.name, o.id FROM customers c LEFT JOIN orders o ON o.customer_id = c.id WHERE (SELECT o.total) IS NULL OR EXISTS (SELECT 1 WHERE o.total > 40) ORDER BY c.id, o.id',
    'SELECT c.name, (SELECT o.id FROM customers x LEFT JOIN orders o ON o.customer_id = x.id AND o.total > c.id * 10 WHERE x.id = c.id ORDER BY o.id LIMIT 1) FROM customers c ORDER BY c.id',
    'SELECT c.name, (SELECT o.id FROM blank b LEFT JOIN orders o ON o.customer_id = c.id) FROM customers c ORDER BY c.id',
    'SELECT c.name, o.id, ci.country FROM customers c LEFT JOIN orders o ON o.customer_id = c.id AND EXISTS (SELECT 1 FROM cities WHERE cities.name = c.city AND (SELECT o.total) > 10) JOIN cities ci ON ci.name = c.city ORDER BY c.id, o.id',
]

# Cut down from the fuzzer (tests/fuzz, seed 11, with 08.02-08.03 in): each failed before.
FUZZED = [
    # a rowid lookup of p14 keyed by a subquery that reads p15 and p16, not in the row yet:
    # "no such column: b"
    ("CREATE TABLE t0(b INTEGER); CREATE TABLE t1(z TEXT); INSERT INTO t1 VALUES (0);",
     "SELECT X'0102' FROM t1 JOIN t1 p14, t0 AS p15 JOIN t1 p16 WHERE ((SELECT p14.oid FROM t1 AS q17 "
     "WHERE (p15.b LIKE '_b%') ORDER BY p16.z DESC, q17.rowid LIMIT 1) = p14.oid)"),
    # the same through t0's INTEGER PRIMARY KEY, the subquery reading the LEFT JOIN's p7
    ("CREATE TABLE t0(c TEXT DEFAULT 1e+20, z INTEGER PRIMARY KEY); CREATE TABLE t1(x NUMERIC); "
     "INSERT INTO t1 VALUES (500);",
     "SELECT x AS r0 FROM t1, t0 LEFT JOIN t0 AS p7 WHERE ((SELECT p7.z FROM t1 AS q8 ORDER BY t0.c, q8.rowid LIMIT 1) "
     "== t0.z)"),
    # a LEFT JOIN's ON whose subquery reads only p3 and t1, with a table after it:
    # "ON clause references tables to its right"
    ("CREATE TABLE t0(a TEXT); CREATE TABLE t1(e NUMERIC, id INTEGER PRIMARY KEY); "
     "CREATE TABLE t2(e REAL, a INTEGER, d REAL);",
     "SELECT p3.a FROM t1 LEFT JOIN t2 p3 ON ((t1.e < p3.rowid) AND (NOT EXISTS (SELECT (10 || p3.e) FROM t1 AS q6 "
     "ORDER BY coalesce(id, X'FF', p3.d) DESC, q6.rowid))) JOIN t0 AS p4"),
]

# One column of every affinity, each row holding the same "one" spelled another way (an
# integer, a real, text, a blob, text with a space, '1.0'), NULL and text, so that IN's
# comparison affinity is tried for every pair: through the set kept by a subquery run once
# and through a correlated scan (made so by naming the outer row), which must agree with
# each other and with sqlite3.
MIXED = """CREATE TABLE s(v);
INSERT INTO s VALUES (1),(NULL);
CREATE TABLE one(v);
INSERT INTO one VALUES (1);
CREATE TABLE e(v);
CREATE TABLE nul(v);
INSERT INTO nul VALUES (NULL);
CREATE TABLE x(id INTEGER PRIMARY KEY, v);
INSERT INTO x VALUES (1, 1),(2, 2),(3, NULL),(4, 1.0),(5, '1'),(6, x'31'),(7, 'a'),(8, 1.5);
CREATE TABLE ti(id INTEGER PRIMARY KEY, i INTEGER, r REAL, t TEXT, n NUMERIC, b BLOB, u);
INSERT INTO ti VALUES (1, 1, 1, '1', 1, 1, 1), (2, '1', '1', 1, '1', '1', '1'), (3, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0),
  (4, x'31', x'31', x'31', x'31', x'31', x'31'), (5, '1.0', '1.0', '1.0', '1.0', '1.0', '1.0'),
  (6, NULL, NULL, NULL, NULL, NULL, NULL), (7, 'a', 'a', 'a', 'a', 'a', 'a'), (8, 2, 2.5, '2', 2, 2, 2),
  (9, ' 1', ' 1', ' 1', ' 1', ' 1', ' 1');
CREATE TABLE tx(id INTEGER PRIMARY KEY, i INTEGER, r REAL, t TEXT, n NUMERIC, b BLOB, u);
INSERT INTO tx VALUES (1, 1, 1, '1', 1, 1, 1), (2, '1', '1', 1, '1', '1', '1'), (3, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0),
  (4, x'31', x'31', x'31', x'31', x'31', x'31'), (5, '1.0', '1.0', '1.0', '1.0', '1.0', '1.0'),
  (6, NULL, NULL, NULL, NULL, NULL, NULL), (7, 'a', 'a', 'a', 'a', 'a', 'a'), (8, 2, 2.5, '2', 2, 2, 2),
  (9, ' 1', ' 1', ' 1', ' 1', ' 1', ' 1'), (10, '10', '10', '10', '10', '10', '10'), (11, '9', '9', '9', '9', '9', '9');
CREATE INDEX tx_i ON tx(i);
CREATE INDEX tx_r ON tx(r);
CREATE INDEX tx_t ON tx(t);
CREATE INDEX tx_n ON tx(n);
CREATE INDEX tx_b ON tx(b);
CREATE INDEX tx_u ON tx(u);
"""
COLS = ["i", "r", "t", "n", "b", "u"]
LHS = ["1", "1.0", "'1'", "x'31'", "NULL", "'a'", "2", "'1.0'", "' 1'"]


def mixed_queries():
    q = []
    # the whole NULL table: x NULL or not, the set empty, with and without NULL, hit and miss
    for lhs in ["1", "2", "NULL"]:
        for tab in ["s", "one", "e", "nul"]:
            q.append(f"SELECT {lhs} IN (SELECT v FROM {tab}), {lhs} NOT IN (SELECT v FROM {tab})")
            q.append(f"SELECT x.id, {lhs} IN (SELECT v FROM {tab} WHERE x.id = x.id), "
                     f"{lhs} NOT IN (SELECT v FROM {tab} WHERE x.id > 0) FROM x ORDER BY x.id")
    for tab, col in [("s", "v"), ("one", "v"), ("e", "v"), ("nul", "v"), ("x", "v"), ("ti", "t"), ("ti", "b")]:
        q.append(f"SELECT id, v IN (SELECT {col} FROM {tab}), v NOT IN (SELECT {col} FROM {tab}) FROM x ORDER BY id")
        q.append(f"SELECT x.id, x.v IN (SELECT {col} FROM {tab} WHERE x.id = x.id), "
                 f"x.v NOT IN (SELECT {col} FROM {tab} WHERE x.id = x.id) FROM x ORDER BY x.id")
        q.append(f"SELECT id FROM x WHERE v NOT IN (SELECT {col} FROM {tab}) ORDER BY id")
        q.append(f"SELECT id FROM x WHERE v IN (SELECT {col} FROM {tab}) ORDER BY id")
    # every affinity on the left against every affinity on the right, set and scan
    for a in COLS:
        for b in COLS:
            q.append(f"SELECT o.id, o.{a} IN (SELECT {b} FROM ti), o.{a} NOT IN (SELECT {b} FROM ti WHERE id <> 6), "
                     f"o.{a} IN (SELECT {b} FROM ti WHERE o.id > 0), "
                     f"o.{a} NOT IN (SELECT {b} FROM ti WHERE id <> 6 AND o.id > 0) FROM ti o ORDER BY o.id")
            q.append(f"SELECT o.id, o.{a} IN (SELECT {b} + 0 FROM ti), o.{a} IN (SELECT {b} || '' FROM ti), "
                     f"o.{a} IN (SELECT {b} FROM ti WHERE id = 4) FROM ti o ORDER BY o.id")
            # a scalar subquery carries its column's affinity into =, < and >
            q.append(f"SELECT o.id, o.{a} = (SELECT {b} FROM ti WHERE id = 2), (SELECT {b} FROM ti WHERE id = 5) = o.{a}, "
                     f"o.{a} > (SELECT {b} FROM ti WHERE id = 3) FROM ti o ORDER BY o.id")
            # lookups keyed by a name from outside or a scalar subquery, on an index of each
            # affinity: the plan may narrow the rows read, never lose one
            q.append(f"SELECT o.id, (SELECT tx.id FROM tx WHERE tx.{b} = o.{a} ORDER BY tx.id LIMIT 1), "
                     f"(SELECT tx.id FROM tx WHERE o.{a} < tx.{b} ORDER BY tx.id LIMIT 1), "
                     f"(SELECT tx.id FROM tx WHERE tx.{b} >= o.{a} ORDER BY tx.id DESC LIMIT 1), "
                     f"(SELECT tx.id FROM tx WHERE tx.{b} BETWEEN o.{a} AND 'z' ORDER BY tx.id LIMIT 1) "
                     f"FROM ti o ORDER BY o.id")
            q.append(f"SELECT o.id FROM ti o WHERE EXISTS (SELECT 1 FROM tx WHERE tx.{b} = o.{a}) ORDER BY o.id")
            for k in (1, 2, 4, 5, 9):
                q.append(f"SELECT id FROM tx WHERE {b} = (SELECT {a} FROM ti WHERE id = {k}) ORDER BY id")
            q.append(f"SELECT id FROM tx WHERE {b} > (SELECT {a} FROM ti WHERE id = 1) ORDER BY id")
        for lhs in LHS:
            q.append(f"SELECT {lhs} IN (SELECT {a} FROM ti), {lhs} NOT IN (SELECT {a} FROM ti WHERE id <> 6), "
                     f"{lhs} IN (SELECT {a} FROM ti WHERE id = 3), ({lhs}) + 0 IN (SELECT {a} FROM ti), "
                     f"{lhs} = (SELECT {a} FROM ti WHERE id = 1), (SELECT {a} FROM ti WHERE id = 2) = {lhs}")
            q.append(f"SELECT o.id, {lhs} IN (SELECT {a} FROM ti WHERE o.id = o.id) FROM ti o ORDER BY o.id")
    return q


# Errors in both engines (errors_alike); the first few also by sqlite3's exact words.
ERRORS = [
    ("SELECT (SELECT 1, 2)", "sub-select returns 2 columns - expected 1"),
    ("SELECT 1 IN (SELECT 1, 2)", "sub-select returns 2 columns - expected 1"),
    ("SELECT 1 IN (SELECT * FROM orders)", "sub-select returns 3 columns - expected 1"),
    ("SELECT (SELECT * FROM customers WHERE id = 1)", "sub-select returns 3 columns - expected 1"),
    ("SELECT (SELECT c.* FROM customers c, orders o)", "sub-select returns 3 columns - expected 1"),
    ("SELECT name FROM customers WHERE (SELECT id, name FROM customers) = 1", "sub-select returns 2 columns - expected 1"),
    ("SELECT (SELECT nope FROM customers)", "no such column: nope"),
    ("SELECT (SELECT customers.nope FROM customers)", "no such column: customers.nope"),
    ("SELECT (SELECT zz.name FROM customers)", "no such column: zz.name"),
    ("SELECT (SELECT id FROM customers, orders)", "ambiguous column name: id"),
    ("SELECT (SELECT id FROM customers JOIN orders ON 1) FROM customers", "ambiguous column name: id"),
    ("SELECT (SELECT rowid FROM customers, orders) FROM cities", "ambiguous column name: rowid"),
    ("SELECT (SELECT 1 FROM nosuch)", "no such table: nosuch"),
    ("SELECT (SELECT x.* FROM customers)", "no such table: x"),
    ("CREATE TABLE d(a DEFAULT ((SELECT 1)))", "default value of column [a] is not constant"),
    ("SELECT * FROM customers c LEFT JOIN orders o ON EXISTS (SELECT 1 FROM cities WHERE cities.name = ci.name) "
     "JOIN cities ci", "ON clause references tables to its right"),
    ("SELECT * FROM customers c LEFT JOIN orders o ON (SELECT (SELECT ci.name)) JOIN cities ci",
     "ON clause references tables to its right"),
]
ERRORS_ALIKE = [
    "SELECT name FROM customers WHERE id IN (SELECT nope FROM orders)",
    "SELECT name FROM customers c WHERE EXISTS (SELECT 1 FROM orders WHERE nope = c.id)",
    "SELECT (SELECT id FROM blank) FROM customers c JOIN orders o ON 1",
    "SELECT c.id FROM customers c ORDER BY (SELECT nope FROM orders)",
    "SELECT (SELECT c.name FROM customers) FROM orders",
    "SELECT (SELECT c.name FROM customers c) FROM customers c, customers d WHERE (SELECT d.nope)",
    "SELECT (SELECT 1",
    "SELECT (SELECT)",
    "SELECT EXISTS 1",
    "SELECT EXISTS (1)",
    "SELECT EXISTS SELECT 1",
    "SELECT 1 IN SELECT 1",
    "SELECT 1 NOT EXISTS (SELECT 1)",
    "SELECT (SELECT *)",
    "SELECT * FROM customers WHERE id IN (SELECT id FROM customers c WHERE c.nope = customers.id)",
    "UPDATE customers SET name = (SELECT nope FROM orders)",
    "DELETE FROM customers WHERE id IN (SELECT 1, 2)",
    "INSERT INTO customers VALUES (9, (SELECT name), 'x')",
    "CREATE TABLE d(a DEFAULT ((SELECT 1)))",
]

# What 08.06 does not build, refused by name (sqlite3 runs each of them).
REFUSED = [
    ("SELECT (SELECT x FROM (SELECT 1 AS x))", "subqueries in FROM are not supported"),
    ("SELECT name FROM customers WHERE id IN ids", "IN with a table name is not supported"),
    ("SELECT name FROM customers WHERE id NOT IN ids", "IN with a table name is not supported"),
]

# Writes whose subqueries read the table being written: what sqlite3 leaves, read back.
WRITES = """CREATE TABLE t(a);
INSERT INTO t VALUES (1),(2),(3),(4),(5);
DELETE FROM t WHERE EXISTS (SELECT 1 FROM t AS u WHERE u.a = t.a - 1);
SELECT rowid, a FROM t ORDER BY rowid;
DELETE FROM t;
INSERT INTO t VALUES (1),(2),(3),(4),(5);
UPDATE t SET a = a * 10 WHERE EXISTS (SELECT 1 FROM t AS u WHERE u.a = t.a - 1);
SELECT rowid, a FROM t ORDER BY rowid;
UPDATE t SET a = (SELECT u.a FROM t AS u WHERE u.rowid = t.rowid - 1);
SELECT rowid, a FROM t ORDER BY rowid;
DELETE FROM t;
INSERT INTO t VALUES (1),(2),(3),(4),(5);
UPDATE t SET a = coalesce((SELECT u.a FROM t AS u WHERE u.rowid = t.rowid - 1), 0) + a;
SELECT rowid, a FROM t ORDER BY rowid;
UPDATE t SET a = (SELECT u.a FROM t AS u WHERE u.rowid = t.rowid + 1) WHERE rowid IN (SELECT rowid FROM t WHERE a > 3);
SELECT rowid, a FROM t ORDER BY rowid;
UPDATE t SET a = (SELECT a FROM t ORDER BY a DESC LIMIT 1) + rowid;
SELECT rowid, a FROM t ORDER BY rowid;
DELETE FROM t WHERE a = (SELECT a FROM t ORDER BY a LIMIT 1);
SELECT rowid, a FROM t ORDER BY rowid;
DELETE FROM t WHERE a NOT IN (SELECT a FROM t WHERE rowid > 3);
SELECT rowid, a FROM t ORDER BY rowid;
INSERT INTO t VALUES ((SELECT a FROM t ORDER BY a DESC LIMIT 1) + 1);
INSERT INTO t VALUES ((SELECT a FROM t ORDER BY a DESC LIMIT 1) + 1), ((SELECT a FROM t ORDER BY a DESC LIMIT 1) + 1), (7);
INSERT INTO t VALUES ((SELECT rowid FROM t ORDER BY rowid DESC LIMIT 1)), (EXISTS (SELECT 1 FROM t WHERE a = 7)), ((SELECT a FROM t WHERE a > 1000) IS NULL);
SELECT rowid, a FROM t ORDER BY rowid;
UPDATE customers SET city = (SELECT name FROM cities WHERE country = 'IT') WHERE id IN (SELECT customer_id FROM orders WHERE total < 10);
UPDATE orders SET total = total + (SELECT id FROM customers WHERE city = 'Rome') WHERE customer_id IN (SELECT id FROM customers WHERE city = 'Rome');
SELECT * FROM customers ORDER BY id;
SELECT * FROM orders ORDER BY id;
DELETE FROM orders WHERE customer_id NOT IN (SELECT id FROM customers);
SELECT * FROM orders ORDER BY id;
DELETE FROM orders WHERE customer_id NOT IN (SELECT id FROM customers WHERE id IS NOT NULL) OR customer_id IS NULL;
SELECT * FROM orders ORDER BY id;
DELETE FROM customers WHERE NOT EXISTS (SELECT 1 FROM orders WHERE orders.customer_id = customers.id);
SELECT * FROM customers ORDER BY id;
BEGIN;
INSERT INTO orders VALUES (20, (SELECT id FROM customers WHERE name = 'Chen'), (SELECT total FROM orders WHERE id = 10) + 1);
COMMIT;
SELECT * FROM orders ORDER BY id;
"""

# The REPL's EXPLAIN shows a subquery as written, inside the filter that runs it.
EXPLAIN = """Filter EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.id)
  Scan customers
"""
# In a join, a term with a subquery is checked as soon as the tables it reads are in the row,
# those its subquery reads included: the NOT IN reads only c, the EXISTS reads o too.
EXPLAIN_IN = """Filter EXISTS (SELECT 1 FROM orders o2 WHERE o2.total > o.total)
  Join
    Filter c.id NOT IN (SELECT customer_id FROM orders)
      Scan customers AS c
    Scan orders AS o
"""


def files(t, setup):
    tr = t.track
    a, b = tr.path(t), tr.path(t)
    tr.db(t, a, setup)
    tr.sqlite(t, b, setup)
    return a, b


def lines(out):
    return "".join(sorted(out.splitlines(keepends=True)))


def compare(t, a, b, sql, sort=False, tiny=True, env=None):
    """sql through ./db on file a (with the default cache, and with a two-page one, which evicts
    pages under a running subquery; or once, with env) and through sqlite3 on file b: the
    answers must agree."""
    tr = t.track
    ours = tr.db(t, a, sql, env=env).out
    theirs = tr.sqlite(t, b, sql).out
    if sort:
        ours, theirs = lines(ours), lines(theirs)
    if not tr.same_output(ours, theirs):
        la, lb = ours.splitlines(), theirs.splitlines()
        i = next((i for i in range(max(len(la), len(lb)))
                  if i >= len(la) or i >= len(lb) or not tr.same_output(la[i], lb[i])), 0)
        got = la[i] if i < len(la) else "<nothing>"
        want = lb[i] if i < len(lb) else "<nothing>"
        t.check(False, f"./db and sqlite3 disagree at output line {i + 1}:\n  ./db:    {got!r}\n"
                       f"  sqlite3: {want!r}\n--- sql\n{sql[:3000]}")
    if tiny:
        small = tr.db(t, a, sql, env={"DB_CACHE_PAGES": "2"}).out
        if sort:
            small = lines(small)
        t.check(small == ours, f"with DB_CACHE_PAGES=2 ./db answers differently:\n{small[:1500]}\n--- sql\n{sql[:2000]}")
    return ours


def listing(queries):
    return "".join(f"{q};\nSELECT '--';\n" for q in queries)


def hits(t, path, sql):
    """The page cache hits a query costs (DB_STATS): pages looked at, from the cache or not."""
    r = t.track.db(t, path, sql, env={"DB_STATS": "1"})
    return t.track.stats(r.err)["cache hits"], r.out


def big_tables():
    """p 3000 rows, q 2000, r 300; a pad of 4500 bytes every 700th p row and a note of 3000
    every 450th q row (overflow pages); q.v an integer, text, real, NULL or blob by turns."""
    s = ["CREATE TABLE p(id INTEGER PRIMARY KEY, k INTEGER, name TEXT, pad TEXT);",
         "CREATE TABLE q(id INTEGER PRIMARY KEY, pk INTEGER, v, note TEXT);",
         "CREATE TABLE r(a, b TEXT);", "CREATE INDEX q_pk ON q(pk);", "BEGIN;"]
    for i in range(1, 3001):
        pad = ("p" * (4500 if i % 700 == 0 else 60)) + str(i)
        s.append(f"INSERT INTO p VALUES ({i}, {i * 7 % 300 + 1}, 'name {i % 500}', '{pad}');")
    for j in range(1, 2001):
        v = [j, f"'{j}'", f"{j}.0", "NULL", f"x'{0x41 + j % 26:02x}{0x61 + j % 7:02x}'"][j % 5]
        s.append(f"INSERT INTO q VALUES ({j}, {j * 13 % 3000 + 1}, {v}, "
                 f"'{chr(97 + j % 26) * (3000 if j % 450 == 0 else 80)}');")
    for j in range(1, 301):
        s.append(f"INSERT INTO r VALUES ({j % 50}, 'r{j}');")
    s.append("COMMIT;")
    return "\n".join(s) + "\n"


BIG_QUERIES = [
    # correlated, in the result, by key and through q's index
    "SELECT p.id, (SELECT q.id FROM q WHERE q.pk = p.id ORDER BY q.id LIMIT 1), length(p.pad) FROM p WHERE p.id % 97 = 3 ORDER BY p.id",
    "SELECT p.id, p.pad, (SELECT q.note FROM q WHERE q.id = p.k) FROM p WHERE p.id % 350 = 0 ORDER BY p.id",
    "SELECT p.id, (SELECT note FROM q WHERE q.id = p.id % 2000 + 1) FROM p ORDER BY p.id",
    # run once, its text kept while the outer query goes on for thousands of rows
    "SELECT p.id, (SELECT note FROM q WHERE id = 450), (SELECT pad FROM p WHERE id = 1400) FROM p ORDER BY p.id",
    "SELECT p.id, p.name FROM p WHERE p.name NOT IN (SELECT note FROM q) AND p.pad NOT IN (SELECT b FROM r) ORDER BY p.id",
    # IN over thousands of values, NOT IN with NULLs among them, EXISTS
    "SELECT p.id FROM p WHERE p.id IN (SELECT pk FROM q) ORDER BY p.id",
    "SELECT p.id FROM p WHERE p.id NOT IN (SELECT pk FROM q) ORDER BY p.id",
    "SELECT p.id FROM p WHERE p.id IN (SELECT v FROM q) ORDER BY p.id",
    "SELECT p.id FROM p WHERE p.id NOT IN (SELECT v FROM q) ORDER BY p.id",
    "SELECT p.id FROM p WHERE p.id NOT IN (SELECT v FROM q WHERE v IS NOT NULL) ORDER BY p.id",
    "SELECT p.id FROM p WHERE p.name IN (SELECT note FROM q) OR p.pad IN (SELECT pad FROM p AS p2 WHERE p2.id = p.id + 700) ORDER BY p.id",
    "SELECT p.id FROM p WHERE EXISTS (SELECT 1 FROM q WHERE q.pk = p.id AND q.note > 'm') ORDER BY p.id",
    "SELECT p.id FROM p WHERE NOT EXISTS (SELECT 1 FROM q WHERE q.pk = p.id) AND p.id < 200 ORDER BY p.id",
    "SELECT p.id, p.pad FROM p WHERE p.pad IN (SELECT pad FROM p WHERE id % 700 = 0) ORDER BY p.id",
    "SELECT p.id FROM p WHERE p.k IN (SELECT a FROM r WHERE b > 'r2' || p.id % 10) ORDER BY p.id",
    # ON, a join outside
    "SELECT p.id, q.id FROM p JOIN q ON q.id = p.k AND q.note IN (SELECT note FROM q AS q2 WHERE q2.id = p.k) ORDER BY p.id, q.id",
    "SELECT p.id, q.id, (SELECT r.b FROM r WHERE r.rowid = q.id % 300 + 1) FROM p, q WHERE q.id = p.id AND p.id % 50 = 1 ORDER BY 1",
    # ORDER BY a subquery
    "SELECT p.id FROM p WHERE p.id < 300 ORDER BY (SELECT note FROM q WHERE q.id = p.id), p.id",
    "SELECT p.id, p.pad FROM p WHERE p.id % 100 = 0 ORDER BY (SELECT q.note FROM q WHERE q.pk = p.id ORDER BY q.id LIMIT 1) DESC, p.pad",
    # two and three deep
    "SELECT p.id, (SELECT (SELECT r.b FROM r WHERE r.rowid = q.id % 300 + 1) FROM q WHERE q.pk = p.id ORDER BY q.id LIMIT 1) "
    "FROM p WHERE p.id % 10 = 0 ORDER BY p.id",
    "SELECT p.id FROM p WHERE EXISTS (SELECT 1 FROM q WHERE q.pk = p.id AND EXISTS (SELECT 1 FROM r WHERE r.a = q.id % 50 "
    "AND r.b IN (SELECT 'r' || (p.id % 300 + 1)))) ORDER BY p.id",
    "SELECT p.id, (SELECT (SELECT (SELECT p.pad || q.note FROM r WHERE r.rowid = 1) FROM q WHERE q.id = p.id) FROM r WHERE r.rowid = 2) "
    "FROM p WHERE p.id % 700 = 0 ORDER BY 1",
    "SELECT p.id, (SELECT q.id FROM q WHERE q.note = (SELECT note FROM q AS q3 WHERE q3.id = p.id % 2000 + 1) ORDER BY q.id LIMIT 1) "
    "FROM p WHERE p.id % 33 = 0 ORDER BY 1",
]

# Then writes whose subqueries read big tables, the table written among them.
BIG_WRITES = [
    "UPDATE q SET note = (SELECT p.pad FROM p WHERE p.id = q.pk) WHERE q.id % 100 = 0",
    "SELECT id, length(note), note LIKE 'ppppp%' FROM q WHERE id % 100 = 0 ORDER BY id",
    "UPDATE q SET v = (SELECT v FROM q AS q2 WHERE q2.id = q.id - 1) WHERE id IN (SELECT pk FROM q WHERE pk < 500)",
    "SELECT id, v + 0, typeof(v), length(v) FROM q WHERE id < 500 ORDER BY id",
    "UPDATE p SET name = (SELECT name FROM p AS p2 WHERE p2.id = p.id + 1) || '!' WHERE id % 200 = 0",
    "SELECT id, name FROM p WHERE name LIKE '%!%' ORDER BY id",
    "UPDATE p SET k = (SELECT k FROM p AS p2 WHERE p2.id = p.id - 1) + 1 WHERE id <= 50",
    "SELECT id, k FROM p WHERE id <= 50 ORDER BY id",
    "UPDATE p SET name = name || '?' WHERE name NOT IN (SELECT b FROM r) AND pad NOT IN (SELECT note FROM q)",
    "SELECT id, name FROM p WHERE id % 250 = 0 ORDER BY id",
    "DELETE FROM q WHERE pk IN (SELECT id FROM p WHERE k < 20)",
    "SELECT id FROM q ORDER BY id",
    "DELETE FROM r WHERE EXISTS (SELECT 1 FROM r AS r2 WHERE r2.a = r.a AND r2.rowid < r.rowid)",
    "SELECT rowid, a, b FROM r ORDER BY rowid",
    "DELETE FROM p WHERE p.pad IN (SELECT note FROM q) OR p.id IN (SELECT pk + 1 FROM q WHERE q.id < 50)",
    "SELECT id FROM p ORDER BY id",
    "INSERT INTO r VALUES ((SELECT a FROM r ORDER BY a DESC, rowid LIMIT 1) + 1, (SELECT b FROM r ORDER BY rowid DESC LIMIT 1) || '+'), "
    "((SELECT a FROM r ORDER BY a DESC, rowid LIMIT 1) + 1, (SELECT b FROM r ORDER BY rowid DESC LIMIT 1) || '+')",
    "INSERT INTO r VALUES ((SELECT rowid FROM r ORDER BY rowid DESC LIMIT 1), (SELECT p.pad FROM p WHERE p.id = 1400))",
    "SELECT rowid, a, length(b), b LIKE 'p%' FROM r ORDER BY rowid",
    "INSERT INTO q(pk, v, note) VALUES ((SELECT id FROM p WHERE id > 2990 ORDER BY id LIMIT 1), "
    "EXISTS (SELECT 1 FROM q WHERE v IS NULL), (SELECT note FROM q WHERE id = 450))",
    "SELECT id, pk, v, length(note) FROM q ORDER BY id DESC LIMIT 3",
]


def test(t):
    tr = t.track

    # the data set of the module: every query in both engines, and with a two-page cache
    a, b = files(t, SHOP)
    compare(t, a, b, listing(SHOP_QUERIES))
    for q, msg in ERRORS:
        r = tr.errors_alike(t, SHOP, f"{q};\n")
        t.check(f"Error: {msg}\n" in r.err, f"{q} should fail with {msg!r}, as sqlite3 does, but:\n{r}")
    for q in ERRORS_ALIKE:
        tr.errors_alike(t, SHOP, f"{q};\n")
    for q, msg in REFUSED:
        r = tr.db(t, a, f"{q};\n", check=False)
        t.check(r.rc != 0 and f"Error: {msg}" in r.err, f"{q} should be refused with {msg!r}, but:\n{r}")
        tr.sqlite(t, b, f"{q};\n")     # sqlite3 runs it: a feature, not an error

    # sixty-four subqueries one inside another, and no more
    deep = "SELECT " + "(SELECT " * 64 + "1" + ")" * 64 + ";\n"
    t.check(tr.db(t, a, deep).out == "1\n", "64 levels of subqueries should give 1")
    r = tr.db(t, a, "SELECT " + "(SELECT " * 65 + "1" + ")" * 65 + ";\n", check=False)
    t.check(r.rc != 0 and "Error: too many levels of subqueries (at most 64)" in r.err, f"65 levels:\n{r}")

    # joins and subqueries together; the fuzzer's cases, cut down
    compare(t, a, b, listing(JOIN_QUERIES))
    for setup, q in FUZZED:
        fa, fb = files(t, setup.replace("; ", ";\n") + "\n")
        compare(t, fa, fb, f"{q};\n")

    # EXPLAIN: the subquery, as written, in the filter that runs it
    out = tr.db(t, a, "EXPLAIN SELECT name FROM customers c WHERE EXISTS (SELECT 1 FROM orders o "
                      "WHERE o.customer_id = c.id) ORDER BY id;\n").out
    t.check(out == EXPLAIN, f"EXPLAIN of a correlated EXISTS:\n{out}\nexpected:\n{EXPLAIN}")
    out = tr.db(t, a, "EXPLAIN SELECT c.name FROM customers c, orders o WHERE c.id NOT IN "
                      "(SELECT customer_id FROM orders) AND EXISTS (SELECT 1 FROM orders o2 WHERE o2.total > o.total);\n").out
    t.check(out == EXPLAIN_IN, f"EXPLAIN of a join with NOT IN:\n{out}\nexpected:\n{EXPLAIN_IN}")

    # writes whose subqueries read the table being written, outside and inside BEGIN
    a2, b2 = files(t, SHOP)
    ours = tr.db(t, a2, WRITES).out
    theirs = tr.sqlite(t, b2, WRITES).out
    t.check(tr.same_output(ours, theirs), f"writes with subqueries:\n./db:\n{ours}\nsqlite3:\n{theirs}")
    tr.integrity(t, a2)

    # IN's NULL table and affinities, a set run once against a correlated scan; lookups keyed
    # by a name from outside or a scalar subquery on an index of every affinity
    a3, b3 = files(t, MIXED)
    compare(t, a3, b3, listing(mixed_queries()))

    # tables of thousands of rows, text on overflow pages, a two-page cache
    big = big_tables()
    a4, b4 = files(t, big)
    compare(t, a4, b4, listing(BIG_QUERIES))
    r = tr.db(t, a4, "SELECT p.id, (SELECT note FROM q WHERE q.id = p.id % 2000 + 1) FROM p;\n",
              env={"DB_CACHE_PAGES": "2", "DB_STATS": "1"})
    st = tr.stats(r.err)
    t.check(st["evictions"] > 100 and len(r.lines()) == 3000,
            f"the two-page cache should evict pages between rows: {st}, {len(r.lines())} rows")
    for w in BIG_WRITES:          # a write runs once, with the two-page cache
        reads = w.startswith("SELECT")
        compare(t, a4, b4, f"{w};\n", tiny=reads, env=None if reads else {"DB_CACHE_PAGES": "2"})
    tr.integrity(t, a4)

    # a subquery that names nothing outside runs once; a correlated one runs per outer row
    a5, b5 = files(t, big)
    scan_p, _ = hits(t, a5, "SELECT id FROM p WHERE pad IS NULL;\n")      # every row read, none out
    scan_q, _ = hits(t, a5, "SELECT id FROM q WHERE note IS NULL;\n")
    once, out1 = hits(t, a5, "SELECT id FROM p WHERE k NOT IN (SELECT pk + 5000 FROM q) AND id > 2900;\n")
    every, out2 = hits(t, a5, "SELECT id FROM p WHERE k NOT IN (SELECT pk + 5000 FROM q WHERE p.id > 0) AND id > 2900;\n")
    t.check(out1 == out2 and out1, "the two IN queries should give the same rows")
    t.check(once <= scan_p + scan_q + 50,
            f"an uncorrelated IN should read q once: {once} cache hits, a scan of p is {scan_p}, of q {scan_q}")
    t.check(every > 50 * scan_q, f"a correlated IN runs per row: {every} cache hits, a scan of q is {scan_q}")
    s1, _ = hits(t, a5, "SELECT (SELECT note FROM q WHERE id = 7) FROM p;\n")
    t.check(s1 <= scan_p + 20, f"a scalar subquery run once: {s1} cache hits, a scan of p is {scan_p}")
    # and a correlated one uses the index on the inner column, keyed by the outer row
    idx, o1 = hits(t, a5, "SELECT id FROM p WHERE id <= 300 AND EXISTS (SELECT 1 FROM q WHERE q.pk = p.id);\n")
    full, o2 = hits(t, a5, "SELECT id FROM p WHERE id <= 300 AND EXISTS (SELECT 1 FROM q WHERE q.pk + 0 = p.id);\n")
    t.check(o1 == o2 and o1, "the EXISTS queries should give the same rows")
    t.check(idx * 20 < full, f"a correlated lookup should use q_pk: {idx} cache hits against {full} for a scan")
    sq = tr.sqlite(t, b5, "SELECT id FROM p WHERE id <= 300 AND EXISTS (SELECT 1 FROM q WHERE q.pk = p.id);\n").out
    t.check(sq == o1, "sqlite3 finds other rows for the EXISTS")

    # the sqllogictest slice, with subqueries (and joins) no longer skipped
    tr.sqllogictest(t, have=("join", "subquery"))
    # and a quick slice of the fuzzer, with subqueries anywhere it can put them, joins and LEFT JOINs
    tr.fuzz(t, ("join", "leftjoin", "subquery"), n=300)
