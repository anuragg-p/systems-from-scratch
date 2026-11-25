"""08.03 An index for the inner loop

A table after the first is looked up for each outer row, by rowid (or its INTEGER
PRIMARY KEY) or by an index on its column, when a condition sets that column equal to
a value of the tables before it; a LEFT JOIN table only by its own ON. A lookup may
only narrow what is read: every query gives the same rows with the indexes as without
them, and sqlite3's rows. The test runs each query on a file with indexes and one
without, through ./db (also with a two-page cache) and sqlite3: keys that are columns,
expressions and constants; NULL keys; duplicate keys on both sides; chains where each
table looks up the next. Then every pairing of column affinities (INTEGER, REAL,
NUMERIC, TEXT, BLOB, none) on the two sides of the join term, over values that look
alike (1, 1.0, '1', '1.0', ' 1', x'31', NULL, ...): with an index, with an INTEGER
PRIMARY KEY and with neither, the rows must be the same, and EXPLAIN QUERY PLAN must
say SEARCH exactly where sqlite3 does (sqlite3IndexAffinityOk). EXPLAIN names the
lookups; with a few thousand rows and a two-page cache, DB_STATS shows a lookup reads
a small part of the pages a scan reads. Then 300 cases of the fuzzer with joins over
tables with random indexes, and the kept sqllogictest scripts of joins.
"""

import os

from harness.core import load_test

J = load_test(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "0801_two_tables_in_one_query_the_nested_loop_join.py"))

SHOP = """CREATE TABLE customers(id INTEGER PRIMARY KEY, name TEXT, city TEXT);
CREATE TABLE orders(id INTEGER PRIMARY KEY, customer_id INTEGER, total INTEGER);
CREATE TABLE items(order_id INTEGER, product_id INTEGER, qty INTEGER);
CREATE TABLE products(id INTEGER PRIMARY KEY, title TEXT, price REAL);
CREATE TABLE cities(name TEXT, country TEXT);
CREATE TABLE countries(code TEXT, name TEXT);
CREATE TABLE blank(x, y);
INSERT INTO customers VALUES (1,'Ada','London'),(2,'Brook','Paris'),(3,'Chen','London'),(4,'Dee','Oslo'),
  (5,'Eve',NULL);
INSERT INTO orders VALUES (10,1,30),(11,3,15),(12,1,50),(13,2,20),(14,3,5),(15,NULL,40),(16,9,10),(17,'3',7);
INSERT INTO items VALUES (10,100,1),(10,101,2),(11,100,5),(12,102,1),(12,102,3),(13,NULL,1),(14,104,2),
  (15,100,1),(99,101,1),(NULL,100,9);
INSERT INTO products VALUES (100,'pen',1.5),(101,'ink',4.0),(102,'pad',2.25),(103,'nib',0.5);
INSERT INTO cities VALUES ('London','UK'),('Paris','FR'),('Oslo','NO'),('London','CA'),(NULL,'XX');
INSERT INTO countries VALUES ('UK','United Kingdom'),('FR','France'),('NO','Norway'),('UK','Britain');
CREATE TABLE u(k TEXT UNIQUE, v);
INSERT INTO u VALUES ('London', 'uk'), ('Paris', 'fr'), ('1', 'one');
CREATE TABLE pairs(a, b, v);
INSERT INTO pairs VALUES (1, 'x', 'p1'), ('1', 'y', 'p2'), (2, 'z', 'p3'), ('Ada', 'w', 'p4');
"""

INDEXES = """CREATE INDEX orders_customer ON orders(customer_id);
CREATE INDEX items_order ON items(order_id);
CREATE INDEX cities_name ON cities(name);
CREATE INDEX countries_code ON countries(code);
CREATE INDEX orders_total ON orders(total);
CREATE INDEX pairs_ab ON pairs(a, b);
"""

CO = "customers c JOIN orders o ON o.customer_id = c.id"

