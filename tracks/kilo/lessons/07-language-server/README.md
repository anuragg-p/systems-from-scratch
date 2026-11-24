---
id: 07
title: A language server client
optional: true
---

# Module 07 - A language server client

This module is optional: it stands on the finished core, modules 00 to 05, and nothing in the core needs it. It is ours, not antirez's: his kilo has no such thing. kilo knows nothing about C, but a language server does: a program, clangd for C, that reads code the way a compiler does and answers an editor's questions about it, in messages of the Language Server Protocol over its standard input and output. It runs as another process, so whatever it does, slow, wrong, silent or dead, cannot take the unsaved file down with it. The first lesson starts it as kilo's child, joined by pipes; the second frames the messages that go each way, and the third reads the JSON inside them. The fourth has kilo wait for a key and for the server in one call, so that it never stops for the server and an answer is seen the moment it arrives. The fifth keeps the server's copy of the text the same as the one on the screen, unsaved changes and all; the sixth underlines what the server says is wrong; the seventh asks it where a name is defined, and goes there. After this module a C file shows its errors underlined as you type, Ctrl-G jumps to a definition, and whatever the server does, the editor still edits and saves. It needs clangd installed; without it, kilo says it cannot start one and works as the core does.
