---
id: 02
title: The screen
---

# Module 02 - The screen

Module 01 left the editor in raw mode, reading whole keys and knowing the size of its window, but all it could show was a line of text per key, scrolling up the terminal. This module gives it a screen of its own. After every key the editor builds the whole screen in memory, a line at a time, with escape sequences that move the cursor and erase each line as it goes, and hands it to the terminal in one write, so the terminal never shows half of it; when the window changes size, it draws again at once. After this module the editor shows a column of tildes and a welcome line that it redraws on every key, and everything the later modules add, the rows of a file, the cursor, the status bar, edits and search, is something new drawn into that same frame.
