---
id: 06
title: Syntax highlighting
optional: true
---

# Module 06 - Syntax highlighting

This module is optional: it stands on the finished core, modules 00 to 05, and nothing in the core needs it. The core editor opens, edits, saves and searches a file in one colour. This module gives every character of a row a colour. Each row keeps a highlight class for every character of its render, worked out whenever the row's text changes and read when the frame is drawn. The first lesson adds that array, the table that turns a class into a terminal colour, and the table of languages kilo knows, with the choice of one by the file's name. The next three teach the scanner numbers and strings; comments, where a comment that spans rows makes a row's colours depend on the row above it, so one keystroke can recolour the rest of the file; and keywords. The last colours a search's match and puts the row's colours back afterwards. It is antirez's own highlighting, cut out of the core and restored here, with the bugs found in it fixed and each one shown in its lesson. After this module a C file opens in colour, and its colours stay right while you edit it.
