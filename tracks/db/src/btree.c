/*
 * btree.c - tables and indexes as B-trees of pages.
 *
 * Every table is a B-tree keyed by rowid, and every index a B-tree keyed
 * by (indexed columns..., rowid). A tree is named by the page number of
 * its root, which never changes: that number is what sqlite_schema stores.
 *
 * A B-tree page (after the 100-byte file header on page 1) is:
 *
 *   header, 8 bytes on a leaf, 12 on an interior page:
 *     0  page type: 13 table leaf, 5 table interior, 10 index leaf, 2 index interior
 *     1  offset of the first freeblock (0: none; we never make any)
 *     3  number of cells
 *     5  where the cell content area starts (0 means 65536)
 *     7  fragmented free bytes (we keep this 0)
 *     8  interior pages only: the right-most child's page number
 *   cell pointer array: 2 bytes per cell, in key order
 *   ... free space ...
 *   cell content area: the cells themselves, packed against the page's end
 *
 * The two kinds of tree differ in what their interior pages hold:
 *
 *   A table tree is a B+tree. Rows live only in the leaves; an interior
 *   cell is (left child, rowid), a signpost: every rowid in the left child
 *   is <= that rowid.
 *
 *   An index tree is a plain B-tree. Every cell, interior ones too, is an
 *   entry of the index. Entries in a cell's left child sort before it.
 *
 * A payload too big for its page spills into a chain of overflow pages,
 * each one: 4 bytes next page (0 ends the chain), then data.
 */
#include <stdlib.h>
#include <string.h>

#include "db.h"

/* A page seen as a B-tree node. */
typedef struct Node {
    u32 pgno;
    u8 *d;       /* the page's bytes */
    int h;       /* where the b-tree header starts: 100 on page 1, else 0 */
} Node;

static Node node_at(Pager *p, u32 pgno, int writable)
{
    Node n;
    n.pgno = pgno;
    n.d = writable ? pager_write(p, pgno) : pager_get(p, pgno);
    n.h = pgno == 1 ? 100 : 0;
    int t = n.d[n.h];
    if (t != PAGE_TABLE_LEAF && t != PAGE_TABLE_INTERIOR && t != PAGE_INDEX_LEAF && t != PAGE_INDEX_INTERIOR)
        fatal("database is corrupt: page %u is not a b-tree page (type %d)", pgno, t);
    return n;
}

static Node node_get(Pager *p, u32 pgno) { return node_at(p, pgno, 0); }
static Node node_write(Pager *p, u32 pgno) { return node_at(p, pgno, 1); }

/* A page just allocated: all zeroes, no page type yet. */
static Node node_new(Pager *p, u32 pgno)
{
    Node n = {pgno, pager_write(p, pgno), pgno == 1 ? 100 : 0};
    return n;
}

static int n_type(const Node *n) { return n->d[n->h]; }
static int n_leaf(const Node *n) { return (n_type(n) & 8) != 0; }
static int n_hdrsize(const Node *n) { return n_leaf(n) ? 8 : 12; }
static int n_ncells(const Node *n) { return (int)get2(n->d + n->h + 3); }
static u32 n_right(const Node *n) { return get4(n->d + n->h + 8); }

static u32 n_content(const Node *n)
{
    u32 c = get2(n->d + n->h + 5);
    return c == 0 ? 65536 : c;
}

static u8 *n_cell(const Node *n, int i)
{
    return n->d + get2(n->d + n->h + n_hdrsize(n) + 2 * i);
}

/* Child i of an interior page: the left child of cell i, or for i ==
 * ncells the right-most child. */
static u32 n_child(const Node *n, int i)
{
    return i < n_ncells(n) ? get4(n_cell(n, i)) : n_right(n);
}

static void n_set_child(Node *n, int i, u32 child)
{
    if (i < n_ncells(n))
        put4(n_cell(n, i), child);
    else
        put4(n->d + n->h + 8, child);
}

static int is_leaf_type(int type) { return (type & 8) != 0; }
static int hdrsize_of(int type) { return is_leaf_type(type) ? 8 : 12; }

/* ------------------------------------------------------------ cells */

/* How much of a P-byte payload stays on the page; the rest overflows.
 * The formula is the file format's, so that sqlite3 agrees on where every
 * payload splits. */
static u32 local_size(Pager *p, int type, u32 P)
{
    u32 U = p->usable;
    u32 X = type == PAGE_TABLE_LEAF ? U - 35 : (U - 12) * 64 / 255 - 23;
    if (P <= X)
        return P;
    u32 M = (U - 12) * 32 / 255 - 23;
    u32 K = M + (P - M) % (U - 4);
    return K <= X ? K : M;
}

typedef struct CellInfo {
    u32 child;           /* interior pages: the left child */
    i64 key;             /* table pages: the rowid */
    u32 npayload;        /* bytes of payload in all (0 on a table interior page) */
    const u8 *payload;   /* the part of the payload on this page */
    u32 nlocal;          /* its length */
    u32 ovfl;            /* first overflow page, or 0 */
    u32 len;             /* bytes the cell's fields take */
    u32 size;            /* bytes it occupies on the page: len, but at least 4 */
} CellInfo;

/* Take apart the cell at `cell` on a page of the given type. The four
 * layouts are:
 *   table leaf (13):     varint payload size, varint rowid, payload
 *   table interior (5):  4-byte left child, varint rowid
 *   index leaf (10):     varint payload size, payload
 *   index interior (2):  4-byte left child, varint payload size, payload
 * Only local_size() bytes of the payload are on the page; when that is less
 * than the whole payload, a 4-byte overflow page number follows them. A
 * cell always occupies at least 4 bytes on the page (a file format rule),
 * hence size is len or 4, whichever is more. */
