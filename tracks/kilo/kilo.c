/* kilo: a text editor in one C file, with no library between it and the
 * terminal. It puts the terminal in raw mode, reads keys a byte at a time,
 * keeps the file as an array of rows, and redraws the whole screen after
 * every key with VT100 escape codes, in a single write.
 *
 * This file is derived from kilo.c by Salvatore Sanfilippo,
 * https://github.com/antirez/kilo (commit 323d93b). It keeps his functions
// @from 06.01
 * and their structure, his syntax highlighting with them. The comments are
 * rewritten as notes for the reader, and the few places where the code
 * itself differs from his say so in a comment. His notice follows.
// @else
//  * and their structure. The syntax highlighting is left out, the comments
//  * are rewritten as notes for the reader, and the few places where the code
//  * itself differs from his say so in a comment. His notice follows.
// @end
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
#include "lsp.h"        // @from 07.01
#include "api.h"        // @from 09.02
#include "script.h"     // @from 09.01

// @from 06.01
/* What each character of a row is, for its colour: its highlight class.
 * A row keeps one per character of render, in hl. */
#define HL_NORMAL 0
#define HL_NONPRINT 1
// @end
#define HL_COMMENT 2    // a // comment, to the end of the row @from 06.03
#define HL_MLCOMMENT 3  // a /* */ comment, over as many rows as it takes @from 06.03
#define HL_KEYWORD1 4   // a keyword: if, return, ... @from 06.04
#define HL_KEYWORD2 5   // a type: int, char, ... @from 06.04
#define HL_STRING 6     // @from 06.02
#define HL_NUMBER 7     // @from 06.02
#define HL_MATCH 8      // the search's match @from 06.05
// @from 06.01

// @end
// @from 06.02
/* What a syntax asks to be highlighted (editorSyntax.flags). Nothing reads
 * these: strings and numbers are highlighted in every syntax. */
#define HL_HIGHLIGHT_STRINGS (1<<0)
#define HL_HIGHLIGHT_NUMBERS (1<<1)

// @end
// @from 06.01
/* A language kilo can highlight: the files written in it, and the words and
 * comment marks it has. */
struct editorSyntax {
    char **filematch;   // file name endings (".c"), or parts of a name
    char **keywords;    // its keywords; one ending in '|' is a type @from 06.04
    // @from 06.03
    /* The original kilo has singleline_comment_start[2]: room for the two
     * characters of "//" in HLDB but not for the '\0' after them, which
     * new compilers warn about. */
    char singleline_comment_start[3];
    char multiline_comment_start[3];
    char multiline_comment_end[3];
    // @end
    int flags;          // HL_HIGHLIGHT_STRINGS, HL_HIGHLIGHT_NUMBERS @from 06.02
};

// @end
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
    int idx;            // where the row is in E.row: its neighbours are idx-1, idx+1 @from 06.03
    int size;           // bytes in chars
    int rsize;          // bytes in render @from 03.03
    char *chars;        // the line as the file has it
    char *render;       // the line as the screen shows it @from 03.03
    unsigned char *hl;  // a highlight class (HL_*) for each byte of render @from 06.01
    int hl_oc;          // does the row end inside a /* */ comment? @from 06.03
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
    long long changedtick;  // changes to the text so far: it only goes up @from 09.05
    char *filename;     // the file being edited @from 03.01
    char statusmsg[80];         // the message under the status bar @from 03.04
    time_t statusmsg_time;      // when it was set: it shows for 5 seconds @from 03.04
    struct editorSyntax *syntax;    // the file's language, or NULL: no colours @from 06.01
};

static struct editorConfig E;

/* What a key sends. A Ctrl key sends its letter's code with the top three
 * bits cleared: Ctrl-Q is 'q' & 0x1f, 17. Enter sends 13, a carriage
 * return, and Backspace sends 127, DEL. */
