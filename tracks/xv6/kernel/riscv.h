// The RISC-V machine, as seen from C: the control and status registers
// (CSRs) and the bits in them.
//
// Each CSR gets a tiny inline reader/writer because C has no way to name
// a CSR; only the csrr/csrw instructions can touch them.

#ifndef __ASSEMBLER__

// which hart (core) is this? Only readable in machine mode.
static inline uint64
r_mhartid(void)
{
  uint64 x;
  asm volatile("csrr %0, mhartid" : "=r" (x) );
  return x;
}

// ---- Machine Status Register, mstatus

#define MSTATUS_MPP_MASK (3L << 11) // previous mode
#define MSTATUS_MPP_M (3L << 11)
#define MSTATUS_MPP_S (1L << 11)
#define MSTATUS_MPP_U (0L << 11)

static inline uint64
r_mstatus(void)
{
  uint64 x;
  asm volatile("csrr %0, mstatus" : "=r" (x) );
  return x;
}

static inline void
w_mstatus(uint64 x)
{
  asm volatile("csrw mstatus, %0" : : "r" (x));
}

// machine exception program counter: where mret jumps to.
static inline void
w_mepc(uint64 x)
{
  asm volatile("csrw mepc, %0" : : "r" (x));
}

// ---- Supervisor Status Register, sstatus

#define SSTATUS_SPP (1L << 8)  // Previous mode, 1=Supervisor, 0=User
#define SSTATUS_SPIE (1L << 5) // Supervisor Previous Interrupt Enable
#define SSTATUS_SIE (1L << 1)  // Supervisor Interrupt Enable

static inline uint64
r_sstatus(void)
{
  uint64 x;
  asm volatile("csrr %0, sstatus" : "=r" (x) );
  return x;
}

static inline void
w_sstatus(uint64 x)
{
  asm volatile("csrw sstatus, %0" : : "r" (x));
}

// @from 03.01
// Supervisor Interrupt Pending
static inline uint64
r_sip(void)
{
  uint64 x;
  asm volatile("csrr %0, sip" : "=r" (x) );
  return x;
}

static inline void
w_sip(uint64 x)
{
  asm volatile("csrw sip, %0" : : "r" (x));
}
// @end

// Supervisor Interrupt Enable
#define SIE_SEIE (1L << 9) // external
#define SIE_STIE (1L << 5) // timer
#define SIE_SSIE (1L << 1) // software

static inline uint64
r_sie(void)
{
  uint64 x;
  asm volatile("csrr %0, sie" : "=r" (x) );
  return x;
}

static inline void
w_sie(uint64 x)
{
  asm volatile("csrw sie, %0" : : "r" (x));
}

// @from 03.02
// Machine-mode Interrupt Enable
#define MIE_STIE (1L << 5)  // supervisor timer

static inline uint64
r_mie(void)
{
  uint64 x;
  asm volatile("csrr %0, mie" : "=r" (x) );
  return x;
}

static inline void
w_mie(uint64 x)
{
  asm volatile("csrw mie, %0" : : "r" (x));
}
// @end

// @from 03.01
// supervisor exception program counter: the instruction that trapped,
// and where sret returns to.
static inline void
w_sepc(uint64 x)
{
  asm volatile("csrw sepc, %0" : : "r" (x));
}

static inline uint64
r_sepc(void)
{
  uint64 x;
  asm volatile("csrr %0, sepc" : "=r" (x) );
  return x;
}
// @end

// Machine Exception / Interrupt Delegation: which traps go straight to
// supervisor mode instead of machine mode.
static inline uint64
r_medeleg(void)
{
  uint64 x;
  asm volatile("csrr %0, medeleg" : "=r" (x) );
  return x;
}

static inline void
w_medeleg(uint64 x)
{
  asm volatile("csrw medeleg, %0" : : "r" (x));
}

static inline uint64
r_mideleg(void)
{
  uint64 x;
  asm volatile("csrr %0, mideleg" : "=r" (x) );
  return x;
}

static inline void
w_mideleg(uint64 x)
{
  asm volatile("csrw mideleg, %0" : : "r" (x));
}

// @from 03.01
// Supervisor Trap-Vector Base Address: where the hart jumps on a trap.
static inline void
w_stvec(uint64 x)
{
  asm volatile("csrw stvec, %0" : : "r" (x));
}

static inline uint64
r_stvec(void)
{
  uint64 x;
  asm volatile("csrr %0, stvec" : "=r" (x) );
  return x;
}
// @end

// @from 03.02
// Supervisor Timer Comparison Register (the Sstc extension): a timer
// interrupt is pending whenever time >= stimecmp.
static inline uint64
r_stimecmp(void)
{
  uint64 x;
  asm volatile("csrr %0, stimecmp" : "=r" (x) );
  return x;
}

static inline void
w_stimecmp(uint64 x)
{
  asm volatile("csrw stimecmp, %0" : : "r" (x));
}

// Machine Environment Configuration Register
static inline uint64
r_menvcfg(void)
{
  uint64 x;
  asm volatile("csrr %0, menvcfg" : "=r" (x) );
  return x;
}

