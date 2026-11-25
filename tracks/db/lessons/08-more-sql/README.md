---
id: 08
title: More SQL
optional: true
---

# Module 08 - More SQL

This module is optional: it stands on the finished core, modules 00 to 07, and nothing in the core needs it. Until now every query read one table and gave back some of its rows. This module adds the questions people really ask, on one small shop of customers and orders. First rows from several tables: a join as two nested loops, every name bound to the table it means and each condition checked as soon as its tables are in the row; then LEFT JOIN and the row of NULLs it makes for a customer with no orders; then an index lookup in place of the inner loop, and what the order the tables are written in costs. Then one row from many: count, sum, total, avg, min and max, then GROUP BY, which finds its groups by sorting, HAVING, and DISTINCT. Then a query inside a query, run once or once for every outer row, and why NOT IN with a NULL in its set returns nothing. Last, UNIQUE, a rule kept by looking in an index before every write. It stands on the operators of module 04 (a join and an aggregate are new operators in their tree) and the indexes and planner of module 05, and every answer is still sqlite3's, in a file sqlite3 still opens. After it, one query joins customers to their orders and adds them up by city: London, 4 orders, 100 in all.
