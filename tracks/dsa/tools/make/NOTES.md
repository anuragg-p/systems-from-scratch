# make (module 07): notes for the lesson writers

Everything here was run on the reference code: Apple M4 Pro, macOS 26.6.2,
Apple clang 21; the system's make is GNU Make 3.81 (/usr/bin/make), and
Homebrew's GNU Make 4.4.1 (gmake) was run beside it. Checked on Linux too:
Docker debian:stable-slim (Debian 13.7, aarch64), gcc 14.2, GNU Make 4.4.1,
GNU coreutils 9.7 (tsort), bmake 20200710, dash as /bin/sh. Each "break
it" was run on the project as `./learn files dsa --at 07.0N DIR` writes it,
with that one change made and the project built again with `make clean;
make` (GNU make 3.81 compares whole seconds: an edit within a second of a
build is not seen). Times are the fastest of three runs. None of this file
is shown to learners (HIDDEN in tests/tools/make.py).

## The files

```
lib/depgraph.h, .c       the graph: nodes in an Array, a Table from name to node, each node's
                         needs as an Array of node indexes (an adjacency list)
                           07.01 graph_init, graph_node, graph_edge, walk (graph_walk)
                           07.02 graph_search: depth-first, three states, the path in an Array
lib/readyq.h, .c         07.04 the queue of ready work: an Array and the index of its front
tools/make/make.h        what read.c and make.c share: Recipe, Target, the reader's interface
tools/make/read.c        reading makefiles: lines, variables, include; 07.01 add_rule
tools/make/make.c        main, running commands; 07.01 print_graph, make_node; 07.02
                         report_cycle; 07.03 out_of_date, build_in_order; 07.04 finished,
                         build_queue
tools/make/tool.mk       builds bin/make; adds depgraph.o (07.01) and readyq.o (07.04) to LIB
tools/make/gen.py        kinds for data/gen.py: diamonds (levels), wide (targets)
tools/make/examples/     diamond.mk (07.01), cycle.mk (07.01), slow.mk (07.04)
tests/tools/make.py      fixtures, the differential table, timeline steps
tests/0701..0704_*.py    one test per lesson
```

The reader (read.c) and the command runner (make.c: command_line,
start_command, run_recipe) are not regions: they come whole at 07.01, as
sort's reading and writing came whole at 02.01. The lessons are the graph
and the walks over it.

## What it reads, and what it does not

The scope is the plan's: what this track's Makefile and every
tools/*/tool.mk use. Supported:

- rules `TARGETS: PREREQS`, several targets in one rule, several rules for
  one target (their prerequisites added together, the one with the recipe
  first, as GNU make orders them), a prerequisite named twice counted once;
- recipes: tab-started lines under a rule, each run with `/bin/sh -c`, `@`
  in front (after any blanks) to not print it;
- variables `NAME = VALUE` and `NAME += VALUE`, `$(NAME)` and `${NAME}` in
  rules, includes and recipes, names made of variables (`$($(WHICH))`),
  `$$`; a value keeps its trailing blanks before a comment, as GNU make's
  does (this matters: the track's `LIB += x   # @from 01.01` lines put
  those blanks into the `ar` command, and our -n output has them too);
  `NAME=VALUE` on the command line wins over the makefile, which wins over
  the environment;
- `include` with a glob (`include tools/*/tool.mk`, the matches in sorted
  order), comments, blank lines, backslash-newline in any line;
- `.PHONY`;
- options -n, -s, -f FILE, -j N, NAME=VALUE, targets; makefile or Makefile
  found by its exact name in the directory, as GNU make does (on a disk
  that ignores case, `access("makefile")` finds Makefile: GNU make reports
  errors as `Makefile:2:`, and so do we).

Not supported, each an ordinary error with status 2 naming the line:
`:=`, `?=`, `!=`, `::`, functions (`$(wildcard ...)`), substitution
references (`$(X:.c=.o)`), automatic variables (`$@`, `$<`, `$^`, ...),
pattern and suffix rules, special targets other than .PHONY, conditionals,
`define`, `export`, `override`, `vpath`, `-include`, target-specific
variables, order-only prerequisites, a recipe after `;` on the rule's line,
the `-` and `+` command prefixes. Not there at all: GNU make's built-in
variables and rules (`CC` is empty unless the makefile or the environment
sets it), remaking makefiles, `$(MAKE)` and MAKEFLAGS, `-k -B -q -C`, `-j`
without a number, `\#` in a value, deleting a target whose recipe failed.