enum KEY_ACTION{
        KEY_NULL = 0,       /* NULL */
        CTRL_B = 2,         /* Ctrl-b */ // @from 07.07
        CTRL_C = 3,         /* Ctrl-c */
        CTRL_D = 4,         /* Ctrl-d */
        CTRL_E = 5,         /* Ctrl-e */ // @from 09.01
        CTRL_F = 6,         /* Ctrl-f */
        CTRL_G = 7,         /* Ctrl-g */ // @from 07.07
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
// @from 09.01
/* In "The API", near the end of the file: what the editor's own code calls
 * of it, here so that it can. */
char *editorPrompt(const char *prompt);
// @from 09.04
int editorFed = -1;     /* a key a script feeds the editor (feed_key), or -1 */
int editorScriptKey(int c);
// @end
void editorEvent(const char *event);                // @from 09.05
// @from 09.06
struct abuf;
void editorDrawHighlights(struct abuf *ab, int filerow);
int editorStatusLine(char *status, int size, int len);
// @end
// @end

// @from 06.01
/* =========================== Syntax highlights DB ========================= */

/* The languages kilo knows, one struct editorSyntax each in HLDB. A file is
 * highlighted in the first whose filematch fits its name: a pattern that
 * starts with a dot must end the name (".c"), any other may be anywhere in
 * it. To add a language, write its lists and add a stanza to HLDB. */

/* C / C++ */
char *C_HL_extensions[] = {".c",".h",".cpp",".hpp",".cc",NULL};
// @end
// @from 06.04
/* The words highlighted as keywords, and, ending in '|', as types. */
char *C_HL_keywords[] = {
	/* C Keywords */
	"auto","break","case","continue","default","do","else","enum",
	"extern","for","goto","if","register","return","sizeof","static",
	"struct","switch","typedef","union","volatile","while","NULL",

	/* C++ Keywords */
	"alignas","alignof","and","and_eq","asm","bitand","bitor","class",
	/* The original kilo has "deltype" here, a typo for decltype. */
	"compl","constexpr","const_cast","decltype","delete","dynamic_cast",
	"explicit","export","false","friend","inline","mutable","namespace",
	"new","noexcept","not","not_eq","nullptr","operator","or","or_eq",
	"private","protected","public","reinterpret_cast","static_assert",
	"static_cast","template","this","thread_local","throw","true","try",
	"typeid","typename","virtual","xor","xor_eq",

	/* C types */
        "int|","long|","double|","float|","char|","unsigned|","signed|",
        "void|","short|","auto|","const|","bool|",NULL
};
// @end
// @from 06.01

/* The database itself: each stanza in the order of struct editorSyntax. */
struct editorSyntax HLDB[] = {
    {
        /* C / C++ */
        C_HL_extensions,
        C_HL_keywords,                  // @from 06.04
        "//","/*","*/",                 // @from 06.03
        HL_HIGHLIGHT_STRINGS | HL_HIGHLIGHT_NUMBERS     // @from 06.02
    }
};

#define HLDB_ENTRIES (sizeof(HLDB)/sizeof(HLDB[0]))

// @end
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
    lspWaitKey(fd);     /* the keyboard and the language server at once */ // @from 07.04
    // @from 07.02
    // @from 07.04
    while ((nread = read(fd,&c,1)) == 0);
    // @else
    // while ((nread = read(fd,&c,1)) == 0)
    //     lspPump();      /* the language server, every 0.1 s */
    // @end
    // @else
    // while ((nread = read(fd,&c,1)) == 0);
    // @end
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

// @from 06.01
/* ====================== Syntax highlight color scheme  ==================== */

// @end
/* Does a word end at c? White space, the '\0' at the end of the row, and
 * the characters , . ( ) + - / * = ~ % [ ] ; are separators. A number or a
 * keyword starts only after one. */
int is_separator(int c) {
    // @build 06.02 where a word ends
    // True for '\0', for white space (isspace()), and for any of the
    // characters , . ( ) + - / * = ~ % [ ] ;
    return c == '\0' || isspace(c) || strchr(",.()+-/*=~%[];",c) != NULL;
    // @end
}

/* Does the row end inside a multi-line comment, so that the row after it
 * starts inside one? */
int editorRowHasOpenComment(erow *row) {
    // @build 06.03 does the row end inside a comment
    // Return the row's hl_oc: editorUpdateSyntax() keeps there whether the
    // row ended inside a comment.
    /* The original kilo works it out from the row's last character:
     *     if (row->hl && row->rsize && row->hl[row->rsize-1] == HL_MLCOMMENT &&
     *         (row->rsize < 2 || (row->render[row->rsize-2] != '*' ||
     *                             row->render[row->rsize-1] != '/'))) return 1;
     *     return 0;
     * An empty row, or one of spaces, has no character in the comment's
     * colour, so a blank line inside a comment ended it; and a row that
     * ends in an opening mark with a slash after it (slash, star, slash)
     * looked closed. */
    return row->hl_oc;
    // @end
}

// @from 06.01
// @from 06.03
/* Set row->hl: the highlight class of every character of render, read left
 * to right in the language of E.syntax. A change to whether the row ends
 * inside a comment changes the row below too, so that one is done next, and
 * so on down while it keeps changing. */
// @else
// /* Set row->hl: the highlight class of every character of render, read left
//  * to right in the language of E.syntax. */
// @end
// @end
void editorUpdateSyntax(erow *row) {
nextrow:                            // @from 06.03
    // @build 06.01 a class for every character
    // Make hl as long as render and fill it with HL_NORMAL. With no syntax
    // (a file kilo has no language for), that is all.
    row->hl = realloc(row->hl,row->rsize);
    memset(row->hl,HL_NORMAL,row->rsize);

    if (E.syntax == NULL) return; /* No syntax, everything is HL_NORMAL. */
    // @end

    // @from 06.02
    // @from 06.03
    int i, prev_sep, in_string, in_comment;
    // @else
    // int i, prev_sep, in_string;
    // @end
    // @else
    // int i;
    // @end
    char *p;
    char **keywords = E.syntax->keywords;               // @from 06.04
    char *scs = E.syntax->singleline_comment_start;     // @from 06.03
    char *mcs = E.syntax->multiline_comment_start;      // @from 06.03
    char *mce = E.syntax->multiline_comment_end;        // @from 06.03

    /* p walks render, i is where it is. Spaces at the start are left
     * normal. */
    p = row->render;
    i = 0;
    while(*p && isspace(*p)) {
        p++;
        i++;
    }
    // @from 06.02
    prev_sep = 1;       /* a word may start at p */
    in_string = 0;      /* the quote that opened the string p is in, or 0 */
    // @end
    in_comment = 0;     /* is p inside a multi-line comment? */ // @from 06.03

    // @from 06.03
    /* A row below one that ends inside a comment starts inside it. */
    if (row->idx > 0 && editorRowHasOpenComment(&E.row[row->idx-1]))
        in_comment = 1;

    // @end
    while(*p) {
        // @build 06.03 comments
        // A // after a separator, outside a multi-line comment: the rest of
        // the row is HL_COMMENT, and the scan stops. Inside a multi-line
        // comment: HL_MLCOMMENT, up to and including its */. Outside one
        // and outside a string, a /* opens one.
        /* The original kilo has no !in_comment here: inside a multi-line
         * comment, a row starting with // was taken for a // comment, and
         * the multi-line one ended there. */
        if (prev_sep && !in_comment && *p == scs[0] && *(p+1) == scs[1]) {
            /* The original kilo marks row->size-i bytes, counting chars
             * where hl follows render: after a tab, too few, and when the
             * tabs make i larger than size, a negative count that memset()
             * takes for an enormous one: kilo crashes. */
            memset(row->hl+i,HL_COMMENT,row->rsize-i);
            /* The original kilo returns here, so the row's comment state
             * (at the end of this function) was never kept: // typed in
             * front of a comment's opening left the rows below it in the
             * comment's colour. */
            break;
        }

        if (in_comment) {
            row->hl[i] = HL_MLCOMMENT;
            if (*p == mce[0] && *(p+1) == mce[1]) {
                row->hl[i+1] = HL_MLCOMMENT;
                p += 2; i += 2;
                in_comment = 0;
                prev_sep = 1;
                continue;
            } else {
                prev_sep = 0;
                p++; i++;
                continue;
            }
        } else if (!in_string && *p == mcs[0] && *(p+1) == mcs[1]) {
            /* The original kilo has no !in_string: the two characters that
             * open a comment, inside a string, opened one, and everything
             * after them to the end of the file was comment. */
            row->hl[i] = HL_MLCOMMENT;
            row->hl[i+1] = HL_MLCOMMENT;
            p += 2; i += 2;
            in_comment = 1;
            prev_sep = 0;
            continue;
        }
        // @end

        // @build 06.02 strings
        // A " or ' opens a string, and the same quote closes it; all of it
        // is HL_STRING. A backslash in a string takes the character after
        // it along, so \" does not close it.
        if (in_string) {
            row->hl[i] = HL_STRING;
            /* The original kilo tests only *p == '\\': a backslash last in
             * the row wrote hl[rsize], one past the end of hl, and the scan
             * went on past the '\0' that ends render. */
            if (*p == '\\' && *(p+1)) {
                row->hl[i+1] = HL_STRING;
                p += 2; i += 2;
                prev_sep = 0;
                continue;
            }
            if (*p == in_string) in_string = 0;
            p++; i++;
            continue;
        } else {
            if (*p == '"' || *p == '\'') {
                in_string = *p;
                row->hl[i] = HL_STRING;
                p++; i++;
                prev_sep = 0;
                continue;
            }
        }
        // @end

        // @build 06.01 non-printable characters
        // A character isprint() says no to is HL_NONPRINT.
        if (!isprint(*p)) {
            row->hl[i] = HL_NONPRINT;
            p++; i++;
            prev_sep = 0;   // @from 06.02
            continue;
        }
        // @end

        // @build 06.02 numbers
        // A digit after a separator starts a number; a digit or a '.'
        // right after a number goes on with it. All HL_NUMBER.
        if ((isdigit(*p) && (prev_sep || row->hl[i-1] == HL_NUMBER)) ||
            (*p == '.' && i >0 && row->hl[i-1] == HL_NUMBER)) {
            row->hl[i] = HL_NUMBER;
            p++; i++;
            prev_sep = 0;
            continue;
        }
        // @end

        // @build 06.04 keywords
        // After a separator, try each keyword: one that is here, with a
        // separator after it, is HL_KEYWORD1, or HL_KEYWORD2 if it ends in
        // '|' (the '|' is not part of the word).
        if (prev_sep) {
            int j;
            for (j = 0; keywords[j]; j++) {
                int klen = strlen(keywords[j]);
                int kw2 = keywords[j][klen-1] == '|';
                if (kw2) klen--;

                /* The original kilo has memcmp(p,keywords[j],klen), which
                 * may read all klen bytes, past the end of render;
                 * strncmp() stops at its '\0'. */
                if (!strncmp(p,keywords[j],klen) &&
                    is_separator(*(p+klen)))
                {
                    memset(row->hl+i,kw2 ? HL_KEYWORD2 : HL_KEYWORD1,klen);
                    p += klen;
                    i += klen;
                    break;
                }
            }
            if (keywords[j] != NULL) {
                prev_sep = 0;
                continue;
            }
        }
        // @end

        /* Anything else stays normal. */
        prev_sep = is_separator(*p);    /* may a word start after it? */ // @from 06.02
        p++; i++;
    }

    // @build 06.03 the comment goes on to the next row
    // Keep in row->hl_oc whether the row ended inside a comment. If that
    // changed, the next row (if there is one) starts differently now:
    // highlight it the same way, from the top of this function.
    /* The original kilo has int oc = editorRowHasOpenComment(row); (see
     * there why this is the scan's own in_comment now), and then
     *     if (row->hl_oc != oc && row->idx+1 < E.numrows)
     *         editorUpdateSyntax(&E.row[row->idx+1]);
     *     row->hl_oc = oc;
     * a call one level deeper for every row the change reaches: a comment
     * opened at the top of a file of 100000 lines overflowed the stack. */
    int oc = in_comment;
    if (row->hl_oc != oc && row->idx+1 < E.numrows) {
        row->hl_oc = oc;
        row = &E.row[row->idx+1];
        goto nextrow;
    }
    row->hl_oc = oc;
    // @end
}

/* The colour of a highlight class, as the number in ESC [ n m that sets
 * the text colour. */
int editorSyntaxToColor(int hl) {
    // @build 06.01 the colour of a class
    // A switch on hl: each class's colour, and for any other, 37 (white).
    switch(hl) {
    case HL_COMMENT:                // @from 06.03
    case HL_MLCOMMENT: return 36;   // cyan @from 06.03
    case HL_KEYWORD1: return 33;    // yellow @from 06.04
    case HL_KEYWORD2: return 32;    // green @from 06.04
    case HL_STRING: return 35;      // magenta @from 06.02
    case HL_NUMBER: return 31;      // red @from 06.02
    case HL_MATCH: return 34;       // blue @from 06.05
    default: return 37;             /* white */
    }
    // @end
}

/* Choose the file's language by its name: E.syntax is the first in HLDB
 * that fits, or stays NULL. */
void editorSelectSyntaxHighlight(char *filename) {
    // @build 06.01 a syntax chosen by the file's name
    // For each syntax in HLDB, each of its filematch patterns: if the
    // pattern is in filename, and either does not start with '.' or ends
    // filename there, set E.syntax to that syntax and return.
    for (unsigned int j = 0; j < HLDB_ENTRIES; j++) {
        struct editorSyntax *s = HLDB+j;
        unsigned int i = 0;
        while(s->filematch[i]) {
            int patlen = strlen(s->filematch[i]);
            /* The original kilo looks only where the pattern is first,
             * if ((p = strstr(filename,s->filematch[i])) != NULL): in
             * "my.cool.c" or ".config/x.c" that is not the end, and the
             * file had no colours. */
            char *p = filename;
            while ((p = strstr(p,s->filematch[i])) != NULL) {
                if (s->filematch[i][0] != '.' || p[patlen] == '\0') {
                    E.syntax = s;
                    return;
                }
                p++;
            }
            i++;
        }
    }
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
    // @from 06.01

    /* A new render needs its colours worked out again. */
    editorUpdateSyntax(row);
    // @end
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
        for (int j = at+1; j <= E.numrows; j++) E.row[j].idx++; // @from 06.03
    }
    E.row[at].size = len;
    E.row[at].chars = malloc(len+1);
    memcpy(E.row[at].chars,s,len+1);
    E.row[at].hl = NULL;            // @from 06.01
    E.row[at].hl_oc = 0;            // @from 06.03
    E.row[at].render = NULL;        // @from 03.03
    E.row[at].rsize = 0;            // @from 03.03
    E.row[at].idx = at;             // @from 06.03
    // @from 06.03
    /* The original kilo counts the row after editorUpdateRow(). Until
     * then the rows below it end one early, and a comment the new row
     * opens or closes never reached the last row of the file. */
    E.numrows++;
    // @end
    editorUpdateRow(E.row+at);      // @from 03.03
    // @from 06.03
    // @else
    // E.numrows++;
    // @end
    E.dirty++;                      // @from 04.01
    E.changedtick++;                // @from 09.05
    // @end
}

