"""Figures for db module 08, More SQL: lessons 08.04 and 08.05.

    python3 art/db/figs08b.py           writes tracks/db/lessons/08-more-sql/figures/08.0[45]-*.svg
    python3 art/db/figs08b.py --check   runs the queries below through the engine at each figure's
                                        lesson (./learn run db --at 08.04, 08.05) and checks every
                                        value, state, row count and operator name the figures draw

The look is 08.01's (figs08a.py, whose helpers these use): customers' values in the neutral tone,
orders' values in the accent tone; NULL an empty dashed cell with the word NULL in muted text.
An aggregate over orders (a count of orders, a sum of their totals) is drawn in the orders' tone,
as the module cover draws "London 4 100".

Every value comes from the engine on the module's data set, shop.db (DATA_SQL, the same as
figs08a's): `./learn run db --at 08.04 -- shop.db "<sql>"` for 08.04's figures, --at 08.05 for
08.05's. The states inside the Aggregate and the Distinct, which no query prints, were read from
a traced run: a copy of the project (./learn files db --at 08.04 DIR, and --at 08.05) with
fprintfs added to exec.c (after aggregate_next steps a row: the row and every Agg's n and isum;
in group_done: the row handed up; in set_add: the list, its hash's slot, the slot it took, new
or seen; and a counter on every operator's next(), printed by op_close). What it printed is
quoted below and in tracks/db/NOTES.md (08.04 and 08.05 blocks). --check rederives each of those
numbers from queries the plain engine runs, as said for each figure.

08.04-step (stepped): STEP_SQL. The traced copy printed, after each row (rowid order, as the
  Scan hands them up), count(*)'s n, count(customer_id)'s n and sum(total)'s isum: STATES; then
  "group done" with 6 5 160, and the query prints 6|5|160. --check: the state after the first k
  rows is the same query over WHERE id <= (the k-th order's id), the rows are SELECT * FROM
  orders in the order the scan gives them, and EXPLAIN gives the box names (STEP_TREE).
08.04-functions: what each function keeps, steps and finishes is exec.c's agg_step and
  agg_finish at 08.04 (NOTES' table, from func.c). The "empty input" column is what the engine
  prints for EMPTY_SQL on a table with no rows: EMPTY_OUT, with typeof() of each (EMPTY_TYPES)
  telling the NULLs (printed as nothing) from the text.
08.05-groups (stepped): GROUP_SQL. EXPLAIN is GROUP_TREE; the Sort hands the Aggregate SORTED
  (NULL first, equal keys in rowid order). The traced copy printed, row by row: order 15 count 1
  sum 40; group done |1|40; order 10 count 1 sum 30; order 12 count 2 sum 80; group done 1|2|80;
  order 13 count 1 sum 20; group done 2|1|20; order 11 count 1 sum 15; order 14 count 2 sum 20;
  group done 3|2|20 (at the end of the input). HAND and DONE are that, frame by frame. --check:
  the same query over the first k sorted rows (WHERE id IN (...)) gives the groups done so far
  and, last, the group in hand.
08.05-pipeline: PIPE_SQL; EXPLAIN prints PIPE_TREE. Rows each operator handed up, counted by the
  traced copy: Scan customers 4, Scan orders 24, Join 24, Filter (o.customer_id = c.id) 5, Sort by
  city DESC 5, Aggregate 2, Filter (count(*) > 1) 1, Sort by sum(total) DESC 1 (PIPE_ROWS). The
  Aggregate's rows, Paris|1|20 then London|4|100, are the query without HAVING and ORDER BY with
  ORDER BY city DESC (the order the Sort under it gives). --check rederives each count with a
  counting query (PIPE_COUNTS).
08.05-distinct: DIST_SQL prints DIST_OUT; EXPLAIN is DIST_TREE. The traced copy printed set_add
  new 'London' home 0 slot 0 cap 16; new 'Paris' home 5 slot 5; seen 'London' slot 0; new 'Oslo'
  home 13 slot 13. --check computes the slots again with set_hash's FNV-1a (exec.c at 08.05:
  the value's type tag, then its bytes; the slot is the hash's low bits, SET_MIN 16 slots), and
  checks the four rows the scan gives.
"""
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import figlib  # noqa: E402
from figlib import tw  # noqa: E402
import steps  # noqa: E402
import figs08a as A  # noqa: E402  the module's look, its data and run_at

REPO = A.REPO
MOD = A.MOD
Fig, cells, ring, val, TONE = A.Fig, A.cells, A.ring, A.val, A.TONE
CUSTOMERS, ORDERS = A.CUSTOMERS, A.ORDERS

