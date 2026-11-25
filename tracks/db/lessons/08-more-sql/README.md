---
id: 08
title: More SQL
optional: true
---

# Module 08 - More SQL

This module is optional: it stands on the finished core, modules 00 to 07, and nothing in the core needs it. The core engine answers questions about one table, one row at a time. This module makes it answer the questions people really ask a database: rows from several tables at once, joined by a nested loop and then by an index lookup for each outer row; LEFT JOIN, and the row that matches nothing; one row from many, with count, sum, avg, min and max; GROUP BY, HAVING and DISTINCT; a query inside a query; and UNIQUE, a rule the database enforces with an index. Every answer is still sqlite3's answer, and the file is still one sqlite3 opens. It stands on the operators of module 04 (a join is one more operator in their tree) and the indexes and planner of module 05.