QUERIES = [
    # an index lookup per outer row; the term either way round; in ON or WHERE
    f"SELECT c.name, o.id, o.total FROM {CO} ORDER BY c.id, o.id",
    "SELECT c.name, o.id FROM customers c JOIN orders o ON c.id = o.customer_id ORDER BY c.id, o.id",
    "SELECT c.name, o.id FROM customers c, orders o WHERE o.customer_id = c.id ORDER BY c.id, o.id",
    "SELECT c.name, o.id FROM customers c, orders o WHERE o.customer_id = c.id AND c.city = 'London' "
    "ORDER BY c.id, o.id",
    "SELECT c.name, o.id FROM customers c JOIN orders o ON 1 WHERE c.id = o.customer_id AND o.total > 10 "
    "ORDER BY c.id, o.id",
    # a rowid lookup: by the INTEGER PRIMARY KEY, rowid, oid
    "SELECT o.id, c.name FROM orders o JOIN customers c ON c.id = o.customer_id ORDER BY o.id",
    "SELECT o.id, c.name FROM orders o JOIN customers c ON o.customer_id = c.rowid ORDER BY o.id",
    "SELECT o.id, c.name FROM orders o, customers c WHERE c.oid = o.customer_id ORDER BY o.id",
    "SELECT o.id, c.name FROM orders o CROSS JOIN customers c ON c._rowid_ = o.customer_id ORDER BY o.id",
    # the rowid first when both fit; a term on a table further right is not a key
    "SELECT c.name, o.id FROM customers c JOIN orders o ON o.customer_id = c.id AND o.id = c.id + 9 "
    "ORDER BY c.id, o.id",
    "SELECT c.name, o.id, ci.country FROM customers c JOIN orders o ON 1 JOIN cities ci "
    "ON o.customer_id = c.id AND ci.name = c.city ORDER BY c.id, o.id, ci.country",
    # a key that is an expression of the outer row; one that reads the inner table is not a key
    "SELECT o.id, c.name FROM orders o JOIN customers c ON c.id = o.customer_id + 0 ORDER BY o.id",
    "SELECT o.id, c.name FROM orders o JOIN customers c ON c.id = o.total / 10 ORDER BY o.id",
    "SELECT o.id, c.name FROM orders o JOIN customers c ON c.id = abs(o.customer_id - 6) ORDER BY o.id, c.id",
    "SELECT c.name, o.id FROM customers c JOIN orders o ON o.customer_id = (c.id + 1) - 1 ORDER BY c.id, o.id",
    "SELECT c.name, o.id FROM customers c JOIN orders o ON o.total = c.id * 10 ORDER BY c.id, o.id",
    "SELECT c.name, o.id FROM customers c JOIN orders o ON o.customer_id = c.id || '' ORDER BY c.id, o.id",
    "SELECT c.name, o.id FROM customers c JOIN orders o ON o.customer_id = o.total - o.total + c.id "
    "ORDER BY c.id, o.id",
    "SELECT o.id, c.name FROM orders o JOIN customers c ON c.id = coalesce(o.customer_id, 4) ORDER BY o.id",
    # constant keys
    "SELECT c.name, o.id FROM customers c JOIN orders o ON o.customer_id = 1 ORDER BY c.id, o.id",
    "SELECT c.name, o.id FROM customers c JOIN orders o ON o.customer_id = '3' ORDER BY c.id, o.id",
    "SELECT c.name, o.id FROM customers c JOIN orders o ON o.customer_id = 3.0 ORDER BY c.id, o.id",
    "SELECT c.name, o.id FROM customers c JOIN orders o ON o.id = 12 ORDER BY c.id",
    "SELECT c.name, o.id FROM customers c JOIN orders o ON o.id = '12' ORDER BY c.id",
    "SELECT c.name, o.id FROM customers c JOIN orders o ON o.id = 12.0 ORDER BY c.id",
    "SELECT c.name, o.id FROM customers c JOIN orders o ON o.id = 12.5 ORDER BY c.id",
    "SELECT c.name, o.id FROM customers c JOIN orders o ON o.id = 'x' ORDER BY c.id",
    "SELECT c.name, o.id FROM customers c JOIN orders o ON o.id = NULL ORDER BY c.id",
    "SELECT c.name, o.id FROM customers c JOIN orders o ON o.customer_id = NULL ORDER BY c.id",
    # NULL keys on either side find nothing; IS is not a lookup but still right
    "SELECT o.id, c.name FROM orders o JOIN customers c ON c.id = o.customer_id WHERE o.id >= 15 ORDER BY o.id",
    "SELECT c.name, ci.country FROM customers c JOIN cities ci ON ci.name = c.city ORDER BY c.id, ci.country",
    "SELECT c.name, o.id FROM customers c JOIN orders o ON o.customer_id IS c.id ORDER BY c.id, o.id",
    "SELECT ci.country, c.name FROM cities ci JOIN customers c ON c.city IS ci.name ORDER BY 1, 2",
    # duplicate keys on both sides
    "SELECT ci.country, co.name FROM cities ci JOIN countries co ON co.code = ci.country ORDER BY 1, 2",
    "SELECT c.name, ci.country, co.name FROM customers c JOIN cities ci ON ci.name = c.city "
    "JOIN countries co ON co.code = ci.country ORDER BY c.id, ci.country, co.name",
    "SELECT o.id, it.product_id, it.qty FROM orders o JOIN items it ON it.order_id = o.id ORDER BY o.id, it.rowid",
    "SELECT x.id, y.id FROM orders x JOIN orders y ON y.customer_id = x.customer_id ORDER BY x.id, y.id",
    "SELECT x.id, y.id FROM orders x JOIN orders y ON y.total = x.total ORDER BY x.id, y.id",
    # chains: each table looks up the next
    "SELECT c.name, o.id, it.qty, p.title FROM customers c JOIN orders o ON o.customer_id = c.id "
    "JOIN items it ON it.order_id = o.id JOIN products p ON p.id = it.product_id ORDER BY c.id, o.id, it.rowid",
    "SELECT p.title, it.qty, o.id, c.name FROM products p JOIN items it ON it.product_id = p.id "
    "JOIN orders o ON o.id = it.order_id JOIN customers c ON c.id = o.customer_id ORDER BY p.id, it.rowid",
    "SELECT it.rowid, o.id, c.name, ci.country FROM items it, orders o, customers c, cities ci "
    "WHERE o.id = it.order_id AND c.id = o.customer_id AND ci.name = c.city ORDER BY 1, 4",
    # self-joins by rowid
    "SELECT x.id, y.id FROM orders x JOIN orders y ON y.id = x.id + 1 ORDER BY x.id",
    "SELECT a.name, b.name FROM customers a JOIN customers b ON b.id = a.id * 2 ORDER BY a.id",
    # LEFT JOIN: looked up by its own ON only, never by WHERE
    "SELECT c.name, o.id FROM customers c LEFT JOIN orders o ON o.customer_id = c.id ORDER BY c.id, o.id",
    "SELECT o.id, c.name FROM orders o LEFT JOIN customers c ON c.id = o.customer_id ORDER BY o.id",
    "SELECT c.name, o.id FROM customers c LEFT JOIN orders o ON o.customer_id = c.id AND o.total > 10 "
    "ORDER BY c.id, o.id",
    "SELECT c.name, o.id FROM customers c LEFT JOIN orders o ON 1 WHERE o.customer_id = c.id ORDER BY c.id, o.id",
    "SELECT c.name, o.id FROM customers c LEFT JOIN orders o ON o.total > 10 WHERE o.customer_id = c.id "
    "ORDER BY c.id, o.id",
    "SELECT c.name, o.id FROM customers c LEFT JOIN orders o ON o.customer_id = c.id WHERE o.id IS NULL "
    "ORDER BY c.id",
    "SELECT c.name, o.id, it.qty FROM customers c LEFT JOIN orders o ON o.customer_id = c.id "
    "LEFT JOIN items it ON it.order_id = o.id ORDER BY c.id, o.id, it.rowid",
    "SELECT c.name, o.id, it.qty FROM customers c LEFT JOIN orders o ON o.customer_id = c.id "
    "JOIN items it ON it.order_id = o.id ORDER BY c.id, o.id, it.rowid",
    "SELECT c.name, o.id, p.title FROM customers c LEFT JOIN orders o ON o.customer_id = c.id "
    "LEFT JOIN products p ON p.id = o.total + 90 ORDER BY c.id, o.id",
    # a UNIQUE constraint's index (08.07); the first column of a two-column index, which
    # has no affinity, so an INTEGER key cannot use it (its '1' would equal 1) and text can
    "SELECT c.name, u.v FROM customers c JOIN u ON u.k = c.city ORDER BY c.id",
    "SELECT o.id, u.v FROM orders o JOIN u ON u.k = o.customer_id ORDER BY o.id",
    "SELECT c.name, p.v FROM customers c JOIN pairs p ON p.a = c.id ORDER BY c.id, p.v",
    "SELECT c.name, p.v FROM customers c JOIN pairs p ON p.a = c.name ORDER BY c.id, p.v",
    "SELECT c.name, p.v FROM customers c JOIN pairs p ON p.a = c.id || '' ORDER BY c.id, p.v",
    # an empty inner or outer table
    "SELECT c.name FROM customers c JOIN blank b ON b.x = c.id",
    "SELECT c.name, b.x FROM customers c LEFT JOIN blank b ON b.rowid = c.id ORDER BY c.id",
    "SELECT * FROM blank b JOIN customers c ON c.id = b.x",
]

