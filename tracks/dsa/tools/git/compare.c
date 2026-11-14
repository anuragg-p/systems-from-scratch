/*
 * compare.c - two commits compared: what changed between their trees, as
 * patches, and the best common ancestor of the two.
 *
 * diff walks the two trees side by side, entries in git's order, like a
 * merge of two sorted lists. Where both have an entry of the same name,
 * mode and object name, the two are the same all the way down, and the
 * walk goes past without opening it: a subdirectory nobody touched costs
 * one comparison of 20 bytes, however much is in it. Where the names
 * differ, it opens both and walks on inside. A file that changed is
 * compared line by line by module 06's diff (lib/diff.h, Myers), and
 * printed as git prints it: "diff --git", the blobs' names, the hunks.
 * --algo=all is the comparison one would write first: open every tree and
 * read every file of both commits, and compare them byte by byte.
 *
 * merge-base finds the newest commits both histories hold, from which
 * neither has a newer one in common (the "best" common ancestors). It walks
 * back from the two commits at once, newest first through the heap of
 * 02.04, marking each commit with which of the two reaches it; a commit
 * both reach is common, and everything behind it is common too and no
 * better, so it is marked stale and the walk stops once the queue holds
 * nothing else. --algo=rewalk asks the question the obvious way: for each
 * ancestor of the second commit, newest first, walk the whole history of
 * the first again to see whether it is in it.
 *
 * DS_STATS=1 prints "stats: diff: trees read T, blobs read B, entries
 * compared E, subtrees skipped S, blobs skipped K, bytes compared Y, files
 * changed F" and "stats: merge-base: commits visited V, walks W".
 */
#include <stdlib.h>
#include <string.h>

#include "git.h"
#include "diff.h"

static struct {
    long trees, blobs, compared, skipped_trees, skipped_blobs, bytes, files;
} st;

static struct {
    long visited, walks;
} mb;

static void print_stats(void)
{
    ds_stats_print("diff", "trees read %ld, blobs read %ld, entries compared %ld, subtrees skipped %ld, "
                   "blobs skipped %ld, bytes compared %ld, files changed %ld", st.trees, st.blobs, st.compared,
                   st.skipped_trees, st.skipped_blobs, st.bytes, st.files);
}

static void print_mb_stats(void)
{
    ds_stats_print("merge-base", "commits visited %ld, walks %ld", mb.visited, mb.walks);
}

/* One file that differs: its path, and its mode and blob in each commit
 * (mode 0: not in that one). */
typedef struct {
    char *path;
    size_t len;
    uint32_t amode, bmode;
    unsigned char aoid[20], boid[20];
} Change;

static char *join(const char *prefix, size_t plen, const char *name, size_t len)
{
    char *p = xmalloc(plen + len + 1);
    memcpy(p, prefix, plen);
    memcpy(p + plen, name, len);
    p[plen + len] = '\0';
    return p;
}

/* A file in a, in b, or in both: one change; two (gone, then new) when it
 * changed from one kind to another (a file to a symbolic link). */
static void add_change(Array *changes, const char *path, size_t len, uint32_t amode, const unsigned char *aoid,
                       uint32_t bmode, const unsigned char *boid)
{
    if (amode && bmode && (amode & 0170000) != (bmode & 0170000)) {
        add_change(changes, path, len, amode, aoid, 0, NULL);
        add_change(changes, path, len, 0, NULL, bmode, boid);
        return;
    }
    Change *c = array_push(changes);
    c->path = xstrndup(path, len);
    c->len = len;
    c->amode = amode;
    c->bmode = bmode;
    if (aoid)
        memcpy(c->aoid, aoid, 20);
    if (boid)
        memcpy(c->boid, boid, 20);
    st.files++;
}

static void read_tree(const unsigned char *name, Object *o, Array *entries)
{
    if (name == NULL) {
        array_init(entries, sizeof(TreeEntry));
        o->buf.data = NULL;
        o->buf.len = 0;
        return;
    }
    object_read(name, o);
    tree_entries(name, o, entries);
    st.trees++;
}

