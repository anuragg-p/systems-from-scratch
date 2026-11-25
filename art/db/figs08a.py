"""Figures for db module 08, More SQL: lessons 08.01-08.03, and the module's cover and icon.

    python3 art/db/figs08a.py           writes tracks/db/lessons/08-more-sql/figures/08.0[1-3]-*.svg,
                                        cover.svg and icon.svg
    python3 art/db/figs08a.py --check   runs the queries below through the engine at each figure's
                                        lesson (./learn run db --at 08.01, 08.02, 08.03), walks the
                                        B-trees of the file shop.py makes, and checks every number

The look every 08 figure shares: customers' values in the neutral tone (class "s f", text "t"),
orders' values in the accent tone ("a af", "ta"), so a joined row reads at a glance; NULL is an
empty dashed cell with the word NULL in muted text.

Every value, slot, operator name and row count here comes from the engine as it stands at 08.01
(`./learn run db --at 08.01 -- shop.db "<sql>"`) on the module's data set, shop.db:

  CREATE TABLE customers(id INTEGER PRIMARY KEY, name TEXT, city TEXT);
  CREATE TABLE orders(id INTEGER PRIMARY KEY, customer_id INTEGER, total INTEGER);
  INSERT INTO customers VALUES (1,'Ada','London'),(2,'Brook','Paris'),(3,'Chen','London'),(4,'Dee','Oslo');
  INSERT INTO orders VALUES (10,1,30),(11,3,15),(12,1,50),(13,2,20),(14,3,5),(15,NULL,40);

08.01-loops (stepped): the order the 24 pairs are visited in and the ON test's value on each are
  PAIRS below, the output of
    SELECT c.id, c.name, o.id, o.customer_id, c.id = o.customer_id FROM customers c CROSS JOIN orders o;
  which runs the same Join over the same two scans with the ON test as a result column. Checked
  against the join itself: a copy of the 08.01 project (./learn files db --at 08.01 DIR) with one
  fprintf added after join_next fills the inner slots and one after filter_next's eval(), running
  SELECT c.name, o.id, o.total FROM customers c JOIN orders o ON c.id = o.customer_id;
  printed the same 24 rows in the same order, the Filter's value_truth() 1 for (1,10) (1,12)
  (2,13) (3,11) (3,14), -1 (NULL) for every pair with order 15, 0 for the rest; the query's
  output is OUTPUT below, in that order (no ORDER BY: the order the loops make).
08.01-row: the same traced copy printed the joined row of the first pair as
  1 'Ada' 'London' 1 10 1 30 10 (slots 0-7), and a second fprintf in resolve_names, after it sets
  e->col, printed o.total -> item 1 base 4 col 6, o.customer_id -> col 5, c.name -> col 1,
  c.rowid -> col 3, o.rowid -> col 7.
08.01-tree: EXPLAIN SELECT name FROM customers WHERE city = 'London';  prints
  Filter (city = 'London') / Scan customers, and
  EXPLAIN SELECT c.name, o.total FROM customers c JOIN orders o ON c.id = o.customer_id;  prints
  Filter (c.id = o.customer_id) / Join / Scan customers AS c / Scan orders AS o.
08.01-levels: a third table, added for this figure only (shop.db with it is shop3.db):
    CREATE TABLE lines(id INTEGER PRIMARY KEY, order_id INTEGER, item TEXT);
    INSERT INTO lines VALUES (1,10,'tea'),(2,12,'jam'),(3,13,'pen'),(4,14,'tea');
  EXPLAIN SELECT c.name, o.id, l.item FROM customers c JOIN orders o ON o.customer_id = c.id
    JOIN lines l ON l.order_id = o.id WHERE c.city = 'London';   prints LEVELS below; the query
  gives Ada|10|tea, Ada|12|jam, Chen|14|tea. The traced copy counted the rows each Filter tested
  and passed: (c.city = 'London') 4 and 2, (o.customer_id = c.id) 12 and 4, (l.order_id = o.id)
  16 and 3; SELECT * FROM customers c, orders o, lines l gives 96 rows.
cover: the five joined pairs are OUTPUT's; "London 4 100" is the London rows of the join,
  SELECT c.city, o.total FROM customers c JOIN orders o ON c.id = o.customer_id WHERE c.city = 'London';
  London|30, London|50, London|15, London|5: 4 rows, 100 in all (what 08.04's count(*) and
  sum(total) give for them). Brook's pair is Paris, so its row is the one with no line to it.

08.02 (the engine at 08.02, `./learn run db --at 08.02 -- shop.db "<sql>"`, the same shop.db):
08.02-nomatch: NOMATCH_SQL prints NOMATCH (the same six rows with ORDER BY c.id, o.id); on Dee's
  row typeof(o.id) is 'null' and o.rowid is NULL (DEE_SQL).
08.02-on-where: ON_SQL prints ON_OUT, WHERE_SQL prints WHERE_OUT. What the Left join hands up to
  WHERE, with the term's value on each row, is WHERE_IN (o.total > 25 as a result column of the
  LEFT JOIN with no WHERE). EXPLAIN puts the term in "Left join on ((o.customer_id = c.id) AND
  (o.total > 25))" for ON_SQL, and in "Filter (o.total > 25)" over "Left join on (o.customer_id =
  c.id)" for WHERE_SQL (ON_TREE, WHERE_TREE). The orders each NULL row stands for (Brook's 13 of
  20, Chen's 11 and 14 of 15 and 5, none for Dee) are ORDERS'. NOTES' runs use o.total > 20: the
  same rows, since no order's total is between 21 and 25.

08.03 (the engine at 08.03):
08.03-ladder: EXPLAIN QUERY PLAN SELECT * <clause>; on shop.db after INDEX_SQL; the line drawn is
  the last one the engine prints (the inner table's), for each clause in LADDER, BOTH and LEFTW.
08.03-lookup: shop.py's file, made by piping shop_sql() (shop.py as NOTES gives it) into
  `./learn run db --at 08.03 -- shop.big.db`: 69 pages. Its pages were dumped by reading the file:
  page 1's sqlite_schema rows give each table's root page, and each B-tree page is walked from its
  header (type 0x05 interior: cells of child page and divider rowid, then the right child; 0x0d
  leaf: cells of rowid and record), which is tree() below; --check walks it again. customers:
  root page 2 with dividers 168 327 486 645 804 963 over leaves 5 6 7 8 9 10 4 (in key order;
  leaf 5 holds rows 1-168). orders: root page 3 over 59 leaves; order 358 (customer_id 3, total
  58, the first order of customer 3) is in leaf 13 (orders 356-700). Customer 3 is 'customer 3',
  'Rome'. A copy of the 08.03 project with an fprintf of every page number in pager.c page_get
  showed what is asked for: with WHERE o.id = 358, the rowid lookup asks for page 2 once and leaf
  5 six times (7 requests); the same order with ON c.id + 0 = o.customer_id (SCAN c) asks for
  page 2 and leaves 5, 6, 7, 8, 9, 10, 4 in that order, page 2 again between leaves, 3,028 in all.
  --check gets 7 and 3,028 from DB_STATS: that query's page requests less those of
  SELECT o.id FROM orders o WHERE o.id = 358 alone.
08.03-cost: the lesson's "Run it", in its order, on one shop.big.db with DB_STATS=1: COST[0] with no
  index; then INDEX_SQL (the file grows to 134 pages); then COST[1] and COST[2], the index still in
  the schema. Page requests are cache hits + misses; with the default 500-page cache each page is
  read from the file once whatever the plan: 69, 134 and 69 pages read (COST's pages). The third
  is 200,727, not the 200,724 it is on a file with no index: with the index in the schema every
  statement starts with 11 requests, not 8 (NOTES, 08.03, "For the lesson"). The nested loop is
  1000 x 60,236 (one scan of orders: three requests a row, as cursor_next, settle and cursor_load
  each ask for the leaf, plus leaf changes) + 3,028 (the scan of customers) + 8 = 60,239,036. The
  bars are the page requests; the times are the lesson's (0.861, 0.012 and 0.010 s; the median of
  7 runs here was 856, 12.0 and 10.7 ms), printed as "about N ms": they vary from run to run, so
  --check prints its own and does not compare them.
"""
import os
import re
import statistics
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import figlib  # noqa: E402
from figlib import tw  # noqa: E402
import steps  # noqa: E402

REPO = os.path.dirname(os.path.dirname(HERE))
figlib.LESSONS = os.path.join(REPO, "tracks", "db", "lessons")
MOD = "08-more-sql"


class Fig(figlib.Fig):
    """figlib.Fig whose text() takes anchor None as "start" (figlib would write text-anchor="None")."""

    def text(self, x, y, s, cls="t", size=12, anchor="start", weight=None, mono=False):
        super().text(x, y, s, cls, size, anchor or "start", weight, mono)

# ------------------------------------------------------------------ the data, from the runs above

