// In-kernel self-tests (lesson 00.02).
//
// Only compiled into a SELFTEST=1 build (what ./learn test boots). Each
// lesson below the system-call line gets a function here that exercises
// the code it introduced and prints "[NN.LL] ok", or "[NN.LL] FAIL ..."
// for each check that does not hold. tracks/xv6/tests/NNLL_*.py wait for
// those lines.
//
// A normal build (make qemu) compiles this file to nothing but stubs.

#include "kernel/types.h"
#include "kernel/param.h"
#include "kernel/memlayout.h"
#include "kernel/riscv.h"
#include "kernel/spinlock.h"
#include "kernel/proc.h"
#include "kernel/defs.h"
#include "kernel/sleeplock.h"
#include "kernel/fs.h"
#include "kernel/buf.h"
#include "kernel/file.h"
#include "kernel/stat.h"

#ifdef SELFTEST

static char *cur;   // lesson id being checked
static int curfail; // failed checks for it

static void
st_begin(char *id)
{
  cur = id;
  curfail = 0;
}

static void
st_end(void)
{
  if(curfail == 0)
    printf("[%s] ok\n", cur);
}

#define EXPECT(c) do { \
    if(!(c)){ printf("[%s] FAIL line %d: %s\n", cur, __LINE__, #c); curfail++; } \
  } while(0)

// ---------------------------------------------------------------- 01.03

// printf has no return value worth checking; the test compares this
// exact line from the outside.
static void
t0103_printf(void)
{
  st_begin("01.03");
  printf("[01.03] printf: %d %d %u %x %lx %p %s %s %c %%\n",
         42, -7, 4000000000U, 0x2a, 0xdeadbeefcafeL, (void*)KERNBASE,
         "hello", (char*)0, 'z');
  st_end();
}

// ---------------------------------------------------------------- 02.01

extern char etext[], end[], trampoline[], stack0[];

static void
t0201_memory_map(void)
{
  st_begin("02.01");
  uint64 freepages = (PHYSTOP - PGROUNDUP((uint64)end)) / PGSIZE;
  printf("[02.01] text %p-%p, data+bss %p-%p, free RAM %p-%p (%ld pages)\n",
         (void*)KERNBASE, etext, etext, end, (void*)PGROUNDUP((uint64)end), (void*)PHYSTOP, freepages);
  EXPECT((uint64)etext > KERNBASE);
  EXPECT((uint64)etext % PGSIZE == 0);  // so text and data get different permissions
  EXPECT((uint64)end >= (uint64)etext);
  EXPECT((uint64)end < PHYSTOP);
  EXPECT((uint64)trampoline % PGSIZE == 0);
  st_end();
}

// ---------------------------------------------------------------- 02.02

static void
t0202_kalloc(void)
{
  st_begin("02.02");
  int total = (PHYSTOP - PGROUNDUP((uint64)end)) / PGSIZE;
  int before = kfreecount();
  // Boot already took some. The kernel page table alone needs 102: 1
  // root page; 3 level-1 pages (for the 1 GB regions holding devices,
  // RAM, and the trampoline); and one level-0 page per 2 MB mapped - 1
  // for UART+virtio, 32 for the 64 MB PLIC, 64 for 128 MB of RAM, 1 for
  // the trampoline and kernel stacks. Then one page per kernel stack,
  // and a few for drivers.
  EXPECT(total - before >= 1 + 3 + (1 + 32 + 64 + 1) + NPROC);

  // Take every page there is.
  struct page { struct page *next; } *list = 0;
  int n = 0, junk_ok = 1, range_ok = 1;
  for(;;){
    char *p = kalloc();
    if(p == 0)
      break;
    if(p[100] != 5)
      junk_ok = 0;
    if((uint64)p % PGSIZE != 0 || p < end || (uint64)p >= PHYSTOP)
      range_ok = 0;
    ((struct page*)p)->next = list;
    list = (struct page*)p;
    n++;
  }
  EXPECT(n == before);         // every free page, exactly once
  EXPECT(kfreecount() == 0);
  EXPECT(junk_ok);             // kalloc fills pages with 5s
  EXPECT(range_ok);            // page aligned, between end and PHYSTOP

  // Give them all back.
  char *one = (char*)list;
  while(list){
    struct page *next = list->next;
    kfree(list);
    list = next;
  }
  EXPECT(one[100] == 1);       // kfree fills pages with 1s
  EXPECT(kfreecount() == before);
  printf("[02.02] %d pages of RAM, %d used during boot, took all %d and gave them back\n",
         total, total - before, n);
  st_end();
}

// ---------------------------------------------------------------- 02.04

static pte_t
pte_of(pagetable_t pt, uint64 va)
{
  pte_t *pte = walk(pt, va, 0);
  return pte ? *pte : 0;
}

#define FLAGS(pte) ((pte) & (PTE_V|PTE_R|PTE_W|PTE_X|PTE_U))

static void
t0204_page_tables(void)
{
  st_begin("02.04");
  pte_t pte;

  // Paging is on, with our table.
  EXPECT(r_satp() == MAKE_SATP(kernel_pagetable));

  // Kernel text: readable and executable, not writable, not for users.
  pte = pte_of(kernel_pagetable, KERNBASE);
  EXPECT(FLAGS(pte) == (PTE_V|PTE_R|PTE_X));
  EXPECT(PTE2PA(pte) == KERNBASE);  // direct mapped: va == pa

  // Kernel data and free RAM: readable and writable, not executable.
  pte = pte_of(kernel_pagetable, (uint64)etext);
  EXPECT(FLAGS(pte) == (PTE_V|PTE_R|PTE_W));
  pte = pte_of(kernel_pagetable, PHYSTOP - PGSIZE);
  EXPECT(FLAGS(pte) == (PTE_V|PTE_R|PTE_W));
  EXPECT(pte_of(kernel_pagetable, PHYSTOP) == 0);

  // Devices are mapped where the hardware put them.
  pte = pte_of(kernel_pagetable, UART0);
  EXPECT(FLAGS(pte) == (PTE_V|PTE_R|PTE_W) && PTE2PA(pte) == UART0);

  // The trampoline sits at the top of the address space, not at its
  // physical address.
  pte = pte_of(kernel_pagetable, TRAMPOLINE);
  EXPECT(FLAGS(pte) == (PTE_V|PTE_R|PTE_X) && PTE2PA(pte) == (uint64)trampoline);

  // Address 0 is not mapped in the kernel.
  EXPECT((pte_of(kernel_pagetable, 0) & PTE_V) == 0);

  // Build a page table by hand. One mapping costs a root page plus one
  // page at each of the two lower levels, plus the page itself.
  int before = kfreecount();
  uint64 va = 0x12345000;
  pagetable_t pt = uvmcreate();
  char *page = kalloc();
  EXPECT(mappages(pt, va, PGSIZE, (uint64)page, PTE_R|PTE_W|PTE_U) == 0);
  EXPECT(before - kfreecount() == 4);
  EXPECT(walkaddr(pt, va) == (uint64)page);
  EXPECT(walkaddr(pt, va + PGSIZE) == 0);
  printf("[02.04] va %p -> L2[%ld] L1[%ld] L0[%ld] -> pa %p\n",
         (void*)va, PX(2, va), PX(1, va), PX(0, va), page);
  uvmunmap(pt, va, 1, 1);
  uvmfree(pt, 0);
  EXPECT(kfreecount() == before);

  // Now make the MMU use a mapping we wrote: give a physical page a
  // second, made-up virtual address in the live kernel page table,
  // write through one address, read through the other.
  uint64 alias = 0x20000000;
  page = kalloc();
  mappages(kernel_pagetable, alias, PGSIZE, (uint64)page, PTE_R|PTE_W);
  sfence_vma();
  *(volatile uint64*)alias = 0xfeedfacecafeL;
  EXPECT(*(volatile uint64*)page == 0xfeedfacecafeL);
  uvmunmap(kernel_pagetable, alias, 1, 1);
  sfence_vma();
  st_end();
}

// ---------------------------------------------------------------- 02.03

static struct spinlock st_lock;
static volatile int st_arrived, st_counted, st_badstack;
static volatile int st_harts_reported; // hart 0 has printed 01.01 and 02.03
static volatile uint64 st_locked, st_racy;
#define ROUNDS 100000

// Runs on every hart, just before the scheduler.
void
selftest_harts(void)
{
  int id = cpuid();

  // 01.01: entry.S gave this hart its own 4096-byte slice of stack0.
  uint64 sp = r_sp();
  if(!(sp > (uint64)stack0 + id*4096 && sp <= (uint64)stack0 + (id+1)*4096)){
    printf("[01.01] FAIL hart %d has sp %p outside its own stack\n", id, (void*)sp);
    st_badstack = 1;
  }

  __sync_fetch_and_add(&st_arrived, 1);
  // Wait ~0.2s (time ticks at 10 MHz) so every hart counts at once.
  uint64 t0 = r_time();
  while(r_time() - t0 < 2000000)
    ;

  for(int i = 0; i < ROUNDS; i++){
    acquire(&st_lock);
    st_locked++;
    release(&st_lock);
  }
  // The same count without the lock: load, add, store can interleave.
  for(int i = 0; i < ROUNDS; i++)
    st_racy++;

  __sync_fetch_and_add(&st_counted, 1);
  if(id != 0)
    return;
  while(st_counted < st_arrived)
    ;
  st_begin("01.01");
  EXPECT(st_badstack == 0);
  st_end();
  st_begin("02.03");
  printf("[02.03] %d harts x %d increments: with the lock %ld, without it %ld\n",
         st_arrived, ROUNDS, st_locked, st_racy);
  EXPECT(st_locked == (uint64)st_arrived * ROUNDS);
  EXPECT(st_racy <= (uint64)st_arrived * ROUNDS);
  st_end();
  __sync_synchronize();
  st_harts_reported = 1;
}

// ---------------------------------------------------------------- 03.01

void kernelvec(void);

static volatile int trap_expected;
static volatile uint64 trap_scause, trap_stval;

// kerneltrap() asks this about any exception it does not recognize.
// If a check below provoked it on purpose, record it and skip the
// faulting instruction (all of them are 4 bytes long).
int
selftest_trap(uint64 scause, uint64 stval, uint64 *sepc)
{
  if(!trap_expected || (scause >> 63))  // only exceptions, never interrupts
    return 0;
  trap_expected = 0;
  trap_scause = scause;
  trap_stval = stval;
  *sepc += 4;
  return 1;
}

// Run one instruction that should trap. norvc keeps it 4 bytes long.
#define PROVOKE(insn, ...) do {                                         \
    trap_scause = trap_stval = 0;                                       \
    trap_expected = 1;                                                  \
    asm volatile(".option push\n.option norvc\n" insn "\n.option pop" __VA_ARGS__); \
    trap_expected = 0;                                                  \
  } while(0)

