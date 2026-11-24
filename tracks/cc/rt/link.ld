/* rt/link.ld: where the program sits in the machine's memory. QEMU's virt
 * machine has its RAM at 0x80000000, and with -bios none that is where it
 * starts running, so _start goes first, there. After the code come the
 * constants, the data and the zeroed data, then 64 KiB of stack: stack_top
 * is its top, since the stack grows down. */

OUTPUT_ARCH("riscv")
ENTRY(_start)

SECTIONS
{
  . = 0x80000000;

  .text : {
    *(.text.start)
    *(.text .text.*)
  }

  .rodata : {
    *(.rodata .rodata.* .srodata .srodata.*)
  }

  .data : {
    *(.data .data.* .sdata .sdata.*)
  }

  .bss : {
    *(.bss .bss.* .sbss .sbss.*)
    *(COMMON)
  }

  . = ALIGN(16);
  . = . + 0x10000;
  stack_top = .;
}