CUSTOMERS = [(1, "Ada", "London"), (2, "Brook", "Paris"), (3, "Chen", "London"), (4, "Dee", "Oslo")]
ORDERS = [(10, 1, 30), (11, 3, 15), (12, 1, 50), (13, 2, 20), (14, 3, 5), (15, None, 40)]

# (c.id, o.id, the ON test: 1 true, 0 false, None NULL), in the order the nested loop visits them
PAIRS = [
    (1, 10, 1), (1, 11, 0), (1, 12, 1), (1, 13, 0), (1, 14, 0), (1, 15, None),
    (2, 10, 0), (2, 11, 0), (2, 12, 0), (2, 13, 1), (2, 14, 0), (2, 15, None),
    (3, 10, 0), (3, 11, 1), (3, 12, 0), (3, 13, 0), (3, 14, 1), (3, 15, None),
    (4, 10, 0), (4, 11, 0), (4, 12, 0), (4, 13, 0), (4, 14, 0), (4, 15, None),
]
JOIN_SQL = "SELECT c.name, o.id, o.total FROM customers c JOIN orders o ON c.id = o.customer_id;"
OUTPUT = [("Ada", 10, 30), ("Ada", 12, 50), ("Brook", 13, 20), ("Chen", 11, 15), ("Chen", 14, 5)]

# the first joined row, slots 0-7: customers c from base 0, orders o from base 4
ROW = [("id", 1, "c"), ("name", "Ada", "c"), ("city", "London", "c"), ("rowid", 1, "c"),
       ("id", 10, "o"), ("customer_id", 1, "o"), ("total", 30, "o"), ("rowid", 10, "o")]

TREE1_SQL = "EXPLAIN SELECT name FROM customers WHERE city = 'London';"
TREE1 = ["Filter (city = 'London')", "  Scan customers"]
TREE2_SQL = "EXPLAIN SELECT c.name, o.total FROM customers c JOIN orders o ON c.id = o.customer_id;"
TREE2 = ["Filter (c.id = o.customer_id)", "  Join", "    Scan customers AS c", "    Scan orders AS o"]

LINES_SQL = ("CREATE TABLE lines(id INTEGER PRIMARY KEY, order_id INTEGER, item TEXT); "
             "INSERT INTO lines VALUES (1,10,'tea'),(2,12,'jam'),(3,13,'pen'),(4,14,'tea');")
LEVELS_Q = ("SELECT c.name, o.id, l.item FROM customers c JOIN orders o ON o.customer_id = c.id "
            "JOIN lines l ON l.order_id = o.id WHERE c.city = 'London';")
LEVELS = ["Filter (l.order_id = o.id)", "  Join", "    Filter (o.customer_id = c.id)", "      Join",
          "        Filter (c.city = 'London')", "          Scan customers AS c", "        Scan orders AS o",
          "    Scan lines AS l"]
LEVELS_OUT = [("Ada", 10, "tea"), ("Ada", 12, "jam"), ("Chen", 14, "tea")]
# rows each Filter tested and passed, level 0, 1, 2 (from the traced copy; --check rederives them)
TESTED, PASSED = [4, 12, 16], [2, 4, 3]
CROSS3 = 96

LONDON = ("London", 4, 100)

# 08.02, the engine at 08.02 on shop.db
NOMATCH_SQL = "SELECT * FROM customers c LEFT JOIN orders o ON o.customer_id = c.id;"
NOMATCH = [(1, "Ada", "London", 10, 1, 30), (1, "Ada", "London", 12, 1, 50), (2, "Brook", "Paris", 13, 2, 20),
           (3, "Chen", "London", 11, 3, 15), (3, "Chen", "London", 14, 3, 5), (4, "Dee", "Oslo", None, None, None)]
DEE_SQL = "SELECT typeof(o.id), o.rowid FROM customers c LEFT JOIN orders o ON o.customer_id = c.id WHERE c.id = 4;"
DEE = ("null", None)
ON_SQL = "SELECT c.name, o.id, o.total FROM customers c LEFT JOIN orders o ON o.customer_id = c.id AND o.total > 25;"
ON_OUT = [("Ada", 10, 30), ("Ada", 12, 50), ("Brook", None, None), ("Chen", None, None), ("Dee", None, None)]
WHERE_SQL = "SELECT c.name, o.id, o.total FROM customers c LEFT JOIN orders o ON o.customer_id = c.id WHERE o.total > 25;"
WHERE_OUT = [("Ada", 10, 30), ("Ada", 12, 50)]
# the rows the Left join hands up to WHERE, and o.total > 25 on each (1 true, 0 false, None NULL)
WHERE_IN_SQL = "SELECT c.name, o.id, o.total, o.total > 25 FROM customers c LEFT JOIN orders o ON o.customer_id = c.id;"
WHERE_IN = [("Ada", 10, 30, 1), ("Ada", 12, 50, 1), ("Brook", 13, 20, 0), ("Chen", 11, 15, 0), ("Chen", 14, 5, 0),
            ("Dee", None, None, None)]
ON_TREE = ["Left join on ((o.customer_id = c.id) AND (o.total > 25))", "  Scan customers AS c", "  Scan orders AS o"]
WHERE_TREE = ["Filter (o.total > 25)", "  Left join on (o.customer_id = c.id)", "    Scan customers AS c",
              "    Scan orders AS o"]

# 08.03, the engine at 08.03: on shop.db with the index, the inner table's EXPLAIN QUERY PLAN line
INDEX_SQL = "CREATE INDEX orders_customer ON orders(customer_id);"
LADDER = [
    ("1", "its rowid equals a value from the outer row", "FROM orders o JOIN customers c ON c.id = o.customer_id",
     "SEARCH c USING INTEGER PRIMARY KEY (rowid=?)"),
    ("2", "an index's first column equals such a value", "FROM customers c JOIN orders o ON o.customer_id = c.id",
     "SEARCH o USING INDEX orders_customer (customer_id=?)"),
    ("3", "anything else", "FROM customers c JOIN orders o ON o.customer_id + 0 = c.id", "SCAN o"),
]
BOTH = ("FROM customers c JOIN orders o ON o.id = c.id AND o.customer_id = c.id",
        "SEARCH o USING INTEGER PRIMARY KEY (rowid=?)")
LEFTW = ("FROM customers c LEFT JOIN orders o ON 1 WHERE o.customer_id = c.id", "SCAN o LEFT-JOIN")

# shop.py's file (shop.big.db): its pages, dumped (tree()), and what one order's lookup asks for
SHOP_ROWS = (1000, 20000)
SHOP_PAGES, SHOP_PAGES_IX = 69, 134
LOOK_SQL = "SELECT o.id, c.name FROM orders o JOIN customers c ON c.id = o.customer_id WHERE o.id = 358;"
SWEEP_SQL = "SELECT o.id, c.name FROM orders o JOIN customers c ON c.id + 0 = o.customer_id WHERE o.id = 358;"
ALONE_SQL = "SELECT o.id FROM orders o WHERE o.id = 358;"
LOOK_ORDER = (358, 3, 58)                     # o.id, o.customer_id, o.total: customer 3's first order
LOOK_ORDER_LEAF = 13
CUST_ROOT = 2
CUST_DIVIDERS = [168, 327, 486, 645, 804, 963]
CUST_LEAVES = [5, 6, 7, 8, 9, 10, 4]          # in key order
CUST_LEAF_RANGE = (1, 168)                    # leaf 5's rowids, where customer 3 is
LOOK_ROW = (3, "customer 3", "Rome")
LOOK_REQ, SWEEP_REQ = 7, 3028                 # page requests for order 358's customer, each way

# the same join three ways on shop.py's file, as the lesson runs them, in its order (INDEX_SQL
# between the first and the second): (tables, ON, how the inner side is read, page requests,
# pages read, ms)
COST_SQL = "SELECT c.name, o.id, o.total FROM {} ON {};"
COST = [
    ("customers c JOIN orders o", "o.customer_id = c.id", "scan orders, per customer", 60239036, 69, 860),
    ("customers c JOIN orders o", "o.customer_id = c.id", "index lookup, per customer", 147241, 134, 12),
    ("orders o JOIN customers c", "c.id = o.customer_id", "rowid lookup, per order", 200727, 69, 10),
]
ORDERS_SCAN = 60236                           # page requests of one scan of orders, less the statement's 8

# ------------------------------------------------------------------ the shared look

TONE = {"c": ("s f", "t"), "o": ("a af", "ta"), "l": ("s fs", "t")}


def val(v):
    return "NULL" if v is None else str(v)


