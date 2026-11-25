"""08.05 GROUP BY, HAVING and DISTINCT

GROUP BY on expressions, on a result column's number or alias, on several terms, over one
table and over a join, gives sqlite3's groups in sqlite3's order (key order: NULLs first,
1 and 1.0 one group, 1 and '1' two), with the bare columns and GROUP BY values from the
rows sqlite3 takes them from; an empty input gives no rows. HAVING works with and without
GROUP BY, on aggregates the result does not show, and through an alias. SELECT DISTINCT
keeps the first row of each result in the order rows come (as sqlite3 does on tables with
no index), NULLs equal and 1 equal to 1.0, with ORDER BY and LIMIT, over joins, with GROUP
BY. count, sum, total, avg, min and max take DISTINCT, sum's type from whichever equal
value came first. The set behind DISTINCT holds thousands of values, long text and blobs,
and gives the same answers when every hash collides (DB_SET_COLLIDE, a test aid). Every
query also runs with a two-page cache, over tables of thousands of rows with more than 256
groups or distinct rows, so pages are evicted between output rows while the operators hold
their state. HAVING terms on GROUP BY terms are checked on the rows, and the grouping sort
takes ORDER BY's directions, as in sqlite3 (both found by the fuzzer). Errors are sqlite3's.
Then a quick fuzzer slice, 08.04's test, and the sqllogictest slice with GROUP BY and
DISTINCT no longer skipped.
"""

import os

from harness.core import load_test

SHOP = """CREATE TABLE customers(id INTEGER PRIMARY KEY, name TEXT, city TEXT);
CREATE TABLE orders(id INTEGER PRIMARY KEY, customer_id INTEGER, total INTEGER);
INSERT INTO customers VALUES (1,'Ada','London'),(2,'Brook','Paris'),(3,'Chen','London'),(4,'Dee','Oslo');
INSERT INTO orders VALUES (10,1,30),(11,3,15),(12,1,50),(13,2,20),(14,3,5),(15,NULL,40);
CREATE TABLE blank(x, y);
"""

# The research file's tables (sqlite3 3.54.1 runs), and a few more.
EDGE = """CREATE TABLE t(id INTEGER PRIMARY KEY, g TEXT, h INTEGER, x INTEGER);
INSERT INTO t(g, h, x) VALUES ('b', 2, 3), ('a', 1, 1), (NULL, 1, 7), ('c', 2, 2), ('a', 2, 5), ('b', 1, NULL), (NULL, 2, 4);
CREATE TABLE k(v, w INTEGER);
INSERT INTO k VALUES (1.0, 1), (1, 2), ('1', 3), ('a', 4), ('A', 5), (NULL, 6), (NULL, 7), (X'61', 8);
CREATE TABLE k2(v); INSERT INTO k2 VALUES (1), (1.0);
CREATE TABLE k4(v INTEGER); INSERT INTO k4 VALUES (1), ('1'), (1.0);
CREATE TABLE p(id INTEGER PRIMARY KEY, a, b);
INSERT INTO p(a, b) VALUES ('first', 5), ('second', 9), ('third', 2), ('fourth', 9), ('fifth', NULL);
CREATE TABLE w(a, b, c); INSERT INTO w VALUES ('w1', NULL, 1), ('w2', 3, 1), ('w3', NULL, 2), ('w4', 3, 2), ('w5', 1, 1),
  ('w6', 3, 2), ('w7', 1, 2);
CREATE TABLE ss(h, x); INSERT INTO ss VALUES (1, 10), (1, 11), (2, 12);
CREATE TABLE d(x); INSERT INTO d VALUES (1.0), (1), (2), (2), (NULL), (NULL), (3);
CREATE TABLE d2(x); INSERT INTO d2 VALUES (1), (1.0), (2);
CREATE TABLE hv(g, x); INSERT INTO hv VALUES (1, 5), (2, 9223372036854775807), (2, 1);
CREATE TABLE mix(v, n); INSERT INTO mix VALUES (1, 1), ('1', 2), (1.0, 3), (X'31', 4), (NULL, 5), ('a', 6), (2, 7), (NULL, 8),
  (2.0, 9), ('a', 10), (X'31', 11), (-0.0, 12), (0, 13), ('', 14), (9223372036854775807, 15), (9.2233720368547758e18, 16),
  (1.5, 17), (1.5, 18);
"""

