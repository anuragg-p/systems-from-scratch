# Notes for the lesson writers

Everything here was run on the reference code or on the project as the
site shows it at a lesson (`./learn files kilo --at NN.LL`), on an Apple
M-series Mac (macOS, Darwin 25.6, Apple clang 21), and every "break it"
was run as the change it describes. Screens are what the tests' terminal
emulator (Screen in track.py) made of kilo's bytes, rows with trailing
spaces dropped, `[cursor R,C]` counting from 1. The same tests, the
skeleton check and the timeline check also pass on Linux (Alpine, gcc and
musl, aarch64, in Docker), and every lesson's project builds there with
no warnings. Function names are given instead of line numbers.

## The upstream, and what this track does with it

antirez/kilo, master at 323d93b29bd89a2cb446de90c4ed4fea1764176e, one file
of 1308 lines, BSD-2-Clause. `tracks/kilo/LICENSE` is its LICENSE, byte
for byte; kilo.c keeps antirez's notice in its header. The finished kilo.c
here is 1057 lines with the notes (`./learn files kilo --at 05.02`).

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

Note for whoever restores highlighting as the 06 extension: the original
`editorDelRow` renumbers `idx` with `idx++` where it means `idx--`.

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

`./learn run kilo -- file.txt` runs the finished editor (files in
`build/at/kilo/finished/`); without a file, it edits `learn.txt` there.

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
30x100 shows 28 rows of text and a 100-column status bar.

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

## Other behaviour of the original, kept

- kilo does not clear the screen on exit: the shell prompt appears where
  the cursor was, over the last screen.
- If standard input is not a terminal, `enableRawMode` fails and main
  ignores it; `editorReadKey` then spins on end of file.
- The SIGWINCH handler draws the screen from inside the signal handler
  (malloc and write in a handler); a resize in the middle of a frame is
  not guarded against.
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
