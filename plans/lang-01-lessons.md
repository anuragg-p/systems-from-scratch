# lang track, chapter 1: design of the lessons and figures

This is the design the lesson writers and the art builders work from. It is
decided. Build it, and report where it did not survive contact with the code or
the page. Lessons and figures are made in parallel by different agents, so the
figure file names and captions below are a contract: a lesson uses exactly
these names; an art builder draws exactly these files.

## Sources of truth

- The code: `tracks/lang/` on master. The project at a lesson:
  `./learn files lang --at NN.LL DIR`, or `./learn run lang --at NN.LL`, which
  leaves it in `build/at/lang/NN.LL/`.
- `tracks/lang/NOTES.md`: regions by lesson, exact transcripts, the numbers a
  lesson quotes, departures from the plan, what was read in the RISC-V manual.
  A lesson states about another system only what NOTES.md records or what the
  writer has read in that system's source or documentation and adds to NOTES.md.
- `plans/lang.md`: the plan, and "Chapter 1 as built".
- The format: `templates/lesson.md`, `templates/module.md`, README.md ("How it
  is organized", "Verifying a lesson"). Models to read before writing:
  `tracks/cc/lessons/02-expressions/02.03-*.md` and
  `tracks/cc/lessons/00-the-smallest-compiler/00.01-*.md` (a first lesson).

## Rules for everyone

- ASCII only, in every file.
- Do not open any file in the main checkout's root named "Programming Language
  Pragmatics..." or any PDF there. What a reader finds in each section of the
  book is written below, in our words; a lesson says no more about the book
  than that, and copies nothing from it or from any other text.
- Work in your own git worktree. First run `git merge --ff-only master`.
  Commit as you go, each message ending with
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Do not push. Do
  not touch the main checkout, other worktrees, the harness, README.md, or
  tracks other than lang. Never stash, reset or clean.
- Do not change the track's code or tests. If a lesson needs the code changed,
  list the exact line in your report instead.
- For a person whose pronouns are not stated (the reader, an author), use
  they/them.
- Module folder: `tracks/lang/lessons/01-introduction/`. Lesson files:
  `NN.LL-<slug>.md`, the slug the title in lower case with hyphens. Figures in
  `figures/` beside them.

## Lesson titles

```
01.01 A machine, and a program written in its language
01.02 Your language, and the programs you want it to run
01.03 An interpreter: the program run from its text
01.04 A translator: to C, and from there to the machine
01.05 The tools around a language: a prompt and a test runner
01.06 The phases of a compiler, and the first: a scanner
01.07 The parser: tokens into a tree
01.08 Semantic analysis: the syntax tree and the symbol table
01.09 Walking the tree: an interpreter built on the front end
01.10 Target code: loads, stores, tests and branches
01.11 Code improvement: variables kept in registers
```

## How a lesson is written

- This track is read with the book open. Every lesson's opening paragraph ends
  with one line in this form, given for each lesson below:
  `**Read first:** <what>, in Programming Language Pragmatics, 4th edition.`
  The lesson then makes that reading real: it says which of the book's
  examples or figures the reader is about to reproduce for their own language
  ("Example 1.21 lists the tokens of a C program; this lesson prints the
  tokens of yours"), by number only. The book's examples are in C and x86
  assembly; ours are in the reader's language and RISC-V. Say so once, in
  01.01.
- Follow `templates/lesson.md` section by section: the opening, Where this fits
  (with the map), The idea (the main figure, and a `### name` lead-in for each
  piece of code the lesson adds, from the region titles and function names in
  NOTES.md), Run it, How it works, Decide the boundary (where given), Break
  it, Go deeper, Related.
- The language is called Mote in the lessons; 01.02 tells the reader to give it
  a name of their own and says the commands here keep `mote`.
- Voice: plain, short sentences, for someone who programs in C and has never
  looked inside a language. A term in bold the first time. No hook questions,
  no "simply", no telling the reader to write the code. Never mention stubs,
  tests, workspaces or check tools. Never use what a later lesson brings as if
  the reader had it; say "lesson NN.LL builds this".
- "Run it": `./learn run lang --at NN.LL`, then inside `build/at/lang/NN.LL/`
  the project's own programs. Run every command yourself in the project at
  that lesson and paste what you got. Every code block carries a
  `<!-- verify: ... -->` comment as the template shows; the lesson is done
  only when `./learn verify lang NN.LL` passes. Output that depends on the
  computer (the C compiler's assembly, its error text, timings) is shown from
  one real run with the computer named, marked `verify: skip` with the reason,
  and the text says the reader's will differ. Counts (`--count`) are exact and
  are replayed.
- "Break it": the one given below, verified with a patch block; if the code as
  built makes it impossible or makes the program run forever, choose the
  nearest that ends and say so in your report.
- "Go deeper": first the book, as `[Programming Language
  Pragmatics](https://www.cs.rochester.edu/~scott/pragmatics/), 4th edition, by
  Michael L. Scott (Morgan Kaufmann, 2016), section N.N: <what to read again
  now that the code exists>.` The book is not free online: do not say or imply
  it is, and link no copy of its text. Then the other references given for the
  lesson. Fetch every outside page before you link it and link it only if it
  says what the lesson claims. Links into this course: `[the cc track's lesson
  02.03](/t/cc/02.03)`.
- Length: 150 to 300 lines a lesson.
- Labels: `with code`, plus `decision boundary` where the lesson has one.
- Module page (`README.md` in the module folder): the template's one
  paragraph: what chapter 1 of the book covers, what the reader has built by
  its end (five ways to run one program, and the check that they agree), and
  that section 1.7, the chapter's summary, is the page to read last.

## The map (figures/NN.LL-map.svg, one per lesson)

One map for chapter 1, the same in every lesson: the system as it stands at the
end of the chapter. The lesson's piece in the accent colour, earlier pieces
solid, later ones dashed and muted. 640 wide.

- Top, centred: `the program's text` with `programs/` under it (01.02's
  piece), and to its left a small `gcd.c` (also 01.02).
- Three roads run down from the text.
  - Left road: box **first interpreter** (01.03), with a cell inside it,
    "prompt" (01.05). Out of it: `output`.
  - Middle road: box **translator to C** (01.04), then a hollow box "the
    computer's C compiler, assembler and linker" (not ours: drawn with a
    dashed outline in every lesson, lit with the translator in 01.04), with
    a small box `rt` feeding the linker from the side (01.02) and `gcd.c`
    entering the compiler from the left. Out of it: `a program for your
    computer`, then `output`.
  - Right road, the widest, inside one frame labelled `mote`: **scanner**
    (01.06) -> **parser** (01.07) -> **semantic analysis** (01.08), with
    "symbol table" as a small cell under semantic analysis. Then a fork:
    down-left **tree walk** (01.09) to `output`; down-right **improver**
    (01.11) -> **code generator** (01.10) -> `assembly`. The frame and the
    arrows between the phases are 01.06's piece too (the driver).
- Bottom right, under `assembly`: box **the machine** (01.01), with a small
  `gcd.s, by hand` feeding it from the right (01.01). Out of it: `output`.
- Across the bottom, one thin wide box joining the four outputs: **agree:
  every way, the same answer** (01.05).

Nothing on the map names a function. 01.05 lights the prompt cell and the
agree bar; 01.10 lights the code generator; 01.01 the machine and `gcd.s`.

## What the book says, section by section (ours, for the writers)

- Opening (pages 5 to 7). The first computers were programmed in machine
  language, the bits that drive the processor. One program, the greatest
  common divisor by Euclid's algorithm, is shown as bytes (Example 1.1) and
  as assembly (Example 1.2), which names each operation and maps one to one
  onto the bytes; an assembler does the translating. Each kind of machine has
  its own. Wanting programs that outlive one machine led to high-level
  languages and to compilers.
- 1.1 (7 to 10). Why there are so many languages (the field keeps finding
  better ways; languages made for one kind of problem; taste) and what makes
  one succeed: expressive power, ease for a beginner, ease of implementing
  it, a standard, open source, excellent compilers, and money and inertia.
  The programmer's view and the implementor's often pull apart.
- 1.2 (11 to 14). Families: declarative (functional, dataflow, logic) and
  imperative (von Neumann, object-oriented, scripting). GCD is written three
  ways, in C, OCaml and Prolog (Figure 1.2), to show the family changes how
  one thinks.
- 1.3 (14 to 16). Why study languages: to choose one, to learn the next
  faster, to understand features and what they cost, to use debuggers and
  linkers well, and because every large program holds small languages of its
  own (file formats, configuration, extension languages).
- 1.4 (17 to 24). A compiler translates and goes away; the target program
  runs later by itself. An interpreter stays and is in charge while the
  program runs; it reads statements more or less one at a time. Interpreting
  gives flexibility and better error messages; compiling gives speed, because
  a decision made before the run is not made again during it (the example: a
  variable's place known in advance against looked up in a table on every
  use). Most systems mix the two. Then a list of arrangements: an interpreter
  with a first pass that strips comments and groups characters (and early
  Basics that had none, so comments slowed a program down), Example 1.10;
  library routines and the linker, Example 1.11; compilers that write
  assembly, 1.12; the C preprocessor, 1.13; translating to another high-level
  language, with the first C++ compiler as the case, and the remark that a
  compiler understands its input while a preprocessor does not and may write
  text that fails further on, 1.14; bootstrapping, 1.15; compiling languages
  that are usually interpreted, 1.16; compiling at the last moment, 1.17;
  microcode, 1.18.
- 1.5 (24 to 25). The tools around a compiler: assemblers, debuggers,
  preprocessors, linkers, editors, pretty printers, style checkers,
  configuration management, tools to inspect files, profilers; separate tools
  against an integrated environment.
- 1.6 (26 to 28). A compiler works in phases, each handing the next a more
  useful form: scanner, parser, semantic analysis and intermediate code,
  improvement, target code, improvement again (Figure 1.3); the first three
  are the front end. An interpreter shares the front end and then walks the
  tree (Figure 1.4).
- 1.6.1 (28 to 32). The GCD program in C with two input and output routines,
  `getint` and `putint` (Example 1.20). The scanner groups characters into
  tokens, drops white space and comments, and notes each token's line and
  column (Example 1.21 lists the tokens). The parser arranges tokens into a
  parse tree by the rules of a context-free grammar (Example 1.22 shows
  rules for C's while loop); the whole tree for GCD is Figure 1.5, large
  because every rule used is a node, most of them there only for lists and
  for precedence.
- 1.6.2 (32 to 34). Semantic analysis finds meaning: which uses of a name
  are the same thing, and whether they are consistent. It keeps a symbol
  table. It enforces rules the grammar cannot, such as a name being declared
  before use: the static semantics. Rules that can only be checked while the
  program runs are dynamic: a variable used before it has a value, a
  subscript out of bounds, overflow; a compiler may generate the check, or
  the language may leave it unchecked. The parse tree is reduced to a syntax
  tree whose nodes point into the symbol table (Figure 1.6). Example 1.25
  walks that tree as an interpreter would.
- 1.6.3 (34 to 36). The code generator gives each variable a place and walks
  the tree writing loads, stores, arithmetic, tests and branches. Figure 1.7
  is naive x86 code for GCD from a simple teaching compiler.
- 1.6.4 (36 to 37). Code improvement makes the program compute the same
  thing with less. Applied to Figure 1.7 it gives the short code of Example
  1.2: the loads and stores are gone because the variables can stay in
  registers through the loop, which holds only while nothing else can change
  them.

## The lessons

For each: the Read first line, what the lesson must get across, Run it, How it
works, the boundary, Break it, Go deeper, and its figures (file name, caption
word for word, what it shows; "stepped" where it is).

### 01.01 A machine, and a program written in its language

Read first: chapter 1 from its first page to the start of section 1.1 (pages 5
to 7).

Makes real: Example 1.2, for a machine of the reader's own. (Example 1.1, the
bytes, is lesson 01.02's, on their real computer, and chapter 5's for this
machine.)

This is the track's first lesson, so Where this fits is the tour: one program,
the greatest common divisor of 1071 and 462, and the five ways chapter 1 runs
it, each ending in 21, in the book's order: by hand in assembly on a machine
(this lesson), from its text by an interpreter (01.03), translated to C and
compiled (01.04), through a compiler's front end to a tree that is walked
(01.06 to 01.09), and through its back end to assembly for the machine again
(01.10, 01.11). Say how the track is read: the section first, then the lesson.

The idea: a machine is a few registers, a list of instructions, and a rule for
which runs next. Assembly is one instruction a line. Walk `programs/gcd.s`:
the larger number loses the smaller until they are equal. What writing it by
hand asks of you: which register holds what, where every jump goes. And it
runs on this machine only. The machine's assembly is real RISC-V text; this
machine runs the text itself, and chapter 5 gives it bits.

Run it: the sample (21); then in the project `printf '12 18\n' | ./machine
programs/gcd.s` (6); `--count`; `--trace` on `6 4`, whole.

How it works: labels need a pass of their own (a jump may name a line further
down); every instruction has an address, `call` leaves the way back in `ra`;
the library routines are part of the machine, and why (on a real computer
they are code linked in, lesson 01.04); the invariant: `zero` is always 0,
and the line that keeps it.

Decide the boundary: text now, bits later. This machine cannot treat a program
as data; a real one stores both in the same memory. What that buys, and why
chapter 5 is the place to pay for it.

Break it: make the machine resolve labels in the same pass as instructions (or
the nearest change the code allows): `gcd.s` fails at its first jump forward
with an undefined label, though the label is in the file.

Go deeper: the book's opening again. The RISC-V manual and the assembler
manual's table of pseudo-instructions (github.com/riscv/riscv-isa-manual,
github.com/riscv-non-isa/riscv-asm-manual). `[the cc track's lesson
00.02](/t/cc/00.02)`: the same assembly through a real assembler and linker.

Figures:
- `01.01-five-ways.svg` - "One program, the greatest common divisor of 1071
  and 462, and the five ways chapter 1 runs it: every road ends in 21." Five
  rows, each a chain of small boxes ending in `21`, with its lesson numbers:
  by hand (gcd.s, the machine); the first interpreter; translator, C
  compiler, your computer; scanner, parser, analysis, tree walk; scanner,
  parser, analysis, improver, code generator, the machine. This lesson's row
  in accent.
- `01.01-machine.svg` - "The machine: a few registers, a program, and the rule
  for which instruction runs next." Left, the registers the program uses
  (`a0`, `s1`, `s2`, `ra`) and `zero`; middle, `gcd.s` as numbered
  instructions with an arrow at the current one; right, the library routines
  between the machine and the input and output.
- `01.01-gcd-run.svg` (stepped) - "gcd.s on 6 and 4, an instruction a step:
  the registers after each, until 2 is printed." Frames from `--trace` of
  the real run: the listing with the current line marked, `s1`, `s2`, `a0`,
  and the output line when it appears.

### 01.02 Your language, and the programs you want it to run

Read first: sections 1.1, 1.2 and 1.3 (pages 7 to 16).

Makes real: the C third of Figure 1.2 as a program the reader runs, Examples
1.1 and 1.2 on their own computer, and section 1.1's list applied to a
language of their own.

The idea, in four steps. (1) The same program one level up: `programs/gcd.c`.
What 01.01 made you decide, the C compiler decides. (2) See what it decided
on your computer: its assembly and its bytes; the book's first two examples
are this for an x86. (3) The language of your own: its name (the track says
Mote), the whole of it in one short program, `programs/gcd.mote`, and a small
table setting it against section 1.1's list: ease of implementing it (a page
of rules; this chapter builds it five times), ease for a beginner (words, not
marks: `while ... do ... end`), a standard (the programs with their expected
output: every way of running them must print exactly that), expressive power
(little, on purpose; each chapter adds), open source (it is yours). (4) Where
it starts among section 1.2's families: a von Neumann language, statements
that change variables. One sentence each, in words and without code, on how
the same problem looks as a definition (chapter 11) and as rules to search
(chapter 12), which this track builds too.

