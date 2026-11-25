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

Everything module 08 adds to files of the core is behind `@from 08.xx` markers;
the project at every core lesson is byte for byte what it was. Its data set
(design): customers(id INTEGER PRIMARY KEY, name, city) with Ada London, Brook
Paris, Chen London, Dee Oslo; orders(id INTEGER PRIMARY KEY, customer_id,
total) with (10,1,30) (11,3,15) (12,1,50) (13,2,20) (14,3,5) (15,NULL,40).

### 08.01 Two tables in one query: the nested loop join

Regions: src/parse.c `parse_from` "the FROM clause"; src/expr.c
`resolve_names` "bind a name to its table"; src/exec.c `join_next` "the
nested loop"; src/plan.c `plan_select` "where each condition is checked".
Also added (@from 08.01): FromItem, Scope, Query and the new Op and Plan fields
(db.h); at_word, at_join_word, join_type (parse.c); answers_to (expr.c); select_resolve,
join_order_target, item_name, star_ambiguous, op_join (exec.c); last_table,
terms_at, item_scan, explain_join_plan, access_line, explain_op (plan.c);
qualified names in expr_text; "UPDATE ... FROM is not supported".

Before (08.01 cut out): every SELECT with a FROM clause stops, a one-table
one too, because the FROM clause is parse_from's now. `SELECT 1 + 1;` still
prints 2.

```
$ ./db shop.db "SELECT * FROM customers;"
db: 08.01: the FROM clause not written yet          (exit 3)
```

After:

```
SELECT c.name, o.id, o.total FROM customers c JOIN orders o ON o.customer_id = c.id ORDER BY o.id;
Ada|10|30
Chen|11|15
Ada|12|50
Brook|13|20
Chen|14|5
EXPLAIN SELECT c.name, o.id FROM customers c, orders o WHERE o.customer_id = c.id AND c.city = 'London' AND o.total > 10;
Filter ((o.customer_id = c.id) AND (o.total > 10))
  Join
    Filter (c.city = 'London')
      Scan customers AS c
    Scan orders AS o
EXPLAIN SELECT * FROM customers c JOIN orders o ON o.customer_id = c.id WHERE c.id = 3;
Filter (o.customer_id = c.id)
  Join
    Filter (c.id = 3)
      Rowid lookup customers rowid = ?
    Scan orders AS o
EXPLAIN QUERY PLAN SELECT c.name, o.id, o.total FROM customers c JOIN orders o ON o.customer_id = c.id ORDER BY o.id;
QUERY PLAN
|--SCAN c
|--SCAN o
`--USE TEMP B-TREE FOR ORDER BY
SELECT c.name, o.id FROM customers c CROSS JOIN orders o LIMIT 7;
Ada|10
Ada|11
Ada|12
Ada|13
Ada|14
Ada|15
Brook|10
SELECT * FROM customers c JOIN orders o ON o.customer_id = c.id ORDER BY id DESC LIMIT 3;
3|Chen|London|11|3|15
3|Chen|London|14|3|5
2|Brook|Paris|13|2|20
```

Errors, ./db and sqlite3 3.54.1 (same text; sqlite3 prefixes "Parse error"):
`ambiguous column name: id` (bare id in customers JOIN orders),
`ambiguous column name: rowid` (bare rowid with two tables: not "no such
column", which the design guessed), `ambiguous column name: main.customers.id`
(`SELECT * FROM customers JOIN customers`), `no such table: x` (`x.*`),
`no such column: zz.name`, `no such column: customers.name` (after `FROM
customers AS c`: an alias hides the name), `1st ORDER BY term out of range -
should be between 1 and 1`, `a JOIN clause is required before ON`, `unknown
join type: OUTER`, `at most 64 tables in a join` (65 tables). Refused by
./db, run by sqlite3: `LEFT JOIN is not supported` (until 08.02), `NATURAL
JOIN`, `RIGHT JOIN`, `FULL JOIN`, `USING`, `subqueries in FROM`,
`parenthesised joins`, `UPDATE ... FROM` (each "... is not supported").

Facts worth knowing for the text:

- The joined row: item k's columns, then its rowid, from base k on:
  customers c takes slots 0-2 and its rowid 3; orders o takes 4-6 and 7.
  `o.customer_id` is bound once to slot 5 and eval() reads `row->cols[5]`,
  unchanged. With one table nothing changes (base 0, rowid stays E_ROWID).
- An inner join's ON is WHERE: both are one list of ANDed terms, each checked
  in a Filter right above the operator that brings the last table it names
  (last_table). Constants go to the first filter. A term may name a table to
  its right in ON (`a JOIN b ON a.x = c.z JOIN c`), as in sqlite3.
- One exception, from the row layout: table 0's rowid named as rowid/oid
  (`c.rowid = 1`) is in a slot only once the first join has copied the row,
  so that term waits for item 1 (EXPLAIN shows it in the top filter). `c.id`
  (the INTEGER PRIMARY KEY) is a column, checked at level 0 and used for a
  rowid lookup.
- Table 0 is read the way its own terms allow (05.03's choose_access): a
  rowid or index lookup or range. Every later table is scanned whole, once
  per row the join below it hands up (08.03 adds lookups).
- The outer row is copied (keep()) into the Join's own arena, which is
  emptied for the next outer row; the inner row is not (good until the next
  call, like a scan's). The statement loop evicts pages every 256 output
  rows (pager_shrink), so a two-page cache shows any slip at output row 256.
- `*` in a join expands left to right; with two tables answering to one name
  sqlite3 writes the column as main.<name>.<col> (select.c selectExpander),
  hence that error text. ORDER BY a bare name that a `*` stands for is the
  first result column of that name (resolve.c resolveAsName: expanded columns
  are ENAME_NAME), so `ORDER BY id` over customers JOIN orders sorts by
  customers.id with no ambiguity. 08.01 follows that for joins
  (join_order_target); one-table queries keep the core's order_target.
- A qualifier q (q.c, q.*) matches an item's alias if it has one, else its
  table's name as the catalog has it or as the query wrote it (answers_to):
  the catalog calls sqlite_master sqlite_schema. Found while building: the
  core says `no such column: sqlite_master.name` for `SELECT
  sqlite_master.name FROM sqlite_master`; from 08.01 it works, as in sqlite3,
  and `sqlite_master.*` (the core read any `x.*` as `*`) still does.
- INNER, CROSS, LEFT ... are names to the tokenizer (`CREATE TABLE jw(left,
  inner, cross)` works in both engines); after a table name they are join
  words, never an alias (`FROM t inner` is a syntax error in sqlite3 too);
  `AS left` is fine. Join words combine as sqlite3JoinType does (select.c).
- Measured (p 3000 rows, q 300, 130 pages): `p JOIN q ON q.id = p.k`, 3000
  rows, 0.04 s, stats: pages read 130, cache hits 2913300 (q read 3000
  times, all from the cache). sqlite3 doing the same nested loop
  (automatic_index=OFF, CROSS JOIN, `q.id + 0`) 0.02 s; sqlite3 as it likes
  (q.id is q's INTEGER PRIMARY KEY: one lookup per row) 0.01 s.
- The order written is the order run. t1 1000 rows, t2 and t3 100 each,
  `WHERE t1.b = t2.a AND t2.b = t3.a`: `FROM t1, t2, t3` 1000 rows in 0.01
  s; `FROM t1, t3, t2` the same rows in 0.44 s (t1 x t3 have no term between
  them: 100000 pairs, each meeting all of t2). EXPLAIN shows why:

```
EXPLAIN SELECT t1.a, t3.a FROM t1, t3, t2 WHERE t1.b = t2.a AND t2.b = t3.a;
Filter ((t1.b = t2.a) AND (t2.b = t3.a))
  Join
    Join
      Scan t1
      Scan t3
    Scan t2
