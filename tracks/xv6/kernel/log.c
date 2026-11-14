// The write-ahead log.
//
// Creating a file touches several blocks: the inode, the directory, the
// free bitmap. A crash between those writes would leave the disk
// inconsistent. The log makes a group of writes atomic: they are first
// written to a log area on disk, then a header block naming them is
// written (the commit point), and only then are they copied to their
// real locations. After a crash, recovery either finds a committed
// header and replays the copies, or finds none and ignores the log.
//
// A file-system operation brackets its writes:
//   begin_op();
//   ...
//   bp = bread(...);
//   bp->data[...] = ...;
//   log_write(bp);
//   ...
//   end_op();
//
// Log appends are synchronous, and several operations can share one
// transaction (group commit): the log commits when the last of them
// calls end_op.
//
// The on-disk log format:
//   header block, containing block #s for block A, B, C, ...
//   block A
//   block B
//   block C
//   ...

#include "kernel/types.h"
#include "kernel/riscv.h"
#include "kernel/defs.h"
#include "kernel/param.h"
#include "kernel/spinlock.h"
#include "kernel/sleeplock.h"
#include "kernel/fs.h"
#include "kernel/buf.h"

// Contents of the header block, used for both the on-disk header block
// and to keep track in memory of logged block# before commit.
struct logheader {
  int n;
  int block[LOGBLOCKS];
};

struct log {
  struct spinlock lock;
  int start;
  int outstanding; // how many FS operations are executing.
  int committing;  // in commit(), please wait.
  int dev;
  struct logheader lh;
};
struct log log;

// How many blocks recovery replayed at boot.
int log_recovered;

static void recover_from_log(void);
static void commit(void);

void
initlog(int dev, struct superblock *sb)
{
  if (sizeof(struct logheader) >= BSIZE)
    panic("initlog: too big logheader");

  initlock(&log.lock, "log");
  log.start = sb->logstart;
  log.dev = dev;
  recover_from_log();
}

// Copy committed blocks from log to their home location
static void
install_trans(int recovering)
{
  int tail;

  for (tail = 0; tail < log.lh.n; tail++) {
    struct buf *lbuf = bread(log.dev, log.start+tail+1); // read log block
    struct buf *dbuf = bread(log.dev, log.lh.block[tail]); // read dst
    memmove(dbuf->data, lbuf->data, BSIZE);  // copy block to dst
    bwrite(dbuf);  // write dst to disk
    if(recovering == 0)
      bunpin(dbuf);
    brelse(lbuf);
    brelse(dbuf);
  }
}

// Read the log header from disk into the in-memory log header
static void
read_head(void)
{
  struct buf *buf = bread(log.dev, log.start);
  struct logheader *lh = (struct logheader *) (buf->data);
  int i;
  log.lh.n = lh->n;
  for (i = 0; i < log.lh.n; i++) {
    log.lh.block[i] = lh->block[i];
  }
  brelse(buf);
}

// Write in-memory log header to disk.
// This is the true point at which the
// current transaction commits.
static void
write_head(void)
{
  struct buf *buf = bread(log.dev, log.start);
  struct logheader *hb = (struct logheader *) (buf->data);
  int i;
  hb->n = log.lh.n;
  for (i = 0; i < log.lh.n; i++) {
    hb->block[i] = log.lh.block[i];
  }
  bwrite(buf);
  brelse(buf);
}

static void
recover_from_log(void)
{
  // @build 05.04 recover_from_log
  // At boot: read_head(). If the header lists blocks, a transaction
  // committed but may not be installed - install_trans(1) copies them home.
  // Record how many in log_recovered. Then empty the log: n = 0,
  // write_head().
  read_head();
  log_recovered = log.lh.n;
  install_trans(1); // if committed, copy from log to disk
  log.lh.n = 0;
  write_head(); // clear the log
  // @end
}

// called at the start of each FS operation.
void
begin_op(void)
{
  acquire(&log.lock);
  while(1){
    if(log.committing){
      sleep(&log, &log.lock);
    } else if(log.lh.n + (log.outstanding+1)*MAXOPBLOCKS > LOGBLOCKS){
      // this op might exhaust log space; wait for commit.
      sleep(&log, &log.lock);
    } else {
      log.outstanding += 1;
      release(&log.lock);
      break;
    }
  }
}

// called at the end of each FS operation.
// commits if this was the last outstanding operation.
void
end_op(void)
{
  int do_commit = 0;

  acquire(&log.lock);
  log.outstanding -= 1;
  if(log.committing)
    panic("log.committing");
  if(log.outstanding == 0){
    do_commit = 1;
    log.committing = 1;
  } else {
    // begin_op() may be waiting for log space,
    // and decrementing log.outstanding has decreased
    // the amount of reserved space.
    wakeup(&log);
  }
  release(&log.lock);

  if(do_commit){
    // call commit w/o holding locks, since not allowed
    // to sleep with locks.
    commit();
    acquire(&log.lock);
    log.committing = 0;
    wakeup(&log);
    release(&log.lock);
  }
}

// Copy modified blocks from cache to log.
static void
write_log(void)
{
  int tail;

  for (tail = 0; tail < log.lh.n; tail++) {
    struct buf *to = bread(log.dev, log.start+tail+1); // log block
    struct buf *from = bread(log.dev, log.lh.block[tail]); // cache block
    memmove(to->data, from->data, BSIZE);
    bwrite(to);  // write the log
    brelse(from);
    brelse(to);
  }
}

static void
commit(void)
{
  // @build 05.04 commit
  // If this transaction wrote anything: copy the blocks into the log
  // (write_log), write the header (write_head) - that one write is the
  // commit point - copy the blocks home (install_trans(0)), then empty the
  // log (n = 0, write_head()). Keep the two selftest_log_crashpoint() calls
  // just before and just after the commit point.
  if (log.lh.n > 0) {
    write_log();     // Write modified blocks from cache to log
    // @internal
#ifdef SELFTEST
    selftest_log_crashpoint(1);  // 05.04: crash before the commit point
#endif
    // @end
    write_head();    // Write header to disk -- the real commit
    // @internal
#ifdef SELFTEST
    selftest_log_crashpoint(2);  // 05.04: crash after the commit point
#endif
    // @end
    install_trans(0); // Now install writes to home locations
    log.lh.n = 0;
    write_head();    // Erase the transaction from the log
  }
  // @end
}

// Caller has modified b->data and is done with the buffer.
// Record the block number and pin in the cache by increasing refcnt.
// commit()/write_log() will do the disk write.
//
// log_write() replaces bwrite(); a typical use is:
//   bp = bread(...)
//   modify bp->data[]
//   log_write(bp)
//   brelse(bp)
void
log_write(struct buf *b)
{
  // @build 05.04 log_write
  // Use instead of bwrite(): remember that b belongs to this transaction.
  // Under log.lock, panic if the log is full or no operation is open. If
  // b's block number is already in log.lh.block (absorption), do nothing
  // more; else append it, pin b in the cache (bpin), and grow log.lh.n.
  int i;

  acquire(&log.lock);
  if (log.lh.n >= LOGBLOCKS)
    panic("too big a transaction");
  if (log.outstanding < 1)
    panic("log_write outside of trans");

  for (i = 0; i < log.lh.n; i++) {
    if (log.lh.block[i] == b->blockno)   // log absorption
      break;
  }
  log.lh.block[i] = b->blockno;
  if (i == log.lh.n) {  // Add new block to log?
    bpin(b);
    log.lh.n++;
  }
  release(&log.lock);
  // @end
}
