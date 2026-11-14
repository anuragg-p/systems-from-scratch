/*
 * spell - the words of a text that are not in the dictionary.
 *
 *   spell [option ...] [file ...]      the unknown words, one to a line
 *   spell [option ...] -p PREFIX       the dictionary's words that start with PREFIX
 *   spell -s [option ...] [file ...]   each unknown word, and the words nearest to it  @from 05.03
 *   spell --distance WORD WORD         the edit distance between two words             @from 05.03
 *
 * A word of the text is a run of the letters A-Z and a-z, lowercased, as
 * freq reads them. Words of one letter are not checked ("a" and "I", and
 * the "s" and "t" of "Holmes's" and "don't"); aspell leaves them alone by
 * default too. Each unknown word is printed once, in byte order, as this
 * pipeline prints them:
 *
 *   tr -cs A-Za-z '\n' | tr A-Z a-z | grep .. | sort -u | comm -23 - DICTIONARY
 *
 * The dictionary is tools/spell/words.txt, 60388 words of English (12dicts'
 * 2of4brif list: tools/spell/NOTICE.txt), or the files -d names: a word to
 * a line, lowercased as it is read; a line with anything but letters on it
 * is not a word, and is left out.
 *
 *   -d FILE        a dictionary file to use instead (given again: all of them)
 *   -p PREFIX      complete PREFIX: every word of the dictionary that starts
 *                  with it (lowercased), in byte order, as look(1) prints
 *                  them from a sorted list; exit 1 if there is none
 *   --algo=NAME    what holds the dictionary:
 *     list         the words in an array; a lookup looks at them in turn
 *     table        the hash table of module 01
 *     trie         a trie (the default)
 *     bloom        a Bloom filter: a few bits a word. It never calls a      @from 05.02
 *                  word of the dictionary unknown, but lets about --fp      @from 05.02
 *                  of the unknown words through as known. It holds no       @from 05.02
 *                  words, so -p is refused                                  @from 05.02
 *                  (-s reads the dictionary again, into a trie for the     @from 05.03
 *                  suggestions, once there is a word to suggest them for)   @from 05.03
 *   --fp=P         the filter's false-positive rate (default 0.01)          @from 05.02
 *   --hashes=K     the filter's hashes (default: the best number for P)     @from 05.02
 *   -s             suggest: print each unknown word as "word: near ...",    @from 05.03
 *                  with the dictionary's words nearest to it: those at the  @from 05.03
 *                  smallest distance there is, up to -e, in byte order      @from 05.03
 *   -e N           ... no more than N edits away (default 2)                @from 05.03
 *   -n N           ... no more than N of them (default 5; 0: all)           @from 05.03
 *   --near=NAME    how they are found:                                      @from 05.03
 *     scan         the distance to every word of the dictionary             @from 05.03
 *     trie         a walk down the trie, leaving out each subtree with no  @from 05.03
 *                  word near enough (the default, but with --algo=list or   @from 05.03
 *                  table, which have no trie)                               @from 05.03
 *
 * DS_STATS=1 prints, before the structures' own lines, "stats: spell: words
 * W, checked C, unknown U, dict words D, dict text T, dict bytes B, scanned
 * S": the words of the text, how many were checked (two letters or more),
 * how many different ones were unknown, the words read from the dictionary
 * files, their size as text (a byte a letter, and one for each newline),
 * the bytes of memory the structure holding them takes by its own count,
 * and how many dictionary words a scan looked at (list lookups, and -p
 * without a trie). DS_TRACE=1 has the structures print their steps: see
 * the top of each one's file in lib/.
 */
#include <errno.h>
#include <stdlib.h>
#include <string.h>

#include "ds.h"
#include "trie.h"
#include "bloom.h"     // @from 05.02
#include "edit.h"      // @from 05.03

#define DICTIONARY "tools/spell/words.txt"

/* What holds the dictionary: --algo, an index into algos[]. */
enum {
    LIST,
    TABLE,
    TRIE,
    BLOOM,      // @from 05.02
};

typedef struct {
    char  *w;            /* lowercase, with a NUL after it */
    size_t len;
} DictWord;

static int algo = TRIE;
static Array list;       /* DictWord, as the files have them: --algo=list */
static Table table;      /* --algo=table */
static Trie trie;        /* --algo=trie */
static Bloom bloom;      /* --algo=bloom */      // @from 05.02
static Array dicts;      /* const char *: the dictionary files */
// @from 05.02
static double fp = 0.01; /* --fp: the filter's false-positive rate */
static int hashes;       /* --hashes; 0: the best number for fp */
// @end