/* The changes from tree a to tree b (either may be NULL: no tree, so
 * every file of the other is new, or gone), for paths starting prefix. */
static void walk_skip(const unsigned char *a, const unsigned char *b, const char *prefix, size_t plen, Array *changes)
{
    // @build 10.04 two trees side by side in git's order: what is the same is passed over unopened
    Object oa, ob;
    Array ea, eb;
    read_tree(a, &oa, &ea);
    read_tree(b, &ob, &eb);
    size_t i = 0, j = 0;
    while (i < ea.len || j < eb.len) {
        TreeEntry *x = i < ea.len ? array_at(&ea, i) : NULL;
        TreeEntry *y = j < eb.len ? array_at(&eb, j) : NULL;
        int c = x == NULL ? 1 : y == NULL ? -1 :
                tree_cmp(x->name, x->len, x->mode == MODE_TREE, y->name, y->len, y->mode == MODE_TREE);
        TreeEntry *e = c <= 0 ? x : y;
        char *path = join(prefix, plen, e->name, e->len);
        size_t len = plen + e->len;
        if (c == 0) {
            st.compared++;
            if (x->mode == y->mode && memcmp(x->oid, y->oid, 20) == 0) {
                if (x->mode == MODE_TREE)
                    st.skipped_trees++;
                else
                    st.skipped_blobs++;
                if (git_tracing())
                    trace("diff: %s%s: %s on both sides: the same, passed over", path,
                          x->mode == MODE_TREE ? "/" : "", short_hex(x->oid));
            } else if (x->mode == MODE_TREE) {
                if (git_tracing())
                    trace("diff: %s/: %s and %s: different, opened", path, short_hex(x->oid), short_hex(y->oid));
                char *sub = join(path, len, "/", 1);
                walk_skip(x->oid, y->oid, sub, len + 1, changes);
                free(sub);
            } else {
                if (git_tracing())
                    trace("diff: %s: %s and %s: changed", path, short_hex(x->oid), short_hex(y->oid));
                add_change(changes, path, len, x->mode, x->oid, y->mode, y->oid);
            }
            i++;
            j++;
        } else {
            if (git_tracing())
                trace("diff: %s%s: only in the %s", path, e->mode == MODE_TREE ? "/" : "", c < 0 ? "first" : "second");
            if (e->mode == MODE_TREE) {
                char *sub = join(path, len, "/", 1);
                walk_skip(c < 0 ? e->oid : NULL, c < 0 ? NULL : e->oid, sub, len + 1, changes);
                free(sub);
            } else if (c < 0) {
                add_change(changes, path, len, e->mode, e->oid, 0, NULL);
            } else {
                add_change(changes, path, len, 0, NULL, e->mode, e->oid);
            }
            if (c < 0)
                i++;
            else
                j++;
        }
        free(path);
    }
    array_free(&ea);
    array_free(&eb);
    if (a)
        object_free(&oa);
    if (b)
        object_free(&ob);
    // @end
}

/* A file of a commit, read: --algo=all. */
typedef struct {
    char *path;
    size_t len;
    uint32_t mode;
    unsigned char oid[20];
    Object blob;
} File;

static void flatten(const unsigned char *tree, const char *prefix, size_t plen, Array *files)
{
    // @build 10.04 the slow way: open every tree and read every file, all the way down
    Object o;
    Array entries;
    read_tree(tree, &o, &entries);
    for (size_t i = 0; i < entries.len; i++) {
        TreeEntry *e = array_at(&entries, i);
        char *path = join(prefix, plen, e->name, e->len);
        if (e->mode == MODE_TREE) {
            char *sub = join(path, plen + e->len, "/", 1);
            flatten(e->oid, sub, plen + e->len + 1, files);
            free(sub);
            free(path);
            continue;
        }
        File *f = array_push(files);
        f->path = path;
        f->len = plen + e->len;
        f->mode = e->mode;
        memcpy(f->oid, e->oid, 20);
        memset(&f->blob, 0, sizeof f->blob);
        if (e->mode != 0160000) {            /* a submodule's commit is not in this repository */
            object_read(e->oid, &f->blob);
            st.blobs++;
        }
    }
    array_free(&entries);
    object_free(&o);
    // @end
}