DATA_SQL = ("CREATE TABLE customers(id INTEGER PRIMARY KEY, name TEXT, city TEXT); "
            "CREATE TABLE orders(id INTEGER PRIMARY KEY, customer_id INTEGER, total INTEGER); "
            "INSERT INTO customers VALUES (1,'Ada','London'),(2,'Brook','Paris'),(3,'Chen','London'),(4,'Dee','Oslo'); "
            "INSERT INTO orders VALUES (10,1,30),(11,3,15),(12,1,50),(13,2,20),(14,3,5),(15,NULL,40);")

# ------------------------------------------------------------------ 08.04, the engine at 08.04

STEP_SQL = "SELECT count(*), count(customer_id), sum(total) FROM orders;"
STEP_TREE = ["Aggregate count(*), count(customer_id), sum(total)", "  Scan orders"]
STEP_AGGS = ["count(*)", "count(customer_id)", "sum(total)"]
STEP_FIELDS = ["n", "n", "isum"]               # the Agg field each box shows
# count(*)'s n, count(customer_id)'s n, sum(total)'s isum after each row, in ORDERS' order
STATES = [(1, 1, 30), (2, 2, 45), (3, 3, 95), (4, 4, 115), (5, 5, 120), (6, 5, 160)]
STEP_OUT = (6, 5, 160)

EMPTY_TABLE = "CREATE TABLE empty(x INTEGER);"
EMPTY_SQL = "SELECT count(*), count(x), sum(x), total(x), avg(x), min(x), max(x) FROM empty;"
EMPTY_OUT = "0|0||0.0|||"
EMPTY_TYPES = ["integer", "integer", "null", "real", "null", "null", "null"]
# (function, its state, a step, the finish): exec.c's agg_step and agg_finish at 08.04, one
# string a line; `...` is an Agg field or a name from the code, set in mono
FUNCS = [
    ("count(*)", ["`n`"], ["every row: `n` + 1"], ["`n`"]),
    ("count(x)", ["`n`"], ["x not NULL: `n` + 1"], ["`n`"]),
    ("sum(x)", ["`n`, `isum`: exact", "`rsum`, `rerr`: a real"], ["x not NULL: `n` + 1, add x:", "in `isum` while all integers"],
     ["`isum` while all integers,", "else the real sum;", "overflow: an error"]),
    ("total(x)", ["as sum"], ["as sum"], ["the sum, always a real"]),
    ("avg(x)", ["as sum"], ["as sum"], ["the sum / `n`, a real"]),
    ("min(x)", ["`best`, a copy"], ["x not NULL and less than", "`best`: x is the new `best`"], ["`best`"]),
    ("max(x)", ["`best`, a copy"], ["x not NULL and more than", "`best`: x is the new `best`"], ["`best`"]),
]

# ------------------------------------------------------------------ 08.05, the engine at 08.05

GROUP_SQL = "SELECT customer_id, count(*), sum(total) FROM orders GROUP BY customer_id;"
GROUP_TREE = ["Aggregate count(*), sum(total) by customer_id", "  Sort by customer_id", "    Scan orders"]
SORTED = [(15, None, 40), (10, 1, 30), (12, 1, 50), (13, 2, 20), (11, 3, 15), (14, 3, 5)]
GROUPS = [(None, 1, 40), (1, 2, 80), (2, 1, 20), (3, 2, 20)]
# after each sorted row: the group in hand (key, count, sum), and how many groups are done
HAND = [(None, 1, 40), (1, 1, 30), (1, 2, 80), (2, 1, 20), (3, 1, 15), (3, 2, 20)]
DONE = [0, 1, 1, 2, 3, 3]

PIPE_SQL = ("SELECT city, count(*), sum(total) FROM customers c JOIN orders o ON o.customer_id = c.id "
            "GROUP BY city HAVING count(*) > 1 ORDER BY 3 DESC;")
PIPE_TREE = ["Sort by sum(total) DESC", "  Filter (count(*) > 1)", "    Aggregate count(*), sum(total) by city",
             "      Sort by city DESC", "        Filter (o.customer_id = c.id)", "          Join",
             "            Scan customers AS c", "            Scan orders AS o"]
PIPE_ROWS = {"Scan customers AS c": 4, "Scan orders AS o": 24, "Join": 24, "Filter (o.customer_id = c.id)": 5,
             "Sort by city DESC": 5, "Aggregate count(*), sum(total) by city": 2, "Filter (count(*) > 1)": 1,
             "Sort by sum(total) DESC": 1}
