# Plan: track `gpu` - GPU kernels for LLM inference, from scratch

Status: plan (direction set by Fable; implementation by Opus agents).
Outline: `outlines/gpu-kernels.md`; it moves to `plans/gpu-outline.md` when
`tracks/gpu` lands, as cc's and lang's did. Modules 00 and 01 are being
built; modules 02 to 09 wait for a machine with an NVIDIA GPU (see "The GPU
machine").

## What the owner asked for (2026-11-25)

"Does the Inference engineering covers writing kernels?" (it does not), then:
"Should we create a course for creating a GPU kernel like vllm? Step by step
guide?", then "Lets go?" to the recommendation (a separate track, CUDA,
following vLLM's own kernels), then "Lets get started on this".

So: a step by step guide in which the reader writes the kernels an inference
server like vLLM runs on the GPU, and can read vLLM's afterwards.

## What the reader ends with

Their own CUDA kernels for every operation of a small Llama-style model -
matrix multiply, SiLU, RMS norm, rotary positions, a KV cache in blocks and
attention over it - each one checked against a plain reference, called from
Python, and timed against PyTorch on the same GPU. On the way: matrix
multiply made fast on the CPU five ways, which is where every idea the GPU
modules use is first met.

## Decisions

- Track id `gpu`, kind `gpu`, title "GPU kernels for LLM inference, from
  scratch". Modules 00 to 09 as the outline has them.
- CUDA, not Metal: the systems worth reading (vLLM, FlashAttention) are
  CUDA. The owner was asked "CUDA or Metal?" and answered "Lets go?"; CUDA
  is my reading of that, not their words.
- The spine is vLLM at tag v0.2.0 (commit e2fb71ec): five kernel files under
  csrc/, about 1,200 lines (activation_kernels.cu, layernorm_kernels.cu with
  reduction_utils.cuh, pos_encoding_kernels.cu, cache_kernels.cu,
  attention/attention_kernels.cu). The reader writes each kernel, then reads
  vLLM's. No vLLM code is copied; a "Reading vLLM" lesson links to the file
  at the tag and quotes at most a few lines, with the licence named.
- **Modules 00 and 01 need no GPU** (changed on 2026-11-25 from the first
  outline, which put the first GPU kernel in 00.01). The workbench is C on
  the CPU; the first kernel on a GPU is 02.01 and "wait before you stop the
  clock" is 02.04. Reasons: a reader can start on any laptop, and these two
  modules can be built and tested today on the owner's Mac.
- Languages: C11 for modules 00 and 01, built by `make` with the host's
  `cc`; CUDA C++ from module 02; Python only for the tests and, in module
  09, the binding.
- Two rules of the track, stated in its first lesson and kept in every one:
  a function is checked against a slow plain reference before it is timed;
  every speed on a page is one the reader measures, with the library's
  number beside it. A lesson's transcript shows the numbers of the machine
  it was written on and names that machine; `./learn verify` replays it with
  the numbers allowed to vary (`vary ... num`).
- Nothing is taken from a book or an article: the matmul ladder is the
  common one (CS:APP chapter 6, Goto and van de Geijn, the Algorithmica and
  Boehm write-ups are cited in Go deeper), every line of code is ours.

## The GPU machine

The owner's Mac (M4 Pro, arm64, no NVIDIA GPU) cannot run CUDA. Nothing from
module 02 on is designed in detail, coded or written until there is a Linux
x86-64 machine with an NVIDIA GPU that `./learn test gpu` and `./learn
verify gpu` can run on over ssh. That is the owner's to provide. The same
machine then also runs modules 00 and 01 on x86-64 (AVX2), which today are
checked on arm64 only (macOS natively, Linux in Docker).

## Layout of `tracks/gpu/` after modules 00 and 01

```
Makefile          builds wb and mm; finds a BLAS; `make SANITIZE=1`
rng.h rng.c       numbers from a seed, the same on every machine      00.01
add.h add.c       add_ref (the plain version) and add                 00.01
wb.c              the workbench program: show, check, time            00.01 on
check.h check.c   how close is close, and the worst element           00.02
bench.h bench.c   warm up, repeat, the fastest run                    00.03
matmul.h          every matmul variant's prototype, the table of them 01.01 on
matmul.c          matmul_ref, matmul_ijk; _ikj; _blocked              01.01-01.03
matmul_simd.c     matmul_simd                                         01.04
matmul_threads.c  matmul_threads                                      01.05
blas.c            matmul_blas: the system's BLAS, when there is one   01.05
mm.c              the matmul program: list, check, time               01.01 on
tests/            one file a lesson (tracks/lang/tests is the model)
NOTES.md          what the lesson writers need: sources read, numbers measured
```

## Module 00 - the workbench

### rng (00.01)

`uint32_t rng_u32(uint64_t *state)` and `float rng_f32(uint64_t *state)`
(in [0, 1), 24 random bits, so every value is exact in a float), and
`void rng_fill(float *x, size_t n, uint64_t seed)` (values in [-1, 1):
`2 * rng_f32 - 1`). The generator is the xorshift* that llama2.c's run.c
uses for sampling (the research agent confirms its three shifts and
multiplier from the source before the lesson names it). Same seed, same
numbers on every machine: this is what lets a lesson show values.

### add (00.01)

`void add_ref(const float *a, const float *b, float *out, size_t n)`: one
loop, one element at a time, nothing clever. `void add(...)`: the same
signature, the "version under test"; in this module it is the loop
unrolled by four with a tail, so it is a second implementation that can be
wrong in ways the first cannot (the tail). `wb show` prints n, the seed and
the first four values of a, b and add(a, b).

### check (00.02)

```c
typedef struct {
    size_t n, bad;          /* elements compared; elements outside the tolerance */
    size_t worst;           /* index of the element furthest outside (or closest to the limit) */
    float got, want;        /* that element */
    double err, allowed;    /* |got - want| and atol + rtol * |want| for it */
} check_result;
check_result check_close(const float *got, const float *want, size_t n, double rtol, double atol);
int check_report(const char *name, check_result r);   /* one line; returns 0 when r.bad == 0 */
```

The rule is numpy.isclose's: an element is good when
`|got - want| <= atol + rtol * |want|`, written so that a NaN on either side
is bad and two equal infinities are good. "Worst" is the largest
`err / allowed` (a NaN beats everything). `wb check` runs add against
add_ref with rtol = 0, atol = 0 (adding is exact: both versions must agree
to the bit) and prints the report line. The lesson's point: `==` is right
for add and wrong for everything after it; module 01 needs a tolerance and
says where its size comes from.

### bench (00.03)

```c
typedef struct { double min_time; int min_runs, max_runs; double (*clock)(void); } bench_opts;
typedef struct { int runs; double min, median, total; } bench_result;
double bench_now(void);                                   /* monotonic seconds */
bench_result bench(void (*fn)(void *), void *arg, bench_opts o);
```

One call first whose time is thrown away (the warm-up: page faults, cold
caches), then calls until `runs >= min_runs` and `total >= min_time`, or
`runs == max_runs`. Defaults (a zero field means the default): 0.5 s, 5,
1000, bench_now. The headline is the fastest run (noise only ever adds
time); the median is printed beside it. `clock` is a parameter so the test
can pass a scripted clock and check the arithmetic exactly.
`wb time [-n N]` times add (default n = 1 << 24) and prints runs, min and
median in ms, and GB/s counted as 12 bytes an element (two floats read, one
written). That GB/s is the machine's memory speed: later modules set every
kernel's bytes per second against it.

### Tests, module 00

- 00.01: `wb show` for three seeds against the same generator written
  again in Python (struct-rounded to float32), value for value; add equals
  add_ref for every n from 0 to 67 (every tail length); out's neighbours
  untouched (canaries either side).
- 00.02: a C test driver (tests/check_driver.c, not shown to learners)
  feeds check_close cases from the test: equal arrays; one element off by
  less, exactly, and more than the allowance; NaN in got, in want, in both;
  +inf against +inf and against -inf; n = 0; the worst index when several
  are bad. `wb check` prints the ok line. With add's tail broken on purpose
  (a patched copy), `wb check` fails and names an index in the tail.
- 00.03: bench with a scripted clock: the warm-up is not counted, min and
  median of a known list, stops at min_runs and min_time and max_runs each;
  `wb time -n 4096` prints the line in the stated format with min <= median
  and a positive GB/s.
- Whole module: `-std=c11 -Wall -Wextra -pedantic -Werror` clean on Apple
  clang and on gcc; the tests again under ASan and UBSan (`GPU_SANITIZE=1`).

## Module 01 - matrix multiply on the CPU

One signature for every variant, row-major, single precision:

```c
/* c[m][n] = a[m][k] * b[k][n]. c may hold anything on entry; it must not overlap a or b. */
void matmul_NAME(const float *a, const float *b, float *c, int m, int k, int n);
```

`matmul.h` has a table `{name, function}` that `mm` walks; a variant joins
the table in the lesson that writes it (`@from`).

- **matmul_ref (01.01):** three loops, the sum of each element kept in a
  double. Never timed as a contestant; it is the truth the others are held
  to.
- **matmul_ijk (01.01):** three loops in float, the inner one over k.
- **matmul_ikj (01.02):** the two inner loops swapped: c's row zeroed, then
  for each k, `c[i][j] += a[i][k] * b[k][j]` along j. Reads b by rows.
- **matmul_blocked (01.03):** ikj over tiles of `MM_BLOCK` (a constant the
  reader changes in Break it; the agent picks the default by measuring
  32 to 256 on both machines) so the pieces of a, b and c in use fit in the
  cache.
- **matmul_simd (01.04):** blocked, with the j loop written in vectors of 8
  floats using the compiler's vector types (`__attribute__((vector_size(32)))`,
  loads and stores through memcpy so any pointer is allowed, a scalar tail),
  and four values of k taken at once so each vector of c is loaded and
  stored once per four multiplies. One source for AVX2 and NEON; the lesson
  shows the intrinsics it stands for in Decide the boundary.
