/*
 * tree.c - a directory as an object.
 *
 * A tree object lists one directory: for each file or subdirectory, a
 * mode, a name, and the 20-byte name of the object holding it (a blob for
 * a file, another tree for a subdirectory), as "100644 hello.txt", a NUL,
 * and the 20 bytes. The entries are in git's own order, which is the order
 * of the bytes of the names, except that a directory's name counts as if it
 * ended in '/': "b c" (a space is 0x20) comes before the directory "b"
 * (as "b/", 0x2f), though plain byte order puts "b" first.
 *
 * A tree's name is the SHA-1 of all that, so it stands for the whole of
 * the directory below it: two trees with the same name hold the same files
 * with the same bytes all the way down. A change to one file changes its
 * blob's name, so the tree that lists it, so the tree above that, up to the
 * top: every tree on the path is renamed, and every other tree is the same
 * object as before.
 *
 * write_tree builds the trees of the index, bottom up. The index keeps the
 * name of each directory's tree from the last time (the cached trees), and
 * forgets it when anything under the directory changes; so the trees built
 * again are the changed ones, and the rest are looked up.
 *
 * DS_STATS=1 prints "stats: write-tree: trees built B, from the cache C".
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "git.h"

static struct {
    long built, cached;
} st;

static void print_stats(void)
{
    ds_stats_print("write-tree", "trees built %ld, from the cache %ld", st.built, st.cached);
}

int tree_cmp(const char *a, size_t alen, int adir, const char *b, size_t blen, int bdir)
{
    // @build 10.02 git's order: by the bytes, a directory's name as if it ended in '/'
    size_t n = alen < blen ? alen : blen;
    int c = memcmp(a, b, n);
    if (c != 0)
        return c;
    int ca = alen > n ? (unsigned char)a[n] : adir ? '/' : 0;
    int cb = blen > n ? (unsigned char)b[n] : bdir ? '/' : 0;
    return ca - cb;
    // @end
}

const char *mode_type(uint32_t mode)
{
    return mode == MODE_TREE ? "tree" : mode == 0160000 ? "commit" : "blob";
}

void tree_entries(const unsigned char name[20], const Object *o, Array *out)
{
    // @build 10.02 a tree's entries, each checked: a mode git writes, a name, 20 bytes, in git's order
    char hex[41];
    sha1_hex(name, hex);
    if (o->type != OBJ_TREE)
        die("%s is a %s, not a tree", hex, type_name(o->type));
    array_init(out, sizeof(TreeEntry));
    const char *p = (const char *)o->data, *end = p + o->size;
    while (p < end) {
        TreeEntry e;
        const char *sp = memchr(p, ' ', (size_t)(end - p) < 8 ? (size_t)(end - p) : 8);
        if (sp == NULL || sp == p || *p == '0')
            die("tree %s is damaged: an entry without a mode git writes", hex);
        e.mode = 0;
        for (const char *q = p; q < sp; q++) {
            if (*q < '0' || *q > '7')
                die("tree %s is damaged: a mode that is not octal", hex);
            e.mode = e.mode * 8 + (uint32_t)(*q - '0');
        }
        e.name = sp + 1;
        const char *nul = memchr(e.name, '\0', (size_t)(end - e.name));
        if (nul == NULL || (size_t)(end - nul) < 21)
            die("tree %s is damaged: it ends in the middle of an entry", hex);
        e.len = (size_t)(nul - e.name);
        e.oid = (const unsigned char *)nul + 1;
        if (e.len == 0 || memchr(e.name, '/', e.len) != NULL || (e.len == 1 && e.name[0] == '.') ||
            (e.len == 2 && e.name[0] == '.' && e.name[1] == '.'))
            die("tree %s is damaged: an entry named '%.*s'", hex, (int)e.len, e.name);
        if (e.mode != MODE_TREE && e.mode != 0100644 && e.mode != 0100755 && e.mode != 0120000 &&
            e.mode != 0160000)
            die("tree %s: entry '%.*s' has mode %o, which git does not write", hex, (int)e.len, e.name, e.mode);
        if (out->len > 0) {
            TreeEntry *prev = array_at(out, out->len - 1);
            if (tree_cmp(prev->name, prev->len, prev->mode == MODE_TREE, e.name, e.len, e.mode == MODE_TREE) >= 0)
                die("tree %s is damaged: '%.*s' comes after '%.*s', out of git's order", hex,
                    (int)e.len, e.name, (int)prev->len, prev->name);
        }
        *(TreeEntry *)array_push(out) = e;
        p = (const char *)e.oid + 20;
    }
    // @end
}

void tree_of(const char *arg, unsigned char tree[20])
{
    Object o;
    resolve(arg, tree);
    object_read(tree, &o);
    // @from 10.03
    if (o.type == OBJ_COMMIT) {
        Commit *c = commit_read(tree);
        memcpy(tree, c->tree, 20);
        commit_free(c);
        object_free(&o);
        object_read(tree, &o);
    }
    // @end
    if (o.type != OBJ_TREE)
        die("%s is a %s, not a tree", arg, type_name(o.type));
    object_free(&o);
}

/* ------------------------------------------------------------ printing paths */

