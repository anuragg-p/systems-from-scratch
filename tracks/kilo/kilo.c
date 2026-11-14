/* kilo: a text editor in one C file, with no library between it and the
 * terminal. It puts the terminal in raw mode, reads keys a byte at a time,
 * keeps the file as an array of rows, and redraws the whole screen after
 * every key with VT100 escape codes, in a single write.
 *
 * This file is derived from kilo.c by Salvatore Sanfilippo,
 * https://github.com/antirez/kilo (commit 323d93b). It keeps his functions
 * and their structure. The syntax highlighting is left out, the comments
 * are rewritten as notes for the reader, and the few places where the code
 * itself differs from his say so in a comment. His notice follows.
 *
 * -----------------------------------------------------------------------
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

#define KILO_VERSION "0.0.1"

// @from 03.01
// getline() is POSIX, not C99: on Linux, ask for it. macOS shows it anyway.
// @else
// // POSIX is more than C99: on Linux, ask for it. macOS shows it anyway.
// @end
#ifdef __linux__
#define _POSIX_C_SOURCE 200809L
#endif

#include <termios.h>
#include <stdlib.h>
#include <stdio.h>
#include <stdint.h>     // @from 03.03
#include <errno.h>
#include <string.h>     // @from 01.03
#include <ctype.h>      // @from 05.01
#include <time.h>       // @from 03.04
#include <sys/types.h>  // @from 03.01
#include <sys/ioctl.h>  // @from 01.03
#include <unistd.h>
#include <stdarg.h>     // @from 03.04
#include <fcntl.h>      // @from 04.04
#include <signal.h>     // @from 02.01

// @from 03.01
// @from 03.03
/* One line of the file. chars is the line as it is in the file, without
 * its newline; render is the same line as the screen shows it, with each
 * tab turned into spaces. Both end in a '\0' that size and rsize do not
 * count. */
// @else
// /* One line of the file. chars is the line as it is in the file, without
//  * its newline, and ends in a '\0' that size does not count. */
// @end
typedef struct erow {
    int size;           // bytes in chars
    int rsize;          // bytes in render @from 03.03
    char *chars;        // the line as the file has it
    char *render;       // the line as the screen shows it @from 03.03
} erow;

// @end
/* Everything the editor knows, in one global. */
struct editorConfig {
    int cx,cy;          // the cursor: column and row on the screen, not in the file @from 02.01
    int rowoff;         // the file row on the top line: the cursor is on row rowoff+cy @from 03.01
    int coloff;         // the file column in the leftmost column: the cursor is on coloff+cx @from 03.01
    int screenrows;     // rows of text the screen has room for @from 01.03
    int screencols;     // columns the screen has @from 01.03
    int numrows;        // rows in the file @from 03.01
    int rawmode;        // is the terminal in raw mode now?
    erow *row;          // the rows, E.numrows of them @from 03.01
    // @from 04.01
    // @from 04.04
    int dirty;          // changes since the file was opened or saved; 0: none
    // @else
    // int dirty;          // changes since the file was opened; 0: none
    // @end
    // @end
    char *filename;     // the file being edited @from 03.01
    char statusmsg[80];         // the message under the status bar @from 03.04
    time_t statusmsg_time;      // when it was set: it shows for 5 seconds @from 03.04
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
        ESC = 27,           /* Escape */
        BACKSPACE =  127,   /* Backspace */
        // @from 01.02
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
        // @end
};

void editorSetStatusMessage(const char *fmt, ...);  // @from 03.04

/* ======================= Low level terminal handling ====================== */

/* The terminal's settings as they were before raw mode, to put back at exit. */
static struct termios orig_termios;

// @internal
/* Stands in for code a workspace has cut out: puts the terminal back as it
 * was, names the lesson whose code is missing, and exits with status 3. */
__attribute__((noreturn)) void kiloTodo(const char *lesson, const char *what) {
    if (E.rawmode) tcsetattr(STDIN_FILENO,TCSAFLUSH,&orig_termios);
    fprintf(stderr,"\r\nkilo: %s: %s not written yet\r\n",lesson,what);
    _exit(3);
}
// @end

/* Leave raw mode: put back the settings enableRawMode() saved. Nothing is
 * checked; this runs on the way out, when nothing could be done about it. */
void disableRawMode(int fd) {
    // @build 01.01 leave raw mode
    // If the terminal is in raw mode, put orig_termios back with tcsetattr()
    // and note that raw mode is off.
    if (E.rawmode) {
        tcsetattr(fd,TCSAFLUSH,&orig_termios);
        E.rawmode = 0;
    }
    // @end
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
    // @build 01.01 enter raw mode
    // Save the terminal's settings in orig_termios and arrange for
    // editorAtExit() to run at exit. Then switch off, on a copy: break,
    // CR-to-NL, parity check, bit stripping and flow control on input; all
    // output processing; echo, canonical mode, the extended keys and
    // signals. Set 8-bit characters, and make read() return after 0.1 s
    // with whatever it has, even nothing. Return -1 (errno ENOTTY) if
    // standard input is not a terminal.
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
    // @end
}

