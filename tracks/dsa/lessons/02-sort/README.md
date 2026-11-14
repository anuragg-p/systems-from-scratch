---
id: 02
title: Putting things in order: sort
---

# Module 02 - Putting things in order: sort

Module 01 counted words with a growable array and a hash table; this module puts lines in order, and builds the track's second tool on that array. `sort` prints the same bytes as the system's sort. It starts the obvious way, with insertion sort, which is fine for the book's lines and takes hours for a few million; merge sort takes it to millions of lines in a second or two; quicksort sorts in place, and shows how one input, a file already in order, can make the obvious version as slow as insertion sort, and how a random pivot and a three-way split take that power away from any input. A heap gives freq its most common words in one pass instead of one pass per word, and gives sort heapsort; the same heap then merges sorted runs written to disk, so that sort can take a file bigger than the memory it is allowed. The module ends with a second tool, `look`, which finds the lines of a sorted file that begin with a string by binary search, reading a few blocks where a scan reads them all. After this module the library can sort anything it is given a comparison for and keep the smallest of a stream at hand, which route, gzip and git will need again.
