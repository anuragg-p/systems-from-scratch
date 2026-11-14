/*
 * wal.c - the write-ahead log.
 *
 * The rollback journal saves the old pages and overwrites the database in
 * place. A write-ahead log does the opposite: the database file is left
 * alone, and each commit appends the new versions of its pages to a second
 * file, file.db-wal. The last page of a transaction carries a commit mark.
 * Readers look in the log first. Now and then a checkpoint copies the
 * newest version of each page back into the database and empties the log.
 *
 * A commit is one append and one fsync, and a crash can only leave a torn
 * tail on the log, which the checksums expose: everything after the last
 * intact commit mark is ignored.
 *
 * The format is SQLite's:
 *
 *   header, 32 bytes:
 *     0  magic 0x377f0682 (checksums over little-endian words) or
 *              0x377f0683 (big-endian words; what we write)
 *     4  format version 3007000     8  page size     12  checkpoint sequence
 *     16 salt-1     20 salt-2       24 checksum-1    28  checksum-2
 *   then frames, each a 24-byte header and one page:
 *     0  page number
 *     4  for a commit frame, the database size in pages after it; else 0
 *     8  salt-1   12  salt-2  (must match the header's)
 *     16 checksum-1   20 checksum-2
 *
 * Checksums run on, from the header through every frame: each frame's
 * checksum covers its first 8 header bytes and its page, starting from
 * the previous frame's checksum. sqlite3 keeps an index of the log in a
 * shared-memory file (-shm); we keep ours in memory and rebuild it from
 * the log when we open the database, which is what sqlite3 does too when
 * no other process has the database open.
 */
#include <errno.h>
#include <fcntl.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

#include "db.h"

#define WAL_MAGIC 0x377f0682
#define WAL_VERSION 3007000
#define WAL_HDR 32
#define FRAME_HDR 24

/* File offset of a frame; frames are numbered from 1. */
static off_t frame_offset(Pager *p, u32 frame)
{
    return WAL_HDR + (off_t)(frame - 1) * (FRAME_HDR + p->page_size);
}

/* SQLite's WAL checksum: two running 32-bit sums over pairs of words,
 * read in the byte order the log's magic number selects. n must be a
 * multiple of 8; (*s0, *s1) carries the chain from one call to the next. */
static void wal_checksum(int bigendian, const u8 *d, u32 n, u32 *s0, u32 *s1)
{
    u32 a = *s0, b = *s1;
    for (u32 i = 0; i < n; i += 8) {
        u32 x0, x1;
        if (bigendian) {
            x0 = get4(d + i);
            x1 = get4(d + i + 4);
        } else {
            x0 = (u32)d[i] | (u32)d[i + 1] << 8 | (u32)d[i + 2] << 16 | (u32)d[i + 3] << 24;
            x1 = (u32)d[i + 4] | (u32)d[i + 5] << 8 | (u32)d[i + 6] << 16 | (u32)d[i + 7] << 24;
        }
        a += x0 + b;
        b += x1 + a;
    }
    *s0 = a;
    *s1 = b;
}

/* pwrite() that finishes a short write, retries on EINTR and treats any
 * other error as fatal. */
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

/* The in-memory index: frame_of[pgno] is the newest committed frame that
 * holds the page, 0 if the log has none. index_set grows the table to
 * cover pgno. */
static void index_set(Wal *w, u32 pgno, u32 frame)
{
    if (pgno >= w->frame_of_cap) {
        u32 cap = w->frame_of_cap ? w->frame_of_cap : 1024;
        while (cap <= pgno)
            cap *= 2;
        w->frame_of = xrealloc(w->frame_of, cap * sizeof(u32));
        memset(w->frame_of + w->frame_of_cap, 0, (cap - w->frame_of_cap) * sizeof(u32));
        w->frame_of_cap = cap;
    }
    w->frame_of[pgno] = frame;
}

/* Forgets every frame: the log is empty. */
static void index_clear(Wal *w)
{
    if (w->frame_of)
        memset(w->frame_of, 0, w->frame_of_cap * sizeof(u32));
    w->nframes = 0;
    w->db_size = 0;
}

/* Opens file.db-wal (creating it if absent) and rebuilds the index from
 * the frames in it. Returns 0, or -1 with errmsg set if the file cannot
 * be opened. A log with a bad header, or for another page size, is
 * treated as empty.
 *
 * A frame is valid if its salts match the header's and its checksum,
 * chained from the previous valid frame, is right. Scanning stops at the
 * first invalid frame, and only frames up to the last commit frame (one
 * whose database size field is non-zero) count: anything after it is the
 * torn tail of a commit that never finished. The running checksum at that
 * commit frame is kept, so the next commit continues the chain. */
