/*
 * deflate.c - bytes into DEFLATE data (RFC 1951), which inflate.c reads
 * back.
 *
 * LZ77 (lz77.c) turns the input into tokens: literal bytes, and matches
 * that point back at bytes already seen. A block of tokens is then written
 * in Huffman codes (huffman.c), in one of three forms:
 *
 *   stored    the bytes as they are, for data that does not compress
 *   fixed     the codes RFC 1951 gives once and for all: nothing to send
 *             first, but common bytes cost 8 bits, as rare ones do
 *   dynamic   codes built for this block's own counts, sent first as
 *             code lengths (themselves run-length coded and in a Huffman
 *             code): 50 to 100 bytes of header that pay for themselves on
 *             a block of any size
 *
 * Each block is priced in all three forms, to the bit, before one is
 * written: the smallest wins.
 *
 * The stream is written as inflate.c reads it: numbers from their lowest
 * bit, Huffman codes from their first (highest) bit, each byte filled from
 * its lowest bit up.
 */
#include <stdlib.h>
#include <string.h>

#include "deflate.h"
#include "huffman.h"
#include "inflate.h"

#define BLOCK_TOKENS 16384    /* the tokens of one block, at most */

static struct {
    long stored, fixed, dynamic;
    long long bits;
} st;

static void print_stats(void)
{
    ds_stats_print("deflate", "stored blocks %ld, fixed blocks %ld, dynamic blocks %ld, bits out %lld",
                   st.stored, st.fixed, st.dynamic, st.bits);
}

static int tracing(void)
{
    static int on = -1;
    if (on < 0) {
        const char *s = getenv("DS_TRACE");
        on = s != NULL && *s != '\0' && strcmp(s, "0") != 0;
    }
    return on;
}

/* ------------------------------------------------------------ writing bits */

/* The output: whole bytes go into out, the bits of the last part byte wait. */
typedef struct {
    Array *out;
    uint64_t bits;      /* waiting; the first written is the lowest */
    int nbits;          /* under 8 between calls */
} Writer;

/* The k low bits of value (k <= 32), the lowest first. */
static void put(Writer *w, unsigned value, int k)
{
    // @build 09.04 the bit writer: the lowest bit first, a byte out whenever 8 are waiting
    w->bits |= (uint64_t)value << w->nbits;
    w->nbits += k;
    st.bits += k;
    while (w->nbits >= 8) {
        *(unsigned char *)array_push(w->out) = (unsigned char)(w->bits & 0xff);
        w->bits >>= 8;
        w->nbits -= 8;
    }
    // @end
}

/* Zero bits up to the next byte boundary. */
static void align(Writer *w)
{
    if (w->nbits > 0)
        put(w, 0, 8 - w->nbits);
}

/* ------------------------------------------------------------ codes */

/* A code ready to write: each symbol's length, and its code with the bits
 * in reverse, so that put() sends its first (highest) bit first. */
typedef struct {
    unsigned char len[288];
    unsigned rev[288];
} Codes;

static void make_codes(Codes *c, int n)
{
    unsigned codes[288];
    huff_codes(c->len, n, codes);
    for (int s = 0; s < n; s++) {
        unsigned r = 0;
        for (int k = 0; k < c->len[s]; k++)
            r |= ((codes[s] >> k) & 1) << (c->len[s] - 1 - k);
        c->rev[s] = r;
    }
}

/* A match length (3..258) -> its length code, less 257; and a distance
 * (1..32768) -> its distance code: the last code whose base it reaches. */
static int length_code(unsigned len)
{
    int c = 28;
    while (deflate_length_base[c] > len)
        c--;
    return c;
}

static int dist_code(unsigned dist)
{
    int c = 29;
    while (deflate_dist_base[c] > dist)
        c--;
    return c;
}

/* Give a code at least two symbols, so that every pattern of bits is a
 * code: a symbol alone, or none, gets company that is never used. No
 * reader we know of needs it. Huffman's code for two symbols or more uses
 * every pattern, so all this changes is a lone symbol's 1-bit code (the
 * literal/length code of an empty block; a distance code with one
 * distance code used) and a distance code with none. RFC 1951 (3.2.7)
 * allows both for distances; zlib (inftrees.c) refuses an incomplete
 * literal/length or distance code only when it is not a lone 1-bit one,
 * and takes one with no codes; zlib, GNU gzip 1.13 and ours read all
 * three back. The code-length code, which zlib wants complete, always has
 * two symbols or more here: it says 258 lengths or more, not all 0 (the
 * end of block's is not), and lengths that differ take two symbols, while
 * one length said 258 times is that length and then 16s. What it buys is
 * that every code written is complete, for a bit or two in a rare header. */
static void at_least_two(long *counts, int n)
{
    int used = 0;
    for (int s = 0; s < n; s++)
        used += counts[s] > 0;
    for (int s = 0; s < n && used < 2; s++)
        if (counts[s] == 0) {
            counts[s] = 1;
            used++;
        }
}

/* The bits the block's symbols take in codes lit and dist, extra bits and
 * the end of the block included. */
