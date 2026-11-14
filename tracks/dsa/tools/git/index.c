/*
 * index.c - the index (.git/index): the list of files the next commit
 * will hold, sorted by path, each with the name of its blob.
 *
 * add hashes a file, stores its blob, and puts (path, mode, blob name, and
 * what stat() says of the file) in the list; commit makes trees of the
 * list. The file is version 2 of git's index format (gitformat-index): a
 * header ("DIRC", the version, the number of entries), the entries in
 * order of their paths' bytes, each padded with NULs to a multiple of 8
 * bytes, then extensions, then the SHA-1 of everything before it.
 *
 * The one extension written is TREE, the cached trees: for each directory,
 * how many entries are under it and the name of the tree they made the
 * last time, or -1 once an entry under it has changed. A change to a/b/c
 * makes the top, a and a/b -1, and nothing else; write_tree builds only
 * those again.
 *
 * DS_STATS=1 prints "stats: index: entries read R, entries written W,
 * files hashed H".
 */
#include <dirent.h>
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <unistd.h>

#include "git.h"

static struct {
    long read, written, hashed;
} st;

static void print_stats(void)
{
    ds_stats_print("index", "entries read %ld, entries written %ld, files hashed %ld", st.read, st.written, st.hashed);
}

static uint32_t be32(const unsigned char *p)
{
    return (uint32_t)p[0] << 24 | (uint32_t)p[1] << 16 | (uint32_t)p[2] << 8 | p[3];
}

static void put32(Array *a, uint32_t v)
{
    for (int s = 24; s >= 0; s -= 8)
        *(unsigned char *)array_push(a) = (unsigned char)(v >> s);
}

static void put_bytes(Array *a, const void *p, size_t n)
{
    for (size_t i = 0; i < n; i++)
        *(char *)array_push(a) = ((const char *)p)[i];
}

/* A path git would keep: not empty, no empty, "." or ".." part, no
 * ".git" part, no '/' at either end. */
static int path_ok(const char *p, size_t n)
{
    if (n == 0 || p[0] == '/' || p[n - 1] == '/')
        return 0;
    for (size_t i = 0; i < n;) {
        size_t j = i;
        while (j < n && p[j] != '/')
            j++;
        size_t k = j - i;
        if (k == 0 || (k == 1 && p[i] == '.') || (k == 2 && p[i] == '.' && p[i + 1] == '.') ||
            (k == 4 && strncasecmp(p + i, ".git", 4) == 0))
            return 0;
        i = j + 1;
    }
    return memchr(p, '\0', n) == NULL;
}

/* Two paths in the index's order: their bytes, a shorter one first when it
 * is the start of the other. */
static int path_cmp(const char *a, size_t alen, const char *b, size_t blen)
{
    int c = memcmp(a, b, alen < blen ? alen : blen);
    return c != 0 ? c : (alen > blen) - (alen < blen);
}

/* ------------------------------------------------------------ the cached trees */

static CacheTree *cache_new(const char *name, size_t len)
{
    CacheTree *ct = xmalloc(sizeof *ct);
    ct->name = xstrndup(name, len);
    ct->len = len;
    ct->count = -1;
    array_init(&ct->subs, sizeof(CacheTree *));
    return ct;
}

/* One entry of the TREE extension at *p (before end), and its
 * subdirectories after it: "name", NUL, "count subs", newline, and the
 * tree's name unless count is -1. NULL if it is not that. */
