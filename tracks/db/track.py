"""Track db: a SQL database in C, from scratch.

The engine is one binary, ./db (make builds it): a REPL on a database file,
or one-shot with the SQL as an argument. Its database file is a real SQLite
file, so the tests hold it to the real sqlite3: the same SQL in both must
give the same answers, and each must open what the other wrote.

Fixtures the lesson tests use:

    db(t, path, sql, env=None, check=True)
                        run sql through ./db on the file at path (sql on
                        stdin, as a user would pipe it); a Result with
                        .out, .err, .rc. check=True fails on any error.
    sqlite(t, path, sql, check=True)
                        the same through the real sqlite3
    both(t, sql, setup="")
                        run setup + sql in ./db and in sqlite3, each on a
                        fresh file, and fail unless the output is the same
                        (floats compared as numbers); returns the output
    errors_alike(t, setup, sql)
                        sql must fail in both engines
    integrity(t, path)  sqlite3's PRAGMA integrity_check must say ok
    crash(t, path, point, sql, env=None)
                        run sql with DB_CRASH=point: ./db must die there
    kill_sqlite(t, path, sql)
                        run sql in an interactive sqlite3 and SIGKILL it
                        with the transaction still open (a hot journal or a
                        WAL left behind, written by sqlite3 itself)
    repl(t, path)       ./db -interactive as a Session; ask(s, sql) types a
                        statement and returns what it printed
    stats(err)          the DB_STATS=1 counters, as a dict
    header(path), page(path, n), page_type(path, n)
                        read the file's bytes directly
    path(t, name)       a file in the test's scratch directory
    sqlite_bin()        the newest sqlite3 found ($SQLITE3 overrides)
    sqllogictest(t, have=(), scripts=None)
                        SQLite's sqllogictest corpus through ./db (tests/sqllogictest,
                        its README.md): a quick slice, or every kept script with
                        SLT=full in the environment; have names what module 08 added
                        (join, aggregate, ...), which is then run instead of skipped
    keeps_unique(root)  does the project at root keep UNIQUE and PRIMARY KEY
                        constraints (08.07)? A core test that checks the refusal
                        before it checks what 08.07 makes of the same SQL instead

Tests are internal. A lesson's test runs the whole engine, so with that
lesson's code cut out it fails at the stub: "db: NN.LL: ... not written yet".
"""

import os
import re
import signal
import struct
import subprocess
import sys
import time

from harness.core import Fail

TITLE = "A SQL database in C, from scratch"
KIND = "database"
SUMMARY = "Pages, B-trees, SQL, a query planner and crash-proof commits, in a file sqlite3 can open."

# What this track is built on (see harness/web/views.py, upstreams()): not SQLite's code,
# none of which is here, but its documented file, journal and WAL formats, and the real
# sqlite3 the engine is held to. "also": more links for /credits.
UPSTREAM = {
    "name": "SQLite",
    "url": "https://github.com/sqlite/sqlite",
    "licence": "Public domain",
    "owes": "Our own engine, written to SQLite's file format and checked against the real sqlite3.",
    "derived": False,
    "also": [("The database file format", "https://www.sqlite.org/fileformat2.html"),
             ("SQLite's source, at its home", "https://sqlite.org/src"),
             ("SQLite's copyright statement", "https://sqlite.org/copyright.html")],
    "chip": "SQLite-compatible",
}

# Internal, and so not in UPSTREAM (which the site shows): the test corpus the author tests
# run the engine against. A subset of it is kept in tests/sqllogictest/test/, unchanged;
# tests/sqllogictest/README.md says which files, and COPYRIGHT.md there is its licence.
TEST_CORPUS = {
    "name": "sqllogictest",
    "url": "https://www.sqlite.org/sqllogictest/",
    "mirror": "https://github.com/gregrahn/sqllogictest",
    "commit": "c93ac416f05635ff5cc490009add936d9753d01d",
    "copyright": "Copyright (c) 2008 D. Richard Hipp",
    "licence": "Free to redistribute and modify, no attribution required; GPL, BSD, MIT or CC0, "
               "whichever best applies",
    "licence_file": "tests/sqllogictest/COPYRIGHT.md",
    "kept": "tests/sqllogictest/test/",
}

