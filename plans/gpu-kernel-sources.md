# How the best sources teach GPU kernel writing: notes for gpu modules 02 to 09

Fetched and read on 2026-11-26. Every note below comes from a page or file fetched
in that session; URL, version or commit, and date are in the table. Notes are in my
own words. "My reading" marks a conclusion I drew from code or text that the source
does not state itself. Hardware named with a number is the source's hardware, not ours.

Plan read first: plans/gpu-outline.md (modules 02 to 09) and plans/gpu.md (rules).

## (a) Sources

| # | Title | URL | Version / date | Licence | What was read |
|---|---|---|---|---|---|
| 1 | CUDA Programming Guide (NVIDIA) | https://docs.nvidia.com/cuda/cuda-programming-guide/ | v13.5, last updated 2026-10-31 | Copyright 2007-2026 NVIDIA, all rights reserved | Full TOC; 1.2 Programming Model; 2.3 Writing SIMT Kernels; 2.5 Asynchronous Execution; 5.6 Floating-Point Computation (both halves) |
| 2 | CUDA C++ Best Practices Guide (NVIDIA) | https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/ | v13.5, last updated 2026-11-02 | Copyright 2007-2026 NVIDIA, all rights reserved | Whole page in three parts (ch 1-21) |
| 3 | Programming Massively Parallel Processors, 4th ed. (Hwu, Kirk, El Hajj) and its public course material | https://shop.elsevier.com/books/programming-massively-parallel-processors/hwu/978-0-323-91231-0 ; https://shop.elsevier.com/books/catalog/isbn/9780443439001 (5th ed.) ; https://canvas.illinois.edu/courses/53796/assignments/syllabus ; https://developer.nvidia.com/accelerated-computing-teaching-kit-syllabus | 4th ed. 2022 (page says 2022-05-28); 5th ed. 2026; ECE 408 Spring 2025 syllabus; DLI Teaching Kit syllabus (undated) | Book: commercial, Elsevier copyright. Syllabi: no licence stated | Books: chapter-level TOC and blurb only. ECE 408: lecture and lab schedule. Teaching Kit: module and slide titles. No book text, no slides |
| 4 | OLCF / NVIDIA CUDA Training Series | https://www.olcf.ornl.gov/cuda-training-series/ ; github.com/olcf/cuda-training-series | Sessions 2020-01 to 2021-10; repo at commit 9cd77d53 (2021-10-13) | Page: (c) 2026 OLCF. Repo: no licence file (GitHub reports none) | Session list; readmes of hw1, hw2, hw3, hw4, hw5, hw8, hw12; grep of hw2/matrix_mul_shared.cu and hw5/reductions.cu |
| 5 | Simon Boehm, How to Optimize a CUDA Matmul Kernel for cuBLAS-like Performance: a Worklog | https://siboehm.com/articles/22/CUDA-MMM ; github.com/siboehm/SGEMM_CUDA | Post dated 2022-12-31; repo at commit 5a7dcc51 | Post: no licence stated. Repo: MIT | Whole post; sgemm.cu and src/runner.cu (timing, verify, cuBLAS call) |
| 6 | NVIDIA developer blog posts: Harris "An Even Easier Introduction to CUDA"; Harris "How to Implement Performance Metrics in CUDA C/C++"; Harris "How to Access Global Memory Efficiently"; Harris "Using Shared Memory in CUDA C/C++"; Harris "How to Optimize Data Transfers"; Luitjens "Faster Parallel Reductions on Kepler"; Harris "Optimizing Parallel Reduction in CUDA" (slide deck) | developer.nvidia.com/blog/even-easier-introduction-cuda/ ; .../how-implement-performance-metrics-cuda-cc/ ; .../how-access-global-memory-efficiently-cuda-c-kernels/ ; .../using-shared-memory-cuda-cc/ ; .../how-optimize-data-transfers-cuda-cc/ ; .../faster-parallel-reductions-kepler/ ; https://developer.download.nvidia.com/assets/cuda/files/reduction.pdf | 2017-01-25 (updated 2025-05-02); 2012-11-07; 2013-01-07; 2013-01-28; 2012-12-04; 2014-02-13; deck undated | NVIDIA pages; no licence line in the fetched text; treat as all rights reserved | All seven in full |
| 7 | GPU MODE lectures | https://github.com/gpu-mode/lectures | commit 77a8df41 (2026-09-09) | Apache-2.0 (repo licence) | README (lecture list); folders lecture_001, 008, 009, 012 (file lists, load_inline.py, pytorch_square.py, the five reduce kernels, accuracy.py, nondeterminism.py, flash_attention.cu comments) |
| 8 | Horace He, Making Deep Learning Go Brrrr From First Principles | https://horace.io/brrr_intro.html | 2022 (from its BibTeX) | No licence stated | Whole essay |
| 9 | karpathy/llm.c | https://github.com/karpathy/llm.c | commit f1e2ace6 (2025-05-10) | MIT | dev/cuda/README.md; common.h (validate_result, benchmark_kernel); headers and drivers of layernorm_forward.cu, softmax_forward.cu, attention_forward.cu, gelu_forward.cu, matmul_forward.cu; dev/cuda/Makefile flags; train_gpt2.cu includes; test_gpt2.cu tolerances |
| 10 | vLLM csrc/ and tests/kernels at tag v0.2.0 | https://github.com/vllm-project/vllm/tree/v0.2.0 | commit e2fb71ec (2023-09-28) | Apache-2.0; reduction_utils.cuh and attention_kernels.cu also carry NVIDIA FasterTransformer Apache-2.0 headers | In full: activation_kernels.cu, layernorm_kernels.cu, reduction_utils.cuh, pos_encoding_kernels.cu, cache_kernels.cu, attention/attention_kernels.cu, attention_utils.cuh, dispatch_utils.h, the .cpp bindings, setup.py (flags, extensions), all of tests/kernels; grep of vllm/model_executor/layers/attention.py and vllm/worker/worker.py |
| 11 | Kwon et al., Efficient Memory Management for LLM Serving with PagedAttention | https://arxiv.org/abs/2309.06180 | v1, 2023-09-12 (SOSP 2023) | CC BY 4.0 (arXiv); ACM notice: copyright held by owners | Sections 4 (method), 5 (implementation, kernels), 7.1-7.2 (kernel microbenchmark, block size), via pdftotext |
| 12 | Dao et al., FlashAttention (2205.14135); Dao, FlashAttention-2 (2307.08691); Milakov and Gimelshein, Online normalizer calculation for softmax (1805.02867) | https://arxiv.org/abs/2205.14135 ; https://arxiv.org/abs/2307.08691 ; https://arxiv.org/abs/1805.02867 | v2 2022-06-23; v1 2023-07-17; v2 2018-07-28 | All three: arXiv non-exclusive distribution licence 1.0 | FA1: sections 2-3 and the speed claims; FA2: sections 3-4; online softmax: whole paper. Via pdftotext. Appendices of FA1 not read |
| 13 | NVIDIA Compute Sanitizer | https://docs.nvidia.com/compute-sanitizer/ComputeSanitizer/index.html | v2026.4.0 | NVIDIA documentation; copyright line not in the part read | First 100k of 125k characters (tools, options, compile flags, limits) |
| 14 | cuBLAS documentation | https://docs.nvidia.com/cuda/cublas/ | 13.5 | NVIDIA documentation; copyright line not in the parts read | Characters 0-300k of 326k: data layout, math modes, tensor-core rules, reproducibility, `cublas<t>gemm` |
| 15 | Stanford CS149 Assignment 3, A Simple CUDA Renderer | https://github.com/stanford-cs149/asst3 | commit 43bf4722 (2025-10-31) | No licence file (GitHub reports none) | README.md in full |

Fifteen entries, about twenty-five documents. All read in full except where the last column says "part".

## (b) Notes by source

### 1. CUDA Programming Guide, v13.5

Order of the guide (rewritten since the old "CUDA C++ Programming Guide"): Part 1
introduces the model; Part 2 is programming (2.1 CUDA C++, 2.2 CUDA Python, 2.3 SIMT
kernels, 2.4 Tile kernels, 2.5 asynchronous execution, 2.6 unified memory, 2.7 nvcc);
Part 3 advanced; Part 4 features (graphs, cooperative groups, async copies...); Part 5
appendices (compute capabilities, floating point, memory model). There is no chapter
called "memory hierarchy" and none called "timing"; timing lives inside 2.5.