static void cell_parse_type(Pager *p, int type, const u8 *cell, CellInfo *ci)
{
    memset(ci, 0, sizeof *ci);
    // @build 02.01 take a cell apart
    const u8 *q = cell;
    u64 v;
    if (!is_leaf_type(type)) {
        ci->child = get4(q);
        q += 4;
    }
    if (type == PAGE_TABLE_INTERIOR) {
        q += varint_get(q, &v);
        ci->key = (i64)v;
    } else {
        q += varint_get(q, &v);
        ci->npayload = (u32)v;
        if (type == PAGE_TABLE_LEAF) {
            q += varint_get(q, &v);
            ci->key = (i64)v;
        }
        ci->payload = q;
        ci->nlocal = local_size(p, type, ci->npayload);
        q += ci->nlocal;
        if (ci->nlocal < ci->npayload) {
            ci->ovfl = get4(q);
            q += 4;
        }
    }
    ci->len = (u32)(q - cell);
    ci->size = ci->len < 4 ? 4 : ci->len;
    // @end
}

static void cell_parse(Pager *p, const Node *n, int i, CellInfo *ci)
{
    cell_parse_type(p, n_type(n), n_cell(n, i), ci);
}

// @from 02.02
/* Write overflow pages holding data[0..n) and return the first one. */
static u32 overflow_write(Pager *p, const u8 *data, u32 n)
{
    u32 first = 0, prev = 0, room = p->usable - 4;
    while (n > 0) {
        u32 pgno = page_alloc(p);
        u8 *d = pager_write(p, pgno);
        u32 take = n < room ? n : room;
        put4(d, 0);
        memcpy(d + 4, data, take);
        if (prev)
            put4(pager_write(p, prev), pgno);
        else
            first = pgno;
        prev = pgno;
        data += take;
        n -= take;
    }
    return first;
}
// @end

// @from 02.05
static void overflow_free(Pager *p, u32 pgno, u32 n)
{
    u32 room = p->usable - 4;
    while (pgno && n > 0) {
        u32 next = get4(pager_get(p, pgno));
        page_free(p, pgno);
        pgno = next;
        n = n > room ? n - room : 0;
    }
}
// @end

/* The whole payload of a cell: on the page if it all fits, else gathered
 * into buf from the overflow chain. */
static const u8 *payload_of(Pager *p, const CellInfo *ci, Buf *buf)
{
    if (ci->nlocal == ci->npayload)
        return ci->payload;
    buf->n = 0;
    buf_put(buf, ci->payload, ci->nlocal);
    u32 left = ci->npayload - ci->nlocal, pgno = ci->ovfl, room = p->usable - 4;
    while (left > 0) {
        if (pgno == 0 || pgno > p->npages)
            fatal("database is corrupt: overflow chain ends early");
        const u8 *d = pager_get(p, pgno);
        u32 take = left < room ? left : room;
        buf_put(buf, d + 4, take);
        left -= take;
        pgno = get4(d);
    }
    return buf->p;
}

// @from 02.02
/* Build a cell of the given type in out (room for page_size + 32 bytes),
 * spilling into overflow pages as needed. Returns its size on the page. */
static u32 cell_build(Pager *p, int type, u32 child, i64 rowid, const u8 *payload, u32 n, u8 *out)
{
    u8 *q = out;
    if (!is_leaf_type(type)) {
        put4(q, child);
        q += 4;
    }
    if (type == PAGE_TABLE_INTERIOR) {
        q += varint_put(q, (u64)rowid);
    } else {
        q += varint_put(q, n);
        if (type == PAGE_TABLE_LEAF)
            q += varint_put(q, (u64)rowid);
        u32 local = local_size(p, type, n);
        memcpy(q, payload, local);
        q += local;
        if (local < n) {
            put4(q, overflow_write(p, payload + local, n - local));
            q += 4;
        }
    }
    u32 len = (u32)(q - out);
    while (len < 4)
        out[len++] = 0;
    return len;
}
// @end

/* ------------------------------------------------------------ searching a page */

/* What to look for: a rowid in a table, or a key record in an index. In an
 * index, only the first nfields fields are compared; bias says where the
 * probe goes among entries equal to it in those fields: -1 before them
 * all, +1 after them all. */
typedef struct SeekKey {
    int intkey;
    i64 rowid;
    const u8 *rec;
    u32 nrec;
    int nfields;
    int bias;
} SeekKey;

static Buf cmp_buf;

/* Negative, zero or positive as cell i of n sorts before, with or after k. */
static int cell_compare(Pager *p, const Node *n, int i, const SeekKey *k)
{
    CellInfo ci;
    cell_parse(p, n, i, &ci);
    if (k->intkey)
        return ci.key < k->rowid ? -1 : ci.key > k->rowid;
    const u8 *rec = payload_of(p, &ci, &cmp_buf);
    int c = record_compare(rec, ci.npayload, k->rec, k->nrec, k->nfields);
    return c ? c : -k->bias;
}

/* The first cell of n that does not sort before k: its index, or ncells.
 * The cells of a page are in key order, so this is a binary search. On a
 * leaf the result is where k is or would go; on an interior page it is the
 * child to descend into. */
static int node_search(Pager *p, const Node *n, const SeekKey *k)
{
    // @build 02.01 binary search a page
    int lo = 0, hi = n_ncells(n);
    while (lo < hi) {
        int mid = lo + (hi - lo) / 2;
        if (cell_compare(p, n, mid, k) < 0)
            lo = mid + 1;
        else
            hi = mid;
    }
    return lo;
    // @end
}

// @from 02.02
/* ------------------------------------------------------------ rebuilding pages */

/* A list of cells copied out of their pages, to be laid out again. */
typedef struct CellList {
    int n, cap;
    u32 *off, *size;
    Buf bytes;
    u32 right;           /* interior: the right-most child */
} CellList;

