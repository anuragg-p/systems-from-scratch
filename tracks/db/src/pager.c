/*
 * pager.c - the database file as an array of numbered pages.
 *
 * Everything above this file sees pages, never the file: pager_get(n) gives
 * the bytes of page n, pager_write(n) the same bytes made writable. Pages
 * are numbered from 1; page n lives at byte offset (n - 1) * page_size.
 * Page 1 starts with the 100-byte database header.
 * Pages are read through a cache of the ones used most recently. @from 01.02
 *
 * A changed ("dirty") page stays in memory until COMMIT. Nothing touches
 * the database file before then, so ROLLBACK only has to forget the dirty
 * pages, and a crash before COMMIT leaves the file as it was.
 * The rollback journal (journal.c) makes COMMIT itself atomic. @from 06.02
 * So does the write-ahead log (wal.c), the other journal mode. @from 06.04
 */
#include <errno.h>
#include <fcntl.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#include "db.h"

/* ------------------------------------------------------------ raw pages (01.01) */

/* Read page pgno from the database file into buf (page_size bytes). Bytes
 * past the end of the file, including a short last page, read as zeroes.
 * An I/O error is fatal: the caller cannot carry on without the page. */
void read_page(Pager *p, u32 pgno, u8 *buf)
{
    // @build 01.01 read a page
    off_t off = (off_t)(pgno - 1) * p->page_size;
    ssize_t got = 0;
    while (got < (ssize_t)p->page_size) {
        ssize_t n = pread(p->fd, buf + got, p->page_size - (size_t)got, off + got);
        if (n < 0) {
            if (errno == EINTR)
                continue;
            fatal("reading page %u of %s: %s", pgno, p->path, strerror(errno));
        }
        if (n == 0)
            break;
        got += n;
    }
    memset(buf + got, 0, p->page_size - (size_t)got);
    stats.pages_read++;
    // @end
}

/* Write buf as page pgno of the database file, retrying short writes.
 * Writing past the end of the file makes the file longer. An I/O error is
 * fatal. */
void write_page(Pager *p, u32 pgno, const u8 *buf)
{
    // @build 01.01 write a page
    off_t off = (off_t)(pgno - 1) * p->page_size;
    size_t done = 0;
    while (done < p->page_size) {
        ssize_t n = pwrite(p->fd, buf + done, p->page_size - done, off + (off_t)done);
        if (n < 0) {
            if (errno == EINTR)
                continue;
            fatal("writing page %u of %s: %s", pgno, p->path, strerror(errno));
        }
        done += (size_t)n;
    }
    stats.pages_written++;
    // @end
}

/* An empty file is an empty database. The first time anything is written
 * to it, page 1 is made: the 100-byte header, then an empty table leaf
 * page, the root of sqlite_schema. The values are the ones sqlite3 writes. */
void header_init(Pager *p)
{
    p->npages = 1;
    u8 *d = pager_write(p, 1);
    // @build 01.01 the database header
    /* The page arrives zeroed. Header fields, by offset:
     *   0   the 16 bytes "SQLite format 3" and its terminating NUL
     *   16  page size, 2 bytes (65536 is stored as 1)
     *   18  file format write and read versions: 1 and 1 (rollback journal)
     *   20  reserved bytes per page: 0
     *   21  payload fractions: 64, 32, 32 (fixed by the format)
     *   44  schema format number: 4
     *   56  text encoding: 1 (UTF-8)
     *   96  SQLITE_VERSION_STAMP
     * The page count (28), change counter (24) and version-valid-for (92)
     * are left at zero: every commit sets them. */
    memcpy(d, "SQLite format 3", 16);
    put2(d + 16, p->page_size == 65536 ? 1 : p->page_size);
    d[18] = 1;
    d[19] = 1;
    d[20] = 0;
    d[21] = 64;
    d[22] = 32;
    d[23] = 32;
    put4(d + 44, 4);
    put4(d + 56, 1);
    put4(d + 96, SQLITE_VERSION_STAMP);

    /* The b-tree page header follows at offset 100: an empty table leaf,
     * with no freeblocks, no cells, and the cell content area starting at
     * the end of the page (65536 is stored as 0). */
    u8 *h = d + 100;
    h[0] = PAGE_TABLE_LEAF;
    put2(h + 1, 0);
    put2(h + 3, 0);
    put2(h + 5, p->page_size == 65536 ? 0 : p->page_size);
    h[7] = 0;
    // @end
}

// @from 01.02
/* ------------------------------------------------------------ the page cache (01.02) */