/* Free what a row points to (not the row itself: it is part of E.row). */
void editorFreeRow(erow *row) {
    // @build 04.03 free a row
    // Free the row's render and chars.
    free(row->render);
    free(row->chars);
    free(row->hl);                  // @from 06.01
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
    // @from 06.03
    /* The original kilo has idx++ here: each row that moved up claimed a
     * place further down, so its "row above" was the wrong row, or past
     * the end of E.row. */
    for (int j = at; j < E.numrows-1; j++) E.row[j].idx--;
    // @end
    E.numrows--;
    E.dirty++;
    E.changedtick++;                // @from 09.05
    // @from 06.03
    /* Not in the original kilo: the row now at at has another row above
     * it, which may end inside a comment where the deleted one did not. */
    if (at < E.numrows) editorUpdateSyntax(E.row+at);
    // @end
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
    E.changedtick++;                // @from 09.05
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
    E.changedtick++;                // @from 09.05
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
    E.changedtick++;                // @from 09.05
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
        E.changedtick++;            // @from 09.05
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
        editorEvent("BufReadPost");     /* a new file: in the editor too */ // @from 09.05
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
    editorEvent("BufReadPost");     // @from 09.05
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
    editorEvent("BufWritePre");     // @from 09.05
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
    editorEvent("BufWritePost");    // @from 09.05
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
        int current_color = -1;     // the colour set now; -1: the default @from 06.01
        if (len > 0) {
            if (len > E.screencols) len = E.screencols;
            // @from 06.01
            /* A byte at a time, each in the colour of its class. A colour
             * is sent only where it changes: ESC [ n m to set it, ESC [ 39 m
             * for the default. A non-printable character is drawn as a
             * letter (Ctrl-A as A) or '?', in reverse video. */
            char *c = r->render+E.coloff;
            unsigned char *hl = r->hl+E.coloff;
            int j;
            for (j = 0; j < len; j++) {
                if (hl[j] == HL_NONPRINT) {
                    char sym;
                    abAppend(&ab,"\x1b[7m",4);
                    /* The original kilo tests c[j] <= 26. char is signed: a
                     * byte above 127 is negative, passes, and '@'+c[j] sent
                     * the terminal another control or high byte, not '?'. */
                    if ((unsigned char)c[j] <= 26)
                        sym = '@'+c[j];
                    else
                        sym = '?';
                    abAppend(&ab,&sym,1);
                    abAppend(&ab,"\x1b[0m",4);
                    /* Not in the original kilo: ESC [ 0 m has put the
                     * default colour back, and a run after this one in the
                     * colour before it was drawn without its colour. */
                    current_color = -1;
                } else if (hl[j] == HL_NORMAL) {
                    if (current_color != -1) {
                        abAppend(&ab,"\x1b[39m",5);
                        current_color = -1;
                    }
                    abAppend(&ab,c+j,1);
                } else {
                    int color = editorSyntaxToColor(hl[j]);
                    if (color != current_color) {
                        char buf[16];
                        int clen = snprintf(buf,sizeof(buf),"\x1b[%dm",color);
                        current_color = color;
                        abAppend(&ab,buf,clen);
                    }
                    abAppend(&ab,c+j,1);
                }
            }
            // @else
            // /* The original kilo writes a byte at a time here, to switch
            //  * colours for the syntax highlighting. */
            // @end
            // @from 03.03
            // @from 06.01
            // @else
            // abAppend(&ab,r->render+E.coloff,len);
            // @end
            // @else
            // abAppend(&ab,r->chars+E.coloff,len);
            // @end
        }
        // @from 06.01
        /* The original kilo sends ESC [ 39 m after every row, coloured or
         * not. Here it goes only after a colour, so that a row with none,
         * and every row of a file with no syntax, is the same bytes as in
         * the editor without highlighting (00.02 shows those bytes). */
        if (current_color != -1) abAppend(&ab,"\x1b[39m",5);
        // @end
        abAppend(&ab,"\x1b[0K",4);
        // @from 07.06
        lspDrawRow(&ab,filerow,r->chars,r->size,r->render,r->rsize,
                   E.coloff,E.screencols);
        // @end
        editorDrawHighlights(&ab,filerow);  // @from 09.06
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
    len = editorStatusLine(status,sizeof(status),len);  // @from 09.06
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

    // @from 06.05
    /* The match is shown by colouring it HL_MATCH in its row's hl. The
     * colours it replaced are kept here, with the row they came from, to
     * put back when the search moves on or ends. */
    int saved_hl_line = -1;  /* No saved HL */
    char *saved_hl = NULL;

    // @end
    // @build 06.05 put the colours back
    // @stub #define FIND_RESTORE_HL kiloTodo("06.05", "put the colours back")
    // A macro, so it can change saved_hl: if colours are saved, copy them
    // back into the hl of row saved_hl_line, free them, and note that none
    // are saved.
    /* The original kilo has these lines at the left margin, as a #define
     * usually is; here they are indented with the code around them. */
    #define FIND_RESTORE_HL do { \
        if (saved_hl) { \
            memcpy(E.row[saved_hl_line].hl,saved_hl, E.row[saved_hl_line].rsize); \
            free(saved_hl); \
            saved_hl = NULL; \
        } \
    } while (0)

    // @end
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
            FIND_RESTORE_HL;                // @from 06.05
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

            // @from 06.05
            /* The last match's row gets its own colours back. */
            FIND_RESTORE_HL;

            // @end
            if (match) {
                erow *row = &E.row[current];        // @from 06.05
                last_match = current;
                // @from 06.05
                /* Keep the row's colours, and colour the match. */
                if (row->hl) {
                    saved_hl_line = current;
                    saved_hl = malloc(row->rsize);
                    memcpy(saved_hl,row->hl,row->rsize);
                    /* Not in the original kilo, which colours from
                     * match_offset: there it is a place in render, here in
                     * chars (see above), and hl follows render. Count the
                     * columns the tabs before the match take, as
                     * editorUpdateRow() does. */
                    int j, rx = 0;
                    for (j = 0; j < match_offset; j++)
                        rx += row->chars[j] == TAB ? 8 - rx%8 : 1;
                    memset(row->hl+rx,HL_MATCH,qlen);
                }
                // @end
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
    // @from 09.04
    int c = editorFed != -1 ? editorFed : editorReadKey(fd);
    // @else
    // int c = editorReadKey(fd);
    // @end
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
    if (editorFed == -1 && editorScriptKey(c)) return;  /* a script took it */ // @from 09.04
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
    // @from 07.07
    case CTRL_G:        /* Ctrl-g: go to the definition */
        lspDefinition();
        break;
    case CTRL_B:        /* Ctrl-b: and back */
        lspBack();
        break;
    // @end
    // @from 09.01
    case CTRL_E: {      /* Ctrl-e: a line of Lua, run */
        char *line = editorPrompt("lua: ");
        if (line) scriptEval(line);
        free(line);
        break;
    }
    // @end
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
    E.syntax = NULL;                // @from 06.01
    updateWindowSize();
    // @from 02.01
    /* The original kilo installs the handler with
     *     signal(SIGWINCH, handleSigWinCh);
     * On Linux with glibc, in a C99 build that asks for POSIX, as this one
     * does, that is the old System V signal(): the read() a resize
     * interrupts fails, and kilo exits; and after one resize the handler is
     * gone. sigaction() asks for the same thing on every system: the
     * handler stays, and the read() it interrupts carries on (SA_RESTART). */
    struct sigaction sa;
    sa.sa_handler = handleSigWinCh;
    sigemptyset(&sa.sa_mask);
    sa.sa_flags = SA_RESTART;
    sigaction(SIGWINCH,&sa,NULL);
    // @end
    // @end
}

// @from 07.06
/* ================ The editor's side of the language client ================ */

// @from 07.07
/* lsp.c knows what the server says, but not E, which only this file can
 * see: these two are its way to the cursor, to find it and to move it. */
// @else
// /* lsp.c knows what the server says, but not E, which only this file can
//  * see: this is its way to the cursor. */
// @end

/* Where the cursor is in the file: its row, and its byte in that row's
 * chars. */
void editorCursor(int *row, int *col) {
    // @build 07.06 where the cursor is
    // The screen's row and column of the cursor, plus the view's offsets.
    *row = E.rowoff+E.cy;
    *col = E.coloff+E.cx;
    // @end
}

// @end
// @from 07.07
/* Move the cursor to row, col (a byte of that row's chars), clamped to the
 * file, and scroll so it shows. path NULL, or the open file's name: in the
 * open file; another path: that file is read in place of the open one,
 * unless the open one has unsaved changes. Returns 0, or -1 with a
 * message when the other file is not opened. */
