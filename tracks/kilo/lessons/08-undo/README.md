---
id: 08
title: Undo and redo
optional: true
---

# Module 08 - Undo and redo

This module is optional: it stands on the finished core, modules 00 to 05, and nothing in the core needs it. It is ours, not antirez's: his kilo has no undo, so in it one wrong key is permanent, and the only way back is to quit without saving and lose every other change with it. The design is Vim's, cut to kilo's size: before a line changes, keep what it was, and to undo, swap the kept lines back in. The first lesson does that: just before a row changes, the row functions keep what it was in a record, and Ctrl-Z puts the rows back, a key at a time. The second makes applying a record keep what it replaces, so that the record becomes its own opposite and the same act, run the other way, is redo. The third makes one Ctrl-Z take back one thought, a run of typing or of deleting, and puts the cursor back where it began. The fourth makes "(modified)" tell the truth after undo and redo, and keeps the history inside 8 MB. After this module Ctrl-Z and Ctrl-R go back and forth through everything done since the file was opened, as far as that bound allows, and each lesson sets kilo's choice beside other editors': Vim's and Emacs's in every one, and Helix's, Zed's and VS Code's where they chose otherwise.
