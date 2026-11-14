/*
 * gap.c - a gap buffer: the text in one array again, but with a gap of
 * unused room in it, kept where the editing is.
 *
 * The text before the gap is at the start of the block, the text after it
 * at the end, and the gap is all the room between them. A byte typed at
 * the gap costs only itself: it goes into the gap, which gets one byte
 * shorter. Erasing next to the gap just widens it. Only an edit somewhere
 * else moves the gap there first, and moving it carries the bytes between
 * where it was and where it goes across to its other side: a jump from
 * the start of a 100 MB file to its middle moves 50 MB, once, and then
 * every key typed there costs nothing again. A gap used up is made again:
 * the text moves to a block twice as big, and the room it gains is the
 * new gap.
 *
 * Editing is mostly typing in one place, so most keys move nothing. Edits
 * all over the text are another matter: each one moves the gap across the
 * distance from the last.
 *
 * DS_STATS=1 prints "stats: gap buffer: bytes loaded L, inserts I, erases
 * E, bytes moved M, grows G, bytes copied C": as flat.c's, M counting the
 * bytes the gap carried across.
 *
 * DS_TRACE=1 prints each call, and the text after it, with the gap as its
 * size in brackets:
 *
 *   trace: gap buffer: insert 1 "X": moved 2 | "aX" [15] "bc"
 */
#include <stdlib.h>
#include <string.h>

#include "ds.h"
#include "gap.h"

#define GAP_MIN 16      /* the least room a new gap has */

typedef struct {
    Text   text;
    char  *data;
    size_t cap;         /* the block: the text and the gap */
    size_t gap;         /* the gap is data[gap, end); the text before it data[0, gap) */
    size_t end;         /* and the text after it data[end, cap) */
} Gap;

static struct {
    long loaded, inserts, erases, moved, grows, copied;
} st;

static void print_stats(void)
{
    ds_stats_print("gap buffer", "bytes loaded %ld, inserts %ld, erases %ld, bytes moved %ld, grows %ld, "
                   "bytes copied %ld", st.loaded, st.inserts, st.erases, st.moved, st.grows, st.copied);
}

static void trace(Gap *g, size_t moved)
{
    text_trace(": moved %zu | ", moved);
    text_trace_bytes(g->data, g->gap);
    text_trace(" [%zu] ", g->end - g->gap);
    text_trace_bytes(g->data + g->end, g->cap - g->end);
    text_trace("\n");
}

/* Move the gap to pos: the bytes between it and pos cross to its other
 * side. Returns how many moved. */
static size_t move_gap(Gap *g, size_t pos)
{
    // @build 03.02 move the gap to pos
    size_t k = 0;
    if (pos < g->gap) {                  /* the bytes in [pos, gap) go to just before end */
        k = g->gap - pos;
        memmove(g->data + g->end - k, g->data + pos, k);
        g->gap = pos;
        g->end -= k;
    } else if (pos > g->gap) {           /* the bytes in [end, end + k) go to gap */
        k = pos - g->gap;
        memmove(g->data + g->gap, g->data + g->end, k);
        g->gap = pos;
        g->end += k;
    }
    st.moved += (long)k;
    return k;
    // @end
}

/* Make the gap at least n bytes: a new block twice as big (or as big as
 * it must be), the text before the gap at its start, the text after the
 * gap at its end, and all the room between. */
static void grow(Gap *g, size_t n)
{
    // @build 03.02 grow: the text into a bigger block, with a wider gap
    size_t after = g->cap - g->end;
    size_t cap = 2 * g->cap;
    if (cap < g->text.len + n + GAP_MIN)
        cap = g->text.len + n + GAP_MIN;
    char *data = xmalloc(cap);
    memcpy(data, g->data, g->gap);
    memcpy(data + cap - after, g->data + g->end, after);
    free(g->data);
    g->data = data;
    g->end = cap - after;
    g->cap = cap;
    st.grows++;
    st.copied += (long)g->text.len;
    // @end
}

/* Insert: the gap goes to pos, and the bytes into the gap. */
static void gap_insert(Text *t, size_t pos, const char *s, size_t n)
{
    // @build 03.02 insert: into the gap, moved to pos first
    Gap *g = (Gap *)t;
    size_t moved = move_gap(g, pos);
    if (g->end - g->gap < n)
        grow(g, n);
    memcpy(g->data + g->gap, s, n);
    g->gap += n;
    t->len += n;
    st.inserts++;
    if (text_tracing()) {
        text_trace("trace: gap buffer: insert %zu ", pos);
        text_trace_bytes(s, n);
        trace(g, moved);
    }
    // @end
}

/* Erase: the gap goes to pos, and the n bytes after it join the gap. */
static void gap_erase(Text *t, size_t pos, size_t n)
{
    // @build 03.02 erase: the gap goes to pos and widens over them
    Gap *g = (Gap *)t;
    size_t moved = move_gap(g, pos);
    g->end += n;
    t->len -= n;
    st.erases++;
    if (text_tracing()) {
        text_trace("trace: gap buffer: erase %zu %zu", pos, n);
        trace(g, moved);
    }
    // @end
}

/* Read: what is before the gap, then what is after it. Position pos of
 * the text is data[pos] before the gap, data[pos + gap size] after it. */
static void gap_read(Text *t, size_t pos, char *buf, size_t n)
{
    // @build 03.02 read: around the gap
    Gap *g = (Gap *)t;
    size_t done = 0;
    if (pos < g->gap) {
        done = g->gap - pos < n ? g->gap - pos : n;
        memcpy(buf, g->data + pos, done);
        pos += done;
    }
    if (done < n)
        memcpy(buf + done, g->data + g->end + (pos - g->gap), n - done);
    // @end
}

static int gap_write(Text *t, FILE *out)
{
    Gap *g = (Gap *)t;
    size_t after = g->cap - g->end;
    if (fwrite(g->data, 1, g->gap, out) != g->gap || fwrite(g->data + g->end, 1, after, out) != after)
        return -1;
    return 0;
}

static void gap_free(Text *t)
{
    Gap *g = (Gap *)t;
    free(g->data);
    free(g);
}

static const TextOps gap_ops = {"gap buffer", gap_insert, gap_erase, gap_read, gap_write, gap_free};

Text *gap_open(const char *path)
{
    // @build 03.02 open: the file read in, and the gap after it
    Gap *g = xmalloc(sizeof *g);
    g->text.ops = &gap_ops;
    g->data = text_load(path, &g->text.len, GAP_MIN);
    g->cap = g->text.len + GAP_MIN;
    g->gap = g->text.len;
    g->end = g->cap;
    st.loaded += (long)g->text.len;
    ds_stats_at_exit(print_stats);
    return &g->text;
    // @end
}