Lead-ins: `getint`, `putint`, and the C program.

Run it: the sample (21); `cat programs/gcd.mote`; the three `.in` and `.out`;
`cc -S` on `programs/gcd.c` and a disassembly of `./gcd`, a few lines of each
(this computer's; skip, with the computer named); nothing runs `gcd.mote`
yet, and say which lessons will.

How it works: two routines every implementation shares, so their outputs can
be compared byte for byte; `long` is 64 bits and that is the language's
integer; the expected outputs are the standard, and lesson 01.05 builds the
check that holds every implementation to them.

Decide the boundary: a name comes into being when the text first gives it a
value; C and most of the book's languages make you declare it. What each
buys: less to write against a mistake caught earlier. Chapters 3 and 4 return
to it.

Break it: in `rt.c` make `putint` print no line end. `./gcd < programs/gcd.in
| cmp - programs/gcd.out` now reports a difference: one byte is enough to
fail the standard.

Go deeper: the book's 1.1 (reread the list with the table beside it) and 1.2.

Figures:
- `01.02-c-and-assembly.svg` - "gcd.c beside the assembly of lesson 01.01:
  each line of C stands for the instructions on its right, and the choices in
  grey are the ones the compiler now makes for you." Two columns joined by
  lines: `i = getint()` with `call getint` / `mv s1, a0`; `while (i != j)`
  with `beq s1, s2, done` and the `j loop`s; `i = i - j` with `sub s1, s1,
  s2`; `putint(i)` with `mv a0, s1` / `call putint`. Register names and
  labels in grey.
- `01.02-growth.svg` - "What your language can say after chapter 1, and what
  each later chapter adds." A ladder of chapters, bottom to top: 1 numbers,
  variables, loops (accent); 3 functions and scopes; 6 control flow; 7 types;
  8 records, arrays; 9 exceptions, coroutines; 10 objects; 11 functional
  programming; 12 logic programming; 13 threads; 14 scripting. The family
  names of section 1.2 as small labels on the rungs where they arrive.
- `01.02-standard.svg` - "A program, its input, and the output every way of
  running it must print." Three cards (`gcd.mote`, `gcd.in`, `gcd.out`, real
  contents), and under them five dashed slots for the ways to come, each
  with its lesson number, all pointing at the same `gcd.out`.

