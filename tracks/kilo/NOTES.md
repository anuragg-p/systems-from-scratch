# Notes for the lesson writers

Everything here was run on the reference code or on the project as the
site shows it at a lesson (`./learn files kilo --at NN.LL`), on an Apple
M-series Mac (macOS, Darwin 25.6, Apple clang 21), and every "break it"
was run as the change it describes. Screens are what the tests' terminal
emulator (Screen in track.py) made of kilo's bytes, rows with trailing
spaces dropped, `[cursor R,C]` counting from 1; in module 06, each run of
one colour is written `[c:text]` (see "06 Syntax highlighting"); in module
07, each underlined run `[_:text]` (see "07 A language server client"). The same tests, the
skeleton check and the timeline check also pass on Linux (Alpine, gcc and
musl, aarch64, in Docker), and every lesson's project builds there with
no warnings. On Linux with glibc (Debian trixie, gcc 14, aarch64, in
Docker) they failed until departure 33, and pass there since, with every
project built without warnings. Module 07 was run the same way on both,
with their clangd (Debian 19.1.7, Alpine 20.1.8; Apple clangd 21.0.0 on
the Mac); the projects at 07.05 to 07.07 did not build on glibc until
lsp.c asked for X/Open (see there). Function names are given instead of
line numbers.

## The upstream, and what this track does with it

antirez/kilo, master at 323d93b29bd89a2cb446de90c4ed4fea1764176e, one file
of 1308 lines, BSD-2-Clause. `tracks/kilo/LICENSE` is its LICENSE, byte
for byte; kilo.c keeps antirez's notice in its header. The finished core's
kilo.c here is 1068 lines with the notes (`./learn files kilo --at 05.02`).

Kept: every function of the editor, with its name and its code, in the
original order. The original formatting is kept where the code is the
same (spacing such as `abAppend(&ab,"\x1b[H",3)`), so a reader can diff.

Cut, as the plan says: the syntax highlighting, whole. That is the
`HL_*` defines, `struct editorSyntax`, `C_HL_extensions`, `C_HL_keywords`,
`HLDB`, `is_separator`, `editorRowHasOpenComment`, `editorUpdateSyntax`,
`editorSyntaxToColor`, `editorSelectSyntaxHighlight`, the `hl`, `hl_oc`
and `idx` fields of erow (`idx` is used only by the highlighter), `E.syntax`,
`struct hlcolor`, the saved-highlight code in `editorFind`
(`FIND_RESTORE_HL`, `saved_hl`, `HL_MATCH`) and the colour switching in
`editorRefreshScreen`. Without the colours, a row is drawn with one
`abAppend` of its visible part instead of a byte at a time. Also cut:
`editorFileWasModified` (never called in the original), the unused
`nonprint` counter in `editorUpdateRow`, and `#include <sys/time.h>`
(nothing uses it).

