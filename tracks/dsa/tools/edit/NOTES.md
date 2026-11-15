# edit: notes for the lesson writers (module 03)

Everything here was run on the reference code, or on the project as
`./learn files dsa --at NN.LL` writes it: Apple M4 Pro, macOS 26.6.2,
Apple clang 21, Python 3.12. The tests, check-skeleton and check-timeline
also pass on Linux (Docker debian:stable-slim, aarch64, gcc 14.2.0, Python
3.13.5, dash as /bin/sh), where every lesson's project builds with no
warnings. Times are the fastest of three runs, with the file already in the
page cache. Every "break it" was run as described, on the project at its
lesson, and its output is pasted.

## What it is

`edit` is the kilo track's finished editor (raw mode, keys, the screen in
one write, cursor and scrolling, search, saving, the quit warning) with its
text moved behind one interface, `lib/text.h`, and four structures behind
it. The terminal, key and screen code comes whole at 03.01 and has no
regions: the lessons are only the structures in `lib/`.

```
lib/text.h, text.c   03.01  the interface (insert, erase, read, write, free), the
                            checks on positions, text_load, DS_TRACE helpers (whole)
lib/flat.c, flat.h   03.01  the text in one array
lib/gap.c, gap.h     03.02  a gap buffer
lib/undo.c, undo.h   03.03  undo and redo: two stacks of edits (lib's Array)
lib/pieces.c, .h     03.04  a piece table, its pieces in a linked list
lib/ptree.c, .h      03.05  the same pieces in an AVL tree
tools/edit/edit.c    03.01  the editor (whole; @from markers for later lessons)
tools/edit/LICENSE   03.01  kilo's BSD-2-Clause licence, beside the code derived from it
tools/edit/gen.py    03.01  inputs for bench/grow.py: typing, scattered, opening
```

Flags: `--algo=array|gap|pieces|tree` (from 03.02; the default is gap at
03.02-03.04 and tree from 03.05), `--replay SCRIPT` (from 03.01; `-` is
standard input). Keys are kilo's, plus Ctrl-Z (undo) and Ctrl-Y (redo).

```
$ ./learn run dsa --at 03.01 -- edit f.c                the editor on a terminal
$ ./learn run dsa --at 03.02 -- edit --algo=gap --replay - data/book.txt
```

### The interface, and how the editor finds lines

