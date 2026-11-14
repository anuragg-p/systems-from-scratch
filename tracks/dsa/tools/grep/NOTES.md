# grep (module 04): notes for the lesson writers

Everything here was run on the reference code: Apple M4 Pro, macOS 26.6.2,
Apple clang 21, the system's BSD grep 2.6.0-FreeBSD; and on Linux: Docker
debian:stable-slim (aarch64), gcc 14.2 (no warnings with -Werror), GNU grep
3.11, GNU Make 4.4.1. Times are the fastest of three runs on the Mac unless
a row says otherwise; a run past a time limit was killed and says so. Every
"break it" was run on the project as `./learn files dsa --at NN.LL` writes
it, with that one change made; outputs are pasted as they came.

## The tool

```
grep [-E|-F] [-ncvi] [--algo=NAME] [--cache=N] pattern [file ...]
```

- `-F` a fixed string (04.01); `-E` an extended regular expression, grep -E's
  dialect in the C locale (04.02). **Without either, ours reads the pattern
  as -E does**; the system's grep without -E reads a *basic* expression, where
  `( ) | + ?` stand for themselves. Lessons that compare must say `grep -E`.
- `-n -c -v -i`, in any combination and bundled (`-vc`). Several files: each
  line after `name:`, `(standard input)` for `-`. Exit 0 if a line was
  selected, 1 if not, 2 on trouble; a missing file prints `grep: x: No such
  file or directory`, the others are still searched, and the status is 2.
  All as BSD and GNU grep do.
- `--algo=`: with -F `scan` or `horspool`; with -E `backtrack` (04.02), `nfa`
  (04.03), `dfa` (04.04). The default is the last one built. A wrong one:
  `grep: no --algo 'scan' for a regular expression (have: backtrack, nfa, dfa)`.
- `--cache=N` (04.04): the most DFA states kept at once, 10000 by default.
- What it leaves out, each an ordinary error with status 2: `{2,3}`, `\w` and
  every other `\letter`, `[. .]` `[= =]`, `*` `+` `?` with nothing before them
  or after an anchor, a pattern with a newline in it. Not there at all: -e
  -w -x -o -r -l -h, basic regular expressions. `a{` (a brace not followed by
  a digit or comma) and a `)` with no `(` stand for themselves, as in both
  system greps.
- It reads each file whole into memory (the file's size, from fstat; a pipe
  in doubling blocks), then searches it. A regular expression is matched a
  line at a time; a fixed string is searched for in the whole text (below).

| file | lesson | what |
|---|---|---|
| lib/strsearch.c, .h | 04.01 | Search: scan and Horspool, with -i by a folding map |
| lib/re.c, .h | 04.02 | Re: the parser (a tree of nodes) and the backtracking matcher |
| lib/nfa.c, .h | 04.03 | Nfa: Thompson's construction, and the simulation by state lists |
| lib/dfa.c, .h | 04.04 | Dfa: DStates made from NFA state lists, found in a Table (01.02) |
| tools/grep/grep.c | 04.01 | the tool; @from blocks bring -E, the engines, --cache |
| tools/grep/tool.mk, gen.py | 04.01 | the build (LIB += and GREP_H += per lesson); inputs `runs`, `ab` |

The headers are re.h and strsearch.h, not regex.h and search.h: with -Ilib
those would hide the system's <regex.h> and <search.h> from every tool.

Before 04.02 there are no regular expressions: `printf 'one\n' | bin/grep
'o.e'` prints `grep: regular expressions are not supported: -F searches for
'o.e' as it is` (a pattern with none of `\ . [ ( ) * + ? { | ^ $` is searched
as a fixed string without -F), and `-E` is `grep: unknown option -E`.

## DS_STATS and DS_TRACE

`DS_STATS=1`, one line per structure, the tool's first:

```
stats: grep: bytes B, lines selected S
stats: search: positions P, examined E, skipped K        positions tried, text bytes compared,
                                                         positions passed over untried
stats: regex: nodes N                                    the tree's size
stats: backtrack: steps S, examined E, deepest D         nodes visited, bytes compared, deepest nesting
stats: nfa: states N, examined E, live L, peak P         machine states, bytes read, live states summed
                                                         over every byte (the work), most live at once
stats: dfa: examined E, hits H, misses M, states built B, flushes F
                                                         bytes read; transitions found in a state's
                                                         table / worked out from the NFA; states made;
                                                         times the cache was full and emptied
```