PIPE_JOIN = "FROM customers c JOIN orders o ON o.customer_id = c.id"
# a counting query for each operator's rows (the inner scan runs once per customer: one row
# for each pair, as many as the Join's)
PIPE_COUNTS = {
    "Scan customers AS c": "SELECT count(*) FROM customers c;",
    "Scan orders AS o": "SELECT count(*) FROM customers c CROSS JOIN orders o;",
    "Join": "SELECT count(*) FROM customers c CROSS JOIN orders o;",
    "Filter (o.customer_id = c.id)": f"SELECT count(*) {PIPE_JOIN};",
    "Sort by city DESC": f"SELECT count(*) {PIPE_JOIN};",
    "Aggregate count(*), sum(total) by city": f"SELECT city {PIPE_JOIN} GROUP BY city;",
    "Filter (count(*) > 1)": f"SELECT city {PIPE_JOIN} GROUP BY city HAVING count(*) > 1;",
    "Sort by sum(total) DESC": PIPE_SQL,
}
AGG_ROWS_SQL = f"SELECT city, count(*), sum(total) {PIPE_JOIN} GROUP BY city ORDER BY city DESC;"
AGG_ROWS = [("Paris", 1, 20), ("London", 4, 100)]
PIPE_OUT = [("London", 4, 100)]

DIST_SQL = "SELECT DISTINCT city FROM customers;"
DIST_TREE = ["Distinct city", "  Scan customers"]
DIST_OUT = ["London", "Paris", "Oslo"]
SET_CAP = 16
SLOTS = {"London": 0, "Paris": 5, "Oslo": 13}


# ------------------------------------------------------------------ helpers

def row_cells(f, x, y, widths, values, tone, h=24, size=11, muted=False):
    """One row of a table, its values in tone ("c" or "o"); muted draws them as done with
    (the muted outline and text), NULL still as the dashed cell."""
    if not muted:
        return cells(f, x, y, list(zip(widths, values, [tone] * len(values))), h=h, size=size)
    for w, v in zip(widths, values):
        if v is None:
            cells(f, x, y, [(w, None, tone)], h=h, size=size)
        else:
            f.rect(x, y, w, h, "m fs", 0)
            f.text(x + w / 2, y + h / 2 + size * 0.36, str(v), "tm", size, "middle", None, True)
        x += w
    return x


def heads(f, x, y, widths, names, size=10):
    for w, n in zip(widths, names):
        f.text(x + w / 2, y, n, "tm", size, "middle", None, True)
        x += w


def curve(f, x1, y1, x2, y2, cls="s", arrow=True, dash=False, k=36):
    f.path(f"M{x1} {y1} C {x1 + k} {y1}, {x2 - k} {y2}, {x2} {y2}", cls, arrow=arrow, dash=dash)


# ------------------------------------------------------------------ 08.04

