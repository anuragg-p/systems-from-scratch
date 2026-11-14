/*
 * sort - sort the lines of text files: the same bytes out as LC_ALL=C sort.
 *
 *   sort [-rnu] [-t C] [-k KEY]... [--algo=NAME] [file ...]
 *   sort ... [-S SIZE] [-T DIR]                                         @from 02.05
 *
 * Lines are compared byte by byte, as the C locale does, and a line that
 * is the start of another comes first.
 *
 *   -r       reverse the order
 *   -n       compare as numbers: blanks, an optional -, digits, and
 *            optionally a . and more digits; a line without one counts
 *            as 0
 *   -u       print only the first of each run of equal lines (equal by
 *            the keys, with -k): the one that came first in the input
 *   -t C     fields are separated by the character C; without -t, each
 *            field is a run of blanks and the non-blanks after it
 *   -k F1[.C1][,F2[.C2]]
 *            compare by the key from character C1 of field F1 (1 if no
 *            C1) to character C2 of field F2 (the end of that field if
 *            no C2; the end of the line if no F2). An n or r after a
 *            position applies -n or -r to that key alone. A key without
 *            either takes -n and -r from the command line. Several -k
 *            compare in turn.
 *   -S SIZE  hold no more than SIZE bytes of lines in memory: the rest     @from 02.05
 *            goes to sorted runs in files, merged at the end. K (1024)     @from 02.05
 *            is the unit unless SIZE ends in b, K, M or G, as sort's is.   @from 02.05
 *   -T DIR   where the runs go: $TMPDIR, or /tmp, without it               @from 02.05
 *
 * Lines whose keys are equal (with -n or -k) are compared whole, byte by
 * byte, as a last resort, reversed by -r; with -u they stay equal.
 *
 * --algo=NAME picks the sort. They all print the same lines; they differ
 * in how long they take, and on which input:
 *   insertion     insertion sort
 *   merge         merge sort (the default)                        @from 02.02
 *   quick-first   quicksort, the first line as the pivot          @from 02.03
 *   quick         quicksort, a random pivot and a three-way split  @from 02.03
 *   heap          heapsort                                        @from 02.04
 *
 * DS_STATS=1 prints, besides lib's lines, "stats: lines: read N, peak
 * bytes P": the lines read and the most bytes of them held at once.
 * "stats: runs: written R, merges M": sorted runs written to files, and   @from 02.05
 * the merges that read them back.                                         @from 02.05
 */
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "ds.h"

/* One line of input, without its newline, and where it came in the input:
 * the last tiebreak with -u when the sort is not stable (see by_index). */
typedef struct {
    size_t len;
    size_t index;
    char   text[];
} Line;

/* One -k key: from character schar of field sfield to character echar of
 * field efield (efield SIZE_MAX: the end of the line; echar 0: the end of
 * field efield). Fields and characters are counted from 0 here. */
typedef struct {
    size_t sfield, schar;
    size_t efield, echar;
    int numeric, reverse;
    int own;                /* has an n or r of its own */
} Key;

#define MAX_KEYS 16

static Key keys[MAX_KEYS];
static int nkeys;
static int reverse, numeric, unique;
static int tab = -1;        /* -t C, or -1: fields are separated by blanks */

/* With -u, sort prints the first line of each run of equal ones in the
 * input. A stable sort leaves equal lines in input order by itself; for
 * one that is not, lines that are otherwise equal are put in input order
 * by index, the last thing compared. */
static int by_index;

static long nread;
static size_t held, peak;   /* bytes of lines in memory, now and at most */

static void print_stats(void)
{
    ds_stats_print("lines", "read %ld, peak bytes %zu", nread, peak);
}

/* ------------------------------------------------------------ reading and writing */

static char  *buf;
static size_t bufcap;

/* The next line of f, or NULL at the end of it. A last line without a
 * newline is a line all the same. */
static Line *read_line(FILE *f, size_t index)
{
    ssize_t n = getline(&buf, &bufcap, f);
    if (n < 0) {
        if (ferror(f))
            die("read error: %s", strerror(errno));
        return NULL;
    }
    if (n > 0 && buf[n - 1] == '\n')
        n--;
    Line *l = xmalloc(sizeof(Line) + (size_t)n + 1);
    l->len = (size_t)n;
    l->index = index;
    memcpy(l->text, buf, (size_t)n);
    l->text[n] = '\0';
    return l;
}

/* What a line costs in memory: itself, and its pointer in the array. */
static size_t line_bytes(const Line *l)
{
    return sizeof(Line) + l->len + 1 + sizeof(Line *);
}

