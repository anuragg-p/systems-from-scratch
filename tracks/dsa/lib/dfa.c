/*
 * dfa.c - a DFA built as it runs: each set of NFA states the text leads
 * to becomes one state, made the first time it is met.
 *
 * Running the NFA, every byte costs a walk over the list of live states
 * and the arrows out of them. But the list after a byte depends only on
 * the list before it and the byte, and the same lists come round again
 * and again: on ordinary text a pattern has a few dozen of them at most.
 * So each list is made into a state once, and a state remembers where
 * each byte took it. After the first few lines, almost every byte is one
 * lookup in a state's table.
 *
 * A DFA built all at once can need a state for every subset of the NFA's
 * states: (a|b)*a(a|b)(a|b)...(a|b), with k (a|b) after the a, needs 2^k
 * of them. Built as the text needs them, there are never more than the
 * bytes read; and when even that is too many, the cache is emptied and
 * the building starts again, so memory stays bounded. The price is time:
 * a text that needs a new state at most bytes pays for the NFA's step
 * and for building a state besides, several times what the NFA alone
 * costs. RE2 counts how often its cache fills, and goes back to running
 * the NFA when it fills too often; this DFA does not.
 */
#include <ctype.h>
#include <stdlib.h>
#include <string.h>

#include "ds.h"
#include "dfa.h"

static struct {
    long examined, hits, misses, built, flushes;
} st;

static void print_stats(void)
{
    ds_stats_print("dfa", "examined %ld, hits %ld, misses %ld, states built %ld, flushes %ld",
                   st.examined, st.hits, st.misses, st.built, st.flushes);
}

static int by_id(const void *a, const void *b)
{
    int x = *(const int *)a, y = *(const int *)b;
    return (x > y) - (x < y);
}

static DState *state(Dfa *d, int i)
{
    return array_at(&d->states, (size_t)i);
}

static void print_ids(const DState *s)
{
    fputc('{', stderr);
    for (int k = 0; k < s->len; k++)
        fprintf(stderr, k ? " %d" : "%d", s->ids[k]);
    fputc('}', stderr);
}

/* One line of DS_TRACE: from -1 is the start of a line. */
static void trace(size_t i, unsigned char c, int from, int to, const char *how, const DState *s)
{
    if (from < 0)
        fprintf(stderr, "trace: dfa: start: D%d (%s", to, how);
    else
        fprintf(stderr, "trace: dfa: at %zu '%c': D%d -> D%d (%s", i, isprint(c) ? c : '?', from, to, how);
    if (strcmp(how, "built") == 0) {
        fputs(": ", stderr);
        print_ids(s);
    }
    fputs(")\n", stderr);
}

void dfa_init(Dfa *d, Nfa *m, size_t max)
{
    d->nfa = m;
    array_init(&d->states, sizeof(DState));
    table_init(&d->cache);
    d->max = max ? max : 1;
    d->start = -1;
    nfa_list_init(m, &d->work);
    nfa_list_init(m, &d->end);
    ds_stats_at_exit(print_stats);
}

void dfa_free(Dfa *d)
{
    for (size_t i = 0; i < d->states.len; i++)
        free(state(d, (int)i)->ids);
    array_free(&d->states);
    table_free(&d->cache);
    free(d->work.ids);
    free(d->end.ids);
}

/* Would the line match if it ended with these NFA states live? Only if a
 * $ waiting among them leads, at the end, to the match state. */
static int matches_at_end(Dfa *d, const int *ids, int len)
{
    Nfa *m = d->nfa;
    nfa_clear(m, &d->end);
    for (int k = 0; k < len; k++)
        if (m->states[ids[k]].op == NFA_EOL)
            nfa_add(m, &d->end, ids[k], 0, 1);
    return d->end.match;
}

/* The cache is full: every state goes, and the building starts again
 * from nothing. The state a line starts in has to be built again too. */
