/*
 * readyq.c - a queue of ready work: first in, first out.
 *
 * Items go on at the end of an array and come off at the front, which is
 * an index that moves along as they do. Nothing is ever moved, so a push
 * and a pop each cost the same however long the queue is. The room before
 * the front is not used again: make puts each target on the queue once,
 * so the array never holds more than there are targets. (A queue that
 * took items for ever would wrap round to the start of its room: a ring.)
 */
#include "readyq.h"

static struct {
    long pushes, pops, longest;
} st;

static void print_stats(void)
{
    ds_stats_print("readyq", "pushes %ld, pops %ld, longest %ld", st.pushes, st.pops, st.longest);
}

/* An empty queue. */
void readyq_init(ReadyQueue *q)
{
    // @build 07.04 an empty queue
    array_init(&q->items, sizeof(long));
    q->head = 0;
    ds_stats_at_exit(print_stats);
    // @end
}

/* item goes on the end. */
void readyq_push(ReadyQueue *q, long item)
{
    // @build 07.04 push: on at the end
    *(long *)array_push(&q->items) = item;
    st.pushes++;
    if ((long)readyq_len(q) > st.longest)
        st.longest = (long)readyq_len(q);
    // @end
}

/* The item at the front, taken off; -1 if there is none. */
long readyq_pop(ReadyQueue *q)
{
    // @build 07.04 pop: off at the front
    if (q->head == q->items.len)
        return -1;
    st.pops++;
    return *(long *)array_at(&q->items, q->head++);
    // @end
}

size_t readyq_len(const ReadyQueue *q)
{
    return q->items.len - q->head;
}

void readyq_free(ReadyQueue *q)
{
    array_free(&q->items);
    q->head = 0;
}