static void write_line(FILE *out, const Line *l)
{
    fwrite(l->text, 1, l->len, out);
    putc('\n', out);
}

/* ------------------------------------------------------------ keys */

static int blank(int c)
{
    return c == ' ' || c == '\t';
}

/* Where key k starts in line l. Without -t a field starts with the blanks
 * before it, so they are part of the key; a character position past the
 * end of the line is the end of the line. */
static const char *key_start(const Line *l, const Key *k)
{
    const char *p = l->text, *lim = l->text + l->len;
    for (size_t f = 0; f < k->sfield && p < lim; f++) {
        if (tab >= 0) {
            while (p < lim && *p != tab)
                p++;
            if (p < lim)
                p++;
        } else {
            while (p < lim && blank(*p))
                p++;
            while (p < lim && !blank(*p))
                p++;
        }
    }
    return (size_t)(lim - p) < k->schar ? lim : p + k->schar;
}

/* Where key k ends in line l: just past its last character. */
static const char *key_end(const Line *l, const Key *k)
{
    const char *p = l->text, *lim = l->text + l->len;
    if (k->efield == SIZE_MAX)
        return lim;
    size_t fields = k->echar == 0 ? k->efield + 1 : k->efield;
    for (size_t f = 0; f < fields && p < lim; f++) {
        if (tab >= 0) {
            while (p < lim && *p != tab)
                p++;
            if (p < lim && (f + 1 < fields || k->echar))
                p++;
        } else {
            while (p < lim && blank(*p))
                p++;
            while (p < lim && !blank(*p))
                p++;
        }
    }
    if (k->echar)
        p = (size_t)(lim - p) < k->echar ? lim : p + k->echar;
    return p;
}

static int bytecmp(const char *a, size_t alen, const char *b, size_t blen)
{
    int c = memcmp(a, b, alen < blen ? alen : blen);
    if (c != 0)
        return c < 0 ? -1 : 1;
    return alen < blen ? -1 : alen > blen;
}

/* A number as -n reads it: the digits of its whole part without leading
 * zeros, and of its fraction without trailing ones, so that comparing
 * them as strings compares the numbers, however long they are. */
typedef struct {
    int neg;
    const char *ip, *fp;
    size_t il, fl;
} Num;

static int digit(int c)
{
    return c >= '0' && c <= '9';
}

static Num read_num(const char *p, const char *e)
{
    Num x = {0, p, p, 0, 0};
    while (p < e && blank(*p))
        p++;
    if (p < e && *p == '-') {
        x.neg = 1;
        p++;
    }
    while (p < e && *p == '0')
        p++;
    x.ip = p;
    while (p < e && digit(*p))
        p++;
    x.il = (size_t)(p - x.ip);
    if (p < e && *p == '.') {
        x.fp = ++p;
        while (p < e && digit(*p))
            p++;
        x.fl = (size_t)(p - x.fp);
        while (x.fl > 0 && x.fp[x.fl - 1] == '0')
            x.fl--;
    }
    if (x.il == 0 && x.fl == 0)
        x.neg = 0;              /* -0, - and -.0 are all 0 */
    return x;
}

static int numcmp(const char *a, size_t alen, const char *b, size_t blen)
{
    Num x = read_num(a, a + alen), y = read_num(b, b + blen);
    if (x.neg != y.neg)
        return x.neg ? -1 : 1;
    int c;
    if (x.il != y.il)
        c = x.il < y.il ? -1 : 1;
    else if ((c = x.il ? memcmp(x.ip, y.ip, x.il) : 0) == 0)
        c = bytecmp(x.fp, x.fl, y.fp, y.fl);
    c = c < 0 ? -1 : c > 0;
    return x.neg ? -c : c;
}

/* 0 when a and b are equal by the keys: by each -k in turn, or with none
 * by the whole line (as a number with -n), each reversed by its r. */
static int compare_keys(const Line *a, const Line *b)
{
    if (nkeys == 0) {
        int c = numeric ? numcmp(a->text, a->len, b->text, b->len)
                        : bytecmp(a->text, a->len, b->text, b->len);
        return reverse ? -c : c;
    }
    for (int i = 0; i < nkeys; i++) {
        const Key *k = &keys[i];
        const char *as = key_start(a, k), *ae = key_end(a, k);
        const char *bs = key_start(b, k), *be = key_end(b, k);
        size_t al = ae > as ? (size_t)(ae - as) : 0, bl = be > bs ? (size_t)(be - bs) : 0;
        int c = k->numeric ? numcmp(as, al, bs, bl) : bytecmp(as, al, bs, bl);
        if (c != 0)
            return k->reverse ? -c : c;
    }
    return 0;
}

