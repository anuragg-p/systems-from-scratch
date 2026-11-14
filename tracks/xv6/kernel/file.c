// Open files.
//
// A file descriptor in a process is an index into p->ofile[], which
// points at a struct file in the one system-wide table here. A struct
// file is "an open file": it remembers the offset and whether reads and
// writes are allowed, and hides whether the thing underneath is an inode,
// a pipe, or a device like the console.

#include "kernel/types.h"
#include "kernel/riscv.h"
#include "kernel/defs.h"
#include "kernel/param.h"
#include "kernel/fs.h"
#include "kernel/spinlock.h"
#include "kernel/sleeplock.h"
#include "kernel/file.h"
#include "kernel/stat.h"
#include "kernel/proc.h"

struct devsw devsw[NDEV];
struct {
  struct spinlock lock;
  struct file file[NFILE];
} ftable;

void
fileinit(void)
{
  initlock(&ftable.lock, "ftable");
}

// Allocate a file structure.
struct file*
filealloc(void)
{
  // @build 05.07 filealloc
  // Find a struct file with ref 0 in ftable, set ref to 1 and return it,
  // all under ftable.lock. Return 0 if the table is full.
  struct file *f;

  acquire(&ftable.lock);
  for(f = ftable.file; f < ftable.file + NFILE; f++){
    if(f->ref == 0){
      f->ref = 1;
      release(&ftable.lock);
      return f;
    }
  }
  release(&ftable.lock);
  return 0;
  // @end
}

// Increment ref count for file f.
struct file*
filedup(struct file *f)
{
  // @build 05.07 filedup
  // One more reference to f, under ftable.lock. Panic if ref < 1.
  acquire(&ftable.lock);
  if(f->ref < 1)
    panic("filedup");
  f->ref++;
  release(&ftable.lock);
  return f;
  // @end
}

// @from 08.04
// Close a socket's file (module 08): drop a reference as fileclose()
// does, and close the socket with the last one. Sockets take this path
// so that fileclose() below need not know about them.
static void
fileclose_sock(struct file *f)
{
  struct sock *so;

  acquire(&ftable.lock);
  if(f->ref < 1)
    panic("fileclose");
  if(--f->ref > 0){
    release(&ftable.lock);
    return;
  }
  so = f->sock;
  f->ref = 0;
  f->type = FD_NONE;
  f->sock = 0;
  release(&ftable.lock);
  sockclose(so);
}
// @end

// Close file f.  (Decrement ref count, close when reaches 0.)
void
fileclose(struct file *f)
{
  // @from 08.04
  if(f->type == FD_SOCK){
    fileclose_sock(f);
    return;
  }
  // @end

  // @build 05.07 fileclose
  // Drop a reference, under ftable.lock. When the last one goes: copy the
  // struct, mark the slot free (ref 0, FD_NONE), release the lock, and only
  // then close what is underneath - pipeclose for a pipe, iput (inside a
  // transaction) for an inode or device.
  struct file ff;

  acquire(&ftable.lock);
  if(f->ref < 1)
    panic("fileclose");
  if(--f->ref > 0){
    release(&ftable.lock);
    return;
  }
  ff = *f;
  f->ref = 0;
  f->type = FD_NONE;
  release(&ftable.lock);

  // @from 06.06
  if(ff.type == FD_PIPE){
    pipeclose(ff.pipe, ff.writable);
  } else if(ff.type == FD_INODE || ff.type == FD_DEVICE){
  // @else
  // if(ff.type == FD_INODE || ff.type == FD_DEVICE){
  // @end
    begin_op();
    iput(ff.ip);
    end_op();
  }
  // @end
}

// Get metadata about file f.
// addr is a user virtual address, pointing to a struct stat.
int
filestat(struct file *f, uint64 addr)
{
  struct proc *p = myproc();
  struct stat st;

  if(f->type == FD_INODE || f->type == FD_DEVICE){
    memset(&st, 0, sizeof(st));   // its padding would carry kernel stack bytes
    ilock(f->ip);
    stati(f->ip, &st);
    iunlock(f->ip);
    if(copyout(p->pagetable, addr, (char *)&st, sizeof(st)) < 0)
      return -1;
    return 0;
  }
  return -1;
}

// Read from file f.
// addr is a user virtual address.
int
fileread(struct file *f, uint64 addr, int n)
{
  int r = 0;

  if(f->readable == 0 || n < 0)
    return -1;

  // @from 06.06
  if(f->type == FD_PIPE){
    r = piperead(f->pipe, addr, n);
  } else if(f->type == FD_DEVICE){
  // @else
  // if(f->type == FD_DEVICE){
  // @end
    if(f->major < 0 || f->major >= NDEV || !devsw[f->major].read)
      return -1;
    r = devsw[f->major].read(1, addr, n);
  } else if(f->type == FD_INODE){
    ilock(f->ip);
    if((r = readi(f->ip, 1, addr, f->off, n)) > 0)
      f->off += r;
    iunlock(f->ip);
  // @from 08.04
  } else if(f->type == FD_SOCK){
    // read() on a socket takes one datagram; recvfrom() also says who sent it.
    r = sockrecv(f->sock, addr, n, 0, 0);
  // @end
  } else {
    panic("fileread");
  }

  return r;
}

// Write to file f.
// addr is a user virtual address.
int
filewrite(struct file *f, uint64 addr, int n)
{
  int r, ret = 0;

  if(f->writable == 0 || n < 0)
    return -1;

  // @from 06.06
  if(f->type == FD_PIPE){
    ret = pipewrite(f->pipe, addr, n);
  } else if(f->type == FD_DEVICE){
  // @else
  // if(f->type == FD_DEVICE){
  // @end
    if(f->major < 0 || f->major >= NDEV || !devsw[f->major].write)
      return -1;
    ret = devsw[f->major].write(1, addr, n);
  } else if(f->type == FD_INODE){
    // write a few blocks at a time to avoid exceeding
    // the maximum log transaction size, including
    // i-node, indirect block, allocation blocks,
    // and 2 blocks of slop for non-aligned writes.
    int max = ((MAXOPBLOCKS-1-1-2) / 2) * BSIZE;
    int i = 0;
    while(i < n){
      int n1 = n - i;
      if(n1 > max)
        n1 = max;

      begin_op();
      ilock(f->ip);
      if ((r = writei(f->ip, 1, addr + i, f->off, n1)) > 0)
        f->off += r;
      iunlock(f->ip);
      end_op();

      if(r != n1){
        // error from writei
        break;
      }
      i += r;
    }
    ret = (i == n ? n : -1);
  } else {
    panic("filewrite");
  }

  return ret;
}
