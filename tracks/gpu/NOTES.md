# Notes for the lesson writers

Step 1 of the track (plans/gpu.md, "Build order"): the code and tests of modules 00 and 01, on
the CPU, in C11. No lessons and no figures yet. Module 01 follows the coordinator's change of
2026-11-25: SIMD (01.03) comes before blocking (01.04), and the tiles go around the vector
kernel. Run on the owner's Mac (Apple M4 Pro, 10 performance and 4 efficiency cores, macOS
26.6.2, Darwin 25.6, Apple clang 21.0.0 (clang-2100.1.1.101), GNU Make 3.81, Python 3.12.7) and
in Docker on the same Mac: Linux arm64 (gcc 14.4.0, OpenBLAS from Debian, Python 3.13), Linux
arm64 with gcc 12.2.0 (Debian bookworm), and Linux x86-64 under Rosetta (CPU reported as
"VirtualApple @ 2.50GHz" with avx2 and fma). Function names are given instead of line numbers.

`RESEARCH.md` (hidden) is the research agent's reading of the sources the lessons cite
(llama2.c's generator, numpy.isclose, hyperfine, the matmul write-ups, BLIS, OpenBLAS,
Accelerate, the compiler manuals, cache sizes). Quote sources from there, not from here.

## What this step is built on

No code is taken from anywhere. The generator is xorshift64* written from its definition; the
research agent read llama2.c's run.c at commit 350e04fe and confirmed that rng_u32 and rng_f32
give its random_u32 and random_f32 bit for bit (RESEARCH.md 1.1; 00.01's test holds rng to the
values it recorded for seeds 1, 42 and 1234). numpy.isclose's rule is the documented one. The
matmul ladder is the common one; no line of BLIS, the Algorithmica or Boehm pages or CS:APP was
read for the code. `UPSTREAM` in track.py names vLLM, flash-attention, llama2.c and llm.c, all
`"derived": False`.

## Where the code is, lesson by lesson

```
tracks/gpu/
  Makefile           95  wb and mm; add.o and matmul.o with the vectorizer off; matmul_simd.o
                         with -ffp-contract=fast (and -march=native on x86-64); blas.o with
                         the BLAS flags; an @internal `flags` target for the tests
  rng.h rng.c    26  57  xorshift64*: rng_u32, rng_f32, rng_fill (00.01); todo() is @internal here
  add.h add.c    21  31  add_ref, add (00.01)
  wb.c              186  show (00.01), check (00.02), time (00.03)
  check.h check.c 28 90  check_result, check_close, check_report (00.02)
  bench.h bench.c 31 77  bench_opts, bench_result, bench_now, bench (00.03)
  matmul.h           74  prototypes, mul_add_tile (01.03), blocked_rows (01.04), the thread
                         count and blas_name (01.05), the table matmul_variants
  matmul.c           64  matmul_ref, matmul_ijk (01.01), matmul_ikj (01.02)
  matmul_simd.c     115  LANES, vec, load, store, splat, mul_add_tile, matmul_simd (01.03)
  matmul_blocked.c   46  MM_BLOCK, blocked_rows, matmul_blocked (01.04)
  matmul_threads.c   75  thread_count, matmul_threads: blocked_rows on each share (01.05)
  blas.c             56  matmul_blas (01.05)
  mm.c              278  list, check, time (01.01 on)
  track.py          567  settings, fixtures, run and bench hooks, the timeline
  tests/             a test per lesson; rng_, add_, check_, bench_ and matmul_driver.c
  RESEARCH.md        the research notes (hidden)
  lessons/           placeholders only (see "Placeholders")
```

Those are the lines as the track holds them; the site shows each without its markers and
instruction comments (at 01.05: wb.c 174, mm.c 262, matmul.c 58, matmul_simd.c 97,
matmul_blocked.c 42, matmul_threads.c 69, matmul.h 64, Makefile 78).

The regions (`./learn solution gpu NN.LL` prints them):

| lesson | file: region title |
|---|---|
| 00.01 | rng.c: xorshift64*: the next 32 bits; a float in [0, 1); an array from a seed. add.c: add_ref: one element at a time; add: four at a time, then the tail. wb.c: a row of values; wb show |
| 00.02 | check.c: how far past the limit; which of two elements is worse; check_close: each element against its allowance; check_report: one line. wb.c: wb check |
| 00.03 | bench.c: bench_now: a clock that only goes forward; the order of two times; bench: warm up, repeat, sort the times. wb.c: one call of add, as bench calls it; wb time |
| 01.01 | matmul.c: matmul_ref: each sum kept in a double; matmul_ijk: three loops. mm.c: mm check; one call of a variant, as bench calls it; mm time |
| 01.02 | matmul.c: matmul_ikj: the inner loop along the rows |
| 01.03 | matmul_simd.c: a vector of floats in; a vector of floats out; one float in every lane; mul_add_tile: a vector of columns and four values of p a step; matmul_simd: c set to 0, then the whole product at once |
| 01.04 | matmul_blocked.c: blocked_rows: the rows, a tile at a time; matmul_blocked: every row |
| 01.05 | matmul_threads.c: how many threads; one thread's share; matmul_threads: the rows split between threads. blas.c: matmul_blas: one call to the library |

mul_add_tile(a, b, c, k, n, i0, i1, p0, p1, j0, j1) adds to c[i][j], for i in [i0, i1) and j in
[j0, j1), the sum over p in [p0, p1) of a[i][p] * b[p][j]: vectors of LANES along j, four values
of p a step, scalar tails for both. matmul_simd sets c to 0 and calls it once over everything.
blocked_rows(a, b, c, k, n, i0, i1) sets rows [i0, i1) of c to 0 and calls it on each tile of
MM_BLOCK rows by MM_BLOCK values of p by MM_BLOCK columns (tiles in i, p, j order).
matmul_blocked is blocked_rows over all rows; each thread of matmul_threads runs blocked_rows on
its share of the rows.

What a lesson adds outside its regions, through `@from` ("Also added in this lesson" on the
site): 00.02 wb.c's `math.h` and `check.h`, the `check` command and its usage line, the
Makefile's check.c; 00.03 wb.c's `bench.h`, struct add_args, the `time` command and its usage
line, the header comment's wb time line, the Makefile's bench.c; 01.01 the Makefile's mm, MM and
matmul.o; 01.02 to 01.05 each variant's prototype and table entry in matmul.h; 01.03
mul_add_tile's prototype, the Makefile's SIMD flags and matmul_simd.o; 01.04 blocked_rows's
prototype and the Makefile's matmul_blocked.c; 01.05 MAX_THREADS, matmul_thread_count,
thread_count and blas_name in matmul.h, mm's -t (option, usage, the threads line of mm time),
missing() and its calls (blas without a BLAS), the blas line of mm list, the Makefile's BLAS
detection, blas.o, matmul_threads.c and -pthread.

