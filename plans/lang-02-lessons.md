# lang track, chapter 2: design of the lessons and figures

The design the lesson writers and the art builders work from. It is decided.
Build it, and report where it did not survive the code or the page. Lessons
and figures are made in parallel by different agents, so the figure file names
and captions below are a contract: a lesson uses exactly these names and
captions; an art builder draws exactly these files.

Everything in `plans/lang-01-lessons.md` under "Rules for everyone", "How a
lesson is written" and "After the first read" holds here too. Read those
three sections first. What differs for chapter 2 is below.

## Sources of truth

- The code: `tracks/lang/` on master. The project at a lesson:
  `./learn run lang --at NN.LL` leaves it in `build/at/lang/NN.LL/`.
- `tracks/lang/NOTES.md`, the sections "Chapter 2, scanning", "Chapter 2,
  parsing" and "Chapter 2, joined": regions by lesson, real transcripts, the
  numbers a lesson quotes, break-its, what was read of flex, Bison, GCC and
  Russ Cox's article. A lesson states about another system only what is
  recorded there, or what its writer reads now and adds.
- `plans/lang.md`, "Chapter 2: the plan" and "Chapter 2 as built".
- Module folder: `tracks/lang/lessons/02-programming-language-syntax/`.

## Lesson titles

```
02.01 Tokens as regular expressions
02.02 A grammar, and the trees it derives
02.03 From an expression to an automaton that guesses
02.04 From guessing to knowing: the DFA
02.05 The smallest automaton
02.06 The scanner as an automaton in code
02.07 The scanner as a table and a driver
02.08 Lexical errors, and notes to the compiler
02.09 Recursive descent, from an LL(1) grammar
02.10 Writing a grammar a parser can use
02.11 Predict sets: which token chooses which production
02.12 A top-down parser as a table and a stack
02.13 Bottom-up: shift, reduce, and the states of a parse
02.14 A bottom-up parser as a table and a stack
02.15 Syntax errors: carrying on after a mistake
```

## What is particular to chapter 2

- The book's running example in this chapter is a small calculator language
  and one program for it (it reads two numbers and writes their sum and
  their average). The reader's language already is such a language and more.
  Every lesson shows the chapter's construction on the reader's own token
  file, grammars and programs: `syntax/mote.tokens`, `syntax/mote.bnf`,
  `syntax/mote-ll.bnf`, `programs/02/rect.mote`. Where the book walks its
  example, the lesson says "the book does this for its calculator language;
  here it is for yours", and gives the example or figure number with three or
  four words of what it is.
- The small examples (`digits.tokens`, `dots.tokens`, the `sum-*.bnf`
  grammars, `dangling.bnf`) are ours. A reader who wants the book's own
  expressions and grammars run by their tools types them from the book into
  a file in our notation; a lesson may say so, and shows none of them.
- Words. An NFA is "an automaton that guesses" on first use, then NFA. A DFA
  "one that never has to guess", then DFA. FIRST, FOLLOW, PREDICT and EPS
  keep the book's names, each defined in a sentence at first use in each
  lesson that uses it. "Epsilon" is "the empty string", written `''` in our
  files. A production is a production; "rule" is not used for it once 02.02
  has defined the word.
- Two tools are new, `re` and `gram`. A lesson shows a tool's whole output
  when it is under about 40 lines and its first lines and a count otherwise.
- Sections 2.3.5 (most of it) and 2.4 are on the book's companion site, not
  in the printed volume: 02.15 says so at its Read first.

## The map (figures/02.NN-map.svg, one per lesson)

One map for chapter 2, the same in every lesson: the front end of chapter 1
opened up, with the two tools beside it. 640 wide. The lesson's piece in the
accent colour, earlier pieces solid, later ones dashed and muted.

- Top row, the descriptions: `mote.tokens` on the left (02.01); `mote.bnf`
  (02.02) and `mote-ll.bnf` (02.09) on the right.
- Left column, the tool `re`, a frame with five boxes top to bottom:
  **expression** (02.01), **NFA** (02.03), **DFA** (02.04), **smallest DFA**
  (02.05), **all tokens in one** (02.06), and out of the bottom `tables`
  (02.07). `mote.tokens` feeds the top.
- Right column, the tool `gram`, a frame: **every tree** (02.02), **check**
  (02.10), **predict sets** (02.11) leading to `LL(1) table` (02.12), and
  **states** (02.13) leading to `SLR(1) table` (02.14). The two grammars
  feed the top.
- Middle column, inside a frame labelled `mote`, top to bottom: `the
  program's text`; a row of three scanners: **by hand** (solid from the
  start, labelled "chapter 1"), **nested cases** (02.06), **table driver**
  (02.07); `tokens`; a row of four parsers: **first** (solid from the start,
  "chapter 1"), **recursive descent** (02.09), **LL driver** (02.12), **LR
  driver** (02.14); **flatten** (02.09); `the tree of lesson 01.07`; then one
  muted box "the rest of chapter 1" (analysis, the walk, the code generator).
  `tables` enters the table driver from the left; the two parser tables
  enter their drivers from the right.
