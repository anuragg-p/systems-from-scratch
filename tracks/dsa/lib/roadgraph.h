/*
 * roadgraph.h - a road map as a graph: junctions, and the roads between
 * them, with each junction's roads in one place (module 08, route).
 *
 * The map file (tools/route/gen.py says how one is made):
 *
 *   # comment lines, anywhere before the numbers
 *   credit TEXT          optional: what a picture of the map must say
 *   junctions N
 *   X Y                  N lines: junction 0, 1, ... at X metres east and
 *                        Y metres north of the map's south-west corner
 *   roads M
 *   A B METRES           M lines: a road between junctions A and B, both
 *                        ways, and its length in whole metres
 *
 * In memory the roads are kept twice. Once as the file lists them (road r
 * joins road_a[r] and road_b[r]), and once as adjacency lists in three
 * compact arrays: every road is two arcs, one out of each of its ends, and
 * the arcs out of junction j are arcs first[j] up to first[j+1], all side
 * by side. Arc a goes to to[a] and is len[a] metres long. Finding the
 * roads at a junction is then one look-up, not a read of every road.
 */
#ifndef ROADGRAPH_H
#define ROADGRAPH_H

typedef struct {
    int    n;          /* junctions, numbered 0 to n-1 */
    long   m;          /* roads */
    int   *x, *y;      /* where junction j is, in metres */
    int   *road_a, *road_b, *road_len;   /* road r: its two ends, its metres */
    long  *first;      /* n+1 of them: junction j's arcs are first[j] .. first[j+1]-1 */
    int   *to;         /* 2m arcs: where arc a goes */
    int   *len;        /* and how many metres it is */
    char  *credit;     /* the map's credit line, or NULL */
} RoadGraph;

/* Read the map at path into g. A file that cannot be read, or is not a map,
 * is fatal, with the line that is wrong. */
void roadgraph_load(RoadGraph *g, const char *path);
void roadgraph_free(RoadGraph *g);

#endif