static CacheTree *cache_parse(const unsigned char **p, const unsigned char *end, int depth)
{
    const unsigned char *q = *p;
    const unsigned char *nul = memchr(q, '\0', (size_t)(end - q));
    if (nul == NULL || depth > 1000)
        return NULL;
    CacheTree *ct = cache_new((const char *)q, (size_t)(nul - q));
    q = nul + 1;
    long count = 0, subs = 0;
    int neg = 0, digits = 0;
    if (q < end && *q == '-') {
        neg = 1;
        q++;
    }
    for (; q < end && *q >= '0' && *q <= '9' && digits < 10; q++, digits++)
        count = count * 10 + (*q - '0');
    if (digits == 0 || q >= end || *q++ != ' ')
        return NULL;
    for (digits = 0; q < end && *q >= '0' && *q <= '9' && digits < 10; q++, digits++)
        subs = subs * 10 + (*q - '0');
    if (digits == 0 || q >= end || *q++ != '\n')
        return NULL;
    ct->count = neg ? -1 : count;
    if (!neg) {
        if (end - q < 20)
            return NULL;
        memcpy(ct->oid, q, 20);
        q += 20;
    }
    for (long i = 0; i < subs; i++) {
        CacheTree *s = cache_parse(&q, end, depth + 1);
        if (s == NULL)
            return NULL;
        *(CacheTree **)array_push(&ct->subs) = s;
    }
    *p = q;
    return ct;
}

static void cache_put(Array *out, const CacheTree *ct)
{
    char line[48];
    put_bytes(out, ct->name, ct->len);
    put_bytes(out, "", 1);
    put_bytes(out, line, (size_t)snprintf(line, sizeof line, "%ld %zu\n", ct->count < 0 ? -1 : ct->count, ct->subs.len));
    if (ct->count >= 0)
        put_bytes(out, ct->oid, 20);
    for (size_t i = 0; i < ct->subs.len; i++)
        cache_put(out, *(CacheTree **)array_at(&ct->subs, i));
}

/* Forget the trees of every directory above path: the top, a, a/b for
 * a/b/c. Their files have changed, so their trees must be built again. */
static void cache_invalidate(Index *ix, const char *path, size_t len)
{
    CacheTree *ct = ix->cache;
    size_t at = 0;
    while (ct != NULL) {
        if (ct->count >= 0 && git_tracing())
            trace("index: %s changed: the cached tree of %.*s%s is gone", path, (int)at, path, at ? "" : "/");
        ct->count = -1;
        const char *name = path + at;
        const char *slash = memchr(name, '/', len - at);
        if (slash == NULL)
            break;
        size_t n = (size_t)(slash - name);
        CacheTree *next = NULL;
        for (size_t i = 0; i < ct->subs.len && next == NULL; i++) {
            CacheTree *s = *(CacheTree **)array_at(&ct->subs, i);
            if (s->len == n && memcmp(s->name, name, n) == 0)
                next = s;
        }
        ct = next;
        at += n + 1;
    }
}

/* ------------------------------------------------------------ reading and writing */