/* The order sort prints lines in: by the keys; then, when the keys are
 * equal, by the whole line as a last resort (reversed by -r), except with
 * -u; then, with -u and a sort that is not stable, by where each came in
 * the input. A Cmp, for lib's sorts. */
static int compare_lines(const void *a, const void *b, void *ctx)
{
    // @build 02.01 compare two lines as sort does
    const Line *x = a, *y = b;
    int c = compare_keys(x, y);
    if (c == 0 && !unique && (nkeys > 0 || numeric)) {
        c = bytecmp(x->text, x->len, y->text, y->len);
        if (reverse)
            c = -c;
    }
    if (c == 0 && by_index)
        c = x->index < y->index ? -1 : x->index > y->index;
    return c;
    // @end
}

/* The lines of v in order to out, and with -u only the first of each run
 * that compares equal by the keys. */
static void write_lines(Line **v, size_t n, FILE *out)
{
    Line *last = NULL;
    for (size_t i = 0; i < n; i++) {
        if (unique && last != NULL && compare_keys(last, v[i]) == 0)
            continue;
        write_line(out, v[i]);
        last = v[i];
    }
}

// @from 02.05
/* ------------------------------------------------------------ bigger than memory */

#define MERGE_WAYS 16       /* runs merged at once */

static size_t cap;          /* -S, in bytes; 0: no cap */
static const char *tmpdir;  /* -T */
static Array runs;          /* char *: the run files, earliest input first */
static long nruns, merges;

static void print_runs(void)
{
    ds_stats_print("runs", "written %ld, merges %ld", nruns, merges);
}

/* Remove any run files left, however sort exits. */
static void remove_runs(void)
{
    for (size_t i = 0; i < runs.len; i++)
        unlink(*(char **)array_at(&runs, i));
}

/* A new, empty run file in the -T directory; its path in *path. */
static FILE *new_run(char **path)
{
    const char *dir = tmpdir ? tmpdir : getenv("TMPDIR");
    if (dir == NULL || *dir == '\0')
        dir = "/tmp";
    size_t n = strlen(dir) + 20;
    char *p = xmalloc(n);
    snprintf(p, n, "%s/sortXXXXXX", dir);
    int fd = mkstemp(p);
    if (fd < 0)
        die("cannot make a file in %s: %s", dir, strerror(errno));
    FILE *f = fdopen(fd, "wb");
    if (f == NULL)
        die("%s: %s", p, strerror(errno));
    *path = p;
    return f;
}

/* The lines held, sorted, out to a new run file; then they are let go. */
static void spill(Array *lines, void (*sort)(void **, size_t, Cmp, void *))
{
    // @build 02.05 a run: the lines in memory, sorted, out to a file
    char *path;
    FILE *f = new_run(&path);
    *(char **)array_push(&runs) = path;
    Line **v = (Line **)lines->data;
    sort((void **)v, lines->len, compare_lines, NULL);
    write_lines(v, lines->len, f);
    if (fclose(f) != 0)
        die("%s: %s", path, strerror(errno));
    for (size_t i = 0; i < lines->len; i++)
        free(v[i]);
    array_clear(lines);
    held = 0;
    nruns++;
    // @end
}

/* A run being merged: its file, and its line that is next out. no is its
 * place among the runs merged, which is their order in the input. */
typedef struct {
    FILE  *f;
    Line  *line;
    size_t no;
} Run;

/* Runs in the order of their next lines; on a tie, the earlier run first. */
static int run_cmp(const void *a, const void *b, void *ctx)
{
    const Run *x = a, *y = b;
    int c = compare_lines(x->line, y->line, NULL);
    return c != 0 ? c : (x->no < y->no ? -1 : x->no > y->no);
}

/* Merge the n run files at paths into out. A heap holds one run for each
 * file that has lines left, the run with the smallest next line on top:
 * take its line, write it, put the run back with its next line. Each line
 * costs log2(n) comparisons, and only n lines are in memory at a time. */