JOIN = "customers c JOIN orders o ON o.customer_id = c.id"

GROUP_QUERIES = [
    # the data set: a group per customer_id, the NULL one first; a row per city with a HAVING
    "SELECT customer_id, count(*), sum(total) FROM orders GROUP BY customer_id",
    f"SELECT city, count(*), sum(total) FROM {JOIN} GROUP BY city HAVING count(*) > 1 ORDER BY 3 DESC",
    f"SELECT city, count(*), sum(total) FROM {JOIN} GROUP BY city",
    f"SELECT c.name, count(o.id), sum(o.total), max(o.total) FROM {JOIN} GROUP BY c.id",
    f"SELECT c.city, c.name, count(*) FROM {JOIN} GROUP BY c.city, c.name",
    f"SELECT c.city, count(*) FROM {JOIN} GROUP BY 1 ORDER BY 2 DESC, 1",
    f"SELECT c.city AS place, sum(o.total) AS money FROM {JOIN} GROUP BY place ORDER BY money",
    f"SELECT o.total > 20, count(*) FROM {JOIN} GROUP BY o.total > 20",
    "SELECT c.city, count(*) FROM customers c, orders o GROUP BY c.city",
    "SELECT c.rowid, count(*) FROM customers c, orders o WHERE o.customer_id = c.id GROUP BY c.rowid",
    "SELECT o.customer_id IS NULL, count(*) FROM orders o GROUP BY 1",
    # the research file's GROUP BY runs
    "SELECT g, count(*), sum(x) FROM t GROUP BY g",
    "SELECT h, g, count(*) FROM t GROUP BY h, g",
    "SELECT g, count(*) AS n FROM t GROUP BY g ORDER BY count(*) DESC, g LIMIT 2",
    "SELECT g, count(*) FROM t GROUP BY g ORDER BY g DESC",
    # rows ORDER BY finds equal come in the groups' order, which takes ORDER BY's direction
    # when the two clauses have as many terms (select.c, sqlite3CopySortOrder)
    "SELECT g, count(*) FROM t GROUP BY g ORDER BY count(*) DESC",
    "SELECT g, count(*) FROM t GROUP BY g ORDER BY count(*)",
    "SELECT g, count(*) FROM t GROUP BY g ORDER BY count(*) DESC LIMIT 2",
    "SELECT g, count(*) FROM t GROUP BY g HAVING count(*) > 1 ORDER BY count(*) DESC",
    "SELECT h, x > 2, count(*) FROM t GROUP BY h, x > 2 ORDER BY count(*) DESC, 1 DESC",
    "SELECT h, x > 2, count(*) FROM t GROUP BY h, x > 2 ORDER BY count(*), 1",
    "SELECT h, g, count(*) FROM t GROUP BY h, g ORDER BY count(*) DESC",
    "SELECT x % 2 AS parity, count(*) FROM t GROUP BY x % 2",
    "SELECT x % 2 AS parity, count(*) FROM t GROUP BY 1",
    "SELECT x % 2 AS parity, count(*) FROM t GROUP BY parity",
    "SELECT x % 2 AS h, count(*) FROM ss GROUP BY h",
    "SELECT v, typeof(v), count(*) FROM k GROUP BY v",
    "SELECT v, typeof(v), count(*) FROM k2 GROUP BY v",
    "SELECT v, typeof(v), count(*) FROM k4 GROUP BY v",
    "SELECT v, max(w) FROM k WHERE typeof(v) <> 'text' AND v IS NOT NULL AND typeof(v) <> 'blob' GROUP BY v",
    "SELECT v, typeof(v), min(n), max(n) FROM mix GROUP BY v",
    "SELECT v, typeof(v), count(*), sum(n) FROM mix GROUP BY v, v",
    "SELECT count(*) FROM t HAVING count(*) > 100",
    "SELECT count(*) FROM t HAVING count(*) > 1",
    "SELECT g, count(*) FROM t GROUP BY g HAVING g = 'a'",
    "SELECT g FROM t GROUP BY g HAVING count(*) > 1",
    "SELECT g, x FROM t GROUP BY g HAVING x > 1",
    "SELECT h, count(*) AS n FROM t GROUP BY h HAVING n > 3",
    "SELECT h, sum(x) AS s FROM t GROUP BY h HAVING s > 10 ORDER BY s",
    "SELECT g, sum(x) FROM t GROUP BY g HAVING sum(x) IS NULL OR sum(x) > 5 ORDER BY g",
    "SELECT g, avg(x), total(x), typeof(avg(x)) FROM t GROUP BY g HAVING max(x) - min(x) >= 0 OR max(x) IS NULL",
    "SELECT g FROM t GROUP BY g HAVING min(h) = 1 AND max(h) = 2",
    "SELECT count(*), sum(x) FROM t HAVING sum(x) > 20",
    "SELECT count(*), sum(x) FROM t WHERE 0 HAVING count(*) = 0",
    # a HAVING term that reads only GROUP BY terms and constants is checked on the rows, in
    # WHERE (select.c, havingToWhere): a group it rules out is never finished, and only the
    # rows it keeps are counted (found by the fuzzer, seed 2, cases 1287 and 2335)
    "SELECT g, sum(x) FROM hv GROUP BY g HAVING g = 1",
    "SELECT g, sum(x) FROM hv GROUP BY g HAVING g = 1 AND count(*) > 0",
    "SELECT g, sum(x) FROM hv GROUP BY g HAVING sum(x) > 0 AND g < 2",
    "SELECT g, sum(x) FROM hv GROUP BY g HAVING 0.0",
    "SELECT g, sum(x) FROM hv GROUP BY g HAVING NULL",
    "SELECT g FROM hv GROUP BY g HAVING g = 2 OR count(*) = 1",
    "SELECT v, count(*), min(w) FROM k GROUP BY v HAVING typeof(v) = 'integer'",
    "SELECT v, count(*), min(w) FROM k GROUP BY v HAVING typeof(v) = 'real'",
    "SELECT v, count(*) FROM k GROUP BY v HAVING v + 0 = 1 AND count(*) > 0",
    "SELECT g, h, count(*) FROM t GROUP BY g, h HAVING h = 2 AND g IS NOT NULL AND count(*) = 1",
    # groups of groups: no aggregate, aggregates only in ORDER BY or HAVING, keys not shown
    "SELECT g FROM t GROUP BY g",
    "SELECT h FROM t GROUP BY h, g ORDER BY h, g",
    "SELECT count(*) FROM t GROUP BY g",
    "SELECT g FROM t GROUP BY g ORDER BY count(*) DESC, g",
    "SELECT g FROM t GROUP BY g ORDER BY max(x)",
    "SELECT h FROM t GROUP BY h HAVING count(DISTINCT g) > 2",
    # expressions, constants, rowids, LIMIT and OFFSET; an empty input gives no groups
    "SELECT h * 10 + (x > 2), count(*) FROM t GROUP BY h * 10 + (x > 2)",
    "SELECT g || h, count(*) FROM t GROUP BY g || h",
    "SELECT count(*), sum(x) FROM t GROUP BY 'x'",
    "SELECT count(*) FROM t GROUP BY 2.0",
    "SELECT rowid % 2, count(*), min(rowid), max(rowid) FROM t GROUP BY rowid % 2",
    "SELECT rowid, count(*) FROM t GROUP BY rowid % 2 ORDER BY 1",
    "SELECT h, count(*) FROM t GROUP BY h LIMIT 1",
    "SELECT h, count(*) FROM t GROUP BY h LIMIT 1 OFFSET 1",
    "SELECT g, count(*) FROM t GROUP BY g LIMIT 2 OFFSET 1",
    "SELECT g, count(*) FROM t WHERE 0 GROUP BY g",
    "SELECT count(*) FROM blank GROUP BY x",
    "SELECT count(*), max(x) FROM blank GROUP BY x HAVING 1",
    "SELECT count(*), 1 GROUP BY 2",
    "SELECT x + 1 AS y, count(*) FROM t GROUP BY y ORDER BY y",
    "SELECT h AS g, count(*) FROM t GROUP BY g",
    "SELECT h AS hh, count(*) FROM t GROUP BY hh + 0",
    # bare columns per group: the first row of the group, or the row a min() or max() took
    "SELECT a, max(b) FROM p GROUP BY b > 4",
    "SELECT a, sum(b) FROM p GROUP BY b > 4",
    "SELECT c, a, max(b) FROM w GROUP BY c",
    "SELECT c, a, min(b) FROM w GROUP BY c",
    "SELECT c, a, min(b), max(b) FROM w GROUP BY c",
    "SELECT c, a, count(*) FROM w GROUP BY c",
    "SELECT b, a, max(c) FROM w GROUP BY b",
    "SELECT g, id, x, max(x) FROM t GROUP BY g",
    f"SELECT c.city, c.name, o.id, max(o.total) FROM {JOIN} GROUP BY c.city",
]

