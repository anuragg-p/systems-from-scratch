# gpu track, modules 00 and 01: design of the lessons and figures

This is the design the lesson writers and the art builders work from. It is
decided. Build it, and report where it did not survive contact with the code
or the page. Lessons and figures are made in parallel by different agents, so
the figure file names and captions below are a contract: a lesson uses exactly
these names; an art builder draws exactly these files.

## Sources of truth

- The code: `tracks/gpu/` on master. The project at a lesson:
  `./learn files gpu --at NN.LL DIR`, or `./learn run gpu --at NN.LL`, which
  leaves it in `build/at/gpu/NN.LL/`.
- `tracks/gpu/NOTES.md`: regions by lesson, what the programs print, every
  measurement with its machine, the bugs found. `tracks/gpu/RESEARCH.md`: what
  was read in other systems' sources and documentation, with URLs and
  versions. A lesson states about another system only what RESEARCH.md
  records, or what the writer reads in that system's source or documentation
  and adds to NOTES.md with the URL and version. Nothing from memory. What
  RESEARCH.md lists under "Could not confirm" is not stated at all.
- `plans/gpu.md`: the plan and its decisions. `plans/gpu-outline.md`: titles.
- The format: `templates/lesson.md`, `templates/module.md`, README.md ("How it
  is organized", "Verifying a lesson"). Models to read before writing:
  `tracks/lang/lessons/01-introduction/01.01-*.md` (a first lesson) and
  `01.03-*.md`.

## Rules for everyone

- ASCII only, in every file.
- Work in your own git worktree. First run `git merge --ff-only master`.
  Commit as you go, each message starting "gpu" and ending with
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Do not push. Do
  not touch the main checkout, other worktrees, the harness, README.md, or
  tracks other than gpu. Never stash, reset or clean.
- Do not change the track's code or tests. If a lesson needs the code changed,
  give the exact line in your report instead.
- For a person whose pronouns are not stated, use they/them.
- Module folders: `tracks/gpu/lessons/00-the-workbench/` and
  `tracks/gpu/lessons/01-matrix-multiply-on-the-cpu/`. The placeholder lesson
  files there are replaced whole; each lesson's line comes out of
  `lessons/verify-pending.txt` when `./learn verify gpu NN.LL` passes.
  Figures in `figures/` beside the lessons.

## How a lesson is written

- Follow `templates/lesson.md` section by section: the opening, Where this
  fits (with the map), The idea (the main figure, and a `### name` lead-in for
  each piece of code the lesson adds, from the region titles in NOTES.md), Run
  it, How it works, Decide the boundary, Break it, Go deeper, Related.
- Voice: plain, short sentences, for someone who writes C and has never asked
  why one loop is faster than another. A term in **bold** the first time, with
  its meaning in the same sentence. No hook questions, no "simply", no telling
  the reader to write the code. Never mention stubs, tests, workspaces or
  check tools. Never use what a later lesson brings as if the reader had it;
  say "lesson NN.LL builds this".
- The track's two rules, stated in 00.01 and kept everywhere: a function is
  checked against a slow plain version before it is timed; a speed on a page
  is one the reader measures.
- **Numbers.** Values that come from a seed (wb show, check's errors) are the
  same on every machine: show them and let verify compare them exactly.
  Timings are not: show one real run, name the machine once per lesson in the
  text just before it ("on an Apple M4 Pro, with Apple clang 21"), say the
  reader's will differ, and annotate the block so `./learn verify` lets those
  numbers vary (`vary ... num`, or a line regex; see README) while still
  checking the lines' shape. Never round, tidy or invent a timing, and never
  state a speed-up in prose as a fixed fact: write "here, about 4 times", tied
  to the block above it. Before taking a transcript, run `uptime`; take it
  again if the load is above the core count, and put the load average in your
  report.
- Never explain a measurement with a cause nobody checked. NOTES.md marks
  some effects "not investigated" (gcc's slow ijk; the power-of-two sizes):
  a lesson may show the effect and say what is known to be different there,
  in the words given below, and no more.
- "Run it": `./learn run gpu --at NN.LL`, then the project's own programs
  inside `build/at/gpu/NN.LL/`. Run every command yourself and paste what you
  got. The lesson is done only when `./learn verify gpu NN.LL` passes.
- "Break it" is really done: make the change in the project at that lesson,
  run it, paste what happened, with the `verify: patch` and `session`
  annotations. If the experiment given below does not show what is claimed on
  your run, do not bend it: use the fallback named, or report.
- "Go deeper": links only to pages RESEARCH.md records (or that you fetch and
  record), each with what to look for there. CS:APP is cited by chapter only
  (chapter 5 for 00.03 and 01.03, chapter 6 for 01.02 and 01.04): nobody has
  read it for this track, so say nothing about what a page of it says beyond
  the chapter's subject.
- Length: 00.x about 700 to 1000 words of prose, 01.x about 900 to 1300.

## The map (every lesson's "Where this fits")

`figures/NN.LL-map.svg`, caption "Where NN.LL fits". The same picture in every
lesson of the track, 640 wide: the whole track as a stack, read bottom to top.

- Bottom, full width: **the workbench**, with three pieces in a row:
  "plain version", "checker", "timer". Module 00.
- Above it, left third: **on the CPU**: "matrix multiply" with five small
  rungs in a row: "ijk", "ikj", "simd", "blocked", "threads". Module 01.
- Above the workbench, right two thirds: **on the GPU**, a column of six
  rows, bottom to top: "element-wise kernels (02)", "matrix multiply (03)",
  "sums across a block: RMS norm, softmax (04)", "rotary positions and the
  KV cache in blocks (05)", "attention: one token (06), a whole prompt (07)",
  "half precision (08)".
- Top, full width: "a small model on your kernels, against PyTorch (09)".

In lesson NN.LL its own piece is in the accent colour (00.01: "plain version";
00.02: "checker"; 00.03: "timer"; 01.01: "ijk"; 01.02: "ikj"; 01.03: "simd";
01.04: "blocked"; 01.05: "threads"), pieces of earlier lessons are solid,
later ones dashed. One generator writes all eight.

## Module 00 - The workbench

Module README (one paragraph): before anything fast is written, the two tools
every later lesson leans on: a way to know an answer is right, and a way to
know how long it took. Everything here is C on the CPU and runs on any
laptop. Three files stay for the whole track: check.c, bench.c, rng.c.

### 00.01 A first function, and the plain version you trust

Teaches: every function in this track exists twice, a plain version nobody
could get wrong and the version being made fast; and test data comes from a
seed so two machines see the same numbers.

- Opening lesson of the track, so "Where this fits" is the tour: the map,
  then what a kernel is (one function a GPU runs as thousands of threads; an
  inference server is mostly Python on top of a few of them), the order the
  track builds in and why the first two modules have no GPU in them (the
  ideas that make a kernel fast - memory order, vectors, tiles, many workers
  - are met first where a debugger can step through them). The two rules.
  Say plainly: an NVIDIA GPU is needed from module 02.
- The idea: `add_ref` and `add` do the same sums; add takes four a pass and
  then a tail, so it has a place to be wrong that add_ref has not. Worked
  example n = 11: passes at 0 and 4, tail 8, 9, 10.
  `### xorshift64*`, `### a float in [0, 1)`, `### an array from a seed`:
  the generator, in the words of RESEARCH.md section 1: three shifts and a
  multiply, the top 24 bits make a float that is exact; it is the generator
  llama2.c samples with, bit for bit (commit named there). Why not rand():
  different numbers on every C library.
- Run it: `./learn run gpu --at 00.01` (wb show); then `./wb show -s 7`,
  `./wb show -n 6`. Exact values, compared exactly.
- How it works: (1) `i + 4 <= n`, not `i < n - 3`: n is unsigned. (2) the
  seed is the state, so seed 0 is stuck at 0 and `wb` refuses it: show
  `./wb show -s 0` and its message. (3) b's seed is the seed plus one.
- Decide the boundary: a reference in the same language and file (ours)
  against a reference from another system (numpy, PyTorch: what module 09
  does). Ours can be read in ten seconds and has no install; theirs has had
  a million users. The question: who checks the reference?
- Break it: in add.c change the tail's `i < n` to `i < n - 1`. `./wb show`
  prints exactly what it did before: the last element is wrong and nothing
  on the screen says so. That is the lesson's last line and 00.02's reason.
- Go deeper: llama2.c's run.c at the commit in RESEARCH.md (find the two
  random functions); the xorshift* reference RESEARCH.md gives.
- Figures: `00.01-map.svg`; `00.01-two-versions.svg`, caption "The same
  eleven sums, one at a time and four at a time": two rows of 11 cells
  numbered 0 to 10; the top row "add_ref" has 11 single steps; the bottom
  "add" has brackets over 0-3 and 4-7 labelled "one pass" and the cells 8,
  9, 10 in accent labelled "the tail, one at a time". `00.01-seed.svg`,
  caption "From a seed to a float": left to right, "state: 64 bits" ->
  "three shifts, each XORed back" -> "times a constant, top 32 bits" ->
  "top 24 bits / 2^24: a float in [0, 1)" -> "2x - 1: in [-1, 1)"; under the
  first box "the seed is the first state"; the 24-bit step in accent.

### 00.02 Right before fast: checking against a reference

Teaches: how to compare two arrays of floats: when `==` is right, what a
tolerance is and why it has two parts, and what a useful failure says.

- The idea: start from last lesson's invisible bug. A checker looks at every
  element. For add, the two versions do the same single addition per element,
  so they must agree to the bit: rtol = atol = 0. From module 01 on the
  versions add in different orders and floats round at each step, so equal
  answers differ in the last bits; then "close" needs a rule:
  `|got - want| <= atol + rtol * |want|`. rtol alone fails near zero (nothing
  is allowed around a want of 0); atol alone is too tight for big numbers and
  too loose for small ones. Worked example with rtol 1e-4, atol 1e-3: want
  20, got 20.002 (allowed 0.003: good); want 0, got 0.002 (allowed 0.001:
  bad). The rule is numpy.isclose's, and like it is not symmetric: want is
  the trusted side (RESEARCH.md section 2).
  `### check_close`, `### check_report`, and the two small helpers by their
  region titles.
- Run it: `./learn run gpu --at 00.02` (wb check: the ok line); `./wb check
  -n 6`.
- How it works: (1) `!(err <= allowed)` rather than `err > allowed`: a NaN
  compares false to everything, so only the first form calls it bad. (2) two
  equal infinities are good, and nothing is allowed around an infinite want.
  (3) "worst" is the element furthest past its own limit, err / allowed, not
  the largest error; say why (a big error on a big number can be fine). (4)
  wb fills out with NaN before calling add, so an element add never wrote
  cannot pass by luck. A small table of the special cases at the end.
- Decide the boundary: one tolerance for a whole array (ours, numpy's)
  against a bound worked out per element from the inputs (what an error
  analysis gives: tighter, and a page of algebra per function). The question:
  how small is the smallest bug you need to catch?
- Break it: the same change as 00.01's (`i < n - 1` in add.c's tail). Now
  `./wb check` prints FAIL, names [1002], and shows got nan. Then put it
  back.
- Go deeper: numpy.isclose's page (the formula, the note that it is not
  symmetric); torch.allclose's page, as RESEARCH.md records them.
- Figures: `00.02-map.svg`; `00.02-allowance.svg`, caption "What counts as
  close: the allowance around want": two number lines. Top: want = 20, a
  band from 19.997 to 20.003 labelled "atol + rtol x 20 = 0.003", a got at
  20.002 inside it marked good. Bottom: want = 0, a band from -0.001 to
  0.001 labelled "atol alone = 0.001", a got at 0.002 outside it marked bad
  (accent). Under both, in mono: rtol = 1e-4, atol = 1e-3. The generator
  computes both allowances and asserts 0.003 and 0.001.

### 00.03 Timing: warm up, repeat, count the bytes

Teaches: one run of a function is not a measurement; what the warm-up is
for; why the fastest run is the headline; and turning seconds into bytes per
second so numbers can be compared.

- The idea: time add once and the number includes things that are not add:
  the first touch of out's memory (the system hands pages over on first
  use), cold caches, whatever else the machine was doing. So: one run thrown
  away, then runs until there are enough, then the fastest. Noise only adds
  time, never removes it, so the fastest run is the closest to the function
  alone; the median beside it says how steady the machine was. Then the
  unit: n elements, 12 bytes each (two floats read, one written), divided by
  the fastest time: GB/s. Say what that number is and is not: how fast this
  loop moves bytes. add.c is built with the compiler's vectorizer off (the
  Makefile says so), so this is one float at a time; it is not the most this
  machine's memory can do.
  `### bench_now`, `### bench`, and the sort helper by its region title.
