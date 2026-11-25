#!/usr/bin/env python3
"""sqllogictest for the db track: SQLite's own query test corpus, run against ./db.

Internal, for authors: it checks the reference engine and is never shown to learners.
README.md (next to this file) says where the corpus comes from and under which licence.

    python3 tracks/db/tests/sqllogictest/runner.py [options] [file or dir ...]

    no files           the vendored subset, test/ next to this file
    --quick            the slice ./learn test db --ref runs: the first QUICK_RECORDS of each file
    --engine sqlite3   run the records through the real sqlite3 instead of ./db: a check
                       of the runner itself, which must pass every record
    --like-db          with --engine sqlite3: skip and rewrite exactly as for ./db, which
                       checks that the skips and the emulation below lose nothing
    --strict           no emulation (below): those statements are skipped instead
    --db PATH          the engine binary (default: ./db at the top of the track; make it first)
    --jobs N           files run at once (default: the number of CPUs)
    --show N           print the first N failures in full (default 10)
    --limit N          run only the first N records of each file
    --autocommit       every statement its own transaction, as the corpus was written
                       (some 40 times slower); by default a script runs in one BEGIN ... COMMIT
    --have a,b,...     categories the engine has now (db module 08): join, aggregate, groupby,
                       distinct, subquery, unique. SQL of a category named here is no longer
                       skipped for the look of it, and with unique, CREATE UNIQUE INDEX is sent
                       as written; what ./db itself reports as "not supported" is still a skip

What the corpus is: files of records. "statement ok|error" runs SQL that must succeed or
fail; "query <types> <sort> [label]" runs a SELECT whose values, formatted by type (I
integer, R real to 3 decimals, T text; NULL, "(empty)"), sorted as asked (nosort,
rowsort, valuesort) and above "hash-threshold" values hashed with MD5, must equal the
expected ones, and must agree with every other query of the same label. "skipif" and
"onlyif" name an engine (this one is "sqlite"); "halt" ends the file. The rules are
those of sqllogictest.c and slt_sqlite.c, the reference driver.

How it runs: one ./db process per file, every record fed through stdin in one go,
stderr merged into stdout. After each record the runner adds SELECT '~slt~ N'; so its
output can be cut back into records. ./db flushes its results before every error
message, so the merged stream keeps the order. Results are read from the shell's list
mode (| between columns, NULL as nothing): an empty field is taken as NULL. An empty
string prints the same and would show up as a failure; none of the kept scripts has one.

What is skipped, counted by reason and never as a failure: records for another
engine; SQL this engine does not have (subqueries, joins, aggregates, GROUP BY, CASE,
DISTINCT, CAST, compound SELECTs, views, functions it lacks, the bitwise operators,
INDEXED BY, ...), found by looking at the SQL, or reported by ./db as "... is not
supported"; and every later record that names a table or index such a skipped statement
would have created or changed (also when the statement has a skipif or onlyif line that
lets sqlite run it).

Emulation (off with --strict), for statements the engine lacks but whose effect is
plain: "INSERT INTO a SELECT * FROM b", when b has only been filled by literal INSERTs,
is replayed as those INSERTs into a; CREATE UNIQUE INDEX and DESC index columns become
an ordinary index (an index never changes an answer, and the corpus inserts no
duplicates: a uniqueness error the corpus expected would show up as a failure).
"""

import collections
import concurrent.futures
import hashlib
import os
import re
import subprocess
import sys
import tempfile
import time
from decimal import ROUND_HALF_UP, Decimal

HERE = os.path.dirname(os.path.abspath(__file__))
TRACK = os.path.dirname(os.path.dirname(HERE))
CORPUS = os.path.join(HERE, "test")

# The quick slice: the first records of every vendored file, each from its start (its
# CREATE and INSERTs, which a file of 1000-row tables takes some 6000 records for).
QUICK_RECORDS = 1500

MARK = "~slt~"
ENGINE_NAME = "sqlite"      # what skipif/onlyif match: the engine is held to SQLite's answers


# ---------------------------------------------------------------- the script format

