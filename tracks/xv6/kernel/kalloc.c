// The physical page allocator.
//
// Hands out whole 4096-byte pages of RAM, one at a time, to the rest of
// the kernel. Every free page holds a struct run in its first bytes, so
// the free list costs no memory of its own: the free pages *are* the list.

#include "kernel/types.h"
#include "kernel/param.h"
#include "kernel/memlayout.h"
#include "kernel/spinlock.h"
#include "kernel/riscv.h"
#include "kernel/defs.h"

void freerange(void *pa_start, void *pa_end);

extern char end[]; // first address after kernel.
                   // defined by kernel.ld.

struct run {
  struct run *next;
};

struct {
  struct spinlock lock;
  struct run *freelist;
} kmem;

void
kinit(void)
{
  initlock(&kmem.lock, "kmem");  // @from 02.03
  freerange(end, (void*)PHYSTOP);
}

void
freerange(void *pa_start, void *pa_end)
{
  char *p;
  p = (char*)PGROUNDUP((uint64)pa_start);
  for(; p + PGSIZE <= (char*)pa_end; p += PGSIZE)
    kfree(p);
}

// Free the page of physical memory pointed at by pa,
// which normally should have been returned by a
// call to kalloc().  (The exception is when
// initializing the allocator; see kinit above.)
void
kfree(void *pa)
{
  // @build 02.02 kfree
  // Put the page at pa back on kmem.freelist. Panic unless pa is page
  // aligned and inside [end, PHYSTOP). Fill the page with 1s first, so code
  // that keeps using a freed page reads garbage and fails loudly. The list
  // node (struct run) lives inside the free page itself. Hold kmem.lock
  // while you touch the list.
  struct run *r;

  if(((uint64)pa % PGSIZE) != 0 || (char*)pa < end || (uint64)pa >= PHYSTOP)
    panic("kfree");

  // Fill with junk (1s) to catch dangling refs: code that keeps using a
  // page after freeing it reads garbage and fails loudly, not subtly.
  memset(pa, 1, PGSIZE);

  r = (struct run*)pa;

  acquire(&kmem.lock);  // @from 02.03
  r->next = kmem.freelist;
  kmem.freelist = r;
  release(&kmem.lock);  // @from 02.03
  // @end
}

// Allocate one 4096-byte page of physical memory.
// Returns a pointer that the kernel can use.
// Returns 0 if the memory cannot be allocated.
void *
kalloc(void)
{
  // @build 02.02 kalloc
  // Take one page off kmem.freelist, holding kmem.lock. Fill it with 5s so
  // no caller can count on getting zeroes. Return it, or 0 if the list is
  // empty.
  struct run *r;

  acquire(&kmem.lock);  // @from 02.03
  r = kmem.freelist;
  if(r)
    kmem.freelist = r->next;
  release(&kmem.lock);  // @from 02.03

  if(r)
    memset((char*)r, 5, PGSIZE); // fill with junk (5s): callers must not assume zeroes
  return (void*)r;
  // @end
}

// @internal
// How many pages are free right now. Not in the original xv6; the
// self-tests use it to prove that every page handed out comes back.
int
kfreecount(void)
{
  int n = 0;
  acquire(&kmem.lock);
  for(struct run *r = kmem.freelist; r; r = r->next)
    n++;
  release(&kmem.lock);
  return n;
}
// @end