- Two thin boxes beside the scanners and the parsers: **every lexical
  error; pragmas** (02.08), and **recovery** (02.15, attached to recursive
  descent).
- 02.08 also lights a thin arrow from pragmas down to "the rest of chapter
  1" (they reach the improver and the code generator).

Nothing on the map names a function.

## What the book says, section by section (ours, for the writers)

- Opening and 2.1 (pages 43 to 45). Syntax is form, semantics is meaning (the
  example: the digits of a number against the quantity). Specifying syntax
  is one task, recognising it another. Tokens need three kinds of rule:
  putting side by side, choosing among alternatives, and repeating. The rest
  of syntax needs one more: recursion. Scanners and parsers can be made by
  tools from the descriptions (lex, yacc).
- 2.1.1 (45 to 48). Tokens: kinds, some with one spelling and some with
  many. Example 2.2: how many kinds of token C has. A regular expression is
  a character, the empty string, two expressions side by side, two with a
  bar, or one with a star. Example 2.3: the numbers a calculator accepts,
  written as named expressions that build on one another; nothing may be
  defined in terms of itself. Then character sets and layout: upper and
  lower case, free format against fixed columns, languages where line ends
  or indentation matter. Then other uses of regular expressions: grep,
  editors, scripting languages, with extensions that go beyond regular sets.
- 2.1.2 (48 to 50). Expressions cannot nest; a context-free grammar can,
  because a rule may use itself. Example 2.4: an expression grammar.
  Productions, nonterminals, terminals (the tokens), the start symbol. BNF,
  and EBNF with its star and brackets as shorthand (Example 2.5).
- 2.1.3 (50 to 53). A derivation replaces one nonterminal at a time until
  only tokens are left (Example 2.6, a right-most one). A parse tree is a
  derivation drawn. Example 2.7 and Figures 2.1 and 2.2: one string, two
  trees: the grammar is ambiguous. Example 2.8 and Figures 2.3 and 2.4: a
  better grammar, with precedence in how the rules build on each other and
  associativity in which side recurs.
- 2.2 (54 to 56). What a scanner does for the parser. Example 2.9: the
  tokens of the calculator language, with comments. Example 2.10 and Figure
  2.5: an ad hoc scanner, the simple cases first, peeking ahead, loops for
  long tokens; the longest possible token is taken. Production compilers
  often scan this way; while a language is being developed an explicit
  automaton made by a tool is better, because it can be made again when the
  tokens change. Example 2.11 and Figure 2.6: that automaton, drawn.
- 2.2.1 (56 to 62). Three steps from expressions to a scanner's automaton.
  First an NFA, an automaton that may have several moves on one character
  and moves on the empty string: Example 2.12 and Figure 2.7 give a small
  construction for each kind of expression, each keeping one start and one
  final state; Example 2.13 and Figure 2.8 build one for a number with a
  decimal point. Second a DFA, by letting each of its states stand for the
  set of states the NFA could be in (Example 2.14, Figure 2.9). Third the
  smallest DFA: start with the final states in one class and the rest in
  another, and split a class whenever some character sends its members to
  different classes (Example 2.15, Figure 2.10).
- 2.2.2 (61 to 65). The automaton as code: an outer case on the state, an
  inner one on the character (Example 2.16). Keywords are read as
  identifiers and then looked up. Sidebar 2.4: a scanner must say which
  token, so all the tokens' automata are joined under one new start state
  and their final states kept apart. Example 2.17: a token that can be
  extended by two more characters but not by one (in C, a number followed by
  dots) needs more than one character of look-ahead. Example 2.18: Fortran
  needed far more. The general answer: remember the last point where a token
  could have ended, and go back to it.
- 2.2.3 (65 to 67). The automaton as tables and a driver (Example 2.19,
  Figures 2.11 and 2.12): one table gives the next state for a state and a
  character, another the token a state may end; the driver remembers and
  goes back as above, drops white space and comments, and looks keywords up.
- 2.2.4 (65 to 67). A lexical error: throw the bad token away, skip to a
  character that can start a token, start again, and leave the rest to the
  parser. A scanner hands on a token's spelling as well as its kind; the
  spelling makes messages better.
- 2.2.5 (67 to 68). Pragmas: comments that mean something to the compiler.
  Directives (turn a check or an improvement on or off) and hints (this
  variable is used heavily). Those allowed anywhere are read by the scanner.
- 2.3 (69 to 73). Any grammar can be parsed in time that grows with the cube
  of the input; two classes can be parsed in linear time, LL (top-down,
  predictive) and LR (bottom-up, shift-reduce), set side by side in Figure
  2.13. Example 2.20 and Figure 2.14: one list parsed both ways. Example
  2.21 and Figure 2.15: a grammar that lets the bottom-up parser reduce as
  it goes, and that a top-down parser cannot use.
- 2.3.1 (73 to 79). Figure 2.16: the calculator language's LL(1) grammar,
  less natural than the one of Example 2.8 because the parser must choose
  before it has seen the operator. Example 2.23 and Figure 2.17: the
  recursive descent parser, a routine for each nonterminal and a `match`.
  Example 2.24 and Figure 2.18: a program and its parse tree; the calls trace
  the tree depth first. The hard part is which tokens label each arm: those
  that can start the right-hand side, and, if it can vanish, those that can
  come after.