class Record:
    def __init__(self, kind, line, conds):
        self.kind = kind            # statement, query, hash-threshold, halt
        self.line = line            # line number of the record's first line
        self.conds = conds          # [(skipif|onlyif, engine)]
        self.sql = ""
        self.ok = True              # statement: ok (True) or error (False)
        self.types = ""
        self.sort = "nosort"
        self.label = ""
        self.expected = []          # query: the lines after ----
        self.threshold = 0          # hash-threshold: its number


def parse(path):
    """The records of a script, as sqllogictest.c reads them: lines starting with # are
    comments wherever they are, a line of only spaces is blank, records end at a blank."""
    with open(path, encoding="latin-1") as f:
        raw = f.read().split("\n")
    lines = []                      # (line number, text) without comments
    for n, l in enumerate(raw, 1):
        l = l[:-1] if l.endswith("\r") else l
        if not l.strip():
            l = ""
        if l.startswith("#"):
            continue
        lines.append((n, l))
    recs = []
    i = 0
    while i < len(lines):
        if not lines[i][1]:
            i += 1
            continue
        block = []
        while i < len(lines) and lines[i][1]:
            block.append(lines[i])
            i += 1
        conds = []
        j = 0
        while j < len(block) and block[j][1].split()[0] in ("skipif", "onlyif"):
            tok = block[j][1].split()
            conds.append((tok[0], tok[1] if len(tok) > 1 else ""))
            j += 1
        if j >= len(block):
            continue
        n, head = block[j]
        tok = head.split()
        rest = [l for _, l in block[j + 1:]]
        r = Record(tok[0], n, conds)
        if r.kind == "statement":
            r.ok = len(tok) > 1 and tok[1] == "ok"
            if len(tok) < 2 or tok[1] not in ("ok", "error"):
                r.kind = "bad"
            r.sql = "\n".join(rest)
        elif r.kind == "query":
            r.types = tok[1] if len(tok) > 1 else ""
            r.sort = tok[2] if len(tok) > 2 else "nosort"
            r.label = tok[3][:20] if len(tok) > 3 else ""
            if "----" in rest:
                k = rest.index("----")
                r.sql, r.expected = "\n".join(rest[:k]), rest[k + 1:]
            else:
                r.sql = "\n".join(rest)
            if not r.types or set(r.types) - set("TIR") or r.sort not in ("nosort", "rowsort", "valuesort"):
                r.kind = "bad"
        elif r.kind == "hash-threshold":
            r.threshold = int(tok[1]) if len(tok) > 1 and tok[1].lstrip("-").isdigit() else 0
        elif r.kind != "halt":
            r.kind = "bad"
        recs.append(r)
    return recs


# ---------------------------------------------------------------- values, as slt_sqlite.c prints them

INT_RE = re.compile(r"^-?\d+$")
FLOAT_RE = re.compile(r"^-?(\d+\.\d*|\.\d+|\d+)([eE][-+]?\d+)?$|^-?(Inf|inf|NaN|nan)$")
NUM_PREFIX = re.compile(r"^\s*[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?")


def _atoi_prefix(s):
    """sqlite3Atoi64 on text: the integer at its start, clamped; 0 when there is none."""
    m = re.match(r"^\s*([-+]?)0*(\d*)", s)
    v = int(m.group(2) or "0")
    v = -v if m.group(1) == "-" else v
    return max(-2 ** 63, min(2 ** 63 - 1, v))


def _real_to_i64(r):
    if r != r:
        return 0
    if r <= -2.0 ** 63:
        return -2 ** 63
    if r >= 2.0 ** 63:
        return 2 ** 63 - 1
    return int(r)


def _as_c_int(v):
    """sqlite3_column_int: the low 32 bits of the 64-bit value."""
    v &= 0xFFFFFFFF
    return v - 2 ** 32 if v >= 2 ** 31 else v


def _fmt_real(r):
    """%.3f as sqlite3_snprintf prints it: halves round away from zero, no -0.000."""
    if r != r:
        return "NaN"
    if r in (float("inf"), float("-inf")):
        return "Inf" if r > 0 else "-Inf"
    s = str(Decimal(r).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))
    return "0.000" if s == "-0.000" else s