void index_read(Index *ix)
{
    array_init(&ix->entries, sizeof(IndexEntry));
    ix->cache = NULL;
    ds_stats_at_exit(print_stats);
    size_t size;
    unsigned char *d = (unsigned char *)read_file(".git/index", &size);
    if (d == NULL)
        return;
    // @build 10.02 read the index: header, entries in order, the cached trees, the checksum
    if (size < 12 + 20)
        die("the index is damaged: it is only %zu bytes", size);
    if (memcmp(d, "DIRC", 4) != 0)
        die("the index is damaged: it does not start with DIRC");
    uint32_t version = be32(d + 4), count = be32(d + 8);
    if (version == 4)
        die("the index is version 4, which this git does not read (it reads 2 and 3)");
    if (version != 2 && version != 3)
        die("the index is version %u, which this git does not read (it reads 2 and 3)", version);
    unsigned char sum[20], zero[20] = {0};
    sha1(d, size - 20, sum);
    if (memcmp(sum, d + size - 20, 20) != 0 && memcmp(zero, d + size - 20, 20) != 0)
        die("the index is damaged: its checksum is not the SHA-1 of its bytes");
    size_t pos = 12, end = size - 20;
    for (uint32_t k = 0; k < count; k++) {
        if (end - pos < 62)
            die("the index is damaged: it ends in entry %u of %u", k + 1, count);
        const unsigned char *e = d + pos;
        unsigned flags = (unsigned)e[60] << 8 | e[61];
        size_t name_at = 62;
        if (flags & 0x4000) {                /* extended flags: version 3 */
            if (version < 3 || end - pos < 64)
                die("the index is damaged: an extended entry in a version %u index", version);
            name_at = 64;
        }
        if (flags & 0x3000)
            die("the index has unmerged entries (a merge stopped half way), which this git does not read");
        size_t len = flags & 0xfff;
        const unsigned char *name = e + name_at;
        const unsigned char *nul = memchr(name, '\0', end - pos - name_at);
        if (nul == NULL || (len < 0xfff && (size_t)(nul - name) != len))
            die("the index is damaged: entry %u's path", k + 1);
        len = (size_t)(nul - name);
        size_t step = (name_at + len + 8) & ~(size_t)7;
        if (step > end - pos)
            die("the index is damaged: it ends in entry %u of %u", k + 1, count);
        IndexEntry ie;
        uint32_t *f[10] = {&ie.ctime_s, &ie.ctime_ns, &ie.mtime_s, &ie.mtime_ns, &ie.dev, &ie.ino,
                           &ie.mode, &ie.uid, &ie.gid, &ie.size};
        for (int i = 0; i < 10; i++)
            *f[i] = be32(e + 4 * i);
        memcpy(ie.oid, e + 40, 20);
        if (!path_ok((const char *)name, len))
            die("the index is damaged: a path git would not keep, '%.*s'", (int)len, name);
        if (ie.mode != 0100644 && ie.mode != 0100755 && ie.mode != 0120000 && ie.mode != 0160000)
            die("the index is damaged: '%.*s' has mode %o", (int)len, name, ie.mode);
        if (ix->entries.len > 0) {
            IndexEntry *prev = array_at(&ix->entries, ix->entries.len - 1);
            if (path_cmp(prev->path, prev->len, (const char *)name, len) >= 0)
                die("the index is damaged: '%.*s' comes after '%s', out of order", (int)len, name, prev->path);
        }
        ie.path = xstrndup((const char *)name, len);
        ie.len = len;
        *(IndexEntry *)array_push(&ix->entries) = ie;
        st.read++;
        pos += step;
    }
    while (pos < end) {                      /* the extensions */
        if (end - pos < 8 || be32(d + pos + 4) > end - pos - 8)
            die("the index is damaged: an extension runs past its end");
        const unsigned char *sig = d + pos, *body = d + pos + 8;
        size_t n = be32(d + pos + 4);
        if (memcmp(sig, "TREE", 4) == 0) {
            const unsigned char *p = body;
            ix->cache = cache_parse(&p, body + n, 0);
            if (ix->cache == NULL || p != body + n)
                die("the index is damaged: its cached trees (TREE) cannot be read");
        } else if (!(sig[0] >= 'A' && sig[0] <= 'Z')) {
            die("the index has an extension '%.4s' that this git does not know, and may not ignore", sig);
        }                                    /* an optional one this git does not use: passed over */
        pos += 8 + n;
    }
    // @end
    free(d);
}

void index_write(Index *ix)
{
    // @build 10.02 write the index: header, entries padded to 8 bytes, the cached trees, the checksum
    Array out;
    array_init(&out, 1);
    put_bytes(&out, "DIRC", 4);
    put32(&out, 2);
    put32(&out, (uint32_t)ix->entries.len);
    for (size_t i = 0; i < ix->entries.len; i++) {
        IndexEntry *e = array_at(&ix->entries, i);
        size_t start = out.len;
        uint32_t f[10] = {e->ctime_s, e->ctime_ns, e->mtime_s, e->mtime_ns, e->dev, e->ino,
                          e->mode, e->uid, e->gid, e->size};
        for (int k = 0; k < 10; k++)
            put32(&out, f[k]);
        put_bytes(&out, e->oid, 20);
        unsigned flags = e->len < 0xfff ? (unsigned)e->len : 0xfff;
        put_bytes(&out, (unsigned char[]){(unsigned char)(flags >> 8), (unsigned char)flags}, 2);
        put_bytes(&out, e->path, e->len);
        size_t step = (62 + e->len + 8) & ~(size_t)7;
        while (out.len - start < step)
            put_bytes(&out, "", 1);
        st.written++;
    }
    if (ix->cache != NULL) {
        Array ext;
        array_init(&ext, 1);
        cache_put(&ext, ix->cache);
        put_bytes(&out, "TREE", 4);
        put32(&out, (uint32_t)ext.len);
        put_bytes(&out, ext.data, ext.len);
        array_free(&ext);
    }
    unsigned char sum[20];
    sha1(out.data, out.len, sum);
    put_bytes(&out, sum, 20);
    write_file_locked(".git/index", out.data, out.len);
    array_free(&out);
    // @end
}