static long long data_bits(const Codes *lit, const Codes *dist, const long *litc, const long *distc)
{
    long long b = 0;
    for (int s = 0; s < 286; s++) {
        b += (long long)litc[s] * lit->len[s];
        if (s > 256)
            b += (long long)litc[s] * deflate_length_extra[s - 257];
    }
    for (int d = 0; d < 30; d++)
        b += (long long)distc[d] * (dist->len[d] + deflate_dist_extra[d]);
    return b;
}

/* The bits n bytes take as stored blocks (at most 65535 bytes each),
 * starting with nbits bits of a byte already written. */
static long long stored_bits(size_t n, int nbits)
{
    long long b = 0;
    do {
        size_t k = n < 65535 ? n : 65535;
        b += 3 + (8 - (nbits + 3) % 8) % 8 + 32 + 8 * (long long)k;
        nbits = 0;
        n -= k;
    } while (n > 0);
    return b;
}

/* ------------------------------------------------------------ the forms of a block */

/* Stored: after the 3 block bits, up to the byte boundary, then LEN and
 * NLEN and the bytes. A block holds 65535 bytes at most, so more is split. */
static void write_stored(Writer *w, const unsigned char *p, size_t n, int last)
{
    // @build 09.04 stored blocks: LEN, its complement, and the bytes as they are
    do {
        size_t k = n < 65535 ? n : 65535;
        put(w, last && k == n, 1);
        put(w, 0, 2);
        align(w);
        put(w, (unsigned)k, 16);
        put(w, (unsigned)~k & 0xffff, 16);
        for (size_t i = 0; i < k; i++)
            put(w, p[i], 8);
        p += k;
        n -= k;
        st.stored++;
    } while (n > 0);
    // @end
}

/* The tokens in codes lit and dist, then the end of the block. */
static void write_tokens(Writer *w, const Lz77Token *t, size_t nt, const Codes *lit, const Codes *dist)
{
    // @build 09.04 the symbols: a literal's code, or a length and a distance, each with its extra bits
    for (size_t i = 0; i < nt; i++) {
        if (t[i].dist == 0) {
            put(w, lit->rev[t[i].len], lit->len[t[i].len]);
            continue;
        }
        int lc = length_code(t[i].len), dc = dist_code(t[i].dist);
        put(w, lit->rev[257 + lc], lit->len[257 + lc]);
        put(w, t[i].len - deflate_length_base[lc], deflate_length_extra[lc]);
        put(w, dist->rev[dc], dist->len[dc]);
        put(w, t[i].dist - deflate_dist_base[dc], deflate_dist_extra[dc]);
    }
    put(w, lit->rev[256], lit->len[256]);
    // @end
}

/* A dynamic block's codes, and its header as it will be written. */
typedef struct {
    Codes lit, dist, cl;
    int nlit, ndist, nclen;            /* HLIT + 257, HDIST + 1, HCLEN + 4 */
    unsigned char item[286 + 30];      /* the code lengths, run-length coded: 0..15, 16, 17, 18 */
    unsigned char extra[286 + 30];     /* the repeat count of a 16, 17 or 18 */
    int nitems;
    long long bits;                    /* the header's size, after the 3 block bits */
} Header;

static void add_item(Header *h, int item, int extra)
{
    h->item[h->nitems] = (unsigned char)item;
    h->extra[h->nitems++] = (unsigned char)extra;
}

static const int item_extra_bits[19] = {[16] = 2, [17] = 3, [18] = 7};

/* The codes for a dynamic block with these counts, no code longer than 15
 * bits, and the header that says them: the lengths of both codes as one
 * run, coded with 16 (repeat the last length 3-6 times), 17 (3-10 zeros)
 * and 18 (11-138 zeros), in a third Huffman code of at most 7 bits. */
static void plan_dynamic(Header *h, const long *litc, const long *distc)
{
    // @build 09.04 a dynamic block's header: the lengths of its codes, run-length coded, in a code of their own
    long lc[286], dc[30], clc[19] = {0};
    memcpy(lc, litc, sizeof lc);
    memcpy(dc, distc, sizeof dc);
    at_least_two(lc, 286);
    at_least_two(dc, 30);
    huff_lengths_limited(lc, 286, HUFF_MAX_BITS, h->lit.len);
    huff_lengths_limited(dc, 30, HUFF_MAX_BITS, h->dist.len);
    for (h->nlit = 286; h->nlit > 257 && h->lit.len[h->nlit - 1] == 0; h->nlit--)
        ;
    for (h->ndist = 30; h->ndist > 1 && h->dist.len[h->ndist - 1] == 0; h->ndist--)
        ;
    unsigned char all[286 + 30];
    int n = h->nlit + h->ndist;
    memcpy(all, h->lit.len, (size_t)h->nlit);
    memcpy(all + h->nlit, h->dist.len, (size_t)h->ndist);
    h->nitems = 0;
    for (int i = 0; i < n;) {
        int v = all[i], run = 1;
        while (i + run < n && all[i + run] == v)
            run++;
        i += run;
        if (v == 0) {
            while (run >= 11) {
                int k = run < 138 ? run : 138;
                add_item(h, 18, k - 11);
                run -= k;
            }
            if (run >= 3) {
                add_item(h, 17, run - 3);
                run = 0;
            }
        } else {
            add_item(h, v, 0);
            run--;
            while (run >= 3) {
                int k = run < 6 ? run : 6;
                add_item(h, 16, k - 3);
                run -= k;
            }
        }
        while (run-- > 0)
            add_item(h, v, 0);
    }
    for (int i = 0; i < h->nitems; i++)
        clc[h->item[i]]++;
    at_least_two(clc, 19);
    huff_lengths_limited(clc, 19, 7, h->cl.len);
    for (h->nclen = 19; h->nclen > 4 && h->cl.len[deflate_clen_order[h->nclen - 1]] == 0; h->nclen--)
        ;
    make_codes(&h->lit, 286);
    make_codes(&h->dist, 30);
    make_codes(&h->cl, 19);
    h->bits = 5 + 5 + 4 + 3 * h->nclen;
    for (int i = 0; i < h->nitems; i++)
        h->bits += h->cl.len[h->item[i]] + item_extra_bits[h->item[i]];
    // @end
}

