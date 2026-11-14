# Notes for the lesson writers, and for the agents adding tools

Everything here was run on the reference code: Apple M4 Pro, macOS 26.6.2,
Apple clang 21, GNU Make 3.81, the system's BSD tools (sort 2.3-Apple);
and checked on Linux: Docker debian:stable-slim (aarch64), gcc 14.2, GNU
coreutils 9.7, dash as /bin/sh. Every "break it" below was run on the
project as `./learn files dsa --at NN.LL` writes it, with that one change
made, and the output is pasted, trimmed only where it says so. Times are
from `bench/grow.py` on the Mac, the fastest of three runs below a second.

## The project

```
Makefile               rules, recipes, variables and "include tools/*/tool.mk"
lib/ds.h               the library's one header (util, Array, Table, sort, Heap)
lib/util.c             die, xmalloc, open_input, DS_STATS; ds_todo (@internal)
lib/array.c            01.01   the growable array
lib/table.c            01.02, 01.03   the hash table (chained, entries in an Array)
lib/sort.c             02.01-02.03   insertion, merge, quick-first, quick
lib/heap.c             02.04   the binary heap, and heapsort
tools/<name>/<name>.c  one tool; tools/<name>/tool.mk builds it into bin/<name>
tools/paste/           00.01   paste -s, the workbench's job (whole, no regions)
tools/freq/            01.01-01.03, 02.04
tools/sort/            02.01-02.05
tools/look/            02.06
bench/grow.py          00.02   the growth harness (whole)
data/book.txt          00.01   the text every tool runs on
data/gen.py            00.02   inputs of any size, the same bytes every time (whole)
tests/NNLL_*.py        one test per lesson; tests/tools/<name>.py, one fixtures file per tool
```