/* Read one key. Most keys are one byte; the arrows, Home, End, Delete and
 * Page Up/Down arrive as escape sequences, ESC followed by two or three
 * bytes, which come back as one of the codes above 1000. A lone ESC is the
 * Escape key: nothing follows it within 0.1 s. */
int editorReadKey(int fd) {
    // @build 01.02 read one key
    // Wait for a byte. If it is ESC, read up to three more and turn
    // ESC [ A..D, ESC [ H/F, ESC O H/F and ESC [ 3/5/6 ~ into ARROW_*,
    // HOME_KEY, END_KEY, DEL_KEY and PAGE_UP/DOWN. If nothing follows the
    // ESC within VTIME, return ESC. Any other byte is the key. Exit if
    // read() fails.
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
            return c;
        }
    }
    // @end
}

/* Ask the terminal where its cursor is: write ESC [ 6 n, and the terminal
 * answers on the input side, as if typed, with ESC [ row ; col R. Rows and
 * columns count from 1. Returns 0, or -1 if the answer does not parse. */
int getCursorPosition(int ifd, int ofd, int *rows, int *cols) {
    // @build 01.03 ask the terminal where the cursor is
    // Write ESC [ 6 n to ofd. Read the answer from ifd up to its 'R' (at
    // most 31 bytes) and parse "ESC [ rows ; cols". Return 0 with *rows and
    // *cols set, or -1.
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
    // @end
}

/* The size of the terminal window. The kernel knows it (TIOCGWINSZ); when
 * it does not say, the terminal itself is asked: move the cursor right and
 * down as far as it goes, ask where it ended up, and put it back. Returns
 * 0, or -1 on error. */
int getWindowSize(int ifd, int ofd, int *rows, int *cols) {
    // @build 01.03 the window size
    // Ask the kernel with ioctl(TIOCGWINSZ) on standard output. If that
    // fails or says 0 columns, use getCursorPosition(): note where the
    // cursor is, send ESC [ 999 C ESC [ 999 B (the terminal stops at its
    // edges), ask again (that is the size), and move the cursor back.
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
    // @end
}

// @from 03.01
/* ======================= Editor rows implementation ======================= */

// @end
/* Make row->render from row->chars: the same bytes, with each tab turned
 * into spaces up to the next column that is a multiple of 8. The screen
 * draws render, never chars. */
void editorUpdateRow(erow *row) {
    // @build 03.03 render a row
    // Free the old render. Count the tabs in chars and allocate room for
    // eight spaces each (exit if that is more than 4 GB). Copy chars,
    // writing each tab as one space and then spaces up to the next
    // multiple of 8. Set rsize and end render with '\0'.
    unsigned int tabs = 0;
    int j, idx;

    free(row->render);
    for (j = 0; j < row->size; j++)
        if (row->chars[j] == TAB) tabs++;

    unsigned long long allocsize =
        (unsigned long long) row->size + tabs*8 + 1;
    if (allocsize > UINT32_MAX) {
        printf("Some line of the edited file is too long for kilo\n");
        exit(1);
    }

    row->render = malloc(row->size + tabs*8 + 1);
    idx = 0;
    for (j = 0; j < row->size; j++) {
        if (row->chars[j] == TAB) {
            row->render[idx++] = ' ';
            /* The original kilo pads while (idx+1) % 8 != 0, which puts
             * its tab stops at columns 7, 15, 23 and so on: one short of
             * where a terminal or any other program puts them. */
            while(idx % 8 != 0) row->render[idx++] = ' ';
        } else {
            row->render[idx++] = row->chars[j];
        }
    }
    row->rsize = idx;
    row->render[idx] = '\0';
    // @end
}

/* Insert a row holding the len bytes at s, at position at (0 to
 * E.numrows), moving the rows from there down by one. */
void editorInsertRow(int at, char *s, size_t len) {
    // @build 03.01 insert a row
    // Ignore an at past the end. Grow E.row by one, move the rows from at
    // on down one place, and fill in row at with a copy of s (and its
    // '\0'). Count the new row in E.numrows.
    if (at > E.numrows) return;
    E.row = realloc(E.row,sizeof(erow)*(E.numrows+1));
    if (at != E.numrows) {
        memmove(E.row+at+1,E.row+at,sizeof(E.row[0])*(E.numrows-at));
    }
    E.row[at].size = len;
    E.row[at].chars = malloc(len+1);
    memcpy(E.row[at].chars,s,len+1);
    E.row[at].render = NULL;        // @from 03.03
    E.row[at].rsize = 0;            // @from 03.03
    editorUpdateRow(E.row+at);      // @from 03.03
    E.numrows++;
    E.dirty++;                      // @from 04.01
    // @end
}

/* Free what a row points to (not the row itself: it is part of E.row). */
void editorFreeRow(erow *row) {
    // @build 04.03 free a row
    // Free the row's render and chars.
    free(row->render);
    free(row->chars);
    // @end
}

