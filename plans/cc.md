# Plan: track `cc` - a C compiler for RISC-V

Status: plan (direction set by Fable; implementation by Opus agents).
Outline: `outlines/cc.md`. Nothing is built yet.

## What the learner ends with

A compiler for a large subset of C, written in C, that they built a lesson
at a time and that is a whole compiler at every lesson. It reads C and
writes RISC-V assembly. Its programs run on a bare RISC-V machine in QEMU
and on this course's xv6 kernel, link with code gcc compiled, give gcc's
answers on every test, build xv6's user programs, and compile the
compiler's own source. It is chibicc, built up the way the kilo track is
antirez's kilo, with a code generator of our own for RISC-V.

## Decisions

- Track id `cc`, kind `compiler`, title "A C compiler for RISC-V".
- Upstream (the owner, 2026-11-24: "go with chibicc"):
  https://github.com/rui314/chibicc, MIT, Copyright (c) 2019 Rui Ueyama,
  branch `main` at 90d1f7f199cc55b13c7fdb5839d1409806633fdb (2020-12-07,
  316 commits, 8916 lines). The front end is derived from it
  (`"derived": True`): `tracks/cc/LICENSE` holds its licence whole and
  comes with the project from the first lesson, and `NOTICE` gets a `cc`
  section saying what was taken and what is ours.
- Taken: `tokenize.c`, `preprocess.c`, `parse.c`, `type.c`, the header and
  what of `main.c` reads options, as they stand at upstream's commit 205
  (603de50, 6308 lines, eight commits after it first compiles itself at
  197), less what "The language" below leaves out. Function names and
  structure stay as upstream has them, so a reader can hold its file
  beside ours. Comments are rewritten as lesson notes. Every departure is
  listed in `tracks/cc/NOTES.md` with its reason and the original quoted.
- Ours: `codegen.c` (upstream's is for x86-64 and the System V ABI; ours
  is for RV64 and the RISC-V calling convention, and keeps upstream's
  shape: `gen_expr`, `gen_stmt`, `gen_addr`, `codegen`), the runtime
  (`rt/`), the scripts, the order the code is built in, the lessons and
  the internal checks.
- The reference is gcc for the same machine (`riscv64-elf-gcc -O0`), not
  the host's cc: same target, same ABI, same runtime, so the two programs
  must agree byte for byte in what they print and in their exit status.
  The host's compiler would disagree on things C leaves to the platform
  (plain `char` is unsigned on RISC-V, signed on x86-64 and on macOS).
- The compiler writes assembly and stops there. Assembling and linking
  are done by the toolchain's `as` and `ld`, which the reader runs by hand
  in 00.02 and through a script afterwards. Upstream's driver (it forks
  `cc1`, `as` and `ld`) is left out: the compiler has to run on a bare
  machine in 09.05, where there is nothing to fork.
- Programs run on QEMU's `virt` machine with no firmware and no kernel
  under them (`-bios none -kernel prog.elf`), from 00.01. xv6 comes in at
  09.04 only. One run costs 0.02 s here, so a test may run hundreds.
- The same tools as the xv6 track and nothing more: a host C compiler,
  the riscv64 gcc toolchain, `qemu-system-riscv64`.
- The project at every lesson builds, compiles that lesson's programs and
  runs them. What a later lesson brings is a stub: the compiler stops with
  `cc: NN.LL: <what> not written yet` and exit status 3, never a crash and
  never wrong code.
- Tests are internal. No benchmark in the core; module 10 measures
  instructions executed.
- The book: Programming Language Pragmatics, 4th edition. Every lesson
  ends with the sections that explain its concept, by number and title,
  as the xv6 lessons end with OSTEP's chapters. No sentence, figure,
  example or exercise of the book goes into a lesson, a diagram or the
  code; the owner's copies stay out of the repository (they are in
  `.git/info/exclude`). The book is not free online, so the lessons name
  the sections and link the author's page, not a text.

## The language

