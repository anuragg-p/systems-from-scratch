/*
 * route - the shortest way between two junctions of a road map, and a
 * picture of it.
 *
 *   route [option ...] MAP FROM TO
 *   route --info [option ...] MAP
 *
 * MAP is a map file: tools/route/london.map is the roads of central London
 * from OpenStreetMap, tools/route/tiny.map a dozen junctions made up to
 * follow by hand (lib/roadgraph.h has the format). FROM and TO are
 * junctions: a junction's number, or X,Y for the junction nearest the
 * point X metres east and Y metres north of the map's south-west corner.
 *
 * --info prints the map's size, how many junctions have 1, 2, 3, ... roads,
 * and its connected pieces: parts of the map that no road joins together.
 * --graph=NAME: how --info finds the roads at a junction:
 *   lists   in the junction's adjacency list (the default)
 *   edges   by reading every road of the map
 *                                                                          @from 08.02
 * A route is printed as a line that sums it up, then one line for each    @from 08.02
 * junction on it, from FROM to TO: the metres so far, the junction, and    @from 08.02
 * where it is. When no road joins the two, route says so and exits 1.      @from 08.02
 * How the route is found:                                                  @from 08.02
 *   bfs            breadth-first search: the fewest junctions, whatever    @from 08.02
 *                  the metres                                              @from 08.02
 *   dijkstra-scan  Dijkstra: the shortest, finding the nearest junction    @from 08.03
 *                  not finished yet by looking at every junction           @from 08.03
 *   dijkstra       Dijkstra, with that junction kept on top of a heap      @from 08.03
 *   astar          A*: Dijkstra, steered towards TO by the straight line   @from 08.04
 * --algo=NAME picks one; the default is the last of them, the best.        @from 08.03
 *
 * --svg=FILE draws the map in FILE, an SVG picture: every road in grey;
 * in colour the roads the search went along from the junctions it finished
 * (with --info: the pieces other than the largest), and the route.
 * --box=X0,Y0,X1,Y1 draws only that part of the map, in metres.
 *
 * DS_STATS=1 prints "stats: route: junctions N, roads M, reached R,
 * finished F, scanned S, relaxed X, stale P, roads read Q": the map's size;
 * junctions the search gave a distance to, and finished (knew their
 * distance for good); junctions looked at to pick the next one to finish;
 * roads followed from a finished junction; old entries taken off the heap
 * and thrown away; and roads read to find the roads at a junction (--info).
 * DS_TRACE=1 prints on stderr one line for each junction a search
 * finishes, with what the search holds then (tools/route/NOTES.md).
 */
#include <math.h>
#include <stdlib.h>
#include <string.h>

#include "ds.h"
#include "roadgraph.h"

static long map_junctions, map_roads;       /* the map's size, for the stats line */
static long reached, finished, scanned, relaxed, stale, roads_read;
static int tracing;

static void print_stats(void)
{
    ds_stats_print("route", "junctions %ld, roads %ld, reached %ld, finished %ld, scanned %ld, relaxed %ld, "
                   "stale %ld, roads read %ld",
                   map_junctions, map_roads, reached, finished, scanned, relaxed, stale, roads_read);
}

/* ------------------------------------------------------------ the map's pieces */

/* DS_TRACE: a junction taken off the flood fill's stack. */
static void trace_stack(int u, int piece, const int *stack, int top)
{
    fprintf(stderr, "trace: pieces: take %d into piece %d; stack:", u, piece);
    for (int i = 0; i < top; i++)
        fprintf(stderr, " %d", stack[i]);
    fputc('\n', stderr);
}

/* Which piece each junction is in, numbered from 0 in the order they are
 * found: from each junction not in a piece yet, everything its roads lead
 * to. Returns how many pieces there are. use_edges: find the roads at a
 * junction by reading every road of the map, not its adjacency list. */
