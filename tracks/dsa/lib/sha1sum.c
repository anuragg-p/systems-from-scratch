/*
 * sha1sum.c - SHA-1, as FIPS 180-4 defines it (sections 4.1.1, 4.2.1,
 * 5.1.1, 5.3.1 and 6.1.2).
 *
 * The message is padded to a whole number of 64-byte blocks: a 1 bit,
 * zero bits, and the message's length in bits as the last 8 bytes. Each
 * block in turn is stirred into a hash value of five 32-bit words, which
 * starts at fixed constants: the block becomes 80 words (the first 16 are
 * the block, each later one the earlier ones mixed and rotated), and 80
 * rounds each mix one of them into the five words. After the last block
 * the five words, big-endian, are the digest.
 *
 * Nothing in it is secret or clever to write down; what makes it a hash
 * is that every bit of the input reaches every bit of the output many
 * times over, so no one knows how to find two inputs with one digest
 * except by trying (for SHA-1, people have now done it, with great effort:
 * git checks for the known way of doing it; this one does not).
 */
#include <string.h>

#include "sha1sum.h"

static struct {
    long blocks, bytes;
} st;

static void print_stats(void)
{
    ds_stats_print("sha1", "blocks %ld, bytes %ld", st.blocks, st.bytes);
}

static uint32_t rotl(uint32_t x, int n)
{
    return (x << n) | (x >> (32 - n));
}

/* Stir one 64-byte block into the hash value (6.1.2). */
static void compress(uint32_t h[5], const unsigned char *block)
{
    // @build 10.01 one block: 80 words from 16, and 80 rounds of mixing
    uint32_t w[80];
    for (int t = 0; t < 16; t++)
        w[t] = (uint32_t)block[4 * t] << 24 | (uint32_t)block[4 * t + 1] << 16 |
               (uint32_t)block[4 * t + 2] << 8 | (uint32_t)block[4 * t + 3];
    for (int t = 16; t < 80; t++)
        w[t] = rotl(w[t - 3] ^ w[t - 8] ^ w[t - 14] ^ w[t - 16], 1);
    uint32_t a = h[0], b = h[1], c = h[2], d = h[3], e = h[4];
    for (int t = 0; t < 80; t++) {
        uint32_t f, k;
        if (t < 20) {
            f = (b & c) ^ (~b & d);              /* Ch: b chooses between c and d */
            k = 0x5a827999;
        } else if (t < 40) {
            f = b ^ c ^ d;                       /* Parity */
            k = 0x6ed9eba1;
        } else if (t < 60) {
            f = (b & c) ^ (b & d) ^ (c & d);     /* Maj: the majority of the three */
            k = 0x8f1bbcdc;
        } else {
            f = b ^ c ^ d;
            k = 0xca62c1d6;
        }
        uint32_t T = rotl(a, 5) + f + e + k + w[t];
        e = d;
        d = c;
        c = rotl(b, 30);
        b = a;
        a = T;
    }
    h[0] += a;
    h[1] += b;
    h[2] += c;
    h[3] += d;
    h[4] += e;
    st.blocks++;
    // @end
}

/* The initial hash value (5.3.1). */
void sha1_init(Sha1 *s)
{
    s->h[0] = 0x67452301;
    s->h[1] = 0xefcdab89;
    s->h[2] = 0x98badcfe;
    s->h[3] = 0x10325476;
    s->h[4] = 0xc3d2e1f0;
    s->len = 0;
    s->nbuf = 0;
    ds_stats_at_exit(print_stats);
}

/* Bytes in: whole blocks are compressed as soon as they are whole; the
 * rest waits in buf for more. */
void sha1_update(Sha1 *s, const void *data, size_t n)
{
    // @build 10.01 bytes in, a block at a time
    const unsigned char *p = data;
    s->len += n;
    st.bytes += (long)n;
    if (s->nbuf > 0) {
        size_t take = 64 - s->nbuf < n ? 64 - s->nbuf : n;
        memcpy(s->buf + s->nbuf, p, take);
        s->nbuf += take;
        p += take;
        n -= take;
        if (s->nbuf < 64)
            return;
        compress(s->h, s->buf);
        s->nbuf = 0;
    }
    while (n >= 64) {
        compress(s->h, p);
        p += 64;
        n -= 64;
    }
    memcpy(s->buf, p, n);
    s->nbuf = n;
    // @end
}

/* The padding (5.1.1): a 1 bit, zeros up to 8 bytes short of a block, and
 * the length in bits, big-endian. Then the five words, big-endian, are
 * the digest. */
void sha1_final(Sha1 *s, unsigned char out[20])
{
    // @build 10.01 the padding, the length, and the digest
    uint64_t bits = s->len * 8;
    s->buf[s->nbuf++] = 0x80;
    if (s->nbuf > 56) {                  /* no room for the length: one more block */
        memset(s->buf + s->nbuf, 0, 64 - s->nbuf);
        compress(s->h, s->buf);
        s->nbuf = 0;
    }
    memset(s->buf + s->nbuf, 0, 56 - s->nbuf);
    for (int i = 0; i < 8; i++)
        s->buf[56 + i] = (unsigned char)(bits >> (56 - 8 * i));
    compress(s->h, s->buf);
    for (int i = 0; i < 5; i++) {
        out[4 * i] = (unsigned char)(s->h[i] >> 24);
        out[4 * i + 1] = (unsigned char)(s->h[i] >> 16);
        out[4 * i + 2] = (unsigned char)(s->h[i] >> 8);
        out[4 * i + 3] = (unsigned char)s->h[i];
    }
    // @end
}

void sha1(const void *data, size_t n, unsigned char out[20])
{
    Sha1 s;
    sha1_init(&s);
    sha1_update(&s, data, n);
    sha1_final(&s, out);
}

void sha1_hex(const unsigned char name[20], char hex[41])
{
    static const char digits[] = "0123456789abcdef";
    for (int i = 0; i < 20; i++) {
        hex[2 * i] = digits[name[i] >> 4];
        hex[2 * i + 1] = digits[name[i] & 15];
    }
    hex[40] = '\0';
}

static int hexval(int c)
{
    if (c >= '0' && c <= '9')
        return c - '0';
    if (c >= 'a' && c <= 'f')
        return c - 'a' + 10;
    if (c >= 'A' && c <= 'F')
        return c - 'A' + 10;
    return -1;
}

int sha1_unhex(const char *hex, unsigned char name[20])
{
    for (int i = 0; i < 20; i++) {
        int hi = hexval((unsigned char)hex[2 * i]);
        if (hi < 0)
            return -1;
        int lo = hexval((unsigned char)hex[2 * i + 1]);
        if (lo < 0)
            return -1;
        name[i] = (unsigned char)(hi << 4 | lo);
    }
    return 0;
}