```

Break it (verified):

1. In join_next copy the outer row without keep()
   (`op->row.cols[i] = l->cols[i];`). With an ASan build and
   DB_CACHE_PAGES=2, `SELECT p.id, length(p.pad), q.id FROM p, q WHERE p.id %
   1000 = 1` prints 256 rows, then "AddressSanitizer: heap-use-after-free ...
   READ of size 1 ... in eval expr.c ... freed by thread T0 here: ... in
   pager_shrink". A plain build printed all 900 rows correctly, with the
   default cache and with a two-page one: the freed page was not reused yet.
   The bug is silent until it is not; that is why the test runs every query
   with a two-page cache and the module is checked under a sanitizer.
2. Delete `op->inner->started = 0;`: the inner scan is never restarted, so
   only the first outer row finds partners. The join on the data set prints
   `Ada|10|30` and `Ada|12|50` and nothing for Chen or Brook.
3. Make last_table() return 0 for every column: every term lands in the
   first filter, on table 0's own row, before orders is in it. EXPLAIN shows
   `Filter (o.customer_id = c.id)` under the Join, over `Scan customers AS
   c`, and running it stops with `Error: no such column: customer_id` (the
   slot is past the end of table 0's row): a term must wait for its tables.

Known differences from sqlite3:

- sqlite3 picks the join order (and builds automatic indexes); ./db runs the
  order written. Without ORDER BY the rows come out in another order; with
  CROSS JOIN and `PRAGMA automatic_index=OFF` sqlite3 runs the same nested
  loop and the order is the same (the test checks it).
- What the written order costs, on SQLite's own joins: sqllogictest's
  select5.test (not kept in tests/; fetched from the pinned commit, run with
  `--have join`): its first 911 records, 207 of them join queries of up to
  20 tables, all pass; the 912th, 21 tables written in an order its
  conditions do not follow (line 6422), is still running when the runner
  stops it at 600 s. sqlite3 reorders and answers it at once.
- EXPLAIN QUERY PLAN for a join: later tables are always SCAN (sqlite3
  SEARCHes when an index or the rowid fits: 08.03); ORDER BY always sorts
  (sqlite3 skips the sort for, e.g., ORDER BY the outer table's rowid);
  `c.rowid = 1` on table 0 is not a lookup here (above).
- One table with an alias: `EXPLAIN QUERY PLAN SELECT * FROM customers AS x`
  prints `SCAN customers` here (05.03's code names the table) and `SCAN x` in
  sqlite3. In a join ./db names each item by its alias, as sqlite3 does.
- Kept from the core for one table: `SELECT *, b AS a FROM t ORDER BY a`
  sorts by b here, by t.a in sqlite3; `ORDER BY 5` past the last column is
  a constant here, an error in sqlite3. A result alias in WHERE (`SELECT a +
  b AS x FROM t WHERE x < 10`) works in sqlite3, not here (joins included).

Decide the boundary (from source; SQLite 3.54.1, PostgreSQL REL_18_7):

- SQLite builds no joined row. where.c, sqlite3WhereBegin's header (~6759):
  "There are Btree cursors associated with each table ... can use OP_Column
  and OP_Rowid opcodes on these cursors to extract data from the various
  tables of the loop"; expr.c sqlite3ExprCodeGetColumnOfTable emits
  `OP_Column iTabCur` (or OP_Rowid): a column reference names a cursor, not
  a slot. Its loops: one per table, "foreach row1 in t1 do / foreach row2 in
  t2 do" (same comment); with no usable index the inner table is rewound and
  scanned again per outer row (wherecode.c ~2635, `aStart[] = { OP_Rewind,
  OP_Last }`).
- PostgreSQL hands up a combined tuple, but builds it only for a pair that
  passes, and only of the values needed above (corrected by the 08.01 writer,
  below). src/backend/executor/nodeNestloop.c ExecNestLoop: for a new outer
  tuple `econtext->ecxt_outertuple = outerTupleSlot;` then "now rescan the
  inner plan" `ExecReScan(innerPlan);`, each inner tuple in
  `ecxt_innertuple`, the quals tested over the two slots, and the result
  `ExecProject(node->js.ps.ps_ProjInfo)`.
- Where conditions go: SQLite moves an inner join's ON into WHERE (select.c
  sqlite3ProcessJoin ~653, "Add the ON clause to the end of the WHERE clause,
  connected by an AND operator") and codes each term in the first loop where
  all its tables are ready (wherecode.c ~2680, `(pTerm->prereqAll &
  pLevel->notReady)!=0` skips it; the comment calls this "MySQL push-down").
- The order: where.c wherePathSolver (5846) "attempts to find the lowest
  cost path that visits each WhereLoop once"; only CROSS JOIN and outer joins
  pin it (whereLoopAddAll ~4974, "Add prerequisites to prevent reordering of
  FROM clause terms across CROSS joins and outer joins"). This engine's
  fixed order is the next lessons' question.

Read and run for the lesson text (the 08.01 writer):

- PostgreSQL REL_18_7 (scratchpad copy; configure.ac `AC_INIT([PostgreSQL],
  [18.7], ...)`; the GitHub page of nodeNestloop.c at tag REL_18_7 shows the
  same lines). nodeNestloop.c ExecNestLoop, lines 105-151: when
  `nl_NeedNewOuter`, `outerTupleSlot = ExecProcNode(outerPlan);`,
  `econtext->ecxt_outertuple = outerTupleSlot;`, then "now rescan the inner
  plan" `ExecReScan(innerPlan);`. Lines 159-160: `innerTupleSlot =
  ExecProcNode(innerPlan); econtext->ecxt_innertuple = innerTupleSlot;`.
  Lines 213-240: `if (ExecQual(joinqual, econtext))` ... `if (otherqual ==
  NULL || ExecQual(otherqual, econtext))` ... `return
  ExecProject(node->js.ps.ps_ProjInfo);`. So the quals read two slots, and
  only a passing pair is projected. How a qual names a slot: setrefs.c
  set_join_references (2324), "Modify the target list and quals of a join
  node to reference its subplans, by setting the varnos to OUTER_VAR or
  INNER_VAR and setting attno values to the result domain number of either
  the corresponding outer or inner join tuple item"; primnodes.h's Var
  comment: "At the end of planning, Var nodes appearing in upper-level plan
  nodes are reassigned to point to the outputs of their subplans". What the
  projection holds: pathnodes.h RelOptInfo, "reltarget - Default Path output
  tlist for this rel; normally contains Var and PlaceHolderVar nodes for the
  values we need to output from this relation."
- SQLite 3.54.1: whereInt.h above struct WhereLoop: each WhereLoop is
  "describing a potential way of implementing that FROM-clause term";
  where.c ~1075-1110 (constructAutomaticIndex): the automatic index is
  covering, key = the equality columns, then `extraCols = pSrc->colUsed &
  ...`, then the rowid. expr.c sqlite3ExprCodeGetColumnOfTable (4526):
  `sqlite3VdbeAddOp3(v, OP_Column, iTabCur, x, regOut);`.
- sqlite3 3.54.1 on the lesson's shop.db (customers and orders only):

```
EXPLAIN QUERY PLAN SELECT c.name, o.id, o.total FROM customers c JOIN orders o ON o.customer_id = c.id;
QUERY PLAN
|--SCAN o
`--SEARCH c USING INTEGER PRIMARY KEY (rowid=?)
(rows: Ada|10|30 Chen|11|15 Ada|12|50 Brook|13|20 Chen|14|5; ./db: Ada 10, Ada 12, Brook 13, Chen 11, Chen 14)
EXPLAIN QUERY PLAN SELECT c.name, o.id, o.total FROM customers c CROSS JOIN orders o ON o.customer_id = c.id;
QUERY PLAN
|--SCAN c
|--BLOOM FILTER ON o (customer_id=?)
`--SEARCH o USING AUTOMATIC COVERING INDEX (customer_id=?)
(rows: Ada|10|30 Ada|12|50 Brook|13|20 Chen|14|5 Chen|11|15: Chen's by total, the index's key order)
EXPLAIN QUERY PLAN SELECT a.name, c.name, o.id FROM customers a JOIN customers c ON c.city = a.city JOIN orders o ON o.customer_id = c.id WHERE a.name = 'Ada' AND o.total > 10;
QUERY PLAN
|--SCAN o
|--SEARCH c USING INTEGER PRIMARY KEY (rowid=?)
|--BLOOM FILTER ON a (name=? AND city=?)
`--SEARCH a USING AUTOMATIC PARTIAL COVERING INDEX (name=? AND city=?)
```

