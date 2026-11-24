# Plan: track `kilo` - a text editor in C, from scratch

Status: plan (direction set by Fable; implementation by Opus agents).

## What the learner ends with

A terminal text editor in one C file that they can really use: it opens a
file, scrolls, edits, saves and searches, and draws its own screen with
escape codes, with no library between it and the terminal. It is antirez's
kilo, built up a lesson at a time, the way the xv6 track is MIT's xv6.

## Decisions

- Track id `kilo`, kind `editor`, title "A text editor in C, from scratch".
- Upstream: https://github.com/antirez/kilo, BSD-2-Clause, Copyright (c)
  2016 Salvatore Sanfilippo. The code is derived from its `kilo.c`
  (`"derived": True`), so `tracks/kilo/LICENSE` holds its licence whole and
  comes with the project from the first lesson, and `NOTICE` gets a `kilo`
  section saying what was taken and what is ours.
- Code: one `kilo.c` and a `Makefile`, C99, libc only. Function names and
  structure stay as upstream has them, so a reader can hold antirez's file
  beside ours. Comments are rewritten as lesson notes. Every departure
  from upstream is listed in `tracks/kilo/NOTES.md` with its reason.
- The core is the bare minimum: upstream without syntax highlighting. The
  highlighting code is cut out cleanly (no `hl` arrays, no colours, no
  syntax database), not stubbed. It returns later as an extension.
- The project at every lesson builds and runs. Before files exist the
  editor is a blank screen that quits on Ctrl-Q; a key whose lesson is
  still ahead does nothing or shows an ordinary message, never a crash.
- Tests are internal and drive the editor as a user does: on a
  pseudo-terminal of a fixed size, keys in, then either the screen (the
  escape stream turned into a grid of text) or the saved file is checked.
- No benchmark.

## Modules (core)

00 The workbench
  00.01 How a terminal editor works (lab: the whole loop, key to screen)
  00.02 What the terminal sends and understands (lab: see the bytes)
01 The terminal
  01.01 Raw mode
  01.02 Reading a key
  01.03 The window size
02 The screen
  02.01 One frame, one write
03 A text viewer
  03.01 Rows: opening a file
  03.02 Moving the cursor, and scrolling
  03.03 Tabs
  03.04 The status bar and messages
04 A text editor
  04.01 Inserting characters
  04.02 Enter: splitting a line
  04.03 Deleting, and joining lines
  04.04 Saving
05 Search
  05.01 Find as you type
  05.02 Next match, previous match, and going back