static size_t dict_words, dict_text, nunknown;
static long nwords, checked, scanned;

static size_t dict_bytes(void);

static void print_stats(void)
{
    ds_stats_print("spell", "words %ld, checked %ld, unknown %zu, dict words %zu, dict text %zu, "
                   "dict bytes %zu, scanned %ld",
                   nwords, checked, nunknown, dict_words, dict_text, dict_bytes(), scanned);
}

static int is_letter(int c)
{
    return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z');
}

/* The len bytes at w lowercased in place: 1, or 0 if one is no letter. */
static int lower_word(char *w, size_t len)
{
    for (size_t i = 0; i < len; i++) {
        if (!is_letter((unsigned char)w[i]))
            return 0;
        if (w[i] >= 'A' && w[i] <= 'Z')
            w[i] = (char)(w[i] - 'A' + 'a');
    }
    return 1;
}

/* The next word of f, lowercased, in buf (an Array of char, with no NUL
 * after it): 1, or 0 at the end of the input. */
static int next_word(FILE *f, Array *buf)
{
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
}

/* Byte order, for sorting words (char *) with lib/sort.c. */
static int compare_words(const void *a, const void *b, void *ctx)
{
    return strcmp(a, b);
}

/* ------------------------------------------------------------ the dictionary */

/* Reads a dictionary file, a word to a line, and hands each word to add()
 * lowercased, without its newline (or a \r before it). A line with
 * anything but letters on it is no word, and is left out. */
static void read_dict(const char *path, void (*add)(const char *w, size_t len))
{
    FILE *f = fopen(path, "rb");
    if (f == NULL)
        die("%s: %s", path, strerror(errno));
    Array line;
    array_init(&line, 1);
    int c;
    do {
        array_clear(&line);
        while ((c = getc(f)) != EOF && c != '\n')
            *(char *)array_push(&line) = (char)c;
        if (line.len > 0 && line.data[line.len - 1] == '\r')
            line.len--;
        if (line.len > 0 && lower_word(line.data, line.len)) {
            dict_words++;
            dict_text += line.len + 1;
            add(line.data, line.len);
        }
    } while (c != EOF);
    array_free(&line);
    fclose(f);
}

static void add_list(const char *w, size_t len)
{
    DictWord *x = array_push(&list);
    x->w = xstrndup(w, len);
    x->len = len;
}

static void add_table(const char *w, size_t len)
{
    table_put(&table, w, len);
}

static void add_trie(const char *w, size_t len)
{
    trie_add(&trie, w, len);
}

// @from 05.02
static void add_none(const char *w, size_t len)
{
}

static void add_bloom(const char *w, size_t len)
{
    bloom_add(&bloom, w, len);
}
// @end

/* Every dictionary file into the structure --algo names. */
static void load(void)
{
    void (*add)(const char *, size_t) = add_trie;
    switch (algo) {
    case LIST:
        array_init(&list, sizeof(DictWord));
        add = add_list;
        break;
    case TABLE:
        table_init(&table);
        add = add_table;
        break;
    // @from 05.02
    case BLOOM:
        /* The filter's size depends on how many words it will hold: count
         * them first, then read the files again to add them. */
        for (size_t i = 0; i < dicts.len; i++)
            read_dict(*(const char **)array_at(&dicts, i), add_none);
        bloom_init(&bloom, dict_words, fp, hashes);
        dict_words = dict_text = 0;     /* counted again as they go in */
        add = add_bloom;
        break;
    // @end
    default:
        trie_init(&trie);
        break;
    }
    for (size_t i = 0; i < dicts.len; i++)
        read_dict(*(const char **)array_at(&dicts, i), add);
}

/* The memory the dictionary takes, by its structure's own count: the
 * blocks it asked for, room to spare included (not what malloc keeps for
 * itself around each one). */
static size_t dict_bytes(void)
{
    size_t n = 0;
    switch (algo) {
    case LIST:
        n = list.cap * list.size;
        for (size_t i = 0; i < list.len; i++)
            n += ((DictWord *)array_at(&list, i))->len + 1;
        return n;
    case TABLE:
        if (table.buckets == NULL)
            return 0;
        n = table.entries.cap * table.entries.size + table.nbuckets * sizeof(long);
        for (size_t i = 0; i < table_len(&table); i++)
            n += table_entry(&table, i)->len + 1;
        return n;
    case BLOOM:                        // @from 05.02
        return bloom_bytes(&bloom);    // @from 05.02
    default:
        return trie.nodes.size ? trie_bytes(&trie) : 0;
    }
}

