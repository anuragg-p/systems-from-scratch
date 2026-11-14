# systems from scratch

**Code first, theory second.**

Real systems - a SQL database and a Unix kernel - built end to end and
read one lesson at a time. Each lesson adds a piece to a system that
builds and runs at every step, and shows it in the same order: where the
piece fits, the idea, the code itself with the notes that explain it, a
run that shows it working, and a way to break it on purpose. The theory
comes after, once you have seen it work.

## Start

Read the lessons on the site, and run the system as it stands at any of
them:

```
./learn serve                 the lessons in your browser (http://127.0.0.1:8000;
                              --port N for another port)
./learn run xv6 --at 02.03    build the kernel as it stands at a lesson and boot it;
                              its files go to build/at/xv6/02.03/, yours to change
                              (kept until the track's code changes; --fresh rewrites)
./learn run xv6               the same for the finished kernel (build/at/xv6/finished/)
./learn run db --at 04.02 -- demo.db "SELECT 1;"
                              args after -- go to the program
./learn bench db --at 07.03   build it the same way and run the benchmark on it
./learn files db --at 04.02 <dir>
                              just write the project at a lesson to <dir>; build nothing
./learn export <dir>          the site as plain files for a static host such as Vercel
```

Each lesson page shows the project as it stands at that lesson. "The code"
holds what the lesson adds, under the notes that explain it, and "Run it"
the commands that show it working. The Files drawer has every file of the
project at that lesson, whole.

## The book

The xv6 track reads alongside **Operating Systems: Three Easy Pieces**
(OSTEP) by Remzi H. Arpaci-Dusseau and Andrea C. Arpaci-Dusseau,
Arpaci-Dusseau Books, version 1.10, November 2023. It is free online at
https://pages.cs.wisc.edu/~remzi/OSTEP/ - every lesson ends with the
chapters that explain its concept, linked to the authors' own PDFs as
they ask, never copied. The book explains the ideas; this course builds
them, a lesson at a time.

## Credits