A Text is bytes: `insert(pos, s, n)`, `erase(pos, n)`, `read(pos, buf,
n)`, `write(FILE *)`, `free`; positions are 0 to len. Every structure's
struct starts with a `Text`, so a pointer to one is a pointer to the other
(C's way of doing an interface: a table of function pointers, `TextOps`).
Lines are the editor's business. kilo keeps an array of rows; edit keeps
only the row on the top line of the screen and where it starts
(`E.rowoff`, `E.topoff`), and finds every other row it needs by reading on
from there (`rowSpan`, `findNewline`, `lineStart`; 128 bytes at a time,
doubling to 4096 for long lines). An edit before the top of the screen
moves `topoff` (`afterInsert`, `afterErase`). So a key costs the editor a
screenful of reading whatever the file's size, and what is left to grow
with the file is the structure. Measured in the 03.01 test's way, a file of
10 lines and one of 20000, five keys typed on row 2 (24x80):

```
the editor's bytes read a key:   about 1200 (10 lines), about 3500 (20000 lines)
flat array's bytes moved a key:  171 (10 lines), 448871 (20000 lines)
```

The one read of the whole text the editor makes is at the start, on a
terminal only: it counts the newlines for the status bar ("N lines"). The
replay never counts them.

### Departures from the kilo track's kilo.c (all in edit.c)

- The text: rows replaced by text.h, as above. `editorTypingAt` does what
  kilo's insert does below the last row (adds empty rows) and past the end
  of a row (pads with spaces), as byte inserts.
- Saving writes the bytes the text holds, exactly: a file whose last line
  has no newline is saved without one, and "\r\n" stays "\r\n" (kilo saves
  every row with "\n"). It writes a new file beside the old one (mkstemp
  `NAME.edit-XXXXXX`) and renames it over it, keeping the old file's mode
  (0644 less the umask for a new one): the old file is whole until the new
  one is, and the piece table, which maps the old file, goes on reading it
  (03.04). Cost: hard links to the file are broken, a symlink is replaced
  by a file, and the directory must be writable. Messages are kilo's:
  `13 bytes written on disk`, `Can't save! I/O error: No such file or
  directory`.
- Control bytes other than tab are drawn as `?` (kilo sends them raw; a
  "\r" from a CRLF file would blank the row). Bytes of 128 and up go to the
  terminal as they are; a column is a byte, as in kilo.
- The welcome on an empty file says what holds the text: `edit -- the text
  in a flat array` (always 32 characters). The status bar's right side is
  the structure and the row: `gap buffer 1/40`; as in kilo, when the two
  sides do not both fit, the right side is left out.
- Ctrl-Z and Ctrl-Y: before 03.03 they set the message `Nothing to undo:
  this editor keeps no history` (`... to redo ...`); from 03.03 they undo and
  redo. The help line: `HELP: Ctrl-S = save | Ctrl-Q = quit | Ctrl-F =
  find`, and from 03.03 `... | Ctrl-Z/Y = undo/redo`.
- Standard input not a terminal: an ordinary error, `edit: f.txt: standard
  input and output must be a terminal (or use --replay SCRIPT)`, status 2
  (kilo spins). DS_TRACE is switched off when stderr is a terminal.
- `editorReadKey` returns a byte as unsigned, and the search prompt calls
  `isprint` only below 256 (kilo's two limits on that, noted in its NOTES).
- Kept from kilo: everything else, including `coloff` counting bytes but
  applied to the rendered row, Home and End bound to nothing, the search
  putting a match's row at the top of the screen.

### --replay

One command a line, `#` a comment. Positions are bytes from 0; lines and
columns from 1. Errors exit 2 with `edit: script line N: ...`.

```
goto POS | goto end | goto LINE:COL     move the cursor
type TEXT      a key at a time (\n Enter, \t tab, \\ backslash, \xHH a byte)
paste TEXT     one insert, the cursor after it
back N         Backspace N times (stops at the start)
delete N       one erase of the N bytes after the cursor (fewer at the end)
undo [N], redo [N]                       from 03.03; before it: unknown command 'undo'
print          the whole text on stdout
save           to FILE, as Ctrl-S
```

Every structure prints the same bytes for the same script; the tests hold
them to a Python model (`Model` in tests/tools/edit.py), undo grouping and
cursor included.

### DS_STATS lines

```
stats: edit: inserts I, erases E, bytes read R      the editor's own edits and reads
stats: flat array: bytes loaded L, inserts I, erases E, bytes moved M, grows G, bytes copied C
stats: gap buffer: bytes loaded L, inserts I, erases E, bytes moved M, grows G, bytes copied C
stats: piece list: bytes mapped M, bytes loaded L, bytes added A, inserts I, erases E, pieces P, pieces walked W
stats: piece tree: bytes mapped M, bytes loaded L, bytes added A, inserts I, erases E, pieces P, nodes visited V, rotations R, height H
stats: undo: edits E, undos U, redos R, bytes kept B
stats: array: ...                                   lib's Array, from undo's stacks (03.03 on)
```

"bytes moved" is memmove to open or close a hole (array) or to carry bytes
across the gap; "bytes copied" is what moving to a bigger block copied.
The structure counts include undo's own inserts and erases; edit's do not.

### DS_TRACE format (for the stepped figures)

One line per call on stderr, `trace: <structure>: <call>: <cost> | <state>`,
bytes quoted as C would write them (cut with `...` after 40). Real output,
`the cat\n` and `goto 4 / type fat  / goto end / back 4 / paste dog`:

```
trace: flat array: insert 4 "f": moved 4 | "the fcat\n"
trace: flat array: erase 11 1: moved 0 | "the fat cat"
trace: gap buffer: insert 4 "f": moved 4 | "the f" [15] "cat\n"
trace: gap buffer: insert 5 "a": moved 0 | "the fa" [14] "cat\n"
trace: gap buffer: erase 11 1: moved 3 | "the fat cat" [13] ""
trace: piece list: insert 4 "f": walked 1 | orig 0+4 "the " | add 0+1 "f" | orig 4+4 "cat\n"
trace: piece list: insert 5 "a": walked 3 | orig 0+4 "the " | add 0+2 "fa" | orig 4+4 "cat\n"
trace: piece list: insert 8 "dog": walked 2 | orig 0+4 "the " | add 0+7 "fat dog"
trace: piece tree: rotate right at orig 4+4
trace: piece tree: rotate left at orig 0+4
trace: piece tree: insert 4 "f": visited 6 | ((. orig 0+4 "the " .) add 0+1 "f" (. orig 4+4 "cat\n" .))
trace: undo: note insert 4 "fat ": more of the same edit | done 1, undone 0
trace: undo: note erase 8 "cat\n": more of the same edit | done 2, undone 0
trace: undo: undo erase 8 "cat\n": inserted again | done 1, undone 1
```

The gap is `[size]` between the text before and after it. A piece is
`buffer start+length "bytes"`. A tree is `(left piece right)`, `.` for no
subtree; each rotation gets a line of its own before the call's line. (The
last insert of "dog" extends the piece "fat ": its bytes follow at the end
of the add buffer, paste or not.) `DS_CHECK=1` (an @internal test aid in
ptree.c, not shown on the site) checks the whole tree after every change.

## 03.01 An editor, and its text in one array

Regions: `flat_insert`, `flat_erase`, `flat_read`, `flat_open` (lib/flat.c).
Whole: text.h, text.c, flat.h, edit.c, tool.mk, LICENSE, gen.py. No
`--algo` yet (`edit: unknown option '--algo=gap'`).

On a 10x44 terminal, a missing file, then a C file after Down x3, Right, Ctrl-Z:

```
~
~
~  edit -- the text in a flat array
...
new.txt - 0 lines             flat array 1/0
HELP: Ctrl-S = save | Ctrl-Q = quit | Ctrl-F
[cursor 1,1]

#include <stdio.h>

int main(void) {
        printf("hello\n");
        return 0;
}
~
~
f.c - 6 lines                 flat array 4/6
Nothing to undo: this editor keeps no histor
[cursor 4,9]
```

Every insert moves every byte after it. "Hello, " typed at the start of
the book (562404 bytes):

```
$ printf 'goto 0\ntype Hello, \n' | DS_STATS=1 bin/edit --algo=array --replay - data/book.txt
stats: flat array: bytes loaded 562404, inserts 7, erases 0, bytes moved 3936828, grows 1, bytes copied 562404
```

7 x 562404 = 3936828 exactly (the test checks k keys at the start move k*S).
The first insert grows the block, exactly as full as the file, to twice.

Measured, the cost of a key at line 2 against the file's size (the book
repeated; 100 keys, the run with 0 keys taken off):

