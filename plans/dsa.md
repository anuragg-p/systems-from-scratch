# Plan: track `dsa` - data structures and algorithms, by building the tools that use them

Status: plan (direction set by Fable; implementation by Opus agents).
Started 2026-11-14, once kilo's code and lessons were in (its clean-up
pass still running), on the owner's word: "after this start building the
data structures and algorithm part".
The outline is now plans/dsa-outline.md (moved out of outlines/ when
tracks/dsa took the id over): its modules and lesson titles are the list
to build. Its module art stays in outlines/data-structures-and-algorithms/
until every module has copied its cover and icon. This file holds the
decisions.

## What the learner ends with

Ten tools in C - freq, sort, edit, grep, spell, diff (and patch), make,
route, gzip (and gunzip), git - built on one small library of data
structures they wrote, each held to the real tool: same output as the
system's sort and grep, a diff that patch applies, a gzip file gunzip
opens, a repository git reads and checks.

## The shape of every module

Write the tool the obvious way. Run it on real input and watch it stop
finishing (or run out of memory). Bring in the structure or algorithm.
Measure the difference. This order is the point of the track: a lesson
that opens with the structure and then looks for a use is wrong.

## Decisions

- Language: C11, libc only. Nothing is built in, so the learner writes the
  array, the table, the heap and the sort that every tool then uses.
- Layout: `lib/` (the structures, one .c each; `ds.h` for what step 1
  built, and one header per structure added after it, so agents working
  in parallel never edit the same header), `tools/<name>/` (one tool
  each, with its own `tool.mk`), `data/` (inputs), `bench/` (the growth
  harness). One Makefile; each tool is `bin/<name>`. A tool uses lib/ from the lesson
  that built the piece, never before.
- Ours, not derived: no code is taken from the tools we copy. They are
  written to the documented formats (RFC 1951 and 1952, the unified diff
  format, git's object, tree, commit and index formats) and checked
  against the system's tools, as db is checked against sqlite3. The one
  exception is `edit` (below).
- `edit` (module 03) starts from the finished core of this course's kilo
  track, which is derived from antirez's kilo (BSD-2-Clause): its file
  comes whole at 03.01 with the licence beside it and is not taught again.
  The lessons are only the buffer: an array, a gap buffer, undo and redo,
  a piece table, the pieces in a balanced tree.
- Measuring: the harness doubles the input and reports the ratio of
  running times, for the learner. Internal tests do not gate on the
  clock: each structure counts its own work (comparisons, probes, node
  visits, printed with `DS_STATS=1`) and tests assert on the counts.
- Checked against the system's tools, BSD or GNU, whichever the machine
  has: tests must pass on macOS and Linux. Where the two differ (sort's
  locale, grep's dialect), the test pins it (`LC_ALL=C`, `grep -E`).
- Inputs come with the track and are never downloaded by a build or a
  test: a public-domain book for text, a word list, a source tree (this
  repo's own), and one city's road map from OpenStreetMap (ODbL, credited
  in NOTICE) as plain nodes and edges. Large inputs are made from these
  by a seeded generator, so every run sees the same bytes. Each file's
  licence is read, not assumed, and recorded in NOTICE.
- Scope of each tool: enough to be the real thing on ordinary input, and
  an ordinary error for what is left out, never a crash.
  - sort: bytewise order, -r -n -u -k, a file bigger than a memory cap
    set by a flag.
  - grep: fixed strings and -E (literals, classes, . * + ? | groups,
    anchors), -n -c -v -i.
  - diff: unified output; patch applies unified diffs.
  - make: rules, prerequisites, recipes, variables (`=`, `+=`, `$(VAR)`
    in prerequisites and recipes), `include` with a glob, .PHONY, -j:
    what this track's own Makefile uses, so it can build the track.
  - gzip: inflate of all three block types; deflate with fixed and
    dynamic codes.
  - git: init, add, commit, log, diff, merge-base, on loose objects and a
    version 2 index, with our own SHA-1 and zlib framing. A packed
    repository gets an ordinary error.
- The site: `tracks/dsa/` takes the id over from the outline as soon as it
  exists. Do not export or publish the site while the track is half built.
- Art is not optional (track card and icon, cover and icon per module,
  the architecture map and at least one diagram in every lesson). The
  outline's module art moves over to the track's modules.

- Stepped figures (agreed by the owner, 2026-11-14): where the idea
  is a process (a sort, a heap sift, a table being filled, a search
  spreading over a graph), the lesson's diagram is a short series of
  frames the reader steps through, forward and back, with no autoplay.
  The frames are made from a real run of the reference code, so they
  cannot disagree with it. Without scripts, in the export's plain form or
  with reduced motion, the frames show one under another as ordinary
  diagrams. Covers and icons stay still. This needs one harness change
  (figure syntax, the SVG loader, a little script and its tests), done
  as its own piece of work before step 3 and not while another session is
  editing the harness.

## Build order for the agents

1. Skeleton, `lib/` and modules 00 to 02 (workbench, freq, sort), by one
   agent: the Makefile, track.py, the fixtures every tool's tests share
   (run a tool, run the system's tool, compare), the data and generator.
2. The other tools, one agent each, in parallel, each inside its own
   `tools/<name>/` and its own fixtures file: 03 edit, 04 grep, 05 spell,
   06 diff, 07 make, 08 route, 09 gzip. Then 10 git, alone, because it
   uses 06's diff and 09's deflate.
   Each step is done when `./learn test dsa`, `check-skeleton`,
   `check-timeline` and `selftest` pass; `./learn check` passes only once
   the module's lessons are written (a template page has no figures yet).
   "The same output as the system's tool" means the same bytes where the
   tool's output is fixed (sort, grep, gzip -d) and the same content where
   BSD and GNU format it differently (uniq -c pads counts differently).
3. Lessons, module READMEs and art, in parallel by module, from the
   finished code and `tracks/dsa/NOTES.md`.
4. Review: full internal run, every lesson read on the site.

## Step 1 as built (skeleton, lib, modules 00 to 02; see tracks/dsa/NOTES.md)

- Tools: `paste` (module 00: joining lines, slow by rescanning, fast by
  remembering the end), `freq`, `sort`, and `look` for 02.06 (binary
  search in a sorted file, checked against the system's look).
- The slow version of everything stays runnable by a flag, and a feature
  whose lesson is ahead gives an ordinary error with exit status 2.
- A tool is added with files only: `tools/<name>/` with its `tool.mk`,
  `tests/tools/<name>.py` (fixtures and timeline steps, which track.py
  loads), its lessons, and a header of its own for any new structure.
- Data: `data/book.txt`, The Adventures of Sherlock Holmes with every
  Project Gutenberg reference removed, as their licence asks; larger
  inputs are generated with a fixed seed.
- Passes on macOS and on Linux (Debian in Docker, GNU tools).
- Parallel agents work in git worktrees, one each, and commit on their
  own branch; nothing is merged to master unchecked.
