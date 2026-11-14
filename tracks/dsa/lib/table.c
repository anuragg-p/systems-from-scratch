/*
 * table.c - a hash table: from a key (any bytes) to a long, found in about
 * the same time whether the table holds a thousand keys or a million.
 *
 * A hash function turns the key into a number, and the number picks one
 * of nbuckets buckets; only the keys in that bucket are looked at. Each
 * bucket is a list of entries (separate chaining). The entries themselves
 * live in one growable array, in the order they were added, and a bucket
 * is the index of its first entry, each entry holding the index of the
 * next: no allocation per bucket, and a walk over every key is a walk down
 * the array.
 *
 * Keeping each bucket short takes a hash that spreads keys evenly    @from 01.03
 * over the buckets, and more buckets as more keys come in.           @from 01.03
 *                                                                    @from 01.03
 * DS_STATS=1 prints "stats: table: lookups L, probes P, inserts I, resizes
 * R, moves M": how many times a key was looked for, how many entries
 * those lookups compared it with, how many keys were added, how many
 * times the buckets doubled, and how many entries moved to a new bucket
 * then.
 */
#include <stdlib.h>
#include <string.h>

#include "ds.h"

static struct {
    long lookups, probes, inserts, resizes, moves;
} st;

static void print_stats(void)
{
    ds_stats_print("table", "lookups %ld, probes %ld, inserts %ld, resizes %ld, moves %ld",
                   st.lookups, st.probes, st.inserts, st.resizes, st.moves);
}

/* The first hash anyone writes: add up the bytes. Anagrams ("stop",
 * "pots", "tops") all get the same number, and words of English add up to
 * a few thousand at most, however many buckets there are. */
uint64_t hash_sum(const void *key, size_t len)
{
    // @build 01.02 the first hash: add up the bytes
    const unsigned char *p = key;
    uint64_t h = 0;
    for (size_t i = 0; i < len; i++)
        h += p[i];
    return h;
    // @end
}

/* FNV-1a (Fowler, Noll and Vo): for each byte, mix it into the low bits
 * with xor, then multiply by a large prime, which carries every bit of it
 * up into the high bits. Every byte changes every bit of the result, so
 * keys that differ a little land far apart. */
uint64_t hash_fnv1a(const void *key, size_t len)
{
    // @build 01.03 FNV-1a: every byte stirs every bit
    const unsigned char *p = key;
    uint64_t h = 14695981039346656037u;    /* the FNV offset basis */
    for (size_t i = 0; i < len; i++) {
        h ^= p[i];
        h *= 1099511628211u;                /* the FNV prime */
    }
    return h;
    // @end
}

static long *new_buckets(size_t n)
{
    long *b = xmalloc(n * sizeof *b);
    for (size_t i = 0; i < n; i++)
        b[i] = -1;
    return b;
}

/* An empty table with 1024 empty buckets. */
void table_init(Table *t)
{
    // @build 01.02 an empty table
    array_init(&t->entries, sizeof(Entry));
    t->nbuckets = 1024;
    t->buckets = new_buckets(t->nbuckets);
    // @from 01.03
    t->hash = hash_fnv1a;
    t->no_grow = 0;
    // @else
    // t->hash = hash_sum;
    // @end
    ds_stats_at_exit(print_stats);
    // @end
}

/* The entry holding key, or -1. Only the key's bucket is walked, and an
 * entry's bytes are compared only when its whole hash matches. The bucket
 * is the hash's low bits: nbuckets is a power of two. */
static long find(Table *t, const void *key, size_t len, uint64_t h)
{
    // @build 01.02 find: walk the key's bucket
    st.lookups++;
    long i = t->buckets[h & (t->nbuckets - 1)];
    while (i >= 0) {
        Entry *e = array_at(&t->entries, (size_t)i);
        st.probes++;
        if (e->hash == h && e->len == len && memcmp(e->key, key, len) == 0)
            return i;
        i = e->next;
    }
    return -1;
    // @end
}

/* Twice the buckets, with every entry linked into its new bucket. The
 * entries stay where they are in the array; only the bucket heads and the
 * next links are rebuilt, from the hash each entry kept. */
static void grow(Table *t)
{
    // @build 01.03 resize: twice the buckets
    free(t->buckets);
    t->nbuckets *= 2;
    t->buckets = new_buckets(t->nbuckets);
    for (size_t i = 0; i < t->entries.len; i++) {
        Entry *e = array_at(&t->entries, i);
        size_t b = e->hash & (t->nbuckets - 1);
        e->next = t->buckets[b];
        t->buckets[b] = (long)i;
    }
    st.resizes++;
    st.moves += (long)t->entries.len;
    // @end
}

long *table_get(Table *t, const void *key, size_t len)
{
    // @build 01.02 get
    long i = find(t, key, len, t->hash(key, len));
    if (i < 0)
        return NULL;
    return &((Entry *)array_at(&t->entries, (size_t)i))->value;
    // @end
}

/* The value of key, which is added first, with the value 0, if it is not
 * there. A new entry goes at the head of its bucket's list.
 * Once there are as many entries as buckets, the buckets double first,   @from 01.03
 * so a bucket holds about one entry on average, however many there are.  @from 01.03
 */
long *table_put(Table *t, const void *key, size_t len)
{
    // @build 01.02 put: a new key goes at the head of its bucket
    uint64_t h = t->hash(key, len);
    long i = find(t, key, len, h);
    if (i >= 0)
        return &((Entry *)array_at(&t->entries, (size_t)i))->value;
    // @from 01.03
    if (!t->no_grow && t->entries.len >= t->nbuckets)
        grow(t);
    // @end
    size_t b = h & (t->nbuckets - 1);
    Entry *e = array_push(&t->entries);
    e->key = xstrndup(key, len);
    e->len = len;
    e->hash = h;
    e->value = 0;
    e->next = t->buckets[b];
    t->buckets[b] = (long)(t->entries.len - 1);
    st.inserts++;
    return &e->value;
    // @end
}

size_t table_len(const Table *t)
{
    return t->entries.len;
}

Entry *table_entry(const Table *t, size_t i)
{
    return array_at(&t->entries, i);
}

void table_free(Table *t)
{
    for (size_t i = 0; i < t->entries.len; i++)
        free(((Entry *)array_at(&t->entries, i))->key);
    array_free(&t->entries);
    free(t->buckets);
    t->buckets = NULL;
    t->nbuckets = 0;
}
