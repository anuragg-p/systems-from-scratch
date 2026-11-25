#!/usr/bin/env python3
"""A seeded differential fuzzer for the db track: random schemas, rows and statements run
through ./db and through the real sqlite3, compared statement by statement.

Internal, for authors: it checks the reference engine and is never shown to learners.
README.md (next to this file) says what it generates, what it leaves out and why.

    python3 tracks/db/tests/fuzz/fuzz.py --seed S --n N --features LIST [options]

    --features LIST   from core,join,leftjoin,aggregate,groupby,distinct,subquery,unique:
                      the SQL the generator may write (core is always on; leftjoin brings
                      join, groupby brings aggregate)
    --engine db       ./db against sqlite3 (the default)
    --engine sqlite3  sqlite3 against itself under other plans: a check of the generator,
                      which must never write a query whose answer depends on the plan
    --db PATH         the engine binary (default: ./db at the top of the track)
    --sqlite PATH     the sqlite3 to compare with (default: the newest on this machine)
    --db-env K=V      run ./db with K=V in its environment (DB_CACHE_PAGES=2, say)
    --keep DIR        write every failing case (script, outputs, files) under DIR
    --shrink          cut the first failing case down and print the smallest script
    --case K          run case K only (as a report numbers it)
    --print           print the cases' scripts instead of running them
    --stats           also tally the errors both engines gave, by message
    --show N          print the first N failures (default 3)
    --jobs N          cases run at once (default: the number of CPUs)

A case is a script: CREATE TABLEs, INSERTs, then SELECTs mixed with UPDATEs, DELETEs,
INSERTs, CREATE INDEX and transactions. Both engines run it on fresh files, one statement
per line, each followed by SELECT '~fz~ N'; so the output can be cut back into statements.
For each statement both must fail or both succeed (the texts are not compared), and their
rows must agree: in order when the query's ORDER BY fixes the order completely, else as
multisets. Afterwards sqlite3 opens the file ./db wrote: PRAGMA integrity_check must say
ok, and both files must hold the same sqlite_schema rows and the same rows in every table.

The rule the generator keeps: a query's answer must follow from SQL's semantics alone,
never from the plan sqlite3 happens to choose. So it knows, for every expression, a superset
of the values it can take (the "facts" below), and it writes LIMIT, DISTINCT, GROUP BY,
min/max, sum and the rest only where those facts make the answer determined.
"""

import argparse
import concurrent.futures
import copy
import math
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TRACK = os.path.dirname(os.path.dirname(HERE))

FEATURES = ("core", "join", "leftjoin", "aggregate", "groupby", "distinct", "subquery", "unique")
REQUIRES = {"leftjoin": "join", "groupby": "aggregate"}
MARK = "~fz~"
TIMEOUT = 120
I64_MAX = 2 ** 63 - 1
I64_MIN = -2 ** 63
BIG = 2 ** 64

# Differences between the core engine and sqlite3 that are known and not fixed yet. The
# generator steers around each one; an entry goes when the engine is fixed (and the run
# then exercises it again).
KNOWN = {
    "float-to-text": "a real turned into text has 15 significant digits here, up to 17 in "
                     "sqlite3 3.54 (NOTES.md): no real that needs more is made into text",
    "abs-of-text": "abs('5') is 5 here, 5.0 in sqlite3 (abs of text or a blob is a real "
                   "there): abs() is given numbers only",
    "like-utf8": "'_' in LIKE matches one byte here, one character in sqlite3: LIKE is "
                 "given ASCII only",
    "text-with-nul": "a blob with a NUL byte or invalid UTF-8, made into text, prints and "
                     "measures differently (sqlite3 stops at the NUL): such blobs are never "
                     "made into text",
    "order-by-range": "ORDER BY 9 on a two-column result is an error in sqlite3, a constant "
                      "here; so are ORDER BY -1, ORDER BY +2 and terms sqlite3's parser folds "
                      "to an integer ('a' IS NULL, x AND 0): never written",
    "negate-min": "- -9223372036854775808 is folded to an integer here (it overflows), "
                  "9.2233720368547758e+18 in sqlite3: never written",
    "rem-of-text": "x % '1e3' divides by 1000 here, by 1 in sqlite3 (OP_Remainder reads a "
                   "text by its integer prefix, sqlite3VdbeIntValue): % is given no text or blob",
    "real-min-to-int": "the real -9.2233720368547758e+18 stored in an INTEGER or NUMERIC column "
                       "becomes the integer -9223372036854775808 here; sqlite3 keeps it a real "
                       "(sqlite3VdbeIntegerAffinity leaves both i64 extremes alone): never stored "
                       "there",
    "rowid-order-index": "WHERE b = 1 ORDER BY rowid, with an index on (b, z), comes out in z "
                         "order here: plan.c takes an equality lookup on an index's first "
                         "column to give rowid order, true only of a one-column index; on a "
                         "table with a multi-column index the rowid is never the whole ORDER BY "
                         "ascending",
    "is-empty-in": "'abc' IS (1 IN ()) is 1 in sqlite3, 0 here: its parser makes x IN () the "
                   "keyword false, and IS false is a truth test there (resolve.c, TK_TRUTH): "
                   "never written",
}
REAL_MIN = ("real", -2.0 ** 63)


# ---------------------------------------------------------------- values and literals
#
# A value is a pair: ("null", None), ("int", n), ("real", x), ("text", s), ("blob", b).

NULL = ("null", None)
INTS = [0, 1, -1, 2, 3, 5, 7, 10, 42, -7, 100, -100, 255, 1000, 2 ** 31 - 1, -2 ** 31, 2 ** 53,
        2 ** 53 + 1, I64_MAX, I64_MIN, I64_MAX - 1, I64_MIN + 1, 2 ** 62]
REALS = [0.0, 1.0, -1.0, 1.5, 2.5, -0.5, 0.25, 3.0, 7.0, 100.0, -2.25, 0.1, 1e20, -1e20, 1e15,
         2.0 ** 53, 2.0 ** 63, 1 / 3]
TEXTS = ["", "a", "A", "b", "abc", "ABC", "abd", "a b", "z", "x%", "_", "1", "01", "1.0", "1.5",
         " 1", "1 ", "1e3", "-0", "+7", ".5", "5.", "2", "7", "1a", "a1", "it's", "NULL", "0x10",
         "9223372036854775807", "9223372036854775808", "-9223372036854775808", "1e400",
         "\u00e9", "caf\u00e9"]
BLOBS = [b"", b"\x00", b"1", b"a", b"\x01\x02", b"\xff", b"abc", b"7"]
POOL = ([NULL] + [("int", n) for n in INTS] + [("real", x) for x in REALS] +
        [("text", s) for s in TEXTS] + [("blob", b) for b in BLOBS])

# Where a column's values come from: few values each, so that rows collide.
PROFILES = {
    "small": [("int", n) for n in (0, 1, 2, 3, -1, 5, 7)] +
             [NULL, ("text", "1"), ("real", 1.0), ("blob", b"1"), ("text", "2"), ("real", 2.5)],
    "dyadic": [("int", n) for n in (0, 1, 2, -3, 10)] +
              [("real", x) for x in (1.5, -0.5, 2.5, 0.25, 3.0, 1.0)] + [NULL, ("text", "2"), ("text", "1.5")],
    "text": [("text", s) for s in TEXTS[:24]] + [NULL, ("int", 1), ("blob", b"a")],
    "big": [("int", n) for n in (2 ** 62, 2 ** 62 + 1, I64_MAX, 2 ** 61, 2 ** 62 + 7)] + [NULL],
    "edge": [("int", n) for n in (I64_MAX, I64_MIN, I64_MAX - 1, I64_MIN + 1, 0, 1, -1)] +
            [("real", x) for x in (2.0 ** 63, -2.0 ** 63, 1e20)] +
            [("text", "9223372036854775807"), ("text", "9223372036854775808"), NULL],
    "mix": POOL,
}
# Values for columns a UNIQUE rule covers, so that most rows go in; a duplicate is drawn
# from the column's ordinary values now and then, on purpose.
FRESH = {"int": [("int", 500 + i) for i in range(80)],
         "text": [("text", "k%d" % i) for i in range(80)],
         "real": [("real", 500.5 + i) for i in range(80)]}
LOOKALIKES = [("int", 1), ("real", 1.0), ("text", "1"), ("blob", b"1"), ("text", "1.0"), ("int", 2),
              ("text", "2"), NULL]
LIKE_PATTERNS = ["%", "a%", "%a", "_", "a_", "%1%", "1%", "A%", "", "abc", "%b%", "_b%", "1", "1.5", "%.%"]


def lit(v):
    """The SQL literal for a value."""
    k, x = v
    if k == "null":
        return "NULL"
    if k == "int":
        return str(x)
    if k == "real":
        if math.isinf(x):
            return "1e999" if x > 0 else "-1e999"
        s = repr(x)
        return s if ("e" in s or "." in s) else s + ".0"
    if k == "text":
        return "'" + x.replace("'", "''") + "'"
    return "X'" + x.hex().upper() + "'"


def unquote(s):
    """A value from sqlite3's quote() of it."""
    if s == "NULL":
        return NULL
    if s.startswith("'"):
        return ("text", s[1:-1].replace("''", "'"))
    if s[:2] in ("X'", "x'"):
        return ("blob", bytes.fromhex(s[2:-1]))
    if re.fullmatch(r"-?\d+", s):
        return ("int", int(s))
    return ("real", float(s))


def printable(x):
    """A real both engines turn into the same text: 15 significant digits give it back, and
    it is not in [1e15, 1e17), which sqlite3 writes out in full (1000000000000000.0) and
    ./db's "%.15g" with an exponent (1.0e+15)."""
    return math.isinf(x) or (float("%.15g" % x) == x and not 1e15 <= abs(x) < 1e17)


def clean(b):
    """Bytes that are fine as text in both engines: no NUL, valid UTF-8."""
    if b"\x00" in b:
        return False
    try:
        b.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def affinity(decl):
    """A declared type's affinity, by SQLite's rules (datatype3.html, 3.1)."""
    d = decl.upper()
    if "INT" in d:
        return "INTEGER"
    if "CHAR" in d or "CLOB" in d or "TEXT" in d:
        return "TEXT"
    if "BLOB" in d or not d:
        return "BLOB"
    if "REAL" in d or "FLOA" in d or "DOUB" in d:
        return "REAL"
    return "NUMERIC"


AFFS = ("INTEGER", "TEXT", "REAL", "NUMERIC", "BLOB")
NUM_AFF = ("INTEGER", "REAL", "NUMERIC")


# ---------------------------------------------------------------- what sqlite3 makes of a value

class Store:
    """What sqlite3 makes of each value the generator writes: the value stored in a column
    of each affinity, what sum() adds for it, and the number arithmetic reads from it.
    Asked of sqlite3 itself, once, so the generator's facts are sqlite3's, not a model."""

    def __init__(self, sqlite):
        self.stored = {}    # (value, affinity) -> value
        self.contrib = {}   # value -> ("int", n) | ("approx", x) | None for NULL
        self.num = {}       # value -> ("int", n) | ("real", x) | NULL
        todo = list(POOL) + [v for vs in FRESH.values() for v in vs]
        for _ in range(4):
            todo = sorted({v for v in todo if v not in self.num}, key=repr)
            if not todo:
                break
            todo = self._ask(sqlite, todo)

    def _ask(self, sqlite, vals):
        lines = ["CREATE TABLE p(k INTEGER, i INTEGER, t TEXT, r REAL, n NUMERIC, b BLOB);"]
        for k, v in enumerate(vals):
            lines.append(f"INSERT INTO p VALUES ({k}, {', '.join([lit(v)] * 5)});")
        lines.append("SELECT k, quote(i), quote(t), quote(r), quote(n), quote(b) FROM p ORDER BY k;")
        lines.append(f"SELECT '{MARK}';")
        for k, v in enumerate(vals):
            lines.append(f"SELECT {k}, quote(sum(v)), quote(v + 0) FROM (SELECT {lit(v)} AS v);")
        with tempfile.TemporaryDirectory(prefix="fuzz-store-") as tmp:
            p = subprocess.run([sqlite, "-batch", os.path.join(tmp, "s.db")], input="\n".join(lines).encode(),
                               capture_output=True, timeout=TIMEOUT)
        if p.returncode or p.stderr:
            raise SystemExit("fuzz: sqlite3 failed on the value table:\n" + p.stderr.decode(errors="replace"))
        out = p.stdout.decode("utf-8", "surrogateescape").split("\n")
        cut = out.index(MARK)
        new = set()
        for line in out[:cut]:
            f = line.split("|")
            v = vals[int(f[0])]
            for a, q in zip(AFFS, f[1:]):
                s = unquote(q)
                self.stored[(v, a)] = s
                new.add(s)
        for line in out[cut + 1:]:
            if not line:
                continue
            f = line.split("|")
            v = vals[int(f[0])]
            s = unquote(f[1])
            self.contrib[v] = None if s == NULL else (("int", s[1]) if s[0] == "int" else ("approx", s[1]))
            self.num[v] = unquote(f[2])
        return list(new)

    def store(self, v, aff):
        return self.stored.get((v, aff))


