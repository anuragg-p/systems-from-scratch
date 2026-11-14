---
id: 04
title: Running queries
---

# Module 04 - Running queries

Module 03 turns a statement into a tree and knows where every table lives; module 02 stores rows in B-trees. This module runs the tree against the B-tree. A query becomes a small stack of operators, each handing the one above it one row at a time: a scan at the bottom reading the table in rowid order, a filter for WHERE with SQL's three-valued logic for NULL, a sort that must see every row before it hands out the first, and a limit that stops reading as soon as it has enough. INSERT turns values into records under a new rowid, and UPDATE and DELETE find their rows with the same operators before changing anything. After this module the engine answers SQL on one table, row for row as sqlite3 does; module 05 then makes it fast with indexes.