def format_value(field, typ):
    """One field of the shell's list output, formatted for the type character."""
    if field == "":
        return "NULL"
    if typ == "T":
        return "".join(c if " " <= c <= "~" else "@" for c in field)
    if INT_RE.match(field):
        v = int(field)
        return str(_as_c_int(v)) if typ == "I" else _fmt_real(float(v))
    if FLOAT_RE.match(field):
        r = float(field)
        return str(_as_c_int(_real_to_i64(r))) if typ == "I" else _fmt_real(r)
    if typ == "I":                      # text: the number at its start
        return str(_as_c_int(_atoi_prefix(field)))
    m = NUM_PREFIX.match(field)
    return _fmt_real(float(m.group(0)) if m else 0.0)


def md5_values(values):
    h = hashlib.md5()
    for v in values:
        h.update(v.encode("latin-1") + b"\n")
    return h.hexdigest()


# ---------------------------------------------------------------- what the engine lacks

STRING = re.compile(r"'(?:[^']|'')*'")
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
FUNCS = {"typeof", "length", "abs", "lower", "upper", "coalesce", "ifnull"}
AGGREGATES = {"count", "sum", "avg", "total", "group_concat", "min", "max"}
NOT_CALLS = {"in", "values", "exists", "and", "or", "not", "where", "select", "between", "is", "like",
             "on", "as", "from", "by", "key", "then", "else", "when", "case", "cast", "into", "table",
             "index", "view", "using", "join", "set", "null", "distinct", "all", "having", "limit", "offset",
             "glob", "escape", "collate", "default", "check", "unique", "references", "primary", "if"}
# (reason, pattern): SQL the engine has no support for, and the skip reason it is counted under
UNSUPPORTED = [
    ("subquery", re.compile(r"\(\s*SELECT\b|\bEXISTS\s*\(", re.I)),
    ("view", re.compile(r"\b(CREATE|DROP)\s+(TEMP\w*\s+)?VIEW\b", re.I)),
    ("trigger", re.compile(r"\bTRIGGER\b", re.I)),
    ("join", re.compile(r"\bJOIN\b", re.I)),
    ("GROUP BY", re.compile(r"\bGROUP\s+BY\b|\bHAVING\b", re.I)),
    ("compound SELECT", re.compile(r"\b(UNION|EXCEPT|INTERSECT)\b", re.I)),
    ("CASE", re.compile(r"\bCASE\b", re.I)),
    ("DISTINCT", re.compile(r"\bDISTINCT\b", re.I)),
    ("CAST", re.compile(r"\bCAST\s*\(", re.I)),
    ("CREATE TABLE AS", re.compile(r"^\s*CREATE\s+TABLE\b[^(]*\bAS\b", re.I)),
    ("INSERT OR / REPLACE", re.compile(r"^\s*(INSERT\s+OR\b|REPLACE\b|UPDATE\s+OR\b)", re.I)),
    ("REINDEX", re.compile(r"^\s*REINDEX\b", re.I)),
    ("ALTER TABLE", re.compile(r"^\s*ALTER\b", re.I)),
    ("INDEXED BY", re.compile(r"\bINDEXED\b", re.I)),
]
# the bitwise operators << >> & | ~ (not the || of concatenation), which the core lacks
BITWISE = re.compile(r"<<|>>|&|~|(?<!\|)\|(?!\|)")
# --have: a category the engine has, and the skip reasons it stops (see unsupported())
HAVE = {"join": {"join"}, "aggregate": {"aggregate"}, "groupby": {"GROUP BY"}, "distinct": {"DISTINCT"},
        "subquery": {"subquery"}, "unique": set()}
# a pattern is tried only when the SQL has one of its words (most SQL has none of them)
TRIGGERS = {"subquery": {"EXISTS"}, "view": {"VIEW"}, "trigger": {"TRIGGER"}, "join": {"JOIN"},
            "GROUP BY": {"GROUP", "HAVING"}, "compound SELECT": {"UNION", "EXCEPT", "INTERSECT"},
            "CASE": {"CASE"}, "DISTINCT": {"DISTINCT"}, "CAST": {"CAST"}, "CREATE TABLE AS": {"AS"},
            "INSERT OR / REPLACE": {"OR", "REPLACE"}, "REINDEX": {"REINDEX"}, "ALTER TABLE": {"ALTER"},
            "INDEXED BY": {"INDEXED"}}
