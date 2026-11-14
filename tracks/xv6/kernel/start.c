// @from 01.02
// Machine mode, and the drop to supervisor mode.
//
// RISC-V has three privilege levels: machine (M), supervisor (S) and
// user (U). The hart wakes up in M-mode, which can do anything. The
// kernel proper runs in S-mode, where paging works and where traps from
// user programs arrive. start() does the few M-mode-only setup steps,
// then "returns" into main() in S-mode with mret.
// @else
// // The boot stacks: entry.S gives each hart its own slice of stack0.
// @end

#include "kernel/types.h"
#include "kernel/param.h"
#include "kernel/memlayout.h"  // @from 01.02
#include "kernel/riscv.h"      // @from 01.02
#include "kernel/defs.h"       // @from 01.02

void main(void);       // @from 01.02
void timerinit(void);  // @from 03.02

// entry.S needs one stack per CPU.
__attribute__ ((aligned (16))) char stack0[4096 * NCPU];

// @from 01.02
// The simplest output there is: store each byte straight into the UART's
// transmit register. No locks, no interrupts, no printf - so it works
// before anything else does.
void
early_puts(char *s)
{
  while(*s)
    *(volatile char *)UART0 = *s++;
}
// @end

// entry.S jumps here in machine mode on stack0.
void
start(void)
{
  // @build 01.02 drop to supervisor mode
  // We wake up in machine mode. Arrange for mret to "return" into main()
  // in supervisor mode: put S in mstatus.MPP and main's address in mepc.
  // Before that: paging off (satp = 0); delegate every exception and
  // interrupt to S-mode (medeleg, mideleg = 0xffff) and enable external and
  // timer interrupts in sie; open all of memory to S-mode with PMP
  // (pmpaddr0, pmpcfg0); call timerinit(); and copy the hart id into tp,
  // because S-mode cannot read mhartid. Then mret.
  // @stub if(r_mhartid() == 0){ early_puts("01.02: start() not written yet\n"); } for(;;){ }

  // mret "returns" to the privilege mode stored in mstatus.MPP.
  // Pretend we came from supervisor mode.
  unsigned long x = r_mstatus();
  x &= ~MSTATUS_MPP_MASK;
  x |= MSTATUS_MPP_S;
  w_mstatus(x);

  // ...and to the address in mepc. So mret will land in main().
  w_mepc((uint64)main);

  // Paging off: main() starts out on physical addresses.
  w_satp(0);

  // Hand every exception and interrupt to supervisor mode, so the
  // kernel never has to come back to machine mode.
  w_medeleg(0xffff);
  w_mideleg(0xffff);
  w_sie(r_sie() | SIE_SEIE | SIE_STIE);

  // Physical memory protection: by default S-mode may touch no memory
  // at all. Give it access to everything.
  w_pmpaddr0(0x3fffffffffffffull);
  w_pmpcfg0(0xf);

  // @from 03.02
  // Ask for clock interrupts.
  timerinit();
  // @end

  // Keep each CPU's hartid in its tp register: S-mode cannot read
  // mhartid, so this is how the kernel finds out later which hart it is.
  int id = r_mhartid();
  w_tp(id);

  // Switch to supervisor mode and jump to main().
  asm volatile("mret");
  // @end
}

// Ask each hart to generate timer interrupts.
void
timerinit(void)
{
  // @build 03.02 ask for timer interrupts
  // In machine mode, once per hart: enable supervisor timer interrupts in
  // mie; set bit 63 of menvcfg to turn on the Sstc extension (stimecmp);
  // let S-mode read the time counter (mcounteren bit 1); and ask for the
  // first interrupt by setting stimecmp to now + 1000000 (time runs at
  // 10 MHz, so that is a tenth of a second).
  // @stub early_puts("03.02: timerinit not written yet\n");

  // enable supervisor-mode timer interrupts.
  w_mie(r_mie() | MIE_STIE);

  // enable the sstc extension (i.e. stimecmp).
  w_menvcfg(r_menvcfg() | (1L << 63));

  // allow supervisor to use stimecmp and to read time (mcounteren.TM).
  w_mcounteren(r_mcounteren() | 2);

  // ask for the very first timer interrupt.
  w_stimecmp(r_time() + 1000000);
  // @end
}
