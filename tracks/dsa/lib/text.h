/*
 * text.h - the text an editor holds, behind one interface.
 *
 * To the editor (tools/edit) the text is a row of bytes it can read, and
 * insert into and erase from at any position: nothing more. How the bytes
 * are kept is the business of the structure behind the interface, and the
 * lessons of module 03 put one after another there:
 *
 *   flat.c     the whole text in one array, the obvious way
 *   gap.c      one array with a gap in it where the editing is      @from 03.02
 *   pieces.c   a list of pieces of the file and of what was added   @from 03.04
 *   ptree.c    the same pieces, in a balanced tree                  @from 03.05
 *   undo.c     what was done, to undo and redo, on any of them      @from 03.03
 *
 * Positions count bytes from 0, and a text is len bytes long: a position
 * is anything from 0 (before the first byte) to len (after the last). A
 * newline is the byte '\n' like any other; lines are the editor's business.
 *
 * Every structure counts its work for DS_STATS=1, and with DS_TRACE=1 in
 * the environment it prints what each call did, one line a call, on
 * stderr: "trace: <structure>: <what it did>: <its cost> | <what it holds
 * now>". That is for small texts: the whole structure is in the line.
 */
#ifndef TEXT_H
#define TEXT_H

#include <stddef.h>
#include <stdio.h>

typedef struct Text Text;

/* What a structure does for the interface: a function for each thing the
 * editor asks of a text. */
typedef struct {
    const char *name;     /* "flat array", ...: for DS_STATS and the status bar */

    /* Put the n bytes at s at position pos: what was at pos and after it
     * comes after them. */
    void   (*insert)(Text *t, size_t pos, const char *s, size_t n);

    /* Take out the n bytes from pos on. */
    void   (*erase)(Text *t, size_t pos, size_t n);

    /* Copy the n bytes from pos on into buf. */
    void   (*read)(Text *t, size_t pos, char *buf, size_t n);

    /* Write the whole text to f, in order: 0, or -1 with errno set. */
    int    (*write)(Text *t, FILE *f);

    void   (*free)(Text *t);
} TextOps;

/* Every structure that holds a text starts with one of these: a pointer
 * to the structure is then a pointer to its Text too, and back. */
struct Text {
    const TextOps *ops;
    size_t len;           /* how many bytes the text is */
};

/* What the editor calls. Each checks its positions (one past the end of
 * the text is a bug in the caller, and fatal), and calls the structure's
 * own function. text_read reads as many of the n bytes as there are, and
 * says how many. */
void   text_insert(Text *t, size_t pos, const char *s, size_t n);
void   text_erase(Text *t, size_t pos, size_t n);
size_t text_read(Text *t, size_t pos, char *buf, size_t n);
int    text_write(Text *t, FILE *f);
void   text_free(Text *t);

/* The whole file at path, read into a new block with room for `room` more
 * bytes after it; *len says how long the file is. A file that does not
 * exist is an empty text (the first save makes it); any other trouble
 * opening or reading it is fatal. */
char  *text_load(const char *path, size_t *len, size_t room);

/* DS_TRACE: text_tracing() says whether it is set (to anything but 0);
 * text_trace() prints, printf style, on stderr; text_trace_bytes() prints
 * n bytes as a C string would be written, "a\tb\n", cut short with ...
 * after 40 of them. text_trace_off() stops it (the editor's screen is on
 * the same terminal). */
int    text_tracing(void);
void   text_trace_off(void);
void   text_trace(const char *fmt, ...);
void   text_trace_bytes(const char *s, size_t n);

#endif
