/* edit: a text editor on a terminal, with its text in whichever structure
 * of lib/ holds it best.
 *
 *   edit [option ...] FILE                   edit FILE on the terminal
 *   edit [option ...] --replay SCRIPT FILE   make SCRIPT's edits to FILE's
 *                                            text, with no screen at all
 * --algo=NAME: the structure that holds the text:                  @from 03.02
 *   array   the whole text in one array                            @from 03.02
 *   gap     a gap buffer                                           @from 03.02
 *   pieces  a piece table, its pieces in a list                    @from 03.04
 *   tree    a piece table, its pieces in a balanced tree           @from 03.05
 *
 * The editor is the kilo of this course's kilo track (tracks/kilo), whole:
 * raw mode, reading keys, drawing the screen with VT100 escapes in one
 * write, moving the cursor and scrolling, saving and search are kilo's,
 * as that track builds them, and nothing of them is new here. What is new
 * is where the text lives. kilo keeps it as an array of rows, a string a
 * line; here it is behind lib/text.h, a row of bytes the editor can read,
 * insert into and erase from, and nothing more. The editor finds the lines
 * itself, by reading the text near the top of the screen, so a key costs
 * the editor the same in a file of ten lines as in one of ten million:
 * what is left to cost more is the structure.
 *
 * --replay SCRIPT reads edits from SCRIPT ("-": standard input), one a
 * line, and makes them to the text with no terminal at all. That is how
 * the structures are timed on the same edits (bench/grow.py) and tested
 * on them, byte for byte against each other. The commands:
 *
 *   goto POS       the cursor to byte POS of the text, from 0 ("end": the end)
 *   goto LINE:COL  the cursor to column COL of line LINE, both from 1
 *   type TEXT      type TEXT at the cursor, a key at a time: \n is Enter,
 *                  \t a tab, \\ a backslash, \xHH any byte
 *   paste TEXT     put TEXT in at the cursor at once, the cursor after it
 *   back N         press Backspace N times
 *   delete N       erase the N bytes after the cursor at once
 *   undo [N]       undo the last edit (N of them)                   @from 03.03
 *   redo [N]       redo the last undone (N of them)                 @from 03.03
 *   print          write the whole text on standard output
 *   save           save it to FILE, as Ctrl-S does
 *
 * and a line that starts with # is a comment. A bad command is an error,
 * exit status 2.
 *
 * DS_STATS=1 prints "stats: edit: inserts I, erases E, bytes read R" (the
 * changes made, and the bytes the editor read from the text to find its
 * lines, draw the screen and search), and the structure's own line.
 *
 * -----------------------------------------------------------------------
 *
 * kilo, and so this file, is derived from kilo.c by Salvatore Sanfilippo,
 * https://github.com/antirez/kilo (commit 323d93b), under the licence in
 * LICENSE beside this file. His notice follows.
 *
 * Copyright (C) 2016 Salvatore Sanfilippo <antirez at gmail dot com>
 *
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are
 * met:
 *
 *  *  Redistributions of source code must retain the above copyright
 *     notice, this list of conditions and the following disclaimer.
 *
 *  *  Redistributions in binary form must reproduce the above copyright
 *     notice, this list of conditions and the following disclaimer in the
 *     documentation and/or other materials provided with the distribution.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 * LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
 * A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
 * HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 * SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 * LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 * DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 * THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

#include <termios.h>
#include <stdlib.h>
#include <stdio.h>
#include <errno.h>
#include <string.h>
#include <ctype.h>
#include <time.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <stdarg.h>
#include <signal.h>

#include "ds.h"
#include "text.h"
#include "flat.h"
#include "gap.h"        // @from 03.02
#include "undo.h"       // @from 03.03
#include "pieces.h"     // @from 03.04
#include "ptree.h"      // @from 03.05

/* Everything the editor knows, in one global. */
struct editorConfig {
    int cx,cy;          // the cursor: column and row on the screen, not in the file
    int rowoff;         // the row of the text on the top line: the cursor is on row rowoff+cy
    size_t topoff;      // where that row starts in the text
    int coloff;         // the column in the leftmost column: the cursor is on coloff+cx
    int screenrows;     // rows of text the screen has room for
    int screencols;     // columns the screen has
    int rawmode;        // is the terminal in raw mode now?
    Text *text;         // the text, in the structure --algo picked
    long newlines;      // how many '\n' the text holds
    int dirty;          // changes since the file was opened or saved; 0: none
    char *filename;     // the file being edited
    char statusmsg[80];         // the message under the status bar
    time_t statusmsg_time;      // when it was set: it shows for 5 seconds
    Undo undo;          // what was done, to undo and redo @from 03.03
};

static struct editorConfig E;

/* What a key sends. A Ctrl key sends its letter's code with the top three
 * bits cleared: Ctrl-Q is 'q' & 0x1f, 17. Enter sends 13, a carriage
 * return, and Backspace sends 127, DEL. */
enum KEY_ACTION{
        KEY_NULL = 0,       /* NULL */
        CTRL_C = 3,         /* Ctrl-c */
        CTRL_D = 4,         /* Ctrl-d */
        CTRL_F = 6,         /* Ctrl-f */
        CTRL_H = 8,         /* Ctrl-h */
        TAB = 9,            /* Tab */
        CTRL_L = 12,        /* Ctrl+l */
        ENTER = 13,         /* Enter */
        CTRL_Q = 17,        /* Ctrl-q */
        CTRL_S = 19,        /* Ctrl-s */
        CTRL_U = 21,        /* Ctrl-u */
        CTRL_Y = 25,        /* Ctrl-y */
        CTRL_Z = 26,        /* Ctrl-z */
        ESC = 27,           /* Escape */
        BACKSPACE =  127,   /* Backspace */
        /* Keys the terminal sends as escape sequences, several bytes each.
         * editorReadKey() turns each sequence into one of these codes,
         * above 255 so no byte can be mistaken for one. */
        ARROW_LEFT = 1000,
        ARROW_RIGHT,
        ARROW_UP,
        ARROW_DOWN,
        DEL_KEY,
        HOME_KEY,
        END_KEY,
        PAGE_UP,
        PAGE_DOWN
};

void editorSetStatusMessage(const char *fmt, ...);

/* ======================= Low level terminal handling ====================== */

/* The terminal's settings as they were before raw mode, to put back at exit. */
static struct termios orig_termios;

/* Leave raw mode: put back the settings enableRawMode() saved. Nothing is
 * checked; this runs on the way out, when nothing could be done about it. */
void disableRawMode(int fd) {
    if (E.rawmode) {
        tcsetattr(fd,TCSAFLUSH,&orig_termios);
        E.rawmode = 0;
    }
}

/* Registered with atexit(): however the editor exits, the terminal goes
 * back to the way the shell needs it. */
void editorAtExit(void) {
    disableRawMode(STDIN_FILENO);
}

