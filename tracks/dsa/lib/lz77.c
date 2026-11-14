/*
 * lz77.c - finding repeats: at each place in the input, the longest run of
 * bytes that also starts somewhere in the 32 KB before it.
 *
 * The parse is greedy: take the longest match at the current place (if it
 * is at least 3 bytes), or else one literal byte, and move on past it.
 * The work is in finding that match. The obvious way tries every earlier
 * place in the window, up to 32768 of them, for every byte of the input
 * (match_scan). But a match of 3 bytes or more can only start where the
 * same three bytes were before, and a hash table of three-byte strings
 * keeps those places: for each hash, a chain of the places with it,
 * newest first (match_hash). Following a chain tries a few places instead
 * of thousands, and the nearest first, whose distance takes the fewest
 * bits. A chain of a common string can still be long, so it is cut after
 * chain places: the match found may then be a little shorter.
 */
#include <stdlib.h>
#include <string.h>

#include "lz77.h"

#define HASH_BITS 15
#define HASH_SIZE (1 << HASH_BITS)

static struct {
    long literals, matches, matched, candidates, comparisons, cut;
} st;

static void print_stats(void)
{
    ds_stats_print("lz77", "literals %ld, matches %ld, match bytes %ld, candidates %ld, comparisons %ld, "
                   "chains cut %ld", st.literals, st.matches, st.matched, st.candidates, st.comparisons, st.cut);
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

void lz77_init(Lz77 *z, const unsigned char *in, size_t n, int algo, int chain)
{
    z->in = in;
    z->n = n;
    z->pos = 0;
    z->algo = algo;
    z->chain = chain;
    z->head = z->prev = NULL;
    z->hashed = 0;
    if (algo == LZ77_HASH) {
        z->head = xmalloc(HASH_SIZE * sizeof *z->head);
        z->prev = xmalloc(LZ77_WINDOW * sizeof *z->prev);
        for (size_t i = 0; i < HASH_SIZE; i++)
            z->head[i] = -1;
        for (size_t i = 0; i < LZ77_WINDOW; i++)
            z->prev[i] = -1;
    }
    ds_stats_at_exit(print_stats);
}

void lz77_free(Lz77 *z)
{
    free(z->head);
    free(z->prev);
    z->head = z->prev = NULL;
}

/* How many bytes from "from" on are the same as from pos on, up to max. */
static int match_length(const Lz77 *z, size_t from, size_t pos, size_t max)
{
    size_t k = 0;
    while (k < max) {
        st.comparisons++;
        if (z->in[from + k] != z->in[pos + k])
            break;
        k++;
    }
    return (int)k;
}

/* The most a match at pos can be: 258 bytes, or what is left of the input. */
static size_t longest_possible(const Lz77 *z, size_t pos)
{
    return z->n - pos < LZ77_MAX ? z->n - pos : LZ77_MAX;
}

/* --algo=scan: the longest match for the bytes at pos, trying every place
 * in the window, nearest first. Its length (0 if it is under 3 bytes), and
 * its distance in *dist; of two as long, the nearer. */
static int match_scan(Lz77 *z, size_t pos, unsigned *dist)
{
    // @build 09.03 the longest match: try every place in the window
    size_t max = longest_possible(z, pos);
    size_t far = pos < LZ77_WINDOW ? pos : LZ77_WINDOW;
    int best = 0;
    if (max < LZ77_MIN)
        return 0;
    for (size_t d = 1; d <= far; d++) {
        st.candidates++;
        int len = match_length(z, pos - d, pos, max);
        if (len > best) {
            best = len;
            *dist = (unsigned)d;
            if ((size_t)len == max)
                break;
        }
    }
    return best >= LZ77_MIN ? best : 0;
    // @end
}

/* Which chain the three bytes at p go in. Multiplying by a large odd
 * number stirs all 24 bits into the top ones, and the top 15 are kept. */
static unsigned hash3(const unsigned char *p)
{
    uint32_t x = (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16;
    return (x * 2654435761u) >> (32 - HASH_BITS);
}

/* Put place p at the head of its chain: what was there comes after it. */
static void insert(Lz77 *z, size_t p)
{
    // @build 09.03 a place into the hash table: at the head of its chain
    unsigned h = hash3(z->in + p);
    z->prev[p % LZ77_WINDOW] = z->head[h];
    z->head[h] = (long)p;
    // @end
}

/* --algo=hash: the longest match for the bytes at pos among the places
 * with the same hash, nearest first, trying at most z->chain of them. */
static int match_hash(Lz77 *z, size_t pos, unsigned *dist)
{
    // @build 09.03 the longest match: try only the places on the chain of the same three bytes
    size_t max = longest_possible(z, pos);
    if (max < LZ77_MIN)
        return 0;
    /* Every place before pos goes in first: those a match skipped over too.
     * pos itself goes in afterwards, so the chain read here holds only
     * earlier places, and prev[] of a place in the window is still its own. */
    for (; z->hashed < pos; z->hashed++)
        insert(z, z->hashed);
    int best = 0, tries = 0;
    long cand = z->head[hash3(z->in + pos)];
    while (cand >= 0 && pos - (size_t)cand <= LZ77_WINDOW) {
        if (z->chain > 0 && tries == z->chain) {
            st.cut++;
            break;
        }
        tries++;
        st.candidates++;
        int len = match_length(z, (size_t)cand, pos, max);
        if (len > best) {
            best = len;
            *dist = (unsigned)(pos - (size_t)cand);
            if ((size_t)len == max)
                break;
        }
        cand = z->prev[cand % LZ77_WINDOW];
    }
    return best >= LZ77_MIN ? best : 0;
    // @end
}

size_t lz77_parse(Lz77 *z, Lz77Token *t, size_t max)
{
    // @build 09.03 the parse: at each place the longest match, or a literal when there is none
    size_t k = 0;
    while (k < max && z->pos < z->n) {
        unsigned dist = 0;
        int len = z->algo == LZ77_HASH ? match_hash(z, z->pos, &dist)
                : z->algo == LZ77_SCAN ? match_scan(z, z->pos, &dist) : 0;
        if (len > 0) {
            t[k].len = (unsigned short)len;
            t[k].dist = (unsigned short)dist;
            st.matches++;
            st.matched += len;
        } else {
            len = 1;
            t[k].len = z->in[z->pos];
            t[k].dist = 0;
            st.literals++;
        }
        if (tracing()) {
            if (t[k].dist)
                fprintf(stderr, "trace: lz77: %zu: match distance %u length %d ", z->pos, dist, len);
            else
                fprintf(stderr, "trace: lz77: %zu: literal ", z->pos);
            trace_bytes(z->in + z->pos, (size_t)len);
        }
        z->pos += (size_t)len;
        k++;
    }
    return k;
    // @end
}