static void
t0301_kernel_traps(void)
{
  st_begin("03.01");
  EXPECT(r_stvec() == (uint64)kernelvec);

  // A machine-mode register, read from supervisor mode: illegal
  // instruction. This is the proof that start()'s mret worked.
  PROVOKE("csrr t0, mstatus", ::: "t0");
  printf("[03.01] csrr mstatus from S-mode -> scause %ld (illegal instruction)\n", trap_scause);
  EXPECT(trap_scause == 2);

  // A breakpoint.
  PROVOKE("ebreak");
  printf("[03.01] ebreak -> scause %ld (breakpoint)\n", trap_scause);
  EXPECT(trap_scause == 3);

  // A load from address 0, which the kernel page table does not map.
  PROVOKE("ld t0, 0(%0)", :: "r"(0L) : "t0");
  printf("[03.01] load from %p -> scause %ld (load page fault), stval %p\n",
         (void*)0, trap_scause, (void*)trap_stval);
  EXPECT(trap_scause == 13 && trap_stval == 0);

  // A store into kernel text, which is mapped without PTE_W.
  PROVOKE("sd zero, 0(%0)", :: "r"(KERNBASE) : "memory");
  printf("[03.01] store to %p -> scause %ld (store page fault), stval %p\n",
         (void*)KERNBASE, trap_scause, (void*)trap_stval);
  EXPECT(trap_scause == 15 && trap_stval == KERNBASE);
  st_end();
}

