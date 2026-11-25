---
id: lang
title: Your own language, chapter by chapter
kind: language
status: coming soon
audience: Readers of Programming Language Pragmatics who want to build what each chapter describes, as they read it.
prerequisites: C (pointers, structs, malloc), a terminal, and a copy of the book. No compiler background needed.
outcome: A language of your own, with an interpreter, a compiler, a virtual machine and the tools around them, built in the order of the book's chapters, each piece run the day you read about it.
upstream: Proposed, not decided: this course's cc track, and through it [chibicc](https://github.com/rui314/chibicc) (MIT), for the shape of the hand-written scanner and parser; [the RISC-V instruction set manual](https://github.com/riscv/riscv-isa-manual) (CC-BY-4.0) for the instructions of the small machine the compiler targets. The language and its code are the course's own. The real systems each later module takes its mechanism from (for closures, the collector, the bytecode machine, the parser generators) are named when that module is planned.
---

# Your own language, chapter by chapter

This track is read with a book open beside it: Programming Language
Pragmatics by Michael L. Scott, 4th edition. Module 01 is chapter 1,
module 02 is chapter 2, and so on to 17. Inside a module the lessons come
in the order of the chapter's sections, and each one names the section it
follows. You read the section in your copy; the lesson then gives you the
code that makes it real and the commands that run it, with what they
print.

What grows, lesson by lesson, is one small language of your own. The
track calls it Mote; lesson 01.02 is where you give it your own name. It
starts as a calculator that reads, computes and writes. Each chapter adds
what that chapter is about: scopes and closures, types and inference,
records and arrays, exceptions and coroutines, objects, lazy lists,
threads. By chapter 15 it is compiled to the instructions of a small
machine you built in chapter 5, and by chapter 16 it has a virtual
machine, a debugger and a profiler.

Nothing of the book is copied here: no sentence, figure, example or
exercise. The book explains; this track builds. Three of its chapters
(5 and 17, and the sections it marks as on its companion site) are not in
the printed book; their lessons say where to find them.

It is a different road from this course's cc track, which builds a C
compiler in the order the code needs and checks it against gcc. Here the
order is the book's, and what the pieces are checked against is each
other: the interpreter, the virtual machine and the compiled program must
give the same answer for every program you have written.

**Coming soon.** This is the outline: the direction, not the lessons yet.
Format: `templates/outline.md`.

## Module 01 - Introduction

