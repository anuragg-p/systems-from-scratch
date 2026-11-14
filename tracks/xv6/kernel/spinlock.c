// Spinlocks.
//
// Three harts share one memory. When two of them update the same data
// at the same time, updates get lost. A spinlock lets only one hart into
// a critical section; the others spin until it leaves.

#include "kernel/types.h"
#include "kernel/param.h"
#include "kernel/memlayout.h"
#include "kernel/spinlock.h"
#include "kernel/riscv.h"
#include "kernel/proc.h"
#include "kernel/defs.h"

void
initlock(struct spinlock *lk, char *name)
{
  lk->name = name;
  lk->locked = 0;
  lk->cpu = 0;
}

// Acquire the lock.
// Loops (spins) until the lock is acquired.
void
acquire(struct spinlock *lk)
{
  // @build 02.03 acquire
  // Interrupts off first (push_off): an interrupt handler on this hart that
  // wanted this lock would spin forever. Panic if this hart already holds
  // lk. Spin on an atomic swap - __sync_lock_test_and_set(&lk->locked, 1) -
  // until the old value was 0. Then __sync_synchronize() so no load or
  // store of the critical section moves above this point, and record
  // mycpu() in lk->cpu.

  // Interrupts off first: if an interrupt handler on this CPU tried to
  // take a lock we already hold, it would spin forever.
  push_off();
  if(holding(lk))
    panic("acquire");

  // On RISC-V, sync_lock_test_and_set turns into an atomic swap:
  //   a5 = 1
  //   s1 = &lk->locked
  //   amoswap.w.aq a5, a5, (s1)
  // Read-old-value-and-write-1 happens as one indivisible step, so only
  // one hart can see the old value 0.
  while(__sync_lock_test_and_set(&lk->locked, 1) != 0)
    ;

  // Tell the C compiler and the processor to not move loads or stores
  // past this point, to ensure that the critical section's memory
  // references happen strictly after the lock is acquired.
  // On RISC-V, this emits a fence instruction.
  __sync_synchronize();

  // Record info about lock acquisition for holding() and debugging.
  lk->cpu = mycpu();
  // @end
}

// Release the lock.
void
release(struct spinlock *lk)
{
  // @build 02.03 release
  // Panic unless this hart holds lk. Clear lk->cpu, __sync_synchronize() so
  // every store made under the lock is visible before the lock looks free,
  // release with an atomic store (__sync_lock_release), then pop_off().
  if(!holding(lk))
    panic("release");

  lk->cpu = 0;

  // Make every store in the critical section visible before the lock
  // is seen as free.
  __sync_synchronize();

  // Release the lock: lk->locked = 0, as a release store. GCC emits a
  // fence (rw,w) and then a plain sw - see kernel.asm - which is enough:
  // the fence keeps the critical section's accesses before the store.
  __sync_lock_release(&lk->locked);

  pop_off();
  // @end
}

// Check whether this cpu is holding the lock.
// Interrupts must be off.
int
holding(struct spinlock *lk)
{
  int r;
  r = (lk->locked && lk->cpu == mycpu());
  return r;
}

// push_off/pop_off are like intr_off()/intr_on() except that they are
// matched: it takes two pop_off()s to undo two push_off()s. Also, if
// interrupts are initially off, then push_off, pop_off leaves them off.
void
push_off(void)
{
  int old = intr_get();

  // @from 04.04
  // disable interrupts to prevent an involuntary context
  // switch while using mycpu().
  // @else
  // // disable interrupts first: mycpu() is only used with them off.
  // @end
  intr_off();

  if(mycpu()->noff == 0)
    mycpu()->intena = old;
  mycpu()->noff += 1;
}

void
pop_off(void)
{
  struct cpu *c = mycpu();
  if(intr_get())
    panic("pop_off - interruptible");
  if(c->noff < 1)
    panic("pop_off");
  c->noff -= 1;
  if(c->noff == 0 && c->intena)
    intr_on();
}
