"""05.03 Choosing a plan, and EXPLAIN

The planner picks the access path sqlite3 picks for simple queries, and
EXPLAIN QUERY PLAN prints it the way sqlite3 does. (Not compared: plans
where sqlite3 goes further, such as a = 3 AND id > 1, which it answers
with the rowid at the end of each index entry: (a=? AND rowid>?).)

Then whatever plan is chosen, the answers are SQLite's: SQLite's own query
corpus, sqllogictest, runs through ./db (tests/sqllogictest/README.md): the
first records of each kept script here, every record with SLT=full.
"""


def test(t):
    tr = t.track
    setup = ("CREATE TABLE t(id INTEGER PRIMARY KEY, a INTEGER, b TEXT);\nCREATE INDEX t_a ON t(a);\n"
             "INSERT INTO t VALUES (1, 10, 'x'), (2, 20, 'y'), (3, 30, 'z');\n"
             "CREATE TABLE r(v, w);\n")
    queries = ["SELECT * FROM t WHERE id = 5", "SELECT * FROM t WHERE a = 5", "SELECT * FROM t WHERE a > 5 AND a < 9",
               "SELECT * FROM t WHERE a > 5", "SELECT * FROM t WHERE a < 5", "SELECT * FROM t WHERE a BETWEEN 1 AND 2",
               "SELECT * FROM t WHERE id > 5", "SELECT * FROM t WHERE id < 5", "SELECT * FROM t WHERE id >= 2 AND id <= 3",
               "SELECT * FROM t WHERE 5 = a", "SELECT * FROM t", "SELECT * FROM t WHERE b = 'x'",
               "SELECT * FROM t ORDER BY b", "SELECT * FROM t ORDER BY id", "SELECT * FROM t WHERE a = 5 ORDER BY b",
               "SELECT * FROM t WHERE id = 5 AND a = 3",
               "SELECT 1", "SELECT * FROM r WHERE rowid = 2", "SELECT * FROM r WHERE v = 1",
               "UPDATE t SET b = 'q' WHERE id = 3", "DELETE FROM t WHERE a = 2", "UPDATE t SET b = 'q'"]
    tr.both(t, "".join(f"EXPLAIN QUERY PLAN {q};\n" for q in queries), setup)
    tr.both(t, "".join(f"{q};\n" for q in queries if q.startswith("SELECT")), setup)

    f = tr.path(t)
    tr.db(t, f, setup)
    plans = {"SELECT b FROM t WHERE id = 2": "Rowid lookup", "SELECT b FROM t WHERE a = 20": "Index lookup",
             "SELECT b FROM t WHERE a > 15": "Index range", "SELECT b FROM t WHERE id > 1": "Rowid range",
             "SELECT b FROM t WHERE b = 'y'": "Scan"}
    for q, op in plans.items():
        out = tr.db(t, f, f"EXPLAIN {q};\n").out.splitlines()
        t.check(out[-1].strip().startswith(op), f"EXPLAIN {q} should end in a {op} operator:\n" + "\n".join(out))

    tr.sqllogictest(t)
