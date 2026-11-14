/*
 * record.c - a row as bytes.
 *
 * A record is a header followed by a body. The header is a list of
 * varints: first the header's own length in bytes, then one "serial type"
 * per column, saying how that column's value is stored in the body:
 *
 *   0       NULL, no bytes          7      a float, 8 bytes, IEEE 754
 *   1..4    an integer in 1, 2, 3, 4 bytes, big-endian, two's complement
 *   5, 6    an integer in 6 or 8 bytes
 *   8, 9    the integer 0 or 1, no bytes
 *   N >= 12, even:  a blob of (N - 12) / 2 bytes
 *   N >= 13, odd:   text of (N - 13) / 2 bytes (UTF-8)
 *
 * A varint is SQLite's variable-length integer: 1 to 9 bytes, big-endian.
 * In the first 8 bytes the high bit says "more follows" and the low 7 bits
 * are data; a 9th byte, if reached, gives all 8 of its bits. Small numbers,
 * which are most numbers, take one byte.
 */
#include <stdlib.h>
#include <string.h>

#include "db.h"

/* Decode the varint at p into *v. Returns how many bytes it took (1-9).
 * The 9th byte, when reached, contributes all 8 of its bits. */
int varint_get(const u8 *p, u64 *v)
{
    // @build 01.03 read a varint
    u64 x = 0;
    for (int i = 0; i < 8; i++) {
        x = (x << 7) | (p[i] & 0x7f);
        if (!(p[i] & 0x80)) {
            *v = x;
            return i + 1;
        }
    }
    *v = (x << 8) | p[8];
    return 9;
    // @end
}

/* Encode v as a varint at p, which must have room for 9 bytes. Returns the
 * length written; the inverse of varint_get. */
int varint_put(u8 *p, u64 v)
{
    // @build 01.03 write a varint
    /* A value with any of its top 8 bits set (v > 0x00ffffffffffffff)
     * takes all 9 bytes: the last holds the low 8 bits, the 8 before it 7
     * bits each, with the high bit set. Anything smaller takes as few
     * 7-bit groups as hold it, most significant first, 0x80 on every byte
     * but the last. */
    if (v > 0x00ffffffffffffffULL) {
        p[8] = (u8)v;
        v >>= 8;
        for (int i = 7; i >= 0; i--) {
            p[i] = (u8)((v & 0x7f) | 0x80);
            v >>= 7;
        }
        return 9;
    }
    u8 tmp[9];
    int n = 0;
    do {
        tmp[n++] = (u8)((v & 0x7f) | 0x80);
        v >>= 7;
    } while (v);
    tmp[0] &= 0x7f;              /* the last byte, written first here, ends it */
    for (int i = 0; i < n; i++)
        p[i] = tmp[n - 1 - i];
    return n;
    // @end
}

int varint_len(u64 v)
{
    u8 tmp[9];
    return varint_put(tmp, v);
}

/* The serial type that stores v in the fewest bytes. Text of n bytes is
 * 13 + 2n and a blob 12 + 2n. An integer takes the smallest type that
 * holds it: 8 for 0 and 9 for 1 (no body bytes at all), then 1, 2, 3, 4,
 * 5 for 8, 16, 24, 32, 48 bits, and 6 for anything wider. */
u32 serial_type(const Value *v)
{
    // @build 01.03 choose a serial type
    switch (v->type) {
    case V_NULL:
        return 0;
    case V_REAL:
        return 7;
    case V_TEXT:
        return 13 + 2 * (u32)v->n;
    case V_BLOB:
        return 12 + 2 * (u32)v->n;
    }
    i64 i = v->i;
    if (i == 0)
        return 8;
    if (i == 1)
        return 9;
    if (i >= -128 && i <= 127)
        return 1;
    if (i >= -32768 && i <= 32767)
        return 2;
    if (i >= -8388608 && i <= 8388607)
        return 3;
    if (i >= -2147483648LL && i <= 2147483647LL)
        return 4;
    if (i >= -140737488355328LL && i <= 140737488355327LL)
        return 5;
    return 6;
    // @end
}

/* How many body bytes a value of this serial type takes. */
u32 serial_size(u32 type)
{
    static const u8 size[] = {0, 1, 2, 3, 4, 6, 8, 8, 0, 0, 0, 0};
    if (type >= 12)
        return (type - 12) / 2;
    return size[type];
}

/* Decode the value of serial type `type` whose body bytes start at p into
 * *v. Integers are sign-extended from their first byte; a float is
 * assembled as a u64 and copied into a double so no pointer is
 * type-punned. Text and blobs are not copied: v->s points into p. */
