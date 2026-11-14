/*
 * inflate.c - DEFLATE data back into the bytes it stands for (RFC 1951).
 *
 * DEFLATE data is a stream of bits, read from the lowest bit of each byte
 * up, cut into blocks. Each block starts with three bits: one that says
 * whether it is the last, and two for its type. A stored block (type 0)
 * holds its bytes as they are. The other two hold symbols in Huffman
 * codes: a literal byte (0..255), the end of the block (256), or a length
 * (257..285) followed by a distance, which says "copy that many bytes
 * from that far back in what has been written". A block in the fixed codes
 * (type 1) uses codes the RFC gives once and for all; a block in dynamic
 * codes (type 2) first says which code lengths its own codes have, and
 * says even that in a Huffman code.
 *
 * Reading a symbol is reading one bit at a time until the bits so far are
 * a code. The codes are canonical (huffman.c), so the codes of each length
 * are consecutive numbers, and "is this a code of length L, and whose" is
 * one subtraction. That is decode_bits(). decode_table() reads 9 bits at
 * once and looks them up in a table of 512 entries that says which symbol
 * they start with, and how long its code really is: the short codes, which
 * Huffman gives the common symbols, take one look; the rare long ones go
 * on a bit at a time.
 *
 * The input is untrusted: every count it gives is checked before it is
 * used, reading past its end gives zero bits that are caught, and a
 * distance is checked against what has been written.
 */
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>

#include "huffman.h"
#include "inflate.h"

int inflate_decoder = INFLATE_TABLE;

const unsigned short deflate_length_base[29] = {
    3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 15, 17, 19, 23, 27, 31,
    35, 43, 51, 59, 67, 83, 99, 115, 131, 163, 195, 227, 258};
const unsigned char deflate_length_extra[29] = {
    0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2,
    3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 0};
const unsigned short deflate_dist_base[30] = {
    1, 2, 3, 4, 5, 7, 9, 13, 17, 25, 33, 49, 65, 97, 129, 193,
    257, 385, 513, 769, 1025, 1537, 2049, 3073, 4097, 6145, 8193, 12289, 16385, 24577};
const unsigned char deflate_dist_extra[30] = {
    0, 0, 0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6,
    7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13};

void deflate_fixed_lengths(unsigned char lit[288], unsigned char dist[32])
{
    for (int s = 0; s < 288; s++)
        lit[s] = s < 144 ? 8 : s < 256 ? 9 : s < 280 ? 7 : 8;
    for (int s = 0; s < 32; s++)
        dist[s] = 5;
}

static struct {
    long stored, fixed, dynamic, symbols, lookups, walked;
} st;

