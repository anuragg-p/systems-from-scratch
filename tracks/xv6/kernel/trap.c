// Traps: exceptions, interrupts and system calls.
//
// A trap is the hardware forcing a jump into the kernel. There are three
// kinds, and all of them arrive through stvec:
//   - exceptions: the running instruction cannot proceed (page fault,
//     illegal instruction, ecall)
//   - interrupts: the timer, or a device such as the UART
//   - system calls: an ecall from user mode, which is an exception too
// scause says which one it was.

#include "kernel/types.h"
#include "kernel/param.h"
#include "kernel/memlayout.h"
#include "kernel/riscv.h"
#include "kernel/spinlock.h"
#include "kernel/proc.h"
#include "kernel/defs.h"

struct spinlock tickslock;  // @from 03.02
uint ticks;  // @from 03.02

extern char trampoline[], uservec[], userret[];  // @from 06.01

// in kernelvec.S, calls kerneltrap().
void kernelvec(void);

int devintr(void);

// @from 03.02
void
trapinit(void)
{
  initlock(&tickslock, "time");
}
// @end

// set up to take exceptions and traps while in the kernel.
void
trapinithart(void)
{
  w_stvec((uint64)kernelvec);
}

// An exception in the kernel is a kernel bug: report it and stop.
// unexpected() returns a value and takes sepc so that a kernel could
// resume after an exception it expected, at *sepc (real kernels keep a
// table of instructions that may fault and where each one goes on). This
// kernel expects none, so here it never returns.
// @internal
// A SELFTEST build first lets the self-tests claim exceptions they caused
// on purpose (03.01); then this returns 1 and *sepc says where to resume.
// @end
static int
unexpected(uint64 scause, uint64 *sepc)
{
  // @internal
#ifdef SELFTEST
  if(selftest_trap(scause, r_stval(), sepc))
    return 1;
#endif
  // @end
  printf("scause=0x%lx sepc=0x%lx stval=0x%lx\n", scause, r_sepc(), r_stval());
  panic("kerneltrap");
}

// handle an interrupt, exception, or system call from user space.
// called from trampoline.S. Returns the user satp for userret.
uint64
usertrap(void)
{
  // @build 06.01 usertrap
  // A trap from user space; uservec already saved the user registers in
  // the trapframe and switched to the kernel page table. Point stvec at
  // kernelvec (we are in the kernel now) and save sepc in trapframe->epc.
  //   scause 8, a system call: if the process was killed, kexit(-1).
  //     Advance epc past the 4-byte ecall, turn interrupts on (sepc and
  //     scause are saved, so it is safe now) and syscall().
  //   a device or timer interrupt (devintr() != 0): fine.
  //   anything else - a page fault, say: print scause, sepc and stval and
  //     mark the process killed.
  // Then: if killed, kexit(-1); if it was the timer, yield(). Finally
  // prepare_return() and return the user page table as a satp value.
  int which_dev = 0;

  if((r_sstatus() & SSTATUS_SPP) != 0)
    panic("usertrap: not from user mode");

  // send interrupts and exceptions to kerneltrap(),
  // since we're now in the kernel.
  w_stvec((uint64)kernelvec);

  struct proc *p = myproc();

  // save user program counter.
  p->trapframe->epc = r_sepc();

  if(r_scause() == 8){
    // system call

    if(killed(p))
      kexit(-1);

    // sepc points to the ecall instruction,
    // but we want to return to the next instruction.
    p->trapframe->epc += 4;

    // an interrupt will change sepc, scause, and sstatus,
    // so enable only now that we're done with those registers.
    intr_on();

    syscall();  // @from 06.02
  } else if((which_dev = devintr()) != 0){
    // ok
  } else {
    printf("usertrap(): unexpected scause 0x%lx pid=%d\n", r_scause(), p->pid);
    printf("            sepc=0x%lx stval=0x%lx\n", r_sepc(), r_stval());
    setkilled(p);
  }

  if(killed(p))
    kexit(-1);

  // give up the CPU if this is a timer interrupt.
  if(which_dev == 2)
    yield();

  prepare_return();

  // the user page table to switch to, for trampoline.S
  uint64 satp = MAKE_SATP(p->pagetable);

  // return to trampoline.S; satp value in a0.
  return satp;
  // @end
}