def step0804():
    f = Fig("f0804a", "Three aggregates over orders: every row steps each state; the finish makes one row", 300)
    f.text(24, 22, STEP_SQL, "tm", 10.5, None, None, True)
    OX, OW, Y0, RH = 64, [34, 84, 46], 82, 26
    ow = sum(OW)
    f.text(OX, 52, "orders, as the Scan hands them up", "ta", 11.5, None, 600)
    heads(f, OX, 74, OW, ["id", "customer_id", "total"])
    BX, BW, BH = 296, 222, 56
    BY = [60, 128, 196]
    FX, FW = 556, 56
    f.text(BX, 52, "the Aggregate's state", "t", 11.5, None, 600)

    def mid(i):
        return Y0 + i * RH + RH / 2

    def table(now):
        """The orders, those stepped already muted, row `now` ringed."""
        for i, row in enumerate(ORDERS):
            row_cells(f, OX, Y0 + i * RH, OW, row, "o", h=RH, muted=i < now)
        if now < len(ORDERS):
            ring(f, OX, Y0 + now * RH, ow, RH, "a")
            f.text(OX - 10, mid(now) + 4, "now", "ta", 10.5, "end", 600)

    def box(k, value, note, skipped=False):
        y = BY[k]
        f.rect(BX, y, BW, BH, "m f" if skipped else "s f", 6, dash=skipped)
        f.text(BX + 12, y + 22, STEP_AGGS[k], "tm" if skipped else "t", 11.5, None, 600, True)
        f.text(BX + 12, y + 42, note, "ta" if skipped else "tm", 10.5, None, 600 if skipped else None)
        f.text(BX + BW - 12, y + 19, STEP_FIELDS[k], "tm", 10, "end", None, True)
        f.text(BX + BW - 12, y + 43, str(value), "tm" if skipped else "ta", 19, "end", 600, True)

    # the row goes to every aggregate: along a bus beside the boxes, one branch to each
    BUS = BX - 34

    def feed(i, skip):
        f.line(OX + ow + 4, mid(i), BUS, mid(i), "a")
        ys = [BY[k] + BH / 2 for k in range(3)] + [mid(i)]
        f.line(BUS, min(ys), BUS, max(ys), "a")
        for k in range(3):
            ym = BY[k] + BH / 2
            if k == 1 and skip:
                f.line(BUS, ym, BX - 14, ym, "m", dash=True)
                f.line(BX - 12, ym - 8, BX - 12, ym + 8, "m")
            else:
                f.line(BUS, ym, BX - 5, ym, "a", arrow=True)

    prev = (0, 0, 0)
    for i, ((oid, cust, total), state) in enumerate(zip(ORDERS, STATES)):
        skip = cust is None
        notes = ["a row: n + 1",
                 "customer_id NULL: skipped" if skip else f"customer_id {cust}: n + 1",
                 f"total {total}: {prev[2]} + {total}"]
        if skip:
            cap = (f"Order {oid}: count(*) counts the row ({state[0]}); its customer_id is NULL, so "
                   f"count(customer_id) skips it and stays at {state[1]}; sum(total) adds {total}: {state[2]}.")
        else:
            cap = (f"Order {oid} (customer_id {cust}, total {total}): both counts add one, to {state[0]} and "
                   f"{state[1]}; sum(total) adds {total}: {prev[2]} + {total} = {state[2]}.")
        with steps.step(f, cap):
            table(i)
            feed(i, skip)
            for k in range(3):
                box(k, state[k], notes[k], skipped=k == 1 and skip)
        prev = state
    out = "|".join(str(v) for v in STEP_OUT)
    with steps.step(f, f"The input is done. The finish turns each state into its answer, and one row comes out: "
                       f"{out}. Order 15 is in count(*) and sum(total), not in count(customer_id)."):
        table(len(ORDERS))
        f.text(FX + FW / 2, 52, "finish", "t", 11.5, "middle", 600)
        for k in range(3):
            ym = BY[k] + BH / 2
            box(k, STATES[-1][k], ["finish: n", "finish: n", "finish: isum, an integer"][k])
            f.line(BX + BW + 4, ym, FX - 5, ym, "a", arrow=True)
            cells(f, FX, ym - 13, [(FW, STEP_OUT[k], "o")], h=26, size=12)
        f.text(FX + FW, 272, "one row out", "t", 11.5, "end", 600)
        f.text(FX + FW, 288, out, "ta", 11, "end", 600, True)
    return f


def rich(f, x, y, s, cls="t", size=10.5):
    """One line of text in which `...` parts are set in mono (a field or a name from the code):
    one <text>, the mono parts as <tspan>s, so the spaces between them stay as the font sets them."""
    body = "".join(figlib.esc(p) if j % 2 == 0 else f'<tspan class="mono">{figlib.esc(p)}</tspan>'
                   for j, p in enumerate(s.split("`")) if p)
    f.add(f'<text class="{cls}" x="{figlib.fmt(x)}" y="{figlib.fmt(y)}" font-size="{figlib.fmt(size)}">{body}</text>')


def functions0804():
    f = Fig("f0804b", "The seven aggregates: the state each keeps, its step, its finish, and its answer over no rows",
            424)
    f.text(24, 22, "what agg_step() and agg_finish() do for each function, and what each gives over no rows", "tm", 11)
    COLS = [("function", 80), ("state", 124), ("a step", 164), ("the finish", 156), ("empty input", 68)]
    xs = [24]
    for _, w in COLS[:-1]:
        xs.append(xs[-1] + w)
    HY, Y0, LH = 52, 64, 15
    for (name, _), x in zip(COLS[:-1], xs):
        f.text(x + 8, HY, name, "t", 11, None, 600)
    f.text(616, HY, COLS[-1][0], "t", 11, "end", 600)
    f.line(24, Y0 - 4, 616, Y0 - 4, "s")
    y = Y0
    for k, (fn, state, step, fin) in enumerate(FUNCS):
        n = max(len(state), len(step), len(fin))
        h = 16 + n * LH
        f.text(xs[0] + 8, y + 19, fn, "t", 11.5, None, 600, True)
        for col, lines in ((1, state), (2, step), (3, fin)):
            for j, s in enumerate(lines):
                rich(f, xs[col] + 8, y + 19 + j * LH, s, "tm" if lines == ["as sum"] else "t")
        v = EMPTY_OUT.split("|")[k] if EMPTY_TYPES[k] != "null" else None
        cells(f, 616 - 54, y + 5, [(52, v, "c")], h=22, size=11)
        y += h
        f.line(24, y, 616, y, "m")
    yb = y + 26
    f.text(24, yb, "Over a table with no rows the engine prints one row all the same:", "t", 11)
    f.text(24, yb + 20, EMPTY_SQL, "tm", 10, None, None, True)
    e = A.spans(f, 24, yb + 38, [(EMPTY_OUT, "t", 700)], 11)
    f.text(e + 12, yb + 38, "a NULL prints as nothing: sum, avg, min and max have no value to give", "tm", 10.5)
    return f