ST = None       # the Store of this process


def _init_worker(store):
    global ST
    ST = store


# ---------------------------------------------------------------- facts about values
#
# Every expression carries an F: a superset of the values it can take, and what follows
# from that. The determinism rules are written against these.

ALLK = frozenset(("null", "int", "real", "text", "blob"))


class F:
    __slots__ = ("kinds", "vals", "aff", "messy", "bad", "wide", "maxabs")

    def __init__(self, kinds, vals=None, aff=None, messy=False, bad=False, wide=False, maxabs=0):
        self.kinds = frozenset(kinds)
        self.vals = vals            # frozenset of the exact values, or None if not known
        self.aff = aff              # the affinity a comparison sees, or None
        self.messy = messy          # may be a real that needs more than 15 digits as text
        self.bad = bad              # may be a blob that must not be made into text
        self.wide = wide            # may be text or a blob with non-ASCII bytes
        self.maxabs = maxabs        # a bound on the magnitude of its integer values

    @property
    def mixnum(self):
        """May hold an integer and a real that compare equal but print differently (1 and
        1.0): then which one DISTINCT, GROUP BY, min() or a tie keeps depends on the plan."""
        if self.vals is not None:
            ints = {x for k, x in self.vals if k == "int"}
            return any(k == "real" and math.isfinite(x) and x == math.floor(x) and int(x) in ints
                       for k, x in self.vals)
        return "int" in self.kinds and "real" in self.kinds

    @property
    def has_min(self):
        return self.maxabs >= 2 ** 63

    def nullable(self):
        return "null" in self.kinds

    def or_null(self):
        f = copy.copy(self)
        f.kinds = self.kinds | {"null"}
        f.vals = None if self.vals is None else self.vals | {NULL}
        return f

    def with_aff(self, aff):
        f = copy.copy(self)
        f.aff = aff
        return f


def vfacts(vals, aff=None):
    """The facts of a known set of values."""
    vals = frozenset(vals)
    messy = bad = wide = False
    m = 0
    for k, x in vals:
        if k == "real":
            messy = messy or not printable(x)
        elif k == "int":
            m = max(m, abs(x))
        elif k in ("text", "blob"):
            wide = wide or not x.isascii()
            bad = bad or (k == "blob" and not clean(x))
            n = ST.num.get((k, x))
            if n is None:
                m = BIG
            elif n[0] == "int":
                m = max(m, abs(n[1]))
    return F({k for k, _ in vals}, vals, aff, messy, bad, wide, m)


def union(fs):
    vals = None
    if all(f.vals is not None for f in fs):
        vals = frozenset().union(*[f.vals for f in fs])
    return F(frozenset().union(*[f.kinds for f in fs]), vals, None, any(f.messy for f in fs),
             any(f.bad for f in fs), any(f.wide for f in fs), max(f.maxabs for f in fs))


WILD = F(ALLK, None, None, True, True, True, BIG)
BOOL = F({"int"}, frozenset({("int", 0), ("int", 1)}), maxabs=1)
BOOLN = F({"int", "null"}, frozenset({("int", 0), ("int", 1), NULL}), maxabs=1)
COUNT = F({"int"}, None, maxabs=2 ** 30)
ROWID = F({"int"}, None, "INTEGER", maxabs=2 ** 20)


def textable(f):
    """Can be made into text the same way by both engines."""
    return not f.messy and not f.bad


def cmp_ok(a, b):
    """A comparison of a with b gives the same answer in both engines: when SQLite's rule
    makes one side text (TEXT affinity against no affinity), that side is not a real that
    prints differently. A BLOB column has an affinity (BLOB), so it is never converted."""
    if a.aff in NUM_AFF or b.aff in NUM_AFF:
        return True
    if a.aff == "TEXT" and b.aff is None:
        return not b.messy
    if b.aff == "TEXT" and a.aff is None:
        return not a.messy
    return True


def numkinds(f):
    """What arithmetic reads the values as: int and/or real."""
    if f.vals is not None:
        out = set()
        for v in f.vals:
            if v[0] in ("int", "real"):
                out.add(v[0])
            elif v[0] != "null":
                n = ST.num.get(v)
                out |= {"int", "real"} if n is None else ({n[0]} if n[0] != "null" else set())
        return out
    out = set()
    for k in f.kinds:
        if k in ("int", "real"):
            out.add(k)
        elif k in ("text", "blob"):
            out |= {"int", "real"}
    return out


def arith_facts(op, a, b):
    ka, kb = numkinds(a), numkinds(b)
    if not ka or not kb:
        return F({"null"}, frozenset({NULL}))
    kinds = set()
    if a.nullable() or b.nullable() or op in "/%":
        kinds.add("null")
    m = 0
    if "int" in ka and "int" in kb:
        m = {"+": a.maxabs + b.maxabs, "-": a.maxabs + b.maxabs, "*": a.maxabs * b.maxabs,
             "/": a.maxabs, "%": min(a.maxabs, b.maxabs)}[op]
        kinds.add("int")
        if m > I64_MAX or (op == "/" and a.has_min):
            kinds.add("real")           # overflow: done again in floating point
    if "real" in ka or "real" in kb:
        kinds.add("real")
    return F(kinds, None, None, messy="real" in kinds, maxabs=min(m, BIG))


def contrib(v):
    """What sum() adds for one value: ("int", n), ("approx", x), or None if unknown."""
    if v[0] == "int":
        return v
    if v[0] == "real":
        return ("approx", v[1])
    return ST.contrib.get(v, None)


def sum_info(f):
    """When sum/total/avg over these values is the same in every order: (the kinds of what
    is added, whether sum() may overflow), else None.

    1. every value adds an integer or a real that is a multiple of 1/4 under 2^20: every
       partial sum is exact, so the order cannot matter;
    2. every value adds an integer, all of one sign: the partial sums only grow, so sum()
       overflows in every order or in none (this is how overflow is fuzzed on purpose)."""
    if f.vals is None:
        if f.kinds <= {"int", "null"} and f.maxabs <= 2 ** 20:
            return ({"int"}, False)
        return None
    cs = [contrib(v) for v in f.vals if v[0] != "null"]
    if any(c is None for c in cs):
        return None
    kinds = {k for k, _ in cs}
    if all(math.isfinite(x) and abs(x) <= 2 ** 20 and (x * 4) == math.floor(x * 4) for _, x in cs):
        return (kinds, False)
    if kinds == {"int"} and (all(x >= 0 for _, x in cs) or all(x <= 0 for _, x in cs)):
        return (kinds, max(abs(x) for _, x in cs) >= 2 ** 39)
    return None


# ---------------------------------------------------------------- schema and data

COLNAMES = ["a", "b", "c", "d", "e", "x", "y", "z"]
DECLS = ["INTEGER", "TEXT", "REAL", "NUMERIC", "BLOB", ""]


class Col:
    def __init__(self, name, decl):
        self.name = name
        self.decl = decl
        self.aff = affinity(decl)
        self.ipk = False            # the INTEGER PRIMARY KEY, the rowid
        self.pk = False             # PRIMARY KEY on this column alone, not the rowid
        self.unique = False
        self.notnull = False
        self.default = None
        self.choices = []           # the values rows draw from
        self.vals = set()           # every value ever written (as stored)
        self.wild = False           # written from an expression: nothing is known
        self.used = set()           # fresh values drawn so far
        self._f = None

    def add(self, v):
        if not self.ipk:
            s = ST.store(v, self.aff)
            if s is None:
                self.wild = True
            else:
                self.vals.add(s)
            self._f = None

    def facts(self):
        if self.ipk:
            return ROWID
        if self.wild:
            return WILD.with_aff(self.aff)
        if self._f is None:
            self._f = vfacts(self.vals | ({NULL} if not self.vals else set()), self.aff)
        return self._f


class Tab:
    def __init__(self, name):
        self.name = name
        self.cols = []
        self.ipk_form = None        # "inline" or "table"
        self.cons = []              # table constraints: ("UNIQUE" | "PRIMARY KEY", [names])
        self.uindexes = []          # column lists of unique indexes
        self.indexes = []           # column lists of every CREATE INDEX
        self.nrows = 0              # rows inserted: a bound on its size
        self.ipk_used = []

    def col(self, name):
        return next(c for c in self.cols if c.name == name)

    def keycols(self):
        """Columns some uniqueness rule covers: an UPDATE gives them constants only."""
        names = {c.name for c in self.cols if c.ipk or c.pk or c.unique}
        for _, cs in self.cons:
            names |= set(cs)
        for cs in self.uindexes:
            names |= set(cs)
        return names

    def sql(self):
        defs = []
        for c in self.cols:
            d = c.name + (" " + c.decl if c.decl else "")
            if (c.ipk and self.ipk_form == "inline") or c.pk:
                d += " PRIMARY KEY"
            if c.notnull:
                d += " NOT NULL"
            if c.unique:
                d += " UNIQUE"
            if c.default is not None:
                d += " DEFAULT " + lit(c.default)
            defs.append(d)
        ipk = next((c for c in self.cols if c.ipk), None)
        if ipk and self.ipk_form == "table":
            defs.append(f"PRIMARY KEY({ipk.name})")
        for kind, cs in self.cons:
            defs.append(f"{kind}({', '.join(cs)})")
        return f"CREATE TABLE {self.name}({', '.join(defs)})"


def gen_table(r, name, feats, domain):
    t = Tab(name)
    names = r.sample(COLNAMES, r.randint(2, 5))
    for n in names:
        t.cols.append(Col(n, r.choice(DECLS)))
    if r.random() < 0.45:
        c = r.choice(t.cols)
        if r.random() < 0.4 and "id" not in names:
            c.name = "id"
        c.decl, c.aff, c.ipk = "INTEGER", "INTEGER", True
        t.ipk_form = "inline" if r.random() < 0.75 else "table"
    unique = "unique" in feats
    for c in t.cols:
        if c.ipk:
            continue
        c.notnull = r.random() < 0.08
        if r.random() < 0.08:
            c.default = r.choice(POOL[1:])
        prof = pick(r, [(5, "domain"), (2, "small"), (1.5, "dyadic"), (1.5, "text"), (0.4, "big"),
                        (0.5, "edge"), (1, "mix")])
        src = domain if prof == "domain" else PROFILES[prof]
        c.choices = r.sample(src, min(len(src), r.randint(2, 8)))
        if unique and r.random() < 0.15:
            c.unique = True
    if unique:
        free = [c for c in t.cols if not c.ipk]
        if not any(c.ipk for c in t.cols) and r.random() < 0.3 and free:
            if r.random() < 0.5:
                c = r.choice(free)
                c.pk = True
                if c.decl == "INTEGER":         # INTEGER PRIMARY KEY would be the rowid
                    c.decl = r.choice(["TEXT", "", "REAL", "NUMERIC", "BLOB", "INT"])
                    c.aff = affinity(c.decl)
            elif len(free) >= 2:
                t.cons.append(("PRIMARY KEY", [c.name for c in r.sample(free, 2)]))
        if r.random() < 0.25 and len(free) >= 2:
            t.cons.append(("UNIQUE", [c.name for c in r.sample(free, r.randint(1, 2))]))
    for c in t.cols:
        if c.default is not None:
            c.default = text_safe(c.default, c)
    return t


