---
id: 05
title: Generalisation
---

# Module 05 - Generalisation

Module 04 made deep networks train; this module asks whether what they learned holds on digits they have never seen. It starts by cutting MNIST three ways - a training set to learn from, a validation set to choose with, a test set scored once at the end - and shows why it has to: the same network of two hidden layers gets every one of 1000 training labels right whether the labels are real or drawn at random, and only the held-out digits tell learning from memorising. Then three ways to make a network trained on 2000 digits memorise less and generalise more, each tested against the same untouched network over several seeds: weight decay, from module 03's AdamW, which helps a little; dropout, a new layer for the engine under PyTorch's name, which helps more, as Srivastava et al. found on all of MNIST; and new training images made every pass by moving each digit a pixel or two, which helps most. The module ends with double descent: on a model of random features fitted exactly by least squares, the test error climbs to a peak where the model has just enough features to fit its training set, then falls below its first minimum as the model keeps growing, which the older picture of overfitting does not predict. It stands on module 03's MNIST, training loop and optimisers. After it, the track judges a model by digits it was not trained on: choices are made on the validation set, and the test set is scored once.
