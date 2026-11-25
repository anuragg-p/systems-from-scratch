# Notes for the lesson writers

Step 1 of the track: chapter 1's code, the eleven lessons of module 01 as `plans/lang.md` sets
them out. Everything here was run on the reference code or on the project as the site shows it at
a lesson (`./learn files lang --at NN.LL DIR`), on an Apple M4 Pro Mac (macOS 26.6.2, Darwin
25.6, Apple clang 21.0.0, Python 3.12.7, GNU as 2.46.0 as riscv64-elf-as from Homebrew).
Function names are given instead of line numbers. Nothing was run on Linux in this step.

## What this step is built on

No code is taken from anywhere. The machine's instructions and their meaning are the RISC-V
manuals' (see "Reads" at the end); the scanner and the parser have chibicc's shape (a list of
tokens, a function for each rule) and nothing else of it; `tracks/cc` was read for the track
contract and its markers only. The language, the programs and every line of C are the course's.
`UPSTREAM` in `track.py` names both, `"derived": False`.

## Where the code is, lesson by lesson

```
tracks/lang/
  Makefile        62  every program; make makes build/ too (FILES_FROM 01.01; @from per lesson)
  machine.c      470  the machine: tables, two passes, getint and the routines, --trace, the run
                      loop; memory, addi, ld, sd and divzero at 01.10
  programs/gcd.s  20  by hand, the brief's text (FILES_FROM 01.01); gcd.in 1071 462
  rt.h, rt.c   6, 52  getint and putint for C programs (rt.h FILES_FROM 01.02)
  programs/           gcd.c, and gcd, sum, primes as .mote .in .out (FILES_FROM 01.02)
  mote0.c        481  the first interpreter; the prompt at 01.05
  mote2c.c       209  the translator to C
  motec           25  sh: mote2c, cc -O1 -fwrapv -c, link with rt.o, all into build/
  agree           80  sh: every program, every way; the ways of 01.09 to 01.11 by @from
  mote.h          89  Token, Parse, Symbol, Node, the phases' prototypes (FILES_FROM 01.06)
  main.c         228  the driver and the printers (from 01.06)
  scan.c         132  the scanner, and error_at, error_tok, equal (01.06)
  parse.c        172  the parser (01.07)
  analyze.c      150  the syntax tree, the symbol table, the static rule (01.08)
  interp.c       103  the tree-walking interpreter (01.09)
  gen.c          189  the code generator (01.10; the register paths at 01.11)
  improve.c       46  the improver (01.11)
  art.svg, icon.svg   the outline's track art, copied (the site's card and icon)
  lessons/01-introduction/cover.svg, icon.svg
                      module 01's art, written there by art/outlines/lang_art.py
  track.py            settings, fixtures, run hooks, the timeline; NOTES.md; tests/ (11 tests,
                      proggen.py, fuzz.py)
```

Those are the lines of each file as the track holds it; the site shows a file without its
markers and its regions' instruction comments (at 01.11: machine.c 404, mote0.c 405, mote2c.c 186,
main.c 179, gen.c 151, parse.c 156). See the departures for the ceilings.

The regions (`./learn solution lang NN.LL` prints them):

| lesson | file: function (region title) |
|---|---|
| 01.01 | machine.c: reg, find_labels, read_instructions, getint, routine, trace, run |
| 01.02 | rt.c: getint, putint |
| 01.03 | mote0.c: find, set, factor, term, expr, cond, input, statement, skip, run, split |
| 01.04 | mote2c.c: find_names, translate, main (the C program); motec (translate, compile, link) |
| 01.05 | mote0.c: prompt; agree (every program, every way) |
| 01.06 | scan.c: number, name, op, scan; main.c: options, print_tokens, main (the phases, in order) |
| 01.07 | parse.c: factor, term, expr, cond, stmt, parse; main.c: print_parse |
| 01.08 | analyze.c: find, enter, expression, statement; main.c: print_expr, print_tree, print_symbols |
| 01.09 | interp.c: input, eval, test, interpret |
| 01.10 | machine.c: check, load, store; gen.c: operand, check_divisor, into, branch_unless, stmt, generate |
| 01.11 | improve.c: count, improve |