# EXPLAIN QUERY PLAN against sqlite3 (CROSS JOIN pins its order; automatic indexes off).
PLANS = [
    "SELECT * FROM customers AS c CROSS JOIN orders AS o ON o.customer_id = c.id",
    "SELECT * FROM orders AS o CROSS JOIN customers AS c ON c.id = o.customer_id",
    "SELECT * FROM orders AS o CROSS JOIN customers AS c ON c.rowid = o.customer_id + 1",
    "SELECT * FROM customers c CROSS JOIN orders o ON o.customer_id = c.id CROSS JOIN items it "
    "ON it.order_id = o.id CROSS JOIN products p ON p.id = it.product_id",
    "SELECT * FROM customers c CROSS JOIN cities ci ON ci.name = c.city CROSS JOIN countries co "
    "ON co.code = ci.country",
    "SELECT * FROM customers c LEFT JOIN orders o ON o.customer_id = c.id",
    "SELECT * FROM orders o LEFT JOIN customers c ON c.id = o.customer_id",
    "SELECT * FROM customers c CROSS JOIN orders o ON o.id = 12",
    "SELECT * FROM customers c CROSS JOIN orders o ON o.customer_id = c.id || ''",
    "SELECT * FROM customers c CROSS JOIN orders o ON o.customer_id + 0 = c.id",
    "SELECT * FROM customers c CROSS JOIN blank b ON b.x = c.id",
    "SELECT * FROM orders x CROSS JOIN orders y ON y.id = x.id + 1",
    "SELECT * FROM customers c CROSS JOIN u ON u.k = c.city",
    "SELECT * FROM orders o CROSS JOIN u ON u.k = o.customer_id",
    "SELECT * FROM customers c CROSS JOIN pairs p ON p.a = c.id",
    "SELECT * FROM customers c CROSS JOIN pairs p ON p.a = c.name",
]

