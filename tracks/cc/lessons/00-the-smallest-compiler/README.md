---
id: 00
title: The smallest compiler
---

# Module 00 - The smallest compiler

A compiler for the smallest language there is, a file that holds one number, and the whole road from its output to a result. 00.01 builds the compiler: it reads the file and writes four lines of RISC-V assembly, and it follows that number through every stage the finished system has. 00.02 takes the assembly the rest of the way by hand, through the assembler and the linker to a bare RISC-V machine in QEMU, with 31 lines of start-up code standing in for an operating system, and the number comes back as the program's exit status. 00.03 builds the same source with gcc for the same machine and compares the two statuses, the habit the whole track keeps. After this module a number in a file becomes a program that runs and returns it, and every program the compiler makes from now on can be checked against gcc's. It stands on nothing but a C compiler on your computer, the RISC-V toolchain and QEMU: this is where the track starts, and modules 01 and 02 grow the compiler inside a road that already works.
