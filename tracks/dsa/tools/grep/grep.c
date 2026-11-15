/*
 * grep - print the lines of a text that match a pattern.
 *
 *   grep [-F] [-ncvi] [--algo=NAME] pattern [file ...]
 *   grep -E ...                                                        @from 04.02
 *   grep ... [--cache=N]                                               @from 04.04
 *
 * grep reads each file (standard input with none, or for "-"), and
 * prints the lines the pattern is found in, each after its file's name
 * and a colon when there is more than one file. It exits 0 if it found a
 * line, 1 if not, and 2 on trouble (a file it cannot read: it goes on
 * with the others), as the system's grep does.
 *
 *   -F   the pattern is a fixed string: each of its bytes stands for itself
 *   -E   the pattern is a regular expression, as grep -E reads it, and    @from 04.02
 *        what lib/re.h says is supported (the default)                 @from 04.02
 *   -n   put each line's number in its file before it
 *   -c   print only how many lines there were
 *   -v   the lines the pattern is not found in, instead
 *   -i   upper and lower case letters are the same
 *
 * --algo=NAME picks how it searches; every way prints the same lines:
 *   with -F:
 *   scan        try the string at every position of the text
 *   horspool    compare from its end, and skip ahead (the default)
 *   with -E:                                                           @from 04.02
 *   backtrack   walk the expression's tree, trying one way and going   @from 04.02
 *               back to try the others                                 @from 04.02
 *   nfa         run it as a machine in every state at once             @from 04.03
 *   dfa         the same machine, each set of its states made a state  @from 04.04
 *               the first time the text leads to it (the default)      @from 04.04
 * --cache=N     keep at most N DFA states (10000 unless it says)       @from 04.04
 *
 * DS_STATS=1 prints, before the structures' own lines, "stats: grep:
 * bytes B, lines selected S": the bytes read, and the lines printed (or
 * counted). DS_TRACE=1 makes each search print its steps (each file of
 * lib/ says how).
 */
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#include "ds.h"
#include "strsearch.h"
#include "re.h"       // @from 04.02
#include "nfa.h"      // @from 04.03
#include "dfa.h"      // @from 04.04

static int fixed, number, count, invert, icase;
static int many;              /* more than one file: each line after its file's name */
static long bytes, selected;

static void print_stats(void)
{
    ds_stats_print("grep", "bytes %ld, lines selected %ld", bytes, selected);
}

// @from 04.02
/* Where the next line that matches starts, looking from at (the start of
 * a line) in buf[0..end); end if there is none. next_fixed for -F,
 * next_regex for a regular expression. */
// @else
// /* Where the next line that matches starts, looking from at (the start of
//  * a line) in buf[0..end); end if there is none: next_fixed. */
// @end
static size_t (*next_match)(const char *buf, size_t at, size_t end);

static Search search;
static const char *(*find)(const Search *s, const char *text, size_t n);

/* Search the rest of the text itself, newlines and all, not a line at a
 * time: the lines between two matches are passed over unread (Horspool
 * does not even look at most of their bytes), and only a match is traced
 * back to the start of its line. The pattern has no newline, so a match
 * never runs from one line into the next. */
static size_t next_fixed(const char *buf, size_t at, size_t end)
{
    // @build 04.01 the next line with the string in it: search the text, not each line
    const char *p = find(&search, buf + at, end - at);
    if (p == NULL)
        return end;
    size_t start = (size_t)(p - buf);
    while (start > at && buf[start - 1] != '\n')
        start--;
    return start;
    // @end
}

// @from 04.02
static Re *re;
static int (*matches)(const char *line, size_t len);

static int by_backtracking(const char *s, size_t n)
{
    return re_backtrack(re, s, n);
}
// @end
// @from 04.03
static Nfa nfa;

static int by_nfa(const char *s, size_t n)
{
    return nfa_match(&nfa, s, n);
}
// @end
// @from 04.04
static Dfa dfa;
static size_t cache = 10000;

static int by_dfa(const char *s, size_t n)
{
    return dfa_match(&dfa, s, n);
}
// @end

