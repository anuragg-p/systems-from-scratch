/*
 * depgraph.h - a dependency graph: things with names, and for each thing
 * the things it needs, in the order they were given. make's targets are
 * its nodes and their prerequisites its edges (module 07).
 *
 *   graph_init, graph_node, graph_edge    build the graph
 *   graph_walk     the obvious walk: every path to a node, each time
 *   graph_search   depth-first search: each node once, and any cycle      @from 07.02
 *
 * DS_STATS=1 prints "stats: depgraph: nodes N, edges E, walk visits W,
 * walk edges X, search visits V, search edges F": the nodes and edges
 * added; how many times the walk came to a node, and the edges it went
 * along to get there; and the same for the search.
 * DS_TRACE=1 prints each step of a walk or a search on stderr, one line
 * each, as "trace: EVENT DEPTH NAME":
 *   walk    the walk came to the node, DEPTH edges below where it started
 *   enter   the search came to a new node: it is open (on the path)       @from 07.02
 *   leave   the search has finished everything the node needs: done      @from 07.02
 *   again   the search met a node that was done already, and went on     @from 07.02
 *   cycle   the search met a node that is still open: a cycle            @from 07.02
 */
#ifndef DEPGRAPH_H
#define DEPGRAPH_H

#include "ds.h"

// @from 07.02
/* Where a depth-first search stands with a node: not reached yet, open
 * (on the path from where the search started down to where it is now), or
 * done (it and everything it needs, finished). */
enum { NODE_NEW, NODE_OPEN, NODE_DONE };
// @end

typedef struct {
    char  *name;
    Array  needs;        /* long: the nodes this one needs, each once, in order */
    Array  needed_by;    /* long: the nodes that need this one */            // @from 07.04
    int    state;        /* NODE_NEW, NODE_OPEN or NODE_DONE */              // @from 07.02
    long   from;         /* the node the search reached it from; -1 */       // @from 07.02
    long   waiting;      /* what it needs that is not finished yet */        // @from 07.04
    void  *data;         /* the tool's own: make hangs its rule here */
} Node;

typedef struct {
    Array nodes;         /* Node, in the order they were added; a node is its index */
    Table index;         /* a name -> the index of its node */
} Graph;

void   graph_init(Graph *g);
long   graph_node(Graph *g, const char *name);    /* the node called name, added if new */
long   graph_find(Graph *g, const char *name);    /* the node called name, or -1 */
void   graph_edge(Graph *g, long from, long to);  /* from needs to; a second time is ignored */
Node  *graph_at(const Graph *g, long i);
size_t graph_len(const Graph *g);

/* The obvious walk from root: walk each node it needs, in order, then
 * call visit(g, node, from, ctx), from being the node the walk came from
 * (-1 for root). Nothing is remembered between paths, so a node that can
 * be reached by k paths is walked, and visited, k times. Returns 0, or -1
 * if the walk went deeper than there are nodes, which only a cycle can
 * make it do. */
typedef void (*Visit)(Graph *g, long node, long from, void *ctx);
int graph_walk(Graph *g, long root, Visit visit, void *ctx);

// @from 07.02
/* Depth-first search from each of roots in turn: every node they need,
 * each entered once. Each node goes on the end of order (an Array of
 * long) as the search finishes with it. Returns 0; or -1 when it meets a
 * cycle, with the nodes that form it in cycle (an Array of long, the
 * first node again at the end: each needs the next).
 * A node is finished only after everything it needs, so in order every    @from 07.03
 * node comes after all the nodes it needs: a topological order.            @from 07.03
 */
int graph_search(Graph *g, const long *roots, size_t nroots, Array *order, Array *cycle);
// @end

#endif
