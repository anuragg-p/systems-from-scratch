        #
        # Traps taken while in the kernel.
        #
        # trapinithart() points stvec here. When an interrupt or exception
        # happens in supervisor mode, the hardware: saves pc in sepc, the
        # reason in scause, the previous mode and interrupt-enable bit in
        # sstatus, disables interrupts, and jumps here - on whatever
        # kernel stack was in use. Nothing else is saved for us.
        #
        # So: push the caller-saved registers on that stack, call the C
        # handler kerneltrap() (which saves the rest, by the normal calling
        # convention), restore, and sret back to sepc.
        #
.section .text
.globl kerneltrap
.globl kernelvec
.align 4
kernelvec:
        # @build 03.01 kernelvec
        # The hardware jumped here and saved nothing but pc (in sepc). Make
        # room on the current stack (256 bytes), store the caller-saved
        # registers there - ra, gp, tp, t0-t6, a0-a7 - and call
        # kerneltrap(), which follows the calling convention and saves the
        # rest itself. Then load them all back (not tp: it holds the hart
        # id, which belongs to the hart and not to the interrupted code),
        # pop the frame, and sret to sepc.
        # @stub la a0, kernelvec_todo; call panic
        addi sp, sp, -256

        # save caller-saved registers.
        sd ra, 0(sp)
        # sd sp, 8(sp)
        sd gp, 16(sp)
        sd tp, 24(sp)
        sd t0, 32(sp)
        sd t1, 40(sp)
        sd t2, 48(sp)
        sd a0, 72(sp)
        sd a1, 80(sp)
        sd a2, 88(sp)
        sd a3, 96(sp)
        sd a4, 104(sp)
        sd a5, 112(sp)
        sd a6, 120(sp)
        sd a7, 128(sp)
        sd t3, 216(sp)
        sd t4, 224(sp)
        sd t5, 232(sp)
        sd t6, 240(sp)

        # call the C trap handler in trap.c
        call kerneltrap

        # restore registers.
        ld ra, 0(sp)
        # ld sp, 8(sp)
        ld gp, 16(sp)
        # @from 04.04
        # not tp (contains hartid), in case we moved CPUs
        # @else
        # # not tp (contains hartid): it belongs to this CPU
        # @end
        ld t0, 32(sp)
        ld t1, 40(sp)
        ld t2, 48(sp)
        ld a0, 72(sp)
        ld a1, 80(sp)
        ld a2, 88(sp)
        ld a3, 96(sp)
        ld a4, 104(sp)
        ld a5, 112(sp)
        ld a6, 120(sp)
        ld a7, 128(sp)
        ld t3, 216(sp)
        ld t4, 224(sp)
        ld t5, 232(sp)
        ld t6, 240(sp)

        addi sp, sp, 256

        # return to whatever we were doing in the kernel.
        sret
        # @end

# @internal
.section .rodata
kernelvec_todo:
        .string "03.01: kernelvec not written yet"
# @end
