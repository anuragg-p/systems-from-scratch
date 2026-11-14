---
id: 03
title: A text viewer
---

# Module 03 - A text viewer

Module 02 gave the editor a frame to draw, but nothing to put in it. This module makes it a viewer. It reads the file named on the command line into an array of rows, one per line; moves a cursor over them with the arrow and page keys, scrolling the view down and across whenever the cursor would leave the screen; draws each row from a second copy in which every tab has become the spaces it takes up, so the text and the cursor land in the right columns; and gives the bottom two lines of the screen to a status bar, with the file's name, its length and the cursor's line, and a line for messages. After this module kilo opens any text file and lets you read all of it, but it cannot change a byte: module 04 builds editing on these rows.