Each track is backed by real code or formats, credited on the site (the
track's overview, its home card, and /credits):

- **xv6** is derived from MIT's xv6 for RISC-V,
  https://github.com/mit-pdos/xv6-riscv, under the MIT licence; its full
  text is in `tracks/xv6/LICENSE`. The network and GUI modules are this
  course's own.
- **kilo** is derived from antirez's kilo,
  https://github.com/antirez/kilo, under the BSD 2-Clause licence; its full
  text is in `tracks/kilo/LICENSE`. Syntax highlighting is left out of the
  core, and the fixes to the original are listed in `tracks/kilo/NOTES.md`.
- **db** is this course's own engine, written to SQLite's file format
  (SQLite is public domain) and checked against the real sqlite3. It
  contains no SQLite code.

`NOTICE` says per track what was taken and what is ours. A track names its
upstream in `UPSTREAM` in its `track.py`; an outline names the repos it is
proposed to follow in its `upstream` field.

## How it is organized

A **track** is one system built end to end: a kernel, a compiler, an
interpreter. Every track has the same shape, so the tools work for any
of them:

```
learn                         one command for every track
harness/                      shared: the command, the project at each lesson, the web UI
templates/                    lesson, module, test and track templates
tracks/<id>/track.py          title, kind, how to build and run it
tracks/<id>/lessons/NN-slug/  a module: README.md + NN.LL-slug.md lessons
tracks/<id>/...               the reference code, with @build regions
tracks/<id>/tests/            internal checks (see "For authors")
outlines/<name>.md            a track still being planned (templates/outline.md):
                              the site shows it as coming soon, with no lessons to open
outlines/<name>/NN/           its module art: cover.svg and icon.svg
```

A module whose `README.md` front matter says `optional: true` is an
**extension**: the site lists it after the core, under "Extensions". Each
one builds on the finished core and is independent of the others: at an
extension's lesson the project is the whole core plus that extension's
lessons so far.

Lessons are numbered `NN.LL` (module, lesson). The code a lesson builds
is marked in the reference source:

```c
  // @build 02.02 kalloc
  // Take one page off kmem.freelist, holding kmem.lock. Fill it with 5s
  // so no caller can count on getting zeroes. Return it, or 0 if the
  // list is empty.
  ...reference code...
  // @end
```

The comment lines after `@build` say what the region does; the code up
to `@end` is the lesson's own, which "The code" shows under the lesson's
notes. `@stub <code>` sets what `check-skeleton` puts in its place when it
cuts the lesson out.

## Adding a track

1. `./learn new-track <id> <kind> "<title>"` creates `tracks/<id>/track.py`.
2. Fill in `SOURCES` and `STUBS` (which files hold regions, and what a
   cut region becomes), `prepare(root)` and `run_argv(root)` (how to
   build and run it), and the fixtures your internal checks use.
3. Write the reference code with `@build` regions, and a lesson per
   region: `./learn new <id> 01.01 "<title>"`.

## For authors

Tests are internal: they verify that the reference code works and that
each lesson's code is really needed (cut it out and its test fails). The
site never shows them.

```
./learn test xv6              every internal check against the reference
python3 tracks/xv6/tests/upstream/run.py [--both] [--slow]
                              xv6's own usertests on the kernel (07.03's check runs the quick
                              set; see tracks/xv6/tests/upstream/README.md)
./learn check-skeleton xv6    each lesson cut out still builds, and its check fails
./learn check-timeline xv6    the project as the site shows it at each lesson builds and boots
./learn selftest              the harness and web UI's own unit tests
./learn check                 every lesson has a doc; every file has a lesson it comes with;
                              outlines follow the template; all text is ASCII; and verify's
                              static checks on every annotated lesson (no builds, about a second)
./learn verify [db] [04.02]   every annotated lesson says only what its project really does
                              (see "Verifying a lesson" below)
./learn map --write           regenerate the map below
```

The site shows the project as it stands at the lesson being read: a file
appears with the first lesson that has a `@build` region in it, or with the
lesson `FILES_FROM` in `track.py` names for it (every file without regions
needs one). Code of later lessons is left out with the whole definition
around it, and "The code" shows what each lesson adds: new files whole (one
over 150 lines that no lead-in in the notes talks about starts folded to its
functions, or, with none to fold, as its first 20 lines), and the functions
it builds in files that were there already. What it adds there through
`@from` sits behind one closed "Also added in this lesson" row: an older
definition as its signature and two lines each side of each addition, and a
header's new prototypes as a count. A piece the notes' `### name` lead-in
names is shown open, under its notes.

Code outside the regions that comes with a later lesson - a call in
`main()`, a prototype, a syscall table entry, a Makefile rule - is marked
with that lesson in any file, with the file's own comment leader, as a
block or, for one line, at the very end of that line's comment:

```c
  // @from 05.03
  virtio_disk_init();
  // @end

#define SYS_fork 1   // @from 06.04
```

An `@else` part holds, commented out, what stands there before that lesson
(the idle loop `main()` runs until 04.02 brings the scheduler); `@internal`
... `@end` marks test aids that are built but never shown. No marker is ever
shown on the site, and none changes the track's own build. The project at
every lesson must build with the track's normal command and run:
`./learn check-timeline` checks that (see `harness/timeline.py`), with each
track's `timeline_boot` steps and, where a run leaves files behind, its
`timeline_after` check (db has sqlite3 open them). Where the finished code
calls something a later lesson brings, the earlier project has an ordinary
error in its place, such as db's `WHERE is not supported`, never a crash.

A lesson's figures are SVG files in the `figures/` folder beside it, each on a
line of its own as `![Caption](figures/NN.LL-name.svg)` (the rules are in
`harness/web/art.py`). A **stepped figure** shows a process as frames the
reader steps through with Back and Next: each top-level `<g class="step">` in
the file is one frame, drawn over the rest of the file, and a `<title>` first
in it is that step's caption. Without scripts, and in print, the page shows
every frame one under another. Use one only where the idea is a process, at
most one per lesson, with frames made from a real run of the reference code
(`art/steps.py` writes the step groups from a figure generator). At most 40
frames (and 1 MB of them in all): past that the page shows the last frame as a
still figure and `./learn check` reports it.

## Verifying a lesson

`./learn verify` holds each lesson to what the project at that lesson really
does. A lesson is read top to bottom in the reader's terminal (and a second
one where the page says "from another terminal"), as a reader follows it:
every transcript is typed again and its output compared, every "change this
line" is made, every quoted line of code is looked up in the project as it
stands at that lesson. It is an author's tool: no page, lesson or learner
help mentions it (the code: `harness/verify.py`; its tests:
`harness/tests/test_verify.py`).

