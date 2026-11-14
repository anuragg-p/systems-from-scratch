/*
 * gz.c - the gzip file format (RFC 1952) around DEFLATE data.
 *
 * A gzip member is a header of at least 10 bytes, the DEFLATE data, and an
 * 8-byte trailer:
 *
 *   1f 8b      the magic number: this is a gzip file
 *   08         the compression method: 8 is DEFLATE, the only one
 *   FLG        which optional fields follow the 10 bytes: FEXTRA (4), a
 *              length and that many bytes; FNAME (8), the file's name, and
 *              FCOMMENT (16), a comment, each ending in a 0 byte; FHCRC (2),
 *              two bytes of CRC-32 of the header so far. The top three
 *              bits are reserved and must be 0.
 *   MTIME      4 bytes, the file's time, lowest byte first
 *   XFL, OS    how hard the compressor tried, and its system
 *   ...        the DEFLATE data
 *   CRC32      4 bytes: the CRC-32 of the bytes the data stands for
 *   ISIZE      4 bytes: how many bytes that is, modulo 2^32
 *
 * The trailer is the check that the data came out as it went in: DEFLATE
 * itself has none, and a damaged file can inflate to the wrong bytes
 * without a single error.
 */
#include <errno.h>
#include <stdlib.h>
#include <string.h>

#include "gz.h"
#include "inflate.h"

#define FHCRC    2
#define FEXTRA   4
#define FNAME    8
#define FCOMMENT 16

static char message[200];       /* what gz_unpack() returns when the file is wrong */

unsigned char *read_all(const char *path, size_t *n)
{
    FILE *f = open_input(path);
    size_t cap = 1 << 16, len = 0, k;
    unsigned char *buf = xmalloc(cap);
    while ((k = fread(buf + len, 1, cap - len, f)) > 0) {
        len += k;
        if (len == cap) {
            unsigned char *bigger = xmalloc(2 * cap);
            memcpy(bigger, buf, len);
            free(buf);
            buf = bigger;
            cap *= 2;
        }
    }
    if (ferror(f))
        die("%s: %s", path && strcmp(path, "-") != 0 ? path : "stdin", strerror(errno));
    close_input(f);
    *n = len;
    return buf;
}

void write_all(const char *path, const void *p, size_t n)
{
    FILE *f = fopen(path, "wb");
    if (f == NULL)
        die("%s: %s", path, strerror(errno));
    int bad = n > 0 && fwrite(p, 1, n, f) != n;      /* p may be NULL when n is 0 */
    if (fclose(f) != 0)
        bad = 1;
    if (bad) {
        int e = errno;
        remove(path);
        die("%s: %s", path, strerror(e));
    }
}

uint32_t crc32(uint32_t crc, const unsigned char *p, size_t n)
{
    // @build 09.02 CRC-32: a byte at a time, with a table of what each byte value adds
    /* The data is one long binary number, divided by the CRC-32 polynomial
     * in arithmetic where adding is xor; the CRC is the remainder. The bits
     * are taken lowest first, so the polynomial is written backwards:
     * 0xedb88320. table[b] is what dividing out the byte b leaves. */
    static uint32_t table[256];
    if (table[1] == 0) {
        for (uint32_t b = 0; b < 256; b++) {
            uint32_t r = b;
            for (int k = 0; k < 8; k++)
                r = r & 1 ? (r >> 1) ^ 0xedb88320u : r >> 1;
            table[b] = r;
        }
    }
    crc = ~crc;
    for (size_t i = 0; i < n; i++)
        crc = table[(crc ^ p[i]) & 0xff] ^ (crc >> 8);
    return ~crc;
    // @end
}