/* A regular expression is matched a line at a time: a match may start
 * anywhere, and ^ and $ are the line's own start and end. */
static size_t next_regex(const char *buf, size_t at, size_t end)
{
    // @build 04.02 the next line the expression matches: each line in turn
    while (at < end) {
        const char *nl = memchr(buf + at, '\n', end - at);
        size_t len = nl ? (size_t)(nl - (buf + at)) : end - at;
        if (re_tracing())
            fprintf(stderr, "trace: line: %.*s\n", (int)len, buf + at);
        if (matches(buf + at, len))
            return at;
        at += len + 1;
    }
    return end;
    // @end
}

/* The --algo names for each kind of pattern; with no --algo, the last of
 * them, the best one there is. */
static const char *const fixed_algos[] = {"scan", "horspool", NULL};
// @from 04.02
static const char *const regex_algos[] = {
    "backtrack",
    "nfa",        // @from 04.03
    "dfa",        // @from 04.04
    NULL,
};
// @end

/* The --algo to use: algo, if it is one of names, or the last of names. */
static const char *pick(const char *algo, const char *const *names, const char *kind)
{
    char have[100] = "";
    int i;
    for (i = 0; names[i]; i++) {
        if (algo != NULL && strcmp(algo, names[i]) == 0)
            return names[i];
        strcat(strcat(have, i ? ", " : ""), names[i]);
    }
    if (algo == NULL)
        return names[i - 1];
    die("no --algo '%s' for %s (have: %s)", algo, kind, have);
}

// @from 04.02
/* Without -F: parse the pattern, and get the matcher --algo names ready.
 * The backtracker walks the tree itself; the NFA is made from the tree, and   @from 04.03
 * the DFA from the NFA.                                                      @from 04.04
 */
static void use_regex(const char *pattern, size_t len, const char *algo)
{
    const char *how = pick(algo, regex_algos, "a regular expression");
    re = re_parse(pattern, len, icase);
    next_match = next_regex;
    if (strcmp(how, "backtrack") == 0) {
        matches = by_backtracking;
        return;
    }
    // @from 04.03
    nfa_compile(&nfa, re);
    matches = by_nfa;
    // @end
    // @from 04.04
    if (strcmp(how, "dfa") == 0) {
        dfa_init(&dfa, &nfa, cache);
        matches = by_dfa;
    }
    // @end
}
// @end

/* The whole of f, in one block of memory: as big as the file and one byte
 * more (to see that it has ended), or for a pipe, doubled as it fills. */
static char *read_all(FILE *f, const char *name, size_t *len)
{
    size_t cap = 1 << 16, n = 0;
    struct stat sb;
    if (fstat(fileno(f), &sb) == 0 && S_ISREG(sb.st_mode) && sb.st_size > 0)
        cap = (size_t)sb.st_size + 1;
    char *buf = xmalloc(cap);
    for (;;) {
        n += fread(buf + n, 1, cap - n, f);
        if (n < cap)
            break;
        char *bigger = xmalloc(2 * cap);
        memcpy(bigger, buf, n);
        free(buf);
        buf = bigger;
        cap *= 2;
    }
    if (ferror(f))
        die("%s: %s", name, strerror(errno));
    *len = n;
    return buf;
}

static size_t line_end(const char *buf, size_t at, size_t end)
{
    const char *nl = memchr(buf + at, '\n', end - at);
    return nl ? (size_t)(nl - buf) : end;
}

static void print_line(const char *name, long lineno, const char *line, size_t len)
{
    if (many)
        printf("%s:", name);
    if (number)
        printf("%ld:", lineno);
    fwrite(line, 1, len, stdout);
    putchar('\n');
}

/* The selected lines of buf[0..len), one file's text: printed, or with
 * -c counted. Returns how many. The lines between one match and the next
 * are only gone through with -v (to print them) or -n (to number the
 * next match). A last line without a newline is printed with one. */
