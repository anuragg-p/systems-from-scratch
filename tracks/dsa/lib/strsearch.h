/*
 * strsearch.h - finding a fixed string in a text (grep -F, lesson 04.01).
 *
 *   search_scan       try the pattern at every position of the text
 *   search_horspool   compare from the pattern's last byte, and on a
 *                     mismatch skip ahead as far as the byte of the text
 *                     under that last byte allows (Horspool, 1980)
 *
 * DS_STATS=1 prints "stats: search: positions P, examined E, skipped K":
 * the positions the pattern was tried at, the bytes of text compared, and
 * the positions passed over without being tried.
 *
 * DS_TRACE=1 prints one line on stderr for each position tried:
 *   trace: scan: at P: examined K, match
 *   trace: scan: at P: examined K, mismatch at J, shift 1
 *   trace: horspool: at P: examined K, mismatch at J, 'c' under the last byte, shift S
 * P is the offset in the text of the pattern's first byte, K the bytes
 * compared there, J the offset in the pattern of the byte that differed,
 * and c the byte of the text under the pattern's last byte, which picks S.
 */
#ifndef STRSEARCH_H
#define STRSEARCH_H

#include <stddef.h>

/* A fixed string, ready to be searched for. With icase, the pattern is
 * kept in lower case and map folds each byte of the text to lower case
 * before it is compared; without, map leaves every byte as it is. */
typedef struct {
    unsigned char *pat;
    size_t len;
    unsigned char map[256];
    size_t shift[256];    /* Horspool: how far to move on, by the byte under the last one */
} Search;

void search_init(Search *s, const char *pat, size_t len, int icase);
void search_free(Search *s);

/* The first place in text[0..n) where the pattern is, or NULL. */
const char *search_scan(const Search *s, const char *text, size_t n);
const char *search_horspool(const Search *s, const char *text, size_t n);

#endif
