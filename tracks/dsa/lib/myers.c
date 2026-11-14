/*
 * myers.c - a shortest edit script without the whole table: the search
 * of Eugene Myers, "An O(ND) Difference Algorithm and Its Variations"
 * (Algorithmica 1, 1986), in its basic form.
 *
 * Take diff.c's table as a grid of points: (x, y) is "x lines of a and
 * y lines of b done", from (0, 0) to (n, m). A step right deletes line x
 * of a; a step down inserts line y of b; where a[x] equals b[y], a
 * diagonal step keeps the line, and costs nothing. This is the edit
 * graph, and an edit script is a path through it from corner to corner:
 * a shortest script is a path with the fewest steps that are not
 * diagonal. The table worked out every point of the grid; the search
 * below spreads out from (0, 0) by the number of edits, and stops as soon
 * as it reaches (n, m).
 *
 * Name each diagonal by k = x - y: diagonal 0 runs from (0, 0), and (n, m)
 * is on diagonal n - m. After d edits a path can only be on a diagonal
 * from -d to d, every second one. For each of them the search keeps one
 * point: the furthest along it that d edits can reach, as its x. Round d
 * takes, for each diagonal k, one more edit from round d-1's point on a
 * neighbouring diagonal (down from k+1 or right from k-1, whichever is
 * further on), then follows diagonal k for free while the lines are
 * equal: a "snake". The first round in which a point reaches (n, m) is the
 * length of a shortest script, D. Round d costs d+1 points and their
 * snakes, so the search looks at about (n + m) x D points, not n x m;
 * for two versions of one file D is small, and the search is quick. For
 * two files with nothing in common D is n + m, and it is no better.
 *
 * To find the path again, every round's points are kept: 1 + 2 + ... +
 * (D+1) of them, memory that grows with D squared, not with the files.
 * A walk back from (n, m) asks of each round which neighbour its point
 * came from, by the same rule the search used.
 *
 * DS_STATS=1 prints "stats: myers: d D, diagonals K, cells C, bytes B":
 * the length of the script; the furthest points worked out, one for each
 * diagonal of each round; the points of the edit graph the search
 * reached, those and each step of a snake (diff.c's "cells" are the same
 * points, all of them); and the bytes of the kept points.
 */
#include <stdint.h>
#include <stdlib.h>

#include "diff.h"

static struct {
    long d, diagonals, cells, bytes;
} st;

static void print_stats(void)
{
    ds_stats_print("myers", "d %ld, diagonals %ld, cells %ld, bytes %ld", st.d, st.diagonals, st.cells, st.bytes);
}

/* The kept points: round d's point on diagonal k is its x, at index
 * d(d+1)/2 + (k+d)/2 of an Array of int32_t, after every earlier round. */
static int32_t at(const Array *v, long d, long k)
{
    return ((const int32_t *)v->data)[d * (d + 1) / 2 + (k + d) / 2];
}

/* Keep round d's point on the next diagonal, x. The kept points may take
 * no more memory than the table may (DIFF_MAX_BYTES): two files with
 * nothing in common take D x D / 2 of them. */
static void keep(Array *v, long x)
{
    if ((v->len + 1) * sizeof(int32_t) > DIFF_MAX_BYTES)
        die("the files are so different that the search would keep more than %zu MB of points",
            (size_t)(DIFF_MAX_BYTES >> 20));
    *(int32_t *)array_push(v) = (int32_t)x;
}

/* Whether round d reached diagonal k by a step down from k+1 (an
 * insertion), rather than right from k-1 (a deletion): down when k is
 * the lowest diagonal, or when k+1's point is further on; right on a tie,
 * so that a change deletes before it inserts. */
static int came_down(const Array *v, long d, long k)
{
    return k == -d || (k != d && at(v, d - 1, k - 1) < at(v, d - 1, k + 1));
}

/* The search: round after round, the furthest point on each diagonal,
 * into v, until one is (n, m). Returns d, the number of edits. */
static long search(const DiffText *a, const DiffText *b, Array *v)
{
    // @build 06.03 search: the furthest point on each diagonal, d edits at a time
    const DiffLine *A = (const DiffLine *)a->lines.data;
    const DiffLine *B = (const DiffLine *)b->lines.data;
    long n = (long)a->lines.len, m = (long)b->lines.len;
    for (long d = 0; d <= n + m; d++) {
        for (long k = -d; k <= d; k += 2) {
            long x;
            if (d == 0)
                x = 0;
            else if (came_down(v, d, k))
                x = at(v, d - 1, k + 1);
            else
                x = at(v, d - 1, k - 1) + 1;
            long y = x - k;
            st.diagonals++;
            st.cells++;
            while (x < n && y < m && A[x].id == B[y].id) {
                x++, y++;
                st.cells++;
            }
            keep(v, x);
            if (x >= n && y >= m)
                return d;
        }
    }
    return n + m;   /* not reached: n + m edits always do it */
    // @end
}