Taken (the commit numbers are upstream's, oldest first):

- every statement: blocks, `if`, `while`, `for` (with a declaration in
  its head), `do`, `switch`, `break`, `continue`, `goto`, `return`;
- every integer operator, with C's precedence: arithmetic, bitwise,
  shifts, comparisons, `&&` `||` `!`, `?:`, the comma, `=` and the `op=`
  forms, `++` and `--` before and after, `sizeof`, casts;
- types: `void`, `_Bool`, `char`, `short`, `int`, `long` (`long long` is
  `long`), signed and unsigned, pointers, arrays (and arrays of arrays),
  structs, unions, enums, functions and pointers to them, `typedef`, the
  full declarator syntax; the usual arithmetic conversions;
- storage: locals, globals, `static` (locals, globals, functions),
  `extern`, tentative definitions, initialisers with braces and strings;
- functions: any number of parameters, structs passed and returned by
  value, variable arguments (`va_start`, `va_arg`, `va_end`);
- the preprocessor: `#include` (both forms, `-I`), `#define` with and
  without arguments, `#undef`, `#` and `##`, `__VA_ARGS__`, `#if`
  `#ifdef` `#ifndef` `#elif` `#else` `#endif`, `defined`, `#error`,
  `__FILE__` `__LINE__` `__func__`, line continuation, `-D`;
- accepted and ignored: `const`, `volatile`, `register`, `restrict`,
  `inline`, and `__attribute__((...))` (xv6's `user.h` uses it; ours).

Left out, each a line in NOTES.md: floating point (commits 139 to 149 and
280; xv6's programs have none); bit-fields; variable-length arrays and
`alloca`; `_Generic`, `typeof`, `_Alignof`, `_Alignas`, `_Atomic`,
thread-local storage; designated initialisers, compound literals, flexible
array members, anonymous structs; wide and UTF strings and `\u` escapes;
every GNU extension upstream marks `[GNU]` (statement expressions, case
ranges, labels as values, `#include_next`, `#pragma once`); inline
assembly; the hash map (commits 285 to 288: lists are fast enough); the
driver and its flags (154 to 157, 276 to 305). Where upstream's own code
uses something left out (its `type.c` builds the basic types as compound
literals), ours is rewritten without it, and NOTES.md says so.

Departures from upstream that are decisions, not cuts: plain `char` is
unsigned, as the RISC-V ABI says; `switch` gets a jump table as well as
upstream's chain of compares (03.07); the scanner and the parser can
print what they made (`--tokens`, `--tree`), which 01 and 02 show.

## Files

```
tracks/cc/
  LICENSE              chibicc's MIT licence
  Makefile             builds ./cc with the host's compiler (HOSTCC)
  cc.h                 Token, Node, Obj, Type, Member; every prototype
  main.c               options, reads the file, runs the phases
  tokenize.c           characters to tokens; error_at, error_tok
  preprocess.c         tokens to tokens (from module 08)
  parse.c              tokens to a tree: declarations, statements,
                       expressions, initialisers, scopes, constant
                       expressions
  type.c               the types, and add_type: a type on every node
  codegen.c            the tree to RISC-V assembly (ours)
  strings.c            format(): printf into a new string
  include/             the compiler's own headers: stdarg.h, stddef.h,
                       stdbool.h (from 09.02)
  ccrun                script: compile, assemble, link with rt/, run in QEMU
  same                 script: the same with gcc as well, and compare (00.03)
  rt/start.S           entry: stack, bss, main, exit through the test device
  rt/link.ld           where the program sits: 0x80000000
  rt/io.c              putchar and getchar on the UART (from 04.01)
  rt/libc.c            printf, strings, malloc: what the tests and the
                       compiler itself need (from 04.01, grows to 09.05)
  rt/file.c            open and read on an archive in memory (09.05)
  rt/include/          the runtime's own libc headers
  tests/               internal checks
  track.py, NOTES.md
```

`./cc [-E] [-I dir] [-D name[=value]] [--tokens] [--tree] [-o file] file.c`
writes assembly to standard output or to `file`. One translation unit a
run. It never reads the host's system headers: a program includes
`rt/include/` (or xv6's headers at 09.04) and the compiler's `include/`.

## The code generator (ours)

- RV64, base integer instructions and multiply/divide, the LP64 ABI, no
  compressed and no floating-point instructions. It writes the usual
  pseudo-instructions (`li`, `la`, `mv`, `call`, `ret`, `j`, `seqz`).
  An assembly file is assembled with the flags of what it links with.
- Expressions: the temporaries `t0` to `t5` are a stack. `gen_expr(node,
  d)` leaves its value in the register at depth `d`; a binary operator
  computes its left side at `d`, its right at `d + 1`. At the sixth the
  left side is pushed to memory, the right side takes its register, and
  the left comes back into `t6`, the spare (02.06).
  This is the scheme of the book's section 15.3.2 (read there). tcc keeps
  a value stack in registers too, as far as I remember: to be read from
  its source before a lesson says so. Upstream's push and pop of every
  value is the other design, set against it in 02.03's "Decide the
  boundary".
- A call does not keep `t` registers, so the live ones are saved around
  it (04.01): the caller-saves half of the convention, seen at work.
- The frame is gcc's at -O0: `s0` is the frame pointer, the return
  address at `-8(s0)`, the caller's `s0` at `-16(s0)`, locals below, `sp`
  kept at a multiple of 16. An offset that does not fit in 12 bits is
  loaded into a register first, from the start.
- `int` arithmetic uses the `w` instructions, so a 32-bit value is always
  sign-extended in its register, as the ABI requires; loads pick `lb`
  `lbu` `lh` `lhu` `lw` `lwu` `ld` by type (06.02).
- Arguments: the first eight in `a0` to `a7`, the rest on the stack. A
  struct of up to 16 bytes travels in one or two registers, a larger one
  by reference to a copy; a struct comes back in `a0` and `a1` or through
  a hidden pointer (07.07). Every case is checked against gcc in both
  directions.
- Variable arguments: the function stores `a0` to `a7` just under the
  arguments that came on the stack, so `va_arg` walks from one into the
  other; `va_list` is a pointer, as the ABI says (09.02). Laid out as gcc
  lays it out, read from `gcc -S`.

## The runtime (ours)

- `rt/start.S`: set `sp`, clear bss, call `main`, write the status to
  QEMU's test device at 0x100000 (0x5555 for 0, else the status shifted
  left 16, or 0x3333), which ends QEMU with that status.
- `rt/io.c`: the UART at 0x10000000. Input ends at a byte 0x04, since a
  serial port has no end of file.
- Up to 09.02 the runtime is compiled by gcc: it is the "code someone
  else compiled" of 04.01. At 09.05 the compiler compiles it too.
- 09.05, the compiler on the bare machine: its command line is the first
  line it reads from the UART; its source files are a ustar archive that
  QEMU puts in memory (`-device loader,file=src.tar,addr=0x88000000`),
  read by `rt/file.c`; its output goes to the UART. So the compiler is
  written against a small libc that exists on both sides: the host's when
  built by the host, `rt/libc.c` when built by itself.

## How the project stands in the first modules

The finished compiler is a pipeline, and the first lessons come before
the pipeline exists. Three forms, kept behind `@from` / `@else` markers
and listed in NOTES.md; no more than these:

1. 00.01 to 00.03: `main.c` alone. The file holds one number; the
   program prints the three lines of assembly that return it.
2. 01.01 to 01.05: `tokenize.c` exists. `main.c` walks the tokens itself
   and compiles sums and differences (upstream's commits 2 and 3);
   `--tokens` prints every token the scanner now knows, with its line and
   column, which is what 01.02 to 01.04 show.
3. From 02.03: tokens, tree, code. At 02.01 and 02.02 the parser exists
   and `--tree` prints what it builds, while form 2 still does the
   compiling. The input is one expression until 03.01, then real C: a
   single `int main() { ... }` with `int` locals, until 04.02 allows any
   function. Every value is a 64-bit integer until module 06 gives nodes
   types (as upstream until its commit 56); on what C defines for `int`
   that gives gcc's answers.

## Modules (core), with the upstream commits each draws on

00 The smallest compiler
  00.01 From a number to assembly (1, 40)
  00.02 What the assembler, the linker and the machine do with it (ours:
        `ccrun`, `rt/start.S`, `rt/link.ld`; the first run)
  00.03 The same answer as gcc: a test for every lesson (ours)
01 Tokens
  01.01 A stream of tokens: numbers, plus and minus (2, 3)
  01.02 Longest match (7, read_punct)
  01.03 Identifiers and keywords (10, 11, convert_keywords)
  01.04 Comments, character constants and strings (34 to 38, 43, 73, 80)
  01.05 Errors that point at the source (4, 19, 46)
02 Expressions
  02.01 A grammar, and a function for each rule (5: sums, and the tree
        they build; `--tree` ours)
  02.02 The syntax tree (5: `*`, `/` and parentheses; precedence is the
        tree's shape)
  02.03 Code from a tree: registers as a stack (ours)
  02.04 Precedence and associativity: the whole table (83, 84, 94)
  02.05 Unary operators and comparisons (6, 7, 81, 82)
  02.06 Out of registers: spilling to memory (ours)
03 Statements and control flow
  03.01 Statements, and a frame for local variables (9 to 14, 22)
  03.02 Assignment: a place and a value (10, 77 to 79)
  03.03 if and else (15)
  03.04 while, for and do (16, 17, 76, 124)
  03.05 `&&`, `||` and `?:` (48, 85, 95)
  03.06 break, continue and goto (89 to 92)
  03.07 switch: a chain of compares, then a jump table (93; table ours)
04 Functions
  04.01 Calling a function someone else compiled (23, 24, 125)
  04.02 Defining one: prologue, frame and epilogue (25, 26)
  04.03 Parameters, in registers and past the eighth (198, 199)
  04.04 Recursion, and reading the stack (60, 69, 129)
  04.05 The other way: gcc's code calls yours (ours)
05 Names, scopes and storage
  05.01 Blocks: a stack of scopes (44)
  05.02 Global variables (32, 111, 115, 265)
  05.03 Constant expressions (96, 105, 135)
  05.04 static locals (120)
  05.05 extern, static and prototypes (75, 116, 117, 123)
06 Types and pointers
  06.01 A type on every node (type.c, add_type; 20)
  06.02 char, short, int and long (33, 56 to 58, 63, 66, 72, 130 to 133)
  06.03 Conversions and casts (67, 68, 70, 71, 126, 134)
  06.04 Pointers (20, 21, 61)
  06.05 Reading declarators (59, 62, 138)
  06.06 typedef (64, 65, 90)
  06.07 Type errors (the error_tok calls of the above, gathered)
07 Arrays, strings and structs
  07.01 Arrays (27 to 29, 86, 87)
  07.02 sizeof, and arrays of arrays (28, 30, 65)
  07.03 String literals (34, 193)
  07.04 Structs (49 to 53, 88)
  07.05 Unions and enums (54, 74)
  07.06 Initialisers (97 to 110)
  07.07 Structs by value (55, 200 to 203; passing is ours)
08 The preprocessor
  08.01 `#include` (158 to 162, 184 to 186)
  08.02 `#define` (167, 168, 207, 208)
  08.03 Macros with arguments (172 to 175, 177, 178, 190)
  08.04 The hide set (170, 176)
  08.05 `#if` and `#ifdef` (163 to 166, 169, 171, 180, 181, 187)
  08.06 Headers and separate compilation (183, 188, 189, 191, 195)
09 Real programs
  09.01 Function pointers (151 to 153)
  09.02 Variable arguments (127, 128, 196; layout ours)
  09.03 A test suite you did not write (136, 219; c-testsuite)
  09.04 On xv6: its user programs, built by your compiler (ours)
  09.05 The compiler compiles itself (150, 197)

The list is the direction. Where upstream's code does not divide this way
(a function that does two lessons' work), merge or split lessons to fit
the code and say so in NOTES.md. Do not restructure upstream's code to
fit the list. The order is ours and not upstream's (it reaches pointers
at commit 20 and block scope at 44), so a region's code may be simpler at
its own lesson than in the finished file; that is what `@from` is for.

## The book, lesson by lesson (modules 00 to 02)

The sections of Programming Language Pragmatics, 4th edition, that each
lesson ends with, read in the text before being listed here. A lesson
names them by number and title and says nothing the section does not.

  00.01  1.4 Compilation and Interpretation; 1.6 An Overview of
         Compilation (1.6.3 Target Code Generation)
  00.02  15.4 Address Space Organization; 15.5 Assembly; 15.6 Linking
  00.03  1.6.2 Semantic Analysis and Intermediate Code Generation (what
         a language defines and what it leaves to run time)
  01.01  2.1.1 Tokens and Regular Expressions; 2.2 Scanning
  01.02  2.2 Scanning (the longest possible token)
  01.03  2.2 Scanning
  01.04  2.2 Scanning (comments)
  01.05  2.2.4 Lexical Errors; 2.3.5 Syntax Errors (companion site)
  02.01  2.1.2 Context-Free Grammars; 2.3.1 Recursive Descent
  02.02  2.1.3 Derivations and Parse Trees; 1.6.2 (the syntax tree)
  02.03  15.3 Code Generation (15.3.1 An Attribute Grammar Example)
  02.04  6.1.1 Precedence and Associativity
  02.05  6.1 Expression Evaluation
  02.06  15.3.2 Register Allocation

## Extensions (each `optional: true`; not started)

Each stands on the finished core and is independent of the others, as
the kilo track's are. Direction only; each gets its design when the owner
starts it.

10 An optimising back end: a second `codegen`, chosen by a flag, through
   three-address code in basic blocks, liveness and linear-scan register
   allocation, value numbering and a peephole. Measured in instructions
   executed, read from the machine's own counter (`minstret`, exact under
   `-icount shift=0`). Mechanisms from QEMU-sized real systems: QBE first,
   then what gcc and LLVM do differently.
11 An assembler and a linker: for the instructions and pseudo-instructions
   the compiler writes; ELF objects that binutils reads, and binutils'
   objects that ours links.
12 A debugger's view: DWARF line tables, frame information and variable
   locations, checked by reading them back with the toolchain's tools; a
   debugger session where one is installed (there is no riscv gdb on the
   owner's machine today).
13 Beyond call and return: `setjmp` and `longjmp`, exceptions on them,
   coroutines that switch stacks as xv6's `swtch` does.

## Tests and checks

- Fixtures in `track.py`: `compile(t, src)` gives the assembly or the
  error; `run(t, src, stdin, files)` builds with ours and runs in QEMU;
  `same(t, src)` builds with gcc as well and fails on any difference in
  output or status; `link(t, ours, gccs)` builds a program out of files
  from both compilers; `error(t, src)` gives the message and where it
  points.
- One test per lesson, a set of small programs that need that lesson's
  code, every one through `same`. With the lesson cut out the test fails
  at the stub. Before 04.01 a program can only return a status; from
  04.01 it prints.
- Interop tests for 04.01, 04.03, 04.05, 07.07 and 09.02: every argument
  shape (count, width, sign, struct size) called ours-to-gcc and
  gcc-to-ours.
- Compile errors: the message, the line and the caret's column, for every
  error a lesson introduces; a wrong program never reaches the assembler.
- 09.03: c-testsuite's single-exec tests at commit 5c72756, fetched once
  into a cache outside the project and checked by hash, not stored: 150
  come from scc and 69 from tinycc, under those projects' licences. The
  9 that use floating point are skipped by name; the count that passes
  is asserted, and every skip is listed with its reason.
- 09.04: the xv6 track's finished tree with its user programs built by
  ours and its kernel by gcc, booted, a script of commands run, and the
  console compared with the all-gcc system's.
- 09.05: stage 2 against stage 3, byte for byte, for every source file.
  Slow, so it runs under `./learn test cc` and is marked slow.
- A fuzz run before the lessons are written: random expressions and
  random argument lists through `same`, under the host's sanitizers for
  the compiler itself.
- `./learn check-skeleton cc`, `check-timeline cc` (at each lesson: build
  the compiler, compile that lesson's sample, run it), `./learn check`,
  `./learn verify`.

## Build order for the agents

Lessons follow each code step (the owner, 2026-11-14: module by module),
and each step's brief carries the design, not a request for one.

1. Workbench and modules 00 to 02: `track.py`, the runtime, the scripts,
   the three early forms, the scanner, expressions and the first code
   generator; their tests; then their lessons and art.
2. Modules 03 and 04: statements and functions, with the interop tests;
   lessons and art.
3. Modules 05 to 07: scopes, types, composite types; lessons and art.
4. Modules 08 and 09: the preprocessor, the test suite, xv6, itself;
   lessons and art.
5. The read: every lesson on the site, light and dark and at 390 px; the
   full internal run on macOS and on Linux.

Claims about what gcc, clang, tcc or QBE do are read from their source or
their output at a named version and recorded in NOTES.md before a lesson
states them. Agents do not open the owner's copies of the book.

## Checked before this plan was written (2026-11-24)

On the owner's Mac (riscv64-elf-gcc 15.2.0, QEMU 10.2.1), with a
throwaway program outside the repository:

- A program linked at 0x80000000 with a five-line `start.S` runs under
  `qemu-system-riscv64 -machine virt -bios none -nographic -kernel`, and
  what it writes to the test device becomes QEMU's exit status (42, 7
  and 0 tried). One run takes 0.02 s.
- Input piped to QEMU arrives on the UART; a ustar archive given to
  `-device loader` at 0x88000000 is readable there.
- `minstret` read around a loop is the same on every run under
  `-icount shift=0` (12022 for 1000 iterations) and differs between runs
  without it.
- riscv64-elf-gcc treats plain `char` as unsigned.
- The RISC-V calling convention (riscv-elf-psabi-doc, `riscv-cc.adoc`,
  master at 56561cb3e733) says what "The code generator" above relies
  on: arguments in a0 to a7, the first two also for return values; a
  32-bit value sign-extended in its register, signed or unsigned; an
  aggregate of up to 16 bytes in a pair of registers and a larger one by
  reference; `char` unsigned; `va_list` a `void *` over arguments laid
  out as on the stack; the stack pointer aligned to 16 bytes at entry.
- chibicc: the commit list above; it first compiles itself at commit 197;
  its preprocessor uses hide sets; its code generator pushes and pops
  every value on the machine stack; its `type.c` makes the basic types
  with compound literals; the names this plan uses (`read_punct`,
  `convert_keywords`, `add_type`, `error_at`, `error_tok`, `format`,
  `enter_scope`, `gen_addr`, `gen_expr`, `gen_stmt`, `codegen`,
  `__va_area__`) are in its source at commit 205.
- c-testsuite at 5c72756: 220 single-exec tests, 9 with floating point,
  96 tagged needs-cpp and 63 needs-libc; 150 name scc as their origin
  and 69 tinycc.
- The xv6 track's user programs use no floating point and no inline
  assembly; `user.h` and `sh.c` use `__attribute__`. Its file system is
  2000 blocks and a file at most 268, and its machine has 128 MB, which
  is why 09.05 runs on the bare machine and not on xv6.

## Risks and open points

- 09.05 is the largest risk. The compiler's source must stay inside the
  language it compiles and inside the small libc of `rt/`, from the first
  step, or the last lesson needs a rewrite. Step 1 sets that rule and a
  check for it (the compiler's own files go through `same`'s front half
  as soon as the language allows).
- Time for 09.05 under emulation is not measured. If stage 3 takes
  minutes, the lesson compiles one file on the machine and the test does
  the rest less often.
- 09.04: whether the xv6 track's objects and ours agree on assembler
  flags is to be checked first thing in step 4; `usertests` is in if it
  compiles, and said so if not.
- Struct passing has many cases, and a wrong one corrupts memory quietly.
  The interop tests are generated, not written by hand.
- c-testsuite's tests are not ours to store: scc's and tinycc's licences
  are still to be read before the lesson says more than "fetched".
- Upstream rewrites its history, so the commit numbers above are true of
  90d1f7f only. NOTES.md records the hash.
- The site and README: `./learn map`, README's "The book" and "Credits",
  and NOTICE change when step 1 lands, not before. README has another
  session's uncommitted edits today.
