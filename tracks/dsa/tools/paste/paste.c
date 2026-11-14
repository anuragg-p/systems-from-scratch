/*
 * paste - join the lines of a file into one line, as paste -s does.
 *
 *   paste -s [-d LIST] [--algo=strcat|end] [file ...]
 *
 * Each file (standard input for none, or for "-") becomes one line of
 * output: its lines, without their newlines, with a delimiter between
 * them. The delimiter is a tab, or the characters of -d LIST in turn; in
 * LIST, \t is a tab, \n a newline, \\ a backslash and \0 no delimiter at
 * all. Only -s is here: paste's other mode, files side by side, is not.
 *
 * The job is small on purpose. The two ways of doing it differ in one
 * line, and they give the same output:
 *
 *   --algo=strcat  find the end of the line built so far with strlen()
 *                  before each piece is added, which is what strcat()
 *                  does: it walks every byte joined so far, every time
 *   --algo=end     remember where the end is (the default)
 *
 * DS_STATS=1 prints how many bytes each one copied and scanned.
 */
#include <stdlib.h>
#include <string.h>

#include "ds.h"

enum { STRCAT, END };

static char  *out;       /* the line being built, NUL-terminated */
static size_t len;       /* how many bytes of it are in use */
static size_t cap;       /* how many bytes it has room for */

static long lines, copied, scanned;

static void print_stats(void)
{
    ds_stats_print("paste", "lines %ld, bytes copied %ld, bytes scanned %ld", lines, copied, scanned);
}

/* Room for at least need bytes: twice as much as before, or need if that is more. */
static void reserve(size_t need)
{
    if (need <= cap)
        return;
    size_t n = cap ? 2 * cap : 4096;
    if (n < need)
        n = need;
    out = realloc(out, n);
    if (out == NULL)
        die("out of memory");
    cap = n;
}

/* Add the n bytes at s to the end of the line. */
static void add(int algo, const char *s, size_t n)
{
    size_t end;
    if (algo == STRCAT) {
        end = strlen(out);        /* look at every byte so far for the NUL */
        scanned += (long)end;
    } else {
        end = len;                /* or just remember it */
    }
    reserve(end + n + 1);
    memcpy(out + end, s, n);
    out[end + n] = '\0';
    len = end + n;
    copied += (long)n;
}

/* The delimiters of -d LIST, with its escapes turned into the bytes they
 * stand for; "\0" is an empty delimiter, stored as a NUL. */
static char *delimiters(const char *list, size_t *count)
{
    char *d = xmalloc(strlen(list) + 1);
    size_t n = 0;
    for (const char *p = list; *p; p++) {
        if (*p != '\\') {
            d[n++] = *p;
            continue;
        }
        p++;
        if (*p == 't')
            d[n++] = '\t';
        else if (*p == 'n')
            d[n++] = '\n';
        else if (*p == '0')
            d[n++] = '\0';
        else if (*p == '\\')
            d[n++] = '\\';
        else if (*p == '\0')
            die("-d: a backslash at the end of the list");
        else
            die("-d: unknown escape \\%c", *p);
    }
    if (n == 0)
        d[n++] = '\0';            /* -d '': no delimiter */
    *count = n;
    return d;
}

static void usage(void)
{
    die("usage: paste -s [-d list] [--algo=strcat|end] [file ...]");
}

int main(int argc, char **argv)
{
    progname = "paste";
    ds_stats_at_exit(print_stats);
    int serial = 0, algo = END;
    const char *list = "\\t";
    int i;
    for (i = 1; i < argc; i++) {
        const char *a = argv[i];
        if (a[0] == '-' && a[1] != '-' && a[1] != '\0') {
            for (const char *p = a + 1; *p; p++) {          /* -s, -d LIST, -sd LIST, -d: */
                if (*p == 's') {
                    serial = 1;
                } else if (*p == 'd') {
                    if (p[1])
                        list = p + 1;
                    else if (i + 1 < argc)
                        list = argv[++i];
                    else
                        usage();
                    break;
                } else {
                    usage();
                }
            }
        } else if (strcmp(a, "--algo=strcat") == 0) {
            algo = STRCAT;
        } else if (strcmp(a, "--algo=end") == 0) {
            algo = END;
        } else if (strncmp(a, "--algo=", 7) == 0) {
            die("no --algo '%s' (have: strcat, end)", a + 7);
        } else if (strcmp(a, "--") == 0) {
            i++;
            break;
        } else if (a[0] == '-' && a[1] == '-') {
            usage();
        } else {
            break;
        }
    }
    if (!serial)
        die("only paste -s is here: joining the lines of each file into one");
    size_t ndelims;
    char *delims = delimiters(list, &ndelims);
    reserve(1);

    char *line = NULL;
    size_t linecap = 0;
    int nfiles = argc - i;
    for (int f = 0; f < (nfiles ? nfiles : 1); f++) {
        FILE *in = open_input(nfiles ? argv[i + f] : NULL);
        len = 0;
        out[0] = '\0';
        ssize_t n;
        size_t k = 0;
        while ((n = getline(&line, &linecap, in)) > 0) {
            if (line[n - 1] == '\n')
                n--;
            if (k > 0) {
                char d = delims[(k - 1) % ndelims];
                if (d != '\0')
                    add(algo, &d, 1);
            }
            add(algo, line, (size_t)n);
            k++;
            lines++;
        }
        close_input(in);
        fwrite(out, 1, len, stdout);
        putchar('\n');
    }
    free(line);
    free(delims);
    free(out);
    return ferror(stdout) ? 2 : 0;
}
