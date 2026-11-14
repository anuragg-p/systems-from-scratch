/*
 * deflate.h - writing DEFLATE data (RFC 1951): bytes in, compressed bytes
 * out, which inflate_raw() (inflate.h), gunzip or zlib read back.
 *
 * Raw DEFLATE only, as inflate.h: the gzip or zlib wrapper is the caller's.
 *
 * DS_STATS=1 prints "stats: deflate: stored blocks S, fixed blocks F,
 * dynamic blocks D, bits out B": the blocks written of each kind, and the
 * bits they took.
 * DS_TRACE=1 prints each block as it is written, with what each form of
 * it would have cost and which was taken:
 *
 *   trace: deflate: block 1 (last): 11 bytes, 8 tokens: stored 128 bits, fixed 74 bits, dynamic 102 bits: fixed
 */
#ifndef DEFLATE_H
#define DEFLATE_H

#include "ds.h"
#include "lz77.h"

/* Which form each block takes: the smallest of the three (the default),
 * or always the one given. */
enum { DEFLATE_BEST, DEFLATE_STORED, DEFLATE_FIXED, DEFLATE_DYNAMIC };

typedef struct {
    int algo;       /* how LZ77 finds matches: LZ77_HASH, LZ77_SCAN or LZ77_NONE (lz77.h) */
    int chain;      /* LZ77_HASH: the most places to try for one match; 0 for no limit */
    int blocks;     /* DEFLATE_BEST, or the one form every block takes */
} DeflateOptions;

/* What deflate_raw() does with NULL options: gzip -6's. */
#define DEFLATE_DEFAULTS {LZ77_HASH, 128, DEFLATE_BEST}

/* Deflates in[0..n), appending the raw DEFLATE data to out, an Array of
 * bytes (array_init(out, 1)): whole bytes, the last block marked last.
 * opt may be NULL for the defaults; in may not be NULL, even when n is 0. */
void deflate_raw(const unsigned char *in, size_t n, const DeflateOptions *opt, Array *out);

#endif
