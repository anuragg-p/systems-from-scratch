---
id: 04
title: Finding text: grep
---

# Module 04 - Finding text: grep

This module builds grep, which prints the lines of a text that match a pattern, with the same lines as the system's `grep -F` and `grep -E`. It starts with a fixed string. The obvious search tries the string at every position and reads every byte; Horspool's compares from the string's end and skips ahead, and reads a tenth of the book for a 15-byte string. Neither ever stops being usable on ordinary text, each has an input of its own that makes it slow, and macOS's own `grep -F` falls into one of them. Then regular expressions: a parser turns the pattern into a tree, one function for each rule of the grammar, and a backtracking matcher walks the tree, as the regex libraries of Perl, Python and Ruby do, until a pattern someone would really write, lines made only of words, needs hours for one line of the book. Thompson's construction turns the tree into a machine that is run in all its states at once, so that each byte is read once; a DFA built as it runs then remembers each set of those states the first time it comes up, finding it again through the hash table of module 01, and most bytes cost one lookup. The DFA's cache is bounded, and the module ends on the patterns that overflow it, where the plain NFA wins. It stands on module 01's array and hash table, and on module 00's workbench, whose generator makes the large texts every measurement here runs on.