DISTINCT_QUERIES = [
    "SELECT DISTINCT city FROM customers",
    "SELECT DISTINCT customer_id FROM orders",
    # the research file's runs: first-seen order (no index), NULLs one row, LIMIT, ORDER BY
    "SELECT DISTINCT g FROM t",
    "SELECT DISTINCT g FROM t LIMIT 2",
    "SELECT DISTINCT g FROM t LIMIT 2 OFFSET 1",
    "SELECT DISTINCT g, h FROM t ORDER BY h",
    "SELECT DISTINCT g FROM t ORDER BY g",
    "SELECT DISTINCT g FROM t ORDER BY g DESC LIMIT 2",
    "SELECT DISTINCT h, g FROM t",
    "SELECT DISTINCT h FROM t ORDER BY h DESC LIMIT 1",
    "SELECT ALL h FROM t",
    # 1 and 1.0 are one row (the first spelling seen), 1 and '1' two; NULLs one
    "SELECT DISTINCT v FROM k",
    "SELECT DISTINCT v, typeof(v) FROM k",
    "SELECT DISTINCT v FROM mix",
    "SELECT DISTINCT v, typeof(v) FROM mix",
    "SELECT DISTINCT v FROM k2",
    "SELECT DISTINCT x FROM d",
    # expressions, constants, *, LIMIT 0
    "SELECT DISTINCT h + 1, h * 0 FROM t",
    "SELECT DISTINCT 1 FROM t",
    "SELECT DISTINCT NULL FROM t",
    "SELECT DISTINCT g IS NULL FROM t",
    "SELECT DISTINCT x % 3, x IS NULL FROM t",
    "SELECT DISTINCT * FROM ss",
    "SELECT DISTINCT h, h FROM t",
    "SELECT DISTINCT g FROM t LIMIT 0",
    "SELECT DISTINCT x FROM blank",
    "SELECT DISTINCT 'a'",
    # with GROUP BY and aggregates
    "SELECT DISTINCT count(*) FROM t GROUP BY h",
    "SELECT DISTINCT count(*) FROM t GROUP BY g ORDER BY 1 DESC",
    "SELECT DISTINCT h FROM t GROUP BY g, h ORDER BY 1",
    "SELECT DISTINCT count(*), sum(x) FROM t",
    "SELECT DISTINCT b FROM w GROUP BY c, b",
    # over a join: with an ORDER BY that fixes the order (sqlite3 picks the join order)
    f"SELECT DISTINCT c.city FROM {JOIN} ORDER BY 1",
    f"SELECT DISTINCT c.city, o.total > 20 FROM {JOIN} ORDER BY 1, 2",
    "SELECT DISTINCT o.customer_id FROM customers c, orders o ORDER BY 1",
    f"SELECT DISTINCT c.name FROM {JOIN} ORDER BY c.name DESC LIMIT 2",
    f"SELECT DISTINCT c.city, count(*) FROM {JOIN} GROUP BY c.name ORDER BY 1, 2",
    # DISTINCT inside an aggregate: the value steps once per group
    "SELECT count(DISTINCT x), sum(DISTINCT x), typeof(sum(DISTINCT x)), count(x), sum(x) FROM d",
    "SELECT sum(DISTINCT x), typeof(sum(DISTINCT x)) FROM d2",
    "SELECT count(DISTINCT g), count(DISTINCT h), count(DISTINCT x), sum(DISTINCT h), avg(DISTINCT h) FROM t",
    "SELECT total(DISTINCT x), avg(DISTINCT x), min(DISTINCT x), max(DISTINCT x) FROM d",
    "SELECT h, count(DISTINCT g), sum(DISTINCT x), count(*) FROM t GROUP BY h",
    "SELECT count(DISTINCT v), count(v), sum(DISTINCT n) FROM mix",
    "SELECT n % 3, count(DISTINCT v) FROM mix GROUP BY n % 3",
    f"SELECT count(DISTINCT c.city), count(DISTINCT o.customer_id), sum(DISTINCT o.total) FROM {JOIN}",
    f"SELECT c.city, count(DISTINCT c.id), count(*) FROM {JOIN} GROUP BY c.city ORDER BY 1",
    "SELECT count(DISTINCT x), count(ALL x) FROM blank",
    "SELECT sum(DISTINCT total), sum(total), count(DISTINCT total) FROM orders",
    # bare columns with a DISTINCT min() or max(): a value seen before steps nothing
    "SELECT a, max(DISTINCT b) FROM p",
    "SELECT a, min(DISTINCT b) FROM p",
    "SELECT a, max(DISTINCT b), count(*) FROM p",
    "SELECT a, count(DISTINCT b), max(b) FROM p",
    "SELECT a, max(b), count(DISTINCT b) FROM p",
    "SELECT c, a, max(DISTINCT b) FROM w GROUP BY c",
    "SELECT c, a, min(DISTINCT b), max(b) FROM w GROUP BY c",
]