static void cells_add(CellList *cl, const u8 *cell, u32 size)
{
    if (cl->n == cl->cap) {
        cl->cap = cl->cap ? 2 * cl->cap : 64;
        cl->off = xrealloc(cl->off, (size_t)cl->cap * sizeof(u32));
        cl->size = xrealloc(cl->size, (size_t)cl->cap * sizeof(u32));
    }
    cl->off[cl->n] = (u32)cl->bytes.n;
    cl->size[cl->n] = size;
    buf_put(&cl->bytes, cell, size);
    cl->n++;
}

static u8 *cells_at(CellList *cl, int i) { return cl->bytes.p + cl->off[i]; }

static void cells_from_node(Pager *p, CellList *cl, const Node *n)
{
    for (int i = 0; i < n_ncells(n); i++) {
        CellInfo ci;
        cell_parse(p, n, i, &ci);
        cells_add(cl, n_cell(n, i), ci.size);
    }
    cl->right = n_leaf(n) ? 0 : n_right(n);
}

static void cells_free(CellList *cl)
{
    free(cl->off);
    free(cl->size);
    buf_free(&cl->bytes);
    memset(cl, 0, sizeof *cl);
}

static u32 cells_bytes(CellList *cl, int from, int to)
{
    u32 sum = 0;
    for (int i = from; i < to; i++)
        sum += cl->size[i] + 2;
    return sum;
}

/* Lay out page n from scratch as a page of `type` holding cells [from, to)
 * of cl: header, cell pointers, and the cells packed against the end. */
static void node_fill(Pager *p, Node *n, int type, CellList *cl, int from, int to, u32 right)
{
    int hs = hdrsize_of(type);
    if (cells_bytes(cl, from, to) > p->usable - (u32)n->h - (u32)hs)
        fatal("internal error: %d cells do not fit on page %u", to - from, n->pgno);
    u8 *h = n->d + n->h;
    u32 content = p->usable;
    for (int i = from; i < to; i++) {
        content -= cl->size[i];
        memcpy(n->d + content, cells_at(cl, i), cl->size[i]);
        put2(h + hs + 2 * (i - from), content);
    }
    h[0] = (u8)type;
    put2(h + 1, 0);
    put2(h + 3, (u32)(to - from));
    put2(h + 5, content == 65536 ? 0 : content);
    h[7] = 0;
    if (!is_leaf_type(type))
        put4(h + 8, right);
}

/* Rewrite n with its cells packed together, dropping cell `skip` (-1 for none). */
static void node_rebuild(Pager *p, Node *n, int skip)
{
    CellList cl = {0};
    cells_from_node(p, &cl, n);
    if (skip >= 0) {
        memmove(cl.off + skip, cl.off + skip + 1, (size_t)(cl.n - skip - 1) * sizeof(u32));
        memmove(cl.size + skip, cl.size + skip + 1, (size_t)(cl.n - skip - 1) * sizeof(u32));
        cl.n--;
    }
    node_fill(p, n, n_type(n), &cl, 0, cl.n, cl.right);
    cells_free(&cl);
}

static void node_remove(Pager *p, Node *n, int i)
{
    node_rebuild(p, n, i);
}

/* Bytes the cells of n take, not counting their pointers. */
static u32 node_used(Pager *p, const Node *n)
{
    u32 sum = 0;
    for (int i = 0; i < n_ncells(n); i++) {
        CellInfo ci;
        cell_parse(p, n, i, &ci);
        sum += ci.size;
    }
    return sum;
}
// @end

/* Put a cell into page n so that it becomes cell i. Returns 0, leaving the
 * page alone, if it cannot fit even with the page's cells packed together;
 * returns 1 otherwise. A page grows from both ends: cell pointers from the
 * header down, cell content from the end of the page up. */
static int node_insert(Pager *p, Node *n, int i, const u8 *cell, u32 size)
{
    // @build 02.02 put a cell into a page
    int nc = n_ncells(n), hs = n_hdrsize(n);
    /* The gap between pointer array and content area must hold the cell and
     * its 2-byte pointer. If it does not, but the total free space would
     * suffice, packing the cells together closes the gaps left by removals. */
    u32 ptrs_end = (u32)(n->h + hs + 2 * (nc + 1));
    u32 content = n_content(n);
    if (ptrs_end + size > content) {
        u32 room = p->usable - (u32)n->h - (u32)hs;
        if (node_used(p, n) + size + 2 * (u32)(nc + 1) > room)
            return 0;
        node_rebuild(p, n, -1);
        content = n_content(n);
    }
    content -= size;
    memcpy(n->d + content, cell, size);
    u8 *ptr = n->d + n->h + hs + 2 * i;
    memmove(ptr + 2, ptr, (size_t)(2 * (nc - i)));
    put2(ptr, content);
    put2(n->d + n->h + 3, (u32)(nc + 1));
    put2(n->d + n->h + 5, content);
    return 1;
    // @end
}

// @from 02.02
/* ------------------------------------------------------------ insert */

static void insert_cell(Cursor *c, int L, int i, const u8 *cell, u32 size);
static void seek_raw(Cursor *c, const SeekKey *k);  // @from 02.03

/* Where to cut cl (which overflows one page) so that both halves fit and
 * are about the same size, or -1 if no cut into two will do. In a table
 * leaf the halves are [0, m) and [m, n); everywhere else cell m goes up to
 * the parent, between them. */
static int split_point(Pager *p, int type, CellList *cl)
{
    int up = type != PAGE_TABLE_LEAF;
    u32 cap = p->usable - (u32)hdrsize_of(type);
    u32 total = cells_bytes(cl, 0, cl->n);
    int best = -1;
    u32 best_diff = 0, left = 0;
    for (int m = 1; m < cl->n - up; m++) {
        left += cl->size[m - 1] + 2;
        u32 right = total - left - (up ? cl->size[m] + 2 : 0);
        if (left > cap || right > cap)
            continue;
        u32 diff = left > right ? left - right : right - left;
        if (best < 0 || diff < best_diff) {
            best = m;
            best_diff = diff;
        }
    }
    return best;    /* -1: no two pages can hold them (see partition) */
}
// @end