The DFA's hash table and arrays print their own `table:` and `array:` lines;
with --algo=dfa the nfa line shows the machine's states and zeros (the NFA
is built, never run). For -F, `positions + skipped` is every position the
string fits at, when it is not found.

`DS_TRACE=1` prints, on stderr, one line per step (made for small inputs):

```
trace: scan: at P: examined K, match | mismatch at J, shift 1
trace: horspool: at P: examined K, mismatch at J, 'c' under the last byte, shift S
trace: line: <the line>                                  (before each line, for -E)
trace: backtrack: start at I
trace: backtrack: at I: 'c' against R: yes|no             R: the part of the pattern
trace: backtrack: at I: the end against R: no
trace: backtrack: back at I: R, the other way
trace: nfa: state 3: R -> 4 | split -> 3, 5 | match      the machine, once
trace: nfa: start 0
trace: nfa: start: {1 3 5 6}                              live states before the first byte
trace: nfa: at I 'c': {1 3 5 6 7}                         and after each byte
trace: dfa: start: D0 (built: {2 3 4}) | (hit) | (found)
trace: dfa: at I 'c': D0 -> D1 (built: {2 3 4 5}) | (hit) | (found)
trace: dfa: cache full at N states: all thrown away
```

For -F, P is an offset in the whole input (the search runs over the text,
not line by line); for -E, I is an offset in the line. State lists show only
states that read a byte, the match state, and a `$` waiting for the end:
splits are followed, never kept.

## Checked against the system's grep, and where BSD and GNU differ

tests/tools/grep.py holds the table: 36 fixed strings (on the book and on
lib/*.[ch] tools/*/*.c together), 71 expressions on the book and 24 on the
source. Every one was run with each of 9 flag sets ([], -n, -c, -v, -i, -in,
-vc, -vn, -ic) through BSD grep and GNU grep, with every engine of ours: all
agree byte for byte, with the same status (1575 runs each way, with the
patterns below). The tests
run each pattern plain and with one flag set in turn, to stay quick.

Left out of the table because BSD and GNU grep disagree (ours does as GNU
does, except the first two rows, where it errors):

| pattern | BSD grep 2.6.0 | GNU grep 3.11 |
|---|---|---|
| `*a`, `^*` | error: repetition-operator operand invalid | `*` is a literal, with a warning |
| `a**`, `a+*`, `a*+`, `a?*` | the same error | a repeat of a repeat |
| `a+?` | a lazy `+`: the same lines as `a+` | `(a+)?`: every line |
| `a\|\|b`, `x\|`, `(\|x)`, `(a\|)` | error: empty (sub)expression | an empty side matches nothing at once |
| `-vc ''` (and -F) | prints 0 | prints nothing at all (but `-vc 'x*'` prints 0) |
| `a{1` | error: braces not balanced | literal |
| `\d` | something else (no match on "d") | "d", with a warning |

Both accept `()`, `[[.a.]]`, `[[=a=]]`; ours refuses the last two. Also found:
GNU grep stops at the first match when its output is /dev/null, so time it
with -c (bench/grow.py throws output away).

## 04.01 Searching for a string, and skipping ahead

Regions: search_init, search_scan, search_horspool (lib/strsearch.c);
next_fixed (grep.c). search_init folds the pattern with -i (a 256-byte map
is applied to every text byte compared) and fills Horspool's table: every
byte shifts the whole length m, a byte of the pattern other than its last
shifts m-1-i for its last place i. next_fixed searches the rest of the whole
text, newlines and all, and backs up from a match to the start of its line:
the lines between matches are never looked at, except with -v or -n
(grep_text walks them to print or number). That is the point of Haertel's
"why GNU grep is fast"; the pattern has no newline, so no match spans lines.

```
$ bin/grep -F -n 'Sherlock Holmes' data/book.txt | head -3
1:The Adventures of Sherlock Holmes
29:To Sherlock Holmes she is always _the_ woman. I have seldom heard him
747:Sherlock Holmes' succinct description, but the locality appeared to be
$ bin/grep -F -c 'Sherlock Holmes' data/book.txt
89
```