/* The script, from (n, m) back to (0, 0) through the kept points. At
 * round d the point on diagonal k came by one edit from round d-1's point
 * on k+1 or k-1, then a snake of kept lines; round 0's point came by a
 * snake from (0, 0). The steps come out last first, and are turned round
 * at the end. */
static void backtrack(const Array *v, long d, const DiffText *a, const DiffText *b, DiffScript *s)
{
    // @build 06.03 walk back through the kept points to the script
    long x = (long)a->lines.len, y = (long)b->lines.len;
    for (; d >= 0; d--) {
        long k = x - y, px = 0, py = 0;     /* where this round's edit started */
        int down = 0;
        if (d > 0) {
            down = came_down(v, d, k);
            px = at(v, d - 1, down ? k + 1 : k - 1);
            py = px - (down ? k + 1 : k - 1);
        }
        long sx = d > 0 && !down ? px + 1 : px;   /* where the snake started */
        while (x > sx) {
            DiffEdit *e = array_push(&s->edits);
            e->op = ' ';
            e->a = (size_t)--x;
            e->b = (size_t)--y;
        }
        if (d > 0) {
            DiffEdit *e = array_push(&s->edits);
            e->op = down ? '+' : '-';
            e->a = (size_t)px;
            e->b = (size_t)py;
            x = px;
            y = py;
        }
    }
    DiffEdit *e = (DiffEdit *)s->edits.data;
    for (size_t i = 0, j = s->edits.len; i + 1 < j; i++, j--) {
        DiffEdit t = e[i];
        e[i] = e[j - 1];
        e[j - 1] = t;
    }
    // @end
}

/* DS_TRACE: each round, a line for each diagonal: the edit that brought
 * it there, from which point, and the snake after it; then the path. */
static void trace(const Array *v, long D, const DiffText *a, const DiffText *b, const DiffScript *s)
{
    fprintf(stderr, "trace: myers: a has %zu lines, b %zu; a point (x, y) is x lines of a and y of b "
            "done; diagonal k holds the points with x - y = k\n", a->lines.len, b->lines.len);
    for (long d = 0; d <= D; d++) {
        for (long k = -d; k <= d; k += 2) {
            if (d * (d + 1) / 2 + (k + d) / 2 >= (long)v->len)
                break;                          /* round D stops at the corner */
            long x = at(v, d, k), sx, sy;
            if (d == 0) {
                sx = sy = 0;
                fprintf(stderr, "trace: myers: d 0 k 0: start (0,0)");
            } else {
                int down = came_down(v, d, k);
                long px = at(v, d - 1, down ? k + 1 : k - 1), py = px - (down ? k + 1 : k - 1);
                sx = down ? px : px + 1;
                sy = sx - k;
                fprintf(stderr, "trace: myers: d %ld k %ld: %s from (%ld,%ld) to (%ld,%ld)", d, k,
                        down ? "down" : "right", px, py, sx, sy);
            }
            fprintf(stderr, ", snake %ld, reaches (%ld,%ld)\n", x - sx, x, x - k);
        }
    }
    fprintf(stderr, "trace: myers: (%zu,%zu) reached with d %ld\n", a->lines.len, b->lines.len, D);
    for (size_t i = 0; i < s->edits.len; i++) {
        const DiffEdit *e = array_at(&s->edits, i);
        fprintf(stderr, "trace: myers: path (%zu,%zu) %s\n", e->a, e->b,
                e->op == ' ' ? "keep" : e->op == '-' ? "delete" : "insert");
    }
}

void diff_myers(DiffScript *s, DiffText *a, DiffText *b)
{
    size_t n = a->lines.len, m = b->lines.len;
    ds_stats_at_exit(print_stats);
    if (n + m > INT32_MAX)
        die("%zu and %zu lines: too many to compare", n, m);
    diff_number(a, b);
    Array v;
    array_init(&v, sizeof(int32_t));
    long d = search(a, b, &v);
    st.d += d;
    st.bytes += (long)(v.len * sizeof(int32_t));
    array_init(&s->edits, sizeof(DiffEdit));
    s->ndel = s->nins = 0;
    backtrack(&v, d, a, b, s);
    for (size_t i = 0; i < s->edits.len; i++) {
        const DiffEdit *e = array_at(&s->edits, i);
        s->ndel += e->op == '-';
        s->nins += e->op == '+';
    }
    s->common = n - s->ndel;
    if (diff_tracing(a, b))
        trace(&v, d, a, b, s);
    array_free(&v);
}
