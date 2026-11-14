/*
 * huffman.h - Huffman codes: the shortest prefix code for symbols whose
 * counts are known, in the canonical form DEFLATE stores (RFC 1951, 3.2.2).
 *
 * A code is given by its lengths: lengths[s] is how many bits symbol s's
 * code takes, 0 for a symbol that never occurs. The codes themselves
 * follow from the lengths by a fixed rule (huff_codes), so a compressed
 * file stores only the lengths and its reader rebuilds the same codes.
 *
 * DS_STATS=1 prints "stats: huffman: trees T, joins J, rebuilds R": the
 * trees built, the joins of two nodes they took, and how many times a tree
 * was built again because a code came out longer than a limit allows.
 * DS_TRACE=1 prints each tree as it is built, a line per join:
 *
 *   trace: huffman: tree of 5 symbols
 *   trace: huffman: join 'c' 1 + 'd' 1 = n1 2
 *
 * a symbol as 'c' when it is a printable character, else as its number;
 * n1, n2, ... are the joins in the order they were made, each with its
 * count, the sum of the two below it.
 */
#ifndef HUFFMAN_H
#define HUFFMAN_H

#include "ds.h"

#define HUFF_MAX_BITS 15      /* the longest code DEFLATE can store */
#define HUFF_MAX_CODE 32      /* the longest code huff_codes() will number */

/* The code lengths of the n symbols whose counts are counts[0..n): Huffman's
 * tree, built with the heap by joining the two rarest trees until one is
 * left; a symbol's length is its depth in that tree. A symbol with count 0
 * gets length 0; one symbol alone gets a code of 1 bit. Returns the
 * longest length (0 when no symbol occurs). */
int huff_lengths(const long *counts, int n, unsigned char *lengths);

/* The same with no code longer than maxbits: while the tree is too deep,   @from 09.04
 * halve every count (keeping each above 0) and build it again.             @from 09.04
 * maxbits must be enough for every symbol used to have a code of its own.  @from 09.04
 */                                                                          // @from 09.04
int huff_lengths_limited(const long *counts, int n, int maxbits, unsigned char *lengths);   // @from 09.04

/* The canonical code for those lengths, in codes[0..n): the codes of each
 * length are consecutive numbers, given out in the order of the symbols,
 * and every shorter code comes before every longer one. codes[s] is to be
 * read from its highest bit: lengths[s] bits of it. No length may be over
 * HUFF_MAX_CODE, and the lengths must not ask for more codes of some length
 * than there are bit patterns for (as Huffman's lengths never do). */
void huff_codes(const unsigned char *lengths, int n, unsigned *codes);

#endif
