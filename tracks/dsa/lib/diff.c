/*
 * diff.c - two texts compared line by line, the plain way: a table of
 * the longest common subsequence of every pair of their ends.
 *
 * Two versions of a file share most of their lines, in the same order,
 * with other lines between. The shared lines, as many as there can be,
 * are a longest common subsequence (LCS): keep them, delete every other
 * line of the first text, insert every other line of the second, and
 * the first text has become the second. No script does it with fewer
 * lines deleted and inserted.
 *
 * Cell L[i][j] of the table holds the length of the LCS of what is left
 * of the texts from line i of a and line j of b on. The last row and the
 * last column are the empty ends, 0. Every other cell needs only the
 * cells below it and to its right:
 *
 *     a[i] == b[j]:  L[i][j] = L[i+1][j+1] + 1           keep both lines
 *     otherwise:     L[i][j] = max(L[i+1][j], L[i][j+1])  drop one of them
 *
 * so the table is filled from its bottom right corner up, and L[0][0]
 * answers for the whole texts. It has (n+1) x (m+1) cells of four bytes
 * for texts of n and m lines: its time and its memory both grow with the
 * product of the two lengths.
 *
 * A walk from L[0][0] to the far corner reads the script off the          @from 06.02
 * table; its changes, with a few unchanged lines around each, are the     @from 06.02
 * hunks of a unified diff.                                                @from 06.02
 *
 * DS_STATS=1 prints "stats: lcs: cells C, bytes B": the cells filled,
 * and the bytes of the table.
 */
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include "diff.h"

static struct {
    long cells, bytes;
} st;

static void print_stats(void)
{
    ds_stats_print("lcs", "cells %ld, bytes %ld", st.cells, st.bytes);
}

/* The lines of the text at data: each runs to its newline, kept with it;
 * bytes after the last newline are one more line, without one. */
size_t diff_text(DiffText *t, const char *data, size_t size)
{
    array_init(&t->lines, sizeof(DiffLine));
    size_t start = 0;
    while (start < size) {
        const char *nl = memchr(data + start, '\n', size - start);
        size_t end = nl ? (size_t)(nl - data) + 1 : size;
        DiffLine *l = array_push(&t->lines);
        l->s = data + start;
        l->len = end - start;
        l->id = 0;
        start = end;
    }
    return t->lines.len;
}

void diff_text_free(DiffText *t)
{
    array_free(&t->lines);
}

int diff_tracing(const DiffText *a, const DiffText *b)
{
    static int on = -1;
    if (on < 0) {
        const char *s = getenv("DS_TRACE");
        on = s != NULL && *s != '\0' && strcmp(s, "0") != 0;
    }
    return on && a->lines.len <= TRACE_LINES && b->lines.len <= TRACE_LINES;
}

/* Number the lines so that two are equal exactly when their numbers are:
 * each line is looked up in a hash table of the lines seen so far, in
 * either text, and one not seen before takes the next number. From then
 * on, comparing two lines is comparing two numbers, however long the
 * lines are. */
void diff_number(DiffText *a, DiffText *b)
{
    // @build 06.01 number the lines: equal lines, equal numbers
    Table seen;
    table_init(&seen);
    long next = 0;
    DiffText *texts[2] = {a, b};
    for (int k = 0; k < 2; k++) {
        DiffLine *line = (DiffLine *)texts[k]->lines.data;
        for (size_t i = 0; i < texts[k]->lines.len; i++) {
            long *id = table_put(&seen, line[i].s, line[i].len);
            if (*id == 0)
                *id = ++next;
            line[i].id = *id;
        }
    }
    table_free(&seen);
    // @end
}

/* A table of rows x cols cells, refused when it would be too big to be
 * worth waiting for. */
static uint32_t *new_table(size_t rows, size_t cols)
{
    double mb = (double)rows * (double)cols * sizeof(uint32_t) / (1 << 20);
    if (mb > (double)(TABLE_MAX_BYTES >> 20))
        die("%zu and %zu lines: the table would take %.0f MB, more than the %zu MB it may",
            rows - 1, cols - 1, mb, (size_t)(TABLE_MAX_BYTES >> 20));
    st.bytes += (long)(rows * cols * sizeof(uint32_t));
    return xmalloc(rows * cols * sizeof(uint32_t));
}

/* Fill L, a table of (n+1) x (m+1) cells, row after row: L[i][j] is
 * L[i * (m+1) + j]. The bottom row and the right column are the empty
 * ends, 0; every other cell is filled from the three cells below and to
 * the right of it, so the rows go from the bottom up and each row from
 * right to left. */