1.2 Programming Model, in order: host and device, a kernel as a device function
launched as many threads; the hardware (SMs in GPCs, register file, unified L1 and
shared memory with a configurable split); threads in blocks in a grid (1D-3D, all
blocks the same size); clusters (CC 9.0+, optional); warps of 32 and SIMT with
masking on divergence; tile programming (a block-level model that coexists with
SIMT); GPU memory (global, host, unified address space, registers, shared, L1/L2/
constant caches, unified memory). Warnings: blocks run in any order, never depend on
another block's result; block sizes a multiple of 32; avoid divergence within a warp;
registers per thread times threads per block must fit or the launch fails.

2.3 Writing SIMT Kernels, in order: SIMT basics; thread hierarchy and the built-ins
(`gridDim`, `blockDim`, `blockIdx`, `threadIdx`; x varies fastest); block
synchronisation; a table of memory spaces (scope, lifetime, location); global memory
with a vecAdd example (`cudaMalloc`, `cudaMemcpy`, `cudaFree`; kernels return void);
shared memory (static and dynamic via the third launch argument; only one dynamic
array per kernel, carve it by hand; alignment warning); registers (spills from
`-maxrregcount`); local memory (lives in device memory); constant memory (64 KB);
caches; distributed shared memory. Then 2.3.4 Memory Performance uses matrix
transpose as its running example: coalescing in 32-byte transactions (worst case 32
threads in 32 segments: 12.5% efficiency), shared memory with 32 banks of 32 bits,
broadcast on same address, a 32x32 tile with a 32-way conflict on column access,
fixed by padding to 32x33. 2.3.5 Atomics: no grid-wide sync exists; a sum_reduce
example (2^18 elements, blocks of 256, shared-memory sum per block then one atomic
add per block); warns a non-atomic update of a shared total gives run-dependent
results; recommends CCCL primitives over hand-written reductions. 2.3.7 Occupancy:
CC 10.0 limits (1024 threads per block, 2048 per SM, 65536 registers per SM, 48 KB
static shared per block) and worked occupancy examples; `nvcc --resource-usage`.
This page has no warp-shuffle reduction and no tree reduction.

2.5 Asynchronous Execution: streams as in-order queues; pinned host memory needed for
truly async copies; events as markers in a stream; timing = record a start event,
launch, record a stop event, synchronise the stream, `cudaEventElapsedTime` in ms
(an event takes its timestamp when it reaches the head of the stream). Launches
return at once; a launch error may only surface at the next synchronisation;
`cudaGetLastError` reads and clears, `cudaPeekAtLastError` reads only;
`CUDA_LAUNCH_BLOCKING=1` makes every launch synchronous for debugging (slow). It
does not discuss host timers or event resolution.

5.6 Floating-Point Computation: GPUs follow IEEE 754-2019 with fixed rounding mode
and masked exceptions; contraction of `x*y+z` into FMA is on by default (`-fmad=true`)
and host results can differ because host FMA depends on flags; `__half` is IEEE
(max 65504, epsilon 2^-10), `__nv_bfloat16` is listed as not IEEE compliant and as
needing CC 8.0 or higher; many math functions have no native half/bf16 version and
are emulated by converting to float. `--use_fast_math` = `-ftz=true`,
`-prec-div=false`, `-fmad=true`, and maps `expf` to `__expf`, `tanhf` to `__tanhf`,
`x/y` to `__fdividef`. Errors: `expf` 2 ulp; `__expf` 2 + floor(1.173 |x|) ulp (grows
with |x|); `__fdividef` 2 ulp; `rsqrtf` 2 ulp; `__tanhf` relative error 2^-11.
Warns that a difference between host and device results does not by itself mean the
GPU is wrong.

### 2. CUDA C++ Best Practices Guide, v13.5

Order: overview, APOD (assess, parallelize, optimize, deploy), heterogeneous
computing, profiling, parallelizing, getting started, getting the right answer,
optimizing, performance metrics (ch 9), memory optimizations (ch 10), execution
configuration (11), instruction optimization (12), control flow (13), deployment
(14-18), recommendations (19), nvcc switches (20).

Getting the right answer (ch 7): compare with a known-good result after each change;
bitwise equality is not always possible, use a small epsilon; write kernels as short
`__device__` functions and mark them `__host__ __device__` so the same code can be
tested on CPU and GPU; parallel reordering changes float sums; FMA changes results.

Metrics (ch 9): CPU timers need `cudaDeviceSynchronize()` before start and stop (used
sparingly, it stalls the pipeline); events measure on the GPU clock with a resolution
of about half a microsecond. Theoretical bandwidth = memory clock x bus width in bytes
x 2 / 1e9 (V100: 898 GB/s); effective bandwidth = (bytes read + bytes written) / 1e9
/ seconds; use the same divisor (1e9 vs 1024^3) on both or the ratio lies. "Use
effective bandwidth as a metric" is a high-priority item.

Memory (ch 10): host-device transfers are the first cost (V100 898 GB/s on device vs
16 GB/s PCIe Gen3 x16); keep data on the device, batch small copies; pinned memory
reaches about 12 GB/s on Gen3 x16 (`cudaHostAlloc`, `cudaHostRegister`), do not
overuse it; `cudaMemcpyAsync` needs pinned memory and a non-default stream.
Coalescing (CC 6.0+, 32-byte transactions): aligned sequential, misaligned (V100
offsetCopy about 790 GB/s when aligned, loss smaller than predicted because adjacent
warps reuse lines), strided (stride 2 = 50% efficiency). Shared memory matrix
multiply, effective bandwidth on V100: C = AB simpleMultiply 119.9 GB/s, A tile in
shared memory 144.4, A and B tiles 195.5 (the gain is from removing redundant loads,
not coalescing); C = AA^T naive 12.8 GB/s, transposed tile in shared 140.2, padded
tile [TILE_DIM][TILE_DIM+1] 199.4.

Execution configuration (ch 11): occupancy helps hide latency but higher is not
always faster; register example (37 registers: 75% occupancy at 128-thread blocks,
63% at 320); block size a multiple of 32, at least 64, 128-256 a good start; more
blocks than SMs, ideally thousands. Instruction (ch 12): `__expf` and
`-use_fast_math` are fast and less accurate, use selectively; suffix constants with
`f`; `rsqrtf()` explicitly. Control flow (ch 13): divergence serialises a warp; make
conditions warp-aligned. Ch 19 summarises three strategies: maximise parallel
execution, optimise memory use, optimise instruction use; the priority labels sit
inline (high: profile first, effective bandwidth as the metric, minimise transfers,
coalesce global accesses, minimise global memory use, avoid divergence).

### 3. PMPP 4th edition (table of contents and public course material only)

Chapters (Elsevier page): 1 Introduction. Part I: 2 Heterogeneous data parallel
computing; 3 Multidimensional grids and data; 4 Compute architecture and scheduling;
5 Memory architecture and data locality; 6 Performance considerations. Part II: 7
Convolution (constant memory and caching); 8 Stencil; 9 Parallel histogram; 10
Reduction and minimizing divergence; 11 Prefix sum; 12 Merge. Part III: 13 Sorting;
14 Sparse matrix; 15 Graph traversal; 16 Deep learning; 17 MRI; 18 Electrostatic
potential; 19 Computational thinking. Part IV: 20 Heterogeneous cluster and CUDA
streams; 21 Dynamic parallelism; 22 Advanced practices; 23 Conclusion. Appendix A
Numerical considerations. The blurb lists as new: stencil, reduction and sorting
chapters, a GPU architecture chapter (Ampere examples), and "a new optimization
checklist".

A 5th edition exists (Elsevier page https://shop.elsevier.com/books/catalog/isbn/9780443439001,
fetched: same three authors, dated 2026-02-27 under the edition heading and
2026-06-03 under product details). Its blurb lists an expanded optimization
checklist, new chapters on filtering, wavefront parallelism, advanced matrix
multiplication optimizations and large language models, and more on warp-level
programming, cooperative groups, C++ atomics and multi-GPU (NCCL, NVSHMEM). Its
chapter list on that page: 1-9 as in the 4th; 10 Reduction; 11 Prefix sum; 12 Merge;
13 Sorting; 14 Filtering; 15 Sparse matrix; 16 Wavefront algorithms; 17 Graph
traversal; 18 Deep learning; 19 Multi-GPU API; 20 Electrostatic potential map; 21
Computational thinking; 22 Heterogeneous cluster; 23 Advanced optimizations for
matrix multiplication; 24 Advanced practices; 25 Conclusion. (No chapter titled for
LLMs appears in that list although the blurb names one.) Our outline's library cites
the 4th edition.

