---
id: 02
title: The B-tree
---

# Module 02 - The B-tree

Module 01 gave the engine pages and records, but no way to decide which page a row belongs in or to find it again. This module builds that layer: every table, and later every index, becomes a B-tree of pages in SQLite's own format, with the rows sorted in leaf pages and interior pages above them as signposts, up to a root whose page number the catalog keeps. Lesson by lesson it reads a leaf and searches it, inserts and splits full pages, grows the tree at the root without moving it, walks the leaves in order with a cursor, and deletes rows while handing empty pages back through the freelist. After it, the engine can store a table of any size and find any row in a few page reads, in a file sqlite3 checks and reads; the SQL layers of modules 03 to 05 are built on top of it.
