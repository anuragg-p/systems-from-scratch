# GPU track, modules 00 and 01: what the sources say

Read on 2026-11-25 for plans/gpu.md (modules 00 and 01). GitHub files were fetched with
`gh api` at the tag or commit given. Web pages were fetched with curl and turned into
text. Facts marked "observed" come from commands run on the owner's Mac today
(Apple M4 Pro, macOS kernel Darwin 25.6.0, Apple clang 21.0.0 (clang-2100.1.1.101),
MacOSX SDK 26.5). Each one says which machine and compiler it ran on.

Quotes are verbatim, except that non-ASCII characters in a source (curly quotes, the Greek
sigma, the multiplication sign, the plus-minus sign) are written here in ASCII.
Speed-ups in section 4 are the authors' own, measured on their machines. None of them were
measured here.

---

## 1. llama2.c: the sampling RNG and the smallest checkpoints

Repository: https://github.com/karpathy/llama2.c, licence MIT (GitHub API `license.spdx_id`).
Version: branch master at commit `350e04fe35433e6d2941dce5a1f53308f87058eb`
(2024-05-29, "Merge pull request #514 ..."). This is the newest commit on master today.

### 1.1 The generator (run.c, lines 680-689 at that commit)

URL: https://github.com/karpathy/llama2.c/blob/350e04fe35433e6d2941dce5a1f53308f87058eb/run.c#L680-L689

```c
unsigned int random_u32(unsigned long long *state) {
    // xorshift rng: https://en.wikipedia.org/wiki/Xorshift#xorshift.2A
    *state ^= *state >> 12;
    *state ^= *state << 25;
    *state ^= *state >> 27;
    return (*state * 0x2545F4914F6CDD1Dull) >> 32;
}
float random_f32(unsigned long long *state) { // random float32 in [0,1)
    return (random_u32(state) >> 8) / 16777216.0f;
}
```

- The 64-bit state is updated in place: right shift 12, left shift 25, right shift 27,
  each XORed into the state, in that order. The output is the state times
  `0x2545F4914F6CDD1D` (mod 2^64), shifted right by 32. That is the top 32 bits of the
  product.
- The float is `(u32 >> 8) / 16777216.0f`, i.e. the top 24 bits of the 32-bit output
  divided by 2^24. That gives a value in [0, 1) that a float holds exactly.
- Seeding (run.c lines 915, 929, 939): `unsigned long long rng_seed = 0;`, then
  `rng_seed = atoi(argv[i + 1]);` for `-s`, then
  `if (rng_seed <= 0) rng_seed = (unsigned int)time(NULL);`. `build_sampler` stores the seed
  directly as the state (`sampler->rng_state = rng_seed;`, line 671). Nothing in run.c
  mixes or scrambles the seed first.
- The generator's only use is the sampling coin: `float coin = random_f32(&sampler->rng_state);`
  (line 703).