def cells(f, x, y, items, h=22, size=11):
    """items: (width, value, tone), tone "c" (customers), "o" (orders) or "l" (lines). Cells left
    to right with no gap; a None value is a NULL: an empty dashed cell, the word muted. Returns
    the x after the last cell."""
    for w, v, tone in items:
        if v is None:
            f.rect(x, y, w, h, "m f", 0, dash=True)
            f.text(x + w / 2, y + h / 2 + size * 0.36, "NULL", "tm", size - 1.5, "middle", None, True)
        else:
            cls, tcls = TONE[tone]
            f.rect(x, y, w, h, cls, 0)
            f.text(x + w / 2, y + h / 2 + size * 0.36, str(v), tcls, size, "middle", None, True)
        x += w
    return x


def ring(f, x, y, w, h, cls="s"):
    """A marker drawn round a row: a heavier outline just outside it."""
    f.add(f'<rect class="{cls}" x="{x - 3}" y="{y - 3}" width="{w + 6}" height="{h + 6}" rx="4" stroke-width="2.25"/>')


# ------------------------------------------------------------------ 08.01

def loops0801():
    f = Fig("f0801a", "The nested loop: every customer against every order, the ON test on each pair", 300)
    RH = 24
    Y0 = 78
    CX, CW = 70, [26, 52, 58]
    OX, OW = 250, [30, 78, 44]
    VX = OX + sum(OW) + 8                     # the verdict beside each order
    PX, PW = 478, [50, 38, 50]
    f.text(24, 22, JOIN_SQL, "tm", 10.5, None, None, True)
    f.text(CX, 52, "customers c (outer)", "t", 11.5, None, 600)
    f.text(OX, 52, "orders o (inner)", "ta", 11.5, None, 600)
    f.text(PX, 52, "output", "t", 11.5, None, 600)

    def heads(x, widths, names, tcls):
        for w, n in zip(widths, names):
            f.text(x + w / 2, 70, n, tcls, 10, "middle", None, True)
            x += w
    heads(CX, CW, ["id", "name", "city"], "tm")
    heads(OX, OW, ["id", "customer_id", "total"], "tm")
    heads(PX, PW, ["c.name", "o.id", "o.total"], "tm")
    for i, (cid, name, city) in enumerate(CUSTOMERS):
        cells(f, CX, Y0 + i * RH, [(CW[0], cid, "c"), (CW[1], name, "c"), (CW[2], city, "c")], h=RH)
    for j, (oid, cust, total) in enumerate(ORDERS):
        cells(f, OX, Y0 + j * RH, [(OW[0], oid, "o"), (OW[1], cust, "o"), (OW[2], total, "o")], h=RH)
    # the ON test's box, under the tables
    TY = 242
    f.rect(24, TY, 592, 38, "s fs", 6)
    f.text(36, TY + 24, "ON", "tm", 11, None, 600)
    f.text(60, TY + 24, "c.id = o.customer_id", "t", 11.5, None, None, True)

    cw, ow = sum(CW), sum(OW)
    oidx = {o[0]: j for j, o in enumerate(ORDERS)}
    word = {1: "true", 0: "false", None: "NULL"}

    def mid(i):
        return Y0 + i * RH + RH / 2

    def verdict(j, v, now=False):
        cls = "t" if v == 1 else "tm"
        f.text(VX, mid(j) + 4, word[v], cls, 10.5, None, 700 if (v == 1 or now) else None, v is None)

    def link(i, j, v):
        if v == 1:
            f.path(f"M{CX + cw + 4} {mid(i)} C {CX + cw + 30} {mid(i)}, {OX - 30} {mid(j)}, {OX - 5} {mid(j)}",
                   "s", arrow=True)
        else:
            f.path(f"M{CX + cw + 4} {mid(i)} C {CX + cw + 30} {mid(i)}, {OX - 30} {mid(j)}, {OX - 5} {mid(j)}",
                   "m", dash=True)

    def output(n, new=()):
        """The first n rows of output; new (consecutive) are the ones this step added, ringed."""
        for k in range(n):
            name, oid, total = OUTPUT[k]
            cells(f, PX, Y0 + k * RH, [(PW[0], name, "c"), (PW[1], oid, "o"), (PW[2], total, "o")], h=RH)
        new = list(new)
        if new:
            ring(f, PX, Y0 + new[0] * RH, sum(PW), len(new) * RH)

    def test_line(cid, custs, v_text, v_cls):
        """The values the ON test compared, in the box: c.id's in the neutral tone, each
        customer_id in the accent tone (NULL muted)."""
        x = 230
        f.text(x, TY + 24, str(cid), "t", 12, None, 700, True)
        x += tw(str(cid), 12, True) + 8
        f.text(x, TY + 24, "=", "tm", 12, None, None, True)
        x += 16
        for k, c in enumerate(custs):
            s = val(c) + ("," if k < len(custs) - 1 else "")
            f.text(x, TY + 24, s, "tm" if c is None else "ta", 12, None, 700, True)
            x += tw(s, 12, True) + 6
        f.text(x + 8, TY + 24, v_text, v_cls, 11.5, None, 600)

    nout = 0
    for i, (cid, name, _) in enumerate(CUSTOMERS):
        mine = [p for p in PAIRS if p[0] == cid]
        if i == 0:
            # Ada: one frame per order
            for n, (_, oid, v) in enumerate(mine):
                j = oidx[oid]
                cust = ORDERS[j][1]
                new = []
                if v == 1:
                    new = [nout]
                    nout += 1
                if v == 1:
                    tail = "true, so the pair is a row of output"
                elif v == 0:
                    tail = "false; the pair is dropped"
                else:
                    tail = "NULL, which is not true either; dropped"
                cap = f"{name} (c.id {cid}) against order {oid} (customer_id {val(cust)}): {cid} = {val(cust)} is {tail}."
                if n == len(mine) - 1:
                    cap += " The inner scan is done: Ada matched 2 of the 6 orders."
                with steps.step(f, cap):
                    ring(f, CX, Y0 + i * RH, cw, RH)
                    f.text(CX - 10, mid(i) + 4, "outer", "t", 10.5, "end", 600)
                    for m in range(n):
                        _, o2, v2 = mine[m]
                        verdict(oidx[o2], v2)
                    verdict(j, v, now=True)
                    ring(f, OX, Y0 + j * RH, ow, RH, "a")
                    link(i, j, v)
                    if v == 1:
                        f.path(f"M{VX + 30} {mid(j)} C {VX + 40} {mid(j)}, {PX - 22} {mid(new[0])}, {PX - 6} {mid(new[0])}",
                               "s", arrow=True)
                    output(nout, new)
                    test_line(cid, [cust], {1: "true", 0: "false", None: "NULL: not true"}[v], "t" if v == 1 else "tm")
        else:
            # every later customer: one frame with all six of its tests
            hits = [oid for _, oid, v in mine if v == 1]
            new = list(range(nout, nout + len(hits)))
            nout += len(hits)
            if hits:
                which = " and ".join(str(o) for o in hits)
                plural = "s" if len(hits) > 1 else ""
                cap = (f"{name} (c.id {cid}): the inner scan starts again from order 10; {cid} = customer_id "
                       f"is true for order{plural} {which}, so {len(hits)} row{plural} of output.")
            else:
                cap = (f"{name} (c.id {cid}): no order has customer_id {cid}, so all six tests fail and {name} "
                       f"adds nothing. The outer scan is done.")
            with steps.step(f, cap):
                ring(f, CX, Y0 + i * RH, cw, RH)
                f.text(CX - 10, mid(i) + 4, "outer", "t", 10.5, "end", 600)
                for _, oid, v in mine:
                    link(i, oidx[oid], v)
                    verdict(oidx[oid], v)
                for k, oid in enumerate(hits):
                    j = oidx[oid]
                    f.path(f"M{VX + 30} {mid(j)} C {VX + 40} {mid(j)}, {PX - 22} {mid(new[k])}, {PX - 6} {mid(new[k])}",
                           "s", arrow=True)
                output(nout, new)
                v_text = (f"true for order{'s' if len(hits) > 1 else ''} {' and '.join(str(o) for o in hits)}"
                          if hits else "never true")
                test_line(cid, [o[1] for o in ORDERS], v_text, "t" if hits else "tm")
    # the result
    tested, passed = len(PAIRS), sum(1 for p in PAIRS if p[2] == 1)
    with steps.step(f, f"The output: {passed} rows, from {len(CUSTOMERS)} x {len(ORDERS)} = {tested} pairs "
                       "tested. Order 15 (customer_id NULL) and Dee never match, so neither is in it."):
        output(nout, range(nout))
        f.text(230, TY + 24, f"{tested} pairs tested ({len(CUSTOMERS)} x {len(ORDERS)}), {passed} true", "t", 11.5,
               None, 600)
    return f


