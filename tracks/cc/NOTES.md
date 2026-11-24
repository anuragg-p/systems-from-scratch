# Notes for the lesson writers

Step 1 of the track: modules 00 to 02, the compiler as it stands at 02.06. Everything here was
run on the reference code or on the project as the site shows it at a lesson (`./learn files cc
--at NN.LL DIR`), on an Apple M-series Mac (macOS, Darwin 25.6, Apple clang 21, riscv64-elf-gcc
15.2.0, QEMU 10.2.1). The tests, the skeleton check, the timeline check, the sanitizer pass and a
5000-expression fuzz run also pass on Linux (Debian trixie in Docker, aarch64: gcc 14.2,
riscv64-unknown-elf-gcc 14.2, QEMU 10.0.13), and the project at every lesson builds there with
gcc and `-Werror`. Function names are given instead of line numbers.

## The upstream, and what this step takes from it

chibicc, https://github.com/rui314/chibicc, MIT, Copyright (c) 2019 Rui Ueyama, pinned at
90d1f7f199cc55b13c7fdb5839d1409806633fdb (upstream rewrites its history; the commit numbers in
this file count from the oldest commit at that pin: 1 is 0522e2d, 205 is 603de50).
`tracks/cc/LICENSE` is its LICENSE, byte for byte, and comes with the project from 00.01.