The algorithm is the one in the Wikipedia article that the comment cites
(https://en.wikipedia.org/wiki/Xorshift, revision 1381218019, 2026-10-20). That article's
`xorshift64star` uses `x ^= x >> 12; x ^= x << 25; x ^= x >> 27; return x * 0x2545F4914F6CDD1DULL;`.
Its comment reads "xorshift64s, variant A_1(12,25,27) with multiplier M_32 from line 3 of
table 5" and "initial seed must be nonzero". The article says that a version returning only
the high 32 bits "passes BigCrush with zero failures". llama2.c returns those high 32 bits.

**Is "this is the generator llama2.c uses" true for the course's rng.c?** Yes, provided that
rng.c does all of the following:
(a) updates the state with shifts 12 (right), 25 (left), 27 (right), in that order, before
producing output;
(b) returns `(uint32_t)((state * 0x2545F4914F6CDD1DULL) >> 32)`;
(c) makes the float as `(u32 >> 8) / 16777216.0f`;
(d) uses the seed itself as the initial state.
If those hold, every output matches llama2.c's bit for bit. These differences are allowed
and do not change any output:
- `uint64_t`/`uint32_t` in place of `unsigned long long`/`unsigned int`. llama2.c's
  `unsigned int` is 32 bits only by platform convention, so `uint32_t` is the more exact
  spelling.
- rng_fill's `2 * f - 1`. That is the course's own step on top of the generator.

These differences would change outputs or behaviour, and should be stated if rng.c has them:
- Seed 0. Xorshift maps state 0 to 0 forever, so outputs are all 0 (observed:
  `seed 0 u32: 0 0`). llama2.c never runs with seed 0, because it replaces any seed `<= 0`
  with `time(NULL)`. A course rng.c that accepts seed 0 has to reject it, remap it, or document it.
- Seeds above INT_MAX. llama2.c's command line goes through `atoi`, so its seeds are ints.
  The course takes a uint64_t seed. The generator is the same; only the range of seeds that
  llama2.c's CLI can reach differs.
- Any other choice of output bits (low 32 bits, or `u32 * 2^-32` for the float) is no longer
  llama2.c's generator.

Reference values (observed): the two functions above were copied verbatim from run.c into a
test file and compiled with Apple clang 21 at -O2. The results were cross-checked by an
independent Python version.
- seed 1: u32 = 1206177355 2882512552 3117485455 1303648416; f32 = 0.280835032 0.671137214 0.725846112 0.303529263
- seed 42: u32 = 1456360119 3359763283 3393612768 4054632243; f32 = 0.339085221 0.782255828 0.790136993 0.944042623
- seed 1234: u32 = 3159758022 1306163061 1764681998 1393191135; f32 = 0.735688448 0.304114759 0.410872042 0.324377537

### 1.2 The smallest published checkpoints (README.md, same commit, lines 148-155)

URL: https://github.com/karpathy/llama2.c/blob/350e04fe35433e6d2941dce5a1f53308f87058eb/README.md

The table header is `| model | dim | n_layers | n_heads | n_kv_heads | max context length | parameters | val loss | download`.
The rows, as the README gives them:

| model | dim | n_layers | n_heads | n_kv_heads | max ctx | parameters | val loss | file |
|---|---|---|---|---|---|---|---|---|
| 260K | 64 | 5 | 8 | 4 | 512 | 260K | 1.297 | stories260K (a folder on HF) |
| OG | 288 | 6 | 6 | 6 | 256 | 15M | 1.072 | stories15M.bin |
| 42M | 512 | 8 | 8 | 8 | 1024 | 42M | 0.847 | stories42M.bin |
| 110M | 768 | 12 | 12 | 12 | 1024 | 110M | 0.760 | stories110M.bin |

Download links are at https://huggingface.co/karpathy/tinyllamas. The README describes
stories15M as "this 15M parameter model I trained on the TinyStories dataset (~60MB download)".
For speed it says only "On my M1 MacBook Air this runs at ~110 tokens/s".

Caution: README line 9 says "one simple 700-line C file (run.c)", but run.c at this commit is
973 lines (counted with `wc -l`). Do not repeat "700 lines".

---

## 2. How close is close

### 2.1 numpy.isclose and numpy.allclose

URLs: https://numpy.org/doc/stable/reference/generated/numpy.isclose.html and
https://numpy.org/doc/stable/reference/generated/numpy.allclose.html.
Version: both pages read "NumPy v2.5 Manual". Their [source] links point to tag v2.5.0,
file `numpy/_core/numeric.py` (isclose at L2319-L2448, allclose at L2225-L2312).

- Signature and defaults: `numpy.isclose(a, b, rtol=1e-05, atol=1e-08, equal_nan=False)`.
  allclose has the same signature.
- Formula, quoted from the isclose Notes: "For finite values, isclose uses the following
  equation ...: `absolute(a - b) <= (atol + rtol * absolute(b))`".
- Not symmetric, quoted: "Unlike the built-in math.isclose, the above equation is not
  symmetric in a and b - it assumes b is the reference value - so that isclose(a, b) might be
  different from isclose(b, a)." So b is the reference. In the course's
  `check_close(got, want, ...)`, `want` plays b's role.
- The default atol is a trap. The page warns: "The default atol is not appropriate for
  comparing numbers with magnitudes much smaller than one". Its example is that
  `isclose(1e-9, 2e-9)` is True with the default settings.
- NaN and inf, from the allclose page: "NaNs are treated as equal if they are in the same
  place and if equal_nan=True. Infs are treated as equal if they are in the same place and
  of the same sign in both arrays." The isclose examples include
  `np.isclose([1.0, np.nan], [1.0, np.nan])` -> `array([ True, False])`.
- The implementation (numeric.py at v2.5.0):
  `result = (less_equal(abs(x - y), atol + rtol * abs(y)) & isfinite(y) | (x == y))`,
  followed by `if equal_nan: result |= isnan(x) & isnan(y)`.
  An element is therefore close when it is within the tolerance and the reference is finite,
  or when it is exactly equal. Equal infinities pass through `x == y`. Opposite infinities
  fail. NaN fails unless equal_nan is set. The plan's rule matches this: NaN on either side
  is bad, two equal infinities are good.
- isclose also warns (or raises, depending on `np.geterr()["invalid"]`) when rtol or atol is
  not finite.

### 2.2 torch.allclose

URL: https://docs.pytorch.org/docs/stable/generated/torch.allclose.html. That URL redirects
to https://docs.pytorch.org/docs/2.15/generated/torch.allclose.html, so the version is
PyTorch 2.15 docs.

- Signature: `torch.allclose(input, other, rtol=1e-05, atol=1e-08, equal_nan=False) -> bool`.
- Condition, elementwise: `|input_i - other_i| <= atol + rtol * |other_i|`, quoted from the
  page. `other` is the reference, so the test is asymmetric in the same way as numpy's.
- The page says: "The behaviour of this function is analogous to numpy.allclose".
- NaN: "equal_nan (bool, optional) - if True, then two NaN s will be considered equal.
  Default: False". The page says nothing about infinities.

---

## 3. Timing: warm-up, run count, which number to report

### 3.1 hyperfine

Repository: https://github.com/sharkdp/hyperfine. Latest release tag v2.0.0, commit
`b33755fe1fca8bcc1f182c773ca3ab040bfe517d`, published 2026-10-07. Licence: Apache-2.0
according to the GitHub API. The repository has both LICENSE-APACHE and LICENSE-MIT.

- Run count, from README.md lines 35-37: "By default, it will perform *at least* 10
  benchmarking runs and estimate a run count targeting roughly 3 seconds, including shell
  overhead and preparation and conclusion commands."
  The code (src/benchmark/mod.rs) times one run first and then sets
  `runs_in_min_time = min_benchmarking_time / (first run + overheads)` and
  `count = max(runs_in_min_time, min_runs)`, capped by `--max-runs` when that is given.
  Defaults in src/options.rs: `RunBounds { min: 10, max: None }` and
  `min_benchmarking_time: Time::new::<second>(3.0)`.
- The first timed run counts. That run, `BenchmarkIteration::Benchmark(0)`, is pushed into
  `measurements` and enters the statistics. The default is `warmup_count: 0`, so hyperfine
  discards nothing unless `--warmup` is given.
- Warm-up, from the `--warmup` help in src/cli.rs: "Perform NUM warmup runs before the
  actual benchmark. This can be used to fill (disk) caches for I/O-heavy programs."
  README: "you can use the -w/--warmup option to perform a certain number of program
  executions before the actual benchmark". `--prepare` runs a command before each timed run,
  for example to drop caches when you want them cold.
- Outliers. In v2.0.0, src/output/warnings.rs has one outlier warning, and it is about the
  first run only: "The first benchmarking run for this command was significantly slower than
  the rest (...). This could be caused by (filesystem) caches that were not filled until after
  the first run." It then suggests `--warmup` or `--prepare`.
  An outlier is a modified Z-score above `OUTLIER_THRESHOLD = 1.4826 * 10.0`
  (src/outlier_detection.rs, after Iglewicz and Hoaglin 1993).
  The general warning "Statistical outliers were detected. Consider re-running this benchmark
  on a quiet system without any interferences from other programs." was in v1.20.0. It is not
  in v2.0.0's warnings enum.
- Statistics. The terminal report (src/output/report.rs) has the columns "mean", "sigma"
  (printed as the Greek letter), "min" and "max". There is no median in the terminal output.
  The README says the CSV export has `<metric>_mean`, `<metric>_stddev`, `<metric>_median`,
  `<metric>_min` and `<metric>_max`, and that the JSON export holds every measured run,
  "excluding warmup runs".

### 3.2 Google Benchmark

Repository: https://github.com/google/benchmark, file docs/user_guide.md. Tag v1.10.0
(annotated tag object `f2bc56f35f4f2c9921496d19e25f558e69d1eff7`), published 2026-10-14.
Licence Apache-2.0.

- How the iteration count is chosen: "the number of iterations is at least one, not more than
  1e9, until CPU time is greater than the minimum time, or the wallclock time is 5x minimum
  time." It finds the count "by running the benchmark a few times and measuring the time taken
  and ensuring that the ultimate result will be statistically stable".
- `--benchmark_min_time` has "**Default:** `0.5` seconds". The flag also accepts `<int>x` for
  a fixed number of iterations.
- Warm-up: `--benchmark_min_warmup_time` defaults to `0.0` seconds. The guide says "Results
  gathered within this period are discarded" and "Per default the warmup phase is set to 0
  seconds and is therefore disabled."
- What it reports: "Average timings are then reported over the iterations run." With
  `--benchmark_repetitions` above 1, "the mean, median, standard deviation and coefficient of
  variation of the runs will be reported". The default is 1 repetition. A minimum is not among
  the built-in aggregates; the guide's "Custom Statistics" section shows how to add "max"
  with `ComputeStatistics`.

### 3.3 Julia BenchmarkTools

Repository: https://github.com/JuliaCI/BenchmarkTools.jl, file docs/src/manual.md. Tag v1.8.0
(annotated tag object `3ac45a452a0e999b01679b83e437096bf7047d88`), published 2026-04-15.
Licence: LICENSE.md says "licensed under the MIT 'Expat' License".

- "Which estimator should I use?" (manual.md line 403 onwards). Quoted: "Time distributions
  are always right-skewed for the benchmarks we've tested. This phenomena can be justified by
  considering that the machine noise affecting the benchmarking process is, in some sense,
  inherently positive". Then:
  - "The minimum is a robust estimator for the location parameter of the time distribution,
    and should not be considered an outlier"
  - "The median, as a robust measure of central tendency, should be relatively unaffected by
    outliers"
  - "The mean, as a non-robust measure of central tendency, will usually be positively skewed
    by outliers"
  - "The maximum should be considered a primarily noise-driven outlier, and can change
    drastically between benchmark trials."
- What `@btime` prints, from its docstring in src/execution.jl at v1.8.0: "The printed time is
  the *minimum* elapsed time measured during the benchmark."
- Defaults (manual.md): `samples = 10000`, `seconds = 5`, `evals = 1`, `gctrial = true`.
- Caveat (line 1016): "BenchmarkTools attempts to be robust against machine noise occurring
  between *samples*, but BenchmarkTools can't do very much about machine noise occurring
  between *trials*."

### 3.4 For and against "fastest run headline, median beside it"

- For: BenchmarkTools gives the course's reason almost word for word. Noise is "inherently
  positive", and the minimum is "a robust estimator". `@btime` prints the minimum.
- Mixed: BenchmarkTools also calls the median robust, and its regression examples use both
  `median(...)` and `judge(minimum(results), minimum(old_results))`.
- Against, or at least different: hyperfine (v2.0.0) leads with mean and sigma and shows the
  median only in its exports. Google Benchmark reports the mean over iterations, plus mean,
  median, stddev and CV across repetitions, and has no built-in min.
  Neither tool discards a run by default: hyperfine's warm-up is 0 runs and Google
  Benchmark's is 0 s. The course's always-on warm-up of one call is a deliberate difference.
- Defaults compared: the course's min_time of 0.5 s is Google Benchmark's default. Its minimum
  of 5 runs is below hyperfine's 10.

---

## 4. The matmul ladder as the notable write-ups do it

### 4.a Algorithmica, "Matrix Multiplication" (Sergey Slotin)

URL: https://en.algorithmica.org/hpc/algorithms/matmul/ (the page's text matches the source
file). Source: https://github.com/algorithmica-org/algorithmica/blob/ed1945c3d2de8548b1c744d3161eb668703db808/content/english/hpc/algorithms/matmul.md
(repo head `ed1945c`; the last commit to this file is `19bb630`, 2022-07-21).
The repository has no LICENSE file. The page footer reads "Copyright 2021-2022 Sergey Slotin".
Cite and link it; do not copy from it.

