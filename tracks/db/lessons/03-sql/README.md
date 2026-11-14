---
id: 03
title: SQL
---

# Module 03 - SQL

Up to here the engine stores rows in B-trees, but the only way in is C. This module builds the part that reads SQL: a tokenizer that cuts a statement into words, a parser that turns the words into a tree (with operator precedence settled, so `1 + 2 * 3` is 7), and the catalog, which records every table's name, columns and root page as rows of a table on page 1 of the file itself, exactly where sqlite3 keeps them. It stands on module 02: the catalog is just another B-tree. After it, CREATE TABLE works, a file written by sqlite3 opens with all its tables known, and every statement arrives as a tree ready for module 04 to run.