EXPLAIN_INDEX = """Sort by c.id, o.id
  Filter (o.customer_id = c.id)
    Join
      Scan customers AS c
      Index lookup orders using orders_customer (customer_id = ?)
"""

EXPLAIN_ROWID = """Left join on (c.id = o.customer_id)
  Scan orders AS o
  Rowid lookup customers rowid = ?
"""

# The affinity pairings: a table o_X and i_X for each column type X, each holding the
# same look-alike values; i_X has an index on k (the plain file has none), p an INTEGER
# PRIMARY KEY and p2 the same values in a plain INTEGER column.
TYPES = [("i", "INTEGER"), ("r", "REAL"), ("n", "NUMERIC"), ("t", "TEXT"), ("b", "BLOB"), ("x", "")]
VALUES = ["1", "1.0", "'1'", "'1.0'", "' 1'", "'1 '", "x'31'", "NULL", "'01'", "2", "'a'", "1.5", "'1e0'", "-0.0"]


def affinity_setup(indexed):
    sql = ""
    for name, typ in TYPES:
        for side in ("o", "i"):
            sql += f"CREATE TABLE {side}_{name}(k {typ}, tag);\n"
            sql += "".join(f"INSERT INTO {side}_{name} VALUES ({v}, {j});\n" for j, v in enumerate(VALUES))
        if indexed:
            sql += f"CREATE INDEX ix_{name} ON i_{name}(k);\n"
    sql += "CREATE TABLE p(k INTEGER PRIMARY KEY, tag);\nCREATE TABLE p2(k INTEGER, tag);\n"
    sql += "".join(f"INSERT INTO {t} VALUES ({v}, {v * 10});\n" for t in ("p", "p2") for v in (1, 2, 3))
    return sql