- Break it 1 again, on the project as `./learn files db --at 08.01` writes
  it: ASan build (`EXTRA_CFLAGS="-fsanitize=address,undefined
  -fno-omit-frame-pointer -g"`), DB_CACHE_PAGES=2, the same p and q: 256
  rows, then "heap-use-after-free ... READ of size 1 ... located 4031 bytes
  inside of 4152-byte region" (a Page struct and its 4096-byte page), exit
  134; on this macOS build the inner frames were not symbolized. The plain
  build: 900 rows, byte for byte the reference's.

### 08.02 LEFT JOIN: the row with no match

Region: src/exec.c `left_join` "the row with no match" (a function of its
own, which join_next calls: regions cannot nest, and join_next's loop is
08.01's region). Also added (@from 08.02): FromItem.left; Op.leftjoin, on,
matched (db.h); LEFT [OUTER] JOIN read by join_type (returns 1) and set on
the next item in parse_from (parse.c); in join_next, matched reset for each
outer row and the two calls of left_join; op_join makes a LEFT item's
operator "Left join on (...)" with the item's ON (exec.c); in plan_select a
LEFT JOIN's ON is not split into the filter terms, and "ON clause references
tables to its right"; " LEFT-JOIN" in explain_join_plan (plan.c).

Before (08.02 cut out): inner joins work; a LEFT JOIN parses and plans and
stops at the first pair it looks at (or, with an empty inner table, when
its inner side first runs out).

```
$ ./db shop.db "SELECT c.name, o.id FROM customers c LEFT JOIN orders o ON o.customer_id = c.id;"
db: 08.02: the row with no match not written yet          (exit 3)
```

(At 08.01 the same statement is `Error: LEFT JOIN is not supported`.)

After (shop data set, no index):

```
SELECT c.name, o.id, o.total FROM customers c LEFT JOIN orders o ON o.customer_id = c.id ORDER BY c.id, o.id;
Ada|10|30
Ada|12|50
Brook|13|20
Chen|11|15
Chen|14|5
Dee||
SELECT c.name, o.id FROM customers c LEFT JOIN orders o ON o.customer_id = c.id AND o.total > 20 ORDER BY c.id, o.id;
Ada|10
Ada|12
Brook|
Chen|
Dee|
SELECT c.name, o.id FROM customers c LEFT JOIN orders o ON o.customer_id = c.id WHERE o.total > 20 ORDER BY c.id, o.id;
Ada|10
Ada|12
SELECT c.name FROM customers c LEFT JOIN orders o ON o.customer_id = c.id WHERE o.id IS NULL;
Dee
SELECT c.name, o.id FROM customers c LEFT JOIN orders o ON o.customer_id = c.id AND c.city = 'London' ORDER BY c.id, o.id;
Ada|10
Ada|12
Brook|
Chen|11
Chen|14
Dee|
SELECT o.id, c.name FROM orders o LEFT JOIN customers c ON c.id = o.customer_id;
10|Ada
11|Chen
12|Ada
13|Brook
14|Chen
15|
EXPLAIN SELECT c.name, o.id FROM customers c LEFT JOIN orders o ON o.customer_id = c.id AND o.total > 20 WHERE c.city = 'London' AND o.id IS NULL;
Filter (o.id IS NULL)
  Left join on ((o.customer_id = c.id) AND (o.total > 20))
    Filter (c.city = 'London')
      Scan customers AS c
    Scan orders AS o
EXPLAIN QUERY PLAN SELECT * FROM customers c LEFT JOIN orders o ON o.customer_id = c.id;
QUERY PLAN
|--SCAN c
`--SCAN o LEFT-JOIN
SELECT * FROM customers c LEFT JOIN orders o ON o.customer_id = x.id JOIN customers x;
Error: ON clause references tables to its right
SELECT * FROM customers c RIGHT JOIN orders o ON o.customer_id = c.id;
Error: RIGHT JOIN is not supported
```

Facts worth knowing for the text:

- Where each condition is checked, the whole lesson: a LEFT JOIN's own ON
  is evaluated inside the join, on each pair, and only says whether the
  pair is a match; it never moves to a Filter. WHERE terms and an inner
  join's ON keep 08.01's rule (a Filter right above the operator that brings
  the last table they name), so they see the rows a LEFT join hands up, the
  NULL row too. Hence `AND o.total > 20` in ON keeps Brook, Chen and Dee
  with NULLs, and the same term in WHERE drops them (`NULL > 20` is NULL).
  A term on the outer table alone behaves the same way: in ON it only stops
  matches (`c.city = 'London'` in ON: Brook has no orders matched), in WHERE
  it drops outer rows before the join (EXPLAIN shows it under the Left join).
- The NULL row: once the inner side runs out for an outer row that matched
  nothing, every slot of the inner table, its rowid slot too, is set to NULL
  (memset: V_NULL is 0) and the row goes up once. `o.rowid` and `typeof(o.id)`
  are NULL and 'null' on it, as in sqlite3. `WHERE o.id IS NULL` is the way
  to ask for "customers with no orders" (an anti-join).
- An inner join's ON that names a LEFT JOIN's table is checked above that
  join, on the NULL rows too, even when it is written before the LEFT JOIN
  (`a JOIN b ON o.id IS NULL LEFT JOIN orders o ...`, allowed in sqlite3).
  A LEFT JOIN's ON may not name a table to its right: "ON clause references
  tables to its right" (checked after names are bound, as sqlite3 does: a
  bad name in the same statement is reported first).
- LEFT, LEFT OUTER, OUTER LEFT, LEFT LEFT, LEFT OUTER OUTER all mean LEFT
  JOIN (sqlite3JoinType combines the words as bits); LEFT INNER and LEFT
  CROSS are "unknown join type". A LEFT JOIN with no ON pairs every row,
  and an empty right table gives each left row once, NULL.

Break it (verified):

1. In plan_select add the LEFT JOIN's ON to the filter terms like an inner
   one (`if (1)` in place of `if (!sc->from[k].left)`): the ON then also
   runs in a Filter above the Left join, on the NULL row, where it is NULL.
   The LEFT JOIN of the data set prints Ada 10, Ada 12, Brook 13, Chen 11,
   Chen 14 and no Dee: an inner join. EXPLAIN shows `Filter (o.customer_id
   = c.id)` over `Left join on (o.customer_id = c.id)`.
2. In left_join delete `op->matched = 1;`: no outer row is ever "matched",
   so every one also gets its NULL row: `Ada|`, `Ada|10`, `Ada|12`,
   `Brook|`, `Brook|13`, ... `Dee|`.
3. In join_next delete `op->matched = 0;` (the reset for a new outer row):
   after Ada's first match nothing is ever NULL-filled again. The data set
   prints no Dee, and `orders o LEFT JOIN customers c ON c.id =
   o.customer_id` loses order 15.

Known differences from sqlite3:

- Row order with no ORDER BY: sqlite3 keeps a LEFT JOIN in the order
  written, but it builds automatic indexes (A2) and turns a LEFT JOIN whose
  WHERE rejects the NULL row into an inner join, which it may reorder
  (select.c ~7889, "OUTER JOIN strength reduction"). With `PRAGMA
  automatic_index=OFF` the order is the same (the test checks it).
- sqlite3 drops a LEFT JOIN table that is never read and matches at most
  one row (where.c whereOmitNoopJoin); EXPLAIN QUERY PLAN then lists one
  table fewer. ./db always reads it.
- The fuzzer (tests/fuzz), with 08.02 and 08.03 in: `--features
  core,join,leftjoin --n 3000 --seed 1`, 75056 statements, 17966 SELECTs,
  572052 rows compared, 0 failing (203 s); 800 more at seed 7 on an
  `-fsanitize=address,undefined` build with DB_CACHE_PAGES=2, 0 failing.
- RIGHT and FULL JOIN (sqlite3 3.54.1 has them: whereInt.h WhereRightJoin,
  wherecode.c sqlite3WhereRightJoinLoop) and NATURAL/USING are refused by
  name.

Decide the boundary (from source; SQLite 3.54.1, PostgreSQL REL_18_7):

- SQLite does the same thing with a flag in a register. wherecode.c
  sqlite3WhereCodeOneLoopStart: `OP_Integer, 0, pLevel->iLeftJoin` "init
  LEFT JOIN match flag" (1597) before the inner loop; after the ON terms
  pass, `OP_Integer, 1` "record LEFT JOIN hit" (2833); then "WHERE clause
  constraints must be deferred until after outer join row elimination has
  completed, since WHERE clause constraints apply to the results of the
  OUTER JOIN" (2854). where.c sqlite3WhereEnd: when the flag is still 0,
  `OP_NullRow` on the table's cursor (7711) and a jump back to just after
  the "hit", so WHERE and the output run once more on a row of NULLs.
  EXPLAIN QUERY PLAN's " LEFT-JOIN": wherecode.c 212. The error: select.c
  selectCheckOnClausesExpr (7532), "%s references tables to its right"
  (7579), run from resolve.c (2128) after the names are resolved.
- PostgreSQL, nodeNestloop.c ExecNestLoop: when the inner side runs out,
  `if (!node->nl_MatchedOuter && (node->js.jointype == JOIN_LEFT || ...))`
  "Generate a fake join tuple with nulls for the inner tuple, and return it
  if it passes the non-join quals" (`ecxt_innertuple =
  node->nl_NullInnerTupleSlot`); and "Only the joinquals determine
  MatchedOuter status, but all quals must pass to actually return the
  tuple." Its joinquals are the ON, its "otherqual" the WHERE terms pushed
  into the join: the same split as here, kept on one node.

Read and run for the lesson text (the 08.02 writer; SQLite 3.54.1, the
scratchpad tree, VERSION 3.54.1, manifest.uuid 555e07ef...):

- A correction to the block above: sqlite3WhereEnd jumps to
  `pLevel->addrFirst` (where.c 7736), which wherecode.c 2831 sets to the
  address of the "record LEFT JOIN hit" instruction itself, so the NULL
  row goes back to the hit, not to just after it (the research file's
  listing agrees: `Goto 0 9`, and 9 is `Integer 1 1`). Setting the flag
  to 1 there is what stops a second NULL row (`IfPos` at the loop's end).
- OUTER JOIN strength reduction: select.c 7881-7907, in sqlite3Select's
  loop over the FROM items: "If terms of the i-th table are used in the
  WHERE clause in such a way that the i-th table cannot be the NULL row
  of a join, then perform the appropriate simplification. This is called
  "OUTER JOIN strength reduction" in the SQLite documentation."; the test
  `(pItem->fg.jointype & (JT_LEFT|JT_LTORJ))!=0 &&
  sqlite3ExprImpliesNonNullRow(p->pWhere, pItem->iCursor, ...)`, then
  `pItem->fg.jointype &= ~(JT_LEFT|JT_OUTER);` and `unsetJoinExpr(...)`.
  The proof: expr.c sqlite3ExprImpliesNonNullRow (7150), "Return true
  ... if expression p can only be true if at least one column of table
  iTab is non-null"; its walker impliesNotNullRow (7019): "False
  positives ... are deadly, but false-negatives ... is a harmless missed
  optimization"; TK_ISNULL, TK_IS, TK_FUNCTION, TK_CASE and others end
  the walk (7032-7048); for AND/OR both sides must imply it (7057).
  Once JT_LEFT is cleared, whereLoopAddAll (4972) no longer adds the
  prerequisites that pin the order, so the planner may reorder.
- sqlite3 3.54.1 on shop.db (EXPLAIN QUERY PLAN): `... LEFT JOIN orders o
  ON o.customer_id = c.id AND o.total > 25` is `SCAN c`, `BLOOM FILTER ON
  o (customer_id=?)`, `SEARCH o USING AUTOMATIC PARTIAL COVERING INDEX
  (customer_id=?) LEFT-JOIN`; the same with `WHERE o.total > 25` is `SCAN
  o`, `SEARCH c USING INTEGER PRIMARY KEY (rowid=?)` (reduced, then
  reordered); `WHERE o.id IS NULL`, `WHERE o.total > 25 OR o.id IS NULL`
  and `WHERE coalesce(o.total, 0) > 25` keep LEFT-JOIN with c outside
  (the last rejects the NULL row too: a missed reduction, not an error);
  `LEFT JOIN orders o WHERE o.customer_id = c.id` (the ON moved to WHERE)
  is reduced and reordered like the second.
- Fetched for Go deeper: sqlite.org/optoverview.html, section 7 (#joins),
  "outer joins are neither commutative nor associative and hence will
  not be reordered"; section 16
  (#the_outer_join_strength_reduction_optimization), "A LEFT or RIGHT
  JOIN can be converted into an ordinary (INNER) JOIN ... if there are
  terms in the WHERE clause that guarantee the same result after
  simplification"; select.c at tag version-3.54.1 on GitHub shows the
  code above; nodeNestloop.c at REL_18_7 on GitHub shows the lines of the
  PostgreSQL bullet above.
- Run on ./db at 08.02 (sqlite3 gives the same rows): `orders o LEFT JOIN
  customers c ON c.id = o.customer_id JOIN customers m ON m.city = c.city
  WHERE o.id >= 14` gives 14|Chen|Ada, 14|Chen|Chen (order 15's NULL row
  fails the inner ON); with `LEFT JOIN customers m` also 15||; writing
  the inner join first (`orders o JOIN customers m ON m.city = c.city
  LEFT JOIN customers c ON ...`) gives the two 14 rows, no 15: an inner
  ON naming a LEFT JOIN's table is checked above that join either way.
  With one LEFT and one inner join and the same ONs, the order of the
  two joins never changes the rows; which table is written first does.
- The rowid slot, verified: with left_join's NULL loop stopped one short
  (`i < op->row.ncols - 1`), `SELECT c.name, o.id, o.rowid ...` prints
  `Dee||15` (the last order the scan read) and `WHERE o.rowid IS NULL`
  prints nothing; `WHERE o.id IS NULL` still prints Dee.

### 08.03 An index for the inner loop

Regions: src/plan.c `choose_join_access` "choose how to read the inner
table"; src/exec.c `scan_rebind` "start the inner side for this outer row".
Also added (@from 08.03): key_item, join_key, index_affinity_ok (plan.c,
before choose_join_access); in plan_select's join loop, the call, the scan
made from a copy of the Access with no key (op_scan must not evaluate it)
and the real Access stored in the scan; join_next calls scan_rebind where
08.01 had `op->inner->started = 0;`; the two prototypes (db.h).
scan_rebind returns int, not void as the design had it: a key can fail to
evaluate (`abs(-9223372036854775808)` is "integer overflow", in sqlite3
too), and the error must stop the statement.

Before (08.03 cut out): every join stops in the planner; one table is the
core's plan.

```
$ ./db shop.db "SELECT c.name, o.id FROM customers c JOIN orders o ON o.customer_id = c.id;"
db: 08.03: choose how to read the inner table not written yet          (exit 3)
$ ./db shop.db "SELECT * FROM customers WHERE id = 2;"
2|Brook|Paris
```

After (shop data set):

```
EXPLAIN QUERY PLAN SELECT c.name, o.id, o.total FROM customers c JOIN orders o ON o.customer_id = c.id;
QUERY PLAN
|--SCAN c
`--SCAN o
CREATE INDEX orders_customer ON orders(customer_id);
EXPLAIN SELECT c.name, o.id, o.total FROM customers c JOIN orders o ON o.customer_id = c.id;
Filter (o.customer_id = c.id)
  Join
    Scan customers AS c
    Index lookup orders using orders_customer (customer_id = ?)
EXPLAIN QUERY PLAN SELECT c.name, o.id, o.total FROM customers c JOIN orders o ON o.customer_id = c.id;
QUERY PLAN
|--SCAN c
`--SEARCH o USING INDEX orders_customer (customer_id=?)
SELECT c.name, o.id, o.total FROM customers c JOIN orders o ON o.customer_id = c.id;
Ada|10|30
Ada|12|50
Brook|13|20
Chen|11|15
Chen|14|5
EXPLAIN SELECT o.id, c.name FROM orders o JOIN customers c ON c.id = o.customer_id;
Filter (c.id = o.customer_id)
  Join
    Scan orders AS o
    Rowid lookup customers rowid = ?
EXPLAIN QUERY PLAN SELECT o.id, c.name FROM orders o JOIN customers c ON c.id = o.customer_id;
QUERY PLAN
|--SCAN o
`--SEARCH c USING INTEGER PRIMARY KEY (rowid=?)
EXPLAIN QUERY PLAN SELECT * FROM customers c LEFT JOIN orders o ON o.customer_id = c.id;
QUERY PLAN
|--SCAN c
`--SEARCH o USING INDEX orders_customer (customer_id=?) LEFT-JOIN
EXPLAIN QUERY PLAN SELECT * FROM customers c LEFT JOIN orders o ON 1 WHERE o.customer_id = c.id;
QUERY PLAN
|--SCAN c
`--SCAN o LEFT-JOIN
EXPLAIN QUERY PLAN SELECT * FROM customers c JOIN orders o ON o.customer_id + 0 = c.id;
QUERY PLAN
|--SCAN c
`--SCAN o
EXPLAIN QUERY PLAN SELECT * FROM customers c JOIN orders o ON o.customer_id = c.id * 1;
QUERY PLAN
|--SCAN c
`--SEARCH o USING INDEX orders_customer (customer_id=?)
```

The measurement (the lesson's and the cost figure's numbers). shop.py, as
the reader writes it:

```
print('CREATE TABLE customers(id INTEGER PRIMARY KEY, name TEXT, city TEXT);')
print('CREATE TABLE orders(id INTEGER PRIMARY KEY, customer_id INTEGER, total INTEGER);')
print('BEGIN;')
cities = ['London', 'Paris', 'Oslo', 'Rome', 'Lima']
for i in range(1, 1001): print(f"INSERT INTO customers VALUES({i}, 'customer {i}', '{cities[i % 5]}');")
for i in range(1, 20001): print(f"INSERT INTO orders VALUES({i}, {i * 7919 % 1000 + 1}, {i % 100});")
print('COMMIT;')
```

69 pages (134 with the index). The join `SELECT c.name, o.id, o.total ...`
(20000 rows, to /dev/null), DB_STATS=1, best of three, Apple M4 Pro.
"Page requests" is cache hits + misses, every page the B-tree code asked
for; "pages read" is what came from the file, which with the default cache
(500 pages) is each page once whatever the plan:

```
                                                     time     page requests   pages read (cache 500 / 2)
customers c JOIN orders o, no index (nested loop)   0.873 s   60,239,036      69 / 4678
customers c JOIN orders o, orders_customer index    0.014 s      147,241     134 / 4872
orders o JOIN customers c (rowid lookup)            0.013 s      200,724      69 /  674
```

The nested loop asks for every page of orders once per customer (1000 x
about 60 pages); the index asks for a path down the index and one down
the table per order; the other order asks for a path down customers (2
levels) per order and needs no index at all. With DB_CACHE_PAGES=2 the
file reads mostly measure the cache, which only shrinks every 256 output
rows (pager_shrink in the statement loop), so the lesson should show page
requests. sqlite3 on the same files: 0.012 s, 0.013 s and 0.011 s (it
builds an automatic index or reorders); forced into the written nested loop
(automatic_index=OFF, CROSS JOIN, `o.customer_id + 0`) 0.42 s.

Facts worth knowing for the text:

- Which terms may give a key: for item k, a term `column of k = key`
  (either way round) whose key reads only items before k, or nothing (a
  constant); among item k's own ON if it is a LEFT JOIN, else among the
  WHERE and inner ON terms (any of them: `a JOIN b ON 1 JOIN c ON b.x =
  a.y` looks b up by c's ON). A LEFT JOIN table cannot take a key from WHERE
  (EXPLAIN QUERY PLAN above): narrowing its rows by WHERE would change what
  matches. Rowid (or the INTEGER PRIMARY KEY) first, then each index by its
  first column, else a scan. A key may be any expression (`c.id * 1`,
  `coalesce(o.customer_id, 4)`, `c.rowid`: table 0's rowid is in the join's
  row by the time the key is evaluated); one that reads the inner table
  itself (`o.customer_id + 0 = c.id` puts o on the key side) is not a key.
- The term stays where it was (its Filter, or the LEFT JOIN's ON): a
  rowid key 1.5 reads rowids 1 and 2 (rowid_bound rounds down and up) and
  the Filter drops both. The lookup only narrows what is read (invariant 3).
- The key is evaluated once per outer row, in scan_rebind, against the
  join's row. An index key is turned into a record and `hi` is decoded back
  out of that record, so neither points into the row arena: a Filter above
  the join resets that arena whenever it drops a row, in the middle of the
  inner loop. A NULL key reads nothing (`= NULL` is never true).
- The affinity rule is sqlite3IndexAffinityOk (expr.c 395):
  ```
  int sqlite3IndexAffinityOk(const Expr *pExpr, char idx_affinity){
    char aff = comparisonAffinity(pExpr);
    if( aff<SQLITE_AFF_TEXT ){
      return 1;
    }
    if( aff==SQLITE_AFF_TEXT ){
      return idx_affinity==SQLITE_AFF_TEXT;
    }
    return sqlite3IsNumericAffinity(idx_affinity);
  }
  ```
  comparisonAffinity (372) is sqlite3CompareAffinity (350) of the two sides:
  two columns give NUMERIC if either is numeric, else BLOB; a column and a
  non-column give the column's affinity. Worked out per pairing (X the
  indexed column, Y the key): X INTEGER, REAL or NUMERIC: always (the key is
  what gets converted); X TEXT or BLOB: unless Y is a column of numeric
  affinity, for then the comparison converts X's stored values ('1', '1.0',
  ' 1', '01' all equal 1), which no lookup of one key finds. That is
  index_affinity_ok(), and the test checks EXPLAIN QUERY PLAN against
  sqlite3 for all 6 x 6 pairings, three ways each.
- Where it departs from the design: the design allowed a BLOB (none) column
  only a key of no affinity. sqlite3 also SEARCHes a BLOB index with a TEXT
  column's key (both columns, neither numeric: BLOB comparison affinity,
  neither side converted), and so does ./db: such a lookup cannot lose a
  row, and EXPLAIN QUERY PLAN agrees with sqlite3's.