```
10 MB    0.18-0.19 ms a key   (0.16 in a first run; lesson 03.01 says about 0.2)
100 MB   1.9 ms a key
1 GB     19 ms a key     (the editor on a terminal: 0.10 s for the first key, the
                          grow; then 0.018-0.022 s a key)
```

So on this machine memmove is fast enough that the array is fine for typing
in files up to a few hundred MB; past about 1 GB every key takes longer
than a frame (16.7 ms at 60 Hz), and the array needs twice the file in
memory once it has grown. Where it really stops is typing that goes on in
a big file: `bench/grow.py --input typing` types n/8 keys at line 2 of n
lines:

```
$ python3 bench/grow.py --limit 2 --start 8000 --input typing bin/edit --algo=array --replay
        n       bytes   seconds  ratio
     8000      191033     0.006
    16000      383897     0.017
    32000      768957     0.059
    64000     1566128     0.228    3.8
   128000     3160872     0.892    3.9
   256000     6347574     3.613    4.0
growth: each doubling multiplies the time by about 3.9: about n^2
```

Break it (grow by what is needed, not double): in `flat_insert`, `size_t
cap = 2 * f->cap;` becomes `size_t cap = t->len + n;`. 1000 keys at the end
of the book, where nothing moves:

```
before: stats: flat array: bytes loaded 562404, inserts 1000, erases 0, bytes moved 0, grows 1, bytes copied 562404
after:  stats: flat array: bytes loaded 562404, inserts 1000, erases 0, bytes moved 0, grows 1000, bytes copied 562903500
```