static int pieces(const RoadGraph *g, int use_edges, int *piece)
{
    // @build 08.01 connected pieces: from each junction not in one yet, fill its piece with a stack
    int *stack = xmalloc(g->n * sizeof *stack);
    int count = 0;
    for (int j = 0; j < g->n; j++)
        piece[j] = -1;
    for (int s = 0; s < g->n; s++) {
        if (piece[s] >= 0)
            continue;
        int top = 0;
        piece[s] = count;
        stack[top++] = s;
        while (top > 0) {
            int u = stack[--top];
            if (use_edges) {
                for (long r = 0; r < g->m; r++) {
                    roads_read++;
                    int v = g->road_a[r] == u ? g->road_b[r] : g->road_b[r] == u ? g->road_a[r] : -1;
                    if (v >= 0 && piece[v] < 0) {
                        piece[v] = count;
                        stack[top++] = v;
                    }
                }
            } else {
                for (long a = g->first[u]; a < g->first[u + 1]; a++) {
                    roads_read++;
                    int v = g->to[a];
                    if (piece[v] < 0) {
                        piece[v] = count;
                        stack[top++] = v;
                    }
                }
            }
            if (tracing)
                trace_stack(u, count, stack, top);
        }
        count++;
    }
    free(stack);
    return count;
    // @end
}

// @from 08.02
/* ------------------------------------------------------------ searching */

enum { UNSEEN, REACHED, FINISHED };

static long *dist;              /* from FROM: metres (roads, for bfs); -1 until reached */
static int *prev;               /* the junction before it on the best way found, or -1 */
static unsigned char *state;    /* UNSEEN, REACHED (has a distance) or FINISHED (for good) */

static void start(const RoadGraph *g)
{
    dist = xmalloc(g->n * sizeof *dist);
    prev = xmalloc(g->n * sizeof *prev);
    state = xmalloc(g->n);
    for (int j = 0; j < g->n; j++) {
        dist[j] = -1;
        prev[j] = -1;
        state[j] = UNSEEN;
    }
}

/* DS_TRACE: the start of the line for junction j, just finished. */
static void trace_head(const char *algo, int j, double guess_left)
{
    fprintf(stderr, "trace: %s: finish %d at %ld", algo, j, dist[j]);
    if (guess_left >= 0)
        fprintf(stderr, ", guess %.0f, sum %.0f", guess_left, dist[j] + guess_left);
    if (prev[j] < 0)
        fprintf(stderr, " (start); ");
    else
        fprintf(stderr, " (from %d); ", prev[j]);
}

static void trace_queue(int u, const int *queue, int head, int tail)
{
    trace_head("bfs", u, -1);
    fprintf(stderr, "queue:");
    for (int i = head; i < tail; i++)
        fprintf(stderr, " %d:%ld", queue[i], dist[queue[i]]);
    fputc('\n', stderr);
}
// @end

/* --algo=bfs: the route with the fewest roads, so the fewest junctions.
 * The queue hands out junctions in the order they were reached, so all
 * those one road from FROM are finished before any two roads away. */
static int search_bfs(const RoadGraph *g, int from, int to)
{
    // @build 08.02 breadth-first search: finish junctions in the order a queue reached them
    int *queue = xmalloc(g->n * sizeof *queue);
    int head = 0, tail = 0;
    dist[from] = 0;
    state[from] = REACHED;
    reached++;
    queue[tail++] = from;
    while (head < tail && state[to] != FINISHED) {
        int u = queue[head++];
        state[u] = FINISHED;
        finished++;
        if (u != to) {
            for (long a = g->first[u]; a < g->first[u + 1]; a++) {
                int v = g->to[a];
                relaxed++;
                if (state[v] == UNSEEN) {
                    state[v] = REACHED;
                    reached++;
                    dist[v] = dist[u] + 1;
                    prev[v] = u;
                    queue[tail++] = v;
                }
            }
        }
        if (tracing)
            trace_queue(u, queue, head, tail);
    }
    free(queue);
    return state[to] == FINISHED;
    // @end
}

// @from 08.03
static void trace_reached(const RoadGraph *g, int u)
{
    trace_head("dijkstra-scan", u, -1);
    fprintf(stderr, "reached:");
    for (int j = 0; j < g->n; j++)
        if (state[j] == REACHED)
            fprintf(stderr, " %d:%ld", j, dist[j]);
    fputc('\n', stderr);
}
// @end

/* --algo=dijkstra-scan: the shortest route. Finish the junction nearest
 * FROM of those reached and not finished, found by looking at every
 * junction; follow its roads, giving each junction they lead to a shorter
 * distance if they make one. A junction is finished once nothing can be
 * nearer: every other way to it starts further out. */
