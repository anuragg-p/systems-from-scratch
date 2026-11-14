        #
        # The trampoline: the code that crosses between
        # user space and kernel space.
        #
        # The problem it solves: a trap from user space arrives with the
        # user's page table still installed, and the hardware will not
        # switch page tables for us. So the first kernel instructions must
        # be mapped in the user page table - and must keep running at the
        # same address after we switch to the kernel page table. This page
        # is therefore mapped at the same virtual address, TRAMPOLINE, in
        # every user page table and in the kernel page table.
        #
        # It is never mapped with PTE_U, so user code cannot run it or
        # read it; the hardware only gets here through stvec.
        #

#include "kernel/riscv.h"
#include "kernel/memlayout.h"

.section trampsec
.globl trampoline
.globl usertrap
trampoline:
.align 4
.globl uservec
uservec:
        #
        # trap.c sets stvec to point here, so
        # traps from user space start here,
        # in supervisor mode, but with a
        # user page table.
        #
        # @build 06.01 uservec
        # Save every user register into the trapframe, which is mapped at
        # TRAPFRAME in every user page table. You need one register to hold
        # that address, so first park the user's a0 in sscratch. Store ra
        # through t6 at the offsets in proc.h, then the parked a0. Load the
        # kernel's sp, hartid (into tp), the address of usertrap and the
        # kernel satp from the trapframe; switch page tables (sfence.vma,
        # csrw satp, sfence.vma) and jalr to usertrap. This code keeps
        # running after the switch because the trampoline is mapped at the
        # same address in the kernel page table.
        # @stub j .
        csrw sscratch, a0

        # each process has a separate p->trapframe memory area,
        # but it's mapped to the same virtual address
        # (TRAPFRAME) in every process's user page table.
        li a0, TRAPFRAME

        # save the user registers in TRAPFRAME
        sd ra, 40(a0)
        sd sp, 48(a0)
        sd gp, 56(a0)
        sd tp, 64(a0)
        sd t0, 72(a0)
        sd t1, 80(a0)
        sd t2, 88(a0)
        sd s0, 96(a0)
        sd s1, 104(a0)
        sd a1, 120(a0)
        sd a2, 128(a0)
        sd a3, 136(a0)
        sd a4, 144(a0)
        sd a5, 152(a0)
        sd a6, 160(a0)
        sd a7, 168(a0)
        sd s2, 176(a0)
        sd s3, 184(a0)
        sd s4, 192(a0)
        sd s5, 200(a0)
        sd s6, 208(a0)
        sd s7, 216(a0)
        sd s8, 224(a0)
        sd s9, 232(a0)
        sd s10, 240(a0)
        sd s11, 248(a0)
        sd t3, 256(a0)
        sd t4, 264(a0)
        sd t5, 272(a0)
        sd t6, 280(a0)

        # save the user a0 in p->trapframe->a0
        csrr t0, sscratch
        sd t0, 112(a0)

        # initialize kernel stack pointer, from p->trapframe->kernel_sp
        ld sp, 8(a0)

        # make tp hold the current hartid, from p->trapframe->kernel_hartid
        ld tp, 32(a0)

        # load the address of usertrap(), from p->trapframe->kernel_trap
        ld t0, 16(a0)

        # fetch the kernel page table address, from p->trapframe->kernel_satp.
        ld t1, 0(a0)

        # wait for any previous memory operations to complete, so that
        # they use the user page table.
        sfence.vma zero, zero

        # install the kernel page table.
        csrw satp, t1

        # flush now-stale user entries from the TLB.
        sfence.vma zero, zero

        # call usertrap(). It returns the user satp to use on the way
        # back, in a0, and returns right here - to userret.
        jalr t0
        # @end

.globl userret
userret:
        # usertrap() returns here, with user satp in a0.
        # forkret() also jumps here, for a process's first trip to user space.

        # @build 06.01 userret
        # The way back: a0 holds the user satp. Switch to the user page
        # table (sfence.vma, csrw satp, sfence.vma), point a0 at TRAPFRAME,
        # load every user register back except a0, load a0 last, and sret -
        # prepare_return() already set sepc and sstatus.
        # @stub j .
        sfence.vma zero, zero
        csrw satp, a0
        sfence.vma zero, zero

        li a0, TRAPFRAME

        # restore all but a0 from TRAPFRAME
        ld ra, 40(a0)
        ld sp, 48(a0)
        ld gp, 56(a0)
        ld tp, 64(a0)
        ld t0, 72(a0)
        ld t1, 80(a0)
        ld t2, 88(a0)
        ld s0, 96(a0)
        ld s1, 104(a0)
        ld a1, 120(a0)
        ld a2, 128(a0)
        ld a3, 136(a0)
        ld a4, 144(a0)
        ld a5, 152(a0)
        ld a6, 160(a0)
        ld a7, 168(a0)
        ld s2, 176(a0)
        ld s3, 184(a0)
        ld s4, 192(a0)
        ld s5, 200(a0)
        ld s6, 208(a0)
        ld s7, 216(a0)
        ld s8, 224(a0)
        ld s9, 232(a0)
        ld s10, 240(a0)
        ld s11, 248(a0)
        ld t3, 256(a0)
        ld t4, 264(a0)
        ld t5, 272(a0)
        ld t6, 280(a0)

        # restore user a0
        ld a0, 112(a0)

        # return to user mode and user pc.
        # prepare_return() set up sstatus and sepc.
        sret
        # @end