```
$ printf 'X := 1\n' > Makefile; bin/make
make: Makefile:1: ':=' is not supported: only = and +=
$ printf 'a:\n\techo $@\n' > Makefile; bin/make
make: Makefile:1: '$@' is not supported: write $(NAME), ${NAME} or $$
```

## Options, lesson by lesson

```
07.01  --graph, -n, -s, -f, NAME=VALUE; the build is the walk
07.02  the same; the search runs first and stops a cycle
07.03  --order, --algo=recurse|topo (topo the default)
07.04  -j N (picks --algo=queue), --algo=queue
```

Before its lesson an option is an ordinary error, as the track's other
tools do it: `make: unknown option '--order'`, `make: unknown option -j`,
`make: no --algo 'queue' (have: recurse, topo)`, status 2.

## DS_STATS and DS_TRACE

`DS_STATS=1` prints, on stderr at exit:

```
stats: make: recipes run R, commands C, files checked F, most at once M
stats: depgraph: nodes N, edges E, walk visits W, walk edges X, search visits V, search edges S
stats: readyq: pushes P, pops Q, longest L                    (07.04, when -j or --algo=queue)
```

(plus the array and table lines of the library). Commands are the command
lines run, or printed with -n; files checked, the stat() calls; most at
once, the most commands running together (0 with -n, which runs none).
Before 07.02 the depgraph line stops after the walk's two counts.

`DS_TRACE=1` prints one line per step on stderr, `trace: EVENT ...`:

```
trace: walk DEPTH NAME      07.01  the walk comes to NAME, DEPTH edges below the goal
trace: run NAME             07.01  NAME's recipe runs (serial builds)
trace: enter DEPTH NAME     07.02  the search reaches NAME for the first time: open
trace: leave DEPTH NAME     07.02  everything NAME needs is done: NAME is done
trace: again DEPTH NAME     07.02  the search meets NAME, done already, and goes on
trace: cycle DEPTH NAME     07.02  the search meets NAME while it is open: a cycle
trace: check NAME: WHY      07.03  out of date or not, and why: "phony", "missing",
                                   "X was made", "X is newer", "up to date",
                                   "a file with no rule"
trace: ready NAME           07.04  everything NAME needs is finished: NAME joins the queue
trace: start NAME           07.04  NAME comes off the queue and its recipe starts
trace: skip NAME            07.04  NAME comes off the queue up to date (a finish follows)
trace: finish NAME          07.04  NAME is finished
```

The trace goes to stderr unbuffered and the commands to stdout, so in a
pipe the commands come out after the trace; in a terminal they interleave.
A figure made from a run should use `2>&1` with stdout to a terminal, or
take the trace alone.

## 07.01 A makefile as a graph

Regions: graph_init, graph_node, graph_edge, walk (lib/depgraph.c);
add_rule (read.c); print_graph, make_node (make.c). graph_node looks the
name up in the Table and adds a node when it is new; graph_edge appends to
the node's needs unless it is there already (a linear scan: fine for the
few dozen prerequisites a real target has, quadratic for a target with
tens of thousands). The build is the obvious recursion: graph_walk calls
make_node after everything a node needs, and make_node runs the recipe,
every time. Nothing is remembered, so nothing is out of date yet either:
everything is made, by every path to it.

```
$ bin/make --graph -f tools/make/examples/diamond.mk
app: liba libb
liba: common.h
libb: common.h
common.h:
$ DS_TRACE=1 bin/make -n -f tools/make/examples/diamond.mk     (stderr first, as a pipe shows it)
trace: walk 0 app
trace: walk 1 liba
trace: walk 2 common.h
trace: run common.h
trace: run liba
trace: walk 1 libb
trace: walk 2 common.h
trace: run common.h
trace: run libb
trace: run app
touch common.h
touch liba
touch common.h
touch libb
touch app
stats: depgraph: nodes 4, edges 4, walk visits 5, walk edges 4     (with DS_STATS=1)
```