### 01.03 An interpreter: the program run from its text

Read first: section 1.4 up to and including Example 1.10 (pages 17 to 19).

Makes real: Example 1.8 (pure interpretation), and Example 1.10's early Basic
with no first pass.

The idea: `mote0` holds the program's text, the number of the line it is on,
and a table of names. To run a line it reads the line's characters. Nothing
is prepared and nothing is remembered about the text: a loop's lines are read
again on every pass, and a name is found by comparing strings each time. This
is the interpreter that "stays": it is what runs, the program is its data.

Run it: the sample; `--count` for each of the three programs; add a comment
line inside gcd's loop (in a copy) and count again: the count rises, the
book's remark about comments in early Basic made exact; a program that uses a
name with no value, and one that divides by zero: each stops with the file
and the line.

How it works: the search for a name on every use (the cost section 1.4 names);
blocks found by reading and counting (the invariant: each `while` or `if`
adds one, each `end` takes one away, the match is where the count returns);
why a statement must have a line to itself (there is no scanner; the line is
the unit).

Decide the boundary: run the text, or translate it first. Running it costs
every pass of every loop; it buys an interpreter with nothing to build before
the first line runs and errors that name the line being run. The question:
how many times is each line run?

Break it: make the forward search for a block's `end` stop counting nested
blocks. `gcd.mote` (an `if` inside the `while`) goes wrong; show what it does.

