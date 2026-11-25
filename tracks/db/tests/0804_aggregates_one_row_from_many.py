"""08.04 Aggregates: one row from many

count(*), count(x), sum, total, avg, min and max over the whole input, of one table, of a
join and of no table at all, give sqlite3's answers: the same values and the same types
(sum an integer over integers, a real once a real or text is added, NULL over nothing,
"integer overflow" even when later values bring it back; total and avg always real;
count never NULL), the same compensated sum (ten 0.1s are exactly 1.0), min and max
across types, and the bare columns from the row sqlite3 takes them from. An empty input
still gives its one row. An aggregate where none may be (WHERE, ON, LIMIT, inside another
aggregate) and a wrong number of arguments are errors in both engines. Every query also
runs with a two-page cache, over tables of thousands of rows whose text spills to
overflow pages. Then the core and the join are untouched: 08.01's test, and the
sqllogictest slice with aggregates no longer skipped.
"""

import os

from harness.core import load_test

SHOP = """CREATE TABLE customers(id INTEGER PRIMARY KEY, name TEXT, city TEXT);
CREATE TABLE orders(id INTEGER PRIMARY KEY, customer_id INTEGER, total INTEGER);
INSERT INTO customers VALUES (1,'Ada','London'),(2,'Brook','Paris'),(3,'Chen','London'),(4,'Dee','Oslo');
INSERT INTO orders VALUES (10,1,30),(11,3,15),(12,1,50),(13,2,20),(14,3,5),(15,NULL,40);
CREATE TABLE blank(x, y);
"""

# The research file's tables (sqlite3 3.54.1 runs): result types, overflow, the compensated
# sum, min and max across types, and the rows bare columns come from.
EDGE = """CREATE TABLE e(x);
CREATE TABLE i(x); INSERT INTO i VALUES (1), (2), (NULL), (4);
CREATE TABLE m(x); INSERT INTO m VALUES (1), (2.0), (3);
CREATE TABLE n(x); INSERT INTO n VALUES (NULL), (NULL);
CREATE TABLE s(x); INSERT INTO s VALUES ('12'), ('abc'), (X'3132'), ('1.5'), (' 7 '), ('1e2'), ('0x10'), (''), ('-3abc');
CREATE TABLE big(x); INSERT INTO big VALUES (9223372036854775807), (1);
CREATE TABLE big2(x); INSERT INTO big2 VALUES (9223372036854775807), (1), (0.5);
CREATE TABLE big3(x); INSERT INTO big3 VALUES (9223372036854775807), (1), (-1);
CREATE TABLE big4(x); INSERT INTO big4 VALUES (-9223372036854775808), (-1);
CREATE TABLE big5(x); INSERT INTO big5 VALUES (9007199254740993), (9007199254740993), (0.5);
CREATE TABLE mm(x); INSERT INTO mm VALUES (NULL), ('a'), (X'00'), (2.5), (1), ('B');
CREATE TABLE tenth(x); INSERT INTO tenth VALUES (0.1), (0.1), (0.1), (0.1), (0.1), (0.1), (0.1), (0.1), (0.1), (0.1);
CREATE TABLE kb(x); INSERT INTO kb VALUES (1e100), (1.0), (-1e100);
CREATE TABLE inf(x); INSERT INTO inf VALUES (1e308), (1e308);
CREATE TABLE ninf(x); INSERT INTO ninf VALUES (1e308), (1e308), (-1e308), (-1e308);
CREATE TABLE p(id INTEGER PRIMARY KEY, a, b);
INSERT INTO p(a, b) VALUES ('first', 5), ('second', 9), ('third', 2), ('fourth', 9), ('fifth', NULL);
CREATE TABLE z(a, b); INSERT INTO z VALUES ('r1', NULL), ('r2', NULL), ('r3', NULL);
CREATE TABLE w(a, b); INSERT INTO w VALUES ('w1', NULL), ('w2', 3), ('w3', NULL), ('w4', 3), ('w5', 1);
CREATE TABLE ty(v); INSERT INTO ty VALUES (1), (1.0), ('1'), (X'01'), (NULL), (-0.0), (0), ('');
"""

