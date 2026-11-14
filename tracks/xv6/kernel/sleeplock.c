// Sleeping locks.
//
// A spinlock is the wrong tool for holding something across a disk read:
// the disk takes milliseconds, and every hart that wants the lock would
// burn those milliseconds spinning, with interrupts off. A sleep lock
// puts the waiting process to sleep instead. Only usable by a process
// (it calls sleep), so never from an interrupt handler.

#include "kernel/types.h"
#include "kernel/riscv.h"
#include "kernel/defs.h"
#include "kernel/param.h"
#include "kernel/memlayout.h"
#include "kernel/spinlock.h"
#include "kernel/proc.h"
#include "kernel/sleeplock.h"

void
initsleeplock(struct sleeplock *lk, char *name)
{
  initlock(&lk->lk, "sleep lock");
  lk->name = name;
  lk->locked = 0;
  lk->pid = 0;
}

void
acquiresleep(struct sleeplock *lk)
{
  // @build 05.02 acquiresleep
  // Like acquire(), but sleep instead of spinning: under lk->lk, sleep(lk,
  // &lk->lk) while the lock is held. Then take it and record the pid.
  acquire(&lk->lk);
  while (lk->locked) {
    sleep(lk, &lk->lk);
  }
  lk->locked = 1;
  lk->pid = myproc()->pid;
  release(&lk->lk);
  // @end
}

void
releasesleep(struct sleeplock *lk)
{
  // @build 05.02 releasesleep
  // Under lk->lk: mark the lock free, clear the pid, wakeup(lk).
  acquire(&lk->lk);
  lk->locked = 0;
  lk->pid = 0;
  wakeup(lk);
  release(&lk->lk);
  // @end
}

int
holdingsleep(struct sleeplock *lk)
{
  int r;

  acquire(&lk->lk);
  r = lk->locked && (lk->pid == myproc()->pid);
  release(&lk->lk);
  return r;
}