- Goal: Know what a language implementation is made of, by building a small one of every kind the chapter shows and running one program through each.
- You build: A small machine and a program in its assembly, the first programs in your own language, an interpreter that runs them from their text, a translator to C, a prompt and a test runner, and then a compiler phase by phase: scanner, parser, semantic analysis, a tree-walking interpreter, a code generator for your machine and an improver.
- Value: Your language runs one program five ways that must all agree; every later chapter makes one of these pieces deeper, and the programs written here are the tests the whole track is held to.
- Lessons:
  - 01.01 A machine, and a program written in its language (the chapter's opening)
  - 01.02 Your language, and the programs you want it to run (sections 1.1 to 1.3)
  - 01.03 An interpreter: the program run from its text (1.4 to Example 1.10)
  - 01.04 A translator: to C, and from there to the machine (1.4 from Example 1.11)
  - 01.05 The tools around a language: a prompt and a test runner (1.5)
  - 01.06 The phases of a compiler, and the first: a scanner (1.6 and the first half of 1.6.1)
  - 01.07 The parser: tokens into a tree (the rest of 1.6.1)
  - 01.08 Semantic analysis: the syntax tree and the symbol table (1.6.2 to Example 1.24)
  - 01.09 Walking the tree: an interpreter built on the front end (1.6.2, Example 1.25)
  - 01.10 Target code: loads, stores, tests and branches (1.6.3)
  - 01.11 Code improvement: variables kept in registers (1.6.4)
- Learn from: [B-PLP01], [T-CC], [B-CRAFT]

## Module 02 - Programming language syntax

- Goal: Understand how the syntax of a language is written down, and the two ways each of its halves is turned into code: by hand, and by a tool from the description.
- You build: A regular expression matcher, a scanner written by hand and the same scanner as a table made from the token definitions, a recursive descent parser, a tool that works out the sets a top-down parser needs and the table-driven parser that uses them, a bottom-up parser, and error handling that carries on after a mistake.
- Value: You can read any language's grammar, write a parser for a format of your own in an afternoon, and know what lex and yacc are doing when a project uses them.
- Lessons:
  - 02.01 Tokens as regular expressions: a matcher you can run (2.1.1)
  - 02.02 A grammar for your language, and the trees it derives (2.1.2, 2.1.3)
  - 02.03 From regular expressions to an automaton (2.2.1)
  - 02.04 The scanner, written by hand (2.2.2)
  - 02.05 The scanner as a table and a driver (2.2.3)
  - 02.06 Lexical errors, and notes to the compiler (2.2.4, 2.2.5)
  - 02.07 Recursive descent: a function for each rule (2.3.1)
  - 02.08 Making a grammar fit: first, follow and predict sets (2.3.2)
  - 02.09 A top-down parser as a table and a stack (2.3.3)
  - 02.10 Bottom-up parsing: shift and reduce (2.3.4)
  - 02.11 Syntax errors: carrying on after a mistake (2.3.5)
- Learn from: [B-PLP02], [T-CC], [B-DRAGON], [A-RECOX]

## Module 03 - Names, scopes and bindings

- Goal: Know what a name is bound to, when that is decided, how long the thing it names lives, and what a function carries with it when it is passed around.
- You build: Variables with static, stack and heap storage, blocks and nested functions under static scope, a switch that runs the same program under dynamic scope, a symbol table, modules, closures, and a macro expander.
- Value: Scope, lifetime and binding stop being one blurred idea; you can say why a closure works, why dynamic scope surprised people, and what a macro can do that a function cannot.
- Lessons:
  - 03.01 What is decided when: binding time (3.1)
  - 03.02 Where values live: static, stack and heap (3.2)
  - 03.03 Static scope: blocks, nested functions, declaration order (3.3.1 to 3.3.3)
  - 03.04 Modules (3.3.4, 3.3.5)
  - 03.05 Dynamic scope: the same program, another answer (3.3.6)
  - 03.06 The symbol table (3.4)
  - 03.07 Aliases and overloading (3.5)
  - 03.08 Closures: a function and the environment it was made in (3.6)
  - 03.09 Macros (3.7)
  - 03.10 Separate compilation (3.8)
- Learn from: [B-PLP03], [B-SICP], [B-CRAFT]

## Module 04 - Semantic analysis

- Goal: Understand the pass between parsing and running: what it checks, what it adds to the tree, and how grammar rules can carry the checking with them.
- You build: Checks the parser cannot make, attributes computed over a tree, parser actions that build the syntax tree directly, and a pass that decorates that tree with types, converts integers to reals where the language allows it, and reports every error with its place.
- Value: This is the pass where "it parses" becomes "it means something"; linters and type checkers are this pass and nothing else.
- Lessons:
  - 04.01 What the parser cannot check (4.1)
  - 04.02 Attributes on a grammar, and the order to compute them in (4.2, 4.3)
  - 04.03 Action routines: the parser builds the tree (4.4, 4.5)
  - 04.04 Decorating the tree: types, conversions and errors (4.6)
- Learn from: [B-PLP04], [B-DRAGON], [T-CC]

## Module 05 - Target machine architecture

- Goal: Know the machine a compiler writes for: how numbers are stored, what an instruction is, and what makes code fast or slow on it.
- You build: A program that shows any number as its bits, a small RISC machine in software (registers, memory, a few dozen RISC-V instructions read as assembly text), programs written for it by hand, and measurements of what memory access order costs on your real machine.
- Value: The machine built here is the one your compiler targets in module 15, and reading assembly stops being a barrier anywhere.
- Lessons:
  - 05.01 The memory hierarchy, measured (5.1)
  - 05.02 Numbers as bits: integers and floating point (5.2)
  - 05.03 A small machine: registers, memory, instructions (5.3)
  - 05.04 Addresses, conditions and branches: a program by hand (5.3.1, 5.3.2)
  - 05.05 What a compiler has to know about a modern processor (5.4, 5.5)
- Learn from: [B-PLP05], [A-RISCV], [B-CSAPP], [T-CC]

## Module 06 - Control flow

- Goal: Understand every way a language decides what happens next, and what each costs to implement.
- You build: Precedence and evaluation order made visible, assignment with values and references, a check for variables used before they are set, short-circuit conditions, exits from loops and functions, case statements with a jump table, counted and conditional loops and iterators, and recursion with tail calls that do not grow the stack.
- Value: You can predict what an expression with side effects does in any language, and say what a loop or a switch compiles to.
- Lessons:
  - 06.01 Precedence, associativity and the order of evaluation (6.1.1, 6.1.4)
  - 06.02 Assignment: values and references (6.1.2)
  - 06.03 Initialisation, and use before a value is given (6.1.3)
  - 06.04 Short-circuit evaluation (6.1.5)
  - 06.05 Leaving a loop, leaving a function: structured flow (6.2)
  - 06.06 Selection: if, and case with a jump table (6.3, 6.4)
  - 06.07 Loops: counted, conditional, and iterators (6.5)
  - 06.08 Recursion, tail calls, and when arguments are evaluated (6.6, 6.7)
- Learn from: [B-PLP06], [B-SICP], [T-CC]

## Module 07 - Type systems

- Goal: Understand a type as a claim about a value that the language can check, and the choices a checker has to make.
- You build: A type checker for your language with numeric, enumeration and subrange types, both rules for when two types are the same, conversions and coercions, inference by unification for expressions and functions, generic functions, and shallow and deep equality.
- Value: You can read a type error as the checker's reasoning, and you know what "structural", "nominal", "inferred" and "generic" mean because you built each.
- Lessons:
  - 07.01 What a type is, and the kinds there are (7.1)
  - 07.02 When two types are the same: structure or name (7.2.1)
  - 07.03 Compatibility, conversion and coercion (7.2.2)
  - 07.04 Inference by unification (7.2.3, 7.2.4)
  - 07.05 Generic functions (7.3)
  - 07.06 Equality and assignment: shallow and deep (7.4)
- Learn from: [B-PLP07], [B-TAPL], [B-CRAFT]

## Module 08 - Composite types

- Goal: Know how values made of other values are laid out and reclaimed, and what each choice costs.
- You build: Records with their layout and holes, arrays with bounds checks and both layouts, strings and sets, pointers and recursive types, two defences against dangling references, a reference-counting collector and then a tracing one, lists, and files.
- Value: You can predict the size and address of anything in memory, and you have written the two families of garbage collector that every managed language chooses between.
- Lessons:
  - 08.01 Records: fields, layout and holes (8.1)
  - 08.02 Arrays: bounds, shape and layout (8.2)
  - 08.03 Strings and sets (8.3, 8.4)
  - 08.04 Pointers and recursive types (8.5.1)
  - 08.05 Dangling references: tombstones, locks and keys (8.5.2)
  - 08.06 Garbage collection: counting, then tracing (8.5.3)
  - 08.07 Lists (8.6)
  - 08.08 Files and input and output (8.7)
- Learn from: [B-PLP08], [B-GC], [B-CSAPP], [B-CRAFT]

## Module 09 - Subroutines and control abstraction

- Goal: Understand a call from the stack up: the frame, who saves what, how arguments travel, and the three things that are not a plain call and return.
- You build: Stack frames with static links for nested functions, every parameter mode, default, named and variable arguments, exceptions that unwind to a handler, coroutines with a stack each, and event handlers.
- Value: You can read a stack trace in any language, say what "pass by reference" really passes, and you know what exceptions, generators and async code are underneath.
- Lessons:
  - 09.01 The stack frame (9.1)
  - 09.02 Calling sequences: who saves what, and the static chain (9.2)
  - 09.03 Parameter modes: value, reference, result, name (9.3.1, 9.3.2)
  - 09.04 Default, named and variable arguments; returning values (9.3.3, 9.3.4)
  - 09.05 Exceptions: raise, handle, unwind (9.4)
  - 09.06 Coroutines: a stack each, and transfer (9.5)
  - 09.07 Events and handlers (9.6)
- Learn from: [B-PLP09], [A-PSABI], [T-CC], [T-XV6]

## Module 10 - Data abstraction and object orientation

- Goal: Understand objects as records with a table of functions, and inheritance as a rule about how those tables are laid out.
- You build: Classes with fields and methods, visibility and inheritance, constructors and destructors in the right order, dynamic method binding through a table of method addresses, interfaces, multiple inheritance, and a mode in which everything, numbers included, is an object.
- Value: A virtual call, a vtable and an interface stop being words; you can say what each costs and draw the memory of any object.
- Lessons:
  - 10.01 Classes and objects (10.1)
  - 10.02 Encapsulation and inheritance (10.2)
  - 10.03 Constructors and destructors (10.3)
  - 10.04 Dynamic method binding: the table of methods (10.4)
  - 10.05 Interfaces and mix-ins (10.5)
  - 10.06 Multiple inheritance (10.6)
  - 10.07 Everything is an object (10.7)
- Learn from: [B-PLP10], [B-CRAFT]

## Module 11 - Functional languages

- Goal: See how much of a language is left when assignment is taken away, and what has to be added in its place.
- You build: A functional core of your language: lists and recursion in the style of the chapter's Scheme, tagged types and pattern matching in the style of its OCaml, lazy evaluation and endless streams, higher-order functions and currying, and the lambda calculus run as a program.
- Value: Map, filter, fold, closures and lazy sequences are in every language now; you know how each is built and what it costs.
- Lessons:
  - 11.01 Programs without assignment (11.1, 11.2)
  - 11.02 Lists and recursion: the chapter's Scheme in your language (11.3)
  - 11.03 Tagged types and pattern matching: the chapter's OCaml in your language (11.4)
  - 11.04 Lazy evaluation and streams (11.5)
  - 11.05 Higher-order functions and currying (11.6)
  - 11.06 The lambda calculus, run (11.7)
- Learn from: [B-PLP11], [B-SICP], [B-TAPL]

## Module 12 - Logic languages

- Goal: Understand a program as facts and rules, and running it as a search for a proof.
- You build: A second small language beside your own: facts, rules and queries, unification, resolution with backtracking, lists and arithmetic, and the cut.
- Value: Unification is the same algorithm as the type inference of module 07, and backtracking search is behind every solver; here you see both bare.
- Lessons:
  - 12.01 Facts, rules and queries (12.1, 12.2)
  - 12.02 Unification (12.2.1)
  - 12.03 Resolution and backtracking: the search (12.2.4)
  - 12.04 Lists, arithmetic and the cut (12.2.2, 12.2.3, 12.2.6)
  - 12.05 What logic programming leaves out (12.3, 12.4)
- Learn from: [B-PLP12], [B-SICP]

## Module 13 - Concurrency

- Goal: Understand threads as coroutines with a scheduler, and synchronisation as the cure for what the scheduler makes possible.
- You build: Threads in your language on top of module 09's coroutines, a scheduler that switches them, a race you can reproduce, spin locks, semaphores, monitors with condition variables, and message passing.
- Value: You have caused a race on purpose and fixed it three ways, which is the only way the vocabulary of concurrency sticks.
- Lessons:
  - 13.01 Threads from coroutines, and a scheduler (13.1, 13.2)
  - 13.02 A race, and busy-wait locks (13.3.1 to 13.3.3)
  - 13.03 The scheduler and semaphores (13.3.4, 13.3.5)
  - 13.04 Monitors and condition variables (13.4)
  - 13.05 Message passing (13.5)
- Learn from: [B-PLP13], [T-XV6], [B-OSTEP]

## Module 14 - Scripting languages

- Goal: See what a scripting language adds to a language like yours, and why those additions make short programs short.
- You build: A scripting mode for your language: pattern matching on strings with module 02's regular expressions, dynamic types and associative arrays, names that need no declaration, running other programs and using their output, and objects made the scripting way.
- Value: You can say what Python, Perl, Ruby and the shell have in common underneath, and you have a tool of your own for the jobs they are used for.
- Lessons:
  - 14.01 What makes a language a scripting language (14.1, 14.2)
  - 14.02 Scripting the web: a program that answers a request (14.3)
  - 14.03 Names and scopes without declarations (14.4.1)
  - 14.04 Strings and patterns (14.4.2)
  - 14.05 Dynamic types and associative arrays (14.4.3)
  - 14.06 Objects, the scripting way (14.4.4)
- Learn from: [B-PLP14], [A-RECOX]

## Module 15 - Building a runnable program

- Goal: Follow a program from the decorated tree to bytes a machine runs: intermediate code, instructions, an object file, a linked program.
- You build: A back end for your language: stack code and three-address code from the tree, code generation for module 05's machine with a simple register allocator, the layout of a program in memory, an assembler, and a linker that joins separately compiled files.
- Value: Your language is now compiled, and "undefined symbol" and "relocation" are things you implemented.
- Lessons:
  - 15.01 The phases of a back end (15.1)
  - 15.02 Intermediate forms: stack code and three-address code (15.2)
  - 15.03 Code generation from the tree (15.3.1)
  - 15.04 Registers, the simple way (15.3.2)
  - 15.05 The address space of a program (15.4)
  - 15.06 An assembler (15.5)
  - 15.07 A linker (15.6)
  - 15.08 Linking at run time (15.7)
- Learn from: [B-PLP15], [A-RISCV], [B-LINK], [T-CC]

## Module 16 - Run-time program management

- Goal: Understand what a language's run-time system does while the program runs: execute it, translate it, and let it be inspected.
- You build: A virtual machine with its own bytecode and file format, translation of hot code at run time, reflection (a program asking about its own types and fields), a debugger with breakpoints and single steps, and a profiler.
- Value: You have built in small what the Java and .NET machines are in large, and a debugger and profiler are no longer other people's tools.
- Lessons:
  - 16.01 A virtual machine and its bytecode (16.1)
  - 16.02 Translating at run time (16.2)
  - 16.03 Reflection (16.3.1)
  - 16.04 A debugger: breakpoints and single steps (16.3.2)
  - 16.05 A profiler (16.3.3)
- Learn from: [B-PLP16], [B-CRAFT], [A-DWARF]

## Module 17 - Code improvement

- Goal: Understand what an optimiser does as a series of small, checkable rewrites, each measured.
- You build: A peephole pass, value numbering in a basic block, data flow analysis and static single assignment form across blocks, loop improvements, instruction scheduling, and register allocation by graph colouring, each measured in instructions executed on module 05's machine.
- Value: You can read a compiler's optimisation report, and know which passes matter for which code.
- Lessons:
  - 17.01 Peephole optimisation (17.1, 17.2)
  - 17.02 Redundancy in a basic block: value numbering (17.3)
  - 17.03 Across blocks: data flow and single assignment (17.4)
  - 17.04 Loops: invariants and induction variables (17.5, 17.7)
  - 17.05 Instruction scheduling (17.6)
  - 17.06 Register allocation by graph colouring (17.8)
- Learn from: [B-PLP17], [B-EAC], [B-DRAGON]

## Library

| Key | Kind | Title | By | Where |
|---|---|---|---|---|
| B-PLP01 | book | Programming Language Pragmatics, 4th edition, chapter 1: Introduction | Michael L. Scott | Morgan Kaufmann, 2016. The author's page: https://www.cs.rochester.edu/~scott/pragmatics/ |
| B-PLP02 | book | Programming Language Pragmatics, chapter 2: Programming Language Syntax | Michael L. Scott | Morgan Kaufmann, 2016 |
| B-PLP03 | book | Programming Language Pragmatics, chapter 3: Names, Scopes, and Bindings | Michael L. Scott | Morgan Kaufmann, 2016 |
| B-PLP04 | book | Programming Language Pragmatics, chapter 4: Semantic Analysis | Michael L. Scott | Morgan Kaufmann, 2016 |
| B-PLP05 | book | Programming Language Pragmatics, chapter 5: Target Machine Architecture | Michael L. Scott | The book's companion site: https://booksite.elsevier.com/9780124104099/ |
| B-PLP06 | book | Programming Language Pragmatics, chapter 6: Control Flow | Michael L. Scott | Morgan Kaufmann, 2016 |
| B-PLP07 | book | Programming Language Pragmatics, chapter 7: Type Systems | Michael L. Scott | Morgan Kaufmann, 2016 |
| B-PLP08 | book | Programming Language Pragmatics, chapter 8: Composite Types | Michael L. Scott | Morgan Kaufmann, 2016 |
| B-PLP09 | book | Programming Language Pragmatics, chapter 9: Subroutines and Control Abstraction | Michael L. Scott | Morgan Kaufmann, 2016 |
| B-PLP10 | book | Programming Language Pragmatics, chapter 10: Data Abstraction and Object Orientation | Michael L. Scott | Morgan Kaufmann, 2016 |
| B-PLP11 | book | Programming Language Pragmatics, chapter 11: Functional Languages | Michael L. Scott | Morgan Kaufmann, 2016 |
| B-PLP12 | book | Programming Language Pragmatics, chapter 12: Logic Languages | Michael L. Scott | Morgan Kaufmann, 2016 |
| B-PLP13 | book | Programming Language Pragmatics, chapter 13: Concurrency | Michael L. Scott | Morgan Kaufmann, 2016 |
| B-PLP14 | book | Programming Language Pragmatics, chapter 14: Scripting Languages | Michael L. Scott | Morgan Kaufmann, 2016 |
| B-PLP15 | book | Programming Language Pragmatics, chapter 15: Building a Runnable Program | Michael L. Scott | Morgan Kaufmann, 2016 |
| B-PLP16 | book | Programming Language Pragmatics, chapter 16: Run-Time Program Management | Michael L. Scott | Morgan Kaufmann, 2016 |
| B-PLP17 | book | Programming Language Pragmatics, chapter 17: Code Improvement | Michael L. Scott | The book's companion site: https://booksite.elsevier.com/9780124104099/ |
| B-CRAFT | book | Crafting Interpreters | Robert Nystrom | https://craftinginterpreters.com/ |
| B-SICP | book | Structure and Interpretation of Computer Programs, 2nd edition | Harold Abelson, Gerald Jay Sussman, Julie Sussman | MIT Press, 1996 |
| B-TAPL | book | Types and Programming Languages | Benjamin C. Pierce | MIT Press, 2002 |
| B-DRAGON | book | Compilers: Principles, Techniques, and Tools, 2nd edition | Alfred Aho, Monica Lam, Ravi Sethi, Jeffrey Ullman | Addison-Wesley, 2006 |
| B-EAC | book | Engineering a Compiler, 3rd edition | Keith Cooper, Linda Torczon | Morgan Kaufmann, 2022 |
| B-GC | book | The Garbage Collection Handbook, 2nd edition | Richard Jones, Antony Hosking, Eliot Moss | CRC Press, 2023 |
| B-CSAPP | book | Computer Systems: A Programmer's Perspective, 3rd edition | Randal Bryant, David O'Hallaron | Pearson, 2015 |
| B-LINK | book | Linkers and Loaders | John R. Levine | Morgan Kaufmann, 1999 |
| B-OSTEP | book | Operating Systems: Three Easy Pieces | Remzi H. Arpaci-Dusseau, Andrea C. Arpaci-Dusseau | https://pages.cs.wisc.edu/~remzi/OSTEP/ |
| A-RISCV | article | The RISC-V Instruction Set Manual | RISC-V International | https://github.com/riscv/riscv-isa-manual |
| A-PSABI | article | RISC-V ELF psABI: the calling convention, ELF, DWARF and relocations | RISC-V International | https://github.com/riscv-non-isa/riscv-elf-psabi-doc |
| A-DWARF | article | Introduction to the DWARF Debugging Format | Michael J. Eager | https://dwarfstd.org/doc/Debugging%20using%20DWARF-2012.pdf |
| A-RECOX | article | Regular Expression Matching Can Be Simple And Fast | Russ Cox | https://swtch.com/~rsc/regexp/regexp1.html |
| T-CC | course | A C compiler for RISC-V: this course's cc track | systems from scratch | /t/cc |
| T-XV6 | course | A Unix kernel for RISC-V: this course's xv6 track | systems from scratch | /t/xv6 |
