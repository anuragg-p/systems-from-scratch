---
id: 02
title: Expressions
---

# Module 02 - Expressions

Module 01 left the compiler reading tokens, with errors that point at the source, but still compiling only sums, by walking the tokens left to right. This module gives it the two phases that make it a compiler in shape. The parser reads the tokens as a grammar says, one function to a rule, and builds a syntax tree whose shape is C's precedence and associativity: the operator that binds tighter sits deeper. The code generator walks that tree and writes RISC-V instructions, keeping the values that wait for their operators in registers used as a stack, and in memory once the registers run out. Level by level the grammar grows to C's whole ladder of binary operators, with the unary ones under it. After this module the compiler turns any integer expression of C's arithmetic, bitwise, shift and comparison operators, nested as deep as you like, into a program that runs on the bare machine of module 00 and gives gcc's answer wherever the values fit in a C `int`.