- **matmul_threads (01.05):** rows of c split evenly over pthreads (count
  from `sysconf`, or `mm -t N`), each running the simd kernel on its rows.
- **matmul_blas (01.05):** `cblas_sgemm` from Accelerate on macOS or
  OpenBLAS on Linux when make finds one; without one, `mm` says how to get
  it and the rest still works.

**Scalar means scalar.** `matmul.c` is compiled with the compiler's
vectorizer off (the Makefile picks the flags for clang and gcc), or the
compiler quietly turns 01.02's loop into 01.04's and the ladder lies. 01.04
says so and has the reader turn it back on to see what the compiler does
unasked. `matmul_simd.c` gets `-march=native` on x86-64.

`mm list` names the variants built. `mm check` runs every variant over a
fixed set of shapes against matmul_ref and prints one line each. `mm time
[-n N] [-t T] [name...]` prints, per variant: min ms, GFLOP/s (2mkn
operations), and how many times faster than ijk. Default n = 1024 unless
the agent's measurements say ijk makes a lesson's transcript take over 30 s
there; then 768.

**The tolerance (01.01).** Inputs are rng_fill's, in [-1, 1). check_close
with rtol = 1e-4 and atol = 1e-3: a float sum of k products of such numbers
drifts by about sqrt(k) rounding errors of the running sum, some 1e-4 at
k = 2048, while a real bug (a term dropped, a wrong index) moves an element
by about 0.3. The agent measures the worst error of every variant at the
largest shape and records it in NOTES.md; if any comes within a factor of 3
of the tolerance, stop and report instead of loosening it.