static void walk_all(const unsigned char *a, const unsigned char *b, Array *changes)
{
    // @build 10.04 every file of one commit against the file of the same path in the other, byte by byte
    Array fa, fb;
    array_init(&fa, sizeof(File));
    array_init(&fb, sizeof(File));
    flatten(a, "", 0, &fa);
    flatten(b, "", 0, &fb);
    size_t i = 0, j = 0;
    while (i < fa.len || j < fb.len) {
        File *x = i < fa.len ? array_at(&fa, i) : NULL;
        File *y = j < fb.len ? array_at(&fb, j) : NULL;
        int c = x == NULL ? 1 : y == NULL ? -1 : tree_cmp(x->path, x->len, 0, y->path, y->len, 0);
        if (c == 0) {
            st.compared++;
            size_t n = x->blob.size < y->blob.size ? x->blob.size : y->blob.size;
            st.bytes += (long)n;
            int same = x->mode == y->mode && x->blob.size == y->blob.size &&
                       (n == 0 || memcmp(x->blob.data, y->blob.data, n) == 0) &&
                       (x->mode != 0160000 || memcmp(x->oid, y->oid, 20) == 0);
            if (!same)
                add_change(changes, x->path, x->len, x->mode, x->oid, y->mode, y->oid);
            i++;
            j++;
        } else if (c < 0) {
            add_change(changes, x->path, x->len, x->mode, x->oid, 0, NULL);
            i++;
        } else {
            add_change(changes, y->path, y->len, 0, NULL, y->mode, y->oid);
            j++;
        }
    }
    Array *both[2] = {&fa, &fb};
    for (int k = 0; k < 2; k++) {
        for (size_t m = 0; m < both[k]->len; m++) {
            File *f = array_at(both[k], m);
            free(f->path);
            object_free(&f->blob);
        }
        array_free(both[k]);
    }
    // @end
}

/* ------------------------------------------------------------ printing a change as git does */

/* "a/path" in a header line, quoted as git quotes it. */
static void side(const char *prefix, const Change *c)
{
    put_path(stdout, prefix, c->path, c->len);
}

/* A blob's bytes, or a submodule's commit as git shows it. */
static const char *content(uint32_t mode, const unsigned char *oid, Object *o, size_t *n, char *sub)
{
    if (mode == 0) {
        *n = 0;
        return "";
    }
    if (mode == 0160000) {
        char hex[41];
        sha1_hex(oid, hex);
        *n = (size_t)sprintf(sub, "Subproject commit %s\n", hex);
        return sub;
    }
    object_read(oid, o);
    st.blobs++;
    *n = o->size;
    return (const char *)o->data;
}

static int binary(const char *p, size_t n)
{
    return memchr(p, '\0', n < 8000 ? n : 8000) != NULL;
}

