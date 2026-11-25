# sqllogictest for the db track

Internal, for authors: SQLite's own query test corpus, run against the
reference engine. Learners never see it (tests/ is not part of any project
the site shows), and no lesson mentions it.

## Where it comes from

- Upstream: sqllogictest, by D. Richard Hipp, https://www.sqlite.org/sqllogictest/
  (a Fossil repository; its web pages put a browser check in front of
  scripted downloads).
- Fetched from its GitHub mirror, https://github.com/gregrahn/sqllogictest,
  at commit c93ac416f05635ff5cc490009add936d9753d01d (2026-10-07, "Merge
  the 3.54.0 beta sources for testing"). Every file was checked against its
  git blob id in that commit's tree. MANIFEST gives the SHA-256 and size of
  every script of test/ at that commit: 622 of them, index/ (214),
  evidence/ (12), random/ (391) and select1-5.
- Licence: COPYRIGHT.md here, copied unchanged from the top of that
  repository (src/sqllogictest.c carries the same text): "As far as the
  author is concerned, you can redistribute it and/or modify the code as
  you see fit. No attribution is required." It names the GPL, BSD, MIT and
  CC0 licences, whichever best applies. The test scripts carry no notice of
  their own. NOTICE at the top of this repo records it too.

## What is kept here

test/ holds 26 scripts, unchanged (some end their lines with CRLF, as
upstream has them; .gitattributes keeps git from touching them), 26.8 MB.
The core's 15, 13.9 MB, one table each:

| script | bytes | records |
|---|---:|---:|
| test/index/between/1000/slt_good_0.test | 1310358 | 3792 |
| test/index/commute/10/slt_good_10.test | 785768 | 4261 |
| test/index/commute/1000/slt_good_0.test | 828761 | 4741 |
| test/index/delete/1/slt_good_0.test | 1028342 | 10907 |
| test/index/delete/1000/slt_good_1.test | 1040842 | 11838 |
| test/index/in/10/slt_good_5.test | 4054789 | 10038 |
| test/index/orderby/10/slt_good_4.test | 1736641 | 10052 |
| test/index/orderby_nosort/10/slt_good_14.test | 1688396 | 10052 |
| test/index/random/1000/slt_good_1.test | 102099 | 1061 |
| test/index/random/1000/slt_good_2.test | 97765 | 1027 |
| test/index/random/1000/slt_good_3.test | 97979 | 1033 |
| test/index/random/1000/slt_good_4.test | 91231 | 1037 |
| test/index/view/10000/slt_good_0.test | 1025951 | 10712 |
| test/evidence/in1.test | 14926 | 216 |
| test/evidence/in2.test | 5231 | 54 |

The number in an index/ path is the rows per table. The two evidence/
scripts are there for the one engine bug the corpus found (below).

Module 08's 11 (12.7 MB), chosen for the SQL each 08 lesson adds, by the
records that run (the counts are of records that pass with every --have):

| script | bytes | records | run | joins | aggregates | GROUP BY | DISTINCT | subqueries |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| test/select1.test | 257999 | 1031 | 531 | 0 | 155 | 0 | 0 | 194 |
| test/select2.test | 238643 | 1031 | 550 | 0 | 174 | 0 | 0 | 211 |
| test/select3.test | 855728 | 3351 | 1719 | 0 | 498 | 0 | 0 | 668 |
| test/select4.test | 1194685 | 3857 | 2857 | 1814 | 0 | 0 | 0 | 0 |
| test/random/select/slt_good_0.test | 1244902 | 11084 | 9587 | 1475 | 0 | 0 | 2480 | 0 |
| test/random/select/slt_good_1.test | 1301591 | 11319 | 9480 | 1158 | 0 | 0 | 2400 | 0 |
| test/random/groupby/slt_good_0.test | 1231168 | 10559 | 9712 | 1355 | 0 | 9700 | 2411 | 0 |
| test/random/groupby/slt_good_9.test | 1193790 | 10245 | 9979 | 86 | 284 | 9967 | 2780 | 0 |
| test/random/aggregates/slt_good_106.test | 1860392 | 13971 | 8707 | 276 | 2116 | 0 | 2658 | 0 |
| test/random/aggregates/slt_good_60.test | 1851041 | 13983 | 8699 | 304 | 2118 | 0 | 2606 | 0 |
| test/random/expr/slt_good_54.test | 1636904 | 15700 | 8254 | 0 | 3725 | 0 | 1964 | 0 |

select1-3 hold aggregates beside correlated scalar and EXISTS subqueries;
select4 comma joins of up to three indexed tables (and compound SELECTs,
skipped); random/ joins of two and three tables, GROUP BY and HAVING,
DISTINCT, and aggregates of expressions; the two random/aggregates scripts
hold 9 LEFT JOINs that run between them (the corpus has few: 177 run in
all, every one in random/).
UNIQUE comes from the core's index/ scripts, whose 974 CREATE UNIQUE INDEX
statements (870 in index/delete/1) are sent as written with --have unique.

Which lesson runs which (each through track.py's sqllogictest(t, have,
scripts): the quick slice, or every record with SLT=full):

| lesson | --have | scripts |
|---|---|---|
| 05.03 | (none) | all 26 |
| 08.01 | join | select4, random/select 0 and 1 |
| 08.02 | join | random/aggregates 106 and 60 (their LEFT JOINs) |
| 08.03 | join | 08.01's, and random/groupby 0 |
| 08.04 | join, aggregate | select1-3, random/aggregates 106 and 60, random/expr 54 |
| 08.05 | ... groupby, distinct | random/groupby 0 and 9, random/select 1, random/aggregates 106 |
| 08.06 | ... subquery | select1-3, evidence/in1 and in2, index/in/10/slt_good_5 |
| 08.07 | unique | index/delete/1 and 1000, index/commute/1000, evidence/in1 |