static int search_dijkstra_scan(const RoadGraph *g, int from, int to)
{
    // @build 08.03 Dijkstra, slowly: look at every junction to find the nearest not finished
    dist[from] = 0;
    state[from] = REACHED;
    reached++;
    while (state[to] != FINISHED) {
        int u = -1;
        for (int j = 0; j < g->n; j++) {
            scanned++;
            if (state[j] == REACHED && (u < 0 || dist[j] < dist[u]))
                u = j;
        }
        if (u < 0)
            return 0;
        state[u] = FINISHED;
        finished++;
        if (u != to) {
            for (long a = g->first[u]; a < g->first[u + 1]; a++) {
                int v = g->to[a];
                long d = dist[u] + g->len[a];
                relaxed++;
                if (state[v] != FINISHED && (dist[v] < 0 || d < dist[v])) {
                    if (state[v] == UNSEEN)
                        reached++;
                    state[v] = REACHED;
                    dist[v] = d;
                    prev[v] = u;
                }
            }
        }
        if (tracing)
            trace_reached(g, u);
    }
    return 1;
    // @end
}

// @from 08.03
/* A junction waiting on the heap, with what it was pushed with. The heap has no way
 * to change an entry already in it, so a junction given a shorter distance
 * is pushed again, and its old entry stays where it is. The new one comes
 * off the heap first; when the old one does, its junction is finished, and
 * it is thrown away ("stale"). */
typedef struct {
    double key;      /* what the heap orders by: the distance, or for A* that plus the guess */
    long   dist;
    int    j;
} Waiting;

static Waiting *pool;          /* every entry pushed, so that a pointer to one stays good */
static long npool;

static Waiting *waiting(double key, long d, int j)
{
    Waiting *e = &pool[npool++];
    e->key = key;
    e->dist = d;
    e->j = j;
    return e;
}

/* The heap's order: the smaller key first; on a tie, the smaller junction,
 * which is the one --algo=dijkstra-scan picks too. */
static int by_key(const void *a, const void *b, void *ctx)
{
    const Waiting *x = a, *y = b;
    if (x->key != y->key)
        return x->key < y->key ? -1 : 1;
    return (x->j > y->j) - (x->j < y->j);
}

/* DS_TRACE: the heap as it is, in its array's order (the top first); an
 * entry whose junction has been given a shorter distance since is marked
 * (old). */
static void trace_heap(const char *algo, int u, const Heap *h, double guess_left)
{
    if (u >= 0)
        trace_head(algo, u, guess_left);
    fprintf(stderr, "heap:");
    for (size_t i = 0; i < heap_len(h); i++) {
        const Waiting *e = ((Waiting **)h->items.data)[i];
        fprintf(stderr, " %d:%.0f%s", e->j, e->key, e->dist != dist[e->j] ? "(old)" : "");
    }
    fputc('\n', stderr);
}

static void trace_stale(const char *algo, const Waiting *e, const Heap *h)
{
    fprintf(stderr, "trace: %s: skip %d at %.0f, finished at %ld already; ", algo, e->j, e->key, dist[e->j]);
    trace_heap(algo, -1, h, -1);
}
// @end

/* --algo=dijkstra: the same, with the junctions reached kept in a heap by
 * their distance, so the nearest is the one on top. */
static int search_dijkstra(const RoadGraph *g, int from, int to)
{
    // @build 08.03 Dijkstra with a heap: the nearest junction not finished is on top
    Heap h;
    heap_init(&h, by_key, NULL);
    dist[from] = 0;
    state[from] = REACHED;
    reached++;
    heap_push(&h, waiting(0, 0, from));
    while (heap_len(&h) > 0 && state[to] != FINISHED) {
        Waiting *e = heap_pop(&h);
        int u = e->j;
        if (state[u] == FINISHED) {
            stale++;
            if (tracing)
                trace_stale("dijkstra", e, &h);
            continue;
        }
        state[u] = FINISHED;
        finished++;
        if (u != to) {
            for (long a = g->first[u]; a < g->first[u + 1]; a++) {
                int v = g->to[a];
                long d = dist[u] + g->len[a];
                relaxed++;
                if (state[v] != FINISHED && (dist[v] < 0 || d < dist[v])) {
                    if (state[v] == UNSEEN)
                        reached++;
                    state[v] = REACHED;
                    dist[v] = d;
                    prev[v] = u;
                    heap_push(&h, waiting(d, d, v));
                }
            }
        }
        if (tracing)
            trace_heap("dijkstra", u, &h, -1);
    }
    heap_free(&h);
    return state[to] == FINISHED;
    // @end
}