Taken, as they stand at commit 205 less what the plan leaves out: tokenize.c (error, verror_at,
error_at, error_tok, equal, skip, new_token, startswith, is_ident1, is_ident2, from_hex,
read_punct, is_keyword, read_escaped_char, string_literal_end, read_string_literal,
read_char_literal, read_int_literal, convert_keywords, add_line_numbers, tokenize), the token
and node types of chibicc.h (in cc.h), and the expression part of parse.c (new_node, new_binary,
new_unary, new_num, expr, bitor, bitxor, bitand, equality, relational, shift, add, mul, unary,
primary). main.c keeps upstream's shape for options (parse_args, usage, open_file) and its
read_file, and its print_tokens name. Ours: codegen.c (upstream's writes x86-64), rt/, ccrun,
same, try.c, the order of the lessons, print_tree and the --tokens and --tree formats, the
early forms, and the tests.

## Where the code is, lesson by lesson

```
tracks/cc/
  LICENSE      21   chibicc's, whole (FILES_FROM 00.01)
  Makefile     26   HOSTCC ?= cc, -std=c11 -Wall -Wextra -pedantic -g (FILES_FROM 00.01)
  main.c      317   options, read_file, print_tokens, print_tree, main; the three forms
  cc.h        107   Token, TokenKind, Node, NodeKind, the prototypes (FILES_FROM 01.01)
  tokenize.c  537   the scanner and the error functions (from 01.01)
  parse.c     402   the parser (from 02.01)
  codegen.c   181   the code generator, ours (from 02.03)
  try.c        13   the sample; four versions behind @from/@else (FILES_FROM 00.01)
  ccrun        49   sh: compile, assemble, link, run (from 00.02)
  same         88   sh: the same with gcc, compare (from 00.03)
  rt/start.S   31   _start: stack, call main, status to the test device (FILES_FROM 00.02)
  rt/link.ld   35   0x80000000, text, rodata, data, bss, 64 KiB stack (FILES_FROM 00.02)
  icon.svg, art.svg  the outline's track art, copied (the site's card and icon)
  track.py    713   settings, fixtures, timeline; NOTES.md; tests/ (14 tests, exprgen.py,
                    fuzz_expr.py)
```

The regions (`./learn solution cc NN.LL` prints them):

| lesson | file: function (region title) |
|---|---|
| 00.01 | main.c: parse_args (the command line), read_file (reading the file) |
| 00.02 | ccrun: the as, ld and qemu lines (assemble, link and run) |
| 00.03 | same: everything after the tool checks (the same program from gcc) |
| 01.01 | tokenize.c: error, equal, skip, new_token, read_int_literal, add_line_numbers, tokenize; main.c: print_tokens (printing the tokens) |
| 01.02 | tokenize.c: startswith, read_punct |
| 01.03 | tokenize.c: is_ident1, is_ident2, is_keyword, convert_keywords |
| 01.04 | tokenize.c: from_hex, read_escaped_char, string_literal_end, read_string_literal, read_char_literal |
| 01.05 | tokenize.c: verror_at (pointing at the source) |
| 02.01 | parse.c: new_node, new_binary, new_num, add, primary, parse; main.c: print_tree (printing the tree) |
| 02.02 | parse.c: mul |
| 02.03 | codegen.c: gen_binary, gen_expr, codegen |
| 02.04 | parse.c: bitor, bitxor, bitand, shift |
| 02.05 | parse.c: new_unary, equality, relational, unary |
| 02.06 | codegen.c: spill |

What a lesson adds outside its regions, through `@from` (the site shows it under "Also added in
this lesson"): 01.01 main.c's `--tokens` option, its call of tokenize and print_tokens, cc.h,
the Makefile's tokenize.c; 01.02 tokenize's punctuator branch (replacing the "+ or -" one); 01.03
the identifier branch, the convert_keywords call, TK_IDENT and TK_KEYWORD, their names in
print_tokens; 01.04 the comment, string and character branches in tokenize, the bases in
read_int_literal, TK_STR, the `str` and `str_len` fields, the string length in print_tokens;
01.05 the calls of verror_at in error_at and error_tok; 02.01 `--tree`, the parse call and the
tree in main, Node in cc.h; 02.02 the parenthesis in primary, the calls of mul in add, ND_MUL
and ND_DIV; 02.03 the codegen call in main; 02.04 `%` in mul, expr calling bitor, the rem, and,
or, xor, sll, sra cases; 02.05 unary in mul's calls, bitand calling equality, the comparison and
unary cases in gen_binary and gen_expr; 02.06 the spill call in gen_expr.

A cut region stops the compiler with `cc: NN.LL: <title> not written yet`, status 3, from todo()
(@internal in main.c, `_Noreturn`, declared in cc.h); in ccrun and same the stub (STUBS[""]) is
the same line from the shell. With a lesson's regions cut, its test fails at the stub (see
check-skeleton). In the project as the site shows it at a lesson there is no stub: where the
finished code calls what a later lesson brings, the earlier project has an ordinary error (02.03
to 02.05: `out of registers: the expression is too deep`).

## The three forms, and the markers that hold them

1. 00.01 to 00.03, main.c alone. main() skips spaces, takes one decimal number with strtoul,
   insists on nothing after it (`expected a number`, `expected the end of the file after the
   number`), and prints `  .globl main`, `main:`, `  li a0, N`, `  ret`. Held by: main.c's
   header comment (`@from 01.01` / `@else`), the includes (`#include "cc.h"` `@from 01.01`, the
   five system headers in its `@else`), a form-1 `error()` (an empty `@from 01.01` whose `@else`
   is the function), and main()'s body: the `@else` of the big `@from 01.01` block.
2. 01.01 to 02.02, the token walker. main() tokenizes, then walks: `get_number` (in the `@else`
   of an empty `@from 02.03` nested in a `@from 01.01`, top of main.c), `li a0, N`, then for each
   `+ n` or `- n`: `li t0, n` and `add a0, a0, t0` or `sub a0, a0, t0`, with upstream's `tok =
   skip(tok, "-")` for anything but "+". Held by the `@else` of main()'s `@from 02.03` block. At
   02.01 and 02.02 main() also parses (for `--tree`, and so the parser's errors come first);
   `Node *node = parse(tok)` is in a `@from 02.01` block used by both forms 2 and 3.
3. From 02.03: tokenize, parse, codegen; the input is one expression and then the end of the file.

try.c has four versions in nested blocks (`@from 01.01` > `@from 02.02` > `@from 02.06`, each
with an `@else`): `42`, `5 + 20 - 4` (21), `1 + 2 * 3 - 4 / 2` (5), `9 - (8 - (7 - (6 - (5 - (4
- (3 - 2))))))` (4). The materialized file has no marker lines, so the scanner before 01.04 never
sees a comment; the track's own try.c has them, and the finished scanner skips them.

The parser's rule comments (`// add = mul ("+" mul | "-" mul)*`) are the first lines inside each
function, not above it as upstream has them: a function hidden before its lesson (mul, bitand)
is hidden with its comment block only when no marker sits between the comment and the
signature, and the rule of mul changes at 02.04 and 02.05, that of bitand at 02.05.

## Every departure from upstream, and why

Upstream is quoted from commit 205 unless said otherwise.

1. **RISC-V code, our own codegen.c.** Upstream: `push %%rax` / `pop %s` around every operand.
   Ours: t0 to t5 as a stack and a spill past them (see "Reads").
2. **The input is a file from 00.01** (upstream reads argv[1] until commit 40). read_file lives
   in main.c, since form 1 has no tokenize.c; upstream's is in tokenize.c with tokenize_file.
   Upstream reads with `open_memstream`, not in our C library: ours grows a buffer with realloc.
3. **No driver.** Upstream's main.c forks cc1, as and ld (`run_subprocess`, `execvp`). Ours
   writes assembly and stops; ccrun and same do the rest (the plan: nothing to fork at 09.05).
4. **equal() with strncmp.** Upstream: `return memcmp(tok->loc, op, tok->len) == 0 &&
   op[tok->len] == '\0';`. memcmp may read all tok->len bytes of op even when op is shorter;
   AddressSanitizer says so (`global-buffer-overflow ... READ of size 8` in equal, from
   is_keyword, on the token `12345678`). strncmp stops at op's '\0'. With upstream's line back,
   `CC_SANITIZE=1 ./learn test cc 01.03` fails and the plain run passes.
5. **One argument to tokenize less, no File.** Upstream at 205: `Token *tokenize(File *file)`,
   File for the preprocessor's many files. Ours is commit 46's `tokenize(char *filename, char
   *p)` with `current_filename` and `current_input`; File comes with module 08.
6. **The end-of-file token sits on the newline that ends the last line.** Upstream puts it at
   the '\0' after that newline, so `1+` reports `t.c:2: ` and an empty line. Ours: `t.c:1: 1+`
   with the caret after the `+`. add_line_numbers is reshaped for it (upstream's `do ... while
   (*p++)` loop would read tok->loc after the last token).
7. **Columns.** Token gains `col` (from 1, in bytes, a tab is one), set by add_line_numbers with
   the line, for `--tokens` and the caret. add_line_numbers comes at 01.01, not 01.05 as the
   brief has "line numbers on tokens": `--tokens` prints `line:column` from 01.01.
8. **The caret under tabs.** Upstream prints `pos` spaces. Ours copies each tab of the line
   before the place into the caret line and a space for every other byte: the caret lines up
   whatever the terminal's tab width. Test: 0105, "after tabs".
9. **read_punct without `...`, `##` or ispunct.** Upstream's table has `"..."` and `"##"`; they
   come with variadic functions (09.02) and the preprocessor (08.03). `ispunct` is not in our C
   library, and accepts `@`, `$` and backquote: ours is a list of C's single-character
   punctuators, `strchr("+-*/%&|^~!=<>()[]{}.,;:?#", *p)`, so `@` is an invalid token at once.
10. **Keywords.** Upstream's is_keyword at 205 less `_Alignof`, `_Alignas`, `float`, `double`,
    plus `inline` (upstream reads it as an identifier with special cases in parse.c) and
    `__attribute__` (upstream's list gains it after 205), both in the plan's language.
11. **Escapes.** No GNU `\e` (upstream: `case 'e': return 27;`); unknown escapes are an error,
    `unknown escape sequence`, at the backslash (upstream: `default: return *p;`;
    riscv64-elf-gcc 15.2.0 compiles `'\q'` with `warning: unknown escape sequence: '\q'`); `\\ \' \" \?` named; a value over 255 is `escape sequence out
    of range` (upstream truncates); the hex loop checks as it goes, so `\x123456789` cannot
    overflow an int.
12. **Character constants.** One argument (no wide `L'x'`); `''` is `empty character
    constant`; `'ab'` is `a character constant holds one character` (upstream takes the first
    and skips to the quote with `strchr(p, '\'')`, across lines too); a value over 127 is
    `a character constant above 127 is not supported yet`: what '\xff' is depends on the sign
    of plain char (unsigned on RISC-V), which arrives with types at 06.02.
13. **Strings.** The decoded length is kept in `str_len` (upstream's is the array type,
    `tok->ty = array_of(ty_char, len + 1)`; types come at 06.01); an unclosed string is
    reported at its opening quote (upstream: at the character after it).
14. **Numbers.** No suffixes (06.02), no floating point ever; `strncasecmp`, not in our
    library, is spelled out; a letter, digit or `_` right after the digits is `invalid numeric
    constant` (upstream at 205 reads `12a` as a number and an identifier; it adds pp-numbers
    and this error at 207). The value is `long`, not `int64_t` (stdint.h is not in the list; the
    host and RV64 are both LP64). A literal over 2^64 - 1 is not diagnosed (strtoul clamps and
    sets errno, which the list leaves out).
15. **Comments.** `/* */` is found with a loop of startswith, not `strstr`.
16. **Parser.** new_add/new_sub (pointer arithmetic) are new_binary until 06.04; unary's
    operand is `unary`, not `cast` (06.03); `expr` is the loosest level (`add`, then `bitor`
    from 02.04), not `assign`; `consume` is left out until its first caller (it has none in
    modules 00 to 02). Unary `+` makes no node, as upstream, so `--tree` of `+3` is `num 3`.
17. **_Noreturn** on error, error_at, error_tok and todo (C11; in the keyword list), so a
    function that ends in error_tok needs no dummy return under -Wall. Upstream asks for no
    warnings at all (its Makefile at 205: `CFLAGS=-std=c11 -g -fno-common`); ours builds
    silent under `-Wall -Wextra -pedantic` with clang 21 and gcc 14, at every lesson.
18. **The compiler's own C library.** Upstream uses assert, errno, strerror, glob, fork,
    strndup, open_memstream and more. Ours uses only the list below; 00.01's test checks it.

Where this step departs from the brief, and why:

- **CC_UNDER_TEST, not CC**, names the compiler `same` tests. CC is the host's C compiler to
  make, to kilo's track.py (`os.environ.get("CC", "cc")`) and to most Linux shells that set
  it; with `CC=gcc` exported, `same` would have run gcc as the compiler under test.
- **The parser's 02.01 grammar is `expr = add`, `add = primary (...)*`**, not `expr = primary
  (...)*`: the + and - loop is in add from the start, under upstream's name, so that 02.04 can
  put levels above it with a one-line change in expr.
- **`./learn run cc` at 02.01 and 02.02 prints the tree** (`./cc --tree try.c`): at 02.02 the
  sample needs precedence and the walker that still makes the code cannot compile it (it stops
  at `*` with `expected '-'`, an ordinary error the timeline checks).
- **gcc gets `-mcmodel=medany -fno-pie`** besides the brief's flags: the program sits at
  0x80000000, out of reach of the default code model, and a PIE wants a GOT. Neither matters
  until there are globals (05.02).
- **start.S does not clear bss** (the plan has it): nothing is in bss before 05.02, and QEMU's
  memory starts zeroed. It belongs to 05.02.
- **The track's icon.svg and art.svg are copies of outlines/cc/icon.svg and art.svg.** Once
  tracks/cc exists the site reads the track's own; without them it loses the card and icon, and
  a selftest (test_progress, which takes the first track with lessons, now cc) fails.

## The C library the compiler may use

stdio.h `fopen fclose fread fprintf vfprintf printf fputc`, `stdin stdout stderr`, `FILE`;
stdlib.h `calloc realloc exit strtoul`; string.h `strlen strcmp strncmp memcmp memcpy strchr`;
ctype.h `isdigit isalpha isalnum isspace isxdigit`; stdarg.h; stdbool.h. track.py has the list
(LIBC_HEADERS, LIBC_FUNCTIONS) and libc_problems(), which 00.01's test runs: it fails on any
other header and on any call of a name the sources do not define and the list does not hold. The
same test compiles the sources with `-Werror` and the Makefile's flags. Used so far: all but
`printf`, `memcpy` and `isalpha`. Nothing is added to the list in this step. The formats used
(our printf must have them at 09.05): `%s %d %ld %lu %c %%`, `%*s` and `%.*s`; fprintf's
return value (verror_at's indent). Plain char goes to the ctype functions as upstream does: on
RISC-V char is unsigned, so the course's ctype must take 0 to 255.

## What the compiler prints

`--tokens`, one line a token: `LINE:COL KIND TEXT`, then ` VALUE` for `num` (decimal, as a
signed 64-bit number) and ` LENGTH` for `str` (bytes decoded, without the '\0'). KIND is `num
punct ident keyword str eof`; a character constant is a `num`; `eof` has no text.

```
$ printf '5 + 20 - 4' | ./cc --tokens -
1:1 num 5 5
1:3 punct +
1:5 num 20 20
1:8 punct -
1:10 num 4 4
1:11 eof
```

`--tree`, one node a line, two spaces of indent a level, the left child first: the operator
(`+ - * / % << >> & ^ | == != < <= ! ~`, and `-` for negation, told from subtraction by having
one child) or `num` and the value. `a > b` prints as `<` over `b` then `a`.

```
$ printf '2*3+4' | ./cc --tree -          $ printf '-2 > 1' | ./cc --tree -
+                                         <
  *                                         num 1
    num 2                                   -
    num 3                                     num 2
  num 4
```

An error with a place, from 01.05: `FILE:LINE: TEXT OF THE LINE`, then as many spaces as that
prefix, a tab for each tab before the place and a space for each other byte, `^ ` and the
message. Before 01.05 the message alone. Without a place (`cannot open x.c`, `unknown
argument: -x`): one line. Exit status 1, and nothing on standard output in form 3; in form 2 the
walker has written part of the assembly when it meets an error (as upstream's first commits
do), so the timeline sends its output to /dev/null for those.

The assembly: `  .globl main`, `main:`, instructions with two spaces before them and `, `
between operands, `mv a0, t0`, `ret`. No comments, no frame yet.

## Tests and the int rule

One test a lesson in tests/ (`./learn test cc`), fixtures in track.py (its docstring lists
them). Programs are checked against gcc for the same machine (`same`, `value`). Expressions in
tests and in the fuzz stay inside what C defines for int: no overflow, no division by zero or of
INT_MIN by -1, no shift by less than 0 or more than 31, no negative number shifted left (`>>` of
a negative number is implementation-defined; gcc shifts in the sign, as ours does). So gcc's
32-bit int and our 64-bit values are the same numbers, and value() checks all 64 bits of ours by
compiling `(e) == (want)`. tests/exprgen.py makes random expressions with their values by
those rules; 02.06's test runs 200 of them (seed 2026) through value() on eight threads, and
tests/fuzz_expr.py runs as many as asked, twenty to a program, falling back to one at a time on a
failure.

`CC_SANITIZE=1 ./learn test cc` runs every compile under AddressSanitizer and
UndefinedBehaviorSanitizer (leak checking off: the compiler frees nothing, as chibicc). A
missing toolchain or QEMU fails a test in one line saying what to install.

## Measurements (this Mac)

- `./cc try.c` 3 ms at best; `./ccrun try.c` 53 ms at best, 60 ms on average (cc, two `as`, `ld`
  and QEMU; QEMU alone 26 ms); `./same try.c` 124 ms at best, 141 ms on average.
- `./learn test cc`: 28 s for the 14 tests (02.06 alone 10 s: 200 random expressions on eight
  threads); with CC_SANITIZE=1, 68 s. On Linux in Docker the whole round (tests, the
  sanitizer pass, check-skeleton, check-timeline, the 14 projects with gcc -Werror, 5000 fuzzed
  expressions) took 53 s.
- `./learn check-skeleton cc` 9 s; `./learn check-timeline cc` 16 s (14 lessons, 4 at a time).
- `fuzz_expr.py -n 5000`: 5 to 6 s (250 programs from each compiler); 437 of those 5000 need more
  than six registers.

## Kept simple, or left for later steps

- The spill pushes the left operand even when the right one is a number, which needs no register
  of its own (`li t5, 7` then a `ld t6`). Sethi-Ullman numbering, or computing the deeper side
  first, would spill less; neither is in the design.
- Every number is loaded with `li`, even where an immediate form exists (`addi`); gcc folds
  constant expressions even at -O0 (see "Reads").
- `consume` (upstream's) has no caller in modules 00 to 02 and is left out until it has one.
- A workspace (`./learn start cc`) is the finished tree with one lesson cut, so its try.c has the
  marker comment lines, which a learner's scanner before 01.04 cannot read: run the project as
  the site shows it (`./learn run cc --at NN.LL`) for the lesson's own try.c.
- In form 2 the walker's errors come after part of the assembly is on standard output.
- `make` on macOS is GNU make 3.81, which compares whole seconds: a source written in the same
  second as ./cc was built may not trigger a rebuild (found while running the break-it
  experiments; `make clean` or removing ./cc fixes it).
- `read_file`'s added newline and start.S's `andi a0, a0, 0xff` are not needed by anything in this
  step (with either taken out every test passes): the scanner and verror_at stop at the '\0' as
  well as the newline, and the system keeps only the low 8 bits of QEMU's exit code anyway.
  Both stay: the newline is upstream's and lines are easier to talk about, and the andi says
  what a status is.

## The lessons, one by one

Every transcript below was run in the project as the site shows it at that
lesson (`./learn files cc --at NN.LL DIR`, then `make -s` there), on the
owner's Mac (Apple clang 21, riscv64-elf binutils and gcc 15.2.0, QEMU
10.2.1). Commands are as typed; output is exact, stdout and stderr together.
"Break it" items marked (test) were run on tracks/cc with the lesson's test
(`./learn test cc NN.LL`) and the file put back after; the others were run
in a copy of the lesson's project, never in the track.

### 00.01 From a number to a running program

- Regions: main.c `parse_args` (the command line), `read_file` (reading the
  file). Given whole with the new file: `error` (form 1's own), `usage`,
  `open_file`, and `main`, which is form 1: skip spaces, `strtoul(p, &p, 10)`,
  nothing else allowed, four `fprintf` lines. Also LICENSE, the Makefile
  (SRCS = main.c, HDRS empty) and try.c (`42`).

```
$ ./cc try.c
  .globl main
main:
  li a0, 42
  ret
$ printf '4 2\n' > two.c
$ ./cc two.c; echo $?
expected the end of the file after the number
1
$ ./cc nosuch.c; echo $?
cannot open nosuch.c
1
```

Break it:
- (test) `read_file` without the newline it adds at the end: 00.01's test
  still passes. Finding: nothing in this step needs that newline (form 1
  skips with isspace; later the scanner stops at '\0'). It is chibicc's;
  when it is there the end-of-file token sits on it.
- `strtoul(p, &p, 0)` instead of base 10: `printf '042\n' > o.c; ./cc o.c`
  gives `li a0, 34`. Base 10 is a decision; C's octal arrives at 01.04.

### 00.02 What the assembler, the linker and the machine do with it

- Region: ccrun's three commands (assemble, link and run). Given: ccrun's
  usage line, the search for a tool prefix and for QEMU (one line naming
  what to install), `./cc -o build/prog.s`. New files, whole: rt/start.S,
  rt/link.ld.

The steps by hand, as the lesson has the reader type them first:

```
$ ./cc -o prog.s try.c
$ riscv64-elf-as -march=rv64im -mabi=lp64 -o start.o rt/start.S
$ riscv64-elf-as -march=rv64im -mabi=lp64 -o prog.o prog.s
$ riscv64-elf-ld -T rt/link.ld -o prog.elf start.o prog.o
$ qemu-system-riscv64 -machine virt -bios none -display none -monitor none -serial stdio -kernel prog.elf; echo $?
42
$ riscv64-elf-objdump -d prog.elf | sed -n '/<_start>:/,$p' | head -20
0000000080000000 <_start>:
    80000000:	00010117          	auipc	sp,0x10
    80000004:	04010113          	addi	sp,sp,64 # 80010040 <stack_top>
    80000008:	030000ef          	jal	80000038 <main>
    8000000c:	0ff57513          	zext.b	a0,a0
    ...
0000000080000038 <main>:
    80000038:	02a00513          	li	a0,42
    8000003c:	00008067          	ret
$ printf '300\n' > n.c; ./ccrun n.c; echo $?
44
$ ./ccrun nosuch.c; echo $?
cannot open nosuch.c
1
```

The objdump shows what the lesson can point at: `la` became auipc + addi,
`call` became one `jal` (the linker relaxed it), and `andi a0, a0, 0xff` is
printed as its alias `zext.b`.

Break it:
- (test) rt/start.S without `andi a0, a0, 0xff`: the test still passes.
  Finding: QEMU exits with the device's 16-bit code and the OS keeps its low
  8 bits, so 300 still gives 44; the andi only decides between the PASS and
  FAIL commands, and 0x3333 with code 0 also exits 0.
- (test) rt/link.ld at `. = 0x80001000`: "ccrun n0.c did not finish within
  120 s". The machine starts at 0x80000000, where nothing is now, and never
  reaches the test device.

### 00.03 The same answer as gcc: a test for every lesson

- Region: `same`'s body (the same program from gcc): build with the
  compiler under test and with gcc, run both, compare. Given: usage, the
  gcc prefix and QEMU search, `CC_UNDER_TEST`.

```
$ ./same try.c; echo $?
same: status 42
0
$ cat wrongcc
#!/bin/sh
printf "  .globl main\nmain:\n  li a0, 7\n  ret\n" > "$2"
$ CC_UNDER_TEST=./wrongcc ./same try.c; echo $?
ours: status 7
gcc: status 42
differ
1
$ cat build/same/gcc.c
int main(void) { return 42

; }
```

Break it:
- A compiler that is wrong on purpose, through `CC_UNDER_TEST` (above):
  `differ`, exit 1. On a file holding 7 the same fake says `same: status 7`:
  one sample can agree by luck, which is why every later test runs many.
- gcc without `-mcmodel=medany -fno-pie`: still `same: status 42`. Finding:
  with no global variable there is no address to reach; the flags matter
  from 05.02's globals, not now.

### 01.01 A stream of tokens: numbers, plus and minus

- Regions: tokenize.c `error`, `equal`, `skip`, `new_token`,
  `read_int_literal` (decimal only), `add_line_numbers`, `tokenize` (spaces,
  numbers, "+" and "-"); main.c `print_tokens` (printing the tokens).
- Outside regions: cc.h comes whole; main.c includes it and takes
  `--tokens`; `get_number` and the walker in `main` (form 2, chibicc's
  commits 2 and 3: `li a0, N`, then `li t0, N` / `add` or `sub a0, a0, t0`);
  `error_at` and `error_tok` print the message alone; the Makefile adds
  tokenize.c and cc.h; try.c becomes `5 + 20 - 4`.

```
$ ./cc --tokens try.c
1:1 num 5 5
1:3 punct +
1:5 num 20 20
1:8 punct -
1:10 num 4 4
1:11 eof
$ ./cc try.c
  .globl main
main:
  li a0, 5
  li t0, 20
  add a0, a0, t0
  li t0, 4
  sub a0, a0, t0
  ret
$ ./ccrun try.c; echo $?
21
$ printf '1 * 2\n' > mul.c; ./cc mul.c; echo $?
invalid token
1
```

Break it:
- (test) columns from 0 (`tok->col = p - line`): fails, "--tokens of
  '5 + 20 - 4':".
- `add_line_numbers` not called: every token prints `0:0` (and clang warns
  that the function is unused).

### 01.02 Longest match

- Regions: `startswith`, `read_punct` (21 punctuators of three and two
  characters, longest first, then the single characters
  `+-*/%&|^~!=<>()[]{}.,;:?#`). `tokenize`'s punctuator branch replaces the
  "+ or -" one (@from 01.02, the old one in @else).

```
$ printf '1 >>= 2 -> 3 != 4 ... 5' > p.c; ./cc --tokens p.c
1:1 num 1 1
1:3 punct >>=
1:7 num 2 2
1:9 punct ->
1:12 num 3 3
1:14 punct !=
1:17 num 4 4
1:19 punct .
1:20 punct .
1:21 punct .
1:23 num 5 5
1:24 eof
$ printf '1 * 2\n' > mul.c; ./cc mul.c >/dev/null; echo $?
expected '-'
1
```

"..." is three dots here: it comes with variadic functions (09.02). The
walker now sees "*" as a token, and `skip(tok, "-")` names what it wanted.

Break it:
- (test) the two-character punctuators tried before the three-character
  ones: "'a>>=b': ['ident a', 'punct >>', 'punct =', 'ident b']".
- "--" taken out of the table: `1 -- 2` scans as `1`, `-`, `-`, `2`.

### 01.03 Identifiers and keywords

- Regions: `is_ident1`, `is_ident2`, `is_keyword` (37 keywords),
  `convert_keywords`. Outside: `tokenize`'s identifier branch and its call of
  `convert_keywords`; `TK_IDENT`, `TK_KEYWORD` and the prototype in cc.h;
  their names in `print_tokens`.

```
$ printf 'return x1 _y int2 float\n' > i.c; ./cc --tokens i.c
1:1 keyword return
1:8 ident x1
1:11 ident _y
1:14 ident int2
1:19 ident float
1:24 eof
$ printf '1 + x\n' > x.c; ./cc x.c >/dev/null; echo $?
expected a number
1
```

Break it:
- (test) "float" added to the keywords: "should be identifiers:
  [('keyword', 'float')]". The test holds the cut of floating point.
- `is_ident2` without digits: `x1 int2` scans as `ident x`, `num 1`,
  `keyword int`, `num 2`.

### 01.04 Comments, character constants and strings

- Regions: `from_hex`, `read_escaped_char`, `string_literal_end`,
  `read_string_literal`, `read_char_literal`. Outside: comment skipping and
  the string and character branches in `tokenize`; `read_int_literal`'s
  prefixes (0x, 0b, a leading 0); `str`, `str_len` and `TK_STR` in cc.h; a
  string's decoded length in `print_tokens`.

```
$ cat lit.c
/* a comment */ "a\tb" '\n' 0x1F 017 0b101 // the end
$ ./cc --tokens lit.c
1:17 str "a\tb" 3
1:24 num '\n' 10
1:29 num 0x1F 31
1:34 num 017 15
1:38 num 0b101 5
1:54 eof
$ cat e.c
'\e'
$ ./cc e.c; echo $?
unknown escape sequence
1
$ printf '0x10 + 010 + 0b10 - 1\n' > b.c; ./ccrun b.c; echo $?; ./same b.c
25
same: status 25
```

Break it:
- (test) a block comment that ends at any "*": "comments run together:
  ['1:5 num 1 1', '1:12 punct +', '1:17 punct /', ...]".
- (test) `case 'v': return 'v';`: "'\v' should be 11: 1:1 num '\v' 118".

### 01.05 Errors that point at the source

- Region: `verror_at` (pointing at the source). Outside: `error_at` and
  `error_tok` call it (@from 01.05; their message-only bodies are the @else).

```
$ printf '1 +\n\t2 +\n' > end.c; ./cc end.c >/dev/null; echo $?
end.c:2: 	2 +
         	   ^ expected a number
1
$ printf '1 + $\n' > d.c; ./cc d.c; echo $?
d.c:1: 1 + $
           ^ invalid token
1
$ printf '1 +\n\n   '"'"'ab'"'"'\n' > q.c; ./cc q.c; echo $?
q.c:3:    'ab'
          ^ a character constant holds one character
1
```

The caret's line is the prefix's width in spaces, then a tab for each tab
of the line before the place. The end of the file sits on the last line's
newline, so `expected a number` points just after `2 +`.

Break it:
- (test) spaces for tabs under the caret: fails, "after tabs:".
- The caret without the prefix's width: `    ^ invalid token`, four columns
  in, under nothing (clang also warns that `indent` is unused).

### 02.01 A grammar, and a function for each rule

- Regions: parse.c `new_node`, `new_binary`, `new_num`, `add`, `primary`,
  `parse`; main.c `print_tree` (printing the tree). Outside: `expr` (here
  `return add(rest, tok);`), the prototypes, Node and NodeKind (ND_ADD,
  ND_SUB, ND_NUM) in cc.h, `--tree`, and `main` parsing before the walker.

```
$ ./cc --tree try.c
-
  +
    num 5
    num 20
  num 4
$ printf '1 * 2\n' > mul.c; ./cc --tree mul.c; echo $?
mul.c:1: 1 * 2
           ^ extra token
1
$ printf '1 +\n' > e.c; ./cc --tree e.c; echo $?
e.c:1: 1 +
          ^ expected an expression
1
```

Break it:
- (test) minus with its operands swapped in `add`: fails, "--tree of
  1-2-3:".
- The right operand of "-" read by `add` instead of `primary`: `--tree` of
  `1 - 2 - 3` leans right, `(- 1 (- 2 3))`, but `./ccrun s.c` still exits
  252, which is -4: at 02.01 the code comes from the walker, which goes left
  to right whatever the tree says. Tree and program agree only from 02.03.

### 02.02 The syntax tree

- Region: `mul`. Outside: `add` calls `mul` (three @from lines),
  `primary`'s `"(" expr ")"`, ND_MUL and ND_DIV, the prototype, their names
  in `print_tree`; try.c becomes `1 + 2 * 3 - 4 / 2`.

```
$ ./cc --tree try.c
-
  +
    num 1
    *
      num 2
      num 3
  /
    num 4
    num 2
$ printf '(1 + 2) * 3\n' > p.c; ./cc --tree p.c
*
  +
    num 1
    num 2
  num 3
$ ./ccrun try.c; echo $?
try.c:1: 1 + 2 * 3 - 4 / 2
               ^ expected '-'
1
```

The parser takes "*", the walker that still makes the code does not: an
ordinary error, which is why `./learn run cc` shows the tree at 02.01 and
02.02.

Break it:
- (test) `add`'s first operand a `primary`: "./cc failed (status 1) on
  '2*3+4'".
- `primary` not skipping the ")": `(1 + 2) * 3` is "extra token" at the ")".

### 02.03 Code from a tree: registers as a stack

- Regions: codegen.c `gen_binary` (add, sub, mul, div), `gen_expr`,
  `codegen`. Outside: `println`, `reg[]` and NREG, the "out of registers"
  error where 02.06 will call `spill` (@else), `main` calls `codegen` (the
  walker and `get_number` go), the Makefile adds codegen.c.

```
$ ./cc try.c
  .globl main
main:
  li t0, 1
  li t1, 2
  li t2, 3
  mul t1, t1, t2
  add t0, t0, t1
  li t1, 4
  li t2, 2
  div t1, t1, t2
  sub t0, t0, t1
  mv a0, t0
  ret
$ ./ccrun try.c; echo $?
5
$ printf '1 - (2 - (3 - (4 - (5 - (6 - 7)))))\n' > deep.c; ./cc deep.c >/dev/null; echo $?
deep.c:1: 1 - (2 - (3 - (4 - (5 - (6 - 7)))))
                                     ^ out of registers: the expression is too deep
1
```

Break it:
- (test) the right operand computed at d, over the left: fails, "the code
  for 1+2:".
- No `mv a0, t0`: `./ccrun try.c` exits 0 (a0 holds what `_start` left
  there), and `same` says `ours: status 0`, `gcc: status 5`, `differ`.

### 02.04 Precedence and associativity: the whole table

- Regions: `bitor`, `bitxor`, `bitand`, `shift`. Outside: `expr` returns
  `bitor`, `mul` takes "%", `gen_binary` gets rem, and, or, xor, sll, sra,
  the six kinds in cc.h and `print_tree`.

```
$ ./cc --tree ops.c
|
  <<
    %
      num 6
      num 4
    num 2
  num 1
$ ./cc ops.c
  .globl main
main:
  li t0, 6
  li t1, 4
  rem t0, t0, t1
  li t1, 2
  sll t0, t0, t1
  li t1, 1
  or t0, t0, t1
  mv a0, t0
  ret
$ ./ccrun ops.c; echo $?
9
$ printf '(0-16) >> 2\n' > sh.c; ./same sh.c
same: status 252
$ printf -- '-3 < 2\n' > c.c; ./cc c.c; echo $?
c.c:1: -3 < 2
       ^ expected an expression
1
```

Break it:
- (test) ">>" as `srl`: fails, "no sra in:".
- `bitor` calling `bitand`, past the "^" level: `1 ^ 3 | 4` is "extra
  token" at the "^" (and clang warns that `bitxor` is unused).

### 02.05 Unary operators and comparisons

- Regions: `new_unary`, `equality`, `relational`, `unary`. Outside: `bitand`
  calls `equality` and `mul` calls `unary` (@from 02.05 lines), the
  comparisons in `gen_binary` and neg, seqz, not in `gen_expr`.

```
$ printf '1 > 2\n' > g.c; ./cc --tree g.c; ./cc g.c
<
  num 2
  num 1
  .globl main
main:
  li t0, 2
  li t1, 1
  slt t0, t0, t1
  mv a0, t0
  ret
$ printf '1 <= 2\n' > le.c; ./cc le.c
  .globl main
main:
  li t0, 1
  li t1, 2
  slt t0, t1, t0
  xori t0, t0, 1
  mv a0, t0
  ret
$ printf -- '-3 < 2 == !0\n' > cmp.c; ./ccrun cmp.c; echo $?; ./same cmp.c
1
same: status 1
```

Break it:
- (test) ">" without swapping its operands: "1>2: (< 1 2), not (< 2 1)".
- (test) "<=" as plain `slt`: fails, "the code for 1<=2:".

### 02.06 Out of registers: spilling to memory

- Region: `spill`. Outside: `gen_expr` calls it where the error was, its
  prototype, the comment on t6; try.c becomes the deep subtraction.

```
$ cat try.c
9 - (8 - (7 - (6 - (5 - (4 - (3 - 2))))))
$ ./cc try.c
  .globl main
main:
  li t0, 9
  li t1, 8
  li t2, 7
  li t3, 6
  li t4, 5
  li t5, 4
  addi sp, sp, -16
  sd t5, 0(sp)
  li t5, 3
  addi sp, sp, -16
  sd t5, 0(sp)
  li t5, 2
  ld t6, 0(sp)
  addi sp, sp, 16
  sub t5, t6, t5
  ld t6, 0(sp)
  addi sp, sp, 16
  sub t5, t6, t5
  sub t4, t4, t5
  sub t3, t3, t4
  sub t2, t2, t3
  sub t1, t1, t2
  sub t0, t0, t1
  mv a0, t0
  ret
$ ./ccrun try.c; echo $?
4
$ ./same try.c
same: status 4
```

Two spills: `4 - (3 - 2)` has 4 in t5, and inside it `3 - 2` has 3 in t5;
even the leaf `2` goes through a spill, since the scheme spills whenever
d + 1 would be 6. A left-leaning chain (`((((((1 - 2) - 3) - 4) - 5) - 6) -
7) - 8`) uses t0 and t1 only, at any length.

Break it:
- (test) the `addi sp, sp, 16` after the reload left out: fails, "1 spills,
  as many pops as pushes".
- The operands swapped in the instruction after the reload
  (`gen_binary(node, reg[d], reg[d], "t6")`): `./ccrun try.c` exits 12,
  `same` says `ours: status 12`, `gcc: status 4`, `differ`.

## Reads

What other compilers and QEMU do, each read in their source or their output at the version
named, with the file, the function and a short quote. A lesson may say only what is here.

### chibicc, commits 1 to 8 (pinned at 90d1f7f; commit numbers count from the oldest)

Read from each commit's tree and its diff against the one before.

1. 0522e2d "Compile an integer to an exectuable that exits with the given number". main.c
   takes the number from the command line, not a file: `printf("  mov $%d, %%rax\n",
   atoi(argv[1]));` then `printf("  ret\n");`. test.sh assembles with the host's gcc:
   `gcc -static -o tmp tmp.s`, runs it and compares `$?`.
2. bf7081f "Add + and - operators". Still no tokens: main() walks the string with strtol,
   `printf("  add $%ld, %%rax\n", strtol(p, &p, 10));` and the same with sub; anything else
   is `unexpected character`.
3. a1ab0ff "Add a tokenizer to allow space characters between tokens". Token, tokenize(),
   new_token(), equal(), skip() and get_number(); main() walks the tokens:
   `printf("  mov $%d, %%rax\n", get_number(tok));`, then `+ n` or `skip(tok, "-")` and
   `- n`. Errors are plain messages (`error("expected a number")`). Our form 2 is this walker
   (main.c, 01.01 to 02.02), with li/add/sub for RISC-V and the file read from disk.
4. cc5a6d9 "Improve error message". verror_at(), error_at(), error_tok(): one line of input
   and a caret, `fprintf(stderr, "%*s", pos, ""); // print pos spaces.` There is one line only
   (the input is argv[1]); the file name and line number come at commit 46.
5. 84cfcaf "Add *, / and ()". Node, new_binary(), expr/mul/primary by recursive descent, and
   the first code generator. Every value goes through %rax and the machine stack:

        gen_expr(node->rhs);
        push();
        gen_expr(node->lhs);
        pop("%rdi");

   with `push()` printing `"  push %%rax\n"` and counting `depth++`, and main() ending in
   `assert(depth == 0);`. ND_DIV is `cqo` then `idiv %%rdi`.
6. bf9ab52 "Add unary plus and minus". `// unary = ("+" | "-") unary | primary`; "+" returns
   the operand with no node (`return unary(rest, tok->next);`), "-" makes ND_NEG, and
   gen_expr does `printf("  neg %%rax\n");`. mul() now calls unary().
7. 25b4b85 "Add ==, !=, <= and >= operators". read_punct() with `startswith(p, "==") ||
   startswith(p, "!=") || startswith(p, "<=") || startswith(p, ">=")` and `ispunct(*p)` for one
   character; equality() and relational(), with `>` as `new_binary(ND_LT, add(&tok,
   tok->next), node)` (the operands swapped, as ours); the code is `cmp %%rdi, %%rax`, then
   sete/setne/setl/setle into %al and `movzb %%al, %%rax`.
8. 725badf "Split main.c into multiple small files". chibicc.h, tokenize.c, parse.c,
   codegen.c, and a main.c of `tokenize(argv[1])`, `parse(tok)`, `codegen(node)`.

The design ours does not use. chibicc evaluates the right operand first, pushes it, evaluates
the left one into %rax, pops the right one into %rdi: one register for every value, and a
memory push and pop for every binary operator, at any depth. Ours (02.03, 02.06) keeps values in
t0 to t5 as a stack, left operand at d and right at d + 1, and touches memory only past the sixth
(spill(): `addi sp, sp, -16`, `sd t5`, then `ld t6` and `addi sp, sp, 16`). chibicc's order
(right first) also matters: ours computes the left operand first, as the tree reads.

### tcc (mob branch, e9e9e7f6236895a32c5e905aada486bab6671e95, 2026-11-23)

The plan says tcc keeps a value stack in registers "as far as I remember". Confirmed, with three
corrections: the stack holds descriptions of values, not registers; when registers run out it
spills the oldest value, not the newest; and on RISC-V the values live in a0 to a7.

- tccgen.c: `ST_DATA SValue *vtop;`, `static SValue _vstack[1 + VSTACK_SIZE];`, `#define vstack
  (_vstack + 1)`; tcc.h: `#define VSTACK_SIZE 512`. An SValue says where a value is: a
  constant, a register (`vtop->r`), or an lvalue in the frame (`VT_LOCAL | VT_LVAL`).
- get_reg(int rc), tccgen.c: `/* find a free register of class 'rc'. If none, save one
  register */`. It first looks for a register no vstack entry uses; if there is none:
  `/* no register left : free the first one on the stack (VERY IMPORTANT to start from the
  bottom to ensure that we don't spill registers used in gen_opi()) */`, and calls
  `save_reg(r)`.
- save_reg_upstack(): `/* save r to the memory stack, and mark it as being free */`. The value
  goes to a temporary in the frame, `l = get_temp_local_var(size, align, &r2);`, and the entry is
  rewritten to say so: `p->r = VT_LVAL | VT_LOCAL;`. So a spilled value stays on tcc's value
  stack, as a memory operand; ours leaves the register stack and comes back into t6.
- Calls: riscv64-gen.c, gfunc_call(int nb_args): `save_regs(nb_args + 1);` then
  `gcall_or_jmp(1);`. save_regs(), tccgen.c: `/* save registers up to (vtop - n) stack entry
  */` - every value below the call's arguments that sits in a register goes to memory first,
  since a call does not keep them. The plan's 04.01 does the same for live t registers.
- riscv64-gen.c: `#define NB_REGS 19 // x10-x17 aka a0-a7, f10-f17 aka fa0-fa7, xxx, ra, sp`;
  reg_classes[] gives RC_INT to the first eight, and ireg() maps them: `return r + 10;  // tccrX
  --> aX == x(10+X)`. Expression values are in a0 to a7, the argument registers.
- gen_opic(), tccgen.c: two constants are folded at compile time, `if (c1 && c2) { switch(op)
  { case '+': l1 += l2; break;`... so tcc, like gcc, writes no code for `1 + 2 * 3`.
- gen_opil(), riscv64-gen.c: a constant right operand that fits 12 bits becomes an immediate:
  `EI(0x13 | cll, func3, ireg(d), a, fc);` with the comment `// addi d, a, fc`. Ours always
  loads both operands (`li`), one more instruction for every constant.

### clang (llvmorg-21.1.0): precedence climbing, one loop for every level

clang/lib/Parse/ParseExpr.cpp, Parser::ParseRHSOfBinaryExpression(ExprResult LHS, prec::Level
MinPrec). One function handles every binary operator; precedence is a number from a table, not
a function per level. The loop stops at an operator looser than MinPrec (`if (NextTokPrec <
MinPrec) return LHS;`), reads one operand (`RHS = ParseCastExpression(...)`), and if the next
operator binds tighter, recurses for the right side:

    // Assignment and conditional expressions are right-associative.
    bool isRightAssoc = ThisPrec == prec::Conditional ||
                        ThisPrec == prec::Assignment;
    ...
    if (ThisPrec < NextTokPrec ||
        (ThisPrec == NextTokPrec && isRightAssoc)) {
      ...
      RHS = ParseRHSOfBinaryExpression(RHS,
                            static_cast<prec::Level>(ThisPrec + !isRightAssoc));

`ThisPrec + !isRightAssoc` is associativity in one expression: a left-associative operator asks
for strictly tighter operators on its right. The table, clang/include/clang/Basic/
OperatorPrecedence.h, `namespace prec`: Comma 1, Assignment 2, Conditional 3, LogicalOr 4,
LogicalAnd 5, InclusiveOr 6, ExclusiveOr 7, And 8, Equality 9, Relational 10, Spaceship 11,
Shift 12, Additive 13, Multiplicative 14; getBinOpPrecedence() in OperatorPrecedence.cpp maps
each token (`case tok::pipe: return prec::InclusiveOr;`). The levels are C's, the same as
chibicc's functions bitor, bitxor, bitand, equality, relational, shift, add, mul; chibicc (and
ours) writes one function per level and lets the call chain be the table, so adding a level is
adding a function and changing one call (02.04, 02.05), where clang adds a row.

### gcc's C parser (releases/gcc-15.2.0): operator precedence with an explicit stack

gcc/c/c-parser.cc, c_parser_binary_expression(). The grammar is in its comment, one rule a
level as in C11 6.5.5 to 6.5.14 (`additive-expression: multiplicative-expression
additive-expression + multiplicative-expression ...`), but the code is not a function per
level. In its own words: `A binary expression is parsed using operator-precedence parsing, with
the operands being cast expressions. All the binary operators are left-associative.` ... `which
we represent on a stack. On the stack, the precedence levels are strictly increasing.` A tighter
operator is pushed; `When a new operator is encountered with precedence less than or equal to
that at the top of the stack, triples E[i-1] op[i] E[i] are popped and replaced by the result
of the operation`. The stack is a local array, `stack[NUM_PRECS]`, so its depth is the number of
levels, not the length of the expression. So three parsers of one grammar: chibicc's (and ours)
recursion a function per level, clang's recursion a precedence number per call, gcc's no
recursion at all.

### What gcc writes at -O0 (riscv64-elf-gcc 15.2.0)

`riscv64-elf-gcc -O0 -march=rv64im -mabi=lp64 -ffreestanding -nostdlib -fno-builtin -mno-relax
-S` on `int main(void) { return 1 + 2 * 3; }`: the constant is folded even at -O0, and main has
a frame although it needs none.

    main:
        addi    sp,sp,-16
        sd      ra,8(sp)
        sd      s0,0(sp)
        addi    s0,sp,16
        li      a5,7
        mv      a0,a5
        ld      ra,8(sp)
        ld      s0,0(sp)
        addi    sp,sp,16
        jr      ra

The frame is the one the plan takes for module 04: s0 is the frame pointer, ra at 8(sp) which is
-8(s0), the caller's s0 at 0(sp) which is -16(s0). The same shape with variables, `int a = 1, b
= 2, c = 3; return a + b * c;`, keeps the order of the tree and the 32-bit instructions:

    li a5,1 / sw a5,-20(s0) / li a5,2 / sw a5,-24(s0) / li a5,3 / sw a5,-28(s0)
    lw a5,-24(s0) / mv a4,a5 / lw a5,-28(s0) / mulw a5,a4,a5 / sext.w a5,a5
    lw a4,-20(s0) / addw a5,a4,a5 / sext.w a5,a5 / mv a0,a5

Ours for `1+2*3` (02.03), every value 64 bits, no frame:

    li t0, 1 / li t1, 2 / li t2, 3 / mul t1, t1, t2 / add t0, t0, t1 / mv a0, t0 / ret

gcc at -O0 keeps each variable in memory and goes through a5 and a4; ours keeps the values in
registers as a stack. Its `mulw`, `addw` and `sext.w` are what 06.02 brings for int.

### QEMU's test device (v10.2.1)

hw/riscv/virt.c, the memory map: `[VIRT_TEST] = { 0x100000, 0x1000 },`, created by
`sifive_test_create(s->memmap[VIRT_TEST].base);`. hw/misc/sifive_test.c,
sifive_test_write(): a write at offset 0 is split, `int status = val64 & 0xffff;` and `int code
= (val64 >> 16) & 0xffff;`. include/hw/misc/sifive_test.h: `FINISHER_FAIL = 0x3333`,
`FINISHER_PASS = 0x5555`, `FINISHER_RESET = 0x7777`. FAIL calls
`qemu_system_shutdown_request_with_code(SHUTDOWN_CAUSE_GUEST_PANIC, code);`, PASS the same with
`SHUTDOWN_CAUSE_GUEST_SHUTDOWN` and the same code; RESET resets the machine. Any other value is
logged (`qemu_log_mask(LOG_GUEST_ERROR, ...`) and ignored. The ops accept
`.min_access_size = 2` to `.max_access_size = 4` bytes; start.S's `sw` is 4. Reads return 0.

Run on this machine (QEMU 10.2.1, a program that stores one word there and loops):

    word         QEMU's exit status
    0x3333       0      (FAIL with code 0 is still 0)
    0x75555      7      (PASS carries a code too)
    0x2a3333     42
    0x12345555   52     (code 0x1234; the OS keeps its low 8 bits, 0x34)
    0x1234       none   (not a command: QEMU runs on; killed after 2 s)

So the status reaches the shell either way: start.S's choice (0x5555 for 0, else (status << 16)
| 0x3333) only picks the shutdown cause QEMU records, guest shutdown or guest panic, which the
exit status does not show. `(status << 16) | 0x5555` for every status would do as well.
