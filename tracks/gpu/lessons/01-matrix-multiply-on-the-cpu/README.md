---
id: 01
title: Matrix multiply on the CPU
---

# Module 01 - Matrix multiply on the CPU

One operation, the one a language model spends most of its arithmetic on, written as three plain loops beside a reference that keeps every sum in a double, with a tolerance for how far a float answer may drift from it (01.01). Then made faster four times over, each step checked against that reference before it is timed: by the order memory is read in (01.02), by several floats in one instruction (01.03), by tiles that keep the data in use in the cache (01.04), and by every core (01.05). Last, the system's own BLAS goes in the same table, to measure the distance left and what a library does to cover it. It stands on module 00: the checker, now with a tolerance, and the timer, now reporting GFLOP/s. Everything is still C on the CPU, in one program, mm, that lists, checks and times every variant.