The track's own Makefile as a graph (the 5 tools of this branch: paste,
freq, sort, look, make; more once the other modules are in): 38 nodes, 56
edges; `--graph` prints 39 lines (the last is `.PHONY: all clean`), and
for every target with prerequisites they are the same, in the same order,
as in `make -p -q`'s database (the test checks it). The first lines:

```
all: bin/freq bin/look bin/make bin/paste bin/sort
build/lib/util.o: lib/util.c lib/ds.h
lib/util.c:
lib/ds.h:
```

On this project the walk compiles each library file once per tool that
links the library: `bin/make -n --algo=recurse` prints 102 commands
against 38, `mkdir -p build/lib` 35 times (7 objects, 5 tools), and the
compile of lib/util.c 5 times. Measured (a clean build, `make clean` before
each):

```
system make -s                     0.854 s
bin/make -s (in order, 07.03)      0.946 s
bin/make -s --algo=recurse         2.268 s      every tool adds a whole library build
bin/make -s, nothing to do         0.003 s
bin/make -s --algo=recurse, again  2.270 s      it makes everything, every time
```

A cycle at 07.01: the walk cannot tell, until it goes deeper than there
are nodes (a path that long must pass a node twice):

```
$ bin/make -n -f tools/make/examples/cycle.mk
make: a cycle in what 'all' needs: the walk went deeper than the 4 targets there are
```

And the walk is a recursion on the C stack: a chain of 100000 targets
crashed it (status 139) until it was given a floor, WALK_DEEPEST = 10000
levels (the search, 07.02, keeps its path in an Array and has none):

```
$ bin/make -n --algo=recurse -f chain.mk        (t0: t1, t1: t2, ... 100000 deep)
make: what 't0' needs goes more than 10000 levels deep: too deep for the walk
```

Break it (no lookup: graph_node adds a node for every name it is given,
delete the three lines that ask the table first). Each mention is a new
node, so app needs a liba that has no rule, and the track's default goal
is the first `all:`, which needs nothing:

```
$ bin/make --graph -f tools/make/examples/diamond.mk
app: liba libb
liba:
libb:
liba: common.h
common.h:
libb: common.h
common.h:
common.h:
$ bin/make -n -f tools/make/examples/diamond.mk
make: *** No rule to make target 'liba', needed by 'app'.  Stop.
$ bin/make -n                                  (the project)
make: Nothing to be done for 'all'.
```

## 07.02 Depth-first search, and finding a cycle

Regions: graph_search (lib/depgraph.c), report_cycle (make.c); enter()
and the Frame are `@from 07.02`. Three states per node, NEW, OPEN (on the
path from the goal to where the search is) and DONE. The path is an Array
of frames (a node and how far along its needs it is), so the open nodes
are exactly the frames, and a cycle is the frames from the open node met
to the top. Each node finished goes on the end of `order` (07.03 uses it).
make runs the search before building; at 07.02 the build is still the
walk.

```
$ DS_TRACE=1 DS_STATS=1 bin/make -n -f tools/make/examples/diamond.mk
trace: enter 0 app
trace: enter 1 liba
trace: enter 2 common.h
trace: leave 2 common.h
trace: leave 1 liba
trace: enter 1 libb
trace: again 2 common.h
trace: leave 1 libb
trace: leave 0 app
(then the walk's lines, as at 07.01)
stats: depgraph: nodes 4, edges 4, walk visits 5, walk edges 4, search visits 4, search edges 4
$ DS_TRACE=1 bin/make -n -f tools/make/examples/cycle.mk
trace: enter 0 all
trace: enter 1 a
trace: enter 2 b
trace: enter 3 c
trace: cycle 4 a
make: dependency cycle: a -> b -> c -> a
```

Status 2. What the system's makes say for the same file:

```
GNU make 3.81:  make: Circular c <- a dependency dropped.       then runs c, b, a; status 0
GNU make 4.4.1: gmake: Circular c <- a dependency dropped.      the same
bmake:          bmake: Graph cycles through a                   and "`all' not remade because
                                                                of errors."