def pick(r, pairs):
    """A weighted choice among (weight, value) pairs."""
    total = sum(w for w, _ in pairs if w > 0)
    x = r.random() * total
    for w, v in pairs:
        if w <= 0:
            continue
        x -= w
        if x < 0:
            return v
    return pairs[-1][1]


# ---------------------------------------------------------------- expressions

class X:
    """An expression: a template with {} for its children (expressions or queries), and
    its facts. agg: holds an aggregate; sub: a subquery; err: may fail at run time."""
    __slots__ = ("t", "k", "f", "agg", "sub", "err", "op")

    def __init__(self, t, k=(), f=None, agg=False, sub=False, err=False, op=None):
        if op is None and (re.match(r"[a-z_]+\(", t) or "LIKE {}" in t):
            op = "func"             # a function call; SQLite makes LIKE one too
        self.t, self.k, self.f, self.op = t, tuple(k), f, op
        self.agg = agg or any(getattr(c, "agg", False) for c in self.k)
        self.sub = sub or any(isinstance(c, Query) or getattr(c, "sub", False) for c in self.k)
        self.err = err or any(getattr(c, "err", False) for c in self.k)

    def render(self, pin=False):
        return self.t.format(*[c.render(pin) for c in self.k])


def leaf(sql, f):
    return X(sql.replace("{", "{{").replace("}", "}}"), (), f)


def litx(v):
    x = leaf(lit(v), vfacts((v,)))
    x.op = "lit"
    return x


class Item:
    """One table of a FROM clause."""
    __slots__ = ("tab", "alias", "op", "on", "left", "idx")

    def __init__(self, tab, alias, idx):
        self.tab, self.alias, self.idx = tab, alias, idx
        self.op, self.on, self.left = None, None, False

    @property
    def qual(self):
        return self.alias or self.tab.name


class Ref:
    """A column (or the rowid) an expression may name, and how it may be written."""
    __slots__ = ("item", "col", "f", "depth", "bare", "rowid")

    def __init__(self, item, col, f, depth, bare, rowid=None):
        self.item, self.col, self.f, self.depth, self.bare, self.rowid = item, col, f, depth, bare, rowid

    def x(self, r):
        name = self.col.name if self.col else self.rowid
        if self.bare and r.random() < 0.6:
            return leaf(name, self.f)
        return leaf(self.item.qual + "." + name, self.f)

    def deeper(self):
        return Ref(self.item, self.col, self.f, self.depth + 1, False, self.rowid)


def refs_of(items, r):
    """What the expressions of a query may name in its own FROM."""
    count = {}
    for it in items:
        for c in it.tab.cols:
            count[c.name] = count.get(c.name, 0) + 1
    out = []
    for it in items:
        for c in it.tab.cols:
            f = c.facts()
            out.append(Ref(it, c, f.or_null() if it.left else f, 0, count[c.name] == 1))
        rid = ROWID.or_null() if it.left else ROWID
        out.append(Ref(it, None, rid, 0, len(items) == 1, r.choice(["rowid", "rowid", "_rowid_", "oid"])))
    return out


class Env:
    """Where an expression is written. mode "row": it names any column in refs (WHERE, ON,
    a plain query's result). mode "agg": an aggregate query's result, HAVING or ORDER BY,
    where it may call aggregates (whose arguments name argrefs, the query's own columns)
    and names only GROUP BY terms (groups, and the columns among them in refs)."""

    def __init__(self, g, refs, mode="row", groups=(), argrefs=(), sub=False, err=False, level=0, cost=1,
                 exclude=frozenset()):
        self.refs = list(refs)
        self.mode = mode
        self.groups = list(groups)
        self.argrefs = list(argrefs)
        self.sub = sub and g.has("subquery") and level < 2
        self.err = err
        self.level = level
        self.cost = cost            # how many times an expression here may be evaluated
        self.exclude = exclude      # tables a subquery here must not read


def gen_lit(g, like=None):
    """A literal; given the facts of what it will meet, often one of those values, so
    that conditions match rows. (Sets are sorted first: their order varies with Python's
    hash seed, and a case must not.)"""
    r = g.r
    if like is not None and like.vals and r.random() < 0.6:
        return litx(r.choice(sorted(like.vals, key=repr)))
    return litx(r.choice(g.domain) if r.random() < 0.6 else r.choice(POOL))


def gen_leaf(g, env):
    r = g.r
    opts = [(1, "lit")]
    if env.refs:
        opts.append((3, "ref"))
    if env.groups:
        opts.append((3, "group"))
    what = pick(r, opts)
    if what == "ref":
        return r.choice(env.refs).x(r)
    if what == "group":
        return r.choice(env.groups)
    return gen_lit(g)


def gen_value(g, env, d=2):
    """A value: a column, a literal, arithmetic, a function, a condition, an aggregate or a
    scalar subquery, as the Env allows."""
    r = g.r
    if d <= 0:
        return gen_leaf(g, env)
    opts = [(4, p_leaf), (1.5, p_arith), (0.7, p_concat), (0.4, p_neg), (1.5, p_func), (0.7, p_cond)]
    if env.mode == "agg":
        opts.append((4, p_agg))
    if env.sub:
        opts.append((0.6, p_scalar))
    for _ in range(6):
        x = pick(r, opts)(g, env, d)
        if x is not None and (env.err or not x.err):
            return x
    return gen_leaf(g, env)


def p_leaf(g, env, d):
    return gen_leaf(g, env)


def p_arith(g, env, d):
    a, b = gen_value(g, env, d - 1), gen_value(g, env, d - 1)
    op = g.r.choice(["+", "-", "*", "/", "%", "+", "-", "*"])
    if op == "%" and (a.f.kinds | b.f.kinds) & {"text", "blob"}:     # KNOWN rem-of-text
        op = "-"
    return X("({} %s {})" % op, (a, b), arith_facts(op, a.f, b.f))


def p_concat(g, env, d):
    a, b = gen_value(g, env, d - 1), gen_value(g, env, d - 1)
    if not (textable(a.f) and textable(b.f)):
        return None
    kinds = {"text"} | ({"null"} if a.f.nullable() or b.f.nullable() else set())
    return X("({} || {})", (a, b), F(kinds, wide=a.f.wide or b.f.wide))


def p_neg(g, env, d):
    a = gen_value(g, env, d - 1)
    if g.r.random() < 0.3:
        return X("(+ {})", (a,), a.f.with_aff(None))       # unary plus drops the affinity
    if folds(a) == I64_MIN:                                 # KNOWN negate-min
        return None
    kinds = numkinds(a.f) | ({"null"} if a.f.nullable() else set())
    if a.f.has_min:
        kinds.add("real")
    return X("(- {})", (a,), F(kinds, None, None, messy="real" in kinds, maxabs=a.f.maxabs))


def p_func(g, env, d):
    r = g.r
    a = gen_value(g, env, d - 1)
    fn = r.choice(["typeof", "length", "abs", "lower", "upper", "coalesce", "ifnull"])
    if fn == "typeof":
        names = {"null": "null", "int": "integer", "real": "real", "text": "text", "blob": "blob"}
        return X("typeof({})", (a,), vfacts({("text", names[k]) for k in a.f.kinds}))
    if fn == "length":
        if a.f.messy:
            return None
        return X("length({})", (a,), F({"int"} | ({"null"} if a.f.nullable() else set()), maxabs=2 ** 20))
    if fn == "abs":
        if not a.f.kinds <= {"int", "real", "null"}:          # KNOWN abs-of-text
            return None
        vals = None
        if a.f.vals is not None and not a.f.has_min:
            vals = frozenset((k, abs(x)) if k != "null" else NULL for k, x in a.f.vals)
        f = F(a.f.kinds, vals, None, a.f.messy, maxabs=a.f.maxabs)
        return X("abs({})", (a,), f, err=a.f.has_min)
    if fn in ("lower", "upper"):
        if not textable(a.f):
            return None
        return X(fn + "({})", (a,), F({"text"} | ({"null"} if a.f.nullable() else set()), wide=a.f.wide))
    more = [gen_value(g, env, d - 1) for _ in range(1 if fn == "ifnull" else r.randint(1, 2))]
    kids = [a] + more
    return X(fn + "(" + ", ".join(["{}"] * len(kids)) + ")", kids, union([k.f for k in kids]))


def p_cond(g, env, d):
    return gen_cond(g, env, d)


def gen_cond(g, env, d=2):
    """A condition (a value that is 1, 0 or NULL)."""
    r = g.r
    opts = [(4, c_cmp), (1, c_null), (0.7, c_between), (1.2, c_inlist), (0.8, c_like), (0.3, c_value)]
    if d > 0:
        opts += [(1.5, c_and), (1.5, c_or), (0.5, c_not)]
    if env.sub:
        opts += [(0.8, c_exists), (0.9, c_insub)]
    for _ in range(8):
        x = pick(r, opts)(g, env, d)
        if x is not None and (env.err or not x.err):
            return x
    return X("({} IS NULL)", (gen_leaf(g, env),), BOOL)


def c_value(g, env, d):
    return gen_value(g, env, d - 1)


def subject(g, env, d):
    """What a condition tests: mostly a column, so that conditions are about the rows."""
    if env.refs and g.r.random() < 0.6:
        return g.r.choice(env.refs).x(g.r)
    return gen_value(g, env, d)


def c_cmp(g, env, d):
    r = g.r
    a = subject(g, env, d - 1)
    b = gen_lit(g, a.f) if r.random() < 0.5 else gen_value(g, env, d - 1)
    if r.random() < 0.5:
        a, b = b, a
    if not cmp_ok(a.f, b.f):
        return None
    op = r.choice(["=", "=", "==", "!=", "<>", "<", "<=", ">", ">=", "IS", "IS NOT"])
    if op.startswith("IS") and b.t in ("({} IN ())", "({} NOT IN ())"):     # KNOWN is-empty-in
        op = "="
    return X("({} %s {})" % op, (a, b), BOOL if op.startswith("IS") else BOOLN)


def c_null(g, env, d):
    form = g.r.choice(["IS NULL", "IS NOT NULL", "ISNULL", "NOTNULL", "NOT NULL"])
    return X("({} %s)" % form, (subject(g, env, d - 1),), BOOL)


def c_between(g, env, d):
    a = subject(g, env, d - 1)
    b, c = gen_lit(g, a.f), (gen_lit(g, a.f) if g.r.random() < 0.5 else gen_value(g, env, 0))
    if not (cmp_ok(a.f, b.f) and cmp_ok(a.f, c.f)):
        return None
    return X("({} %sBETWEEN {} AND {})" % ("NOT " if g.r.random() < 0.3 else ""), (a, b, c), BOOLN)


def c_inlist(g, env, d):
    r = g.r
    a = subject(g, env, d - 1)
    items = [gen_lit(g, a.f) if r.random() < 0.75 else gen_value(g, env, 0) for _ in range(r.choice([0, 1, 2, 3, 4, 5]))]
    if a.f.aff == "TEXT" and any(i.f.messy for i in items):     # the left side's affinity is applied to each
        return None
    neg = "NOT " if r.random() < 0.3 else ""
    return X("({} %sIN (%s))" % (neg, ", ".join(["{}"] * len(items))), [a] + items, BOOLN)