ECE 408 Spring 2025 (UIUC): uses the 3rd edition chapter numbers. Lectures 2-6:
intro to CUDA, execution model, memory model, locality and tiled matrix multiply,
generalized tiling and DRAM bandwidth; then convolution (7-9), deep learning and
transformers (10-12), reductions (13), a GPT-2 project (14, 24-25), scan, histogram,
sparse, profiling with Nsight (guest), streams. Labs: device query, vector add,
simple matmul, tiled matmul, 3D convolution, list reduction, scan, histogram, SpMV.
Labs are graded 90% on correctness (data sets passed) and 10% quiz; the syllabus
names no performance grading.

DLI GPU Teaching Kit syllabus (NVIDIA, built on the same book): module 2 intro to
CUDA C (allocation and data movement before threads and kernels; Nsight; unified
memory); module 3 parallelism model (multidimensional configuration; grayscale and
blur examples; thread scheduling); module 4 memory and data locality (4.1 memories,
4.2 tiled algorithms, 4.3-4.4 tiled matmul and its kernel, 4.5 arbitrary sizes);
module 5 warps and control divergence; module 6 DRAM bandwidth and coalescing; module
9 reduction (basic kernel, better kernel); module 12 floating point precision and
stability; module 14 pinned memory, streams, overlap; module 25 cuBLAS. Labs include
basic and tiled matmul, reduction, pinned-memory and streams vector add.