static void write_header(Writer *w, const Header *h)
{
    // @build 09.04 write a dynamic block's header
    put(w, (unsigned)(h->nlit - 257), 5);
    put(w, (unsigned)(h->ndist - 1), 5);
    put(w, (unsigned)(h->nclen - 4), 4);
    for (int i = 0; i < h->nclen; i++)
        put(w, h->cl.len[deflate_clen_order[i]], 3);
    for (int i = 0; i < h->nitems; i++) {
        put(w, h->cl.rev[h->item[i]], h->cl.len[h->item[i]]);
        put(w, h->extra[i], item_extra_bits[h->item[i]]);
    }
    // @end
}

/* One block: the tokens t[0..nt), which stand for the bytes raw[0..nraw). */
static void write_block(Writer *w, const Lz77Token *t, size_t nt, const unsigned char *raw, size_t nraw,
                        int last, int form, int number)
{
    // @build 09.04 a block: count its symbols, price it in each form, write the cheapest
    static Codes fixed_lit, fixed_dist;
    static int ready;
    if (!ready) {
        deflate_fixed_lengths(fixed_lit.len, fixed_dist.len);
        make_codes(&fixed_lit, 288);
        make_codes(&fixed_dist, 32);
        ready = 1;
    }
    long litc[286] = {0}, distc[30] = {0};
    for (size_t i = 0; i < nt; i++) {
        if (t[i].dist == 0) {
            litc[t[i].len]++;
        } else {
            litc[257 + length_code(t[i].len)]++;
            distc[dist_code(t[i].dist)]++;
        }
    }
    litc[256] = 1;
    Header h;
    plan_dynamic(&h, litc, distc);
    long long sb = stored_bits(nraw, w->nbits);
    long long fb = 3 + data_bits(&fixed_lit, &fixed_dist, litc, distc);
    long long db = 3 + h.bits + data_bits(&h.lit, &h.dist, litc, distc);
    if (form == DEFLATE_BEST)
        form = sb <= fb && sb <= db ? DEFLATE_STORED : fb <= db ? DEFLATE_FIXED : DEFLATE_DYNAMIC;
    if (tracing())
        fprintf(stderr, "trace: deflate: block %d%s: %zu bytes, %zu tokens: stored %lld bits, fixed %lld bits, "
                "dynamic %lld bits: %s\n", number, last ? " (last)" : "", nraw, nt, sb, fb, db,
                form == DEFLATE_STORED ? "stored" : form == DEFLATE_FIXED ? "fixed" : "dynamic");
    if (form == DEFLATE_STORED) {
        write_stored(w, raw, nraw, last);
        return;
    }
    put(w, (unsigned)last, 1);
    if (form == DEFLATE_FIXED) {
        put(w, 1, 2);
        write_tokens(w, t, nt, &fixed_lit, &fixed_dist);
        st.fixed++;
    } else {
        put(w, 2, 2);
        write_header(w, &h);
        write_tokens(w, t, nt, &h.lit, &h.dist);
        st.dynamic++;
    }
    // @end
}

void deflate_raw(const unsigned char *in, size_t n, const DeflateOptions *opt, Array *out)
{
    // @build 09.04 the input a block of tokens at a time, then the last bits out
    static const DeflateOptions defaults = DEFLATE_DEFAULTS;
    if (opt == NULL)
        opt = &defaults;
    ds_stats_at_exit(print_stats);
    Lz77 z;
    lz77_init(&z, in, n, opt->algo, opt->chain);
    Lz77Token *t = xmalloc(BLOCK_TOKENS * sizeof *t);
    Writer w = {out, 0, 0};
    int last = 0, number = 0;
    while (!last) {
        size_t start = z.pos;
        size_t nt = lz77_parse(&z, t, BLOCK_TOKENS);
        last = z.pos == n;
        write_block(&w, t, nt, in + start, z.pos - start, last, opt->blocks, ++number);
    }
    align(&w);
    free(t);
    lz77_free(&z);
    // @end
}