// set up trapframe and control registers for a return to user space
void
prepare_return(void)
{
  // @build 06.01 prepare_return
  // About to point traps at user space again, so turn interrupts off: a
  // trap now would go to uservec while we are still in the kernel. Set
  // stvec to uservec's address in the trampoline page (TRAMPOLINE +
  // (uservec - trampoline)). Fill in the trapframe fields uservec will
  // need next time: kernel_satp, kernel_sp (top of p->kstack),
  // kernel_trap (usertrap), kernel_hartid (tp). In sstatus clear SPP (so
  // sret goes to user mode) and set SPIE (interrupts on there). Put the
  // saved user pc in sepc.
  struct proc *p = myproc();

  // we're about to switch the destination of traps from
  // kerneltrap() to usertrap(). because a trap from kernel
  // code to usertrap would be a disaster, turn off interrupts.
  intr_off();

  // send syscalls, interrupts, and exceptions to uservec in trampoline.S
  uint64 trampoline_uservec = TRAMPOLINE + (uservec - trampoline);
  w_stvec(trampoline_uservec);

  // set up trapframe values that uservec will need when
  // the process next traps into the kernel.
  p->trapframe->kernel_satp = r_satp();         // kernel page table
  p->trapframe->kernel_sp = p->kstack + PGSIZE; // process's kernel stack
  p->trapframe->kernel_trap = (uint64)usertrap;
  p->trapframe->kernel_hartid = r_tp();         // hartid for cpuid()

  // set up the registers that trampoline.S's sret will use
  // to get to user space.

  // set S Previous Privilege mode to User.
  unsigned long x = r_sstatus();
  x &= ~SSTATUS_SPP; // clear SPP to 0 for user mode
  x |= SSTATUS_SPIE; // enable interrupts in user mode
  w_sstatus(x);

  // set S Exception Program Counter to the saved user pc.
  w_sepc(p->trapframe->epc);
  // @end
}

// interrupts and exceptions from kernel code go here via kernelvec,
// on whatever the current kernel stack is.
void
kerneltrap(void)
{
  int which_dev = 0;
  uint64 sepc = r_sepc();
  uint64 sstatus = r_sstatus();
  uint64 scause = r_scause();

  // @build 03.01 kerneltrap
  // A trap arrived while the kernel was running. Panic unless it came
  // from supervisor mode (sstatus.SPP set) with interrupts off. Then ask
  // devintr() what it was: 1 a device, 2 the timer, 0 an exception. An
  // exception in the kernel is a bug: hand it to unexpected(). If that
  // returns 1 (the exception was expected, and sepc now says where to
  // resume), write sepc and sstatus back and return.
  if((sstatus & SSTATUS_SPP) == 0)
    panic("kerneltrap: not from supervisor mode");
  if(intr_get() != 0)
    panic("kerneltrap: interrupts enabled");

  if((which_dev = devintr()) == 0){
    if(unexpected(scause, &sepc)){
      // an expected exception: resume at sepc.
      w_sepc(sepc);
      w_sstatus(sstatus);
      return;
    }
  }
  // @end

  // @build 04.04 preemption
  // If that was a timer interrupt and a process is running on this hart,
  // give up the CPU: yield(). These two lines are preemption.
  // @stub ;
  if(which_dev == 2 && myproc() != 0)
    yield();
  // @end

  // @from 04.04
  // the yield() may have caused some traps to occur,
  // so restore trap registers for use by kernelvec.S's sret instruction.
  // @else
  // // put back the trap registers kernelvec.S's sret uses, as they were
  // // when this trap arrived.
  // @end
  w_sepc(sepc);
  w_sstatus(sstatus);
}

void
clockintr(void)
{
  // @build 03.02 clockintr
  // The timer fired. On hart 0 only, count it: ticks++ under tickslock and
  // wakeup(&ticks) for anyone sleeping on time. On every hart, ask for the
  // next interrupt: stimecmp = time + 1000000. Writing stimecmp is also
  // what clears this one.
  if(cpuid() == 0){
    acquire(&tickslock);
    ticks++;
    wakeup(&ticks);  // @from 04.03
    release(&tickslock);
  }

  // ask for the next timer interrupt. this also clears
  // the interrupt request. 1000000 is about a tenth
  // of a second.
  w_stimecmp(r_time() + 1000000);
  // @end
}

// check if it's an external interrupt or a timer interrupt,
// and handle it.
// returns 2 if timer interrupt,
// 1 if other device,
// 0 if not recognized.
int
devintr(void)
{
  uint64 scause = r_scause();

  if(scause == 0x8000000000000009L){
    // this is a supervisor external interrupt, via PLIC.

    // @from 03.03
    // irq indicates which device interrupted.
    int irq = plic_claim();

    if(irq == UART0_IRQ){
      uartintr();
    } else if(irq == VIRTIO0_IRQ){  // @from 05.01
      virtio_disk_intr();  // @from 05.01
    } else if(irq == VIRTIO1_IRQ){  // @from 08.01
      virtio_net_intr();  // @from 08.01
    } else if(irq == VIRTIO2_IRQ || irq == VIRTIO3_IRQ){  // @from 09.03
      virtio_input_intr(irq);  // @from 09.03
    } else if(irq){
      printf("unexpected interrupt irq=%d\n", irq);
    }

    // the PLIC allows each device to raise at most one
    // interrupt at a time; tell the PLIC the device is
    // now allowed to interrupt again.
    if(irq)
      plic_complete(irq);
    // @end

    return 1;
  } else if(scause == 0x8000000000000005L){
    // timer interrupt.
    clockintr();  // @from 03.02
    return 2;
  } else {
    return 0;
  }
}