/* Raw mode: the terminal hands over every byte as it is typed, and does
 * nothing with it on the way. By default (canonical, "cooked" mode) the
 * terminal driver collects a whole line, echoes it, handles Backspace
 * itself, and turns Ctrl-C into a signal. An editor wants none of that. */
int enableRawMode(int fd) {
    struct termios raw;

    if (E.rawmode) return 0; /* Already enabled. */
    if (!isatty(STDIN_FILENO)) goto fatal;
    atexit(editorAtExit);
    if (tcgetattr(fd,&orig_termios) == -1) goto fatal;

    raw = orig_termios;  /* modify the original mode */
    /* Input: no SIGINT on a break, no CR turned into NL (Enter arrives as
     * 13), no parity check, no stripping of the 8th bit, and no Ctrl-S and
     * Ctrl-Q flow control, so those two keys reach the editor. */
    raw.c_iflag &= ~(BRKINT | ICRNL | INPCK | ISTRIP | IXON);
    /* Output: no processing, so "\n" moves down one line and nothing more.
     * The editor writes "\r\n" where it wants a new line. */
    raw.c_oflag &= ~(OPOST);
    /* 8-bit characters. */
    raw.c_cflag |= (CS8);
    /* Local: no echo, no line at a time, no Ctrl-V, and no signals from
     * Ctrl-C or Ctrl-Z: they arrive as the bytes 3 and 26. */
    raw.c_lflag &= ~(ECHO | ICANON | IEXTEN | ISIG);
    /* read() returns as soon as there is one byte (VMIN 0), or after 0.1 s
     * with nothing (VTIME 1, in tenths of a second). */
    raw.c_cc[VMIN] = 0;
    raw.c_cc[VTIME] = 1;

    /* TCSAFLUSH: switch once all output is written, and throw away input
     * typed before the switch. */
    if (tcsetattr(fd,TCSAFLUSH,&raw) < 0) goto fatal;
    E.rawmode = 1;
    return 0;

fatal:
    errno = ENOTTY;
    return -1;
}

/* Read one key. Most keys are one byte; the arrows, Home, End, Delete and
 * Page Up/Down arrive as escape sequences, ESC followed by two or three
 * bytes, which come back as one of the codes above 1000. A lone ESC is the
 * Escape key: nothing follows it within 0.1 s. */
int editorReadKey(int fd) {
    int nread;
    char c, seq[3];
    while ((nread = read(fd,&c,1)) == 0);
    if (nread == -1) exit(1);

    while(1) {
        switch(c) {
        case ESC:    /* escape sequence */
            /* A lone Escape key: the next read() times out. */
            if (read(fd,seq,1) == 0) return ESC;
            if (read(fd,seq+1,1) == 0) return ESC;

            /* ESC [ sequences. */
            if (seq[0] == '[') {
                if (seq[1] >= '0' && seq[1] <= '9') {
                    /* ESC [ digit ~: one more byte to read. */
                    if (read(fd,seq+2,1) == 0) return ESC;
                    if (seq[2] == '~') {
                        switch(seq[1]) {
                        case '3': return DEL_KEY;
                        case '5': return PAGE_UP;
                        case '6': return PAGE_DOWN;
                        }
                    }
                } else {
                    switch(seq[1]) {
                    case 'A': return ARROW_UP;
                    case 'B': return ARROW_DOWN;
                    case 'C': return ARROW_RIGHT;
                    case 'D': return ARROW_LEFT;
                    case 'H': return HOME_KEY;
                    case 'F': return END_KEY;
                    }
                }
            }

            /* ESC O sequences: what some terminals send for Home and End. */
            else if (seq[0] == 'O') {
                switch(seq[1]) {
                case 'H': return HOME_KEY;
                case 'F': return END_KEY;
                }
            }
            break;
        default:
            return (unsigned char)c;
        }
    }
}

/* Ask the terminal where its cursor is: write ESC [ 6 n, and the terminal
 * answers on the input side, as if typed, with ESC [ row ; col R. Rows and
 * columns count from 1. Returns 0, or -1 if the answer does not parse. */
int getCursorPosition(int ifd, int ofd, int *rows, int *cols) {
    char buf[32];
    unsigned int i = 0;

    /* Report cursor location */
    if (write(ofd, "\x1b[6n", 4) != 4) return -1;

    /* Read the response: ESC [ rows ; cols R */
    while (i < sizeof(buf)-1) {
        if (read(ifd,buf+i,1) != 1) break;
        if (buf[i] == 'R') break;
        i++;
    }
    buf[i] = '\0';

    /* Parse it. */
    if (buf[0] != ESC || buf[1] != '[') return -1;
    if (sscanf(buf+2,"%d;%d",rows,cols) != 2) return -1;
    return 0;
}

/* The size of the terminal window. The kernel knows it (TIOCGWINSZ); when
 * it does not say, the terminal itself is asked: move the cursor right and
 * down as far as it goes, ask where it ended up, and put it back. Returns
 * 0, or -1 on error. */
int getWindowSize(int ifd, int ofd, int *rows, int *cols) {
    struct winsize ws;

    if (ioctl(1, TIOCGWINSZ, &ws) == -1 || ws.ws_col == 0) {
        /* ioctl() failed. Try to query the terminal itself. */
        int orig_row, orig_col, retval;

        /* Get the initial position so we can restore it later. */
        retval = getCursorPosition(ifd,ofd,&orig_row,&orig_col);
        if (retval == -1) goto failed;

        /* Go to right/bottom margin and get position. */
        if (write(ofd,"\x1b[999C\x1b[999B",12) != 12) goto failed;
        retval = getCursorPosition(ifd,ofd,rows,cols);
        if (retval == -1) goto failed;

        /* Restore position. */
        char seq[32];
        snprintf(seq,32,"\x1b[%d;%dH",orig_row,orig_col);
        if (write(ofd,seq,strlen(seq)) == -1) {
            /* Can't recover... */
        }
        return 0;
    } else {
        *cols = ws.ws_col;
        *rows = ws.ws_row;
        return 0;
    }

failed:
    return -1;
}

/* ============================ The text, and its rows ======================== */

/* kilo keeps an array of rows. Here the text is bytes behind text.h, and
 * a row is a line of them: from just after a '\n' (or the start) up to
 * the next '\n' (or the end). A last line without a '\n' is a row too, and
 * the row just after the last, where typing at the end of the text goes,
 * is where the cursor can stand, as in kilo. The editor finds rows by
 * reading the text, never all of it: the row on the top line of the
 * screen and where it starts (E.rowoff, E.topoff) are always known, and
 * every other row the editor needs is found by reading on from there, or
 * back. */

static long stat_inserts, stat_erases, stat_read;

static void editorPrintStats(void) {
    ds_stats_print("edit", "inserts %ld, erases %ld, bytes read %ld", stat_inserts, stat_erases, stat_read);
}