static u32 hash_of(Pager *p, u32 pgno)
{
    return (pgno * 2654435761u) & (p->nhash - 1);
}

/* The LRU list holds only clean pages, most recently used first. A dirty
 * page cannot be evicted, so it leaves the list when it is first written
 * and comes back when it is committed; eviction never has to skip it. */
static void lru_unlink(Page *pg)
{
    pg->prev->next = pg->next;
    pg->next->prev = pg->prev;
    pg->prev = pg->next = NULL;
}

static void lru_push_front(Pager *p, Page *pg)
{
    pg->next = p->lru.next;
    pg->prev = &p->lru;
    p->lru.next->prev = pg;
    p->lru.next = pg;
}

static void hash_remove(Pager *p, Page *pg)
{
    Page **pp = &p->hash[hash_of(p, pg->pgno)];
    while (*pp != pg)
        pp = &(*pp)->hnext;
    *pp = pg->hnext;
}

/* Double the hash table when it gets crowded: a big transaction can hold
 * many more dirty pages than cache_max. */
static void hash_grow(Pager *p)
{
    u32 old = p->nhash;
    Page **oh = p->hash;
    p->nhash = old * 2;
    p->hash = xcalloc(p->nhash, sizeof(Page *));
    for (u32 i = 0; i < old; i++) {
        Page *pg = oh[i];
        while (pg) {
            Page *next = pg->hnext;
            u32 h = hash_of(p, pg->pgno);
            pg->hnext = p->hash[h];
            p->hash[h] = pg;
            pg = next;
        }
    }
    free(oh);
}
// @end

// @from 06.04
/* The bytes of page pgno, from the WAL if it has a newer copy, else from
 * the database file. */
// @else
// /* The bytes of page pgno, from the database file. */
// @end
static void fetch_page(Pager *p, u32 pgno, u8 *buf)
{
    if (pgno > p->npages_orig) {
        /* Added by this transaction: nothing committed holds it yet. */
        memset(buf, 0, p->page_size);
        return;
    }
    // @from 06.04
    if (p->wal && wal_read(p, pgno, buf))
        return;
    // @end
    read_page(p, pgno, buf);
}

/* Find page pgno in the cache, loading it on a miss, and move it to the
 * front of the LRU list. Pages are chained in hash buckets through hnext.
 * A dirty page is not on the LRU list (prev is NULL) and stays off it. */
static Page *page_get(Pager *p, u32 pgno)
{
    if (pgno == 0 || pgno > p->npages)
        fatal("page %u is out of range (the database has %u pages)", pgno, p->npages);
    // @build 01.02 look up a page in the cache
    Page *pg;
    for (pg = p->hash[hash_of(p, pgno)]; pg; pg = pg->hnext) {
        if (pg->pgno == pgno) {
            if (pg->prev) {
                lru_unlink(pg);
                lru_push_front(p, pg);
            }
            stats.cache_hits++;
            return pg;
        }
    }
    /* Nothing is evicted here: callers may hold pointers into other
     * pages. Eviction waits for pager_shrink(). */
    if (p->ncached >= 2 * p->nhash)
        hash_grow(p);
    /* The page's bytes sit right after the struct, in one allocation. */
    pg = xmalloc(sizeof *pg + p->page_size);
    memset(pg, 0, sizeof *pg);
    pg->pgno = pgno;
    pg->data = (u8 *)(pg + 1);
    fetch_page(p, pgno, pg->data);
    u32 h = hash_of(p, pgno);
    pg->hnext = p->hash[h];
    p->hash[h] = pg;
    lru_push_front(p, pg);
    p->ncached++;
    stats.cache_misses++;
    return pg;
    // @end
}

// @from 01.02
// @else
// /* There is no cache: every request reads the page from the file into
//  * memory of its own, which is never given back. A page that has been
//  * changed is the only copy of the change until it is written, so the
//  * dirty list is searched first. */
// static Page *page_get(Pager *p, u32 pgno)
// {
//     if (pgno == 0 || pgno > p->npages)
//         fatal("page %u is out of range (the database has %u pages)", pgno, p->npages);
//     for (Page *pg = p->dirty; pg; pg = pg->dnext)
//         if (pg->pgno == pgno)
//             return pg;
//     Page *pg = xmalloc(sizeof *pg + p->page_size);
//     memset(pg, 0, sizeof *pg);
//     pg->pgno = pgno;
//     pg->data = (u8 *)(pg + 1);
//     fetch_page(p, pgno, pg->data);
//     return pg;
// }
// @end

/* Evict clean pages from the cold end of the LRU list until no more than
 * cache_max clean pages are cached. Only called between rows and
 * statements, when no one holds a pointer into a page. */
