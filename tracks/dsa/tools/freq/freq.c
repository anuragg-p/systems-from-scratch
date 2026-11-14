/*
 * freq - the most common words in a text.
 *
 *   freq [-n N] [option ...] [file ...]
 *
 * A word is a run of the letters A-Z and a-z, lowercased; anything else
 * only separates words. freq prints the N most common words (10 unless -n
 * says otherwise; -n 0 prints every word), most common first, each as its
 * count and the word. Words with the same count come in reverse byte
 * order, where the shell pipeline freq replaces leaves them, so the two
 * print the same counts and words in the same order:
 *
 *   tr -cs A-Za-z '\n' | tr A-Z a-z | sort | uniq -c | sort -rn | head -n N
 *                                                                      @from 01.02
 * The options choose how freq does its work; the answer is the same.  @from 01.02
 * --algo=NAME: how a word is found among the words counted so far:    @from 01.02
 *   list    look at each of them in turn                               @from 01.02
 *   table   ask a hash table where it is (the default)                 @from 01.02
 * --hash=NAME: the table's hash function, fnv1a (the default) or sum   @from 01.03
 * --no-grow: keep the table at the 1024 buckets it starts with         @from 01.03
 * --top=NAME: how the N most common are picked out:                    @from 02.04
 *   select  N passes over all the words, each taking the best left     @from 02.04
 *   heap    one pass, keeping the best N so far in a heap (the default)  @from 02.04
 *
 * DS_STATS=1 prints, besides the structures' own lines, "stats: freq:
 * words W, distinct D, list probes L, rank comparisons R": the words
 * read, how many were different, how many words the search of the list
 * looked at, and how many times two words were compared to rank them.
 */
#include <stdlib.h>
#include <string.h>

#include "ds.h"

typedef struct {
    char  *word;          /* lowercase, with a NUL after it */
    size_t len;
    long   count;
} Word;

static Array words;       /* Word, in the order each was first seen */
static Table table;       /* a word -> where it is in words */   // @from 01.02

static long nwords, list_probes, rank_comparisons;

static void print_stats(void)
{
    ds_stats_print("freq", "words %ld, distinct %zu, list probes %ld, rank comparisons %ld",
                   nwords, words.len, list_probes, rank_comparisons);
}

static int is_letter(int c)
{
    return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z');
}

/* The next word of f, lowercased, in buf (an Array of char, with no NUL
 * after it): 1, or 0 at the end of the input. A word can be as long as
 * the input: buf grows with it. */
static int next_word(FILE *f, Array *buf)
{
    // @build 01.01 read a word, a letter at a time
    int c;
    array_clear(buf);
    while ((c = getc(f)) != EOF && !is_letter(c))
        ;
    if (c == EOF)
        return 0;
    do {
        *(char *)array_push(buf) = (char)(c >= 'A' && c <= 'Z' ? c - 'A' + 'a' : c);
    } while ((c = getc(f)) != EOF && is_letter(c));
    return 1;
    // @end
}

/* A word not seen before goes at the end of words, counted once. */
static void add_word(const char *w, size_t len)
{
    Word *x = array_push(&words);
    x->word = xstrndup(w, len);
    x->len = len;
    x->count = 1;
}

/* --algo=list: count a word by looking at every word seen so far. */
static void count_list(const char *w, size_t len)
{
    // @build 01.01 count a word: look at every word so far
    for (size_t i = 0; i < words.len; i++) {
        Word *x = array_at(&words, i);
        list_probes++;
        if (x->len == len && memcmp(x->word, w, len) == 0) {
            x->count++;
            return;
        }
    }
    add_word(w, len);
    // @end
}

/* --algo=table: count a word by asking the table where it is in words. */
static void count_table(const char *w, size_t len)
{
    // @build 01.02 count a word: ask the table
    long *at = table_get(&table, w, len);
    if (at != NULL) {
        ((Word *)array_at(&words, (size_t)*at))->count++;
        return;
    }
    *table_put(&table, w, len) = (long)words.len;
    add_word(w, len);
    // @end
}

/* Which of two words ranks higher: more than 0 when a does. The higher
 * count wins; on equal counts, the word that is bigger byte by byte, as
 * "sort -rn" orders lines with equal numbers. A Cmp, so a heap can use it. */
static int rank(const void *a, const void *b, void *ctx)
{
    const Word *x = a, *y = b;
    rank_comparisons++;
    if (x->count != y->count)
        return x->count < y->count ? -1 : 1;
    size_t n = x->len < y->len ? x->len : y->len;
    int c = memcmp(x->word, y->word, n);
    if (c != 0)
        return c;
    return x->len < y->len ? -1 : x->len > y->len;
}

/* --top=select: the n best words into best[0..n), best first: n passes over
 * all the words, each taking the best one not taken yet. */
