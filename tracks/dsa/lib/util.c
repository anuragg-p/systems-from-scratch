/*
 * util.c - what every tool needs and none of them is about: messages,
 * memory, opening its input, and printing the counters of DS_STATS=1.
 */
#include <errno.h>
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>

#include "ds.h"

const char *progname = "dsa";

void die(const char *fmt, ...)
{
    va_list ap;
    fflush(stdout);
    fprintf(stderr, "%s: ", progname);
    va_start(ap, fmt);
    vfprintf(stderr, fmt, ap);
    va_end(ap);
    fputc('\n', stderr);
    exit(2);
}

void *xmalloc(size_t n)
{
    void *p = malloc(n ? n : 1);
    if (p == NULL)
        die("out of memory (wanted %zu bytes)", n);
    return p;
}

char *xstrndup(const char *s, size_t n)
{
    char *p = xmalloc(n + 1);
    memcpy(p, s, n);
    p[n] = '\0';
    return p;
}

FILE *open_input(const char *path)
{
    if (path == NULL || strcmp(path, "-") == 0)
        return stdin;
    FILE *f = fopen(path, "rb");
    if (f == NULL)
        die("%s: %s", path, strerror(errno));
    return f;
}

void close_input(FILE *f)
{
    if (f != stdin)
        fclose(f);
}

/* ------------------------------------------------------------ DS_STATS */

#define MAX_PRINTERS 32

static int stats_on = -1;
static void (*printers[MAX_PRINTERS])(void);
static int nprinters;

int ds_stats_on(void)
{
    if (stats_on < 0) {
        const char *s = getenv("DS_STATS");
        stats_on = s != NULL && *s != '\0' && strcmp(s, "0") != 0;
    }
    return stats_on;
}

static void print_all(void)
{
    fflush(stdout);
    for (int i = 0; i < nprinters; i++)
        printers[i]();
}

void ds_stats_at_exit(void (*print)(void))
{
    if (!ds_stats_on())
        return;
    for (int i = 0; i < nprinters; i++)
        if (printers[i] == print)
            return;
    if (nprinters == MAX_PRINTERS)
        return;
    if (nprinters == 0)
        atexit(print_all);
    printers[nprinters++] = print;
}

void ds_stats_print(const char *name, const char *fmt, ...)
{
    va_list ap;
    fprintf(stderr, "stats: %s: ", name);
    va_start(ap, fmt);
    vfprintf(stderr, fmt, ap);
    va_end(ap);
    fputc('\n', stderr);
}

// @internal
void ds_todo(const char *lesson, const char *what)
{
    fflush(stdout);
    fprintf(stderr, "%s: %s: %s not written yet\n", progname, lesson, what);
    exit(3);
}
// @end