/* ------------------------------------------------------------ add */

static int cmp_paths(const void *a, const void *b, void *ctx)
{
    return strcmp(a, b);
}

/* Every file under dir (a path from the top, or "" for the top): its path
 * pushed to out (char *). */
static void walk(const char *dir, Array *out)
{
    DIR *d = opendir(*dir ? dir : ".");
    if (d == NULL)
        die("%s: %s", *dir ? dir : ".", strerror(errno));
    struct dirent *de;
    while ((de = readdir(d)) != NULL) {
        const char *n = de->d_name;
        if (strcmp(n, ".") == 0 || strcmp(n, "..") == 0 || strcmp(n, ".git") == 0)
            continue;
        size_t len = strlen(dir) + strlen(n) + 2;
        char *path = xmalloc(len);
        snprintf(path, len, "%s%s%s", dir, *dir ? "/" : "", n);
        struct stat sb;
        if (lstat(path, &sb) != 0)
            die("%s: %s", path, strerror(errno));
        if (S_ISDIR(sb.st_mode)) {
            char sub[4096];
            snprintf(sub, sizeof sub, "%s/.git", path);
            if (access(sub, F_OK) == 0)
                die("%s is a repository of its own (a submodule), which this git does not add", path);
            walk(path, out);
            free(path);
        } else if (S_ISREG(sb.st_mode) || S_ISLNK(sb.st_mode)) {
            *(char **)array_push(out) = path;
        } else {
            free(path);                      /* a socket, a device: not a file git keeps */
        }
    }
    closedir(d);
}

/* Is path one of the files the pathspec p names: p itself, or under it? */
static int under(const char *path, size_t len, const char *p)
{
    size_t n = strlen(p);
    return n == 0 || (len >= n && memcmp(path, p, n) == 0 && (len == n || path[n] == '/'));
}

/* The entry for the file at path as it is now: its blob stored, its stat. */
static void entry_of(const char *path, IndexEntry *e)
{
    struct stat sb;
    if (lstat(path, &sb) != 0)
        die("%s: %s", path, strerror(errno));
    size_t n;
    char *data;
    if (S_ISLNK(sb.st_mode)) {               /* a symbolic link: its blob is where it points */
        data = xmalloc((size_t)sb.st_size + 1);
        ssize_t got = readlink(path, data, (size_t)sb.st_size + 1);
        if (got < 0)
            die("%s: %s", path, strerror(errno));
        n = (size_t)got;
        e->mode = 0120000;
    } else {
        data = read_file(path, &n);
        if (data == NULL)
            die("%s: gone while it was being added", path);
        e->mode = (sb.st_mode & 0100) ? 0100755 : 0100644;
    }
    object_write(OBJ_BLOB, data, n, e->oid);
    free(data);
    st.hashed++;
#ifdef __APPLE__
    e->ctime_s = (uint32_t)sb.st_ctimespec.tv_sec;
    e->ctime_ns = (uint32_t)sb.st_ctimespec.tv_nsec;
    e->mtime_s = (uint32_t)sb.st_mtimespec.tv_sec;
    e->mtime_ns = (uint32_t)sb.st_mtimespec.tv_nsec;
#else
    e->ctime_s = (uint32_t)sb.st_ctim.tv_sec;
    e->ctime_ns = (uint32_t)sb.st_ctim.tv_nsec;
    e->mtime_s = (uint32_t)sb.st_mtim.tv_sec;
    e->mtime_ns = (uint32_t)sb.st_mtim.tv_nsec;
#endif
    e->dev = (uint32_t)sb.st_dev;
    e->ino = (uint32_t)sb.st_ino;
    e->uid = (uint32_t)sb.st_uid;
    e->gid = (uint32_t)sb.st_gid;
    e->size = (uint32_t)sb.st_size;
}

