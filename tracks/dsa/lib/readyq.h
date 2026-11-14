/*
 * readyq.h - a queue of ready work: first in, first out (module 07).
 *
 * make -j puts a target on it once everything the target needs is
 * finished, and takes targets off the front to run them.
 *
 * DS_STATS=1 prints "stats: readyq: pushes P, pops Q, longest L": items
 * put on, items taken off, and the most it ever held at once.
 */
#ifndef READYQ_H
#define READYQ_H

#include "ds.h"

/* The items are in an Array, oldest first from head: a push goes on the
 * end, a pop takes the one at head and moves head along. */
typedef struct {
    Array  items;        /* long */
    size_t head;         /* the index in items of the front of the queue */
} ReadyQueue;

void   readyq_init(ReadyQueue *q);
void   readyq_push(ReadyQueue *q, long item);
long   readyq_pop(ReadyQueue *q);           /* the oldest item, taken off; -1 if empty */
size_t readyq_len(const ReadyQueue *q);
void   readyq_free(ReadyQueue *q);

#endif
