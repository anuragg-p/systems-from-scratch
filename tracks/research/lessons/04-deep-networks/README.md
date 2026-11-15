---
id: 04
title: Deep networks that train
---

# Module 04 - Deep networks that train

Module 03 trained a network with one hidden layer on MNIST and gave it good steps to take; this module makes the network deep, and it starts by failing. Twenty layers stacked the obvious way learn nothing at all, and a picture of every layer shows why: the difference between one digit and the next shrinks layer by layer on the way in, and the gradient shrinks layer by layer on the way back. Three ideas let a network go deep, and each comes in as a change to the network already on the page, held to the paper that introduced it and run again at laptop size: starting weights of the right size (Glorot and Bengio, and He et al.), normalising what each layer passes on (Ioffe and Szegedy's batch norm, then Ba, Kiros and Hinton's layer norm, which does not depend on the rest of the batch), and shortcuts that give the gradient a path around the layers (He et al.'s residual networks). For each paper the page states its claim, shows our number beside it, and says where it held and where it did not. The module ends with five bugs that crash nothing and a checklist of five measurements, one to catch each, which the lab keeps from then on. After it a network of thirty layers trains, and a training script that runs without an error can be checked for being right.
