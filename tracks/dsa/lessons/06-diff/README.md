---
id: 06
title: Comparing files: diff
---

# Module 06 - Comparing files: diff

This module builds diff and patch. diff says which lines changed between two versions of a file, by finding the lines they have in common, as many as can be kept in order: the longest common subsequence. It starts with a table of the answer for every pair of the files' ends, filled from the bottom right corner, which is dynamic programming as 05.03's edit distance did it, now over lines. The table is right and quick, and it needs four bytes for every pair of lines: 568 MB for the book against an edited copy, and a refusal at 1.7 MB a file. A walk back through the table gives the edit script, which diff prints as hunks of unified output, the same bytes as the system's `diff -u` on the files tried, and which the system's patch applies. Myers' search then finds an equally short script by spreading out from the start one edit at a time: on the pair the table refused it keeps 176 bytes of points where the table wanted 4.9 GB, and its time grows with the files, though on files that share almost nothing it is slower and hungrier than the table. Last comes patch, which places each hunk by its lines, searching near the stated line when the file has moved on, and changes nothing when a hunk does not fit. It stands on module 01's hash table, which numbers the lines so two lines compare as two numbers, and its growable array; git uses this diff in module 10.
