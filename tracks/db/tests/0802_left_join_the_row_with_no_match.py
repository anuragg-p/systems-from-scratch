"""08.02 LEFT JOIN: the row with no match

LEFT [OUTER] JOIN keeps every row of the tables before it: a row that matches nothing
comes up once, with the joined table's columns (and rowid) NULL. A LEFT JOIN's own ON
decides what matches and is checked inside the join; WHERE, and the ON of an inner
join, are checked on the rows the join hands up, NULL rows included. The test holds
./db to sqlite3 wherever the two placements would give different rows: a condition in
ON against the same one in WHERE, a condition on the outer table in ON, an inner ON
that names a LEFT JOIN table, IS NULL to find what matched nothing; chains of LEFT
joins and LEFT mixed with inner joins in both orders; empty tables on either side; a
two-page cache; and many rows with text that must be kept. Rows come out in the order
sqlite3 gives with automatic indexes off (a LEFT JOIN pins the order in sqlite3), and
EXPLAIN QUERY PLAN prints its " LEFT-JOIN". An ON that names a table to its right is
sqlite3's error; RIGHT and FULL JOIN are still refused by name. Then 300 cases of the
fuzzer with LEFT joins, and the kept sqllogictest scripts that hold LEFT JOINs.
"""

import os

from harness.core import load_test

J = load_test(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "0801_two_tables_in_one_query_the_nested_loop_join.py"))

SHOP = """CREATE TABLE customers(id INTEGER PRIMARY KEY, name TEXT, city TEXT);
CREATE TABLE orders(id INTEGER PRIMARY KEY, customer_id INTEGER, total INTEGER);
CREATE TABLE cities(name TEXT, country TEXT);
CREATE TABLE countries(code TEXT, name TEXT);
CREATE TABLE blank(x, y);
INSERT INTO customers VALUES (1,'Ada','London'),(2,'Brook','Paris'),(3,'Chen','London'),(4,'Dee','Oslo');
INSERT INTO orders VALUES (10,1,30),(11,3,15),(12,1,50),(13,2,20),(14,3,5),(15,NULL,40);
INSERT INTO cities VALUES ('London','UK'),('Paris','FR'),('Oslo',NULL),('Rome','IT');
INSERT INTO countries VALUES ('UK','United Kingdom'),('FR','France'),('NO','Norway');
CREATE TABLE jw(left, outer, v);
INSERT INTO jw VALUES (1, 2, 'one'), (4, 1, 'four');
"""

CO = "customers c LEFT JOIN orders o ON o.customer_id = c.id"

