---
id: 00
title: The workbench
---

# Module 00 - The workbench

The whole engine, before any part of it is built. 00.01 follows one SELECT from the text you type down to the bytes in the file and back, names each layer on the way, and explains why the track builds them from the bottom up, starting at the file; then it builds the finished `./db`, runs it, and opens the same file with the real sqlite3. 00.02 runs the benchmark that holds `./db` against sqlite3 on the same work, and shows how each of its numbers is made. After this module you know what every layer is for, how to run and check the engine, and how to tell whether a change made it faster. It stands on nothing: this is where the track starts.