int editorJump(const char *path, int row, int col) {
    // @build 07.07 read another file in place of this one
    // With unsaved changes, say to save first, and return -1. editorOpen()
    // exits when a file is there but cannot be read: try fopen() first,
    // and if it fails say why and return -1. Then free every row, empty
    // the file and the view, and editorOpen() the path (it sets
    // E.filename and E.dirty itself).
    if (path && strcmp(path,E.filename) != 0) {
        FILE *fp;
        int j;

        if (E.dirty) {
            editorSetStatusMessage("Unsaved changes: save first (Ctrl-S), then try again");
            return -1;
        }
        if ((fp = fopen(path,"r")) == NULL) {
            editorSetStatusMessage("Can't open %s: %s",path,strerror(errno));
            return -1;
        }
        fclose(fp);
        for (j = 0; j < E.numrows; j++) editorFreeRow(E.row+j);
        free(E.row);
        E.row = NULL;
        E.numrows = 0;
        E.cx = E.cy = E.rowoff = E.coloff = 0;
        editorOpen((char *)path);
    }
    // @end
    // @build 07.07 move the cursor there
    // Clamp row to the rows there are, and col to that row's bytes. A row
    // off the screen goes to the top of it, as a search puts its match;
    // then the cursor goes on it, the view scrolled right if col is past
    // the screen's width.
    int size;

    if (row >= E.numrows) row = E.numrows-1;
    if (row < 0) row = 0;
    size = row < E.numrows ? E.row[row].size : 0;
    if (col > size) col = size;
    if (col < 0) col = 0;
    if (row < E.rowoff || row >= E.rowoff+E.screenrows) E.rowoff = row;
    E.cy = row-E.rowoff;
    E.coloff = 0;
    E.cx = col;
    if (E.cx >= E.screencols) {
        E.coloff = E.cx-E.screencols+1;
        E.cx = E.screencols-1;
    }
    return 0;
    // @end
}

// @end
// @from 09.01
/* ================================= The API ================================ */

// @from 09.02
/* What a script can do to the editor: the functions in the table API, at
 * the end of this section, which script.c hands to Lua as kilo.api. They
 * work on E, which only this file sees, and take and return only the API's
 * own types (api.h). No Lua header is included in this file: the API does
 * not know that it is Lua that calls it. */
// @else
// /* What a script can do to the editor. So far: say something in the message
//  * line. And Ctrl-E asks for a line of Lua to run. No Lua header is included
//  * in this file: script.c is Lua's side. */
// @end

static int editorScreen = 1;        /* 0 under kilo -l: no screen and no keys */ // @from 09.09
// @from 09.05
static const char *editorRunning;   /* the event whose functions run now, or NULL */
static int editorFire(const char *event, const char *arg, int stop);
// @end
static int editorQuit;             /* quit() was called: leave once back from the script */ // @from 09.07

/* Copy len bytes at s into buf (size bytes, with its '\0'), cut to fit, so
 * that the copy can go to the terminal: a tab becomes a space, any other
 * control byte a '?'. A script's text may hold anything, and a byte such as
 * ESC would reach the terminal as a command. */
static void editorClean(char *buf, size_t size, const char *s, size_t len) {
    size_t j;

    if (len > size-1) len = size-1;
    for (j = 0; j < len; j++) {
        unsigned char c = s[j];
        buf[j] = c == '\t' ? ' ' : (c < 32 || c == 127) ? '?' : (char)c;
    }
    buf[len] = '\0';
}

/* Say len bytes at s from a script, an error or not (in the message line
 * the two look the same): in the message line, cleaned and cut to it. */
void editorMessage(const char *s, size_t len, int error) {
    // @build 09.09 with no screen
    // Under kilo -l: the bytes as they are and a newline, on standard error
    // for an error, else on standard output; and that is all.
    if (!editorScreen) {
        FILE *out = error ? stderr : stdout;
        fwrite(s,1,len,out);
        fputc('\n',out);
        return;
    }
    // @end
    // @build 09.01 say it in the message line
    // Clean a copy as big as E.statusmsg (editorClean()) and make it the
    // message.
    char msg[sizeof(E.statusmsg)];

    (void)error;
    editorClean(msg,sizeof(msg),s,len);
    editorSetStatusMessage("%s",msg);
    // @end
}

/* Ask for a line in the message line: prompt, then what is typed, at most
 * SCRIPT_PROMPT_MAX bytes. Enter gives the line, in a new allocation the
 * caller frees; Escape gives NULL. Backspace deletes, and a key that is not
 * a printable character is not taken. Like editorFind(), it has its own
 * loop of drawing the screen and reading a key. */
char *editorPrompt(const char *prompt) {
    // @build 09.01 the prompt
    // Loop: the message is prompt and the line so far; draw the screen; read
    // a key from standard input. Backspace, Delete or Ctrl-H: drop the last
    // byte. Escape: clear the message, return NULL. Enter: clear the
    // message, return a copy of the line. A printable character: add it, if
    // there is room.
    char line[SCRIPT_PROMPT_MAX+1] = {0};
    int len = 0;

    while(1) {
        editorSetStatusMessage("%s%s",prompt,line);
        editorRefreshScreen();
        int c = editorReadKey(STDIN_FILENO);
        if (c == DEL_KEY || c == CTRL_H || c == BACKSPACE) {
            if (len != 0) line[--len] = '\0';
        } else if (c == ESC) {
            editorSetStatusMessage("");
            return NULL;
        } else if (c == ENTER) {
            char *copy = malloc(len+1);
            editorSetStatusMessage("");
            if (copy) memcpy(copy,line,len+1);
            return copy;
        } else if (isprint(c) && len < SCRIPT_PROMPT_MAX) {
            line[len++] = c;
            line[len] = '\0';
        }
    }
    // @end
}

// @from 09.02
/* The name of a type, in --api-info and in errors. */
const char *apiTypeName(ApiType type) {
    switch(type) {
    case API_NIL: return "nil";
    case API_BOOLEAN: return "boolean";
    case API_INTEGER: return "integer";
    case API_STRING: return "string";
    case API_LINES: return "lines";
    case API_POSITION: return "position";
    case API_FUNCTION: return "function";       // @from 09.04
    }
    return "?";
}

/* A value of type t, its members zero. */
static ApiValue apiValue(ApiType t) {
    ApiValue v;
    memset(&v,0,sizeof(v));
    v.type = t;
    return v;
}

static ApiValue apiInteger(long long n) {
    ApiValue v = apiValue(API_INTEGER);
    v.u.integer = n;
    return v;
}

static ApiValue apiPosition(long long row, long long col) {
    ApiValue v = apiValue(API_POSITION);
    v.u.position.row = row;
    v.u.position.col = col;
    return v;
}

/* How a function fails: fill err, printf style, and return nil. */
static ApiValue apiFail(ApiError *err, const char *fmt, ...) {
    va_list ap;

    va_start(ap,fmt);
    vsnprintf(err->msg,sizeof(err->msg),fmt,ap);
    va_end(ap);
    err->set = 1;
    return apiValue(API_NIL);
}

/* A string to return: a copy of len bytes at s. No memory: fail. */
static ApiValue apiString(const char *s, size_t len, ApiError *err) {
    ApiValue v = apiValue(API_STRING);

    if ((v.u.string.s = malloc(len+1)) == NULL) return apiFail(err,"not enough memory");
    memcpy(v.u.string.s,s,len);
    v.u.string.s[len] = '\0';
    v.u.string.len = len;
    return v;
}

/* Free what a function returned, and make it nil. */
void apiFree(ApiValue *v) {
    int j;

    if (v->type == API_STRING) free(v->u.string.s);
    if (v->type == API_LINES) {
        for (j = 0; j < v->u.lines.count; j++) free(v->u.lines.line[j].s);
        free(v->u.lines.line);
    }
    v->type = API_NIL;
}

/* Is [start, end) a range of rows of the file? If not, fail. Out of range
 * is an error, never cut to fit. */
static int apiRange(long long start, long long end, ApiError *err) {
    if (start >= 0 && start <= end && end <= E.numrows) return 1;
    apiFail(err,"[%lld, %lld) is not a range of the file's %d rows",start,end,E.numrows);
    return 0;
}

/* line_count() -> integer */
static ApiValue apiLineCount(ApiValue *args, int nargs, ApiError *err) {
    (void)args; (void)nargs; (void)err;
    return apiInteger(E.numrows);
}

/* get_lines(start, end) -> lines: a copy of the rows [start, end). */
static ApiValue apiGetLines(ApiValue *args, int nargs, ApiError *err) {
    // @build 09.02 get_lines
    // Check the range (apiRange()). Allocate an ApiString for each row, and
    // a copy of each row's chars with its '\0'; with no memory, free what
    // was made and fail.
    long long start = args[0].u.integer, end = args[1].u.integer, j;
    ApiValue v = apiValue(API_LINES);

    (void)nargs;
    if (!apiRange(start,end,err)) return v;
    if ((v.u.lines.line = malloc(sizeof(ApiString)*(end-start+1))) == NULL)
        return apiFail(err,"not enough memory");
    for (j = start; j < end; j++) {
        erow *row = &E.row[j];
        ApiString *line = &v.u.lines.line[v.u.lines.count];
        if ((line->s = malloc(row->size+1)) == NULL) {
            apiFree(&v);
            return apiFail(err,"not enough memory");
        }
        memcpy(line->s,row->chars,row->size+1);
        line->len = row->size;
        v.u.lines.count++;
    }
    return v;
    // @end
}

/* get_cursor() -> position: the cursor's row, and its byte in that row. */
static ApiValue apiGetCursor(ApiValue *args, int nargs, ApiError *err) {
    // @build 09.02 get_cursor
    // The screen's row and column of the cursor, plus the view's offsets.
    (void)args; (void)nargs; (void)err;
    return apiPosition(E.rowoff+E.cy,E.coloff+E.cx);
    // @end
}

