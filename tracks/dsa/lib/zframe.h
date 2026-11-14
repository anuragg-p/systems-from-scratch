/*
 * zframe.h - the zlib format (RFC 1950) around raw DEFLATE: two bytes of
 * header, the DEFLATE data of deflate.h and inflate.h, and an Adler-32 of
 * the uncompressed bytes, most significant byte first.
 *
 * git stores every loose object as one such stream. (The name "zlib" is
 * the format's; this is not the zlib library, and its header is not
 * called zlib.h so that it never hides the system's.)
 *
 *     zframe_pack(data, n, &opt, &out);        appends a whole stream to out
 *     err = zframe_unpack(in, n, &out, &used); appends the bytes it stands for
 *
 * DS_STATS=1 prints "stats: zlib: packed P, unpacked U, bytes checked B":
 * streams written and read, and the bytes run through Adler-32.
 */
#ifndef ZFRAME_H
#define ZFRAME_H

#include "ds.h"
#include "deflate.h"

/* Adler-32 (RFC 1950, 2.2) of n more bytes, from adler (1 to start). */
uint32_t zframe_adler32(uint32_t adler, const unsigned char *p, size_t n);

/* A zlib stream of in[0..n), appended to out (an Array of bytes): the
 * header, deflate_raw() with opt (NULL for its defaults), the Adler-32. */
void zframe_pack(const unsigned char *in, size_t n, const DeflateOptions *opt, Array *out);

/* The bytes the zlib stream at in[0..n) stands for, appended to out.
 * Returns NULL, and in *used how many bytes of in the stream took; or a
 * message saying what is wrong (good until the next call). Never reads
 * outside in[0..n). */
const char *zframe_unpack(const unsigned char *in, size_t n, Array *out, size_t *used);

#endif