def row0801():
    f = Fig("f0801b", "The joined row: both tables' values side by side, each name bound to one slot", 264)
    f.text(24, 22, "the row Join hands up for Ada and order 10: customers c's slots, then orders o's", "tm", 11)
    X0, W, Y = 24, 74, 96
    xs = [X0 + k * W for k in range(len(ROW))]
    # o.total above, with its arrow to its slot
    k6 = 6
    cx = xs[k6] + W / 2
    f.rect(cx - 38, 40, 76, 24, "a af", 4)
    f.text(cx, 56.5, "o.total", "ta", 12, "middle", 600, True)
    f.line(cx, 66, cx, Y - 4, "a", arrow=True)
    f.text(cx - 48, 50, "base 4 + column 2 = slot 6", "t", 11.5, "end", 600)
    f.text(cx - 48, 66, "bound once, when the names are resolved", "tm", 10.5, "end")
    for k, (name, v, tone) in enumerate(ROW):
        cls, tcls = TONE[tone]
        f.rect(xs[k], Y, W, 46, cls, 0)
        f.text(xs[k] + W / 2, Y + 15, name, "tm", 10, "middle", None, True)
        f.text(xs[k] + W / 2, Y + 35, str(v), tcls, 13, "middle", 600, True)
        f.text(xs[k] + W / 2, Y + 62, f"slot {k}", "tm", 10.5, "middle", None, True)
    f.brace_h(xs[0] + 2, xs[4] - 2, Y + 74, "s")
    f.brace_h(xs[4] + 2, xs[7] + W - 2, Y + 74, "a")
    f.text((xs[0] + xs[4]) / 2, Y + 92, "customers c: base 0", "t", 11.5, "middle", 600)
    f.text((xs[4] + xs[7] + W) / 2, Y + 92, "orders o: base 4", "ta", 11.5, "middle", 600)
    f.text((xs[0] + xs[4]) / 2, Y + 107, "3 columns, then its rowid", "tm", 10.5, "middle")
    f.text((xs[4] + xs[7] + W) / 2, Y + 107, "3 columns, then its rowid", "tm", 10.5, "middle")
    f.line(24, 214, 616, 214, "m")
    f.text(24, 234, "c.name is slot 1, o.customer_id slot 5: eval() reads row->cols[slot], as it does for one table.",
           "t", 11)
    f.text(24, 252, "A scan's row carries its rowid beside its values, not in one; the join copies it into slot 3 or 7.",
           "tm", 10.5)
    return f


def tree0801():
    f = Fig("f0801c", "One table's plan and a join's: what each edge carries is one row", 312)
    BH = 26

    def op(cx, y, w, label, cls="s f", tcls="t"):
        f.rect(cx - w / 2, y, w, BH, cls, 6)
        f.text(cx, y + 17, label, tcls, 10.5, "middle", None, True)

    def strip(x, y, items, rowid, anchor="start"):
        """A row as a short strip of cells, its rowid noted under it (a scan's row carries it
        outside its values). anchor "end" puts the strip's right edge at x."""
        w = sum(i[0] for i in items)
        x0 = x - w if anchor == "end" else x
        cells(f, x0, y, items, h=18, size=10)
        if rowid is not None:
            f.text(x0 + w if anchor == "end" else x0, y + 31, f"+ rowid {rowid}", "tm", 10,
                   "end" if anchor == "end" else "start", None, True)

    # one table, as in 04.02
    f.text(24, 22, "one table, as in 04.02", "t", 11.5, None, 600)
    L = 112
    op(L, 40, 176, TREE1[0].strip())
    op(L, 234, 120, TREE1[1].strip(), "s f", "t")
    f.line(L, 232, L, 68, "s", arrow=True)
    cust = [(18, 1, "c"), (30, "Ada", "c"), (46, "London", "c")]
    strip(L + 10, 140, cust, 1)
    f.text(24, 290, "SELECT name FROM customers", "tm", 10, None, None, True)
    f.text(24, 304, "WHERE city = 'London';", "tm", 10, None, None, True)

    # two tables, joined
    f.text(252, 22, "two tables, joined (08.01)", "t", 11.5, None, 600)
    R = 434
    op(R, 40, 212, TREE2[0].strip())
    op(R, 146, 64, TREE2[1].strip())
    lc, rc = 330, 538
    op(lc, 234, 148, TREE2[2].strip(), "s f", "t")
    op(rc, 234, 130, TREE2[3].strip(), "a af", "ta")
    f.line(R, 144, R, 68, "s", arrow=True)
    joined = [(16, 1, "c"), (28, "Ada", "c"), (44, "London", "c"), (16, 1, "c"),
              (20, 10, "o"), (16, 1, "o"), (20, 30, "o"), (20, 10, "o")]
    strip(R + 10, 97, joined, None)
    f.text(R + 10 + sum(i[0] for i in joined) / 2, 92, "8 values", "tm", 10, "middle")
    f.line(lc + 22, 232, R - 14, 174, "s", arrow=True)
    f.line(rc - 22, 232, R + 14, 174, "a", arrow=True)
    strip(lc + 6, 188, cust, 1, anchor="end")
    orde = [(20, 10, "o"), (16, 1, "o"), (20, 30, "o")]
    strip(rc - 6, 188, orde, 10)
    f.text(252, 290, "SELECT c.name, o.total FROM customers c JOIN orders o", "tm", 10, None, None, True)
    f.text(252, 304, "ON c.id = o.customer_id;", "tm", 10, None, None, True)
    return f


def levels0801():
    f = Fig("f0801d", "Three tables: each condition is checked as soon as the last table it names is in the row", 540)
    f.text(24, 20, LEVELS_Q[:LEVELS_Q.index(" JOIN lines")], "tm", 10, None, None, True)
    f.text(24, 35, "  " + LEVELS_Q[LEVELS_Q.index("JOIN lines"):], "tm", 10, None, None, True)
    f.text(24, 56, "lines is a third table, made for this figure:", "tm", 10.5)
    f.text(256, 56, "lines(id INTEGER PRIMARY KEY, order_id INTEGER, item TEXT)", "tm", 10, None, None, True)
    f.text(256, 71, "(1, 10, 'tea') (2, 12, 'jam') (3, 13, 'pen') (4, 14, 'tea')", "tm", 10, None, None, True)

    BH = 28
    SX = 270                                  # the spine: filters, joins, the first scan
    yF2, yJ2, yF1, yJ1, yF0, yS = 112, 172, 248, 308, 384, 444
    # where one level ends and the next begins: 12 px over the filter, under every label of the
    # level above (its row count, its scan's note), and broken where the spine's arrow crosses
    for y in (yF1 - 12, yF0 - 12):
        f.line(24, y, SX - 14, y, "m", dash=True)
        f.line(SX + 60, y, 616, y, "m", dash=True)

    def op(cx, y, w, label, cls="s f", tcls="t", weight=None):
        f.rect(cx - w / 2, y, w, BH, cls, 6)
        f.text(cx, y + 18.5, label, tcls, 11, "middle", weight, True)

    filt = [l.strip() for l in LEVELS if l.strip().startswith("Filter")]   # level 2, 1, 0
    op(SX, yF2, 220, filt[0], weight=600)
    op(SX, yJ2, 72, "Join")
    op(SX, yF1, 220, filt[1], weight=600)
    op(SX, yJ1, 72, "Join")
    op(SX, yF0, 220, filt[2], weight=600)
    op(SX, yS, 164, "Scan customers AS c")
    RX = 520
    op(RX, yJ2, 148, "Scan lines AS l", "s fs", "t")
    op(RX, yJ1, 148, "Scan orders AS o", "a af", "ta")

    # rows flowing up the spine, with how many went along each edge
    edges = [(yS, yF0 + BH, f"{len(CUSTOMERS)} rows"), (yF0, yJ1 + BH, f"{PASSED[0]} rows"),
             (yJ1, yF1 + BH, f"{TESTED[1]} rows"), (yF1, yJ2 + BH, f"{PASSED[1]} rows"),
             (yJ2, yF2 + BH, f"{TESTED[2]} rows"), (yF2, yF2 - 26, f"{PASSED[2]} rows out")]
    for y1, y2, label in edges:
        f.line(SX, y1 - 2, SX, y2 + 3, "s", arrow=True)
        ly = min((y1 + y2) / 2 + 4, y2 + 20)                    # above a level's line
        f.text(SX + 8, ly, label, "t" if "out" in label else "tm", 10.5, None, 600 if "out" in label else None)
    for y, n, per, outer in ((yJ1, TESTED[1], len(ORDERS), PASSED[0]), (yJ2, TESTED[2], 4, PASSED[1])):
        f.line(RX - 76, y + BH / 2, SX + 40, y + BH / 2, "a" if y == yJ1 else "s", arrow=True)
        f.text((RX - 76 + SX + 40) / 2, y + BH / 2 - 6, f"{n} rows", "tm", 10.5, "middle")
        f.text(RX, y + BH + 15, f"{per} rows for each of {outer} outer rows", "tm", 10, "middle")

    # the levels, at the left; what each filter's term names, at its right
    # (the table letters in mono, where l and I differ)
    labels = [(yF2, "level 2", "row: c, o, l", "names l, o: waits for l"),
              (yF1, "level 1", "row: c, o", "names o, c: waits for o"),
              (yF0, "level 0", "row: c", "names only c")]
    for y, lv, what, names in labels:
        f.text(24, y + 13, lv, "t", 12, None, 700)
        f.text(24, y + 28, what, "tm", 10, None, None, True)
        f.text(SX + 118, y + 18.5, names, "tm", 10.5, None, None, True)

    f.line(24, 494, 616, 494, "m")
    f.text(24, 513, f"Each condition meets the fewest rows it can: the filters test {TESTED[0]}, {TESTED[1]} and "
           f"{TESTED[2]} rows.", "t", 11)
    f.text(24, 530, f"Checked only at the top, all three would test every one of {len(CUSTOMERS)} x {len(ORDERS)} x 4 = "
           f"{CROSS3} rows.", "tm", 10.5)
    return f