/* What A* guesses is left from junction j to TO: the straight line. */
static double guess(const RoadGraph *g, int j, int to)
{
    // @build 08.04 the guess: the straight line to TO, which no road can beat
    double dx = g->x[j] - g->x[to], dy = g->y[j] - g->y[to];
    return sqrt(dx * dx + dy * dy);
    // @end
}

/* --algo=astar: Dijkstra, but the heap is ordered by the distance so far
 * plus the guess of what is left, so junctions towards TO come off first
 * and those behind FROM may never be reached. */
static int search_astar(const RoadGraph *g, int from, int to)
{
    // @build 08.04 A*: Dijkstra, with the heap ordered by the distance plus the guess
    Heap h;
    heap_init(&h, by_key, NULL);
    dist[from] = 0;
    state[from] = REACHED;
    reached++;
    heap_push(&h, waiting(guess(g, from, to), 0, from));
    while (heap_len(&h) > 0 && state[to] != FINISHED) {
        Waiting *e = heap_pop(&h);
        int u = e->j;
        if (state[u] == FINISHED) {
            stale++;
            if (tracing)
                trace_stale("astar", e, &h);
            continue;
        }
        state[u] = FINISHED;
        finished++;
        if (u != to) {
            for (long a = g->first[u]; a < g->first[u + 1]; a++) {
                int v = g->to[a];
                long d = dist[u] + g->len[a];
                relaxed++;
                if (state[v] != FINISHED && (dist[v] < 0 || d < dist[v])) {
                    if (state[v] == UNSEEN)
                        reached++;
                    state[v] = REACHED;
                    dist[v] = d;
                    prev[v] = u;
                    heap_push(&h, waiting(d + guess(g, v, to), d, v));
                }
            }
        }
        if (tracing)
            trace_heap("astar", u, &h, guess(g, u, to));
    }
    heap_free(&h);
    return state[to] == FINISHED;
    // @end
}

// @from 08.02
typedef struct {
    const char *name;
    int (*search)(const RoadGraph *g, int from, int to);
} Algo;

static const Algo algos[] = {
    {"bfs", search_bfs},
    {"dijkstra-scan", search_dijkstra_scan},     // @from 08.03
    {"dijkstra", search_dijkstra},               // @from 08.03
    {"astar", search_astar},                     // @from 08.04
    {NULL, NULL},
};

/* The search called name; with no name, the last of them, the best. */
static const Algo *pick(const char *name)
{
    char have[200] = "";
    int i;
    for (i = 0; algos[i].name; i++) {
        if (name != NULL && strcmp(name, algos[i].name) == 0)
            return &algos[i];
        strcat(strcat(have, i ? ", " : ""), algos[i].name);
    }
    if (name == NULL)
        return &algos[i - 1];
    die("no --algo '%s' (have: %s)", name, have);
}

/* The length of the shortest road between junctions a and b. */
static long road_between(const RoadGraph *g, int a, int b)
{
    long best = -1;
    for (long k = g->first[a]; k < g->first[a + 1]; k++)
        if (g->to[k] == b && (best < 0 || g->len[k] < best))
            best = g->len[k];
    return best;
}

/* The route, from FROM to TO, as prev[] has it backwards; its length in
 * *n. */
static int *route_of(int to, int *n)
{
    *n = 0;
    for (int j = to; j >= 0; j = prev[j])
        (*n)++;
    int *path = xmalloc(*n * sizeof *path);
    int k = *n;
    for (int j = to; j >= 0; j = prev[j])
        path[--k] = j;
    return path;
}