static void top_select(size_t n, Word **best)
{
    // @build 01.01 the top n: n passes, each taking the best word left
    char *taken = xmalloc(words.len);
    memset(taken, 0, words.len);
    for (size_t k = 0; k < n; k++) {
        size_t at = 0;
        Word *b = NULL;
        for (size_t i = 0; i < words.len; i++) {
            Word *w = array_at(&words, i);
            if (!taken[i] && (b == NULL || rank(w, b, NULL) > 0)) {
                b = w;
                at = i;
            }
        }
        taken[at] = 1;
        best[k] = b;
    }
    free(taken);
    // @end
}

/* --top=heap: one pass over the words, keeping the best n so far in a heap
 * with the worst of them on top. A word better than that one takes its
 * place; most words are not, and cost one comparison. */
static void top_heap(size_t n, Word **best)
{
    // @build 02.04 the top n: the best so far in a heap, the worst of them on top
    Heap h;
    heap_init(&h, rank, NULL);
    for (size_t i = 0; i < words.len; i++) {
        Word *w = array_at(&words, i);
        if (heap_len(&h) < n) {
            heap_push(&h, w);
        } else if (rank(w, heap_top(&h), NULL) > 0) {
            heap_pop(&h);
            heap_push(&h, w);
        }
    }
    for (size_t k = heap_len(&h); k > 0; k--)
        best[k - 1] = heap_pop(&h);
    heap_free(&h);
    // @end
}

// @from 01.02
/* The value of --name=value, which must be one of names. */
static const char *pick(const char *name, const char *value, const char *const *names)
{
    char have[200] = "";
    for (int i = 0; names[i]; i++) {
        if (strcmp(value, names[i]) == 0)
            return names[i];
        strcat(strcat(have, i ? ", " : ""), names[i]);
    }
    die("no %s '%s' (have: %s)", name, value, have);
}
// @end

static const char *const algos[] = {"list", "table", NULL};      // @from 01.02
static const char *const hashes[] = {"fnv1a", "sum", NULL};      // @from 01.03
static const char *const tops[] = {"select", "heap", NULL};      // @from 02.04

static void usage(void)
{
    die("usage: freq [-n N] [option ...] [file ...]");
}

int main(int argc, char **argv)
{
    progname = "freq";
    ds_stats_at_exit(print_stats);
    long n = 10;
    const char *algo = "table";   // @from 01.02
    const char *top = "heap";     // @from 02.04
    // @from 01.03
    const char *hash = "fnv1a";
    int no_grow = 0;
    // @end
    int i;
    for (i = 1; i < argc; i++) {
        const char *a = argv[i];
        if (strcmp(a, "-n") == 0 || (strncmp(a, "-n", 2) == 0 && a[2])) {
            const char *v = a[2] ? a + 2 : (i + 1 < argc ? argv[++i] : "");
            char *end;
            n = strtol(v, &end, 10);
            if (*v == '\0' || *end != '\0' || n < 0)
                die("-n wants a count of words, 0 for all of them, not '%s'", v);
            continue;
        }
        // @from 01.02
        if (strncmp(a, "--algo=", 7) == 0) {
            algo = pick("--algo", a + 7, algos);
            continue;
        }
        // @end
        // @from 01.03
        if (strncmp(a, "--hash=", 7) == 0) {
            hash = pick("--hash", a + 7, hashes);
            continue;
        }
        if (strcmp(a, "--no-grow") == 0) {
            no_grow = 1;
            continue;
        }
        // @end
        // @from 02.04
        if (strncmp(a, "--top=", 6) == 0) {
            top = pick("--top", a + 6, tops);
            continue;
        }
        // @end
        if (strcmp(a, "--") == 0) {
            i++;
            break;
        }
        if (a[0] == '-' && a[1] != '\0') {
            if (a[1] == '-')
                die("unknown option '%s'", a);
            usage();
        }
        break;
    }

    array_init(&words, sizeof(Word));
    // @from 01.02
    int use_table = strcmp(algo, "table") == 0;
    if (use_table)
        table_init(&table);
    // @end
    // @from 01.03
    table.hash = strcmp(hash, "sum") == 0 ? hash_sum : hash_fnv1a;
    table.no_grow = no_grow;
    // @end
    Array buf;
    array_init(&buf, 1);
    int nfiles = argc - i;
    for (int f = 0; f < (nfiles ? nfiles : 1); f++) {
        FILE *in = open_input(nfiles ? argv[i + f] : NULL);
        while (next_word(in, &buf)) {
            nwords++;
            // @from 01.02
            if (use_table)
                count_table(buf.data, buf.len);
            else
                count_list(buf.data, buf.len);
            // @else
            // count_list(buf.data, buf.len);
            // @end
        }
        close_input(in);
    }

    size_t k = n == 0 || (size_t)n > words.len ? words.len : (size_t)n;
    Word **best = xmalloc((k ? k : 1) * sizeof *best);
    // @from 02.04
    if (strcmp(top, "heap") == 0)
        top_heap(k, best);
    else
        top_select(k, best);
    // @else
    // top_select(k, best);
    // @end
    for (size_t j = 0; j < k; j++)
        printf("%7ld %s\n", best[j]->count, best[j]->word);
    free(best);
    return ferror(stdout) ? 2 : 0;
}