static long grep_text(const char *name, const char *buf, size_t len)
{
    long n = 0, lineno = 1;
    size_t at = 0;
    while (at < len) {
        size_t m = next_match(buf, at, len);
        while (at < m && (invert || number)) {
            size_t e = line_end(buf, at, m);
            if (invert && !count)
                print_line(name, lineno, buf + at, e - at);
            n += invert;
            lineno++;
            at = e + 1;
        }
        if (m >= len)
            break;
        size_t e = line_end(buf, m, len);
        if (!invert && !count)
            print_line(name, lineno, buf + m, e - m);
        n += !invert;
        lineno++;
        at = e + 1;
    }
    if (count) {
        if (many)
            printf("%s:", name);
        printf("%ld\n", n);
    }
    return n;
}

static void usage(void)
{
    // @from 04.02
    die("usage: grep [-E|-F] [-ncvi] [--algo=NAME] pattern [file ...]");
    // @else
    // die("usage: grep [-F] [-ncvi] [--algo=NAME] pattern [file ...]");
    // @end
}

int main(int argc, char **argv)
{
    progname = "grep";
    ds_stats_at_exit(print_stats);
    const char *algo = NULL;
    int i;
    for (i = 1; i < argc; i++) {
        const char *a = argv[i];
        if (strcmp(a, "--") == 0) {
            i++;
            break;
        }
        if (strncmp(a, "--algo=", 7) == 0) {
            algo = a + 7;
            continue;
        }
        // @from 04.04
        if (strncmp(a, "--cache=", 8) == 0) {
            char *e;
            long n = strtol(a + 8, &e, 10);
            if (a[8] == '\0' || *e != '\0' || n < 1)
                die("--cache wants a number of states, 1 or more, not '%s'", a + 8);
            cache = (size_t)n;
            continue;
        }
        // @end
        if (a[0] == '-' && a[1] == '-')
            die("unknown option '%s'", a);
        if (a[0] != '-' || a[1] == '\0')
            break;
        for (const char *f = a + 1; *f; f++) {
            switch (*f) {
            case 'F': fixed = 1; break;
            case 'E': fixed = 0; break;     // @from 04.02
            case 'n': number = 1; break;
            case 'c': count = 1; break;
            case 'v': invert = 1; break;
            case 'i': icase = 1; break;
            default: die("unknown option -%c", *f);
            }
        }
    }
    if (i >= argc)
        usage();
    const char *pattern = argv[i++];
    size_t plen = strlen(pattern);
    if (strchr(pattern, '\n') != NULL)
        die("a pattern with a newline in it is not supported");
    // @from 04.02
    if (!fixed)
        use_regex(pattern, plen, algo);
    // @else
    // /* No regular expressions yet: without -F, a pattern must be a plain string. */
    // if (!fixed && strpbrk(pattern, "\\.[()*+?{|^$") != NULL)
    //     die("regular expressions are not supported: -F searches for '%s' as it is", pattern);
    // fixed = 1;
    // @end
    if (fixed) {
        const char *how = pick(algo, fixed_algos, "a fixed string");
        search_init(&search, pattern, plen, icase);
        find = strcmp(how, "scan") == 0 ? search_scan : search_horspool;
        next_match = next_fixed;
    }

    int nfiles = argc - i, trouble = 0;
    many = nfiles > 1;
    for (int k = 0; k < (nfiles ? nfiles : 1); k++) {
        const char *path = nfiles ? argv[i + k] : "-";
        int std = strcmp(path, "-") == 0;
        const char *name = std ? "(standard input)" : path;
        FILE *f = std ? stdin : fopen(path, "rb");
        if (f == NULL) {
            fflush(stdout);
            fprintf(stderr, "grep: %s: %s\n", path, strerror(errno));
            trouble = 1;
            continue;
        }
        size_t len;
        char *text = read_all(f, name, &len);
        if (!std)
            fclose(f);
        bytes += (long)len;
        selected += grep_text(name, text, len);
        free(text);
    }
    if (ferror(stdout) || fflush(stdout) != 0)
        return 2;
    return trouble ? 2 : selected > 0 ? 0 : 1;
}