- Setup: "All implementations are compiled with GCC 13 and run on a Zen 2 CPU clocked at
  2GHz." The flags are `g++ -O3 -march=native -ffast-math -funroll-loops`. Sizes are square,
  n = 1920 for the headline, and benchmarks use only multiples of 48 (`48 = 6*16/gcd(6,16)`).
  Data is float32.
- The steps, in order:
  1. Naive i-j-k: "~16.7 seconds", about 0.42 GFLOPS.
  2. Transpose B: "~12.4s, or about 30% faster".
  3. Vectorize with GCC vector types: "around 2.3 GFLOPS - or another ~4 times higher".
     The page notes that adding `__restrict__` lets the compiler auto-vectorize the same loop,
     and that "Both manually and auto-vectorized implementations perform roughly the same."
  4. Register reuse, then a 6x16 kernel: "improves the benchmark performance, but only by
     ~40%". It says "(2-3x) on smaller arrays".
  5. Cache blocking (macro-kernel around micro-kernel): "Cache blocking completely removes the
     memory bottleneck". The numbers are in a chart only.
  6. Removing allocation and `std::min`, and a hand-unrolled micro-kernel: "another 50%
     improvement".
  7. Result: "~93% of BLAS performance and ~75% of the theoretical performance limit". The
     intro says "50 times faster ... under 40 lines of C". The peak is computed as
     8 (SIMD) * 2 (FMA throughput) * 2e9 = 32 GFLOPS. BLAS (through NumPy) "ends up reaching
     80% of the theoretical limit".
  The markdown also contains an HTML comment that the page does not show. It has seconds and
  GFLOPS per version: baseline 13.59 s / 0.52, transposed 12.38 / 0.57, vectorized 3.08 / 2.30,
  kernel 2.24 / 3.16, blocked 0.461 / 15.3, noalloc 0.408 / 17.3, nomove 0.304 / 23.3,
  blas 0.275 / 25.7. Those numbers are not the displayed text; cite the displayed text.
- The vector type is a GCC vector extension. The exact typedef:
  `typedef float vec __attribute__ (( vector_size(32) ));` with the comment
  `// a vector of 256 / 32 = 8 floats`.