static void merge_runs(char **paths, size_t n, FILE *out)
{
    // @build 02.05 merge runs through a heap
    Heap h;
    heap_init(&h, run_cmp, NULL);
    Run *r = xmalloc(n * sizeof *r);
    for (size_t i = 0; i < n; i++) {
        r[i].f = fopen(paths[i], "rb");
        if (r[i].f == NULL)
            die("%s: %s", paths[i], strerror(errno));
        unlink(paths[i]);
        r[i].no = i;
        r[i].line = read_line(r[i].f, i);
        if (r[i].line != NULL)
            heap_push(&h, &r[i]);
        else
            fclose(r[i].f);
    }
    Line *last = NULL;
    while (heap_len(&h) > 0) {
        Run *top = heap_pop(&h);
        Line *l = top->line;
        if (unique && last != NULL && compare_keys(last, l) == 0) {
            free(l);
        } else {
            write_line(out, l);
            free(last);
            last = l;
        }
        top->line = read_line(top->f, top->no);
        if (top->line != NULL)
            heap_push(&h, top);
        else
            fclose(top->f);
    }
    free(last);
    free(r);
    heap_free(&h);
    merges++;
    // @end
}

/* Merge all the runs into out, in passes. While there are more than
 * MERGE_WAYS runs, a pass merges each MERGE_WAYS of them in turn (the last
 * group perhaps fewer) into a new run, put on the end of the list, so the
 * new runs keep the input's order; then the runs it merged are dropped
 * from the front. Each pass leaves a sixteenth as many runs, and every line
 * goes through one merge a pass. The last merge writes to out. */
static void merge_all(FILE *out)
{
    // @build 02.05 merge every run, in passes of MERGE_WAYS at a time
    while (runs.len > MERGE_WAYS) {
        size_t n = runs.len;            /* this pass merges runs 0 to n-1 */
        for (size_t i = 0; i < n; i += MERGE_WAYS) {
            size_t k = n - i < MERGE_WAYS ? n - i : MERGE_WAYS;
            char *path;
            FILE *f = new_run(&path);
            *(char **)array_push(&runs) = path;
            merge_runs((char **)runs.data + i, k, f);
            if (fclose(f) != 0)
                die("%s: %s", path, strerror(errno));
        }
        char **p = (char **)runs.data;
        for (size_t i = 0; i < n; i++)
            free(p[i]);
        memmove(p, p + n, (runs.len - n) * sizeof *p);
        runs.len -= n;
    }
    merge_runs((char **)runs.data, runs.len, out);
    // @end
}

/* -S SIZE: a number of K, or of b(ytes), K, M or G. */
static size_t parse_size(const char *s)
{
    char *end;
    errno = 0;
    unsigned long long v = strtoull(s, &end, 10);
    unsigned long long unit = 1024;
    if (end == s || errno != 0 || v == 0 || *s == '-')
        die("-S wants a size, such as 64K or 2M, not '%s'", s);
    if (*end == 'b')
        unit = 1;
    else if (*end == 'k' || *end == 'K')
        unit = 1024;
    else if (*end == 'm' || *end == 'M')
        unit = 1024 * 1024;
    else if (*end == 'g' || *end == 'G')
        unit = 1024 * 1024 * 1024;
    else if (*end != '\0')
        die("-S wants a size, such as 64K or 2M, not '%s'", s);
    if (*end != '\0' && end[1] != '\0')
        die("-S wants a size, such as 64K or 2M, not '%s'", s);
    return (size_t)(v * unit);
}
// @end

/* ------------------------------------------------------------ options */

typedef void (*SortFn)(void **v, size_t n, Cmp cmp, void *ctx);

typedef struct {
    const char *name;
    SortFn fn;
    int stable;             /* keeps equal items in the order they came */
} Algo;

static const Algo algos[] = {
    {"insertion", sort_insertion, 1},
    {"merge", sort_merge, 1},                // @from 02.02
    {"quick-first", sort_quick_first, 0},    // @from 02.03
    {"quick", sort_quick, 0},                // @from 02.03
    {"heap", heap_sort, 0},                  // @from 02.04
    {NULL, NULL, 0},
};

static const Algo *pick_algo(const char *name)
{
    char have[200] = "";
    for (int i = 0; algos[i].name; i++) {
        if (strcmp(name, algos[i].name) == 0)
            return &algos[i];
        strcat(strcat(have, i ? ", " : ""), algos[i].name);
    }
    die("no --algo '%s' (have: %s)", name, have);
}

/* A field or character number of -k, at *p. */
static size_t key_number(const char **p, const char *spec)
{
    if (!digit(**p))
        die("-k %s: a number is missing", spec);
    size_t n = 0;
    while (digit(**p))
        n = n * 10 + (size_t)(*(*p)++ - '0');
    return n;
}

/* The n and r after a -k position. */
static void key_options(const char **p, Key *k, const char *spec)
{
    for (; **p && **p != ','; (*p)++) {
        if (**p == 'n')
            k->numeric = 1;
        else if (**p == 'r')
            k->reverse = 1;
        else
            die("-k %s: '%c' is not an option here (only n and r are)", spec, **p);
        k->own = 1;
    }
}

