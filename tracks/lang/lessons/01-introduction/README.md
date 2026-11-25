---
id: 01
title: Introduction
---

# Module 01 - Introduction

Chapter 1 of Programming Language Pragmatics is the whole subject at a glance: machine language and assembly, why there are so many languages and what makes one succeed, the families they fall into, compiling against interpreting and the tools around both, and then one program, the greatest common divisor of two numbers, taken through every phase of a compiler. This module builds all of it, small, for a language of your own, in C. That one program is first written by hand, in RISC-V assembly, for a machine of your own (01.01): not a way of running your language, but the measure for the code a compiler writes. Then it is written once in your language (01.02), and by the module's end it runs five ways: by a first interpreter, straight from its text (01.03); translated to C and finished by your computer's own compiler and linker (01.04); through a scanner, a parser and semantic analysis (01.06 to 01.08) to a tree that an interpreter walks (01.09); from that same front end, compiled to assembly for the machine (01.10); and compiled and improved, with variables kept in registers (01.11). Every one prints 21, and `agree` (01.05) runs every program every way there is and holds each to the output written down for it in 01.02. The module stands on nothing but a C compiler and make on your computer. Read section 1.7, the chapter's summary, last: by then each thing it names is something you have built and run.
