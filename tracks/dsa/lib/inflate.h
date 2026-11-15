/*
 * inflate.h - reading DEFLATE data (RFC 1951): compressed bytes in, the
 * bytes they stand for out.
 *
 * Raw DEFLATE only. A gzip file (RFC 1952, tools/gzip/gz.c) wraps it in a
 * header and a CRC-32; a zlib stream (RFC 1950, git's objects) in two
 * bytes of header and an Adler-32. The wrapper is the caller's.
 *
 * DS_STATS=1 prints "stats: inflate: stored blocks S, fixed blocks F,
 * dynamic blocks D, symbols N, table lookups T, bits walked W": the blocks
 * of each kind read, the Huffman-coded symbols decoded, how many of those
 * were looked up in a table, and how many bits were read one at a time.
 * DS_TRACE=1 prints each block and each literal and match as it is read;
 * for abracadabra in a dynamic block:
 *
 *   trace: inflate: block 1: dynamic (last), header 130 bits, 259 literal/length codes (longest 3 bits), 6 distance codes (longest 1 bits)
 *   trace: inflate: 0: literal "a"
 *   ...
 *   trace: inflate: 7: match distance 7 length 4 "abra"
 *   trace: inflate: end of block 1: 159 bits, 11 bytes
 *
 * where 0 and 7 are where in the output the bytes go. A stored block says
 * "stored", a block in the fixed codes "fixed".
 */
#ifndef INFLATE_H
#define INFLATE_H

#include "ds.h"

/* Inflates the raw DEFLATE data at in[0..n), appending the bytes it stands
 * for to out, an Array of bytes (array_init(out, 1)). Returns NULL, and in
 * *used the number of bytes of in the data took (whatever follows them, a
 * gzip trailer or a zlib checksum, is the caller's); or, for data that is
 * damaged or cut short, a message saying what is wrong (good until the
 * next call), with out holding whatever came before the damage. Never
 * reads outside in[0..n), whatever the bytes are. */
const char *inflate_raw(const unsigned char *in, size_t n, Array *out, size_t *used);

/* How a Huffman code is read: with a table for the short codes (the
 * default), or a bit at a time (gunzip --algo=bits). */
enum { INFLATE_TABLE, INFLATE_BITS };
extern int inflate_decoder;

/* RFC 1951, 3.2.5: the length codes 257..285 as a base length and how
 * many extra bits to add to it; the distance codes 0..29 the same. */
extern const unsigned short deflate_length_base[29];
extern const unsigned char  deflate_length_extra[29];
extern const unsigned short deflate_dist_base[30];
extern const unsigned char  deflate_dist_extra[30];

/* RFC 1951, 3.2.6: the code lengths of the fixed codes, for the 288
 * literal/length symbols and the 32 distance symbols. */
void deflate_fixed_lengths(unsigned char lit[288], unsigned char dist[32]);

/* RFC 1951, 3.2.7: the order in which a dynamic block gives the lengths of
 * the code-length code. */
extern const unsigned char deflate_clen_order[19];

#endif
