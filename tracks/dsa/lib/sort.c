/*
 * sort.c - sorting an array of pointers into the order a comparison gives.
 *
 * Every sort here takes the same arguments: the array v of n pointers, a
 * comparison cmp, and a ctx that cmp gets with each pair. They differ in
 * how many comparisons they make, and on which inputs:
 *
 *   sort_insertion    each item slides left past the larger ones before
 *                     it: about n*n/4 comparisons on input in no order,
 *                     n on input already in order
 *   sort_merge        sort each half, then merge the halves: about        @from 02.02
 *                     n*log2(n) comparisons on any input; stable           @from 02.02
 *   sort_quick_first  quicksort with the first item as the pivot: fast     @from 02.03
 *                     on input in no order, n*n/2 comparisons on input     @from 02.03
 *                     already in order, or all equal                       @from 02.03
 *   sort_quick        quicksort with a random pivot and a three-way        @from 02.03
 *                     split: no input makes it slow (but bad luck can)     @from 02.03
 *
 * A stable sort keeps items that compare equal in the order they came in.
 *
 * DS_STATS=1 prints "stats: sort: comparisons C, moves M": how many times
 * cmp was called, and how many pointers were written into an array.
 */
#include <stdlib.h>
#include <string.h>

#include "ds.h"

static struct {
    long comparisons, moves;
} st;

static void print_stats(void)
{
    ds_stats_print("sort", "comparisons %ld, moves %ld", st.comparisons, st.moves);
}

/* What the sorts below compare with: cmp and its ctx, and the count. */
typedef struct {
    Cmp cmp;
    void *ctx;
} Order;

static int compare(const Order *o, const void *a, const void *b)
{
    st.comparisons++;
    return o->cmp(a, b, o->ctx);
}

// @from 02.03
static void swap(void **v, size_t i, size_t j)
{
    void *t = v[i];
    v[i] = v[j];
    v[j] = t;
    st.moves += 2;
}
// @end

/* v[0..i) is in order; v[i] slides left past every item bigger than it.
 * Equal items never pass each other, so the sort is stable. */
void sort_insertion(void **v, size_t n, Cmp cmp, void *ctx)
{
    // @build 02.01 insertion sort
    Order o = {cmp, ctx};
    ds_stats_at_exit(print_stats);
    for (size_t i = 1; i < n; i++) {
        void *x = v[i];
        size_t j = i;
        while (j > 0 && compare(&o, v[j - 1], x) > 0) {
            v[j] = v[j - 1];
            st.moves++;
            j--;
        }
        v[j] = x;
        st.moves++;
    }
    // @end
}

/* Merge v[lo..mid) and v[mid..hi), each in order already, into v[lo..hi),
 * through aux. On a tie the left item goes first: that is what makes the
 * whole sort stable. */
static void merge(void **v, void **aux, size_t lo, size_t mid, size_t hi, const Order *o)
{
    // @build 02.02 merge two sorted halves
    memcpy(aux + lo, v + lo, (hi - lo) * sizeof *v);
    size_t i = lo, j = mid;
    for (size_t k = lo; k < hi; k++) {
        if (i == mid)
            v[k] = aux[j++];
        else if (j == hi)
            v[k] = aux[i++];
        else if (compare(o, aux[j], aux[i]) < 0)
            v[k] = aux[j++];
        else
            v[k] = aux[i++];
    }
    st.moves += (long)(hi - lo);
    // @end
}

static void merge_sort(void **v, void **aux, size_t lo, size_t hi, const Order *o)
{
    // @build 02.02 sort each half, then merge them
    if (hi - lo < 2)
        return;
    size_t mid = lo + (hi - lo) / 2;
    merge_sort(v, aux, lo, mid, o);
    merge_sort(v, aux, mid, hi, o);
    merge(v, aux, lo, mid, hi, o);
    // @end
}

/* Merge sort needs room for n more pointers while it merges. */
void sort_merge(void **v, size_t n, Cmp cmp, void *ctx)
{
    // @build 02.02 merge sort
    Order o = {cmp, ctx};
    ds_stats_at_exit(print_stats);
    void **aux = xmalloc(n * sizeof *aux);
    merge_sort(v, aux, 0, n, &o);
    free(aux);
    // @end
}

/* Quicksort picks one item, the pivot, and splits the rest around it:
 * smaller ones to its left, the others to its right. The pivot is then in
 * its final place, and each side is sorted the same way. It is fast when
 * the pivot lands near the middle. Each pass sorts the smaller side by
 * calling itself and goes round its loop for the larger one, so the calls
 * nest at most log2(n) deep, whatever the input: a bad input makes
 * quicksort slow, but never runs it out of stack.
 *
 * This one takes the first item as the pivot, and splits two ways:
 * v[lo+1..m] holds the items smaller than the pivot. On input already in
 * order the pivot is the smallest item every time, and each pass takes
 * just one item off. */
static void quick_first(void **v, size_t lo, size_t hi, const Order *o)
{
    // @build 02.03 quicksort, first item as the pivot
    while (hi - lo > 1) {
        void *pivot = v[lo];
        size_t m = lo;
        for (size_t i = lo + 1; i < hi; i++)
            if (compare(o, v[i], pivot) < 0)
                swap(v, ++m, i);
        swap(v, lo, m);
        if (m - lo < hi - m - 1) {
            quick_first(v, lo, m, o);
            lo = m + 1;
        } else {
            quick_first(v, m + 1, hi, o);
            hi = m;
        }
    }
    // @end
}

void sort_quick_first(void **v, size_t n, Cmp cmp, void *ctx)
{
    // @build 02.03 the obvious quicksort
    Order o = {cmp, ctx};
    ds_stats_at_exit(print_stats);
    quick_first(v, 0, n, &o);
    // @end
}

// @from 02.03
/* A number from 0 to n-1 (xorshift64*). The seed is fixed, so a run's
 * counts are the same every time it is run. */
static size_t below(uint64_t *seed, size_t n)
{
    uint64_t x = *seed;
    x ^= x >> 12;
    x ^= x << 25;
    x ^= x >> 27;
    *seed = x;
    return (size_t)((x * 2685821657736338717u) % n);
}
// @end

/* A random item as the pivot, and a three-way split (Dijkstra's): as the
 * scan goes, v[lo..lt) < pivot, v[lt..i) == pivot, v[gt..hi) > pivot.
 * The items equal to the pivot are done with: on input where every item is
 * the same, one pass finishes it. */
static void quick3(void **v, size_t lo, size_t hi, const Order *o, uint64_t *seed)
{
    // @build 02.03 quicksort, random pivot, three-way split
    while (hi - lo > 1) {
        swap(v, lo, lo + below(seed, hi - lo));
        void *pivot = v[lo];
        size_t lt = lo, i = lo + 1, gt = hi;
        while (i < gt) {
            int c = compare(o, v[i], pivot);
            if (c < 0)
                swap(v, lt++, i++);
            else if (c > 0)
                swap(v, i, --gt);
            else
                i++;
        }
        if (lt - lo < hi - gt) {
            quick3(v, lo, lt, o, seed);
            lo = gt;
        } else {
            quick3(v, gt, hi, o, seed);
            hi = lt;
        }
    }
    // @end
}

void sort_quick(void **v, size_t n, Cmp cmp, void *ctx)
{
    // @build 02.03 quicksort that no input can break
    Order o = {cmp, ctx};
    uint64_t seed = 0x9E3779B97F4A7C15u;
    ds_stats_at_exit(print_stats);
    quick3(v, 0, n, &o, &seed);
    // @end
}
