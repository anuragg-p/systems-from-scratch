---
id: 00
title: The workbench
---

# Module 00 - The workbench

The whole editor, before any part of it is built. 00.01 follows one key from the keyboard through kilo and back to the screen: raw mode hands over its byte, the key is read and handled, the rows change, and the whole screen is drawn again from them in one write. It names each piece on the way, explains the order the track builds them in, and runs the finished editor on a new file. 00.02 looks at the two streams of bytes that are all kilo ever works with: what each key sends, escape sequences included, and what a terminal does with the bytes a program writes, down to the 108 bytes of kilo's own first screen. After this module you know what every piece is for and can read what passes between kilo and the terminal. It stands on nothing: this is where the track starts.