# ------------------------------------------------------------------ 08.05

def groups0805():
    f = Fig("f0805a", "GROUP BY by sorting: a group ends where the key changes, and its row goes up", 302)
    f.text(24, 22, GROUP_SQL, "tm", 10.5, None, None, True)
    OX, OW, Y0, RH = 64, [34, 84, 46], 82, 26
    ow = sum(OW)
    f.text(OX, 52, "orders, as the Sort hands them up", "ta", 11.5, None, 600)
    heads(f, OX, 74, OW, ["id", "customer_id", "total"])
    GX, GW = 296, [88, 68, 80]
    gw = sum(GW)
    f.text(GX, 52, "the group in hand", "t", 11.5, None, 600)
    heads(f, GX, 74, GW, ["customer_id", "count(*)", "sum(total)"])
    OY = 196                                  # the groups done
    f.text(GX, OY - 12, "groups done, handed up", "t", 11.5, None, 600)

    def mid(i):
        return Y0 + i * RH + RH / 2

    # where each group's rows end in the sorted column
    ends = [i for i in range(len(SORTED)) if i == len(SORTED) - 1 or SORTED[i + 1][1] != SORTED[i][1]]

    def frame(now, done, hand, why):
        for i, row in enumerate(SORTED):
            row_cells(f, OX, Y0 + i * RH, OW, row, "o", h=RH, muted=i < now)
        # a bracket beside the rows of each group done
        start = 0
        for g in range(done):
            e = ends[g]
            A.brace_v(f, OX + ow + 14, Y0 + start * RH + 4, Y0 + (e + 1) * RH - 4, "s")
            start = e + 1
        if now < len(SORTED):
            ring(f, OX, Y0 + now * RH, ow, RH, "a")
            f.text(OX - 10, mid(now) + 4, "now", "ta", 10.5, "end", 600)
            curve(f, OX + ow + 4, mid(now), GX - 6, Y0 + 13, "a", k=48)
        if hand:
            row_cells(f, GX, Y0, GW, hand, "o", h=26)
        else:
            f.rect(GX, Y0, gw, 26, "m f", 0)
            f.text(GX + gw / 2, Y0 + 17, "none", "tm", 10.5, "middle")
        f.text(GX, Y0 + 50, why[0], "t", 11, None, 600)
        if len(why) > 1:
            f.text(GX, Y0 + 66, why[1], "tm", 10.5)
        for g in range(done):
            row_cells(f, GX, OY + g * 24, GW, GROUPS[g], "o", h=24)
        if not done:
            f.text(GX, OY + 16, "none yet", "tm", 10.5)

    def new(g, note):
        ring(f, GX, OY + g * 24, gw, 24)
        f.text(GX + gw + 12, OY + g * 24 + 16, note, "t", 10.5, None, 600)

    for i, ((oid, key, total), hand, done) in enumerate(zip(SORTED, HAND, DONE)):
        closed = i > 0 and done > DONE[i - 1]
        if i == 0:
            why = ("the first row: a group starts", f"key {val(key)}: the Sort put NULL first")
            cap = (f"Order {oid} comes first: the Sort put the NULL key before every number. A group starts "
                   f"with it: count {hand[1]}, sum {hand[2]}.")
        elif closed:
            last = GROUPS[done - 1]
            why = (f"{val(key)} is not {val(SORTED[i - 1][1])}: the key changed",
                   f"group {val(last[0])} is done; order {oid} starts group {val(key)}")
            cap = (f"Order {oid}: its customer_id {val(key)} differs from the group's {val(last[0])}, so that group "
                   f"is done and its row ({val(last[0])}, {last[1]}, {last[2]}) goes up; order {oid} starts group "
                   f"{val(key)}: count {hand[1]}, sum {hand[2]}.")
        else:
            why = (f"{val(key)} is {val(SORTED[i - 1][1])}: the same group", "count + 1, sum + " + str(total))
            cap = (f"Order {oid}: customer_id {val(key)} again, the same group: count {hand[1]}, "
                   f"sum {hand[2] - total} + {total} = {hand[2]}.")
        with steps.step(f, cap):
            frame(i, done, hand, why)
            if closed:
                new(done - 1, "key changed")
    last = GROUPS[-1]
    with steps.step(f, f"The input ends, so the last group is done too: ({last[0]}, {last[1]}, {last[2]}) goes up. "
                       f"{len(GROUPS)} groups from {len(SORTED)} rows, in key order."):
        frame(len(SORTED), len(GROUPS), None, ("no more rows: the input ended", f"group {last[0]} is done"))
        new(len(GROUPS) - 1, "input ended")
    return f