Mapping to our modules (by chapter and lecture title, not by book text):
02 <- ch 2, 3 (and ch 20 for streams/pinned copies; Teaching Kit modules 2, 3, 14);
03 <- ch 5 (tiled matmul: ECE 408 lecture 5, Kit module 4) and ch 6 (coalescing:
Kit module 6); 04 <- ch 10 (Kit module 9, ECE 408 lab 5); 05, 06, 07 <- no chapter
(ch 16 is deep learning, read only as a title; ECE 408 lecture 12 "Computation in CNNs
and Transformers" is the nearest); 08 <- Appendix A (Kit module 12).

### 4. OLCF / NVIDIA CUDA Training Series

Thirteen sessions (2020-2021): 1 Intro to CUDA C++; 2 Shared memory; 3-4 Fundamental
optimization; 5 Atomics, reductions, warp shuffle; 6 Managed memory; 7 Concurrency;
8 Performance analysis; 9 Cooperative groups; 10 Streams and multithreading; 11 MPS;
12 Debugging; 13 Graphs. The page gives no slide or recording links.

Exercises (FIXME skeletons with solutions): hw1 hello (prints block and thread, notes
that ordering varies and `cudaDeviceSynchronize` is needed because launches are
async), vector add with an error-check macro (and a check after the launch), naive 2D
matmul (2D indexing introduced). hw2 1D stencil and matmul with shared memory, with
timing built in ("compare with hw1"). hw3 vector add with a grid-stride loop, then
run under Nsight Compute with blocks/threads of 1x1, then larger (threads per block
limited to 1..1024). hw4 row sums vs column sums of a matrix, profiled with
`l1tex__t_sectors...` and `l1tex__t_requests...` metrics to see load efficiency
(row_sums slower: uncoalesced). hw5 compares three reductions (atomic-only, shared
tree with atomic finish, warp shuffle with atomic finish), asks why the difference is
small at 8M and larger at 163840 elements, and a bonus: raise N to about 32M "what
happened?"; then a max reduction; then fix row_sums with one block per row and a
block-stride loop. hw8 matrix transpose driven by ncu metrics (naive, then shared-
memory tiled, then bank conflicts) with PASS plus achieved bandwidth. hw12
compute-sanitizer on a tiled matmul taken from the programming guide: memcheck finds an
off-by-one index (compile with `-lineinfo` to get the line), then racecheck finds a
missing barrier; cuda-gdb on an `-inf` in a reduction.

How they check: constant inputs with a known exact answer (matmul A = 3, B = 2; sums of
ones compared with `== (float)N`), "row sums correct!". My reading: the hw5 bonus is
the float-exactness limit (2^24) breaking that equality. How they time: host
`clock()` around init and compute (hw2), then the profilers (nsys/ncu) from hw3 on.

### 5. Boehm, CUDA matmul worklog (Dec 2022)

GPU: RTX A6000 (Ampere, CC 8.6); A100 for some plots. FP32 SGEMM at 4092 (he also
writes 4096). Steps, with his GFLOP/s and share of cuBLAS (23249.6 GFLOP/s):
1 naive, one thread per C element, 32x32 blocks: 309.0, 1.3%.
2 global memory coalescing, remap threads so consecutive threadIdx.x reads
consecutive addresses: 1986.5, 8.5%.
3 shared memory cache blocking (tiles of A and B per block): 2980.3, 12.8%.
4 1D blocktiling, several C entries per thread (TM): 8474.7, 36.5%.
5 2D blocktiling, 8x8 outputs per thread, outer products in registers: 15971.7, 68.7%.
6 vectorized access (transposed As, float4 loads): 18237.3, 78.4%.
9 autotuning BM, BN, BK, TM, TN by script: 19721.0, 84.8%.
10 warptiling: 21779.3, 93.7%. (7 and 8 dropped: removed bank conflicts but ran slower.)

Warnings: tile quantisation when sizes do not divide; occupancy maths approximate;
warp-synchronous code unsafe since Volta; coalescing does not show in SASS (hardware
does it at run time); `reinterpret_cast` to float4 needed to promise alignment; tuned
parameters differ between A6000 and A100; thread swizzling gave nothing (L2 hit rate
already about 80%); cuBLAS picks different kernels by size (split-K at 256) so small
sizes compare differently; tensor cores (TF32/BF16) left out and could add 2.5-3.5x.
He used Nsight Compute (warp stalls, instruction mix) and Nsight Systems (to see which
cuBLAS kernel ran). Text and table numbers disagree in two places (he says the post is
less polished than usual).

Repo (sgemm.cu, runner.cu): sizes 128 to 4096; correctness first against cuBLAS with
an absolute difference of 0.01 (inputs small values: an integer 0-4 plus 0.01 x 0-4);
timing is cudaEvent around 50 back-to-back launches, divided by 50 (mean, no L2 flush,
no separate warm-up in that loop). The cuBLAS call is `cublasGemmEx` with B passed
before A and the sizes swapped (N, M, K), CUBLAS_COMPUTE_32F; my reading: this is the
row-major-through-column-major trick (C^T = B^T A^T).

### 6. NVIDIA blog posts and the reduction deck

Even Easier Introduction (Harris, 2017, updated 2025-05-02, T4): C++ add of 1M floats
on the CPU -> `__global__` and `cudaMallocManaged` -> `<<<1,1>>>` (about 75-91 ms)
-> `<<<1,256>>>` with a block-stride loop (about 2-4 ms) -> many blocks with a
grid-stride loop (`(N+blockSize-1)/blockSize`) which first does not help, because the
time is unified-memory page faults -> `cudaMemPrefetchAsync` -> 47.5 us, about 265
GB/s of the T4's 320. Timing with Nsight Systems (`nsys`). Check: max error against
the known answer 3.0f. Warnings: every thread running the whole loop is a race;
launches are async, sync before reading; page faults can hide all the parallel gain.

Performance Metrics (Harris, 2012, Tesla M2050): host timers measure only the launch
unless you `cudaDeviceSynchronize()`; events (`cudaEventRecord`, `cudaEventSynchronize`,
`cudaEventElapsedTime`) on the GPU clock, about 0.5 us resolution; SAXPY of 20M floats;
effective bandwidth (bytes read + written)/(t x 1e9), counted as 12 bytes per element;
measured about 110 GB/s of 148 theoretical; GFLOP/s = 2N/(t x 1e9) but SAXPY is
bandwidth-bound so bandwidth is the metric that matters.

Global Memory (Harris, 2013, C870, C1060, C2050): offset kernel `a[i+s]` and stride
kernel `a[i*s]`; misalignment mattered greatly on CC 1.0 and hardly at all on CC 2.0;
large strides are bad on every architecture; fix strided access by staging coalesced
tiles in shared memory. Timing with events, a warm-up launch, `cudaMemset` reset
before each run.

Shared Memory (Harris, 2013): static and dynamic (`extern __shared__`, size as third
launch parameter; carve one array for several); array reverse of 64 elements through
shared memory with global reads and writes coalesced; `__syncthreads()` between the
store and the load; a barrier in divergent code is undefined and can deadlock; banks
and conflicts (16 banks on CC 1.x, 32 later, configurable width on CC 3.x).

Data Transfers (Harris, 2012, NVS 4200M laptop and GTX 680 desktop): measure copies
with the profiler; minimise and batch transfers; pinned memory: laptop 2.31 -> 5.77
GB/s host to device, desktop 5.37 -> 6.19 GB/s; do not over-allocate pinned memory.

Faster Parallel Reductions on Kepler (Justin Luitjens, not Harris, 2014, K20X):
shuffle reads another lane's register; warpReduceSum halves the offset from 16 with
`__shfl_down` (the post predates the `_sync` forms); blockReduceSum = each warp
reduces, lane 0 writes to a 32-entry shared array, sync, first warp reduces those;
device reduce two ways: two passes (grid-stride sum per thread, block reduce, one
partial per block, then one block of 1024 over the partials) or atomics (per warp or
per block); interleaving independent reductions for ILP. Results only in figures; text
says warp reduce plus atomics was fastest, and CUB matches or beats it. Warnings:
block size must be a multiple of 32; width a power of two; float atomics are not
bitwise reproducible.

Optimizing Parallel Reduction in CUDA (Harris deck, undated in its text; G80, 4M
ints, his peak 86.4 GB/s): 1 interleaved addressing with a divergent modulo branch
2.083 GB/s; 2 strided index, no divergence but bank conflicts 4.854; 3 sequential
addressing 9.741; 4 first add during load 17.377; 5 unroll the last warp (warp-
synchronous, `volatile` shared pointer) 31.289; 6 complete unroll with the block size
as a template parameter 43.996; 7 several elements per thread (his Brent's-theorem
argument) 62.671 GB/s, 30x over kernel 1, and 73 GB/s on 32M elements. Note: step 5's
warp-synchronous trick is the one sources 1, 5 and 13 now call unsafe since Volta.

### 7. GPU MODE lectures (README at 77a8df41)

The README links the PMPP book. Lectures relevant to us: 1 profiling and integrating
CUDA kernels in PyTorch; 2 recap of PMPP ch 1-3; 3 getting started with CUDA (Jeremy
Howard, Colab); 4 compute and memory architecture; 5 CUDA for Python programmers; 7
quantization (CUDA vs Triton); 8 CUDA performance checklist (files: coalesce.cu,
coarsening.cu, divergence.cu, occupancy.cu, privatization.cu, tiling.cu; my reading:
these match the 4th edition's "optimization checklist"); 9 reductions; 12 Flash
Attention; 14 Triton; 15 CUTLASS; 18 fused kernels; 20-21 scan (Izzat El Hajj, a PMPP
author); 22 speculative decoding in vLLM; 23 tensor cores; 28 Liger kernels (notebooks
on verifying RMSNorm correctness, "contiguity is the hidden killer", int32 overflow);
29 Triton internals; 30 quantized training; 33-34 BitBLAS, low-bit Triton; 35 SGLang;
36 CUTLASS and FA3; 40 FlashInfer; 41 CUDA docs for humans.

Lecture 1 code: `torch.utils.cpp_extension.load_inline` with a 2D square kernel and a
C++ wrapper returning a tensor; timing with `torch.cuda.Event(enable_timing=True)`,
five warm-up calls, one timed call, `torch.cuda.synchronize()`, with the comment that
Python's time module is wrong because CUDA is async; then the PyTorch profiler and
ncu logs. Lecture 9 code follows the book's reduction order: SimpleSumReduction
(interleaved, `threadIdx.x % stride`), FixDivergence (contiguous threads, stride
halving), SharedMemoryReduction (comment: could not make it faster than the previous
one, though L1 throughput rose), segmented multi-block with `atomicAdd`, coarsened
(COARSE_FACTOR per thread); all on inputs of ones. accuracy.py shows 1000 + 0.001 is
lost in float16; nondeterminism.py shows sum order changes the result. Lecture 12
flash_attention.cu: Q_i, K_j, V_j and S tiles in `__shared__` float arrays, per-thread
O, l, m in registers, rescale by `expf(last_m - m)`.

### 8. Horace He, Go Brrrr (2022)

Three costs: compute (time in FLOPs), memory bandwidth (moving tensors between DRAM
and the cores), overhead (everything else: Python, framework dispatch, launches).
Know the regime first, then the fix. Compute: A100 312 TFLOP/s for matmul but 19.5
for non-matmul; non-matmul ops are about 0.2% of BERT's FLOPs yet slow, so they are
memory problems. Bandwidth: `x.cos().cos()` costs 4 global accesses unfused, 2 fused,
about 2x; a fused pair costs about the same as one op, which is why activations cost
about the same as each other. Rule of thumb on A100 (1.5 TB/s, 19.5 TFLOP/s): a unary
op needs on the order of a hundred operations per element before compute matters;
microbenchmark of repeated `x*2` flat until about 64 multiplies. Overhead: does not
scale with size; test by doubling the batch (10% more time = overhead-bound); gaps in
a profiler trace; nvidia-smi GPU-Util. Fixes table: overhead -> tracing, fusion,
CUDA graphs; bandwidth -> fusion; compute -> tensor cores.

### 9. karpathy/llm.c (f1e2ace6)

dev/cuda/README: each file develops one kernel in several numbered versions,
increasing in complexity, compiled alone (`nvcc -O3 --use_fast_math ...`); running
`./layernorm_forward 1` first runs the CPU reference, then version 1 on the GPU,
compares, then times it over several block sizes; the fastest version is copied by
hand, with its best block size hard-coded, into the training file. Can run on Modal.

common.h: `validate_result` copies the GPU result back and checks each element with
tolerance + |ref| x epsilon, epsilon = FLT_EPSILON for fp32 and 0.079 for bf16 (the
numpy.isclose shape with rtol tied to the type), skips non-finite reference elements
(masked), prints the first five pairs, stops after ten mismatches. `benchmark_kernel`
allocates a buffer the size of L2, memsets it before every repetition to flush L2,
records events around each call, returns the mean time over the repeats. Drivers:
validate every block size in {32, 64, 128, 256, 512, 1024} first ("All results match"),
then time each (layernorm: 2000 repeats) and print time and GB/s (comment cites A100
40GB PCIe at 1,555 GB/s).

Version ladders (file headers): layernorm 1 thread per row looping C; 2 parallel over
B, T, C; 3 cooperative groups; 4 one pass with var = E[x^2] - E[x]^2; 5 a block per
row. softmax 1 naive; 2 fused over B, T, C; 3 warp reductions for max and sum (block
of 32 only); 4 warps plus shared memory (any multiple of 32); 5-6 online softmax;
7 for very large C. attention 1 naive over batch, time, heads; 2 a naive flash
attention adapted from flash-attention-minimal, which the header says is about 3x
slower than version 1; 3 cuBLAS for QK^T and the weighted sum plus a custom softmax,
about 20x faster than version 1; 4 fuses the scale and uses an online, autoregressive
softmax; 5 FP16; 10-11 cuDNN flash attention. gelu: 1 naive, 2 bf16 with Packed128
(128-bit loads). matmul: 1 naive, 2 cuBLAS, 3 cuBLASLt.

Training file: matmuls through cuBLASLt (`matmul_forward_cublaslt`), attention through
cuDNN or attention.cuh; hand-written: encoder, layernorm, gelu, fused classifier,
adamw, global norm. test_gpt2.cu checks the whole model against a state file written
by the PyTorch script: logits within 1e-3 and loss within 1e-5 in fp32; with bf16/fp16
the logit threshold is 25.0 and loss 0.05, with the author's comment that he is not
sure whether bf16 or a bug explains it, and that GPUs choose different matmul
algorithms so errors are hardware specific.

### 10. vLLM v0.2.0 (e2fb71ec), csrc and tests/kernels

Six files, 1,260 lines. Each op group is a separate `CUDAExtension` in setup.py
(`vllm.activation_ops`, `layernorm_ops`, `pos_encoding_ops`, `cache_ops`,
`attention_ops`), each with a .cpp file that only declares the host functions and
binds them with `PYBIND11_MODULE`; host functions take preallocated output tensors,
read sizes and strides from the tensors, launch on `at::cuda::getCurrentCUDAStream()`.
NVCC flags `-O2 -std=c++17` (a TODO asks about -O3; no fast-math flag), one `-gencode`
per arch from 7.0, 7.5, 8.0, 8.6, 8.9, 9.0. Types: `VLLM_DISPATCH_FLOATING_TYPES`
(adapted from ATen's Dispatch.h) over Float, Half, BFloat16; the attention file maps
them itself to float, uint16_t and `__nv_bfloat16` with its own vector-type headers.

activation_kernels.cu: grid = num_tokens, block = min(d, 1024); each thread strides by
blockDim over its token's row; `silu_and_mul` reads x from the first half and y from
the second half of a [tokens, 2d] row (read through `__ldg`) and writes silu(x) * y;
silu computes in float and casts back; a generic `activation_kernel` template takes
the function as a template parameter for `gelu_new` and `gelu_fast` (tanh forms). No
shared memory.

layernorm_kernels.cu (RMS norm only): same grid and block; pass 1 accumulates x^2 in
float; `blockReduceSum`; thread 0 writes `rsqrtf(var/h + eps)` to a `__shared__` float;
`__syncthreads`; pass 2 reads the input again and writes (x * scale cast to type) *
weight. A TODO says it is not yet optimised.

reduction_utils.cuh (from FasterTransformer): `warpReduceSum` with `__shfl_xor_sync`
over masks 16..1; `blockReduceSum` with a `static __shared__ T shared[32]`: lane 0 of
each warp stores its sum, sync, the first blockDim/32 threads (rounded with a float
division so a partial last warp counts) reload and reduce again. My reading: only warp
0 ends with the total; calling it twice in one kernel would need a barrier before the
second write to `shared`; and with a partial last warp the full-mask shuffle runs with
lanes that do not exist (the RMS norm test uses hidden size 67).

pos_encoding_kernels.cu: grid = num_tokens, block = min(num_heads * rot_dim / 2, 512);
each thread rotates one pair, in place in query and key (strided, since q and k come
from a fused qkv); cos and sin come from a precomputed [max_position, rot_dim] cache
indexed by the token's position; a template flag selects NeoX pairing (i with
i + rot_dim/2) or GPT-J pairing (2i with 2i+1); separate loops for query heads and
key heads (GQA). No shared memory.

cache_kernels.cu: `swap_blocks` is host code issuing one `cudaMemcpyAsync` per block
(comment: slow when there are many). `copy_blocks_kernel`: grid (num_layers,
num_pairs), block min(1024, elements per block), each thread copies strided elements of
one key block then one value block; per-layer cache pointers go into an int64 tensor
copied to the GPU (comment: this synchronises CPU and GPU). `reshape_and_cache_kernel`:
grid = num_tokens, block = min(num_heads * head_size, 512); `slot_mapping[token]` gives
a flat slot, block = slot / block_size, offset = slot % block_size; key cache layout
[num_blocks, num_heads, head_size/x, block_size, x] with x = 16 bytes / element size,
value cache [num_blocks, num_heads, head_size, block_size] (tokens innermost). Also
`gather_cached_kv` (the inverse, unrolled by 4).

attention_kernels.cu (adapted from FasterTransformer's decoder masked MHA):
`single_query_cached_kv_attention_kernel`, grid (num_heads, num_seqs), 128 threads,
templated on type, HEAD_SIZE (64, 80, 96, 112, 128, 256) and BLOCK_SIZE (8, 16, 32).
A thread group of max(32/BLOCK_SIZE, 1) threads handles one key; each group reads 16
bytes at a time (VEC_SIZE chosen for that). Steps: the query vectors go to shared
memory; each warp takes a KV block at a time (block_idx = warp, += NUM_WARPS) through
the block table; each group dots q with one key (partial sums across the group by
xor shuffle), scales, adds ALiBi, and lane 0 of the group writes the logit to a float
array in dynamic shared memory (masked positions written as 0 and kept out of the max);
max by shuffles within each warp then across warps via `red_smem`; then every thread
strides the logits: `__expf(logit - max)`, sum, `block_sum`, multiply by
`__fdividef(1, sum + 1e-6)`. Values: each warp again walks blocks; lanes take
V_VEC_SIZE consecutive tokens for a set of head-dimension rows, accumulate in float
`accs`; reduce within the warp, then across warps by halving through shared memory
(reusing the logits space, hence a barrier), and warp 0 writes the output. Dynamic
shared memory = max(context padded to a block x 4 bytes, (NUM_WARPS/2) x head_size x
4), raised with `cudaFuncSetAttribute`; the Python side checks the longest sequence
fits (worker.py `_check_if_can_support_max_seq_len`). Comments note fp32 logits and
accumulators "for better accuracy" and that out-of-context values must be zeroed
because they may hold NaNs. My reading: that zeroing loop runs `j <= V_VEC_SIZE`, one
element past the vector; and the softmax is two-pass over a stored row, not online.
GQA/MQA via `head_mapping`. Prefill attention at this tag is not vLLM's own kernel:
the model layer calls xformers `memory_efficient_attention_forward`.

tests/kernels, all against PyTorch in the same process, seed 0, `torch.allclose`:
activation vs `F.silu(x1) * x2` and transformers' gelu, tokens {7, 83, 2048}, d {512,
4096, 5120, 13824}, all three dtypes at atol = rtol = 1e-5. RMS norm vs a PyTorch
module that computes in fp32 and casts before the weight, hidden {67, 768, 2048,
5120, 8192}, atol 1e-2. Rotary vs a PyTorch reference (both pairings, rot_dim = head
or 32), atol 1e-5. Cache: copy_blocks vs cloned tensors updated by Python indexing;
reshape_and_cache vs the same with a random slot mapping. Attention vs a Python loop
that gathers each sequence's keys and values through the block table and runs an
einsum softmax in float; context lengths random up to MAX_SEQ_LEN (shared memory / 4 -
512, the last one at the maximum), random block numbers from 128 blocks, 7 sequences,
heads (40,40) and (64,8), atol 1e-3. The prefill test checks xformers against an
einsum reference.

### 11. PagedAttention paper (v1, 2023-09-12)

The KV cache of a sequence is split into KV blocks of B tokens (like pages); blocks
need not be contiguous; a block table per request maps logical blocks to physical
blocks and records how many positions are filled; blocks fill left to right and a new
physical block is taken only when the last is full. Attention written block-wise: the
scores of query i against each key block, normalised over all of the context, then
weighted sums of value blocks (my reading: a two-pass form, matching the v0.2.0
kernel). Block size trade-off: bigger blocks let the kernel read more positions in
parallel; smaller ones waste less memory and share more. Ablation: on ShareGPT block
sizes 16-128 best, on Alpaca 16 and 32 best and larger ones hurt (sequences shorter
than blocks); default 16. Kernels (section 5.1): fused reshape and block write (split
into blocks, reshape to the read-friendly layout, write where the block table says, one
launch); fused block read and attention (adapted from FasterTransformer, "a GPU warp to
read each block" for coalescing, variable sequence lengths); fused block copy for
copy-on-write (many small `cudaMemcpyAsync` calls would be slow, so one kernel batches
them). Microbenchmark: the attention kernel is 20-26% slower than FasterTransformer's
because of the table lookups, extra branches and variable lengths; they argue it only
affects attention. Sharing: parallel sampling and beam search share prompt blocks with
reference counts and copy-on-write; fork, append, free. Engine: 8.5K lines of Python
and 2K of C++/CUDA. Hardware: A100 40GB/80GB.

### 12. FlashAttention, FlashAttention-2, online softmax

FA1 (v2, 2022): A100 has 40-80 GB HBM at 1.5-2.0 TB/s and 192 KB of on-chip SRAM per
SM (108 SMs) at about 19 TB/s; compute-bound vs memory-bound by arithmetic intensity;
softmax, masking, dropout and element-wise ops are memory-bound. Algorithm 0 (standard)
writes S then P to HBM. Algorithm 1: block sizes Bc = ceil(M / 4d), Br = min(ceil(M /
4d), d) for SRAM size M and head dim d; O, l (row sums) and m (row maxima) in HBM,
initialised to 0, 0, -inf; outer loop over K/V blocks j, inner loop over Q blocks i:
load Q_i, O_i, l_i, m_i; S = Q_i K_j^T on chip; block row max, P = exp(S - max), block
row sum; new m = max(old m, block max); new l = both sums rescaled to the new max and
added; O_i rewritten to HBM as the rescaled old O plus the rescaled P V_j, divided by
the new l; l and m written back. One CUDA kernel. Theorem 2: standard attention does
Theta(N d + N^2) HBM accesses, FlashAttention Theta(N^2 d^2 / M); Proposition 3: no
exact algorithm does asymptotically better for all M. Backward recomputes S and P from
the stored m and l. Reported (A100): 15% on BERT-large training vs MLPerf 1.1, 3x
GPT-2, 2.4x long-range arena, up to 7.6x on GPT-2 attention, up to 3x faster than
standard attention for 128-2K.

FA2 (v1, 2023): FA1 reaches 25-40% of peak; three changes. (1) Fewer non-matmul
FLOPs (A100: 312 TFLOP/s matmul vs 19.5 non-matmul, so each non-matmul FLOP costs
16x): keep the output un-normalised and divide by l once at the end; store only the
logsumexp L = m + log(l) for the backward. (2) Parallelise over sequence length too:
FA1 used one thread block per (batch, head), fine when that count is at least about
80; FA2 swaps the loops (outer over Q row blocks, inner over K/V blocks, first done by
Phil Tillet in Triton) and gives each row block its own thread block. (3) Inside a
block, split Q across 4 or 8 warps with K and V shared, instead of FA1's split of K
and V across warps ("split-K"), which needed shared-memory reductions. Causal mask:
skip blocks whose columns all exceed the rows (about half for long sequences, 1.7-1.8x
over no mask); apply the mask only in the one diagonal block per row. Blocks
{64, 128} x {64, 128} tuned by hand per head dim. Results on A100 80GB SXM4: about 2x
FA1, up to 230 TFLOP/s forward (73% of peak), 225 TFLOP/s end-to-end training (72%
MFU). These are FP16/BF16 tensor-core numbers.

Online softmax (v2, 2018, NVIDIA, Tesla V100 fp32): naive softmax overflows; safe
softmax subtracts the max and needs three passes and 4 memory accesses per element;
Algorithm 3 keeps a running max m and a running normaliser d, and when the max grows
it rescales d by exp(old m - new m) before adding exp(x - new m): one pass for m and d,
3 accesses per element. Pairs (m, d) combine with an operator that takes the larger m
and rescales both d's to it; it is associative and commutative, so it parallelises as
a reduction. Fused softmax + top-k needs one access per element. Benchmarks: batch
4000 vectors, online about 1.3x safe for vector sizes from 4000 (all equal below about
1000); batch 10 lower, latency-limited; fused softmax+top-k 1.5x rising to 5x at
V = 25000.

### 13. Compute Sanitizer v2026.4.0

Run as `compute-sanitizer [options] app [args]`, tool chosen with `--tool memcheck`
(default), `racecheck`, `initcheck`, `synccheck`. memcheck: out-of-bounds and
misaligned accesses in global, local and shared memory (precise), hardware exceptions,
device malloc/free errors, CUDA API errors, leaks with `--leak-check full`. racecheck:
shared-memory hazards only (write-after-write, write-after-read, read-after-write);
run memcheck first; warp-synchronous code without explicit sync is reported (assumption
no longer holds after Volta). initcheck: reads of uninitialised global memory (shared
with an option). synccheck: misuse of `__syncthreads`/`__syncwarp`, including barriers
in divergent code. Compile with `-lineinfo` for source lines without changing
optimisation (`-G` for full debug); on Linux `-Xcompiler -rdynamic` for host
backtraces. Tools cost memory and time (Windows TDR can kill long kernels); errors
terminate the kernel by default.

### 14. cuBLAS 13.5

Column-major storage, 1-based in the Fortran sense; for C use `IDX2C(i,j,ld) =
j*ld + i`; ld is the leading dimension (rows of the allocated matrix). `cublasSgemm(handle,
transa, transb, m, n, k, alpha, A, lda, B, ldb, beta, C, ldc)` computes C = alpha
op(A) op(B) + beta C; op is N, T or C; m rows of op(A) and C, n columns of op(B) and C,
k the shared dimension; alpha/beta on host or device per pointer mode; if beta is 0, C
need not be valid on entry. Math modes: `CUBLAS_DEFAULT_MATH` (tensor cores where the
requested precision allows), `CUBLAS_TF32_TENSOR_OP_MATH` (lets FP32 routines use TF32),
`CUBLAS_PEDANTIC_MATH` (prescribed precision, for testing); environment variable
`NVIDIA_TF32_OVERRIDE=0` forbids TF32 in NVIDIA libraries. The page does not say in so
many words that SGEMM stays FP32 by default; my reading of the mode definitions is that
it does unless TF32 is enabled. Practice: create the handle once (destroy synchronises
the device), one handle per thread, `cublasSetStream`; results bitwise reproducible for
the same toolkit, architecture and SM count, not across versions or with several
streams (`CUBLAS_WORKSPACE_CONFIG` to restore); some algorithms split K. Llm.c's
common.h switches between `CUBLAS_DEFAULT_MATH` and `CUBLAS_TF32_TENSOR_OP_MATH` with
a flag.

### 15. Stanford CS149 Assignment 3 (asst3 at 43bf4722)

On AWS T4 GPUs (CC 7.5). Part 1 SAXPY (5 pts): add timers for the whole process
(copies included) and for the kernel alone; warns that timing a launch without
`cudaDeviceSynchronize()` gives an "amazingly fast" number; `cudaMemcpy` is already
synchronous; compare both bandwidths with the T4's memory bandwidth and the bus (they
quote about 5.3 GB/s for the AWS bus, and point at pinned memory). Part 2 (10 pts):
exclusive scan and find-repeats; graded by `checker.py` on correctness and speed,
full credit within 20% of a reference; warns that launching N threads per step and
masking most off is slow. Part 3 (85 pts): a circle renderer; the starter CUDA code is
deliberately incorrect (violates atomicity and order) and students are told to
convince themselves of that first; `render --check` compares the image with the CPU
reference renderer and prints time. Grading: 2 correctness points per scene, 7
performance points only if correct: full if T <= 1.2 Tref, zero if T >= 10 Tref,
otherwise 7 x Tref / T, with Tref measured on the student's own machine. Tips: wrap
every CUDA call in an error-check macro (an unchecked `cudaMalloc` out-of-memory shows
up only as a wrong image).

## (c) By module

### Module 02 - Threads, blocks and a grid

Sources: 1 (1.2, 2.3, 2.5), 2 (ch 9, 10.1), 3 (ch 2-3; Kit modules 2-3, 14; ECE 408
labs 0-1), 4 (hw1, hw3), 6 (Even Easier, Metrics, Data Transfers), 7 (lectures 1-3),
8, 9 (gelu_forward), 10 (activation_kernels.cu and its test), 13, 15 (part 1).

Order of ideas in the best of them:
- Harris (Even Easier): CPU loop -> `__global__` + managed memory -> one thread ->
  one block with a block-stride loop -> many blocks with a grid-stride loop -> the
  profiler shows the time is page faults -> prefetch -> bandwidth against the card's
  peak.
- OLCF: hello world printing block and thread (order varies; sync needed) -> vector add
  with explicit allocation, copies and an error-check macro -> 2D indexing on a naive
  matmul -> grid sizing studied in the profiler.
- Programming Guide: host/device and kernels -> grid/block/thread -> warps/SIMT ->
  memory spaces; asynchronous execution and events as their own later chapter.
- CS149: one exercise (SAXPY) holds both timers (with and without copies) and asks
  the reader to compare each with a known bandwidth.
- Teaching Kit: memory allocation and data movement before threads and kernels.

Worked examples: vector add (all), SAXPY (Harris metrics, CS149), hello world (OLCF),
grayscale and blur (Kit), square of a matrix (GPU MODE 1), vLLM's silu_and_mul and
gelu (block per token, block-stride loop).

Mistakes they warn about: timing only the launch (2, 6, 15); reading results before a
sync (4, 6); launch errors that appear only at the next sync, `cudaGetLastError`,
`CUDA_LAUNCH_BLOCKING=1` (1); unchecked `cudaMalloc` (15); unified-memory page faults
(6); pinned memory overuse (2, 6); every thread running the whole loop (6); block size
not a multiple of 32, over 1024 threads (1, 2, 4).

Correctness: known exact answer and max error (Harris), PASS/values (OLCF), CPU
reference via a checker (CS149, llm.c `validate_result`), PyTorch reference with
`torch.allclose` (vLLM test, atol = rtol = 1e-5 for all three dtypes).

Timing: events with stream sync (1, 2: about 0.5 us resolution); host timer with
`cudaDeviceSynchronize` (2, 15); nsys or ncu (6, 4); effective bandwidth = (bytes read
+ written)/time/1e9 (2, 6).

Where our outline differs:
- 02.03 (copies) comes before 02.04 (timing); CS149 teaches both timers in one
  exercise and makes "with and without copies" the comparison; Harris uses managed
  memory and no explicit copies.
- The outline goes from 02.02 to vLLM's block-per-token shape in 02.05; Harris, OLCF
  hw3 and the Guide teach the grid-stride loop as the general form, and OLCF hw5
  teaches the block-per-row, block-stride loop as a named variant of it.
- No lesson names error checking; OLCF, CS149 and the Guide put it with the first
  program.
- Compute Sanitizer is in 02's "Learn from"; OLCF teaches it in its 12th session, on
  a tiled matmul; memcheck is useful from 02, racecheck only once shared memory
  appears (03).
- Harris 2025 and CS149 both use a T4 (CC 7.5); the Guide lists `__nv_bfloat16` as
  needing CC 8.0 or higher, which bears on what 02.01 recommends if module 08 is to run
  bf16 natively (not verified on a T4 in this session).
- vLLM's activation launch (block = min(d, 1024), no `num_tokens` bound check because
  grid = num_tokens) and llm.c's gelu ladder (naive, then 128-bit packed loads) are the
  two shapes a reader meets after this module.

### Module 03 - Matrix multiply on the GPU

Sources: 1 (2.3.4: coalescing, banks, transpose), 2 (10.2: coalescing, C = AB and
C = AA^T), 3 (ch 5-6; Kit modules 4 and 6; ECE 408 lectures 5-6, labs 2-3), 4 (hw1,
hw2, hw4, hw8, hw12), 5, 6 (Global Memory, Shared Memory), 7 (lecture 8), 9
(matmul_forward: naive, cuBLAS, cuBLASLt), 14.

Order of ideas:
- Boehm: naive -> coalescing (remap threads to C) -> shared-memory tiles -> 1D
  blocktiling -> 2D blocktiling in registers -> vectorised loads -> autotune ->
  warptiling; every step measured against cuBLAS on one GPU.
- PMPP / Kit / ECE 408: CUDA memories -> tiled algorithms -> tiled matmul -> its
  kernel -> arbitrary sizes; warps and divergence; then DRAM bandwidth and
  coalescing.
- Best Practices: the same kernel family scored in GB/s of effective bandwidth.
- OLCF: naive (hw1) -> shared memory (hw2, timing compared with hw1) -> coalescing
  shown with ncu sector counts on row vs column sums (hw4) and transpose (hw8).

Worked examples: matmul (Boehm, PMPP, Kit, OLCF, BPG C = AB), transpose (Guide, OLCF
hw8), C = AA^T (BPG), row and column sums (OLCF hw4).

Numbers the sources report as theirs: Boehm (A6000, 4092, FP32): naive 309 GFLOP/s
(1.3% of cuBLAS), coalesced 1986.5 (8.5%), shared tiles 2980.3 (12.8%), 1D blocktiling
8474.7 (36.5%), 2D 15971.7 (68.7%) ... warptiling 21779.3 (93.7%). BPG (V100): C = AB
119.9 -> 144.4 -> 195.5 GB/s; C = AA^T 12.8 -> 140.2 -> 199.4 GB/s with padding.

Mistakes: tile quantisation and sizes that do not divide (5; Kit 4.5); missing barrier
between loading a tile and using it, and before overwriting it (1, 6; OLCF hw12 is
exactly this, found with racecheck); bank conflicts and the +1 padding (1, 2); float4
alignment (5); warp-synchronous code (5); tuning that does not carry across GPUs (5);
comparing at small sizes where cuBLAS uses other kernels (5).

Correctness: against cuBLAS with an absolute 0.01 (Boehm); constant matrices with a
known product (OLCF); an epsilon against a reference (BPG ch 7).

Timing: Boehm, events around 50 back-to-back launches, mean, GFLOP/s = 2MNK/t, sizes
128-4096; BPG, effective bandwidth; OLCF, host clock then ncu.

cuBLAS facts a lesson needs: column-major; for row-major data Boehm passes B before
A with N and M swapped; default math keeps FP32 unless TF32 is enabled, and
`NVIDIA_TF32_OVERRIDE=0` forbids TF32; create the handle once.

Where our outline differs:
- The outline stops at shared-memory tiles (Boehm's kernel 3, 12.8% of cuBLAS on his
  card); in Boehm most of the distance to cuBLAS is closed by per-thread register
  blocking (kernels 4-5), which the outline does not include, so 03.04's "what is
  left" will be most of it. PMPP's 5th edition adds a chapter "Advanced optimizations
  for matrix multiplication" (title only seen); the 4th, which the outline cites, has
  none by that name.
- The outline has coalescing (03.02) before tiles (03.03), as Boehm does; PMPP, the
  Kit and ECE 408 put tiling first and coalescing in a later performance chapter.
- Boehm's uncoalesced naive kernel comes from mapping threadIdx.x to rows of C; the
  Guide teaches coalescing on transpose, not matmul.
- The track's CPU ladder reports the fastest run; Boehm and llm.c report the mean.

### Module 04 - Many threads, one number

Sources: 1 (2.3.5 atomics), 3 (ch 10; Kit module 9; ECE 408 lecture 13, lab 5), 4
(hw5), 6 (Luitjens; Harris deck), 7 (lecture 9), 9 (layernorm_forward,
softmax_forward), 10 (reduction_utils.cuh, layernorm_kernels.cu, the softmax inside
attention_kernels.cu), 12 (online softmax), 13 (racecheck, synccheck).

Order of ideas:
- Harris deck: interleaved with a divergent branch -> strided index (bank conflicts)
  -> sequential addressing -> first add during load -> unroll the last warp ->
  complete unroll by template -> several elements per thread.
- PMPP order as GPU MODE 9 codes it: simple interleaved -> fix divergence -> shared
  memory -> many blocks with an atomic finish -> coarsening.
- Luitjens: warp shuffle -> block = warps + 32 shared slots -> whole array by two
  passes or atomics -> ILP.
- OLCF: atomics only -> shared tree with atomic finish -> warp shuffle with atomic
  finish -> a max instead of a sum -> one block per matrix row.
- llm.c layernorm and softmax: thread per row -> parallel over all elements -> warp
  reductions -> warps plus shared memory -> single-pass statistics -> block per row;
  softmax adds online versions.

Numbers: Harris (G80, 4M ints): 2.083, 4.854, 9.741, 17.377, 31.289, 43.996, 62.671
GB/s (30x), 73 GB/s at 32M, his peak 86.4. Online softmax (V100, fp32): 1.3x over safe
from vector size 4000 at batch 4000.

Mistakes: divergent modulo branches; bank conflicts from strided indices; the
warp-synchronous `volatile` unroll (Harris kernel 5) is unsafe since Volta (1, 5, 13);
a barrier inside divergent code (6, 13 synccheck); block sizes not a multiple of 32
for shuffles (6); float atomics not reproducible (6; GPU MODE nondeterminism.py); float
exactness on large sums (OLCF hw5 bonus); precision loss in fp16 (GPU MODE
accuracy.py); a non-atomic shared total (1).

Correctness: sums of ones compared exactly (OLCF, GPU MODE), CPU reference with a
type-scaled relative tolerance (llm.c), PyTorch reference (vLLM RMS norm at atol 1e-2
with hidden sizes including 67).

Timing: kernel durations in the profiler at two sizes (OLCF: why shuffles matter more
at 163840 than at 8M); every block size from 32 to 1024 with GB/s (llm.c).

Where our outline differs:
- 04.01 sum -> 04.02 shuffles -> 04.03 block matches Luitjens and OLCF, not the
  Harris deck, whose warp step is the dated warp-synchronous one.
- 04.05 "softmax without overflow" is the safe softmax (max, then sum, then divide),
  which Milakov says all frameworks used; the outline holds the online one-pass
  formula to 07.02, while llm.c and Milakov teach it as a softmax kernel on its own.
- vLLM's RMS norm reads the input twice (sum of squares, then scale); llm.c's
  layernorm v4 computes both statistics in one pass; the outline does not say which.
- OLCF hw5's row sums with one block per row is the same shape as vLLM's RMS norm.

### Module 05 - Positions and the KV cache

Sources: 10 (pos_encoding_kernels.cu, cache_kernels.cu, tests), 11. (RoPE paper not
in this list.)

Order in the paper: blocks like pages -> block table (logical to physical, filled
count) -> attention written per block -> kernels: fused reshape and block write, fused
block read and attention, fused block copy -> copy-on-write for parallel sampling and
beam search.

What vLLM does: rotary in place on q and k, block per token, cos/sin from a cache
indexed by position, NeoX or GPT-J pairing by flag; `reshape_and_cache` block per
token writing to the slot `slot_mapping` names; `copy_blocks` one launch for all
(layer, pair) copies; keys stored [blocks, heads, head_size/x, block_size, x] with x =
16 bytes / element, values [blocks, heads, head_size, block_size].

Mistakes they warn about: many small `cudaMemcpyAsync` calls (11; swap_blocks
comment); moving pointer arrays to the GPU synchronises (cache_kernels.cu comment).

Correctness: vLLM compares the cache kernels with the same writes done by Python
indexing on a cloned tensor, and rotary with a PyTorch formula at atol 1e-5.

Where our outline differs:
- vLLM's cache layout is not the plain [block, token, head, dim]; its key layout is
  chosen for the attention kernel's 16-byte loads and its value layout puts tokens
  innermost. If the reader's layout is simpler, 05.05 has to explain both.
- Which rotary pairing llama2.c uses was not checked in this session; vLLM supports
  both and the reference must match the model.
- The paper's ablation, not the code, is the source for block size 16.

### Module 06 - Attention for one new token

Sources: 10 (attention_kernels.cu, attention_utils.cuh, test_attention.py), 11, 1
(shared memory, shuffles absent from 2.3), 12 (online softmax, for the contrast).

How vLLM v0.2.0 does it: grid (heads, sequences), 128 threads; thread groups per key;
query in shared memory; a warp per KV block through the block table; logits for the
whole context in float in dynamic shared memory; max (warp shuffles, then shared),
exp and sum (`__expf`, block_sum), normalise; values with float accumulators per
head-dimension row, reduced within and then across warps through shared memory;
GQA via head_mapping; ALiBi. The context length is capped by shared memory, checked in
Python. Paper: a warp reads each block for coalescing; 20-26% slower than
FasterTransformer's contiguous kernel.

Correctness (vLLM): a Python reference that gathers keys and values through the block
table, einsum in float, softmax, compare at atol 1e-3; random block tables (numbers
may repeat), random lengths with one at the maximum, GQA and MHA head counts, all
head sizes and block sizes.

Where our outline differs:
- 06.02 to 06.04 follow vLLM's three phases (scores, softmax across the block,
  values); vLLM's softmax is two-pass over a stored row, so the reader's kernel will
  have the same shared-memory limit on context length unless it does something else.