/* Where to split the table leaf at level L of the path, whose cells are cl
 * with a new cell put in at newidx, or -1 for "split in the middle as
 * usual". Rows are usually inserted in rowid order, each one after the last.
 * A split down the middle would then leave every left half half empty
 * forever, so for an append the old cells stay put and the new one goes
 * alone on the right: the result is cl->n - 1. */
static int append_split(Cursor *c, int L, CellList *cl, int newidx)
{
    // @build 07.03 split for an append
    /* An append is a new last cell on the right-most leaf of the whole
     * tree: on every level above L the path went down the right-most child,
     * which shows as idx equal to that page's cell count. */
    if (newidx != cl->n - 1)
        return -1;
    for (int l = 0; l < L; l++) {
        Node n = node_get(c->pager, c->pgno[l]);
        if (c->idx[l] != n_ncells(&n))
            return -1;
    }
    stats.append_splits++;
    return cl->n - 1;
    // @end
}

// @from 02.02
#define MAX_PARTS 8

/* Cut cl into parts that each fit on a page: two, at m, when m >= 0;
 * else as many as it takes, filling each page in turn. A page can need
 * three: cells of 2000, 4000 and 2000 bytes do not split into two pages
 * of 4096. Fills gs[] and ge[] with each part's cells [gs, ge); between
 * parts, unless this is a table leaf, one cell goes up to the parent.
 * Returns the number of parts. */
static int partition(Pager *p, int type, CellList *cl, int m, int *gs, int *ge)
{
    int up = type != PAGE_TABLE_LEAF;
    if (m >= 0) {
        gs[0] = 0;
        ge[0] = m;
        gs[1] = m + up;
        ge[1] = cl->n;
        return 2;
    }
    u32 cap = p->usable - (u32)hdrsize_of(type);
    int k = 0, start = 0;
    for (;;) {
        if (k == MAX_PARTS)
            fatal("internal error: %d cells need more than %d pages", cl->n, MAX_PARTS);
        if (cells_bytes(cl, start, cl->n) <= cap) {
            gs[k] = start;
            ge[k] = cl->n;
            return k + 1;
        }
        int e = start;
        while (e < cl->n && cells_bytes(cl, start, e + 1) <= cap)
            e++;
        if (up && e + 1 >= cl->n)
            e--;                 /* leave a cell for the last part */
        if (e <= start)
            fatal("internal error: a cell does not fit on a page");
        gs[k] = start;
        ge[k] = e;
        k++;
        start = e + up;
    }
}

/* How many levels of pages are below page pgno. */
static int node_height(Pager *p, u32 pgno)
{
    int h = 0;
    for (;;) {
        Node n = node_get(p, pgno);
        if (n_leaf(&n))
            return h;
        pgno = n_child(&n, 0);
        if (++h > MAX_DEPTH)
            fatal("database is corrupt: b-tree is too deep");
    }
}

// @from 02.03
/* Put the dividers of a split into the parent level, in key order. The
 * last goes where the parent points at the split page; inserting it may
 * split the parent too, so each earlier divider then finds its place
 * afresh by searching the tree for its own key: just before the next one. */
// @else
// /* Put the last divider of a split into the parent level, where the
//  * parent points at the split page. A split into three pages has an
//  * earlier one too, which needs a search of the tree to find its place. */
// @end
static void insert_dividers(Cursor *c, int L, int h, u8 **div, u32 *dsize, int nd)
{
    Pager *p = c->pager;  // @from 02.03
    insert_cell(c, L - 1, c->idx[L - 1], div[nd - 1], dsize[nd - 1]);
    // @from 02.03
    int itype = c->intkey ? PAGE_TABLE_INTERIOR : PAGE_INDEX_INTERIOR;
    for (int j = nd - 2; j >= 0; j--) {
        CellInfo ci;
        Buf key = {0};
        cell_parse_type(p, itype, div[j], &ci);
        SeekKey k = {c->intkey, ci.key, NULL, 0, 1 << 30, -1};
        if (!c->intkey) {
            const u8 *pl = payload_of(p, &ci, &key);
            if (pl != key.p) {
                key.n = 0;
                buf_put(&key, pl, ci.npayload);
            }
            k.rec = key.p;
            k.nrec = ci.npayload;
        }
        seek_raw(c, &k);
        int level = c->depth - 2 - h;
        insert_cell(c, level, c->idx[level], div[j], dsize[j]);
        buf_free(&key);
    }
    // @end
}
// @end

/* The page at level L of the path cannot hold cl (its cells, with a new
 * one already among them at newidx, or -1). Split them over pages: new
 * pages take the left parts, the page itself keeps the last part, so the
 * parent's pointer to it stays right; a divider for each new page goes
 * into the parent, just before that pointer. */
