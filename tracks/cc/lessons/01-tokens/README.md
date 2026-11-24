---
id: 01
title: Tokens
---

# Module 01 - Tokens

Module 00's compiler read one number straight from the characters of its file. This module puts a scanner in front of everything else: the compiler's first phase, which reads the characters once and cuts them into tokens, after which no other part of the compiler looks at a character. 01.01 cuts numbers, plus and minus, and the compiler takes sums and differences, with spaces or without, its driver walking the tokens to write the code. 01.02 reads every operator of C, taking the longest one that fits; 01.03 reads names, and picks out the ones the language keeps for itself as keywords; 01.04 skips comments, and reads character constants, strings, and numbers in hexadecimal, octal and binary. 01.05 makes every error show the line it is on, with a caret under the place. After this module the compiler sees words where it saw characters, and its errors point at the source; what it compiles is still a sum, until module 02 builds a parser on the tokens. It stands on module 00: the file the driver reads, the way from assembly to a running machine, and gcc to check the answers against.