The list is the direction. Where upstream's code does not divide this way
(one function that does two lessons' work), merge or split lessons to fit
the code, and say so in NOTES.md. Do not restructure the code to fit the
list.

## Extensions (started 2026-11-15 on the owner's word; each `optional: true`)

Each extension stands on the finished core and is independent of the
others: at an extension's lesson the site shows the core plus that
extension only. So neither may need the other's code, though both are in
the tree. No core lesson may change when one is added: the workbench
(00.01, 00.02) runs and measures the core at 05.02, not the finished
project.

06 Syntax highlighting: upstream's own, cut out of the core in step 1 and
   restored here, in kilo.c, under upstream's names. Real bugs in it are
   fixed the way the core's were (the original quoted, a test).
   06.01 A colour for every character
   06.02 Numbers and strings
   06.03 Comments, on one line and across many
   06.04 Keywords, and a syntax chosen by the file's name
   06.05 Showing the match
07 A language server client: ours, in files of its own (kilo.c takes
   only the calls into it), C99 and POSIX. Checked against a real server,
   clangd, and against a small scripted server in the tests for what must
   be exact and for hostile input (a damaged frame, a server that dies
   mid-message: never a crash, a hang, or a lost file). With no server
   the editor works as before and says so in one line.
   07.01 Starting a server: fork, exec and two pipes
   07.02 Messages: Content-Length and JSON-RPC
   07.03 Reading JSON: just enough of a parser
   07.04 Keys and the server at once: poll()
   07.05 Telling the server what you see: initialize, didOpen, didChange
   07.06 Diagnostics: errors as you type
   07.07 Go to definition

08 Undo and redo: Vim's way, cut to kilo's size, in kilo.c. Before a row
   changes, what it was is kept; a record that is applied takes what was
   there and so becomes its own opposite, as Vim's u_undoredo() swaps.
   Records are made in the core's row functions, so anything that edits
   through them is remembered. Ctrl-Z and Ctrl-R.
   08.01 Remembering what a line was
   08.02 Redo: a record that undoes itself
   08.03 One Ctrl-Z, one thought: steps
   08.04 The saved point, and a bound on memory
09 An API, and Lua on top of it: Neovim's shape, and fully extensible
   (the owner, 2026-11-24): the test is that the editor's own features
   could have been written as scripts. The editor's operations as a table
   of typed functions in C; Lua (the real one, its source in the tree
   unchanged, the one thing in this track we do not write) embedded and
   given that table; any key and the editor's events bound to Lua
   functions; colour and the status bar drawn from a script; a script
   that goes wrong never takes the file with it; the editor run with no
   screen at all; and, as the proof, find-like, colouring and vi-key
   plugins written only in Lua. Not built, and said so: timers and
   background work, more than one file, marks that move with the text.
   09.01 A second language inside the editor: embedding Lua
   09.02 The API is a table
   09.03 Changing the text from a script: set_lines
   09.04 Any key can run a Lua function
   09.05 Events: autocommands
   09.06 Drawing from a script: highlights and the status bar
   09.07 Asking, opening, leaving: input(), open(), quit()
   09.08 Scripts that go wrong
   09.09 The editor without its screen
   09.10 Features as scripts

The lists are the direction; fit them to the code, as the core's were.
08 and 09 were started on 2026-11-24 on the owner's word, with this
direction for both: take the mechanisms from the notable editors (Vim and
Neovim, Zed, Emacs, Helix, VS Code), so a reader learns how the real ones
work at their core; every claim about another editor is read from its
source at a named tag or commit and recorded in NOTES.md before a lesson
states it. The owner also allowed changes to the core for 09; the designs
do not need them (hooks behind markers, as 06 and 07), so the core's
lessons stand as they are. Order: 08's code, then 09's code on top of it
while 08's lessons and art are made, then 09's lessons and art.
Order before that (the owner, 2026-11-15: "first finish highlighting", then "stop
after completing highlighting"): 06 whole, its code, then its lessons and
art, then a read of it. 07 was started on 2026-11-24 on the owner's word:
its code, tests and notes first (see "Module 07 as built"), then its
lessons and art from NOTES.md. Art for everything, as in the core.

The `dsa` outline's module 03 (gap buffer, piece table, balanced tree)
builds on this track: it starts from this track's finished core and
teaches only the buffer (plans/dsa.md).

## Build order for the agents

1. Reference code: `kilo.c` with `@build` regions and `@from` markers,
   `track.py` (build, run, fixtures, timeline hooks), internal tests,
   LICENSE, NOTICE section, NOTES.md. Done when `./learn test kilo`,
   `./learn check-skeleton kilo`, `./learn check-timeline kilo`,
   `./learn check` and `./learn selftest` all pass.
2. Lessons, module READMEs and art, from the finished code and NOTES.md,
   in parallel by module. Art is not optional: the track's `art.svg` and
   `icon.svg`, a `cover.svg` and `icon.svg` for every module, the
   architecture map in every lesson, and at least one diagram of the idea
   in every lesson, the same as db and xv6 have.
3. Review: full internal run, a read of every lesson on the site.

## Step 1 as built (reference code; see tracks/kilo/NOTES.md)

- The 16 lessons are the plan's, in its order. 02.01 also brings the
  resize handler (it redraws the screen); 05.02's own region is small
  (Escape goes back), its arrow keys are additions to 05.01's function.
- Before 02.01 there is no screen: at 01.01 to 01.03 the program prints
  each key's code (and at 01.03 the window size) and quits on Ctrl-Q.
- Twelve departures from upstream, each marked in kilo.c with the
  original line quoted: highlighting cut whole, raw mode entered before
  the window is measured, tab stops at multiples of 8, files with \r\n
  shown, Home and End no longer typed as bytes, a join onto a line wider
  than the screen, left arrow at the top of a scrolled screen, search in
  the stored text, two off-by-one comparisons, a typo, the Makefile,
  and (found while the lessons were written) the welcome line's padding
  going negative on a terminal narrower than 33 columns, which hung the
  editor.
- Tests drive the editor on a pseudo-terminal of a fixed size through a
  screen emulator in track.py. check-timeline runs programs on pipes, so
  track.py carries a small relay that holds the pseudo-terminal. No
  harness change was made.
- "All pass" was true on macOS and on Linux with musl (Alpine), not on
  Linux in general. On glibc (Debian, found while module 06 was added)
  the 02.01 test and the timeline at 02.01 and 03.04 failed: kilo exited
  on the first resize, because there `signal()` in a C99 build is System
  V's. Fixed in the core at 02.01 with `sigaction()` and `SA_RESTART`,
  departure 33 in NOTES.md; since then everything passes on glibc too.
- All 16 lessons pass ./learn verify and are off the pending list. The
  transcript checker cannot show a full-screen program, so the editor's
  own screens are declared as skipped, each with how it was checked.

## Steps 2 and 3 as done

- 16 lessons, 6 module pages, a map in every lesson, at least one
  diagram of the idea in every lesson, a cover and icon per module, the
  track card and icon (generators in art/kilo/).
- A clean-up pass fixed the narrow-terminal hang, moved six comments that
  named something a later lesson brings behind @from markers, corrected
  NOTES.md, and read all 16 lessons in order for consistency.
- Kept from upstream and documented in NOTES.md: Delete acts as
  Backspace, control characters go into the text, a key within 0.1 s
  after an unknown escape sequence is lost.

## Module 07 as built (code, tests and notes; 2026-11-24)

- Files of its own: lsp.c and lsp.h (the client), json.c and json.h (a
  JSON reader and jsonQuote, knowing nothing of kilo). The Makefile builds
  them from 07.01 (json.c from 07.02), same flags. The design (files,
  hooks, messages, limits) was fixed by the coordinator; tracks/kilo/
  NOTES.md, "07 A language server client", lists where the code departs
  from it and why.
- This relaxes the plan's "kilo.c takes only the calls into it": besides
  one-line hooks (lspStart in main, lspPump then lspWaitKey in
  editorReadKey, lspDrawRow after a row is drawn, Ctrl-G and Ctrl-B),
  kilo.c has a short section "The editor's side of the language client"
  above main() with editorCursor (07.06) and editorJump (07.07): moving the
  cursor and replacing the file are editor code, and stay where E is.
- The seven lessons are the plan's, in its order; two titles changed to
  fit the code: 07.01 "fork, exec and three pipes" (a close-on-exec pipe
  brings back execvp's errno), 07.05 "didOpen and didChange" (initialize
  is sent at 07.02).
- The server: clangd for C and C++ by the file's name; KILO_LSP names
  another for any file (set and empty: none). No server for the file: not
  a word, and the screen is the core's to the byte. Keys and the server
  in one poll(); writes queued and written as the pipe takes them; the
  whole text sent 300 ms after the last key, a waiting change replaced by
  a newer one; diagnostics underlined by drawing over the row, counted in
  the message line when they change, or, when the cursor's row has one, its
  message instead (as the list arrives, and at a pause); Ctrl-G to a
  definition (another file only with no unsaved changes), Ctrl-B back.
- Independence holds: the project at all 16 core lessons and the 5 of 06
  is byte for byte what it was (diff -r); at a 07 lesson module 06 is not
  there; the row-drawing hook is outside 06's blocks, the same on core +
  07 and in the finished file. In the finished project an underlined span
  is drawn over in the default colour, not 06's.
- Tests: one per lesson, a scripted server (tests/lsp_server.py) for
  everything exact and every hostile case (under ASan), a fuzzer
  (tests/lsp_fuzz.c) of the frame reader, the JSON reader and whole
  messages, and clangd on a sample program where it is installed (a
  printed skip line where it is not; the harness has no SKIP). The
  timeline uses the scripted server only.
- All pass on macOS (Apple clangd 21.0.0), Debian trixie (glibc, gcc 14,
  clangd 19.1.7) and Alpine (musl, gcc 14, clangd 20.1.8): ./learn test
  kilo (28), check-skeleton, check-timeline; ./learn check reports only
  the 4 research problems master has. Lessons and art followed, from
  NOTES.md (below).

## Module 07's lessons, art and read (all on 2026-11-24)

- 7 lessons and the module page, written in parallel on two branches
  (07.01 to 07.04 and the page; 07.05 to 07.07) from a lesson design,
  and the art on a third from an art design: a cover and icon, the map in
  every lesson (the client in three rows under the core's grid: its
  features, messages, then the server with start beside it), and 16
  figures of the idea, at least two a lesson, five of them stepped
  (07.01 fork-exec, 07.02 split-reads, 07.03 descent, 07.04 poll-set,
  07.07 jump). Generators: art/kilo/figs07.py, covers.py, archmap.py.
  Every lesson passes ./learn verify; none is on the pending list.
- The sample program: 07.01 to 07.04 make sum.c and add.h in the
  lesson's folder; 07.05 on make them in "sam ple" inside it, so the URI
  has a space to escape, and 07.05 says so.
- figs07.py runs the projects: with the scripted server (bytes fixed)
  and with clangd (Apple clangd 21 here; other versions give other
  bytes). What needed instrumented builds it does not repeat (the
  descriptor tables, wake-up counts, delays) it reads from NOTES.md and
  checks against its words. Its runs type the lessons' own keys.
- The read (in order, on the site in light and dark and at 390 px, Back
  and Next on every stepped figure; the Run it of every lesson but 07.05,
  and the Break it of 07.02, 07.06 and 07.07, run again with clangd):
  json.h's comment at 07.02
  (said a phrase twice); 07.02's reply in pieces (NOTES.md and the text
  had an older scripted server's 125 bytes; the figure's 171 is now);
  07.04's wake-ups (the figure's and the text's numbers were from two
  servers; NOTES.md said the 2 at 07.04 were "the pause and the answer",
  they are the answer and the Ctrl-Q); 07.07's jump figure asked at
  character 17 where the text says 18; five regions with no lead-in;
  captions that said more or less than their figures; NOTICE's kilo
  section now says module 07 is ours. Details in the commits.
