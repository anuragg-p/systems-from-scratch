/*
 * nfa.c - a regular expression as a machine, run in every state at once.
 *
 * Thompson's construction (1968) makes a state for each byte to read and
 * a split for each choice, with arrows between them: a? is a split to a
 * and past it, a* a split to a and past it with an arrow from a back to
 * the split. The machine is nondeterministic: at a split it is in both
 * places at once.
 *
 * The backtracker followed one way at a time and came back for the
 * others. This keeps every way it could be at once, as a list of states:
 * read a byte, and the list after it is every state an arrow from a live
 * state leads to on that byte. The list never holds a state twice, so it
 * is never longer than the machine, and each byte of the line is read
 * once: a?^n a^n against a^n takes n bytes and about n*n state moves, not
 * 2^n tries.
 */
#include <ctype.h>
#include <stdlib.h>
#include <string.h>

#include "ds.h"
#include "nfa.h"

static struct {
    long states, examined, live, peak;
} st;

static void print_stats(void)
{
    ds_stats_print("nfa", "states %ld, examined %ld, live %ld, peak %ld", st.states, st.examined, st.live, st.peak);
}

static int by_id(const void *a, const void *b)
{
    int x = *(const int *)a, y = *(const int *)b;
    return (x > y) - (x < y);
}

/* "{1 3 4}": the states on l, smallest first, for a trace. */
static void print_list(const StateList *l)
{
    int *ids = xmalloc((size_t)(l->len ? l->len : 1) * sizeof *ids);
    memcpy(ids, l->ids, (size_t)l->len * sizeof *ids);
    qsort(ids, (size_t)l->len, sizeof *ids, by_id);
    fputc('{', stderr);
    for (int k = 0; k < l->len; k++)
        fprintf(stderr, k ? " %d" : "%d", ids[k]);
    fputs("}\n", stderr);
    free(ids);
}

/* The machine, a state a line, for a trace. */
static void print_machine(const Nfa *m)
{
    for (int id = 0; id < m->nstates; id++) {
        const NfaState *s = &m->states[id];
        fprintf(stderr, "trace: nfa: state %d: ", id);
        if (s->op == NFA_SPLIT)
            fprintf(stderr, "split -> %d, %d\n", s->out, s->out1);
        else if (s->op == NFA_MATCH)
            fprintf(stderr, "match\n");
        else
            fprintf(stderr, "%.*s -> %d\n", s->srclen, s->src, s->out);
    }
    fprintf(stderr, "trace: nfa: start %d\n", m->start);
}

/* How many states the machine for re has: one for each byte, anchor and
 * choice (a split), none for a sequence or for nothing. */
static int size(const Re *re)
{
    switch (re->op) {
    case RE_CHAR:
    case RE_BOL:
    case RE_EOL:
        return 1;
    case RE_EMPTY:
        return 0;
    case RE_CAT:
        return size(re->left) + size(re->right);
    case RE_ALT:
        return 1 + size(re->left) + size(re->right);
    case RE_STAR:
    case RE_PLUS:
    case RE_QUEST:
        return 1 + size(re->left);
    }
    return 0;
}

static void set(Nfa *m, int id, NfaOp op, int out, int out1, const Re *re)
{
    NfaState *s = &m->states[id];
    s->op = op;
    s->out = out;
    s->out1 = out1;
    s->set = re->set;
    s->src = re->src;
    s->srclen = re->srclen;
}

/* The states for re, numbered from base in the order the pattern is
 * written, with every way out of them leading to next: the state to
 * start re in. A sequence is built back to front, so each part knows
 * where it leads; a loop's split is made first, so its body can lead back
 * to it. */
static int build(Nfa *m, const Re *re, int base, int next)
{
    // @build 04.03 Thompson's construction: a node as states, leading to next
    switch (re->op) {
    case RE_CHAR:
        set(m, base, NFA_CHAR, next, -1, re);
        return base;
    case RE_BOL:
        set(m, base, NFA_BOL, next, -1, re);
        return base;
    case RE_EOL:
        set(m, base, NFA_EOL, next, -1, re);
        return base;
    case RE_EMPTY:
        return next;
    case RE_CAT: {
        int right = build(m, re->right, base + size(re->left), next);
        return build(m, re->left, base, right);
    }
    case RE_ALT: {
        int left = build(m, re->left, base + 1, next);
        int right = build(m, re->right, base + 1 + size(re->left), next);
        set(m, base, NFA_SPLIT, left, right, re);
        return base;
    }
    case RE_QUEST:
        set(m, base, NFA_SPLIT, build(m, re->left, base + 1, next), next, re);
        return base;
    case RE_STAR:
        set(m, base, NFA_SPLIT, build(m, re->left, base + 1, base), next, re);
        return base;
    case RE_PLUS: {
        int split = base + size(re->left);
        int body = build(m, re->left, base, split);
        set(m, split, NFA_SPLIT, body, next, re);
        return body;
    }
    }
    return next;
    // @end
}