# Files that may hold "@build NN.LL" regions (see harness/workspace.py),
# and what replaces a region's code when a learner's workspace cuts it.
SOURCES = ["src/*.c", "src/*.h"]
# Not for learners: notes for the lesson writers (break-its, real outputs), and
# the ./db binary the Makefile builds at the top of the track.
HIDDEN = ["NOTES.md", "db"]
# When each file comes into the project the site shows, lesson by lesson (see
# harness/timeline.py): a file with @build regions comes with its first region's
# lesson unless it is named here; every file without regions must be named. A file
# belongs to the first lesson that needs it to build or run, and the project at every
# lesson builds and runs (./learn check-timeline db). What later lessons add to a
# file outside their regions is marked "@from NN.LL" in the file itself.
FILES_FROM = {
    "Makefile": "00.01",
    "bench/bench.py": "00.02",
    "src/db.h": "01.01",
    "src/main.c": "01.01",
    "src/util.c": "01.01",
    "src/expr.c": "02.01",       # value_compare: the order of index keys
    "src/exec.c": "03.02",       # db_exec: statements run from the parser on
    "src/plan.c": "04.01",       # plan_query: every SELECT has a plan
}
STUBS = {".c": 'todo("{id}", "{title}");'}

MIN_SQLITE = (3, 37, 0)


def build(t):
    t.run(["make", "-s"])


# ---------------------------------------------------------------- run it, and the benchmark
#
# The track contract's optional hooks: prepare(root) returns the command
# that builds the tree, run_argv(root) the command that starts the system,
# bench(root) the command that runs the benchmark. All run with cwd=root.

def prepare(root):
    return ["make", "-s"]


def run_argv(root, args=()):
    """The REPL, on a database file kept between runs; with args (./learn run db -- ...),
    ./db with those instead: a file, and SQL to run on it once."""
    return ["./db"] + (list(args) or ["learn.db"])


def bench(root):
    """The benchmark: ./db against sqlite3 on the same workloads."""
    return [sys.executable, "bench/bench.py", "--db", "./db"]


# ---------------------------------------------------------------- the project at each lesson
#
# Internal: ./learn check-timeline db builds the project as the site shows it at each
# lesson (harness/timeline.py), types a few statements into its REPL (timeline_boot), then
# runs it once more and has sqlite3 open the files (timeline_after). Before module 03
# there is no SQL: the shell opens the file and refuses every statement. A statement
# whose lesson is still ahead gets an ordinary error ("WHERE is not supported"), never a
# crash or a stub.

TIMELINE_FAIL = [r"not written yet", r"db: fatal", r"internal error"]


def timeline_run(root):
    """The REPL with its prompts, on a file of its own."""
    return ["./db", "-interactive", "learn.db"]


def _refused(msg):
    return r"Error: " + re.escape(msg) + r"\r?\n" + PROMPT


def _rows(*lines):
    return "".join(re.escape(l) + r"\r?\n" for l in lines) + PROMPT