static void flush(Dfa *d)
{
    // @build 04.04 a full cache: throw every state away
    if (re_tracing())
        fprintf(stderr, "trace: dfa: cache full at %zu states: all thrown away\n", d->states.len);
    for (size_t i = 0; i < d->states.len; i++)
        free(state(d, (int)i)->ids);
    array_clear(&d->states);
    table_free(&d->cache);
    table_init(&d->cache);
    d->start = -1;
    st.flushes++;
    // @end
}

/* The DFA state for the set of NFA states on l: the one the cache holds
 * for that set, or a new one, with no transitions worked out yet. The
 * set is sorted first, so the same states in another order are the same
 * key. */
static int state_for(Dfa *d, StateList *l)
{
    // @build 04.04 the DFA state for a set of NFA states: from the cache, or built
    qsort(l->ids, (size_t)l->len, sizeof *l->ids, by_id);
    size_t keylen = (size_t)l->len * sizeof *l->ids;
    long *have = table_get(&d->cache, l->ids, keylen);
    if (have != NULL)
        return (int)*have;
    if (d->states.len >= d->max)
        flush(d);
    DState *s = array_push(&d->states);
    s->ids = xmalloc(keylen ? keylen : 1);
    memcpy(s->ids, l->ids, keylen);
    s->len = l->len;
    for (int c = 0; c < 256; c++)
        s->next[c] = -1;
    s->match = (char)l->match;
    s->match_at_end = (char)(l->match || matches_at_end(d, s->ids, s->len));
    int i = (int)d->states.len - 1;
    *table_put(&d->cache, l->ids, keylen) = i;
    st.built++;
    return i;
    // @end
}

/* Where state from goes on byte c, worked out from the NFA as nfa_match
 * would: the states its NFA states lead to on c, and the start again,
 * since a match may begin at the next byte. Kept in from's table, unless
 * the cache was emptied meanwhile and from is gone. */
static int step(Dfa *d, int from, unsigned char c)
{
    // @build 04.04 a transition not worked out yet: from the NFA, then kept
    Nfa *m = d->nfa;
    DState *s = state(d, from);
    nfa_clear(m, &d->work);
    for (int k = 0; k < s->len; k++) {
        const NfaState *q = &m->states[s->ids[k]];
        if (q->op == NFA_CHAR && re_has(q->set, c))
            nfa_add(m, &d->work, q->out, 0, 0);
    }
    nfa_add(m, &d->work, m->start, 0, 0);
    long flushes = st.flushes;
    int to = state_for(d, &d->work);
    if (st.flushes == flushes)
        state(d, from)->next[c] = to;
    return to;
    // @end
}

int dfa_match(Dfa *d, const char *s, size_t n)
{
    // @build 04.04 run the DFA: a lookup a byte, building what is missing
    Nfa *m = d->nfa;
    const unsigned char *t = (const unsigned char *)s;
    if (n == 0) {                       /* both ^ and $ hold: not worth a state */
        nfa_clear(m, &d->work);
        nfa_add(m, &d->work, m->start, 1, 1);
        return d->work.match;
    }
    int tracing = re_tracing();
    const char *how = "hit";
    long built = st.built;
    if (d->start < 0) {
        nfa_clear(m, &d->work);
        nfa_add(m, &d->work, m->start, 1, 0);
        d->start = state_for(d, &d->work);
        how = st.built != built ? "built" : "found";
    }
    if (tracing)
        trace(0, 0, -1, d->start, how, state(d, d->start));
    int at = d->start;
    DState *states = (DState *)d->states.data;
    if (states[at].match)
        return 1;
    for (size_t i = 0; i < n; i++) {
        int to = states[at].next[t[i]];
        how = "hit";
        st.examined++;
        if (to >= 0) {
            st.hits++;
        } else {
            built = st.built;
            st.misses++;
            to = step(d, at, t[i]);
            states = (DState *)d->states.data;    /* building may have moved them */
            how = st.built != built ? "built" : "found";
        }
        if (tracing)
            trace(i, t[i], at, to, how, &states[to]);
        at = to;
        if (states[at].match)
            return 1;
        if (states[at].len == 0)              /* no NFA state live: nothing can match now */
            return 0;
    }
    return states[at].match_at_end;
    // @end
}
