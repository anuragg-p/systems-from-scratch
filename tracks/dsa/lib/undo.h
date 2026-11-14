/*
 * undo.h - undo and redo, as two stacks of edits (undo.c).
 */
#ifndef UNDO_H
#define UNDO_H

#include "ds.h"
#include "text.h"

/* One change made to the text: what it was, where, and the bytes it put
 * in or took out. */
typedef struct {
    int    erase;        /* 1: bytes were erased at pos; 0: inserted at pos */
    size_t pos;
    Array  bytes;        /* char: those bytes */
    int    backwards;    /* bytes is in reverse order (see undo.c) */
} Edit;

/* The two stacks: the edits made, the last on top, and the edits undone,
 * the last undone on top. */
typedef struct {
    Array done;          /* Edit */
    Array undone;        /* Edit */
    int   typing;        /* the edit on top of done is still being typed */
} Undo;

/* What undo_undo() or undo_redo() just did to the text, for the editor to
 * follow: bytes went in at pos (erased 0) or out from it (erased 1), and
 * where the cursor goes now. bytes is good until the next undo call. */
typedef struct {
    int         erased;
    size_t      pos;
    const char *bytes;
    size_t      n;
    size_t      cursor;
} Change;

void undo_init(Undo *u);

/* Note a change just made to the text: the n bytes at s inserted at pos
 * (erase 0), or erased from pos (erase 1). typed: it came from typing, a
 * key that inserts a byte or Backspace, so it may join the edit before it
 * instead of being one of its own. */
void undo_note(Undo *u, int erase, size_t pos, const char *s, size_t n, int typed);

/* The next change starts an edit of its own (the cursor moved). */
void undo_break(Undo *u);

/* Undo the last edit made, or redo the last undone, on the text t:
 * 1, with what was done in *c; 0 if there was nothing to undo or redo. */
int  undo_undo(Undo *u, Text *t, Change *c);
int  undo_redo(Undo *u, Text *t, Change *c);

void undo_free(Undo *u);

#endif
