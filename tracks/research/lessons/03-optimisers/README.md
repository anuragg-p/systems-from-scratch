---
id: 03
title: Optimisers: from the plain step to AdamW
---

# Module 03 - Optimisers: from the plain step to AdamW

Module 02 ended with a small PyTorch: tensors, layers and cross-entropy, all checked against PyTorch's gradients, and a network trained on two groups of points by a step written out by hand. This module trains on real data, 60,000 handwritten digits, and turns that step into the optimisers almost every published model is trained with, each one the fix for something the one before it was seen to do wrong. Plain stochastic gradient descent, in batches, learns MNIST in one pass at the right rate and wrecks the network at a rate four times too big. Momentum stops it zigzagging across a narrow valley. Adam gives every weight a step of its own size, so one rate serves weights whose gradients differ a thousandfold, where momentum needs a rate for the steepest and then crawls on the rest; the Adam paper's race against momentum is run again on the way, and at this size it is a tie. AdamW takes the weight decay out of Adam's gradient, after a run shows Adam with an L2 term driving to zero the weights the data never touches. A schedule finally changes the rate as training goes: a warmup takes away the spike of the first steps, and a cosine decay ends lower than the best constant rate. After this module the engine has `torch.optim` with SGD, Adam, AdamW and LambdaLR, and every later module trains with them.