static void split(Cursor *c, int L, CellList *cl, int newidx)
{
    Pager *p = c->pager;
    Node n = node_write(p, c->pgno[L]);
    int type = n_type(&n), leaf = n_leaf(&n);
    int h = node_height(p, n.pgno);
    int m = -1;
    // @from 07.03
    if (type == PAGE_TABLE_LEAF)
        m = append_split(c, L, cl, newidx);
    // @end
    if (m < 0)
        m = split_point(p, type, cl);
    int gs[MAX_PARTS], ge[MAX_PARTS];
    int k = partition(p, type, cl, m, gs, ge);
    u8 *div[MAX_PARTS];
    u32 dsize[MAX_PARTS];
    // @build 02.02 split a page
    /* cl's cells are cut into k parts, part g being cells [gs[g], ge[g]).
     * Each part but the last goes on a new page; the last stays on page n.
     * For each new page a divider is built in div[g], the cell the parent
     * will hold, depending on the kind of page:
     *   table leaf:  page g's number, then the rowid of its last cell.
     *   index leaf:  cell ge[g] is an entry and moves up, so the divider is
     *                page g's number followed by that cell's bytes.
     *   interior:    cell ge[g] moves up too. Its left child becomes page
     *                g's right-most child, and the divider is the cell with
     *                its first 4 bytes replaced by page g's number.
     * The last part keeps cl->right. */
    for (int g = 0; g < k; g++) {
        u32 pgno;
        Node pn;
        if (g < k - 1) {
            pgno = page_alloc(p);
            pn = node_new(p, pgno);
        } else {
            pgno = c->pgno[L];
            pn = node_write(p, pgno);
        }
        CellInfo ci;
        u32 right = 0;
        if (!leaf) {
            if (g < k - 1) {
                cell_parse_type(p, type, cells_at(cl, ge[g]), &ci);
                right = ci.child;
            } else {
                right = cl->right;
            }
        }
        node_fill(p, &pn, type, cl, gs[g], ge[g], right);
        if (g == k - 1)
            break;
        div[g] = xmalloc(p->page_size + 32);
        if (type == PAGE_TABLE_LEAF) {
            cell_parse_type(p, type, cells_at(cl, ge[g] - 1), &ci);
            put4(div[g], pgno);
            dsize[g] = 4 + (u32)varint_put(div[g] + 4, (u64)ci.key);
        } else if (type == PAGE_INDEX_LEAF) {
            cell_parse_type(p, type, cells_at(cl, ge[g]), &ci);
            put4(div[g], pgno);
            memcpy(div[g] + 4, cells_at(cl, ge[g]), ci.len);
            dsize[g] = 4 + ci.len;
        } else {
            cell_parse_type(p, type, cells_at(cl, ge[g]), &ci);
            memcpy(div[g], cells_at(cl, ge[g]), ci.len);
            put4(div[g], pgno);
            dsize[g] = ci.len;
        }
    }
    stats.splits++;
    // @end
    insert_dividers(c, L, h, div, dsize, k - 1);
    for (int g = 0; g < k - 1; g++)
        free(div[g]);
}

/* The root is full. Its page number must not change (sqlite_schema holds
 * it), so instead of splitting it, move everything in it down into a new
 * page and make the root an interior page whose only child is that page.
 * The tree is now one level deeper, and the old root's content can split
 * like any other page. */
static void grow_root(Cursor *c)
{
    Pager *p = c->pager;
    // @build 02.03 grow the tree
    /* Copy the root's content to a new page, then turn the root into an
     * interior page of the matching kind whose only child is that page. */
    Node root = node_write(p, c->root);
    u32 child = page_alloc(p);
    Node ch = node_new(p, child);
    root = node_write(p, c->root);
    CellList cl = {0};
    cells_from_node(p, &cl, &root);
    node_fill(p, &ch, n_type(&root), &cl, 0, cl.n, cl.right);
    CellList none = {0};
    node_fill(p, &root, c->intkey ? PAGE_TABLE_INTERIOR : PAGE_INDEX_INTERIOR, &none, 0, 0, child);
    cells_free(&cl);
    /* The path gets one level longer: level 0 is still the root, with idx
     * 0, and level 1 is the new page with the root's old idx. */
    if (c->depth == MAX_DEPTH)
        fatal("b-tree is too deep");
    memmove(&c->pgno[1], &c->pgno[0], (size_t)c->depth * sizeof c->pgno[0]);
    memmove(&c->idx[1], &c->idx[0], (size_t)c->depth * sizeof c->idx[0]);
    c->pgno[1] = child;
    c->idx[0] = 0;
    c->depth++;
    // @end
}

// @from 02.02
/* Make `cell` cell i of the page at level L of the path, splitting pages
 * (and growing the tree) as needed. */
static void insert_cell(Cursor *c, int L, int i, const u8 *cell, u32 size)
{
    Pager *p = c->pager;
    Node n = node_write(p, c->pgno[L]);
    if (node_insert(p, &n, i, cell, size))
        return;
    // @from 02.03
    if (L == 0) {
        grow_root(c);
        L = 1;
        n = node_write(p, c->pgno[L]);
        if (node_insert(p, &n, i, cell, size))
            return;
    }
    // @end
    CellList cl = {0};
    cells_from_node(p, &cl, &n);
    cells_add(&cl, cell, size);
    /* move the new cell from the end to position i */
    u32 off = cl.off[cl.n - 1], sz = cl.size[cl.n - 1];
    memmove(cl.off + i + 1, cl.off + i, (size_t)(cl.n - 1 - i) * sizeof(u32));
    memmove(cl.size + i + 1, cl.size + i, (size_t)(cl.n - 1 - i) * sizeof(u32));
    cl.off[i] = off;
    cl.size[i] = sz;
    split(c, L, &cl, i);
    cells_free(&cl);
}
// @end

// @from 02.03
/* ------------------------------------------------------------ cursors */

void cursor_open(Cursor *c, Pager *p, u32 root, int intkey)
{
    memset(c, 0, sizeof *c);
    c->pager = p;
    c->root = root;
    c->intkey = intkey;
}

void cursor_close(Cursor *c)
{
    buf_free(&c->buf);
    c->valid = 0;
    c->depth = 0;
}
// @end

/* Go from the root down to a leaf, choosing at every page the child where
 * k belongs. The path ends at k's place in that leaf: the first cell that
 * does not sort before k, which may be one past the last cell. */