def c_like(g, env, d):
    r = g.r
    a = subject(g, env, d - 1)
    if not textable(a.f) or a.f.wide:                           # KNOWN like-utf8
        return None
    p = litx(("text", r.choice(LIKE_PATTERNS))) if r.random() < 0.75 else gen_value(g, env, 0)
    if not textable(p.f) or p.f.wide:
        return None
    return X("({} %sLIKE {})" % ("NOT " if r.random() < 0.3 else ""), (a, p), BOOLN)


def c_and(g, env, d):
    return X("({} AND {})", (gen_cond(g, env, d - 1), gen_cond(g, env, d - 1)), BOOLN, op="and")


def c_or(g, env, d):
    return X("({} OR {})", (gen_cond(g, env, d - 1), gen_cond(g, env, d - 1)), BOOLN, op="or")


def c_not(g, env, d):
    return X("(NOT {})", (gen_cond(g, env, d - 1),), BOOLN)


def c_exists(g, env, d):
    q = gen_query(g, env, "exists")
    if q is None:
        return None
    return X("(%sEXISTS ({}))" % ("NOT " if g.r.random() < 0.4 else ""), (q,), BOOL)


def c_insub(g, env, d):
    a = gen_value(g, env, d - 1)
    q = gen_query(g, env, "in")
    if q is None or not cmp_ok(a.f, q.cols[0][0].f):
        return None
    return X("({} %sIN ({}))" % ("NOT " if g.r.random() < 0.4 else ""), (a, q), BOOLN)


def p_scalar(g, env, d):
    q = gen_query(g, env, "scalar")
    if q is None:
        return None
    f = q.cols[0][0].f
    return X("({})", (q,), f.or_null().with_aff(f.aff))


def p_agg(g, env, d):
    """An aggregate call whose answer does not depend on the order rows arrive in."""
    if env.mode != "agg":
        return None
    r = g.r
    fn = pick(r, [(2, "count*"), (2, "count"), (2, "sum"), (1, "total"), (1, "avg"), (2, "min"), (2, "max")])
    if fn == "count*":
        return X("count(*)", (), COUNT, agg=True)
    argenv = Env(g, env.argrefs, "row", level=env.level)
    arg = gen_value(g, argenv, 1) if r.random() < 0.3 else gen_leaf(g, argenv)
    if arg.err or arg.agg or arg.sub:
        return None
    dist = g.has("distinct") and r.random() < 0.25
    err = False
    if fn == "count":
        f = COUNT
    elif fn in ("min", "max"):
        if arg.f.mixnum:
            return None
        f = arg.f.or_null().with_aff(None)
    else:
        s = sum_info(arg.f)
        if s is None or (dist and arg.f.mixnum):
            return None
        sk, big = s
        if fn == "sum":
            kinds = ({"int"} if "int" in sk else set()) | ({"real"} if "approx" in sk else set()) | {"null"}
            f = F(kinds, None, None, messy="real" in kinds, maxabs=BIG if big else 2 ** 45)
            err = big
        else:
            # always a real; under rule 2 (big integers) it may be off in the last bit from
            # one order to another, so it is marked as if it could hold 1 and 1.0: no
            # DISTINCT over it and no ORDER BY that counts on it
            kinds = {"real"} | ({"null"} if fn == "avg" else set()) | ({"int"} if big else set())
            f = F(kinds, messy=True)
    name = "count" if fn == "count" else fn
    return X(name + "(" + ("DISTINCT " if dist else "") + "{})", (arg,), f, agg=True, err=err)


NULL_TESTS = {"({} IS NULL)": 0, "({} ISNULL)": 0, "({} IS NOT NULL)": 1, "({} NOTNULL)": 1, "({} NOT NULL)": 1}


def _lit_under_sign(x):
    while isinstance(x, X) and x.t in ("(- {})", "(+ {})"):
        x = x.k[0]
    return isinstance(x, X) and x.op == "lit" and x.t != "NULL"


def has_func(x):
    """A function call (LIKE is one) anywhere in x outside a subquery: SQLite's EP_HasFunc."""
    return isinstance(x, X) and (x.op == "func" or any(has_func(k) for k in x.k))


def folds(x):
    """The integer SQLite's parser turns x into, or None. An integer literal under any
    unary - or +; literal IS NULL, ISNULL, NOTNULL, NOT NULL, IS NOT NULL (parse.y,
    sqlite3PExprIsNull: 0 or 1); and AND with a side that folds to 0 when no function is
    involved (expr.c, sqlite3ExprAnd). In ORDER BY and GROUP BY such a term is the number
    of a result column, not a value."""
    if not isinstance(x, X):
        return None
    if x.op == "lit":
        return int(x.t) if re.fullmatch(r"-?\d+", x.t) else None
    if x.t in ("(- {})", "(+ {})"):
        v = folds(x.k[0])
        return None if v is None else (-v if x.t[1] == "-" else v)
    if x.t in NULL_TESTS and _lit_under_sign(x.k[0]):
        return NULL_TESTS[x.t]
    if x.t in ("({} IS {})", "({} IS NOT {})") and isinstance(x.k[1], X) and x.k[1].op == "lit" and \
            x.k[1].t == "NULL" and _lit_under_sign(x.k[0]):
        return 0 if x.t == "({} IS {})" else 1
    if x.op == "and" and (is_false(x.k[0]) or is_false(x.k[1])) and not has_func(x):
        return 0
    return None


def is_false(x):
    """False to SQLite's parser (EP_IsFalse): what folds to 0, or x IN (), which parse.y
    turns into false whatever x is."""
    return folds(x) == 0 or (isinstance(x, X) and x.t == "({} IN ())")


def gen_term(g, env, d):
    """An ORDER BY or GROUP BY expression that SQLite does not read as a column number
    (KNOWN order-by-range)."""
    for _ in range(6):
        x = gen_value(g, env, d)
        if folds(x) is None:
            return x
    return litx(("text", "k"))


def conj(terms):
    x = None
    for t in terms:
        x = t if x is None else X("({} AND {})", (x, t), BOOLN, op="and")
    return x


# ---------------------------------------------------------------- queries

class Query:
    """A SELECT, built as a tree so it can be rendered with its joins pinned and shrunk."""

    def __init__(self):
        self.distinct = False
        self.cols = []              # (X, alias) | ("*", None) | ("*", item)
        self.items = []
        self.key = None             # a WHERE term that keeps a scalar subquery to one row
        self.where = None
        self.group = []             # (X, how): how is "expr", ("num", i) or ("alias", name)
        self.having = None
        self.order = []             # (target, desc): target is X, ("num", i) or ("alias", name)
        self.limit = None           # (limit, offset or None, form)
        self.ordered = False        # ORDER BY fixes the order of the rows completely
        self.agg = False

    def render(self, pin=False):
        out = ["SELECT "]
        if self.distinct:
            out.append("DISTINCT ")
        cols = []
        for c, alias in self.cols:
            if isinstance(c, str):
                cols.append("*" if alias is None else alias.qual + ".*")
            else:
                cols.append(c.render(pin) + (alias if alias else ""))
        out.append(", ".join(cols))
        if self.items:
            out.append(" FROM ")
            for k, it in enumerate(self.items):
                if k:
                    op = it.op
                    if pin and op in (",", "JOIN", "INNER JOIN", "CROSS JOIN"):
                        op = "CROSS JOIN"
                    out.append(", " if op == "," else " " + op + " ")
                out.append(it.tab.name)
                if it.alias:
                    out.append((" AS " if (it.idx % 2 == 0) else " ") + it.alias)
                if it.on is not None:
                    out.append(" ON " + it.on.render(pin))
        w = [x for x in (self.key, self.where) if x is not None]
        if w:
            out.append(" WHERE " + " AND ".join(x.render(pin) for x in w))
        if self.group:
            out.append(" GROUP BY " + ", ".join(_target(t, pin) for t in
                                                (x if how == "expr" else how for x, how in self.group)))
        if self.having is not None:
            out.append(" HAVING " + self.having.render(pin))
        if self.order:
            out.append(" ORDER BY " + ", ".join(_target(t, pin) + (" DESC" if desc else "")
                                                for t, desc in self.order))
        if self.limit:
            n, off, form = self.limit
            if off is None:
                out.append(" LIMIT " + n)
            elif form == "comma":
                out.append(f" LIMIT {off}, {n}")
            else:
                out.append(f" LIMIT {n} OFFSET {off}")
        return "".join(out)

    def out_facts(self):
        """The facts of each result column, with * expanded."""
        out = []
        for c, alias in self.cols:
            if isinstance(c, str):
                for it in (self.items if alias is None else [alias]):
                    for col in it.tab.cols:
                        f = col.facts()
                        out.append(f.or_null() if it.left else f)
            else:
                out.append(c.f)
        return out


def _target(t, pin):
    if isinstance(t, tuple):
        return str(t[1] + 1) if t[0] == "num" else t[1]
    return t.render(pin)


def rows_of(t):
    return max(1, t.nrows)


def gen_from(g, pool, level, cap):
    r = g.r
    n = 1
    if g.has("join") and r.random() < (0.65 if level == 0 else 0.3):
        n = r.choice([2, 2, 2, 3, 3, 4]) if level == 0 else 2
    tabs = [r.choice(pool) for _ in range(n)]
    while len(tabs) > 1 and math.prod(rows_of(t) for t in tabs) > cap:
        tabs.pop()
    if math.prod(rows_of(t) for t in tabs) > cap:
        return None
    items = []
    for k, t in enumerate(tabs):
        alias = None
        if level > 0 or (t in tabs[:k]) or r.random() < 0.35:
            alias = g.alias("q" if level else "p")
        it = Item(t, alias, k)
        if k:
            ops = [(2, ","), (2, "JOIN"), (1, "INNER JOIN"), (1, "CROSS JOIN")]
            if g.has("leftjoin"):
                ops += [(4, "LEFT JOIN"), (1.5, "LEFT OUTER JOIN")]
            it.op = pick(r, ops)
            it.left = it.op.startswith("LEFT")
        items.append(it)
    return items


def gen_ons(g, items, outer_refs, own, level, cost, exclude):
    """The ON clauses: mostly an equality between the new table and one before it (on
    columns of any affinity, on purpose), sometimes more."""
    r = g.r
    anyleft = any(it.left for it in items)
    for k, it in enumerate(items):
        if k == 0:
            continue
        p = {",": 0.15, "CROSS JOIN": 0.3}.get(it.op, 0.85 if it.left else 0.7)
        if r.random() >= p:
            continue
        # a LEFT JOIN's ON may not name a table to its right; an inner one may (unless a
        # LEFT JOIN is in the way: then this keeps to the tables so far)
        allowed = set(range(k + 1)) if (it.left or anyleft) else set(range(len(items)))
        refs = [x for x in own if x.item.idx in allowed]
        env = Env(g, refs + outer_refs, "row", sub=True, level=level, cost=cost, exclude=exclude)
        terms = []
        mine = [x for x in refs if x.item is it]
        before = [x for x in refs if x.item.idx < k]
        if mine and before and r.random() < 0.85:
            pairs = [(r.choice(mine), r.choice(before)) for _ in range(8)]
            pairs = [(a, b) for a, b in pairs if cmp_ok(a.f, b.f)]
            # columns that hold some value in common, when there are such: rows then join
            share = [(a, b) for a, b in pairs if a.f.vals and b.f.vals and (a.f.vals & b.f.vals) - {NULL}]
            if share or pairs:
                a, b = (share or pairs)[0]
                op = r.choice(["=", "=", "=", "IS", "<", ">="])
                terms.append(X("({} %s {})" % op, (b.x(r), a.x(r)), BOOLN))
        if not terms or r.random() < 0.3:
            terms.append(gen_cond(g, env, 1))
        it.on = conj(terms)


def star_count(q):
    n = 0
    for c, alias in q.cols:
        if isinstance(c, str):
            n += sum(len(it.tab.cols) for it in (q.items if alias is None else [alias]))
        else:
            n += 1
    return n