Go deeper: the book's 1.4, first part. Crafting Interpreters, "A Map of the
Territory" (craftinginterpreters.com/a-map-of-the-territory.html), on
single-pass and tree-walk interpreters.

Figures:
- `01.03-stays.svg` - "An interpreter stays: the program's text and its input
  go in together, and the interpreter is what runs." Two small pictures with
  real names. Above: `gcd.mote` and `1071 462` into `mote0`, `21` out. Below,
  muted, "lesson 01.04": `gcd.mote` into a translator, a program out; later,
  `1071 462` into that program, `21` out.
- `01.03-reread.svg` (stepped) - "mote0 on gcd.mote with 6 and 4: the line it
  reads at each step and the table of names. The loop's lines are read again
  on every pass." Frames from the real order of lines read (the generator
  simulates the order and asserts its total against `--count`): the program
  with the current line marked and a tally beside each line of how often it
  has been read; the table `i`, `j`.

### 01.04 A translator: to C, and from there to the machine

Read first: the rest of section 1.4, from Example 1.11 (pages 19 to 24).

Makes real: Example 1.7 (a translator that goes away), 1.11 (the library and
the linker), 1.12 (assembly on the way), 1.13 (the preprocessor), 1.14
(another high-level language as the target).

The idea: translate each line into a line of C and let the computer's C
compiler do the rest. Then the stages one at a time, each leaving a file to
look at: the C (`./mote2c`), the preprocessor's output (`cc -E`: `rt.h`
pasted in), the assembly (`cc -S`), the object file, incomplete (`nm` shows
`getint` and `putint` undefined), the link with `rt.o`, the program. Then
`./motec`, which does them all. Then the two ways set against each other: a
long `sum` under `mote0` and as a compiled program (one real timing, the
computer named), and a mistake under each: `mote0` names the line; `mote2c`
passes it through and the C compiler complains about a C file. By the book's
own test (it understands its input, or it does not) `mote2c` is a
preprocessor; the compiler in this road is the C compiler. Lessons 01.06 to
01.10 build one that understands. Examples 1.15 to 1.18 are for reading: one
sentence each on where this track meets them (bootstrapping: this track
writes the language in C, as the book suggests a first compiler be written;
bytecode and compiling at the last moment: chapter 16).