```

GNU make names only the edge it drops, the one that closes the cycle (c
needs a), and builds the rest as if it were not there; ours names the
whole cycle and builds nothing. GNU's edge is always the last of our path:
the test checks it on a cycle of 1 (`a: a`: "Circular a <- a", ours "a ->
a"), 2, 3, and one reached through a later goal. A cycle the goals do not
need is reported by neither.

Counts: on N diamonds the search enters 3N + 1 nodes and follows 4N edges;
the walk comes to 2^(N+2) - 3 (at N = 20: 61 against 4194301). A chain of
100000 targets: 100001 visits, no trouble; a cycle 100001 long is printed
whole.

Break it (two states: let a done node count as a cycle, deleting the `else
if (next->state == NODE_DONE)` branch; or never mark a node done, deleting
`node->state = NODE_DONE;`). Both give the same: the shared common.h looks
like a cycle, and reading the cycle off the path then looks for common.h on
a path that does not hold it, down past the bottom of the array, which
array_at stops:

```
$ bin/make -n -f tools/make/examples/diamond.mk
make: array: element 18446744073709551615 of 2
```

(2^64 - 1: index -1 as a size_t. A good aside on why the third state is
there: "seen" alone cannot tell a shared prerequisite from a cycle.)

## 07.03 Topological order, and what is out of date

Regions: out_of_date, build_in_order (make.c); newer() and made() are
`@from 07.03`, as are --order, --algo and the dispatch in main. The order
is the search's finishing order: a node is finished only after everything
it needs, so walking `order` from the start builds each target once,
after what it needs. A target is made when it is phony, its file is
missing, or something it needs was made in this run or is newer (mtimes to
the nanosecond: st_mtimespec on macOS, st_mtim on Linux). "Made in this
run" is what makes -n right: nothing really changes under -n, so times
alone would say the targets above a changed file are up to date. A file
with no rule must exist: `make: *** No rule to make target 'x', needed by
'y'.  Stop.` (y is the node the search reached x from, as in GNU make).

```
$ bin/make --order -f tools/make/examples/diamond.mk
common.h
liba
libb
app
$ bin/make -n                       (the built project)
make: Nothing to be done for 'all'.
$ touch lib/heap.c; DS_TRACE=1 DS_STATS=1 bin/make -n      (trace trimmed to the check lines)
trace: check build/lib/util.o: up to date
...
trace: check build/lib/heap.o: lib/heap.c is newer
trace: run build/lib/heap.o
trace: check build/lib/depgraph.o: up to date
trace: check build/libds.a: build/lib/heap.o was made
trace: run build/libds.a
trace: check bin/freq: build/libds.a was made
...
trace: check all: phony
stats: make: recipes run 7, commands 14, files checked 33, most at once 0
```

(that run was at 07.03, where the project has no readyq yet: 35 nodes, 34
of them needed by all; clean is the other.)

Same as the system's make: `-n` on this project prints the system's
commands to the byte (the trailing blanks of LIB included), a real build
prints the same lines, and the programs it builds are the same bytes as
the system's make's (compared with ZERO_AR_DATE=1 on macOS, which keeps
file times out of what ld and ar write; Linux needs nothing). After
changing lib/ds.h, lib/depgraph.h or tools/sort/sort.c, -n prints the
system's commands again. On the differential table (tests/tools/make.py
CASES: a chain, a diamond, variables, several rules for a target, phony
targets, include with a glob, continued lines and blanks before @, goals
on the command line, a command-line variable, an empty makefile, an
up-to-date target) ours and the system's agree on -n in a clean
directory, a real run (its output, its log and its files), a second run,
and -n after a file is made newer: with GNU make 3.81 on macOS and 4.4.1
on Linux. --order is checked by the system's tsort: given every edge and
the order's own consecutive pairs, tsort prints exactly our order (it
would report a cycle if the order broke an edge).

The slow version kept: `--algo=recurse` is 07.01's walk. Measured on
chains of diamonds (`python3 data/gen.py diamonds N -o dN.mk`; grow.py
does not suit it, since doubling N squares the time):

```
-n (print the commands, run none)
  N  targets  walk visits  recurse s  ratio   topo s
 16       49       262141      0.027           0.002
 18       55      1048573      0.099    3.7    0.002
 20       61      4194301      0.377    3.8    0.002
 22       67     16777213      1.538    4.1    0.002
 24       73     67108861      6.093    4.0    0.003