static void seek_raw(Cursor *c, const SeekKey *k)
{
    // @build 02.03 go down from the root
    c->depth = 0;
    u32 pgno = c->root;
    for (;;) {
        if (c->depth == MAX_DEPTH)
            fatal("database is corrupt: b-tree %u is too deep", c->root);
        Node n = node_get(c->pager, pgno);
        int i = node_search(c->pager, &n, k);
        c->pgno[c->depth] = pgno;
        c->idx[c->depth] = i;
        c->depth++;
        if (n_leaf(&n))
            return;
        pgno = n_child(&n, i);
    }
    // @end
}

// @from 02.04
/* Set the cursor's rowid and payload from the cell it is at. */
static void cursor_load(Cursor *c)
{
    Node n = node_get(c->pager, c->pgno[c->depth - 1]);
    CellInfo ci;
    cell_parse(c->pager, &n, c->idx[c->depth - 1], &ci);
    c->rowid = ci.key;
    c->payload = payload_of(c->pager, &ci, &c->buf);
    c->npayload = ci.npayload;
    c->valid = 1;
}
// @end

/* From the last page of the path, keep going down the child at idx with
 * idx 0 on each new page, until a leaf is reached. */
static void descend_leftmost(Cursor *c)
{
    // @build 02.04 down to the leftmost leaf
    for (;;) {
        Node n = node_get(c->pager, c->pgno[c->depth - 1]);
        if (n_leaf(&n))
            return;
        if (c->depth == MAX_DEPTH)
            fatal("database is corrupt: b-tree %u is too deep", c->root);
        c->pgno[c->depth] = n_child(&n, c->idx[c->depth - 1]);
        c->idx[c->depth] = 0;
        c->depth++;
    }
    // @end
}

/* The path ends at a leaf position that may be past the leaf's last cell.
 * Move to the first entry at or after it, in key order. Returns 1 at an
 * entry, 0 if there is none (the end of the tree). */
static int settle(Cursor *c)
{
    // @build 02.04 climb to the next entry
    for (;;) {
        Node n = node_get(c->pager, c->pgno[c->depth - 1]);
        if (c->idx[c->depth - 1] < n_ncells(&n)) {
            cursor_load(c);
            return 1;
        }
        /* This leaf is used up: climb to the nearest level whose idx is
         * below its page's cell count, i.e. we came up out of a child that
         * is not the right-most one. None means the tree is done. */
        for (;;) {
            if (c->depth == 1) {
                c->valid = 0;
                return 0;
            }
            c->depth--;
            Node up = node_get(c->pager, c->pgno[c->depth - 1]);
            if (c->idx[c->depth - 1] < n_ncells(&up))
                break;
        }
        /* In an index, the interior cell climbed to sits between child idx
         * and child idx + 1 and is itself the next entry. In a table,
         * interior cells are only signposts: go on to the next child. */
        if (!c->intkey) {
            cursor_load(c);
            return 1;
        }
        c->idx[c->depth - 1]++;
        descend_leftmost(c);
    }
    // @end
}

// @from 02.04
int cursor_first(Cursor *c)
{
    c->depth = 1;
    c->pgno[0] = c->root;
    c->idx[0] = 0;
    descend_leftmost(c);
    return settle(c);
}

int cursor_next(Cursor *c)
{
    if (!c->valid)
        return 0;
    Node n = node_get(c->pager, c->pgno[c->depth - 1]);
    c->idx[c->depth - 1]++;
    if (!n_leaf(&n))
        descend_leftmost(c);    /* was at an index's interior cell */
    return settle(c);
}

/* Go to the first row whose rowid is >= rowid. Returns 1 if there is one. */
int cursor_seek_rowid(Cursor *c, i64 rowid)
{
    SeekKey k = {1, rowid, NULL, 0, 0, 0};
    seek_raw(c, &k);
    return settle(c);
}

/* Go to the first index entry at or after key (comparing nfields fields;
 * bias -1 lands on the first entry equal to key, +1 just after the last). */
int cursor_seek_key(Cursor *c, const u8 *key, u32 n, int nfields, int bias)
{
    SeekKey k = {0, 0, key, n, nfields, bias};
    seek_raw(c, &k);
    return settle(c);
}
// @end

// @from 02.03
i64 btree_max_rowid(Cursor *c)
{
    u32 pgno = c->root;
    for (;;) {
        Node n = node_get(c->pager, pgno);
        if (n_leaf(&n)) {
            int nc = n_ncells(&n);
            if (nc == 0)
                return 0;
            CellInfo ci;
            cell_parse(c->pager, &n, nc - 1, &ci);
            return ci.key;
        }
        pgno = n_right(&n);
    }
}

/* Insert a row (table: rowid and record; a row with that rowid already
 * there is replaced) or an index entry (payload is the key record). The
 * cursor is left unpositioned. */
void btree_insert(Cursor *c, i64 rowid, const u8 *payload, u32 n)
{
    Pager *p = c->pager;
    SeekKey k = {c->intkey, rowid, payload, n, 1 << 30, -1};
    seek_raw(c, &k);
    int L = c->depth - 1, i = c->idx[L];
    Node leaf = node_get(p, c->pgno[L]);
    if (c->intkey && i < n_ncells(&leaf)) {
        CellInfo old;
        cell_parse(p, &leaf, i, &old);
        if (old.key == rowid) {
            leaf = node_write(p, c->pgno[L]);
            // @from 02.05
            if (old.ovfl)
                overflow_free(p, old.ovfl, old.npayload - old.nlocal);
            // @end
            node_remove(p, &leaf, i);
        }
    }
    u8 *cell = xmalloc(p->page_size + 32);
    u32 size = cell_build(p, n_type(&leaf), 0, rowid, payload, n, cell);
    insert_cell(c, L, i, cell, size);
    free(cell);
    c->valid = 0;
    c->depth = 0;
}
// @end

// @from 02.05
/* ------------------------------------------------------------ delete */

/* The tree is one page shorter than it could be: the root has no cells,
 * only a right-most child. Copy that child up into the root. */
