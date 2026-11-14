/*
 * re.c - a regular expression parsed into a tree, and matched by
 * backtracking.
 *
 * The parser reads the pattern once, left to right, a function for each
 * level of precedence, loosest first: alternatives (r|s), sequences (rs),
 * repetitions (r* r+ r?), and atoms (a byte, ., [...], ^, $, (r)). Each
 * returns the tree of what it read, so "ab|c*" comes out as
 * ALT(CAT(a, b), STAR(c)).
 *
 * The backtracking matcher walks that tree along the line. At a choice
 * (r|s, r?, a loop) it takes the first way, and if what comes after fails,
 * it goes back and takes the other. It is what most languages' regex
 * libraries do, and it is short. But every choice can double the ways to
 * try: n optional letters, a?a?...a? followed by aa...a, against n a's,
 * tries about 2^n of them before it finds the one that works.
 */
#include <ctype.h>
#include <stdlib.h>
#include <string.h>

#include "ds.h"
#include "re.h"

static struct {
    long nodes;
} st;

static struct {
    long steps, examined, deepest;
} bst;

static void print_stats(void)
{
    ds_stats_print("regex", "nodes %ld", st.nodes);
}

static void print_bt_stats(void)
{
    ds_stats_print("backtrack", "steps %ld, examined %ld, deepest %ld", bst.steps, bst.examined, bst.deepest);
}

int re_tracing(void)
{
    static int on = -1;
    if (on < 0) {
        const char *s = getenv("DS_TRACE");
        on = s != NULL && *s != '\0' && strcmp(s, "0") != 0;
    }
    return on;
}

/* ------------------------------------------------------------ the parser */

static const char *p, *pend;   /* where the parser is in the pattern, and its end */
static int icase;
static int depth;              /* how many ( are open */

static void add(unsigned char *set, int c)
{
    set[c >> 3] |= (unsigned char)(1 << (c & 7));
}

/* With -i: a letter in the set brings its other case in too. */
static void fold(unsigned char *set)
{
    for (int c = 'a'; c <= 'z'; c++)
        if (re_has(set, (unsigned char)c) || re_has(set, (unsigned char)toupper(c))) {
            add(set, c);
            add(set, toupper(c));
        }
}

/* A new node, made from the pattern between from and where the parser is. */
static Re *node(ReOp op, Re *left, Re *right, const char *from)
{
    Re *n = xmalloc(sizeof *n);
    memset(n, 0, sizeof *n);
    n->op = op;
    n->left = left;
    n->right = right;
    n->src = from;
    n->srclen = (int)(p - from);
    st.nodes++;
    return n;
}

static const struct {
    const char *name;
    int (*is)(int);
} classes[] = {
    {"alpha", isalpha}, {"digit", isdigit}, {"alnum", isalnum}, {"upper", isupper},
    {"lower", islower}, {"space", isspace}, {"blank", isblank}, {"punct", ispunct},
    {"print", isprint}, {"graph", isgraph}, {"cntrl", iscntrl}, {"xdigit", isxdigit},
};

/* [:name:]: every byte of that class (in the C locale) into set. */
static void add_class(unsigned char *set, const char *name, size_t len)
{
    for (size_t k = 0; k < sizeof classes / sizeof classes[0]; k++)
        if (strlen(classes[k].name) == len && memcmp(classes[k].name, name, len) == 0) {
            for (int c = 0; c < 256; c++)
                if (classes[k].is(c))
                    add(set, c);
            return;
        }
    die("no class [:%.*s:]", (int)len, name);
}

/* The bytes of a bracket expression, the parser just past its [. A ]
 * first, or after the ^, is one of the bytes; so is a - first or last. */
static void parse_class(unsigned char *set)
{
    // @build 04.02 a bracket expression: the bytes between [ and ]
    int negate = 0;
    memset(set, 0, 32);
    if (p < pend && *p == '^') {
        negate = 1;
        p++;
    }
    for (int first = 1;; first = 0) {
        if (p == pend)
            die("'[' with no ']' after it");
        unsigned char lo = (unsigned char)*p++;
        if (lo == ']' && !first)
            break;
        if (lo == '[' && p < pend && (*p == ':' || *p == '.' || *p == '=')) {
            char kind = *p++;
            const char *name = p;
            while (p + 1 < pend && !(p[0] == kind && p[1] == ']'))
                p++;
            if (p + 1 >= pend)
                die("'[%c' with no '%c]' after it", kind, kind);
            size_t len = (size_t)(p - name);
            p += 2;
            if (kind != ':')
                die("[%c %c] is not supported", kind, kind);
            add_class(set, name, len);
            continue;
        }
        unsigned char hi = lo;
        if (p + 1 < pend && p[0] == '-' && p[1] != ']') {
            hi = (unsigned char)p[1];
            p += 2;
            if (hi < lo)
                die("the range %c-%c goes backwards", lo, hi);
        }
        for (int c = lo; c <= hi; c++)
            add(set, c);
    }
    if (icase)
        fold(set);
    if (negate) {
        for (int i = 0; i < 32; i++)
            set[i] = (unsigned char)~set[i];
        set['\n' >> 3] &= (unsigned char)~(1 << ('\n' & 7));
    }
    // @end
}