- Run it: `./learn run gpu --at 00.03` (wb time), then `./wb time -n 4096`
  and `./wb time -n 1000000`: the GB/s is not the same at every size, and
  the lesson says only that small arrays stay in the cache and large ones do
  not; module 01 is about that.
- How it works: (1) the warm-up call. (2) the stopping rule: at least
  min_runs and at least min_time, at most max_runs; why both. (3) the clock:
  monotonic, and why CLOCK_MONOTONIC_RAW (NOTES.md: macOS's CLOCK_MONOTONIC
  moves in whole microseconds). (4) the clock is a parameter of bench, so the
  arithmetic can be checked with a clock that returns chosen times.
- Decide the boundary: which number to report. Ours: the minimum, as Julia's
  BenchmarkTools prints and argues for. hyperfine prints the mean with the
  deviation and keeps the first run unless told `--warmup`; Google Benchmark
  reports means. In the words of RESEARCH.md section 3 only. The question:
  are you measuring the function, or the machine it will run on with
  everything else going?
- Break it: in bench.c delete the warm-up call `fn(arg);` and in wb.c make
  the timed runs one (the writer finds the one line that sets the options;
  if wb passes all defaults, set `o.max_runs = 1` in bench instead). Run
  `./wb time` several times: one cold run, slower and less steady than
  before. If on your run the cold run is not clearly slower, say so in your
  report and use instead: `./wb time -n 64`, which prints the "too fast for
  the clock" line, and explain it.
