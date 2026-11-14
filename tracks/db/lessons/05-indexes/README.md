---
id: 05
title: Indexes and the planner
---

# Module 05 - Indexes and the planner

Until now every question about a column other than the rowid was answered by reading the whole table. This module adds indexes: a second B-tree per index, keyed by the indexed column and the rowid, filled when the index is created and kept in step by every INSERT, UPDATE and DELETE. Then come the operators that read a range of an index or of the rowids, and a small rule-based planner that looks at the WHERE clause, picks one of them, decides whether ORDER BY still needs a sort, and shows its choice with EXPLAIN and EXPLAIN QUERY PLAN in sqlite3's own words. It stands on the B-tree of module 02 (an index is made of the same pages) and the operators of module 04 (the planner chooses what sits at the bottom of their tree). After it, a lookup by an indexed value reads five pages instead of 252.