```
./learn verify                    every lesson not listed as pending, both tracks
./learn verify xv6 07.02          one lesson (ids are prefixes: 07 is the module)
./learn verify -j 4 --fresh       4 at a time, ignoring the cache
./learn verify --static           only what needs no build (what ./learn check runs)
./learn verify --report           every skip and allowance, with its reason; pending lessons
./learn verify --keep             keep each lesson's terminal and files, even when it passes
./learn verify --allow-missing    a missing QEMU, toolchain or sqlite3 is a skip, not a failure
```

A lesson that passed is cached (`build/verify/cache/`) until the lesson, the
project at any lesson it uses, the verifier or a tool changes. Replays run in
`build/verify/run/<track>/<id>/`, a copy of the checkout's layout where
`./learn run`, `bench` and `files` are the real commands; nothing is written
under `work/` or `tracks/`. xv6 needs QEMU and the RISC-V toolchain, db needs
sqlite3 (Homebrew's when there is one, as the tests use).

`tracks/<track>/lessons/verify-pending.txt` lists the lessons not annotated
yet. `./learn verify` and `./learn check` skip them; naming a lesson runs it
anyway. To take a lesson on: annotate it, run `./learn verify <track> <id>`
until it passes, then delete its line from the list.

### What is checked without an annotation

- **Every fenced block is code from the project at that lesson**, line by line
  (whitespace and trailing comments aside; `...` stands for code left out,
  alone or inside a line). A block that is anything else - a transcript,
  code the reader types, a picture - must say so with an annotation. A
  block of nothing but `./learn ...` commands is checked as commands.
- **`name()`, `file.c`, `path/file.c:name` and `build/at/<track>/<id>/file`
  in backticks exist at that lesson** (the build/at form at the lesson it
  names), unless the same sentence names the lesson they come with ("`write()`
  from lesson 05.07 on") or a `mention` annotation declares them.
- `./learn` commands are ones learners use, on a track and lesson that
  exist; no test, stub, exercise, workspace or `--ref` talk; front matter and
  sections as `templates/lesson.md`; figures exist (unused ones are reported).

### Annotations

An annotation is an HTML comment: the site never shows it (the renderer drops
every comment, so the page is the same with or without). One goes on lines of
its own; a block annotation goes directly before its fenced block (blank
lines are fine, text is not), and several may stack there.

```
<!-- verify: KIND name=value name="value with spaces" name='value "with" quotes' flag -->

<!-- verify: KIND options
rule or patch line
...
-->
```

| kind | for | options |
|---|---|---|
| `session` | the next block is a terminal transcript: replay it | `at=`, `run=`, `type=`, `send=`, `cwd=`, `terminal=`, `fresh`, `host`, `before`, `more`, `hangs[=N]`, `panics=`, `build-fails=`, `exit=`, `wait=`, `timeout=`, `needs=` |
| `file` | the next block is an excerpt of a file of the project or one its build writes | `path=` (required), `at=` |
| `patch` | change a file of the reader's copy of the project | `file=` (required), `at=`, `append`, `create`, `old=` with `new=` |
| `revert` | undo the patches (of `file=`, or all) | `file=`, `at=` |
| `setup` | what the prose says to do but no block shows, done unseen | `at=`, `cwd=`, `terminal=`, `timeout=` |
| `fact` | a value the prose states, from a command | `cmd=`, `expect=`, `at=` |
| `quote` | the next block is code from another lesson's project | `at=` |
| `skip` | the next block is not checked | `reason=` (required) |
| `mention` | names in backticks that are not at this lesson | `names=`, then `at=` or `outside reason=` |

`at=` is a lesson id or `finished`; it defaults to the lesson's own id (for a
session, to the `--at` of its `run=`). In a double-quoted value only `\"` and
`\\` are escapes: `"\d+"` is the regex `\d+`.

**session.** The block is what the reader's terminal shows. A line that
starts with the prompt the terminal is showing (`$ `, and the track's own:
db's `db> `, `   ...> `, `sqlite> `; xv6's `$ `, `(qemu) `) is typed, and so
is the next line of a command the shell is still reading (a quote left open);
the rest is what must come back, compared exactly. The terminal is one bash
per lesson, started in the checkout, without job control: `cd build/at/...`,
variables, pipes and `$ ./learn run ...` lines all work as they do for the
reader (a block that starts `./learn` is typed at the top of the checkout),
`time` prints one line as zsh's does, and a block with no start line carries
on with whatever the last one left running. When a program exits mid-line
(`db> ` then Control-D), the shell's `$ ` starts a line of its own.

- `run="..."`: the block does not show the command that starts it (the prose
  does); it is typed at the computer's prompt first (quitting whatever was
  running): `./learn run xv6 --at 07.02`, or any command, `make qemu
  UDPFWD=2000` with `cwd=project`. The block starts after its echo (and
  after ./learn's "Running ..." line), or at the prompt when its first line
  is one.
- `send="ctrl-a c"`: keys pressed before the block (ctrl-X, enter, tab, esc,
  space, backspace, "quoted text", or words, typed with a space between them).
- `type="info mem"`: a line typed (with Enter) before the block, which the
  block leaves out: the block starts with what it printed.
- `cwd=project` (or a path in the checkout): `cd` there first, unseen.
- `terminal=2`: the block happens in a second terminal (a reader's "from
  another terminal"), while whatever runs in the first goes on.
- `fresh`: start the lesson's copy of the project again; `host`: quit what is
  running, the block is typed at the computer's own prompt.
- `wait=N`: done after N quiet seconds (a system that prints nothing at all;
  one started by ./learn is ready once quiet after it starts anyway);
  `timeout=N`: how long to wait for a prompt (default 30, for slow commands).
- `needs="sample"`: tools beyond the track's (a missing one makes the lesson
  "missing", as a missing QEMU does).
- Expectations: `hangs[=N]` (nothing more for N seconds, default 3, and no
  prompt comes back), `panics="text"` (the output reaches "panic: text"),
  `build-fails="text"` (./learn's build fails, printing text), `exit=N` (the
  exit status of the last command typed at the computer's prompt).

What the reader does at a line where no prompt shows is a rule:

```
line 3 keys ctrl-p       press these keys once the screen shows everything before
                         line 3 (its start, too: a prompt it opens with); the
                         output they bring is line 3 on. Words between keys are
                         typed: line 5 keys echo one ctrl-h ctrl-h two enter
lines 4-5 typed          the reader types these lines as shown (after whatever
                         prompt the terminal has up, or none)
line 2 output            this line starts with a prompt but is printed, not typed
                         ("$ paint: draw in the window" when a background program
                         writes after the shell's prompt)
```

A trailing prompt the block does not show is ignored; anything else extra is
an error. Allowances are explicit, narrow and listed by `--report`:

```
...                      a line of its own in the block (the reader sees it too):
                         any number of lines
more                     (option) the output goes on after the block's last line
before                   (option) the output began before the block's first line
trimmed                  (option) lines picked from a longer output, in order, with
                         anything between them (a page that says "(trimmed)")
lines 3-4 unordered      these lines in any order (harts that print at once)
lines 3-4 mixed          these lines' characters in any order, on any number of
                         lines (harts mid-line)
lines 3-4 optional       these lines may be missing (a hart cut off by a panic)
line 6 anywhere          this line may come anywhere in the output, or with
                         optional not at all
line 5 ~ REGEX           line 5 matches REGEX instead (Python syntax, whole line;
                         everything after "~ " is the regex, spaces too)
vary TEXT KIND           wherever TEXT is in the block, any KIND: int, num, hex,
                         addr (0x...), word, any, or /REGEX/; quote TEXT with spaces
ignore job-reports       leave out the shell's job and kill reports ("[1] 4242",
                         "Killed: 9", "zsh: killed ..."), which differ by shell
ignore /REGEX/           leave out output lines REGEX matches whole (tcpdump's
                         "reading from file ..." on stderr)
```

**file.** The block is an excerpt of `path` in the project at `at`, after a
build: `build/kernel/kernel.asm`, `build/mkfs.log`, a file the reader made.
It may start and end anywhere in the file; `...` inside it, `trimmed` and the
rules above apply.

A note after a line of code that points at it, `    <- delete this line` or
`  <- was: x`, is the lesson's own marker: quoted code and file excerpts are
compared without it.

**patch.** A unified-diff-like body: `-` a line to find and delete, ` ` (a
space) a line to find and keep, `+` a line to add, and `@block` for the lines
of the block right after the annotation (the code the page tells the reader
to type, indented like the line before it). The `-` and context lines must
occur exactly once in the file (whitespace aside); every `+` line must be on
the page, whole, without its `;`, or as the words it changes (a line
commented out needs only the line). `append` adds at the end, `create` makes
a new file. A change inside a line is `old="< 0" new="<= 0"` (no body): `old`
must occur exactly once in the file, and the page must show `new` (or, to
delete, `old`). A patch stays until a `revert`, as the reader's edit would.

**setup.** Steps the page describes in prose but shows no block for, done in
the terminal and never compared, one per line:

```
<!-- verify: setup at=07.03 cwd=project
$ make qemu                    typed at the prompt; waits for it to finish or show one
keys ctrl-a x                  pressed
$ cp build/fs.img spare.img
replay 05.01 "$ python3 rows.py | ./db demo.db"
                               do what that block of 05.01 does (by its first line,
                               or its number in the lesson): replay a session unseen,
                               or apply the code the reader typed there, to this at=
-->
```

A setup is for what the reader really does; it never stands in for a block
the page should show. A replayed lesson's page is part of the cache key.

**fact.** `cmd` runs in the project's directory after a build; its output,
stripped, must be `expect`, and the sentence after the annotation must state
`expect`. A fact checks a value: it is not a way to make files (that is
`setup`).

### Examples, from the pilot lessons

db 03.01, a transcript that starts itself, and the same lines one lesson back:

    <!-- verify: session -->
    ```
    $ ./learn run db --at 03.01
    Running db as it stands at 03.01 (The tokenizer). Its files are in build/at/db/03.01/
    db: a SQL database, from scratch. Statements end with ;  .help for help
    db> SELECT 'a;
       ...> b';
    Error: SQL is not supported
    ```
    ...
    <!-- verify: session run="./learn run db --at 02.05" -->
    ```
    db> SELECT 'a;
    Error: SQL is not supported
    ```

db 04.02, Break it: delete a branch, then run on the file Run it filled:

    <!-- verify: patch file=src/expr.c
    -    } else if (a.type == V_NULL || b.type == V_NULL) {
    -        set_null(out);
    -        return;
    -    }
    +    }
    -->
    <!-- verify: session run="./learn run db --at 04.02 -- where.db" -->

