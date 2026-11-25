---
id: 01
title: Introduction
---

# Module 01 - Introduction

Chapter 1 of Programming Language Pragmatics is the whole subject at a glance: machine language and assembly, why there are so many languages and what makes one succeed, the families they fall into, compiling against interpreting and the tools around both, and then one program, the greatest common divisor of two numbers, taken through every phase of a compiler. This module builds all of it, small, for a language of your own, in C. By its end that one program runs five ways: by hand, in RISC-V assembly, on a machine of your own (01.01); straight from its text, by a first interpreter (01.03); translated to C and finished by your computer's own compiler and linker (01.04); through a scanner, a parser and semantic analysis to a tree that an interpreter walks (01.06 to 01.09); and through a code generator and an improver to assembly for the machine again (01.10, 01.11). Every way prints 21, and `agree` (01.05) runs every program every way there is and holds each to the output written down for it in 01.02. The module stands on nothing but a C compiler and make on your computer. Read section 1.7, the chapter's summary, last: by then each thing it names is something you have built and run.
