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
other: at an extension's lesson the site shows the core plus that
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

The lists are the direction; fit them to the code, as the core's were.
Order (the owner, 2026-11-15: "first finish highlighting", then "stop
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
  the message line, and the cursor row's message at a pause; Ctrl-G to a
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
  the 4 research problems master has. Lessons and art are next, from
  NOTES.md.