- Go deeper: BenchmarkTools' manual on the minimum; hyperfine's README on
  warm-up; Google Benchmark's user guide on the minimum time.
- Figures: `00.03-map.svg`; `00.03-runs.svg`, caption "One measurement:
  a run thrown away, then the fastest of the rest": a time axis; bar 1,
  dashed and muted, the longest, labelled "warm-up: not counted"; then six
  solid bars of slightly different lengths labelled "timed runs"; the
  shortest in accent labelled "the fastest: reported"; a tick on the middle
  length labelled "the median: printed beside it". No numbers on the bars.

## Module 01 - Matrix multiply on the CPU

Module README (one paragraph): one operation, the one a model spends most of
its arithmetic on, made faster four times without changing a single sum:
by the order memory is read in, by doing several floats per instruction, by
keeping the working data in the cache, by using every core; then set against
the library. Stands on module 00's checker and timer.

The numbers every lesson here needs are in NOTES.md's tables. The default
size is n = 1000.

### 01.01 Three loops and a reference

Teaches: what matrix multiply computes and how it is laid out in memory; the
reference with sums in double; why this module's checker needs a tolerance
and where its size comes from.

- The idea: c[i][j] is row i of a times column j of b, summed. Row by row
  storage: a[i][p] is `a[i * k + p]`. Worked example 2 x 3 times 3 x 2 with
  small whole numbers, one element worked out. `### matmul_ref`,
  `### matmul_ijk`. The reference keeps each sum in a double; the comment in
  matmul.c gives the reason in one line.
