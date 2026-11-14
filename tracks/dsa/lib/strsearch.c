/*
 * strsearch.c - finding a fixed string in a text.
 *
 * The obvious search puts the pattern at the first byte of the text and
 * compares, then at the second, and so on: it tries every position. On
 * ordinary text most positions fail at the first byte, so it looks at
 * each byte of the text about once. It can never look at fewer.
 *
 * Horspool's search compares the pattern's last byte first. Whatever
 * byte of the text sits under it, the pattern cannot match until a byte
 * of the pattern that is the same comes over it: a byte the pattern does
 * not hold at all lets it jump its whole length. So a long pattern skips
 * most of the text without looking at it, and the longer the pattern,
 * the less of the text is read.
 *
 * Both are n*m in the worst case (m the pattern's length), on different
 * inputs: scan on "aaaab" in a run of a's, Horspool on "baaaa".
 */
#include <ctype.h>
#include <stdlib.h>
#include <string.h>

#include "ds.h"
#include "strsearch.h"

static struct {
    long positions, examined, skipped;
} st;

static void print_stats(void)
{
    ds_stats_print("search", "positions %ld, examined %ld, skipped %ld",
                   st.positions, st.examined, st.skipped);
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

/* A byte as a trace shows it: 'a', or '\n', or '\xNN'. */
static const char *shown(unsigned char c)
{
    static char buf[8];
    if (c == '\n')
        return "'\\n'";
    if (c == '\t')
        return "'\\t'";
    if (isprint(c) && c != '\'' && c != '\\')
        snprintf(buf, sizeof buf, "'%c'", c);
    else
        snprintf(buf, sizeof buf, "'\\x%02x'", c);
    return buf;
}

/* Keep a copy of the pattern (in lower case, with icase), and work out
 * Horspool's table. A byte that is not in the pattern, or only at its
 * end, moves the pattern on by its whole length; a byte that is moves it
 * just far enough to put the last such byte of the pattern under it. */
void search_init(Search *s, const char *pat, size_t len, int icase)
{
    // @build 04.01 the pattern, and how far each byte lets it move on
    for (int c = 0; c < 256; c++)
        s->map[c] = (unsigned char)(icase ? tolower(c) : c);
    s->pat = xmalloc(len);
    s->len = len;
    for (size_t i = 0; i < len; i++)
        s->pat[i] = s->map[(unsigned char)pat[i]];
    for (int c = 0; c < 256; c++)
        s->shift[c] = len;
    for (size_t i = 0; i + 1 < len; i++)
        s->shift[s->pat[i]] = len - 1 - i;
    ds_stats_at_exit(print_stats);
    // @end
}

void search_free(Search *s)
{
    free(s->pat);
}

/* Put the pattern at each position in turn and compare from its first
 * byte, until a byte differs or all of them are the same. */
const char *search_scan(const Search *s, const char *text, size_t n)
{
    // @build 04.01 try every position
    const unsigned char *t = (const unsigned char *)text;
    size_t m = s->len;
    if (m == 0)
        return text;
    for (size_t at = 0; at + m <= n; at++) {
        size_t j = 0;
        st.positions++;
        while (j < m) {
            st.examined++;
            if (s->map[t[at + j]] != s->pat[j])
                break;
            j++;
        }
        if (tracing()) {
            if (j == m)
                fprintf(stderr, "trace: scan: at %zu: examined %zu, match\n", at, j);
            else
                fprintf(stderr, "trace: scan: at %zu: examined %zu, mismatch at %zu, shift 1\n", at, j + 1, j);
        }
        if (j == m)
            return text + at;
    }
    return NULL;
    // @end
}

/* Compare from the pattern's last byte back to its first. On a mismatch,
 * the byte of the text under the last byte says how far to move on. */
const char *search_horspool(const Search *s, const char *text, size_t n)
{
    // @build 04.01 compare from the end, and skip ahead
    const unsigned char *t = (const unsigned char *)text;
    size_t m = s->len;
    if (m == 0)
        return text;
    size_t at = 0;
    while (at + m <= n) {
        size_t j = m;
        st.positions++;
        while (j > 0) {
            st.examined++;
            if (s->map[t[at + j - 1]] != s->pat[j - 1])
                break;
            j--;
        }
        if (j == 0) {
            if (tracing())
                fprintf(stderr, "trace: horspool: at %zu: examined %zu, match\n", at, m);
            return text + at;
        }
        unsigned char last = s->map[t[at + m - 1]];
        size_t shift = s->shift[last];
        if (tracing())
            fprintf(stderr, "trace: horspool: at %zu: examined %zu, mismatch at %zu, %s under the last byte, shift %zu\n",
                    at, m - j + 1, j - 1, shown(t[at + m - 1]), shift);
        /* positions passed over: those between here and where it lands,
         * but none past the last one the pattern fits at */
        size_t left = n - m - at;
        st.skipped += (long)(shift - 1 < left ? shift - 1 : left);
        at += shift;
    }
    return NULL;
    // @end
}