/* Read n bytes of the text from pos (fewer at its end) into buf. Every
 * read the editor makes for itself comes here, so DS_STATS counts them. */
static size_t editorRead(size_t pos, char *buf, size_t n) {
    if (pos >= E.text->len) return 0;
    size_t got = text_read(E.text, pos, buf, n);
    stat_read += (long)got;
    return got;
}

/* Looking for the end of a line, the text is read 128 bytes at first (most
 * lines are shorter), then twice as much each time, up to 4096. */
#define EDIT_CHUNK 4096

/* Where the first '\n' at or after pos is; the end of the text if none. */
static size_t findNewline(size_t pos) {
    char buf[EDIT_CHUNK];
    size_t got, want = 128;
    while ((got = editorRead(pos, buf, want)) > 0) {
        char *nl = memchr(buf, '\n', got);
        if (nl) return pos + (size_t)(nl - buf);
        pos += got;
        if (want < sizeof buf) want *= 2;
    }
    return E.text->len;
}

/* Where the line holding pos starts: just after the last '\n' before pos,
 * or 0. */
static size_t lineStart(size_t pos) {
    char buf[EDIT_CHUNK];
    size_t want = 128;
    if (pos > E.text->len) pos = E.text->len;
    while (pos > 0) {
        size_t from = pos > want ? pos - want : 0;
        size_t got = editorRead(from, buf, pos - from);
        for (size_t i = got; i > 0; i--)
            if (buf[i-1] == '\n') return from + i;
        pos = from;
        if (want < sizeof buf) want *= 2;
    }
    return 0;
}

/* How many '\n' are in the n bytes at s. */
static long newlinesIn(const char *s, size_t n) {
    long count = 0;
    const char *end = s + n;
    while (s < end && (s = memchr(s, '\n', (size_t)(end - s))) != NULL) {
        count++;
        s++;
    }
    return count;
}

/* How many '\n' are in the text between from and to. */
static long countNewlines(size_t from, size_t to) {
    char buf[EDIT_CHUNK];
    long count = 0;
    while (from < to) {
        size_t got = editorRead(from, buf, to - from < sizeof buf ? to - from : sizeof buf);
        if (got == 0) break;
        count += newlinesIn(buf, got);
        from += got;
    }
    return count;
}

/* How many rows the text has: a '\n' ends each, and a last line without
 * one is a row as well. */
static int editorNumRows(void) {
    size_t len = E.text->len;
    char c;
    if (len == 0) return 0;
    editorRead(len-1, &c, 1);
    return (int)E.newlines + (c != '\n');
}

/* Where the rows on the screen start: rowstart[i] is the start of row
 * E.rowoff+i, read on from E.topoff as far as anything has asked, and
 * kept until the text changes or the screen scrolls. */
static size_t *rowstart;
static int rowsknown, rowscap;

/* The text, or the top of the screen, changed: forget the rows found. */
static void rowsChanged(void) {
    rowsknown = 0;
}

/* Where row r starts, and where its text ends: at its '\n', or the end of
 * the text. */
static void rowSpan(int r, size_t *start, size_t *end) {
    if (r < E.rowoff) {     /* above the screen: read back from its top */
        size_t s = E.topoff;
        for (int i = E.rowoff; i > r && s > 0; i--) s = lineStart(s-1);
        *start = s;
        *end = findNewline(s);
        return;
    }
    int i = r - E.rowoff;
    if (rowsknown == 0) {
        if (rowscap == 0) {
            rowscap = 64;
            rowstart = xmalloc(rowscap * sizeof *rowstart);
        }
        rowstart[0] = E.topoff;
        rowsknown = 1;
    }
    while (rowsknown <= i+1) {
        if (rowsknown == rowscap) {
            size_t *bigger = xmalloc(2 * rowscap * sizeof *rowstart);
            memcpy(bigger, rowstart, rowscap * sizeof *rowstart);
            free(rowstart);
            rowstart = bigger;
            rowscap *= 2;
        }
        size_t prev = rowstart[rowsknown-1];
        rowstart[rowsknown] = prev >= E.text->len ? prev + 1 : findNewline(prev) + 1;
        rowsknown++;
    }
    *start = rowstart[i] < E.text->len ? rowstart[i] : E.text->len;
    *end = rowstart[i+1] - 1 < E.text->len ? rowstart[i+1] - 1 : E.text->len;
}

/* How many bytes row r has, not counting its '\n'. */
static int rowSize(int r) {
    size_t start, end;
    rowSpan(r, &start, &end);
    return (int)(end - start);
}

/* Scroll the screen one row down, or up: the next row, or the one
 * before, goes on the top line. */
static void editorScrollDown(void) {
    size_t start, end;
    rowSpan(E.rowoff+1, &start, &end);
    if (rowsknown > 1) {
        memmove(rowstart, rowstart+1, (rowsknown-1) * sizeof *rowstart);
        rowsknown--;
    }
    E.rowoff++;
    E.topoff = start;
}

static void editorScrollUp(void) {
    E.rowoff--;
    E.topoff = lineStart(E.topoff-1);
    rowsChanged();
}

/* The text changed: n bytes s went in at pos, or out from it. Keep the
 * count of newlines, and the top of the screen on the same row of the
 * text: an edit before it moves it. */
static void afterInsert(size_t pos, const char *s, size_t n) {
    long nl = newlinesIn(s, n);
    E.newlines += nl;
    if (pos < E.topoff) {
        E.topoff += n;
        E.rowoff += (int)nl;
    }
    rowsChanged();
    E.dirty++;
}

static void afterErase(size_t pos, const char *s, size_t n) {
    long nl = newlinesIn(s, n);
    E.newlines -= nl;
    if (pos + n < E.topoff) {
        E.topoff -= n;
        E.rowoff -= (int)nl;
    } else if (pos < E.topoff) {
        /* The '\n' before the top row went: the top row is now the line
         * that holds pos. */
        E.rowoff -= (int)newlinesIn(s, E.topoff - pos);
        E.topoff = lineStart(pos);
    }
    rowsChanged();
    E.dirty++;
}

// @from 03.03
/* Every change the editor makes to the text: insert n bytes at pos, or
 * erase n from pos. typed: it was typed (a key that inserts, or
 * Backspace), so undo can count it with the keys typed before it. */
// @else
// /* Every change the editor makes to the text: insert n bytes at pos, or
//  * erase n from pos. typed: it was typed (a key that inserts, or
//  * Backspace). */
// @end
static void editorInsertText(size_t pos, const char *s, size_t n, int typed) {
    text_insert(E.text, pos, s, n);
    stat_inserts++;
    afterInsert(pos, s, n);
    undo_note(&E.undo, 0, pos, s, n, typed);    // @from 03.03
}

static void editorEraseText(size_t pos, size_t n, int typed) {
    char *s = xmalloc(n);
    editorRead(pos, s, n);
    text_erase(E.text, pos, n);
    stat_erases++;
    afterErase(pos, s, n);
    undo_note(&E.undo, 1, pos, s, n, typed);    // @from 03.03
    free(s);
}

