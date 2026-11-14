// @from 04.01
// Processes and scheduling.
//
// A process is: a kernel stack, a saved register context, a user page
// table and memory, a trapframe, and some bookkeeping - one slot in the
// fixed-size proc[] table.
// @from 04.02
// The scheduler on each hart loops over that table looking for RUNNABLE
// processes and swtch()es into them.
// @end
// @else
// // The CPUs: one struct cpu per hart, and how a hart finds its own.
// @end

#include "kernel/types.h"
#include "kernel/param.h"
#include "kernel/memlayout.h"
#include "kernel/riscv.h"
#include "kernel/spinlock.h"
#include "kernel/proc.h"
#include "kernel/defs.h"

struct cpu cpus[NCPU];

// @from 04.01
struct proc proc[NPROC];

struct proc *initproc;

int nextpid = 1;
struct spinlock pid_lock;

extern void forkret(void);
static void freeproc(struct proc *p);

extern char trampoline[]; // trampoline.S @from 06.01

// @from 06.04
// helps ensure that wakeups of wait()ing
// parents are not lost. helps obey the
// memory model when using p->parent.
// must be acquired before any p->lock.
// @else
// // guards p->parent in every process.
// // must be acquired before any p->lock.
// @end
struct spinlock wait_lock;

// Allocate a page for each process's kernel stack.
// Map it high in memory, followed by an invalid
// guard page.
void
proc_mapstacks(pagetable_t kpgtbl)
{
  struct proc *p;

  for(p = proc; p < &proc[NPROC]; p++) {
    char *pa = kalloc();
    if(pa == 0)
      panic("kalloc");
    uint64 va = KSTACK((int) (p - proc));
    kvmmap(kpgtbl, va, (uint64)pa, PGSIZE, PTE_R | PTE_W);
  }
}

// initialize the proc table.
void
procinit(void)
{
  struct proc *p;

  initlock(&pid_lock, "nextpid");
  initlock(&wait_lock, "wait_lock");
  for(p = proc; p < &proc[NPROC]; p++) {
      initlock(&p->lock, "proc");
      p->state = UNUSED;
      p->kstack = KSTACK((int) (p - proc));
  }
}
// @end

// The hartid of this CPU, which start() left in tp.
// @from 04.04
// Must be called with interrupts disabled,
// to prevent race with process being moved
// to a different CPU.
// @end
int
cpuid(void)
{
  int id = r_tp();
  return id;
}

// Return this CPU's cpu struct.
// Interrupts must be disabled.
struct cpu*
mycpu(void)
{
  int id = cpuid();
  struct cpu *c = &cpus[id];
  return c;
}

// @from 04.01
// Return the current struct proc *, or zero if none.
struct proc*
myproc(void)
{
  push_off();
  struct cpu *c = mycpu();
  struct proc *p = c->proc;
  pop_off();
  return p;
}

int
allocpid(void)
{
  int pid;

  acquire(&pid_lock);
  pid = nextpid;
  nextpid = nextpid + 1;
  release(&pid_lock);

  return pid;
}
// @end

// Look in the process table for an UNUSED proc.
// If found, initialize state required to run in the kernel,
// and return with p->lock held.
// If there are no free procs, or a memory allocation fails, return 0.
static struct proc*
allocproc(void)
{
  struct proc *p;

  for(p = proc; p < &proc[NPROC]; p++) {
    acquire(&p->lock);
    if(p->state == UNUSED) {
      goto found;
    } else {
      release(&p->lock);
    }
  }
  return 0;

found:
  // @build 04.01 allocproc
  // Claim the slot you found (you hold its lock): give it a pid
  // (allocpid) and state USED, a trapframe page, and a user page table
  // (proc_pagetable). If either allocation fails, freeproc, release the
  // lock and return 0. Then set up its context so the first swtch() into
  // it starts forkret() on the top of its own kernel stack: context.ra =
  // forkret, context.sp = kstack + PGSIZE. Return p, still locked.
  p->pid = allocpid();
  p->state = USED;

  // Allocate a trapframe page.
  if((p->trapframe = (struct trapframe *)kalloc()) == 0){
    freeproc(p);
    release(&p->lock);
    return 0;
  }

  // An empty user page table.
  p->pagetable = proc_pagetable(p);
  if(p->pagetable == 0){
    freeproc(p);
    release(&p->lock);
    return 0;
  }

  // Set up new context to start executing at forkret,
  // on the top of the process's own kernel stack.
  memset(&p->context, 0, sizeof(p->context));
  p->context.ra = (uint64)forkret;
  p->context.sp = p->kstack + PGSIZE;

  return p;
  // @end
}