int wal_open(Pager *p)
{
    Wal *w = xcalloc(1, sizeof *w);
    size_t n = strlen(p->path);
    w->path = xmalloc(n + 5);
    memcpy(w->path, p->path, n);
    memcpy(w->path + n, "-wal", 5);
    w->fd = open(w->path, O_RDWR | O_CREAT, 0644);
    if (w->fd < 0) {
        free(w->path);
        free(w);
        return err("cannot open %s: %s", p->path, strerror(errno));
    }
    w->bigendian = 1;
    p->wal = w;
    struct stat st;
    if (fstat(w->fd, &st) < 0 || st.st_size < WAL_HDR)
        return 0;    /* empty: a new log */
    // @build 06.04 read the log
    u8 hdr[WAL_HDR];
    if (!read_at(w->fd, hdr, WAL_HDR, 0))
        return 0;
    u32 magic = get4(hdr);
    if ((magic & ~1u) != WAL_MAGIC || get4(hdr + 4) != WAL_VERSION || get4(hdr + 8) != p->page_size)
        return 0;
    int big = magic & 1;
    u32 s0 = 0, s1 = 0;
    wal_checksum(big, hdr, 24, &s0, &s1);
    if (s0 != get4(hdr + 24) || s1 != get4(hdr + 28))
        return 0;
    w->bigendian = big;
    w->ckpt_seq = get4(hdr + 12);
    w->salt1 = get4(hdr + 16);
    w->salt2 = get4(hdr + 20);
    w->s0 = s0;
    w->s1 = s1;

    size_t flen = FRAME_HDR + p->page_size;
    u8 *f = xmalloc(flen);
    u32 *pending = xmalloc(sizeof(u32));
    u32 npending = 0, pending_cap = 1;
    for (u32 frame = 1; frame_offset(p, frame) + (off_t)flen <= st.st_size; frame++) {
        if (!read_at(w->fd, f, flen, frame_offset(p, frame)))
            break;
        if (get4(f + 8) != w->salt1 || get4(f + 12) != w->salt2)
            break;
        wal_checksum(big, f, 8, &s0, &s1);
        wal_checksum(big, f + FRAME_HDR, p->page_size, &s0, &s1);
        if (s0 != get4(f + 16) || s1 != get4(f + 20))
            break;
        if (npending == pending_cap) {
            pending_cap *= 2;
            pending = xrealloc(pending, pending_cap * sizeof(u32));
        }
        pending[npending++] = get4(f);
        if (get4(f + 4) != 0) {
            /* A commit frame: every frame since the last commit is real. */
            u32 first = frame - npending + 1;
            for (u32 i = 0; i < npending; i++)
                index_set(w, pending[i], first + i);
            npending = 0;
            w->nframes = frame;
            w->db_size = get4(f + 4);
            w->s0 = s0;
            w->s1 = s1;
        }
    }
    free(pending);
    free(f);
    return 0;
    // @end
}

/* Copies the newest committed version of the page into buf. Returns 1 if
 * the log has the page, 0 if the caller should read the database file. */
int wal_read(Pager *p, u32 pgno, u8 *buf)
{
    Wal *w = p->wal;
    if (pgno >= w->frame_of_cap || w->frame_of[pgno] == 0)
        return 0;
    if (!read_at(w->fd, buf, p->page_size, frame_offset(p, w->frame_of[pgno]) + FRAME_HDR))
        fatal("reading frame %u of %s", w->frame_of[pgno], w->path);
    stats.pages_read++;
    return 1;
}

/* Starts a fresh log: a new header with new salts, so frames left over
 * from an older log can never be mistaken for frames of this one. */
static void wal_restart(Pager *p)
{
    Wal *w = p->wal;
    u8 hdr[WAL_HDR];
    u32 r = (u32)time(NULL) ^ ((u32)getpid() << 16);
    int fd = open("/dev/urandom", O_RDONLY);
    if (fd >= 0) {
        if (read(fd, &r, sizeof r) != sizeof r)
            r ^= 0x5bd1e995;
        close(fd);
    }
    w->bigendian = 1;
    w->salt1 = w->salt1 + 1;
    w->salt2 = r;
    put4(hdr, WAL_MAGIC | 1);
    put4(hdr + 4, WAL_VERSION);
    put4(hdr + 8, p->page_size);
    put4(hdr + 12, w->ckpt_seq);
    put4(hdr + 16, w->salt1);
    put4(hdr + 20, w->salt2);
    u32 s0 = 0, s1 = 0;
    wal_checksum(1, hdr, 24, &s0, &s1);
    put4(hdr + 24, s0);
    put4(hdr + 28, s1);
    must_pwrite(w->fd, hdr, WAL_HDR, 0, w->path);
    w->s0 = s0;
    w->s1 = s1;
    index_clear(w);
}