# exactly sqlite3's text (the outputs above are compared with floats as numbers): what a
# GROUP BY term shows when the group's own row is not its first, and the types of merged groups
EXACT = """SELECT v + 0, typeof(v + 0), max(w) FROM k WHERE w < 3 GROUP BY v + 0;
SELECT v + 0 AS q, typeof(v + 0), max(w) FROM k WHERE w < 3 GROUP BY q;
SELECT abs(v), typeof(abs(v)), max(w), abs(v) FROM k WHERE w < 3 GROUP BY abs(v) ORDER BY 1;
SELECT v * 1, max(w), v FROM k WHERE w < 3 GROUP BY 1;
SELECT DISTINCT v + 0, max(w) FROM k WHERE w < 3 GROUP BY v + 0;
SELECT v, typeof(v), count(*) FROM k GROUP BY v;
SELECT DISTINCT v, typeof(v) FROM mix WHERE n < 15;
SELECT sum(DISTINCT x), typeof(sum(DISTINCT x)) FROM d;
SELECT sum(DISTINCT x), typeof(sum(DISTINCT x)) FROM d2;
"""

# Errors in both engines (errors_alike); the text after "Error: " must be sqlite3's.
ERRORS = [
    ("SELECT count(*) FROM p GROUP BY count(*)", "aggregate functions are not allowed in the GROUP BY clause"),
    ("SELECT b, count(*) FROM p GROUP BY 2", "aggregate functions are not allowed in the GROUP BY clause"),
    ("SELECT count(*) AS c FROM p GROUP BY c", "aggregate functions are not allowed in the GROUP BY clause"),
    ("SELECT b FROM p GROUP BY b + max(b)", "aggregate functions are not allowed in the GROUP BY clause"),
    ("SELECT b, count(*) FROM p GROUP BY 3", "1st GROUP BY term out of range - should be between 1 and 2"),
    ("SELECT b, count(*) FROM p GROUP BY 0", "1st GROUP BY term out of range - should be between 1 and 2"),
    ("SELECT b, count(*) FROM p GROUP BY b, -1", "2nd GROUP BY term out of range - should be between 1 and 2"),
    ("SELECT a FROM p HAVING a > 'a'", "HAVING clause on a non-aggregate query"),
    ("SELECT g FROM t HAVING count(*) > 1", "HAVING clause on a non-aggregate query"),
    ("SELECT g FROM t GROUP BY g HAVING max(count(*)) > 0", "misuse of aggregate function count()"),
    ("SELECT g FROM t GROUP BY g HAVING count(g, h) > 0", "wrong number of arguments to function count()"),
    ("SELECT count(DISTINCT a, b) FROM p", "wrong number of arguments to function count()"),
    ("SELECT count(DISTINCT) FROM p", "DISTINCT aggregates must have exactly one argument"),
    ("SELECT g FROM t GROUP BY nope", "no such column: nope"),
    ("SELECT g FROM t GROUP BY g HAVING nope > 1", "no such column: nope"),
    ("SELECT g, sum(x) FROM hv GROUP BY g HAVING 0", "integer overflow"),
    ("SELECT g, sum(x) FROM hv GROUP BY g HAVING count(*) = 1", "integer overflow"),
    ("SELECT g FROM t WHERE count(*) > 1 GROUP BY g", "misuse of aggregate function count()"),
    ("SELECT DISTINCT nope FROM t", "no such column: nope"),
    ("SELECT DISTINCT FROM t", 'near "FROM": syntax error'),
    ("SELECT g FROM t GROUP BY", 'near ";": syntax error'),
    ("SELECT g FROM t GROUP g", 'near "g": syntax error'),
]