/* get_name() -> string: the file's name ("" if there is none). */
static ApiValue apiGetName(ApiValue *args, int nargs, ApiError *err) {
    const char *name = E.filename ? E.filename : "";
    (void)args; (void)nargs;
    return apiString(name,strlen(name),err);
}

/* is_modified() -> boolean */
static ApiValue apiIsModified(ApiValue *args, int nargs, ApiError *err) {
    ApiValue v = apiValue(API_BOOLEAN);
    (void)args; (void)nargs; (void)err;
    v.u.boolean = E.dirty != 0;
    return v;
}

/* message(text): in the message line. */
static ApiValue apiMessage(ApiValue *args, int nargs, ApiError *err) {
    // @build 09.02 message
    // editorMessage() of the text: the way print() goes too.
    (void)nargs; (void)err;
    editorMessage(args[0].u.string.s,args[0].u.string.len,0);
    return apiValue(API_NIL);
    // @end
}

// @end
// @from 09.03
/* Put the cursor on row, col of the file, and scroll the view as little as
 * shows it. */
static void editorShowCursor(int row, int col) {
    if (row < E.rowoff) E.rowoff = row;
    if (E.screenrows > 0 && row >= E.rowoff+E.screenrows) E.rowoff = row-E.screenrows+1;
    if (col < E.coloff) E.coloff = col;
    if (E.screencols > 0 && col >= E.coloff+E.screencols) E.coloff = col-E.screencols+1;
    E.cy = row-E.rowoff;
    E.cx = col-E.coloff;
}

/* set_lines(start, end, lines): replace the rows [start, end) by the lines,
 * as many as there are. No lines: the rows are deleted. start == end: the
 * lines go in before row start. It is the one way a script changes the
 * text, and it changes it all or not at all. */
static ApiValue apiSetLines(ApiValue *args, int nargs, ApiError *err) {
    // @build 09.03 set_lines: check everything first
    // Check the range (apiRange()), and that no line holds a '\n': "a line
    // cannot hold a newline (line N)", N counted from 1 as Lua counts the
    // list. Fail before anything has changed.
    long long start = args[0].u.integer, end = args[1].u.integer;
    ApiString *line = args[2].u.lines.line;
    int n = args[2].u.lines.count, j, row, col, size;

    (void)nargs;
    if (!apiRange(start,end,err)) return apiValue(API_NIL);
    for (j = 0; j < n; j++)
        if (memchr(line[j].s,'\n',line[j].len))
            return apiFail(err,"a line cannot hold a newline (line %d)",j+1);
    // @end
    // @build 09.03 set_lines: the change
    // Note where the cursor is. Delete rows end-1 down to start with
    // editorDelRow(), then insert line j at start+j with editorInsertRow():
    // the core's own functions for rows, so whatever watches those sees
    // this change as it sees a key's.
    row = E.rowoff+E.cy;
    col = E.coloff+E.cx;
    for (j = end-1; j >= start; j--) editorDelRow(j);
    for (j = 0; j < n; j++) editorInsertRow(start+j,line[j].s,line[j].len);
    // @end
    // @build 09.03 set_lines: the cursor afterwards
    // On a row below the range: the same line, so its row moves by the
    // change in the count. Inside the range: the same row, or the range's
    // new last row if that is higher; with no new rows, the row that took
    // the range's place, or the file's last row. Its column cut to the row.
    // Then show it (editorShowCursor()).
    if (row >= end) {
        row += n-(end-start);
    } else if (row >= start) {
        if (n > 0 && row > start+n-1) row = start+n-1;
        if (n == 0) row = start < E.numrows || E.numrows == 0 ? start : E.numrows-1;
        size = row < E.numrows ? E.row[row].size : 0;
        if (col > size) col = size;
    }
    editorShowCursor(row,col);
    return apiValue(API_NIL);
    // @end
}

/* set_cursor(pos): move the cursor to {row, col}. The row past the last,
 * where kilo puts the cursor below the text, is a place too (column 0). */
static ApiValue apiSetCursor(ApiValue *args, int nargs, ApiError *err) {
    // @build 09.03 set_cursor
    // A row from 0 to E.numrows, and a column from 0 to the row's size (0
    // past the last row); otherwise fail. Show it (editorShowCursor()).
    long long row = args[0].u.position.row, col = args[0].u.position.col;
    int size;

    (void)nargs;
    if (row < 0 || row > E.numrows)
        return apiFail(err,"row %lld is outside the file (it has %d rows)",row,E.numrows);
    size = row < E.numrows ? E.row[row].size : 0;
    if (col < 0 || col > size)
        return apiFail(err,"column %lld is outside row %lld (it has %d bytes)",col,row,size);
    editorShowCursor(row,col);
    return apiValue(API_NIL);
    // @end
}

/* save() -> boolean: save the file as Ctrl-S does; false when that failed
 * (the message line says why). */
static ApiValue apiSave(ApiValue *args, int nargs, ApiError *err) {
    // @build 09.03 save
    // editorSave(), and whether it gave 0.
    ApiValue v = apiValue(API_BOOLEAN);

    (void)args; (void)nargs; (void)err;
    // @from 09.05
    if (editorRunning && strncmp(editorRunning,"BufWrite",8) == 0)
        return apiFail(err,"a save is already going on");
    // @end
    if (E.filename == NULL) return apiFail(err,"no file name");    // @from 09.09
    v.u.boolean = editorSave() == 0;
    return v;
    // @end
}

/* script.c calls this each time a script has returned to the editor. The
 * cursor must be in the text: on a row, or on the one just past the last,
 * where kilo itself may put it, and inside its row; and the view must show
 * it. Nothing in the API puts it anywhere else: this is the check. */
void editorScriptReturned(void) {
    // @build 09.03 the cursor after a script
    // Cut the cursor's row to 0 .. E.numrows and its column to that row's
    // size (0 past the last row), and show it (editorShowCursor()).
    int row = E.rowoff+E.cy, col = E.coloff+E.cx, size;

    if (row > E.numrows) row = E.numrows;
    if (row < 0) row = 0;
    size = row < E.numrows ? E.row[row].size : 0;
    if (col > size) col = size;
    if (col < 0) col = 0;
    editorShowCursor(row,col);
    // @end
}

// @end
// @from 09.04
/* ================================== Keys ================================== */

/* Keys by name: every key editorReadKey() can return has one. These, and
 * besides them "<C-a>" to "<C-z>", any printable character as itself ("x",
 * "<"), and "<xNN>" (two hex digits) for any other byte. A name in angle
// @from 09.05
 * brackets may be in either case. The one table serves both ways: a name
 * to a key, and (for KeyPress) a key to its name. */
// @else
//  * brackets may be in either case. */
// @end
static const struct { const char *name; int key; } KEYNAMES[] = {
    {"<Enter>",ENTER}, {"<Esc>",ESC}, {"<Tab>",TAB}, {"<BS>",BACKSPACE},
    {"<Space>",' '}, {"<Del>",DEL_KEY}, {"<Up>",ARROW_UP},
    {"<Down>",ARROW_DOWN}, {"<Left>",ARROW_LEFT}, {"<Right>",ARROW_RIGHT},
    {"<Home>",HOME_KEY}, {"<End>",END_KEY}, {"<PageUp>",PAGE_UP},
    {"<PageDown>",PAGE_DOWN}, {NULL,0}
};

/* Is a the same as b, len bytes of each, in either case? */
static int editorSameName(const char *a, const char *b, size_t len) {
    size_t j;
    for (j = 0; j < len; j++)
        if (tolower((unsigned char)a[j]) != tolower((unsigned char)b[j])) return 0;
    return 1;
}

/* The key a name of len bytes names, or -1. */
static int editorKeyByName(const char *name, size_t len) {
    // @build 09.04 a name to a key
    // One printable character, not a space: itself. A name in KEYNAMES, in
    // either case: its key. "<C-x>" for a letter x: x & 0x1f. "<xNN>": the
    // byte NN. Anything else: -1.
    unsigned int byte;
    int j;

    if (len == 1 && isprint((unsigned char)name[0]) && name[0] != ' ')
        return (unsigned char)name[0];
    for (j = 0; KEYNAMES[j].name; j++)
        if (strlen(KEYNAMES[j].name) == len && editorSameName(KEYNAMES[j].name,name,len))
            return KEYNAMES[j].key;
    if (len == 5 && name[0] == '<' && name[4] == '>') {
        if (tolower((unsigned char)name[1]) == 'c' && name[2] == '-' && isalpha((unsigned char)name[3]))
            return toupper((unsigned char)name[3]) & 0x1f;
        if (tolower((unsigned char)name[1]) == 'x' && isxdigit((unsigned char)name[2]) &&
            isxdigit((unsigned char)name[3]) && sscanf(name+2,"%2x",&byte) == 1)
            return byte;
    }
    return -1;
    // @end
}

// @from 09.05
/* The other way, for KeyPress: the name of key c, as editorKeyByName()
 * takes it, in buf: from KEYNAMES, "<C-x>", the character itself, or
 * "<xNN>". */
static void editorKeyName(int c, char *buf, size_t size) {
    int j;

    for (j = 0; KEYNAMES[j].name; j++)
        if (KEYNAMES[j].key == c) {
            snprintf(buf,size,"%s",KEYNAMES[j].name);
            return;
        }
    if (c >= 1 && c <= 26) snprintf(buf,size,"<C-%c>",'a'+c-1);
    else if (c > ' ' && c < 127) snprintf(buf,size,"%c",c);
    else snprintf(buf,size,"<x%02x>",c & 0xff);
}

