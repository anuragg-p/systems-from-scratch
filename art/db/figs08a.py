"""Figures for db module 08, More SQL: lessons 08.01-08.03 (08.02's and 08.03's are still to come),
and the module's cover and icon.

    python3 art/db/figs08a.py           writes tracks/db/lessons/08-more-sql/figures/08.0[1-3]-*.svg,
                                        cover.svg and icon.svg
    python3 art/db/figs08a.py --check   runs the queries below through the engine at 08.01
                                        (./learn run db --at 08.01) and checks every number

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
"""
import os
import subprocess
import sys
import tempfile

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
# (08.02's figures go here: one function each, and a line each in FIGS below.)


# ------------------------------------------------------------------ 08.03
# (08.03's figures go here: one function each, and a line each in FIGS below.)


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
]


# ------------------------------------------------------------------ --check: the numbers against a run

def run_at(dbfile, sql):
    """The output lines of sql run by the engine at 08.01 on dbfile (./learn run's own line dropped)."""
    r = subprocess.run([os.path.join(REPO, "learn"), "run", "db", "--at", "08.01", "--", dbfile, sql],
                       cwd=REPO, capture_output=True, text=True)
    lines = r.stdout.splitlines()
    if lines and lines[0].startswith("Running db"):
        lines = lines[1:]
    if r.returncode or r.stderr.strip():
        raise SystemExit(f"{sql}: exit {r.returncode}: {r.stderr.strip()}")
    return lines


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