/* Remove the row at position at, moving the rows below it up by one. */
void editorDelRow(int at) {
    // @build 04.03 delete a row
    // Ignore an at past the last row. Free the row, move the rows after it
    // up one place, and count one row fewer and one change more.
    erow *row;

    if (at >= E.numrows) return;
    row = E.row+at;
    editorFreeRow(row);
    memmove(E.row+at,E.row+at+1,sizeof(E.row[0])*(E.numrows-at-1));
    E.numrows--;
    E.dirty++;
    // @end
}

/* The whole file as one string, every row followed by "\n", in a new
 * allocation the caller frees. *buflen is its length, without the '\0'. */
char *editorRowsToString(int *buflen) {
    // @build 04.04 the file as one string
    // Add up the row sizes plus one newline each, allocate that and one
    // more for '\0', and copy every row in, each followed by '\n'.
    char *buf = NULL, *p;
    int totlen = 0;
    int j;

    /* Compute count of bytes */
    for (j = 0; j < E.numrows; j++)
        totlen += E.row[j].size+1; /* +1 is for "\n" at end of every row */
    *buflen = totlen;
    totlen++; /* Also make space for nulterm */

    p = buf = malloc(totlen);
    for (j = 0; j < E.numrows; j++) {
        memcpy(p,E.row[j].chars,E.row[j].size);
        p += E.row[j].size;
        *p = '\n';
        p++;
    }
    *p = '\0';
    return buf;
    // @end
}

/* Insert the character c into a row at column at. A column past the end of
 * the row is allowed: the gap is filled with spaces first. */
void editorRowInsertChar(erow *row, int at, int c) {
    // @build 04.01 insert a character into a row
    // If at is past the end, grow chars to hold the spaces, c and '\0',
    // and fill the gap with spaces. Otherwise grow it by one and move the
    // bytes from at on (with the '\0') one place right. Put c at at, render
    // the row again, and count a change.
    if (at > row->size) {
        /* Pad the string with spaces if the insert location is outside the
         * current length by more than a single character. */
        int padlen = at-row->size;
        /* In the next line +2 means: new char and null term. */
        row->chars = realloc(row->chars,row->size+padlen+2);
        memset(row->chars+row->size,' ',padlen);
        row->chars[row->size+padlen+1] = '\0';
        row->size += padlen+1;
    } else {
        /* If we are in the middle of the string just make space for 1 new
         * char plus the (already existing) null term. */
        row->chars = realloc(row->chars,row->size+2);
        memmove(row->chars+at+1,row->chars+at,row->size-at+1);
        row->size++;
    }
    row->chars[at] = c;
    editorUpdateRow(row);
    E.dirty++;
    // @end
}

/* Append len bytes at s to the end of a row. */
void editorRowAppendString(erow *row, char *s, size_t len) {
    // @build 04.03 append to a row
    // Grow chars by len, copy s after the row's bytes, end it with '\0',
    // render the row again and count a change.
    row->chars = realloc(row->chars,row->size+len+1);
    memcpy(row->chars+row->size,s,len);
    row->size += len;
    row->chars[row->size] = '\0';
    editorUpdateRow(row);
    E.dirty++;
    // @end
}

/* Delete the character at column at of a row. */
void editorRowDelChar(erow *row, int at) {
    // @build 04.03 delete a character from a row
    // Ignore an at past the end. Move the bytes after at (with the '\0')
    // one place left, and count one byte fewer and one change more.
    if (row->size <= at) return;
    memmove(row->chars+at,row->chars+at+1,row->size-at);
    editorUpdateRow(row);
    row->size--;
    E.dirty++;
    // @end
}

/* Insert a character where the cursor is, and move the cursor past it. */
void editorInsertChar(int c) {
    // @build 04.01 insert at the cursor
    // Find the file row and column under the cursor. Below the last row,
    // first add empty rows down to the cursor. Insert c there, then move
    // the cursor one column right, or scroll the view right by one if the
    // cursor is in the last column.
    int filerow = E.rowoff+E.cy;
    int filecol = E.coloff+E.cx;
    erow *row = (filerow >= E.numrows) ? NULL : &E.row[filerow];

    /* If the row where the cursor is currently located does not exist in our
     * logical representaion of the file, add enough empty rows as needed. */
    if (!row) {
        while(E.numrows <= filerow)
            editorInsertRow(E.numrows,"",0);
    }
    row = &E.row[filerow];
    editorRowInsertChar(row,filecol,c);
    if (E.cx == E.screencols-1)
        E.coloff++;
    else
        E.cx++;
    E.dirty++;
    // @end
}

/* Enter: split the row at the cursor, and move the cursor to the start of
 * the new row below. */