QUERIES = [
    # no match (Dee), some matches, every row matched, nothing matched
    f"SELECT c.name, o.id, o.total FROM {CO} ORDER BY c.id, o.id",
    "SELECT o.id, c.name FROM orders o LEFT JOIN customers c ON c.id = o.customer_id ORDER BY o.id",
    "SELECT a.name, b.name FROM customers a LEFT JOIN customers b ON b.id = a.id ORDER BY a.id",
    "SELECT c.name, o.id FROM customers c LEFT JOIN orders o ON o.customer_id = c.id + 100 ORDER BY c.id",
    "SELECT c.name, o.id FROM customers c LEFT OUTER JOIN orders o ON o.customer_id = c.id ORDER BY c.id, o.id",
    "SELECT c.name, o.id FROM customers c left outer join orders o on o.customer_id = c.id order by c.id, o.id",
    "SELECT c.name, o.id FROM customers c OUTER LEFT JOIN orders o ON o.customer_id = c.id ORDER BY c.id, o.id",
    "SELECT c.name, o.id FROM customers c left JOIN orders o ON o.customer_id = c.id ORDER BY c.id, o.id",
    "SELECT c.name, o.id FROM customers c LEFT LEFT JOIN orders o ON o.customer_id = c.id ORDER BY c.id, o.id",
    "SELECT c.name, o.id FROM customers c LEFT OUTER OUTER JOIN orders o ON o.customer_id = c.id ORDER BY c.id, o.id",
    # the NULL row: every column of the right table, its rowid, *, typeof, functions on it
    f"SELECT * FROM {CO} ORDER BY c.id, o.id",
    f"SELECT o.*, c.* FROM {CO} ORDER BY c.id, o.id",
    f"SELECT c.name, o.rowid, o.oid, typeof(o.id), typeof(o.total), o.total + 1, o.total IS NULL FROM {CO} "
    "ORDER BY c.id, o.id",
    f"SELECT c.name, coalesce(o.total, 0), ifnull(o.id, -1), length(o.total), upper(c.name) FROM {CO} "
    "ORDER BY c.id, o.id",
    # ON against WHERE: the same condition gives other rows
    "SELECT c.name, o.id FROM customers c LEFT JOIN orders o ON o.customer_id = c.id AND o.total > 20 "
    "ORDER BY c.id, o.id",
    f"SELECT c.name, o.id FROM {CO} WHERE o.total > 20 ORDER BY c.id, o.id",
    "SELECT c.name, o.id FROM customers c LEFT JOIN orders o ON o.customer_id = c.id AND c.city = 'London' "
    "ORDER BY c.id, o.id",
    f"SELECT c.name, o.id FROM {CO} WHERE c.city = 'London' ORDER BY c.id, o.id",
    "SELECT c.name, o.id FROM customers c LEFT JOIN orders o ON c.city = 'London' ORDER BY c.id, o.id",
    "SELECT c.name, o.id FROM customers c LEFT JOIN orders o ON o.customer_id = c.id AND c.id = 2 "
    "ORDER BY c.id, o.id",
    "SELECT c.name, o.id FROM customers c LEFT JOIN orders o ON o.customer_id = c.id AND o.total IS NULL "
    "ORDER BY c.id, o.id",
    f"SELECT c.name, o.id FROM {CO} WHERE o.total IS NULL ORDER BY c.id, o.id",
    f"SELECT c.name, o.id FROM {CO} WHERE o.total > 20 OR o.id IS NULL ORDER BY c.id, o.id",
    f"SELECT c.name, o.id FROM {CO} WHERE NOT (o.total > 20) ORDER BY c.id, o.id",
    f"SELECT c.name, o.id FROM {CO} WHERE coalesce(o.total, 0) < 20 ORDER BY c.id, o.id",
    # IS NULL finds what matched nothing (the anti-join)
    f"SELECT c.name FROM {CO} WHERE o.id IS NULL ORDER BY c.id",
    f"SELECT c.name FROM {CO} WHERE o.rowid IS NULL ORDER BY c.id",
    "SELECT o.id FROM orders o LEFT JOIN customers c ON c.id = o.customer_id WHERE c.id IS NULL ORDER BY o.id",
    "SELECT c.name FROM customers c LEFT JOIN orders o ON o.customer_id = c.id AND o.total >= 30 "
    "WHERE o.id IS NULL ORDER BY c.id",
    # ON that is constant, missing, NULL, or names only the outer table
    "SELECT c.name, o.id FROM customers c LEFT JOIN orders o ON 1 ORDER BY c.id, o.id",
    "SELECT c.name, o.id FROM customers c LEFT JOIN orders o ON 0 ORDER BY c.id, o.id",
    "SELECT c.name, o.id FROM customers c LEFT JOIN orders o ON NULL ORDER BY c.id, o.id",
    "SELECT c.name, o.id FROM customers c LEFT JOIN orders o ORDER BY c.id, o.id",
    "SELECT c.name, o.id FROM customers c LEFT JOIN orders o ON c.id > 3 ORDER BY c.id, o.id",
    "SELECT c.name, o.id FROM customers c LEFT JOIN orders o ON o.id = 12 ORDER BY c.id, o.id",
    "SELECT c.name, o.id FROM customers c LEFT JOIN orders o ON o.customer_id IS c.id ORDER BY c.id, o.id",
    # empty tables: the right one (every row once, NULL), the left one (nothing), both
    "SELECT c.name, b.x, b.y, b.rowid FROM customers c LEFT JOIN blank b ON b.x = c.id ORDER BY c.id",
    "SELECT c.name, b.x FROM customers c LEFT JOIN blank b ORDER BY c.id",
    "SELECT * FROM blank b LEFT JOIN customers c ON c.id = b.x",
    "SELECT * FROM blank b LEFT JOIN blank b2 ON 1",
    "SELECT c.name, b.x, o.id FROM customers c LEFT JOIN blank b ON 1 LEFT JOIN orders o ON o.customer_id = c.id "
    "ORDER BY c.id, o.id",
    "SELECT c.name, b.x, o.id FROM customers c LEFT JOIN blank b ON 1 JOIN orders o ON o.customer_id = c.id "
    "ORDER BY c.id, o.id",
    "SELECT c.name, b.x FROM customers c JOIN blank b ON 1 LEFT JOIN orders o ON 1",
    # chains of three: LEFT, LEFT; and LEFT mixed with inner joins both ways round
    "SELECT c.name, ci.country, co.name FROM customers c LEFT JOIN cities ci ON ci.name = c.city "
    "LEFT JOIN countries co ON co.code = ci.country ORDER BY c.id",
    "SELECT c.name, o.id, ci.country FROM customers c LEFT JOIN orders o ON o.customer_id = c.id "
    "LEFT JOIN cities ci ON ci.name = c.city AND o.total > 10 ORDER BY c.id, o.id",
    "SELECT c.name, o.id, ci.country FROM customers c LEFT JOIN orders o ON o.customer_id = c.id "
    "JOIN cities ci ON ci.name = c.city ORDER BY c.id, o.id",
    "SELECT c.name, o.id, ci.country FROM customers c JOIN cities ci ON ci.name = c.city "
    "LEFT JOIN orders o ON o.customer_id = c.id ORDER BY c.id, o.id",
    "SELECT o.id, c.name, ci.country, co.name FROM orders o LEFT JOIN customers c ON c.id = o.customer_id "
    "LEFT JOIN cities ci ON ci.name = c.city LEFT JOIN countries co ON co.code = ci.country ORDER BY o.id",
    "SELECT ci.name, c.name, o.id FROM cities ci LEFT JOIN customers c ON c.city = ci.name "
    "LEFT JOIN orders o ON o.customer_id = c.id ORDER BY ci.rowid, c.id, o.id",
    "SELECT ci.name, c.name, o.id FROM cities ci JOIN customers c ON c.city = ci.name "
    "LEFT JOIN orders o ON o.customer_id = c.id AND o.total < 30 ORDER BY ci.rowid, c.id, o.id",
    "SELECT ci.name, co.name, c.name FROM cities ci LEFT JOIN countries co ON co.code = ci.country "
    "JOIN customers c ON c.city = ci.name ORDER BY ci.rowid, c.id",
    "SELECT c.name, o.id, o2.id FROM customers c LEFT JOIN orders o ON o.customer_id = c.id "
    "LEFT JOIN orders o2 ON o2.customer_id = c.id AND o2.id > o.id ORDER BY c.id, o.id, o2.id",
    # an inner join's ON is WHERE: one that names a LEFT JOIN table waits for its rows,
    # NULL rows too, and may name a table to its right
    "SELECT c.name, o.id, ci.name FROM customers c LEFT JOIN orders o ON o.customer_id = c.id "
    "JOIN cities ci ON ci.name = c.city AND o.total > 10 ORDER BY c.id, o.id",
    "SELECT c.name, o.id, ci.name FROM customers c LEFT JOIN orders o ON o.customer_id = c.id "
    "JOIN cities ci ON ci.name = c.city AND o.id IS NULL ORDER BY c.id, o.id",
    "SELECT c.name, ci.name, o.id FROM customers c JOIN cities ci ON ci.name = c.city AND o.total > 10 "
    "LEFT JOIN orders o ON o.customer_id = c.id ORDER BY c.id, o.id",
    "SELECT c.name, ci.name, o.id FROM customers c JOIN cities ci ON o.id IS NULL "
    "LEFT JOIN orders o ON o.customer_id = c.id WHERE ci.name = c.city ORDER BY c.id, o.id",
    # the outer table's own terms in WHERE (checked before the join) and in ON (not)
    f"SELECT c.name, o.id FROM {CO} WHERE c.id > 2 ORDER BY c.id, o.id",
    "SELECT c.name, o.id FROM customers c LEFT JOIN orders o ON o.customer_id = c.id AND c.id > 2 "
    "ORDER BY c.id, o.id",
    f"SELECT c.name, o.id FROM {CO} WHERE c.city = 'London' AND o.total > 10 ORDER BY c.id, o.id",
    f"SELECT c.name, o.id FROM {CO} WHERE c.city = 'Oslo' OR o.total = 5 ORDER BY c.id, o.id",
    # self-joins, rowid in ON, ORDER BY a NULL column, LIMIT and OFFSET
    "SELECT a.name, b.name FROM customers a LEFT JOIN customers b ON b.city = a.city AND b.id > a.id "
    "ORDER BY a.id, b.id",
    "SELECT x.id, y.id FROM orders x LEFT JOIN orders y ON y.total = x.total * 2 ORDER BY x.id",
    "SELECT c.name, o.id FROM customers c LEFT JOIN orders o ON o.rowid = c.rowid + 9 ORDER BY c.id",
    "SELECT c.rowid, o.rowid FROM customers c LEFT JOIN orders o ON o.customer_id = c.rowid ORDER BY 1, 2",
    f"SELECT c.name, o.total FROM {CO} ORDER BY o.total, c.id",
    f"SELECT c.name, o.total FROM {CO} ORDER BY o.total DESC, c.id",
    f"SELECT c.name, o.id FROM {CO} ORDER BY c.id DESC, o.id LIMIT 3",
    f"SELECT c.name, o.id FROM {CO} ORDER BY c.id, o.id LIMIT 2 OFFSET 4",
    # join words are names everywhere else
    "SELECT jw.left, jw.outer, c.name FROM jw LEFT JOIN customers c ON c.id = jw.outer ORDER BY 1",
    "SELECT left.name, outer.id FROM customers AS left LEFT JOIN orders AS outer ON outer.customer_id = left.id "
    "ORDER BY left.id, outer.id",
]

