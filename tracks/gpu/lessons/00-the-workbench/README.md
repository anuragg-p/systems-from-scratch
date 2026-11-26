---
id: 00
title: The workbench
---

# Module 00 - The workbench

Before anything fast is written, the two tools every later lesson leans on: a way to know an answer is right, and a way to know how long it took. A first function, adding two arrays, comes in two versions, a plain one you trust and one under test, working on numbers drawn from a seed so that every machine sees the same ones (00.01). A checker compares any answer with the plain version's, every element against its allowance, and names the element furthest off (00.02). A timer throws away a first call, repeats the rest, and reports the fastest run, in bytes moved a second (00.03). Everything here is C on the CPU and runs on any laptop with a C compiler; it stands on nothing earlier. Three of its files stay for the whole track: check.c, bench.c and rng.c.
