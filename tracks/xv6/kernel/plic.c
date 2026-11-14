// The PLIC, the platform-level interrupt controller.
//
// Devices do not interrupt a hart directly. Each device raises a numbered
// line into the PLIC, and the PLIC decides which harts to signal. A hart
// then "claims" the interrupt to learn which device it was, handles it,
// and "completes" it so the PLIC will deliver that device's next one.
//
// The lines this kernel takes interrupts from (memlayout.h):
//   10  the UART
//   1   the virtio disk @from 05.01
//   2   the network card @from 08.01
//   3   the keyboard @from 09.03
//   4   the mouse @from 09.03

#include "kernel/types.h"
#include "kernel/param.h"
#include "kernel/memlayout.h"
#include "kernel/riscv.h"
#include "kernel/defs.h"

void
plicinit(void)
{
  // set desired IRQ priorities non-zero (otherwise disabled).
  *(uint32*)(PLIC + UART0_IRQ*4) = 1;
  *(uint32*)(PLIC + VIRTIO0_IRQ*4) = 1;  // @from 05.01
  *(uint32*)(PLIC + VIRTIO1_IRQ*4) = 1;  // @from 08.01
  *(uint32*)(PLIC + VIRTIO2_IRQ*4) = 1;  // @from 09.03
  *(uint32*)(PLIC + VIRTIO3_IRQ*4) = 1;  // @from 09.03
}

void
plicinithart(void)
{
  int hart = cpuid();

  // set enable bits for this hart's S-mode,
  // one for each of those lines.
  uint32 enable = 1 << UART0_IRQ;
  enable |= 1 << VIRTIO0_IRQ;  // @from 05.01
  enable |= 1 << VIRTIO1_IRQ;  // @from 08.01
  enable |= (1 << VIRTIO2_IRQ) | (1 << VIRTIO3_IRQ);  // @from 09.03
  *(uint32*)PLIC_SENABLE(hart) = enable;

  // set this hart's S-mode priority threshold to 0.
  *(uint32*)PLIC_SPRIORITY(hart) = 0;
}

// ask the PLIC what interrupt we should serve.
int
plic_claim(void)
{
  // @build 03.03 plic_claim
  // Ask the PLIC which device interrupted this hart: read this hart's
  // claim register, PLIC_SCLAIM(cpuid()). 0 means none.
  int hart = cpuid();
  int irq = *(uint32*)PLIC_SCLAIM(hart);
  return irq;
  // @end
}

// tell the PLIC we've served this IRQ.
void
plic_complete(int irq)
{
  // @build 03.03 plic_complete
  // Tell the PLIC this hart is done with irq by writing it back to the
  // same claim register. Until then the device cannot interrupt again.
  int hart = cpuid();
  *(uint32*)PLIC_SCLAIM(hart) = irq;
  // @end
}