def timeline_boot(lesson_id):
    """(text to type, regex to wait for) steps for the REPL as it stands at a lesson:
    what that lesson's code can do, and an ordinary error for the next thing it cannot."""
    from harness.core import lesson_key
    k = lesson_key(lesson_id)
    if k < (1, 1):
        return []
    P = PROMPT
    steps = [(None, P)]
    if k < (3, 1):        # no tokenizer: a statement ends at its first semicolon
        steps += [("CREATE TABLE t(a);", _refused("SQL is not supported")),
                  ("SELECT 'a;", _refused("SQL is not supported"))]
    else:                 # a semicolon inside a string does not end the statement
        steps += [("SELECT 'a;", r"\.\.\.> $"),
                  ("b';", _refused("SQL is not supported") if k < (3, 2) else
                   _refused("SELECT is not supported") if k < (4, 1) else _rows("a;", "b"))]
    if k >= (3, 2):
        steps += [("SELECT 1 +;", _refused('near ";": syntax error')),
                  ("PRAGMA page_size;", _rows("4096"))]
        if k < (6, 2):
            steps += [("PRAGMA journal_mode;", _rows("off")),
                      ("PRAGMA journal_mode=delete;", _refused("journal_mode delete is not supported (off)"))]
        elif k < (6, 4):
            steps += [("PRAGMA journal_mode;", _rows("delete")),
                      ("PRAGMA journal_mode=wal;", _refused("journal_mode wal is not supported (delete or off)"))]
    if (3, 2) <= k < (3, 3):
        steps += [("CREATE TABLE t(id INTEGER PRIMARY KEY, a TEXT, b);", _refused("CREATE TABLE is not supported"))]
    if k >= (3, 3):
        steps += [("CREATE TABLE t(id INTEGER PRIMARY KEY, a TEXT, b);", P),
                  ("BEGIN;", P), ("CREATE TABLE gone(x);", P), ("ROLLBACK;", P),
                  (".tables", _rows("t")),
                  (".schema", _rows("CREATE TABLE t(id INTEGER PRIMARY KEY, a TEXT, b);"))]
    if (3, 3) <= k < (4, 1):
        steps += [("INSERT INTO t VALUES (1, 'one', 1);", _refused("INSERT is not supported")),
                  ("SELECT * FROM t;", _refused("SELECT is not supported"))]
    if k >= (4, 1):
        steps += [("INSERT INTO t(a, b) VALUES ('one', 1), ('two', 2), ('three', 3);", P),
                  ("SELECT * FROM t;", _rows("1|one|1", "2|two|2", "3|three|3")),
                  ("SELECT 1 + 2 * 3, 'a' || 'b', typeof(b) FROM t WHERE id = 1;" if k >= (4, 2)
                   else "SELECT 1 + 2 * 3, 'a' || 'b';", _rows("7|ab|integer") if k >= (4, 2) else _rows("7|ab"))]
    if k >= (4, 1):
        steps += [("EXPLAIN SELECT a FROM t;", _rows("Scan t"))]
        if k < (4, 4):
            steps += [("EXPLAIN DELETE FROM t;", _refused("EXPLAIN is only supported for SELECT"))]
        else:
            steps += [("EXPLAIN DELETE FROM t;", _rows("Scan t"))]
        if k < (5, 3):
            steps += [("EXPLAIN QUERY PLAN SELECT a FROM t;", _refused("EXPLAIN QUERY PLAN is not supported"))]
    if (4, 1) <= k < (4, 2):
        steps += [("SELECT a FROM t WHERE id = 2;", _refused("WHERE is not supported")),
                  ("SELECT 1 = 1;", _refused("comparisons are not supported"))]
    if k >= (4, 2):
        steps += [("SELECT a FROM t WHERE id = 2 OR b > 2;", _rows("two", "three"))]
    if (4, 2) <= k < (4, 3):
        steps += [("SELECT a FROM t ORDER BY a;", _refused("ORDER BY is not supported")),
                  ("SELECT a FROM t LIMIT 1;", _refused("LIMIT is not supported"))]
    if k >= (4, 3):
        steps += [("SELECT a FROM t ORDER BY a DESC LIMIT 2;", _rows("two", "three"))]
    if (4, 3) <= k < (4, 4):
        steps += [("UPDATE t SET b = 0;", _refused("UPDATE is not supported")),
                  ("DELETE FROM t;", _refused("DELETE is not supported"))]
    if k >= (4, 4):
        steps += [("UPDATE t SET b = b * 10 WHERE id = 3;", P), ("DELETE FROM t WHERE id = 1;", P),
                  ("SELECT * FROM t;", _rows("2|two|2", "3|three|30"))]
    if (4, 4) <= k < (5, 1):
        steps += [("CREATE INDEX t_b ON t(b);", _refused("CREATE INDEX is not supported"))]
    if k >= (5, 1):
        steps += [("CREATE INDEX t_b ON t(b);", P), ("INSERT INTO t VALUES (4, 'four', 4);", P),
                  ("SELECT a FROM t WHERE b = 4;", _rows("four"))]
    if k >= (5, 3):
        steps += [("EXPLAIN QUERY PLAN SELECT a FROM t WHERE b = 4;",
                   _rows("QUERY PLAN", "`--SEARCH t USING INDEX t_b (b=?)"))]
    if k >= (6, 4):
        steps += [("PRAGMA journal_mode=wal;", _rows("wal")), ("INSERT INTO t VALUES (5, 'five', 5);", P),
                  ("PRAGMA journal_mode=delete;", _rows("delete"))]
    # Module 08 (More SQL) is an extension: its lessons stand on the whole core above.
    if lesson_id.startswith("08."):
        steps += [(JOIN_QUERY, _rows("two|three", "three|four", "four|five"))]
        if k < (8, 2):
            steps += [("SELECT * FROM t LEFT JOIN t AS u ON u.id = t.b;", _refused("LEFT JOIN is not supported"))]
    # The 08.07 extension: UNIQUE is an index, and a duplicate is refused as sqlite3 refuses it.
    if (3, 3) <= k < (8, 7):
        steps += [("CREATE TABLE u(a UNIQUE, b);", _refused("UNIQUE is not supported"))]
    if k >= (8, 7):
        steps += [("CREATE TABLE u(a UNIQUE, b TEXT PRIMARY KEY);", P), ("INSERT INTO u VALUES (1, 'x'), (2, 'y');", P),
                  ("INSERT INTO u VALUES (1, 'z');", _refused("UNIQUE constraint failed: u.a")),
                  ("UPDATE u SET b = 'x' WHERE a = 2;", _refused("UNIQUE constraint failed: u.b")),
                  ("SELECT a FROM u WHERE b = 'y';", _rows("2"))]
    return steps


