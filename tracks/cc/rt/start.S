# rt/start.S: the first instructions the machine runs. There is no kernel
# and no firmware under the program (QEMU runs with -bios none), so this is
# all there is between the machine starting and main: give main a stack,
# call it, and hand what it returns to QEMU, which exits with it.
#
# QEMU's virt machine has a test device at 0x100000: a 32-bit store there
# stops the machine. 0x5555 means "passed", and QEMU exits with status 0;
# 0x3333 with a code in the upper 16 bits means "failed", and QEMU exits
# with that code. A Unix status is 8 bits, so only main's low byte counts:
# 0 becomes 0x5555, anything else (status << 16) | 0x3333.
#
# Plain assembly: as reads it directly, with no C preprocessor first.

  .section .text.start          # link.ld puts this first, at 0x80000000
  .globl _start
_start:
  la sp, stack_top              # the stack grows down from the top of its room
  call main

  andi a0, a0, 0xff             # the status: main's low 8 bits
  li t0, 0x5555                 # 0: passed
  beqz a0, 1f
  slli a0, a0, 16               # else (status << 16) | 0x3333: failed, with it
  li t1, 0x3333
  or t0, a0, t1
1:
  li t1, 0x100000               # the test device
  sw t0, 0(t1)

2:
  j 2b                          # QEMU has stopped; in case it has not, wait