// free a proc structure and the data hanging from it,
// including user pages.
// p->lock must be held.
static void
freeproc(struct proc *p)
{
  // @build 04.01 freeproc
  // Give a slot back: free its trapframe page and its user page table
  // (proc_freepagetable, with p->sz), zero every field that describes the
  // old process, and set the state to UNUSED. Caller holds p->lock.
  if(p->trapframe)
    kfree((void*)p->trapframe);
  p->trapframe = 0;
  if(p->pagetable)
    proc_freepagetable(p->pagetable, p->sz);
  p->pagetable = 0;
  p->sz = 0;
  p->pid = 0;
  p->parent = 0;
  p->name[0] = 0;
  p->chan = 0;
  p->killed = 0;
  p->xstate = 0;
  // @internal
  p->kfn = 0;
  p->karg = 0;
  // @end
  p->state = UNUSED;
  // @end
}

// Create a user page table for a given process, with no user memory,
// but with the pages the kernel keeps at the top of every process's
// address space.
pagetable_t
proc_pagetable(struct proc *p)
{
  // @build 04.01 proc_pagetable
  // A new process's page table, with no user memory yet - only two pages
  // at the very top, neither user accessible: the trampoline at TRAMPOLINE
  // (read/execute) and this process's trapframe at TRAPFRAME (read/write).
  // On any failure, free what you made and return 0.
  pagetable_t pagetable;

  // An empty page table.
  pagetable = uvmcreate();
  if(pagetable == 0)
    return 0;

  // @from 06.01
  // map the trampoline code (for system call return)
  // at the highest user virtual address.
  // only the supervisor uses it, on the way
  // to/from user space, so not PTE_U.
  if(mappages(pagetable, TRAMPOLINE, PGSIZE,
              (uint64)trampoline, PTE_R | PTE_X) < 0){
    uvmfree(pagetable, 0);
    return 0;
  }
  // @end

  // map the trapframe page at TRAPFRAME, just below TRAMPOLINE.
  if(mappages(pagetable, TRAPFRAME, PGSIZE,
              (uint64)(p->trapframe), PTE_R | PTE_W) < 0){
    uvmunmap(pagetable, TRAMPOLINE, 1, 0);  // @from 06.01
    uvmfree(pagetable, 0);
    return 0;
  }

  return pagetable;
  // @end
}

// @from 04.01
// Free a process's page table, and free the
// physical memory it refers to.
void
proc_freepagetable(pagetable_t pagetable, uint64 sz)
{
  uvmunmap(pagetable, TRAMPOLINE, 1, 0);  // @from 06.01
  uvmunmap(pagetable, TRAPFRAME, 1, 0);
  fbunmap(pagetable);   // the screen, if this process mapped it (module 09) @from 09.02
  uvmfree(pagetable, sz);
}
// @end

// @internal
// Kernel threads (not in the original xv6). A kernel thread is a process
// with no user half: its first swtch() lands in kthread_start(), which
// calls fn(arg) on the process's kernel stack and exits when fn returns.
static void
kthread_start(void)
{
  struct proc *p = myproc();

  // Still holding p->lock from scheduler.
  release(&p->lock);
  // Kernel threads run with interrupts on, so the timer can preempt them.
  intr_on();

  p->kfn(p->karg);
  kexit(0);
}

// Start fn(arg) in a new kernel thread whose parent is the caller.
// Returns the new pid, or -1.
int
kthread(char *name, void (*fn)(void*), void *arg)
{
  struct proc *np;

  if((np = allocproc()) == 0)
    return -1;
  np->context.ra = (uint64)kthread_start;
  np->kfn = fn;
  np->karg = arg;
  safestrcpy(np->name, name, sizeof(np->name));
  int pid = np->pid;
  release(&np->lock);

  acquire(&wait_lock);
  np->parent = myproc();
  release(&wait_lock);

  acquire(&np->lock);
  np->state = RUNNABLE;
  release(&np->lock);

  return pid;
}
// @end

// @from 06.01
// Pass p's abandoned children to init.
// Caller must hold wait_lock.
void
reparent(struct proc *p)
{
  struct proc *pp;

  for(pp = proc; pp < &proc[NPROC]; pp++){
    if(pp->parent == p){
      pp->parent = initproc;
      wakeup(initproc);
    }
  }
}