# 08.01 on: a self-join of the REPL's table t, each row with the row whose id is one more.
JOIN_QUERY = "SELECT x.a, y.a FROM t AS x JOIN t AS y ON y.id = x.id + 1 ORDER BY x.id;"


def timeline_after(root, lesson_id):
    """After the REPL: one-shot runs, and sqlite3 on the file the REPL wrote and on files
    sqlite3 wrote for ./db. Raises Fail; returns a short note."""
    from harness.core import lesson_key
    k = lesson_key(lesson_id)
    sq = sqlite_bin()

    def run(argv, sql=None, env=None, crash=None):
        r = _run(argv, sql or "", _env(env), 60)
        bad = [p for p in TIMELINE_FAIL if re.search(p, r.err + r.out)]
        if crash and not (r.rc == -signal.SIGKILL and f"crash injected at {crash}" in r.err):
            raise Fail(f"{' '.join(argv)} should have been killed at {crash}:\n{r}")
        if bad or (r.rc < 0 and not crash):
            raise Fail(f"{' '.join(argv)} {'died' if r.rc < 0 else 'printed ' + bad[0]}:\n{r}")
        return r

    def mine(*args, sql=None, env=None, crash=None):
        if crash:
            env = dict(env or {}, DB_CRASH=crash)
        return run([os.path.join(root, "db")] + list(args), sql, env, crash)

    def theirs(path, sql):
        r = run([sq, path], sql)
        if r.rc != 0 or r.err.strip():
            raise Fail(f"sqlite3 failed on {os.path.basename(path)}:\n{r}")
        return r.out

    learn = os.path.join(root, "learn.db")
    r = mine(os.path.join(root, "Makefile"), ".tables")
    if r.rc != 1 or "Error: file is not a database" not in r.err:
        raise Fail(f"./db should refuse the Makefile as not a database:\n{r}")
    if theirs(learn, "PRAGMA integrity_check;").strip() != "ok":
        raise Fail("sqlite3 says learn.db is damaged")
    notes = ["sqlite3: learn.db ok"]
    if k >= (4, 1):
        q = "SELECT * FROM t" + (" ORDER BY id" if k >= (4, 3) else "") + ";"
        ours, real = mine(learn, q), theirs(learn, q)
        if ours.rc != 0 or ours.out != real or not real:
            raise Fail(f"./db and sqlite3 read t differently:\n./db: {ours.out!r}\nsqlite3: {real!r}")
        notes.append(f"reads t like ./db, {len(real.splitlines())} rows")
    if lesson_id.startswith("08."):
        ours, real = mine(learn, JOIN_QUERY), theirs(learn, JOIN_QUERY)
        if ours.rc != 0 or ours.out != real or not real:
            raise Fail(f"./db and sqlite3 join t with itself differently:\n./db: {ours.out!r}\nsqlite3: {real!r}")
        notes.append(f"joins t with itself like sqlite3, {len(real.splitlines())} rows")
    if k >= (3, 3):
        s3 = os.path.join(root, "s3.db")
        theirs(s3, "CREATE TABLE u(x, y); INSERT INTO u VALUES (1, 'a');")
        r = mine(s3, ".tables")
        if r.rc != 0 or r.out != "u\n":
            raise Fail(f"./db does not see sqlite3's table u:\n{r}")
        if k >= (4, 1) and mine(s3, "SELECT * FROM u;").out != "1|a\n":
            raise Fail("./db does not read sqlite3's row in u")
        notes.append("./db reads sqlite3's file")
    wal = os.path.join(root, "w.db")
    theirs(wal, "PRAGMA journal_mode=wal; CREATE TABLE w(x);")
    r = mine(wal, ".exit")
    if k < (6, 4):
        if r.rc != 1 or "file format version 2 is newer than this engine understands" not in r.err:
            raise Fail(f"./db should refuse a WAL file before 06.04:\n{r}")
        notes.append("refuses a WAL file")
    elif r.rc != 0:
        raise Fail(f"./db cannot open a WAL file:\n{r}")
    if k < (4, 1):
        return ", ".join(notes)

    # A table sqlite3 made with UNIQUE: read-only until 08.07 keeps its indexes, then written soundly.
    uq = os.path.join(root, "uq.db")
    theirs(uq, "CREATE TABLE q(a UNIQUE, b TEXT PRIMARY KEY); INSERT INTO q VALUES (1, 'x');")
    r = mine(uq, "INSERT INTO q VALUES (2, 'y');")
    if k < (8, 7):
        if r.rc != 1 or "read-only" not in r.err:
            raise Fail(f"./db should refuse to write sqlite3's UNIQUE table before 08.07:\n{r}")
        notes.append("sqlite3's UNIQUE table read-only")
    else:
        dup = mine(uq, "INSERT INTO q VALUES (1, 'z');")
        if r.rc != 0 or dup.rc != 1 or "UNIQUE constraint failed: q.a" not in dup.err:
            raise Fail(f"./db should write sqlite3's UNIQUE table and refuse a duplicate:\n{r}\n{dup}")
        if theirs(uq, "PRAGMA integrity_check;").strip() != "ok":
            raise Fail("sqlite3 says uq.db is damaged after ./db wrote it")
        notes.append("writes sqlite3's UNIQUE table")

    # 300 rows in rowid order, over several leaves: from 07.03 a full leaf splits for an append
    fill = os.path.join(root, "f.db")
    sql = "CREATE TABLE f(id INTEGER PRIMARY KEY, b TEXT);\nBEGIN;\n" + "".join(
        f"INSERT INTO f VALUES ({i}, 'old {'o' * 100}');\n" for i in range(1, 301)) + "COMMIT;\n"
    r = mine(fill, sql=sql, env={"DB_STATS": "1"})
    appends = stats(r.err)["append splits"]
    if r.rc != 0 or (appends > 0) != (k >= (7, 3)):
        raise Fail(f"filling f in rowid order: {appends} append splits at {lesson_id}:\n{r}")
    if theirs(fill, "PRAGMA integrity_check;").strip() != "ok":
        raise Fail("sqlite3 says f.db is damaged")
    notes.append(f"{appends} append splits")
    if k < (6, 1):
        return ", ".join(notes)

    def copy(name):
        path = os.path.join(root, name)
        with open(fill, "rb") as a, open(path, "wb") as b:
            b.write(a.read())
        return path

    def changed(path):
        return len(mine(path, "SELECT id FROM f WHERE b = 'new';").out.splitlines())

    # 06.01: with no journal a crash halfway through a commit leaves half of it
    off = copy("off.db")
    mine(off, "PRAGMA journal_mode=off; UPDATE f SET b = 'new';", crash="db-partial")
    half = changed(off)
    if not 0 < half < 300 or theirs(off, "PRAGMA integrity_check;").strip() != "ok":
        raise Fail(f"a crash with no journal should leave some rows changed, not {half}")
    notes.append(f"no journal: a crash leaves {half} of 300 rows changed")
    if k < (6, 2):
        return ", ".join(notes)
    # 06.02: the same crash with the journal leaves a hot journal; 06.03 plays it back
    hot = copy("hot.db")
    mine(hot, "UPDATE f SET b = 'new';", crash="db-partial")
    if not os.path.exists(hot + "-journal"):
        raise Fail("a crash in the middle of a commit left no journal")
    if k < (6, 3):
        if theirs(hot, "SELECT count(*) FROM f WHERE b = 'new';").strip() != "0":
            raise Fail("sqlite3 did not roll back the hot journal ./db left")
        notes.append("sqlite3 rolls back its hot journal")
    else:
        if changed(hot) != 0 or os.path.exists(hot + "-journal"):
            raise Fail("./db did not roll back its own hot journal")
        notes.append("./db rolls back its hot journal")
    return ", ".join(notes)