static uint32_t le32(const unsigned char *p)
{
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

/* The member header at in[0..n): its length in *len, or what is wrong. */
static const char *header(const unsigned char *in, size_t n, size_t *len)
{
    // @build 09.02 the header: check the magic number and the method, and skip the fields FLG says are there
    if (n == 0)
        return "empty, not a gzip file";
    if (n < 2 || in[0] != 0x1f || in[1] != 0x8b) {
        if (n == 1)
            snprintf(message, sizeof message, "not in gzip format (it is one byte, %02x)", in[0]);
        else
            snprintf(message, sizeof message, "not in gzip format (it starts %02x %02x, not 1f 8b)", in[0], in[1]);
        return message;
    }
    if (n < 10)
        return "the file ends inside the gzip header";
    if (in[2] != 8) {
        snprintf(message, sizeof message, "compression method %d, not 8 (deflate)", in[2]);
        return message;
    }
    int flg = in[3];
    if (flg & 0xe0) {
        snprintf(message, sizeof message, "flag bits 0x%02x set, which RFC 1952 reserves", flg & 0xe0);
        return message;
    }
    size_t p = 10;
    if (flg & FEXTRA) {
        if (n - p < 2)
            return "the file ends inside the gzip header";
        size_t xlen = in[p] | (size_t)in[p + 1] << 8;
        p += 2;
        if (n - p < xlen)
            return "the file ends inside the gzip header";
        p += xlen;
    }
    for (int field = FNAME; field <= FCOMMENT; field *= 2) {
        if (!(flg & field))
            continue;
        while (p < n && in[p] != 0)
            p++;
        if (p == n)
            return "the file ends inside the gzip header";
        p++;
    }
    if (flg & FHCRC) {
        if (n - p < 2)
            return "the file ends inside the gzip header";
        unsigned want = in[p] | in[p + 1] << 8, got = crc32(0, in, p) & 0xffff;
        if (want != got) {
            snprintf(message, sizeof message, "the header's CRC-16 is %04x, but its bytes give %04x", want, got);
            return message;
        }
        p += 2;
    }
    *len = p;
    return NULL;
    // @end
}

const char *gz_unpack(const unsigned char *in, size_t n, Array *out)
{
    // @build 09.02 the members: a header, the DEFLATE data, and the trailer it must agree with
    size_t pos = 0;
    do {
        if (pos > 0 && (n - pos < 2 || in[pos] != 0x1f || in[pos + 1] != 0x8b)) {
            snprintf(message, sizeof message, "%zu bytes after the end of the gzip data, not another member",
                     n - pos);
            return message;
        }
        size_t len, used, start = out->len;
        const char *err = header(in + pos, n - pos, &len);
        if (err)
            return err;
        pos += len;
        err = inflate_raw(in + pos, n - pos, out, &used);
        if (err)
            return err;
        pos += used;
        if (n - pos < 8)
            return "the file ends before the trailer (the CRC-32 and the size)";
        uint32_t size = (uint32_t)(out->len - start);
        uint32_t crc = out->len > start ? crc32(0, (unsigned char *)out->data + start, out->len - start) : 0;
        if (crc != le32(in + pos)) {
            snprintf(message, sizeof message, "the data's CRC-32 is %08x, but the trailer says %08x",
                     (unsigned)crc, (unsigned)le32(in + pos));
            return message;
        }
        if (size != le32(in + pos + 4)) {
            snprintf(message, sizeof message, "the data is %u bytes (modulo 2^32), but the trailer says %u",
                     (unsigned)size, (unsigned)le32(in + pos + 4));
            return message;
        }
        pos += 8;
    } while (pos < n);
    return NULL;
    // @end
}

// @from 09.04
/* Four bytes, the lowest first, as every number in a gzip file is. */
static void put32(Array *out, uint32_t v)
{
    for (int k = 0; k < 4; k++)
        *(unsigned char *)array_push(out) = (unsigned char)(v >> (8 * k));
}
// @end

void gz_pack(const unsigned char *in, size_t n, const char *name, long mtime, int xfl,
             const DeflateOptions *opt, Array *out)
{
    // @build 09.04 a member: the header, the deflated data, then its CRC-32 and size
    static const unsigned char magic[3] = {0x1f, 0x8b, 8};
    for (int k = 0; k < 3; k++)
        *(unsigned char *)array_push(out) = magic[k];
    *(unsigned char *)array_push(out) = name ? FNAME : 0;
    put32(out, (uint32_t)mtime);
    *(unsigned char *)array_push(out) = (unsigned char)xfl;
    *(unsigned char *)array_push(out) = 3;      /* OS: Unix */
    if (name) {
        for (const char *c = name; *c; c++)
            *(unsigned char *)array_push(out) = (unsigned char)*c;
        *(unsigned char *)array_push(out) = 0;
    }
    deflate_raw(in, n, opt, out);
    put32(out, crc32(0, in, n));
    put32(out, (uint32_t)n);
    // @end
}
