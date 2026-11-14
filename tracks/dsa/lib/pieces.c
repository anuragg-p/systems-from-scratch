/*
 * pieces.c - a piece table: the text as a list of pieces of two buffers,
 * neither of which is ever changed, only added to.
 *
 * The first buffer is the file as it was opened. It is not read in at
 * all: it is mapped into memory (mmap), so opening a file of any size
 * copies nothing, and the system reads a page of it only when something
 * asks for bytes on that page. The second, the add buffer, holds every
 * byte inserted since, one after another, in the order they came.
 *
 * The text is then a list of pieces, each a span of one buffer: "bytes 0
 * to 999 of the file", "bytes 0 to 4 of the add buffer", "bytes 1000 to
 * the end of the file". Read in order, the pieces are the text. Inserting
 * appends the new bytes to the add buffer and puts a piece for them in
 * the list, cutting the piece where they go in two; erasing shortens or
 * cuts or drops pieces. Nothing is ever moved but a few numbers. Typing
 * on at the end of what was just typed only makes the last piece longer:
 * its bytes are already the last of the add buffer.
 *
 * The price is finding a position. A piece knows its own length, not
 * where it starts in the text, so finding byte pos means walking the list
 * from the first piece, adding up lengths. Every edit adds a piece or two,
 * so after many edits all over the text every read, insert and erase walks
 * a long list.
 *
 * DS_STATS=1 prints "stats: piece list: bytes mapped M, bytes loaded L,
 * bytes added A, inserts I, erases E, pieces P, pieces walked W": the file
 * mapped (or read, when it could not be), the bytes put in the add buffer,
 * the calls, the pieces in the list at the end, and how many pieces the
 * walks looked at.
 *
 * DS_TRACE=1 prints each call, and every piece after it, in order:
 *
 *   trace: piece list: insert 1 "X": walked 1 | orig 0+1 "a" | add 0+1 "X" | orig 1+2 "bc"
 */
#include <errno.h>
#include <fcntl.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

#include "ds.h"
#include "pieces.h"

typedef struct Piece {
    struct Piece *next;
    Span          span;
} Piece;

typedef struct {
    Text    text;
    Buffers b;
    Piece  *head;        /* the first piece; NULL for an empty text */
} Pieces;

static struct {
    long mapped, loaded, added, inserts, erases, pieces, walked;
} st;

static void print_stats(void)
{
    ds_stats_print("piece list", "bytes mapped %ld, bytes loaded %ld, bytes added %ld, inserts %ld, erases %ld, "
                   "pieces %ld, pieces walked %ld", st.mapped, st.loaded, st.added, st.inserts, st.erases,
                   st.pieces, st.walked);
}

/* ------------------------------------------------------------ the buffers */

void buffers_open(Buffers *b, const char *path, long *mapped, long *loaded)
{
    // @build 03.04 the file mapped: nothing of it read yet
    memset(b, 0, sizeof *b);
    int fd = open(path, O_RDONLY);
    if (fd < 0) {
        if (errno != ENOENT)
            die("%s: %s", path, strerror(errno));
        return;                         /* no file: an empty text */
    }
    struct stat sb;
    if (fstat(fd, &sb) == 0 && S_ISREG(sb.st_mode) && sb.st_size > 0) {
        void *m = mmap(NULL, (size_t)sb.st_size, PROT_READ, MAP_PRIVATE, fd, 0);
        if (m != MAP_FAILED) {
            close(fd);
            b->orig = m;
            b->origlen = (size_t)sb.st_size;
            b->mapped = 1;
            *mapped += (long)b->origlen;
            return;
        }
    }
    close(fd);
    /* Empty, not a plain file, or mmap would not: read it in. */
    b->orig = text_load(path, &b->origlen, 0);
    *loaded += (long)b->origlen;
    // @end
}

size_t buffers_add(Buffers *b, const char *s, size_t n)
{
    // @build 03.04 the add buffer: new bytes go on its end
    if (b->addlen + n > b->addcap) {
        size_t cap = 2 * b->addcap;
        if (cap < b->addlen + n)
            cap = b->addlen + n + 256;
        char *add = xmalloc(cap);
        memcpy(add, b->add, b->addlen);
        free(b->add);
        b->add = add;
        b->addcap = cap;
    }
    memcpy(b->add + b->addlen, s, n);
    b->addlen += n;
    return b->addlen - n;
    // @end
}

const char *span_bytes(const Buffers *b, Span s)
{
    return (s.buf == ORIG ? b->orig : b->add) + s.start;
}

void buffers_free(Buffers *b)
{
    if (b->mapped)
        munmap((void *)b->orig, b->origlen);
    else
        free((void *)b->orig);
    free(b->add);
}

/* ------------------------------------------------------------ the list */

static void trace(Pieces *p, size_t walked)
{
    text_trace(": walked %zu", walked);
    for (Piece *x = p->head; x; x = x->next) {
        text_trace(" | %s %zu+%zu ", x->span.buf == ORIG ? "orig" : "add", x->span.start, x->span.len);
        text_trace_bytes(span_bytes(&p->b, x->span), x->span.len);
    }
    text_trace("\n");
}

static Piece *new_piece(Span s, Piece *next)
{
    Piece *x = xmalloc(sizeof *x);
    x->span = s;
    x->next = next;
    st.pieces++;
    return x;
}

/* The piece that holds byte pos of the text, and where in it (*off); in
 * *prev the piece before it, NULL for the first. At the end of the text
 * there is no such piece: NULL, with *prev the last piece. */