/* Put the cursor on byte pos of the text. If its row is not on the
 * screen, the screen scrolls to put it on the top line, as a search does
 * with a match. */
static void editorGoTo(size_t pos) {
    size_t start = lineStart(pos);
    long row;
    if (start >= E.topoff)
        row = E.rowoff + countNewlines(E.topoff, start);
    else
        row = E.rowoff - countNewlines(start, E.topoff);
    if (row < E.rowoff || row >= E.rowoff + E.screenrows) {
        E.rowoff = (int)row;
        E.topoff = start;
        rowsChanged();
    }
    E.cy = (int)(row - E.rowoff);
    E.cx = (int)(pos - start);
    E.coloff = 0;
    if (E.cx >= E.screencols) {
        int diff = E.cx - E.screencols + 1;
        E.cx -= diff;
        E.coloff += diff;
    }
}

/* Where a typed key goes when the cursor is at row filerow, column
 * filecol. As in kilo, the cursor may be below the last row (empty rows
 * are added down to it first) or past the end of its row (the row is
 * padded with spaces up to it). */
static size_t editorTypingAt(int filerow, int filecol) {
    int numrows = editorNumRows();
    if (filerow >= numrows) {
        /* A '\n' for each row missing, and one to end the last row first
         * if it has none. */
        char c = '\n';
        if (E.text->len > 0) editorRead(E.text->len-1, &c, 1);
        int k = filerow - numrows + (c != '\n');
        if (k > 0) {
            char *nl = xmalloc((size_t)k);
            memset(nl, '\n', (size_t)k);
            editorInsertText(E.text->len, nl, (size_t)k, 1);
            free(nl);
        }
    }
    size_t start, end;
    rowSpan(filerow, &start, &end);
    if ((size_t)filecol > end - start) {
        size_t pad = (size_t)filecol - (end - start);
        char *spaces = xmalloc(pad);
        memset(spaces, ' ', pad);
        editorInsertText(end, spaces, pad, 1);
        free(spaces);
    }
    return start + (size_t)filecol;
}

/* Insert a character where the cursor is, and move the cursor past it. */
void editorInsertChar(int c) {
    int filerow = E.rowoff+E.cy;
    int filecol = E.coloff+E.cx;
    char ch = (char)c;

    editorInsertText(editorTypingAt(filerow, filecol), &ch, 1, 1);
    if (E.cx == E.screencols-1)
        E.coloff++;
    else
        E.cx++;
}

/* Enter: split the row at the cursor, and move the cursor to the start of
 * the new row below. */
void editorInsertNewline(void) {
    int filerow = E.rowoff+E.cy;
    int filecol = E.coloff+E.cx;
    int numrows = editorNumRows();
    size_t pos;

    if (filerow > numrows) return;
    if (filerow == numrows) {
        pos = editorTypingAt(filerow, 0);
    } else {
        size_t start, end;
        rowSpan(filerow, &start, &end);
        /* If the cursor is over the current line size, we want to
         * conceptually think it's just over the last character. */
        if ((size_t)filecol > end - start) filecol = (int)(end - start);
        pos = start + (size_t)filecol;
    }
    editorInsertText(pos, "\n", 1, 1);
    if (E.cy == E.screenrows-1) {
        editorScrollDown();
    } else {
        E.cy++;
    }
    E.cx = 0;
    E.coloff = 0;
}

/* Backspace: delete the character left of the cursor. At the start of a
 * row, join the row onto the end of the one above: that is erasing the
 * '\n' between them. */
void editorDelChar(void) {
    int filerow = E.rowoff+E.cy;
    int filecol = E.coloff+E.cx;
    size_t start, end;

    if (filerow >= editorNumRows() || (filecol == 0 && filerow == 0)) return;
    rowSpan(filerow, &start, &end);
    if (filecol == 0) {
        /* Handle the case of column 0, we need to move the current line
         * on the right of the previous one. */
        filecol = (int)(start - 1 - lineStart(start-1));
        editorEraseText(start-1, 1, 1);
        /* On the top line, the erase has moved the top of the screen up
         * to the joined row already (kilo: E.rowoff--). */
        if (E.cy != 0) E.cy--;
        E.cx = filecol;
        if (E.cx >= E.screencols) {
            int shift = (E.cx-E.screencols)+1;
            E.cx -= shift;
            E.coloff += shift;
        }
    } else {
        if ((size_t)filecol <= end - start) editorEraseText(start + (size_t)filecol - 1, 1, 1);
        if (E.cx == 0 && E.coloff)
            E.coloff--;
        else
            E.cx--;
    }
}

/* The structures that can hold the text, by their --algo names. */
typedef Text *(*Opener)(const char *path);

// @from 03.02
static const struct {
    const char *name;
    Opener open;
} algos[] = {
    {"array", flat_open},
    {"gap", gap_open},
    {"pieces", pieces_open},        // @from 03.04
    {"tree", ptree_open},           // @from 03.05
    {NULL, NULL}
};

/* The structure --algo=name names. */
static Opener editorPickAlgo(const char *name) {
    char have[200] = "";
    for (int i = 0; algos[i].name; i++) {
        if (strcmp(name, algos[i].name) == 0)
            return algos[i].open;
        strcat(strcat(have, i ? ", " : ""), algos[i].name);
    }
    die("no --algo '%s' (have: %s)", name, have);
}

// @end
/* Open the file into the structure open() makes. A file that does not
 * exist is an empty text, created by the first save. */
void editorOpen(const char *filename, Opener open) {
    free(E.filename);
    E.filename = xstrndup(filename, strlen(filename));
    E.text = open(filename);
    E.topoff = 0;
    E.rowoff = 0;
    rowsChanged();
    E.dirty = 0;
}

/* Save the text to E.filename. It is written to a new file beside the old
 * one, which is then renamed over it, so the old file stays whole until
 * the new one is. Returns 0, or 1 on error; either way the message line
 * says what happened. */
// @from 03.04
/* (kilo cuts the old file short and writes over it, but the piece table
 * reads the text from the old file, mapped: it must stay as it was.) */
