/*
 * journal.c - the rollback journal.
 *
 * Before the database file is changed, the original content of every page
 * the transaction will overwrite is copied into a second file, the
 * journal, next to it (file.db-journal). Then the pages are written in
 * place. Deleting the journal is the commit: one filesystem operation that
 * either happened or did not. A crash before it leaves a "hot" journal,
 * from which the originals can be copied back, undoing the half-written
 * transaction.
 * The next open does just that, in journal_recover(). @from 06.03
 *
 * The journal is in SQLite's own format, so sqlite3 can roll back a
 * journal we left.
 * We can roll back one sqlite3 left, too. @from 06.03
 * The format:
 *
 *   header, padded to one sector (we use 512 bytes):
 *     0   8 bytes  magic d9 d5 05 f9 20 a1 63 d7
 *     8   4        number of page records that follow (nRec)
 *     12  4        nonce: a random number that seeds the checksums
 *     16  4        database size in pages before the transaction
 *     20  4        sector size
 *     24  4        page size
 *   then nRec records:
 *     4 bytes page number, page_size bytes original content, 4 bytes checksum
 *
 * The header is first written with the magic and nRec zeroed: a journal
 * whose first byte is 0 is not hot, so a crash while it is being written
 * leaves nothing to roll back (the database file has not been touched).
 */
#include <errno.h>
#include <fcntl.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

#include "db.h"

#define JOURNAL_SECTOR 512
static const u8 journal_magic[8] = {0xd9, 0xd5, 0x05, 0xf9, 0x20, 0xa1, 0x63, 0xd7};

/* The journal's path: the database path plus "-journal". The caller frees
 * it. */
char *journal_path(Pager *p)
{
    size_t n = strlen(p->path);
    char *s = xmalloc(n + 9);
    memcpy(s, p->path, n);
    memcpy(s + n, "-journal", 9);
    return s;
}

/* SQLite's journal checksum: the nonce plus every 200th byte of the page,
 * counting down from 200 bytes before its end. Weak, but enough to notice
 * a record that was never completely written. */
static u32 journal_checksum(u32 nonce, const u8 *data, u32 page_size)
{
    u32 sum = nonce;
    for (int i = (int)page_size - 200; i > 0; i -= 200)
        sum += data[i];
    return sum;
}

/* pwrite() that finishes a short write, retries on EINTR and treats any
 * other error as fatal (what names the file in the message). */
static void must_pwrite(int fd, const void *buf, size_t n, off_t off, const char *what)
{
    size_t done = 0;
    while (done < n) {
        ssize_t w = pwrite(fd, (const u8 *)buf + done, n - done, off + (off_t)done);
        if (w < 0) {
            if (errno == EINTR)
                continue;
            fatal("writing %s: %s", what, strerror(errno));
        }
        done += (size_t)w;
    }
}

/* A nonce for a new journal, from /dev/urandom mixed with the time and
 * process id. It need not be secret, only different from journal to
 * journal, so that stale records left in a reused file fail their
 * checksums. */
static u32 nonce_seed(void)
{
    u32 r = 0;
    int fd = open("/dev/urandom", O_RDONLY);
    if (fd >= 0) {
        if (read(fd, &r, sizeof r) != sizeof r)
            r = 0;
        close(fd);
    }
    return r ^ (u32)time(NULL) ^ (u32)getpid();
}

/* Copies the original of every page this transaction overwrites into the
 * journal (jfd, empty), then makes it hot.
 *
 * Only pages that existed before the transaction (pgno <= npages_orig)
 * get a record: newer pages have no original, and recovery cuts the file
 * back to npages_orig. The header goes out first with the magic and nRec
 * zeroed, so a crash while the records are being written leaves a journal
 * that is not hot. The records and the new directory entry are made
 * durable before the magic and the real nRec are written over the first
 * 12 bytes; only then can the database file be touched. */