xv6 01.03, a boot whose hart lines interleave, a line the reader adds, an
address that depends on the build, and putting it back:

    <!-- verify: session run="./learn run xv6 --at 01.03"
    lines 3-4 mixed
    -->
    ...
    <!-- verify: patch file=kernel/main.c
         printf("xv6 kernel is booting\n");
    @block
    -->
    ```
    printf("%p %d %x %ld\n", main, -42, 255, -1L);
    ```
    ...
    <!-- verify: session run="./learn run xv6 --at 01.03" more
    vary 0x000000008000007a addr
    -->
    ...
    <!-- verify: revert file=kernel/main.c -->

xv6 07.02, harts in either order; a hang, then Control-P in the same boot:

    <!-- verify: session run="./learn run xv6 --at 07.02"
    lines 3-4 unordered
    -->
    ...
    <!-- verify: session run="./learn run xv6 --at 07.02" hangs=2 -->
    ...
    <!-- verify: session send=ctrl-p -->

And the others: `<!-- verify: fact cmd='./db t.db "PRAGMA page_count;"' expect=59 -->`
directly above "... the file is 59 pages ...";
`<!-- verify: skip reason="a picture of the tree, not code" -->`;
`<!-- verify: quote at=finished -->` above code the workbench lessons show
from the finished system; `<!-- verify: mention names="mmap() pread()" outside
reason="SQLite's, not this engine's" -->`.