// @end
int editorSave(void) {
    size_t n = strlen(E.filename);
    char *tmp = xmalloc(n + 16);
    int fd, err, made = 0;
    FILE *f = NULL;
    struct stat sb;
    mode_t mode;

    snprintf(tmp, n + 16, "%s.edit-XXXXXX", E.filename);
    fd = mkstemp(tmp);
    if (fd == -1) goto writeerr;
    made = 1;
    /* A new file gets 0644 less the umask, as kilo's open() gives it; an
     * old one keeps its own permissions. */
    if (stat(E.filename, &sb) == 0) {
        mode = sb.st_mode & 07777;
    } else {
        mode = umask(0);
        umask(mode);
        mode = 0644 & ~mode;
    }
    if (fchmod(fd, mode) == -1) goto writeerr;
    f = fdopen(fd, "wb");
    if (f == NULL) goto writeerr;
    if (text_write(E.text, f) == -1) goto writeerr;
    fd = -1;
    if (fclose(f) == EOF) {
        f = NULL;
        goto writeerr;
    }
    f = NULL;
    if (rename(tmp, E.filename) == -1) goto writeerr;
    free(tmp);
    E.dirty = 0;
    editorSetStatusMessage("%zu bytes written on disk", E.text->len);
    return 0;

writeerr:
    err = errno;
    if (f) fclose(f);
    else if (fd != -1) close(fd);
    if (made) unlink(tmp);
    free(tmp);
    editorSetStatusMessage("Can't save! I/O error: %s",strerror(err));
    return 1;
}

/* ============================= Terminal update ============================ */

/* A frame is built in memory and written to the terminal in one write():
 * written piece by piece, the terminal would show it half drawn, and the
 * screen would flicker. struct abuf is a string that grows as it is
 * appended to. */
struct abuf {
    char *b;
    int len;
};

#define ABUF_INIT {NULL,0}

/* Append len bytes at s to the frame. */
void abAppend(struct abuf *ab, const char *s, int len) {
    char *new = realloc(ab->b,ab->len+len);

    if (new == NULL) return;
    memcpy(new+ab->len,s,len);
    ab->b = new;
    ab->len += len;
}

void abFree(struct abuf *ab) {
    free(ab->b);
}

/* What the screen shows for the n bytes of a row at chars: each tab turned
 * into spaces up to the next column that is a multiple of 8 (kilo's
 * editorUpdateRow), and any other control character as '?', one column,
 * so the cursor's column still counts one a byte. Returns its length. */
static int editorRender(const char *chars, size_t n, char **render, size_t *cap) {
    size_t tabs = 0, j;
    int idx = 0;
    for (j = 0; j < n; j++)
        if (chars[j] == TAB) tabs++;
    if (*cap < n + tabs*8 + 1) {
        free(*render);
        *cap = n + tabs*8 + 1;
        *render = xmalloc(*cap);
    }
    for (j = 0; j < n; j++) {
        unsigned char c = (unsigned char)chars[j];
        if (c == TAB) {
            (*render)[idx++] = ' ';
            while(idx % 8 != 0) (*render)[idx++] = ' ';
        } else {
            (*render)[idx++] = (c < 32 || c == 127) ? '?' : (char)c;
        }
    }
    return idx;
}

/* Draw the whole screen from E: hide the cursor, go to the top left, write
 * every line (each erased to its end, so nothing of the last frame is left
 * over), then put the cursor where it belongs and show it again. One
 * write() sends it all. */
void editorRefreshScreen(void) {
    int y;
    char buf[32];
    struct abuf ab = ABUF_INIT;
    int numrows = editorNumRows();
    static char *chars, *render;
    static size_t charscap, rendercap;
    size_t start, end;

    abAppend(&ab,"\x1b[?25l",6); /* Hide cursor. */
    abAppend(&ab,"\x1b[H",3); /* Go home. */
    for (y = 0; y < E.screenrows; y++) {
        int filerow = E.rowoff+y;

        if (filerow >= numrows) {
            if (numrows == 0 && y == E.screenrows/3) {
                char what[64], welcome[80];
                /* In place of kilo's version: what holds the text. */
                snprintf(what,sizeof(what),"edit -- the text in a %s",E.text->ops->name);
                int welcomelen = snprintf(welcome,sizeof(welcome),
                    "%.*s\x1b[0K\r\n", E.screencols, what);
                int padding = (E.screencols-welcomelen)/2;
                if (padding < 0) padding = 0;
                if (padding) {
                    abAppend(&ab,"~",1);
                    padding--;
                }
                while(padding--) abAppend(&ab," ",1);
                abAppend(&ab,welcome,welcomelen);
            } else {
                abAppend(&ab,"~\x1b[0K\r\n",7);
            }
            continue;
        }

        /* Only as much of the row as can show is read: a byte is at least
         * one column, so no more than coloff+screencols of them. */
        rowSpan(filerow, &start, &end);
        size_t want = end - start;
        if (want > (size_t)(E.coloff + E.screencols)) want = (size_t)(E.coloff + E.screencols);
        if (charscap < want + 1) {
            free(chars);
            charscap = want + 1;
            chars = xmalloc(charscap);
        }
        editorRead(start, chars, want);
        int len = editorRender(chars, want, &render, &rendercap) - E.coloff;
        if (len > 0) {
            if (len > E.screencols) len = E.screencols;
            abAppend(&ab,render+E.coloff,len);
        }
        abAppend(&ab,"\x1b[0K",4);
        abAppend(&ab,"\r\n",2);
    }

    /* The status bar: name, lines and whether it has changed on the left;
     * the structure holding the text, and where the cursor is, on the right. */
    abAppend(&ab,"\x1b[0K",4);
    abAppend(&ab,"\x1b[7m",4);
    char status[80], rstatus[80];
    int len = snprintf(status, sizeof(status), "%.20s - %d lines %s",
        E.filename, numrows, E.dirty ? "(modified)" : "");
    int rlen = snprintf(rstatus, sizeof(rstatus),
        "%s %d/%d",E.text->ops->name,E.rowoff+E.cy+1,numrows);
    if (len > E.screencols) len = E.screencols;
    abAppend(&ab,status,len);
    while(len < E.screencols) {
        if (E.screencols - len == rlen) {
            abAppend(&ab,rstatus,rlen);
            break;
        } else {
            abAppend(&ab," ",1);
            len++;
        }
    }
    abAppend(&ab,"\x1b[0m\r\n",6);

    /* The message line: the last message, for 5 seconds after it was set.
     * It ends the frame, with no "\r\n": a newline on the bottom line
     * would scroll the whole screen up by one. */
    abAppend(&ab,"\x1b[0K",4);
    int msglen = strlen(E.statusmsg);
    if (msglen && time(NULL)-E.statusmsg_time < 5)
        abAppend(&ab,E.statusmsg,msglen <= E.screencols ? msglen : E.screencols);

    /* Put the cursor where it belongs: ESC [ row ; col H, counting from 1.
     * E.cx counts bytes, but on the screen each tab before the cursor takes
     * up to 8 columns. */
    int j;
    int cx = 1;
    int filerow = E.rowoff+E.cy;
    if (filerow < numrows) {
        rowSpan(filerow, &start, &end);
        size_t want = end - start;
        if (want > (size_t)(E.coloff + E.cx)) want = (size_t)(E.coloff + E.cx);
        if (charscap < want + 1) {
            free(chars);
            charscap = want + 1;
            chars = xmalloc(charscap);
        }
        editorRead(start, chars, want);
        for (j = E.coloff; j < (E.cx+E.coloff); j++) {
            if ((size_t)j < want && chars[j] == TAB) cx += 7-((cx-1)%8);
            cx++;
        }
    }
    snprintf(buf,sizeof(buf),"\x1b[%d;%dH",E.cy+1,cx);
    abAppend(&ab,buf,strlen(buf));
    abAppend(&ab,"\x1b[?25h",6); /* Show cursor. */
    if (write(STDOUT_FILENO,ab.b,ab.len) == -1) {
        /* Nothing to be done: the next frame tries again. */
    }
    abFree(&ab);
}

