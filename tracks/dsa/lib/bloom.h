/*
 * bloom.h - a Bloom filter (lib/bloom.c): a set that answers "certainly
 * not in it" or "probably in it", in a few bits a key, and keeps no keys.
 */
#ifndef BLOOM_H
#define BLOOM_H

#include "ds.h"

typedef struct {
    uint8_t *bits;       /* m bits, 8 to a byte */
    uint64_t m;
    int      k;          /* bits set for each key */
    size_t   n;          /* keys added */
} Bloom;

/* A filter sized for n keys with a false-positive rate of p (0 < p < 1):
 * m = n ln(1/p) / (ln 2)^2 bits (the first prime from there up), and
 * k = (m / n) ln 2 hashes, or k itself when k is more than 0. */
void   bloom_init(Bloom *b, size_t n, double p, int k);
void   bloom_add(Bloom *b, const void *key, size_t len);
int    bloom_test(Bloom *b, const void *key, size_t len);  /* 0: not in it; 1: probably in it */
size_t bloom_bytes(const Bloom *b);
void   bloom_free(Bloom *b);

#endif
