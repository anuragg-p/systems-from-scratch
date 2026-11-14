# Module 09, gzip and gunzip: notes for the lesson writers, and the API for git

Everything here was run on the reference code: Apple M4 Pro, macOS 26.6.2,
Apple clang 21, Apple gzip 479 (its DEFLATE data is zlib's, byte for byte:
checked with gzip -6 -n on the book against Python's zlib 1.2.12); and on
Linux: Docker debian:stable-slim (aarch64, the same Mac), gcc 14.2, GNU gzip
1.13, busybox. Times are wall clock, the best of three (`timeit.py`-style:
Python's perf_counter around the run), or bench/grow.py where it says so.
The Mac was shared with other jobs while these ran (load average anywhere
from 10 to 150), so a time can be 20% off the next run's: the book's scan
measured 3.19 s once and 2.713 s later, the hash 0.04 s and 0.027 s. The
counts (DS_STATS) are the same every run.
Every "break it" was made on the project as `./learn files dsa --at NN.LL`
writes it, with that one change, and the output is pasted as it came.

Written from RFC 1951 (DEFLATE) and RFC 1952 (gzip), fetched 2026-11-14 from
www.rfc-editor.org and read; no code from zlib or anywhere else. NOTICE.txt
here is the text for the top-level NOTICE.

## The files, and the lesson each part comes with

```
lib/huffman.h, .c   09.01  Huffman code lengths from counts (the heap of 02.04),
                           canonical codes; 09.04 adds the 15-bit limit
lib/inflate.h, .c   09.02  raw inflate: the bit reader, codes read a bit at a time
                           or with a table, stored, fixed and dynamic blocks; and the
                           RFC's tables (length and distance codes, fixed lengths)
lib/lz77.h, .c      09.03  the parse into literals and matches: the window scan,
                           the hash chains and their bound
lib/deflate.h, .c   09.04  raw deflate: the bit writer, the three forms of block,
                           each block priced in all three and the cheapest written
tools/gzip/gz.h, .c 09.02  the gzip container: read_all, write_all, CRC-32, the
                           header, gz_unpack (members, trailer checks); 09.04 gz_pack
tools/gzip/gzip.c   09.01  --huffman; 09.03 --lz77, --algo, --chain; 09.04 compressing
tools/gzip/gunzip.c 09.02  gunzip, whole
tools/gzip/tool.mk  09.01  both programs; LIB += each lib object as its lesson comes
```

Regions (`@build`) are the bodies of: 09.01 huff_lengths, huff_codes (huffman.c),
show_huffman (gzip.c); 09.02 bits, build, decode_bits, decode_table, stored,
codes, fixed, dynamic, inflate_raw (inflate.c), crc32, header, gz_unpack
(gz.c), gunzip_one (gunzip.c); 09.03 match_scan, insert, match_hash, lz77_parse
(lz77.c), show_lz77 (gzip.c); 09.04 huff_lengths_limited, put, write_stored,
write_tokens, plan_dynamic, write_header, write_block, deflate_raw (deflate.c),
gz_pack (gz.c), gzip_one (gzip.c). gzip.c's main, usage and includes grow by
`@from` lines. A note on order: the module's programs appear as gzip at 09.01
(only --huffman), gunzip at 09.02, and gzip's compressing at 09.04. Before
09.04 a plain `bin/gzip` prints its usage (exit 2), listing only the modes it
has:

```
$ bin/gzip < /dev/null            (at 09.03)
gzip: usage: gzip --huffman [file]
       gzip --lz77 [--algo=NAME] [--chain=N] [file]
```

## The programs

```
gzip --huffman [file]                     09.01  each byte's code, and the size in it
gzip --lz77 [--algo=NAME] [--chain=N] [file]
                                          09.03  literals and matches, counted
gzip [-1 ... -9] [-c] [-f] [-k] [--blocks=NAME] [--algo=NAME] [--chain=N] [file ...]
                                          09.04  FILE -> FILE.gz, FILE removed
gunzip [-c] [-f] [-k] [-t] [--algo=NAME] [file ...]
                                          09.02  FILE.gz -> FILE, FILE.gz removed
```

- gzip --algo: `hash` (the default), `scan` (the slow one), `none` (no
  matches: Huffman codes alone). --chain=N: the most places a hash search
  tries, 0 for no limit; 128 by default; -1 ... -9 set it to 4, 8, 16, 32,
  64, 128, 256, 1024, 4096 (last option wins). --blocks: `best` (default,
  each block the cheapest form), `stored`, `fixed`, `dynamic`.
- gunzip --algo: `table` (default) or `bits`.
- As the system's: no file or `-` is standard input to standard output; a
  named file is replaced (FILE.gz there already is an error without -f);
  gzip keeps the file's name and mtime in the header (none for stdin, MTIME
  0), XFL 2 at -9 and 4 at -1, OS 3. gzip will not write to a terminal
  without -f. gunzip reads several members one after another (a `cat` of
  .gz files). Every error is status 2 with nothing written for that file.
- Both read the whole file into memory; gunzip holds the whole output. Not
  done: -d, -l, -n/-N, -r, restoring modes and times, trailing zeros after
  the last member (GNU warns and goes on; ours is an error naming them).

## DS_STATS and DS_TRACE

DS_STATS=1 lines (the tool's first, then each structure in the order used):

```
stats: gzip: bytes in I, bytes out O
stats: gunzip: files F, bytes in I, bytes out O
stats: huffman: trees T, joins J, rebuilds R        (R: built again for the 15-bit limit)
stats: inflate: stored blocks S, fixed blocks F, dynamic blocks D, symbols N, table lookups T, bits walked W
stats: lz77: literals L, matches M, match bytes B, candidates C, comparisons K, chains cut X
stats: deflate: stored blocks S, fixed blocks F, dynamic blocks D, bits out B
```

plus `heap` (huffman uses it) and `array` (every byte buffer is an Array).
"candidates": places tried as the start of a match; "comparisons": bytes
compared doing it (the failing one included); "bits walked": bits read one at
a time by decode_bits (all of them with --algo=bits, only codes over 9 bits
with the table).

DS_TRACE=1 (anything but 0) prints every step on stderr, so use small inputs.
The format, one line per step, for making figures from real runs:

```
trace: huffman: tree of 5 symbols
trace: huffman: join 'c' 1 + 'd' 1 = n1 2         the two lightest: name count + name count = join sum
trace: lz77: 0: literal "a"                       position: the byte, as C writes it in quotes
trace: lz77: 7: match distance 7 length 4 "abra"  position: distance, length, the bytes it stands for
trace: deflate: block 1 (last): 11 bytes, 8 tokens: stored 128 bits, fixed 79 bits, dynamic 159 bits: fixed
trace: inflate: block 1: fixed (last)             or "stored"; a dynamic block's line comes after its header:
trace: inflate: block 1: dynamic (last), header 130 bits, 259 literal/length codes (longest 3 bits), 6 distance codes (longest 1 bits)
trace: inflate: 0: literal "a"                    the same token lines as lz77's
trace: inflate: end of block 1: 79 bits, 11 bytes
```

A symbol in a huffman join is `'c'` when printable, else its number (256 is
end of block, 257... lengths; in a dynamic block's other two trees the
numbers are distance codes 0-29 and code-length symbols 0-18). nK is the K-th
join. In one gzip run three trees are built per block: literal/length,
distance, code-length, in that order. Bytes in quotes: `\n \t \" \\`, other
non-printables `\xNN`. The token lines of lz77 (writing) and inflate (reading)
are the same format, and the same tokens: what gzip wrote is what gunzip read.

## The API, for git (module 10)

git needs zlib streams: a 2-byte header (CMF 0x78, FLG), raw DEFLATE, and an
Adler-32 of the data, big-endian. Both directions are in the library
(build/libds.a has them once tools/gzip/tool.mk is there; its LIB += lines
add the objects); the zlib framing and Adler-32 are git's to write.

```c
#include "inflate.h"
Array out;
array_init(&out, 1);                       /* bytes */
size_t used;
const char *err = inflate_raw(in, n, &out, &used);
/* err: NULL, or what is wrong (a static string, good until the next call);
   used: the bytes of in the DEFLATE data took, so in + used is the Adler-32.
   Never reads outside in[0..n), whatever the bytes. out keeps what came
   before an error. */

#include "deflate.h"
deflate_raw(in, n, NULL, &out);            /* appends raw DEFLATE; NULL: the defaults,
                                              {LZ77_HASH, 128, DEFLATE_BEST}, gzip -6's */
DeflateOptions opt = {LZ77_HASH, 4096, DEFLATE_BEST};   /* -9's chain */
deflate_raw(in, n, &opt, &out);
```

Also there: `huff_lengths`, `huff_lengths_limited`, `huff_codes` (huffman.h),
the RFC tables `deflate_length_base/extra`, `deflate_dist_base/extra`,
`deflate_clen_order`, `deflate_fixed_lengths()` (inflate.h), and lz77.h's
parse. CRC-32 is not in lib/ (it is gz.c's, the gzip container's). Things
the git agent should know: inflate_raw holds the whole output in one Array
(objects are small; fine); git's loose objects are zlib level 1 by default
but any level reads; deflate_raw always ends on a byte boundary with the
last block marked final, so the Adler-32 goes right after it. A one-liner to
check a zlib stream made with deflate_raw: `python3 -c "import zlib,sys;
zlib.decompress(sys.stdin.buffer.read())"`.

## 09.01 Huffman codes: a greedy tree

The code: gzip --huffman counts the bytes, `huff_lengths` builds the tree
with the heap (each join two pops and a push; ties go to the leaf of the
smaller symbol, then the earlier join, so the tree is the same everywhere),
a symbol's length is its depth; `huff_codes` numbers the codes canonically
(RFC 1951 3.2.2: count each length, first code of each length, then in
symbol order). The table prints each byte's count, length and code, and the
total.

The worked example, "abracadabra" (a 5, b 2, r 2, c 1, d 1):

```
$ printf abracadabra | DS_TRACE=1 bin/gzip --huffman
trace: huffman: tree of 5 symbols
trace: huffman: join 'c' 1 + 'd' 1 = n1 2
trace: huffman: join 'b' 2 + 'r' 2 = n2 4
trace: huffman: join n1 2 + n2 4 = n3 6
trace: huffman: join 'a' 5 + n3 6 = n4 11
byte      count  bits  code
'a'           5     1  0
'b'           2     3  100
'c'           1     3  101
'd'           1     3  110
'r'           2     3  111
11 bytes, 5 different: 88 bits as bytes, 23 bits in these codes (3 bytes)
```

Sizes to set beside it: 88 bits as bytes; 33 bits in the best fixed-length
code (5 symbols need 3 bits each); 23 in Huffman's. Why the two rarest, with
these numbers (worked by hand from the run above, for a figure):

- Common symbols must be shallow: swap 'a' (5, depth 1) with 'c' (1, depth
  3) and the total grows by (5 - 1) x (3 - 1) = 8, to 31 bits. So in a best
  code the rarest symbols sit deepest, and the two rarest can be the two
  leaves under one node (c and d, under n1).
- Joining them shrinks the problem by one symbol: {a 5, b 2, r 2, n1 2}. Its
  best code costs 21 bits (a 1 bit, n1 2 bits, b and r 3 bits: 5 + 4 + 6 +
  6). Splitting n1 back into c and d adds one bit to each: + 1 + 1 = + 2,
  the count of n1, to every code of the smaller problem alike; so the best
  for the smaller is the best for the larger: 21 + 2 = 23. Repeat.
- Ties make other best trees: a 1, b 2, r 3, c 4, d 4 is also 23 bits
  (5 + 4 + 6 + 4 + 4). Canonical numbering makes the lengths the only thing
  stored, whichever tree gave them.

On the book:

```
$ DS_STATS=1 bin/gzip --huffman data/book.txt
byte      count  bits  code
'\n'      11922     6  110010
' '       95573     3  000
...
'/'           1    18  111111111111111110
...
'Z'           2    18  111111111111111111
...
'e'       52886     3  001
...
562404 bytes, 78 different: 4499232 bits as bytes, 2538424 bits in these codes (317303 bytes)
stats: gzip: bytes in 562404, bytes out 0
stats: huffman: trees 1, joins 77, rebuilds 0
stats: array: pushes 155, grows 5, moves 120
stats: heap: pushes 155, pops 154, comparisons 1433, moves 979
```

56.4% of the bytes, from Huffman alone. 77 joins for 78 symbols. Lengths run
from 3 bits (space, e) to 18 ('/' once, 'Z' twice): longer than DEFLATE's 15,
which is 09.04's problem. The test checks the total against a Huffman tree
built independently in Python (heapq): the same 2538424 bits.

The slow way here: there is none worth a flag. The alphabet is at most 288
symbols, so picking the two rarest by looking at every node (n^2/2 = 41000
looks for 288) or with the heap (1433 comparisons for the book's 78) both
take no measurable time; the heap is used because module 02 built it, and
the comparisons count says what it saves. The lesson's "obvious first" is the
fixed-length code (8 bits, or 7 for 78 symbols: 3936828 bits) against which
Huffman's 2538424 is measured.

Break it (join the two most common instead: in `lighter()`, `return x->count
< y->count ? -1 : 1;` becomes `return x->count > y->count ? -1 : 1;`):

```
$ printf abracadabra | DS_TRACE=1 bin/gzip --huffman
trace: huffman: tree of 5 symbols
trace: huffman: join 'a' 5 + 'b' 2 = n1 7
trace: huffman: join n1 7 + 'r' 2 = n2 9
trace: huffman: join n2 9 + 'c' 1 = n3 10
trace: huffman: join n3 10 + 'd' 1 = n4 11
byte      count  bits  code
'a'           5     4  1110
'b'           2     4  1111
'c'           1     2  10
'd'           1     1  0
'r'           2     3  110
11 bytes, 5 different: 88 bits as bytes, 37 bits in these codes (5 bytes)
$ bin/gzip --huffman data/book.txt
gzip: huffman: a code of 65 bits, longer than 32
```

(The heap now always hands back the heaviest tree, which is the one just
made: the tree is a chain, 'a' at the bottom, the rarest on top. On the
book, a chain 65 deep: huff_codes refuses codes over 32 bits, an ordinary
error.)

## 09.02 Inflate: reading a real gzip file

The code: the bit reader (`bits()`: a 64-bit buffer refilled a byte at a
time; past the end it reads zeros, and `cut_short()` notices any bit used
from there); `build()` turns lengths into the canonical numbering (count,
first code, where each length's symbols start) and a 512-entry table for
codes up to 9 bits, checking that the lengths do not ask for more codes than
there are (over-subscribed: an error; fewer is allowed); `decode_bits()` (a
bit at a time: the code so far is a code of length L if it is within count[L]
of first[L]) and `decode_table()` (peek 9 bits, one look; a longer code falls
back to decode_bits); the three block types; and in gz.c the header, CRC-32
(table of 256, built from the reversed polynomial 0xedb88320), and the
trailer checks. gunzip_one reads the whole file, unpacks it in memory, and
writes only when everything checked.

It reads the system's gzip at -1 to -9 (Apple's and GNU's), busybox gzip -1,
-6, -9, GNU gzip --rsyncable, Python's zlib at levels 0-9 with every strategy
(default, filtered, huffman-only, rle, fixed), windows of 2^9 to 2^12, memLevel
1 and 9, sync and full flushes (empty stored blocks mid-stream), zlib's own
gzip framing, Info-ZIP's `zip -9` (Zip 3.0, built without zlib: a deflate of
its own) wrapped in a gzip member, headers with FNAME, FCOMMENT, FEXTRA, FHCRC and FTEXT, and
several members in one file. All of this is in the 09.02 test.

```
$ printf 'hello hello hello\n' | gzip -9 | DS_TRACE=1 bin/gunzip
trace: inflate: block 1: fixed (last)
trace: inflate: 0: literal "h"
trace: inflate: 1: literal "e"
trace: inflate: 2: literal "l"
trace: inflate: 3: literal "l"
trace: inflate: 4: literal "o"
trace: inflate: 5: literal " "
trace: inflate: 6: literal "h"
trace: inflate: 7: match distance 6 length 10 "ello hello"
trace: inflate: 17: literal "\n"
trace: inflate: end of block 1: 87 bits, 18 bytes
hello hello hello
```

(The match overlaps what it copies: 10 bytes from 6 back. That is why the
copy goes a byte at a time.) The book from the system's gzip -6 (216849
bytes) is 8 dynamic blocks, headers of 463 to 595 bits, literal/length codes
of 271 to 275 symbols and 12 to 14 bits at most:

```
$ gzip -6 -c data/book.txt | DS_STATS=1 bin/gunzip -t
stats: gunzip: files 1, bytes in 216849, bytes out 562404
stats: array: pushes 562404, grows 18, moves 1048568
stats: inflate: stored blocks 0, fixed blocks 0, dynamic blocks 8, symbols 198811, table lookups 198811, bits walked 28997
$ gzip -6 -c data/book.txt | DS_STATS=1 bin/gunzip -t --algo=bits
stats: inflate: stored blocks 0, fixed blocks 0, dynamic blocks 8, symbols 198811, table lookups 0, bits walked 873719
```

198811 symbols for 562404 bytes. A bit at a time: 873719 steps, 4.4 a
symbol; with the table: 198811 looks and 28997 bits walked for the few codes
over 9 bits, 30 times fewer steps. The time, though, hardly moves, and that
is worth saying honestly: writing the bytes out (an array_push for each)
costs more than reading the codes.

```
                                  gz bytes   --algo=table  --algo=bits  system gunzip
book.txt (gzip -6)                  216849       0.007 s      0.008 s      0.005 s
gen.py text 1000000 (5.5 MB)       2463021       0.044 s      0.055 s      0.012 s
this repo as a tar (21.4 MB)       3031382       0.116 s      0.129 s      0.014 s
the same, zlib huffman-only       13621939       0.186 s      0.274 s      0.046 s
```

The table gains most where every byte is a symbol (huffman-only: 1.5x). The
system's gunzip (zlib, with its fast path for long matches) is 1.4 to 8
times quicker than ours; ours does about 185 MB/s on the tar. The slow way is
never unusable here: it is linear, a few bits' work more per symbol.

Damaged files: every error is status 2, a message saying what is wrong,
nothing written. Real messages:

```
$ printf 'not gzip' | bin/gunzip
gunzip: stdin: not in gzip format (it starts 6e 6f, not 1f 8b)
$ printf 'hello\n' | gzip | head -c 12 | bin/gunzip
gunzip: stdin: the data ends in the middle of a block
gunzip: stdin: the data's CRC-32 is a8e6f8ce, but the trailer says df8a7c3b
gunzip: stdin: the data is 3000 bytes (modulo 2^32), but the trailer says 0
gunzip: stdin: a match 2 bytes back, but only 1 bytes have been written
gunzip: stdin: a block of type 3, which DEFLATE reserves
gunzip: stdin: a stored block's length 5 and its check 0 do not match
gunzip: stdin: a block with 287 literal/length codes; DEFLATE has 286
gunzip: stdin: the code-length code has more codes than its lengths allow
gunzip: stdin: a repeat of the code length before, with none before it
gunzip: stdin: code lengths that run past the 258 the block says
gunzip: stdin: a block with no code for its end (256)
gunzip: stdin: length code 286, which DEFLATE does not use
gunzip: stdin: distance code 30, which DEFLATE does not use
gunzip: stdin: bits that are no literal/length code
gunzip: stdin: flag bits 0x20 set, which RFC 1952 reserves
gunzip: stdin: 4 bytes after the end of the gzip data, not another member
```

Hostile input under AddressSanitizer and UndefinedBehaviorSanitizer: see
"Hostile input" below.

Break it (copy a match from one byte too near: in `codes()`,
`out->data[out->len - back]` becomes `out->data[out->len - back + 1]`):

```
$ printf 'hello hello hello\n' | gzip -9 | DS_TRACE=1 bin/gunzip
...
trace: inflate: 7: match distance 6 length 10 "llo hllo h"
trace: inflate: 17: literal "\n"
trace: inflate: end of block 1: 87 bits, 18 bytes
gunzip: stdin: the data's CRC-32 is a8e6f8ce, but the trailer says df8a7c3b
$ bin/gunzip -t book.txt.gz
gunzip: book.txt.gz: the data's CRC-32 is fbf17e11, but the trailer says f8c846cb
```

DEFLATE itself has no check: the wrong bytes inflate without a single error,
the right length, and only the trailer's CRC-32 catches it. That is what the
trailer is for (and why gunzip writes nothing until it has checked).

## 09.03 LZ77: finding repeats with a hash table

The code: `lz77_parse` is greedy (the longest match at each place, 3 bytes
or more, else a literal). `match_scan` tries every place in the window,
nearest first, keeping the longest (the nearest of equals). `match_hash`
keeps, for each hash of 3 bytes (15 bits of a multiplicative hash), a chain
of the places with it, newest first: `head[hash]` and `prev[place % 32768]`;
every place before the current one is inserted first (those inside matches
too), the current one after, so a chain read holds only earlier places; the
walk stops past 32768 back or after `chain` places. With no bound (--chain=0)
it finds exactly the scan's matches (the test checks the token streams are
equal), since a match of 3 or more must start with the same 3 bytes.

```
$ printf abracadabra | DS_TRACE=1 bin/gzip --lz77
trace: lz77: 0: literal "a"
trace: lz77: 1: literal "b"
trace: lz77: 2: literal "r"
trace: lz77: 3: literal "a"
trace: lz77: 4: literal "c"
trace: lz77: 5: literal "a"
trace: lz77: 6: literal "d"
trace: lz77: 7: match distance 7 length 4 "abra"
11 bytes: 7 literals, 1 matches for the other 4 bytes
```

The book, the scan against the hash table:

```
$ /usr/bin/time -p env DS_STATS=1 bin/gzip --lz77 --algo=scan data/book.txt
562404 bytes: 10685 literals, 93951 matches for the other 551719 bytes
stats: lz77: literals 10685, matches 93951, match bytes 551719, candidates 3275711270, comparisons 3452025839, chains cut 0
real 3.19
$ DS_STATS=1 bin/gzip --lz77 --chain=0 data/book.txt      (no bound: the very same tokens)
stats: lz77: literals 10685, matches 93951, match bytes 551719, candidates 4346757, comparisons 19903425, chains cut 0
$ /usr/bin/time -p env DS_STATS=1 bin/gzip --lz77 data/book.txt     (the default bound, 128)
562404 bytes: 10726 literals, 94587 matches for the other 551678 bytes
stats: lz77: literals 10726, matches 94587, match bytes 551678, candidates 3403020, comparisons 15649934, chains cut 9029
real 0.04
```

(Trimmed: the gzip and array stats lines, and time's user and sys lines.)

The same matches for 1/750 of the places tried and 1/170 of the
comparisons; with the bound, 41 bytes fewer in matches (0.007%) for a little
less again. Where the scan stops being usable, measured (input: text):

```
$ python3 bench/grow.py --limit 2 bin/gzip --lz77 --algo=scan
        n       bytes   seconds  ratio
     1000        5260     0.008
     2000       10634     0.018
     4000       21395     0.053
     8000       42818     0.177    3.3
    16000       85604     0.452    2.6
    32000      171174     1.013    2.2
    64000      342492     2.181    2.2
growth: each doubling multiplies the time by about 2.2: about n: twice the input, twice the time
$ python3 bench/grow.py --limit 2 --start 64000 bin/gzip --lz77
        n       bytes   seconds  ratio
    64000      342492     0.020
   128000      684437     0.040    2.0
   256000     1395080     0.080    2.0
   512000     2818492     0.155    1.9
  1024000     5663824     0.309    2.0
  2048000    11346023     0.606    2.0
  4096000    22717280     1.118    1.8
growth: each doubling multiplies the time by about 2.0: about n: twice the input, twice the time
```

Worth a sentence: the scan grows as n^2 only while the input is under 32 KB
(each byte has all the bytes before it to try); past that the window caps it
and it is linear, but every byte costs up to 32768 tries. It is a constant
factor of about 100, not a power: 342 KB in 2.181 s against 0.020 s; 5.5 MB
(`gen.py text 1000000`) compressed in 35.5 s against 0.335 s, where the
system's gzip -6 takes 0.226 s. A 22 MB file would take the scan about 2.5
minutes. (--chain=0 is linear too on text: 1.372 s at 22.7 MB.)

Where the bound matters: two letters at random (30000 bytes of a and b),
where every three bytes come back every 8 bytes, so chains are thousands long
and matches short:

```
--chain=0    2198 matches   candidates 3878639   comparisons 19396390
--chain=128  2904 matches   candidates  363791   comparisons  1818589   chains cut 2790
--chain=4    5442 matches   candidates   21758   comparisons   108642   chains cut 5435
```

The bound trades the length of the matches (13.6, 10.3, 5.5 bytes on
average) for the work: that is what gzip's -1 to -9 are.

Break it (a poor hash: `hash3()` returns `p[0]`, only the first byte, 256
chains instead of 32768):

```
$ /usr/bin/time -p env DS_STATS=1 bin/gzip --lz77 --chain=0 data/book.txt
562404 bytes: 10685 literals, 93951 matches for the other 551719 bytes
stats: lz77: literals 10685, matches 93951, match bytes 551719, candidates 151794811, comparisons 328109380, chains cut 0
real 1.67
$ /usr/bin/time -p env DS_STATS=1 bin/gzip --lz77 data/book.txt
562404 bytes: 55613 literals, 108933 matches for the other 506791 bytes
stats: lz77: literals 55613, matches 108933, match bytes 506791, candidates 20103535, comparisons 44381666, chains cut 153651
real 0.07
```

(Trimmed as above. The compiler warns that `x` in hash3 is now unused.)

With no bound the matches are the same (a chain still holds every place with
the same first byte), for 35 times the tries; with the bound of 128 the right
places are too far down the chains, and 5 times as many bytes stay literals
(55613 against 10726). The same lesson as freq's hash_sum in 01.03.

## 09.04 Deflate: writing a file gunzip accepts

The code: `put()` (the bit writer, lowest bit first); Huffman codes are
reversed once (`make_codes`) so put() sends their first bit first.
`write_block` counts the block's symbols, prices it to the bit in all three
forms (stored: 3 bits, the pad to a byte, LEN, NLEN, the bytes, 65535 bytes
a block at most; fixed: the RFC's lengths; dynamic: plan_dynamic's header
plus the data in its own codes), and writes the cheapest. `plan_dynamic`
builds the literal/length and distance codes from the counts, no code over
15 bits (`huff_lengths_limited`), gives a code with fewer than two symbols a
partner so every code is complete, trims HLIT/HDIST, run-length codes the lengths (16 repeats the last
length 3-6 times, 17 is 3-10 zeros, 18 is 11-138 zeros), and builds the
code-length code (7 bits at most), sending its lengths in the RFC's order
16, 17, 18, 0, 8, 7, 9, ... with the zeros at the end left off (HCLEN). A
block is 16384 tokens at most (as zlib's default); the last is marked final
and the stream padded to a byte.

Why complete codes: the RFC allows a code with patterns left over (it says so
for a lone distance code), and our inflate reads one, but the system's do
not. Tried with a hand-made block whose literal/length code is a 1 bit, 256
2 bits, the pattern 11 unused: ours prints "a"; Apple's gunzip says "data
stream error", Python's zlib "invalid literal/lengths set", GNU gzip 1.13
"invalid compressed data--format violated". The same block with 257 given
the spare pattern, all four read it.

How the 15-bit limit is kept: build Huffman's tree; while its deepest code is
over the limit, halve every count (rounding up, so no used symbol drops to
0) and build it again. Halving keeps the order of the counts but brings the
rare symbols closer to the common, so the tree is less lopsided; once every
count is 1 it is balanced (9 bits for 288 symbols), so it ends. It is not
optimal (package-merge is), but it is rare and cheap: on the test's
Fibonacci input (18 byte values with counts 1, 2, 3, 5, ... 4181, 10944
bytes, which with the end-of-block's 1 make a tree 17 deep), one halving
gives a code of 10 bits at most, and the block's data costs 28643 bits
against 28634 for the unlimited (unwritable) code: 9 bits more. On ordinary
text it never happens: the book in 7 blocks, rebuilds 0.

```
$ printf abracadabra | DS_TRACE=1 bin/gzip -c > a.gz      (huffman lines left out)
trace: lz77: 0: literal "a"
...
trace: lz77: 7: match distance 7 length 4 "abra"
trace: deflate: block 1 (last): 11 bytes, 8 tokens: stored 128 bits, fixed 79 bits, dynamic 159 bits: fixed
$ od -An -tx1 a.gz
 1f 8b 08 00 00 00 00 00 00 03 4b 4c 2a 4a 4c 4e
 4c 01 51 00 b7 f9 ea 17 0b 00 00 00
```

28 bytes: 10 of header, 10 of DEFLATE (79 bits), 8 of trailer. A small input
goes fixed; the dynamic header alone is 130 bits here. On the book every
block goes dynamic (block 1: stored 619352 bits, fixed 320490, dynamic
259517).

The book in each form, and with each level, against the system's gzip (Apple
gzip 479; bytes of the whole .gz file, name included in ours):

```
--blocks=stored  562496     --algo=none (Huffman alone)  318565
--blocks=fixed   278222     --algo=hash                  223193
--blocks=dynamic 223193     (gzip --huffman's one code:  317303)

level   ours      time     system    time
 -1    247068    0.015 s   257889   0.009 s
 -2    238073    0.019 s   246990   0.009 s
 -3    232067    0.020 s   235918   0.012 s
 -4    227571    0.025 s   229735   0.014 s
 -5    224713    0.030 s   221281   0.022 s
 -6    223193    0.036 s   216849   0.024 s
 -7    222612    0.041 s   216266   0.032 s
 -8    222354    0.044 s   215996   0.039 s
 -9    222354    0.046 s   215996   0.032 s
```

Sizes on more files (the DEFLATE data and trailer: ours less its file name,
the system's with -n; Apple gzip 479 on the Mac, GNU gzip 1.13 in Docker):

```
file                    bytes   ours -1   Apple -1   GNU -1   ours -6   Apple -6   GNU -6   ours -9   Apple -9   GNU -9
book.txt               562404    247059     257880   257722    223184     216840   216700    222345     215987   215839
gen.py text 1000000   5530609   2716154    2793703  2791544   2526081    2463008  2460938   2521487    2458171  2456088
gen.py lines 100000   2436133   1186842    1219518  1218708   1104008    1076083  1075320   1101530    1073788  1072991
this repo, a tar     21411840   3419115    3625548  3634162   3141976    3031373  3032942   3127446    2963133  2962151
/bin/ls (Mach-O)       154208     34731      35259    35335     34432      33714    33640     34404      33656    33592
random bytes          1048576   1048914    1048914  1048754   1048914    1048914  1048754   1048914    1048914  1048754
zeros                 1048576      1051       4608     4608      1051       1051     1051      1051       1051     1051
Fibonacci text          10944      4656       4730     4730      4538       4397     4397      4538       4402     4402
```

At -6 ours is 2 to 4% larger than either system gzip, at -9 2 to 6% (the
tar: 3127446 against 2963133); at -1 it is smaller (their -1 inserts fewer places into the chains). Random bytes go out
stored (5 bytes a block over the data; ours 16384-byte blocks, GNU's larger).
The gap at -6 is lazy matching, which ours does not do (RFC 1951 section 4
describes it): measured in a scratch copy, one look ahead (if the match at
the next byte is longer, write this byte as a literal and take that one)
gives the book 216969 bytes against Apple's 216840, the text 2464474 against
2463008, the tar 2990142 against 3031373. A good "Decide the boundary" for
09.03 or 09.04: greedy is simpler and 3% bigger.

The Fibonacci text is a case where matches hurt: with --algo=none it is 3621
bytes, with matches 4538 (and Apple's gzip -9, 4402; all without the name):
random letters with skewed counts have short repeats that cost more as
pointers than as literals.

Break it (send the codes with their bits in the wrong order: in
`make_codes`, `c->rev[s] = r;` becomes `c->rev[s] = codes[s];`):

```
$ printf 'hello hello hello\n' | bin/gzip > h.gz
$ gunzip -c h.gz
gunzip: data stream error
gunzip: h.gz: uncompress failed
$ bin/gunzip -c h.gz
gunzip: h.gz: a match 1765 bytes back, but only 0 bytes have been written
$ bin/gzip -c data/book.txt > b.gz; bin/gunzip -t b.gz
gunzip: b.gz: code lengths that run past the 304 the block says
```

Break it (no 15-bit limit: in `plan_dynamic`, `huff_lengths_limited(lc, 286,
HUFF_MAX_BITS, h->lit.len);` becomes `huff_lengths(lc, 286, h->lit.len);`,
on the Fibonacci text, which needs 17 bits):

```
$ bin/gzip -c --algo=none fib.txt > fib2.gz
$ gzip -t fib2.gz
gzip: data stream error
gzip: fib2.gz: uncompress failed
$ bin/gunzip -t fib2.gz
gunzip: fib2.gz: code lengths that run past the 259 the block says
```

(A length of 16 or 17 cannot be written: in the code-length alphabet 16 and
17 mean "repeat", so the header says something else entirely.)

## Hostile input

The finished project built with AddressSanitizer and UndefinedBehaviorSanitizer
(`make EXTRA_CFLAGS="-fsanitize=address,undefined -fno-omit-frame-pointer
-fno-sanitize-recover=all"`) was fed by a fuzz script (kept out of the track):
the system's gzip -1, -6 and -9, zlib's fixed, huffman-only, rle and level-0
(stored) streams, and our own gzip's, of five inputs (4000 and 60000 bytes
of the book, 5000 random bytes, 5000 a's, nothing); every truncation of each
under 3000 bytes; every single bit flipped in the first 400 bytes of one;
random flips, random bytes, spliced junk and garbage after a valid header,
each read with --algo=table and --algo=bits; random DEFLATE after a valid
gzip header; and 200 random inputs through our gzip (every level, form and
--algo=none) read back by zlib and our gunzip. Every run had to end with the
right bytes, or status 2 and a "gunzip: " message; a sanitizer report, a
signal or any other status counted as a failure.

- Linux (gcc 14.2, Debian, in Docker): the first run had 42 failures out of
  21759 runs. The report kept (only the last was printed) was UBSan's, at
  gunzip.c's `fwrite(out.data, 1, out.len, stdout)` with an empty output:
  an Array has no block until its first push, and fwrite(NULL, 1, 0, ...)
  is undefined. Fixed there and in write_all, and gz_unpack no longer adds
  0 to a NULL pointer for the CRC of an empty member. The same run again:
  21759 runs, 0 failures. Nothing in inflate itself was ever reported.
- Mac (Apple clang 21, the fixed code): 21759 runs, 0 failures (about 30
  minutes: a sanitized process is slow to start on macOS).

The 09.02 test runs the same kinds of input without the sanitizers on every
`./learn test`: a 3000-byte text's .gz cut at every byte of its header and
trailer and every fifth byte between (some 300 cuts), 150 random damages,
and the hand-made blocks above, written bit by bit in Python (the test's
`Bits` and `canonical`).

## The tests and the timeline

09.01: the abracadabra table and joins exactly; on the book, every count, a
complete canonical prefix-free code, and the total equal to Python's own
Huffman total; one join per symbol but one. 09.02: the reading above, the
two decoders, the files, the damage. 09.03: the tokens rebuild the input; no
bound gives the scan's very tokens with a fiftieth of the comparisons or
less; the bound of 128 keeps 98% of the scan's match bytes; a repeat 20000
back is found and 40000 back is not; the two-letter input. 09.04: round
trips through the system's gzip -t and gunzip, ours and Python's zlib, for
the book, lines, noise, zeros, nothing, one byte, every byte, two letters,
every level and every forced form; the cheapest form wins; within 5% of the
system's -6 and -9 on the book; the Fibonacci limit; the file handling.
check-timeline types at each lesson: abracadabra's table (09.01 on);
gunzip on the system's gzip -9, on "not gzip" and on a cut file (09.02 on);
gzip --lz77 with hash and scan (09.03 on); before 09.04 plain gzip's usage,
from 09.04 a round trip both ways and a bad --blocks; then the book through
each (timeline_after). Whole runs on the Mac: the four tests about 7 s on a
quiet machine (09.02 is most of it: 54 runs of the system's gzip and about
450 damaged files, each a process; with the machine loaded by other jobs it
took 38 s before the cuts were thinned to every fifth byte).