- lspDrawRow's signature runs onto a second, indented line, which the
  site did not take for the start of a function (harness/timeline.py,
  definition_span), so at 07.06 its region showed without the signature
  or its notes. Fixed in the code, on the coordinator's word: its opening
  brace is on a line of its own at column 0, the only function in the
  track written so (NOTES.md 07, "Departures from the design"). The
  harness is unchanged.
- On a phone (390 px) every figure fits and nothing overflows; the
  figures are drawn 640 wide and scale down, as in the core and 06.

## Module 08 as built (code, tests and notes; 2026-11-24)

- In kilo.c, as 06 is: a block "The undo history" at the top (the record
  types, struct undoRecord, undoStep, undoState and the global U) and a
  section "Undo and redo" after editorSave. Hooks behind `@from` markers,
  one line each: undoSave() in editorInsertRow, editorDelRow, the three
  row-text functions and editorInsertNewline's cut; undoClear() and the
  recording switched off around editorOpen's read; editorSave sets the
  saved point (08.04); one call in editorProcessKeypress after the key is
  read; Ctrl-Z and Ctrl-R. The design (Vim's records and swap, steps as
  runs of a kind, the saved point, an 8 MB bound) was fixed by the
  coordinator; tracks/kilo/NOTES.md, "08 Undo and redo", lists where the
  code departs from it and why.