# Mixed types and NULLs in the join columns.
MIXED_QUERIES = [
    "SELECT a.id, b.id FROM a LEFT JOIN b ON a.x = b.x ORDER BY a.id, b.id",
    "SELECT a.id, b.id, typeof(b.x) FROM a LEFT JOIN b ON b.x = a.x AND b.id > 10 ORDER BY a.id, b.id",
    "SELECT a.id, c.rowid FROM a LEFT JOIN c ON a.x = c.k ORDER BY a.id, c.rowid",
    "SELECT m1.rowid, m2.rowid FROM m m1 LEFT JOIN m m2 ON m1.v = m2.v AND m1.rowid <> m2.rowid ORDER BY 1, 2",
    "SELECT m.rowid, a.id FROM m LEFT JOIN a ON a.x = m.v WHERE a.id IS NULL ORDER BY 1",
    "SELECT a.id, e.x FROM a LEFT JOIN e ON 1 ORDER BY a.id",
    "SELECT a.id, b.id, c.rowid FROM a LEFT JOIN b ON a.x = b.x LEFT JOIN c ON c.k = b.x ORDER BY 1, 2, 3",
]

# sqlite3 keeps a LEFT JOIN in the order written; with automatic indexes off it runs the
# same nested loop, and the rows come out in the same order with no ORDER BY.
NESTED_ORDER = [
    f"SELECT c.name, o.id FROM {CO}",
    "SELECT c.name, o.id FROM customers c LEFT JOIN orders o ON o.customer_id = c.id AND o.total > 10",
    "SELECT ci.name, c.name, o.id FROM cities ci LEFT JOIN customers c ON c.city = ci.name "
    "LEFT JOIN orders o ON o.customer_id = c.id",
    f"SELECT c.name, o.id FROM {CO} LIMIT 4 OFFSET 2",
]