void index_add(Index *ix, char **paths, size_t n)
{
    // @build 10.02 add: the files named, found, sorted, and merged into the index's sorted list
    Array found;                             /* char *: every file under the paths */
    array_init(&found, sizeof(char *));
    for (size_t i = 0; i < n; i++) {
        struct stat sb;
        if (lstat(*paths[i] ? paths[i] : ".", &sb) != 0) {
            int known = 0;                   /* gone: fine if the index has it, to take it out */
            for (size_t k = 0; k < ix->entries.len && !known; k++) {
                IndexEntry *e = array_at(&ix->entries, k);
                known = under(e->path, e->len, paths[i]);
            }
            if (!known)
                die("pathspec '%s' did not match any files", paths[i]);
        } else if (S_ISDIR(sb.st_mode)) {
            walk(paths[i], &found);
        } else {
            *(char **)array_push(&found) = xstrndup(paths[i], strlen(paths[i]));
        }
    }
    /* the walk finds them in no order: sort them as the index is (02.02's merge sort) */
    sort_merge((void **)found.data, found.len, cmp_paths, NULL);

    /* merge two sorted lists, the index and the files found, into a new index */
    Array merged;
    array_init(&merged, sizeof(IndexEntry));
    size_t i = 0, j = 0;
    while (i < ix->entries.len || j < found.len) {
        IndexEntry *e = i < ix->entries.len ? array_at(&ix->entries, i) : NULL;
        const char *f = j < found.len ? *(char **)array_at(&found, j) : NULL;
        if (f != NULL && j > 0 && strcmp(f, *(char **)array_at(&found, j - 1)) == 0) {
            j++;                             /* named twice */
            continue;
        }
        int c = e == NULL ? 1 : f == NULL ? -1 : path_cmp(e->path, e->len, f, strlen(f));
        if (c < 0) {                         /* in the index, not found: gone if it is under a path */
            int gone = 0;
            for (size_t k = 0; k < n && !gone; k++)
                gone = under(e->path, e->len, paths[k]);
            if (gone) {
                if (git_tracing())
                    trace("index: remove %s", e->path);
                cache_invalidate(ix, e->path, e->len);
                free(e->path);
            } else {
                *(IndexEntry *)array_push(&merged) = *e;
            }
            i++;
            continue;
        }
        IndexEntry ne;
        if (!path_ok(f, strlen(f)))
            die("'%s' is not a path git keeps", f);
        entry_of(f, &ne);
        ne.len = strlen(f);
        if (c == 0) {                        /* in both: the same file, perhaps changed */
            ne.path = e->path;
            if (ne.mode != e->mode || memcmp(ne.oid, e->oid, 20) != 0) {
                if (git_tracing())
                    trace("index: update %s %o %s", f, ne.mode, short_hex(ne.oid));
                cache_invalidate(ix, f, ne.len);
            }
            i++;
        } else {                             /* new */
            ne.path = xstrndup(f, ne.len);
            if (git_tracing())
                trace("index: add %s %o %s", f, ne.mode, short_hex(ne.oid));
            cache_invalidate(ix, f, ne.len);
        }
        *(IndexEntry *)array_push(&merged) = ne;
        j++;
    }
    for (size_t k = 0; k < found.len; k++)
        free(*(char **)array_at(&found, k));
    array_free(&found);
    array_free(&ix->entries);
    ix->entries = merged;
    // @end
}