### Reading a failure

Each problem is `file:line: what`, at the line of the lesson that is wrong:

```
tracks/db/lessons/04-queries/04.02-where-and-expressions.md:158: quoted code not in the
    project at 04.02; it comes with 04.03: 'Op *op = new_op(db, "Limit", limit_next);'
tracks/db/lessons/04-queries/04.02-where-and-expressions.md:264: session at 04.02: the
    lesson shows    '3'
    the project printed '2' (output line 7)
    output around it:
        6 | db> SELECT id FROM t WHERE n = NULL;
    >   7 | 2
```

A failed lesson keeps its terminal in `build/verify/run/<track>/<id>/`:
`transcripts.txt` has what the screen showed for each block and the whole
session, and `build/at/...` there holds the reader's copy of the project,
patches and all.

### Rules for annotating

- An annotation never changes what the learner sees. A block may gain or lose
  a line only to make it true (a `...` where output was trimmed, the real
  output where it was wrong), never to make a check pass.
- Never weaken a check to get a pass. When the lesson is wrong, fix the
  lesson (re-run the real thing and paste it); when a block honestly cannot
  be checked, `skip` it with a reason that says why. `--report` lists them.
- Allowances are for what legitimately varies - timing, pids, ports, build
  addresses, harts printing at once - and as narrow as the variation.