void editorInsertNewline(void) {
    // @build 04.02 split the line at the cursor
    // Just below the last row, add an empty row. At column 0, insert an
    // empty row above. Otherwise insert the part of the row from the cursor
    // on as a new row below, and cut the row at the cursor. Then put the
    // cursor at column 0 of the next row, scrolling down one row if it was
    // on the bottom line.
    int filerow = E.rowoff+E.cy;
    int filecol = E.coloff+E.cx;
    erow *row = (filerow >= E.numrows) ? NULL : &E.row[filerow];

    if (!row) {
        if (filerow == E.numrows) {
            editorInsertRow(filerow,"",0);
            goto fixcursor;
        }
        return;
    }
    /* If the cursor is over the current line size, we want to conceptually
     * think it's just over the last character. */
    if (filecol >= row->size) filecol = row->size;
    if (filecol == 0) {
        editorInsertRow(filerow,"",0);
    } else {
        /* We are in the middle of a line. Split it between two rows. */
        editorInsertRow(filerow+1,row->chars+filecol,row->size-filecol);
        row = &E.row[filerow];
        row->chars[filecol] = '\0';
        row->size = filecol;
        editorUpdateRow(row);
    }
fixcursor:
    if (E.cy == E.screenrows-1) {
        E.rowoff++;
    } else {
        E.cy++;
    }
    E.cx = 0;
    E.coloff = 0;
    // @end
}

/* Backspace: delete the character left of the cursor. At the start of a
 * row, join the row onto the end of the one above. */
void editorDelChar(void) {
    // @build 04.03 delete at the cursor
    // Nothing to do below the last row or at the very start of the file.
    // At column 0, append this row to the one above, delete it, and put
    // the cursor where the two now meet (scrolling up, or right, to keep
    // it on the screen). Otherwise delete the character before the cursor
    // and move the cursor (or the view) one column left.
    int filerow = E.rowoff+E.cy;
    int filecol = E.coloff+E.cx;
    erow *row = (filerow >= E.numrows) ? NULL : &E.row[filerow];

    if (!row || (filecol == 0 && filerow == 0)) return;
    if (filecol == 0) {
        /* Handle the case of column 0, we need to move the current line
         * on the right of the previous one. */
        filecol = E.row[filerow-1].size;
        editorRowAppendString(&E.row[filerow-1],row->chars,row->size);
        editorDelRow(filerow);
        row = NULL;
        if (E.cy == 0)
            E.rowoff--;
        else
            E.cy--;
        E.cx = filecol;
        if (E.cx >= E.screencols) {
            /* The original kilo computes (E.screencols-E.cx)+1 here,
             * which is negative: the cursor goes off the screen, and the
             * next screen is drawn from before the start of the row. */
            int shift = (E.cx-E.screencols)+1;
            E.cx -= shift;
            E.coloff += shift;
        }
    } else {
        editorRowDelChar(row,filecol-1);
        if (E.cx == 0 && E.coloff)
            E.coloff--;
        else
            E.cx--;
    }
    if (row) editorUpdateRow(row);
    E.dirty++;
    // @end
}

// @from 03.01
// @from 04.04
/* Read a file into E.row, one row per line. A file that does not exist is
 * an empty file, created by the first save. Returns 0, or 1 when there was
 * no file. */
// @else
// /* Read a file into E.row, one row per line. A file that does not exist is
//  * an empty file. Returns 0, or 1 when there was no file. */
// @end
// @end
int editorOpen(char *filename) {
    // @build 03.01 read the file into rows
    // Keep a copy of filename in E.filename. Open the file; if it does not
    // exist return 1 with no rows, and on any other error print it and
    // exit. Read it with getline(), strip the line ending ("\n" or "\r\n")
    // and append each line as a row. Return 0.
    FILE *fp;

    E.dirty = 0;                    // @from 04.01
    free(E.filename);
    size_t fnlen = strlen(filename)+1;
    E.filename = malloc(fnlen);
    memcpy(E.filename,filename,fnlen);

    fp = fopen(filename,"r");
    if (!fp) {
        if (errno != ENOENT) {
            perror("Opening file");
            exit(1);
        }
        return 1;
    }

    char *line = NULL;
    size_t linecap = 0;
    ssize_t linelen;
    while((linelen = getline(&line,&linecap,fp)) != -1) {
        /* The original kilo strips one byte here (an if, not a while), so
         * a "\r\n" line keeps its '\r'; drawn, the '\r' sends the cursor
         * back to column 0 and the erase after it blanks the line. */
        while (linelen && (line[linelen-1] == '\n' || line[linelen-1] == '\r'))
            line[--linelen] = '\0';
        editorInsertRow(E.numrows,line,linelen);
    }
    free(line);
    fclose(fp);
    E.dirty = 0;                    // @from 04.01
    return 0;
    // @end
}

/* Write the rows to E.filename. Returns 0, or 1 on error; either way the
 * message line says what happened. */
int editorSave(void) {
    // @build 04.04 save the file
    // Make the file's text with editorRowsToString(). Open E.filename for
    // writing, creating it (mode 0644) if need be, cut it to the new length
    // and write the text in one write(). On success clear E.dirty and say
    // "N bytes written on disk"; on any error say "Can't save! I/O error:"
    // and the reason. Free the text either way.
    int len;
    char *buf = editorRowsToString(&len);
    int fd = open(E.filename,O_RDWR|O_CREAT,0644);
    if (fd == -1) goto writeerr;

    /* Use truncate + a single write(2) call in order to make saving
     * a bit safer, under the limits of what we can do in a small editor. */
    if (ftruncate(fd,len) == -1) goto writeerr;
    if (write(fd,buf,len) != len) goto writeerr;

    close(fd);
    free(buf);
    E.dirty = 0;
    editorSetStatusMessage("%d bytes written on disk", len);
    return 0;

writeerr:
    free(buf);
    if (fd != -1) close(fd);
    editorSetStatusMessage("Can't save! I/O error: %s",strerror(errno));
    return 1;
    // @end
}