static inline void
w_menvcfg(uint64 x)
{
  asm volatile("csrw menvcfg, %0" : : "r" (x));
}
// @end

// Physical Memory Protection
static inline void
w_pmpcfg0(uint64 x)
{
  asm volatile("csrw pmpcfg0, %0" : : "r" (x));
}

static inline void
w_pmpaddr0(uint64 x)
{
  asm volatile("csrw pmpaddr0, %0" : : "r" (x));
}

// @from 02.04
// use riscv's sv39 page table scheme.
#define SATP_SV39 (8L << 60)

#define MAKE_SATP(pagetable) (SATP_SV39 | (((uint64)pagetable) >> 12))
// @end

// supervisor address translation and protection;
// holds the address of the page table.
static inline void
w_satp(uint64 x)
{
  asm volatile("csrw satp, %0" : : "r" (x));
}

static inline uint64
r_satp(void)
{
  uint64 x;
  asm volatile("csrr %0, satp" : "=r" (x) );
  return x;
}

// @from 03.01
// Supervisor Trap Cause
static inline uint64
r_scause(void)
{
  uint64 x;
  asm volatile("csrr %0, scause" : "=r" (x) );
  return x;
}

// Supervisor Trap Value: the faulting address, for a page fault.
static inline uint64
r_stval(void)
{
  uint64 x;
  asm volatile("csrr %0, stval" : "=r" (x) );
  return x;
}
// @end

// @from 03.02
// Machine-mode Counter-Enable: lets lower modes read counters.
static inline void
w_mcounteren(uint64 x)
{
  asm volatile("csrw mcounteren, %0" : : "r" (x));
}

static inline uint64
r_mcounteren(void)
{
  uint64 x;
  asm volatile("csrr %0, mcounteren" : "=r" (x) );
  return x;
}

// the real-time counter, time; ticks at 10 MHz on QEMU's virt machine.
// S-mode may read it once mcounteren.TM (bit 1) is set.
static inline uint64
r_time(void)
{
  uint64 x;
  asm volatile("csrr %0, time" : "=r" (x) );
  return x;
}
// @end

// enable device interrupts
static inline void
intr_on(void)
{
  w_sstatus(r_sstatus() | SSTATUS_SIE);
}

// disable device interrupts
static inline void
intr_off(void)
{
  w_sstatus(r_sstatus() & ~SSTATUS_SIE);
}

// are device interrupts enabled?
static inline int
intr_get(void)
{
  uint64 x = r_sstatus();
  return (x & SSTATUS_SIE) != 0;
}

static inline uint64
r_sp(void)
{
  uint64 x;
  asm volatile("mv %0, sp" : "=r" (x) );
  return x;
}

// read and write tp, the thread pointer, which xv6 uses to hold
// this core's hartid (core number).
static inline uint64
r_tp(void)
{
  uint64 x;
  asm volatile("mv %0, tp" : "=r" (x) );
  return x;
}

static inline void
w_tp(uint64 x)
{
  asm volatile("mv tp, %0" : : "r" (x));
}

static inline uint64
r_ra(void)
{
  uint64 x;
  asm volatile("mv %0, ra" : "=r" (x) );
  return x;
}

// @from 02.04
// flush the TLB.
static inline void
sfence_vma(void)
{
  // the zero, zero means flush all TLB entries.
  asm volatile("sfence.vma zero, zero");
}

typedef uint64 pte_t;
typedef uint64 *pagetable_t; // 512 PTEs
// @end

#endif // __ASSEMBLER__

// @from 02.02
#define PGSIZE 4096 // bytes per page
#define PGSHIFT 12  // bits of offset within a page

#define PGROUNDUP(sz)  (((sz)+PGSIZE-1) & ~(PGSIZE-1))
#define PGROUNDDOWN(a) (((a)) & ~(PGSIZE-1))
// @end

// @from 02.04
// Sv39 page-table entries: the flag bits, and where the physical page
// number goes.
#define PTE_V (1L << 0) // valid
#define PTE_R (1L << 1)
#define PTE_W (1L << 2)
#define PTE_X (1L << 3)
#define PTE_U (1L << 4) // user can access
#define PTE_A (1L << 6) // accessed
#define PTE_D (1L << 7) // dirty

// shift a physical address to the right place for a PTE.
#define PA2PTE(pa) ((((uint64)pa) >> 12) << 10)

#define PTE2PA(pte) (((pte) >> 10) << 12)

#define PTE_FLAGS(pte) ((pte) & 0x3FF)

// extract the three 9-bit page table indices from a virtual address.
#define PXMASK          0x1FF // 9 bits
#define PXSHIFT(level)  (PGSHIFT+(9*(level)))
#define PX(level, va) ((((uint64) (va)) >> PXSHIFT(level)) & PXMASK)

// one beyond the highest possible virtual address.
// MAXVA is actually one bit less than the max allowed by
// Sv39, to avoid having to sign-extend virtual addresses
// that have the high bit set.
#define MAXVA (1L << (9 + 9 + 9 + 12 - 1))
// @end