(0.0024 s against 0.0098 s: the counts tell it better than the clock, as in
01.01.)

## 03.02 The gap buffer

Regions: `move_gap`, `grow`, `gap_insert`, `gap_erase`, `gap_read`,
`gap_open` (lib/gap.c). gap.h whole; in edit.c `--algo`, the table of
structures and `editorPickAlgo` are `@from 03.02`. The gap starts after the
text, 16 bytes (GAP_MIN); a full gap doubles the block. `--algo=pieces`:
`edit: no --algo 'pieces' (have: array, gap)`.

The same "Hello, " at the start of the book: the gap crosses the book
once, then nothing moves:

```
stats: gap buffer: bytes loaded 562404, inserts 7, erases 0, bytes moved 562404, grows 0, bytes copied 0
```

Typing in one place (`--input typing`) is about n: 0.042 s for 4096000
lines (104 MB), ratio 1.8. A jump across a 1 GB file moves the gap the
whole way: the first key at line 2 of the 1 GB file costs 0.018 s, the
next ones nothing. Where the gap buffer stops: edits all over the text.
`--input scattered` types n/64 words at random places of n lines:

```
                   array               gap
512000 lines       4.489 s  (3.8)      0.495 s  (3.9)
1024000 lines      -                   2.223 s  (4.5)    about n^2 for both
```

At 1024000 lines (25 MB, 16000 words, 78714 keys): array 16.42 s, bytes
moved 984047158787; gap 2.15 s, bytes moved 134870041711 (the gap goes a
third of the file, on average, at each new place). On 64000 lines (1.5 MB,
1000 words): array moved 3874465988, gap 516246844. The 03.02 test checks
the gap's bytes moved against an exact simulation of where the gap is.

Break it (erase without moving the gap there first): in `gap_erase`,
`size_t moved = move_gap(g, pos);` becomes `size_t moved = 0;`. On "one two
three", `goto 0 / type > / goto 8 / back 1`:

```
before: trace: gap buffer: erase 7 1: moved 6 | ">one tw" [16] " three\n"
        >one tw three
after:  trace: gap buffer: erase 7 1: moved 0 | ">" [16] "ne two three\n"
        >ne two three
```

The byte taken is the one after the gap, wherever the gap is.

## 03.03 Undo and redo: two stacks

Regions: `undo_init`, `undo_note`, `undo_undo`, `undo_redo` (lib/undo.c).
undo.h whole. In edit.c `@from 03.03`: `E.undo`, the `undo_note` calls in
`editorInsertText`/`editorEraseText`, `editorUndo`, the Ctrl-Z/Ctrl-Y cases,
the `typing` flag and `undo_break` after any other key, `undo`/`redo` in the
replay, the help line.

What an edit is: typed keys that go where the last typed one ended are one
edit; a run of Backspaces is one erase (its bytes kept backwards while it
is typed, turned round when undone); any other key, command or a cursor move
ends it. A new edit empties the redo stack. Undo puts the cursor at the
start of an erased insert and after re-inserted bytes; the full-screen
editor scrolls there (`editorGoTo`) if it is off the screen.

```
$ (trace on "the cat\n": goto 4 / type fat  / goto end / back 4 / undo / undo / redo / goto 0 / type > / redo)
trace: undo: note insert 4 "f": a new edit | done 1, undone 0
trace: undo: note insert 4 "fat ": more of the same edit | done 1, undone 0
trace: undo: note erase 11 "\n": a new edit | done 2, undone 0
trace: undo: note erase 8 "cat\n": more of the same edit | done 2, undone 0
trace: undo: undo erase 8 "cat\n": inserted again | done 1, undone 1
trace: undo: undo insert 4 "fat ": erased | done 0, undone 2
trace: undo: redo insert 4 "fat ": inserted again | done 1, undone 1
trace: undo: note insert 0 ">": a new edit | done 2, undone 0
>the fat cat
stats: undo: edits 3, undos 2, redos 1, bytes kept 5
```

