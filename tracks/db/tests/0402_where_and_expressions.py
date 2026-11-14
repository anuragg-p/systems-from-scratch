"""04.02 WHERE and expressions

Expressions follow SQLite: NULL is unknown (three-valued AND, OR, NOT),
comparisons apply column affinity, integer arithmetic overflows into
floats, and WHERE keeps a row only when its condition is true.
"""


def test(t):
    tr = t.track
    setup = """CREATE TABLE t(id INTEGER PRIMARY KEY, i INTEGER, s TEXT, x, f REAL);
INSERT INTO t VALUES (1, 5, '5', 5, 1.5), (2, NULL, 'abc', 'abc', NULL), (3, -3, '10', '10', -0.5),
  (4, 0, NULL, NULL, 0.0), (5, 9223372036854775807, 'Abc', x'00', 2.5), (6, 2, '2', 2.0, 100.0),
  (7, 10, 'b%c', 'B_C', 1e20), (8, NULL, NULL, NULL, NULL);
"""
    wheres = ["i = 5", "i = '5'", "s = 5", "s = '5'", "x = 5", "x = '5'", "x = 2", "i > 2", "i < 2",
              "i >= 0 AND s IS NOT NULL", "i IS NULL", "i IS NOT NULL", "s IS i", "i = NULL", "NOT i = 5",
              "i > 0 OR s = 'abc'", "i > 100 OR i IS NULL", "NOT (i > 0 AND s IS NULL)", "i BETWEEN 0 AND 5",
              "i NOT BETWEEN 0 AND 5", "i IN (5, 10, NULL)", "i NOT IN (5, 10)", "i NOT IN (5, NULL)",
              "s LIKE 'a%'", "s LIKE 'AB_'", "s NOT LIKE '%b%'", "x LIKE 'b_c'", "f > 1", "f = 2.5",
              "i + 1 > 5", "i * 2 = 20", "i / 2 = 2", "i % 3 = 2", "s || 'x' = 'abcx'", "x > 'a'",
              "x < 1", "typeof(x) = 'blob'", "length(s) = 3", "abs(i) = 3", "coalesce(i, 0) = 0", "1",
              "0", "NULL", "'1abc'", "i", "s", "f"]
    sql = "".join(f"SELECT id FROM t WHERE {w};\nSELECT '--';\n" for w in wheres)
    tr.both(t, sql, setup)
    exprs = """SELECT 9223372036854775807 + 1, -9223372036854775808 - 1, 3037000500 * 3037000500, 7 / 2, -7 / 2;
SELECT 7 % 3, -7 % 3, 7 % -3, 5.5 % 2, 7 / 0, 7 % 0, 7.0 / 2, 1 / 2.0, 2 * 0.5;
SELECT '3' + 4, 'abc' + 1, '12abc' * 2, ' 4 ' + 1, '1e2' + 0, x'3132' + 1, NULL + 1, -'5', -NULL;
SELECT 1 || 2, 1.5 || 'x', NULL || 'x', typeof(1 || 2), 'a' = 'A', 'a' < 'b', 'a' < 'B', x'61' = 'a';
SELECT lower('MiXeD'), upper('MiXeD'), length('h\u00e9llo'), length(x'0102'), length(12345), abs(-4.5), abs(NULL);
SELECT typeof(NULL), typeof(1), typeof(1.0), typeof('1'), typeof(x'01'), coalesce(NULL, NULL, 3), ifnull(NULL, 'd');
SELECT 1 = 1.0, 2 < 2.5, 9007199254740993 = 9007199254740992.0, 3 > '2', '10' > '9', 10 > 9;
SELECT NULL AND 0, NULL AND 1, NULL OR 1, NULL OR 0, NOT NULL, 0 AND NULL, 1 OR NULL;
"""
    tr.both(t, exprs)
    sel = "SELECT id, i + f, s || i, i * 2, -f, i > s, x = s FROM t;\n"
    tr.both(t, sel, setup)
    tr.errors_alike(t, setup, "SELECT nosuch FROM t;\n")
    tr.errors_alike(t, setup, "SELECT id FROM t WHERE nosuchfn(i);\n")