- Every Run it and Break it transcript gets a `session`; every "change this
  line" a `patch`; every number the prose asserts that a command can show, a
  `fact`.

## The map

<!-- map:start -->
### A SQL database in C, from scratch

Track `db` - kind: database - 27 lessons - on the site: `./learn serve`, then /t/db


**Module 00 - The workbench**

- 00.01 [How a database works](tracks/db/lessons/00-workbench/00.01-how-a-database-works.md) - lab
- 00.02 [Measuring a database](tracks/db/lessons/00-workbench/00.02-measuring-a-database.md) - lab

**Module 01 - Pages**

- 01.01 [The database file as pages](tracks/db/lessons/01-pages/01.01-the-database-file-as-pages.md) - with code
- 01.02 [The page cache](tracks/db/lessons/01-pages/01.02-the-page-cache.md) - with code, decision boundary
- 01.03 [Records: varints and serial types](tracks/db/lessons/01-pages/01.03-records-varints-and-serial-types.md) - with code, decision boundary

**Module 02 - The B-tree**

- 02.01 [A leaf page: cells and search](tracks/db/lessons/02-btree/02.01-a-leaf-page-cells-and-search.md) - with code
- 02.02 [Insert and split](tracks/db/lessons/02-btree/02.02-insert-and-split.md) - with code
- 02.03 [Interior pages and the root](tracks/db/lessons/02-btree/02.03-interior-pages-and-the-root.md) - with code
- 02.04 [Cursors and range scans](tracks/db/lessons/02-btree/02.04-cursors-and-range-scans.md) - with code
- 02.05 [Delete and free pages](tracks/db/lessons/02-btree/02.05-delete-and-free-pages.md) - with code

**Module 03 - SQL**

- 03.01 [The tokenizer](tracks/db/lessons/03-sql/03.01-the-tokenizer.md) - with code
- 03.02 [The parser and the AST](tracks/db/lessons/03-sql/03.02-the-parser-and-the-ast.md) - with code
- 03.03 [The schema: CREATE TABLE and the catalog](tracks/db/lessons/03-sql/03.03-the-schema-create-table-and-the-catalog.md) - with code

**Module 04 - Running queries**

- 04.01 [INSERT and a full table scan](tracks/db/lessons/04-queries/04.01-insert-and-a-full-table-scan.md) - with code
- 04.02 [WHERE and expressions](tracks/db/lessons/04-queries/04.02-where-and-expressions.md) - with code
- 04.03 [ORDER BY and LIMIT](tracks/db/lessons/04-queries/04.03-order-by-and-limit.md) - with code
- 04.04 [UPDATE and DELETE](tracks/db/lessons/04-queries/04.04-update-and-delete.md) - with code

**Module 05 - Indexes and the planner**

- 05.01 [An index is a B-tree](tracks/db/lessons/05-indexes/05.01-an-index-is-a-btree.md) - with code
- 05.02 [Index lookups and range scans](tracks/db/lessons/05-indexes/05.02-index-lookups-and-range-scans.md) - with code
- 05.03 [Choosing a plan, and EXPLAIN](tracks/db/lessons/05-indexes/05.03-choosing-a-plan-and-explain.md) - with code

**Module 06 - Transactions**

- 06.01 [What a crash does to a half-written page](tracks/db/lessons/06-transactions/06.01-what-a-crash-does-to-a-half-written-page.md) - lab
- 06.02 [The rollback journal and atomic commit](tracks/db/lessons/06-transactions/06.02-the-rollback-journal-and-atomic-commit.md) - with code
- 06.03 [Recovery](tracks/db/lessons/06-transactions/06.03-recovery.md) - with code
- 06.04 [A write-ahead log](tracks/db/lessons/06-transactions/06.04-a-write-ahead-log.md) - with code

**Module 07 - Fast**

- 07.01 [Reading the benchmark](tracks/db/lessons/07-fast/07.01-reading-the-benchmark.md) - lab
- 07.02 [Where the time goes](tracks/db/lessons/07-fast/07.02-where-the-time-goes.md) - lab
- 07.03 [One more optimisation, measured](tracks/db/lessons/07-fast/07.03-one-more-optimisation-measured.md) - with code

