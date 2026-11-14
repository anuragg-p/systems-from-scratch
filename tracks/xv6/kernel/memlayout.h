// Physical memory layout.
//
// QEMU -machine virt is set up like this, based on qemu's hw/riscv/virt.c:
//
// 00001000 -- boot ROM, provided by qemu
// 02000000 -- CLINT (core-local timer; we use the Sstc extension instead)
// 0C000000 -- PLIC, the platform-level interrupt controller
// 10000000 -- uart0
// 10001000 -- virtio disk
// 10002000 -- virtio network card (module 08, optional) @from 08.01
// 10003000 -- virtio keyboard (module 09, optional) @from 09.03
// 10004000 -- virtio tablet: the mouse (module 09, optional) @from 09.03
// 10100000 -- fw_cfg, QEMU's configuration device (module 09: the screen) @from 09.01
// 80000000 -- boot ROM jumps here in machine mode; -kernel loads the kernel here
// unused RAM after 80000000.
// @from 02.01
//
// The kernel uses physical memory thus:
// 80000000 -- entry.S, then kernel text and data
// end -- start of kernel page allocation area
// PHYSTOP -- end of RAM used by the kernel
// @end

// qemu puts UART registers here in physical memory.
#define UART0 0x10000000L
#define UART0_IRQ 10  // @from 02.01

// @from 02.01
// virtio mmio interface
#define VIRTIO0 0x10001000
#define VIRTIO0_IRQ 1
// @end

// @from 08.01
// the network card, on the next virtio mmio slot (module 08). QEMU's virt
// machine has eight slots, 0x1000 bytes apart, raising irqs 1 to 8.
#define VIRTIO1 0x10002000
#define VIRTIO1_IRQ 2
// @end

// @from 09.03
// the keyboard and the mouse (module 09), on virtio mmio slots 2 and 3:
// each slot is 0x1000 bytes further on and raises the next irq. Slot 1
// belongs to the network card (module 08).
#define VIRTIO2 0x10003000
#define VIRTIO2_IRQ 3
#define VIRTIO3 0x10004000
#define VIRTIO3_IRQ 4
// @end

// @from 09.01
// QEMU's firmware configuration device, fw_cfg (module 09): a selector,
// a data register and a DMA address register, through which the kernel
// finds and sets up the ramfb screen.
#define FW_CFG 0x10100000L
// @end

// @from 02.01
// qemu puts the platform-level interrupt controller (PLIC) here.
#define PLIC 0x0c000000L
#define PLIC_PRIORITY (PLIC + 0x0)
#define PLIC_PENDING (PLIC + 0x1000)
#define PLIC_SENABLE(hart) (PLIC + 0x2080 + (hart)*0x100)
#define PLIC_SPRIORITY(hart) (PLIC + 0x201000 + (hart)*0x2000)
#define PLIC_SCLAIM(hart) (PLIC + 0x201004 + (hart)*0x2000)

// the kernel expects there to be RAM
// for use by the kernel and user pages
// from physical address 0x80000000 to PHYSTOP.
#define KERNBASE 0x80000000L
#define PHYSTOP (KERNBASE + 128*1024*1024)

// map the trampoline page to the highest address,
// in both user and kernel space.
#define TRAMPOLINE (MAXVA - PGSIZE)

// map kernel stacks beneath the trampoline,
// each surrounded by invalid guard pages.
#define KSTACK(p) (TRAMPOLINE - ((p)+1)* 2*PGSIZE)

// User memory layout.
// Address zero first:
//   text
//   original data and bss
//   fixed-size stack
//   expandable heap
//   ...
//   FBVA (the screen, if the process mapped it; module 09) @from 09.02
//   ... @from 09.02
//   TRAPFRAME (p->trapframe, used by the trampoline)
//   TRAMPOLINE (the same page as in the kernel)
#define TRAPFRAME (TRAMPOLINE - PGSIZE)
// @end

// @from 09.02
// Where fbmap() puts the screen in a process that asks for it (module
// 09): at 1 GB, far above any heap a 128 MB machine can grow, far below
// the trapframe.
#define FBVA 0x40000000L
// @end