real runs (every recipe is sh -c 'touch NAME'), in an empty directory
  4 recurse    0.269 s (61 recipes)      topo  0.058 s (13 recipes)
  6 recurse    1.043 s (253 recipes)     topo  0.074 s (19 recipes)
  8 recurse    4.272 s (1021 recipes)    topo  0.109 s (25 recipes)
 10 recurse   16.877 s (4093 recipes)    topo  0.133 s (31 recipes)
 12 recurse   65.153 s (16381 recipes)   topo  0.145 s (37 recipes)
```

Each level doubles the walk; 73 targets take it 6 s to print and 12 levels
(37 targets) a minute to build. The system's make on d24: 0.01 s (3.81 and
4.4.1); ours in order on 1000 diamonds (3001 targets): 0.00 s, GNU make
3.81 0.08 s. On this project the walk is the 2.27 s against 0.95 s above.

What the walk leaves behind (worth a paragraph): it makes common.h, then
liba from it, then common.h again, then libb and app. liba is now older
than common.h: built from a common.h that is no longer there. The next
make in order rebuilds it:

```
$ bin/make --algo=recurse         (diamond.mk, a twentieth of a second between touches)
touch common.h
touch liba
touch common.h
touch libb
touch app
$ DS_TRACE=1 bin/make -n
...
trace: check liba: common.h is newer
touch liba
touch app
```

(Without the pause, Linux's file times, kept to a clock tick, can give
common.h and liba the same time; the test makes the recipes sleep 0.05 s.)

Break it (forget "made in this run": delete the `if (u->remade)` check in
out_of_date). After `touch lib/heap.c`, -n now lists only the compile of
heap.o (2 lines: mkdir and cc) and none of the 7 recipes a real build runs,
the archive and the five links; the real build is still right, because by
then heap.o's time really has changed. And a phony prerequisite no longer
makes its target: with `out: gen` and `.PHONY: gen`, an existing out is
left alone, where GNU make remakes it every time:

```
$ bin/make -f ph.mk           (broken)        $ make -f ph.mk         (GNU 3.81)
echo generating                               echo generating
generating                                    generating
                                              touch out
```

## 07.04 Building in parallel: a queue of ready work

Regions: readyq_init, readyq_push, readyq_pop (lib/readyq.c); finished,
build_queue (make.c); Job and next_command are `@from 07.04`, and so are
Node's needed_by (each edge is also recorded backwards in graph_edge) and
waiting. Kahn's algorithm over the search's nodes: each waits for as many
targets as it needs; those that need none are queued, in the search's
order; up to N recipes run, each a Job stepping through its recipe's
lines; when one ends, `wait()` says which, and when its last line is done
the target is finished: everything that needs it (and that the search
reached) waits for one fewer, and what reaches 0 is queued. A target that
comes off the queue up to date is finished at once. -j N picks
--algo=queue; --algo=queue alone is -j 1, which runs the queue's order:
breadth first, not the serial make's depth-first order (both valid). A
failed command stops the build: the commands already running are waited
for, nothing more starts, `make: *** [bad] Error 1`, `make: *** Waiting for
unfinished jobs....`, status 2.

```
$ DS_TRACE=1 DS_STATS=1 bin/make -j 2 -f tools/make/examples/diamond.mk    (check lines left out)
trace: ready common.h
trace: start common.h
touch common.h
trace: finish common.h
trace: ready liba
trace: ready libb
trace: start liba
touch liba
trace: start libb
touch libb
trace: finish libb
trace: finish liba
trace: ready app
trace: start app
touch app
trace: finish app
stats: make: recipes run 4, commands 4, files checked 4, most at once 2
stats: readyq: pushes 4, pops 4, longest 2
```

(liba and libb run together; here libb happened to finish first.)

```
examples/slow.mk (four targets, each `sleep 1; touch NAME`):
  bin/make -s           4.04 s
  bin/make -s -j 4      1.01 s       most at once 4; readyq pushes 5 (all and the four)
  bin/make -j 2         2.02 s
this project, clean builds:
  bin/make -s -j 1      0.940 s
  bin/make -s -j 2      0.489 s
  bin/make -s -j 4      0.286 s
  bin/make -s -j 8      0.214 s      system make -s -j 8: 0.195 s