# a name and "(": a function call, unless the word before says it is a table's or an index's name
CALL = re.compile(r"(?:\b(\w+)\s+)?\b([A-Za-z_]\w*)\s*\(")
AFTER_NAME = {"into", "table", "on", "index", "exists", "view", "from", "update"}
INSERT_SELECT = re.compile(r"^\s*INSERT\s+INTO\s+(\w+)\s+SELECT\s+\*\s+FROM\s+(\w+)\s*;?\s*$", re.I)
INSERT_VALUES = re.compile(r"^\s*INSERT\s+INTO\s+(\w+)(\s*(?:\([^()]*\)\s*)?VALUES\b.*)$", re.I | re.S)
CREATE_TABLE = re.compile(r"^\s*CREATE\s+TABLE\s+(\w+)\s*(\(.*)$", re.I | re.S)
CREATE_INDEX = re.compile(r"^(\s*CREATE\s+)(UNIQUE\s+)?(INDEX\s+\w+\s+ON\s+\w+\s*)\((.*)\)\s*;?\s*$", re.I | re.S)
TARGET = re.compile(r"^\s*(?:CREATE\s+(?:UNIQUE\s+)?(?:TEMP\w*\s+)?(?:TABLE|VIEW|INDEX|TRIGGER)\s+(?:IF\s+NOT\s+EXISTS\s+)?"
                    r"|INSERT\s+(?:OR\s+\w+\s+)?INTO\s+|REPLACE\s+INTO\s+|UPDATE\s+(?:OR\s+\w+\s+)?"
                    r"|DELETE\s+FROM\s+|DROP\s+(?:TABLE|VIEW|INDEX|TRIGGER)\s+(?:IF\s+EXISTS\s+)?)(\w+)", re.I)


def bare(sql):
    """The SQL with its strings blanked out, so keywords inside them do not count."""
    return STRING.sub("''", sql)


def names(sql):
    return {w.lower() for w in IDENT.findall(bare(sql))}


def _from_has_comma(b):
    """A join written as FROM a, b: a comma at the top level of a FROM clause."""
    for m in re.finditer(r"\bFROM\b", b, re.I):
        depth = 0
        rest = b[m.end():]
        for i, c in enumerate(rest):
            if c == "(":
                depth += 1
            elif c == ")":
                if depth == 0:
                    break
                depth -= 1
            elif depth == 0:
                if c == ",":
                    return True
                if re.match(r"(WHERE|ORDER|GROUP|LIMIT|HAVING|UNION|EXCEPT|INTERSECT)\b", rest[i:], re.I) and \
                        (i == 0 or not rest[i - 1].isalnum()):
                    break
    return False


def unsupported(sql, have=()):
    """Why ./db cannot run this SQL, or None. have: the --have categories, whose SQL it can."""
    b = bare(sql)
    words = [w.upper() for w in IDENT.findall(b)]
    seen = set(words)
    known = set().union(*(HAVE[h] for h in have))
    for reason, pat in UNSUPPORTED:
        if reason in known:
            continue
        if (seen & TRIGGERS[reason] or (reason == "subquery" and words.count("SELECT") > 1)) and pat.search(b):
            return reason
    if "join" not in known and "," in b and _from_has_comma(b):
        return "join"
    if any(c in b for c in "<>&|~") and BITWISE.search(b):
        return "bitwise operator"
    if re.match(r"\s*CREATE\b", b, re.I):
        return None                 # column types such as VARCHAR(10) are not calls
    for m in CALL.finditer(b):
        f = m.group(2).lower()
        if f in NOT_CALLS or (m.group(1) or "").lower() in AFTER_NAME:
            continue
        if f in AGGREGATES:
            if "aggregate" in known:
                continue
            return "aggregate"
        if f not in FUNCS:
            return "function " + f
    return None


# ---------------------------------------------------------------- one file

class Outcome:
    def __init__(self, path):
        self.path = path
        self.records = 0            # records of the kinds that run (statement, query)
        self.passed = 0
        self.failed = 0
        self.emulated = collections.Counter()   # how, for records that ran through emulation
        self.skipped = collections.Counter()    # reason -> count
        self.failures = []          # (line, what, detail)
        self.seconds = 0.0
        self.died = ""
        self.checked = False        # sqlite3's integrity_check passed on the file it left