### A text editor in C, from scratch

Track `kilo` - kind: editor - 16 lessons - on the site: `./learn serve`, then /t/kilo


**Module 00 - The workbench**

- 00.01 [How a terminal editor works](tracks/kilo/lessons/00-workbench/00.01-how-a-terminal-editor-works.md) - lab
- 00.02 [What the terminal sends and understands](tracks/kilo/lessons/00-workbench/00.02-what-the-terminal-sends-and-understands.md) - lab

**Module 01 - The terminal**

- 01.01 [Raw mode](tracks/kilo/lessons/01-terminal/01.01-raw-mode.md) - with code
- 01.02 [Reading a key](tracks/kilo/lessons/01-terminal/01.02-reading-a-key.md) - with code
- 01.03 [The window size](tracks/kilo/lessons/01-terminal/01.03-the-window-size.md) - with code

**Module 02 - The screen**

- 02.01 [One frame, one write](tracks/kilo/lessons/02-screen/02.01-one-frame-one-write.md) - with code

**Module 03 - A text viewer**

- 03.01 [Rows: opening a file](tracks/kilo/lessons/03-viewer/03.01-rows-opening-a-file.md) - with code
- 03.02 [Moving the cursor, and scrolling](tracks/kilo/lessons/03-viewer/03.02-moving-the-cursor-and-scrolling.md) - with code
- 03.03 [Tabs](tracks/kilo/lessons/03-viewer/03.03-tabs.md) - with code
- 03.04 [The status bar and messages](tracks/kilo/lessons/03-viewer/03.04-the-status-bar-and-messages.md) - with code

**Module 04 - A text editor**

- 04.01 [Inserting characters](tracks/kilo/lessons/04-editor/04.01-inserting-characters.md) - with code
- 04.02 [Enter: splitting a line](tracks/kilo/lessons/04-editor/04.02-enter-splitting-a-line.md) - with code
- 04.03 [Deleting, and joining lines](tracks/kilo/lessons/04-editor/04.03-deleting-and-joining-lines.md) - with code
- 04.04 [Saving](tracks/kilo/lessons/04-editor/04.04-saving.md) - with code

**Module 05 - Search**

- 05.01 [Find as you type](tracks/kilo/lessons/05-search/05.01-find-as-you-type.md) - with code
- 05.02 [Next match, previous match, and going back](tracks/kilo/lessons/05-search/05.02-next-match-previous-match-and-going-back.md) - with code

### A Unix kernel for RISC-V, from scratch

Track `xv6` - kind: kernel - 33 lessons, +2 optional modules - on the site: `./learn serve`, then /t/xv6


**Module 00 - The workbench**

- 00.01 [How a kernel works](tracks/xv6/lessons/00-workbench/00.01-how-a-kernel-works.md) - lab
- 00.02 [Running and debugging the kernel](tracks/xv6/lessons/00-workbench/00.02-running-and-debugging-the-kernel.md) - lab

**Module 01 - Boot**

- 01.01 [The first instruction](tracks/xv6/lessons/01-boot/01.01-the-first-instruction.md) - with code
- 01.02 [Machine mode and the drop to supervisor mode](tracks/xv6/lessons/01-boot/01.02-machine-mode-and-the-drop-to-supervisor-mode.md) - with code, decision boundary
- 01.03 [The UART and printf](tracks/xv6/lessons/01-boot/01.03-the-uart-and-printf.md) - with code

**Module 02 - Memory**

- 02.01 [The physical memory map](tracks/xv6/lessons/02-memory/02.01-the-physical-memory-map.md) - decision boundary
- 02.02 [The page allocator](tracks/xv6/lessons/02-memory/02.02-the-page-allocator.md) - with code, decision boundary
- 02.03 [Spinlocks and multiple harts](tracks/xv6/lessons/02-memory/02.03-spinlocks-and-multiple-harts.md) - with code
- 02.04 [Sv39 page tables](tracks/xv6/lessons/02-memory/02.04-sv39-page-tables.md) - with code, decision boundary

**Module 03 - Traps and interrupts**

- 03.01 [Kernel traps](tracks/xv6/lessons/03-traps/03.01-kernel-traps.md) - with code, lab
- 03.02 [Timer interrupts](tracks/xv6/lessons/03-traps/03.02-timer-interrupts.md) - with code, decision boundary
- 03.03 [The PLIC and console input](tracks/xv6/lessons/03-traps/03.03-the-plic-and-console-input.md) - with code, lab