```

The -j 4 build is the same bytes as the system's make's serial build, and
each of the 37 targets goes through the queue once.

What the tests hold it to, without a clock: the trace never shows `start
X` before `finish` of everything X needs; recipes that log `begin X` and
`end X` (with random short sleeps, on random graphs) never begin before
what they need has ended; two recipes that each wait (up to 10 s) for the
other to have started both finish under -j 2, and -j 1 fails, so they
really ran together; most at once is N; and every table makefile gives
the same commands (sorted), status and log as the system's `make -j 3`.

Worth a sentence: a recipe that makes two targets (`one.o two.o: defs.h`
with `touch one.o two.o`) runs once for each under -j, since both are
ready together and neither exists yet; serially the second finds its file
made. GNU make 3.81 and 4.4.1 do exactly the same (checked); GNU make 4.3
added grouped targets (`&:`) for it.

Break it (queue a target as soon as any one of its prerequisites is
finished: in finished(), push on every decrement instead of at 0). On this
project with -j 8, links start before the archive is made:

```
clang: error: no such file or directory: 'build/libds.a'
make: *** [bin/look] Error 1
make: *** Waiting for unfinished jobs....
stats: readyq: pushes 96, pops 59, longest 38
```

and on diamond.mk, `-n -j 2` prints `touch app` twice.

## GNU and BSD make: where they differ, and what we follow

macOS ships GNU make 3.81 as `make`; Debian's `make` is 4.4.1. The tests
compare with whichever the machine has, on cases where the two agree. They
differ (and we follow 4.4.1, untested against the system's) on:

- `+=` to an empty value: 3.81 gives " a", 4.4.1 "a"; `X +=` with nothing
  after it: 3.81 adds a space, 4.4.1 nothing.
- a recipe line continued with a backslash: 4.4.1 drops the next line's
  leading tab in what it prints and runs; 3.81 keeps it in what -n prints.
- quoting in messages: 3.81 `all', 4.4.1 'all' (ours: 'all'); a failed
  command: 3.81 `make: *** [x] Error 1` (ours), 4.4.1 `make: *** [Makefile:3:
  x] Error 1`.

bmake (BSD make, run on Linux; not on macOS) agrees on chains, diamonds,
phony targets, goals, command-line variables and up-to-date checks, and
differs where GNU make is GNU's:

- `include parts/*.mk`: "Could not find parts/*.mk": bmake does not glob
  an include, so it cannot read this track's Makefile at all;
- it strips the blanks before a comment from a value (`[one.o two.o]`
  where GNU make and ours keep `[one.o two.o   ]`);
- several rules for one target: prerequisites in makefile order (c d e f),
  where GNU make puts the rule with the recipe first (e c d f);
- a continued line keeps more blanks (`one  two`, GNU `one two`);
- it prints nothing for an up-to-date goal; cycles as above.

## The tests and the timeline

- 07.01: --graph on the project against `make -p -q`'s database; counts;
  the walk's 2^(N+2) - 3 on diamonds 1 to 8; lib/util.c compiled once per
  tool by the walk, once in order; the unsupported syntax errors; a makefile
  that includes itself; a chain too deep for the walk.
- 07.02: the cycle messages against the system's (the dropped edge is our
  last), unreached cycles, 3N + 1 and 4N on diamonds, a 100000-deep chain
  and cycle, the trace's nesting, 60 random graphs against a Python search.
- 07.03: --order valid and tsort agrees, the differential table, the
  project (-n, real build, same bytes, after three files change), the walk
  against the order on diamonds, the walk leaving liba out of date, the
  check reasons.
- 07.04: the queue's order, most at once on `wide`, the rendezvous, random
  graphs by trace and by log, the table against the system's -j 3, the
  project with -j 4, a failing recipe, bad -j values.

check-timeline at each lesson types into the shell: `--graph` and `-n` on
diamond.mk (the walk's 5 lines before 07.03, 4 after), cycle.mk (the
walk's guard at 07.01, the path from 07.02), and the ordinary error for
the next option; then timeline_after compares with the system's make on
the built project: before 07.03, every command of `make -n -B` is among
the walk's (92 commands against 36 at 07.01); from 07.03, both say
"Nothing to be done for 'all'". Whole runs on the Mac: `./learn test dsa
07` about 7 s; on Linux about 5 s.