// Exit the current process.  Does not return.
// @from 06.04
// An exited process remains in the zombie state
// until its parent calls wait().
// @end
void
kexit(int status)
{
  struct proc *p = myproc();

  if(p == initproc)
    panic("init exiting");

  // Close all open files.
  for(int fd = 0; fd < NOFILE; fd++){
    if(p->ofile[fd]){
      struct file *f = p->ofile[fd];
      fileclose(f);
      p->ofile[fd] = 0;
    }
  }

  if(p->cwd){
    begin_op();
    iput(p->cwd);
    end_op();
    p->cwd = 0;
  }

  acquire(&wait_lock);

  // Give any children to init.
  reparent(p);

  // @from 06.04
  // Parent might be sleeping in wait().
  // @end
  wakeup(p->parent);

  acquire(&p->lock);

  p->xstate = status;
  p->state = ZOMBIE;

  release(&wait_lock);

  // Jump into the scheduler, never to return.
  sched();
  panic("zombie exit");
}
// @end

// @from 06.04
// Wait for a child process to exit and return its pid.
// Return -1 if this process has no children.
// addr is a user address for the exit status, or 0.
int
kwait(uint64 addr)
{
  struct proc *pp;
  int havekids, pid;
  struct proc *p = myproc();

  acquire(&wait_lock);

  for(;;){
    // Scan through table looking for exited children.
    havekids = 0;
    for(pp = proc; pp < &proc[NPROC]; pp++){
      if(pp->parent == p){
        // make sure the child isn't still in exit() or swtch().
        acquire(&pp->lock);

        havekids = 1;
        if(pp->state == ZOMBIE){
          // Found one.
          pid = pp->pid;
          if(addr != 0 && copyout(p->pagetable, addr, (char *)&pp->xstate,
                                  sizeof(pp->xstate)) < 0) {
            release(&pp->lock);
            release(&wait_lock);
            return -1;
          }
          freeproc(pp);
          release(&pp->lock);
          release(&wait_lock);
          return pid;
        }
        release(&pp->lock);
      }
    }

    // No point waiting if we don't have any children.
    if(!havekids || killed(p)){
      release(&wait_lock);
      return -1;
    }

    // Wait for a child to exit.
    sleep(p, &wait_lock);
  }
}
// @end

// Per-CPU process scheduler.
// Each CPU calls scheduler() after setting itself up.
// Scheduler never returns.  It loops, doing:
//  - choose a process to run.
//  - swtch to start running that process.
//  - eventually that process transfers control
//    via swtch back to the scheduler.
void
scheduler(void)
{
  // @build 04.02 scheduler
  // Each hart loops forever: briefly turn interrupts on and off again (a
  // device may be waiting), then walk proc[]. For each RUNNABLE process,
  // under its lock: mark it RUNNING, set c->proc, and swtch() from this
  // hart's c->context into the process. When swtch() comes back the
  // process has given the hart up; clear c->proc. If a whole pass found
  // nothing to run, wait for an interrupt with wfi.
  struct proc *p;
  struct cpu *c = mycpu();

  c->proc = 0;
  for(;;){
    // The most recent process to run may have had interrupts
    // turned off; enable them to avoid a deadlock if all
    // processes are waiting. Then turn them back off
    // to avoid a possible race between an interrupt
    // and wfi.
    intr_on();
    intr_off();

    int found = 0;
    for(p = proc; p < &proc[NPROC]; p++) {
      acquire(&p->lock);
      if(p->state == RUNNABLE) {
        // Switch to chosen process.  It is the process's job
        // to release its lock and then reacquire it
        // before jumping back to us.
        p->state = RUNNING;
        c->proc = p;
        swtch(&c->context, &p->context);

        // Process is done running for now.
        // It should have changed its p->state before coming back.
        c->proc = 0;
        found = 1;
      }
      release(&p->lock);
    }
    if(found == 0) {
      // nothing to run; stop running on this core until an interrupt.
      asm volatile("wfi");
    }
  }
  // @end
}

// Switch to scheduler.  Must hold only p->lock
// and have changed proc->state. Saves and restores
// intena because intena is a property of this
// kernel thread, not this CPU. It should
// be proc->intena and proc->noff, but that would
// break in the few places where a lock is held but
// there's no process.
void
sched(void)
{
  // @build 04.02 sched
  // Switch from the current process into this hart's scheduler. Check the
  // rules first and panic if one is broken: holding p->lock, holding no
  // other lock (noff == 1), state already changed from RUNNING, interrupts
  // off. intena belongs to this process, not the hart: save it, swtch(),
  // restore it.
  int intena;
  struct proc *p = myproc();

  if(!holding(&p->lock))
    panic("sched p->lock");
  if(mycpu()->noff != 1)
    panic("sched locks");
  if(p->state == RUNNING)
    panic("sched RUNNING");
  if(intr_get())
    panic("sched interruptible");

  intena = mycpu()->intena;
  swtch(&p->context, &mycpu()->context);
  mycpu()->intena = intena;
  // @end
}

