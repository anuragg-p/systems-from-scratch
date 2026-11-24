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
07, the other extension, is ours: a language server client in lsp.c and
json.c, which kilo.c calls from a few one-line hooks (see "07 A language
server client"). The finished kilo.c (`./learn files kilo`, every lesson
of every path) is 1541 lines (1472 with module 06 alone); at 05.02 it is
1068, as without either.

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
| lsp.c | 1505 | the client: the server table, starting and stopping, frames, the session, poll(), diagnostics, definitions |
| json.h | 60 | the JSON tree (`struct json`), the reader's and getters' prototypes, jsonQuote |
| json.c | 424 | the reader (recursive descent, depth cap) and the one writer helper; knows nothing of kilo or LSP |
| Makefile | | from 07.01 `kilo.c lsp.c`, from 07.02 `kilo.c lsp.c json.c`, same flags |

The project at each lesson (lines, `./learn files kilo --at 07.LL`):

| lesson | kilo.c | lsp.c | lsp.h | json.c | json.h |
|---|---|---|---|---|---|
| 07.01 | 1070 | 237 | 15 | - | - |
| 07.02 | 1071 | 502 | 17 | 59 | 15 |
| 07.03 | 1071 | 542 | 17 | 370 | 49 |
| 07.04 | 1071 | 576 | 17 | 370 | 49 |
| 07.05 | 1071 | 798 | 18 | 370 | 49 |
| 07.06 | 1085 | 1076 | 28 | 370 | 49 |
| 07.07 | 1137 | 1224 | 31 | 370 | 49 |

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
  tabs, which render no longer shows.
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
- **The counts are said when they change**, not on every list: with
  clangd a list comes after every change, the same counts each time while
  you type on an error's row, and saying them every time would replace the
  row's message. "lsp: no problems" is said when they go to none.
- **The row's message shows at the pause after the list arrives.** As
  designed; but clangd's list for a change comes about 60 ms after the
  pause that sent the change, so the message of an error just typed shows
  only at the next pause (an arrow, Left then Right). Worth revisiting.
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
- Added for safety: the child resets SIGWINCH to the default before exec
  (until exec it runs kilo's handler, which would draw a frame into the
  pipe); SIGWINCH is held back while the diagnostics list changes (the
  handler draws rows); every function that talks to the server returns at
  once when none is running (see "Found on the way", the first).

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
(exit 127) is reaped at once.

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
read; the scripted server writing 10 bytes, 30, then the rest, 0.255 s
apart): kilo read 10 (the buffer holds 10), 0.202 s later 30 (40), 0.303 s
later 85 (125), and then took the whole message off, 125 bytes with a body
of 102. The gaps are the 0.1 s read: kilo looks at the server only when
read() on the keyboard times out.

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
(10.6 a second), 2 at 07.04** (the pause, and the server's answer). The
delay from the server writing its answer to kilo's frame with it reaching
the terminal (the server's log of its write and the test's read of the
pseudo-terminal, both on Python's monotonic clock), 20 runs each: **07.03
min 1.4 ms, median 45.5 ms, max 100.3 ms; 07.04 min 0.1 ms, median 0.2
ms, max 0.7 ms**.

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

On the project at 07.06, the error typed:

```
    |        int [_:total] = add(2, 3);
    |        printf("%d\n", [_:totl]);
    |        return 0;
    |}
    |sam ple/sum.c - 8 lines (modified)                                   6/8
    |lsp: 1 error, 1 info
```

clangd 21 sends two: the error, range line 5 characters 16 to 20 (`totl`),
severity 1, message "Use of undeclared identifier 'totl'; did you mean
'total'? (fix available)\n\nsum.c:5:6: note: 'total' declared here"; and
its note as a diagnostic of its own, line 4 characters 5 to 10 (`total` in
`int total`), severity 3, "'total' declared here\n\n...". Hence "1 error,
1 info", and `total` underlined too. Left, Right (the cursor rests on the
row):

```
    |6: error: Use of undeclared identifier 'totl'; did you mean 'total'? (fi
```

The fix: no underline, `lsp: no problems`. The bytes kilo writes for the
error's row, at 07.06 (core + 07):

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
  descriptors it was started with; it exits on end of input, and on its
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
  Backspace from 07.05, the error underlined and its message at the pause
  from 07.06, Ctrl-G, Ctrl-B and Ctrl-B again at 07.07. The relay's
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