static Re *parse_alt(void);

/* An atom: one byte (a literal, an escaped one, ., or [...]), an anchor,
 * or a whole expression in parentheses. */
static Re *parse_atom(void)
{
    // @build 04.02 an atom: a byte, ., [...], ^, $, or (...)
    const char *from = p;
    unsigned char c = (unsigned char)*p++;
    Re *r;
    switch (c) {
    case '(':
        depth++;
        r = parse_alt();
        if (p == pend)
            die("'(' with no ')' after it");
        p++;
        depth--;
        r->src = from;
        r->srclen = (int)(p - from);
        return r;
    case '^':
        return node(RE_BOL, NULL, NULL, from);
    case '$':
        return node(RE_EOL, NULL, NULL, from);
    case '.':
        r = node(RE_CHAR, NULL, NULL, from);
        memset(r->set, 0xff, sizeof r->set);
        r->set['\n' >> 3] &= (unsigned char)~(1 << ('\n' & 7));
        return r;
    case '[': {
        unsigned char set[32];
        parse_class(set);
        r = node(RE_CHAR, NULL, NULL, from);
        memcpy(r->set, set, sizeof set);
        return r;
    }
    case '*':
    case '+':
    case '?':
        die("'%c' with nothing before it to repeat", c);
    case '{':
        if (p < pend && (isdigit((unsigned char)*p) || *p == ','))
            die("intervals such as {2,3} are not supported");
        break;
    case '\\':
        if (p == pend)
            die("a \\ at the end of the pattern");
        c = (unsigned char)*p++;
        if (isalnum(c))
            die("'\\%c' is not supported", c);
        break;
    }
    r = node(RE_CHAR, NULL, NULL, from);
    add(r->set, c);
    if (icase)
        fold(r->set);
    return r;
    // @end
}

/* An atom and the * + ? after it, each applying to all before it: a+?
 * is (a+)?. An anchor cannot be repeated. */
static Re *parse_repeat(void)
{
    // @build 04.02 a repetition: an atom, and any * + ? after it
    const char *from = p;
    Re *r = parse_atom();
    while (p < pend && (*p == '*' || *p == '+' || *p == '?')) {
        if (r->op == RE_BOL || r->op == RE_EOL)
            die("'%c' after '%c': an anchor cannot be repeated", *p, *from);
        ReOp op = *p == '*' ? RE_STAR : *p == '+' ? RE_PLUS : RE_QUEST;
        p++;
        r = node(op, r, NULL, from);
    }
    return r;
    // @end
}

/* A sequence: repetitions one after another, up to a |, the ) that closes
 * the group it is in, or the end. An empty one matches nothing, at once. */
static Re *parse_cat(void)
{
    // @build 04.02 a sequence: one repetition after another
    const char *from = p;
    Re *seq = NULL;
    while (p < pend && *p != '|' && !(*p == ')' && depth > 0)) {
        Re *r = parse_repeat();
        seq = seq ? node(RE_CAT, seq, r, from) : r;
    }
    return seq ? seq : node(RE_EMPTY, NULL, NULL, from);
    // @end
}

/* Alternatives: sequences between |. */
static Re *parse_alt(void)
{
    // @build 04.02 alternatives: sequences between |
    const char *from = p;
    Re *alt = parse_cat();
    while (p < pend && *p == '|') {
        p++;
        Re *r = parse_cat();
        alt = node(RE_ALT, alt, r, from);
    }
    return alt;
    // @end
}

Re *re_parse(const char *pattern, size_t len, int fold_case)
{
    // @build 04.02 parse a whole pattern
    p = pattern;
    pend = pattern + len;
    icase = fold_case;
    depth = 0;
    ds_stats_at_exit(print_stats);
    return parse_alt();
    // @end
}

void re_free(Re *re)
{
    if (re == NULL)
        return;
    re_free(re->left);
    re_free(re->right);
    free(re);
}

/* ------------------------------------------------------------ backtracking */

