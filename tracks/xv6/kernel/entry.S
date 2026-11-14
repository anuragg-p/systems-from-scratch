        # The first instruction.
        #
        # QEMU's boot ROM at 0x1000 jumps here, to 0x80000000, on every
        # hart at once. We are in machine mode, paging is off, and there is
        # no stack - so C cannot run yet. The only job of this file is to
        # @from 01.02
        # give each hart its own stack and call start() in start.c.
        # @else
        # # give each hart its own stack; with no C to call yet, each hart
        # # then spins.
        # @end

.section .text
.global _entry
_entry:
        # @build 01.01 a stack per hart
        # Every hart arrives here at the same moment, so each needs a stack
        # of its own before it can call C. stack0 (in start.c) has 4096
        # bytes per hart. Stacks grow down, so hart N's stack pointer starts
        # at the top of its slice: sp = stack0 + (N + 1) * 4096. The hart
        # number is in the mhartid CSR.
        # @stub j spin
        la sp, stack0
        li a0, 1024*4
        csrr a1, mhartid
        addi a1, a1, 1
        mul a0, a0, a1
        add sp, sp, a0
        # @end
        # @from 01.02
        # jump to start() in start.c
        call start
        # @end
spin:
        j spin