def affinity_queries():
    """(query for the indexed file, the same for the plain file)."""
    out = []
    for o, _ in TYPES:
        for i, _ in TYPES:
            for on in ("i.k = o.k", "o.k = i.k", "i.k = o.k || ''", "i.k = o.k + 0", "i.k = +o.k"):
                q = f"SELECT o.tag, i.tag FROM o_{o} o CROSS JOIN i_{i} i ON {on} ORDER BY 1, 2"
                out.append((q, q))
        for on in ("p.k = o.k", "o.k = p.rowid", "p.k = o.k || ''", "p.k = o.k + 0"):
            q = f"SELECT o.tag, p.tag FROM o_{o} o CROSS JOIN p ON {on} ORDER BY 1, 2"
            out.append((q, q.replace("p.", "p2.").replace("JOIN p ON", "JOIN p2 ON").replace("p2.rowid", "p2.k")))
    for i, _ in TYPES:
        for v in VALUES:
            q = f"SELECT o.tag, i.tag FROM o_n o CROSS JOIN i_{i} i ON i.k = {v} WHERE o.tag < 2 ORDER BY 1, 2"
            out.append((q, q))
    return out


def affinity_plans():
    return [f"SELECT * FROM o_{o} o CROSS JOIN i_{i} i ON {on}"
            for o, _ in TYPES for i, _ in TYPES for on in ("i.k = o.k", "o.k = i.k", "i.k = o.k || ''")]


