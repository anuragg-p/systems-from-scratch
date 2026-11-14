/*
 * trie.c - a trie: a set of words kept a letter at a time down a tree.
 *
 * Each node stands for the letters on the path from the root down to it,
 * and has a child for each letter that comes next in some word of the
 * set: "car", "cart" and "cat" share the nodes for "c" and "ca", and a
 * node is marked where a word ends. Looking a word up is one walk down, a
 * node a letter, however many words the trie holds. Every word that
 * starts with a prefix is in the subtree below the prefix's node, and
 * comes out in alphabetical order when the children are taken from a to z.
 *
 * The nodes live in one growable array (01.01), and a child is the index
 * of its node there, not a pointer: the array moves to a bigger block as
 * it grows, and an index into it stays good when it does. A node has room
 * for all 26 children, used or not, which makes a step down one array
 * access, and makes the trie big: see "bytes" below.
 *
 * DS_STATS=1 prints "stats: trie: words W, nodes N, bytes B, nodes visited
 * V": the different words added, the nodes they take (the root too), the
 * bytes of the block the nodes are in (room to spare included: what the
 * trie really holds on to), and how many nodes lookups, prefix walks and
 * suggestion walks stepped into. Adding words is not counted in V.
 *
 * DS_TRACE=1 prints a line on stderr for each step:
 *   trace: trie: add "cat": c -> 1 new          a step down while adding
 *   trace: trie: add "cat": t -> 3 new, a word  ... and where the word ends
 *   trace: trie: has "cab": b -> none           a step with no child there
 *   trace: trie: has "cab": no                  the answer
 *   trace: trie: find "ca": a -> 2              the walk down to a prefix
 *   trace: trie: each "cat" -> 3, a word        the walk below a node
 *   trace: trie: near "ca" -> 2: 2 1 1 2, min 1 the walk for suggestions:  @from 05.03
 *                                               the node's row of the table  @from 05.03
 *                                               (lib/edit.c), then ", a      @from 05.03
 *                                               word at D" or ", pruned"     @from 05.03
 */
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>

#include "trie.h"
#include "edit.h"      // @from 05.03

static struct {
    long visited;
} st;

static Trie *counted;          /* the trie whose sizes the stats line shows */

static void print_stats(void)
{
    size_t words = counted ? counted->words : 0, nodes = counted ? counted->nodes.len : 0;
    ds_stats_print("trie", "words %zu, nodes %zu, bytes %zu, nodes visited %ld",
                   words, nodes, counted ? trie_bytes(counted) : 0, st.visited);
}

static int tracing(void)
{
    static int on = -1;
    if (on < 0) {
        const char *s = getenv("DS_TRACE");
        on = s != NULL && *s != '\0' && strcmp(s, "0") != 0;
    }
    return on;
}

static void trace(const char *fmt, ...)
{
    va_list ap;
    fprintf(stderr, "trace: trie: ");
    va_start(ap, fmt);
    vfprintf(stderr, fmt, ap);
    va_end(ap);
    fputc('\n', stderr);
}

static TrieNode *node_at(const Trie *t, long i)
{
    return array_at(&t->nodes, (size_t)i);
}

/* 0 to 25 for a to z; -1 for anything else. */
static int letter(int c)
{
    return c >= 'a' && c <= 'z' ? c - 'a' : -1;
}

/* An empty trie: the root alone, which stands for the empty prefix. */
void trie_init(Trie *t)
{
    // @build 05.01 an empty trie: the root alone
    array_init(&t->nodes, sizeof(TrieNode));
    memset(array_push(&t->nodes), 0, sizeof(TrieNode));
    t->words = 0;
    counted = t;
    ds_stats_at_exit(print_stats);
    // @end
}

/* Adds w: down from the root a letter at a time, making each node that is
 * not there yet, and marks the last one as the end of a word. */
int trie_add(Trie *t, const char *w, size_t len)
{
    // @build 05.01 add a word: walk down, making the nodes that are missing
    for (size_t i = 0; i < len; i++)
        if (letter((unsigned char)w[i]) < 0)
            return -1;
    long node = 0;
    for (size_t i = 0; i < len; i++) {
        int c = letter((unsigned char)w[i]);
        int32_t next = node_at(t, node)->child[c];
        int made = next == 0;
        if (made) {
            next = (int32_t)t->nodes.len;
            memset(array_push(&t->nodes), 0, sizeof(TrieNode));  /* may move the nodes */
            node_at(t, node)->child[c] = next;
        }
        if (tracing())
            trace("add \"%.*s\": %c -> %ld%s%s", (int)len, w, w[i], (long)next, made ? " new" : "",
                  i + 1 == len ? ", a word" : "");
        node = next;
    }
    TrieNode *end = node_at(t, node);
    if (end->word)
        return 0;
    end->word = 1;
    t->words++;
    return 1;
    // @end
}

/* The node at the end of the path s spells, or -1 when the path stops
 * short: some letter has no child. op names the walk in the trace. */