Run it: as above. Machine-dependent output (assembly, `nm`, timings, the C
compiler's message) from one real run, marked skip; what `mote2c` writes and
what the program prints are replayed.

How it works: two passes, because C wants a name declared before it is used;
expressions go through untouched because the operators are C's (a decision
of 01.02), and what that leaves unchecked; `-fwrapv`, because the language
says arithmetic wraps and C says it is undefined; the checks `mote0` made
that the translated program does not.

Decide the boundary: borrow a compiler or write one. Translating to C gets a
back end that took decades to build; the price is that errors arrive in C's
terms and the language can say only what C can. Lesson 01.10 pays the other
price.

Break it: make the first pass miss the names that `read` gives a value.
`./motec programs/gcd.mote` fails in the C compiler, on a file the reader
never wrote; show the status and the first line of the generated C that is
wrong.

Go deeper: the book's 1.4, second part, with the five files beside it.
`[the cc track's lesson 00.02](/t/cc/00.02)` for what the assembler and the
linker do.

Figures:
- `01.04-stages.svg` - "From gcd.mote to a program your computer runs: the
  stages, and the file each one leaves." A chain: `gcd.mote`, **mote2c**,
  `build/gcd.c`, preprocessor, compiler, `assembly`, assembler, `gcd.o`,
  linker (with `rt.o: getint, putint` joining), `build/gcd`. Ours in accent;
  the computer's own tools hollow.
- `01.04-line-for-line.svg` - "The translator works a line at a time: each
  line of gcd.mote and the line of C it becomes." Two columns from the real
  output, a thin line joining each pair; the declarations at the top of the
  C marked "from the first pass".
- `01.04-when.svg` - "What is decided when. The interpreter decides
  everything while the program runs, on every pass of the loop; the
  translator and the C compiler decide it once, before." Two lanes, "before
  the run" and "during the run, each time round", with the same four
  decisions placed in each: where the loop ends, where `i` is, what `-`
  means here, the subtraction itself. Under `mote0` all four are during;
  compiled, only the subtraction is.

### 01.05 The tools around a language: a prompt and a test runner

Read first: section 1.5 (pages 24 to 25).

The idea: two tools now. The prompt: an interpreter that stays can also wait
for the next line; a block is held until its `end`; a mistake is reported and
the prompt comes back. And `agree`: the standard of 01.02, enforced: every
program, every way there is. A short table of section 1.5's tools and where
this track builds each (make, since 01.01; the assembler and linker, chapter
15; the debugger and profiler, chapter 16).

Run it: a real session at the prompt (use what the verifier offers for typing
into a program; if it cannot replay one, replay the same lines from a file
and show the interactive session marked skip); `./agree`.

How it works: the prompt is the same interpreter with a buffer and a depth
count; how an error returns to the prompt instead of ending the program;
`agree` compares bytes, and the invariant it keeps: a way is added in the
lesson that builds it, and from then on every program must pass it.

Break it: the same change as 01.02's (`putint` in `rt.c` without its line
end): `./agree` shows `motec DIFFERS` on every row and `mote0 ok`.