JOIN = "customers c JOIN orders o ON o.customer_id = c.id"

SHOP_QUERIES = [
    # the data set: 6 orders, 5 with a customer, 160 in all
    "SELECT count(*), count(customer_id), sum(total), total(total), avg(total), min(total), max(total) FROM orders",
    "SELECT count(*), count(customer_id), sum(customer_id), avg(customer_id), min(customer_id), max(customer_id) "
    "FROM orders",
    "SELECT count(*), sum(total) FROM orders WHERE total > 15",
    "SELECT count(*), sum(total) FROM orders WHERE customer_id = 1",
    "SELECT count(*), sum(total), min(id), max(id) FROM orders WHERE id > 11 AND id < 15",
    "SELECT count(*) FROM customers WHERE city = 'London'",
    "SELECT min(name), max(name), min(city), max(city), count(city) FROM customers",
    # an empty input: still one row, the right empty answers, and with WHERE false
    "SELECT count(*), count(x), sum(x), total(x), avg(x), min(x), max(x), typeof(sum(x)), typeof(total(x)), "
    "typeof(avg(x)), typeof(count(x)) FROM blank",
    "SELECT count(*), sum(total), max(total) FROM orders WHERE 0",
    "SELECT count(*), sum(total) FROM orders WHERE total > 1000",
    "SELECT x, y, count(*) FROM blank",
    "SELECT rowid, count(*) FROM orders WHERE 0",
    "SELECT id, rowid, count(*), name FROM customers WHERE id > 9",
    # over a join, and a join that matches nothing
    f"SELECT count(*), count(c.id), sum(o.total), avg(o.total), min(c.name), max(o.id) FROM {JOIN}",
    f"SELECT count(*), sum(o.total) FROM {JOIN} WHERE c.city = 'London'",
    "SELECT count(*), sum(o.total), min(c.name) FROM customers c JOIN orders o ON o.customer_id = c.id + 100",
    "SELECT count(*), count(o.customer_id) FROM customers c, orders o",
    "SELECT count(*) FROM customers c, orders o, customers d",
    "SELECT count(*), sum(b.x) FROM customers c, blank b",
    # aggregates inside expressions, the same call twice, constants, no FROM at all
    "SELECT sum(total) + 1, count(*) * 2, max(total) || 'z', -min(total), NOT count(*) FROM orders",
    "SELECT max(total) - min(total), avg(total) * count(*) = sum(total), sum(total) / count(*) FROM orders",
    "SELECT max(total), max(total) + 1, max(TOTAL), MAX(total) FROM orders",
    "SELECT count(*), count(), count(1), count(NULL), sum(1), sum(NULL), max('x'), min(2) FROM orders",
    "SELECT count(*)",
    "SELECT count(*), sum(1), total(2), avg(3), min(4), max(5), count(6)",
    "SELECT max(5), count(*), sum(1) WHERE 0",
    "SELECT count(*) = 0, sum(x) IS NULL FROM blank",
    "SELECT count(ALL customer_id), sum(ALL total), count( all total ) FROM orders",
    "SELECT abs(-sum(total)), coalesce(sum(x), 'none'), typeof(max(total)) FROM orders, blank",
    # ORDER BY, LIMIT and OFFSET on the one row
    "SELECT count(*) FROM orders ORDER BY count(*)",
    "SELECT sum(total) AS s FROM orders ORDER BY s DESC",
    "SELECT count(*) FROM orders LIMIT 1",
    "SELECT count(*) FROM orders LIMIT 0",
    "SELECT count(*) FROM orders LIMIT 1 OFFSET 1",
    "SELECT count(*) FROM orders LIMIT -1",
    # bare columns: no min() or max(), the first row; one, the row that set it
    "SELECT name, count(*) FROM customers",
    "SELECT id, name, max(id) FROM customers",
    "SELECT name, city, min(id) FROM customers WHERE city = 'London'",
    "SELECT name, min(name) FROM customers",
    "SELECT id, customer_id, max(total) FROM orders",
    "SELECT id, customer_id, min(customer_id) FROM orders",
    "SELECT *, count(*) FROM customers",
    "SELECT rowid, name, max(name) FROM customers",
    "SELECT o.id, c.name, max(o.total) FROM customers c JOIN orders o ON o.customer_id = c.id",
    "SELECT o.id, c.name, min(o.total * 100 + o.id) FROM customers c, orders o WHERE o.customer_id = c.id",
]