### Tests, module 01

- Every variant, as soon as its lesson exists, against matmul_ref on: every
  square size 1 to 67; forty seeded random (m, k, n) with each side in
  1..200; sizes one less, equal and one more than MM_BLOCK and than 8 and
  than a multiple of both; a 1 x k x 1 and a m x 1 x n; any side 0 (c
  untouched or empty, no crash).
- c is filled with a sentinel before every call (a variant that adds into
  c instead of setting it fails) and has canaries either side.
- The identity: a times I is a, exactly, for every variant.
- matmul_blas, when built, within the same tolerance of matmul_ref; every
  variant within it of matmul_blas.
- The checker checked: three wrong matmuls in the test driver (the last
  column skipped, b read transposed, one term dropped) must each fail
  `check_close` at the tolerance above.
- matmul_threads with 1, 2, 3, 7 and 64 threads, and with more threads
  than rows; under ThreadSanitizer.
- Everything again under ASan and UBSan; `-Werror` clean on Apple clang and
  gcc; the whole suite on Linux arm64 in Docker (gcc, OpenBLAS). x86-64
  under emulation if Docker can run it with AVX2; otherwise that run is
  owed on the GPU machine and NOTES.md says so.
- The ladder is real: on the machine the lessons are written on, at the
  default n, each of ikj, blocked, simd, threads is faster than the one
  before (a check for the author, run by hand and recorded in NOTES.md, not
  a unit test: speed is not asserted in the suite).
- The repo's own: `./learn test gpu`, `check-skeleton gpu` (each lesson cut
  out, its test fails at the stub), `check-timeline gpu`, `./learn check`.

Every bug found while building becomes a case in that lesson's test.

## Build order

1. Code and tests for modules 00 and 01 (one Opus agent, a worktree), with a
   second agent reading the sources the lessons will cite and writing what
   they say into notes (llama2.c's generator, numpy.isclose, hyperfine's
   warm-up and statistics, CS:APP 6, Goto and van de Geijn, the Algorithmica
   and Boehm pages, BLIS's micro-kernel, Accelerate and OpenBLAS sgemm).
2. Lessons for 00 and 01 as soon as that code passes: my lesson and figure
   design from the real numbers, then Opus writers by lesson range and art
   agents by lesson range; module 00's cover redrawn for the CPU workbench
   (the reference and the version under test compared; then runs on a time
   axis, the first thrown away, the fastest reported). `./learn verify` on
   every transcript.
3. Stop there until the GPU machine exists. Then module 02, designed from
   vLLM's activation_kernels.cu, and on.
