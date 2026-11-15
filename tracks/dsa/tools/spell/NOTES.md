# spell (module 05): notes for the lesson writers

Everything here was run on the reference code: Apple M4 Pro, macOS 26.6.2,
Apple clang 21, GNU Make 3.81, the system's BSD tools; and checked on
Linux: Debian 13.7 in Docker (aarch64), gcc 14.2, GNU coreutils, once with
look installed and once without (bin/look stands in). Every "break it" was
run on the project as `./learn files dsa --at NN.LL` writes it, with that
one change made. Times are the fastest of three runs, or bench/grow.py's.

Make 3.81 compares times to the second: after an edit made within a second
of the last build, `make` may relink nothing. A break-it replay should
`rm -rf build bin` (or wait a second) before `make`.

## The tool

```
spell [option ...] [file ...]       the unknown words of the text, one to a line
spell [option ...] -p PREFIX        the dictionary's words that start with PREFIX
spell -s [option ...] [file ...]    each unknown word and the nearest words   (05.03)
spell --distance WORD WORD          the edit distance                         (05.03)
```

- A word of the text is a run of A-Za-z, lowercased (freq's rule). Words
  of one letter are not checked: the dictionary has none ("a" and "I" are
  not in it), and the "s" and "t" of "Holmes's" and "don't" are not words.
  aspell skips words of one letter by default too.
- Output: each unknown word once, in byte order: what `tr -cs A-Za-z '\n' |
  tr A-Z a-z | grep .. | sort -u | comm -23 - tools/spell/words.txt`
  prints (LC_ALL=C). Exit 0. `-p`: exit 1 when nothing starts with the
  prefix (as look). Errors: status 2, "spell: ...".
- The dictionary: `tools/spell/words.txt` (relative: run from the
  project's directory), or `-d FILE` (repeatable). Lines are lowercased; a
  line with anything but letters is left out (so /usr/share/dict/words
  works: `-d /usr/share/dict/words`).
- Options by lesson:
  - 05.01: `-d`, `-p`, `--algo=list|table|trie` (trie the default).
  - 05.02: `--algo=bloom`, `--fp=P` (default 0.01), `--hashes=K`.
  - 05.03: `-s`, `-e N` (most edits, 1 to 3, default 2), `-n N` (most
    suggestions, default 5, 0 all), `--near=scan|trie`, `--distance A B`.
- Before its lesson an option is an ordinary error: at 05.01 `spell:
  no --algo 'bloom' (have: list, table, trie)` and `spell: unknown option
  '-s'`; at 05.02 still `spell: unknown option '-s'`.
- `-s` prints `word: near near ...`: the words at the smallest distance
  found, if it is at most -e, in byte order, at most -n. No word that
  near: `word:` and nothing after it.

## Files

```
lib/trie.c, trie.h     05.01   the trie (05.03 adds trie_near, the suggestion walk)
lib/bloom.c, bloom.h   05.02   the Bloom filter
lib/edit.c, edit.h     05.03   the edit distance, a row at a time
tools/spell/spell.c    05.01   the tool
tools/spell/tool.mk    05.01   LIB += and SPELL_H += lines marked @from 05.02 / 05.03; links -lm
tools/spell/words.txt  05.01   12dicts' 2of4brif list, 60388 words, 563527 bytes, public domain
tools/spell/NOTICE.txt 05.01   where it came from, its licence as read, its hashes
tools/spell/gen.py     05.03   gen.py's kind "typos" (book words, one in ten with a typo)
```

The list is in tools/spell/, not data/: no later tool needs a dictionary.

Regions (what each lesson writes):

- 05.01: trie_init, trie_add, descend, walk (lib/trie.c); list_has,
  complete_scan, complete_trie, check (spell.c).
- 05.02: bloom_init, place, bloom_add, bloom_test (lib/bloom.c).
- 05.03: edit_next_row, edit_distance (lib/edit.c); near_walk, trie_near
  (lib/trie.c); near_scan, suggest (spell.c).

## DS_STATS and DS_TRACE

```
stats: spell: words W, checked C, unknown U, dict words D, dict text T, dict bytes B, scanned S
stats: trie: words W, nodes N, bytes B, nodes visited V
stats: bloom: keys N, bits M, hashes K, bytes B, bits set S, bits tested T, bits on O
stats: edit: distances D, rows R, cells filled C
```

spell's own line comes first. "dict text" is the list as text (a byte a
letter, one a newline: the file's size for a clean file); "dict bytes" is
what the structure holding the dictionary takes by its own count (the
blocks it asked for, room to spare included, not malloc's own overhead).
"scanned" counts dictionary words looked at one by one (list lookups, -p
without a trie). The trie's "nodes visited" counts steps of lookups, -p
walks and suggestion walks, not adds. The table's line is lib/table.c's.

DS_TRACE=1 prints one line a step on stderr (formats in each file's
header):

```
$ printf 'cab\n' | DS_TRACE=1 bin/spell -d small.txt        (small.txt: car cart cat)
trace: trie: add "car": c -> 1 new
trace: trie: add "car": a -> 2 new
trace: trie: add "car": r -> 3 new, a word
trace: trie: add "cart": c -> 1
trace: trie: add "cart": a -> 2
trace: trie: add "cart": r -> 3
trace: trie: add "cart": t -> 4 new, a word
trace: trie: add "cat": c -> 1
trace: trie: add "cat": a -> 2
trace: trie: add "cat": t -> 5 new, a word
trace: trie: has "cab": c -> 1
trace: trie: has "cab": a -> 2
trace: trie: has "cab": b -> none
trace: trie: has "cab": no
cab
$ DS_TRACE=1 bin/spell -d small.txt -p ca      (after the adds)
trace: trie: find "ca": c -> 1
trace: trie: find "ca": a -> 2
trace: trie: each "car" -> 3, a word
trace: trie: each "cart" -> 4, a word
trace: trie: each "cat" -> 5, a word
$ printf 'cat cot\n' | DS_TRACE=1 bin/spell --algo=bloom -d small4.txt   (car cart cat dog)
trace: bloom: add "car": 11 15 19 23 27 31 35
trace: bloom: add "cart": 18 4 31 17 3 30 16
trace: bloom: add "cat": 20 3 27 10 34 17 0
trace: bloom: add "dog": 4 30 15 0 26 11 37
trace: bloom: test "cat": 20 on, 3 on, 27 on, 10 on, 34 on, 17 on, 0 on: yes
trace: bloom: test "cot": 2 off: no
cot
```

(4 words at 1%: m = 39, the next prime 41, k = 7.) The edit table and the
suggestion walk are under 05.03 below. Node numbers are the order nodes
were made in, so a figure can draw the trie from the add lines alone.

## 05.01 A trie, and completing a prefix

The tool comes whole at 05.01 but for its regions. The obvious way is
`--algo=list`: the words in an Array (01.01), and each lookup compares the
word with every word in turn until one matches (all 60388 for a word that
is not there). The table (01.02) is there too, to answer "why not the hash
table?": lookups as fast as the trie's, but -p has to look at every word
and sort what matches, as the list does. The trie: nodes in one Array,
26 int32 children each (an index, not a pointer: the Array moves when it
grows), a mark where a word ends; 108 bytes a node.

```
$ bin/spell data/book.txt | wc -l
     615
$ bin/spell data/book.txt | head -5
aberdeen
accompli
acetones
acquirement
adler
$ bin/spell -p zygot
zygote
zygotes
$ DS_STATS=1 bin/spell data/book.txt > /dev/null
stats: spell: words 105885, checked 99572, unknown 615, dict words 60388, dict text 563527, dict bytes 28311552, scanned 0
stats: array: pushes 1076369, grows 33, moves 266272
stats: trie: words 60388, nodes 138676, bytes 28311552, nodes visited 417367
stats: sort: comparisons 31023, moves 35203
$ DS_STATS=1 bin/spell --algo=list data/book.txt > /dev/null
stats: spell: words 105885, checked 99572, unknown 615, dict words 60388, dict text 563527, dict bytes 1612103, scanned 3467112081
$ DS_STATS=1 bin/spell --algo=table data/book.txt > /dev/null
stats: table: lookups 159960, probes 177900, inserts 60388, resizes 6, moves 64512
```

Most of the 615 are names (holmes is the most common unknown word: 462
times; then mr, sherlock, st, watson), contractions' first halves (didn,
ll, ve) and Victorian words. The list looks at 34820 words a lookup on
average (3.47 billion in all); the trie steps into 4.2 nodes a lookup.
lookups 159960 = 99572 checked + 60388 puts while loading.

Measured (book: best of three; grow.py: input text):

```
the book (105885 words)    list 4.04 s    table 0.02 s    trie 0.02 s
loading the dictionary     0.01 s each (the start of every run)

$ python3 bench/grow.py --limit 2 bin/spell --algo=list
        n       bytes   seconds  ratio
     1000        5260     0.055
     2000       10634     0.097    1.8
     4000       21395     0.184    1.9
     8000       42818     0.357    1.9
    16000       85604     0.709    2.0
    32000      171174     1.401    2.0
    64000      342492     2.844    2.0
growth: about n
$ python3 bench/grow.py --limit 2 --max 4194304 bin/spell
   ... 0.016 to 0.023 s up to 64000 words (the dictionary's loading), then
  1024000     5663824     0.143    1.8
  2048000    11346023     0.265    1.9
  4096000    22717280     0.504    1.9
```

Both are linear in the text: the list's cost is the words of the text
times the words of the dictionary, about 44 microseconds a word against
the trie's 0.12. The input that makes the list unusable is the book
itself (4 s); 4 million words would take it about 3 minutes, the trie half
a second. The table and the filter are as fast as the trie on lookups
(4096000 words: table 0.549 s, filter 0.489 s).

-p: the trie walks down the prefix, then every node below it; the list and
the table look at all 60388 words and sort the matches.

```
-p zygot   trie: nodes visited 7 (5 down, 2 below)     list: scanned 60388   2 words
-p qu      trie: nodes visited 649                     list: scanned 60388   291 words
```

Break it (a prefix is not a word): in trie_has, `int yes = node >= 0 &&
node_at(t, node)->word;` becomes `int yes = node >= 0;`. 63 of the book's
615 unknown words now pass, every one a start of a real word:

```
accompli ado agra blanche bohemia cal carlo carte christ chubb clair co cobb crewe de dr eg
employe en enigmatical esq est etc fain fait franco freemason fro german gras inst introspect
iv jem ku la ll marm membra oct paris parr partie passers pince pon pre prima rockies romper san
saxe scala shan st standi swash th typewrite un
```

(552 lines instead of 615.) Break it (children from z to a): in walk(),
`for (int c = 0; c < TRIE_LETTERS; c++)` becomes `for (int c =
TRIE_LETTERS - 1; c >= 0; c--)`. -p comes out backwards, each word still
before the longer words under it; look disagrees:

```
$ bin/spell -p quo | head -5          $ look quo tools/spell/words.txt | head -5
quoting                               quoit
quotient                              quoits
quotients                             quorate
quotidian                             quorum
quoth                                 quorums
```

The trie is big: 138676 nodes of 108 bytes is 15.0 MB, in a block of
262144 nodes (the Array doubles): 28.3 MB, 50 times the text. Most of
each node is children that are not there. That is 05.02's opening.

## 05.02 A Bloom filter: the dictionary in far less memory

bloom_init takes n (so spell reads the files twice: once to count, once
to add) and p, and sets m = n ln(1/p) / (ln 2)^2 rounded up to a prime,
and k = (m/n) ln 2. The k places of a key are (h1 + i h2) mod m with h1
and h2 the halves of its FNV-1a hash (01.03); m prime keeps the k places
different (a first version clamped m to at least 64: "cart" got the
places 15 31 47 63 15 31 47 63 ..., h2 mod 64 being 16). FNV-1a's halves
were good enough: the measured rates below match the formula with no
extra mixing.

Memory, each structure's own count (DS_STATS=1 bin/spell --algo=X /dev/null):

```
the list as text (the file)          563527 bytes    9.3 bytes a word
--algo=list   (Array + the words)   1612103          26.7
--algo=table  (entries, buckets,    3709255          61.4
               keys: lib/table.c)
--algo=trie                        28311552         468.8   (138676 nodes used of 262144)
--algo=bloom --fp=0.1                 36178           0.6   m 289417, k 3
--algo=bloom (0.01)                   72354           1.2   m 578827, k 7
--algo=bloom --fp=0.001              108532           1.8   m 868249, k 10
```

The filter at 1% is an eighth of the text and 1/391 of the trie. About
half its bits are on (299656 of 578827), as the best k makes them.

On the book, `--algo=bloom` prints 608 of the 615 unknown words; the 7
that got through: calcutta counterpaned freebody marseilles maudsley
monomaniac sarasate. It never prints a word that is in the dictionary.

The false-positive rate measured against the formula (1 - e^(-kn/m))^k,
on a million random strings of 2 to 10 letters that are not words:

```
--fp=0.1     m 289417   k 3    formula 0.100709   measured 0.100827
--fp=0.01    m 578827   k 7    formula 0.010039   measured 0.010001
--fp=0.001   m 868249   k 10   formula 0.001000   measured 0.001006
--fp=0.0001  m 1157669  k 13   formula 0.000100   measured 0.000103
```

and with m fixed (1%) and k changed, on 100000 of them: k=1 10.02% (the
formula 9.91%), 2 3.57 (3.55), 4 1.30 (1.36), 7 0.97 (1.00), 10 1.23
(1.30), 14 2.38 (2.48). Too few hashes leave too many bits telling;
too many fill the filter. A reader can measure it with the tools alone:
the unknown words of a big text are surely not words, so the filter's
list of them is short by its false positives:

```
$ python3 data/gen.py typos 1000000 > typos.txt
$ bin/spell typos.txt > unknown.txt; wc -l < unknown.txt
   36907
$ bin/spell --algo=bloom unknown.txt | wc -l      (--fp=0.1: 33184; --fp=0.001: 36860)
   36551
```

356 of 36907 got through: 0.96% (3723: 10.09%; 47: 0.13%).

What it cannot do, and how spell uses it: the filter holds no words, so
it cannot list them (`-p` with it is refused: "spell: a Bloom filter
holds no words to list: -p needs --algo=trie, table or list"), cannot say
which words are near one (05.03), and cannot remove one. In spell it
decides which words are unknown; -s (05.03) then reads the dictionary
again into a trie for the suggestions, the first time an unknown word
needs them, so a text with no unknown word never builds it (DS_STATS shows
no trie line). Unix spell made the same trade (McIlroy's paper, P-SPELL in
the outline's library; check its details before quoting them): hashes of
the words instead of the words, and a small chance, accepted, of letting a
misspelling through. Be honest that in a speller
the filter saves memory, not reads: most words of a text are in the
dictionary, so "certainly not" is the rare answer. The storage-engine use
(the outline's "guards the disk reads") is the other way round: most keys
asked for are absent there.

Break it (one place, k times): in place(), `return (h1 + (uint64_t)i * h2)
% b->m;` becomes `return h1 % b->m;`. Every key sets one bit k times:

```
before:  bits on 299656 (51.8%); 969 of 100000 non-words through; the book: 608 lines
after:   bits on 57316  (9.9%);  10024 of 100000 through;          the book: 557 lines
trace: bloom: add "car": 11 11 11 11 11 11 11
```

The same as `--hashes=1` without the code change: 10.02%.

## 05.03 Edit distance, and "did you mean"

The track's first dynamic programming (module 06's diff fills the same
kind of table). Levenshtein: insert, delete, replace, each 1; no
transposition, so "teh" to "the" is 2 and "recieve" finds "relieve" (1)
before "receive" (2). That is worth a sentence, and Damerau's extra case
is a good exercise. The table is filled a row at a time, keeping two rows:
`edit_distance` is `edit_first_row` and then `edit_next_row` per letter of
b, which is what lets the trie walk share rows between words.

```
$ bin/spell --distance kitten sitting
3
$ DS_TRACE=1 bin/spell --distance kitten sitting
trace: edit: "kitten" "sitting"
trace: edit: row 0 -: 0 1 2 3 4 5 6
trace: edit: row 1 s: 1 1 2 3 4 5 6
trace: edit: row 2 i: 2 2 1 2 3 4 5
trace: edit: row 3 t: 3 3 2 1 2 3 4
trace: edit: row 4 t: 4 4 3 2 1 2 3
trace: edit: row 5 i: 5 5 4 3 2 2 3
trace: edit: row 6 n: 6 6 5 4 3 3 2
trace: edit: row 7 g: 7 7 6 5 4 4 3
trace: edit: distance 3
3
$ printf 'speling recieve teh holmes quik accomodate seperate definately wierd\n' | bin/spell -s
accomodate: accommodate
definately: definitely
holmes: holes homes
quik: quick quid quin quip quirk
recieve: relieve
seperate: separate
speling: spelling spewing
teh: eh tea tech ted tee
wierd: wield
```

(Columns are a's letters, rows b's; in -s, a is the unknown word and b
the dictionary word.)

The slow way (`--near=scan`): the distance from the word to every word of
the dictionary. The walk (`--near=trie`, the default with a trie): down
the trie carrying one row; each child's row from its parent's and one
letter; a word reported where its row's last cell is within -e; a subtree
left out once no cell of its row is within -e (the smallest cell of a row
never goes down from one row to the next). Its trace, for "cst" with the
words car cart cat dog and -e 1:

```
trace: trie: near "c" -> 1: 1 0 1 2, min 0
trace: trie: near "ca" -> 2: 2 1 1 2, min 1
trace: trie: near "car" -> 3: 3 2 2 2, min 2, pruned
trace: trie: near "cat" -> 5: 3 2 2 1, min 1, a word at 1
trace: trie: near "d" -> 6: 1 1 2 3, min 1
trace: trie: near "do" -> 7: 2 2 2 3, min 2, pruned
cst: cat
```

("cart" and "dog" are never visited.) On the book, every unknown word
(615; 153 have no word within 2):

```
                      time     distances   rows         cells filled    trie nodes visited
-s (walk, -e 2)       0.13 s   0           3969047      32263386        4385799
-s --near=scan        5.28 s   37138620    346569105    2785513961      85702492
-s -e 1 (walk)        0.03 s   0           603861       4920045         1020613
-s --near=scan
   --algo=list        6.56 s
-s --algo=bloom       0.15 s   (the trie built once, for the first unknown word)
```

37138620 = 615 words times 60388. The walk fills 86 times fewer cells.
Measured on texts with typos (gen.py typos; the different unknown words
grow with the text: 756 in 10000 words, 5521 in 100000):

```
$ python3 bench/grow.py --limit 2 --input typos bin/spell -s --near=scan
     1000        5132     0.750
     2000       10196     1.393    1.9
     4000       20269     2.570    1.8
$ python3 bench/grow.py --limit 2 --input typos --max 4194304 bin/spell -s
     4000       20269     0.067    1.6
    ...
   128000      648583     1.118    1.8
   256000     1299038     2.014    1.8
```

The scan stops being usable at a page or two of text with typos (4000
words: 2.6 s); the walk does 256000 words in 2 s.

Break it (prune on the last cell, not the smallest): in near_walk, `if
(min <= n->maxd)` becomes `if (row[n->len] <= n->maxd)`. The last cell is
the distance to the prefix itself, which is large for a short prefix of a
near word ("spel" is 3 from "speling"), so the walk stops above it:

```
$ printf 'speling recieve teh holmes quik\n' | bin/spell -s
holmes:
quik:
recieve:
speling:
teh: eh tea tech ted tee
```

On the book, 434 of the 615 lines change (line by line, or `comm -23`
against the right output; macOS's diff between the two files reports 435,
since its diff is not always the shortest), and 573 have no suggestion at
all where 153 had none; cells filled 486209 instead of 32263386: fast, and
wrong. --near=scan is right, which is the point of keeping it.

Break it (no insertions): in edit_next_row, `int best = del < ins ? del :
ins;` becomes `int best = del;` (the compiler warns that ins is unused).
The distance is no longer the same both ways:

```
$ bin/spell --distance kitten sitting
3
$ bin/spell --distance sitting kitten
6
$ printf 'holmes\n' | bin/spell -s
holmes: dolmen dolmens haloes halves helmet
```

## The tests and the timeline

- tests/tools/spell.py: the model (Python sets and lists), the pipeline
  (tr | tr | grep .. | sort -u | comm -23), look (the system's, or
  bin/look where there is none), the whole-table distance, nearest(), and
  random non-words; timeline steps and after-checks for every lesson from
  05.01.
- 0501: the book with trie and table against model and pipeline; the list
  on 1500 lines of the book, with its "scanned" equal to the exact sum (a
  word's place in the list, or the whole list); the trie's nodes equal to
  the different prefixes plus the root, its visits to the letters walked;
  -p for 10 prefixes three ways against look; -d twice with capitals,
  CRLF, a non-word and a duplicate; the trace lines; the errors.
- 0502: the book's filter output a subset of the exact one, at most 3%
  missing; m the first prime from the formula, k = (m/n) ln 2; on 40000
  non-words, the share that gets through within five standard deviations
  of the formula for --fp 0.1, 0.01, 0.001 and --hashes 1 and 14; memory
  in the order bloom < text/7 < list < table < trie; -p refused; trace.
- 0503: 62 distances against the whole table, with rows and cells
  counted; the trace table for kitten/sitting; -s on a typo text against a
  quarter of the dictionary, walk equal to scan and to the model; the scan's
  distances = unknown words times dictionary words, the walk's cells under
  a tenth of the scan's; 7 words through 5 ways with -e and -n; the
  filter's trie built only when needed; the walk's trace; the errors.
- `./learn test dsa 05` about 9 s on the Mac (05.03 5.7 s, most of it the
  Python model); the same tests pass with -fsanitize=address,undefined.