// ---------------------------------------------------------------- 03.02

static void
t0302_timer(void)
{
  st_begin("03.02");
  EXPECT(intr_get());   // kernel threads run with interrupts on

  acquire(&tickslock);
  uint t0 = ticks;
  uint64 r0 = r_time();
  while(ticks - t0 < 5)
    sleep(&ticks, &tickslock);  // clockintr() wakes us every tick
  release(&tickslock);

  uint64 ms = (r_time() - r0) / 10000;  // time runs at 10 MHz
  printf("[03.02] waited for 5 timer ticks: %ld ms\n", ms);
  EXPECT(ms >= 350 && ms <= 1500);
  st_end();
}

// ---------------------------------------------------------------- 04.01

extern struct proc proc[NPROC];

static void
t0401_proc_table(void)
{
  st_begin("04.01");
  struct proc *me = myproc();
  pte_t pte;
  EXPECT(me != 0 && me->state == RUNNING);

  // Every slot owns a kernel stack page with an unmapped guard page
  // below it, so a stack overflow faults instead of corrupting the
  // neighbour's stack.
  int ok = 1;
  for(int i = 0; i < NPROC; i++){
    pte = pte_of(kernel_pagetable, proc[i].kstack);
    if(proc[i].kstack != KSTACK(i) || FLAGS(pte) != (PTE_V|PTE_R|PTE_W) ||
       (pte_of(kernel_pagetable, proc[i].kstack - PGSIZE) & PTE_V))
      ok = 0;
  }
  EXPECT(ok);

  // This code is running on this process's own kernel stack.
  uint64 sp = r_sp();
  EXPECT(sp > me->kstack && sp <= me->kstack + PGSIZE);

  // Every process's page table maps the trampoline and its trapframe at
  // the top, neither one user-accessible.
  pte = pte_of(me->pagetable, TRAMPOLINE);
  EXPECT(FLAGS(pte) == (PTE_V|PTE_R|PTE_X) && PTE2PA(pte) == (uint64)trampoline);
  pte = pte_of(me->pagetable, TRAPFRAME);
  EXPECT(FLAGS(pte) == (PTE_V|PTE_R|PTE_W) && PTE2PA(pte) == (uint64)me->trapframe);

  printf("[04.01] pid %d \"%s\" in slot %ld of %d, kernel stack %p, sp %p\n",
         me->pid, me->name, (long)(me - proc), NPROC, (void*)me->kstack, (void*)sp);
  st_end();
}