def test(t):
    tr = t.track

    # the same queries with indexes and without: the same rows, and sqlite3's
    a, b = J.files(t, SHOP + INDEXES)
    plain = tr.path(t)
    tr.db(t, plain, SHOP)
    sql = J.listing(QUERIES)
    ours = J.compare(t, a, b, sql)
    bare = tr.db(t, plain, sql).out
    t.check(bare == ours, "the same joins give other rows without the indexes:\n" + tr._diff(ours, bare))
    J.compare(t, a, b, "".join(f"EXPLAIN QUERY PLAN {q};\n" for q in PLANS), theirs_first="PRAGMA automatic_index=OFF;\n")

    # EXPLAIN names the lookups
    out = tr.db(t, a, f"EXPLAIN SELECT c.name, o.id FROM {CO} ORDER BY c.id, o.id;\n").out
    t.check(out == EXPLAIN_INDEX, f"EXPLAIN of an index lookup:\n{out}\nexpected:\n{EXPLAIN_INDEX}")
    out = tr.db(t, a, "EXPLAIN SELECT * FROM orders o LEFT JOIN customers c ON c.id = o.customer_id;\n").out
    t.check(out == EXPLAIN_ROWID, f"EXPLAIN of a rowid lookup:\n{out}\nexpected:\n{EXPLAIN_ROWID}")
    out = tr.db(t, plain, f"EXPLAIN SELECT c.name, o.id FROM {CO};\n").out
    t.check("Scan orders AS o" in out, f"with no index the inner table is scanned:\n{out}")
    # a LEFT JOIN table takes its key from its own ON, never from WHERE (sqlite3 turns this
    # one into an inner join first, so only the rows, above, are compared with it)
    out = tr.db(t, a, "EXPLAIN QUERY PLAN SELECT * FROM customers c LEFT JOIN orders o ON o.total > 10 "
                      "WHERE o.customer_id = c.id;\n").out
    t.check(out == "QUERY PLAN\n|--SCAN c\n`--SCAN o LEFT-JOIN\n", f"a LEFT JOIN looked up by WHERE:\n{out}")
    out = tr.db(t, a, "EXPLAIN QUERY PLAN SELECT * FROM customers c LEFT JOIN orders o ON o.customer_id = c.id "
                      "WHERE o.total = 10;\n").out
    t.check(out == "QUERY PLAN\n|--SCAN c\n`--SEARCH o USING INDEX orders_customer (customer_id=?) LEFT-JOIN\n",
            f"a LEFT JOIN looked up by its ON:\n{out}")

    # a key that cannot be evaluated is an error, in both
    tr.errors_alike(t, "CREATE TABLE a(x);\nCREATE TABLE b(id INTEGER PRIMARY KEY);\n"
                       "INSERT INTO a VALUES (-9223372036854775808);\nINSERT INTO b VALUES (1);\n",
                    "SELECT * FROM a JOIN b ON b.id = abs(a.x);\n")

    # every pairing of affinities over look-alike values: an index lookup, a rowid lookup
    # and a scan give the same rows, sqlite3's; SEARCH where sqlite3 searches
    a2, b2 = J.files(t, affinity_setup(True))
    plain2 = tr.path(t)
    tr.db(t, plain2, affinity_setup(False))
    pairs = affinity_queries()
    ours = J.compare(t, a2, b2, J.listing(q for q, _ in pairs))
    bare = tr.db(t, plain2, J.listing(p for _, p in pairs)).out
    t.check(bare == ours, "an affinity pairing gives other rows looked up than scanned:\n" + tr._diff(ours, bare))
    J.compare(t, a2, b2, "".join(f"EXPLAIN QUERY PLAN {q};\n" for q in affinity_plans()),
              theirs_first="PRAGMA automatic_index=OFF;\n")

    # a few thousand rows, a two-page cache: the same rows looked up as scanned, and the
    # lookup reads a small part of the pages
    big = ("CREATE TABLE customers(id INTEGER PRIMARY KEY, name TEXT, city TEXT);\n"
           "CREATE TABLE orders(id INTEGER PRIMARY KEY, customer_id INTEGER, total INTEGER, note TEXT);\nBEGIN;\n" +
           "".join(f"INSERT INTO customers VALUES ({i}, 'customer {i}', 'city {i % 17}');\n" for i in range(1, 2001)) +
           "".join(f"INSERT INTO orders VALUES ({i}, {i * 7919 % 2000 + 1}, {i % 97}, '{'n' * (3000 if i % 700 == 0 else 40)}');\n"
                   for i in range(1, 4001)) +
           "COMMIT;\n")
    a3, b3 = J.files(t, big + "CREATE INDEX orders_customer ON orders(customer_id);\n")
    plain3 = tr.path(t)
    tr.db(t, plain3, big)
    for q in ["SELECT c.name, o.id, o.note FROM customers c JOIN orders o ON o.customer_id = c.id",
              "SELECT o.id, c.name, o.note FROM orders o JOIN customers c ON c.id = o.customer_id WHERE o.total < 5",
              "SELECT c.id, o.id, o.note FROM customers c LEFT JOIN orders o ON o.customer_id = c.id AND o.total = 3"]:
        ours = J.compare(t, a3, b3, f"{q};\n", sort=True)
        bare = tr.db(t, plain3, f"{q};\n", env={"DB_CACHE_PAGES": "2"}).out
        t.check(J.lines(bare) == ours, f"looked up and scanned differ: {q}")
    # one key's rows come out of the index in rowid order, as a scan finds them
    q = "SELECT c.name, o.id FROM customers c JOIN orders o ON o.customer_id = c.id;\n"
    t.check(tr.db(t, a3, q).out == tr.db(t, plain3, q).out, "looked up, the rows come out in another order")
    # pages asked for (from the cache or the file): the cache only shrinks between
    # output rows, so with few rows "pages read" counts each page once either way
    def pages(r):
        st = tr.stats(r.err)
        return st["cache hits"] + st["cache misses"]

    env = {"DB_CACHE_PAGES": "2", "DB_STATS": "1"}
    q = "SELECT c.name, o.id FROM customers c JOIN orders o ON o.customer_id = c.id WHERE c.id <= 100;\n"
    looked, scanned = tr.db(t, a3, q, env=env), tr.db(t, plain3, q, env=env)
    lp, sp = pages(looked), pages(scanned)
    t.check(J.lines(looked.out) == J.lines(scanned.out) and len(looked.lines()) == 200 and lp * 3 < sp,
            f"an index lookup should ask for far fewer pages than a scan: {lp} against {sp}, "
            f"{len(looked.lines())} rows")
    q = "SELECT o.id, c.name FROM orders o JOIN customers c ON c.id = o.customer_id WHERE o.id <= 200;\n"
    rowid = tr.db(t, a3, q, env=env)
    scan = tr.db(t, a3, q.replace("c.id = o.customer_id", "c.id + 0 = o.customer_id"), env=env)
    rp, sp = pages(rowid), pages(scan)
    t.check(rowid.out == scan.out and len(rowid.lines()) == 200 and rp * 3 < sp,
            f"a rowid lookup should ask for far fewer pages than a scan: {rp} against {sp}")

    # a quick slice of the fuzzer: random joins over tables with random indexes, which are
    # now looked up (another seed than 08.02's, so other cases)
    tr.fuzz(t, "join,leftjoin", n=300, seed=3)

    # SQLite's own joins, read with lookups now (select4's tables have indexes, and its joins
    # are on their columns), and random/groupby's joins of two and three tables
    tr.sqllogictest(t, have=("join",), scripts=J.SLT_JOINS + ["test/random/groupby/slt_good_0.test"])
