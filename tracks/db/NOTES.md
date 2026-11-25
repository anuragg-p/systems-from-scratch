# Notes for the lesson writers

Everything here was run on the reference engine (Apple M4 Pro, macOS 26.6.2,
sqlite3 3.54.1 from Homebrew), and every "before" and "break it" was run on
a copy of the track with that lesson cut out or that one change made. The
outputs are pasted, trimmed only where it says so. Function names are given
instead of line numbers, which move.

## How the engine shows a hole

A cut region becomes `todo("NN.LL", "<title>");` (STUBS in track.py). It
prints `db: NN.LL: <title> not written yet` on stderr and exits with
status 3, before anything is written to the database file, so the file is
never damaged by a hole. With a lesson cut out, everything that does not
reach that code still works: with 05.02 cut, `SELECT * FROM t` works and
`SELECT * FROM t WHERE id = 5` stops at the stub.

Useful environment variables (all in main.c's header comment):

- `DB_STATS=1` prints counters at exit: pages read, cache hits/misses,
  evictions, pages written, fsyncs, journal pages, WAL frames,
  checkpoints, splits, append splits, merges.
- `DB_CRASH=<point>` (or `<point>:<n>`, the n-th time) SIGKILLs the process
  at a named point. Points: `journal-partial`, `journal-hot`, `db-partial`,
  `db-torn`, `db-written`, `before-delete`, `recover-partial` (rollback
  journal); `wal-partial`, `wal-torn`, `wal-written`, `checkpoint-partial`,
  `checkpoint-done` (WAL). With `PRAGMA journal_mode=off`, `db-partial` and
  `db-torn` and `db-written` apply too.
- `DB_CACHE_PAGES=<n>` sizes the page cache (default 500 pages, 2 MB,
  sqlite3's default). `DB_PAGE_SIZE=<n>` or `PRAGMA page_size=<n>` before
  the first write picks the page size of a new file.

The file is a real SQLite file: `sqlite3 file.db "PRAGMA integrity_check"`
is the best checker a lesson can point to. The journal and WAL are in
SQLite's formats too, so sqlite3 recovers our crashes and we recover its.

Facts worth knowing for the text:

- A dirty page stays in memory until COMMIT; the database file is only
  written by COMMIT. So ROLLBACK is "forget the dirty pages", and a
  transaction must fit in memory (sqlite3 spills instead). Dirty pages do
  not count against the cache size.
- The rollback journal is written at COMMIT, not as pages change: the
  originals are still in the database file then, so it reads them back
  with read_page(). sqlite3 journals as it goes.
- Inside BEGIN, each statement that may fail after writing keeps copies of
  the pages it changes (a statement savepoint) so it alone can be undone;
  a one-row INSERT checks everything first and needs none.
- Index B-trees are true B-trees: interior cells are entries. Table
  B-trees are B+trees: interior cells are only rowid signposts. Both are
  dictated by the file format (sqlite3's integrity_check counts index
  entries, interior ones included).
- Pages split in two, or into as many pages as the cells need (three when
  cells of 2000, 4000 and 2000 bytes meet on a 4096-byte page). A page is
  merged into a sibling only when it is empty, never for being under-full:
  enough for the format, but deletes leave half-empty pages (sqlite3
  rebalances).
- The planner re-checks the whole WHERE on every row the access path
  produces, so a plan can be slow but never wrong. Rowid bounds are
  widened to whole numbers for the same reason.
- Floats print as sqlite3 3.51 and older print them ("%!.15g"). sqlite3
  3.54 prints up to 17 digits (1.0/3 is 0.33333333333333332 there,
  0.333333333333333 here); the tests compare floats as numbers.
- The sqlite3 first on this machine's PATH is the Android SDK's 3.44.3;
  /usr/bin/sqlite3 is 3.51.0; the fixtures pick the newest, Homebrew's 3.54.1.

## 00 The workbench (labs, no regions)

### 00.01 How a database works

Regions: none. `make` builds `./db`; `./learn run db` runs `./db learn.db`.

What the learner sees (a terminal session, captured with `script`):

```
db: a SQL database, from scratch. Statements end with ;  .help for help
db> CREATE TABLE fruit(id INTEGER PRIMARY KEY, name TEXT, price REAL);
db> INSERT INTO fruit(name, price) VALUES ('apple', 0.5), ('pear', 0.75);
db> SELECT name, price
   ...>   FROM fruit ORDER BY price DESC;
pear|0.75
apple|0.5
db> .tables
fruit
db> SELECT * FROM nosuch;
Error: no such table: nosuch
db> .exit
```

One-shot mode: `./db learn.db "SELECT * FROM fruit"` prints `1|apple|0.5`
and `2|pear|0.75`. Dot-commands work one-shot too (`./db learn.db .schema`).
A script on stdin exits 1 if any statement failed; the REPL at a terminal
exits 0.

Break it (verified): point it at a file that is not a database:
`./db Makefile "select 1"` prints `Error: file is not a database: Makefile`
and exits 1. Then `sqlite3 learn.db "PRAGMA integrity_check; SELECT * FROM
fruit"` reads our file: `ok`, `1|apple|0.5`, `2|pear|0.75`.

### 00.02 Measuring a database

Regions: none. `./learn bench db` (it runs `bench/bench.py`; `--quick`,
`--wal`, `--repeats N`, `--rows N`, `--json FILE`). A full run takes about
40 s. The real table from a full run is in 07.01 below. `--quick` (2000
rows, one run) shows what small runs do: start-up dominates (db 2.7 ms,
sqlite3 4.6 ms per process), and the autocommit row swings widely (one quick
run gave sqlite3 943 ops/s, a full run 3,059).

Break it (verified, see 07.01): make `sys_fsync()` in util.c return 0
without syncing and rerun: autocommit inserts go from about 2,400-4,200
ops/s to 6,726 on this Mac. macOS fsync(2) does not flush the drive's
cache, which is why the gap is small; with F_FULLFSYNC it would be large.

## 01 Pages

### 01.01 The database file as pages

Regions (src/pager.c): `read_page` "read a page", `write_page` "write a
page", `header_init` "the database header".

Before (stub; nothing is written, the file stays 0 bytes):

```
$ ./db demo.db "CREATE TABLE t(a); INSERT INTO t VALUES ('hello'); SELECT * FROM t;"
db: 01.01: the database header not written yet
```

After:

```
$ ./db demo.db "CREATE TABLE t(a); INSERT INTO t VALUES ('hello'); SELECT * FROM t;"
hello
$ ls -l demo.db         -> 8192 bytes: two pages
$ head -c 16 demo.db | od -c
0000000    S   Q   L   i   t   e       f   o   r   m   a   t       3  \0
$ sqlite3 demo.db "PRAGMA integrity_check; SELECT * FROM t;"
ok
hello
```

Break it (verified): in read_page, compute the offset as
`pgno * page_size` (forgetting pages count from 1). Open a file sqlite3
made: `db: fatal: database is corrupt: page 1 is not a b-tree page (type 0)`
- page 1 is read from where page 2 is.

### 01.02 The page cache

Regions (src/pager.c): `page_get` "look up a page in the cache",
`pager_shrink` "evict cold pages".

Before (pager_shrink runs before every statement, so it is hit first):

```
db: 01.02: evict cold pages not written yet
```

After (a 3000-row table of 39 pages; `SELECT b FROM t` once, twice, and
twice with a 10-page cache):

```
stats: pages read 39, cache hits 9114, cache misses 39, evictions 0, ...
stats: pages read 39, cache hits 18262, cache misses 39, evictions 0, ...
stats: pages read 76, cache hits 18225, cache misses 76, evictions 64, ...
```

The second scan in the same process costs no reads; with a 10-page cache
the second scan reads the table again.

Break it (verified): on a hit, do not move the page to the front of the
LRU list (FIFO eviction). 2000 random point lookups on a 30000-row table
with `DB_CACHE_PAGES=10`: 2179 page reads instead of 1981, because the
root page now gets evicted while it is the hottest page there is.

### 01.03 Records: varints and serial types

Regions (src/record.c): `varint_get` "read a varint", `varint_put` "write
a varint", `serial_type` "choose a serial type", `serial_get` "decode a
value".

Before: `db: 01.03: choose a serial type not written yet` (the first INSERT).

After:

```
$ ./db demo.db "CREATE TABLE v(x); INSERT INTO v VALUES (NULL), (1), (300), (-2), (1e100), ('text'), (x'414243'); SELECT x, typeof(x) FROM v;"
|null
1|integer
300|integer
-2|integer
1.0e+100|real
text|text
ABC|blob
```

The test checks that the leaf page we write is byte for byte the page
sqlite3 writes for the same rows (only the header's version stamp at
offset 96 differs).

Break it (verified): in varint_put, drop the line that clears the high bit
of the last byte (`tmp[0] &= 0x7f`). Every varint runs on into the next
byte: `db: fatal: database is corrupt: overflow chain ends early`, and
sqlite3 says `database disk image is malformed`.

## 02 The B-tree

### 02.01 A leaf page: cells and search

Regions (src/btree.c): `cell_parse_type` "take a cell apart",
`node_search` "binary search a page".

Before: `db: 02.01: take a cell apart not written yet`.

After (a table sqlite3 made, rowids 3, 7, 9):

```
$ ./db demo.db 'SELECT * FROM t WHERE id = 7; SELECT * FROM t WHERE id = 8;'
7|seven
```

Break it (verified): in node_search, move lo past cells that compare
`<= 0` instead of `< 0` (an upper bound instead of a lower one). The same
query prints nothing: every search lands one cell after its key.

### 02.02 Insert and split

Regions (src/btree.c): `node_insert` "put a cell into a page", `split`
"split a page". (`partition`, `split_point` and `insert_dividers` are
reference code next to it.)

Before: `db: 02.02: put a cell into a page not written yet` (the first INSERT).

After (2000 rows in one transaction):

```
stats: pages read 2, cache hits 15923, cache misses 27, evictions 0, pages written 29, fsyncs 8, journal pages 2, wal frames 0, checkpoints 0, splits 24, append splits 24, merges 0
$ ./db demo.db 'PRAGMA page_count; SELECT * FROM t WHERE id = 1234;'
27
1234|6678|row 1234 xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
$ sqlite3 demo.db 'PRAGMA integrity_check'
ok
```

Break it (verified): make a table leaf's divider the first rowid of the
right page (cell ge[g]) instead of the last of the left (ge[g] - 1).
Insert 2000 random keys; sqlite3's integrity check:

```
*** in database main ***
Tree 2 page 2 cell 31: Rowid 97329 out of order
Tree 2 page 2 cell 30: Rowid 95152 out of order
```

### 02.03 Interior pages and the root

Regions (src/btree.c): `grow_root` "grow the tree", `seek_raw` "go down
from the root".

Before: `db: 02.03: go down from the root not written yet`.

After (4000 rows of 400 bytes, a tree three levels deep):

```
$ sqlite3 demo.db "SELECT name, rootpage FROM sqlite_schema; PRAGMA integrity_check;"
t|2
ok
$ ./db demo.db 'SELECT id, length(v) FROM t WHERE id = 3999'
3999|400
```

The root is still page 2. Page 1 grows the same way once sqlite_schema has
enough rows (the 02.03 test makes 150 tables).

Break it (verified): in grow_root, leave the path alone (no shift, no
depth++). The split that follows sends its divider to the wrong level:
`db: fatal: page 0 is out of range (the database has 3 pages)` after 29
inserts of 400 bytes.

### 02.04 Cursors and range scans

Regions (src/btree.c): `descend_leftmost` "down to the leftmost leaf",
`settle` "climb to the next entry".

Before: `db: 02.04: down to the leftmost leaf not written yet`.

After:

```
$ ./db demo.db 'SELECT id, a FROM t WHERE id BETWEEN 1499 AND 1502;'
1499|4058
1500|11977
1501|19896
1502|7804
```

Break it (verified): in settle, treat index interior cells like a
table's (skip the `if (!c->intkey)` return). Walking an index then misses
its interior entries: `SELECT id FROM t WHERE a >= 0` with an index on a
returns 2993 rows of 3000.

### 02.05 Delete and free pages

Regions (src/btree.c): `btree_delete` "delete an entry", `freelist_pop`
"take a page off the freelist", `page_free` "put a page on the freelist".
(`fix_empty`, which merges an empty page into a sibling, and
`collapse_root` are reference code.)

Before: `db: 02.05: delete an entry not written yet`.

After (3000 rows; delete 2000; insert 500 more):

```
$ ./db demo.db 'DELETE FROM t WHERE id > 1000; PRAGMA page_count; PRAGMA freelist_count;'
39
25
$ ... 500 INSERTs ...
$ ./db demo.db 'PRAGMA page_count; PRAGMA freelist_count;'
39
18
$ sqlite3 demo.db 'PRAGMA integrity_check'
ok
```

The file did not grow: the new rows took pages off the freelist.

Break it (verified): in freelist_pop, forget to lower the count at header
offset 36. sqlite3: `Freelist: size is 18 but should be 25`.

## 03 SQL

### 03.01 The tokenizer

Regions (src/tokenize.c): `next_token` "read one token", `scan_quoted`
"strings and quoted names", `scan_number` "numbers".

Before: `db: 03.01: read one token not written yet`. Any SQL stops there,
and so does opening a database that has tables: the catalog is parsed at
open.

After:

```
$ ./db demo.db "SELECT 'it''s', 1e3, .5, x'414243', 7 <> 8 -- a comment
;"
it's|1000.0|0.5|ABC|1
```

Break it (verified): in scan_quoted, drop the doubled-quote case. `'it''s'`
becomes two strings: `Error: near "'s'": syntax error`.

### 03.02 The parser and the AST

Regions (src/parse.c): `parse_binary` "operators and precedence",
`parse_select` "the SELECT statement".

Before: `db: 03.02: the SELECT statement not written yet`.

After:

```
$ ./db demo.db 'SELECT 1 + 2 * 3, 10 - 4 - 3, NOT 1 = 2;'
7|3|1
$ ./db demo.db 'CREATE TABLE t(a, b); EXPLAIN SELECT a FROM t WHERE a > 1 ORDER BY b LIMIT 3;'
Limit 3 offset 0
  Sort by b
    Filter (a > 1)
      Scan t
```

Break it (verified): read the right operand with `parse_binary(ps, prec)`
instead of `prec + 1`. Operators become right-associative:
`SELECT 10 - 4 - 3, 2 * 3 - 1, 100 / 10 / 5` gives `9|5|50`; sqlite3 gives
`3|5|2`.

### 03.03 The schema: CREATE TABLE and the catalog

Regions (src/schema.c): `schema_load` "read the catalog", `create_table`
"CREATE TABLE".

Before: `db: 03.03: CREATE TABLE not written yet` (schema_load is cut too,
but it only runs once there is a page 1; on an empty file CREATE comes
first).

After:

```
$ ./db demo.db 'CREATE TABLE fruit(id INTEGER PRIMARY KEY, name TEXT); CREATE TABLE veg(name);'
$ ./db demo.db .tables
fruit
veg
$ ./db demo.db 'SELECT * FROM sqlite_schema;'
table|fruit|fruit|2|CREATE TABLE fruit(id INTEGER PRIMARY KEY, name TEXT)
table|veg|veg|3|CREATE TABLE veg(name)
```

The text stored is what sqlite3 stores: "CREATE TABLE " and then the
statement from the name on (IF NOT EXISTS dropped). Tables sqlite3 made
with UNIQUE, AUTOINCREMENT, triggers, a non-INTEGER PRIMARY KEY... are
read-only here: `Error: table u is read-only here: it uses a UNIQUE or
PRIMARY KEY constraint, which this engine does not support`. CREATE TABLE
refuses the same features instead of making a table it could not keep:
`CREATE TABLE k(id INT PRIMARY KEY, v)` gives `Error: a PRIMARY KEY that
is not INTEGER PRIMARY KEY is not supported` (sqlite3 backs such a key
with an automatic index, sqlite_autoindex_k_1, and calls a file without
it malformed). A table whose CREATE text does not parse here is listed
but unusable: `Error: table gen uses SQL this engine cannot parse`.

Break it (verified): in create_table, skip schema_insert_row. The CREATE
succeeds, but the table is gone at once (`Error: no such table: fruit`) and
sqlite3 finds its root page orphaned: `Page 2: never used`.

## 04 Running queries

### 04.01 INSERT and a full table scan

Regions (src/exec.c): `decode_row` "decode a row", `scan_next` "the table
scan", `insert_row` "insert a row".

Before: `db: 04.01: insert a row not written yet`.

After:

```
$ ./db demo.db "CREATE TABLE p(id INTEGER PRIMARY KEY, n INTEGER, s TEXT); INSERT INTO p(n, s) VALUES ('42', 7), (NULL, 'x'); INSERT INTO p VALUES (10, 1, 'ten'); INSERT INTO p(s) VALUES ('next'); SELECT id, n, typeof(n), s, typeof(s) FROM p;"
1|42|integer|7|text
2||null|x|text
10|1|integer|ten|text
11||null|next|text
```

Affinity at work: '42' became an integer, 7 became text; the rowid after
10 is 11.

decode_row also reads two things sqlite3 writes that this engine never
does (verified, files made by sqlite3 3.54.1):

```
$ sqlite3 p.db "CREATE TABLE p(name TEXT, price REAL); INSERT INTO p VALUES ('pear', 2.0), ('fig', 0.75);"
$ ./db p.db "SELECT name, price, typeof(price), price / 4 FROM p;"
pear|2.0|real|0.5
fig|0.75|real|0.1875
$ sqlite3 t.db "CREATE TABLE t(a); INSERT INTO t VALUES (1); ALTER TABLE t ADD COLUMN b DEFAULT 5; ALTER TABLE t ADD COLUMN c REAL DEFAULT 3; INSERT INTO t(a) VALUES (2);"
$ ./db t.db "SELECT a, b, typeof(b), c, typeof(c) FROM t;"
1|5|integer|3.0|real
2|5|integer|3.0|real
```

sqlite3 stores a whole-number float in a REAL column as an integer (2.0
as the one-byte integer 2), and it must read back as a float. Row 1 was
stored before the two ADD COLUMNs and holds one value; the missing columns
read as their DEFAULT, with the column's affinity (evaluated once per
catalog load, in schema.c's column_default).

Break it (verified): in decode_row, do not put the rowid into the INTEGER
PRIMARY KEY column. Every id prints empty (`|42|integer|7|text`): the
record stores NULL there, by design of the format.

### 04.02 WHERE and expressions

Regions: src/exec.c `filter_next` "keep the rows WHERE is true for";
src/expr.c `eval_compare` "compare two values", `eval_logic` "AND and OR".

Before: `db: 04.02: keep the rows WHERE is true for not written yet`.

After (rows (1, 5), (2, NULL), (3, 7)):

```
SELECT id FROM t WHERE n = '5';             -> 1
SELECT id FROM t WHERE n > 1 OR n IS NULL;  -> 1 2 3
SELECT NULL = NULL, NULL AND 0, NULL OR 1;  -> |0|1
```

Break it (verified): in eval_compare, drop the NULL check before
comparing. `SELECT NULL = NULL, 1 < NULL` gives `1|0` instead of `|`, and
`WHERE n < 6` now returns the NULL row too (NULL sorts below numbers).

### 04.03 ORDER BY and LIMIT

Regions (src/exec.c): `sort_next` "sort the rows", `limit_next` "LIMIT and
OFFSET".

Before: `db: 04.03: sort the rows not written yet`.

After (x = 'b', 3, NULL, 'a', 2.5 for ids 1-5):

```
SELECT id, x FROM t ORDER BY x DESC;
1|b
4|a
2|3
5|2.5
3|
SELECT id FROM t ORDER BY id LIMIT 2 OFFSET 1;
2
3
```

Text sorts above numbers, NULL lowest: SQLite's order.

Break it (verified): in limit_next, test `seen >= limit` instead of
`seen - offset >= limit`. `SELECT id FROM t LIMIT 3 OFFSET 2` over ids 1-6
gives `3` alone instead of `3 4 5`.

### 04.04 UPDATE and DELETE

Regions (src/exec.c): `exec_update` "UPDATE", `exec_delete` "DELETE".

Before: `db: 04.04: UPDATE not written yet`.

After:

```
$ ./db demo.db "CREATE TABLE t(id INTEGER PRIMARY KEY, n); INSERT INTO t VALUES (1, 10), (2, 20), (3, 30); UPDATE t SET n = n + 1 WHERE id >= 2; UPDATE t SET id = id + 100; DELETE FROM t WHERE n = 21; SELECT * FROM t;"
101|10
103|31
```

`UPDATE t SET id = id + 100` moves every row to a higher rowid; it works
because the rowids are collected before anything changes (the Halloween
problem). `UPDATE t SET id = id + 1` fails in both engines with `UNIQUE
constraint failed: t.id`, row 1 meeting row 2.

Break it (verified): in exec_delete, skip index_remove. With an index on
n, delete row 2 and look it up by n: `db: fatal: database is corrupt: index
t_n points at row 2, which is not there`; sqlite3: `wrong # of entries in
index t_n`.

## 05 Indexes and the planner

### 05.01 An index is a B-tree

Regions (src/exec.c): `index_key` "an index entry", `index_build` "fill a
new index".

Before: `db: 05.01: fill a new index not written yet` (CREATE INDEX).

After:

```
$ ./db demo.db 'CREATE INDEX t_a ON t(a); SELECT name, rootpage, sql FROM sqlite_schema;'
t|2|CREATE TABLE t(id INTEGER PRIMARY KEY, a INTEGER, b TEXT)
t_a|28|CREATE INDEX t_a ON t(a)
$ sqlite3 demo.db 'PRAGMA integrity_check'
ok
```

sqlite3's check looks up every row in every index, so "ok" means every
entry is right.

Break it (verified): leave the rowid out of the key. sqlite3:
`row 1 missing from index t_n`, `row 2 missing from index t_n`; our own
lookup: `db: fatal: database is corrupt: bad entry in index t_n`.

### 05.02 Index lookups and range scans

Regions (src/exec.c): `rowid_range_next` "a range of rowids",
`index_range_next` "an index range".

Before: `db: 05.02: an index range not written yet` (only for WHERE
clauses the planner answers with an index; a scan still works).

After (20000 rows, index on a):

```
$ DB_STATS=1 ./db demo.db 'SELECT id, a FROM t WHERE a = 7919;'
1|7919
stats: pages read 5, cache hits 14, cache misses 5, ...
$ DB_STATS=1 ./db demo.db "SELECT id FROM t WHERE b = 'row 1 xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx';"
1
stats: pages read 252, cache hits 60756, cache misses 252, ...
```

Five pages through the index against 252 for a scan.

Break it (verified): seek the lower bound with bias +1 instead of -1
("after every equal entry"). `WHERE a = 7919` prints nothing, and
`WHERE a >= 20009` loses its first row (`18980|20010` only).

### 05.03 Choosing a plan, and EXPLAIN

Regions (src/plan.c): `choose_access` "choose how to read the table",
`sort_needed` "when the sort can go".

Before: `db: 05.03: choose how to read the table not written yet` (any
query on a table).

After:

```
EXPLAIN QUERY PLAN SELECT * FROM t WHERE a > 5;
QUERY PLAN
`--SEARCH t USING INDEX t_a (a>?)
EXPLAIN QUERY PLAN SELECT * FROM t WHERE id = 2 AND a = 6;
QUERY PLAN
`--SEARCH t USING INTEGER PRIMARY KEY (rowid=?)
EXPLAIN QUERY PLAN SELECT * FROM t ORDER BY b;
QUERY PLAN
|--SCAN t
`--USE TEMP B-TREE FOR ORDER BY
EXPLAIN SELECT b FROM t WHERE a > 5;
Filter (a > 5)
  Index range t using t_a (a > ?)
```

EXPLAIN QUERY PLAN matches sqlite3's output for 23 test queries. Where
sqlite3 does better it is left out of the test, e.g. `a = 3 AND id > 1`,
which sqlite3 answers with the rowid stored at the end of each index entry:
`(a=? AND rowid>?)`.

Break it (verified): let a lower bound count as an equality
(`if (!ib.eq) ib.eq = ib.lo;`). `SELECT id, a FROM t WHERE a > 5` returns
nothing (the plan reads only a = 5, and WHERE rejects those), with plan
`SEARCH t USING INDEX t_a (a=?)`. The point: the access path must never
read less than WHERE accepts; reading more is only slow.

## 06 Transactions

### 06.01 What a crash does to a half-written page (lab, no regions)

With no journal, a crash halfway through writing the pages of a commit
(2000 rows, `UPDATE t SET b = 'new'`):

```
$ DB_CRASH=db-partial ./db demo.db "PRAGMA journal_mode=off; UPDATE t SET b = 'new';"
off
db: crash injected at db-partial
$ ./db demo.db "SELECT id FROM t WHERE b = 'new';" | wc -l
     945
```

945 of 2000 rows changed: half a transaction. With a torn page
(`DB_CRASH=db-torn`, half of one page written):

```
$ sqlite3 demo.db 'PRAGMA integrity_check'
*** in database main ***
Tree 2 page 15 cell 80: Rowid 120 out of order
Tree 2 page 15 cell 79: Rowid 120 out of order
Tree 2 page 15 cell 78: Rowid 120 out of order
```

The same db-partial crash with the default rollback journal: 0 rows new.

### 06.02 The rollback journal and atomic commit

Regions (src/journal.c): `journal_write` "write the journal",
`journal_commit` "commit with the journal".

Before: `db: 06.02: commit with the journal not written yet` (the first
commit; the file stays empty).

After:

```
$ DB_CRASH=db-partial ./db demo.db "UPDATE t SET b = 'new';"
db: crash injected at db-partial
$ ls demo.db*
demo.db
demo.db-journal
$ ./db demo.db "SELECT id FROM t WHERE b = 'new';" | wc -l
db: rolled back an interrupted transaction (26 pages)
       0
$ sqlite3 demo.db 'PRAGMA integrity_check'
ok
```

sqlite3 itself can do the rollback: open the crashed file with sqlite3
first and it replays our journal (the 06.02 test does this).

Break it (verified): write the database pages before the journal (and
crash halfway through them). 1028 of 2000 rows come back changed: there
was no hot journal to undo them.

### 06.03 Recovery

Regions (src/journal.c): `journal_recover` "roll back a hot journal".

Before: the crash leaves a hot journal, and the next open stops:
`db: 06.03: roll back a hot journal not written yet`.

After: as in 06.02, `db: rolled back an interrupted transaction (26
pages)`, 0 rows changed, the journal deleted. A journal that never became
hot (`DB_CRASH=journal-partial`: magic still zero) is deleted silently.
The test also kills a real sqlite3 in the middle of a transaction big
enough to spill pages into the database file (`PRAGMA cache_size=10`) and
rolls back sqlite3's journal.

Break it (verified): delete the journal before copying the pages back,
and crash during recovery (`DB_CRASH=recover-partial`). The next open has
no journal to finish with: 945 of 2000 rows stay changed, though the
transaction never committed. Recovery has to be safe to repeat.

### 06.04 A write-ahead log

Regions (src/wal.c): `wal_open` "read the log", `wal_commit` "append a
commit", `wal_checkpoint` "checkpoint".

Before: `PRAGMA journal_mode=wal` still works (it commits with the
rollback journal); the first WAL commit stops: `db: 06.04: append a commit
not written yet`, and the next open: `db: 06.04: read the log not written
yet`.

After:

```
$ (echo 'PRAGMA journal_mode=wal;'; echo "UPDATE t SET b = 'w' WHERE id < 10;"; echo 'SELECT 1;') | DB_STATS=1 ./db demo.db
wal
1
stats: pages read 5, cache hits 119, cache misses 3, evictions 0, pages written 2, fsyncs 8, journal pages 1, wal frames 1, checkpoints 1, splits 0, append splits 0, merges 0
$ DB_CRASH=checkpoint-done ./db demo.db "UPDATE t SET b = 'v' WHERE id = 1;"
$ ls -l demo.db*      -> demo.db 57344, demo.db-wal 4152 (header + one frame)
$ sqlite3 demo.db "SELECT b FROM t WHERE id = 1; PRAGMA integrity_check;"
v
ok
```

sqlite3 reads the frame we left in the log.

Break it (verified): put the commit mark (the database size) on the first
frame of a commit instead of the last, and crash halfway through
appending (`DB_CRASH=wal-partial`). On reopening, 82 of 1000 rows are
changed: a commit that never finished was taken as complete.

## 07 Fast

### 07.01 Reading the benchmark (lab, no regions)

A full run, `python3 bench/bench.py` (also `./learn bench db`), the one
recorded in tests/bench_baseline.json:

```
Benchmark: ./db against sqlite3 3.54.1 (/opt/homebrew/opt/sqlite/bin/sqlite3)
machine:   Apple M4 Pro, 14 cores, macOS 26.6.2
table:     t(id INTEGER PRIMARY KEY, a INTEGER, b TEXT), 100000 rows inserted in id order,
           an index on a; every statement is SQL text fed to the engine's shell on stdin
durability, the same on both sides: rollback journal (journal_mode=DELETE), synchronous=FULL:
           fsync(2) at every commit; F_FULLFSYNC off (fullfsync=OFF, sqlite3's default)
runs:      1 warm-up, then median of 3; page size 4096, a 2000 KiB page cache each

workload                              ops     db ops/s  sqlite3 ops/s  db/sqlite3
insert, autocommit                  10000        2,414          3,059       0.79x
insert, one transaction            100000    1,073,616        967,951       1.11x
point lookup by primary key        100000      607,003        179,415       3.38x
range scan, 100 rows each            1000       38,958         27,846       1.40x
lookup by secondary index          100000      410,718        152,010       2.70x
update by key, one transaction      10000      203,249        246,323       0.83x
delete by key, one transaction      10000      113,209        144,120       0.79x
file size, bytes                             6,852,608      5,914,624       1.16x
```

(That run printed its spread on a separate line; the current script puts
it in a column. Autocommit spread was 1.70 for db and 1.66 for sqlite3:
fsync timings swing. Another full run gave autocommit 4,163 vs 2,873.)

Things to read out of it (measured by the 07.01 lesson writer; the lesson
has the commands and numbers):

- Lookups are faster here mainly because, outside a transaction, sqlite3
  begins every statement by taking a shared lock on the file and checking
  for a hot journal (and for changes by another process); this engine
  assumes it is the only user of the file and does none of that. A
  sampling profile of sqlite3 puts almost half of its lookup time in
  acquiring the lock, and inside one BEGIN its 100000 lookups go from
  0.556 s to 0.248 s. A cheaper statement (no bytecode compiler) is the
  smaller part. The B-trees themselves are about even: about 1.3 us per
  lookup here, 1.4 us in sqlite3 inside a transaction, once the cost of an
  empty statement is taken away.
- Autocommit inserts are bound by four fsyncs per commit on both sides.
- The file is 16% bigger because of the index: sqlite3's CREATE INDEX
  sorts all the entries first and appends them in order, so its index
  pages come out about 99% full (288 pages); this engine inserts the
  entries one at a time in table order, and its 50/50 splits leave the
  index about 55% full (516 pages). The table itself is the same size as
  sqlite3's, both 99.3% full (1156 and 1155 pages; see 07.03). When
  sqlite3 has to insert index entries out of order (the index created
  before the rows), it rebalances neighbouring pages and ends at 311
  pages, 92% full; this engine does neither.

Break it: see 00.02 (make fsync a no-op and watch only the autocommit row
move).

### 07.02 Where the time goes (lab, no regions)

```
$ DB_STATS=1 ./db demo.db 'SELECT b FROM t WHERE id = 23456;'      (30000 rows)
row 23456 xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
stats: pages read 3, cache hits 9, cache misses 3, ...
```

Three page reads: page 1 (the schema), the root, one leaf.

Five autocommit INSERTs with the rollback journal, then five in WAL mode:

```
stats: pages read 13, cache hits 37, cache misses 3, evictions 0, pages written 10, fsyncs 20, journal pages 10, ...
stats: pages read 4, cache hits 32, cache misses 3, evictions 0, pages written 1, fsyncs 8, journal pages 0, wal frames 5, checkpoints 1, ...
```

Four fsyncs per journal commit (journal, its directory, the journal's
header, the database) against one per WAL commit (plus the directory once
and two for the checkpoint at close). Each journal commit journals two
pages: the leaf and page 1 (the change counter).

Break it (verified, see 01.02): `DB_CACHE_PAGES=10` and random lookups.

### 07.03 One more optimisation, measured

Regions (src/btree.c): `append_split` "split for an append".

Before: the first page split of a table stops:
`db: 07.03: split for an append not written yet`.

After (20000 rows inserted in rowid order, one transaction):

```
stats: pages read 2, cache hits 161498, cache misses 252, evictions 0, pages written 254, fsyncs 8, journal pages 2, wal frames 0, checkpoints 0, splits 249, append splits 249, merges 0
./db's file:     1032192 bytes
sqlite3's file:  1032192 bytes
```

Byte-for-byte the same size as sqlite3's.

Break it (verified; this is "the optimisation, turned off"): make
append_split always return -1, so appends split in the middle like any
other insert. 493 splits instead of 249, and the file is 2031616 bytes:
twice sqlite3's, every left half stuck half empty forever.

Note (reasoned, not measured): in an insert-only workload the "right-most
leaf" test in append_split never changes the result, because a key larger
than every key in a leaf other than the last would have gone to the next
leaf. It can matter once deletes leave dividers larger than their leaf's
last key.

## 08 More SQL (an optional extension)

### 08.07 UNIQUE: a constraint is an index lookup

Regions: src/schema.c `auto_indexes` "an automatic index for a
constraint"; src/exec.c `unique_taken` "look before you write".

Also added in this lesson, behind `@from 08.07`: in db.h `Unique` (one
constraint), `Stmt.uniques`, `Index.unique`; in parse.c `add_unique` and
`parse_unique` (constraints kept in the order written, a second PRIMARY
KEY refused) and the check at the end of CREATE TABLE that every
constraint names a column; in schema.c `rowid_constraint` (is this the
INTEGER PRIMARY KEY?), table_from's use of it, `auto_index_root` and
`auto_index_check` in schema_load (root pages from the rows with no sql),
create_table writing the automatic indexes, schema_insert_row writing a
NULL sql, index_from's `unique`, and DROP INDEX refusing an automatic
index; in exec.c `unique_failed` (the message), `check_unique` (the
order: newest index first), its calls in insert_row and exec_update, the
duplicate check in index_build (CREATE UNIQUE INDEX), and
`update_in_rowid_order`.

Before, with the lesson cut out: `db: 08.07: an automatic index for a
constraint not written yet` (CREATE TABLE with a constraint, or opening a
file that has one); `db: 08.07: look before you write not written yet`
(a write to a table with a unique index). Plain tables and INTEGER
PRIMARY KEY tables still work.

Before, in the core (the project at 07.03):

```
$ ./db core.db "CREATE TABLE users(id INTEGER PRIMARY KEY, email TEXT UNIQUE, name TEXT);"
Error: UNIQUE is not supported
$ ./db core.db "CREATE TABLE k(id TEXT PRIMARY KEY, v);"
Error: a PRIMARY KEY that is not INTEGER PRIMARY KEY is not supported
$ ./db core.db "CREATE TABLE t(a, b); CREATE UNIQUE INDEX t_a ON t(a);"
Error: UNIQUE indexes are not supported
$ ./db sqlite3s.db "INSERT INTO users VALUES (9, 'x@example.com', 'X', NULL);"
Error: table users is read-only here: it uses a UNIQUE or PRIMARY KEY constraint, which this engine does not support
```

After. The sqlite_schema of a table with two automatic indexes, as ./db
wrote it, then as sqlite3 reads the same file (for the figure: root pages
2, 3, 4 in creation order, and sql NULL for each automatic index):

```
$ ./db users.db "CREATE TABLE users(id INTEGER PRIMARY KEY, email TEXT UNIQUE, name TEXT, phone TEXT, UNIQUE(name, phone)); INSERT INTO users VALUES (1, 'ada@example.com', 'Ada', '555-0101'), (2, 'brook@example.com', 'Brook', NULL), (3, 'chen@example.com', 'Chen', '555-0103');"
$ ./db users.db "SELECT type, name, tbl_name, rootpage, typeof(sql), sql FROM sqlite_schema;"
table|users|users|2|text|CREATE TABLE users(id INTEGER PRIMARY KEY, email TEXT UNIQUE, name TEXT, phone TEXT, UNIQUE(name, phone))
index|sqlite_autoindex_users_1|users|3|null|
index|sqlite_autoindex_users_2|users|4|null|
$ sqlite3 users.db "SELECT name, rootpage, quote(sql) FROM sqlite_schema; PRAGMA integrity_check;"
users|2|'CREATE TABLE users(id INTEGER PRIMARY KEY, email TEXT UNIQUE, name TEXT, phone TEXT, UNIQUE(name, phone))'
sqlite_autoindex_users_1|3|NULL
sqlite_autoindex_users_2|4|NULL
ok
$ sqlite3 users.db "SELECT il.name, il.origin, ii.seqno, ii.name FROM pragma_index_list('users') il, pragma_index_info(il.name) ii ORDER BY il.name, ii.seqno;"
sqlite_autoindex_users_1|u|0|email
sqlite_autoindex_users_2|u|0|name
sqlite_autoindex_users_2|u|1|phone
$ ./db users.db "SELECT email, rowid FROM users WHERE email > '';"
ada@example.com|1
brook@example.com|2
chen@example.com|3
$ ./db users.db "EXPLAIN SELECT name FROM users WHERE email = 'chen@example.com'; EXPLAIN QUERY PLAN SELECT name FROM users WHERE email = 'chen@example.com';"
Filter (email = 'chen@example.com')
  Index lookup users using sqlite_autoindex_users_1 (email = ?)
QUERY PLAN
`--SEARCH users USING INDEX sqlite_autoindex_users_1 (email=?)
```

The id INTEGER PRIMARY KEY has no index (it is the rowid), so the two
UNIQUE constraints are _1 and _2. Page 3, the index on email, after five
rows (each cell: payload size, record header size 3, serial types, the
email, the rowid; serial type 9 is the constant 1, 1 the one-byte integer
that follows):

```
page 3: type 0x0a, 5 cells, content at 3994
  cell 0 at 4077: 12 03 2b 09 61 64 61 40 65 78 61 6d 70 6c 65 2e 63 6f 6d       ada@example.com, 1
  cell 1 at 4055: 15 03 2f 01 62 72 6f 6f 6b 40 65 78 61 6d 70 6c 65 2e 63 6f 6d 02    brook@..., 2
  cell 2 at 4034: 14 03 2d 01 63 68 65 6e 40 65 78 61 6d 70 6c 65 2e 63 6f 6d 03       chen@..., 3
  cell 3 at 4014: 13 03 2b 01 64 65 65 40 65 78 61 6d 70 6c 65 2e 63 6f 6d 04          dee@..., 4
  cell 4 at 3994: 13 03 2b 01 65 76 65 40 65 78 61 6d 70 6c 65 2e 63 6f 6d 05          eve@..., 5
```

Pages 2, 3 and 4 are byte for byte the pages sqlite3 writes for the same
statements: an entry of a unique index is the bytes of any index entry.

The checks, the same statements through ./db and sqlite3 (sqlite3 adds
"near line N"):

```
INSERT INTO users VALUES (4, 'ada@example.com', 'Dee', NULL);
Error: UNIQUE constraint failed: users.email
INSERT INTO users VALUES (4, 'dee@example.com', 'Ada', '555-0101');
Error: UNIQUE constraint failed: users.name, users.phone
INSERT INTO users VALUES (1, 'ada@example.com', 'Ada', '555-0101');
Error: UNIQUE constraint failed: users.id                    (the rowid is checked first)
INSERT INTO users VALUES (4, 'ada@example.com', 'Ada', '555-0101');
Error: UNIQUE constraint failed: users.name, users.phone     (breaks two: the one declared last)
INSERT INTO users VALUES (4, 'dee@example.com', 'Brook', NULL), (5, 'eve@example.com', 'Brook', NULL);
                                                             (no error: a NULL never conflicts)
INSERT INTO users VALUES (6, 'fay@example.com', 'Fay', NULL), (7, 'chen@example.com', 'Gus', NULL);
Error: UNIQUE constraint failed: users.email                 (and fay is not there either)
UPDATE users SET email = 'ada@example.com' WHERE id = 2;
Error: UNIQUE constraint failed: users.email
```

UPDATE row by row (ord.db; asc_t holds 1, 2, 3 in rowids 1, 2, 3 and
desc_t holds 3, 2, 1):

```
UPDATE asc_t SET a = a + 1;      Error: UNIQUE constraint failed: asc_t.a   (1 -> 2 meets row 2)
UPDATE desc_t SET a = a + 1;     (no error: 3 -> 4, 2 -> 3, 1 -> 2)
SELECT rowid, a FROM asc_t;      1|1  2|2  3|3
SELECT rowid, a FROM desc_t;     1|4  2|3  3|2
UPDATE desc_t SET a = a + 1 WHERE a > 0;     (no error: found through the index, changed in rowid order)
SELECT rowid, a FROM desc_t;     1|5  2|4  3|3
```

A failed multi-row INSERT, outside BEGIN and inside:

```
INSERT INTO t VALUES (10), (11), (1), (12);     Error: UNIQUE constraint failed: t.a
SELECT a FROM t;                                1 2 3
BEGIN;
INSERT INTO t VALUES (20);
INSERT INTO t VALUES (21), (22), (1), (23);     Error: UNIQUE constraint failed: t.a
SELECT a FROM t;                                1 2 3 20   (the statement undone, the transaction kept)
COMMIT;
SELECT a FROM t;                                1 2 3 20
```

Cost: 20000 rows under `a INTEGER UNIQUE, b TEXT PRIMARY KEY` (b's
index has 3 levels, the table 2): a one-row INSERT reads 8 pages from the
file (DB_STATS cache misses), the same whether it is refused or written.

Break it (all verified):

- Check the indexes oldest first (in check_unique, test ix before the
  rest of the list). `CREATE TABLE m(a UNIQUE, b UNIQUE, c TEXT PRIMARY
  KEY); CREATE UNIQUE INDEX m_ab ON m(a, b)`, a row (1, 1, 'x'), then the
  same row again: ./db says `UNIQUE constraint failed: m.a`, sqlite3
  `m.a, m.b`; (2, 1, 'x'): ./db `m.b`, sqlite3 `m.c`. Every row is still
  refused, but not with sqlite3's words.
- Give a constraint that repeats another its own index (drop the `if
  (repeat) continue;`). `CREATE TABLE u(id INTEGER PRIMARY KEY, x UNIQUE,
  y UNIQUE, UNIQUE(x))` writes sqlite_autoindex_u_3, and sqlite3 refuses
  the whole file: `Parse error in 2nd command line argument: malformed
  database schema (sqlite_autoindex_u_3) - orphan index (11)`.
- Forget the NULL rule in unique_taken. `CREATE TABLE p(k TEXT PRIMARY
  KEY, v)`, then `INSERT INTO p VALUES (NULL, 1)` and `(NULL, 2)`: the
  second fails, `UNIQUE constraint failed: p.k`, where sqlite3 stores both.
- Do not skip the row's own entry (`taken = 1;` for any equal entry).
  `UPDATE t SET id = id + 10` on `t(id INTEGER PRIMARY KEY, a UNIQUE)`
  fails, `UNIQUE constraint failed: t.a`: each row meets its own old
  entry, because a new rowid makes every index entry change.

Facts worth knowing for the text (SQLite 3.54.1 source; the research file,
section C, has the quoted lines for most):

- Each UNIQUE or PRIMARY KEY becomes an index while the CREATE TABLE is
  parsed, in the order written (parse.y). The name is
  `sqlite_autoindex_<table>_<n>`, n one more than the indexes already on
  the table (build.c, sqlite3CreateIndex). A constraint on the same
  columns in the same order (and collations) as an earlier one makes none
  and takes no number; UNIQUE(b, a) after UNIQUE(a, b) is a new one.
  `UNIQUE(a, a)` is an index of two columns, both a (run).
- No index for a lone PRIMARY KEY column declared exactly INTEGER (the
  type string, so not `INT` and not `INTEGER(10)`): it is the rowid
  (build.c, sqlite3AddPrimaryKey). Written on the column as `PRIMARY KEY
  DESC` it is not the rowid; as a table constraint `PRIMARY KEY(k DESC)`
  it still is. `k INTEGER UNIQUE PRIMARY KEY` makes an index on the rowid
  alias anyway: the repeat test only compares indexes.
- sqlite3 does not store which constraint an index belongs to: it parses
  CREATE TABLE again at every open, rebuilds the names, and pairs each
  row with no sql by name (prepare.c, sqlite3InitCallback); a name it
  does not make is "orphan index". So ./db's numbering is not a style
  choice: any other is a file sqlite3 will not open.
- The order of the checks: NOT NULL, then the rowid, then each unique
  index in the table's index list, which sqlite3 keeps newest first
  (build.c, sqlite3CreateIndex, `pIndex->pNext = pTab->pIndex`; insert.c,
  sqlite3GenerateConstraintChecks). So of two constraints a row breaks,
  the one declared last is reported, and a CREATE UNIQUE INDEX made after
  the table comes before all of them. ./db keeps its list oldest first
  (the planner walks it that way) and checks it from the end.
- The probe compares only the key columns (OP_NoConflict with P4 =
  nKeyCol) and jumps straight to "no conflict" when any of them is NULL
  (vdbe.c, OP_NoConflict). For an UPDATE an equal entry is no conflict
  when its rowid is the row's old rowid; an index none of whose columns
  the UPDATE sets is not checked (update.c, sqlite3Update gives it no
  register, through indexColumnIsBeingUpdated, unless the rowid changes;
  insert.c `if( aRegIdx[ix]==0 ) continue; /* Skip indices that do not
  change */`). ./db skips an index whose values do not change, which
  comes to the same: an index that keeps its values can only meet the
  row's own entry.
- The message: `UNIQUE constraint failed: ` and the key columns as
  table.column joined by ", " (build.c, sqlite3UniqueConstraint), the
  same for a PRIMARY KEY (only the extended error code differs).
- The order an UPDATE changes rows in (update.c, sqlite3Update, read for
  this lesson): with WHERE_ONEPASS_MULTIROW it changes each row as the
  scan finds it, but sqlite3WhereOkOnePass's choice is dropped to
  ONEPASS_OFF when the scan reads an index the UPDATE writes ("A one-pass
  strategy that might update more than one row may not be used if any
  column of the index used for the scan is being updated", around line
  756), and the flag is never asked for when the rowid changes
  (`!chngKey`). ONEPASS_OFF stores each rowid in an ephemeral table
  (`OP_OpenEphemeral, iEph, 0`, `OP_Insert, iEph, regRowSet, regOldRowid`)
  and then walks it with OP_Rewind, which is rowid order. Runs:
  `UPDATE e SET a = a + 1 WHERE b > 0` with an index on b and rows (1,3),
  (2,2), (3,1) succeeds (b order), `UPDATE e SET a = a + 1` fails (rowid
  order); `UPDATE f SET id = id + 1 WHERE b > 0` on the same shape with an
  INTEGER PRIMARY KEY fails in sqlite3. update_in_rowid_order copies that
  rule.
- A failed statement is undone whole: outside BEGIN the transaction it
  ran in is rolled back; inside BEGIN the statement savepoint (06.02) is,
  and the transaction goes on. That is SQLite's default ABORT. A one-row
  INSERT checks every index before it writes anything, so it still needs
  no savepoint.
- CREATE UNIQUE INDEX over a duplicate fails with the INSERT's message
  (build.c, sqlite3RefillIndex sorts the rows and compares neighbours;
  ./db looks each row up as it adds it). Outside BEGIN the file is left
  byte for byte as it was.
- `DROP INDEX sqlite_autoindex_t_1`: "index associated with UNIQUE or
  PRIMARY KEY constraint cannot be dropped" (build.c, sqlite3DropIndex).
  Two PRIMARY KEYs: `table "t" has more than one primary key` (build.c,
  sqlite3AddPrimaryKey, the TF_HasPrimaryKey test). A constraint on a
  column the table lacks: `no such column: b` (each column is resolved as
  an expression: build.c sqlite3CreateIndex, sqlite3ResolveSelfReference
  with NC_IdxExpr; resolve.c lookupName).
- integrity_check checks uniqueness itself ("non-unique entry in index",
  pragma.c), so "ok" on a file ./db wrote covers the constraint, not only
  the entries.
- A one-row lookup through a unique index: sqlite3 marks it WHERE_ONEROW
  (where.c, whereLoopAddBtreeIndex) and uses it to drop a sort; EXPLAIN
  QUERY PLAN prints the same line as for any index.

Known differences from sqlite3:

- `SELECT * FROM t WHERE a = 5 ORDER BY b` with a UNIQUE: sqlite3 knows
  one row comes back and prints no `USE TEMP B-TREE FOR ORDER BY`; ./db
  still plans (and does) the sort of that one row. The 05.03 planner also
  never prints COVERING INDEX.
- update_in_rowid_order follows sqlite3's rule only as far as this
  planner picks the index sqlite3 picks; with two usable indexes they can
  differ, and so can the row that fails.
- The extended error codes (SQLITE_CONSTRAINT_PRIMARYKEY or _UNIQUE) are
  not kept; the text is the same.
- A schema sqlite3 calls malformed (an automatic index row missing, or one
  that matches no constraint) makes that table read-only here; sqlite3
  refuses the whole file.
- Left out and refused, as before: INSERT OR ..., REPLACE, ON CONFLICT
  (in a statement, or in a constraint: such a CREATE TABLE does not parse
  here, and a sqlite3 table with it can be listed but not read), COLLATE
  or DESC in a constraint (read-only), WITHOUT ROWID (opaque), more than
  8 columns in one constraint.
- Found while building, in the core and not changed there: the core
  checks a duplicate rowid before NOT NULL (`INSERT INTO t VALUES (1,
  NULL, 2)` with id 1 taken: ./db `UNIQUE constraint failed: t.id`,
  sqlite3 `NOT NULL constraint failed: t.a`); the core reads a sqlite3
  table's `id INTEGER PRIMARY KEY DESC` as the rowid (it is an ordinary
  column; 08.07's rowid_constraint gets it right); and the core changes
  rows in index order when an UPDATE changes the rowid through an index
  scan (`UPDATE f SET id = id + 1 WHERE b > 0` succeeds in the core, fails
  in sqlite3; from 08.07 it fails here too).