- The four lessons are the plan's, in its order, under its titles. 08.01
  puts rows back (undoPut) a key a step; 08.02's undoApply takes what is
  there first, so the record becomes its opposite, and adds the redo
  stack; 08.03 brings steps as runs of a kind, the leave-out rule and the
  cursor; 08.04 the saved point and the bound. Allocations are checked from
  08.01 (the history is given up, never the edit).
- Found against the design, and settled in the code: editorOpen's early
  return for a new file would have left recording off, so it is off only
  around the read; the saved point is lost when more steps are dropped
  than were under it, not whenever one under it is; invariant 4 as written
  does not hold for edits that cancel out (stated as it holds in NOTES.md);
  a jump of module 07 is not an edit, it starts a new history; the bound
  is kept when a record is made, so an undo can pass it until the next
  record.
- Independence holds: the project at all 28 lessons of the core, 06 and
  07 is byte for byte what it was (diff -r); no line of 06 or 07 is in an
  08 project, and each 08 project builds with -Werror. Test aids are
  `@internal` (a second count of the history after every key, a smaller
  bound, a check that a record's row is in the file).
- Tests: one per lesson; every kind of edit undone and redone with the
  file saved after; steps; the saved point; the bound; random keys under
  ASan in five runs (sizes, a .c file, undo and redo in the mix, a small
  bound); 06's colours after an undo and 07's server sent the text after
  one. The core's 0101 typed Ctrl-Z and expected it in the text; its last
  check now takes either, as module 08 is in the tree or not (NOTES.md 08,
  "Found on the way"). ./learn test kilo (32), check-skeleton and
  check-timeline pass on macOS; the module's tests and timeline also on
  Debian and Alpine (the 07 containers), where every 08 project builds with
  gcc -Werror.
- The editors' sources (Vim, Neovim, Emacs, Zed, Helix, VS Code) were read
  at named tags and quoted in NOTES.md, with what could not be confirmed.
  Lessons and art follow, from NOTES.md.

## Module 08's lessons, art and read (2026-11-25)

- 4 lessons and the module page, written from a lesson design (on
  2026-11-24), and the art on another branch from an art design: a cover
  and icon, the map in every lesson (under the core's grid, steps, saved
  point, redo and records in a row, and the history under them all),
  and 9 figures of the idea, four of them stepped (08.01 undo-enter, 08.02
  swap and two-stacks, 08.04 saved-point). Generators: art/kilo/figs08.py
  (it runs each lesson's project, with a trace patched into a scratch copy,
  and checks its numbers against NOTES.md), covers.py, archmap.py.
- The read (in order, on the site in light and dark and at 390 px, Back and
  Next on every stepped figure; every Run it and Break it typed again
  through `./learn run` as written, on a 10x44 pseudo-terminal): 08.03's
  runs figure had a second row of its own (a, Left, b on an empty file);
  it now has the keys Run it types next, `so `, Down, Left three times,
  `and `, from the same run as the lesson. 08.02 numbered rows from 1
  where the figures and a record's `at` count from 0; it counts from 0 now,
  and 08.01 says the cursor's row and column count from 1. 08.01's Break it
  (a double free) warns before the key that kills kilo and says `reset`
  first; its Linux result was run in the module 07 Debian container
  (glibc's "double free detected in tcache 2", SIGABRT; SIGTRAP on the
  Mac). The site's code spans drop a trailing space (harness/web/
  markdown.py), so `so `, `if ` and `and ` showed as "so", "if", "and"
  where the reader types them: 08.03 and 08.04 now say "and a space". The
  one-record figure named "the leave-out rule", which no lesson does; 08.01
  read as if Ctrl-Z's case did nothing; the module page said every lesson
  compares five editors. figs08.py's tree() copied no file of module 09
  and no longer built; it copies script.c, script.h, api.h and lua/ now,
  and every other figure comes out byte for byte as before.