# ------------------------------------------------------------------ 08.02

def brace_v(f, x, y1, y2, cls="s"):
    """A flat bracket beside a span of rows, open to the left: x is its spine."""
    f.path(f"M{x - 6} {y1} L{x} {y1} L{x} {y2} L{x - 6} {y2}", cls)


def spans(f, x, y, parts, size=10):
    """One line of monospaced text in pieces: parts are (text, class, weight). Returns the x after it."""
    for s, cls, weight in parts:
        f.text(x, y, s, cls, size, None, weight, True)
        x += tw(s, size, True)
    return x


def nomatch0802():
    f = Fig("f0802a", "customers LEFT JOIN orders: the five matched pairs, and one row for Dee with NULLs", 304)
    f.text(24, 22, NOMATCH_SQL, "tm", 10.5, None, None, True)
    W = [30, 56, 64, 36, 92, 50]
    X0, Y0, RH = 40, 76, 26
    xs = [X0 + sum(W[:k]) for k in range(len(W))]
    f.text(X0 + sum(W[:3]) / 2, 46, "customers c", "t", 11.5, "middle", 600)
    f.text(xs[3] + sum(W[3:]) / 2, 46, "orders o", "ta", 11.5, "middle", 600)
    for k, h in enumerate(["id", "name", "city", "id", "customer_id", "total"]):
        f.text(xs[k] + W[k] / 2, 66, h, "tm", 10, "middle", None, True)
    for i, row in enumerate(NOMATCH):
        cells(f, X0, Y0 + i * RH, [(W[k], row[k], "c" if k < 3 else "o") for k in range(6)], h=RH)
    # beside the rows: which are pairs, which is the row with no match
    BX = X0 + sum(W) + 18
    nm = sum(1 for r in NOMATCH if r[3] is not None)
    brace_v(f, BX, Y0 + 3, Y0 + nm * RH - 3)
    ym = Y0 + nm * RH / 2
    f.text(BX + 12, ym - 3, f"{nm} pairs that passed ON", "t", 11.5, None, 600)
    f.text(BX + 12, ym + 13, "the rows of 08.01's inner join", "tm", 10.5)
    dee = NOMATCH[-1]
    brace_v(f, BX, Y0 + nm * RH + 3, Y0 + (nm + 1) * RH - 3)
    yd = Y0 + nm * RH + RH / 2
    f.text(BX + 12, yd + 4, f"{dee[1]}: no order passed ON", "t", 11.5, None, 600)
    # under Dee's NULL cells: who made them
    yb = Y0 + len(NOMATCH) * RH + 8
    f.brace_h(xs[3] + 2, xs[5] + W[5] - 2, yb, "s")
    f.text(xs[3] - 6, yb + 18, "made by the join, not read from orders", "t", 11.5, None, 600)
    f.line(24, 272, 616, 272, "m")
    f.text(24, 292, f"On that row every slot of orders is NULL, its rowid too: typeof(o.id) is '{DEE[0]}', "
           "and the row goes up once.", "tm", 10.5)
    return f


def onwhere0802():
    f = Fig("f0802b", "The same LEFT JOIN with o.total > 25 in ON, then in WHERE: what comes out", 372)
    TERM = "o.total > 25"
    RH = 22
    PW = [56, 40, 52]
    L, R = 24, 336
    f.line(320, 10, 320, 362, "m")
    # the two statements, the term in the accent
    for x, where in ((L, "ON"), (R, "WHERE")):
        e = spans(f, x, 22, [(TERM, "ta", 700)], 12)
        f.text(e + 6, 22, f"in {where}", "t", 12, None, 700)
        spans(f, x, 44, [("SELECT c.name, o.id, o.total", "tm", None)])
        spans(f, x, 58, [("FROM customers c LEFT JOIN orders o", "tm", None)])
    spans(f, L, 72, [("ON o.customer_id = c.id AND ", "tm", None), (TERM, "ta", 700), (";", "tm", None)])
    spans(f, R, 72, [("ON o.customer_id = c.id", "tm", None)])
    spans(f, R, 86, [("WHERE ", "tm", None), (TERM, "ta", 700), (";", "tm", None)])
    f.text(L, 112, "checked inside the Left join, on each pair:", "t", 11)
    f.text(L, 127, "it decides what counts as a match", "tm", 10.5)
    f.text(R, 112, "checked in a Filter above the Left join:", "t", 11)
    f.text(R, 127, "it decides which rows survive", "tm", 10.5)

    def heads(x, y, note):
        for w, h in zip(PW, ["c.name", "o.id", "o.total"]):
            f.text(x + w / 2, y, h, "tm", 10, "middle", None, True)
            x += w
        f.text(x + 10, y, note, "ta", 10, None, None, True)

    YT = 156
    NX = sum(PW) + 10                         # the notes beside the rows
    heads(L, YT - 6, TERM + "?")
    heads(R, YT - 6, TERM)
    # ON: every customer comes out; a NULL row where none of their orders passed
    cid = {c[1]: c[0] for c in CUSTOMERS}
    for i, (name, oid, total) in enumerate(ON_OUT):
        y = YT + i * RH
        cells(f, L, y, [(PW[0], name, "c"), (PW[1], oid, "o"), (PW[2], total, "o")], h=RH)
        if oid is not None:
            note, cls = f"{total}: match", "t"
        else:
            mine = [o[2] for o in ORDERS if o[1] == cid[name]]
            note, cls = (", ".join(map(str, mine)) + ": no match", "tm") if mine else ("no orders", "tm")
        f.text(L + NX, y + RH / 2 + 3.5, note, cls, 10, None, None, True)
    # WHERE: the rows that pass, then (muted) the rest of what the Left join handed up
    word = {1: "true", 0: "false", None: "NULL"}
    for i, (name, oid, total) in enumerate(WHERE_OUT):
        y = YT + i * RH
        cells(f, R, y, [(PW[0], name, "c"), (PW[1], oid, "o"), (PW[2], total, "o")], h=RH)
        f.text(R + NX, y + RH / 2 + 3.5, word[1], "t", 10, None, None, True)
    dropped = [r for r in WHERE_IN if r[3] != 1]
    yd = YT + len(WHERE_OUT) * RH + 30
    f.text(R, yd - 8, f"the Left join's other {len(dropped)} rows, dropped:", "tm", 10.5)
    for i, (name, oid, total, v) in enumerate(dropped):
        y = yd + i * RH
        x = R
        for w, val_ in zip(PW, (name, oid, total)):
            if val_ is None:
                f.rect(x, y, w, RH, "m f", 0, dash=True)
                f.text(x + w / 2, y + RH / 2 + 3.5, "NULL", "tm", 9.5, "middle", None, True)
            else:
                f.rect(x, y, w, RH, "m fs", 0)
                f.text(x + w / 2, y + RH / 2 + 4, str(val_), "tm", 11, "middle", None, True)
            x += w
        f.text(R + NX, y + RH / 2 + 3.5, word[v], "tm", 10, None, None, True)
    yb = 342
    f.text(L, yb, f"{len(ON_OUT)} rows: every customer", "t", 11.5, None, 600)
    f.text(L, yb + 16, "NULLs where no order passed ON", "tm", 10.5)
    f.text(R, yb, f"{len(WHERE_OUT)} rows: only orders over 25", "t", 11.5, None, 600)
    f.text(R, yb + 16, "Dee's NULL row met WHERE like any other", "tm", 10.5)
    return f


# ------------------------------------------------------------------ 08.03