static void fill(uint32_t *L, const DiffText *a, const DiffText *b)
{
    // @build 06.01 fill the table from the bottom right corner up
    const DiffLine *A = (const DiffLine *)a->lines.data;
    const DiffLine *B = (const DiffLine *)b->lines.data;
    size_t n = a->lines.len, m = b->lines.len, w = m + 1;
    for (size_t j = 0; j <= m; j++)
        L[n * w + j] = 0;
    for (size_t i = n; i-- > 0;) {
        L[i * w + m] = 0;
        for (size_t j = m; j-- > 0;) {
            if (A[i].id == B[j].id) {
                L[i * w + j] = L[(i + 1) * w + j + 1] + 1;
            } else {
                uint32_t down = L[(i + 1) * w + j], right = L[i * w + j + 1];
                L[i * w + j] = down >= right ? down : right;
            }
        }
    }
    st.cells += (long)((n + 1) * w);
    // @end
}

/* DS_TRACE: a line of a text, quoted, without its newline, cut at 30
 * bytes. */
static void trace_line(const DiffLine *l)
{
    size_t len = l->len && l->s[l->len - 1] == '\n' ? l->len - 1 : l->len;
    fputc('"', stderr);
    for (size_t i = 0; i < len && i < 30; i++) {
        unsigned char c = (unsigned char)l->s[i];
        if (c == '"' || c == '\\')
            fprintf(stderr, "\\%c", c);
        else if (c < 32 || c > 126)
            fprintf(stderr, "\\x%02x", c);
        else
            fputc(c, stderr);
    }
    fputs(len > 30 ? "...\"" : "\"", stderr);
}

/* DS_TRACE: both texts, then the table a row at a time in the order it
 * was filled, the bottom row first. A cell where the two lines are equal
 * has "=" after it: its value came from the cell to its lower right. */
static void trace_table(const uint32_t *L, const DiffText *a, const DiffText *b)
{
    const DiffLine *A = (const DiffLine *)a->lines.data;
    const DiffLine *B = (const DiffLine *)b->lines.data;
    size_t n = a->lines.len, m = b->lines.len, w = m + 1;
    fprintf(stderr, "trace: lcs: a has %zu lines, b %zu; L[i][j] is the length of the longest "
            "common subsequence of a from line i and b from line j (from 0)\n", n, m);
    for (size_t i = 0; i < n; i++) {
        fprintf(stderr, "trace: lcs: a %zu ", i);
        trace_line(&A[i]);
        fputc('\n', stderr);
    }
    for (size_t j = 0; j < m; j++) {
        fprintf(stderr, "trace: lcs: b %zu ", j);
        trace_line(&B[j]);
        fputc('\n', stderr);
    }
    for (size_t i = n + 1; i-- > 0;) {
        fprintf(stderr, "trace: lcs: row %zu:", i);
        for (size_t j = 0; j <= m; j++)
            fprintf(stderr, " %u%s", L[i * w + j], i < n && j < m && A[i].id == B[j].id ? "=" : "");
        fputc('\n', stderr);
    }
    fprintf(stderr, "trace: lcs: length %u\n", L[0]);
}

// @from 06.02
static void script_init(DiffScript *s)
{
    array_init(&s->edits, sizeof(DiffEdit));
    s->common = s->ndel = s->nins = 0;
}

void diff_script_free(DiffScript *s)
{
    array_free(&s->edits);
}

static const char *op_name(char op)
{
    return op == ' ' ? "keep" : op == '-' ? "delete" : "insert";
}
// @end

/* The script, read off the filled table by a walk from its top left
 * corner: where the two lines are equal, keep them both and step to the
 * lower right; where they are not, step to whichever of the cells below
 * and to the right holds the longer common subsequence. Down deletes a
 * line of a, right inserts a line of b. On a tie, delete: diff prints the
 * old lines of a change before the new ones. */
static void walk(const uint32_t *L, const DiffText *a, const DiffText *b, DiffScript *s)
{
    // @build 06.02 walk the table to the edit script
    const DiffLine *A = (const DiffLine *)a->lines.data;
    const DiffLine *B = (const DiffLine *)b->lines.data;
    size_t n = a->lines.len, m = b->lines.len, w = m + 1;
    size_t i = 0, j = 0;
    while (i < n || j < m) {
        DiffEdit *e = array_push(&s->edits);
        e->a = i;
        e->b = j;
        if (i < n && j < m && A[i].id == B[j].id) {
            e->op = ' ';
            i++, j++;
        } else if (j == m || (i < n && L[(i + 1) * w + j] >= L[i * w + j + 1])) {
            e->op = '-';
            i++;
        } else {
            e->op = '+';
            j++;
        }
    }
    // @end
}

// @from 06.02
/* DS_TRACE: each step of the walk, with the cells that chose it. */
static void trace_walk(const uint32_t *L, const DiffText *a, const DiffText *b, const DiffScript *s)
{
    const DiffLine *A = (const DiffLine *)a->lines.data;
    const DiffLine *B = (const DiffLine *)b->lines.data;
    size_t n = a->lines.len, m = b->lines.len, w = m + 1;
    for (size_t k = 0; k < s->edits.len; k++) {
        const DiffEdit *e = array_at(&s->edits, k);
        size_t i = e->a, j = e->b;
        fprintf(stderr, "trace: walk: at %zu %zu, L %u: %s ", i, j, L[i * w + j], op_name(e->op));
        trace_line(e->op == '+' ? &B[j] : &A[i]);
        if (e->op != ' ') {
            if (i == n)
                fputs(": a is done", stderr);
            else if (j == m)
                fputs(": b is done", stderr);
            else
                fprintf(stderr, ": below %u %s right %u", L[(i + 1) * w + j],
                        e->op == '-' ? ">=" : "<", L[i * w + j + 1]);
        }
        fputc('\n', stderr);
    }
}
// @end