def gen_query(g, outer, purpose, exclude=None):
    """A SELECT. outer: the Env it is written in (None for a statement). purpose: "top",
    "scalar" (one row of one column by construction), "in" (one column) or "exists"."""
    r = g.r
    level = outer.level + 1 if outer else 0
    exclude = outer.exclude if (outer and exclude is None) else (exclude or frozenset())
    cost = outer.cost if outer else 1
    outer_refs = [x.deeper() for x in outer.refs] if outer else []
    pool = [t for t in g.tables if t.name not in exclude]
    q = Query()
    if purpose == "scalar":
        return gen_scalar(g, q, outer_refs, pool, level, cost, exclude)
    cap = {0: 3000}.get(level, 400)
    cap = min(cap, 200000 // cost)
    items = []
    if pool and cap >= 1 and not (purpose == "top" and r.random() < 0.04):
        items = gen_from(g, pool, level, cap) or []
    if level > 0 and not items and purpose != "exists":
        return None
    q.items = items
    size = math.prod(rows_of(it.tab) for it in items) if items else 1
    own = refs_of(items, r)
    gen_ons(g, items, outer_refs, own, level, cost * size, exclude)
    rowenv = Env(g, own + outer_refs, "row", sub=True, level=level, cost=cost * size, exclude=exclude)
    if items and r.random() < 0.7:
        terms = [gen_cond(g, rowenv, 2) for _ in range(r.choice([1, 1, 1, 1, 2, 2, 3]))]
        if len(items) > 1 and r.random() < 0.5:     # a join condition in WHERE
            a, b = r.choice(own), r.choice(own)
            if a.item is not b.item and cmp_ok(a.f, b.f):
                terms.append(X("({} = {})", (a.x(r), b.x(r)), BOOLN))
        q.where = conj(terms)
    shapes = [(5, "plain")]
    if g.has("aggregate"):
        shapes.append((2.5 if purpose == "top" else 1.5, "agg"))
    if g.has("groupby") and items:
        shapes.append((3, "group"))
    shape = pick(r, shapes)
    want_limit = r.random() < (0.25 if purpose == "top" else 0.1)
    err = purpose == "top" and not want_limit
    if shape == "plain":
        gen_plain(g, q, purpose, rowenv, own, want_limit, err)
    elif shape == "agg":
        gen_agg_query(g, q, purpose, own, outer_refs, level, cost * size, exclude, want_limit, err)
    else:
        gen_group_query(g, q, purpose, own, outer_refs, level, cost * size, exclude, want_limit, err, rowenv)
    return q


def alias_for(g, i):
    r = g.r
    if r.random() < 0.3:
        return (" AS r%d" % i) if r.random() < 0.6 else (" r%d" % i)
    return ""


def gen_plain(g, q, purpose, env, own, want_limit, err):
    r = g.r
    env.err = err
    q.distinct = g.has("distinct") and r.random() < 0.3
    if purpose == "in":
        # often a column that holds NULL: x NOT IN a set with a NULL is never true
        nullable = [x for x in env.refs if x.depth == 0 and x.f.nullable()]
        q.cols = [(r.choice(nullable).x(r) if nullable and r.random() < 0.4 else gen_value(g, env, 1), "")]
    elif purpose == "exists":
        c = r.random()
        q.cols = [("*", None)] if (c < 0.3 and q.items) else [(litx(("int", 1)), "")] if c < 0.6 else \
            [(gen_value(g, env, 1), "")]
    else:
        n = r.choice([1, 1, 2, 2, 3, 4])
        for i in range(n):
            c = r.random()
            if c < 0.08 and q.items:
                q.cols.append(("*", None))
            elif c < 0.14 and len(q.items) > 1:
                q.cols.append(("*", r.choice(q.items)))
            else:
                q.cols.append((gen_value(g, env, 2), alias_for(g, i)))
    if q.distinct and any(f.mixnum for f in q.out_facts()):
        q.distinct = False
    ncols = star_count(q)
    if r.random() < 0.45 or want_limit:
        for _ in range(r.randint(1, 2)):
            if q.distinct or r.random() < 0.4:
                q.order.append((result_column(q, r.randrange(ncols), r), r.random() < 0.3))
            else:
                env.err = False
                q.order.append((gen_term(g, env, 1), r.random() < 0.3))
    if want_limit or r.random() < 0.3:
        total(q, own, ncols, r)
    if want_limit and q.ordered:
        q.limit = gen_limit(r)


def result_column(q, i, r):
    """ORDER BY naming result column i: by its number, or by its alias if it has one (when
    no * comes before it, its number is its place in q.cols)."""
    if all(not isinstance(c, str) for c, _ in q.cols) and q.cols[i][1] and r.random() < 0.5:
        return ("alias", q.cols[i][1].split()[-1])
    return ("num", i)


def total(q, own, ncols, r):
    """Make the ORDER BY fix the order: every table's rowid (each row is then one of a
    kind), or every result column when none of them holds both 1 and 1.0."""
    if not q.items:
        q.ordered = True
        return
    if not q.distinct and r.random() < 0.6:
        alone = not q.order and len(q.items) == 1
        for it in q.items:
            x = next(x for x in own if x.item is it and x.col is None)
            q.order.append((leaf(it.qual + ".rowid", x.f), alone and rowid_desc(it.tab)))
        q.ordered = True
        return
    if any(f.mixnum for f in q.out_facts()):
        return
    have = {t[1] for t, _ in q.order if isinstance(t, tuple)}
    for i in range(ncols):
        if i not in have:
            q.order.append((("num", i), False))
    q.ordered = True


def rowid_desc(t):
    """ORDER BY rowid alone on t must be DESC (KNOWN rowid-order-index): t has an index of
    several columns."""
    return any(len(cs) > 1 for cs in t.indexes) or any(len(cs) > 1 for _, cs in t.cons)


def gen_limit(r):
    n = str(r.choice([0, 1, 1, 2, 3, 5, 10, -1]))
    if r.random() < 0.05:
        n = r.choice(["'2'", "2.0", "1 + 1"])
    if r.random() < 0.35:
        return (n, str(r.choice([0, 1, 2, 5])), r.choice(["offset", "comma"]))
    return (n, None, None)


def gen_agg_query(g, q, purpose, own, outer_refs, level, cost, exclude, want_limit, err):
    """An aggregate query with no GROUP BY: one row, always."""
    r = g.r
    q.agg = True
    env = Env(g, outer_refs, "agg", argrefs=own, sub=True, err=err, level=level, cost=cost, exclude=exclude)
    n = 1 if purpose in ("in", "scalar") else r.choice([1, 1, 2, 3])
    for i in range(n):
        q.cols.append((gen_value(g, env, 2), alias_for(g, i)))
    if not any(c.agg for c, _ in q.cols):
        q.cols[0] = (X("count(*)", (), COUNT, agg=True), "")
    env.err = False
    if g.has("groupby") and r.random() < 0.3:
        q.having = gen_cond(g, env, 1)
    if r.random() < 0.2:
        q.order.append((("num", 0), r.random() < 0.5))
    q.distinct = g.has("distinct") and r.random() < 0.1
    q.ordered = True
    if want_limit or r.random() < 0.05:
        q.limit = gen_limit(r)


def gen_group_query(g, q, purpose, own, outer_refs, level, cost, exclude, want_limit, err, rowenv):
    """A GROUP BY query: only GROUP BY terms are named outside aggregates, and only those
    that cannot hold both 1 and 1.0 (which one a group shows would depend on the plan)."""
    r = g.r
    q.agg = True
    terms = []
    plain = Env(g, rowenv.refs, "row", level=level)
    for _ in range(r.choice([1, 1, 2, 3])):
        if r.random() < 0.75:
            ref = r.choice(own)
            terms.append((ref.x(r), ref))
        else:
            terms.append((gen_term(g, plain, 1), None))
    shown = [x for x, _ in terms if not x.f.mixnum]
    shown_refs = [ref for x, ref in terms if ref is not None and not x.f.mixnum]
    env = Env(g, shown_refs + outer_refs, "agg", groups=shown, argrefs=own, sub=True, err=err, level=level,
              cost=cost, exclude=exclude)
    n = 1 if purpose in ("in", "scalar") else r.choice([1, 2, 2, 3, 4])
    for i in range(n):
        if shown and r.random() < 0.4:
            q.cols.append((r.choice(shown), alias_for(g, i)))
        else:
            q.cols.append((gen_value(g, env, 2), alias_for(g, i)))
    q.group = []
    for x, _ in terms:
        how = "expr"
        hits = [i for i, (c, _) in enumerate(q.cols) if c is x]
        if hits and r.random() < 0.5:
            i = hits[0]
            alias = q.cols[i][1].split()[-1] if q.cols[i][1] else None
            how = ("alias", alias) if alias and r.random() < 0.5 else ("num", i)
        q.group.append((x, how))
    env.err = False
    if r.random() < 0.4:
        q.having = gen_cond(g, env, 1)
    q.distinct = g.has("distinct") and r.random() < 0.15 and not any(c.f.mixnum for c, _ in q.cols)
    if r.random() < 0.5 or want_limit:
        for _ in range(r.randint(1, 2)):
            if r.random() < 0.5:
                q.order.append((result_column(q, r.randrange(len(q.cols)), r), r.random() < 0.3))
            else:
                q.order.append((gen_term(g, env, 1), r.random() < 0.3))
    if want_limit or r.random() < 0.3:
        if q.distinct:
            if not any(c.f.mixnum for c, _ in q.cols):
                have = {t[1] for t, _ in q.order if isinstance(t, tuple)}
                q.order += [(("num", i), False) for i in range(len(q.cols)) if i not in have]
                q.ordered = True
        else:
            q.order += [(x, r.random() < 0.3) for x, _ in terms]     # each group has its own key
            q.ordered = True
    if want_limit and q.ordered:
        q.limit = gen_limit(r)


def gen_scalar(g, q, outer_refs, pool, level, cost, exclude):
    """A subquery that gives at most one row by construction: an aggregate with no GROUP
    BY, a lookup by rowid, a total ORDER BY with LIMIT 1, or no FROM at all."""
    r = g.r
    forms = [(2, "lookup"), (1.5, "first"), (0.4, "nofrom")]
    if g.has("aggregate"):
        forms.append((3, "agg"))
    form = pick(r, forms)
    cap = min(400, 200000 // cost)
    if form == "lookup" and pool and min(rows_of(t) for t in pool) > cap:
        form = "nofrom"
    if form != "nofrom":
        if not pool or cap < 1:
            form = "nofrom"
        else:
            q.items = gen_from(g, pool, level, cap) if form != "lookup" else \
                [Item(r.choice([t for t in pool if rows_of(t) <= cap]), g.alias("q"), 0)]
            if not q.items:
                form, q.items = "nofrom", []
    if form == "nofrom":
        env = Env(g, outer_refs, "row", level=level, cost=cost, exclude=exclude)
        q.cols = [(gen_value(g, env, 1), "")]
        q.ordered = True
        return q
    size = math.prod(rows_of(it.tab) for it in q.items)
    own = refs_of(q.items, r)
    gen_ons(g, q.items, outer_refs, own, level, cost * size, exclude)
    env = Env(g, own + outer_refs, "row", sub=True, level=level, cost=cost * size, exclude=exclude)
    if r.random() < 0.7:
        q.where = gen_cond(g, env, 1)
    if form == "agg":
        aenv = Env(g, outer_refs, "agg", argrefs=own, sub=True, level=level, cost=cost * size, exclude=exclude)
        x = gen_value(g, aenv, 2)
        if not x.agg:
            x = X("count(*)", (), COUNT, agg=True)
        q.cols = [(x, "")]
        q.agg = True
        if g.has("groupby") and r.random() < 0.15:
            q.having = gen_cond(g, aenv, 1)
    elif form == "lookup":
        it = q.items[0]
        ipk = next((c for c in it.tab.cols if c.ipk), None)
        name = ipk.name if (ipk and r.random() < 0.5) else r.choice(["rowid", "_rowid_", "oid"])
        keyenv = Env(g, outer_refs, "row", level=level)
        k = gen_leaf(g, keyenv) if (outer_refs and r.random() < 0.7) else \
            litx(r.choice([("int", n) for n in (0, 1, 2, 3, 5, 8)] + [("text", "2"), ("real", 3.0)]))
        q.key = X("({} = {})", (leaf(it.qual + "." + name, ROWID), k), BOOLN)
        q.cols = [(gen_value(g, env, 1), "")]
    else:
        q.cols = [(gen_value(g, env, 1), "")]
        if r.random() < 0.4:
            q.order.append((gen_term(g, env, 0), r.random() < 0.5))
        alone = not q.order and len(q.items) == 1
        for it in q.items:
            q.order.append((leaf(it.qual + ".rowid", ROWID), (alone and rowid_desc(it.tab)) or r.random() < 0.3))
        q.limit = ("1", None, None) if r.random() < 0.7 else ("1", str(r.choice([1, 2])), "offset")
    q.ordered = True
    return q


# ---------------------------------------------------------------- statements and a case

class Stmt:
    """One statement. ordered: its rows come in an order both engines must keep."""
    ordered = False
    kind = "raw"

    def __init__(self, sql):
        self.sql = sql

    def render(self, pin=False):
        return self.sql


class CreateTable(Stmt):
    kind = "create"

    def __init__(self, tab):
        self.tab = tab

    def render(self, pin=False):
        return self.tab.sql() + ";"


class CreateIndex(Stmt):
    kind = "index"

    def __init__(self, name, tab, cols, unique):
        self.name, self.tab, self.cols, self.unique = name, tab, cols, unique

    def render(self, pin=False):
        return f"CREATE {'UNIQUE ' if self.unique else ''}INDEX {self.name} ON {self.tab.name}({', '.join(self.cols)});"


class Insert(Stmt):
    kind = "insert"

    def __init__(self, tab, cols, rows):
        self.tab, self.cols, self.rows = tab, cols, rows      # cols: names, or None for all

    def render(self, pin=False):
        names = f"({', '.join(self.cols)})" if self.cols is not None else ""
        rows = ", ".join("(" + ", ".join(v.render(pin) for v in row) + ")" for row in self.rows)
        return f"INSERT INTO {self.tab.name}{names} VALUES {rows};"


class Update(Stmt):
    kind = "update"

    def __init__(self, tab, sets, where):
        self.tab, self.sets, self.where = tab, sets, where

    def render(self, pin=False):
        s = f"UPDATE {self.tab.name} SET " + ", ".join(f"{n} = {x.render(pin)}" for n, x in self.sets)
        return s + (f" WHERE {self.where.render(pin)}" if self.where is not None else "") + ";"


class Delete(Stmt):
    kind = "delete"

    def __init__(self, tab, where):
        self.tab, self.where = tab, where

    def render(self, pin=False):
        return f"DELETE FROM {self.tab.name}" + (f" WHERE {self.where.render(pin)}" if self.where is not None else "") + ";"


class Select(Stmt):
    kind = "select"

    def __init__(self, q):
        self.q = q
        self.ordered = q.ordered

    def render(self, pin=False):
        return self.q.render(pin) + ";"


class Gen:
    def __init__(self, r, feats, tables, domain):
        self.r, self.feats, self.tables, self.domain = r, feats, tables, domain
        self.n = 0

    def has(self, f):
        return f in self.feats

    def alias(self, p):
        self.n += 1
        return f"{p}{self.n}"


class Case:
    def __init__(self, seed, index, feats):
        self.seed, self.index, self.feats = seed, index, feats
        self.tables = []
        self.stmts = []

    def lines(self, pin=False):
        return [s.render(pin) for s in self.stmts]


def draw(g, col, key=False):
    r = g.r
    if key and r.random() < 0.85:
        kind = {"INTEGER": "int", "NUMERIC": "int", "REAL": "real", "TEXT": "text"}.get(col.aff) or \
            r.choice(["int", "text", "real"])
        free = [v for v in FRESH[kind] if v not in col.used]
        if free:
            v = free[0] if r.random() < 0.7 else r.choice(free)
            col.used.add(v)
            return v
    v = r.choice(col.choices) if col.choices else r.choice(g.domain)
    if v == NULL and col.notnull and r.random() < 0.9:
        v = next((c for c in col.choices if c != NULL), ("int", 0))
    return text_safe(v, col)


def text_safe(v, col):
    """A value both engines store alike in this column: a TEXT column turns a real into
    text (KNOWN float-to-text), so never one that needs more than 15 digits; an INTEGER or
    NUMERIC column never gets the real -2^63 (KNOWN real-min-to-int)."""
    if col.aff == "TEXT" and v[0] == "real" and not printable(v[1]):
        return ("real", 1.5)
    if col.aff in ("INTEGER", "NUMERIC") and v == REAL_MIN:
        return ("real", 1.5)
    return v


def store_ok(f, col):
    """Values with these facts may be written to col by an expression (see text_safe)."""
    if col.aff == "TEXT":
        return not f.messy
    if col.aff in ("INTEGER", "NUMERIC"):
        return "real" not in f.kinds if f.vals is None else REAL_MIN not in f.vals
    return True


def ipk_value(g, t):
    r = g.r
    x = r.random()
    if x < 0.45:
        return NULL
    if x < 0.9 or not t.ipk_used:
        n = r.randint(-5, 300)
        while n in t.ipk_used:
            n = r.randint(-5, 300)
        t.ipk_used.append(n)
        return ("int", n)
    if x < 0.96:
        return ("int", r.choice(t.ipk_used))                  # taken: the INSERT fails
    return r.choice([("text", "12"), ("real", 13.0), ("text", " 14"), ("text", "x"), ("real", 1.5)])


def gen_insert(g, t, nrows, subq=False):
    r = g.r
    cols = None
    if r.random() < 0.35:
        cols = [c.name for c in r.sample(t.cols, r.randint(1, len(t.cols)))]
    use = [t.col(n) for n in cols] if cols is not None else t.cols
    keys = t.keycols()
    rows = []
    for _ in range(nrows):
        row = []
        for c in use:
            if c.ipk:
                v = ipk_value(g, t)
                row.append(litx(v))
            elif subq and r.random() < 0.15:
                env = Env(g, [], "row", sub=True, level=0, exclude=frozenset({t.name}))
                x = p_scalar(g, env, 1)
                if x is None or not store_ok(x.f, c):
                    v = draw(g, c)
                    c.add(v)
                    row.append(litx(v))
                else:
                    c.wild, c._f = True, None
                    row.append(x)
            else:
                v = draw(g, c, c.name in keys)
                c.add(v)
                row.append(litx(v))
        rows.append(row)
    for c in t.cols:
        if c not in use:
            c.add(c.default if c.default is not None else NULL)
    t.nrows += nrows
    return Insert(t, cols, rows)


def table_env(g, t, sub=True):
    item = Item(t, None, 0)
    return Env(g, refs_of([item], g.r), "row", sub=sub, level=0, cost=rows_of(t), exclude=frozenset({t.name}))


def gen_update(g, t):
    """An UPDATE whose outcome does not depend on the order rows are visited in: a column
    some UNIQUE rule covers gets a constant only (then a clash is a clash in every order)."""
    r = g.r
    keys = t.keycols()
    env = table_env(g, t)
    sets = []
    for c in r.sample(t.cols, r.randint(1, min(2, len(t.cols)))):
        if c.ipk:
            v = r.choice([("int", r.randint(-5, 300)), ("int", r.choice(t.ipk_used or [1])), NULL])
            sets.append((c.name, litx(v)))
            continue
        x = r.random()
        others = [o for o in t.cols if o is not c and not o.ipk]
        if c.name in keys or x < 0.55:
            v = draw(g, c, c.name in keys and r.random() < 0.5)
            c.add(v)
            sets.append((c.name, litx(v)))
        elif x < 0.7 and others and store_ok(others[0].facts(), c):
            o = others[0]
            if o.wild:
                c.wild = True
            for v in list(o.vals):
                c.add(v)
            c._f = None
            sets.append((c.name, leaf(o.name, o.facts())))
        else:
            e = gen_value(g, Env(g, env.refs, "row", sub=x > 0.9, level=0, exclude=env.exclude), 1)
            if store_ok(e.f, c):
                c.wild, c._f = True, None
            else:
                v = draw(g, c)
                c.add(v)
                e = litx(v)
            sets.append((c.name, e))
    where = gen_cond(g, env, 2) if r.random() < 0.8 else None
    return Update(t, sets, where)


def gen_delete(g, t):
    r = g.r
    where = gen_cond(g, table_env(g, t), 2) if r.random() < 0.93 else None
    return Delete(t, where)


def gen_error(g):
    """A statement both engines must refuse."""
    r = g.r
    t = r.choice(g.tables)
    a = t.cols[0].name
    forms = ["nocol", "notable", "badqual", "aliashides", "arity", "setnocol"]
    if g.has("join"):
        forms.append("ambiguous")
    if g.has("aggregate"):
        forms += ["aggwhere", "nested"]
    if g.has("groupby"):
        forms += ["havingplain", "grouprange"]
    if g.has("subquery"):
        forms += ["sub2", "in2"]
    if g.has("leftjoin"):
        forms.append("leftright")
    f = r.choice(forms)
    two = t.cols[1].name if len(t.cols) > 1 else a
    sql = {
        "nocol": f"SELECT nosuch FROM {t.name};",
        "notable": "SELECT * FROM nosuch;",
        "badqual": f"SELECT zz.{a} FROM {t.name};",
        "aliashides": f"SELECT {t.name}.{a} FROM {t.name} AS w;",
        "arity": f"INSERT INTO {t.name} VALUES ({', '.join(['1'] * (len(t.cols) + 1))});",
        "setnocol": f"UPDATE {t.name} SET nosuch = 1;",
        "ambiguous": f"SELECT {a} FROM {t.name} AS w1, {t.name} AS w2;",
        "aggwhere": f"SELECT * FROM {t.name} WHERE count(*) > 1;",
        "nested": f"SELECT max(count(*)) FROM {t.name};",
        "havingplain": f"SELECT {a} FROM {t.name} HAVING {a} > 1;",
        "grouprange": f"SELECT {a}, count(*) FROM {t.name} GROUP BY 3;",
        "sub2": f"SELECT (SELECT {a}, {two} FROM {t.name});",
        "in2": f"SELECT 1 WHERE 1 IN (SELECT {a}, {two} FROM {t.name});",
        "leftright": f"SELECT 1 FROM {t.name} AS w1 LEFT JOIN {t.name} AS w2 ON w1.rowid = w3.rowid "
                     f"JOIN {t.name} AS w3;",
    }[f]
    return Stmt(sql)


def gen_case(seed, index, feats):
    """Case index of a run: the same seed, index and features always give the same case."""
    r = random.Random(f"fuzz {seed} {index} {','.join(f for f in FEATURES if f in feats)}")
    case = Case(seed, index, feats)
    domain = r.sample(POOL, r.randint(6, 14)) + r.sample(LOOKALIKES, r.randint(2, 5))
    many = "join" in feats or "subquery" in feats
    ntab = r.choice([1, 2, 2, 3, 3, 4] if many else [1, 1, 2, 3])
    tables = [gen_table(r, f"t{i}", feats, domain) for i in range(ntab)]
    g = Gen(r, feats, tables, domain)
    case.tables = tables
    setup = [CreateTable(t) for t in tables]
    nidx = 0

    def index_stmt(t, late):
        nonlocal nidx
        nidx += 1
        cols = [c.name for c in r.sample(t.cols, r.randint(1, min(2, len(t.cols))))]
        unique = "unique" in feats and r.random() < (0.5 if late else 0.3)
        if unique:
            t.uindexes.append(cols)
        t.indexes.append(cols)
        return CreateIndex(f"i{nidx}", t, cols, unique)

    for t in tables:
        for _ in range(r.choice([0, 0, 1, 1, 2])):
            setup.append(index_stmt(t, False))
    for t in tables:
        n = r.choice([0, 1, 2, 3, 5, 8, 10, 12, 15, 20, 25, 30, 40])
        constrained = bool(t.keycols())
        while n > 0:
            k = min(n, r.randint(1, 3) if constrained else r.randint(1, 10))
            setup.append(gen_insert(g, t, k))
            n -= k
    # the rest, in order: DML changes what the columns may hold, so it is made first and
    # every query after it is made against the final facts (a superset at every point)
    later = []
    ndml = r.randint(2, 7) if "unique" in feats else r.choice([0, 0, 1, 2, 3, 4])
    for _ in range(ndml):
        t = r.choice(tables)
        w = r.random()
        if w < 0.4:
            later.append(gen_insert(g, t, r.randint(1, 3), subq="subquery" in feats))
        elif w < 0.75:
            later.append(gen_update(g, t))
        else:
            later.append(gen_delete(g, t))
    if r.random() < 0.3:
        later.insert(r.randint(0, len(later)), index_stmt(r.choice(tables), True))
    queries = [Select(gen_query(g, None, "top")) for _ in range(r.randint(3, 9))]
    if r.random() < 0.3:
        queries.append(gen_error(g))
    for s in queries:
        later.insert(r.randint(0, len(later)), s)
    if later and r.random() < 0.3:
        i = r.randrange(len(later))
        j = r.randint(i + 1, len(later))
        later[i:j] = [Stmt("BEGIN;")] + later[i:j] + [Stmt("COMMIT;" if r.random() < 0.6 else "ROLLBACK;")]
    case.stmts = setup + later
    return case


# ---------------------------------------------------------------- running a case

ERR_DB = re.compile(r"^(Error: |db: fatal|db: .*not written yet)")
# sqlite3 3.54's shell shows the bytes 0x00-0x1f other than tab as ^@ .. ^_; ./db prints
# them as they are. A display convention of the shell, not an answer: ./db's output is
# shown the same way before it is compared.
CTRL = re.compile(r"[\x00-\x08\x0a-\x1f]")


def _caret(m):
    return "^" + chr(ord(m.group()) + 64)
ERR_SQ = re.compile(r"^(?:Parse error|Runtime error|Error) near line (\d+): (.*)$")


class Run:
    def __init__(self, who):
        self.who = who
        self.segs = []          # per statement: its output lines
        self.errs = []          # per statement: its error text, or None
        self.died = None        # why the run stopped early, if it did
        self.text = ""


def _script(lines, prefix=()):
    out = list(prefix)
    if prefix:
        out.append(f"SELECT '{MARK} -1';")
    for i, s in enumerate(lines):
        out.append(s)
        out.append(f"SELECT '{MARK} {i}';")
    return "\n".join(out) + "\n", len(out) - 2 * len(lines)


def _env():
    return {k: v for k, v in os.environ.items() if not k.startswith("DB_")}


def _split(text, n, run):
    """Cut the output at the markers into one list of lines per statement."""
    cur = []
    for line in text.split("\n"):
        if line.startswith(MARK + " "):
            i = int(line[len(MARK) + 1:])
            if i >= 0:
                run.segs.append(cur)
            cur = []
        else:
            cur.append(line)
    if len(run.segs) < n:
        run.died = run.died or f"{run.who} stopped after {len(run.segs)} of {n} statements"
    return cur


def run_db(binary, path, lines, env=None):
    run = Run("./db")
    data, _ = _script(lines)
    try:
        p = subprocess.run([binary, path], input=data.encode("utf-8"), stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=TIMEOUT, env=dict(_env(), **(env or {})))
        text, rc = p.stdout.decode("utf-8", "surrogateescape"), p.returncode
    except subprocess.TimeoutExpired as e:
        text, rc = (e.stdout or b"").decode("utf-8", "surrogateescape"), "timeout"
    run.text = text
    kept = [l for l in text.split("\n") if not l.startswith("stats:") and not l.startswith("db: rolled back")]
    tail = _split("\n".join(kept), len(lines), run)
    for i, seg in enumerate(run.segs):
        errs = [l for l in seg if ERR_DB.match(l)]
        run.errs.append(errs[0] if errs else None)
        run.segs[i] = [CTRL.sub(_caret, l) for l in seg if not ERR_DB.match(l)]
        if errs and re.search(r"internal error|db: fatal|not written yet", errs[0]):
            run.died = run.died or f"./db, statement {i}: {errs[0]}"
    if rc not in (0, 1):
        run.died = f"./db exited with {rc} after {len(run.segs)} statements: " + " / ".join(tail[-5:])
    return run


def run_sqlite(binary, path, lines, prefix=(), who="sqlite3"):
    run = Run(who)
    data, pre = _script(lines, prefix)
    try:
        p = subprocess.run([binary, "-batch", path], input=data.encode("utf-8"), stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, timeout=TIMEOUT, env=_env())
        out, err, rc = p.stdout.decode("utf-8", "surrogateescape"), p.stderr.decode("utf-8", "surrogateescape"), \
            p.returncode
    except subprocess.TimeoutExpired as e:
        out, err, rc = (e.stdout or b"").decode("utf-8", "surrogateescape"), "", "timeout"
    run.text = out + err
    _split(out, len(lines), run)
    run.errs = [None] * len(run.segs)
    for line in err.split("\n"):
        m = ERR_SQ.match(line)
        if m:
            i = (int(m.group(1)) - pre - 1) // 2
            if 0 <= i < len(run.errs):
                run.errs[i] = m.group(2)
    if rc not in (0, 1):
        run.died = f"{who} exited with {rc}"
    return run


PIN_B = ("PRAGMA automatic_index=OFF;",)
PIN_C = (".testctrl optimizations 0x7fffffff", "PRAGMA reverse_unordered_selects=ON;")


def run_case(case, cfg, keep=None):
    """Runs a case both ways and returns (difference text or None, counts)."""
    tmp = tempfile.mkdtemp(prefix=f"fuzz-{case.index}-")
    try:
        lines = case.lines()
        counts = {"statements": len(lines), "selects": sum(s.kind == "select" for s in case.stmts)}
        pa = os.path.join(tmp, "a.db")
        if cfg.engine == "db":
            runs = [run_db(cfg.db, pa, lines, cfg.db_env), run_sqlite(cfg.sqlite, os.path.join(tmp, "b.db"), lines)]
        else:
            runs = [run_sqlite(cfg.sqlite, pa, lines, who="sqlite3"),
                    run_sqlite(cfg.sqlite, os.path.join(tmp, "b.db"), case.lines(pin=True), PIN_B,
                               "sqlite3 (automatic_index=OFF, joins pinned)"),
                    run_sqlite(cfg.sqlite, os.path.join(tmp, "c.db"), lines, PIN_C,
                               "sqlite3 (optimizations off, reverse_unordered_selects)")]
        diff = None
        for k, other in enumerate(runs[1:]):
            diff = diff or compare_runs(case, runs[0], other, counts if k == 0 else {})
        files = [pa] + [os.path.join(tmp, n) for n in ("b.db", "c.db")][:len(runs) - 1]
        diff = diff or check_files(cfg.sqlite, case, files, runs)
        if diff and keep:
            d = os.path.join(keep, f"case-{case.seed}-{case.index}")
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, "script.sql"), "w", encoding="utf-8", errors="surrogateescape") as f:
                f.write("\n".join(lines) + "\n")
            for k, run in enumerate(runs):
                with open(os.path.join(d, f"out{k}.txt"), "w", encoding="utf-8", errors="surrogateescape") as f:
                    f.write(f"# {run.who}\n{run.text}")
            with open(os.path.join(d, "difference.txt"), "w", encoding="utf-8", errors="surrogateescape") as f:
                f.write(diff + "\n")
            for p in files:
                if os.path.exists(p):
                    shutil.copy(p, d)
        return diff, counts
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def check_files(sqlite, case, files, runs):
    """sqlite3 opens the first file (the one ./db wrote): integrity_check must say ok, and
    every file must hold the same schema rows and table rows."""
    lines = ["PRAGMA integrity_check;"]
    dbs = ["main"] + [f"o{k}" for k in range(1, len(files))]
    for k, p in enumerate(files[1:], 1):
        lines.append(f"ATTACH '{p}' AS o{k};")
    groups = []
    for d in dbs:
        lines.append(f"SELECT type, name, tbl_name, quote(sql) FROM {d}.sqlite_schema ORDER BY name;")
    groups.append(("sqlite_schema", list(range(len(lines) - len(dbs), len(lines)))))
    for t in case.tables:
        cols = ", ".join(f"quote({c.name})" for c in t.cols)
        for d in dbs:
            lines.append(f"SELECT quote(rowid), {cols} FROM {d}.{t.name} ORDER BY rowid;")
        groups.append((t.name, list(range(len(lines) - len(dbs), len(lines)))))
    run = run_sqlite(sqlite, files[0], lines, who="sqlite3 reading the files")
    if run.died or len(run.segs) < len(lines):
        return f"checking the files: {run.died}\n{run.text[-2000:]}"
    if run.errs[0] or run.segs[0] != ["ok"]:
        return (f"sqlite3's PRAGMA integrity_check on the file {runs[0].who} wrote: "
                f"{run.errs[0] or ' / '.join(run.segs[0])[:1500]}")
    for what, idx in groups:
        first = idx[0]
        for k in idx[1:]:
            if run.errs[first] != run.errs[k] and not (run.errs[first] and run.errs[k]):
                return f"{what}: readable in one file only ({run.errs[first] or run.errs[k]})"
            if run.segs[first] != run.segs[k]:
                return (f"the files differ after the script, in {what}:\n"
                        f"  {runs[0].who}'s file:\n{_lines(run.segs[first])}\n"
                        f"  {runs[idx.index(k)].who}'s file:\n{_lines(run.segs[k])}")
    return None


