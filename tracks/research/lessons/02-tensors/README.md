---
id: 02
title: Tensors: a small PyTorch
---

# Module 02 - Tensors: a small PyTorch

Module 01 built an engine of single numbers and trained a network with it, at about seventy milliseconds a step for a network of 105 weights. This module writes the engine again over numpy arrays, under PyTorch's own names, and from here on it gives PyTorch's gradients: the same lines run with `import engine as torch` or `import torch` and print the same numbers. It starts with elementwise arithmetic, one object for a whole array instead of one per number, a thousand times faster than the Values on twenty thousand numbers. Broadcasting lets a batch and a bias meet in one operation, and its backward is a sum; the nudge of 01.01 becomes `gradcheck`, which holds every gradient after it. A matrix product makes a whole layer one operation, and its backward is two more products; with sums, indexing and in-place updates the two groups train again, hundreds of times faster a step. Softmax and cross-entropy are written so that no score can overflow them, and their gradient comes out as p - y. Last, `nn.Module`, `nn.Linear` and `nn.Sequential` hold a network's weights and name them as PyTorch does, and a trained network goes to a safetensors file whose bytes are on the page, which PyTorch's own `nn.Sequential` loads. After this module the engine can train any small network a PyTorch script describes, and module 03 feeds it the digits of MNIST.