class Plan:
    """What the runner sends for one file: per record, the statements, or why it is skipped."""

    def __init__(self, recs, emulate, skip_unsupported, limit=None, have=()):
        self.items = []             # (record, sql list or None, skip reason, emulation)
        tainted = {}                # lower name -> reason a later record is skipped
        filled = {}                 # table -> literal INSERT tails, while it has only those
        columns = {}                # table -> its CREATE TABLE column list
        count = 0
        for r in recs:
            if r.kind in ("statement", "query"):
                count += 1
                if limit is not None and count > limit:
                    break
            if r.kind in ("hash-threshold", "halt", "bad"):
                if r.kind == "halt" and self._conds(r):
                    continue            # a halt for another engine: "onlyif mssql" then "halt"
                self.items.append((r, None, None, None))
                if r.kind == "halt":
                    break
                continue
            skip = self._conds(r)
            sql = r.sql.strip().rstrip(";").strip()
            hit = names(sql) & set(tainted) if tainted and not skip else set()
            if hit:
                skip = tainted[sorted(hit)[0]]
            how = None
            out = [sql]
            if not skip and r.kind == "statement" and emulate:
                m = INSERT_SELECT.match(sql)
                ci = CREATE_INDEX.match(sql)
                if m:
                    dst, src = m.group(1).lower(), m.group(2).lower()
                    if src in filled and dst in columns and columns.get(src) == columns[dst]:
                        out = [f"INSERT INTO {m.group(1)}{tail}" for tail in filled[src]]
                        how = "INSERT ... SELECT replayed as INSERTs"
                elif ci and ((ci.group(2) and "unique" not in have) or re.search(r"\bDESC\b", ci.group(4), re.I)):
                    cols = re.sub(r"\s+(ASC|DESC)\b", "", ci.group(4), flags=re.I)
                    unique = ci.group(2) if "unique" in have else ""
                    out = [f"{ci.group(1)}{unique or ''}{ci.group(3)}({cols})"]
                    how = "DESC index made ordinary" if "unique" in have else "UNIQUE/DESC index made ordinary"
            if not skip and skip_unsupported and how is None:
                skip = unsupported(sql, have)
                if not skip and r.kind == "statement" and INSERT_SELECT.match(sql):
                    skip = "INSERT ... SELECT"
            if skip:
                self.items.append((r, None, skip, None))
                # what a skipped statement would have made or changed is missing, so later
                # records that name it are skipped too; not when skipif/onlyif skipped it,
                # which pick among versions of the same statement for different engines (a
                # statement sqlite runs, skipped for SQL this engine lacks, still counts)
                t = TARGET.match(sql) if r.kind == "statement" and not skip.startswith(("skipif ", "onlyif ")) \
                    else None
                if t and not re.match(r"^\s*DROP\s+VIEW\b", sql, re.I):
                    tainted.setdefault(t.group(1).lower(), "view" if skip == "view" else
                                       skip if skip.endswith("(earlier statement)") else skip + " (earlier statement)")
                continue
            self.items.append((r, out, None, how))
            if r.kind == "statement":
                self._track(sql, out, filled, columns)

    @staticmethod
    def _conds(r):
        for kind, eng in r.conds:
            match = eng.lower() == ENGINE_NAME
            if (kind == "skipif" and match) or (kind == "onlyif" and not match):
                return f"{kind} {eng.lower()}"
        return None

    @staticmethod
    def _track(sql, out, filled, columns):
        """Which tables have been filled only by literal INSERTs (what an INSERT ... SELECT
        replays), and each table's column list (a replay needs the same columns)."""
        ct = CREATE_TABLE.match(sql)
        iv = INSERT_VALUES.match(sql)
        ins = INSERT_SELECT.match(sql)
        t = TARGET.match(sql)
        if ct:
            name = ct.group(1).lower()
            columns[name] = " ".join(ct.group(2).lower().split())
            filled[name] = []
        elif iv and iv.group(1).lower() in filled:
            filled[iv.group(1).lower()].append(iv.group(2))
        elif ins and out != [sql]:          # replayed: the copy has the source's rows
            if ins.group(1).lower() in filled:
                filled[ins.group(1).lower()].extend(filled[ins.group(2).lower()])
        elif t and not re.match(r"^\s*CREATE\s+(UNIQUE\s+)?INDEX\b", sql, re.I):
            filled.pop(t.group(1).lower(), None)
            if re.match(r"^\s*DROP\s+TABLE\b", sql, re.I):
                columns.pop(t.group(1).lower(), None)


