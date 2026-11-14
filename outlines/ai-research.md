---
id: research
title: AI research, from a first experiment to your own result
kind: research
status: coming soon
audience: Programmers who want to do machine learning research, not only use models.
prerequisites: Python, high-school calculus, basic linear algebra and probability. No ML background needed.
outcome: A paper result you reproduced yourself and one small original experiment, both written up with code anyone can rerun.
upstream: Proposed, not decided: [micrograd](https://github.com/karpathy/micrograd) (MIT) for the autograd engine; [nanoGPT](https://github.com/karpathy/nanoGPT) (MIT) for the transformer language model; [grok](https://github.com/openai/grok) (MIT) for the reproduction; [TransformerLens](https://github.com/TransformerLensOrg/TransformerLens) (MIT) for probes and circuits.
---

# AI research, from a first experiment to your own result

Research is a craft: train a model, doubt the result, change one thing,
measure again, write down what is true. You learn it by doing it. Every
lesson here ends with a plot or a number you produced, and the track ends
with a reproduction and a result of your own.

**Coming soon.** This is the outline: the direction, not the lessons yet.
Format: `templates/outline.md`.

## Module 00 - The workbench

- Goal: Be able to run an experiment twice and get the same answer.
- You build: A project skeleton with seeds, config files, logging and plots.
- Value: Every later experiment, and any research code you write after this, starts from this skeleton.
- Lessons:
  - 00.01 A reproducible run
  - 00.02 Tracking experiments
- Learn from: [B-D2L], [A-RECIPE], [A-SCHUL]

## Module 01 - A learning machine, by hand

- Goal: Understand training as a few lines of calculus you wrote.
- You build: An automatic differentiation engine, and a network trained with it.
- Value: You can now read and debug any training loop, in any framework.
- Lessons:
  - 01.01 Backpropagation
  - 01.02 A network that learns
  - 01.03 Optimisers
- Learn from: [B-UDL], [V-MICRO], [V-3B1B], [B-DL], [P-ADAM]

## Module 02 - Training well

- Goal: Get a model to train, and know why when it does not.
- You build: A debugging checklist you ran yourself, on a model you broke on purpose.
- Value: Most research time is spent here; this is the skill that saves weeks.
- Lessons:
  - 02.01 The recipe
  - 02.02 Initialisation and normalisation
  - 02.03 Generalisation
- Learn from: [A-RECIPE], [B-UDL], [V-ZTH]

## Module 03 - Architectures that matter

- Goal: Build the three model families most current work stands on.
- You build: A residual network for images, a transformer language model, and a fine-tune of a pretrained model.
- Value: These are working baselines you can modify for your own questions.
- Lessons:
  - 03.01 Convolution and residual connections
  - 03.02 A transformer language model
  - 03.03 Fine-tuning
- Learn from: [B-UDL], [K-231N], [P-RESNET], [V-GPT], [P-ATTN], [P-LORA]

## Module 04 - Reading and reproducing

- Goal: Turn a paper into code, and find out whether its claim holds.
- You build: A reproduction of one published figure.
- Value: Reproduction is how you learn a subfield, and a reproduced result is a real contribution.
- Lessons:
  - 04.01 How to read a paper
  - 04.02 Reproduce a figure
  - 04.03 Ablations
- Learn from: [A-KESHAV], [P-GROK], [A-SCHUL]

## Module 05 - Experimenting like a scientist

- Goal: Produce results that would survive someone trying to break them.
- You build: A baseline, error bars, and an evaluation you tried to fool.
- Value: This is the difference between a demo and a finding.
- Lessons:
  - 05.01 Hypotheses and baselines
  - 05.02 Noise
  - 05.03 Evaluation that cannot be gamed
- Learn from: [A-SCHUL], [B-MML], [P-RLMAT], [B-DL]

## Module 06 - Looking inside

- Goal: Ask what a trained model computes, not only how well it scores.
- You build: A probe and a small circuit analysis on a model you trained.
- Value: Interpretability is an open field where small, careful work still counts.
- Lessons:
  - 06.01 Probing
  - 06.02 A circuit
- Learn from: [A-CIRC], [A-MATH]

## Module 07 - Your own result

- Goal: Ask a small question nobody has answered, and answer it.
- You build: An experiment, a short paper, and a public repository.
- Value: Finished, public research you can point to.
- Lessons:
  - 07.01 Choosing a question
  - 07.02 The experiment
  - 07.03 The paper
- Learn from: [A-HAMMING], [A-SCHUL]

## Library

| Key | Kind | Title | By | Where |
|---|---|---|---|---|
| B-UDL | book | Understanding Deep Learning | Simon J.D. Prince | MIT Press, 2023; free at https://udlbook.github.io/udlbook/ |
| B-DL | book | Deep Learning | Ian Goodfellow, Yoshua Bengio, Aaron Courville | MIT Press, 2016; free at https://www.deeplearningbook.org |
| B-D2L | book | Dive into Deep Learning | Zhang, Lipton, Li, Smola | free at https://d2l.ai |
| B-MML | book | Mathematics for Machine Learning | Deisenroth, Faisal, Ong | Cambridge, 2020; free at https://mml-book.github.io |
| V-MICRO | video | The spelled-out intro to neural networks and backpropagation: building micrograd | Andrej Karpathy | https://www.youtube.com/watch?v=VMj-3S1tku0 |
| V-ZTH | video | Neural Networks: Zero to Hero (playlist) | Andrej Karpathy | https://karpathy.ai/zero-to-hero.html |
| V-GPT | video | Let's build GPT: from scratch, in code, spelled out | Andrej Karpathy | https://www.youtube.com/watch?v=kCc8FmEb1nY |
| V-3B1B | video | Neural networks (series) | 3Blue1Brown | https://www.3blue1brown.com/topics/neural-networks |
| K-231N | course | CS231n: Deep Learning for Computer Vision | Stanford | https://cs231n.stanford.edu |
| A-RECIPE | article | A Recipe for Training Neural Networks | Andrej Karpathy | https://karpathy.github.io/2019/04/25/recipe/ |
| A-SCHUL | article | An Opinionated Guide to ML Research | John Schulman | http://joschu.net/blog/opinionated-guide-ml-research.html |
| A-KESHAV | article | How to Read a Paper | S. Keshav | https://web.stanford.edu/class/ee384m/Handouts/HowtoReadPaper.pdf |
| A-HAMMING | article | You and Your Research | Richard Hamming | https://www.cs.virginia.edu/~robins/YouAndYourResearch.html |
| A-CIRC | article | Zoom In: An Introduction to Circuits | Olah et al., Distill 2020 | https://distill.pub/2020/circuits/zoom-in/ |
| A-MATH | article | A Mathematical Framework for Transformer Circuits | Elhage et al., 2021 | https://transformer-circuits.pub/2021/framework/index.html |
| P-ATTN | paper | Attention Is All You Need | Vaswani et al., 2017 | https://arxiv.org/abs/1706.03762 |
| P-ADAM | paper | Adam: A Method for Stochastic Optimization | Kingma, Ba, 2014 | https://arxiv.org/abs/1412.6980 |
| P-RESNET | paper | Deep Residual Learning for Image Recognition | He et al., 2015 | https://arxiv.org/abs/1512.03385 |
| P-LORA | paper | LoRA: Low-Rank Adaptation of Large Language Models | Hu et al., 2021 | https://arxiv.org/abs/2106.09685 |
| P-GROK | paper | Grokking: Generalization Beyond Overfitting on Small Algorithmic Datasets | Power et al., 2022 | https://arxiv.org/abs/2201.02177 |
| P-RLMAT | paper | Deep Reinforcement Learning that Matters | Henderson et al., 2017 | https://arxiv.org/abs/1709.06560 |
