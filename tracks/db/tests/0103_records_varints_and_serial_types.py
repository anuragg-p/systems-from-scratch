"""01.03 Records: varints and serial types

Every serial type round-trips between ./db and sqlite3 in both
directions, and ./db encodes each value in the smallest serial type,
byte for byte as sqlite3 does.
"""

VALUES = ["NULL", "0", "1", "2", "-1", "127", "128", "-128", "-129", "32767", "32768", "-32768", "-32769",
          "8388607", "8388608", "-8388608", "-8388609", "2147483647", "2147483648", "-2147483648",
          "-2147483649", "140737488355327", "140737488355328", "-140737488355328", "-140737488355329",
          "9223372036854775807", "-9223372036854775808", "0.5", "-1.25", "1e300", "3.141592653589793",
          "''", "'a'", "'" + "long text " * 120 + "'", "x''", "x'41ff42'", "x'" + "ab" * 700 + "'"]

# Blobs avoid control characters, which newer sqlite3 shells print escaped.
# length() of a float depends on how it prints, which sqlite3 versions do
# differently; the floats themselves are compared as numbers.
QUERY = ("SELECT rowid, typeof(x), x FROM v;\n"
         "SELECT rowid, length(x) FROM v WHERE typeof(x) IN ('integer', 'text', 'blob');\n")


def test(t):
    tr = t.track
    sql = "CREATE TABLE v(x);\n" + "".join(f"INSERT INTO v VALUES({v});\n" for v in VALUES)
    ours, theirs = tr.path(t), tr.path(t)
    tr.db(t, ours, sql)
    tr.sqlite(t, theirs, sql)

    want = tr.sqlite(t, theirs, QUERY).out
    t.check(tr.same_output(tr.db(t, ours, QUERY).out, want), "./db reads back different values from what it wrote")
    t.check(tr.same_output(tr.sqlite(t, ours, QUERY).out, want), "sqlite3 reads different values from ./db's file")
    t.check(tr.same_output(tr.db(t, theirs, QUERY).out, want), "./db reads different values from sqlite3's file")
    tr.integrity(t, ours)

    # The records themselves: the leaf page holding them is byte for byte
    # the one sqlite3 wrote, so every varint and serial type matches.
    a, b = tr.page(ours, 2), tr.page(theirs, 2)
    t.check(tr.page_type(ours, 2) == tr.page_type(theirs, 2) == 13, "page 2 should be the table's leaf in both")
    if a != b:
        first = next(i for i in range(len(a)) if a[i] != b[i])
        t.check(False, f"page 2 differs from sqlite3's, first at byte {first}: "
                       f"./db {a[first:first + 12].hex()}, sqlite3 {b[first:first + 12].hex()}")
