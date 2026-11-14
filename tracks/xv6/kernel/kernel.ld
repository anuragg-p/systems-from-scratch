/*
 * Linker script for the kernel.
 *
 * QEMU's virt machine puts RAM at 0x80000000 and, with -bios none, jumps
 * there on every hart. So the kernel is linked to run at exactly that
 * address, with _entry (kernel/entry.S) as the very first byte.
 */
OUTPUT_ARCH( "riscv" )
ENTRY( _entry )

SECTIONS
{
  . = 0x80000000;

  .text : {
    *(.text .text.*)
    /* @from 06.01 */
    /*
     * The trampoline (kernel/trampoline.S) gets a page of its own. It is
     * mapped at the top of every address space, user and kernel, so it
     * must not share a page with anything else.
     */
    /* @end */
    . = ALIGN(0x1000);
    /* @from 06.01 */
    _trampoline = .;
    *(trampsec)
    . = ALIGN(0x1000);
    ASSERT(. - _trampoline == 0x1000, "error: trampoline larger than one page");
    /* @end */
    PROVIDE(etext = .);
  }

  .rodata : {
    . = ALIGN(16);
    *(.srodata .srodata.*)
    . = ALIGN(16);
    *(.rodata .rodata.*)
  }

  .data : {
    . = ALIGN(16);
    *(.sdata .sdata.*)
    . = ALIGN(16);
    *(.data .data.*)
  }

  .bss : {
    . = ALIGN(16);
    *(.sbss .sbss.*)
    . = ALIGN(16);
    *(.bss .bss.*)
  }

  /* First address after the kernel: the RAM from here up is free. */
  PROVIDE(end = .);
}