What a lesson adds outside its regions, through `@from` (the site shows it under "Also added in
this lesson"): 01.02 the Makefile's rt.o and gcd; 01.03 the Makefile's mote0; 01.04 mote2c in the
Makefile; 01.05 mote0's `setjmp.h`, `again`, read_line, the `line N:` form of error() and its
longjmp, the rest of a line dropped after a number read at the prompt, the call of prompt() in
main, the `[FILE]` usage and header line; 01.06 the Makefile's mote and MOTE; 01.07 Parse and
parse() in mote.h, `--parse-tree`, the parse call in main, print_parse; 01.08 Symbol, Node,
analyze, symbols in mote.h, `--tree` and `--symbols`, print_var, the analyze call; 01.09 `value`
and `has_value`, interpret(), the usage in brackets (an option is no longer needed), the interpret
call; 01.10 machine.c's ADDI, LD, SD, MEMORY, memory[], sp at the top, divzero, the `mem[...]`
part of --trace; gen.c in the Makefile, `-S`, agree's machine way; 01.11 `uses` and `reg`,
improve(), `-O`, gen.c's register paths (operand, into's variable case, store, the assignment,
the frame) and the last sentence of its header, agree's fifth way.

A cut region stops its program with `lang: NN.LL: <title> not written yet`, status 3, from
todo() (`@internal` in each C program: machine.c, rt.c, mote0.c, mote2c.c, main.c; declared in
mote.h for the phases); in motec and agree the stub is the same line from the shell. Region
titles hold no double quote (the C stub puts the title in a string). In the project as the site
shows it at a lesson there is no stub: what a later lesson brings is an ordinary error
(`machine: mem.s:3: unknown instruction 'ld'` before 01.10; `usage: mote (--tokens |
--parse-tree) FILE` for `./mote FILE` before 01.09; `usage: mote0 [--count] FILE` for `./mote0`
with no file before 01.05; `-O` is a usage error before 01.11).

## What the programs print

machine (`machine.c`):

- `./machine [--count] [--trace] FILE.s`; anything else is `usage: machine [--count] [--trace]
  FILE.s`, status 2. A file that will not open: `machine: cannot open FILE`, status 1.
- Errors in the program or while it runs: `machine: FILE:LINE: message`, status 1, no count:
  `unknown instruction 'xyz'`, `unknown register 'q1'`, `expected a register`, `expected ','`
  (or `'('`, `')'`), `expected a number`, `number too large: 999...`, `expected a label`, `no
  label 'nowhere'`, `label 'main' defined twice`, `unexpected text after the instruction: 'a0'`,
  `ran off the end of the program`, `no instruction at address 6` (a ret to where there is
  none), `address 1048576 is outside the memory` (01.10). With no `main:`: `machine: FILE: no
  label main to start at` (no line).
- The routines: `machine: getint: no more input` and `machine: getint: not a number` (both
  status 1; the plan names only the first, the second is ours), `line N: division by zero`
  (divzero, 01.10, status 1). These are the program's own ends, so the count is printed after
  them and --trace shows the instruction that ended it.
- `--count`: `N instructions` on stderr when the program ends (exit, a ret from main, divzero, a
  getint error). Every instruction counts one, `call` and a large `li` included.
