/*
 * dfa.h - the NFA's sets of states, each made once into one state of a
 * deterministic machine, as the text needs it (lesson 04.04).
 *
 * A DFA state stands for one set of NFA states, and has a table of where
 * it goes on each byte, filled in the first time that byte comes. Once
 * the text has been through a state and a byte, the next time costs one
 * lookup. The states are found by their set in a hash table (01.02); at
 * most a fixed number are kept, and when that many are built and another
 * is needed, all of them are thrown away and the building starts again.
 *
 * DS_STATS=1 prints "stats: dfa: examined E, hits H, misses M, states
 * built B, flushes F": the bytes of text read; the transitions found in a
 * state's table, and those that were not and had to be worked out from
 * the NFA; the states built; and the times the cache was full and was
 * emptied. Its hash table prints its own "stats: table:" line.
 *
 * DS_TRACE=1 prints, at the start of each line and for each byte:
 *   trace: dfa: start: D0 (built: {0 3})
 *   trace: dfa: start: D0 (hit)
 *   trace: dfa: at I 'c': D0 -> D0 (hit)
 *   trace: dfa: at I 'c': D0 -> D1 (built: {1 3})
 *   trace: dfa: at I 'c': D1 -> D0 (found)
 * hit: the table had it; built: a new state, its NFA states listed;
 * found: worked out, and the cache had that set already. And when the
 * cache is full:
 *   trace: dfa: cache full at N states: all thrown away
 */
#ifndef DFA_H
#define DFA_H

#include <stddef.h>

#include "ds.h"
#include "nfa.h"

typedef struct {
    int *ids;            /* the NFA states it stands for, smallest first */
    int len;
    int next[256];       /* the state after each byte, or -1: not worked out yet */
    char match;          /* the match state is one of them: the line matches */
    char match_at_end;   /* the line matches if it ends in this state */
} DState;

typedef struct {
    Nfa *nfa;
    Array states;        /* DState, by number */
    Table cache;         /* a set of NFA states, as bytes -> the number of its DState */
    size_t max;          /* the most states kept at once */
    int start;           /* the state a line starts in, or -1: not built */
    StateList work, end; /* room to work out a set of NFA states */
} Dfa;

/* A DFA for the NFA m (which must outlive it), keeping at most max states. */
void dfa_init(Dfa *d, Nfa *m, size_t max);
void dfa_free(Dfa *d);

/* Is the pattern found anywhere in the line s[0..n)? */
int dfa_match(Dfa *d, const char *s, size_t n);

#endif