void pager_shrink(Pager *p)
{
    // @build 01.02 evict cold pages
    /* Every page on the list is clean: what it holds can be read again.
     * Dirty pages are not on the list and do not count against cache_max:
     * they are the only copy of this transaction's changes, so they stay
     * in memory until it commits. */
    while (p->ncached - p->ndirty > p->cache_max && p->lru.prev != &p->lru) {
        Page *pg = p->lru.prev;
        lru_unlink(pg);
        hash_remove(p, pg);
        free(pg);
        p->ncached--;
        stats.evictions++;
    }
    // @end
}

u8 *pager_get(Pager *p, u32 pgno)
{
    return page_get(p, pgno)->data;
}

/* Make page pgno writable and return its bytes: it joins the dirty list and
 * is written at COMMIT. While a statement is active, the page's content
 * from before the statement is saved on first write, so the statement
 * alone can be undone if it fails. Pages added by the statement need no
 * copy; rolling back forgets them. */
u8 *pager_write(Pager *p, u32 pgno)
{
    Page *pg = page_get(p, pgno);
    if (p->stmt_active && pg->stmt_gen != p->stmt_gen && pgno <= p->stmt_npages) {
        if (p->nsaved == p->saved_cap) {
            p->saved_cap = p->saved_cap ? 2 * p->saved_cap : 64;
            p->saved = xrealloc(p->saved, p->saved_cap * sizeof *p->saved);
        }
        u8 *copy = xmalloc(p->page_size);
        memcpy(copy, pg->data, p->page_size);
        p->saved[p->nsaved].pgno = pgno;
        p->saved[p->nsaved].data = copy;
        p->nsaved++;
        pg->stmt_gen = p->stmt_gen;
    }
    if (!pg->dirty) {
        // @from 01.02
        if (pg->prev)
            lru_unlink(pg);       /* pinned until commit */
        // @end
        pg->dirty = 1;
        pg->dnext = p->dirty;
        p->dirty = pg;
        p->ndirty++;
    }
    return pg->data;
}

// @from 01.02
/* Remove a cached page from the dirty list, the LRU list and the hash
 * table and free it, discarding any change it holds. Used when the page is
 * past the end of the database or its content no longer matters. */
// @else
// /* Remove a page from the dirty list and free it, discarding any change
//  * it holds. Used when the page is past the end of the database or its
//  * content no longer matters. */
// @end
static void forget(Pager *p, Page *pg)
{
    if (pg->dirty) {
        Page **pp = &p->dirty;
        while (*pp != pg)
            pp = &(*pp)->dnext;
        *pp = pg->dnext;
        p->ndirty--;
    }
    // @from 01.02
    if (pg->prev)
        lru_unlink(pg);
    hash_remove(p, pg);
    // @end
    free(pg);
    p->ncached--;  // @from 01.02
}

// @from 01.02
void pager_drop(Pager *p, u32 pgno)
{
    for (Page *pg = p->hash[hash_of(p, pgno)]; pg; pg = pg->hnext) {
        if (pg->pgno == pgno) {
            forget(p, pg);
            return;
        }
    }
}
// @end

/* ------------------------------------------------------------ open and close */

static int read_header(Pager *p)
{
    u8 h[100];
    struct stat st;
    if (fstat(p->fd, &st) < 0)
        return err("cannot stat %s: %s", p->path, strerror(errno));
    if (st.st_size == 0) {
        p->page_size = DEFAULT_PAGE_SIZE;
        const char *env = getenv("DB_PAGE_SIZE");
        if (env) {
            u32 ps = (u32)atoi(env);
            if (ps >= 512 && ps <= 65536 && (ps & (ps - 1)) == 0)
                p->page_size = ps;
        }
        p->usable = p->page_size;
        p->npages = 0;
        p->journal_mode = JOURNAL_DELETE;
        return 0;
    }
    if (st.st_size < 100 || pread(p->fd, h, 100, 0) != 100)
        return err("file is not a database: %s", p->path);
    if (memcmp(h, "SQLite format 3", 16) != 0)
        return err("file is not a database: %s", p->path);
    u32 ps = get2(h + 16);
    if (ps == 1)
        ps = 65536;
    if (ps < 512 || ps > 65536 || (ps & (ps - 1)) != 0)
        return err("file is not a database: bad page size %u", ps);
    // @from 06.04
    if (h[18] > 2 || h[19] > 2)
        return err("file format version %d is newer than this engine understands", h[19]);
    // @else
    // if (h[18] > 1 || h[19] > 1)
    //     return err("file format version %d is newer than this engine understands", h[19]);
    // @end
    if (h[21] != 64 || h[22] != 32 || h[23] != 32)
        return err("file is not a database: bad payload fractions");
    u32 enc = get4(h + 56);
    if (enc != 0 && enc != 1)
        return err("only UTF-8 databases are supported (this one is UTF-16)");
    p->page_size = ps;
    p->usable = ps - h[20];
    /* The page count in the header is trusted only if the version-valid-for
     * number matches the change counter: an old program that did not know
     * about the field would have changed the file without updating it. */
    u32 n = get4(h + 28);
    if (n == 0 || get4(h + 24) != get4(h + 92))
        n = (u32)(st.st_size / ps);
    p->npages = n;
    p->journal_mode = h[18] == 2 ? JOURNAL_WAL : JOURNAL_DELETE;
    return 0;
}