def pipeline0805():
    f = Fig("f0805b", "GROUP BY, HAVING and ORDER BY as operators, with the rows each one hands up", 560)
    f.text(24, 20, PIPE_SQL[:PIPE_SQL.index(" GROUP BY")], "tm", 10, None, None, True)
    f.text(24, 35, "  " + PIPE_SQL[PIPE_SQL.index("GROUP BY"):], "tm", 10, None, None, True)
    BH, SX = 28, 214
    names = [l.strip() for l in PIPE_TREE]
    # bottom to top along the spine: the first scan, the join, then everything above it
    spine = [names[6], names[5], names[4], names[3], names[2], names[1], names[0]]
    ys = [474, 410, 346, 282, 218, 154, 90]
    NX = {}                                   # where each spine box's note starts

    def op(cx, y, label, cls="s f", tcls="t", weight=None):
        w = tw(label, 11, True) + 26
        f.rect(cx - w / 2, y, w, BH, cls, 6)
        f.text(cx, y + 18.5, label, tcls, 11, "middle", weight, True)
        return cx + w / 2

    for name, y in zip(spine, ys):
        NX[name] = op(SX, y, name, weight=600 if name.startswith(("Aggregate", "Filter (count")) else None) + 14
    RX = 520
    op(RX, ys[1], names[7], "a af", "ta")
    # the rows along each edge
    for k in range(len(spine) - 1):
        y1, y2 = ys[k], ys[k + 1] + BH
        n = PIPE_ROWS[spine[k]]
        f.line(SX, y1 - 2, SX, y2 + 3, "s", arrow=True)
        f.text(SX + 8, (y1 + y2) / 2 + 4, f"{n} row{'s' if n != 1 else ''}", "tm", 10.5)
    # the Aggregate's two rows on the edge above it, in the order it hands them up
    k = spine.index(names[2])
    ay = (ys[k] + ys[k + 1] + BH) / 2 - 10
    x = SX + 66
    for city, n, s in AGG_ROWS:
        x = A.cells(f, x, ay, [(56, city, "c"), (24, n, "o"), (34, s, "o")], h=20, size=10) + 10
    n_o = PIPE_ROWS[names[7]]
    f.line(RX - 66, ys[1] + BH / 2, SX + 40, ys[1] + BH / 2, "a", arrow=True)
    f.text((RX - 66 + SX + 40) / 2, ys[1] + BH / 2 - 6, f"{n_o} rows", "tm", 10.5, "middle")
    f.text(RX, ys[1] + BH + 15, f"{len(ORDERS)} rows for each of {len(CUSTOMERS)} customers", "tm", 10, "middle")
    # the top: the rows out
    top = PIPE_ROWS[spine[-1]]
    f.line(SX, ys[-1] - 2, SX, 52, "s", arrow=True)
    f.text(SX + 8, 70, f"{top} row out", "t", 11, None, 600)
    A.cells(f, SX + 84, 56, [(62, PIPE_OUT[0][0], "c"), (26, PIPE_OUT[0][1], "o"), (36, PIPE_OUT[0][2], "o")], h=22)

    def note(name, first, second=None, mono=True):
        y = ys[spine.index(name)]
        f.text(NX[name], y + (12 if second else 18.5), first, "tm", 10, None, None, mono)
        if second:
            f.text(NX[name], y + 26, second, "tm", 10.5)

    note(spine[0], "FROM customers c")
    note(spine[2], "ON o.customer_id = c.id", f"{PIPE_ROWS[spine[2]]} of the {PIPE_ROWS[spine[1]]} pairs match")
    note(spine[3], "GROUP BY city, sorted first", "DESC: the direction of ORDER BY 3 DESC")
    note(spine[4], "GROUP BY city", "a row each time city changes")
    note(spine[5], "HAVING count(*) > 1", "WHERE, but over the groups' rows")
    note(spine[6], "ORDER BY 3 DESC")
    f.line(24, 518, 616, 518, "m")
    f.text(24, 538, "Each operator pulls rows from the one below it: the Aggregate reads all 5 joined rows, "
                    "sorted, and hands up 2.", "tm", 10.5)
    return f


