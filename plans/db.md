# Plan: track `db` - a SQL database in C, from scratch

Status: plan (direction set by Fable; implementation by Opus agents).

## What the learner ends with

A single-file SQL database engine in C, in the spirit of SQLite: a REPL
and a C API, tables and indexes stored in B-trees on disk, a SQL subset
with a query planner, and atomic, durable transactions that survive a
crash. Judged with real benchmarks against sqlite3 on the same machine.

## Decisions

- Language: C (C11), no dependencies beyond libc. One `db` binary (REPL
  and one-shot `db file.db "sql"`), plus a small library the REPL uses.
- File format: aim to be SQLite-compatible for the database file (page
  header, table and index B-tree pages, record format, the schema table),
  so `sqlite3` can open a file we wrote and we can open one it wrote.
  This is the strongest possible check and real value. The journal/WAL
  may be our own format. If compatibility would put the rest of the
  track at risk, fall back to our own format and say so.
- Execution: iterator (Volcano) operators, not a bytecode VM: easier to
  build one piece at a time, and still how many real engines work.
- Tests are internal. Three kinds:
  1. differential: run the same SQL in our engine and in real sqlite3,
     compare results (and, if compatible, cross-open the files);
  2. crash: kill the process at injected points during commit, reopen,
     check atomicity and integrity;
  3. benchmarks: fixed workloads, reported as ops/sec and file size, with
     sqlite3 as the reference line. Benchmarks report; they do not gate
     on beating sqlite3, only on not regressing by a large factor.
- Learner check is running it: the REPL, and `./learn bench db`.

## Modules

00 The workbench
  00.01 How a database works (the whole engine; building and running the shell)
  00.02 Measuring a database (the benchmark harness)
01 Pages
  01.01 The database file as pages (pager)   01.02 The page cache
  01.03 Records: varints and serial types
02 The B-tree
  02.01 A leaf page: cells and search        02.02 Insert and split
  02.03 Interior pages and the root          02.04 Cursors and range scans
  02.05 Delete and free pages
03 SQL
  03.01 The tokenizer     03.02 The parser and the AST
  03.03 The schema: CREATE TABLE and the catalog
04 Running queries
  04.01 INSERT and a full table scan         04.02 WHERE and expressions
  04.03 ORDER BY and LIMIT                   04.04 UPDATE and DELETE
05 Indexes and the planner
  05.01 An index is a B-tree                 05.02 Index lookups and range scans
  05.03 Choosing a plan, and EXPLAIN
06 Transactions
  06.01 What a crash does to a half-written page
  06.02 The rollback journal and atomic commit
  06.03 Recovery                             06.04 A write-ahead log
07 Fast
  07.01 Reading the benchmark                07.02 Where the time goes
  07.03 One more optimisation, measured

## Optional extensions (after the core; each `optional: true`)

Built one at a time once the core engine is in, because they share files.
Each gets build regions, internal tests and its own benchmark.

08 More SQL (being built, 2026-11-25; see "Module 08" below)
  08.01 Two tables in one query: the nested loop join
  08.02 LEFT JOIN: the row with no match
  08.03 An index for the inner loop
  08.04 Aggregates: one row from many
  08.05 GROUP BY, HAVING and DISTINCT
  08.06 Subqueries: a query inside a query
  08.07 UNIQUE: a constraint is an index lookup
Not started, in the order proposed to the owner on 2026-11-25:
  A planner that counts: ANALYZE and sqlite_stat1, cost estimates, join
    order, pushing work down (needs 08's joins)
  Fast, part two (more lessons in 07): freeblocks instead of rewriting a
    page on delete, a sorted bulk index build
  Many readers, one writer: file locks, readers on a snapshot while a
    writer commits (WAL), checkpoints under load. Benchmark: read
    throughput while a writer runs.
  A server and an event loop: a blocking TCP server, a wire protocol,
    non-blocking sockets and poll(), kqueue/epoll with timers and slow
    clients, a client library, prepared statements and parameters.
    Benchmark: queries/sec and p50/p99 latency with 1, 10 and 100 clients.
    This is the only async work in the plan; the engine has none today.
  Operating it: backup while running, shipping the WAL to a follower,
    metrics and slow-query logging.

Order changed from the first plan (server first): a server on an engine
that cannot join two tables shows sockets, not a database.

## Module 08 (More SQL): how it is being built

- Design by Fable, from SQLite 3.54.1's and PostgreSQL 18's source (read
  at the tags, with real sqlite3 runs); code, lessons and art by Opus
  agents. Left out and refused by name: NATURAL/USING, RIGHT and FULL
  JOIN, subqueries in FROM, views, UNION, window functions, group_concat,
  INSERT ... SELECT, INSERT OR ..., ON CONFLICT.
- Decisions: a joined row is every table's values side by side (each table
  owns ncols + 1 slots, the last its rowid), so eval() does not change;
  joins run in the order written (choosing an order is the planner
  module's); a condition is checked as soon as its tables are in the row;
  GROUP BY sorts, as SQLite always does; DISTINCT uses a hash set and keeps
  first-seen order, as sqlite3's output does; a subquery that names nothing
  outside itself runs once; a one-table plain query runs the core's code
  path unchanged.
- Tests (the owner, 2026-11-25: everything backed by tests, so a learner
  never meets a bug): a differential test per lesson against sqlite3,
  sqllogictest with the module's features no longer skipped, a seeded
  differential fuzzer (tests/fuzz), a sanitizer build with a two-page
  cache, check-skeleton, check-timeline, the core lessons' projects byte
  for byte unchanged, and ./learn verify on every transcript.

## Benchmarks (fixed workloads, 100k rows unless noted)

insert autocommit (10k); insert in one transaction; point lookup by
primary key; range scan; lookup by secondary index; update by key;
delete by key; file size. Each run on our engine and on sqlite3.

## Build order for the agents

1. Engine: the reference implementation with `@build` regions, internal
   tests, benchmarks, track.py (build, run, fixtures), check-skeleton clean.
2. Lessons and figures, in parallel by module, from the finished code.
3. Review: full internal run, benchmark table, site pass.

## Step 1 as built (engine; see tracks/db/NOTES.md)

- File format: SQLite-compatible, decided after a spike that wrote pages,
  a hot journal and a WAL by hand and had sqlite3 accept all three. The
  journal and WAL use SQLite's formats as well (the plan allowed our own),
  so sqlite3 recovers our crashes and we recover its.
- Lessons without code (labs): 00.01, 00.02, 06.01, 07.01, 07.02. The
  other 22 lessons own 48 @build regions.
- 07.03's optimisation is the append split: rows arriving in rowid order
  split at the end, so table pages stay full (file size equals sqlite3's
  for sequential inserts; twice it without).
- Benchmark op counts: autocommit inserts 10k; one-transaction inserts
  100k; point lookups 100k; range scans 1k of 100 rows; index lookups
  100k; updates and deletes 10k each in one transaction. File size is
  taken after the 100k inserts and CREATE INDEX.
- Not in the plan, added because they were needed: statement savepoints
  (a failing statement inside BEGIN undoes only itself); tables sqlite3
  made with features we lack (UNIQUE, AUTOINCREMENT, triggers, ...) are
  read-only; `./learn bench <track>` in the harness.
