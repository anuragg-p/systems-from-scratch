/*
 * ds.h - the library every tool of this track is built on.
 *
 *   util.c    errors, memory, input files, and the counters DS_STATS=1 prints
 *   array.c   a growable array                                      @from 01.01
 *   table.c   a hash table                                          @from 01.02
 *   sort.c    sorting an array of pointers: insertion sort          @from 02.01
 *             merge sort                                            @from 02.02
 *             quicksort                                             @from 02.03
 *   heap.c    a binary heap, and heapsort                           @from 02.04
 *
 * Every structure counts its own work. Run any tool with DS_STATS=1 in its
 * environment and it prints, on stderr as it exits, one line for each
 * structure it used: "stats: <structure>: <count> <n>, <count> <n>, ...".
 */
#ifndef DS_H
#define DS_H

#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

/* ------------------------------------------------------------ util.c */

/* The tool's name, for its messages: each main() sets it first. */
extern const char *progname;

/* Print "progname: message" on stderr and exit with status 2, as sort and
 * grep do for trouble. */
_Noreturn void die(const char *fmt, ...);

/* malloc that never returns NULL: running out of memory is fatal. */
void *xmalloc(size_t n);

/* A NUL-terminated copy of the n bytes at s. */
char *xstrndup(const char *s, size_t n);

/* The file at path opened for reading, or standard input for "-" or NULL.
 * A file that cannot be opened is fatal. */
FILE *open_input(const char *path);
void close_input(FILE *f);

/* DS_STATS: ds_stats_on() says whether it is set (to anything but 0).
 * ds_stats_at_exit(print) has print() called once as the program exits,
 * if it is; each structure registers its own printer the first time it is
 * used, so the lines come out in that order. A printer writes its line
 * with ds_stats_print("table", "lookups %ld, probes %ld", ...). */
int ds_stats_on(void);
void ds_stats_at_exit(void (*print)(void));
void ds_stats_print(const char *name, const char *fmt, ...);

// @internal
/* What a cut-out lesson leaves in place of its code: prints
 * "progname: NN.LL: <what> not written yet" and exits with status 3. */
_Noreturn void ds_todo(const char *lesson, const char *what);
// @end

// @from 01.01
/* ------------------------------------------------------------ array.c */

/* A growable array: len elements of size bytes each, one after another at
 * data, with room for cap of them before it has to move to a bigger block.
 * A pointer into data is good until the next push: a push may move it. */
typedef struct {
    char  *data;
    size_t len;
    size_t cap;
    size_t size;
} Array;

void   array_init(Array *a, size_t size);
void  *array_push(Array *a);                /* room for one more at the end */
void  *array_at(const Array *a, size_t i);  /* element i, which must exist */
void  *array_pop(Array *a);                 /* the last element, taken off; NULL if empty */
void   array_clear(Array *a);               /* empty it, keeping the room */
void   array_free(Array *a);
// @end

// @from 01.02
/* ------------------------------------------------------------ table.c */

/* One key and its value. The table keeps its own copy of the key, with a
 * NUL after it, and the key's hash, so it never has to hash a key twice. */
typedef struct {
    char    *key;
    size_t   len;
    uint64_t hash;
    long     value;
    long     next;       /* the next entry in the same bucket, or -1 */
} Entry;

typedef uint64_t (*HashFn)(const void *key, size_t len);

/* A hash table from byte strings to longs: the entries in an Array, in the
 * order they were added, and nbuckets lists of them, linked through next. */
typedef struct {
    Array   entries;     /* Entry */
    long   *buckets;     /* the first entry of each bucket, or -1 */
    size_t  nbuckets;    /* a power of two */
    HashFn  hash;
    int     no_grow;     /* keep nbuckets as it starts (freq --no-grow) */   // @from 01.03
} Table;

void    table_init(Table *t);
long   *table_get(Table *t, const void *key, size_t len);  /* its value, or NULL */
long   *table_put(Table *t, const void *key, size_t len);  /* its value; a new key's is 0 */
size_t  table_len(const Table *t);
Entry  *table_entry(const Table *t, size_t i);             /* the i-th key added */
void    table_free(Table *t);

/* The pointer table_get and table_put return is good until the next put. */

uint64_t hash_sum(const void *key, size_t len);
uint64_t hash_fnv1a(const void *key, size_t len);   // @from 01.03
// @end

// @from 02.01
/* ------------------------------------------------------------ sort.c */

/* How two items compare: less than 0, 0 or more than 0, as strcmp says it.
 * The sorts call it with the items themselves (the pointers in the array)
 * and pass ctx through untouched. */
typedef int (*Cmp)(const void *a, const void *b, void *ctx);

/* Each sorts the n pointers at v into the order cmp gives, smallest first. */
void sort_insertion(void **v, size_t n, Cmp cmp, void *ctx);
void sort_merge(void **v, size_t n, Cmp cmp, void *ctx);         // @from 02.02
void sort_quick_first(void **v, size_t n, Cmp cmp, void *ctx);   // @from 02.03
void sort_quick(void **v, size_t n, Cmp cmp, void *ctx);         // @from 02.03
// @end

// @from 02.04
/* ------------------------------------------------------------ heap.c */

/* A binary min-heap of pointers: the smallest item, as cmp orders them, is
 * always on top. The items live in an Array; the children of the item at
 * i are at 2i+1 and 2i+2, and neither is smaller than it. */
typedef struct {
    Array items;         /* void * */
    Cmp   cmp;
    void *ctx;
} Heap;

void   heap_init(Heap *h, Cmp cmp, void *ctx);
void   heap_push(Heap *h, void *item);
void  *heap_pop(Heap *h);                  /* the smallest, taken off; NULL if empty */
void  *heap_top(const Heap *h);            /* the smallest, left in place; NULL if empty */
size_t heap_len(const Heap *h);
void   heap_free(Heap *h);

/* Heapsort: sorts v as the sorts in sort.c do, in place, with the heap's
 * own sifting. */
void heap_sort(void **v, size_t n, Cmp cmp, void *ctx);
// @end

#endif
