/*
 * zframe.c - a zlib stream (RFC 1950, 2.2): DEFLATE data with two bytes
 * in front and a checksum behind.
 *
 *   CMF   the method, 8 (DEFLATE), and the window, 7 (32 KB): 0x78
 *   FLG   two bits saying how hard the compressor tried, and five check
 *         bits chosen so that CMF * 256 + FLG is a multiple of 31
 *   ...   the DEFLATE data (lib/deflate.c writes it, lib/inflate.c reads it)
 *   ADLER32  of the bytes before compression, most significant byte first
 *
 * Adler-32 is two sums kept modulo 65521, the largest prime below 2^16: s1,
 * the bytes so far plus one, and s2, the sum of every s1. It is far weaker
 * than a CRC, and quicker; what it catches is a stream damaged in a way
 * inflate does not notice.
 */
#include <stdio.h>

#include "zframe.h"
#include "inflate.h"

static struct {
    long packed, unpacked, checked;
} st;

static void print_stats(void)
{
    ds_stats_print("zlib", "packed %ld, unpacked %ld, bytes checked %ld", st.packed, st.unpacked, st.checked);
}

uint32_t zframe_adler32(uint32_t adler, const unsigned char *p, size_t n)
{
    // @build 10.01 Adler-32: two running sums, modulo 65521
    uint32_t s1 = adler & 0xffff, s2 = adler >> 16;
    for (size_t i = 0; i < n; i++) {
        s1 = (s1 + p[i]) % 65521;
        s2 = (s2 + s1) % 65521;
    }
    st.checked += (long)n;
    return s2 << 16 | s1;
    // @end
}

static void put_byte(Array *out, unsigned char c)
{
    *(unsigned char *)array_push(out) = c;
}

void zframe_pack(const unsigned char *in, size_t n, const DeflateOptions *opt, Array *out)
{
    // @build 10.01 a zlib stream: the header, the DEFLATE data, the checksum
    ds_stats_at_exit(print_stats);
    unsigned cmf = 0x78;                 /* CM 8, CINFO 7: DEFLATE, a 32 KB window */
    unsigned flg = 0;                    /* FLEVEL 0 ("fastest"), as git writes its objects */
    flg += (31 - (cmf * 256 + flg) % 31) % 31;   /* FCHECK */
    put_byte(out, (unsigned char)cmf);
    put_byte(out, (unsigned char)flg);
    deflate_raw(in, n, opt, out);
    uint32_t a = zframe_adler32(1, in, n);
    for (int shift = 24; shift >= 0; shift -= 8)
        put_byte(out, (unsigned char)(a >> shift));
    st.packed++;
    // @end
}

const char *zframe_unpack(const unsigned char *in, size_t n, Array *out, size_t *used)
{
    // @build 10.01 reading one: check the header, inflate, check the sum
    static char msg[160];
    ds_stats_at_exit(print_stats);
    if (n < 2)
        return "the zlib stream ends in its header";
    unsigned cmf = in[0], flg = in[1];
    if ((cmf & 0x0f) != 8) {
        snprintf(msg, sizeof msg, "compression method %u in the zlib header, not 8 (DEFLATE)", cmf & 0x0f);
        return msg;
    }
    if ((cmf >> 4) > 7)
        return "a window larger than 32 KB in the zlib header";
    if ((cmf * 256 + flg) % 31 != 0)
        return "the zlib header's check bits are wrong";
    if (flg & 0x20)
        return "the zlib stream wants a preset dictionary";
    size_t start = out->len, took;
    const char *err = inflate_raw(in + 2, n - 2, out, &took);
    if (err != NULL)
        return err;
    size_t end = 2 + took;
    if (n - end < 4)
        return "the zlib stream ends before its Adler-32";
    uint32_t want = (uint32_t)in[end] << 24 | (uint32_t)in[end + 1] << 16 | (uint32_t)in[end + 2] << 8 | in[end + 3];
    uint32_t got = out->len > start ? zframe_adler32(1, (const unsigned char *)out->data + start, out->len - start) : 1;
    if (got != want) {
        snprintf(msg, sizeof msg, "the data's Adler-32 is %08x, but the stream says %08x", (unsigned)got, (unsigned)want);
        return msg;
    }
    *used = end + 4;
    st.unpacked++;
    return NULL;
    // @end
}