Module 06, an extension (`optional: true`), puts the highlighting back,
upstream's own code under upstream's names, in the same kilo.c: it arrives
only at its own lessons, and the project at every core lesson is byte for
byte what it was without it. See "06 Syntax highlighting" below. Module
07, another extension, is ours: a language server client in lsp.c and
json.c, which kilo.c calls from a few one-line hooks (see "07 A language
server client"). Module 08, a third, is ours too: undo and redo, in kilo.c
(see "08 Undo and redo"). Module 09, the fourth, is ours too: an API in C
and the real Lua on top of it (see "09 An API, and Lua on top of it").
The finished kilo.c (`./learn files kilo`, every lesson of every path) is
2749 lines (1862 with 06, 07 and 08; 1541 with 06 and 07; 1472 with
module 06 alone); at 05.02 it is 1068, as without any of them.

## Every departure from upstream, and why

Each is marked in kilo.c by a comment that quotes the original. All were
checked by putting the original line back and running it.

1. **main(): raw mode before measuring the window.** The original calls
   `initEditor()` (which measures) before `enableRawMode()`. When the
   kernel does not know the window size (TIOCGWINSZ gives 0 columns),
   kilo asks the terminal with `ESC [ 6 n`; in cooked mode the answer is
   echoed and `read()` waits for an Enter. Verified with the original
   upstream binary and with our code reordered, on a 0x0 pseudo-terminal
   whose "terminal" answers: kilo hangs, and the screen shows
   `ESC [ 6 n` followed by the echoed answer `^[[1;1R`. In our order the
   output is `\x1b[6n\x1b[999C\x1b[999B\x1b[6n\x1b[1;1H` and then the
   size: on a 0x0 pseudo-terminal whose terminal (Screen) is 24x80, 01.03
   prints "This window has 24 rows and 80 columns.", the same as when the
   kernel knows. The second answer is the cell the cursor stopped in, the
   bottom right one, and rows and columns count from 1, so it is the size
   itself; and at 01.03 nothing is taken off yet (the 1, later 2, rows come
   off from 02.01). An earlier version of this note said 25 rows: that was
   wrong, re-run on the project at 01.03.
2. **Tab stops at multiples of 8.** The original pads `while((idx+1) % 8
   != 0)` in `editorUpdateRow` and counts `cx += 7-((cx)%8)` for the
   cursor: its tab stops are columns 7, 15, 23... (from 0), one short of
   every terminal's. Original, on "\tone" and "ab\tc": `       one`,
   `ab     c`. Ours: `        one`, `ab      c`.
3. **"\r\n" files.** The original strips one byte off each line
   (`if`, not `while`), so a "\r\n" line keeps its '\r'. Drawn, the '\r'
   sends the cursor to column 0 and the `ESC [ 0 K` after it erases the
   line: original, on "first\r\nsecond\r\n", the screen shows two empty
   rows. Ours shows them, and a save writes "\n" endings.
4. **Home and End.** The original decodes them in `editorReadKey` but has
   no case for them in `editorProcessKeypress`, so they reach
   `editorInsertChar` and put the low byte of the key code into the text.
   Original, Home and End on "ab", saved: `b'\xed\xeeab\n'`. Ours: a case
   that does nothing.
5. **Joining onto a long row** (`editorDelChar`). The original computes
   `shift = (E.screencols-E.cx)+1`, negative when the row above is wider
   than the screen. Original, Backspace joining "abc" onto 100 x's: the
   cursor is off the right edge, `E.coloff` is negative, and the next
   screen is drawn from before the start of the row. Under
   `-fsanitize=address`: `heap-buffer-overflow ... READ of size 80` in
   `editorRefreshScreen`. Ours: `(E.cx-E.screencols)+1`.
6. **Left at the top of a scrolled screen** (`editorMoveCursor`). The
   original always does `E.cy--`; at the top row of a scrolled view that
   makes `E.cy` -1: the status bar says row 4 but the view does not
   scroll, and two more Ups put `ESC [ -2 ; 25 H` on the wire (not a valid
   sequence; the emulator printed it as text). Ours scrolls up instead,
   as Up does.
7. **Search finds in chars, not render** (`editorFind`). The original
   searches `render` and uses the offset there as a column of `chars`.
   Original, on "\tdelta", Ctrl-F delta Enter: the cursor is at column 16
   instead of 8, and typing X there pads the row with spaces:
   `        delta  X`. Ours: cursor on the 'd', X goes in before it.
8. **Search scrolls a match at the edge** (`editorFind`). The original
   tests `E.cx > E.screencols`; a match at exactly that column leaves the
   cursor one past the edge, and typing then goes in off the screen with
   the view never scrolling. Ours: `>=`, and one more column.
9. **Resize** (`handleSigWinCh`). The original tests `E.cy > E.screenrows`;
   shrinking the window so the cursor's row becomes exactly the status
   bar's leaves it there. Original, cursor on row 11, resized to 12 rows:
   `[cursor 11,1]` on the status bar; two Downs: `[cursor 12,1]`, on the
   message line, "13/40". Ours: `>=` for rows and columns; the cursor
   goes to row 10, and Down scrolls.
10. **The welcome on a narrow screen** (`editorRefreshScreen`). The
    original pads the welcome with `(E.screencols-welcomelen)/2` spaces,
    and `welcomelen` counts the 6 bytes of `ESC [ 0 K` and "\r\n" too: on
    a screen narrower than 33 columns that is negative, and
    `while(padding--)` counts down away from 0, a space at a time. Original,
    and ours before the fix, on 10x30 with an empty file (at 02.01, with
    any file): not one byte reaches the terminal, kilo keeps a CPU busy
    and its memory grows by about 56 MB a second (205 MB after 4 s, then
    killed). Ours: `if (padding < 0) padding = 0;`. With only that, the
    28 columns of text wrap onto the next row of a screen narrower than
    them and the frame scrolls by one (on 10x20: `Kilo editor -- versi`,
    then `on 0.0.1`, and the first `~` gone off the top), so the format
    is also `"%.*s\x1b[0K\r\n"` with the width, which cuts the text: on
    10x20 the row reads `Kilo editor -- vers` (the `ESC [ 0 K` after a
    full row erases its last column, as on any full row; see "The tests
    and the timeline"). At 33 columns and wider the bytes are the
    original's. The 02.01 test runs 32, 30, 20 and 12 columns; with
    either original line back it fails.
11. **The welcome says "version"**, not the original's "verison".
12. **The Makefile** is kilo's (fetched from the same commit: `kilo:
    kilo.c` built with `-Wall -W -pedantic -std=c99`), with a comment on
    top, `rm -f` in clean (the original `rm kilo` fails when there is no
    binary) and a `.PHONY` line.

### In module 06, the syntax highlighting

Each was reproduced on upstream's own kilo.c (built as it is, and with
`-fsanitize=address`) before it was fixed, and each fix was checked by
putting the original line back in our kilo.c and running the module's
tests: every one then fails (the test named in brackets), and passes
again with the fix. Screens in the colour notation of "06 Syntax
highlighting"; upstream's own tab stops show in its screens.

13. **A // comment after a tab** (`editorUpdateSyntax`, 06.03). The
    original marks `row->size-i` bytes, counting `chars` where `hl` and `i`
    follow `render`: after a tab too few, and when the tabs make `i` larger
    than `size`, a negative count that `memset()` takes as a huge one.
    Upstream, a C file with the row "\t// x" kills kilo as it opens it
    (status -5 on macOS; ASan: the memset); "a\t// comment text" shows
    `a      [c:// comment] text`. Ours: `row->rsize-i`. (0603: kilo exits.)
14. **// typed in front of a comment's opening** (`editorUpdateSyntax`,
    06.03). The original `return`s from the // case, before the end of the
    function where the row's comment state is kept and passed on: on
    "/* a", "b", "*/ int x;", typing // at the start of the first row leaves
    `[c:b]` and `[c:*/] [g:int] x;` in the comment's colour. Ours: `break`.
    (0603: "// in front".)
15. **// inside a multi-line comment** (06.03). The original takes // after
    a separator for a // comment wherever it is: in a multi-line comment, a
    row starting with // ended that comment (upstream: "/*", "// old",
    "int y = 2;", "*/" shows `[g:int] y = [r:2];` and a plain `*/`), and a
    */ later on such a row was never seen. Ours: `!in_comment` in the test.
    (0603: row 7, "// old */ z = 3;".)
16. **A comment's opening inside a string** (06.03). The original has no
    `!in_string` before it: `char *open = "/*";` shows
    `[g:char] *open = [m:"][c:/*";]` and every row after it, to the end of
    the file, is comment. (0603: row 9.)
17. **Whether a row ends inside a comment** (`editorRowHasOpenComment`,
    06.03). The original works it out from the row's last character: in
    the comment's colour and not the end of a */. An empty row, or one of
    spaces (left normal), has none, so a blank line inside a comment ended
    it: "/* start", "", "   end */" shows the third row plain. And
    "a = 1; /*/" (opened, then a slash) looks closed: the row after it is
    plain. Ours: the scan's own `in_comment` at the end of the row is kept
    in `hl_oc`, and `editorRowHasOpenComment` returns `hl_oc`. (0603:
    rows 5 and 11.)
18. **A comment opened at the top of a long file** (06.03). The original
    passes a change on with `editorUpdateSyntax(&E.row[row->idx+1])` at the
    end of `editorUpdateSyntax`: one call deeper for every row it reaches.
    Upstream, "/" then "*" typed at the top of 100000 rows of "int x;":
    SIGSEGV (status -11), the stack overflowed; 50000 rows were fine. Ours:
    `row = &E.row[row->idx+1]; goto nextrow;` back to a label at the top,
    with `hl_oc` set first. (0603: the 100000-row file; kilo exits -11.)
19. **`idx` after a row is deleted** (`editorDelRow`, 06.03). The original
    renumbers with `idx++` where it means `idx--`: each row after the
    deleted one claims a place two further down, and its "row above" is
    another row, or past the end of `E.row`. Upstream, "x", "/* a",
    "b */", "c = 1;": Backspace at the start of row 2, then x typed on
    "b */": `bx */` plain. On "a" "b" "c" "d", two joins and a key typed:
    ASan, heap-buffer-overflow READ of size 8 in `editorRowHasOpenComment`.
    (0603: "joined", and under ASan "two joins".)
20. **The row below a deleted row** (`editorDelRow`, 06.03; not in the
    original). After a delete the next row has a new row above it, which
    may end inside a comment where the deleted one did not; nothing
    highlighted it again. Upstream, "a = 1; // note", "/* b", "c = 2;",
    "*/": Backspace at the start of row 2 joins "/* b" into the // comment,
    and `[c:c = 2;]`, `[c:*/]` stay. Ours: `editorUpdateSyntax(E.row+at)`
    after the delete. (0603: "joined onto //".)
21. **A row inserted above the last** (`editorInsertRow`, 06.03). The
    original counts the new row (`E.numrows++`) after `editorUpdateRow()`,
    so while the new row is highlighted the rows end one early and a change
    it passes on stops before the last row. Upstream, "x = 1; // a /* b",
    "c;", "d;", Enter before the "/*": `[c:c;]` but `d;` plain. Ours: the
    count first (an `@else` keeps the core's order before 06.03). (0603:
    "split before the opening".)
22. **A backslash last in a string** (`editorUpdateSyntax`, 06.02). The
    original takes the character after a backslash along without looking:
    at the end of a row it writes `hl[rsize]`, one past `hl`, and the scan
    goes on past the '\0' that ends `render`. Upstream, `char *s = "one \`
    (a C line continuation): nothing shows, but ASan stops it,
    heap-buffer-overflow WRITE of size 1 in `editorUpdateSyntax`. Ours:
    `*p == '\\' && *(p+1)`. (0602, under ASan; on a compiler without ASan
    this one does not show.)
23. **Keywords read past the row** (06.04). The original compares with
    `memcmp(p,keywords[j],klen)`, which may read all `klen` bytes, past the
    end of `render` near the end of a row: ASan (whose memcmp checks the
    whole length, its default) stops upstream on the first C row shorter
    than a keyword after a separator, READ of size 16 from
    `editorUpdateSyntax`. Ours: `strncmp`, which stops at the '\0'. (0604,
    under ASan.)
24. **A byte above 127 drawn as a letter** (`editorRefreshScreen`, 06.01).
    The original tests `c[j] <= 26`; char is signed, so a high byte passes
    and `'@'+c[j]` sends the terminal another control or high byte instead
    of '?'. Upstream, "int caf\xc3\xa9 = 1;" sends 0x03 and 0xe9: the
    emulator shows `caf[#:\xe9]` (one cell for two bytes, the rest of the row
    one column left; a real terminal shows worse). Ours: `(unsigned char)`.
    (0601: row 1.)
25. **The colour after a non-printable character** (06.01). The original
    ends one with ESC [ 0 m, which puts the default colour back, but keeps
    its own idea of the colour set: on `x = "a"` Ctrl-A `"b";` the second
    string is drawn uncoloured, `[m:"a"][M:A]"b";`. Ours: `current_color =
    -1` after it. (0602: row 5.)
26. **The file's name** (`editorSelectSyntaxHighlight`, 06.01). The
    original looks only where the pattern is first: in "my.cool.c" or
    ".config/t.c" the first ".c" is not the end, and the file had no
    colours (checked upstream). Ours: every place it is. (0601: the names.)
27. **"deltype"** in `C_HL_keywords` is a typo for decltype. (0604: row 4.)
28. **The match after a tab** (`editorFind`, 06.05). Not a bug upstream,
    which searches `render`: ours searches `chars` (departure 7), so the
    match's column is a place in `chars`, and `hl` follows `render`. The
    colour goes where the screen shows the match: the tabs before it are
    counted as `editorUpdateRow` counts them. With `match_offset`, on
    "\tchar *s = "beta";" the cells of ` *s ` turn blue. (0605: "after a
    tab".)
29. **ESC [ 39 m only after a colour** (`editorRefreshScreen`, 06.01). The
    original sends it at the end of every row. Ours only when the row left
    a colour set, so a file with no syntax, and any row with no colour, is
    the same bytes as without highlighting: the first screen 00.02 shows
    and its test holds byte for byte stay true of the finished editor.
    (0002 fails with the original line.)
30. **`singleline_comment_start[3]`**, not `[2]`: room for the '\0' of the
    "//" HLDB puts there. Apple clang 21 warns about the original
    (`-Wunterminated-string-initialization`, part of `-W`).
31. **`FIND_RESTORE_HL` indented** with the code around it; the original
    has the `#define` and its `} while (0)` at the left margin, inside
    `editorFind`. Only a layout change: the site reads a "}" at the left
    margin as the end of a function.
32. **Left out**: `struct hlcolor`, which nothing in the original uses.

### Found later, in the core

33. **The resize handler, installed with `sigaction()`** (`initEditor`,
    02.01). The original has `signal(SIGWINCH, handleSigWinCh);`, and what
    `signal()` installs is up to the C library. macOS and musl give it BSD's
    meaning: the handler stays, SIGWINCH is held back while it runs, and a
    `read()` it interrupts is restarted. glibc does that only with
    `_DEFAULT_SOURCE` on, and `-std=c99` turns it off, as does an explicit
    `_POSIX_C_SOURCE` (kilo has both on Linux); then `signal()` is System
    V's: `SA_RESETHAND` and `SA_NODEFER`, no `SA_RESTART` (checked in Debian
    trixie, glibc 2.41, with a small program that asks `sigaction()` what
    `signal()` installed, under each set of options). Original, on glibc:
    the first resize interrupts the `read()` in `editorReadKey`, which fails
    with EINTR (a build that prints errno there: `errno 4 (Interrupted
    system call)`), and `if (nread == -1) exit(1);` ends kilo with status 1,
    the terminal put back. With only that `read()` retried on EINTR, kilo
    lives through the first resize, but the handler is back to the default
    (SIGWINCH gone from SigCgt in /proc) and the second resize is not drawn.
    Ours: `sigaction()` with `SA_RESTART`, an empty mask and no other flag,
    which is what `signal()` already means on macOS and musl, so nothing
    changes there. `SA_RESTART` is right for this handler because it draws
    the frame itself: once it returns, all that is left is to wait for the
    key, which is what the restarted `read()` does. Not taken: a retry on
    EINTR alone (the handler is still reset, and every `read()` and
    `write()` would need one), or `_DEFAULT_SOURCE` (glibc only, and the
    meaning still left to the C library). What the handler calls is as in
    the original: `read()`, `write()` and `time()` are async-signal-safe;
    `realloc()`, `free()` and `snprintf()` (the frame), `ioctl()`, and
    `perror()` and `exit()` (a size that cannot be read) are not on POSIX's
    list (see "Other behaviour of the original, kept"). (0201: "resize 1 of
    3", kilo exits; with only the retry, "resize 2 of 3", no new screen.
    Only on glibc: on macOS and musl the test passes with the original line
    too, and it runs there all the same.)

What the project shows at a lesson (the `@else` parts), not in the
finished file:

- **01.01 to 01.03: no screen yet.** `editorProcessKeypress` reads one
  byte with `read()` until 01.02 brings `editorReadKey`, and until 02.01
  it prints the code of each key, `97 ('a')` or `13`, one per line with
  "\r\n". 01.03 prints the window size once at start. This is ours; the
  original has nothing to show before its screen.
- **02.01 to 03.03: the bottom line stays empty.** `updateWindowSize`
  takes 1 row off, not 2: every row of the frame ends in "\r\n", and a
  "\r\n" on the bottom line scrolls the whole screen up by one (the first
  row of the file would never be seen). From 03.04 the message line,
  which has no "\r\n", is the bottom line, and 2 rows are taken off.
- **The help line** says only the keys that exist: "HELP: Ctrl-Q = quit"
  at 03.04, "+ Ctrl-S = save" from 04.04, "+ Ctrl-F = find" from 05.01.
  The search prompt says "(Use ESC/Enter)" at 05.01 and "(Use
  ESC/Arrows/Enter)" from 05.02.
- **Keys whose lesson is ahead do nothing.** From 04.01 (when any other
  key is inserted as text) Enter, Backspace, Delete, Ctrl-H, Ctrl-S and
  Ctrl-F have cases that just `break` until their lesson fills them in.
  Before 04.01 there is no `default:`, so every key not handled does
  nothing.
- **rowoff, coloff come with 03.01** (they stay 0 until 03.02 moves the
  cursor), and `E.dirty` with 04.01. Before 03.03 a row is drawn from
  `chars`, so tabs go to the terminal raw (see 03.03).
- **Comments name only what is there.** Where the finished comment names
  a later piece, an `@else` holds the earlier wording: the `getline()`
  note above `_POSIX_C_SOURCE` (before 03.01), the comments above
  `updateWindowSize` and in `handleSigWinCh` (no status bar before 03.04),
  the one above `struct erow` (no render before 03.03), and the ones above
  `editorOpen` and on `E.dirty` (no save before 04.04).

## The lessons, and how they divide the code

Same 16 lessons as the plan, in its order; no merges or splits.
Regions (`./learn solution kilo NN.LL` prints them):

| lesson | regions (function: title) |
|---|---|
| 01.01 | disableRawMode: leave raw mode; enableRawMode: enter raw mode |
| 01.02 | editorReadKey: read one key |
| 01.03 | getCursorPosition; getWindowSize; updateWindowSize; initEditor |
| 02.01 | abAppend; abFree; editorRefreshScreen: start the frame, the empty lines and the welcome, end the frame; handleSigWinCh |
| 03.01 | editorInsertRow; editorOpen; editorRefreshScreen: draw a row of the file |
| 03.02 | editorMoveCursor |
| 03.03 | editorUpdateRow; editorRefreshScreen: the cursor, past tabs |
| 03.04 | editorRefreshScreen: the status bar and the message line; editorSetStatusMessage |
| 04.01 | editorRowInsertChar; editorInsertChar |
| 04.02 | editorInsertNewline |
| 04.03 | editorFreeRow; editorDelRow; editorRowAppendString; editorRowDelChar; editorDelChar |
| 04.04 | editorRowsToString; editorSave |
| 05.01 | editorFind: search the rows |
| 05.02 | editorFind: Escape goes back |

Not in regions, arriving with `@from`: `main()` and `editorProcessKeypress`
(plain code from 01.01, a case per lesson), struct erow, the abuf struct,
the page keys (03.02), the quit confirmation (04.04), the arrows in the
search (05.02), most of `editorFind` (it appears with 05.01). 02.01 is the
one place a lesson is bigger than its title: it also brings the SIGWINCH
handler (redraw at the new size), because that handler draws the screen.

## How the project shows a hole

A cut region becomes `kiloTodo("NN.LL", "<title>");` (STUBS in track.py;
kiloTodo is `@internal` in kilo.c). It puts the terminal back, prints
`kilo: NN.LL: <title> not written yet` and exits with status 3. Lessons
never mention it.

## 00 The workbench (labs, no regions)

The workbench describes the editor as the core leaves it, the project at
05.02: its runs are `./learn run kilo --at 05.02 -- file.txt` (files in
`build/at/kilo/05.02/`; without a file, it edits `learn.txt` there), and
its quotes, patches and facts are `at=05.02`. So no extension changes a
workbench lesson. `./learn run kilo` with no `--at` runs the finished
project, every extension in it (`build/at/kilo/finished/`); 00.01 says so
in one sentence where it first runs the editor. xv6's 00.02 does the same
with the last lesson of its core, 07.03.

Measured at 05.02 (macOS): kilo.c is 1068 lines and 30 functions (a line
at the left margin ending in ") {"; the `fact`s check both); one key on a
24x80 screen of kilo.c itself is a 1324-byte frame; on 10x44, the frame
after "!" typed at the end of "world" in hello.txt ("Hello", "world") is
192 bytes; the first screen of "ab\n" on 6x20 is the 108 bytes below.

### 00.01 How a terminal editor works

The loop: `main` = raw mode, measure, open, then forever draw the screen
and process one key. On a 10x44 terminal at 04.04, typing "// done" on a
new last row, then Ctrl-Q, then Ctrl-S:

```
    |#include <stdio.h>
    |
    |int main(void) {
    |        printf("hello\n");
    |        return 0;
    |}
    |// done
    |~
    |f.txt - 7 lines (modified)               7/7
    |WARNING!!! File has unsaved changes. Press C
    [cursor 7,8]
...
    |f.txt - 7 lines                          7/7
    |78 bytes written on disk
```

The message line is cut at the screen's width (44 here).

### 00.02 What the terminal sends and understands

What keys send, as the project at 01.01 prints them (raw mode, one line
per byte read): a `97 ('a')`, Enter `13`, Up `27`, `91 ('[')`, `65 ('A')`,
Backspace `127`, Tab `9`, Ctrl-A `1`, Ctrl-C `3`, Ctrl-Z `26`, Ctrl-S `19`,
Escape `27`. In a cooked terminal, `cat -v` shows Up as `^[[A`: typing a,
Up, b, Enter gives the echo `a^[[Ab` and then cat's copy `a^[[Ab`.

What kilo sends, the whole first screen on a 6x20 terminal with "ab\n"
(the 00.02 test holds it byte for byte):

```
ESC[?25l ESC[H                       hide the cursor, top left
ab ESC[0K \r\n                       a row, erased to the end
~ ESC[0K \r\n  (x3)                  rows past the end of the file
ESC[0K ESC[7m f.txt - 1 lines  1/1 ESC[0m \r\n   status bar, reverse video
ESC[0K HELP: Ctrl-S = save           message, cut to 20 columns
ESC[1;1H ESC[?25h                    cursor to row 1 column 1, shown
```

`printf 'normal \033[7mreverse\033[0m normal\n' | od -An -c` shows the
escapes are plain bytes: `033 [ 7 m`.

## 01 The terminal

### 01.01 Raw mode

Run it (project at 01.01, keys a, Enter, Up, Backspace, Tab, Ctrl-A,
Ctrl-C, Ctrl-Z, Ctrl-S, Escape, 1, then Ctrl-Q):

```
97 ('a')
13
27
91 ('[')
65 ('A')
127
9
1
3
26
19
27
49 ('1')
```

and Ctrl-Q (17) exits with status 0; the shell is normal again. Nothing
typed is echoed. kilo ignores Ctrl-C in its switch, but the byte arrives:
the point is that ISIG is off.

Break it (all verified, on a pseudo-terminal that is kilo's controlling
terminal, as a real one is):

- Delete `atexit(editorAtExit);`: Ctrl-Q exits 0, and the terminal is
  left with ECHO, ICANON, ISIG, ICRNL, IXON and OPOST all off: the shell
  prompt shows no typing and lines stair-step.
- Leave ISIG on: Ctrl-C kills kilo with SIGINT (exit status -2 from
  Python), and the terminal is left raw: a signal death runs no atexit
  handler. So raw mode must also turn the signals off, not just restore.
- Leave IXON on: a, Ctrl-S, b, Ctrl-Q prints `97 ('a')` and `98 ('b')`
  and never 19 or 17: Ctrl-S stopped the output and Ctrl-Q restarted it,
  both swallowed by the terminal. kilo is still running and cannot be
  quit with Ctrl-Q.
- Leave ICRNL on: Enter prints `10`, not `13`.
- Leave OPOST on: harmless here, each "\r\n" goes out as "\r\r\n".
- Print "\n" instead of "\r\n" with OPOST off: the bytes are
  `97 ('a')\n98 ('b')\n`: each line starts below the end of the last.

### 01.02 Reading a key

At 01.02 the same printer shows decoded keys: Up `1002`, Down `1003`,
Right `1001`, Left `1000`, Home `1005`, End `1006`, Page Up `1007`, Page
Down `1008`, Delete `1004`; `ESC O H` and `ESC O F` are Home and End too.
A lone Escape prints `27` after about 0.1 s. Insert (`ESC [ 2 ~`, which
kilo does not know) prints `27`: the switch falls through, the loop reads
on, finds nothing within 0.1 s and returns ESC.

Escape then "[A" typed more than 0.1 s apart are three keys: Escape, '['
and 'A' (the 01.02 test types them into the text).

Break it (verified): VMIN 1 and VTIME 0 (block until a byte): Escape, a,
b, c prints nothing at all: the Escape waits for two more bytes and takes
'a' and 'b' as its sequence, and the next keys go the same way; even
Ctrl-Q is eaten.

### 01.03 The window size

At 01.03, started on a 30x100 terminal, the first line is `This window has
30 rows and 100 columns.` On a terminal whose size the kernel does not
know (0x0), kilo asks: the bytes are `ESC[6n ESC[999C ESC[999B ESC[6n
ESC[1;1H`, the terminal's answers come in on standard input (`ESC [ 1 ; 1
R`, then the bottom right corner), and it prints the answer's size.

Break it: measure before raw mode (the original order): see departure 1.

## 02 The screen

### 02.01 One frame, one write

At 02.01 on 10x44 (no file is read yet; the welcome is on row 9/3 = 3):

```
    |~
    |~
    |~
    |~    Kilo editor -- version 0.0.1
    |~
    |~
    |~
    |~
    |~
    |
    [cursor 1,1]
```

Facts, measured with a `write()` counter (a DYLD_INSERT_LIBRARIES
interposer around kilo at 02.01, 24x80, three Ctrl-L then Ctrl-Q): 4
screens, **4** `write()` calls to standard output, 928 bytes. Break it:
make `abAppend` write each piece straight to standard output: the same
928 bytes take **204** calls, and the terminal can show any of them half
drawn.

Break it (verified, at 04.03): drop the `ESC [ 0 K` after each file row.
On "hello world", six Backspaces at its end: the text is "hello", the
screen still says `hello world`.

Resize: the handler measures again and draws at once. 24x80 resized to
30x100 shows 28 rows of text and a 100-column status bar. `initEditor`
installs it with `sigaction()` and `SA_RESTART` (departure 33).

A window narrower than the welcome (below 33 columns, and at 02.01 with
any file): departure 10. On 10x30 at 02.01 the welcome row is the whole
text from column 1, `Kilo editor -- version 0.0.1`, with no `~`.

Shown at 02.01, the code for the ~ lines and the welcome is indented one
level deeper than the loop around it needs: it sits where 03.01's `if
(filerow >= E.numrows) { ... continue; }` will wrap it, as in the
original. It builds the same; worth a sentence if a reader asks.

## 03 A text viewer

Screens below are at 10x44 on this file (tabs before printf and return):

```
#include <stdio.h>

int main(void) {
	printf("hello\n");
	return 0;
}
```

### 03.01 Rows: opening a file

```
    |#include <stdio.h>
    |
    |int main(void) {
    |        printf("hello\n");
    |        return 0;
    |}
    |~
    |~
    |~
    |
    [cursor 1,1]
```

(The tabs look right here only because the screen under them was empty:
see 03.03.) A missing file opens empty, with the welcome, and is not
created until saved. A line longer than the screen is cut at its edge.
Break it: departure 3 ("\r\n" files).

### 03.02 Moving the cursor, and scrolling

`E.cx, E.cy` are screen positions; the file position is `E.coloff+E.cx`,
`E.rowoff+E.cy`. Scrolling is done inside `editorMoveCursor` itself (no
separate scroll function in kilo). Down can go one row past the end of
the file (the status bar says "5/4" on a 4-line file). Page Down first
puts the cursor on the bottom line, then moves a screenful.

Before 03.03 the cursor on a tab's line is wrong: same keys (down 3,
right 1) at 03.02 put the cursor at `[cursor 4,2]`, at 03.03 `[cursor
4,9]`. And raw tabs leave old characters on the screen: in the timeline
run, after Page Down and Page Up the tab's row reads `line 20 after a
tab`: the tab moved the cursor over "line 20 " without erasing it.

Break it (verified): remove the pull-back at the end of
`editorMoveCursor` (the `if (filecol > rowlen)` block). On "a longer
line" / "ab": ten Rights, Down, X: the row becomes `ab        X`: the
cursor stayed at column 10 on a 2-character row and the insert padded it
with spaces.

### 03.03 Tabs

Cursor after the tab on row 4: `[cursor 4,9]`. Break it: departure 2.

Limit kept from the original: `E.coloff` counts bytes of `chars` but is
applied to `render`, so on a row with a tab, scrolling right is off by
the tab's extra width. On a row of 100 x's then a tab and "end", 101
Rights: the screen shows only x's, "end" never comes into view, and the
cursor is drawn at the right edge.

### 03.04 The status bar and messages

```
    |f.txt - 6 lines                          1/6
    |HELP: Ctrl-Q = quit
```

(rows 9 and 10 of the 10x44 screen). The name is cut to 20 characters;
the message shows for 5 seconds, counted in whole seconds by `time()`, and
goes only when the next key draws the screen (nothing redraws on a
timer).

Break it (verified): delete `E.screenrows -= 2`: the frame is two rows
taller than the screen, so the terminal scrolls: the top two rows of the
file are gone (`line 3` is on the top row of the screen) while kilo
thinks `line 1` is.

## 04 A text editor

### 04.01 Inserting characters

`editorInsertChar` below the end of the file adds empty rows down to the
cursor first (Page Down on a short file then typing fills the gap). Any
byte with no case of its own is text: Ctrl-A, Ctrl-Z and so on go into
the file. A terminal draws nothing for most control characters, so the
cursor (which counts them) drifts right of the text: Ctrl-A then x on
"ab" shows `xab` with the cursor at column 3 and saves `\x01xab`. A BEL
(7) in a file rings on every redraw. (Original behaviour, kept.)

Break it (verified at 04.01, on "abc"): drop `editorUpdateRow(row)` from
`editorRowInsertChar`: typed XYZ does not appear (render is stale, the
screen still says `abc`, with "(modified)" and the cursor at column 4),
but chars holds `XYZabc`: Right goes on to column 7 before it moves to the
next row. There is no save at 04.01 (Ctrl-S does nothing, the file stays
"abc\n"); from 04.04 on, Ctrl-S writes the 7 bytes `XYZabc\n` ("7 bytes
written on disk") while the screen still says `abc`.

### 04.02 Enter: splitting a line

Break it (verified): drop `row = &E.row[filerow];` after
`editorInsertRow` in `editorInsertNewline`. `editorInsertRow` reallocs
`E.row`, so `row` points into freed memory: Enter in the middle of a row
kills kilo with SIGSEGV (exit -11). Under `-fsanitize=address`:
`heap-use-after-free ... READ of size 8` in `editorInsertNewline`, freed
by the `realloc` in `editorInsertRow`.

### 04.03 Deleting, and joining lines

In kilo, Delete and Ctrl-H do exactly what Backspace does: delete the
character left of the cursor (original behaviour, kept). Break it:
departure 5 (the join shift).

`editorRowDelChar` calls `editorUpdateRow` before `row->size--`, so the
row is rendered once with its '\0' counted; `editorDelChar` renders it
again right after, so nothing shows. Original order, kept.

### 04.04 Saving

One `open(O_RDWR|O_CREAT, 0644)`, `ftruncate` to the new length, one
`write`. Not atomic: a crash between the truncate and the write leaves a
short file (the original's comment says as much). Messages: `78 bytes
written on disk`; `Can't save! I/O error: No such file or directory`.

Break it (verified): drop the `ftruncate`: "a long first line" cut to
"a long" and saved: the file is `a long\nfirst line\n`: the old tail
stays after the new text.

Quit: with unsaved changes Ctrl-Q says `WARNING!!! File has unsaved
changes. Press Ctrl-Q 3 more times to quit.`, then 2, then 1; the fourth
press quits. Any other key resets the count (`quit_times` is reset at
the end of every other key).

## 05 Search

### 05.01 Find as you type

`editorFind` is its own little event loop: set the prompt, draw, read a
key, search. A match puts its row at the top of the screen (`E.rowoff =
current, E.cy = 0`). On the 10x44 file, Ctrl-F "ret":

```
    |        return 0;
    |}
    |~
    ...
    |f.txt - 6 lines                          5/6
    |Search: ret (Use ESC/Arrows/Enter)
    [cursor 1,9]
```

A query with no match leaves the view where the last match put it.
Break it: departure 7.

Also verified at 05.01: delete `if (last_match == -1) find_next = 1;`
and typing never searches (find_next stays 0): on "one alpha / two /
three beta", Ctrl-F beta leaves the view at the top.

### 05.02 Next match, previous match, and going back

`find_next` +1 or -1 makes the same loop continue from `last_match`,
wrapping at either end. Escape restores `cx, cy, coloff, rowoff` saved
before the search.

Break it (verified): delete `E.coloff = saved_coloff; E.rowoff =
saved_rowoff;` from the Escape case, so only the cursor goes back. The
build warns `unused variable 'saved_coloff'` (and `saved_rowoff`). On 30
numbered lines at 10x44: Page Down twice, Ctrl-F, "line 2", Down, Up, Up,
Escape: the cursor is back on screen row 8, but the view is where the
last match left it (`line 29` on the top row), so the cursor is on file
row 36 of 30 ("36/30"); typing X adds empty rows down to it, and the file
has 36 lines.

Limit kept from the original: `isprint(c)` is called on key codes above
255 (Home, End and the like) in the search prompt, which C leaves
undefined; on macOS it returns 0 for all of 1000 to 1008 (checked).

## 06 Syntax highlighting (an extension)

Module 06 (`lessons/06-highlighting/`, `optional: true`) is upstream's
highlighting: the `HL_*` classes, `struct editorSyntax`, `HLDB` with its C
stanza, `is_separator`, `editorRowHasOpenComment`, `editorUpdateSyntax`,
`editorSyntaxToColor`, `editorSelectSyntaxHighlight`, the `idx`, `hl` and
`hl_oc` fields of erow, `E.syntax`, the drawing a byte at a time in its
colour, and the coloured match in `editorFind`; upstream's names, its order
in the file, and its code but for departures 13 to 32. At a lesson of the
module the project is the whole core plus the module's lessons so far
(`./learn files kilo --at 06.03`); at every core lesson, and at any lesson
of another extension, none of it is there (checked: the project at each of
the 16 core lessons written with `./learn files` before the module existed
and after, compared with `diff -r`: identical).

The finished project (`build/at/kilo/finished/`, every lesson of every
path) does include it. The workbench lessons do not run that one but the
core's, at 05.02 ("00 The workbench" above), so nothing in them changes
with this module, or with module 07. For a file with no syntax the
finished editor draws the same bytes as the core all the same (departure
29). At first 00.01 stated the finished file's numbers, and they changed
with this module (1472 lines, 35 functions, 1542 bytes a key on kilo.c,
its first rows a comment, now cyan, against the core's 1068, 30 and
1324): that was the wrong dependency, and why the workbench now stays at
05.02.

### How the screens below were captured

With a scratch driver around track.py's own `Editor` and `Screen`: the
project at the lesson (`./learn files kilo --at 06.LL`, built with make)
run on a 10x44 pseudo-terminal on this `hello.c` (a tab before printf and
return), keys typed, then each row printed with `Editor.painted()`, which
is what the relay's `colors` prints too:

```
#include <stdio.h>

/* Say hello
   and go. */
int main(void) {
	printf("hello %d\n", 42);  // once
	return 0;
}
```

In a painted row, text in the default colour is as it is, and a run in a
colour is `[x:text]`: r red (ESC [ 31 m), g green (32), y yellow (33),
b blue (34), m magenta (35), c cyan (36); `#` is reverse video in the
default colour, a capital letter reverse video in that colour. Leading
white space is left in the default colour (the scan skips it), so a
comment's indentation shows uncoloured.

### The lessons, and how they divide the code

Five lessons, the plan's but for one move: the syntax database and the
choice by file name come with 06.01, not 06.04. Upstream's
`editorUpdateSyntax` begins `if (E.syntax == NULL) return;` and every
rule after that reads its comment marks or keywords from `E.syntax`: with
no syntax chosen there is not one colour to show, so the choice has to
come first. 06.04 is "Keywords" alone. HLDB's stanza and struct
editorSyntax grow a field per lesson (the comment marks with 06.03, the
keywords with 06.04, the flags with 06.02), each line of the initializer
marked with its lesson.

| lesson | regions (function: title) |
|---|---|
| 06.01 | editorUpdateSyntax: a class for every character, non-printable characters; editorSyntaxToColor: the colour of a class; editorSelectSyntaxHighlight: a syntax chosen by the file's name |
| 06.02 | is_separator: where a word ends; editorUpdateSyntax: strings, numbers |
| 06.03 | editorRowHasOpenComment: does the row end inside a comment; editorUpdateSyntax: comments, the comment goes on to the next row |
| 06.04 | editorUpdateSyntax: keywords |
| 06.05 | editorFind: put the colours back (the `FIND_RESTORE_HL` macro; its stub is `#define FIND_RESTORE_HL kiloTodo(...)`) |

Not in regions, arriving with `@from`: the `HL_*` defines (each with its
lesson), `HL_HIGHLIGHT_*` (06.02), struct editorSyntax and its fields,
`C_HL_extensions`, `HLDB` and `HLDB_ENTRIES` (06.01), `C_HL_keywords`
(06.04), the erow fields (`hl` 06.01, `idx` and `hl_oc` 06.03),
`E.syntax`, the declarations and the loop of `editorUpdateSyntax` around
its regions, the cases of `editorSyntaxToColor` (each with its class), and
these hooks in core code, each small and marked:

- `editorUpdateRow` ends by calling `editorUpdateSyntax(row)` (06.01).
- `editorInsertRow`: `hl = NULL` (06.01); `idx`, `hl_oc`, the renumbering
  of the rows below, and the count before the update (06.03, departure 21).
- `editorFreeRow` frees `hl` (06.01); `editorDelRow` renumbers `idx` and
  highlights the row that moved up (06.03, departures 19 and 20).
- `editorRefreshScreen`: a row is drawn a byte at a time in its colour
  (06.01), inside the core's 03.01 region "draw a row of the file", whose
  one `abAppend` it replaces through an `@else`.
- `editorFind`: the saved colours, `FIND_RESTORE_HL` before each new match
  and on Escape and Enter, and the match coloured in its row (06.05),
  inside the 05.01 region "search the rows".
- `initEditor` sets `E.syntax = NULL`; `main` calls
  `editorSelectSyntaxHighlight(argv[1])` before `editorOpen` (06.01).
- The header comment of kilo.c says the highlighting is in, from 06.01
  (an `@else` keeps the core's sentence).

Nothing else in kilo depends on any of it: take module 06 away and the
core is as it was (module 07 never sees it either: its lessons are the
core plus its own).

### 06.01 A colour for every character

`hl` beside `render`, one class per byte of render, made in
`editorUpdateSyntax` (all `HL_NORMAL`, and done, when the file has no
syntax), freed with the row. `editorSelectSyntaxHighlight` picks the
syntax from the name once, before the file is read: ".c", ".h", ".cpp",
".hpp", ".cc" at the end of the name. The scan at this lesson only marks
what `isprint()` says no to as `HL_NONPRINT`; drawn, that is a letter
(Ctrl-A as A, `'@'+c`) for 1 to 26 and '?' for anything else, in reverse
video, one cell per byte, so the cursor stays on its character.
`editorSyntaxToColor` is a switch with only its default (37) at this
lesson; each class adds its case.

The screen of hello.c at 06.01 is the core's, text and bytes: nothing is
coloured yet (294 bytes for the first screen at 10x44, at 05.02 and at
06.01, for hello.c and for the same text as hello.txt). Ctrl-A typed
between x and y on "ab": in a.c `x[#:A]yab` (cursor 1,4), in a.txt `xyab`
(the terminal draws nothing for the byte 1; cursor 1,4 still, past an
invisible character). A file holding ESC [ H red shows `[#:?][Hred` in a
.c file; in a .txt file the ESC goes to the terminal as it is, as in the
core.

Break it (verified at 06.01): fill `hl` with `HL_NONPRINT` instead of
`HL_NORMAL`: every row of hello.c is reverse-video question marks,
`[#:??????????????????]`, the blank row blank. Delete `if (E.syntax ==
NULL) return;`: at 06.01 a .txt file is scanned too and Ctrl-A shows as
`x[#:A]yab` there (and at 06.02 the same: strings and numbers read nothing
from the syntax); from 06.03 on, where the comment marks are read from
`E.syntax`, the same deletion kills kilo on any .txt file with SIGSEGV
(checked at 06.02, 06.03 and 06.04).

### 06.02 Numbers and strings

`is_separator`: white space, '\0' and `, . ( ) + - / * = ~ % [ ] ;`.
`prev_sep` says whether a word may start at p. A digit after a separator,
or a digit or '.' right after a number, is `HL_NUMBER`; a quote opens a
string to the same quote, a backslash taking the next character along
(not past the end of the row: departure 22). `HL_HIGHLIGHT_STRINGS` and
`HL_HIGHLIGHT_NUMBERS` are set in HLDB's flags but nothing reads them, in
upstream as here: strings and numbers are coloured in every syntax.

hello.c at 06.02:

```
    |#include <stdio.h>
    |
    |/* Say hello
    |   and go. */
    |int main(void) {
    |        printf([m:"hello %d\n"], [r:42]);  // once
    |        return [r:0];
    |}
```

(The comment and the keywords are plain until 06.03 and 06.04.) More, from
the 0602 test: `x = [r:12.5] + y3 - [r:7];`, `s = [m:"say \"hi\""] +
[m:'q'];`, an unterminated `t = [m:"no end]` with `after = [r:1];` plain
on the row below, `w = ([r:8])+[[r:9]];`.

Break it (verified at 06.02): drop `|| row->hl[i-1] == HL_NUMBER` from the
number test: only a number's first digit is red, `[r:4]2`, `[r:3.]14`,
`[r:1]000` (the '.' still goes on from the 3). Delete the backslash case
in the string: `s = "say \"hi\" now";` shows `s = [m:"say \"]hi\[m:" now"];`,
the escaped quote ending the string.

### 06.03 Comments, on one line and across many

// after a separator, outside a multi-line comment, makes the rest of the
row `HL_COMMENT` and ends the scan; /* opens `HL_MLCOMMENT` up to and
including its */, outside a string. Whether the row ends inside one is
the scan's `in_comment` at the end, kept in `hl_oc`;
`editorRowHasOpenComment` returns it, and the next row starts from its
row above's. When it changes, the next row is highlighted again, and so on
down while it keeps changing, as a loop (departure 18). Rows find their
neighbours by `idx`, kept right through inserts and deletes.

hello.c at 06.03:

```
    |#include <stdio.h>
    |
    |[c:/* Say hello]
    |   [c:and go. */]
    |int main(void) {
    |        printf([m:"hello %d\n"], [r:42]);  [c:// once]
    |        return [r:0];
    |}
```

From the 0603 test: `        [c:// x]` (a tab, then a short comment: the
row that crashes upstream), a blank row inside a comment and
`   [c:end */] y = [r:2];` after it, `[c:// old */] z = [r:3];` inside a
comment (the */ closes it), `s = [m:"/*"];`.

Break it (verified at 06.03): delete the block that goes on to the next
row (`if (row->hl_oc != oc ...) { ... goto nextrow; }`; the build warns
`unused label 'nextrow'`): on "int x = 1;", "int y = 2;", "*/ int z;",
typing /* at the top colours only that row, `[c:/*int x = 1;]`,
`int y = [r:2];`, `*/ int z;`; a row below changes only when it is itself
edited (x typed on row 2: `[c:inxt y = 2;]`). As it is:
`[c:int y = 2;]`, `[c:*/] int z;`. Make `editorRowHasOpenComment` return
0: a comment ends with its first row, `[c:/* Say hello]` then
`   and go. */` plain.

A long file: 100000 rows of "x;", /* typed at the top, every row below
highlighted again: the screen comes back in well under a tenth of a
second (macOS, M-series; upstream overflows its stack here, departure 18).

### 06.04 Keywords

After a separator, each word of `C_HL_keywords` that is here with a
separator after it: `HL_KEYWORD1` (yellow), or `HL_KEYWORD2` (green) for
the ones ending in '|', the types. hello.c at 06.04:

```
    |#include <stdio.h>
    |
    |[c:/* Say hello]
    |   [c:and go. */]
    |[g:int] main([g:void]) {
    |        printf([m:"hello %d\n"], [r:42]);  [c:// once]
    |        [y:return] [r:0];
    |}
```

384 bytes for that first screen (294 without colours): `ESC [ 36 m` before
the comment, `ESC [ 39 m` after it, and so on, once per run. From the 0604
test: `integer = iffy + intx;` plain, `[y:decltype](x) y = [y:NULL];`,
`static_cast<int>(c)` plain ('<' is no separator), "x = s" with "witch"
typed: `x = [y:switch]`, then y: `x = switchy`.

Break it (verified at 06.04): drop `is_separator(*(p+klen))`: the start of
a longer word is coloured, `[g:int]eger = [g:int]erval + [y:if]fy;`,
`[y:return]ed = [r:1];`.

### 06.05 Showing the match

A match is coloured `HL_MATCH` (blue) in its row's `hl`; the colours it
covers are saved first (`saved_hl`, `saved_hl_line`) and `FIND_RESTORE_HL`
puts them back before the next match is coloured and when the search ends,
by Escape or Enter. It works in a file with no syntax too: `hl` is there,
all normal. Ctrl-F hello on hello.c at 06.05:

```
    |[c:/* Say ][b:hello]
    |   [c:and go. */]
    |[g:int] main([g:void]) {
    |        printf([m:"hello %d\n"], [r:42]);  [c:// once]
    |        [y:return] [r:0];
    |}
    |~
    |~
    |hello.c - 8 lines                        3/8
    |Search: hello (Use ESC/Arrows/Enter)
```

(the status bar is `[#:...]`, reverse video). Escape: the first screen of
06.04 again. Only the first match in a row is coloured.

Break it (verified at 06.05): delete `FIND_RESTORE_HL;` from the
Escape/Enter case: Ctrl-F 42, Escape, and `[b:42]` stays blue after the
search (`printf([m:"hello %d\n"], [b:42]);`) until the row is edited, and
a second search, Ctrl-F return Enter, leaves `[b:return]` blue as well.
Delete the one before the next match is coloured: Ctrl-F hello, Down,
Escape leaves
`#include <stdio.[b:h]>` (the match of "h", the first key typed) and
`[c:/* Say ][b:hello]` blue, and the saved colours of each are lost
(nothing frees them).

### Kept from the original

- Only a file with a syntax is highlighted, non-printable characters
  included: in a .txt file control bytes go to the terminal as in the
  core. And inside a string or a comment they go as they are too (the
  string and comment cases come before the non-printable one).
- The white space at the start of a row is skipped and left in the
  default colour: a form feed or vertical tab there goes to the terminal.
- The separators are only white space and `, . ( ) + - / * = ~ % [ ] ;`:
  in `i<10`, `{0}`, `x?1:2` the number is plain, `static_cast<int>` is no
  keyword, and `"a"// b` is no comment (after a string `prev_sep` is 0).
- Numbers: `0x1F` colours only the 0; `3.14.15` is one number; `.5` only
  its 5.
- A string does not go on past the end of its row (a backslash-newline in
  C does).
- A '\0' in a row ends the scan; the rest of the row stays normal.
- The reverse-video letter of a non-printable character takes the colour
  of the run before it (`[m:"a"][M:A]` in departure 25's example).
- `isprint()`, `isspace()`, `isdigit()` get a plain `char`, negative for a
  byte above 127, which C leaves undefined: macOS (checked for every value
  from -128 to -1), glibc and musl all say no, so such a byte is
  `HL_NONPRINT` outside strings and comments.
- `realloc(row->hl,0)` for an empty row may give NULL (glibc frees); the
  search checks `row->hl`, as upstream does.

## 07 A language server client (an extension)

Module 07 (`lessons/07-language-server/`, `optional: true`, started
2026-11-24 on the owner's word) is ours, not upstream's: a client for a
language server, clangd for C, in files of its own. At a lesson of the
module the project is the whole core plus the module's lessons so far;
module 06 is never in it, and module 07 is in no core lesson and no 06
lesson (checked: the projects at all 21 lessons written with `./learn
files` before the module existed and after, compared with `diff -r`:
identical). The finished project has both: its kilo.c is 1541 lines (1472
with 06 alone; 1068 at 05.02, as always).

The design (files, hooks, the editor's side, messages, limits) was fixed by
the coordinator before the code was written; where the code departs from
it, "Departures from the design" below says where and why.

### The files

| file | lines in tracks/ (markers and instructions in) | what it is |
|---|---|---|
| lsp.h | 51 | what kilo.c calls (lspStart, lspPump until 07.04, lspWaitKey, lspDrawRow, lspDefinition, lspBack) and what lsp.c calls in kilo.c (editorSetStatusMessage, editorRefreshScreen, editorRowsToString, abAppend, editorCursor, editorJump); `struct abuf;` as an incomplete type |
| lsp.c | 1524 | the client: the server table, starting and stopping, frames, the session, poll(), diagnostics, definitions |
| json.h | 60 | the JSON tree (`struct json`), the reader's and getters' prototypes, jsonQuote |
| json.c | 424 | the reader (recursive descent, depth cap) and the one writer helper; knows nothing of kilo or LSP |
| Makefile | | from 07.01 `kilo.c lsp.c`, from 07.02 `kilo.c lsp.c json.c`, same flags |

The project at each lesson (lines, `./learn files kilo --at 07.LL`):

| lesson | kilo.c | lsp.c | lsp.h | json.c | json.h |
|---|---|---|---|---|---|
| 07.01 | 1070 | 248 | 15 | - | - |
| 07.02 | 1071 | 513 | 17 | 59 | 14 |
| 07.03 | 1071 | 553 | 17 | 370 | 49 |
| 07.04 | 1071 | 587 | 17 | 370 | 49 |
| 07.05 | 1071 | 809 | 18 | 370 | 49 |
| 07.06 | 1085 | 1092 | 28 | 370 | 49 |
| 07.07 | 1137 | 1240 | 31 | 370 | 49 |

lsp.c in order: the limits; the servers (`struct lspServer`, `LSPDB` with a
C stanza and a C++ stanza, `lspServerFor`); the state (`struct lspBuf`,
`struct lspDiag`, `struct lspState L`, a block of prototypes); `lspNow`,
`lspSay`, the buffer helpers and `lspFormat`; starting and stopping
(`lspSpawn`, `lspEnd`, `lspGone`, `lspKill`, `lspStart`, `lspStop`);
messages (`lspHeaderLine`, `lspFrame`, `lspFlush`, `lspSend`,
`lspRequest`, `lspNotify`, `lspHandle`, `lspRead`, `lspPump`,
`lspInitialize`, `lspInitialized`); keys and the server (`lspWaitKey`);
the text on the server (`lspAbsolute`, `lspUri`, `lspOpen`,
`lspSendChange`, `lspSendText`, `lspPause`, `lspNotFound`,
`lspWaitServer`); diagnostics (`lspLine`, `lspCharLen`, `lspColumn`,
`lspSetDiagnostics`, `lspPath`, `lspSameFile`, `lspDiagnostics`,
`lspShowDiagnostic`, `lspDrawRow`); definitions (`lspUnits`, `lspSwitch`,
`lspGoTo`, `lspDefinition`, `lspDefinitionResult`, `lspBack`). Everything
but the six kilo.c calls is static. json.c: `jsonSpace`, `jsonNew`,
`jsonUtf8`, `jsonHex4`, `jsonString`, `jsonNumber`, `jsonList`,
`jsonValue`, `jsonParse`, `jsonFree`, `jsonGet`, `jsonIs`, `jsonInt`,
`jsonStr`, `jsonQuote`.

### The lessons, and how they divide the code

The plan's seven, in its order. Two titles changed to fit the code: 07.01
"fork, exec and three pipes" (the third brings back execvp's errno), and
07.05 "didOpen and didChange" (initialize is sent at 07.02; 07.05 brings
initialized, didOpen, didChange, the replies to the server's requests and
shutdown/exit). Regions (`./learn solution kilo 07.LL`):

| lesson | regions (file: title) |
|---|---|
| 07.01 | lsp.c: a server chosen by the file's name; fork, exec and the pipes; stop the server (lspEnd); start the server; at exit (lspStop) |
| 07.02 | json.c: quote a string; lsp.c: take a message off the input (lspFrame); write what the pipe takes (lspFlush); write a message (lspSend); read what the server wrote (lspRead); send initialize |
| 07.03 | json.c: a string; a number; arrays and objects; one value; the whole message; free a tree; the getters; lsp.c: the server is ready (lspInitialized) |
| 07.04 | lsp.c: a server that does not read (in lspSend); the keyboard and the server at once (lspWaitKey) |
| 07.05 | lsp.c: shutdown, then exit (in lspStop); tell the server what is open (in lspInitialized); a path as a URI; open the file on the server; a newer change replaces one still waiting; send the text, if it changed; answer the server's requests |
| 07.06 | kilo.c: where the cursor is (editorCursor); lsp.c: a line of the copy; from the server's columns to bytes; a URI as a path; the server's diagnostics; the diagnostic under the cursor; underline the diagnostics (lspDrawRow) |
| 07.07 | kilo.c: read another file in place of this one; move the cursor there (both editorJump); lsp.c: from bytes to the server's columns; another file (lspSwitch); jump (lspGoTo); ask for the definition; where it is; back |

Not in regions, arriving with `@from`: the limits, each with its lesson;
the state's fields, by lesson; `lspSay`, `lspNow`, the buffer helpers and
`lspFormat` (07.01, 07.02); `lspHeaderLine`, `lspRequest`, `lspGone`,
`lspKill`, `lspPump`, `lspHandle` (07.02; lspHandle is an `@else` at 07.02,
which says "lsp: N bytes from NAME: " and the first 50 bytes of the body,
and the JSON dispatch from 07.03, a line per lesson after); `lspNotify`,
`lspAbsolute`, `lspPause`, `lspWaitServer` (07.05); `lspCharLen`,
`lspSetDiagnostics`, `lspSameFile` (07.06); the initialize params, a line
of the capabilities per lesson (`{}` at 07.02, `textDocument.synchronization`
from 07.05, `general.positionEncodings` and `publishDiagnostics` from 07.06,
`definition` from 07.07); in lspWaitKey the pause (07.05) and the line
that cancels a jump (07.07); the ready line's key help (07.07); the Linux
feature macro (`_POSIX_C_SOURCE 200809L`, then `_XOPEN_SOURCE 700` from
07.05, for realpath()).

### Hooks in core code

Each is one marked line or a small marked block; none is inside module
06's blocks.

- `#include "lsp.h"` with the other includes (07.01).
- `main`: `lspStart(argv[1]);` after the HELP message, before the loop
  (07.01).
- `editorReadKey` (inside 01.02's region): at 07.02 and 07.03 the core's
  `while ((nread = read(fd,&c,1)) == 0);` becomes `while (...) lspPump();`
  (a nested `@from 07.02` / `@from 07.04` with `@else` parts); from 07.04
  the core's line is back as it was, with `lspWaitKey(fd);` before it.
- `editorRefreshScreen` (inside 03.01's "draw a row of the file"):
  `lspDrawRow(&ab,filerow,r->chars,r->size,r->render,r->rsize,
  E.coloff,E.screencols);` after the row's `ESC [ 0 K` and before its
  "\r\n" (07.06). It is outside 06's blocks, so it is the same two lines on
  core + 07 and in the finished file; core and core + 06 are unchanged
  (the diff above).
- `enum KEY_ACTION`: `CTRL_B = 2`, `CTRL_G = 7` (07.07, one-line markers).
- `editorProcessKeypress`: `case CTRL_G: lspDefinition();` and
  `case CTRL_B: lspBack();` after Ctrl-F's case (07.07).
- A section "The editor's side of the language client" just above
  `main()`: `editorCursor` (07.06) and `editorJump` (07.07), the two things
  lsp.c needs of E. editorJump frees every row itself and calls
  `editorOpen` (which, called a second time, frees and replaces
  E.filename and sets E.dirty to 0, but exits on a file it cannot read:
  editorJump tries `fopen` first).

There is no hook in the edit functions, editorSave, editorAtExit or the
status bar: the text goes to the server at the pause, by comparing
`editorRowsToString()` with the copy; atexit(lspStop) is registered by
lspStart. atexit runs its functions last registered first, so lspStop
runs before editorAtExit puts the terminal back: at most LSP_STOP_MS
(500 ms) later. Measured, Ctrl-Q to kilo's exit, 5 runs each: a server
that never reads, 0.504 to 0.510 s (killed); one that answered initialize
and then stops reading (its shutdown never answered), 0.502 to 0.503 s;
the scripted server answering shutdown, 0.013 s; clangd 21, 0.026 s.

### Limits and timeouts

| name | value | why |
|---|---|---|
| LSP_STOP_MS | 500 ms | at exit: shutdown, its answer, exit and the process's end must fit, then SIGKILL; the terminal waits for it |
| (lspGone) | 100 ms | a server that closed its output is exiting; one that has not after 100 ms is killed |
| LSP_HEADER_MAX | 4096 bytes | a header that long without its empty line is not a header |
| LSP_BODY_MAX | 16 MB | a Content-Length over it is absurd; exactly 16 MB is read (0702) |
| LSP_READ_MAX | 1 MB | read from the server in one lspRead, so a flood cannot hold the keys |
| LSP_QUEUE_MAX | 8 MB | waiting for a server before a new message is queued: it is not reading |
| LSP_PAUSE_MS | 300 ms | no key this long: the keys have paused; send the text, show the row's diagnostic |
| LSP_DIAG_MAX | 1000 | diagnostics kept for the file (all are counted) |
| JSON_MAX_DEPTH | 64 | nesting; the reader recurses once a level |
| JSON_MAX_VALUES | 1000000 | values in one message: a 16 MB array of zeros would be about 450 MB of nodes |
| numbers | 63 characters | copied to a buffer for strtod(); longer is an error |
| the message | 79 bytes | lspSay's buffer, then the screen's width |

### Departures from the design, and why

- **lspDrawRow takes chars and size too** (eight arguments). Diagnostics
  are byte columns of chars; turning them into columns of render needs the
  tabs, which render no longer shows. Its signature is the only one in the
  track that takes two lines, so its opening brace is on a line of its own
  at column 0: the site finds the function around a region by the nearest
  column-0 line above it that ends in "{", and the signature's indented
  second line is not one.
- **ESC [ n C counts cells, not render columns.** n is the bytes of render
  before the range less the UTF-8 continuation bytes (0x80 to 0xBF): on
  `printf("e-acute t e-acute: %d\n", totl);` totl is at render column 30
  and cell 28, and `ESC [ 28 C` lands on it on a real terminal (and in
  Screen with utf8=True); `ESC [ 30 C` would draw "totl" two cells right,
  over ");". A character two cells wide (CJK, emoji) still counts as one,
  so the underline lands a cell left per such character before it.
- **KILO_LSP set and empty means no server**, nothing said. The design
  said only what a non-empty value does. The tests of the core and of 06
  run the finished editor on .c files; they set KILO_LSP= so none of them
  starts clangd (edit(..., lsp=None), the default).
- **Two stanzas, C and C++**, both clangd, so languageId is "c" or "cpp".
- **Ctrl-G with no server at all says "lsp: no server"**; "lsp: not ready"
  is for a server that has not answered initialize.
- **editorJump says "Unsaved changes: save first (Ctrl-S), then try
  again"**, not "... then Ctrl-G again": Ctrl-B goes through it too.
- **The version in the ready line** is the first word of serverInfo.version
  that starts with a digit ("Apple clangd version 21.0.0 (...)" gives
  "21.0.0"), else its first word.
- **07.02 says "lsp: N bytes from NAME: ..." and the body's first 50
  bytes**, not "reply to request 1": without a JSON reader the id cannot be
  read.
- **The output queue starts at 07.02.** The pipe is non-blocking from
  07.01, so even initialize may be written in part; 07.02 queues and writes
  what the pipe takes, 07.04 adds POLLOUT and the 8 MB bound, 07.05 the
  didChange replacement. **lspPump stays** after 07.04: lspWaitKey calls it
  when poll() wakes; only the read every 0.1 s goes.
- **The 8 MB bound is checked before a new message is queued**, so one
  large didOpen is allowed; the didChange replacement never adds to the
  queue.
- Added for safety: SIGWINCH is held back while the diagnostics list
  changes (the resize handler draws rows); every function that talks to
  the server returns at once when none is running (see "Found on the way",
  the first). And SIGWINCH is held back across fork() (07.01, below).

Two rules of the design changed after the first review, and are the
design now:

- **The message line when a list arrives** (07.06): if the cursor's row
  has a diagnostic, it is said ("6: error: ..."), the one under the
  cursor or the row's first, and not the counts; otherwise the counts,
  only when they differ from the ones last said. Either way the counts are
  noted as said, so a later list with the same counts says nothing. The
  pause still says the diagnostic of the row the cursor has come to. With
  clangd a list comes about 60 ms after the pause that sent the change; so
  an error typed where the cursor is is said at once, with no other key.
- **SIGWINCH across fork()** (07.01): see there.

### How the screens below were captured

With a scratch driver around track.py's `Editor` (no changes to the
track): the project at the lesson (`./learn files kilo --at 07.LL`, built
with make), on a 12x72 pseudo-terminal, KILO_LSP not set (so the table
starts clangd: Apple clangd 21.0.0 on the Mac), on this sample in a
directory named `sam ple` (a space, so the uri has %20):

```
sum.c                                  add.h
#include <stdio.h>                     /* add.h: the one function sum.c calls. */
#include "add.h"                       static inline int add(int a, int b) {
                                           return a + b;
int main(void) {                       }
    int total = add(2, 3);
    printf("%d\n", total);
    return 0;
}
```

(tabs for indentation). Rows with an underlined run are written `[_:text]`
(`ed.under(n)`); the two `~` rows are left out. The error is the `a` of
`total` deleted in the printf line (`totl`); the fix types it back. The
traffic came through a logging proxy between kilo and clangd (a scratch
script that relays both pipes and writes each frame with its time).

### 07.01 Starting a server: fork, exec and three pipes

```
    |sam ple/sum.c - 8 lines                                              1/8
    |lsp: started clangd (pid 91348)
```

A file with no server in the table (any .txt) is edited as without the
module, to the byte: the 00.02 screen, compared in 0701. KILO_LSP naming a
missing program: `lsp: cannot start no-such-server: No such file or
directory`; a file that is not a program: `... Permission denied`.

The descriptors, from a scratch build of the project at 07.01 with a line
after each step that lists the open descriptors (`c`: close-on-exec) into
a file (opened and closed by that line, so it is not in its own list):

```
kilo   before                             0 1 2
kilo   pipe(in)                           0 1 2 3 4
kilo   pipe(out)                          0 1 2 3 4 5 6
kilo   pipe(err)                          0 1 2 3 4 5 6 7 8
kilo   FD_CLOEXEC on all six              0 1 2 3c 4c 5c 6c 7c 8c
kilo   after fork                         0 1 2 3c 4c 5c 6c 7c 8c
kilo   closed in[0] out[1] err[1]         0 1 2 4c 5c 7c
child  after fork, open(/dev/null)        0 1 2 3c 4c 5c 6c 7c 8c 9c
child  dup2(in[0],0)                      0 1 2 3c 4c 5c 6c 7c 8c 9c
child  dup2(out[1],1)                     0 1 2 3c 4c 5c 6c 7c 8c 9c
child  dup2(null,2), then execvp          0 1 2 3c 4c 5c 6c 7c 8c 9c
kilo   read(err) gave 0 bytes             0 1 2 4c 5c 7c
kilo   closed err[0]                      0 1 2 4c 5c
server after exec: 0 pipe, 1 pipe, 2 /dev/null (the scripted server's own list)
```

So in[0]=3, in[1]=4, out[0]=5, out[1]=6, err[0]=7, err[1]=8, /dev/null 9
in the child; kilo keeps 4 (to the server) and 5 (from it). When exec
fails (KILO_LSP a missing path): `read(err) gave 4 bytes, an errno`,
errno 2 (No such file or directory), sizeof(int) = 4; then the child
(exit 127) is reaped at once. (Taken again on the final code, with the
change below: the same.)

Between fork() and exec the child runs kilo's code, its SIGWINCH handler
too, which would draw a screen from the child: so lspSpawn blocks SIGWINCH
with sigprocmask() before fork(); the child sets it to SIG_DFL and then
restores the mask (a mask still blocking it is inherited across exec), and
the parent restores the mask once fork() has returned, when a resize that
came meanwhile is drawn as usual. The scripted server logs the signals it
starts with blocked; 0701 checks SIGWINCH is not one (with the child's
restore left out, the test fails: `signals blocked in the server: [28]`,
macOS).

### 07.02 Messages: Content-Length and JSON-RPC

The first message at 07.02, as the scripted server read it, to the byte:

```
Content-Length: 108\r\n
\r\n
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"processId":88879,"rootUri":null,"capabilities":{}}}
```

(270 bytes of body at 07.07, with the capabilities.) With clangd the
project at 07.02 shows the raw reply, 2008 bytes (2060 to 07.07's
request); clangd writes `id` first:

```
    |lsp: 2008 bytes from clangd: {"id":1,"jsonrpc":"2.0","result":{"capabili
```

The reply in pieces (a scratch build at 07.02 with a line after each
read, figs07.py's READ_PATCH; the scripted server writing its 171-byte
answer, a header of 23 bytes and a body of 148, as 10 bytes, 30, then the
other 131, 0.255 s apart): kilo read 10 (the buffer holds 10), then 30
(40), then 131 (171), and then took the whole message off, 171 bytes with
a body of 148. The reads came 0.202 and 0.303 s apart in one run, 0.303
and 0.202 in the next (the figure's run: 0.203 and 0.306): the gaps are
the 0.1 s read, since kilo looks at the server only when read() on the
keyboard times out.

### 07.03 Reading JSON: just enough of a parser

```
    |lsp: clangd 21.0.0 ready
```

clangd 21's initialize result is 2060 bytes; the members kilo reads:
`serverInfo` {"name": "clangd", "version": "Apple clangd version 21.0.0
(clang-2100.1.1.101) mac+xpc arm64-apple-darwin25.6.0"}, and in
`capabilities`: `positionEncoding` "utf-8" (when kilo offers
["utf-8","utf-16"]; "utf-16" when it offers only that), `textDocumentSync`
{"change": 2, "openClose": true, "save": true}, `definitionProvider` true.

What the reader makes of escapes (printed and checked by tests/lsp_fuzz.c):
`"\n"` 0a; `"\u00e9"` c3 a9; `"\ud83d\ude00"` f0 9f 98 80 (the pair is one
character); `"\ud83d"` ef bf bd (U+FFFD); `"\ud83dx"` ef bf bd 78;
`"\udc00"` ef bf bd; `"\u0000"` ef bf bd. Depth 64 parses; 65, and 300000,
do not (an error, at once).

### 07.04 Keys and the server at once: poll()

Measured with scratch builds that count: at 07.03, calls to lspPump (one
per read() that times out); at 07.04, returns from poll(); written at exit.
Idle for 5 s with the scripted server running: **53 wakeups at 07.03
(about 10 a second, one per 0.1 s timeout), 2 at 07.04**, counted over
the whole run, from kilo's start to the Ctrl-Q that ends it. The 2 are
not idle ones. Taken again for the read through (each wake-up logged
with its time and revents): they are the server's answer to initialize
(the server's output readable) and the Ctrl-Q that ended the run (the
keyboard), and there are none in the 5 idle seconds between; at 07.03
that run had 54 in all, 49 of them in the 5 idle seconds. With clangd,
idle for 10 s: 07.03 98 in the idle seconds (101 in all), 07.04 none (2
in all, clangd's answer and the Ctrl-Q). The delay from the server writing its answer to kilo's frame with it reaching
the terminal (the server's log of its write and the test's read of the
pseudo-terminal, both on Python's monotonic clock), 20 runs each, two
sets: **07.03 min 1.4 ms, median 45.5 ms, max 100.3 ms (and 12.4, 56.4,
101.9); 07.04 min 0.1 ms, median 0.2 ms, max 0.7 ms (and 0.1, 0.2,
1.2)**. The wakeup counts were the same both times.

### 07.05 Telling the server what you see: didOpen and didChange

A session with clangd on the project at 07.07 (the proxy adds its own
start-up, so the first frames are about 0.7 s after kilo starts; the
intervals after that are kilo's). `>` kilo to clangd, `<` back; times from
kilo's start:

```
  0.712s > initialize                     id=1   270 bytes
  0.730s < reply                          id=1  2060 bytes
  0.730s > initialized                            52 bytes
  0.731s > textDocument/didOpen                  361 bytes   version 1
  0.752s < textDocument/publishDiagnostics       214 bytes   none
  5.070s   (key) Backspace: totl
  5.371s > textDocument/didChange                366 bytes   version 2
  5.431s < textDocument/publishDiagnostics       691 bytes   an error and a note
  6.999s   (key) a: total again
  7.301s > textDocument/didChange                367 bytes   version 3
  7.362s < textDocument/publishDiagnostics       214 bytes   none
  8.578s   (keys) " /* ok */", 9 keys, the last at 8.834s
  9.136s > textDocument/didChange                376 bytes   version 4: one for the 9
  9.198s < textDocument/publishDiagnostics       214 bytes
 12.478s > textDocument/definition        id=2   238 bytes   (07.07)
 12.480s < reply                          id=2   226 bytes
 14.195s > textDocument/definition        id=3   238 bytes
 14.195s < reply                          id=3   227 bytes
 14.196s > textDocument/didClose                 192 bytes   sum.c
 14.196s > textDocument/didOpen                  333 bytes   add.h, version 1
 14.945s > textDocument/didClose                 192 bytes   (Ctrl-B) add.h
 14.945s > textDocument/didOpen                  370 bytes   sum.c, version 1
 15.803s > shutdown                       id=4    44 bytes   (Ctrl-Q)
 15.804s < reply                          id=4    38 bytes   result null
 15.804s > exit                                   33 bytes
```

Each didChange left 301 to 302 ms after the last key. Ctrl-Q to kilo's
exit: 0.026 s (clangd 21 exits 0 at once on shutdown and exit). The
didOpen, uri and all:

```
{"jsonrpc":"2.0","method":"textDocument/didOpen","params":{"textDocument":{"uri":"file:///private/var/folders/.../sam%20ple/sum.c","languageId":"c","version":1,"text":"#include <stdio.h>\n#include \"add.h\"\n\nint main(void) {\n\tint total = add(2, 3);\n..."}}}
```

clangd publishes an empty list, without a version, for a file closed with
didClose; after a switch that is the other file's uri, so it is ignored.

### 07.06 Diagnostics: errors as you type

On the project at 07.06, 2 s after the Backspace that makes `totl`, with
no other key (the cursor is on the error's row, so its message is said as
the list arrives, and the counts are not):

```
    |#include <stdio.h>
    |#include "add.h"
    |
    |int main(void) {
    |        int [_:total] = add(2, 3);
    |        printf("%d\n", [_:totl]);
    |        return 0;
    |}
    |sam ple/sum.c - 8 lines (modified)                                   6/8
    |6: error: Use of undeclared identifier 'totl'; did you mean 'total'? (fi
    [cursor 6,27]
```

(The message is cut at the screen's 72 columns.) clangd 21 sends two
diagnostics: the error, range line 5 characters 16 to 20 (`totl`),
severity 1, message "Use of undeclared identifier 'totl'; did you mean
'total'? (fix available)\n\nsum.c:5:6: note: 'total' declared here"; and
its note as a diagnostic of its own, line 4 characters 5 to 10 (`total` in
`int total`), severity 3, "'total' declared here\n\n...". So `total` is
underlined too, and the counts noted as said are 1 error, 1 info. With the
cursor on a row without one when such a list comes (sum.c opened with
`totl` already in it, the cursor on row 1), the message line says
`lsp: 1 error, 1 info`.

The fix (`a` typed back): no underline, `lsp: no problems` (the cursor's
row has none, and the counts went to none). The bytes kilo writes for the
error's row, in the frame above (core + 07, at 07.06):

```
        printf("%d\n", totl);ESC[0K \r ESC[23C ESC[4m totl ESC[0m \r\n
```

and in the finished project, with module 06's colours (the string in
magenta; the overlay is the same, so `totl` is drawn over in the default
colour, accepted: the two extensions do not know each other):

```
        printf(ESC[35m"%d\n"ESC[39m, totl);ESC[0K \r ESC[23C ESC[4m totl ESC[0m
```

Positions, with the printf line as `printf("e-acute t e-acute: %d\n",
totl);` (written with \u escapes by the capture; the repo stays ASCII):
under utf-8 (kilo offers utf-8 first) clangd 21 says characters 23 to 27;
with utf-8 left out of the offer (the proxy took it out), utf-16 and
characters 21 to 25 (each e-acute is 2 bytes and 1 unit). Both become
bytes 23 to 27 of the row, render columns 30 to 34 (the tab is 8), and the
overlay `\r ESC[28C ESC[4m totl ESC[0m`: cells 28 to 31, where the
terminal shows `totl`.

### 07.07 Go to definition

```
    |lsp: clangd 21.0.0 ready | Ctrl-G = definition | Ctrl-B = back
```

Ctrl-G with the cursor on `total` in the printf line (byte 18 of the row):
request position line 5 character 18; reply `[{"range":{"end":{"character":10,"line":4},
"start":{"character":5,"line":4}},"uri":"file:///.../sam%20ple/sum.c"}]`;
the cursor goes to 5,13 (the `t` of `int total`, after the tab). Then nine
Rights and Ctrl-G on `add`: position line 4 character 14; reply range line
1 characters 18 to 21 in `file:///.../sam%20ple/add.h`; kilo reads add.h
in place of sum.c (didClose sum.c, didOpen add.h version 1):

```
    |/* add.h: the one function sum.c calls. */
    |static inline int add(int a, int b) {
    |        return a + b;
    |}
    |sam ple/add.h - 4 lines                                              2/4
    [cursor 2,19]
```

Ctrl-B: sum.c again, cursor 5,22 (where Ctrl-G was pressed); a second
Ctrl-B would go to add.h. With a space typed on the empty row 3 (unsaved),
Ctrl-G on `add`: `Unsaved changes: save first (Ctrl-S), then try again`,
and sum.c stays. The status bar shows the path from the current directory
(`sam ple/add.h`) when the file is under it.

### Hostile input, and what kilo does

Every case below is run by the module's tests against the scripted server
(the test in brackets), under AddressSanitizer where the compiler has it.
The editor keeps editing and saving after each.

| input | kilo |
|---|---|
| a header with no Content-Length, a bad number, a sign, two that differ, no colon, over 16 MB, 26 digits, 5000 bytes with no line end, a line of 5000 bytes, "\n" for "\r\n" (0702) | `lsp: bad message from NAME; stopped`, the server killed and reaped |
| a body of exactly 16 MB (0702) | read, and the next message too |
| a reply in pieces of 10/30/rest, or a byte at a time (0702) | read whole |
| two messages in one write (0702) | both acted on |
| a body that is not JSON, bytes after the value, a bad escape, a raw newline in a string, nesting 100000 or 65 deep, a trailing comma, an empty body, a leading zero, bytes FF FE (0703) | dropped; the server goes on |
| lone surrogates, \u0000, an ESC in serverInfo.name (0703) | U+FFFD; the ESC shown as '?' |
| ids never sent: 99, "1", 1.5, 1e400, null (0703) | ignored; 1.0 is 1 |
| an initialize result that is a string, null, or an error (0703) | `lsp: NAME did not initialize; stopped` |
| a server that dies in a message (status 5), by SIGSEGV in a message, or idle (status 7) (0702, 0704) | `lsp: NAME exited (status 5)`, `(signal 11)`, `(status 7)`; reaped |
| a server that closes its input and stays (0702) | the next write fails with EPIPE (SIGPIPE is ignored); `exited (signal 9)` |
| a server that writes without end (0704) | each key answered in well under a second |
| a server that stops reading, with a 5 MB file (0704) | keys answered; once over 8 MB waits, `lsp: NAME is not reading; stopped` |
| a server that never reads, at Ctrl-Q (0701) | killed after 0.5 s; the terminal put back |
| a slow server (0705) | a waiting didChange replaced: versions 2 and 4 arrive, 3 never |
| requests from the server, ids "abc" and 9 (0705) | error -32601 "method not found", same id |
| diagnostic ranges: past a line's end, on no line, ending on no line, backwards, negative, of the wrong type; severity 9; a message that is a number, or has newlines and ESC [ 2 J (0706) | clamped, dropped, empty, made the start, ignored; severity 1; ""; its first line, '?' for the ESC |
| 1500 diagnostics (0706) | all counted, the first 1000 kept |
| diagnostics for another uri, an older version, http://, file://t.c, %zz, %00, a uri that is a number (0706) | ignored; the same file through a link and with letters escaped is not |
| definition results: null, [], http://, %00, no range, line -1, a character that is a string, a string, a missing file (0707) | `lsp: no definition found`; `Can't open ...: No such file or directory` |
| a LocationLink; a line past the end; a character past a line's end (0707) | its targetSelectionRange; the last row; the line's end |
| an answer after a key (0707) | ignored: the key cancelled the jump |

tests/lsp_fuzz.c (see "The tests and the timeline") ran 3 s of each mode
under ASan and UBSan on the Mac: 250497 frame runs, 942145 JSON runs,
36324 message runs, no error.

### Found on the way

1. **A second stop after the server was gone.** When a write failed with
   EPIPE inside lspInitialized, lspGone stopped the server, and lspOpen,
   called next, wrote again: lspEnd ran a second time with `L.pid` 0, and
   `waitpid(0, ...)` and `kill(0, SIGKILL)` mean every process in kilo's
   group, kilo too. It showed as "exited (status 0)" over the real
   message, in 0702's EPIPE case. Fixed before the first commit: lspEnd,
   lspGone, lspSend, lspFlush and lspSendChange return at once with no
   server.
2. **editorJump's message was not drawn.** It calls
   editorSetStatusMessage, which does not ask lsp.c to redraw, so "save
   first" appeared only at the next key (0707). lspGoTo now asks for the
   redraw whatever happens.
3. **realpath() on glibc** is declared only with POSIX's X/Open part, and
   gcc 14 makes an implicit declaration an error: the projects at 07.05 to
   07.07 did not build on Debian. `_XOPEN_SOURCE 700` from 07.05
   (commit "ask for X/Open on Linux from 07.05").
4. A terminal nobody reads blocks kilo in its frame's write(): a capture
   that typed nine keys and slept without reading saw no didChange until
   it read again. A real terminal always reads; the tests' `wait_for`
   reads while it waits.
5. On macOS, Python's `time.monotonic()` and C's `CLOCK_MONOTONIC` are
   different clocks (one stops in sleep): compare times on one of them.

No bug in the core or in module 06 was found.

### Kept simple

- One server, started once, for the file kilo opened; a jump to a file of
  another language keeps it (languageId from the table, or "plaintext").
- The whole text in every didChange; `rootUri` null (clangd looks for a
  compile_commands.json from the file's directory up).
- In the finished project a jump to another file keeps E.syntax, chosen
  for the first file (07 cannot call 06's editorSelectSyntaxHighlight).
- One place to go back to.
- During a search, a message from the server can replace the "Search:"
  prompt until the next key.
- Positions under the core's model: a control character (drawn by the
  terminal as nothing in a file module 06 does not colour) and a
  double-width character still count as one cell.
- clangd's notes come as diagnostics of their own (kilo declares no
  relatedInformation), with severity 3.

### clangd versions

Apple clangd 21.0.0 (macOS): everything above. Debian clangd 19.1.7
(trixie, in Docker) and Alpine clangd 20.1.8 (in Docker): the clangd parts
of 0706 and 0707 pass (the message starts "Use of undeclared identifier
'totl'", the jumps land on the same rows and columns).

## 08 Undo and redo (an extension)

Module 08 (`lessons/08-undo/`, `optional: true`, started 2026-11-24 on the
owner's word) is ours, not upstream's: undo and redo, Vim's way cut to
kilo's size. Before a row changes, what it was is kept in a record; applying
a record puts that back and takes what was there, so the record becomes its
own opposite and redo is the same act as undo. It lives in kilo.c, as module
06 does: it works on E.row, which only kilo.c sees. At a lesson of the
module the project is the whole core plus the module's lessons so far;
modules 06 and 07 are never in it, and module 08 is in no lesson of the
core, of 06 or of 07 (checked: the projects at all 28 of those lessons
written with `./learn files` before the module existed and after, compared
with `diff -r`: identical; and no line of 06 or 07 is in an 08 project).
kilo.c at 08.01, 08.02, 08.03 and 08.04 is 1249, 1304, 1352 and 1389 lines
(1068 at 05.02); each of the four builds with `-Wall -W -pedantic -std=c99
-Werror`. The lessons are not written yet: this section is for them.

The design (records, hooks, steps, the saved point, the bound, the keys)
was fixed by the coordinator before the code was written; where the code
departs from it, "Departures from the design" says where and why.

### Where the code is

| where in kilo.c | what | lesson |
|---|---|---|
| "The undo history", after the editorSetStatusMessage prototype | U_CHG, U_INS, U_DEL; struct undoRecord, struct undoStep, struct undoState and the one global U; the prototypes of undoSave, undoClear and (08.04) undoClose | 08.01, fields by lesson |
| the core's row functions, editorOpen, editorSave, editorProcessKeypress, enum KEY_ACTION | the hooks (below) | 08.01, 08.03, 08.04 |
| "Undo and redo", a section after editorSave | UNDO_MAX_BYTES, undoSize (08.04); undoFreeStep, undoClear, undoGiveUp, undoPush (08.01); undoSave; undoClose; undoPut (08.01); undoApply (08.02); undoCursor (08.03); editorUndo (08.01); editorRedo (08.02); UNDO_OTHER, UNDO_TYPING, UNDO_DELETING, undoKind, undoKey (08.03) | |
| `@internal`, in no project | undoBroken, undoMaxBytes (KILO_TEST_UNDO_MAX), undoCheck (KILO_TEST_UNDO_LOG), the check in undoApply, the call of undoCheck after every key | |

U is a struct of its own, not fields of E: the history is not the editor's
state but a record of it, and the core's struct stays the core's. Its
fields: the undo stack (`undo`, `numundo`, oldest step first), the redo
stack (`redo`, `numredo`, 08.02), `open` (the last step on the undo stack
still takes records), `off` (nothing is remembered: a step being applied,
a file being read), `lost` (the history was given up in this step), `kind`
(08.03), `saved` and `bytes` (08.04).

### The lessons, and how they divide the code

The design's four, in its order, under its titles. Regions (`./learn
solution kilo 08.LL`):

| lesson | regions (function: title) |
|---|---|
| 08.01 | undoSave: keep what the row was; undoClose: close the open step; undoPut: put the row back; editorUndo: undo the last step |
| 08.02 | undoSave: a new edit forgets what was undone; undoApply: apply a record, and keep what it replaces; editorUndo: keep the step for redo; editorRedo: redo the step undone last |
| 08.03 | undoSave: a row already covered; undoClose: where the step ended; undoCursor: put the cursor back; editorUndo: the cursor where the step began; editorRedo: the cursor where the step ended; undoKind: the kind of a key; undoKey: where a step ends |
| 08.04 | undoSave: room for the record; editorUndo: modified or not, after an undo; editorRedo: modified or not, after a redo |

Not in regions, arriving with `@from`: the top block, a field per lesson
(the redo stack 08.02; row0, col0, row1, col1 and kind 08.03; saved and
bytes 08.04); undoSave's guard (`if (U.off || U.lost) return;`), and the
helpers undoFreeStep, undoClear, undoGiveUp and undoPush (08.01), with
their lines of 08.02 (the redo stack) and 08.04 (the byte count, the saved
point); the cursor before a step, kept as undoSave opens it (08.03);
UNDO_MAX_BYTES and undoSize (08.04); the three kinds (08.03); the keys.

What the project shows at a lesson, before the module is whole (the
`@else` parts):

- **08.01: every key is a step of its own**: editorProcessKeypress calls
  `undoClose()` for every key. editorUndo puts each record back with
  undoPut and frees the step ("nothing redoes it yet"). Ctrl-R has a case
  that does nothing. Undo leaves the cursor where it is.
- **08.02**: editorUndo applies the records with undoApply and pushes the
  step on the redo stack; Ctrl-R redoes. Still a key a step, the cursor
  left where it is.
- **08.03**: `undoKey(c)` takes the place of `undoClose()`; undo and redo
  put the cursor back.
- **Before 08.04** E.dirty counts as in the core, the changes undo and redo
  make included, so "(modified)" stays after an undo back to the file as it
  was.
- The comment above struct undoState names the redo stack only from 08.02.

### Hooks in core code

Each is one marked line or a small marked block; none is inside module 06's
or 07's blocks.

- `editorInsertRow`, after its `at > E.numrows` guard:
  `undoSave(U_INS,at);` (08.01).
- `editorDelRow`, after its guard: `undoSave(U_DEL,at);` (08.01).
- `editorRowInsertChar` (first line), `editorRowAppendString` (first line),
  `editorRowDelChar` (after its guard): `undoSave(U_CHG,row-E.row);`
  (08.01). The row's index is `row-E.row`: `idx` is module 06's.
- `editorInsertNewline`, just before it cuts the row by hand
  (`row->chars[filecol] = '\0'`): `undoSave(U_CHG,filerow);` (08.01).
- `editorOpen`: `undoClear();` at its top (a file read anew: a history
  anew), `U.off = 1;` just before the getline() loop and `U.off = 0;` just
  after it (08.01).
- `editorSave`, after a good write: `undoClose(); U.saved = U.numundo;`
  (08.04).
- `editorProcessKeypress`, just after the key is read: `undoClose();` at
  08.01 and 08.02, `undoKey(c);` from 08.03; and after Ctrl-F's case (and
  07's), `case CTRL_Z: editorUndo();` and `case CTRL_R:` (`editorRedo();`
  from 08.02) (08.01).
- `enum KEY_ACTION`: `CTRL_R = 18`, `CTRL_Z = 26` (08.01).

The records are made in the row functions, not in the key handlers: every
change to the text goes through those five functions and the one cut in
editorInsertNewline, so whatever edits through them is remembered with no
code of its own. That is why the hooks sit this low. In the finished
project it holds for all there is: module 06 changes no text; module 07's
editorJump does not edit either: it frees the rows itself and calls
editorOpen, which starts a new history, so a jump to another file starts
one with no code in module 07 (and the jump cannot be undone, as opening a
file cannot). Module 09's set_lines, when it comes, edits through them and
needs no undo code of its own. Not remembered: what undo and redo do
themselves (they change the rows through the same functions, with U.off
set) and the rows editorOpen reads.

### Records, the swap, steps

A record is one of three, made just before the change:

    U_CHG  row at is about to change    text: a copy of its chars, '\0' and all
    U_INS  a row is about to be inserted at at    text: NULL
    U_DEL  the row at at is about to be deleted   text: a copy of its chars

undoPut (08.01) puts a row back as a record says it was: U_CHG gives the
row the record's text (freeing the row's), U_INS deletes the row, U_DEL
inserts it again; the text is used up. undoApply (08.02) takes what the row
holds first (for U_CHG and U_INS: the row's chars pointer itself, set to
NULL in the row, so undoPut frees nothing; no copy), then calls undoPut,
and leaves the record holding what it took, with the opposite type:

    U_CHG(r, old)    the row gets old; the record gets the row's text    stays U_CHG
    U_INS(r)         the row is deleted; the record gets its text        becomes U_DEL(r, text)
    U_DEL(r, text)   a row with text is inserted at r                    becomes U_INS(r)

A step holds its records in the order they were made. Undo applies them
last to first and pushes the step on the redo stack; redo applies the same
records first to last and pushes it back. Enter in the middle of "abcdef"
at column 3: U_INS(r+1) (editorInsertRow), then U_CHG(r, "abcdef") before
the cut. Undone: U_CHG puts "abcdef" back and keeps "abc", then U_INS
deletes row r+1 and keeps "def" (now U_DEL(r+1, "def")). Redone, first to
last: U_DEL inserts "def" at r+1, U_CHG puts "abc" back.

A new edit (a record that opens a new step) empties the redo stack: the
history is a line, not a tree.

The leave-out rule (08.03): a U_CHG of row r is not recorded when the open
step's last record is a U_CHG or a U_INS of row r. So a run of typing on
one row is one record, as Vim saves a line once in an insert. Why it is
safe: every change to the text goes through a hook, and every hook makes a
record but for the ones this rule leaves out, which are only U_CHGs. So
while that last record stays the step's last, every change since it was a
change to the text of one row (a U_CHG left out), and each was of row r (a
U_CHG of another row is recorded, and would be the last record); no row was
inserted or deleted (U_INS and U_DEL are always recorded). So row r is
still at r and no other row has changed: undone, U_CHG(r) puts back r's
text from before all of those changes, and U_INS(r) deletes r whatever it
holds; either way the text is what it was before that record. Redone, the
record holds what it took at the undo: the row after all of them. Only the
last record is looked at, because a record further back may have rows
inserted or deleted after it, and then "row r" is another row. (Tested in
0803: ten characters are one record; typing below the last row is one,
the U_INS; a run of Backspaces that changes a row, joins it onto the row
above and changes that row again is four records, U_CHG, U_CHG, U_DEL,
U_CHG, and all of it comes undone.)

Steps (08.03): a step is a run of keys of one kind: UNDO_TYPING (Tab, a
printable character, a byte above 127), UNDO_DELETING (Backspace, Ctrl-H,
Delete), UNDO_OTHER (every other key). undoKey(c), called with every key
before it acts, closes the open step when the key is UNDO_OTHER or of
another kind than the keys before it (U.kind). An UNDO_OTHER key's own
edits (Enter's) open a step that the next key closes. A step is opened only
by its first record, so a step with no records is never kept. A step keeps
the cursor in the file (E.rowoff+E.cy, E.coloff+E.cx) from before its first
record and from the moment it is closed; undo puts the cursor at the first,
redo at the second, with undoCursor: a row off the screen goes to the top
line, as a search puts its match, and a column past the screen's width
scrolls the view right. That is what module 07's editorJump does after its
clamping; 08 has its own few lines (07's are not in an 08 project), and
does not clamp: the place is put back as it was, below the last row or
past the end of a row if that is where the cursor was (the core lets it be
there).

Undo and redo both close the open step first (undoClose), so a step is
whole before it is taken back, whoever calls them.

### Limits

| name | value | why |
|---|---|---|
| UNDO_MAX_BYTES | 8 MB (8388608) | what the history may hold: the bytes of text in both stacks, '\0's included, plus 24 bytes per record (sizeof struct undoRecord) and 32 per step (sizeof struct undoStep) on a 64-bit machine |

The count is U.bytes, kept as records are made, swapped and freed. It is
not malloc()'s own overhead, and the stack arrays are not shrunk when steps
leave them (as E.row is not when a row is deleted), so a few dropped or
undone steps' 32 bytes may still be allocated until the next push.

When a new record would take the count past the bound, the oldest undo
steps are dropped (never the open one) until it fits. If the open step and
the record alone do not fit, the history is given up: emptied, the message
line says `undo: change too big to remember`, and the rest of that step is
not remembered either (U.lost, until the step is closed: half a step
undone would put back a text that never was). An allocation that fails
gives the history up the same way, `undo: out of memory`. Either way the
change itself is made: undoSave returns, and the row function goes on.

The bound is kept when a record is made, as the design says, not when undo
or redo swap: an undo can take the count past it by what the step takes in
(the text needed to redo it; undoing a run of typing on an empty row takes
the whole typed row into the record). With nothing left to redo the count
is always within the bound: redo gives each record back what it held, and
the next record trims. 0804 checks exactly that, with a bound of 2000
bytes, on every key of a random run.

### The saved point (08.04)

U.saved is the number of steps under the text that is on disk: 0 when the
file is opened (undoClear), U.numundo in editorSave after a good write (the
open step closed first). After every undo and redo, E.dirty = (U.numundo !=
U.saved): "(modified)" goes when the undo stack is back at the save, and
comes back past it. Between them E.dirty counts as in the core. The saved
point is put out of reach, -1, so that the file stays modified until the
next save:

- by a new edit made after undoing below it (U.saved > U.numundo when the
  redo stack is emptied): the steps between were the way back to it;
- by dropping steps for memory, when more steps are dropped than were
  under it: each dropped step takes it down one, and below 0 it is -1. When
  exactly the steps under it are dropped, it is 0, the bottom of the
  stack, and still reachable (0804: saved after 2 steps, 12 in all with a
  bound of 10: undone to the bottom, not modified; one more step, and it is
  -1);
- by giving the history up (undoGiveUp).

### Invariants, and where each is tested

1. After undoing every step, the text is byte for byte what editorOpen read;
   after redoing every step, byte for byte what it was before the first
   undo. Tested by 0801 (every kind of edit, saved after the undo), 0802
   (undone and redone three times over) and 0804's random runs: 400 keys
   from a fixed seed (letters, space, Tab, Enter, Backspace, Delete, the
   arrows, Page Up and Down; in three runs Ctrl-Z and Ctrl-R too, alone and
   in bursts of up to six), on 24x80, 10x30, 6x20 and 12x40, on a .txt file
   and a .c file (module 06's idx and colours in the way), under ASan; then
   Ctrl-Z until "Nothing to undo" and a save, compared with the file as
   opened; then Ctrl-R until "Nothing to redo" and a save, compared with the
   save before the undos. A fifth run has a bound of 2000 bytes (steps are
   dropped, the saved point goes to -1): there only the second half holds,
   and it is checked. The four other runs end their 400 keys with 86 to
   134 steps of 94 to 168 records on the undo stack (counted through
   KILO_TEST_UNDO_LOG); where Ctrl-Z and Ctrl-R are in the mix, the redo
   stack holds up to 6 steps at times; the bounded run keeps about 30.
2. A record's row is inside the file when it is applied (0 to numrows-1,
   or to numrows for a U_DEL). An `@internal` check in undoApply exits with
   status 4 if not; every test runs with it, and the random runs under ASan
   would stop on any access out of E.row.
3. The bytes counted are the bytes held: U.bytes is what the stacks hold,
   counted again from them (each step's 32, each record's 24 and its text's
   len+1). With KILO_TEST_UNDO_LOG set, the `@internal` undoCheck counts
   again after every key and exits with status 4 when the two differ; 0803
   and 0804 run with it, the random runs included. (A test that left out
   `U.bytes -= undoSize(r)` in undoApply was caught by it at once; see
   "Break it".)
4. As the design states it, "E.dirty is 0 exactly when the text is the file
   as last opened or saved and the saved point is reachable", it is not
   true: type "a" and Backspace it, and the text is the file again with
   E.dirty not 0 and "(modified)" in the status bar (the core's count; a
   step that cancels another is still a change). What holds: after every undo and redo, E.dirty is 0 exactly when
   the undo stack is at a reachable saved point, and whenever E.dirty is 0
   the text is the file as last opened or saved. Tested by 0804 (each case
   of "The saved point", and in the random runs one Ctrl-Z after the last
   save is modified and the Ctrl-R after it is not).

### Departures from the design, and why

- **The swap is 08.02's function around 08.01's.** At 08.01 undo only puts
  rows back (undoPut: free the row's text, put the record's in); 08.02's
  undoApply takes what is there first and keeps it, and calls undoPut for
  the rest. So 08.01's code stays as it was and 08.02 adds to it; the swap
  in one function from 08.01 would teach what the record keeps a lesson
  before anything needs it. editorUndo calls undoPut at 08.01 and undoApply
  from 08.02 (an `@else`).
- **"A key a step" at 08.01 and 08.02 is `undoClose()` for every key**, at
  the place where `undoKey(c)` goes at 08.03 (an `@else`).
- **The cursor is 08.03's**, as the design's heading has it: at 08.01 and
  08.02 undo and redo leave the cursor where it is (it may then be past the
  end of a row or below the last row, places the core allows: typing there
  pads with spaces or adds rows, as in the core).
- **The leave-out rule is 08.03's** (a region of undoSave), not 08.01's:
  it changes no result, only memory, and it matters once a step is a run
  of keys. At 08.01 and 08.02 every change is recorded.
- **Allocations are checked from 08.01**, not only at 08.04: undoSave and
  the pushes of undo and redo give the history up (undoGiveUp: emptied,
  U.lost, "undo: out of memory") when malloc or realloc fails. Written
  without the checks, 08.01's code would have to change in three places at
  08.04. 08.04 adds the saved point's -1 to undoGiveUp, and the bound.
- **U.lost** (not in the design): after the history is given up in the
  middle of a step, the rest of that step is not remembered, until the step
  is closed. Without it, the records after the one that did not fit would
  make a step of their own, and undoing it would put back a text that never
  was (the middle of a join, say).
- **editorOpen turns recording off around the getline() loop**, not "at its
  top ... and on at its end": editorOpen returns early, with no rows, for a
  file that does not exist, and recording would have stayed off for the
  whole session on a new file. undoClear is at its top, as the design says.
- **Typing is "a key that types a character"**, not "whatever reaches
  editorInsertChar": undoKind cannot see which keys have no case of their
  own without repeating the switch. It is Tab, 32 to 126, and a byte above
  127, which editorReadKey returns as a negative char where char is signed
  (macOS on arm64: 0xc3 comes as -61) and as 128 to 255 where it is not
  (Linux on aarch64, Debian and Alpine: 195; checked with a two-line
  program on each): both are typing, so the two bytes of an e-acute are
  one step with the letters around them (0803, which passes on all three). A control character typed as text (Ctrl-A)
  is UNDO_OTHER: a step of its own.
- **Ctrl-R does nothing at 08.01** (a case that breaks), as the core's keys
  do before their lesson; before 08.01, Ctrl-Z and Ctrl-R are text, as any
  control key is in the core.
- **The saved point and dropped steps**: the design says the saved point is
  unreachable "if steps under the saved point are dropped". Dropping steps
  under it does not by itself lose it: it is lost when more steps are
  dropped than were under it (above). The code takes it down one per step
  dropped, to -1 below 0.
- **The bound is kept when a record is made**, not after undo and redo
  (above); and a record's need is counted before it is made, with the step's
  32 when it opens one.
- **"A jump of module 07" is not remembered**, though the design lists it
  with set_lines: a jump does not edit (above).
- **undoPut's U_CHG counts a change** (`E.dirty++`), as editorInsertRow and
  editorDelRow do for the other two; at 08.04 editorUndo and editorRedo set
  E.dirty after the step anyway.
- **Invariant 4** as stated does not hold (above).

### How the screens below were captured

With a scratch driver around track.py's `Editor`: the project at the lesson
(`./learn files kilo --at 08.LL`, built with make), on a 10x44
pseudo-terminal, on this notes.txt:

```
undo keeps
what each line was
before it changed
```

and the keys Down, `and `, Enter, Backspace, Backspace (which leave
`andwhat each line was`, cursor 2,4), then Ctrl-Z until "Nothing to undo",
then Ctrl-R until "Nothing to redo". Rows 5 to 8 (all `~`) are left out
below; the status bar is in reverse video.

### 08.01 Remembering what a line was

Every key a step, the cursor left where it is. The first screen, then each
Ctrl-Z (the message line keeps the HELP line until "Nothing to undo"):

```
    |undo keeps
    |andwhat each line was
    |before it changed
    |~
    |notes.txt - 3 lines (modified)           2/3
    [cursor 2,4]
```

Ctrl-Z 1: `and what each line was` (the second Backspace, the space).
Ctrl-Z 2: `and` and `what each line was` on two rows, `notes.txt - 4 lines
(modified)           2/4` (the join). Ctrl-Z 3: `and what each line was`
(Enter). Ctrl-Z 4 to 7: `andwhat ...`, `anwhat ...`, `awhat ...`, `what
each line was` (the four characters). Ctrl-Z 8:

```
    |undo keeps
    |what each line was
    |before it changed
    |~
    |notes.txt - 3 lines (modified)           2/3
    |Nothing to undo
    [cursor 2,4]
```

The cursor stayed at 2,4 throughout, and "(modified)" stays: E.dirty is
the core's count. Ctrl-R changes nothing. Ctrl-Z in a file just opened:
`Nothing to undo` (0801).

### 08.02 Redo: a record that undoes itself

The same eight Ctrl-Z, then Ctrl-R 1 to 7 give the screens back in the
other order: `awhat`, `anwhat`, `andwhat`, `and what`, `and` / `what each
line was` (4 lines), `and what`, `andwhat each line was`; Ctrl-R 8:

```
    |undo keeps
    |andwhat each line was
    |before it changed
    |~
    |notes.txt - 3 lines (modified)           2/3
    |Nothing to redo
    [cursor 2,4]
```

(Until then the message line still says `Nothing to undo`: nothing is said
when a step is undone or redone.) An edit after an undo empties the redo
stack: Ctrl-Z, a key typed, Ctrl-R says `Nothing to redo`.

### 08.03 One Ctrl-Z, one thought: steps

Three steps: `and ` (typing), Enter (other), the two Backspaces (deleting).
Ctrl-Z 1, the Backspaces (the cursor where the first one was pressed):

```
    |undo keeps
    |and
    |what each line was
    |before it changed
    |notes.txt - 4 lines (modified)           3/4
    [cursor 3,1]
```

Ctrl-Z 2, Enter: `and what each line was`, cursor 2,5. Ctrl-Z 3, `and `:
`what each line was`, cursor 2,1. Ctrl-Z 4: `Nothing to undo`. Ctrl-R 1 to
3: `and what ...` cursor 2,5; the two rows, cursor 3,1; `andwhat ...`
cursor 2,4 (where each step ended). Ctrl-R 4: `Nothing to redo`.

### 08.04 The saved point, and a bound on memory

The same keys and screens as 08.03, but for the status bar: the file was
not saved, so the saved point is the file as opened, and after Ctrl-Z 3

```
    |undo keeps
    |what each line was
    |before it changed
    |~
    |notes.txt - 3 lines                      2/3
    [cursor 2,1]
```

with no "(modified)"; Ctrl-R 1 puts it back. With a save between, on the
same file, A, Ctrl-S, B:

```
    |ABundo keeps
    |what each line was
    |before it changed
    |~
    |notes.txt - 3 lines (modified)           1/3
    |49 bytes written on disk
    [cursor 1,3]
```

Then (rows 2 to 4 as above, the message line keeping `49 bytes written on
disk` for its 5 seconds):

- Ctrl-Z, back at the save: `Aundo keeps`, `notes.txt - 3 lines
  1/3` (no "(modified)"), cursor 1,2;
- Ctrl-Z, past it: `undo keeps`, `notes.txt - 3 lines (modified)
  1/3`, cursor 1,1;
- C, a new edit below the save: `Cundo keeps`, "(modified)", cursor 1,2;
- Ctrl-Z: `undo keeps`, still "(modified)": the text on disk, `Aundo keeps`,
  cannot be reached now.

A file of two rows, `short` and 9 000 000 w's, X typed at the start of the
second row (the project's own 8 MB bound):

```
    |short
    |Xwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwww
    |~
    |~
    |big.txt - 2 lines (modified)             2/2
    |undo: change too big to remember
    [cursor 2,2]
```

and Ctrl-Z then says `Nothing to undo`; the X stays, and a save writes it.
`undo: out of memory` was not seen: nothing here makes malloc fail, and no
test does.

### Measurements

On the Mac (Apple M-series, macOS): the bytes read from KILO_TEST_UNDO_LOG
with the tree's own build (the finished editor), the times with the project
at 08.04 built with make.

- **A 60-character line typed into an empty row**: as one step (a run of
  typing, 08.03), 57 bytes held: one step (32), one record (24) and the
  empty row it kept (1). As 60 steps (Ctrl-L, a key that does nothing,
  after each character): 5190 bytes: 60 steps and records (3360), and the
  row as it was before each character, 1 to 60 bytes with its '\0' (1830).
  At 08.01 and 08.02, where every key is a step, typing is the second case.
  On a file with no rows, the first character's record is the U_INS of the
  row it makes (no text), and the rest are left out: 56 bytes, or 5189.
- **A step that touches 10000 rows**: 10000 empty rows, the cursor on the
  last, 9999 Backspaces in one run (each joins an empty row onto the one
  above): one step of 19998 records (a U_CHG and a U_DEL a join), 499982
  bytes held. Undo and redo, from the key sent to the frame drawn (the
  frame itself takes about 0.5 ms), on the project at 08.04, 10 of each:
  undo min 1.0, median 1.3, max 3.1 ms; redo min 0.7, median 0.9, max 2.8
  ms. With the last row 60 y's (so each U_DEL keeps 61 bytes, 1099922
  bytes held): undo median 4.3 ms (3.6 to 5.3), redo median 3.4 ms (3.1 to
  11.0). Rows are inserted at the end each time (the joins went up from the
  last row), so no memmove of E.row is long.

### Ctrl-Z and the terminal

Raw mode clears ISIG (enableRawMode, 01.01, says so in its comment), so
Ctrl-Z reaches kilo as the byte 26 and Ctrl-R as 18. Checked otherwise, with
a scratch build of the project at 08.04 that leaves ISIG on, run under a
small job-control shell (a Python script that takes the pseudo-terminal as
its controlling terminal, runs kilo in a process group of its own in the
foreground, and waits for it with WUNTRACED): x, then Ctrl-Z. The terminal
turns Ctrl-Z (VSUSP) into SIGTSTP for the foreground group, and kilo, which
has no handler for it, stops: `stopped by signal 18 (SIGTSTP)` (macOS's
number), and the shell has its terminal back still in kilo's
raw mode (ECHO off, ICANON off). Built as it is, kilo keeps running and the
x is undone. In the tests' own terminal the same build does not stop:
there kilo leads a session of its own, its process group is orphaned, and
a stop signal from the terminal to an orphaned group is not delivered.

### Break it

Each was run as the change it describes, on a copy of the tree, with the
module's four tests (a scratch script; the result in brackets).

- **08.01, reading the file remembered**: take out `U.off = 1;` before
  editorOpen's loop. The rows read are one step: Ctrl-Z in a file just
  opened deletes every row, and the screen is all `~`. (0801, 0803, 0804.)
- **08.02, no opposite**: `was.type = r->type;` in undoApply, so a U_INS
  stays a U_INS. Enter at the start of `xyz` (on `abc`, `xyz`), undone,
  redone: the redo deletes a row again, and `xyz` is gone (`abc`, `~`).
  In the longer runs the `@internal` check stops kilo with status 4 (a
  record of a row that is not in the file). (0802, 0803, 0804.)
- **08.02, redo last to first**: kilo stops with status 4 on the first
  step of more than one record whose rows move (invariant 2). (0802, 0804.)
- **08.02, the redo stack kept after a new edit**: take out the loop that
  frees it in undoSave. `a`, Enter, `b`, two Ctrl-Z, `Q`, Ctrl-R: the redo
  puts the rows back as they were before `Q` (`a`, `one`): the Q typed is
  lost. (0802, 0804.)
- **08.03, no leave-out rule**: ten characters typed on `abc` are ten
  records, 357 bytes, not one record and 57. Nothing else changes. (0803.)
- **08.03, a byte above 127 as an UNDO_OTHER key**: `caf` and an e-acute
  typed, then Ctrl-Z: the e-acute's second byte is undone alone, and its
  first stays on the screen. (0803.)
- **08.03, no cursor row after a step**: take out the line that keeps row1
  in undoClose: redo puts the cursor on the first row of the file, in the
  right column (row1 is still the 0 the step was made with). (0802, 0803.)
- **08.04, the count not taken down when a record is applied**: take out
  `U.bytes -= undoSize(r);` in undoApply: the `@internal` count after the
  next key differs, and kilo stops with status 4 (invariant 3). (0803,
  0804.)
- **08.04, E.dirty set to 1 after an undo**: "(modified)" stays after an
  undo back to the file. (0801, 0803, 0804.)
- **08.04, the saved point not taken down when a step is dropped**: with
  ten steps allowed, saved after six, twelve made: the saved point is still
  6 where it is 4. (0804.)
- **08.04, the saved point kept after a new edit below it**: take out `if
  (U.saved > U.numundo) U.saved = -1;`. `a`, Ctrl-S, Ctrl-Z, `c`, Ctrl-Z,
  Ctrl-R: the undo stack is one step high, as at the save, so the status
  bar says the file is not modified, with `cone` on the screen and `aone`
  on disk. (0804.)
- **08.01, the rest of a step kept after the history is given up**: take
  out `|| U.lost` from undoSave's guard. With a bound of 1000 bytes, `tail`
  joined onto a row of 5000 w's: the long row's record does not fit (the
  message says so), the U_DEL of `tail` after it is kept as a step of its
  own, and Ctrl-Z puts `tail` back under the row that already ends in it:
  2 lines, where there never were. (0804.)

Not caught, and why: the leave-out rule without its `type != U_DEL`
(a U_CHG of row r left out after a U_DEL of row r too). With kilo's keys
no step holds a U_DEL of row r and then a change to row r: after a join
(the only U_DEL) the cursor is on the row above, and getting to row r
takes a key that ends the step. So the half of the rule that excludes
U_DEL is there for edits that do not come from keys (module 09's
set_lines); the proof above covers it, no test reaches it.

### Found on the way

1. **The cursor past the end of a row.** The core lets the cursor stand
   past the end of its row: when the window shrinks, handleSigWinCh pulls
   E.cy up onto the screen and keeps E.cx, so on a shorter row the cursor is
   past its end (0801 uses this: row 15 at column 25, the window cut to 8
   rows, the cursor on row 5, `r5`, at column 25; X typed pads 23 spaces,
   and an undo takes them all). Upstream's, kept.
2. **Down from a long row scrolled right.** On a row of 120 x's at column
   101 (the view scrolled right by 22), Down to `short` leaves the view
   scrolled right by 5 with the cursor in column 0: the row shows empty.
   editorMoveCursor's fix-up moves the view, not the cursor alone.
   Upstream's, kept; 0803 moves left instead.
3. **A stop from the terminal in the tests' terminal** (above): the
   tests could not show Ctrl-Z stopping kilo. 0101's comment says that with
   ISIG on, Ctrl-C, Ctrl-Z and Ctrl-\ "would stop it" there; for Ctrl-Z that
   is not so (the stop is not delivered), though the test still catches ISIG
   on: the byte never reaches kilo, and the file saved shows it.
4. **0101 expected Ctrl-Z in the text.** The core's 01.01 test types Ctrl-C,
   Ctrl-Z and Ctrl-\, and expected the saved file to start with the bytes
   26 and 28: true of the core, but in the finished editor Ctrl-Z is now
   undo, and the test failed there. Its last check was changed, and only
   that: when kilo said `Nothing to undo` (module 08 is in the tree), the
   file starts with 28 alone; otherwise with 26 and 28, as before. A learner
   at 01.01 has the reference code of every later lesson, module 08's
   included, so the test meets the same editor there.

No bug in the core, module 06 or module 07 was found.

### Kept simple

- A line of history, not a tree: a new edit after an undo loses the steps
  undone (Vim and Helix keep them as branches; see below).
- No undo of opening another file (module 07's jump): the history starts
  again.
- Steps are runs of a kind of key, with no clock: no time interval groups
  them (Zed's 300 ms), and no count ends a run (Emacs's 20).
- Records hold whole rows: a character typed into a long row copies the
  row once per step (the leave-out rule makes it once, not once a key).
- No persistent undo; the history goes when kilo exits.
- Module 09's mapped keys: undoKind classes a key by its code, so a
  printable key that 09 maps to a function would count as typing. When 09
  comes, a mapped key should be UNDO_OTHER (a script's edits a step of
  their own, as the design says).

### The notable editors

Read from the sources at the tags below (raw files on GitHub, fetched with
curl, 2026-11-24); every claim here is in a line quoted, and line numbers
are the files' at those tags. What could not be seen in a source is under
"Not confirmed" and must not go into a lesson.

**Vim**, tag v9.2.1398 (6abceda02d4ede92405d61a435f846a06a1f32f3),
https://raw.githubusercontent.com/vim/vim/v9.2.1398/ + the path.

- What is saved: `src/undo.c` 242-243, u_save: "Save the lines between
  "top" and "bot" for both the "u" and "U" command." u_savecommon (404-407):
  "Common code for various ways to save text before a change." It copies
  each line into the entry (724, 732): `for (i = 0, lnum = top + 1; i <
  size; ++i)` ... `if (u_save_line(&uep->ue_array[i], lnum++) == FAIL)`.
- The entry, `src/structs.h` 472-476: `ue_top; // number of line above undo
  block`, `ue_bot; // number of line below undo block`, `ue_lcount; //
  linecount when u_save called`, `*ue_array; // array of lines in undo
  block`, `ue_size; // number of lines in ue_array`.
- The swap, `src/undo.c` 2777-2779, u_undoredo: "The lines in the file are
  replaced by the lines in the entry list at curbuf->b_u_curhead. The
  replaced lines in the file are saved in the entry list for the next
  undo/redo." Then (2888) "Delete the lines between top and bot and save
  them in newarray.", and (2994-2995) `uep->ue_size = oldsize;`
  `uep->ue_array = newarray;`. The entry list is reversed as it goes (2999,
  3001-3003): "insert this entry in front of the new entry list". Undo calls
  `u_undoredo(TRUE);` (2384), redo `u_undoredo(FALSE);` (2400): one
  function for both.
- A line saved once: `src/undo.c` 617-622: "When saving a single line, and
  it has been saved just before, it doesn't make sense saving it again.
  Saves a lot of memory when making lots of changes inside the same line.
  This is only possible if the previous change didn't increase or decrease
  the number of lines. Check the ten last changes." (648: `if
  (uep->ue_size == 1 && uep->ue_top == top)`). Vim looks at ten; kilo at
  one.
- A step: `runtime/doc/undo.txt` 83-84: "One undo command normally undoes a
  typed command, no matter how many changes that command makes. This
  sequence of undo-able changes forms an undo block." In Insert mode,
  `src/getchar.c` 1475-1476, may_sync_undo: "Do not sync: - In Insert
  mode, unless cursor key has been used." `runtime/doc/insert.txt` 362-363,
  of the cursor keys and the like: "The changes (inserted or deleted
  characters) before and after these keys can be undone separately." CTRL-G
  u starts a new block (undo.txt 109-111).
- The tree: `runtime/doc/undo.txt` 130-135: "Undo branches ... it is also
  possible to branch off. This happens when you undo a few changes and then
  make a new change. The undone changes become a branch." `:undol[ist]`
  "List the leafs in the tree of changes." (140); `g-` "Go to older text
  state." (164); `:ea[rlier] {N}s` "Go to older text state about {N}
  seconds before." (168); `:ea[rlier] {N}f` "... {N} file writes before."
  (173); `g+`, `:lat[er]` (183, 186). 242-243: "Note that using "u" and
  CTRL-R will not get you to all possible text states while repeating "g-"
  and "g+" does."
- Persistent undo: `runtime/doc/undo.txt` 246-251: "By setting the
  'undofile' option, Vim will automatically save your undo history when you
  write a file and restore undo history when you edit the file again."

**Neovim**, tag v0.12.6 (022946c802832f938398dfae34b3f277ca9509d4),
https://raw.githubusercontent.com/neovim/neovim/v0.12.6/ + the path. The
same design, the same comments: `src/nvim/undo.c` 250 (u_save), 345-348
(u_savecommon), 2256-2258 (u_undoredo: "The replaced lines in the file are
saved in the entry list for the next undo/redo."), 2417-2418 (`uep->ue_size
= oldsize;` `uep->ue_array = newarray;`), 502-504 and 531-532 (a single
line saved once); `src/nvim/undo_defs.h` 22-27 (u_entry_T: `ue_top`,
`ue_bot`, `ue_lcount`, `char **ue_array;`, `ue_size`); `runtime/doc/undo.txt`
86-87 (undo blocks), 131-137 (branches; "The undo-tree of a file can be
visualized and interactively applied using |:Undotree|."), 142
(`:undolist`), 248-253 ('undofile').

**Emacs**, tag emacs-31.1 (1f9518d22ae0fe4490ea9761ea7d39fbb970a890),
https://raw.githubusercontent.com/emacs-mirror/emacs/emacs-31.1/ + the path.

- An entry of buffer-undo-list, `doc/lispref/text.texi` (node Undo): "(BEG .
  END) This kind of element indicates how to delete text that was inserted.
  Upon insertion, the text occupied the range BEG--END in the buffer."
  (1398-1401); "(TEXT . POSITION) This kind of element indicates how to
  reinsert text that was deleted. The deleted text itself is the string
  TEXT." (1403-1405); "nil This element is a boundary. The elements between
  two boundaries are called a change group; normally, each change group
  corresponds to one keyboard command" (1452-1455). Others: a position
  (point), (t . TIME-FLAG), text properties, markers, (apply ...). An
  insertion records no text, a deletion the text.
- `src/undo.c` 81-84, record_insert: "Record an insertion ... (It is
  possible to record an insertion before or after the fact because we
  don't need to record the contents.)"; 98-99: "If this is following
  another insertion and consecutive with it in the buffer, combine the
  two."; record_delete (159-160, 189-191) pushes `(string . beg)`.
- Undo is recorded too: `doc/lispref/text.texi` 1522-1527:
  "primitive-undo adds elements to the buffer's undo list when it changes
  the buffer. ... The new elements added by undoing are not part of this
  saved value, so they don't interfere with continuing to undo."
  `lisp/simple.el` 3427-3430: "a redo record is just an undo record, the
  only difference is that it is created by an undo command (instead of an
  ordinary buffer edit). ... a record used to undo an undo is called redo
  record." undo-redo (3606-3607): "Undo the last ARG undos, i.e., redo the
  last ARG changes."
- Amalgamating, still 20: `lisp/simple.el` 49-50: `(defvar
  amalgamating-undo-limit 20` "The maximum number of changes to possibly
  amalgamate when undoing changes."; `doc/lispref/text.texi` 1476-1484:
  "The editor command loop automatically calls undo-boundary just before
  executing each key sequence ... A few exceptional commands are
  amalgamating ... with these a boundary is inserted only every 20th
  command ... By default, the commands self-insert-command ... and
  delete-char ... are amalgamating."

**Zed**, tag v1.29.3 (d01b134cddf5e4f71964deb2d6f81cdb38fcf1e7),
https://raw.githubusercontent.com/zed-industries/zed/v1.29.3/ + the path.

- An undo is an operation of its own: `crates/text/src/text.rs` 619-622,
  `pub enum Operation { Edit(EditOperation), Undo(UndoOperation), }`;
  633-636, `pub struct UndoOperation { pub timestamp: clock::Lamport, pub
  version: clock::Global, pub counts: HashMap<clock::Lamport, u32>,`. Undo
  and redo both build one (1423-1426, undo_or_redo): `counts.insert(edit_id,
  self.undo_map.undo_count(edit_id).saturating_add(1));`. An edit is undone
  when its count is odd, `crates/text/src/undo_map.rs` 68-69: `pub fn
  is_undone(&self, edit_id: clock::Lamport) -> bool {
  self.undo_count(edit_id) % 2 == 1`; a fragment of text is visible when its
  insertion is not undone and every deletion of it is (text.rs 3151-3152).
  So an undo marks edits; it does not apply an inverse edit.
- A transaction: `pub struct Transaction { pub id: TransactionId, pub
  edit_ids: Vec<clock::Lamport>, pub start: clock::Global,` (135-138); the
  history is `undo_stack` and `redo_stack` (156-157), and ending a
  transaction does `self.redo_stack.clear();` (278).
- Grouping, 300 ms: 225-230, `group_interval: if cfg!(any(test, feature =
  "test-support")) { Duration::ZERO } else { Duration::from_millis(300) },`;
  293-294: `&& entry.first_edit_at - prev_entry.last_edit_at <
  self.group_interval`.

**Helix**, tag 25.07.1 (ac94841019910ff405f31a8668389a06a169e0e5),
https://raw.githubusercontent.com/helix-editor/helix/25.07.1/ + the path.

- `helix-core/src/history.rs` 58-65: `struct Revision { parent: usize,
  last_child: Option<NonZeroUsize>, transaction: Transaction, // We need an
  inversion for undos because delete transactions don't store // the
  deleted text. inversion: Transaction, timestamp: Instant,`. 15-20: "the
  history is represented as a vector of revisions ... Each revision ... has
  a parent revision, a [Transaction] that can be applied to its parent to
  transition from the parent to itself, and an inversion of that
  transaction".
- By time: 305-309, `pub enum UndoKind { Steps(usize),
  TimePeriod(std::time::Duration),`; `earlier` and `later` (287-300) take
  either. Steps follow the vector, not a path in the tree (228:
  `self.jump_to(self.current.saturating_sub(delta))`).
- A revision in Insert mode: `helix-term/src/ui/editor.rs` 1449-1452: "Store
  a history state if not in insert mode. This also takes care of committing
  changes when leaving insert mode."

**VS Code**, tag 1.147.0 (8a14f0cc1b08d531eb83255ea3764ae22aa932b5),
https://raw.githubusercontent.com/microsoft/vscode/1.147.0/ + the path.

- An element of the edit stack, `src/vs/editor/common/model/editStack.ts`
  40-47 (SingleModelEditStackElement's data): `beforeCursorState`,
  `afterCursorState`, `changes: TextChange[]`, with before and after
  version ids and line endings; a TextChange
  (`src/vs/editor/common/core/textChange.ts` 35-39)
  is `oldPosition, oldText, newPosition, newText`. pushEditOperation
  (428-432) applies the edits and keeps their inverses: `const
  inverseEditOperations = this._model.applyEdits(editOperations, true,
  reason);`.
- Undo stops: `src/vs/editor/common/cursorCommon.ts` 34-40, `export const
  enum EditOperationType { Other = 0, DeletingLeft = 2, DeletingRight = 3,
  TypingOther = 4, TypingFirstSpace = 5, TypingConsecutiveSpace = 6,`; and
  `src/vs/editor/common/cursor/cursorTypeEditOperations.ts` 1022-1033,
  shouldPushStackElementBetween: "Always set an undo stop before non-type
  operations" ... "Insert undo stop between different operation types"
  (`return normalizeOperationType(previousTypingOperation) !==
  normalizeOperationType(typingOperation);`); Enter (581-582)
  `shouldPushStackElementBefore: true`; a cursor move pushes one
  (`src/vs/editor/browser/coreCommands.ts` 607, 611:
  `viewModel.model.pushStackElement();`);
  a delete that spans lines too
  (`src/vs/editor/common/cursor/cursorDeleteOperations.ts` 183-184).
- A line, not a tree: `src/vs/platform/undoRedo/common/undoRedoService.ts`
  284-292, pushElement: "remove the future" ... `this._future = [];`.

| editor | what a record holds | what one step is | line or tree |
|---|---|---|---|
| Vim, Neovim | whole lines: the lines between ue_top and ue_bot, swapped with the buffer's on undo and redo | an undo block: one command; in Insert mode the whole insert, cut by cursor keys or CTRL-G u | tree (branches, g- g+, :undolist, :earlier by count, time or writes); persistent with 'undofile' |
| Emacs | positions and characters: (BEG . END) for an insertion (no text), (TEXT . POSITION) for a deletion, and more | a change group between boundaries: one command; typed characters and delete-char amalgamated up to 20 | a line, in which undoing adds records, so redo is undoing the undo |
| Zed | operations: a transaction is a list of edit ids; an undo is an operation of counts that marks edits undone | a transaction; transactions less than 300 ms apart are grouped | a line: undo and redo stacks, redo cleared when a transaction ends |
| Helix | operations: a transaction and its inversion, with a timestamp | a revision, committed when not in Insert mode (so an insert is one) | tree of revisions (parent, last_child); earlier and later by steps or time |
| VS Code | characters: TextChanges (old and new text and positions) from the inverse edits, with the cursor before and after | a run of one kind of edit (typing, deleting left, deleting right, other) between undo stops; Enter, a cursor move, a delete over lines push a stop | a line: a new element removes the future |
| kilo (this module) | whole rows: a row's text before it changes or is deleted, or that it was inserted; swapped on undo and redo, as Vim's | a run of keys of one kind (typing, deleting, other), as VS Code's types; an other key ends one | a line |

Not confirmed (could not be seen in the sources read, so not for a lesson):

- Zed: the word "CRDT" is in neither file read; that the buffer is one is
  an inference from the Lamport timestamps and versions. Which keys start
  and end a transaction is decided in Zed's editor crate, not read; only
  the 300 ms grouping in text.rs is confirmed. No inverse-edit construction
  was seen in the undo path read (undo_or_redo, apply_undo), which does not
  prove there is none elsewhere.
- Neovim's getchar.c and options.txt were not read: its sync rule and its
  'undofile' option text are confirmed through Vim and Neovim's undo.txt
  only.
- Vim: no doc line says "an Insert-mode session is one undo block" in so
  many words; it follows from "One undo command normally undoes a typed
  command" and the "Do not sync" comment in getchar.c.
- Emacs's key bindings for undo and undo-redo, and Helix's keymap and any
  persistent undo, were not read. VS Code's undo across file reloads was
  not looked for.

## 09 An API, and Lua on top of it (an extension)

Module 09 (`lessons/09-api-and-lua/`, `optional: true`, started 2026-11-24
on the owner's word) is ours: the editor's operations as a table of typed C
functions, the real Lua embedded and given that table as `kilo.api`, any
key and the editor's events bound to Lua functions, colour and the status
bar drawn from a script, a script that goes wrong never taking the file with
it, and the editor run with no screen at all. Neovim's shape, cut to kilo's
size; "The notable editors" below says where Neovim and the others really
stand, from their sources. The design (files, types, functions, limits,
guards) was fixed by the coordinator, with a second revision the same day
("fully extensible": every key, KeyPress and CursorMoved, drawing, input,
open, quit); where the code departs from it, "Departures" says so.

At a lesson of the module the project is the core plus 09's lessons so far:
no code of 06, 07 or 08 (checked: no `editorSelectSyntaxHighlight`, `lsp`,
`json`, `HL_`, `E.syntax`, `undo`, `CTRL_Z` or `CTRL_R` in any 09 project,
and each builds with `-Wall -W -pedantic -std=c99 -Werror`). Module 09 is
in no core, 06, 07 or 08 lesson: the projects at the 28 lessons to 07.07,
written out before the module existed and after, are identical (`diff
-r`); and after module 08 was merged in, the projects at all 32 lessons to
08.04 are identical to master's at cf9919a, which has 08 and not 09; no 08
project holds code of 09. The finished kilo.c is 2749 lines (with 06, 07
and 08). 09.10, "Features as scripts" (plugins written only in Lua), is
not built yet: it follows the review of this code.

### Lua itself

Lua 5.4.9, https://www.lua.org/ftp/lua-5.4.9.tar.gz, sha256
2335b6c582a52654f94612bf10d2f4672805d05329aa6568b1d8cd9e5c6fb8e6 (checked
on download, 2026-11-24). `tracks/kilo/lua/` holds the release's README and
src/ exactly as they are (63 files, all ASCII; no doc/, no Makefile of the
top), in a commit of their own; `lua/.gitignore` keeps out what a build
leaves there. NOTICE has a Lua section with the MIT licence text (the end of
src/lua.h). It is the one thing in the track we do not write.

The site does not show it (track.py `HIDDEN` "lua/*"), so a project written
out by `./learn files` has no lua/. A reader fetches it once, and 09.01
gives the commands (tried on the project at 09.01 as written out):

    curl -O https://www.lua.org/ftp/lua-5.4.9.tar.gz
    shasum -a 256 lua-5.4.9.tar.gz     # 2335b6c5...b8e6
    tar xzf lua-5.4.9.tar.gz && mv lua-5.4.9 lua

(The whole release as lua/: the Makefile uses lua/src only.) The course's
own tools supply it: track.py's `prepare(root)`, which `./learn run`,
`bench`, `verify` and `check-timeline` call before they build a project,
first calls `supply_lua(root)`, which copies the track's lua/ (README and
src/, not what a build left there) into a project that has script.c and no
lua/. Projects without script.c (every core, 06 and 07 lesson) get nothing.
`check-skeleton` and the tests copy or use the whole track, lua/ included.
No change under harness/.

The Makefile builds the library once, as a target of its own, with Lua's
own Makefile, and links it:

    lua/src/liblua.a:
    	$(MAKE) -C lua/src liblua.a MYCFLAGS=-DLUA_USE_POSIX

Lua's Makefile compiles with `gcc -std=gnu99 -O2`; kilo's own files keep
kilo's flags, and Lua's headers pass them with `-Werror`. It takes 2.8 s
here (Lua and kilo). The Makefile has four shapes, written with @from
blocks nested inside other blocks' @else parts (the harness takes those: a
block's @else lines are uncommented once per enclosing block not reached):
the core's (unchanged), core + 07 (unchanged, to the byte), core + 09
(kilo.c script.c, api.h from 09.02, and Lua), and the finished tree (all of
them). `make clean` removes Lua's build too (from 09.01).

### The files

| file | lines in tracks/ (markers in) | what it is |
|---|---|---|
| script.h | 43 | the limits, all of them; what kilo.c calls (scriptStart, scriptEval, scriptCall, scriptUnref, scriptRun) and what script.c calls in kilo.c (editorMessage, editorScriptReturned, disableRawMode) |
| script.c | 743 | everything that includes lua.h: the state, the protected way in, errors, print, the dispatcher, references, the Lua on top, the count hook, the allocator, the panic function, kilo -l |
| api.h | 79 | the API's types (ApiType, ApiString, ApiValue, ApiError, ApiFn, ApiFunc) and the table's declaration |
| kilo.c | 3647 | the hooks below, and the section "The API" above main(): the 24 functions, the table, --api-info, the prompt, keys by name, autocommands, highlights, the status line, kilo -l. No Lua header. |
| Makefile | | from 09.01 `kilo.c script.c` and Lua's library |

The project at each lesson (lines, `./learn files kilo --at 09.LL`):

| lesson | kilo.c | script.c | script.h | api.h |
|---|---|---|---|---|
| 09.01 | 1141 | 218 | 24 | - |
| 09.02 | 1318 | 403 | 24 | 77 |
| 09.03 | 1406 | 404 | 25 | 77 |
| 09.04 | 1535 | 476 | 27 | 79 |
| 09.05 | 1681 | 476 | 28 | 79 |
| 09.06 | 1858 | 476 | 30 | 79 |
| 09.07 | 1915 | 476 | 30 | 79 |
| 09.08 | 1915 | 559 | 32 | 79 |
| 09.09 | 1941 | 571 | 33 | 79 |

### The lessons, and how they divide the code

The coordinator's revised list, in its order (09.10 later). Regions
(`./learn solution kilo 09.LL`):

| lesson | regions (file: title) |
|---|---|
| 09.01 | kilo.c: say it in the message line (editorMessage); the prompt (editorPrompt); script.c: say what went wrong; every way in is a protected call; run a file; a line at the prompt; print to the message line; the libraries and the table kilo; a state for the scripts; the init file; at exit |
| 09.02 | kilo.c: get_lines; get_cursor; message; --api-info; script.c: check an argument; an argument as the API's value; the API's value as Lua's; the dispatcher; kilo.api |
| 09.03 | kilo.c: set_lines: check everything first; set_lines: the change; set_lines: the cursor afterwards; set_cursor; save; the cursor after a script |
| 09.04 | kilo.c: a name to a key; set_keymap; del_keymap; feed_key; a mapped key; script.c: call a function kept as a reference; the Lua on top |
| 09.05 | kilo.c: KeyPress; create_autocmd; del_autocmd; an event's functions; TextChanged and CursorMoved |
| 09.06 | kilo.c: create_namespace; add_highlight; clear_namespace; draw the highlights; the status bar |
| 09.07 | kilo.c: leave, once back from the script; input; open; quit |
| 09.08 | script.c: count the memory; a panic; back from a script that went wrong; Ctrl-C stops a script; no os.exit in the editor |
| 09.09 | kilo.c: with no screen (in editorMessage); the editor with no screen; script.c: run a script with no screen |

Not in regions, arriving with `@from`: the limits, each with its lesson;
the trivial functions (line_count, get_name, is_modified, get_changedtick,
set_statusline, get_view, get_size), editorClean, the value helpers
(apiValue, apiInteger, apiPosition, apiFail, apiString, apiFree, apiRange,
apiTypeName, apiKey), editorShowCursor (09.03), KEYNAMES and
editorKeymapSlot (09.04), editorKeyName (09.05), the tables (EVENTS,
STYLES, the autocommands, the namespaces, the highlights), the API table, a
line per lesson's functions; in script.c the reader for files, scriptEval,
scriptRelease, scriptCall and scriptUnref (09.04), SCRIPT_LUA (09.04),
scriptNoExit (09.08); `luaL_newstate()` to 09.07, `lua_newstate()` with
scriptAlloc from 09.08.

### Hooks in core code

Each is one marked line or a small marked block; none is inside 06's or
07's blocks, so core + 09 and the finished file have the same lines.

- `#include "script.h"` (09.01) and `#include "api.h"` (09.02).
- `enum KEY_ACTION`: `CTRL_E = 5` (09.01).
- `struct editorConfig`: `long long changedtick;` (09.05).
- A block of prototypes after editorSetStatusMessage's: editorPrompt
  (09.01), `int editorFed = -1;` and editorScriptKey (09.04), editorEvent
  (09.05), `struct abuf;`, editorDrawHighlights and editorStatusLine (09.06).
- `E.changedtick++;` after `E.dirty++` in editorInsertRow, editorDelRow,
  editorRowInsertChar, editorRowAppendString, editorRowDelChar, and after
  the cut in editorInsertNewline (09.05).
- editorOpen: `editorEvent("BufReadPost");` before each return, the one for
  a file that is not there too (09.05).
- editorSave: `editorEvent("BufWritePre");` before the text is made into a
  string, `editorEvent("BufWritePost");` after a good write (09.05).
- editorRefreshScreen: `editorDrawHighlights(&ab,filerow);` after the row
  (after 07's lspDrawRow block, outside it), and `len =
  editorStatusLine(status,sizeof(status),len);` after the status bar's text
  is made (09.06).
- editorProcessKeypress: the read becomes `int c = editorFed != -1 ?
  editorFed : editorReadKey(fd);` (a 09.04 block nested in 01.02's, the
  core's line as its @else), then `if (editorFed == -1 &&
  editorScriptKey(c)) return;` before the switch, after 08's undoKey(c)
  (09.04); and `case CTRL_E:` the prompt and scriptEval (09.01), after
  08's Ctrl-Z and Ctrl-R. In the finished tree only, 08's `undoKey(c);`
  is `if (editorFed == -1) undoKey(c);` (a 09.04 block nested in 08.03's,
  08's line as its @else), and two small blocks of 08 in editorScriptKey and
  one of 09 in undoSave make a script's change a step of its own (below).
- main: `--api-info` (09.02) and `-l` (09.09) before the argument check;
  two more usage lines (the first unchanged); `scriptStart();` after
  lspStart's place (09.01); `editorEvent("BufReadPost");` after it, and
  `editorAfterKey();` at the top of the loop (09.05).

### With module 08: a script's change is a step of its own

Module 08 was built at the same time on another branch and merged in
after: its undoSave() calls are at the top of the row functions and before
the cut, 09's tick lines next to `E.dirty++`; in editorProcessKeypress its
`undoKey(c)` (which ends the open step at a key of another kind) comes
first, then 09's hook. Because set_lines is built from editorDelRow() and
editorInsertRow(), 08 remembers a script's change with no code for it in
09, and module 07 sends it to the server likewise.

What a step is, when scripts run for a key, was decided here (in the
finished tree only: each part is a block of one module nested in a block of
the other, so it is at no 08 lesson and no 09 lesson):

- **What a key's scripts change is one step of its own.** undoKey() alone
  would glue a script's change to the typing before it when the key a
  script takes is itself a typed character ("x" mapped, or "j" in a vi
  layer: same kind, no new step), and the typing after it to the script's.
  Closing the step before every key offered to a script would split all
  typing into one-key steps whenever a KeyPress function exists. So the
  step ends lazily: editorScriptKey() sets `editorStepBreak` before the
  KeyPress functions and the mapping run, undoSave() closes the open step
  at the scripts' first change (and clears the flag), and editorScriptKey()
  closes the scripts' step when they return, if the changed tick moved.
  A KeyPress function that changes nothing leaves 08's steps as they were.
- **A key a script feeds is part of the script's step**: undoKey() is not
  called for a fed key, so a function that sets lines and feeds "B" and
  Enter is one Ctrl-Z.
- **Ctrl-Z and Ctrl-R can be a script's**, mapped or taken by KeyPress, as
  Ctrl-S can; feed_key("<C-z>") is 08's undo (undo runs with U.off set, so
  it never trips the break).
- Not done: a TextChanged or CursorMoved function's change joins the open
  step (the key's), so one Ctrl-Z takes back the key and what its events
  did; and after an undo, TextChanged fires again.

Tested in 0904 (the finished tree, with 08's own invariant check after
every key, KILO_TEST_UNDO_LOG): set_lines undone by one Ctrl-Z, the cursor
at the step's start, redone by Ctrl-R, the cursor at its end; typing, a
typed key a script takes, typing: three steps; several changes with fed
keys: one step; a row deleted with set_lines and the row now at its index
changed by a fed key (a U_DEL then a U_CHG of the same row, which 08's own
keys never make): one Ctrl-Z puts the text back; Ctrl-Z mapped and Ctrl-R
taken by KeyPress, both feeding the editor's. With editorStepBreak never
set, the test fails ("the script's step alone": the script's change and the
typing before it go together).

### The API as built

`kilo --api-info` (no Lua is started for it: the table is C):

    line_count() -> integer  -- the number of rows in the file
    get_lines(start: integer, end: integer) -> lines  -- the rows [start, end), counted from 0
    get_cursor() -> position  -- the cursor's {row, col}, col a byte of the row
    get_name() -> string  -- the file's name
    is_modified() -> boolean  -- true when the file has unsaved changes
    message(text: string)  -- show text in the message line
    set_lines(start: integer, end: integer, lines: lines)  -- replace the rows [start, end) by lines
    set_cursor(pos: position)  -- move the cursor to {row, col}
    save() -> boolean  -- save the file, as Ctrl-S does; false if that failed
    set_keymap(key: string, fn: function)  -- run fn for key, in place of what the editor does
    del_keymap(key: string)  -- give key back to the editor
    feed_key(key: string)  -- do what the editor itself does for key
    create_autocmd(event: string, fn: function) -> integer  -- run fn on event; returns its id
    del_autocmd(id: integer)  -- stop running an autocommand
    get_changedtick() -> integer  -- a count that goes up with every change to the text
    create_namespace(name: string) -> integer  -- the id of a namespace for highlights; "" makes a new one
    add_highlight(ns: integer, row: integer, start: integer, end: integer, style: string)  -- draw bytes [start, end) of row in style
    clear_namespace(ns: integer)  -- remove the namespace's highlights
    set_statusline(text: string)  -- the status bar's left part; "" for the editor's own
    get_view() -> position  -- the file's {row, col} at the screen's top left
    get_size() -> position  -- the {rows, cols} of text the screen shows
    input(prompt: string) -> string  -- a line typed at the prompt; nil for Escape
    open(path: string)  -- edit the file at path in place of this one
    quit(force: boolean)  -- leave the editor; force: even with unsaved changes

The dispatcher (scriptDispatch, one C function behind every name, its
entry as an upvalue) checks the count, then every argument's type, before
the function runs: an integer is a Lua number with no fraction (2.0 is 2,
"2" is not), a string a Lua string (a number is not), lines a table whose
keys are exactly 1 to #t and every value a string, a position a table of
two integers. Strings are lent to the function (Lua's own bytes, alive while
on the stack), lines get an array of them; a function argument becomes a
reference in Lua's registry (luaL_ref), which the API keeps or, if the
function failed, the dispatcher lets go. What a function returns it
allocated; the dispatcher pushes it in a protected call of its own and
frees it either way, so no memory error between them leaks it. Errors, with
the script's place in front (`luaL_error`, level 1: the Lua caller; none
when the caller is pcall, a C function):

| from | text |
|---|---|
| the dispatcher | `NAME: expected N arguments, got M`; `NAME: argument I (ARG): expected TYPE, got WHAT` (WHAT: Lua's type, `float`, `a table that is not a list`, `a table that is not {row, col}`, `a table with a TYPE at K`); `NAME: not enough memory` |
| get_lines, set_lines | `[S, E) is not a range of the file's N rows` |
| set_lines | `a line cannot hold a newline (line N)` (N from 1, as Lua counts the list) |
| set_cursor | `row R is outside the file (it has N rows)`; `column C is outside row R (it has N bytes)` |
| save | `a save is already going on` (in BufWritePre/Post); `no file name` (kilo -l, no file) |
| set_keymap, del_keymap, feed_key | `unknown key "NAME"`; `<C-q> is the way out: no script can have it` |
| del_keymap | `NAME is not mapped` |
| feed_key | `a save is already going on` (Ctrl-S in BufWritePre/Post); `NAME waits for the keyboard, and there is none` (Ctrl-E, Ctrl-F under -l) |
| create_autocmd, del_autocmd | `unknown event "NAME"`; `too many autocommands (64)`; `no autocommand ID` |
| create_namespace | `too many namespaces (64)`; `not enough memory` |
| add_highlight, clear_namespace | `no namespace N`; `row R is outside the file (it has N rows)`; `[S, E) is not a range of bytes`; `unknown style "X": red, green, yellow, blue, magenta, cyan, bold, underline or reverse`; `too many highlights (10000)` |
| input | `no keyboard` (kilo -l) |
| open | `a save is going on`; `unsaved changes`; `"X" is not a file name` (empty, or with a NUL); `cannot read PATH: REASON` |
| quit | `unsaved changes (quit(true) leaves anyway)` |
| script.c | `interrupted`; Lua's `not enough memory`; `os.exit is taken away in the editor: kilo.api.quit() leaves`; `cannot open PATH: REASON` (a script); `(error object is a TYPE value)`; `lua: cannot start: not enough memory`; at a panic, on standard error, `kilo: Lua panic: MESSAGE` |

Every text is tested except the three "not enough memory" of C
allocations (malloc failing) and "lua: cannot start".

Rows and columns count from 0, a column is a byte, a range is [start,
end); out of range is an error, never clamped (as Neovim with
strict_indexing). Lua's lists count from 1. The cursor may be on the row
past the last, column 0: kilo puts it there itself (Down at the end, an
empty file), so set_cursor takes it and get_cursor gives it.

### Limits

All in script.h, each tested:

| name | value | why |
|---|---|---|
| SCRIPT_PROMPT_MAX | 256 bytes | a line at the "lua: " prompt or input(); the 257th byte is not taken (0901) |
| AUTOCMD_MAX | 64 | autocommands at once (0905) |
| NAMESPACE_MAX | 64 | namespaces (0906); not in the design: each keeps a copy of its name, outside Lua's memory |
| HIGHLIGHT_MAX | 10000 | highlights at once, in all namespaces (0906) |
| SCRIPT_MAX_MEMORY | 64 MB | what Lua may hold (0908) |
| SCRIPT_HOOK_COUNT | 100000 | instructions between looks at the keyboard (0908) |
| (the message line) | 79 bytes | E.statusmsg, then the screen's width (0901, 0908) |

### Invariants, and where each is tested

- No core, 06 or 07 lesson's project changes; no 06/07 code at a 09
  lesson; every 09 project builds with -Werror: the diff and the builds
  above.
- No init file: the screen is the core's, to the byte (0901).
- Every way into Lua is one function, scriptProtected (lua_pcall of a C
  function with a light userdata: neither push needs memory), so an error
  or a memory error always comes back as a status; the panic function is
  reached only by the test aid (0908), never by the fuzz.
- After any script returns to the editor, the cursor is in the text
  (editorScriptReturned, called at the outermost return): 0903 (Page Down
  past a short file, then a script).
- set_lines changes all or nothing (0903).
- Nothing a script writes reaches the terminal as a control byte: messages,
  print, errors, the status line, the prompt of input() (0901, 0902, 0906,
  0907, 0908).
- Ctrl-Q is never offered to a script: the first line of editorScriptKey,
  the one function that offers keys to scripts; set_keymap and feed_key
  refuse it (0904); an init.lua that maps every other key and has a
  KeyPress function taking every key still lets Ctrl-Q quit (0908), and so
  does the end of the editor fuzz.
- No event fires while another's functions run (0905, 0907).
- kilo does not exit, nor close the state, while Lua runs: quit() sets a
  mark read at the top of main's loop (0907); scriptStop leaves the state
  when exit() comes from inside Lua (os.exit under -l: 0909).
- References are let go: 2000 mappings of one key leave the registry's
  count of functions as it was, del_keymap takes one off, a refused mapping
  keeps none (0904).
- Lua's memory is bounded and given back (0908); a runaway script is
  stoppable, in five shapes (0908).
- The API does not know which way it was called: the same trim() with no
  screen and on a key gives the same file (0909).
- Highlights are cut to the row as it is when drawn (0906).

### Departures from the design, and why

- **The second revision is built**, 09.01 to 09.09; 09.10 is not.
- **ApiFunc has the arguments' names** (`argnames`), for --api-info and
  for the errors; API_MAX_ARGS is 5 (add_highlight).
- **NAMESPACE_MAX 64**, a limit the design did not have.
- **Key names: "<xNN>" for any other byte**, both ways. The design's list
  ("<C-a>" to "<C-z>", the named keys, printable characters) leaves bytes
  0, 28 to 31 and 128 to 255 without a name, though "every key
  editorReadKey() returns" includes them (typing a UTF-8 character gives
  two such keys). A byte above 127 comes back from editorReadKey() as a
  negative char on a machine where char is signed; editorScriptKey takes
  its low byte.
- **Ctrl-H is not Backspace here.** The design: "Ctrl-H Backspace's:
  mapping one maps the other". Backspace sends 127 on the terminals kilo
  targets (kilo's own enum, BACKSPACE = 127; the tests send 127), and
  Ctrl-H is byte 8 (which kilo also treats as Backspace). Mapping "<C-h>"
  maps byte 8 only; the Backspace key stays the editor's (0904). "<C-m>" is
  Enter and "<C-i>" is Tab, as the design says.
- **The cursor rule when the range is deleted.** The design: inside the
  range, "the same row or the range's new last row, whichever is higher".
  With no new lines there is no new last row (set_lines(3, 6, {}) with the
  cursor on row 4). Built: the row that took the range's place, or the
  file's last row if none did (0, past the last, for an empty file), as
  Vim's dd leaves it.
- **set_cursor takes the row past the last (column 0)**: see above.
- **BufReadPost for a file that is not there too**, from both of
  editorOpen's returns: open() makes such a file "as on the command line",
  and at start BufReadPost fires once for the first file whatever it is.
  Neovim has BufNewFile for that; kilo has the one event.
- **An event's function gets one string**: the key's name for KeyPress,
  the event's name for the others (Neovim passes a table: id, event, buf,
  match, ...). "Returns true": any value Lua counts as true.
- **TextChanged and CursorMoved are fired by one function, editorAfterKey,
  at the top of main's loop**, before the frame: TextChanged first, then
  CursorMoved; the tick and the place are noted after the functions run.
- **feed_key refuses more than Ctrl-Q**: Ctrl-S inside BufWritePre/Post
  (as save() does), and Ctrl-E and Ctrl-F under -l (they read the
  keyboard: with standard input at its end, editorReadKey() spins for
  ever).
- **Under -l, E has the size of a 24 x 80 terminal** (22 x 80 of text).
  The core's key functions assume a screen: Page Down with 0 rows sets
  E.cy to -1, and the next arrow reads E.row[-1]. Found reading the code
  for feed_key, not seen.
- **A tab in a message shows as a space**; any other control byte as '?'.
  print() joins with tabs, as Lua's does.
- **Chunk names**: the init file and a -l script by their own name
  ("init.lua:3: ..."), the prompt "lua", the Lua on top "kilo.lua".
- **os.exit in the editor is a function that raises** (not nil), so the
  error says why.
- **lua_close at exit, after the terminal is put back**: scriptStop calls
  disableRawMode() first. A finalizer runs with Lua's hooks off (lgc.c,
  GCTM: `L->allowhook = 0;  /* stop debug hooks during GC metamethod */`);
  one that never ends would hang kilo at exit, and with the terminal back
  in its own mode Ctrl-C is SIGINT again and ends it (0908). Before it,
  Ctrl-C is byte 3, and nothing would.
- **Ctrl-C's error is raised again at every instruction** (the hook's
  count set to 1) until the outermost call returns: a script's pcall()
  would otherwise catch "interrupted" and go on (`while true do
  pcall(function() while true do end end) end`, 0908). Its place is level
  0 for luaL_where: a count hook runs inside the function it stops.
- **A full collection after any error** at the outermost return, not only
  after a memory error.
- **luaL_newstate() to 09.07, lua_newstate() with kilo's allocator and
  panic function from 09.08**, the lesson that is about them.
- **open() is refused during a save's events** ("a save is going on",
  checked before "unsaved changes": during a save the file is usually
  unsaved), and input()'s prompt is cleaned and cut to 63 bytes.
- **set_statusline's text is cut so that "row/rows" still fits**, as the
  design says the count stays.
- **The panic aid** is an @internal Lua function, `kilo.test_panic()`,
  which asks scriptProtected to raise once the call has returned, outside
  any protected call.

### Where the design was wrong, or missed a case

- The deleted-range cursor and Ctrl-H, above.
- **The count hook does not stop everything.** Two ways a script hangs the
  editor with Ctrl-C unheard: a finalizer that never ends (hooks are off in
  finalizers, lgc.c above: `setmetatable({}, {__gc = function() while true
  do end end})` hangs the editor at whatever collection runs it), and a
  loop inside one C function, such as a pattern with heavy backtracking:
  `string.find(string.rep('a', n), string.rep('a*', n) .. 'b')` took 0.009
  s at n = 10, 0.118 s at 12, 1.548 s at 14, 23.3 s at 16 (under -l). Kept:
  a script has the user's whole trust, as the design says; the editor can
  be killed from another terminal, and at exit the first case is handled.
- **Recursion without end is not "stack overflow" here**: with the 64 MB
  limit, memory runs out first (`local function f() return 1 + f() end
  f()` gives "not enough memory"); without the limit (the project at 09.07)
  it is "lua:1: stack overflow". Through C (string.gsub calling itself) it
  is "C stack overflow" either way.
- **The count hook costs every instruction, not every 100000th.** With a
  count hook set, Lua's VM takes its slow path for each instruction to
  count it down (lvm.c, `trap`; ldebug.c, luaG_traceexec): an empty loop of
  10 million iterations took 15 ms with no hook (kilo -l) and 22 ms in the
  editor; a call of an empty Lua function 7 ns and 17 ns. lua.c avoids
  that by setting its hook only from the SIGINT handler; kilo cannot, since
  in raw mode Ctrl-C is a byte, not a signal. A timer signal that sets the
  hook while a script runs would do it, with more code: not built.
- **In the finished project, open() does not tell module 07's language
  server** that the file changed: 09 cannot call lsp.c, so the server keeps
  the old file's name and is sent the new file's text as a change to it.
  (07's own jump, Ctrl-G, does it right, and fires BufReadPost through
  editorOpen.) The extensions do not know each other, as 06 and 07 do not.
- feed_key under -l and the size under -l, above.

### How the screens below were captured

With a scratch driver around track.py's `Editor` (no change to the track):
the project at 09.09 (`./learn files kilo --at 09.09`, with lua/ copied in,
built with make), on an 8 x 60 pseudo-terminal (7 x 40 for the vi keys),
KILO_INIT naming the init.lua shown, the cursor `[cursor R,C]` from 1. In
the finished project the screens are the same for a .txt file.

### 09.01 A second language inside the editor: embedding Lua

    -- init.lua: print("hello from init.lua")
    |hello world
    |second line
    |~
    |~
    |~
    |~
    |f.txt - 2 lines                                          1/2
    |hello from init.lua

With `local name = 'kilo'` and `print('hello ' .. nme)` (a typo):

    |init.lua:2: attempt to concatenate a nil value (global 'nme'

(cut at the 60 columns). Ctrl-E shows `lua: `, then `lua: 1+1`; Enter
gives `2` in the message line, the cursor where it was. A statement (`x =
5`) shows nothing; several values are joined with spaces (`10 a nil`); an
error is `lua:1: attempt to call a nil value (global 'nosuch')`.

### 09.02 The API is a table

    lua: kilo.api.line_count()                       -> 2
    lua: kilo.api.get_lines(0, 2)                    -> table: 0x950c04400
    lua: table.concat(kilo.api.get_lines(0, 2), ' | ')
                                                     -> hello world   | second line
    lua: kilo.api.get_lines(0, 5)                    -> lua:1: get_lines: [0, 5) is not a range of the file's 2 rows
    lua: kilo.api.get_lines('a', 1)                  -> lua:1: get_lines: argument 1 (start): expected integer, got string

(A table is shown as Lua's tostring() shows it; the lesson can use
table.concat. The trailing spaces of "hello world  " are the row's.)

### 09.03 Changing the text from a script: set_lines

The cursor on row 2, column 3 (1-based), then `kilo.api.set_lines(0, 0,
{'-- a header, from a script'})`: the row goes in above, the cursor stays on
its line, now row 3:

    |-- a header, from a script
    |hello world
    |second line
    |~
    |~
    |~
    |f.txt - 3 lines (modified)                               3/3
    |
    [cursor 3,3]

`kilo.api.set_lines(0, 1, {'a', 'b\nc'})`: `lua:1: set_lines: a line
cannot hold a newline (line 2)`, and nothing changed. The cursor rule, as
0903 checks it on rows line0..line9 (cursor before -> call -> cursor
after): (1,3) 5,7,{'x'} -> (1,3); (8,2) 2,5,{} -> (5,2); (8,2)
2,3,{'a','b','c'} -> (10,2); (6,4) 3,8,{'x','y'} -> (4,1); (4,3)
3,5,{'p','q','r','s'} -> (4,1); (5,4) 5,6,{'Z'} -> (5,1); (4,2) 3,6,{} ->
(3,2); (8,4) 7,10,{} -> (6,4); (5,1) 0,10,{} -> (0,0); (2,2)
0,0,{'-- header'} -> (3,2); (9,1) 10,10,{'end1','end2'} -> (9,1); (10,0)
9,10,{'x','y'} -> (11,0).

### 09.04 Any key can run a Lua function

The lesson's two, in init.lua:

    kilo.keymap.set('<C-d>', function()
      local row = kilo.api.get_cursor()[1]
      local line = kilo.api.get_lines(row, row + 1)[1]
      kilo.api.set_lines(row + 1, row + 1, {line})
    end)
    kilo.keymap.set('<C-t>', function()
      local row = kilo.api.get_cursor()[1]
      local line = kilo.api.get_lines(row, row + 1)[1]
      if line:sub(1, 3) == '-- ' then line = line:sub(4) else line = '-- ' .. line end
      kilo.api.set_lines(row, row + 1, {line})
    end)

On "local x = 1 / print(x)": Ctrl-D gives `local x = 1` twice (the cursor
stays on row 1); Down, Ctrl-T gives `-- local x = 1` on row 2; Ctrl-T again
takes it back. The Lua on top (SCRIPT_LUA in script.c, 19 lines):
kilo.keymap.set takes a key or a list of keys and calls set_keymap for
each; kilo.lines() is an iterator, `for row, line in kilo.lines()`, rows
from 0, over the file as it was when the loop began. A mapped Ctrl-S that
still saves: `kilo.api.set_keymap('<C-s>', function() ... 
kilo.api.feed_key('<C-s>') end)` (0904).

### 09.05 Events: autocommands

The lesson's two (trailing spaces trimmed before a save; the words counted
as you type), on "hello world  / second line\t": typing "a " gives `5
words` in the message line; Ctrl-S saves `a hello world\nsecond line\n`
(the spaces and the tab gone) and says `25 bytes written on disk`... then
the message is the save's? No: the screen shows `5 words` after Ctrl-S,
since TextChanged fires after the key (the trim changed the text) and its
function says the count after the save's own message. The order around a
save, from 0905: `BufWritePre true BufWritePost false` (is_modified() in
each). A function that fails is said (`lua:1: post failed`) and the next
runs; the file is written.

### 09.06 Drawing from a script: highlights and the status bar

Every number on the screen in red (the init.lua of 0906, NUMBERS: on
BufReadPost, TextChanged and CursorMoved, clear the namespace and add a
highlight for each `%d+` in the rows get_view() and get_size() say are
shown):

    |int width = [r:640];
    |int height = [r:480];
    |print(width * height * [r:3]);

Row 0 as kilo sends it: `int width = 640;ESC[0K \r ESC[12C ESC[31m 640
ESC[0m` (spaces added here): the core's row, then the highlight drawn over
it, as module 07's underline is. `kilo.api.set_statusline('3 numbers | '
.. kilo.api.get_name())`:

    |3 numbers | f.txt                                        1/3

### 09.07 Asking, opening, leaving: input(), open(), quit()

Go to a line on Ctrl-O (GOTO in 0907): Ctrl-O, "30" shows `Go to line: 30`
in the message line; Enter puts the cursor on line 30 (the view scrolled
to show it, line 25 to 30 on the 6 rows, the bar `30/40`). quit(true) in
a line at the prompt: the rest of the line still runs (it wrote a file),
then kilo exits 0 and the terminal is put back.

### 09.08 Scripts that go wrong

`kilo.api.set_keymap('<C-t>', function() while true do end end)`: Ctrl-T,
a second later Ctrl-C: `init.lua:2: interrupted`; the frame came 170 ms
after Ctrl-C, of which the driver's own wait for quiet is 150 ms: the hook
runs every 100000 instructions, about 0.2 ms here. What each hostile
script did before its guard (the project at 09.07, which has no 09.08
code) and after (09.09):

| script | at 09.07 | from 09.08 |
|---|---|---|
| `while true do end` at the prompt, then Ctrl-C | still running after 3 s (the process killed) | `lua:1: interrupted` at once |
| the same inside `pcall`, or in a coroutine | (as above) | `lua:1: interrupted`; `lua:1: lua:1: interrupted` (coroutine.wrap puts its place in front) |
| `#string.rep('x', 200 * 2^20)` | `209715200`; collectgarbage('count') after: 212642 KB | `not enough memory`; 1584 KB after |
| a table grown for ever | (not run: it would take the machine's memory) | `not enough memory` after 51468 strings of 1 KB; 87 KB after the collection |
| `local function f() return 1 + f() end f()` | `lua:1: stack overflow` | `not enough memory` |
| `local function f(s) return (s:gsub('.', f)) end f('ab')` | `C stack overflow` | `C stack overflow` |
| `os.exit(0)` with a change unsaved | kilo exits 0, the change lost | `lua:1: os.exit is taken away in the editor: kilo.api.quit() leaves` |
| `print("\27[2J")`, any control byte | (from 09.01) `?[2J` | `?[2J` |
| `kilo.test_panic()` (the aid) | (luaL_newstate's panic: a line on standard error, then abort(), the terminal left raw) | `kilo: Lua panic: a panic, on purpose`, status 1, the terminal put back |
| a KeyPress function that takes every key | (not before 09.05) | Ctrl-Q still quits |
| a finalizer that never ends, at Ctrl-Q | (terminal put back first from 09.01) | hangs, the terminal back; Ctrl-C ends kilo (SIGINT) |

### 09.09 The editor without its screen

    $ ./kilo -l upper.lua notes.txt          (hello / World / 123)
    2 lines upper-cased                      (status 0; notes.txt: HELLO / WORLD / 123)
    $ ./kilo -l bad.lua notes.txt            (set_lines, then get_lines(0, 99))
    bad.lua:2: get_lines: [0, 99) is not a range of the file's 3 rows
                                             (status 1, on standard error; nothing saved)

print() and message() write their bytes as they are (control bytes too:
no terminal is being drawn); os.exit(3) gives status 3; input() is
`input: no keyboard`; keys fed go to a 22 x 80 view; an event's failing
function is a line on standard error and the script goes on.

### Measurements

On the Mac (Apple M-series, Apple clang 21):

- The binary: the core at 05.02 53320 bytes (52304 stripped); core + 09 at
  09.09 337672 (311104 stripped): Lua and module 09 add about 284 KB.
  liblua.a is 401200 bytes.
- Start: `kilo --api-info` (no Lua) median 2.40 ms, `kilo -l empty.lua`
  (a state, the libraries, kilo.api, the Lua on top, an empty script) 2.60
  ms, of 50 runs each; a 100-line script 2.7 ms. In the editor, spawn to
  first frame is about 64 ms with no init file, an empty one or 100 lines
  (the median of 15 runs each, 42 to 62 ms the least): the tests' Python
  wrapper that makes the terminal the controlling one is most of it.
- An API call from Lua (a million, os.clock()): line_count 34 to 42 ns,
  get_lines(0, 1) 192 to 203 ns (a table and a string made), an empty Lua
  function 7 ns.
- The count hook: an empty loop of 10 million iterations, best of 5, three
  runs: 14.8 to 15.7 ms with no hook (kilo -l), 21.7 to 23.9 ms in the
  editor (hook on); an empty function call 6.8 to 7.3 ns and 16.9 to 18.6
  ns. See "Where the design was wrong".
- The fuzz (below) runs 5000 calls in 0.6 s under ASan and UBSan with no
  screen.

### Found on the way

1. **The hook's error had no place.** luaL_error() in a count hook says
   where level 1 is, the function's caller (C, so nothing): "interrupted"
   alone. Level 0 is the function the hook stopped: `init.lua:2:
   interrupted` (0908).
2. **open() said "unsaved changes" inside BufWritePre**, where "a save is
   going on" is the reason (the file is unsaved during most saves). The
   order of the checks swapped (0907).
3. **A long set_statusline text hid the row count**: the core's bar writes
   "row/rows" only where it fits after the left part. Cut to leave room
   (0906).
4. **string.rep's own limit**: string.rep('x', 2^40) is "resulting string
   too large" (lstrlib, at 2^31 bytes), not a memory error; 0908 asks for
   2^30 to reach the allocator.
5. **Undefined behaviour in module 06, found by the fuzz on Debian.**
   editorUpdateSyntax() does `row->hl = realloc(row->hl,row->rsize);` and
   then `memset(row->hl,HL_NORMAL,row->rsize);`: for an empty row, glibc's
   realloc(p, 0) frees and gives NULL, and memset() with a NULL pointer is
   undefined even for 0 bytes. UBSan stops there (`kilo.c:547:5: runtime
   error: null pointer passed as argument 1, which is declared to never be
   null`, from editorDelChar through editorUpdateRow) when the fuzz feeds
   Backspace until a row is empty; typing the same does it, in any file of
   the finished tree. macOS's realloc never gives NULL there. Harmless in
   practice (nothing is written), and NOTES's 06 section already says the
   search checks row->hl for the NULL. Not changed: it is 06's code, and
   its lessons must not change. The fuzz suppresses that one report by name
   (tests/api_fuzz.py, UBSAN_SUPPRESSIONS). 06's tests run ASan, not UBSan.
6. **10000 highlights on one row make a frame of some 150 KB**: each is
   drawn over the row in turn. Under ASan in Docker that was slow enough
   for 0906's prompt to outrun the test's wait for a quiet screen; the test
   clears them in the same line now. Kept: HIGHLIGHT_MAX bounds it.
7. No bug in the core, in 07 or in 08 was found. All earlier tests (the 28
   to 07.07, and 08's 4) pass on the finished tree, which has 09 in it.

### Kept simple, and the frontier

- One state for the whole run; one init file; scripts trusted (io,
  os.execute, io.read on the keyboard left as they are, as a Neovim
  plugin's are).
- A mapped key does not reset the Ctrl-Q count (a mapped key returns before
  the switch).
- The prompt shows what fits of the line in the message line, as find's
  does; bytes above 127 are not taken there.
- A highlight is a row and bytes, drawn after the row; it does not move
  with the text. A script puts its highlights again on TextChanged (which
  fires before the frame). In the finished project a highlight is drawn
  over 06's colours, and over 07's underline where they meet.
- Highlights are not cleared by open() or by 07's jump: a script clears its
  namespace on BufReadPost.
- The frontier, not built (the design's): no timers and no work in the
  background (one loop would have to own all the waiting, as libuv does in
  Neovim; 07's poll() and a timer here could not know of each other); one
  file at a time (E is one file: no buffers, no windows); highlights that
  do not move when the text does (Neovim's extmarks do); no floating
  windows or menus.

### For 09.10: does the API reach the three proofs

- **A modal layer of vi keys**: yes. A KeyPress function (created first, so
  it runs first) takes the keys of "normal" mode, moves with feed_key or
  set_cursor, edits with set_lines, gives keys back by returning false;
  Escape and i switch modes (0905 does j, k, i and x). A mode in the status
  bar with set_statusline. Missing for the full thing: nothing essential;
  the cursor's shape cannot change, and there is no visual selection
  drawn but by highlights.
- **Colouring as module 06 does it**: yes, by highlights over the visible
  rows, again on BufReadPost, TextChanged and CursorMoved (0906 colours the
  numbers). Comments over many rows need the rows above the view read on
  each change (get_lines(0, top)), so the cost grows with the file; and a
  highlight's styles are the 8 colours and bold, underline, reverse, as
  06's are.
- **A find**, or go to a line: go to a line, yes (0907). Find: a one-shot
  find (input(), then set_cursor and a highlight) yes; find as you type, as
  the core's, by a KeyPress layer that collects the query and shows it with
  message() or set_statusline, yes. Missing: a way to set the view, so
  that Escape puts back the exact view find started from (the core's
  saves rowoff and coloff; a script can put the cursor back, and the view
  follows only as little as shows it), and putting the match's row at the
  top of the screen as the core's find does. A `set_view(position)` would
  close it.

### The notable editors

This subsection is filled in from the coordinator's research for module 09;
what follows was confirmed while the code was built, and is kept as it is.

Read on 2026-11-24, by fetching each file or page at the tag or commit
named (the research was done for this section; quotes are exact, a
non-ASCII character in one replaced by its ASCII equivalent). Neovim is at
**v0.12.6** (released 2026-10-09, commit
779c36969e31080503be2dfccbcc3f999e289606) unless another tag is named;
URLs are `https://raw.githubusercontent.com/neovim/neovim/v0.12.6/PATH`.

**Neovim, against the design's guesses:**

- **Indexing** (runtime/doc/api.txt, api-indexing): "Most of the API uses
  0-based indices, and ranges are end-exclusive." "Negative indices are
  interpreted as length+1+index: -1 refers to the index past the end."
  "Out-of-bounds indices are clamped to the nearest valid value, unless
  `strict_indexing` is set." The cursor: "Sets the (1,0)-indexed cursor
  position (byte offset) in the window" (nvim_win_set_cursor). So the
  design's guess holds: rows from 0, end-exclusive, a cursor counting rows
  from 1; kilo's cursor counts rows from 0, and kilo never clamps.
- **nvim_buf_set_lines** (src/nvim/api/buffer.c): checks first
  (`VALIDATE((!strict_indexing || !oob), "%s", "Index out of bounds", {`,
  `VALIDATE((start <= end), "%s", "'start' is higher than 'end'", {`; a
  newline in an item is an error for Lua and RPC callers,
  src/nvim/api/private/validate.c: `"'%s' item contains newlines"`); saves
  for undo before any change (`if (u_save_buf(b, (linenr_T)(start - 1),
  (linenr_T)end) == FAIL) {`); then marks (mark_adjust_buf, extmark_splice)
  and the tick (`changed_lines(b, (linenr_T)start, 0, (linenr_T)end,
  (linenr_T)extra, true);`, which reaches `buf_inc_changedtick(buf);` in
  change.c).
- **The cursor after set_lines differs from kilo's.** Neovim's fix_cursor
  keeps a cursor inside the replaced range on the same line number, and
  only clamps it to the last line when lines were deleted (`} else if
  (extra < 0) { check_cursor_lnum(win); }`); below the range, `lnum +=
  extra`. kilo's (the design's) moves a cursor inside the range up to the
  range's new last row when the range shrank.
- **set_lines is not "the function the others are built from".**
  nvim_buf_set_text is its own implementation of the same steps, and says
  so: "unlike set_lines, we want to save the undo state of one past the
  end_row, since end_row is inclusive." The only callers of
  nvim_buf_set_lines found in src/nvim/api/*.c are the deprecated wrappers
  in deprecated.c (buffer_insert, buffer_set_line, ...).
- **The types** (src/nvim/api/private/defs.h): `kObjectTypeNil = 0,
  kObjectTypeBoolean, kObjectTypeInteger, kObjectTypeFloat,
  kObjectTypeString, kObjectTypeArray, kObjectTypeDict, kObjectTypeLuaRef`
  (and Buffer, Window, Tabpage); `typedef struct { ErrorType type; char
  *msg; } Error;`; and in src/nvim/types_defs.h, `typedef int LuaRef;`.
- **The generator**: src/gen/gen_api_dispatch.lua reads the api headers
  (api.txt: "parses headers in src/nvim/api/* and generates
  dispatch-functions mapping RPC API method names to public C API
  functions, converting/validating arguments and return values") and
  writes the RPC wrappers (each checks "Wrong number of arguments" and
  "Wrong type for argument"), the Lua bindings (`static int
  nlua_api_<name>(lua_State *lstate)`, put into `vim.api` by
  `lua_setfield(lstate, -2, "api");`), and the metadata that
  src/gen/gen_api_metadata.lua packs and `nvim --api-info` prints
  ("Print msgpack-encoded |api-metadata| and exit", starting.txt). kilo
  writes its table by hand, and --api-info prints text.
- **Lua in Neovim** (src/nvim/lua/executor.c): `lua_State *lstate =
  luaL_newstate();` and `luaL_openlibs(lstate);` in nlua_init; a function
  becomes a LuaRef in nlua_ref (`LuaRef ref = luaL_ref(lstate,
  LUA_REGISTRYINDEX);`); nlua_call_ref calls one later, through nlua_pcall
  ("Like lua_pcall, but use debug.traceback as errfunc."); errors go to
  nlua_error ("Converts a Lua error into a Vim error message"), e.g. `"E5108:
  Lua: %.*s"`. The language is 5.1: "Lua 5.1 is the permanent interface for
  Nvim Lua", built with LuaJIT where it can be (lua.txt). kilo's is 5.4;
  what the lessons use is the same in both but integers (5.4 has them, 5.1
  has only doubles: converter.c makes a whole number an Integer).
- **converter.c**: nlua_pop_Object and nlua_push_Object; a table is an
  Array when its keys are 1 to n, a Dict when all are strings, else
  "Cannot convert given Lua table".
- **vim.keymap.set is Lua** (runtime/lua/vim/keymap.lua):
  `vim.api.nvim_set_keymap(m, lhs, rhs, opts)` and
  `vim.api.nvim_buf_set_keymap(buf, m, lhs, rhs, opts)`, as the design
  supposed; kilo.keymap.set is the same idea in 3 lines.
- **Starting** (starting.txt): `-l {script}` "Executes Lua {script}
  non-interactively (no UI) ... then exits. Exits 1 on Lua error."; and it
  makes print() write to output. `--headless`: "Start without UI". The
  order: step 3 "Buffers are created for all files (but not loaded yet).",
  step 8 "Load user config ...", step 18 "Buffers for all windows will be
  loaded": **Neovim runs init.lua before it reads the files**; kilo reads
  the file first, so init.lua can see it, and fires BufReadPost once after.
- **The UI as a client**: since Neovim 0.9 (news.txt at v0.9.5): "The
  |TUI| is changed to run in a separate process (previously, a separate
  thread was used)." tui.txt (v0.12.6): "Nvim has a client-server
  architecture: by default when you run `nvim`, this starts the builtin UI
  client, which starts a `nvim --embed` server (child) process that the UI
  client connects to." kilo's screen is in its own process; only the API
  is shared by the editor and -l.
- **b:changedtick** (vimeval.txt): "The total number of changes to the
  current buffer. It is incremented for each change. An undo command is
  also a change in this case." kilo's tick goes up in each row function.
- **Nesting** (autocmd.txt): "By default, autocommands do not nest. For
  example, if you use ":e" or ":w" in an autocommand, Vim does not execute
  the BufRead and BufWrite autocommands for those commands." In autocmd.c
  such an event is skipped, not queued (`if (autocmd_busy && !(force ||
  autocmd_nested)) { goto BYPASS_AU; }`), as in kilo. Event names in Neovim
  are case-insensitive ("Names are case-insensitive."); kilo's are exact.
- **TextChanged, CursorMoved** (normal.c): the tick is noted after the
  autocommands, so a callback's own change does not fire it again
  (`apply_autocmds(EVENT_TEXTCHANGED, NULL, NULL, false, curbuf);` then
  `curbuf->b_last_changedtick = buf_get_changedtick(curbuf);`), and
  CursorMoved compares the cursor's position with the last one, as kilo's
  editorAfterKey does. Which of the two Neovim checks first was not read.
- **Stopping a Lua script: Neovim does not.** executor.c has no
  lua_sethook; issue #6800, "Lua: interrupt / ctrl-c / cancel Lua code",
  is open (fetched): "if you write an endless loop inside `:lua` then it
  can't be interrupted." kilo's count hook is Lua's own lua.c's idea, and
  Redis's (below).
- **Highlights** (api.txt): nvim_create_namespace "If `name` matches an
  existing namespace, the associated id is returned. If `name` is an empty
  string a new, anonymous namespace is created." (as kilo's);
  nvim_buf_set_extmark with `end_col` and `hl_group`;
  nvim_buf_clear_namespace; nvim_buf_add_highlight is deprecated (API
  level 13). Extmarks move with the text (extmark.c: "Marks sit in a
  MarkTree datastructure which provides both efficient mark
  insertations/lookups and adjustment to text changes."); kilo's do not.
- **Keys**: vim.on_key sees every key "after mappings have been applied but
  before further processing", and since 0.11 "callbacks can consume the
  key by returning an empty string" (news-0.11.txt). kilo's KeyPress runs
  before the mappings, and returning true takes the key. nvim_feedkeys with
  mode 'n' ("Do not remap keys") is feed_key's nearest.
- **Asking, opening, leaving**: vim.ui.input's default calls vim.fn.input
  and gives nil "if the user aborted the dialog" (ui.lua); `:edit` with
  changes is E37 "No write since last change (add ! to override)"; `:q[uit]!`
  "Quit without writing, also when the current buffer has changes."

**The others:**

- **Vim** (v9.2.1398, runtime/doc/usr_41.txt): "The Vim script language is
  used for the startup vimrc file, syntax files, and many other things."
  Neovim's own docs on what it changed (v0.12.6): "Nvim exposes a powerful
  API that can be used by plugins and external processes via |RPC|, |Lua|
  and Vimscript" (api.txt); "Extensibility is a primary goal of Nvim. Any
  programming language may be used to extend Nvim without changes to Nvim
  itself." (remote_plugin.txt).
- **Emacs** (GNU Emacs Lisp Reference Manual, read 2026-11-24): "Most of
  the GNU Emacs text editor is written in the programming language called
  Emacs Lisp." (Introduction); "Lisp primitives are Lisp functions
  implemented in C. The details of interfacing the C function so that Lisp
  can call it are handled by a few C macros." (Writing Emacs Primitives,
  https://www.gnu.org/software/emacs/manual/html_node/elisp/Writing-Emacs-Primitives.html),
  the macro being `DEFUN (lname, fname, sname, min, max, interactive, doc)`.
  The other design: the editor mostly in its extension language, C only for
  the primitives.
- **Zed** (v1.29.3, commit d01b134cddf5e4f71964deb2d6f81cdb38fcf1e7):
  "Procedural parts of extensions are written in Rust and compiled to
  WebAssembly." (zed.dev/docs/extensions/developing-extensions). The API is
  WIT, crates/extension_api/wit/since_v0.8.0/extension.wit: `world
  extension {` with exports such as `language-server-command`,
  `run-slash-command`, `context-server-command`, and imports such as a
  worktree's `read-text-file`. Capabilities (`process:exec`,
  `download_file`, `npm:install`) are granted by the user. No function in
  the WIT files read edits a buffer or draws in the editor (github.wit was
  not read).
- **VS Code** (https://code.visualstudio.com/api/advanced-topics/extension-host,
  read 2026-11-24): "The **Extension Host** is responsible for running
  extensions." "VS Code aims to deliver a stable and high performance
  editor to users, and misbehaving extensions should not impact the user
  experience. The Extension Host in VS Code prevents extensions from:
  Impacting startup performance / Slowing down UI operations / Modifying
  the UI". There can be several hosts (local, remote, web).
- **Redis** (tag 8.12.0, commit 215f2e33da9dfb2e0783cdd3a7acd29f8f6e9dd2):
  deps/lua is `"Lua 5.1.5"`; src/script_lua.c stops a slow script with a
  count hook, the same count as kilo's:
  `lua_sethook(lua,luaMaskCountHook,LUA_MASKCOUNT,100000);` ("This is the
  Lua script "count" hook that we use to detect scripts timeout."), and
  once a script is killed re-arms it "so the user will not be able to
  catch the error with pcall", as kilo does. Redis does not stop a slow
  script by itself; it serves other clients and lets an operator kill it.
  Why Lua (redis.io, eval-intro): "Lua lets you run part of your
  application logic inside Redis."
- **Helix** (25.07.1): no plugin system in a release; a Scheme one (Steel)
  is an open pull request, #8675 (fetched).

| editor | extension language | where it runs | what the API is |
|---|---|---|---|
| kilo (09) | Lua 5.4 | in the editor's process | 24 C functions in a table, given to Lua by one dispatcher |
| Neovim | Lua 5.1 (LuaJIT), Vimscript; any, as a remote plugin | Lua and Vimscript in the editor's process; remote plugins and the UI in other processes | C functions with typed Objects, a generated table serving Lua, msgpack-RPC and --api-info |
| Vim | Vimscript | in the editor's process (not read in a source) | the language's functions and commands |
| Emacs | Emacs Lisp | in the editor's process, by its own interpreter | a Lisp: most of the editor is Lisp, C primitives by DEFUN |
| Zed | Rust (or any) compiled to WebAssembly | a sandbox in the editor's process, with capabilities | WIT interfaces |
| VS Code | JavaScript or TypeScript | another process (the extension host), or a web worker | the extension API (not read here) |
| Redis (not an editor) | Lua 5.1 | in the server's process | redis.call and its kin |

**Not confirmed** (kept out of the lessons): that nothing else in
Neovim's C tree calls nvim_buf_set_lines (only the api files were read);
the release in which the TUI became a process rests on the 0.9 news line
alone; that Ctrl-C cannot stop `:lua while true do end` was read from the
source and the open issue, not run; which of TextChanged and CursorMoved
Neovim checks first; Vim's process model (no Vim source read for it); VS
Code's pages do not say "separate process from the window" in those words;
Zed's github.wit was not read.

## Other behaviour of the original, kept

- kilo does not clear the screen on exit: the shell prompt appears where
  the cursor was, over the last screen.
- If standard input is not a terminal, `enableRawMode` fails and main
  ignores it; `editorReadKey` then spins on end of file.
- The SIGWINCH handler draws the screen from inside the signal handler
  (realloc, free and write in a handler; departure 33 says which calls are
  safe there). A second resize waits while the handler runs, but a resize
  while the main loop is in the middle of a frame, or of any realloc, is
  not guarded against. Making it safe would mean a flag set in the handler
  and the drawing done from the loop: a change of structure, not of a line.
- Page Down on a file shorter than the screen puts the cursor on the
  bottom line, below the end of the file; typing there adds empty rows.
- After an escape sequence kilo does not know (Insert, `ESC [ 2 ~`; F1,
  `ESC O P`), `editorReadKey` goes round its loop with the key still ESC
  and reads two more bytes as if a new sequence had begun: whatever
  arrives within the next 0.1 s is taken as that sequence and lost.
  Verified at 01.02: Insert then `a` at once, or 50 ms later, prints only
  `27`; so do Insert then `abc` at once, and Insert then Up 50 ms later;
  `a` 300 ms later prints `27` and then `97 ('a')`. In the finished
  editor, Insert followed at once by `x` puts no `x` in the text. And
  since the key comes back as ESC, Insert in the search prompt ends the
  search as Escape does, cursor and view put back. 01.02 says the first
  part ("One cost of going round").

## The tests and the timeline

The tests drive the reference on a pseudo-terminal (24x80 unless said),
made kilo's controlling terminal so Ctrl-C would really be SIGINT and a
resize really sends SIGWINCH. `Screen` (track.py) is a small VT100
subset: it moves, erases, wraps, scrolls, tracks reverse video, and
answers `ESC [ 6 n`. One assumption worth knowing: as on a VT100, a row
written to the last column leaves the cursor there, and the `ESC [ 0 K`
that kilo sends next erases that last column; the tests do not depend on
that column.

`./learn check-timeline kilo` runs each lesson's project through the
relay at the end of track.py (a pseudo-terminal of 24x80 on a 40-line
learn.txt) and checks its screens step by step: the key codes at 01.0x,
the welcome and a resize at 02.01, the file, moves, page keys, tabs,
status bar, typing, Enter, Backspace, the quit warning, saving and search
at the later lessons, and that keys whose lesson is ahead change nothing.
After the run, learn.txt must be untouched before 04.04 and saved with
the edits from 04.04 on.

For module 06, `Screen` also keeps each cell's foreground colour (ESC [
30 m to 37 m, 39 m for the default, 0 m resetting it with reverse video),
`Screen.colors()` gives a letter per character, and the tests read
`ed.colors(n)`, `ed.color(n, text)` and `ed.painted(n)` (the `[c:text]`
notation above). `edit(..., asan=True)` runs kilo built with
`-fsanitize=address` into the test's scratch directory, where the compiler
can (Apple clang; gcc with libasan, as in Debian): a memory error then
stops kilo with a report, which is how departures 19, 22 and 23 show in
the tests. Where it cannot (gcc on musl), the plain build runs and those
checks see only what the screen shows. The 0603 test also opens a C file
of 100000 rows (about a second).

From 06.01 the timeline runs the project on `learn.c` (TIMELINE_C_TEXT: a
comment over three rows with a blank one, a string, a // comment,
numbers, keywords and a Ctrl-A) instead of learn.txt, when its kilo.c has
`editorSelectSyntaxHighlight` in it, and checks the relay's `colors` dump:
each lesson's classes coloured and the later ones still plain; from 06.03,
// typed in front of the comment's opening ends it for the rows below and
two Backspaces bring it back; at 06.05, Ctrl-F 42 colours the match blue
over the number's red and Escape puts the red back. learn.c must be
untouched after the run (nothing there saves).

On Linux with glibc (Debian trixie, gcc 14, aarch64, in Docker) the 02.01
test and the timeline at 02.01 and 03.04 failed, before module 06 and
with it: kilo exited with status 1 on the first resize. The cause was in
the core (departure 33), not in module 06. Since that fix the tests (21),
the skeleton check and the timeline check all pass there, module 06
included (with ASan), and every lesson's project builds without
warnings. To run them in a container, copy the tree in without the
host's `tracks/kilo/kilo`: a macOS binary newer than kilo.c is kept by
make, and every test then fails at once.

For module 07 (all of this in track.py and tests/, none of it in a
project a reader sees):

- `edit(..., lsp=None)`, the default, sets KILO_LSP to the empty string,
  so the 21 earlier tests run the finished editor with no server even on
  .c files, as before the module. `lsp="..."` runs the scripted server,
  `lsp="table"` leaves KILO_LSP out (clangd for a C file), `lsp="env"`
  takes it from the test.
- tests/lsp_server.py, the scripted server (Python, standard library
  only): kilo runs it through a one-line script track.py writes
  (`scripted-lsp`, a `#!` line naming this Python, so nothing sits between
  them). By default it is a tiny language server: "oops" is an error,
  "meh" a warning, the definition of a name is its first `int NAME`,
  positions in the encoding it chose (utf-8 when offered first, as
  clangd; a scenario can force utf-16 or leave it out). A scenario is a
  Python file the test writes: `on_message(srv, msg)` and `srv` settings,
  with `srv.raw`, `srv.pieces`, `srv.frame`, `srv.reply`, `srv.notify`,
  `srv.die`. It logs every message it gets, with times, and the
  descriptors it was started with, and the signals it started with
  blocked; it exits on end of input, and on its
  own when kilo has gone or after 120 s.
- Screen keeps underline (ESC [ 4 m, 24 m and 0 m end it) per cell:
  `ed.under(n)` paints underlined runs `[_:text]`, `ed.underlined(n)` lists
  the underlined columns (a space past the end of a line too). With
  `utf8=True` a UTF-8 character is one cell, as on a real terminal (only
  module 07's tests of non-ASCII text use it).
- Replies come when they come: `ed.wait_for(cond, what)` reads the screen
  until cond holds (at most 10 s), `ed.wait_said(text)` waits for a
  message line that may since have been replaced; there is no sleep
  standing in for an answer.
- `edit(..., asan=True)` compiles kilo.c with lsp.c and json.c when they
  are there. The hostile cases of 0702 to 0707 run under it; on musl (no
  ASan for gcc) they run the plain build.
- tests/lsp_fuzz.c: 0702 runs its "frames" mode, 0703 "json", 0706
  "messages", 3 s each, built with `-fsanitize=address,undefined` (and
  leak checks on Linux), or ASan alone, or no sanitizer, whichever the
  compiler takes: on Alpine with gcc, none.
- clangd: 0706 and 0707 end with clangd on the sample program where
  `clangd` is on PATH. Where it is not, the test prints a line before its
  PASS, `   07.06  skipped: with clangd (not installed): ...`: the harness
  has no SKIP, so the lesson reads PASS for the parts that ran. clangd was
  installed on every machine these were run on (macOS, Debian, Alpine);
  with it deleted from the Debian container, 0706 and 0707 printed
  `   07.06  skipped: with clangd (not installed): an error typed,
  underlined, fixed` and `   07.07  skipped: with clangd (not installed):
  definitions in the same file and in add.h`, and passed.
- The timeline at 07.01 to 07.07 runs the project on learn.c
  (TIMELINE_LSP_TEXT) with the scripted server, never clangd, so it is the
  same on any machine: the message each lesson's code leads to (started,
  the raw reply, ready, the counts), the cursor past a tab, typing and
  Backspace from 07.05, the error underlined and its message with the
  cursor on its row from 07.06 (the first screen, the cursor on a row with
  none, shows the counts), Ctrl-G, Ctrl-B and Ctrl-B again at 07.07. The relay's
  `until REGEX` waits for what the server causes (under four parallel jobs
  the scripted server can take longer than the 0.4 s of quiet "screen"
  waits for). timeline_after checks learn.c untouched and the scripted
  server's log: nothing received at 07.01, initialize alone to 07.04, then
  initialized, didOpen with the text, version 1, and a didChange at each
  pause, versions 2 and 3, whole.
- Running in a container as above: the module's tests, the skeleton and
  timeline checks pass on Debian trixie (glibc 2.41, gcc 14.2, clangd
  19.1.7) and Alpine 3.22 (musl, gcc 14.2, clangd 20.1.8), and every 07
  project and the finished one builds there with `-Werror`.

For module 08 (the test aids `@internal` in kilo.c, the rest in track.py
and tests/):

- `undo_env(t, max_bytes=None)` gives an environment for `edit(...,
  env=...)` and a log path: with KILO_TEST_UNDO_LOG set, kilo counts its
  history again after every key and appends `bytes N undo N redo N records
  N saved N open N` to the log (`undo_counts(log)` reads it, a dict a key),
  and exits with status 4 when the count is not U.bytes; KILO_TEST_UNDO_MAX
  sets the bound in bytes. A record applied to a row not in the file exits
  with status 4 too. None of this is in a project a reader sees.
- 0801 and 0802 undo and redo each kind of edit on a fresh editor and
  check the rows, the cursor and the file saved after; 0801 also has the
  two checks with other modules (06's colours after the undo of a line that
  opened a comment; 07's scripted server sent the text as the undo left
  it). 0803 counts steps and records through the log. 0804 has the saved
  point, the bound made small, and the random runs under ASan (about 40 s of
  the module's 100 or so).
- The timeline at 08.01 to 08.04 runs the core's steps first (05.02's, on
  learn.txt) and then the module's: the history they leave ("a", "b", "c",
  Enter, two Backspaces; saved) undone and redone as each lesson's code
  can, a key a step with the cursor left alone at 08.01 and 08.02, steps
  and the cursor from 08.03, "(modified)" by the saved point at 08.04.
  timeline_after: at 08.01, after every step undone and a save, learn.txt
  is the file as it was; from 08.02 it is saved with the edits, as in the
  core.

For module 09 (the test aid `@internal` in script.c, the rest in track.py
and tests/):

- `edit(..., init=None)`, the default, sets KILO_INIT to the empty string,
  so no test of any module runs a developer's own init.lua; a string is Lua
  written to an init.lua of the test's (`initN/init.lua` for the Nth
  editor, so errors still say "init.lua"); "env" takes it from the test.
  `run_script(t, lua, text, ...)` runs `kilo -l` with no terminal.
  `lua_quote(s)` writes any bytes as a Lua literal. `asan_build(t,
  sanitize)` links Lua's library and takes "address,undefined" too.
- The tests drive the editor through the Ctrl-E prompt and init files,
  and compare strings longer than the message line inside Lua (`... ==
  "..."`, which shows true or false): the line holds 79 bytes.
- `kilo.test_panic()` (`@internal`) asks for an error outside any
  protected call, the one way to reach the panic function (0908).
- tests/api_fuzz.py writes random calls of every API function as Lua:
  0908 runs 10 blocks of 300 in the editor, a block a key, the screen drawn
  after each, under ASan and UBSan (input, quit and keys that read the
  keyboard left out; autocommand 1, the driver, never deleted); 0909 runs 3
  scripts of 2000 with no screen under ASan and UBSan, with LeakSanitizer
  on Linux. The seed is the clock's, printed with a failure. UBSan's one
  report from module 06 is suppressed by name (Found on the way, 5).
- The timeline at 09.01 to 09.09 runs the project with TIMELINE_INIT
  (an init.lua that uses what each lesson has), on learn.txt: init.lua's
  message, a line at the prompt and an error, from 09.02 the reads, from
  09.03 a header put in with set_lines, 09.04 Ctrl-T (Lua) commenting a row
  and back, 09.05 the words counted on TextChanged, 09.06 the numbers in
  red and the status bar set, 09.07 Ctrl-O asking for a line, 09.08 a loop
  stopped by Ctrl-C. timeline_after: learn.txt untouched; `--api-info` has
  the lesson's count of functions (6, 9, 12, 15, 21, 24); at 09.09 `kilo
  -l` upper-cases a copy of learn.txt. prepare() copies lua/ into the
  project first (supply_lua).
- On Linux (in Docker, aarch64): Debian trixie (glibc 2.41, gcc 14.2),
  the finished tree with module 08: all 41 tests (09's fuzz with ASan,
  UBSan and LeakSanitizer), check-skeleton of 09 and check-timeline pass,
  and every 09 project and the finished one build with -Werror; that took
  the two findings above (5 and 6). Alpine 3.22 (musl, gcc 14.2), the tree
  before module 08 was merged: the same pass (no ASan for gcc there, so
  the plain build).
