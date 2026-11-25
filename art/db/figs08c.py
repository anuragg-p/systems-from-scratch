"""Figures for db module 08, More SQL: lessons 08.06 and 08.07.

    python3 art/db/figs08c.py                 writes tracks/db/lessons/08-more-sql/figures/08.0[67]-*.svg
    python3 art/db/figs08c.py --check         runs the statements below through the engine at each figure's
                                              lesson (./learn run db --at 08.06, 08.07) and checks every
                                              value, answer, byte, page number and error text the figures draw
    python3 art/db/figs08c.py --dump FILE N   prints the cells of page N of a database file

The look is 08.01's (figs08a.py, whose helpers these use): customers' values in the neutral tone,
orders' values in the accent tone; NULL an empty dashed cell with the word NULL in muted text.

08.06, the engine at 08.06 (`./learn run db --at 08.06 -- shop.db "<sql>"`) on the module's data set,
shop.db (DATA_SQL, the same as figs08a's). What no query prints (how often a subquery runs, the set it
keeps) was read from a traced run: a copy of the project (./learn files db --at 08.06 DIR) with fprintfs
added to exec.c: in run_subquery, when a run starts (the outer row's rowid, e->correlated) and ends (the
answer; for IN run once, nset, has_null and the kept values in order); in eval_subquery, where a kept
answer is used instead of a run, and after set_lookup (x and its 1, 0 or -1); in filter_next, each row a
Filter tests while db->nouter > 0, with its value_truth.
  08.06-kinds: KIND_SCALAR prints Brook, and its subquery alone prints 2; KIND_IN prints Ada, Brook,
    Chen; the traced copy printed its set, built once: nset 5 has_null 1: 1 1 2 3 3. KIND_EXISTS prints
    Ada, Brook, Chen; EXISTS as a result column (EXISTS_SQL) prints 1, 1, 1, 0; NOT EXISTS prints Dee.
  08.06-outer: OUTER_SQL prints Ada|2 Brook|1 Chen|2 Dee|0. Traced: 4 runs, on outer rowids 1, 2, 3, 4,
    each correlated; on rowid 1 the Filter (o.customer_id = c.id) tested orders 10-15 and gave 1 0 1 0 0
    -1, and the run's answer was 2 (then 1, 2, 0). ONCE_SQL prints 2 for every customer; traced: one run,
    on outer rowid 1, not correlated, its Filter (id = 13) tested order 13 only (EXPLAIN of the subquery
    alone: Filter (id = 13) over Rowid lookup orders rowid = ?), answer 2; for rowids 2, 3, 4 the kept
    answer, no run. --check: the answers; Ada's run as SELECT o.id, o.customer_id, o.customer_id = 1 FROM
    orders o and its count; the count's subquery alone is "no such column: c.id" (it names a column
    outside), order 13's alone runs (it names none).
  08.06-notin: NOTIN_VALUES_SQL prints 1|1|0 2|1|0 3|1|0 4|| (IN, NOT IN; NULL prints as nothing) and
    NOTIN_SQL nothing at all; with WHERE customer_id IS NOT NULL in the subquery it prints Dee. The scan
    gives customer_id 1 3 1 2 3 NULL (orders 10-15). Traced: the set built once, on outer rowid 1: kept
    sorted (qsort with value_compare), duplicates kept, the NULL not stored but noted in has_null; then
    set_lookup gave 1, 1, 1 for ids 1, 2, 3 and -1 for 4. --check: the kept values as the non-NULL
    customer_ids in ORDER BY order (the same comparison), has_null as a NULL among them.

08.07, the engine at 08.07 (`./learn run db --at 08.07 -- <file> "<sql>"`), on the files lesson 08.07
makes, with its statements in its order, dumped with --dump (the page header, the cell pointer array,
each cell's bytes), checked against sqlite3 3.54.1 (/opt/homebrew/opt/sqlite/bin/sqlite3):
  users.db  USERS_SQL; SELECT type, name, tbl_name, rootpage, typeof(sql), sql FROM sqlite_schema:
              table|users|users|2|text|CREATE TABLE users(id INTEGER PRIMARY KEY, email TEXT UNIQUE, name TEXT)
              index|sqlite_autoindex_users_1|users|3|null|
            page 1, cell 1 (the index's row, 43 bytes): SCHEMA_ROW below.
            Then TWO_SQL (Ada and Brook in one statement): page 3 (index leaf, 2 cells):
              12 03 2b 09 'ada@example.com' (rowid 1 is serial type 9: no byte), and Brook's, ENTRY below:
              15 03 2f 01 'brook@example.com' 02, cell 1, 22 bytes. Then CHEN_SQL: Error: UNIQUE constraint
              failed: users.email, and the file is byte for byte what it was (cmp); sqlite3 refuses the same
              row in the same words and leaves it as it was too.
  plain.db  the lesson's: PLAIN_SQL, then TWO_SQL. `cmp users.db plain.db 4096 4096` finds them the same
            from page 2 on (3 pages each): page 3 is byte for byte users.db's page 3. sqlite3 3.54.1
            writing the same statements makes files that are the same as these from page 2 on.
  08.07-check follows The idea's paragraph: with Ada in row 1 (fig.db: USERS_SQL, then Ada alone),
    inserting Brook gives DB_STATS=1 "pages written 3", and cmp -l against the file before shows bytes
    changed on pages 1 (the header: offsets 24-27, the change counter, and 92-95), 2 and 3; then CHEN_SQL
    gives the error, "pages written 0", and cmp finds the file unchanged. From page 2 on that file is
    the lesson's users.db.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import figlib  # noqa: E402
from figlib import tw  # noqa: E402
import figs08a as A  # noqa: E402  the module's look, its data and run_at
import figs08b as B  # noqa: E402  row_cells, heads

REPO = A.REPO
figlib.LESSONS = os.path.join(REPO, "tracks", "db", "lessons")
MOD = A.MOD
Fig = A.Fig
SQLITE3 = "/opt/homebrew/opt/sqlite/bin/sqlite3"


def cells(f, x, y, items, h=22, size=11):
    """items: (width, text, cls). Cells left to right with no gap; cls "null" is a NULL:
    an empty dashed cell with the word in muted text. Returns the x after the last cell."""
    for w, text, cls in items:
        if cls == "null":
            f.rect(x, y, w, h, "m f", 0, dash=True)
            f.text(x + w / 2, y + h / 2 + size * 0.36, "NULL", "tm", size - 1, "middle", None, True)
        else:
            f.rect(x, y, w, h, cls, 0)
            tcls = "ta" if cls.startswith("a") else ("tm" if cls.startswith("m") else "t")
            f.text(x + w / 2, y + h / 2 + size * 0.36, text, tcls, size, "middle", None, True)
        x += w
    return x


def byte_row(f, x, y, items, h=30, subs=True):
    """items: (width, text, sub, cls), as in figs05: boxes left to right, a label under each
    (above each when subs is "above", none when False). Returns the x of each box's left edge,
    and the x after the last."""
    xs = []
    for w, text, sub, cls in items:
        f.rect(x, y, w, h, cls, 0)
        tcls = "ta" if cls.startswith("a") else "t"
        size, dy = (11.5, 4) if w >= 24 else (10, 3.5)  # a narrow box: a smaller hex pair
        f.text(x + w / 2, y + h / 2 + dy, text, tcls, size, "middle", None, True)
        if sub and subs:
            f.text(x + w / 2, y - 8 if subs == "above" else y + h + 14, sub, "tm", 10.5, "middle")
        xs.append(x)
        x += w
    xs.append(x)
    return xs


def step(f, x, y, n, label, cls="t"):
    """A numbered step heading: a small circle with n, then the label."""
    f.circle(x + 9, y - 4, 9, "a af" if cls == "ta" else "s fs")
    f.text(x + 9, y, str(n), "t", 10.5, "middle", 700)
    f.text(x + 24, y, label, cls, 11.5, None, 600)


# ------------------------------------------------------------------ 08.06, the engine at 08.06

DATA_SQL = (
    "CREATE TABLE customers(id INTEGER PRIMARY KEY, name TEXT, city TEXT); "
    "CREATE TABLE orders(id INTEGER PRIMARY KEY, customer_id INTEGER, total INTEGER); "
    "INSERT INTO customers VALUES (1,'Ada','London'),(2,'Brook','Paris'),(3,'Chen','London'),(4,'Dee','Oslo'); "
    "INSERT INTO orders VALUES (10,1,30),(11,3,15),(12,1,50),(13,2,20),(14,3,5),(15,NULL,40);")
CUSTOMERS, ORDERS = A.CUSTOMERS, A.ORDERS

# 08.06-kinds
SCALAR_SUB = "SELECT customer_id FROM orders WHERE id = 13"
KIND_SCALAR = f"SELECT name FROM customers WHERE id = ({SCALAR_SUB});"
SCALAR_BACK = 2
SCALAR_OUT = ["Brook"]
KIND_IN = "SELECT name FROM customers WHERE id IN (SELECT customer_id FROM orders);"
IN_OUT = ["Ada", "Brook", "Chen"]
KEPT = [1, 1, 2, 3, 3]                # the set kept on the node, as run_subquery sorts it
HAS_NULL = 1                          # ... and its has_null: order 15's customer_id
EXISTS_SUB = "SELECT 1 FROM orders o WHERE o.customer_id = c.id"
KIND_EXISTS = f"SELECT name FROM customers c WHERE EXISTS ({EXISTS_SUB});"
EXISTS_SQL = f"SELECT name, EXISTS ({EXISTS_SUB}) FROM customers c;"
EXISTS_BACK = [("Ada", 1), ("Brook", 1), ("Chen", 1), ("Dee", 0)]
EXISTS_OUT = ["Ada", "Brook", "Chen"]
NOT_EXISTS_OUT = ["Dee"]

# 08.06-outer
COUNT_SUB = "SELECT count(*) FROM orders o WHERE o.customer_id = c.id"
OUTER_SQL = f"SELECT name, ({COUNT_SUB}) FROM customers c;"
OUTER_OUT = [("Ada", 2), ("Brook", 1), ("Chen", 2), ("Dee", 0)]
# Ada's run (c.id = 1): each order the Filter tests, (o.id, o.customer_id, the test: 1, 0, None NULL)
ADA_TESTS = [(10, 1, 1), (11, 3, 0), (12, 1, 1), (13, 2, 0), (14, 3, 0), (15, None, None)]
ONCE_SQL = f"SELECT name, ({SCALAR_SUB}) FROM customers c;"
ONCE_OUT = [("Ada", 2), ("Brook", 2), ("Chen", 2), ("Dee", 2)]
ONCE_PLAN = ["Filter (id = 13)", "  Rowid lookup orders rowid = ?"]

# 08.06-notin
IN_SUB = "SELECT customer_id FROM orders"
NOTIN_SQL = f"SELECT name FROM customers WHERE id NOT IN ({IN_SUB});"
NOTIN_VALUES_SQL = f"SELECT id, id IN ({IN_SUB}), id NOT IN ({IN_SUB}) FROM customers;"
NOTIN_VALUES = [(1, 1, 0), (2, 1, 0), (3, 1, 0), (4, None, None)]
SCAN_CIDS = [1, 3, 1, 2, 3, None]     # customer_id as the subquery's scan reads it, orders 10-15
NOTIN_FIX_SQL = f"SELECT name FROM customers WHERE id NOT IN ({IN_SUB} WHERE customer_id IS NOT NULL);"
NOTIN_FIX_OUT = ["Dee"]


def code(f, x, y, parts, size=10.5):
    """One line of monospaced text in pieces: parts are (text, class) or (text, class, weight).
    The page collapses runs of spaces and drops them at the ends of a <text>, so each run of
    words with single spaces is drawn at its own x. Returns the x after the line."""
    cw = tw(" ", size, True)
    for p in parts:
        for m in re.finditer(r"\S+(?: \S+)*", p[0]):
            f.text(x + m.start() * cw, y, m.group(), p[1], size, None, p[2] if len(p) > 2 else None, True)
        x += len(p[0]) * cw
    return x


def kinds0806():
    f = Fig("f0806a", "Three kinds of subquery: one value, a set, a yes or no; what each hands back, and the answer", 400)
    QX, BX, OX = 36, 318, 508                 # the query, what it hands back, the answer
    f.text(QX, 22, "the query, its subquery in the accent", "tm", 10.5)
    f.text(BX, 22, "the subquery hands back", "tm", 10.5)
    f.text(OX, 22, "the answer", "tm", 10.5)
    BH, GAP, Y0 = 100, 10, 34
    ind = tw("WHERE id = ", 10.5, True)
    bands = [
        ("(SELECT ...): one value", [
            [("SELECT name FROM customers", "tm")],
            [("WHERE id = ", "tm"), ("(SELECT customer_id", "ta")],
            (ind, [("FROM orders WHERE id = 13)", "ta"), (";", "tm")])], SCALAR_OUT),
        ("x IN (SELECT ...): is x in a set?", [
            [("SELECT name FROM customers", "tm")],
            [("WHERE id IN ", "tm"), ("(SELECT customer_id", "ta")],
            (tw("WHERE id IN ", 10.5, True), [("FROM orders)", "ta"), (";", "tm")])], IN_OUT),
        ("EXISTS (SELECT ...): is there a row?", [
            [("SELECT name FROM customers c", "tm")],
            [("WHERE EXISTS ", "tm"), ("(SELECT 1 FROM orders o", "ta")],
            (tw("WHERE EXISTS ", 10.5, True), [("WHERE o.customer_id = ", "ta"), ("c.id", "t", 700),
                                               (")", "ta"), (";", "tm")])], EXISTS_OUT),
    ]
    for k, (title, lines, out) in enumerate(bands):
        y = Y0 + k * (BH + GAP)
        f.rect(24, y, 592, BH, "s f", 8)
        f.text(QX, y + 22, title, "t", 11.5, None, 600)
        for j, line in enumerate(lines):
            dx, parts = line if isinstance(line, tuple) else (0, line)
            code(f, QX + dx, y + 44 + 15 * j, parts)
        # the answer: the customers that come out
        for j, name in enumerate(out):
            oy = y + (BH - 22 * len(out)) / 2 + 22 * j
            A.cells(f, OX, oy, [(64, name, "c")], h=22)
        # what the subquery hands back
        if k == 0:
            A.cells(f, BX, y + 14, [(30, SCALAR_BACK, "o")], h=24)
            f.text(BX + 40, y + 30, "order 13's customer_id", "tm", 10.5)
            notes = ["its first row's value", "(NULL if it has no row)"]
        elif k == 1:
            x = A.cells(f, BX, y + 14, [(22, v, "o") for v in KEPT], h=24)
            if HAS_NULL:
                A.cells(f, x + 8, y + 14, [(40, None, "o")], h=24)
            notes = ["every customer_id, sorted,", "and the NULL noted apart"]
        else:
            for j, (name, v) in enumerate(EXISTS_BACK):
                A.cells(f, BX + (j % 2) * 84, y + 8 + (j // 2) * 24, [(50, name, "c"), (24, v, "o")], h=22)
            notes = ["1 if it finds a row, else 0;", "again for every customer"]
        for j, s in enumerate(notes):
            f.text(BX, y + 70 + 15 * j, s, "tm", 10.5)
    yb = Y0 + 3 * (BH + GAP) + 18
    f.text(24, yb, f"NOT EXISTS with the same subquery turns each 1 and 0 over: it gives {', '.join(NOT_EXISTS_OUT)}.",
           "tm", 10.5)
    return f


def outer0806():
    f = Fig("f0806b", "A correlated subquery runs under each row of the query outside; one that names nothing outside runs once",
            518)
    RX = 412                                  # the right panel: the subquery that runs once
    f.line(400, 10, 400, 456, "m")

    # ---- left: the count, correlated
    f.text(24, 20, "it names c.id, outside: it runs for every row", "t", 11.5, None, 600)
    code(f, 24, 38, [("SELECT name, ", "tm"), ("(SELECT count(*) FROM orders o", "ta")], 10)
    code(f, 24 + tw("SELECT name, ", 10, True), 52,
         [("WHERE o.customer_id = ", "ta"), ("c.id", "t", 700), (")", "ta"), (" FROM customers c;", "tm")], 10)
    CX, CW = 40, [28, 50, 62]                 # the outer row: id, name, city
    PX, PW = 300, [50, 36]                    # the result row: name, the subquery's answer
    YR = 94
    cid, cname, ccity = CUSTOMERS[0]
    f.text(CX, YR - 8, f"customers c: row 1 of {len(CUSTOMERS)}, stopped", "t", 11, None, 600)
    f.text(PX, YR - 8, "its result row", "tm", 10.5)
    A.cells(f, CX, YR, [(CW[0], cid, "c"), (CW[1], cname, "c"), (CW[2], ccity, "c")], h=24)
    A.ring(f, CX, YR, sum(CW), 24)
    f.line(CX + sum(CW) + 8, YR + 12, PX - 6, YR + 12, "s", arrow=True)
    A.cells(f, PX, YR, [(PW[0], OUTER_OUT[0][0], "c"), (PW[1], OUTER_OUT[0][1], "o")], h=24)
    # the query inside, under that row
    IX, IY, IB = 28, 156, 354                 # its box: left, top, bottom
    f.rect(IX, IY, 392 - IX, IB - IY, "s fs", 8)
    idx = CX + CW[0] / 2                      # c.id's cell, and the tag that reads it
    f.line(idx, IY - 12, idx, YR + 27, "s", arrow=True)
    f.text(idx + 10, YR + 42, "c.id, read from the row above", "tm", 10.5)
    A.cells(f, IX + 8, IY - 10, [(64, "c.id = 1", "c")], h=20, size=10.5)
    f.text(IX + 84, IY + 18, f"the query inside, run 1 of {len(CUSTOMERS)}", "t", 11.5, None, 600)
    OX, OW = 44, [34, 84]                     # orders o: id, customer_id
    TX = 176                                  # the test on each
    AX, AW = 316, 68                          # the Aggregate
    RY, RH = IY + 50, 22
    B.heads(f, OX, RY - 8, OW, ["o.id", "customer_id"])
    f.text(TX, RY - 8, "o.customer_id = c.id", "tm", 10, None, None, True)
    word = {1: "true", 0: "false", None: "NULL"}
    for i, (oid, ocid, t) in enumerate(ADA_TESTS):
        y = RY + i * RH
        B.row_cells(f, OX, y, OW, (oid, ocid), "o", h=RH, size=10.5, muted=t != 1)
        code(f, TX, y + 15, [(A.val(ocid), "ta" if t == 1 else "tm"), (" = ", "tm"), (str(cid), "t")], 10)
        f.text(TX + 60, y + 15, word[t], "t" if t == 1 else "tm", 10.5, None, 600 if t == 1 else None)
        if t == 1:
            f.line(TX + 96, y + RH / 2, AX - 4, y + RH / 2, "a", arrow=True)
    n_rows = len(ADA_TESTS) * RH
    f.rect(AX, RY, AW, n_rows, "a af", 6)
    f.text(AX + AW / 2, RY + 20, "Aggregate", "tm", 10, "middle")
    f.text(AX + AW / 2, RY + 36, "count(*)", "ta", 10.5, "middle", None, True)
    f.text(AX + AW / 2, RY + n_rows / 2 + 30, str(OUTER_OUT[0][1]), "ta", 24, "middle", 700)
    # its answer goes up into the result row
    ax = PX + PW[0] + PW[1] / 2
    f.line(ax, RY - 4, ax, YR + 27, "a", arrow=True)
    f.text(ax - 8, YR + 42, f"its answer, {OUTER_OUT[0][1]}", "ta", 10.5, "end")
    # the rows still to come
    yl = IB + 22
    f.text(24, yl, "rows 2, 3 and 4: the query inside runs again for each", "tm", 10.5)
    for i, ((cid2, name2, city2), (_, n2)) in enumerate(zip(CUSTOMERS[1:], OUTER_OUT[1:])):
        y = yl + 10 + i * 24
        B.row_cells(f, CX, y, CW, (cid2, name2, city2), "c", h=20, size=10.5, muted=True)
        f.text(CX + sum(CW) + 12, y + 14, f"run {i + 2}, c.id = {cid2}", "tm", 10, None, None, True)
        B.row_cells(f, PX, y, PW, (name2, n2), "c", h=20, size=10.5, muted=True)

    # ---- right: order 13's customer_id, not correlated, in the muted tone
    f.text(RX, 20, "it names nothing outside: it runs once", "tm", 11.5, None, 600)
    code(f, RX, 38, [("SELECT name, (SELECT customer_id", "tm")], 10)
    sx = RX + tw("SELECT name, (", 10, True)
    code(f, sx, 52, [("FROM orders", "tm")], 10)
    code(f, sx, 66, [("WHERE id = 13)", "tm")], 10)
    code(f, RX, 80, [("FROM customers c;", "tm")], 10)
    QW = [50, 30]
    B.row_cells(f, RX, YR, QW, ONCE_OUT[0], "c", h=24, size=10.5, muted=True)
    f.text(RX + sum(QW) + 10, YR + 16, "row 1: the run", "tm", 10.5)
    f.rect(RX, IY, 616 - RX, 104, "m f", 8)
    f.text(RX + 12, IY + 18, "the query inside, its one run", "tm", 11, None, 600)
    f.text(RX + 12, IY + 36, "a rowid lookup of order 13", "tm", 10.5)
    B.row_cells(f, RX + 12, IY + 46, OW, (13, ONCE_OUT[0][1]), "o", h=20, size=10.5, muted=True)
    f.text(RX + 12, IY + 90, f"its answer, {ONCE_OUT[0][1]}, kept on the node", "tm", 10.5, None, 600)
    kx = RX + QW[0] + QW[1] / 2
    f.line(kx, IY - 2, kx, YR + 27, "m", arrow=True)
    f.text(RX, yl, "rows 2, 3 and 4 get the kept 2", "tm", 10.5)
    for i, row in enumerate(ONCE_OUT[1:]):
        y = yl + 10 + i * 24
        B.row_cells(f, RX, y, QW, row, "c", h=20, size=10.5, muted=True)
        f.text(RX + sum(QW) + 10, y + 14, "no run", "tm", 10.5)

    f.line(24, 470, 616, 470, "m")
    answers = ", ".join(str(n) for _, n in OUTER_OUT[:-1]) + f" and {OUTER_OUT[-1][1]}"
    f.text(24, 490, f"The count names c.id: {len(CUSTOMERS)} customers, {len(CUSTOMERS)} runs, answers {answers}.",
           "t", 11)
    f.text(24, 507, "Order 13's query names nothing outside: it runs the first time it is needed, and its answer "
                    "is kept.", "tm", 10.5)
    return f


def notin0806():
    f = Fig("f0806c", "NOT IN against a set that holds a NULL: no customer's answer is true, so no row comes out", 370)
    code(f, 24, 22, [("SELECT name FROM customers WHERE id NOT IN ", "tm"), (f"({IN_SUB})", "ta"), (";", "tm")])
    f.text(616, 22, "prints nothing", "t", 11.5, "end", 600)
    # the set, built once
    W = 28
    f.text(24, 52, "customer_id, as the subquery reads orders", "t", 11, None, 600)
    scan = [(W if v is not None else 40, v, "o") for v in SCAN_CIDS]
    A.cells(f, 24, 60, scan, h=24)
    f.text(24, 100, f"orders {ORDERS[0][0]} to {ORDERS[-1][0]}, in rowid order", "tm", 10.5)
    sx = 300
    se = 24 + sum(w for w, _, _ in scan)
    f.line(se + 10, 72, sx - 10, 72, "a", arrow=True)
    f.text((se + sx) / 2, 64, "run once", "tm", 10.5, "middle")
    f.text(sx, 52, "the set kept on the node", "t", 11, None, 600)
    x = A.cells(f, sx, 60, [(W, v, "o") for v in KEPT], h=24)
    f.text(sx, 100, "sorted, duplicates kept", "tm", 10.5)
    if HAS_NULL:
        A.cells(f, x + 14, 60, [(40, None, "o")], h=24)
        f.text(x + 62, 77, f"has_null = {HAS_NULL}", "t", 10.5, None, None, True)
        f.text(x + 14, 100, "the NULL: a flag, not a value", "tm", 10.5)
    f.line(24, 116, 616, 116, "m")
    # each customer against it
    CX, CW = 24, [26, 56]
    TX, IX, NX, VX = 140, 372, 420, 484
    HY, Y0, RH = 138, 150, 36
    f.text(CX, HY, "customers", "t", 11, None, 600)
    f.text(TX, HY, "is id in the set?", "t", 11, None, 600)
    f.text(IX + 20, HY, "IN", "t", 10.5, "middle", 600, True)
    f.text(NX + 26, HY, "NOT IN", "t", 10.5, "middle", 600, True)
    f.text(VX, HY, "does WHERE keep it?", "t", 11, None, 600)
    for i, ((cid, name, _), (vid, v_in, v_not)) in enumerate(zip(CUSTOMERS, NOTIN_VALUES)):
        y = Y0 + i * RH
        ym = y + 12
        A.cells(f, CX, y, [(CW[0], cid, "c"), (CW[1], name, "c")], h=24)
        f.line(CX + sum(CW) + 6, ym, TX - 8, ym, "s", arrow=True)
        if v_in == 1:
            f.text(TX, ym - 2, f"{cid}: found", "t", 11, None, 600)
            f.text(TX, ym + 13, f"the bisection meets a {cid}", "tm", 10.5)
        else:
            f.text(TX, ym - 2, f"{cid}: not found", "t", 11, None, 600)
            f.text(TX, ym + 13, "but the NULL might be a " + str(cid) + ": unknown", "tm", 10.5)
        A.cells(f, IX, y, [(40, v_in, "c")], h=24)
        A.cells(f, NX, y, [(52, v_not, "c")], h=24)
        f.text(VX, ym - 2, "no", "t", 11, None, 600)
        f.text(VX, ym + 13, "0 is false" if v_not == 0 else "NULL is not true", "tm", 10.5)
    yb = Y0 + len(CUSTOMERS) * RH + 4
    f.line(24, yb, 616, yb, "m")
    f.text(24, yb + 20, "No row survives: x NOT IN a set that holds a NULL is never true.", "t", 11)
    code(f, 24, yb + 38, [("SELECT id, id IN (...), id NOT IN (...) FROM customers;", "tm"),
                          ("   " + "  ".join("|".join(A.val(v) if v is not None else "" for v in r)
                                             for r in NOTIN_VALUES), "t")], 10)
    f.text(24, yb + 56, "With WHERE customer_id IS NOT NULL inside the subquery the set has no NULL, and the query "
                        f"gives {', '.join(NOTIN_FIX_OUT)}.", "tm", 10.5)
    return f


# ------------------------------------------------------------------ 08.07, the engine at 08.07

USERS_SQL = "CREATE TABLE users(id INTEGER PRIMARY KEY, email TEXT UNIQUE, name TEXT)"
PLAIN_SQL = ("CREATE TABLE users(id INTEGER PRIMARY KEY, email TEXT, name TEXT); "
             "CREATE INDEX users_email ON users(email)")
ADA, BROOK, CHEN = (1, "ada@example.com", "Ada"), (2, "brook@example.com", "Brook"), (3, "ada@example.com", "Chen")


def ins(*rows):
    return "INSERT INTO users VALUES " + ", ".join(f"({i}, '{e}', '{n}')" for i, e, n in rows)


TWO_SQL = ins(ADA, BROOK)                     # the lesson's Run it: both in one statement
CHEN_SQL = ins(CHEN)
ERROR = "Error: UNIQUE constraint failed: users.email"
SCHEMA = [("table", "users", "users", 2, "text", USERS_SQL), ("index", "sqlite_autoindex_users_1", "users", 3, "null", "")]
# page 1, cell 1: sqlite_schema's row for the index
SCHEMA_ROW = bytes([0x29, 0x02, 0x06, 0x17, 0x3d, 0x17, 0x01, 0x00]) + b"indexsqlite_autoindex_users_1users\x03"
# The index leaf (page 3) after Ada, then after Brook: (email, rowid), in key order.
ENTRIES = [(ADA[1], ADA[0]), (BROOK[1], BROOK[0])]
BROOK_PAGES = [1, 2, 3]                       # pages Brook's INSERT changes (cmp -l), DB_STATS: written 3
# Brook's entry in either file's index: page 3, cell 1
ENTRY_CELL = 1
ENTRY = bytes([0x15, 0x03, 0x2f, 0x01]) + BROOK[1].encode() + bytes([BROOK[0]])


def index_leaf(f, x, y, entries, hot=None, h=None):
    """users.db's index leaf, page 3, as a box of (email, rowid) entries. hot: the index of an
    entry to ring. Returns (the y of each entry's top, the box's bottom)."""
    h = h or 40 + 24 * len(entries)
    f.rect(x, y, 266, h, "a af", 6)
    f.text(x + 12, y + 18, "page 3: sqlite_autoindex_users_1", "ta", 10.5, None, 600, True)
    tops = []
    for i, (email, rid) in enumerate(entries):
        ey = y + 28 + 24 * i
        cells(f, x + 12, ey, [(130, email, "a f"), (26, str(rid), "a f")], h=20, size=11)
        if i == hot:
            f.rect(x + 8, ey - 4, 164, 28, "a", 4)
        tops.append(ey)
    return tops, y + h


def check0807():
    f = Fig("f0807a", "Two INSERTs into users: a lookup in the unique index comes before any write", 478)
    R = 316                                   # the right column: what is written

    # a new email
    f.text(24, 22, ins(BROOK) + ";", "t", 11.5, None, 600, True)
    f.text(616, 22, f"{ADA[2]} is in row {ADA[0]}: a new email", "tm", 10.5, "end")
    step(f, 24, 50, 1, f"look up '{BROOK[1]}'", "ta")
    step(f, R, 50, 2, "nothing equal: write both B-trees")
    tops, bot = index_leaf(f, 24, 62, ENTRIES[:1], h=80)
    gap = tops[-1] + 30
    f.line(36, gap, 192, gap, "a", dash=True)
    f.line(278, gap, 200, gap, "a", arrow=True)
    f.text(240, gap - 6, "the seek", "ta", 10.5, "middle")
    f.text(24, bot + 18, f"past {ADA[1]}: no equal entry", "tm", 10.5)
    # the two writes
    f.rect(R, 62, 616 - R, 52, "s f", 6)
    f.text(R + 12, 80, "page 2: table users", "t", 10.5, None, 600, True)
    f.text(R + 12, 102, "+ row", "t", 11)
    cells(f, R + 56, 88, [(26, str(BROOK[0]), "s f"), (130, BROOK[1], "s f"), (50, BROOK[2], "s f")], h=20)
    f.rect(R, 124, 616 - R, 52, "a af", 6)
    f.text(R + 12, 142, "page 3: sqlite_autoindex_users_1", "ta", 10.5, None, 600, True)
    f.text(R + 12, 164, "+ entry", "ta", 11)
    cells(f, R + 70, 150, [(130, BROOK[1], "a f"), (26, str(BROOK[0]), "a f")], h=20)
    f.path(f"M292 102 C 304 102, 300 88, {R - 3} 88", "s", arrow=True)
    f.path(f"M292 102 C 304 102, 300 150, {R - 3} 150", "a", arrow=True)
    f.text(R, 196, f"the row, then its entry; {len(BROOK_PAGES)} pages written:", "tm", 10.5)
    f.text(R, 211, "page 1's header, page 2 and page 3", "tm", 10.5)

    f.line(24, 222, 616, 222, "m")

    # an email already there
    y0 = 222
    f.text(24, y0 + 26, CHEN_SQL + ";", "t", 11.5, None, 600, True)
    f.text(616, y0 + 26, "an email already there", "tm", 11, "end")
    step(f, 24, y0 + 54, 1, f"look up '{CHEN[1]}'", "ta")
    step(f, R, y0 + 54, 2, "an equal entry: write nothing")
    tops, bot = index_leaf(f, 24, y0 + 66, ENTRIES, hot=0)
    hit = tops[0] + 10
    f.line(278, hit, 200, hit, "a", arrow=True)
    f.text(240, hit - 6, "the seek", "ta", 10.5, "middle")
    f.text(24, bot + 18, f"it lands on ('{ADA[1]}', {ADA[0]}):", "tm", 10.5)
    f.text(24, bot + 33, f"rowid {ADA[0]}, not this row's {CHEN[0]}", "tm", 10.5)
    f.rect(R, y0 + 66, 616 - R, 36, "m f", 6, dash=True)
    f.text(R + 12, y0 + 88, "page 2: table users", "tm", 10.5, None, 600, True)
    f.text(604, y0 + 88, "unchanged", "tm", 10.5, "end")
    f.rect(R, y0 + 112, 616 - R, 36, "m f", 6, dash=True)
    f.text(R + 12, y0 + 134, "page 3: the index", "tm", 10.5, None, 600, True)
    f.text(604, y0 + 134, "unchanged", "tm", 10.5, "end")
    f.rect(R, y0 + 162, 616 - R, 32, "s fs", 6)
    f.text((R + 616) / 2, y0 + 182, ERROR, "t", 10.5, "middle", None, True)
    f.text(R, y0 + 214, "0 pages written; the file is unchanged (cmp)", "tm", 10.5)

    f.line(24, 452, 616, 452, "m")
    f.text(24, 470, "Before either lookup the table is asked whether the rowid is free (04.01's check): "
                    f"{BROOK[0]} and {CHEN[0]} are.", "tm", 10.5)
    return f


def schema0807():
    f = Fig("f0807b", "sqlite_schema for users: the table's row, and its automatic index's row with no sql", 378)
    f.text(24, 22, "page 1 of users.db: the two rows of sqlite_schema, as ./db wrote them (sqlite3 reads the same)", "tm", 11)
    sql = ["CREATE TABLE users(id INTEGER", "PRIMARY KEY, email TEXT", "UNIQUE, name TEXT)"]
    cards = [(24, "row 1", "table", "users", "2", "page 2: the table's B-tree", sql, "s"),
             (328, "row 2", "index", "sqlite_autoindex_users_1", "3", "page 3: the index's B-tree", None, "a")]
    for x, rid, typ, name, root, page, sqltext, tone in cards:
        f.rect(x, 36, 288, 204, "s f", 8)
        f.text(x + 12, 56, rid, "t", 11.5, None, 700)
        fields = [("type", typ), ("name", name), ("tbl_name", "users"), ("rootpage", root)]
        for i, (k, v) in enumerate(fields):
            y = 68 + 26 * i
            f.text(x + 12, y + 15, k, "tm", 10.5, None, None, True)
            if k == "rootpage":
                cells(f, x + 76, y, [(28, v, "a af")], h=20)
                f.line(x + 108, y + 10, x + 130, y + 10, "a", arrow=True)
                f.text(x + 136, y + 14, page, "ta" if tone == "a" else "t", 10.5)
            else:
                cells(f, x + 76, y, [(max(36, tw(v, 11, True) + 16), v, "s f")], h=20)
        y = 68 + 26 * 4
        f.text(x + 12, y + 15, "sql", "tm", 10.5, None, None, True)
        if sqltext:
            f.rect(x + 76, y, 200, 16 * len(sqltext) + 8, "s f", 0)
            for k, line in enumerate(sqltext):
                f.text(x + 84, y + 15 + 16 * k, line, "t", 10.5, None, None, True)
        else:
            cells(f, x + 76, y, [(60, "", "null")], h=20)
            f.text(x + 148, y + 15, "no CREATE text", "tm", 10.5)

    # the index row's record, from the dump of page 1
    f.text(24, 266, "row 2 as stored: its record header ends in serial type 00, a NULL, which takes no bytes", "tm", 11)
    xs = byte_row(f, 24, 276, [
        (34, "29", "size", "s f"), (34, "02", "rowid", "s f"), (34, "06", "hdr", "s fs"),
        (34, "17", "type", "s fs"), (34, "3d", "name", "s fs"), (34, "17", "tbl", "s fs"),
        (34, "01", "root", "s fs"), (34, "00", "sql", "a af"),
        (50, "index", "", "s f"), (184, "sqlite_autoindex_users_1", "", "s f"), (50, "users", "", "s f"),
        (32, "03", "", "a af"),
    ])
    f.text((xs[8] + xs[12]) / 2, 320, "the values: type, name, tbl_name, rootpage; nothing for sql", "tm", 10.5, "middle")
    f.line(24, 334, 616, 334, "m")
    f.text(24, 354, "id INTEGER PRIMARY KEY makes no index (it is the rowid), so email's UNIQUE is the table's index _1.", "t", 11)
    f.text(24, 371, "At every open the CREATE text is parsed again, its UNIQUE named _1 again, and that name finds this row.",
           "tm", 10.5)
    return f


def entry0807():
    f = Fig("f0807c", "An entry of the unique index and of an ordinary index on the same column: the same bytes", 292)
    key = BROOK[1]
    f.text(24, 22, f"{BROOK[2]}'s row, rowid {BROOK[0]}: its entry in each file's index, leaf page 3, cell {ENTRY_CELL}, "
                   f"{len(ENTRY)} bytes", "tm", 11)
    f.text(24, 40, "users.db: sqlite_autoindex_users_1, made for UNIQUE.   plain.db: users_email, from CREATE INDEX.",
           "tm", 10.5)
    hdr = ENTRY[:4]
    items = [(40, f"{hdr[0]:02x}", f"size {hdr[0]}", "s f"), (32, f"{hdr[1]:02x}", "hdr", "s fs"),
             (32, f"{hdr[2]:02x}", "email", "s fs"), (32, f"{hdr[3]:02x}", "rowid", "s fs")]
    items += [(20, f"{b:02x}", "", "a af") for b in key.encode()]
    items += [(40, f"{ENTRY[-1]:02x}", f"rowid {BROOK[0]}", "a af")]
    x0 = 616 - sum(w for w, _, _, _ in items)
    rows = [(70, "UNIQUE", "ta", "users.db"), (128, "ordinary", "t", "plain.db")]
    for k, (y, role, rcls, where) in enumerate(rows):
        f.text(24, y + 14, role, rcls, 12, None, 700)
        f.text(24, y + 30, where, "tm", 10.5, None, None, True)
        xs = byte_row(f, x0, y, items, subs="above" if k == 0 else False)
    f.text((xs[4] + xs[4 + len(key)]) / 2, 62, f"'{key}', {len(key)} bytes", "tm", 10.5, "middle")
    # the same bytes: an = under each box of the first row
    for i in range(len(items)):
        f.text((xs[i] + xs[i + 1]) / 2, 120, "=", "tm", 12, "middle", 600)
    # the key's characters under its bytes
    for i, c in enumerate(key):
        f.text((xs[4 + i] + xs[5 + i]) / 2, 175, c, "tm", 10.5, "middle", None, True)
    kend = 4 + len(key)
    f.brace_h(xs[4], xs[kend], 190, "a")
    f.brace_h(xs[kend], xs[kend + 1], 190, "a")
    f.text((xs[4] + xs[kend]) / 2, 208, "the key: the email", "ta", 11, "middle", 600)
    f.text(xs[kend + 1], 208, "then the rowid", "ta", 11, "end", 600)
    f.line(24, 222, 616, 222, "m")
    f.text(24, 242, "Nothing in an entry, or in its page, says unique: page 3 is the same bytes in both files.", "t", 11)
    f.text(24, 260, "cmp users.db plain.db 4096 4096 finds them the same from page 2 on, as sqlite3 writes them too.",
           "tm", 10.5)
    f.text(24, 276, "Only page 1 differs: one CREATE TABLE says UNIQUE, and the other file has a CREATE INDEX.",
           "tm", 10.5)
    return f


FIGS = [
    ("08.06-kinds", kinds0806), ("08.06-outer", outer0806), ("08.06-notin", notin0806),
    ("08.07-check", check0807), ("08.07-schema", schema0807), ("08.07-entry", entry0807),
]


# ------------------------------------------------------------------ the dump the numbers came from

def varint(b, i):
    """The varint at b[i]: (value, index after it)."""
    v = 0
    for k in range(9):
        c = b[i + k]
        if k == 8:
            return (v << 8) | c, i + 9
        v = (v << 7) | (c & 0x7f)
        if c < 0x80:
            return v, i + k + 1


def page_cells(path, n):
    """Page n of the database file at path: (its type, the content offset, each cell's bytes)."""
    with open(path, "rb") as fh:
        data = fh.read()
    p = data[(n - 1) * 4096:n * 4096]
    h = 100 if n == 1 else 0
    kind, ncell = p[h], int.from_bytes(p[h + 3:h + 5], "big")
    hl = 8 if kind in (0x0a, 0x0d) else 12
    out = []
    for c in range(ncell):
        off = int.from_bytes(p[h + hl + 2 * c:h + hl + 2 * c + 2], "big")
        size, i = varint(p, off)
        if kind == 0x0d:
            _, i = varint(p, i)
        out.append((off, p[off:i + size]))
    return kind, int.from_bytes(p[h + 5:h + 7], "big"), out


def dump(path, n):
    """Prints page n of the database file at path: its type, cell count, and each leaf cell's bytes."""
    kind, content, cs = page_cells(path, n)
    print(f"page {n}: type 0x{kind:02x}, {len(cs)} cells, content at {content}")
    for c, (off, b) in enumerate(cs):
        print(f"  cell {c} at {off}: " + " ".join(f"{x:02x}" for x in b))


def index_entries(path):
    """The (email, rowid) entries of the index leaf on page 3 of a users file, in key order:
    a record of header size, serial types (text, rowid) and the two values."""
    out = []
    for _, b in page_cells(path, 3)[2]:
        _, i = varint(b, 0)
        hsize, j = varint(b, i)
        t_key, j = varint(b, j)
        t_rid, j = varint(b, j)
        k = i + hsize
        n = (t_key - 13) // 2
        key = b[k:k + n].decode()
        rid = {8: 0, 9: 1}.get(t_rid)
        if rid is None:
            rid = int.from_bytes(b[k + n:], "big")
        out.append((key, rid))
    return out


# ------------------------------------------------------------------ --check: the numbers against a run

def run(path, sql, at, stats=False):
    """sql run by the engine at lesson `at` on path: (exit code, its output lines, its error text,
    and with stats DB_STATS=1's pages written)."""
    argv = [os.path.join(REPO, "learn"), "run", "db", "--at", at, "--", path, sql]
    env = dict(os.environ, DB_STATS="1") if stats else None
    r = subprocess.run(argv, cwd=REPO, capture_output=True, text=True, env=env)
    lines = [l for l in r.stdout.splitlines() if not l.startswith("Running db")]
    err = "\n".join(l for l in r.stderr.splitlines() if not l.startswith(("Running db", "stats:")))
    written = None
    if stats:
        m = re.search(r"pages written (\d+)", r.stderr)
        written = int(m[1]) if m else None
    errs = [l for l in lines + err.splitlines() if l.startswith("Error")]
    return r.returncode, [l for l in lines if not l.startswith("Error")], errs, written


def changed_pages(a, b):
    """The pages (1-based) on which files a and b differ."""
    with open(a, "rb") as fa, open(b, "rb") as fb:
        x, y = fa.read(), fb.read()
    n = max(len(x), len(y))
    return sorted({i // 4096 + 1 for i in range(n) if x[i:i + 1] != y[i:i + 1]})


def same_from(a, b, offset):
    """cmp a b offset offset: are the two files the same from offset to the end?"""
    with open(a, "rb") as fa, open(b, "rb") as fb:
        return fa.read()[offset:] == fb.read()[offset:]


def check():
    d = tempfile.mkdtemp(prefix="figs08c-")

    def same(what, got, want):
        if got != want:
            raise SystemExit(f"{what}: the engine says\n  {got}\nthe figure says\n  {want}")
        print("ok", what)

    def parse(v):
        return None if v == "" else int(v) if v.lstrip("-").isdigit() else v

    def rows(path, sql, at):
        rc, lines, errs, _ = run(path, sql, at)
        if rc or errs:
            raise SystemExit(f"{sql}: exit {rc}: {errs}")
        return [tuple(map(parse, l.split("|"))) for l in lines]

    def col(path, sql, at):
        return [r[0] for r in rows(path, sql, at)]

    # 08.06
    shop = os.path.join(d, "shop.db")
    rows(shop, DATA_SQL, "08.06")
    same("08.06: customers", rows(shop, "SELECT * FROM customers;", "08.06"), CUSTOMERS)
    same("08.06: orders", rows(shop, "SELECT * FROM orders;", "08.06"), ORDERS)
    same("08.06-kinds: the scalar subquery alone", col(shop, f"SELECT ({SCALAR_SUB});", "08.06"), [SCALAR_BACK])
    same("08.06-kinds: the scalar's answer", col(shop, KIND_SCALAR, "08.06"), SCALAR_OUT)
    same("08.06-kinds: IN's answer", col(shop, KIND_IN, "08.06"), IN_OUT)
    cids = col(shop, f"{IN_SUB} ORDER BY customer_id;", "08.06")
    same("08.06: the set kept, sorted, duplicates kept", [v for v in cids if v is not None], KEPT)
    same("08.06: has_null", int(None in cids), HAS_NULL)
    same("08.06-kinds: EXISTS for each customer", rows(shop, EXISTS_SQL, "08.06"), EXISTS_BACK)
    same("08.06-kinds: EXISTS's answer", col(shop, KIND_EXISTS, "08.06"), EXISTS_OUT)
    same("08.06-kinds: NOT EXISTS", col(shop, KIND_EXISTS.replace("WHERE EXISTS", "WHERE NOT EXISTS"), "08.06"),
         NOT_EXISTS_OUT)
    same("08.06-outer: the count for each customer", rows(shop, OUTER_SQL, "08.06"), OUTER_OUT)
    ada = CUSTOMERS[0][0]
    same("08.06-outer: Ada's run, the test on each order",
         rows(shop, f"SELECT o.id, o.customer_id, o.customer_id = {ada} FROM orders o;", "08.06"), ADA_TESTS)
    same("08.06-outer: Ada's run, its count",
         col(shop, COUNT_SUB.replace("c.id", str(ada)) + ";", "08.06"), [OUTER_OUT[0][1]])
    rc, _, errs, _ = run(shop, COUNT_SUB + ";", "08.06")
    same("08.06-outer: the count's subquery alone names a column outside", errs, ["Error: no such column: c.id"])
    same("08.06-outer: order 13's names none: it runs alone", col(shop, SCALAR_SUB + ";", "08.06"), [ONCE_OUT[0][1]])
    same("08.06-outer: ... as a rowid lookup", run(shop, f"EXPLAIN {SCALAR_SUB};", "08.06")[1], ONCE_PLAN)
    same("08.06-outer: order 13's customer_id for each customer", rows(shop, ONCE_SQL, "08.06"), ONCE_OUT)
    same("08.06-notin: customer_id as the scan reads it", col(shop, IN_SUB + ";", "08.06"), SCAN_CIDS)
    same("08.06-notin: IN and NOT IN for each customer", rows(shop, NOTIN_VALUES_SQL, "08.06"), NOTIN_VALUES)
    same("08.06-notin: the query's rows", rows(shop, NOTIN_SQL, "08.06"), [])
    same("08.06-notin: the NULL left out", col(shop, NOTIN_FIX_SQL, "08.06"), NOTIN_FIX_OUT)

    # 08.07: the lesson's users.db and plain.db, its statements in its order
    users, plain = os.path.join(d, "users.db"), os.path.join(d, "plain.db")
    rows(users, USERS_SQL, "08.07")
    same("08.07-schema: sqlite_schema's rows",
         rows(users, "SELECT type, name, tbl_name, rootpage, typeof(sql), sql FROM sqlite_schema;", "08.07"),
         [r[:5] + (r[5] or None,) for r in SCHEMA])
    same("08.07-schema: the index's row on page 1", page_cells(users, 1)[2][1][1], SCHEMA_ROW)
    rows(users, TWO_SQL, "08.07")
    before = os.path.join(d, "users-two.db")
    shutil.copy(users, before)
    _, _, errs, _ = run(users, CHEN_SQL, "08.07")
    same("08.07: the lesson's third insert", errs, [ERROR])
    same("08.07: ... leaves the file as it was", changed_pages(before, users), [])
    rows(plain, PLAIN_SQL, "08.07")
    rows(plain, TWO_SQL, "08.07")
    same("08.07-entry: cmp users.db plain.db 4096 4096: the same from page 2 on", same_from(users, plain, 4096), True)
    same("08.07-entry: both files' pages", [os.path.getsize(p) // 4096 for p in (users, plain)], [3, 3])
    for p in (users, plain):
        same(f"08.07-entry: {os.path.basename(p)}'s entries", index_entries(p), ENTRIES)
        same(f"08.07-entry: {os.path.basename(p)}'s page 3, cell {ENTRY_CELL}", page_cells(p, 3)[2][ENTRY_CELL][1], ENTRY)
    # 08.07-check, in The idea's order: Ada in row 1, then Brook, then the second Ada
    fig = os.path.join(d, "fig.db")
    rows(fig, USERS_SQL, "08.07")
    rows(fig, ins(ADA), "08.07")
    same("08.07-check: the index before Brook", index_entries(fig), ENTRIES[:1])
    shutil.copy(fig, before)
    rc, _, errs, written = run(fig, ins(BROOK), "08.07", stats=True)
    same("08.07-check: Brook's insert: no error, pages written", (rc, errs, written), (0, [], len(BROOK_PAGES)))
    same("08.07-check: ... the pages it changed", changed_pages(before, fig), BROOK_PAGES)
    same("08.07-check: the index after Brook", index_entries(fig), ENTRIES)
    same("08.07-check: Brook's row", rows(fig, f"SELECT * FROM users WHERE id = {BROOK[0]};", "08.07"), [BROOK])
    shutil.copy(fig, before)
    rc, _, errs, written = run(fig, CHEN_SQL, "08.07", stats=True)
    same("08.07-check: the second Ada: the error, pages written", (errs, written), ([ERROR], 0))
    same("08.07-check: ... and the file is unchanged", changed_pages(before, fig), [])
    same("08.07-check: that file is the lesson's users.db from page 2 on", same_from(fig, users, 4096), True)
    if not os.path.exists(SQLITE3):
        print("(no", SQLITE3, "- skipped the comparison with sqlite3's files)")
        return
    for name, create in (("users", USERS_SQL), ("plain", PLAIN_SQL)):
        sq = os.path.join(d, f"sq-{name}.db")
        subprocess.run([SQLITE3, sq, f"{create}; {TWO_SQL};"], check=True)
        same(f"08.07-entry: sqlite3's {name}.db is the same from page 2 on",
             same_from(sq, os.path.join(d, f"{name}.db"), 4096), True)
    r = subprocess.run([SQLITE3, users, CHEN_SQL], capture_output=True, text=True)
    same("08.07-check: sqlite3 refuses the second Ada in the same words",
         r.stderr.strip().split(": ", 1)[-1], ERROR.split(": ", 1)[1])
    shutil.rmtree(d)


def main():
    if sys.argv[1:2] == ["--dump"]:
        return dump(sys.argv[2], int(sys.argv[3]))
    if sys.argv[1:] == ["--check"]:
        return check()
    for name, fn in FIGS:
        print(figlib.write(MOD, name, fn()))


if __name__ == "__main__":
    main()
