# Module 06, diff and patch: notes for the lesson writers, and the API for git

Everything here was run on the reference code: Apple M4 Pro (48 GB),
macOS 26.6.2, Apple clang 21.0.0, GNU Make 3.81, Python 3.12.7, the
system's Apple diff ("based on FreeBSD diff") and patch 2.0-12u11-Apple;
and checked on Linux: Docker debian:stable-slim (aarch64), gcc 14.2.0, GNU
diffutils 3.10, GNU patch 2.8. Every "break it" was run on the project as
`./learn files dsa --at NN.LL` writes it, with that one change made; the
output is pasted. Times are the fastest of three, from `bench/grow.py` or
`/usr/bin/time -l` (which also gives the peak memory, "maximum resident
set size").

## What is where

```
lib/diff.h          the engine's API (FILES_FROM 06.01; its later parts are @from)
lib/diff.c          06.01 lines and their numbers, the table; 06.02 the walk, hunks, unified output
lib/myers.c         06.03 Myers' search and the walk back
tools/diff/diff.c   the command: options, reading the files, the header lines (FILES_FROM 06.01)
tools/diff/gen.py   input kinds versions, revised, unrelated (pairs of files; FILES_FROM 06.01)
tools/patch/patch.c 06.04 the whole of patch
tests/tools/diff.py the fixtures (both programs), timeline steps, UPSTREAM (GNU diffutils and patch)
```

Regions: 06.01 `diff_number`, `fill` (lib/diff.c). 06.02 `walk`,
`next_hunk`, `print_hunk` (lib/diff.c), `print_header` (diff.c). 06.03
`search`, `backtrack` (lib/myers.c). 06.04 `read_hunk`, `find`, `apply`
(patch.c). A cut region prints, for example, `diff: 06.01: fill the table
from the bottom right corner up not written yet` and exits 3.

## The tool at each lesson

```
06.01  bin/diff [--algo=table] a b      "Files a and b differ", exit 1; nothing, exit 0
06.02  + unified output by default; -u, -U N, -q ("Files ... differ" only)
06.03  + --algo=myers, the default from now on; --algo=table stays
06.04  + bin/patch [-p N] [-o OUT] [-s] [-i PATCH] [FILE [PATCH]]
```

Before its lesson an option is an ordinary error, status 2: at 06.01
`diff: unknown option -u`, `diff: no --algo 'myers' (have: table)`. Exit
statuses are diff's and patch's: 0 same / applied, 1 different / a hunk
did not apply, 2 trouble. With `-q` (and at 06.01) the work is the same:
the whole script's size is found; only the printing differs.

At 06.01 the program's answer is only "differ or not". Its real result is
in DS_STATS (the lines in common) and DS_TRACE (the table): show those.

## The lib API (for git, module 10)

Lines in, edit script out; both algorithms; the hunks printer. git's diff
between two blobs is:

```c
#include "diff.h"
DiffText a, b;
diff_text(&a, blob1, len1);          /* lines point into blob1: keep it alive */
diff_text(&b, blob2, len2);
DiffScript s;
diff_myers(&s, &a, &b);              /* or diff_table(): the same ndel, nins */
if (s.ndel + s.nins > 0) {
    printf("--- a/%s\n+++ b/%s\n", path, path);   /* git's own headers */
    diff_unified(stdout, &a, &b, &s, 3);           /* "@@ -l,n +k,m @@" hunks, returns how many */
}
diff_script_free(&s);
diff_text_free(&a);
diff_text_free(&b);
```

- A line keeps its newline; a last line without one is a different line
  from the same text with one, and is printed with `\ No newline at end of
  file`, as git and diff print it.
- `s.edits` is an Array of `DiffEdit {char op; size_t a, b;}`: every line
  of both texts once, in order, ' ' keep, '-' delete line a of the first,
  '+' insert line b of the second (0-based). `s.common`, `s.ndel`, `s.nins`
  count them. Both algorithms number lines through module 01's Table
  (`diff_number`, called by each), so two lines compare as two longs.
- Within a run of changes the printer puts deletions before insertions,
  whatever order the script has, as diff and git print them.
- Memory: the table takes 4 x (n+1) x (m+1) bytes; Myers keeps
  (D+1)(D+2)/2 int32 at most (D = ndel + nins). Either stops with `die()`
  (exit 2) past `DIFF_MAX_BYTES`, 4 GB. Two unrelated 20000-line files are
  past it for Myers (see 06.03); git would need the linear-space variant of
  the paper (section 4b) for that, or to refuse such files.
- Stats are summed over calls (`stats: myers: d D, ...` counts every pair
  git diffs). `DS_TRACE=1` prints only for texts of 200 lines or fewer.
- Link with `build/libds.a`: diff.o is in it from 06.01, myers.o from
  06.03 (tools/diff/tool.mk adds both to LIB), table.o and array.o from
  module 01. Nothing in lib/ prints header lines or reads files.

## DS_TRACE: the format (for figures)

All on stderr, every line starting `trace: `, for texts of up to 200 lines
(`TRACE_LINES`). Lines of text are shown quoted, without the newline, cut
to 30 bytes with `...`.

The table (06.01), after it is filled: the lines of a and b, then the rows
in the order they were filled, bottom first; a cell where a[i] equals b[j]
has `=` after it (its value came from the lower right, +1).

```
trace: lcs: a has 4 lines, b 4; L[i][j] is the length of the longest common subsequence of a from line i and b from line j (from 0)
trace: lcs: a 0 "a"            ... a 1 "b", a 2 "c", a 3 "d"; then b 0 "a" ... b 3 "e"
trace: lcs: row 4: 0 0 0 0 0
trace: lcs: row 3: 1 1 1= 0 0
trace: lcs: row 2: 2 2= 1 0 0
trace: lcs: row 1: 2 2 1 0 0
trace: lcs: row 0: 3= 2 1 0 0
trace: lcs: length 3
```

The walk (06.02), one line a step: where it stands (i j), the cell's
value, the step, and for a change the two cells that chose it.

```
trace: walk: at 0 0, L 3: keep "a"
trace: walk: at 1 1, L 2: delete "b": below 2 >= right 1
trace: walk: at 2 1, L 2: keep "c"
trace: walk: at 3 2, L 1: keep "d"
trace: walk: at 4 3, L 0: insert "e": a is done
trace: hunk: edits 0 to 4
```

Myers (06.03), one line for each diagonal of each round: the edit that
brought it there (down = insert, right = delete) from round d-1's point,
the snake's length, the furthest point reached; then the path.

```
trace: myers: d 0 k 0: start (0,0), snake 1, reaches (1,1)
trace: myers: d 1 k -1: down from (1,1) to (1,2), snake 0, reaches (1,2)
trace: myers: d 1 k 1: right from (1,1) to (2,1), snake 2, reaches (4,3)
trace: myers: d 2 k -2: down from (1,2) to (1,3), snake 0, reaches (1,3)
trace: myers: d 2 k 0: down from (4,3) to (4,4), snake 0, reaches (4,4)
trace: myers: (4,4) reached with d 2
trace: myers: path (0,0) keep        ... (1,1) delete, (2,1) keep, (3,2) keep, (4,3) insert
```

The last round stops at the corner, so its later diagonals are not
printed. patch (06.04): each place tried, `trace: patch: hunk of line 3 at
line 1: line 1 differs` ... `at line 3: fits` (lines from 1).

The tests pin these three formats on a/b/c/d against a/c/d/e.

## The example used below

`old.txt` is lines 8-13 of the book (the contents, I to VI); `new.txt`
drops II, changes "Mystery" to "Murder" in IV, adds VII:

```
   I.     A Scandal in Bohemia              I.     A Scandal in Bohemia
   II.    The Red-Headed League             III.   A Case of Identity
   III.   A Case of Identity                IV.    The Boscombe Valley Murder
   IV.    The Boscombe Valley Mystery       V.     The Five Orange Pips
   V.     The Five Orange Pips              VI.    The Man with the Twisted Lip
   VI.    The Man with the Twisted Lip      VII.   The Adventure of the Blue Carbuncle
```

## 06.01 The longest common subsequence, as a table

The code: split each file into lines (diff_text, whole), number them so
equal lines have equal numbers through module 01's hash table
(`diff_number`, a region), fill the (n+1) x (m+1) table from the bottom
right (`fill`, a region). L[0][0] is the LCS; deleted = n - L, inserted =
m - L. The tool prints `Files a and b differ` or nothing.

```
$ bin/diff old.txt new.txt
Files old.txt and new.txt differ
$ bin/diff old.txt old.txt; echo "exit $?"
exit 0
$ DS_STATS=1 bin/diff old.txt new.txt
Files old.txt and new.txt differ
stats: diff: lines 6 and 6, common 4, deleted 2, inserted 2
stats: array: pushes 20, grows 3, moves 0
stats: lcs: cells 49, bytes 196
stats: table: lookups 12, probes 4, inserts 8, resizes 0, moves 0
$ DS_TRACE=1 bin/diff old.txt new.txt      (the rows; the lines listed first are left out)
trace: lcs: row 6: 0 0 0 0 0 0 0
trace: lcs: row 5: 1 1 1 1 1= 0 0
trace: lcs: row 4: 2 2 2 2= 1 0 0
trace: lcs: row 3: 2 2 2 2 1 0 0
trace: lcs: row 2: 3 3= 2 2 1 0 0
trace: lcs: row 1: 3 3 2 2 1 0 0
trace: lcs: row 0: 4= 3 2 2 1 0 0
trace: lcs: length 4
```

"table: lookups 12": one lookup for each of the 12 lines; "inserts 8": 8
different lines in the two files (4 shared, 2 only in each).

Where it stops being usable: not the time. The fill is about 0.7 ns a
cell here (sequential, one compare of two longs); the wall is memory, 4
bytes for every pair of lines.

```
$ python3 bench/grow.py --limit 3 --input versions bin/diff --algo=table
        n       bytes   seconds  ratio
     1000       92520     0.003
     2000      182782     0.006
     4000      376956     0.015
     8000      756278     0.047
    16000     1509521     0.176    3.7
    32000     3020820     0.701    4.0
grow.py: ... failed (exit 2):
diff: 64000 and 63996 lines: the table would take 15625 MB, more than the 4096 MB it may
```

Peak memory (`/usr/bin/time -l`, versions pairs): 8000 lines 0.04 s, 260
MB; 16000 lines 0.17 s, 1.0 GB; 32000 lines 0.71 s, 4.1 GB. Built with the
limit raised (`make clean; make EXTRA_CFLAGS=-DDIFF_MAX_BYTES=10737418240`,
in a copy): 45000 lines 1.79 s, 8.1 GB (2,024,909,997 cells). The machine's
48 GB would be full at about 110000 lines; files of 3 MB (32000 lines)
already need 4 GB. The real input: the book against a copy with three
edits (`sed -e '3d' -e '700s/$/ (changed)/' -e '5000,5004d'`; 11922 lines,
562 KB): 0.10 s and 574 MB (142,086,391 cells); the book twice over, the
same edits (23844 lines, 1.1 MB): 0.43 s and 2.3 GB (568,440,955 cells);
three times (35766 lines, 1.7 MB): refused, `diff: 35766 and 35765 lines:
the table would take 4880 MB, more than the 4096 MB it may`. Myers on the
same three: 0.00 to 0.01 s, 5.6 to 11 MB (d 8; 11,963 and 23,885 cells).

The limit (DIFF_MAX_BYTES, 4 GB, in lib/diff.h, overridable with -D) is
the code's, so that a reader who tries a big file gets an error and not a
machine swapping. Say so: it is the point where the table stops being
worth it here, not a law.

Break it (forget the +1: in `fill`, `L[i * w + j] = L[(i + 1) * w + j + 1]
+ 1;` becomes `L[i * w + j] = L[(i + 1) * w + j + 1];`). Nothing is ever in
common, so a file differs from itself:

```
$ bin/diff old.txt old.txt
Files old.txt and old.txt differ
$ DS_STATS=1 bin/diff old.txt new.txt
Files old.txt and new.txt differ
stats: diff: lines 6 and 6, common 0, deleted 6, inserted 6
```

## 06.02 From the table to hunks: unified output

The code: `walk` (from L[0][0]: equal lines are kept, diagonally; else down
= delete when the cell below is at least the cell to the right, else right
= insert), `next_hunk` (a change, context lines before and after; two
changes with 2 x context or fewer unchanged lines between share a hunk),
`print_hunk` (the header, then the lines; deletions before insertions in
each run of changes), `print_header` (GNU's time format, from stat()).

```
$ bin/diff old.txt new.txt
--- old.txt	2026-11-14 10:20:30.000000000 +0530
+++ new.txt	2026-11-14 10:21:05.000000000 +0530
@@ -1,6 +1,6 @@
    I.     A Scandal in Bohemia
-   II.    The Red-Headed League
    III.   A Case of Identity
-   IV.    The Boscombe Valley Mystery
+   IV.    The Boscombe Valley Murder
    V.     The Five Orange Pips
    VI.    The Man with the Twisted Lip
+   VII.   The Adventure of the Blue Carbuncle
$ bin/diff -U0 old.txt new.txt | tail -n +3
@@ -2 +1,0 @@
-   II.    The Red-Headed League
@@ -4 +3 @@
-   IV.    The Boscombe Valley Mystery
+   IV.    The Boscombe Valley Murder
@@ -6,0 +6 @@
+   VII.   The Adventure of the Blue Carbuncle
$ diff -u old.txt new.txt | tail -n +3          (the system's: the same hunk, byte for byte)
$ bin/diff old.txt new.txt > change.diff; cp old.txt work.txt; patch work.txt change.diff; cmp work.txt new.txt && echo same
patching file work.txt
same
$ DS_TRACE=1 bin/diff old.txt new.txt 2>&1 >/dev/null | grep -v "trace: lcs"
trace: walk: at 0 0, L 4: keep "   I.     A Scandal in Bohemia"
trace: walk: at 1 1, L 3: delete "   II.    The Red-Headed Leagu...": below 3 >= right 2
trace: walk: at 2 1, L 3: keep "   III.   A Case of Identity"
trace: walk: at 3 2, L 2: delete "   IV.    The Boscombe Valley ...": below 2 >= right 2
trace: walk: at 4 2, L 2: insert "   IV.    The Boscombe Valley ...": below 1 < right 2
trace: walk: at 4 3, L 2: keep "   V.     The Five Orange Pips"
trace: walk: at 5 4, L 1: keep "   VI.    The Man with the Twi..."
trace: walk: at 6 5, L 0: insert "   VII.   The Adventure of the...": a is done
trace: hunk: edits 0 to 7
```

The range format: `-l,n`; n = 1 is left out (`-2`); n = 0 names the line
before (`+1,0`: after line 1 of new, nothing; `-0,0` is the start of an
empty file). The header's times are the files' (here set with touch -t);
the system's are `2026-11-14 10:20:30` on macOS, GNU's like ours.

Joining hunks, at -U3, lines 1-20 numbered: lines 5 and 12 changed (6
unchanged between) give one hunk `@@ -2,14 +2,14 @@`; lines 5 and 13 (7
between) give two, `@@ -2,7 +2,7 @@` and `@@ -10,7 +10,7 @@`. No newline at
the end:

```
$ printf "a\nb" > x.txt; printf "a\nc" > y.txt; bin/diff x.txt y.txt | tail -n +3
@@ -1,2 +1,2 @@
 a
-b
\ No newline at end of file
+c
\ No newline at end of file
```

Break it (join too little: in `next_hunk`, `next - end > 2 * context`
becomes `next - end > context`). Lines 5 and 10 changed, 4 lines apart:
the system's diff and ours print one hunk, `@@ -2,12 +2,12 @@`; broken, two
hunks whose context overlaps (lines 7 and 8 are in both):

```
@@ -2,7 +2,7 @@
 line 2
 ...
+LINE 5
 ...
 line 8
@@ -7,7 +7,7 @@
 line 7
 line 8
 ...
```

Worth a sentence for 06.04: the system's patch (BSD and GNU) applies that
broken diff and makes the right file; ours refuses it (hunk #2 starts
before hunk #1 ends: "does not apply", exit 1). Another break, the line
number off by one (`start + 1` to `start` in print_range's last case):
`@@ -0,6 +0,6 @@`; BSD patch says "No such line 0 in input file, ignoring"
and applies it, GNU's "Hunk #1 succeeded at 1 (offset 1 line)", ours
applies it at line 1 with no message. patch forgives a wrong line number;
it does not forgive wrong lines.

## 06.03 Myers: the shortest path of edits

The code: `search` (rounds d = 0, 1, ...; each diagonal k = -d, -d+2, ...,
d; one edit from round d-1's point on k+1 (down) or k-1 (right), whichever
is further, right on a tie; then the snake), `backtrack` (from (n, m),
each round's point came from k+1 or k-1 by the same rule; the snake between
is kept lines; the script is reversed at the end). Every round's points
are kept in an Array of int32 (module 01's), round d at d(d+1)/2.

```
$ DS_STATS=1 bin/diff old.txt new.txt > /dev/null
stats: diff: lines 6 and 6, common 4, deleted 2, inserted 2, hunks 1
stats: array: pushes 41, grows 6, moves 8
stats: myers: d 4, diagonals 13, cells 17, bytes 52
stats: table: lookups 12, probes 4, inserts 8, resizes 0, moves 0
$ DS_STATS=1 bin/diff --algo=table old.txt new.txt > /dev/null
stats: lcs: cells 49, bytes 196                  (and the same diff line)
```

`cells` counts the same thing for both: points of the edit graph looked
at (Myers: each furthest point, and each step of a snake). On the same
pairs:

```
pair                                   table cells      myers cells   myers d
versions 2000 (16 edits)                 3,995,997            3,287        50
the book against 3 edits (11922)       142,086,391           11,963         8
versions 45000 (16 edits)            2,024,909,997           46,280        50
unrelated 4000                          16,008,001       20,130,341      6344
unrelated 16000                        256,032,001      314,531,741     25080
```

Measured, Myers (`--algo=myers`, the default):

```
$ python3 bench/grow.py --limit 2 --start 64000 --input versions bin/diff --algo=myers
        n       bytes   seconds  ratio
    64000     6040422     0.013
   128000    12080922     0.021
   256000    24145180     0.038    1.8
   512000    48305181     0.073    1.9
  1024000    96615085     0.143    2.0
  2048000   193225651     0.277    1.9
  4096000   386441973     0.559    2.0
growth: each doubling multiplies the time by about 2.0: about n
```

(386 MB of input in 0.56 s; most of it is reading and numbering lines.)
When the difference grows with the files (`revised`, an edit every 32
lines), Myers is n^2 too, as O(ND) says: 128000 lines 0.209 s, 256000
0.907 s (4.3), 512000 4.944 s (5.5; the kept points, D^2/2, start to cost
memory). The table on the same: 32000 lines 0.70 s, refused at 64000.

The honest case: two files with nothing in common but blank lines
(`unrelated`). D is about 1.6 n, Myers looks at D^2/2 points, more than
the table's n^2, each dearer (jumps, an Array push); and it keeps them:

```
unrelated   table              myers
4000        0.01 s,  68 MB     0.07 s,  218 MB
8000        0.04 s, 261 MB     0.27 s,  854 MB
16000       0.17 s, 1.0 GB     1.11 s,  3.4 GB  (kept points 1.26 GB; the Array doubles)
32000       0.68 s, 4.1 GB     refused: "the files are so different that the search would
                               keep more than 4096 MB of points"
```

(grow.py on unrelated, myers: ratios 3.5, 3.8, 4.0: about n^2.) A boundary
worth naming: GNU diff gives up on exactness here (its heuristics, unless
-d), git's xdiff too; the paper's linear-space variant (section 4b) keeps
the time and drops the memory to O(n). We kept the basic algorithm and
its D^2 memory, and say so.

Break it (no snake: in `search`, `while (x < n && y < m && A[x].id ==
B[y].id) {` becomes `while (0 && x < n && ...) {`). No free diagonal step
is ever taken: every line is deleted and inserted, d = n + m, and the
script is still a correct one (the system's patch applies it):

```
$ DS_STATS=1 bin/diff old.txt new.txt
--- old.txt	...
+++ new.txt	...
@@ -1,6 +1,6 @@
-   I.     A Scandal in Bohemia
-   II.    The Red-Headed League
 ...(all six deleted, all six inserted)
stats: diff: lines 6 and 6, common 0, deleted 6, inserted 6, hunks 1
stats: myers: d 12, diagonals 85, cells 85, bytes 340
```

Tried and not worth a lesson: ties to "down" (`<` to `<=` in came_down)
changes nothing on old/new, not even the path.

## 06.04 patch: applying a diff

The code: `read_hunk` (the header's counts say how many lines to read; an
empty line is an empty context line; `\` takes the newline off the line
before), `find` (the old lines, kept and deleted, compared with the
file's, at the header's line moved by the last hunk's offset, then one on,
one back, two on, ...; never before the last hunk's end), `apply` (copy up
to the place, the hunk's new lines, then the rest). The result is a list
of line pointers (DiffLine, from lib/diff.c's diff_text) written only when
every hunk has applied: all or nothing, through a new file renamed over
the old. The system's patch applies what it can and writes the rest to
FILE.rej; ours, like `git apply`, changes nothing. No fuzz (GNU's drops
context lines to find a place: it applied an insertion into a file "q" of
one line, "succeeded at 1 with fuzz 2").

```
$ diff -u old.txt new.txt > change.diff; cp old.txt work.txt; bin/patch work.txt change.diff; cmp work.txt new.txt && echo same
patching file work.txt
same
$ bin/patch work.txt change.diff; echo "exit $?"
patching file work.txt
patch: work.txt: hunk #1 (line 3 of the patch) does not apply: its lines are not in the file
patch: work.txt: 1 of 1 hunk did not apply: the file is not changed
exit 1
$ (echo "A note at the top."; echo; cat old.txt) > moved.txt; bin/patch moved.txt change.diff
patching file moved.txt
Hunk #1 succeeded at 3 (offset 2 lines).
$ DS_TRACE=1 DS_STATS=1 bin/patch -s -o - moved.txt change.diff > /dev/null
trace: patch: hunk of line 3 at line 1: line 1 differs
trace: patch: hunk of line 3 at line 2: line 2 differs
trace: patch: hunk of line 3 at line 3: fits
stats: patch: files 1, hunks 1, failed 0, places tried 3, lines compared 8
$ printf "just text\n" | bin/patch work.txt; echo "exit $?"
patch: no hunks in the patch: it is not a unified diff
exit 2
```

An empty patch (what diff prints for files the same) is exit 0, as both
system patches do. Without FILE the name comes from the headers: the
`---` file if it exists, else the `+++` one, after -p N; `/dev/null` as
the old name makes a new file, as the new name (with nothing left)
deletes it. Two files' worth of hunks and a FILE named: an error.

Break it (no search: in `find`, `for (long d = 0; want + d <= hi || want -
d >= lo; d++) {` becomes `for (long d = 0; d < 1; d++) {`): the moved
file is refused, though the system's patch takes it:

```
$ bin/patch moved.txt change.diff
patching file moved.txt
patch: moved.txt: hunk #1 (line 3 of the patch) does not apply: its lines are not in the file
patch: moved.txt: 1 of 1 hunk did not apply: the file is not changed
$ patch moved.txt change.diff
patching file moved.txt
```

## BSD and GNU: what differs, and how the tests pin it

- **Minimal or not.** GNU diff without `-d` (--minimal) takes shortcuts:
  on `unrelated` 120 lines it printed 119 deletions and 119 insertions
  where 93 + 93 do (seeds 1 and 2: 120 + 120 against 90 + 90). The tests
  run the system's diff as `diff -d`; ours is always minimal.
- **Apple's -U0 bug.** Without -d, Apple's diff -U0 writes `@@ -1,0 +1 @@`
  for a line put before line 1 of a non-empty file (it should be `-0,0`,
  as GNU's and ours write), and Apple's own patch then puts the line after
  line 1. With -d it writes `-0,0`. A good "is the format's corner case
  really that subtle" aside; pinned by -d.
- **Header times.** BSD `--- old.txt	2026-11-14 10:20:30`, GNU and ours
  `2026-11-14 10:20:30.000000000 +0530`. Tests compare everything after
  the two header lines; header lines are checked by pattern.
- `\ No newline at end of file`: the same text on both, and both patches
  read it (all cases pass both ways).
- Same-length scripts: where several are shortest, our hunks may differ
  from the system's in which lines are kept (the tests compare text only
  on pairs whose LCS is the only one: there both systems and ours print the
  same bytes, at -U 0, 1, 3, 5).
- patch's chatter: GNU and ours print `patching file x`; Apple's prints
  more (`Hmm...  Looks like a unified diff to me...`) without -s. Tests
  run the system's patch with -s -f.
- Debian has no `patch` by default: the fixtures fall back to a strict
  Python applier (`reference_patch`), and the tests passed that way too.

## Tests and timeline

Each test runs the finished code on 30 pairs (19 made by hand: empty
files, no newline, CRLF, lines like headers, a swap; 11 generated) against
the system's diff -d and patch: the same exit status and numbers of lines,
a strict check of every hunk (positions on both sides, context exactly as
-U says, joined exactly when 2 x context or fewer lines apart), and the
system's patch reproducing the second file. 06.01 also: cells = (n+1)(m+1),
one table lookup per line, four times the cells for twice the lines, a
33000-line pair refused. 06.03: myers d = the script's length, points kept
= diagonals, 500 times fewer cells than the table on 2000 lines, under 2.5x
for twice the lines, 3 to 5.5x for twice the edits, 40000 lines quick. 06.04:
our patch on 150 diffs (ours, ours -U0, the system's -U3/1/0), offsets,
refusal leaving the file alone, -p1 in a tree, /dev/null, bad input.

Timeline (each lesson from 06.01): `bin/diff` same / differ / usage /
missing file; the next lesson's option as an error; from 06.02 the unified
output (header by pattern) and -U0; from 06.04 patch applying and refusing.
After: 1500 lines of the book against a sed-edited copy, counts against the
system's diff -d; from 06.02 the system's patch on ours; from 06.04 ours on
the system's.

Whole runs on the Mac: `./learn test dsa 06` 5.7 s, most of it starting
processes (under a second on Linux, where starting one takes about 1 ms:
300 runs of diff in 0.284 s); check-skeleton dsa 06 6.7 s; check-timeline
dsa 06 13.9 s.
