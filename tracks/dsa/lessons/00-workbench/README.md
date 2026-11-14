---
id: 00
title: The workbench
---

# Module 00 - The workbench

This module sets up the bench that every tool of the track is built and measured on. It brings the build (one Makefile that archives the library in `lib/` and links each tool into `bin/`), the library's first file, with the counters every structure will print under `DS_STATS=1`, and a book to run on. Then it does one small job, joining a file's lines into one as `paste -s` does, in two ways that differ in a single line: the obvious way reads everything joined so far before each piece and is quadratic, the other remembers where the end is and is linear. Its second lesson adds the growth harness, which runs any command on inputs that double in size and reads off how its time grows, and the generator that makes those inputs, the same bytes on every machine. After this module you can tell by measuring, not by guessing, whether a program will still finish on an input a thousand times bigger. It stands on nothing: the track starts here.