def ladder0803():
    f = Fig("f0803a", "How the inner table is read: three rules, tried in order; the first that matches wins", 296)
    f.text(24, 20, "on shop.db after " + INDEX_SQL, "tm", 10.5, None, None, True)
    f.text(24, 36, "the rules choose how the table written second is read for each row of the first", "tm", 10.5)
    BH, GAP, Y0 = 58, 8, 48
    for i, (n, cond, ex, out) in enumerate(LADDER):
        y = Y0 + i * (BH + GAP)
        last = i == len(LADDER) - 1
        f.rect(24, y, 592, BH, "s fs" if last else "a af", 6)
        f.circle(44, y + 19, 10, "s f" if last else "a fa")
        f.text(44, y + 23, n, "t", 11.5, "middle", 700)
        f.text(62, y + 23, cond, "t", 11.5, None, 600)
        f.text(62, y + 38, ex, "tm", 10.5, None, None, True)
        f.text(62, y + 52, out, "t" if last else "ta", 10.5, None, 600, True)
    yf = Y0 + len(LADDER) * (BH + GAP) + 16
    f.text(24, yf, "ON o.id = c.id AND o.customer_id = c.id fits rules 1 and 2: rule 1 is tried first, "
           "so the rowid wins", "t", 11)
    f.text(24, yf + 17, "a LEFT JOIN's key must be in its own ON: ON 1 WHERE o.customer_id = c.id gives "
           + LEFTW[1], "tm", 10.5)
    return f


def lookup0803():
    f = Fig("f0803b", "One order's customer: down customers' B-tree to one leaf, against a sweep across every leaf",
            400)
    f.text(24, 22, f"orders o JOIN customers c ON c.id = o.customer_id, on shop.py's file ({SHOP_ROWS[0]} customers, "
           f"{SHOP_ROWS[1]} orders)", "tm", 11)
    # the outer row
    OW = [40, 92, 56]
    f.text(24 + OW[0] / 2, 46, "o.id", "tm", 10, "middle", None, True)
    f.text(24 + OW[0] + OW[1] / 2, 46, "o.customer_id", "tm", 10, "middle", None, True)
    f.text(24 + OW[0] + OW[1] + OW[2] / 2, 46, "o.total", "tm", 10, "middle", None, True)
    cells(f, 24, 52, [(OW[0], LOOK_ORDER[0], "o"), (OW[1], LOOK_ORDER[1], "o"), (OW[2], LOOK_ORDER[2], "o")], h=24)
    ring(f, 24 + OW[0], 52, OW[1], 24, "a")
    f.text(24 + sum(OW) + 14, 62, f"the outer row: order {LOOK_ORDER[0]}", "t", 11.5, None, 600)
    f.text(24 + sum(OW) + 14, 77, f"read by the outer scan from orders leaf {LOOK_ORDER_LEAF}", "tm", 10.5)

    RY, RHt = 140, 40                         # the root
    LY, LH, LW, LG = 212, 28, 34, 7           # the leaves

    def tree(x0, hot):
        """customers' B-tree drawn from x0, 280 wide: the root with its dividers, the leaves under
        it. hot: the lookup's path in the foreground; else the whole tree muted."""
        rs, rt = ("s f", "t") if hot else ("m f", "tm")
        f.rect(x0, RY, 280, RHt, rs, 6)
        f.text(x0 + 140, RY + 15, f"page {CUST_ROOT}", rt, 10.5, "middle", 600, True)
        for i, d in enumerate(CUST_DIVIDERS):
            f.text(x0 + 40 + 40 * i, RY + 32, str(d), "tm", 10, "middle", None, True)
        for i, pg in enumerate(CUST_LEAVES):
            lx = x0 + i * (LW + LG)
            on = hot and i == 0
            f.line(x0 + 20 + 40 * i, RY + RHt, lx + LW / 2, LY - (3 if on else 1), "s" if on else "m", arrow=on)
            f.rect(lx, LY, LW, LH, "s f" if on else "m f", 4, dash=hot and not on)
            f.text(lx + LW / 2, LY + 18, str(pg), "t" if on else "tm", 11, "middle", 700 if on else None, True)

    # the lookup
    LX = 24
    kx = LX + OW[0] + OW[1] / 2
    f.line(kx, 80, kx, RY - 3, "a", arrow=True)
    f.text(kx + 10, 104, f"the key: c.id = {LOOK_ORDER[1]}", "ta", 11, None, 600)
    f.text(kx + 10, 119, f"{LOOK_ORDER[1]} <= {CUST_DIVIDERS[0]}: the first child", "tm", 10.5)
    tree(LX, True)
    ax = LX + LW / 2
    f.line(ax, LY + LH + 2, ax, 268, "s", arrow=True)
    f.text(ax + 12, 256, f"leaf {CUST_LEAVES[0]} holds rows {CUST_LEAF_RANGE[0]} to {CUST_LEAF_RANGE[1]}", "tm", 10.5)
    cells(f, LX, 272, [(24, LOOK_ROW[0], "c"), (84, LOOK_ROW[1], "c"), (50, LOOK_ROW[2], "c")], h=22)
    f.text(LX + 168, 287, f"row {LOOK_ROW[0]}, its customer", "t", 11, None, 600)

    # the sweep, muted, beside it
    SX = 336
    f.text(SX, 104, "without a lookup: SCAN c", "tm", 11.5, None, 600)
    f.text(SX, 119, "the same order against every row", "tm", 10.5)
    tree(SX, False)
    f.line(SX, LY + LH + 14, SX + 278, LY + LH + 14, "m", arrow=True, dash=True)
    f.text(SX, 272, "leaves " + ", ".join(str(p) for p in CUST_LEAVES) + ", in key order", "tm", 10.5)
    f.text(SX, 287, f"{SHOP_ROWS[0]} rows, each tested against c.id = {LOOK_ORDER[1]}", "tm", 10.5)

    yb = 322
    f.text(LX, yb, f"2 pages, {LOOK_REQ} page requests", "t", 11.5, None, 600)
    f.text(LX, yb + 16, LADDER[0][3], "ta", 10, None, None, True)
    f.text(SX, yb, f"{1 + len(CUST_LEAVES)} pages, {SWEEP_REQ:,} page requests", "tm", 11.5, None, 600)
    f.text(SX, yb + 16, "SCAN c", "tm", 10, None, None, True)
    f.line(24, 352, 616, 352, "m")
    f.text(24, 372, "A page request is each time the B-tree code asks the cache for a page: a leaf is asked for",
           "tm", 10.5)
    f.text(24, 388, f"again for each row read from it. The join does this once for every order, {SHOP_ROWS[1]} times.",
           "tm", 10.5)
    return f


def cost0803():
    f = Fig("f0803c", "The same join three ways on shop.py's file: page requests, and time beside them", 306)
    f.text(24, 22, COST_SQL.format("...", "..."), "tm", 10.5, None, None, True)
    f.text(24, 38, f"on shop.py's file, {SHOP_ROWS[1]} rows out each way, in this order: no index, then "
           "CREATE INDEX orders_customer", "tm", 10.5)
    X0, WMAX = 214, 240
    top = max(c[3] for c in COST)
    for i, (frm, on, how, req, read, ms) in enumerate(COST):
        y = 52 + i * 60
        f.text(X0 - 12, y + 14, frm, "t", 10.5, "end", None, True)
        f.text(X0 - 12, y + 28, "ON " + on, "tm", 10, "end", None, True)
        f.text(X0 - 12, y + 43, how, "tm", 10.5, "end")
        w = max(3, WMAX * req / top)
        f.rect(X0, y + 6, w, 24, "s fs" if i == 0 else "a fa", 3)
        f.text(X0 + w + 8, y + 22, f"{req:,} page requests", "t" if i == 0 else "ta", 11, None, 600)
        f.text(X0 + w + 8, y + 38, f"about {ms} ms", "tm", 10.5)
    f.line(24, 240, 616, 240, "m")
    f.text(24, 258, f"The nested loop scans all of orders once per customer: {SHOP_ROWS[0]} x {ORDERS_SCAN:,} "
           "requests, about three a row.", "t", 11)
    ratios = [round(top / c[3]) for c in COST[1:]]
    f.text(24, 275, f"To scale, the two lower bars would be under a pixel long: 1/{ratios[0]} and 1/{ratios[1]} "
           "of the first.", "tm", 10.5)
    reads = [c[4] for c in COST]
    f.text(24, 292, f"Page requests are cache hits plus misses. Pages read from the file: {reads[0]}, {reads[1]} and "
           f"{reads[2]}, each page once.", "tm", 10.5)
    return f


# ------------------------------------------------------------------ cover and icon

