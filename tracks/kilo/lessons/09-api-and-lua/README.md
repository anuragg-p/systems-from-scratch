---
id: 09
title: An API, and Lua on top of it
optional: true
---

# Module 09 - An API, and Lua on top of it

This module is optional: it stands on the finished core, modules 00 to 05, and nothing in the core needs it. Until now every new feature meant changing `kilo.c` and compiling it again. Real editors are extended without that, by code their users write and load while the editor runs, and this module shows how, in the shape Neovim has: the editor's operations described as a table of typed C functions, and a real language, Lua, given that table. Lua is the one thing in the track that is not written here. A language is a project of its own, and Neovim and Redis do the same, embedding a Lua someone else wrote; `./learn run` supplies its source, and 09.01 shows how to fetch it once to build by hand. The first lesson puts the interpreter inside the editor, with a prompt to type Lua at and an init file run at start, every call into it protected so that a script's error is a message and not a crash. The second describes the editor's operations as a table of functions and hands all of them to Lua through one function that checks every call; the third lets a script change the text, through one function that inserts, deletes and replaces lines. Then any key can run a Lua function, the editor's events, a save or a change, run the functions registered for them, and a script can colour parts of the screen and set the status bar, ask for a line, open another file and leave. Scripts that loop forever or take all the memory are stopped, and the editor runs with no screen at all, a script against a file. The last lesson builds features as plugins, with no new C. After this module an `init.lua` adds keys and reacts to saves, and `kilo -l` edits files from a script.

The lessons:

- 09.01 A second language inside the editor: embedding Lua
- 09.02 The API is a table
- 09.03 Changing the text from a script: set_lines
- 09.04 Any key can run a Lua function
- 09.05 Events: autocommands
- 09.06 Drawing from a script: highlights and the status bar
- 09.07 Asking, opening, leaving: input(), open(), quit()
- 09.08 Scripts that go wrong
- 09.09 The editor without its screen
- 09.10 Features as scripts