# EXPLAIN QUERY PLAN where sqlite3 must print the same lines: no index, CROSS JOIN with
# automatic indexes off, no DISTINCT whose list is the ORDER BY's (sqlite3 turns that into
# a GROUP BY), no rowid in a DISTINCT list (it makes the rows unique).
PLANS = [
    "SELECT g, count(*), sum(x) FROM t GROUP BY g",
    "SELECT g, count(*) AS n FROM t GROUP BY g ORDER BY count(*) DESC, g LIMIT 2",
    "SELECT customer_id, sum(total) FROM orders GROUP BY customer_id HAVING sum(total) > 20",
    "SELECT DISTINCT g FROM t",
    "SELECT DISTINCT g, h FROM t ORDER BY h",
    "SELECT count(DISTINCT x) FROM t",
    "SELECT count(DISTINCT x), sum(DISTINCT h) FROM t",
    "SELECT h, count(DISTINCT g) FROM t GROUP BY h",
    "SELECT DISTINCT count(*) FROM t GROUP BY h",
    "SELECT DISTINCT count(*) FROM t GROUP BY h ORDER BY 1 DESC",
    "SELECT c.city, count(*) FROM customers c CROSS JOIN orders o ON o.customer_id = c.id GROUP BY c.city",
    "SELECT count(DISTINCT c.city) FROM customers c CROSS JOIN orders o ON o.customer_id = c.id",
    "SELECT DISTINCT c.city FROM customers c CROSS JOIN orders o ON o.customer_id = c.id",
]

