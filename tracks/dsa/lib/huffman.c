/*
 * huffman.c - Huffman codes: short codes for common symbols, long ones for
 * rare symbols, and no code the start of another, so a reader always knows
 * where one ends.
 *
 * A prefix code is a binary tree: each symbol a leaf, its code the path
 * from the root, 0 for left and 1 for right, so its length is the leaf's
 * depth. Huffman's algorithm (1952) builds the best such tree from the
 * bottom up. Every symbol starts as a tree of one node, weighed by its
 * count. Take the two lightest trees, join them under a new node that
 * weighs their sum, and put that back; when one tree is left, it is the
 * code. The heap of module 02 does the picking: the lightest tree is
 * always on top.
 *
 * Why the two rarest: in some best code the two rarest symbols are the two
 * deepest leaves, side by side (a commoner symbol down there could swap
 * places with a rarer one higher up, and the total could only fall). Join
 * them and they act as one symbol, a level up, whose count is their sum;
 * every code for that smaller alphabet costs exactly that sum less than
 * the same code with the two split again. So the best code for the smaller
 * alphabet gives the best for this one, and the greedy choice is never
 * wrong.
 *
 * DEFLATE stores only each symbol's code length. huff_codes() turns the
 * lengths back into codes by numbering them in order, the canonical code,
 * which the writer and the reader of a file both build the same way.
 */
#include <stdlib.h>
#include <string.h>

#include "huffman.h"

static struct {
    long trees, joins, rebuilds;
} st;

static void print_stats(void)
{
    ds_stats_print("huffman", "trees %ld, joins %ld, rebuilds %ld", st.trees, st.joins, st.rebuilds);
}

/* DS_TRACE: set to anything but 0, print each step. */
static int tracing(void)
{
    static int on = -1;
    if (on < 0) {
        const char *s = getenv("DS_TRACE");
        on = s != NULL && *s != '\0' && strcmp(s, "0") != 0;
    }
    return on;
}

/* A node of the tree: a symbol (a leaf), or the join of two trees. */
typedef struct {
    long count;      /* the symbol's count, or the sum of the two below */
    int  order;      /* the symbol for a leaf; n + k for the k-th join */
    int  parent;     /* the node above, as an index into the nodes, or -1 */
} Node;

/* Which of two nodes is lighter: the smaller count; on equal counts the
 * leaf of the smaller symbol, then the join made first, so the tree is
 * the same on every machine. A Cmp, for the heap. */
static int lighter(const void *a, const void *b, void *ctx)
{
    const Node *x = a, *y = b;
    if (x->count != y->count)
        return x->count < y->count ? -1 : 1;
    return x->order < y->order ? -1 : x->order > y->order;
}

/* A node's name in the trace: 'c' or a number for a symbol, nK for a join. */
static const char *name(const Node *x, int n, char *buf, size_t size)
{
    if (x->order >= n)
        snprintf(buf, size, "n%d", x->order - n + 1);
    else if (x->order >= 32 && x->order < 127 && x->order != '\'' && x->order != '\\')
        snprintf(buf, size, "'%c'", x->order);
    else
        snprintf(buf, size, "%d", x->order);
    return buf;
}

int huff_lengths(const long *counts, int n, unsigned char *lengths)
{
    // @build 09.01 the tree: join the two rarest until one is left; a code's length is its depth
    Node *node = xmalloc(2 * (size_t)n * sizeof *node);
    int *depth = xmalloc(2 * (size_t)n * sizeof *depth);
    Heap h;
    ds_stats_at_exit(print_stats);
    heap_init(&h, lighter, NULL);
    st.trees++;
    for (int s = 0; s < n; s++) {
        node[s].count = counts[s];
        node[s].order = s;
        node[s].parent = -1;
        if (counts[s] > 0)
            heap_push(&h, &node[s]);
    }
    if (tracing())
        fprintf(stderr, "trace: huffman: tree of %zu symbols\n", heap_len(&h));
    int used = (int)heap_len(&h), top = n;
    while (heap_len(&h) > 1) {
        Node *a = heap_pop(&h), *b = heap_pop(&h), *j = &node[top];
        j->count = a->count + b->count;
        j->order = top;
        j->parent = -1;
        a->parent = b->parent = top;
        if (tracing()) {
            char x[16], y[16], z[16];
            fprintf(stderr, "trace: huffman: join %s %ld + %s %ld = %s %ld\n", name(a, n, x, sizeof x),
                    a->count, name(b, n, y, sizeof y), b->count, name(j, n, z, sizeof z), j->count);
        }
        heap_push(&h, j);
        top++;
        st.joins++;
    }
    heap_free(&h);
    /* Each join is made after the two below it, so walking back from the
     * last one (the root) reaches every parent before its children. */
    int longest = 0;
    for (int i = top - 1; i >= 0; i--)
        depth[i] = node[i].parent < 0 ? 0 : depth[node[i].parent] + 1;
    for (int s = 0; s < n; s++) {
        lengths[s] = counts[s] > 0 ? (unsigned char)(used == 1 ? 1 : depth[s]) : 0;
        if (lengths[s] > longest)
            longest = lengths[s];
    }
    free(node);
    free(depth);
    return longest;
    // @end
}

int huff_lengths_limited(const long *counts, int n, int maxbits, unsigned char *lengths)
{
    // @build 09.04 no code longer than maxbits: flatten the counts until the tree is shallow enough
    long *c = xmalloc((size_t)n * sizeof *c);
    memcpy(c, counts, (size_t)n * sizeof *c);
    int longest;
    while ((longest = huff_lengths(c, n, lengths)) > maxbits) {
        /* Halving every count keeps the symbols in the same order, but the
         * rare ones come closer to the common ones, so the tree is less
         * lopsided. Once every count is 1 the tree is balanced. */
        int all_one = 1;
        for (int s = 0; s < n; s++) {
            if (c[s] > 1)
                all_one = 0;
            if (c[s] > 0)
                c[s] = (c[s] + 1) / 2;
        }
        if (all_one)
            die("huffman: no code of %d bits or fewer for %d symbols", maxbits, n);
        st.rebuilds++;
    }
    free(c);
    return longest;
    // @end
}

void huff_codes(const unsigned char *lengths, int n, unsigned *codes)
{
    // @build 09.01 canonical codes: count the codes of each length, then number them in order
    long count[HUFF_MAX_CODE + 1] = {0};
    unsigned long long next[HUFF_MAX_CODE + 1];
    for (int s = 0; s < n; s++) {
        if (lengths[s] > HUFF_MAX_CODE)
            die("huffman: a code of %d bits, longer than %d", lengths[s], HUFF_MAX_CODE);
        count[lengths[s]]++;
    }
    /* The first code of each length: one past the last code of the length
     * before, with a 0 put after it. */
    unsigned long long code = 0;
    count[0] = 0;
    for (int len = 1; len <= HUFF_MAX_CODE; len++) {
        code = (code + (unsigned long long)count[len - 1]) << 1;
        next[len] = code;
    }
    for (int s = 0; s < n; s++)
        codes[s] = lengths[s] ? (unsigned)next[lengths[s]]++ : 0;
    // @end
}