// Give up the CPU for one scheduling round.
void
yield(void)
{
  // @build 04.02 yield
  // Give up the hart for one round: under p->lock, set the state to
  // RUNNABLE and sched().
  struct proc *p = myproc();
  acquire(&p->lock);
  p->state = RUNNABLE;
  sched();
  release(&p->lock);
  // @end
}

// @from 04.01
// Where a new process first runs, the first time it is scheduled:
// allocproc() pointed its context here.
void
forkret(void)
{
  extern char userret[];  // @from 06.01
  static int first = 1;  // @from 06.03
  struct proc *p = myproc();

  // Still holding p->lock: the switch into this process was made with
  // it held.
  release(&p->lock);

  // @from 06.03
  if (first) {
    // File system initialization must be run in the context of a
    // regular process (e.g., because it calls sleep), and thus cannot
    // be run from main().
    fsinit(ROOTDEV);

    first = 0;
    // ensure other cores see first=0.
    __sync_synchronize();

    // We can invoke kexec() now that file system is initialized.
    // Put the return value (argc) of kexec into a0.
    p->trapframe->a0 = kexec("/init", (char *[]){ "/init", 0 });
    if (p->trapframe->a0 == -1) {
      panic("exec");
    }
  }
  // @end

  // @from 06.01
  // return to user space, mimicking usertrap()'s return.
  prepare_return();
  uint64 satp = MAKE_SATP(p->pagetable);
  uint64 trampoline_userret = TRAMPOLINE + (userret - trampoline);
  ((void (*)(uint64))trampoline_userret)(satp);
  // @end
}
// @end

// @from 07.02
// Set up the first user process. It has no program yet: its first
// trip through forkret() execs /init.
void
userinit(void)
{
  struct proc *p;

  p = allocproc();
  initproc = p;

  p->cwd = namei("/");

  p->state = RUNNABLE;

  release(&p->lock);
}
// @end

// Grow or shrink user memory by n bytes.
// Return 0 on success, -1 on failure.
int
growproc(int n)
{
  // @build 06.05 growproc
  // Change p->sz by n. Growing: refuse to reach TRAPFRAME, then
  // uvmalloc the new pages writable (PTE_W). Shrinking: uvmdealloc.
  // Return -1 if allocation fails, else 0 with p->sz updated.
  uint64 sz;
  struct proc *p = myproc();

  sz = p->sz;
  if(n > 0){
    if(sz + n > TRAPFRAME)
      return -1;
    if((sz = uvmalloc(p->pagetable, sz, sz + n, PTE_W)) == 0) {
      return -1;
    }
  } else if(n < 0){
    sz = uvmdealloc(p->pagetable, sz, sz + n);
  }
  p->sz = sz;
  return 0;
  // @end
}

// Create a new process, copying the parent.
// Sets up child kernel stack to return as if from fork() system call.
int
kfork(void)
{
  // @build 06.04 kfork
  // Make a child that is a copy of the caller. allocproc() a slot; copy
  // the parent's user memory with uvmcopy (on failure freeproc and
  // return -1); copy sz and the whole trapframe, but set the child's a0
  // to 0 - that is why fork() returns 0 in the child. Share open files
  // (filedup) and the cwd (idup), copy the name. Set the parent (under
  // wait_lock) and only then make the child RUNNABLE. Return its pid.
  int i, pid;
  struct proc *np;
  struct proc *p = myproc();

  // Allocate process.
  if((np = allocproc()) == 0){
    return -1;
  }

  // Copy user memory from parent to child.
  if(uvmcopy(p->pagetable, np->pagetable, p->sz) < 0){
    freeproc(np);
    release(&np->lock);
    return -1;
  }
  np->sz = p->sz;

  // copy saved user registers.
  *(np->trapframe) = *(p->trapframe);

  // Cause fork to return 0 in the child.
  np->trapframe->a0 = 0;

  // increment reference counts on open file descriptors.
  for(i = 0; i < NOFILE; i++)
    if(p->ofile[i])
      np->ofile[i] = filedup(p->ofile[i]);
  np->cwd = idup(p->cwd);

  safestrcpy(np->name, p->name, sizeof(p->name));

  pid = np->pid;

  release(&np->lock);

  acquire(&wait_lock);
  np->parent = p;
  release(&wait_lock);

  acquire(&np->lock);
  np->state = RUNNABLE;
  release(&np->lock);

  return pid;
  // @end
}