static void journal_write(Pager *p, Page **pages, u32 n, int jfd, const char *jpath)
{
    // @build 06.02 write the journal
    u8 hdr[JOURNAL_SECTOR];
    memset(hdr, 0, sizeof hdr);
    u32 nonce = nonce_seed();
    put4(hdr + 12, nonce);
    put4(hdr + 16, p->npages_orig);
    put4(hdr + 20, JOURNAL_SECTOR);
    put4(hdr + 24, p->page_size);
    must_pwrite(jfd, hdr, sizeof hdr, 0, jpath);

    /* The originals are still in the database file: nothing has been
     * written over them yet. */
    u32 want = 0;
    for (u32 i = 0; i < n; i++)
        if (pages[i]->pgno <= p->npages_orig)
            want++;
    size_t reclen = 8 + p->page_size;
    u8 *rec = xmalloc(reclen);
    off_t off = JOURNAL_SECTOR;
    u32 nrec = 0;
    for (u32 i = 0; i < n; i++) {
        u32 pgno = pages[i]->pgno;
        if (pgno > p->npages_orig)
            continue;
        put4(rec, pgno);
        read_page(p, pgno, rec + 4);
        put4(rec + 4 + p->page_size, journal_checksum(nonce, rec + 4, p->page_size));
        must_pwrite(jfd, rec, reclen, off, jpath);
        off += (off_t)reclen;
        nrec++;
        stats.journal_pages++;
        if (nrec == (want + 1) / 2)
            crash_point("journal-partial");
    }
    free(rec);

    if (sys_fsync(jfd) < 0)
        fatal("fsync %s: %s", jpath, strerror(errno));
    fsync_dir(jpath);
    memcpy(hdr, journal_magic, 8);
    put4(hdr + 8, nrec);
    must_pwrite(jfd, hdr, 12, 0, jpath);
    if (sys_fsync(jfd) < 0)
        fatal("fsync %s: %s", jpath, strerror(errno));
    crash_point("journal-hot");
    // @end
}

/* Commits the dirty pages (sorted by page number) with a rollback
 * journal. The order of the steps is what makes the commit atomic:
 *
 *   1. journal the originals and make the journal hot
 *   2. write the new pages into the database file
 *   3. fsync the database file: the new pages are durable
 *   4. delete the journal: the moment the transaction commits
 *
 * A crash before step 4 leaves a hot journal that the next open rolls
 * back; a crash after it leaves a complete transaction. Any I/O error is
 * fatal. Returns 0. */
int journal_commit(Pager *p, Page **pages, u32 n)
{
    char *jpath = journal_path(p);
    // @build 06.02 commit with the journal
    int jfd = open(jpath, O_RDWR | O_CREAT | O_TRUNC, 0644);
    if (jfd < 0)
        fatal("cannot create %s: %s", jpath, strerror(errno));
    journal_write(p, pages, n, jfd, jpath);

    for (u32 i = 0; i < n; i++) {
        /* A torn page: with db-torn armed, only the first half of the
         * middle page reaches the file before the crash. */
        if (i == n / 2 && crash_armed("db-torn")) {
            must_pwrite(p->fd, pages[i]->data, p->page_size / 2,
                        (off_t)(pages[i]->pgno - 1) * p->page_size, p->path);
            crash_point("db-torn");
        }
        write_page(p, pages[i]->pgno, pages[i]->data);
        if (i + 1 == (n + 1) / 2)
            crash_point("db-partial");
    }
    crash_point("db-written");
    if (sys_fsync(p->fd) < 0)
        fatal("fsync %s: %s", p->path, strerror(errno));

    crash_point("before-delete");
    close(jfd);
    if (unlink(jpath) < 0)
        fatal("cannot delete %s: %s", jpath, strerror(errno));
    free(jpath);
    return 0;
    // @end
}

// @from 06.03
/* Reads exactly n bytes at off. Returns 1 on success, 0 if the file ends
 * first or the read fails. */
static int read_at(int fd, void *buf, size_t n, off_t off)
{
    size_t got = 0;
    while (got < n) {
        ssize_t r = pread(fd, (u8 *)buf + got, n - got, off + (off_t)got);
        if (r < 0 && errno == EINTR)
            continue;
        if (r <= 0)
            return 0;
        got += (size_t)r;
    }
    return 1;
}

