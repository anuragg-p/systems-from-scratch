/*
 * flat.c - the text in one array: every byte of it, in order, one after
 * another in a single block of memory.
 *
 * It is the obvious way, and reading could not be cheaper: byte i is
 * data[i]. Changing it is another matter. To put a byte in at pos, every
 * byte from pos to the end first moves up one place to make room; to take
 * one out, they all move back down. Typing at the start of a 100 MB file
 * moves 100 MB for every key. When the block is full it moves to one
 * twice as big, as the growable array of 01.01 does.
 *
 * DS_STATS=1 prints "stats: flat array: bytes loaded L, inserts I, erases
 * E, bytes moved M, grows G, bytes copied C": the bytes read from the file
 * at the start, the calls, the bytes moved to open or close a hole, and how
 * many times the text moved to a bigger block, copying C bytes in all.
 *
 * DS_TRACE=1 prints each insert and erase, and the whole text after it:
 *
 *   trace: flat array: insert 1 "X": moved 2 | "aXbc"
 *   trace: flat array: erase 1 1: moved 2 | "abc"
 */
#include <stdlib.h>
#include <string.h>

#include "ds.h"
#include "flat.h"

typedef struct {
    Text   text;         /* first: a Flat is a Text */
    char  *data;         /* the text, text.len bytes of it */
    size_t cap;          /* room for this many before it has to grow */
} Flat;

static struct {
    long loaded, inserts, erases, moved, grows, copied;
} st;

static void print_stats(void)
{
    ds_stats_print("flat array", "bytes loaded %ld, inserts %ld, erases %ld, bytes moved %ld, grows %ld, "
                   "bytes copied %ld", st.loaded, st.inserts, st.erases, st.moved, st.grows, st.copied);
}

static void trace(Flat *f, size_t moved)
{
    text_trace(": moved %zu | ", moved);
    text_trace_bytes(f->data, f->text.len);
    text_trace("\n");
}

/* Insert: everything from pos to the end moves up by n, and the n bytes
 * go into the hole. */
static void flat_insert(Text *t, size_t pos, const char *s, size_t n)
{
    // @build 03.01 insert: move up everything after pos
    Flat *f = (Flat *)t;
    if (t->len + n > f->cap) {
        size_t cap = 2 * f->cap;
        if (cap < t->len + n)
            cap = t->len + n;
        char *data = xmalloc(cap);
        memcpy(data, f->data, t->len);
        free(f->data);
        f->data = data;
        f->cap = cap;
        st.grows++;
        st.copied += (long)t->len;
    }
    memmove(f->data + pos + n, f->data + pos, t->len - pos);
    memcpy(f->data + pos, s, n);
    st.inserts++;
    st.moved += (long)(t->len - pos);
    t->len += n;
    if (text_tracing()) {
        text_trace("trace: flat array: insert %zu ", pos);
        text_trace_bytes(s, n);
        trace(f, t->len - n - pos);
    }
    // @end
}

/* Erase: everything after the n bytes moves down over them. */
static void flat_erase(Text *t, size_t pos, size_t n)
{
    // @build 03.01 erase: move down everything after the hole
    Flat *f = (Flat *)t;
    memmove(f->data + pos, f->data + pos + n, t->len - pos - n);
    st.erases++;
    st.moved += (long)(t->len - pos - n);
    t->len -= n;
    if (text_tracing()) {
        text_trace("trace: flat array: erase %zu %zu", pos, n);
        trace(f, t->len - pos);
    }
    // @end
}

/* Read: the bytes are where they are, in order. */
static void flat_read(Text *t, size_t pos, char *buf, size_t n)
{
    // @build 03.01 read: copy them out
    Flat *f = (Flat *)t;
    memcpy(buf, f->data + pos, n);
    // @end
}

static int flat_write(Text *t, FILE *out)
{
    Flat *f = (Flat *)t;
    return fwrite(f->data, 1, t->len, out) == t->len ? 0 : -1;
}

static void flat_free(Text *t)
{
    Flat *f = (Flat *)t;
    free(f->data);
    free(f);
}

static const TextOps flat_ops = {"flat array", flat_insert, flat_erase, flat_read, flat_write, flat_free};

Text *flat_open(const char *path)
{
    // @build 03.01 open: the whole file, read into one array
    Flat *f = xmalloc(sizeof *f);
    f->text.ops = &flat_ops;
    f->data = text_load(path, &f->text.len, 0);
    f->cap = f->text.len;
    st.loaded += (long)f->text.len;
    ds_stats_at_exit(print_stats);
    return &f->text;
    // @end
}
