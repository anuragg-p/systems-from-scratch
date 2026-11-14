---
id: dsa
title: Data structures and algorithms, by building the tools that use them
kind: algorithms
status: coming soon
audience: Programmers who use sort, grep, diff, make, gzip and git every day and want to know what is inside them.
prerequisites: C at the level of pointers and structs, and comfort with a terminal. No algorithms course needed.
outcome: Ten working tools in C - freq, sort, edit, grep, spell, diff, make, route, gzip and git - on a library of data structures you wrote, each checked against the real tool it copies.
upstream: Proposed, not decided: [git](https://github.com/git/git) (GPL-2.0) for the repository format the capstone writes, with no code taken; [zlib](https://github.com/madler/zlib) (Zlib) for the DEFLATE and gzip formats; [toybox](https://github.com/landley/toybox) (0BSD) for small, readable versions of the Unix tools to read beside ours; [kilo](https://github.com/antirez/kilo) (BSD-2-Clause) for the terminal editor; [re2](https://github.com/google/re2) (BSD-3-Clause) for regular expressions run as automata.
---

# Data structures and algorithms, by building the tools that use them

You do not start from a structure and look for a use. You start from a
tool you already use, write it the obvious way, and watch it stop
finishing on real input. The structure or the algorithm is what makes it
finish, and you measure the difference yourself. Every tool is checked
against the real one: the system's gunzip opens the file your gzip wrote,
patch applies your diff, and git reads the repository your git made.

**Coming soon.** This is the outline: the direction, not the lessons yet.
Format: `templates/outline.md`.

## Module 00 - The workbench

- Goal: Tell by measuring, not by guessing, whether a program will still finish when its input is a thousand times bigger.
- You build: The same small job written a slow way and a fast way, and a harness that doubles the input and reports how the running time grows.
- Value: The harness judges every tool in the track, and any slow program you meet after it.
- Lessons:
  - 00.01 One job, done slow and done fast
  - 00.02 Measuring growth
- Learn from: [B-PEARLS], [B-SEDG], [K-6006]

## Module 01 - Counting words: freq

- Goal: Understand how a table finds a thing by its name in the same time among a thousand entries or a million.
- You build: `freq`, which prints the most common words in a text, on your own growable array and hash table, with the same answer as `sort | uniq -c`.
- Value: The array and the table are the two structures every later tool is built on, and the ones behind the list and the dictionary of any language.
- Lessons:
  - 01.01 A growable array
  - 01.02 A hash table
  - 01.03 Hash functions, collisions and resizing
- Learn from: [P-LITERATE], [A-CRAFT], [B-OPENDS], [B-SEDG]

## Module 02 - Putting things in order: sort

- Goal: Know several ways to sort, what each one costs, and how to sort more data than fits in memory.
- You build: `sort`, with output byte for byte the same as the system's sort, a heap for "the top ten" and a merge of sorted runs for files bigger than memory.
- Value: Sorted data is what makes searching, merging and removing duplicates cheap, and the heap comes back in three later tools.
- Lessons:
  - 02.01 Insertion sort, and where it stops being enough
  - 02.02 Merge sort
  - 02.03 Quicksort, and the input that breaks it
  - 02.04 A heap, and the top ten without sorting everything
  - 02.05 Sorting a file bigger than memory
  - 02.06 Binary search in a sorted file
- Learn from: [B-SEDG], [B-CLRS], [B-TAOCP3], [P-KILLER], [C-TOYBOX]

## Module 03 - A text editor: edit

- Goal: See how the structure that holds the text decides whether a keystroke costs the same in a ten-line file as in a ten-million-line one.
- You build: `edit`, a terminal text editor you can really use, with its text moved off an array, first onto a gap buffer, then onto a piece table kept in a balanced tree, with undo and redo.
- Value: Sequences, stacks, linked lists and balanced trees in one program; the piece table is what holds the text in Visual Studio Code.
- Lessons:
  - 03.01 An editor, and its text in one array
  - 03.02 The gap buffer
  - 03.03 Undo and redo: two stacks
  - 03.04 The piece table: a list of pieces
  - 03.05 The pieces in a balanced tree
- Learn from: [A-KILO], [P-CROWLEY], [A-VSCODE], [B-OPENDS], [B-CLRS], [C-KILO]

## Module 04 - Finding text: grep

- Goal: Understand a pattern as a small machine, and why running that machine reads each character of the input once.
- You build: `grep`, with a fixed-string search that skips ahead and regular expressions compiled to an automaton, printing the same lines as `grep -E`.
- Value: The same machine is inside every lexer, router and input validator, and it is the reason some regex engines can be made to hang and others cannot.
- Lessons:
  - 04.01 Searching for a string, and skipping ahead
  - 04.02 Parsing a regular expression
  - 04.03 The pattern as a machine: an NFA
  - 04.04 Caching the states: a DFA built as it runs
- Learn from: [A-COX], [A-KERN], [B-TPOP], [A-HAERTEL], [P-THOMPSON], [C-RE2]

## Module 05 - Checking spelling: spell

- Goal: Know how to store a dictionary so that a prefix is one walk down a tree, how to trade a small error rate for most of the memory, and how to measure the distance between two words.
- You build: `spell`, which lists the words in a text that are not in the dictionary, suggests the nearest ones, and completes a prefix.
- Value: Completion, "did you mean" and a cheap "definitely not here" test are in every search box, and the last one guards the disk reads of most storage engines.
- Lessons:
  - 05.01 A trie, and completing a prefix
  - 05.02 A Bloom filter: the dictionary in far less memory
  - 05.03 Edit distance, and "did you mean"
- Learn from: [P-SPELL], [B-PEARLS], [P-BLOOM], [B-SKIENA]

## Module 06 - Comparing files: diff

- Goal: Understand dynamic programming as filling in a table of smaller answers, and then how to reach the same answer without the whole table.
- You build: `diff` and `patch`: the system's patch applies what your diff prints, and your patch applies what the system's diff prints.
- Value: The table is the method behind alignment, spell checking and many scheduling problems; the diff is what code review and version control stand on.
- Lessons:
  - 06.01 The longest common subsequence, as a table
  - 06.02 From the table to hunks: unified output
  - 06.03 Myers: the shortest path of edits
  - 06.04 patch: applying a diff
- Learn from: [P-MYERS], [A-COGLAN], [B-CLRS], [B-ERICKSON]

## Module 07 - Building in order: make

- Goal: See dependencies as a graph, and walk it so that everything is built after what it needs and nothing is built twice.
- You build: `make`, which reads a makefile, rebuilds only what is out of date, runs independent steps in parallel, and builds this track's own tools.
- Value: Build systems, package managers, spreadsheets and task schedulers are all this one walk over a graph.
- Lessons:
  - 07.01 A makefile as a graph
  - 07.02 Depth-first search, and finding a cycle
  - 07.03 Topological order, and what is out of date
  - 07.04 Building in parallel: a queue of ready work
- Learn from: [P-MAKE], [B-SEDG], [B-ERICKSON], [K-6006]

## Module 08 - Finding the way: route

- Goal: Know how to find the shortest path when the edges have lengths, and how a good guess lets the search look at far less of the map.
- You build: `route`, which finds the shortest route between two points on the road map of a real city and draws it, using the heap from module 02.
- Value: The same search runs in maps, network routing and games, and it is the usual first answer to "what is the cheapest way from here to there".
- Lessons:
  - 08.01 A road map as a graph
  - 08.02 Breadth-first search: the fewest junctions
  - 08.03 Dijkstra, with a heap
  - 08.04 A*: searching towards the goal
- Learn from: [A-REDBLOB], [B-SEDG], [B-CLRS], [B-SKIENA]

## Module 09 - Making files smaller: gzip

- Goal: Understand compression as two ideas: short codes for common symbols, and pointing back at text already seen.
- You build: `gunzip` and then `gzip`: yours opens what the system's wrote, and the system's opens what yours wrote.
- Value: DEFLATE is in every zip file, PNG image and compressed web response; Huffman's tree is the standard example of a greedy choice that is provably right.
- Lessons:
  - 09.01 Huffman codes: a greedy tree
  - 09.02 Inflate: reading a real gzip file
  - 09.03 LZ77: finding repeats with a hash table
  - 09.04 Deflate: writing a file gunzip accepts
- Learn from: [A-RFC1951], [A-RFC1952], [A-FELDSPAR], [P-HUFFMAN], [C-ZLIB]

## Module 10 - Capstone: git

- Goal: See the structures work together: objects named by their hash, directories as trees, history as a graph.
- You build: `git` with init, add, commit, log, diff and merge-base, on your own hash table, sort, heap, diff and deflate, writing a repository the real git reads and checks.
- Value: You can say what git does on every command you type, and you have ten tools in public that show what you can build.
- Lessons:
  - 10.01 Objects: a hash is a name
  - 10.02 Trees and the index: a directory as a hash
  - 10.03 Commits: walking a graph for log
  - 10.04 diff between commits, and the merge base
- Learn from: [B-PROGIT], [B-BGIT], [A-COGLAN], [C-GIT]

## Library

| Key | Kind | Title | By | Where |
|---|---|---|---|---|
| B-SEDG | book | Algorithms, 4th edition | Robert Sedgewick, Kevin Wayne | Addison-Wesley, 2011; site at https://algs4.cs.princeton.edu |
| B-CLRS | book | Introduction to Algorithms, 4th edition | Cormen, Leiserson, Rivest, Stein | MIT Press, 2022 |
| B-SKIENA | book | The Algorithm Design Manual, 3rd edition | Steven Skiena | Springer, 2020; site at https://www.algorist.com |
| B-ERICKSON | book | Algorithms | Jeff Erickson | 2019; free at https://jeffe.cs.illinois.edu/teaching/algorithms/ |
| B-OPENDS | book | Open Data Structures | Pat Morin | free at https://opendatastructures.org |
| B-PEARLS | book | Programming Pearls, 2nd edition | Jon Bentley | Addison-Wesley, 1999 |
| B-TPOP | book | The Practice of Programming | Brian Kernighan, Rob Pike | Addison-Wesley, 1999 |
| B-TAOCP3 | book | The Art of Computer Programming, Volume 3: Sorting and Searching, 2nd edition | Donald Knuth | Addison-Wesley, 1998 |
| B-PROGIT | book | Pro Git, 2nd edition (chapter 10, Git Internals) | Scott Chacon, Ben Straub | Apress, 2014; free at https://git-scm.com/book/en/v2/Git-Internals-Git-Objects |
| B-BGIT | book | Building Git | James Coglan | 2019; https://shop.jcoglan.com/building-git/ |
| K-6006 | course | Introduction to Algorithms (MIT 6.006, Spring 2020) | Erik Demaine, Jason Ku, Justin Solomon | https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/ |
| A-CRAFT | article | Crafting Interpreters, chapter 20: Hash Tables | Robert Nystrom | https://craftinginterpreters.com/hash-tables.html |
| A-KILO | article | Build Your Own Text Editor | Paige Ruten | https://viewsourcecode.org/snaptoken/kilo/ |
| A-VSCODE | article | Text Buffer Reimplementation | Peng Lyu, Visual Studio Code | https://code.visualstudio.com/blogs/2018/03/23/text-buffer-reimplementation |
| A-COX | article | Regular Expression Matching Can Be Simple And Fast | Russ Cox | https://swtch.com/~rsc/regexp/regexp1.html |
| A-KERN | article | A Regular Expression Matcher | Brian Kernighan | https://www.cs.princeton.edu/courses/archive/spr09/cos333/beautiful.html |
| A-HAERTEL | article | why GNU grep is fast | Mike Haertel | https://lists.freebsd.org/pipermail/freebsd-current/2010-August/019310.html |
| A-COGLAN | article | The Myers diff algorithm | James Coglan | https://blog.jcoglan.com/2017/02/12/the-myers-diff-algorithm-part-1/ |
| A-REDBLOB | article | Introduction to the A* Algorithm | Amit Patel, Red Blob Games | https://www.redblobgames.com/pathfinding/a-star/introduction.html |
| A-RFC1951 | article | RFC 1951: DEFLATE Compressed Data Format Specification | Peter Deutsch | https://www.rfc-editor.org/rfc/rfc1951 |
| A-RFC1952 | article | RFC 1952: GZIP File Format Specification | Peter Deutsch | https://www.rfc-editor.org/rfc/rfc1952 |
| A-FELDSPAR | article | An Explanation of the Deflate Algorithm | Antaeus Feldspar | https://zlib.net/feldspar.html |
| P-LITERATE | paper | Programming Pearls: A Literate Program | Jon Bentley, Donald Knuth, Doug McIlroy, 1986 | https://doi.org/10.1145/5948.315654 |
| P-KILLER | paper | A Killer Adversary for Quicksort | Doug McIlroy, 1999 | https://www.cs.dartmouth.edu/~doug/mdmspe.pdf |
| P-CROWLEY | paper | Data Structures for Text Sequences | Charles Crowley, 1998 | https://www.cs.unm.edu/~crowley/papers/sds.pdf |
| P-THOMPSON | paper | Regular Expression Search Algorithm | Ken Thompson, 1968 | https://doi.org/10.1145/363347.363387 |
| P-SPELL | paper | Development of a Spelling List | Doug McIlroy, 1982 | https://www.cs.dartmouth.edu/~doug/spell.pdf |
| P-BLOOM | paper | Space/Time Trade-offs in Hash Coding with Allowable Errors | Burton Bloom, 1970 | https://doi.org/10.1145/362686.362692 |
| P-MYERS | paper | An O(ND) Difference Algorithm and Its Variations | Eugene Myers, 1986 | http://www.xmailserver.org/diff2.pdf |
| P-MAKE | paper | Make: A Program for Maintaining Computer Programs | Stuart Feldman, 1979 | Software: Practice and Experience 9(4) |
| P-HUFFMAN | paper | A Method for the Construction of Minimum-Redundancy Codes | David Huffman, 1952 | Proceedings of the IRE 40(9) |
| C-TOYBOX | code | toybox | Rob Landley and contributors | https://github.com/landley/toybox |
| C-KILO | code | kilo | Salvatore Sanfilippo | https://github.com/antirez/kilo |
| C-RE2 | code | RE2 | Google and contributors | https://github.com/google/re2 |
| C-ZLIB | code | zlib | Jean-loup Gailly, Mark Adler | https://github.com/madler/zlib |
| C-GIT | code | git | Linus Torvalds, Junio Hamano and contributors | https://github.com/git/git |