// @end

/* The functions mapped to keys: a reference for each key editorReadKey()
 * can return (the bytes, then ARROW_LEFT to PAGE_DOWN), 0 for none. */
static int editorKeymap[256+PAGE_DOWN-ARROW_LEFT+1];

static int *editorKeymapSlot(int key) {
    if (key >= 0 && key < 256) return &editorKeymap[key];
    if (key >= ARROW_LEFT && key <= PAGE_DOWN) return &editorKeymap[256+key-ARROW_LEFT];
    return NULL;
}

/* The key a name names, for set_keymap(), del_keymap() and feed_key(): -1
 * after failing with err for a name that is no key's, and for Ctrl-Q. */
static int apiKey(ApiValue *name, ApiError *err) {
    int key = editorKeyByName(name->u.string.s,name->u.string.len);

    if (key == -1) apiFail(err,"unknown key \"%.40s\"",name->u.string.s);
    else if (key == CTRL_Q) apiFail(err,"<C-q> is the way out: no script can have it");
    return err->set ? -1 : key;
}

/* set_keymap(key, fn): from now on the key runs fn, instead of what the
 * editor does with it. */
static ApiValue apiSetKeymap(ApiValue *args, int nargs, ApiError *err) {
    // @build 09.04 set_keymap
    // The key by its name (apiKey(): it refuses Ctrl-Q). Let go of the
    // function the key had (scriptUnref()) and keep the new reference.
    int key = apiKey(&args[0],err), *slot;

    (void)nargs;
    if (key == -1) return apiValue(API_NIL);
    slot = editorKeymapSlot(key);
    if (*slot) scriptUnref(*slot);
    *slot = args[1].u.function;
    return apiValue(API_NIL);
    // @end
}

/* del_keymap(key): give the key back to the editor. */
static ApiValue apiDelKeymap(ApiValue *args, int nargs, ApiError *err) {
    // @build 09.04 del_keymap
    // The key by its name; one with no function is an error ("NAME is not
    // mapped"). Let go of the reference.
    int key = apiKey(&args[0],err), *slot;

    (void)nargs;
    if (key == -1) return apiValue(API_NIL);
    slot = editorKeymapSlot(key);
    if (*slot == 0) return apiFail(err,"%.40s is not mapped",args[0].u.string.s);
    scriptUnref(*slot);
    *slot = 0;
    return apiValue(API_NIL);
    // @end
}

/* feed_key(key): do now what the editor itself does for the key: its own
 * action, with no mapping and no KeyPress consulted, so a function mapped
 * to Ctrl-S can still save as Ctrl-S does. */
static ApiValue apiFeedKey(ApiValue *args, int nargs, ApiError *err) {
    // @build 09.04 feed_key
    // The key by its name (Ctrl-Q refused: leaving is quit()'s). Put it in
    // editorFed and run editorProcessKeypress(): it takes the key from there
    // instead of reading one, and offers it to no script. Then put back what
    // editorFed held.
    int key = apiKey(&args[0],err), fed = editorFed;

    (void)nargs;
    if (key == -1) return apiValue(API_NIL);
    // @from 09.05
    if (key == CTRL_S && editorRunning && strncmp(editorRunning,"BufWrite",8) == 0)
        return apiFail(err,"a save is already going on");
    // @end
    // @from 09.09
    if (!editorScreen && (key == CTRL_E || key == CTRL_F))
        return apiFail(err,"%.40s waits for the keyboard, and there is none",args[0].u.string.s);
    // @end
    editorFed = key;
    editorProcessKeypress(STDIN_FILENO);
    editorFed = fed;
    return apiValue(API_NIL);
    // @end
}

/* editorProcessKeypress() offers this every key the user types, before
 * its own switch. Ctrl-Q is never offered to a script, whatever a script
 * has asked: this is the one place that guarantees the user can leave.
 * Returns 1 if a script took the key. */
int editorScriptKey(int c) {
    int *slot;

    if (c == CTRL_Q) return 0;
    if (c < 0) c &= 0xff;           /* a byte above 127, read as a negative char */
    // @build 09.05 KeyPress
    // Fire KeyPress with the key's name (editorKeyName()), stopping at the
    // first function that returns true: if one did, the key is taken.
    char name[16];

    editorKeyName(c,name,sizeof(name));
    if (editorFire("KeyPress",name,1)) return 1;
    // @end
    // @build 09.04 a mapped key
    // If the key has a function, call it (scriptCall()): the key is taken.
    slot = editorKeymapSlot(c);
    if (slot && *slot) {
        scriptCall(*slot,NULL);
        return 1;
    }
    return 0;
    // @end
}

// @end
// @from 09.05
/* ============================= Autocommands =============================== */

/* The events, and the functions scripts have bound to them, autocommands
 * as Vim and Neovim call them, kept in the order they were made. */
static const char *EVENTS[] = {"BufReadPost","BufWritePre","BufWritePost",
    "TextChanged","CursorMoved","KeyPress",NULL};

static struct autocmd {
    int id;             /* from 1, never given twice */
    const char *event;  /* one of EVENTS */
    int ref;            /* the function */
} editorAutocmds[AUTOCMD_MAX];
static int editorNumAutocmds, editorLastId;

/* create_autocmd(event, fn) -> integer: run fn on event; its id. */
static ApiValue apiCreateAutocmd(ApiValue *args, int nargs, ApiError *err) {
    // @build 09.05 create_autocmd
    // Find the event in EVENTS, its name exactly (none: "unknown event"). At
    // AUTOCMD_MAX, fail. Add it at the end, with the next id; return the id.
    const char *name = args[0].u.string.s;
    struct autocmd *a;
    int j;

    (void)nargs;
    for (j = 0; EVENTS[j]; j++)
        if (strlen(EVENTS[j]) == args[0].u.string.len && strcmp(EVENTS[j],name) == 0) break;
    if (EVENTS[j] == NULL) return apiFail(err,"unknown event \"%.40s\"",name);
    if (editorNumAutocmds == AUTOCMD_MAX)
        return apiFail(err,"too many autocommands (%d)",AUTOCMD_MAX);
    a = &editorAutocmds[editorNumAutocmds++];
    a->id = ++editorLastId;
    a->event = EVENTS[j];
    a->ref = args[1].u.function;
    return apiInteger(a->id);
    // @end
}

/* del_autocmd(id) */
static ApiValue apiDelAutocmd(ApiValue *args, int nargs, ApiError *err) {
    // @build 09.05 del_autocmd
    // Find the id (none: "no autocommand ID"); let go of its function and
    // close the gap, keeping the order.
    int j;

    (void)nargs;
    for (j = 0; j < editorNumAutocmds; j++)
        if (editorAutocmds[j].id == args[0].u.integer) break;
    if (j == editorNumAutocmds) return apiFail(err,"no autocommand %lld",args[0].u.integer);
    scriptUnref(editorAutocmds[j].ref);
    memmove(editorAutocmds+j,editorAutocmds+j+1,sizeof(editorAutocmds[0])*(editorNumAutocmds-j-1));
    editorNumAutocmds--;
    return apiValue(API_NIL);
    // @end
}

/* get_changedtick() -> integer */
static ApiValue apiGetChangedtick(ApiValue *args, int nargs, ApiError *err) {
    (void)args; (void)nargs; (void)err;
    return apiInteger(E.changedtick);
}

/* Call the functions bound to event, in the order they were made, each with
 * arg. With stop set (KeyPress), stop at the first that returns true, and
 * return 1. While they run, no event fires: what their work causes is not
 * heard (no nesting). The functions bound before the event began are the
 * ones that run; one deleted meanwhile does not; one that fails is said
 * and the next runs. */
static int editorFire(const char *event, const char *arg, int stop) {
    // @build 09.05 an event's functions
    // Nothing while editorRunning is set; set it for the time this runs.
    // Over and over: the first autocommand for event with an id above the
    // last one called and not above editorLastId as it was at the start;
    // none left: done. scriptCall() it with arg.
    int last = 0, top = editorLastId, taken = 0, j;

    if (editorRunning) return 0;
    editorRunning = event;
    while (!taken) {
        struct autocmd *a = NULL;
        for (j = 0; j < editorNumAutocmds && a == NULL; j++)
            if (editorAutocmds[j].id > last && editorAutocmds[j].id <= top &&
                strcmp(editorAutocmds[j].event,event) == 0) a = &editorAutocmds[j];
        if (a == NULL) break;
        last = a->id;
        if (scriptCall(a->ref,arg) == 1 && stop) taken = 1;
    }
    editorRunning = NULL;
    return taken;
    // @end
}

/* Fire event: its functions are called with its name. */
void editorEvent(const char *event) {
    editorFire(event,event,0);
}

/* At the top of main()'s loop, after a key's work and before the screen is
 * drawn: TextChanged if the text has changed since the last look (the
 * changed tick moved), CursorMoved if the cursor is somewhere else. Each
 * fires once, outside any other event. The first look only notes. */
void editorAfterKey(void) {
    // @build 09.07 leave, once back from the script
    // If quit() was called, exit(0).
    if (editorQuit) exit(0);
    // @end
    // @build 09.05 TextChanged and CursorMoved
    // Keep the tick and the cursor's place of the last look (statics; tick
    // -1 before the first). Fire TextChanged if the tick is not the same,
    // then CursorMoved if the place is not. Note both as they are now,
    // after the functions: what those changed is not heard again.
    static long long tick = -1;
    static int row, col;
    int moved = row != E.rowoff+E.cy || col != E.coloff+E.cx;

    if (tick != -1 && tick != E.changedtick) editorEvent("TextChanged");
    if (tick != -1 && moved) editorEvent("CursorMoved");
    tick = E.changedtick;
    row = E.rowoff+E.cy;
    col = E.coloff+E.cx;
    // @end
}

