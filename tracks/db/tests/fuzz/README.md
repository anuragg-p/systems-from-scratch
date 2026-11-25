# The db fuzzer

Internal, for authors: a seeded differential fuzzer. It writes random schemas, rows
and statements, runs them through the reference ./db and the real sqlite3, and fails
on the first answer they do not share. Learners never see it (tests/ is not part of
any project the site shows), and no lesson mentions it. It was written for module 08
(More SQL), whose joins, aggregates, GROUP BY, DISTINCT, subqueries and UNIQUE have far
more corners than its lesson tests can list; every failure it finds is cut down and
becomes a case in a lesson test.

## Running it

    python3 tracks/db/tests/fuzz/fuzz.py --seed 1 --n 300 --features join,leftjoin
                                  300 cases with the SQL of 08.01 and 08.02 (make ./db first)
        --shrink                  cut the first failing case down and print the smallest script
        --case K                  run case K alone (a report gives the command)
        --print                   print the cases' SQL instead of running them
        --keep DIR                keep each failing case: script, both outputs, both files
        --engine sqlite3          sqlite3 against itself under other plans (below)
        --db-env DB_CACHE_PAGES=2 run ./db with that in its environment (a sanitizer build
                                  and a tiny page cache, as the module's rules ask)
        --stats                   also count the errors both engines gave, by message

From a lesson test, track.py's fixture: `fuzz(t, features, n=300, seed=1)` runs it
against the reference ./db with --shrink and fails with the smallest failing script.
`FUZZ_N=20000` in the environment makes it a long run. Each 08 lesson's test ends with
300 cases, seeded, with the features that exist at that lesson: 08.01 join; 08.02
join,leftjoin; 08.03 the same at another seed (its tables' indexes are now looked up);
08.04 adds aggregate; 08.05 groupby,distinct; 08.06 subquery; 08.07 unique alone.

A case is a function of the seed, its number and the features: the same command always
writes the same SQL. 300 cases take a few seconds; cases run in parallel, one process
per engine per case, every statement of the case on one line of its stdin.

| feature | lesson | what the generator may write |
|---|---|---|
| core (always on) | 00-07 | one-table SELECT with WHERE, ORDER BY (expression, number, alias), LIMIT/OFFSET, `t.*`, table aliases, rowid/oid/_rowid_; SELECT with no FROM; INSERT, UPDATE, DELETE, CREATE INDEX, BEGIN with COMMIT or ROLLBACK; comparisons, AND/OR/NOT, + - * / % \|\|, IS [NOT] NULL, ISNULL, NOTNULL, [NOT] BETWEEN, [NOT] IN (list), [NOT] LIKE, unary - +, typeof length abs lower upper coalesce ifnull |
| join | 08.01 | 2-4 tables: comma, JOIN, INNER JOIN, CROSS JOIN, ON (also on a comma join, and naming a table to the right), self-joins with aliases, `x.*`, join columns of mixed affinity on purpose |
| leftjoin | 08.02 | LEFT [OUTER] JOIN with or without ON, WHERE on the null row (brings join) |
| aggregate | 08.04 | count(*), count, sum, total, avg, min, max over the whole input, with no FROM too |
| groupby | 08.05 | GROUP BY by expression, number or alias, HAVING with and without GROUP BY (brings aggregate) |
| distinct | 08.05 | SELECT DISTINCT, and agg(DISTINCT x) where aggregates are on |
| subquery | 08.06 | scalar, [NOT] IN, [NOT] EXISTS, correlated or not, one or two deep, in WHERE, ON, the result, HAVING, ORDER BY, and in INSERT, UPDATE and DELETE |
| unique | 08.07 | column UNIQUE, UNIQUE(a, b), PRIMARY KEY not on a lone INTEGER column, CREATE UNIQUE INDEX (before and after the rows), INSERTs and UPDATEs that break them |

## A case

1 to 4 tables of 2 to 5 columns, typed INTEGER, TEXT, REAL, NUMERIC, BLOB or nothing,
some with an INTEGER PRIMARY KEY (inline or as a table constraint), NOT NULL, DEFAULT
and indexes; 0 to 40 rows each. Values come from a pool built to collide: NULL, 1, 1.0,
'1', X'31' and '1.0' side by side, empty strings and blobs, negatives, the i64 edges and
their neighbours, 2^53, reals that need 17 digits, text that reads as a number (' 1',
'1e3', '0x10', '9223372036854775808'), and a little non-ASCII. Each column draws from a
handful of them, so rows repeat. Then 3 to 9 SELECTs among UPDATEs, DELETEs, INSERTs,
a late CREATE [UNIQUE] INDEX, sometimes a BEGIN ... COMMIT or ROLLBACK around some of
them, and now and then a statement both engines must refuse (no such column, ambiguous
name, aggregate in WHERE, HAVING without an aggregate, GROUP BY 3 of 2, a two-column
subquery, a LEFT JOIN ON naming a table to its right, too many VALUES).

## What is compared

- Each statement: both fail or both succeed (the messages are not compared); a failing
  SELECT's partial rows are not compared.
- Each SELECT's rows: in order when its ORDER BY fixes the order completely, else as
  multisets. A field is the same if the text is, or if both are finite reals equal to
  12 digits (sqlite3 3.54 prints 17 significant digits, ./db 15). Unlike track.py's
  same_output an integer never equals a real: 5 against 5.0 is a difference of type.
  sqlite3's shell shows the bytes 0x00-0x1f (not tab) as ^@ .. ^_; ./db prints them
  raw, so its output is shown the same way first (a convention of the shell).
- After the script, sqlite3 opens ./db's file: PRAGMA integrity_check must say ok, and
  both files must hold the same sqlite_schema rows (type, name, tbl_name, sql) and the
  same rows, rowids included, in every table.

## What it never writes, and why

Left out of module 08 by design-08 (./db refuses them, sqlite3 does not): NATURAL,
USING, RIGHT and FULL JOIN, parenthesised joins, subqueries in FROM, views, compound
SELECTs, window functions, group_concat, INSERT ... SELECT, CREATE TABLE AS, INSERT OR,
ON CONFLICT, UPDATE ... FROM, joins in UPDATE and DELETE; and CASE, CAST, scalar
min/max and the other functions the core has no use for.

Answers that depend on sqlite3's plan, which it chooses (join order, automatic indexes,
EXISTS turned into a join, which row comes first). For every expression the generator
keeps a superset of the values it can take, asked of sqlite3 itself (what each value
becomes stored under each affinity, what sum() adds for it, the number arithmetic reads
from it), and writes only what those values determine:

- LIMIT and OFFSET only under an ORDER BY that fixes the order: every table's rowid, or
  every result column; a scalar subquery only where it gives one row by construction (an
  aggregate with no GROUP BY, a lookup by rowid, LIMIT 1 under such an ORDER BY).
- A column, outside an aggregate, of an aggregate query only if it is a GROUP BY term.
- DISTINCT, a displayed GROUP BY term, min(), max() and sum(DISTINCT) only over values
  that never hold an integer and a real that are equal (1 and 1.0): which one is kept
  would depend on the order rows arrive in. No ORDER BY on an unselected expression
  under DISTINCT.
- sum, total and avg only over values where the order of adding cannot matter: every
  value an integer or a multiple of 1/4 under 2^20 (every partial sum is then exact), or
  every value an integer of one sign. The second is how integer overflow is fuzzed on
  purpose: the partial sums only grow, so sum() fails in every order or in none, and
  both engines must fail. Such a sum appears only in a top-level result with no LIMIT,
  where every row is evaluated whatever the plan; total() and avg() of it may differ in
  the last bit and are kept away from DISTINCT and ORDER BY.
- An expression that may fail at run time (abs(-9223372036854775808), such a sum) only in
  a top-level result with no LIMIT, never in WHERE or ON, where the rows it meets depend
  on the plan.
- An UPDATE gives a column a UNIQUE rule covers a constant only: then a clash is a clash
  in every order (`SET a = a + 1` over 1, 2, 3 fails or not with the order rows are
  visited in). A subquery in INSERT, UPDATE or DELETE never reads the table it changes.
- ORDER BY and GROUP BY terms are never what sqlite3's parser turns into an integer, as
  that is a column number there: 2, -1, +2, 'a' IS NULL, x NOTNULL on a literal,
  x AND 0, x AND (y IN ()) (parse.y, sqlite3PExprIsNull; expr.c, sqlite3ExprAnd).

Known differences in the core engine, each found by this fuzzer and not yet fixed (the
KNOWN table in fuzz.py; an entry goes when the engine is fixed):

| name | the difference | what the generator does |
|---|---|---|
| float-to-text | a real made into text has 15 digits here, 17 in sqlite3 3.54, which also writes 1e15..1e17 out in full (NOTES.md) | no real that prints differently is made into text (\|\|, LIKE, length, lower, upper, a TEXT column, a TEXT comparison) |
| abs-of-text | abs('5') is 5 here, 5.0 in sqlite3 | abs() gets numbers only |
| like-utf8 | '_' in LIKE matches a byte here, a character in sqlite3 | LIKE gets ASCII only |
| text-with-nul | a blob with a NUL or invalid UTF-8 made into text prints and measures differently | such blobs are not made into text |
| order-by-range | ORDER BY 9 of 2 columns (or -1, +2) is an error or a column in sqlite3, a constant here | never written |
| negate-min | `- -9223372036854775808` overflows into an integer here, is 9.2233720368547758e+18 in sqlite3 | never written |
| rem-of-text | `x % '1e3'` divides by 1000 here, by 1 in sqlite3 (OP_Remainder reads text by its integer prefix) | % gets no text or blob |
| real-min-to-int | the real -2^63 stored in an INTEGER or NUMERIC column becomes an integer here, stays a real in sqlite3 (sqlite3VdbeIntegerAffinity) | never stored there |
| rowid-order-index | `WHERE b = 1 ORDER BY rowid` with an index on (b, z) comes out in z order here: plan.c takes an equality lookup on an index's first column to give rowid order, true only of a one-column index | on a table with an index of several columns, the rowid alone is never an ascending ORDER BY |
| is-empty-in | `'abc' IS (1 IN ())` is 1 in sqlite3, 0 here: its parser makes `x IN ()` the keyword false, and `IS false` is a truth test (resolve.c, TK_TRUTH) | IS and IS NOT never have an empty IN on their right |

## Checking the generator: sqlite3 against itself

`--engine sqlite3` runs each case three times through sqlite3: as written; with `PRAGMA
automatic_index=OFF` and every inner join pinned in the order written with CROSS JOIN
(where that keeps the meaning); and with `.testctrl optimizations 0x7fffffff` (every
optimisation off) and `PRAGMA reverse_unordered_selects=ON`. Every run must agree with
the first, file included. A difference means the generator wrote a query whose answer
depends on the plan, and the generator is fixed, not the run. It is how the rules above
were found (the parser's folding of `'a' IS NULL` into a column number among them).

What it can and cannot see: breaking one rule at a time (a scratch script that
monkeypatches the generator) flags, in 600 cases with every feature, a missing total
ORDER BY under LIMIT in 73, a scalar subquery without its ORDER BY in 36 and a bare
column in a GROUP BY query in 11; DISTINCT, min() and max() over 1 and 1.0 in 4 of
4000. It never flags sums added in another order (0 of 4000): sqlite3's sum() is
compensated (Kahan-Babuska-Neumaier), so its own plans agree to the last digit. The sum
rule rests on the argument above, not on this check; ./db, which joins in the order
written, is where an order-dependent sum would show.

## Results (2026-11-25, Apple M4 Pro, sqlite3 3.54.1, 14 jobs)

- The generator, sqlite3 against itself: 22000 cases, 0 differences, 410 s. 12000 with
  every feature (seed 1000: 387252 statements, 72125 SELECTs, 845397 rows compared,
  37315 errors alike, 25 of them integer overflow; 244 s), and 1000 each (seed 2000) of
  core, join, join+leftjoin, aggregate, aggregate+groupby, distinct,
  aggregate+groupby+distinct, subquery, subquery+aggregate+groupby, unique.
- The core engine, ./db against sqlite3 with `--features core`: 5000 cases (seed 1,
  100502 statements, 29986 SELECTs), 0 differences, 42 s; 8000 more at seed 2, and 8000
  at seed 3 with DB_CACHE_PAGES=2, 0 differences; 3000 at seed 5 with ./db built with
  `-fsanitize=address,undefined` and DB_CACHE_PAGES=2, 0 differences and no reports.
  That is after steering around the KNOWN differences above, each of which these runs
  found first (a run before it showed it, and `--shrink` cut it to a few lines).
- About half the SELECTs return rows (the rest filter everything or read empty tables,
  on purpose); 6 to 10 statements in a hundred fail in both engines, mostly UNIQUE,
  NOT NULL and datatype mismatch, on purpose.

## Results with module 08 finished (2026-11-25, the same machine)

./db against sqlite3, not kept in the tests (the lesson slices are above):

- Every feature at once, the plain build: seeds 101 to 105, 20000 cases each, 100000
  in all: 3212504 statements, 600560 SELECTs, 7206732 rows compared, 304330 errors
  alike; 1750 s. 2 differences, both the core's (below, coalesce): seed 104 case 6270,
  seed 105 case 17330.
- The same, ./db built with `-fsanitize=address,undefined -fno-sanitize-recover=undefined`
  and run with `--db-env DB_CACHE_PAGES=2`: seeds 201 and 202, 10000 cases each:
  643144 statements, 120346 SELECTs, 1431885 rows compared, 0 differences and no
  sanitizer reports; 494 s.
- Each feature alone (with core, and what it brings), seed 301, 10000 cases each, 0
  differences but one: join (252256 statements, 108 s), join+leftjoin (251538, 123 s),
  aggregate (201817, 89 s), aggregate+groupby (202015, 77 s), distinct (203466, 84 s),
  subquery (252433, 119 s; its one difference is the core's coalesce again, case 4849,
  cut down to `SELECT ifnull(upper(1000), abs(b)) FROM t0` over b = -2^63), unique
  (259839, 117 s). About 60000 SELECTs each.
- The generator against sqlite3 itself, after the fixes below: 3000 cases with every
  feature (seed 1000), 0 differences, 102 s.

The first run (seeds 101 and 102, 40000 cases) gave 9 differences, none of them ./db's:
the generator had three faults, now fixed. A subquery's aggregate made the expression
around it an aggregate, so HAVING went on a query with none (an error in both, but
sqlite3 never saw it where its parser dropped the subquery: below). GROUP BY with
DISTINCT could ORDER BY an expression outside the result, whose value depends on which
of two equal rows DISTINCT keeps (sqlite3 groups by rowid without a sort when the rowid
is a GROUP BY term; ./db sorts). And text of unknown value, an 08.06 INSERT's subquery
('-9223372036854775808' || '.5'), stored in an INTEGER or NUMERIC column reads as the
real -2^63: KNOWN real-min-to-int by another road.

What the steering might hide, checked at the same time (1500 cases each, seed 77, a
scratch copy of the generator with one rule lifted, checked against sqlite3 itself
first): subqueries in an aggregate's argument; an inner join's ON naming a table to its
right while a LEFT JOIN is in the query; IN and scalar subqueries with no FROM; and
subqueries in INSERT, UPDATE and DELETE that read the table being changed: 0
differences each. Names from the query outside written bare: sqlite3 disagrees with
itself (the generator's facts are then wrong), and ./db's 7 differences were all of the
parser kind below. Error messages compared (3000 cases, seed 88, 9238 errors alike):
the only difference is the core's order of checks (NOTES.md, 08.07: a row that repeats
the rowid and leaves a NOT NULL column NULL is UNIQUE here, NOT NULL in sqlite3).

Differences these runs found in the core, not in KNOWN and not steered around (the
core is being fixed in its own pass):

- coalesce and ifnull evaluate every argument here (expr.c, eval_func); sqlite3 stops
  at the first that is not NULL, so `coalesce(0.0, abs(-9223372036854775808))` is 0.0
  there and "integer overflow" here. 3 cases in the runs above (2 of the 100000 with
  every feature, 1 of the 10000 with subquery; the last is plain core SQL).
- sqlite3's parser drops the left side of `x IN ()` and both sides of an AND with a
  constant false side (parse.y; expr.c, sqlite3ExprAnd) before names are bound, so an
  error inside them never shows: `SELECT x FROM t WHERE nosuch IN ()` is no rows there,
  "no such column: nosuch" here; the same with an ambiguous name, or HAVING on a query
  with no aggregate, in a subquery so dropped. The same folding as is-empty-in.

KNOWN reaches module 08 in one place: order-by-range. A one-table aggregate, GROUP BY,
DISTINCT or subquery reads ORDER BY with the core's order_target, so `SELECT count(*)
FROM t ORDER BY 2` (or `... GROUP BY a ORDER BY 3`, `ORDER BY -1`) is a constant here,
"1st ORDER BY term out of range" in sqlite3; a join, read by join_order_target, gives
sqlite3's error. And `GROUP BY 1 IS NULL`, which sqlite3's parser folds to 0, is "1st
GROUP BY term out of range" there and an expression here.
