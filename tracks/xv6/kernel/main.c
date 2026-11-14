// main(): where every hart arrives in supervisor mode.
// @from 01.03
//
// Hart 0 initializes each subsystem in dependency order; the others wait
// until it is done and then set up only their per-hart state.
// @end

#include "kernel/types.h"
#include "kernel/param.h"
#include "kernel/memlayout.h"
#include "kernel/riscv.h"
#include "kernel/defs.h"

volatile static int started = 0;  // @from 01.03

// start() jumps here in supervisor mode on all CPUs.
void
main(void)
{
  // @from 01.03
  if(cpuid() == 0){
    consoleinit();
    printfinit();  // @from 02.03
    printf("\n");
    printf("xv6 kernel is booting\n");
    printf("\n");
    kinit();         // physical page allocator @from 02.02
    kvminit();       // create kernel page table @from 02.04
    kvminithart();   // turn on paging @from 02.04
    procinit();      // process table @from 04.01
    trapinit();      // the tick counter's lock @from 03.02
    trapinithart();  // install kernel trap vector @from 03.01
    plicinit();      // set up interrupt controller @from 03.03
    plicinithart();  // ask PLIC for device interrupts @from 03.03
    binit();         // buffer cache @from 05.02
    iinit();         // inode table @from 05.05
    fileinit();      // file table @from 05.07
    virtio_disk_init(); // emulated hard disk @from 05.03
    virtio_net_init();  // network card, if there is one (module 08) @from 08.01
    arpinit();          // ARP cache @from 08.02
    sockinit();         // UDP sockets @from 08.04
    fbinit();           // the screen, if there is one (module 09) @from 09.01
    virtio_input_init(); // keyboard and mouse, if there are any @from 09.03
    // @internal
#ifdef SELFTEST
    selftest_early();
    selftest_start(); // the rest of the self-tests run in a kernel thread,
                      // which then starts init itself
#else
    // @end
    userinit();      // first user process @from 07.02
    // @internal
#endif
    // @end
    __sync_synchronize();
    started = 1;
  } else {
    while(started == 0)
      ;
    __sync_synchronize();
    printf("hart %d starting\n", cpuid());
    kvminithart();    // turn on paging @from 02.04
    trapinithart();   // install kernel trap vector @from 03.01
    plicinithart();   // ask PLIC for device interrupts @from 03.03
  }
  // @end

  // @internal
#ifdef SELFTEST
  selftest_harts();
#endif
  // @end

  // @from 04.02
  scheduler();
  // @else
  // // Nothing to run yet: wait for interrupts, and take them.
  // for(;;){
  //   intr_on();
  //   asm volatile("wfi");
  // }
  // @end
}