static long descend(Trie *t, const char *s, size_t len, const char *op)
{
    // @build 05.01 walk down, a node a letter
    long node = 0;
    for (size_t i = 0; i < len; i++) {
        int c = letter((unsigned char)s[i]);
        int32_t next = c < 0 ? 0 : node_at(t, node)->child[c];
        if (next == 0) {
            if (tracing())
                trace("%s \"%.*s\": %c -> none", op, (int)len, s, s[i]);
            return -1;
        }
        st.visited++;
        if (tracing())
            trace("%s \"%.*s\": %c -> %ld", op, (int)len, s, s[i], (long)next);
        node = next;
    }
    return node;
    // @end
}

int trie_has(Trie *t, const char *w, size_t len)
{
    long node = descend(t, w, len, "has");
    int yes = node >= 0 && node_at(t, node)->word;
    if (tracing())
        trace("has \"%.*s\": %s", (int)len, w, yes ? "yes" : "no");
    return yes;
}

long trie_find(Trie *t, const char *prefix, size_t len)
{
    return descend(t, prefix, len, "find");
}

/* Below node: each child from a to z, its word (if one ends there) before
 * the words below it. path holds the letters from the root to node. */
static void walk(Trie *t, long node, Array *path, TrieFn fn, void *ctx)
{
    // @build 05.01 every word below a node: the children from a to z
    for (int c = 0; c < TRIE_LETTERS; c++) {
        int32_t next = node_at(t, node)->child[c];
        if (next == 0)
            continue;
        st.visited++;
        *(char *)array_push(path) = (char)('a' + c);
        int word = node_at(t, next)->word;
        if (tracing())
            trace("each \"%.*s\" -> %ld%s", (int)path->len, path->data, (long)next, word ? ", a word" : "");
        if (word)
            fn(path->data, path->len, ctx);
        walk(t, next, path, fn, ctx);
        path->len--;
    }
    // @end
}

void trie_each(Trie *t, long node, const char *prefix, size_t len, TrieFn fn, void *ctx)
{
    Array path;
    array_init(&path, 1);
    for (size_t i = 0; i < len; i++)
        *(char *)array_push(&path) = prefix[i];
    if (node_at(t, node)->word)
        fn(prefix, len, ctx);
    walk(t, node, &path, fn, ctx);
    array_free(&path);
}

size_t trie_bytes(const Trie *t)
{
    return t->nodes.cap * t->nodes.size;
}

void trie_free(Trie *t)
{
    array_free(&t->nodes);
    t->words = 0;
    if (counted == t)
        counted = NULL;
}

// @from 05.03
/* What one suggestion walk carries along. */
typedef struct {
    Trie       *t;
    const char *w;       /* the word to find neighbours of */
    size_t      len;
    int         maxd;
    TrieNearFn  fn;
    void       *ctx;
    Array       path;    /* char: the letters from the root to the node */
} Near;

static void trace_row(const Near *n, long node, const int *row, int min, const char *after)
{
    fprintf(stderr, "trace: trie: near \"%.*s\" -> %ld:", (int)n->path.len, n->path.data, node);
    for (size_t j = 0; j <= n->len; j++)
        fprintf(stderr, " %d", row[j]);
    fprintf(stderr, ", min %d%s\n", min, after);
}
// @end

/* Below node, whose row of the edit-distance table is prev: each child's
 * row comes from its parent's and one more letter. A child where a word
 * ends, with its row's last cell within maxd, is a suggestion. A child
 * whose row has no cell within maxd is left, with all below it: each cell
 * is the cell above it, to its left or above and left, plus 0 or 1, so
 * the smallest cell of a row is never smaller than the smallest of the
 * row above. Once none is within maxd, no row further down will be. */
static void near_walk(Near *n, long node, const int *prev)
{
    // @build 05.03 walk the trie carrying one row of the table; prune what cannot come back
    int *row = xmalloc((n->len + 1) * sizeof *row);
    for (int c = 0; c < TRIE_LETTERS; c++) {
        int32_t next = node_at(n->t, node)->child[c];
        if (next == 0)
            continue;
        st.visited++;
        edit_next_row(prev, row, n->w, n->len, 'a' + c);
        *(char *)array_push(&n->path) = (char)('a' + c);
        int min = row[0];
        for (size_t j = 1; j <= n->len; j++)
            if (row[j] < min)
                min = row[j];
        int word = node_at(n->t, next)->word && row[n->len] <= n->maxd;
        if (tracing()) {
            char after[40] = "";
            if (word)
                snprintf(after, sizeof after, ", a word at %d", row[n->len]);
            else if (min > n->maxd)
                snprintf(after, sizeof after, ", pruned");
            trace_row(n, next, row, min, after);
        }
        if (word)
            n->fn(n->path.data, n->path.len, row[n->len], n->ctx);
        if (min <= n->maxd)
            near_walk(n, next, row);
        n->path.len--;
    }
    free(row);
    // @end
}

void trie_near(Trie *t, const char *w, size_t len, int maxd, TrieNearFn fn, void *ctx)
{
    // @build 05.03 the root's row, then the walk
    Near n = {t, w, len, maxd, fn, ctx, {0}};
    array_init(&n.path, 1);
    int *row = xmalloc((len + 1) * sizeof *row);
    edit_first_row(row, len);
    near_walk(&n, 0, row);
    free(row);
    array_free(&n.path);
    // @end
}
