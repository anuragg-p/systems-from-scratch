/*
 * bloom.c - a Bloom filter: a set that answers "certainly not in it" or
 * "probably in it", in a few bits a key, and keeps no keys at all.
 *
 * The filter is m bits, all 0 to begin with. Adding a key sets k of them,
 * at places that k hash functions pick from the key. Asking about a key
 * looks at the same k places. If any of them is 0, the key was never
 * added: adding it would have set them all. If all k are 1, it probably
 * was, but they may all have been set by other keys: a false positive.
 *
 * With n keys added, a bit is still 0 with a chance of about e^(-kn/m),
 * so a key never added finds all k of its bits set with a chance of about
 *
 *   p = (1 - e^(-kn/m))^k
 *
 * which is smallest when k = (m/n) ln 2, half the bits set. Then p is
 * 0.6185^(m/n): 4.8 bits a key for 10%, 9.6 for 1%, 14.4 for 0.1%,
 * whatever the keys are and however long. bloom_init sizes the filter
 * the other way round, from the n and p wanted.
 *
 * The k places come from one 64-bit hash, FNV-1a (01.03), taken as two
 * halves h1 and h2: place i is (h1 + i * h2) mod m, with m a prime so
 * that the k places are k different bits. Kirsch and Mitzenmacher showed
 * that two hashes mixed this way do as well as k hashes of their own.
 *
 * What it cannot do: it holds no keys, so it cannot list them, say which
 * are near another, or say for sure that one is there. Nor can a key be
 * taken out (its bits may be other keys' too).
 *
 * DS_STATS=1 prints "stats: bloom: keys N, bits M, hashes K, bytes B,
 * bits set S, bits tested T, bits on O": the keys added, the size of the
 * filter in bits and in bytes, the bits each key sets, how many times a
 * bit was set by an add and looked at by a test (a test stops at the
 * first 0), and how many bits are 1 at the end.
 *
 * DS_TRACE=1 prints a line for each add and each test, on stderr:
 *   trace: bloom: add "cat": 2741 90233 4410 ...      the k bits it sets
 *   trace: bloom: test "cot": 77 on, 5016 off: no     the bits looked at
 *   trace: bloom: test "cat": 2741 on, ... on: yes
 */
#include <math.h>
#include <stdlib.h>
#include <string.h>

#include "bloom.h"

static struct {
    long set, tested;
} st;

static Bloom *counted;

static uint64_t bits_on(const Bloom *b)
{
    uint64_t on = 0;
    for (uint64_t i = 0; i < b->m; i++)
        on += (b->bits[i / 8] >> (i % 8)) & 1;
    return on;
}

static void print_stats(void)
{
    const Bloom *b = counted;
    ds_stats_print("bloom", "keys %zu, bits %llu, hashes %d, bytes %zu, bits set %ld, bits tested %ld, bits on %llu",
                   b ? b->n : 0, b ? (unsigned long long)b->m : 0ULL, b ? b->k : 0, b ? bloom_bytes(b) : 0,
                   st.set, st.tested, b ? (unsigned long long)bits_on(b) : 0ULL);
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

/* The first prime from m up. */
static uint64_t prime_from(uint64_t m)
{
    for (;; m++) {
        int prime = m >= 2;
        for (uint64_t d = 2; prime && d * d <= m; d++)
            prime = m % d != 0;
        if (prime)
            return m;
    }
}

/* m and k for n keys and a false-positive rate p, all bits 0. m is made
 * a prime, so that i * h2 mod m never comes round to the same place
 * before i reaches m: a key's k places are k different bits. */
void bloom_init(Bloom *b, size_t n, double p, int k)
{
    // @build 05.02 size the filter: m bits and k hashes for n keys and a rate p
    double ln2 = log(2.0);
    double m = ceil((double)(n ? n : 1) * -log(p) / (ln2 * ln2));
    b->m = prime_from((uint64_t)m);
    if (k <= 0) {
        k = (int)lround((double)b->m / (double)(n ? n : 1) * ln2);
        if (k < 1)
            k = 1;
    }
    b->k = k;
    b->n = 0;
    b->bits = xmalloc(bloom_bytes(b));
    memset(b->bits, 0, bloom_bytes(b));
    counted = b;
    ds_stats_at_exit(print_stats);
    // @end
}

/* The i-th of a key's k places: h1 and h2 are the two halves of its hash
 * (an h2 that is 0 mod m would put all k in one place: it is taken as 1). */
static uint64_t place(const Bloom *b, uint64_t h, int i)
{
    // @build 05.02 the i-th place: two halves of one hash, mixed
    uint64_t h1 = h & 0xffffffffu, h2 = (h >> 32) % b->m;
    if (h2 == 0)
        h2 = 1;
    return (h1 + (uint64_t)i * h2) % b->m;
    // @end
}

void bloom_add(Bloom *b, const void *key, size_t len)
{
    // @build 05.02 add: set the key's k bits
    uint64_t h = hash_fnv1a(key, len);
    if (tracing())
        fprintf(stderr, "trace: bloom: add \"%.*s\":", (int)len, (const char *)key);
    for (int i = 0; i < b->k; i++) {
        uint64_t at = place(b, h, i);
        b->bits[at / 8] |= (uint8_t)(1u << (at % 8));
        st.set++;
        if (tracing())
            fprintf(stderr, " %llu", (unsigned long long)at);
    }
    if (tracing())
        fputc('\n', stderr);
    b->n++;
    // @end
}

int bloom_test(Bloom *b, const void *key, size_t len)
{
    // @build 05.02 test: a key is out if any of its bits is 0
    uint64_t h = hash_fnv1a(key, len);
    if (tracing())
        fprintf(stderr, "trace: bloom: test \"%.*s\":", (int)len, (const char *)key);
    int yes = 1;
    for (int i = 0; i < b->k && yes; i++) {
        uint64_t at = place(b, h, i);
        yes = (b->bits[at / 8] >> (at % 8)) & 1;
        st.tested++;
        if (tracing())
            fprintf(stderr, "%s %llu %s", i ? "," : "", (unsigned long long)at, yes ? "on" : "off");
    }
    if (tracing())
        fprintf(stderr, ": %s\n", yes ? "yes" : "no");
    return yes;
    // @end
}

size_t bloom_bytes(const Bloom *b)
{
    return (size_t)((b->m + 7) / 8);
}

void bloom_free(Bloom *b)
{
    free(b->bits);
    b->bits = NULL;
    if (counted == b)
        counted = NULL;
}