/* --algo=list: is w a word of the dictionary? Each word is looked at in
 * turn, from the first, until one is w: every word, when it is not there. */
static int list_has(const char *w, size_t len)
{
    // @build 05.01 a lookup in the list: look at each word in turn
    for (size_t i = 0; i < list.len; i++) {
        DictWord *x = array_at(&list, i);
        scanned++;
        if (x->len == len && memcmp(x->w, w, len) == 0)
            return 1;
    }
    return 0;
    // @end
}

static int known(const char *w, size_t len)
{
    switch (algo) {
    case LIST:
        return list_has(w, len);
    case TABLE:
        return table_get(&table, w, len) != NULL;
    case BLOOM:                                  // @from 05.02
        return bloom_test(&bloom, w, len);       // @from 05.02
    default:
        return trie_has(&trie, w, len);
    }
}

/* ------------------------------------------------------------ -p: completing a prefix */

/* -p with a list or a table: look at every word, keep those that start
 * with prefix, and sort them (the list is in the files' order, which -d
 * may not keep sorted; the table is in no order at all). The number of
 * words printed. */
static size_t complete_scan(const char *prefix, size_t len)
{
    // @build 05.01 complete a prefix the slow way: look at every word, sort the ones that match
    Array match;
    array_init(&match, sizeof(char *));
    size_t n = algo == LIST ? list.len : table_len(&table);
    for (size_t i = 0; i < n; i++) {
        char *w;
        size_t wlen;
        if (algo == LIST) {
            DictWord *x = array_at(&list, i);
            w = x->w;
            wlen = x->len;
        } else {
            Entry *e = table_entry(&table, i);
            w = e->key;
            wlen = e->len;
        }
        scanned++;
        if (wlen >= len && memcmp(w, prefix, len) == 0)
            *(char **)array_push(&match) = w;
    }
    char **v = (char **)match.data;
    sort_merge((void **)v, match.len, compare_words, NULL);
    size_t printed = 0;
    for (size_t i = 0; i < match.len; i++) {
        if (i > 0 && strcmp(v[i], v[i - 1]) == 0)
            continue;               /* the same word in two files */
        puts(v[i]);
        printed++;
    }
    array_free(&match);
    return printed;
    // @end
}

static void print_word(const char *w, size_t len, void *ctx)
{
    fwrite(w, 1, len, stdout);
    putchar('\n');
    (*(size_t *)ctx)++;
}

/* -p with the trie: one walk down to the prefix's node, and every word
 * below it, in order already. */
static size_t complete_trie(const char *prefix, size_t len)
{
    // @build 05.01 complete a prefix: walk down to its node, then every word below it
    size_t printed = 0;
    long node = trie_find(&trie, prefix, len);
    if (node >= 0)
        trie_each(&trie, node, prefix, len, print_word, &printed);
    return printed;
    // @end
}

// @from 05.03
/* ------------------------------------------------------------ -s: did you mean */

enum { NEAR_SCAN, NEAR_TRIE };
static const char *const nears[] = {"scan", "trie", NULL};
static int near = -1;            /* -1: trie when there is one */
static int maxd = 2;             /* -e */
static long nmax = 5;            /* -n */
static int have_trie;            /* --algo=bloom: the trie is built */

typedef struct {
    char  *w;
    size_t len;
    int    d;
} Cand;

static Array cands;              /* Cand: the words within maxd */
static const char *near_w;       /* the word suggestions are for */
static size_t near_len;

static void add_cand(const char *w, size_t len, int d, void *ctx)
{
    Cand *c = array_push(&cands);
    c->w = xstrndup(w, len);
    c->len = len;
    c->d = d;
}

/* One word of the dictionary tried against near_w. */
static void try_word(const char *w, size_t len, void *ctx)
{
    int d = edit_distance(near_w, near_len, w, len);
    if (d <= maxd)
        add_cand(w, len, d, NULL);
}

/* --near=scan: the distance from near_w to every word of the dictionary,
 * whichever structure holds them. */
static void near_scan(void)
{
    // @build 05.03 the slow way: the distance to every word of the dictionary
    if (algo == LIST) {
        for (size_t i = 0; i < list.len; i++) {
            DictWord *x = array_at(&list, i);
            try_word(x->w, x->len, NULL);
        }
    } else if (algo == TABLE) {
        for (size_t i = 0; i < table_len(&table); i++) {
            Entry *e = table_entry(&table, i);
            try_word(e->key, e->len, NULL);
        }
    } else {
        trie_each(&trie, 0, "", 0, try_word, NULL);
    }
    // @end
}