def cover():
    f = Fig("m08db", "Two tables joined row by row into one, then many rows made one", 300)
    CW, RH = 24, 18
    TX = 52
    CY, OY = 46, 152                         # customers' grid, orders' grid

    def grid(x, y, nrows, tone):
        cls = TONE[tone][0]
        for r in range(nrows):
            for c in range(3):
                f.rect(x + c * CW, y + r * RH, CW, RH, cls, 0)

    grid(TX, CY, len(CUSTOMERS), "c")
    grid(TX, OY, len(ORDERS), "o")
    # the five joined rows, in the order the loops make them
    JX, JY, GAP = 278, 92, 10
    rows = []
    for k, (name, oid, total) in enumerate(OUTPUT):
        y = JY + k * (RH + GAP)
        for c in range(3):
            f.rect(JX + c * CW, y, CW, RH, TONE["c"][0], 0)
            f.rect(JX + (3 + c) * CW, y, CW, RH, TONE["o"][0], 0)
        ci = next(i for i, cu in enumerate(CUSTOMERS) if cu[1] == name)
        oi = next(i for i, o in enumerate(ORDERS) if o[0] == oid)
        rows.append((y + RH / 2, ci, oi))
    x1, x2 = TX + 3 * CW + 4, JX - 6
    for ym, ci, oi in rows:
        yc = CY + ci * RH + RH / 2
        yo = OY + oi * RH + RH / 2
        f.path(f"M{x1} {yc} C {x1 + 90} {yc}, {x2 - 80} {ym}, {x2} {ym}", "s")
        f.path(f"M{x1} {yo} C {x1 + 90} {yo}, {x2 - 80} {ym}, {x2} {ym}", "a")
    # the London rows narrow into one
    city = {c[1]: c[2] for c in CUSTOMERS}
    RX, RY = 492, JY + 2 * (RH + GAP)
    ex = JX + 6 * CW + 6
    for (name, _, _), (ym, _, _) in zip(OUTPUT, rows):
        if city[name] == LONDON[0]:
            f.path(f"M{ex} {ym} C {ex + 50} {ym}, {RX - 50} {RY + RH / 2}, {RX - 6} {RY + RH / 2}", "m")
    x = RX
    for w, v, tone in ((62, LONDON[0], "c"), (26, LONDON[1], "o"), (38, LONDON[2], "o")):
        cls, tcls = TONE[tone]
        f.rect(x, RY - 4, w, RH + 8, cls, 0)
        f.text(x + w / 2, RY + RH / 2 + 4.5, str(v), tcls, 12.5, "middle", 600, True)
        x += w
    return f


ICON = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="none" stroke="currentColor" '
        'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="2.25" y="2.25" width="10.5" height="10.5" rx="2"/><rect x="7.25" y="7.25" width="10.5" height="10.5" rx="2"/>'
        '<path d="M7.25 7.25h5.5v5.5h-5.5z" fill="currentColor"/></svg>\n')


FIGS = [
    ("08.01-loops", loops0801), ("08.01-row", row0801), ("08.01-tree", tree0801), ("08.01-levels", levels0801),
    ("08.02-nomatch", nomatch0802), ("08.02-on-where", onwhere0802),
    ("08.03-ladder", ladder0803), ("08.03-lookup", lookup0803), ("08.03-cost", cost0803),
]


# ------------------------------------------------------------------ --check: the numbers against a run

def run_at(dbfile, sql, at="08.01", stats=False, stdin=None):
    """The output lines of sql run by the engine at lesson `at` on dbfile (./learn run's own line
    dropped). With stats, DB_STATS=1, and it returns (lines, page requests: cache hits + misses,
    pages read). With stdin and no sql, the engine reads its statements from stdin."""
    argv = [os.path.join(REPO, "learn"), "run", "db", "--at", at, "--", dbfile] + ([sql] if sql else [])
    env = dict(os.environ, DB_STATS="1") if stats else None
    r = subprocess.run(argv, cwd=REPO, capture_output=True, text=True, input=stdin, env=env)
    lines = r.stdout.splitlines()
    if lines and lines[0].startswith("Running db"):
        lines = lines[1:]
    err = r.stderr.strip()
    if stats:
        m = re.search(r"pages read (\d+), cache hits (\d+), cache misses (\d+)", err)
        if r.returncode or not m:
            raise SystemExit(f"{sql}: exit {r.returncode}: {err}")
        return lines, int(m[2]) + int(m[3]), int(m[1])
    if r.returncode or err:
        raise SystemExit(f"{sql}: exit {r.returncode}: {err}")
    return lines


def shop_sql():
    """What shop.py prints, as NOTES gives the script the reader writes in 08.03."""
    out = ["CREATE TABLE customers(id INTEGER PRIMARY KEY, name TEXT, city TEXT);",
           "CREATE TABLE orders(id INTEGER PRIMARY KEY, customer_id INTEGER, total INTEGER);", "BEGIN;"]
    cities = ["London", "Paris", "Oslo", "Rome", "Lima"]
    out += [f"INSERT INTO customers VALUES({i}, 'customer {i}', '{cities[i % 5]}');" for i in range(1, 1001)]
    out += [f"INSERT INTO orders VALUES({i}, {i * 7919 % 1000 + 1}, {i % 100});" for i in range(1, 20001)]
    return "\n".join(out + ["COMMIT;"]) + "\n"


