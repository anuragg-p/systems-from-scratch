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
  every script of test/index/ and test/evidence/ at that commit.
- Licence: COPYRIGHT.md here, copied unchanged from the top of that
  repository (src/sqllogictest.c carries the same text): "As far as the
  author is concerned, you can redistribute it and/or modify the code as
  you see fit. No attribution is required." It names the GPL, BSD, MIT and
  CC0 licences, whichever best applies. The test scripts carry no notice of
  their own. NOTICE at the top of this repo records it too.

## What is kept here

test/ holds 15 scripts, unchanged (some end their lines with CRLF, as
upstream has them; .gitattributes keeps git from touching them), 13.9 MB:

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

## Running it

    ./learn test db --ref                    includes the quick slice (in 05.03's test):
                                             the first 1500 records of every script
    SLT=full ./learn test db 05.03 --ref     every record of every script
    python3 tracks/db/tests/sqllogictest/runner.py [--quick] [files or dirs]
                                             the runner itself (make the engine first);
                                             --help for its options
    python3 tracks/db/tests/sqllogictest/runner.py --engine sqlite3
                                             the same records through the real sqlite3:
                                             a check of the runner, which must pass all

A long run, outside the repo:

    python3 tracks/db/tests/sqllogictest/fetch.py 'test/index/*'    # 430 MB into build/sqllogictest/
    python3 tracks/db/tests/sqllogictest/runner.py build/sqllogictest/test
    python3 tracks/db/tests/sqllogictest/fetch.py --verify           # the kept files against MANIFEST

runner.py's docstring says how records run, what counts as a skip (SQL the
engine does not have, such as subqueries, joins, aggregates, DISTINCT, CAST
and views, and what such a skipped statement would have changed) and what is
emulated (INSERT INTO a SELECT * FROM b replayed as b's INSERTs; UNIQUE and
DESC indexes made ordinary). A script runs inside one BEGIN ... COMMIT
(--autocommit runs it statement by statement, some 40 times slower), and
sqlite3's PRAGMA integrity_check then checks the file it left.

## Results (2026-11-14, Apple M4 Pro)

- Kept scripts: 80605 records, 77543 run, all passed, 3062 skipped
  (subquery 2456, view 420, other engines 101, compound SELECT 60,
  DISTINCT 15, CAST 10); 3.6 s. Quick slice: 17171 run of 17712, 0.8 s.
- Whole index/ family (214 scripts, 433 MB): 2114262 records, 1824456 run,
  all passed, 289806 skipped; 27 s.
- Beyond index/: select1-5, all of evidence/ and 43 scripts of random/
  (442528 records, 150117 run, the rest mostly aggregates, DISTINCT, GROUP
  BY, CAST and joins): one failure, now fixed. `NULL IN ()` was NULL where
  sqlite3 says 0 (and `NULL NOT IN ()` 1): an empty list holds no match,
  whatever the left side is (src/expr.c, eval, the E_IN case).
- The runner itself, through the real sqlite3 3.54.1: every record of all
  of the above passes, with and without ./db's skips and rewrites.