- 06.05 adds the block table after a contiguous cache; vLLM's own test reference is
  exactly the gather-through-the-table loop a reader could write first.
- The `j <= V_VEC_SIZE` loop (my reading, one past the end) is a candidate for 06.06's
  reading lesson; not checked against later vLLM versions.
- vLLM uses `__expf` (error grows with |x| per the Guide) and adds 1e-6 to the sum;
  a tolerance for 06 has to allow for both.

### Module 07 - Attention over a whole prompt

Sources: 12 (FA1, FA2, online softmax), 7 (lecture 12 code), 9 (attention_forward
ladder), 10 (prefill uses xformers at the tag), 8 (why fusion pays).

Order in the papers: memory hierarchy and the memory-bound argument -> standard
attention writes S and P -> softmax by blocks with (m, l) statistics -> the tiled
algorithm -> IO complexity -> backward by recomputation (FA1). FA2: then reduce
non-matmul work (normalise once at the end), parallelise over row blocks, split Q
across warps, skip masked blocks.

Block sizes: FA1 Bc = ceil(M/4d), Br = min(Bc, d); FA2 {64, 128} x {64, 128} by hand
per head dim, 4 or 8 warps.

Warnings: llm.c's simple tiled flash attention (version 2) is about 3x slower than its
naive kernel, and cuBLAS plus a softmax kernel is about 20x faster than naive; FA's
reported speeds are FP16/BF16 tensor-core numbers on A100.