Go deeper: the book's 1.5.

Figures:
- `01.05-prompt.svg` (stepped) - "A session at the prompt: what is typed,
  what is held until the block ends, and the names after each line." Frames
  from a real session: `x := 6`; `while x > 4 do` (held); `x := x - 1`
  (held); `end` (the block runs); `write x` (4).
- `01.05-agree.svg` - "agree: the programs down the side, the ways across,
  and one expected output for each row." A grid, three rows, five columns:
  `mote0` and `motec` solid with `ok`; the three to come dashed, with their
  lesson numbers.

### 01.06 The phases of a compiler, and the first: a scanner

Read first: section 1.6 as far as the start of 1.6.1, then 1.6.1 as far as
Example 1.21 (pages 26 to 28).

Makes real: Figures 1.3 and 1.4, as the order of calls in `main.c`; Example
1.21, for the reader's program.

The idea: a new program, `mote`, begins, built as the book's figures are
drawn: phases in a row, each handing the next a form that is easier to work
on. The driver is that row. The first phase reads the characters once and
hands on tokens, each with its kind, its text, and its line and column.
`mote0` did this work on every line every time; the scanner does it once.

Run it: `--tokens` on `gcd.mote`, whole; characters against tokens (`wc -c`,
and the count of lines `--tokens` prints); a program on one line (`read i
read j write i + j`) scans, and `mote0` on the same file refuses it: a
scanner is why line ends stop mattering; a character the language does not
have, with its line and column.

How it works: the longest match for the two-character operators (and
`[the cc track's lesson 01.02](/t/cc/01.02)`, which is this rule at length);
a keyword is read as a name and then looked up; the line and column ride on
every token so that every later phase can say where; in the driver, each
option stops after its phase.

Decide the boundary: a scanner of its own, or a parser that reads characters.
The book calls the second possible, awkward and slow; `mote0` was the
second.

Break it: try the one-character operators before the two-character ones.
`gcd.mote` no longer scans; show the message and where it points.

Go deeper: the book's 1.6 and Figures 1.3 and 1.4 against `main.c`. Crafting
Interpreters, "Scanning" (craftinginterpreters.com/scanning.html).

Figures:
- `01.06-phases.svg` - "The phases in the order the driver calls them, and
  what each hands to the next. Solid: what exists after this lesson." A row:
  characters, **scanner**, tokens, parser, parse tree, semantic analysis,
  syntax tree (symbol table beside it), then two ends: tree walk, and
  improver, code generator, assembly. Lesson numbers under each phase.
- `01.06-scan.svg` (stepped) - "The scanner on `while i != j do`: where it
  is in the characters, and each token as it is finished." Frames from the
  real tokens: a pointer over the characters, the tokens made so far below
  with their line and column.
- `01.06-chars-to-tokens.svg` - "gcd.mote as the scanner leaves it: the
  comment and the spaces are gone, and what is left is a list of tokens."
  The program's text with each token boxed and the comment and white space
  greyed, and the two real counts (characters, tokens).

### 01.07 The parser: tokens into a tree

Read first: the rest of section 1.6.1, from Example 1.22 (pages 28 to 32).

Makes real: Example 1.22 (rules of a grammar), Example 1.23 and Figure 1.5
(the whole parse tree), for the reader's language and program.

The idea: the language's grammar, all of it (it is in `plans/lang.md` and in
the comment at the top of `parse.c`). A function for each rule; each makes a
node named after the rule and hangs under it what it took. The tree is the
proof that the text follows the rules. One statement, `i := i - j`: five
tokens under a `stmt`, an `expr`, two `term`s and two `factor`s; the nodes
in between are there only so that `*` binds tighter than `-`. The book says
the same of Figure 1.5: the size is the grammar's, not the program's.