/* How deep the matcher may go: each byte a loop takes is a few calls
 * deeper, and the stack is only so big. Past this, an ordinary error. */
#define MAX_DEPTH 10000

/* What is left to match, after the node in hand: a list, the next node
 * first. It lives on the matcher's own stack, so going back is just
 * returning. An entry for a loop (a * or +) that has just gone round
 * once more holds where that time round began: one that matched nothing
 * is not gone round again, or (a*)* would loop for ever. */
enum { PLAIN, AGAIN, FIRST };

typedef struct Next {
    const Re *re;
    const struct Next *next;
    size_t from;
    int loop;                 /* PLAIN, or AGAIN, or FIRST: the first time round a + */
} Next;

static const unsigned char *text;
static size_t tlen;
static long calls;            /* how deep the matcher is now */

static int bt(const Re *re, const Next *k, size_t i);
static int go_on(const Next *k, size_t i);

static void back(const Re *re, size_t i)
{
    if (re_tracing())
        fprintf(stderr, "trace: backtrack: back at %zu: %.*s, the other way\n", i, re->srclen, re->src);
}

/* A * or + has matched up to i: go round once more, and if what follows
 * fails, stop going round and go on from i. */
static int loop(const Re *re, const Next *k, size_t i)
{
    // @build 04.02 a loop: once more round, or stop
    Next again = {re, k, i, AGAIN};
    if (bt(re->left, &again, i))
        return 1;
    back(re, i);
    return go_on(k, i);
    // @end
}

/* Go on from i with what is left, k. Nothing left: a match. */
static int go_on(const Next *k, size_t i)
{
    // @build 04.02 go on with what is left
    if (k == NULL)
        return 1;
    if (k->loop == PLAIN)
        return bt(k->re, k->next, i);
    if (i == k->from)            /* that time round matched nothing */
        return k->loop == FIRST ? go_on(k->next, i) : 0;
    return loop(k->re, k->next, i);
    // @end
}

/* Match re at i, then what is left, k: 1 if both can be done. */
static int bt(const Re *re, const Next *k, size_t i)
{
    // @build 04.02 match a node, then what is left; at a choice, one way then the other
    int ok = 0;
    bst.steps++;
    if (++calls > bst.deepest) {
        bst.deepest = calls;
        if (calls > MAX_DEPTH)
            die("the backtracking matcher is %d calls deep, on a line of %zu bytes: "
                "more than its stack can hold (--algo=nfa needs no stack)", MAX_DEPTH, tlen);
    }
    switch (re->op) {
    case RE_CHAR:
        if (i < tlen) {
            int yes = re_has(re->set, text[i]);
            bst.examined++;
            if (re_tracing())
                fprintf(stderr, "trace: backtrack: at %zu: '%c' against %.*s: %s\n", i,
                        isprint(text[i]) ? text[i] : '?', re->srclen, re->src, yes ? "yes" : "no");
            ok = yes && go_on(k, i + 1);
        } else if (re_tracing()) {
            fprintf(stderr, "trace: backtrack: at %zu: the end against %.*s: no\n", i, re->srclen, re->src);
        }
        break;
    case RE_BOL:
        ok = i == 0 && go_on(k, i);
        break;
    case RE_EOL:
        ok = i == tlen && go_on(k, i);
        break;
    case RE_EMPTY:
        ok = go_on(k, i);
        break;
    case RE_CAT: {
        Next rest = {re->right, k, 0, PLAIN};
        ok = bt(re->left, &rest, i);
        break;
    }
    case RE_ALT:
        ok = bt(re->left, k, i);
        if (!ok) {
            back(re, i);
            ok = bt(re->right, k, i);
        }
        break;
    case RE_QUEST:
        ok = bt(re->left, k, i);
        if (!ok) {
            back(re, i);
            ok = go_on(k, i);
        }
        break;
    case RE_STAR:
        ok = loop(re, k, i);
        break;
    case RE_PLUS: {
        Next first = {re, k, i, FIRST};
        ok = bt(re->left, &first, i);
        break;
    }
    }
    calls--;
    return ok;
    // @end
}

int re_backtrack(const Re *re, const char *s, size_t n)
{
    // @build 04.02 try a match from each start in turn
    text = (const unsigned char *)s;
    tlen = n;
    ds_stats_at_exit(print_bt_stats);
    for (size_t start = 0; start <= n; start++) {
        if (re_tracing())
            fprintf(stderr, "trace: backtrack: start at %zu\n", start);
        if (bt(re, NULL, start))
            return 1;
    }
    return 0;
    // @end
}
