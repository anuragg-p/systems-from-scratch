/*
 * nfa.h - a regular expression as a machine (lesson 04.03): Thompson's
 * construction turns the tree into states joined by arrows, and the
 * machine is run on a line in every state it could be in at once.
 *
 * DS_STATS=1 prints "stats: nfa: states N, examined E, live L, peak P":
 * the machine's states, the bytes of text read, the states live summed
 * over every byte read (the work), and the most live at once.
 *
 * DS_TRACE=1 prints the machine as it is built, a state a line:
 *   trace: nfa: state 3: R -> 4         (reads a byte R matches, then 4)
 *   trace: nfa: state 2: split -> 3, 5  (goes on to both, reading nothing)
 *   trace: nfa: state 6: ^ -> 7         (or $: only at the start, or the end)
 *   trace: nfa: state 8: match
 *   trace: nfa: start 0
 * and, as it runs, the states live before the first byte and after each:
 *   trace: nfa: start: {0 3}
 *   trace: nfa: at I 'c': {1 3 4}
 * Only states that read a byte, the match state, and a $ waiting for the
 * end of the line are listed: the splits are followed, never kept.
 */
#ifndef NFA_H
#define NFA_H

#include <stddef.h>

#include "re.h"

typedef enum {
    NFA_CHAR,     /* read one byte of set, then go to out */
    NFA_SPLIT,    /* go to out and to out1, reading nothing */
    NFA_BOL,      /* at the start of the line: go to out */
    NFA_EOL,      /* at the end of the line: go to out */
    NFA_MATCH     /* the pattern has been matched */
} NfaOp;

typedef struct {
    NfaOp op;
    int out, out1;
    const unsigned char *set;   /* NFA_CHAR: the bytes it reads (in the tree) */
    const char *src;            /* the part of the pattern it was made from */
    int srclen;
} NfaState;

/* A set of states, as a list in the order they were added. */
typedef struct {
    int *ids;
    int len;
    int match;                  /* NFA_MATCH is on it */
} StateList;

typedef struct {
    NfaState *states;
    int nstates;
    int start;
    unsigned *mark;             /* mark[s] == gen: s is on the list being built */
    unsigned gen;
    StateList a, b;             /* the simulation's lists: now, and after the next byte */
} Nfa;

/* The machine for re (which must outlive it). */
void nfa_compile(Nfa *m, const Re *re);
void nfa_free(Nfa *m);

/* Is the machine's pattern found anywhere in the line s[0..n)? */
int nfa_match(Nfa *m, const char *s, size_t n);

/* For dfa.c: an empty list, room for every state; and state id onto list
 * l, with every state it leads to without reading a byte (^ only if bol,
 * $ only if eol), each once. */
void nfa_list_init(const Nfa *m, StateList *l);
void nfa_clear(Nfa *m, StateList *l);
void nfa_add(Nfa *m, StateList *l, int id, int bol, int eol);

#endif