(The last redo does nothing: ">" emptied the redo stack.) It works on every
structure through text.h; the test runs random scripts with undo and redo
on all four against the model.

Break it (a new edit keeps the redo stack): delete the two lines at the top
of `undo_note` that pop and forget the undone edits.

```
on "ab\n": goto 2 / type xyz / undo / goto 0 / delete 3 / print / redo / print
before: prints nothing, exit 0 (the redo does nothing)
after:  edit: gap buffer: insert at 2, past the end of 0 bytes      exit 2
on "ab\n": type hello / undo / goto 0 / type > / redo / print
before: >ab
after:  hello>ab
```

The redo puts bytes back at a place in a text that is not there any more.

## 03.04 The piece table: a list of pieces

Regions: `buffers_open`, `buffers_add`, `find`, `pieces_insert`,
`pieces_erase`, `pieces_read`, `pieces_open` (lib/pieces.c). pieces.h
whole. The default stays gap: the list is not better than the gap buffer
for typing (below). `--algo=tree`: `edit: no --algo 'tree' (have: array,
gap, pieces)`.

Opening maps the file (mmap, PROT_READ, MAP_PRIVATE): `bytes mapped
562404, bytes loaded 0` for the book. A pipe, an empty file or anything
mmap refuses is read in (`/dev/stdin` from a pipe: `bytes mapped 0, bytes
loaded 1000`). Measured, open and `goto end` with no edit:

```
              10 MB      100 MB     1 GB
array         0.0044 s   0.0134 s   0.1047 s
gap           0.0050 s   0.0129 s   0.1042 s
pieces        0.0029 s   0.0029 s   0.0084 s
tree          0.0042 s   0.0035 s   0.0081 s
```

On a terminal the difference goes: the editor reads the whole text once to
count its lines, whatever holds it (first screen of the 1 GB file: array
0.303 s, gap 0.315 s, list 0.268 s, tree 0.263 s). grow.py's `--input
opening` is too quick to time for all of them below 100 MB.

Typing in one place makes one piece longer ("Hello, ": pieces 2, walked
13). But Backspace leaves a piece behind: after it, the piece no longer
ends at the end of the add buffer, so the next key starts a new piece.
On `--input typing` (a Backspace run every ten words or so), 256000 lines:
655 corrections, 647 pieces, 10418651 pieces walked; without the
Backspaces, 3 pieces and 92074 walked. So the list is n^2 even on typing:

```
$ python3 bench/grow.py --limit 2 --start 8000 --input typing bin/edit --algo=pieces --replay
  1024000    25441346     0.167    3.9
  2048000    51843745     1.008    6.0
  4096000   104636518     4.258    4.2
```

and on edits all over (`--input scattered`): 0.617 s at 512000 lines, 2.803
s at 1024000 (ratios 6.1, 4.5). At 1024000 lines: 31994 pieces, 622785224
pieces walked, 2.9 to 3.5 s over several runs (3.66 s once; about 5 ns a
piece: the pieces are in no order in memory). On 64000 lines: 2001 pieces, 2459137 walked. Corrections typed in
one place (`type ab / back 1`, repeated): 10000 of them replay in 0.25 s
and a key after them costs 3.8 us; 100000 replay in 25.3 s, 46 us a key
(the walk follows pieces made in order, so here it is under half a ns a
piece). On a terminal each screen reads its rows through the list as well,
a walk for each.

Break it (extend the piece before without checking it ends where the new
bytes start): in `pieces_insert`, `prev->span.buf == ADD &&
prev->span.start + prev->span.len == start` becomes `prev->span.buf ==
ADD`. On "one two", `goto 0 / type abc / goto end / type X / goto 3 / type
Y / print`:

```
before: trace: piece list: insert 3 "Y": walked 2 | add 0+3 "abc" | add 4+1 "Y" | orig 0+8 "one two\n" | add 3+1 "X"
        abcYone two
        X
after:  trace: piece list: insert 3 "Y": walked 2 | add 0+4 "abcX" | orig 0+8 "one two\n" | add 3+1 "X"
        abcXone two
        X
