/*
 * lz77.h - finding repeats: the input as literal bytes and matches, each
 * match a (distance, length) pair that says "the next length bytes are
 * the ones distance bytes back" (Ziv and Lempel, 1977).
 *
 * DS_STATS=1 prints "stats: lz77: literals L, matches M, match bytes B,
 * candidates C, comparisons K, chains cut X": the tokens of each kind, the
 * bytes the matches stand for, the earlier places tried as the start of a
 * match, the bytes compared doing it, and the searches the chain bound
 * stopped early.
 * DS_TRACE=1 prints each token as it is found, with where it starts:
 *
 *   trace: lz77: 0: literal "a"
 *   trace: lz77: 7: match distance 7 length 4 "abra"
 */
#ifndef LZ77_H
#define LZ77_H

#include "ds.h"

#define LZ77_WINDOW 32768     /* how far back a match may point */
#define LZ77_MIN 3            /* the shortest match worth a pointer */
#define LZ77_MAX 258          /* the longest one DEFLATE can say */

/* How to look for the longest match at each place:
 *   LZ77_HASH  only at the earlier places that start with the same three
 *              bytes, which a hash table of chains lists, nearest first
 *   LZ77_SCAN  at every place in the window
 *   LZ77_NONE  nowhere: every byte a literal (Huffman codes alone) */
enum { LZ77_HASH, LZ77_SCAN, LZ77_NONE };

/* One step of the parse: a literal byte (dist 0, len the byte), or a match
 * of len bytes (3..258) from dist bytes back (1..32768). */
typedef struct {
    unsigned short len;
    unsigned short dist;
} Lz77Token;

/* A parse in progress over in[0..n), all of it in memory. */
typedef struct {
    const unsigned char *in;
    size_t n;
    size_t pos;           /* the parse has got this far */
    int algo;
    int chain;            /* LZ77_HASH: the most places to try for one match; 0 for no limit */
    long *head;           /* LZ77_HASH: hash of three bytes -> the last place they were seen, or -1 */
    long *prev;           /* place % LZ77_WINDOW -> the place before it with the same hash, or -1 */
    size_t hashed;        /* the places before this one are in the chains */
} Lz77;

void   lz77_init(Lz77 *z, const unsigned char *in, size_t n, int algo, int chain);
/* The next tokens of the parse, at most max of them, into t: how many; 0
 * once the whole input is parsed. */
size_t lz77_parse(Lz77 *z, Lz77Token *t, size_t max);
void   lz77_free(Lz77 *z);

#endif