static int compare_cands(const void *a, const void *b, void *ctx)
{
    return strcmp(((const Cand *)a)->w, ((const Cand *)b)->w);
}

/* A filter holds no words to suggest: the first time one is needed, the
 * dictionary is read again, into a trie. A text with no unknown word never
 * builds it. */
static void need_words(void)
{
    if (algo != BLOOM || have_trie)
        return;
    trie_init(&trie);
    size_t words = dict_words, text = dict_text;
    for (size_t i = 0; i < dicts.len; i++)
        read_dict(*(const char **)array_at(&dicts, i), add_trie);
    dict_words = words;
    dict_text = text;
    have_trie = 1;
}

/* -s: w, and the dictionary's words nearest to it: those at the smallest
 * distance found, if it is no more than maxd, in byte order, no more
 * than nmax of them (0: all). */
static void suggest(const char *w, size_t len)
{
    // @build 05.03 did you mean: the nearest words, in byte order
    need_words();
    for (size_t i = 0; i < cands.len; i++)
        free(((Cand *)array_at(&cands, i))->w);
    array_clear(&cands);
    near_w = w;
    near_len = len;
    if (near == NEAR_TRIE)
        trie_near(&trie, w, len, maxd, add_cand, NULL);
    else
        near_scan();
    int best = maxd + 1;
    for (size_t i = 0; i < cands.len; i++)
        if (((Cand *)array_at(&cands, i))->d < best)
            best = ((Cand *)array_at(&cands, i))->d;
    Array top;
    array_init(&top, sizeof(Cand *));
    for (size_t i = 0; i < cands.len; i++)
        if (((Cand *)array_at(&cands, i))->d == best)
            *(Cand **)array_push(&top) = array_at(&cands, i);
    Cand **v = (Cand **)top.data;
    sort_merge((void **)v, top.len, compare_cands, NULL);
    printf("%s:", w);
    long shown = 0;
    for (size_t i = 0; i < top.len && (nmax == 0 || shown < nmax); i++) {
        if (i > 0 && strcmp(v[i]->w, v[i - 1]->w) == 0)
            continue;               /* the same word in two files */
        printf(" %s", v[i]->w);
        shown++;
    }
    putchar('\n');
    array_free(&top);
    // @end
}
// @end

/* ------------------------------------------------------------ checking a text */

/* The words of f: each one of two letters or more that the dictionary
 * does not have goes on unknown (char *: a copy of the word). */
static void check(FILE *f, Array *buf, Array *unknown)
{
    // @build 05.01 check a text: look up every word of two letters or more
    while (next_word(f, buf)) {
        nwords++;
        if (buf->len < 2)
            continue;
        checked++;
        if (!known(buf->data, buf->len))
            *(char **)array_push(unknown) = xstrndup(buf->data, buf->len);
    }
    // @end
}

/* The value of an option: what follows it in the same argument ("-dfile"),
 * or the next argument. */
static const char *value(int argc, char **argv, int *i)
{
    const char *a = argv[*i];
    if (a[2] != '\0')
        return a + 2;
    if (*i + 1 >= argc)
        die("%s wants a value", a);
    return argv[++*i];
}

/* The value of --name=value, which must be one of names: its index. */
static int pick(const char *name, const char *value, const char *const *names)
{
    char have[200] = "";
    for (int i = 0; names[i]; i++) {
        if (strcmp(value, names[i]) == 0)
            return i;
        strcat(strcat(have, i ? ", " : ""), names[i]);
    }
    die("no %s '%s' (have: %s)", name, value, have);
}

// @from 05.02
static const char *const algos[] = {"list", "table", "trie", "bloom", NULL};
// @else
// static const char *const algos[] = {"list", "table", "trie", NULL};
// @end

// @from 05.02
/* A number from s, which must be all of it and within [lo, hi]. */
static double number(const char *opt, const char *s, double lo, double hi)
{
    char *end;
    double v = strtod(s, &end);
    if (*s == '\0' || *end != '\0' || !(v >= lo && v <= hi))
        die("%s wants a number from %g to %g, not '%s'", opt, lo, hi, s);
    return v;
}
// @end