// ---------------------------------------------------------------- 04.02

static volatile int pp_turn, pp_handoffs, pp_yields;
static volatile int pp_harts[2]; // bitmask of the harts each thread ran on

// Two threads take turns: each waits (yielding) until it is its turn,
// counts, and passes the turn on.
static void
pingpong(void *arg)
{
  int me = (int)(uint64)arg;
  for(int i = 0; i < 1000; i++){
    while(pp_turn != me){
      __sync_fetch_and_add(&pp_yields, 1);
      yield();
    }
    push_off();
    pp_harts[me] |= 1 << cpuid();
    pop_off();
    pp_handoffs++;
    __sync_synchronize();
    pp_turn = 1 - me;
  }
}

static void
t0402_context_switch(void)
{
  st_begin("04.02");
  int a = kthread("ping", pingpong, (void*)0);
  int b = kthread("pong", pingpong, (void*)1);
  EXPECT(a > 0 && b > 0 && a != b);
  int w1 = kwait(0);
  int w2 = kwait(0);
  EXPECT((w1 == a && w2 == b) || (w1 == b && w2 == a));
  EXPECT(kwait(0) == -1);  // no children left
  printf("[04.02] ping and pong: %d hand-offs, %d yields, ran on harts %x and %x\n",
         pp_handoffs, pp_yields, pp_harts[0], pp_harts[1]);
  EXPECT(pp_handoffs == 2000);
  st_end();
}

// ---------------------------------------------------------------- 04.03

static struct spinlock mb_lock;
static volatile int mb_full, mb_value, mb_sleeps;
#define NITEMS 1000

// A one-slot mailbox. The producer sleeps while it is full; the consumer
// sleeps while it is empty. Each wakes the other.
static void
producer(void *arg)
{
  for(int i = 1; i <= NITEMS; i++){
    acquire(&mb_lock);
    while(mb_full){
      mb_sleeps++;
      sleep((void*)&mb_full, &mb_lock);
    }
    mb_value = i;
    mb_full = 1;
    wakeup((void*)&mb_value);
    release(&mb_lock);
  }
}

static void
consumer(void *arg)
{
  uint64 *sum = arg;
  for(int i = 1; i <= NITEMS; i++){
    acquire(&mb_lock);
    while(!mb_full){
      mb_sleeps++;
      sleep((void*)&mb_value, &mb_lock);
    }
    *sum += mb_value;
    mb_full = 0;
    wakeup((void*)&mb_full);
    release(&mb_lock);
  }
}

static void
t0403_sleep_wakeup(void)
{
  st_begin("04.03");
  uint64 sum = 0;
  initlock(&mb_lock, "mailbox");
  kthread("producer", producer, 0);
  kthread("consumer", consumer, &sum);
  kwait(0);
  kwait(0);
  printf("[04.03] %d items through a one-slot mailbox: sum %ld, %d sleeps\n",
         NITEMS, sum, mb_sleeps);
  EXPECT(sum == (uint64)NITEMS * (NITEMS + 1) / 2);
  EXPECT(mb_sleeps > 0);
  st_end();
}

// ---------------------------------------------------------------- 04.04

#define NSPIN 6
static volatile int spin_stop;
static volatile uint64 spin_count[NSPIN];

