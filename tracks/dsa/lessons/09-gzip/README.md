---
id: 09
title: Making files smaller: gzip
---

# Module 09 - Making files smaller: gzip

This module builds gunzip and then gzip, to RFC 1951 and RFC 1952: the system's gunzip opens the files ours writes, and ours opens the files the system's gzip writes, checked against the CRC-32 in their trailers. Compression here is two ideas, each fixing what the obvious way leaves on the table. A fixed-length code spends the same bits on 'e' as on 'Z'; Huffman's greedy tree, built with the heap of module 02, gives common bytes short codes and takes the book to 56% of its size on its own. Inflate then reads a real gzip file exactly, bit by bit, with a table that decodes the short codes in one look. Text repeats itself, so LZ77 writes a repeat as a pointer back to its earlier copy; trying every earlier place in the 32 KB window takes 3 seconds on the book, and a hash table of three-byte strings, a fixed-size cousin of module 01's, finds the same matches in a hundredth of that. Deflate puts the two together, prices every block in its three possible forms and writes the cheapest, and keeps every code within the 15 bits the format can state. After this module gzip makes the book 40% of its size, within 3% of the system's gzip, and module 10's git stores its objects with this same inflate and deflate.