int main(int argc, char **argv)
{
    progname = "spell";
    ds_stats_at_exit(print_stats);
    array_init(&dicts, sizeof(const char *));
    const char *prefix = NULL;
    // @from 05.03
    int suggesting = 0;
    const char *pair[2] = {NULL, NULL};
    // @end
    int i;
    for (i = 1; i < argc; i++) {
        const char *a = argv[i];
        if (strncmp(a, "-d", 2) == 0) {
            *(const char **)array_push(&dicts) = value(argc, argv, &i);
            continue;
        }
        if (strncmp(a, "-p", 2) == 0) {
            prefix = value(argc, argv, &i);
            continue;
        }
        if (strncmp(a, "--algo=", 7) == 0) {
            algo = pick("--algo", a + 7, algos);
            continue;
        }
        // @from 05.02
        if (strncmp(a, "--fp=", 5) == 0) {
            fp = number("--fp", a + 5, 1e-9, 0.5);
            continue;
        }
        if (strncmp(a, "--hashes=", 9) == 0) {
            hashes = (int)number("--hashes", a + 9, 1, 64);
            continue;
        }
        // @end
        // @from 05.03
        if (strcmp(a, "-s") == 0) {
            suggesting = 1;
            continue;
        }
        if (strncmp(a, "-e", 2) == 0) {
            maxd = (int)number("-e", value(argc, argv, &i), 1, 3);
            continue;
        }
        if (strncmp(a, "-n", 2) == 0) {
            nmax = (long)number("-n", value(argc, argv, &i), 0, 1e9);
            continue;
        }
        if (strncmp(a, "--near=", 7) == 0) {
            near = pick("--near", a + 7, nears);
            continue;
        }
        if (strcmp(a, "--distance") == 0) {
            if (i + 2 >= argc)
                die("--distance wants two words");
            pair[0] = argv[++i];
            pair[1] = argv[++i];
            continue;
        }
        // @end
        if (strcmp(a, "--") == 0) {
            i++;
            break;
        }
        if (a[0] == '-' && a[1] != '\0')
            die("unknown option '%s'", a);
        break;
    }
    int nfiles = argc - i;

    // @from 05.03
    if (pair[0] != NULL) {
        if (nfiles > 0 || prefix != NULL || suggesting)
            die("--distance takes two words and nothing else");
        printf("%d\n", edit_distance(pair[0], strlen(pair[0]), pair[1], strlen(pair[1])));
        return ferror(stdout) ? 2 : 0;
    }
    if (near < 0)
        near = algo == LIST || algo == TABLE ? NEAR_SCAN : NEAR_TRIE;
    if (near == NEAR_TRIE && (algo == LIST || algo == TABLE))
        die("--near=trie walks the trie: it needs --algo=trie (or bloom)");
    array_init(&cands, sizeof(Cand));
    // @end
    // @from 05.02
    if (prefix != NULL && algo == BLOOM)
        die("a Bloom filter holds no words to list: -p needs --algo=trie, table or list");
    // @end
    if (prefix != NULL && nfiles > 0)
        die("-p completes a prefix from the dictionary: it reads no files");
    if (dicts.len == 0)
        *(const char **)array_push(&dicts) = DICTIONARY;
    load();

    if (prefix != NULL) {
        size_t len = strlen(prefix);
        char *p = xstrndup(prefix, len);
        for (size_t j = 0; j < len; j++)
            if (p[j] >= 'A' && p[j] <= 'Z')
                p[j] = (char)(p[j] - 'A' + 'a');
        size_t printed = algo == TRIE ? complete_trie(p, len) : complete_scan(p, len);
        free(p);
        return ferror(stdout) ? 2 : printed > 0 ? 0 : 1;
    }

    Array buf, unknown;
    array_init(&buf, 1);
    array_init(&unknown, sizeof(char *));
    for (int f = 0; f < (nfiles ? nfiles : 1); f++) {
        FILE *in = open_input(nfiles ? argv[i + f] : NULL);
        check(in, &buf, &unknown);
        close_input(in);
    }
    char **v = (char **)unknown.data;
    sort_merge((void **)v, unknown.len, compare_words, NULL);
    for (size_t j = 0; j < unknown.len; j++) {
        if (j > 0 && strcmp(v[j], v[j - 1]) == 0)
            continue;
        nunknown++;
        // @from 05.03
        if (suggesting) {
            suggest(v[j], strlen(v[j]));
            continue;
        }
        // @end
        puts(v[j]);
    }
    return ferror(stdout) ? 2 : 0;
}