- Run it: `./learn run gpu --at 01.01` (mm check, then mm time): the ok line
  with its worst error, and the first row of the table every later lesson
  adds to. GFLOP/s explained: 2 m k n operations (a multiply and an add per
  term) over the fastest time, in billions.
- How it works: (1) the tolerance, rtol 1e-4 and atol 1e-3, from plans/gpu.md
  "The tolerance" and NOTES.md's measured worst errors: what the float sums
  really drift by here against what a real bug moves an element by. (2) c is
  filled with NaN before each call. (3) mm check's shapes are not all square
  and not all round: say which, and that sizes like 33 x 31 x 65 are where
  index mistakes show.
- Decide the boundary: a reference that is slower and more exact (ours: a
  double) against one that is the same arithmetic done plainly (add_ref's
  kind). With the first, every variant has one truth to be near; the cost is
  that even the plain float version does not match it exactly.
- Break it: in matmul_ijk change `p < k` to `p < k - 1` (one term dropped).
  `./mm check` fails; quote the line: the error is hundreds of times the
  allowance, not just past it. That gap is what makes the tolerance safe.
- Go deeper: numpy.isclose again for the rule; Goto and van de Geijn's paper
  as where this module is heading (title and link only).
- Figures: `01.01-map.svg`; `01.01-row-times-column.svg`, caption "One
  element of c: a row of a times a column of b": three small grids, a (2 x
  3), b (3 x 2), c (2 x 2) holding the worked example's numbers; row 1 of a
  and column 0 of b marked, c[1][0] in accent, and under them in mono the sum
  written out with its three products. Numbers computed and asserted in the
  generator: a = [[1, 2, 3], [4, 5, 6]], b = [[7, 8], [9, 10], [11, 12]],
  c[1][0] = 4*7 + 5*9 + 6*11 = 139.