void nfa_list_init(const Nfa *m, StateList *l)
{
    l->ids = xmalloc((size_t)m->nstates * sizeof *l->ids);
    l->len = 0;
    l->match = 0;
}

/* Empty l, and start a new round of marks: no state is on it. */
void nfa_clear(Nfa *m, StateList *l)
{
    l->len = 0;
    l->match = 0;
    if (++m->gen == 0) {
        memset(m->mark, 0, (size_t)m->nstates * sizeof *m->mark);
        m->gen = 1;
    }
}

void nfa_compile(Nfa *m, const Re *re)
{
    // @build 04.03 the machine for a whole pattern, and a match state at its end
    int n = size(re);
    m->nstates = n + 1;
    m->states = xmalloc((size_t)m->nstates * sizeof *m->states);
    m->states[n] = (NfaState){NFA_MATCH, -1, -1, NULL, "", 0};
    m->start = build(m, re, 0, n);
    m->mark = xmalloc((size_t)m->nstates * sizeof *m->mark);
    memset(m->mark, 0, (size_t)m->nstates * sizeof *m->mark);
    m->gen = 0;
    nfa_list_init(m, &m->a);
    nfa_list_init(m, &m->b);
    st.states += m->nstates;
    ds_stats_at_exit(print_stats);
    if (re_tracing())
        print_machine(m);
    // @end
}

void nfa_free(Nfa *m)
{
    free(m->states);
    free(m->mark);
    free(m->a.ids);
    free(m->b.ids);
}

/* Put state id on l, unless it is there already, and follow every arrow
 * out of it that reads nothing: both of a split's, a ^'s at the start of
 * the line, a $'s at the end. A split or a ^ is followed, never kept; a $
 * not at the end is kept, as the end may come later. */
void nfa_add(Nfa *m, StateList *l, int id, int bol, int eol)
{
    // @build 04.03 a state onto the list, with every state it leads to without reading
    if (m->mark[id] == m->gen)
        return;
    m->mark[id] = m->gen;
    const NfaState *s = &m->states[id];
    switch (s->op) {
    case NFA_SPLIT:
        nfa_add(m, l, s->out, bol, eol);
        nfa_add(m, l, s->out1, bol, eol);
        return;
    case NFA_BOL:
        if (bol)
            nfa_add(m, l, s->out, bol, eol);
        return;
    case NFA_EOL:
        if (eol) {
            nfa_add(m, l, s->out, bol, eol);
            return;
        }
        break;
    case NFA_MATCH:
        l->match = 1;
        break;
    case NFA_CHAR:
        break;
    }
    l->ids[l->len++] = id;
    // @end
}

int nfa_match(Nfa *m, const char *s, size_t n)
{
    // @build 04.03 run the machine: every live state at once, a byte at a time
    const unsigned char *t = (const unsigned char *)s;
    int tracing = re_tracing();
    StateList *now = &m->a, *next = &m->b;
    nfa_clear(m, now);
    nfa_add(m, now, m->start, 1, n == 0);
    for (size_t i = 0;; i++) {
        st.live += now->len;
        if (now->len > st.peak)
            st.peak = now->len;
        if (tracing) {
            if (i == 0)
                fprintf(stderr, "trace: nfa: start: ");
            else
                fprintf(stderr, "trace: nfa: at %zu '%c': ", i - 1, isprint(t[i - 1]) ? t[i - 1] : '?');
            print_list(now);
        }
        if (now->match)
            return 1;
        if (i == n || now->len == 0)    /* the end, or no state live: no match can come */
            return 0;
        st.examined++;
        nfa_clear(m, next);
        for (int k = 0; k < now->len; k++) {
            const NfaState *q = &m->states[now->ids[k]];
            if (q->op == NFA_CHAR && re_has(q->set, t[i]))
                nfa_add(m, next, q->out, 0, i + 1 == n);
        }
        /* a match may start at the next byte as well */
        nfa_add(m, next, m->start, 0, i + 1 == n);
        StateList *x = now;
        now = next;
        next = x;
    }
    // @end
}
