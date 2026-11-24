---
id: cc
title: A C compiler for RISC-V
kind: compiler
status: coming soon
audience: Programmers who run a compiler every day and want to know what it does with their code.
prerequisites: C (pointers and structs), a terminal, and the RISC-V toolchain and QEMU the xv6 track uses. No assembly and no compiler background needed.
outcome: A C compiler you wrote, in C, whose RISC-V output runs on a bare machine and on the xv6 kernel, agrees with gcc on every test and on a published test suite, links with code gcc compiled, builds xv6's user programs, and compiles itself.
upstream: [chibicc](https://github.com/rui314/chibicc) (MIT), decided on 2026-11-24, for the front end and the order it is built in, one feature a step; its code generator is for x86-64, so the RISC-V one is the course's own, written to the RISC-V calling convention and checked against gcc; [xv6-riscv](https://github.com/mit-pdos/xv6-riscv) (MIT) for the kernel the programs run on at the end and the user programs the compiler builds, by way of this course's xv6 track. Proposed, not decided: [c-testsuite](https://github.com/c-testsuite/c-testsuite) (MIT for its runner; its tests come from scc and from tcc, under their own licences, so they are fetched and not stored) for the test corpus; [QBE](https://c9x.me/compile/) (MIT) for the optimising back end, an extension.
---

# A C compiler for RISC-V

You write a compiler for C, in C. It begins as a program that turns one
number into an assembly file, and at every lesson after that it is still
a whole compiler, for a slightly larger language: expressions, then
statements, functions, types, structs, the preprocessor. What it writes
is RISC-V assembly, which runs on a bare machine in QEMU from the first
lesson and, by the end, on the kernel of this course's xv6 track.

It is held to the real thing at every step. The same program, built by
gcc and by your compiler for the same machine, must print the same and
exit the same. Your functions and gcc's call each other. At the end it builds
xv6's user programs, and then its own source.

The track reads alongside Programming Language Pragmatics by Michael L.
Scott (4th edition). Modules 01 to 09 follow its chapters 2 to 9 and 15,
and each lesson ends with the sections that explain its concept. The
book explains why languages and their compilers are the way they are;
this track builds one. What the book covers that C does not have -
closures, garbage collection, objects, virtual machines - is not in this
track.

Modules 00 to 09 are the core. After them come four optional modules,
10 to 13, each one built on the finished compiler and independent of
the others.

**Coming soon.** This is the outline: the direction, not the lessons yet.
Format: `templates/outline.md`.

## Module 00 - The smallest compiler

- Goal: See a compiler as an ordinary program, text in and assembly out, and know every step between that assembly and a running machine.
- You build: A compiler that turns one number into a RISC-V program that exits with it, the forty lines of startup code that run it on a bare machine in QEMU, and a test that holds every later lesson to what gcc says for the same machine.
- Value: Nothing in the toolchain is a black box after this: you have run the assembler, the linker and the machine by hand, once each.
- Lessons:
  - 00.01 From a number to a running program
  - 00.02 What the assembler, the linker and the machine do with it
  - 00.03 The same answer as gcc: a test for every lesson
- Learn from: [B-PLP01], [P-INCR], [C-CHIBICC], [A-RISCV], [B-CSAPP]

## Module 01 - Tokens

- Goal: Know how a compiler turns characters into tokens, and why it does that before anything else.
- You build: A scanner written by hand: numbers, operators by longest match, identifiers and keywords, comments, character and string constants, and error messages that print the line and point at the column.
- Value: Every tool that reads source text - a formatter, a highlighter, a linter - starts with this loop.
- Lessons:
  - 01.01 A stream of tokens: numbers, plus and minus
  - 01.02 Longest match: `=` and `==`, `-` and `->`
  - 01.03 Identifiers and keywords
  - 01.04 Comments, character constants and strings
  - 01.05 Errors that point at the source
- Learn from: [B-PLP02], [C-CHIBICC], [A-DIAG], [A-C11]

## Module 02 - Expressions

- Goal: Understand how a grammar becomes a parser, and why the parser's output is a tree.
- You build: A recursive descent parser for C's expressions, with the precedence and associativity of every operator, the syntax tree it builds, and a code generator that walks the tree with the temporary registers as a stack.
- Value: You can add an operator to any language, and you can read a grammar in a language's reference manual as the code that implements it.
- Lessons:
  - 02.01 A grammar, and a function for each rule
  - 02.02 The syntax tree
  - 02.03 Code from a tree: registers as a stack
  - 02.04 Precedence and associativity: the whole table of C's operators
  - 02.05 Unary operators and comparisons
  - 02.06 Out of registers: spilling to memory
- Learn from: [B-PLP02], [B-PLP06], [B-PLP15], [A-CLIMB], [B-WIRTH], [C-CHIBICC], [C-CLANG]

## Module 03 - Statements and control flow

- Goal: Know what an if, a loop and a switch are once the machine has only compare and branch.
- You build: Local variables in a stack frame, assignment, if, while, for and do, break, continue and goto, the operators that jump instead of computing (`&&`, `||`, `?:`), and switch, first as a chain of compares and then as a jump table.
- Value: You can read the assembly of any loop, and say why one way of writing a condition costs a branch and another does not.
- Lessons:
  - 03.01 Statements, and a frame for local variables
  - 03.02 Assignment: a place and a value
  - 03.03 if and else: labels and branches
  - 03.04 while, for and do
  - 03.05 `&&`, `||` and `?:`: code that jumps instead of computing
  - 03.06 break, continue and goto
  - 03.07 switch: a chain of compares, then a jump table
- Learn from: [B-PLP06], [B-PLP03], [A-RISCV], [C-CHIBICC]

## Module 04 - Functions

- Goal: Understand a function call as an agreement about registers and the stack that both sides keep.
- You build: Function definitions and calls that follow the RISC-V calling convention: arguments in registers and, past the eighth, on the stack; the registers each side saves; the frame, the return address, recursion. Your code calls functions gcc compiled, and gcc's code calls yours.
- Value: The calling convention is what lets libraries, debuggers and other languages work with C. After this you can read a stack by hand.
- Lessons:
  - 04.01 Calling a function someone else compiled
  - 04.02 Defining one: prologue, frame and epilogue
  - 04.03 Parameters, in registers and past the eighth
  - 04.04 Recursion, and reading the stack
  - 04.05 The other way: gcc's code calls yours
- Learn from: [B-PLP09], [A-PSABI], [B-CSAPP], [C-CHIBICC]

## Module 05 - Names, scopes and storage

- Goal: Know what a name is bound to, when that is decided, and how long the thing it names lives.
- You build: A symbol table of nested scopes: declarations in any block and shadowing, global variables in the data and bss sections, constant expressions worked out by the compiler, static locals, and extern and static names across several files.
- Value: Scope, lifetime and linkage are three different things, and most confusing bugs with names come from taking one for another.
- Lessons:
  - 05.01 Blocks: a stack of scopes
  - 05.02 Global variables: storage that is there before main
  - 05.03 Constant expressions: what the compiler works out itself
  - 05.04 static locals: scope is not lifetime
  - 05.05 extern, static and prototypes: names across files
- Learn from: [B-PLP03], [B-PLP15], [B-KR], [C-CHIBICC]

## Module 06 - Types and pointers

- Goal: Understand a type as what the compiler knows about a value before the program runs, and what it does with that knowledge.
- You build: A pass that gives every node of the tree a type: the integer types with their sizes and signs, the conversions between them and casts, pointers and pointer arithmetic, C's declarator syntax, typedef, and type errors reported at compile time.
- Value: You know why `char` plus `char` is an `int`, what a cast costs, and what the compiler checked for you and what it did not.
- Lessons:
  - 06.01 A type on every node
  - 06.02 char, short, int and long: sizes, signs and the right load
  - 06.03 Conversions and casts
  - 06.04 Pointers: an address with a type
  - 06.05 Reading declarators: `int *(*f)(int)`
  - 06.06 typedef, and why the parser needs the symbol table
  - 06.07 Type errors, found before the program runs
- Learn from: [B-PLP07], [B-PLP04], [B-KR], [A-C11], [C-CHIBICC]

## Module 07 - Arrays, strings and structs

- Goal: Know how composite values are laid out in memory, and that indexing and field access are arithmetic on addresses.
- You build: Arrays and the pointers they turn into, sizeof, string literals, structs laid out with gcc's alignment and padding, unions and enums, brace initialisers, and structs assigned, passed and returned by value as the calling convention says.
- Value: You can predict the size of any struct and the address of any element, which is what reading a file format, a network packet or a kernel data structure takes.
- Lessons:
  - 07.01 Arrays, and the pointer they turn into
  - 07.02 sizeof, and arrays of arrays
  - 07.03 String literals
  - 07.04 Structs: offsets, alignment and padding
  - 07.05 Unions and enums
  - 07.06 Initialisers: braces into bytes
  - 07.07 Structs by value: assignment, arguments and returns
- Learn from: [B-PLP08], [A-PSABI], [B-KR], [B-CSAPP], [C-CHIBICC]

## Module 08 - The preprocessor

- Goal: See the preprocessor as a second, smaller language that runs on tokens before the parser sees them.
- You build: `#include`, macros without and with arguments, the standard's rule that stops a macro expanding itself for ever, `#` and `##`, and `#if` and `#ifdef` with their own constant expressions: enough to read real header files.
- Value: You can say exactly what a macro expands to, and why header files, include guards and separate compilation work the way they do.
- Lessons:
  - 08.01 `#include`: many files, one stream of tokens
  - 08.02 `#define`: a name for some tokens
  - 08.03 Macros with arguments, and what they get wrong
  - 08.04 A macro that names itself: the hide set
  - 08.05 `#if` and `#ifdef`: code that is not there
  - 08.06 Headers and separate compilation
- Learn from: [B-PLP03], [A-PROSSER], [A-C11], [C-CHIBICC]

## Module 09 - Real programs

- Goal: Find out what stands between a compiler that passes its own tests and one that builds programs other people wrote.
- You build: Function pointers and variable arguments, then three proofs: a published test suite your compiler passes, the xv6 track's user programs built by it and run on that kernel, and the compiler built by itself, twice, with the same assembly both times.
- Value: A compiler that compiles itself is the oldest test in the field, and after it you can read the source of gcc, clang or tcc and know where you are.
- Lessons:
  - 09.01 Function pointers: code as a value
  - 09.02 Variable arguments: how printf finds its own
  - 09.03 A test suite you did not write
  - 09.04 On xv6: its user programs, built by your compiler
  - 09.05 The compiler compiles itself
- Learn from: [B-PLP09], [B-PLP01], [C-TESTS], [C-XV6], [P-TRUST], [C-TCC], [C-CHIBICC]

## Module 10 - An optimising back end

- Optional: yes
- Goal: Understand why compilers lower the tree to a flat intermediate form, and what a control flow graph and virtual registers make possible.
- You build: A second back end: three-address code in basic blocks, a control flow graph, liveness, register allocation by linear scan, value numbering within a block and a peephole pass, measured in instructions executed against your own first back end and against gcc at -O0 and -O1.
- Value: This is the shape of every production compiler's back end, at a size you can hold in your head, with a number that says what each pass bought.
- Lessons:
  - 10.01 Measure first: instructions executed
  - 10.02 Three-address code and basic blocks
  - 10.03 The control flow graph
  - 10.04 Liveness: which values are still needed
  - 10.05 Register allocation by linear scan
  - 10.06 Value numbering: the same work, done once
  - 10.07 The peephole, and what gcc still does better
- Learn from: [B-PLP15], [B-PLP17], [B-PLP05], [P-LSRA], [C-QBE], [B-EAC]

## Module 11 - An assembler and a linker

- Optional: yes
- Goal: Know what is in an object file, and what a linker does to several of them to make a program.
- You build: An assembler for the instructions your compiler emits, writing ELF object files with symbols and relocations, and a linker that lays out sections, resolves symbols and applies relocations. The toolchain's as and ld are replaced by your own, and each reads what the other writes.
- Value: "Undefined reference" and "relocation truncated" stop being mysteries, and an executable becomes a file you can read byte by byte.
- Lessons:
  - 11.01 Encoding an instruction: 32 bits, six formats
  - 11.02 Labels, and two passes over the file
  - 11.03 An ELF object file: sections, symbols, relocations
  - 11.04 Linking: one address space from many files
  - 11.05 Applying relocations
  - 11.06 An executable the machine boots, and xv6's exec loads
- Learn from: [B-PLP15], [A-RISCV], [A-PSABI], [B-LINK], [B-CSAPP], [C-MOLD]

## Module 12 - A debugger's view

- Optional: yes
- Goal: Understand how a debugger gets from an address in the machine back to a line and a variable in your source.
- You build: Line tables, frame descriptions and the locations of variables, written by your compiler, so that gdb attached to QEMU steps through your C program a line at a time, prints its locals and shows a backtrace.
- Value: Debug information is the compiler's symbol table kept for later; knowing what is in it tells you what a debugger can and cannot show you.
- Lessons:
  - 12.01 Which line is this instruction: the line table
  - 12.02 Backtraces: describing the frame
  - 12.03 Names and types for the debugger: locals and structs
- Learn from: [B-PLP16], [A-DWARF], [A-PSABI]

## Module 13 - Beyond call and return

- Optional: yes
- Goal: See that exceptions and coroutines are things done to the stack, built from what the calling convention already guarantees.
- You build: setjmp and longjmp in assembly, try and throw on top of them, and coroutines that each run on a stack of their own and switch as the xv6 kernel switches between threads, with an iterator written as one.
- Value: You know what an exception costs and where it goes, and what a generator, a green thread and an async function are underneath.
- Lessons:
  - 13.01 setjmp and longjmp: a saved place to return to
  - 13.02 Exceptions: unwinding to a handler
  - 13.03 Coroutines: a stack each, and a switch
  - 13.04 An iterator written as a coroutine
- Learn from: [B-PLP09], [B-PLP06], [A-XV6BOOK], [A-PSABI]

## Library

| Key | Kind | Title | By | Where |
|---|---|---|---|---|
| B-PLP01 | book | Programming Language Pragmatics, 4th edition, chapter 1: Introduction (1.4 compilation and interpretation, 1.6 an overview of compilation) | Michael L. Scott | Morgan Kaufmann, 2016. The author's page: https://www.cs.rochester.edu/~scott/pragmatics/ |
| B-PLP02 | book | Programming Language Pragmatics, chapter 2: Programming Language Syntax (2.2 scanning, 2.3 parsing) | Michael L. Scott | Morgan Kaufmann, 2016 |
| B-PLP03 | book | Programming Language Pragmatics, chapter 3: Names, Scopes, and Bindings (3.2 storage, 3.3 scope rules, 3.7 macro expansion) | Michael L. Scott | Morgan Kaufmann, 2016 |
| B-PLP04 | book | Programming Language Pragmatics, chapter 4: Semantic Analysis (4.6 decorating a syntax tree) | Michael L. Scott | Morgan Kaufmann, 2016 |
| B-PLP05 | book | Programming Language Pragmatics, chapter 5: Target Machine Architecture | Michael L. Scott | The book's companion site: https://booksite.elsevier.com/9780124104099/ |
| B-PLP06 | book | Programming Language Pragmatics, chapter 6: Control Flow | Michael L. Scott | Morgan Kaufmann, 2016 |
| B-PLP07 | book | Programming Language Pragmatics, chapter 7: Type Systems (7.2 type checking) | Michael L. Scott | Morgan Kaufmann, 2016 |
| B-PLP08 | book | Programming Language Pragmatics, chapter 8: Composite Types (8.1 records, 8.2 arrays, 8.5 pointers) | Michael L. Scott | Morgan Kaufmann, 2016 |
| B-PLP09 | book | Programming Language Pragmatics, chapter 9: Subroutines and Control Abstraction (9.2 calling sequences, 9.3 parameter passing, 9.4 exceptions, 9.5 coroutines) | Michael L. Scott | Morgan Kaufmann, 2016 |
| B-PLP15 | book | Programming Language Pragmatics, chapter 15: Building a Runnable Program (15.3 code generation, 15.5 assembly, 15.6 linking) | Michael L. Scott | Morgan Kaufmann, 2016 |
| B-PLP16 | book | Programming Language Pragmatics, chapter 16: Run-Time Program Management (16.3.2 symbolic debugging) | Michael L. Scott | Morgan Kaufmann, 2016 |
| B-PLP17 | book | Programming Language Pragmatics, chapter 17: Code Improvement | Michael L. Scott | The book's companion site: https://booksite.elsevier.com/9780124104099/ |
| B-KR | book | The C Programming Language, 2nd edition | Brian Kernighan, Dennis Ritchie | Prentice Hall, 1988 |
| B-CSAPP | book | Computer Systems: A Programmer's Perspective, 3rd edition | Randal Bryant, David O'Hallaron | Pearson, 2015 |
| B-EAC | book | Engineering a Compiler, 3rd edition | Keith Cooper, Linda Torczon | Morgan Kaufmann, 2022 |
| B-LINK | book | Linkers and Loaders | John R. Levine | Morgan Kaufmann, 1999 |
| B-WIRTH | book | Compiler Construction | Niklaus Wirth | https://people.inf.ethz.ch/wirth/CompilerConstruction/index.html |
| A-C11 | article | N1570, the committee draft of the C11 standard | ISO/IEC JTC1/SC22/WG14 | https://www.open-std.org/jtc1/sc22/wg14/www/docs/n1570.pdf |
| A-RISCV | article | The RISC-V Instruction Set Manual | RISC-V International | https://github.com/riscv/riscv-isa-manual |
| A-PSABI | article | RISC-V ELF psABI: the calling convention, ELF, DWARF and relocations | RISC-V International | https://github.com/riscv-non-isa/riscv-elf-psabi-doc |
| A-CLIMB | article | Parsing expressions by precedence climbing | Eli Bendersky | https://eli.thegreenplace.net/2012/08/02/parsing-expressions-by-precedence-climbing |
| A-DIAG | article | Clang: Expressive Diagnostics | The LLVM project | https://clang.llvm.org/diagnostics.html |
| A-PROSSER | article | Dave Prosser's C Preprocessing Algorithm | Diomidis Spinellis | https://www.spinellis.gr/blog/20060626/ |
| A-DWARF | article | Introduction to the DWARF Debugging Format | Michael J. Eager | https://dwarfstd.org/doc/Debugging%20using%20DWARF-2012.pdf |
| A-XV6BOOK | article | xv6: a simple, Unix-like teaching operating system (the chapter on scheduling) | Russ Cox, Frans Kaashoek, Robert Morris | https://pdos.csail.mit.edu/6.828/2024/xv6/book-riscv-rev4.pdf |
| P-INCR | paper | An Incremental Approach to Compiler Construction | Abdulaziz Ghuloum | Scheme and Functional Programming Workshop, 2006 |
| P-LSRA | paper | Linear Scan Register Allocation | Massimiliano Poletto, Vivek Sarkar | ACM Transactions on Programming Languages and Systems, 1999 |
| P-TRUST | paper | Reflections on Trusting Trust | Ken Thompson | Communications of the ACM, 1984 |
| C-CHIBICC | code | chibicc, a small C compiler | Rui Ueyama | https://github.com/rui314/chibicc |
| C-XV6 | code | xv6 for RISC-V | MIT PDOS | https://github.com/mit-pdos/xv6-riscv |
| C-TESTS | code | c-testsuite | Andrew Chambers | https://github.com/c-testsuite/c-testsuite |
| C-TCC | code | Tiny C Compiler | Fabrice Bellard | https://bellard.org/tcc/ |
| C-CLANG | code | Clang and LLVM | The LLVM project | https://github.com/llvm/llvm-project |
| C-QBE | code | QBE, a compiler backend | Quentin Carbonneaux | https://c9x.me/compile/ |
| C-MOLD | code | mold, a linker | Rui Ueyama | https://github.com/rui314/mold |
