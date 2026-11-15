/*
 * re.h - a regular expression as a tree (grep -E, lesson 04.02), and
 * the obvious way to match one: backtracking over the tree.
 *
 * The dialect is grep -E's (POSIX extended), in the C locale:
 *   c          a byte stands for itself; \c too, for c not a letter or digit
 *   .          any byte
 *   [abc]      one of the bytes in the brackets: ranges (a-z), classes
 *   [^abc]     ([:alpha:] [:digit:] [:alnum:] [:upper:] [:lower:]
 *              [:space:] [:blank:] [:punct:] [:print:] [:graph:]
 *              [:cntrl:] [:xdigit:]), and ] first or - first or last
 *              for themselves; ^ first: any byte but these
 *   ^ $        the start and the end of the line
 *   (r)        r
 *   r*  r+  r? r any number of times, once or more, at most once
 *   rs         r and then s
 *   r|s        r or s
 * and an ordinary error (status 2) for what is not supported: intervals
 * ({2,3}), back references and the other \ escapes, [. .] and [= =].
 * A ) with no ( before it stands for itself, as POSIX says.
 *
 * DS_STATS=1 prints "stats: regex: nodes N", the size of the tree, and,
 * for the backtracking matcher, "stats: backtrack: steps S, examined E,
 * deepest D": the nodes it visited, the bytes of text it compared, and
 * the most calls it was ever nested in.
 *
 * DS_TRACE=1 prints, while backtracking, one line for each start:
 *   trace: backtrack: start at I
 * for each byte compared, or the end of the line where one was wanted:
 *   trace: backtrack: at I: 'c' against R: yes|no
 *   trace: backtrack: at I: the end against R: no
 * and for each time it goes back to take the other way at a choice:
 *   trace: backtrack: back at I: R, the other way
 * where R is the part of the pattern a node was parsed from.
 */
#ifndef RE_H
#define RE_H

#include <stddef.h>

typedef enum {
    RE_CHAR,     /* one byte, out of set: a literal, ., or a bracket expression */
    RE_BOL,      /* ^ */
    RE_EOL,      /* $ */
    RE_EMPTY,    /* nothing: () */
    RE_CAT,      /* left, then right */
    RE_ALT,      /* left or right */
    RE_STAR,     /* left, any number of times */
    RE_PLUS,     /* left, once or more */
    RE_QUEST     /* left, or nothing */
} ReOp;

typedef struct Re {
    ReOp op;
    struct Re *left, *right;
    unsigned char set[32];    /* RE_CHAR: bit c is set for each byte c it matches */
    const char *src;          /* the part of the pattern it was parsed from */
    int srclen;
} Re;

/* The tree of the len bytes at pattern. With icase, every letter, in a
 * class or not, matches both its cases. A pattern that is not one is
 * fatal, with a message saying why. The tree points into pattern, which
 * must outlive it. */
Re *re_parse(const char *pattern, size_t len, int icase);
void re_free(Re *re);

/* Does byte c belong to set? */
static inline int re_has(const unsigned char *set, unsigned char c)
{
    return set[c >> 3] & (1 << (c & 7));
}

/* Is re found anywhere in the line s[0..n) (with no newline in it)? */
int re_backtrack(const Re *re, const char *s, size_t n);

// @from 04.03
// @from 04.04
/* DS_TRACE is set (for nfa.c and dfa.c too). */
// @else
// /* DS_TRACE is set (for nfa.c too). */
// @end
// @else
// /* DS_TRACE is set. */
// @end
int re_tracing(void);

#endif