- 08.02 has two stepped figures, the only lesson in any track with more
  than one; both step on their own on the page. art/steps.py's "at most
  one per lesson" now allows it; the root README says the same and was
  left alone (another session's edits are in it).
- On a phone every figure fits and nothing overflows; the figures are drawn
  640 wide and scale down, as in 07. `./learn verify` passes 08.01 to
  08.04; `./learn check` lists nothing for kilo 00 to 08.

## Module 09 as built (code, tests and notes; 2026-11-24)

- Files of its own: script.c and script.h (everything that includes
  lua.h: the state, the one protected way in, the dispatcher, references,
  the Lua on top, the count hook, the allocator, the panic function, kilo
  -l) and api.h (the API's types); in kilo.c a section "The API" above
  main() (24 functions, the table, --api-info, the prompt, keys by name,
  autocommands, highlights, the status line) and one-line hooks. No Lua
  header in kilo.c. Lua 5.4.9's README and src/ unchanged in lua/ (a commit
  of its own, sha256 checked; NOTICE has its licence); hidden from the site,
  fetched by the reader, copied into a written-out project by track.py's
  prepare() (supply_lua). The Makefile builds liblua.a once; its four
  shapes (core, core + 07, core + 09, all) use blocks nested in other
  blocks' @else parts. The design (two revisions, the second "fully
  extensible") was fixed by the coordinator; NOTES.md, "09", lists where
  the code departs from it and where it was wrong.
- Nine lessons, 09.01 to 09.09, as the revised list; 09.10 (plugins in Lua
  only) follows the review. NOTES.md says, for each of 09.10's three
  proofs, whether the API reaches it: vi keys and colouring yes; a find yes
  but for putting back the exact view (no set_view).
- Independence holds: the projects at all 32 lessons to 08.04 are byte for
  byte master's (diff -r, against cf9919a); no 06, 07 or 08 code in a 09
  project, none of 09 in an 08 one; every 09 project builds with -Werror.
  With module 08 merged in, what a key's scripts change is one step of undo
  of its own (finished tree only; NOTES.md 09, "With module 08").
- Tests: one per lesson (0901 to 0909) with init files the tests write,
  every error text, the cursor rule, references let go, the guards
  (Ctrl-C on five kinds of runaway script, the 64 MB bound, os.exit, the
  panic aid, Ctrl-Q never a script's), kilo -l, and a fuzz in Python of
  random API calls under ASan and UBSan (in the editor and with no
  screen). In the finished tree: 06's colours and 07's scripted server
  after set_lines, 08's undo and redo of a script's change. KILO_INIT is
  set and empty in every test's editor unless the test gives one.
- Found: module 06's memset of the NULL that realloc(p, 0) gives on glibc
  (UBSan, on Debian; 06 unchanged, the fuzz names it); the count hook slows
  every Lua instruction (a loop 1.4 times, a call 2.4 times); a finalizer
  or a backtracking pattern cannot be stopped by Ctrl-C; open() does not
  tell 07's server.
- The editors' sources (Neovim at v0.12.6, Vim, Emacs, Zed, VS Code,
  Redis, Helix) were read at named tags and quoted in NOTES.md, with what
  could not be confirmed. Where Neovim differs from the design's guesses:
  the cursor after set_lines, set_lines not the base of set_text, the TUI a
  process since 0.9, init.lua before files are read, no interrupt for Lua.
- All pass on macOS; on Debian trixie and Alpine 3.22 (the 07 containers)
  every test, check-skeleton of 09 and check-timeline, every 09 project
  with gcc -Werror. Lessons and art follow, from NOTES.md.

## Module 09's lessons, art and read (2026-11-25)

- 10 lessons and the module page, from a lesson design, on four writers'
  branches: 09.01 to 09.03 and the module page, 09.04 to 09.06, 09.07 to
  09.09, each running its lessons' examples on the projects as written out
  (NOTES.md 09, "what the lessons ran"); and 09.10, a lab, written after
  the review, on the three plugins built on the code's branch
  (plugins/vi.lua, colour.lua and find.lua: only Lua, no line of C; test
  0910). The art on two branches, from an art design: a cover and the icon
  (redrawn as a plug), the map in every lesson (three rows under the core's
  grid: kilo.c's side of the API, then Lua and the guards, then the scripts
  and no screen; archmap.py), and 12 figures for each half, art/kilo/
  figs09a.py for 09.01 to 09.05 (five stepped: 09.01 stack, 09.02
  dispatch, 09.03 set-lines, 09.04 reference, 09.05 nesting) and
  figs09b.py for 09.06 to 09.10.
- The read of the track's card and cover, the module page and 09.01 to
  09.05 (in order, on the site in light and dark and at 390 px, Back and
  Next on every stepped figure; every Run it and Break it typed again
  through `./learn run` as written, on an 8 x 80 or 8 x 72 pseudo-
  terminal). 09.01's fetch was run exactly as written in a fresh `./learn
  files` project: the checksum was the lesson's, the first make built
  Lua's 32 files and kilo in 3.6 s (2.5 s user), kilo 318072 bytes.
  Found and fixed: 09.01's "Where this fits" put "Lua itself" under the
  interpreter, where the map has one box, Lua, for both; the protected-call
  caption said Left and Right of a figure drawn above and below; the stack
  caption put the 2 "after the protected call" where the frame has it
  after lua_call(), inside it; the checksum, inline, made the page scroll
  sideways at 390 px (now a block); and Break it said how to get the
  terminal back only after the run (now before it, `stty sane`). 09.03 and
  09.04 gave the bar's rows, from 1, beside the API's, from 0, without
  saying which ("row 3 now", "row 2, after the b", "row 1", "row 2"): each
  now says, and 09.03 says once that the bar counts from 1. 09.05: `new `
  showed as "new" (the dropped trailing space) and is "`new` and a space";
  its Break it warns before the key that hangs the editor (a second
  terminal; `reset`). The module page links its ten lessons (07's and
  08's pages list none: the site lists lessons from the files).
- Found fine: every figure against its text and the runs (the cover's
  Ctrl-D screen; the registry's 4 5 6, 5 6 7, 4 6 7; 12 names in kilo.api
  at 09.04; the tick and save time lines; the nesting frames' word
  counts), every message, screen, byte count and Break it result of the
  five lessons (09.04's `-3.7060546875` from a fresh start only), the
  lessons' editor claims against NOTES.md 09 (Zed in its confirmed wording,
  no "sandbox"), the init file started the same way in every lesson that
  has one, no dead link, nothing naming NOTES.md, a test or an agent.
  NOTES.md 09: Zed's cell in "The notable editors" says what was confirmed,
  not "a sandbox"; the lines that said 09.10 was not built are current.
- 09.06 to 09.10: see the commits of the second read.
- `./learn verify` passes 09.01 to 09.05; `./learn check` lists nothing for
  kilo; `./learn test kilo` passes (all 42). Once, run beside the
  read's screenshots and verify, 0908 failed at its last step: the fuzz's
  four Ctrl-Q, 0.1 s apart, met a pseudo-terminal kilo had already closed
  (EIO on the send); alone three times and in the whole run again, it
  passed. The test is unchanged.