A cut region stops its program with `gpu: NN.LL: <title> not written yet`, status 3, from
todo() (@internal in rng.c, which every program and driver links; declared @internal in each
header). In the project as the site shows it at a lesson there is no stub: what a later lesson
brings is a usage error (`wb check` before 00.02 and `wb time` before 00.03 print wb's usage,
status 2; `mm time -t 2` before 01.05 prints mm's; `mm time blocked` before 01.04 says `mm: no
variant called 'blocked' (mm list names them)`). With 01.03 cut out, 01.04's and 01.05's tests
fail at 01.03's stub too (they run the kernel); each lesson's own test fails at its own stub.

## What the programs print

wb (`wb.c`), status 2 for every usage error:

- `wb show [-n N] [-s SEED]`: `n = 1003, seed = 1`, then `a`, `b` and `add` rows: the name in 4
  columns and up to four values as ` %10.6f`. n is 1003 (a tail of three after four a pass), the
  seed 1; b's seed is the seed + 1.
- `wb check [-n N] [-s SEED]`: check_report's line for `add`, rtol = atol = 0; status 1 on a
  failure. add's output starts as NaN.
- `wb time [-n N]`: `add: n = 16777216, R runs, min M ms, median D ms, G GB/s` (M and D as
  %.4g, G as %.1f, 12 bytes an element); when the fastest run reads 0 on the clock, `too fast
  for the clock: try a larger -n` instead of the GB/s. Seeds 1 and 2.
- Errors: `wb: -n wants a whole number from 1 to 268435456, not 'X'`; `wb: -s wants a whole
  number from 1 to 4294967295, not 'X'`; `wb: -s 0: xorshift's state 0 never changes, so every
  number would be the same; a seed is 1 to 4294967295` (the seed limit keeps b's seed, one
  more, from wrapping to 0). Anything else prints the usage lines.

check_report (check.c), one line:

- `NAME: ok, worst error E at [I] of N (allowed A)` (E and A as %.3g), status 0;
- `NAME: ok, no elements to compare` for n = 0;
- `NAME: FAIL, B of N wrong; worst at [I]: got G, want W (error E, allowed A)` (G and W as
  %.9g, so every float shows exactly), status 1.

The worst element is the one furthest past its limit: the largest err / allowed (err > 0 with
nothing allowed is infinitely far), a NaN beating everything, at equal distance the larger
error, a tie keeping the first. So for an ok result it is the element closest to its limit, not
the largest error: mm check's "worst error" is that element's error.

mm (`mm.c`), status 2 for every usage error:

- `mm list`: one variant a line, in the table's order (ijk, ikj, simd, blocked, threads, blas);
  blas as `blas (Accelerate)` or `blas (OpenBLAS)`, or left out with `mm: blas: make found no
  BLAS library. On Debian or Ubuntu: sudo apt install libopenblas-dev pkg-config, then make
  clean && make` on stderr.
- `mm check [-t T] [name...]`: per variant, check_report's line labelled `%-7s MxKxN`: the first
  of the shapes 1x1x1, 3x5x7, 8x8x8, 33x31x65, 64x64x64, 100x200x50, 129x65x63, 256x256x256 it
  fails on, or if none the last; status 1 if any failed. c starts as NaN.
- `mm time [-n N] [-t T] [name...]`: `n = N` (1000 unless -n says otherwise); `threads = T` when
  the threads variant runs; the header `variant      min ms    GFLOP/s  vs ijk`; a row a variant:
  `%-8s %10.3f %10.2f`, then ` %6.1fx` (ijk's fastest run over this one's) or `-` when ijk was
  not timed in this run. Names pick variants; they still run in the table's order.
- Errors: `mm: -n wants a whole number from 1 to 8192, not 'X'`, the same for -t (1 to 256),
  `mm: no variant called 'X' (mm list names them)`; -n only with time, -t only with check and
  time; anything else prints the usage lines.

`./learn run gpu` runs the lesson's sample: `./wb show` (00.01), `./wb check` (00.02), `./wb
time` (00.03), `./mm check && ./mm time` (01.01 on). `./learn bench gpu` runs `./mm time`
(`./wb time` at 00.03; before that it says there is nothing to time yet).

## Where this departs from plans/gpu.md, and why

- **Module 01's order** (the coordinator's change, from the measurements in "Tried and dropped"):
  ijk, ikj, simd (01.03), blocked (01.04), threads (01.05). The scalar matmul_blocked is gone; the
  tiles go around the vector kernel, mul_add_tile. plans/gpu-outline.md has the titles swapped and
  module 01's "You build" in the new order.
- **The seed is the state** (coordinator, from the research): rng_fill starts the generator at the
  seed itself, as llama2.c does. State 0 is the generator's trap (it stays 0, every number is 0);
  rng_u32 stays the raw generator and its comment says so, rng_fill does not remap, and wb refuses
  `-s 0` with the reason, status 2. wb's seeds are 1 to 4294967295, so that b's seed (one more)
  never wraps to 0. mm takes no seed (a and b are always seeds 1 and 2).
- **Floating-point contraction** (coordinator): every file is built with `-ffp-contract=off`
  except matmul_simd.c, built with `-ffp-contract=fast`. So the scalar variants round the same
  on every compiler (Apple clang's default `on` fuses `sum += a * b`; GCC 14 with -std=c11 does
  not), and the vector kernel uses fused multiply-adds where the machine has them.
- **The vectorizer flags** are one spelling for both compilers, `-fno-tree-vectorize
  -fno-tree-slp-vectorize` (Apple clang rejects GCC's `-fno-tree-loop-vectorize`), on add.c and
  matmul.c, each built on its own (add.o, matmul.o). matmul_blocked.c has no arithmetic of its
  own and is built with the plain flags.
- **BLAS flags only for blas.c** (blas.o); `-DACCELERATE_NEW_LAPACK` is among them on macOS.
- **No `make SANITIZE=1`.** As the brief said, the sanitizer build is lang's pattern, outside the
  track: track.py builds the programs and drivers with ASan and UBSan when GPU_SANITIZE=1, with
  the flags the Makefile reports (`make -s flags`, an @internal target). 01.05's test always runs
  matmul_threads under ThreadSanitizer as well (GPU_TSAN=0 leaves that out, for x86-64 under
  Rosetta, where TSan cannot run).
- **bench_now reads CLOCK_MONOTONIC_RAW**, not CLOCK_MONOTONIC: on macOS CLOCK_MONOTONIC moves in
  whole microseconds (clock_getres says 1000 ns; the smallest step seen was 999.9 ns). RAW steps
  by 41 ns on this Mac and in the Linux container. bench.c and matmul_threads.c define
  `_DEFAULT_SOURCE`: a strict C11 build hides clock_gettime and _SC_NPROCESSORS_ONLN on glibc,
  and `_POSIX_C_SOURCE` would hide _SC_NPROCESSORS_ONLN and CLOCK_MONOTONIC_RAW on macOS.
- **wb time** prints `too fast for the clock: try a larger -n` instead of a GB/s when the fastest
  run reads 0. wb's default n is 1003 for show and check (1003 leaves a tail of three), 2^24 for
  time; -n is 1 to 2^28.
- **check_close's allowance for a non-finite want is 0**: an infinity is close only to the same
  infinity (numpy.isclose: `... & isfinite(y) | (x == y)`), and a NaN want to nothing. The rule
  is written `!(err <= allowed)` so a NaN error counts as bad.
- **mm check** prints one line a variant: the first of its shapes the variant fails on, or the
  largest when it passes them all.
- **mm time**: names choose variants but they run in the table's order, so ijk comes first and
  "vs ijk" can be filled in; without ijk that column is `-`. mm time does not check before it
  times; the lessons run `./mm check && ./mm time`.
- **mm's default n is 1000** (coordinator): round, not a power of two (see "The power-of-two
  cliff"). `./mm check && ./mm time` at 1000 takes 7.1 s on the Mac and 8.3 s with gcc, under
  the 30 s limit.
- **The thread count**: the fixed signature has no room for it, so matmul.h has `int
  matmul_thread_count` (mm -t sets it) and `int thread_count(void)` (that, or the cores online,
  at most MAX_THREADS = 256). A thread that cannot be created has its rows done by the caller.
- **blas_name** (`const char *`, NULL when make found no BLAS) tells mm whether blas can run;
  without one blas.c still defines matmul_blas, which says so and exits if it is ever called.
  matmul_blas passes leading dimensions of at least 1, so a side of 0 is legal.
- **Sizes**: the "set c to 0" loops count in size_t; the indexes elsewhere are ints, so matmul.h
  says each matrix must have fewer than 2^31 elements (8 GiB of floats). mm allows n up to 8192.
- **MM_BLOCK is 128**, in matmul_blocked.c (not shared: the threads call blocked_rows). See the
  sweep.
- **The vector is the machine's own width** (coordinator, 2026-11-26, on the trial's numbers): 8
  floats with `__AVX2__`, 4 otherwise, one constant LANES; the splat is a loop over the lanes.
  The plan's "vectors of 8 floats ... one source for AVX2 and NEON" is now "one source, each
  machine's width" (see "Vector width").
- **matmul_variants** ends with a `{NULL, NULL}` entry instead of a count macro.
- **The test drivers** (tests/*.c, never shown) are C programs the tests feed with commands;
  track.py compiles them from the tree's sources with the Makefile's flags for each file.
- **Placeholders** were needed for `./learn check` (see the next section).

## Placeholders

`./learn check` reports "test has no lesson doc" for every test without a lesson, and its static
verify checks every doc not listed as pending. So that check stays clean, this step created:

```
tracks/gpu/lessons/00-the-workbench/00.01-a-first-function-and-the-plain-version-you-trust.md
tracks/gpu/lessons/00-the-workbench/00.02-right-before-fast-checking-against-a-reference.md
tracks/gpu/lessons/00-the-workbench/00.03-timing-warm-up-repeat-count-the-bytes.md
tracks/gpu/lessons/01-matrix-multiply-on-the-cpu/01.01-three-loops-and-a-reference.md
tracks/gpu/lessons/01-matrix-multiply-on-the-cpu/01.02-loop-order-and-the-cache.md
tracks/gpu/lessons/01-matrix-multiply-on-the-cpu/01.03-simd-several-floats-in-one-instruction.md
tracks/gpu/lessons/01-matrix-multiply-on-the-cpu/01.04-blocking.md
tracks/gpu/lessons/01-matrix-multiply-on-the-cpu/01.05-threads-and-the-distance-left-to-blas.md
tracks/gpu/lessons/verify-pending.txt      all eight ids
```

Each doc is front matter (id, title, `labels: with code`), the `# NN.LL Title` heading and one
line saying it is a placeholder. There are no module READMEs, so the site names the modules from
their folders: "The workbench" and "Matrix multiply on the cpu" (lower case, until a README gives
the title). The lesson writers replace each doc whole and take its line out of verify-pending.txt
once `./learn verify gpu NN.LL` passes.

## Scalar means scalar: what the disassembly shows

matmul.c (and add.c) are built with `-fno-tree-vectorize -fno-tree-slp-vectorize
-ffp-contract=off`; matmul_simd.c with `-ffp-contract=fast` (and `-march=native` on x86-64).
Read with `otool -tv` on the Mac and `objdump -d` in the containers (before the redesign and before vec
became the machine's width; ikj is the same code now):

| compiler, target | matmul.o (matmul_ikj's inner loop) | matmul_simd.o |
|---|---|---|
| Apple clang 21.0.0, arm64 | `fmul s1, s1, s2` + `fadd s0, s0, s1`: scalar, not fused; no vector arithmetic in the file (only `movi.2d v0, #0`, which zeroes a register) | `fmla.4s` (fused, 4 lanes; then two per vec8) |
| gcc 14.4.0, Linux arm64 | `fmul s30, s31, s30` + `fadd s29, s29, s30`; no vector arithmetic in the file | `fmla v.4s`; with vec8, splat8 built through the stack (stores of pairs of floats, loads of vector pairs) |
| gcc 14.4.0, Linux x86-64 (Rosetta) | `mulss` + `addss`; no packed arithmetic | `vfmadd132ps` on `ymm` (AVX2 + FMA from -march=native) |

Without the two flags (same -O2, contraction off):

- Apple clang 21 vectorizes ikj's inner loop by itself: four `fmul.4s` and four `fadd.4s` a
  pass, 16 floats (with clang's default contraction, four `fmla.4s`). This is the plan's
  "quietly turns 01.02's loop into 01.03's", and what 01.03 can have the reader see by deleting
  `$(SCALAR)` from matmul.o's rule.
- gcc 14.4 at -O2 leaves ikj scalar even without the flags: its -O2 cost model ("very cheap")
  does not allow the run time overlap check the loop needs. At -O3 gcc vectorizes it; with the
  two flags it stays scalar at -O3 too. So the flags matter for clang at -O2 and gcc at -O3.

Contraction: with `-ffp-contract=fast` matmul_simd.o has fused instructions on every compiler
above; built with `-ffp-contract=off` instead, gcc's has none. The Makefile has been seen to work
with Apple clang 21.0.0, gcc 14.4.0 and gcc 12.2.0, and GNU Make 3.81 (macOS) and 4.x (Debian).
Nothing older was tried; gcc before 12 does not vectorize at -O2 at all (RESEARCH.md 6.1).

## Bugs found while building, and the test that holds each

- **macOS's CLOCK_MONOTONIC moves in whole microseconds** (clock_getres 1000 ns; smallest step
  seen 999.9 ns). A 4096-element add then timed as 0 or 0.001 ms. bench_now reads
  CLOCK_MONOTONIC_RAW (41 ns steps). 00.03: bench_driver's `steps` must find a step under 250 ns
  and never a step back; `wb time -n 4096` must have min > 0, min <= median and a GB/s that
  matches 12 bytes x n over min; `wb time -n 1` never prints inf or nan. Put CLOCK_MONOTONIC
  back and 00.03 fails ("bench_now's smallest step is 1000 ns").
- **A zero leading dimension aborts Accelerate.** `cblas_sgemm` with k = 0 and lda = 0 prints
  "lda must be >= MAX(K,1): lda=0 K=0. BLAS error: Parameter number 9 passed to cblas_sgemm had
  an invalid value" and the program exits with status 255. matmul_blas passes at least 1. 01.05:
  check_variant("blas") runs the shapes with a side of 0; with lda = k it fails with that message.
- **Accelerate's cblas_sgemm is deprecated without -DACCELERATE_NEW_LAPACK** (macOS 13.3 on), so
  -Werror fails on blas.c. The Makefile's BLAS flags carry it. 00.01: warnings() compiles every
  source with -Werror and the Makefile's flags for it, blas.c with BLAS.
- **Feature macros differ**: on glibc a strict -std=c11 build hides clock_gettime and
  _SC_NPROCESSORS_ONLN; on macOS `_POSIX_C_SOURCE` hides _SC_NPROCESSORS_ONLN and
  CLOCK_MONOTONIC_RAW. `_DEFAULT_SOURCE` works on both. The suite builds and passes on both.
- **Seed 0 and the wrap of b's seed.** State 0 gives 0 for ever; with seeds up to 2^64 - 1, b's
  seed (one more) could wrap to 0. 00.01: rng_driver with state 0 gives `u32 0 0 0`, f32 0 and
  rng_fill -1; `wb show -s 0` is refused with its reason; `-s 4294967296` is out of range.
- **Rosetta**: x86-64 under Rosetta cannot run ThreadSanitizer ("FATAL: ThreadSanitizer:
  unexpected memory mapping 0x800000000000-0x800000026000"), and with GPU_SANITIZE=1 one `mm time
  -n 64 simd` process hung in LeakSanitizer's exit-time check (two processes, 0.8% CPU, 7 minutes)
  until killed; with `ASAN_OPTIONS=detect_leaks=0` it passed. Those are the emulator's, not the
  code's: GPU_TSAN=0 leaves TSan out, and x86-64 sanitizer runs are owed on the GPU machine.

The new kernel and band functions have tests of their own through the driver (01.03: 76
mul_add_tile tiles, in the middle, at the edges, of every width relative to a vector and a group
of four values of p, and empty or backwards ranges in i, p and j; 01.04: blocked_rows on bands
in the middle, at either end, of one row and of none). c is filled with a pattern; outside the
tile or band every element must be unchanged bit for bit, inside it within the tolerance of the
partial sums. Nothing new was found by them; they were checked by mutation.

Checked by mutation (each change made, the named test failed, the change undone): check_close
counting a NaN as good (00.02, "NaN in got"); check_close without the `g == w` case (00.02, "+inf
against +inf"); add's tail running to `i <= n` (00.01, "wrote past out[n - 1]"); two threads
sharing a row (01.05, values doubled); an unlocked counter in run_share (01.05, "ThreadSanitizer:
data race"); lda = k (01.05); CLOCK_MONOTONIC (00.03); mul_add_tile skipping its first value of p
(01.03, every tile outside the tolerance); mul_add_tile's column tail stopping one short (01.03,
4 of 72 elements of a tile wrong).

## Claims the lessons can make, and their sources

- "rng is the generator llama2.c samples with": confirmed by the research agent from run.c at
  commit 350e04fe (RESEARCH.md 1.1): same shifts (12 right, 25 left, 27 right), same multiplier,
  the top 32 bits, the float as `(u32 >> 8) / 16777216.0f`, the seed used as the state. 00.01's
  test holds rng_u32 and rng_f32 to the four values it recorded for seeds 1, 42 and 1234.
  llama2.c itself never runs with seed 0 (it replaces a seed <= 0 with the time). Do not say
  run.c is "700 lines": it is 973 at that commit (RESEARCH.md 1.1).
- check_close's rule is numpy.isclose's, with want as numpy's b (the reference): not symmetric
  (RESEARCH.md 2.1). numpy's defaults (rtol 1e-5, atol 1e-8) are not this track's.
- hyperfine prints no median in the terminal (RESEARCH.md, "Could not confirm").
- This Mac's performance cores have a 128 KiB L1d and a 16 MiB L2 shared by 5 cores, 128-byte
  lines; `hw.l1dcachesize` (64 KiB) is the efficiency cores' value (RESEARCH.md 7.1).
- How Accelerate gets its speed is not documented (RESEARCH.md 5.2): do not name a unit.

## The measurements, and the load

Every figure below is the fastest run (`mm time`'s min ms, GFLOP/s in brackets) unless it says
otherwise. `uptime` was run before each set; the Docker VM reports its own load but shares the
Mac's cores, so the Mac's is given for the Linux runs too.

- Mac, 2026-11-25 17:54 to 17:59 (vec8): load average 4.7 before, 7.5 at the most, 2.0 after.
- Linux container (gcc 14.4.0, OpenBLAS), 2026-11-26 09:29 to 09:45 Mac time (vec8): the Mac's
  load 21.8 before (another session had started), 14.2 after; the VM's 2.9 before, 3.5 after.
- The vector width trial: 2026-11-25 17:51 to 17:53, Mac load 5.3 to 5.2; the container right
  after it, VM load 0.9 to 1.9.
- After the change to the machine's width (n = 1000 and 2000 only), 2026-11-26: Mac 10:00 to
  10:01, load 16.9 to 26.6; Linux 10:02 to 10:04, Mac load 33.9 to 32.9 (VM 17.7 to 14.0), and
  n = 1000 again at 10:07, Mac load 21.5 to 19.2 (VM 15.4).

### mm time, every variant: the vector at the machine's width (LANES 4 on arm64)

| | ijk | ikj | simd | blocked | threads | blas |
|---|---|---|---|---|---|---|
| Mac, 1000 | 742.8 (2.69) | 308.5 (6.48) | 46.1 (43.4) | 32.1 (62.2) | 6.26 (319) | 0.582 (3438) |
| Mac, 2000 | 5959.9 (2.68) | 2445.0 (6.54) | 492.8 (32.5) | 312.1 (51.3) | 86.6 (185) | 5.10 (3140) |
| Linux, 1000, second run | 632.6 (3.16) | 266.8 (7.50) | 44.8 (44.6) | 30.5 (65.6) | 4.67 (429) | 5.59 (358) |
| Linux, 1000, first run | 957.7 (2.09) | 324.7 (6.16) | 52.5 (38.1) | 34.6 (57.8) | 40.0 (50.0) | 45.6 (43.8) |
| Linux, 2000 | 7720.7 (2.07) | 2568.4 (6.23) | 642.6 (24.9) | 362.5 (44.1) | 130.3 (123) | 305.0 (52.5) |

The Mac was much busier than in the vec8 tables below (load 17 to 34 against 2 to 7), so the
scalar rows and the threaded ones (threads, and both BLAS libraries, which use every core) are
slower; the first Linux run at 1000, under the heaviest load, had threads and OpenBLAS ten times
slower than the second. Compare variants within a row, not rows across tables.

### mm time, every variant: with vec8 (before the change)

Mac, Apple clang 21.0.0, Accelerate, 14 threads:

| n | ijk | ikj | simd | blocked | threads | blas |
|---|---|---|---|---|---|---|
| 768 | 276.6 (3.28) | 120.4 (7.53) | 20.2 (44.8) | 15.2 (59.7) | 2.21 (410) | 0.269 (3366) |
| 1000 | 628.1 (3.18) | 268.5 (7.45) | 45.5 (43.9) | 31.0 (64.6) | 4.65 (430) | 0.583 (3430) |
| 1024 | 999.6 (2.15) | 292.9 (7.33) | 53.3 (40.3) | 60.3 (35.6) | 8.01 (268) | 0.709 (3028) |
| 2000 | 5751.2 (2.78) | 2185.5 (7.32) | 485.0 (33.0) | 267.3 (59.9) | 32.7 (489) | 4.95 (3235) |
| 2048 | 10680.1 (1.61) | 2169.8 (7.92) | 422.6 (40.7) | 437.1 (39.3) | 50.4 (341) | 4.98 (3450) |

Linux arm64 in Docker, gcc 14.4.0, OpenBLAS, 14 threads:

| n | ijk | ikj | simd | blocked | threads | blas |
|---|---|---|---|---|---|---|
| 768 | 477.2 (1.90) | 109.2 (8.29) | 18.9 (47.9) | 26.8 (33.8) | 3.95 (230) | 1.97 (460) |
| 1000 | 651.8 (3.07) | 243.7 (8.21) | 40.8 (49.0) | 71.7 (27.9) | 10.7 (186) | 4.22 (474) |
| 1024 | 3833.6 (0.56) | 265.8 (8.08) | 49.8 (43.1) | 77.1 (27.9) | 10.2 (210) | 4.44 (483) |
| 2000 | 4732.1 (3.38) | 2003.3 (7.99) | 443.9 (36.1) | 514.1 (31.1) | 53.3 (300) | 25.5 (628) |
| 2048 | 97297.3 (0.18) | 2478.2 (6.93) | 622.1 (27.6) | 886.2 (19.4) | 114.5 (150) | 53.4 (322) |

### The ladder: ijk > ikj > simd > blocked > threads, in time

With the vector at the machine's width:

| | n = 1000 | n = 2000 |
|---|---|---|
| Mac, clang | **holds**: 742.8 > 308.5 > 46.1 > 32.1 > 6.26 | **holds**: 5959.9 > 2445.0 > 492.8 > 312.1 > 86.6 |
| Linux, gcc | **holds** (second run): 632.6 > 266.8 > 44.8 > 30.5 > 4.67. In the first run, under load 34, threads (40.0) was slower than blocked (34.6) | **holds**: 7720.7 > 2568.4 > 642.6 > 362.5 > 130.3 |

With vec8 it held on the Mac and failed with gcc at blocked (71.7 against simd's 40.8 at 1000,
514.1 against 443.9 at 2000): gcc built splat8 through the stack, four times for every four
values of p in every row of every tile, so the smaller the tile, the more it cost (the sweep:
gcc's vec8 blocked is 203 ms at MM_BLOCK 32 against 47 ms with no tiles at n = 1000). On the Mac
the ladder also fails at the power-of-two sizes (vec8 tables): at 1024 and 2048 blocked (60.3,
437.1) is slower than simd (53.3, 422.6). Nothing was tuned but MM_BLOCK and the vector width.

### The power-of-two cliff: ijk at 1000 against 1024

(vec8 sessions; ijk does not use the vector.)

| | n = 1000 | n = 1024 | n = 2000 | n = 2048 |
|---|---|---|---|---|
| Mac, clang | 628.1 ms (3.18) | 999.6 ms (2.15) | 5751 ms (2.78) | 10680 ms (1.61) |
| Linux, gcc | 651.8 ms (3.07) | 3833.6 ms (0.56) | 4732 ms (3.38) | 97297 ms (0.18) |

7% more work at 1024 takes 1.6 times as long with clang and 5.9 times with gcc; at 2048 (7% more
than 2000), 1.9 and 21 times. At those sizes each step down a column of b is a multiple of 4
KiB; ikj, which reads along rows, does not see it (268.5 against 292.9 on the Mac). Why gcc's ijk
suffers so much more than clang's was not looked into: both inner loops are a scalar load, a
multiply and an add.

### MM_BLOCK: the sweep, blocked only, and the default (128)

`mm time -n N blocked` on copies of the track with MM_BLOCK changed in matmul_blocked.c; 100000
means no tiles (one tile holds everything, as in simd). With vec8, the same sessions as the vec8
tables; not repeated after the change of width (on the Mac the change made no difference, see
"Vector width").

| MM_BLOCK | Mac 1000 | Mac 2000 | Linux 1000 | Linux 2000 |
|---|---|---|---|---|
| 32 | 47.0 | 388.0 | 203.1 | 1555.1 |
| 48 | 42.2 | 343.3 | 140.9 | 1128.9 |
| 64 | 42.8 | 352.3 | 126.3 | 1045.7 |
| 96 | 29.8 | 238.8 | 94.9 | 710.6 |
| 128 | **28.7** | **231.4** | 78.2 | 580.7 |
| 192 | 52.6 | 409.8 | 69.8 | 552.1 |
| 256 | 49.4 | 432.2 | 58.0 | 523.2 |
| no tiles | 42.8 | 374.5 | 47.4 | 649.0 |
| simd, same session | 42.6 | 376.2 | 52.3 | 628.2 |

128 is the Mac's best at both sizes, 1.5 times faster than no tiles at 1000 and 1.6 at 2000;
96 is close and 192 is worse than no tiles. gcc's column is vec8's splat cost, gone with the
machine's width (its blocked at 1000 went from 78 to 31 ms at 128). A 128 x 128 tile of floats is
64 KiB, half a performance core's L1d. The default stays 128.

### Vector width: the machine's own (adopted)

Two candidates were tried against vec8, each a whole matmul_simd.c: (A) a vector of the
machine's width, 8 floats when `__AVX2__` is defined and 4 otherwise, one constant LANES, splat
as a loop over the lanes, j one vector a step; (B) the same with j two vectors a step. Best of
three interleaved rounds, `mm time -n N simd blocked`, ms:

| | simd 1000 | blocked 1000 | simd 2000 | blocked 2000 |
|---|---|---|---|---|
| clang, vec8 | 47.6 | 32.0 | 473.7 | 260.2 |
| clang, A | 47.3 | 32.6 | 493.6 | 263.3 |
| clang, B | 46.9 | 32.1 | 472.3 | 261.4 |
| gcc, vec8 | 47.2 | 77.2 | 525.0 | 605.2 |
| gcc, A | 48.7 | **32.3** | 529.4 | **263.2** |
| gcc, B | 53.2 | 40.5 | 509.4 | 297.0 |

The first rule was: adopt if gcc-arm64's simd and blocked both get at least 20% faster at n =
1000 and clang-arm64's no more than 10% slower. With A gcc's blocked is 2.4 times faster and
clang unchanged (within 2%), but gcc's simd is not faster: simd calls the kernel once with whole
rows, so the splat is rare there. The coordinator relaxed the rule to blocked alone (2026-11-26),
and A is what matmul_simd.c now is. On arm64 a vec is one NEON register of 4 floats; on x86-64
with AVX2 one ymm register of 8 (under Rosetta, `vfmadd...ps` on `ymm` in matmul_simd.o, and the
suite passes there with LANES 8); on x86-64 without AVX2 one SSE register of 4. The tests'
shapes cover sides around both 4 and 8. In the disassembly the splat's loop over lanes stays in
registers on both compilers: clang multiplies by a lane of a register (`fmla.4s v, v, v[0]`),
gcc fills the lanes with `mov v.s[1..3], v.s[0]`; no float goes through the stack.

### Tried and dropped: tiles around the scalar loop

The first design had a scalar matmul_blocked (ikj over tiles, in matmul.c) as 01.03, before simd.
It never beat ikj. Measured with MM_BLOCK 128 (Mac load 13.7 to 22.3; Linux the same evening):

| n | Mac ikj | Mac scalar blocked | Linux ikj | Linux scalar blocked |
|---|---|---|---|---|
| 512 | 41.3 | 47.5 | 41.6 | 49.0 |
| 768 | 134.6 | 144.8 | 132.6 | 160.8 |
| 1024 | 287.2 | 343.4 | 312.8 | 381.5 |
| 2048 | 2538.8 | 3051.0 | 2510.4 | 3184.1 |

In a sweep of MM_BLOCK 32 to 256 at n = 768, 1024 and 2048 it lost to ikj in 38 of 42 runs (the
4 it won were runs where ikj itself was 17 to 46% slower than its other runs at that n). The
coordinator's measurement of the vector kernel on the Mac, MM_BLOCK 128 against no tiles: n =
768 17.7 against 21.6 ms; 1000 32.8 against 49.4; 1536 214.5 against 216.0; 2000 268.7 against
519.2; ikj 6.8 to 7.4 GFLOP/s at every n. So the scalar loop is limited by its arithmetic and
tiles cannot help it; once the arithmetic is in vectors, memory is the limit and tiles pay.

### The worst error against matmul_ref, at n = 2000

The largest |got - want| over all of c, and the largest |got - want| / (1e-3 + 1e-4 |want|) (1
would be at the tolerance), seeds 1 and 2 (a scratch program, build-gpu/errs.c). The Mac and
Linux give the same figures for every variant of ours: with contraction off the scalar variants
round the same, and the kernel fuses on both. simd and blocked were measured again with the
vector at the machine's width (4 lanes on arm64), on both: the same figures to the digit, fused
and with -ffp-contract=off.

| variant | Mac | Linux |
|---|---|---|
| ijk, ikj | 1.79e-04, 0.0652 | 1.79e-04, 0.0652 |
| simd, blocked, threads (fused) | 1.91e-04, 0.0685 | 1.91e-04, 0.0685 |
| simd, blocked built with -ffp-contract=off | 1.79e-04, 0.0652 | 1.79e-04, 0.0652 |
| blas | 1.91e-04, 0.0685 (Accelerate) | 5.72e-05, 0.0430 (OpenBLAS) |

The worst is 0.069 of the allowance, far from the factor of 3 (0.33) at which the plan says to
stop; the largest want is 73.3, so rtol carries most of the allowance. Fused or not, the worst
error moves by 5 to 7%: fusing changes the last bits, as 01.03 can say, and the tolerance does not
notice. blocked and threads equal simd bit for bit (01.04's and 01.05's tests check it).

### wb time, and how long each lesson's commands take

`wb time` (n = 2^24, 12 bytes an element): Mac 57.8 to 59.6 GB/s (min 3.38 to 3.49 ms, medians
3.6 to 5.1 ms, 41 to 129 runs, load 13.7 to 22.3); Linux container 36.7 to 45.2 GB/s (min 4.45
to 5.48 ms). add.c is built with the vectorizer off, so this is how fast that scalar loop moves
bytes, not the machine's memory speed: a lesson must say "the speed of this loop", and must not
present it as what the memory can do. (No vectorized add was timed for comparison.)

`./mm check && ./mm time` at n = 1000, at each lesson of module 01, wall clock (the project as
the site shows it there: `./learn files gpu --at NN.LL`):

| lesson (variants) | Mac | Linux, gcc |
|---|---|---|
| 01.01 (ijk) | 3.4 s | 4.2 s |
| 01.02 (+ ikj) | 5.0 s | 6.1 s |
| 01.03 (+ simd) | 5.5 s | 6.5 s |
| 01.04 (+ blocked) | 6.1 s | 7.0 s |
| 01.05 (+ threads, blas) | 7.1 s | 8.3 s |

Module 00's samples: `./wb show` and `./wb check` 0.01 s, `./wb time` 0.6 s on both.

Threads (the earlier session, Mac load 24 to 28, `mm time -t T threads`, min ms): at 768, 4
threads 4.53, 10 threads 2.55, 14 threads 2.36; at 1024, 16.6, 6.99 and 8.90 (then over
matmul_simd, before the redesign). With 14 threads 4 run on the efficiency cores and every
thread has as many rows, so the slow cores can set the time. Rows split evenly is the plan's
design and was kept.

## Where the suite has passed

With the code as committed: `./learn test gpu`, `GPU_SANITIZE=1 ./learn test gpu` (ASan and
UBSan), `./learn check-skeleton gpu`, `./learn check-timeline gpu`:

- Mac, Apple clang 21.0.0, Accelerate: all pass; 01.05 runs matmul_threads under ThreadSanitizer
  on 1, 2, 3, 7, 64 and 256 threads. `./learn check` and `./learn selftest` pass.
- Linux arm64, gcc 14.4.0, OpenBLAS (Docker): all pass, TSan included.
- Linux arm64, gcc 12.2.0 (Debian bookworm), OpenBLAS: all pass, TSan included.
- Linux x86-64 under Rosetta, gcc 14.4.0, OpenBLAS: all pass with GPU_TSAN=0 and, for the
  sanitizer run, `ASAN_OPTIONS=detect_leaks=0` (see "Owed").
- Before the redesign, also: Linux arm64 with pkg-config unable to find OpenBLAS (mm leaves blas
  out and says how to get it).

## Owed, and what could not be checked here

- **A real x86-64 run.** Under Rosetta the suite passes (`-march=native` gives AVX2 and FMA:
  `vfmadd132ps` on `ymm`), except what Rosetta cannot do: ThreadSanitizer and LeakSanitizer.
  Rosetta's timings are a translator's, so none are recorded. Owed on the GPU machine
  (plans/gpu.md, "The GPU machine"): the suite with TSan and LSan, and the tables on AVX2, where
  a vec is one register of 8 floats.
- **A quiet machine**: the Mac's load was 14 to 34 during the Linux tables and the tables after the change of width.
- Nothing was run on an Intel Mac or with a gcc older than 12.2.

## From the module 00 lessons

Written 2026-11-25 and 26 on the owner's Mac (Apple M4 Pro, macOS 26.6.2, Apple clang 21.0.0),
`uptime` checked before every transcript: load averages 4 to 12 on its 14 cores while the lessons'
transcripts were taken, 14.4 at the worst during the side experiments below.

- **rand() is not the same on two C libraries** (00.01 says so with the first two). `srand(1)`, then
  three `rand()`, a scratch program built with `-std=c11 -O2`: macOS 26.6.2's libc 16807 282475249
  1622650073; glibc 2.41 (Debian, the gpu-track-arm64 image) 1804289383 846930886 1681692777; musl
  1.2.5 (Alpine 3.22.8) 0 740882966 1616430695. RAND_MAX is 2147483647 on all three.
- **CS:APP chapter titles**, read in the table of contents of the 3rd edition's "TOC and Preface"
  PDF, https://csapp.cs.cmu.edu/3e/pieces/preface3e.pdf (linked from
  https://csapp.cs.cmu.edu/3e/home.html), on 2026-11-26: chapter 5 "Optimizing Program
  Performance" (page 495), chapter 6 "The Memory Hierarchy" (page 579). Nothing else in the book
  was read. 00.03 cites chapter 5 by its title only.
- **wb time at three sizes** (00.03's Run it), the fastest run: 2^24 3.22 to 3.39 ms (59.4 to 62.5
  GB/s, 107 to 149 runs); 4096 0.0007499 ms (65.5 GB/s, 1000 runs, 18 ticks of the 41 ns clock);
  1000000 0.189 to 0.202 ms (59.5 to 63.5 GB/s). Nearly the same GB/s whether the 48 KiB fit the
  L1d or the 192 MiB fit no cache. The plan's "the GB/s is not the same at every size" did not
  show here, so the lesson says what was seen and no cause.
- **add.c with the vectorizer on is no faster here** (a scratch copy with `$(SCALAR)` taken off
  add.o's rule; `otool -tv` shows 10 `fadd.4s` in add.o): 59.3 to 60.7 GB/s at 2^24, 62.1 to 65.5
  at 4096, 59.5 to 60.6 at 10^6, interleaved with the scalar build at the same numbers. So the
  design's "not the most this machine's memory can do" could not be shown on this Mac; 00.03 says
  only that the GB/s describes this loop, one float at a time, not the memory. Why both builds
  stop near 60 GB/s at every size was not investigated.
- **The cold run** (00.03's Break it: no warm-up, max_runs 1), one run each time: 11.1 to 19.8 ms
  on 2026-11-25, 6.6 to 11.4 ms on 2026-11-26, against a fastest run of 3.2 to 3.4 ms with the
  warm-up and the default runs. What the warm-up pays for, checked with two more scratch builds,
  10 runs each interleaved (2026-11-26, load 8): no warm-up 6.7 to 10.8 ms; the warm-up kept and
  one timed run 3.25 to 5.30 ms; no warm-up but out written with memset before bench 3.81 to
  7.56 ms. So most of the cold run's extra is the first write to out's 64 MiB (a and b were
  written by rng_fill), which is what 00.03 says. On 2026-11-25 the same three gave 11 to 20,
  6.1 to 7.4 and 6.1 to 8.3 ms: one run, even warm, is slower than the fastest of a hundred, and
  why was not looked into.
- **wb time -n 64** prints `min 0 ms` on this Mac every time tried (64 adds take less than one
  41 ns tick); the median was 0 in some runs and 4.098e-05 ms (one tick) in others, so 00.03's
  transcript lets it vary. On a machine with a finer clock it may print a GB/s instead; not tried.
- **wb check -n 4 passes with the tail broken** (00.02's Break it shows it): with n a multiple of
  4 the tail never runs. wb's default n of 1003 is what makes the check reach it.

## From the module 01 lessons

Written 2026-11-26 on the owner's Mac (Apple M4 Pro, 10 performance and 4 efficiency cores,
macOS 26.6.2, Apple clang 21.0.0, Accelerate), `uptime` checked before every transcript. The
lessons' timed transcripts were taken at load averages 6.2 to 10.8 on its 14 cores (two taken at
13 to 16 were taken again); the verify replays ran at up to 24, which only moves their numbers,
and verify lets those vary.

- **01.01's Break it fails on 1x1x1, 54 times the allowance, not hundreds.** With ijk's inner loop
  stopping at `p < k - 1`, `./mm check` stops at the first shape it fails on: `ijk 1x1x1: FAIL, 1
  of 1 wrong; worst at [0]: got 0, want -0.0540636703 (error 0.0541, allowed 0.00101)`. The term
  left out is the whole sum, a[0] x b[0] = -0.438330 x 0.123340 (wb show's first values). The
  design's "hundreds of times the allowance" would need a larger shape, which mm check never
  reaches; the lesson says 54 times, against the right ijk's worst of 0.0068 of its allowance.
- **01.01, GFLOP/s at two sizes**: ijk 72.5 ms (3.45 GFLOP/s) at n = 500, 659.5 ms (3.03) at 1000.
- **01.02's Break it** (DEFAULT_N 1024 in mm.c, `./mm time ijk ikj`, load 7.7): ijk 669.5 ms at
  1000 and 1135.5 at 1024 (1.7 times as long for 7% more work); ikj 281.8 and 278.5. The verify
  replay at load 13 gave 672.4 / 1178.4 and 279.5 / 306.3. The lesson says only what may be said
  (a power of two and a whole number of lines; the floats of a column compete for the same few
  places in the cache), not "a whole number of pages": this Mac's page is 16 KiB
  (`hw.pagesize: 16384`), so 4096 bytes is a quarter of one.
- **Cache sizes on Linux** (01.02 names `lscpu --caches`). Its manual, util-linux v2.41
  (https://github.com/util-linux/util-linux/blob/v2.41/sys-utils/lscpu.1.adoc, read 2026-11-26):
  "-C, --caches ... Display details about CPU caches." In the gpu-track-arm64 container on this
  Mac (Debian 13.8, util-linux 2.41.5, glibc 2.41) it printed the three levels (L1d, L1i, L2) with
  every size column empty; `getconf -a` gave LEVEL1_DCACHE_LINESIZE 64 and every size 0; and
  /sys/devices/system/cpu/cpu0/cache/index*/ has no `size` or `coherency_line_size` files. So the
  lesson says a virtual machine may leave the sizes out. A real Linux machine was not tried.
- **01.03, the vectorizer turned back on for matmul.o** (Break it): ikj 265 ms -> 66.8 and 68.1
  ms (load 8 and 9); ijk unchanged within the noise (599 in Run it, 617 and 622 after); the check
  lines unchanged. The compiler's ikj (68 ms) stays slower than simd (45 ms) here; not looked into. In `otool -tv
  matmul.o` of that build, matmul_ijk has a vector path only for n == 1 (and k > 3), where b's
  column is contiguous: `fmul.4s` with the adds still scalar and in order (`fadd s0, s0, s1`
  sixteen times); for n > 1 the loop is `ldr s` / `fmul s` / `fadd s`. A scratch build of matmul.c
  with `-fassociative-math -fno-signed-zeros -fno-trapping-math` added (vectorizer on) gave that
  n == 1 path `fadd.4s` and a horizontal add, but the n > 1 loop stayed scalar: ijk 596 ms, worst
  error 9.3e-06 as before. So the design's reason ("ijk would have to add the terms of one sum in
  a different order") is not the whole reason on clang: allowed to reorder, it still does not
  vectorize the strided column. The lesson states both observations and no further cause.
- **Intrinsic names** (01.03's Decide the boundary), read in Apple clang 21.0.0's own headers
  (/Library/Developer/CommandLineTools/usr/lib/clang/21.0.0/include): `vfmaq_f32` in arm_neon.h,
  `_mm256_fmadd_ps` in fmaintrin.h.
- **01.04, GFLOP/s by size** (`mm time -n N ikj simd`, load 8.8): ikj 7.53, 7.76, 7.79 and simd
  47.10, 46.04, 40.75 at n = 500, 1000, 2000. `mm time -n 2000 simd blocked`: 411.6 ms (38.87)
  against 242.3 ms (66.04). blocked's check line is simd's (1.91e-05 at [37521]); MM_BLOCK 8 and
  100000 keep it so.
- **01.04's Break it** (load 7.7): MM_BLOCK 8, simd 43.0 ms, blocked 67.9; MM_BLOCK 100000, simd
  43.2, blocked 43.1. Why tiles of 8 cost so much was not looked into; the lesson gives no cause.
- **01.05, threads by count** (n = 1000, fastest run): at load 6 to 7, 1 thread 29.6 ms (blocked
  29.6), 2 15.0, 4 7.62, 10 3.36, 14 4.33 (the default), 28 3.6; at load 10.8 (the lesson's
  transcript), 1 33.6, 4 8.53, 10 4.69, 14 4.55. Whether 10 beats 14 depends on the load: it did
  at 6 (three rounds of three), not at 10 (mixed). `-n 64 simd threads`: 0.009 against 0.071 ms.
- **01.05's Break it does not show what the design said.** thread_count() returning twice the
  cores (28) was faster than 14, not "not faster": three interleaved rounds of `mm time -t T
  threads` at load 5.7 to 6.4 gave 14 threads 4.373, 4.347, 4.335 ms; 28 threads 3.633, 3.584,
  3.568; 10 threads 3.356, 3.391, 3.359. At load 9.5 to 10.1: 14 5.501, 5.051, 4.727; 28 4.305,
  4.031, 3.780; 10 6.259, 4.838, 5.028. At 13.4 to 16.2 the two were within the noise (14 5.568,
  6.206, 4.954; 28 5.956, 5.870, 4.946), and verify's replay at about 12 gave 28 5.683 against 14
  5.462. The lesson's transcript (load 8.8): 28 4.752, 14 5.048. The design's fallback (core count
  against twice it) is the same comparison, so the lesson shows the real result and says it is
  within the noise on a busy machine. A scratch program (the 01.05 split, each
  thread calling blocked_rows and timing its share with bench_now; 20 calls, the last printed) gave share times at
  14 threads of 2.23 to 4.18 ms and 2.36 to 4.34 ms (total 4.59 and 4.48); at 28, 21 shares at
  1.17 to 1.23 ms and 7 at 1.36 to 3.22 (total 3.68); at 10, 3.31 to 4.76 (total 4.82). So the
  shares do not take the same time and the slowest sets the call's; which core each ran on cannot
  be read on macOS, so the lesson names the two kinds of core as a certain difference, not as the
  measured cause.
- **blas's check line on this Mac equals simd's** (1.91e-05 at [37521] of 256x256x256), as the
  n = 2000 table above found for Accelerate; 01.05 says nothing in the track promises it.
- **Links** opened 2026-11-26 (HTTP 200): BLIS 2.1 docs/Multithreading.md, docs/FAQ.md and
  docs/KernelsHowTo.md on GitHub; OpenBLAS v0.3.34's kernel/ directory; the GCC 16.2 Vector
  Extensions page; Apple's cblas_sgemm and "Determining system capabilities" pages; lscpu.1.adoc
  at util-linux v2.41.