EXPLAIN_GROUPS = """Sort by sum(total) DESC
  Filter (count(*) > 1)
    Aggregate count(*), sum(total) by city
      Sort by city DESC
        Filter (o.customer_id = c.id)
          Join
            Scan customers AS c
            Scan orders AS o
"""

EXPLAIN_DISTINCT = """Sort by city
  Distinct city
    Scan customers
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


def many_rows():
    """20000 rows of one column: thousands of distinct numbers, each as an integer, a whole
    real (equal to it) and a half; text; blobs; NULLs; in an order that mixes them."""
    out = ["CREATE TABLE many(v, g);", "BEGIN;"]
    for i in range(1, 20001):
        n = i * 7919 % 3001
        kind = i % 4
        if i % 1000 == 0:
            v = "NULL"
        elif i % 500 == 0:
            v = "x'" + f"b{n}".encode().hex() + "'"      # printable bytes: sqlite3 escapes others
        elif kind == 0:
            v = str(n)
        elif kind == 1:
            v = f"{n}.5"
        elif kind == 2:
            v = f"{n}.0"
        else:
            v = f"'t{i * 31 % 2003}'"
        out.append(f"INSERT INTO many VALUES ({v}, {i % 7});")
    out.append("COMMIT;")
    return "\n".join(out) + "\n"


def long_rows():
    """600 rows of text and blobs of 1000 to 6000 bytes (most of them spill to overflow
    pages), each value twice, 300 distinct, and 300 groups."""
    out = ["CREATE TABLE longs(id INTEGER PRIMARY KEY, v, k);", "BEGIN;"]
    for i in range(600):
        j = i * 7 % 300
        if j % 3 == 0:
            v = "x'" + f"{0x41 + j % 26:02x}" * (1000 + j * 10) + f"{j}".encode().hex() + "'"
        else:
            v = "'" + chr(97 + j % 26) * (1000 + j * 17) + str(j) + "'"
        out.append(f"INSERT INTO longs(v, k) VALUES ({v}, {j % 11});")
    out.append("COMMIT;")
    return "\n".join(out) + "\n"


def errors(t, setup, cases):
    """Each case is an error in both engines, with sqlite3's text."""
    tr = t.track
    for sql, msg in cases:
        r = tr.errors_alike(t, setup, f"{sql};\n")
        t.check(f"Error: {msg}\n" in r.err, f"{sql}: ./db should say {msg!r}, said:\n{r.err}")