// @from 02.01
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

// @end
/* Append len bytes at s to the frame. */
void abAppend(struct abuf *ab, const char *s, int len) {
    // @build 02.01 append to the frame
    // Grow ab->b by len (give up quietly if realloc fails), copy s to its
    // end, and add len to ab->len.
    char *new = realloc(ab->b,ab->len+len);

    if (new == NULL) return;
    memcpy(new+ab->len,s,len);
    ab->b = new;
    ab->len += len;
    // @end
}

void abFree(struct abuf *ab) {
    // @build 02.01 free the frame
    // Free the frame's bytes.
    free(ab->b);
    // @end
}

/* Draw the whole screen from E: hide the cursor, go to the top left, write
 * every line (each erased to its end, so nothing of the last frame is left
 * over), then put the cursor where it belongs and show it again. One
 * write() sends it all. */
void editorRefreshScreen(void) {
    int y;
    erow *r;                        // @from 03.01
    char buf[32];
    struct abuf ab = ABUF_INIT;

    // @build 02.01 start the frame
    // Start the frame with ESC [ ? 25 l (hide the cursor) and ESC [ H
    // (cursor to the top left).
    abAppend(&ab,"\x1b[?25l",6); /* Hide cursor. */
    abAppend(&ab,"\x1b[H",3); /* Go home. */
    // @end
    for (y = 0; y < E.screenrows; y++) {
        // @from 03.01
        int filerow = E.rowoff+y;

        if (filerow >= E.numrows) {
        // @end
            // @build 02.01 the empty lines, and the welcome
            // On the line a third of the way down, write "Kilo editor --
            // version" and KILO_VERSION, cut to the screen's width and
            // centred (no padding when there is no room for it), with a "~"
            // in the first column. Every other line is "~". End each line
            // with ESC [ 0 K (erase to the end of the line) and "\r\n".
            // @from 03.01
            if (E.numrows == 0 && y == E.screenrows/3) {
            // @else
            // if (y == E.screenrows/3) {
            // @end
                char welcome[80];
                /* The original kilo says "verison" here, in the format
                 * "Kilo editor -- verison %s\x1b[0K\r\n", KILO_VERSION:
                 * the whole text, which wraps onto the next row of a
                 * screen narrower than it. %.*s cuts it to the width. */
                int welcomelen = snprintf(welcome,sizeof(welcome),
                    "%.*s\x1b[0K\r\n", E.screencols,
                    "Kilo editor -- version " KILO_VERSION);
                int padding = (E.screencols-welcomelen)/2;
                /* Not in the original kilo: there, on a screen narrower
                 * than 33 columns, padding is negative, and
                 * while(padding--) below counts down away from 0, a
                 * space at a time, and nothing is ever drawn. */
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
            // @end
            continue;               // @from 03.01
        }                           // @from 03.01

        // @build 03.01 draw a row of the file
        // Write the part of row filerow that fits on the screen, from
        // column E.coloff, at most E.screencols bytes, then ESC [ 0 K and
        // "\r\n".
        r = &E.row[filerow];

        // @from 03.03
        int len = r->rsize - E.coloff;
        // @else
        // int len = r->size - E.coloff;
        // @end
        if (len > 0) {
            if (len > E.screencols) len = E.screencols;
            /* The original kilo writes a byte at a time here, to switch
             * colours for the syntax highlighting. */
            // @from 03.03
            abAppend(&ab,r->render+E.coloff,len);
            // @else
            // abAppend(&ab,r->chars+E.coloff,len);
            // @end
        }
        abAppend(&ab,"\x1b[0K",4);
        abAppend(&ab,"\r\n",2);
        // @end
    }

    // @build 03.04 the status bar and the message line
    // Write the status bar in reverse video (ESC [ 7 m ... ESC [ 0 m): the
    // file name (at most 20 characters), the number of lines, "(modified)"
    // if E.dirty, and at the right edge "row/rows" for the cursor. On the
    // last line write E.statusmsg if it is less than 5 seconds old.
    /* The status bar: name, lines and whether it has changed on the left,
     * where the cursor is on the right. */
    abAppend(&ab,"\x1b[0K",4);
    abAppend(&ab,"\x1b[7m",4);
    char status[80], rstatus[80];
    // @from 04.01
    int len = snprintf(status, sizeof(status), "%.20s - %d lines %s",
        E.filename, E.numrows, E.dirty ? "(modified)" : "");
    // @else
    // int len = snprintf(status, sizeof(status), "%.20s - %d lines",
    //     E.filename, E.numrows);
    // @end
    int rlen = snprintf(rstatus, sizeof(rstatus),
        "%d/%d",E.rowoff+E.cy+1,E.numrows);
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
    // @end

    /* Put the cursor where it belongs: ESC [ row ; col H, counting from 1. */
    // @build 03.03 the cursor, past tabs
    // Walk the cursor's row from E.coloff to the cursor, counting one
    // screen column per byte and, for a tab, the columns up to the next
    // multiple of 8. Move the cursor there (ESC [ row ; col H, both from 1).
    /* E.cx counts bytes of chars, but on the screen each tab before the
     * cursor takes up to 8 columns. */
    int j;
    int cx = 1;
    int filerow = E.rowoff+E.cy;
    erow *row = (filerow >= E.numrows) ? NULL : &E.row[filerow];
    if (row) {
        for (j = E.coloff; j < (E.cx+E.coloff); j++) {
            /* The original kilo has 7-((cx)%8): its tab stops, as in
             * editorUpdateRow(), are one column short. */
            if (j < row->size && row->chars[j] == TAB) cx += 7-((cx-1)%8);
            cx++;
        }
    }
    snprintf(buf,sizeof(buf),"\x1b[%d;%dH",E.cy+1,cx);
    abAppend(&ab,buf,strlen(buf));
    // @end
    // @from 03.03
    // @else
    // snprintf(buf,sizeof(buf),"\x1b[%d;%dH",E.cy+1,E.cx+1);
    // abAppend(&ab,buf,strlen(buf));
    // @end
    // @build 02.01 end the frame
    // Show the cursor again (ESC [ ? 25 h), write the frame to standard
    // output in one write(), and free it.
    abAppend(&ab,"\x1b[?25h",6); /* Show cursor. */
    write(STDOUT_FILENO,ab.b,ab.len);
    abFree(&ab);
    // @end
}

/* Set the message for the line under the status bar, printf style. It is
 * shown for 5 seconds, counted from now. */
void editorSetStatusMessage(const char *fmt, ...) {
    // @build 03.04 set the message
    // Format the arguments into E.statusmsg with vsnprintf() (it is cut to
    // fit) and note the time in E.statusmsg_time.
    va_list ap;
    va_start(ap,fmt);
    vsnprintf(E.statusmsg,sizeof(E.statusmsg),fmt,ap);
    va_end(ap);
    E.statusmsg_time = time(NULL);
    // @end
}

// @from 05.01
/* =============================== Find mode ================================ */

#define KILO_QUERY_LEN 256

// @end
/* Ctrl-F: search as you type. The message line becomes the search prompt,
 * and this function runs its own loop of drawing the screen and reading a
 * key until Enter or Escape. Every change to the query searches again from
 * the top of the file, and the view jumps to the first row that has a
 * match, with that row at the top of the screen. */
void editorFind(int fd) {
    char query[KILO_QUERY_LEN+1] = {0};
    int qlen = 0;
    int last_match = -1; /* Last line where a match was found. -1 for none. */
    int find_next = 0; /* if 1 search next, if -1 search prev. */

    // @from 05.02
    /* Where the cursor and the view were, for Escape to go back to. */
    int saved_cx = E.cx, saved_cy = E.cy;
    int saved_coloff = E.coloff, saved_rowoff = E.rowoff;

    // @end
    while(1) {
        // @from 05.02
        editorSetStatusMessage(
            "Search: %s (Use ESC/Arrows/Enter)", query);
        // @else
        // editorSetStatusMessage("Search: %s (Use ESC/Enter)", query);
        // @end
        editorRefreshScreen();

        int c = editorReadKey(fd);
        if (c == DEL_KEY || c == CTRL_H || c == BACKSPACE) {
            if (qlen != 0) query[--qlen] = '\0';
            last_match = -1;
        } else if (c == ESC || c == ENTER) {
            // @build 05.02 Escape goes back
            // On Escape (not Enter), put the cursor and the view back where
            // they were before the search.
            if (c == ESC) {
                E.cx = saved_cx; E.cy = saved_cy;
                E.coloff = saved_coloff; E.rowoff = saved_rowoff;
            }
            // @end
            editorSetStatusMessage("");
            return;
        // @from 05.02
        } else if (c == ARROW_RIGHT || c == ARROW_DOWN) {
            find_next = 1;
        } else if (c == ARROW_LEFT || c == ARROW_UP) {
            find_next = -1;
        // @end
        } else if (isprint(c)) {
            if (qlen < KILO_QUERY_LEN) {
                query[qlen++] = c;
                query[qlen] = '\0';
                last_match = -1;
            }
        }

        // @build 05.01 search the rows
        // If the query changed (last_match is -1), search forwards from the
        // top. Otherwise, if find_next is set, search on from last_match in
        // that direction. Try each row once, wrapping around at either
        // end, and stop at the first whose chars contain the query. Put
        // that row at the top of the screen and the cursor on the match,
        // scrolling right if the match is past the screen's width.
        /* Search occurrence. */
        if (last_match == -1) find_next = 1;
        if (find_next) {
            char *match = NULL;
            int match_offset = 0;
            int i, current = last_match;

            for (i = 0; i < E.numrows; i++) {
                current += find_next;
                if (current == -1) current = E.numrows-1;
                else if (current == E.numrows) current = 0;
                /* The original kilo searches render, and then uses the
                 * match's place in render as a column of chars: past a tab
                 * that puts the cursor to the right of the match. */
                match = strstr(E.row[current].chars,query);
                if (match) {
                    match_offset = match-E.row[current].chars;
                    break;
                }
            }
            find_next = 0;

            if (match) {
                last_match = current;
                E.cy = 0;
                E.cx = match_offset;
                E.rowoff = current;
                E.coloff = 0;
                /* Scroll horizontally as needed. The original kilo tests
                 * E.cx > E.screencols, which leaves the cursor one column
                 * past the edge of the screen. */
                if (E.cx >= E.screencols) {
                    int diff = E.cx - E.screencols + 1;
                    E.cx -= diff;
                    E.coloff += diff;
                }
            }
        }
        // @end
    }
}

/* ========================= Editor events handling  ======================== */

/* Move the cursor one step with an arrow key, scrolling the view when it
 * would leave the screen. Left at the start of a row goes to the end of
 * the row above, right at the end of a row to the start of the next. Up
 * and down keep the column, unless the new row is shorter. */
void editorMoveCursor(int key) {
    // @build 03.02 move the cursor
    // Left: one column left, or scroll left, or to the end of the row
    // above. Right: one column right (or scroll) while inside the row, or
    // from its end to column 0 of the next. Up and down: one row, scrolling
    // at the top and bottom of the screen; down stops one row past the end
    // of the file. Then, if the cursor is past the end of its row, pull it
    // back to the end.
    int filerow = E.rowoff+E.cy;
    int filecol = E.coloff+E.cx;
    int rowlen;
    erow *row = (filerow >= E.numrows) ? NULL : &E.row[filerow];

    switch(key) {
    case ARROW_LEFT:
        if (E.cx == 0) {
            if (E.coloff) {
                E.coloff--;
            } else {
                if (filerow > 0) {
                    /* The original kilo always does E.cy-- here, which
                     * takes the cursor off the top of a scrolled screen. */
                    if (E.cy == 0)
                        E.rowoff--;
                    else
                        E.cy--;
                    E.cx = E.row[filerow-1].size;
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
        if (row && filecol < row->size) {
            if (E.cx == E.screencols-1) {
                E.coloff++;
            } else {
                E.cx += 1;
            }
        } else if (row && filecol == row->size) {
            E.cx = 0;
            E.coloff = 0;
            if (E.cy == E.screenrows-1) {
                E.rowoff++;
            } else {
                E.cy += 1;
            }
        }
        break;
    case ARROW_UP:
        if (E.cy == 0) {
            if (E.rowoff) E.rowoff--;
        } else {
            E.cy -= 1;
        }
        break;
    case ARROW_DOWN:
        if (filerow < E.numrows) {
            if (E.cy == E.screenrows-1) {
                E.rowoff++;
            } else {
                E.cy += 1;
            }
        }
        break;
    }
    /* Fix cx if the current line has not enough chars. */
    filerow = E.rowoff+E.cy;
    filecol = E.coloff+E.cx;
    row = (filerow >= E.numrows) ? NULL : &E.row[filerow];
    rowlen = row ? row->size : 0;
    if (filecol > rowlen) {
        E.cx -= filecol-rowlen;
        if (E.cx < 0) {
            E.coloff += E.cx;
            E.cx = 0;
        }
    }
    // @end
}

/* Read one key and act on it. */
#define KILO_QUIT_TIMES 3           // @from 04.04
void editorProcessKeypress(int fd) {
    // @from 04.04
    /* With unsaved changes, Ctrl-Q has to be pressed KILO_QUIT_TIMES more
     * times to quit; any other key starts the count again. */
    static int quit_times = KILO_QUIT_TIMES;

    // @end
    // @from 01.02
    int c = editorReadKey(fd);
    // @else
    // char ch;
    // if (read(fd,&ch,1) != 1) return; /* nothing typed in 0.1 s */
    // int c = (unsigned char)ch;
    // @end
    // @from 02.01
    // @else
    // /* No screen yet: show each key's code, one per line. */
    // if (c >= 32 && c < 127) printf("%d ('%c')\r\n",c,c);
    // else printf("%d\r\n",c);
    // @end
    switch(c) {
    case ENTER:         /* Enter */ // @from 04.01
        editorInsertNewline();      // @from 04.02
        break;                      // @from 04.01
    case CTRL_C:        /* Ctrl-c */
        /* Ignored: losing the changes to the file should not be one
         * keystroke away. */
        break;
    case CTRL_Q:        /* Ctrl-q */
        // @from 04.04
        if (E.dirty && quit_times) {
            editorSetStatusMessage("WARNING!!! File has unsaved changes. "
                "Press Ctrl-Q %d more times to quit.", quit_times);
            quit_times--;
            return;
        }
        // @end
        exit(0);
        break;
    case CTRL_S:        /* Ctrl-s */ // @from 04.01
        editorSave();               // @from 04.04
        break;                      // @from 04.01
    case CTRL_F:                    // @from 04.01
        editorFind(fd);             // @from 05.01
        break;                      // @from 04.01
    case BACKSPACE:     /* Backspace */ // @from 04.01
    case CTRL_H:        /* Ctrl-h */ // @from 04.01
    case DEL_KEY:                   // @from 04.01
        editorDelChar();            // @from 04.03
        break;                      // @from 04.01
    // @from 03.02
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
    // @end
    // @from 02.01
    case CTRL_L: /* ctrl+l, clear screen */
        /* Nothing to do: the screen is drawn again after every key. */
        break;
    // @end
    // @from 01.02
    case ESC:
        /* Nothing to do for ESC in this mode. */
        break;
    // @end
    // @from 04.01
    case HOME_KEY:
    case END_KEY:
        /* Not bound to anything. The original kilo has no case for them,
         * so they reach editorInsertChar() and put a stray byte (the low
         * byte of the key's code) into the text. */
        break;
    default:
        /* Any other key is text. */
        editorInsertChar(c);
        break;
    // @end
    }

    quit_times = KILO_QUIT_TIMES; /* Reset it to the original value. */ // @from 04.04
}

// @from 01.03
// @from 02.01
// @from 03.04
/* Measure the window into E.screenrows and E.screencols, or exit. The last
 * two lines are kept for the status bar and the message line. */
// @else
// /* Measure the window into E.screenrows and E.screencols, or exit. The
//  * last line is kept empty. */
// @end
// @else
// /* Measure the window into E.screenrows and E.screencols, or exit. */
// @end
// @end
void updateWindowSize(void) {
    // @build 01.03 measure the window
    // Fill E.screenrows and E.screencols with getWindowSize() (standard
    // input and output are the terminal); if it fails, print why and exit.
    if (getWindowSize(STDIN_FILENO,STDOUT_FILENO,
                      &E.screenrows,&E.screencols) == -1) {
        perror("Unable to query the screen for size (columns / rows)");
        exit(1);
    }
    // @from 02.01
    // @from 03.04
    E.screenrows -= 2; /* Get room for status bar. */
    // @else
    // E.screenrows -= 1; /* The bottom line stays empty: the "\r\n" after it would scroll the screen. */
    // @end
    // @end
    // @end
}

/* SIGWINCH: the kernel's signal that the window changed size. Measure it
 * again, keep the cursor on the screen, and draw everything at the new
 * size. */
void handleSigWinCh(int unused __attribute__((unused))) {
    // @build 02.01 draw again at a new size
    // Measure the window again with updateWindowSize(), pull the cursor
    // back inside the screen if it is now outside, and draw the screen.
    updateWindowSize();
    // @from 03.04
    /* The original kilo tests > here, which leaves the cursor on the
     * status bar when the screen shrinks to just above it. */
    // @else
    // /* The original kilo tests > here, which leaves the cursor on the
    //  * empty last line when the screen shrinks to just above it. */
    // @end
    if (E.cy >= E.screenrows) E.cy = E.screenrows - 1;
    if (E.cx >= E.screencols) E.cx = E.screencols - 1;
    editorRefreshScreen();
    // @end
}

/* Set E to an empty editor the size of the window. */
void initEditor(void) {
    // @build 01.03 set up the editor
    // Zero the cursor, the view, the rows, E.dirty and E.filename; measure
    // the window with updateWindowSize(); and have SIGWINCH call
    // handleSigWinCh().
    E.cx = 0;                       // @from 02.01
    E.cy = 0;                       // @from 02.01
    E.rowoff = 0;                   // @from 03.01
    E.coloff = 0;                   // @from 03.01
    E.numrows = 0;                  // @from 03.01
    E.row = NULL;                   // @from 03.01
    E.dirty = 0;                    // @from 04.01
    E.filename = NULL;              // @from 03.01
    updateWindowSize();
    signal(SIGWINCH, handleSigWinCh); // @from 02.01
    // @end
}

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr,"Usage: kilo <filename>\n");
        exit(1);
    }

    enableRawMode(STDIN_FILENO);
    // @from 01.03
    /* The window is measured in raw mode. When the kernel does not know its
     * size, the terminal is asked, and its answer must reach us a byte at a
     * time. The original kilo measures first and enters raw mode after:
     * the answer then waits for an Enter nobody types, and kilo hangs. */
    initEditor();
    // @from 02.01
    // @else
    // printf("This window has %d rows and %d columns.\r\n",E.screenrows,E.screencols);
    // @end
    // @end
    // @from 03.01
    editorOpen(argv[1]);
    // @else
    // (void)argv; /* The file is not read yet. */
    // @end
    // @from 03.04
    // @from 04.04
    // @from 05.01
    editorSetStatusMessage(
        "HELP: Ctrl-S = save | Ctrl-Q = quit | Ctrl-F = find");
    // @else
    // editorSetStatusMessage("HELP: Ctrl-S = save | Ctrl-Q = quit");
    // @end
    // @else
    // editorSetStatusMessage("HELP: Ctrl-Q = quit");
    // @end
    // @end
    while(1) {
        editorRefreshScreen();      // @from 02.01
        editorProcessKeypress(STDIN_FILENO);
    }
    return 0;
}
