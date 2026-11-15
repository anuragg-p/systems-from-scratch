---
id: 01
title: Counting words: freq
---

# Module 01 - Counting words: freq

This module builds the first tool and the two structures most later tools stand on. freq prints the most common words of a text, with the same counts as the shell pipeline it copies, `tr`, `sort`, `uniq -c` and `sort -rn`. It starts the obvious way: its words in a growable array, which moves to a block twice its size when full, and each new word searched for among all those seen so far. That is quick on a book and takes five seconds on half a million words, growing faster than the text. A hash table replaces the search. The first one, which adds up a word's bytes to pick one of 1024 buckets, compares each word with 119 times fewer others on the book, and is quadratic again on a big text; a hash that stirs every bit (FNV-1a) and buckets that double as words come make a lookup about one probe, and freq linear: two million words in a quarter of a second, a third of the pipeline's time. It stands on module 00's build, counters and growth harness. The array goes on to hold sort's lines in module 02, and the hash table comes back in grep, spell, diff, make and git.