/* Commits the dirty pages (sorted by page number) by appending them to
 * the log. Returns 0; an I/O error is fatal.
 *
 * Each page becomes one frame after the last committed one. The last
 * frame carries the database size in pages, which is what marks the
 * transaction committed. The log is fsynced first, and only then does
 * the in-memory index learn of the frames, so a reader never sees a
 * commit that a crash could take back. A new log's directory entry is
 * synced too. */
int wal_commit(Pager *p, Page **pages, u32 n)
{
    Wal *w = p->wal;
    int fresh = 0;
    if (w->nframes == 0) {
        wal_restart(p);
        fresh = 1;
    }
    // @build 06.04 append a commit
    size_t flen = FRAME_HDR + p->page_size;
    u8 *f = xmalloc(flen);
    u32 s0 = w->s0, s1 = w->s1;
    for (u32 i = 0; i < n; i++) {
        put4(f, pages[i]->pgno);
        put4(f + 4, i == n - 1 ? p->npages : 0);
        put4(f + 8, w->salt1);
        put4(f + 12, w->salt2);
        wal_checksum(w->bigendian, f, 8, &s0, &s1);
        wal_checksum(w->bigendian, pages[i]->data, p->page_size, &s0, &s1);
        put4(f + 16, s0);
        put4(f + 20, s1);
        memcpy(f + FRAME_HDR, pages[i]->data, p->page_size);
        off_t off = frame_offset(p, w->nframes + 1 + i);
        /* A torn frame: with wal-torn armed, only half of the commit
         * frame reaches the log before the crash. */
        if (i == n - 1 && crash_armed("wal-torn")) {
            must_pwrite(w->fd, f, flen / 2, off, w->path);
            crash_point("wal-torn");
        }
        must_pwrite(w->fd, f, flen, off, w->path);
        if (i + 1 == (n + 1) / 2 && n > 1)
            crash_point("wal-partial");
    }
    free(f);
    crash_point("wal-written");
    if (sys_fsync(w->fd) < 0)
        fatal("fsync %s: %s", w->path, strerror(errno));
    if (fresh)
        fsync_dir(w->path);
    for (u32 i = 0; i < n; i++)
        index_set(w, pages[i]->pgno, w->nframes + 1 + i);
    w->nframes += n;
    w->db_size = p->npages;
    w->s0 = s0;
    w->s1 = s1;
    stats.wal_frames += n;
    return 0;
    // @end
}

/* Copies the newest version of every page in the log into the database
 * file, makes that durable, and empties the log. Returns 0.
 *
 * The log is emptied only after the database file is synced. A crash
 * before that is harmless: the next open replays the same frames into
 * the same places. */
int wal_checkpoint(Pager *p)
{
    Wal *w = p->wal;
    if (!w || w->nframes == 0)
        return 0;
    // @build 06.04 checkpoint
    u8 *buf = xmalloc(p->page_size);
    int copied = 0;
    for (u32 pgno = 1; pgno < w->frame_of_cap; pgno++) {
        if (w->frame_of[pgno] == 0)
            continue;
        wal_read(p, pgno, buf);
        write_page(p, pgno, buf);
        if (++copied == 1)
            crash_point("checkpoint-partial");
    }
    free(buf);
    if (sys_fsync(p->fd) < 0)
        fatal("fsync %s: %s", p->path, strerror(errno));
    if (ftruncate(p->fd, (off_t)w->db_size * p->page_size) < 0)
        fatal("truncating %s: %s", p->path, strerror(errno));
    crash_point("checkpoint-done");
    if (ftruncate(w->fd, 0) < 0)
        fatal("truncating %s: %s", w->path, strerror(errno));
    sys_fsync(w->fd);
    index_clear(w);
    w->ckpt_seq++;
    stats.checkpoints++;
    return 0;
    // @end
}

/* Closes the log. With checkpoint, first moves everything into the
 * database file and deletes the log, as sqlite3's last connection does. */
void wal_close(Pager *p, int checkpoint)
{
    Wal *w = p->wal;
    if (!w)
        return;
    if (checkpoint) {
        wal_checkpoint(p);
        unlink(w->path);
    }
    close(w->fd);
    free(w->frame_of);
    free(w->path);
    free(w);
    p->wal = NULL;
}