**Module 04 - Processes**

- 04.01 [The process table and kernel stacks](tracks/xv6/lessons/04-processes/04.01-the-process-table-and-kernel-stacks.md) - with code
- 04.02 [Context switch and the scheduler](tracks/xv6/lessons/04-processes/04.02-context-switch-and-the-scheduler.md) - with code
- 04.03 [Sleep and wakeup](tracks/xv6/lessons/04-processes/04.03-sleep-and-wakeup.md) - with code
- 04.04 [Preemption](tracks/xv6/lessons/04-processes/04.04-preemption.md) - with code, lab

**Module 05 - Storage**

- 05.01 [The virtio block device](tracks/xv6/lessons/05-storage/05.01-the-virtio-block-device.md) - with code
- 05.02 [The buffer cache](tracks/xv6/lessons/05-storage/05.02-the-buffer-cache.md) - with code
- 05.03 [mkfs and the on-disk layout](tracks/xv6/lessons/05-storage/05.03-mkfs-and-the-on-disk-layout.md) - with code
- 05.04 [The write-ahead log](tracks/xv6/lessons/05-storage/05.04-the-write-ahead-log.md) - with code, lab
- 05.05 [Inodes](tracks/xv6/lessons/05-storage/05.05-inodes.md) - with code
- 05.06 [Directories and path names](tracks/xv6/lessons/05-storage/05.06-directories-and-path-names.md) - with code
- 05.07 [Open files](tracks/xv6/lessons/05-storage/05.07-open-files.md) - with code

**Module 06 - User space**

- 06.01 [The trampoline and user traps](tracks/xv6/lessons/06-user-space/06.01-the-trampoline-and-user-traps.md) - with code, decision boundary
- 06.02 [System calls](tracks/xv6/lessons/06-user-space/06.02-system-calls.md) - with code, decision boundary
- 06.03 [exec and the ELF loader](tracks/xv6/lessons/06-user-space/06.03-exec-and-the-elf-loader.md) - with code
- 06.04 [fork, exit and wait](tracks/xv6/lessons/06-user-space/06.04-fork-exit-and-wait.md) - with code
- 06.05 [sbrk and the user heap](tracks/xv6/lessons/06-user-space/06.05-sbrk-and-the-user-heap.md) - with code
- 06.06 [Pipes](tracks/xv6/lessons/06-user-space/06.06-pipes.md) - with code
- 06.07 [File system calls](tracks/xv6/lessons/06-user-space/06.07-file-system-calls.md) - with code

**Module 07 - Userland**

- 07.01 [The user library](tracks/xv6/lessons/07-userland/07.01-the-user-library.md) - with code
- 07.02 [init and the shell](tracks/xv6/lessons/07-userland/07.02-init-and-the-shell.md) - with code, lab
- 07.03 [The utilities](tracks/xv6/lessons/07-userland/07.03-the-utilities.md) - with code, lab

**Extensions** - optional modules, each independent of the others, each built on the finished core


**Module 08 - Network** (optional)

- 08.01 [The virtio network card](tracks/xv6/lessons/08-network/08.01-the-virtio-network-card.md) - with code
- 08.02 [Ethernet and ARP](tracks/xv6/lessons/08-network/08.02-ethernet-and-arp.md) - with code, lab
- 08.03 [IPv4 and UDP](tracks/xv6/lessons/08-network/08.03-ipv4-and-udp.md) - with code
- 08.04 [Sockets](tracks/xv6/lessons/08-network/08.04-sockets.md) - with code, decision boundary
- 08.05 [A DNS lookup](tracks/xv6/lessons/08-network/08.05-a-dns-lookup.md) - with code, lab

**Module 09 - GUI** (optional)

- 09.01 [A framebuffer](tracks/xv6/lessons/09-gui/09.01-a-framebuffer.md) - with code
- 09.02 [Pixels from user space](tracks/xv6/lessons/09-gui/09.02-pixels-from-user-space.md) - with code, decision boundary
- 09.03 [Keyboard and mouse](tracks/xv6/lessons/09-gui/09.03-keyboard-and-mouse.md) - with code
- 09.04 [A drawing library](tracks/xv6/lessons/09-gui/09.04-a-drawing-library.md) - with code
- 09.05 [A program worth showing](tracks/xv6/lessons/09-gui/09.05-a-program-worth-showing.md) - with code, lab

<!-- map:end -->
