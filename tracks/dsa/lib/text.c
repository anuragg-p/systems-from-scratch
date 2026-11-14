/*
 * text.c - what every structure behind text.h shares: the checks on the
 * positions the editor asks for, reading a whole file, and DS_TRACE.
 */
#include <errno.h>
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#include "ds.h"
#include "text.h"

void text_insert(Text *t, size_t pos, const char *s, size_t n)
{
    if (pos > t->len)
        die("%s: insert at %zu, past the end of %zu bytes", t->ops->name, pos, t->len);
    if (n > 0)
        t->ops->insert(t, pos, s, n);
}

void text_erase(Text *t, size_t pos, size_t n)
{
    if (pos > t->len || n > t->len - pos)
        die("%s: erase %zu at %zu, past the end of %zu bytes", t->ops->name, n, pos, t->len);
    if (n > 0)
        t->ops->erase(t, pos, n);
}

size_t text_read(Text *t, size_t pos, char *buf, size_t n)
{
    if (pos > t->len)
        die("%s: read at %zu, past the end of %zu bytes", t->ops->name, pos, t->len);
    if (n > t->len - pos)
        n = t->len - pos;
    if (n > 0)
        t->ops->read(t, pos, buf, n);
    return n;
}

int text_write(Text *t, FILE *f)
{
    return t->ops->write(t, f);
}

void text_free(Text *t)
{
    t->ops->free(t);
}

char *text_load(const char *path, size_t *len, size_t room)
{
    FILE *f = fopen(path, "rb");
    if (f == NULL) {
        if (errno != ENOENT)
            die("%s: %s", path, strerror(errno));
        *len = 0;
        return xmalloc(room);
    }
    /* The size the file says it is, and then whatever is really there:
     * a pipe or a device says 0. */
    struct stat sb;
    size_t cap = (fstat(fileno(f), &sb) == 0 && sb.st_size > 0 ? (size_t)sb.st_size : 4096) + room;
    char *buf = xmalloc(cap);
    size_t n = 0;
    for (;;) {
        if (n + room == cap) {           /* full: grow only if there is more */
            int c = getc(f);
            if (c == EOF)
                break;
            char *bigger = xmalloc(2 * cap);
            memcpy(bigger, buf, n);
            free(buf);
            buf = bigger;
            cap *= 2;
            buf[n++] = (char)c;
        }
        size_t got = fread(buf + n, 1, cap - room - n, f);
        n += got;
        if (got == 0)
            break;
    }
    if (ferror(f))
        die("%s: %s", path, strerror(errno));
    fclose(f);
    *len = n;
    return buf;
}

/* ------------------------------------------------------------ DS_TRACE */

static int trace_on = -1;

int text_tracing(void)
{
    if (trace_on < 0) {
        const char *s = getenv("DS_TRACE");
        trace_on = s != NULL && *s != '\0' && strcmp(s, "0") != 0;
    }
    return trace_on;
}

void text_trace_off(void)
{
    trace_on = 0;
}

void text_trace(const char *fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    vfprintf(stderr, fmt, ap);
    va_end(ap);
}

void text_trace_bytes(const char *s, size_t n)
{
    size_t show = n > 40 ? 40 : n;
    fputc('"', stderr);
    for (size_t i = 0; i < show; i++) {
        unsigned char c = (unsigned char)s[i];
        if (c == '\n')
            fputs("\\n", stderr);
        else if (c == '\t')
            fputs("\\t", stderr);
        else if (c == '"' || c == '\\')
            fprintf(stderr, "\\%c", c);
        else if (c < 32 || c >= 127)
            fprintf(stderr, "\\x%02x", c);
        else
            fputc(c, stderr);
    }
    fputs(n > show ? "\"..." : "\"", stderr);
}