The book is 562404 bytes. DS_STATS (`-c`, so every match counts):

```
                        scan: positions  examined   horspool: positions  examined  skipped
'Sherlock Holmes' (15)            558060    560223               53466     58947   504594
'Holmes' (6)                      545318    548532              103727    111920   441591
'zzzzzzzzzzzzzzz' (15)            562390    562556               37502     37517   524888
```

Scan looks at each byte about once (1.004 a position: most fail at the first
byte); Horspool at a tenth of them for 15 bytes, a fifth for 6. The trace:

```
$ printf 'here is a needle in a haystack\n' | DS_TRACE=1 bin/grep -F --algo=horspool needle
trace: horspool: at 0: examined 1, mismatch at 5, 'i' under the last byte, shift 6
trace: horspool: at 6: examined 2, mismatch at 4, 'e' under the last byte, shift 3
trace: horspool: at 9: examined 1, mismatch at 5, 'l' under the last byte, shift 1
trace: horspool: at 10: examined 6, match
here is a needle in a haystack
```

(scan: positions 0 to 9 one byte each, then 6 at position 10.)

Measured, 'Sherlock Holmes' on `gen.py text 16384000` (93382612 bytes),
`grep -F -c`: scan 0.091 s, horspool 0.068 s, BSD grep 0.144 s; a string of
rare letters ('zzz...', 15): scan 0.090 s, horspool 0.032 s, BSD 0.098 s.
Both of ours grow as n (grow.py ratio 2.0). Reading the file is about 0.018 s
of that (a 200-byte string, which horspool all but skips: 0.018 s); the rest is the search: horspool examines 9.7 million bytes, scan
93.7 million. On ordinary text the obvious search never stops being usable:
the gain is a constant, about m, and it shows in bytes examined more than in
seconds.