- Alignment: memory comes from `std::aligned_alloc(32, 32 * n)` plus `memset`. Rows are copied
  into "memory-aligned arrays" and padded with zeros so that each dimension is a multiple of 8
  (later 6 and 16). The intrinsic sketch uses aligned `_mm256_load_ps`. In the final
  optimisations, a is read one element at a time, and the page says "we can use an unaligned
  store for c as we only use it rarely, so our only concern is reading b".
- Kernel: a 6x16 micro-kernel, `vec t[6][2]{}` accumulators, which is 12 ymm registers. Each
  step broadcasts one element of a (`vec{} + a[...]`, "converts to a broadcast") and does an
  FMA with two vectors of b. The reasoning given: Zen 2's FMA has "a latency of 5 and a
  throughput of 2", so at least 10 FMAs must be in flight, and there are 16 vector registers.
  The page says: "Note that this kernel is architecture-specific."
- Block sizes, in the order the loops run: `s3 = 64` columns of B, `s2 = 120` rows of A,
  `s1 = 240` rows of B. The page says "we want B to be in the L1 cache while A can stay in the
  L2 cache". It notes that cache associativity causes dips at n that are multiples of large
  powers of two (1536 runs "roughly 3 times slower than for n=1535").
- The Acknowledgements credit the algorithm to Kazushige Goto and link the Goto and
  van de Geijn PDF (see 4.c).

### 4.b Simon Boehm, "Fast Multidimensional Matrix Multiplication on CPU from Scratch"

URL: https://siboehm.com/articles/22/Fast-MMM-on-CPU. Version: page dated "August 2022", and
its footer reads "August 14, 2022". No licence is stated on the page.

- Machine and tools: "quadcore Intel i7-6700 CPU @ 3.40GHz ... 32KiB per-core L1d cache,
  256KiB of per-core L2 cache, and a shared 8MB L3 cache". The compiler is "clang v14.0",
  benchmarking uses Google Benchmark, and results are checked against PyTorch. Matrices are
  1024x1024 fp32, with the sizes as template parameters. He calls that choice "unfair" to BLAS.
