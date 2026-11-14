/*
 * gz.h - the gzip file format (RFC 1952), for gzip and gunzip: a header,
 * the DEFLATE data, and a trailer with the CRC-32 and the size of the
 * bytes it stands for. A file may hold several of these members, one
 * after another; it stands for their bytes one after another.
 */
#ifndef GZ_H
#define GZ_H

#include "ds.h"
#include "deflate.h"     // @from 09.04

/* A file whole (standard input for NULL or "-"), in memory: its bytes,
 * with its length in *n. */
unsigned char *read_all(const char *path, size_t *n);

/* p[0..n) as the file path, made or replaced. An error is fatal, and
 * leaves no half-written file behind. */
void write_all(const char *path, const void *p, size_t n);

/* The CRC-32 of p[0..n) carried on from crc, the CRC-32 of the bytes
 * before them (0 to start). */
uint32_t crc32(uint32_t crc, const unsigned char *p, size_t n);

/* The gzip members in[0..n) hold, inflated, checked against their
 * trailers and appended to out, an Array of bytes. Returns NULL, or what
 * is wrong with the file. */
const char *gz_unpack(const unsigned char *in, size_t n, Array *out);

/* in[0..n) as one gzip member appended to out: a header with name (no     @from 09.04
 * directory; NULL for none) and mtime (seconds since 1970, 0 for none),    @from 09.04
 * the data deflated with opt, and the trailer. xfl is the header's extra   @from 09.04
 * flags: 2 for the slowest, smallest setting, 4 for the fastest, else 0.   @from 09.04
 */                                                                          // @from 09.04
void gz_pack(const unsigned char *in, size_t n, const char *name, long mtime, int xfl,    // @from 09.04
             const DeflateOptions *opt, Array *out);                                      // @from 09.04

#endif