// Never yields, never sleeps. Only the timer can take its hart away.
static void
spinner(void *arg)
{
  int i = (int)(uint64)arg;
  while(!spin_stop)
    spin_count[i]++;
}

static void
t0404_preemption(void)
{
  st_begin("04.04");
  for(int i = 0; i < NSPIN; i++)
    kthread("spinner", spinner, (void*)(uint64)i);

  // More spinners than harts. We get to run again (to set spin_stop)
  // only if the timer interrupt takes a hart away from a spinner.
  acquire(&tickslock);
  uint t0 = ticks;
  while(ticks - t0 < 5)
    sleep(&ticks, &tickslock);
  release(&tickslock);
  spin_stop = 1;
  for(int i = 0; i < NSPIN; i++)
    kwait(0);

  int progressed = 0;
  for(int i = 0; i < NSPIN; i++)
    if(spin_count[i] > 0)
      progressed++;
  printf("[04.04] %d spinners on %d harts, none ever yields: %d of them ran\n",
         NSPIN, st_arrived, progressed);
  EXPECT(progressed == NSPIN);
  st_end();
}

// ---------------------------------------------------------------- 05.x helpers

// Sleep for n timer ticks.
static void
st_sleep(int n)
{
  acquire(&tickslock);
  uint t0 = ticks;
  while(ticks - t0 < n)
    sleep(&ticks, &tickslock);
  release(&tickslock);
}

// Create a file or directory, as sys_open(O_CREATE) and sys_mkdir will
// in 06.07. Caller must be inside a transaction. Returns it locked.
static struct inode*
st_create(char *path, short type)
{
  char name[DIRSIZ];
  struct inode *dp, *ip;

  if((dp = nameiparent(path, name)) == 0)
    return 0;
  ilock(dp);
  if((ip = dirlookup(dp, name, 0)) != 0){
    iunlockput(dp);
    ilock(ip);
    return ip;
  }
  ip = ialloc(dp->dev, type);
  ilock(ip);
  ip->nlink = 1;
  iupdate(ip);
  if(type == T_DIR){
    // . and .. ; "." does not count as a link, or the directory could
    // never be freed.
    dirlink(ip, ".", ip->inum);
    dirlink(ip, "..", dp->inum);
    dp->nlink++;   // for ".."
    iupdate(dp);
  }
  dirlink(dp, name, ip->inum);
  iunlockput(dp);
  return ip;
}

// Remove a name, as sys_unlink will. Caller must be inside a transaction.
static void
st_unlink(char *path)
{
  char name[DIRSIZ];
  uint off;
  struct dirent de;
  struct inode *dp = nameiparent(path, name);
  ilock(dp);
  struct inode *ip = dirlookup(dp, name, &off);
  ilock(ip);
  memset(&de, 0, sizeof(de));
  writei(dp, 0, (uint64)&de, off, sizeof(de));
  if(ip->type == T_DIR){
    dp->nlink--;
    iupdate(dp);
  }
  iunlockput(dp);
  ip->nlink--;
  iupdate(ip);
  iunlockput(ip);
}

// ---------------------------------------------------------------- 05.01

extern int virtio_disk_reads, virtio_disk_writes;
static struct buf st_buf;   // a private buffer, outside the cache
#define ST_PATTERN "written by the 05.01 self-test"

static void
t0501_virtio(void)
{
  st_begin("05.01");
  initsleeplock(&st_buf.lock, "st_buf");
  st_buf.dev = ROOTDEV;

  // Read block 1 straight from the device, bypassing the buffer cache.
  int r0 = virtio_disk_reads;
  st_buf.blockno = 1;
  virtio_disk_rw(&st_buf, 0);
  struct superblock *sbp = (struct superblock*)st_buf.data;
  printf("[05.01] read block 1 from the device: magic %x, %d blocks\n", sbp->magic, sbp->size);
  EXPECT(sbp->magic == FSMAGIC);
  EXPECT(virtio_disk_reads == r0 + 1);

  // Write a pattern to the last block (mkfs leaves it unused), wipe our
  // copy, and read it back from the device.
  st_buf.blockno = FSSIZE - 1;
  memset(st_buf.data, 0, BSIZE);
  safestrcpy((char*)st_buf.data, ST_PATTERN, BSIZE);
  virtio_disk_rw(&st_buf, 1);
  memset(st_buf.data, 0, BSIZE);
  virtio_disk_rw(&st_buf, 0);
  EXPECT(strncmp((char*)st_buf.data, ST_PATTERN, BSIZE) == 0);
  printf("[05.01] wrote block %d and read it back\n", FSSIZE - 1);
  st_end();
}