static void print_route(const RoadGraph *g, const int *path, int n)
{
    long total = 0;
    for (int k = 1; k < n; k++)
        total += road_between(g, path[k - 1], path[k]);
    printf("from %d to %d: %ld metres, %d junctions\n", path[0], path[n - 1], total, n);
    printf("  metres  junction       x       y\n");
    long so_far = 0;
    for (int k = 0; k < n; k++) {
        if (k > 0)
            so_far += road_between(g, path[k - 1], path[k]);
        printf("%8ld %9d %7d %7d\n", so_far, path[k], g->x[path[k]], g->y[path[k]]);
    }
}
// @end

/* ------------------------------------------------------------ the picture */

typedef struct {
    int x0, y0, x1, y1;
} Box;

static void xml_text(FILE *f, const char *s)
{
    for (; *s; s++) {
        if (*s == '&')
            fputs("&amp;", f);
        else if (*s == '<')
            fputs("&lt;", f);
        else if (*s == '>')
            fputs("&gt;", f);
        else
            fputc(*s, f);
    }
}

/* Draw the map into the SVG file at path: every road in grey; in colour
 * the roads with an end marked in mark (if not NULL); the route (n
 * junctions, if any) on top; and the map's credit, as its licence asks.
 * Only the part in box is drawn, or all of the map. The picture's y goes
 * down, the map's up: a point is drawn at (x, top - y). */
static void write_svg(const RoadGraph *g, const char *path, const Box *box, const unsigned char *mark,
                      const int *route, int n, const char *caption)
{
    FILE *f = fopen(path, "w");
    if (f == NULL)
        die("cannot write %s", path);
    int top = 0;
    Box all = {0, 0, 1, 1};
    for (int j = 0; j < g->n; j++) {
        if (g->x[j] > all.x1)
            all.x1 = g->x[j];
        if (g->y[j] > all.y1)
            all.y1 = g->y[j];
    }
    top = all.y1;
    if (box == NULL)
        box = &all;
    int w = box->x1 - box->x0, h = box->y1 - box->y0, pad = (w > h ? w : h) / 40 + 1;
    int vx = box->x0 - pad, vy = top - box->y1 - pad, vw = w + 2 * pad, vh = h + 2 * pad;
    double font = vw / 70.0, dot = vw / 160.0;

    fprintf(f, "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"%d %d %d %d\" width=\"1000\" height=\"%d\">\n",
            vx, vy, vw, vh, (int)(1000.0 * vh / vw + 0.5));
    fprintf(f, "<title>");
    xml_text(f, caption);
    fprintf(f, "</title>\n");
    fprintf(f, "<rect x=\"%d\" y=\"%d\" width=\"%d\" height=\"%d\" fill=\"#ffffff\"/>\n", vx, vy, vw, vh);
    for (int layer = 0; layer < 2; layer++) {
        if (layer == 1 && mark == NULL)
            break;
        fprintf(f, "<path fill=\"none\" stroke=\"%s\" stroke-width=\"%s\" stroke-linecap=\"round\" "
                "vector-effect=\"non-scaling-stroke\" d=\"",
                layer ? "#2f6fd0" : "#bbbbbb", layer ? "1.4" : "0.7");
        for (long r = 0; r < g->m; r++) {
            int a = g->road_a[r], b = g->road_b[r];
            if (layer == 1 && !mark[a] && !mark[b])
                continue;
            int in_a = g->x[a] >= box->x0 && g->x[a] <= box->x1 && g->y[a] >= box->y0 && g->y[a] <= box->y1;
            int in_b = g->x[b] >= box->x0 && g->x[b] <= box->x1 && g->y[b] >= box->y0 && g->y[b] <= box->y1;
            if (in_a || in_b)
                fprintf(f, "M%d %dL%d %d", g->x[a], top - g->y[a], g->x[b], top - g->y[b]);
        }
        fprintf(f, "\"/>\n");
    }
    if (n > 0) {
        fprintf(f, "<path fill=\"none\" stroke=\"#d1495b\" stroke-width=\"3.5\" stroke-linecap=\"round\" "
                "stroke-linejoin=\"round\" vector-effect=\"non-scaling-stroke\" d=\"");
        for (int k = 0; k < n; k++)
            fprintf(f, "%c%d %d", k ? 'L' : 'M', g->x[route[k]], top - g->y[route[k]]);
        fprintf(f, "\"/>\n");
        fprintf(f, "<circle cx=\"%d\" cy=\"%d\" r=\"%.1f\" fill=\"#2a9d4b\"/>\n", g->x[route[0]],
                top - g->y[route[0]], dot);
        fprintf(f, "<circle cx=\"%d\" cy=\"%d\" r=\"%.1f\" fill=\"#d1495b\"/>\n", g->x[route[n - 1]],
                top - g->y[route[n - 1]], dot);
    }
    fprintf(f, "<text x=\"%.0f\" y=\"%.0f\" font-size=\"%.0f\" fill=\"#222222\">", vx + font, vy + 1.6 * font, font);
    xml_text(f, caption);
    fprintf(f, "</text>\n");
    if (g->credit != NULL) {
        fprintf(f, "<text x=\"%.0f\" y=\"%.0f\" font-size=\"%.0f\" fill=\"#444444\" text-anchor=\"end\">",
                vx + vw - font / 2, vy + vh - font / 2, font * 0.75);
        xml_text(f, g->credit);
        fprintf(f, "</text>\n");
    }
    fprintf(f, "</svg>\n");
    if (ferror(f) || fclose(f) != 0)
        die("cannot write %s", path);
}