int pager_open(Pager *p, const char *path)
{
    memset(p, 0, sizeof *p);
    p->path = xstrndup(path, strlen(path));
    p->fd = open(path, O_RDWR | O_CREAT, 0644);
    if (p->fd < 0)
        return err("cannot open %s: %s", path, strerror(errno));
    // @from 01.02
    p->nhash = 1024;
    p->hash = xcalloc(p->nhash, sizeof(Page *));
    p->lru.next = p->lru.prev = &p->lru;
    p->cache_max = DEFAULT_CACHE_PAGES;
    const char *env = getenv("DB_CACHE_PAGES");
    if (env && atoi(env) > 0)
        p->cache_max = (u32)atoi(env);
    // @end
    // @from 06.03
    /* A journal left by a crash must be played back before anything reads
     * the file: until then, the file may hold half a transaction. */
    if (journal_recover(p) < 0)
        return -1;
    // @end
    if (read_header(p) < 0)
        return -1;
    // @from 06.04
    if (p->journal_mode == JOURNAL_WAL) {
        if (wal_open(p) < 0)
            return -1;
        if (p->wal->nframes > 0)
            p->npages = p->wal->db_size;
    }
    // @end
    // @from 06.02
    // @else
    // p->journal_mode = JOURNAL_OFF;     /* no journal: a commit writes the pages in place */
    // @end
    p->npages_orig = p->npages;
    return 0;
}

void pager_close(Pager *p)
{
    // @from 06.04
    if (p->wal)
        wal_close(p, 1);
    // @end
    // @from 01.02
    for (u32 i = 0; i < p->nhash; i++) {
        Page *pg = p->hash[i];
        while (pg) {
            Page *next = pg->hnext;
            free(pg);
            pg = next;
        }
    }
    free(p->hash);
    // @end
    free(p->saved);
    if (p->fd >= 0)
        close(p->fd);
    free(p->path);
    p->fd = -1;
}

/* ------------------------------------------------------------ transactions */

static int by_pgno(const void *a, const void *b)
{
    u32 x = (*(Page *const *)a)->pgno, y = (*(Page *const *)b)->pgno;
    return x < y ? -1 : x > y;
}

/* Write every dirty page straight into the database file, then fsync it.
 * There is no journal (journal_mode=OFF): a crash in the middle leaves
 * half a transaction in the file. The crash points (DB_CRASH) can stage
 * exactly that. */
static int commit_unsafe(Pager *p, Page **pages, u32 n)
{
    for (u32 i = 0; i < n; i++) {
        if (i == n / 2 && crash_armed("db-torn")) {
            if (pwrite(p->fd, pages[i]->data, p->page_size / 2,
                       (off_t)(pages[i]->pgno - 1) * p->page_size) < 0)
                fatal("write: %s", strerror(errno));
            crash_point("db-torn");
        }
        write_page(p, pages[i]->pgno, pages[i]->data);
        if (i + 1 == (n + 1) / 2)
            crash_point("db-partial");
    }
    crash_point("db-written");
    if (sys_fsync(p->fd) < 0)
        fatal("fsync: %s", strerror(errno));
    return 0;
}