ERROR_LINE = re.compile(r"^(Error: |Parse error|Runtime error|db: fatal|db: .* not written yet)")


def _segments(text, n):
    """Cut the merged output at the markers: one list of lines per record sent."""
    segs = []
    cur = []
    for line in text.split("\n"):
        if line.startswith(MARK + " "):
            segs.append(cur)
            cur = []
            if len(segs) == n:
                break
        elif not line.startswith("stats:") and not line.startswith("db: rolled back"):
            cur.append(line)
    return segs, cur


def compare(r, lines, threshold, labels):
    """None if the query's output (list-mode lines) gives the expected values, else why not."""
    ncol = len(r.types)
    values = []
    for line in lines:
        fields = line.split("|")
        if len(fields) != ncol:
            return f"expected {ncol} column(s), got a row of {len(fields)}: {line[:200]!r}"
        values.extend(format_value(f, t) for f, t in zip(fields, r.types))
    if r.sort == "rowsort":
        rows = [values[i:i + ncol] for i in range(0, len(values), ncol)]
        rows.sort(key=lambda row: [v.encode("latin-1") for v in row])
        values = [v for row in rows for v in row]
    elif r.sort == "valuesort":
        values.sort(key=lambda v: v.encode("latin-1"))
    why = None
    if r.label or (threshold > 0 and len(values) > threshold):
        digest = md5_values(values)
        if r.label and labels.setdefault(r.label, digest) != digest:
            why = f"label {r.label} disagrees with an earlier query of the same label"
    if threshold > 0 and len(values) > threshold:
        got = f"{len(values)} values hashing to {md5_values(values)}"
        if not r.expected or r.expected[0] != got:
            return f"expected [{r.expected[0] if r.expected else ''}] got [{got}]"
        return why
    for i, (e, g) in enumerate(zip(r.expected, values)):
        if e != g:
            return f"value {i + 1}: expected [{e}] got [{g}] (expected {r.expected[:12]}, got {values[:12]})"
    if len(values) != len(r.expected):
        return f"expected {len(r.expected)} values, got {len(values)} (expected {r.expected[:12]}, got {values[:12]})"
    return why


def expected_digest(r):
    if r.expected and re.match(r"^\d+ values hashing to [0-9a-f]{32}$", r.expected[0]):
        return r.expected[0].split()[-1]
    return md5_values(r.expected)


TXN = re.compile(r"^\s*(BEGIN|COMMIT|END|ROLLBACK|SAVEPOINT|RELEASE|VACUUM|ATTACH|DETACH|PRAGMA)\b", re.I)