/* 1 if v is a power of two in [lo, hi]. */
static int power_of_two(u32 v, u32 lo, u32 hi)
{
    return v >= lo && v <= hi && (v & (v - 1)) == 0;
}
// @end

/* Called when the database is opened. A hot journal means the last
 * transaction did not finish, so its original pages are copied back and
 * the file is cut to its original size. Returns 0 (also when there is no
 * journal), or -1 with errmsg set if the journal header is unusable.
 *
 * A journal that is shorter than its 28-byte header or lacks the magic
 * never became hot, so the database was not touched and the journal is
 * simply deleted. Both sizes in the header must be powers of two (page
 * 512..65536, sector 32..65536) or recovery refuses. Recovery is safe to
 * run twice, since it only copies originals back: a crash during it just
 * leaves the journal for the next open. */
int journal_recover(Pager *p)
{
    char *jpath = journal_path(p);
    int jfd = open(jpath, O_RDONLY);
    if (jfd < 0) {
        free(jpath);
        return 0;    /* no journal: the last transaction finished */
    }
    // @build 06.03 roll back a hot journal
    struct stat st;
    u8 hdr[28];
    if (fstat(jfd, &st) < 0 || st.st_size < 28 || !read_at(jfd, hdr, 28, 0) ||
        memcmp(hdr, journal_magic, 8) != 0) {
        close(jfd);
        unlink(jpath);
        free(jpath);
        return 0;
    }
    u32 orig = get4(hdr + 16);
    u32 sector = get4(hdr + 20);
    u32 ps = get4(hdr + 24);
    if (!power_of_two(ps, 512, 65536) || !power_of_two(sector, 32, 65536)) {
        close(jfd);
        free(jpath);
        return err("hot journal %s has a bad header; not touching the database", jpath);
    }
    /* Records start one sector into the file. sqlite3 may have written
     * several segments, each a header followed by its records. */
    u8 *rec = xmalloc(8 + ps);
    off_t hdr_off = 0;
    u32 restored = 0;
    for (;;) {
        u32 nrec = get4(hdr + 8), nonce = get4(hdr + 12);
        off_t off = hdr_off + sector;
        /* nRec of 0xffffffff means as many records as fit in the file. */
        if (nrec == 0xffffffff)
            nrec = (u32)((st.st_size - off) / (8 + ps));
        int stop = 0;
        for (u32 i = 0; i < nrec; i++, off += 8 + ps) {
            /* A record that is cut short or fails its checksum was being
             * written when the crash came: it and all after it are
             * ignored. */
            if (!read_at(jfd, rec, 8 + ps, off) ||
                get4(rec + 4 + ps) != journal_checksum(nonce, rec + 4, ps)) {
                stop = 1;
                break;
            }
            u32 pgno = get4(rec);
            if (pgno == 0 || pgno > orig)
                continue;
            must_pwrite(p->fd, rec + 4, ps, (off_t)(pgno - 1) * ps, p->path);
            restored++;
            if (restored == 1)
                crash_point("recover-partial");
        }
        if (stop)
            break;
        /* The next segment, if any, starts at the next sector boundary. */
        hdr_off = (off + sector - 1) / sector * sector;
        if (hdr_off + 28 > st.st_size || !read_at(jfd, hdr, 28, hdr_off) ||
            memcmp(hdr, journal_magic, 8) != 0)
            break;
    }
    free(rec);
    /* Pages the transaction added past the original size are cut off. */
    if (ftruncate(p->fd, (off_t)orig * ps) < 0)
        fatal("truncating %s: %s", p->path, strerror(errno));
    if (sys_fsync(p->fd) < 0)
        fatal("fsync %s: %s", p->path, strerror(errno));
    close(jfd);
    if (unlink(jpath) < 0)
        fatal("cannot delete %s: %s", jpath, strerror(errno));
    fsync_dir(jpath);
    fflush(stdout);
    fprintf(stderr, "db: rolled back an interrupted transaction (%u pages)\n", restored);
    free(jpath);
    return 0;
    // @end
}
