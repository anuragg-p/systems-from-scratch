/*
 * heap.c - a binary heap: the smallest item always on top, a new item in
 * and the top item out in log2(n) steps each.
 *
 * The heap is a binary tree kept in an array, level by level: the item at
 * i has its children at 2i+1 and 2i+2 and its parent at (i-1)/2, so the
 * tree needs no pointers at all. The one rule is that no item is smaller
 * than its parent; so the smallest of all is at the root, v[0], and
 * nothing else about the order is promised. A push puts the new item at
 * the end and sifts it up, swapping it with its parent while it is the
 * smaller; a pop takes the root, puts the last item there and sifts it
 * down, swapping it with its smaller child while that is smaller. Each
 * walks one path between the root and the bottom: log2(n) levels.
 *
 * heap_sort uses the same sifting to sort an array in place: arrange it
 * as a heap with the largest item on top, then swap the top to the end
 * and sift down what took its place, n times.
 *
 * DS_STATS=1 prints "stats: heap: pushes P, pops Q, comparisons C, moves
 * M": items in and out, calls to cmp, and pointers written.
 */
#include <stdlib.h>

#include "ds.h"

static struct {
    long pushes, pops, comparisons, moves;
} st;

static void print_stats(void)
{
    ds_stats_print("heap", "pushes %ld, pops %ld, comparisons %ld, moves %ld",
                   st.pushes, st.pops, st.comparisons, st.moves);
}

/* Is a above b in a heap whose top is the smallest (dir 1) or the largest
 * (dir -1)? */
static int above(const void *a, const void *b, Cmp cmp, void *ctx, int dir)
{
    st.comparisons++;
    return dir * cmp(a, b, ctx) < 0;
}

/* Move the item at i up while it belongs above its parent. */
static void sift_up(void **v, size_t i, Cmp cmp, void *ctx, int dir)
{
    // @build 02.04 sift up
    void *x = v[i];
    while (i > 0) {
        size_t parent = (i - 1) / 2;
        if (!above(x, v[parent], cmp, ctx, dir))
            break;
        v[i] = v[parent];
        st.moves++;
        i = parent;
    }
    v[i] = x;
    st.moves++;
    // @end
}

/* Move the item at i down, among v[0..n), while a child belongs above it:
 * the child that belongs higher of the two takes its place. */
static void sift_down(void **v, size_t n, size_t i, Cmp cmp, void *ctx, int dir)
{
    // @build 02.04 sift down
    void *x = v[i];
    for (;;) {
        size_t child = 2 * i + 1;
        if (child >= n)
            break;
        if (child + 1 < n && above(v[child + 1], v[child], cmp, ctx, dir))
            child++;
        if (!above(v[child], x, cmp, ctx, dir))
            break;
        v[i] = v[child];
        st.moves++;
        i = child;
    }
    v[i] = x;
    st.moves++;
    // @end
}

void heap_init(Heap *h, Cmp cmp, void *ctx)
{
    array_init(&h->items, sizeof(void *));
    h->cmp = cmp;
    h->ctx = ctx;
    ds_stats_at_exit(print_stats);
}

void heap_push(Heap *h, void *item)
{
    // @build 02.04 push: at the end, then up
    *(void **)array_push(&h->items) = item;
    sift_up((void **)h->items.data, h->items.len - 1, h->cmp, h->ctx, 1);
    st.pushes++;
    // @end
}

void *heap_pop(Heap *h)
{
    // @build 02.04 pop: the top out, the last item down from the top
    if (h->items.len == 0)
        return NULL;
    void **v = (void **)h->items.data;
    void *top = v[0];
    void *last = *(void **)array_pop(&h->items);
    if (h->items.len > 0) {
        v[0] = last;
        sift_down(v, h->items.len, 0, h->cmp, h->ctx, 1);
    }
    st.pops++;
    return top;
    // @end
}

void *heap_top(const Heap *h)
{
    return h->items.len ? *(void **)h->items.data : NULL;
}

size_t heap_len(const Heap *h)
{
    return h->items.len;
}

void heap_free(Heap *h)
{
    array_free(&h->items);
}

void heap_sort(void **v, size_t n, Cmp cmp, void *ctx)
{
    // @build 02.04 heapsort: a heap with the largest on top, emptied from the end
    ds_stats_at_exit(print_stats);
    for (size_t i = n / 2; i-- > 0;)
        sift_down(v, n, i, cmp, ctx, -1);
    for (size_t end = n; end > 1; end--) {
        void *top = v[0];
        v[0] = v[end - 1];
        v[end - 1] = top;
        st.moves += 2;
        sift_down(v, end - 1, 0, cmp, ctx, -1);
    }
    // @end
}