def distinct0805():
    f = Fig("f0805c", "SELECT DISTINCT: a row goes on only if its city is not in the set yet", 344)
    f.text(24, 22, DIST_SQL, "tm", 10.5, None, None, True)
    f.text(24 + tw(DIST_SQL, 10.5, True) + 16, 22, "EXPLAIN: " + " over ".join(l.strip() for l in DIST_TREE),
           "tm", 10.5)
    CX, CW, Y0, RH = 40, [26, 52, 62], 78, 34
    cw = sum(CW)
    f.text(CX, 52, "customers (Scan)", "t", 11.5, None, 600)
    heads(f, CX, 70, CW, ["id", "name", "city"])
    VX = CX + cw + 46                       # the test, beside each row
    PX, PW = 532, 70                        # what the Distinct hands up
    f.text(VX, 52, "is the city in the set?", "t", 11.5, None, 600)
    f.text(PX, 52, "out", "t", 11.5, None, 600)
    seen = set()
    for i, (cid, name, city) in enumerate(CUSTOMERS):
        y = Y0 + i * RH
        ym = y + 13
        row_cells(f, CX, y + 1, CW, (cid, name, city), "c", h=24)
        f.line(CX + cw + 6, ym, VX - 8, ym, "s", arrow=True)
        if city in seen:
            f.text(VX, ym - 2, f"{city}: in slot {SLOTS[city]} already", "tm", 11, None, 600)
            f.text(VX, ym + 13, "seen: the row stops here", "tm", 10.5)
            f.line(VX + 196, ym, PX - 52, ym, "m", dash=True)
            f.line(PX - 50, ym - 8, PX - 50, ym + 8, "m")
        else:
            seen.add(city)
            f.text(VX, ym - 2, f"{city}: not in the set", "t", 11, None, 600)
            f.text(VX, ym + 13, f"new: a copy goes in slot {SLOTS[city]}", "tm", 10.5)
            f.line(VX + 196, ym, PX - 6, ym, "s", arrow=True)
            cells(f, PX, y + 1, [(PW, city, "c")], h=24)
    # the set at the end, as a row of slots
    SY, SW = 248, 37
    sx = 320 - SET_CAP * SW / 2
    f.text(sx, SY - 10, f"the set after the {len(CUSTOMERS)} rows: {SET_CAP} slots, {len(SLOTS)} cities", "t", 11.5,
           None, 600)
    at = {s: c for c, s in SLOTS.items()}
    for k in range(SET_CAP):
        x = sx + k * SW
        if k in at:
            cells(f, x, SY, [(SW, at[k], "c")], h=26, size=8.5)
        else:
            f.rect(x, SY, SW, 26, "m f", 0)
        f.text(x + SW / 2, SY + 40, str(k), "tm" if k not in at else "t", 9.5, "middle", 600 if k in at else None, True)
    f.text(sx, SY + 64, "A city's slot is its hash's low bits. The second London hashes alike, finds slot 0 "
                        "holding an equal", "tm", 10.5)
    f.text(sx, SY + 80, "list, and is dropped; the rows come out in the order they were first seen.", "tm", 10.5)
    return f


FIGS = [
    ("08.04-step", step0804), ("08.04-functions", functions0804),
    ("08.05-groups", groups0805), ("08.05-pipeline", pipeline0805), ("08.05-distinct", distinct0805),
]
STEPPED = ["08.04-step", "08.05-groups"]


# ------------------------------------------------------------------ --check: the numbers against a run

def set_slot(text, cap):
    """The slot exec.c's set_hash and set_add pick for a list of one text value, in an empty set
    of cap slots: FNV-1a over the type tag (V_TEXT, from db.h's enum) and the text's bytes."""
    src = open(os.path.join(REPO, "tracks", "db", "src", "db.h")).read()
    tags = re.search(r"enum \{ (V_NULL[^}]*) \};", src)[1].replace(" ", "").split(",")
    h = 14695981039346656037
    for b in [tags.index("V_TEXT")] + list(text.encode()):
        h = ((h ^ b) * 1099511628211) % (1 << 64)
    return h & (cap - 1)


