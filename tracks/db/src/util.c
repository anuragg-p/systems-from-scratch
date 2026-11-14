/*
 * util.c - errors, memory, crash injection and counters.
 *
 * The plumbing every other file uses.
 */
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "db.h"

char errmsg[512];
struct stats stats;

// @internal
/* Stands in for code a workspace has cut out: names the lesson whose code
 * is missing and exits with status 3 before anything is written. */
_Noreturn void todo(const char *lesson, const char *what)
{
    fflush(stdout);
    fprintf(stderr, "\ndb: %s: %s not written yet\n", lesson, what);
    exit(3);
}
// @end

/* Prints the message to stderr and exits with status 2. */
_Noreturn void fatal(const char *fmt, ...)
{
    va_list ap;
    fflush(stdout);
    fprintf(stderr, "db: fatal: ");
    va_start(ap, fmt);
    vfprintf(stderr, fmt, ap);
    va_end(ap);
    fprintf(stderr, "\n");
    exit(2);
}

/* Formats the message into errmsg and returns -1. */
int err(const char *fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(errmsg, sizeof errmsg, fmt, ap);
    va_end(ap);
    return -1;
}

/* ------------------------------------------------------------ crash injection */

static const char *crash_name;
static int crash_count = -1;    /* hits left before the crash; -1 = not read yet */

/* Reads DB_CRASH ("point" or "point:n") once. A missing or malformed
 * count means the first hit. */
static void crash_init(void)
{
    if (crash_count != -1)
        return;
    crash_count = 0;
    const char *env = getenv("DB_CRASH");
    if (!env || !*env)
        return;
    const char *colon = strchr(env, ':');
    crash_name = colon ? xstrndup(env, (size_t)(colon - env)) : env;
    crash_count = colon ? atoi(colon + 1) : 1;
    if (crash_count < 1)
        crash_count = 1;
}

/* 1 if the next crash_point(point) would be the one that kills the
 * process. Used before a write that should be torn rather than whole. */
int crash_armed(const char *point)
{
    crash_init();
    return crash_name && crash_count == 1 && strcmp(point, crash_name) == 0;
}

/* Counts a pass through the named point and kills the process on the
 * configured one. */
void crash_point(const char *point)
{
    crash_init();
    if (!crash_name || strcmp(point, crash_name) != 0)
        return;
    if (--crash_count > 0)
        return;
    /* SIGKILL: no atexit handlers, no flushing, no cleanup. What is in the
     * file now is what a crash at this instant would leave behind. */
    fflush(stdout);
    fprintf(stderr, "db: crash injected at %s\n", point);
    kill(getpid(), SIGKILL);
    _exit(137);
}

/* ------------------------------------------------------------ counters */

/* Writes every counter, on one line, to stderr. */
void stats_print(void)
{
    fprintf(stderr,
            "stats: pages read %llu, cache hits %llu, cache misses %llu, evictions %llu, "
            "pages written %llu, fsyncs %llu, journal pages %llu, wal frames %llu, "
            "checkpoints %llu, splits %llu, append splits %llu, merges %llu\n",
            (unsigned long long)stats.pages_read, (unsigned long long)stats.cache_hits,
            (unsigned long long)stats.cache_misses, (unsigned long long)stats.evictions,
            (unsigned long long)stats.pages_written, (unsigned long long)stats.fsyncs,
            (unsigned long long)stats.journal_pages, (unsigned long long)stats.wal_frames,
            (unsigned long long)stats.checkpoints, (unsigned long long)stats.splits,
            (unsigned long long)stats.append_splits, (unsigned long long)stats.merges);
}

/* fsync(2), counted in stats.fsyncs. */
int sys_fsync(int fd)
{
    stats.fsyncs++;
    return fsync(fd);
}

/* Syncs the directory that holds path. A new file is durable only once
 * its directory entry is, so a file just created needs this before
 * anything may rely on it, as in sqlite3. Returns -1 on failure. */
int fsync_dir(const char *path)
{
    char dir[4096];
    const char *slash = strrchr(path, '/');
    if (!slash) {
        strcpy(dir, ".");
    } else if (slash == path) {
        strcpy(dir, "/");
    } else {
        size_t n = (size_t)(slash - path);
        if (n >= sizeof dir)
            return -1;
        memcpy(dir, path, n);
        dir[n] = 0;
    }
    int fd = open(dir, O_RDONLY);
    if (fd < 0)
        return -1;
    int rc = sys_fsync(fd);
    close(fd);
    return rc;
}

/* ------------------------------------------------------------ memory */

/* The x* allocators never return NULL: running out of memory is fatal.
 * Size 0 is treated as 1 so a successful call always yields a pointer. */

void *xmalloc(size_t n)
{
    void *p = malloc(n ? n : 1);
    if (!p)
        fatal("out of memory");
    return p;
}

void *xcalloc(size_t n, size_t m)
{
    void *p = calloc(n ? n : 1, m ? m : 1);
    if (!p)
        fatal("out of memory");
    return p;
}

void *xrealloc(void *p, size_t n)
{
    p = realloc(p, n ? n : 1);
    if (!p)
        fatal("out of memory");
    return p;
}

char *xstrndup(const char *s, size_t n)
{
    char *p = xmalloc(n + 1);
    memcpy(p, s, n);
    p[n] = 0;
    return p;
}

/* One block of an arena. Chunks form a list, newest first. */
struct Chunk {
    struct Chunk *next;
    size_t used, size;
    _Alignas(max_align_t) unsigned char data[];
};

/* Returns n zeroed bytes, rounded up to 16 and aligned for any type, valid
 * until the arena is reset. A request larger than a standard 32 KB chunk
 * gets a chunk of its own. */
void *arena_alloc(Arena *a, size_t n)
{
    n = (n + 15) & ~(size_t)15;
    struct Chunk *c = a->head;
    if (!c || c->used + n > c->size) {
        size_t size = n > 32768 ? n : 32768;
        c = xmalloc(sizeof *c + size);
        c->size = size;
        c->used = 0;
        c->next = a->head;
        a->head = c;
    }
    void *p = c->data + c->used;
    c->used += n;
    memset(p, 0, n);
    return p;
}

char *arena_strndup(Arena *a, const char *s, size_t n)
{
    char *p = arena_alloc(a, n + 1);
    memcpy(p, s, n);
    p[n] = 0;
    return p;
}

void arena_reset(Arena *a)
{
    /* The newest chunk is kept for reuse; the rest are freed. */
    struct Chunk *c = a->head;
    if (!c)
        return;
    struct Chunk *rest = c->next;
    while (rest) {
        struct Chunk *next = rest->next;
        free(rest);
        rest = next;
    }
    c->next = NULL;
    c->used = 0;
}

/* Makes room for n more bytes, doubling the capacity as needed. */
void buf_reserve(Buf *b, size_t n)
{
    if (b->n + n <= b->cap)
        return;
    size_t cap = b->cap ? b->cap : 256;
    while (cap < b->n + n)
        cap *= 2;
    b->p = xrealloc(b->p, cap);
    b->cap = cap;
}

void buf_put(Buf *b, const void *data, size_t n)
{
    buf_reserve(b, n);
    memcpy(b->p + b->n, data, n);
    b->n += n;
}

void buf_free(Buf *b)
{
    free(b->p);
    b->p = NULL;
    b->n = b->cap = 0;
}