# EXPLAIN QUERY PLAN against sqlite3 (automatic indexes off): " LEFT-JOIN" on the line.
PLANS = [
    f"SELECT * FROM {CO}",
    "SELECT * FROM orders o LEFT JOIN customers c ON c.id = o.customer_id",
    "SELECT * FROM customers c LEFT JOIN orders o ON 1 LEFT JOIN cities ci ON ci.name = c.city",
    "SELECT * FROM customers c CROSS JOIN cities ci LEFT JOIN orders o ON o.customer_id = c.id",
    "SELECT * FROM customers c LEFT JOIN orders o ON o.customer_id = c.id ORDER BY o.total",
]

# What 08.02 still leaves out: refused by name (sqlite3 runs each of them).
REFUSED = [
    ("SELECT * FROM customers c RIGHT JOIN orders o ON o.customer_id = c.id", "RIGHT JOIN is not supported"),
    ("SELECT * FROM customers c RIGHT OUTER JOIN orders o ON 1", "RIGHT JOIN is not supported"),
    ("SELECT * FROM customers c FULL JOIN orders o ON o.customer_id = c.id", "FULL JOIN is not supported"),
    ("SELECT * FROM customers c FULL OUTER JOIN orders o ON 1", "FULL JOIN is not supported"),
    ("SELECT * FROM customers c LEFT JOIN orders o ON 1 RIGHT JOIN cities ON 1", "RIGHT JOIN is not supported"),
    ("SELECT * FROM customers NATURAL LEFT JOIN orders", "NATURAL JOIN is not supported"),
    ("SELECT * FROM customers c LEFT JOIN orders o USING (id)", "USING is not supported"),
]