- 2.3.2 (79 to 82). The two obstacles: left recursion (Example 2.25) and
  common prefixes (2.26), and how each is removed (2.27, 2.28). The dangling
  else (2.29, 2.30): the natural grammar is ambiguous. End markers remove
  the problem (2.31) and bring `elsif` (2.32).
- 2.3.3 (82 to 89). The table-driven top-down parser: a stack of what is
  still expected, and a table from the top nonterminal and the next token to
  a production (Figures 2.19 and 2.20); Example 2.34 and Figure 2.21 trace
  it. Then the sets the table is made from: FIRST, FOLLOW and PREDICT,
  worked out from obvious facts and repeated passes (Example 2.35, Figures
  2.22 to 2.24). A grammar is LL(1) when no two productions of one
  nonterminal share a predicting token. Sidebar 2.7: the driver's stack is
  not the call stack of recursive descent; one is what is to come, the other
  the way back to the root.
- 2.3.4 (89 to 101). Bottom-up: tokens are shifted onto a stack and a
  right-hand side on top is reduced to its left side; the stack holds what
  has been seen. Example 2.36: the stack and the input together are the
  right-most derivation backwards. Figure 2.25: the calculator's bottom-up
  grammar, left recursive. Example 2.38: LR items, a production with a dot;
  a state is a set of them, a basis and its closure. The states and their
  moves are a finite machine; LR(0), SLR and LALR share it and differ in how
  a state that could both shift and reduce is settled (SLR: reduce only on a
  token in FOLLOW of the left side). Figures 2.26 to 2.30: the states, the
  table, the driver and a trace. Examples 2.40 and 2.41: an empty
  right-hand side.
- 2.3.5 (102 to 103, the rest on the companion site). One syntax error a run
  is not acceptable. Panic mode: drop tokens to a safe one and back out to
  where it fits. Phrase-level: different safe tokens in different places.
- 2.4 and 2.5 (103 to 105). A scanner is a finite automaton, a parser one
  with a stack. The summary: generators against recognisers, top-down
  against bottom-up, by hand against by tool.

## The lessons

For each: Read first, what it makes real, the idea, Run it, How it works,
the boundary, Break it, Go deeper, figures. Read first lines end ", in
Programming Language Pragmatics, 4th edition."

### 02.01 Tokens as regular expressions

Read first: the opening of chapter 2, section 2.1 and section 2.1.1 (pages
43 to 48).

Makes real: Example 2.3 (definitions that build on one another and generate
a set of strings), for the reader's own tokens.

The idea: form against meaning in one case (the characters `1_000` against
the number). A token's spellings are a set, and three operations describe
it: side by side, either, repeated. `syntax/mote.tokens` is from now on the
law for what a token is. Two things to do with an expression: generate (how
the book reads one) and test a string against it by trying every way. New in
the language: a number may have single underscores between digits.

Run it: the sample (the first twelve numbers); `gen` on `name`; `match`
yes and no; `match --steps` on the bad case at three lengths (the counts
explode); `./mote --tokens` on `1_000_000` and on `1_x`.

How it works: an expression is a tree, and the star binds tightest; a name
is replaced by its definition, so a definition that reached itself would
never end: that is what "regular" forbids and lesson 02.02 allows; why
trying every way can take time that doubles with each character, which
lessons 02.03 to 02.05 cure.

Decide the boundary: tokens in a file a tool reads, or in the scanner's
code. Chapter 1's scanner is the second; the chapter builds the first and
keeps both.

Break it: in `scan.c` let an underscore continue a number whatever follows.
`1_x` is no longer a number and a name.