def _lines(seg, n=12):
    out = "\n".join("    " + repr(l)[1:-1] for l in seg[:n])
    if len(seg) > n:
        out += f"\n    ... ({len(seg)} lines)"
    return out or "    (nothing)"


# ---------------------------------------------------------------- comparing

FLOATY = re.compile(r"^-?(\d+\.\d*([eE][-+]?\d+)?|\d+[eE][-+]?\d+|Inf)$")


def same_field(a, b):
    """Two printed values are the same: equal text, or two reals equal to 12 digits
    (sqlite3 3.54 prints reals with up to 17 digits, ./db with 15). Unlike track.py's
    same_output an integer never equals a real: 5 against 5.0 is a difference of type."""
    if a == b:
        return True
    if not (FLOATY.match(a) and FLOATY.match(b)):
        return False
    x, y = float(a), float(b)
    if math.isinf(x) or math.isinf(y):          # Inf is near nothing but itself
        return x == y
    return x == y or abs(x - y) <= 1e-12 * max(abs(x), abs(y))


def same_line(a, b):
    fa, fb = a.split("|"), b.split("|")
    return len(fa) == len(fb) and all(same_field(x, y) for x, y in zip(fa, fb))


def _key(line):
    """Sorts reals by value, so the same real printed with 15 or 17 digits sorts alike."""
    return tuple(("f", float(f)) if FLOATY.match(f) else ("s", f) for f in line.split("|"))


