/*
 * array.c - a growable array.
 *
 * C's arrays have the size they were born with. This one starts empty and
 * takes one more element at a time, as many as come: the elements sit one
 * after another in a block with room to spare, and when the room runs out
 * they all move to a block twice as big. Moving everything sounds dear,
 * but each move buys as many cheap pushes as there were elements, so n
 * pushes copy fewer than n elements in all.
 *
 * DS_STATS=1 prints "stats: array: pushes P, grows G, moves M": how many
 * elements were added, how many times an array moved to a bigger block,
 * and how many elements those moves copied.
 */
#include <stdlib.h>
#include <string.h>

#include "ds.h"

static struct {
    long pushes, grows, moves;
} st;

static void print_stats(void)
{
    ds_stats_print("array", "pushes %ld, grows %ld, moves %ld", st.pushes, st.grows, st.moves);
}

/* An empty array of elements of size bytes. It takes no memory until the
 * first push. */
void array_init(Array *a, size_t size)
{
    // @build 01.01 an empty array
    a->data = NULL;
    a->len = 0;
    a->cap = 0;
    a->size = size;
    ds_stats_at_exit(print_stats);
    // @end
}

/* Room for one more element at the end, for the caller to fill in. A full
 * array first moves to a new block twice its size (8 elements to start
 * with): every element is copied across once, by hand rather than with
 * realloc(), so the copying can be seen and counted. */
void *array_push(Array *a)
{
    // @build 01.01 push, doubling when full
    if (a->len == a->cap) {
        size_t cap = a->cap ? 2 * a->cap : 8;
        char *data = xmalloc(cap * a->size);
        if (a->len > 0)
            memcpy(data, a->data, a->len * a->size);
        free(a->data);
        a->data = data;
        a->cap = cap;
        st.grows++;
        st.moves += (long)a->len;
    }
    st.pushes++;
    return a->data + a->len++ * a->size;
    // @end
}

/* Element i. An index past the end is a bug in the caller, and fatal. */
void *array_at(const Array *a, size_t i)
{
    if (i >= a->len)
        die("array: element %zu of %zu", i, a->len);
    return a->data + i * a->size;
}

void *array_pop(Array *a)
{
    if (a->len == 0)
        return NULL;
    a->len--;
    return a->data + a->len * a->size;
}

void array_clear(Array *a)
{
    a->len = 0;
}

void array_free(Array *a)
{
    free(a->data);
    a->data = NULL;
    a->len = a->cap = 0;
}
