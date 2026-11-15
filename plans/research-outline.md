---
id: research
title: AI research, from a first experiment to your own result
kind: research
status: coming soon
audience: Programmers who want to do machine learning research, not only call models: build them, train them, and test the claims made about them.
prerequisites: Python, high-school calculus (a derivative, the chain rule), and what a matrix and a probability are. No machine learning background, and no GPU: every lesson runs on a laptop.
outcome: A deep learning engine you wrote that gives PyTorch's gradients, a GPT that loads the published GPT-2 weights and gives the same numbers, the central idea of more than twenty papers written into your own code and tested on your own laptop, one published result reproduced, and one small result of your own, written up with code anyone can rerun.
upstream: Proposed, not decided: [pytorch](https://github.com/pytorch/pytorch) (BSD-3-Clause) for the names the engine uses and the numbers it is checked against, with no code taken; [micrograd](https://github.com/karpathy/micrograd) (MIT) for the autograd engine; [nanoGPT](https://github.com/karpathy/nanoGPT) (MIT) for the transformer language model; [minbpe](https://github.com/karpathy/minbpe) (MIT) for the tokenizer; [gpt-2](https://github.com/openai/gpt-2) (Modified MIT) for the published weights and tokenizer the model is checked against; [grok](https://github.com/openai/grok) (MIT) for the reproduction; [TransformerLens](https://github.com/TransformerLensOrg/TransformerLens) (MIT) for the interpretability extension.
---

# AI research, from a first experiment to your own result

You do not start from a paper and look for a use. You start from a model
that will not train, trains too slowly, or forgets what it read, and the
paper is what fixes it. You write the fix into your own code, then run
the paper's own experiment again at a size a laptop can finish, and see
for yourself whether the claim holds.

The first third is an engine you write yourself in numpy: automatic
differentiation, tensors and optimisers, checked against PyTorch to six
decimal places. Once yours gives the same numbers, the same scripts run
on PyTorch by changing one import, and the rest of the track uses it, as
research does. Everything is held to the real thing: your tokenizer gives
tiktoken's ids, your GPT loads the published GPT-2 weights and gives the
same logits, and each paper's figure is drawn again from your own run.

Modules 00 to 05 build the engine and the craft of training. Modules 06
to 12 build the models, up to a GPT you trained, tuned and made fast.
Modules 13 to 15 are research itself: experiments that hold up, a
reproduction, and a result of your own. After the core comes a shelf of
optional modules, 16 to 21, each one a field's founding papers built on
the code you already have. Each is independent of the others.

**Coming soon.** This is the outline: the direction, not the lessons yet.
Format: `templates/outline.md`.

## Module 00 - The workbench

- Goal: Run an experiment twice and get the same number, and know how far that number moves when only the seed changes.
- You build: A whole experiment in one file - data, model, loss, update, evaluation - fitting a curve with gradients worked out by hand, then a runner that records the config, the seed and the log of every run and draws runs over each other.
- Value: Every result in the track, and any you report after it, is a set of runs from this runner over several seeds.
- Lessons:
  - 00.01 One experiment, end to end
  - 00.02 The same run twice: seeds, configs and logs
  - 00.03 Five seeds: how far a number moves by chance
- Learn from: [A-RECIPE], [A-SCHUL], [B-D2L], [P-VAR]

## Module 01 - Backpropagation: an autograd engine

- Goal: Understand training as the chain rule run backwards over a graph you built.
- You build: An automatic differentiation engine over single numbers, a small network on top of it that learns to tell two groups of points apart, and a check that holds every derivative to a nudge: move the input a little each way and watch the output.
- Value: You can read and debug any training loop in any framework, and the nudge is the test you will use on every formula in the track.
- Lessons:
  - 01.01 A derivative by nudging
  - 01.02 A graph of values, and the chain rule backwards
  - 01.03 A neuron, a layer, a network
  - 01.04 Training it: a loss that goes down
- Learn from: [V-MICRO], [P-BACKPROP], [B-UDL], [V-3B1B], [P-AD], [C-MICROGRAD]

## Module 02 - Tensors: a small PyTorch

- Goal: Know what a tensor library does on every line you will write later: shapes, broadcasting, and the backward of each operation.
- You build: The engine again over numpy arrays, under PyTorch's own names - `Tensor`, `nn.Module`, `nn.Linear`, `F.cross_entropy` - giving PyTorch's gradients to six decimal places, and a checkpoint in the safetensors format that PyTorch's tools open.
- Value: The framework stops being a black box: a shape error or a wrong gradient in PyTorch is now something you have built and can reason about.
- Lessons:
  - 02.01 The scalar engine is a thousand times too slow
  - 02.02 Broadcasting, and its backward
  - 02.03 Matrix multiply, sums and indexing
  - 02.04 Softmax and cross-entropy without overflow
  - 02.05 Modules, parameters, and a checkpoint file
- Learn from: [K-DLSYS], [C-TINYGRAD], [B-UDL], [B-MML], [P-AD], [A-SAFET], [C-PYTORCH]

## Module 03 - Optimisers: from the plain step to AdamW

- Goal: Understand each optimiser as the fix for something you watched the one before it do wrong.
- You build: A digit classifier on MNIST trained with your own SGD, momentum, Adam and AdamW and a warmup and cosine schedule, and the Adam paper's comparison run again on your engine.
- Value: These five pieces train almost every model published today; you will know which knob to turn when a run misbehaves, and why.
- Lessons:
  - 03.01 MNIST in batches, and a learning rate that is too big
  - 03.02 Momentum: the zigzag in a narrow valley
  - 03.03 Adam: a step size for each parameter
  - 03.04 AdamW: weight decay is not L2
  - 03.05 Learning-rate schedules: warmup and cosine decay
- Learn from: [P-LENET], [P-MOM], [A-MOMENTUM], [P-ADAM], [P-ADAMW], [P-SGDR], [B-UDL], [A-TUNE]

## Module 04 - Deep networks that train

- Goal: Know why adding layers stops a network from learning, and the three ideas that let it go deep.
- You build: Pictures of the activations and gradients at every layer, a deep network that learns nothing and then trains after each fix - initialisation, normalisation, residual connections - and a checklist run against five bugs that do not crash.
- Value: Most research time goes to runs that fail silently; this is the skill that turns a week of guessing into an afternoon.
- Lessons:
  - 04.01 Twenty layers that learn nothing: looking at activations and gradients
  - 04.02 Initialisation: keeping the signal the same size
  - 04.03 Batch normalisation
  - 04.04 Layer normalisation, and what the batch had to do with it
  - 04.05 Residual connections: a path the gradient keeps
  - 04.06 Five bugs that do not crash: a debugging checklist
- Learn from: [P-GLOROT], [P-HE], [P-BN], [P-LN], [P-RESNET], [V-ZTH], [A-RECIPE], [B-UDL]

## Module 05 - Generalisation

- Goal: Tell learning from memorising, and know what really narrows the gap between the two.
- You build: A network that memorises labels given at random, the same network regularised with weight decay, dropout and augmented data, and a double-descent curve from your own sweep of model sizes.
- Value: Every claim that a model "works" is a claim about data it has not seen; you will know how to make that claim and how to check someone else's.
- Lessons:
  - 05.01 Train, validation and test: a network that memorises random labels
  - 05.02 Weight decay and dropout
  - 05.03 More data for free: augmentation
  - 05.04 Double descent: when a bigger model overfits less
- Learn from: [P-RETHINK], [P-DROP], [P-DD], [B-UDL], [B-DL], [A-TUNE]

## Module 06 - Images: convolution and residual networks

- Goal: See what a convolution assumes about an image, and reproduce the result that made networks deep.
- You build: Convolution on your own engine, then the same script on PyTorch by changing one import, and ResNet against a plain network of the same depth on CIFAR-10, as in the paper's figure.
- Value: From here on you work in the framework researchers use, knowing what it does underneath, and the residual network is a baseline you can change for your own questions.
- Lessons:
  - 06.01 Convolution: the same weights at every position
  - 06.02 One import: the same script on PyTorch
  - 06.03 A convolutional network on CIFAR-10
  - 06.04 ResNet: the plain network against the residual one
- Learn from: [K-231N], [P-LENET], [P-CIFAR], [P-RESNET], [B-UDL], [A-BRRR], [C-PYTORCH]

## Module 07 - Language models, from counting to attention

- Goal: Understand a language model as a guess at the next symbol, scored by how surprised it is, and see what each model before the transformer could not do.
- You build: Next-character models of growing power on the same text - a table of counts, a network over embeddings, a recurrent network - each scored in bits per character, and an attention layer that solves the copying task the recurrent network fails.
- Value: Perplexity, embeddings and attention are the vocabulary of every paper on language models, and you will have measured each one.
- Lessons:
  - 07.01 Counting pairs: a bigram model, and the loss to beat
  - 07.02 Embeddings and a network: a neural language model
  - 07.03 A recurrent network, and how it forgets
  - 07.04 Attention: looking back at every position
- Learn from: [V-ZTH], [P-SHANNON], [P-NPLM], [A-RNN], [P-RNNDIFF], [P-BAHD], [B-SLP]

## Module 08 - The transformer: a GPT

- Goal: Understand the transformer as arithmetic you wrote: attention moves information between positions, and everything else changes it in place.
- You build: A GPT in one file - causal self-attention, heads, the residual stream, layer normalisation, positions - trained on Shakespeare until it writes passable verse, and a sampler with temperature, top-k and top-p.
- Value: This is the architecture under almost every current model; yours is small enough to read in one sitting and change in an afternoon.
- Lessons:
  - 08.01 Self-attention with a causal mask
  - 08.02 Many heads, and the residual stream
  - 08.03 Where am I: position embeddings
  - 08.04 Training a GPT on Shakespeare
  - 08.05 Sampling: temperature, top-k and top-p
- Learn from: [P-ATTN], [V-GPT], [A-ANNOT], [A-ILLUS], [C-NANOGPT], [P-NUCLEUS], [B-LLMFS]

## Module 09 - GPT-2: the tokenizer and the real weights

- Goal: Close the gap between your toy and a published model: the same tokens in, the same numbers out.
- You build: A byte pair encoding trainer, GPT-2's tokenizer giving tiktoken's ids, your GPT loading the published GPT-2 weights and giving the reference's logits, and a small model pretrained on TinyStories that tells a whole story.
- Value: The strongest check there is: a real model runs on code you wrote, so every later experiment can start from real weights.
- Lessons:
  - 09.01 Bytes, UTF-8 and byte pair encoding
  - 09.02 GPT-2's tokenizer: the same ids as tiktoken
  - 09.03 Loading GPT-2: the same logits as the reference
  - 09.04 Pretraining on TinyStories: a model that tells a story
- Learn from: [V-TOK], [P-BPE], [C-MINBPE], [C-TIKTOKEN], [P-GPT2], [C-GPT2], [P-TINY], [V-GPT2], [K-336]

## Module 10 - Today's architecture

- Goal: Read a current model's code and name each change since 2017: what it replaced and what it bought.
- You build: Your GPT changed one paper at a time into the architecture open models use now - RMSNorm, rotary positions, a gated MLP, grouped-query attention - loading a small open model's weights with the reference's logits, and an ablation table that says which change paid.
- Value: You can open the source of a model released this year and find nothing in it you have not written.
- Lessons:
  - 10.01 RMSNorm: normalising with less
  - 10.02 Rotary positions: turning instead of adding
  - 10.03 A gated MLP: SwiGLU
  - 10.04 Grouped-query attention, and loading a current open model
  - 10.05 Which change paid: an ablation table
- Learn from: [P-RMSNORM], [P-ROPE], [P-GLU], [P-GQA], [P-LLAMA], [C-SMOLLM], [K-336]

## Module 11 - Fast

- Goal: Know where a training step spends its time, and make the same loss arrive several times sooner.
- You build: A benchmark that reports tokens per second and the time to reach a target loss, a profile of one step, and four optimisations, each measured before and after: fused attention, lower precision, larger effective batches, and one of your own.
- Value: Compute is the budget of every experiment; a run that is three times faster is three times as many ideas tried.
- Lessons:
  - 11.01 Reading the benchmark: time to a target loss
  - 11.02 Where a step goes: profiling
  - 11.03 Attention without the big matrix
  - 11.04 Lower precision: sixteen bits, and what breaks
  - 11.05 Bigger batches: accumulation, clipping and the learning rate
  - 11.06 One more optimisation, measured
- Learn from: [A-BRRR], [A-PERF], [P-FLASH], [P-AMP], [C-MODDED], [K-336]

## Module 12 - Fine-tuning

- Goal: Change what a pretrained model does without training it again from zero, and prove that it changed.
- You build: GPT-2 fine-tuned to classify text, a LoRA adapter trained on a laptop, and a small model taught to follow instructions, each with an evaluation before and after.
- Value: Almost all applied work starts from someone else's weights; this is how you make them yours and know what you gave up.
- Lessons:
  - 12.01 A new head on a pretrained body
  - 12.02 LoRA: training under one percent of the weights
  - 12.03 Instructions: a chat template, and a model that answers
  - 12.04 What fine-tuning forgot: measuring before and after
- Learn from: [B-LLMFS], [P-GPT1], [P-LORA], [K-336]

## Module 13 - Experiments that hold up

- Goal: Produce a result that survives someone trying to break it.
- You build: A baseline tuned as hard as your own method, error bars over seeds, an evaluation you tried to fool and could not, and a scaling law that predicts the loss of a model before you train it.
- Value: This is the difference between a demo and a finding, and it is what a reviewer looks for first.
- Lessons:
  - 13.01 A hypothesis, and a baseline tuned as hard as your method
  - 13.02 Error bars: is the difference real?
  - 13.03 An evaluation you tried to fool
  - 13.04 Scaling: predicting a model you have not trained
- Learn from: [A-SCHUL], [P-RLMAT], [P-VAR], [P-EVALBARS], [P-IMNETV2], [P-SCALING], [A-TUNE]

## Module 14 - Reproduce a paper: grokking

- Goal: Turn a paper into code, and find out for yourself whether its claim holds.
- You build: The grokking paper's central figure from your own run - a network that memorises, then long afterwards suddenly generalises - the ablations that show what causes it, and a short reproduction report.
- Value: Reproduction is how you learn a subfield, and a careful reproduction is a real contribution in its own right.
- Lessons:
  - 14.01 Reading a paper for what it claims
  - 14.02 The experiment from the text: modular arithmetic
  - 14.03 The figure: memorise first, generalise much later
  - 14.04 Ablations, and the report
- Learn from: [A-KESHAV], [P-GROK], [C-GROK], [P-PROG], [A-SCHUL]

## Module 15 - Your own result

- Goal: Ask a small question nobody has answered, and answer it.
- You build: An experiment of your own design, a short paper, and a public repository anyone can rerun.
- Value: Finished, public research you can point to.
- Lessons:
  - 15.01 Choosing a question a laptop can answer
  - 15.02 The experiment, and the result you did not expect
  - 15.03 The paper, and a repository anyone can rerun
- Learn from: [A-HAMMING], [A-SCHUL], [A-SPJ]

## Module 16 - Looking inside

- Optional: yes
- Goal: Ask what a trained network computes, not only how well it scores.
- You build: A probe that reads a fact out of your GPT's activations, the algorithm inside the grokked network from module 14, found and then confirmed by breaking it, and a sparse autoencoder that splits your GPT's activations into features you can name.
- Value: Interpretability is an open field where small, careful work on small models still counts.
- Lessons:
  - 16.01 Probing: is it written in the activations?
  - 16.02 Patching: which part did the work?
  - 16.03 A circuit: the algorithm inside the grokked network
  - 16.04 Superposition: more features than dimensions
  - 16.05 A sparse autoencoder on your GPT
- Learn from: [P-PROBE], [P-PATCH], [A-CIRC], [A-MATH], [P-PROG], [A-TOY], [A-MONO], [P-SAE], [K-ARENA], [C-TLENS]

## Module 17 - Images from noise

- Optional: yes
- Goal: Understand generation as learning to undo noise, one step at a time.
- You build: A variational autoencoder, then a diffusion model trained on small images, a sampler that needs a tenth of the steps, and guidance that draws the class you ask for.
- Value: The same few ideas are under every current image, audio and video generator.
- Lessons:
  - 17.01 A variational autoencoder: a space you can sample from
  - 17.02 Diffusion: learning to remove noise
  - 17.03 Fewer steps: a deterministic sampler
  - 17.04 Guidance: asking for a class
  - 17.05 Flow matching: a straight path from noise
- Learn from: [P-VAE], [P-DDPM], [P-DDIM], [P-CFG], [P-FM], [A-WENGDIFF], [B-UDL]

## Module 18 - Learning from reward

- Optional: yes
- Goal: Train a network when nothing tells it the right answer, only how well it did.
- You build: A pole-balancing environment you wrote yourself, and three agents that master it - deep Q-learning, a policy gradient, and PPO - with an ablation of the implementation details the paper leaves out.
- Value: Reinforcement learning is where results are hardest to reproduce; having done it once by hand, you can tell a real gain from a lucky seed.
- Lessons:
  - 18.01 An environment, and a policy that acts at random
  - 18.02 Q-learning with a network
  - 18.03 Policy gradients: making good actions more likely
  - 18.04 A critic and an advantage
  - 18.05 PPO, and the details the paper leaves out
- Learn from: [B-RL], [K-SPIN], [P-DQN], [P-PG], [P-GAE], [P-PPO], [A-PPO37], [C-CLEANRL], [P-RLMAT]

## Module 19 - Seeing with transformers

- Optional: yes
- Goal: See that the block you built for text works on images, and what it needs that a convolution had built in.
- You build: A vision transformer made from your GPT's block and compared with your ResNet on the same small data, a contrastive loss, and CLIP's published weights loaded and used to label images it was never trained to label.
- Value: One architecture for text and images is what makes current multimodal models possible.
- Lessons:
  - 19.01 An image as a sequence of patches
  - 19.02 The vision transformer against ResNet when data is small
  - 19.03 A contrastive loss: matching pairs
  - 19.04 Loading CLIP: classifying with words
- Learn from: [P-VIT], [P-SIMCLR], [P-CLIP], [C-CLIP]

## Module 20 - Preferences

- Optional: yes
- Goal: Understand how a pretrained model is shaped afterwards by comparisons between answers, not by examples of the right one.
- You build: A reward model fitted to choices between pairs of stories, and your story model tuned with direct preference optimisation until a judge prefers what it writes, with a measure of what the tuning cost elsewhere.
- Value: This step turns a text predictor into an assistant, and it is where much current alignment work is done.
- Lessons:
  - 20.01 Comparisons as data: a reward model
  - 20.02 Direct preference optimisation
  - 20.03 Over-optimising: when the reward stops meaning what you wanted
- Learn from: [P-PREFS], [P-RLHF], [P-DPO], [K-336]

## Module 21 - Phenomena

- Optional: yes
- Goal: Reproduce four surprising results about how networks learn, each on a laptop, and judge the explanation offered for each.
- You build: A network pruned to a tenth of its weights that still trains, a small student that learns from its teacher's wrong answers, a training run sitting at the edge of stability, and a low-loss path between two separately trained networks.
- Value: These are the puzzles that theory is still trying to explain, and each is small enough to be the start of your own question.
- Lessons:
  - 21.01 The lottery ticket: a tenth of the weights was enough
  - 21.02 Distillation: learning from a teacher's mistakes
  - 21.03 The edge of stability: sharpness rises to meet the step size
  - 21.04 The loss landscape: two solutions, and the path between them
- Learn from: [P-LTH], [P-DISTILL], [P-EOS], [P-LANDSCAPE], [P-MODE], [P-DD]

## Library

| Key | Kind | Title | By | Where |
|---|---|---|---|---|
| B-UDL | book | Understanding Deep Learning | Simon J.D. Prince | MIT Press, 2023; free at https://udlbook.github.io/udlbook/ |
| B-DL | book | Deep Learning | Ian Goodfellow, Yoshua Bengio, Aaron Courville | MIT Press, 2016; free at https://www.deeplearningbook.org |
| B-D2L | book | Dive into Deep Learning | Zhang, Lipton, Li, Smola | free at https://d2l.ai |
| B-MML | book | Mathematics for Machine Learning | Deisenroth, Faisal, Ong | Cambridge, 2020; free at https://mml-book.github.io |
| B-LLMFS | book | Build a Large Language Model (From Scratch) | Sebastian Raschka | Manning, 2024; code at https://github.com/rasbt/LLMs-from-scratch |
| B-SLP | book | Speech and Language Processing, 3rd edition draft | Dan Jurafsky, James H. Martin | free at https://web.stanford.edu/~jurafsky/slp3/ |
| B-RL | book | Reinforcement Learning: An Introduction, 2nd edition | Richard Sutton, Andrew Barto | MIT Press, 2018; free at http://incompleteideas.net/book/the-book-2nd.html |
| V-MICRO | video | The spelled-out intro to neural networks and backpropagation: building micrograd | Andrej Karpathy | https://www.youtube.com/watch?v=VMj-3S1tku0 |
| V-ZTH | video | Neural Networks: Zero to Hero (playlist) | Andrej Karpathy | https://karpathy.ai/zero-to-hero.html |
| V-GPT | video | Let's build GPT: from scratch, in code, spelled out | Andrej Karpathy | https://www.youtube.com/watch?v=kCc8FmEb1nY |
| V-TOK | video | Let's build the GPT Tokenizer | Andrej Karpathy | https://www.youtube.com/watch?v=zduSFxRajkE |
| V-GPT2 | video | Let's reproduce GPT-2 (124M) | Andrej Karpathy | https://www.youtube.com/watch?v=l8pRSuU81PU |
| V-3B1B | video | Neural networks (series) | 3Blue1Brown | https://www.youtube.com/playlist?list=PLZHQObOWTQDNU6R1_67000Dx_ZCJB-3pi |
| K-231N | course | CS231n: Deep Learning for Computer Vision | Stanford | https://cs231n.stanford.edu |
| K-336 | course | CS336: Language Modeling from Scratch | Stanford | https://cs336.stanford.edu |
| K-DLSYS | course | Deep Learning Systems: Algorithms and Implementation | Zico Kolter, Tianqi Chen (2022 online course); Tianqi Chen, Tim Dettmers (CMU 10-414/714) | https://dlsyscourse.org |
| K-ARENA | course | ARENA: Alignment Research Engineer Accelerator | Callum McDougall and contributors | https://www.arena.education |
| K-SPIN | course | Spinning Up in Deep RL | Joshua Achiam, OpenAI | https://spinningup.openai.com |
| A-RECIPE | article | A Recipe for Training Neural Networks | Andrej Karpathy | https://karpathy.github.io/2019/04/25/recipe/ |
| A-SCHUL | article | An Opinionated Guide to ML Research | John Schulman | http://joschu.net/blog/opinionated-guide-ml-research.html |
| A-TUNE | article | Deep Learning Tuning Playbook | Godbole, Dahl, Gilmer, Shallue, Nado | https://github.com/google-research/tuning_playbook |
| A-MOMENTUM | article | Why Momentum Really Works | Gabriel Goh, Distill 2017 | https://distill.pub/2017/momentum/ |
| A-SAFET | article | safetensors README, section "Format" | Hugging Face | https://github.com/safetensors/safetensors#format |
| A-BRRR | article | Making Deep Learning Go Brrrr From First Principles | Horace He | https://horace.io/brrr_intro.html |
| A-PERF | article | Performance Tuning Guide | Szymon Migacz, PyTorch Tutorials | https://docs.pytorch.org/tutorials/recipes/recipes/tuning_guide.html |
| A-RNN | article | The Unreasonable Effectiveness of Recurrent Neural Networks | Andrej Karpathy | https://karpathy.github.io/2015/05/21/rnn-effectiveness/ |
| A-ILLUS | article | The Illustrated Transformer | Jay Alammar | https://jalammar.github.io/illustrated-transformer/ |
| A-ANNOT | article | The Annotated Transformer | Sasha Rush; 2022 update by Austin Huang and others | https://nlp.seas.harvard.edu/annotated-transformer/ |
| A-KESHAV | article | How to Read a Paper | S. Keshav | https://web.stanford.edu/class/ee384m/Handouts/HowtoReadPaper.pdf |
| A-HAMMING | article | You and Your Research | Richard Hamming | https://www.cs.virginia.edu/~robins/YouAndYourResearch.html |
| A-SPJ | article | How to Write a Great Research Paper | Simon Peyton Jones | https://www.microsoft.com/en-us/research/academic-program/write-great-research-paper/ |
| A-CIRC | article | Zoom In: An Introduction to Circuits | Olah et al., Distill 2020 | https://distill.pub/2020/circuits/zoom-in/ |
| A-MATH | article | A Mathematical Framework for Transformer Circuits | Elhage et al., 2021 | https://transformer-circuits.pub/2021/framework/index.html |
| A-TOY | article | Toy Models of Superposition | Elhage et al., 2022 | https://transformer-circuits.pub/2022/toy_model/index.html |
| A-MONO | article | Towards Monosemanticity: Decomposing Language Models With Dictionary Learning | Bricken et al., 2023 | https://transformer-circuits.pub/2023/monosemantic-features/index.html |
| A-WENGDIFF | article | What are Diffusion Models? | Lilian Weng | https://lilianweng.github.io/posts/2021-07-11-diffusion-models/ |
| A-PPO37 | article | The 37 Implementation Details of Proximal Policy Optimization | Huang et al., ICLR Blog Track 2022 | https://iclr-blog-track.github.io/2022/03/25/ppo-implementation-details/ |
| P-BACKPROP | paper | Learning representations by back-propagating errors | Rumelhart, Hinton, Williams, 1986 | https://doi.org/10.1038/323533a0 |
| P-AD | paper | Automatic Differentiation in Machine Learning: a Survey | Baydin et al., 2015 | https://arxiv.org/abs/1502.05767 |
| P-LENET | paper | Gradient-Based Learning Applied to Document Recognition | LeCun, Bottou, Bengio, Haffner, 1998 | http://yann.lecun.com/exdb/publis/pdf/lecun-98.pdf |
| P-MOM | paper | On the importance of initialization and momentum in deep learning | Sutskever, Martens, Dahl, Hinton, 2013 | https://proceedings.mlr.press/v28/sutskever13.html |
| P-ADAM | paper | Adam: A Method for Stochastic Optimization | Kingma, Ba, 2014 | https://arxiv.org/abs/1412.6980 |
| P-ADAMW | paper | Decoupled Weight Decay Regularization | Loshchilov, Hutter, 2017 | https://arxiv.org/abs/1711.05101 |
| P-SGDR | paper | SGDR: Stochastic Gradient Descent with Warm Restarts | Loshchilov, Hutter, 2016 | https://arxiv.org/abs/1608.03983 |
| P-GLOROT | paper | Understanding the difficulty of training deep feedforward neural networks | Glorot, Bengio, 2010 | https://proceedings.mlr.press/v9/glorot10a.html |
| P-HE | paper | Delving Deep into Rectifiers: Surpassing Human-Level Performance on ImageNet Classification | He et al., 2015 | https://arxiv.org/abs/1502.01852 |
| P-BN | paper | Batch Normalization: Accelerating Deep Network Training by Reducing Internal Covariate Shift | Ioffe, Szegedy, 2015 | https://arxiv.org/abs/1502.03167 |
| P-LN | paper | Layer Normalization | Ba, Kiros, Hinton, 2016 | https://arxiv.org/abs/1607.06450 |
| P-RESNET | paper | Deep Residual Learning for Image Recognition | He et al., 2015 | https://arxiv.org/abs/1512.03385 |
| P-RETHINK | paper | Understanding deep learning requires rethinking generalization | Zhang et al., 2016 | https://arxiv.org/abs/1611.03530 |
| P-DROP | paper | Dropout: A Simple Way to Prevent Neural Networks from Overfitting | Srivastava et al., 2014 | https://jmlr.org/papers/v15/srivastava14a.html |
| P-DD | paper | Deep Double Descent: Where Bigger Models and More Data Hurt | Nakkiran et al., 2019 | https://arxiv.org/abs/1912.02292 |
| P-CIFAR | paper | Learning Multiple Layers of Features from Tiny Images | Alex Krizhevsky, 2009 | https://www.cs.toronto.edu/~kriz/learning-features-2009-TR.pdf |
| P-SHANNON | paper | Prediction and Entropy of Printed English | Claude Shannon, 1951 | https://archive.org/details/bstj30-1-50 |
| P-NPLM | paper | A Neural Probabilistic Language Model | Bengio et al., 2003 | https://www.jmlr.org/papers/v3/bengio03a.html |
| P-RNNDIFF | paper | On the difficulty of training recurrent neural networks | Pascanu, Mikolov, Bengio, 2012 | https://arxiv.org/abs/1211.5063 |
| P-BAHD | paper | Neural Machine Translation by Jointly Learning to Align and Translate | Bahdanau, Cho, Bengio, 2014 | https://arxiv.org/abs/1409.0473 |
| P-ATTN | paper | Attention Is All You Need | Vaswani et al., 2017 | https://arxiv.org/abs/1706.03762 |
| P-NUCLEUS | paper | The Curious Case of Neural Text Degeneration | Holtzman et al., 2019 | https://arxiv.org/abs/1904.09751 |
| P-BPE | paper | Neural Machine Translation of Rare Words with Subword Units | Sennrich, Haddow, Birch, 2015 | https://arxiv.org/abs/1508.07909 |
| P-GPT1 | paper | Improving Language Understanding by Generative Pre-Training | Radford et al., 2018 | https://cdn.openai.com/research-covers/language-unsupervised/language_understanding_paper.pdf |
| P-GPT2 | paper | Language Models are Unsupervised Multitask Learners | Radford et al., 2019 | https://cdn.openai.com/better-language-models/language_models_are_unsupervised_multitask_learners.pdf |
| P-TINY | paper | TinyStories: How Small Can Language Models Be and Still Speak Coherent English? | Eldan, Li, 2023 | https://arxiv.org/abs/2305.07759 |
| P-RMSNORM | paper | Root Mean Square Layer Normalization | Zhang, Sennrich, 2019 | https://arxiv.org/abs/1910.07467 |
| P-ROPE | paper | RoFormer: Enhanced Transformer with Rotary Position Embedding | Su et al., 2021 | https://arxiv.org/abs/2104.09864 |
| P-GLU | paper | GLU Variants Improve Transformer | Noam Shazeer, 2020 | https://arxiv.org/abs/2002.05202 |
| P-GQA | paper | GQA: Training Generalized Multi-Query Transformer Models from Multi-Head Checkpoints | Ainslie et al., 2023 | https://arxiv.org/abs/2305.13245 |
| P-LLAMA | paper | LLaMA: Open and Efficient Foundation Language Models | Touvron et al., 2023 | https://arxiv.org/abs/2302.13971 |
| P-FLASH | paper | FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness | Dao et al., 2022 | https://arxiv.org/abs/2205.14135 |
| P-AMP | paper | Mixed Precision Training | Micikevicius et al., 2017 | https://arxiv.org/abs/1710.03740 |
| P-LORA | paper | LoRA: Low-Rank Adaptation of Large Language Models | Hu et al., 2021 | https://arxiv.org/abs/2106.09685 |
| P-RLMAT | paper | Deep Reinforcement Learning that Matters | Henderson et al., 2017 | https://arxiv.org/abs/1709.06560 |
| P-VAR | paper | Accounting for Variance in Machine Learning Benchmarks | Bouthillier et al., 2021 | https://arxiv.org/abs/2103.03098 |
| P-EVALBARS | paper | Adding Error Bars to Evals: A Statistical Approach to Language Model Evaluations | Evan Miller, 2024 | https://arxiv.org/abs/2411.00640 |
| P-IMNETV2 | paper | Do ImageNet Classifiers Generalize to ImageNet? | Recht et al., 2019 | https://arxiv.org/abs/1902.10811 |
| P-SCALING | paper | Scaling Laws for Neural Language Models | Kaplan et al., 2020 | https://arxiv.org/abs/2001.08361 |
| P-GROK | paper | Grokking: Generalization Beyond Overfitting on Small Algorithmic Datasets | Power et al., 2022 | https://arxiv.org/abs/2201.02177 |
| P-PROG | paper | Progress measures for grokking via mechanistic interpretability | Nanda et al., 2023 | https://arxiv.org/abs/2301.05217 |
| P-PROBE | paper | Understanding intermediate layers using linear classifier probes | Alain, Bengio, 2016 | https://arxiv.org/abs/1610.01644 |
| P-PATCH | paper | How to use and interpret activation patching | Heimersheim, Nanda, 2024 | https://arxiv.org/abs/2404.15255 |
| P-SAE | paper | Sparse Autoencoders Find Highly Interpretable Features in Language Models | Cunningham et al., 2023 | https://arxiv.org/abs/2309.08600 |
| P-VAE | paper | Auto-Encoding Variational Bayes | Kingma, Welling, 2013 | https://arxiv.org/abs/1312.6114 |
| P-DDPM | paper | Denoising Diffusion Probabilistic Models | Ho, Jain, Abbeel, 2020 | https://arxiv.org/abs/2006.11239 |
| P-DDIM | paper | Denoising Diffusion Implicit Models | Song, Meng, Ermon, 2020 | https://arxiv.org/abs/2010.02502 |
| P-CFG | paper | Classifier-Free Diffusion Guidance | Ho, Salimans, 2022 | https://arxiv.org/abs/2207.12598 |
| P-FM | paper | Flow Matching for Generative Modeling | Lipman et al., 2022 | https://arxiv.org/abs/2210.02747 |
| P-DQN | paper | Playing Atari with Deep Reinforcement Learning | Mnih et al., 2013 | https://arxiv.org/abs/1312.5602 |
| P-PG | paper | Simple statistical gradient-following algorithms for connectionist reinforcement learning | Ronald Williams, 1992 | https://doi.org/10.1007/BF00992696 |
| P-GAE | paper | High-Dimensional Continuous Control Using Generalized Advantage Estimation | Schulman et al., 2015 | https://arxiv.org/abs/1506.02438 |
| P-PPO | paper | Proximal Policy Optimization Algorithms | Schulman et al., 2017 | https://arxiv.org/abs/1707.06347 |
| P-VIT | paper | An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale | Dosovitskiy et al., 2020 | https://arxiv.org/abs/2010.11929 |
| P-SIMCLR | paper | A Simple Framework for Contrastive Learning of Visual Representations | Chen et al., 2020 | https://arxiv.org/abs/2002.05709 |
| P-CLIP | paper | Learning Transferable Visual Models From Natural Language Supervision | Radford et al., 2021 | https://arxiv.org/abs/2103.00020 |
| P-PREFS | paper | Deep reinforcement learning from human preferences | Christiano et al., 2017 | https://arxiv.org/abs/1706.03741 |
| P-RLHF | paper | Training language models to follow instructions with human feedback | Ouyang et al., 2022 | https://arxiv.org/abs/2203.02155 |
| P-DPO | paper | Direct Preference Optimization: Your Language Model is Secretly a Reward Model | Rafailov et al., 2023 | https://arxiv.org/abs/2305.18290 |
| P-LTH | paper | The Lottery Ticket Hypothesis: Finding Sparse, Trainable Neural Networks | Frankle, Carbin, 2018 | https://arxiv.org/abs/1803.03635 |
| P-DISTILL | paper | Distilling the Knowledge in a Neural Network | Hinton, Vinyals, Dean, 2015 | https://arxiv.org/abs/1503.02531 |
| P-EOS | paper | Gradient Descent on Neural Networks Typically Occurs at the Edge of Stability | Cohen et al., 2021 | https://arxiv.org/abs/2103.00065 |
| P-LANDSCAPE | paper | Visualizing the Loss Landscape of Neural Nets | Li et al., 2017 | https://arxiv.org/abs/1712.09913 |
| P-MODE | paper | Loss Surfaces, Mode Connectivity, and Fast Ensembling of DNNs | Garipov et al., 2018 | https://arxiv.org/abs/1802.10026 |
| C-PYTORCH | code | PyTorch | The PyTorch Foundation and contributors | https://github.com/pytorch/pytorch |
| C-MICROGRAD | code | micrograd | Andrej Karpathy | https://github.com/karpathy/micrograd |
| C-TINYGRAD | code | tinygrad | George Hotz, the tiny corp and contributors | https://github.com/tinygrad/tinygrad |
| C-NANOGPT | code | nanoGPT | Andrej Karpathy | https://github.com/karpathy/nanoGPT |
| C-MINBPE | code | minbpe | Andrej Karpathy | https://github.com/karpathy/minbpe |
| C-TIKTOKEN | code | tiktoken | OpenAI | https://github.com/openai/tiktoken |
| C-GPT2 | code | gpt-2 | OpenAI | https://github.com/openai/gpt-2 |
| C-SMOLLM | code | SmolLM2-135M | Hugging Face | https://huggingface.co/HuggingFaceTB/SmolLM2-135M |
| C-MODDED | code | modded-nanogpt | Keller Jordan and contributors | https://github.com/KellerJordan/modded-nanogpt |
| C-GROK | code | grok | OpenAI | https://github.com/openai/grok |
| C-TLENS | code | TransformerLens | Neel Nanda, Joseph Bloom and contributors | https://github.com/TransformerLensOrg/TransformerLens |
| C-CLEANRL | code | CleanRL | Costa Huang and contributors | https://github.com/vwxyzjn/cleanrl |
| C-CLIP | code | CLIP | OpenAI | https://github.com/openai/CLIP |