Where our outline differs:
- FA1's loop order (outer over K/V, O, l, m rewritten to HBM on each inner step) and
  FA2's (outer over Q blocks, statistics kept on chip) both "keep a running softmax";
  07.03 does not say which. FA2's is the one with one thread block per Q tile.
- 07.04's block skipping and diagonal-only mask are stated in FA2, not FA1.
- vLLM at the tag has no prefill kernel of its own (xformers), so 07 has no vLLM file
  to read; 07.05 reads FlashAttention, consistent with that.
- A float32 tiled kernel on CUDA cores may not beat a plain kernel at all (llm.c's
  experience); the outline's "every speed measured, library beside it" rule will show
  this, and the lesson text should expect it.

### Module 08 - Half the bits

Sources: 1 (5.6), 2 (ch 12), 7 (lecture 9 accuracy.py; lectures 7, 30, 33-34 on
quantisation, not read beyond titles), 9 (tolerances), 10 (dispatch, fp32
accumulators), 14 (math modes).

What they say: half is IEEE, bf16 is not and needs CC 8.0+; many math functions on
these types are float underneath; contraction to FMA is on by default; fast math
swaps in `__expf`, `__fdividef`, `__tanhf` with stated errors. vLLM: one template, three
types by dispatch; accumulate sums, logits and outputs in float ("for better
accuracy"); silu and RMS norm compute in float and cast. llm.c: tolerance rtol =
FLT_EPSILON for fp32, 0.079 for bf16; whole-model logits 1e-3 vs 25.0.

Where our outline differs:
- 08.02 "one kernel, three types" is vLLM's design; vLLM's tests use one tolerance for
  all three types per kernel (1e-5 activation, 1e-2 RMS norm, 1e-3 attention), while
  the outline (and llm.c) set them per type.
- The CPU side of the track is built with `-ffp-contract=off`; nvcc contracts by
  default, so GPU float results differ from the CPU reference in their last bits from
  module 02 on, not only here.
- The GPU chosen in 02.01 decides whether bf16 is native (CC 8.0+ per the Guide).
- AWQ (08.05) was not in this list and not read.

### Module 09 - Capstone

Sources: 10 (setup.py, bindings, tests), 7 (lecture 1), 9 (test_gpt2.cu), 8, 11, 14.

Binding: vLLM builds ahead of time with setuptools `CUDAExtension`, one module per op
group, `PYBIND11_MODULE` in a .cpp, outputs passed in preallocated, the current
PyTorch stream; GPU MODE lecture 1 uses `load_inline` (compiled at run time) and times
with `torch.cuda.Event` after five warm-ups. Whole-model check: llm.c compares logits,
loss and gradients with a file written by the PyTorch script. Reporting: Horace He's
regimes (overhead, bandwidth, compute) and his scaling test; FA2 and Boehm report a
share of peak; BPG reports effective bandwidth against theoretical.

Where our outline differs:
- The outline does not say ahead-of-time vs `load_inline`; vLLM and GPU MODE show one
  each.
- 09.04 compares with PyTorch per kernel; Horace He's point is that small decode-step
  kernels can be overhead-bound, so per-kernel time and end-to-end time can rank
  differently.
- Whether PyTorch's float32 matmul uses TF32 on the reader's version was not checked;
  cuBLAS's own modes are above.

### Cross-cutting: how the sources time a kernel

| Source | Clock | Warm-up | Statistic | L2 |
|---|---|---|---|---|
| Programming Guide 2.5 | events, stream sync | not stated | one interval | not stated |
| Best Practices ch 9 | events (about 0.5 us) or host timer + device sync | not stated | not stated | not stated |
| Harris global memory | events | one launch | per run | `cudaMemset` of the data before each run |
| Boehm repo | events around 50 launches | none in that loop | mean | not flushed |
| llm.c common.h | events per call | none | mean of repeats | flushed before every call |
| GPU MODE lecture 1 | torch.cuda.Event | 5 calls | one run | not flushed |
| OLCF | host clock, then nsys/ncu | not stated | profiler | not stated |
| CS149 | host timer + `cudaDeviceSynchronize` | not stated | one run | not stated |
| Our track (00.03) | monotonic clock | one call | fastest, median beside | not decided for GPU |

My reading: a kernel that touches only a few MB (one token's activations) stays in L2
when repeated, so the track's GB/s for module 02's small kernels will exceed the
DRAM figure unless the timer flushes L2 as llm.c does or the size exceeds L2.

## (d) Could not read

- PMPP 4th edition text: not free; read only the Elsevier chapter list and blurb.
  O'Reilly's page refused (HTTP 403), so no section-level contents. No figures,
  examples or numbers from the book are in these notes.
- PMPP 5th edition: only its Elsevier page (blurb and chapter titles); no text.
- ECE 408 lecture slides: behind a Canvas folder, not public. GPU Teaching Kit slides:
  the syllabus is public; it refers to the slides as part of a downloaded kit, which I
  did not obtain. Search results showed third-party university copies of kit slides;
  not used, as they are not the authors' or publisher's site.
- OLCF slides and recordings: the series page links none; only the GitHub exercises
  were read.
- GPU MODE slides and videos (Google Slides, YouTube): not read; only the README and
  the code in folders 001, 008, 009, 012.
- Programming Guide 3.2 Advanced Kernel Programming (where warp shuffles are likely to
  be): not read; 2.3 has none.
- Compute Sanitizer: last 25k of 125k characters; cuBLAS: last 26k of 326k characters
  (neither includes anything needed above as far as the parts read show).
- FlashAttention appendices (backward pass, masking and dropout details, exact
  benchmark tables): not read.
- vLLM's later kernels (for 09.05) and whether the `j <= V_VEC_SIZE` loop was fixed:
  not read.
- llama2.c's rotary pairing, and PyTorch's TF32 default: not checked.