/* Set the message for the line under the status bar, printf style. It is
 * shown for 5 seconds, counted from now. */
void editorSetStatusMessage(const char *fmt, ...) {
    va_list ap;
    va_start(ap,fmt);
    vsnprintf(E.statusmsg,sizeof(E.statusmsg),fmt,ap);
    va_end(ap);
    E.statusmsg_time = time(NULL);
}

/* =============================== Find mode ================================ */

#define KILO_QUERY_LEN 256

/* Where the n bytes of query first appear in the len bytes at s: their
 * offset, or -1. */
static long findBytes(const char *s, size_t len, const char *query, size_t n) {
    if (n == 0) return 0;
    for (size_t i = 0; i + n <= len; i++) {
        const char *p = memchr(s + i, query[0], len - n + 1 - i);
        if (p == NULL) return -1;
        i = (size_t)(p - s);
        if (memcmp(p, query, n) == 0) return (long)i;
    }
    return -1;
}

/* Where the last row starts (there must be one). */
static size_t lastRowStart(void) {
    size_t len = E.text->len;
    char c;
    editorRead(len-1, &c, 1);
    return lineStart(c == '\n' ? len-1 : len);
}

/* Ctrl-F: search as you type. The message line becomes the search prompt,
 * and this function runs its own loop of drawing the screen and reading a
 * key until Enter or Escape. Every change to the query searches again from
 * the top of the file, and the view jumps to the first row that has a
 * match, with that row at the top of the screen. Rows are read one after
 * another, from the row of the last match, forwards or back. */
void editorFind(int fd) {
    char query[KILO_QUERY_LEN+1] = {0};
    int qlen = 0;
    int last_match = -1; /* Last line where a match was found. -1 for none. */
    size_t last_start = 0; /* and where it starts */
    int find_next = 0; /* if 1 search next, if -1 search prev. */
    char *row = NULL;
    size_t rowcap = 0;

    /* Where the cursor and the view were, for Escape to go back to. */
    int saved_cx = E.cx, saved_cy = E.cy;
    int saved_coloff = E.coloff, saved_rowoff = E.rowoff;
    size_t saved_topoff = E.topoff;

    while(1) {
        editorSetStatusMessage(
            "Search: %s (Use ESC/Arrows/Enter)", query);
        editorRefreshScreen();

        int c = editorReadKey(fd);
        if (c == DEL_KEY || c == CTRL_H || c == BACKSPACE) {
            if (qlen != 0) query[--qlen] = '\0';
            last_match = -1;
        } else if (c == ESC || c == ENTER) {
            if (c == ESC) {
                E.cx = saved_cx; E.cy = saved_cy;
                E.coloff = saved_coloff; E.rowoff = saved_rowoff;
                E.topoff = saved_topoff;
                rowsChanged();
            }
            editorSetStatusMessage("");
            free(row);
            return;
        } else if (c == ARROW_RIGHT || c == ARROW_DOWN) {
            find_next = 1;
        } else if (c == ARROW_LEFT || c == ARROW_UP) {
            find_next = -1;
        } else if (c < 256 && isprint(c)) {
            if (qlen < KILO_QUERY_LEN) {
                query[qlen++] = c;
                query[qlen] = '\0';
                last_match = -1;
            }
        }

        /* Search occurrence. */
        if (last_match == -1) find_next = 1;
        if (find_next) {
            int numrows = editorNumRows();
            int i, current = last_match;
            size_t start = last_start;
            long match = -1;

            for (i = 0; i < numrows; i++) {
                if (find_next == 1) {
                    if (current == -1 || current == numrows-1) {
                        current = 0;
                        start = 0;
                    } else {
                        current++;
                        start = findNewline(start) + 1;
                    }
                } else {
                    if (current <= 0) {
                        current = numrows-1;
                        start = lastRowStart();
                    } else {
                        current--;
                        start = lineStart(start-1);
                    }
                }
                size_t end = findNewline(start);
                if (rowcap < end - start + 1) {
                    free(row);
                    rowcap = end - start + 1;
                    row = xmalloc(rowcap);
                }
                editorRead(start, row, end - start);
                match = findBytes(row, end - start, query, (size_t)qlen);
                if (match >= 0) break;
            }
            find_next = 0;

            if (match >= 0) {
                last_match = current;
                last_start = start;
                E.cy = 0;
                E.cx = (int)match;
                E.rowoff = current;
                E.topoff = start;
                rowsChanged();
                E.coloff = 0;
                /* Scroll horizontally as needed. */
                if (E.cx >= E.screencols) {
                    int diff = E.cx - E.screencols + 1;
                    E.cx -= diff;
                    E.coloff += diff;
                }
            }
        }
    }
}

/* ========================= Editor events handling  ======================== */

/* Move the cursor one step with an arrow key, scrolling the view when it
 * would leave the screen. Left at the start of a row goes to the end of
 * the row above, right at the end of a row to the start of the next. Up
 * and down keep the column, unless the new row is shorter. */
void editorMoveCursor(int key) {
    int filerow = E.rowoff+E.cy;
    int filecol = E.coloff+E.cx;
    int rowlen;
    int numrows = editorNumRows();

    switch(key) {
    case ARROW_LEFT:
        if (E.cx == 0) {
            if (E.coloff) {
                E.coloff--;
            } else {
                if (filerow > 0) {
                    if (E.cy == 0)
                        editorScrollUp();
                    else
                        E.cy--;
                    E.cx = rowSize(filerow-1);
                    if (E.cx > E.screencols-1) {
                        E.coloff = E.cx-E.screencols+1;
                        E.cx = E.screencols-1;
                    }
                }
            }
        } else {
            E.cx -= 1;
        }
        break;
    case ARROW_RIGHT:
        if (filerow < numrows && filecol < rowSize(filerow)) {
            if (E.cx == E.screencols-1) {
                E.coloff++;
            } else {
                E.cx += 1;
            }
        } else if (filerow < numrows && filecol == rowSize(filerow)) {
            E.cx = 0;
            E.coloff = 0;
            if (E.cy == E.screenrows-1) {
                editorScrollDown();
            } else {
                E.cy += 1;
            }
        }
        break;
    case ARROW_UP:
        if (E.cy == 0) {
            if (E.rowoff) editorScrollUp();
        } else {
            E.cy -= 1;
        }
        break;
    case ARROW_DOWN:
        if (filerow < numrows) {
            if (E.cy == E.screenrows-1) {
                editorScrollDown();
            } else {
                E.cy += 1;
            }
        }
        break;
    }
    /* Fix cx if the current line has not enough chars. */
    filerow = E.rowoff+E.cy;
    filecol = E.coloff+E.cx;
    rowlen = filerow < numrows ? rowSize(filerow) : 0;
    if (filecol > rowlen) {
        E.cx -= filecol-rowlen;
        if (E.cx < 0) {
            E.coloff += E.cx;
            E.cx = 0;
        }
    }
}