// ---------------------------------------------------------------- 05.02

static volatile int bc_stage;

// Holds block 300 across a sleep, the way a process holds a buffer while
// it waits for more I/O.
static void
holder(void *arg)
{
  struct buf *b = bread(ROOTDEV, 300);
  bc_stage = 1;
  st_sleep(3);
  b->data[0] = 'H';
  bc_stage = 2;
  brelse(b);
}

static void
t0502_buffer_cache(void)
{
  st_begin("05.02");
  int r0 = virtio_disk_reads;
  struct buf *b = bread(ROOTDEV, 200);
  EXPECT(b->valid && holdingsleep(&b->lock));
  brelse(b);
  int first = virtio_disk_reads - r0;

  r0 = virtio_disk_reads;
  struct buf *b2 = bread(ROOTDEV, 200);
  EXPECT(b2 == b);            // the same buffer...
  brelse(b2);
  int second = virtio_disk_reads - r0;   // ...and no disk read

  // Touch NBUF other blocks: block 200 becomes least recently used and
  // its buffer is recycled.
  for(int i = 0; i < NBUF; i++)
    brelse(bread(ROOTDEV, 100 + i));
  r0 = virtio_disk_reads;
  brelse(bread(ROOTDEV, 200));
  int third = virtio_disk_reads - r0;

  printf("[05.02] disk reads for block 200: first bread %d, second %d, after %d other blocks %d\n",
         first, second, NBUF, third);
  EXPECT(first == 1 && second == 0 && third == 1);

  // One process at a time per buffer: bread() of a block another process
  // holds sleeps until that process calls brelse().
  kthread("holder", holder, 0);
  while(bc_stage == 0)
    yield();
  b = bread(ROOTDEV, 300);
  EXPECT(bc_stage == 2 && b->data[0] == 'H');
  printf("[05.02] bread of a held block waited for brelse: %s\n",
         bc_stage == 2 ? "yes" : "no");
  b->data[0] = 0;
  brelse(b);
  kwait(0);
  st_end();
}

// ---------------------------------------------------------------- 05.03

extern struct superblock sb;

static void
t0503_layout(void)
{
  st_begin("05.03");
  printf("[05.03] superblock: size %d nblocks %d ninodes %d nlog %d logstart %d inodestart %d bmapstart %d\n",
         sb.size, sb.nblocks, sb.ninodes, sb.nlog, sb.logstart, sb.inodestart, sb.bmapstart);
  EXPECT(sb.magic == FSMAGIC);
  EXPECT(sb.logstart == 2);
  EXPECT(sb.inodestart == sb.logstart + sb.nlog);
  EXPECT(sb.bmapstart == sb.inodestart + sb.ninodes / IPB + 1);

  begin_op();
  struct inode *root = namei("/");
  ilock(root);
  EXPECT(root->inum == ROOTINO && root->type == T_DIR);
  printf("[05.03] / holds:");
  struct dirent de;
  for(uint off = 0; off < root->size; off += sizeof(de)){
    readi(root, 0, (uint64)&de, off, sizeof(de));
    if(de.inum == 0)
      continue;
    char name[DIRSIZ+1];
    memmove(name, de.name, DIRSIZ);
    name[DIRSIZ] = 0;
    printf(" %s", name);
  }
  printf("\n");
  struct inode *ip = dirlookup(root, "README", 0);
  EXPECT(ip != 0);
  if(ip){
    ilock(ip);
    printf("[05.03] README is inode %d, %d bytes\n", ip->inum, ip->size);
    iunlockput(ip);
  }
  iunlockput(root);
  end_op();

  // The block allocator: writing one byte to a new file takes exactly one
  // block out of the bitmap, and unlinking it puts the block back.
  uint free0 = balloc_count_free(ROOTDEV);
  begin_op();
  ip = st_create("/blocktest", T_FILE);
  EXPECT(writei(ip, 0, (uint64)"x", 0, 1) == 1);
  iunlockput(ip);
  end_op();
  uint free1 = balloc_count_free(ROOTDEV);
  begin_op();
  st_unlink("/blocktest");
  end_op();
  printf("[05.03] free blocks: %d, after a 1-byte file %d, after unlinking it %d\n",
         free0, free1, balloc_count_free(ROOTDEV));
  EXPECT(free1 == free0 - 1);
  EXPECT(balloc_count_free(ROOTDEV) == free0);
  st_end();
}

// ---------------------------------------------------------------- 05.04