// Sleep on channel chan, releasing condition lock lk.
// Re-acquires lk when awakened.
void
sleep(void *chan, struct spinlock *lk)
{
  // @build 04.03 sleep
  // Sleep on chan, giving up lk while asleep. Take p->lock before letting
  // go of lk: wakeup() also needs p->lock, so no wakeup can slip in between
  // "I am about to sleep" and "I am asleep" (the lost wakeup). Record chan,
  // set SLEEPING, sched(). When woken: clear chan, release p->lock, take lk
  // back.
  struct proc *p = myproc();

  // Must acquire p->lock in order to
  // change p->state and then call sched.
  // Once we hold p->lock, we can be
  // guaranteed that we won't miss any wakeup
  // (wakeup locks p->lock),
  // so it's okay to release lk.

  acquire(&p->lock);
  release(lk);

  // Go to sleep.
  p->chan = chan;
  p->state = SLEEPING;

  sched();

  // Tidy up.
  p->chan = 0;

  // Reacquire original lock.
  release(&p->lock);
  acquire(lk);
  // @end
}

// Wake up all processes sleeping on channel chan.
// Caller should hold the condition lock.
void
wakeup(void *chan)
{
  // @build 04.03 wakeup
  // Make every process SLEEPING on chan RUNNABLE. Check each one under its
  // own lock, and skip the caller.
  struct proc *p;

  for(p = proc; p < &proc[NPROC]; p++) {
    if(p != myproc()){
      acquire(&p->lock);
      if(p->state == SLEEPING && p->chan == chan) {
        p->state = RUNNABLE;
      }
      release(&p->lock);
    }
  }
  // @end
}

// @from 06.04
// Kill the process with the given pid.
// The victim won't exit until it tries to return
// to user space (see usertrap() in trap.c).
int
kkill(int pid)
{
  struct proc *p;

  if(pid == 0)       // every unused slot has pid 0
    return -1;

  for(p = proc; p < &proc[NPROC]; p++){
    acquire(&p->lock);
    if(p->pid == pid){
      p->killed = 1;
      if(p->state == SLEEPING){
        // Wake process from sleep().
        p->state = RUNNABLE;
      }
      release(&p->lock);
      return 0;
    }
    release(&p->lock);
  }
  return -1;
}
// @end

// @from 05.07
void
setkilled(struct proc *p)
{
  acquire(&p->lock);
  p->killed = 1;
  release(&p->lock);
}

int
killed(struct proc *p)
{
  int k;

  acquire(&p->lock);
  k = p->killed;
  release(&p->lock);
  return k;
}
// @end

// @from 05.05
// Copy to either a user address, or kernel address,
// depending on usr_dst.
// Returns 0 on success, -1 on error.
int
either_copyout(int user_dst, uint64 dst, void *src, uint64 len)
{
  struct proc *p = myproc();
  if(user_dst){
    return copyout(p->pagetable, dst, src, len);
  } else {
    memmove((char *)dst, src, len);
    return 0;
  }
}

// Copy from either a user address, or kernel address,
// depending on usr_src.
// Returns 0 on success, -1 on error.
int
either_copyin(void *dst, int user_src, uint64 src, uint64 len)
{
  struct proc *p = myproc();
  if(user_src){
    return copyin(p->pagetable, dst, src, len);
  } else {
    memmove(dst, (char*)src, len);
    return 0;
  }
}
// @end

// @from 04.01
// Print a process listing to console.  For debugging.
// Runs when user types ^P on console.
// No lock to avoid wedging a stuck machine further.
void
procdump(void)
{
  static char *states[] = {
  [UNUSED]    "unused",
  [USED]      "used",
  [SLEEPING]  "sleep ",
  [RUNNABLE]  "runble",
  [RUNNING]   "run   ",
  [ZOMBIE]    "zombie"
  };
  struct proc *p;
  char *state;

  printf("\n");
  for(p = proc; p < &proc[NPROC]; p++){
    if(p->state == UNUSED)
      continue;
    if(p->state >= 0 && p->state < NELEM(states) && states[p->state])
      state = states[p->state];
    else
      state = "???";
    printf("%d %s %s", p->pid, state, p->name);
    printf("\n");
  }
}
// @end