// @end
// @from 09.06
/* ================================ Drawing ================================= */

/* Namespaces, so that two scripts can each clear their own highlights; and
 * the highlights: a row, its bytes [start, end), and a style. They do not
 * move when the text does: a script puts them again when it changes. */
static char *editorNamespaces[NAMESPACE_MAX];   /* names; "" for one made without */
static int editorNumNamespaces;

static const struct { const char *name; const char *code; } STYLES[] = {
    {"red","31"}, {"green","32"}, {"yellow","33"}, {"blue","34"},
    {"magenta","35"}, {"cyan","36"}, {"bold","1"}, {"underline","4"},
    {"reverse","7"}, {NULL,NULL}
};

static struct highlight {
    int ns, row, style;
    long long start, end;
} editorHighlights[HIGHLIGHT_MAX];
static int editorNumHighlights;

static char editorStatus[80];       /* set_statusline()'s text, cleaned; "" for none */

/* create_namespace(name) -> integer: the namespace of that name, made if
 * it is new; "" makes a new one each time. Ids count from 1. */
static ApiValue apiCreateNamespace(ApiValue *args, int nargs, ApiError *err) {
    // @build 09.06 create_namespace
    // A name already there (not ""): its id, its place plus 1. Else, unless
    // there are NAMESPACE_MAX, keep a copy of the name and return the new id.
    const char *name = args[0].u.string.s;
    int j;

    (void)nargs;
    if (name[0])
        for (j = 0; j < editorNumNamespaces; j++)
            if (strcmp(editorNamespaces[j],name) == 0) return apiInteger(j+1);
    if (editorNumNamespaces == NAMESPACE_MAX)
        return apiFail(err,"too many namespaces (%d)",NAMESPACE_MAX);
    if ((editorNamespaces[editorNumNamespaces] = malloc(strlen(name)+1)) == NULL)
        return apiFail(err,"not enough memory");
    memcpy(editorNamespaces[editorNumNamespaces],name,strlen(name)+1);
    return apiInteger(++editorNumNamespaces);
    // @end
}

/* add_highlight(ns, row, start, end, style): draw bytes [start, end) of
 * the row in the style, over whatever the editor drew there. */
static ApiValue apiAddHighlight(ApiValue *args, int nargs, ApiError *err) {
    // @build 09.06 add_highlight
    // The namespace must be one, the row in the file, start not negative
    // and not past end, the style one of STYLES; and there must be room
    // (HIGHLIGHT_MAX). Keep it at the end: later ones are drawn over
    // earlier ones.
    long long ns = args[0].u.integer, row = args[1].u.integer;
    long long start = args[2].u.integer, end = args[3].u.integer;
    struct highlight *h;
    int j;

    (void)nargs;
    if (ns < 1 || ns > editorNumNamespaces) return apiFail(err,"no namespace %lld",ns);
    if (row < 0 || row >= E.numrows)
        return apiFail(err,"row %lld is outside the file (it has %d rows)",row,E.numrows);
    if (start < 0 || start > end) return apiFail(err,"[%lld, %lld) is not a range of bytes",start,end);
    for (j = 0; STYLES[j].name; j++)
        if (strcmp(STYLES[j].name,args[4].u.string.s) == 0) break;
    if (STYLES[j].name == NULL || strlen(STYLES[j].name) != args[4].u.string.len)
        return apiFail(err,"unknown style \"%.20s\": red, green, yellow, blue, magenta, cyan, "
                       "bold, underline or reverse",args[4].u.string.s);
    if (editorNumHighlights == HIGHLIGHT_MAX)
        return apiFail(err,"too many highlights (%d)",HIGHLIGHT_MAX);
    h = &editorHighlights[editorNumHighlights++];
    h->ns = ns;
    h->row = row;
    h->start = start;
    h->end = end;
    h->style = j;
    return apiValue(API_NIL);
    // @end
}

/* clear_namespace(ns): remove its highlights. */
static ApiValue apiClearNamespace(ApiValue *args, int nargs, ApiError *err) {
    // @build 09.06 clear_namespace
    // The namespace must be one. Keep the highlights of every other, in
    // their order.
    long long ns = args[0].u.integer;
    int j, k = 0;

    (void)nargs;
    if (ns < 1 || ns > editorNumNamespaces) return apiFail(err,"no namespace %lld",ns);
    for (j = 0; j < editorNumHighlights; j++)
        if (editorHighlights[j].ns != ns) editorHighlights[k++] = editorHighlights[j];
    editorNumHighlights = k;
    return apiValue(API_NIL);
    // @end
}

/* Called by editorRefreshScreen() after it has drawn file row filerow, as
 * module 07's underline is: draw the row's highlights over it, cut to the
 * row as it is now and to the columns on the screen. */
void editorDrawHighlights(struct abuf *ab, int filerow) {
    // @build 09.06 draw the highlights
    // For each highlight on the row: its bytes of chars, cut to the row, as
    // columns of render (a tab goes to the next multiple of 8, as
    // editorUpdateRow() has it); cut to the screen's columns. Then "\r" back
    // to the row's start, ESC [ n C to the first cell (n: the cells before
    // it from E.coloff, a UTF-8 character taking one), ESC [ code m, the
    // same bytes of render again (ESC [ C for a control byte, leaving its
    // cell as it was drawn), and ESC [ 0 m.
    erow *r = &E.row[filerow];
    int j, k;

    for (j = 0; j < editorNumHighlights; j++) {
        struct highlight *h = &editorHighlights[j];
        long long from = h->start, to = h->end;
        int a = 0, b = 0, cells = 0, n;
        char buf[32];

        if (h->row != filerow) continue;
        if (from > r->size) from = r->size;
        if (to > r->size) to = r->size;
        if (from >= to) continue;
        for (k = 0; k < to; k++) {          /* bytes of chars to columns of render */
            if (k == from) a = b;
            b += r->chars[k] == TAB ? 8-b%8 : 1;
        }
        if (a < E.coloff) a = E.coloff;
        if (b > E.coloff+E.screencols) b = E.coloff+E.screencols;
        if (a >= b) continue;
        for (k = E.coloff; k < a; k++)
            if (((unsigned char)r->render[k] & 0xc0) != 0x80) cells++;
        abAppend(ab,"\r",1);
        if (cells > 0) {
            n = snprintf(buf,sizeof(buf),"\x1b[%dC",cells);
            abAppend(ab,buf,n);
        }
        n = snprintf(buf,sizeof(buf),"\x1b[%sm",STYLES[h->style].code);
        abAppend(ab,buf,n);
        for (k = a; k < b; k++) {
            unsigned char c = r->render[k];
            if (c < 32 || c == 127) abAppend(ab,"\x1b[C",3);
            else abAppend(ab,(char *)&c,1);
        }
        abAppend(ab,"\x1b[0m",4);
    }
    // @end
}

/* set_statusline(text): the left part of the status bar, in place of the
 * file's name and lines; "" gives the editor's own back. */
static ApiValue apiSetStatusline(ApiValue *args, int nargs, ApiError *err) {
    (void)nargs; (void)err;
    editorClean(editorStatus,sizeof(editorStatus),args[0].u.string.s,args[0].u.string.len);
    return apiValue(API_NIL);
}

/* Called by editorRefreshScreen() with the left part of the status bar it
 * made (len bytes in status, size big): put set_statusline()'s text there
 * if there is one, cut so that the cursor's "row/rows" still fits on the
 * right. Returns the length of what is there now. */
int editorStatusLine(char *status, int size, int len) {
    // @build 09.06 the status bar
    // No text set: len, untouched. Else the room is the screen's width less
    // the "row/rows" the bar ends with and a space (and at most size-1):
    // copy that much of the text in, and return its length.
    int room = E.screencols-snprintf(NULL,0,"%d/%d",E.rowoff+E.cy+1,E.numrows)-1;

    if (editorStatus[0] == '\0') return len;
    if (room > size-1) room = size-1;
    if (room < 0) room = 0;
    snprintf(status,size,"%.*s",room,editorStatus);
    return strlen(status);
    // @end
}

/* get_view() -> position: the file's row and column at the screen's top
 * left. get_size() -> position: the rows and columns of text the screen
 * shows. */
static ApiValue apiGetView(ApiValue *args, int nargs, ApiError *err) {
    (void)args; (void)nargs; (void)err;
    return apiPosition(E.rowoff,E.coloff);
}

static ApiValue apiGetSize(ApiValue *args, int nargs, ApiError *err) {
    (void)args; (void)nargs; (void)err;
    return apiPosition(E.screenrows,E.screencols);
}

// @end
// @from 09.07
/* ========================= Asking, opening, leaving ======================= */

/* input(prompt) -> string: a line typed at the prompt; nil for Escape. */
static ApiValue apiInput(ApiValue *args, int nargs, ApiError *err) {
    // @build 09.07 input
    // Clean the prompt (editorClean()), ask with editorPrompt(): NULL is
    // nil, a line is a string (free editorPrompt()'s copy).
    char prompt[64], *line;
    ApiValue v;

    (void)nargs;
    if (!editorScreen) return apiFail(err,"no keyboard");      // @from 09.09
    editorClean(prompt,sizeof(prompt),args[0].u.string.s,args[0].u.string.len);
    if ((line = editorPrompt(prompt)) == NULL) return apiValue(API_NIL);
    v = apiString(line,strlen(line),err);
    free(line);
    return v;
    // @end
}