// @from 03.03
/* Ctrl-Z, Ctrl-Y: undo the last edit, or redo the last undone, and put
 * the cursor where it happened. */
static void editorUndo(int redo) {
    Change c;
    if (!(redo ? undo_redo : undo_undo)(&E.undo, E.text, &c)) {
        editorSetStatusMessage(redo ? "Nothing to redo" : "Nothing to undo");
        return;
    }
    if (c.erased)
        afterErase(c.pos, c.bytes, c.n);
    else
        afterInsert(c.pos, c.bytes, c.n);
    editorGoTo(c.cursor);
}

// @end
/* Read one key and act on it. */
#define KILO_QUIT_TIMES 3
void editorProcessKeypress(int fd) {
    /* With unsaved changes, Ctrl-Q has to be pressed KILO_QUIT_TIMES more
     * times to quit; any other key starts the count again. */
    static int quit_times = KILO_QUIT_TIMES;
    int typing = 0;     /* the key typed into the text */ // @from 03.03

    int c = editorReadKey(fd);
    switch(c) {
    case ENTER:         /* Enter */
        editorInsertNewline();
        typing = 1;                 // @from 03.03
        break;
    case CTRL_C:        /* Ctrl-c */
        /* Ignored: losing the changes to the file should not be one
         * keystroke away. */
        break;
    case CTRL_Q:        /* Ctrl-q */
        if (E.dirty && quit_times) {
            editorSetStatusMessage("WARNING!!! File has unsaved changes. "
                "Press Ctrl-Q %d more times to quit.", quit_times);
            quit_times--;
            return;
        }
        exit(0);
        break;
    case CTRL_S:        /* Ctrl-s */
        editorSave();
        break;
    case CTRL_F:
        editorFind(fd);
        break;
    case CTRL_Z:        /* Ctrl-z */
        // @from 03.03
        editorUndo(0);
        // @else
        // editorSetStatusMessage("Nothing to undo: this editor keeps no history");
        // @end
        break;
    case CTRL_Y:        /* Ctrl-y */
        // @from 03.03
        editorUndo(1);
        // @else
        // editorSetStatusMessage("Nothing to redo: this editor keeps no history");
        // @end
        break;
    case BACKSPACE:     /* Backspace */
    case CTRL_H:        /* Ctrl-h */
    case DEL_KEY:
        editorDelChar();
        typing = 1;                 // @from 03.03
        break;
    case PAGE_UP:
    case PAGE_DOWN:
        /* To the top (or bottom) line of the screen first, then a
         * screenful of moves up (or down). */
        if (c == PAGE_UP && E.cy != 0)
            E.cy = 0;
        else if (c == PAGE_DOWN && E.cy != E.screenrows-1)
            E.cy = E.screenrows-1;
        {
        int times = E.screenrows;
        while(times--)
            editorMoveCursor(c == PAGE_UP ? ARROW_UP:
                                            ARROW_DOWN);
        }
        break;

    case ARROW_UP:
    case ARROW_DOWN:
    case ARROW_LEFT:
    case ARROW_RIGHT:
        editorMoveCursor(c);
        break;
    case CTRL_L: /* ctrl+l, clear screen */
        /* Nothing to do: the screen is drawn again after every key. */
        break;
    case ESC:
        /* Nothing to do for ESC in this mode. */
        break;
    case HOME_KEY:
    case END_KEY:
        /* Not bound to anything. */
        break;
    default:
        /* Any other key is text. */
        editorInsertChar(c);
        typing = 1;                 // @from 03.03
        break;
    }

    quit_times = KILO_QUIT_TIMES; /* Reset it to the original value. */
    // @from 03.03
    /* Any key but typing ends the edit being typed: the next starts a new one. */
    if (!typing) undo_break(&E.undo);
    // @end
}

/* Measure the window into E.screenrows and E.screencols, or exit. The last
 * two lines are kept for the status bar and the message line. */
void updateWindowSize(void) {
    if (getWindowSize(STDIN_FILENO,STDOUT_FILENO,
                      &E.screenrows,&E.screencols) == -1) {
        perror("Unable to query the screen for size (columns / rows)");
        exit(1);
    }
    E.screenrows -= 2; /* Get room for status bar. */
}

/* SIGWINCH: the kernel's signal that the window changed size. Measure it
 * again, keep the cursor on the screen, and draw everything at the new
 * size. */
void handleSigWinCh(int unused __attribute__((unused))) {
    updateWindowSize();
    if (E.cy >= E.screenrows) E.cy = E.screenrows - 1;
    if (E.cx >= E.screencols) E.cx = E.screencols - 1;
    editorRefreshScreen();
}

/* Set E to an empty editor the size of the window. */
void initEditor(void) {
    E.cx = 0;
    E.cy = 0;
    E.rowoff = 0;
    E.topoff = 0;
    E.coloff = 0;
    E.dirty = 0;
    updateWindowSize();
    signal(SIGWINCH, handleSigWinCh);
}

/* ================================ Replay ================================== */

/* The bytes TEXT of a script's "type" or "paste" stands for, into out
 * (as long as text, at most): its length. */
static size_t replayText(const char *text, char *out, int lineno) {
    size_t n = 0;
    for (const char *p = text; *p; p++) {
        if (*p != '\\') {
            out[n++] = *p;
            continue;
        }
        p++;
        if (*p == 'n') out[n++] = '\n';
        else if (*p == 't') out[n++] = '\t';
        else if (*p == '\\') out[n++] = '\\';
        else if (*p == 'x' && isxdigit((unsigned char)p[1]) && isxdigit((unsigned char)p[2])) {
            char hex[3] = {p[1], p[2], 0};
            out[n++] = (char)strtol(hex, NULL, 16);
            p += 2;
        } else die("script line %d: no escape '\\%.1s' (have: \\n \\t \\\\ \\xHH)", lineno, p);
    }
    return n;
}

/* A script's count: arg, or 1 when there is none (if one is allowed). */
static size_t replayCount(const char *word, const char *arg, int lineno, int optional) {
    char *end;
    if (*arg == '\0' && optional) return 1;
    unsigned long long v = strtoull(arg, &end, 10);
    if (*arg == '\0' || !isdigit((unsigned char)*arg) || *end != '\0')
        die("script line %d: %s wants a count, not '%s'", lineno, word, arg);
    return (size_t)v;
}