EDGE_QUERIES = [
    "SELECT count(*), count(x), sum(x), total(x), avg(x), min(x), max(x), typeof(sum(x)), typeof(total(x)), "
    "typeof(avg(x)) FROM e",
    "SELECT count(*), count(x), sum(x), typeof(sum(x)), total(x), typeof(total(x)), avg(x), typeof(avg(x)) FROM i",
    "SELECT sum(x), typeof(sum(x)), avg(x), total(x) FROM m",
    "SELECT count(*), count(x), sum(x), total(x), avg(x), min(x), max(x), typeof(total(x)) FROM n",
    # what sum adds for text and blobs: a whole number as itself, anything else the number it starts with
    "SELECT sum(x), typeof(sum(x)) FROM s WHERE x = '12'",
    "SELECT sum(x), typeof(sum(x)), total(x), avg(x) FROM s WHERE x = 'abc'",
    "SELECT sum(x), typeof(sum(x)) FROM s WHERE typeof(x) = 'blob'",
    "SELECT sum(x), typeof(sum(x)), total(x), avg(x), count(x) FROM s",
    "SELECT x, sum(x), typeof(sum(x)), total(x), avg(x) FROM s WHERE rowid = 4",
    "SELECT x, sum(x), typeof(sum(x)) FROM s WHERE rowid = 5",
    "SELECT x, sum(x), typeof(sum(x)) FROM s WHERE rowid = 6",
    "SELECT x, sum(x), typeof(sum(x)) FROM s WHERE rowid = 7",
    "SELECT x, sum(x), typeof(sum(x)) FROM s WHERE rowid = 8",
    "SELECT x, sum(x), typeof(sum(x)) FROM s WHERE rowid = 9",
    "SELECT sum(x), typeof(sum(x)) FROM s WHERE rowid IN (1, 5)",
    # overflow: total and avg do not care; a real after the overflow makes sum a real
    "SELECT total(x), avg(x) FROM big",
    "SELECT sum(x), typeof(sum(x)), total(x), avg(x) FROM big2",
    "SELECT total(x), avg(x) FROM big3",
    "SELECT sum(x), typeof(sum(x)) FROM big5",
    "SELECT sum(x), total(x), avg(x) FROM big4 WHERE x < -1",
    "SELECT sum(-9223372036854775808), sum(-9223372036854775807), avg(9223372036854775807), "
    "total(9223372036854775807)",
    # the compensated sum: exactly 1.0, where adding doubles one by one gives 0.99999999999999989
    "SELECT sum(x) = 1.0, sum(x) - 1.0, total(x) = 1.0, avg(x) = 0.1, sum(x) FROM tenth",
    "SELECT sum(x), total(x), avg(x) FROM kb",
    "SELECT sum(x), total(x), avg(x) FROM inf",
    "SELECT sum(x), total(x), avg(x), typeof(sum(x)) FROM ninf",
    # min and max across types: NULL skipped, numbers, text, blobs, by value_compare
    "SELECT min(x), typeof(min(x)), max(x) = X'00', typeof(max(x)) FROM mm",
    "SELECT min(x), max(x) FROM mm WHERE typeof(x) IN ('integer', 'real', 'text')",
    "SELECT min(x), max(x) FROM mm WHERE typeof(x) = 'text'",
    "SELECT min(x), max(x), typeof(min(x)), typeof(max(x)) FROM mm WHERE x IS NOT NULL AND typeof(x) <> 'blob'",
    "SELECT min(v), typeof(min(v)), max(v) = X'01', typeof(max(v)), count(v), sum(v), typeof(sum(v)) FROM ty",
    "SELECT min(v), typeof(min(v)) FROM ty WHERE typeof(v) IN ('integer', 'real')",
    "SELECT max(v), typeof(max(v)) FROM ty WHERE typeof(v) IN ('integer', 'real')",
    "SELECT min(v), typeof(min(v)), max(v), typeof(max(v)) FROM ty WHERE rowid IN (1, 2)",
    "SELECT min(v), typeof(min(v)), max(v), typeof(max(v)) FROM ty WHERE rowid IN (6, 7)",
    # bare columns: the research file's rules, all of them
    "SELECT a, max(b) FROM p",
    "SELECT a, min(b) FROM p",
    "SELECT a, sum(b) FROM p",
    "SELECT a, count(*) FROM p WHERE b > 100",
    "SELECT a, max(b), min(b) FROM p",
    "SELECT a, min(b), max(b) FROM p",
    "SELECT a, max(b), min(b), max(b) FROM p",
    "SELECT a, min(b), max(b), min(b) FROM p",
    "SELECT a, max(b) FROM z",
    "SELECT a, sum(b) FROM z",
    "SELECT a, min(b) FROM w",
    "SELECT a, max(b) FROM w",
    "SELECT a, max(b), count(*) FROM w WHERE b IS NULL",
    "SELECT id, a, max(b) FROM p WHERE b < 9",
    "SELECT a, b, max(b) + min(b) FROM p",
    "SELECT a, max(a), b FROM p",
    "SELECT rowid, id, max(b), a FROM p",
    "SELECT a, sum(b), max(b) - 9 FROM p",
]