- `--trace`, the format chosen here: for each instruction run, on stderr, after it has run: the
  line number right-aligned in 4 columns, two spaces, the instruction's text as written (its
  comment and the space around it dropped); if it changed anything, the text padded to 24
  columns, then for each register whose value changed, in register order, two spaces and `name =
  value` (decimal), and for an sd (01.10) `mem[ADDRESS] = value` (the address in decimal). A
  `call` changes `ra` (the next instruction's address) and, for getint, `a0`. stdout is flushed
  before each line, so the program's output sits among the trace lines in the order it happened.
- Instruction i (from 0, in the file's order) is at address 4 * i. At the start `ra` holds 4 *
  (the number of instructions), the address just past the last one; a `ret` to it ends the
  program with status `a0`, as a return from main into the C library would. A main that calls
  anything has lost that `ra`, so gcd.s and compiled code end with `call exit`. The exit status is
  `a0`'s low 8 bits (`li a0, 300; call exit` exits 44). sp starts at 1048576 (01.10; 0 before).
- getint skips white space (C's isspace), takes an optional `-` or `+`, then one digit or more,
  added up in an unsigned long (so `9223372036854775808` reads as the most negative number and
  `18446744073709551617` as 1), and leaves the first character after the digits to be read next.
  rt.c's getint and the `read` of mote0.c and interp.c read the same way, so every way agrees on
  any input.

mote0 (`mote0.c`): `./mote0 [--count] [FILE]` (FILE is needed before 01.05). Errors `FILE:LINE:
message`, status 1; at the prompt `line N: message`, N counting every line typed in the session
(a number taken by `read` at the prompt is not a line of the program). `--count`: `N lines read`
on stderr at a normal end. `mote0: cannot open FILE`, status 1; a wrong command line, status 2.

mote2c (`mote2c.c`): `./mote2c FILE.mote` writes C on stdout; errors `FILE:LINE: message`,
status 1: `expected a statement`, `expected ':='`, `expected a name`, `expected 'do'`, `expected
'then'`, `expected the end of the line` (after read's name, after else and end). A blank line
stays blank; a line that is only a comment is dropped; a comment after a statement is dropped.

mote (`main.c` and the phases): `./mote [OPTION] FILE`. Errors `FILE:LINE:COL: message`, status
1 (COL from 1, a tab one column); usage, status 2: `usage: mote (--tokens) FILE` at 01.06, `(... |
--parse-tree)` at 01.07, `(... | --tree | --symbols)` at 01.08, the same in brackets from 01.09
(an option is no longer needed), `| -S` at 01.10, `| -S [-O]` at 01.11. `-O` without `-S`, two
options, two files, an unknown option: the usage.

- `--tokens`: `LINE:COL KIND TEXT`, KIND `name`, `number`, `keyword` or `op`; then `LINE:COL
  eof`. The end of the file is on the last line after its last character: a line end that ends
  the file ends that line and starts no other (`x` and `x` with a line end both have eof at 1:2;
  `x` and two line ends at 2:1; an empty file at 1:1). `\r` is a space everywhere.
- `--parse-tree`: a node a line, two spaces deeper a level; a rule by its name, a token as `KIND
  TEXT`. The end-of-file token is not in it (program = { stmt } takes no token).
- `--tree`: `read i#1`, `write (+ i#1 1)`, `:= i#1 (- i#1 j#2)`, `if (> i#1 j#2)`, `while (!= i#1
  j#2)`, `else` at its if's indentation; a number as its value, a negation as `(- x#1)`.
- `--symbols`: `INDEX NAME LINE:COL`, the place of the name token where the text first gives it
  a value (in a read or an assignment).
- `-S`: an instruction is written `    %-4s %s` (four spaces, its name padded to 4, a space, the
  operands); a load or a store has `# name`, the instruction padded to 26 columns as in gcd.s;
  the labels `main:` and `.L1:` at column 0.

agree: a row a program, the first column the longest name and two spaces, then `WAY ok` or `WAY
DIFFERS` with two spaces between; the last line `N programs, M ways each: all agree`, or `K
differ` (`1 differs`; `1 program`), status 1. What each way printed is in `build/NAME.WAY.out`
and `.err`. `./agree DIR` takes the programs of DIR (the tests use it).

## The lessons, one by one

Each transcript below was run in a fresh copy of the project as the site shows it at that lesson
(`./learn files lang --at NN.LL DIR`, then `make -s`), stdout and stderr together. What is in
parentheses after a line is a note, not output.

### 01.01 A machine, and a program written in its language

- Two passes (find_labels, read_instructions) because a branch may name a label further down: the
  first pass knows each label's address by counting the instructions before it. A label may share
  a line with an instruction (`main:  li a0, 7`). A label is letters, digits, `_` and `.` (so the
  compiler's `.L1` is one).
- The table of instructions says in a short string what each takes after its name (`rrr`, `rrl`,
  `rm`, ...); one loop reads every instruction's operands from it. Registers go into r[] in the
  order written, so `sd a0, 8(sp)` has the value's register in r[0] and the base in r[1].
- `call` sets ra even for a routine of the machine, as the real call would; so a main that calls
  getint can no longer end with ret, and gcd.s ends with `call exit`.
- --trace prints a line after its instruction has run, so a putint's output comes before its own
  trace line (in the tail below, `21` before line 18's `call putint`).
- The lesson's look at the reader's real computer (`cc -S`, a disassembler) has nothing in the
  project and was not run here.

```
$ ./machine programs/gcd.s < programs/gcd.in
21
$ ./machine --count programs/gcd.s < programs/gcd.in
21
53 instructions
$ ./machine --trace programs/gcd.s < programs/gcd.in 2>&1 | tail -6
   9  beq  s1, s2, done
  17  mv   a0, s1               a0 = 21
21
  18  call putint               ra = 48
  19  li   a0, 0                a0 = 0
  20  call exit                 ra = 56
$ ./machine --trace programs/gcd.s < programs/gcd.in          (its first 8 lines, on stderr)
   4  call getint               ra = 4  a0 = 1071
   5  mv   s1, a0               s1 = 1071
   6  call getint               ra = 12  a0 = 462
   7  mv   s2, a0               s2 = 462
   9  beq  s1, s2, done
  10  ble  s1, s2, smaller
  11  sub  s1, s1, s2           s1 = 609
  12  j    loop
$ ./machine mem.s          (main: / li a0, 7 / ld a0, 0(sp) / ret)
machine: mem.s:3: unknown instruction 'ld'                  (status 1; from 01.10 it runs)
$ ./machine programs/gcd.s < /dev/null
machine: getint: no more input                              (status 1)
```

### 01.02 Your language, and the programs you want it to run

- rt.c's getint behaves as the machine's; see "What the programs print".
- The .out files were written by hand and are checked by the 01.02 test against tests/proggen.py's
  reference (Python), not against C versions: only gcd has one. primes.mote has no remainder
  operator, so it writes `p - p / d * d`, and its comment says why.

```
$ make gcd
cc -std=c11 -O2 -Wall -Wextra -c -o rt.o rt.c
cc -std=c11 -O2 -Wall -Wextra -I. -o gcd programs/gcd.c rt.o
$ ./gcd < programs/gcd.in
21
$ echo 12 | ./gcd
getint: no more input                                       (status 1)
```

### 01.03 An interpreter: the program run from its text

- Nothing is prepared: run() looks at a line's first word each time it reaches the line. open[]
  holds what is needed to come back: for a while its line, for an if -1. A false condition calls
  skip(), which reads forward counting whiles and ifs against ends (only each line's first word is
  looked at); the end of a while goes back to the while's line, whose condition is worked out
  again from its text.
- An expression is worked out by expr, term and factor moving one `const char *p` over the
  characters; a name is found by comparing its characters with each entry of a list (find).
- A line only read past is never checked: mote0 runs a program with `x := 1 +` in a branch it
  never takes. mote finds it at once (01.07).
- --count counts every line looked at: comment lines, lines read only to skip them, and the while
  line each time it is gone back to. sum on 100: 4 lines before the loop, the while line 101
  times, the body's 2 lines and the end 100 times each, 3 lines read past at the end, the write:
  409. A comment line in the loop: 510 (one a pass, and one more when the loop is read past).

```
$ ./mote0 programs/gcd.mote < programs/gcd.in
21
$ ./mote0 --count programs/gcd.mote < programs/gcd.in
21
88 lines read
$ ./mote0 --count programs/sum.mote < programs/sum.in
5050
409 lines read
$ ./mote0 --count programs/primes.mote < programs/primes.in
2
3
5
7
11
13
17
19
23
29
844 lines read
$ ./mote0 late.mote                    (write 1 / x := y + 1)
1
late.mote:2: y has no value yet                             (status 1)
$ ./mote0 oops.mote                    (x := 1 + / write x)
oops.mote:1: expected a number, a name or '('               (status 1)
$ ./mote0
usage: mote0 [--count] FILE                                 (status 2; a prompt from 01.05)
```

### 01.04 A translator: to C, and from there to the machine

- mote2c checks only the form of a statement, by its first word (and that a while line ends in
  `do`, an if line in `then`); everything else is copied.
- motec puts its files in build/ of the directory it is run from, and finds mote2c, rt.h and rt.o
  beside itself; `|| exit` after each step ends it with the failing step's status.
- C's int (found by the fuzzer; the design is kept): an expression made only of numbers that each
  fit in 32 bits is worked out by C in int, so `write 18 * 1000000007` prints 820130942 from
  motec's program (clang warns "overflow in expression") and 18000000126 every other way. The
  translator passes the expression through untouched; the language's numbers are 64-bit and C's
  literals are not. A good example for the lesson's question of what makes a compiler.
- The other places C differs, none met by a program in programs/: division by zero (on this
  arm64 Mac the C program prints a result; x86 traps), the most negative number divided by -1
  (undefined in C even with -fwrapv), a number written with a leading 0 (C reads it as octal), two
  minus signs written together (C's `--`), a name that is a C keyword or getint, putint or main.
  The generator in tests/proggen.py avoids each.

```
$ ./mote2c programs/gcd.mote
#include "rt.h"

int main(void) {
    long i = 0;
    long j = 0;
    i = getint();
    j = getint();
    while (i != j) {
        if (i > j) {
            i = i - j;
        } else {
            j = j - i;
        }
    }
    putint(i);
    return 0;
}
$ ./motec programs/gcd.mote && build/gcd < programs/gcd.in
21
$ ./motec oops.mote
build/oops.c:5:12: error: expected expression
    5 |     x = 1 +;
      |            ^
1 error generated.                                          (status 1)
$ ./motec wide.mote && build/wide      (write 18 * 1000000007 / x := 18 / write x * 1000000007)
820130942
18000000126
$ ./mote0 wide.mote
18000000126
18000000126
```

### 01.05 The tools around a language: a prompt and a test runner

- The prompt holds a block's lines until its end (it counts whiles and ifs against ends by their
  first word), then runs them with run(), the function a file's lines go through. An error
  longjmps back to the prompt; the names keep their values.
- At the prompt a `read` takes its number from the next line and drops the rest of that line, so
  that the number's line end is not taken for an empty line of the program.
- The end of the input prints a line end, so the shell's prompt starts on a line of its own.
- agree compares stdout only, byte for byte (cmp).

```
$ ./mote0 < session.in    (x := 6 / write x * 7 / while x > 3 do / write x / x := x - 1 / end / write y / write x)
> > 42
> . . . 6
5
4
> line 7: y has no value yet
> 3
>
$ ./agree
gcd     mote0 ok  motec ok
primes  mote0 ok  motec ok
sum     mote0 ok  motec ok
3 programs, 2 ways each: all agree
```

(The session's last line is `> ` with its space, then the line end.)

### 01.06 The phases of a compiler, and the first: a scanner

- main() is the picture: scan, then each later phase under its own `@from`, each printing option
  returning after its phase. Before 01.09, `./mote FILE` with no option is a usage error.
- The scanner takes the longest operator (`<=` before `<`), and a whole word before looking it up
  among the keywords (`done` is a name, not `do`). The error functions are in scan.c, which knows
  the file's name; error_tok is what every later phase calls.

```
$ ./mote --tokens programs/gcd.mote
2:1 keyword read
2:6 name i
3:1 keyword read
3:6 name j
4:1 keyword while
4:7 name i
4:9 op !=
4:12 name j
4:14 keyword do
5:5 keyword if
5:8 name i
5:10 op >
5:12 name j
5:14 keyword then
6:9 name i
6:11 op :=
6:14 name i
6:16 op -
6:18 name j
7:5 keyword else
8:9 name j
8:11 op :=
8:14 name j
8:16 op -
8:18 name i
9:5 keyword end
10:1 keyword end
11:1 keyword write
11:7 name i
11:8 eof
$ ./mote programs/gcd.mote
usage: mote (--tokens) FILE                                 (status 2)
$ ./mote --tokens at.mote              (x := 1 @ 2)
at.mote:1:8: unexpected character '@'                       (status 1)
```

### 01.07 The parser: tokens into a tree

- add() walks to the end of a node's children to hang the next one there (the plan's Parse has
  no pointer to the last child).
- 64 nodes for gcd.mote's 11 lines: 29 leaves (every token but the end of the file) and 35 rule
  nodes. The leaves read in order are the tokens; the 01.07 test checks it.
- A syntax error is found before anything runs; mote0 finds a mistake only on reaching its line.

```
$ ./mote --parse-tree programs/gcd.mote | wc -l
      64
$ ./mote --parse-tree oops.mote
oops.mote:2:1: expected a number, a name or '('             (status 1)
$ ./mote programs/gcd.mote
usage: mote (--tokens | --parse-tree) FILE                  (status 2)
$ ./mote --parse-tree programs/gcd.mote
program
  stmt
    keyword read
    name i
  stmt
    keyword read
    name j
  stmt
    keyword while
    cond
      expr
        term
          factor
            name i
      op !=
      expr
        term
          factor
            name j
    keyword do
    stmt
      keyword if
      cond
        expr
          term
            factor
              name i
        op >
        expr
          term
            factor
              name j
      keyword then
      stmt
        name i
        op :=
        expr
          term
            factor
              name i
          op -
          term
            factor
              name j
      keyword else
      stmt
        name j
        op :=
        expr
          term
            factor
              name j
          op -
          term
            factor
              name i
      keyword end
    keyword end
  stmt
    keyword write
    expr
      term
        factor
          name i
```

### 01.08 Semantic analysis: the syntax tree and the symbol table

- expression() turns an expr or a term node (operand, operator, operand, ...) into left-nested
  binary nodes; parentheses leave nothing behind. statement() analyzes `x := e`'s e before it
  enters x.
- The static rule is about the text, not the run: maybe.mote, which gives x a value in a branch
  never taken and then writes x, passes it.

```
$ ./mote --tree programs/gcd.mote
read i#1
read j#2
while (!= i#1 j#2)
  if (> i#1 j#2)
    := i#1 (- i#1 j#2)
  else
    := j#2 (- j#2 i#1)
write i#1
$ ./mote --symbols programs/gcd.mote
1 i 2:6
2 j 3:6
$ ./mote --tree late.mote
late.mote:2:6: y is used before anything gives it a value   (status 1)
$ ./mote --tree maybe.mote             (if 1 > 2 then / x := 1 / end / write x)
if (> 1 2)
  := x#1 1
write x#1
```

### 01.09 Walking the tree: an interpreter built on the front end

- A variable's value lives in its Symbol (value, has_value); nothing is looked up by name.
- The dynamic rule catches what the static one let through. Compiled code (01.10) does not check
  it, and prints 0 for maybe.mote: the machine's memory starts as zeroes.

```
$ ./mote programs/gcd.mote < programs/gcd.in
21
$ ./mote maybe.mote
maybe.mote:4:7: x has no value yet                          (status 1)
$ echo 5 | ./mote zero.mote            (read a / b := 0 / write a / b)
zero.mote:3:9: division by zero                             (status 1)
$ ./mote0 maybe.mote
maybe.mote:4: x has no value yet                            (status 1)
```

### 01.10 Target code: loads, stores, tests and branches

- operand() returns the register a value is in; into() computes into a given register. Without
  -O they are the plan's stack: a node's value in T[depth], the left operand at the same depth,
  the right one a register deeper. The depth check is in operand(), where a t register is taken:
  the eighth value waiting is `expression too deep`, at its token. What was written before the
  error is on stdout already (`mote -S deep.mote > f.s` leaves part of f.s, status 1).
- Labels are numbered in the order they are made: a while takes two (top, end) before its body,
  an if one or two (else, end), a division's check one.
- The listing for gcd.mote is GCD_S in tests/0110: 26 instructions, `addi sp, sp, -16`, i at
  0(sp) and j at 8(sp).

```
$ ./mote -S programs/gcd.mote > build/gcd.s && ./machine --count build/gcd.s < programs/gcd.in
21
142 instructions
$ ./mote -S zero.mote > build/zero.s && echo 5 | ./machine build/zero.s
line 3: division by zero                                    (status 1)
$ ./mote -S maybe.mote > build/maybe.s && ./machine build/maybe.s
0
$ ./agree
gcd     mote0 ok  motec ok  mote ok  machine ok
primes  mote0 ok  motec ok  mote ok  machine ok
sum     mote0 ok  motec ok  mote ok  machine ok
3 programs, 4 ways each: all agree
```

### 01.11 Code improvement: variables kept in registers

- improve() counts every appearance (a target counts as an operand does), then hands out s1 to
  s11 by count, a tie to the lower index; s0 is left alone (by convention the frame pointer).
- Only loads and stores carry a `# name` comment (the plan's rule), so the improved listing has
  none.
- With -O a variable in a register needs no t register, so the depth check can pass with -O where
  it fails without.
- The improved gcd against gcd.s by hand: the same 14 instructions in the listing, the same
  registers (i in s1, j in s2), the same two branches (beq out, ble to the other arm). The
  difference: where the hand version's `i = i - j` arm jumps straight back to `loop`, the compiled
  one jumps to the if's end label, where the while's `j .L1` waits: a jump to a jump, once on
  each of the 8 passes where i > j. 61 instructions against 53; the naive code runs 142.

```
$ ./mote -S -O programs/gcd.mote
main:
    call getint
    mv   s1, a0
    call getint
    mv   s2, a0
.L1:
    beq  s1, s2, .L2
    ble  s1, s2, .L3
    sub  s1, s1, s2
    j    .L4
.L3:
    sub  s2, s2, s1
.L4:
    j    .L1
.L2:
    mv   a0, s1
    call putint
    li   a0, 0
    call exit
$ ./mote -S -O programs/gcd.mote > build/gcd.s && ./machine --count build/gcd.s < programs/gcd.in
21
61 instructions
$ ./mote -S programs/gcd.mote > build/gcd.s && ./machine --count build/gcd.s < programs/gcd.in
21
142 instructions
$ ./machine --count programs/gcd.s < programs/gcd.in
21
53 instructions
$ ./agree
gcd     mote0 ok  motec ok  mote ok  machine ok  machine -O ok
primes  mote0 ok  motec ok  mote ok  machine ok  machine -O ok
sum     mote0 ok  motec ok  mote ok  machine ok  machine -O ok
3 programs, 5 ways each: all agree
```

## The numbers the lessons quote

All exact, and replayed by the tests or the timeline, except the timings.

| what | number |
|---|---|
| instructions in programs/gcd.s (the brief's text) | 14 (the plan says 15; see the departures) |
| gcd.s on 1071 462, `--count` | 53 instructions |
| naive (`mote -S`) gcd on 1071 462 | 142 instructions (26 in the listing) |
| improved (`mote -S -O`) gcd on 1071 462 | 61 instructions (14 in the listing) |
| passes of gcd's loop on 1071 462 | 11: 8 with i > j, 3 with j > i |
| `mote0 --count`: gcd on 1071 462 / sum on 100 / primes on 30 | 88 / 409 / 844 lines read |
| sum with a comment line in its loop, on 100 | 510 lines read |
| gcd.mote's tokens | 29, then eof |
| gcd.mote's parse tree | 64 nodes for 11 lines: 29 token leaves, 35 rule nodes |

## Timing (one computer; not replayed)

sum.mote on n = 3000000 (it prints 4500001500000), wall clock, best of three runs, on the Apple
M4 Pro Mac above, the programs built by the Makefile (-O2) and motec's program by cc -O1:

| way | time | count |
|---|---|---|
| mote0 | 0.259 s | 12000009 lines read |
| mote (the tree-walker) | 0.031 s | |
| motec's program | 0.002 s | (clang at -O1 may have turned the loop into arithmetic) |
| machine, mote -S | 0.136 s | 36000015 instructions |
| machine, mote -S -O | 0.055 s | 15000009 instructions |

mote0 is only about 8 times slower than mote here, because sum's lines are short and it has three
names; the lesson can say the gap grows with long lines and many names. The motec figure is the C
compiler's work, not the translator's.

## Departures from the plan and the brief, with reasons

1. **The ceilings.** As the track holds them, machine.c is 470 lines (404 as the site shows it)
   against 280, mote0.c 481 (405) against 280, mote2c.c 209 (186) against 130, main.c 228 (179)
   against 160; the rest are under theirs. No function is long (the longest, machine.c's run, is
   59 lines with its switch); the size is in what the brief asks of each program: every error
   with its message, --trace and --count, the routines, the prompt, the usage forms that change
   by lesson. Getting to the ceilings would mean dropping some of that or writing much denser C.
2. **gcd.s has 14 instructions, not 15** (the plan, "The machine at chapter 1"): the text the
   brief gives has 14. The improved listing has 14 too.
3. **getint has a second error**, `not a number`, in the machine, rt.c, mote0 and mote (`read:
   not a number`): the plan names only the end of the input. Without it, a letter in the input
   would have no defined meaning.
4. **The expected outputs are checked against the Python reference**, not against C versions
   (the plan's 01.02 says "what the C versions print"; only gcd has one, as the brief says).
5. **`make` makes build/** (an `@mkdir -p build` in `all`), so that the 01.10 sample `./mote -S
   programs/gcd.mote > build/gcd.s` works in a fresh project; motec and agree make it too.
6. **mote.h has three more names**: equal(), error_at() and error_tok() (in scan.c); generate()
   takes no -O flag, as the plan has it: it reads sym->reg, which only improve() sets.
7. **mote2c checks a little more than the first word**: `expected ':='` for a name not followed
   by it, `expected the end of the line` after read's name and after else and end. Expressions
   and conditions are not checked, as designed.
8. **The `--trace` line shows the line number, not the address**, as the brief asks; the address
   of instruction i is 4 * i, and `ra`'s values in the trace are addresses.
9. **agree takes an optional directory** of programs (`./agree DIR`), for the tests; with no
   argument it is the brief's `./agree`.
10. **`\r` is a space** in the scanner and in mote0, so that a file with CRLF line ends works.
11. **The stub's prefix is `lang:`** in every program, so the stub names the track rather than
    the program it stopped.

## Found while building

- C's int, in 01.04 above: the translator copies expressions, and C works out `18 * 1000000007`
  in 32 bits. The design is kept; the test asserts the difference, and the fuzzer's programs leave
  it out (proggen.c_int_overflow).
- mote2c measured a statement wrongly when a comment followed it after spaces (`end    # end`);
  the fuzzer found it, and it is fixed (translate() no longer skips past the statement's end).
- The machine first did not trace the instruction that ends the program (`call exit` stops inside
  the call); stop() now traces it.
- The generator's never-zero divisor `(b * b + 1)`, nested, can make an expression that needs more
  than t0 to t6: one of the 2000 programs of seed 7 did, and `mote -S` rightly stopped with
  `expression too deep`. The generator was at fault, not the compiler: proggen.too_deep (the
  register depth as gen.c counts it, held to `mote -S` by the 01.10 test) now leaves such
  programs out, as c_int_overflow leaves out motec's int overflows.

## Tests and checks

- A test per lesson, `tests/01LL_<title>.py`, each running the real programs; each fails at the
  stub when its lesson's code is cut out (`./learn check-skeleton lang`: ok, all eleven).
- `tests/proggen.py`: a reference for the language in Python (its own scanner and parser by
  regular expression and recursion, integers wrapped to 64 bits) and a generator of random
  programs in one-statement-a-line form that always stop (each loop counts with a variable of its
  own, never assigned in the body), with comments, blank lines and indentation, using only names
  that have a value on every path; a program whose run divides by zero or reads past its input,
  that has a C int overflow, or that needs more than t0 to t6 is not kept. The tests run it: 100 programs through mote0, 25 through
  motec, 200 through mote, 150 through `-S` and 150 through `-S -O` on the machine; the first 20
  of the `-S` and of the `-S -O` listings also go through riscv64-elf-as.
- `tests/fuzz.py N --seed S`: N programs every way there is (about 17 minutes for 2000 on this
  Mac, most of it motec's C compiler). Run in this step: 2000 of seed 1 before the last edits to
  mote0.c, mote2c.c and machine.c, 0 disagreements; 2000 of seed 7 on the final code, 1 (the
  generator's too-deep program above); after too_deep, 2000 of seed 7 again: 0 disagreements
  (`2000 programs (seed 7, size 14), 5 ways each (mote0, motec, mote, machine, machine -O): 0
  disagree, 1015.6 s`).
- A program with 13 variables under -O (tests/0111): 11 in s1 to s11, v11 and v12 in memory
  (`addi sp, sp, -16`), and the right output, with and without -O.
- `-std=c11 -Wall -Wextra -pedantic -Werror`: the 01.01 test compiles every program's sources so;
  the project as the site shows it at each of the eleven lessons was also built so (not part of
  any test or check: done by hand with `./learn files` and `make CFLAGS=...`).
- `LANG_SANITIZE=1 ./learn test lang`: every program built with ASan and UBSan; all pass.
- Every .s the tests write or hold assembles with `riscv64-elf-as -march=rv64im -mabi=lp64`
  (skipped when no RISC-V as is installed).
- `./learn check-timeline lang`: the project at each lesson builds and boots; its steps check each
  lesson's sample and the ordinary errors for what is to come.

## Reads

- The RISC-V Instruction Set Manual, unprivileged volume, at the tag
  `riscv-isa-release-c05f172-2026-11-20` (commit c05f1725f255) of
  github.com/riscv/riscv-isa-manual:
  - `src/unpriv/rv32.adoc`: x0 is hardwired to 0 (norm:x0eq0); add, sub and addi ignore overflow
    and keep the low XLEN bits (norm:add_sub_overflow, norm:addi_overflow); mv is addi rd, rs, 0;
    jal writes pc + 4 to rd, j is jal with rd x0, ret is jalr with rd x0, rs1 x1, imm 0; beq,
    bne, blt and bge compare two registers (signed for blt and bge), and bgt and ble are blt and
    bge with the operands reversed; loads and stores add the register and the 12-bit offset for
    their address (norm:ldst_ea); the memory's byte order is the execution environment's choice
    (norm:endianness), and instructions are always little-endian (`intro.adoc`).
  - `src/unpriv/rv64.adoc`: ld loads 64 bits, sd stores the low 64 bits of rs2.
  - `src/unpriv/m-st-ext.adoc`: mul keeps the low XLEN bits of the product; div rounds toward
    zero; division by zero gives a quotient with every bit set (-1) and raises no exception (the
    manual's note: a language that wants an error adds one branch, which is what gen.c's check
    is); the most negative number divided by -1 overflows and gives the dividend.
  - The pseudo-instruction table and the registers' ABI names are no longer in this manual (its
    preface says the calling convention moved to the psABI), so they were read in the RISC-V
    Assembly Programmer's Manual, github.com/riscv-non-isa/riscv-asm-manual at commit 9d99308
    (2026-11-23), `src/asm-manual.adoc`: the names zero, ra, sp, gp, tp, t0 to t6, s0 to s11 and
    a0 to a7 for x0 to x31; `li` (a sequence of instructions, as many as the value needs), `mv`
    (addi rd, rs, 0), `neg` (sub rd, x0, rs), `beqz` and `bnez` (beq and bne against x0), `bgt`
    and `ble` (blt and bge reversed), `j` (jal x0), `call` (auipc x1 then jalr x1: two
    instructions, and ra holds the address after the second), `ret` (jalr x0, 0(x1)).
- The machine is little-endian, as the common RISC-V systems are; chapter 1 never shows it, since
  every load and store is 8 bytes. `call` and a large `li` count one instruction each here, where
  the real ones are two or more (the plan says so; chapter 5).
- Every .s here assembled with GNU as 2.46.0 for rv64im: gcd.s, the tests' programs, and what
  mote -S and -S -O write.