static void show_change(const Change *c, long context)
{
    // @build 10.04 one file's patch: git's header lines, then module 06's diff of the two blobs
    char a_abbr[41] = "0000000", b_abbr[41] = "0000000", asub[80], bsub[80];
    fputs("diff --git ", stdout);
    side("a/", c);
    putchar(' ');
    side("b/", c);
    putchar('\n');
    if (c->amode == 0)
        printf("new file mode %06o\n", c->bmode);
    else if (c->bmode == 0)
        printf("deleted file mode %06o\n", c->amode);
    else if (c->amode != c->bmode)
        printf("old mode %06o\nnew mode %06o\n", c->amode, c->bmode);
    if (c->amode && c->bmode && memcmp(c->aoid, c->boid, 20) == 0)
        return;                              /* the mode alone changed */
    if (c->amode)
        abbrev(c->aoid, a_abbr);
    if (c->bmode)
        abbrev(c->boid, b_abbr);
    printf("index %s..%s", a_abbr, b_abbr);
    if (c->amode == c->bmode)
        printf(" %06o", c->amode);
    putchar('\n');
    Object oa = {0}, ob = {0};
    size_t na, nb;
    const char *da = content(c->amode, c->aoid, &oa, &na, asub);
    const char *db = content(c->bmode, c->boid, &ob, &nb, bsub);
    const char *tab = memchr(c->path, ' ', c->len) ? "\t" : "";
    if (binary(da, na) || binary(db, nb)) {
        fputs("Binary files ", stdout);
        if (c->amode)
            side("a/", c);
        else
            fputs("/dev/null", stdout);
        fputs(" and ", stdout);
        if (c->bmode)
            side("b/", c);
        else
            fputs("/dev/null", stdout);
        fputs(" differ\n", stdout);
    } else {
        DiffText ta, tb;
        DiffScript s;
        diff_text(&ta, da, na);
        diff_text(&tb, db, nb);
        diff_myers(&s, &ta, &tb);
        if (s.ndel + s.nins > 0) {
            fputs("--- ", stdout);
            if (c->amode) {
                side("a/", c);
                fputs(tab, stdout);
            } else {
                fputs("/dev/null", stdout);
            }
            fputs("\n+++ ", stdout);
            if (c->bmode) {
                side("b/", c);
                fputs(tab, stdout);
            } else {
                fputs("/dev/null", stdout);
            }
            putchar('\n');
            diff_unified(stdout, &ta, &tb, &s, (size_t)context);
        }
        diff_script_free(&s);
        diff_text_free(&ta);
        diff_text_free(&tb);
    }
    if (c->amode && c->amode != 0160000)
        object_free(&oa);
    if (c->bmode && c->bmode != 0160000)
        object_free(&ob);
    // @end
}

void diff_trees(const unsigned char a[20], const unsigned char b[20], int algo, long context)
{
    Array changes;
    ds_stats_at_exit(print_stats);
    array_init(&changes, sizeof(Change));
    if (algo == WALK_ALL)
        walk_all(a, b, &changes);
    else
        walk_skip(a, b, "", 0, &changes);
    for (size_t i = 0; i < changes.len; i++) {
        Change *c = array_at(&changes, i);
        show_change(c, context);
        free(c->path);
    }
    array_free(&changes);
}

/* ------------------------------------------------------------ merge-base */

enum { P1 = 1, P2 = 2, STALE = 4, RESULT = 8, QUEUED = 16 };

static long walk_no;

/* Is target from, or one of its ancestors? A walk of from's whole history
 * (marked with a new number, so each commit is visited once in it). */
static int reaches(Commit *from, Commit *target)
{
    Array stack;
    array_init(&stack, sizeof(Commit *));
    walk_no++;
    mb.walks++;
    from->walk = walk_no;
    *(Commit **)array_push(&stack) = from;
    int found = 0;
    while (stack.len > 0 && !found) {
        Commit *c = *(Commit **)array_pop(&stack);
        mb.visited++;
        if (c == target) {
            found = 1;
            break;
        }
        for (size_t i = 0; i < c->parents.len; i++) {
            Commit *p = commit_get(array_at(&c->parents, i));
            if (p->walk != walk_no) {
                p->walk = walk_no;
                *(Commit **)array_push(&stack) = p;
            }
        }
    }
    array_free(&stack);
    return found;
}

/* Drop from results every commit that another of them reaches: an
 * ancestor of a common ancestor is common, but not the best. */