def run_file(path, argv, emulate=True, skip_unsupported=True, limit=None, timeout=600, autocommit=False,
             integrity=None, have=()):
    """Run one script through an engine (argv, plus the database file) and classify each record.

    Unless autocommit is set (or the script runs transactions or pragmas of its own), the
    whole script runs inside one BEGIN ... COMMIT: a commit per statement makes it some
    40 times slower and tests nothing the corpus is about. With integrity (a sqlite3),
    the real sqlite3 then checks the file the engine wrote."""
    o = Outcome(path)
    start = time.monotonic()
    plan = Plan(parse(path), emulate, skip_unsupported, limit, have)
    sent = []
    chunks = []
    for r, out, skip, how in plan.items:
        if out is None:
            continue
        for s in out:
            chunks.append(s + "\n;\n")
        chunks.append(f"SELECT '{MARK} {len(sent)}';\n")
        sent.append(r)
    wrap = not autocommit and not any(out and any(TXN.match(s) for s in out) for _, out, _, _ in plan.items)
    if wrap:
        chunks = ["BEGIN;\n"] + chunks + ["COMMIT;\n", f"SELECT '{MARK} end';\n"]
    with tempfile.TemporaryDirectory(prefix="slt-") as tmp:
        env = {k: v for k, v in os.environ.items() if not k.startswith("DB_")}
        dbfile = os.path.join(tmp, "slt.db")
        try:
            p = subprocess.run(argv + [dbfile], input="".join(chunks).encode("latin-1"),
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout, env=env)
            text, rc = p.stdout.decode("latin-1"), p.returncode
        except subprocess.TimeoutExpired as e:
            text, rc = (e.stdout or b"").decode("latin-1"), "timeout"
        segs, tail = _segments(text, len(sent) + wrap)
        complete = len(segs) == len(sent) + wrap
        if wrap and complete:
            end = segs.pop()
            if [l for l in end if l]:
                complete = False
                o.failed += 1
                o.failures.append((0, "COMMIT", "the final COMMIT: " + " / ".join(l for l in end if l)[:300]))
        elif wrap and len(segs) == len(sent):
            o.failed += 1
            o.failures.append((0, "COMMIT", f"the final COMMIT did not finish (exit {rc}): " + " / ".join(tail[-5:])))
        if complete and rc in (0, 1):   # 1: a script that hit an error, as some records mean to
            if integrity and os.path.exists(dbfile):
                q = subprocess.run([integrity, dbfile, "PRAGMA integrity_check;"], capture_output=True, text=True,
                                   timeout=timeout)
                if q.stdout.strip() != "ok" or q.returncode:
                    o.failed += 1
                    o.failures.append((0, "PRAGMA integrity_check", "sqlite3 says the file is damaged: " +
                                       (q.stdout + q.stderr).strip()[:500]))
                else:
                    o.checked = True
    if len(segs) < len(sent):
        o.died = f"{os.path.basename(argv[0])} stopped (exit {rc}) after {len(segs)} of {len(sent)} records:\n" + \
                 "\n".join(tail[-15:])
    threshold = 8                   # DEFAULT_HASH_THRESHOLD in sqllogictest.c
    labels = {}
    tainted = {}
    k = 0
    for r, out, skip, how in plan.items:
        if r.kind == "hash-threshold":
            threshold = r.threshold
            continue
        if r.kind == "halt":
            break
        if r.kind == "bad":
            o.records += 1
            o.failed += 1
            o.failures.append((r.line, "record", "a record this runner cannot read"))
            continue
        o.records += 1
        if out is None:
            o.skipped[skip] += 1
            if r.kind == "query" and r.label:
                labels.setdefault(r.label, expected_digest(r))
            continue
        seg = segs[k] if k < len(segs) else None
        k += 1
        if seg is None:
            o.failed += 1
            if k == len(segs) + 1:
                o.failures.append((r.line, r.sql, o.died))
            continue
        hit = names(r.sql) & set(tainted) if tainted else ()
        if hit:
            o.skipped[tainted[sorted(hit)[0]]] += 1
            continue
        errs = [l for l in seg if ERROR_LINE.match(l)]
        if errs and "not supported" in errs[0] and skip_unsupported:
            reason = re.sub(r"^Error: ", "", errs[0])
            reason = re.sub(r":.*$", "", reason)
            o.skipped[reason] += 1
            t = TARGET.match(r.sql) if r.kind == "statement" else None
            if t:
                tainted.setdefault(t.group(1).lower(), reason + " (earlier statement)")
            continue
        if r.kind == "statement":
            bad = None
            if r.ok and errs:
                bad = errs[0]
            elif r.ok and any(l for l in seg):
                bad = "unexpected output: " + " / ".join(l for l in seg if l)[:300]
            elif not r.ok and not errs:
                bad = "expected an error, the statement succeeded"
        else:
            bad = errs[0] if errs else compare(r, seg, threshold, labels)
        if bad:
            o.failed += 1
            o.failures.append((r.line, r.sql, bad))
        else:
            o.passed += 1
            if how:
                o.emulated[how] += 1
    o.seconds = time.monotonic() - start
    return o


# ---------------------------------------------------------------- many files

def corpus_files(paths):
    out = []
    for p in paths:
        if os.path.isdir(p):
            for d, _, fs in os.walk(p):
                out.extend(os.path.join(d, f) for f in fs if f.endswith(".test"))
        else:
            out.append(p)
    return sorted(out)