# ---------------------------------------------------------------- ./learn verify
#
# Internal: how ./learn verify (harness/verify.py) replays the transcripts in the lessons. A
# line of a transcript that starts with one of these prompts is typed; EOF (Control-D) leaves
# the shell, as it leaves sqlite3's.

VERIFY_PROMPTS = ["db> ", "   ...> ", "sqlite> "]
VERIFY_QUIT = ["\x04"]
VERIFY_QUIET = 0.15         # seconds of quiet after a prompt that mean "done"
VERIFY_SETTLE = 1.0         # without a prompt: seconds of quiet that mean "done"


def verify_tools():
    """What replaying a lesson needs: the C compiler and make that build ./db, and the sqlite3
    the tests use (Homebrew's, found as sqlite_bin() finds it), first on the terminal's PATH."""
    import shutil as sh
    try:
        sq = sqlite_bin()
    except Fail:
        sq = None
    return {"sqlite3": sq, "cc": sh.which("cc"), "make": sh.which("make")}


# ---------------------------------------------------------------- the engines

_sqlite = None


def _version(path):
    try:
        out = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    m = re.match(r"(\d+)\.(\d+)\.(\d+)", out)
    return tuple(int(x) for x in m.groups()) if m else None


def sqlite_bin():
    """The newest sqlite3 on this machine: $SQLITE3, Homebrew's, then PATH."""
    global _sqlite
    if _sqlite:
        return _sqlite
    cands = [os.environ["SQLITE3"]] if os.environ.get("SQLITE3") else []
    cands += ["/opt/homebrew/opt/sqlite/bin/sqlite3", "/usr/local/opt/sqlite/bin/sqlite3"]
    cands += [os.path.join(d, "sqlite3") for d in os.environ.get("PATH", "").split(os.pathsep)]
    cands.append("/usr/bin/sqlite3")
    best = None
    for c in cands:
        if os.path.isfile(c) and os.access(c, os.X_OK):
            v = _version(c)
            if v and (best is None or v > best[0]):
                best = (v, c)
    if best is None:
        raise Fail("no sqlite3 found: install it, or set SQLITE3 to one")
    if best[0] < MIN_SQLITE:
        raise Fail(f"sqlite3 at {best[1]} is {'.'.join(map(str, best[0]))}; the tests need "
                   f"{'.'.join(map(str, MIN_SQLITE))} or newer")
    _sqlite = best[1]
    return _sqlite