Run it: `--parse-tree` on a one-line program, whole; on `gcd.mote`, its first
lines and its count of nodes against 11 lines of text; a missing `do`, with
its line and column; the leaves of the tree, left to right, are exactly the
tokens (show it with the project's own commands).

How it works: one token ahead is always enough, because every statement
starts with a different word; `{ }` in a rule is a loop in its function, `[
]` an `if`; the tree keeps everything, even `:=` and `end`, and the invariant
that makes it a parse tree: its leaves are the tokens, in order.

Decide the boundary: a parser written by hand from the grammar, or one made
by a tool from the grammar (chapter 2 builds both). By hand: easy to read and
to give good messages; by tool: the grammar is the only thing to maintain.

Break it: swap which of `expr` and `term` handles `+ -` and which `* /`. `1
+ 2 * 3` still parses, and the tree now groups the addition first; show the
two trees.

Go deeper: the book's 1.6.1 and Figure 1.5. `[the cc track's lesson
02.01](/t/cc/02.01)`. Crafting Interpreters, "Parsing Expressions"
(craftinginterpreters.com/parsing-expressions.html).

Figures:
- `01.07-rule-and-function.svg` - "A rule of the grammar and the function
  that is that rule: each name on the right of the rule is a call, each
  quoted word a token to take." The `while` alternative of `stmt` above, the
  shape of its code below, joined piece to piece.
- `01.07-tree.svg` - "The parse tree of `i := i - j`: five tokens at the
  bottom, and above them the nodes that only say which rule was used." The
  real tree; leaves in one colour, rule nodes in another.
- `01.07-descent.svg` (stepped) - "The parser on `write i - j`: the functions
  that are running at each token, and the tree as it grows." Frames: the
  tokens with a marker, the stack of rule functions, the tree so far.

### 01.08 Semantic analysis: the syntax tree and the symbol table

Read first: section 1.6.2 as far as Example 1.24 (pages 32 to 34).

Makes real: Figure 1.6 (a syntax tree and its symbol table), and the section's
split between static and dynamic rules, with one static rule checked.

The idea: the parse tree is walked once and three things happen. What was
only there for the parser is dropped (`i := i - j` goes from its parse tree
to four nodes). Every name is entered in the symbol table the first time the
text gives it a value, and every use becomes a pointer to that entry: "the
same `i`" is now a fact, not a comparison of strings. And the one rule the
grammar cannot state is checked: a name may be used only after the text has
given it a value.

Run it: `--tree` and `--symbols` on `gcd.mote`, whole; the two trees' sizes;
a program that uses a name too early, and `x := x + 1` as a first statement:
each refused with its line and column; a program the rule accepts although it
can go wrong when run (the value given inside an `if` that is not taken):
accepted here, and lesson 01.09 catches it.

How it works: what is dropped and why nothing is lost (the shape of the tree
says what `:=`, `do` and `end` said); a flat list of terms folded into
left-nested nodes, so `a - b - c` means what it should; the symbol table's
order and the invariant (after analysis every use of a name points at an
entry); the rule reads the text, not the future: that is what static means.

Decide the boundary: names made by their first assignment, or declared. What
the static rule can promise in each case, and what it leaves to the running
program.

Break it: enter the target of `:=` before checking its right side. `x := x +
1` as a first statement is now accepted; show `--tree` taking it.

Go deeper: the book's 1.6.2 and Figure 1.6 beside `--tree` and `--symbols`.
`[the cc track's lesson 02.02](/t/cc/02.02)`.

Figures:
- `01.08-two-trees.svg` - "The parse tree of `i := i - j` and the syntax
  tree made from it: what the parser needed is gone, and each name points
  into the symbol table." Left, the parse tree of 01.07 small and muted;
  right, four nodes; arrows from the name nodes to rows 1 and 2 of a table.
- `01.08-gcd-tree.svg` - "The syntax tree of gcd.mote and its symbol table:
  every `i` is entry 1, every `j` entry 2." The whole tree as `--tree` gives
  it, drawn as a tree, with the table beside it.
- `01.08-static.svg` - "The static rule reads the text from the top: a name
  may be used only below the place that first gives it a value." Three small
  programs: one accepted; one refused, the use marked; one accepted although
  the value is given inside an `if`, marked "left for the running program,
  lesson 01.09".

### 01.09 Walking the tree: an interpreter built on the front end

Read first: Example 1.25 in section 1.6.2 (page 33), with Figure 1.4 (page
27) beside it.

Makes real: Figure 1.4's last box and Example 1.25: the tree of 01.08 walked
in program order.

The idea: two functions that call each other, one for statements and one for
expressions, each a switch on the kind of node. A variable's value lives in
its symbol table entry, so using it is following a pointer. No text is read
while the program runs. This is the mixed arrangement of section 1.4: a
front end that translates to an intermediate form, and a small machine (the
walk) that runs it.

Run it: the sample (21); `./agree`, three ways now; the program of 01.08 that
gives a value inside an `if` not taken: stopped while running, with its
place; division by zero; the one-line program of 01.06 runs; a long `sum`
under `mote0` and under `mote` (one real timing, marked skip).

How it works: values in the symbol table (set against 01.03's search by
name); the walk has the grammar's shape, a function's recursion for every
level of nesting; the dynamic rule costs one flag and one test on every use,
and the line that keeps the invariant (no entry is read before it is
written); what is still decided on every pass: which kind of node this is,
which lesson 01.10 decides once.

Decide the boundary: walk the tree, or translate it again into instructions
for a simpler machine (chapter 16). Crafting Interpreters builds both for
one language and measures the gap.

Break it: evaluate a loop's condition once instead of on every pass.
`gcd.mote` prints the wrong number and `./agree` shows `mote DIFFERS` beside
`mote0 ok`.

Go deeper: the book's Example 1.25. Crafting Interpreters, "Evaluating
Expressions" and "Statements and State"
(craftinginterpreters.com/evaluating-expressions.html,
craftinginterpreters.com/statements-and-state.html).

Figures:
- `01.09-walk.svg` (stepped) - "The walker on gcd.mote with 6 and 4: the node
  it is at, and the values in the symbol table." Frames: the tree of
  `01.08-gcd-tree` with the current node marked, the table with `i` and `j`,
  the output when it comes. The generator walks the tree `--tree` prints and
  asserts its answer against the real run.
- `01.09-per-pass.svg` - "One pass of gcd's loop under each interpreter: the
  first reads lines and searches for names; the walker follows pointers."
  Two columns with real counts for one pass: `mote0` (lines read, searches of
  the table); `mote` (nodes visited, searches: none).

### 01.10 Target code: loads, stores, tests and branches

Read first: section 1.6.3 (pages 34 to 36).

Makes real: Example 1.26 and Figure 1.7 (naive code for GCD), for the reader's
machine.

The idea: the compiler's back end. First the machine gets a memory, and each
variable a place in it. Then code is written for each node of the tree: a
use of a variable is a load, an assignment a store, an operator one
instruction on registers used as a stack, a loop a test and two jumps.
Nothing is remembered from one statement to the next, which is what makes it
simple and always right. `i := i - j` becomes four instructions.

Run it: the sample (21 and the count of instructions); `./mote -S
programs/gcd.mote`, whole; that count against `programs/gcd.s` by hand; a
division by zero in a compiled program (the check the compiler added, and
its code in the listing); the program of 01.09 that uses a name with no
value: compiled, it prints a number and says nothing, and why; `./agree`,
four ways.

How it works: slot k at `8*(k-1)(sp)`, and why `sp` moves by a multiple of
16; a condition becomes one branch on its opposite, past the code it guards;
registers as a stack and its limit of seven (and `[the cc track's lesson
02.03](/t/cc/02.03)`, where this scheme is the subject); the generated check
before a division: code the programmer did not write, and the check the
compiler leaves out.

Decide the boundary: every variable in memory, or in registers. Memory is
simple and never wrong; it costs a load on every use. gcc without
optimisation makes the same choice (the cc lesson above shows its output).
Lesson 01.11 makes the other.

Break it: branch on the condition instead of its opposite. `gcd.mote`
compiled prints the wrong number and `./agree` shows `machine DIFFERS`.

Go deeper: the book's 1.6.3 and Figure 1.7 beside the listing. The cc track's
lessons 02.03 and `[02.06](/t/cc/02.06)` (running out of registers).

Figures:
- `01.10-slots.svg` - "Where the variables of gcd.mote live: a slot each in
  the machine's memory, found from sp." A strip of memory with `sp`, the two
  slots and their offsets, and the symbol table rows they come from.
- `01.10-statement.svg` (stepped) - "`i := i - j` as the code generator
  writes it, an instruction a step: two loads, a subtraction, a store."
  Frames: the statement's tree with the node being visited, the instruction
  written, and `t0`, `t1` and the two slots after it runs (values from a real
  run with 6 and 4).
- `01.10-while.svg` - "A while loop as a test and two jumps: the condition
  becomes one branch on its opposite, past the loop." The source of gcd's
  loop beside its real listing, with arrows for the branch out and the jump
  back.

### 01.11 Code improvement: variables kept in registers

Read first: section 1.6.4, then the chapter's summary, section 1.7 (pages 36
to 38).