def tree(path, table):
    """Reads table's B-tree out of the database file at path: (root page, the root's divider
    rowids, the leaves in key order as (page, first rowid, last rowid)). Page 1's sqlite_schema
    rows (type, name, tbl_name, rootpage, sql) give the root; an interior table page (0x05) holds
    cells of a 4-byte child page and a varint rowid, then its right child in the header; a leaf
    (0x0d) cells of a varint size, a varint rowid and the record."""
    with open(path, "rb") as fh:
        data = fh.read()
    ps = int.from_bytes(data[16:18], "big") or 65536

    def varint(b, i):
        v = 0
        for k in range(8):
            v = (v << 7) | (b[i + k] & 0x7f)
            if b[i + k] < 0x80:
                return v, i + k + 1
        return (v << 8) | b[i + 8], i + 9

    def page(pg):
        """(kind, right child or None, cells as (child, rowid, record bytes from its header on))."""
        p = data[(pg - 1) * ps: pg * ps]
        h = 100 if pg == 1 else 0
        kind, n = p[h], int.from_bytes(p[h + 3:h + 5], "big")
        hl = 8 if kind == 0x0d else 12
        right = int.from_bytes(p[h + 8:h + 12], "big") if kind == 0x05 else None
        out = []
        for c in range(n):
            i = int.from_bytes(p[h + hl + 2 * c:h + hl + 2 * c + 2], "big")
            if kind == 0x05:
                rowid, _ = varint(p, i + 4)
                out.append((int.from_bytes(p[i:i + 4], "big"), rowid, None))
            else:
                _, i = varint(p, i)
                rowid, i = varint(p, i)
                out.append((None, rowid, p[i:]))
        return kind, right, out

    def fields(rec):
        """A record's values, as far as sqlite_schema's need: NULL, integers and text."""
        hsize, j = varint(rec, 0)
        k, vals = hsize, []
        while j < hsize:
            t, j = varint(rec, j)
            n = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 6, 6: 8, 8: 0, 9: 0}.get(t, (t - 12) // 2)
            b = rec[k:k + n]
            vals.append(None if t == 0 else t - 8 if t in (8, 9) else int.from_bytes(b, "big", signed=True)
                        if t < 12 else b.decode())
            k += n
        return vals

    def leaves(pg):
        kind, right, cs = page(pg)
        if kind == 0x0d:
            return [(pg, cs[0][1], cs[-1][1])]
        return [lf for child, _, _ in cs for lf in leaves(child)] + leaves(right)

    root = next(f[3] for _, _, rec in page(1)[2] for f in [fields(rec)] if f[0] == "table" and f[1] == table)
    kind, _, cs = page(root)
    return root, [rowid for _, rowid, _ in cs] if kind == 0x05 else [], leaves(root)


def check():
    """Builds shop.db (and shop3.db, with lines) with the engine at 08.01 and checks every
    number the figures draw against what it prints."""
    d = tempfile.mkdtemp(prefix="figs08a-")
    shop, shop3 = os.path.join(d, "shop.db"), os.path.join(d, "shop3.db")
    data = ("CREATE TABLE customers(id INTEGER PRIMARY KEY, name TEXT, city TEXT); "
            "CREATE TABLE orders(id INTEGER PRIMARY KEY, customer_id INTEGER, total INTEGER); "
            "INSERT INTO customers VALUES (1,'Ada','London'),(2,'Brook','Paris'),(3,'Chen','London'),(4,'Dee','Oslo'); "
            "INSERT INTO orders VALUES (10,1,30),(11,3,15),(12,1,50),(13,2,20),(14,3,5),(15,NULL,40);")
    for p in (shop, shop3):
        run_at(p, data)
    run_at(shop3, LINES_SQL)

    def same(what, got, want):
        if got != want:
            raise SystemExit(f"{what}: the engine says\n  {got}\nthe figure says\n  {want}")
        print("ok", what)

    def parse(v):
        return None if v == "" else int(v) if v.lstrip("-").isdigit() else v

    same("customers", [tuple(map(parse, l.split("|"))) for l in run_at(shop, "SELECT * FROM customers;")], CUSTOMERS)
    same("orders", [tuple(map(parse, l.split("|"))) for l in run_at(shop, "SELECT * FROM orders;")], ORDERS)
    got = [tuple(map(parse, l.split("|"))) for l in run_at(
        shop, "SELECT c.id, o.id, c.id = o.customer_id FROM customers c CROSS JOIN orders o;")]
    same("pairs and the ON test", got, PAIRS)
    same("the join's output", [tuple(map(parse, l.split("|"))) for l in run_at(shop, JOIN_SQL)], OUTPUT)
    got = run_at(shop, "SELECT c.id, c.name, c.city, c.rowid, o.id, o.customer_id, o.total, o.rowid "
                       "FROM customers c JOIN orders o ON c.id = o.customer_id LIMIT 1;")
    same("the first joined row", [parse(v) for v in got[0].split("|")], [v for _, v, _ in ROW])
    same("EXPLAIN, one table", run_at(shop, TREE1_SQL), TREE1)
    same("EXPLAIN, the join", run_at(shop, TREE2_SQL), TREE2)
    same("EXPLAIN, three tables", run_at(shop3, "EXPLAIN " + LEVELS_Q), LEVELS)
    same("three tables' output", [tuple(map(parse, l.split("|"))) for l in run_at(shop3, LEVELS_Q)], LEVELS_OUT)
    # what each filter tests: the rows the level below passed, times the new table's rows
    n_c = len(run_at(shop3, "SELECT * FROM customers c;"))
    n_o = len(run_at(shop3, "SELECT * FROM orders o;"))
    n_l = len(run_at(shop3, "SELECT * FROM lines l;"))
    p0 = len(run_at(shop3, "SELECT * FROM customers c WHERE c.city = 'London';"))
    p1 = len(run_at(shop3, "SELECT * FROM customers c JOIN orders o ON o.customer_id = c.id WHERE c.city = 'London';"))
    p2 = len(run_at(shop3, LEVELS_Q))
    same("rows each filter tests and passes", ([n_c, p0 * n_o, p1 * n_l], [p0, p1, p2]), (TESTED, PASSED))
    same("three tables, no condition", len(run_at(shop3, "SELECT * FROM customers c, orders o, lines l;")), CROSS3)
    got = [int(l.split("|")[1]) for l in run_at(
        shop, "SELECT c.city, o.total FROM customers c JOIN orders o ON c.id = o.customer_id WHERE c.city = 'London';")]
    same("London's rows: how many, and their totals", (len(got), sum(got)), LONDON[1:])

    # 08.02, the engine at 08.02 on a shop.db of its own
    shop2 = os.path.join(d, "shop2.db")
    run_at(shop2, data, "08.02")

    def rows(sql, at, path):
        return [tuple(map(parse, l.split("|"))) for l in run_at(path, sql, at)]
    same("08.02: the LEFT JOIN's rows", rows(NOMATCH_SQL, "08.02", shop2), NOMATCH)
    same("08.02: ... in the same order with ORDER BY c.id, o.id",
         rows(NOMATCH_SQL[:-1] + " ORDER BY c.id, o.id;", "08.02", shop2), NOMATCH)
    same("08.02: Dee's row: typeof(o.id), o.rowid", rows(DEE_SQL, "08.02", shop2), [DEE])
    same("08.02: o.total > 25 in ON", rows(ON_SQL, "08.02", shop2), ON_OUT)
    same("08.02: o.total > 25 in WHERE", rows(WHERE_SQL, "08.02", shop2), WHERE_OUT)
    same("08.02: what WHERE is handed, and the term on each", rows(WHERE_IN_SQL, "08.02", shop2), WHERE_IN)
    same("08.02: EXPLAIN, the term in ON", run_at(shop2, "EXPLAIN " + ON_SQL, "08.02"), ON_TREE)
    same("08.02: EXPLAIN, the term in WHERE", run_at(shop2, "EXPLAIN " + WHERE_SQL, "08.02"), WHERE_TREE)

    # 08.03: the ladder, on a shop.db with the index
    shop3x = os.path.join(d, "shop3x.db")
    run_at(shop3x, data + " " + INDEX_SQL, "08.03")
    for frm, line in [(c[2], c[3]) for c in LADDER] + [BOTH, LEFTW]:
        got = run_at(shop3x, f"EXPLAIN QUERY PLAN SELECT * {frm};", "08.03")
        same(f"08.03: EXPLAIN QUERY PLAN ... {frm[5:]}", got[-1], "`--" + line)

    # 08.03: shop.py's file, its pages, and what the lookup and the scan ask for
    big = os.path.join(d, "shop.big.db")
    run_at(big, None, "08.03", stdin=shop_sql())
    same("shop.py's file: customers and orders", [len(run_at(big, f"SELECT id FROM {t};", "08.03"))
                                                   for t in ("customers", "orders")], list(SHOP_ROWS))
    same("shop.py's file: pages", os.path.getsize(big) // 4096, SHOP_PAGES)
    root, divs, lvs = tree(big, "customers")
    same("customers: root page, its dividers, its leaves in key order",
         (root, divs, [p for p, _, _ in lvs]), (CUST_ROOT, CUST_DIVIDERS, CUST_LEAVES))
    home = next(lf for lf in lvs if lf[1] <= LOOK_ROW[0] <= lf[2])
    same("the leaf customer 3 is in, and its rows", home, (CUST_LEAVES[0],) + CUST_LEAF_RANGE)
    _, _, olvs = tree(big, "orders")
    same("the orders leaf of order 358", next(p for p, a, b in olvs if a <= LOOK_ORDER[0] <= b), LOOK_ORDER_LEAF)
    same("order 358", rows(f"SELECT * FROM orders WHERE id = {LOOK_ORDER[0]};", "08.03", big), [LOOK_ORDER])
    same("customer 3's first order", rows(f"SELECT id FROM orders WHERE customer_id = {LOOK_ORDER[1]} LIMIT 1;",
                                          "08.03", big), [(LOOK_ORDER[0],)])
    same("customer 3", rows(f"SELECT * FROM customers WHERE id = {LOOK_ORDER[1]};", "08.03", big), [LOOK_ROW])
    _, alone, _ = run_at(big, ALONE_SQL, "08.03", stats=True)
    out1, look, _ = run_at(big, LOOK_SQL, "08.03", stats=True)
    out2, sweep, _ = run_at(big, SWEEP_SQL, "08.03", stats=True)
    same("the lookup and the scan find the same row", out1, out2)
    same("how customers is read, each way", [run_at(big, "EXPLAIN QUERY PLAN " + q, "08.03")[-1]
                                          for q in (LOOK_SQL, SWEEP_SQL)], ["`--" + LADDER[0][3], "`--SCAN c"])
    same("page requests for order 358's customer: lookup, scan", (look - alone, sweep - alone), (LOOK_REQ, SWEEP_REQ))

    # 08.03: the same join three ways, as the lesson runs them: on the one file, the first with no
    # index, then CREATE INDEX, then the other two with the index in the schema
    binary = os.path.join(REPO, "build", "at", "db", "08.03", "db")    # what ./learn run just built
    _, base, _ = run_at(big, "SELECT 1;", "08.03", stats=True)
    _, scan_o, _ = run_at(big, "SELECT id FROM orders;", "08.03", stats=True)
    _, scan_c, _ = run_at(big, "SELECT id FROM customers;", "08.03", stats=True)
    same("one scan of orders, less the statement's own requests", scan_o - base, ORDERS_SCAN)
    same("the nested loop: customers x one scan of orders + the scan of customers + the statement's own",
         SHOP_ROWS[0] * (scan_o - base) + (scan_c - base) + base, COST[0][3])
    for i, (frm, on, how, req, read, ms) in enumerate(COST):
        if i == 1:
            run_at(big, INDEX_SQL, "08.03")
            same("with the index: pages", os.path.getsize(big) // 4096, SHOP_PAGES_IX)
        sql = COST_SQL.format(frm, on)
        lines, got, pages = run_at(big, sql, "08.03", stats=True)
        same(f"{frm} ON {on}, {how}: rows, page requests, pages read", (len(lines), got, pages),
             (SHOP_ROWS[1], req, read))
        ts = []
        for _ in range(7):
            with open(os.devnull, "w") as dn:
                t = time.perf_counter()
                subprocess.run([binary, big, sql], stdout=dn, check=True)
                ts.append((time.perf_counter() - t) * 1000)
        print(f"   time, median of 7: {statistics.median(ts):.1f} ms (the figure says about {ms} ms)")


def main():
    if sys.argv[1:] == ["--check"]:
        return check()
    for name, fn in FIGS:
        fig = fn()
        print(figlib.write(MOD, name, fig))
    loops = os.path.join(figlib.LESSONS, MOD, "figures", "08.01-loops.svg")
    with open(loops) as fh:
        print("08.01-loops:", steps.check(fh.read()), "steps")
    d = os.path.join(figlib.LESSONS, MOD)
    s = cover().svg()
    s.encode("ascii")
    with open(os.path.join(d, "cover.svg"), "w") as fh:
        fh.write(s)
    with open(os.path.join(d, "icon.svg"), "w") as fh:
        fh.write(ICON)
    print("cover and icon in", d)


if __name__ == "__main__":
    main()
