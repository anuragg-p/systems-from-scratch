/*
 * diff.h - two texts compared line by line: the shortest edit script that
 * turns the first into the second, and that script printed as the hunks
 * of a unified diff.
 *
 *   diff.c    a text as lines, numbered so that equal lines have equal
 *             numbers; the longest common subsequence, as a table
 *             the walk through the table to the script; hunks, and      @from 06.02
 *             the unified format                                        @from 06.02
 *   myers.c   a script as short, from Myers' search of the edit graph   @from 06.03
 *
 * tools/diff is one front end to it; git's diff is another. The whole of
 * it, for two texts in memory:
 *
 *     DiffText a, b;
 *     diff_text(&a, data, size);             the lines, pointing into data
 *     diff_text(&b, data2, size2);
 *     DiffScript s;
 *     diff_table(&s, &a, &b);                lines to delete and insert: s.ndel, s.nins
 *                                            and the script itself: s.edits         @from 06.02
 *     diff_myers(&s, &a, &b);                or this: as few, and quicker           @from 06.03
 *     diff_unified(stdout, &a, &b, &s, 3);   the script as hunks, 3 lines of context  @from 06.02
 *     diff_script_free(&s);                                                         @from 06.02
 *     diff_text_free(&a);
 *     diff_text_free(&b);
 *
 * The texts are the same when s.ndel + s.nins is 0.
 *
 * DS_STATS=1: diff_table prints "stats: lcs: ...", as diff.c says.
 * diff_myers prints "stats: myers: ...", as myers.c says.                   @from 06.03
 * DS_TRACE=1: each algorithm prints its steps on stderr, for texts of
 * TRACE_LINES lines or fewer.
 */
#ifndef DIFF_H
#define DIFF_H

#include "ds.h"

/* One line of a text: its bytes, with its newline if it has one. Only a
 * text's last line can lack it, and then it is not equal to the same
 * line with one. */
typedef struct {
    const char *s;
    size_t      len;
    long        id;      /* equal lines, in either text, have equal ids (diff_number) */
} DiffLine;

/* A text as lines: DiffLine, first to last, pointing into the bytes
 * given to diff_text(), which must outlive it. */
typedef struct {
    Array lines;
} DiffText;

// @from 06.02
/* One step of an edit script: keep a line of both texts (' '), delete a
 * line of the first ('-'), or insert a line of the second ('+'). a and b
 * are where it stands in each text, counted from 0: a line kept or
 * deleted is line a of the first, a line kept or inserted is line b of
 * the second. */
typedef struct {
    char   op;
    size_t a, b;
} DiffEdit;
// @end

/* An edit script: what turns the first text into the second, with the
 * fewest lines deleted and inserted. The lines it keeps are a longest
 * common subsequence of the two texts; every other line of the first is
 * deleted, and every other line of the second inserted. */
typedef struct {
    Array  edits;        /* DiffEdit: every line of both texts, in order */   // @from 06.02
    size_t common;       /* lines kept */
    size_t ndel, nins;   /* lines deleted and inserted: the script's length is their sum */
} DiffScript;

/* Split size bytes at data into lines; returns how many. */
size_t diff_text(DiffText *t, const char *data, size_t size);
void   diff_text_free(DiffText *t);

/* Give equal lines equal ids, across both texts. The algorithms call it
 * themselves. */
void diff_number(DiffText *a, DiffText *b);

/* The script that turns a into b, from a table of (lines of a + 1) x
 * (lines of b + 1) cells. */
void diff_table(DiffScript *s, DiffText *a, DiffText *b);

// @from 06.03
/* The same length of script, by Myers' O(ND) search: its work grows with
 * the size of the script, not with the size of the texts. */
void diff_myers(DiffScript *s, DiffText *a, DiffText *b);
// @end

/* The most memory the table may take: past it, diff_table stops with an
 * error rather than run the machine out of memory. 4 GB is the table of
 * two files of 32768 lines.
 * Myers' kept points are held to it too.                                @from 06.03
 * To try more: make clean; make EXTRA_CFLAGS=-DDIFF_MAX_BYTES=8589934592
 */
#ifndef DIFF_MAX_BYTES
#define DIFF_MAX_BYTES ((size_t)4 << 30)
#endif

// @from 06.02
/* Print the script's changes as the hunks of a unified diff, each with up
 * to context lines of the texts around it: "@@ -1,4 +1,5 @@" and its
 * lines. No header lines: those are the caller's. Returns how many hunks
 * it printed (none for a script with no changes). */
size_t diff_unified(FILE *out, const DiffText *a, const DiffText *b, const DiffScript *s, size_t context);

void diff_script_free(DiffScript *s);
// @end

/* DS_TRACE=1: the algorithms print each step on stderr, for texts of no
 * more than TRACE_LINES lines each. */
int diff_tracing(const DiffText *a, const DiffText *b);
#define TRACE_LINES 200

#endif