/* ------------------------------------------------------------ --info */

static void info(const RoadGraph *g, int use_edges, const char *svg, const Box *box)
{
    long metres = 0;
    int most = 0;
    for (long r = 0; r < g->m; r++)
        metres += g->road_len[r];
    for (int j = 0; j < g->n; j++)
        if (g->first[j + 1] - g->first[j] > most)
            most = (int)(g->first[j + 1] - g->first[j]);
    printf("junctions %d, roads %ld, %.1f km of road\n", g->n, g->m, metres / 1000.0);

    long *count = xmalloc((most + 1) * sizeof *count);
    memset(count, 0, (most + 1) * sizeof *count);
    for (int j = 0; j < g->n; j++)
        count[g->first[j + 1] - g->first[j]]++;
    for (int d = 0; d <= most; d++)
        if (count[d])
            printf("%8ld junction%s with %d road%s\n", count[d], count[d] == 1 ? " " : "s", d, d == 1 ? "" : "s");
    free(count);

    int *piece = xmalloc((g->n ? g->n : 1) * sizeof *piece);
    int np = pieces(g, use_edges, piece);
    long *size = xmalloc((np ? np : 1) * sizeof *size);
    memset(size, 0, (np ? np : 1) * sizeof *size);
    for (int j = 0; j < g->n; j++)
        size[piece[j]]++;
    int largest = 0;
    for (int p = 1; p < np; p++)
        if (size[p] > size[largest])
            largest = p;
    printf("pieces %d", np);
    /* the ten largest, by ten passes that each take the largest left */
    for (int k = 0; k < 10 && k < np; k++) {
        int best = -1;
        for (int p = 0; p < np; p++)
            if (size[p] >= 0 && (best < 0 || size[p] > size[best]))
                best = p;
        printf("%s%ld", k ? ", " : ": junctions in each, the largest first: ", size[best]);
        size[best] = -1;
    }
    printf("%s\n", np > 10 ? ", ..." : "");

    if (svg != NULL) {
        unsigned char *other = xmalloc(g->n ? g->n : 1);
        for (int j = 0; j < g->n; j++)
            other[j] = piece[j] != largest;
        char caption[200];
        snprintf(caption, sizeof caption, "%d junctions, %ld roads; in colour: the %d pieces but the largest",
                 g->n, g->m, np > 0 ? np - 1 : 0);
        write_svg(g, svg, box, other, NULL, 0, caption);
        free(other);
    }
    free(size);
    free(piece);
}

/* ------------------------------------------------------------ main */

/* A junction given on the command line: its number, or X,Y for the
 * junction nearest that point. */
static int junction(const RoadGraph *g, const char *s)
{
    char *end;
    long v = strtol(s, &end, 10);
    if (end != s && *end == '\0') {
        if (v < 0 || v >= g->n)
            die("no junction %s: the map's are 0 to %d", s, g->n - 1);
        return (int)v;
    }
    long x, y;
    char extra;
    if (sscanf(s, "%ld,%ld%c", &x, &y, &extra) != 2)
        die("'%s' is not a junction: give its number, or X,Y in metres", s);
    int best = -1;
    double bd = 0;
    for (int j = 0; j < g->n; j++) {
        double dx = g->x[j] - x, dy = g->y[j] - y, d = dx * dx + dy * dy;
        if (best < 0 || d < bd) {
            best = j;
            bd = d;
        }
    }
    if (best < 0)
        die("the map has no junctions");
    return best;
}

