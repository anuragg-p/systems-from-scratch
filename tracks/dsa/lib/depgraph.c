/*
 * depgraph.c - a dependency graph, and two ways to walk it.
 *
 * The nodes live in one growable array, in the order they were added, and
 * a node is known by its index there. A hash table maps each name to its
 * index, so the reader of a makefile finds "lib/ds.h" in one lookup however
 * many targets there are. Each node keeps the indexes of the nodes it
 * needs, in an array of its own, in the order they were given: an
 * adjacency list.
 *
 * The obvious way to do something to everything a node needs is to
 * recurse: graph_walk. It remembers nothing, so a node reached by two
 * paths is walked twice, and everything below it twice too.
 * Depth-first search (graph_search) marks each node as it goes, open      @from 07.02
 * while it is on the path and done once everything below it is: a done    @from 07.02
 * node is never entered again, and meeting an open one is a cycle.       @from 07.02
 */
#include <stdlib.h>
#include <string.h>

#include "depgraph.h"

static struct {
    long nodes, edges, walk_visits, walk_edges, search_visits, search_edges;
} st;

static void print_stats(void)
{
    ds_stats_print("depgraph", "nodes %ld, edges %ld, walk visits %ld, walk edges %ld, "
                   "search visits %ld, search edges %ld", st.nodes, st.edges, st.walk_visits,
                   st.walk_edges, st.search_visits, st.search_edges);
}

static int tracing = -1;

/* DS_TRACE=1: one line on stderr for each step of a walk or a search. */
static void trace(const char *event, long depth, const Node *n)
{
    if (tracing < 0) {
        const char *s = getenv("DS_TRACE");
        tracing = s != NULL && *s != '\0' && strcmp(s, "0") != 0;
    }
    if (tracing)
        fprintf(stderr, "trace: %s %ld %s\n", event, depth, n->name);
}

/* An empty graph. */
void graph_init(Graph *g)
{
    // @build 07.01 an empty graph: no nodes, and an empty table of names
    array_init(&g->nodes, sizeof(Node));
    table_init(&g->index);
    ds_stats_at_exit(print_stats);
    // @end
}

long graph_find(Graph *g, const char *name)
{
    long *i = table_get(&g->index, name, strlen(name));
    return i ? *i : -1;
}

/* The node called name: found in the table, or added at the end of the
 * nodes, with nothing it needs yet. */
long graph_node(Graph *g, const char *name)
{
    // @build 07.01 a node by its name: look in the table, add it if new
    size_t len = strlen(name);
    long *i = table_get(&g->index, name, len);
    if (i != NULL)
        return *i;
    Node *n = array_push(&g->nodes);
    memset(n, 0, sizeof *n);
    n->name = xstrndup(name, len);
    array_init(&n->needs, sizeof(long));
    array_init(&n->needed_by, sizeof(long));      // @from 07.04
    *table_put(&g->index, name, len) = (long)g->nodes.len - 1;
    st.nodes++;
    return (long)g->nodes.len - 1;
    // @end
}

/* from needs to: to goes at the end of from's list, unless it is there
 * already (a makefile may name a prerequisite twice). */
void graph_edge(Graph *g, long from, long to)
{
    // @build 07.01 an edge: one more node that this node needs
    Node *f = graph_at(g, from);
    for (size_t i = 0; i < f->needs.len; i++)
        if (*(long *)array_at(&f->needs, i) == to)
            return;
    *(long *)array_push(&f->needs) = to;
    *(long *)array_push(&graph_at(g, to)->needed_by) = from;   // @from 07.04
    st.edges++;
    // @end
}

Node *graph_at(const Graph *g, long i)
{
    return array_at(&g->nodes, (size_t)i);
}

size_t graph_len(const Graph *g)
{
    return g->nodes.len;
}

/* Walk node n, which the walk reached from node from at depth edges below
 * the root: everything it needs first, then n itself. A path longer than
 * there are nodes must pass some node twice: the graph has a cycle. */
static int walk(Graph *g, long n, long from, long depth, Visit visit, void *ctx)
{
    // @build 07.01 the walk: everything a node needs, then the node
    Node *node = graph_at(g, n);
    st.walk_visits++;
    trace("walk", depth, node);
    if (depth >= (long)g->nodes.len)
        return -1;
    for (size_t i = 0; i < node->needs.len; i++) {
        st.walk_edges++;
        if (walk(g, *(long *)array_at(&node->needs, i), n, depth + 1, visit, ctx) < 0)
            return -1;
    }
    visit(g, n, from, ctx);
    return 0;
    // @end
}

int graph_walk(Graph *g, long root, Visit visit, void *ctx)
{
    return walk(g, root, -1, 0, visit, ctx);
}

// @from 07.02
/* One node on the search's path, and how far along its needs it is. */
typedef struct {
    long node;
    size_t next;         /* the index in needs of the next one to look at */
} Frame;

/* Enter node n, reached from node from: it is open, and on top of the path. */
static void enter(Graph *g, Array *path, long n, long from)
{
    Node *node = graph_at(g, n);
    node->state = NODE_OPEN;
    node->from = from;
    Frame *f = array_push(path);
    f->node = n;
    f->next = 0;
    st.search_visits++;
    trace("enter", (long)path->len - 1, node);
}
// @end

/* Depth-first search, with the path kept in an array rather than on the
 * C stack, so that a chain of a million targets cannot overflow it, and so
 * that the path is there to read when the search meets a cycle. */
int graph_search(Graph *g, const long *roots, size_t nroots, Array *order, Array *cycle)
{
    // @build 07.02 depth-first search: new, open and done
    for (size_t i = 0; i < g->nodes.len; i++)
        graph_at(g, (long)i)->state = NODE_NEW;
    Array path;
    array_init(&path, sizeof(Frame));
    for (size_t r = 0; r < nroots; r++) {
        if (graph_at(g, roots[r])->state != NODE_NEW)
            continue;
        enter(g, &path, roots[r], -1);
        while (path.len > 0) {
            Frame *top = array_at(&path, path.len - 1);
            Node *node = graph_at(g, top->node);
            if (top->next == node->needs.len) {
                /* everything it needs is done: so is it */
                node->state = NODE_DONE;
                *(long *)array_push(order) = top->node;
                trace("leave", (long)path.len - 1, node);
                array_pop(&path);
                continue;
            }
            long m = *(long *)array_at(&node->needs, top->next++);
            Node *next = graph_at(g, m);
            st.search_edges++;
            if (next->state == NODE_NEW) {
                enter(g, &path, m, top->node);
            } else if (next->state == NODE_DONE) {
                trace("again", (long)path.len, next);
            } else {
                /* open: m is on the path, so the path from m to here,
                 * and back to m, is a cycle */
                trace("cycle", (long)path.len, next);
                size_t k = path.len;
                while (((Frame *)array_at(&path, k - 1))->node != m)
                    k--;
                for (; k <= path.len; k++)
                    *(long *)array_push(cycle) = ((Frame *)array_at(&path, k - 1))->node;
                *(long *)array_push(cycle) = m;
                array_free(&path);
                return -1;
            }
        }
    }
    array_free(&path);
    return 0;
    // @end
}