/* open(path): edit another file in place of this one. A path where there
 * is no file is a new, empty file of that name, as on the command line. */
static ApiValue apiOpen(ApiValue *args, int nargs, ApiError *err) {
    // @build 09.07 open
    // In a save's events: fail. Unsaved changes: fail. A name with a '\0'
    // in it, or none: fail. fopen() it first: editorOpen() exits on a file
    // that is there but cannot be read, so that is an error here. Then free
    // every row, empty the file and the view, and editorOpen() the path (it
    // sets E.filename, and fires BufReadPost).
    const char *path = args[0].u.string.s;
    FILE *fp;
    int j;

    (void)nargs;
    if (editorRunning && strncmp(editorRunning,"BufWrite",8) == 0)
        return apiFail(err,"a save is going on");
    if (E.dirty) return apiFail(err,"unsaved changes");
    if (path[0] == '\0' || strlen(path) != args[0].u.string.len)
        return apiFail(err,"\"%.40s\" is not a file name",path);
    if ((fp = fopen(path,"r")) != NULL) fclose(fp);
    else if (errno != ENOENT) return apiFail(err,"cannot read %.60s: %s",path,strerror(errno));
    for (j = 0; j < E.numrows; j++) editorFreeRow(E.row+j);
    free(E.row);
    E.row = NULL;
    E.numrows = 0;
    E.cx = E.cy = E.rowoff = E.coloff = 0;
    editorOpen((char *)path);
    return apiValue(API_NIL);
    // @end
}

/* quit(force): leave the editor, once the script has returned. Without
 * force, unsaved changes are an error. */
static ApiValue apiQuit(ApiValue *args, int nargs, ApiError *err) {
    // @build 09.07 quit
    // Without force and with unsaved changes: fail. Otherwise note it in
    // editorQuit: kilo must not exit, nor the state close, while Lua is
    // running.
    (void)nargs;
    if (!args[0].u.boolean && E.dirty)
        return apiFail(err,"unsaved changes (quit(true) leaves anyway)");
    editorQuit = 1;
    return apiValue(API_NIL);
    // @end
}

// @end
// @from 09.02
/* =============================== The table ================================ */

/* Every function a script can call: its name, its arguments' types and
 * names, what it returns, the C function, and what it does. script.c makes
 * kilo.api from this table, and kilo --api-info prints it. */
const ApiFunc API[] = {
    {"line_count", {API_NIL}, {NULL}, 0, API_INTEGER, apiLineCount,
     "the number of rows in the file"},
    {"get_lines", {API_INTEGER,API_INTEGER}, {"start","end"}, 2, API_LINES, apiGetLines,
     "the rows [start, end), counted from 0"},
    {"get_cursor", {API_NIL}, {NULL}, 0, API_POSITION, apiGetCursor,
     "the cursor's {row, col}, col a byte of the row"},
    {"get_name", {API_NIL}, {NULL}, 0, API_STRING, apiGetName,
     "the file's name"},
    {"is_modified", {API_NIL}, {NULL}, 0, API_BOOLEAN, apiIsModified,
     "true when the file has unsaved changes"},
    {"message", {API_STRING}, {"text"}, 1, API_NIL, apiMessage,
     "show text in the message line"},
    // @from 09.03
    {"set_lines", {API_INTEGER,API_INTEGER,API_LINES}, {"start","end","lines"}, 3, API_NIL,
     apiSetLines, "replace the rows [start, end) by lines"},
    {"set_cursor", {API_POSITION}, {"pos"}, 1, API_NIL, apiSetCursor,
     "move the cursor to {row, col}"},
    {"save", {API_NIL}, {NULL}, 0, API_BOOLEAN, apiSave,
     "save the file, as Ctrl-S does; false if that failed"},
    // @end
    // @from 09.04
    {"set_keymap", {API_STRING,API_FUNCTION}, {"key","fn"}, 2, API_NIL, apiSetKeymap,
     "run fn for key, in place of what the editor does"},
    {"del_keymap", {API_STRING}, {"key"}, 1, API_NIL, apiDelKeymap,
     "give key back to the editor"},
    {"feed_key", {API_STRING}, {"key"}, 1, API_NIL, apiFeedKey,
     "do what the editor itself does for key"},
    // @end
    // @from 09.05
    {"create_autocmd", {API_STRING,API_FUNCTION}, {"event","fn"}, 2, API_INTEGER,
     apiCreateAutocmd, "run fn on event; returns its id"},
    {"del_autocmd", {API_INTEGER}, {"id"}, 1, API_NIL, apiDelAutocmd,
     "stop running an autocommand"},
    {"get_changedtick", {API_NIL}, {NULL}, 0, API_INTEGER, apiGetChangedtick,
     "a count that goes up with every change to the text"},
    // @end
    // @from 09.06
    {"create_namespace", {API_STRING}, {"name"}, 1, API_INTEGER, apiCreateNamespace,
     "the id of a namespace for highlights; \"\" makes a new one"},
    {"add_highlight", {API_INTEGER,API_INTEGER,API_INTEGER,API_INTEGER,API_STRING},
     {"ns","row","start","end","style"}, 5, API_NIL, apiAddHighlight,
     "draw bytes [start, end) of row in style"},
    {"clear_namespace", {API_INTEGER}, {"ns"}, 1, API_NIL, apiClearNamespace,
     "remove the namespace's highlights"},
    {"set_statusline", {API_STRING}, {"text"}, 1, API_NIL, apiSetStatusline,
     "the status bar's left part; \"\" for the editor's own"},
    {"get_view", {API_NIL}, {NULL}, 0, API_POSITION, apiGetView,
     "the file's {row, col} at the screen's top left"},
    {"get_size", {API_NIL}, {NULL}, 0, API_POSITION, apiGetSize,
     "the {rows, cols} of text the screen shows"},
    // @end
    // @from 09.07
    {"input", {API_STRING}, {"prompt"}, 1, API_STRING, apiInput,
     "a line typed at the prompt; nil for Escape"},
    {"open", {API_STRING}, {"path"}, 1, API_NIL, apiOpen,
     "edit the file at path in place of this one"},
    {"quit", {API_BOOLEAN}, {"force"}, 1, API_NIL, apiQuit,
     "leave the editor; force: even with unsaved changes"},
    // @end
    {NULL, {API_NIL}, {NULL}, 0, API_NIL, NULL, NULL}
};

/* kilo --api-info: the table, a line per function, as a script calls it,
 * "get_lines(start: integer, end: integer) -> lines  -- what it does". It
 * needs no Lua: the API is the table. */
int apiInfo(void) {
    // @build 09.02 --api-info
    // For each entry: its name, "(", each argument as "NAME: TYPE" with ", "
    // between, ")", " -> TYPE" unless it returns nil, "  -- " and its help.
    const ApiFunc *f;
    int j;

    for (f = API; f->name; f++) {
        printf("%s(",f->name);
        for (j = 0; j < f->nargs; j++)
            printf("%s%s: %s",j ? ", " : "",f->argnames[j],apiTypeName(f->args[j]));
        printf(")");
        if (f->ret != API_NIL) printf(" -> %s",apiTypeName(f->ret));
        printf("  -- %s\n",f->help);
    }
    return 0;
    // @end
}

// @end
// @from 09.09
/* kilo -l script [file]: the editor with no screen and no keys. The file
 * is read if one is named, the script runs with the same kilo.api, and
 * kilo ends: 0, or 1 when the script failed (its error on standard error).
 * Nothing is saved unless the script calls save(). init.lua is not run. */
int editorRunScript(char *script, char *filename) {
    // @build 09.09 the editor with no screen
    // No raw mode, no window: note there is no screen (editorScreen 0), and
    // give E the size of a 24 x 80 terminal for the keys a script feeds.
    // Read the file, if one is named. Run the script (scriptRun()); return
    // 0, or 1 if it failed.
    editorScreen = 0;
    E.screenrows = 22;
    E.screencols = 80;
    if (filename) editorOpen(filename);
    return scriptRun(script) == 0 ? 0 : 1;
    // @end
}

// @end
// @end
int main(int argc, char **argv) {
    if (argc == 2 && strcmp(argv[1],"--api-info") == 0) return apiInfo();   // @from 09.02
    // @from 09.09
    if ((argc == 3 || argc == 4) && strcmp(argv[1],"-l") == 0)
        return editorRunScript(argv[2],argc == 4 ? argv[3] : NULL);
    // @end
    if (argc != 2) {
        fprintf(stderr,"Usage: kilo <filename>\n");
        fprintf(stderr,"       kilo --api-info\n");                     // @from 09.02
        fprintf(stderr,"       kilo -l <script.lua> [filename]\n");     // @from 09.09
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
    editorSelectSyntaxHighlight(argv[1]);  // @from 06.01
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
    lspStart(argv[1]);              // @from 07.01
    scriptStart();                  // @from 09.01
    editorEvent("BufReadPost");     /* now the scripts are there to hear it */ // @from 09.05
    while(1) {
        editorAfterKey();           // @from 09.05
        editorRefreshScreen();      // @from 02.01
        editorProcessKeypress(STDIN_FILENO);
    }
    return 0;
}
