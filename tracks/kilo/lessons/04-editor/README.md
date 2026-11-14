---
id: 04
title: A text editor
---

# Module 04 - A text editor

Module 03 made kilo a viewer: it reads a file into rows, moves a cursor over them and scrolls, but any key that does not move the cursor does nothing. This module makes it an editor. Lesson by lesson it puts a typed character into the row under the cursor, splits a row in two at Enter, deletes the character before the cursor and joins a row onto the one above at Backspace, and writes the rows back to the file with Ctrl-S, with a warning on Ctrl-Q while changes are unsaved. Every edit is made of the same few moves on the same data: change a row's bytes in place, add or remove a row in the array of rows, and render the changed row again; the frame of module 02 then draws the result as it draws anything else. After it, kilo can open a file, change it and save it: an editor you can use.