void serial_get(u32 type, const u8 *p, Value *v)
{
    memset(v, 0, sizeof *v);
    // @build 01.03 decode a value
    if (type == 0) {
        v->type = V_NULL;
    } else if (type == 8 || type == 9) {
        v->type = V_INT;
        v->i = type - 8;
    } else if (type <= 6) {
        u32 n = serial_size(type);
        u64 x = (u64)(i64)(signed char)p[0];    /* sign-extend the first byte */
        for (u32 k = 1; k < n; k++)
            x = (x << 8) | p[k];
        v->type = V_INT;
        v->i = (i64)x;
    } else if (type == 7) {
        u64 bits = 0;
        for (int k = 0; k < 8; k++)
            bits = (bits << 8) | p[k];
        v->type = V_REAL;
        memcpy(&v->r, &bits, sizeof v->r);
    } else if (type >= 12) {
        v->type = (type & 1) ? V_TEXT : V_BLOB;
        v->s = (const char *)p;
        v->n = (int)serial_size(type);
    }
    // @end
}

/* Write the body bytes of v, whose serial type is `type`, at p. Types that
 * have no body (NULL, 8, 9) write nothing. */
void serial_put(u32 type, const Value *v, u8 *p)
{
    if (type >= 1 && type <= 6) {
        u32 n = serial_size(type);
        u64 x = (u64)v->i;
        for (int k = (int)n - 1; k >= 0; k--) {
            p[k] = (u8)x;
            x >>= 8;
        }
    } else if (type == 7) {
        u64 bits;
        memcpy(&bits, &v->r, sizeof bits);
        for (int k = 7; k >= 0; k--) {
            p[k] = (u8)bits;
            bits >>= 8;
        }
    } else if (type >= 12) {
        memcpy(p, v->s, serial_size(type));
    }
}

/* Encode n values as a record and append it to out. */
void record_build(Buf *out, const Value *vals, int n)
{
    u32 types[256];
    u32 *t = n <= 256 ? types : xmalloc((size_t)n * sizeof(u32));
    u64 hdr = 0, body = 0;
    for (int i = 0; i < n; i++) {
        t[i] = serial_type(&vals[i]);
        hdr += (u64)varint_len(t[i]);
        body += serial_size(t[i]);
    }
    /* The header's length counts the varint that holds it. */
    int lenlen = 1;
    while (varint_len(hdr + (u64)lenlen) > lenlen)
        lenlen++;
    u64 hlen = hdr + (u64)lenlen;
    buf_reserve(out, (size_t)(hlen + body));
    u8 *p = out->p + out->n;
    p += varint_put(p, hlen);
    for (int i = 0; i < n; i++)
        p += varint_put(p, t[i]);
    for (int i = 0; i < n; i++) {
        serial_put(t[i], &vals[i], p);
        p += serial_size(t[i]);
    }
    out->n += (size_t)(hlen + body);
    if (t != types)
        free(t);
}

/* Decode up to max columns of the record rec (len bytes) into out. Returns
 * how many columns the record has, which may be more or fewer than max,
 * or -1 if the record is malformed. Text and blob values point into rec. */
int record_decode(const u8 *rec, u32 len, Value *out, int max)
{
    u64 hlen;
    u32 h = (u32)varint_get(rec, &hlen);
    if (hlen > len || hlen < h)
        return -1;
    u32 body = (u32)hlen;
    int n = 0;
    while (h < hlen) {
        u64 type;
        h += (u32)varint_get(rec + h, &type);
        u32 size = serial_size((u32)type);
        if (type == 10 || type == 11 || body + size > len)
            return -1;
        if (n < max)
            serial_get((u32)type, rec + body, &out[n]);
        body += size;
        n++;
    }
    return n;
}

int record_count(const u8 *rec, u32 len)
{
    return record_decode(rec, len, NULL, 0);
}

// @from 02.01
/* Compare two records field by field, over at most nfields fields (or all
 * of the shorter one). The order is SQLite's: NULL < numbers < text <
 * blobs; text compares bytewise (the BINARY collation). */
int record_compare(const u8 *a, u32 alen, const u8 *b, u32 blen, int nfields)
{
    u64 ahl, bhl, at, bt;
    u32 ah = (u32)varint_get(a, &ahl), bh = (u32)varint_get(b, &bhl);
    u32 ab = (u32)ahl, bb = (u32)bhl;
    for (int i = 0; i < nfields && ah < ahl && bh < bhl; i++) {
        ah += (u32)varint_get(a + ah, &at);
        bh += (u32)varint_get(b + bh, &bt);
        if (ab + serial_size((u32)at) > alen || bb + serial_size((u32)bt) > blen)
            return 0;
        Value x, y;
        serial_get((u32)at, a + ab, &x);
        serial_get((u32)bt, b + bb, &y);
        int c = value_compare(&x, &y);
        if (c)
            return c;
        ab += serial_size((u32)at);
        bb += serial_size((u32)bt);
    }
    return 0;
}
// @end