Where one of them does stop: each has its own n*m input. On `--input runs`
(lines of 1000 a's), m = 100:

```
grow.py --input runs                 16000 lines (16 MB)   128000 lines (128 MB)
scan      aaa...ab (99 a's, b)       0.540 s               4.545 s     (100 bytes a position)
horspool  aaa...ab                   0.047 s               0.349 s     (1: 'b' first, shift 1)
scan      baa...a                    0.018 s               0.132 s     (1: 'b' first)
horspool  baa...a                    0.511 s               4.094 s     (100 bytes a position)
BSD grep -F aaa...ab                 5.785 s               -           (stopped at 16000)
BSD grep -F baa...a                  0.008 s               0.039 s
GNU grep -F (Linux) aaa...ab / baa...a   0.002 / 0.010 s   0.021 / 0.070 s
```

So macOS's own grep -F falls into scan's trap, ten times slower than our
scan and 120 times slower than our horspool on that input; GNU's does not.
The exact counts (the 04.01 test asserts them) on one line of 10000 a's:
scan on aa..ab 9902 positions, 990200 bytes examined; horspool 9902 and
9902; on baa..a scan 9902 and 9902, horspool 9902 and 990101.

Break it (put the pattern's last byte in the table too): in search_init,
`for (size_t i = 0; i + 1 < len; i++)` becomes `for (size_t i = 0; i < len;
i++)`. The last byte now shifts 0, and the search stops moving:

```
$ printf 'the cat sat on the mat\n' | DS_TRACE=1 bin/grep -F --algo=horspool 'cat on' 2>&1 | head -4
trace: horspool: at 0: examined 1, mismatch at 5, 'a' under the last byte, shift 4
trace: horspool: at 4: examined 1, mismatch at 5, 'a' under the last byte, shift 4
trace: horspool: at 8: examined 6, mismatch at 0, 'n' under the last byte, shift 0
trace: horspool: at 8: examined 6, mismatch at 0, 'n' under the last byte, shift 0
$ bin/grep -F -c Holmes data/book.txt
(still running after 20 s: killed)
```

A milder one (always shift the whole length: `size_t shift = s->shift[last];`
becomes `size_t shift = m;`; the compiler then warns that `last` is unused):
`bin/grep -F -c Holmes data/book.txt` prints 88, the system's grep 458;
`printf 'aaab\n' | bin/grep -F -c aab` prints 0; 'Sherlock Holmes' 7 of 89.

## 04.02 Parsing a regular expression

Regions: parse_class, parse_atom, parse_repeat, parse_cat, parse_alt,
re_parse, and the backtracker loop, go_on, bt, re_backtrack (lib/re.c);
next_regex (grep.c). One function per level of precedence, loosest first;
sequences nest to the left (`abc` is CAT(CAT(a, b), c)). Every byte-reading
node is RE_CHAR with a 256-bit set: a literal is a set of one (two with -i),
`.` all but newline, `[...]` its bytes, closed under case with -i before `^`
negates it (so `-i '[^a]'` matches neither a nor A, as both greps do).

The backtracker matches a node and then "what is left", a list of nodes on
the C stack (struct Next). At a choice it takes the first way (greedy) and
returns to try the other: that return is the backtracking. A loop entry
records where its last time round began; a time round that matched nothing
is not repeated, or `(a*)*` would go round for ever. It tries each start in
the line in turn. Its depth is limited to 10000 calls: past that, an
ordinary error, not a stack overflow (`a*b` on 30000 a's prints `grep: the
backtracking matcher is 10000 calls deep, on a line of 30000 bytes: more
than its stack can hold`, status 2; from 04.03 on, with `--algo=backtrack`,
the message ends `(--algo=nfa needs no stack)`, an `@from 04.03` block in
bt(); the timeline checks both).

```
$ printf 'colour\ncolor\ncolr\n' | bin/grep -E 'colou?r'
colour
color
$ printf 'x\n' | DS_STATS=1 bin/grep -E --algo=backtrack 'ab|c*'
x
stats: grep: bytes 2, lines selected 1
stats: regex: nodes 6
stats: backtrack: steps 5, examined 2, deepest 3
$ printf 'aa\n' | DS_TRACE=1 bin/grep -E --algo=backtrack 'a?a?aa'
trace: line: aa
trace: backtrack: start at 0
trace: backtrack: at 0: 'a' against a: yes
trace: backtrack: at 1: 'a' against a: yes
trace: backtrack: at 2: the end against a: no
trace: backtrack: back at 1: a?, the other way
trace: backtrack: at 1: 'a' against a: yes
trace: backtrack: at 2: the end against a: no
trace: backtrack: back at 0: a?, the other way
trace: backtrack: at 0: 'a' against a: yes
trace: backtrack: at 1: 'a' against a: yes
trace: backtrack: at 2: the end against a: no
trace: backtrack: back at 0: a?, the other way
trace: backtrack: at 0: 'a' against a: yes
trace: backtrack: at 1: 'a' against a: yes
aa
```

(`ab|c*` is ALT(CAT(a, b), STAR(c)): 6 nodes.) Errors, each status 2:
`(a` "'(' with no ')' after it"; `[a` "'[' with no ']' after it"; `a\` "a \
at the end of the pattern"; `[z-a]` "the range z-a goes backwards";
`[[:nope:]]` "no class [:nope:]"; `a{2}` "intervals such as {2,3} are not
supported"; `\w` "'\w' is not supported"; `[[.a.]]` "[. .] is not
supported"; `*a` "'*' with nothing before it to repeat"; `^*` "'*' after
'^': an anchor cannot be repeated".

Where it stops being usable: n optional a's then n a's, against n a's. The
match needs every a? to take nothing, which greedy tries last: about 2^n
ways first. Each two more a's, about 4.3 times the steps (the tests: 1804,
8208, 36884, 163864, 720924 steps for n = 8 to 16).

```
n    backtrack: steps      seconds     nfa: live  seconds   dfa: states  seconds
20          13631524         0.052          651     0.003            21    0.003
22          58720296         0.196          782     0.003            23    0.003
24         251658284         0.837          925     0.003            25    0.003
26        1073741872         3.412         1080     0.004            27    0.005
28        4563402804        14.992         1247     0.003            29    0.003
30       19327352888        62.406         1426     0.003            31    0.003
32       81604378684       259.758         1617     0.003            33    0.003
```

Seconds at 26, a minute at 30, four minutes at 32, for a 33-byte line.

A pattern someone would write, on the book itself: lines made only of
words and spaces, `^([A-Za-z]+ ?)*$`. A word of k letters can be split
between the `+` and the `*` in 2^(k-1) ways, and the ways multiply word by
word; a line that ends in punctuation fails only after trying all of them.
NFA and DFA: 3200 lines in a few milliseconds. The backtracker on the whole
book did not finish in 20 s; on 93 MB it was killed at 300 s (the DFA: 0.173
s; BSD grep 5.708 s). Single lines, `--algo=backtrack`:

```
line 29 "To Sherlock Holmes she is always _the_ woman. ..."         38923238 steps    0.134 s
line 30 "mention her under any other name. In his eyes ..."         32472699 steps    0.114 s
line 31 "predominates the whole of her sex. It was not ..."         74692819 steps    0.278 s
line 41 "throw a doubt upon all his mental results. Grit ..."      951534875 steps    3.208 s
line 57 "observation in following out those clues, and ..."       7914161342 steps   26.174 s
line 58 "mysteries which had been abandoned as hopeless by ..."   killed after 6 minutes of CPU
```

(Line numbers as `sed -n 41p data/book.txt` counts them.) The cost is
predictable: the letters before the first punctuation can be split into
pieces in 2^(letters - words) ways, and the backtracker takes about 14.5
steps a way, at about 300 million steps a second: line 41 has 34 letters in
8 words (2^26 ways, 14.2 steps each), line 57 35 in 6 (2^29, 14.7). Line 58
has 59 letters in 11 words before its full stop: 2^48 ways, about 4e15
steps, about 157 days. The NFA takes each of these lines in microseconds.

Ordinary patterns are fine for it, only slower: on 93 MB of text (`-c`),

```
                                    backtrack   nfa       dfa       BSD grep -E
Holmes|Watson                       2.899 s     0.556 s   0.216 s   1.105 s
[A-Z][a-z]+ [A-Z][a-z]+             1.183 s     0.413 s   0.226 s   2.231 s
(very|rather|quite) [a-z]+ly        5.027 s     0.897 s   0.231 s   1.682 s
^([A-Za-z]+ ?)*$                    > 300 s     0.716 s   0.173 s   5.708 s
```

Break it (no guard against a loop that matched nothing): in go_on, delete
`if (i == k->from)` and the `return` under it. Then:

```
$ printf 'aaab\naaac\n' | bin/grep -E '(a*)*b'
grep: the backtracking matcher is 10000 calls deep, on a line of 4 bytes: more than its stack can hold
$ printf 'xy\n' | bin/grep -E '(a|)*y'
grep: the backtracking matcher is 10000 calls deep, on a line of 2 bytes: more than its stack can hold
$ printf 'colour\n' | bin/grep -E 'colou?r'
colour
```

Patterns without a loop that can match nothing are untouched. Without the
depth limit this would be a crash (a stack overflow), not a message.

## 04.03 The pattern as a machine: an NFA

Regions: build, nfa_compile, nfa_add, nfa_match (lib/nfa.c). build is
Thompson's construction written backwards: it is given the state a node
leads to, and returns the state to start the node in, so a sequence builds
its right side first and no list of arrows to patch is needed. States are
numbered in pattern order all the same: size() counts each subtree's
states, so every node knows its range before it is built (one per byte and
anchor, one split per |, *, + and ?, and the match state last: 3n+1 for
a?^n a^n). nfa_add follows splits and anchors (a ^ only at the start, a $
only at the end, else kept waiting) and marks each state per list with a
generation number, so a state is on a list at most once and epsilon loops
end. nfa_match keeps two lists; after each byte it adds the start state
again (a match may start at any byte), and stops early on a match, or when
the list is empty (only ^-anchored patterns get there).

```
$ printf 'aaa\n' | DS_TRACE=1 DS_STATS=1 bin/grep -E --algo=nfa 'a?a?a?aaa'
trace: nfa: state 0: split -> 1, 2
trace: nfa: state 1: a -> 2
trace: nfa: state 2: split -> 3, 4
trace: nfa: state 3: a -> 4
trace: nfa: state 4: split -> 5, 6
trace: nfa: state 5: a -> 6
trace: nfa: state 6: a -> 7
trace: nfa: state 7: a -> 8
trace: nfa: state 8: a -> 9
trace: nfa: state 9: match
trace: nfa: start 0
trace: line: aaa
trace: nfa: start: {1 3 5 6}
trace: nfa: at 0 'a': {1 3 5 6 7}
trace: nfa: at 1 'a': {1 3 5 6 7 8}
trace: nfa: at 2 'a': {1 3 5 6 7 8 9}
aaa
stats: grep: bytes 4, lines selected 1
stats: regex: nodes 14
stats: nfa: states 10, examined 3, live 22, peak 7
```

and a machine with a loop, which never matches here:

```
$ printf 'abab\n' | DS_TRACE=1 bin/grep -E --algo=nfa '(a|b)*abb'
trace: nfa: state 0: split -> 1, 4
trace: nfa: state 1: split -> 2, 3
trace: nfa: state 2: a -> 0
trace: nfa: state 3: b -> 0
trace: nfa: state 4: a -> 5
trace: nfa: state 5: b -> 6
trace: nfa: state 6: b -> 7
trace: nfa: state 7: match
trace: nfa: start 0
trace: line: abab
trace: nfa: start: {2 3 4}
trace: nfa: at 0 'a': {2 3 4 5}
trace: nfa: at 1 'b': {2 3 4 6}
trace: nfa: at 2 'a': {2 3 4 5}
trace: nfa: at 3 'b': {2 3 4 6}
```

On a?^n a^n it reads n bytes; the work (live) grows as about 1.5 n^2, not
2^n: 651 at n = 20, 1617 at 32, 15251 at 100 (peak 201 of 301 states), 3 ms
each. At n = 20 the backtracker takes 13631524 steps against 651. On the
book: Holmes|Watson reads 533815 bytes with 1096291 live states in all, peak
3; `^([A-Za-z]+ ?)*$` 205421 bytes (the dead-list stop saves the rest),
peak 3 of 8 states. The 93 MB table is under 04.02.

Break it (do not add the start again after each byte: delete the line
`nfa_add(m, next, m->start, 0, i + 1 == n);` and its comment). Only matches
that start a line are found:

```
$ bin/grep -E -c --algo=nfa Holmes data/book.txt
42
$ grep -E -c Holmes data/book.txt
458
$ printf 'abab\n' | DS_TRACE=1 bin/grep -E --algo=nfa 'ba' 2>&1 | tail -2
trace: nfa: start: {0}
trace: nfa: at 0 'a': {}
```

## 04.04 Caching the states: a DFA built as it runs

Regions: flush, state_for, step, dfa_match (lib/dfa.c). A DState is a
sorted list of NFA states (the ones nfa_add keeps), a next[256] table, all
-1 until worked out, and two flags: the list holds the match state, and
"would match if the line ended here" (a waiting $ that leads to the match).
state_for sorts the list and looks its bytes up in a Table from 01.02 (the
key is the int array); a new set is built, unless the cache holds max
states already, when flush frees them all, empties the table and starts
again (the start state too). step works a transition out exactly as
nfa_match would, keeps it in the state's table unless a flush happened
meanwhile, and dfa_match is then one lookup a byte. The DFA is built from
the NFA: use_regex compiles the NFA for both. An empty line is checked on
the NFA directly (^ and $ both hold there; not worth a state). A state with
an empty list is dead: the line cannot match, stop reading.

```
$ printf 'xabb\nab\n' | DS_TRACE=1 DS_STATS=1 bin/grep -E --algo=dfa '(a|b)*abb' 2>&1 | grep -v 'nfa: state'
trace: nfa: start 0
trace: line: xabb
trace: dfa: start: D0 (built: {2 3 4})
trace: dfa: at 0 'x': D0 -> D0 (found)
trace: dfa: at 1 'a': D0 -> D1 (built: {2 3 4 5})
trace: dfa: at 2 'b': D1 -> D2 (built: {2 3 4 6})
trace: dfa: at 3 'b': D2 -> D3 (built: {2 3 4 7})
trace: line: ab
trace: dfa: start: D0 (hit)
trace: dfa: at 0 'a': D0 -> D1 (hit)
trace: dfa: at 1 'b': D1 -> D2 (hit)
xabb
stats: grep: bytes 8, lines selected 1
stats: regex: nodes 10
stats: nfa: states 8, examined 0, live 0, peak 0
stats: array: pushes 8, grows 2, moves 0
stats: table: lookups 9, probes 1, inserts 4, resizes 0, moves 0
stats: dfa: examined 6, hits 2, misses 4, states built 4, flushes 0
```

On the book (`-c`, the default --algo):

```
pattern                       lines   states built   bytes read     hits   misses
Holmes|Watson                   531             12       533815   533695      120
[A-Z][a-z]+ [A-Z][a-z]+         702              6       527392   527142      250
w[aeiou]+n                      498              4       534768   534639      129
^([A-Za-z]+ ?)*$               3200              3       205421   205315      106
```

On 93 MB the DFA is 1.8 to 4.1 times faster than the NFA and 5 to 22 times
faster than the backtracker (the table under 04.02), and 5 to 33 times
faster than BSD grep -E.

The cache filling: `(a|b)*a(a|b)^k$` (the a k+1 bytes from the end) needs a
state for every one of the last k+1 bytes there can be: 2^(k+1). On 200000
random lines of 40 a's and b's (`gen.py ab 200000`, 8.2 MB, `-c`):

```
k    nfa       dfa (--cache 10000)   states built   flushes   BSD grep -E
3    0.193 s   0.024 s                         16         0   0.313 s
6    0.273 s   0.024 s                        128         0   0.443 s
9    0.335 s   0.029 s                       1024         0   0.531 s
12   0.395 s   0.063 s                       8192         0   0.626 s
15   0.431 s   2.008 s                    5680555       568   0.689 s
20   0.489 s   2.499 s                    6141620       614   0.814 s
```

k = 12 with a smaller cache: --cache=1000 1.816 s (6434308 states built,
6434 flushes); --cache=100 1.805 s (7549148, 75491); --cache=10000 or
100000 0.063 s. When the states the text needs do not fit, nearly every
byte is a miss that also builds a state, and the DFA is four to five times
slower than the NFA it was built to beat; memory stays bounded either way
(at most N states of about 1 KB). RE2 counts its flushes and falls back to
the NFA when they come too often; ours does not (a "decide the boundary"
question). A flush, small:

```
$ printf 'ab\nba\nabba\n' | DS_TRACE=1 bin/grep -E --algo=dfa --cache=2 'a(a|b)$' 2>&1 | grep 'dfa:\|line:'
trace: line: ab
trace: dfa: start: D0 (built: {0})
trace: dfa: at 0 'a': D0 -> D1 (built: {0 2 3})
trace: dfa: cache full at 2 states: all thrown away
trace: dfa: at 1 'b': D1 -> D0 (built: {0 4})
trace: line: ba
trace: dfa: start: D1 (built: {0})
...
```

(prints `ab`; states built 9, flushes 4 over the three lines.)

Break it (do not keep a transition: in step, delete `if (st.flushes ==
flushes)` and the line under it; the compiler then warns that `flushes` is
unused, so delete `long flushes = st.flushes;` too). Every byte is worked
out again:

```
$ DS_STATS=1 bin/grep -E -c 'Holmes|Watson' data/book.txt
531
stats: table: lookups 533828, probes 533804, inserts 12, resizes 0, moves 0
stats: dfa: examined 533815, hits 0, misses 533815, states built 12, flushes 0
```

The same 12 states, found again in the table at every byte. On 93 MB:
1.734 s, against the NFA's 0.514 s and the real DFA's 0.197 s.

## The tests and the timeline

Each lesson's test runs its own engine through the table against the
system's grep, and asserts on counts, never on time: 04.01 the positions
and bytes above (exact, on a run of a's), 04.02 the steps growing about 4x
per two a's and the depth error, 04.03 n bytes and 3n+1 states for a?^n a^n
and backtracking taking over 10000 times the NFA's work at n = 20, 04.04 a
handful of states and over 99% hits on the book and the flushes. 04.02 to
04.04 also compare their engine with Python's re on random patterns of a
small grammar (`a b c . [..] [^..] ^ $`, sequences, `|`, `( )* + ?`), with
and without -i, and 04.04 with --cache=1. Times on the Mac: 1.6, 4.3, 2.0
and 2.0 s; on Linux 0.8, 1.7, 0.7 and 0.5 s. check-timeline types, at each
lesson, what grep can do then and the error for what comes next (`-E` at
04.01, `--algo=nfa` at 04.02, `--algo=dfa` and `--cache` at 04.03), the
backtracker's depth error word for word (naming --algo=nfa only from 04.03),
and compares -F and each engine so far with the system's grep on the book.