# Errors in both engines (errors_alike); the text after "Error: " must be sqlite3's.
ERRORS = [
    ("SELECT * FROM p WHERE count(*) > 1", "misuse of aggregate function count()"),
    ("SELECT max(count(*)) FROM p", "misuse of aggregate function count()"),
    ("SELECT sum(max(b)) FROM p", "misuse of aggregate function max()"),
    ("SELECT sum(b + avg(b)) FROM p", "misuse of aggregate function avg()"),
    ("SELECT count(a, b) FROM p", "wrong number of arguments to function count()"),
    ("SELECT sum() FROM p", "wrong number of arguments to function sum()"),
    ("SELECT avg(*) FROM p", "wrong number of arguments to function avg()"),
    ("SELECT total(a, b) FROM p", "wrong number of arguments to function total()"),
    ("SELECT max() FROM p", "wrong number of arguments to function max()"),
    ("SELECT min(*) FROM p", "wrong number of arguments to function min()"),
    ("SELECT sum(*) FROM p", "wrong number of arguments to function sum()"),
    ("SELECT a FROM p WHERE count(a, b) > 1", "wrong number of arguments to function count()"),
    ("SELECT count(a, b) FROM p WHERE count(*) > 1", "wrong number of arguments to function count()"),
    ("SELECT a FROM p ORDER BY count(*)", "misuse of aggregate: count()"),
    ("SELECT a FROM p ORDER BY sum(b) + 1", "misuse of aggregate: sum()"),
    ("SELECT count(*) AS c FROM p WHERE b > 1 AND max(b) > 1", "misuse of aggregate function max()"),
    ("SELECT count(*) FROM p LIMIT count(*)", "misuse of aggregate function count()"),
    ("SELECT count(*) FROM p LIMIT 1 OFFSET max(1)", "misuse of aggregate function max()"),
    ("SELECT c.name FROM customers c JOIN orders o ON count(*) > 0", "misuse of aggregate function count()"),
    ("SELECT count(*) FROM customers c JOIN orders o ON sum(o.total) > 0", "misuse of aggregate: sum()"),
    ("SELECT count(*) FROM customers c, orders o WHERE max(o.total) > 0", "misuse of aggregate function max()"),
    ("SELECT sum(x) FROM big", "integer overflow"),
    ("SELECT sum(x) FROM big3", "integer overflow"),
    ("SELECT count(*), sum(x) FROM big WHERE x > 0", "integer overflow"),
    ("SELECT sum(x) FROM big4", "integer overflow"),
    ("SELECT max(nope) FROM p", "no such column: nope"),
    ("SELECT count(*) FROM nope", "no such table: nope"),
]

