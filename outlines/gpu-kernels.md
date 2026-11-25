---
id: gpu
title: GPU kernels for LLM inference, from scratch
kind: gpu
status: coming soon
audience: Engineers who use PyTorch or an inference server and want to know what runs on the GPU underneath it, well enough to write it.
prerequisites: C (pointers, arrays, loops) and a little Python. Modules 00 and 01 run on any laptop; from module 02 on you need an NVIDIA GPU you can reach - your own, a cloud instance or a hosted notebook. No CUDA and no ML background needed; the inference track helps but is not required.
outcome: Your own CUDA kernels for every operation in a small Llama-style model - matrix multiply, SiLU, RMS norm, rotary positions, a paged KV cache and attention over it - each checked against a reference, called from Python, and timed against PyTorch on the same GPU.
upstream: Proposed, not decided: [vLLM](https://github.com/vllm-project/vllm) (Apache-2.0) at tag v0.2.0 for the kernels the track follows one by one - activation, RMS norm, rotary embedding, the block cache and paged attention, five files and about 1,200 lines of CUDA under csrc/; [flash-attention](https://github.com/Dao-AILab/flash-attention) (BSD-3-Clause) for attention in tiles; [llama2.c](https://github.com/karpathy/llama2.c) (MIT) for the small model and its forward pass in plain C, the reference every kernel is checked against; [llm.c](https://github.com/karpathy/llm.c) (MIT) for a second forward pass in hand-written CUDA to read.
---

# GPU kernels for LLM inference, from scratch

A kernel is one function that the GPU runs as thousands of threads at
once. An inference server such as vLLM is mostly Python; what makes it
fast is a small set of these functions underneath. In this track you
write that set yourself: first matrix multiply on the CPU, to see why
memory decides the speed, then the same on the GPU, then the kernels a
language model needs, ending at attention over a KV cache stored in
blocks, which is the idea vLLM is known for.

The track follows vLLM at its tag v0.2.0, when its kernels were five
files a person can read in an afternoon. You write each one before you
read theirs. Today's vLLM has many times as much kernel code and the
paged attention files are no longer in it; the last lesson reads what
changed and why.

Two rules hold from the first lesson. A kernel is checked against a
slow, plain reference before anyone times it. And every speed in a
lesson is one you measured on your own GPU, with the library's number
next to it.

**Coming soon.** This is the outline: the direction, not the lessons yet.
Format: `templates/outline.md`.

## Module 00 - The workbench

- Goal: Know when to believe a result and when to believe a timing, before there is anything fast to measure.
- You build: A first function that adds two arrays, the plain version of it you trust, a checker that compares any output with a reference, and a timer that warms up, repeats and reports bytes moved per second. All of it in C, on the CPU.
- Value: The checker and the timer are used in every later module, and they are what any claim about performance needs behind it.
- Lessons:
  - 00.01 A first function, and the plain version you trust
  - 00.02 Right before fast: checking against a reference
  - 00.03 Timing: warm up, repeat, count the bytes
- Learn from: [B-CSAPP], [A-BRRR], [A-CLOSE], [C-HYPER], [C-LLAMA2C]

## Module 01 - Matrix multiply on the CPU

- Goal: Understand why the same arithmetic can run many times faster: the cost is in how memory is read, not in the multiplications.
- You build: Matrix multiply in C five ways - three plain loops, the loops reordered, blocked for the cache, vectorised, threaded - each one timed against the BLAS library on your machine.
- Value: Every idea the GPU modules use - locality, tiles, many lanes at once - appears here first, on a machine you can step through with a debugger.
- Lessons:
  - 01.01 Three loops and a reference
  - 01.02 Loop order and the cache
  - 01.03 Blocking
  - 01.04 SIMD: several floats in one instruction
  - 01.05 Threads, and the distance left to BLAS
- Learn from: [B-CSAPP], [P-GOTO], [A-MMCPU], [A-ALGO]

## Module 02 - Threads, blocks and a grid

- Goal: Know how a GPU runs one function as thousands of threads, and where the data has to be before it can.
- You build: A first kernel that adds two arrays on the GPU, held to module 00's checker, a timer that waits for the GPU to finish, and an element-wise kernel in the shape vLLM uses - one block of threads for each token, each thread striding across the row - for SiLU, GELU and the fused SiLU-and-multiply of a Llama MLP.
- Value: Most kernels in an inference engine have this shape. After it you can read vLLM's activation kernels line by line.
- Lessons:
  - 02.01 A GPU you can reach, and a first kernel
  - 02.02 One function, many threads: the grid, the block, the thread
  - 02.03 Host and device: what a copy costs
  - 02.04 Timing a GPU: wait before you stop the clock
  - 02.05 SiLU and GELU, a block for each token
  - 02.06 Two operations in one kernel: SiLU and multiply
  - 02.07 Reading vLLM: activation_kernels.cu
- Learn from: [B-PMPP], [A-CUDA], [A-SAN], [A-BRRR], [C-VLLM]

## Module 03 - Matrix multiply on the GPU

- Goal: Understand what limits a GPU kernel - how its threads read memory - by making one kernel faster three times.
- You build: Matrix multiply on the GPU: one thread for each output element, then reads the hardware can combine, then tiles held in shared memory, measured against cuBLAS at each step.
- Value: The linear layers are most of a model's arithmetic. You come out knowing how the library gets its speed, and when to call it instead of writing your own.
- Lessons:
  - 03.01 One thread for each output element
  - 03.02 Coalescing: neighbouring threads read neighbouring memory
  - 03.03 Tiles in shared memory
  - 03.04 Against cuBLAS: what is left, and when to call the library
- Learn from: [B-PMPP], [A-MMGPU], [A-BPG]

## Module 04 - Many threads, one number

- Goal: Know how the threads of a block combine their values into one, which is what normalisation and softmax both need.
- You build: A sum across a whole block, made from warp shuffles and a little shared memory, and on top of it an RMS norm kernel and a softmax that cannot overflow.
- Value: The reduction is the second kernel shape after element-wise. With the two of them you can write most of what a model needs apart from attention.
- Lessons:
  - 04.01 A sum in parallel
  - 04.02 Warps and shuffles
  - 04.03 From one warp to the whole block
  - 04.04 RMS norm, as vLLM writes it
  - 04.05 Softmax without overflow
- Learn from: [B-PMPP], [A-CUDA], [P-RMS], [C-VLLM]

## Module 05 - Positions and the KV cache

- Goal: Understand the memory an inference server manages on the GPU: keys and values in fixed-size blocks, found through a table.
- You build: A rotary embedding kernel that turns queries and keys in place, a KV cache laid out as blocks, the kernel that writes each new token's key and value into its slot, and the one that copies a block.
- Value: This is the memory design of vLLM's paper. Because a sequence's blocks need not be next to each other, a server can grow sequences without moving them and share a prefix between them.
- Lessons:
  - 05.01 Rotary positions, in place
  - 05.02 The KV cache as blocks and a block table
  - 05.03 Writing a token into its slot
  - 05.04 Copying blocks: two sequences that share a prefix
  - 05.05 Reading vLLM: cache_kernels.cu
- Learn from: [P-ROPE], [P-VLLM], [C-VLLM]

## Module 06 - Attention for one new token

- Goal: Understand the kernel that runs for every generated token: one query against every cached key, read through the block table.
- You build: A decode attention kernel - a block of threads for each head of each sequence, the scores, a softmax across the block, the weighted sum of values - first over a cache in one piece, then over the paged one.
- Value: You can now read vLLM's paged attention kernel, and say what each of its loops is for.
- Lessons:
  - 06.01 What one step of attention computes
  - 06.02 A block of threads for each head of each sequence
  - 06.03 Scores: the query against every key
  - 06.04 Softmax across the block, then the values
  - 06.05 Through the block table: paged attention
  - 06.06 Reading vLLM: attention_kernels.cu
- Learn from: [P-ATTN], [P-VLLM], [C-VLLM]

## Module 07 - Attention over a whole prompt

- Goal: Understand how attention over a long prompt is computed without ever storing its table of scores.
- You build: A prefill attention kernel twice: the plain one that stores a score for every pair of tokens, and a tiled one that keeps a running softmax and holds only one tile at a time.
- Value: This is the idea of FlashAttention, which most engines use for the prompt. You can follow its paper and find your way in its source.
- Lessons:
  - 07.01 The table that does not fit
  - 07.02 A running softmax: one pass, tile by tile
  - 07.03 A tiled attention kernel
  - 07.04 The causal mask, and the tiles it lets you skip
  - 07.05 Reading FlashAttention
- Learn from: [P-FLASH], [P-FLASH2], [P-ONLINE], [C-FLASH]

## Module 08 - Half the bits

- Goal: Know what changes in a kernel when its numbers are 16 bits wide instead of 32, and where it must still use 32.
- You build: Every kernel so far made to work on float32, float16 and bfloat16 from one source, with sums and exponentials kept in float32, and the checker's tolerances set for each type.
- Value: Models are served in half precision. A kernel that is only right in float32 is not one a server can use.
- Lessons:
  - 08.01 float16 and bfloat16 on a GPU
  - 08.02 One kernel, three types
  - 08.03 Where to keep full precision: sums and exponentials
  - 08.04 Measuring it: bytes, time and error
  - 08.05 Reading vLLM: 4-bit weights in the AWQ kernel
- Learn from: [A-CUDA], [P-AWQ], [C-VLLM]

## Module 09 - Capstone: a model on your kernels

- Goal: Put the kernels under a real model and judge the result against PyTorch, honestly.
- You build: A Python extension that offers your kernels as functions on PyTorch tensors, the small Llama-style model generating text with every operation on the GPU yours, and a benchmark report against PyTorch on the same GPU.
- Value: A public, reproducible write-up, kernel by kernel, of what you wrote and how close it comes.
- Lessons:
  - 09.01 Kernels as Python functions
  - 09.02 The whole model on your kernels
  - 09.03 Many sequences at once
  - 09.04 The report: against PyTorch, kernel by kernel
  - 09.05 What vLLM's kernels became
- Learn from: [C-VLLM], [C-LLAMA2C], [C-LLMC], [P-VLLM]

## Library

| Key | Kind | Title | By | Where |
|---|---|---|---|---|
| B-PMPP | book | Programming Massively Parallel Processors, 4th edition | Wen-mei Hwu, David Kirk, Izzat El Hajj | Morgan Kaufmann, 2022 |
| B-CSAPP | book | Computer Systems: A Programmer's Perspective, 3rd edition | Randal Bryant, David O'Hallaron | Pearson, 2015 |
| A-CUDA | article | CUDA Programming Guide | NVIDIA | https://docs.nvidia.com/cuda/cuda-programming-guide/ |
| A-BPG | article | CUDA C++ Best Practices Guide | NVIDIA | https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/ |
| A-SAN | article | Compute Sanitizer | NVIDIA | https://docs.nvidia.com/compute-sanitizer/ |
| A-CLOSE | article | numpy.isclose: when two floating-point numbers count as equal | NumPy | https://numpy.org/doc/stable/reference/generated/numpy.isclose.html |
| A-BRRR | article | Making Deep Learning Go Brrrr From First Principles | Horace He | https://horace.io/brrr_intro.html |
| A-MMCPU | article | Fast Multidimensional Matrix Multiplication on CPU from Scratch | Simon Boehm | https://siboehm.com/articles/22/Fast-MMM-on-CPU |
| A-MMGPU | article | How to Optimize a CUDA Matmul Kernel for cuBLAS-like Performance: a Worklog | Simon Boehm | https://siboehm.com/articles/22/CUDA-MMM |
| A-ALGO | article | Matrix Multiplication (Algorithms for Modern Hardware) | Sergey Slotin | https://en.algorithmica.org/hpc/algorithms/matmul/ |
| P-GOTO | paper | Anatomy of High-Performance Matrix Multiplication | Goto and van de Geijn, 2008 | https://www.cs.utexas.edu/~flame/pubs/GotoTOMS_revision.pdf |
| P-ATTN | paper | Attention Is All You Need | Vaswani et al., 2017 | https://arxiv.org/abs/1706.03762 |
| P-RMS | paper | Root Mean Square Layer Normalization | Zhang and Sennrich, 2019 | https://arxiv.org/abs/1910.07467 |
| P-ROPE | paper | RoFormer: Enhanced Transformer with Rotary Position Embedding | Su et al., 2021 | https://arxiv.org/abs/2104.09864 |
| P-VLLM | paper | Efficient Memory Management for Large Language Model Serving with PagedAttention | Kwon et al., 2023 | https://arxiv.org/abs/2309.06180 |
| P-FLASH | paper | FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness | Dao et al., 2022 | https://arxiv.org/abs/2205.14135 |
| P-FLASH2 | paper | FlashAttention-2: Faster Attention with Better Parallelism and Work Partitioning | Tri Dao, 2023 | https://arxiv.org/abs/2307.08691 |
| P-ONLINE | paper | Online normalizer calculation for softmax | Milakov and Gimelshein, 2018 | https://arxiv.org/abs/1805.02867 |
| P-AWQ | paper | AWQ: Activation-aware Weight Quantization for LLM Compression and Acceleration | Lin et al., 2023 | https://arxiv.org/abs/2306.00978 |
| C-VLLM | code | vLLM, the kernels under csrc/ at tag v0.2.0 | The vLLM team | https://github.com/vllm-project/vllm/tree/v0.2.0/csrc |
| C-HYPER | code | hyperfine, a command-line benchmarking tool | David Peter and contributors | https://github.com/sharkdp/hyperfine |
| C-FLASH | code | flash-attention | Tri Dao and contributors | https://github.com/Dao-AILab/flash-attention |
| C-LLAMA2C | code | llama2.c | Andrej Karpathy | https://github.com/karpathy/llama2.c |
| C-LLMC | code | llm.c | Andrej Karpathy | https://github.com/karpathy/llm.c |