Makes real: Example 1.27: the naive code improved until it looks like the
code written by hand at the start of the chapter.

The idea: most of what 01.10's code does is move values between memory and
registers. If a variable can stay in a register for the whole program, every
load and store of it goes. Here it always can: only the program's own
assignments change a variable, and the library routines leave these
registers alone. The book's warning is the limit: it stops being true when
something else can reach the variable. The improver decides which variables
(the most used, eleven at most); the generator then uses a variable's
register as the operand and writes results straight into it. `i := i - j` is
one instruction.

Run it: the sample; the two listings for `gcd.mote`; the three counts on
`1071 462`: by hand, compiled, improved; the improved listing against
`programs/gcd.s`, each difference explained; a program with more variables
than registers (which stay in memory, by their counts); `./agree`, five ways.

How it works: why it is safe here and what later chapters do to that; which
variables, and why eleven; the improver changes no node of the tree, it marks
symbols: a decision that does not depend on the machine (may it live in a
register) apart from one that does (which); the invariant: the improved
program prints what the unimproved one prints, and `agree` holds it.

Decide the boundary: count uses in the text, as here, or weigh each use by
how often it runs (a use inside a loop counts for more) and let two variables
that are never alive together share a register. Chapter 17 builds that.

Break it: make the improver give two variables the same register. `./agree`
shows `machine -O DIFFERS` beside `machine ok`: the unimproved program is
what catches an improver's mistake.

Go deeper: the book's 1.6.4, and then 1.7, the summary of the chapter this
module has built.

Figures:
- `01.11-before-after.svg` - "gcd.mote compiled twice: on the left every use
  is a load and every assignment a store; on the right `i` and `j` live in
  `s1` and `s2`." The two real listings side by side, the loads and stores
  marked on the left, with the instruction counts for `1071 462` under each.
- `01.11-who-gets-a-register.svg` - "Which variables get a register: counted
  by use, the most used first, eleven at most." The four variables of
  `primes.mote` with their real counts as bars and the register each gets,
  and a note for the case of more than eleven.
- `01.11-three-counts.svg` - "Instructions run for the same answer, 21: by
  hand, compiled, and improved." Three bars with the real numbers.