int pager_commit(Pager *p)
{
    if (p->ndirty == 0 && p->npages == p->npages_orig)
        return 0;
    // @from 06.04
    /* Every commit in rollback mode bumps the change counter in page 1, as
     * sqlite3 does; in WAL mode only when page 1 changes anyway or the
     * database grew. The page count and version-valid-for go with it. */
    // @else
    // /* Every commit bumps the change counter in page 1, as sqlite3 does.
    //  * The page count and version-valid-for go with it. */
    // @end
    int page1_dirty = 0;
    for (Page *pg = p->dirty; pg; pg = pg->dnext)
        if (pg->pgno == 1)
            page1_dirty = 1;
    if (p->journal_mode != JOURNAL_WAL || page1_dirty || p->npages != p->npages_orig) {
        u8 *h = pager_write(p, 1);
        u32 counter = get4(h + 24) + 1;
        put4(h + 24, counter);
        put4(h + 28, p->npages);
        put4(h + 92, counter);
        put4(h + 96, SQLITE_VERSION_STAMP);
    }
    Page **pages = xmalloc(p->ndirty * sizeof *pages);
    u32 n = 0;
    for (Page *pg = p->dirty; pg; pg = pg->dnext)
        pages[n++] = pg;
    qsort(pages, n, sizeof *pages, by_pgno);

    int rc;
    // @from 06.02
    // @from 06.04
    if (p->journal_mode == JOURNAL_WAL)
        rc = wal_commit(p, pages, n);
    else if (p->journal_mode == JOURNAL_DELETE)
    // @else
    // if (p->journal_mode == JOURNAL_DELETE)
    // @end
        rc = journal_commit(p, pages, n);
    else
        rc = commit_unsafe(p, pages, n);
    // @else
    // rc = commit_unsafe(p, pages, n);
    // @end
    free(pages);
    if (rc < 0)
        return rc;

    for (Page *pg = p->dirty; pg; pg = pg->dnext) {
        pg->dirty = 0;
        lru_push_front(p, pg);    /* clean again: evictable */ // @from 01.02
    }
    p->dirty = NULL;
    p->ndirty = 0;
    p->npages_orig = p->npages;
    pager_stmt_end(p);
    // @from 06.04
    if (p->wal && p->wal->nframes >= WAL_AUTOCHECKPOINT)
        wal_checkpoint(p);
    // @end
    return 0;
}

/* Forget every change since the transaction began. The file was never
 * touched, so the next read of a page fetches its committed version. */
void pager_rollback(Pager *p)
{
    while (p->dirty)
        forget(p, p->dirty);
    p->npages = p->npages_orig;
    pager_stmt_end(p);
}

/* ------------------------------------------------------------ statement savepoints */

void pager_stmt_begin(Pager *p)
{
    pager_stmt_end(p);
    p->stmt_active = 1;
    p->stmt_gen++;
    p->stmt_npages = p->npages;
}

void pager_stmt_end(Pager *p)
{
    for (u32 i = 0; i < p->nsaved; i++)
        free(p->saved[i].data);
    p->nsaved = 0;
    p->stmt_active = 0;
}

/* Put back every page the statement changed, and forget pages it added. */
void pager_stmt_rollback(Pager *p)
{
    for (u32 i = 0; i < p->nsaved; i++)
        memcpy(pager_get(p, p->saved[i].pgno), p->saved[i].data, p->page_size);
    Page *pg = p->dirty;
    while (pg) {
        Page *next = pg->dnext;
        if (pg->pgno > p->stmt_npages)
            forget(p, pg);
        pg = next;
    }
    p->npages = p->stmt_npages;
    pager_stmt_end(p);
}

// @from 06.02
/* ------------------------------------------------------------ journal modes */

// @from 06.04
/* Switch between the rollback journal, the WAL and no journal at all. The
 * file says which of the first two it uses in bytes 18 and 19 of the
 * header (1 = rollback, 2 = WAL); that change is itself committed with
 * the rollback journal, as sqlite3 does it. */
// @else
// /* Switch between the rollback journal and no journal at all. The file
//  * does not record the choice: every database opens with the rollback
//  * journal. */
// @end
int pager_set_journal_mode(Pager *p, int mode)
{
    if (mode == p->journal_mode)
        return 0;
    if (p->ndirty)
        return err("cannot change the journal mode inside a transaction");
    if (p->npages == 0)
        header_init(p);
    // @from 06.04
    if (p->journal_mode == JOURNAL_WAL) {
        wal_close(p, 1);
        p->journal_mode = JOURNAL_DELETE;
        u8 *h = pager_write(p, 1);
        h[18] = h[19] = 1;
        if (pager_commit(p) < 0)
            return -1;
    }
    if (mode == JOURNAL_WAL) {
        p->journal_mode = JOURNAL_DELETE;
        u8 *h = pager_write(p, 1);
        h[18] = h[19] = 2;
        if (pager_commit(p) < 0)
            return -1;
        p->journal_mode = JOURNAL_WAL;
        return wal_open(p);
    }
    // @end
    if (p->ndirty && pager_commit(p) < 0)
        return -1;
    p->journal_mode = mode;
    return 0;
}
// @end
