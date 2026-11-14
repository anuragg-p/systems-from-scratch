/*
 * roadgraph.c - a road map read from its file into a graph: the junctions
 * where they are, the roads as the file lists them, and each junction's
 * roads as an adjacency list (roadgraph.h has the file's format).
 *
 * The adjacency lists are not a list per junction. They are three arrays
 * for all of them: first[] says where each junction's arcs start, and to[]
 * and len[] hold the arcs themselves, junction 0's, then junction 1's, and
 * so on. Building them takes two passes over the roads: one to count each
 * junction's roads, which says where each junction's arcs start; one to
 * put each road's two arcs in place.
 */
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>

#include "ds.h"
#include "roadgraph.h"

#define MAX_COORD 1000000000L      /* a million kilometres */

typedef struct {
    FILE       *f;
    const char *path;
    char       *line;
    size_t      cap;
    long        lineno;
} Reader;

/* The next line that is neither blank nor a comment, without its newline;
 * NULL at the end of the file. */
static char *next_line(Reader *r)
{
    ssize_t len;
    while ((len = getline(&r->line, &r->cap, r->f)) >= 0) {
        r->lineno++;
        while (len > 0 && (r->line[len - 1] == '\n' || r->line[len - 1] == '\r'))
            r->line[--len] = '\0';
        if (len > 0 && r->line[0] != '#')
            return r->line;
    }
    return NULL;
}

static _Noreturn void bad(Reader *r, const char *what)
{
    die("%s: line %ld: %s", r->path, r->lineno, what);
}

/* Read want whole numbers from s into v: 1 if s holds exactly that many,
 * each from 0 to max, else 0. */
static int numbers(const char *s, long *v, int want, long max)
{
    for (int k = 0; k < want; k++) {
        char *end;
        errno = 0;
        v[k] = strtol(s, &end, 10);
        if (end == s || errno != 0 || v[k] < 0 || v[k] > max || (*end != ' ' && *end != '\t' && *end != '\0'))
            return 0;
        s = end;
    }
    while (*s == ' ' || *s == '\t')
        s++;
    return *s == '\0';
}

/* The credit line, the junctions and the roads, as the file has them. */
static void read_map(RoadGraph *g, Reader *r)
{
    long v[3];
    char *s = next_line(r);
    if (s != NULL && strncmp(s, "credit ", 7) == 0) {
        g->credit = xstrndup(s + 7, strlen(s + 7));
        s = next_line(r);
    }
    if (s == NULL || strncmp(s, "junctions ", 10) != 0 || !numbers(s + 10, v, 1, 100000000))
        bad(r, "expected \"junctions N\"");
    g->n = (int)v[0];
    g->x = xmalloc(g->n * sizeof *g->x);
    g->y = xmalloc(g->n * sizeof *g->y);
    for (int j = 0; j < g->n; j++) {
        if ((s = next_line(r)) == NULL || !numbers(s, v, 2, MAX_COORD))
            bad(r, "expected a junction: \"X Y\", whole metres from 0 up");
        g->x[j] = (int)v[0];
        g->y[j] = (int)v[1];
    }
    if ((s = next_line(r)) == NULL || strncmp(s, "roads ", 6) != 0 || !numbers(s + 6, v, 1, 500000000))
        bad(r, "expected \"roads M\"");
    g->m = v[0];
    g->road_a = xmalloc(g->m * sizeof *g->road_a);
    g->road_b = xmalloc(g->m * sizeof *g->road_b);
    g->road_len = xmalloc(g->m * sizeof *g->road_len);
    for (long k = 0; k < g->m; k++) {
        if ((s = next_line(r)) == NULL || !numbers(s, v, 3, MAX_COORD))
            bad(r, "expected a road: \"A B METRES\"");
        if (v[0] >= g->n || v[1] >= g->n)
            bad(r, "a road to a junction the map does not have");
        g->road_a[k] = (int)v[0];
        g->road_b[k] = (int)v[1];
        g->road_len[k] = (int)v[2];
    }
    if (next_line(r) != NULL)
        bad(r, "more lines than \"roads\" said");
}

/* Each road as two arcs, one out of each of its ends, every junction's
 * arcs side by side: first[j] .. first[j+1]-1. */
static void build_lists(RoadGraph *g)
{
    // @build 08.01 adjacency lists: count each junction's roads, then put each road's two arcs in place
    g->first = xmalloc((g->n + 1) * sizeof *g->first);
    memset(g->first, 0, (g->n + 1) * sizeof *g->first);
    for (long r = 0; r < g->m; r++) {
        g->first[g->road_a[r] + 1]++;
        g->first[g->road_b[r] + 1]++;
    }
    for (int j = 0; j < g->n; j++)
        g->first[j + 1] += g->first[j];

    long *next = xmalloc(g->n * sizeof *next);        /* where junction j's next arc goes */
    memcpy(next, g->first, g->n * sizeof *next);
    g->to = xmalloc(2 * g->m * sizeof *g->to);
    g->len = xmalloc(2 * g->m * sizeof *g->len);
    for (long r = 0; r < g->m; r++) {
        int a = g->road_a[r], b = g->road_b[r];
        g->to[next[a]] = b;
        g->len[next[a]++] = g->road_len[r];
        g->to[next[b]] = a;
        g->len[next[b]++] = g->road_len[r];
    }
    free(next);
    // @end
}

void roadgraph_load(RoadGraph *g, const char *path)
{
    memset(g, 0, sizeof *g);
    Reader r = {open_input(path), path, NULL, 0, 0};
    read_map(g, &r);
    if (ferror(r.f))
        die("%s: %s", path, strerror(errno));
    free(r.line);
    close_input(r.f);
    build_lists(g);
}

void roadgraph_free(RoadGraph *g)
{
    free(g->x);
    free(g->y);
    free(g->road_a);
    free(g->road_b);
    free(g->road_len);
    free(g->first);
    free(g->to);
    free(g->len);
    free(g->credit);
}