extern int log_recovered;
#ifdef LOGCRASH
static int crash_armed;
#endif

// log.c calls this at two points inside commit(). A kernel built with
// -DLOGCRASH=1 or =2 crashes there, once the 05.04 check arms it.
void
selftest_log_crashpoint(int point)
{
#ifdef LOGCRASH
  if(crash_armed && point == LOGCRASH)
    panic("[05.04] simulated crash during commit");
#endif
}

static void
t0504_log(void)
{
  st_begin("05.04");
  printf("[05.04] recovery at boot replayed %d blocks\n", log_recovered);
  begin_op();
  struct inode *ip = namei("/crashtest");
  if(ip){
    char buf[64];
    ilock(ip);
    int n = readi(ip, 0, (uint64)buf, 0, sizeof(buf) - 1);
    buf[n > 0 ? n : 0] = 0;
    iunlockput(ip);
    printf("[05.04] /crashtest is present: \"%s\"\n", buf);
  } else {
    printf("[05.04] /crashtest is absent\n");
  }
  end_op();

  // A transaction that commits normally leaves the on-disk log empty.
  begin_op();
  ip = st_create("/logtest", T_FILE);
  iunlockput(ip);
  end_op();
  struct buf *h = bread(ROOTDEV, sb.logstart);
  EXPECT(*(int*)h->data == 0);
  brelse(h);
  begin_op();
  st_unlink("/logtest");
  end_op();

#ifdef LOGCRASH
  // Create /crashtest and write to it in one transaction, then crash in
  // the middle of committing it.
  begin_op();
  ip = st_create("/crashtest", T_FILE);
  char *msg = "survived the crash";
  writei(ip, 0, (uint64)msg, 0, strlen(msg));
  iunlockput(ip);
  crash_armed = 1;
  printf("[05.04] committing /crashtest; will crash at point %d\n", LOGCRASH);
  end_op();
  panic("[05.04] the crash point was never reached");
#endif
  st_end();
}

// ---------------------------------------------------------------- 05.05

static void
t0505_inodes(void)
{
  st_begin("05.05");
  static char blk[BSIZE];
  uint free0 = balloc_count_free(ROOTDEV);

  begin_op();
  struct inode *ip = st_create("/bigfile", T_FILE);
  iunlock(ip);
  end_op();

  // More blocks than fit in the inode's NDIRECT direct pointers.
  int nblk = NDIRECT + 20;
  int ok = 1;
  for(int i = 0; i < nblk && ok; i++){
    memset(blk, 'a' + i % 26, BSIZE);
    begin_op();       // one block per transaction keeps each one small
    ilock(ip);
    ok = writei(ip, 0, (uint64)blk, i * BSIZE, BSIZE) == BSIZE;
    iunlock(ip);
    end_op();
  }
  EXPECT(ok);

  ilock(ip);
  EXPECT(ip->size == nblk * BSIZE);
  EXPECT(ip->addrs[NDIRECT] != 0);   // the indirect block is in use
  uint used = free0 - balloc_count_free(ROOTDEV);
  int good = 1;
  for(int i = 0; i < nblk; i++){
    readi(ip, 0, (uint64)blk, i * BSIZE, BSIZE);
    if(blk[0] != 'a' + i % 26 || blk[BSIZE-1] != 'a' + i % 26)
      good = 0;
  }
  EXPECT(good);
  // A file cannot grow past MAXFILE blocks.
  EXPECT(writei(ip, 0, (uint64)blk, MAXFILE * BSIZE, 1) == -1);
  iunlock(ip);
  printf("[05.05] /bigfile: %d blocks (%d direct, %d via the indirect block) took %d disk blocks; max file %ld KB\n",
         nblk, NDIRECT, nblk - NDIRECT, used, (long)MAXFILE * BSIZE / 1024);
  EXPECT(used == nblk + 1);   // the data, plus the indirect block itself

  // Unlink it; dropping the last reference frees every block.
  begin_op();
  st_unlink("/bigfile");
  iput(ip);
  end_op();
  uint after = balloc_count_free(ROOTDEV);
  printf("[05.05] after unlink: %d blocks free, %d before the file existed\n", after, free0);
  EXPECT(after == free0);
  st_end();
}

// ---------------------------------------------------------------- 05.06

static uint
inum_of(char *path)
{
  struct inode *ip = namei(path);
  if(ip == 0)
    return 0;
  uint n = ip->inum;
  iput(ip);
  return n;
}