def test(t):
    tr = t.track

    a, b = files(t, SHOP + EDGE)
    compare(t, a, b, listing(GROUP_QUERIES))
    compare(t, a, b, listing(DISTINCT_QUERIES))
    # the same answers when every hash in the sets collides
    compare(t, a, b, listing(DISTINCT_QUERIES), env={"DB_SET_COLLIDE": "1"})
    ours, theirs = tr.db(t, a, EXACT).out, tr.sqlite(t, b, EXACT).out
    t.check(ours == theirs, f"./db printed:\n{ours}\nsqlite3 printed:\n{theirs}")
    errors(t, SHOP + EDGE, ERRORS)

    compare(t, a, b, "".join(f"EXPLAIN QUERY PLAN {q};\n" for q in PLANS), theirs_first="PRAGMA automatic_index=OFF;\n")
    out = tr.db(t, a, f"EXPLAIN SELECT city, count(*), sum(total) FROM {JOIN} GROUP BY city HAVING count(*) > 1 "
                      "ORDER BY 3 DESC;\n").out
    t.check(out == EXPLAIN_GROUPS, f"EXPLAIN of GROUP BY and HAVING over a join:\n{out}\nexpected:\n{EXPLAIN_GROUPS}")
    out = tr.db(t, a, "EXPLAIN SELECT DISTINCT city FROM customers ORDER BY city;\n").out
    t.check(out == EXPLAIN_DISTINCT, f"EXPLAIN of DISTINCT:\n{out}\nexpected:\n{EXPLAIN_DISTINCT}")

    # the set: thousands of values (it grows many times), with every hash colliding too
    a2, b2 = files(t, many_rows())
    for env in (None, {"DB_SET_COLLIDE": "1"}):
        compare(t, a2, b2, "SELECT DISTINCT v FROM many;\n", env=env)
        compare(t, a2, b2, "SELECT DISTINCT v, g FROM many LIMIT 5000;\n", env=env)
        compare(t, a2, b2, "SELECT count(DISTINCT v), sum(DISTINCT v), total(DISTINCT v), avg(DISTINCT v), "
                           "min(DISTINCT v), max(DISTINCT v), count(v) FROM many;\n", env=env)
        compare(t, a2, b2, "SELECT g, count(DISTINCT v), sum(DISTINCT v), count(*) FROM many GROUP BY g;\n", env=env)
    out = compare(t, a2, b2, "SELECT v, count(*), typeof(v) FROM many GROUP BY v;\n")
    t.check(len(out.splitlines()) > 5000, f"GROUP BY v over many should give thousands of groups, got {len(out.splitlines())}")

    # long text and blobs, more than 256 groups and distinct rows: pages are evicted between
    # output rows while the set, the group's row and the min and max hold copies
    a3, b3 = files(t, long_rows())
    compare(t, a3, b3, "SELECT DISTINCT v FROM longs;\n")
    compare(t, a3, b3, "SELECT DISTINCT v FROM longs;\n", env={"DB_SET_COLLIDE": "1"})
    compare(t, a3, b3, "SELECT v, count(*), min(id), max(id), length(v) FROM longs GROUP BY v;\n")
    compare(t, a3, b3, "SELECT k, count(DISTINCT v), max(v), min(v) FROM longs GROUP BY k;\n")
    compare(t, a3, b3, "SELECT id, v, max(length(v) * 1000 + id) FROM longs GROUP BY id % 400;\n")
    r = tr.db(t, a3, "SELECT DISTINCT v FROM longs;\n", env={"DB_CACHE_PAGES": "2", "DB_STATS": "1"})
    st = tr.stats(r.err)
    t.check(st["evictions"] > 100 and len(r.lines()) == 300,
            f"the two-page cache should evict pages between DISTINCT's rows: {st}, {len(r.lines())} rows")

    # a join of many pages grouped into 300 groups, with the long text of the max row kept
    big = ("CREATE TABLE p(id INTEGER PRIMARY KEY, k INTEGER, pad TEXT);\n"
           "CREATE TABLE q(id INTEGER PRIMARY KEY, name TEXT, pad TEXT);\nBEGIN;\n" +
           "".join(f"INSERT INTO p VALUES ({i}, {i * 7 % 300 + 1}, '{chr(97 + i * 13 % 26) * (5000 if i % 500 == 0 else 120)}{i}');\n"
                   for i in range(1, 3001)) +
           "".join(f"INSERT INTO q VALUES ({j}, 'name {j}', '{chr(97 + j % 26) * 200}');\n" for j in range(1, 301)) +
           "COMMIT;\n")
    a4, b4 = files(t, big)
    compare(t, a4, b4, "SELECT q.name, count(*), max(p.pad), sum(p.id), min(q.pad) FROM p JOIN q ON q.id = p.k "
                       "GROUP BY q.name;\n")
    compare(t, a4, b4, "SELECT q.name, p.id, max(p.id) FROM p JOIN q ON q.id = p.k GROUP BY q.id;\n")
    compare(t, a4, b4, "SELECT DISTINCT q.name, q.pad FROM p JOIN q ON q.id = p.k;\n", sort=True)
    compare(t, a4, b4, "SELECT p.k % 10, count(DISTINCT q.name), count(*) FROM p JOIN q ON q.id = p.k GROUP BY 1 "
                       "HAVING count(*) > 10 ORDER BY 2 DESC, 1;\n")

    # a quick slice of the fuzzer: random GROUP BY, HAVING and DISTINCT queries, against sqlite3
    tr.fuzz(t, "join,aggregate,groupby,distinct", n=300, seed=1)

    # aggregates over the whole input, and the join and the core, are untouched: 08.04's test
    load_test(os.path.join(os.path.dirname(os.path.abspath(__file__)), "0804_aggregates_one_row_from_many.py")).test(t)
    # and the sqllogictest slice, with SQL that groups or takes DISTINCT no longer skipped
    tr.sqllogictest(t, have=("join", "aggregate", "groupby", "distinct"))