/* goto LINE:COL: the byte where column col of line line is (both from 1). */
static size_t replayLine(const char *arg, int lineno) {
    unsigned long line, col;
    char *end;
    line = strtoul(arg, &end, 10);
    if (end == arg || *end != ':' || !isdigit((unsigned char)end[1]))
        die("script line %d: goto wants a byte or LINE:COL, not '%s'", lineno, arg);
    col = strtoul(end+1, &end, 10);
    if (*end != '\0' || line == 0 || col == 0)
        die("script line %d: goto wants a byte or LINE:COL, not '%s'", lineno, arg);
    size_t start = 0;
    for (unsigned long i = 1; i < line; i++) {
        size_t nl = findNewline(start);
        if (nl == E.text->len)
            die("script line %d: goto %s: the last line is %lu", lineno, arg, i);
        start = nl + 1;
    }
    size_t size = findNewline(start) - start;
    if (col - 1 > size)
        die("script line %d: goto %s: line %lu has %zu bytes", lineno, arg, line, size);
    return start + col - 1;
}

/* --replay: make the edits of a script to the text, with no screen. The
 * cursor is a byte of the text, and every edit is made through the same
 * functions the keys use. */
static void replay(const char *script) {
    FILE *f = open_input(script);
    char *line = NULL, *bytes = NULL;
    size_t linecap = 0, cursor = 0;
    ssize_t got;
    int lineno = 0;

    while ((got = getline(&line, &linecap, f)) != -1) {
        lineno++;
        if (got > 0 && line[got-1] == '\n') line[--got] = '\0';
        if (got == 0 || line[0] == '#') continue;
        char *arg = strchr(line, ' ');
        if (arg) *arg++ = '\0';
        else arg = line + got;
        const char *word = line;
        size_t n, i;

        // @from 03.03
        /* Only typing joins the edit before it. */
        if (strcmp(word, "type") != 0 && strcmp(word, "back") != 0)
            undo_break(&E.undo);
        // @end
        if (strcmp(word, "goto") == 0) {
            if (strcmp(arg, "end") == 0) {
                cursor = E.text->len;
            } else if (strchr(arg, ':')) {
                cursor = replayLine(arg, lineno);
            } else {
                n = replayCount(word, arg, lineno, 0);
                if (n > E.text->len)
                    die("script line %d: goto %zu: the text is %zu bytes", lineno, n, E.text->len);
                cursor = n;
            }
        } else if (strcmp(word, "type") == 0 || strcmp(word, "paste") == 0) {
            bytes = realloc(bytes, strlen(arg) + 1);
            n = replayText(arg, bytes, lineno);
            if (word[0] == 't') {
                for (i = 0; i < n; i++)
                    editorInsertText(cursor++, bytes + i, 1, 1);
            } else if (n > 0) {
                editorInsertText(cursor, bytes, n, 0);
                cursor += n;
            }
        } else if (strcmp(word, "back") == 0) {
            n = replayCount(word, arg, lineno, 0);
            for (i = 0; i < n && cursor > 0; i++)
                editorEraseText(--cursor, 1, 1);
        } else if (strcmp(word, "delete") == 0) {
            n = replayCount(word, arg, lineno, 0);
            if (n > E.text->len - cursor) n = E.text->len - cursor;
            if (n > 0) editorEraseText(cursor, n, 0);
        // @from 03.03
        } else if (strcmp(word, "undo") == 0 || strcmp(word, "redo") == 0) {
            n = replayCount(word, arg, lineno, 1);
            for (i = 0; i < n; i++) {
                Change c;
                if (!(word[0] == 'u' ? undo_undo : undo_redo)(&E.undo, E.text, &c)) break;
                if (c.erased)
                    afterErase(c.pos, c.bytes, c.n);
                else
                    afterInsert(c.pos, c.bytes, c.n);
                cursor = c.cursor;
            }
        // @end
        } else if (strcmp(word, "print") == 0) {
            if (text_write(E.text, stdout) == -1 || fflush(stdout) == EOF)
                die("standard output: %s", strerror(errno));
        } else if (strcmp(word, "save") == 0) {
            if (editorSave() != 0)
                die("%s", E.statusmsg);
        } else {
            die("script line %d: unknown command '%s'", lineno, word);
        }
    }
    free(line);
    free(bytes);
    close_input(f);
}

static void usage(void) {
    // @from 03.02
    die("usage: edit [--algo=NAME] [--replay SCRIPT] FILE");
    // @else
    // die("usage: edit [--replay SCRIPT] FILE");
    // @end
}

int main(int argc, char **argv) {
    const char *script = NULL;
    int i;

    progname = "edit";
    ds_stats_at_exit(editorPrintStats);
    // @from 03.02
    // @from 03.05
    const char *algo = "tree";
    // @else
    // const char *algo = "gap";
    // @end
    // @end
    for (i = 1; i < argc; i++) {
        const char *a = argv[i];
        // @from 03.02
        if (strncmp(a, "--algo=", 7) == 0) {
            algo = a + 7;
            continue;
        }
        // @end
        if (strcmp(a, "--replay") == 0) {
            if (i + 1 == argc) usage();
            script = argv[++i];
            continue;
        }
        if (strcmp(a, "--") == 0) {
            i++;
            break;
        }
        if (a[0] == '-' && a[1] == '-')
            die("unknown option '%s'", a);
        if (a[0] == '-' && a[1] != '\0')
            usage();
        break;
    }
    if (argc - i != 1) usage();

    // @from 03.02
    editorOpen(argv[i], editorPickAlgo(algo));
    // @else
    // editorOpen(argv[i], flat_open);
    // @end
    undo_init(&E.undo);     // @from 03.03
    if (script) {
        replay(script);
        return 0;
    }

    /* A screen needs a terminal; anything else would wait for keys that
     * never come. */
    if (!isatty(STDIN_FILENO) || !isatty(STDOUT_FILENO))
        die("%s: standard input and output must be a terminal (or use --replay SCRIPT)", argv[i]);
    /* DS_TRACE would write over the screen. */
    if (isatty(STDERR_FILENO)) text_trace_off();
    E.newlines = countNewlines(0, E.text->len);
    enableRawMode(STDIN_FILENO);
    /* The window is measured in raw mode. When the kernel does not know its
     * size, the terminal is asked, and its answer must reach us a byte at a
     * time. */
    initEditor();
    // @from 03.03
    editorSetStatusMessage(
        "HELP: Ctrl-S = save | Ctrl-Q = quit | Ctrl-F = find | Ctrl-Z/Y = undo/redo");
    // @else
    // editorSetStatusMessage(
    //     "HELP: Ctrl-S = save | Ctrl-Q = quit | Ctrl-F = find");
    // @end
    while(1) {
        editorRefreshScreen();
        editorProcessKeypress(STDIN_FILENO);
    }
    return 0;
}