static void parse_key(const char *spec)
{
    if (nkeys == MAX_KEYS)
        die("at most %d keys", MAX_KEYS);
    Key *k = &keys[nkeys++];
    memset(k, 0, sizeof *k);
    const char *p = spec;
    size_t f = key_number(&p, spec);
    if (f == 0)
        die("-k %s: fields are numbered from 1", spec);
    k->sfield = f - 1;
    if (*p == '.') {
        p++;
        size_t c = key_number(&p, spec);
        if (c == 0)
            die("-k %s: characters are numbered from 1", spec);
        k->schar = c - 1;
    }
    key_options(&p, k, spec);
    k->efield = SIZE_MAX;
    if (*p == ',') {
        p++;
        f = key_number(&p, spec);
        if (f == 0)
            die("-k %s: fields are numbered from 1", spec);
        k->efield = f - 1;
        if (*p == '.') {
            p++;
            k->echar = key_number(&p, spec);
        }
        key_options(&p, k, spec);
    }
    if (*p != '\0')
        die("-k %s: cannot read it", spec);
}

/* The options that take a value, as the next argument or the rest of this one. */
// @from 02.05
#define TAKES_VALUE "ktST"
// @else
// #define TAKES_VALUE "kt"
// @end

int main(int argc, char **argv)
{
    progname = "sort";
    ds_stats_at_exit(print_stats);
    // @from 02.02
    const Algo *algo = pick_algo("merge");
    // @else
    // const Algo *algo = pick_algo("insertion");
    // @end
    int i;
    for (i = 1; i < argc; i++) {
        const char *a = argv[i];
        if (strcmp(a, "--") == 0) {
            i++;
            break;
        }
        if (strncmp(a, "--algo=", 7) == 0) {
            algo = pick_algo(a + 7);
            continue;
        }
        if (a[0] != '-' || a[1] == '\0')
            break;
        if (a[1] == '-')
            die("unknown option '%s'", a);
        for (const char *p = a + 1; *p; p++) {
            if (*p == 'r') {
                reverse = 1;
            } else if (*p == 'n') {
                numeric = 1;
            } else if (*p == 'u') {
                unique = 1;
            } else if (strchr(TAKES_VALUE, *p)) {
                const char *v = p[1] ? p + 1 : (i + 1 < argc ? argv[++i] : NULL);
                if (v == NULL)
                    die("-%c wants a value", *p);
                if (*p == 'k')
                    parse_key(v);
                else if (*p == 't' && strlen(v) == 1)
                    tab = (unsigned char)v[0];
                else if (*p == 't')
                    die("-t wants one character, not '%s'", v);
                // @from 02.05
                else if (*p == 'S')
                    cap = parse_size(v);
                else
                    tmpdir = v;
                // @end
                break;
            } else {
                die("unknown option -%c", *p);
            }
        }
    }
    for (int k = 0; k < nkeys; k++) {
        if (!keys[k].own) {         /* a key without n or r of its own takes the global ones */
            keys[k].numeric = numeric;
            keys[k].reverse = reverse;
        }
    }
    SortFn sort = algo->fn;
    by_index = unique && !algo->stable;

    Array lines;
    array_init(&lines, sizeof(Line *));
    // @from 02.05
    array_init(&runs, sizeof(char *));
    atexit(remove_runs);
    ds_stats_at_exit(print_runs);
    // @end
    size_t index = 0;
    int nfiles = argc - i;
    for (int f = 0; f < (nfiles ? nfiles : 1); f++) {
        FILE *in = open_input(nfiles ? argv[i + f] : NULL);
        Line *l;
        while ((l = read_line(in, index++)) != NULL) {
            size_t size = line_bytes(l);
            // @from 02.05
            if (cap > 0 && held + size > cap && lines.len > 0)
                spill(&lines, sort);
            // @end
            *(Line **)array_push(&lines) = l;
            held += size;
            if (held > peak)
                peak = held;
            nread++;
        }
        close_input(in);
    }
    // @from 02.05
    if (runs.len > 0) {
        if (lines.len > 0)
            spill(&lines, sort);
        merge_all(stdout);
        return ferror(stdout) ? 2 : 0;
    }
    // @end
    sort((void **)lines.data, lines.len, compare_lines, NULL);
    write_lines((Line **)lines.data, lines.len, stdout);
    return ferror(stdout) ? 2 : 0;
}