def engine_argv(engine, db=None):
    if engine == "db":
        path = db or os.path.join(TRACK, "db")
        if not os.access(path, os.X_OK):
            raise SystemExit(f"no engine at {path}: run make in {TRACK}")
        return [path]
    sys.path.insert(0, os.path.dirname(TRACK))
    sys.path.insert(0, os.path.dirname(os.path.dirname(TRACK)))
    import importlib.util
    spec = importlib.util.spec_from_file_location("db_track", os.path.join(TRACK, "track.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return [mod.sqlite_bin(), "-batch"]


def run(files, argv, emulate=True, skip_unsupported=True, jobs=None, limits=None, autocommit=False,
        integrity=None, processes=False, have=()):
    """Run every file (limits: path -> record limit) and return the outcomes, in file order.
    The runner's own work is Python's, so files go to processes when run as a command."""
    limits = limits or {}
    pool = concurrent.futures.ProcessPoolExecutor if processes else concurrent.futures.ThreadPoolExecutor
    with pool(jobs or os.cpu_count() or 4) as ex:
        futs = [ex.submit(run_file, f, argv, emulate, skip_unsupported, limits.get(f), autocommit=autocommit,
                          integrity=integrity, have=have) for f in files]
        return [f.result() for f in futs]


def summary(outcomes, seconds, show=10, root=CORPUS):
    """The results as text: totals, skips by reason, and the first failures in full."""
    rec = sum(o.records for o in outcomes)
    passed = sum(o.passed for o in outcomes)
    failed = sum(o.failed for o in outcomes)
    skipped = collections.Counter()
    emulated = collections.Counter()
    for o in outcomes:
        skipped.update(o.skipped)
        emulated.update(o.emulated)
    out = [f"sqllogictest: {len(outcomes)} files, {rec} records: {passed + failed} run, {passed} passed, "
           f"{failed} failed, {sum(skipped.values())} skipped ({seconds:.1f}s)"]
    checked = sum(o.checked for o in outcomes)
    if checked:
        out.append(f"  sqlite3's integrity_check: ok on the file each of {checked} scripts left")
    for how, n in emulated.most_common():
        out.append(f"  emulated  {n:7d}  {how} (passed)")
    for why, n in skipped.most_common():
        out.append(f"  skipped   {n:7d}  {why}")
    shown = 0
    for o in outcomes:
        name = os.path.relpath(o.path, root) if o.path.startswith(root) else o.path
        if o.failed:
            out.append(f"  FAILED    {o.failed:7d}  {name}")
        for line, sql, why in o.failures:
            if shown >= show:
                break
            shown += 1
            out.append(f"    {name}:{line}: {why}\n      {sql[:400]}".replace("\n      \n", "\n"))
    return "\n".join(out)


def main(args):
    import argparse
    ap = argparse.ArgumentParser(description="Run sqllogictest scripts against ./db (or sqlite3).")
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--engine", choices=["db", "sqlite3"], default="db")
    ap.add_argument("--like-db", action="store_true")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--db")
    ap.add_argument("--jobs", type=int)
    ap.add_argument("--show", type=int, default=10)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--autocommit", action="store_true")
    ap.add_argument("--have", default="")
    a = ap.parse_args(args)
    have = tuple(h for h in a.have.split(",") if h)
    for h in have:
        if h not in HAVE:
            ap.error(f"--have: unknown category {h!r} (one of {', '.join(HAVE)})")
    if a.quick:
        files = corpus_files(a.paths or [CORPUS])
        limits = {f: QUICK_RECORDS for f in files}
    else:
        files = corpus_files(a.paths or [CORPUS])
        limits = {f: a.limit for f in files} if a.limit else {}
    if not files:
        raise SystemExit("no .test files")
    as_db = a.engine == "db" or a.like_db
    argv = engine_argv(a.engine, a.db)
    t0 = time.monotonic()
    outcomes = run(files, argv, emulate=as_db and not a.strict, skip_unsupported=as_db, jobs=a.jobs,
                   limits=limits, autocommit=a.autocommit,
                   integrity=engine_argv("sqlite3")[0] if a.engine == "db" else None, processes=True, have=have)
    print(summary(outcomes, time.monotonic() - t0, a.show))
    return 1 if any(o.failed for o in outcomes) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
