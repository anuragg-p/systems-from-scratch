# Notes for the lesson writers

Everything here was run on the reference code or on the project as the
site shows it at a lesson (`./learn files kilo --at NN.LL`), on an Apple
M-series Mac (macOS, Darwin 25.6, Apple clang 21), and every "break it"
was run as the change it describes. Screens are what the tests' terminal
emulator (Screen in track.py) made of kilo's bytes, rows with trailing
spaces dropped, `[cursor R,C]` counting from 1; in module 06, each run of
one colour is written `[c:text]` (see "06 Syntax highlighting"). The same tests, the
skeleton check and the timeline check also pass on Linux (Alpine, gcc and
musl, aarch64, in Docker), and every lesson's project builds there with
no warnings. On Linux with glibc (Debian trixie, gcc 14, aarch64, in
Docker) they failed until departure 33, and pass there since, with every
project built without warnings. Function names are given instead of line
numbers.

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
byte what it was without it. See "06 Syntax highlighting" below. The
finished kilo.c (`./learn files kilo`, every lesson of every path) is 1472
lines; at 05.02 it is 1068, as without the module.

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