def check():
    d = tempfile.mkdtemp(prefix="figs08b-")
    s4, s5 = os.path.join(d, "shop4.db"), os.path.join(d, "shop5.db")

    def same(what, got, want):
        if got != want:
            raise SystemExit(f"{what}: the engine says\n  {got}\nthe figure says\n  {want}")
        print("ok", what)

    def parse(v):
        return None if v == "" else int(v) if v.lstrip("-").isdigit() else v

    def rows(path, sql, at):
        return [tuple(map(parse, l.split("|"))) for l in A.run_at(path, sql, at)]

    # 08.04
    A.run_at(s4, DATA_SQL, "08.04")
    same("08.04: orders, in the order the scan gives them", rows(s4, "SELECT * FROM orders;", "08.04"), ORDERS)
    same("08.04: EXPLAIN, the three aggregates", A.run_at(s4, "EXPLAIN " + STEP_SQL, "08.04"), STEP_TREE)
    same("08.04: the boxes are the Aggregate's aggregates", ", ".join(STEP_AGGS), STEP_TREE[0][len("Aggregate "):])
    got = [rows(s4, STEP_SQL[:-1] + f" WHERE id <= {o[0]};", "08.04")[0] for o in ORDERS]
    same("08.04: the state after each row (the same query over the rows so far)", got, STATES)
    same("08.04: the one row", rows(s4, STEP_SQL, "08.04"), [STEP_OUT])
    A.run_at(s4, EMPTY_TABLE, "08.04")
    same("08.04: the functions over no rows", A.run_at(s4, EMPTY_SQL, "08.04"), [EMPTY_OUT])
    typeof = EMPTY_SQL.replace("count(*), ", "typeof(count(*)), ")
    for fn in ("count(x)", "sum(x)", "total(x)", "avg(x)", "min(x)", "max(x)"):
        typeof = typeof.replace(f" {fn}", f" typeof({fn})")
    same("08.04: ... and the type of each", A.run_at(s4, typeof, "08.04"), ["|".join(EMPTY_TYPES)])
    same("08.04: the figure's function list", [fn[0] for fn in FUNCS],
         ["count(*)", "count(x)", "sum(x)", "total(x)", "avg(x)", "min(x)", "max(x)"])

    # 08.05
    A.run_at(s5, DATA_SQL, "08.05")
    same("08.05: EXPLAIN, GROUP BY customer_id", A.run_at(s5, "EXPLAIN " + GROUP_SQL, "08.05"), GROUP_TREE)
    same("08.05: the rows the Sort hands up", rows(s5, "SELECT * FROM orders ORDER BY customer_id;", "08.05"), SORTED)
    same("08.05: the groups", rows(s5, GROUP_SQL, "08.05"), GROUPS)
    hand, done = [], []
    for k in range(1, len(SORTED) + 1):
        ids = ", ".join(str(r[0]) for r in SORTED[:k])
        got = rows(s5, GROUP_SQL[:-len(" GROUP BY customer_id;")] + f" WHERE id IN ({ids}) GROUP BY customer_id;",
                   "08.05")
        hand.append(got[-1])
        done.append(len(got) - 1)
        same(f"08.05: the groups done after {k} rows are the first of the groups", got[:-1], GROUPS[:len(got) - 1])
    same("08.05: the group in hand after each row", hand, HAND)
    same("08.05: groups done after each row", done, DONE)

    same("08.05: EXPLAIN, the pipeline", A.run_at(s5, "EXPLAIN " + PIPE_SQL, "08.05"), PIPE_TREE)
    same("08.05: the pipeline's operators", sorted(PIPE_ROWS), sorted(l.strip() for l in PIPE_TREE))
    got = {}
    for name, sql in PIPE_COUNTS.items():
        out = A.run_at(s5, sql, "08.05")
        got[name] = int(out[0]) if sql.startswith("SELECT count(*)") else len(out)
    same("08.05: rows each operator hands up", got, PIPE_ROWS)
    same("08.05: the Aggregate's rows, in the Sort's order", rows(s5, AGG_ROWS_SQL, "08.05"), AGG_ROWS)
    same("08.05: the pipeline's result", rows(s5, PIPE_SQL, "08.05"), PIPE_OUT)

    same("08.05: EXPLAIN, DISTINCT", A.run_at(s5, "EXPLAIN " + DIST_SQL, "08.05"), DIST_TREE)
    same("08.05: the cities the scan gives", [r[0] for r in rows(s5, "SELECT city FROM customers;", "08.05")],
         [c[2] for c in CUSTOMERS])
    same("08.05: DISTINCT city", A.run_at(s5, DIST_SQL, "08.05"), DIST_OUT)
    exec_c = open(os.path.join(REPO, "tracks", "db", "src", "exec.c")).read()
    same("08.05: an empty set's slots (SET_MIN)", int(re.search(r"#define SET_MIN (\d+)", exec_c)[1]), SET_CAP)
    same("08.05: each city's slot", {c: set_slot(c, SET_CAP) for c in DIST_OUT}, SLOTS)
    same("08.05: no two cities share a slot", len(set(SLOTS.values())), len(SLOTS))


def main():
    if sys.argv[1:] == ["--check"]:
        return check()
    figlib.LESSONS = os.path.join(REPO, "tracks", "db", "lessons")
    for name, fn in FIGS:
        print(figlib.write(MOD, name, fn()))
    for name in STEPPED:
        with open(os.path.join(figlib.LESSONS, MOD, "figures", name + ".svg")) as fh:
            print(name + ":", steps.check(fh.read()), "steps")


if __name__ == "__main__":
    main()