# Errors in both engines.
ERRORS = [
    "SELECT * FROM customers c LEFT JOIN orders o ON o.customer_id = ci.rowid JOIN cities ci",
    "SELECT * FROM customers c LEFT JOIN orders o ON ci.name = c.city JOIN cities ci ON 1",
    "SELECT * FROM customers c JOIN orders o ON 1 LEFT JOIN cities ci ON ci.name = co.name JOIN countries co",
    "SELECT * FROM customers c LEFT JOIN orders o ON o.customer_id = c.id LEFT JOIN cities ci ON co.code = 'UK' "
    "LEFT JOIN countries co",
    "SELECT * FROM customers c LEFT JOIN orders o ON nope = 1",
    "SELECT * FROM customers c LEFT JOIN orders o ON o.nope = c.id",
    "SELECT id FROM customers c LEFT JOIN orders o ON 1",
    "SELECT * FROM customers c LEFT JOIN nosuch n ON 1",
    "SELECT * FROM customers LEFT JOIN",
    "SELECT * FROM customers LEFT orders",
    "SELECT * FROM customers LEFT OUTER orders",
    "SELECT * FROM customers LEFT INNER JOIN orders",
    "SELECT * FROM customers LEFT CROSS JOIN orders",
    "SELECT * FROM customers LEFT ON 1",
    "SELECT * FROM customers c LEFT JOIN orders o ON o.customer_id = c.id ON 1",
    "SELECT nope FROM customers c LEFT JOIN orders o ON o.customer_id = x.id JOIN customers x",
]

EXPLAIN_TREE = """Sort by c.id, o.id
  Join
    Filter (o.total > 20)
      Left join on (o.customer_id = c.id)
        Filter (c.city = 'London')
          Scan customers AS c
        Scan orders AS o
    Scan cities AS ci
"""


