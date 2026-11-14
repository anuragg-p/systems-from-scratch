---
id: 01
title: The terminal
---

# Module 01 - The terminal

The two streams of module 00, made usable. 01.01 switches the terminal into raw mode, so every key reaches kilo the moment it is pressed, unechoed and unchanged, with Ctrl-C, Ctrl-S and Ctrl-Q as plain bytes, and puts the terminal back at every exit. 01.02 reads the escape sequences of the arrows, Home, End, Delete and Page Up and Down back into one key each, and tells the Escape key apart from them by a tenth of a second. 01.03 learns the window's size, from the kernel or, when the kernel does not know, by asking the terminal. There is no screen yet: kilo prints the code of each key you press, one per line. After this module it has everything it needs from the terminal to draw one, which module 02 does.