static void usage(void)
{
    die("usage: route [option ...] MAP FROM TO, or route --info [option ...] MAP");
}

int main(int argc, char **argv)
{
    progname = "route";
    ds_stats_at_exit(print_stats);
    const char *t = getenv("DS_TRACE");
    tracing = t != NULL && *t != '\0' && strcmp(t, "0") != 0;
    int want_info = 0, use_edges = -1;
    const char *svg = NULL;
    Box box;
    int have_box = 0;
    const char *algo_name = NULL;   // @from 08.02
    const char *args[3];
    int nargs = 0;
    for (int i = 1; i < argc; i++) {
        const char *a = argv[i];
        if (strcmp(a, "--info") == 0) {
            want_info = 1;
            continue;
        }
        if (strncmp(a, "--graph=", 8) == 0) {
            if (strcmp(a + 8, "lists") != 0 && strcmp(a + 8, "edges") != 0)
                die("no --graph '%s' (have: lists, edges)", a + 8);
            use_edges = strcmp(a + 8, "edges") == 0;
            continue;
        }
        if (strncmp(a, "--svg=", 6) == 0 && a[6] != '\0') {
            svg = a + 6;
            continue;
        }
        if (strncmp(a, "--box=", 6) == 0) {
            char extra;
            if (sscanf(a + 6, "%d,%d,%d,%d%c", &box.x0, &box.y0, &box.x1, &box.y1, &extra) != 4 ||
                box.x0 >= box.x1 || box.y0 >= box.y1)
                die("--box wants X0,Y0,X1,Y1 in metres, X0 < X1 and Y0 < Y1, not '%s'", a + 6);
            have_box = 1;
            continue;
        }
        // @from 08.03
        if (strncmp(a, "--algo=", 7) == 0) {
            algo_name = pick(a + 7)->name;
            continue;
        }
        // @end
        if (strcmp(a, "--") == 0) {
            for (i++; i < argc; i++) {
                if (nargs == 3)
                    usage();
                args[nargs++] = argv[i];
            }
            break;
        }
        if (a[0] == '-' && a[1] == '-')
            die("unknown option '%s'", a);
        if (a[0] == '-' && a[1] != '\0')
            usage();
        if (nargs == 3)
            usage();
        args[nargs++] = a;
    }
    if (want_info ? nargs != 1 : nargs != 3)
        usage();
    if (use_edges >= 0 && !want_info)
        die("--graph goes with --info");

    RoadGraph g;
    roadgraph_load(&g, args[0]);
    map_junctions = g.n;
    map_roads = g.m;
    if (want_info) {
        info(&g, use_edges > 0, svg, have_box ? &box : NULL);
        return ferror(stdout) ? 2 : 0;
    }
    // @from 08.02
    int from = junction(&g, args[1]), to = junction(&g, args[2]);
    const Algo *algo = pick(algo_name);
    start(&g);
    pool = xmalloc((2 * g.m + 1) * sizeof *pool);   // @from 08.03
    int found = algo->search(&g, from, to);
    int n = 0;
    int *path = found ? route_of(to, &n) : NULL;
    if (svg != NULL) {
        unsigned char *done = xmalloc(g.n ? g.n : 1);
        for (int j = 0; j < g.n; j++)
            done[j] = state[j] == FINISHED;
        char caption[200];
        if (found)
            snprintf(caption, sizeof caption, "%s from %d to %d: %ld junctions finished; route in red",
                     algo->name, from, to, finished);
        else
            snprintf(caption, sizeof caption, "%s from %d to %d: %ld junctions finished; no route",
                     algo->name, from, to, finished);
        write_svg(&g, svg, have_box ? &box : NULL, done, path, n, caption);
        free(done);
    }
    if (!found) {
        printf("from %d to %d: no route: no road joins them\n", from, to);
        return 1;
    }
    print_route(&g, path, n);
    free(path);
    return ferror(stdout) ? 2 : 0;
    // @else
    // die("no search to find a route with yet: try --info");
    // @end
}