int path_needs_quotes(const char *path, size_t len)
{
    for (size_t i = 0; i < len; i++) {
        unsigned char c = (unsigned char)path[i];
        if (c < 0x20 || c == '"' || c == '\\' || c >= 0x7f)
            return 1;
    }
    return 0;
}

void put_path(FILE *f, const char *prefix, const char *path, size_t len)
{
    if (!path_needs_quotes(path, len)) {
        fprintf(f, "%s%.*s", prefix, (int)len, path);
        return;
    }
    fprintf(f, "\"%s", prefix);
    for (size_t i = 0; i < len; i++) {
        unsigned char c = (unsigned char)path[i];
        const char *esc = c == '\a' ? "\\a" : c == '\b' ? "\\b" : c == '\t' ? "\\t" : c == '\n' ? "\\n" :
                          c == '\v' ? "\\v" : c == '\f' ? "\\f" : c == '\r' ? "\\r" : c == '"' ? "\\\"" :
                          c == '\\' ? "\\\\" : NULL;
        if (esc != NULL)
            fputs(esc, f);
        else if (c < 0x20 || c >= 0x7f)
            fprintf(f, "\\%03o", c);
        else
            fputc(c, f);
    }
    fputc('"', f);
}

/* ------------------------------------------------------------ the index as trees */

/* The cached tree of the subdirectory name of ct, made (empty, not valid)
 * if there is none. */
static CacheTree *cache_sub(CacheTree *ct, const char *name, size_t len)
{
    for (size_t i = 0; i < ct->subs.len; i++) {
        CacheTree *s = *(CacheTree **)array_at(&ct->subs, i);
        if (s->len == len && memcmp(s->name, name, len) == 0)
            return s;
    }
    CacheTree *s = xmalloc(sizeof *s);
    s->name = xstrndup(name, len);
    s->len = len;
    s->count = -1;
    array_init(&s->subs, sizeof(CacheTree *));
    *(CacheTree **)array_push(&ct->subs) = s;
    return s;
}

static void cache_free(CacheTree *ct)
{
    for (size_t i = 0; i < ct->subs.len; i++)
        cache_free(*(CacheTree **)array_at(&ct->subs, i));
    array_free(&ct->subs);
    free(ct->name);
    free(ct);
}

static void put_bytes(Array *a, const void *p, size_t n)
{
    for (size_t i = 0; i < n; i++)
        *(char *)array_push(a) = ((const char *)p)[i];
}

/* For the trace: "a/b/", or "/" for the top. */
static const char *dir_label(Index *ix, size_t lo, size_t plen)
{
    static char buf[256];
    if (plen == 0)
        return "/";
    snprintf(buf, sizeof buf, "%.*s", (int)plen, ((IndexEntry *)array_at(&ix->entries, lo))->path);
    return buf;
}

/* The tree of the index entries [lo, hi), which are everything under the
 * directory whose path (with its '/') is the first plen bytes of each;
 * ct is that directory's cached tree. */