static void collapse_root(Cursor *c)
{
    Pager *p = c->pager;
    Node root = node_write(p, c->root);
    u32 child = n_right(&root);
    Node ch = node_get(p, child);
    CellList cl = {0};
    cells_from_node(p, &cl, &ch);
    /* Page 1 has 100 bytes less room; if the child does not fit there the
     * root stays as it is, which the file format allows for page 1 only. */
    if (cells_bytes(&cl, 0, cl.n) <= p->usable - (u32)root.h - (u32)hdrsize_of(n_type(&ch))) {
        node_fill(p, &root, n_type(&ch), &cl, 0, cl.n, cl.right);
        page_free(p, child);
    }
    cells_free(&cl);
}

/* The divider between two siblings, as a cell of their own level: a merge
 * pulls it down between their cells. Nothing for a table leaf (the divider
 * only repeated a rowid that is still in the leaf); for an index leaf, the
 * entry itself; for an interior page, the entry or rowid with the left
 * sibling's right-most child as its child. */
static void add_divider(Pager *p, CellList *cl, int type, const u8 *gcell, int gtype, u32 leftright)
{
    if (type == PAGE_TABLE_LEAF)
        return;
    CellInfo ci;
    cell_parse_type(p, gtype, gcell, &ci);
    u8 *tmp = xmalloc(ci.len + 8);
    u32 len;
    if (type == PAGE_INDEX_LEAF) {
        len = ci.len - 4;
        memcpy(tmp, gcell + 4, len);
        while (len < 4)
            tmp[len++] = 0;
    } else {
        memcpy(tmp, gcell, ci.len);
        put4(tmp, leftright);
        len = ci.len;
    }
    cells_add(cl, tmp, len);
    free(tmp);
}

/* The page at level L of the path has no cells left. A page with no cells
 * may not stay in the tree (an index entry must be found on its way down,
 * and every leaf must stay at the same depth), so merge it into a sibling:
 * the sibling takes its content and the divider between them, the parent
 * loses that divider, and the empty page goes to the freelist. If the
 * sibling overflows it splits again (that is a redistribution); if the
 * parent is now empty in turn, fix it the same way, one level up. */
static void fix_empty(Cursor *c, int L)
{
    Pager *p = c->pager;
    Node n = node_write(p, c->pgno[L]);
    Node g = node_write(p, c->pgno[L - 1]);
    int i = c->idx[L - 1], ng = n_ncells(&g), type = n_type(&n), gtype = n_type(&g);
    stats.merges++;
    if (ng == 0) {
        /* Only page 1 may be a root with no cells. Its single child is
         * this empty page: drop it, keeping the tree's shape. */
        if (n_leaf(&n)) {
            CellList none = {0};
            node_fill(p, &g, type, &none, 0, 0, 0);
        } else {
            put4(g.d + g.h + 8, n_right(&n));
        }
        page_free(p, n.pgno);
        return;
    }
    CellList cl = {0};
    u32 target;
    int tpos;
    if (i > 0) {
        target = n_child(&g, i - 1);
        Node s = node_get(p, target);
        cells_from_node(p, &cl, &s);
        add_divider(p, &cl, type, n_cell(&g, i - 1), gtype, cl.right);
        cl.right = n_leaf(&n) ? 0 : n_right(&n);
        node_remove(p, &g, i - 1);
        n_set_child(&g, i - 1, target);
        tpos = i - 1;
    } else {
        target = n_child(&g, 1);
        Node r = node_get(p, target);
        add_divider(p, &cl, type, n_cell(&g, 0), gtype, n_leaf(&n) ? 0 : n_right(&n));
        CellList rc = {0};
        cells_from_node(p, &rc, &r);
        for (int k = 0; k < rc.n; k++)
            cells_add(&cl, cells_at(&rc, k), rc.size[k]);
        cl.right = rc.right;
        cells_free(&rc);
        node_remove(p, &g, 0);
        tpos = 0;
    }
    page_free(p, n.pgno);
    Node t = node_write(p, target);
    c->pgno[L] = target;
    c->idx[L - 1] = tpos;
    int fits = cells_bytes(&cl, 0, cl.n) <= p->usable - (u32)t.h - (u32)hdrsize_of(type);
    if (fits)
        node_fill(p, &t, type, &cl, 0, cl.n, cl.right);
    else
        split(c, L, &cl, -1);
    cells_free(&cl);
    if (fits) {
        g = node_get(p, c->pgno[L - 1]);
        if (n_ncells(&g) == 0) {
            if (L - 1 == 0)
                collapse_root(c);
            else
                fix_empty(c, L - 1);
        }
    }
}

/* Remove the cell at the end of the path from its leaf; then mend the tree
 * if the leaf is empty. */
static void leaf_delete(Cursor *c)
{
    Pager *p = c->pager;
    int L = c->depth - 1;
    Node n = node_write(p, c->pgno[L]);
    CellInfo ci;
    cell_parse(p, &n, c->idx[L], &ci);
    if (ci.ovfl)
        overflow_free(p, ci.ovfl, ci.npayload - ci.nlocal);
    node_remove(p, &n, c->idx[L]);
    if (n_ncells(&n) == 0 && L > 0)
        fix_empty(c, L);
}
// @end

/* Delete the entry the cursor is at. The cursor is left unpositioned.
 * An entry in a leaf is simply removed. An index entry in an interior cell
 * cannot just go, because its left child hangs off it: it is replaced by
 * its predecessor, the last entry of the right-most leaf below its left
 * child. That entry is then in the tree twice, and the copy in the leaf,
 * which sorts first, is deleted. */