```

The piece grew over the next byte of the add buffer, which is the X.

## 03.05 The pieces in a balanced tree

Regions: `rotate_right`, `rotate_left`, `balance`, `find`, `insert_at`,
`remove_at`, `set_len`, `cut`, `ptree_insert`, `ptree_erase`, `copy`,
`ptree_open` (lib/ptree.c); `remove_min`, `update`, `ptree_read` and the
tree printing come with the file. The default `--algo` becomes tree.

The tree is AVL, and why (also in ptree.c's header): one rule, about
heights, that can be checked at any node by looking at its children, and
one repair, the rotation, used the same way after an insert and after a
removal; a red-black tree (VS Code's piece tree) rotates less but restoring
its colours after a removal is a page of cases; treaps and splay trees are
balanced on average or over many operations, not at each step. Each node
keeps its height and the length of the text under it; finding byte pos goes
down by the left subtree's length. An edit cuts the piece at its start (and
end, for an erase) in two, then adds a node or removes the nodes between.

```
scattered, 64000 lines:   pieces 2001, nodes visited 125113, rotations 1985, height 13
                          (the list: pieces walked 2459137)
scattered, 1024000 lines: pieces 31994, nodes visited 2842400, rotations 29002, height 18;
                          0.018 s (list 2.9-3.5 s, gap 2.15 s, array 16.42 s)
typing, 256000 lines:     pieces 647, nodes visited 560565, height 10 (list: 10418651 walked)
100000 corrections:       0.092 s, 0.5 us a key after them (list: 25.3 s, 46 us)
```

`--input scattered` on the tree: 0.070 s at 4096000 lines (105 MB, 64000
words), ratio 2.1, about n; `--input typing`: 0.036 s at 4096000 lines, too
quick to time.

Break it (a tree that never rotates): `balance()` keeps only `update(n);`
and `return n;`. Pieces added at both ends in turn, the lesson's script on
a 12-byte file:

```
$ printf 'the cat sat\n' > cat.txt
$ python3 -c "import sys; sys.stdout.write('goto end\ntype ab\ngoto 0\ntype >\n' * 6000)" > ends.txt
$ DS_STATS=1 bin/edit --replay ends.txt cat.txt 2>&1 | grep tree
```

and scattered edits of 512000 lines:

```
                 balanced                                   never rotated
both ends        height 14, nodes visited 454880, 0.00 s     height 6001, nodes visited 108030000, 0.58 s
scattered        height 17, nodes visited 1314874, 0.0095 s  height 48, nodes visited 2421026, 0.0111 s
```

(both ends: 12001 pieces either way, and 11974 rotations when balanced.)

The text is the same bytes either way (cmp says so): an unbalanced tree is
still a correct one. Edits at random places keep it shallow by luck; edits
in order (typing at the end, a log file growing) make it a list, which is
what the rotations are for.

## The tests and the timeline

tests/tools/edit.py holds the Model, random and generated scripts, the
replay fixture (`check` runs each structure with DS_STATS=1 against the
model), and a pseudo-terminal Editor with a small VT100 Screen (the kilo
track's, trimmed). 0301-0305 each check their structure against the model
on random edits of the book and of an empty file, the counts for the
lesson's claim, and the full-screen editor on a terminal. Whole run on the
Mac: about 16 s for the five.

check-timeline runs, in its shell at each lesson from 03.01: the replay
(and its errors), each `--algo` there is, the next one as an ordinary
error, undo as an unknown command before 03.03; and the full-screen editor
on an 8x40 terminal through `python3 tests/tools/edit.py drive ROWS COLS
KEYS -- bin/edit ...` (it types the keys and prints the screen), with each
structure: type, Ctrl-S, `cat` the file, then type and Ctrl-Z (undone, or
the "Nothing to undo" message before 03.03). timeline_after replays 300
random edits of the book with every structure against the model.

## Left for later, or worth a sentence

- Lines are found by reading; there is no line index, so "go to line N"
  (only in the replay, `goto LINE:COL`) reads from the start. A piece tree
  can keep newline counts in its nodes, as VS Code's does; not done here.
- The first screen counts all the lines: opening is instant for the piece
  table only without a screen (see 03.04).
- Not built: syntax highlighting (as in the kilo track), multiple cursors,
  a merge of adjacent pieces (VS Code's piece tree does not merge either).
