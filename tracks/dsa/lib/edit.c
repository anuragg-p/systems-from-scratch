/*
 * edit.c - the edit distance between two words, by filling in a table.
 *
 * How many letters must be inserted, deleted or replaced to turn "kitten"
 * into "sitting"? Three: k to s, e to i, and a g on the end. Trying every
 * way to edit one into the other would never finish; a table answers the
 * question from smaller ones, each answered once. Cell (i, j) holds the
 * distance between the first i letters of b and the first j letters of a.
 * Row 0 is 0 1 2 ...: from nothing to j letters is j insertions. Each row
 * starts with i: from i letters to nothing is i deletions. Every other
 * cell is the smallest of three, each one edit from a cell already filled:
 *
 *   the cell above, plus 1              b's i-th letter deleted
 *   the cell to the left, plus 1        a's j-th letter inserted
 *   the cell above and to the left,     the two letters lined up:
 *     plus 0 if they are the same,        kept
 *     plus 1 if not                       replaced
 *
 * The last cell of the last row is the answer. This is dynamic
 * programming: one big question answered from a table of smaller ones.
 * Module 06's diff fills the same kind of table.
 *
 * A row needs nothing but the row above it, so the table is filled a row
 * at a time and only two rows are kept: all (na + 1) * (nb + 1) cells are
 * filled, but no more than 2 * (na + 1) are held at once. The suggestion
 * walk of lib/trie.c takes the rows one at a time too: words that start
 * with the same letters share their first rows.
 *
 * DS_STATS=1 prints "stats: edit: distances D, rows R, cells filled C":
 * the distances computed whole (edit_distance), the rows filled (theirs,
 * and the trie walk's), and the cells in those rows.
 *
 * DS_TRACE=1 prints the table of each distance computed whole, a line a
 * row, on stderr:
 *   trace: edit: "kitten" "sitting"     a, then b
 *   trace: edit: row 0 -: 0 1 2 3 4 5 6 row 0, for no letter of b yet
 *   trace: edit: row 1 s: 1 1 2 3 4 5 6 row i, for b's i-th letter
 *   trace: edit: distance 3             the last cell of the last row
 */
#include <stdlib.h>
#include <string.h>

#include "edit.h"

static struct {
    long distances, rows, cells;
} st;

static void print_stats(void)
{
    ds_stats_print("edit", "distances %ld, rows %ld, cells filled %ld", st.distances, st.rows, st.cells);
}

static int tracing(void)
{
    static int on = -1;
    if (on < 0) {
        const char *s = getenv("DS_TRACE");
        on = s != NULL && *s != '\0' && strcmp(s, "0") != 0;
    }
    return on;
}

static void trace_row(size_t i, int c, const int *row, size_t na)
{
    fprintf(stderr, "trace: edit: row %zu %c:", i, c);
    for (size_t j = 0; j <= na; j++)
        fprintf(stderr, " %d", row[j]);
    fputc('\n', stderr);
}

/* Row 0: from nothing to the first j letters of a takes j insertions. */
void edit_first_row(int *row, size_t na)
{
    ds_stats_at_exit(print_stats);
    for (size_t j = 0; j <= na; j++)
        row[j] = (int)j;
    st.rows++;
    st.cells += (long)na + 1;
}

/* The next row of the table, for one more letter c of b, from prev, the
 * row above it. */
void edit_next_row(const int *prev, int *row, const char *a, size_t na, int c)
{
    // @build 05.03 one more row: each cell the cheapest of three edits
    row[0] = prev[0] + 1;
    for (size_t j = 1; j <= na; j++) {
        int del = prev[j] + 1;
        int ins = row[j - 1] + 1;
        int rep = prev[j - 1] + ((unsigned char)a[j - 1] != c);
        int best = del < ins ? del : ins;
        row[j] = rep < best ? rep : best;
    }
    st.rows++;
    st.cells += (long)na + 1;
    // @end
}

int edit_distance(const char *a, size_t na, const char *b, size_t nb)
{
    // @build 05.03 the whole table, a row at a time, two rows kept
    int *prev = xmalloc((na + 1) * sizeof *prev);
    int *row = xmalloc((na + 1) * sizeof *row);
    edit_first_row(prev, na);
    if (tracing()) {
        fprintf(stderr, "trace: edit: \"%.*s\" \"%.*s\"\n", (int)na, a, (int)nb, b);
        trace_row(0, '-', prev, na);
    }
    for (size_t i = 1; i <= nb; i++) {
        edit_next_row(prev, row, a, na, (unsigned char)b[i - 1]);
        if (tracing())
            trace_row(i, b[i - 1], row, na);
        int *t = prev;
        prev = row;
        row = t;
    }
    int d = prev[na];
    if (tracing())
        fprintf(stderr, "trace: edit: distance %d\n", d);
    free(prev);
    free(row);
    st.distances++;
    return d;
    // @end
}