void diff_table(DiffScript *s, DiffText *a, DiffText *b)
{
    size_t n = a->lines.len, m = b->lines.len;
    ds_stats_at_exit(print_stats);
    diff_number(a, b);
    uint32_t *L = new_table(n + 1, m + 1);
    fill(L, a, b);
    script_init(s);   // @from 06.02
    s->common = L[0];
    s->ndel = n - s->common;
    s->nins = m - s->common;
    walk(L, a, b, s);   // @from 06.02
    if (diff_tracing(a, b)) {
        trace_table(L, a, b);
        trace_walk(L, a, b, s);   // @from 06.02
    }
    free(L);
}

// @from 06.02
/* A hunk: the edits [first, last) of a script. */
typedef struct {
    size_t first, last;
} Hunk;

/* The lines of a hunk in one text, as "start,count": start counts from
 * 1, and a count of 1 is left out. With no lines, start is the line
 * before the hunk, so that "-0,0" is the start of an empty file. */
static void print_range(FILE *out, size_t start, size_t count)
{
    if (count == 0)
        fprintf(out, "%zu,0", start);
    else if (count == 1)
        fprintf(out, "%zu", start + 1);
    else
        fprintf(out, "%zu,%zu", start + 1, count);
}

/* One line of a hunk: its mark and its bytes. A line without a newline,
 * the last of its text, gets one, and the note that it had none. */
static void print_line(FILE *out, char op, const DiffLine *l)
{
    fputc(op, out);
    fwrite(l->s, 1, l->len, out);
    if (l->len == 0 || l->s[l->len - 1] != '\n')
        fputs("\n\\ No newline at end of file\n", out);
}
// @end

/* The next hunk at or after edit i, into h; 0 when no change is left. A
 * hunk starts context lines before a change and ends context lines after
 * one; when two changes have no more than 2 x context unchanged lines
 * between them, those lines would be the context of both, and the two go
 * in one hunk. */
static int next_hunk(const DiffScript *s, size_t i, size_t context, Hunk *h)
{
    // @build 06.02 the next hunk: a change, and the lines around it
    const DiffEdit *e = (const DiffEdit *)s->edits.data;
    size_t n = s->edits.len;
    while (i < n && e[i].op == ' ')
        i++;
    if (i == n)
        return 0;
    h->first = i > context ? i - context : 0;
    size_t end = i;                      /* just after the last change so far */
    for (;;) {
        while (end < n && e[end].op != ' ')
            end++;
        size_t next = end;               /* the next change after it */
        while (next < n && e[next].op == ' ')
            next++;
        if (next == n || next - end > 2 * context)
            break;
        end = next;
    }
    h->last = n - end > context ? end + context : n;
    return 1;
    // @end
}

/* A hunk: its header, then its lines. In each run of changes, the deleted
 * lines come before the inserted ones, as diff prints them, whatever
 * order the script has them in. */
static void print_hunk(FILE *out, const DiffText *a, const DiffText *b, const DiffScript *s, const Hunk *h)
{
    // @build 06.02 print a hunk: "@@ -a,n +b,m @@", then its lines
    const DiffEdit *e = (const DiffEdit *)s->edits.data;
    size_t na = 0, nb = 0;
    for (size_t k = h->first; k < h->last; k++) {
        na += e[k].op != '+';
        nb += e[k].op != '-';
    }
    fputs("@@ -", out);
    print_range(out, e[h->first].a, na);
    fputs(" +", out);
    print_range(out, e[h->first].b, nb);
    fputs(" @@\n", out);
    for (size_t k = h->first; k < h->last;) {
        if (e[k].op == ' ') {
            print_line(out, ' ', array_at(&a->lines, e[k].a));
            k++;
            continue;
        }
        size_t run = k;
        while (run < h->last && e[run].op != ' ')
            run++;
        for (size_t r = k; r < run; r++)
            if (e[r].op == '-')
                print_line(out, '-', array_at(&a->lines, e[r].a));
        for (size_t r = k; r < run; r++)
            if (e[r].op == '+')
                print_line(out, '+', array_at(&b->lines, e[r].b));
        k = run;
    }
    // @end
}

// @from 06.02
size_t diff_unified(FILE *out, const DiffText *a, const DiffText *b, const DiffScript *s, size_t context)
{
    size_t i = 0, hunks = 0;
    Hunk h;
    while (next_hunk(s, i, context, &h)) {
        if (diff_tracing(a, b))
            fprintf(stderr, "trace: hunk: edits %zu to %zu\n", h.first, h.last - 1);
        print_hunk(out, a, b, s, &h);
        i = h.last;
        hunks++;
    }
    return hunks;
}
// @end