static void print_stats(void)
{
    ds_stats_print("inflate", "stored blocks %ld, fixed blocks %ld, dynamic blocks %ld, symbols %ld, "
                   "table lookups %ld, bits walked %ld",
                   st.stored, st.fixed, st.dynamic, st.symbols, st.lookups, st.walked);
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

/* Bytes for the trace, in double quotes, as C would write them. */
static void trace_bytes(const unsigned char *p, size_t n)
{
    fputc('"', stderr);
    for (size_t i = 0; i < n; i++) {
        int c = p[i];
        if (c == '"' || c == '\\')
            fprintf(stderr, "\\%c", c);
        else if (c == '\n')
            fputs("\\n", stderr);
        else if (c == '\t')
            fputs("\\t", stderr);
        else if (c >= 32 && c < 127)
            fputc(c, stderr);
        else
            fprintf(stderr, "\\x%02x", c);
    }
    fputs("\"\n", stderr);
}

/* ------------------------------------------------------------ reading bits */

#define TABLE_BITS 9                  /* the table looks at this many bits at once */

/* One code, ready to read: the canonical numbering, and the table. */
typedef struct {
    const char *name;                 /* for messages: "literal/length", "distance", "code-length" */
    int count[HUFF_MAX_BITS + 1];     /* how many codes have each length */
    int first[HUFF_MAX_BITS + 1];     /* the first (smallest) code of each length */
    int index[HUFF_MAX_BITS + 1];     /* where the symbols of each length start in sym */
    short sym[288];                   /* the symbols in the order of their codes */
    unsigned short table[1 << TABLE_BITS];   /* the next 9 bits -> symbol << 4 | its length, or 0 */
    int longest;
} Code;

/* Where the reading is: the input, the bits taken from it so far, and the
 * output. */
typedef struct {
    const unsigned char *in;
    size_t n;
    size_t pos;                       /* the next byte to load */
    uint64_t bits;                    /* loaded, not used yet; the next bit is the lowest */
    int nbits;
    Array *out;
    int block;                        /* blocks begun, for the trace */
    int last;                         /* this block is the last */
} State;

static char message[200];             /* what inflate_raw() returns when the data is wrong */

static int fail(State *s, const char *fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(message, sizeof message, fmt, ap);
    va_end(ap);
    return -1;
}

/* Make sure at least k bits (k <= 56) are loaded. Past the end of the
 * input the bytes are taken as zeros: cut_short() catches any use of them. */
static void load(State *s, int k)
{
    while (s->nbits < k) {
        uint64_t byte = s->pos < s->n ? s->in[s->pos] : 0;
        s->pos++;
        s->bits |= byte << s->nbits;
        s->nbits += 8;
    }
}

/* The next k bits (k <= 16) as a number, the first of them its lowest bit:
 * how DEFLATE packs every number that is not a Huffman code. */
static unsigned bits(State *s, int k)
{
    // @build 09.02 the bit reader: the next k bits, lowest first
    load(s, k);
    unsigned v = (unsigned)(s->bits & ((1u << k) - 1));
    s->bits >>= k;
    s->nbits -= k;
    return v;
    // @end
}

/* Have the bits read so far gone past the last byte of the input? */
static int cut_short(const State *s)
{
    return s->pos > s->n && (s->pos - s->n) * 8 > (size_t)s->nbits;
}

/* The code whose lengths are lengths[0..n), made ready to read. Lengths
 * that ask for more codes than there are bit patterns are an error. Fewer
 * is allowed: a pattern no symbol has is caught when it is read. */
static int build(State *s, Code *c, const unsigned char *lengths, int n, const char *name)
{
    // @build 09.02 a code from its lengths: its codes in order, and a table for the short ones
    unsigned codes[288];
    memset(c->count, 0, sizeof c->count);
    memset(c->table, 0, sizeof c->table);
    c->name = name;
    c->longest = 0;
    for (int i = 0; i < n; i++) {
        c->count[lengths[i]]++;
        if (lengths[i] > c->longest)
            c->longest = lengths[i];
    }
    long left = 1;                    /* bit patterns of the current length no code has taken */
    for (int len = 1; len <= HUFF_MAX_BITS; len++) {
        left = 2 * left - c->count[len];
        if (left < 0)
            return fail(s, "the %s code has more codes than its lengths allow", name);
    }
    /* Canonical: the codes of each length are consecutive from first[len],
     * in symbol order, so sym lists the symbols by length, then by symbol. */
    int code = 0, at = 0;
    c->count[0] = 0;
    for (int len = 1; len <= HUFF_MAX_BITS; len++) {
        code = (code + c->count[len - 1]) << 1;
        c->first[len] = code;
        c->index[len] = at;
        at += c->count[len];
    }
    int fill[HUFF_MAX_BITS + 1];
    memcpy(fill, c->index, sizeof fill);
    for (int i = 0; i < n; i++)
        if (lengths[i])
            c->sym[fill[lengths[i]]++] = (short)i;
    /* The table: a code of len <= 9 bits arrives first bit first, in the
     * lowest bit, so the 9 bits read at once end in it reversed, and the
     * bits after it can be anything: every one of those entries is it. */
    huff_codes(lengths, n, codes);
    for (int i = 0; i < n; i++) {
        int len = lengths[i];
        if (len == 0 || len > TABLE_BITS)
            continue;
        unsigned r = 0;
        for (int k = 0; k < len; k++)
            r |= ((codes[i] >> k) & 1) << (len - 1 - k);
        for (unsigned e = r; e < (1u << TABLE_BITS); e += 1u << len)
            c->table[e] = (unsigned short)(i << 4 | len);
    }
    return 0;
    // @end
}

/* --algo=bits: read a symbol a bit at a time. The bits so far, as a number,
 * are a code of this length if they are among the count[len] consecutive
 * codes that start at first[len]. */
static int decode_bits(State *s, const Code *c)
{
    // @build 09.02 read a code a bit at a time, until the bits so far are a code
    int code = 0;
    for (int len = 1; len <= HUFF_MAX_BITS; len++) {
        code = code << 1 | (int)bits(s, 1);
        st.walked++;
        int k = code - c->first[len];
        if (k >= 0 && k < c->count[len])
            return c->sym[c->index[len] + k];
    }
    return fail(s, "bits that are no %s code", c->name);
    // @end
}

/* --algo=table: the next 9 bits, looked up. A code that fits in them is
 * there with its length, and only that many bits are used up; a longer
 * code is read a bit at a time. */
static int decode_table(State *s, const Code *c)
{
    // @build 09.02 read a code with one look in the table, when it is a short one
    load(s, TABLE_BITS);
    unsigned e = c->table[s->bits & ((1u << TABLE_BITS) - 1)];
    st.lookups++;
    if (e != 0) {
        s->bits >>= e & 15;
        s->nbits -= (int)(e & 15);
        return (int)(e >> 4);
    }
    return decode_bits(s, c);
    // @end
}

/* The next symbol of code c, or -1 (with the message set). */
static int decode(State *s, const Code *c)
{
    st.symbols++;
    int sym = inflate_decoder == INFLATE_BITS ? decode_bits(s, c) : decode_table(s, c);
    if (cut_short(s))
        return fail(s, "the data ends in the middle of a block");
    return sym;
}

/* ------------------------------------------------------------ blocks */

/* Type 0: the bytes as they are, after the next byte boundary: LEN in two
 * bytes, NLEN (its ones' complement, a check), then LEN bytes. */
static int stored(State *s)
{
    // @build 09.02 a stored block: LEN bytes as they are
    /* Drop the bits up to the byte boundary, and give back the whole bytes
     * still loaded: from here on it is bytes, not bits. */
    s->bits >>= s->nbits % 8;
    s->nbits -= s->nbits % 8;
    s->pos -= (size_t)s->nbits / 8;
    s->bits = 0;
    s->nbits = 0;
    if (s->pos > s->n || s->n - s->pos < 4)
        return fail(s, "the data ends in the middle of a block");
    const unsigned char *p = s->in + s->pos;
    unsigned len = p[0] | p[1] << 8, nlen = p[2] | p[3] << 8;
    if (len != (~nlen & 0xffff))
        return fail(s, "a stored block's length %u and its check %u do not match", len, nlen);
    s->pos += 4;
    if (len > s->n - s->pos)
        return fail(s, "a stored block of %u bytes, but the data ends after %zu", len, s->n - s->pos);
    for (unsigned i = 0; i < len; i++)
        *(unsigned char *)array_push(s->out) = s->in[s->pos + i];
    s->pos += len;
    return 0;
    // @end
}

/* The symbols of a block, until its end: literals, and matches to copy. */
static int codes(State *s, const Code *lit, const Code *dist)
{
    // @build 09.02 the symbols of a block: a literal, or a length and a distance to copy from, until 256
    Array *out = s->out;
    for (;;) {
        int sym = decode(s, lit);
        if (sym < 0)
            return -1;
        if (sym < 256) {
            if (tracing()) {
                unsigned char b = (unsigned char)sym;
                fprintf(stderr, "trace: inflate: %zu: literal ", out->len);
                trace_bytes(&b, 1);
            }
            *(unsigned char *)array_push(out) = (unsigned char)sym;
            continue;
        }
        if (sym == 256)
            return 0;
        sym -= 257;
        if (sym >= 29)
            return fail(s, "length code %d, which DEFLATE does not use", sym + 257);
        unsigned len = deflate_length_base[sym] + bits(s, deflate_length_extra[sym]);
        int d = decode(s, dist);
        if (d < 0)
            return -1;
        if (d >= 30)
            return fail(s, "distance code %d, which DEFLATE does not use", d);
        unsigned back = deflate_dist_base[d] + bits(s, deflate_dist_extra[d]);
        if (cut_short(s))
            return fail(s, "the data ends in the middle of a block");
        if (back > out->len)
            return fail(s, "a match %u bytes back, but only %zu bytes have been written", back, out->len);
        /* Byte by byte, from the output itself: a match may overlap the
         * bytes it is writing ("ab" then 6 back 2 is "abababab"). */
        size_t at = out->len;
        for (unsigned i = 0; i < len; i++) {
            unsigned char b = (unsigned char)out->data[out->len - back];
            *(unsigned char *)array_push(out) = b;
        }
        if (tracing()) {
            fprintf(stderr, "trace: inflate: %zu: match distance %u length %u ", at, back, len);
            trace_bytes((unsigned char *)out->data + at, len);
        }
    }
    // @end
}

/* Type 1: the fixed codes, built the first time one is needed. */
static int fixed(State *s)
{
    // @build 09.02 a block in the fixed codes
    static Code lit, dist;
    static int ready;
    if (!ready) {
        unsigned char l[288], d[32];
        deflate_fixed_lengths(l, d);
        build(s, &lit, l, 288, "literal/length");
        build(s, &dist, d, 32, "distance");
        ready = 1;
    }
    return codes(s, &lit, &dist);
    // @end
}

/* The order the code-length code's lengths come in (RFC 1951, 3.2.7): the
 * ones most blocks use first, so the zeros at the end can be left out. */
const unsigned char deflate_clen_order[19] = {16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15};

/* Type 2: the block's own codes first. HLIT, HDIST and HCLEN say how many
 * literal/length, distance and code-length lengths follow; the
 * code-length code's lengths come as 3-bit numbers, and the other two
 * codes' lengths in that code, with 16, 17 and 18 for runs. */
static int dynamic(State *s)
{
    // @build 09.02 a block in its own codes: read the code lengths, themselves in a code
    size_t start = s->pos * 8 - (size_t)s->nbits;
    int nlit = (int)bits(s, 5) + 257, ndist = (int)bits(s, 5) + 1, nclen = (int)bits(s, 4) + 4;
    if (nlit > 286)
        return fail(s, "a block with %d literal/length codes; DEFLATE has 286", nlit);
    if (ndist > 30)
        return fail(s, "a block with %d distance codes; DEFLATE has 30", ndist);
    unsigned char clen[19] = {0}, lengths[286 + 30];
    for (int i = 0; i < nclen; i++)
        clen[deflate_clen_order[i]] = (unsigned char)bits(s, 3);
    if (cut_short(s))
        return fail(s, "the data ends in the middle of a block");
    Code cl, lit, dist;
    if (build(s, &cl, clen, 19, "code-length") < 0)
        return -1;
    for (int i = 0; i < nlit + ndist;) {
        int sym = decode(s, &cl);
        if (sym < 0)
            return -1;
        if (sym < 16) {
            lengths[i++] = (unsigned char)sym;
            continue;
        }
        int value = 0, repeat;
        if (sym == 16) {
            if (i == 0)
                return fail(s, "a repeat of the code length before, with none before it");
            value = lengths[i - 1];
            repeat = 3 + (int)bits(s, 2);
        } else if (sym == 17) {
            repeat = 3 + (int)bits(s, 3);
        } else {
            repeat = 11 + (int)bits(s, 7);
        }
        if (i + repeat > nlit + ndist)
            return fail(s, "code lengths that run past the %d the block says", nlit + ndist);
        while (repeat-- > 0)
            lengths[i++] = (unsigned char)value;
    }
    if (cut_short(s))
        return fail(s, "the data ends in the middle of a block");
    if (lengths[256] == 0)
        return fail(s, "a block with no code for its end (256)");
    if (build(s, &lit, lengths, nlit, "literal/length") < 0 ||
        build(s, &dist, lengths + nlit, ndist, "distance") < 0)
        return -1;
    if (tracing())
        fprintf(stderr, "trace: inflate: block %d: dynamic%s, header %zu bits, %d literal/length codes "
                "(longest %d bits), %d distance codes (longest %d bits)\n", s->block,
                s->last ? " (last)" : "", s->pos * 8 - (size_t)s->nbits - start,
                nlit, lit.longest, ndist, dist.longest);
    return codes(s, &lit, &dist);
    // @end
}

const char *inflate_raw(const unsigned char *in, size_t n, Array *out, size_t *used)
{
    // @build 09.02 the blocks, one after another, until the one marked last
    State s = {in, n, 0, 0, 0, out, 0, 0};
    ds_stats_at_exit(print_stats);
    do {
        size_t start = s.pos * 8 - (size_t)s.nbits, before = out->len;
        s.last = (int)bits(&s, 1);
        int type = (int)bits(&s, 2), r;
        s.block++;
        if (cut_short(&s)) {
            fail(&s, "the data ends before its last block");
            return message;
        }
        if (tracing() && type != 2)
            fprintf(stderr, "trace: inflate: block %d: %s%s\n", s.block,
                    type == 0 ? "stored" : type == 1 ? "fixed" : "type 3", s.last ? " (last)" : "");
        if (type == 0) {
            st.stored++;
            r = stored(&s);
        } else if (type == 1) {
            st.fixed++;
            r = fixed(&s);
        } else if (type == 2) {
            st.dynamic++;
            r = dynamic(&s);
        } else {
            r = fail(&s, "a block of type 3, which DEFLATE reserves");
        }
        if (r < 0)
            return message;
        if (tracing())
            fprintf(stderr, "trace: inflate: end of block %d: %zu bits, %zu bytes\n", s.block,
                    s.pos * 8 - (size_t)s.nbits - start, out->len - before);
    } while (!s.last);
    *used = (s.pos * 8 - (size_t)s.nbits + 7) / 8;
    return NULL;
    // @end
}