# What 08.04 does not build: refused by name (sqlite3 runs each of them).
REFUSED = [
    ("SELECT group_concat(name) FROM customers", "group_concat is not supported"),
    ("SELECT count(*), string_agg(name, ',') FROM customers", "string_agg is not supported"),
]

# EXPLAIN QUERY PLAN where sqlite3 must print the same lines: no index sqlite3 could use
# for a count(*) or a lone min() or max(), CROSS JOIN with automatic indexes off.
PLANS = [
    "SELECT count(*), sum(total) FROM orders",
    "SELECT count(*) FROM orders WHERE id > 11",
    "SELECT max(total), min(total) FROM orders",
    "SELECT count(*) FROM customers AS c CROSS JOIN orders AS o ON o.customer_id = c.id",
    "SELECT sum(o.total), max(c.name) FROM customers AS c CROSS JOIN orders AS o WHERE c.id = 2",
    "SELECT count(*) FROM orders ORDER BY count(*)",
]

EXPLAIN_TREE = """Aggregate count(*), sum(o.total), max(c.name)
  Filter (o.customer_id = c.id)
    Join
      Filter (c.city = 'London')
        Scan customers AS c
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


def compare(t, a, b, sql, theirs_first="", sort=False, env=None):
    """sql through ./db on file a, with the default cache and with a two-page cache, and
    through sqlite3 on b (theirs_first before it): the answers must agree (sorted line by
    line, with sort; floats as numbers)."""
    tr = t.track
    ours = tr.db(t, a, sql, env=env).out
    tiny = tr.db(t, a, sql, env=dict(env or {}, DB_CACHE_PAGES="2")).out
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


def listing(queries):
    return "".join(f"{q};\nSELECT '--';\n" for q in queries)


def errors(t, setup, cases):
    """Each case is an error in both engines, with sqlite3's text."""
    tr = t.track
    for sql, msg in cases:
        r = tr.errors_alike(t, setup, f"{sql};\n")
        t.check(f"Error: {msg}\n" in r.err, f"{sql}: ./db should say {msg!r}, said:\n{r.err}")


