---
id: 06
title: Transactions
---

# Module 06 - Transactions

A commit writes many pages, and until now a crash between two of them left the file half old and half new. This module first makes that happen on purpose and looks at the damage, then makes commits atomic and durable in two ways: a rollback journal that saves the original pages before the database is overwritten, with recovery that puts them back the next time the file is opened, and a write-ahead log that appends new pages instead and copies them home at a checkpoint. Both use SQLite's own file formats, so sqlite3 recovers a crash of this engine and this engine recovers a crash of sqlite3. It stands on the pager of module 01, which already keeps every change in memory until COMMIT; the journal and the log decide only how those pages reach the file.