class Result:
    def __init__(self, argv, r):
        self.argv = argv
        self.out = r.stdout
        self.err = r.stderr
        self.rc = r.returncode

    def lines(self):
        return self.out.splitlines()

    def __repr__(self):
        return f"rc={self.rc}\n--- stdout\n{self.out[-1500:]}\n--- stderr\n{self.err[-1500:]}"


def _env(extra=None):
    env = {k: v for k, v in os.environ.items() if not k.startswith("DB_")}
    env.update(extra or {})
    return env


def _run(argv, sql, env=None, timeout=300):
    try:
        r = subprocess.run(argv, input=sql, capture_output=True, text=True, errors="surrogateescape",
                           timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        raise Fail(f"{' '.join(argv)} did not finish in {timeout}s")
    return Result(argv, r)


def _quiet_err(err):
    """stderr without the lines the engine prints by request (stats) or to inform."""
    return "\n".join(l for l in err.splitlines()
                     if not l.startswith("stats:") and not l.startswith("db: rolled back")).strip()


def db(t, path, sql, env=None, check=True, timeout=300):
    """Run sql through ./db on the file at path."""
    r = _run([os.path.join(t.root, "db"), path], sql, _env(env), timeout)
    if check and (r.rc != 0 or _quiet_err(r.err)):
        raise Fail(f"./db failed on {os.path.basename(path)}:\n{r}\n--- sql\n{sql[:1500]}")
    return r


def sqlite(t, path, sql, check=True, timeout=300):
    """Run sql through the real sqlite3 on the file at path."""
    r = _run([sqlite_bin(), path], sql, _env(), timeout)
    if check and (r.rc != 0 or r.err.strip()):
        raise Fail(f"sqlite3 failed on {os.path.basename(path)}:\n{r}\n--- sql\n{sql[:1500]}")
    return r


_n = [0]


def path(t, name=None):
    """A new file name in the test's scratch directory."""
    _n[0] += 1
    return os.path.join(t.tmp, name or f"f{_n[0]}.db")


def _same_field(a, b):
    if a == b:
        return True
    try:
        x, y = float(a), float(b)
    except ValueError:
        return False
    if x == y:
        return True
    return abs(x - y) <= 1e-12 * max(abs(x), abs(y))


def same_output(a, b):
    """Two engines' outputs agree: line by line, field by field, with floats
    compared as numbers (sqlite3 versions print floats differently)."""
    la, lb = a.splitlines(), b.splitlines()
    if len(la) != len(lb):
        return False
    for x, y in zip(la, lb):
        fx, fy = x.split("|"), y.split("|")
        if len(fx) != len(fy) or not all(_same_field(p, q) for p, q in zip(fx, fy)):
            return False
    return True


def _diff(a, b):
    la, lb = a.splitlines(), b.splitlines()
    for i in range(max(len(la), len(lb))):
        x = la[i] if i < len(la) else "<nothing>"
        y = lb[i] if i < len(lb) else "<nothing>"
        if not same_output(x, y):
            return f"first difference at output line {i + 1}:\n  ./db:    {x!r}\n  sqlite3: {y!r}"
    return "outputs differ"


def both(t, sql, setup=""):
    """Run setup + sql in both engines on fresh files and compare outputs."""
    a, b = path(t), path(t)
    if setup:
        db(t, a, setup)
        sqlite(t, b, setup)
    ours = db(t, a, sql)
    theirs = sqlite(t, b, sql)
    if not same_output(ours.out, theirs.out):
        raise Fail(f"./db and sqlite3 disagree. {_diff(ours.out, theirs.out)}\n--- sql\n{sql[:2000]}")
    return ours.out


def errors_alike(t, setup, sql):
    """sql must be an error in both engines."""
    a, b = path(t), path(t)
    if setup:
        db(t, a, setup)
        sqlite(t, b, setup)
    ours = db(t, a, sql, check=False)
    theirs = sqlite(t, b, sql, check=False)
    t.check(theirs.rc != 0 or theirs.err.strip(), f"sqlite3 accepted {sql!r}; the test is wrong")
    t.check(ours.rc != 0 and "Error:" in ours.err,
            f"./db should reject {sql!r} as sqlite3 does ({theirs.err.strip()}), but:\n{ours}")
    return ours


def integrity(t, path_):
    """The real sqlite3 checks every page, cell and index of the file."""
    r = sqlite(t, path_, "PRAGMA integrity_check;")
    t.check(r.out.strip() == "ok", f"sqlite3 says {os.path.basename(path_)} is damaged:\n{r.out[:2000]}")


def crash(t, path_, point, sql, env=None):
    """Run sql in ./db with DB_CRASH=point; it must die at that point."""
    e = {"DB_CRASH": point}
    e.update(env or {})
    r = db(t, path_, sql, env=e, check=False)
    t.check(r.rc == -signal.SIGKILL and f"crash injected at {point}" in r.err,
            f"./db with DB_CRASH={point} should have been killed at {point}, but:\n{r}")
    return r


def kill_sqlite(t, path_, sql, marker="ready-to-die"):
    """Run sql in an interactive sqlite3, wait until it is done, and SIGKILL
    it: whatever it was in the middle of (an open transaction, an
    uncheckpointed WAL) stays on disk exactly as a crash would leave it."""
    s = t.spawn([sqlite_bin(), "-interactive", path_], name="sqlite3")
    s.sendline(sql)
    s.sendline(f"SELECT '{marker}';")
    s.expect(marker + r"\s*\n", timeout=60)
    s.close()
    time.sleep(0.05)


# ---------------------------------------------------------------- the REPL

PROMPT = r"db> $"


def repl(t, path_, env=None):
    s = t.spawn([os.path.join(t.root, "db"), "-interactive", path_], name="db", env=_env(env),
                fail_on=[r"not written yet", r"db: fatal"])
    s.expect(r"db> ", timeout=10)
    return s


def ask(s, sql, timeout=20):
    """Type one statement (or dot-command) and return what it printed."""
    s.sendline(sql)
    m = s.expect(r"(?s)(.*?)db> ", timeout=timeout)
    return m.group(1).replace("\r", "")


# ---------------------------------------------------------------- looking inside

def stats(err):
    m = re.search(r"^stats: (.*)$", err, re.M)
    if not m:
        raise Fail(f"no stats line (DB_STATS=1) in:\n{err}")
    return {k.strip(): int(v) for k, v in (p.rsplit(" ", 1) for p in m.group(1).split(", "))}


def header(path_):
    """The 100-byte database header, decoded."""
    with open(path_, "rb") as f:
        h = f.read(100)
    ps = struct.unpack(">H", h[16:18])[0]
    return {"magic": h[:16], "page_size": 65536 if ps == 1 else ps, "write_version": h[18],
            "read_version": h[19], "reserved": h[20], "fractions": tuple(h[21:24]),
            "change_counter": struct.unpack(">I", h[24:28])[0], "page_count": struct.unpack(">I", h[28:32])[0],
            "freelist_trunk": struct.unpack(">I", h[32:36])[0], "freelist_count": struct.unpack(">I", h[36:40])[0],
            "schema_cookie": struct.unpack(">I", h[40:44])[0], "schema_format": struct.unpack(">I", h[44:48])[0],
            "encoding": struct.unpack(">I", h[56:60])[0], "valid_for": struct.unpack(">I", h[92:96])[0],
            "raw": h}


def page(path_, n, page_size=None):
    page_size = page_size or header(path_)["page_size"]
    with open(path_, "rb") as f:
        f.seek((n - 1) * page_size)
        return f.read(page_size)


def page_type(path_, n):
    p = page(path_, n)
    return p[100 if n == 1 else 0]


def tree_depth(path_, root):
    """Levels from the root page of a B-tree to its leaves."""
    depth = 1
    n = root
    while True:
        p = page(path_, n)
        h = 100 if n == 1 else 0
        if p[h] in (10, 13):
            return depth
        n = struct.unpack(">I", p[h + 8:h + 12])[0]
        depth += 1


def rows(text):
    """Output lines split into fields."""
    return [line.split("|") for line in text.splitlines()]


def keeps_unique(root):
    """Does the project at root keep UNIQUE and PRIMARY KEY constraints as automatic
    indexes (08.07, an extension)? The finished track does; the core alone refuses them."""
    try:
        with open(os.path.join(root, "src", "schema.c"), errors="replace") as f:
            return "sqlite_autoindex_" in f.read()
    except OSError:
        return False


# ---------------------------------------------------------------- sqllogictest

def sqllogictest(t, have=(), scripts=None):
    """SQLite's own query corpus (tests/sqllogictest/runner.py) through ./db: the first
    records of each kept script, or every record with SLT=full in the environment. The
    real sqlite3 runs the same records first, a check of the runner itself (with SLT=full
    also with ./db's skips and rewrites, a check that those lose nothing). have: the
    runner's --have categories, SQL the engine has from module 08 on (join, aggregate,
    groupby, distinct, subquery, unique), which is then run, not skipped. scripts: files
    or directories to run instead of the kept scripts. Returns the summaries; fails with
    them on any failed record."""
    runner = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests", "sqllogictest", "runner.py")
    full = os.environ.get("SLT") == "full"
    passes = [["--engine", "sqlite3"]] + ([["--engine", "sqlite3", "--like-db"]] if full else [])
    passes.append(["--db", os.path.join(t.root, "db")])
    extra_args = (["--have", ",".join(have)] if have else []) + list(scripts or [])
    out = []
    for extra in passes:
        argv = [sys.executable, runner] + ([] if full else ["--quick"]) + extra + extra_args
        try:
            r = subprocess.run(argv, capture_output=True, text=True, timeout=1800)
        except subprocess.TimeoutExpired:
            raise Fail(f"sqllogictest did not finish in 30 minutes: {' '.join(argv[1:])}")
        out.append(f"$ {' '.join(argv[2:])}\n{r.stdout}{r.stderr}")
        if r.returncode != 0:
            raise Fail("sqllogictest failed (tests/sqllogictest/README.md):\n" + "\n".join(out))
    return "\n".join(out)
