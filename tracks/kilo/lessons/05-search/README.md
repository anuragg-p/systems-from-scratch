---
id: 05
title: Search
---

# Module 05 - Search

Module 04 left an editor in which getting anywhere means pressing arrow keys. This module adds search. Ctrl-F turns the message line into a prompt; every key typed there searches the rows again from the top, and the first row holding the query jumps to the top of the screen with the cursor on the match. The second lesson makes the arrow keys step to the next or the previous matching row, around the ends of the file, and makes Escape put the cursor and the view back where they were. Search stands on the rows of module 03 and on the four numbers of 03.02 that place the cursor in the file; it reads the rows and changes none of them. With it the core of the track is complete: a terminal editor in one C file that opens, edits, saves and searches.
