/*
 * sha1sum.h - SHA-1 (FIPS 180-4): any number of bytes in, a 160-bit
 * digest out, the same for the same bytes on any machine, and in practice
 * different for any other bytes.
 *
 * git names every object by the SHA-1 of its bytes (tools/git). The name
 * is 20 bytes; written out it is 40 hexadecimal digits.
 *
 *     Sha1 s;
 *     sha1_init(&s);
 *     sha1_update(&s, data, n);       as many times as there are pieces
 *     unsigned char name[20];
 *     sha1_final(&s, name);
 *
 * or sha1(data, n, name) for bytes all in one place.
 *
 * DS_STATS=1 prints "stats: sha1: blocks B, bytes N": the 64-byte blocks
 * compressed (the padding's included) and the bytes given to it.
 */
#ifndef SHA1SUM_H
#define SHA1SUM_H

#include "ds.h"

typedef struct {
    uint32_t      h[5];        /* the hash value so far */
    uint64_t      len;         /* bytes given so far */
    unsigned char buf[64];     /* the start of a block not yet full */
    size_t        nbuf;
} Sha1;

void sha1_init(Sha1 *s);
void sha1_update(Sha1 *s, const void *data, size_t n);
void sha1_final(Sha1 *s, unsigned char out[20]);
void sha1(const void *data, size_t n, unsigned char out[20]);

/* A name as 40 lowercase hexadecimal digits and a NUL. */
void sha1_hex(const unsigned char name[20], char hex[41]);
/* The name 40 hexadecimal digits at hex stand for: 0, or -1 if they are
 * not 40 such digits. */
int  sha1_unhex(const char *hex, unsigned char name[20]);

#endif