`make` builds `build/lib/*.o`, archives them as `build/libds.a`, and links
each tool into `bin/`. `./learn run dsa --at 01.02 -- freq data/book.txt`
runs `bin/freq data/book.txt` in `build/at/dsa/01.02/`; `./learn run dsa
--at 01.02` with nothing after it starts the reader's shell there.
`./learn bench dsa --at 01.01 bin/freq --algo=list` runs the growth harness
on that command (grow.py's own options go before the command).

Conventions every tool keeps (the tool agents should too):

- Our tools are always `bin/<name>`; the system's are the bare names. bin/
  is never put on PATH, so `sort` in a lesson is always the system's.
- `--algo=NAME` picks how a tool does its job, when a lesson has brought a
  choice; the default is the best one built so far. The slow way stays
  runnable beside the fast one, with the same output. An option a later
  lesson brings is an ordinary error before it: `freq: unknown option
  '--hash=sum'`, `freq: no --algo 'tree' (have: list, table)`, `sort:
  unknown option -S`; status 2 for every error, as sort and grep use.
- Everything is compared with `LC_ALL=C`. The fixtures set it; lessons
  that compare with the system's tools should say so once.
- `DS_STATS=1` prints, at exit on stderr, one line per structure used, in
  the order first used: `stats: <name>: <count> <n>, <count> <n>`. The
  tool's own line comes first. Counts are summed over every instance (all
  of a tool's arrays share one `array` line). Tests assert on these counts,
  never on the clock.

How a cut lesson shows (check-skeleton, and a learner's workspace): a
region becomes `ds_todo("NN.LL", "<title>");` which prints `freq: 01.02:
count a word: ask the table not written yet` and exits 3. Everything that
does not reach that code still works (with 01.02 cut, `freq --algo=list`
works).

## Data

- `data/book.txt`: The Adventures of Sherlock Holmes (NOTICE says where it
  came from and what was changed: Gutenberg's header, footer and licence
  taken out, ASCII, LF). 562404 bytes, 11922 lines, 105885 words (runs of
  A-Za-z), 7818 different ones lowercased, 8422 different as written. It
  starts with "The Adventures...", so the pipeline counts no empty word on
  it (a text that starts with a non-letter makes `tr -cs` print an empty
  first line, which `uniq -c` counts; the fixtures drop it).
- `data/gen.py KIND N [--seed S]`: text, words, lines, sorted, reversed,
  same, numbers, fields, dict (its docstring says what each is). Its own
  splitmix64, so the bytes are the same on any machine and Python: `gen.py
  text 1000 | sha1sum` is 3688ac30... on the Mac and on Linux. Made-up
  words ("tavomi") come from syllables; text has one in ten made up, from
  a stock of n/4, so its vocabulary keeps growing: 2851 different words at
  n = 10000, 4656 at 20000, 7561 at 40000, 12111 at 80000 (about n^0.7,
  as Heaps' law says of real text).
- Not shipped: /usr/share/dict/web2 (Webster's Second, 2.49 MB; its README
  says "The 1934 copyright has lapsed, according to the supplier"). Too big
  for this step's budget; the spell agent should read that README itself
  before taking any of it, and record it in NOTICE.

## BSD and GNU: where they differ, found so far

- `uniq -c` pads counts to 4 columns (BSD) or 7 (GNU): "   1 a" against
  "      1 a". freq prints 7, as GNU's. Compare with `diff -b`, or counts
  and words (the fixture does).
- `paste -s` on BSD needs a file operand (`paste -s` alone prints usage;
  use `paste -s -`); prints nothing for an empty input, and no newline
  after a last line that had none. GNU's and ours always end with a
  newline. BSD refuses `-d ''`; ours, as GNU's, takes it as no delimiter.
- `sort`: on every case tried, macOS's sort and GNU's agree with LC_ALL=C:
  tests/tools/sort.py FLAGS (30 option sets) on random lines of
  `aAbB019-., \t`, and numbers such as "+4", "1e3", "0x10", "1,000", "-",
  "-0", ".5", which -n reads as 0, 1, 0, 1, 0, 0, 0.5. With -u, both print
  the first line in the input of each equal run, also with -r.
- `look` exists on macOS; on Debian only with bsdextrautils. Both look
  with a file compare bytes. A missing file exits 2 on BSD, 1 on Linux.
  The tests fall back to a Python reference when there is no look.
- GNU Make 3.81 (macOS) compares mtimes to the second: an edit made within
  a second of the last build is not rebuilt. A replay that patches a file
  and rebuilds at once may need to touch it.

## For the tool agents: adding a tool

Adding a tool is adding files; edit none of Makefile, track.py, lib/ds.h,
lib/*.c, data/gen.py, bench/grow.py, another tool's files, or NOTICE beyond
your own lines. freq is the worked example.

1. Lessons and tests: `./learn new dsa 04.01 "<title from the outline>"`
   for each lesson (module dir: rename `04-module` to `04-grep` after the
   first, set its README title to the outline's module title, copy the
   outline's `04/cover.svg` and `icon.svg` into it). Add your ids to
   `lessons/verify-pending.txt` (your own lines, in id order).
2. `tools/<name>/<name>.c` with `@build NN.LL` regions (comment lines after
   `@build` say what the region does; regions are function bodies). Main
   sets `progname = "<name>";` and registers its own stats printer with
   `ds_stats_at_exit`. Use lib (`#include "ds.h"`) only from the lesson
   that built the piece. Code a later lesson adds outside its regions is
   marked `// @from NN.LL` (a block, or at the end of one line), with an
   `// @else` part for what stands there before; freq.c's main has all
   three forms (the default --algo, the dispatch, the option parsing).
3. `tools/<name>/tool.mk`, as `tools/freq/tool.mk`:
   ```
   TOOLS += bin/freq

   bin/freq: build/freq/freq.o build/libds.a
   	@mkdir -p bin
   	$(CC) $(CFLAGS) -o bin/freq build/freq/freq.o build/libds.a

   build/freq/freq.o: tools/freq/freq.c lib/ds.h
   	@mkdir -p build/freq
   	$(CC) $(CFLAGS) -c -o build/freq/freq.o tools/freq/freq.c
   ```
   Two programs in one module (diff and patch, gzip and gunzip): either two
   directories, or one tool.mk with two `TOOLS +=` lines and their rules.
   Code another tool reuses (git uses diff's and gzip's): keep it in a .c
   of its own without a main (say `tools/diff/myers.c`); the other tool's
   tool.mk lists `build/diff/myers.o` among its objects and gives the rule
   only if no tool.mk has it already. A new structure for lib/ (a queue, a
   trie): `lib/<x>.c` with its own `lib/<x>.h` (ds.h is shared; adding to it
   from seven agents at once is a conflict), and in your tool.mk
   `LIB += build/lib/<x>.o` and its rule; the archive picks it up.
   Only rules, recipes, `=` and `+=` variables, `$(VAR)` and `include` are
   used, so module 07's make can build this Makefile; keep to those.
4. `tests/tools/<name>.py`, as `tests/tools/freq.py`: `PROGRAMS = {"freq":
   "01.01"}` (each program and the lesson it first appears at, which the
   timeline's `ls bin` checks); `FILES_FROM` for every file of yours with
   no regions (tool.mk always; a gen.py; a LICENSE); `timeline_steps(k)`
   and `timeline_after(root, k)` (k is a (module, lesson) tuple; return
   [] / None before your first lesson); and the fixtures your tests use.
   `T` is track.py: `T.run`, `T.system`, `T.sh`, `T.same`, `T.stats`,
   `T.gen`, `T.data`, `T.write`, `T.have`, `T.sh_step` (its docstring lists
   them). HIDDEN, SOURCES, STUBS and UPSTREAM there are merged too (edit's
   kilo credit goes in its own file's UPSTREAM); a path named twice stops
   track.py from loading.
5. Timeline steps run in one `/bin/sh` reading a pipe: give every command
   its input (`< /dev/null`, a file, or `printf ... |`), or it reads the
   shell's own commands. `T.sh_step(cmd, out, status)` wants the exact
   output and status.
6. Inputs: a kind of your own goes in `tools/<name>/gen.py` as `KINDS =
   {"map": (make, "nodes", "what it is")}`, where `make(n, rng)` returns
   the bytes of one file, or a list of bytes for a command that takes
   several (grow.py then appends every path; diff can use that); the kind
   name must be new. Data files you add: their licence read, a line in
   NOTICE's dsa section, and a FILES_FROM entry.
7. Done: `./learn test dsa`, `check-skeleton dsa`, `check-timeline dsa`,
   `selftest`, and `check` with no problem but the template lessons'.

## 00 The workbench (labs, no regions)

### 00.01 One job, done slow and done fast

Comes whole: Makefile, lib/ds.h, lib/util.c, data/book.txt,
tools/paste/paste.c and tool.mk. The job is `paste -s`: join each file's
lines into one. `--algo=strcat` finds the end of the line built so far
with strlen() before each piece, which is what strcat() does; `--algo=end`
keeps the length. The difference is one line in add().

```
$ printf 'a\nb\nc\n' | bin/paste -s -d ' '
a b c
$ cmp <(bin/paste -s data/book.txt) <(paste -s data/book.txt) && echo same
same
$ DS_STATS=1 bin/paste -s --algo=strcat l10k > /dev/null   (gen.py lines 10000, 20000)
stats: paste: lines 10000, bytes copied 236580, bytes scanned 2360699089
stats: paste: lines 20000, bytes copied 474351, bytes scanned 9472733867
--algo=end:  bytes scanned 0 at both sizes
```

Twice the lines, 4.01 times the bytes scanned. Measured (input: text):

```
$ python3 bench/grow.py --limit 2 bin/paste -s --algo=strcat
        n       bytes   seconds  ratio
    64000      342492     0.031
   128000      684437     0.115    3.7
   256000     1395080     0.461    4.0
   512000     2818492     1.893    4.1
  1024000     5663824     7.555    4.0
growth: each doubling multiplies the time by about 4.0: about n^2: twice the input, four times the time
```

`--algo=end` on 2048000 words (11.3 MB): 0.010 s, too quick to time at any
size up to that. The system's `paste -s` on the same: 0.317 s, ratio 1.9
("about n"). At 1024000 words (5.7 MB) strcat takes 7.555 s and end 0.007
s, a thousand times less; at 128000 words (0.7 MB) 0.115 s against 0.003
s. The gap doubles with every doubling.

Break it (a C string cannot hold a NUL): the system's paste and --algo=end
keep the bytes after a NUL; strcat loses them, since strlen stops there.

```
$ printf 'one\0two\nthree\n' | bin/paste -s --algo=end | od -c
0000000    o   n   e  \0   t   w   o  \t   t   h   r   e   e  \n
$ printf 'one\0two\nthree\n' | bin/paste -s --algo=strcat | od -c
0000000    o   n   e  \t   t   h   r   e   e  \n
$ printf 'one\0two\nthree\n' | paste -s - | od -c
0000000    o   n   e  \0   t   w   o  \t   t   h   r   e   e  \n
```

### 00.02 Measuring growth

Comes whole: bench/grow.py, data/gen.py. The harness doubles n from
--start until a run passes --limit seconds (default 2) or n passes --max;
it prints a ratio only when both runs took 20 ms or more (below that the
time is mostly starting the program: every row under 64000 words above is
3 to 10 ms), and its verdict is the median of the last three ratios, as a
power of n. An exit status of 1 is not a failure (look, grep and diff).

Worth showing: the same harness on a system tool (`grow.py --input lines
sort`: 0.761 s for 2048000 lines, 51 MB, ratio 2.1), and that small n
lies (the strcat table above is "flat" until 32000 words).

## 01 Counting words: freq

The tool at each lesson: 01.01 a list (an Array of words, searched from the
start for every word) and the top N by N passes; 01.02 adds `--algo=table`
(the default from then on), with the first table: 1024 buckets, the bytes
summed; 01.03 changes the table's defaults to FNV-1a and doubling, and adds
`--hash=fnv1a|sum` and `--no-grow` to get the 01.02 table back. 02.04 adds
`--top=heap` (the default from then) beside `--top=select`.

```
$ bin/freq data/book.txt
   5630 the
   3038 i
   3018 and
   2744 to
   2655 of
   2643 a
   1766 in
   1752 that
   1734 it
   1502 you
$ tr -cs A-Za-z '\n' < data/book.txt | tr A-Z a-z | sort | uniq -c | sort -rn | head    (macOS)
5630 the
3038 i
...
1502 you
```

Ties come in reverse byte order of the word: the last of `-n 0` are "1
abhorrent", "1 abbots", "1 abandons", in both.

### 01.01 A growable array

Regions: array_init, array_push (lib/array.c); next_word, count_list,
top_select (freq.c). The array copies by hand (xmalloc, memcpy, free), not
with realloc, so the moves can be counted.

```
$ DS_STATS=1 bin/freq --algo=list data/book.txt        (finished code; at 01.01 just bin/freq)
stats: freq: words 105885, distinct 7818, list probes 100262362, rank comparisons 7982
```

A word is looked at 947 times on average. Measured (input: text, whose
vocabulary grows as n^0.7, so the list's work grows as n^1.7):

```
$ python3 bench/grow.py --limit 2 bin/freq --algo=list
        n       bytes   seconds  ratio
    32000      171174     0.065    2.7
    64000      342492     0.194    3.0
   128000      684437     0.568    2.9
   256000     1395080     1.660    2.9
   512000     2818492     5.308    3.2
growth: each doubling multiplies the time by about 2.9: about n^1.6
```

(The verdict said n^1.6, not n^2: honest, and worth a sentence. With a
fixed vocabulary the list would be linear with a large constant; the
cost is words times different words.) Against the table at 512000 words:
5.308 s against 0.060 s.

Break it (grow by 8 instead of doubling): `size_t cap = a->cap ? 2 * a->cap
: 8;` becomes `size_t cap = a->cap + 8;`. On a word of 200000 letters:

```
before: stats: array: pushes 200001, grows 17, moves 262136
after:  stats: array: pushes 200001, grows 25001, moves 2499900000
```

The time hardly moves here (0.44 s to 0.53 s, most of it Python writing
the file; memcpy is fast), so make the point with the counts, or with a
longer word: the moves grow as n squared over 16. On the book: grows 981,
moves 3822048 (against 16392 doubling).

### 01.02 A hash table

Regions: hash_sum, table_init, find, table_get, table_put (lib/table.c);
count_table (freq.c). The table at 01.02 is `--algo=table --hash=sum
--no-grow` in the finished code.

```
$ DS_STATS=1 bin/freq --hash=sum --no-grow data/book.txt      (at 01.02: bin/freq)
stats: table: lookups 113703, probes 842939, inserts 7818, resizes 0, moves 0
```

7.4 probes a lookup, 842939 in all against the list's 100262362: 119
times fewer. lookups = words + distinct (a get per word, a put per new
word). Measured:

```
$ python3 bench/grow.py --limit 2 --max 2097152 bin/freq --algo=table --hash=sum --no-grow
        n       bytes   seconds  ratio
   256000     1395080     0.095    2.2
   512000     2818492     0.327    3.4
  1024000     5663824     1.405    4.3
  2048000    11346023     6.454    4.6
growth: each doubling multiplies the time by about 4.3: about n^2
```

So the first table is quick on the book and quadratic again on a large,
growing vocabulary: the sums of words fall in a narrow range, and 1024
buckets is a fixed number. That sets up 01.03.

Break it (compare the hashes, not the words): in find(), `if (e->hash == h
&& e->len == len && memcmp(e->key, key, len) == 0)` becomes `if (e->hash ==
h)`. Every anagram is one word:

```
$ printf 'stop pots tops opts post spot\nstop\n' | bin/freq
      7 stop
$ bin/freq data/book.txt
   5704 the
   3424 of
   3038 i
   3023 and
   2745 to
   2643 a
   2506 it
   2177 was
   2035 viii
   1862 in
```

("viii", in the book's contents before any of them, takes the counts of
every word whose letters add up to the same 433: "that", "year", "days",
"sign", "tell", "used", ...)

### 01.03 Hash functions, collisions and resizing

Regions: hash_fnv1a, grow (lib/table.c). table_init's defaults and the
call to grow() in table_put are `@from 01.03` blocks.

Probes a lookup on `gen.py text 100000` (100000 words, 14316 different):

```
fnv1a, doubling (the default)   1.37   (resizes 4: 16384 buckets)
fnv1a, --no-grow                 8.15
sum, doubling                   22.83
sum, --no-grow                  22.96
```

and on the book: 1.48, 5.15, 7.24, 7.41. Summing gives the same few
thousand values however many buckets there are, so doubling does not help
it; FNV-1a without doubling is linear in the words per bucket. Measured
(input: text, to 2048000 words, 11.3 MB):

```
                                       at 2048000 words   ratio
bin/freq (fnv1a, doubling)              0.253 s           1.9-2.2   about n
bin/freq --no-grow                      2.768 s           3.4
bin/freq --hash=sum                     6.817 s           4.3
bin/freq --hash=sum --no-grow           6.454 s           4.3
the shell pipeline (tr|sort|uniq|sort)  0.702 s           2.0
bin/freq --algo=list                    stopped at 512000: 5.308 s
```

Break it (double the buckets but do not relink): delete the loop in
grow() that puts each entry in its new bucket. Words already counted are
no longer found and are added again:

```
$ DS_STATS=1 bin/freq -n 5 data/book.txt
   3122 the
   1807 i
   1681 the
   1633 and
   1528 to
stats: freq: words 105885, distinct 13801, list probes 0, rank comparisons 68990
stats: table: lookups 119686, probes 117828, inserts 13801, resizes 4, moves 15360
```

## 02 Putting things in order: sort

The sort tool comes at 02.01 whole but for its regions: reading lines,
keys (-k -t), numbers (-n), and writing (-u) are not regions. Its
comparison (compare_lines) is 02.01's. Defaults: insertion at 02.01, merge
from 02.02 on. With -u, a stable sort (insertion, merge) leaves equal lines
in input order by itself; for the others (quick-first, quick, heap) sort
sets `by_index`, so compare_lines adds the input order as the last
tiebreak. That is why breaking a sort's stability shows with -u.

### 02.01 Insertion sort, and where it stops being enough

Regions: sort_insertion (lib/sort.c), compare_lines (sort.c).

```
$ printf '10\n9\n-1\n1.5\nabc\n' | bin/sort -n
-1
abc
1.5
9
10
$ printf 'b 1\na 2\nb 3\na 4\n' | bin/sort -u -k1,1
a 2
b 1
$ DS_STATS=1 bin/sort data/book.txt > /dev/null       (at 02.01, insertion)
stats: lines: read 11922, peak bytes 848532
stats: sort: comparisons 33615695, moves 33615696
```

Comparisons for 2000 lines: 1999 on dict (in order), 1999000 = n(n-1)/2
on dict reversed, 1032225 on lines (n*n/4 is 1000000). Measured:

```
$ python3 bench/grow.py --limit 2 --input lines bin/sort --algo=insertion
        n       bytes   seconds  ratio
     8000      188711     0.097    3.7
    16000      379291     0.403    4.1
    32000      759822     1.682    4.2
    64000     1547709     6.517    3.9
growth: about n^2
```

On input already in order it is linear: `--input sorted`, 2048000 lines in
0.212 s, ratio 2.0. The system's sort on 2048000 lines in no order: 0.761
s; insertion would take about 6.5 * 4^5 s = 1.9 hours.

Break it (`> 0` to `>= 0` in the while: equal lines pass each other):

```
$ printf 'b 1\na 2\nb 3\na 4\n' > keys.txt; bin/sort -u -k1,1 keys.txt
a 4
b 3
$ sort -u -k1,1 keys.txt
a 2
b 1
```

The book still sorts to the same bytes (equal lines are identical), but
with 37017961 comparisons instead of 33615695.

### 02.02 Merge sort

Regions: merge, merge_sort, sort_merge (lib/sort.c).

For 2000 lines: 19406 comparisons in no order, 10864 in order (each merge
stops comparing when one half runs out), 11138 reversed; the bound
n*ceil(log2 n) is 22000. Measured: 2048000 lines in 1.003 s (ratio 2.0 to
2.2); the system's sort 0.761 s.

Break it (take the right half on a tie: `< 0` to `<= 0` in merge()):

```
$ bin/sort -u -k1,1 keys.txt
a 4
b 3
```

### 02.03 Quicksort, and the input that breaks it

Regions: quick_first, sort_quick_first, quick3, sort_quick (lib/sort.c);
swap() and below() are `@from 02.03`. Both quicksorts sort the smaller
side by recursion and loop on the larger, so the stack stays log2(n) deep
on any input; a bad input costs time, never a crash.

Comparisons, 20000 lines:

```
                 sorted        all the same   (n(n-1)/2 = 199990000)
quick-first      199990000     199990000
quick            314268        19999
```

The real input that breaks the first-pivot quicksort is the book's own
words, one to a line: a few words very many times (`--input words`):

```
$ python3 bench/grow.py --limit 2 --input words --max 2097152 bin/sort --algo=quick-first
        n       bytes   seconds  ratio
    64000      336897     0.108    3.4
   128000      673817     0.341    3.1
   256000     1372843     1.290    3.8
   512000     2773837     4.961    3.8
growth: about n^2
```

and so does input already sorted (`--input sorted`: 32000 lines in 2.681
s, ratio 4.1) or all the same (`--input same`: 32000 in 2.000 s, ratio
4.1). quick on sorted: 2048000 lines in 0.523 s; on all the same: 0.186 s.
On lines in no order (which repeat their short lines) quick-first is
n^1.5 (2048000 lines in 2.216 s), quick n (1.030 s).

Break it (no random pivot in quick3: delete the `swap(v, lo, lo +
below(seed, hi - lo));` line). Sorted input costs nine times the
comparisons again, but equal lines are still one pass, thanks to the
three-way split:

```
quick, first pivot, 20000 sorted lines:  comparisons 2896211   (314268 with the random pivot)
quick, first pivot, 20000 dict words:    comparisons 2932763   (all different, in order)
quick, first pivot, 20000 same lines:    comparisons 19999
```

(Not n(n-1)/2 = 199990000, as quick-first takes: the three-way split's
swaps send each line above the pivot to the far end, which reverses that
part, so the next pass's first line is its largest, and the pass after
that sees it in order again. Sorted input stops being the worst case;
some other order is. That is the argument for the random pivot: no fixed
input is the worst case.)

### 02.04 A heap, and the top ten without sorting everything

Regions: sift_up, sift_down, heap_push, heap_pop, heap_sort (lib/heap.c);
top_heap (freq.c). freq's default --top becomes heap.

```
$ DS_STATS=1 bin/freq -n 1000 data/book.txt     (and --top=select)
heap:   rank comparisons 40590      stats: heap: pushes 1895, pops 1895, comparisons 33772
select: rank comparisons 7317500
```

On `gen.py text 100000`, -n 1000: 49667 against 13815500. Times are small
for both (4096000 words: select 0.924 s, heap at 2048000: 0.268 s against
select's 0.462 s); the comparisons tell it better than the clock. Heapsort:
37689 comparisons on 2000 lines in no order (merge: 19406); measured on
lines it is 2048000 in 3.288 s with ratio 2.5, slower than merge (1.003 s)
and growing faster: its sifting jumps across the array, so the larger the
array the more of its reads miss the cache. A good "comparisons are not
the whole cost" aside.

Break it (sift_down always takes the left child: delete `if (child + 1 <
n && above(v[child + 1], v[child], cmp, ctx, dir)) child++;`):

```
$ bin/freq data/book.txt
   5630 the
     21 arthur
   3038 i
      5 contents
   2655 of
    349 by
   3018 and
     97 sherlock
   1734 it
   2744 to
$ bin/sort --algo=heap data/book.txt | cmp - <(sort data/book.txt)
stdin /dev/fd/63 differ: char 2, line 2
```

### 02.05 Sorting a file bigger than memory

Regions: spill, merge_runs, merge_all (sort.c); the rest of the section
(new_run, run_cmp, parse_size, the -S and -T options, MERGE_WAYS = 16) is
`@from 02.05`. -S counts each line's bytes, its Line header and its
pointer; the unit is K unless it says b, K, M or G, as GNU's.

```
$ DS_STATS=1 bin/sort -S 256K lines.txt > out.txt      (gen.py lines 100000, 2.4 MB)
stats: lines: read 100000, peak bytes 262142
stats: runs: written 19, merges 3
stats: sort: comparisons 1113625, moves 1245995
stats: heap: pushes 200000, pops 200000, comparisons 824161, moves 838655
$ cmp out.txt <(sort lines.txt) && echo same
same
```

merge_all merges in passes: while there are more than 16 runs, a pass
merges each 16 in turn (the last group perhaps fewer) into a new run on
the end of the list, then drops the runs it merged from the front; the
last merge writes the output. So a line goes through ceil(log16 runs)
merges, which the heap's pushes count (one push per line per merge): 19
runs, 2 merges in the pass and 1 to the output, 200000 pushes. Without
-S: peak bytes 4836133. -S 64K: 74 runs, 6 merges (5 + 1), 200000 pushes;
-S 16K: 296 runs, 22 merges (19 + 2 + 1), 300000 pushes, 3 a line. With
-S 1M on 2048000 lines: 96 runs, 7 merges, 4096000 pushes, 2 a line
(the chain merge it replaced, the first 16 into one run that went into
the next merge with 15 more, made 8914352 pushes there, 4.35 a line, and
took 2.6 s). Measured with -S 1M, grow.py --input lines: 2048000 lines
in 1.373 s, against 0.91 to 1.0 s all in memory; the ratio is 2.0 to 2.2 but
2.6 at 512000, the first size (24 runs) with a second pass. The 02.05
test asserts the pushes and merges exactly. The runs go in $TMPDIR, or
-T; they are unlinked as soon as a merge opens them, and at exit.

Break it (forget `held = 0;` in spill): every line after the first run is
a run of its own. Same bytes out, but:

```
stats: lines: read 100000, peak bytes 4836133
stats: runs: written 94561, merges 6308
stats: heap: pushes 500000, pops 500000, comparisons 2942155, moves 2485900
real 12.19          (0.06 s before; 10 s of it in the system, making files)
```

(The lesson uses 10000 lines, -S 64K: 8628 runs, 578 merges.)

### 02.06 Binary search in a sorted file

A second program of module 02, `look` (the BSD tool of that name: the
lines of a sorted file that start with a string). Regions: find_scan,
find_binary (tools/look/look.c). It reads the file in 4096-byte blocks
through pread(), so "blocks read" is like a disk's reads.

```
$ tr -cs A-Za-z '\n' < data/book.txt | sort -u > words.txt     (8422 words)
$ DS_STATS=1 bin/look Holm words.txt
Holmes
stats: look: probes 12, blocks read 5, lines printed 1
$ DS_STATS=1 bin/look --algo=scan Holm words.txt
Holmes
stats: look: probes 494, blocks read 1, lines printed 1
```

On `gen.py dict 200000` (1.8 MB): look tavo, binary 17-19 probes and 11
blocks; scan 168816 probes and 357 blocks. Measured (`--input dict`, look
the, to 2048000 words, 20 MB): scan 0.054 s at the top, ratio 2.2; binary
2 to 3 ms at every size, too quick to time. Exit 0 when something was
printed, 1 when not.

Break it (`< 0` to `<= 0` in find_binary: lines that match go left too):
the search ends after the last match, and nothing is printed.

```
$ DS_STATS=1 bin/look tavo dict.txt
stats: look: probes 17, blocks read 11, lines printed 0
```

## The tests and the timeline

Each lesson's test runs the tools on the finished code; cut its regions
and it fails at the stub (check-skeleton). The comparisons with the
system's tools are in the tests, with counts from DS_STATS for the claims
about work. check-timeline types into one shell at each lesson: `ls bin`
(the programs PROGRAMS says), what each tool can do then, the ordinary
error for the next thing it cannot; then compares each tool's output on
the book with the system's (timeline_after). Whole runs on the Mac:
`./learn test dsa` about 11 s, check-skeleton about 11 s, check-timeline
about 16 s.