static void remove_redundant(Array *results)
{
    Array keep;
    array_init(&keep, sizeof(Commit *));
    for (size_t i = 0; i < results->len; i++) {
        Commit *r = *(Commit **)array_at(results, i);
        int redundant = 0;
        for (size_t j = 0; j < results->len && !redundant; j++)
            if (j != i)
                redundant = reaches(*(Commit **)array_at(results, j), r);
        if (!redundant)
            *(Commit **)array_push(&keep) = r;
    }
    array_free(results);
    *results = keep;
}

/* Does the queue hold any commit that is not stale? */
static int live(const Heap *q)
{
    for (size_t i = 0; i < q->items.len; i++)
        if (!(((Commit **)q->items.data)[i]->flags & STALE))
            return 1;
    return 0;
}

static void paint(Commit *a, Commit *b, Array *results)
{
    // @build 10.04 merge-base: walk back from both at once, newest first, marking who reaches each commit
    Heap q;
    heap_init(&q, commit_newer, NULL);
    a->flags |= P1;
    b->flags |= P2;
    heap_push(&q, a);
    if (b != a)
        heap_push(&q, b);
    while (live(&q)) {
        Commit *c = heap_pop(&q);
        mb.visited++;
        int f = c->flags & (P1 | P2 | STALE);
        if (f == (P1 | P2)) {                /* both reach it: common, and all behind it stale */
            if (!(c->flags & RESULT)) {
                c->flags |= RESULT;
                *(Commit **)array_push(results) = c;
            }
            f |= STALE;
        }
        if (git_tracing())
            trace("merge-base: pop %s %lld, reached by %s%s%s%s", short_hex(c->oid), c->time,
                  (f & P1) ? "1" : "", (f & (P1 | P2)) == (P1 | P2) ? " and " : "", (f & P2) ? "2" : "",
                  (f & STALE) ? ", stale" : "");
        for (size_t i = 0; i < c->parents.len; i++) {
            Commit *p = commit_get(array_at(&c->parents, i));
            if ((p->flags & f) == f)
                continue;
            p->flags |= f;
            heap_push(&q, p);
        }
    }
    heap_free(&q);
    remove_redundant(results);
    // @end
}

static void rewalk(Commit *a, Commit *b, Array *results)
{
    // @build 10.04 merge-base, the obvious way: is each of b's ancestors, newest first, in a's whole history?
    Heap q;
    heap_init(&q, commit_newer, NULL);
    b->flags |= QUEUED;
    heap_push(&q, b);
    while (heap_len(&q) > 0) {
        Commit *x = heap_pop(&q);
        mb.visited++;
        if (reaches(a, x)) {                 /* common: a candidate, and nothing behind it is better */
            if (git_tracing())
                trace("merge-base: %s %lld is in the first's history: a candidate", short_hex(x->oid), x->time);
            *(Commit **)array_push(results) = x;
            continue;
        }
        if (git_tracing())
            trace("merge-base: %s %lld is not in the first's history", short_hex(x->oid), x->time);
        for (size_t i = 0; i < x->parents.len; i++) {
            Commit *p = commit_get(array_at(&x->parents, i));
            if (!(p->flags & QUEUED)) {
                p->flags |= QUEUED;
                heap_push(&q, p);
            }
        }
    }
    heap_free(&q);
    remove_redundant(results);
    // @end
}

size_t merge_base(const unsigned char a[20], const unsigned char b[20], int algo, int all)
{
    Array results;
    ds_stats_at_exit(print_mb_stats);
    array_init(&results, sizeof(Commit *));
    Commit *ca = commit_get(a), *cb = commit_get(b);
    if (algo == BASE_REWALK)
        rewalk(ca, cb, &results);
    else
        paint(ca, cb, &results);
    for (size_t i = 0; i < results.len && (all || i == 0); i++) {
        char hex[41];
        sha1_hex((*(Commit **)array_at(&results, i))->oid, hex);
        printf("%s\n", hex);
    }
    size_t n = results.len;
    array_free(&results);
    return n;
}