def test(t):
    tr = t.track

    a, b = files(t, SHOP)
    compare(t, a, b, listing(SHOP_QUERIES))
    a2, b2 = files(t, EDGE)
    compare(t, a2, b2, listing(EDGE_QUERIES))

    # exactly sqlite3's text where floats print alike: types, the bare-column rows, the empty row
    exact = ("SELECT count(*), sum(total), typeof(sum(total)), typeof(total(total)), typeof(avg(total)), "
             "typeof(count(customer_id)) FROM orders;\nSELECT id, rowid, count(*), name FROM customers WHERE id > 9;\n"
             "SELECT name, city, min(id) FROM customers WHERE city = 'London';\n")
    ours, theirs = tr.db(t, a, exact).out, tr.sqlite(t, b, exact).out
    t.check(ours == theirs, f"./db printed {ours!r}, sqlite3 {theirs!r}")
    t.check(ours == "6|160|integer|real|real|integer\n||0|\nAda|London|1\n", f"the data set's answers: {ours!r}")

    errors(t, SHOP + EDGE, ERRORS)
    for q, msg in REFUSED:
        r = tr.db(t, a, f"{q};\n", check=False)
        t.check(r.rc != 0 and f"Error: {msg}" in r.err, f"{q} should be refused with {msg!r}, but:\n{r}")
        tr.sqlite(t, b, f"{q};\n")     # sqlite3 runs it: a feature, not an error
    # an error in the finish comes before any of the row is printed, as in sqlite3
    sql = "SELECT count(*) FROM big;\nSELECT count(*), sum(x) FROM big;\nSELECT 'next';\n"
    r, s = tr.db(t, a2, sql, check=False), tr.sqlite(t, b2, sql, check=False)
    t.check(r.out == s.out == "2\nnext\n" and r.err.strip() == "Error: integer overflow" and "integer overflow" in s.err,
            f"sum overflowing:\n{r}\nsqlite3:\n{s}")

    compare(t, a, b, "".join(f"EXPLAIN QUERY PLAN {q};\n" for q in PLANS), theirs_first="PRAGMA automatic_index=OFF;\n")
    out = tr.db(t, a, "EXPLAIN SELECT count(*), sum(o.total), max(c.name) FROM customers c JOIN orders o "
                      "ON o.customer_id = c.id WHERE c.city = 'London';\n").out
    t.check(out == EXPLAIN_TREE, f"EXPLAIN of an aggregate over a join:\n{out}\nexpected:\n{EXPLAIN_TREE}")
    # a query with no aggregate still has the core's plan (invariant 4)
    out = tr.db(t, a, "EXPLAIN SELECT name FROM customers WHERE id = 2 ORDER BY id;\n").out
    t.check(out == "Filter (id = 2)\n  Rowid lookup customers rowid = ?\n", f"the core's plan changed:\n{out}")

    # tables of many pages, pages evicted mid-query (a two-page cache), rows whose text spills
    # to overflow pages: min and max keep copies, and so does the group's own row
    big = ("CREATE TABLE p(id INTEGER PRIMARY KEY, k INTEGER, pad TEXT, r REAL);\n"
           "CREATE TABLE q(id INTEGER PRIMARY KEY, name TEXT, pad TEXT);\nBEGIN;\n" +
           "".join(f"INSERT INTO p VALUES ({i}, {i * 7 % 300 + 1}, '{chr(97 + i * 13 % 26) * (5000 if i % 500 == 0 else 120)}{i}', "
                   f"{i % 97 / 10});\n" for i in range(1, 3001)) +
           "".join(f"INSERT INTO q VALUES ({j}, 'name {j}', '{chr(97 + j % 26) * 200}');\n" for j in range(1, 301)) +
           "COMMIT;\n")
    a3, b3 = files(t, big)
    compare(t, a3, b3, "SELECT count(*), sum(k), avg(r), total(r), min(pad), max(pad), min(length(pad)), "
                       "max(length(pad)) FROM p;\n")
    compare(t, a3, b3, "SELECT count(*), sum(p.k), min(q.pad), max(p.pad), max(q.name), sum(length(p.pad)) "
                       "FROM p JOIN q ON q.id = p.k;\n")
    compare(t, a3, b3, "SELECT p.id, length(p.pad), q.name, max(p.id * 1000 + q.id) FROM p JOIN q ON q.id = p.k;\n")
    compare(t, a3, b3, "SELECT id, length(pad), max(pad), k FROM p;\n")
    compare(t, a3, b3, "SELECT id, length(pad), min(pad) FROM p WHERE id > 100;\n")
    compare(t, a3, b3, "SELECT id, length(pad), sum(r) FROM p WHERE id % 500 = 0;\n")
    compare(t, a3, b3, "SELECT max(p.pad), count(*) FROM p, q WHERE q.id < 3;\n")

    # a quick slice of the fuzzer: random tables, rows and aggregate queries, against sqlite3
    tr.fuzz(t, "join,aggregate", n=300, seed=1)

    # the join and the one-table core are untouched: 08.01's test (it runs 05.03's too)
    load_test(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "0801_two_tables_in_one_query_the_nested_loop_join.py")).test(t)
    # and the sqllogictest slice, with SQL that aggregates no longer skipped
    tr.sqllogictest(t, have=("join", "aggregate"))