static Piece *find(Pieces *p, size_t pos, Piece **prev, size_t *off)
{
    // @build 03.04 find a position: walk the list from the start
    Piece *before = NULL, *x;
    for (x = p->head; x != NULL; x = x->next) {
        st.walked++;
        if (pos < x->span.len)
            break;
        pos -= x->span.len;
        before = x;
    }
    *prev = before;
    *off = pos;
    return x;
    // @end
}

/* Insert: the bytes go on the end of the add buffer, and a piece for them
 * goes in the list at pos, cutting in two the piece pos is inside. */
static void pieces_insert(Text *t, size_t pos, const char *s, size_t n)
{
    // @build 03.04 insert: a new piece, cutting the one at pos in two
    Pieces *p = (Pieces *)t;
    long walked = st.walked;
    size_t start = buffers_add(&p->b, s, n);
    Piece *prev, *x;
    size_t off;
    x = find(p, pos, &prev, &off);
    if (off == 0 && prev != NULL && prev->span.buf == ADD && prev->span.start + prev->span.len == start) {
        prev->span.len += n;            /* typing on: the piece before is the end of the add buffer */
    } else if (off == 0) {              /* between two pieces, or at either end */
        Piece *y = new_piece((Span){ADD, start, n}, x);
        if (prev != NULL)
            prev->next = y;
        else
            p->head = y;
    } else {                            /* inside x: x, then the new piece, then the rest of x */
        Piece *rest = new_piece((Span){x->span.buf, x->span.start + off, x->span.len - off}, x->next);
        x->next = new_piece((Span){ADD, start, n}, rest);
        x->span.len = off;
    }
    t->len += n;
    st.added += (long)n;
    st.inserts++;
    if (text_tracing()) {
        text_trace("trace: piece list: insert %zu ", pos);
        text_trace_bytes(s, n);
        trace(p, (size_t)(st.walked - walked));
    }
    // @end
}

/* Erase: the piece the first byte is in loses its end (or is cut in two,
 * when all n bytes are inside it), the pieces after it that are wholly
 * erased are dropped, and the next one loses its start. */
static void pieces_erase(Text *t, size_t pos, size_t n)
{
    // @build 03.04 erase: shorten, cut or drop the pieces the bytes are in
    Pieces *p = (Pieces *)t;
    long walked = st.walked;
    size_t left = n;
    Piece *prev, *x;
    size_t off;
    x = find(p, pos, &prev, &off);
    if (off > 0 && off + left < x->span.len) {         /* all inside x: cut it in two */
        x->next = new_piece((Span){x->span.buf, x->span.start + off + left, x->span.len - off - left}, x->next);
        x->span.len = off;
        left = 0;
    } else if (off > 0) {                              /* the end of x goes */
        left -= x->span.len - off;
        x->span.len = off;
        prev = x;
        x = x->next;
    }
    while (left > 0 && left >= x->span.len) {          /* whole pieces go */
        Piece *next = x->next;
        left -= x->span.len;
        free(x);
        st.pieces--;
        x = next;
    }
    if (prev != NULL)
        prev->next = x;
    else
        p->head = x;
    if (left > 0) {                                    /* the start of the next one goes */
        x->span.start += left;
        x->span.len -= left;
    }
    t->len -= n;
    st.erases++;
    if (text_tracing()) {
        text_trace("trace: piece list: erase %zu %zu", pos, n);
        trace(p, (size_t)(st.walked - walked));
    }
    // @end
}

/* Read: walk to the piece pos is in, then copy from it and the pieces
 * after it until there are n bytes. */
static void pieces_read(Text *t, size_t pos, char *buf, size_t n)
{
    // @build 03.04 read: walk to pos, then piece after piece
    Pieces *p = (Pieces *)t;
    Piece *prev, *x;
    size_t off, done = 0;
    x = find(p, pos, &prev, &off);
    while (done < n) {
        size_t k = x->span.len - off < n - done ? x->span.len - off : n - done;
        memcpy(buf + done, span_bytes(&p->b, x->span) + off, k);
        done += k;
        off = 0;
        x = x->next;
    }
    // @end
}

static int pieces_write(Text *t, FILE *out)
{
    Pieces *p = (Pieces *)t;
    for (Piece *x = p->head; x != NULL; x = x->next)
        if (fwrite(span_bytes(&p->b, x->span), 1, x->span.len, out) != x->span.len)
            return -1;
    return 0;
}

static void pieces_free(Text *t)
{
    Pieces *p = (Pieces *)t;
    while (p->head != NULL) {
        Piece *next = p->head->next;
        free(p->head);
        st.pieces--;
        p->head = next;
    }
    buffers_free(&p->b);
    free(p);
}

static const TextOps pieces_ops = {"piece list", pieces_insert, pieces_erase, pieces_read, pieces_write,
                                   pieces_free};

Text *pieces_open(const char *path)
{
    // @build 03.04 open: the file mapped, as one piece
    Pieces *p = xmalloc(sizeof *p);
    p->text.ops = &pieces_ops;
    buffers_open(&p->b, path, &st.mapped, &st.loaded);
    p->head = NULL;
    if (p->b.origlen > 0)
        p->head = new_piece((Span){ORIG, 0, p->b.origlen}, NULL);
    p->text.len = p->b.origlen;
    ds_stats_at_exit(print_stats);
    return &p->text;
    // @end
}