## Running it

    ./learn test db --ref                    includes the quick slices (05.03's and each
                                             08 lesson's): the first 1500 records of each script
    SLT=full ./learn test db 05.03 08 --ref  every record of every script, each 08 lesson's
                                             with the SQL it adds no longer skipped
    python3 tracks/db/tests/sqllogictest/runner.py [--quick] [files or dirs]
                                             the runner itself (make the engine first);
                                             --help for its options
    python3 tracks/db/tests/sqllogictest/runner.py --engine sqlite3
                                             the same records through the real sqlite3:
                                             a check of the runner, which must pass all

A long run, outside the repo:

    python3 tracks/db/tests/sqllogictest/fetch.py                    # 1.1 GB into build/sqllogictest/
    python3 tracks/db/tests/sqllogictest/runner.py --have join,aggregate,groupby,distinct,subquery,unique \
        build/sqllogictest/test/index build/sqllogictest/test/random ...
    python3 tracks/db/tests/sqllogictest/fetch.py --verify           # the kept files against MANIFEST

(select5.test needs a time limit of its own: below.)

runner.py's docstring says how records run, what counts as a skip (SQL the
engine does not have, such as CAST, CASE, views, compound SELECTs, functions
it lacks, the bitwise operators, x IN table, and without --have module 08's
joins, aggregates, GROUP BY, DISTINCT and subqueries; and what such a
skipped statement would have changed) and what is emulated (INSERT INTO a
SELECT * FROM b replayed as b's INSERTs; DESC indexes, and UNIQUE ones
without --have unique, made ordinary). A script runs inside one BEGIN ...
COMMIT (--autocommit runs it statement by statement, some 40 times slower),
and sqlite3's PRAGMA integrity_check then checks the file it left.

## Results (2026-11-25, Apple M4 Pro, sqlite3 3.54.1, the finished module 08)

With every --have (join, aggregate, groupby, distinct, subquery, unique):

- Kept scripts: 176952 records, 150166 run, all passed, 26786 skipped
  (other engines 16880, CAST 5288, CASE 2715, compound SELECT 1060, view 420,
  nullif 243, INSERT ... SELECT 65, parenthesised joins 43, x IN table 42,
  subqueries in FROM 30); 45 s, 37 of them select4's three-table joins.
  Without --have (05.03's slice, and the core alone): 105441 run, all passed.
- The whole corpus, all 622 scripts (7420230 records): 5244452 run, all
  passed, 2175778 skipped (other engines 1480834, CAST 437169, CASE 102848,
  nullif 68185, view 68064, compound SELECT 10720, subqueries in FROM 4860,
  parenthesised joins 2938, fewer than 300 others), but for select5's slow
  queries (below). By feature, the records that ran and passed: joins
  170144 (LEFT JOIN 177), aggregates 633793, GROUP BY or HAVING 127199,
  DISTINCT 883789, subqueries 90380, CREATE UNIQUE INDEX 5954. index/ 22 s,
  the rest 117 s, most of it select5's 953 records (12 jobs).
- Time limits: every script ran under a limit of 300 s; only select5.test
  reached it, at line 6422 (its 912th record, a join of 21 tables). Timed
  alone at 20 s each, 483 of its 732 queries, joins of 20 to 64 tables, do
  not finish: they are written in an order their conditions do not follow
  (line 6422 names t64 second, and t64's terms name the 19th and 12th
  tables), so almost no inner table has a key from the tables before it,
  and the join runs in the order written, by design (sqlite3's
  wherePathSolver reorders it and answers at once). The other 953 records,
  joins of up to 32 tables among them, pass (114 s). select5 is therefore
  not kept; select4 (47 s, joins of up to three tables of 1000 rows) is
  the next slowest.
- The runner itself, through the real sqlite3 3.54.1: the kept scripts
  pass every record (160072 run), and every record left after ./db's skips
  and rewrites (150239 with every --have, 105456 without). All 622 scripts,
  select5 whole (7420713 records): 5939875 run, all pass but 4 of
  evidence/slt_lang_aggfunc.test (below); with ./db's skips and rewrites
  and every --have, 5252736 run, all pass.
- ./db over the whole corpus again (select5's slow queries left out),
  built with `-fsanitize=address,undefined` and run with DB_CACHE_PAGES=2:
  all 5244452 records pass, no sanitizer reports (838 s, 4 jobs); the kept
  scripts alone: 271 s.
- Found on the way, all in the runner, none in the engine: the bitwise
  operators and INDEXED BY (the core has neither: a syntax error, now
  skipped; evidence/slt_lang_aggfunc.test); a statement skipped for SQL
  this engine lacks did not hide the table it changes when it had a skipif
  or onlyif line (evidence/slt_lang_replace.test); and since 08.06 made the
  runner honour onlyif before halt, evidence/in1.test runs past its first
  lines, where `SELECT 1 IN t1` was skipped only because 08.06's code
  refuses it by name (the runner now skips it itself, so 05.03's slice
  passes on the core alone).
- Not kept, and why: evidence/slt_lang_aggfunc.test fails the runner's own
  check through sqlite3 3.54.1 (4 records: its sum() overflow and
  -9223372036854776000.000 were written by an older sqlite3, which printed
  reals with fewer digits); select5, above.
- Earlier (2026-11-14, the core only): one failure, fixed then. `NULL IN
  ()` was NULL where sqlite3 says 0 (and `NULL NOT IN ()` 1): an empty list
  holds no match, whatever the left side is (src/expr.c, eval, the E_IN
  case).