void btree_delete(Cursor *c)
{
    Pager *p = c->pager;
    if (!c->valid)
        fatal("internal error: btree_delete with no entry");
    // @build 02.05 delete an entry
    int L = c->depth - 1;
    Node n = node_get(p, c->pgno[L]);
    if (n_leaf(&n)) {
        leaf_delete(c);
    } else {
        int i = c->idx[L];
        CellInfo ci;
        cell_parse(p, &n, i, &ci);
        u32 pg = ci.child;
        for (;;) {
            Node m = node_get(p, pg);
            if (n_leaf(&m)) {
                CellInfo pi;
                cell_parse(p, &m, n_ncells(&m) - 1, &pi);
                Buf pred = {0};
                const u8 *pp = payload_of(p, &pi, &pred);
                Buf key = {0};
                buf_put(&key, pp, pi.npayload);
                buf_free(&pred);
                u8 *cell = xmalloc(p->page_size + 32);
                u32 size = cell_build(p, n_type(&n), ci.child, 0, key.p, (u32)key.n, cell);
                Node w = node_write(p, c->pgno[L]);
                if (ci.ovfl)
                    overflow_free(p, ci.ovfl, ci.npayload - ci.nlocal);
                node_remove(p, &w, i);
                c->depth = L + 1;
                insert_cell(c, L, i, cell, size);
                free(cell);
                SeekKey k = {0, 0, key.p, (u32)key.n, 1 << 30, -1};
                seek_raw(c, &k);
                leaf_delete(c);
                buf_free(&key);
                break;
            }
            pg = n_right(&m);
        }
    }
    c->valid = 0;
    c->depth = 0;
    // @end
}

// @from 02.02
/* ------------------------------------------------------------ pages for trees */

u32 btree_create(Pager *p, int intkey)
{
    u32 pgno = page_alloc(p);
    Node n = node_new(p, pgno);
    CellList none = {0};
    node_fill(p, &n, intkey ? PAGE_TABLE_LEAF : PAGE_INDEX_LEAF, &none, 0, 0, 0);
    return pgno;
}
// @end

// @from 02.05
static void drop_page(Pager *p, u32 pgno, int depth)
{
    if (depth > MAX_DEPTH)
        fatal("database is corrupt: b-tree is too deep");
    Node n = node_get(p, pgno);
    int leaf = n_leaf(&n);
    for (int i = 0; i < n_ncells(&n); i++) {
        CellInfo ci;
        cell_parse(p, &n, i, &ci);
        if (ci.ovfl)
            overflow_free(p, ci.ovfl, ci.npayload - ci.nlocal);
        if (!leaf)
            drop_page(p, ci.child, depth + 1);
        n = node_get(p, pgno);
    }
    if (!leaf)
        drop_page(p, n_right(&n), depth + 1);
    page_free(p, pgno);
}

/* Free every page of the tree, the root too. */
void btree_drop(Pager *p, u32 root)
{
    drop_page(p, root, 0);
}

/* ------------------------------------------------------------ the freelist (02.05) */

/* Pages no tree uses any more are kept on the freelist, in the file, and
 * handed out again before the file grows. The list is a chain of "trunk"
 * pages (header offset 32: the first trunk; offset 36: how many pages are
 * free in all). A trunk page holds: 4 bytes next trunk, 4 bytes count,
 * then that many 4-byte numbers of free "leaf" pages. */
// @end

/* Take a page off the freelist and return its number. The list must not be
 * empty (the caller checked the count at offset 36 of page 1). A trunk with
 * leaf pages gives up its last leaf; an exhausted trunk gives up itself and
 * the next trunk becomes the first. */
static u32 freelist_pop(Pager *p)
{
    // @build 02.05 take a page off the freelist
    u8 *h = pager_write(p, 1);
    u32 trunk = get4(h + 32);
    if (trunk == 0 || trunk > p->npages)
        fatal("database is corrupt: bad freelist trunk %u", trunk);
    u8 *t = pager_write(p, trunk);
    u32 nleaf = get4(t + 4);
    u32 pgno;
    if (nleaf > 0) {
        pgno = get4(t + 8 + 4 * (nleaf - 1));
        put4(t + 4, nleaf - 1);
    } else {
        pgno = trunk;
        put4(h + 32, get4(t));
    }
    put4(h + 36, get4(h + 36) - 1);
    return pgno;
    // @end
}

/* Put page pgno on the freelist. It is added to the first trunk's leaf list
 * if that has room; otherwise it becomes the new first trunk. A trunk has
 * usable / 4 words, two of them its header, but sqlite3 fills at most
 * usable / 4 - 8 leaf slots: the last six stay unused, for the sake of old
 * versions. */
void page_free(Pager *p, u32 pgno)
{
    // @build 02.05 put a page on the freelist
    u8 *h = pager_write(p, 1);
    u32 trunk = get4(h + 32);
    if (trunk) {
        u8 *t = pager_write(p, trunk);
        u32 nleaf = get4(t + 4);
        if (nleaf < p->usable / 4 - 8) {
            put4(t + 8 + 4 * nleaf, pgno);
            put4(t + 4, nleaf + 1);
            put4(h + 36, get4(h + 36) + 1);
            return;
        }
    }
    u8 *d = pager_write(p, pgno);
    memset(d, 0, p->page_size);
    put4(d, trunk);
    put4(d + 4, 0);
    put4(h + 32, pgno);
    put4(h + 36, get4(h + 36) + 1);
    // @end
}

// @from 02.02
// @from 02.05
/* A page for a tree: off the freelist if any page is free, else a new one
 * at the end of the file. Zeroed and dirty. */
// @else
// /* A page for a tree: a new one at the end of the file. Zeroed and dirty. */
// @end
u32 page_alloc(Pager *p)
{
    u32 pgno;
    // @from 02.05
    if (get4(pager_get(p, 1) + 36) > 0) {
        pgno = freelist_pop(p);
    } else {
        pgno = ++p->npages;
    }
    // @else
    // pgno = ++p->npages;
    // @end
    memset(pager_write(p, pgno), 0, p->page_size);
    return pgno;
}
// @end
