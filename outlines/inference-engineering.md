---
id: inference
title: An LLM inference server, from scratch
kind: inference
status: coming soon
audience: Engineers who can program and want to run and serve language models well.
prerequisites: Python, basic linear algebra (matrix multiply), comfort with a terminal. No ML background needed.
outcome: Your own server that loads an open model, streams tokens over an OpenAI-compatible API, batches requests, runs quantized, and comes with a benchmark report against llama.cpp.
upstream: Proposed, not decided: [llama.cpp](https://github.com/ggml-org/llama.cpp) (MIT) for the quantised formats, the server and the capstone's yardstick; [picoGPT](https://github.com/jaymody/picoGPT) (MIT) for the GPT-2 forward pass in numpy; [vLLM](https://github.com/vllm-project/vllm) (Apache-2.0) for batching, scheduling and paged KV memory.
---

# An LLM inference server, from scratch

You start with a model file and end with a service other programs can call.
Along the way you write the forward pass yourself, make it fast, make it
small, put it behind an API, and measure every step. Each lesson ends with
a number you measured on your own machine, not a claim you read.

**Coming soon.** This is the outline: the direction, not the lessons yet.
Format: `templates/outline.md`.

## Module 00 - The workbench

- Goal: Know what "running a model" consists of and how to measure it.
- You build: A script that generates text from GPT-2, and a benchmark harness.
- Value: The harness is reused in every later module, and on any model you ever serve.
- Lessons:
  - 00.01 Run a model end to end
  - 00.02 Measure it
- Learn from: [B-AIE], [V-GPT], [A-ILLUS], [B-PERF], [A-ARITH]

## Module 01 - The forward pass, by hand

- Goal: Understand a transformer as arithmetic you wrote yourself.
- You build: A tokenizer and a GPT-2 forward pass in plain numpy that match a reference to the last decimal.
- Value: After this, no inference optimisation is a black box: you know what is being optimised.
- Lessons:
  - 01.01 The tokenizer
  - 01.02 The transformer forward pass
  - 01.03 Sampling
- Learn from: [V-TOK], [P-ATTN], [V-GPT], [A-ANNOT], [B-AIE]

## Module 02 - Fast for one request

- Goal: Know where the time goes in a single generation, and remove the waste.
- You build: A KV cache, a profiled and vectorised hot loop, and memory-mapped weights.
- Value: The same three moves are the first things to check in any slow model service.
- Lessons:
  - 02.01 The KV cache
  - 02.02 Profile, then optimise
  - 02.03 Loading and memory
- Learn from: [A-ARITH], [A-WENG], [B-PERF], [B-CSAPP], [A-BRRR], [C-LLAMA]

## Module 03 - Small

- Goal: Trade precision for memory and speed, and measure what it costs in quality.
- You build: 16-bit, 8-bit and 4-bit versions of your model, and a perplexity evaluation.
- Value: Quantisation is what lets a model fit on the hardware you actually have.
- Lessons:
  - 03.01 Number formats
  - 03.02 8-bit quantisation
  - 03.03 4-bit, and measuring the damage
- Learn from: [B-CSAPP], [K-EFF], [P-QUANT], [P-GPTQ], [A-WENG]

## Module 04 - Served

- Goal: Turn a function into a service many clients can use at once.
- You build: A streaming HTTP API compatible with OpenAI clients, with batching and a scheduler.
- Value: Any existing chat client or SDK can now talk to the thing you wrote.
- Lessons:
  - 04.01 A streaming API
  - 04.02 Batching
  - 04.03 Scheduling and backpressure
- Learn from: [B-DMLS], [P-ORCA], [P-VLLM]

## Module 05 - Bigger hardware, better algorithms

- Goal: Understand what a GPU changes, and three ideas real engines rely on.
- You build: A GPU path, paged KV memory, and speculative decoding.
- Value: These are the ideas behind the engines used in production; you can now read their code.
- Lessons:
  - 05.01 The GPU
  - 05.02 Memory for many sequences
  - 05.03 Speculative decoding
- Learn from: [B-PMPP], [K-DLSYS], [A-BRRR], [P-VLLM], [P-FLASH], [P-SPEC]

## Module 06 - In production

- Goal: Know whether the service is good enough, what it costs, and when it is failing.
- You build: A load test, a cost model, and metrics.
- Value: These three documents are what a team asks for before putting a model in front of users.
- Lessons:
  - 06.01 Load testing and targets
  - 06.02 What a token costs
  - 06.03 Seeing it run
- Learn from: [B-PERF], [B-AIE], [B-DMLS]

## Module 07 - Capstone

- Goal: Judge your own engine against real ones, honestly.
- You build: A benchmark report comparing your server with llama.cpp on the same model and machine.
- Value: A public, reproducible write-up that shows what you can do.
- Lessons:
  - 07.01 The comparison
  - 07.02 The write-up
- Learn from: [C-LLAMA]

## Library

| Key | Kind | Title | By | Where |
|---|---|---|---|---|
| B-AIE | book | AI Engineering | Chip Huyen | O'Reilly, 2025 |
| B-DMLS | book | Designing Machine Learning Systems | Chip Huyen | O'Reilly, 2022 |
| B-PERF | book | Systems Performance, 2nd edition | Brendan Gregg | Addison-Wesley, 2020 |
| B-CSAPP | book | Computer Systems: A Programmer's Perspective, 3rd edition | Randal Bryant, David O'Hallaron | Pearson, 2015 |
| B-PMPP | book | Programming Massively Parallel Processors, 4th edition | Wen-mei Hwu, David Kirk, Izzat El Hajj | Morgan Kaufmann, 2022 |
| V-GPT | video | Let's build GPT: from scratch, in code, spelled out | Andrej Karpathy | https://www.youtube.com/watch?v=kCc8FmEb1nY |
| V-TOK | video | Let's build the GPT Tokenizer | Andrej Karpathy | https://www.youtube.com/watch?v=zduSFxRajkE |
| K-EFF | course | TinyML and Efficient Deep Learning Computing (MIT 6.5940) | Song Han | https://efficientml.ai |
| K-DLSYS | course | Deep Learning Systems | Zico Kolter, Tianqi Chen | https://dlsyscourse.org |
| A-ILLUS | article | The Illustrated Transformer | Jay Alammar | https://jalammar.github.io/illustrated-transformer/ |
| A-ANNOT | article | The Annotated Transformer | Harvard NLP | https://nlp.seas.harvard.edu/annotated-transformer/ |
| A-ARITH | article | Transformer Inference Arithmetic | Kipply | https://kipp.ly/transformer-inference-arithmetic/ |
| A-WENG | article | Large Transformer Model Inference Optimization | Lilian Weng | https://lilianweng.github.io/posts/2023-01-10-inference-optimization/ |
| A-BRRR | article | Making Deep Learning Go Brrrr From First Principles | Horace He | https://horace.io/brrr_intro.html |
| P-ATTN | paper | Attention Is All You Need | Vaswani et al., 2017 | https://arxiv.org/abs/1706.03762 |
| P-QUANT | paper | A White Paper on Neural Network Quantization | Nagel et al., 2021 | https://arxiv.org/abs/2106.08295 |
| P-GPTQ | paper | GPTQ: Accurate Post-Training Quantization for Generative Pre-trained Transformers | Frantar et al., 2022 | https://arxiv.org/abs/2210.17323 |
| P-ORCA | paper | Orca: A Distributed Serving System for Transformer-Based Generative Models | Yu et al., OSDI 2022 | https://www.usenix.org/conference/osdi22/presentation/yu |
| P-VLLM | paper | Efficient Memory Management for Large Language Model Serving with PagedAttention | Kwon et al., 2023 | https://arxiv.org/abs/2309.06180 |
| P-FLASH | paper | FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness | Dao et al., 2022 | https://arxiv.org/abs/2205.14135 |
| P-SPEC | paper | Fast Inference from Transformers via Speculative Decoding | Leviathan et al., 2023 | https://arxiv.org/abs/2211.17192 |
| C-LLAMA | code | llama.cpp | Georgi Gerganov and contributors | https://github.com/ggml-org/llama.cpp |