static void build(Index *ix, size_t lo, size_t hi, size_t plen, CacheTree *ct, int use_cache, unsigned char out[20])
{
    // @build 10.02 one directory's tree: its subdirectories' trees first, then its own
    if (use_cache && ct->count >= 0 && (size_t)ct->count == hi - lo && object_exists(ct->oid)) {
        memcpy(out, ct->oid, 20);
        st.cached++;
        if (git_tracing())
            trace("tree: %s (%zu file%s under it): %s, from the cache", dir_label(ix, lo, plen), hi - lo,
                  hi - lo == 1 ? "" : "s", short_hex(out));
        return;
    }
    Array body, subs;
    array_init(&body, 1);
    array_init(&subs, sizeof(CacheTree *));
    const char *prev = NULL;
    size_t prev_len = 0;
    int prev_dir = 0, nentries = 0;
    for (size_t i = lo; i < hi;) {
        IndexEntry *e = array_at(&ix->entries, i);
        const char *name = e->path + plen;
        size_t rest = e->len - plen;
        const char *slash = memchr(name, '/', rest);
        size_t len = slash ? (size_t)(slash - name) : rest;
        unsigned char sub_oid[20];
        uint32_t mode = e->mode;
        const unsigned char *oid = e->oid;
        size_t next = i + 1;
        if (slash != NULL) {                     /* a subdirectory: all of it, built first */
            while (next < hi) {
                IndexEntry *f = array_at(&ix->entries, next);
                if (f->len <= plen + len || memcmp(f->path, e->path, plen + len + 1) != 0)
                    break;
                next++;
            }
            CacheTree *sub = cache_sub(ct, name, len);
            build(ix, i, next, plen + len + 1, sub, use_cache, sub_oid);
            *(CacheTree **)array_push(&subs) = sub;
            mode = MODE_TREE;
            oid = sub_oid;
        }
        /* the index's order is git's tree order; this checks it */
        if (prev != NULL && tree_cmp(prev, prev_len, prev_dir, name, len, slash != NULL) >= 0)
            die("the index is not in git's order: '%.*s' after '%.*s'", (int)len, name, (int)prev_len, prev);
        prev = name;
        prev_len = len;
        prev_dir = slash != NULL;
        char head[16];
        put_bytes(&body, head, (size_t)snprintf(head, sizeof head, "%o ", mode));
        put_bytes(&body, name, len);
        put_bytes(&body, "", 1);
        put_bytes(&body, oid, 20);
        nentries++;
        i = next;
    }
    object_write(OBJ_TREE, body.data ? body.data : "", body.len, out);
    st.built++;
    if (git_tracing())
        trace("tree: %s (%d entr%s, %zu file%s under it): %s, built", dir_label(ix, lo, plen), nentries,
              nentries == 1 ? "y" : "ies", hi - lo, hi - lo == 1 ? "" : "s", short_hex(out));
    /* the cache: this directory's tree, and only the subdirectories it has now */
    for (size_t k = 0; k < ct->subs.len; k++) {
        CacheTree *old = *(CacheTree **)array_at(&ct->subs, k);
        int kept = 0;
        for (size_t j = 0; j < subs.len && !kept; j++)
            kept = *(CacheTree **)array_at(&subs, j) == old;
        if (!kept)
            cache_free(old);
    }
    array_free(&ct->subs);
    ct->subs = subs;
    ct->count = (long)(hi - lo);
    memcpy(ct->oid, out, 20);
    array_free(&body);
    // @end
}

void write_tree(Index *ix, int use_cache, unsigned char tree[20])
{
    ds_stats_at_exit(print_stats);
    if (ix->cache == NULL) {
        ix->cache = xmalloc(sizeof *ix->cache);
        ix->cache->name = xstrndup("", 0);
        ix->cache->len = 0;
        ix->cache->count = -1;
        array_init(&ix->cache->subs, sizeof(CacheTree *));
    }
    build(ix, 0, ix->entries.len, 0, ix->cache, use_cache, tree);
}
