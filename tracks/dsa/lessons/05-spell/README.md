---
id: 05
title: Checking spelling: spell
---

# Module 05 - Checking spelling: spell

This module builds spell, which prints the words of a text that are not in its dictionary of 60388 English words, completes a prefix from that dictionary, and suggests the nearest words for each misspelling. Each lesson starts from the obvious way and the point where it stops being good enough. A list of the words takes four seconds to check one book; the hash table of module 01 makes the check instant but cannot complete a prefix without looking at every word, so the dictionary goes into a trie, where words that start the same share a path. The trie is fifty times the size of the word list as text, so for the check alone spell can use a Bloom filter instead: 72 KB for the whole dictionary, at the price of letting about one misspelling in a hundred through. Then the edit distance, the track's first dynamic programming, says how far a dictionary word is from a misspelling, and a walk down the trie that drops every branch already too far away finds the nearest words more than thirty times faster than trying them all. It stands on modules 01 and 02: the growable array holds the trie's nodes, the hash function of 01.03 picks the filter's bits, and merge sort puts the output in order. After this module spell does what Unix spell and a search box's "did you mean" do, and module 06's diff fills the same kind of table as the edit distance, for lines instead of letters.