def same_rows(la, lb, ordered):
    if len(la) != len(lb):
        return False
    if ordered:
        return all(same_line(x, y) for x, y in zip(la, lb))
    sa, sb = sorted(la, key=_key), sorted(lb, key=_key)
    if all(same_line(x, y) for x, y in zip(sa, sb)):
        return True
    if len(la) > 3000:
        return False
    rest = list(lb)                 # floats near a rounding edge: match greedily
    for x in la:
        j = next((j for j, y in enumerate(rest) if same_line(x, y)), None)
        if j is None:
            return False
        rest.pop(j)
    return True


def compare_runs(case, a, b, counts):
    if a.died or b.died:
        return f"{a.died or b.died}\n--- {a.who}:\n{a.text[-1500:]}\n--- {b.who}:\n{b.text[-1500:]}"
    for i, st in enumerate(case.stmts):
        ea, eb = a.errs[i], b.errs[i]
        if (ea is None) != (eb is None):
            return _report(case, i, a, b, "one fails, the other does not")
        if ea is not None:
            counts["errors alike"] = counts.get("errors alike", 0) + 1
            why = re.sub(r"\b[tqpw]\d+\b|: [\w.,  ]+$", "", eb)
            counts["error: " + why] = counts.get("error: " + why, 0) + 1
            continue
        if not same_rows(a.segs[i], b.segs[i], st.ordered):
            return _report(case, i, a, b, "different rows" + (" (in order)" if st.ordered else " (as multisets)"))
        counts["rows"] = counts.get("rows", 0) + len(a.segs[i])
    return None


