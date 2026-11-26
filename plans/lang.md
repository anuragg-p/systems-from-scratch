# Plan: track `lang` - your own language, chapter by chapter

Status: plan (direction set by Fable; implementation by Opus agents).
Outline: `plans/lang-outline.md` (moved from `outlines/lang.md` when
`tracks/lang` landed, as cc's was). Chapter 1's code is built (see "Chapter
1 as built" at the end); its lessons are not written yet.

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
`s2` and never touches memory: 14 instructions. Lesson 01.11's improved
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

**01.05 The tools around a language: a prompt and a checker** (1.5,
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
  phase, so the reader does. The owner, shown the eleven on 2026-11-25:
  "eleven lessons is fine, go ahead".
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

## Chapter 1 as built (2026-11-25)

Step 1 of the build order is done: `tracks/lang/` holds chapter 1's code,
a test per lesson, `track.py`, `NOTES.md`, `.gitignore` and the art; no
lesson `.md` is written yet. `tracks/lang/NOTES.md` has the detail: every
sample command's output, the numbers, the formats, what was read in the
RISC-V manuals.

What exists, in lines as the track holds them (as the site shows them at
01.11, without markers and region instructions, in parentheses): Makefile
62, machine.c 470 (404), programs/ (gcd.s, gcd.in, gcd.c, and gcd, sum,
primes as .mote .in .out), rt.h 6, rt.c 52, mote0.c 481 (405), mote2c.c
209 (186), motec 25, agree 80, mote.h 89, main.c 228 (179), scan.c 132,
parse.c 172, analyze.c 150, interp.c 103, gen.c 189 (151), improve.c 46;
tests/ with eleven tests, proggen.py (a reference in Python and a
generator of random programs) and fuzz.py. Module 01's cover and icon are
copied into `tracks/lang/lessons/01-introduction/` by
`art/outlines/lang_art.py`, the track's art.svg and icon.svg into
`tracks/lang/`. The outline is `plans/lang-outline.md`, with module 01's
lessons the eleven above.

The numbers: gcd on 1071 462 runs 53 instructions by hand (gcd.s), 142
naive (`mote -S`) and 61 improved (`mote -S -O`); `mote0 --count` reads
88 lines for gcd, 409 for sum on 100, 844 for primes on 30; gcd.mote's
parse tree has 64 nodes for its 11 lines. One timing, on an Apple M4 Pro,
sum on n = 3000000: mote0 0.26 s, mote 0.03 s, motec's program 0.002 s,
the machine 0.14 s naive and 0.06 s improved.

Checks, all passing: `./learn test lang` (11 of 11), the same with
`LANG_SANITIZE=1` (ASan and UBSan), `./learn check-skeleton lang` (each
lesson cut out fails its test at the stub), `./learn check-timeline lang`
(the project at each of the 11 lessons builds and boots, its samples
checked exactly), `./learn run lang --at NN.LL` for each lesson, the
project at each lesson built with `-Wall -Wextra -pedantic -Werror`, every
.s through riscv64-elf-as, and `tests/fuzz.py` on 2000 random programs,
five ways each, with no disagreement (seed 7, on the final code; an
earlier run of seed 1 also had none, and the first run of seed 7 found a
fault of the generator's, not of the code: see NOTES.md). `./learn check`
reports only that the eleven lessons have no doc yet.

Departures (reasons in NOTES.md):

- Four files are over their ceilings: machine.c, mote0.c, mote2c.c and
  main.c (figures above). No function is long; the size is the errors,
  --trace and --count, the routines, the prompt, and the usage lines that
  change by lesson.
- gcd.s, the text given for 01.01, has 14 instructions, not 15.
- getint (and `read`) has a second error, `not a number`, everywhere.
- The expected outputs of 01.02 are checked against a reference written in
  Python: only gcd has a C version.
- `make` makes `build/`, so that `> build/gcd.s` works in a fresh project.
- mote.h also declares `equal` and `error_tok` (`error_at` was removed after the first read: nothing called it); `generate`
  reads `sym->reg` and takes no flag.
- mote2c checks a little more of a statement's form (`expected ':='`,
  `expected the end of the line`); expressions are still copied unchecked.
- Found: C makes a number that fits in 32 bits an int, so the translated
  `18 * 1000000007` is worked out in 32 bits and motec's program prints
  820130942 where every other way prints 18000000126. The translator is
  kept as designed (expressions copied as they are); the 01.04 test
  asserts the difference, and the random programs leave it out. It belongs
  in 01.04's lesson beside the gaps the plan already names.
- Module 01's cover (drawn for the outline: "One program, two ways to run
  it") gives the compiler's road as stack code (push 6, push 7, mul,
  write); chapter 1's compiler writes RISC-V for a register machine. The
  cover is copied as it is; redrawing it belongs to the art pass.

## Chapter 1's lessons and art as done (2026-11-25)

- Eleven lessons and the module page in `tracks/lang/lessons/01-introduction/`,
  each opening with what to read in the book. Thirty figures (seven stepped),
  the map in eleven copies, and module 01's cover redrawn (one program, every
  way to run it), from generators under `art/lang/` and
  `art/outlines/lang_art.py` that run the real programs and assert what they
  draw.
- On master: `./learn test lang` all 11 pass; `check-skeleton` and
  `check-timeline` ok; `./learn verify lang --fresh` ok for all 11;
  `./learn check` has nothing against lang (its one problem is the owner's
  copy of the book in the repo root).
- Lesson 01.05 is titled "The tools around a language: a prompt and a
  checker": the word check refuses "test runner" in a heading.
- A reader (an Opus agent given the pages and no conclusions) read the
  chapter on the site in both themes and at 390 px. What it found and what
  was changed is at the end of `tracks/lang/NOTES.md`; the rules that came
  out of it are at the end of `plans/lang-01-lessons.md`.
- The numbers the chapter turns on: gcd of 1071 and 462 runs 53 instructions
  written by hand, 142 compiled, 61 improved; the 8 between 61 and 53 are
  jumps to a jump.
- Not done, and not lang's alone: at 390 px every track's figures shrink to
  text of 5 or 6 px with no way to enlarge them; the module page's paragraph
  is not shown on the site; "Related" lines are not links. All three are in
  `harness/web/`, which another session has uncommitted work in.
- Not replayed by the verifier: the typed session at `mote0`'s prompt in
  01.05 (the same lines from a file are), and output that depends on the
  computer (the C compiler's assembly and messages, `nm`, timings).
- Not run on Linux.
- README.md does not name the track yet (another session has uncommitted
  edits there).

Next: chapter 2, on the owner's word. Its lesson list is settled only after
chapter 2 of the book is read as chapter 1 was.

## Chapter 2: the plan (2026-11-26; the owner: "continue")

Chapter 2 of the book (Programming Language Syntax, pages 43 to 105) was
read whole before this was written. It explains how tokens and grammar are
written down and how scanners and parsers are made from the descriptions,
each one twice: by hand and by a tool. The reader builds every construction
the chapter shows and runs it on their own language. Fifteen lessons.

### What the reader builds

Two tools, and each half of the front end again from what the tools make:

- `re`: regular expressions. It reads token definitions, lists the strings
  an expression generates, matches by trying every way, builds the NFA, the
  DFA and the smallest DFA, joins all of a language's tokens into one
  automaton, and writes that automaton as tables for a scanner.
- `gram`: grammars. It reads a grammar, finds every parse tree of a short
  string (so an ambiguous grammar shows two), reports left recursion and
  common prefixes, works out the FIRST, FOLLOW and PREDICT sets, builds the
  LL(1) table and the SLR(1) table with its states, and parses with either,
  printing the stack at every step.
- In `mote`: two more scanners (the automaton as nested cases, written by
  hand from what `re` prints; and a driver over the tables `re` writes) and
  three more parsers (recursive descent written by hand from an LL(1)
  grammar, as the book's Figure 2.17 is; a driver over the LL(1) table; a
  driver over the SLR(1) table).

What holds it together: every scanner prints the same tokens and every
parser gives the same tree, for every program and for thousands of random
ones, right and wrong.

### The language in chapter 2

Three additions, each asked for by a section of the chapter:

- A number may have single underscores between its digits (`1_000_000`). It
  makes the number's definition worth writing as an expression, and it is
  the book's "nontrivial prefix" case (Example 2.17) in the reader's own
  language: after `1`, an underscore continues the number only if a digit
  follows (`1_x` is the number 1 and the name `_x`).
- `elsif` (2.3.2, Example 2.32): with `end` on every `if`, a chain of them
  ends in a row of `end`s. `if c then ... elsif c then ... else ... end`.
  In the syntax tree it is an `if` inside an `else`, so nothing after
  analysis changes.
- Pragmas (2.2.5): a comment that starts `#!`. `#! register NAME` is a hint
  to the improver of 01.11 (give this variable a register before counting
  the others); `#! checks off` and `#! checks on` are directives to the code
  generator of 01.10 (leave out, or put back, the check before a division).
  The scanner collects them. A valid program prints the same with or
  without them.

Programs that use any of these live in `programs/02/`. The first
interpreter, the translator and chapter 1's parser stay at chapter 1's
language; `agree` shows `-` where a way does not take a program.

### Files

```
re.h re.c         02.01  definitions, expressions, gen, match
re_nfa.c          02.03  expression to NFA; an NFA run on a string
re_dfa.c          02.04  NFA to DFA; 02.05 the smallest; 02.06 all tokens in one
scandrv.c         02.07  the driver over a scanner's tables (re and mote share it)
gram.h gram.c     02.02  grammar files; every parse tree; derivations
gram_ll.c         02.10  left recursion, common prefixes; 02.11 the sets; 02.12 the table
lldrv.c           02.12  the driver over an LL(1) table (gram and mote share it)
gram_lr.c         02.13  items and states; 02.14 the SLR(1) table
lrdrv.c           02.14  the driver over an SLR(1) table (gram and mote share it)
syntax/           mote.tokens (02.01); mote.bnf, the natural grammar (02.02);
                  mote-ll.bnf, the LL(1) one (02.09); and small examples of
                  our own: digits.tokens, sum-ambiguous.bnf, sum.bnf,
                  dangling.bnf, sum-right.bnf, sum-left.bnf, dots.tokens
scan_cases.c      02.06  the automaton as nested cases
scan_table.c      02.07  the tables re wrote, and scandrv.c
descent.c         02.09  recursive descent from mote-ll.bnf; recovery at 02.15
flatten.c         02.09  a parser's own tree made into the tree of 01.07
parse_ll.c        02.12  the LL(1) table gram wrote, and lldrv.c
parse_lr.c        02.14  the SLR(1) table gram wrote, and lrdrv.c
```

The tables are written by the tools when `make` runs (`scan_table.h`,
`ll_table.h`, `lr_table.h`) and are not kept in the project: change
`syntax/mote.tokens` or a grammar and `make` builds the scanner and the
parsers again. `parse.c` (chapter 1's parser) is not changed: it stays as
the first parser, as `mote0` stays as the first interpreter.

### Notation

Token definitions (`*.tokens`): `name = expression` a line. In an
expression: a quoted string is those characters (`''` is the empty string);
a bare word is another definition; `[a-z0-9]` and `[^\n]` are sets of
characters; juxtaposition, `|`, `*` and parentheses as in the book. A line
`token NAME = expression` is a token the scanner returns, `skip NAME =
expression` one it drops (white space, comments), and `keyword a b c` the
names that are keywords instead.

Grammars (`*.bnf`): `lhs -> symbol symbol ...`, with `|` for another
right-hand side (on the same line or starting the next); `''` for an empty
right-hand side; `$$` the end of the input. A symbol with no production is
a terminal: a token by its text (`read`, `:=`) or its kind (`name`,
`number`). `%splice a b c` names nonterminals that exist only to make the
grammar fit a parser (`stmt_list`, `term_tail`, `add_op`): `flatten` hangs
their children on their parent, and hangs a left-recursive child's children
on its parent, which turns each parser's own tree into the tree `parse.c`
makes.

### Commands

```
./re gen    [-f FILE] EXPR [N]         the first N strings, shortest first
./re match  [-f FILE] EXPR STRING      by trying every way; --steps counts
./re nfa    [-f FILE] EXPR             02.03
./re run    [-f FILE] EXPR STRING      the set of states after each character
./re dfa    [-f FILE] EXPR             02.04: each state and the NFA states it stands for
./re min    [-f FILE] EXPR             02.05: the classes as they split, then the result
./re scanner FILE.tokens               02.06: one automaton, its final states named
./re tables  FILE.tokens               02.07: that automaton as C
./re tokens  FILE.tokens TEXT [--trace]   02.07: TEXT scanned by the driver

./gram show    GRAMMAR                 the productions, numbered
./gram trees   GRAMMAR 'a b c'         every parse tree, each with its derivation
./gram check   GRAMMAR                 02.10: left recursion, common prefixes
./gram sets    GRAMMAR                 02.11: EPS, FIRST, FOLLOW, PREDICT; conflicts
./gram lltable GRAMMAR [--c]           02.12
./gram ll      GRAMMAR 'a b c' [--trace]
./gram items   GRAMMAR                 02.13: the states, basis and closure, and where each goes
./gram slrtable GRAMMAR [--c]          02.14
./gram lr      GRAMMAR 'a b c' [--trace]

./mote [--scanner=adhoc|cases|table] [--parser=first|rd|ll|lr]
       [--tokens | --pragmas | --raw-tree | --parse-tree | --trace | --tree | --symbols | -S [-O]] FILE
```

`gram` splits its text argument at spaces: a word of digits is `number`, a
word the grammar does not name is `name`. `--scanner` defaults to `adhoc`
(chapter 1's `scan.c`, the kind the book says production compilers use);
`--parser` defaults to `first` until 02.09 and to `rd` from then on.
`--raw-tree` prints the parser's own tree; `--parse-tree` the tree after
`flatten`, the same from every parser; `--trace` the stack, the input and
the step, for `ll` and `lr`.

### Chapter 2, lesson by lesson

Pages are the 4th edition's; "makes real" names the book's example or
figure by number. Every program text and example is ours.

| Lesson | Read first | Built | Makes real |
|---|---|---|---|
| 02.01 Tokens as regular expressions | the chapter's opening, 2.1 and 2.1.1 (43 to 48) | `re`: definitions, `gen`, `match`; `syntax/mote.tokens`; digit separators | Example 2.3: definitions that generate strings |
| 02.02 A grammar, and the trees it derives | 2.1.2 and 2.1.3 (48 to 53) | `gram`: `show`, `trees`; `syntax/mote.bnf` and the two small sum grammars | Examples 2.4 to 2.8, Figures 2.1 to 2.4: a derivation, two trees for one string, precedence and associativity in the grammar |
| 02.03 From an expression to an automaton that guesses | 2.2 up to and including "From a Regular Expression to an NFA" (54 to 59) | `re nfa`, `re run` | Examples 2.9 to 2.13, Figures 2.5 to 2.8; chapter 1's `scan.c` read as the ad hoc scanner of Example 2.10 |
| 02.04 From guessing to knowing: the DFA | "From an NFA to a DFA" (60) | `re dfa` | Example 2.14, Figure 2.9 |
| 02.05 The smallest automaton | "Minimizing the DFA" (60 to 62) | `re min` | Example 2.15, Figure 2.10 |
| 02.06 The scanner as an automaton in code | 2.2.2 up to and including sidebar 2.4 (61 to 63) | `re scanner`; `scan_cases.c`; `--scanner=cases` | Example 2.16, Figure 2.6, sidebar 2.4 |
| 02.07 The scanner as a table and a driver | the rest of 2.2.2 and 2.2.3 (63 to 67) | `re tables`, `re tokens`; `scandrv.c`, `scan_table.c`; `--scanner=table` | Examples 2.17 and 2.19, Figures 2.11 and 2.12 |
| 02.08 Lexical errors, and notes to the compiler | 2.2.4 and 2.2.5 (65 to 68) | every lexical error reported, not the first only; pragmas | the four steps of 2.2.4; both kinds of pragma of 2.2.5 |
| 02.09 Recursive descent, from an LL(1) grammar | 2.3 and 2.3.1 (69 to 79) | `syntax/mote-ll.bnf`; `descent.c`, `flatten.c`; `--parser=rd`, `--raw-tree` | Examples 2.22 to 2.24, Figures 2.16 to 2.18 |
| 02.10 Writing a grammar a parser can use | 2.3.2 (79 to 82) | `gram check`; `syntax/dangling.bnf`; `elsif` | Examples 2.25 to 2.32: left recursion, common prefixes, the dangling else as two trees, end markers, `elsif` |
| 02.11 Predict sets: which token chooses which production | 2.3.3 whole (82 to 89); this lesson builds its second half | `gram sets` | Example 2.35, Figures 2.22 to 2.24 |
| 02.12 A top-down parser as a table and a stack | 2.3.3 again, to Example 2.34 (82 to 85) | `gram lltable`, `gram ll`; `lldrv.c`, `parse_ll.c`; `--parser=ll`, `--trace` | Examples 2.33 and 2.34, Figures 2.19 to 2.21, sidebar 2.7 |
| 02.13 Bottom-up: shift, reduce, and the states of a parse | 2.3.4 up to "Bottom-Up Parsing Tables" (89 to 94) | `gram items`; the two sum grammars parsed both ways by hand in the text | Examples 2.20, 2.21, 2.36 to 2.38, Figures 2.14, 2.15, 2.25 |
| 02.14 A bottom-up parser as a table and a stack | the rest of 2.3.4 (95 to 101) | `gram slrtable`, `gram lr`; `lrdrv.c`, `parse_lr.c`; `--parser=lr` | Examples 2.39 to 2.41, Figures 2.26 to 2.30 |
| 02.15 Syntax errors: carrying on after a mistake | 2.3.5, then 2.4 and the summary, 2.5 (102 to 105) | recovery in `descent.c`: report, skip to a token that can start or follow a statement, go on | Example 2.42; panic mode and phrase-level recovery |

Notes on the table:

- 02.11 and 02.12 are one section of the book read once and built in two
  lessons, the sets before the table that is made from them.
- The SLR(1) tables here are the plain kind (shift, reduce, goto, accept).
  The book folds a state with one finished item into the shift that reaches
  it ("shift and then reduce") and speaks of pushing the left-hand side back
  on the input; 02.14 says how the two descriptions meet.
- 2.3.5's detail and 2.4 are on the book's companion site; 02.15 says so.
- The table-driven parsers stop at the first syntax error; recovery is
  built for the hand-written one only, as the book's account is.

### How the work is split

Two Opus agents at once, then a third:

- Scanning (02.01, 02.03 to 02.08): `re`, the token files, the two
  scanners, lexical errors, pragmas (with their effect in `improve.c` and
  `gen.c`), the digit separator in `scan.c`, and `elsif` as a keyword in
  the two new scanners and `mote.tokens`.
- Parsing (02.02, 02.09 to 02.15): `gram`, the grammar files, `descent.c`,
  `flatten.c`, the two table parsers, `elsif` (keyword in `scan.c`, the
  grammars, `descent.c`, `analyze.c`), recovery.
- Then one agent merges the two, adds the front ends to `agree` (every
  scanner with every parser, one tree), puts the chapter's programs in
  `programs/02/`, and runs every check for modules 01 and 02 together.

Module 01's lessons must still replay unchanged: every change to a file of
chapter 1 is behind `@from 02.NN`.

### Tests

A test per lesson. Beyond them: random expressions and strings (the three
matchers of `re` agree; the smallest DFA accepts what the DFA accepts);
random text (the three scanners print the same tokens and the same errors);
random programs, valid and broken (the four parsers give the same tree, or
refuse at the same token); the grammar files checked by the tool itself
(`mote-ll.bnf` has disjoint predict sets, `mote.bnf` no SLR(1) conflict).
