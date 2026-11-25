# Plan: track `lang` - your own language, chapter by chapter

Status: plan (direction set by Fable; implementation by Opus agents).
Outline: `outlines/lang.md` (it moves to `plans/lang-outline.md` when
`tracks/lang` lands, as cc's did). Chapter 1 is being built; nothing else is.

## What the owner asked for (2026-11-25)

"Someone reading the book should do a code after reading a chapter and
they should build their own language step by step." And: "We need to
follow the pdf exactly and add the code and execution steps." Then: "write
the plan and start chapter 1".

The book is Michael L. Scott, Programming Language Pragmatics, 4th edition
(Morgan Kaufmann, 2016). So this track is a companion to it, read with it
open: module NN is chapter NN, lessons come in the order of the chapter's
sections, each lesson names what to read first, then gives code and the
commands that run it with what they print.

## What the reader ends with

A small language of their own (the track calls it Mote; lesson 01.02 is
where the reader picks a name), with every piece the book describes built
by hand in C: after chapter 1 alone, a machine, two interpreters, a
translator to C, a compiler with all its phases, and a check that every
way of running a program gives the same answer. Each later chapter makes
one part deeper or adds what that chapter is about.

## Decisions

- Track id `lang`, kind `language`, title "Your own language, chapter by
  chapter". Modules are numbered from 01 so that module NN is chapter NN.
  There is no module 00.
- The order is the book's, never the code's convenience. Where the book
  shows something before it explains how (chapter 1 walks one program
  through every phase of a compiler; chapter 2 then explains scanning and
  parsing), the reader builds a first, small version when the book shows
  it and the real one when the book explains it. See "The spiral" below.
- Every lesson starts with "Read first": the section, and the pages in the
  4th edition. It says which of the book's examples and figures the lesson
  makes real ("Example 1.21 lists a C program's tokens; here are your
  program's"), by number only.
- Nothing of the book is copied: no sentence, figure, example or exercise.
  The owner's copies in the repo root are never committed and are not
  opened by the agents; what a lesson needs from the book is in this plan
  and in the lesson design, in our words. Chapters 5 and 17 and the
  sections marked as on the companion site are not in the printed book;
  their lessons say where to find them.
- The running example of chapter 1 is the book's own: the greatest common
  divisor of two numbers by repeated subtraction. The algorithm is
  Euclid's; every program text here is written by us.
- Written in C11 with the C library, built by `make` with the host's `cc`.
  No other tool is needed: no RISC-V toolchain, no QEMU. The machine the
  compiler aims at is a program of the track's own (`machine.c`).
- The code is the course's own. Nothing is copied from `tracks/cc` (its
  front end is derived from chibicc and carries chibicc's licence); the
  scanner and parser take chibicc's shape (a list of tokens, a function
  for each rule) and no more. `UPSTREAM` in `track.py` names the RISC-V
  instruction set manual (the machine's instructions and their meaning)
  and chibicc (shape only), both `"derived": False`.
- The machine's assembly is real RISC-V (RV64) text as the GNU assembler
  takes it: the same mnemonics, registers and pseudo-instructions. In
  chapter 1 the machine runs that text directly; chapter 5 gives the
  instructions their bits and puts the program in memory.
- What every lesson is held to: all the ways of running a program agree.
  `./agree` runs every program in `programs/` each way that exists and
  compares what it prints with the expected output.
- Mechanisms come from real systems and claims about them are read from
  their source before a lesson states them (recorded in `NOTES.md`).

## The spiral: chapter 1 builds a small whole

Chapter 1 of the book is an overview: it shows machine language and
assembly, sets interpretation against compilation, and in section 1.6
takes one program through scanning, parsing, semantic analysis, code
generation and code improvement. The reader does the same, small. Later
chapters come back to each part:

| Built in chapter 1 | Lesson | Comes back in |
|---|---|---|
| The machine (assembly text, registers) | 01.01, 01.10 | chapter 5: bits, memory, addressing; 15: assembler, linker |
| The first interpreter (runs the text) | 01.03 | stays as it is; chapter 14 (scripting) looks back at it |
| The translator to C | 01.04 | stays as it is; chapter 15 (linking, the address space) |
| The prompt and `agree` | 01.05 | every chapter adds programs; chapter 16: debugger, profiler |
| The scanner, by hand | 01.06 | chapter 2: regular expressions, automata, a table-driven scanner |
| The parser and the parse tree | 01.07 | chapter 2: grammars, predict sets, table-driven and bottom-up parsers, error recovery |
| The syntax tree, the symbol table, one check | 01.08 | chapter 3: scopes; chapter 4: attributes, action routines; chapter 7: types |
| The tree-walking interpreter | 01.09 | chapters 3, 6 to 14: where the language grows |
| The code generator | 01.10 | chapter 15: intermediate forms, the whole back end |
| The improver (variables in registers) | 01.11 | chapter 17: the real passes |

Two consequences for the outline's later modules: lessons 02.04 and 02.07
(the scanner and the parser "written by hand") become the principled
rebuild of 01.06 and 01.07, and 05.03 grows the machine of 01.01 instead
of starting one. The outline's lesson lists for modules 02 to 17 are
revised when each module is planned.

The language grows where the interpreter is. The code generator and the
two programs of 01.03 and 01.04 stay at chapter 1's language until
chapter 15 rebuilds the back end; a program that uses something later is
turned away by them with "not in the compiled language yet", and `agree`
runs each program only the ways that can take it.

## The language at chapter 1

```
program = { stmt } .
stmt    = name ":=" expr
        | "read" name
        | "write" expr
        | "if" cond "then" { stmt } [ "else" { stmt } ] "end"
        | "while" cond "do" { stmt } "end" .
cond    = expr ( "==" | "!=" | "<" | ">" | "<=" | ">=" ) expr .
expr    = term { ( "+" | "-" ) term } .
term    = factor { ( "*" | "/" ) factor } .
factor  = number | name | "(" expr ")" | "-" factor .
```

- Names: a letter or `_`, then letters, digits and `_`; not one of the
  keywords `read write if then else end while do`. Numbers: decimal
  digits; the value must fit in 63 bits.
- `#` starts a comment that runs to the end of the line. Spaces, tabs and
  line ends separate tokens and mean nothing else.
- Values are 64-bit signed integers. `+ - *` wrap around; `/` rounds
  toward zero; dividing by zero is an error when the program runs.
- `read x` takes the next whole number of the input; `write e` prints the
  value and a line end. A name comes into being the first time the text
  gives it a value (`read` or `:=`).
- A condition is not a value: it appears only in `if` and `while`
  (booleans as values come with chapters 6 and 7).
- Static rule (checked before the program runs, from 01.08): a name used
  in an expression must have been given a value earlier in the text.
  Dynamic rule (checked while it runs, by the interpreters): it must have
  a value at that moment. Compiled code does not check the second; the
  lesson says so and what the check would cost.
- The operators are C's on purpose: the translator of 01.04 passes an
  expression through untouched.
- The two programs of 01.03 and 01.04 have no scanner, so they ask for
  more: one statement to a line, with `while c do`, `if c then`, `else`
  and `end` each on a line of their own. Every program in `programs/` is
  written that way so that all ways can run it.

The book's GCD program in this language, `programs/gcd.mote`:

```
# gcd.mote: the greatest common divisor of two numbers
read i
read j
while i != j do
    if i > j then
        i := i - j
    else
        j := j - i
    end
end
write i
```

## The machine at chapter 1

`./machine [--count] [--trace] FILE.s` reads assembly, runs it, and ends
with the status the program gave. The program's input is stdin, its
output stdout.

- 32 registers of 64 bits, by their RISC-V names: `zero` (always 0), `ra`,
  `sp`, `gp`, `tp`, `t0`-`t6`, `s0`-`s11`, `a0`-`a7`.
- A line is a label (`name:`), an instruction, or both; `#` starts a
  comment. Execution starts at `main:`.
- Instructions at 01.01: `li rd, n`; `mv rd, rs`; `add`, `sub`, `mul`,
  `div rd, rs1, rs2`; `neg rd, rs`; `beq`, `bne`, `blt`, `bge`, `bgt`,
  `ble rs1, rs2, label`; `beqz`, `bnez rs, label`; `j label`;
  `call label`; `ret`. `div` by zero gives -1, as RISC-V's does.
- Added at 01.10, with the memory: `addi rd, rs, n`; `ld rd, n(rs)`;
  `sd rs2, n(rs1)`. Memory is 1 MiB of bytes; `sp` starts at its top; an
  address outside it is a fault.
- Every instruction has an address, 4 bytes after the one before. `call`
  puts the address of the next instruction in `ra`; `ret` goes to `ra`.
- Library routines, part of the machine ("extensions to the instruction
  set", as the book puts it in its Example 1.11): `call getint` (the next
  number of the input into `a0`), `call putint` (prints `a0` and a line
  end), `call exit` (ends the program, status `a0`), and from 01.10
  `call divzero` (prints "line N: division by zero" with N from `a0`,
  status 1). They keep every register but `a0` and `ra`.
- `--count` prints the number of instructions executed on stderr when the
  program ends. Each line of assembly counts as one, although a real
  RISC-V machine needs two for `call` and for a large `li` (chapter 5).
  `--trace` prints each instruction as it runs and the register it changed.
- Errors (unknown instruction, bad register, undefined label, running off
  the end, a bad address): `machine: FILE:LINE: message`, status 1.

`programs/gcd.s`, written by hand at 01.01, keeps `i` in `s1` and `j` in
`s2` and never touches memory: 15 instructions. Lesson 01.11's improved
code is set beside it.

## Chapter 1, lesson by lesson

Pages are the 4th edition's. "Makes real" names the book's example or
figure by number; the content is ours.

**01.01 A machine, and a program written in its language** (the chapter's
opening, pages 5 to 7). Makes real: Examples 1.1 and 1.2. Built:
`machine.c` (registers, the instruction table, labels, the loop that runs,
the library routines), `programs/gcd.s`, `programs/gcd.in` (`1071 462`),
`Makefile`. Run: `./machine programs/gcd.s < programs/gcd.in` prints 21;
`--count` and `--trace`. (Example 1.1, the bytes, is lesson 01.02's on
the reader's real computer, and chapter 5's for this machine.)

**01.02 Your language, and the programs you want it to run** (1.1 to 1.3,
pages 7 to 16). Makes real: Figure 1.2's top third, and the criteria of
1.1 applied to a language of the reader's own. Built: `rt.h`, `rt.c`
(`getint`, `putint`: the book's "trivial I/O routines"), `programs/gcd.c`
(the program in C, ours), and the programs in the new language with their
input and expected output: `gcd`, `sum`, `primes` (`.mote`, `.in`, `.out`).
Run: `make gcd`, `./gcd < programs/gcd.in`; then what the C compiler made
of it on the reader's own computer, as assembly and as bytes (shown from
one computer, said to differ on theirs, not replayed). Only gcd has a C
version. The lesson names the language, places it in the
book's families (it starts as a von Neumann language; the functional and
logic forms of GCD are shown as where chapters 11 and 12 take it, in the
text only), and weighs it against 1.1's list.

**01.03 An interpreter: the program run from its text** (1.4 to Example
1.10, pages 17 to 19). Makes real: Examples 1.8 and 1.10. Built: `mote0.c`,
a pure interpreter with no translator in front: it executes a line at a
time straight from the characters, looks every name up in a table each
time it is used, and reads a loop's lines again on every pass. `--count`
prints the number of lines it read. Run: `./mote0 programs/gcd.mote <
programs/gcd.in`. The book's remark about comments slowing early Basics is
an experiment here: a comment inside the loop raises the count.

**01.04 A translator: to C, and from there to the machine** (1.4 from
Example 1.11, pages 19 to 24). Makes real: Examples 1.7 and 1.11 to 1.14.
Built: `mote2c.c` (line for line into C, with the names it finds declared
at the top), `motec` (a script: translate, compile, link with `rt.o`). Run:
each stage by hand first (`./mote2c`, `cc -E`, `cc -S`, `cc -c`, the link),
then `./motec programs/gcd.mote` and `build/gcd`. Then the two set
against each other on a long run of `sum`: how long each takes, and what
each says about a mistake (the translator passes one through and the C
compiler complains about a C file: by the book's own test this is a
preprocessor, not yet a compiler). Bootstrapping, just-in-time compiling
and microcode (Examples 1.15 to 1.18) are read, not built; the lesson says
where each returns.

**01.05 The tools around a language: a prompt and a test runner** (1.5,
pages 24 to 25). Built: the prompt in `mote0.c` (`./mote0` with no file: a
line at a time, a block held until its `end`, an error reported and the
prompt kept), and `agree`. Run: a session at the prompt; `./agree`.

**01.06 The phases of a compiler, and the first: a scanner** (1.6 and the
first half of 1.6.1, pages 26 to 28). Makes real: Figures 1.3 and 1.4 (as
the driver's order of calls) and Example 1.21. Built: `mote.h`, `main.c`
(the phases in order, each option stopping after its phase), `scan.c`. Run:
`./mote --tokens programs/gcd.mote`. From here a program need not keep to
one statement a line.

**01.07 The parser: tokens into a tree** (the rest of 1.6.1, pages 28 to
32). Makes real: Examples 1.22 and 1.23 (Figure 1.5). Built: `parse.c`:
a function for each rule, each making a node named after its rule, so the
result is the parse tree whole. Run: `./mote --parse-tree`, and a count of
its nodes against the program's 11 lines; a syntax error with its place.

**01.08 Semantic analysis: the syntax tree and the symbol table** (1.6.2
to Example 1.24, pages 32 to 34). Makes real: Figure 1.6. Built:
`analyze.c`: the parse tree walked once into a syntax tree, each name
entered in the symbol table and each use pointing at its entry, and the
static rule checked. Run: `./mote --tree`, `./mote --symbols`; a program
that breaks the rule.

**01.09 Walking the tree: an interpreter built on the front end** (1.6.2,
Example 1.25, page 33). Makes real: Figure 1.4 and Example 1.25. Built:
`interp.c`; `agree` gains a way. Run: `./mote programs/gcd.mote`; the
dynamic rule caught; this interpreter against `mote0` on the long run.

**01.10 Target code: loads, stores, tests and branches** (1.6.3, pages 34
to 36). Makes real: Example 1.26 (Figure 1.7). Built: memory, `addi`, `ld`,
`sd` and `divzero` in `machine.c`; `gen.c`: a slot in memory for every
variable, expressions in `t0` to `t6` used as a stack, a load for every
use and a store for every assignment, a branch on the opposite condition,
a generated check before each division; `agree` gains a way. Run: `./mote
-S programs/gcd.mote > build/gcd.s`, `./machine --count build/gcd.s`.

**01.11 Code improvement: variables kept in registers** (1.6.4, pages 36
to 37). Makes real: Example 1.27. Built: `improve.c` (counts each
variable's uses and gives the most used a register, up to the eleven of
`s1` to `s11`), and the paths in `gen.c` that use a variable's register
directly; `-O`; `agree` gains a way. Run: the same program with and
without `-O`, the two listings and the two counts, and both against
`programs/gcd.s` from 01.01.

Section 1.7 has no lesson; the module's README is its summary.

## Files (chapter 1)

```
Makefile          01.01   builds what exists
machine.c         01.01   the machine; memory and loads at 01.10
programs/         01.01   gcd.s, gcd.in; from 01.02 gcd.c and the .mote programs
rt.h rt.c         01.02   getint, putint for C programs
mote0.c           01.03   the first interpreter; the prompt at 01.05
mote2c.c          01.04   the translator to C
motec             01.04   script: translate, compile, link
agree             01.05   script: every program, every way
mote.h            01.06   what the phases share
main.c            01.06   the driver: the phases in order
scan.c            01.06
parse.c           01.07
analyze.c         01.08
interp.c          01.09
gen.c             01.10
improve.c         01.11
NOTES.md                  for the lesson writers; hidden from learners
```

`build/` holds what `motec` and the lessons make and is never part of the
project.

## Interfaces

`mote.h` (names may change where the code needs it; the builder reports):

```c
typedef enum { T_NAME, T_NUMBER, T_KEYWORD, T_OP, T_EOF } TokenKind;
typedef struct Token Token;
struct Token { TokenKind kind; const char *text; int len; long value;
               int line, col; Token *next; };
Token *scan(const char *file, const char *src);                 /* 01.06 */

typedef struct Parse Parse;        /* a use of a rule, or a token */
struct Parse { const char *rule; Token *tok; Parse *kids, *next; };
Parse *parse(Token *tok);                                       /* 01.07 */

typedef struct Symbol Symbol;
struct Symbol { int index; const char *name; int len; int line, col;
                long value; bool has_value;                     /* 01.09 */
                int offset;                                     /* 01.10 */
                int uses; const char *reg;                      /* 01.11 */
                Symbol *next; };

typedef enum { N_NUM, N_VAR, N_NEG, N_ADD, N_SUB, N_MUL, N_DIV,
               N_EQ, N_NE, N_LT, N_GT, N_LE, N_GE,
               N_ASSIGN, N_READ, N_WRITE, N_IF, N_WHILE } NodeKind;
typedef struct Node Node;
struct Node { NodeKind kind; Token *tok; long value; Symbol *sym;
              Node *lhs, *rhs;          /* operands; a condition's sides */
              Node *cond, *body, *els;  /* if and while */
              Node *next; };            /* the next statement */
Node *analyze(Parse *tree);                                     /* 01.08 */
Symbol *symbols(void);
void interpret(Node *prog);                                     /* 01.09 */
void generate(Node *prog);                                      /* 01.10 */
void improve(Node *prog);                                       /* 01.11 */
```

`./mote [--tokens | --parse-tree | --tree | --symbols | -S [-O]] FILE`.
With no option it runs the program (from 01.09; before that it is a usage
error that names the options there are). Errors: `FILE:LINE:COL: message`
on stderr, status 1; `mote0` and `mote2c` know lines only
(`FILE:LINE: message`). Usage errors: status 2.

What the options print:

- `--tokens`: a token a line, `LINE:COL KIND TEXT` (`3:9 op !=`), ending
  with `eof`.
- `--parse-tree`: a node a line, two spaces deeper for each level; a rule
  by its name, a token as `KIND TEXT`.
- `--tree`: statements a line, indented by nesting; expressions in
  prefix form on the statement's line, each variable with its index in
  the symbol table (`while (!= i#1 j#2)`).
- `--symbols`: `INDEX NAME LINE:COL` (where it was first given a value).
- `-S`: assembly for the machine on stdout, with the variable's name in
  a comment on each load and store.

## Chapters 2 to 17, in brief (direction; planned one at a time)

- 2: the syntax written down (token definitions, a grammar file), then
  each half of the front end a second way from that description; the
  second way must print the same tokens and the same tree as the first.
- 3: blocks, functions, nested scopes, closures, modules, a switch for
  dynamic scope: in the tree-walker, with the symbol table grown.
- 4: attributes and action routines: the parser builds the syntax tree
  itself and the parse tree of 01.07 becomes an option; types `int` and
  `real` and the conversions between them.
- 5: the machine gets bits: numbers and instructions encoded, the program
  in memory.
- 6 to 14: the language grows in the interpreter (control flow, types,
  composite types and collectors, calls and exceptions, objects,
  functional and logic programming, threads, scripting).
- 15: the back end rebuilt for what the language has become; an
  assembler and a linker.
- 16: a bytecode machine, a debugger, a profiler. 17: the improver's
  real passes, measured in instructions executed.

Not a goal: the language compiling itself. The book's bootstrapping
(Example 1.15) is read; a self-hosting step could be an extension after
chapter 15.

## Tests and checks

- A test per lesson (`tests/NNLL_title.py`), each driving the real
  programs: 01.01 the machine against Python's `math.gcd` on many pairs,
  every instruction, every error; 01.03 `mote0` on the three programs and
  on each kind of error; and so on, one per lesson, failing at the stub
  ("lang: NN.LL: ... not written yet", status 3) when that lesson's code
  is cut out.
- `tests/proggen.py` and `tests/fuzz.py`: random programs of chapter 1's
  language that always stop (bounded loops, no division by zero), run
  every way there is at that lesson and against a reference written in
  Python. All must print the same.
- The sources build with `-Wall -Wextra -Werror`; `LANG_SANITIZE=1` runs
  the tests on binaries built with AddressSanitizer and UBSan.
- If a RISC-V `as` is installed, every `.s` the track holds or generates
  must assemble with it (the text is the real thing); skipped otherwise.
- `./learn test lang`, `check`, `check-skeleton`, `check-timeline`,
  `verify lang`, as for every track. The project at every lesson builds
  and passes every test up to that lesson.

## Art

Module 01's cover and icon exist (`outlines/lang/01/`). Every lesson gets
the map and its figures in the same pass as its text. The map is the
system as it stands at the end of chapter 1: the source text at the top;
under it three roads (the first interpreter; the translator, the C
compiler and the linker; the phases, forking into the tree-walker and the
code generator); the machine at the bottom; the prompt and `agree` at the
side. Each lesson's piece is in the accent colour. Figures are made by
generators under `art/lang/` that run the real programs and assert the
values they draw. The figures of each lesson are set out in the lesson
design (`plans/lang-01-lessons.md`).

## Build order for the agents

1. Code, tests, `track.py`, `NOTES.md` for chapter 1 (one Opus agent, a
   worktree). The outline moves to `plans/lang-outline.md` with module
   01's lesson list replaced by the eleven above.
2. Lessons, module README and art, by lesson range in parallel (Opus
   agents, worktrees), from the lesson design; each lesson replayed with
   `./learn verify`.
3. Review and a read of the eleven lessons in order, by Fable.

## Checked before this plan was written (2026-11-25)

- Chapter 1 of the book read whole (the owner's copy): its opening and
  sections 1.1 to 1.7, with page numbers and example numbers as used
  above.
- The harness has no rule that a track starts at module 00 (seen in
  `harness/core.py`, `harness/cli.py`, `harness/outlines.py`; the builder
  confirms with `./learn check`).
- RISC-V's `div` by zero gives -1 and does not trap; `bgt`, `ble`, `beqz`,
  `bnez`, `li`, `mv`, `neg`, `j`, `call`, `ret` are pseudo-instructions of
  the GNU assembler. From memory of the manual; the builder reads the
  manual and records it in `NOTES.md` before a lesson says it.

## Risks and open points

- Chapter 1 is eleven lessons, where the outline had four. It is the
  price of following section 1.6: the book takes a program through every
  phase, so the reader does. The owner has not seen this count yet.
- The first interpreter and the translator are kept at chapter 1's
  language for good. If they come to feel like dead weight in later
  chapters they move to a folder of their own; they are not deleted,
  because 01.09 and 01.10 are measured against them.
- The compiled language lags the interpreted one from chapter 3 to
  chapter 15. `agree` says which ways ran each program, so the gap is
  visible and not hidden.
- Wall-clock comparisons (01.04, 01.09) differ by computer; the lessons
  show one real run, say so, and are not replayed. The counts (`--count`
  of `mote0` and of the machine) are exact and are replayed.
- The translated C leaves division by zero and the overflow of the most
  negative number divided by -1 to the C compiler and the processor. No
  program in `programs/` does either; the lesson names the gap.