static void
t0506_directories(void)
{
  st_begin("05.06");
  struct inode *ip;

  begin_op();
  ip = st_create("/d", T_DIR);
  uint d = ip->inum;
  iunlockput(ip);
  end_op();
  begin_op();
  ip = st_create("/d/f", T_FILE);
  uint f = ip->inum;
  iunlockput(ip);
  end_op();
  begin_op();
  ip = st_create("/d/abcdefghijklmnopqrstuvwxyz", T_FILE);
  uint lng = ip->inum;
  iunlockput(ip);
  end_op();

  begin_op();
  EXPECT(inum_of("/d/f") == f);
  EXPECT(inum_of("//d///./f") == f);
  EXPECT(inum_of("/d/../d/f") == f);
  EXPECT(inum_of("/d/..") == ROOTINO);
  EXPECT(inum_of("/d/missing") == 0);
  EXPECT(inum_of("/README/x") == 0);              // README is not a directory
  EXPECT(inum_of("/d/abcdefghijklmn") == lng);    // names are cut to DIRSIZ
  char name[DIRSIZ];
  ip = nameiparent("/d/f", name);
  EXPECT(ip && ip->inum == d && namecmp(name, "f") == 0);
  if(ip)
    iput(ip);
  printf("[05.06] /d is inode %d, /d/f is inode %d, \"/d/../d/./f\" resolves to %d\n",
         d, f, inum_of("/d/../d/./f"));
  end_op();

  begin_op();
  st_unlink("/d/abcdefghijklmnopqrstuvwxyz");
  end_op();
  begin_op();
  st_unlink("/d/f");
  end_op();
  begin_op();
  st_unlink("/d");
  EXPECT(inum_of("/d") == 0);
  end_op();
  st_end();
}

// ---------------------------------------------------------------- 05.07

static void
t0507_files(void)
{
  st_begin("05.07");
  struct file *f = filealloc();
  EXPECT(f && f->ref == 1);
  EXPECT(filedup(f) == f && f->ref == 2);
  fileclose(f);
  EXPECT(f->ref == 1);
  fileclose(f);
  EXPECT(f->ref == 0);

  // The table is finite: NFILE open files for the whole system.
  static struct file *all[NFILE + 1];
  int n = 0;
  while(n <= NFILE && (all[n] = filealloc()) != 0)
    n++;
  for(int i = 0; i < n; i++)
    fileclose(all[i]);
  printf("[05.07] the open-file table filled up after %d files\n", n);
  EXPECT(n == NFILE);

  // Devices are reached through devsw[], indexed by major number.
  char *msg = "[05.07] hello through devsw[CONSOLE]\n";
  EXPECT(devsw[CONSOLE].write(0, (uint64)msg, strlen(msg)) == strlen(msg));
  st_sleep(2);  // let the UART drain before printing more
  st_end();
}

// ---------------------------------------------------------------- startup

// The first process, in a SELFTEST build: runs every check that needs a
// process (sleeping, scheduling, disk I/O).
static void
selftest_main(void *arg)
{
  printf("selftest: kernel thread checks\n");
  // Another hart may run this thread while hart 0 is still reporting
  // 01.01 and 02.03 above; st_begin/st_end share `cur`, so wait for it.
  while(!st_harts_reported)
    yield();
  t0302_timer();
  t0401_proc_table();
  t0402_context_switch();
  t0403_sleep_wakeup();
  t0404_preemption();

  fsinit(ROOTDEV);
  t0501_virtio();
  t0502_buffer_cache();
  t0503_layout();
  t0504_log();
  t0505_inodes();
  t0506_directories();
  t0507_files();
  printf("selftest: kernel checks done\n");

  // Start user space, and hand ourselves to init, which reaps orphans.
  extern struct spinlock wait_lock;
  extern struct proc *initproc;
  userinit();
  acquire(&wait_lock);
  myproc()->parent = initproc;
  release(&wait_lock);
}

void
selftest_start(void)
{
  if(kthread("selftest", selftest_main, 0) < 0)
    panic("selftest_start");
}

// Called on hart 0 in main(), after every subsystem is initialized but
// before any other hart runs and before interrupts are on.
void
selftest_early(void)
{
  printf("selftest: early checks\n");
  initlock(&st_lock, "selftest");
  t0103_printf();
  t0201_memory_map();
  t0202_kalloc();
  t0204_page_tables();
  t0301_kernel_traps();
}

#else  // !SELFTEST

void selftest_early(void) {}
void selftest_harts(void) {}
void selftest_start(void) {}
int selftest_trap(uint64 scause, uint64 stval, uint64 *sepc) { return 0; }
void selftest_log_crashpoint(int point) {}

#endif