Go deeper: the book's 2.1.1, with its last part on other uses: try `grep
-E` with one of your expressions. Russ Cox, "Regular Expression Matching
Can Be Simple And Fast" (swtch.com/~rsc/regexp/regexp1.html).

Figures:
- `02.01-tree.svg` - "The definition of a number as a tree: side by side,
  repeated, and the names that stand for other definitions." The expression
  for `number` in `mote.tokens` drawn as the tree `re` builds.
- `02.01-generate.svg` - "Three numbers the definition generates, and the
  choices that make each." `7`, `42` and `1_000` under the expression, each
  with the times round each star marked.
- `02.01-steps.svg` - "Trying every way: the steps `match` takes on one bad
  case as the string grows." Bars for four lengths with the real counts.

### 02.02 A grammar, and the trees it derives

Read first: sections 2.1.2 and 2.1.3 (pages 48 to 53).

Makes real: Examples 2.4 to 2.8 and Figures 2.1 to 2.4: a derivation, two
trees for one string, and a grammar with precedence and associativity built
in.

The idea: a token cannot contain a token; an expression can contain an
expression. One more operation does it: a rule may use itself. Productions,
terminals (your tokens), nonterminals, the start symbol. A derivation; the
parse tree as the derivation drawn. `sum-ambiguous.bnf` gives `rate * hours
+ bonus` two trees, and they mean different sums. `sum.bnf` gives one:
precedence is which rule is built from which, associativity is which side a
rule recurs on. `syntax/mote.bnf` is the whole language written this way.

Run it: the sample (two trees); `gram show` on both small grammars; `trees`
with `sum.bnf` on `2 + 3 * 4` and `9 - 4 - 2`; `--leftmost`; `trees` with
`mote.bnf` on a statement.

How it works: the search tries every left-most derivation and gives one up
as soon as it cannot yield the string; one tree stands for many derivations
(the right-most and the left-most are the same tree read in two orders);
the braces of lesson 01.07's grammar against plain productions (Example
2.5's point).

Decide the boundary: precedence in the grammar, as here (the grammar grows a
level for each), or an ambiguous grammar and a table of precedences beside
it, which parser generators allow.

Break it: in `syntax/sum.bnf` make `expr` recur on its right. `9 - 4 - 2`
still has one tree, and it now means 7.

Go deeper: the book's 2.1.2 and 2.1.3 with `gram trees` open.
`[the cc track's lesson 02.04](/t/cc/02.04)`: C's whole table of precedence.

Figures:
- `02.02-derivation.svg` (stepped) - "A right-most derivation of `rate *
  hours + bonus`, a replacement a step, and the tree it draws." The
  sentential forms as `gram trees` prints them, the tree growing beside.
- `02.02-two-trees.svg` - "One string, two trees: the ambiguous grammar lets
  the multiplication or the addition come first." The two trees, each with
  what it would compute for 2, 3 and 4.
- `02.02-levels.svg` - "Precedence built into the grammar: `*` can only
  appear below `+`, because a term is made inside an expression." The one
  tree of `2 + 3 * 4` under `sum.bnf`, the levels banded.

### 02.03 From an expression to an automaton that guesses

Read first: section 2.2, and section 2.2.1 up to and including "From a
Regular Expression to an NFA" (pages 54 to 59).

Makes real: Example 2.9 (a language's tokens listed: `mote.tokens` is
yours); Example 2.10 (the ad hoc scanner: `scan.c` of chapter 1 is one, and
the lesson sets its shape against what the book describes: simple cases
first, a peek ahead, a loop for long tokens); Examples 2.12 and 2.13 (the
construction).

The idea: an automaton is states, a start, moves on characters, and final
states. A small construction for each of the five kinds of expression, glued
by moves on the empty string, turns any expression into one. It may have a
choice of moves: it guesses. To run it without guessing, keep the set of
states it could be in.

Run it: the sample (`digits.tokens`, the NFA of `number`); `re run` on
`1_000` (the sets after each character) and on `1_`; the bad case of 02.01
under `run`: the sets stay small where `match` took thousands of steps.

How it works: the three properties every piece keeps and why gluing is then
safe; following the empty moves after each character; the cost of a run is
the string's length times the number of states, never more.

Decide the boundary: run the NFA as sets every time, or turn it into a DFA
once (lesson 02.04): work on every character against work done before.

Break it: do not follow the empty moves after a character. `1_000` is
refused.

Go deeper: the book's 2.2.1, first part, and Figure 2.7 beside `re nfa` on
four one-line expressions. Cox's article again, for this construction's
history and its cost.

Figures:
- `02.03-pieces.svg` - "The five small automata every expression is made
  of: a character, the empty string, side by side, either, repeated." Each
  as `re nfa` prints it for a one-character example.
- `02.03-nfa.svg` - "The NFA of `digit digit* ( '_' digit digit* )*`,
  numbered as `re nfa` numbers it." The whole automaton.
- `02.03-run.svg` (stepped) - "The NFA on `1_0`: the states it could be in
  after each character." The automaton with the current set lit.

### 02.04 From guessing to knowing: the DFA

Read first: "From an NFA to a DFA" in section 2.2.1 (pages 60 and 61).

Makes real: Example 2.14 and Figure 2.9.

The idea: let one state of a new automaton stand for a set of the old one's
states. Start with the set the NFA can be in before any character; for each
set and each character work out the set that follows; a set seen before is
the same state. The new automaton never has a choice.

Run it: the sample (the DFA of `number`, each state with its set); the
counts of states, NFA against DFA; a string run through it, one state a
character.

How it works: the list of sets still to do, and why it ends; a state is
final when its set holds the NFA's final state; characters that every state
treats alike are one column; why the number of sets can in theory explode
and in a scanner does not.

Decide the boundary: make every state before the first character is read,
or make each the first time it is needed.

Break it: forget to mark a state final when its set holds the final state.
Nothing is accepted.

Go deeper: the book's Example 2.14 with `re dfa` beside Figure 2.9.

Figures:
- `02.04-sets.svg` - "Each state of the DFA is a set of the NFA's states:
  the NFA of lesson 02.03 with the sets drawn round them." 
- `02.04-dfa.svg` - "The DFA of a number: one move for each state and
  character, and no guessing."
- `02.04-build.svg` (stepped) - "Building the DFA: take a set and a
  character, find the set that follows, and add it if it is new."

### 02.05 The smallest automaton

Read first: "Minimizing the DFA" in section 2.2.1 (pages 60 to 62).

Makes real: Example 2.15 and Figure 2.10.

The idea: two states are the same if no string can tell them apart. Start
by telling apart only final from non-final; split a class whenever some
character sends two of its members to different classes; stop when nothing
splits.

Run it: the sample (the splits, then the result); the three counts for
`number`: NFA, DFA, smallest; the same strings accepted by all three.

How it works: why it ends; the invariant (states in different classes can
be told apart; a class is never joined to another); the result does not
depend on the order of splitting.

Decide the boundary: spend the time to make the automaton smallest, or keep
the first DFA: the size of a table against the time of a tool.

Break it: start with every state in one class. The result is one state,
and it accepts everything or nothing.

Go deeper: the book's Example 2.15 with `re min` beside Figure 2.10.

Figures:
- `02.05-split.svg` (stepped) - "Splitting: the classes of states after
  each split, and the character that forced it."
- `02.05-three.svg` - "One expression, three automata: the NFA, the DFA and
  the smallest DFA, with the number of states of each."

### 02.06 The scanner as an automaton in code

Read first: section 2.2.2 up to and including sidebar 2.4 (pages 61 to 63),
with Figure 2.6 (page 57) again.

Makes real: Figure 2.6 (the automaton for a language's tokens: `re scanner`
prints yours), sidebar 2.4 (all tokens in one automaton), Example 2.16 (the
automaton as nested cases).

The idea: a scanner must say which token it found, so one automaton holds
all of them, with its final states named. Then the automaton is written
down as code a person can read: an outer choice on the state, an inner one
on the character. A name is looked up among the keywords after it is found.

Run it: the sample (gcd's tokens by the new scanner); the same output as
chapter 1's scanner, byte for byte; `re scanner syntax/mote.tokens`, whole,
and its count of states; the automaton in the comment at the top of
`scan_cases.c` is that output.

How it works: one new start state with an empty move to each token's
automaton, the final states kept apart; where two tokens end in one state
the one defined first wins; the splitting starts from a class a token; in
the code a state's cases are that state's row; the two places the code is
not a pure automaton: keywords, and looking two characters ahead at an
underscore.

Decide the boundary: three scanners now exist for one language: by hand as
it came (shortest, the definition spread through it), by hand from the
automaton (longer, checkable line by line against the tool), and lesson
02.07's tables.

Break it: in `scan_cases.c` send `<` followed by `=` to the wrong state.
The two scanners no longer print the same tokens for `programs/sum.mote`.

Go deeper: the book's 2.2.2 and Figure 2.6. `[the cc track's lesson
01.02](/t/cc/01.02)` on the longest match.

Figures:
- `02.06-automaton.svg` - "One automaton for all of your language's tokens,
  each final state named for its token." Drawn from `re scanner`.
- `02.06-joined.svg` - "How the tokens' automata are joined: a new start
  state, a move on the empty string to each, and their final states kept
  apart."
- `02.06-cases.svg` - "A state of the automaton and the `case` that is that
  state: each arrow is a line of code." One state with two or three moves,
  beside its code.

### 02.07 The scanner as a table and a driver

Read first: the rest of section 2.2.2, from the paragraph on keywords, and
section 2.2.3 (pages 63 to 67).

Makes real: Example 2.17 (a token that needs more than one character of
look-ahead: `1_x` in your language), Example 2.19 and Figures 2.11 and 2.12
(the tables and the driver).

The idea: the automaton as data. `re tables` writes it as C; a driver that
knows nothing about any language walks it. When the driver can go no
further it goes back to the last place a token could have ended. Change
`mote.tokens`, run `make`, and the scanner is a new one.

Run it: the sample; the three scanners agree on every program; `re tokens
syntax/dots.tokens '3..5' --trace` and `'3.5'`: the going back, seen; the
size of the tables, characters against classes; add an operator to
`mote.tokens` in a copy and scan with it.

How it works: characters the automaton treats alike share a column;
remembering the last final state and the place; keywords in a table beside
the automaton; flex does both of the first two (as NOTES.md records).

Decide the boundary: a scanner made by a tool from a file, or written by
hand. The book's own verdict: by tool while the language is changing, often
by hand once it has settled.

Break it: do not remember the last final state. `1_x` is an error under
`--scanner=table` and still two tokens under `--scanner=cases`.

Go deeper: the book's 2.2.3 with Figure 2.12 beside the table for your
tokens. The flex manual (the page the writer fetches and cites).

Figures:
- `02.07-table.svg` - "The scanner's table for your language: a row a
  state, a column a class of characters, and the token each state can end."
- `02.07-back.svg` (stepped) - "The driver on `3..5`: it reads past the 3
  hoping for a longer token, cannot go on, and goes back to where a token
  last ended." From `re tokens --trace`.
- `02.07-make.svg` - "From `mote.tokens` to a scanner: what `make` runs
  again when the file changes."

### 02.08 Lexical errors, and notes to the compiler

Read first: sections 2.2.4 and 2.2.5 (pages 65 to 68).

Makes real: the four steps of 2.2.4, and both kinds of pragma of 2.2.5.

The idea: a compiler that stops at the first bad character makes its user
run it once for each. Report, drop characters up to one that can start a
token, go on. And a pragma: a comment the compiler reads. `#! register x` is
a hint (the improver of 01.11 may use it); `#! checks off` is a directive
(the code generator of 01.10 obeys it). A correct program prints the same
either way.

Run it: the sample (the pragmas of `hint.mote`); a file with three bad
places: three messages and status 1; `-S -O` with and without the register
pragma; the listing with `#! checks off`; an unknown pragma: a warning and
nothing else; `mote0` runs a chapter 1 program that has a pragma in it,
because to it the line is a comment.

How it works: where scanning starts again and why a run of bad characters
is one error; pragmas are found by the scanner because they may stand
wherever a comment may; a hint can be ignored, a directive cannot, and the
invariant both keep (a valid program's output does not change), which
`agree` holds.

Decide the boundary: a pragma as a comment, which old tools pass over, or
as syntax the parser checks.

Break it: on an error drop one character only. A run of three bad
characters is three messages.

Go deeper: the book's 2.2.4 and 2.2.5.

Figures:
- `02.08-recover.svg` (stepped) - "A bad character: reported, the run of
  them dropped, and scanning started again at the next character that can
  begin a token."
- `02.08-pragmas.svg` - "Two pragmas and the two parts of the compiler they
  reach: a hint to the improver, a directive to the code generator." The
  lines of `hint.mote`, arrows to the two phases, and the line of the
  listing each changes.

### 02.09 Recursive descent, from an LL(1) grammar

Read first: section 2.3 and section 2.3.1 (pages 69 to 79).

Makes real: Figure 2.16 (an LL(1) grammar: `mote-ll.bnf`), Example 2.23 and
Figure 2.17 (the parser: `descent.c`), Example 2.24 and Figure 2.18 (a
program and its tree: `rect.mote`).

The idea: a top-down parser starts at the root and, at each nonterminal,
must choose a production from the next token alone. So the grammar is bent
until one token is enough: the tails. A routine for each nonterminal; in
each, an arm for each production, labelled with the tokens that predict it;
`match` takes a token. Chapter 1's parser did the same with loops where
this one has tail routines. The tree it builds has the tails in it;
`flatten` takes them out and gives the tree of lesson 01.07.

Run it: the sample (the raw tree of `rect.mote`); the count of nodes, raw
against flattened; `--parse-tree` from `--parser=first` and from
`--parser=rd` is the same; an error, at the same place with the same words.

How it works: how an arm's labels are found by hand (the tokens that can
start the right-hand side; and if it can vanish, the tokens that can come
after), worked for `term_tail`; the calls are a walk of the tree, depth
first; what `flatten` splices and why the result is 01.07's tree.

Decide the boundary: a parser written by hand, as GCC's C parser has been
since 4.1 (NOTES.md records the release note), or one made by a tool; and,
by hand, loops or tails: the same parser written two ways.

Break it: take a token out of the labels of `term_tail`'s empty arm. A
correct program is refused.

Go deeper: the book's 2.3.1 with Figure 2.17 beside `descent.c`.
`[the cc track's lesson 02.01](/t/cc/02.01)`.

Figures:
- `02.09-two-grammars.svg` - "The rules for an expression twice: as you
  would write them, and bent so that one token is enough to choose."
  `mote.bnf`'s lines beside `mote-ll.bnf`'s, joined.
- `02.09-descent.svg` (stepped) - "The parser on `write 2 * (w + h)`: the
  routines running, the next token, and the tree as it grows, tails and
  all."
- `02.09-flatten.svg` - "The parser's own tree of `area := w * h`, and the
  tree after flatten: the same as lesson 01.07's."

### 02.10 Writing a grammar a parser can use

Read first: section 2.3.2 (pages 79 to 82).

Makes real: Examples 2.25 to 2.28 (the two obstacles and their removal),
2.29 and 2.30 (the dangling else, as two trees), 2.31 and 2.32 (end
markers, and `elsif`).

The idea: two things stop a top-down parser: a rule that begins with itself,
and two productions that begin alike. `gram check` finds both in the
natural grammar, and `mote-ll.bnf` is what removing them gives. Then a
choice in the design of a language: an `else` with no end marker can belong
to two `if`s, and `dangling.bnf` shows the two trees. Your language closes
every `if` with `end`, so it has one tree, and pays with rows of `end`s;
`elsif` is the usual cure, and the language gets it here.

Run it: the sample (`gram check` on `mote.bnf`); `gram check` on
`mote-ll.bnf` (nothing); `gram trees` on `dangling.bnf`: two;
`programs/02/sign.mote` run; its `--tree`: an `if` inside an `else`; the
first interpreter refuses it.

How it works: why a rule that begins with itself sends a routine into
itself for ever; the tail as the same language turned round; `elsif`
changes the grammars, the parser and analysis, and nothing after, because
the syntax tree is the one a nested `if` gives.

Decide the boundary: an end marker on every block, a rule that the nearest
`if` wins, or indentation: three languages' answers to one ambiguity.

Break it: in `syntax/mote-ll.bnf` write `expr` left recursive again. `gram
check` names the production.

Go deeper: the book's 2.3.2.

Figures:
- `02.10-dangling.svg` - "One statement, two trees: without an end marker
  the `else` can belong to either `if`."
- `02.10-recursion.svg` - "A rule that begins with itself, the routine it
  would be, and the tail that says the same thing a parser can follow."
- `02.10-elsif.svg` - "Three tests with `end` on every `if`, and with
  `elsif`: two spellings, one syntax tree."

### 02.11 Predict sets: which token chooses which production

Read first: section 2.3.3, whole (pages 82 to 89). This lesson builds its
second half, the sets; lesson 02.12 builds the table and the driver from
them.

Makes real: Example 2.35 and Figures 2.22 to 2.24.

The idea: what lesson 02.09 worked out by hand for each arm, computed.
Whether a symbol can vanish; FIRST, the tokens that can start it; FOLLOW,
the tokens that can come after it; PREDICT of a production: the FIRST of
its right-hand side, and the FOLLOW of its left side if the right can
vanish. Found by going over the grammar again and again until a pass adds
nothing. A grammar is LL(1) when no two productions of a nonterminal share
a predicting token.

Run it: the sample (`gram sets` on `mote-ll.bnf`: its first lines, and "no
conflict"); the PREDICT sets of `term_tail`'s two productions beside the
two arms in `descent.c`; `gram sets` on `mote.bnf`: the conflicts, named.

How it works: the facts one pass can see and the ones that need another;
why it ends; where FOLLOW flows from (what stands after a symbol, and the
FOLLOW of the rule it ends).

Decide the boundary: one token of look-ahead, or more: a larger class of
grammars for a larger table.

Break it: make one pass only. `gram sets` reports smaller sets, and names a
token missing from FOLLOW of `factor`.

Go deeper: the book's Example 2.35 with Figure 2.23 beside `gram sets`.

Figures:
- `02.11-where-from.svg` - "Where the FIRST and the FOLLOW of `term_tail`
  come from: each token traced to the production that puts it there."
- `02.11-passes.svg` (stepped) - "The sets growing, a pass a step, until a
  pass adds nothing."
- `02.11-arms.svg` - "The PREDICT sets of two productions, and the two arms
  of the routine written by hand in lesson 02.09: the same tokens."

### 02.12 A top-down parser as a table and a stack

Read first: section 2.3.3 again, up to and including Example 2.34, and
sidebar 2.7 (pages 82 to 86).

Makes real: Example 2.33 and Figures 2.19 and 2.20 (the driver and its
table), Example 2.34 and Figure 2.21 (the trace), sidebar 2.7.

The idea: the predict sets laid out as a table, and a driver with a stack
of what it still expects to see. A token on top is matched; a nonterminal
on top is replaced by the production the table names. The same parse as
recursive descent, with the grammar as data.

Run it: the sample (the trace of `rect.mote`: its first lines and its count
of steps); `gram lltable` and its size; the same tree as `--parser=rd`;
`gram ll` on `sum-right.bnf`.

How it works: a right-hand side is pushed last symbol first; the stack is
what is to come, not the way back: set against the routines running in
`descent.c` at the same token (sidebar 2.7's point); the tree is made as
productions are predicted.

Decide the boundary: the grammar as a table (change the file, run `make`)
or as code (better messages, room for special cases).

Break it: push a right-hand side first symbol first. The first statement
of a correct program is refused.

Go deeper: the book's Figure 2.21 beside your trace.

Figures:
- `02.12-table.svg` - "The LL(1) table of your language: for the
  nonterminal on top of the stack and the next token, the production to
  use."
- `02.12-stack.svg` (stepped) - "The driver on `read w`: the stack, the
  input and the step, as `--trace` prints them."
- `02.12-two-stacks.svg` - "The same moment in two parsers: recursive
  descent's stack is the way back to the root; the driver's is what is
  still to come."

### 02.13 Bottom-up: shift, reduce, and the states of a parse

Read first: section 2.3.4 up to "Bottom-Up Parsing Tables" (pages 89 to
94), with Examples 2.20 and 2.21 in section 2.3 (pages 70 to 73) again.

Makes real: Examples 2.20 and 2.21 and Figures 2.14 and 2.15 (one list
parsed both ways, and the grammar that lets a bottom-up parser reduce as it
goes), Example 2.36 (the derivation backwards), Figure 2.25 (a bottom-up
grammar: `mote.bnf`), Example 2.38 (items and states).

The idea: a bottom-up parser never predicts. It shifts tokens onto a stack
and, when the top of the stack is a whole right-hand side, reduces it to
its left side. `1 + 2 + 3` by hand under `sum-left.bnf` and under
`sum-right.bnf`: the first reduces as it goes, the second must shift
everything first. To know when a right-hand side is complete the parser
keeps a state: a set of productions each with a dot showing how far along
it could be. `gram items` builds every state.

Run it: the sample (the states of `sum-left.bnf`, whole); the number of
states of `mote.bnf`; one state of it read line by line.

How it works: the basis and the closure; moving the dot over a symbol gives
the next state, and a set seen before is the same state (lesson 02.04's
idea, on grammar symbols); the stack's symbols and the rest of the input
are a line of the right-most derivation, read backwards.

Decide the boundary: what to do in a state that could shift or reduce:
nothing (LR(0)), look at FOLLOW (SLR, lesson 02.14), look at what can
follow in this state (LALR, Bison's default as NOTES.md records), or split
states (full LR).

Break it: add the closure one level deep only. State 0 of `mote.bnf` loses
items; show which.

Go deeper: the book's Example 2.38 with `gram items` beside it.

Figures:
- `02.13-by-hand.svg` (stepped) - "`1 + 2 + 3` bottom-up under the
  left-recursive grammar: the stack, the input, and each shift or reduce."
- `02.13-state.svg` - "A state: the productions the parser could be in the
  middle of, the dot in each, and where each symbol leads."
- `02.13-machine.svg` - "Every state of `sum-left.bnf` and the moves
  between them."

### 02.14 A bottom-up parser as a table and a stack

Read first: the rest of section 2.3.4, from "Bottom-Up Parsing Tables"
(pages 95 to 101).

Makes real: Example 2.39 and Figures 2.26 to 2.30 (the states, the table,
the driver, a trace), Examples 2.40 and 2.41 (an empty right-hand side).

The idea: the states as a table: for a state and a symbol, shift, reduce,
go to, or accept. A reduction is allowed only on a token in FOLLOW of the
production's left side: that is all "SLR" adds. A driver with a stack of
states. The fourth parser, and the same tree again.

Run it: the sample (the trace of `rect.mote`); `gram slrtable` on
`sum-left.bnf`, whole; on `mote.bnf`: states, entries, no conflict; the
four parsers print one tree; `gram lr --trace` on a sum of ten numbers under
each sum grammar: the deepest the stack gets.

How it works: after a reduction the driver uncovers the state it was in
when the right-hand side began and goes to a new one on the left side (the
book says the left side is pushed back on the input and shifted: the same
step in other words); the book's tables also fold a state with one finished
item into the shift that reaches it, which these do not; an empty statement
list is a reduction of nothing, on the end of the input.

Decide the boundary: which grammar would you rather write, `mote.bnf` or
`mote-ll.bnf`, and which parser would you rather read?

Break it: allow a reduction on any token. `gram slrtable` reports
conflicts, and `make` stops.

Go deeper: the book's Figure 2.30 beside your trace. The Bison manual (the
pages NOTES.md records).

Figures:
- `02.14-table.svg` - "The SLR(1) table of `sum-left.bnf`: shift, reduce,
  go to, accept."
- `02.14-parse.svg` (stepped) - "The driver on `1 + 2 + 3`: the stack of
  states, the input and the step."
- `02.14-depth.svg` - "How deep the stack gets on a sum of ten numbers:
  left recursion reduces as it goes; right recursion must hold all ten."
  Two lines of measured depth over the steps.

### 02.15 Syntax errors: carrying on after a mistake

Read first: section 2.3.5, then sections 2.4 and 2.5 (pages 102 to 105).
Most of 2.3.5 and of 2.4 is on the book's companion site, not in the
printed volume.

Makes real: Example 2.42 (an error found at one token), panic mode and
phrase-level recovery.

The idea: report the error, drop tokens up to one where parsing can
sensibly start again, and go on, so that one run finds every broken
statement. Which tokens are safe depends on where the parser is: inside a
block `end`, `else` and `elsif` end the search; at the top only the end of
the file does. Nothing is run or generated after an error.

Run it: the sample (`broken.mote`: three messages); the same file under
`--parser=ll`: one; a file with a bad character and a bad statement: both
reported; a missing `end`.

How it works: how the hand-written parser gets back to the list of
statements it was reading; one message for one broken statement; the
table-driven parsers stop at the first error, and what the book says it
takes to do better.

Decide the boundary: stop at the first error (simple, and never wrong about
what follows) or recover (more found in a run, at the risk of errors that
are only echoes). Bison's `error` token is the same idea in a table (as
NOTES.md records).

Break it: inside a block, treat only the end of the file as safe. An error
in a loop hides the errors after it.

How it works ends with `### The chapter, whole`: three scanners and four
parsers, every pair giving one tree, and `agree`'s last line saying so;
what was made by hand and what by tool; section 2.5 is the page to read
last; chapter 3 leaves syntax for what names mean.

Go deeper: the book's 2.3.5 and its summary, 2.5.

Figures:
- `02.15-recover.svg` (stepped) - "A broken statement: the error is
  reported, tokens are dropped up to one that can start a statement, and
  parsing goes on."
- `02.15-safe.svg` - "The same stray token in two places: which tokens are
  safe to start again at depends on where the parser is."
- `02.15-front-ends.svg` - "Three scanners, four parsers, one tree: every
  pairing of chapter 2's front ends on one program."
