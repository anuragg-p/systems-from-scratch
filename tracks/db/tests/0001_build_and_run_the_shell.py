"""00.01 How a database works

./db is a REPL and a one-shot command over one database file, and the
file it writes is a SQLite database the real sqlite3 opens.
"""

import os


def test(t):
    tr = t.track
    f = tr.path(t, "shell.db")
    s = tr.repl(t, f)
    out = tr.ask(s, "CREATE TABLE fruit(id INTEGER PRIMARY KEY, name TEXT, price REAL);")
    t.check(out.strip() == "", f"CREATE TABLE should print nothing, printed {out!r}")
    tr.ask(s, "INSERT INTO fruit(name, price) VALUES ('apple', 0.5), ('pear', 0.75);")
    s.sendline("SELECT name, price")
    s.expect(r"\.\.\.> ", timeout=10)          # the statement goes on: a continuation prompt
    out = tr.ask(s, "FROM fruit ORDER BY price DESC;")
    t.check(out.splitlines() == ["pear|0.75", "apple|0.5"], f"SELECT printed {out!r}")
    out = tr.ask(s, ".tables")
    t.check(out.split() == ["fruit"], f".tables printed {out!r}")
    out = tr.ask(s, ".schema")
    t.check("CREATE TABLE fruit(id INTEGER PRIMARY KEY, name TEXT, price REAL);" in out, f".schema printed {out!r}")
    out = tr.ask(s, "SELECT * FROM nosuch;")
    t.check("Error: no such table: nosuch" in out, f"a bad query should print an error, printed {out!r}")
    s.sendline(".exit")
    t.check(s.wait_exit() == 0, ".exit should leave the REPL with status 0")

    exe = os.path.join(t.root, "db")
    r = t.run([exe, f, "SELECT id, name FROM fruit WHERE id = 2"])
    t.check(r.stdout == "2|pear\n", f"one-shot mode printed {r.stdout!r}")
    r = t.run([exe, f, "SELECT * FROM nosuch"], check=False)
    t.check(r.returncode == 1 and "no such table" in r.stderr, f"one-shot errors exit 1: {r.returncode} {r.stderr!r}")

    out = tr.sqlite(t, f, "PRAGMA integrity_check;\nSELECT name FROM fruit ORDER BY id;").out
    t.check(out.split() == ["ok", "apple", "pear"], f"sqlite3 should read the same file, got {out!r}")
