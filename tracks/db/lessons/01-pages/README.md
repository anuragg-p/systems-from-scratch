---
id: 01
title: Pages
---

# Module 01 - Pages

The bottom of the stack, standing on module 00's picture of the whole engine. The database file becomes a row of numbered 4096-byte pages, read and written whole, with the 100-byte header that makes it a SQLite database (01.01); a cache keeps the pages in use in memory and holds changed ones there until they are committed (01.02); and rows become records, short runs of bytes built from varints and serial types exactly as sqlite3 builds them (01.03). After this module the engine can make and read every byte of a SQLite file's pages and rows, though it cannot yet find a row among them: that is the B-tree, module 02.