- The key gets the indexed column's affinity (as bound_value does for a
  constant). sqlite3 applies the index's affinity too, except where the
  comparison affinity is BLOB, when it applies none (wherecode.c
  codeAllEqualityTerms 996-1000). They differ only for a TEXT index with a
  BLOB column's key: ./db makes a number key text, sqlite3 keeps it a
  number. Neither finds a row the term accepts, since a TEXT column holds
  no numbers.
- Looked-up rows come out in index order (key, then rowid), the same order
  as a scan's for one key: so with no ORDER BY the rows of `customers c
  JOIN orders o` come out in the same order with or without the index.

Break it (verified):

1. Make index_affinity_ok always return 1. `codes(k TEXT)` holding '1',
   '1.0', ' 1', '01', '2' with an index, and `nums(n INTEGER)` holding 1
   and 2: `SELECT n, what FROM nums JOIN codes ON codes.k = nums.n` gives 5
   rows scanned (and in sqlite3), 2 looked up (`1|text 1`, `2|text 2`):
   the lookup finds only the key '1', the comparison would have turned
   '1.0', ' 1' and '01' into 1. EXPLAIN QUERY PLAN says SEARCH where
   sqlite3 says SCAN. Nothing fails; rows are silently lost.
2. In join_next put back 08.02's `op->inner->started = 0;` in place of
   scan_rebind: the lookup is never given a key (op_scan was made with
   none) and its `done` is never cleared. On shop.py's data the index join
   prints 20 rows (customer 1's, from a walk of the whole index), not
   20000, and the rowid one 1 row. Each outer row must restart the inner
   side and give it its own key.

Known differences from sqlite3:

- Lookups only on `=` and only on an index's first column; sqlite3 also
  uses IS, IN, ranges, several columns of one index, covering indexes
  ("USING COVERING INDEX", no table read), and when no index fits it builds
  an automatic one (EXPLAIN QUERY PLAN: AUTOMATIC COVERING INDEX, with a
  BLOOM FILTER line). Compare plans with `PRAGMA automatic_index=OFF`,
  CROSS JOIN and `SELECT *` (so no index covers the query).
- Which of two fitting indexes: the first in the table's list here;
  sqlite3 by cost.
- sqllogictest select5.test (tables t1..t64 of `aN INTEGER PRIMARY KEY, bN
  INTEGER, xN VARCHAR(40)`, joins of many of them by `aN = bM` terms) with
  `--have join`, from build/: the same 911 records pass as at 08.01, now in
  67.2 s against 105.7 s for the project at 08.02 (`--limit 911`, the same
  machine). The 912th (line 6422, 21 tables) still runs until the runner
  stops it at 600 s: its first tables are written before the tables their
  terms name (t64 is second; its terms `b57 = a64` and `b64 = a18` name
  t57, 19th, and t18, 12th), so almost no table has a key from the tables
  before it. Only a planner
  that changes the order (sqlite3's wherePathSolver) answers it.

Decide the boundary (from source; SQLite 3.54.1, PostgreSQL REL_18_7):

- When no index fits, SQLite builds one for the query: where.c
  constructAutomaticIndex (986), run once (`OP_Once`) inside the outer loop,
  a covering index of the join columns, the other columns used and the
  rowid, plus a Bloom filter. With no ANALYZE every table is guessed at
  1,048,576 rows (build.c ~1374), so it does so even for a three-row table.
  It has no hash join: the automatic index is its stand-in (the six cases of
  wherecode.c sqlite3WhereCodeOneLoopStart; no "hash join" anywhere in
  src/).
- PostgreSQL has all three. nodeNestloop.c (with an index scan inside it,
  as here), nodeHashjoin.c ("This is based on the 'hybrid hash join'
  algorithm"; "the inner plan is used to build ... the hash table"; "If the
  inner side tuples of a hash join do not fit in memory, the hash join can
  be executed in multiple batches"), and nodeMergejoin.c ("routines
  supporting merge joins", inputs sorted on the join key). The planner tries
  them all: optimizer/path/joinpath.c add_paths_to_joinrel "consider all
  possible paths that use the two component rels as outer and inner rel
  ... Add these paths ... if they survive comparison with other paths"
  (mergejoin, nestloop, hash: its steps 1-4). The choice: an index costs a
  write on every INSERT and lives in the file; a hash table costs a pass
  over the inner table on every query.

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

Read for the lesson's Decide the boundary (written after the code):

- SQLite 3.54.1: sqlite3Insert calls sqlite3GenerateConstraintChecks
  (insert.c 1565) and only then sqlite3CompleteInsertion (1581); update.c
  does the same (1043, 1109). One writer: wal.c 3783 "There can only be a
  single writer active at a time."; os.h 86, a RESERVED lock is held by a
  single process at a time.
- PostgreSQL REL_18_7, src/backend/access/nbtree/nbtinsert.c (fetched from
  the tag on GitHub): _bt_doinsert (102) is called with the heap tuple
  already stored ("By here, itup is filled in, including the TID.", 82;
  executor/nodeModifyTable.c ExecInsert calls table_tuple_insert at 1233,
  then ExecInsertIndexTuples at 1239). A key with any NULL skips the check
  (115-137: "core code considers NULL unequal to every value, including
  NULL"). _bt_search_insert returns the first leaf the key could be on,
  write-locked (162-167); _bt_check_unique runs under that lock, which is
  held until the insert: "only one would-be inserter can be making the
  check at one time" (187-196). _bt_check_unique (408) walks the equal
  entries; for each it checks the heap with a dirty snapshot
  (table_index_fetch_tuple_check, 560), so entries of dead versions are not
  conflicts; an in-progress inserter or deleter is returned as xwait
  (586-597), and _bt_doinsert releases the page, calls XactLockTableWait
  and starts the search over (213-232); a live duplicate is ereport ERROR
  "duplicate key value violates unique constraint" (666-673). Several
  entries with one key in a unique index are normal there (versions from
  UPDATEs: nbtree/README, "Deduplication in unique indexes"). Immediate
  unique indexes pass UNIQUE_CHECK_YES, deferrable ones UNIQUE_CHECK_PARTIAL
  (executor/execIndexing.c 431-438).
- SQLite's file format page (fileformat2.html, 2.6) says N in
  sqlite_autoindex_TABLE_N increases "with each constraint seen"; the
  source and the runs say a constraint that makes no index (the INTEGER
  PRIMARY KEY, a repeat) takes no number. users(id INTEGER PRIMARY KEY,
  email TEXT UNIQUE, name TEXT) gets sqlite_autoindex_users_1.
- In a terminal, Homebrew sqlite3 3.54.1 prints query results in box mode;
  a transcript needs `sqlite3 -list` (errors are unaffected).

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