### 01.02 Loop order and the cache

Teaches: the same sums in a different order run several times faster,
because of the order memory is read in.

- The idea: memory is fetched a **cache line** at a time (64 bytes on most
  machines, 128 on Apple silicon: RESEARCH.md section 7), so the float after
  the one just read is nearly free and one far away is a new fetch. ijk's
  inner loop walks down a column of b: each step is a whole row of b further
  on. Swap the two inner loops and the inner loop walks along a row of b and
  a row of c. Same products, same number of them, and each c[i][j] still
  adds its terms in the order p = 0, 1, 2..., so the answers should be ijk's
  to the last bit. Check that before writing it: `./mm check` must print the
  same worst error for ijk and ikj; if it does not, report it and do not
  claim it. `### matmul_ikj`.
- Run it: `./learn run gpu --at 01.02`: check, then the table with two rows.
  The cache sizes of the reader's own machine: the commands for macOS and
  Linux, from RESEARCH.md section 7, with the warning that on Apple silicon
  `hw.l1dcachesize` is the efficiency core's.
- How it works: (1) why c's row is zeroed first and then added to. (2)
  `aip` is read once outside the inner loop. (3) the Makefile builds this
  file with the vectorizer off, and why: lesson 01.03 comes back to it.
- Decide the boundary: fixing the order of the loops (free, and specific to
  how the matrices are stored) against storing b transposed (a copy, and
  then ijk reads rows too). Libraries do neither: they copy pieces of the
  matrices into buffers laid out in the order the inner loop reads them
  (Goto and van de Geijn call it packing; RESEARCH.md section 4).
- Break it: in mm.c change the default n from 1000 to 1024 and time ijk and
  ikj. ijk gets much slower than the 7 percent more work explains; ikj does
  not. What may be said about why: at 1024 one step down a column of b is
  exactly 4096 bytes, a whole number of memory pages and of cache lines, so
  the column's floats compete for the same few places in the cache; at 1000
  they spread out. Say that this is the known hazard of power-of-two sizes
  and that the track's default avoids it; do not give miss counts or
  associativity figures. Paste both runs.
- Go deeper: CS:APP chapter 6 (subject only); Algorithmica's matmul page,
  the part on loop order; Boehm's article, as RESEARCH.md records them.
- Figures: `01.02-map.svg`; `01.02-row-and-column.svg`, caption "A row is
  neighbours in memory; a column is a stride": a 4 x 4 matrix stored row by
  row as a strip of 16 cells numbered 0 to 15, drawn twice. Strip one,
  "ikj reads b by rows": cells 4 5 6 7 filled, bracket "one after another".
  Strip two, "ijk reads b by columns": cells 1 5 9 13 in accent with hops
  between them each labelled "+n". A small 4 x 4 grid left of each strip
  with the same cells marked. Indices computed and asserted. (The module's
  cover uses the same idea; draw this one fresh at lesson-figure size.)

### 01.03 SIMD: several floats in one instruction

Teaches: one instruction can add or multiply several floats at once; how to
write that in C without tying the code to one machine; and that the compiler
had been kept from doing it.