def test(t):
    tr = t.track

    a, b = J.files(t, SHOP)
    J.compare(t, a, b, J.listing(QUERIES))
    for q in NESTED_ORDER:
        J.compare(t, a, b, f"{q};\n", theirs_first="PRAGMA automatic_index=OFF;\n")
    J.compare(t, a, b, "".join(f"EXPLAIN QUERY PLAN {q};\n" for q in PLANS),
              theirs_first="PRAGMA automatic_index=OFF;\n")
    for q, msg in REFUSED:
        r = tr.db(t, a, f"{q};\n", check=False)
        t.check(r.rc != 0 and f"Error: {msg}" in r.err, f"{q} should be refused with {msg!r}, but:\n{r}")
        tr.sqlite(t, b, f"{q};\n")     # sqlite3 runs it: a feature, not an error
    for q in ERRORS:
        tr.errors_alike(t, SHOP, f"{q};\n")
    for q in ERRORS[:4]:
        r = tr.db(t, a, f"{q};\n", check=False)
        t.check("Error: ON clause references tables to its right" in r.err,
                f"a LEFT JOIN's ON naming a table to its right: sqlite3's error, not:\n{r}")

    # EXPLAIN: a LEFT join with its ON; WHERE's terms above it, the outer table's below
    out = tr.db(t, a, "EXPLAIN SELECT c.name, o.id, ci.country FROM customers c LEFT JOIN orders o "
                      "ON o.customer_id = c.id JOIN cities ci WHERE c.city = 'London' AND o.total > 20 "
                      "ORDER BY c.id, o.id;\n").out
    t.check(out == EXPLAIN_TREE, f"EXPLAIN of a LEFT JOIN:\n{out}\nexpected:\n{EXPLAIN_TREE}")
    out = tr.db(t, a, "EXPLAIN SELECT * FROM customers c LEFT JOIN orders o;\n").out
    t.check(out == "Left join\n  Scan customers AS c\n  Scan orders AS o\n", f"EXPLAIN of a LEFT JOIN with no ON:\n{out}")

    # mixed types, NULL keys, an empty table (08.01's data)
    a2, b2 = J.files(t, J.MIXED)
    J.compare(t, a2, b2, J.listing(MIXED_QUERIES))

    # many rows, most matching nothing, with pages evicted mid-join (a two-page cache):
    # the outer row is kept while the inner table is read, and its NULL row goes up
    big = ("CREATE TABLE p(id INTEGER PRIMARY KEY, k INTEGER, pad TEXT);\n"
           "CREATE TABLE q(id INTEGER PRIMARY KEY, k INTEGER, name TEXT, pad TEXT);\nBEGIN;\n" +
           "".join(f"INSERT INTO p VALUES ({i}, {i * 7 % 300 + 1}, '{'p' * (5000 if i % 400 == 0 else 120)}{i}');\n"
                   for i in range(1, 2001)) +
           "".join(f"INSERT INTO q VALUES ({j}, {j * 3}, 'name {j}', '{chr(97 + j % 26) * 200}');\n"
                   for j in range(1, 201)) +
           "COMMIT;\n")
    a3, b3 = J.files(t, big)
    J.compare(t, a3, b3, "SELECT p.id, q.name, length(p.pad), p.pad FROM p LEFT JOIN q ON q.k = p.k;\n", sort=True)
    J.compare(t, a3, b3, "SELECT p.id, p.pad, q.id FROM p LEFT JOIN q ON q.k = p.k WHERE q.id IS NULL;\n", sort=True)
    J.compare(t, a3, b3, "SELECT q.id, p.id, p.pad FROM q LEFT JOIN p ON p.k = q.id * 2 AND p.id % 400 = 0 "
                         "ORDER BY q.id, p.id;\n")
    r = tr.db(t, a3, "SELECT p.id, p.pad, q.name FROM p LEFT JOIN q ON q.k = p.k;\n",
              env={"DB_CACHE_PAGES": "2", "DB_STATS": "1"})
    st = tr.stats(r.err)
    t.check(st["evictions"] > 100 and len(r.lines()) == 2000,
            f"the two-page cache should evict pages mid-join: {st}, {len(r.lines())} rows")

    # a quick slice of the fuzzer: random tables, rows and joins, LEFT ones too, against sqlite3
    tr.fuzz(t, "join,leftjoin", n=300, seed=1)
    # and the kept sqllogictest scripts that hold LEFT JOINs (random/aggregates: a few each,
    # most past the quick slice, so SLT=full runs them all), with joins no longer skipped
    tr.sqllogictest(t, have=("join",), scripts=["test/random/aggregates/slt_good_106.test",
                                                "test/random/aggregates/slt_good_60.test"])