- The steps, in order, with his times:
  1. Naive (RCI), default flags: 4481 ms.
  2. `-O3 -march=native -ffast-math`: 1621 ms.
  3. Accumulating in a register: 1512 ms.
  4. "Cache-aware loop reorder (RIC)", i.e. row, inner, col, the same as the course's ikj:
     89 ms, "A 16x improvement!". He adds: "the loop reordering also enabled vectorization".
     So this step's gain is cache plus compiler vectorization together, which is why the
     course's plan builds matmul.c with the vectorizer off.
  5. Tiling the inner (k) loop, tile 16 after a grid search ("At a tile size of 16, the
     runtime went to 70ms"). His estimate from L1 size was a tile of "~3.5".
  6. OpenMP, `collapse(2) num_threads(8)` over 256x256 row/column tiles: 16 ms.
  7. NumPy (MKL): 8 ms, which he counts as "18 FLOPs / core / cycle" against a peak of 32.
  He wrote no explicit SIMD step; the compiler vectorized from step 4 on. He ends at
  "9 FLOPS / core / cycle".

### 4.c Goto and van de Geijn, "Anatomy of High-Performance Matrix Multiplication"

URL: https://www.cs.utexas.edu/~flame/pubs/GotoTOMS_revision.pdf. Version: HTTP Last-Modified
"Wed, 15 Nov 2006", 25 pages. The PDF's running footer is the placeholder "ACM Transactions on
Mathematical Software, Vol. V, No. N, Month 20YY". The published citation comes from OpenBLAS's
docs/developers.md at v0.3.34, not from the PDF: "ACM Transactions on Mathematical Software
34 (3): Article 12" (2008).
The PDF reads fine as text with pdftotext. Only the figures (graphs, Fig. 4's tree and Fig. 12's
table layout) come out garbled.

- Layering (Section 3, Fig. 4). gemm splits into gepp, gemp or gepm, and those into gebp,
  gepb or gepdot kernels: "if these three lowest level kernels attain high performance, then so
  will the other cases of gemm". The names say which operands are matrix, panel or block
  (Fig. 2 and 3).
- The chosen path is gemm -> gepp (var1) -> gebp (Fig. 8). Section 5.6 argues that for
  column-major storage this "can be expected to be superior to all the other presented options".
- Packing (4.2.3): "The solution is to pack A in a contiguous work array, A~. Parameters mc and
  kc are then chosen so that A~, Bj, and Cj all fit in the L2 cache and are addressable by the
  TLB." B is packed too (copied to B~), because gepp reuses it across many gebp calls. 6.1:
  "A~ is stored so that each mr x kc submatrix is stored contiguously in memory." The paper also
  says packing is cheap relative to the work: "O(n) computations will be performed for every
  copied item".
- The inner kernel is gebp_opt1: Caux := A~ Bj, with A~ (mc x kc) held in L2 and Bj
  (kc x nr) in L1. Inside it, mr x nr blocks of C sit in registers (6.1).
  7.1: "The gebp opt1 algorithm was carefully assembly-coded for each of the architectures ...
  The routines for packing A and B ... were coded in C".
- What sets the block sizes:
  - mr x nr (6.2): "Typically half the available registers are used for the storing mr x nr
    submatrix of C"; amortising register loads "is optimal when mr ~ nr"; and
    `nr >= Rcomp / (2 Rload)` (equation 3).
  - kc (6.3): "kc nr floating point numbers should occupy less than half of the L1 cache".
    Remark 6.1: "the optimal choice is such that kc double precision floating point numbers
    occupy half of a page."
  - mc (6.4): "mc is typically chosen so that A~ only occupies about half of the smaller of
    (1) [the memory addressable by the TLB] and (2) [the L2 cache]".
  The paper treats the TLB as limiting more often than L2 does: "prefetching can mask a cache
  miss but not a TLB miss."
- Example (7.3, Pentium 4 Prescott, 3.6 GHz): mr x nr = 4 x 4. kc was limited to 192 by the
  instruction cache because the loop is fully unrolled. Fig. 13's caption gives the best
  mc x kc as "696 x 196, when the footprint is around 1 Mbyte". The figure label and the
  Fig. 12 table say 696 x 192, so the source itself disagrees.
- Reported performance: graphs only (Fig. 1 and Fig. 13-20, GFLOPS against size). The text
  claims "near-peak performance" and says the packing overhead "accounts almost exactly for
  the degradation in performance from the kernel curve to the dgemm curve". The extracted
  text contains no numeric speed-up.

### 4.d BLIS

Repository: https://github.com/flame/blis. Tag `2.1`, commit
`caf0db6be1202d9c83c79b51e75eceb96aa8b556`, released 2025-01-15. This is the latest release.
Licence: the GitHub API reports NOASSERTION. LICENSE says "All parties provide their portions
of the code under the 3-clause BSD license".

- The five loops, from docs/Multithreading.md (table "Loop around microkernel"):
  5th loop "JC loop" (n), 4th loop "PC loop" (k), 3rd loop "IC loop" (m),
  2nd loop "JR loop" (n), 1st loop "IR loop" (m).
  The 4th loop cannot be parallelised "because each iteration of the loop updates the same part
  of the output matrix C". docs/FAQ.md: "The macrokernel is implemented as two loops around the
  microkernel", and the macrokernel plus microkernel "correspond to the so-called 'inner
  kernels' ... in Kazushige Goto's GotoBLAS (and now in the successor library, OpenBLAS)".
- What the micro-kernel computes (docs/KernelsHowTo.md, "gemm microkernel"):
  `C11 := beta * C11 + alpha * A1 * B1`. A1 is an m x k micropanel "stored in packed
  (column-wise) format", B1 is k x n "stored in packed (row-wise) format", and m <= MR,
  n <= NR. FAQ: "It consists of one loop, where each iteration performs a very small outer
  product". KernelsHowTo also says loops in m and n "should always be fully unrolled", and
  "an unrolling factor of u = 4 is fairly common" for k.
- x86 block sizes, from config/haswell/bli_cntx_init_haswell.c (the active `#if 1` branch):
  sgemm kernel `bli_sgemm_haswell_asm_6x16`, so MR = 6 and NR = 16 for float. The other
  constants are MC = 168, KC = 256, NC = 4080 (float column). For double: MR 6, NR 8, MC 72,
  KC 256, NC 4080.
  docs/HardwareSupport.md maps Haswell, Broadwell, Sky/Kaby/Coffee Lake desktop parts, and
  SkylakeX with one FMA unit, to `haswell`. It explains: "the key detail that determines level-3
  performance outcomes is actually the vector ISA, not the microarchitecture".
  Algorithmica's hand-derived kernel has the same 6x16 shape.
- ARM block sizes, from config/firestorm/bli_cntx_init_firestorm.c: sgemm kernel
  `bli_sgemm_armv8a_asm_12x8r`, so MR 12 and NR 8. The rest: MC 480, KC 4096, NC 9600
  (float); double is 8x6r with MC 256, KC 3072, NC 8184. docs/ReleaseNotes.md:
  "Added Apple Firestorm (A14/M1) subconfiguration, `firestorm`."
  A generic ARM core for contrast, config/cortexa57/bli_cntx_init_cortexa57.c:
  `bli_sgemm_armv8a_asm_8x12`, MR 8, NR 12, MC 120, KC 640, NC 3072 (float).
  BLIS 2.1 has no configuration for M2, M3 or M4.

---

## 5. What a system BLAS does that the course's best version will not

### 5.1 OpenBLAS

Repository: https://github.com/OpenMathLib/OpenBLAS. Tag v0.3.34, commit
`e0166008be8e466242aa76b2ff75ce3f0fbf574a`, released 2026-07-16. Licence BSD-3-Clause.
README: "OpenBLAS is an optimized BLAS ... library based on GotoBLAS2 1.13 BSD version."

- Where the kernels live. docs/developers.md: "To find the kernel currently used for a particular
  supported CPU, please check the corresponding `kernel/$(ARCH)/KERNEL.$(CPU)` file". The call
  tree is `interface/gemm.c` -> `driver/level3/level3.c` -> "gemm assembly kernels at kernel/".
  The same document: "The `driver/level3/level3.c` is the implementation of Goto's algorithm."
  The source tree labels `kernel` "Optimized assembly kernels for CPU architectures".
- Haswell: kernel/x86_64/KERNEL.HASWELL has `SGEMMKERNEL = sgemm_kernel_8x4_haswell_2.c`.
  That is a C file whose body is GCC inline assembly (`vbroadcastss`, `vfmadd231ps` on ymm
  registers). Packing routines: `SGEMMINCOPY = ../generic/gemm_ncopy_8.c`, and others.
  param.h (HASWELL, x86_64): `SGEMM_DEFAULT_UNROLL_M 8`, `SGEMM_DEFAULT_UNROLL_N 4`,
  `SGEMM_DEFAULT_P 320`, `SGEMM_DEFAULT_Q 320`. Other sgemm files sit in the same directory,
  for example `sgemm_kernel_16x4_haswell.S` and `sgemm_kernel_16x4_skylakex.c`.
  In driver/level3/level3_thread.c, GEMM_Q is the step in k ("Determine step size in k") and
  GEMM_P the step in m.
- ARM64 and Apple: kernel/arm64/KERNEL.NEOVERSEN1 uses
  `SGEMMKERNEL = sgemm_kernel_$(SGEMM_UNROLL_M)x$(SGEMM_UNROLL_N).S` (assembly).
  KERNEL.VORTEX and KERNEL.VORTEXM4 each contain only `include $(KERNELDIR)/KERNEL.NEOVERSEN1`.
  param.h gives VORTEX and VORTEXM4 an sgemm unroll of 16x4, with P 512, Q 1024 and R 4096.
  The README lists "Apple Vortex: preliminary support based on ThunderX2/3" and
  "Apple VortexM4: preliminary support based on ThunderX2/3, SME kernels for
  SGEMM,SSYMM,STRMM,SSYRK,SSYR2K".
  param.h: `#if defined(ARMV9SME) || (defined(VORTEXM4)&&defined(__clang__))` defines
  `USE_SGEMM_KERNEL_DIRECT 1`. kernel/Makefile.L3 sets `USE_SME = 1` for VORTEXM4 unless the
  compiler is GCC, and uses `sgemm_direct_arm64_sme1.c` (copyright Qualcomm, SPDX
  BSD-3-Clause-Clear). So OpenBLAS on an M4 built with clang has an SME sgemm path.
- Threads. README: the environment variables are `OPENBLAS_NUM_THREADS`, `GOTO_NUM_THREADS`
  and `OMP_NUM_THREADS`, with "The priorities are OPENBLAS_NUM_THREADS > GOTO_NUM_THREADS >
  OMP_NUM_THREADS". With `USE_OPENMP=1` only `OMP_NUM_THREADS` is honoured.
  `openblas_set_num_threads(int)` also exists.
  driver/level3/level3_thread.c divides m and n ranges between threads. Each thread copies its
  own block of A ("Copy local region of A into workspace") and part of B, and sets a flag
  ("Set flag so other threads can access local region of B"). Other threads then use that
  packed B ("Get regions of B from other threads and apply kernel"). Threads share packed B
  instead of each packing all of it.
- Runtime CPU choice: building with `DYNAMIC_ARCH=1` gives "runtime detection of the target cpu".

### 5.2 Apple Accelerate

Apple's web documentation was read through the JSON that developer.apple.com serves for each
page. The pages carry no version string; they were read on 2026-11-25. The headers come from
MacOSX SDK 26.5 (`xcrun --show-sdk-version`).

- cblas_sgemm page: https://developer.apple.com/documentation/accelerate/cblas_sgemm(_:_:_:_:_:_:_:_:_:_:_:_:_:_:).
  Abstract: "Multiplies two matrices (single-precision)." Availability listed: macOS 13.3,
  iOS 16.4. Discussion: "This function multiplies A * B and multiplies the resulting matrix by
  alpha. It then multiplies matrix C by beta. It stores the sum of these two products in
  matrix C."
  The LDA wording is column-major: "if you are passing a matrix A[m][n], the value should be
  m". The BLAS overview page warns: "In row-major ordering, the leading dimension is the second
  dimension of a matrix." For `CblasRowMajor` with no transpose, lda = k, ldb = n and ldc = n.
- The ACCELERATE_NEW_LAPACK define. The note on both the BLAS page
  (https://developer.apple.com/documentation/accelerate/blas-library) and the sgemm page
  quotes: "To use the new interfaces, define `ACCELERATE_NEW_LAPACK` before including the
  Accelerate or vecLib headers. For ILP64 interfaces, also define `ACCELERATE_LAPACK_ILP64`."
  Also: "Starting with ... macOS 26 ... the libraries are in line with LAPACK 3.12.0."
- Header to include: `<Accelerate/Accelerate.h>`. That pulls in vecLib, and vecLib.h does
  `#if defined(ACCELERATE_NEW_LAPACK)` -> `#include <vecLib/cblas_new.h>`, otherwise
  `<vecLib/cblas.h>`. In the old cblas.h, cblas_sgemm is marked
  `API_DEPRECATED("An updated CBLAS interface supporting ILP64 is available. Please compile with
  -DACCELERATE_NEW_LAPACK ...", macos(10.2,13.3), ...)`.
  Observed on Apple clang 21: `-std=c11 -Wall -Wextra -pedantic -Werror` without the define
  fails with "error: 'cblas_sgemm' is deprecated: first deprecated in macOS 13.3 ...
  [-Werror,-Wdeprecated-declarations]". With `-DACCELERATE_NEW_LAPACK` it compiles clean.
  The course's blas.c therefore needs the define, or the -Werror build breaks.
- How Apple says it is implemented. The Accelerate overview
  (https://developer.apple.com/documentation/accelerate) says: "Accelerate provides
  high-performance, energy-efficient computation on the CPU by leveraging its vector-processing
  capability. The following Accelerate libraries abstract that capability so that code written
  for them executes appropriate instructions for the processor available at runtime". BLAS and
  LAPACK are on that list. The SDK header vecLib/thread_api.h (macOS 15.0+) has
  `BLAS_THREADING_MULTI_THREADED ... = 0, // Accelerate decides how many threads to use` and
  `BLAS_THREADING_SINGLE_THREADED`, set per thread with `BLASSetThreading()`.
  Apple's pages read here say nothing more about the implementation: no AMX, no SME, no matrix
  coprocessor, no kernel shapes, no block sizes.
- Unconfirmed claims, not to be stated as fact:
  - "The M1 chips have undocumented matrix-matrix assembly instructions that only Apple can
    compile for, which is where this speedup comes from". Unconfirmed; source: Simon Boehm,
    https://siboehm.com/articles/22/Fast-MMM-on-CPU, Notes section, August 2022.
    He also reports NumPy with Accelerate at 1 ms and with OpenBLAS at ~8 ms on an M1 Pro.

---

## 6. Compiler facts

Documents read: GCC 16.2.0 manual (latest full release per https://gcc.gnu.org/onlinedocs/),
https://gcc.gnu.org/onlinedocs/gcc-16.2.0/gcc/Optimize-Options.html and
https://gcc.gnu.org/onlinedocs/gcc-16.2.0/gcc/Vector-Extensions.html. For comparison, the same
Optimize-Options page in the 11.4.0, 12.2.0, 13.2.0 and 14.2.0 manuals. Clang 23.1.0
(latest release with docs on https://releases.llvm.org/; 23.1.4 exists but has no docs page):
https://releases.llvm.org/23.1.0/tools/clang/docs/UsersManual.html, ClangCommandLineReference.html,
LanguageExtensions.html, and LLVM 23.1.0 https://releases.llvm.org/23.1.0/docs/Vectorizers.html.
"Observed" means Apple clang 21.0.0 on this Mac. There is no GCC on this Mac
(`/usr/bin/gcc` is Apple clang), so no GCC behaviour was observed.

### 6.1 Which -O level auto-vectorizes

- GCC 16.2: `-ftree-loop-vectorize` and `-ftree-slp-vectorize` are each "enabled by default at
  -O2 and by -ftree-vectorize, -fprofile-use, and -fauto-profile". -O2 also turns on
  `-fvect-cost-model=very-cheap`, and -O3 turns on `-fvect-cost-model=dynamic`.
  `-ftree-vectorize` "enables -ftree-loop-vectorize and -ftree-slp-vectorize if not explicitly
  specified".
  History: the GCC 11.4.0 manual says "enabled by default at -O3". GCC 12.2.0 and later say -O2.
  So an older GCC (11 or earlier) does not vectorize at -O2.
- Clang/LLVM 23.1.0 docs: "Both the Loop Vectorizer and the SLP Vectorizer are enabled by
  default." The docs do not say which -O levels.
  Observed on Apple clang 21 (`clang -### -c`): at -O2 and -Os the driver passes
  `"-vectorize-loops" "-vectorize-slp"`; at -O3 it adds `"-extra-vectorizer-passes"`; at -Oz it
  passes only `"-vectorize-slp"`; at -O0, -O1 and -O it passes neither.
  For `for (i) c[i] += a[i] * b[i]` with restrict pointers, the code had NEON `.4s` vector
  instructions at -O2 and -O3 (fmla.4s), and none at -O0, -O1, -Os or -Oz.

### 6.2 Turning the vectorizers off

- GCC: `-fno-tree-loop-vectorize` and `-fno-tree-slp-vectorize` (the negative forms of the
  documented flags). The GCC manual describes only the positive `-ftree-vectorize`, so whether
  `-fno-tree-vectorize` alone undoes both after -O2 enabled them is not stated in the text read.
  This was not tested here.
- Clang docs: `-fno-vectorize` (Vectorizers.html: "$ clang ... -fno-vectorize file.c") and
  `-fno-slp-vectorize`. ClangCommandLineReference lists the GCC spellings as aliases:
  "-fvectorize, -fno-vectorize, -ftree-vectorize" and
  "-fslp-vectorize, -fno-slp-vectorize, -ftree-slp-vectorize".
- Observed on Apple clang 21:
  - `-fno-tree-vectorize -fno-tree-slp-vectorize` is accepted with
    `-std=c11 -Wall -Wextra -pedantic -Werror`, and the -O2 and -O3 output has no vector
    instructions.
  - `-fno-vectorize -fno-slp-vectorize` also works.
  - **`-fno-tree-loop-vectorize` is rejected**: "clang: error: unknown argument:
    '-fno-tree-loop-vectorize'".
  So the only single spelling both compilers take is `-fno-tree-vectorize -fno-tree-slp-vectorize`.
  For GCC, the documentation-backed pair is `-fno-tree-loop-vectorize -fno-tree-slp-vectorize`,
  which clang rejects. If the Makefile wants that pair, it has to pick flags per compiler, as
  the plan already says.

### 6.3 -ffp-contract: may a*b+c become one fused multiply-add?

- GCC 16.2: "The default is -ffp-contract=off for C in a standards compliant mode (-std=c11 or
  similar), -ffp-contract=fast otherwise." The 14.2.0 manual says the same. `=on` is
  "implemented for C and C++, where it enables contraction within one expression, but not
  across different statements".
- GCC 11.4.0, 12.2.0 and 13.2.0 manuals: "The default is -ffp-contract=fast." They also say of
  `=on`: "This is currently not implemented and treated equal to -ffp-contract=off".
  So with `-std=c11`, GCC 13 and older fuse across statements by default, while GCC 14 and newer
  do not fuse at all. Under `-std=gnu11` every version fuses.
- Clang 23.1.0: "Clang takes advantage of this by default (on)". The value `on` means "enable C
  and C++ standard compliant fusion in the same statement unless dictated by pragmas (default
  for languages other than CUDA/HIP)"; `fast` is the CUDA default and `fast-honor-pragmas` the
  HIP default. `-ffast-math` sets fp-contract to fast.
- Observed on Apple clang 21 (arm64): the driver passes `"-ffp-contract=on"`.
  `return a * b + c;` compiles to `fmadd s0, s0, s1, s2` at -O0 and -O2, with or without
  `-std=c11`. `float t = a * b; return t + c;` stays `fmul` + `fadd` unless
  `-ffp-contract=fast` is given. `-ffp-contract=off` gives `fmul` + `fadd` for both.
  The vectorized `c[i] += a[i] * b[i]` loop uses `fmla.4s`, which is fused.
- Consequence: the same matmul_ikj source rounds differently on Apple clang (fused) than on
  GCC 14+ with -std=c11 (not fused). The per-element error against matmul_ref will differ
  between machines. Passing `-ffp-contract=off` on both compilers would make the scalar
  variants round the same way.

### 6.4 `__attribute__((vector_size(N)))`

- GCC 16.2, "Using Vector Instructions through Built-in Functions": "the attribute specifies the
  vector size for the variable, measured in bytes" and "Only sizes that are positive
  power-of-two multiples of the base type size are currently allowed." On narrower hardware:
  "Specifying a combination that is not valid for the current architecture causes GCC to
  synthesize the instructions using a narrower mode. For example, if you specify a variable of
  type V4SI and your architecture does not allow for this specific SIMD type, GCC produces code
  that uses 4 SIs."
  Allowed operators: `+, -, *, /, unary minus, ^, |, &, ~, %`. A scalar operand is broadcast
  ("the compiler transforms the scalar operand into a vector"). Subscripting works like an
  array. The page's own union example loads with `memcpy (&x, ptr, sizeof x);`.
- Clang 23.1.0 LanguageExtensions: "GCC vector types are created using the vector_size(N)
  attribute. The argument N specifies the number of bytes that will be allocated for an object
  of this type. The size has to be a multiple of the size of the vector element type." The
  operator table marks `+,-,*,/,%` and `[]` as supported for GCC vectors. **The clang docs say
  nothing about hardware narrower than N.**
- Observed on Apple clang 21, with `typedef float v8 __attribute__((vector_size(32)));`:
  - arm64 (128-bit NEON): `*c = *a + *b` compiles to `ldp q1, q0` / two `fadd.4s` /
    `stp q1, q0`, i.e. two 16-byte halves. `_Alignof(v8)` is 16.
  - x86-64 target without AVX (`-target x86_64-apple-macos13`): two `addps`, also
    `_Alignof(v8) == 16`. When the operand is a dereferenced `v8 *`, the compiler emits
    `addps (%rdx), %xmm0`, an SSE memory operand that requires 16-byte alignment.
  - With `-mavx2`: one `vaddps` on ymm, and `_Alignof(v8)` becomes 32. The vector type's
    alignment, and so the layout of any struct holding one, changes with `-march`. Keep v8 out
    of shared headers when one file gets `-march=native` and the others do not.
  - Loading and storing through `memcpy` (the plan's choice) compiles to unaligned
    `ldp`/`stp` on arm64, `movups` without AVX and `vmovups` with AVX2. That works for any
    pointer.
  - No -Wpsabi warning appeared on clang for a v8 passed by value to an x86-64 target without
    AVX. GCC's behaviour was not checked.

---

## 7. Cache sizes for the blocking lesson

### 7.1 This Mac (Apple M4 Pro): sysctl, read today

`sysctl -a | grep -i cache`, plus `sysctl` for the CPU keys. The machine reports
`machdep.cpu.brand_string: Apple M4 Pro`, `hw.model: Mac16,7`, `hw.nperflevels: 2`,
`hw.perflevel0.name: Performance` (10 physical cores) and `hw.perflevel1.name: Efficiency`
(4 physical cores).

Keys read, with their values:
- `hw.perflevel0.l1dcachesize: 131072` (128 KiB L1d per performance core)
- `hw.perflevel0.l1icachesize: 196608` (192 KiB)
- `hw.perflevel0.l2cachesize: 16777216` (16 MiB), with `hw.perflevel0.cpusperl2: 5`
- `hw.perflevel1.l1dcachesize: 65536`, `hw.perflevel1.l2cachesize: 4194304`, `hw.perflevel1.cpusperl2: 4`
- `hw.l1dcachesize: 65536`, `hw.l2cachesize: 4194304`. These unqualified keys are the
  efficiency cores' values, not the performance cores'.
- `hw.cachelinesize: 128`, `hw.pagesize: 16384`
- No L3 key is present.

What the keys mean, from Apple's "Determining system capabilities"
(https://developer.apple.com/documentation/kernel/1387446-sysctlbyname/determining_system_capabilities,
read as JSON today):
- "Lower values of N indicate higher-performance core types."
- "Querying the following parameters is equivalent to querying the per-performance-level
  information for the least performant core. For example, `hw.l1dcachesize` is equivalent to
  `hw.perflevel[N].l1dcachesize`, where N is `hw.nperflevels` minus one."
- `hw.perflevelN.cpusperl2`: "the number of cores that share an L2 cache".
- `hw.cachelinesize`: "The size in bytes of the system cache line."
- The page names the use case itself: "determine the size of the L2 cache and the number of
  processor cores that share it to perform software cache-blocking optimization."

Code that reads `hw.l1dcachesize` on this Mac gets 64 KiB, the E-core value, not the P-core's
128 KiB. No Apple document read today lists M4 Pro cache sizes; the numbers above come only
from sysctl on this machine.

### 7.2 A current x86-64 core: Intel Golden Cove

Source: Intel 64 and IA-32 Architectures Optimization Reference Manual: Volume 1, Document
Number 248966-051US, October 2026. Fetched from https://cdrdv2.intel.com/v1/dl/getContent/671488,
which redirects to https://cdrdv2-public.intel.com/930021/248966-051-optimization-reference-manual-vol1.pdf.

- Section 2.2: "Intel processors based on Sapphire Rapids microarchitecture use Golden Cove
  cores". Sapphire Rapids is the 4th generation Intel Xeon Scalable family. Section 2.3 says
  12th Generation Intel Core (Alder Lake) P-cores are Golden Cove too.
- Figure 2-2 ("Processor Core Pipeline Functionality of the Golden Cove Microarchitecture")
  labels a "48KB DCU" (the L1 data cache) and a "1.25MB Client / 2MB Server MLC" (L2), and
  shows "32KB Instruction Cache". Section 2.4: "Mid-level cache size increased to 2MB on server
  parts; remains 1.25MB on client parts."
- Line size: Section 3.6.7 says "first-level cache lines are 64 bytes". Table 2-9 (Ice Lake
  Client) lists line size 64 for L1, L2 and L3, with L1 "48KB/8" and L2 "512KB/8". The Golden
  Cove section has no table of its own, so the 64-byte line for Golden Cove rests on the
  general statement in 3.6.7.
- So a Sapphire Rapids server core has 48 KB L1d, 2 MB L2 and 64-byte lines. This Mac's
  performance core has 128 KiB L1d, 16 MiB L2 shared by 5 cores, and 128-byte lines.

---

## Could not confirm

- torch.allclose and infinities: the PyTorch 2.15 page says nothing about inf (it mentions only
  NaN and `equal_nan`).
- Clang's documentation does not say at which -O levels the vectorizers run ("enabled by
  default" only). Section 6.1's answer is observation of Apple clang 21 alone, not upstream
  clang, and not documented.
- Clang's documentation does not say what happens when vector_size(N) is wider than the
  hardware vector. Section 6.4's answer is observation only.
- Clang's command-line reference lists `-ftree-vectorize` and `-ftree-slp-vectorize` as aliases
  but does not print the `-fno-tree-*` forms. That they are accepted and work was observed on
  Apple clang 21 only.
- GCC: the manual does not state that `-fno-tree-vectorize` turns off both the loop and SLP
  vectorizers after -O2 has enabled them. No GCC is installed here, so no GCC behaviour was
  observed: not vectorization, not fp-contract, not -Wpsabi for 32-byte vectors without AVX.
- Apple Accelerate: Apple's pages read today say nothing about how cblas_sgemm is implemented
  (AMX, SME, kernel shapes, block sizes), beyond "leveraging its vector-processing capability"
  and the threading header. The M1 "undocumented matrix instructions" claim stays
  unconfirmed (source: Boehm).
- Apple has no document giving M4 Pro L1/L2 sizes or line size. The values come only from
  sysctl on this Mac, interpreted by Apple's sysctl documentation.
- AMD: the AMD documentation could not be fetched. amd.com served a JavaScript "Loading
  application..." page to curl, and the fetch tool timed out on
  https://www.amd.com/content/dam/amd/en/documents/epyc-technical-docs/tuning-guides/58015-epyc-9004-tg-architecture-overview.pdf.
  No AMD cache figures are given. A search result summary claimed Zen 4 has 32 KB L1d and
  1 MB L2, but that was not read from AMD's document and is not reported as fact.
- Goto and van de Geijn: GFLOPS values appear only in graphs that do not survive text
  extraction, so no numeric speed-ups are recorded from the paper. Its publication details
  come from OpenBLAS's docs, not from the PDF, which is the preprint with placeholder volume
  data.
- Algorithmica: the speeds for the kernel and blocked steps appear only in SVG charts. Text
  numbers exist only for the steps listed in 4.a. The numbers in its hidden HTML comment are
  not shown on the page.
- Licences: Algorithmica has no licence file (copyright Sergey Slotin, 2021-2022). Simon
  Boehm's page states no licence. Both can be cited and linked; neither can be copied.
- BLIS has no M2, M3 or M4 configuration; `firestorm` (A14/M1) is the nearest.
- hyperfine v2.0.0 prints no median in the terminal. That is confirmed absent, so any lesson
  wording that says "hyperfine prints the median" would be wrong.
- Not covered by this task, though plans/gpu.md cites it in "Go deeper": CS:APP chapter 6 was
  not read.
