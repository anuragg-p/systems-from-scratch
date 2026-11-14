---
id: 07
title: Fast
---

# Module 07 - Fast

The engine is complete; this module asks how good it is. It runs the benchmark against sqlite3 and reads it honestly, row by row: where this engine is faster and why (it skips work sqlite3 does to share a file between processes), and where it is slower and why (it rewrites a whole page to remove one cell, and builds indexes that are half empty). Then it finds where the time and the bytes go with the engine's own counters and a sampling profiler, and ends with one optimisation chosen from that evidence and measured: how a page splits when rows arrive in rowid order. It stands on everything before it, and on the benchmark harness of 00.02.
