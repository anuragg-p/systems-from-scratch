# Context switch.
#
#   void swtch(struct context *old, struct context *new);
#
# Save current registers in old. Load from new.
#
# This is the entire mechanism behind "running many processes on one
# CPU". swtch is called like an ordinary function, so the caller has
# already saved the caller-saved registers on its own stack; only ra, sp
# and the callee-saved s0-s11 need saving here. Loading a different sp
# and ra and executing ret "returns" into a different thread's call to
# swtch - on a different stack.

.section .text
.globl swtch
swtch:
        # @build 04.02 swtch
        # a0 points at the old struct context, a1 at the new one (see
        # proc.h for the order). Store ra, sp and s0-s11 into *a0, load the
        # same registers from *a1, and ret: you "return" into whoever saved
        # the new context, on their stack.
        # @stub la a0, swtch_todo; call panic
        sd ra, 0(a0)
        sd sp, 8(a0)
        sd s0, 16(a0)
        sd s1, 24(a0)
        sd s2, 32(a0)
        sd s3, 40(a0)
        sd s4, 48(a0)
        sd s5, 56(a0)
        sd s6, 64(a0)
        sd s7, 72(a0)
        sd s8, 80(a0)
        sd s9, 88(a0)
        sd s10, 96(a0)
        sd s11, 104(a0)

        ld ra, 0(a1)
        ld sp, 8(a1)
        ld s0, 16(a1)
        ld s1, 24(a1)
        ld s2, 32(a1)
        ld s3, 40(a1)
        ld s4, 48(a1)
        ld s5, 56(a1)
        ld s6, 64(a1)
        ld s7, 72(a1)
        ld s8, 80(a1)
        ld s9, 88(a1)
        ld s10, 96(a1)
        ld s11, 104(a1)

        ret
        # @end

# @internal
.section .rodata
swtch_todo:
        .string "04.02: swtch not written yet"
# @end
