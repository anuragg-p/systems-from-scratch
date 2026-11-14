/*
 * pieces.h - a piece table, its pieces in a list (pieces.c).
 * The piece tree (ptree.c) reads the same two buffers.   @from 03.05
 */
#ifndef PIECES_H
#define PIECES_H

#include "text.h"

/* The two buffers: the file as it was opened, which is never changed, and
 * every byte inserted since, one after another, which only grows. */
enum { ORIG, ADD };

/* A run of bytes of one of the buffers. */
typedef struct {
    int    buf;          /* ORIG or ADD */
    size_t start;        /* where it starts in that buffer */
    size_t len;
} Span;

typedef struct {
    const char *orig;    /* the file: mapped into memory (or read, when it cannot be) */
    size_t      origlen;
    int         mapped;
    char       *add;     /* what was inserted */
    size_t      addlen;
    size_t      addcap;
} Buffers;

/* Open the file at path as the original buffer, mapped: nothing of it is
 * read until something asks for its bytes. A file that does not exist is
 * an empty one. *mapped and *loaded count the bytes mapped, and those
 * read in when the file cannot be mapped (a pipe, say). */
void        buffers_open(Buffers *b, const char *path, long *mapped, long *loaded);

/* Put n bytes at the end of the add buffer: where they start in it. */
size_t      buffers_add(Buffers *b, const char *s, size_t n);

/* Where the bytes of a span are now (the add buffer moves as it grows). */
const char *span_bytes(const Buffers *b, Span s);

void        buffers_free(Buffers *b);

/* The text of the file at path, as one piece: all of the original buffer. */
Text *pieces_open(const char *path);

#endif