- The idea: a **vector register** holds several floats (8 with AVX2 on
  x86-64, 4 with NEON on arm64: state exactly what the file's own comment
  says after the code agent's final choice); one instruction works on all
  the **lanes**. ikj's inner loop is the same operation on neighbouring
  floats, which is exactly what a vector does. Two changes: the j loop takes
  a vector of columns a step with a scalar tail; and four values of p are
  taken together, so each vector of c is loaded once, gets four products
  added, and is stored once, instead of four loads and stores.
  `### the vector type` (and load, store, splat by their region titles),
  `### mul_add_tile` (the kernel: "the part of the product to do; here, all
  of it" - the ranges are used by the next two lessons, say so in one
  sentence and no more), `### matmul_simd`.
- Run it: `./learn run gpu --at 01.03`: the table with three rows.
- How it works: (1) memcpy as the load and store: the pointer need not be
  aligned, and the compiler makes it one instruction. (2) the two tails
  (columns left over, values of p left over). (3) fused multiply-add: this
  one file is built with `-ffp-contract=fast`, the others with `off`; a
  fused multiply-add rounds once where a multiply and an add round twice, so
  simd's answers differ from ijk's in the last bits, and mm check's worst
  error for simd is not ijk's: quote both lines. This is the first time the
  tolerance is needed. (4) the vector type's width against the machine's.
- Decide the boundary: the compiler's vector types (ours: one source for
  every machine, and the compiler picks the instructions) against intrinsics
  (`_mm256_fmadd_ps`, `vfmaq_f32`: exact control, one source per machine)
  against assembly (what OpenBLAS's kernels are: RESEARCH.md section 5).
- Break it: turn the compiler loose on ikj. In the Makefile remove
  `$(SCALAR)` from the rule for matmul.o, `make clean && make`, time ikj.
  With clang at -O2 it becomes vector code by itself and speeds up; with
  gcc 14 at -O2 it stays scalar and needs -O3 (NOTES.md, "Scalar means
  scalar"). Show the run on the lesson's machine, state the other compiler's
  behaviour from NOTES.md, and say what the experiment shows: ikj's order is
  what made the loop something a compiler can vectorize; ijk's inner loop is
  not (it would have to add the terms of one sum in a different order, which
  changes the rounding, and compilers do not do that unasked). Verify that
  last claim on your machine before writing it: time ijk with the vectorizer
  on. If ijk also speeds up, report it and drop the sentence.
- Go deeper: the GCC manual's page on vector extensions; CS:APP chapter 5
  (subject only); Algorithmica's page, the vectorization part.
- Figures: `01.03-map.svg`; `01.03-lanes.svg`, caption "One step of the
  inner loop: eight columns of c, four values of p": a row of 8 cells "c[i]
  [j .. j+7]" at the top with "load once" on its left; below it four rows,
  each "a[i][p] in every lane" times "b[p][j .. j+7]" with a plus sign into
  an accumulator drawn as one 8-cell row in accent; at the bottom "store
  once". If the final code uses 4 lanes on the lesson's machine, draw 8
  columns as two vectors of 4 and say so in the caption; match the code.

### 01.04 Blocking

Teaches: when the arithmetic is fast, memory is the limit; doing the multiply
a tile at a time keeps the data in use inside the cache.

- The idea: start from a measurement the reader makes: time simd at n = 500,
  1000 and 2000 and look at GFLOP/s, not ms. It falls as n grows, while
  ikj's stays the same at every size. ikj was limited by its arithmetic and
  never noticed memory; simd is fast enough to. For each row of c, simd reads
  all of b: at n = 2000 that is 16 MB, fetched again for every one of 2000
  rows. A **tile** of b, MM_BLOCK rows by MM_BLOCK columns (64 KiB at 128),
  fits in the cache nearest the core; use it for MM_BLOCK rows of c before
  moving on, and each piece of b is fetched once per tile of rows instead of
  once per row. Whether the answers are simd's to the last bit depends on
  whether each c[i][j] still gets its terms in the same order and groups:
  compare the worst-error lines `./mm check` prints for simd and blocked and
  say what you see, with the reason only if the code makes it plain.
  `### MM_BLOCK`, `### blocked_rows`, `### matmul_blocked`.
- Run it: `./learn run gpu --at 01.04`: four rows; then `./mm time -n 2000
  simd blocked`.
- How it works: (1) the three tile loops and which one is outermost, and
  why c's rows are set to 0 once, before the tiles. (2) the last tile along a
  side is smaller. (3) why 128: NOTES.md's sweep, said as a range the reader
  can test, not a law. (4) tiles around ikj were tried while this track was
  built and gained nothing (NOTES.md, "Tried and dropped"): one sentence,
  with the reason the reader has just measured.
- Decide the boundary: one tile size for every cache (ours) against the
  layered scheme of Goto and van de Geijn and of BLIS: a block for each cache
  level, and the tiles copied into contiguous buffers first (RESEARCH.md
  section 4, in its words; BLIS's five loops by name).
- Break it: change MM_BLOCK to 8, rebuild, time blocked: slower than simd.
  Change it to 100000: the same time as simd, because one tile is now the
  whole matrix. Put 128 back.
- Go deeper: Goto and van de Geijn; BLIS's documentation of its loops;
  CS:APP chapter 6 (subject only).
- Figures: `01.04-map.svg`; `01.04-tiles.svg`, caption "Without tiles every
  row of c reads all of b; with them a tile of b serves a whole band of
  rows": two panels. Left, "simd": b as one large square, c as a square with
  one thin row marked, an arrow "all of b, for this one row". Right,
  "blocked": b and c divided into 4 x 4 tiles; one tile of b in accent, a
  band of c's tile-rows marked, an arrow "this tile, for all these rows",
  and a small box "in the cache: one tile of b, one of c".

### 01.05 Threads, and the distance left to BLAS

Teaches: the rows of c are independent, so every core can take a share; and
what a real library does beyond everything in this module.

- The idea: thread t computes its own band of rows of c with blocked_rows.
  Every thread reads a and b; no two write the same element; so no lock is
  needed. Then the comparison the module has been heading to: the system's
  BLAS in the same table. `### matmul_threads`, `### thread_count`,
  `### matmul_blas`.
- Run it: `./learn run gpu --at 01.05`: the whole table, six rows with BLAS
  (or the message saying how to install one). `./mm time -t 1`, `-t 2`,
  `-t 4`: the speed-up is not the thread count; say only what the run shows
  and two reasons that are certain: the threads share the machine's memory,
  and on a machine with two kinds of core (name the lesson's machine if it
  is one) not every core is as fast.
- How it works: (1) how the rows are divided when m is not a multiple of the
  thread count, and with more threads than rows. (2) threads are created and
  joined on every call: what that costs against one multiply at n = 1000,
  measured (`./mm time -n 64 simd threads`), and that a library keeps a pool.
  (3) why splitting rows needs no lock, and what would (two threads adding
  into the same row).
- Decide the boundary: the distance left to BLAS. State the reader's own two
  numbers (blocked or threads against blas). What the library does that this
  module does not, each from RESEARCH.md sections 4 and 5 only: packing;
  a micro-kernel written per CPU in assembly or intrinsics; block sizes per
  cache level; a thread pool. For Accelerate: Apple does not document how
  cblas_sgemm is implemented; say exactly that. The question for the rest of
  the track: when do you write the kernel, and when do you call the library?
  (Module 03 asks it again on the GPU, against cuBLAS.)
- Break it: in matmul_threads.c make thread_count() return twice the number
  of cores. Time threads: not faster. If the change is within the run-to-run
  noise on your machine, show `-t` at the core count against twice it
  instead, and say so in your report.
- Go deeper: OpenBLAS's kernel directory at the pinned tag; BLIS; Apple's
  cblas_sgemm page.
- Figures: `01.05-map.svg`; `01.05-rows-to-threads.svg`, caption "Each
  thread owns a band of c's rows; all of them read a and b": a and b at the
  left as plain squares labelled "read by every thread"; c at the right cut
  into four horizontal bands labelled "thread 0" to "thread 3", band 1 in
  accent; arrows from a and b to c. Under c: "no two threads write the same
  row, so no lock".

## Covers

- Module 00's cover is redrawn (the outline's first version showed GPU
  timing, which is now lesson 02.04's subject). New cover, title "Trust the
  answer, then trust the time": top half as now but relabelled - "input"
  into "the plain version" and "the version under test", both into
  "compare: every element within its allowance?". Bottom half: 00.03-runs's
  picture in cover form (a run thrown away, six timed runs, the fastest in
  accent). Accent: the fastest run and its label.
- Module 01's cover: the row of chips at the bottom becomes "3 loops",
  "reordered", "SIMD", "blocked", "threads", then "BLAS" muted (SIMD before
  blocked).
- Both are regenerated by `art/outlines/gpu_art.py` (edit it) into
  `outlines/gpu-kernels/00/` and `01/`, then copied with their icons to the
  two module folders under `tracks/gpu/lessons/` as cover.svg and icon.svg.

## Art builders

A generator per module under `art/gpu/` (`figs00.py`, `figs01.py`; the map in
`archmap.py`, written by the module 00 builder and imported by the other),
modelled on `art/lang/` or `art/db/`. Same contract as the outline art:
styled only by the `.art` classes, ASCII, every number computed and asserted,
no measured speeds drawn, checked on the real page in light and dark with
`art/outlines/shot.py`, one accent idea a figure. Figures are 640 wide; height
as needed, up to 300.