def _report(case, i, a, b, what):
    st = case.stmts[i]

    def side(run):
        if run.errs[i] is not None:
            return f"error: {run.errs[i]}" + (f" (after {len(run.segs[i])} rows)" if run.segs[i] else "")
        return f"{len(run.segs[i])} rows\n{_lines(run.segs[i] if st.ordered else sorted(run.segs[i], key=_key))}"
    return (f"statement {i + 1}: {what}\n  {st.render()}\n"
            f"--- {a.who}: {side(a)}\n--- {b.who}: {side(b)}")


# ---------------------------------------------------------------- shrinking

def variants(case):
    """Smaller cases, roughly largest cut first: statements, rows, columns, clauses."""
    n = len(case.stmts)
    size = n // 2
    while size >= 1:
        for i in range(0, n, size):
            yield _with(case, case.stmts[:i] + case.stmts[i + size:])
        size //= 2
    for i, st in enumerate(case.stmts):
        if isinstance(st, Insert) and len(st.rows) > 1:
            for j in range(len(st.rows)):
                yield _with(case, case.stmts[:i] + [Insert(st.tab, st.cols, st.rows[:j] + st.rows[j + 1:])] +
                            case.stmts[i + 1:])
    for t in case.tables:
        for c in t.cols:
            if len(t.cols) > 1:
                yield drop_column(case, t, c)
    for i, st in enumerate(case.stmts):
        for v in stmt_variants(st):
            yield _with(case, case.stmts[:i] + [v] + case.stmts[i + 1:])


def _with(case, stmts):
    c = copy.copy(case)
    c.stmts = stmts
    return c


def drop_column(case, t, col):
    """The case without one column of a table: its values leave every INSERT, and what
    still names it fails in both engines."""
    k = t.cols.index(col)
    nt = copy.copy(t)
    nt.cols = t.cols[:k] + t.cols[k + 1:]
    nt.cons = [(kind, cs) for kind, cs in t.cons if col.name not in cs]
    stmts = []
    for st in case.stmts:
        if getattr(st, "tab", None) is not t:
            stmts.append(st)
        elif isinstance(st, CreateTable):
            stmts.append(CreateTable(nt))
        elif isinstance(st, Insert):
            if st.cols is None:
                stmts.append(Insert(nt, None, [row[:k] + row[k + 1:] for row in st.rows]))
            elif col.name in st.cols:
                j = st.cols.index(col.name)
                if len(st.cols) > 1:
                    stmts.append(Insert(nt, st.cols[:j] + st.cols[j + 1:], [row[:j] + row[j + 1:] for row in st.rows]))
            else:
                stmts.append(Insert(nt, st.cols, st.rows))
        elif isinstance(st, CreateIndex):
            if col.name not in st.cols:
                stmts.append(CreateIndex(st.name, nt, st.cols, st.unique))
        elif isinstance(st, Update):
            sets = [(n, x) for n, x in st.sets if n != col.name]
            if sets:
                stmts.append(Update(nt, sets, st.where))
        elif isinstance(st, Delete):
            stmts.append(Delete(nt, st.where))
        else:
            stmts.append(st)
    c = _with(case, stmts)
    c.tables = [nt if x is t else x for x in case.tables]
    return c


def cond_variants(x):
    """Simpler conditions: one side of an AND or an OR."""
    if isinstance(x, X) and x.op in ("and", "or"):
        for kid in x.k:
            yield kid
        for j, kid in enumerate(x.k):
            for v in cond_variants(kid):
                yield X(x.t, x.k[:j] + (v,) + x.k[j + 1:], x.f, op=x.op)


def stmt_variants(st):
    if isinstance(st, Select):
        for q in query_variants(st.q):
            yield Select(q)
    elif isinstance(st, (Update, Delete)) and st.where is not None:
        args = (st.tab, st.sets) if isinstance(st, Update) else (st.tab,)
        yield type(st)(*args, None)
        for w in cond_variants(st.where):
            yield type(st)(*args, w)
    if isinstance(st, Update) and len(st.sets) > 1:
        for j in range(len(st.sets)):
            yield Update(st.tab, st.sets[:j] + st.sets[j + 1:], st.where)


def query_variants(q):
    """Smaller queries that keep the rules: an ORDER BY goes only with its LIMIT, GROUP BY
    terms stay, a rowid lookup stays."""
    def mod(**kw):
        n = copy.copy(q)
        for k, v in kw.items():
            setattr(n, k, v)
        return n
    if q.where is not None:
        yield mod(where=None)
        for w in cond_variants(q.where):
            yield mod(where=w)
    if q.limit:
        yield mod(limit=None)
        if q.limit[1] is not None:
            yield mod(limit=(q.limit[0], None, None))
    if q.order and not q.limit:
        yield mod(order=[], ordered=not q.items or (q.agg and not q.group))
    if q.having is not None:
        yield mod(having=None)
    if q.distinct:
        yield mod(distinct=False)
    if len(q.items) > 1:
        yield mod(items=q.items[:-1])
    for k, it in enumerate(q.items):
        if it.on is not None:
            items = list(q.items)
            items[k] = copy.copy(it)
            items[k].on = None
            yield mod(items=items)
    if len(q.cols) > 1:
        group = [(x, "expr") for x, _ in q.group]
        for j in range(len(q.cols)):
            yield mod(cols=q.cols[:j] + q.cols[j + 1:], group=group)
    if not q.agg and not q.distinct:
        for j, (c, alias) in enumerate(q.cols):
            if isinstance(c, X):
                for kid in c.k:
                    if isinstance(kid, X):
                        yield mod(cols=q.cols[:j] + [(kid, alias)] + q.cols[j + 1:])


def shrink(case, cfg, diff, budget=900):
    """Cuts a failing case down while it still fails; returns (case, its difference, tries)."""
    tries = 0
    progress = True
    while progress and tries < budget:
        progress = False
        for v in variants(case):
            tries += 1
            d, _ = run_case(v, cfg)
            if d:
                case, diff, progress = v, d, True
                break
            if tries >= budget:
                break
    return case, diff, tries


# ---------------------------------------------------------------- the command

class Cfg:
    def __init__(self, engine, db, sqlite, db_env=None):
        self.engine, self.db, self.sqlite = engine, db, sqlite
        self.db_env = db_env or {}      # added to ./db's environment (--db-env)


def _version(path):
    try:
        out = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    m = re.match(r"(\d+)\.(\d+)\.(\d+)", out)
    return tuple(int(x) for x in m.groups()) if m else None


def find_sqlite():
    """The newest sqlite3 on this machine, as track.py's sqlite_bin() finds it."""
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
        raise SystemExit("fuzz: no sqlite3 found: install it, or set SQLITE3 or pass --sqlite")
    return best[1]


def _one(args):
    seed, index, feats, cfg, keep = args
    case = gen_case(seed, index, feats)
    try:
        diff, counts = run_case(case, cfg, keep)
    except Exception:           # a fault of the fuzzer itself is reported, not hidden
        import traceback
        diff, counts = "the fuzzer failed on this case:\n" + traceback.format_exc(), {}
    return index, diff, counts


def main(argv):
    ap = argparse.ArgumentParser(description="Differential fuzzing of ./db against sqlite3.")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--features", default="core")
    ap.add_argument("--engine", choices=["db", "sqlite3"], default="db")
    ap.add_argument("--db")
    ap.add_argument("--sqlite")
    ap.add_argument("--keep")
    ap.add_argument("--shrink", action="store_true")
    ap.add_argument("--case", type=int)
    ap.add_argument("--print", action="store_true", help="print the case scripts instead of running them")
    ap.add_argument("--jobs", type=int)
    ap.add_argument("--show", type=int, default=3)
    ap.add_argument("--stats", action="store_true", help="also tally the errors both engines gave")
    ap.add_argument("--db-env", action="append", default=[], metavar="NAME=VALUE",
                    help="run ./db with this in its environment (e.g. DB_CACHE_PAGES=2)")
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(errors="backslashreplace")      # outputs may hold any bytes
    feats = {f.strip() for f in a.features.split(",") if f.strip()} | {"core"}
    bad = feats - set(FEATURES)
    if bad:
        raise SystemExit(f"fuzz: unknown feature(s) {', '.join(sorted(bad))}; known: {', '.join(FEATURES)}")
    for f, needs in REQUIRES.items():       # a lesson's SQL needs the lessons before it
        if f in feats:
            feats.add(needs)
    db_env = dict(kv.partition("=")[::2] for kv in a.db_env)
    fl = ",".join(f for f in FEATURES if f in feats)
    sqlite = a.sqlite or find_sqlite()
    db = a.db or os.path.join(TRACK, "db")
    if a.engine == "db" and not a.print and not os.access(db, os.X_OK):
        raise SystemExit(f"fuzz: no engine at {db}: run make in {TRACK}")
    cfg = Cfg(a.engine, os.path.abspath(db), sqlite, db_env)
    store = Store(sqlite)
    _init_worker(store)
    indexes = [a.case] if a.case is not None else list(range(a.n))
    if a.print:
        for i in indexes:
            print(f"-- case {i} (seed {a.seed}, {fl})")
            print("\n".join(gen_case(a.seed, i, feats).lines()))
        return 0
    t0 = time.monotonic()
    jobs = 1 if len(indexes) == 1 else (a.jobs or os.cpu_count() or 4)
    work = [(a.seed, i, feats, cfg, a.keep) for i in indexes]
    results = []
    if jobs == 1:
        results = [_one(w) for w in work]
    else:
        with concurrent.futures.ProcessPoolExecutor(jobs, initializer=_init_worker, initargs=(store,)) as ex:
            results = list(ex.map(_one, work, chunksize=8))
    seconds = time.monotonic() - t0
    total = {}
    for _, _, c in results:
        for k, v in c.items():
            total[k] = total.get(k, 0) + v
    fails = sorted((i, d) for i, d, _ in results if d)
    against = "sqlite3 against itself under other plans" if a.engine == "sqlite3" else "./db against sqlite3"
    print(f"fuzz: {len(results)} cases, seed {a.seed}, features {fl}, {against}: "
          f"{total.get('statements', 0)} statements ({total.get('selects', 0)} SELECTs, "
          f"{total.get('errors alike', 0)} errors alike, {total.get('rows', 0)} rows compared), "
          f"{len(fails)} failing ({seconds:.1f}s)")
    if a.stats:
        errs = sorted(((v, k[7:]) for k, v in total.items() if k.startswith("error: ")), reverse=True)
        for v, k in errs[:20]:
            print(f"  {v:7d}  {k}")
    for i, d in fails[:a.show]:
        print(f"\ncase {i} (rerun: --seed {a.seed} --features {fl} --case {i}):\n{d}")
    if fails and a.shrink:
        i, d = fails[0]
        case = gen_case(a.seed, i, feats)
        small, d, tries = shrink(case, cfg, d)
        print(f"\nshrunk case {i} in {tries} tries to {len(small.stmts)} statements:\n")
        print("\n".join(small.lines()))
        print(f"\n{d}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
